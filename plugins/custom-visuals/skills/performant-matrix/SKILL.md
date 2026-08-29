---
name: performant-matrix
version: 26.25
description: 'Diagnose a slow financial matrix before fixing it: separate row-dispatch cost from the per-cell format-string and conditional-formatting tax, then choose with the user between a bridge-table model fix, a native restructure, or a Deneb grid. Use whenever a P&L or financial matrix is slow or unrenderable ("the matrix takes 10 seconds", "slow P&L visual", "my SWITCH dispatch measure is slow", "calculation group on rows is slow", "Performance Analyzer is much higher than the DAX time", "the matrix errors in the Service"). Deneb is one of three outcomes, never the assumed one. Vega spec authoring lives in custom-visuals:deneb-visuals and spec round-tripping in custom-visuals:deneb-pbir.'
---

# Performant Matrix: diagnosing and fixing a slow financial matrix (PBIR)

> **Report modification requires tooling.** Two paths exist:
> 1. **`pbir` CLI (preferred)** -- use the `pbir` command and the `pbir-cli` skill. Install with `uv tool install pbir-cli` or `pip install pbir-cli`. Check availability with `pbir --version`.
> 2. **Direct JSON modification** -- if `pbir` is not available, use the `pbir-format` skill (pbip plugin) for PBIR JSON structure and patterns. Validate every change with `jq empty <file.json>`.
>
> If neither the `pbir-cli` skill nor the `pbir-format` skill is loaded, ask the user to install the appropriate plugin before proceeding with report modifications.

The shape this skill is for: a P&L matrix whose rows or columns are **dispatched** by a `SWITCH(SELECTEDVALUE(...))` over a disconnected table, or by a calculation group on an axis. It takes seconds to render, it gets worse every time a row is added, and past a certain size it stops rendering in the Power BI Service at all.

**Order: DIAGNOSE, then CONSULT, then BUILD.** There are three remedies and they fix different costs. Do not start building until the measurement says which cost dominates and the user has picked a remedy. **Deneb is one of three outcomes, and on account-shaped rows it is the wrong one** (bridge 348 ms cold against Deneb 294 ms cold: not worth a custom visual).

## The three costs

| Cost | Paid per | Visible to `EVALUATE`? | Remedy |
|---|---|---|---|
| (a) Row dispatch | query plan | yes | bridge table, or a Deneb grid |
| (b) Dynamic format strings | rendered cell | **no** | the per-cell ladder |
| (c) Conditional-formatting colour measures | rendered cell, per colour slot | **no** | the per-cell ladder |

(b) and (c) are invisible to every DAX benchmark you will run. An `EVALUATE` returns raw values and never evaluates a `formatStringDefinition`, so a visual can be far slower than the query behind it while the DAX profile looks innocent. That is why the subtraction, not the query timing, is the diagnostic.

**Mechanism for (a):** one query plan is built for the whole group, not one per cell. When the dispatch column is grouped on rows, the engine must compile a single plan capable of producing *every* row of that group, so every branch, every measure under it, and every measure under those gets materialised. Branch pruning cannot fire, by construction. A calculation group on an axis is the same mechanism wearing different syntax, and its cost is `items x measures`.

**Corollary: a card is not affected.** When a slicer filters the dispatch column to one value instead of grouping it, pruning fires and there is nothing to win. Only the grouped-rows case is broken.

## Workflow: fixing a slow matrix

### Step 1: Pin the context and measure

Two things invalidate everything downstream, so do them first.

- **Pin the slicers to what the visual actually has selected.** If you do not, you are not measuring what the visual measures. A stray month selection compares a twelfth of the data against all of it; that single mistake is the difference between 9,133 ms and 12,412 ms on the lab's own monthly matrix.
- **Keep the totals in the timing query.** The matrix shows subtotals, so the query needs `ROLLUPADDISSUBTOTAL` on the grouped column and the flat shape needs its `ALLSELECTED` total measures. Drop either and you timed a different visual: on the diagnosed matrix, removing the 36 `ALLSELECTED` total columns took a flat query from 1,580 ms to 819 ms cold.

Then take three readings, all under the same pinned context:

1. **Performance Analyzer total** for the visual (View -> Performance Analyzer -> Start recording -> Refresh visuals, not a page click). Use **Copy query** to get the exact DAX the visual sends.
2. **The dispatch query**, run bare over ADOMD: `scripts/run_dax.ps1 -QueryFile .\dispatch.dax -Runs 2`.
3. **The flat query** over the same base measures with no dispatch: `examples/flat-query.dax`.

Run each at least twice: run 1 cold, run 2 warm. Measurement mechanics (port discovery, the ADOMD DLL, cold vs warm) are in `references/diagnosing.md`.

### Step 2: Run the two subtractions

- **Dispatch overhead = dispatch query - flat query.** This is what removing dispatch can win. Lab: 2,178 ms dispatch query against a 124 ms grid query.
- **Per-cell tax = Performance Analyzer total - DAX time for the same query.** Only report this when both readings come from the same pinned context and the same thermal state. Clean lab case: 12,412 ms PA cold minus a 2,178 ms cold query leaves **10,234 ms invisible to DAX, 82% of the visual's cost**. Contaminated field case: PA read 3,861 ms while the dispatch query read 4,493 ms cold / 1,997 ms warm, so PA sits *between* the two readings and no clean subtraction is available. Say so rather than quoting a number you cannot defend.

Two supporting signals, neither of them a gate:

- **Warm vs cold.** Warm roughly equal to cold means formula-engine bound; warm much faster than cold means the scans are real. The trap: warm much faster than cold does **not** rule out dispatch. The field dispatch query was 4,493 ms cold / 1,997 ms warm and still carried roughly 500 ms of dispatch. Only the flat comparison settles it.
- **Double the date filter.** If the time barely moves, you are paying for the plan, not the data: 22.4M rows cost 2,963 ms and 50.3M rows cost 3,473 ms, 2.2x the data for 17% more time.

### Step 3: Find the measure floor

The flat query **is** the floor. No visual technique goes below it. If the flat number is already most of your target, stop: this is a measure problem, not a visual problem. On the lab model that floor is 17 ms warm; on a model whose base measures cost 800 ms, 800 ms is what you get.

### Step 4: Route the symptom

| Symptom | Likely cost |
|---|---|
| PA total is close to DAX time; the dispatch query costs much more than a flat query of the same base measures; DAX time scales with branches, not with fact rows | (a) row dispatch |
| Rows or columns come from a **calculation group** rather than a `SWITCH` | (a) row dispatch, same mechanism |
| PA total is much larger than DAX time; the value measure appears inside its own `formatStringDefinition` | (b) format string |
| PA total is much larger than DAX time; several colour measures bound to conditional formatting | (c) CF measures |
| Both (a) and (b)/(c), and the layout is a fixed grid you control | all three at once |
| The flat base-measure query is already most of the dispatch query | **the measures are the floor** |

Rows 1 and 6 are not exclusive. The diagnosed matrix was both at once: roughly 500 ms of warm dispatch overhead sitting on a 1,500 ms warm measure floor, which is why a structural fix alone would not have carried it.

### Step 5: Consult the user

**The defining step. Do not proceed until it is answered.** Two pre-checks fire before the question is asked.

**Pre-check 1 (do not consult, just stop):** if the flat base-measure query is already most of the dispatch query, say:

> Your measures are the floor, not the visual. The flat query over the same base measures is `<B>` ms against a `<A>` ms dispatch query, and no visual technique goes below `<B>` ms. Fix the measures or put fewer on screen; rebuilding the grid buys you `<A - B>` ms at most.

**Pre-check 2 (present two options, not three):** if the bridge gate below fails, drop option 1 and name the clause that failed.

**The consultation block:**

> Here is what your matrix is paying for, from the pinned-context measurements:
>
> - **Row dispatch**: `<dispatch query>` minus `<flat query>` = **`<X>` ms**
> - **Per-cell tax** (format strings + CF colour measures, invisible to `EVALUATE`): Performance Analyzer `<PA>` ms against a `<dispatch>` ms query leaves roughly **`<Y>` ms** unaccounted for
> - **Measure floor**: `<flat query>` ms. Nothing below this is reachable.
>
> Three ways forward. They are not equivalent, and the fastest one is not the one I would recommend by default.
>
> **1. Bridge the model, keep the native visual.**
> Add a physical line-to-account bridge table and a bidirectional relationship; the row measures stop asking "which row am I on" and start asking "which accounts does this row cover". Removes row dispatch at the source.
> *Buys:* on the lab's account-shaped P&L, 4,815 ms to 348 ms cold (13.8x) and 4,594 ms to 319 ms warm.
> *Costs:* a model change, and a bidirectional relationship on a shared dimension can create ambiguous filter paths. I check the blast radius before committing, and RLS needs `securityFilteringBehavior` set separately.
> *Keeps:* native sorting, drill, export to Excel, the conditional-formatting UI, and every future visual inherits it.
>
> **2. Restructure natively, no new tables.**
> Static format strings where the column shares an order of magnitude; kill any `formatStringDefinition` that references its own measure; collapse CF colour measures to a colour column or a static rule; fewer measures on screen.
> *Buys:* the per-cell tax only. Measured: 182 cells went from 622 ms static to 1,270 ms with a self-referencing dynamic format string, so that half is real money.
> *Costs:* row dispatch stays. And a warning: replacing a `SWITCH` with a calculation group on rows made the same 182 cells **4.5x slower** (1,680 ms to 7,530 ms), so "modernising" the dispatch is not a fix.
> *Keeps:* everything. Zero model risk.
>
> **3. Rebuild the grid in Deneb.**
> One flat query, all cells derived client-side. Removes dispatch *and* the per-cell tax at once.
> *Buys:* on rows that are **not** an account set, 12,412 ms to 332 ms (37.4x cold, 69.5x warm), and 419 ms where every native alternative sat between 1,680 ms and 7,530 ms.
> *Costs:* you rebuild the grid chrome by hand. Column widths, headers, indentation, totals and colours are all spec. No native sort, no export, no drill, no CF pane. A Vega spec to maintain.
> *Note:* where the rows **are** an account set, Deneb only beats the bridge 294 ms to 348 ms. **The bridge wins on effort, not on time.**
>
> Which do you want? If you are unsure: **1** if your rows are an account set and you can change the model; **3** if they are not, or you specifically want client-side formatting and colour; **2** if the model is frozen.

Then ask only what the block above has not already answered:

- Can I change the semantic model: add a table and a bidirectional relationship?
- Is this report already published and in use, or still in development? (Bidirectional filtering changes answers for unrelated measures; I want to know the blast radius.)
- Does anyone rely on native sort, export to Excel, drillthrough, or the conditional-formatting pane on this visual?

If the user names a mixed statement, add: *"Rows that are account sets can go on the bridge and ratio rows can stay ordinary measures, and one grid renders both. Want the mixed build?"*

### Step 6: Build the chosen remedy

- **Bridge.** `references/bridge-method.md` for the build and migration recipe, `examples/bridge-table.tmdl` for the table, relationship and one bridge measure. This is a model change: route TMDL edits through the `pbip:tmdl` and `semantic-models:semantic-model` skills.
- **Native restructure.** The per-cell ladder below, plus `references/per-cell-tax.md` for the TMDL syntax and the self-referencing-format-string audit script.
- **Deneb grid.** `references/deneb-grid-template.md` for the dataset contract, transforms and PBIR embedding. Author the spec with `custom-visuals:deneb-visuals`, round-trip and offline-render it with `custom-visuals:deneb-pbir`. **Dispatch the `deneb-reviewer` agent before presenting the spec to the user.**

Report-file edit safety (clone-and-compare, the filter-name census, validate baselines) is in `references/pbir-build-safety.md`.

### Step 7: Tie out

Put old and new measures in the **same** query over the **same** grouping and count mismatches. The gate is zero. Two eyeballed screenshots are not a tie-out: a missing (line, account) pair produces a *smaller* number, not an error.

`examples/tie-out.dax` has the shape, including the `+ 0` guard: `COUNTROWS` over an empty filter returns `BLANK`, not `0`, so without it a clean tie-out is indistinguishable from a query that never ran. Repeat under every slicer state that matters.

## The bridge applicability gate

**Applies when** the statement's rows can be written as *"which accounts or keys does this row cover"*. The row axis then becomes a filter and there is no dispatch DAX at all.

**Does not apply** when any of these is true for a meaningful share of rows:

- The row is a **ratio or a rate**: one measure divided by another, not a sum over a key set.
- The row is a **share of a total computed with `ALLSELECTED`**, which is filter-context manipulation and cannot be expressed as membership in an account list.
- The row is a **distinct count** or another non-additive aggregate. A subtotal is then no longer "a line with more rows", because the union of two account sets does not distinct-count to the sum of their distinct counts.
- The rows are **different grains** (per store, per unit, per transaction) needing a different denominator each.

**Two shape checks before committing.** Signs: the pattern assumes costs are stored negative so every subtotal is a plain sum; otherwise the bridge needs a `Sign` column and a `SUMX`, which puts the iteration back. Join key: match on `AccountKey`, never on the display label, or a renamed row silently blanks that line.

**Blast radius: do not skip.** Bidirectional filtering on a *shared* dimension can create ambiguous filter paths. Desktop will either refuse the relationship or, worse, accept it and change the answer for measures that had nothing to do with the P&L. Re-check other visuals that touch the account dimension. RLS is a separate switch (`securityFilteringBehavior = BothDirections`, off by default). If the model will not take it, fall back to the `TREATAS` variant or to `CROSSFILTER(..., BOTH)` scoped inside the bridge measures only.

**Not exclusive.** A mixed statement puts its account-backed lines on the bridge and its ratio lines on ordinary measures, then renders both through one grid.

## The per-cell remedy ladder

Applied in order. The grep target for cost (b) is a `formatStringDefinition` that opens `VAR _VALUE = ABS ( [X] )`: the cell evaluates `[X]` for its value, then the format string evaluates `[X]` again to decide how to print it.

1. **Static `formatString`.** The tax goes to zero because there is nothing to evaluate. Only valid when every cell in the column lives in the same order of magnitude.
2. **A text measure that pre-formats once.** Return `FORMAT` over a `VAR` you already computed, so the double evaluation disappears. Cost: the column is text, so no sort by value, no data bars, no numeric aggregation. **Untested: the mechanism is clear but the delta was never measured.**
3. **Fewer CF slots.** Where the colour is a property of the *row* rather than of the value, a static rule or a `fieldValue` colour column beats a measure. Keep measure-driven CF only where the colour genuinely depends on the number.
4. **Move all formatting client-side (Deneb).** This tax goes to zero, not down.

## Gotchas (hard-won)

- **Removing `SWITCH` made it slower.** Replacing a 13-branch `SWITCH` with a second calculation group on rows took the same 182 cells from 1,680 ms to 7,530 ms, 4.5x *worse*. Cost is instantiation count, not branch count. "Calculation groups are the modern replacement for `SWITCH`" is not true for performance on this shape.
- **`IFERROR` on every branch more than doubled the cost:** 2,757 ms to 5,997 ms cold in the lab. If a branch can error, fix the branch.
- **Only calendar-registered columns are safe to group in a flat rebuild.** `DATEADD` shifts filters only on registered columns; an unregistered helper column of the same table sitting in the `GROUP BY` survives the shift, and every `*LY` measure returns `BLANK`. Symptom: current-period values perfect, prior-period all blank, no error anywhere. The fix costs no DAX: bind the column as an `Aggregation` field with `Function: 3` (Min). **Scope limit:** a classic marked date table (`dataCategory: Time`) does not have this problem, because `DATEADD` removes filters from every column of that table. The trap belongs to the modern `calendar` object, where registration is explicit and partial.
- **`null` coerces to `0` in JavaScript.** Guard derived thresholds in a Deneb spec with `isValid` and let them stay `null`, so dependent columns fail closed to blank. A visibly empty column gets reported; a plausible one ships.
- **The format-string A/B, the number to quote:** 182 cells warm, 622 ms with a static format string, 1,270 ms with a dynamic one that references its own measure. Same measure, same query, same cells.
- **With two calculation groups the higher-precedence group's format string wins outright**, and `SELECTEDMEASUREFORMATSTRING()` inside it returns the *base measure's* format string. The lower group's format strings are never consulted at all.
- **A clean `pbir validate` and a clean DAX profile are not evidence the visual is fast.** Neither one looks at formatting. The canvas is the referee.

## Limitations

| Constraint | Desktop | Service |
|---|---|---|
| Dispatched matrix past a few hundred evaluations | very slow | may fail to render at all |
| Per-cell tax visible to `EVALUATE` | no | no |
| Performance Analyzer cache state | not reported | n/a |
| Deneb grid: native sort / export / drill / CF pane | none | none |
| Bridge: bidirectional relationship | may be refused as ambiguous | same |
| RLS across a bidirectional relationship | off unless `securityFilteringBehavior` is set | same |

## When to Use Each Remedy

**Bridge** when the rows are an account set and the model can take the relationship. It gets 99% of the improvement Deneb gets, it stays a native visual, and it is a one-off model change every future visual inherits. Measured A/B on that shape: bridge 348 ms cold against Deneb 294 ms cold. **The bridge wins on effort, not on time.**

**Deneb** when the rows are not an account set, and then it is not close: 419 ms against 1,680-7,530 ms for every native alternative on the same rows. Also choose it where the bridge applies if you want client-side formatting and colour and you accept rebuilding the grid chrome by hand.

**Native restructure** when the model is frozen. It buys back the per-cell tax and leaves dispatch alone.

**Neither, when the measures are the floor.** The grid removes dispatch, per-cell format strings and per-cell conditional formatting. It does not make `SUM` over 74.9M rows faster.

## References

- **`references/diagnosing.md`** -- measurement mechanics: port discovery, the ADOMD DLL, pinning the filter context, cold vs warm, the scan-count heuristic
- **`references/bridge-method.md`** -- the bridge build, migration recipe and tie-out
- **`references/per-cell-tax.md`** -- format-string and CF mechanics, TMDL syntax, the self-reference audit script
- **`references/deneb-grid-template.md`** -- the grid implementation spec: dataset contract, transforms, client-side formatting, PBIR embedding
- **`references/measured-results.md`** -- all nine lab pages under one protocol, the table to quote
- **`references/pbir-build-safety.md`** -- safe edit mechanics on a live report
- **`examples/flat-query.dax`** -- the flat base-measure probe that establishes the measure floor
- **`examples/tie-out.dax`** -- old against new in one query, with the `+ 0` blank guard
- **`examples/bridge-table.tmdl`** -- bridge table, relationship and one bridge measure
- **`scripts/run_dax.ps1`** -- times a `.dax` file against the open Desktop model over ADOMD, cold and warm

External: [Understanding the optimization of SWITCH](https://www.sqlbi.com/articles/understanding-the-optimization-of-switch/) (Russo and Ferrari, SQLBI) is the load-bearing reference for cost (a).

## Fetching Docs

To retrieve current Power BI performance and modelling docs, use `microsoft_docs_search` + `microsoft_docs_fetch` (MCP) if available, otherwise `mslearn search` + `mslearn fetch` (CLI). Search based on the user's request and run multiple searches as needed to ensure sufficient context before proceeding. Note: Vega/Vega-Lite docs live at vega.github.io (not MS Learn) -- use `WebFetch` for those.

## Related Skills

- **`deneb-visuals`** -- Vega/Vega-Lite spec authoring, theme colors, interactivity (the Deneb branch)
- **`deneb-pbir`** -- extract/embed the spec in visual.json + offline render to verify without Power BI
- **`semantic-model`** (semantic-models plugin) -- the bridge branch is a model change: bridge table, relationship, RLS filtering behavior
- **`tmdl`** (pbip plugin) -- direct TMDL edits for the bridge table and format strings
- **`dax-optimisation`** (semantic-models plugin) -- when the flat base-measure query IS the floor
- **`pbir-format`** (pbip plugin) -- PBIR JSON format reference
- **`pbi-report-design`** -- layout and design best practices
