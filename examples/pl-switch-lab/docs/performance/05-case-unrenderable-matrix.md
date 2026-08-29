# Field case: the unrenderable matrix, 10,984 ms → 406 ms

The first end-to-end production test of the method in this folder, on a client production report.
The client, the report and its model objects are not named here; everything that matters about the
case is structural, and the structure is common enough that you will recognise it.

Call it **the unrenderable matrix**, because that is its most useful property. In Power BI Desktop
it was merely very slow. Published to the Power BI Service, the visual **did not render at all**:
it returned an error where the numbers should have been. That is the line this method is really
for: past a certain amount of dispatched evaluation a visual stops being slow and starts being
broken, and no amount of "wait longer" fixes it.

| | Visual | Performance Analyzer |
|---|---|---|
| Before | `pivotTable`, 28 measures x a 15-item calculation group | **10,984 ms** (and an error in the Service) |
| After | Deneb grid, same numbers | **406 ms** |

**27x faster. 10,578 ms removed, a 96.3% reduction.** Both measured 2026-08-28 by the report author
on the same filter context, on the same machine, against the live model.

The rebuild required **no semantic model change and no new DAX**. Not one measure, calculated
column, calculation item or report-level extension measure was added, and none was edited. The same
10 base measures the matrix already used are the only things the new visual asks the engine for.
That constraint was set at the start of the job and it held all the way through: including through
the one model quirk that nearly broke it (below).

## What the matrix was

A 15-item calculation group on the Columns axis, crossed with 28 measures on Values.

```
Columns : 'CG Periods FY YTD YTG'[Period]   -- P1..P12, FY, YTD, YTG
Values  : 28 measures                       -- 21 real, 7 blank section titles
```

The calculation items are the period logic. P1-P12 are each a filter rewrite:

```dax
CALCULATE (
    SELECTEDMEASURE (),
    ALLEXCEPT ( Calendar, Calendar[Fiscal Year] ),
    Calendar[Fiscal Period] = __period
)
```

and YTD/YTG first locate the current period with a `REMOVEFILTERS` probe on a month-offset column
before applying the same shape.

## The diagnosis

Read [01-diagnosing-slow-matrices.md](01-diagnosing-slow-matrices.md) for the framework. This visual
paid two of the three costs.

### Cost (a), as a calculation group rather than a SWITCH

**A calculation group on a matrix axis is row dispatch.** The other documents describe the cost
through its `SWITCH(SELECTEDVALUE(...))` form because that is what the lab was built on, but the
mechanism does not care about the syntax. The group's items are on the Columns axis, so the engine
compiles one plan capable of producing *every* item for *every* measure. Each item rewrites the
calendar filter context differently, which is precisely what stops the engine collapsing P1-P12 into
a single `GROUP BY Fiscal Period` scan: twelve of the fifteen items are the same scan with a
different literal, and the plan cannot see that.

**15 items x 28 measures = 420 dispatched cell evaluations per render.**

If you are reading the symptom table in 01 and your rows or columns come from a calculation group,
you are in row 1 of that table. Same cost, same fix.

### Cost (b), 315 cells' worth of dynamic format strings

**21 of the 28 measures carry a `formatStringDefinition`**: a family of number / dollar / currency
/ percent formatting functions in the model's UDF file. Every one of them opens with

```dax
VAR __value = ABS ( SELECTEDMEASURE () )
```

so each rendered cell evaluates its measure a second time, *through the calculation item*, just to
choose between `M`, `K` and plain. Several also probe a disconnected format-selector table with
`ISFILTERED` on top of that.

21 measures x 15 columns = **315 cells each paying that tax**, and none of it appears in a DAX
benchmark : `EVALUATE` never evaluates a format string. See
[03-format-string-and-cf-tax.md](03-format-string-and-cf-tax.md).

The remaining 7 measures are the blank section-title rows. They return nothing and have static
formats, but they were still 7 more measures the dispatch plan had to be able to produce, across all
15 columns.

### Cost (c): none

No conditional-formatting measures were bound to the visual.

### What was ruled out

Only that one calculation group is active in the matrix query. The page's two button slicers bind
disconnected parameter tables that none of the matrix measures read, so they contribute nothing to
the plan. No other calculation group in the model has an effect here.

## Why not the bridge method

[The bridge method](02-bridge-method.md) is cheaper when it applies, and it did not apply. Its
precondition is that the rows *are* a filterable account set: statement lines you can put in a
physical table and join. These rows are not: they are ratios and variances of each other (an average
price row is sales over units, a margin-percent row is profit over net sales, and every `Var %` row
is a function of two other rows). There is no column you could filter to produce "Avg Price Var to
LY %". The derivation has to happen somewhere, and the whole point of the Deneb template is that it
happens in the browser instead of the formula engine.

## What replaced it

The engine now answers exactly one question, with no calculation group anywhere near it:

```dax
SUMMARIZECOLUMNS (
    Calendar[Fiscal Year],
    Calendar[Fiscal Period],
    Calendar[Period],
    <page filters>,
    "MonthOffset", MIN ( Calendar[Fiscal MonthOffset] ),
    "VolAct",  [Volume Act],    "VolLY",   [Volume LY],
    "SalAct",  [Sales Act],     "SalLY",   [Sales LY],
    "NetAct",  [Net Sales Act], "NetLY",   [Net Sales LY],
    "GPAct",   [GP Act],        "GPLY",    [GP LY],
    "DiscAct", [Discounts Act], "DiscLY",  [Discounts LY]
)
```

**Twelve rows for a single selected year.** Everything else is derived in the Vega spec:

| Derived in the spec | From |
|---|---|
| P1..P12 columns | the group-by, one datum per period |
| FY column | sum of the periods (= the calc item's `ALLEXCEPT` year) |
| YTD / YTG columns | sum of periods `<=` / `>` the current period |
| Avg Price, GP %, Discount % rows | ratios of two base measures |
| every `Var %` / `bps` row | differences and ratios of the rows above |
| every number's format | the model's format-function thresholds reimplemented as Vega `format()` calls |

**420 dispatched cell evaluations became one query returning 12 rows x 10 measures.** The spec
renders 315 data cells from it.

### Deriving "the current period" with no extra DAX

The YTD/YTG split needs to know which period is current. The calculation items get it from a
`REMOVEFILTERS` probe for `MonthOffset = 0`, which is dispatch DAX and had to go.

The month-offset column is built upstream as `(12*FY + Period) - (12*todayYear + todayMonth)`.
Rearranged, `12*FY + Period - MonthOffset` is today's absolute month index, and it is **the same
value on every row**: including rows of a year that is not the current year. So the spec reads it
off any row and takes `((todayIdx - 1) % 12) + 1`. That is the same period number the calc group's
probe finds, carries the same staleness (both are frozen at the last warehouse calendar build), and
costs one `MIN` aggregation instead of a filter rewrite.

### One bug found by rebuilding

Not a performance finding, but worth recording because it is the kind of thing a rebuild surfaces.
The matrix's sales variance row bound a `Var % LY to Act` measure : `DIVIDE(LY - Act, Act)`, while
the other six variance rows all bound the `Act to LY` direction. Its sign therefore read backwards
against its own label and against every row around it. It went unnoticed for as long as the numbers
were black; it became obvious the moment the rebuild put green and red on the sign.

The grid derives `DIVIDE(Act - LY, LY)` instead. The original matrix still carries the old measure,
so that one row differs between the two visuals by design.

## The two traps, both of which shipped wrong before they shipped right

### 1. An unregistered calendar column in the GROUP BY silently blanks time intelligence

This one cost the most time and generalises well beyond this report.

The date table has a modern `calendar` object, and the LY measures go through
`CALCULATE ( __amount, DATEADD ( <calendar>, -1, YEAR ) )`. The calendar object registers five
column groups (year, quarter, month, monthOfYear, weekOfYear) and the month-offset column is
**not** among them.

**`DATEADD` shifts filters only on registered columns.** An unregistered column of the same table
sitting in the `GROUP BY` survives the year shift untouched: FY2027 P1 carries MonthOffset −1,
FY2026 P1 carries −13, and after the shift the stale −1 filter matches no last-year row. Every `*LY`
measure returns `BLANK`.

The failure is completely silent: no error in Desktop, none from `pbir validate`, none in Deneb's own
log pane. The `Act` columns were perfect because they never call `DATEADD`; only the LY rows were
empty, which reads as a data problem rather than a query-shape problem.

The fix needs no DAX and no model change: **bind the column as an aggregation, not a grouping
field.** In PBIR that is an `Aggregation` field with `Function: 3` (`Min`):

```json
{
  "field": { "Aggregation": {
      "Expression": { "Column": {
          "Expression": { "SourceRef": { "Entity": "Calendar" } },
          "Property": "MonthOffset" } },
      "Function": 3 } },
  "queryRef": "Min(Calendar.MonthOffset)",
  "nativeQueryRef": "Min of MonthOffset",
  "displayName": "MonthOffset"
}
```

`QueryAggregateFunction`: `0` Sum, `1` Average, `2` DistinctCount, `3` Min, `4` Max, `5` Count,
`6` Median, `7` StandardDeviation, `8` Variance.

It lands in `SUMMARIZECOLUMNS` as an extension column: measure-like, adds no filter, invisible to
`DATEADD`. MonthOffset is constant within a period, so `MIN` returns it exactly.

> **The general rule.** Moving a matrix to a flat grouped query changes which columns are in the
> `GROUP BY`. If any measure in that query does time intelligence over a `calendar` object, only the
> columns registered in that object are safe to group. Offsets, keys and helper columns must be
> aggregated or dropped. A calculation-group matrix hides this because the calc item rewrites the
> filter context before the measure runs; a flat query does not.
>
> **A classic marked date table does not have this problem.** When the date table is marked as a
> date table (`dataCategory: Time` plus a key date column), `DATEADD` removes filters from *every*
> column of that table, so a helper column in the `GROUP BY` cannot go stale. The trap belongs to
> the modern `calendar` object, where registration is explicit and partial. Check which one you have
> before you decide you are safe. Diagnose it by running the same measure three ways: column
> grouped, column aggregated, column absent, and asserting that the last two agree.

A first attempt blamed a primary/associated column distinction instead. That was wrong, both of
those columns are registered and either is safe to group. The report author found the real cause by
removing fields in Desktop one at a time.

### 2. `null` coerces to `0`, and a wrong grid looks like a right one

When MonthOffset went missing, the current period fell back to `0`, and because JavaScript coerces
`null` to `0`, the YTG filter `datum.Period > datum.curP` was true for **every** period. YTG silently
rendered the full year and looked entirely plausible on the canvas.

That is the worst failure mode a client-side grid has: no error, no blank, just wrong numbers in the
right shape. The spec now guards every input with `isValid` and lets `curP` be `null`, so both YTD
and YTG **fail closed to blank**: visibly broken beats quietly wrong. The verifier has a regression
test that strips MonthOffset from the dataset and asserts those two columns come back empty.

## What was verified, and how

**Offline, before Desktop ever saw it.** A Node verifier renders the spec headless with
`renderer: "none"` and diffs all 315 cells against an independent Python recomputation of the same
DAX rules: written straight from the rules, *not* from the Vega transforms. Two implementations,
one gate: `BADDIFF 0`.

That diff is what catches DAX-semantics drift, and the semantics are fiddly enough to need it:

- `DIVIDE(n, d)` returns `BLANK` when `d` is blank or `0`, **and** when `n` is blank.
- `a - b` returns `BLANK` only when *both* are blank; otherwise a blank behaves as `0`.
- A sum over nothing is `BLANK` in DAX but `0` in Vega, so each aggregate carries a `valid` count
  alongside its `sum` and a guard restores the blank.

Get the second rule wrong and future periods stop showing `(100.0%)`, which is what the original
matrix renders and therefore what parity requires.

**In Desktop.** Rendering and numbers confirmed by the report author against the original matrix on
the same page filters, then the 406 ms measured in Performance Analyzer.

**The query level, separately.** A PowerShell harness runs both queries through
[`tools/run_dax.ps1`](tools/run_dax.ps1) and prints the comparison. Two things about that
measurement. **Order matters**, because both queries hit the same base measures: whichever runs
second gets a warmed storage engine. Run the *grid* query first, so the grid's cold number is
genuinely cold and the matrix's cold is the contaminated one; that biases *against* the result being
reported, which is the safe direction. **And the warm pair is the fair comparison**; treat the
matrix's cold number as a floor.

Expect the query gap to be smaller than the 10,578 ms visual gap, and the difference to be real
rather than noise: an `EVALUATE` never evaluates a `formatStringDefinition`, so none of the 315-cell
format-string tax appears in it at all
([03-format-string-and-cf-tax.md](03-format-string-and-cf-tax.md)).

**Not run.** A 10-measure x 15-column cell-for-cell tie-out against the calculation group. The 27x
above is a Performance Analyzer comparison of the two visuals, which is the number that matters here.

For contrast, an earlier Performance Analyzer run on the untouched matrix (a different run to the
10,984 ms headline) reported 11,035 ms total of which 10,568 ms was DAX. That says the matrix's
per-cell tax was the smaller share of a very large number, and the dispatch was the bulk of it.

## What shipped on the canvas

28 rows x 15 columns, laid out to match the matrix it replaces: dark header band, grey (`#F1F1F1`)
section-title rows, every row ruled above and below in the same grey, Segoe UI 12 throughout, and
green/red (`#00B050` / `#C00000`) on the variance rows. All of it is spec-side and costs nothing at
query time, which is the point of
[the conditional-colours section of 04](04-deneb-grid-template.md#conditional-colours-as-static-config).

Two parity gaps, both known and accepted: two rows whose model measures are placeholders are not in
the grid, and a format-selector slicer override is not reimplemented (that slicer is not on this
page). Grid cells do not cross-filter other visuals, matching the house Deneb convention.

## Reproducing it without the client model

This case is reproduced end to end, in the open, on the lab model: see
[07-lab-monthly-matrix.md](07-lab-monthly-matrix.md). Same shape: 15 period columns from a
calculation group, 28 measures on rows, dynamic format strings on 21 of them, built twice in the
same report so the before and after can be measured side by side on a machine you control.
