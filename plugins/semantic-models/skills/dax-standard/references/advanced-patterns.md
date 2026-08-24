# Advanced & Complex Patterns

Where the method scales past a straight aggregation: relationships DAX forms at query time,
report interactions the model cannot express, and calculations the language has no function
for. The move is always the same one — represent the problem as a table, then aggregate over
it.

## Disconnected tables and DAX-formed relationships

A disconnected table has **no** relationship to the model; you relate it **in DAX** at
calculation time. Model relationships only propagate single-column exact-match filters — DAX
has none of those limits, so a disconnected table plus `FILTER` / `IN` / `CONTAINSROW` gives
you many-to-many, range and conditional joins. The shape: read the selected value(s) from the
disconnected table with `SELECTEDVALUE` / `MAX` / `VALUES`, then filter the fact accordingly.

This is the foundation for most of what follows. It is a feature, not a smell.

- **Parameter / what-if tables** — `GENERATESERIES( min, max, step )` as a table, one column
  surfaced in a slicer, the selection read with `SELECTEDVALUE( Param[Value], <default> )`.
  Always give the default; a measure that breaks when nothing is selected is a bug, not an
  edge case.
- **Selector tables** — a table of labels the user picks from, with a `SWITCH` in the measure
  dispatching on the selection. Use when the *calculation* changes, not just the field.
- **NOT slicer (inverse selection)** — show everything *except* the selection: read the
  selected keys from the disconnected slicer table, then
  `FILTER( ALL( Fact ), NOT Fact[Key] IN __Selected )`.
- **AND slicer** — require rows to match **all** selected tags rather than any: count matched
  tags per row and keep the rows whose match count equals the number of selected tags.
- **Complex selector** — a measure that encodes multi-condition selection logic and returns
  1/0, then filtered to `= 1` in the Filters pane. Pushes selection logic into DAX where it
  can be read.
- **Top N + Other with a user-chosen N** — read N from the parameter table, `TOPN` to that,
  and roll the remainder into a single "Other" row so the total still reconciles.

## Field parameters

A field parameter is a generated table whose rows carry the *reference* to a column or measure,
so the user swaps what a visual displays. Model side: create it as a calculated table with
`NAMEOF()` references and the `ParameterMetadata` extended property — the `semantic-model` and
`tmdl` skills cover the object; don't hand-write the metadata blob.

Two gotchas that cost real time:

- **A measure parameter only dispatches from a measure well** (Values, axis values). Dropped on
  matrix Rows it is just a text column, and the visual fails with "Can't determine relationships
  between the fields".
- **The report side is a separate contract.** In PBIR the role bucket holds the *expanded*
  concrete projections plus a sibling `fieldParameters` array pointing at the parameter's
  display column. See the `pbip:pbir-format` skill before hand-editing a visual that uses one.

## Report-interaction patterns

- **Custom matrix hierarchy** — arbitrary, non-natural drilldown levels driven by a
  disconnected level table plus `SWITCH( TRUE(), ISINSCOPE( … ) … )`. Test `ISINSCOPE` from the
  *bottom* of the hierarchy upward: a higher level is in scope at lower levels too.
- **Dynamic granularity** — switch the axis grain (day / week / month) from the selected date
  range or an explicit selector, so a two-year view doesn't render 730 points.
- **SVG measures** — return a `data:image/svg+xml` string from a measure whose column is
  categorised as *Image URL*, to draw sparklines, bars and indicators inside a table or card.
  `custom-visuals:svg-visuals` is the toolkit; check its UDF libraries before hand-rolling.
- **Calculation groups** — when one applies, its format-string expression overrides the
  measure's own, and every measure in the model becomes *variant*, which can break a dynamic
  format string that references a measure by name (use `SELECTEDMEASURE()`). The model-side
  mechanics live in the `semantic-model` skill; the format-string consequence is in
  [`../SKILL.md`](../SKILL.md).

## Calculations DAX has no function for

The playbook: build a table that represents the problem, then aggregate over it.

- **Row index / position within a partition** — count how many rows sort before the current one
  (`COUNTROWS( FILTER( __Partition, sortkey < __Me ) )` plus a tiebreaker). The foundation for
  "nth row", dense ranking, and ordered-window calculations.
- **Streaks and runs** — consecutive days of sales, win streaks, days since last event: find the
  previous occurrence, detect the break with date arithmetic, then size each run.
- **Moving average / trend / smoothing** — a window `FILTER` over `ALL( DimDate )` and
  `AVERAGEX` for the moving average; least-squares slope and intercept built from `SUMX`es for
  a linear trend; locally-weighted smoothing (LOESS) is the same idea with a distance-weighted
  window per point. Statistics reduce to a handful of `SUMX`es —
  see [`text-and-numbers.md`](text-and-numbers.md).
- **Multi-column aggregation** — aggregate over combinations by `SUMMARIZE`ing on several
  columns (or `CROSSJOIN`ing distinct sets) and iterating the result.
- **Fuzzy / approximate matching** — score candidate matches with text functions over a
  generated character-position table and rank by score. Real need in client data; expensive, so
  do it once upstream (Power Query or the source) if the match set is static.
- **Geospatial distance** — great-circle distance between two lat/long points from
  `SIN`/`COS`/`ASIN`/`SQRT` and the Earth's radius, with both points captured as scalar VARs;
  "nearest other point" is `MINX` of that distance over a `FILTER` that excludes self. DAX has
  no two-argument arctangent — build `ATAN2` from `ATAN` plus quadrant logic if a bearing is
  needed.

## Common threads

1. **Disconnected tables unlock interactions** that model relationships cannot express, with
   DAX as the join logic.
2. **Missing function? Build a table.** Index tables, period tables, coefficient tables —
   represent the problem as rows and aggregate.
3. **Self-joins over `ALL`/duplicated tables** power nearest-point, streaks, ranking,
   co-occurrence and previous-occurrence alike.
4. Row-by-row work — DAX-formed relationships, per-point geo maths, fuzzy matching — can be
   slow. Often it is the only way to express the problem, so accept it, and if it matters,
   profile with `semantic-models:dax-optimisation` rather than guessing.
