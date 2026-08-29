# Diagnosing a slow P&L matrix

A dynamic financial matrix is slow for up to three independent reasons, and they have three
different fixes. Work out which one you are paying before you change anything: the structural
fix in [the bridge method](02-bridge-method.md) does nothing for a format-string problem, and
killing format strings does nothing for a dispatch problem.

The diagnostic is two subtractions. **Performance Analyzer total minus the DAX-only time for the
same query** leaves the per-cell tax. **The dispatch query minus a flat query over the same base
measures** leaves the dispatch overhead, and what is left underneath is the measure floor.
Everything below is how to get those numbers honestly and what to do with the answer.

## The three costs

| Cost | Paid per | Visible to `EVALUATE`? | Fix |
|---|---|---|---|
| (a) Row dispatch | query plan | yes | [02-bridge-method.md](02-bridge-method.md) |
| (b) Format strings | rendered cell | **no** | [03-format-string-and-cf-tax.md](03-format-string-and-cf-tax.md) |
| (c) Conditional-formatting measures | rendered cell, per colour slot | **no** | [03-format-string-and-cf-tax.md](03-format-string-and-cf-tax.md) |

(b) and (c) are invisible to every DAX benchmark you will run. That is why the subtraction, not
the query timing, is the diagnostic.

## Cost (a): row dispatch

The shape: a disconnected table holds one row per statement line, sits on the matrix rows, and one
measure decides what each row means.

```dax
Row Amount =
SWITCH ( SELECTEDVALUE ( 'Statement Rows'[Items] ),
    "Volume",       [Volume Main],
    "Sales",        [Sales Main],
    "Net Sales",    [Net Sales Main],
    -- ...one branch per statement line...
)
```

The mechanism is not data volume and it is not the branches being slow. **One query plan is built
for the whole group, not one per cell.** When the switch column is grouped on rows, which is
exactly what a matrix does, `SUMMARIZECOLUMNS('Statement Rows'[Items], ...)`: the engine must
compile a single plan capable of producing *every* row of that group. Every branch is therefore
reachable, so every branch, every measure under it, and every measure under *those* gets
materialised into the plan. Branch pruning cannot fire, by construction. Each cell then needs
exactly one branch out of the plan it just paid to build.

Marco Russo and Alberto Ferrari document the same failure from the other side in
[Understanding the optimization of SWITCH](https://www.sqlbi.com/articles/understanding-the-optimization-of-switch/):
`SWITCH` optimises *only* when the switch column is directly filtered in the filter context, and
when it is not, the engine "prepares for the execution of all the branches, even though many of
them will never provide a result to the report". Their worked example goes from a 40-row physical
query plan to 190.

### The same cost, wearing a calculation group

`SWITCH(SELECTEDVALUE(...))` is the form the lab was built on, but the mechanism is about the
query plan, not the syntax. **A calculation group on a matrix axis is row dispatch.** Its items
are grouped on that axis exactly as a disconnected switch column would be, so the engine compiles
one plan capable of producing every item for every measure on the other axis, and the cost is
`items x measures`.

It is arguably worse than a `SWITCH`, because a calculation item usually rewrites the filter
context (`CALCULATE ( SELECTEDMEASURE (), ALLEXCEPT ( ... ), ... )`) rather than just selecting a
different measure. Twelve period items that differ only in a literal are still twelve different
filter contexts to the plan, so the engine cannot collapse them into the single `GROUP BY` scan
that the same data would need if the period were simply a column on the axis.

Worked example, measured: [05-case-unrenderable-matrix.md](05-case-unrenderable-matrix.md): 15 items x 28
measures = 420 dispatched evaluations, 10,984 ms in Performance Analyzer, 406 ms after.

Two consequences worth knowing before you measure:

- **This is a formula-engine cost, so it barely tracks row count.** In the PL Bridge Demo lab,
  22.4M rows → 2,963 ms and 50.3M rows → 3,473 ms: 2.2x the data cost 17% more time. If your
  matrix scales with branches rather than with the fact table, you are here.
- **A card is not affected.** When a slicer filters the switch column to one value instead of
  grouping it, pruning fires and there is nothing to win. Only the grouped-rows case is broken.

## Cost (b): per-cell format strings

A `formatStringDefinition` is evaluated **once per rendered cell**. If it references its own
measure, that measure is evaluated a second time per cell.

The field report's `[Row Amount]` measure does exactly this: its format string opens with:

```dax
VAR _VALUE = ABS ( [Row Amount] )
```

so every cell pays for the dispatch measure twice: once for the value, once to decide how to print
it. On a plan where the dispatch itself is the expensive part, that is close to a doubling of the
visual's DAX work, and no DAX query will ever show it to you: ADOMD returns raw values and never
evaluates `formatStringDefinition`.

Measured directly in the PL Bridge Demo, on a 182-cell Deneb grid: the *visual* went from
**622 ms to 1,270 ms warm** purely from adding a dynamic format string that references its own
measure. Those are visual timings, not query timings: the query behind that grid is 27 ms, so
the 648 ms difference is all per-cell work. Detail and the fixes are in
[03-format-string-and-cf-tax.md](03-format-string-and-cf-tax.md).

## Cost (c): per-cell conditional formatting measures

Same shape, different hook. Each conditional-formatting slot on the visual runs its colour measure
once per cell. Four of them on the diagnosed matrix:

- `[Row Highlight]`
- `[Row Highlight Text]`
- `[Colour Main]`
- `[Colour Rates]`

Count the cells before you dismiss this. That matrix has 26 rows from `Statement Rows` (18
distinct metrics; 5 are section-header rows with no measure; 3 metrics appear twice) x 4 column
groups (three business units plus Total) x 2 slots (Amount, Var LY). That is 26 x 4 x 2 = 208 cell positions,
of which 21 x 4 x 2 = 168 carry a measure, each one running the value measure, the format string
(which re-runs the value measure), and up to four colour measures. The arithmetic here is mine,
from the shape above; the per-cell timing was not measured on this visual.

## The scan-count heuristic

Predict before you measure. Query cost tracks **the number of independent fact-table scans the plan
must contain**:

- A measure column costs **one scan**. Wide is cheap and roughly linear.
- An expression-dispatched row axis costs **the whole branch set at once**, whatever any single
  cell needs. The plan must cover every row of the group, so every branch and every measure
  underneath it is materialised. Cost tracks branches and the measure pyramid beneath them.
- A **grouped** column (a real column with a relationship, grouped on rows) collapses to **one
  scan**, because the group-by is pushed into the storage engine instead of being reconstructed by
  the formula engine.

The field numbers rank in that order. Same model, same pinned filter context, same day:

| Query shape | Measure columns | Cold | Warm |
|---|---|---|---|
| SWITCH dispatch, 99 rows x 6 columns | 2 dispatch measures over 40 base measures | 4,493 ms | 1,997 ms |
| Flat base measures, 3 rows x 73 columns | 72 | 1,580 ms | 1,500 ms |
| Same, no ALLSELECTED total columns | 36 | 819 ms | 838 ms |
| Only the 7 additive Main measures | 7 | 192 ms | 61 ms |

Read down that table: **the flat query returns 72 measure columns faster than the dispatch query
returns 2.** Halving the columns (72 → 36) roughly halves the time (1,580 → 819 ms cold), which is
the linear-in-scans behaviour. The dispatch query is not doing more aggregation: it is planning
more. Use the heuristic to rank shapes, not to predict a number: it gets the ordering right and
says nothing about the size of the gap (here, 4,493 against 1,580 ms cold).

The 36 measures in the flat query are the pre-existing `[<metric> Main]` /
`[<metric> Compare]` pairs for the 18 metrics on the matrix rows, all of which the `SWITCH`
in `[Row Amount]` and `[Row Comparison]` already dispatches to. Nothing new was written to get
the flat number.

The two dispatch measures between them name **40** base measures : `[Row Amount]` has 25
branches (20 `Main` measures plus five section-header branches returning literal `0`) and
`[Row Comparison]` has 20 `Compare` branches, so on the thesis above, the plan the dispatch
query builds covers a wider measure set than the flat query it loses to.

> The ALLSELECTED totals used above were checked against the matrix's own subtotal row values by
> running both queries and diffing the results: all 36 columns, 0 mismatches. Every figure in this
> document comes from a Performance Analyzer reading or a DAX query: none of them depends on a
> rebuilt visual, and you can reproduce all of them against the report as it stands.

The same heuristic across a much bigger gap, from the PL Bridge Demo lab: fourteen 27-branch
`SWITCH(TRUE(), ...)` columns over a ~184-measure pyramid ran **2,757 ms cold / 2,298-2,335 ms
warm**; the identical result from a physical bridge table plus a bidirectional relationship: a
grouped column, one scan: ran **130 ms cold / 15 ms warm**. 21x cold, ~150x warm, tie-out 27 rows
x 14 columns with zero mismatches.

## How to measure

Nothing below needs anything installed beyond Power BI Desktop and a .NET Framework build of the
ADOMD client DLL, which several tools already ship (you do not have to open any of them).

### 1. Performance Analyzer gives you the visual total

View → Performance Analyzer → Start recording → refresh the page. Take the visual's total: DAX plus
render plus format strings plus conditional formatting. On the diagnosed matrix as it
ships, that is **3,861 ms**.

Use **Copy query** on that row. It hands you the exact DAX the visual sends, filter tables and all:
the cheapest way to get the filter context right.

### 2. An ADOMD `EVALUATE` of the same shape gives you the DAX-only number

Find the port. `msmdsrv.exe` is Desktop's local Analysis Services instance:

```powershell
$pids = (Get-Process msmdsrv).Id
Get-NetTCPConnection -State Listen |
    Where-Object { $pids -contains $_.OwningProcess } |
    Select-Object OwningProcess, LocalPort
```

Use `Get-NetTCPConnection`, not `netstat`: it avoids the duplicate IPv4/IPv6 rows.

Load ADOMD. What matters is that the DLL is a **.NET Framework** build; Windows PowerShell 5.1
cannot load a .NET 8 one. Several tools ship a copy, so point `-Path` at whichever one your machine
has. DAX Studio is a convenient example, and you do not have to open it:

```powershell
Add-Type -Path "C:\Program Files\DAX Studio\bin\Microsoft.AnalysisServices.AdomdClient.dll"
```

Pick a .NET 8 copy instead (Tabular Editor 3 ships one) and `Add-Type` throws
`ReflectionTypeLoadException` ("Unable to load one or more of the requested types") under Windows
PowerShell 5.1. That error means the wrong build, not a missing ADOMD. `pbir model -q` is an
alternative only where the "Enable external tool access to Power BI Desktop through secure local
APIs" preview is turned on; where it is off, go straight to ADOMD.

The bundled harness does the connect/time/print loop for you. Save the query to a `.dax` file:
the pinned one below, or the text **Copy query** gave you, and point the script at it:

```powershell
.\tools\run_dax.ps1 -QueryFile .\dispatch.dax -Runs 2
```

It discovers the port itself (`-Port` overrides, needed when two Desktop instances are open),
prints elapsed ms plus rows x columns per run, and dumps the first `-Rows` result rows (default
200; `-Rows 0` to time only) so you can eyeball the result while you time it.

### 3. Subtract

**Per-cell tax = Performance Analyzer total − DAX-only time for the same query.**

For the diagnosed matrix: 3,861 ms total against 4,493 ms cold / 1,997 ms warm for a dispatch query
of the same shape. The cold DAX number is *larger* than the whole visual total, which means one of
two things: Performance Analyzer was not running cold, or the hand-written query is not the query
the visual sent. Either way the cold figure is the wrong one to subtract, so compare against warm:
3,861 − 1,997 = 1,864 ms unaccounted for by DAX.

Two caveats on that 1,864 ms. It is arithmetic on two measured numbers, not a measured number
itself. And the measurement used a hand-written `CALCULATETABLE` query rather than **Copy query**
verbatim, so the second possibility above was never eliminated: some of the residue may be
query mismatch rather than per-cell tax. Nothing here separates render from the format string
from the four colour measures. Time **Copy query** verbatim if you want the residue to mean only
one thing. Either way the residue is where the per-cell costs live, and it is the reason
[03-format-string-and-cf-tax.md](03-format-string-and-cf-tax.md) exists.

If the residue is small, you have a dispatch problem and only a dispatch problem. If the residue is
comparable to the DAX time, no amount of DAX tuning will halve the visual.

## Pinning the filter context

If you do not pin the slicers, you are not measuring what the visual measures. An unpinned query
usually runs against a wider or emptier filter context and gives you a number with no relationship
to the screenshot you are trying to explain.

The field measurement pinned exactly this context, matching the screenshot:

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
    Calendar[Fiscal Year]            = 2025,
    'Dim Period'[Main]               = "FY",
    'Dim Comparison'[Comparison]     = "PY",
    'Param - Measure Set'[Selection] = "All Measures"
)
```

That returned 99 rows x 6 columns at 4,493 ms cold / 1,997 ms warm. The flat comparison used the
same four pinned filters, grouped by `'Dim Business Unit'[Business Unit]` only, and returned the 18
metrics x {Main, Compare, ALLSELECTED-total Main, ALLSELECTED-total Compare} = 72 measure columns as
3 rows x 73 columns.

Two things that bite:

- **Totals are part of what you are timing.** The matrix shows subtotals, so the query needs
  `ROLLUPADDISSUBTOTAL` on the grouped column; the flat shape needs its `ALLSELECTED` total
  measures. Drop either and you have timed a different visual: the 819 ms / 838 ms row above is
  exactly that mistake made deliberately, the same flat query with the 36 `ALLSELECTED` total
  columns removed, half the columns and roughly half the time. Nothing measured here separates
  the cost of `ROLLUPADDISSUBTOTAL` itself from the cost of the total measures.
- **If the engine rejects `SUMMARIZECOLUMNS` inside `CALCULATETABLE`** (older builds refuse it),
  pass the filters as filter-table arguments to `SUMMARIZECOLUMNS` instead, which is what
  Performance Analyzer's **Copy query** already emits. Same context, different syntax.

## The test that decides: dispatch query against flat query

Warm-vs-cold is the signal everyone reaches for first, and on its own it will mislead you. The
decisive test is the one the table above already runs: **time the dispatch query, then time a
flat query over the same base measures under the same pinned filters, and subtract**:

- **Dispatch overhead** = dispatch query − flat query. This is what removing dispatch can win.
- **Measure floor** = the flat query. No visual technique goes below it.

On the diagnosed matrix, warm: 1,997 − 1,500 = roughly 500 ms of dispatch sitting on a 1,500 ms
measure floor. The dispatch overhead is real, but it is a quarter of the query: the measures
dominate, so a structural fix alone would not have made that visual fast. In the PL Bridge Demo
lab the same subtraction lands the other way: the `SWITCH` build ran 2,298-2,335 ms warm and the
bridge build (same measures, dispatch removed) ran 15 ms warm, so there dispatch was essentially
the entire cost.

### Warm vs cold is a supporting signal, not a gate

Run at least twice. Run one is cold, run two is warm. Then read the *shape*:

- **Warm ≈ cold** → formula-engine bound. There is nothing to cache because the cost is plan
  construction and per-row evaluation, not scanning. The flat 72-column query does this
  (**1,580 ms / 1,500 ms**), as does the 36-column one (**819 ms / 838 ms**: warm slightly slower
  than cold, i.e. noise-level identical). It held on the slow side of the PL Bridge Demo lab too:
  **2,757 ms cold / 2,298-2,335 ms warm**.
- **Warm much faster than cold** → the scans are a real part of the cost and caching them helps.
  The 7 additive Main measures on the field model do this: **192 ms cold / 61 ms warm**.

The trap is reading the second bullet as *therefore not dispatch*. The field dispatch query is
4,493 ms cold / 1,997 ms warm (2.25x faster warm, which reads as storage-bound) and it still
carries ~500 ms of dispatch on top of the flat query. When the base measures under a `SWITCH`
have real scan work of their own, that part caches and the query warms up while the dispatch
overhead stays exactly where it was. Warm ≈ cold confirms dispatch; warm ≪ cold does not rule it
out. Only the flat comparison settles it.

One more signal, when you can get it: **does the query track data volume?** In the PL Bridge Demo
lab, 22.4M rows → 2,963 ms and 50.3M rows → 3,473 ms (single runs, no warm/cold pair on either):
2.2x the data cost 17% more time. If your matrix behaves like that, adding a bigger capacity or
trimming the fact table will not save you; the plan will.

One trap while iterating: Desktop holds its own in-memory copy of the model, so TMDL edits on disk
are not visible to a query until close-and-reopen. Validate a rewritten measure in the query itself
with `DEFINE MEASURE '<Table>'[X new] = ...` and select old and new side by side in one `ROW()`:
that proves the fix against real data with zero risk to the model.

And one side-finding worth not rediscovering: in the PL Bridge Demo lab, wrapping every `SWITCH`
branch in `IFERROR` took the slow side from **2,757 ms to 5,997 ms cold**. Defensive error handling
inside a dispatch measure is not free: it is another node per branch in a plan that already
contains every branch.

## Symptom → cost → next doc

| Symptom | Likely cost | Read next |
|---|---|---|
| PA total ≈ DAX time; the dispatch query costs much more than a flat query of the same base measures; DAX time scales with branches, not with fact rows | (a) row dispatch | [02-bridge-method.md](02-bridge-method.md) |
| Rows or columns come from a **calculation group** rather than a `SWITCH` | (a) row dispatch, same mechanism | [05-case-unrenderable-matrix.md](05-case-unrenderable-matrix.md), then [04-deneb-grid-template.md](04-deneb-grid-template.md) |
| PA total is much larger than DAX time; the value measure appears inside its own `formatStringDefinition` | (b) format string | [03-format-string-and-cf-tax.md](03-format-string-and-cf-tax.md) |
| PA total is much larger than DAX time; several colour measures bound to the visual's conditional formatting | (c) CF measures | [03-format-string-and-cf-tax.md](03-format-string-and-cf-tax.md) |
| Both (a) and (b)/(c), and the layout is a fixed grid you control | all three at once | [04-deneb-grid-template.md](04-deneb-grid-template.md) |
| The flat base-measure query is already most of the dispatch query | **the measures are the floor** | see below |
| You know the fix and need to edit the real report safely | n/a | [06-pbir-build-playbook.md](06-pbir-build-playbook.md) |

Rows 1 and 6 are not exclusive. The diagnosed matrix is both at once: ~500 ms of warm dispatch
overhead on a 1,500 ms warm measure floor, which is why the structural fix on its own would not
have carried it.

### When the measures are the floor

No visual technique goes below the cost of the measures themselves. On the field model, the 7
additive Main measures (Volume, Sales, Net Sales, Gross Margin, Contribution, Discounts, Marketing) alone cost **192 ms cold
/ 61 ms warm**. Nothing you do to the matrix, the format strings, or the rendering layer gets the
visual under that. If your flat base-measure timing is already most of your target, stop optimising
the visual and go optimise the measures, or reduce how many of them are on screen.

The upper bound on what the visual layer can give back, for contrast: in the PL Bridge Demo the
classic 27-line statement rebuilt as a Deneb grid returned 27 rows x 6 base measures from the
engine, derived 8 more columns in the spec, rendered 378 cells, and queried in **14 ms warm**:
against ~2,300 ms warm for the identical native `SWITCH` matrix, roughly 165x. A second Deneb
grid in the same lab, the "odd rows" P&L, returned 30 rows, rendered 182 cells, and queried in
**27 ms**: the grid whose format-string tax is quoted above. That is the ceiling
of moving dispatch and per-cell work out of the engine; the base measures are still the floor
underneath it.

## Source material

- [02-bridge-method.md](02-bridge-method.md): the same mechanism, plus the original 50.3M-row
  lab timings (SWITCH 4,939 ms cold / 4,619 ms warm against bridge 546 ms / 353 ms over 21
  statement rows x 6 columns; 9x cold, 13x warm).
- [Understanding the optimization of SWITCH](https://www.sqlbi.com/articles/understanding-the-optimization-of-switch/)
 : Russo & Ferrari, SQLBI, the load-bearing external reference for cost (a).
