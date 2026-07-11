# Business KPI Recipes (No CALCULATE)

Inventory and characteristic patterns from *DAX For Humans* Ch. 7–11. Each KPI is solved
with the core pattern (scalar VARs → table VAR via `FILTER`/`SUMMARIZE` → X-aggregate). Use
this as a map: when a user asks for one of these, reproduce the *shape* below in
No-CALCULATE style and adapt column names to their model.

The unifying techniques you'll reuse constantly here:
- **Cohort/set membership** — build a table of distinct keys for period A and another for
  period B, then `EXCEPT`/`INTERSECT`/`IN` to get new/lost/returning/retained sets.
- **As-of / point-in-time counts** — `FILTER` a transaction/event table on
  `StartDate <= asOf && (EndDate > asOf || EndDate = BLANK())`, then `COUNTROWS`.
- **Event-relative windows** — capture an event date as a scalar VAR, then filter facts to a
  window around it.
- **Per-entity then aggregate** — `SUMMARIZE` to the entity grain, add per-entity columns
  with `ADDCOLUMNS`, then `AVERAGEX`/`SUMX` (also fixes totals).

## Ch. 7 — Customers

| KPI | No-CALCULATE shape |
|---|---|
| **New / Lost / Returning customers** | Distinct customer sets for current vs prior period via `SUMMARIZE` + `EXCEPT`/`INTERSECT`; `COUNTROWS` each. |
| **Net Promoter Score (NPS)** | `% promoters − % detractors` from `COUNTROWS(FILTER(...))` over score bands. |
| **Churn rate** | Customers active at start but not at end ÷ active at start (set difference). |
| **Lifetime value (LTV)** | Per-customer revenue (`SUMMARIZE` + `ADDCOLUMNS`) × margin × expected lifetime; `AVERAGEX`. |
| **Acquisition cost (CAC)** | `DIVIDE( spend, new-customer count )` using the New-customers set. |
| **Open tickets** | As-of count: `FILTER( Tickets, Opened <= asOf && ( Closed > asOf || ISBLANK(Closed) ) )`. |
| **Funnel drop-off rate** | Counts per stage (`SUMMARIZECOLUMNS`), stage-to-stage ratios via `DIVIDE`. |
| **Better together (market basket)** | Self-join orders on common order key, count co-occurrence of item pairs. |
| **Annual contract value (ACV)** | Normalize each contract's value to a yearly figure, then `SUMX`. |
| **Sales after event** | Capture event date as scalar VAR; `FILTER` sales to `Date >= eventDate` (optionally within N days). |

## Ch. 8 — Human Resources

| KPI | No-CALCULATE shape |
|---|---|
| **Employee turnover rate** | Separations in period ÷ average headcount; both from `FILTER`+`COUNTROWS` over employment spans. |
| **Absenteeism** | Absence days ÷ scheduled days over a date window. |
| **Bradford factor** | `S² × D` per employee (S = absence spells, D = total days); `SUMMARIZE` per employee then `SUMX`. |
| **Employee satisfaction** | Banded survey aggregation (`COUNTROWS(FILTER(...))` per band). |
| **Human capital value added (HCVA)** | `DIVIDE( revenue − (cost − comp), FTE )`. |
| **Utilization** | Billable ÷ available hours, per resource then averaged. |
| **Kaplan-Meier estimator** | Survival probability as a running product across event times — build an ordered event table, compute per-interval survival, cumulative via iterating the table. |
| **Pay equality (Gini coefficient)** | Sort pay, build cumulative-share table, compute Gini from the Lorenz curve area with `SUMX`. |

## Ch. 9 — Projects

| KPI | No-CALCULATE shape |
|---|---|
| **Burndown chart** | Ideal vs actual remaining work by date; ideal from linear arithmetic, actual from running totals over `ALL` dates. |
| **Planned & Earned Value (EVM)** | PV/EV/AC as `SUMX` over tasks filtered by date and % complete. |
| **Schedule variance** | `EV − PV`. |
| **Actual cost / Cost variance** | AC from cost facts; `CV = EV − AC`. |
| **Overlap** | Count tasks whose `[Start,End]` intervals intersect a given interval (interval-overlap `FILTER`). |
| **Overworked** | Resources whose summed assigned hours in a window exceed capacity (`SUMMARIZE` per resource + `FILTER`). |

## Ch. 10 — Finance

| KPI | No-CALCULATE shape |
|---|---|
| **Gross margin / revenue / cost** | Straight `SUMX`/`DIVIDE`. |
| **Currency exchange rates** | Join facts to a rate table by date+currency via `FILTER`/`TREATAS`-free lookup; convert per row in `SUMX`. |
| **Periodic billing** | Expand a contract into billing periods (generated table) and sum recognized amounts per period. |
| **Reverse year-to-date** | Remaining-in-year: total − YTD, using offset filters. |
| **Comparing budgets and actuals** | Align grains with `SUMMARIZECOLUMNS`, variance via `ADDCOLUMNS` + `DIVIDE`. |
| **Accounts payable turnover ratio** | `DIVIDE( purchases, average payables )`. |
| **Modified Dietz return** | Time-weighted return: `(end − start − flows) / (start + Σ weighted flows)` built from a cashflow table. |
| **Compound interest** | Period-by-period growth via a generated period table and running product. |

## Ch. 11 — Operations

| KPI | No-CALCULATE shape |
|---|---|
| **On Time In Full (OTIF)** | Share of orders meeting both on-time and in-full booleans (`COUNTROWS(FILTER(...))`). |
| **Order cycle time** | `AVERAGEX` of `(delivered − ordered)` per order. |
| **Delivery dates** | Add business days to an order date by filtering a working-day calendar (No-CALCULATE `WORKDAY`). |
| **Mean time between failure (MTBF)** | Operating time ÷ failure count; gaps between failure events via previous-occurrence pattern. |
| **Overall equipment effectiveness (OEE)** | `Availability × Performance × Quality`, each a `DIVIDE` over event facts. |
| **Days of supply** | `DIVIDE( on-hand, average daily usage )`. |
| **Order fulfillment** | Fill rate / backorder share via set membership and counts. |

> When implementing any of these: start from the core pattern, build the smallest table that
> represents the question, and **debug with `RETURN TOCSV( __Table )`** before trusting the
> number. Keep filters on precomputed/integer columns (e.g. date offsets, boolean flags) so
> the storage engine does the heavy lifting.
