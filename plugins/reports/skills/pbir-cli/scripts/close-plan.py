#!/usr/bin/env python3
"""Report-surface sweep: find the deliverable axes nobody decided.

A PBIR report has more surfaces than a page artboard covers. Tooltips, navigation,
data labels, axis titles and alt text are report-level chrome that no mockup shows,
so they get retro-fitted onto a locked design instead of decided while it is open.

This script sweeps a finished ``.Report`` and prints one row per (page, visual) with
the state of each axis. A cell reading ``not decided`` means the PBIR carries no
opinion at all: not "off", not "default", simply nothing written. That is the
category the sweep exists to surface, because "off" is a decision and silence is not.

**Where the axes come from.** They are the object namespaces the PBIR schema
supports, filtered to the ones that carry a deliverable decision (see ``AXES``), not
a hand-written list of what went wrong on the last project. A checklist of last
project's misses only ever catches last project's misses. Run with ``--all-axes`` to
also list every supported container namespace a visual leaves untouched.

Usage::

    python close-plan.py "Sales.Report"
    python close-plan.py "Sales.Report" --enforce         # exit 1 if anything is undecided
    python close-plan.py "Sales.Report" --axis tooltip --axis altText
    python close-plan.py "Sales.Report" --json

Advisory by default, so it can run on every build without blocking a legitimate ship.
Pass ``--enforce`` in a plan ticket's ``Exit:`` line, where the gate belongs: a gate
wired into 22 tickets runs 22 times, and a gate that blocks at 11pm gets deleted.

Exit codes: 0 clean (or advisory), 1 undecided axes found under ``--enforce``,
2 bad invocation.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

class BadInvocation(Exception):
    """Raised for a path that is not a PBIR report. Exits 2, not 1."""


UNDECIDED = "not decided"
NA = "--"

DENEB_TYPES = (
    "deneb7E15AEF80B9E4D4F8E12924291ECE89A",
    "STANDALONEdeneb7E15AEF80B9E4D4F8E12924291ECE89A",
    "ALPHAdeneb7E15AEF80B9E4D4F8E12924291ECE89A",
    "BETAdeneb7E15AEF80B9E4D4F8E12924291ECE89A",
)

# Visual types that emit no query, so tooltip / label / axis axes do not apply.
NON_DATA_TYPES = {
    "textbox", "shape", "image", "actionButton", "basicShape",
    "pageNavigator", "bookmarkNavigator", "filterSlicer",
}

# Carries no information of its own, or carries it as readable text, so alt text does not apply.
# An `image` is not in here: an undescribed image is the single most common accessibility gap.
NO_ALT_TYPES = {
    "shape", "basicShape", "actionButton", "pageNavigator", "bookmarkNavigator", "textbox",
}

# Draws its own words, so the container title is not a decision anyone owes an answer for.
NO_TITLE_TYPES = {
    "textbox", "shape", "basicShape", "image", "actionButton",
    "pageNavigator", "bookmarkNavigator",
}

# Visual types with a cartesian axis pair, so the axis-title axis applies.
CARTESIAN_TYPES = {
    "barChart", "clusteredBarChart", "hundredPercentStackedBarChart",
    "columnChart", "clusteredColumnChart", "hundredPercentStackedColumnChart",
    "lineChart", "areaChart", "stackedAreaChart", "lineClusteredColumnComboChart",
    "lineStackedColumnComboChart", "scatterChart", "waterfallChart", "ribbonChart",
}

# Visual types that can print data labels.
LABEL_TYPES = CARTESIAN_TYPES | {
    "pieChart", "donutChart", "treemap", "funnel", "gauge",
}

# Every container namespace the PBIR visualContainerObjects schema supports.
# The generative set that AXES is filtered out of; --all-axes reports the rest.
CONTAINER_NAMESPACES = [
    "title", "subTitle", "background", "border", "dropShadow", "padding",
    "spacing", "divider", "visualHeader", "visualHeaderTooltip",
    "visualTooltip", "visualLink", "lockAspect", "general",
]

# Axes a deliverable has to have an answer for, including the answer "none".
AXES = ["tooltip", "nav", "title", "labels", "axis", "altText"]


# ---------------------------------------------------------------- PBIR reading


def literal(node):
    """Unwrap a PBIR ``{"expr": {"Literal": {"Value": "..."}}}`` to a Python value."""
    if not isinstance(node, dict):
        return None
    value = node.get("expr", {}).get("Literal", {}).get("Value")
    if not isinstance(value, str):
        return None
    if value.startswith("'") and value.endswith("'") and len(value) >= 2:
        return value[1:-1]
    if value in ("true", "false"):
        return value == "true"
    return value


def prop(container, namespace, name):
    """First value of ``<container>[namespace][0].properties[name]``, or None."""
    entries = (container or {}).get(namespace)
    if not isinstance(entries, list) or not entries:
        return None
    return literal(entries[0].get("properties", {}).get(name))


def has_namespace(container, namespace):
    entries = (container or {}).get(namespace)
    return isinstance(entries, list) and len(entries) > 0


def all_literals(node, out=None):
    """Every literal string anywhere under a node. Used to find nav targets
    without depending on which property name the action uses."""
    if out is None:
        out = []
    if isinstance(node, dict):
        value = literal(node)
        if isinstance(value, str):
            out.append(value)
        for v in node.values():
            all_literals(v, out)
    elif isinstance(node, list):
        for v in node:
            all_literals(v, out)
    return out


def resolve_report(raw: str) -> Path:
    """Accept a .Report folder, a definition.pbir, a .pbip, or a project folder."""
    p = Path(raw).expanduser().resolve()
    if p.is_file():
        if p.suffix == ".pbip":
            p = p.parent
        elif p.name == "definition.pbir":
            return p.parent
    if p.is_dir():
        if (p / "definition" / "pages" / "pages.json").exists():
            return p
        candidates = sorted(
            c for c in p.glob("*.Report")
            if (c / "definition" / "pages" / "pages.json").exists()
        )
        if len(candidates) == 1:
            return candidates[0]
        if len(candidates) > 1:
            raise BadInvocation(
                f"{p} holds {len(candidates)} reports; name one:\n  "
                + "\n  ".join(c.name for c in candidates)
            )
    raise BadInvocation(f"Not a PBIR report (no definition/pages/pages.json): {raw}")


# ------------------------------------------------------------------ the model


@dataclass
class Visual:
    page_name: str
    name: str
    visual_type: str
    cells: dict = field(default_factory=dict)
    untouched: list = field(default_factory=list)


@dataclass
class Page:
    name: str
    display: str
    page_type: str
    visibility: str
    display_option: str
    width: int
    height: int
    visuals: list = field(default_factory=list)
    reachable_from: list = field(default_factory=list)
    raised_by: list = field(default_factory=list)


def stem(folder: Path) -> str:
    """Folder names carry a `.Page` / `.Visual` suffix in some writers and not others."""
    return folder.name.rsplit(".", 1)[0] if folder.name.endswith((".Page", ".Visual")) else folder.name


def load_pages(report: Path) -> list:
    pages_dir = report / "definition" / "pages"
    meta = json.loads((pages_dir / "pages.json").read_text(encoding="utf-8"))
    order = meta.get("pageOrder", [])

    pages = {}
    for page_json in sorted(pages_dir.glob("*/page.json")):
        d = json.loads(page_json.read_text(encoding="utf-8"))
        page = Page(
            name=d.get("name", stem(page_json.parent)),
            display=d.get("displayName", d.get("name", "")),
            page_type=d.get("type", "Page"),
            visibility=d.get("visibility", "AlwaysVisible"),
            display_option=d.get("displayOption", ""),
            width=d.get("width", 0),
            height=d.get("height", 0),
        )
        for visual_json in sorted(page_json.parent.glob("visuals/*/visual.json")):
            v = json.loads(visual_json.read_text(encoding="utf-8"))
            if "visualGroup" in v:          # a group is chrome, not a deliverable
                continue
            inner = v.get("visual", {})
            page.visuals.append(
                Visual(
                    page_name=page.name,
                    name=v.get("name", stem(visual_json.parent)),
                    visual_type=inner.get("visualType", "?"),
                )
            )
            page.visuals[-1]._raw = inner   # noqa: SLF001 - local carrier
        pages[page.name] = page

    ordered = [pages[n] for n in order if n in pages]
    ordered += [p for n, p in sorted(pages.items()) if n not in order]
    return ordered


def wire_graph(pages: list) -> bool:
    """Fill in reachable_from (navigation) and raised_by (tooltip) on each page.

    Returns whether the report navigates itself at all. A report with no navigation
    affordance anywhere navigates by the page tab strip, which is a legitimate choice
    and not 105 identical defects. Reachability is only a finding once the author has
    committed to in-canvas navigation and then left a page off it.
    """
    by_name = {p.name: p for p in pages}
    by_display = {p.display: p for p in pages}
    navigator_present = False
    link_present = False

    for page in pages:
        for visual in page.visuals:
            inner = visual._raw                       # noqa: SLF001
            vco = inner.get("visualContainerObjects", {})

            if inner.get("visualType") in ("pageNavigator", "bookmarkNavigator"):
                navigator_present = True

            # Navigation: read every literal under visualLink and match it against
            # a page name or display name. Which property carries the target has
            # changed between schema versions; the value has not.
            if has_namespace(vco, "visualLink"):
                link_present = True
                for value in all_literals(vco["visualLink"]):
                    target = by_name.get(value) or by_display.get(value)
                    if target is not None and target is not page:
                        target.reachable_from.append(f"{page.display}/{visual.name}")

            # Tooltip: a canvas tooltip names its page in visualTooltip.section.
            if prop(vco, "visualTooltip", "type") == "Canvas":
                section = prop(vco, "visualTooltip", "section")
                target = by_name.get(section) or by_display.get(section)
                if target is not None:
                    target.raised_by.append(f"{page.display}/{visual.name}")

    if navigator_present:
        for page in pages:
            if page.page_type == "Page" and page.visibility != "HiddenInViewMode":
                page.reachable_from.append("pageNavigator")

    return navigator_present or link_present


def assess(page: Page, visual: Visual, in_canvas_nav: bool) -> None:
    inner = visual._raw                               # noqa: SLF001
    vtype = visual.visual_type
    vco = inner.get("visualContainerObjects", {})
    objects = inner.get("objects", {})
    is_deneb = vtype in DENEB_TYPES
    is_data = vtype not in NON_DATA_TYPES

    # --- tooltip -----------------------------------------------------------
    if not is_data:
        tooltip = NA
    elif not has_namespace(vco, "visualTooltip"):
        tooltip = UNDECIDED
    else:
        show = prop(vco, "visualTooltip", "show")
        ttype = prop(vco, "visualTooltip", "type")
        if show is False:
            tooltip = "off"
        elif ttype == "Canvas":
            tooltip = f"canvas:{prop(vco, 'visualTooltip', 'section') or '?'}"
        elif ttype == "Default" or ttype is None:
            tooltip = "default"
        else:
            # Anything else is accepted as a string and then silently ignored.
            tooltip = f"INVALID type={ttype!r}"
    if is_deneb and tooltip not in (NA, UNDECIDED):
        enabled = prop(objects, "vega", "enableTooltips")
        wants_tooltip = tooltip != "off"
        if enabled is None:
            tooltip += " (vega.enableTooltips not decided)"
        elif bool(enabled) != wants_tooltip:
            tooltip += f" (MISMATCH vega.enableTooltips={enabled})"

    # --- navigation (page level, reported on every row for grep-ability) ----
    if page.page_type == "Tooltip":
        nav = "tooltip-page"
    elif page.reachable_from:
        nav = f"{len(page.reachable_from)} route(s)"
    elif page.visibility == "HiddenInViewMode":
        nav = "hidden, no route"
    elif in_canvas_nav:
        nav = "UNREACHABLE"
    else:
        nav = "tab strip"

    # --- title -------------------------------------------------------------
    if vtype in NO_TITLE_TYPES:
        title = NA
    elif not has_namespace(vco, "title"):
        title = UNDECIDED
    elif prop(vco, "title", "show") is False:
        title = "off"
    elif prop(vco, "title", "text"):
        title = "explicit"
    else:
        title = "auto"

    # --- data labels -------------------------------------------------------
    if vtype not in LABEL_TYPES:
        labels = NA
    elif not has_namespace(objects, "labels"):
        labels = UNDECIDED
    else:
        labels = "off" if prop(objects, "labels", "show") is False else "on"

    # --- axis titles -------------------------------------------------------
    if vtype not in CARTESIAN_TYPES:
        axis = NA
    elif not (has_namespace(objects, "categoryAxis") or has_namespace(objects, "valueAxis")):
        axis = UNDECIDED
    else:
        titled = []
        for ns, label in (("categoryAxis", "cat"), ("valueAxis", "val")):
            if not has_namespace(objects, ns):
                continue
            if prop(objects, ns, "showAxisTitle") is False:
                titled.append(f"{label}:off")
            elif prop(objects, ns, "titleText"):
                titled.append(f"{label}:set")
            else:
                titled.append(f"{label}:auto")
        axis = ",".join(titled) or UNDECIDED

    # --- alt text ----------------------------------------------------------
    if vtype in NO_ALT_TYPES:
        alt = NA
    elif prop(vco, "general", "altText"):
        alt = "set"
    else:
        alt = UNDECIDED

    visual.cells = {
        "tooltip": tooltip, "nav": nav, "title": title,
        "labels": labels, "axis": axis, "altText": alt,
    }
    visual.untouched = [ns for ns in CONTAINER_NAMESPACES if not has_namespace(vco, ns)]


def page_problems(page: Page, in_canvas_nav: bool = True) -> list:
    out = []
    if page.page_type == "Tooltip":
        if not page.raised_by:
            out.append("tooltip page raised by nothing")
        if page.display_option != "ActualSize":
            out.append(f"tooltip page displayOption={page.display_option or 'unset'}, want ActualSize")
    elif page.visibility == "HiddenInViewMode" and not page.reachable_from:
        out.append("hidden page, and nothing navigates to it")
    elif in_canvas_nav and not page.reachable_from:
        out.append("the report navigates in-canvas, but nothing targets this page")
    return out


# --------------------------------------------------------------------- output


def render(pages: list, axes: list, show_all: bool, all_axes: bool, in_canvas_nav: bool) -> int:
    rows = []
    for page in pages:
        for visual in page.visuals:
            cells = [visual.cells[a] for a in axes]
            if show_all or any(c == UNDECIDED or "MISMATCH" in c or "INVALID" in c or c == "UNREACHABLE" for c in cells):
                rows.append((page.display, visual.name, visual.visual_type, cells))

    headers = ["page", "visual", "type"] + axes
    table = [headers] + [[r[0], r[1], r[2]] + r[3] for r in rows]
    widths = [max(len(str(row[i])) for row in table) for i in range(len(headers))]
    print()
    for i, row in enumerate(table):
        print("  ".join(str(c).ljust(w) for c, w in zip(row, widths)).rstrip())
        if i == 0:
            print("  ".join("-" * w for w in widths))
    if not rows:
        print("  (every axis decided)")

    undecided = sum(1 for r in rows for c in r[3] if c == UNDECIDED)
    broken = sum(1 for r in rows for c in r[3] if "MISMATCH" in c or "INVALID" in c or c == "UNREACHABLE")

    problems = [(p, page_problems(p, in_canvas_nav)) for p in pages]
    problems = [(p, m) for p, m in problems if m]
    if problems:
        print("\nPage-level:")
        for page, messages in problems:
            for message in messages:
                print(f"  {page.display}: {message}")

    if all_axes:
        print("\nContainer namespaces left untouched (--all-axes):")
        for page in pages:
            for visual in page.visuals:
                if visual.untouched:
                    print(f"  {page.display}/{visual.name}: {', '.join(visual.untouched)}")

    total = sum(len(p.visuals) for p in pages)
    print(
        f"\n{len(pages)} page(s), {total} visual(s). "
        f"{undecided} undecided cell(s), {broken} broken cell(s), "
        f"{len(problems)} page-level issue(s)."
    )
    return undecided + broken + len(problems)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Sweep a PBIR report for deliverable axes nobody decided.",
    )
    ap.add_argument("report", help="path to a .Report folder, .pbip, or project folder")
    ap.add_argument("--axis", action="append", choices=AXES, metavar="AXIS",
                    help=f"restrict to one axis (repeatable); default all of: {', '.join(AXES)}")
    ap.add_argument("--all", action="store_true", dest="show_all",
                    help="print every visual, not just the ones with an undecided axis")
    ap.add_argument("--all-axes", action="store_true",
                    help="also list every container namespace each visual leaves untouched")
    ap.add_argument("--enforce", action="store_true",
                    help="exit 1 when anything is undecided or broken (default is advisory)")
    ap.add_argument("--json", action="store_true", dest="as_json",
                    help="emit machine-readable JSON instead of a table")
    args = ap.parse_args(argv)

    report = resolve_report(args.report)
    pages = load_pages(report)
    in_canvas_nav = wire_graph(pages)
    for page in pages:
        for visual in page.visuals:
            assess(page, visual, in_canvas_nav)

    axes = args.axis or AXES

    if args.as_json:
        payload = {
            "report": str(report),
            "axes": axes,
            "inCanvasNavigation": in_canvas_nav,
            "pages": [
                {
                    "name": p.name, "displayName": p.display, "type": p.page_type,
                    "visibility": p.visibility, "reachableFrom": p.reachable_from,
                    "raisedBy": p.raised_by, "problems": page_problems(p, in_canvas_nav),
                    "visuals": [
                        {"name": v.name, "visualType": v.visual_type,
                         "axes": {a: v.cells[a] for a in axes},
                         "untouchedNamespaces": v.untouched}
                        for v in p.visuals
                    ],
                }
                for p in pages
            ],
        }
        print(json.dumps(payload, indent=2))
        findings = sum(
            1 for p in pages for v in p.visuals for a in axes
            if v.cells[a] == UNDECIDED or "MISMATCH" in v.cells[a] or "INVALID" in v.cells[a]
        ) + sum(len(page_problems(p, in_canvas_nav)) for p in pages)
    else:
        print(f"close-plan: {report}")
        if not in_canvas_nav:
            print("  (no in-canvas navigation: this report navigates by the page tab strip)")
        findings = render(pages, axes, args.show_all, args.all_axes, in_canvas_nav)

    if findings and args.enforce:
        return 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:                            # noqa: BLE001
        print(f"close-plan: {exc}", file=sys.stderr)
        sys.exit(2)
