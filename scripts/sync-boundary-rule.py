#!/usr/bin/env python3
"""Copy the boundary rule from LEARNINGS.md into the SKILL.md files that carry it.

Three skills instruct an agent to record what it learns. Each needs the routing rule inline,
because ``${CLAUDE_PLUGIN_ROOT}`` scopes a plugin to its own directory: a link to a repo-root
policy file does not resolve from an installed plugin. Three copies is therefore the correct
design, and this script is what stops them drifting.

LEARNINGS.md is the source. Run this after editing it.

    python scripts/sync-boundary-rule.py           # write the copies
    python scripts/sync-boundary-rule.py --check   # exit 1 if any copy is stale

``scripts/check-skill-hygiene.py`` enforces the same invariant.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LEARNINGS = REPO / "LEARNINGS.md"
BEGIN = "<!-- boundary-rule:begin -->"
END = "<!-- boundary-rule:end -->"

TARGETS = [
    REPO / "plugins/fabric-cli/skills/fabric-cli/SKILL.md",
    REPO / "plugins/pbi-desktop/skills/connect-pbid/SKILL.md",
    REPO / "plugins/reports/skills/pbir-cli/SKILL.md",
]


def extract(text: str, path: Path) -> str:
    start = text.find(BEGIN)
    end = text.find(END)
    if start == -1 or end == -1 or end < start:
        raise SystemExit(f"{path}: no {BEGIN} ... {END} block")
    return text[start + len(BEGIN): end].strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="report drift, write nothing")
    args = ap.parse_args()

    canonical = extract(LEARNINGS.read_text(encoding="utf-8"), LEARNINGS)
    block = f"{BEGIN}\n{canonical}\n{END}"

    stale = 0
    for target in TARGETS:
        if not target.exists():
            print(f"missing: {target}", file=sys.stderr)
            stale += 1
            continue
        text = target.read_text(encoding="utf-8")
        start, end = text.find(BEGIN), text.find(END)
        if start == -1 or end == -1:
            print(f"no boundary-rule block: {target.relative_to(REPO)}", file=sys.stderr)
            stale += 1
            continue
        current = text[start: end + len(END)]
        if current == block:
            continue
        stale += 1
        rel = target.relative_to(REPO)
        if args.check:
            print(f"stale: {rel}")
        else:
            target.write_text(text[:start] + block + text[end + len(END):], encoding="utf-8")
            print(f"synced: {rel}")

    if args.check:
        print(f"{len(TARGETS)} targets, {stale} stale")
        return 1 if stale else 0
    print(f"{len(TARGETS)} targets in sync")
    return 0


if __name__ == "__main__":
    sys.exit(main())
