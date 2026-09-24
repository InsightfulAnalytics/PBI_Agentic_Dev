# Chart Selection, Data Labels, and Small Multiples

## Encoding Hierarchy: Match the Task to the Channel

Encode the value the reader needs to compare most precisely on the highest perceptual channel available. The Cleveland-McGill accuracy ranking: position on a common scale > length > angle/slope > area > color hue/saturation.

Useful inverse for an agent: given a `visual.json` on disk, decide whether `visualType` matches the analytical task and what the minimal repair is.

This block is the closed default vocabulary. A chart is built from one of these types unless it clears the gate in "Leaving the default vocabulary" below.

```
ranking / magnitude compare -> length on common axis  -> barChart / columnChart
trend over time             -> position + slope        -> lineChart / areaChart
two measures correlated     -> 2D position             -> scatterChart
part-to-whole, <=3-4 parts  -> angle/area (accept)     -> pie/donut OR stacked bar
part-to-whole, >4 parts     -> length (prefer)         -> barChart (stacked), not pie
single value vs target      -> position vs marker      -> kpi / card + reference line
```

Read the actual type and roles before judging:
```bash
pbir get "Page.Page/MyVisual.Visual.visualType"
pbir visuals bind "Page/MyVisual.Visual" --list-roles
```

### Repair before retyping

A `visualType` swap is the last repair, not the first. Sort, labels, accent and title are single `pbir` calls that leave the field bindings untouched and reverse cleanly; a swap can strand a bound field in a role the new type does not have. Work down this list and stop at the first move that makes the comparison readable:

```bash
pbir visuals sort "Page.Page/MyVisual.Visual" -f "<Table.Measure>" -d Descending
pbir visuals labels "Page.Page/MyVisual.Visual" --show   # then the value axis off, per "The axis and the label are one decision"
pbir set "Page.Page/MyVisual.Visual.dataPoint.series(<Table.Column>=<Value>).fill" --value "<accent>"   # neutral base first, and the accent from the locked identity, per references/visual-colors.md
pbir set "Page.Page/MyVisual.Visual.title.text" --value "<what the visual answers>"
```

Only when all four leave the comparison unreadable is the type itself wrong. The swap usually preserves bindings (pie, donut and `barChart`, the id the stacked bar chart is stored under, share Category/Y roles); read the roles either side of it so a dropped binding surfaces immediately. `pbir set` cannot reach `visualType`, so the retype itself is an edit to `visual.json`:

```bash
pbir visuals bind "Page.Page/MyVisual.Visual" --list-roles   # before the edit, and again after
pbir schema roles clusteredBarChart                          # the roles the new type expects
```

Then sort and validate. This ordering governs a chart that says the right thing badly. A chart that fails the insight test is simplified or cut instead, not nursed through successive repairs.

### Leaving the default vocabulary

A form outside the routing block is built only when one of two conditions holds, and the condition is stated before the build rather than defended after it:

1. **The audience already reads the form as routine.** The brief's `audience` line says so for these readers, not for readers in general. Reading it then costs them nothing.
2. **The form reveals what the default forms hide.** Name the structure the routing-block form loses (a distribution flattened to one mean, a rank change collapsed to two totals), and name which default form you tried.

State which condition is satisfied before the `pbir add visual <type> <path>` call, before embedding a spec at `visual.objects.vega[0].properties.jsonSpec`, and before binding an SVG extension measure that draws a chart rather than an inline glyph. Failing both, build the routing-block type and repair it with the list above.

The cost of failing this gate is canvas, not taste. A form the reader has to be taught carries its own instructions, and those instructions are real objects that take real space:

- a `legend` the default form would not have needed, or a subtitle textbox explaining how to read the marks
- a canvas tooltip page that exists only to decode the encoding (`references/tooltips-and-annotations.md`)
- a longer `visualContainerObjects.general[].properties.altText`, since that string is the entire description a screen reader gets and an unusual form takes more words to describe

If the form needs more than its own title to be readable, it is spending the space it claimed to buy.

### The sampling gate

A type can be schema-valid and role-correct yet wrong because the data shape defeats the encoding. Sample with `pbir model -q` before trusting a line chart (are there enough distinct x-points to form a trend?) or a bar chart (are there more than two bars?). Two rows back means a line chart is wasted; one dominant slice plus a long tail means the pie should be a sorted bar with the tail grouped into "Other".

### Pitfalls

- Pie/donut beyond ~4 slices forces the weakest channels; apply Top N + "Other" rather than adding colors
- A combo chart second axis is justified only when two genuinely different units share a category axis
- Hue is last; do not solve a comparison problem by adding more colors

---

## Data-Label Discipline

Labels earn their place only when the exact value matters and cannot be read off the axis: line endpoints, a single highlighted bar, KPI deltas. Per-segment labels and stacked totals are two different objects:

```bash
pbir visuals labels "Page.Page/Visual.Visual" --show            # per-data-point labels
pbir set "Page.Page/Visual.Visual.totals.show" --value true     # stacked totals
```

### The axis and the label are one decision

Decide the pair, never each on its own. The same value printed twice is redundant ink:

- Data labels on: the labels carry the scale, so turn the value axis off with `pbir visuals axis "Page.Page/Visual.Visual" value --no-show`
- Data labels off: the value axis stays and carries the scale
- Either way the axis title stays off. It is a theme decision taken once at the `visualStyles["*"]["*"]` wildcard, which `SqlbiDataGoblinTheme.json` and `Fluent2-CY26SU03.json` both do (`DataGoblins2021.json` does not, and needs it added), and after the insight test the visual title already says what is being measured. Turning it back on per visual is a theme-compliance defect, not a fix

### Precision belongs to the model

Trailing zeros, decimal places and units on axis text and data labels are a format-string decision in the semantic model, not a visual formatting one. An agent hunting a `1,200.00` axis label through `visual.json` is reading the wrong file.

- Set the measure's `formatString` in TMDL (the `pbip:tmdl` skill for the edit, `semantic-models:dax-standard` for a dynamic format string). A measure formatted once at the model needs no per-visual precision override anywhere it appears
- `pbir visuals labels ... --labelPrecision` and `--labelDisplayUnits` write `labels.labelPrecision` and `labels.labelDisplayUnits` on that one visual: an override that re-fragments the identity and has to be repeated on every chart the measure lands in
- KPI and card display units are the documented exception, because Auto is unreliable against a custom format string; see `references/cards-and-kpis.md`

### The stacked-total "incorrect number" trap

The recurring symptom where a stacked total does not match a hand-summed expectation is almost always a measure problem, not a label problem. The engine's stacked-group sum diverges from the expected total when the underlying measure is non-additive: a ratio, distinct count, or time-intelligence expression. Verify with `pbir model -q "EVALUATE SUMMARIZECOLUMNS(...)"` before touching the label. If the total is the "wrong" number, the label is honest and the measure needs an explicit aggregation strategy.

### Preferred pattern: endpoint-only labels

Prefer binding a measure that returns the value at the last/relevant point and BLANK elsewhere, rather than global labels plus conditional-formatting-based hiding. The chart stays clean and only the number that matters is annotated. This is the extension-measure label pattern described in `thin-report-measures` references.

### Legend or direct label

A legend makes hue the lookup key for series identity, and hue is last in the ranking at the top of this file. Every read then costs a trip to the legend and back. Route by series count:

- 1 series: legend off always, it encodes nothing
- 2 to 4 series: legend off, and label each series at its last point with the BLANK-elsewhere measure above
- More series than a legend reads cleanly: small multiples (below), not a longer legend; that section sets the threshold
- Legend retained only when the series set is user-driven, a field parameter or a slicer-driven legend field, because the labels cannot then be authored ahead of time

```bash
pbir visuals legend "Page.Page/Visual.Visual" --no-show
pbir visuals legend "Page.Page/Visual.Visual" --no-showTitle   # legend kept, but its title restates the field name
```

Series count is the input to this routing and a theme wildcard cannot see it, so `show` stays the per-visual decision. What the theme settles once is the rest: position, and `showTitle: false` so a kept legend never restates the field name (`modifying-theme-json` skill, `references/theme-authoring.md`, Declutter Defaults). Data labels bind per series rather than per point, which is why the BLANK-elsewhere measure is the mechanism for an endpoint label.

### Pitfalls

- Small multiples disable stacked total labels entirely (see below)
- Label display units must match the axis units
- A measure returning BLANK beats global-labels-plus-CF: less JSON, less fragile

---

## Small Multiples

Choose small multiples over a legend when the question is "does this pattern hold across a dimension" and there are more series than a legend reads cleanly (roughly more than 3-4). A legend overlays series in one frame for value comparison; small multiples separate them into a synchronized grid so you compare shapes across many categories.

Supported only on bar, column, line, and area charts. The grid synchronizes axes and fills left-to-right then top-to-bottom in sort order, with overflow scrolling beyond the visible grid.

### The Series vs SmallMultiples role distinction

`Series`/`Legend` overlays series in a single frame; true small multiples use the dedicated `SmallMultiples` role that partitions into the grid. The `smallMultiplesLayout` object only takes effect when the `SmallMultiples` role is populated. Confirm before editing:

```bash
pbir visuals bind "Page/MyVisual.Visual" --list-roles
```

### Features that are inert once a visual is trellised

Do not waste edits on these; they silently have no effect in a small-multiples context:

- Total labels for stacked charts
- Trend lines and forecasting
- Zoom sliders
- Line high-density sampling
- Concatenated axis labels and hierarchical axis (falls back to concatenated)
- Scroll-to-load-more
- Small-multiple cell title display units/decimals/format (the model's format string controls them, per "Precision belongs to the model" above)

Check for the `SmallMultiples` role before adding any analytics overlays.

### Pitfalls

- A 6x6 grid of dense charts defeats the purpose; apply Top N on the partition field and group the remainder into "Other"
- Synchronized axes are a feature, not a bug; do not give each cell its own scale unless the analytical intent is explicitly within-series comparison
