#!/usr/bin/env python3
"""Skill hygiene checks for the power-bi-agentic-dev marketplace.

Four jobs, one walk of the tracked markdown:

1. Dated-claim rot. A ``Verified <date>`` stamp older than ``--max-age-days`` is reported
   when it carries a ``Retest:`` line, and is an error when the claim pins a tool version
   but gives no ``Retest:`` command. A version in the imperative rots into a lie.
2. Machine-path leakage. Absolute user paths, workspace roots and per-machine memory-file
   locations must not ship in a public plugin.
3. Personal-data denylist. Literal terms are matched by SHA-256 of a normalised n-gram, so
   the tracked denylist never contains the terms it protects.
4. Cross-reference resolution. Every relative markdown link and ``#anchor`` under
   ``plugins/`` must resolve to a real file and a real heading.
5. SKILL.md frontmatter sanity. An unquoted YAML scalar cannot contain ": ", and a skill whose
   frontmatter fails to parse loads with EVERY field silently dropped, so it never triggers.

Usage::

    python scripts/check-skill-hygiene.py
    python scripts/check-skill-hygiene.py --staged
    python scripts/check-skill-hygiene.py --max-age-days 365 --json

Exit codes: 0 clean, 1 errors found, 2 bad invocation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

REPO = Path(__file__).resolve().parent.parent

DENYLIST_HASHES = REPO / ".github" / "denylist-hashes.txt"
DENYLIST_PATTERNS = REPO / ".github" / "denylist-patterns.txt"
LEARNINGS = REPO / "LEARNINGS.md"

# Files carrying a copy of the boundary rule, kept byte-identical to LEARNINGS.md.
SENTINEL_FILES = [
    REPO / "plugins/fabric-cli/skills/fabric-cli/SKILL.md",
    REPO / "plugins/pbi-desktop/skills/connect-pbid/SKILL.md",
    REPO / "plugins/reports/skills/pbir-cli/SKILL.md",
]
SENTINEL_BEGIN = "<!-- boundary-rule:begin -->"
SENTINEL_END = "<!-- boundary-rule:end -->"

# Longest denylist term, in words. Bounds the n-gram sweep.
MAX_NGRAM = 5

VERIFIED_RE = re.compile(
    r"[Vv]erified\s+(?:on\s+)?(\d{4})-(\d{2})-(\d{2})|VERIFIED\s+(\d{4})-(\d{2})-(\d{2})"
)
RETEST_RE = re.compile(r"^\s*(?:[-*>]\s*)?(?:\*\*)?Retest:(?:\*\*)?\s*\S", re.MULTILINE)

# A claim that pins a tool to a version. These rot fastest and need a retest command.
VERSION_CLAIM_RE = re.compile(
    r"\b(?:"
    r"(?:fab|pbir|te|az|pbiviz|node|python)\s+(?:version\s+)?v?\d+\.\d+(?:\.\d+)?"
    r"|version\s+\d+\.\d+(?:\.\d+)?\s+(?:of|is|has|does|lacks)"
    r"|\b\d+\.\d+\.\d+\s+(?:added|removed|introduced|dropped|has no|does not)"
    r"|PyPI's latest"
    r"|as of \d{4}-\d{2}-\d{2}"
    r")",
    re.IGNORECASE,
)

MD_LINK_RE = re.compile(r"(?<!!)\[(?:[^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$", re.MULTILINE)

# Skip link targets we cannot or should not resolve.
SKIP_LINK_PREFIXES = ("http://", "https://", "mailto:", "#", "<", "$", "{")


@dataclass
class Finding:
    path: str
    line: int
    code: str
    message: str
    severity: str = "error"


@dataclass
class Report:
    errors: list[Finding] = field(default_factory=list)
    warnings: list[Finding] = field(default_factory=list)

    def add(self, f: Finding) -> None:
        (self.errors if f.severity == "error" else self.warnings).append(f)


def rel(p: Path) -> str:
    try:
        return str(p.relative_to(REPO)).replace("\\", "/")
    except ValueError:
        return str(p)


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


def normalise(text: str) -> str:
    """Fold case, strip accents and collapse punctuation so hashing is stable."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower()
    text = re.sub(r"[^a-z0-9@.\\/_-]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def digest(term: str) -> str:
    return hashlib.sha256(normalise(term).encode("utf-8")).hexdigest()


def load_hashes() -> dict[str, str]:
    """Return {hash: label}. Labels describe the class of term, never the term."""
    out: dict[str, str] = {}
    if not DENYLIST_HASHES.exists():
        return out
    for raw in read(DENYLIST_HASHES).splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 1)
        out[parts[0].lower()] = parts[1] if len(parts) > 1 else "denylisted term"
    return out


def load_patterns() -> list[tuple[re.Pattern[str], str, list[str]]]:
    """Return (regex, label, allow_globs).

    Fields are tab separated: ``pattern <TAB> label [<TAB> allow-glob,allow-glob]``.
    A path matching an allow glob is exempt from that one pattern, which is how the
    files that legitimately name a per-machine memory location stay clean.
    """
    out: list[tuple[re.Pattern[str], str, list[str]]] = []
    if not DENYLIST_PATTERNS.exists():
        return out
    for raw in read(DENYLIST_PATTERNS).splitlines():
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = [p.strip() for p in line.split("\t") if p.strip()]
        if not parts:
            continue
        pat = parts[0]
        label = parts[1] if len(parts) > 1 else pat
        allow = [g.strip() for g in parts[2].split(",")] if len(parts) > 2 else []
        try:
            out.append((re.compile(pat), label, allow))
        except re.error as exc:  # a bad pattern must not silently disable the check
            print(f"denylist-patterns.txt: bad regex {pat!r}: {exc}", file=sys.stderr)
            sys.exit(2)
    return out


def tracked_markdown(staged_only: bool) -> list[Path]:
    if staged_only:
        cmds = [["git", "-C", str(REPO), "diff", "--cached", "--name-only", "--diff-filter=ACMR"]]
    else:
        # Tracked files PLUS untracked-but-not-ignored ones. A brand new SKILL.md is exactly the
        # file most likely to be malformed, and `ls-files` alone silently skips it, so the check
        # passes locally and only fails in CI after the commit.
        cmds = [["git", "-C", str(REPO), "ls-files"],
                ["git", "-C", str(REPO), "ls-files", "--others", "--exclude-standard"]]
    out = ""
    try:
        for cmd in cmds:
            out += subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return sorted(REPO.glob("plugins/**/*.md"))
    files = []
    for name in out.splitlines():
        if not name.strip():
            continue
        p = REPO / name.strip()
        if p.suffix.lower() == ".md" and p.exists():
            files.append(p)
    return files


# --- job 1: dated claims -------------------------------------------------------------

def check_dated_claims(path: Path, text: str, max_age_days: int, today: str, rep: Report) -> None:
    y, m, d = (int(x) for x in today.split("-"))
    today_ord = _ordinal(y, m, d)
    lines = text.splitlines()
    for i, line in enumerate(lines, 1):
        match = VERIFIED_RE.search(line)
        if not match:
            continue
        groups = [g for g in match.groups() if g]
        stamp_ord = _ordinal(int(groups[0]), int(groups[1]), int(groups[2]))
        age = today_ord - stamp_ord
        # The claim's neighbourhood: the paragraph it sits in.
        block = "\n".join(lines[max(0, i - 6): i + 6])
        has_retest = bool(RETEST_RE.search(block))
        pins_version = bool(VERSION_CLAIM_RE.search(block))
        if pins_version and not has_retest:
            rep.add(Finding(
                rel(path), i, "VERSION_CLAIM_NO_RETEST",
                "a version-pinned claim carries no `Retest:` line naming the command that settles it",
            ))
        elif age > max_age_days:
            rep.add(Finding(
                rel(path), i, "STALE_VERIFIED_CLAIM",
                f"`Verified` stamp is {age} days old (limit {max_age_days}); re-run its Retest and re-stamp",
                severity="warning",
            ))


def _ordinal(y: int, m: int, d: int) -> int:
    """Days since epoch, without importing datetime (kept deterministic and offline)."""
    if m < 3:
        y -= 1
        m += 12
    return 365 * y + y // 4 - y // 100 + y // 400 + (153 * (m - 3) + 2) // 5 + d


# --- jobs 2 and 3: leakage -----------------------------------------------------------

def check_leakage(
    path: Path,
    text: str,
    patterns: list[tuple[re.Pattern[str], str, list[str]]],
    hashes: dict[str, str],
    rep: Report,
) -> None:
    where = rel(path)
    for i, line in enumerate(text.splitlines(), 1):
        for pat, label, allow in patterns:
            if any(PurePosixPath(where).match(g) for g in allow):
                continue
            if pat.search(line):
                rep.add(Finding(where, i, "MACHINE_PATH_LEAK", f"{label} must not ship in a plugin"))
        if hashes:
            words = normalise(line).split()
            for n in range(1, MAX_NGRAM + 1):
                for j in range(len(words) - n + 1):
                    h = hashlib.sha256(" ".join(words[j: j + n]).encode("utf-8")).hexdigest()
                    label = hashes.get(h)
                    if label:
                        rep.add(Finding(where, i, "PERSONAL_DATA", f"denylisted {label}"))


# --- job 4: cross references ---------------------------------------------------------

def slugify(heading: str) -> str:
    s = heading.strip().lower()
    s = re.sub(r"`([^`]*)`", r"\1", s)
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
    s = re.sub(r"[*_~]", "", s)
    s = re.sub(r"[^\w\s-]", "", s)
    return re.sub(r"\s+", "-", s).strip("-")


def anchors_of(text: str) -> set[str]:
    out: set[str] = set()
    seen: dict[str, int] = {}
    for _, heading in HEADING_RE.findall(text):
        base = slugify(heading)
        if not base:
            continue
        n = seen.get(base, 0)
        out.add(base if n == 0 else f"{base}-{n}")
        seen[base] = n + 1
    for name in re.findall(r"<a\s+(?:id|name)=[\"']([^\"']+)[\"']", text):
        out.add(name)
    return out


def check_links(path: Path, text: str, cache: dict[Path, set[str]], rep: Report) -> None:
    fence: str | None = None
    for i, line in enumerate(text.splitlines(), 1):
        stripped = line.lstrip()
        if fence is None:
            if stripped.startswith(("```", "~~~")):
                fence = stripped[:3]
            marker = None
        else:
            if stripped.startswith(fence):
                fence = None
            continue
        if line.startswith(("    ", "	")) and not stripped.startswith(("-", "*", "+", "|", ">")):
            continue  # indented code block
        for target in MD_LINK_RE.findall(line):
            if target.startswith(SKIP_LINK_PREFIXES) or "${" in target:
                continue
            file_part, _, anchor = target.partition("#")
            if not file_part:
                continue
            dest = (path.parent / file_part).resolve()
            if not dest.exists():
                rep.add(Finding(rel(path), i, "DEAD_LINK", f"link target does not exist: {target}"))
                continue
            if anchor and dest.suffix.lower() == ".md":
                if dest not in cache:
                    cache[dest] = anchors_of(read(dest))
                if slugify(anchor) not in cache[dest]:
                    rep.add(Finding(
                        rel(path), i, "DEAD_ANCHOR",
                        f"no such heading in {file_part or dest.name}: #{anchor}",
                    ))


# --- job 5: SKILL.md frontmatter ---------------------------------------------------

FM_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):(.*)$")


def check_frontmatter(path: Path, text: str, rep: Report) -> None:
    """Catch the frontmatter breakages that make a skill load with no metadata.

    Full YAML parsing is validate-plugins.sh's job. This catches the one failure that
    keeps recurring: recasting a dash into a colon inside an unquoted scalar.
    """
    if path.name != "SKILL.md":
        return
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        rep.add(Finding(rel(path), 1, "NO_FRONTMATTER", "SKILL.md does not open with a `---` fence"))
        return
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        rep.add(Finding(rel(path), 1, "UNTERMINATED_FRONTMATTER", "no closing `---` fence"))
        return

    key = None
    start = 0
    buf: list[str] = []

    def flush() -> None:
        if key is None:
            return
        value = " ".join(buf).strip()
        if not value or value[0] in "\"'|>[{&*!":
            return  # quoted, block or flow scalar: a colon inside is legal
        if ": " in value or value.endswith(":"):
            rep.add(Finding(
                rel(path), start + 1, "FRONTMATTER_UNQUOTED_COLON",
                f"`{key}:` is an unquoted scalar containing \": \", which fails YAML parsing; "
                f"the skill would load with every frontmatter field dropped. Recast the colon or "
                f"quote the value",
            ))

    for i in range(1, end):
        line = lines[i]
        m = FM_KEY_RE.match(line)
        if m and not line.startswith((" ", "	", "-")):
            flush()
            key, rest = m.group(1), m.group(2)
            start = i
            buf = [rest]
        elif key is not None:
            buf.append(line)
    flush()


# --- boundary-rule drift -------------------------------------------------------------

def extract_sentinel(text: str) -> str | None:
    start = text.find(SENTINEL_BEGIN)
    end = text.find(SENTINEL_END)
    if start == -1 or end == -1 or end < start:
        return None
    return text[start + len(SENTINEL_BEGIN): end].strip()


def check_boundary_rule(rep: Report) -> None:
    if not LEARNINGS.exists():
        return
    canonical = extract_sentinel(read(LEARNINGS))
    if canonical is None:
        rep.add(Finding(rel(LEARNINGS), 1, "NO_BOUNDARY_SENTINEL",
                        f"LEARNINGS.md carries no {SENTINEL_BEGIN} block"))
        return
    for f in SENTINEL_FILES:
        if not f.exists():
            continue
        copy = extract_sentinel(read(f))
        if copy is None:
            rep.add(Finding(rel(f), 1, "MISSING_BOUNDARY_RULE",
                            "SKILL.md carries no boundary-rule block"))
        elif copy != canonical:
            rep.add(Finding(rel(f), 1, "BOUNDARY_RULE_DRIFT",
                            "boundary-rule block differs from LEARNINGS.md"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--staged", action="store_true", help="check only files staged for commit")
    ap.add_argument("--max-age-days", type=int, default=180, help="age at which a Verified stamp is reported")
    ap.add_argument("--today", default="2026-09-07", help="reference date, YYYY-MM-DD")
    ap.add_argument("--json", action="store_true", help="emit findings as JSON")
    ap.add_argument("--no-links", action="store_true", help="skip the cross-reference job")
    args = ap.parse_args()

    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.today):
        print("--today must be YYYY-MM-DD", file=sys.stderr)
        return 2

    rep = Report()
    patterns = load_patterns()
    hashes = load_hashes()
    anchor_cache: dict[Path, set[str]] = {}

    files = tracked_markdown(args.staged)
    for path in files:
        text = read(path)
        check_dated_claims(path, text, args.max_age_days, args.today, rep)
        check_leakage(path, text, patterns, hashes, rep)
        check_frontmatter(path, text, rep)
        if not args.no_links and rel(path).startswith("plugins/"):
            check_links(path, text, anchor_cache, rep)
    check_boundary_rule(rep)

    if args.json:
        print(json.dumps({
            "scanned": len(files),
            "errors": [f.__dict__ for f in rep.errors],
            "warnings": [f.__dict__ for f in rep.warnings],
        }, indent=2))
    else:
        for f in rep.warnings:
            print(f"warning: {f.path}:{f.line}: [{f.code}] {f.message}")
        for f in rep.errors:
            print(f"ERROR:   {f.path}:{f.line}: [{f.code}] {f.message}")
        print(f"\nscanned {len(files)} markdown files: "
              f"{len(rep.errors)} errors, {len(rep.warnings)} warnings")

    return 1 if rep.errors else 0


if __name__ == "__main__":
    sys.exit(main())
