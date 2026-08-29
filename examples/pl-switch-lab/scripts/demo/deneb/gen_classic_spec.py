# Generates pl_classic_spec.json -- the Deneb rendering of the CLASSIC 27-line P&L
# (the same statement as pages 2 and 3), adapted from the verified Odd Rows spec's
# layout (pl_spec.json).
#
# Dataset contract (display names, via displayName on the projections):
#   Line       string  27 distinct bridge lines; detail rows carry a 4 x U+00A0 indent
#   LineKey    number  10..270 step 10 -- the sort key
#   LineClass  string  Detail | Subtotal | Total
#   Actual, Budget, LY, "YTD Actual", "YTD Budget", "YTD LY"   the 6 base measures
#
# The 8 variance columns (Var, Var %, vs LY, vs LY %, + YTD forms) are derived in the
# spec, and all formatting is client-side -- so unlike every native page there is no
# dynamic-format-string tax at all.
#
# Styling: numbers/labels 14px near-black per Tim's request (2026-08-24); red negatives
# only on variance columns (accounting convention, matches the Odd Rows page).
import json
from pathlib import Path

OUT = Path(__file__).parent / "pl_classic_spec.json"

COLS = ["Actual", "Budget", "Var", "Var %", "LY", "vs LY", "vs LY %",
        "YTD Actual", "YTD Budget", "YTD Var", "YTD Var %", "YTD LY",
        "YTD vs LY", "YTD vs LY %"]
VAR_COLS = ["Var", "Var %", "vs LY", "vs LY %",
            "YTD Var", "YTD Var %", "YTD vs LY", "YTD vs LY %"]
N_ROWS, N_COLS = 27, 14

# palette -- darker than the first cut so the grid reads at a glance
INK = "#1F252D"        # default numbers / detail labels
INK_STRONG = "#05070A" # the Actual / YTD Actual emphasis columns
INK_TOTAL = "#000000"  # subtotal + total rows
HEADER = "#4A5361"
HEADER_STRONG = "#101418"
MUTED = "#5A6472"
RED = "#B42318"
RULE = "#9AA3AF"
DIVIDER = "#D3D8DF"

FS_CELL = 14
FS_HEADER = 12
FS_CAPTION = 11.5

def yscale():
    return {"domain": [N_ROWS, 0], "nice": False, "zero": False, "clamp": False}

def xscale():
    return {"domain": [0, N_COLS], "nice": False, "zero": False, "clamp": False}

def yq(field):
    return {"field": field, "type": "quantitative", "scale": yscale(),
            "axis": None, "title": None}

def xq(field):
    return {"field": field, "type": "quantitative", "scale": xscale(),
            "axis": None, "title": None}

transform = [
    # row order comes from LineKey, rank-normalised so the spec does not bake in the
    # 10-step key convention -- this is the template-friendly shape
    {"window": [{"op": "rank", "as": "rowRank"}],
     "sort": [{"field": "LineKey", "order": "ascending"}]},
    {"calculate": "datum.rowRank - 1", "as": "rowIdx"},
    # the 8 derived columns -- differences and ratios of the 6 base fields
    {"calculate": "datum['Actual'] - datum['Budget']", "as": "Var"},
    {"calculate": "(datum['Actual'] - datum['Budget']) / datum['Budget']", "as": "Var %"},
    {"calculate": "datum['Actual'] - datum['LY']", "as": "vs LY"},
    {"calculate": "(datum['Actual'] - datum['LY']) / datum['LY']", "as": "vs LY %"},
    {"calculate": "datum['YTD Actual'] - datum['YTD Budget']", "as": "YTD Var"},
    {"calculate": "(datum['YTD Actual'] - datum['YTD Budget']) / datum['YTD Budget']", "as": "YTD Var %"},
    {"calculate": "datum['YTD Actual'] - datum['YTD LY']", "as": "YTD vs LY"},
    {"calculate": "(datum['YTD Actual'] - datum['YTD LY']) / datum['YTD LY']", "as": "YTD vs LY %"},
    {"fold": COLS, "as": ["column", "value"]},
    {"calculate": "indexof(datum.column, '%') >= 0", "as": "isPctCol"},
    {"calculate": f"indexof({json.dumps(VAR_COLS)}, datum.column) >= 0", "as": "isVarCol"},
    {"calculate": "datum.LineClass !== 'Detail'", "as": "isSubtotal"},
    {"calculate": f"indexof({json.dumps(COLS)}, datum.column)", "as": "colIdx"},
    {"calculate": "datum.rowIdx + 0.5", "as": "rowMid"},
    {"calculate": "datum.rowIdx + 1", "as": "rowEnd"},
    {"calculate": "datum.colIdx + 1", "as": "colEnd"},
    {"calculate": "abs(datum.value)", "as": "absValue"},
    # money auto-scaled ($M / $K / $), percent columns .1% -- every classic row is money
    {"calculate": "datum.isPctCol ? format(datum.absValue, '.1%') : "
                  "(datum.absValue >= 999950 ? '$' + format(datum.absValue / 1000000, ',.1f') + 'M' : "
                  "(datum.absValue >= 999.5 ? '$' + format(datum.absValue / 1000, ',.1f') + 'K' : "
                  "'$' + format(datum.absValue, ',.0f')))",
     "as": "body"},
    {"calculate": "(!isValid(datum.value) || !isFinite(datum.value)) ? '' : "
                  "(datum.value < 0 ? '(' + datum.body + ')' : datum.body)",
     "as": "cell"},
    {"calculate": "-0.11", "as": "headerRuleY"},
]

layer = [
    {"description": "zebra banding on odd rows, spanning the label gutter and the grid",
     "transform": [{"filter": "datum.column === 'Actual' && datum.rowIdx % 2 === 1"}],
     "mark": {"type": "rect", "fill": "#161C24", "fillOpacity": 0.045,
              "x": -280, "x2": "width"},
     "encoding": {"y": yq("rowIdx"), "y2": {"field": "rowEnd"}}},

    {"description": "accent rule under the column headers",
     "transform": [{"filter": "datum.column === 'Actual' && datum.rowIdx === 0"}],
     "mark": {"type": "rule", "stroke": {"expr": "pbiColor(0)"}, "strokeWidth": 1.5,
              "opacity": 0.9, "x": -280, "x2": "width"},
     "encoding": {"y": yq("headerRuleY")}},

    {"description": "vertical dividers: end of the label gutter, and the period / YTD split",
     "transform": [{"filter": "datum.rowIdx === 0 && (datum.column === 'Actual' || datum.column === 'YTD Actual')"}],
     "mark": {"type": "rule", "stroke": DIVIDER, "y": -46},
     "encoding": {"x": xq("colIdx"),
                  "strokeWidth": {"condition": {"test": "datum.column === 'YTD Actual'",
                                                "value": 1.5}, "value": 1}}},

    {"description": "rule above each subtotal / total line",
     "transform": [{"filter": "datum.column === 'Actual' && datum.isSubtotal"}],
     "mark": {"type": "rule", "stroke": RULE, "strokeWidth": 1, "opacity": 0.8,
              "x": -280, "x2": "width"},
     "encoding": {"y": yq("rowIdx")}},

    {"description": "closing rule under the last row",
     "transform": [{"filter": f"datum.column === 'Actual' && datum.rowIdx === {N_ROWS - 1}"}],
     "mark": {"type": "rule", "stroke": RULE, "strokeWidth": 1, "opacity": 0.8,
              "x": -280, "x2": "width"},
     "encoding": {"y": yq("rowEnd")}},

    {"description": "half captions",
     "transform": [
         {"filter": "datum.rowIdx === 0 && (datum.column === 'Actual' || datum.column === 'YTD Actual')"},
         {"calculate": "datum.column === 'Actual' ? 'CURRENT PERIOD' : 'YEAR TO DATE'",
          "as": "groupLabel"}],
     "mark": {"type": "text", "align": "left", "baseline": "middle",
              "fontSize": FS_CAPTION, "fontWeight": 700,
              "fill": {"expr": "pbiColor(0)"}, "opacity": 0.95, "y": -38, "xOffset": 4},
     "encoding": {"x": xq("colIdx"), "text": {"field": "groupLabel", "type": "nominal"}}},

    {"description": "row-label gutter caption",
     "transform": [{"filter": "datum.rowIdx === 0 && datum.column === 'Actual'"}],
     "mark": {"type": "text", "align": "left", "baseline": "middle",
              "fontSize": FS_CAPTION, "fontWeight": 700, "fill": MUTED,
              "y": -38, "x": -276, "text": "STATEMENT LINE"},
     "encoding": {}},

    {"description": "column headers ('YTD ' stripped, the half caption already says it)",
     "transform": [
         {"filter": "datum.rowIdx === 0"},
         {"calculate": "indexof(datum.column, 'YTD ') === 0 ? slice(datum.column, 4) : datum.column",
          "as": "headerText"}],
     "mark": {"type": "text", "align": "right", "baseline": "middle",
              "fontSize": FS_HEADER, "y": -22, "xOffset": -11,
              "fontWeight": {"expr": "(datum.column === 'Actual' || datum.column === 'YTD Actual') ? 700 : 600"}},
     "encoding": {"x": xq("colEnd"), "text": {"field": "headerText", "type": "nominal"},
                  "fill": {"condition": {"test": "datum.column === 'Actual' || datum.column === 'YTD Actual'",
                                         "value": HEADER_STRONG},
                           "value": HEADER}}},

    {"description": "row labels in the left gutter -- indent is an explicit pixel offset "
                    "per LineClass, not the baked U+00A0 (whitespace survival through the "
                    "SVG pipeline is not guaranteed)",
     "transform": [{"filter": "datum.column === 'Actual'"},
                   {"calculate": "trim(replace(datum.Line, /\u00a0/g, ' '))", "as": "lineLabel"}],
     "mark": {"type": "text", "align": "left", "baseline": "middle",
              "fontSize": FS_CELL,
              "x": {"expr": "-276 + (datum.LineClass === 'Detail' ? 16 : 0)"},
              "limit": 300,
              "fontWeight": {"expr": "datum.isSubtotal ? 700 : 400"}},
     "encoding": {"y": yq("rowMid"), "text": {"field": "lineLabel", "type": "nominal"},
                  "fill": {"condition": {"test": "datum.isSubtotal", "value": INK_TOTAL},
                           "value": INK}}},

    {"description": "the 378 numbers",
     "mark": {"type": "text", "align": "right", "baseline": "middle",
              "fontSize": FS_CELL, "xOffset": -11,
              "fontWeight": {"expr": "datum.isSubtotal ? 700 : 400"}},
     "encoding": {"x": xq("colEnd"), "y": yq("rowMid"),
                  "text": {"field": "cell", "type": "nominal"},
                  "fill": {"condition": [
                      {"test": "datum.isVarCol && datum.value < 0", "value": RED},
                      {"test": "datum.isSubtotal", "value": INK_TOTAL},
                      {"test": "datum.column === 'Actual' || datum.column === 'YTD Actual'",
                       "value": INK_STRONG}],
                      "value": INK}}},

    {"description": "invisible full-cell rects so every cell is hoverable, blanks included",
     "mark": {"type": "rect", "fill": "#161C24", "fillOpacity": 0},
     "encoding": {"x": xq("colIdx"), "x2": {"field": "colEnd"},
                  "y": yq("rowIdx"), "y2": {"field": "rowEnd"},
                  "tooltip": [
                      {"field": "Line", "type": "nominal", "title": "Line"},
                      {"field": "column", "type": "nominal", "title": "Column"},
                      {"field": "cell", "type": "nominal", "title": "Value"},
                      {"field": "value", "type": "quantitative", "title": "Raw",
                       "format": ",.4f"}]}},
]

spec = {
    "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
    "data": {"name": "dataset"},
    "padding": {"left": 4, "top": 10, "right": 16, "bottom": 14},
    "transform": transform,
    "layer": layer,
}
OUT.write_text(json.dumps(spec, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"wrote {OUT.name}: {len(transform)} transforms, {len(layer)} layers")
