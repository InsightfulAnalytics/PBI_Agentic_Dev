# Measured results: all nine pages, one protocol

Every implementation in this document set is built in `PL Bridge Demo`, and every one of them is
measured here under the same conditions on the same afternoon. This is the table to quote.

The point of measuring all nine together is that the interesting comparisons are not only
"slow versus Deneb". They are also **calculation group versus SWITCH**, **one calculation group
versus two**, and **bridge versus Deneb**, and those only mean something if nothing else moved
between the runs.

## The protocol

Reproducing these numbers on your own machine needs all five of these, because each one of them
moved a result by more than the differences being reported.

1. **Power BI Desktop, Performance Analyzer, `Refresh visuals`.** Not a page click. Revisiting a
   page can serve from the report canvas cache and log a misleading 0 ms.
2. **`YEAR = 2026` selected, MONTH / CHANNEL / CATEGORY all clear, on every page.** The four rail
   slicers are cloned per page, not synced, so this has to be set page by page and verified. A
   stray `MONTH = Jun` on one page compares a twelfth of the data against all of it. That single
   mistake is the difference between the 9,133 ms this document set used to quote for the monthly
   matrix and the 12,412 ms below.
3. **`ClearCache` over XMLA before each page**, so run 1 is genuinely cold rather than warmed by
   whatever the previous page touched.
4. **Two runs per page**, cold then warm, with the Performance Analyzer log cleared between them.
5. **One visual read per page**, the statement itself. Slicers, textboxes and the logo are
   measured too and reported separately, because on the fast pages they are the bulk of the page
   total and quoting a page total would flatter the slow pages.

Automated end to end by `scripts/demo/pa_sweep.ps1`, which drives Performance Analyzer through
UI Automation and reads the durations back out of the pane, so every page gets the same sequence
of actions in the same order.

Fact table: 74,876,172 rows. Desktop 2.157.879.0 (26.08). Measured 2026-08-28.

## The statement visual on every page

Cold is after `ClearCache`. Warm is the immediately following `Refresh visuals`.

| # | Page | Technique | Visual | Cold | Warm |
|---|---|---|---|---|---|
| 1 | P&L Accounts SWITCH | `SWITCH` over a disconnected row table | `tableEx` | **4,815 ms** | **4,594 ms** |
| 2 | P&L Accounts Fast Bridge | physical bridge table + relationship | `tableEx` | **348 ms** | **319 ms** |
| 3 | P&L Accounts Deneb | Deneb grid, 6 base measures | Deneb | **294 ms** | **160 ms** |
| 4 | Odd Rows P&L | field parameter rows x calculation group columns | `pivotTable` | **6,317 ms** | **5,634 ms** |
| 5 | Odd Rows P&L - SWITCH | `SWITCH` rows x 14 shipped measures | `tableEx` | **1,680 ms** | **1,303 ms** |
| 6 | Odd Rows P&L - 2 Calc Groups | calculation group on rows AND columns | `pivotTable` | **7,530 ms** | **7,238 ms** |
| 7 | Odd Rows P&L - Deneb | Deneb grid, 10 base measures | Deneb | **419 ms** | **318 ms** |
| 8 | Monthly P&L - Calc Group | 15-item calculation group x 28 measures | `pivotTable` | **12,412 ms** | **11,823 ms** |
| 9 | Monthly P&L - Deneb | Deneb grid, 12 rows x 10 measures | Deneb | **332 ms** | **170 ms** |

## The three comparisons that matter

### A. The accounts statement: rows that ARE a filterable account set

27 statement lines x 14 columns. Every row is a set of general ledger accounts, so the rows can be
turned into data.

| Build | Cold | Warm | vs SWITCH |
|---|---|---|---|
| `SWITCH` over a disconnected table | 4,815 ms | 4,594 ms | |
| Bridge table + relationship | 348 ms | 319 ms | **13.8x cold, 14.4x warm** |
| Deneb grid | 294 ms | 160 ms | **16.4x cold, 28.7x warm** |

**The bridge wins on effort, not on time.** It gets 99% of the improvement Deneb gets, it is a
native visual, and it is a one-off model change that every future visual inherits. Reach for
Deneb here only if you also want the client-side formatting and colour. See
[the bridge method](02-bridge-method.md).

### B. The odd-rows statement: rows that are NOT an account set

13 rows x 14 columns, where eight of the thirteen rows are ratios, per-unit metrics and a distinct
count. No set of accounts produces "Gross Margin %", so the bridge is unavailable and the only
native choices are dispatch of one kind or another.

| Build | Cold | Warm | vs the worst |
|---|---|---|---|
| Two calculation groups (rows and columns) | 7,530 ms | 7,238 ms | |
| Field parameter rows x calculation group columns | 6,317 ms | 5,634 ms | 1.2x |
| `SWITCH` rows x 14 shipped measures | 1,680 ms | 1,303 ms | 4.5x / 5.6x |
| Deneb grid | 419 ms | 318 ms | **18.0x / 22.8x** |

Two findings here, and the first one is counter-intuitive:

**Removing `SWITCH` made it slower.** Replacing the 13-branch `SWITCH` with a second calculation
group on the rows took the same 182 cells from 1,680 ms to 7,530 ms, 4.5x *worse*. Cost is
instantiation count, not branch count. A shallow `SWITCH` evaluated once beats a calculation group
that rewrites the whole cell expression per item, and with two groups stacked the higher-precedence
group's format string wins and re-evaluates on top. "Calculation groups are the modern replacement
for `SWITCH`" is not true for performance on this shape.

**Deneb wins where the bridge cannot go.** These are exactly the rows the bridge method excludes,
and the grid does not care: the ratios are arithmetic on the ten base measures, computed in the
spec at zero query cost.

### C. The monthly matrix: the field case, reproduced in the open

15 period columns from a calculation group x 28 measures on rows, 21 of them carrying a dynamic
format string that reads its own measure back. This is the shape that
[would not render in the Power BI Service at all](05-case-unrenderable-matrix.md).

| | Calc group | Deneb grid | Ratio |
|---|---|---|---|
| **Performance Analyzer, cold** | **12,412 ms** | **332 ms** | **37.4x** |
| **Performance Analyzer, warm** | **11,823 ms** | **170 ms** | **69.5x** |
| DAX query, cold | 2,178 ms | 124 ms | 17.6x |
| DAX query, warm | 1,228 ms | 17 ms | 72.2x |

**12,080 ms removed from the cold render, a 97.3% reduction.**

### The subtraction, which is the whole diagnostic

Read the matrix's two cold numbers together. The visual costs **12,412 ms**. The query that feeds
it costs **2,178 ms**. The missing **10,234 ms** is not in the query and never will be, because an
`EVALUATE` does not evaluate a `formatStringDefinition`. That gap is 315 cells each re-running
their own measure to pick between `$x.xM`, `$x.xK` and plain, plus the render of 420 cells.

The same subtraction on the grid: 332 ms visual against 124 ms query, a gap of 208 ms for a
render of the same 420 cells. The grid pays the render and nothing else.

**82% of the slow visual's cost was invisible to every DAX benchmark.** Optimise only what the
query profile shows and you would tune 2,178 ms while 10,234 ms sat somewhere you were not
looking. This is the single reason [01-diagnosing-slow-matrices.md](01-diagnosing-slow-matrices.md)
insists on measuring the visual and the query separately.

## Page chrome, for context

The same four slicers, the same logo and five or six textboxes appear on all nine pages. On the fast pages they
are most of the page total, which is why the statement visual is reported on its own above.

| Element | Typical cold | Typical warm |
|---|---|---|
| YEAR / MONTH / CHANNEL / CATEGORY slicers | 160-290 ms each | 130-260 ms each |
| Image (logo) | 75-80 ms | 55 ms |
| Text box (five or six per page) | 59-81 ms each | 36-40 ms each |

A Deneb statement at 170 ms warm is faster than any one of the four slicers next to it. At that
point the statement has stopped being the bottleneck on the page, which is the actual goal.

## What these numbers are not

**One machine, one session, one model.** Reproducible on this file, and the file ships so you can
reproduce it. They are not a distribution across hardware or across models.

**Not a claim that Deneb is always faster.** Page 2 shows a native `tableEx` at 348 ms because
the bridge removed the dispatch from the model. When the rows are a filterable account set, fix
the model and keep the native visual.

**The base measures are the floor.** The grid removes dispatch, per-cell format strings and
per-cell conditional formatting. It does not make `SUM` over 74.9M rows faster. On this model that
floor is 17 ms warm; on a model whose base measures cost 800 ms, 800 ms is what you get.
