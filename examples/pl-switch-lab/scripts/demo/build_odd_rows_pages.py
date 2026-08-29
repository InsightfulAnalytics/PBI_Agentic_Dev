# Builds two new report pages for the Odd Rows P&L comparison:
#
#   page 8  "Odd Rows P&L - 2 Calc Groups"  (candidate E)
#           rows = 'P&L Row' calc group (13 items, precedence 5)
#           cols = 'P&L View' calc group (14 items, precedence 10)
#           values = [NM CG Value].  No SWITCH anywhere in the model path.
#
#   page 9  "Odd Rows P&L - Deneb"          (candidate G)
#           A Deneb (Vega-Lite) visual over a 30-row dataset: 5 statement lines on a
#           GROUPED bridge axis x 6 base calculation items, carrying 3 measures. The spec
#           derives the other 8 statement rows and the other 8 column variants client-side,
#           reconstructing all 182 cells for 18 engine scans instead of 182.
#
# Ids are uuid5-derived from fixed seeds, so re-running is idempotent rather than producing
# a second copy of each page. EVERY name id is regenerated per page, filterConfig filter
# names included -- duplicate filter names across pages make Desktop open with "Issues were
# found" and load an empty model, and pbir validate does not catch it.
#
# POWER BI DESKTOP MUST BE CLOSED: it re-serialises the project on close and will revert
# anything written while it is running.
import json
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEF = ROOT / "PL Bridge Demo.Report" / "definition"
PAGES = DEF / "pages"
SPEC_DIR = ROOT / "scripts" / "demo" / "deneb"

DRY = "--dry-run" in sys.argv
if not DRY:
    _probe = "if (Get-Process PBIDesktop -EA SilentlyContinue) { exit 1 } else { exit 0 }"
    if subprocess.run(["powershell", "-NoProfile", "-Command", _probe],
                      capture_output=True).returncode != 0:
        sys.exit("ABORT: Power BI Desktop is running - it will revert these edits on close.")

DENEB = "deneb7E15AEF80B9E4D4F8E12924291ECE89A"
SEMI = "'Segoe UI Semibold', wf_segoe-ui_semibold, helvetica, arial, sans-serif"
REG = "'Segoe UI', wf_segoe-ui_normal, helvetica, arial, sans-serif"
VC = ("https://developer.microsoft.com/json-schemas/fabric/item/report/definition"
      "/visualContainer/2.12.0/schema.json")
PG = ("https://developer.microsoft.com/json-schemas/fabric/item/report/definition"
      "/page/2.3.0/schema.json")

BASE_ITEMS = ["Actual", "LY", "Budget", "YTD Actual", "YTD LY", "YTD Budget"]
BRIDGE_LINES = ["Total Income", "Total Cost of Sales", "Gross Profit",
                "Total Operating Expenses", "Net Profit"]

SQ = chr(39)  # single quote, built at runtime so no shell heredoc can mangle it


def gid(s):
    return uuid.uuid5(uuid.NAMESPACE_URL, "plbridgedemo/page/" + s).hex[:20]


def col(entity, prop, native, **x):
    d = {"field": {"Column": {"Expression": {"SourceRef": {"Entity": entity}},
                              "Property": prop}},
         "queryRef": entity + "." + prop, "nativeQueryRef": native}
    d.update(x)
    return d


def meas(prop, native, **x):
    d = {"field": {"Measure": {"Expression": {"SourceRef": {"Entity": "00_Measures"}},
                               "Property": prop}},
         "queryRef": "00_Measures." + prop, "nativeQueryRef": native}
    d.update(x)
    return d


def lit(expr):
    return {"expr": {"Literal": {"Value": expr}}}


def textbox(name, x, y, w, h, z, paras):
    runs = [{"textRuns": [{"value": t,
                           "textStyle": {"fontFamily": f, "fontSize": s}}]}
            for t, f, s in paras]
    return {"$schema": VC, "name": name,
            "position": {"x": x, "y": y, "z": z, "height": h, "width": w},
            "visual": {"visualType": "textbox",
                       "objects": {"general": [{"properties": {"paragraphs": runs}}]},
                       "drillFilterOtherVisuals": True}}


def cat_filter(fname, entity, prop, values, alias):
    """Categorical IN filter. String literals must be single-quoted inside Value."""
    return {
        "name": fname,
        "field": {"Column": {"Expression": {"SourceRef": {"Entity": entity}},
                             "Property": prop}},
        "type": "Categorical",
        "filter": {
            "Version": 2,
            "From": [{"Name": alias, "Entity": entity, "Type": 0}],
            "Where": [{"Condition": {"In": {
                "Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": alias}},
                                            "Property": prop}}],
                "Values": [[{"Literal": {"Value": v}}] for v in values]}}}],
        },
        "howCreated": "User",
    }


def year_filter(fname):
    return cat_filter(fname, "DimDate", "Year", ["2026L"], "d")


def write_page(pid, display, visuals, page_filters):
    d = PAGES / pid
    (d / "visuals").mkdir(parents=True, exist_ok=True)
    page = {"$schema": PG, "name": pid, "displayName": display,
            "displayOption": "FitToPage", "height": 1000, "width": 2000,
            "filterConfig": {"filters": page_filters}}
    (d / "page.json").write_text(json.dumps(page, indent=2, ensure_ascii=False),
                                 encoding="utf-8")
    for v in visuals:
        vd = d / "visuals" / v["name"]
        vd.mkdir(parents=True, exist_ok=True)
        (vd / "visual.json").write_text(json.dumps(v, indent=2, ensure_ascii=False),
                                        encoding="utf-8")


# ----------------------------------------------------------------- page 8 : candidate E
P8 = gid("e2cg")
p8_matrix = {
    "$schema": VC, "name": gid("e2cg/matrix"),
    "position": {"x": 40, "y": 118, "z": 1, "height": 568, "width": 1920},
    "visual": {
        "visualType": "pivotTable",
        "query": {"queryState": {
            # row levels need active:true on EVERY level, or Desktop renders one column
            # with expanders and silently drops the rest
            "Rows": {"projections": [col("P&L Row", "P&L Row", "P&L Row", active=True)]},
            "Columns": {"projections": [col("P&L View", "P&L View", "P&L View", active=True)]},
            "Values": {"projections": [meas("NM CG Value", "NM CG Value")]},
        }},
        "objects": {
            "subTotals": [{"properties": {"rowSubtotals": lit("false"),
                                          "columnSubtotals": lit("false")}}],
            "columnHeaders": [{"properties": {"autoSizeColumnWidth": lit("true")}}],
        },
        "drillFilterOtherVisuals": True,
    },
}
P8_VISUALS = [
    textbox(gid("e2cg/title"), 40, 20, 1920, 85, 0, [
        ("Odd Rows P&L \u2014 two calculation groups, no SWITCH anywhere", SEMI, "20pt"),
        ("rows are a 13-item calculation group, columns the same 14-item group, values a "
         "single measure \u2014 the same 182 cells with zero branch logic in the model",
         REG, "11pt")]),
    p8_matrix,
    textbox(gid("e2cg/why"), 40, 705, 940, 270, 2, [
        ("How it works", SEMI, "14pt"),
        ("'P&L Row' is a second calculation group, 13 items, precedence 5. 'P&L View' keeps "
         "precedence 10 so it stays the OUTER wrapper.", REG, "10pt"),
        ("That direction is load-bearing. 'Trading Stores' is DISTINCTCOUNT with no measure "
         "reference in it. As the OUTER item there would be nothing for the column group to "
         "rewrite, and all 14 of its columns would return the same current-period count "
         "\u2014 silently, with no error. As the INNER item it is substituted into the column "
         "item's CALCULATE and shifts correctly.", REG, "10pt"),
        ("Ties out 182/182 against the shipped numbers.", REG, "10pt")]),
    textbox(gid("e2cg/verdict"), 1020, 705, 940, 270, 3, [
        ("And it is still not the fastest", SEMI, "14pt"),
        ("Removing SWITCH entirely does NOT win:", REG, "10pt"),
        ("13 measures via field parameter   1,269 ms cold /  812 ms warm\n"
         "14 SWITCH measures (page 7)       1,125 ms cold /  724 ms warm\n"
         "two calculation groups (here)     1,030 ms cold /  641 ms warm\n"
         "one 13-branch SWITCH (page 6)       981 ms cold /  597 ms warm\n"
         "Deneb, grouped axis (page 9)        224 ms cold /   27 ms warm", REG, "10pt"),
        ("13 calculation items x 14 calculation items is still 182 independent expressions. "
         "Cost is instantiation count, not branch count \u2014 a shallow SWITCH evaluated once "
         "beats a calculation group evaluated per row. The only thing that changes the order "
         "of magnitude is putting the rows on a GROUPED column, which is what page 9 does.",
         REG, "10pt"),
        ("What THIS matrix actually pays: its query is the long shape (862 ms warm), and the "
         "dynamic format string: Fmt.Money over SELECTEDMEASURE, which under two "
         "calculation groups is the full rewritten cell expression: doubles it to "
         "1,820 ms warm / 2,331 cold before rendering. Auto-scaled $M/$K formatting is not free.",
         REG, "10pt")]),
]

# ----------------------------------------------------------------- page 9 : candidate G
P9 = gid("gdeneb")
spec_f = SPEC_DIR / "pl_spec.json"
cfg_f = SPEC_DIR / "pl_config.json"
have_spec = spec_f.exists() and cfg_f.exists()
P9_VISUALS = None

if have_spec:
    spec = json.dumps(json.loads(spec_f.read_text(encoding="utf-8")), separators=(",", ":"))
    cfg = json.dumps(json.loads(cfg_f.read_text(encoding="utf-8")), separators=(",", ":"))

    def pbir_literal(s):
        # the whole JSON sits inside a single-quoted DAX literal; embedded ' must be doubled
        return SQ + s.replace(SQ, SQ + SQ) + SQ

    p9_visual = {
        "$schema": VC, "name": gid("gdeneb/visual"),
        "position": {"x": 40, "y": 118, "z": 1, "height": 568, "width": 1920},
        "visual": {
            "visualType": DENEB,
            # Deneb names dataset fields by the DISPLAY name in the Values well, and the
            # spec's datum['Amount'] etc. must match. nativeQueryRef is the field's real
            # native name -- it is NOT a rename. Binding [NM Amount] with a bare
            # nativeQueryRef "Amount" left the dataset field named "NM Amount": every
            # pivot output came up undefined and the isValid guard blanked all 182 cells
            # while the axes (drawn from explicit scale domains) still rendered.
            "query": {"queryState": {"dataset": {"projections": [
                col("P&L Lines", "Line", "Line"),
                col("P&L View", "P&L View", "P&L View"),
                meas("NM Amount", "NM Amount", displayName="Amount"),
                meas("NM Stores All Lines", "NM Stores All Lines",
                     displayName="Trading Stores"),
                meas("NM Products All Lines", "NM Products All Lines",
                     displayName="Active Products"),
            ]}}},
            "objects": {"vega": [{"properties": {
                "provider": lit(SQ + "vegaLite" + SQ),
                "jsonSpec": lit(pbir_literal(spec)),
                "jsonConfig": lit(pbir_literal(cfg)),
                "enableTooltips": lit("true"),
                "enableContextMenu": lit("true"),
                "enableSelection": lit("false"),
                "enableHighlight": lit("false"),
                "isNewDialogOpen": lit("false"),
                "logLevel": lit("3D"),
            }}]},
            "drillFilterOtherVisuals": True,
        },
        # visual-level filterConfig is a SIBLING of "visual", not a property inside it --
        # the visualContainer schema is additionalProperties:false and rejects it there.
        # Restricts the dataset to exactly the 30 rows the spec needs.
        "filterConfig": {"filters": [
            cat_filter(gid("gdeneb/f-lines"), "P&L Lines", "Line",
                       [SQ + v + SQ for v in BRIDGE_LINES], "pl"),
            cat_filter(gid("gdeneb/f-items"), "P&L View", "P&L View",
                       [SQ + v + SQ for v in BASE_ITEMS], "pv"),
        ]},
    }
    P9_VISUALS = [
        textbox(gid("gdeneb/title"), 40, 20, 1920, 85, 0, [
            ("Odd Rows P&L \u2014 Deneb, 182 cells from 30 rows", SEMI, "20pt"),
            ("the engine returns 5 statement lines on a GROUPED bridge axis x 6 base "
             "calculation items; the Vega spec derives the other 8 rows and 8 columns "
             "client-side \u2014 18 scans instead of 182", REG, "11pt")]),
        p9_visual,
        textbox(gid("gdeneb/why"), 40, 705, 940, 270, 2, [
            ("Why this is 20x faster", SEMI, "14pt"),
            ("Measured on this model: cost tracks the number of INDEPENDENT fact-table scans. "
             "A measure column costs one scan per calculation item. If the rows are dispatched "
             "by an expression \u2014 SWITCH, field parameter or calculation group \u2014 it is "
             "one scan per row per item. If the rows sit on a GROUPED column the engine buckets "
             "them in a single scan and the row count becomes free.", REG, "10pt"),
            ("Only 5 of the 13 rows are irreducible; the other 8 are arithmetic on those 5 plus "
             "two counts. Only 6 of the 14 columns are base facts; the other 8 are differences "
             "and ratios. Deneb is the only visual that lets that arithmetic leave the engine.",
             REG, "10pt"),
            ("224 ms cold / 27 ms warm, against 1,269 / 812 for the original page 6.",
             REG, "10pt")]),
        textbox(gid("gdeneb/cost"), 1020, 705, 940, 270, 3, [
            ("What it costs you", SEMI, "14pt"),
            ("The spec has to reimplement what the matrix and the calculation group gave for "
             "free: column headers, row order, subtotal emphasis, and all the number formatting "
             "\u2014 the $M/$K auto-scaling, the percent rows, the count row, and the rule that "
             "a '%' COLUMN overrides its row's own format.", REG, "10pt"),
            ("It also drops the dynamic format string, and that is not a small thing. Measured "
             "separately: evaluating [NM Row Value]'s formatStringDefinition costs as much again "
             "as the value itself (622 -> 1,270 ms warm), because it calls "
             "Fmt.Money ( [NM Row Value] ) and re-runs the whole SWITCH per cell. A DAX query "
             "benchmark never sees that; the visual pays it.", REG, "10pt"),
            ("No cross-filtering out of the visual, and no prior art \u2014 the Deneb community "
             "corpus has financial charts but no statement table.", REG, "10pt")]),
    ]


# ----------------------------------------------------------------- page 10 : classic Deneb
# The CLASSIC 27-line statement (same grid as pages 2 and 3) as a Deneb visual --
# the direct SWITCH-vs-Deneb comparison. Dataset: 27 bridge lines (grouped) x the 6
# base fast measures; the 8 variance columns and all formatting live in the spec.
P10 = gid("cdeneb")
cspec_f = SPEC_DIR / "pl_classic_spec.json"
have_cspec = cspec_f.exists() and cfg_f.exists()
P10_VISUALS = None

if have_cspec:
    cspec = json.dumps(json.loads(cspec_f.read_text(encoding="utf-8")), separators=(",", ":"))
    ccfg = json.dumps(json.loads(cfg_f.read_text(encoding="utf-8")), separators=(",", ":"))

    def pbir_lit(s):
        return SQ + s.replace(SQ, SQ + SQ) + SQ

    p10_visual = {
        "$schema": VC, "name": gid("cdeneb/visual"),
        "position": {"x": 40, "y": 118, "z": 1, "height": 810, "width": 1920},
        "visual": {
            "visualType": DENEB,
            # Deneb names dataset fields by the DISPLAY name -- the spec expects
            # Line / LineKey / LineClass / Actual / Budget / LY / "YTD ..." exactly.
            "query": {"queryState": {"dataset": {"projections": [
                col("P&L Lines", "Line", "Line"),
                col("P&L Lines", "LineKey", "LineKey"),
                col("P&L Lines", "LineClass", "LineClass"),
                meas("P&L Actual", "P&L Actual", displayName="Actual"),
                meas("P&L Budget", "P&L Budget", displayName="Budget"),
                meas("P&L LY", "P&L LY", displayName="LY"),
                meas("P&L Actual YTD", "P&L Actual YTD", displayName="YTD Actual"),
                meas("P&L Budget YTD", "P&L Budget YTD", displayName="YTD Budget"),
                meas("P&L LY YTD", "P&L LY YTD", displayName="YTD LY"),
            ]}}},
            "objects": {"vega": [{"properties": {
                "provider": lit(SQ + "vegaLite" + SQ),
                "jsonSpec": lit(pbir_lit(cspec)),
                "jsonConfig": lit(pbir_lit(ccfg)),
                "enableTooltips": lit("true"),
                "enableContextMenu": lit("true"),
                "enableSelection": lit("false"),
                "enableHighlight": lit("false"),
                "isNewDialogOpen": lit("false"),
                "logLevel": lit("3D"),
            }}]},
            "drillFilterOtherVisuals": True,
        },
    }
    P10_VISUALS = [
        textbox(gid("cdeneb/title"), 40, 20, 1920, 85, 0, [
            ("P&L: Deneb", SEMI, "20pt"),
            ("the classic 27-line statement, 378 cells from a 27-row query: identical "
             "numbers to the Classic SWITCH page, at a fraction of the cost", REG, "11pt")]),
        p10_visual,
        textbox(gid("cdeneb/footer"), 40, 940, 1920, 45, 2, [
            ("Engine query: 27 bridge lines (grouped) x 6 base measures, ~15 ms warm: the "
             "Classic SWITCH page computes the identical grid in ~2,400 ms warm / ~2,900 ms cold. "
             "The 8 variance columns are derived in the Vega spec, and formatting is client-side, "
             "so there is no dynamic-format-string tax either. Measured 2026-08-24.", REG, "9pt")]),
    ]

# ----------------------------------------------------------------- write
if DRY:
    print("DRY RUN - no files written")
    print("  page 8 id " + P8)
    print("  page 9 id " + P9 + "  spec present: " + str(have_spec))
    print("  page 10 id " + P10 + "  spec present: " + str(have_cspec))
    sys.exit(0)

write_page(P8, "Odd Rows P&L - 2 Calc Groups", P8_VISUALS, [year_filter(gid("e2cg/f-year"))])
print("page 8 written: " + P8)
if P9_VISUALS:
    write_page(P9, "Odd Rows P&L - Deneb", P9_VISUALS, [year_filter(gid("gdeneb/f-year"))])
    print("page 9 written: " + P9)
else:
    print("page 9 SKIPPED - no spec at scripts/demo/deneb/pl_spec.json")
if P10_VISUALS:
    # the classic pages pin BOTH Year and Time Period -- the fast measures dispatch on it
    write_page(P10, "P&L - Deneb", P10_VISUALS, [
        year_filter(gid("cdeneb/f-year")),
        cat_filter(gid("cdeneb/f-tp"), "Time Period", "Time Period",
                   [SQ + "Selected Period" + SQ], "tp"),
    ])
    print("page 10 written: " + P10)
else:
    print("page 10 SKIPPED - no spec at scripts/demo/deneb/pl_classic_spec.json")

pj = PAGES / "pages.json"
meta = json.loads(pj.read_text(encoding="utf-8"))
for pid in ([P8, P9] if P9_VISUALS else [P8]):
    if pid not in meta["pageOrder"]:
        meta["pageOrder"].append(pid)
if P10_VISUALS and P10 not in meta["pageOrder"]:
    # the classic Deneb page belongs beside its comparison targets: directly after
    # "P&L - Fast Bridge", not at the end of the deck
    order = meta["pageOrder"]
    order.insert(order.index("b21669a248904517a392") + 1, P10)
pj.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
print("pages.json updated: " + str(meta["pageOrder"]))

if P9_VISUALS or P10_VISUALS:
    rj = DEF / "report.json"
    rep = json.loads(rj.read_text(encoding="utf-8"))
    pcv = rep.setdefault("publicCustomVisuals", [])
    if DENEB not in pcv:
        pcv.append(DENEB)
        rj.write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
        print("report.json: registered Deneb custom visual")
    else:
        print("report.json: Deneb already registered")
