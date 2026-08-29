# Emits the "Odd Rows P&L" objects for PL Bridge Demo (DEMO-SPEC.md addendum 3):
#   definition\functions.tmdl              -- DAX UDFs for format strings (needs compat 1702)
#   definition\tables\P&L View.tmdl        -- calculation group: the 14 COLUMN variants
#   definition\tables\P&L Odd Rows Fields.tmdl   -- field parameter: the 13 ROW lines
#   00_Measures.tmdl                       -- 1 base + 13 row measures (folder 06)
#
# 13 rows x 14 columns = 182 cells from 14 measures + 14 calc items. The point:
# neither axis is a SWITCH, so nothing branches per cell.
#
# Design rule that makes the calc group work: the row measures are deliberately
# SCENARIO- and TIME-agnostic. The calculation group owns scenario and time. If a
# row measure baked in 'Financials'[Scenario]="Actual", that inner CALCULATE would
# beat the calc item's outer filter and the Budget column would silently show Actual.
import re
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "PL Bridge Demo.SemanticModel" / "definition"
MEASURES = ROOT / "tables" / "00_Measures.tmdl"

def tag(name):
    # FROZEN. This string is hash INPUT, never a label -- it is what makes the generator
    # reproduce the lineageTags already in the shipped model. It still spells the demo's
    # old name on purpose: renaming it silently rewrites every tag in the table.
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "plbridgedemo/nightmare/" + name))

# ---------------------------------------------------------------- row measures
# (label, measure name, expression lines, format string, kind)
MONEY = "$#,##0"
PCT = "0.0%"
COUNT = "#,##0;(#,##0)"  # explicit negative section: variances on the count row can go negative

def line(sub):
    return f'CALCULATE ( [NM Amount], \'P&L Lines\'[Line] = "{sub}" )'

ROWS = [
    ("Total Income", "NM Total Income", [line("Total Income")], MONEY),
    ("Total Cost of Sales", "NM Total Cost of Sales", [line("Total Cost of Sales")], MONEY),
    ("Gross Profit", "NM Gross Profit", [line("Gross Profit")], MONEY),
    ("Total Operating Expenses", "NM Total Operating Expenses", [line("Total Operating Expenses")], MONEY),
    ("Net Profit", "NM Net Profit", [line("Net Profit")], MONEY),
    # --- odd lines: ratios (no account can express these) ---
    ("Gross Margin %", "NM Gross Margin %",
     ["DIVIDE ( [NM Gross Profit], [NM Total Income] )"], PCT),
    ("Net Margin %", "NM Net Margin %",
     ["DIVIDE ( [NM Net Profit], [NM Total Income] )"], PCT),
    ("COGS % of Income", "NM COGS % of Income",
     ["DIVIDE ( - [NM Total Cost of Sales], [NM Total Income] )"], PCT),
    ("Opex % of Income", "NM Opex % of Income",
     ["DIVIDE ( - [NM Total Operating Expenses], [NM Total Income] )"], PCT),
    # --- odd lines: per-unit ---
    ("Income per Trading Store", "NM Income per Trading Store",
     ["DIVIDE ( [NM Total Income], [NM Trading Stores] )"], MONEY),
    ("Net Profit per Trading Store", "NM Net Profit per Trading Store",
     ["DIVIDE ( [NM Net Profit], [NM Trading Stores] )"], MONEY),
    ("Income per Active Product", "NM Income per Active Product",
     ["DIVIDE (",
      "    [NM Total Income],",
      "    // ProductKey 0 is the sentinel for the 19 non-product accounts, not a product",
      "    CALCULATE (",
      "        DISTINCTCOUNT ( 'Financials'[ProductKey] ),",
      "        'Financials'[ProductKey] <> 0",
      "    )",
      ")"], MONEY),
    # --- odd line: a plain count, a third format class ---
    ("Trading Stores", "NM Trading Stores",
     ["DISTINCTCOUNT ( 'Financials'[StoreKey] )"], COUNT),
]
assert len(ROWS) == 13

BASE = ("NM Amount", [
    "// deliberately scenario- and time-agnostic: the calculation group owns both",
    "SUM ( 'Financials'[Amount] )",
], MONEY)

# ------------------------------------------------------------- calc group items
def act(ytd):
    inner = "SELECTEDMEASURE ( ), 'Financials'[Scenario] = \"Actual\""
    if ytd:
        inner += ", DATESYTD ( 'DimDate'[Date] )"
    return f"CALCULATE ( {inner} )"

def bud(ytd):
    inner = "SELECTEDMEASURE ( ), 'Financials'[Scenario] = \"Budget\""
    if ytd:
        inner += ", DATESYTD ( 'DimDate'[Date] )"
    return f"CALCULATE ( {inner} )"

def ly(ytd):
    # shift the whole context back a year, THEN evaluate (nested CALCULATE is the
    # safe form -- two date filters as siblings would intersect, not shift)
    return (f"CALCULATE (\n    {act(ytd)},\n    DATEADD ( 'DimDate'[Date], -1, YEAR )\n)")

def pair(a_expr, b_expr, pct):
    body = [
        "VAR __A =",
        *["    " + l for l in a_expr.split("\n")],
        "VAR __B =",
        *["    " + l for l in b_expr.split("\n")],
        "RETURN",
    ]
    body.append("    DIVIDE ( __A - __B, __B )" if pct else "    __A - __B")
    return "\n".join(body)

# (name, ordinal, expression, is_percent_result)
ITEMS = []
for ytd in (False, True):
    p = "YTD " if ytd else ""
    ITEMS += [
        (f"{p}Actual", act(ytd), False),
        (f"{p}LY", ly(ytd), False),
        (f"{p}vs LY", pair(act(ytd), ly(ytd), False), False),
        (f"{p}vs LY %", pair(act(ytd), ly(ytd), True), True),
        (f"{p}Budget", bud(ytd), False),
        (f"{p}Var to Budget", pair(act(ytd), bud(ytd), False), False),
        (f"{p}Var to Budget %", pair(act(ytd), bud(ytd), True), True),
    ]
assert len(ITEMS) == 14

# ------------------------------------------------------------------- functions
FUNCTIONS = '''/// Money format string, auto-scaled: >=1M shows $x.xM, >=1K shows $x.xK.
/// @param {NUMERIC} val - the value being formatted
/// @returns a VBA-style format string
function 'Fmt.Money' =

		(val: NUMERIC) =>
		    // thresholds sit just under the round number so a value that would
		    // render as "1,000.0K" tips into the M branch instead
		    SWITCH (
		        TRUE ( ),
		        ABS ( val ) >= 999950, "$#,##0,,.0""M"";($#,##0,,.0""M"")",
		        ABS ( val ) >= 999.5, "$#,##0,.0""K"";($#,##0,.0""K"")",
		        "$#,##0;($#,##0)"
		    )

/// The one format rule for the whole P&L: percent rows stay percent, money rows
/// auto-scale, anything else keeps the measure's own format. Called from every
/// calculation item instead of repeating the logic 14 times.
/// @param {NUMERIC} val - the value being formatted
/// @param baseFormat - the row measure's own format string
/// @returns a VBA-style format string
function 'Fmt.PL' =

		(val: NUMERIC, baseFormat) =>
		    SWITCH (
		        TRUE ( ),
		        CONTAINSSTRING ( baseFormat, "%" ), "0.0%;(0.0%)",
		        CONTAINSSTRING ( baseFormat, "$" ), Fmt.Money ( val ),
		        baseFormat
		    )
'''

# -------------------------------------------------------------- emit calc group
cg = ["table 'P&L View'", f"\tlineageTag: {tag('table/view')}", "", "\tcalculationGroup", "\t\tprecedence: 10", ""]
for ordinal, (name, expr, is_pct) in enumerate(ITEMS):
    cg.append(f"\t\tcalculationItem '{name}' =")
    cg.append("")
    cg.extend("\t\t\t\t" + l if l else "" for l in expr.split("\n"))
    # WITHOUT an explicit ordinal every item defaults to -1, so the column order is
    # encoded nowhere and the statement is at the mercy of name ordering.
    cg.append(f"\t\t\tordinal: {ordinal}")
    cg.append("")
    if is_pct:
        cg.append('\t\t\tformatStringDefinition = "0.0%;(0.0%)"')
    else:
        cg.append("\t\t\tformatStringDefinition = Fmt.PL ( SELECTEDMEASURE ( ), SELECTEDMEASUREFORMATSTRING ( ) )")
    cg.append("")
cg += [
    "\tcolumn 'P&L View'",
    "\t\tdataType: string",
    f"\t\tlineageTag: {tag('col/view')}",
    "\t\tsummarizeBy: none",
    "\t\tsourceColumn: Name",
    "\t\tsortByColumn: Ordinal",
    "",
    "\t\tannotation SummarizationSetBy = Automatic",
    "",
    "\tcolumn Ordinal",
    "\t\tdataType: int64",
    "\t\tisHidden",
    "\t\tformatString: 0",
    f"\t\tlineageTag: {tag('col/ordinal')}",
    "\t\tsummarizeBy: none",
    "\t\tsourceColumn: Ordinal",
    "",
    "\t\tannotation SummarizationSetBy = Automatic",
    "",
    "\tpartition 'P&L View' = calculationGroup",
    "\t\tmode: import",
    "",
]

# --------------------------------------------------------- emit field parameter
rows_dax = ",\n".join(
    f'\t\t\t\t    ("{label}", NAMEOF(\'00_Measures\'[{mname}]), {i})'
    for i, (label, mname, _, _) in enumerate(ROWS)
)
fp = f"""table 'P&L Odd Rows Fields'
	lineageTag: {tag('table/odd rows')}

	column 'Odd Rows Line'
		dataType: string
		lineageTag: {tag('col/line')}
		summarizeBy: none
		sourceColumn: [Value1]
		sortByColumn: 'Odd Rows Line Order'

		relatedColumnDetails
			groupByColumn: 'Odd Rows Line Fields'

		annotation SummarizationSetBy = Automatic

	column 'Odd Rows Line Fields'
		dataType: string
		isHidden
		lineageTag: {tag('col/fields')}
		summarizeBy: none
		sourceColumn: [Value2]
		sortByColumn: 'Odd Rows Line Order'

		extendedProperty ParameterMetadata = {{"version":3,"kind":2}}

		annotation SummarizationSetBy = Automatic

	column 'Odd Rows Line Order'
		dataType: int64
		isHidden
		formatString: 0
		lineageTag: {tag('col/order')}
		summarizeBy: none
		sourceColumn: [Value3]

		annotation SummarizationSetBy = Automatic

	partition 'P&L Odd Rows Fields' = calculated
		source =
				{{
{rows_dax}
				}}

	annotation PBI_ResultType = Table
"""

# ---------------------------------------------------------------- emit measures
FOLDER = "06 Odd Rows P&L"
mparts = []

def emit_measure(name, body, fmt, desc):
    mparts.append(f"\t/// {desc}")
    mparts.append(f"\tmeasure '{name}' =")
    mparts.append("")
    mparts.extend("\t\t\t" + l for l in body)
    mparts.append(f"\t\tformatString: {fmt}")
    mparts.append(f"\t\tdisplayFolder: {FOLDER}")
    mparts.append(f"\t\tlineageTag: {tag('measure/' + name)}")
    mparts.append("")

emit_measure(BASE[0], BASE[1], BASE[2],
             "Scenario- and time-agnostic base. The calculation group supplies both.")
for label, mname, body, fmt in ROWS:
    if fmt == PCT:
        desc = "Ratio line - no set of accounts can express it."
    elif mname == "NM Trading Stores":
        desc = "A count line - a third format class for the format UDF to handle."
    elif "per " in mname:
        desc = "Per-unit line - no set of accounts can express it."
    else:
        desc = "Account-backed line: one filter on the bridge, no SWITCH."
    emit_measure(mname, body, fmt, desc)

# -------------------------------------------------------------- write everything
(ROOT / "functions.tmdl").write_text(FUNCTIONS, encoding="utf-8", newline="\r\n")
(ROOT / "tables" / "P&L View.tmdl").write_text("\n".join(cg), encoding="utf-8", newline="\r\n")
(ROOT / "tables" / "P&L Odd Rows Fields.tmdl").write_text(fp, encoding="utf-8", newline="\r\n")

# Strip-and-reinsert by measure NAME, never by line position: Power BI Desktop
# re-serialises 00_Measures.tmdl on save and reorders the measures, so a positional
# start/end pair can invert and silently duplicate half the file.
lines = MEASURES.read_text(encoding="utf-8").replace("\r\n", "\n").split("\n")
decl = [i for i, l in enumerate(lines) if l.startswith("\tmeasure '")]
part = next(i for i, l in enumerate(lines) if l.startswith("\tpartition 00_Measures-"))

def block_start(i):
    while i > 0 and lines[i - 1].startswith("\t///"):
        i -= 1
    return i

blocks = []  # (name, [lines])
for k, i in enumerate(decl):
    s = block_start(i)
    e = block_start(decl[k + 1]) if k + 1 < len(decl) else part
    blocks.append((re.match(r"\tmeasure '([^']+)'", lines[i]).group(1), lines[s:e]))

generated = {BASE[0]} | {m for _, m, _, _ in ROWS}
before = len(blocks)
blocks = [b for b in blocks if b[0] not in generated]
if before != len(blocks):
    print(f"stripped {before - len(blocks)} previously generated measures")

head = lines[: block_start(decl[0])]
body = [l for _, blk in blocks for l in blk]
out = head + mparts + body + lines[part:]
MEASURES.write_text("\n".join(out), encoding="utf-8", newline="\r\n")

kept = len(re.findall(r"(?m)^\tmeasure '", "\n".join(out)))
assert kept == len(blocks) + len(generated), f"measure count drift: {kept}"

# model.tmdl refs
model = ROOT / "model.tmdl"
mt = model.read_text(encoding="utf-8").replace("\r\n", "\n")
for t in ("'P&L View'", "'P&L Odd Rows Fields'"):
    if f"ref table {t}" not in mt:
        mt = mt.replace("\nref cultureInfo", f"\nref table {t}\n\nref cultureInfo", 1) \
            if f"ref table {t}" not in mt else mt
model.write_text(mt, encoding="utf-8", newline="\r\n")

total = sum(1 for l in MEASURES.read_text(encoding="utf-8").split("\n") if l.startswith("\tmeasure '"))
print(f"OK: functions.tmdl (2 UDFs), 'P&L View' ({len(ITEMS)} calc items), "
      f"'P&L Odd Rows Fields' ({len(ROWS)} param rows), {len(ROWS) + 1} measures")
print(f"00_Measures now defines {total} measures")
print(f"grid = {len(ROWS)} rows x {len(ITEMS)} cols = {len(ROWS) * len(ITEMS)} cells "
      f"from {len(ROWS) + 1} measures + {len(ITEMS)} calc items")
