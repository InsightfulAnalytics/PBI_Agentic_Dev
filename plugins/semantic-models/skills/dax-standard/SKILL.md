---
name: dax-standard
version: 26.25
description: The house style for authoring DAX measures — build the rows the calculation needs into a table variable, then aggregate over it with an X-function, composing the steps with VARs so every measure reads top-to-bottom and can be debugged step by step. Covers measure formatting (dynamic format strings + user-defined functions), the time-intelligence exception, and worked recipes. Invoke when asked to "write a measure", "how do I write DAX for…", "rewrite this measure", "make this DAX readable/easier to debug", "the DAX pattern", "format a measure", "dynamic format string", "number formatting", or for a recipe (time intelligence, customer/HR/finance/operations KPIs, geospatial, streaks, fuzzy matching, SVG). For tuning a measure that is measurably slow, or reading server timings, use `semantic-models:dax-optimisation` instead.
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
table variable holding the rows the calculation runs over, **(3)** reduce it — usually with an
X-aggregator, sometimes with `CALCULATE` (see
[Step 3 is not always an X-aggregator](#step-3-is-not-always-an-x-aggregator)). Complex measures
grow to dozens of lines — the *shape* stays the same.

Naming conventions (non-negotiable, they make measures greppable and diffable):

- Prefix variables with `__` (double underscore) — avoids reserved words and mirrors the
  variable names the engine generates in its own queries.
- Name the final variable `__Result` and `RETURN __Result`. No functions after `RETURN`.
- Use `&&` / `||` / `<>` inside `FILTER`, not nested `AND()` / `OR()`.

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
| **The aggregation is non-additive** — `DISTINCTCOUNT`, `MIN`/`MAX`, any ratio | **`CALCULATE`** |
| It needs a time shift or another filter modifier                                  | `CALCULATE`    |
| You only want the row count                                                       | `COUNTROWS`    |

**`SUMX( __Table, [Some Measure] )` is the common bug this fixes.** It forces context transition
per row and then *adds* the results — which for a ratio is nonsense (30.9% + 29.1% = 59.9% is not
a margin), and for a `DISTINCTCOUNT` double-counts whatever two rows share.
`CALCULATE( [Some Measure], __Table )` evaluates it once over the pooled set, which is usually
what was meant — and usually faster, because the filter and the scan fuse into one storage-engine
query instead of materialising `__Table` for the formula engine to walk.

Two things cannot move into `CALCULATE`, so there the X-aggregator stays:

- **Computed columns.** Extension columns carry no data lineage, so they filter nothing *and*
  cannot be referenced: `CALCULATE( [@Revenue], __Table )` fails with *"The value for '@Revenue'
  cannot be determined."* Materialise-then-aggregate — weighted averages, per-row currency
  conversion, per-customer thresholds — is X-function territory.
- **Row-level expressions.** `CALCULATE`'s first argument has no row context, so
  `CALCULATE( Sales[Qty] * Sales[Price], __Table )` fails with *"A single value for column 'Qty'
  … cannot be determined."* The working rewrite is `CALCULATE( SUMX( Sales, … ), __Table )` — the
  `SUMX` did not disappear, it moved inside and now iterates `Sales`.

**The guard.** A table filter argument *replaces* the filter context on every column it carries
lineage to. When step 3 is `CALCULATE`, decide `KEEPFILTERS` explicitly and say why in the
comment — otherwise a `__Table` built over `ALL( … )` quietly ignores the slicers on the page. An
X-aggregator over that same table overrides identically, so the culprit is the `ALL`, not the
terminator; `KEEPFILTERS` is the repair, and it exists only inside `CALCULATE`.

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

   **Verified safe (2026-07-22):** a blank line *immediately after* `=`, before the body, does NOT
   trigger the `InvalidLineType: Empty` that `~/.claude/rules/tmdl-pbir-authoring.md` warns about —
   Power BI Desktop opens it cleanly. That warning is about a blank line *breaking the middle* of a
   multi-line expression (between two body lines), which is a different thing. Do not blank-line
   inside the body; do blank-line right after `=`.

   **Durability caveat:** Power BI Desktop's own serializer writes *single-line* expressions inline
   (`measure X = expr`) when it re-saves a model. So one-liners you format as body-on-line-2 can
   revert to inline after a Desktop save. Multi-line measures keep the blank-line/body-on-line-2 form
   (it is Desktop's own canonical form for them). Author on disk in the line-2 form regardless; just
   know a Desktop round-trip may re-inline the trivial one-liners.
2. **One thing per line (short lines).** Each `VAR`, each function, and each argument on its
   own line — break `FILTER`, `DIVIDE`, `GROUPBY`, etc. across lines instead of packing a call
   onto one line. Short lines diff cleanly and read like discrete steps.
3. **Comment every step.** Precede each `VAR` / step with a `//` line saying what it does.
   These `//` comments live *inside* the expression, so the engine keeps them as DAX comments.
   (That is separate from the TMDL `///` line **above** the measure, which sets the measure's
   `Description` property — use both.)

Worked example in this house style:

```DAX
Net Sales % =
    // Keep only the orders that were not cancelled ...
    VAR __Table =
        FILTER (
            Sales,
            Sales[Status] <> "Cancelled"
        )
    // ... and express their value as a share of all sales
    VAR __Result =
        DIVIDE (
            SUMX ( __Table, Sales[Amount] ),
            [Total Sales]
        )
    RETURN
        __Result
```

The same measure in a **TMDL** file — note the **blank line right after `=`**, and the body indented
two levels deeper than the `measure` declaration. The blank line is what makes the editor show the
body on line 2:

```tmdl
/// Cancelled-adjusted sales as a share of all sales.
measure 'Net Sales %' =

		// keep only the orders that were not cancelled ...
		VAR __Table =
		    FILTER (
		        Sales,
		        Sales[Status] <> "Cancelled"
		    )
		// ... and express their value as a share of all sales
		VAR __Result =
		    DIVIDE (
		        SUMX ( __Table, Sales[Amount] ),
		        [Total Sales]
		    )
		RETURN
		    __Result
	formatString: 0.0%
```

Single-expression measures get the same treatment — `=`, a blank line, then the call:

```tmdl
/// One row per order; count them.
measure 'Total Orders' =

		COUNTROWS ( Sales )
	formatString: #,##0
```

## Number formatting: dynamic format strings + UDFs

**Do not `FORMAT()` a measure to make it look right.** `FORMAT` returns *text*, so the
measure stops being a number — charts, sorting and aggregation all break. Format the
**number** instead, with a **dynamic format string** on the measure, and put the repeated
formatting logic in a **user-defined function** so it is written once.

### Rule: a measure has `formatString` OR `formatStringDefinition` — never both

They are mutually exclusive. A measure carrying both makes Power BI Desktop refuse to open
the whole project ("not supported scenario"). **To use a dynamic format string the static
format string must be absent** — delete the `formatString:` line.

In TMDL, `formatStringDefinition` is a **child object, not a property**: it goes *after* the
scalar properties, separated by a blank line, expression inline on the same line.

```tmdl
/// Revenue, auto-scaled to K / M / B for the value on screen.
measure 'Total Revenue' =

		SUM ( Sales[Amount] )
	displayFolder: Sales
	lineageTag: <guid>

	formatStringDefinition = Fmt.Scaled ( SELECTEDMEASURE (), 1 )
```

`SELECTEDMEASURE()` is the value being rendered; referencing the measure by name
(`[Total Revenue]`) also works, but breaks once a calculation group is in the model (every
measure becomes *variant*). Prefer `SELECTEDMEASURE()`.

### The UDF: write the formatting convention once

[DAX user-defined functions](https://www.sqlbi.com/articles/introducing-user-defined-functions-in-dax/)
(Power BI Desktop September 2025+, compatibility level 1702+) hold the scaling/currency rules
in one place instead of a copy-pasted format expression per measure — this is what Microsoft's
own dynamic-format-string docs recommend. Syntax is `name = ( params ) => body`; each
parameter is typed (`NUMERIC`, `INT64`, `STRING`, `TABLE`, …) and takes a passing mode:
`VAL` (evaluated once, in the caller's context) or `EXPR` (lazy, re-evaluated inside the
body — needed for measure references and anything context-sensitive).

Functions live in `functions.tmdl` in the model definition:

```tmdl
/// Scale-aware format string: K / M / B, with `decimals` decimal places.
function 'Fmt.Scaled' =
		(
			value: NUMERIC VAL,
			decimals: INT64 VAL
		) =>

		// The unit comes from the magnitude of the value being displayed.
		VAR __Abs = ABS ( value )
		// "0" repeated = the decimal placeholders.
		VAR __Dp = REPT ( "0", decimals )
		VAR __Result =
			SWITCH (
				TRUE (),
				__Abs >= 1E9, "#,0." & __Dp & ",,,""B""",
				__Abs >= 1E6, "#,0." & __Dp & ",,""M""",
				__Abs >= 1E3, "#,0." & __Dp & ",""K""",
				"#,0." & __Dp
			)
		RETURN
			__Result
```

Every measure that needs it then gets a one-line `formatStringDefinition`. One function per
formatting *convention* (scaled, currency, percent, duration) — not one per measure. Check
[daxlib.org](https://daxlib.org) before writing one; installing packages is covered by
`pbi-desktop:connect-pbid` (`references/daxlib.md`).

### Gotchas

- The expression must return **text**, and it is evaluated per cell in that cell's filter
  context — which is what lets it react to a currency slicer or to the magnitude of the value.
- **Visual display units override it.** If a scaled format "does nothing", set the visual's
  *Display units* from **Auto** to **None** (or turn them off report-wide in the theme).
- A calculation group's format-string expression wins over the measure's own.
- Dynamic format strings only work on **model** measures — not report-level measures in a
  live-connect report.

## The killer feature: debug by swapping the RETURN

Because every step is a `VAR`, you inspect any intermediate by temporarily returning it:

```DAX
    RETURN COUNTROWS( __Table )   -- how many rows survived the filter?
    RETURN TOCSV( __Table )       -- dump the table's rows as text into a card/table visual
```

`EVALUATEANDLOG( __Table )` (DAX query view / SQL Profiler) does the same at scale. A
CALCULATE expression cannot be peeled apart this way: splitting nested CALCULATEs changes
the result, so there is no way to watch it work. That is the practical reason this style is
the default.

## When to use this skill vs. the performance skill

| Situation                                                                              | Use                                                       |
| -------------------------------------------------------------------------------------- | --------------------------------------------------------- |
| Writing a**new** measure; learning DAX; wanting readable/debuggable code         | **this skill**                                      |
| "Rewrite this measure", "make this easier to follow"                                   | **this skill**                                      |
| A measure is**measurably slow**; reading FE/SE server timings; query-plan tuning | `semantic-models:dax-optimisation`                      |
| Model-level perf (relationships, cardinality, Direct Lake)                             | `semantic-models:dax-optimisation` / `semantic-model` |

**Reconciling the CALCULATE tension (important):** this skill defaults to explicit
`FILTER` + X-aggregators; the `semantic-models:dax-optimisation` skill has
CALCULATE/CALCULATETABLE-based optimization patterns (DAX001, DAX005, DAX008, DAX010, …).
These do **not** conflict — they have different jobs. **Author table-first**; reach for the
optimisation skill's CALCULATE-based patterns only when profiling proves a specific measure
is too slow and a rewrite helps. See
[`references/calculate-and-performance.md`](references/calculate-and-performance.md) for the
full reconciliation.

## References (progressive disclosure — read as needed)

- [`references/method.md`](references/method.md) — Think in DAX; FILTER; X-aggregators;
  variables; the core pattern; debugging; the explicit form vs the CALCULATE form.
  **Read this first.**
- [`references/core-functions.md`](references/core-functions.md) — Lookups, ALL/ALLSELECTED,
  running totals, previous-row, grouping (SUMMARIZE/GROUPBY/SUMMARIZECOLUMNS),
  ADDCOLUMNS, IF/SWITCH, HASONEVALUE/ISINSCOPE, SELECTCOLUMNS, IN, set
  functions, and the **Measure Totals** fix.
- [`references/dates-and-time.md`](references/dates-and-time.md) — The **fallback** for what
  the standing exception above does not cover: non-standard calendars, boundaries the
  built-ins will not express, models with no date table. DimDate's **offset columns**,
  period-to-date, rolling windows, and duration maths.
- [`references/text-and-numbers.md`](references/text-and-numbers.md) — Text extraction,
  dynamic text, conditional formatting; safe division, rounding family, ranking, mode,
  weighted average, interpolation, regression, number formatting.
- [`references/business-recipes.md`](references/business-recipes.md) — Which table to build
  for each metric: finance and P&L, budget/target variance, rates and shares, sales and
  customers, delivery and operations, workforce, plus the **report-support measures**
  (titles, colours, labels, indicators, SVG) that outnumber all of them.
- [`references/advanced-patterns.md`](references/advanced-patterns.md) — Disconnected and
  what-if tables, field parameters, NOT/AND slicers, complex selectors, custom matrix
  hierarchies, dynamic granularity, SVG; row index, streaks, moving averages and trend,
  fuzzy matching, geospatial distance.
- [`references/calculate-and-performance.md`](references/calculate-and-performance.md) —
  What CALCULATE really is, why it is hard to debug, when it *is* worth writing, the FE/SE
  optimization model, the debugging toolbox, and how this skill coexists with the
  `semantic-models:dax-optimisation` performance skill.

## Related skills

- `semantic-models:dax-optimisation` — performance optimization of existing DAX (CALCULATE-friendly).
- `semantic-models:semantic-model` — model design, measures, RLS, calculation groups.
- `pbi-desktop:connect-pbid` — run/validate DAX against a local model, EVALUATEANDLOG,
  trace capture.
