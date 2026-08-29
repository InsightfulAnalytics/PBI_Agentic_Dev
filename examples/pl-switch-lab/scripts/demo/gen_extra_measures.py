# Extra measures needed by the two new Odd Rows pages.
#
#  [NM CG Value]           -- the Values-well measure for page 8 (candidate E, two calculation
#                             groups). Numerically it is just [NM Amount]; it exists only to
#                             carry a dynamic format string keyed on the ROW calculation group.
#                             Needed because 'P&L View' has the higher precedence, so ITS
#                             formatStringDefinition wins and Fmt.PL only ever sees the BASE
#                             measure's format string -- the row group's own format strings are
#                             never consulted. Without this the four % rows and the count row
#                             render as money.
#  [NM Stores All Lines]   -- distinct store count with the bridge filter removed.
#  [NM Products All Lines] -- distinct active-product count with the bridge filter removed.
#                             Both are for page 9 (Deneb): its dataset GROUPS BY 'P&L Lines'[Line],
#                             so without REMOVEFILTERS they would count only the stores/products
#                             that transacted on that statement line and every per-unit row
#                             derived from them would be wrong.
import re
import uuid
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / "PL Bridge Demo.SemanticModel" / "definition" / "tables" / "00_Measures.tmdl"

PCT = ["Gross Margin %", "Net Margin %", "COGS % of Income", "Opex % of Income"]
CNT = ["Trading Stores"]
qs = lambda xs: "{ " + ", ".join(f'"{x}"' for x in xs) + " }"

CG_FSD = (f"VAR __Row = SELECTEDVALUE ( 'P&L Row'[P&L Row] ) RETURN SWITCH ( TRUE ( ), "
          f'__Row IN {qs(PCT)}, "0.0%;(0.0%)", '
          f'__Row IN {qs(CNT)}, "#,##0;(#,##0)", '
          f'"$#,##0;($#,##0)" )')

MEASURES = [
    ("NM CG Value",
     ["// numerically identical to [NM Amount]; exists to carry the row-aware format string",
      "[NM Amount]"],
     "06 Odd Rows P&L",
     ["/// Values-well measure for the two-calculation-group page. Same number as [NM Amount];",
      "/// the point is the dynamic format string, which reads the ROW calculation group."],
     CG_FSD, None),
    ("NM Stores All Lines",
     ["CALCULATE ( [NM Trading Stores], REMOVEFILTERS ( 'P&L Lines' ) )"],
     "06 Odd Rows P&L",
     ["/// Distinct trading stores, ignoring any statement-line filter. The Deneb dataset groups",
      "/// by 'P&L Lines'[Line], and this count must NOT inherit that grouping."],
     None, "#,##0;(#,##0)"),
    ("NM Products All Lines",
     ["CALCULATE (",
      "    DISTINCTCOUNT ( 'Financials'[ProductKey] ),",
      "    'Financials'[ProductKey] <> 0,",
      "    REMOVEFILTERS ( 'P&L Lines' )",
      ")"],
     "06 Odd Rows P&L",
     ["/// Distinct active products, ignoring any statement-line filter. ProductKey 0 is the",
      "/// sentinel for the 19 non-product accounts, not a product."],
     None, "#,##0;(#,##0)"),
]

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

names = {m[0] for m in MEASURES}
before = len(blocks)
blocks = [b for b in blocks if b[0] not in names]
print(f"stripped {before - len(blocks)} existing")

new = []
for name, body, folder, docs, fsd, fmt in MEASURES:
    # "///" doc comments are members of the table block and MUST carry the same one-tab
    # indent as 'measure'; at column 0 TMDL fails with an Indentation error.
    new += ["	" + d for d in docs]
    new.append(f"\tmeasure '{name}' =")
    new.append("")
    new += [f"\t\t\t{l}" for l in body]
    if fmt:
        new.append(f"\t\tformatString: {fmt}")
    new.append(f"\t\tdisplayFolder: {folder}")
    new.append(f"\t\tlineageTag: {uuid.uuid5(uuid.NAMESPACE_URL, 'plbridgedemo/' + name)}")
    new.append("")
    if fsd:
        # child object, AFTER the scalars, blank-line separated; a measure may not carry
        # both formatString: and formatStringDefinition
        new.append(f"\t\tformatStringDefinition = {fsd}")
        new.append("")

head = lines[: block_start(decl[0])]
out = head + new + [l for _, b in blocks for l in b] + lines[part:]
OUT.write_text("\n".join(out), encoding="utf-8", newline="\r\n")
total = sum(1 for l in out if l.startswith("\tmeasure '"))
assert total == len(blocks) + len(MEASURES), f"drift: {total}"
print(f"OK: 00_Measures now defines {total} measures")
