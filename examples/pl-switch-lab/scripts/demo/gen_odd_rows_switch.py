# The SWITCH counterpart of the Odd Rows P&L, as SHIPPED model objects so it can be
# bound to a visual and timed like-for-like against page 6.
#   definition\tables\P&L Odd Rows.tmdl  -- disconnected 13-row axis
#   00_Measures.tmdl                           -- 14 x 13-branch SWITCH measures (folder 07)
#
# Deliberately GENEROUS to the SWITCH side: every branch calls the same efficient,
# scenario-agnostic [NM ...] leaf measures the calculation-group version uses, so the
# ONLY variable between page 6 and page 7 is how a cell is dispatched.
#
# Format strings: the calc group gets per-row formats for free. A single SWITCH measure
# spans money, percent and count rows, so it has to branch AGAIN inside its own
# formatStringDefinition to match -- shown here rather than hidden, because that second
# switch is part of the real cost of this approach.
import re
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "PL Bridge Demo.SemanticModel" / "definition"
MEASURES = ROOT / "tables" / "00_Measures.tmdl"
FOLDER = "07 Odd Rows SWITCH"

def tag(name):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "plbridgedemo/switch/" + name))

# (row label, leaf measure) -- byte-identical labels to the 'P&L Odd Rows Fields' field parameter
ROWS = [
    ("Total Income", "NM Total Income"),
    ("Total Cost of Sales", "NM Total Cost of Sales"),
    ("Gross Profit", "NM Gross Profit"),
    ("Total Operating Expenses", "NM Total Operating Expenses"),
    ("Net Profit", "NM Net Profit"),
    ("Gross Margin %", "NM Gross Margin %"),
    ("Net Margin %", "NM Net Margin %"),
    ("COGS % of Income", "NM COGS % of Income"),
    ("Opex % of Income", "NM Opex % of Income"),
    ("Income per Trading Store", "NM Income per Trading Store"),
    ("Net Profit per Trading Store", "NM Net Profit per Trading Store"),
    ("Income per Active Product", "NM Income per Active Product"),
    ("Trading Stores", "NM Trading Stores"),
]
PCT_ROWS = ["Gross Margin %", "Net Margin %", "COGS % of Income", "Opex % of Income"]
COUNT_ROWS = ["Trading Stores"]
SEL = "SELECTEDVALUE ( 'P&L Odd Rows'[Line] )"

def act(leaf, ytd):
    y = ", DATESYTD ( 'DimDate'[Date] )" if ytd else ""
    return f"CALCULATE ( [{leaf}], 'Financials'[Scenario] = \"Actual\"{y} )"

def bud(leaf, ytd):
    y = ", DATESYTD ( 'DimDate'[Date] )" if ytd else ""
    return f"CALCULATE ( [{leaf}], 'Financials'[Scenario] = \"Budget\"{y} )"

def ly(leaf, ytd):
    return f"CALCULATE ( {act(leaf, ytd)}, DATEADD ( 'DimDate'[Date], -1, YEAR ) )"

def maker(kind, ytd):
    return {
        "Actual":          lambda lf: act(lf, ytd),
        "LY":              lambda lf: ly(lf, ytd),
        "vs LY":           lambda lf: f"{act(lf, ytd)} - {ly(lf, ytd)}",
        "vs LY %":         lambda lf: f"DIVIDE ( {act(lf, ytd)} - {ly(lf, ytd)}, {ly(lf, ytd)} )",
        "Budget":          lambda lf: bud(lf, ytd),
        "Var to Budget":   lambda lf: f"{act(lf, ytd)} - {bud(lf, ytd)}",
        "Var to Budget %": lambda lf: f"DIVIDE ( {act(lf, ytd)} - {bud(lf, ytd)}, {bud(lf, ytd)} )",
    }[kind]

KINDS = ["Actual", "LY", "vs LY", "vs LY %", "Budget", "Var to Budget", "Var to Budget %"]
COLS = [(f"{'YTD ' if y else ''}{k}", k, y) for y in (False, True) for k in KINDS]
assert len(COLS) == 14

def quoted_set(items):
    return "{ " + ", ".join(f'"{i}"' for i in items) + " }"

parts = []
for label, kind, ytd in COLS:
    name = f"Slow NM {label}"
    f = maker(kind, ytd)
    # resolve the row label ONCE, then reuse it in all 13 comparisons
    body = [f"VAR __Line = {SEL}", "RETURN", "SWITCH (", "    TRUE ( ),"]
    for rlabel, leaf in ROWS:
        body.append(f'    __Line = "{rlabel}",')
        body.append(f"        {f(leaf)},")
    body[-1] = body[-1].rstrip(",")
    body.append(")")

    is_pct_col = kind.endswith("%")
    parts.append(f"\t/// SWITCH counterpart of the calculation item '{label}' -- 13 branches.")
    parts.append(f"\tmeasure '{name}' =")
    parts.append("")
    parts.extend("\t\t\t" + l for l in body)
    if is_pct_col:
        parts.append('\t\tformatString: 0.0%;(0.0%)')
    parts.append(f"\t\tdisplayFolder: {FOLDER}")
    parts.append(f"\t\tlineageTag: {tag(name)}")
    parts.append("")
    if not is_pct_col:
        # the second switch: one measure spans money, percent and count rows
        parts.append(
            f"		formatStringDefinition = VAR __Line = {SEL} RETURN "
            f"SWITCH ( TRUE ( ), __Line IN {quoted_set(PCT_ROWS)}, "
            f'"0.0%;(0.0%)", __Line IN {quoted_set(COUNT_ROWS)}, "#,##0;(#,##0)", '
            f"Fmt.Money ( [{name}] ) )")
        parts.append("")

# ---- the disconnected row axis -------------------------------------------------
rows_m = ",\n".join(f'\t\t\t\t        {{"{lb}", {i}}}' for i, (lb, _) in enumerate(ROWS))
table = f"""table 'P&L Odd Rows'
	lineageTag: {tag('table')}

	column Line
		dataType: string
		lineageTag: {tag('col/line')}
		summarizeBy: none
		sourceColumn: Line
		sortByColumn: Sort

		changedProperty = SortByColumn

		annotation SummarizationSetBy = Automatic

	column Sort
		dataType: int64
		isHidden
		formatString: 0
		lineageTag: {tag('col/sort')}
		summarizeBy: none
		sourceColumn: Sort

		annotation SummarizationSetBy = Automatic

	partition 'P&L Odd Rows' = m
		mode: import
		source =
				let
				    Source = Table.FromRows({{
{rows_m}
				    }}, type table [Line = Text.Type, Sort = Int64.Type])
				in
				    Source

	annotation PBI_ResultType = Table
"""
(ROOT / "tables" / "P&L Odd Rows.tmdl").write_text(table, encoding="utf-8", newline="\r\n")

# ---- strip-and-reinsert by NAME (never by line position) -----------------------
lines = MEASURES.read_text(encoding="utf-8").replace("\r\n", "\n").split("\n")
decl = [i for i, l in enumerate(lines) if l.startswith("\tmeasure '")]
part = next(i for i, l in enumerate(lines) if l.startswith("\tpartition 00_Measures-"))

def block_start(i):
    while i > 0 and lines[i - 1].startswith("\t///"):
        i -= 1
    return i

blocks = []
for k, i in enumerate(decl):
    s = block_start(i)
    e = block_start(decl[k + 1]) if k + 1 < len(decl) else part
    blocks.append((re.match(r"\tmeasure '([^']+)'", lines[i]).group(1), lines[s:e]))

generated = {f"Slow NM {lb}" for lb, _, _ in COLS}
before = len(blocks)
blocks = [b for b in blocks if b[0] not in generated]
if before != len(blocks):
    print(f"stripped {before - len(blocks)} previously generated measures")

head = lines[: block_start(decl[0])]
out = head + parts + [l for _, blk in blocks for l in blk] + lines[part:]
MEASURES.write_text("\n".join(out), encoding="utf-8", newline="\r\n")
kept = len(re.findall(r"(?m)^\tmeasure '", "\n".join(out)))
assert kept == len(blocks) + len(generated), f"measure count drift: {kept}"

# ---- model.tmdl ref -------------------------------------------------------------
model = ROOT / "model.tmdl"
mt = model.read_text(encoding="utf-8").replace("\r\n", "\n")
if "ref table 'P&L Odd Rows'" not in mt:
    mt = mt.replace("\nref cultureInfo", "\nref table 'P&L Odd Rows'\n\nref cultureInfo", 1)
    model.write_text(mt, encoding="utf-8", newline="\r\n")

print(f"OK: 'P&L Odd Rows' ({len(ROWS)} rows), {len(COLS)} SWITCH measures "
      f"x {len(ROWS)} branches = {len(COLS) * len(ROWS)} branches")
print(f"00_Measures now defines {kept} measures")
