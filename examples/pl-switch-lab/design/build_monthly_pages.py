"""Build the two Monthly P&L pages -- the lab reproduction of the field case in
docs/performance/05-case-unrenderable-matrix.md.

  Monthly P&L - Calc Group   a pivotTable: 'Period View' (15 items) on Columns x 28 measures
                             on Values, values-on-rows. 420 dispatched cell evaluations,
                             315 of them re-evaluating their measure through a
                             self-referencing format string.
  Monthly P&L - Deneb        the same 28 x 15 grid, from one query returning 12 rows x 10
                             base measures. Everything else derived in the Vega spec.

Both pages are cloned from an existing top-strip page so the design is identical by
construction: SVG background, logo, KEY SELECTIONS label, button slicers, footnote, and the
white/light-blue title styling.

The rail is the SAME FOUR SLICERS as every other page -- Year / Month / Channel / Category.
Keeping MONTH here is deliberate, and it does something different on each of the two pages,
which is the whole point:

  on the calc-group page  it filters DimDate, so the matrix re-plans and re-runs its
                          dispatched cells. Clicking a month is visibly, painfully slow --
                          that IS the demonstration.
  on the Deneb page       it filters the dataset query to the selected months, so the grid
                          redraws with just those columns, instantly.

Only the YEAR selection is cloned from the template; Month, Channel and Category open with
nothing selected so the pages show the whole business.

Idempotent: uuid5-seeded ids everywhere, so a re-run overwrites the same pages rather than
adding new ones.

Desktop may stay OPEN: after writing, this clicks "Apply external changes" for you. What is
NOT safe is leaving the two copies diverged -- Desktop writes its stale in-memory copy back on
save, which is how a hand-made slicer change got silently reverted on 2026-08-28.
"""
import copy
import json
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / "PL Bridge Demo.Report" / "definition" / "pages"
DENEB_DIR = ROOT / "scripts" / "demo" / "deneb"
sys.path.insert(0, str(DENEB_DIR))
import gen_monthly_spec as G  # noqa: E402  -- the shared row / measure contract

TEMPLATE = "a7920d23ea7852528ab4"      # Odd Rows P&L - Deneb, the design reference
DENEB_TYPE = "deneb7E15AEF80B9E4D4F8E12924291ECE89A"
MEASURE_TABLE = "00_Measures"

CANVAS_X, CANVAS_W = 336, 1608
BODY_TOP = 132
# 820px between the gold rule and the card bottom. At 13pt the grid needs
# 34 + 28*25 = 734, so give it 740 and the notes take what is left. The Deneb grid then
# never scrolls; the pivotTable on the other page still will, because Desktop's own row
# height is not ours to set -- that is part of the point.
MAIN_H = 740
NOTE_Y, NOTE_H = BODY_TOP + MAIN_H + 16, 64
TITLE = dict(x=CANVAS_X, y=26, z=0, width=1500, height=89, tabOrder=2000)
WHITE, SUB = "#FFFFFF", "#B8D9F2"

PAGE_KEYS = ["calcgroup", "deneb"]


def sid(*parts):
    return uuid.uuid5(uuid.NAMESPACE_URL, "plbridge/monthly/" + "/".join(parts)).hex[:20]


APPLY_PS = r"""
# Desktop 26.08+ raises "This project's files were changed externally" with an
# [Apply external changes] button whenever an open PBIP is edited underneath it. Clicking it
# can raise a SECOND confirmation ("Overwrite your unsaved edits") whenever Desktop has
# unsaved canvas state -- and until that is confirmed, nothing is applied. Verified 2026-08-28
# on 2.157.879.0.
Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes
$AE = [System.Windows.Automation.AutomationElement]
$TS = [System.Windows.Automation.TreeScope]::Descendants
$p = Get-Process PBIDesktop -EA SilentlyContinue |
     Where-Object { $_.MainWindowTitle -match 'PL Bridge' } | Select-Object -First 1
if (-not $p) { 'closed'; exit 0 }
$root = $AE::FromHandle($p.MainWindowHandle)
$byName = { param($n) New-Object System.Windows.Automation.PropertyCondition($AE::NameProperty, $n) }

function Invoke-El($el) {
    try { $el.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke(); $true }
    catch { $false }
}

# 1. the banner button
$banner = $null
for ($i = 0; $i -lt 20; $i++) {
    $banner = $root.FindFirst($TS, (& $byName 'Apply external changes'))
    if ($banner) { break }
    Start-Sleep -Milliseconds 500
}
if (-not $banner) { 'no-banner'; exit 0 }
[void](Invoke-El $banner)

# 2. the confirmation, if Desktop had unsaved edits. Its button carries the SAME name, so
#    look for it inside the dialog rather than at the top level.
for ($i = 0; $i -lt 10; $i++) {
    Start-Sleep -Milliseconds 500
    $dlg = $root.FindFirst($TS, (& $byName 'Overwrite your unsaved edits'))
    if (-not $dlg) { continue }
    $ok = $dlg.FindFirst($TS, (& $byName 'Apply external changes'))
    if ($ok -and (Invoke-El $ok)) { 'applied-confirmed'; exit 0 }
}

# 3. no dialog appeared: either it applied straight away, or the banner is still up
Start-Sleep -Milliseconds 1500
if ($root.FindFirst($TS, (& $byName 'Apply external changes'))) { 'still-pending' } else { 'applied' }
"""


def sync_desktop():
    """Desktop can stay open, but the two copies must not be left diverged: Desktop writes its
    stale in-memory copy back on save and silently undoes on-disk edits. So push the change into
    the running instance rather than asking anyone to close it."""
    out = subprocess.run(["powershell", "-NoProfile", "-Command", APPLY_PS],
                         capture_output=True, text=True).stdout.strip().splitlines()
    state = out[-1] if out else "unknown"
    if state == "closed":
        print("desktop       : not running - nothing to sync")
    elif state in ("applied", "applied-confirmed"):
        extra = " (confirmed the unsaved-edits prompt)" if state.endswith("confirmed") else ""
        print(f"desktop       : applied external changes{extra} - canvas now matches disk")
    else:
        print("desktop       : WARNING - could not apply. Click 'Apply external changes' in "
              "Desktop yourself, or close it WITHOUT saving; otherwise its in-memory copy "
              "will overwrite what was just written.")


read = lambda p: json.loads(p.read_text(encoding="utf-8"))
def write(p, o): p.write_text(json.dumps(o, indent=2, ensure_ascii=False), encoding="utf-8")

VC_SCHEMA = ("https://developer.microsoft.com/json-schemas/fabric/item/report/definition/"
             "visualContainer/2.12.0/schema.json")


# ---------------------------------------------------------------- field helpers
def col_field(entity, prop, display=None):
    f = {"field": {"Column": {"Expression": {"SourceRef": {"Entity": entity}},
                              "Property": prop}},
         "queryRef": f"{entity}.{prop}",
         "nativeQueryRef": prop}
    if display:
        f["displayName"] = display
    return f


def measure_field(name, display=None):
    f = {"field": {"Measure": {"Expression": {"SourceRef": {"Entity": MEASURE_TABLE}},
                               "Property": name}},
         "queryRef": f"{MEASURE_TABLE}.{name}",
         "nativeQueryRef": name}
    if display:
        f["displayName"] = display
    return f


def min_agg_field(entity, prop, display):
    """QueryAggregateFunction 3 = Min. An aggregated column lands in SUMMARIZECOLUMNS as an
    extension column -- measure-like, adds no filter, and invisible to DATEADD. On a marked
    date table a grouped helper column is safe too, but this is the shape that stays safe on
    a model whose date table is a modern `calendar` object; see 05-case-unrenderable-matrix.md."""
    return {"field": {"Aggregation": {
                "Expression": {"Column": {
                    "Expression": {"SourceRef": {"Entity": entity}},
                    "Property": prop}},
                "Function": 3}},
            "queryRef": f"Min({entity}.{prop})",
            "nativeQueryRef": f"Min of {prop}",
            "displayName": display}


def lit(v):
    return {"expr": {"Literal": {"Value": v}}}


def textbox(name, pos, paragraphs, tab_order):
    return {"$schema": VC_SCHEMA, "name": name,
            "position": dict(pos, z=0, tabOrder=tab_order),
            "visual": {"visualType": "textbox",
                       "objects": {"general": [{"properties": {"paragraphs": paragraphs}}]},
                       "drillFilterOtherVisuals": True}}


def para(runs):
    return {"textRuns": [{"value": v, "textStyle": s} for v, s in runs]}


TITLE_RUN = {"fontFamily": "Segoe UI Semibold", "fontSize": "20pt", "color": WHITE}
SUB_RUN = {"fontFamily": "Segoe UI", "fontSize": "11pt", "color": SUB}
NOTE_HEAD = {"fontFamily": "Segoe UI Semibold", "fontSize": "12pt", "color": "#0B1E3F"}
NOTE_BODY = {"fontFamily": "Segoe UI", "fontSize": "10pt", "color": "#333333"}


# ---------------------------------------------------------------- rail, cloned
def load_template():
    tpl_page = read(PAGES / TEMPLATE / "page.json")
    rail, slicers = [], {}
    for vj in sorted((PAGES / TEMPLATE / "visuals").glob("*/visual.json")):
        v = read(vj)
        vt = v["visual"].get("visualType")
        pos = v["position"]
        if vt in ("advancedSlicerVisual", "slicer"):
            prop = (v["visual"]["query"]["queryState"]["Values"]["projections"][0]
                    ["field"]["Column"]["Property"])
            slicers[prop] = v
        elif vt == DENEB_TYPE:
            continue                                   # the template's own statement visual
        elif pos["x"] < 300:
            rail.append(v)                             # logo, KEY SELECTIONS, footnote
    missing = {"Year", "Month Name Short", "Channel", "Category"} - set(slicers)
    if missing or len(rail) != 3:
        sys.exit(f"ABORT: template rail not as expected (missing slicers {missing}, "
                 f"{len(rail)} furniture visuals)")
    return tpl_page, rail, slicers


def clone_slicer(src, keep_selection):
    """Clone a rail slicer verbatim. `objects.general` holds the slicer's SAVED SELECTION, so
    dropping it is what makes the page open with nothing selected -- otherwise the clone inherits
    whatever the template page was filtered to (Jun, Online, ...) and the demo opens showing a
    slice of the business instead of all of it."""
    v = copy.deepcopy(src)
    if not keep_selection:
        v["visual"]["objects"].pop("general", None)
    return v


# ---------------------------------------------------------------- the two main visuals
def build_pivot(name):
    """Values-on-rows with no Rows field: the 28 measures ARE the rows, crossed with the
    calculation group on Columns. 15 x 28 = 420 dispatched cell evaluations."""
    projections = [measure_field(G.MEASURE_BY_KEY[k], label) for k, label, _ in G.ROWS]
    return {
        "$schema": VC_SCHEMA, "name": name,
        "position": {"x": CANVAS_X, "y": BODY_TOP, "z": 1000,
                     "width": CANVAS_W, "height": MAIN_H, "tabOrder": 3000},
        "visual": {
            "visualType": "pivotTable",
            "query": {"queryState": {
                "Columns": {"projections": [
                    dict(col_field("Period View", "Period View"), active=True)]},
                "Values": {"projections": projections},
            }},
            "objects": {
                # no Rows field, so there is nothing to subtotal in either direction
                "subTotals": [{"properties": {"rowSubtotals": lit("false"),
                                              "columnSubtotals": lit("false")}}],
                "columnHeaders": [{"properties": {"autoSizeColumnWidth": lit("true")}}],
                # this is what puts the measures down the rows instead of across the top
                "values": [{"properties": {"valuesOnRow": lit("true")}}],
            },
            "drillFilterOtherVisuals": True,
        },
    }


def build_deneb(name):
    spec = json.dumps(G.build_spec(), separators=(",", ":"))
    config = json.dumps(G.CONFIG, separators=(",", ":"))
    # The spec is a single-quoted PBIR literal, so every single quote inside it doubles.
    esc = lambda s: "'" + s.replace("'", "''") + "'"
    projections = ([col_field("DimDate", "Year", "Year"),
                    col_field("DimDate", "MonthOfYear", "Month"),
                    min_agg_field("DimDate", "MonthOffset", "MonthOffset")]
                   + [measure_field(m, field) for field, m in G.BASE_MEASURE.items()])
    return {
        "$schema": VC_SCHEMA, "name": name,
        "position": {"x": CANVAS_X, "y": BODY_TOP, "z": 1000,
                     "width": CANVAS_W, "height": MAIN_H, "tabOrder": 3000},
        "visual": {
            "visualType": DENEB_TYPE,
            "query": {"queryState": {"dataset": {"projections": projections}}},
            "objects": {
                "vega": [{"properties": {
                    "provider": lit("'vega'"),          # plain Vega, not Vega-Lite
                    "jsonSpec": lit(esc(spec)),
                    "jsonConfig": lit(esc(config)),
                    "enableTooltips": lit("true"),
                    "renderMode": lit("'svg'"),
                }}],
                "stateManagement": [{"properties": {
                    "viewportHeight": lit(f"{MAIN_H - 30}D"),
                    "viewportWidth": lit(f"{CANVAS_W - 30}D")}}],
                "developer": [{"properties": {"version": lit("'1.9.1.0'")}}],
            },
            "drillFilterOtherVisuals": True,
        },
    }


# ---------------------------------------------------------------- page copy
COPY = {
    "calcgroup": {
        "displayName": "Monthly P&L - Calc Group",
        "title": "Monthly P&L: the calculation group",
        "subtitle": ("15 period items on the columns x 28 measures on the rows: the engine "
                     "plans and evaluates 420 cells, and 315 of them re-run their own measure "
                     "to pick a format string"),
        "notes": [
            ("Why this is slow",
             ["The twelve month items differ only in a literal, but each rewrites the DimDate "
              "filter context, so the engine cannot collapse them into one GROUP BY scan. "
              "15 x 28 = 420 dispatched cells, for 10 irreducible numbers."]),
            ("The part a DAX benchmark cannot see",
             ["21 measures carry a format string that reads the measure back: a second "
              "evaluation per cell, 315 times. An EVALUATE never pays it, so it shows up in "
              "Performance Analyzer and nowhere else: 9,133 ms on the visual against 2,307 ms "
              "on the query."]),
        ],
    },
    "deneb": {
        "displayName": "Monthly P&L - Deneb",
        "title": "Monthly P&L: the Deneb grid",
        "subtitle": ("the same 28 x 15 numbers from ONE query returning 12 rows x 10 base "
                     "measures; the columns, the ratios, the variances and every format string "
                     "are derived in the spec"),
        "notes": [
            ("What the engine is asked for",
             ["DimDate[Year] x [MonthOfYear] grouped natively, the ten Act/LY measures, and "
              "MonthOffset as a Min aggregation: one scan shape, twelve rows per selected "
              "year, no calculation group anywhere near it. 370 ms in Performance Analyzer."]),
            ("What the spec derives",
             ["Jan-Dec come from the group-by; YTD, YTG and FY are sums of them, with the "
              "current month read off MonthOffset instead of a REMOVEFILTERS probe. Every "
              "ratio, variance, format string and colour is arithmetic. Query cost: zero."]),
        ],
    },
}


# ---------------------------------------------------------------- build
def build_page(key, tpl_page, rail, slicers):
    pid = sid("page", key)
    pdir = PAGES / pid
    if pdir.exists():
        shutil.rmtree(pdir)
    (pdir / "visuals").mkdir(parents=True)

    page = {
        "$schema": tpl_page["$schema"],
        "name": pid,
        "displayName": COPY[key]["displayName"],
        "displayOption": tpl_page.get("displayOption", "FitToPage"),
        "height": 1000, "width": 2000,
        "objects": {"background": copy.deepcopy(tpl_page["objects"]["background"])},
    }
    write(pdir / "page.json", page)

    visuals = []

    # rail furniture, cloned unchanged
    for v in rail:
        c = copy.deepcopy(v)
        c["name"] = sid("rail", key, v["visual"].get("visualType", "x"), v["name"])
        visuals.append(c)

    # the standard rail, cloned verbatim: Year / Month / Channel / Category.
    # Only Year keeps its selection (2026); the rest open clear.
    for label, prop, keep in [
        ("year",     "Year",             True),
        ("month",    "Month Name Short", False),
        ("channel",  "Channel",          False),
        ("category", "Category",         False),
    ]:
        c = clone_slicer(slicers[prop], keep)
        c["name"] = sid("slicer", key, label)
        for f in c.get("filterConfig", {}).get("filters", []):
            f["name"] = sid("visfilter", key, label, f.get("name", ""))
        visuals.append(c)

    # title
    visuals.append(textbox(
        sid("title", key), TITLE,
        [para([(COPY[key]["title"], TITLE_RUN)]), para([(COPY[key]["subtitle"], SUB_RUN)])],
        2000))

    # main visual
    visuals.append(build_pivot(sid("main", key)) if key == "calcgroup"
                   else build_deneb(sid("main", key)))

    # two commentary boxes under it
    gap, n = 16, 2
    each = (CANVAS_W - gap * (n - 1)) // n
    for i, (head, bodies) in enumerate(COPY[key]["notes"]):
        paras = [para([(head, NOTE_HEAD)])] + [para([(b, NOTE_BODY)]) for b in bodies]
        visuals.append(textbox(
            sid("note", key, str(i)),
            dict(x=CANVAS_X + i * (each + gap), y=NOTE_Y, width=each, height=NOTE_H),
            paras, 4000 + i * 1000))

    for v in visuals:
        d = pdir / "visuals" / v["name"]
        d.mkdir(parents=True, exist_ok=True)
        write(d / "visual.json", v)
    return pid, len(visuals)


def main():
    tpl_page, rail, slicers = load_template()

    pj = read(PAGES / "pages.json")
    built = []
    for key in PAGE_KEYS:
        pid, n = build_page(key, tpl_page, rail, slicers)
        built.append(pid)
        if pid not in pj["pageOrder"]:
            pj["pageOrder"].append(pid)
        print(f"{COPY[key]['displayName']:28s} {pid}  {n} visuals")
    write(PAGES / "pages.json", pj)

    # names must be unique report-wide: duplicates make Desktop open with "Issues were found"
    # and an empty model, and pbir validate does not catch it.
    seen, dupes = {}, []
    for vj in PAGES.glob("*/visuals/*/visual.json"):
        v = read(vj)
        if v["name"] in seen:
            dupes.append((v["name"], seen[v["name"]], str(vj)))
        seen[v["name"]] = str(vj)
    print(f"\npages         : {len(pj['pageOrder'])} total, {len(built)} built here")
    print(f"visual names  : {len(seen)} unique, {len(dupes)} duplicates")
    if dupes:
        for d in dupes:
            print("  DUPLICATE", d)
        sys.exit(1)
    sync_desktop()


if __name__ == "__main__":
    main()
