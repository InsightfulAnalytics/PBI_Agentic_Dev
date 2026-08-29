# The bridge method: replacing row dispatch with filtering

The structural fix for cost (a), the per-query cost of a row axis that dispatches to a different
measure per row. It applies when, and only when, the statement's rows can be written as
*"which accounts does this line cover"*. When they can't, skip to
[When it does not apply](#when-it-does-not-apply) and go to the Deneb grid instead.

## The one-sentence idea

Stop asking *"which row am I on, and which measure should I therefore run?"* and start asking
*"which accounts does this row cover?"*: the first question forces the engine to plan every
branch of the statement, the second is just a filter.

## The anti-pattern it replaces

A disconnected table holds one row per statement line and sits on the matrix rows. One measure
decides what each row means:

```dax
Slow Row Value =
SWITCH ( TRUE (),
    SELECTEDVALUE ( 'Legacy Rows'[Line] ) = "Revenue",
        [Scenario Revenue],
    SELECTEDVALUE ( 'Legacy Rows'[Line] ) = "Cost of Sales",
        [Scenario Cost of Sales],
    SELECTEDVALUE ( 'Legacy Rows'[Line] ) = "Gross Profit",
        [Scenario Revenue] + [Scenario Cost of Sales],
    -- ...24 more branches...
)
```

Behind each branch sits a pyramid (`[Scenario Revenue]` to `[Actual Revenue]` to
`[Base Actual Value]` to `SUM ( 'Financials'[Amount] )`), plus a parallel prior-year stack, plus
scenario switches, plus subtotal measures that re-scan the fact once per component.

It is not a stupid pattern. It is *the* pattern, it reads well, and it is what every published
dynamic-P&L walkthrough lands on. It just does not scale with statement size.

## Why dispatch is expensive

Not data volume. A control run at two fact sizes: 22.4M rows cost 2,963 ms and 50.3M rows cost
3,473 ms, so 2.2x the data for 17% more time. That is a formula-engine signature, not a
storage-engine one. Scanning rows is not the expensive part.

The expensive part is that **one query plan is built for the whole group, not one per cell**.
When the switch column is grouped on rows
(`SUMMARIZECOLUMNS ( 'Legacy Rows'[Line], ... )`), the engine compiles a single plan that must be
able to produce every row of that group. Every branch is therefore reachable, so every branch, and
every measure under it, and every measure under those, is materialised into the plan. Branch
pruning cannot fire, by construction.

Russo and Ferrari document the same failure mode from the other side: `SWITCH` optimises *only*
when the switch column is directly filtered in the filter context; otherwise the engine "prepares
for the execution of all the branches, even though many of them will never provide a result to the
report"
([SQLBI, Understanding the optimization of SWITCH](https://www.sqlbi.com/articles/understanding-the-optimization-of-switch/)).

The corollary matters for scoping the fix: this only bites when the switch column is **grouped**.
A card or KPI where a slicer pins the switch column to a single value usually prunes already, so
there is nothing to win there, though SQLBI notes the optimisation still fails if two filters hit
the same column (a page filter plus a slicer, say) or the filter comes from a complex expression.

So the fix is not to tune the branches. The fix is to have no branches.

## The production shape

Build this. Do **not** ship the `DATATABLE` plus `TREATAS` prototype that gets used to demo the
idea in a query window: it duplicates the mapping literal inside every measure, so a data change
has to be re-applied by hand in every one of them.

**One physical table, one row per (statement line, account) pair.** In the reference build it is a
CSV, `LineKey, Line, LineClass, AccountKey, Account`, 75 rows for a 27-line statement. A subtotal
is simply a line with more rows: `Total Income` has 4, `Gross Profit` 9, `Net Profit` 22. No
addition, no branch.

| LineKey | Line | LineClass | AccountKey | Account |
|---|---|---|---|---|
| 10 | `    Product Revenue` | Detail | 1 | Product Revenue |
| 20 | `    Service Revenue` | Detail | 2 | Service Revenue |
| 30 | `Revenue` | Subtotal | 1 | Product Revenue |
| 30 | `Revenue` | Subtotal | 2 | Service Revenue |
| 60 | `Cost of Sales` | Subtotal | 3 | Direct Materials |
| 60 | `Cost of Sales` | Subtotal | 4 | Direct Labour |

The indent above is literal: detail lines carry four U+00A0 non-breaking spaces, not ASCII spaces.
Table and matrix visuals trim leading ASCII spaces from labels, so ASCII indentation renders flush
left.

**One relationship**, many-to-one from the bridge's account key to the account dimension, set to
**both directions**:

```
'Statement Rows'[AccountKey]  ->  'Dim Account'[AccountKey]     (many-to-one, bothDirections)
```

**`'Statement Rows'[Line]` on the visual rows**, with `Sort by column = LineKey`. The filter then
propagates Statement Rows to Dim Account to Financials on its own. There is no dispatch DAX at
all: the row context *is* the account filter.

The measures collapse to a handful of short ones whose only `CALCULATE`s are the scenario
predicate and the time shifts:

```dax
Row Amount =
CALCULATE ( SUM ( 'Financials'[Amount] ), 'Financials'[Scenario] = "Actual" )

Row Amount LY =
CALCULATE ( [Row Amount], DATEADD ( 'Dim Date'[Date], -1, YEAR ) )

Row Amount YTD =
CALCULATE ( [Row Amount], DATESYTD ( 'Dim Date'[Date] ) )
```

Adding a statement line later costs one or more rows in a CSV. It costs no DAX.

A complete drop-in table, relationship and measure is in
[`examples/bridge-table.tmdl`](../examples/bridge-table.tmdl). That example loads the mapping from
an inline `#table` so it runs with no external file; in production load it from a CSV in the repo
instead, because a CSV diffs and a colleague can edit it. Two TMDL notes, both verified against
`TmdlSerializer::DeserializeDatabaseFromFolder`:

- A single document may hold the `table` block and the `relationship` block together and it parses,
  but in a PBIP put the relationship in `definition/relationships.tmdl`, which is where Desktop
  re-serialises it on the next save.
- **A relationship cannot carry a `///` doc comment.** Relationships have no `Description`
  property, so a `///` line above one fails the whole model with
  `Property 'description' is unknown and is not expected in the situation it appears`, naming no
  line number. `//` is not a TMDL line type either (`InvalidLineType: Unexpected line type: Other!`),
  so there is nowhere to put a note next to the relationship. Put it in the commit message.

Two shape constraints worth checking before you commit:

- **Signs.** The pattern assumes costs are stored negative, so every subtotal is a plain sum. If
  the GL stores everything positive, the bridge needs a `Sign` column and the measure becomes
  `SUMX ( bridge rows, Sign * CALCULATE ( ... ) )`, which puts an iteration back. Fix the sign
  upstream in Power Query instead if you possibly can.
- **The join key is a key, not a label.** Match on `AccountKey`, not on the display string. Label
  matching means a renamed row (or a leading-space change) silently blanks that line.

### When you can't put the bridge on the rows

Brownfield reports often have bookmarks, sort orders and other measures already bound to an
existing disconnected switch table. Keep that table on the rows and filter the bridge in DAX
instead: still no branches, one extra `TREATAS`.

```dax
Row Amount Bridged =
VAR __Line = SELECTEDVALUE ( 'Legacy Rows'[Line] )
VAR __Accounts =
    TREATAS (
        SELECTCOLUMNS (
            CALCULATETABLE ( 'Statement Rows', 'Statement Rows'[Line] = __Line ),
            "@a", 'Statement Rows'[AccountKey]
        ),
        'Dim Account'[AccountKey]
    )
RETURN
    CALCULATE ( [Row Amount], __Accounts )
```

`TREATAS` is what gives the extracted column the data lineage of `'Dim Account'[AccountKey]`, so
`CALCULATE` accepts it and the engine pushes it to the storage engine as a real set predicate: one
scan with a `WHERE`, not N measures added together. This variant was not separately timed; the
physical-relationship version is the one that produced the numbers below.

The two tables are matched on the line label here, so their label strings have to agree byte for
byte, non-breaking spaces included.

## Migration recipe

1. **Enumerate the leaf accounts per branch.** Read the `SWITCH` and write down, for each branch,
   the set of leaf accounts it ultimately resolves to. Chase the measure pyramid all the way to
   the `SUM`; expand every subtotal measure into its components. This is the slow, unavoidable
   step and it is where mistakes get made.
2. **Build the mapping table.** One row per (line, account) pair, with a numeric `LineKey` for
   ordering and a `LineClass` (Detail / Subtotal / Header) for formatting. CSV in the repo beats
   `Enter Data`: it diffs, and a colleague can edit it. A per-unit twin of a dollar line (the same
   line expressed as a rate) is *not* a second account set: map both to the same accounts and both
   rows return the same number. The dollar line goes on the bridge; its per-unit twin is a ratio
   and still needs its own measure. See [When it does not apply](#when-it-does-not-apply).
3. **Load it and set the sort.** `'Statement Rows'[Line]` gets `Sort by column = LineKey`, or the
   statement comes out alphabetical.
4. **Create the relationship, many-to-one, bidirectional.** Bridge account key to account
   dimension. Bidirectional is required: the filter has to travel *up* from the bridge into the
   shared account dimension before it can travel down into the fact.
5. **Check the blast radius of that bidirectional relationship. Do not skip this.** See the next
   section.
6. **Write the small measure set.** Base scenario measure, then the time-shifted variants. Nothing
   else.
7. **Tie out with a full grid diff, not spot checks.** See [The tie-out](#the-tie-out). The gate is
   zero mismatches.
8. **Only then repoint the visual.** Keep the old measures in the model until the diff has run
   green on the real slicer states; delete them afterwards so nobody re-binds to them.

Run the timings before and after, cold and warm, so the before/after number is yours and not this
document's.

## Blast radius of the bidirectional relationship

Bidirectional filtering on a *shared* dimension can create ambiguous filter paths. If the account
dimension is reachable from another table by a second route, or another bidirectional relationship
already exists in that neighbourhood, Desktop will either refuse the relationship as ambiguous or,
worse, accept it and change the answer for measures that had nothing to do with the statement.

- Save the model after adding it and read any ambiguity warning literally.
- Re-check other visuals that touch the account dimension. A wrong answer here is silent.
- **RLS is a separate switch.** Cross-filter direction Both does not propagate row-level security
  on its own: that needs `securityFilteringBehavior = BothDirections` ("Apply security filter in
  both directions") on the relationship, which is off by default. Leave it off unless you need it,
  and re-test every role if you turn it on.
- If the model won't take a bidirectional relationship, fall back to the single-direction
  relationship plus the `TREATAS` variant above, or `CROSSFILTER ( ..., BOTH )` scoped inside the
  bridge measures only.

## The tie-out

Put old and new measures in the *same* query, over the *same* grouping, and count mismatches. The
gate is zero. Template: [`examples/tie-out.dax`](../examples/tie-out.dax).

The old measures dispatch on the *old* table's line column, so grouping on the bridge alone leaves
`SELECTEDVALUE` blank and every old value comes back empty: a diff that reports 100% mismatch and
tells you nothing. Drive the grid from the bridge, then push the matching line onto the old table
by hand, and strip the bridge's own filter off the old side so the two are not agreeing by
construction.

The `+ 0` in that template matters: `COUNTROWS` over an empty filter returns `BLANK`, not `0`, so
without it a clean tie-out prints an empty cell and you cannot tell it from a query that never ran.

Repeat the diff under each slicer state that matters, every column of the real statement, and at
least one non-default year / channel / entity selection. A missing (line, account) pair produces a
*smaller* number, not an error, so the diff is the only thing that catches it. Two eyeballed
screenshots are not a tie-out.

## Measured results

Two builds, timed as DAX queries. Only the first was tied out; no grid diff is on record for the
second.

| Build | Implementation | Cold | Warm |
|---|---|---|---|
| 74.9M-row fact, 27 lines x 14 columns | Fourteen 27-branch `SWITCH(TRUE(),...)` over a ~184-measure pyramid | 2,757 ms | 2,298-2,335 ms |
| same | Bridge: physical CSV table + bidirectional relationship | **130 ms** | **15 ms** |
| 50.3M-row fact, 21 rows x 6 columns | 21-branch `SWITCH(TRUE(),...)` | 4,939 ms | 4,619 ms |
| same | Bridge | **546 ms** | **353 ms** |

21x cold and roughly 150x warm on the first; 9x cold and 13x warm on the second, whose bridge floor
sat much higher in absolute terms. The two builds differ in fact size, grid size and measure set at
once, so nothing here isolates why. Tie-out on the first: 27 rows x 14 columns, zero mismatches.

Measured as *visuals* under Performance Analyzer rather than as queries, the same two pages read
**4,815 ms cold / 4,594 ms warm** dispatched against **348 ms cold / 319 ms warm** bridged, a
13.8x cold and 14.4x warm improvement. Both readings are real: the query number is what the engine
costs, the Performance Analyzer number is what the user waits for, and the gap between them is the
per-cell format-string and conditional-formatting tax, which the bridge does not touch.

Note the warm column on the slow side. Warm close to cold is the branch-planning signature: a
second run of a `SWITCH` statement does not get meaningfully cheaper, because the cost is the plan,
not the scan.

**Data-volume control.** Two single runs, one at each fact size. Which build they ran on, and
whether either was cold, is not on record, so read them against each other, not against the table
above:

| Fact rows | Time |
|---|---|
| 22.4M | 2,963 ms |
| 50.3M | 3,473 ms |

2.2x the data cost 17% more time. This is what rules out "it's just a big model" as the
explanation, and it is the cheapest experiment to run on a client model before committing to the
rebuild: double the date filter and see whether the time moves proportionally. If it barely moves,
you are paying for the plan.

## Side-finding: IFERROR on every branch

Wrapping every `SWITCH` branch in `IFERROR ( ..., 0 )`, a very common defensive habit, took the
slow side from **2,757 ms to 5,997 ms cold**. `IFERROR` alone more than doubled it.

It was removed from the shipped comparison as unfair to the `SWITCH` side, but the number is worth
having when arguing against blanket `IFERROR` in a client model. Why it costs that much was not
investigated: only the timing is on record.

## When it does not apply

The bridge needs the rows to *be* a set of accounts. Plenty of real statements do not clear that
bar. The diagnosed matrix is the counter-example: 26 rows drawn from a disconnected row table, of
which 18 are distinct metrics, and those 18 metrics are not accounts. They are unrelated named
quantities: a unit count, a dollar value, a rate per unit, a ratio of two other rows, a percentage
of a parent, an `ALLSELECTED` share of the visual total. No `(line, account)` mapping produces a
ratio of two other rows, because a ratio is not a sum of anything: it is a function of other rows.
Its base measures are the product, not an implementation detail to be replaced.

Concretely, the bridge is unavailable when any of these is true for a meaningful share of rows:

- The row is a **ratio or a rate**: one measure divided by another, not a sum over a key set.
- The row is a **share of a total** computed with `ALLSELECTED`, which is a filter-context
  manipulation and cannot be expressed as membership in an account list.
- The row is a **distinct count** or another non-additive aggregate: a subtotal is then no longer
  "a line with more rows", because the union of two account sets does not distinct-count to the sum
  of their distinct counts.
- The rows are **different grains** (per store, per unit, per transaction) that need a different
  denominator each.

When the rows are not a filterable account set, the bridge is off the table and you go to the
Deneb grid instead. That route keeps the measures exactly as they are and removes the dispatch a
different way: the engine returns a small flat result and the spec lays out the grid, so the visual
never groups on the dispatch column at all.

The two fixes are not exclusive. A mixed statement can put its account-backed lines on a bridge and
its ratio lines on ordinary measures, then render the whole thing through one grid. And neither fix
touches the per-cell format-string and conditional-formatting tax, which is invisible to every DAX
benchmark you will run while doing this.
