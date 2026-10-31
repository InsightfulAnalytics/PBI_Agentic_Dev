# Labels, layers and dates in `VegaVisual` charts

Five traps found building a nine-page Fabric App on `@microsoft/fabric-visuals` 5.0.0, each
reproduced in a headless `renderVisualToSvg` render and in the browser at widths from 390 to
2860 px (1 Nov 2026).

Retest: `npm ls @microsoft/fabric-visuals`, then render the spec with `npm run validate:visual`
and read the label positions in the SVG.

## 1. Value labels past the last mark are cut or run into the axis

Vega's `fit` autosize, which `VegaVisual` uses, shrinks the plot to make room for axes, legends
and titles. Text marks get no room: a value label placed beyond the outermost dot or bar draws
past the plot, into the row names on the left or cut at the SVG edge on the right. It shows only
at the widths where that mark sits near the edge.

- Put the label inside the plot: under or over its mark (`dy`), or on the side that faces the
  plot's centre. A mark's `dx` takes a per-datum expression, and `scale('x', ...)` works in it,
  so two close labels can be pushed apart by their distance in pixels.
- Or give the plot the room: a spec `padding` replaces the theme's (8 px left and right, 4 px
  top and bottom), so set all four sides.

Label a tie once. Two rows on the same value print one label over the other: add a `window`
`row_number` partitioned by the shown value and keep row 1 in the label layer.

A highlighted point drawn under its neighbours loses its outline. The `order` channel on a
point mark sets the draw order: give the focal row the highest value so it draws last.

## 2. Two-line axis labels overlap the marks, then get clipped

A `labelExpr` that returns an array draws one line per element, and Vega draws the extra lines
downward from the label's anchor. On a top axis, line two lands on the first row of marks. When
the line count depends on the width (wrap only when `bandwidth('x')` is too narrow for the name),
the axis height changes after `fit` has already sized the view: the names overlap the cells, and
once moved up a line they are cut off above the SVG.

Return the same number of lines for every label, a blank first line when the name fits on one,
and use a constant `labelPadding` that includes the extra line:

```ts
axis: {
  orient: "top", labelAngle: 0, labelLineHeight: 14, labelPadding: 6 + 14, labelLimit: 120,
  labelExpr: "bandwidth('x') < 84 && indexof(datum.label, ' ') > 0"
    + " ? [slice(datum.label, 0, lastindexof(datum.label, ' ')), slice(datum.label, lastindexof(datum.label, ' ') + 1)]"
    + " : ['', datum.label]",
}
```

## 3. A layer with a different field on a formatted axis: "Conflicting axis property"

`VegaVisual` formats every quantitative axis from its column. A layer that puts a different field
on the same channel, such as a rule from `__low` to `__high` beside dots on the measure, warns
`Conflicting axis property labelExpr`, and the axis loses its format. Draw the connector as a
`line` mark on the same field as the dots, with `detail` on the row and `order` on the end.

## 4. A test on a temporal field never matches

Vega parses a temporal field into a date before the spec's transforms run, so a focus test such
as `datum.Month === '2026-08-01'` is always false. Add a text key column in the data
(`MonthKey: "2026-08"`) and test that.

## 5. Month labels shift a month in some time zones

`new Date` on a zone-less ISO date, read back with the other convention (UTC against local
time), moves the first of a month into the month before in some time zones. Build month labels
and keys from the text: the year and month are its first seven characters.
