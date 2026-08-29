# The per-cell tax: dynamic format strings and conditional-formatting measures

Three costs sit inside a slow matrix: the query the engine runs, the per-cell work the visual does
on top of it, and the render. This reference covers the second: work that happens once per rendered
cell and that a DAX benchmark structurally cannot see.

## The mechanism

An ADOMD / `EVALUATE` run returns raw values. It never evaluates `formatStringDefinition`.
Formatting is a client-side concern of the presentation layer, and a bare query has no presentation
layer.

A visual does evaluate it, **once per rendered cell**. So the same measure, over the same filter
context, costs one thing in the harness and another thing on the canvas, and every timing you take
with `run_dax.ps1` reports the innocent number.

### The self-reference multiplier

The expensive shape is a format string that reads the measure it formats:

```dax
VAR _VALUE = ABS ( [Row Amount] )
RETURN
    SWITCH (
        TRUE (),
        _VALUE >= 1E7, "#,0,,\M",
        _VALUE >= 1E4, "#,0,\K",
        "#,0"
    )
```

The cell evaluates `[Row Amount]` to get its value, then the format string evaluates `[Row Amount]`
again to decide how to print it. **Two evaluations per cell instead of one**, and the second is
invisible in any query plan captured with `EVALUATE`. If `[Row Amount]` is itself a `SWITCH`
dispatch over a pile of base measures, that whole dispatch is paid twice per cell.

The geometry sets the multiplier: `rows x column groups x value slots`. On the diagnosed matrix that
is 26 rows x 4 column groups x 2 slots = 208 cell positions, of which 168 carry a measure. Each one
runs the value measure, the format string (which re-runs the value measure), and up to four colour
measures.

### Conditional formatting is the same shape

A conditional-formatting colour bound to a measure is a per-cell measure evaluation under a
different name. Background colour is one evaluation, font colour is another. Each is independent of
the value evaluation and of the format string, and each runs for every cell in scope of its rule.
The diagnosed matrix binds four colour measures, so the worst cell pays value + format (value again)
+ four colours.

Mechanism, not measurement: the four colour measures were never isolated the way the format string
was. What is measured is the envelope, below.

### The card corollary

This tax is paid per rendered cell, so a card or a slicer-filtered visual showing one value pays it
once. Only grouped rows multiply it. Do not go hunting for it on a visual that renders a handful of
cells.

## How to detect it

**In TMDL, grep for the self-reference.** A measure whose `formatStringDefinition` mentions the
measure's own name in brackets is the shape you want:

```bash
grep -n -A6 "formatStringDefinition" path/to/definition/tables/*.tmdl
```

then read each hit for a `[<same measure name>]` inside it. The canonical tell is a first line of
`VAR _VALUE = ABS ( [X] )` where `[X]` is the measure being formatted.

A cheap model-wide audit, rough by design:

```python
import re, pathlib, sys

root = pathlib.Path(sys.argv[1])          # the .SemanticModel folder
for f in root.rglob("*.tmdl"):
    text = f.read_text(encoding="utf-8")
    for m in re.finditer(r"measure\s+'?([^'\r\n=]+?)'?\s*=", text):
        name = m.group(1).strip()
        block = text[m.end(): m.end() + 4000]
        fsd = block.find("formatStringDefinition")
        if fsd != -1 and f"[{name}]" in block[fsd:fsd + 2000]:
            print(f"{f.name}: [{name}] format string references itself")
```

It scans a fixed window after each measure rather than parsing TMDL blocks, so treat hits as
candidates to read, not as a verdict.

**On the canvas**, the tell is a visual that is materially slower than the query behind it. When
Performance Analyzer is much larger than the DAX time for the same query, suspect this before you
suspect the render layer and long before you start rewriting DAX. A clean DAX profile is not
evidence the visual is cheap; it is evidence you measured the wrong layer.

## How to measure it

**The rough version: Performance Analyzer against the query.** Record the visual in Performance
Analyzer, use **Copy query** to get the exact DAX it sent, run that same query through
`run_dax.ps1`, and compare. Anything Performance Analyzer is paying that the harness is not is
per-cell work plus render.

Rough because you do not control Performance Analyzer's cache state, and the harness's cold/warm
spread can be wider than the tax you are hunting. On the diagnosed matrix the dispatch query alone
spanned 4,493 ms cold to 1,997 ms warm, and the Performance Analyzer total of 3,861 ms sits between
them, so no clean subtraction is available on that reading. **Read the Performance Analyzer number
against both query numbers rather than subtracting from either**, unless both readings come from the
same pinned context in the same thermal state.

**The controlled version: A/B the format string.** Use this when you need an answer you can defend,
with one property changed and everything else held:

1. Duplicate the measure. Give the copy a static `formatString:` and no `formatStringDefinition`.
2. Swap the copy into the visual, changing nothing else.
3. Re-run Performance Analyzer, warm, several times, same slicer state.
4. Swap back.

Do the same for conditional formatting: point the colour slots at a static rule instead of the
measure, re-run, swap back.

### The measured result

Measured 2026-08-24 in the reference lab, on a grid of **182 cells**, warm:

| Cells | Format string | Warm |
|---|---|---|
| 182 | static | 622 ms |
| 182 | dynamic, referencing its own measure | 1,270 ms |

Same measure, same query, same 182 cells, warm both times. The only difference was adding a dynamic
format string that references its own measure. **That is the entire delta**: not render work, not
extra rows, not a cache miss. Roughly a doubling, from one property.

### The envelope on the diagnosed matrix

Measured 2026-08-26 against a live Desktop model over ADOMD, filter context pinned to match the
screenshot:

| What | Cold | Warm | Shape |
|---|---|---|---|
| Performance Analyzer, the matrix as it ships | 3,861 ms | n/a | as rendered |
| Dispatch query (the visual's shape, run bare) | 4,493 ms | 1,997 ms | 99 rows x 6 cols |
| Flat base measures, with `ALLSELECTED` total columns | 1,580 ms | 1,500 ms | 3 rows x 73 cols |
| Same flat query without the `ALLSELECTED` total columns | 819 ms | 838 ms | 36 measure columns |
| Only the 7 additive base measures | 192 ms | 61 ms | n/a |

Inside the flat-query family (same query shape, only the column list changing) the arithmetic is
clean: 838 - 61 = 777 ms warm is plain base-measure cost from the other 29 columns, and
1,500 - 838 = 662 ms is the `ALLSELECTED` totals. Only what sits above 1,500 ms is dispatch and
per-cell work. The dispatch query is a different shape (99 x 6, not 3 x 73), so read that step as an
ordering, not a subtraction.

## The remedy ladder, in order

**1. Static `formatString` where the magnitude range allows it.** The tax goes to zero because there
is nothing to evaluate. You lose auto K/M scaling, so it only works when every cell in the column
lives in the same order of magnitude. On a statement where one column holds both unit counts and
percentages, it does not.

**2. A text measure that pre-formats once.** Return a formatted string from the measure itself
(`FORMAT ( _v, ... )` over a `VAR` you already computed) instead of returning a number and formatting
it after. The cost is still per cell, but the double evaluation disappears: the value is computed
once and the format decision reads the `VAR`, not the measure. This is the specific fix for the
`VAR _VALUE = ABS ( [X] )` shape. Trade-off: the column is text, so no sorting by value, no data
bars, no numeric aggregation in the visual. **Untested**: the mechanism is clear but the delta was
never measured. Do not quote a number for it.

**3. Fewer conditional-formatting slots.** Where the colour is a property of the **row** rather than
of the value (section headers, subtotal rows, a line that is always red), a static rule or a
`fieldValue`-driven colour column beats a measure. Keep measure-driven conditional formatting only
for the slots where the colour genuinely depends on the number. On the diagnosed matrix the four
colour measures split cleanly: two read row attributes and map to a fixed palette without touching
the cell value (candidates for a colour column), two resolve a comparison measure and colour by its
sign (these stay measures).

**4. Move all formatting client-side.** A Deneb grid does zero server-side formatting: the engine
returns raw numbers and the spec formats them in the browser. **This tax goes to zero, not down.**
In the reference lab the classic 27-line statement rebuilt as Deneb returned 27 rows x 6 base
measures, derived 8 more columns in the spec, rendered 378 cells, and queried in **14 ms warm**
against roughly **2,300 ms warm** for the identical native dispatch matrix: roughly **165x**. That
gap is structural (dispatch removal) *plus* the removal of the per-cell tax, and the two are not
separated on that comparison.

## TMDL syntax rules for `formatStringDefinition`

These break Desktop's file open, not just the render.

- **`formatStringDefinition = <dax>` is a CHILD OBJECT, not a property.** It goes *after* the scalar
  properties (`displayFolder`, `lineageTag`), separated by a blank line. Putting it between the
  scalar properties fails the parser.
- **A measure may NOT carry both `formatString:` and `formatStringDefinition`.** Desktop refuses the
  whole project with "not supported scenario". This bites when you add a dynamic format string to a
  measure that already had a static one and forget to remove the old property. It is also the exact
  trap on rung 1 of the ladder: when you go static, delete the definition.
- A one-line expression sits inline after the `=`. A multi-line one is either indented under the `=`
  or wrapped in a triple-backtick block.
- The measure's expression must be indented one level deeper than its properties. Write it at the
  same level and the parser reads `displayFolder:` and everything after it as more DAX: the file
  still reports PARSE OK, the `formatStringDefinition` silently disappears, and the expression is
  quietly corrupt. Do not accept "it parsed" as the check; deserialize the folder and assert the
  round-trip.

```tmdl
	measure 'Row Amount' = ```
			VAR _Amounts =
			    SWITCH ( SELECTEDVALUE ( 'Statement Rows'[Items] ), ... )
			RETURN
			    _Amounts
			```
		displayFolder: Statement\Columns
		lineageTag: <lineage-tag-guid>

		formatStringDefinition = ```
				VAR _VALUE = ABS ( [Row Amount] )
				VAR _Number = SWITCH ( TRUE (), ... )
				RETURN
				    _Number
				```
```

## Two calculation groups: whose format string wins

With two calculation groups in play, the **higher-precedence group's `formatStringDefinition` wins
outright**. `SELECTEDVALUE`-style chaining does not happen: `SELECTEDMEASUREFORMATSTRING()` inside
the higher group returns the **base measure's** format string, not the lower group's, and the lower
group's format strings are never consulted at all.

So the intuitive design ("outer group handles scenario, inner group handles units") silently loses
the inner group's formatting. To vary format by the inner group, put a dynamic format string on the
**base measure** that reads the inner group's column with `SELECTEDVALUE`:

```dax
SWITCH (
    SELECTEDVALUE ( 'Unit Group'[Unit] ),
    "Thousands", "#,0,\K",
    "Millions",  "#,0,,\M",
    "#,0"
)
```

That moves the decision to a place both groups can see, at the cost of one more dynamic format
string: back into the per-cell tax this reference is about. Prefer it only when the units really must
vary.

## Do not

**Do not blanket-wrap dispatch branches in `IFERROR`.** In the reference lab, wrapping every branch
of fourteen 27-branch `SWITCH ( TRUE (), ... )` measures in `IFERROR` took the slow side from
**2,757 ms to 5,997 ms cold**. It more than doubled the cost and fixed nothing. If a branch can
error, fix the branch.

**Do not trust a clean `pbir validate` or a clean DAX profile as evidence the visual is fast.**
Neither one looks at formatting. The canvas is the referee.
