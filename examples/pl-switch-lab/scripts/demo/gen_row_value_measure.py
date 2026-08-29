# Emits [NM Row Value] -- the single dispatch measure behind the rebuilt page 6
# ("Odd Rows P&L", candidate D). One 13-branch SWITCH over the disconnected
# 'P&L Odd Rows' table, evaluated once per cell instead of thirteen explicit
# measures each evaluated across the 14-item calculation-group column axis.
#
# Measured 2026-08-24: 489 ms warm vs 803 ms for the field-parameter design it replaces.
# The leaf measures are the same [NM ...] measures, so the numbers are unchanged
# (tied out at 182/182 against scripts\demo\_golden_182.csv).
#
# The row label is resolved ONCE into __Line and reused by every branch, per the
# house rule applied to every SWITCH measure in this model.
import re
import uuid
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / "PL Bridge Demo.SemanticModel" / "definition" / "tables" / "00_Measures.tmdl"
NAME = "NM Row Value"
SEL = "SELECTEDVALUE ( 'P&L Odd Rows'[Line] )"

ROWS = [
    "Total Income", "Total Cost of Sales", "Gross Profit",
    "Total Operating Expenses", "Net Profit",
    "Gross Margin %", "Net Margin %", "COGS % of Income", "Opex % of Income",
    "Income per Trading Store", "Net Profit per Trading Store",
    "Income per Active Product", "Trading Stores",
]
PCT = ["Gross Margin %", "Net Margin %", "COGS % of Income", "Opex % of Income"]
COUNT = ["Trading Stores"]

body = [f"VAR __Line = {SEL}", "RETURN", "SWITCH (", "    __Line,"]
for r in ROWS:
    body.append(f'    "{r}", [NM {r}],')
body[-1] = body[-1][:-1]
body.append(")")

qs = lambda xs: "{ " + ", ".join(f'"{x}"' for x in xs) + " }"
fsd = (f"VAR __Line = {SEL} RETURN SWITCH ( TRUE ( ), "
       f'__Line IN {qs(PCT)}, "0.0%;(0.0%)", '
       f'__Line IN {qs(COUNT)}, "#,##0;(#,##0)", '
       f"Fmt.Money ( [{NAME}] ) )")

block = [
    "\t/// Single dispatch measure for the Odd Rows P&L. One 13-branch SWITCH replaces",
    "\t/// thirteen explicit row measures: same leaf measures, same 182 cells, ~40% less time.",
    f"\tmeasure '{NAME}' =",
    "",
]
block += [f"\t\t\t{l}" for l in body]
block += [
    "\t\tdisplayFolder: 06 Odd Rows P&L",
    f"\t\tlineageTag: {uuid.uuid5(uuid.NAMESPACE_URL, 'plbridgedemo/' + NAME)}",
    "",
    f"\t\tformatStringDefinition = {fsd}",
    "",
]

# ---- strip-and-reinsert by NAME (never by line position) ----
lines = OUT.read_text(encoding="utf-8").replace("\r\n", "\n").split("\n")
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

before = len(blocks)
blocks = [b for b in blocks if b[0] != NAME]
print(f"stripped {before - len(blocks)} existing '{NAME}'")

head = lines[: block_start(decl[0])]
out_lines = head + block + [l for _, b in blocks for l in b] + lines[part:]
OUT.write_text("\n".join(out_lines), encoding="utf-8", newline="\r\n")

total = sum(1 for l in out_lines if l.startswith("\tmeasure '"))
assert total == len(blocks) + 1, f"measure count drift: {total}"
print(f"OK: 00_Measures now defines {total} measures")
