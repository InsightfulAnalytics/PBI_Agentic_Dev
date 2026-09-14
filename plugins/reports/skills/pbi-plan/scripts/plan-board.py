#!/usr/bin/env python3
"""Render PLAN.md as a self-contained HTML plan board.

The markdown file is the source of truth and the only thing anyone edits. This script
reads it and writes a single HTML file beside it, so the board can never disagree with
the plan: regenerate after every status change and the two stay in lockstep.

Usage::

    python plan-board.py PLAN.md                  # writes PLAN.html beside it
    python plan-board.py PLAN.md -o board.html
    python plan-board.py PLAN.md --frontier       # print the next tickets, write nothing

Exit codes: 0 fine, 1 the plan has a structural problem (a blocker that does not exist,
or a dependency cycle), 2 bad invocation.

Expected PLAN.md shape (see the skill's SKILL.md for the authoring rules)::

    # <name> build plan

    **PBIP:** Sales.pbip

    ## Out of scope
    - row-level security

    ## Not yet specified
    - Tooltips: not decided

    ## Tickets

    ### 03: Spend by category
    Type: page
    Status: open
    Blocked by: 01, 02
    Exit: `pbir validate "Sales.Report"`

    What to build: one bar chart, spend by category, sorted descending.

    - [ ] the chart passes the insight test
    - [ ] alt text written
"""

from __future__ import annotations

import argparse
import html
import io
import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

TICKET_RE = re.compile(r"^###\s+(\d+)\s*[:.\-]\s*(.+?)\s*$")
FIELD_RE = re.compile(r"^\*{0,2}(Type|Status|Blocked by|Exit|Owner)\*{0,2}\s*:\s*(.*)$", re.I)
CHECK_RE = re.compile(r"^\s*[-*]\s+\[([ xX])\]\s+(.*)$")
HEADING_RE = re.compile(r"^##\s+(.+?)\s*$")

DONE = "done"
CUT = "cut"
OPEN = "open"
ACTIVE = "in progress"
BLOCKED = "blocked"

STATUS_ORDER = [ACTIVE, BLOCKED, OPEN, DONE, CUT]

# The fog list has to name these even when the answer is "none". They are the axes a
# page artboard does not cover, so they are the ones that arrive as scope changes.
REQUIRED_FOG = ["tooltip", "navigation", "theme", "accessib"]


class BadInvocation(Exception):
    """Bad path or unreadable plan. Exits 2."""


@dataclass
class Ticket:
    number: int
    title: str
    type: str = ""
    status: str = OPEN
    blocked_by: list = field(default_factory=list)
    exit_cmd: str = ""
    body: str = ""
    checks: list = field(default_factory=list)
    wave: int = 0
    derived_blocked: bool = False

    @property
    def key(self) -> str:
        return f"{self.number:02d}"

    @property
    def effective_status(self) -> str:
        if self.status in (DONE, CUT):
            return self.status
        if self.derived_blocked:
            return BLOCKED
        return self.status

    @property
    def done_checks(self) -> int:
        return sum(1 for c in self.checks if c[0])


@dataclass
class Plan:
    title: str = "Build plan"
    meta: list = field(default_factory=list)     # (label, value)
    tickets: list = field(default_factory=list)
    fog: list = field(default_factory=list)
    out_of_scope: list = field(default_factory=list)
    notes: list = field(default_factory=list)
    problems: list = field(default_factory=list)


# ------------------------------------------------------------------ parsing


def parse(text: str) -> Plan:
    plan = Plan()
    lines = text.splitlines()
    section = "preamble"
    current = None
    body: list = []

    def close_ticket():
        nonlocal current, body
        if current is not None:
            current.body = "\n".join(body).strip()
            plan.tickets.append(current)
        current, body = None, []

    for raw in lines:
        line = raw.rstrip()

        if line.startswith("# ") and section == "preamble":
            plan.title = line[2:].strip()
            continue

        heading = HEADING_RE.match(line)
        if heading:
            close_ticket()
            name = heading.group(1).lower()
            if "out of scope" in name:
                section = "scope"
            elif "not yet specified" in name or "fog" in name or "undecided" in name:
                section = "fog"
            elif "ticket" in name:
                section = "tickets"
            else:
                section = "notes"
                plan.notes.append((heading.group(1), []))
            continue

        ticket = TICKET_RE.match(line)
        if ticket and section == "tickets":
            close_ticket()
            current = Ticket(number=int(ticket.group(1)), title=ticket.group(2))
            continue

        if current is not None:
            field_m = FIELD_RE.match(line)
            if field_m and not body:
                key, value = field_m.group(1).lower(), field_m.group(2).strip()
                if key == "type":
                    current.type = value
                elif key == "status":
                    current.status = value.lower().strip("*` ") or OPEN
                elif key == "blocked by":
                    if value.lower().strip(" .") not in ("", "none", "-", "nothing"):
                        current.blocked_by = [
                            int(n) for n in re.findall(r"\d+", value)
                        ]
                elif key == "exit":
                    current.exit_cmd = value.strip("`")
                continue
            check = CHECK_RE.match(line)
            if check:
                current.checks.append((check.group(1).lower() == "x", check.group(2)))
                continue
            if line.strip() or body:
                # A blank line between the heading and the first field must not count as
                # body, or every field after it is read as prose and silently dropped.
                body.append(line)
            continue

        stripped = line.strip()
        if section == "scope" and stripped.startswith(("-", "*")):
            plan.out_of_scope.append(stripped.lstrip("-* ").strip())
        elif section == "fog" and stripped.startswith(("-", "*")):
            plan.fog.append(stripped.lstrip("-* ").strip())
        elif section == "preamble" and stripped.startswith("**") and ":" in stripped:
            label, _, value = stripped.partition(":")
            plan.meta.append((label.strip("* "), value.strip().strip("*")))
        elif section == "notes" and plan.notes and stripped:
            plan.notes[-1][1].append(stripped)

    close_ticket()
    return plan


def analyse(plan: Plan) -> None:
    """Derive blocked status and wave depth; record structural problems."""
    by_number = {t.number: t for t in plan.tickets}

    for ticket in plan.tickets:
        for blocker in ticket.blocked_by:
            if blocker not in by_number:
                plan.problems.append(
                    f"ticket {ticket.key} is blocked by {blocker:02d}, which does not exist"
                )
        ticket.derived_blocked = any(
            by_number[b].status not in (DONE, CUT)
            for b in ticket.blocked_by if b in by_number
        )

    # Wave = longest dependency chain behind this ticket. Cycles are reported, not crashed on.
    depth: dict = {}
    visiting: set = set()

    def resolve(number: int, trail: tuple) -> int:
        if number in depth:
            return depth[number]
        if number in visiting:
            plan.problems.append(
                "dependency cycle: " + " -> ".join(f"{n:02d}" for n in trail + (number,))
            )
            depth[number] = 0
            return 0
        visiting.add(number)
        parents = [b for b in by_number[number].blocked_by if b in by_number]
        value = 1 + max((resolve(b, trail + (number,)) for b in parents), default=-1)
        visiting.discard(number)
        depth[number] = value
        return value

    for ticket in plan.tickets:
        ticket.wave = resolve(ticket.number, ())

    missing = [
        axis for axis in REQUIRED_FOG
        if not any(axis in entry.lower() for entry in plan.fog)
    ]
    if missing:
        pretty = {"accessib": "accessibility"}
        plan.problems.append(
            "the fog list does not name: "
            + ", ".join(pretty.get(m, m) for m in missing)
            + ' (name each one even when the answer is "none")'
        )


def frontier(plan: Plan) -> list:
    """Open, unblocked, lowest number first. The only tickets eligible to be picked up."""
    return sorted(
        (t for t in plan.tickets
         if t.effective_status in (OPEN, ACTIVE) and not t.derived_blocked),
        key=lambda t: (t.effective_status != ACTIVE, t.number),
    )


# ------------------------------------------------------------------- render


def esc(value) -> str:
    return html.escape(str(value), quote=True)


# Three theme states, not two. An explicit choice stamps data-theme on the root; the
# default "system" setting stamps nothing, so only prefers-color-scheme separates light
# from dark there. Defining the dark tokens in both places is what makes an explicit
# light choice beat a dark OS, and an explicit dark choice beat a light one.
DARK_TOKENS = """
    --bg: #16171a; --panel: #1e2024; --ink: #e8e8e4; --muted: #9a9a93;
    --line: #2e3035; --accent: #63c0a5; --shadow: none;
    --open: #8a8a84; --active: #d99a3c; --blocked: #d97070; --done: #63c0a5; --cut: #6a6a64;
"""

CSS = """
:root {
  color-scheme: light dark;
  --bg: #f6f6f4; --panel: #ffffff; --ink: #1b1b1a; --muted: #6b6b66;
  --line: #e0dfda; --accent: #1f6f5c; --shadow: 0 1px 2px rgba(0,0,0,.06);
  --open: #8a8a84; --active: #b26a00; --blocked: #a33a3a; --done: #1f6f5c; --cut: #9a9a94;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {""" + DARK_TOKENS + """  }
}
:root[data-theme="dark"] {""" + DARK_TOKENS + """}
* { box-sizing: border-box; }
body {
  margin: 0; padding: 28px 24px 64px; background: var(--bg); color: var(--ink);
  font: 14px/1.55 ui-sans-serif, -apple-system, "Segoe UI", system-ui, sans-serif;
}
.wrap { max-width: 1180px; margin: 0 auto; }
h1 { font-size: 22px; margin: 0 0 4px; letter-spacing: -.01em; }
h2 { font-size: 13px; text-transform: uppercase; letter-spacing: .08em; color: var(--muted);
     margin: 32px 0 12px; font-weight: 600; }
.meta { color: var(--muted); font-size: 13px; margin-bottom: 18px; }
.meta b { color: var(--ink); font-weight: 600; }
.bar { height: 8px; border-radius: 4px; background: var(--line); overflow: hidden; display: flex; }
.bar i { display: block; height: 100%; }
.bar .d { background: var(--done); } .bar .a { background: var(--active); }
.bar .b { background: var(--blocked); } .bar .c { background: var(--cut); }
.legend { display: flex; flex-wrap: wrap; gap: 14px; margin: 10px 0 0; font-size: 12.5px; color: var(--muted); }
.legend span::before { content: ""; display: inline-block; width: 9px; height: 9px; border-radius: 2px;
  margin-right: 6px; vertical-align: baseline; background: currentColor; }
.s-open { color: var(--open); } .s-active { color: var(--active); }
.s-blocked { color: var(--blocked); } .s-done { color: var(--done); } .s-cut { color: var(--cut); }
.timeline { list-style: none; margin: 0; padding: 0 0 0 32px; position: relative; max-width: 720px; }
.timeline::before { content: ""; position: absolute; left: 9px; top: 8px; bottom: 18px;
  width: 2px; background: var(--line); border-radius: 1px; }
.timeline > li { position: relative; }
.timeline > li::before { content: ""; box-sizing: border-box; position: absolute;
  left: -28px; top: 14px; width: 12px; height: 12px; border-radius: 50%;
  background: var(--bg); border: 2px solid var(--open); }
.timeline > li.done::before { background: var(--done); border-color: var(--done); }
.timeline > li.in-progress::before { background: var(--active); border-color: var(--active); }
.timeline > li.blocked::before { border-color: var(--blocked); }
.timeline > li.cut::before { border-color: var(--cut); opacity: .55; }
.timeline > li.milestone { margin: 26px 0 11px; }
.timeline > li.milestone:first-child { margin-top: 0; }
.timeline > li.milestone::before { left: -30px; top: 1px; width: 16px; height: 16px;
  border-radius: 3px; border-color: var(--line); }
.timeline > li.milestone span { font-size: 11.5px; text-transform: uppercase;
  letter-spacing: .09em; color: var(--muted); font-weight: 600; }
.card { background: var(--panel); border: 1px solid var(--line); border-left: 3px solid var(--open);
  border-radius: 6px; padding: 11px 13px; margin-bottom: 10px; box-shadow: var(--shadow); }
.card.done { border-left-color: var(--done); } .card.done .t { text-decoration: line-through; opacity: .62; }
.card.in-progress { border-left-color: var(--active); }
.card.blocked { border-left-color: var(--blocked); }
.card.cut { border-left-color: var(--cut); opacity: .5; }
.card.next { outline: 2px solid var(--accent); outline-offset: 1px; }
.n { font: 600 11px/1 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  color: var(--muted); letter-spacing: .06em; }
.t { font-weight: 600; margin: 3px 0 7px; }
.chips { display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: 7px; }
.chip { font-size: 11px; padding: 1px 7px; border-radius: 10px; border: 1px solid var(--line);
  color: var(--muted); white-space: nowrap; }
.chip.st { border-color: currentColor; }
.what { font-size: 13px; color: var(--muted); margin: 0 0 8px; }
ul.ac { list-style: none; padding: 0; margin: 0 0 8px; font-size: 12.5px; }
ul.ac li { padding-left: 19px; position: relative; color: var(--muted); margin-bottom: 2px; }
ul.ac li::before { content: "\\25A2"; position: absolute; left: 2px; }
ul.ac li.y::before { content: "\\2713"; color: var(--done); }
ul.ac li.y { text-decoration: line-through; opacity: .65; }
code, .exit { font: 11.5px/1.45 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
.exit { display: block; background: var(--bg); border: 1px solid var(--line); border-radius: 4px;
  padding: 5px 7px; color: var(--ink); overflow-x: auto; white-space: pre; }
.exit b { color: var(--muted); font-weight: 600; }
.panels { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 16px; }
.panel { background: var(--panel); border: 1px solid var(--line); border-radius: 6px;
  padding: 14px 16px; box-shadow: var(--shadow); }
.panel h3 { margin: 0 0 9px; font-size: 13px; }
.panel ul { margin: 0; padding-left: 18px; font-size: 13px; color: var(--muted); }
.panel li { margin-bottom: 4px; }
.panel li b { color: var(--ink); font-weight: 600; }
.warn { border-left: 3px solid var(--blocked); }
.warn h3 { color: var(--blocked); }
.next-up { background: var(--panel); border: 1px solid var(--accent); border-radius: 6px;
  padding: 12px 16px; margin-bottom: 8px; }
.next-up h3 { margin: 0 0 6px; font-size: 13px; color: var(--accent); }
.next-up ol { margin: 0; padding-left: 20px; font-size: 13px; }
.next-up li { margin-bottom: 3px; }
.next-up .first { font-weight: 600; }
footer { margin-top: 40px; color: var(--muted); font-size: 12px; border-top: 1px solid var(--line);
  padding-top: 12px; }
@media print {
  body { background: #fff; padding: 0; } .card, .panel { box-shadow: none; break-inside: avoid; }
  .timeline { max-width: none; }
}
"""


def status_class(status: str) -> str:
    return status.replace(" ", "-")


def render(plan: Plan, source: Path) -> str:
    tickets = sorted(plan.tickets, key=lambda t: t.number)
    counts = {s: sum(1 for t in tickets if t.effective_status == s) for s in STATUS_ORDER}
    total = len(tickets) or 1
    live = [t for t in tickets if t.effective_status != CUT]
    next_up = frontier(plan)
    next_keys = {t.number for t in next_up[:1]}

    def pct(n):
        return f"{100 * n / total:.4f}%"

    parts = ["<div class=\"wrap\">"]
    parts.append(f"<h1>{esc(plan.title)}</h1>")

    meta_bits = [f"<b>{esc(k)}</b> {esc(v)}" for k, v in plan.meta]
    meta_bits.append(f"<b>{len(live)}</b> tickets")
    meta_bits.append(f"<b>{counts[DONE]}</b> done")
    parts.append(f"<div class=\"meta\">{' &middot; '.join(meta_bits)}</div>")

    parts.append(
        "<div class=\"bar\">"
        f"<i class=\"d\" style=\"width:{pct(counts[DONE])}\"></i>"
        f"<i class=\"a\" style=\"width:{pct(counts[ACTIVE])}\"></i>"
        f"<i class=\"b\" style=\"width:{pct(counts[BLOCKED])}\"></i>"
        f"<i class=\"c\" style=\"width:{pct(counts[CUT])}\"></i>"
        "</div>"
    )
    parts.append("<div class=\"legend\">" + "".join(
        f"<span class=\"s-{status_class(s)}\">{counts[s]} {esc(s)}</span>"
        for s in STATUS_ORDER if counts[s]
    ) + "</div>")

    if plan.problems:
        parts.append("<h2>Plan problems</h2><div class=\"panel warn\"><h3>Fix before building</h3><ul>")
        parts.extend(f"<li>{esc(p)}</li>" for p in plan.problems)
        parts.append("</ul></div>")

    parts.append("<h2>Next up</h2>")
    if next_up:
        parts.append("<div class=\"next-up\"><h3>The frontier: open, unblocked, lowest number first</h3><ol>")
        for i, ticket in enumerate(next_up[:5]):
            klass = ' class="first"' if i == 0 else ""
            parts.append(f"<li{klass}><code>{esc(ticket.key)}</code> {esc(ticket.title)}</li>")
        parts.append("</ol></div>")
    elif counts[DONE] + counts[CUT] == len(tickets):
        parts.append("<div class=\"next-up\"><h3>Frontier empty. Every ticket is done or cut.</h3></div>")
    else:
        parts.append(
            "<div class=\"panel warn\"><h3>Frontier empty, work outstanding</h3><ul>"
            "<li>Every remaining ticket is blocked. Something upstream needs finishing, "
            "or a <b>Blocked by</b> line is wrong.</li></ul></div>"
        )

    parts.append("<h2>The build</h2><ol class=\"timeline\">")
    waves = sorted({t.wave for t in tickets})
    for wave in waves:
        # A wave is everything whose blockers are all satisfied by the waves above it, so
        # a wave marker is the honest milestone on a timeline: the tickets under it can be
        # worked in any order, and nothing in it can start before the wave above finishes.
        parts.append(f"<li class=\"milestone\"><span>Wave {wave + 1}</span></li>")
        for ticket in [t for t in tickets if t.wave == wave]:
            status = ticket.effective_status
            classes = ["card", status_class(status)]
            if ticket.number in next_keys:
                classes.append("next")
            parts.append(f"<li class=\"{status_class(status)}\">")
            parts.append(f"<div class=\"{' '.join(classes)}\">")
            parts.append(f"<div class=\"n\">{esc(ticket.key)}</div>")
            parts.append(f"<div class=\"t\">{esc(ticket.title)}</div>")

            chips = [f"<span class=\"chip st s-{status_class(status)}\">{esc(status)}</span>"]
            if ticket.type:
                chips.append(f"<span class=\"chip\">{esc(ticket.type)}</span>")
            if ticket.blocked_by:
                chips.append(
                    "<span class=\"chip\">after "
                    + ", ".join(f"{b:02d}" for b in sorted(ticket.blocked_by))
                    + "</span>"
                )
            if ticket.checks:
                chips.append(
                    f"<span class=\"chip\">{ticket.done_checks}/{len(ticket.checks)}</span>"
                )
            parts.append(f"<div class=\"chips\">{''.join(chips)}</div>")

            what = ticket.body.strip().splitlines()
            if what:
                first = re.sub(r"^\*{0,2}What to build\*{0,2}\s*:\s*", "", what[0]).strip()
                if first:
                    parts.append(f"<p class=\"what\">{esc(first)}</p>")

            if ticket.checks:
                parts.append("<ul class=\"ac\">")
                for ok, label in ticket.checks:
                    parts.append(f"<li class=\"{'y' if ok else 'n'}\">{esc(label)}</li>")
                parts.append("</ul>")

            if ticket.exit_cmd:
                parts.append(f"<span class=\"exit\"><b>exit</b> {esc(ticket.exit_cmd)}</span>")
            parts.append("</div></li>")
    parts.append("</ol>")

    parts.append("<h2>What is still open</h2><div class=\"panels\">")
    parts.append("<div class=\"panel\"><h3>Not yet specified</h3>")
    if plan.fog:
        parts.append("<ul>")
        for entry in plan.fog:
            label, sep, rest = entry.partition(":")
            parts.append(
                f"<li><b>{esc(label)}</b>{esc(sep)} {esc(rest.strip())}</li>" if sep
                else f"<li>{esc(entry)}</li>"
            )
        parts.append("</ul>")
    else:
        parts.append("<ul><li>Nothing listed. That is almost never true: fill it in.</li></ul>")
    parts.append("</div>")

    parts.append("<div class=\"panel\"><h3>Out of scope</h3>")
    if plan.out_of_scope:
        parts.append("<ul>" + "".join(f"<li>{esc(e)}</li>" for e in plan.out_of_scope) + "</ul>")
    else:
        parts.append("<ul><li>Nothing declared out of scope.</li></ul>")
    parts.append("</div>")

    for heading, lines in plan.notes:
        if not lines:
            continue
        parts.append(f"<div class=\"panel\"><h3>{esc(heading)}</h3><ul>")
        parts.extend(f"<li>{esc(l.lstrip('-* '))}</li>" for l in lines if l.strip())
        parts.append("</ul></div>")
    parts.append("</div>")

    parts.append(
        f"<footer>Generated from <code>{esc(source.name)}</code> on {date.today().isoformat()}. "
        "The markdown is the source of truth; regenerate this board after every status change."
        "</footer></div>"
    )

    return (
        "<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        f"<title>{esc(plan.title)}</title>\n<style>{CSS}</style>\n</head>\n<body>\n"
        + "\n".join(parts)
        + "\n</body>\n</html>\n"
    )


# --------------------------------------------------------------------- main


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Render PLAN.md as a self-contained HTML plan board.")
    ap.add_argument("plan", help="path to PLAN.md")
    ap.add_argument("-o", "--out", help="output HTML path (default: the plan's name with .html)")
    ap.add_argument("--frontier", action="store_true",
                    help="print the frontier and any plan problems, write no HTML")
    args = ap.parse_args(argv)

    source = Path(args.plan).expanduser().resolve()
    if not source.is_file():
        raise BadInvocation(f"no such plan: {args.plan}")

    plan = parse(io.open(source, encoding="utf-8").read())
    if not plan.tickets:
        raise BadInvocation(
            f"{source.name} has no tickets. Expected `### NN: title` headings under `## Tickets`."
        )
    analyse(plan)

    if args.frontier:
        for ticket in frontier(plan):
            print(f"{ticket.key}  {ticket.effective_status:<11}  {ticket.title}")
        if not frontier(plan):
            print("frontier empty")
        for problem in plan.problems:
            print(f"problem: {problem}", file=sys.stderr)
        return 1 if plan.problems else 0

    out = Path(args.out).expanduser().resolve() if args.out else source.with_suffix(".html")
    io.open(out, "w", encoding="utf-8", newline="\n").write(render(plan, source))

    done = sum(1 for t in plan.tickets if t.effective_status == DONE)
    print(f"plan-board: {out}")
    print(f"  {len(plan.tickets)} tickets, {done} done, {len(frontier(plan))} on the frontier")
    for problem in plan.problems:
        print(f"  problem: {problem}")
    return 1 if plan.problems else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BadInvocation as exc:
        print(f"plan-board: {exc}", file=sys.stderr)
        sys.exit(2)
