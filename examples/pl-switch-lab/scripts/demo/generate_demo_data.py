"""PL Bridge Demo synthetic data generator (DEMO-SPEC.md section 2). Seed 42, deterministic.

FINAL KNOB VALUES (recorded per spec). Deviations from the SPEC literals, tuned so the
full-company P&L lands at GM ~40% and net margin ~5-9% (spec-exact values gave GM ~45%,
net ~17% -- expenses too small relative to the margin the sales/COGS grain produces):
  TRADE_P            = 0.65         (spec 0.45; raised 2026-08-23 with ranging 16 retail +
                                     3 DCs, to grow the fact ~40M -> ~75M rows for a more
                                     painful slow-SWITCH demo)
  COGS_LO..COGS_HI   = 0.57..0.71   (spec 0.52..0.68; up to pull GM from ~45% to ~40%)
  R_SAL_STORES       = 0.19         (spec 0.16)
  R_SAL_WH           = 0.09         (spec 0.07)
  R_MARKETING        = 0.030        (spec 0.025)
  COGS unit cost carries the same 1.04^(year-2024) trend as prices (spec formula had no
  trend on cost, which drifted GM +2.3pp/yr and pushed 2026 net margin to 10.8%).
  Everything else exactly as SPEC section 2.
"""
import csv
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "demo"
DATA.mkdir(parents=True, exist_ok=True)

# ---------------- knobs ----------------
SEED = 42
TRADE_P = 0.65                      # bernoulli per ranged-pair-day (0.45 orig; see header)
COGS_LO, COGS_HI = 0.57, 0.71       # per-product cogs_rate (tuned; spec 0.52-0.68)
SEASONALITY = {1: 0.85, 2: 0.85, 3: 0.95, 4: 0.95, 5: 1.0, 6: 1.05,
               7: 0.9, 8: 0.9, 9: 1.0, 10: 1.05, 11: 1.25, 12: 1.6}
WEEKEND_RETAIL = 1.35
TREND = 1.04
SALES_NOISE = 0.05
BUDGET_FACTOR = 0.98
BUDGET_NOISE = 0.08
OPEX_NOISE_ACT = 0.07
OPEX_NOISE_BUD = 0.04

R_DELIVERY_INC = 0.015   # retail+online
R_FREIGHT_IN = 0.020
R_STOCK_ADJ = 0.004
R_SAL_STORES = 0.19      # retail+online (tuned; spec 0.16)
R_SAL_WH = 0.09          # DCs (tuned; spec 0.07)
R_SUPER = 0.11           # x the store's salaries
R_RENT = 0.055           # not Online
R_UTIL = 0.008
R_MARKETING = 0.030      # tuned; spec 0.025
R_INSURANCE = 0.004
R_VEHICLE = 0.012        # DCs + Online x2.5
VEHICLE_X = 2.5
R_REPAIRS = 0.005
R_IT = 0.006
R_MERCHANT = 0.011       # retail+online
R_DEPR = 0.009
R_OTHER = 0.006

rng = np.random.default_rng(SEED)

# ---------------- stores.parquet (28) ----------------
RETAIL_STORES = [  # (Store, State) -- StoreKey 1..24
    ("Sydney CBD", "NSW"), ("Parramatta", "NSW"), ("Newcastle", "NSW"),
    ("Melbourne Central", "VIC"), ("Geelong", "VIC"), ("Richmond", "VIC"),
    ("Brisbane CBD", "QLD"), ("Gold Coast", "QLD"), ("Cairns", "QLD"),
    ("Perth CBD", "WA"), ("Fremantle", "WA"), ("Joondalup", "WA"),
    ("Adelaide CBD", "SA"), ("Glenelg", "SA"), ("Mount Barker", "SA"),
    ("Hobart", "TAS"), ("Launceston", "TAS"), ("Devonport", "TAS"),
    ("Canberra Centre", "ACT"), ("Belconnen", "ACT"), ("Woden", "ACT"),
    ("Darwin", "NT"), ("Palmerston", "NT"), ("Alice Springs", "NT"),
]
ALL_STORES = (
    [(s, st, "Retail") for s, st in RETAIL_STORES]
    + [("DC East", "NSW", "Wholesale"), ("DC South", "VIC", "Wholesale"), ("DC West", "WA", "Wholesale")]
    + [("Online Store", "NSW", "Online")]
)
pq.write_table(pa.table({
    "StoreKey": np.arange(1, 29, dtype=np.int64),
    "Store": [s for s, _, _ in ALL_STORES],
    "State": [st for _, st, _ in ALL_STORES],
    "Channel": [c for _, _, c in ALL_STORES],
}), DATA / "stores.parquet")

# ---------------- products.parquet (2501) ----------------
CATS = ["Furniture", "Kitchen", "Bedding", "Bathroom", "Outdoor", "Lighting", "Decor", "Storage"]
PRICE_BAND = {"Furniture": (150, 450), "Kitchen": (30, 200), "Bedding": (40, 250),
              "Bathroom": (15, 120), "Outdoor": (60, 400), "Lighting": (25, 220),
              "Decor": (15, 150), "Storage": (20, 180)}
NPROD = 2500
pk = np.arange(0, NPROD + 1, dtype=np.int64)
cat = ["Non-Product"] + [CATS[k % 8] for k in range(1, NPROD + 1)]
pq.write_table(pa.table({
    "ProductKey": pk,
    "Product": ["(Not product-related)"] + [f"{CATS[k % 8]} Product {k:04d}" for k in range(1, NPROD + 1)],
    "Category": cat,
}), DATA / "products.parquet")

# ---------------- accounts.parquet (22, pinned) ----------------
ACCOUNTS = [
    (1, "Retail Sales", "Income"),
    (2, "Wholesale Sales", "Income"),
    (3, "Online Sales", "Income"),
    (4, "Delivery & Freight Income", "Income"),
    (5, "Cost of Goods - Retail", "Cost of Sales"),
    (6, "Cost of Goods - Wholesale", "Cost of Sales"),
    (7, "Cost of Goods - Online", "Cost of Sales"),
    (8, "Freight Inwards", "Cost of Sales"),
    (9, "Stock Adjustments", "Cost of Sales"),
    (10, "Salaries & Wages - Stores", "Operating Expenses"),
    (11, "Salaries & Wages - Warehouse", "Operating Expenses"),
    (12, "Superannuation", "Operating Expenses"),
    (13, "Rent & Outgoings", "Operating Expenses"),
    (14, "Utilities", "Operating Expenses"),
    (15, "Marketing & Advertising", "Operating Expenses"),
    (16, "Insurance", "Operating Expenses"),
    (17, "Vehicle & Delivery Costs", "Operating Expenses"),
    (18, "Repairs & Maintenance", "Operating Expenses"),
    (19, "IT & Software", "Operating Expenses"),
    (20, "Merchant & Bank Fees", "Operating Expenses"),
    (21, "Depreciation", "Operating Expenses"),
    (22, "Other Expenses", "Operating Expenses"),
]
ACCT_NAME = {k: n for k, n, _ in ACCOUNTS}
pq.write_table(pa.table({
    "AccountKey": np.array([k for k, _, _ in ACCOUNTS], dtype=np.int64),
    "Account": [n for _, n, _ in ACCOUNTS],
    "AccountClass": [c for _, _, c in ACCOUNTS],
}), DATA / "accounts.parquet")

# ---------------- pl_lines.csv (27 lines / 75 rows, pinned) ----------------
# Detail-line indent is 4 x U+00A0 (non-breaking space): table visuals trim ASCII spaces.
INDENT = " " * 4
LINES = []  # (LineKey, Line, LineClass, [AccountKey,...])
for ak in range(1, 5):
    LINES.append((ak * 10, INDENT + ACCT_NAME[ak], "Detail", [ak]))
LINES.append((50, "Total Income", "Subtotal", [1, 2, 3, 4]))
for ak in range(5, 10):
    LINES.append((60 + (ak - 5) * 10, INDENT + ACCT_NAME[ak], "Detail", [ak]))
LINES.append((110, "Total Cost of Sales", "Subtotal", list(range(5, 10))))
LINES.append((120, "Gross Profit", "Total", list(range(1, 10))))
for ak in range(10, 23):
    LINES.append((130 + (ak - 10) * 10, INDENT + ACCT_NAME[ak], "Detail", [ak]))
LINES.append((260, "Total Operating Expenses", "Subtotal", list(range(10, 23))))
LINES.append((270, "Net Profit", "Total", list(range(1, 23))))
LINES.sort(key=lambda t: t[0])

csv_path = DATA / "pl_lines.csv"
with open(csv_path, "w", encoding="utf-8", newline="") as f:
    f.write("LineKey,Line,LineClass,AccountKey,Account\n")
    for lk, line, cls, aks in LINES:
        for ak in aks:
            f.write(f'{lk},"{line}",{cls},{ak},{ACCT_NAME[ak]}\n')

# ---------------- financials.parquet (~35-45M) ----------------
# ranging: per product 16 of 24 retail stores + all 3 DCs + the online store = 20 pairs
retail_sel = np.argsort(rng.random((NPROD, 24)), axis=1)[:, :16] + 1
dc_sel = np.argsort(rng.random((NPROD, 3)), axis=1)[:, :3] + 25
price_u = rng.random(NPROD)
cogs_rate = rng.uniform(COGS_LO, COGS_HI, NPROD)

# row i of the per-product arrays below is product key i+1 (category = CATS[key % 8])
band = np.array([PRICE_BAND[CATS[k % 8]] for k in range(1, NPROD + 1)], dtype=np.float64)
retail_price = band[:, 0] + price_u * (band[:, 1] - band[:, 0])   # per product 1..2500

pair_store = np.concatenate(
    [retail_sel, dc_sel, np.full((NPROD, 1), 28, dtype=np.int64)], axis=1).ravel()
pair_prod = np.repeat(np.arange(1, NPROD + 1, dtype=np.int64), 20)
NPAIRS = pair_store.size                                          # 50,000

store_ch = np.array([0] * 24 + [1] * 3 + [2], dtype=np.int64)     # 0 retail, 1 wholesale, 2 online
pair_ch = store_ch[pair_store - 1]
pair_price = retail_price[pair_prod - 1] * np.array([1.0, 0.6, 1.0])[pair_ch]
pair_unitcost = pair_price * cogs_rate[pair_prod - 1]             # wholesale cost off the wholesale price
pair_lam = np.array([3.0, 25.0, 4.0])[pair_ch]
pair_sales_acct = pair_ch + 1                                     # 1/2/3
pair_cogs_acct = pair_ch + 5                                      # 5/6/7
pair_retail = pair_ch == 0

# opex definitions: (AccountKey, per-store rate, store mask, sign)
retail_m, ws_m, onl_m = store_ch == 0, store_ch == 1, store_ch == 2
all_m = np.ones(28, dtype=bool)
sal_rate = np.where(ws_m, R_SAL_WH, R_SAL_STORES)
veh_rate = np.where(retail_m, R_VEHICLE, R_VEHICLE * VEHICLE_X)


def full(r):
    return np.full(28, r)


OPEX_DEFS = [
    (4, full(R_DELIVERY_INC), retail_m | onl_m, 1.0),
    (8, full(R_FREIGHT_IN), all_m, -1.0),
    (9, full(R_STOCK_ADJ), all_m, -1.0),
    (10, full(R_SAL_STORES), retail_m | onl_m, -1.0),
    (11, full(R_SAL_WH), ws_m, -1.0),
    (12, R_SUPER * sal_rate, all_m, -1.0),
    (13, full(R_RENT), ~onl_m, -1.0),
    (14, full(R_UTIL), all_m, -1.0),
    (15, full(R_MARKETING), all_m, -1.0),
    (16, full(R_INSURANCE), all_m, -1.0),
    (17, veh_rate, all_m, -1.0),
    (18, full(R_REPAIRS), all_m, -1.0),
    (19, full(R_IT), all_m, -1.0),
    (20, full(R_MERCHANT), retail_m | onl_m, -1.0),
    (21, full(R_DEPR), all_m, -1.0),
    (22, full(R_OTHER), all_m, -1.0),
]

schema = pa.schema([
    ("ProductKey", pa.int64()), ("StoreKey", pa.int64()), ("Date", pa.timestamp("ms")),
    ("Scenario", pa.string()), ("AccountKey", pa.int64()), ("Amount", pa.float64()),
])

months = np.arange("2024-01", "2027-01", dtype="datetime64[M]")
sanity = {}  # (year, scenario) -> np.array([income, cogs, opex])


def acc(year, scen, inc=0.0, cos=0.0, opx=0.0):
    key = (year, scen)
    if key not in sanity:
        sanity[key] = np.zeros(3)
    sanity[key] += [inc, cos, opx]


total = 0
with pq.ParquetWriter(DATA / "financials.parquet", schema) as writer:
    for m in months:
        d0 = m.astype("datetime64[D]")
        days = np.arange(d0, (m + 1).astype("datetime64[D]"))
        nd = days.size
        year = m.astype("datetime64[Y]").astype(np.int64) + 1970
        mon = int(m.astype(np.int64) % 12 + 1)
        seas = SEASONALITY[mon]
        trend = TREND ** (year - 2024)
        is_wknd = ((days.astype(np.int64) + 3) % 7) >= 5          # Mon=0 .. Sun=6
        m0 = m.astype("datetime64[ms]")
        day_ms = days.astype("datetime64[ms]")

        # actual sales + cogs (daily)
        pi, di = np.nonzero(rng.random((NPAIRS, nd)) < TRADE_P)
        units = np.maximum(1, rng.poisson(pair_lam[pi]))
        noise = rng.normal(1.0, SALES_NOISE, pi.size)
        wk = np.where(pair_retail[pi] & is_wknd[di], WEEKEND_RETAIL, 1.0)
        sales = np.round(units * pair_price[pi] * seas * trend * wk * noise, 2)
        cogs = np.round(-(units * pair_unitcost[pi] * trend), 2)  # cost inflation = price trend (see header)

        # budget sales/cogs (month-start, per ranged pair with nonzero actual)
        b_sales = np.bincount(pi, weights=sales, minlength=NPAIRS)
        b_cogs = np.bincount(pi, weights=cogs, minlength=NPAIRS)
        bidx = np.nonzero(b_sales != 0)[0]
        bud_sales = np.round(b_sales[bidx] * rng.normal(1.0, BUDGET_NOISE, bidx.size) * BUDGET_FACTOR, 2)
        bud_cogs = np.round(b_cogs[bidx] * rng.normal(1.0, BUDGET_NOISE, bidx.size) * BUDGET_FACTOR, 2)

        # other income + opex (month-start, per store x account, both scenarios)
        S_act = np.bincount(pair_store[pi] - 1, weights=sales, minlength=28)
        S_bud = np.bincount(pair_store[bidx] - 1, weights=bud_sales, minlength=28)
        op_store, op_ak, op_amt, op_scen = [], [], [], []
        for scen, S, sd in (("Actual", S_act, OPEX_NOISE_ACT), ("Budget", S_bud, OPEX_NOISE_BUD)):
            for akey, rate, mask, sign in OPEX_DEFS:
                sk = np.nonzero(mask)[0]
                amt = np.round(sign * rate[sk] * S[sk] * rng.normal(1.0, sd, sk.size), 2)
                op_store.append(sk + 1)
                op_ak.append(np.full(sk.size, akey, dtype=np.int64))
                op_amt.append(amt)
                op_scen.append(np.full(sk.size, scen))
                if akey == 4:
                    acc(year, scen, inc=amt.sum())
                elif akey in (8, 9):
                    acc(year, scen, cos=amt.sum())
                else:
                    acc(year, scen, opx=amt.sum())
        op_store = np.concatenate(op_store)
        op_ak = np.concatenate(op_ak)
        op_amt = np.concatenate(op_amt)
        op_scen = np.concatenate(op_scen)

        acc(year, "Actual", inc=sales.sum(), cos=cogs.sum())
        acc(year, "Budget", inc=bud_sales.sum(), cos=bud_cogs.sum())

        ns, nb, no = pi.size, bidx.size, op_ak.size
        writer.write_table(pa.table({
            "ProductKey": np.concatenate([pair_prod[pi], pair_prod[pi], pair_prod[bidx],
                                          pair_prod[bidx], np.zeros(no, dtype=np.int64)]),
            "StoreKey": np.concatenate([pair_store[pi], pair_store[pi], pair_store[bidx],
                                        pair_store[bidx], op_store]),
            "Date": np.concatenate([day_ms[di], day_ms[di], np.full(nb, m0, dtype="datetime64[ms]"),
                                    np.full(nb, m0, dtype="datetime64[ms]"),
                                    np.full(no, m0, dtype="datetime64[ms]")]),
            "Scenario": np.concatenate([np.full(2 * ns, "Actual"), np.full(2 * nb, "Budget"), op_scen]),
            "AccountKey": np.concatenate([pair_sales_acct[pi], pair_cogs_acct[pi],
                                          pair_sales_acct[bidx], pair_cogs_acct[bidx], op_ak]),
            "Amount": np.concatenate([sales, cogs, bud_sales, bud_cogs, op_amt]),
        }, schema=schema))
        n = 2 * ns + 2 * nb + no
        total += n
        print(f"{m}: {n:,} rows (cumulative {total:,})", flush=True)

if not (70_000_000 <= total <= 80_000_000):
    print(f"WARNING: financials row count {total:,} outside the 70-80M window TRADE_P = 0.65 produces -- tune TRADE_P")

# ---------------- report: files ----------------
print("\n=== files ===")
for fn in ["stores.parquet", "products.parquet", "accounts.parquet", "financials.parquet"]:
    p = DATA / fn
    print(f"{fn}: {pq.read_metadata(p).num_rows:,} rows, {p.stat().st_size / 1e6:.1f} MB")
with open(csv_path, encoding="utf-8") as f:
    n_csv = sum(1 for _ in f) - 1
print(f"pl_lines.csv: {n_csv} rows, {csv_path.stat().st_size / 1e3:.1f} KB")

# ---------------- report: sanity P&L ----------------
print("\n=== full-company annual P&L (sanity; target GM ~40%, net margin ~5-9%) ===")
print(f"{'Year':<6}{'Scenario':<10}{'Income $M':>11}{'COGS $M':>10}{'GP $M':>9}{'GM%':>7}"
      f"{'OpEx $M':>10}{'NP $M':>9}{'NP%':>7}")
for year in (2024, 2025, 2026):
    for scen in ("Actual", "Budget"):
        inc, cos, opx = sanity[(year, scen)]
        gp = inc + cos
        npf = gp + opx
        print(f"{year:<6}{scen:<10}{inc / 1e6:>11,.1f}{cos / 1e6:>10,.1f}{gp / 1e6:>9,.1f}"
              f"{gp / inc:>7.1%}{opx / 1e6:>10,.1f}{npf / 1e6:>9,.1f}{npf / inc:>7.1%}")

# ---------------- self-check: pl_lines.csv round-trip ----------------
EXPECT = {10: [1], 20: [2], 30: [3], 40: [4], 50: [1, 2, 3, 4],
          60: [5], 70: [6], 80: [7], 90: [8], 100: [9],
          110: [5, 6, 7, 8, 9], 120: list(range(1, 10)),
          130: [10], 140: [11], 150: [12], 160: [13], 170: [14], 180: [15], 190: [16],
          200: [17], 210: [18], 220: [19], 230: [20], 240: [21], 250: [22],
          260: list(range(10, 23)), 270: list(range(1, 23))}
with open(csv_path, encoding="utf-8", newline="") as f:
    rows = list(csv.reader(f))
assert rows[0] == ["LineKey", "Line", "LineClass", "AccountKey", "Account"], rows[0]
body = rows[1:]
assert len(body) == 75, len(body)
line_by_key, key_by_line, seen = {}, {}, {}
for lk_s, line, cls, ak_s, acct in body:
    lk, ak = int(lk_s), int(ak_s)
    assert 1 <= ak <= 22, (lk, ak)
    assert line_by_key.setdefault(lk, line) == line, lk        # LineKey -> one Line
    assert key_by_line.setdefault(line, lk) == lk, line        # Line -> one LineKey (1:1)
    assert acct == ACCT_NAME[ak], (ak, acct)
    if cls == "Detail":
        assert line == INDENT + ACCT_NAME[ak], repr(line)      # leading NBSP indent intact
    seen.setdefault(lk, []).append(ak)
assert len(line_by_key) == 27 and len(key_by_line) == 27
assert seen == EXPECT, {k: v for k, v in seen.items() if EXPECT.get(k) != v}
print("\npl_lines.csv round-trip OK: 75 rows, 27 lines, Line<->LineKey 1:1, "
      "leading spaces intact, account sets match SPEC")
