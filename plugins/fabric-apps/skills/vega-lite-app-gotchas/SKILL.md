---
name: vega-lite-app-gotchas
version: 26.40.3
description: Hard-won fixes for Vega-Lite specs rendered inside a React / Power BI / Fabric App (the `VegaVisual` + Tailwind stack). Invoke when a value label is cut at the plot edge or runs into the row names, two-line axis labels overlap the marks, a layer reports "Conflicting axis property", a Vega-Lite chart "sorts alphabetically instead of by month", an ordinal axis won't honour a string `sort` array, a multi-series line chart shows all series in one tooltip or ignores a custom `tooltip`, tooltip numbers mix `$420k` and `$1.2M`, a chart renders with no color / "color is not a valid CSS color" after using `var(--ds-*)`, the chart loses its brand color, axis labels get clipped by the card, you're laying out a KPI card in Vega, or you hit "Duplicate signal name" on hover_tuple. Also invoke on fabric-visuals 5.0 when `axis: null` still draws an axis, an axis `format` prints NaN or is ignored, labelled bars sort alphabetically ("unioned domains only support"), text labels read "2.1K", or a click's selection predicates come back with `fieldId`. Covers ordinal sorting, multi-series tooltips, value pre-formatting, CSS-variable resolution in SVG, the `--color-brand` theming bridge, card overflow clipping, KPI-card layout, and the fabric-visuals 5.0 axis, sort, label and interaction traps.
---

# Vega-Lite gotchas (React / Power BI App)

Fourteen traps that cost real time when rendering Vega-Lite specs through a `VegaVisual`
component (Vega writes resolved SVG; Tailwind tree-shakes; cards clip). Each looks like it
*should* work; the fix is non-obvious.

Labels, layers and dates are in
[references/labels-layers-dates.md](references/labels-layers-dates.md): a value label cut
at the plot edge or over the row names, two-line axis labels on the marks, `Conflicting axis
property labelExpr`, a test on a temporal field that never matches, month labels a month out.

> Source: distilled from the Sparklines / Bullet / Imperial-DSMS Fabric Apps. Hex values
> in examples are the corporate-blue design tokens (`--ds-blue-700` = `#1F4E8C`).

## 1. Ordinal sort by a string array silently fails → use a numeric field + `labelExpr`

A `sort: ["Jan", "Feb", …]` array on an ordinal axis is often ignored and the axis sorts
alphabetically (Apr, Aug, Dec, …). Don't fight it with `sort: { field, op: "min" }`.
Bind the axis to the **numeric** field (ordinal scales sort numerically for numeric data)
and re-label ticks with `labelExpr`:

```ts
// ❌ Looks right, didn't sort
x: { field: "monthShort", type: "ordinal", sort: ["Jan","Feb", /* … */ "Dec"] }

// ✅ Numeric field sorts correctly; labelExpr restores the text
x: {
  field: "monthOfYear", type: "ordinal",
  axis: {
    labelExpr:
      "['','Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][datum.value]",
  },
}
```

Same fix for any "string label that should sort by a hidden numeric".

## 2. Multi-series tooltip → invisible wide `rule` layer + `pivot`

For a multi-series line chart with `point: true`, Vega's nearest-x default tooltip kicks in,
shows ALL series with raw field names, and **silently ignores** your custom `tooltip: [...]`.
The canonical fix is a selection-free invisible rule layer that owns the tooltip:

```ts
{
  transform: [
    { pivot: "businessLine", value: "revenueLabel", groupby: ["monthOfYear", "monthShort"] }
  ],
  mark: { type: "rule", opacity: 0, strokeWidth: 32 },   // 32px-wide hover region
  encoding: {
    color: { value: "transparent" },
    tooltip: [
      { field: "monthShort", title: "Month" },
      ...seriesNames.map((name) => ({ field: name, title: name })),
    ],
  },
}
```

Pass `seriesNames` in from React (`Array.from(byLine.keys())`); don't hardcode them. This
pattern is **selection-free** on purpose (see #8).

## 3. Pre-format tooltip values in JS, not with d3-format `~s`

`format: "$,.2s"` auto-picks SI suffixes, so one tooltip mixes `$420k` and `$1.2M`. When the
user said "in millions", compute a **string column** in the React data table and reference
it as a `nominal` field:

```ts
const fmtMillions = (v: number) => "$" + (v / 1_000_000).toFixed(2) + "M";
// row: { …, revenueLabel: fmtMillions(r.revenue) }
tooltip: [{ field: "revenueLabel", title: "Revenue" }]
```

## 4. SVG output can't resolve `var(--ds-*)`: hardcode hex inside the spec

CSS variables work in DOM nodes but Vega writes resolved SVG, where CSS vars become empty
strings (→ "color is not a valid CSS color", or nothing renders). Inside any Vega spec use
literal hex:

```ts
const BLUE_700 = "#1F4E8C";              // mirror the design token once, at module top
mark: { type: "bar", color: BLUE_700 }   // ✅   (never color: "var(--ds-blue-700)")
```

Keep a small palette object per page module so the values live in one place.

## 5. Theming bridge: `--color-brand` must be in `@theme static`

`VegaVisual` and `DataGrid` call `useCssTheme()`, which reads `--color-brand` at runtime. If
it's only set via `@theme { … }`, Tailwind tree-shakes it out when no utility consumes it and
the chart loses its primary color. Force it with `@theme static`:

```css
@theme static {
  --color-brand: #1F4E8C;
  --color-brand-foreground: #1F4E8C;
  --color-hover: #F1F6FC;
}
```

## 6. Card/container clipping eats axis labels → `minHeight`, not fixed `height` + `overflow:hidden`

A `ChartCard` body with `overflow: hidden` and a fixed `height` makes Vega's bottom axis labels
vanish silently. Let the SVG's natural size drive the container:

```tsx
// ❌ <div style={{ padding: 16, height: bodyHeight, overflow: "hidden" }}>
// ✅
<div style={{ padding: 16, minHeight: bodyMinHeight }}>
```

## 7. KPI cards: layered text/rect marks at absolute pixel coords

A label + big value + conditionally-coloured pill is well-suited to Vega-Lite layered
`text`/`rect` marks with literal pixel coordinates (`x: { value: 0 }, y: { value: 30 }`).
Pre-format the metric as a **string** (`nominal`) so each card chooses its own currency /
percent format without baking d3-format codes into the spec.

## 8. Don't use `params: { name: "hover" }` for multi-series tooltips

Re-rendering the same named selection triggers **"Duplicate signal name: hover_tuple"**. The
invisible-rule + `pivot` pattern in #2 is selection-free and side-steps this entirely.

## fabric-visuals 5.0: six more traps in `VegaVisual` and `VisualContainer`

Found building the Reading Room app on `@microsoft/fabric-visuals` 5.0.0 (31 Oct 2026), each
confirmed with a headless `renderVisualToSvg` render as well as in the browser.

### 9. `axis: null` is ignored: switch the parts off one by one

The axis still draws, labels, ticks and title included. For a bar chart labelled at the bar
ends:

```ts
x: { field: "Hours", type: "quantitative",
     axis: { labels: false, ticks: false, domain: false, grid: false, title: null } }
```

### 10. Axis `format` and `formatType` are ignored: format ticks with `labelExpr`

A temporal axis with `format: "%a %e %b"` printed NaN, and a quantitative axis with
`format: ".0%"` used the column's model format string instead. `labelExpr` is honoured:

```ts
axis: { labelExpr: "utcFormat(datum.value, '%a %e %b')" }  // temporal
axis: { labelExpr: "format(datum.value, '.0%')" }          // a 0-1 share
```

### 11. A layered spec drops a `sort` with the default op: use `max` or `min`

Layers share (union) the y scale's domain, and a union accepts only `count`, `min` and `max`
sort ops (the warning reads "as unioned domains only support boolean or op "count", "min",
and "max""). `sort: { field:
"Hours", order: "descending" }` defaults to `sum`, so it is dropped and the bars fall back to
alphabetical order. A bar plus its text label is two layers, so this bites every labelled bar:

```ts
y: { field: "Area", type: "nominal", sort: { field: "Hours", op: "max", order: "descending" } }
```

### 12. Number text marks are compacted: print a string column

A `text` mark over a number prints "2.1K" for 2,131. Add the label as a pre-formatted string
column in the data table (as in #3) and encode it as `nominal`.

### 13. Interaction predicates name the field `fieldId`, and values are tagged

`onInteraction` events carry `selections[0].predicates`, each
`{ type: "set", fieldId, values: [{ kind: "value", value }] }` (not `name` and bare values). A
clear arrives as `action: "clear"` or an empty `selections`.
`selectableFields` lets a click select a field the mark does not encode, such as the part of the
site behind a page's bar.

### 14. `VisualContainer`'s header toolbar re-wraps the title on hover

With a `header`, the Copy visual and More actions toolbar sits in flow beside it at zero width
and widens on hover or focus, by design, so a wrapping title re-wraps and the chart under it
jumps. Keep the width and fade the toolbar instead, in a cascade layer after `fabric-visuals`
(the library's Griffel styles live there):

```css
@layer components {
  [vc-toolbar=""] { width: auto; margin-inline-start: var(--spacing-m); overflow: visible;
                    opacity: 0; transition: opacity 150ms ease-out; }
  [data-lyra-selection-boundary]:hover [vc-toolbar=""],
  [data-lyra-selection-boundary]:focus-within [vc-toolbar=""],
  [vc-toolbar=""]:has([aria-expanded="true"]) { opacity: 1; }
}
```

`[data-lyra-selection-boundary]` is the container's own root; a bare `section:hover` also
matches any `<section>` inside the card. Without a `header` the toolbar floats above the card's
top edge instead, which overlaps the card above in a tight grid.
