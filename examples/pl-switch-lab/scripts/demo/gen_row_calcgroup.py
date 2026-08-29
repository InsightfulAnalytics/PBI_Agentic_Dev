# Emits 'P&L Row' -- candidate E: a SECOND calculation group used as the ROW axis of the
# Odd Rows P&L, so the matrix becomes rows = 'P&L Row', columns = 'P&L View',
# values = ONE measure ([NM Amount]). No SWITCH, no field parameter.
#
# PRECEDENCE. Microsoft Learn's substitution algorithm: the HIGHEST precedence item is the
# OUTER wrapper, and its SELECTEDMEASURE() is replaced by the next-highest item, recursively.
# 'P&L View' (the column group, scenario + time) is precedence 10 and MUST stay outer, so
# 'P&L Row' gets precedence 5. Getting this backwards silently breaks two whole classes of row:
#   - ratio rows would compute DIVIDE(GP - GP_LY, TI - TI_LY) instead of GM%_now - GM%_LY
#   - 'Trading Stores' contains NO measure reference, so as the OUTER item the column group
#     would have nothing to rewrite and every one of its 14 columns would return the same
#     current-period count, with no error.
# As the INNER item it is substituted into the column item's CALCULATE and shifts correctly.
#
# No explicit "ordinal:" -- verified 2026-08-24 that TMDL folder deserialisation assigns
# calculation-item ordinals from DECLARATION ORDER (the shipped 'P&L View' carries none and
# still parses to 0..13), and Desktop strips explicit ordinals on save. File order IS the order.
import uuid
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / "PL Bridge Demo.SemanticModel" / "definition" / "tables" / "P&L Row.tmdl"
MODEL = Path(__file__).resolve().parents[2] / "PL Bridge Demo.SemanticModel" / "definition" / "model.tmdl"

def tag(s):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "plbridgedemo/row/" + s))

SM = "SELECTEDMEASURE ( )"
def line(n):
    return f"CALCULATE ( {SM}, 'P&L Lines'[Line] = \"{n}\" )"

STORES = "DISTINCTCOUNT ( 'Financials'[StoreKey] )"
PRODS = ("CALCULATE (\n    DISTINCTCOUNT ( 'Financials'[ProductKey] ),\n"
         "    'Financials'[ProductKey] <> 0\n)")

# (name, expression, is_percent, is_count)
ITEMS = [
    ("Total Income",             line("Total Income"), False, False),
    ("Total Cost of Sales",      line("Total Cost of Sales"), False, False),
    ("Gross Profit",             line("Gross Profit"), False, False),
    ("Total Operating Expenses", line("Total Operating Expenses"), False, False),
    ("Net Profit",               line("Net Profit"), False, False),
    ("Gross Margin %",
     f"DIVIDE (\n    {line('Gross Profit')},\n    {line('Total Income')}\n)", True, False),
    ("Net Margin %",
     f"DIVIDE (\n    {line('Net Profit')},\n    {line('Total Income')}\n)", True, False),
    ("COGS % of Income",
     f"DIVIDE (\n    - {line('Total Cost of Sales')},\n    {line('Total Income')}\n)", True, False),
    ("Opex % of Income",
     f"DIVIDE (\n    - {line('Total Operating Expenses')},\n    {line('Total Income')}\n)", True, False),
    ("Income per Trading Store",
     f"DIVIDE (\n    {line('Total Income')},\n    {STORES}\n)", False, False),
    ("Net Profit per Trading Store",
     f"DIVIDE (\n    {line('Net Profit')},\n    {STORES}\n)", False, False),
    ("Income per Active Product",
     f"DIVIDE (\n    {line('Total Income')},\n    {PRODS}\n)", False, False),
    ("Trading Stores", STORES, False, True),
]
assert len(ITEMS) == 13

out = ["table 'P&L Row'", f"\tlineageTag: {tag('table')}", "",
       "\tcalculationGroup", "\t\tprecedence: 5", ""]
for name, expr, is_pct, is_count in ITEMS:
    out.append(f"\t\tcalculationItem '{name}' =")
    out.append("")
    out.extend("\t\t\t\t" + l if l else "" for l in expr.split("\n"))
    out.append("")
    if is_pct:
        fsd = '"0.0%;(0.0%)"'
    elif is_count:
        fsd = '"#,##0;(#,##0)"'
    else:
        fsd = "Fmt.Money ( SELECTEDMEASURE ( ) )"
    out.append(f"\t\t\tformatStringDefinition = {fsd}")
    out.append("")

out += [
    "\tcolumn 'P&L Row'",
    "\t\tdataType: string",
    f"\t\tlineageTag: {tag('col/row')}",
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
]
OUT.write_text("\n".join(out), encoding="utf-8", newline="\r\n")
print(f"wrote {OUT.name}: 13 items, precedence 5")

# register the table in model.tmdl (idempotent, insert before the cultureInfo ref)
m = MODEL.read_text(encoding="utf-8")
if "ref table 'P&L Row'" not in m:
    anchor = "ref table 'P&L View'"
    assert anchor in m
    m = m.replace(anchor, anchor + "\nref table 'P&L Row'", 1)
    MODEL.write_text(m, encoding="utf-8")
    print("registered 'P&L Row' in model.tmdl")
else:
    print("'P&L Row' already registered")
