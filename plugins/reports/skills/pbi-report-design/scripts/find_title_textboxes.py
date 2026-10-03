#!/usr/bin/env python3
"""Find textboxes that act as one visual's title.

A visual's title and subtitle belong in its own container `title` and `subTitle` slots
(references/page-titles.md). This script reads a PBIR report from disk and lists every textbox
that is standing in for one:

- it ends at most MAX_GAP px above a single data visual and spans at least half that visual's
  width, or
- it overlaps that visual's top edge, including a textbox laid over the top inside the visual.

A textbox that sits over two or more data visuals is a section header and is not flagged. A data
visual is one with a query (charts, tables, cards, slicers, custom visuals); shapes, images,
buttons and other textboxes are not. Hidden visuals are skipped. Positions inside a visual group
are resolved to page coordinates before comparing.

A candidate that is the highest textbox on its page, with no other textbox level with it, is most
likely the page title sitting over the page's one main visual. It is still listed, marked as such,
but does not set the exit code.

Usage:
    python find_title_textboxes.py "Sales.Report"
    python find_title_textboxes.py "Sales.Report" --json
    python find_title_textboxes.py "Sales.Report" --max-gap 32

Exit codes: 0 none found (or only likely page titles), 1 candidates found, 2 bad invocation.
Read-only: it never edits the report.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

MAX_GAP = 24  # px between the textbox's bottom and the visual's top
MIN_SPAN = 0.5  # share of the visual's width the textbox must cover
TOP_BAND = 48  # px inside the visual's top edge that count as "laid over the top"
OVERLAPS = "overlaps its top edge"


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8-sig") as f:
        return json.load(f)


def literal_text(prop: dict | None) -> str:
    """Text of a `{"expr": {"Literal": {"Value": "'...'"}}}` property, unquoted."""
    try:
        value = prop["expr"]["Literal"]["Value"]
    except (KeyError, TypeError):
        return ""
    if len(value) >= 2 and value[0] == "'" and value[-1] == "'":
        value = value[1:-1].replace("''", "'")
    return value


def textbox_text(visual: dict) -> str:
    try:
        paragraphs = visual["objects"]["general"][0]["properties"]["paragraphs"]
    except (KeyError, IndexError, TypeError):
        return ""
    if isinstance(paragraphs, dict):  # older {"expr": {"Literal": {"Value": "[...]"}}} form
        try:
            paragraphs = json.loads(paragraphs["expr"]["Literal"]["Value"])
        except (KeyError, TypeError, ValueError):
            return ""
    lines = []
    for paragraph in paragraphs or []:
        runs = paragraph.get("textRuns", []) if isinstance(paragraph, dict) else []
        lines.append("".join(str(run.get("value", "")) for run in runs))
    return " / ".join(line for line in lines if line)


def visual_title(visual: dict) -> str:
    try:
        props = visual["visualContainerObjects"]["title"][0]["properties"]
    except (KeyError, IndexError, TypeError):
        return ""
    return literal_text(props.get("text"))


def is_data_visual(visual: dict) -> bool:
    query_state = (visual.get("query") or {}).get("queryState") or {}
    return any((role or {}).get("projections") for role in query_state.values())


def read_page(page_dir: Path) -> tuple[str, list[dict]]:
    page_json = page_dir / "page.json"
    display_name = load_json(page_json).get("displayName", page_dir.name) if page_json.exists() else page_dir.name

    containers = {}
    for visual_json in sorted(page_dir.glob("visuals/*/visual.json")):
        try:
            data = load_json(visual_json)
        except (OSError, ValueError) as exc:
            print(f"warning: skipped {visual_json}: {exc}", file=sys.stderr)
            continue
        containers[data.get("name", visual_json.parent.name)] = data

    def absolute(name: str, seen: frozenset = frozenset()) -> tuple[float, float]:
        data = containers.get(name) or {}
        pos = data.get("position") or {}
        x, y = float(pos.get("x", 0)), float(pos.get("y", 0))
        parent = data.get("parentGroupName")
        if parent and parent in containers and parent not in seen:
            px, py = absolute(parent, seen | {name})
            x, y = x + px, y + py
        return x, y

    def hidden(name: str, seen: frozenset = frozenset()) -> bool:
        data = containers.get(name) or {}
        if data.get("isHidden"):
            return True
        parent = data.get("parentGroupName")
        return bool(parent and parent in containers and parent not in seen and hidden(parent, seen | {name}))

    items = []
    for name, data in containers.items():
        visual = data.get("visual")
        if not visual or hidden(name):  # a visualGroup has no `visual` key
            continue
        pos = data.get("position") or {}
        x, y = absolute(name)
        items.append({
            "name": name,
            "type": visual.get("visualType", ""),
            "x": x,
            "y": y,
            "w": float(pos.get("width", 0)),
            "h": float(pos.get("height", 0)),
            "visual": visual,
        })
    return display_name, items


def find_on_page(items: list[dict], max_gap: float) -> list[dict]:
    textboxes = [i for i in items if i["type"] == "textbox"]
    data_visuals = [i for i in items if i["type"] != "textbox" and is_data_visual(i["visual"])]
    # The page title is the highest textbox on the page, when no other textbox shares its top.
    # Several textboxes level at the top are a row of visual titles, not a page title.
    top = min((t["y"] for t in textboxes), default=0)
    top_textboxes = [t["name"] for t in textboxes if t["y"] <= top + 1]
    page_title = top_textboxes[0] if len(top_textboxes) == 1 else None
    findings = []
    for tb in textboxes:
        tb_bottom = tb["y"] + tb["h"]
        matches = []
        for v in data_visuals:
            if v["w"] <= 0:
                continue
            span = min(tb["x"] + tb["w"], v["x"] + v["w"]) - max(tb["x"], v["x"])
            if span < MIN_SPAN * v["w"]:
                continue
            gap = v["y"] - tb_bottom
            if 0 <= gap <= max_gap:
                matches.append((v, f"ends {gap:g}px above it"))
            elif tb_bottom > v["y"] and tb["y"] < v["y"] + min(TOP_BAND, v["h"] / 2):
                matches.append((v, OVERLAPS))
        if len(matches) == 1:
            v, relation = matches[0]
            findings.append({
                "textbox": tb["name"],
                "text": textbox_text(tb["visual"]),
                "visual": v["name"],
                "visualType": v["type"],
                "visualTitle": visual_title(v["visual"]),
                "relation": relation,
                # A page title never sits over a visual, so an overlap always counts.
                "likelyPageTitle": tb["name"] == page_title and relation != OVERLAPS,
            })
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Find textboxes that act as one visual's title.")
    parser.add_argument("report", help='the "<Name>.Report" folder (or its definition folder)')
    parser.add_argument("--json", action="store_true", help="print findings as JSON")
    parser.add_argument("--max-gap", type=float, default=MAX_GAP,
                        help=f"largest gap in px between textbox and visual (default {MAX_GAP})")
    args = parser.parse_args()

    root = Path(args.report)
    pages_dir = next((p for p in (root / "definition" / "pages", root / "pages") if p.is_dir()), None)
    if pages_dir is None:
        print(f"error: no definition/pages folder under {root}", file=sys.stderr)
        return 2

    results = []
    for page_dir in sorted(p for p in pages_dir.iterdir() if p.is_dir()):
        page_name, items = read_page(page_dir)
        for finding in find_on_page(items, args.max_gap):
            results.append({"page": page_name, **finding})

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    elif not results:
        print("No textbox acts as a single visual's title.")
    else:
        for r in results:
            target = f'{r["visualType"]} {r["visual"]}'
            if r["visualTitle"]:
                target += f' (title "{r["visualTitle"]}")'
            text = r["text"] if len(r["text"]) <= 70 else r["text"][:67] + "..."
            note = " [highest textbox on the page: likely the page title]" if r["likelyPageTitle"] else ""
            print(f'{r["page"]}: textbox {r["textbox"]} "{text}" {r["relation"]}: {target}{note}')
        print(f"\n{len(results)} candidate(s). Move each text into that visual's title/subTitle "
              "and delete the textbox; keep a page title or a section header.")
    return 1 if any(not r["likelyPageTitle"] for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
