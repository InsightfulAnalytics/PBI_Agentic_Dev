# Business KPI Recipes

A map from a business metric to **the table you have to build to compute it**. Every entry is
the same core pattern — scalar VARs, then a table VAR via `FILTER` / `SUMMARIZE`, then an
X-aggregate — so the value here is knowing *which rows the metric needs*, not the column names.
Adapt names to the model in front of you.

The list is scoped to the metrics that actually get built: finance and P&L, budget and target
variance, sales and customers, delivery and operations, a little workforce, and the
report-support measures that outnumber all of them combined.

## The four shapes everything reduces to

- **Cohort / set membership** — build a table of distinct keys for period A and another for
  period B, then `EXCEPT` / `INTERSECT` / `IN` for new, lost, returning, retained.
- **As-of / point-in-time counts** — `FILTER` the event table on
  `StartDate <= asOf && ( EndDate > asOf || ISBLANK( EndDate ) )`, then `COUNTROWS`.
- **Event-relative windows** — capture the event date as a scalar VAR, then filter facts to a
  window around it.
- **Per-entity, then aggregate** — `SUMMARIZE` to the entity grain, add per-entity columns with
  `ADDCOLUMNS`, then `AVERAGEX` / `SUMX`. This is also the fix for measures that don't total.

## Finance and P&L

| KPI | Shape |
|---|---|
| **Revenue / cost / spend** | Straight `SUMX` over the fact, or over a `FILTER` when a status or category qualifies it (spend overdue, spend on hold). |
| **Gross margin, margin %** | `revenue − cost`, then `DIVIDE( margin, revenue )`. Guard the divide; never leave it bare. |
| **Actual vs Budget / Target / Forecast** | Align both to a common grain with `SUMMARIZECOLUMNS`, add the variance column with `ADDCOLUMNS`, then `SUMX`. Variance in currency and variance in % are two measures, not one. |
| **YTD / MTD / QTD, YoY, MoM, PYTD** | Time intelligence — use the standing exception (`CALCULATE` + `DATEADD` / `DATESYTD`), or DimDate's offset columns for non-standard calendars. See [`dates-and-time.md`](dates-and-time.md). |
| **Running / cumulative total** | `FILTER( ALL( DimDate ), DimDate[Date] <= MAX( DimDate[Date] ) )` then `SUMX`. `ALLSELECTED` instead of `ALL` to respect slicers. |
| **Rolling N months** | Filter the offset column to a range: `MonthOffset > -12 && MonthOffset <= 0`. |
| **Reverse YTD (remaining in year)** | Full-year total minus YTD, both from offset filters. |
| **Spend / revenue concentration** | Top-N entity spend ÷ total spend. Build the ranked table with `SUMMARIZECOLUMNS` + `TOPN`, sum it, divide by the *unrestricted* total. |
| **Single-source / preferred-supplier share** | `SUMX` over a `FILTER` on the flag, divided by the total. The flag belongs in the model, not in the measure. |
| **Currency conversion** | Join facts to a rate table on date + currency *inside* the iterator and convert per row. Never convert an already-aggregated total. |
| **Revenue recognition / periodic billing** | Expand each contract into its billing periods as a generated table, then sum the amount recognised in the period. |

## Rates, shares and ratios

The single largest category of measure in a real model. All of them are two moves: a filtered
numerator, and a deliberate choice of denominator.

- **Safe division** — always `DIVIDE( num, den, BLANK() )`. A blank reads as "no data", a zero
  reads as "measured zero". Do not conflate them.
- **Share of total** — the denominator decides the meaning: `ALL` for share of everything,
  `ALLSELECTED` for share of what the user selected, `ALLEXCEPT` for share within a group.
  Getting this wrong is the most common silently-wrong measure there is.
- **Rate over a qualifying subset** — `COUNTROWS( FILTER( T, <qualifies> ) )` ÷ `COUNTROWS( T )`
  (on-time %, unmatched %, single-source %).
- **Weighted average / weighted score** —
  `DIVIDE( SUMX( T, weight * value ), SUMX( T, weight ) )`. Never `AVERAGE` a column that is
  already a per-row percentage.

## Sales and customers

| KPI | Shape |
|---|---|
| **New / lost / returning customers** | Distinct customer sets for current vs prior period (`SUMMARIZE`), then `EXCEPT` / `INTERSECT`; `COUNTROWS` each. |
| **Retention / churn rate** | Active at start ∩ active at end ÷ active at start. Churn is its complement — derive it, don't write it twice. |
| **Customer lifetime value** | Per-customer revenue via `SUMMARIZE` + `ADDCOLUMNS`, then `AVERAGEX` over customers — not a grand total ÷ a count. |
| **Top N + Other** | Rank the entities, keep the top N as themselves, roll the rest into one "Other" row. A user-selected N needs a disconnected parameter table — see [`advanced-patterns.md`](advanced-patterns.md). |
| **Sales after an event** | Event date as a scalar VAR, then `FILTER` sales to `Date >= __Event`, optionally within N days. |
| **Basket / co-occurrence** | Self-join orders on the order key and count item pairs. Expensive — set the grain before iterating. |

## Delivery and operations

| KPI | Shape |
|---|---|
| **On-time delivery %** | `COUNTROWS( FILTER( Orders, Delivered <= Promised ) )` ÷ total orders. Compute the boolean in the model if the model can. |
| **Days late / order cycle time** | `AVERAGEX( Orders, Delivered - Ordered )` — date arithmetic, no function needed. Weight by value if the business means value, not order count. |
| **Open / as-of counts** | The as-of shape: open at the date, not closed by it (open POs, open tickets, WIP). |
| **Backlog splits (overdue, on hold, disputed)** | One `FILTER` per status over the same fact, as separate measures, so a visual can stack them. |
| **Delivery date + N business days** | Count forward over DimDate filtered on `IsBusinessDay = TRUE()`. The holiday calendar lives in the date table, not the measure. |
| **Capacity vs demand, utilisation** | `SUMMARIZE` to the resource grain, assigned ÷ available per resource, then `AVERAGEX`. |
| **Days of supply / cover** | On-hand ÷ average daily usage over a trailing window. |

## Workforce

| KPI | Shape |
|---|---|
| **Headcount as-of** | The as-of shape over employment spans. Never `COUNTROWS` a snapshot table that already holds one row per person per period. |
| **Joiners / leavers** | Set membership between two period-end headcount sets. |
| **Turnover rate** | Leavers in period ÷ average headcount over the period. |
| **Utilisation / billable %** | Billable ÷ available hours per person, then averaged over people. |
| **Absence rate** | Absence days ÷ scheduled days over a date window. |

## Report-support measures

These outnumber the business KPIs in a real model, and they are the ones most often written
badly. They are still measures — the same pattern applies.

| Need | Shape |
|---|---|
| **Dynamic title** | Build the string from the selection with `SELECTEDVALUE` / `CONCATENATEX` + `SWITCH`. The `semantic-models:date-table` skill ships `Dates Selected` for the date part — don't rewrite it. |
| **Selected value / difference from selected** | `SELECTEDVALUE` (or `MAX` over a disconnected selector table) as a scalar VAR, then compare each row against it. |
| **Conditional-formatting colour** | A measure returning a hex string from `SWITCH( TRUE(), … )`. Return the *colour*, not a rank, and keep the thresholds in one measure so every visual agrees. |
| **Data label text** | Concatenate the formatted number and its unit. Reach for this only when the visual genuinely cannot do it — a value that stays numeric is worth more than a pretty string. |
| **Icon / arrow / delta indicator** | `SWITCH( TRUE(), __Delta > 0, "▲", __Delta < 0, "▼", "" )`, with the colour as a separate measure. |
| **Tooltip measures** | Small, single-purpose, named so it is obvious they belong to a tooltip page. |
| **SVG in a table or card** | Return a `data:image/svg+xml` string, with the column's data category set to *Image URL*. `custom-visuals:svg-visuals` is the real toolkit — check its UDF libraries before hand-rolling one. |

> **Formatting belongs in the format string, not the measure.** If a measure returns text only
> so the number looks right, it is the wrong tool: keep it numeric and use a dynamic format
> string. See the number-formatting section of [`../SKILL.md`](../SKILL.md).

> Implementing any of these: build the smallest table that represents the question, debug it
> with `RETURN TOCSV( __Table )` before trusting the number, and keep filters on precomputed
> integer or boolean columns so the storage engine does the work.
