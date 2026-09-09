# Vega-Lite Chart Patterns for Deneb

Common chart patterns for Deneb visuals. All specs assume `"data": {"name": "dataset"}` and Vega-Lite v6, bundled since Deneb 1.8: Deneb 2.0.0.0 ships Vega-Lite 6.4.3, Deneb 1.9.x shipped 6.4.1 (Verified 2026-09-08 against Deneb's `package.json` and the docs changelog "Vega Updates").

Retest: `gh api repos/deneb-viz/deneb/contents/package.json --jq '.content' | base64 -d | grep '"vega-lite"'`

Every block below carries a root `$schema` for editors and the offline renderer; it never goes into `jsonSpec` (`deneb_spec.py embed` strips it; strip it yourself if you hand-embed).

Container signals: Vega-Lite specs normally need none (Deneb sets `width` and `height` to `"container"` for standard layouts). When an `expr` does need the container size, the same rule as Vega applies: `pbiContainerWidth` / `pbiContainerHeight` work on 1.9.x and on every 2.x (rewritten at parse time with a logged warning); `denebContainer.width` / `denebContainer.height` is the 2.0 name and does not exist on 1.9.x. Use the 2.0 name only when the visual.json carries `developer.version` 2.0.0.0 or later; see [deneb-2-migration.md](deneb-2-migration.md#authoring-rules-during-the-transition).

Do not name one of your own params `denebContainer`. Before Deneb patches a Vega-Lite spec it checks only the TOP-LEVEL `params` array for an existing entry of that name, so a param of that name inside a nested layer, concat or facet spec is not detected, Deneb injects its own alongside it, and Vega-Lite raises a duplicate-name error at compile time (read from `parse.ts` and `patch-vega-lite.ts` in Deneb source at `main`, not reproduced in Power BI, Verified 2026-09-08).

Retest: put a `denebContainer` param inside a `layer` entry, open the spec in a Deneb 2.0.0.0 visual and read the Logs pane for the duplicate-name error.

## Bar Chart (Vertical)

```json
{
  "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
  "data": {"name": "dataset"},
  "mark": {"type": "bar", "tooltip": true, "cornerRadiusTopLeft": 4, "cornerRadiusTopRight": 4},
  "encoding": {
    "x": {"field": "Category", "type": "nominal", "sort": "-y"},
    "y": {"field": "Sales", "type": "quantitative"},
    "color": {"value": {"expr": "pbiColor(0)"}}
  }
}
```

## Bar Chart (Horizontal)

```json
{
  "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
  "data": {"name": "dataset"},
  "mark": {"type": "bar", "tooltip": true, "cornerRadiusTopRight": 4, "cornerRadiusBottomRight": 4},
  "encoding": {
    "y": {"field": "Category", "type": "nominal", "sort": "-x"},
    "x": {"field": "Sales", "type": "quantitative"}
  }
}
```

## Bar Chart with Cross-Highlighting

Two-layer pattern: background shows full value at reduced opacity, foreground shows highlighted portion.

```json
{
  "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
  "data": {"name": "dataset"},
  "layer": [
    {
      "mark": {"type": "bar", "opacity": 0.3, "tooltip": true},
      "encoding": {"x": {"field": "Sales"}}
    },
    {
      "mark": {"type": "bar", "tooltip": true},
      "encoding": {
        "x": {"field": "Sales__highlight"},
        "opacity": {
          "condition": {"test": {"field": "__selected__", "equal": "off"}, "value": 0},
          "value": 1
        }
      }
    }
  ],
  "encoding": {
    "y": {"field": "Category", "type": "nominal"},
    "x": {"type": "quantitative"}
  }
}
```

Requires `enableHighlight: true` and `enableSelection: true` in visual objects. `Sales__highlight` is a measure supporting field: on Deneb 1.9.x and on visuals migrated into 2.0 it is always present once cross-highlight is on; in a new 2.0 project it is present by default only because a measure's `highlight` flag defaults to on when cross-highlight is enabled, while `__highlightStatus` and `__highlightComparator` are opt-in through `supportFieldConfiguration`. If the visual was migrated while cross-highlight was off, its measures were stamped `highlight: false` and switching `enableHighlight` on later does not add the field until the flag is set. The migration stamps those flags once, on first open, and then reads them verbatim: the cross-highlight state at that moment is frozen into the configuration. See [deneb-2-migration.md](deneb-2-migration.md#what-20-changes-on-first-open).

## Line Chart

```json
{
  "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
  "data": {"name": "dataset"},
  "mark": {"type": "line", "point": true, "tooltip": true, "strokeWidth": 2},
  "encoding": {
    "x": {"field": "Date", "type": "temporal"},
    "y": {"field": "Sales", "type": "quantitative"},
    "color": {"field": "Region", "type": "nominal", "scale": {"scheme": "pbiColorNominal"}}
  }
}
```

## Line Chart with Area Fill

```json
{
  "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
  "data": {"name": "dataset"},
  "mark": {"type": "area", "opacity": 0.15, "line": {"strokeWidth": 2}, "tooltip": true},
  "encoding": {
    "x": {"field": "Date", "type": "temporal"},
    "y": {"field": "Value", "type": "quantitative"},
    "color": {"field": "Series", "type": "nominal", "scale": {"scheme": "pbiColorNominal"}}
  }
}
```

## Scatter Plot

```json
{
  "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
  "data": {"name": "dataset"},
  "mark": {"type": "point", "tooltip": true, "filled": true, "opacity": 0.7},
  "encoding": {
    "x": {"field": "Revenue", "type": "quantitative"},
    "y": {"field": "Profit", "type": "quantitative"},
    "size": {"field": "Quantity", "type": "quantitative"},
    "color": {"field": "Category", "type": "nominal", "scale": {"scheme": "pbiColorNominal"}}
  }
}
```

## Heatmap

```json
{
  "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
  "data": {"name": "dataset"},
  "mark": {"type": "rect", "tooltip": true},
  "encoding": {
    "x": {"field": "Day", "type": "ordinal"},
    "y": {"field": "Hour", "type": "ordinal"},
    "color": {"field": "Value", "type": "quantitative", "scale": {"scheme": "pbiColorLinear"}}
  }
}
```

## Donut Chart

```json
{
  "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
  "data": {"name": "dataset"},
  "mark": {"type": "arc", "innerRadius": 50, "tooltip": true},
  "encoding": {
    "theta": {"field": "Sales", "type": "quantitative", "stack": true},
    "color": {"field": "Category", "type": "nominal", "scale": {"scheme": "pbiColorNominal"}},
    "order": {"field": "Sales", "type": "quantitative", "sort": "descending"}
  }
}
```

## Bullet Chart (Faceted with Target)

```json
{
  "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
  "data": {"name": "dataset"},
  "transform": [
    {"window": [{"op": "rank", "as": "rank"}], "sort": [{"field": "Value", "order": "descending"}]},
    {"filter": "datum.rank <= 10"}
  ],
  "facet": {
    "row": {
      "field": "Category", "type": "nominal",
      "sort": {"field": "Value", "order": "descending"},
      "header": {"labelAngle": 0, "title": "", "labelAlign": "left"}
    }
  },
  "spec": {
    "layer": [
      {"mark": {"type": "bar", "color": {"expr": "pbiColor(0, 0.7)"}, "size": 10}, "encoding": {"x": {"field": "Value", "type": "quantitative"}}},
      {"mark": {"type": "tick", "size": 25, "color": {"expr": "pbiColor(0, -0.5)"}}, "encoding": {"x": {"field": "Target", "type": "quantitative"}}},
      {"mark": {"type": "text", "align": "right", "dx": -5}, "encoding": {"x": {"value": -15}, "text": {"field": "Value", "format": ",.0f"}, "color": {"value": {"expr": "pbiColor(0, -0.3)"}}}}
    ]
  }
}
```

## Lollipop Chart

```json
{
  "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
  "data": {"name": "dataset"},
  "encoding": {
    "y": {"field": "Category", "type": "nominal", "sort": "-x"},
    "x": {"field": "Value", "type": "quantitative"}
  },
  "layer": [
    {"mark": {"type": "rule", "strokeWidth": 2, "color": {"expr": "pbiColor(0)"}}},
    {"mark": {"type": "point", "filled": true, "size": 100, "color": {"expr": "pbiColor(0)"}}}
  ]
}
```

## Stacked Bar Chart

```json
{
  "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
  "data": {"name": "dataset"},
  "mark": {"type": "bar", "tooltip": true},
  "encoding": {
    "x": {"field": "Date", "type": "temporal"},
    "y": {"field": "Sales", "type": "quantitative"},
    "color": {"field": "Region", "type": "nominal", "scale": {"scheme": "pbiColorNominal"}}
  }
}
```

## Waterfall Chart

```json
{
  "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
  "data": {"name": "dataset"},
  "transform": [
    {"window": [{"op": "sum", "field": "Amount", "as": "sum"}]},
    {"window": [{"op": "lead", "field": "Category", "as": "lead"}]},
    {"calculate": "datum.lead === null ? datum.Category : datum.lead", "as": "lead"},
    {"calculate": "datum.Category === 'Total' ? 0 : datum.sum - datum.Amount", "as": "previous_sum"},
    {"calculate": "datum.Category === 'Total' ? datum.sum : datum.Amount", "as": "amount"},
    {"calculate": "(datum.Category !== 'Begin' && datum.Category !== 'Total' && datum.amount > 0 ? '+' : '') + datum.amount", "as": "text_amount"},
    {"calculate": "(datum.sum + datum.previous_sum) / 2", "as": "center"},
    {"calculate": "datum.sum < datum.previous_sum ? datum.sum : ''", "as": "sum_dec"},
    {"calculate": "datum.sum > datum.previous_sum ? datum.sum : ''", "as": "sum_inc"}
  ],
  "encoding": {
    "x": {"field": "Category", "type": "ordinal", "sort": null}
  },
  "layer": [
    {
      "mark": {"type": "bar", "size": 45},
      "encoding": {
        "y": {"field": "previous_sum", "type": "quantitative", "title": "Amount"},
        "y2": {"field": "sum"},
        "color": {
          "condition": [
            {"test": "datum.Category === 'Begin' || datum.Category === 'Total'", "value": {"expr": "pbiColor(0)"}},
            {"test": "datum.sum < datum.previous_sum", "value": {"expr": "pbiColor('negative')"}}
          ],
          "value": {"expr": "pbiColor('positive')"}
        }
      }
    },
    {
      "mark": {"type": "text", "dy": -4, "baseline": "bottom"},
      "encoding": {
        "y": {"field": "sum_inc", "type": "quantitative"},
        "text": {"field": "sum_inc", "type": "nominal"}
      }
    }
  ]
}
```

## Sparkline (Small Multiple)

```json
{
  "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
  "data": {"name": "dataset"},
  "facet": {"row": {"field": "Category", "type": "nominal", "header": {"labelAngle": 0, "title": ""}}},
  "spec": {
    "width": 200,
    "height": 30,
    "mark": {"type": "line", "strokeWidth": 1.5, "color": {"expr": "pbiColor(0)"}},
    "encoding": {
      "x": {"field": "Date", "type": "temporal", "axis": null},
      "y": {"field": "Value", "type": "quantitative", "axis": null, "scale": {"zero": false}}
    }
  }
}
```

## Field Parameter (Consolidated, Deneb 2.0)

With `stateManagement.consolidateFieldParameters` on, a field parameter arrives as one array-valued column named after the parameter (its display name), plus companion arrays such as `<Parameter>__names` (opt-in). `flatten` gives one row per selected component; `__row__` survives, so tooltips and cross-filtering still resolve. Pattern from the Deneb docs (`field-parameters.md`, "Working with Array Data"):

```json
{
  "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
  "data": {"name": "dataset"},
  "transform": [
    {"flatten": ["Metric", "Metric__names"]}
  ],
  "mark": {"type": "bar", "tooltip": true},
  "encoding": {
    "y": {"field": "Metric__names", "type": "nominal", "title": null},
    "x": {"field": "Metric", "type": "quantitative"},
    "color": {"field": "Metric__names", "type": "nominal", "scale": {"scheme": "pbiColorNominal"}, "legend": null}
  }
}
```

- Reference the parameter's display name, never a component's; `Metric__names` needs `names: true` in the parameter's `supportFieldConfiguration` entry
- 2.0-only: a visual.json with no `denebMetaVersion` and no `supportFieldConfiguration` is treated as a migrated 1.x project on first open under 2.0 and consolidation is pinned off (a configuration without the version stamp is the half-stamped row in `references/pbir-structure.md`, not legacy), so stamp `denebMetaVersion '2'`, `consolidateFieldParameters true` and `supportFieldConfiguration` together; on 1.9.x the components arrive pass-through as ordinary fields. Rules and PBIR shape: `references/vega-patterns.md` (Field Parameters) and [deneb-2-migration.md](deneb-2-migration.md#authoring-rules-during-the-transition)

## Power BI Format Strings (`formatType: "pbiFormat"`)

Wherever Vega-Lite accepts `format`, set `formatType` to `pbiFormat` (a Power BI format string, not d3) or `pbiFormatAutoUnit` (nearest K / M / bn unit, like the Auto display unit). Deneb registers both custom format types and sets `customFormatTypes: true` for you. From the Deneb docs (`formatting-values.md`):

```json
{
  "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
  "data": {"name": "dataset"},
  "mark": {"type": "line", "point": true},
  "encoding": {
    "x": {"field": "Date", "type": "temporal", "axis": {"format": "MMM yyyy", "formatType": "pbiFormat"}},
    "y": {"field": "Sales", "type": "quantitative", "axis": {"format": "$#0,,,.0bn", "formatType": "pbiFormat"}},
    "tooltip": [
      {"field": "Date", "type": "temporal", "format": "d MMM yyyy", "formatType": "pbiFormat"},
      {"field": "Sales", "type": "quantitative", "formatType": "pbiFormatAutoUnit"}
    ]
  }
}
```

The tooltip's `d MMM yyyy` is a standard Power BI date format string but was not exercised in Deneb here; the docs example (`formatting-values.md`) only shows `MMM yyyy`. Retest: paste the spec into a 2.0 visual and read the tooltip.

`format` may also be an object of `ValueFormatterOptions`, e.g. `{"format": "#0.0", "value": 1e9}` with `formatType: "pbiFormat"` (1e9 picks the billions unit). To reuse the measure's model format string, read `datum['Sales__format']` in a `calculate` with the `pbiFormat` expression function, or show `Sales__formatted` directly; both fields are always present on migrated and 1.9 visuals and opt-in on new 2.0 visuals. Offline renders with the deneb-pbir renderer only approximate these formatters; do not read their output as Power BI formatting.

## Standard Config

Use `examples/standard-config.json` as a ready-to-use config file with any of the above specs. Key settings: `autosize: fit`, `view.stroke: transparent`, `font: Segoe UI`, clean axis styling.

## Vega (Full) -- Basic Bar

For cases requiring signals, events, or fine-grained control:

```json
{
  "$schema": "https://vega.github.io/schema/vega/v6.json",
  "data": [{"name": "dataset"}],
  "padding": 5,
  "width": {"signal": "pbiContainerWidth - 25"},
  "height": {"signal": "pbiContainerHeight - 27"},
  "scales": [
    {"name": "xscale", "type": "band", "domain": {"data": "dataset", "field": "Category"}, "range": "width", "padding": 0.1},
    {"name": "yscale", "type": "linear", "domain": {"data": "dataset", "field": "Sales"}, "range": "height", "nice": true}
  ],
  "marks": [
    {
      "type": "rect",
      "from": {"data": "dataset"},
      "encode": {
        "enter": {
          "x": {"scale": "xscale", "field": "Category"},
          "width": {"scale": "xscale", "band": 1},
          "y": {"scale": "yscale", "field": "Sales"},
          "y2": {"scale": "yscale", "value": 0},
          "fill": {"signal": "pbiColor(0)"}
        }
      }
    }
  ]
}
```

Note: In Vega, `data` is an **array** `[{"name": "dataset"}]`, not an object. `pbiContainerWidth`/`pbiContainerHeight` are the legacy container signals (work on 1.9.x and every 2.x); `denebContainer.width`/`denebContainer.height` is the 2.0-only name. See the container signals note at the top of this file and `references/vega-patterns.md`.
