# Emits the slow SWITCH-stack measure block for PL Bridge Demo (cribbed from
# scripts\gen_measures.py). Appends ~184 measures into the existing
# 00_Measures.tmdl table block, before the partition.
# Deliberately reproduces classic P&L anti-patterns (layered SWITCH, lowercase
# calculate/filter over a dimension, raw / division, format() text branches,
# and 14 statement columns incl. a full YTD set).
# Dollar measures carry a dynamic format string (auto $M / $K): same feature as
# the fast side, so the visual A/B stays fair.
# DO NOT optimize the DAX.
import re
import uuid
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / "PL Bridge Demo.SemanticModel" / "definition" / "tables" / "00_Measures.tmdl"

def tag(name):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "plbridgedemo/" + name))

SCEN = ["Actual", "Budget"]

ACCOUNTS = [
    "Retail Sales",
    "Wholesale Sales",
    "Online Sales",
    "Delivery & Freight Income",
    "Cost of Goods - Retail",
    "Cost of Goods - Wholesale",
    "Cost of Goods - Online",
    "Freight Inwards",
    "Stock Adjustments",
    "Salaries & Wages - Stores",
    "Salaries & Wages - Warehouse",
    "Superannuation",
    "Rent & Outgoings",
    "Utilities",
    "Marketing & Advertising",
    "Insurance",
    "Vehicle & Delivery Costs",
    "Repairs & Maintenance",
    "IT & Software",
    "Merchant & Bank Fees",
    "Depreciation",
    "Other Expenses",
]
INCOME = ACCOUNTS[0:4]
COS = ACCOUNTS[4:9]
OPEX = ACCOUNTS[9:22]

# The 27 statement lines, byte-identical to 'P&L Rows' / pl_lines.csv (SPEC section 2).
# Detail-line indent is 4 x U+00A0 (non-breaking space): table visuals trim ASCII spaces.
INDENT = " " * 4
PL_LINES = (
    [f"{INDENT}{a}" for a in INCOME]
    + ["Total Income"]
    + [f"{INDENT}{a}" for a in COS]
    + ["Total Cost of Sales", "Gross Profit"]
    + [f"{INDENT}{a}" for a in OPEX]
    + ["Total Operating Expenses", "Net Profit"]
)
assert len(PL_LINES) == 27

measures = []  # (name, expr) -- expr: str = single body line, list = multi-line body

def m1(name, expr):
    measures.append((name, expr))

def mN(name, lines):
    measures.append((name, lines))

# L0 -- base values (4)
for s in SCEN:
    m1(f"Base {s} Value",
       f"CALCULATE(SUM('Financials'[Amount]), 'Financials'[Scenario] = \"{s}\")")
    m1(f"YTD {s} Value",
       f"CALCULATE([Base {s} Value], DATESYTD('DimDate'[Date]))")

# L1 -- time-period switch + LY (3)
for s in SCEN:
    mN(f"{s} Period Value", [
        f"Switch(True(), SELECTEDVALUE('Time Period'[Time Period]) = \"YTD\", [YTD {s} Value],",
        f"[Base {s} Value])",
    ])
m1("Actual Period Value LY",
   "CALCULATE([Actual Period Value], DATEADD('DimDate'[Date], -1, YEAR))")
m1("YTD Actual Value LY",
   "CALCULATE([YTD Actual Value], DATEADD('DimDate'[Date], -1, YEAR))")

# L2 -- per-account bases via lowercase calculate/filter over the dimension (132)
for a in ACCOUNTS:
    m1(f"Actual {a}",
       f"calculate([Actual Period Value], filter('Accounts', 'Accounts'[Account] = \"{a}\"))")
    m1(f"Budget {a}",
       f"calculate([Budget Period Value], filter('Accounts', 'Accounts'[Account] = \"{a}\"))")
    m1(f"Actual {a} LY",
       f"calculate([Actual Period Value LY], filter('Accounts', 'Accounts'[Account] = \"{a}\"))")
    m1(f"Actual {a} YTD",
       f"calculate([YTD Actual Value], filter('Accounts', 'Accounts'[Account] = \"{a}\"))")
    m1(f"Budget {a} YTD",
       f"calculate([YTD Budget Value], filter('Accounts', 'Accounts'[Account] = \"{a}\"))")
    m1(f"Actual {a} YTD LY",
       f"calculate([YTD Actual Value LY], filter('Accounts', 'Accounts'[Account] = \"{a}\"))")

# L2b -- subtotal pyramids per family (30)
# name(F, x): the family's measure name for statement item x
def fam_name(fam, x):
    if fam == "LY":
        return f"Actual {x} LY"
    if fam == "ActualYTD":
        return f"Actual {x} YTD"
    if fam == "BudgetYTD":
        return f"Budget {x} YTD"
    if fam == "LYYTD":
        return f"Actual {x} YTD LY"
    return f"{fam} {x}"

for fam in ["Actual", "Budget", "LY", "ActualYTD", "BudgetYTD", "LYYTD"]:
    def ref(x):
        return f"[{fam_name(fam, x)}]"
    m1(fam_name(fam, "Total Income"), " + ".join(ref(a) for a in INCOME))
    m1(fam_name(fam, "Total Cost of Sales"), " + ".join(ref(a) for a in COS))
    m1(fam_name(fam, "Gross Profit"),
       f"{ref('Total Income')} + {ref('Total Cost of Sales')}")
    m1(fam_name(fam, "Total Operating Expenses"), " + ".join(ref(a) for a in OPEX))
    m1(fam_name(fam, "Net Profit"),
       f"{ref('Gross Profit')} + {ref('Total Operating Expenses')}")

# L3 -- the fourteen 27-branch SWITCH measures the report binds
SEL = "SELECTEDVALUE('P&L Rows'[Line])"

def line_ref(fam, label):
    return f"[{fam_name(fam, label.strip())}]"

L3 = [
    ("Slow Actual Value", True, lambda lb: line_ref("Actual", lb)),
    ("Slow Budget Value", True, lambda lb: line_ref("Budget", lb)),
    ("Slow Var Value", True, lambda lb: f"{line_ref('Actual', lb)} - {line_ref('Budget', lb)}"),
    ("Slow Var % Value", False,
     lambda lb: f"format(({line_ref('Actual', lb)} - {line_ref('Budget', lb)}) / {line_ref('Budget', lb)}, \"0.0%\")"),
    ("Slow LY Value", True, lambda lb: line_ref("LY", lb)),
    ("Slow vs LY Value", True, lambda lb: f"{line_ref('Actual', lb)} - {line_ref('LY', lb)}"),
    ("Slow vs LY % Value", False,
     lambda lb: f"format(({line_ref('Actual', lb)} - {line_ref('LY', lb)}) / {line_ref('LY', lb)}, \"0.0%\")"),
    ("Slow Actual YTD Value", True, lambda lb: line_ref("ActualYTD", lb)),
    ("Slow Budget YTD Value", True, lambda lb: line_ref("BudgetYTD", lb)),
    ("Slow Var YTD Value", True, lambda lb: f"{line_ref('ActualYTD', lb)} - {line_ref('BudgetYTD', lb)}"),
    ("Slow Var % YTD Value", False,
     lambda lb: f"format(({line_ref('ActualYTD', lb)} - {line_ref('BudgetYTD', lb)}) / {line_ref('BudgetYTD', lb)}, \"0.0%\")"),
    ("Slow LY YTD Value", True, lambda lb: line_ref("LYYTD", lb)),
    ("Slow vs LY YTD Value", True, lambda lb: f"{line_ref('ActualYTD', lb)} - {line_ref('LYYTD', lb)}"),
    ("Slow vs LY % YTD Value", False,
     lambda lb: f"format(({line_ref('ActualYTD', lb)} - {line_ref('LYYTD', lb)}) / {line_ref('LYYTD', lb)}, \"0.0%\")"),
]
DYN_FMT = set()  # dollar SWITCH measures that get the dynamic $M/$K format string
for name, is_dollar, branch in L3:
    # the row label is resolved ONCE into a variable and reused by every branch,
    # instead of re-declaring SELECTEDVALUE in all 27 comparisons
    lines = [f"VAR __Line = {SEL}", "RETURN", "Switch(True(),"]
    for lb in PL_LINES:
        lines.append(f'__Line = "{lb}", {branch(lb)},')
    lines[-1] = lines[-1][:-1]  # last branch: drop trailing comma
    lines.append(")")
    mN(name, lines)
    if is_dollar:
        DYN_FMT.add(name)

# ---- emit the TMDL block ----
def dyn_fmt(name):
    # auto-scale dollars: >=1M -> $M, >=1K -> $K, else $ (negatives in parens)
    return ('SWITCH(TRUE(), ABS([' + name + ']) >= 1000000, "$#,##0,,.0""M"";($#,##0,,.0""M"")", '
            'ABS([' + name + ']) >= 1000, "$#,##0,.0""K"";($#,##0,.0""K"")", "$#,##0;($#,##0)")')

parts = []
for name, expr in measures:
    body = [expr] if isinstance(expr, str) else expr
    parts.append(f"\tmeasure '{name}' =")
    parts.append("")
    parts.extend(f"\t\t\t{ln}" for ln in body)
    parts.append("\t\tdisplayFolder: 02 Slow P&L (SWITCH)")
    parts.append(f"\t\tlineageTag: {tag(name)}")
    parts.append("")
    if name in DYN_FMT:
        # child object, AFTER the scalar properties, blank-line separated (canonical
        # TmdlSerializer shape -- any other placement fails Desktop's parser)
        parts.append(f"\t\tformatStringDefinition = {dyn_fmt(name)}")
        parts.append("")
    else:
        parts.append('\t\tannotation PBI_FormatHint = {"isGeneralNumber":true}')
        parts.append("")

# ---- self-checks before touching the file ----
names = [n for n, _ in measures]
assert len(names) == len(set(names)), "duplicate measure names"
assert len(names) == 184, f"expected 184 measures, got {len(names)}"

nameset = set(names)
bad = []
for n, expr in measures:
    text = "\n".join(expr) if isinstance(expr, list) else expr
    for m in re.finditer(r"(?<!['\]\w])\[([^\]]+)\]", text):
        if m.group(1) not in nameset:
            bad.append((n, m.group(1)))
assert not bad, f"unresolved measure refs: {bad}"

block = "\n".join(parts)
for lb in PL_LINES:
    needle = f'__Line = "{lb}",'
    alt = f'__Line = "{lb}"'
    assert needle in block or alt in block, f"branch string missing: {lb!r}"

# ---- strip-and-reinsert by measure NAME, never by line position ----
# Desktop re-serialises 00_Measures.tmdl on save and reorders measures, so a positional
# start/end pair silently swallows whatever has drifted between the two anchors.
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

generated = set(names)
before = len(blocks)
blocks = [b for b in blocks if b[0] not in generated]
if before != len(blocks):
    print(f"stripped {before - len(blocks)} previously generated measures")

head = lines[: block_start(decl[0])]
out_lines = head + parts + [l for _, blk in blocks for l in blk] + lines[part:]
OUT.write_text("\n".join(out_lines), encoding="utf-8", newline="\r\n")

total = sum(1 for ln in out_lines if ln.startswith("\tmeasure '"))
assert total == len(blocks) + len(generated), f"measure count drift: {total}"
print(f"OK: inserted {len(names)} slow measures into {OUT}")
print(f"00_Measures now defines {total} measures")
