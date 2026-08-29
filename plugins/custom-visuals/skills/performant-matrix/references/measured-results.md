# Measured results: the evidence base

Nine builds of the same problem, measured under one protocol on one afternoon, plus the field case
that started it. This is the file to quote numbers from. Do not round them differently and do not
extrapolate them onto a reader's model: see "What these numbers are not" at the end.

The point of measuring nine builds together is that the interesting comparisons are not only "slow
versus Deneb". They are also **calculation group versus `SWITCH`**, **one calculation group versus
two**, and **bridge versus Deneb**, and those only mean something if nothing else moved between the
runs.

## The measurement protocol

Reproducing these numbers needs all five of the following, because each one of them moved a result
by more than the differences being reported.

1. **Power BI Desktop, Performance Analyzer, `Refresh visuals`.** Not a page click. Revisiting a
   page can serve from the report canvas cache and log a misleading 0 ms.
2. **Pin the slicers, page by page, and verify.** One year selected, every other slicer clear, on
   every page being compared. Rail slicers are usually cloned per page rather than synced, so a
   stray month selection on one page compares a twelfth of the data against all of it.
3. **`ClearCache` over XMLA before each page**, so run 1 is genuinely cold rather than warmed by
   whatever the previous page touched.
4. **Two runs per page**, cold then warm, with the Performance Analyzer log cleared between them.
5. **One visual read per page**, the statement itself. Slicers, textboxes and images are measured
   too and reported separately: on the fast pages they are the bulk of the page total, and quoting
   a page total would flatter the slow pages.

Automated end to end by a PowerShell sweep that drives Performance Analyzer through UI Automation
and reads the durations back out of the pane, so every page gets the same sequence of actions in
the same order.

> **What skipping step 2 costs.** These numbers replace an earlier 9,133 ms / 370 ms pair for the
> monthly matrix. Those were measured with a month still selected on the rail, so the matrix was
> rendering one month rather than twelve. The mistake is silent and the reading is simply void.
> Pin the context first or do not measure at all.

Rig: fact table 74,876,172 rows, Power BI Desktop 2.157.879.0 (26.08), measured 2026-08-28.

## The nine builds

Cold is after `ClearCache`. Warm is the immediately following `Refresh visuals`. One statement
visual per build; page chrome is reported separately below.

| # | Statement | Technique | Visual | Cold | Warm |
|---|---|---|---|---|---|
| 1 | Accounts | `SWITCH` over a disconnected row table | `tableEx` | **4,815 ms** | **4,594 ms** |
| 2 | Accounts | physical bridge table + relationship | `tableEx` | **348 ms** | **319 ms** |
| 3 | Accounts | Deneb grid, 6 base measures | Deneb | **294 ms** | **160 ms** |
| 4 | Odd rows | field parameter rows x calculation group columns | `pivotTable` | **6,317 ms** | **5,634 ms** |
| 5 | Odd rows | `SWITCH` rows x 14 shipped measures | `tableEx` | **1,680 ms** | **1,303 ms** |
| 6 | Odd rows | calculation group on rows AND columns | `pivotTable` | **7,530 ms** | **7,238 ms** |
| 7 | Odd rows | Deneb grid, 10 base measures | Deneb | **419 ms** | **318 ms** |
| 8 | Monthly | 15-item calculation group x 28 measures | `pivotTable` | **12,412 ms** | **11,823 ms** |
| 9 | Monthly | Deneb grid, 12 rows x 10 measures | Deneb | **332 ms** | **170 ms** |

## Comparison A: rows that ARE a filterable account set

27 statement lines x 14 columns. Every row is a set of general ledger accounts, so the rows can be
turned into data.

| Build | Cold | Warm | vs `SWITCH` |
|---|---|---|---|
| `SWITCH` over a disconnected table | 4,815 ms | 4,594 ms | |
| Bridge table + relationship | 348 ms | 319 ms | **13.8x cold, 14.4x warm** |
| Deneb grid | 294 ms | 160 ms | **16.4x cold, 28.7x warm** |

**The bridge wins on effort, not on time.** It gets 99% of the improvement Deneb gets, it stays a
native visual, and it is a one-off model change that every future visual inherits. Reach for Deneb
on this shape only if you also want the client-side formatting and colour.

## Comparison B: rows that are NOT an account set

13 rows x 14 columns, where eight of the thirteen rows are ratios, per-unit metrics and a distinct
count. No set of accounts produces "Gross Margin %", so the bridge is unavailable and the only
native choices are dispatch of one kind or another.

| Build | Cold | Warm | vs the worst |
|---|---|---|---|
| Two calculation groups (rows and columns) | 7,530 ms | 7,238 ms | |
| Field parameter rows x calculation group columns | 6,317 ms | 5,634 ms | 1.2x |
| `SWITCH` rows x 14 shipped measures | 1,680 ms | 1,303 ms | 4.5x / 5.6x |
| Deneb grid | 419 ms | 318 ms | **18.0x / 22.8x** |

Two findings, and the first is counter-intuitive.

**Removing `SWITCH` made it slower.** Replacing the 13-branch `SWITCH` with a second calculation
group on the rows took the same 182 cells from 1,680 ms to 7,530 ms, 4.5x *worse*. Cost is
instantiation count, not branch count. A shallow `SWITCH` evaluated once beats a calculation group
that rewrites the whole cell expression per item, and with two groups stacked the higher-precedence
group's format string wins and re-evaluates on top. "Calculation groups are the modern replacement
for `SWITCH`" is not true for performance on this shape.

**Deneb wins where the bridge cannot go.** These are exactly the rows the bridge method excludes,
and the grid does not care: the ratios are arithmetic on the ten base measures, computed in the
spec at zero query cost.

## Comparison C: the monthly matrix, and the subtraction

15 period columns from a calculation group x 28 measures on rows, 21 of them carrying a dynamic
format string that reads its own measure back. This is the shape reproduced from the unrenderable
matrix below.

| | Calc group | Deneb grid | Ratio |
|---|---|---|---|
| **Performance Analyzer, cold** | **12,412 ms** | **332 ms** | **37.4x** |
| **Performance Analyzer, warm** | **11,823 ms** | **170 ms** | **69.5x** |
| DAX query, cold | 2,178 ms | 124 ms | 17.6x |
| DAX query, warm | 1,228 ms | 17 ms | 72.2x |

**12,080 ms removed from the cold render, a 97.3% reduction.**

Query timings were taken with the grid query run **first**, so the grid's cold number is genuinely
cold and the dispatch query's cold number is the one contaminated by a warmed storage engine. The
bias runs against the result being reported, which is the safe direction.

### 82% of the cost is invisible to a DAX profile

Read the matrix's two cold numbers together:

```
visual            12,412 ms
query behind it    2,178 ms
                 -----------
unaccounted for   10,234 ms      = 82% of what the user waits for
```

That 10,234 ms is not in the query and never will be, because an `EVALUATE` does not evaluate a
`formatStringDefinition`. It is 315 cells each re-running their own measure to choose a format
string, plus the render of 420 cells.

The same subtraction on the grid is the honest control: 332 ms visual against 124 ms query, a gap
of 208 ms for a render of the same 420 cells. The grid pays the render and nothing else.

Optimise only what the query profile shows and you would tune 2,178 ms while 10,234 ms sat
somewhere you were not looking. This is why the workflow measures the visual and the query
separately, and it is the single most useful number in this file.

**The narrower A/B on the same tax:** 182 cells went from **622 ms to 1,270 ms warm** purely from
adding a dynamic format string that references its own measure. If a visual is much slower than a
DAX timing says it should be, suspect this before suspecting the render layer.

## The field case: the unrenderable matrix

The first end-to-end production test of the method, on a client production report. Everything that
matters about the case is structural.

Call it **the unrenderable matrix**, because that is its most useful property. In Power BI Desktop
it was merely very slow. Published to the Power BI Service, the visual **did not render at all**:
it returned an error where the numbers should have been. Past a certain amount of dispatched
evaluation a visual stops being slow and starts being broken, and no amount of waiting fixes it.

| | Visual | Performance Analyzer |
|---|---|---|
| Before | `pivotTable`, 28 measures x a 15-item calculation group | **10,984 ms** (and an error in the Service) |
| After | Deneb grid, same numbers | **406 ms** |

**27x faster. 10,578 ms removed, a 96.3% reduction.** Both measured 2026-08-28 by the report author
on the same filter context, on the same machine, against the live model.

The rebuild required **no semantic model change and no new DAX**. Not one measure, calculated
column, calculation item or report-level extension measure was added, and none was edited. The same
10 base measures the matrix already used are the only things the new visual asks the engine for.

What it was paying for:

- **Cost (a), as a calculation group rather than a `SWITCH`.** 15 items on the Columns axis x 28
  measures on Values = **420 dispatched cell evaluations per render**. Twelve of the fifteen items
  are the same scan with a different literal, and the plan cannot see that. The mechanism does not
  care about the syntax: a calculation group on an axis is row dispatch.
- **Cost (b), 315 cells of dynamic format string.** 21 of the 28 measures carry a
  `formatStringDefinition` whose first line is `VAR __value = ABS ( SELECTEDMEASURE () )`, so each
  rendered cell evaluates its measure a second time, through the calculation item, just to choose
  between `M`, `K` and plain. 21 measures x 15 columns = 315 cells paying that tax, none of it
  visible to `EVALUATE`.
- **Cost (c): none.** No conditional-formatting measures were bound to the visual.

The remaining 7 measures return blank and render section captions. They cost almost nothing
individually, but they are still 7 more measures the dispatch plan has to be able to produce across
all 15 columns.

**Why not the bridge.** Its precondition is that the rows *are* a filterable account set. These
rows are ratios and variances of each other, so there is no column you could filter to produce
them. The derivation has to happen somewhere, and the point of the grid is that it happens in the
browser instead of the formula engine.

**One supporting reading.** An earlier Performance Analyzer run on the untouched matrix, a
different run to the 10,984 ms headline, reported 11,035 ms total of which 10,568 ms was DAX. That
says the per-cell tax was the smaller share of a very large number and the dispatch was the bulk of
it, which is the opposite split to the reproduction below. Both splits are real; measure yours
rather than assuming either.

**Not run:** a cell-for-cell tie-out against the calculation group. The 27x is a Performance
Analyzer comparison of two visuals.

### The field case reproduced in the open

Build 8 and build 9 above are the same case rebuilt on a model that ships, so the before and after
can be measured on a machine you control.

| | Field | Reproduction |
|---|---|---|
| Column axis | 15-item calculation group | 15-item calculation group |
| Row axis | 28 measures on Values, values-on-rows | 28 measures on Values, values-on-rows |
| Dispatched cell evaluations | 420 | 420 |
| Measures with a self-referencing dynamic format string | 21, giving 315 cells | 21, giving 315 cells |
| Irreducible base measures | 10 | 10 |
| Fact rows | not disclosed | 74,876,172 |

**420 dispatched cell evaluations became one query returning 12 rows x 10 measures**, in both
builds. The spec renders 315 data cells from it.

## Correctness gates measured alongside

Speed numbers only count if the rebuild agrees with what it replaced. Two independent gates, both
green on the reproduction:

| Gate | What it proves | Result |
|---|---|---|
| DAX tie-out query | every one of the 315 cells, computed through the calculation group and again by deriving it from the flat dataset the way the spec does, agrees to a relative 1e-9 | **0 bad cells** of 315, 15 of 15 columns |
| Node spec verifier | the Vega spec's 315 cells against an independent Python recomputation of the same DAX rules, plus a regression guard | **0 bad cells**, guard ok |

The two gates check different things and you want both. The DAX tie-out proves the *derivation* is
right against the live model. The verifier proves the *spec* implements that derivation, on
synthetic rows built to hit the awkward cases: a zero denominator, a blank numerator, and periods
with no actuals at all. `pbir validate --fields` separately resolved all 224 field bindings against
the local model, including the calculation-group column, the 28 measures and the aggregated helper
column.

One scope note that decides whether a trap applies to you. The field rebuild lost most of a day to
an unregistered calendar column in the `GROUP BY` silently blanking every `DATEADD` measure. It
does **not** reproduce on the lab model, because that date table is a *classic marked date table*
(`dataCategory: Time` plus a key date column), so `DATEADD` removes filters from **every** column of
the table and a helper column in the `GROUP BY` cannot go stale. The trap belongs to the modern
`calendar` object, where registration is explicit and partial. Check which one your model has
before deciding you are safe, and bind helper columns as aggregations either way: that shape is
correct on both kinds of model and costs nothing.

## Page chrome, for context

The same four slicers, one image and five or six textboxes appear on every page compared. On the
fast pages they are most of the page total, which is why the statement visual is reported on its
own above.

| Element | Typical cold | Typical warm |
|---|---|---|
| Four slicers | 160-290 ms each | 130-260 ms each |
| Image | 75-80 ms | 55 ms |
| Text box (five or six per page) | 59-81 ms each | 36-40 ms each |

A Deneb statement at 170 ms warm is faster than any one of the four slicers next to it. At that
point the statement has stopped being the bottleneck on the page, which is the actual goal.

## What these numbers are not

**One machine, one session, one model.** Reproducible on the file they were taken from. They are
not a distribution across hardware or across models, and a reader's absolute milliseconds will
differ. The *ratios* are the transferable part, and only on a matching shape.

**Not a claim that Deneb is always faster.** Build 2 is a native `tableEx` at 348 ms because the
bridge removed the dispatch from the model. When the rows are a filterable account set, fix the
model and keep the native visual.

**Not a claim about which cost dominates.** The reproduction is 82% per-cell tax; the field case's
supporting run split the other way. Run the subtraction on the visual in front of you.

**The base measures are the floor.** The grid removes dispatch, per-cell format strings and
per-cell conditional formatting. It does not make `SUM` over 74.9M rows faster. On the lab model
that floor is 17 ms warm; on a model whose base measures cost 800 ms, 800 ms is what you get, and
no visual technique goes below it.
