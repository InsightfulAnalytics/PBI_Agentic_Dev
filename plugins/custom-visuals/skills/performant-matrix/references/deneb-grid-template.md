# The Deneb grid template: a financial matrix that costs one query

The build spec for replacing a slow financial matrix with a Deneb grid.

It assumes you already know *which* cost you are paying (row dispatch, per-cell format strings,
per-cell conditional-formatting measures) from `diagnosing.md`. If the answer is "row dispatch
only, and the client will accept a native matrix", the cheaper fix is `bridge-method.md`. Deneb is
what you reach for when you want the row dispatch **and** the per-cell tax to go away at once, and
you are willing to rebuild the grid chrome by hand.

Spec authoring rules (theme colours, escaping, interactivity) live in `custom-visuals:deneb-visuals`.
Extract, embed and offline rendering live in `custom-visuals:deneb-pbir`. This reference is the grid
recipe that sits on top of both.

## The principle

Ask the engine for the **irreducible dataset**: the grouping column, crossed with the base measures,
and nothing else. No derived columns. No formatted strings. No per-cell colour measures. No row
dispatch, because the rows come from a grouped column, so the engine buckets them in one scan
instead of re-entering the formula engine per row.

The spec then does everything else, client-side, on data already in the browser: derives the extra
columns, lays out the grid, formats every number, colours every cell, draws the rules and headers,
and attaches a tooltip to every cell.

Two measured illustrations:

| Grid | Engine returns | Spec renders | Query |
|---|---|---|---|
| Odd-rows P&L page | 30 rows | 182 cells | 27 ms |
| Classic 27-line statement | 27 rows x 6 base measures | 378 cells (8 columns derived in the spec) | 14 ms warm |

The identical native `SWITCH` matrix for that classic statement ran roughly 2,300 ms warm: the spec
version is roughly 165x faster on the same numbers.

**And once in production.** The unrenderable matrix went from **10,984 ms to 406 ms** in Performance
Analyzer, 27x, with no semantic model change and no new DAX: a 15-item calculation group x 28
measures replaced by one query returning 12 rows x 10 base measures, with 315 cells derived and
formatted in the spec. Workings and the two traps it hit are in `measured-results.md`.

## What it buys, and what it does not

It removes three costs completely:

- **Row dispatch.** `SWITCH ( SELECTEDVALUE ( ... ), ... )` per row per column disappears; the rows
  are a `GROUP BY` on a real column.
- **Dynamic format strings.** Measured directly: the same 182 cells went from 622 ms to 1,270 ms
  warm purely from adding a dynamic format string that referenced its own measure. An ADOMD
  `EVALUATE` never evaluates `formatStringDefinition`, so this cost is invisible to a DAX benchmark
  and only shows up in the visual. See `per-cell-tax.md`.
- **Conditional-formatting measures.** Every CF measure is one more evaluation per cell. Colour
  computed in the spec costs nothing at query time.

It does **not** make the base measures faster. Those are the floor, and the floor can be high. On
the diagnosed matrix, the flat base-measure query (18 metrics x {Main, Compare, ALLSELECTED-total
Main, ALLSELECTED-total Compare}, so 72 measure columns over 3 rows) ran 1,580 ms cold / 1,500 ms
warm. Drop the ALLSELECTED total columns, leaving 36 measure columns, and it is 819 ms / 838 ms.
Take only the 7 additive Main measures and it is 192 ms cold / 61 ms warm. Deneb gets you to the
flat-query number and no further; if that number is still too slow, the work is in the measures, not
in the visual.

For context on the same report: that matrix as it shipped measured 3,861 ms in Performance Analyzer,
and its `SWITCH`-dispatch query measured 4,493 ms cold / 1,997 ms warm.

## The dataset contract

Deneb exposes exactly one query role, called `dataset`. Every field, grouping columns and measures
alike, lands in that one well, and the spec reads them off `datum` by name.

The contract for a grid is: **one grouping column, plus any row-property columns you need, and N
measure columns.** Declare it at the top of the generator so it is one place, not scattered:

```python
# Dataset contract (display names, via displayName on the projections):
#   Line       string  27 distinct statement lines; detail rows carry a 4 x U+00A0 indent
#   LineKey    number  10..270 step 10, the sort key
#   LineClass  string  Detail | Subtotal | Total
#   Actual, Budget, LY, "YTD Actual", "YTD Budget", "YTD LY"   the 6 base measures
```

Three things to notice.

`LineKey` is a **sort key delivered as data**, not an assumed ordering. Vega does not inherit the
visual's sort; if you want deterministic row order you must ship the key and rank it in the spec.

`LineClass` is a **row property delivered as data**: one extra grouped column, free at query time,
that drives subtotal bolding, subtotal rules and label indentation in the spec. Anything that is a
property of the row rather than of the value belongs here.

The six measures are the *base* measures only. The eight variance columns (Var, Var %, vs LY,
vs LY %, and the YTD forms) never touch the engine.

The dataset query is one `SUMMARIZECOLUMNS`, the row axis a grouped column on a physical bridge
table, and the page's filter context pinned with `TREATAS` so it measures what the visual measures:

```dax
DEFINE
    VAR __TP = TREATAS ( { "Selected Period" }, 'Time Period'[Time Period] )
    VAR __Yr = TREATAS ( { 2026 }, 'DimDate'[Year] )
EVALUATE
SUMMARIZECOLUMNS (
    'Statement Rows'[Line],
    'Statement Rows'[LineKey],
    'Statement Rows'[LineClass],
    __TP, __Yr,
    "Actual",     [Row Actual],
    "Budget",     [Row Budget],
    "LY",         [Row LY],
    "YTD Actual", [Row Actual YTD],
    "YTD Budget", [Row Budget YTD],
    "YTD LY",     [Row LY YTD]
)
ORDER BY 'Statement Rows'[LineKey]
```

## The displayName rule: the failure mode that produces no error

**Deneb names dataset fields by the field's DISPLAY NAME in the Values well.** A projection's
`displayName` overrides its native name; where a projection has none, the field arrives under
`nativeQueryRef`. A shipped grid normally uses both forms: `Line`, `LineKey` and `LineClass` carry
no `displayName` and resolve by their native names, while every measure is renamed.

If the spec reads `datum['Amount']`, the projection must carry `"displayName": "Amount"`, with
`nativeQueryRef` still holding the field's real native name:

```json
{
  "field": { "Measure": { "Expression": { "SourceRef": { "Entity": "00_Measures" } },
                          "Property": "Row Actual" } },
  "queryRef": "00_Measures.Row Actual",
  "nativeQueryRef": "Row Actual",
  "displayName": "Actual"
}
```

`nativeQueryRef` is the field's real native name. It is **not** a rename. Setting it to `"Amount"`
on a measure called `Row Amount` does not rename anything.

Getting this wrong **fails silently**. The query runs and returns correct data. The dataset arrives
under the wrong key. Every `datum['Amount']` in the spec is `undefined`. A spec with a null guard
(and this template has one) renders an intact skeleton with every cell blank, and the axes still
drawn, because the scale domains are explicit constants rather than derived from data. There is no
error in Power BI Desktop, none from `pbir validate`, and none in Deneb's own log pane. This is the
single most likely reason a newly built grid comes up empty.

The check is mechanical: for every string literal the spec reads off `datum`, there is a projection
with a matching `displayName`, or, where the projection has none, a matching `nativeQueryRef`. Do
that check before you open Desktop.

## The flat query changes what the measures see

Moving from a dispatch matrix to a flat grouped query is not only a performance change. It changes
the **filter context every measure runs in**, and two classes of bug live in that gap. Neither
raises an error.

### Only calendar-registered columns are safe to group

If any measure in the dataset query does time intelligence over a modern `calendar` object, so
`DATEADD ( <calendar>, -1, YEAR )` and friends, then **only the columns registered in that calendar
object may appear in the `GROUP BY`.** `DATEADD` shifts filters on registered columns and leaves
everything else alone, so an unregistered column of the same date table survives the shift with its
original value still filtering. The shifted rows do not match it and the measure returns `BLANK`,
for every row, silently.

A calculation-group matrix hides this completely: the calc item rewrites the filter context before
the measure runs, so the extra column never gets a chance to be stale. Flatten the query and it does.

The symptom is unmistakable once you know it: the current-period measures are perfect and the
prior-period ones are all blank. Nothing else in the visual is wrong.

The fix costs no DAX. Bind the offending column as an **aggregation** rather than a grouping field:
in PBIR, an `Aggregation` field with a `QueryAggregateFunction` (`3` = `Min` for a column that is
constant within the group). It then lands in `SUMMARIZECOLUMNS` as an extension column, which adds
no filter and is invisible to `DATEADD`. If you do not need the value at all, drop the projection.

Scope limit: a classic marked date table (`dataCategory: Time`) does not have this problem. The trap
belongs to the modern `calendar` object, where registration is explicit and partial. Full worked
example, including the diagnostic query that tests grouped / aggregated / absent in one go, is in
`measured-results.md`.

### DAX blank semantics do not survive the trip to JavaScript

Every derived column you move into the spec is a DAX expression you are now reimplementing in Vega,
and the two languages disagree about nothing so much as they disagree about blank:

| DAX | Vega / JS |
|---|---|
| `DIVIDE(n, d)` is `BLANK` when `d` is blank **or** `0`, and when `n` is blank | `n / d` is `Infinity`, `NaN` or a number |
| `a - b` is `BLANK` only when **both** are blank; otherwise blank acts as `0` | `null - 5` is `-5`, `null - null` is `0` |
| `SUM` over no non-blank rows is `BLANK` | `sum` over nothing is `0` |
| `BLANK` compares as neither `>` nor `<` | `null` coerces to `0` in every comparison |

The last row is the dangerous one, because it fails *plausibly*. A missing field makes a threshold
`null`, `datum.Period > datum.threshold` is then true for every row, and a "remaining year" column
silently renders the full year. No blank, no error, just wrong numbers in the right shape. **Guard
derived thresholds with `isValid` and let them stay `null` so the dependent columns fail closed to
blank**: a visibly empty column gets reported; a plausible one ships.

The sum rule needs a specific construction: aggregate each measure twice, `sum` and `valid`, and
restore the blank afterwards.

```json
{"type": "aggregate", "groupby": ["Period"],
 "fields": ["Amount", "Amount"], "ops": ["sum", "valid"], "as": ["sAmount", "vAmount"]},
{"type": "formula", "as": "Amount", "expr": "datum.vAmount > 0 ? datum.sAmount : null"}
```

Without it, a future period with no actuals reports `0` instead of blank, and every variance against
it comes out `-100%` where the original matrix showed nothing. Or the reverse, which is worse,
because `-100%` is what the matrix *does* show when there genuinely is a blank actual over a real
prior-year number.

## Spec anatomy: top level

```json
{
  "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
  "data": { "name": "dataset" },
  "padding": { "left": 4, "top": 10, "right": 16, "bottom": 14 },
  "transform": [ ... 22 entries ... ],
  "layer": [ ... 11 entries ... ]
}
```

`data.name` must be `dataset`: that is the name Deneb binds the query result to.

**There is deliberately no `width` and no `height`.** Deneb sizes the view from the visual container
using `autosize: fit` in the config; putting explicit dimensions in the spec produces an inner
scrollbar inside the visual. An offline renderer has to inject them, precisely because the shipped
spec omits them (see "Verifying without Power BI").

`padding` is the outer margin. The top padding is small because the header band is drawn in negative
pixel space above the plot area.

The matching config, which goes in `jsonConfig`:

```json
{
  "autosize": { "type": "fit", "contains": "padding", "resize": true },
  "background": "transparent",
  "view": { "stroke": null },
  "text": { "font": "Segoe UI, Segoe UI Web (West European), -apple-system, Helvetica Neue, sans-serif",
            "fill": "#4C5563" },
  "rect": { "stroke": null },
  "rule": { "strokeCap": "butt" }
}
```

## Spec anatomy: the scales

Both axes are **quantitative scales in grid-cell space**, with axes switched off. There is no band
scale, no categorical axis, and no Vega-Lite faceting.

```python
def yscale():
    return {"domain": [N_ROWS, 0], "nice": False, "zero": False, "clamp": False}

def xscale():
    return {"domain": [0, N_COLS], "nice": False, "zero": False, "clamp": False}
```

The y domain is `[27, 0]`: **inverted**, so row ordinal 0 renders at the top and row 26 at the
bottom, the way a statement reads. `nice: false` and `zero: false` stop Vega from rounding the
domain out and adding phantom rows. Every body mark then positions itself with plain arithmetic:
`rowIdx` is the top edge of a row, `rowIdx + 1` (`rowEnd`) the bottom, `rowIdx + 0.5` (`rowMid`) the
text baseline. Columns work the same way: `colIdx` is the left edge, `colEnd` the right, and
right-aligned numbers anchor to `colEnd` with a mark-level `xOffset: -11`.

### Two geometry options

**Index space** (what this template does). The `x` domain is `[0, N_COLS]`, so all columns are equal
width and the grid stretches to fill whatever container Power BI gives it. Simplest, and the right
default.

**Pixel space.** Set the `x` domain to `[0, TOTAL_PX]` and replace `colIdx` / `colEnd` with a
cumulative-offset lookup baked in by the generator:

```python
WIDTHS = [120, 120, 96, 72, 120, 96, 72, 120, 120, 96, 72, 120, 96, 72]
EDGES = [sum(WIDTHS[:i]) for i in range(len(WIDTHS) + 1)]   # 15 edges for 14 columns
```

then in the transform, `{"calculate": f"{json.dumps(EDGES)}[datum.colIdx]", "as": "colLeft"}` and the
same with `colIdx + 1` for `colRight`. Use this when you are replacing an existing matrix whose
column widths the client has already tuned and wants preserved: you can copy the saved widths
straight out of the old visual's `objects.columnWidth` entries. Untested; index space is what
shipped.

## Spec anatomy: the transform pipeline

Order is load-bearing. Each step's output is the next step's input, and getting the sequence wrong
produces plausible wrong numbers rather than an error. Derive amounts before the row formulas and
"Gross Margin % vs LY" silently becomes a ratio of differences instead of a difference of ratios.

**1. Rank the sort key into a dense row index.**

```json
{"window": [{"op": "rank", "as": "rowRank"}],
 "sort": [{"field": "LineKey", "order": "ascending"}]},
{"calculate": "datum.rowRank - 1", "as": "rowIdx"}
```

Rank rather than using `LineKey` directly, so the spec does not bake in the key's step convention.
Any monotonic key works, and adding a row to the registry does not require renumbering.

**2. Derive the extra columns**: differences and ratios of the base fields, one `calculate` each,
before the fold:

```json
{"calculate": "datum['Actual'] - datum['Budget']", "as": "Var"},
{"calculate": "(datum['Actual'] - datum['Budget']) / datum['Budget']", "as": "Var %"},
{"calculate": "datum['Actual'] - datum['LY']", "as": "vs LY"},
{"calculate": "(datum['Actual'] - datum['LY']) / datum['LY']", "as": "vs LY %"}
```

and the four YTD equivalents. Note the bracket syntax: field names with spaces, `%` or `&` must be
`datum['...']` throughout.

**3. Fold the wide row into one datum per cell.**

```json
{"fold": ["Actual","Budget","Var","Var %","LY","vs LY","vs LY %",
          "YTD Actual","YTD Budget","YTD Var","YTD Var %","YTD LY","YTD vs LY","YTD vs LY %"],
 "as": ["column", "value"]}
```

27 rows x 14 columns = 378 datums after this point. Everything downstream is per cell.

Caveat: after a fold, each datum **still carries the pre-fold columns**. `datum['Actual']` is still
readable on a datum whose `column` is `"Var %"`. That is useful (the row-label layer uses it) and it
is a trap if you assume "the numeric field" means the folded value.

**4. Column classification and ordinal lookup.**

```json
{"calculate": "indexof(datum.column, '%') >= 0", "as": "isPctCol"},
{"calculate": "indexof([\"Var\",\"Var %\",\"vs LY\",\"vs LY %\",\"YTD Var\",\"YTD Var %\",\"YTD vs LY\",\"YTD vs LY %\"], datum.column) >= 0", "as": "isVarCol"},
{"calculate": "datum.LineClass !== 'Detail'", "as": "isSubtotal"},
{"calculate": "indexof([\"Actual\",\"Budget\", ... ,\"YTD vs LY %\"], datum.column)", "as": "colIdx"}
```

`indexof` over an array literal is the lookup primitive here: the generator interpolates the Python
list straight into the expression with `json.dumps`, so the column order lives in one place.
`isPctCol`, `isVarCol` and `isSubtotal` are the three flags that every formatting and colour decision
downstream reads.

**5. Geometry.**

```json
{"calculate": "datum.rowIdx + 0.5", "as": "rowMid"},
{"calculate": "datum.rowIdx + 1",   "as": "rowEnd"},
{"calculate": "datum.colIdx + 1",   "as": "colEnd"}
```

**6. Formatting.** `absValue`, then `body`, then the guard (next section).

**7. A constant for chrome that must live on the y scale.**

```json
{"calculate": "-0.11", "as": "headerRuleY"}
```

The accent rule under the column headers sits slightly above row 0, in scale space, so it tracks the
grid if the row height changes. A literal-valued field is the way to put a constant onto an encoding
channel that needs a scale.

## Client-side formatting

This replaces the entire dynamic-format-string apparatus. These are Vega expression strings calling
`format()` with d3 format specs, evaluated in the browser on data already fetched.

Money auto-scales to `$M` / `$K`, percent columns to one decimal:

```json
{"calculate": "datum.isPctCol ? format(datum.absValue, '.1%') : (datum.absValue >= 999950 ? '$' + format(datum.absValue / 1000000, ',.1f') + 'M' : (datum.absValue >= 999.5 ? '$' + format(datum.absValue / 1000, ',.1f') + 'K' : '$' + format(datum.absValue, ',.0f')))",
 "as": "body"}
```

Each threshold is the point at which the branch *below* it would round up out of its own unit. At
999,950 the `$K` branch's `,.1f` gives `999950 / 1000 = 999.95`, printing `$1,000.0K`, so the `$M`
branch takes over and prints `$1.0M`. At 999.5 the plain `,.0f` branch would print `$1,000`, so the
`$K` branch takes over and prints `$1.0K`. Switch units *before* the rounding shows, not at a round
`1e6` / `1e3` boundary.

Keep the `,` group separator in every branch. A previous cut of this used `format(v/1e6, '.1f')` and
printed `$9790.8M`; the numeric verifier passed either way, and only the render caught it.

The value is formatted from `absValue`, and the sign becomes **accounting parentheses** in the guard
step, which also blanks non-finite values:

```json
{"calculate": "(!isValid(datum.value) || !isFinite(datum.value)) ? '' : (datum.value < 0 ? '(' + datum.body + ')' : datum.body)",
 "as": "cell"}
```

`!isFinite` is not optional. A ratio column divides by a base measure, and one zero-budget row gives
`Infinity`; the guard turns it into a blank cell. Keep a synthetic dataset with exactly such a row to
exercise that path.

For an **arrow-prefixed variance** format, add a prefix before the parentheses step:

```json
{"calculate": "(datum.value > 0 ? '▲ ' : datum.value < 0 ? '▼ ' : '') + datum.body", "as": "body"}
```

Two notes. Apply it only where you want it (`datum.isVarCol ? ... : datum.body`) or every cell gets
an arrow. And an arrow plus accounting parentheses on the same cell is redundant: pick one convention
per column class, the same way you would in a format string.

## Conditional colours as static config

Cell colour splits cleanly in two.

**Value-dependent colour** stays dynamic, and is computed in the spec from the value that is already
in the dataset. Nothing extra is queried:

```json
"fill": {
  "condition": [
    {"test": "datum.isVarCol && datum.value < 0", "value": "#B42318"},
    {"test": "datum.isSubtotal",                  "value": "#000000"},
    {"test": "datum.column === 'Actual' || datum.column === 'YTD Actual'", "value": "#05070A"}
  ],
  "value": "#1F252D"
}
```

Conditions are evaluated in order, first match wins, `value` is the fallback. This is where per-cell
CF measures go to die: red negatives on variance columns, emphasis on the primary columns, black on
subtotals. Three tests, zero engine cost.

**Row-property colour** becomes either a column in the dataset or a lookup baked into the spec at
build time. This template does the first: `LineClass` arrives from the model and drives bolding,
indentation and the subtotal rules. That is one extra grouped column and it is free.

When the property is not in the model (a section banding rule, or sentiment on named rows that exists
only in the report design), bake the map into the spec from the generator:

```python
NEGATIVE_ROWS = ["Discounts", "Marketing"]
transform.append({
    "calculate": f"indexof({json.dumps(NEGATIVE_ROWS)}, datum.Line) >= 0 ? '{RED}' : '{INK}'",
    "as": "rowInk"})
```

`indexof` over an array literal is the construct the shipped spec already uses, so it is known to
compile. (Vega expression object literals as a map would be tidier and are untested here.)

**The honest trade-off.** A baked lookup is only valid when the colour rule does not depend on
anything the engine computes at query time. "Colour this row red because it is a cost line" is a
design fact and belongs in the spec. "Colour this cell red because it is below the tolerance that
another measure computes" is a query fact: either return that tolerance as a dataset column and
compare in the spec, or keep the CF measure and keep paying for it. What you must not do is bake a
colour map that silently encodes an assumption about the data (a threshold that was true when you
built it), because nothing will tell you when it stops being true.

## PBIR embedding

The visual is a normal PBIR `visual.json` with a custom `visualType`. Prefer the `deneb_spec.py`
extract / embed round-trip from `custom-visuals:deneb-pbir` over hand-writing the literal; the rules
below are what that script is doing, and what you need when you are generating the spec rather than
editing it.

**1. The visual type.**

```
deneb7E15AEF80B9E4D4F8E12924291ECE89A
```

**2. Register it in `report.json`.** The visual type must appear in the report's
`publicCustomVisuals` array or the visual renders "Can't display this visual":

```python
rep = json.loads(rj.read_text(encoding="utf-8"))
pcv = rep.setdefault("publicCustomVisuals", [])
if DENEB not in pcv:
    pcv.append(DENEB)
    rj.write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
```

**3. The property bag.** Everything Deneb needs sits under `visual.objects.vega[0].properties`. Note
the `visual` level: `objects` is not at the root of the file. Each value is an `expr.Literal`:

```json
"visual": { "objects": { "vega": [ { "properties": {
  "provider":          { "expr": { "Literal": { "Value": "'vegaLite'" } } },
  "jsonSpec":          { "expr": { "Literal": { "Value": "'<the whole spec>'" } } },
  "jsonConfig":        { "expr": { "Literal": { "Value": "'<the whole config>'" } } },
  "enableTooltips":    { "expr": { "Literal": { "Value": "true" } } },
  "enableContextMenu": { "expr": { "Literal": { "Value": "true" } } },
  "enableSelection":   { "expr": { "Literal": { "Value": "false" } } },
  "enableHighlight":   { "expr": { "Literal": { "Value": "false" } } },
  "logLevel":          { "expr": { "Literal": { "Value": "3D" } } },
  "version":           { "expr": { "Literal": { "Value": "'6.4.1'" } } }
} } ] } }
```

Booleans are bare `true` / `false`; `logLevel` is the numeric literal `3D` (PBIR's double suffix);
strings, including the spec and the config, are single-quoted. `version` pins the Deneb runtime the
spec was written against, so keep the `v6` schema URLs and the `version` literal in step.

**4. Flatten and quote the spec.** The whole JSON document goes inside a single-quoted literal, so
embedded single quotes must be doubled:

```python
def pbir_lit(s):
    return "'" + s.replace("'", "''") + "'"

spec = json.dumps(json.loads(spec_f.read_text(encoding="utf-8")), separators=(",", ":"))
props["jsonSpec"] = {"expr": {"Literal": {"Value": pbir_lit(spec)}}}
```

Or in one expression:

```python
"'" + json.dumps(obj, separators=(",", ":")).replace("'", "''") + "'"
```

This matters more than it looks: the template's expressions are full of single quotes
(`datum.column === 'Actual'`), so an undoubled literal truncates the spec mid-expression and Deneb
reports a parse error at a position that has nothing to do with your edit.

**5. Round-trip check.** Never trust the write. Parse the literal back out of the file you just wrote
and assert the structure against the counts your generator produced:

```python
lit = v["visual"]["objects"]["vega"][0]["properties"]["jsonSpec"]["expr"]["Literal"]["Value"]
back = json.loads(lit[1:-1].replace("''", "'"))
assert len(back["layer"]) == N_LAYERS, len(back["layer"])
assert len(back["transform"]) == N_TRANSFORMS, len(back["transform"])
```

**6. Expect Deneb to rewrite the bag.** A build script typically writes a minified spec plus an
`isNewDialogOpen` property and no `version`. The on-disk file after Desktop has opened and saved the
report carries a pretty-printed spec (with `\r\n` line breaks), no `isNewDialogOpen`, and a `version`
literal. The reasonable inference is that Deneb re-serialises its own property bag on save. Do not
treat a non-minified literal as a corrupted write, and do not diff a Desktop-touched visual against
your generator's output expecting a byte match.

All the usual PBIR mechanics apply: close Desktop before editing, regenerate every `name` id when
cloning, never write PBIR JSON with a BOM. Those are in `pbir-build-safety.md`.

## Verifying without Power BI

Use the renderer bundled with `custom-visuals:deneb-pbir`. Do not vendor a second one.

```bash
# first use only, deps are gitignored
( cd "${CLAUDE_PLUGIN_ROOT}/skills/deneb-pbir/renderer" && npm install )

node "${CLAUDE_PLUGIN_ROOT}/skills/deneb-pbir/renderer/render.mjs" preview.json out.png \
  --data rows.json --scale 1
```

**It handles raw Vega as well as Vega-Lite** (verified 2026-08-29). Grammar comes from `$schema`,
falls back to a mark/encoding heuristic, and `--provider vega|vegaLite` overrides both; only a
Vega-Lite spec is compiled, a Vega spec is parsed as-is, and `--data` is injected into the object
form or the array form as appropriate. A raw-Vega grid spec rendered clean and reported
`"compiled":"vega"`. So a grid that outgrows Vega-Lite does not cost you your offline loop.

Three things it does not do for you, all of which a *shipped grid spec* needs. Build a **preview
copy** of the spec rather than editing the real one:

- **No `width` / `height` injection.** The shipped spec deliberately omits both (see "Spec anatomy"),
  and without them Vega-Lite renders at its 300x300 default: the whole grid crushed into a square.
  Setting `width` / `height` on the preview copy gives you the real geometry. `--scale` multiplies
  pixels, it does not set dimensions.
- **No `--config` flag.** Merge the config into the preview copy as `spec.config`.
- **No Deneb runtime stubs.** Any spec using `pbiColor`, `pbiFormat` or `pbiPatternSVG` dies at parse
  time with `Error: Unrecognized function: pbiColor`, before rendering starts. Either substitute
  literal colours in the preview copy, or, if the theme call is the thing you are checking, use an
  8-line wrapper that registers stubs against the same install:

```js
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';
const req = createRequire(process.env.DENEB_RENDERER_PKG);  // .../deneb-pbir/renderer/package.json
const vega = await import(pathToFileURL(req.resolve('vega')).href);
vega.expressionFunction('pbiColor', () => '#118DFF');
vega.expressionFunction('pbiFormat', (v) => String(v));
vega.expressionFunction('pbiPatternSVG', () => '');
// ...then parse and render as render.mjs does
```

Use a **white** preview config, not the shipped transparent one: a transparent background renders
black offline and reads exactly like the blank-cell bug.

```json
{"autosize": {"type": "fit", "contains": "padding", "resize": true},
 "background": "#FFFFFF",
 "view": {"stroke": null},
 "text": {"font": "Segoe UI, Segoe UI Web (West European), -apple-system, Helvetica Neue, sans-serif", "fill": "#4C5563"},
 "rect": {"stroke": null},
 "rule": {"strokeCap": "butt"}}
```

`rows.json` is a plain array of objects **in the dataset contract**: the keys are exactly the strings
the spec reads off `datum`.

```json
[
  { "Line": "    Retail Sales", "LineKey": 10, "LineClass": "Detail",
    "Actual": 5072688201.93, "Budget": 4971131423.10999, "LY": 4883800487.2,
    "YTD Actual": 5072688201.93, "YTD Budget": 4971131423.10999, "YTD LY": 4883800487.2 }
]
```

The workflow:

1. Write the dataset query as a `.dax` file with the slicer context pinned, and run it through
   `scripts/run_dax.ps1` against the open Desktop model. That gives you the timing *and* the rows.
2. Shape its output into the dataset contract as JSON. `run_dax.ps1` prints rows as
   `Name=Value | Name=Value`, but those names are the raw DAX result-column names ADOMD reports:
   `Statement Rows[Line]`, `[Actual]`, `[YTD Actual]`, not contract keys. The conversion has to strip
   the brackets and cast the numbers:

   ```powershell
   $rows = .\run_dax.ps1 -QueryFile .\grid.dax -Runs 2 |
     Where-Object { $_ -match ' \| ' } |
     ForEach-Object {
       $h = @{}
       foreach ($f in ($_ -split ' \| ')) {
         $k, $v = $f -split '=', 2
         $k = $k -replace '^.*\[(.+)\]$', '$1'   # 'Statement Rows[Line]' -> 'Line'
         $d = 0.0
         if ([double]::TryParse($v, [ref]$d)) { $h[$k] = $d } else { $h[$k] = $v }
       }
       [pscustomobject]$h
     }
   [IO.File]::WriteAllText("$PWD\rows.json", ($rows | ConvertTo-Json -Depth 3))
   ```

   Stripping the brackets only lands on the contract because the query's measure aliases are already
   the display names (`"Actual", [Row Actual]`). If they are not, rename them in the `.dax` file:
   that is the same name map you have to get right for the projections anyway.

   The `TryParse` cast is not optional: everything comes back as text, and Vega arithmetic on strings
   concatenates instead of adding. Or skip the reshaping and query straight to JSON with your own
   ADOMD snippet.

   Write it through `[IO.File]::WriteAllText`, not `Set-Content -Encoding utf8`. `run_dax.ps1` needs
   Windows PowerShell 5.1, whose `utf8` writes a BOM, and the renderer does a plain
   `JSON.parse(readFileSync(rowsPath, 'utf8'))` that throws `SyntaxError` on a leading BOM.
3. Render to PNG and look at it.
4. Iterate on the generator, re-render.

Why it matters: this catches inverted axes, clipped labels, wrong column order and a blank dataset in
seconds, against a Desktop close-edit-reopen cycle measured in minutes. Two real defects were found
this way *after* the spec had been reported as numerically verified: a money format missing its group
separator (`$9790.8M`), and a `limit` on the gutter text clipping a long row label.

For the numeric half, write a small Node script that re-implements the derived columns independently
and diffs every cell against the spec's own transform output (all 378 on the classic grid). Numeric
verification and visual verification catch different classes of bug and a grid needs both. Worth the
hour on any grid where a client will reconcile the numbers.

## Adapting the template to a new matrix

1. **Identify the grouping column.** One physical column whose distinct values are the grid's row
   groups. If your rows are dispatched by a `SWITCH` over a disconnected table, you may need
   `bridge-method.md` first to get a real column to group on.
2. **List the base measures.** Only the irreducible ones. On the diagnosed matrix that is 18 metrics
   x {Main, Compare}; the ALLSELECTED total pair doubles the column count and roughly doubles the
   cost (819 ms / 838 ms for 36 measure columns, 1,580 ms / 1,500 ms for 72), and all 36 ALLSELECTED
   total values tied out against the matrix's own subtotal row with zero mismatches, so bring them
   back in the same query if you need a total column.
3. **Decide derived against queried.** Anything that is arithmetic on other columns in the same row
   (differences, ratios, variances, percent-of-total against a total column you already have) is
   derived in the spec. Anything requiring a different filter context is queried.
4. **Write the row registry** in the generator: ordinal, label, which metric it reads, which category
   it belongs to, and its row colour. This is where a matrix with repeated metrics is handled: the
   diagnosed matrix has 26 display rows over 18 distinct metrics, with 5 section header rows carrying
   no measure and 3 metrics appearing on two rows each (26 - 5 = 21 measure rows; 18 + 3 = 21). In
   the registry those repeats are three *pairs* of entries, six entries across three fields, plus
   five entries with a null field and a caption style. A native matrix cannot do that without a
   helper table; a registry can.
5. **Write the column geometry.** Index space unless you are matching saved column widths. Set
   `N_ROWS` and `N_COLS`, and remember the y domain is `[N_ROWS, 0]`.
6. **Set the formats per category.** One `isXCol`-style flag per format class (money, percent, unit
   count, ratio) and one ternary chain in the `body` calculate.
7. **Wire the projections.** Every field the spec reads gets a `displayName` that matches the string
   in the spec exactly, including spaces and case.
8. **Render offline** with real rows. Look at it. Fix the layout in the generator, not the JSON.
9. **Embed** into `visual.json`, register the visual type in `report.json`, round-trip-assert the
   layer and transform counts.
10. **Validate** (`pbir validate --fields --qa`) and then **open in Desktop**. Validation passing is
    necessary and not sufficient; Desktop is the referee.

## Gotchas

- Deneb names dataset fields by the projection's `displayName`, falling back to `nativeQueryRef`
  where there is none: a mismatch renders a complete but blank grid with no error anywhere.
- No `width` / `height` in a shipped spec; Deneb sizes from the container and explicit dimensions
  give you a scrollbar inside the visual. The offline renderer needs them injected on a preview copy.
- The y scale domain is inverted (`[N_ROWS, 0]`) so row 0 is at the top; forget it and the statement
  renders upside down with no other symptom.
- Chrome that must sit above the plot area (group captions, column headers, dividers) uses a
  **mark-level constant** in pixel space (`"y": -38`, `"y": -22`, `"y": -46`); body elements use
  **scale-space** `y` encodings. Mixing the two puts headers inside the grid.
- `xOffset` / `yOffset` as *encoding channels* re-anchor a mark to the band start; use mark-level
  `xOffset` / `yOffset`, or a mark-level `x` with a `datum` expression, instead.
- `fontWeight` is not a Vega-Lite encoding channel: it compiles with only a warning and is silently
  dropped. Use a mark-level `fontWeight` with a datum expression, or two filtered mark layers.
- Field names with spaces, `%` or `&` need `datum['...']` everywhere; bare `datum.Var %` is a parse
  error and `datum.Var` is a different field.
- After a `fold`, datums still carry the pre-fold columns, so "the first numeric field" is not the
  folded value.
- Ratio columns produce `Infinity` on a zero denominator: the `!isFinite` guard is load-bearing, and
  you want a zero-denominator row in your test data.
- Money formats need the `,` group separator in every branch; a numeric verifier passes without it
  and only the render shows `$9790.8M`.
- Text `limit` clips silently: check your longest row label in the offline render.
- Native table visuals trim leading ASCII spaces in labels; this template avoids the whole issue by
  stripping the U+00A0 indent and applying a pixel offset per row class instead.
- `pbir validate` passing is necessary but not sufficient: it does not catch the displayName
  mismatch, a truncated `jsonSpec` literal, or an unregistered `publicCustomVisuals` entry.
- An unregistered date-table column in the `GROUP BY` blanks every `DATEADD`-based measure with no
  error; aggregate it or drop it.
- `null` coerces to `0` in every JS comparison, so a derived threshold that goes missing produces a
  plausible wrong column rather than a blank one. Put `isValid` guards on anything a filter reads.
- The bundled renderer throws `Unrecognized function: pbiColor` on Deneb theme helpers, at parse time
  rather than render time. Substitute literals in the preview copy, or register stubs in a wrapper.
- The offline renderer has no Segoe UI and estimates text width well over the true value, so `limit`
  truncation in a PNG is not evidence of truncation in Desktop. Check clipping in Desktop; use the
  render for layout, order and blanks.
