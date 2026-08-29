# Proves the whole 13 x 14 Odd Rows P&L can be reconstructed from the 30-row dataset in
# demo_odd_rows_deneb_query.dax -- i.e. that a Deneb spec can derive the 8 non-account
# rows and the 8 variance columns client-side, for zero engine cost.
# Gate: every one of the 182 cells must equal the shipped page 6 value in _golden_182.csv.
import csv, sys
def load(f): return list(csv.DictReader(open(f, encoding='utf-8-sig')))
base, gold = load('_deneb_base.csv'), load('_golden_182.csv')
f = lambda v: float(v) if v not in ('', None) else None

LK, IK = 'P&L Lines[Line]', 'P&L View[P&L View]'
amt   = {(r[LK], r[IK]): f(r['[Amount]']) for r in base}
store = {r[IK]: f(r['[Trading Stores]'])  for r in base}
prod  = {r[IK]: f(r['[Active Products]']) for r in base}
for r in base:
    assert f(r['[Trading Stores]']) == store[r[IK]], "Trading Stores varies by line"
    assert f(r['[Active Products]']) == prod[r[IK]], "Active Products varies by line"
print("OK  counts constant across lines")

BASE = ["Actual", "LY", "Budget", "YTD Actual", "YTD LY", "YTD Budget"]
def rows_for(b):
    TI, TC, GP, TOE, NP = (amt[(n, b)] for n in (
        "Total Income", "Total Cost of Sales", "Gross Profit",
        "Total Operating Expenses", "Net Profit"))
    d = lambda a, c: (a / c if c else None)
    return {
        "Total Income": TI, "Total Cost of Sales": TC, "Gross Profit": GP,
        "Total Operating Expenses": TOE, "Net Profit": NP,
        "Gross Margin %": d(GP, TI), "Net Margin %": d(NP, TI),
        "COGS % of Income": d(-TC, TI), "Opex % of Income": d(-TOE, TI),
        "Income per Trading Store": d(TI, store[b]),
        "Net Profit per Trading Store": d(NP, store[b]),
        "Income per Active Product": d(TI, prod[b]),
        "Trading Stores": store[b],
    }
V = {b: rows_for(b) for b in BASE}
sub = lambda a, b: None if a is None or b is None else a - b
pct = lambda a, b: None if a is None or b is None or not b else (a - b) / b
DERIVED = {
    "vs LY": ("Actual", "LY", sub),                 "vs LY %": ("Actual", "LY", pct),
    "Var to Budget": ("Actual", "Budget", sub),     "Var to Budget %": ("Actual", "Budget", pct),
    "YTD vs LY": ("YTD Actual", "YTD LY", sub),     "YTD vs LY %": ("YTD Actual", "YTD LY", pct),
    "YTD Var to Budget": ("YTD Actual", "YTD Budget", sub),
    "YTD Var to Budget %": ("YTD Actual", "YTD Budget", pct),
}
out = {b: V[b] for b in BASE}
for item, (a, b, op) in DERIVED.items():
    out[item] = {k: op(V[a][k], V[b][k]) for k in V[a]}

bad = []
for g in gold:
    got, want = out[g['Item']][g['Line']], f(g['Value'])
    if got is None and want is None: continue
    if got is None or want is None or abs(got - want) > max(1e-9, abs(want) * 1e-9):
        bad.append((g['Line'], g['Item'], got, want))
print(f"DERIVED-IN-SPEC vs GOLDEN: {len(gold)} cells | BADDIFF={len(bad)}")
for b in bad[:15]: print("   DIFF", b)
sys.exit(1 if bad else 0)
