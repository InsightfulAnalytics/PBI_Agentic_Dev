# Making a slow Power BI financial matrix fast

A method for one specific, extremely common problem: a P&L-shaped matrix whose rows or columns are
**dispatched**: a `SWITCH(SELECTEDVALUE(...))` over a disconnected table, or a calculation group on
an axis, which takes seconds to render and gets worse every time a row is added.

Two sources feed these documents:

- **The lab.** `PL Switch Lab` / `PL Bridge Demo`, a purpose-built synthetic model (74.9M-row fact)
  whose whole reason to exist is to isolate this cost and measure it. Every implementation here is
  built twice in that report (the slow way and the fast way) so the two can be timed side by side.
- **The field.** A client production report where the method was diagnosed and then, once, applied
  end to end. The client is not named, and every report, page, visual and model-object name from it
  has been replaced with a neutral stand-in: the table, column and measure names in these documents
  are illustrative, not the originals. The two visuals involved are referred to as **the diagnosed
  matrix** (profiled, never rebuilt) and **the unrenderable matrix**
  (rebuilt: 10,984 ms → 406 ms).

Every number quoted in these documents was measured; nothing is estimated unless it says so.

## Start here

A slow financial matrix is almost never one problem. It is up to three independent costs stacked on
top of each other, and they have different fixes:

| Cost | What it is | Fix |
|---|---|---|
| Row dispatch | One query plan must satisfy every branch of the `SWITCH` (or every item of the calculation group) so every branch and every measure under it is materialised whether or not the cell needs it | [The bridge method](02-bridge-method.md), or [the Deneb grid template](04-deneb-grid-template.md) |
| Per-cell format strings | `formatStringDefinition` is evaluated once per rendered cell; one that references its own measure evaluates that measure again per cell | [The per-cell tax](03-format-string-and-cf-tax.md) |
| Per-cell CF measures | Each conditional-formatting colour slot bound to a measure is another evaluation per cell | [The per-cell tax](03-format-string-and-cf-tax.md) |

**Do not skip the diagnosis.** The two per-cell costs are invisible to a DAX query benchmark: an
`EVALUATE` never evaluates a format string, so a visual can be far slower than the query behind it
while the DAX profile looks innocent. [Diagnosing a slow P&L
matrix](01-diagnosing-slow-matrices.md) shows how to separate them with a subtraction: Performance
Analyzer's total minus the same query run over ADOMD. On the lab's monthly matrix that
subtraction is 12,412 ms minus 2,178 ms: **82% of the visual's cost is invisible to the DAX**.

## The documents

1. **[Diagnosing a slow P&L matrix](01-diagnosing-slow-matrices.md)**: the three costs, the
   scan-count heuristic, and a reproducible measurement procedure (port discovery, pinning slicer
   context, cold vs warm) using `tools/run_dax.ps1`.
2. **[The bridge method](02-bridge-method.md)**: the structural fix. Replace row dispatch with
   filtering: a physical line-to-account table and a relationship, so there is no dispatch DAX at
   all. Measured 21x cold and ~150x warm in the lab. Only applies when the rows *are* a filterable
   account set.
3. **[The per-cell tax](03-format-string-and-cf-tax.md)**: dynamic format strings and CF measures,
   how to measure them, and the ranked remedies.
4. **[The Deneb grid template](04-deneb-grid-template.md)**: the implementation spec. The engine
   returns only the irreducible grouped dataset; a Vega spec derives every extra column, lays out
   the grid, formats every number and colours every cell client-side. This is the fix when the
   bridge is unavailable, and it takes the per-cell tax to zero.
5. **[Field case: the unrenderable matrix](05-case-unrenderable-matrix.md)**: the method applied
   end to end on a client production page: 10,984 ms to 406 ms in Performance Analyzer, no model
   change and no new DAX, on a visual that would not render in the Power BI Service at all.
   Includes the two traps that a flat grouped query introduces and a calculation-group matrix hides.
6. **[PBIR build playbook](06-pbir-build-playbook.md)**: the operational rules for editing a real
   report's files safely. Every item in it broke something at least once.
7. **[Lab reproduction: the monthly matrix](07-lab-monthly-matrix.md)**: the same case rebuilt in
   the open on the lab model, both halves in one report so you can measure the before and the after
   yourself. This is the one to read if you want to run the experiment rather than take the numbers
   on trust.
8. **[Measured results: all nine pages](08-measured-results.md)**: every technique in this set,
   measured on the same model on the same afternoon under one protocol. Bridge against SWITCH,
   one calculation group against two, native against Deneb. **This is the table to quote.**

## Tools

The first two are self-contained and live in [`tools/`](tools/).

| File | What it does |
|---|---|
| `tools/run_dax.ps1` | Times a `.dax` file against the open Desktop model over ADOMD. Auto-discovers the port, reports cold and warm, prints result rows. Windows PowerShell 5.1. |
| `tools/render_local.mjs` | Renders a Deneb spec to PNG offline with Deneb's runtime helpers stubbed, so you can look at a grid without reloading Desktop. |
| `scripts/demo/pa_sweep.ps1` | Drives Power BI Desktop's Performance Analyzer over a list of pages through UI Automation: normalises the slicers, clears the engine cache, runs cold and warm, and reads the durations back out of the pane to CSV. This is what produced [08-measured-results.md](08-measured-results.md). |

```powershell
# time a candidate query, cold then warm
.\tools\run_dax.ps1 -QueryFile .\my_query.dax -Runs 2
```

```bash
# see the grid before it ever reaches Power BI
node tools/render_local.mjs spec.json config.json rows.json out.png 1600 900
```

`render_local.mjs` needs `vega`, `vega-lite` and `sharp`; it resolves them from a `node_modules`
beside itself, from `DENEB_RENDERER_PKG`, or from the deneb-pbir plugin renderer on this machine, in
that order.

## Evidence status

Be clear about what has and has not been proven, because the whole value of this set is that its
numbers are real.

**Validated in the lab.** Every multiplier quoted for the bridge method and the Deneb grid template
was measured on `PL Bridge Demo`, a purpose-built synthetic model (74.9M-row fact), with the old and
new implementations tied out cell-for-cell before timing.

**Measured, but not acted on, in the field.** The diagnosed matrix was profiled in place:
Performance Analyzer, the dispatch query, the flat base-measure query, and an equivalence check on
the `ALLSELECTED` totals. Those measurements are in
[01-diagnosing-slow-matrices.md](01-diagnosing-slow-matrices.md) and are reliable. They diagnose the
visual; they do not demonstrate a fix. A rebuild was attempted there and abandoned as needing more
work than it was worth at the time; nothing from it survives in these documents.

**Validated end to end in the field, once.** The unrenderable matrix was rebuilt with the Deneb grid
template and re-measured in place on 2026-08-28: **10,984 ms to 406 ms**, 27x, and it went from
*erroring out* in the Power BI Service to rendering there. Full workings in
[05-case-unrenderable-matrix.md](05-case-unrenderable-matrix.md). One data point, not a
distribution, and its before/after are Performance Analyzer totals, not a query-level breakdown, so
it confirms the size of the win without attributing it between the three costs.

### Field results

Before and after, same filter context, same machine, same session. Record every rebuild here so the
next person can see how the lab numbers hold up outside the lab.

| Report / visual | Before | After | Notes |
|---|---|---|---|
| Field: the unrenderable matrix | **10,984 ms** PA | **406 ms** PA | 27x, −10,578 ms. 15-item calculation group x 28 measures = 420 dispatched evaluations, plus 315 cells of dynamic format string, replaced by one 12-row query. No semantic model change, no new DAX. Errored in the Service before; renders after. 2026-08-28. [Case study](05-case-unrenderable-matrix.md) |
| Lab: Monthly P&L, calc group → Deneb | **12,412 ms** PA cold (2,178 ms cold / 1,228 ms warm query) | **332 ms** PA cold (124 ms cold / 17 ms warm query) | **37.4x cold, 69.5x warm on the visual**, −12,080 ms, a 97.3% reduction. The same shape reproduced in the open on `PL Bridge Demo` (74.9M-row fact), both halves in one report. The 10,234 ms between the matrix's 12,412 ms visual and its 2,178 ms query is the 315-cell format-string tax plus render, invisible to any `EVALUATE`: **82% of the cost is where a DAX profile cannot see it.** 315-cell tie-out: 0 mismatches. [All nine pages](08-measured-results.md), [workings](07-lab-monthly-matrix.md) |
| Lab: P&L accounts, SWITCH → bridge | **4,815 ms** PA cold | **348 ms** PA cold | 13.8x cold, 14.4x warm, and the fast build is still a native `tableEx`. Use this, not Deneb, when the statement rows are a filterable set of accounts. [Method](02-bridge-method.md) |
| Lab: odd rows, 2 calc groups → Deneb | **7,530 ms** PA cold | **419 ms** PA cold | 18.0x cold, 22.8x warm on rows the bridge cannot express (ratios, per-unit metrics, a distinct count). The same 182 cells as a 13-branch `SWITCH` cost 1,680 ms, so **removing `SWITCH` in favour of a second calculation group made it 4.5x slower.** [Details](08-measured-results.md) |
