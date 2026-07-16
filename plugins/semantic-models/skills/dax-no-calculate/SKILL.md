---
name: dax-no-calculate
version: 26.25
description: Author readable DAX measures in the "No CALCULATE" style from Greg Deckler's book *DAX For Humans* — build a virtual table with VAR + FILTER + X-aggregators and aggregate over it, instead of leaning on CALCULATE and filter-context manipulation. Invoke when asked to "write a measure", "how do I write DAX for…", "rewrite this DAX without CALCULATE", "make this DAX readable/easier to debug", "No CALCULATE", "DAX For Humans", "the DAX pattern", or for a worked recipe (time intelligence, customer/HR/finance/operations KPIs, geospatial, streaks, fuzzy matching, SVG). For tuning a slow/existing measure or reading server timings, use the `semantic-models:dax` performance skill instead.
---

# No CALCULATE DAX (DAX For Humans style)

A DAX **authoring and learning** skill that captures the method from Greg Deckler's
2025 book *DAX For Humans: The No CALCULATE Guide that Makes DAX Easy*. It is a
deliberately *non-conventional* alternative to the CALCULATE-centric style taught by
most resources (SQLBI, Microsoft docs).

> Source & attribution: techniques here are distilled and paraphrased from *DAX For
> Humans* by Gregory Deckler (ISBN 9798290175508). Code examples are original
> illustrations of the documented technique, not reproductions of the book's worked
> examples. Credit the book when surfacing this approach to the user.
>
> **License notice:** unlike the rest of this repository, this skill and its
> `references/` files are **not** covered by the repo's GPL-3.0 grant. They summarize
> and paraphrase material from a commercial book; all rights in the underlying method
> and text remain with the author and publisher. This skill is included as an
> attributed educational summary for personal use — do not redistribute it as your
> own work, and buy the book for the full treatment.

## The thesis in one line

You can write almost all DAX **without `CALCULATE`** by thinking in *tables, rows, and
columns*: filter a table down with `FILTER`, then aggregate over it with an X-aggregator
(`SUMX`, `MINX`, …), composing the steps with `VAR`s. This is easier to read, far easier
to debug, and — per the book's experiments up to 20M rows — generally performs the same.

## The core pattern — "A DAX Pattern to Solve Most Problems"

```DAX
Measure =
    VAR __Input  = <scalar setup, e.g. MAX( Dim[Key] )>      -- 1. scalar VAR(s)
    VAR __Table  = FILTER( <table>, <conditions using __Input> )  -- 2. build a virtual table
    VAR __Result = SUMX( __Table, <row expression> )         -- 3. X-aggregate over it
    RETURN
        __Result                                             -- always return a __Result VAR
```

Three steps: **(1)** capture scalars you need, **(2)** build a table variable that filters /
groups the rows the calc needs, **(3)** run an X-aggregator over that table. Extend it to
dozens of lines for complex problems — the *shape* stays the same.

Conventions the book uses (follow them for consistency):
- Prefix variables with `__` (double underscore) to avoid reserved words and mirror the
  engine's own generated queries.
- Name the final variable `__Result` and `RETURN __Result` — no functions after `RETURN`.
- Use `&&` / `||` / `<>` inside `FILTER`, not nested `AND()` / `OR()`.

## House style: short lines, comments, body on the second line

Author every measure so it reads top-to-bottom like prose. Three rules:

1. **Start the expression on the second line.** Put nothing after `=`; the body begins on
   the next line. In **TMDL**, leave a **blank line right after `=`** so the stored
   expression itself begins with a newline. Without it, Power BI's measure editor glues the
   first line of the body (often a leading `//` comment) onto the `Name =` line.
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

The same measure in a **TMDL** file — note the blank line between `=` and the first `//`
comment, and the body indented two levels deeper than the `measure` declaration:

```tmdl
/// Cancelled-adjusted sales as a share of all sales.
measure 'Net Sales %' =

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
	formatString: 0.0%
```

Single-expression measures get the same treatment — `=`, blank line, comment, then the call:

```tmdl
measure 'Total Orders' =

		// One row per order; count them
		COUNTROWS ( Sales )
	formatString: #,##0
```

## The killer feature: debug by swapping the RETURN

Because every step is a `VAR`, you inspect any intermediate by temporarily returning it:

```DAX
    RETURN COUNTROWS( __Table )   -- how many rows survived the filter?
    RETURN TOCSV( __Table )       -- dump the table's rows as text into a card/table visual
```

`EVALUATEANDLOG( __Table )` (DAX query view / SQL Profiler) does the same at scale. A
CALCULATE expression cannot be peeled apart this way — splitting nested CALCULATEs
changes the result — which is the book's central argument against it.

## When to use this skill vs. the performance skill

| Situation | Use |
|---|---|
| Writing a **new** measure; learning DAX; wanting readable/debuggable code | **this skill** |
| "Rewrite this without CALCULATE", "make this easier to follow" | **this skill** |
| A measure is **measurably slow**; reading FE/SE server timings; query-plan tuning | `semantic-models:dax` |
| Model-level perf (relationships, cardinality, Direct Lake) | `semantic-models:dax` / `semantic-model` |

**Reconciling the CALCULATE tension (important):** this skill's default is *no CALCULATE*;
the `semantic-models:dax` perf skill has CALCULATE/CALCULATETABLE-based optimization
patterns (DAX001, DAX005, DAX008, DAX010, …). These do **not** conflict — they have
different jobs. **Author in No-CALCULATE style first**; reach for the perf skill's
CALCULATE-based patterns only when profiling proves a specific measure is too slow and a
rewrite helps. See [`references/calculate-and-performance.md`](references/calculate-and-performance.md)
for the full reconciliation.

## References (progressive disclosure — read as needed)

- [`references/method.md`](references/method.md) — Think in DAX; FILTER; X-aggregators;
  variables; the core pattern; debugging; No CALCULATE vs CALCULATE. **Read this first.**
- [`references/core-functions.md`](references/core-functions.md) — Lookups, ALL/ALLSELECTED,
  running totals, previous-row, grouping (SUMMARIZE/GROUPBY/SUMMARIZECOLUMNS),
  ADDCOLUMNS, IF/SWITCH, HASONEVALUE/ISINSCOPE, SELECTCOLUMNS, IN, set
  functions, and the **Measure Totals** fix.
- [`references/dates-and-time.md`](references/dates-and-time.md) — Time intelligence
  **without** time-intelligence functions: the **offset** technique, period-to-date / YTD /
  previous-period / rolling, plus time & duration math.
- [`references/text-and-numbers.md`](references/text-and-numbers.md) — Text extraction,
  dynamic text, conditional formatting; safe division, rounding family, ranking, mode,
  weighted average, interpolation, regression, number formatting.
- [`references/business-recipes.md`](references/business-recipes.md) — Worked KPI patterns
  for Customers, HR, Projects, Finance, Operations (the book's domain chapters).
- [`references/advanced-patterns.md`](references/advanced-patterns.md) — Disconnected
  tables, NOT/AND slicers, complex selectors, custom matrix hierarchies, SVG, dynamic
  granularity; geospatial; GAMMA, TRIMMEAN, fuzzy matching, DAX INDEX, streaks,
  multi-column aggregation.
- [`references/calculate-and-performance.md`](references/calculate-and-performance.md) —
  What CALCULATE really is, why it is hard to debug, when it *is* worth using, the FE/SE
  optimization model, using AI to write DAX, and how this skill coexists with the
  `semantic-models:dax` performance skill.

## Related skills

- `semantic-models:dax` — performance optimization of existing DAX (CALCULATE-friendly).
- `semantic-models:semantic-model` — model design, measures, RLS, calculation groups.
- `pbi-desktop:connect-pbid` — run/validate DAX against a local model, EVALUATEANDLOG,
  trace capture.
