# Diagnosing a slow financial matrix

A dynamic financial matrix is slow for up to three independent reasons, and they have three
different fixes. Work out which one the user is paying before changing anything: the structural
fix in [bridge-method.md](bridge-method.md) does nothing for a format-string problem, and killing
format strings does nothing for a dispatch problem.

The diagnostic is two subtractions:

- **Dispatch overhead** = the dispatch query minus a flat query over the same base measures. What
  is left underneath is the measure floor.
- **Per-cell tax** = the Performance Analyzer total minus the DAX-only time for the same query,
  and only when both readings are honestly comparable (see [Subtraction 2](#subtraction-2-per-cell-tax)).

Everything below is how to get those numbers honestly and what to do with the answer.

Two conventions for the evidence quoted throughout:

- **"the reference model"** is the open reproduction lab: a 74.9M-row fact table with the slow and
  fast builds of the same statement side by side in one report. Every number attributed to it is
  reproducible.
- **"the diagnosed matrix"** and **"the unrenderable matrix"** are two production visuals that were
  measured but cannot be shared. Their numbers are evidence, not something you can re-run.

## The three costs

| Cost | Paid per | Visible to `EVALUATE`? | Fix |
|---|---|---|---|
| (a) Row dispatch | query plan | yes | [bridge-method.md](bridge-method.md) |
| (b) Dynamic format strings | rendered cell | **no** | [per-cell-tax.md](per-cell-tax.md) |
| (c) Conditional-formatting measures | rendered cell, per colour slot | **no** | [per-cell-tax.md](per-cell-tax.md) |

(b) and (c) are invisible to every DAX benchmark you will run. That is why the subtraction, not the
query timing, is the diagnostic.

### Cost (a): row dispatch

The shape: a disconnected table holds one row per statement line, sits on the matrix rows, and one
measure decides what each row means.

```dax
Row Amount =
SWITCH ( SELECTEDVALUE ( 'Statement Rows'[Items] ),
    "Revenue",        [Revenue Main],
    "Cost of Sales",  [Cost of Sales Main],
    "Gross Profit",   [Gross Profit Main],
    -- ...one branch per statement line...
)
```

The mechanism is not data volume and it is not the branches being slow. **One query plan is built
for the whole group, not one per cell.** When the switch column is grouped on rows, which is exactly
what a matrix does (`SUMMARIZECOLUMNS('Statement Rows'[Items], ...)`), the engine must compile a
single plan capable of producing *every* row of that group. Every branch is therefore reachable, so
every branch, every measure under it, and every measure under *those* gets materialised into the
plan. Branch pruning cannot fire, by construction. Each cell then needs exactly one branch out of
the plan it just paid to build.

Marco Russo and Alberto Ferrari document the same failure from the other side in
[Understanding the optimization of SWITCH](https://www.sqlbi.com/articles/understanding-the-optimization-of-switch/):
`SWITCH` optimises *only* when the switch column is directly filtered in the filter context, and
when it is not, the engine "prepares for the execution of all the branches, even though many of them
will never provide a result to the report". Their worked example goes from a 40-row physical query
plan to 190.

**A calculation group on a matrix axis is the same cost wearing different syntax.** Its items are
grouped on that axis exactly as a disconnected switch column would be, so the engine compiles one
plan capable of producing every item for every measure on the other axis, and the cost is
`items x measures`. It is arguably worse than a `SWITCH`, because a calculation item usually
rewrites the filter context (`CALCULATE ( SELECTEDMEASURE (), ALLEXCEPT ( ... ), ... )`) rather than
just selecting a different measure. Twelve period items differing only in a literal are still twelve
different filter contexts to the plan, so the engine cannot collapse them into the single `GROUP BY`
scan the same data would need if the period were simply a column on the axis. Measured on the
unrenderable matrix: 15 items x 28 measures = 420 dispatched evaluations, **10,984 ms** in
Performance Analyzer, **406 ms** after the rebuild.

Two consequences worth knowing before you measure:

- **This is a formula-engine cost, so it barely tracks row count.** See
  [the data-volume control test](#the-data-volume-control-test) below.
- **A card is not affected.** When a slicer filters the switch column to one value instead of
  grouping it, pruning fires and there is nothing to win. Only the grouped-rows case is broken. Do
  not go looking for dispatch cost in a visual that does not group the dispatch column.

### Cost (b): per-cell format strings

A `formatStringDefinition` is evaluated **once per rendered cell**. If it references its own
measure, that measure is evaluated a second time per cell. The tell is a format string that opens
like this:

```dax
VAR _VALUE = ABS ( [Row Amount] )
```

Every cell then pays for the dispatch measure twice: once for the value, once to decide how to
print it. On a plan where the dispatch is already the expensive part, that is close to a doubling
of the visual's DAX work, and no DAX query will ever show it to you. ADOMD returns raw values and
never evaluates `formatStringDefinition`.

Measured on the reference model, on a 182-cell grid, warm: the *visual* went from **622 ms to
1,270 ms** purely from adding a dynamic format string that references its own measure. Those are
visual timings, not query timings: the query behind that grid is 27 ms, so the 648 ms difference is
all per-cell work. Detail and the remedies are in [per-cell-tax.md](per-cell-tax.md).

### Cost (c): per-cell conditional-formatting measures

Same shape, different hook. Each conditional-formatting slot on the visual runs its colour measure
once per cell. The diagnosed matrix carried four: a row highlight, a row highlight text colour, and
two value colour measures.

Count the cells before dismissing this. On the diagnosed matrix: 26 rows from `'Statement Rows'`
(18 distinct metrics; 5 section-header rows carry no measure; 3 metrics appear twice) x 4 column
groups x 2 slots = 208 cell positions, of which 21 x 4 x 2 = 168 carry a measure. Each of those runs
the value measure, the format string (which re-runs the value measure), and up to four colour
measures. **That arithmetic is derived from the visual's shape, not measured**: no per-cell timing
was taken on that visual. Use it to size the problem, not to quote a number.

## How to measure

Nothing here needs anything installed beyond Power BI Desktop and a .NET Framework build of the
ADOMD client DLL, which several tools already ship. You do not have to open any of them.

### 1. Performance Analyzer gives the visual total

View -> Performance Analyzer -> Start recording -> refresh the page. Take the visual's total: DAX
plus render plus format strings plus conditional formatting.

Use **Copy query** on that row. It hands you the exact DAX the visual sends, filter tables and all,
which is the cheapest way to get the filter context right. If you want the residue in
[Subtraction 2](#subtraction-2-per-cell-tax) to mean only one thing, time that query verbatim rather
than a hand-written equivalent.

Two protocol points that decide whether the reading is usable:

- **Refresh visuals**, not a page click. Revisiting a page can serve from the report canvas cache
  and log a misleading 0 ms.
- Clear the cache before each cold reading, and say which state each number is in. Performance
  Analyzer does not tell you afterwards.

### 2. Find the port and run the query

`msmdsrv.exe` is Desktop's local Analysis Services instance:

```powershell
$msmdPids = (Get-Process msmdsrv).Id
Get-NetTCPConnection -State Listen |
    Where-Object { $msmdPids -contains $_.OwningProcess } |
    Select-Object OwningProcess, LocalPort
```

Use `Get-NetTCPConnection`, not `netstat`: it avoids the duplicate IPv4/IPv6 rows.

The ADOMD DLL must be a **.NET Framework** build. Windows PowerShell 5.1 cannot load a .NET 8 one:
`Add-Type` throws `ReflectionTypeLoadException` ("Unable to load one or more of the requested
types"). That error means the wrong build, not a missing ADOMD.

`scripts/run_dax.ps1` does the port discovery, the DLL probe, and the connect/time/print loop.
Save the query to a `.dax` file and point the script at it:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File "${CLAUDE_PLUGIN_ROOT}/skills/performant-matrix/scripts/run_dax.ps1" `
  -QueryFile .\dispatch.dax -Runs 2
```

It prints elapsed ms plus rows x columns per run and dumps the first `-Rows` result rows (default
200; `-Rows 0` to time only), so you can eyeball the result while you time it. `-Port` overrides
discovery, which is needed when two Desktop instances are open. `-AdomdDll` overrides the probe.

`pbir model -q` is an alternative only where the "Enable external tool access to Power BI Desktop
through secure local APIs" preview is turned on. Where it is off, go straight to ADOMD.

### 3. Pin the filter context

**If you do not pin the slicers, you are not measuring what the visual measures.** An unpinned
query usually runs against a wider or emptier filter context and gives a number with no relationship
to the screenshot you are trying to explain.

```dax
EVALUATE
CALCULATETABLE (
    SUMMARIZECOLUMNS (
        ROLLUPADDISSUBTOTAL ( 'Dim Business Unit'[Business Unit], "IsSubtotal" ),
        'Statement Rows'[Order],
        'Statement Rows'[Items],
        "Amount",     [Row Amount],
        "Comparison", [Row Comparison]
    ),
    'Calendar'[Fiscal Year]   = 2025,
    'Period Basis'[Basis]     = "FY",
    'Comparison Basis'[Basis] = "PY",
    'Measure Set'[Selection]  = "All Measures"
)
```

Substitute the user's own slicers. Every slicer that is set on the page belongs in the query, and
every slicer that is clear must stay clear.

This is not a theoretical risk. A pair of headline figures on the reference model, **9,133 ms /
370 ms**, was retracted because it was measured with a month slicer still selected, so the matrix
was rendering one month instead of twelve. Cloned-per-page slicers rather than synced ones make
that an easy mistake and a silent one. Verify the selection per page, immediately before each run.

**If the engine rejects `SUMMARIZECOLUMNS` inside `CALCULATETABLE`** (older builds refuse it), pass
the filters as filter-table arguments to `SUMMARIZECOLUMNS` instead, which is what **Copy query**
already emits. Same context, different syntax.

### 4. Keep the totals in the query

**Totals are part of what you are timing.** The matrix shows subtotals, so the query needs
`ROLLUPADDISSUBTOTAL` on the grouped column, and a flat comparison query needs its `ALLSELECTED`
total measures. Drop either and you have timed a different visual.

Measured on the diagnosed matrix's model, deliberately making that mistake: the same flat query with
its 36 `ALLSELECTED` total columns removed went from **1,580 ms cold / 1,500 ms warm** to **819 ms
cold / 838 ms warm**. Half the columns, roughly half the time, and a number that describes nothing
on screen. Nothing measured here separates the cost of `ROLLUPADDISSUBTOTAL` itself from the cost of
the total measures.

### 5. Run it at least twice

Run one is cold, run two is warm. Both numbers matter, and mixing them across a subtraction is the
main way these readings go wrong. See
[Warm vs cold](#warm-vs-cold-is-a-supporting-signal-not-a-gate).

## The two subtractions

### Subtraction 1: dispatch overhead

**Dispatch overhead = dispatch query - flat query, under the same pinned filters, at the same
thermal state.** The flat query is the measure floor: no visual technique goes below it. Write it
over the same base measures the dispatch measure already dispatches to, so nothing new has to be
authored to get the number. `examples/flat-query.dax` is the shape.

Two measured outcomes, and they land in opposite places:

- **Diagnosed matrix, warm:** 1,997 ms dispatch minus 1,500 ms flat = roughly **500 ms of dispatch
  sitting on a 1,500 ms measure floor**. The dispatch overhead is real, but it is a quarter of the
  query. The measures dominate, so a structural fix alone would not have made that visual fast.
- **Reference model, warm:** the `SWITCH` build ran **2,298-2,335 ms** and the bridge build, same
  measures with dispatch removed, ran **15 ms**. There, dispatch was essentially the entire cost.

Same subtraction, same procedure, opposite verdicts. This is why you run it rather than assume.

### Subtraction 2: per-cell tax

**Per-cell tax = Performance Analyzer total - DAX-only time for the same query.**

It is only reportable when both readings come from the same pinned context and the same thermal
state. Performance Analyzer does not tell you which cache state it caught, so if its total falls
*between* your cold and warm query numbers, a clean subtraction is not available. Read the three
numbers as an ordering instead.

**A clean reading, measured on the reference model.** The calculation-group matrix and its query,
both cold, both with the same single year pinned:

| | Slow matrix | Rebuilt grid | Ratio |
|---|---|---|---|
| Performance Analyzer, whole visual, cold | **12,412 ms** | **332 ms** | 37.4x |
| Performance Analyzer, whole visual, warm | **11,823 ms** | **170 ms** | 69.5x |
| DAX query, cold | 2,178 ms | 124 ms | 17.6x |
| DAX query, warm | 1,228 ms | 17 ms | 72.2x |

Read the first and third rows together. The visual is 12,412 ms; the query behind it is 2,178 ms.
The missing **10,234 ms** is not in the query and never will be, because an `EVALUATE` does not
evaluate a `formatStringDefinition`. That gap is cost (b): 315 cells each re-running their own
measure to choose a format string, plus the render. **82% of what the user waits for is somewhere a
DAX profile cannot show you.** Optimise only what the query profile shows and you would tune
2,178 ms while 10,234 ms sat where you were not looking.

The rebuilt grid's own gap is the honest comparison in the other direction: 332 ms visual against a
124 ms cold query, so roughly 208 ms of render for the same cell count. That is what a visual costs
when it pays the render and nothing else.

**A contaminated reading, for contrast.** On the diagnosed matrix: 3,861 ms Performance Analyzer
total, against 4,493 ms cold / 1,997 ms warm for a dispatch query of the same shape. The 3,861 ms
sits *between* the two query readings, so the subtraction is not available. Worse, the cold DAX
number exceeds the whole visual total, which means either Performance Analyzer was not running cold
or the hand-written query is not the query the visual sent: that second possibility was never
eliminated, because the measurement used a hand-written `CALCULATETABLE` rather than **Copy query**
verbatim. A subtraction against the warm number gives 1,864 ms, but that is arithmetic on two
numbers of unknown comparability, not a measurement.

The fix for a contaminated reading is not a caveat, it is another run: **Copy query** verbatim,
cache cleared, cold against cold.

## The scan-count heuristic

Predict before you measure. Query cost tracks **the number of independent fact-table scans the plan
must contain**:

- A measure column costs **one scan**. Wide is cheap and roughly linear.
- An expression-dispatched row axis costs **the whole branch set at once**, whatever any single cell
  needs. Cost tracks branches and the measure pyramid beneath them.
- A **grouped column** (a real column with a relationship, grouped on rows) collapses to **one
  scan**, because the group-by is pushed into the storage engine instead of being reconstructed by
  the formula engine.

Measured on the diagnosed matrix's model. Same model, same pinned filter context, same day:

| Query shape | Measure columns | Cold | Warm |
|---|---|---|---|
| `SWITCH` dispatch, 99 rows x 6 columns | 2 dispatch measures over 40 base measures | 4,493 ms | 1,997 ms |
| Flat base measures, 3 rows x 73 columns | 72 | 1,580 ms | 1,500 ms |
| Same, no `ALLSELECTED` total columns | 36 | 819 ms | 838 ms |
| Only the 7 additive base measures | 7 | 192 ms | 61 ms |

Read down that table: **the flat query returns 72 measure columns faster than the dispatch query
returns 2.** Halving the columns (72 to 36) roughly halves the time, which is the linear-in-scans
behaviour. The dispatch query is not doing more aggregation, it is planning more.

Use the heuristic to rank shapes, not to predict a number. It gets the ordering right and says
nothing about the size of the gap, which varies by an order of magnitude between models: 4,493
against 1,580 ms cold above, but on the reference model fourteen 27-branch `SWITCH(TRUE(), ...)`
columns over a ~184-measure pyramid ran **2,757 ms cold / 2,298-2,335 ms warm** against **130 ms
cold / 15 ms warm** for the same result from a grouped column on a physical bridge table. That is
21x cold and roughly 150x warm, tied out at 27 rows x 14 columns with zero mismatches.

## Warm vs cold is a supporting signal, not a gate

Read the *shape* of the pair, not either number alone:

- **Warm close to cold** means formula-engine bound. There is nothing to cache because the cost is
  plan construction and per-row evaluation, not scanning. The 72-column flat query does this
  (1,580 / 1,500 ms), as does the 36-column one (819 / 838 ms, warm marginally slower than cold,
  which is noise-level identical). It held on the slow side of the reference model too: 2,757 ms
  cold / 2,298-2,335 ms warm.
- **Warm much faster than cold** means the scans are a real part of the cost and caching them helps.
  The 7 additive base measures do this: 192 ms cold / 61 ms warm.

**The trap is reading the second bullet as "therefore not dispatch".** The diagnosed matrix's
dispatch query is 4,493 ms cold / 1,997 ms warm, 2.25x faster warm, which reads as storage-bound,
and it still carries roughly 500 ms of dispatch on top of the flat query. When the base measures
under a `SWITCH` have real scan work of their own, that part caches and the query warms up while the
dispatch overhead stays exactly where it was.

**Warm close to cold confirms dispatch. Warm far below cold does not rule it out. Only the flat
comparison settles it.**

## The data-volume control test

One more signal, when you can get it: **does the query track data volume?** Halve or double the date
filter and re-time. If the time barely moves, you are paying for the plan, not the data.

Measured on the reference model: 22.4M rows gave **2,963 ms** and 50.3M rows gave **3,473 ms**.
2.2x the data cost 17% more time. (Single runs, no warm/cold pair on either.)

If a matrix behaves like that, a bigger capacity or a trimmed fact table will not save it. The plan
will. Conversely, a matrix whose time scales with the fact table is not a dispatch problem and this
skill is the wrong tool: tune the measures.

## Symptom -> cost -> what to do

| Symptom | Likely cost | Go to |
|---|---|---|
| PA total close to DAX time; the dispatch query costs much more than a flat query of the same base measures; DAX time scales with branches, not with fact rows | (a) row dispatch | [bridge-method.md](bridge-method.md) |
| Rows or columns come from a **calculation group** rather than a `SWITCH` | (a) row dispatch, same mechanism | [measured-results.md](measured-results.md), then [deneb-grid-template.md](deneb-grid-template.md) |
| PA total much larger than DAX time; the value measure appears inside its own `formatStringDefinition` | (b) format string | [per-cell-tax.md](per-cell-tax.md) |
| PA total much larger than DAX time; several colour measures bound to the visual's conditional formatting | (c) CF measures | [per-cell-tax.md](per-cell-tax.md) |
| Both (a) and (b)/(c), and the layout is a fixed grid you control | all three at once | [deneb-grid-template.md](deneb-grid-template.md) |
| The flat base-measure query is already most of the dispatch query | **the measures are the floor** | see below |

Rows 1 and 6 are not exclusive. The diagnosed matrix is both at once: roughly 500 ms of warm
dispatch overhead on a 1,500 ms warm measure floor, which is why a structural fix on its own would
not have carried it.

## When the measures are the floor

No visual technique goes below the cost of the measures themselves. On the diagnosed matrix's model,
the 7 additive base measures alone cost **192 ms cold / 61 ms warm**. Nothing done to the matrix,
the format strings, or the rendering layer gets the visual under that.

**If the flat base-measure timing is already most of the target, stop optimising the visual.**
Optimise the measures, or reduce how many of them are on screen. Say so plainly rather than
rebuilding a grid for a gain that is not there.

For contrast, the ceiling of what the visual layer can give back, measured on the reference model:
a 27-line statement rebuilt as a client-side grid returned 27 rows x 6 base measures from the
engine, derived 8 more columns in the spec, rendered 378 cells, and queried in **14 ms warm**,
against roughly 2,300 ms warm for the identical native `SWITCH` matrix. A second grid in the same
model, 30 rows and 182 cells, queried in **27 ms**. That is what moving dispatch and per-cell work
out of the engine buys. The base measures are still the floor underneath it.

## Traps while iterating

- **Desktop holds its own in-memory copy of the model**, so TMDL edits on disk are not visible to a
  query until the project is reloaded. Validate a rewritten measure in the query itself with
  `DEFINE MEASURE '<Table>'[X new] = ...` and select old and new side by side in one `ROW()`. That
  proves the fix against real data with zero risk to the model.
- **Defensive error handling inside a dispatch measure is not free.** On the reference model,
  wrapping every `SWITCH` branch in `IFERROR` took the slow side from **2,757 ms to 5,997 ms cold**:
  another node per branch, in a plan that already contains every branch.
- **Re-verify the slicer selection before every run.** It is the single cheapest check here and the
  one that invalidated a published pair of numbers.
