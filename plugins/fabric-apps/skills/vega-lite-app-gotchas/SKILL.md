---
name: vega-lite-app-gotchas
version: 26.40.3
description: Hard-won fixes for Vega-Lite specs rendered inside a React / Power BI / Fabric App (the `VegaVisual` + Tailwind stack). Invoke when a value label is cut at the plot edge or runs into the row names, two-line axis labels overlap the marks, a layer reports "Conflicting axis property", a Vega-Lite chart "sorts alphabetically instead of by month", an ordinal axis won't honour a string `sort` array, a multi-series line chart shows all series in one tooltip or ignores a custom `tooltip`, tooltip numbers mix `$420k` and `$1.2M`, a chart renders with no color / "color is not a valid CSS color" after using `var(--ds-*)`, the chart loses its brand color, axis labels get clipped by the card, you're laying out a KPI card in Vega, or you hit "Duplicate signal name" on hover_tuple. Covers ordinal sorting, multi-series tooltips, value pre-formatting, CSS-variable resolution in SVG, the `--color-brand` theming bridge, card overflow clipping, and KPI-card layout.
---

# Vega-Lite gotchas (React / Power BI App)

Eight traps that cost real time when rendering Vega-Lite specs through a `VegaVisual`
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
