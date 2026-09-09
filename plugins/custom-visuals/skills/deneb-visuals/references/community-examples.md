# Deneb Community Examples

Organized by chart type. Retrieve specific examples when you need a pattern for a chart type.

## Deneb Template Format

Community examples come in three formats. Understand these to fetch and adapt them correctly.

### 1. Deneb Template JSON (`.deneb-template.json` or `.json`)

The most common format in community repos. A valid Vega/Vega-Lite spec with a `usermeta` block bolted on for Deneb's import/export workflow. This is the usermeta v2 shape Deneb 2.0 exports (validated against `https://deneb-viz.github.io/schema/deneb-template-usermeta-v2.json`, Verified 2026-09-08); most community templates still carry the older v1 shape described below it.

Retest: `python -c "import json,jsonschema;from jsonschema import Draft7Validator as V;s=json.load(open('deneb-template-usermeta-v2.json'));t=json.load(open('template.json'));print(list(V(s).iter_errors(t['usermeta'])))"` with the schema downloaded from the URL above (expects `[]`).

```json
{
  "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
  "usermeta": {
    "deneb": {
      "build": "2.0.0.0",
      "metaVersion": 2,
      "provider": "vegaLite",
      "providerVersion": "6.4.3"
    },
    "information": {
      "name": "Simple Bar Chart",
      "description": "Basic bar chart.",
      "author": "Example author",
      "uuid": "3f2c8a1e-6b7d-4c2a-9e1f-0a1b2c3d4e5f",
      "generated": "2026-09-08T00:00:00.000Z"
    },
    "datasets": {
      "dataset": [
        {
          "key": "__dataset.0__",
          "name": "Category",
          "description": "Categorical field on Y-axis",
          "type": "text",
          "kind": "column"
        },
        {
          "key": "__dataset.1__",
          "name": "Value",
          "description": "Numeric measure",
          "type": "numeric",
          "kind": "measure"
        }
      ]
    },
    "interactivity": {
      "tooltip": true,
      "contextMenu": true,
      "contextMenuSelector": true,
      "selection": false,
      "selectionMode": "simple",
      "highlight": false,
      "dataPointLimit": 50
    },
    "config": "{\"autosize\": {\"type\": \"fit\", \"contains\": \"padding\"}}"
  },
  "data": { "name": "dataset" },
  "mark": { "type": "bar", "tooltip": true },
  "encoding": {
    "y": { "field": "__dataset.0__", "type": "nominal" },
    "x": { "field": "__dataset.1__", "type": "quantitative" }
  }
}
```

Key elements:
- **`usermeta.deneb`** -- build version, `metaVersion` (2 for templates written by Deneb 2.0; 1 is still accepted and migrated on import), provider (`vega` or `vegaLite`), `providerVersion`
- **`usermeta.datasets.dataset`** -- field placeholder definitions. `key` (`__dataset.0__`, `__dataset.1__`, ...) maps to field references in the spec. `kind` is `column`, `measure`, `parameter` (a consolidated field parameter) or `any`. `type` is `text`, `numeric`, `dateTime`, `bool` or `other`. An optional per-entry `supportFieldConfiguration` carries the field's supporting-field flags
- **`usermeta.information`** -- metadata (name, author, description)
- **`usermeta.interactivity`** and **`usermeta.config`** -- optional; the config is a JSON string, not an object
- The actual spec (mark, encoding, layer, etc.) sits at the top level using placeholder keys

**Legacy v1 shape** (`metaVersion` 1, written by Deneb 1.x and by most community repos): a flat `usermeta.dataset` array whose keys are `__0__`, `__1__` (Deneb's own exports) or free-form names such as `__category__` (hand-written templates), and a v5 or older `$schema`. Deneb 2.0 imports v1 and rewrites index keys to `__dataset.N__`; free-form keys are not rewritten in the spec body, so substitute those offline (inferred from source, unverified in the UI; Retest in [capabilities.md, v1 (legacy)](capabilities.md#v1-legacy)).

### How to use a template

**To import into Deneb UI:** Use Deneb's built-in "New visual" > "Import from template" dialog. It reads `usermeta.datasets.dataset` (or the v1 `usermeta.dataset`) to prompt for field mappings.

**To inject into PBIR visual.json programmatically:**

1. Strip `usermeta` from the JSON (and the root `$schema`; `deneb_spec.py embed` strips it for you)
2. Replace placeholder keys (`__dataset.0__`, `__dataset.1__`, or the v1 `__0__` / `__category__`) with the display labels of your projections (`displayName` when set, otherwise `nativeQueryRef`), with `\ " . [ ]` replaced by `_`
3. Embed with `deneb_spec.py embed` from the `custom-visuals:deneb-pbir` skill; it wraps the spec as the single-quoted `jsonSpec` literal and doubles apostrophes (escaping rules in SKILL.md Step 3)
4. Parse the `usermeta.config` string (a pre-1.7 template has a top-level `config` object instead) and embed it as `jsonConfig`, not inside the spec

For a full terminal workflow (CLI bind commands, `kind`, the context-menu remap, breaking changes, pitfalls) see `references/advanced-patterns.md`.

**To create a new template from an existing spec:**

1. Replace hardcoded field names with placeholder keys (`__dataset.0__`, `__dataset.1__`, etc.; keys must match `__<dataset>.<index>__`, max 30 characters)
2. Add the `usermeta` block with `deneb` (`metaVersion` 2), `information`, and `datasets.dataset` sections
3. In `datasets.dataset`, define each placeholder with `key`, `name`, `description`, `type`, and `kind`
4. Keep `"data": {"name": "dataset"}` unchanged

### 2. Raw Spec JSON

A plain Vega or Vega-Lite spec without `usermeta`. Used by PBI-David/Deneb-Showcase (`Spec.json` files) and some standalone examples. Ready to inject directly after field name substitution.

### 3. Blog-embedded Spec

Vega/Vega-Lite JSON embedded in HTML blog posts (Thys van der Walt, Kerry Kolosko). Fetch the page and extract the spec from code blocks.

## Template Repositories

### How to Fetch

Each repo has a different file structure. Use these patterns to construct raw URLs:

| Repo | File Pattern | Raw URL Base | API to List |
|---|---|---|---|
| avatorl/Deneb-Vega-Templates | `{category}/{slug}.deneb-template.json` | `https://raw.githubusercontent.com/avatorl/Deneb-Vega-Templates/main/` | `api.github.com/repos/avatorl/Deneb-Vega-Templates/contents/{category}` |
| PowerBI-tips/Deneb-Templates | `templates/{Title Case Name}.json` | `https://raw.githubusercontent.com/PowerBI-tips/Deneb-Templates/main/` | `api.github.com/repos/PowerBI-tips/Deneb-Templates/contents/templates` |
| PBI-David/Deneb-Showcase | `{Title Case Dir}/Spec.json` | `https://raw.githubusercontent.com/PBI-David/Deneb-Showcase/main/` | `api.github.com/repos/PBI-David/Deneb-Showcase/contents` |
| clemviz/Deneb-Templates | `{file}.json` or `{subdir}/{file}.json` | `https://raw.githubusercontent.com/clemviz/Deneb-Templates/main/` | `api.github.com/repos/clemviz/Deneb-Templates/contents` |
| shadfrigui/vega-lite | `deneb-templates/{slug}/{slug}-deneb.json` | `https://raw.githubusercontent.com/shadfrigui/vega-lite/main/` | `api.github.com/repos/shadfrigui/vega-lite/contents/deneb-templates` |
| Giammaria/Vega-Visuals | `{dir}/` (contains `.vg.json`) | `https://raw.githubusercontent.com/Giammaria/Vega-Visuals/main/` | `api.github.com/repos/Giammaria/Vega-Visuals/contents` |

### Repository Index

| Repository | Author | Provider | Format | Count |
|---|---|---|---|---|
| [Deneb-Vega-Templates](https://github.com/avatorl/Deneb-Vega-Templates) | Andrzej Leszkiewicz | Vega | Template JSON | 50+ |
| [Deneb-Showcase](https://github.com/PBI-David/Deneb-Showcase) | PBI-David | Vega | Raw spec (`Spec.json`) | 28 |
| [Deneb-Templates](https://github.com/PowerBI-tips/Deneb-Templates) | PowerBI-tips | Vega-Lite | Template JSON | 57 |
| [Thys Templates](https://thysvdw.github.io/) | Thys van der Walt | Vega-Lite | Blog-embedded | 25 |
| [vega-lite](https://github.com/shadfrigui/vega-lite) | Shad Frigui | Vega-Lite | Template JSON | 27 |
| [Vega-Visuals](https://github.com/Giammaria/Vega-Visuals) | Giammaria | Vega | Raw spec (`.vg.json`) | 11 |
| [DataViz-Vega](https://github.com/avatorl/DataViz-Vega) | Andrzej Leszkiewicz | Vega | Raw spec | 31 |
| [Power-Bi-Deneb](https://github.com/Juan-Power-bi/Power-Bi-Deneb) | Juan-Power-bi | Vega-Lite | Template JSON | 11 |
| [Deneb-Templates](https://github.com/clemviz/Deneb-Templates) | clemviz | Vega-Lite | Template JSON | 10 |
| [deneb-templates](https://github.com/vdvoorder/deneb-templates) | vdvoorder | Vega-Lite | Template JSON | 3 |
| [deneb_examples](https://github.com/pmoldmann/deneb_examples) | pmoldmann | Vega-Lite | Template JSON (IBCS) | 4 |
| [PBIQueryous/Deneb](https://github.com/PBIQueryous/Deneb) | PBI Queryous | Mixed | Mixed | Various |
| [Flynnxx1/Deneb-Vega-Showcase](https://github.com/Flynnxx1/Deneb-Vega-Showcase) | Flynnxx1 | Mixed | Mixed | Various |
| [PMO_toolkit](https://github.com/DL0K-pbi/PMO_toolkit) | DL0K-pbi | Mixed | Mixed | PMO charts |

## Examples by Chart Type

Format column: **T** = Deneb Template JSON, **S** = Raw Spec JSON, **B** = Blog-embedded

### Bar / Column

| Example | Author | Provider | Fmt | Fetch URL |
|---|---|---|---|---|
| Bar Chart | Andrzej Leszkiewicz | Vega | T | `raw.githubusercontent.com/avatorl/Deneb-Vega-Templates/main/magnitude/bar-chart.deneb-template.json` |
| Ordered Bar Chart | Andrzej Leszkiewicz | Vega | T | `raw.githubusercontent.com/avatorl/Deneb-Vega-Templates/main/ranking/bar-chart-ordered.deneb-template.json` |
| Infographic Bar Chart | PBI-David | Vega | S | `raw.githubusercontent.com/PBI-David/Deneb-Showcase/main/Infographic%20Bar%20Chart/Spec.json` |
| Infographic Column Chart | PBI-David | Vega | S | `raw.githubusercontent.com/PBI-David/Deneb-Showcase/main/Infographic%20Column%20Chart/Spec.json` |
| Simple Bar Chart | PowerBI-tips | VL | T | `raw.githubusercontent.com/PowerBI-tips/Deneb-Templates/main/templates/Simple%20Bar%20Chart.json` |
| Compact Bar + Cross-Filter | PowerBI-tips | VL | T | `raw.githubusercontent.com/PowerBI-tips/Deneb-Templates/main/templates/Compact%20Bar%20Chart%20with%20Cross-Highlight%20Filter.json` |
| Stacked Bar TwoCategories | PowerBI-tips | VL | T | `raw.githubusercontent.com/PowerBI-tips/Deneb-Templates/main/templates/Stacked%20Bar%20TwoCategories.json` |
| Bar Chart | Thys van der Walt | VL | B | `https://thysvdw.github.io/posts/2-bar-chart/` |

### Bullet / Comparison / IBCS

| Example | Author | Provider | Fmt | Fetch URL |
|---|---|---|---|---|
| Bullet Graph | Andrzej Leszkiewicz | Vega | T | `raw.githubusercontent.com/avatorl/Deneb-Vega-Templates/main/magnitude/bullet-graph.deneb-template.json` |
| IBCS Three-Tier Chart | Andrzej Leszkiewicz | Vega | S | `raw.githubusercontent.com/avatorl/DataViz-Vega/main/ibcs-three-tier-chart/ibcs-three-tier-chart.json` |
| Actuals vs Forecasts Bullet | Shad Frigui | VL | T | `raw.githubusercontent.com/shadfrigui/vega-lite/main/deneb-templates/actuals-vs-forecasts-bullet-like-chart/actuals-vs-forecasts-bullet-like-chart-deneb.json` |
| Variance Chart | PBI-David | VL | S | `raw.githubusercontent.com/PBI-David/Deneb-Showcase/main/Variance%20Chart/Spec.json` |
| IBCS Absolute Comparison | pmoldmann | VL | T | `raw.githubusercontent.com/pmoldmann/deneb_examples/main/Two_Measure_Absolute_Compare/specification_pbi.json` |
| IBCS Vertical Waterfall | pmoldmann | VL | T | `raw.githubusercontent.com/pmoldmann/deneb_examples/main/ibcs_vertical_waterfall_with_start/ibcs_vertical_waterfall_with_start.json` |

### Line / Area / Time Series

| Example | Author | Provider | Fmt | Fetch URL |
|---|---|---|---|---|
| Line | Andrzej Leszkiewicz | Vega | T | `raw.githubusercontent.com/avatorl/Deneb-Vega-Templates/main/change-over-time/line.deneb-template.json` |
| Area | Andrzej Leszkiewicz | Vega | T | `raw.githubusercontent.com/avatorl/Deneb-Vega-Templates/main/change-over-time/area.deneb-template.json` |
| Column and Line | Andrzej Leszkiewicz | Vega | T | `raw.githubusercontent.com/avatorl/Deneb-Vega-Templates/main/change-over-time/column-and-line.deneb-template.json` |
| Brushable Line Chart | clemviz | VL | T | `raw.githubusercontent.com/clemviz/Deneb-Templates/main/deneb_template_brush_line.json` |
| Forecast Accuracy | PowerBI-tips | VL | T | `raw.githubusercontent.com/PowerBI-tips/Deneb-Templates/main/templates/Forecast%20Accuracy.json` |
| Patterned Area Between Lines | PowerBI-tips | VL | T | `raw.githubusercontent.com/PowerBI-tips/Deneb-Templates/main/templates/Patterned%20Area%20Between%20Lines.json` |
| Steamgraph | PowerBI-tips | VL | T | `raw.githubusercontent.com/PowerBI-tips/Deneb-Templates/main/templates/Steam%20Over%20Time.json` |
| Cumulative Line Chart | Thys van der Walt | VL | B | `https://thysvdw.github.io/posts/cumulative-line-chart/` |
| Temperature Line Area | Andrzej Leszkiewicz | Vega | S | `raw.githubusercontent.com/avatorl/DataViz-Vega/main/temperature-line-area/temperature-line-area.json` |

### Slope / Bump / Ranking

| Example | Author | Provider | Fmt | Fetch URL |
|---|---|---|---|---|
| Slope | Andrzej Leszkiewicz | Vega | T | `raw.githubusercontent.com/avatorl/Deneb-Vega-Templates/main/ranking/slope.deneb-template.json` |
| Bump | Andrzej Leszkiewicz | Vega | T | `raw.githubusercontent.com/avatorl/Deneb-Vega-Templates/main/ranking/bump.deneb-template.json` |
| Slope Chart with Labels | PowerBI-tips | VL | T | `raw.githubusercontent.com/PowerBI-tips/Deneb-Templates/main/templates/Slope%20Chart%20with%20Labels.json` |
| Rank Chart | Thys van der Walt | VL | B | `https://thysvdw.github.io/posts/the-one-with-the-rank-chart/` |

### KPI / Card

| Example | Author | Provider | Fmt | Fetch URL |
|---|---|---|---|---|
| Card Visual | Thys van der Walt | VL | B | `https://thysvdw.github.io/posts/1-card-visual/` |
| Conditional KPI Cards | PowerBI-tips | VL | T | `raw.githubusercontent.com/PowerBI-tips/Deneb-Templates/main/templates/Conditional%20KPI%20Cards.json` |
| KPI Card Area Gradient | clemviz | VL | T | `raw.githubusercontent.com/clemviz/Deneb-Templates/main/KPI_cards/deneb_kpi_card_area_gradient.json` |

### Scatter / Bubble / Beeswarm

| Example | Author | Provider | Fmt | Fetch URL |
|---|---|---|---|---|
| Scatterplot | Andrzej Leszkiewicz | Vega | T | `raw.githubusercontent.com/avatorl/Deneb-Vega-Templates/main/correlation/scatterplot.deneb-template.json` |
| Bubble Plot | Andrzej Leszkiewicz | Vega | T | `raw.githubusercontent.com/avatorl/Deneb-Vega-Templates/main/correlation/bubble-plot.deneb-template.json` |
| Connected Scatterplot | Andrzej Leszkiewicz | Vega | T | `raw.githubusercontent.com/avatorl/Deneb-Vega-Templates/main/correlation/connected-scatterplot.deneb-template.json` |
| S&P Beeswarm Chart | PBI-David | Vega | S | `raw.githubusercontent.com/PBI-David/Deneb-Showcase/main/S%26P%20Beeswarm%20Chart/Spec.json` |
| Cross-Highlighted Scatter | vdvoorder | VL | T | `raw.githubusercontent.com/vdvoorder/deneb-templates/main/cross-highlighted-scatter-chart/template.json` |
| Categorical Jittered Scatter | PowerBI-tips | VL | T | `raw.githubusercontent.com/PowerBI-tips/Deneb-Templates/main/templates/Categorical%20Jittered%20Scatter%20Mean%20Overlay.json` |

### Heatmap / Calendar

| Example | Author | Provider | Fmt | Fetch URL |
|---|---|---|---|---|
| Heatmap | Andrzej Leszkiewicz | Vega | T | `raw.githubusercontent.com/avatorl/Deneb-Vega-Templates/main/correlation/heatmap.deneb-template.json` |
| Calendar Heatmap | PBI-David | Vega | S | `raw.githubusercontent.com/PBI-David/Deneb-Showcase/main/Calendar%20Heatmap/Spec.json` |
| Calendar Heatmap + Histogram | clemviz | VL | T | `raw.githubusercontent.com/clemviz/Deneb-Templates/main/heatmaps/deneb_calendar_heatmap_histo.json` |
| Heatmap with Bars | PowerBI-tips | VL | T | `raw.githubusercontent.com/PowerBI-tips/Deneb-Templates/main/templates/Heatmap%20with%20Bars.json` |
| Warming Stripe | Andrzej Leszkiewicz | Vega | S | `raw.githubusercontent.com/avatorl/DataViz-Vega/main/warming-stripe/warming-stripe.json` |
| Calendar | Thys van der Walt | VL | B | `https://thysvdw.github.io/posts/the-one-with-the-calendar/` |

### Donut / Pie / Part-to-Whole

| Example | Author | Provider | Fmt | Fetch URL |
|---|---|---|---|---|
| Donut | Andrzej Leszkiewicz | Vega | T | `raw.githubusercontent.com/avatorl/Deneb-Vega-Templates/main/part-to-whole/donut.deneb-template.json` |
| Pie | Andrzej Leszkiewicz | Vega | T | `raw.githubusercontent.com/avatorl/Deneb-Vega-Templates/main/part-to-whole/pie.deneb-template.json` |
| Treemap | Andrzej Leszkiewicz | Vega | T | `raw.githubusercontent.com/avatorl/Deneb-Vega-Templates/main/part-to-whole/treemap.deneb-template.json` |
| Parliament Diagram | Andrzej Leszkiewicz | Vega | T | `raw.githubusercontent.com/avatorl/Deneb-Vega-Templates/main/part-to-whole/parliament-diagram.deneb-template.json` |
| TopN Donut Chart | PBI-David | Vega | S | `raw.githubusercontent.com/PBI-David/Deneb-Showcase/main/TopN%20Donut%20Chart/Spec.json` |
| Patterned Doughnut | PowerBI-tips | VL | T | `raw.githubusercontent.com/PowerBI-tips/Deneb-Templates/main/templates/Patterned%20Doughnut.json` |
| Waffle Charts | PBI-David | VL | S | `raw.githubusercontent.com/PBI-David/Deneb-Showcase/main/Waffle%20Charts/Spec.json` |
| Marimekko | Andrzej Leszkiewicz | Vega | T | `raw.githubusercontent.com/avatorl/Deneb-Vega-Templates/main/magnitude/marimekko.deneb-template.json` |

### Distribution (Boxplot / Violin / Histogram / Ridgeline)

| Example | Author | Provider | Fmt | Fetch URL |
|---|---|---|---|---|
| Boxplot | Andrzej Leszkiewicz | Vega | T | `raw.githubusercontent.com/avatorl/Deneb-Vega-Templates/main/distribution/boxplot.deneb-template.json` |
| Violin Plot | Andrzej Leszkiewicz | Vega | T | `raw.githubusercontent.com/avatorl/Deneb-Vega-Templates/main/distribution/violin-plot.deneb-template.json` |
| Histogram | Andrzej Leszkiewicz | Vega | T | `raw.githubusercontent.com/avatorl/Deneb-Vega-Templates/main/distribution/histogram.deneb-template.json` |
| Population Pyramid | Andrzej Leszkiewicz | Vega | T | `raw.githubusercontent.com/avatorl/Deneb-Vega-Templates/main/distribution/population-pyramid.deneb-template.json` |
| Raincloud Plot | PowerBI-tips | VL | T | `raw.githubusercontent.com/PowerBI-tips/Deneb-Templates/main/templates/Raincloud%20Plot%20v1.json` |
| Ridgeline Independent | PowerBI-tips | VL | T | `raw.githubusercontent.com/PowerBI-tips/Deneb-Templates/main/templates/Ridgeline%20Independent.json` |
| Boxplot | Thys van der Walt | VL | B | `https://thysvdw.github.io/posts/the-one-with-the-boxplot/` |

### Waterfall

| Example | Author | Provider | Fmt | Fetch URL |
|---|---|---|---|---|
| Waterfall | Andrzej Leszkiewicz | Vega | T | `raw.githubusercontent.com/avatorl/Deneb-Vega-Templates/main/flow/waterfall.deneb-template.json` |
| Enhanced Waterfall | PowerBI-tips | VL | T | `raw.githubusercontent.com/PowerBI-tips/Deneb-Templates/main/templates/Enhanced%20Waterfall.json` |

### Lollipop / Dumbbell / Comet

| Example | Author | Provider | Fmt | Fetch URL |
|---|---|---|---|---|
| Lollipop | Andrzej Leszkiewicz | Vega | T | `raw.githubusercontent.com/avatorl/Deneb-Vega-Templates/main/magnitude/lollipop.deneb-template.json` |
| Fancy Dumbbell | PowerBI-tips | VL | T | `raw.githubusercontent.com/PowerBI-tips/Deneb-Templates/main/templates/Fancy%20Dumb%20Bell.json` |
| Comet Chart | PowerBI-tips | VL | T | `raw.githubusercontent.com/PowerBI-tips/Deneb-Templates/main/templates/Comet%20Chart.json` |
| Dumbbell Chart | Thys van der Walt | VL | B | `https://thysvdw.github.io/posts/dumbbell-chart/` |

### Gantt / Timeline

| Example | Author | Provider | Fmt | Fetch URL |
|---|---|---|---|---|
| Gantt Chart | PBI-David | Vega | S | `raw.githubusercontent.com/PBI-David/Deneb-Showcase/main/Gantt%20Chart/Spec.json` |
| Simple Gantt Chart | PowerBI-tips | VL | T | `raw.githubusercontent.com/PowerBI-tips/Deneb-Templates/main/templates/Simple%20Gantt%20Chart.json` |
| Hierarchical Gantt | Giammaria | Vega | S | `raw.githubusercontent.com/Giammaria/Vega-Visuals/main/20240724-hierarchical-gantt-chart/` |
| Timeline | Thys van der Walt | VL | B | `https://thysvdw.github.io/posts/the-one-with-the-timeline/` |

### Network / Flow / Sankey

| Example | Author | Provider | Fmt | Fetch URL |
|---|---|---|---|---|
| Sankey | Andrzej Leszkiewicz | Vega | T | `raw.githubusercontent.com/avatorl/Deneb-Vega-Templates/main/flow/sankey.deneb-template.json` |
| Chord Diagram | Andrzej Leszkiewicz | Vega | T | `raw.githubusercontent.com/avatorl/Deneb-Vega-Templates/main/flow/chord.deneb-template.json` |
| Network | Andrzej Leszkiewicz | Vega | T | `raw.githubusercontent.com/avatorl/Deneb-Vega-Templates/main/flow/network.deneb-template.json` |
| Force Directed Graph | PBI-David | Vega | S | `raw.githubusercontent.com/PBI-David/Deneb-Showcase/main/Force%20Directed%20Graph/Spec.json` |
| Sankey Chart | PBI-David | Vega | S | `raw.githubusercontent.com/PBI-David/Deneb-Showcase/main/Sankey%20Chart/Spec.json` |
| Organisation Tree | PBI-David | Vega | S | `raw.githubusercontent.com/PBI-David/Deneb-Showcase/main/Organisation%20Tree%20Chart/Spec.json` |

### Radial / Radar / Spider

| Example | Author | Provider | Fmt | Fetch URL |
|---|---|---|---|---|
| Radar | Andrzej Leszkiewicz | Vega | T | `raw.githubusercontent.com/avatorl/Deneb-Vega-Templates/main/magnitude/radar.deneb-template.json` |
| Pancake Spider Chart | PBI-David | Vega | S | `raw.githubusercontent.com/PBI-David/Deneb-Showcase/main/Pancake%20Spider%20Chart/Spec.json` |
| Circular Radial Chart | PowerBI-tips | VL | T | `raw.githubusercontent.com/PowerBI-tips/Deneb-Templates/main/templates/Circular%20Radial%20Chart%20Variant%202.json` |

### Map / Spatial

| Example | Author | Provider | Fmt | Fetch URL |
|---|---|---|---|---|
| Choropleth | Andrzej Leszkiewicz | Vega | T | `raw.githubusercontent.com/avatorl/Deneb-Vega-Templates/main/spatial/choropleth.deneb-template.json` |
| Dot Density Map | Andrzej Leszkiewicz | Vega | T | `raw.githubusercontent.com/avatorl/Deneb-Vega-Templates/main/spatial/dot-density.deneb-template.json` |
| Hex Map with Sparkline | PowerBI-tips | VL | T | `raw.githubusercontent.com/PowerBI-tips/Deneb-Templates/main/templates/Hex%20Map%20with%20Sparkline.json` |
| Spiked Map | PowerBI-tips | VL | T | `raw.githubusercontent.com/PowerBI-tips/Deneb-Templates/main/templates/Spiked%20Map.json` |
| Earthquakes Globe | Andrzej Leszkiewicz | Vega | S | `raw.githubusercontent.com/avatorl/DataViz-Vega/main/earthquakes-globe/earthquakes-globe.json` |

### Tree / Hierarchy

| Example | Author | Provider | Fmt | Fetch URL |
|---|---|---|---|---|
| Radial Tree | PowerBI-tips | Vega | T | `raw.githubusercontent.com/PowerBI-tips/Deneb-Templates/main/templates/Redial%20Tree.json` |
| Simple Tree | PowerBI-tips | Vega | T | `raw.githubusercontent.com/PowerBI-tips/Deneb-Templates/main/templates/Simple%20Tree.json` |
| Tidy Tree Area | PowerBI-tips | Vega | T | `raw.githubusercontent.com/PowerBI-tips/Deneb-Templates/main/templates/Tidy%20Tree%20Area.json` |
| Zoomable Circle Packing | Giammaria | Vega | S | `raw.githubusercontent.com/Giammaria/Vega-Visuals/main/20231203-zoomable-circle-packing/` |

### Sparkline / Small Multiples

| Example | Author | Provider | Fmt | Fetch URL |
|---|---|---|---|---|
| Sparkline | Thys van der Walt | VL | B | `https://thysvdw.github.io/posts/the-one-with-sparkline/` |
| Small Multiple Line | Andrzej Leszkiewicz | Vega | S | `raw.githubusercontent.com/avatorl/DataViz-Vega/main/small-multiple-line-chart/small-multiple-line-chart-bike.json` |
| Trellis Dot Plot | PowerBI-tips | VL | T | `raw.githubusercontent.com/PowerBI-tips/Deneb-Templates/main/templates/Trellis%20Dot%20Plot.json` |

## Videos and Tutorials

| Resource | Author | URL |
|---|---|---|
| Sentido Analitica Playlist | Sentido Analitica | https://www.youtube.com/playlist?list=PLf18HMTT3dFhM6EI8Oim-cSYbhHaAvgZs |
| Power BI Guy Playlist | Power BI Guy | https://www.youtube.com/playlist?list=PL6oIJxyQvMGTxh4tREeKflcKVlOfGdyim |
| PowerBI.tips Season 3 | PowerBI.tips | https://www.youtube.com/playlist?list=PLn1m_aBmgsbEhKYRXC6Tq3e2FJubEND9b |
| Enterprise DNA Course | Enterprise DNA | https://portal.enterprisedna.co/p/introduction-deneb |
| PBI Queryous (Medium) | PBI Queryous | https://medium.com/@pbiqueryous |

## AI Tools

| Tool | URL |
|---|---|
| Vicky Vega (Custom GPT for Vega specs) | https://bit.ly/VickyVega |
