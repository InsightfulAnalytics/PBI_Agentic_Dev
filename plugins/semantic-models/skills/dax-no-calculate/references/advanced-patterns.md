# Advanced & Complex Patterns (No CALCULATE)

From *DAX For Humans* Ch. 12 (Distance and Space), Ch. 13 (Advanced Scenarios), and Ch. 14
(Complex Patterns). These show the method scaling to problems that "shouldn't" be solvable
in DAX — geospatial math, report-interaction tricks, and missing-function reconstructions.

## Ch. 12 — Distance and Space (geospatial math in DAX)

All built from `SUMX`/scalar VARs over coordinate columns — no special functions:

- **ATAN2** — DAX lacks a 2-arg arctangent; build it from `ATAN` + quadrant logic
  (`SWITCH(TRUE(), …)` on the signs of x/y).
- **Polar ↔ Cartesian** — convert between `(r, θ)` and `(x, y)` with trig (remember radians).
- **Distance (Haversine / great-circle)** — compute distance between lat/long pairs with
  `SIN`/`COS`/`ASIN`/`SQRT` and Earth's radius; capture the two points as scalar VARs.
- **Bearing** — initial compass bearing between two points via the ATAN2 you built.
- **Eastings & Northings** — project lat/long to a planar grid.
- **NEAR** — for each point, find the closest other point: `MINX` of distance over a
  `FILTER` excluding self (a self-join over a disconnected/duplicated table).
- **Transitive closure** — iteratively expand reachable relationships (graph reachability)
  by repeatedly unioning newly reachable pairs.
- **Box sizes** — bin/quantize coordinates into grid boxes.

## Ch. 13 — Advanced Scenarios (bending Power BI's behavior)

**Disconnected tables + DAX-formed relationships.** A disconnected table has *no*
relationship to the model; you relate it **in DAX** at calc time. Relationships in Power BI
only propagate single-column exact-match filters — DAX has none of those limits, so
disconnected tables + `FILTER`/`IN`/`CONTAINSROW` let you build many-to-many, range, and
conditional "joins." Pattern: read the selected value(s) from the disconnected table with
`MAX`/`VALUES`, then `FILTER`/`SUMX` the fact table accordingly.

- **NOT slicer (inverse selection)** — show everything *except* the slicer selection: read
  selected keys from a disconnected slicer table, then `FILTER( ALL(fact), NOT key IN sel )`.
- **Complex selector** — a measure encoding multi-condition selection logic, filtered to
  `= 1` in the Filters pane (see core-functions).
- **AND slicer** — require rows to match **all** selected tags (not the default OR): count
  matched tags per row and keep rows whose match count equals the number of selected tags
  (uses `CALCULATETABLE` in the book, but expressible by intersecting per-tag key sets).
- **Custom matrix hierarchy** — drive arbitrary, non-natural drilldown levels from a
  disconnected level table + `SWITCH(TRUE(), ISINSCOPE(...) …)`.
- **Scalable Vector Graphics (SVG)** — return an SVG `data:image/svg+xml` string from a
  measure (column set to *Image URL* data category) to draw sparklines, bars, KPI
  indicators, etc. entirely in DAX. (See the `reports:svg-visuals` skill for a deep toolkit.)
- **Dynamic granularity scale** — switch the axis grain (day/week/month) based on the
  selected range using a disconnected scale table.

## Ch. 14 — Complex Patterns (reconstructing the impossible)

- **GAMMA** — DAX omits the gamma function (extends factorials to non-integers). Implement
  it with the **Lanczos approximation**: a fixed coefficient table + a `SUMX` over it. True
  recursion isn't possible in DAX, so approximate numerically. (Same playbook for other
  missing special functions.)
- **TRIMMEAN** — Excel's trimmed mean: rank the values, `FILTER` out the top/bottom
  fraction, `AVERAGEX` the middle.
- **Fuzzy matching** — approximate string matching (e.g. Levenshtein-style distance or
  token overlap) built from text functions + a generated character/position table; rank
  candidate matches by score.
- **DAX INDEX** — long considered impossible: produce a stable row index/position within a
  partition by counting how many rows sort before the current one
  (`COUNTROWS(FILTER(partition, sortkey < me))` + tiebreakers). Foundation for
  "nth row," dense ranking, and ordered-window calcs.
- **Streaks** — consecutive runs (e.g. consecutive days of sales, win streaks): use the
  previous-occurrence pattern + offset/gap arithmetic to detect breaks, then size each run.
- **Multi-column aggregations** — aggregate over combinations of columns by `SUMMARIZE`ing
  on multiple columns (or `CROSSJOIN`ing distinct sets) and iterating the result.

## Common threads

1. **Disconnected tables are a feature, not a smell** — they unlock interactions and joins
   that model relationships can't express, with DAX as the join logic.
2. **Missing function? Build a table.** Coefficient tables (Lanczos), index tables (split,
   DAX INDEX), period tables (billing, compounding) — represent the problem as rows and
   aggregate.
3. **Self-joins via duplicated/`ALL` tables** power NEAR, streaks, ranking, market-basket,
   and previous-occurrence.
4. Performance can suffer with DAX-formed relationships and row-by-row geo math — but these
   are often the *only* way to solve the problem, so accept the trade-off and, if it
   matters, profile with the `semantic-models:dax` skill.
