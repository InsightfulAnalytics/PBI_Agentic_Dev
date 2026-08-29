"""Build the Monthly P&L Deneb grid spec -- the fast half of the lab reproduction in
docs/performance/07-lab-monthly-matrix.md.

Replaces a pivotTable whose columns are the 15-item 'Period View' calculation group crossed
with 28 measures on rows: 420 dispatched cell evaluations, 315 of them re-evaluating their
measure through a self-referencing format string.

The grid queries the irreducible dataset instead -- DimDate[Year] x [MonthOfYear] grouped
natively with the 10 base measures, one scan shape -- and derives everything else:

  Jan..Dec   the month columns, straight from the group-by
  FY         sum of the months                    (calc item: ALLEXCEPT year)
  YTD / YTG  sum of months <= / > current period  (calc item: MonthOffset = 0 probe)
  ratios     Gross Margin %, Opex % of Income, every Var % and bps row
  formats    Fmt.Money thresholds and the dynamic percent rule, as Vega format() calls

Current period comes out of the data with no extra DAX. MonthOffset is
(12*Y + M) - (12*todayY + todayM) upstream, so 12*Y + M - MonthOffset is today's absolute
month index on every row; its mod-12 is the same month the calc items' REMOVEFILTERS probe
finds, with the same staleness.

Emits the (preview, deneb) pair plus sample rows and a Python-computed expected-cells file
for verify_monthly.mjs -- two implementations of the same DAX rules, one gate.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

# ---------------------------------------------------------------- styling
INK = "#231F20"
BAND = "#1B3A57"        # header band; the report's navy, not the field report's black
TITLE_BG = "#F1F1F1"    # section-title rows
WHITE = "#FFFFFF"
GRID_H = "#E6E6E6"      # horizontal rule above and below every row
POS = "#00792E"
NEG = "#B3261E"
FONT = "Segoe UI"
FONT_SIZE = 13
HEADER_H = 34
LABEL_W = 160           # the longest label is now "Opex % Var bps"; the section
                        # captions carry the full names, so nothing is lost
MIN_ROW_H = 21          # a FLOOR for a squeezed container, not the row height. Deneb's
                        # own chrome eats ~28px, so a 740px visual gives the view ~712px
                        # and rows land at (712-34)/28 = 24px. Set the floor above that
                        # and NEED_H exceeds the view, which is what puts the scrollbar in.
SCROLL_W = 12

N_COLS = 15
N_ROWS = 28
NEED_H = HEADER_H + N_ROWS * MIN_ROW_H

CONFIG = {"view": {"stroke": "transparent"}, "font": FONT}

# ---------------------------------------------------------------- dataset contract
# displayName on the projection == the field name the spec reads. A mismatch fails SILENTLY:
# the query runs, the dataset arrives under the native name, and the grid renders blank.
MEASURES = ["IncAct", "IncLY", "CogAct", "CogLY", "GPAct", "GPLY",
            "OpxAct", "OpxLY", "NPAct", "NPLY"]

# ---------------------------------------------------------------- row registry
# (key, label, fmt) -- fmt None marks a section-title band row.
# 7 sections x (1 caption + 3 rows) = 28, matching the measure list in
# scripts/demo/gen_monthly_matrix.py one for one.
ROWS = [
    # Each section caption carries the full name, so the three rows under it do not repeat it.
    # At 13pt that is what buys the label gutter down to 160px and gives the fifteen value
    # columns their width back.
    ("t_inc",   "Income",              None),
    ("inc_act", "Income Act",          "money"),
    ("inc_ly",  "Income LY",           "money"),
    ("inc_var", "Income Var %",        "pct"),
    ("t_cogs",  "Cost of Sales",       None),
    ("cog_act", "COGS Act",            "money"),
    ("cog_ly",  "COGS LY",             "money"),
    ("cog_var", "COGS Var %",          "pct"),
    ("t_gp",    "Gross Profit",        None),
    ("gp_act",  "GP Act",              "money"),
    ("gp_ly",   "GP LY",               "money"),
    ("gp_var",  "GP Var %",            "pct"),
    ("t_gm",    "Gross Margin",        None),
    ("gm_act",  "GM % Act",            "pct"),
    ("gm_ly",   "GM % LY",             "pct"),
    ("gm_var",  "GM Var bps",          "pct"),
    ("t_opx",   "Operating Expenses",  None),
    ("opx_act", "Opex Act",            "money"),
    ("opx_ly",  "Opex LY",             "money"),
    ("opx_var", "Opex Var %",          "pct"),
    ("t_ratio", "Cost Ratio",          None),
    ("opr_act", "Opex % Act",          "pct"),
    ("opr_ly",  "Opex % LY",           "pct"),
    ("opr_var", "Opex % Var bps",      "pct"),
    ("t_np",    "Net Profit",          None),
    ("np_act",  "NP Act",              "money"),
    ("np_ly",   "NP LY",               "money"),
    ("np_var",  "NP Var %",            "pct"),
]
assert len(ROWS) == N_ROWS
DATA_KEYS = [k for k, _, f in ROWS if f is not None]
assert len(DATA_KEYS) == 21

# ---------------------------------------------------------------- the shared contract
# The slow page binds these 28 model measures, in this order, as Values-on-rows; the fast
# page binds the 10 below as the dataset. Both live here so the two builders cannot drift:
# design/build_monthly_pages.py imports them rather than restating them.
MEASURE_BY_KEY = {
    "t_inc": "MP Sec Income",            "inc_act": "MP Income Act",
    "inc_ly": "MP Income LY",            "inc_var": "MP Income Var %",
    "t_cogs": "MP Sec Cost of Sales",    "cog_act": "MP COGS Act",
    "cog_ly": "MP COGS LY",              "cog_var": "MP COGS Var %",
    "t_gp": "MP Sec Gross Profit",       "gp_act": "MP GP Act",
    "gp_ly": "MP GP LY",                 "gp_var": "MP GP Var %",
    "t_gm": "MP Sec Gross Margin",       "gm_act": "MP GM % Act",
    "gm_ly": "MP GM % LY",               "gm_var": "MP GM % Var bps",
    "t_opx": "MP Sec Operating Expenses", "opx_act": "MP Opex Act",
    "opx_ly": "MP Opex LY",              "opx_var": "MP Opex Var %",
    "t_ratio": "MP Sec Cost Ratio",      "opr_act": "MP Opex % Act",
    "opr_ly": "MP Opex % LY",            "opr_var": "MP Opex % Var bps",
    "t_np": "MP Sec Net Profit",         "np_act": "MP NP Act",
    "np_ly": "MP NP LY",                 "np_var": "MP NP Var %",
}
assert set(MEASURE_BY_KEY) == {k for k, _, _ in ROWS}

# dataset field name -> model measure. The field name is the projection's displayName, and
# a mismatch here is the silent failure mode: the grid renders its skeleton with no numbers.
BASE_MEASURE = {
    "IncAct": "MP Income Act", "IncLY": "MP Income LY",
    "CogAct": "MP COGS Act",   "CogLY": "MP COGS LY",
    "GPAct": "MP GP Act",      "GPLY": "MP GP LY",
    "OpxAct": "MP Opex Act",   "OpxLY": "MP Opex LY",
    "NPAct": "MP NP Act",      "NPLY": "MP NP LY",
}
assert list(BASE_MEASURE) == MEASURES

ROWS_REG = [{"key": k, "rowIdx": i, "label": lbl,
             "kind": "title" if f is None else "data",
             "fmt": f or "", "isVar": k.endswith("_var")}
            for i, (k, lbl, f) in enumerate(ROWS)]
ROW_EDGES = [{"edge": i} for i in range(N_ROWS + 1)]

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
# Column order must match the calculation group's DECLARATION order, which is what the
# matrix renders: Jan..Dec, YTD, YTG, Full Year.
COLS_REG = ([{"colLabel": m, "colIdx": i} for i, m in enumerate(MONTHS)]
            + [{"colLabel": "YTD", "colIdx": 12},
               {"colLabel": "YTG", "colIdx": 13},
               {"colLabel": "FY", "colIdx": 14}])


# ---------------------------------------------------------------- row arithmetic
# DAX semantics, reproduced exactly:
#   DIVIDE(n, d) -> BLANK when d is BLANK or 0, and when n is BLANK
#   a - b        -> BLANK only when BOTH are BLANK; otherwise BLANK acts as 0
#   x * BLANK()  -> BLANK  (which is why the Opex sign flip is written -1 * [x] in DAX)
def var_pct(act, ly):
    return (f"(datum.{ly} == null || datum.{ly} == 0) ? null : "
            f"(((datum.{act} == null ? 0 : datum.{act}) - datum.{ly}) / datum.{ly})")


def ratio(n, d):
    return (f"(datum.{d} == null || datum.{d} == 0 || datum.{n} == null) ? null : "
            f"(datum.{n} / datum.{d})")


def neg_ratio(n, d):
    """DIVIDE ( -1 * [n], [d] ) -- the sign flip preserves the blank, so the guard is the
    same as ratio()."""
    return (f"(datum.{d} == null || datum.{d} == 0 || datum.{n} == null) ? null : "
            f"(-datum.{n} / datum.{d})")


def sub(a, b):
    return ("(datum.{a} == null && datum.{b} == null) ? null : "
            "((datum.{a} == null ? 0 : datum.{a}) - (datum.{b} == null ? 0 : datum.{b}))"
            ).format(a=a, b=b)


ROW_FORMULAS = {
    "inc_act": "datum.IncAct",
    "inc_ly":  "datum.IncLY",
    "inc_var": var_pct("IncAct", "IncLY"),
    "cog_act": "datum.CogAct",
    "cog_ly":  "datum.CogLY",
    "cog_var": var_pct("CogAct", "CogLY"),
    "gp_act":  "datum.GPAct",
    "gp_ly":   "datum.GPLY",
    "gp_var":  var_pct("GPAct", "GPLY"),
    "gm_act":  ratio("GPAct", "IncAct"),
    "gm_ly":   ratio("GPLY", "IncLY"),
    # sequential: reads the two gm fields calculated immediately above
    "gm_var":  sub("gm_act", "gm_ly"),
    "opx_act": "datum.OpxAct",
    "opx_ly":  "datum.OpxLY",
    "opx_var": var_pct("OpxAct", "OpxLY"),
    "opr_act": neg_ratio("OpxAct", "IncAct"),
    "opr_ly":  neg_ratio("OpxLY", "IncLY"),
    "opr_var": sub("opr_act", "opr_ly"),
    "np_act":  "datum.NPAct",
    "np_ly":   "datum.NPLY",
    "np_var":  var_pct("NPAct", "NPLY"),
}
assert list(ROW_FORMULAS) == DATA_KEYS

# ---------------------------------------------------------------- number formats
# Fmt.Money (functions.tmdl), verbatim:
#   >= 999950  "$#,##0,,.0""M"""   >= 999.5  "$#,##0,.0""K"""   else  "$#,##0"
# and the dynamic percent rule on the 11 ratio measures:
#   ABS(v) >= 1 -> "0%"  else "0.0%"
# Negatives render as accounting parentheses, which is the ";(...)" half of each DAX format.
MONEY_BODY = ("'$' + (datum.av >= 999950 ? format(datum.av / 1e6, ',.1f') + 'M'"
              " : datum.av >= 999.5 ? format(datum.av / 1e3, ',.1f') + 'K'"
              " : format(datum.av, ',.0f'))")
PCT_BODY = "(datum.av >= 1 ? format(datum.av, '.0%') : format(datum.av, '.1%'))"
BODY_EXPR = f"datum.fmt == 'pct' ? {PCT_BODY} : {MONEY_BODY}"


def aggregate(groupby=None):
    """sum + valid per base measure. sum ignores nulls and returns 0 over nothing, which DAX
    would call BLANK; the valid count is what lets null_guards() put the blank back."""
    agg = {
        "type": "aggregate",
        "fields": MEASURES + MEASURES + ["todayIdx"],
        "ops": ["sum"] * len(MEASURES) + ["valid"] * len(MEASURES) + ["max"],
        "as": [f"s{m}" for m in MEASURES] + [f"v{m}" for m in MEASURES] + ["todayIdx"],
    }
    if groupby:
        agg["groupby"] = groupby
    return agg


def null_guards():
    return [{"type": "formula", "as": m,
             "expr": f"datum.v{m} > 0 ? datum.s{m} : null"} for m in MEASURES]


def totals(name, filter_expr, col_label, col_idx):
    entry = {"name": name, "source": "months", "transform": []}
    if filter_expr:
        entry["transform"].append({"type": "filter", "expr": filter_expr})
    entry["transform"].append(aggregate())
    entry["transform"] += null_guards()
    entry["transform"] += [
        {"type": "formula", "as": "colLabel", "expr": f"'{col_label}'"},
        {"type": "formula", "as": "colIdx", "expr": str(col_idx)},
    ]
    return entry


def build_data(inline_rows=None):
    dataset = {"name": "dataset"}
    if inline_rows is not None:
        dataset["values"] = inline_rows
    dataset["transform"] = [
        # Today's absolute month index; constant across rows by construction of MonthOffset.
        # Guard every input: a null MonthOffset would coerce to 0 and give a plausible but
        # entirely wrong current month.
        {"type": "formula", "as": "todayIdx",
         "expr": ("isValid(datum.MonthOffset) && isValid(datum.Year) && isValid(datum.Month)"
                  " ? 12 * datum.Year + datum.Month - datum.MonthOffset"
                  " : null")},
    ]
    return [
        dataset,
        {"name": "rowsReg", "values": ROWS_REG},
        {"name": "rowEdges", "values": ROW_EDGES},
        {"name": "colsReg", "values": COLS_REG},
        {"name": "titleRows", "source": "rowsReg",
         "transform": [{"type": "filter", "expr": "datum.kind == 'title'"}]},
        # One datum per month, summed across any extra grouping -- two selected years land in
        # the same month bucket, exactly as the calc items' ALLEXCEPT ( ..., [Year] ) does.
        {"name": "months", "source": "dataset", "transform":
            [aggregate(groupby=["Month"])] + null_guards() + [
                # No usable MonthOffset anywhere -> curP is null and BOTH cumulative filters
                # below fail closed, blanking YTD and YTG. Deliberate: a blank column gets
                # reported, whereas curP = 0 would render YTG as the full year and look fine.
                {"type": "formula", "as": "curP",
                 "expr": "isFinite(datum.todayIdx) ? ((datum.todayIdx - 1) % 12) + 1 : null"},
            ]},
        {"name": "monthCols", "source": "months", "transform": [
            # A month 13, if a calendar ever carries one, has no column -- exactly like the
            # calculation group, which defines no item for it. It still lands in FY and YTG.
            {"type": "filter", "expr": "datum.Month >= 1 && datum.Month <= 12"},
            {"type": "formula", "as": "colIdx", "expr": "datum.Month - 1"},
            {"type": "formula", "as": "colLabel",
             "expr": f"{json.dumps(MONTHS)}[datum.Month - 1]"},
        ]},
        # isValid guards are load-bearing: JS coerces null to 0, so a bare
        # `datum.Month > datum.curP` is TRUE for every month when curP is null.
        totals("totYTD", "isValid(datum.curP) && datum.Month <= datum.curP", "YTD", 12),
        totals("totYTG", "isValid(datum.curP) && datum.Month > datum.curP", "YTG", 13),
        totals("totFY", None, "FY", 14),
        {"name": "cells", "source": ["monthCols", "totYTD", "totYTG", "totFY"],
         "transform":
            [{"type": "formula", "as": k, "expr": ROW_FORMULAS[k]} for k in DATA_KEYS]
            + [
                {"type": "fold", "fields": DATA_KEYS, "as": ["key", "value"]},
                {"type": "lookup", "from": "rowsReg", "key": "key",
                 "fields": ["key"], "values": ["rowIdx", "label", "fmt", "isVar"],
                 "as": ["rowIdx", "rowLabel", "fmt", "isVar"]},
                {"type": "formula", "as": "av", "expr": "abs(datum.value)"},
                {"type": "formula", "as": "body", "expr": BODY_EXPR},
                {"type": "formula", "as": "fmtd",
                 "expr": ("datum.value == null ? '' : "
                          "(datum.value < 0 ? '(' + datum.body + ')' : datum.body)")},
            ]},
    ]


SIGNALS = [
    {"name": "headerHeight", "value": HEADER_H},
    {"name": "labelWidth", "value": LABEL_W},
    {"name": "colWidth", "update": f"(width - labelWidth) / {N_COLS}"},
    {"name": "rowHeight", "update": f"(height - headerHeight) / {N_ROWS}"},
]

MARKS = [
    {"type": "rect", "name": "headerBand", "interactive": False,
     "encode": {"update": {
         "x": {"value": 0}, "x2": {"signal": "width"},
         "y": {"value": 0}, "y2": {"signal": "headerHeight"},
         "fill": {"value": BAND}}}},
    {"type": "text", "name": "headerLabels", "from": {"data": "colsReg"},
     "interactive": False,
     "encode": {"update": {
         "x": {"signal": "labelWidth + (datum.colIdx + 0.5) * colWidth"},
         "y": {"signal": "headerHeight / 2"},
         "align": {"value": "center"}, "baseline": {"value": "middle"},
         "text": {"field": "colLabel"},
         "font": {"value": FONT}, "fontSize": {"value": FONT_SIZE},
         "fontWeight": {"value": "bold"}, "fill": {"value": WHITE}}}},
    {"type": "rect", "name": "titleBands", "from": {"data": "titleRows"},
     "interactive": False,
     "encode": {"update": {
         "x": {"value": 0}, "x2": {"signal": "width"},
         "y": {"signal": "headerHeight + datum.rowIdx * rowHeight"},
         "height": {"signal": "rowHeight"},
         "fill": {"value": TITLE_BG}}}},
    {"type": "rule", "name": "gridRules", "from": {"data": "rowEdges"},
     "interactive": False,
     "encode": {"update": {
         "x": {"value": 0}, "x2": {"signal": "width"},
         # the last edge lands exactly on `height`, where a centred 1px stroke would render
         # half off-canvas -- pull it inside
         "y": {"signal": "min(headerHeight + datum.edge * rowHeight, height - 0.5)"},
         "stroke": {"value": GRID_H}, "strokeWidth": {"value": 1}}}},
    {"type": "text", "name": "rowLabels", "from": {"data": "rowsReg"},
     "interactive": False,
     "encode": {"update": {
         "x": {"signal": "datum.kind == 'title' ? 10 : 24"},
         "y": {"signal": "headerHeight + (datum.rowIdx + 0.5) * rowHeight"},
         "baseline": {"value": "middle"},
         "text": {"field": "label"},
         "font": {"value": FONT}, "fontSize": {"value": FONT_SIZE},
         "fontWeight": {"signal": "datum.kind == 'title' ? 'bold' : 'normal'"},
         "fill": {"value": INK},
         "limit": {"signal": "labelWidth - (datum.kind == 'title' ? 10 : 24) - 6"}}}},
    {"type": "text", "name": "cellText", "from": {"data": "cells"},
     "encode": {"update": {
         "x": {"signal": "labelWidth + (datum.colIdx + 1) * colWidth - 6"},
         "y": {"signal": "headerHeight + (datum.rowIdx + 0.5) * rowHeight"},
         "align": {"value": "right"}, "baseline": {"value": "middle"},
         "text": {"field": "fmtd"},
         "font": {"value": FONT}, "fontSize": {"value": FONT_SIZE},
         # variance rows only: green above zero, red below. Exactly zero and BLANK stay ink.
         "fill": {"signal": f"datum.isVar && datum.value != null && datum.value != 0"
                            f" ? (datum.value > 0 ? '{POS}' : '{NEG}') : '{INK}'"},
         "limit": {"signal": "colWidth - 8"},
         "tooltip": {"signal":
                     "{'Line': datum.rowLabel, 'Column': datum.colLabel,"
                     " 'Value': datum.fmtd == '' ? ', ' : datum.fmtd}"}}}},
]


def build_spec(inline_rows=None, fixed=None):
    return {
        "$schema": "https://vega.github.io/schema/vega/v6.json",
        "description": "Monthly P&L grid - one flat query, calculation group replaced by spec-side derivation",
        "background": WHITE,
        "padding": 0,
        "autosize": {"type": "none", "resize": True},
        # Height floors at NEED_H: a shorter container scrolls rather than crushing rows.
        # Width tracks the container, less the scrollbar gutter when that happens.
        "width": fixed[0] if fixed else
                 {"signal": f"pbiContainerWidth"
                            f" - (pbiContainerHeight < {NEED_H} ? {SCROLL_W} : 0)"},
        "height": fixed[1] if fixed else {"signal": f"max(pbiContainerHeight, {NEED_H})"},
        "signals": SIGNALS,
        "data": build_data(inline_rows),
        "marks": MARKS,
    }


# ---------------------------------------------------------------- sample rows
# Year 2026, current month = 8 (MonthOffset 0 in Aug 2026 on the lab calendar). Actuals stop
# after month 8 so the render exercises the future-month "(100.0%)" pattern; month 4 has
# CogLY = 0 (zero-denominator guard) and month 5 has OpxAct = null (blank-vs-0 guard).
def sample_rows():
    today_idx = 12 * 2026 + 8
    rows = []
    for m in range(1, 13):
        actual = m <= 8
        inc_ly = 6.5e8 + m * 4.0e7
        cog_ly = 0.0 if m == 4 else -inc_ly * 0.735
        gp_ly = inc_ly + cog_ly
        opx_ly = -inc_ly * 0.305
        np_ly = gp_ly + opx_ly
        inc_a = inc_ly * (1.04 + 0.002 * m) if actual else None
        cog_a = -inc_a * 0.729 if actual else None
        gp_a = (inc_a + cog_a) if actual else None
        opx_a = None if m == 5 else (-inc_a * 0.301 if actual else None)
        np_a = (gp_a + (opx_a or 0.0)) if actual else None
        rows.append({
            "Year": 2026, "Month": m, "MonthOffset": 12 * 2026 + m - today_idx,
            "IncAct": inc_a, "IncLY": inc_ly,
            "CogAct": cog_a, "CogLY": cog_ly,
            "GPAct": gp_a, "GPLY": gp_ly,
            "OpxAct": opx_a, "OpxLY": opx_ly,
            "NPAct": np_a, "NPLY": np_ly,
        })
    return rows


# ------------------------------------------------- expected cells (independent)
# Recomputes every cell in Python straight from the DAX rules -- NOT from the Vega
# transforms -- so verify_monthly.mjs is a genuine two-implementation diff.
def expected_cells(rows):
    def dsum(vals):
        vals = [v for v in vals if v is not None]
        return sum(vals) if vals else None

    def div(n, d):
        if d is None or d == 0 or n is None:
            return None
        return n / d

    def ndiv(n, d):
        r = div(n, d)
        return None if r is None else -r

    def dsub(a, b):
        if a is None and b is None:
            return None
        return (a or 0.0) - (b or 0.0)

    def var_pct(act, ly):
        if ly is None or ly == 0:
            return None
        return ((act or 0.0) - ly) / ly

    today_idx = {12 * r["Year"] + r["Month"] - r["MonthOffset"] for r in rows}
    assert len(today_idx) == 1
    cur_p = ((today_idx.pop() - 1) % 12) + 1

    cols = {}
    for r in rows:
        if 1 <= r["Month"] <= 12:
            cols[r["Month"] - 1] = {m: r[m] for m in MEASURES}
    for idx, sel in ((12, lambda r: r["Month"] <= cur_p),
                     (13, lambda r: r["Month"] > cur_p),
                     (14, lambda r: True)):
        cols[idx] = {m: dsum([r[m] for r in rows if sel(r)]) for m in MEASURES}

    def derive(c):
        gm_act = div(c["GPAct"], c["IncAct"])
        gm_ly = div(c["GPLY"], c["IncLY"])
        opr_act = ndiv(c["OpxAct"], c["IncAct"])
        opr_ly = ndiv(c["OpxLY"], c["IncLY"])
        return {
            "inc_act": c["IncAct"], "inc_ly": c["IncLY"],
            "inc_var": var_pct(c["IncAct"], c["IncLY"]),
            "cog_act": c["CogAct"], "cog_ly": c["CogLY"],
            "cog_var": var_pct(c["CogAct"], c["CogLY"]),
            "gp_act": c["GPAct"], "gp_ly": c["GPLY"],
            "gp_var": var_pct(c["GPAct"], c["GPLY"]),
            "gm_act": gm_act, "gm_ly": gm_ly, "gm_var": dsub(gm_act, gm_ly),
            "opx_act": c["OpxAct"], "opx_ly": c["OpxLY"],
            "opx_var": var_pct(c["OpxAct"], c["OpxLY"]),
            "opr_act": opr_act, "opr_ly": opr_ly, "opr_var": dsub(opr_act, opr_ly),
            "np_act": c["NPAct"], "np_ly": c["NPLY"],
            "np_var": var_pct(c["NPAct"], c["NPLY"]),
        }

    row_idx = {k: i for i, (k, _, f) in enumerate(ROWS) if f is not None}
    out = []
    for col_idx in sorted(cols):
        vals = derive(cols[col_idx])
        for k in DATA_KEYS:
            out.append({"rowIdx": row_idx[k], "colIdx": col_idx, "key": k, "value": vals[k]})
    return out


if __name__ == "__main__":
    rows = sample_rows()
    deneb = build_spec()
    preview = build_spec(inline_rows=rows, fixed=(1608, 740))

    (HERE / "monthly-pl.deneb.vg.json").write_text(json.dumps(deneb, indent=2), encoding="utf-8")
    (HERE / "monthly-pl.preview.vg.json").write_text(json.dumps(preview, indent=2), encoding="utf-8")
    (HERE / "monthly-pl.sample-rows.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    (HERE / "monthly-pl.expected.json").write_text(
        json.dumps(expected_cells(rows), indent=2), encoding="utf-8")
    (HERE / "monthly-pl.config.json").write_text(json.dumps(CONFIG, indent=2), encoding="utf-8")

    print(f"spec      : {len(json.dumps(deneb, separators=(',', ':')))} bytes minified")
    print(f"grid      : {N_ROWS} rows x {N_COLS} cols, {len(DATA_KEYS) * N_COLS} data cells")
    print(f"dataset   : 2 grouping columns + MonthOffset + {len(MEASURES)} base measures, "
          f"12 rows per selected year")
