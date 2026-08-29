# Lab reproduction: the monthly matrix

[The field case](05-case-unrenderable-matrix.md) is one data point on a client model nobody else
can open. This is the same case rebuilt in the open, on `PL Bridge Demo`, with both halves in one
report so you can measure the before and the after yourself on a machine you control.

Same shape as the field matrix, deliberately:

| | Field | Lab |
|---|---|---|
| Column axis | 15-item calculation group (P1-P12, FY, YTD, YTG) | 15-item calculation group (Jan-Dec, YTD, YTG, Full Year) |
| Row axis | 28 measures on Values, values-on-rows | 28 measures on Values, values-on-rows |
| Dispatched cell evaluations | 420 | 420 |
| Measures with a self-referencing dynamic format string | 21 → 315 cells | 21 → 315 cells |
| Irreducible base measures | 10 | 10 |
| Fact rows | not disclosed | 74,876,172 |

Two pages in `PL Bridge Demo.Report`:

| Page | What it is |
|---|---|
| **Monthly P&L - Calc Group** | the slow one: a `pivotTable`, `'Period View'` on Columns x 28 measures on Values |
| **Monthly P&L - Deneb** | the fast one: the same 28 x 15 grid from a single query returning 12 rows x 10 measures |

## Results

### Query level, measured

`scripts/demo/time_monthly.ps1`, 3 runs each, `DimDate[Year] = 2026` pinned, grid query run
**first** so its cold number is genuinely cold and the dispatch query's cold number is the one
contaminated by a warmed storage engine: the bias runs against the result being reported.

| Query | Cold | Warm (best of 2) |
|---|---|---|
| Calc-group dispatch (`monthly_dispatch.dax`): 15 rows x 30 columns | **2,178 ms** | **1,228 ms** |
| Deneb grid dataset (`monthly_grid.dax`): 12 rows x 13 columns | **124 ms** | **17 ms** |
| | **17.6x** | **72.2x** |

Neither number contains the per-cell format-string tax. An `EVALUATE` never evaluates a
`formatStringDefinition`, so the 315 cells that re-run their own measure to choose between `$x.xM`,
`$x.xK` and plain are **completely absent from both figures**. The visual gap is therefore larger
than the query gap; how much larger is exactly the subtraction in
[01-diagnosing-slow-matrices.md](01-diagnosing-slow-matrices.md), and it is measured in Performance
Analyzer, not here.

### Visual level, measured

Performance Analyzer, `ClearCache` before each page, both pages refreshed with **Refresh visuals**
(not just a page click: revisiting a page can serve from the report canvas cache and log a
misleading 0 ms), `YEAR = 2026` selected and every other rail slicer clear. Full protocol and the
other seven pages in [08-measured-results.md](08-measured-results.md).

| Page | Visual | PA cold | PA warm |
|---|---|---|---|
| Monthly P&L - Calc Group | `pivotTable` | **12,412 ms** | **11,823 ms** |
| Monthly P&L - Deneb | Deneb grid | **332 ms** | **170 ms** |

**37.4x faster cold, 69.5x warm. 12,080 ms removed, a 97.3% reduction.**

This is the number to quote. It is what a person sitting in front of the report experiences, and
unlike the query timings it includes everything: the dispatch, the 315 cells of format string, and
the render.

> **These numbers replace the 9,133 ms / 370 ms this document used to carry.** Those were measured
> with `MONTH = Jun` still selected on the rail, so the matrix was rendering one month rather than
> twelve. The rail slicers are cloned per page rather than synced, which makes that an easy mistake
> and a silent one. Everything here is now measured with `YEAR = 2026` and nothing else, on every
> page, verified per page before each run.

### The two numbers side by side, and what the gap between them means

| | Calc group | Deneb grid | Ratio |
|---|---|---|---|
| Performance Analyzer, whole visual, cold | **12,412 ms** | **332 ms** | 37.4x |
| Performance Analyzer, whole visual, warm | **11,823 ms** | **170 ms** | 69.5x |
| DAX query, cold | 2,178 ms | 124 ms | 17.6x |
| DAX query, warm | 1,228 ms | 17 ms | 72.2x |

Read the first and third rows together. The matrix's visual is **12,412 ms** but the query behind
it is **2,178 ms cold**. The missing **10,234 ms** is not in the query and never will be, because
an `EVALUATE` does not evaluate a `formatStringDefinition`. That gap *is* cost (b): 315 cells each
re-running their own measure to choose a format string, plus the render. **82% of what the user
waits for is somewhere a DAX profile cannot show you.**

That single subtraction is the most useful thing in this document. It is the reason
[01-diagnosing-slow-matrices.md](01-diagnosing-slow-matrices.md) insists on measuring the visual
and the query separately: optimise only what the DAX profile shows you and you would be chasing
2,178 ms while 10,234 ms sat somewhere you were not looking.

The grid's gap is the honest comparison in the other direction: 332 ms visual against 124 ms cold
query, so ~208 ms of render and overhead for the same 420 cells drawn in the browser. The grid
pays the render and nothing else.

For scale, everything else on the page is unchanged between the two: the four rail slicers cost
160-290 ms each and the text boxes 59-81 ms, on both pages. **The Deneb statement at 170 ms warm
is faster than any single slicer beside it**, which is the real finish line: the statement has
stopped being the slowest thing on its own page.

### Correctness, measured

Two independent gates, both green.

| Gate | What it proves | Result |
|---|---|---|
| `scripts/demo/monthly_tieout.dax` | every one of the 315 cells, computed through the calculation group and again by deriving it from the flat monthly dataset the way the spec does, agrees to a relative 1e-9 | **`BADDIFF_cells` 0** of 315, 15 of 15 columns, current month 8 |
| `scripts/demo/deneb/verify_monthly.mjs` | the Vega spec's 315 cells against an independent Python recomputation of the same DAX rules, plus the MonthOffset regression guard | **`BADDIFF 0`**, guard ok |

The two gates check different things and you want both. The DAX tie-out proves the *derivation* is
right against the live model. The Node verifier proves the *spec* implements that derivation, on
synthetic rows built to hit the awkward cases: a zero denominator, a blank numerator, and months
with no actuals at all.

`pbir validate "PL Bridge Demo.Report" --fields` resolves all 224 field bindings against the local
model, including the calculation-group column, the 28 measures and the `Min(DimDate[MonthOffset])`
aggregation.

## What the slow page does

```
Columns : 'Period View'[Period View]        -- Jan..Dec, YTD, YTG, Full Year
Values  : 28 measures, valuesOnRow = true   -- 21 real, 7 blank section captions
Rows    : (none -- the measures are the rows)
```

Each month item is a filter rewrite:

```dax
CALCULATE (
    SELECTEDMEASURE ( ),
    ALLEXCEPT ( 'DimDate', 'DimDate'[Year] ),
    'DimDate'[MonthOfYear] = 1
)
```

Twelve items that differ only in a literal, and the engine cannot see that. Each one is a
different filter context, so it compiles one plan able to produce every item for every measure
rather than collapsing the twelve into a single `GROUP BY MonthOfYear` scan. That is cost (a),
wearing a calculation group instead of a `SWITCH`.

YTD and YTG add a `REMOVEFILTERS` probe to locate the current month:

```dax
VAR __CurP =
    CALCULATE (
        MAX ( 'DimDate'[MonthOfYear] ),
        REMOVEFILTERS ( 'DimDate' ),
        'DimDate'[MonthOffset] = 0
    )
```

and 21 of the 28 measures carry a format string that reads the measure back:

```dax
formatStringDefinition = Fmt.Money ( [MP Income Act] )
```

That is cost (b), 315 times. The remaining 7 measures return `BLANK()` and render the section
captions: they cost almost nothing individually, but they are still 7 more measures the dispatch
plan has to be able to produce across all 15 columns.

**Nothing here is badly written.** The five statement lines come off the `P&L Lines` bridge, so each
base measure is a single filtered scan. The page is slow because of its *shape*.

## What the fast page does

One query. No calculation group anywhere near it:

```dax
SUMMARIZECOLUMNS (
    'DimDate'[Year],
    'DimDate'[MonthOfYear],
    "MonthOffset", MIN ( 'DimDate'[MonthOffset] ),
    "IncAct", [MP Income Act], "IncLY", [MP Income LY],
    "CogAct", [MP COGS Act],   "CogLY", [MP COGS LY],
    "GPAct",  [MP GP Act],     "GPLY",  [MP GP LY],
    "OpxAct", [MP Opex Act],   "OpxLY", [MP Opex LY],
    "NPAct",  [MP NP Act],     "NPLY",  [MP NP LY]
)
```

Twelve rows for a selected year. The spec derives the rest:

| Derived in the spec | From |
|---|---|
| Jan-Dec columns | the group-by, one datum per month |
| Full Year | sum of the months (= the calc item's `ALLEXCEPT` year) |
| YTD / YTG | sum of months `<=` / `>` the current month |
| Gross Margin %, Opex % of Income | ratios of two base measures |
| every `Var %` / `bps` row | differences and ratios of the rows above |
| every number's format | `Fmt.Money` thresholds and the dynamic percent rule as Vega `format()` calls |
| green / red on the variance rows | a signal on the sign |

**420 dispatched cell evaluations became one query returning 12 rows x 10 measures.** The spec
renders 315 data cells from it, and the per-cell tax goes to zero because there is no server-side
formatting left to pay for.

### The current month, with no extra DAX

`DimDate[MonthOffset]` is `(12*Y + M) - (12*todayY + todayM)`. Rearranged, `12*Y + M - MonthOffset`
is today's absolute month index, and it is the same value on every row. The spec reads it off any
row and takes `((todayIdx - 1) % 12) + 1`: the same month the calc items' `REMOVEFILTERS` probe
finds, carrying the same staleness, for the cost of one `MIN` aggregation.

The verifier's regression guard strips `MonthOffset` from the dataset and asserts YTD and YTG both
come back **empty**. That is deliberate: JavaScript coerces `null` to `0`, so an unguarded
`datum.Month > datum.curP` is true for every month and YTG quietly renders the full year, wrong
numbers in the right shape, which is the worst failure a client-side grid can have.

### Where the field case's worst trap does *not* apply

The field rebuild lost most of a day to an unregistered calendar column in the `GROUP BY` silently
blanking every `DATEADD` measure ([05](05-case-unrenderable-matrix.md#1-an-unregistered-calendar-column-in-the-group-by-silently-blanks-time-intelligence)).
**It does not reproduce here, and the reason is worth knowing.**

`DimDate` in this model is a *classic marked date table* : `dataCategory: Time` plus a key date
column, so `DATEADD` removes filters from **every** column of the table, and a helper column in the
`GROUP BY` cannot go stale. Tested three ways against the live model (column grouped, aggregated,
absent): all three return identical LY values.

The trap belongs to the **modern `calendar` object**, where registration is explicit and partial and
only registered columns get shifted. Check which one your model has before deciding you are safe.
The lab pages still bind `MonthOffset` as a `Min` aggregation rather than a grouping field, because
that shape is correct on both kinds of model and costs nothing.

## The Month slicer does two different jobs, on purpose

The rail is the same four slicers as every other page (Year / Month / Channel / Category),
and keeping MONTH on these two is the point, because it behaves completely differently on each:

| Page | Click a month and... |
|---|---|
| Monthly P&L - Calc Group | DimDate is filtered, so the matrix re-plans and re-runs its dispatched cells. It is visibly, painfully slow. |
| Monthly P&L - Deneb | the dataset query narrows to that month and the grid redraws with just those columns, instantly. |

Same slicer, same click, same model, and the difference in what happens next is the whole
argument for the method, without anyone having to read a number.

A note on what this is *not*: the Deneb page **filters**, it does not highlight. A Power BI
slicer only ever filters; highlighting is a visual-to-visual behaviour, so a slicer cannot dim
the other eleven months and leave them on screen. Getting that effect means moving the grid's
group-by onto a disconnected month table and reading the selection through a flag measure:
which also means the slicer would stop filtering the *matrix*, and the demonstration above
would be lost.

## Files

| File | What it is |
|---|---|
| `scripts/demo/gen_monthly_matrix.py` | the model objects: `'Period View'` (15 items) and the 28 measures. Idempotent, strips its own objects by name |
| `scripts/demo/deneb/gen_monthly_spec.py` | the spec generator: row registry, DAX-parity formulas, format thresholds, styling, **and the row/measure contract both page builders import**. Edit this, never the embedded literal |
| `scripts/demo/deneb/verify_monthly.mjs` | the 315-cell two-implementation diff plus the MonthOffset guard |
| `scripts/demo/deneb/render_vega.mjs` | offline Vega → PNG (the shared `render_local.mjs` compiles Vega-Lite and rejects these specs) |
| `design/build_monthly_pages.py` | both pages, cloned from an existing top-strip page so the design is identical by construction |
| `scripts/demo/gen_monthly_queries.py` | emits the three measurement queries from the shared contract |
| `scripts/demo/monthly_dispatch.dax` | the before query |
| `scripts/demo/monthly_grid.dax` | the after query |
| `scripts/demo/monthly_tieout.dax` | the 315-cell tie-out, gate `BADDIFF_cells = 0` |
| `scripts/demo/time_monthly.ps1` | runs both timing queries in the honest order and prints the comparison |

## Running it yourself

```powershell
# 1. model objects and pages  (Power BI Desktop must be CLOSED -- both scripts refuse otherwise)
python scripts\demo\gen_monthly_matrix.py
python design\build_monthly_pages.py
pbir validate "PL Bridge Demo.Report" --fields

# 2. offline gates, no Desktop needed
python scripts\demo\deneb\gen_monthly_spec.py
node   scripts\demo\deneb\verify_monthly.mjs
node   scripts\demo\deneb\render_vega.mjs scripts\demo\deneb\monthly-pl.preview.vg.json out.png

# 3. open Desktop, then measure
python scripts\demo\gen_monthly_queries.py
powershell -File scripts\demo\time_monthly.ps1 -Runs 3
powershell -File docs\performance\tools\run_dax.ps1 -QueryFile scripts\demo\monthly_tieout.dax -Runs 1
```

### Two build traps worth knowing

Both cost real time here, both are silent, and both are now guarded in the generators.

**A measure's expression body must be indented one level deeper than its properties.** Three tabs
for the DAX, two for `displayFolder` / `lineageTag` / `formatStringDefinition`. Write the expression
at the same level as the properties and the parser reads `displayFolder:` and everything after it as
*more DAX*: the file still parses clean, the `formatStringDefinition` silently disappears, and the
measure's expression is quietly corrupt. Caught by asserting the round-trip: deserialize the folder
and count the measures that actually carry a format string, do not just check that it parsed.

**`ADDCOLUMNS` cannot see its own siblings.** The Vega spec chains formula transforms, so
`gm_var` can read the `gm_act` computed immediately above it. DAX has no equivalent: a column added
by `ADDCOLUMNS` is invisible to the other columns in the same call. The tie-out therefore derives in
two passes, splitting exactly on that dependency.
