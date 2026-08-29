# The per-cell tax: dynamic format strings and conditional-formatting measures

There are three costs in a slow matrix: the query the engine runs, the per-cell work the visual
does on top of it, and the render itself. [01-diagnosing-slow-matrices.md](01-diagnosing-slow-matrices.md)
splits them apart; [02-bridge-method.md](02-bridge-method.md) attacks the first. This doc is about
the second: the work that happens once per rendered cell and that a DAX benchmark structurally
cannot see.

## What the benchmark cannot see

An ADOMD / `EVALUATE` run returns raw values. It never evaluates `formatStringDefinition`.
Formatting is a client-side concern of the presentation layer, and a bare query has no
presentation layer.

A visual does evaluate it: once per rendered cell. So the same measure, over the same filter
context, costs one thing in the harness and another thing on the canvas, and every diagnostic
you run through [tools/run_dax.ps1](tools/run_dax.ps1) reports the innocent number.

Measured directly in the PL Bridge Demo lab on 2026-08-24, on a grid of **182 cells**, warm:

| Cells | Format string | Warm |
|---|---|---|
| 182 | static | 622 ms |
| 182 | dynamic, referencing its own measure | 1,270 ms |

Same measure, same query, same 182 cells, warm both times. The only difference was adding a
dynamic format string that references its own measure. That is the entire delta, not render
work, not extra rows, not a cache miss.

The practical consequence: when a visual is materially slower than the query behind it, suspect
this before you suspect the render layer or start rewriting DAX. A DAX profile that looks clean
is not evidence the visual is cheap; it is evidence you measured the wrong layer.

## The self-reference multiplier

The expensive shape is a format string that reads the measure it formats:

```dax
VAR _VALUE = ABS ( [X] )
RETURN
    SWITCH (
        TRUE (),
        _VALUE >= 1E7, "#,0,,\M",
        _VALUE >= 1E4, "#,0,\K",
        "#,0"
    )
```

The cell evaluates `[X]` to get its value, then the format string evaluates `[X]` again to decide
how to print it. Two evaluations per cell instead of one, and the second one is not visible in any
query plan you capture with `EVALUATE`. If `[X]` is itself a `SWITCH` dispatch over a pile of base
measures, you are paying for that dispatch twice per cell.

This is not hypothetical on the field report. `[Row Amount]`, the measure that fills the Amount
slot of the diagnosed matrix, carries a `formatStringDefinition` whose first line is:

```dax
VAR _VALUE = ABS ( [Row Amount] )
```

`[Row Amount]` is a `SWITCH ( SELECTEDVALUE ( 'Statement Rows'[Items] ), … )` over 20 pre-existing
`[<metric> Main]` base measures, plus five section-header branches that return 0. Its sibling
`[Row Comparison]`, which fills the Var LY slot, dispatches over the 20 matching
`[<metric> Compare]` measures. Every Amount cell dispatches the SWITCH for its value and
dispatches it again for its format.

The matrix geometry sets the multiplier: **26 rows** from `Statement Rows` (18 distinct metrics;
5 are section header rows with no measure, 3 metrics appear twice) × **4 column groups**
(three business units plus Total) × **2 slots** (Amount, Var LY).

## Conditional formatting is the same shape

A conditional-formatting colour bound to a measure is a per-cell measure evaluation with a different
name. Background colour is one evaluation. Font colour is another. Each is independent of the value
evaluation and of the format string, and each runs for every cell in scope of that rule.

The diagnosed matrix binds four colour measures:

- `[Row Highlight]`
- `[Row Highlight Text]`
- `[Colour Main]`
- `[Colour Rates]`

Mechanism, not measurement: I did not isolate the cost of these four the way the 622 → 1,270 ms
test isolated the format string. What is measured is the envelope: see the next section.

## The envelope on the diagnosed matrix

Measured 2026-08-26 against the live Desktop model over ADOMD, filter context pinned to match the
screenshot (`Calendar[Fiscal Year]` = 2025, `'Dim Period'[Main]` = "FY",
`'Dim Comparison'[Comparison]` = "PY", `'Param - Measure Set'[Selection]` = "All Measures"):

| What | Cold | Warm | Shape |
|---|---|---|---|
| Performance Analyzer, the matrix as it ships | 3,861 ms | n/a |: |
| SWITCH-dispatch query (the visual's shape, run bare) | 4,493 ms | 1,997 ms | 99 rows × 6 cols |
| Flat base measures, 18 metrics × {Main, Compare, ALLSELECTED totals} | 1,580 ms | 1,500 ms | 3 rows × 73 cols |
| Same flat query without the ALLSELECTED total columns | 819 ms | 838 ms | 36 measure columns |
| Only the 7 additive Main measures | 192 ms | 61 ms | n/a |

Read the PA number against the two query numbers rather than subtracting from either. 3,861 ms sits
between the 4,493 ms cold and 1,997 ms warm readings, and Performance Analyzer does not tell you
which cache state it caught, so a clean subtraction is not available here.

What the table does establish is that most of the warm cost is *not* removable overhead. Inside the
flat-query family (same query shape, only the column list changing) the arithmetic is clean:
7 additive Main measures cost 61 ms warm, all 36 base-measure columns cost 838 ms, and adding the
36 ALLSELECTED total columns takes it to 1,500 ms. So 838 − 61 = 777 ms warm is plain base-measure
cost from the other 29 columns (11 non-additive Main ratios (per-unit rates and %) plus all 18 Compare
columns), and 1,500 − 838 = 662 ms is the ALLSELECTED totals. Only what sits above 1,500 ms is
dispatch and per-cell work, and the SWITCH-dispatch query is a different shape (99 × 6, not 3 × 73),
so read that step as an ordering, not a subtraction.

(The ALLSELECTED total columns tie out: all 36 values diffed against the matrix's own subtotal row
values gave 0 mismatches: a query-level equivalence check, not a shipped change.)

## Two calculation groups: whose format string wins

With two calculation groups in play, the **higher-precedence** group's `formatStringDefinition`
wins outright. `SELECTEDMEASUREFORMATSTRING()` inside it returns the **base measure's** format
string, not the lower-precedence group's: the lower group's format strings are never consulted at
all. There is no chaining.

So the intuitive design ("outer group handles scenario, inner group handles units") silently loses
the inner group's formatting. To vary format by the inner group, put a dynamic format string on the
**base measure** that reads the inner group's column with `SELECTEDVALUE` (`'Unit Group'` below is a
placeholder, neither project here ships a units group; substitute your own calc-group column):

```dax
SWITCH (
    SELECTEDVALUE ( 'Unit Group'[Unit] ),
    "Thousands", "#,0,\K",
    "Millions",  "#,0,,\M",
    "#,0"
)
```

That moves the decision to a place both groups can see, at the cost of one more dynamic format
string: i.e. back into the per-cell tax this doc is about. Prefer it only when the units really
must vary.

## How to measure the tax

**The rough version: PA against the query.** Run Performance Analyzer on the visual, copy its DAX
query out, run the same query through [tools/run_dax.ps1](tools/run_dax.ps1), and compare. Anything
PA is paying that the harness is not is per-cell work plus render. It is rough because you do not
control PA's cache state and the harness's cold/warm spread can be wide: on the diagnosed matrix the
SWITCH-dispatch query alone spanned 4,493 ms cold to 1,997 ms warm, which is a bigger window than
most taxes you are hunting.

**The controlled version: A/B the format string.** Use this when you need an answer you can
defend, with one property changed and everything else held:

1. Duplicate the measure. Give the copy a static `formatString:` and no `formatStringDefinition`.
2. Swap the copy into the visual, changing nothing else.
3. Re-run Performance Analyzer, warm, several times, same slicer state.
4. Swap back.

Two measures, one visual property, everything else held constant. Do the same for CF: point the
colour slots at a static rule instead of the measure, re-run, swap back.

A cheap audit for self-referencing format strings across a model's TMDL:

```python
import re, pathlib

root = pathlib.Path(r"<client-repo>")
for f in root.rglob("*.tmdl"):
    text = f.read_text(encoding="utf-8")
    for m in re.finditer(r"measure\s+'?([^'\r\n=]+?)'?\s*=", text):
        name = m.group(1).strip()
        block = text[m.end(): m.end() + 4000]
        fsd = block.find("formatStringDefinition")
        if fsd != -1 and f"[{name}]" in block[fsd:fsd + 2000]:
            print(f"{f.name}: [{name}] format string references itself")
```

Rough by design: it scans a fixed window after each measure rather than parsing TMDL blocks, so
treat hits as candidates to read, not as a verdict.

## Remedies, ranked

**1. Static `formatString` where the magnitude range allows it.** Cheapest possible fix: the tax
goes to zero because there is nothing to evaluate. You lose auto K/M scaling, so it only works when
every cell in the column lives in the same order of magnitude. On a P&L where one column holds both
unit counts and percentages, it does not.

**2. A text measure that pre-formats once.** Return a formatted string from the measure itself
(`FORMAT ( _v, … )` over a `VAR` you already computed) instead of returning a number and formatting
it after. The cost is still per cell, but the double evaluation disappears: the value is computed
once and the format decision reads the `VAR`, not the measure. This is the specific fix for the
`VAR _VALUE = ABS([X])` shape. Trade-off: the column is text, so no sorting by value, no data bars,
no numeric aggregation in the visual. Untested here: the mechanism is clear but I have not measured
the delta on either project.

**3. Fewer CF slots.** Where the colour is a property of the **row** rather than of the value
(section headers, subtotal rows, a metric that is always red), a static rule or a
`fieldValue`-driven colour column beats a measure. Keep measure-driven CF only for the slots where
the colour genuinely depends on the number. On the diagnosed matrix the four split cleanly:

- `[Row Highlight]` reads `'Statement Rows'[Highlight]` and
  `[Row Highlight Text]` reads `'Statement Rows'[Items]`, each mapping the
  row to a fixed palette colour without reading the cell's value. Row-dependent: these are the
  candidates for a colour column.
- `[Colour Main]` and `[Colour Rates]` each resolve a Compare
  measure for the selected row and colour by its sign: one resolves the three headline
  Compare measures (a margin rate, a negated spend ratio, a sales rate), the other resolves the
  same three in their rate variants.
  Value-dependent: these stay measures.

**4. Move all formatting client-side.** The Deneb grid template does zero server-side formatting:
the engine returns raw numbers and the spec formats them in the browser. This tax goes to zero, not
down. See [04-deneb-grid-template.md](04-deneb-grid-template.md).

The measured case: in the PL Bridge Demo lab, the classic 27-line statement rebuilt as Deneb returns
27 rows × 6 base measures, the spec derives 8 more columns and renders 378 cells, and the query runs
**14 ms warm** against roughly **2,300 ms warm** for the identical native SWITCH matrix: roughly
**165x**. The "odd rows" P&L page on the same project returns 30 rows, renders 182 cells, and
queries in **27 ms**. That gap is structural (bridge instead of SWITCH dispatch, per
[02-bridge-method.md](02-bridge-method.md)) *plus* the removal of the per-cell tax. The two are not
separated on this comparison: the 622 → 1,270 ms format-string measurement was taken on the
182-cell odd-rows page, not on the 27-row statement.

## Do not

**Do not blanket-wrap branches in `IFERROR`.** In the PL Bridge Demo lab, wrapping every branch of
the fourteen 27-branch `SWITCH(TRUE(),…)` measures in `IFERROR` took the slow side from **2,757 ms**
to **5,997 ms** cold. It more than doubled the cost and fixed nothing. If a branch can error, fix
the branch.

**Do not give a measure both `formatString:` and `formatStringDefinition`.** Desktop refuses the
whole project, "not supported scenario". This bites when you add a dynamic format string to a
measure that already had a static one and forget to remove the old property. In TMDL,
`formatStringDefinition = <dax>` is a child object, not a property: it goes *after* the scalar
properties (`displayFolder`, `lineageTag`), separated by a blank line. A one-line expression sits
inline after the `=`; a multi-line one is either indented under the `=` or wrapped in a
triple-backtick block. Both forms ship in this model : `[Row Amount]` uses backticks:

````tmdl
	measure 'Row Amount' = ```
			VAR __dashboard_amounts =
			    SWITCH ( SELECTEDVALUE ( 'Statement Rows'[Items] ), … )
			RETURN
			    __dashboard_amounts
			```
		displayFolder: Dashboard\Dashboard Columns\Summary
		lineageTag: <lineage-tag-guid>

		formatStringDefinition = ```
				VAR _VALUE = ABS ( [Row Amount] )
				VAR __format_number = SWITCH ( TRUE (), … )
				VAR __category =
				    SWITCH ( SELECTEDVALUE ( 'Statement Rows'[Category] ), "Number", __format_number, … )
				RETURN
				    __category
				```
````

What does fail the parser is putting it between the scalar properties. See
[06-pbir-build-playbook.md](06-pbir-build-playbook.md) for the safe edit mechanics on a live report.

**Do not trust a clean `pbir validate` or a clean DAX profile as evidence the visual is fast.**
Neither one looks at formatting. The canvas is the referee.
