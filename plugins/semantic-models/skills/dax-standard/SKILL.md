---
name: dax-standard
version: 26.40.3
description: House style for writing DAX measures. Build the rows a calculation needs into a table VAR, then aggregate, so each step can be debugged. Covers measure formatting (dynamic format strings, UDFs), the time-intelligence exception and recipes. Use to write, rewrite, review or format a measure, or for a DAX recipe. For a measurably slow measure, use `semantic-models:dax-optimisation`.
---
# Standard DAX

**This is how measures get written here.** Not a style preference to be argued per measure —
the default shape for every new measure in this repo, and the shape to rewrite an inherited
measure into when it needs to be understood or fixed.

The style is *table-first*: think in tables, rows and columns rather than in filter-context
manipulation. Filter a table down to exactly the rows the calculation needs, then aggregate
over it with an X-function, naming each step with a `VAR`. The result reads top-to-bottom
like prose, and — the part that pays for itself — **every intermediate step can be inspected
on its own** (see [debugging](#the-killer-feature-debug-by-swapping-the-return)).

This is not a performance trade-off in the typical case: the formula engine usually compiles
the explicit form and the equivalent `CALCULATE` form to the same query plan. Where it does
not, that is a measured, specific finding — hand it to `semantic-models:dax-optimisation`
rather than pre-optimising by writing something harder to read.

## The core pattern

```DAX
Measure =
    VAR __Input  = <scalar setup, e.g. MAX( Dim[Key] )>          -- 1. scalar VAR(s)
    VAR __Table  = FILTER( <table>, <conditions using __Input> ) -- 2. build a virtual table
    VAR __Result = SUMX( __Table, <row expression> )             -- 3. X-aggregate over it
    RETURN
        __Result                                                 -- always return a __Result VAR
```

Three steps: **(1)** capture the scalars you need out of the current context, **(2)** build a
table variable holding the rows the calculation runs over, filtered on dimension columns
([Filter the dimension, not the fact](#filter-the-dimension-not-the-fact)), **(3)** reduce it — usually with an
X-aggregator, sometimes with `CALCULATE` (see
[Step 3 is not always an X-aggregator](#step-3-is-not-always-an-x-aggregator)). Complex measures
grow to dozens of lines — the *shape* stays the same.

Naming conventions (non-negotiable, they make measures greppable and diffable):

- Prefix variables with `__` (double underscore) — avoids reserved words and mirrors the
  variable names the engine generates in its own queries.
- Name the final variable `__Result` and `RETURN __Result`. No functions after `RETURN`.
- Keep the VARs flat: one list of `VAR`s at the top of the expression, then `RETURN __Result`.
  No `VAR … RETURN` block inside a function argument. See
  [Keep the VARs flat](#keep-the-vars-flat).
- Use `&&` / `||` / `<>` inside `FILTER`, not nested `AND()` / `OR()`.
- Write a column as `Table[Column]`, always with its table, and quote the table name only where
  DAX requires it (a space, a special character, a leading digit or a reserved word):
  `Sales[Amount]`, `'Sales Order'[Amount]`. Write a measure as `[Measure]`, never with its table
  in front. Examples in other skills that quote every table name do not override this.

## Filter the dimension, not the fact

Step 2 filters a dimension column wherever one carries the attribute: `Store[Region]`, not
`Sales[Region]`, and not `FILTER ( Sales, RELATED ( Store[Region] ) … )`. Group by dimension columns
too, the calendar's own period columns included, rather than by the fact's date or key. The
dimension filter runs over the dimension's few rows and reaches the fact through the relationship,
and it is the same column the slicers use.

Before filtering a fact column, find what it relates to:
`grep -n -A1 "fromColumn: Sales\." definition/relationships.tmdl`. One of three things holds:

| What you find | What to write |
| --- | --- |
| A relationship from the column | Filter its `toColumn`, assuming referential integrity. Switching an existing measure: decide how it meets slicers on that column (`KEEPFILTERS` or not) |
| No relationship, and the column is dimension-like (text or a code people slice by, repeated across many rows) | Propose a dimension and wait for the user. Meanwhile, a column filter on the fact with a comment naming the proposed dimension |
| A numeric or degenerate condition, a dimension over about 131K rows, or an inactive relationship | The fact column, as the reference's exceptions say |

**Assume referential integrity.** Write measures with no fallback for keys a dimension might lack.
A missing key is proven by the reference's test query, never assumed, and a proven gap is reported
so it is fixed upstream.

**Always discuss it.** Every reply that writes or reviews a measure filtering or grouping by an
attribute says which column carries the filter and why: the dimension it moved to and how it meets
slicers on that column, the dimension you propose (name, columns, where it is built, the
relationship), or the exception that keeps it on the fact. A proposed dimension gets built only
after the user agrees, and through `semantic-models:model-change`, since it changes the model.

The patterns, the referential-integrity test, the slicer check, what a proposal contains and the
review checklist are in
[`references/filter-dimensions-not-facts.md`](references/filter-dimensions-not-facts.md).

## Step 3 is not always an X-aggregator

The **table VAR is the part that pays for itself**, not the X-function that follows it. Step 3 is
a *semantic* choice: `SUMX( __Table, <expr> )` **iterates**, `CALCULATE( <expr>, __Table )`
**filters**. They are not two spellings of one thing, and swapping one for the other can silently
change the number. Pick by what is being aggregated:

| `__Table` / expression shape                                                    | Final step     |
| --------------------------------------------------------------------------------- | ---------------- |
| `__Table` carries computed columns you must aggregate (`ADDCOLUMNS` + `"@…"`)  | X-aggregator   |
| The row expression needs row context (`Sales[Qty] * Sales[Price]`, a per-row `IF`) | X-aggregator   |
| **The row expression is an existing measure**                                 | **`CALCULATE`** |
| **The aggregation is non-additive** (`DISTINCTCOUNT`, `MIN`/`MAX`, any ratio), and no filter argument constrains the column being aggregated | **`CALCULATE`** |
| It needs a time shift or another filter modifier                                  | `CALCULATE`    |
| You only want the row count                                                       | `COUNTROWS`    |

**`SUMX( __Table, [Some Measure] )` is the common bug this fixes.** It forces context transition
per row and then *adds* the results — which for a ratio is nonsense (30.9% + 29.1% = 59.9% is not
a margin), and for a `DISTINCTCOUNT` double-counts whatever two rows share.
`CALCULATE( [Some Measure], __Table )` evaluates it once over the pooled set, which is usually
what was meant — and usually faster, because the filter and the scan fuse into one storage-engine
query instead of materialising `__Table` for the formula engine to walk.

Computed columns and row-level expressions cannot move into `CALCULATE`, so there the X-aggregator
stays: [what cannot move, and the errors it raises](references/calculate-and-performance.md#what-cannot-move-into-calculate).

**The guard.** A table filter argument *replaces* the filter context on every column it carries
lineage to. When step 3 is `CALCULATE`, decide `KEEPFILTERS` explicitly and say why in the
comment — otherwise a `__Table` built over `ALL( … )` quietly ignores the slicers on the page. An
X-aggregator over that same table overrides identically, so the culprit is the `ALL`, not the
terminator; `KEEPFILTERS` is the repair, and it exists only inside `CALCULATE`. The same
replacement bites with no `ALL` in sight when a predicate constrains the column being aggregated, and
there the repair is to build the row set and count it:
[When CALCULATE is the wrong call](references/calculate-and-performance.md#when-calculate-is-the-wrong-call-filtering-the-column-you-are-aggregating).

## Keep the VARs flat

A measure is one flat list of steps, and the last one is the result:

```DAX
Measure =
    VAR __Step1  = …
    VAR __Step2  = …
    VAR __Result = …
    RETURN
        __Result
```

Do not open a second `VAR … RETURN` block inside a function argument: not inside `CALCULATE ( … )`,
not inside a user-defined function's `EXPR` argument, not inside an iterator's row expression. Only
a top-level VAR can be [swapped into the RETURN](#the-killer-feature-debug-by-swapping-the-return),
so a nested block hides its steps. A table VAR nested inside `CALCULATE` cannot be returned at all,
because `CALCULATE` must return a single value. A nested block also reads as one measure inside
another.

The three nested shapes that turn up (a block passed to a UDF wrapper that sets the filter context,
a block inside an iterator's row expression, a VAR that captures a row value only to put a filter
back), their flat forms, the one nested VAR that stays, and the query that proves a flattened
measure returns the same numbers are in [`references/flat-vars.md`](references/flat-vars.md).

## Standing exception: time intelligence uses CALCULATE + DATEADD

The table-first style is the default **except when time intelligence is involved**. For
prior-year / period-shift / to-date logic, do not reach for the offset technique in
`references/dates-and-time.md` first — write the standard time-intelligence form with
`CALCULATE` over a **properly formed date table** (contiguous daily dates, marked as a date
table — the `semantic-models:date-table` DimDate qualifies):

```DAX
Sales LY =
    CALCULATE ( [Total Sales], DATEADD ( DimDate[Date], -1, YEAR ) )
```

- Prefer `DATEADD` over `SAMEPERIODLASTYEAR` — it takes an explicit interval, so the same
  form covers year, quarter, month and day shifts.
- `DATESYTD` / `DATESMTD` inside CALCULATE are likewise fine for to-date measures.
- Only the time shift itself uses CALCULATE — the base measure and everything around it
  stays in the table-first style.
- The offset-column technique is the fallback for models with no proper date table or
  non-standard calendars, not the default.

## House style: short lines, comments, body on the second line

Author every measure so it reads top-to-bottom like prose. Three rules:

1. **Start the expression on the second line — always, one-liners included.** In **TMDL** this
   requires a **blank line immediately after `=`**, then the body indented two levels deeper than the
   `measure` declaration. The blank line makes the stored expression begin with a newline, which is
   what makes Power BI's measure editor render the body on line 2. **Without it the editor glues the
   first body line onto the `Name =` line** — e.g. `Card Spend = VAR __Rows =` on one line — even when
   the first body line is a `VAR`, not a `//` comment. Applies to one-liners too.

   ```tmdl
   measure 'Net Cashflow' =

   		[Total Income] - [Total Spend]
   ```

2. **One thing per line (short lines).** Each `VAR`, each function, and each argument on its
   own line — break `FILTER`, `DIVIDE`, `GROUPBY`, etc. across lines instead of packing a call
   onto one line. Short lines diff cleanly and read like discrete steps.
3. **Comment every step, after the measure name rather than above it.** The explanatory comment
   belongs on the line *after* `MeasureName =`, inside the expression, not stranded above the
   declaration. Precede each `VAR` / step with a `//` line saying what it does. These `//` comments
   live inside the expression, so the engine keeps them as DAX comments. That is separate from the
   TMDL `///` line above the measure, which sets the `Description` property. Use both, and keep the
   step-by-step reasoning in the `//` comments where it sits beside the code it explains.
4. **Never leave a measure in an error state.** A measure that does not evaluate is worse than no
   measure: it breaks every visual that touches it, and it breaks the model refresh. If a rewrite is
   half done, or a field it depends on does not exist yet, either finish it or revert it before
   handing the file back. Prove it evaluates before you call the work done. `pbip:tmdl`
   `references/authoring-gotchas.md` covers the parse-level traps; this is about the semantic level,
   where the file parses and the measure still returns an error.


Do not blank-line inside the body. A blank line after `=` is verified safe, and a Desktop save may
re-inline the one-liners; both, and a worked measure in DAX and in TMDL, are in
[`references/house-style.md`](references/house-style.md).

## Number formatting: dynamic format strings + UDFs

**Do not `FORMAT()` a measure to make it look right.** `FORMAT` returns text, so charts, sorting
and aggregation break. Give the measure a dynamic format string (`formatStringDefinition`, over
`SELECTEDMEASURE()`) and keep its logic in one user-defined function per formatting convention
(scaled, currency, percent, duration); check [daxlib.org](https://daxlib.org) first.

- **A measure has `formatString` OR `formatStringDefinition`, never both.** Desktop refuses to open
  a project with both: delete the `formatString:` line.
- **Before one UDF calls another, read the load traps.** After any `functions.tmdl` change, run
  `EVALUATE INFO.USERDEFINEDFUNCTIONS()` and read `ErrorMessage`.

The TMDL syntax, the `Fmt.Scaled` UDF, those traps and the display-unit gotchas are in
[`references/number-formatting.md`](references/number-formatting.md).

## The killer feature: debug by swapping the RETURN

Because every step is a `VAR`, you inspect any intermediate by temporarily returning it:

```DAX
    RETURN COUNTROWS( __Table )   -- how many rows survived the filter?
    RETURN TOCSV( __Table )       -- dump the table's rows as text into a card/table visual
```

In DAX query view, paste the body after `EVALUATE` and return a table VAR to get it as a result
grid; wrap it in `CALCULATETABLE` with a cell's filters to see that cell
([`references/method.md`](references/method.md), section 6). Both swaps reach only top-level
VARs, which is why the VARs stay [flat](#keep-the-vars-flat).

`EVALUATEANDLOG( __Table )` (DAX query view / SQL Profiler) does the same at scale. A
CALCULATE expression cannot be peeled apart this way: splitting nested CALCULATEs changes
the result, so there is no way to watch it work. That is the practical reason this style is
the default.

## Tables come from Power Query, not DAX

This skill writes measures, not tables. Build every table in the source (a view, a lakehouse
table) or in Power Query. A DAX calculated table is the last resort: write one only when no
upstream layer can produce the table, and say why in a comment on its partition.

The reasons (refresh cost, dependencies, storage modes), the Power Query form of the three
calculated tables that turn up, the TMDL conversion with its `.pbi/cache.abf` step, and the two
cases where a calculated table is right (field parameters, a table that needs the model's own
DAX logic) are in [`references/tables-from-power-query.md`](references/tables-from-power-query.md).

## When to use this skill vs. the performance skill

A measure that is **measurably slow**, server timings, query-plan tuning and model-level
performance go to `semantic-models:dax-optimisation` (or `semantic-model` for the model). The
two do not conflict: **author table-first**, and reach for the optimisation skill's
CALCULATE-based patterns (DAX001, DAX005, DAX008, DAX010, …) only when profiling proves a
specific measure too slow and a rewrite helps. The full reconciliation is in
[`references/calculate-and-performance.md`](references/calculate-and-performance.md).

## References (progressive disclosure — read as needed)

- [`references/method.md`](references/method.md): think in DAX, FILTER, X-aggregators,
  variables, the core pattern, debugging, the explicit form vs the CALCULATE form. **Read first.**
- [`references/core-functions.md`](references/core-functions.md): lookups, ALL/ALLSELECTED,
  running totals, previous-row, grouping, IF/SWITCH, ISINSCOPE, set functions, the Measure Totals fix.
- [`references/dates-and-time.md`](references/dates-and-time.md): the fallback to the time
  exception: non-standard calendars, no date table, DimDate offset columns, rolling windows, durations.
- [`references/text-and-numbers.md`](references/text-and-numbers.md): text, dynamic text,
  conditional formatting, safe division, rounding, ranking, weighted average, regression.
- [`references/business-recipes.md`](references/business-recipes.md): the table to build per
  metric (finance, variance, rates, sales, operations, workforce) and the report-support measures.
- [`references/advanced-patterns.md`](references/advanced-patterns.md): disconnected and what-if
  tables, field parameters, selectors, custom hierarchies, streaks, fuzzy matching, geospatial.
- [`references/calculate-and-performance.md`](references/calculate-and-performance.md): what
  CALCULATE is, when it is right or wrong, what cannot move into it, FE/SE, the debugging toolbox.
- [`references/filter-dimensions-not-facts.md`](references/filter-dimensions-not-facts.md): the
  dimension filter, the referential-integrity test, the slicer check, proposing a dimension, the
  exceptions, a review checklist.
- [`references/filter-context-traps.md`](references/filter-context-traps.md): measures right in
  a clean context and wrong in the report's (second calendars, calculation items, tooltips).
- [`references/flat-vars.md`](references/flat-vars.md): the nested `VAR … RETURN` shapes, their
  flat forms, the one nested VAR that stays, and the query that proves a flattened measure.
- [`references/house-style.md`](references/house-style.md): the blank line after `=` in TMDL,
  how a Desktop save re-inlines one-liners, and a worked measure in DAX and TMDL.
- [`references/number-formatting.md`](references/number-formatting.md): dynamic format strings
  in TMDL, the `Fmt.Scaled` UDF, UDF load traps, and the display-unit gotchas.
- [`references/tables-from-power-query.md`](references/tables-from-power-query.md): why tables
  come from the source or Power Query, the M form of each common calculated table, and the
  TMDL conversion.

## Related skills

- `semantic-models:dax-optimisation` — performance optimization of existing DAX (CALCULATE-friendly).
- `semantic-models:semantic-model` — model design, measures, RLS, calculation groups.
- `pbi-desktop:connect-pbid` — run/validate DAX against a local model, EVALUATEANDLOG,
  trace capture.
