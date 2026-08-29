# PL Bridge Demo: build spec (contract for build agents)

Purpose: a **generic, publishable** retail P&L that demonstrates the bridge method from
the bridge method (see `docs/performance/02-bridge-method.md`): slow classic SWITCH P&L vs
fast bridge P&L on the same ~40M-row synthetic fact. Nothing in this project may reference the client it was modelled on
or any client. This is the file that will later back a published Claude skill.

Root: the repository root. Every path below is relative to it.

```
PL Bridge Demo.pbip               <- model agent (crib PL Switch Lab.pbip, path -> PL Bridge Demo.Report)
PL Bridge Demo.SemanticModel\     <- model agent
PL Bridge Demo.Report\            <- report agent
data\demo\*.parquet + pl_lines.csv  <- data agent
scripts\demo\generate_demo_data.py  <- data agent
scripts\demo\gen_demo_measures.py   <- model agent (emits the slow-measure block)
scripts\demo\demo_slow_query.dax    <- verify agent
scripts\demo\demo_fast_query.dax    <- verify agent
scripts\demo\demo_tieout.dax        <- verify agent
```

Reference project for structural cribbing (READ ONLY): the existing
`PL Switch Lab.SemanticModel` / `PL Switch Lab.Report` in this same folder.
compatibilityLevel 1606, definition.pbism `{"version":"4.2","settings":{}}`,
.platform schema 2.0.0 with **new logicalId GUIDs**, definition.pbir version 4.0 byPath.

The two shipped implementations MUST produce identical numbers (tie-out is a build gate).

**Key difference from the old lab:** the fast P&L uses a **physical bridge table loaded from
CSV with a real (bidirectional) relationship**: the production shape from BRIDGE-METHOD.md §5:
not DATATABLE/TREATAS.

---

## 1. Business story (fixed: used in docs and report copy)

"Brightside Home & Living": a fictional Australian retailer: 24 bricks-and-mortar stores,
3 distribution centres selling wholesale, and an online store. Calendar fiscal year.
Scenarios: Actual and Budget; Last Year is derived from Actual via DATEADD.

## 2. Data (data agent)

All files under `data\demo\`. Seed 42, numpy vectorized, deterministic, chunked writes
(pyarrow ParquetWriter, one row-group batch per month) so RAM stays < ~4 GB. Print final row
counts + file sizes. Crib chunking mechanics from `scripts\generate_data.py` (read-only).

### stores.parquet: 28 rows
| column | type | rule |
|---|---|---|
| StoreKey | int64 | 1..28 |
| Store | string | see list |
| State | string | NSW, VIC, QLD, WA, SA, TAS, ACT, NT |
| Channel | string | `Retail`, `Wholesale`, `Online` |

Retail stores (1-24), 3 per state: `"{city} {n}"` from real-ish AU suburbs/cities, e.g.
NSW: Sydney CBD, Parramatta, Newcastle; VIC: Melbourne Central, Geelong, Richmond;
QLD: Brisbane CBD, Gold Coast, Cairns; WA: Perth CBD, Fremantle, Joondalup;
SA: Adelaide CBD, Glenelg, Mount Barker; TAS: Hobart, Launceston, Devonport;
ACT: Canberra Centre, Belconnen, Woden; NT: Darwin, Palmerston, Alice Springs.
Wholesale DCs (25-27): `DC East` (NSW), `DC South` (VIC), `DC West` (WA).
Online (28): `Online Store` (NSW).

### products.parquet: 2,501 rows
| column | type | rule |
|---|---|---|
| ProductKey | int64 | 0..2500 |
| Product | string | `"{Category} Product {k:04d}"`; key 0 = `"(Not product-related)"` |
| Category | string | Furniture, Kitchen, Bedding, Bathroom, Outdoor, Lighting, Decor, Storage (by `k % 8`); key 0 = `"(Not product-related)"` |

### accounts.parquet (22 rows (pinned) bridge CSV and measures must match EXACTLY)
| AccountKey | Account | sign in fact |
|---|---|---|
| 1 | Retail Sales | + |
| 2 | Wholesale Sales | + |
| 3 | Online Sales | + |
| 4 | Delivery & Freight Income | + |
| 5 | Cost of Goods - Retail | − |
| 6 | Cost of Goods - Wholesale | − |
| 7 | Cost of Goods - Online | − |
| 8 | Freight Inwards | − |
| 9 | Stock Adjustments | − |
| 10 | Salaries & Wages - Stores | − |
| 11 | Salaries & Wages - Warehouse | − |
| 12 | Superannuation | − |
| 13 | Rent & Outgoings | − |
| 14 | Utilities | − |
| 15 | Marketing & Advertising | − |
| 16 | Insurance | − |
| 17 | Vehicle & Delivery Costs | − |
| 18 | Repairs & Maintenance | − |
| 19 | IT & Software | − |
| 20 | Merchant & Bank Fees | − |
| 21 | Depreciation | − |
| 22 | Other Expenses | − |

Columns: AccountKey int64, Account string, AccountClass string
(`Income` 1-4, `Cost of Sales` 5-9, `Operating Expenses` 10-22).

### financials.parquet: target 35-45M rows (tall/skinny)
| column | type |
|---|---|
| ProductKey | int64 (0 for non-product rows) |
| StoreKey | int64 |
| Date | timestamp[ms]: daily for sales/COGS, month-start for everything else |
| Scenario | string : `Actual`, `Budget` |
| AccountKey | int64 |
| Amount | double, round 2dp, **expenses/COGS stored negative** |

Grain rules:
- **Ranging:** each product is ranged in a fixed random subset of 12 of the 24 retail stores,
  2 of the 3 DCs, and the online store (choose once per product, seed-stable) → ~15
  product-store pairs × 2,500 products = ~37,500 pairs.
- **Actual sales (daily, 2024-01-01..2026-12-31):** each ranged pair trades on ~45% of days
  (bernoulli per pair-day). Per trading day: units = max(1, poisson(lam per channel:
  retail 3, online 4, wholesale 25)); price per product drawn once uniform by category
  ($15-$450 retail; wholesale price = retail × 0.6). Sales row: AccountKey by channel
  (Retail Sales / Wholesale Sales / Online Sales), Amount = units × price ×
  seasonality × trend. Seasonality by month: Jan 0.85, Feb 0.85, Mar 0.95, Apr 0.95, May 1.0,
  Jun 1.05, Jul 0.9, Aug 0.9, Sep 1.0, Oct 1.05, Nov 1.25, Dec 1.6. Weekday factor for Retail
  only: Sat/Sun 1.35. Trend: ×1.04^(year−2024). Add noise normal(1.0, 0.05) per row.
- **Actual COGS (daily, mirrors each sales row):** same keys/date, AccountKey 5/6/7 by
  channel, Amount = −(units × unitcost) where unitcost = price × cogs_rate, cogs_rate drawn
  once per product uniform 0.52-0.68 (wholesale uses the wholesale price so wholesale margin
  is thinner).
- **Budget sales/COGS (month-start, per ranged pair × month):** monthly-aggregated Actual for
  that pair-month × normal(1.0, 0.08) × 0.98 (slightly optimistic-baseline). Skip pair-months
  with zero actual. AccountKeys same as actual.
- **Other income + operating expenses (month-start, per store × month × account, both
  scenarios):** ProductKey 0. Magnitudes derived from that store's Actual monthly sales S
  (wholesale DCs use their wholesale sales):
  - Delivery & Freight Income: +0.015 × S (retail+online only)
  - Freight Inwards: −0.020 × S ; Stock Adjustments: −0.004 × S
  - Salaries & Wages - Stores: −0.16 × S (retail+online); Salaries & Wages - Warehouse:
    −0.07 × S (DCs only); Superannuation: −0.11 × the store's salaries
  - Rent & Outgoings: −0.055 × S (not Online); Utilities: −0.008 × S
  - Marketing & Advertising: −0.025 × S; Insurance: −0.004 × S
  - Vehicle & Delivery Costs: −0.012 × S (DCs + Online ×2.5)
  - Repairs & Maintenance: −0.005 × S; IT & Software: −0.006 × S
  - Merchant & Bank Fees: −0.011 × S (retail+online only)
  - Depreciation: −0.009 × S; Other Expenses: −0.006 × S
  Every expense row × normal(1.0, 0.07). Budget expense = the same formula applied to Budget
  sales × normal(1.0, 0.04). Result: GM ~40%, net profit margin roughly 5-9%: sanity-print
  the full-company annual P&L totals at the end of generation.
- Print a warning if total rows land outside 30-50M; tune the trading-day probability to hit
  the target, and record the final knob values at the top of the script.

### pl_lines.csv: the bridge (pinned EXACTLY; this is the heart of the demo)
UTF-8, comma, header `LineKey,Line,LineClass,AccountKey,Account`. One row per
(statement line, account) pair. Quote every Line value (they carry leading spaces).
Line labels are byte-identical everywhere they appear (bridge, switch table, SWITCH branches).

Statement definition: LineKey, Line (detail lines indented with **4 × U+00A0 non-breaking
spaces**: table visuals trim ASCII leading spaces, verified on this build; the listing below
shows plain spaces for readability), LineClass, accounts:
```
10   "    Retail Sales"               Detail    [1]
20   "    Wholesale Sales"            Detail    [2]
30   "    Online Sales"               Detail    [3]
40   "    Delivery & Freight Income"  Detail    [4]
50   "Total Income"                   Subtotal  [1,2,3,4]
60   "    Cost of Goods - Retail"     Detail    [5]
70   "    Cost of Goods - Wholesale"  Detail    [6]
80   "    Cost of Goods - Online"     Detail    [7]
90   "    Freight Inwards"            Detail    [8]
100  "    Stock Adjustments"          Detail    [9]
110  "Total Cost of Sales"            Subtotal  [5,6,7,8,9]
120  "Gross Profit"                   Total     [1..9]
130  "    Salaries & Wages - Stores"    Detail  [10]
140  "    Salaries & Wages - Warehouse" Detail  [11]
150  "    Superannuation"             Detail    [12]
160  "    Rent & Outgoings"           Detail    [13]
170  "    Utilities"                  Detail    [14]
180  "    Marketing & Advertising"    Detail    [15]
190  "    Insurance"                  Detail    [16]
200  "    Vehicle & Delivery Costs"   Detail    [17]
210  "    Repairs & Maintenance"      Detail    [18]
220  "    IT & Software"              Detail    [19]
230  "    Merchant & Bank Fees"       Detail    [20]
240  "    Depreciation"               Detail    [21]
250  "    Other Expenses"             Detail    [22]
260  "Total Operating Expenses"       Subtotal  [10..22]
270  "Net Profit"                     Total     [1..22]
```
27 lines, 75 CSV rows (22 detail + 4+5+9+13+22 subtotal rows). `Account` column = the account
name for that AccountKey (for human readability and the How-it-works page). LineKey repeats on
every row of its line: Line↔LineKey is strictly 1:1 (sortByColumn depends on it).
The generator emits this CSV from the same pinned account list (single source of truth).

---

## 3. Semantic model (model agent)

Folder `PL Bridge Demo.SemanticModel\`: .platform (displayName `PL Bridge Demo`, new GUID),
definition.pbism 4.2, database.tmdl 1606, model.tmdl (crib the old lab's header: culture en-US,
defaultPowerBIDataSourceVersion powerBI_V3, sourceQueryCulture en-AU, dataAccessOptions;
`annotation __PBI_TimeIntelligenceEnabled = 0`), relationships.tmdl, tables\*.tmdl, culture
en-US.tmdl cribbed. Read `~/.claude/rules/tmdl-pbir-authoring.md` first. Fresh lineageTags
everywhere (uuid4, or uuid5 in generators for determinism).

### Imported tables (M partitions, mode import)
- `Financials`, `Products`, `Stores`, `Accounts` : `Parquet.Document(File.Contents(DataFolder & "\<name>.parquet"))`, where
  `DataFolder` is the Text parameter declared in `expressions.tmdl`.
  Financials columns all hidden; Date dataType dateTime; Amount summarizeBy sum, others none.
- `P&L Lines`: from the CSV:
  ```
  let
      Source = Csv.Document(File.Contents(DataFolder & "\pl_lines.csv"), [Delimiter = ",", Columns = 5, Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
      Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
      Typed = Table.TransformColumnTypes(Promoted, {{"LineKey", Int64.Type}, {"Line", type text}, {"LineClass", type text}, {"AccountKey", Int64.Type}, {"Account", type text}})
  in
      Typed
  ```
  NO trimming step: the leading spaces in `Line` are load-bearing.
  Column `Line`: sortByColumn LineKey, summarizeBy none. `LineKey` hidden, formatString 0.
  `AccountKey` hidden. `Account`, `LineClass` visible.
- `P&L Rows` (the slow version's disconnected rows table): inline
  `Table.FromRows({...}, type table [Line = Text.Type, Sort = Int64.Type])`: the 27
  (Line, LineKey) pairs from §2, byte-identical labels. `Line` sortByColumn `Sort`.
- `Time Period`: inline, single column `Time Period` string, rows `Selected Period`, `YTD`.
  Disconnected.
- `00_Measures`: measures-only table: crib the old lab's dummy-column pattern exactly.

### DimDate: via the date-table skill script (run it, do not hand-copy)
```
python "<plugins>/semantic-models/skills/date-table/scripts/add_date_table.py" --model "PL Bridge Demo.SemanticModel" --start 2024-01-01 --end 2026-12-31 --fy-start-month 1 --week-start 1 --mark-as-date-table --measure-table 00_Measures
```
Run it AFTER the base tables + model.tmdl exist (it edits model.tmdl refs and drops the
`Dates Selected` measure into 00_Measures). Keep the attribution headers it writes.
Dry-run first. DimDate is the model's only date table.

### Relationships (relationships.tmdl, new GUIDs)
Single-direction many-to-one:
- Financials[ProductKey] → Products[ProductKey]
- Financials[StoreKey] → Stores[StoreKey]
- Financials[Date] → DimDate[Date]
- Financials[AccountKey] → Accounts[AccountKey]
- **'P&L Lines'[AccountKey] → Accounts[AccountKey] with `crossFilteringBehavior: bothDirections`**
 : the load-bearing relationship: putting 'P&L Lines'[Line] on matrix rows propagates
  Lines → Accounts → Financials with no DAX.
'P&L Rows' and 'Time Period' stay disconnected.

### Measures: all in 00_Measures

**A. Fast bridge measures: displayFolder `01 Fast P&L (bridge)`. Hand-author these 8 in the
dax-no-calculate house style** (TMDL: blank line straight after `=`, body starts line 2,
`//` comment per step, short lines). CALCULATE appears ONLY for the scenario predicate and
time intelligence (DATEADD/DATESYTD over DimDate: Tim's standing exception):

```tmdl
	/// Actual for the selected period (slicer-state YTD switch; no row branching).
	measure 'P&L Actual' =

			// scenario predicate + optional YTD shift are the only context changes
			VAR __Base =
			    CALCULATE (
			        SUM ( 'Financials'[Amount] ),
			        'Financials'[Scenario] = "Actual"
			    )
			VAR __Result =
			    IF (
			        SELECTEDVALUE ( 'Time Period'[Time Period] ) = "YTD",
			        CALCULATE (
			            SUM ( 'Financials'[Amount] ),
			            'Financials'[Scenario] = "Actual",
			            DATESYTD ( 'DimDate'[Date] )
			        ),
			        __Base
			    )
			RETURN
			    __Result
		formatString: #,##0;(#,##0)
		displayFolder: 01 Fast P&L (bridge)
```
- `P&L Budget`: same shape, `"Budget"`. formatString `#,##0;(#,##0)`.
- `P&L LY` = `CALCULATE ( [P&L Actual], DATEADD ( 'DimDate'[Date], -1, YEAR ) )` (one-liner
  body, still body-on-line-2). Same formatString.
- `P&L Var` = `[P&L Actual] - [P&L Budget]`. Same formatString.
- `P&L Var %` = `DIVIDE ( [P&L Var], [P&L Budget] )`. formatString `0.0%;(0.0%)`.
- `P&L vs LY` = `[P&L Actual] - [P&L LY]`. formatString `#,##0;(#,##0)`.
- `Demo Actual` / `Demo Budget`: displayFolder `04 Teaching`, the two-liner teaching
  measures: `CALCULATE ( SUM ( 'Financials'[Amount] ), 'Financials'[Scenario] = "Actual" )`
  (resp. Budget). formatString `#,##0;(#,##0)`. These are what the How-it-works page prints.

**B. Card measures: displayFolder `03 Cards`** (bridge reuse: filter the bridge's Line):
- `Total Income $` = `CALCULATE ( [P&L Actual], 'P&L Lines'[Line] = "Total Income" )`
- `Gross Profit $` = same with `"Gross Profit"`; `Net Profit $` with `"Net Profit"`
- `Gross Margin %` = `DIVIDE ( [Gross Profit $], [Total Income $] )` formatString `0.0%`
- `Net Profit vs Budget %` =
  `DIVIDE ( [Net Profit $] - CALCULATE ( [P&L Budget], 'P&L Lines'[Line] = "Net Profit" ), ABS ( CALCULATE ( [P&L Budget], 'P&L Lines'[Line] = "Net Profit" ) ) )` formatString `+0.0%;-0.0%`
- formatStrings for the $ cards: plain `$#,##0`: card visuals apply Auto display units on
  top of the format string, so scaled formats double-scale ("$0.0bnM"). Scaling-comma rule
  (VBA-style): commas go **immediately left of the decimal point** : `$#,##0,,.0"M"` is the
  valid millions-with-decimal form; Excel-style `0.0,,` (commas after decimals) is NOT parsed.

**C. Slow SWITCH stack: displayFolder `02 Slow P&L (SWITCH)`: generated by
`scripts\demo\gen_demo_measures.py`** (crib `scripts\gen_measures.py`; deterministic
lineageTags `uuid.uuid5(uuid.NAMESPACE_URL, "plbridgedemo/" + name)`). FAITHFUL ANTI-PATTERN:
no formatString on any of these, lowercase `calculate(`/`filter(` in L2, raw FORMAT for the
Var % branches, full measure pyramid. Do NOT optimize. S ∈ {Actual, Budget}; A = the 22
account names.

L0 (4): `Base {S} Value` = `CALCULATE(SUM('Financials'[Amount]), 'Financials'[Scenario] = "{S}")`;
`YTD {S} Value` = `CALCULATE([Base {S} Value], DATESYTD('DimDate'[Date]))`
L1 (3): `{S} Period Value` =
`Switch(True(), SELECTEDVALUE('Time Period'[Time Period]) = "YTD", [YTD {S} Value], [Base {S} Value])`;
`Actual Period Value LY` = `CALCULATE([Actual Period Value], DATEADD('DimDate'[Date], -1, YEAR))`
L2 (66): per A: `{S} {A}` =
`calculate([{S} Period Value], filter('Accounts', 'Accounts'[Account] = "{A}"))`
and `Actual {A} LY` = `calculate([Actual Period Value LY], filter('Accounts', 'Accounts'[Account] = "{A}"))`
L2b (15): for each of S=Actual, S=Budget, and the "Actual … LY" family:
`{F} Total Income` = 4-term sum of the account measures; `{F} Total Cost of Sales` = 5-term sum;
`{F} Gross Profit` = `[{F} Total Income] + [{F} Total Cost of Sales]`;
`{F} Total Operating Expenses` = 13-term sum; `{F} Net Profit` = `[{F} Gross Profit] + [{F} Total Operating Expenses]`
(the LY family names: `Actual Total Income LY`, etc.)
L3 (6): the report binds ONLY these; each is one `Switch(True(), …)` with **27 branches** of
`SELECTEDVALUE('P&L Rows'[Line]) = "<byte-exact label>"`:
- `Slow Actual Value` → branch value = the matching `[Actual …]` measure (detail lines map to
  `[Actual {A}]`, subtotal lines to the L2b measures)
- `Slow Budget Value` → `[Budget …]`
- `Slow Var Value` → `[Actual …] - [Budget …]` per branch
- `Slow Var % Value` → `format(([Actual …] - [Budget …]) / [Budget …], "0.0%")` per branch
  (yes, FORMAT: returns text; faithful sin)
- `Slow LY Value` → `[Actual … LY]`
- `Slow vs LY Value` → `[Actual …] - [Actual … LY]`
~94 generated measures. TMDL rules: tab indentation, expression body from line 2 (blank line
after `=`), NO `///` lines in generated block, no blank line inside any expression.

### Model validation (model agent runs before finishing)
```powershell
Add-Type -Path "C:\Program Files\DAX Studio\bin\Microsoft.AnalysisServices.Tabular.dll"
$db = [Microsoft.AnalysisServices.Tabular.TmdlSerializer]::DeserializeDatabaseFromFolder("PL Bridge Demo.SemanticModel\definition")
$db.Model.Tables | Select-Object Name, @{n='Measures';e={$_.Measures.Count}}, @{n='Columns';e={$_.Columns.Count}}
$db.Model.Relationships | Select-Object Name, CrossFilteringBehavior
```
Must deserialize clean; 00_Measures ≈ 108 measures (8 fast + 5 cards + 2 teaching + ~94 slow +
Dates Selected); the P&L Lines→Accounts relationship must show CrossFilteringBehavior BothDirections.

---

## 4. Report (report agent)

Folder `PL Bridge Demo.Report\`; definition.pbir byPath `../PL Bridge Demo.SemanticModel`;
.platform displayName `PL Bridge Demo`, new GUID. Read
`~/.claude/rules/tmdl-pbir-authoring.md` + `~/.claude/rules/pbir-cli.md` first: column-bound
projections must be hand-authored visual.json (pbir CLI cannot author them on this machine).
Crib visual JSON shapes from the old lab report (tableEx) and the Claude Theme report
(cardVisual, advancedSlicerVisual, slicer). New GUIDs for every page/visual/filter name.

**Theme:** the custom theme JSON ships in this repo at
`PL Bridge Demo.Report\StaticResources\RegisteredResources\`. Reproduce the report.json
`themeCollection` (baseTheme `Fluent2-CY26SU07` SharedResources + customTheme
`Claude_Design45464656863167763.json` RegisteredResources, both with `reportVersionAtImport`)
and its `resourcePackages` entries (no custom visuals). Report-level settings crib.

All pages 1600×900. Statement pages share the same layout so slow vs fast is a fair visual
A/B. Fresh uuid4().hex[:20] for every filterConfig filter name.
tableEx projections carry NO `active` property and the Values bucket NO `showAll`:
`active: true` on the first projection silently drops every later column from the render
(pbir validate does not catch it; verified on this build). `active` is a pivotTable concept.

### Page 1 : `Overview` (active page)
- Title textbox "Brightside Home & Living: P&L Lab", subtitle line naming the method
  ("one P&L written twice: classic SWITCH vs the bridge").
- 4 cardVisuals: `Total Income $`, `Gross Profit $` (+`Gross Margin %` as reference label or a
  5th card), `Net Profit $`, `Net Profit vs Budget %`.
- columnChart: `Total Income $` by DimDate[Month & Year] (or Start Of Month): monthly income.
- donutChart: `Total Income $` by Stores[Channel].
- Textbox block: 2-3 sentences on the experiment + placeholder timing line
  "SWITCH: ~X ms · Bridge: ~Y ms (measured on this model)": leave X/Y literal placeholders;
  they are patched after timing.
- Year slicer (DimDate[Year], advancedSlicerVisual tile style).
- Page filter: none (whole history).

### Page 2 : `P&L - Classic SWITCH`
- The statement: tableEx ~x=430 y=120 w=1120 h=740. Values projections in order:
  1. Column 'P&L Rows'[Line]: displayName `P&L Line`
  2. Measure [Slow Actual Value] : `Actual`
  3. [Slow Budget Value] : `Budget`
  4. [Slow Var Value] : `Var`
  5. [Slow Var % Value] : `Var %`
  6. [Slow LY Value] : `LY`
  7. [Slow vs LY Value] : `vs LY`
  sortDefinition ascending on the Line column; totals disabled.
- Left rail x≈20 w≈380: `Dates Selected` card (top), slicers: Year (tiles),
  Month (DimDate month-in-year column with correct sort, dropdown), 'Time Period'[Time Period]
  (tiles), Stores[State] (dropdown), Stores[Channel] (tiles), Products[Category] (dropdown).
  Slicer heights ≥ 76px. A small warning textbox: "Classic pattern, every cell plans all 27
  branches. Feel the lag when you slice."
- Page filters (filterConfig): DimDate[Year] = 2026; 'Time Period'[Time Period] = "Selected Period".

### Page 3 : `P&L - Fast Bridge`
Identical layout/slicers/filters to page 2 (fair A/B), except:
- Statement column 1 projection: 'P&L Lines'[Line] (the bridge table), displayName `P&L Line`.
- Measures 2-7: [P&L Actual]/[P&L Budget]/[P&L Var]/[P&L Var %]/[P&L LY]/[P&L vs LY], same
  displayNames.
- Textbox: "Same statement, zero SWITCH branches: the rows ARE the filter."

### Page 4 : `How the Bridge Works`
The teaching page. Left→right:
1. Textbox with the 3-step recipe (rows table on the visual; bridge CSV maps line→accounts;
   relationship does the rest: quote BRIDGE-METHOD.md's one-sentence summary).
2. The mini P&L: tableEx, projections 'P&L Lines'[Line] + [Demo Actual] (`Actual`) +
   [Demo Budget] (`Budget`), **visual-level filter** 'P&L Lines'[Line] IN
   ("Total Income", "Net Profit"): a 2-row × 2-column P&L.
3. Textbox printing the ENTIRE DAX of `Demo Actual` and `Demo Budget` verbatim (that is the
   whole trick: two lines each).
4. tableEx showing the bridge itself: 'P&L Lines'[Line], [LineClass], [Account], visual-level
   filter Line IN ("Total Income", "Gross Profit") so the subtotal-as-extra-rows idea is visible.
5. Small note: "Subtotals are rows in a CSV, not measures. Adding a P&L line = adding data."

`pbir validate "PL Bridge Demo.Report"` must pass
(schema errors fatal; UNDERSIZED/OVERFLOW advisories acceptable). pages.json lists all 4 pages,
activePageName = Overview.

---

## 5. Verification queries (verify agent)

Author (crib `scripts\pl_table_query.dax` / `verify_persisted.dax` / `bridge_minimal.dax`):
- `demo_slow_query.dax`: SUMMARIZECOLUMNS('P&L Rows'[Line], 'P&L Rows'[Sort], filters
  TREATAS({2026}, DimDate[Year]) + TREATAS({"Selected Period"}, 'Time Period'[Time Period]),
  the six Slow measures), ORDER BY Sort.
- `demo_fast_query.dax`: same shape over 'P&L Lines'[Line]/[LineKey] with the six fast measures.
- `demo_tieout.dax`: one query returning, per line, slow vs fast for all six columns with an
  `ABS(diff) > 0.005` flag (Var % compared as FORMAT of the fast value vs the slow text);
  expected result: 0 flagged rows.
These run later against a live Desktop instance via `scripts\time_query.ps1 -QueryFile <f>`.

## 6. Shared rules

- Quote every path (spaces). PowerShell for .NET/DLL; Bash blocks calling `pbir` need
  `export PYTHONIOENCODING=utf-8 PYTHONUTF8=1`.
- Stay in your lane: data agent → `data\demo\` + `scripts\demo\generate_demo_data.py`; model
  agent → `PL Bridge Demo.SemanticModel\` + `PL Bridge Demo.pbip` + `scripts\demo\gen_demo_measures.py`;
  report agent → `PL Bridge Demo.Report\` only; verify agent → `scripts\demo\*.dax` + read-only checks.
- Do NOT touch the original `PL Switch Lab.*` project or `data\*.parquet` at the data root.
- Power BI Desktop must NOT be launched by build agents (orchestrator handles refresh/timing).
- Line labels are a byte-exact contract across pl_lines.csv, 'P&L Rows', the SWITCH
  measures, and page-4 visual filters. Copy from §2, never retype.

---

## 7. Addendum 2026-08-23 (v2): wider, heavier, prettier

Built on top of the above; where they conflict, this section wins:

- **Fact grew to ~75M rows** for a more painful SWITCH demo: TRADE_P 0.45→0.65, ranging
  16 of 24 retail stores + all 3 DCs (20 pairs/product). Knobs recorded in the generator.
- **The statement now has 14 measure columns** (both implementations, same order/labels):
  Actual, Budget, Var, Var %, LY, vs LY, vs LY %, then the YTD set: YTD Actual, YTD Budget,
  YTD Var, YTD Var %, YTD LY, YTD vs LY, YTD vs LY %. Statement pages are 2000×900; the
  tableEx sits x=420 w=1560. The Time Period slicer is REMOVED from the statement pages
  (the page filter still pins 'Time Period' = "Selected Period", so the slow stack's
  period-switch layer still evaluates); YTD lives in the columns instead.
- **Dynamic format strings** (`formatStringDefinition`) on every $ measure in BOTH stacks:
  >=1M → `$#,##0,,.0"M"`, >=1K → `$#,##0,.0"K"`, else `$#,##0`, negatives in parens.
  TMDL shape rules (all three verified the hard way): it is a CHILD OBJECT: placed AFTER
  the scalar properties, blank-line separated, expression inline; and a measure may NOT
  carry both `formatString:` and `formatStringDefinition` (Desktop refuses the project).
  % measures keep static `0.0%` (fast) / FORMAT-text (slow, the faithful sin: on all four
  % columns).
- **Slow stack v2** (~184 generated measures): full YTD measure families
  (`{S} {A} YTD`, `Actual {A} YTD LY`, YTD subtotal pyramids) and 14 27-branch L3 SWITCHes.
  NO iferror on branches: it was tried and removed as cheating (it alone doubled the slow
  side: 2,757 → 5,997 ms cold; noted in PL-BRIDGE-DEMO.md as an anti-IFERROR data point).
- Fast stack v2: 8 new short measures (`P&L vs LY %` + the 7 YTD twins); scenario predicate +
  DATESYTD/DATEADD remain the only CALCULATEs.
- **All SWITCH measures hoist `SELECTEDVALUE` into a `VAR __Line` at the top of the expression**
  and reference the variable in every branch (2026-08-24). Applies to the Slow P&L stack, the
  Odd Rows SWITCH stack, and the dynamic format strings. Measured performance-neutral (±3%):
  it is a readability rule, enforced by the generators.
- **Page 7 `Odd Rows P&L - SWITCH`**: the SWITCH counterpart of page 6 as shipped model
  objects : `'P&L Odd Rows'` (13-row disconnected axis) + 14 `Slow NM …` measures of 13
  branches each, folder `07 Odd Rows SWITCH`. Same 182 cells, same leaf measures, so the only
  variable is dispatch. Generator: `scripts\demo\gen_odd_rows_switch.py`.
- **All pages are 2000×1000 or 1600×1000** so no visual scrolls internally.
- **Page 6 `Odd Rows P&L`** (2026-08-24, generator `scripts\demo\gen_odd_rows.py`): the
  both-axes-awkward case. 13 field-parameter rows (`'P&L Odd Rows Fields'`) × 14 calculation-group
  columns (`'P&L View'`: Actual/LY/vs LY/vs LY %/Budget/Var to Budget/Var to Budget %, period
  and YTD) = 182 cells from 14 measures + 14 calc items. Row measures (`NM *`, folder
  `06 Odd Rows P&L`) are scenario- AND time-agnostic; the calc group owns both. Format strings
  come from DAX UDFs in `definition\functions.tmdl` (`Fmt.Money`, `Fmt.PL`) called as
  `formatStringDefinition = Fmt.PL ( SELECTEDMEASURE ( ), SELECTEDMEASUREFORMATSTRING ( ) )`.
  **Model compatibilityLevel bumped 1606 → 1702** (UDF requirement). Offline validation must
  now use `scripts\demo\validate_model.ps1` (the local AMO cannot parse `functions.tmdl`).
  Measured 1,597 ms cold / 1,093 ms warm; the SWITCH equivalent of the same grid is 1,400 ms:
  documented as an honest boundary condition, not a speed win.
- **Page 5 `Beyond Accounts`**: field-parameter hybrid for non-account lines. 'P&L Hybrid'
  field parameter (labels + NAMEOF + order) in a matrix VALUES well with valuesOnRow, Columns
  = DimDate[Year]; account lines are one-liner bridge-reuse wrappers
  (`CALCULATE([P&L Actual], 'P&L Lines'[Line] = "…")`), odd lines plain measures
  ([Gross Margin %], [Hybrid Income per Store]). Measure params dispatch ONLY from measure
  wells; PBIR binding = expanded projections + `fieldParameters` marker (see
  tmdl-pbir-authoring rules).
