# Vega Chart Patterns for Deneb

Common Vega chart patterns for Power BI Deneb visuals. All specs use `"data": [{"name": "dataset"}]` (array form) and Vega v6, bundled since Deneb 1.8: Deneb 2.0.0.0 ships Vega 6.4.0, Deneb 1.9.x shipped 6.2.0 (Verified 2026-09-08 against Deneb's `package.json` and the docs changelog "Vega Updates"). Use `pbiColor()` for theme colors.

Retest: `gh api repos/deneb-viz/deneb/contents/package.json --jq '.content' | base64 -d | grep '"vega"'`

Every block below carries a root `$schema` for editors and the offline renderer; it never goes into `jsonSpec` (`deneb_spec.py embed` strips it; strip it yourself if you hand-embed).

### Container signals

Every pattern below sizes itself with `pbiContainerWidth` / `pbiContainerHeight`. Those are the legacy names: they work natively on Deneb 1.9.x and on every 2.x build, where Deneb rewrites them to the 2.0 names at parse time and logs one warning per session (removal target is 3.0). The 2.0 name is the `denebContainer` signal object with `width`, `height`, `scrollWidth`, `scrollHeight`, `scrollTop` and `scrollLeft`; it does not exist in 1.9.x, so a spec that references `denebContainer.width` should fail to parse there (inferred from Vega's parser, never reproduced in a Desktop running Deneb 1.9.1.0, so it is unverified; see the [compatibility matrix](deneb-2-migration.md#compatibility-matrix) for the Retest). Rule: if the visual.json you are editing carries `developer.version` 2.0.0.0 or later, use `denebContainer.width` / `denebContainer.height`; if it carries a 1.x stamp, or the target report has not been confirmed on 2.0, keep the legacy names. Flip a finished spec either way with `deneb_spec.py migrate --signals modern|legacy`. Details and the compatibility matrix: [deneb-2-migration.md, Authoring rules during the transition](deneb-2-migration.md#authoring-rules-during-the-transition).

## Vega Spec Anatomy

Every Vega spec follows this structure:

```json
{
  "$schema": "https://vega.github.io/schema/vega/v6.json",
  "data": [{"name": "dataset"}],
  "width": {"signal": "pbiContainerWidth - 25"},
  "height": {"signal": "pbiContainerHeight - 27"},
  "padding": 5,
  "signals": [],
  "scales": [],
  "axes": [],
  "legends": [],
  "marks": []
}
```

Key differences from Vega-Lite:
- `data` is an **array** of named datasets, not a single object
- Scales, axes, legends are explicit (not inferred from encoding)
- Marks use `encode` blocks with `enter`/`update`/`hover` sets
- Signals enable reactive variables, events, and interactions
- Transforms are defined inside data entries, not at top level
- Full control over every visual element

## Encode Blocks

Marks use three encoding sets:

| Set | When Applied |
|-----|-------------|
| `enter` | First time a mark is rendered (initial values) |
| `update` | Every re-render (reactive to data/signal changes) |
| `hover` | On pointer hover (optional, reverts to `update` on exit) |

Values reference scales, fields, signals, or constants:

```json
"encode": {
  "enter": {
    "x": {"scale": "xscale", "field": "Category"},
    "fill": {"signal": "pbiColor(0)"}
  },
  "update": {
    "fillOpacity": {"value": 1}
  },
  "hover": {
    "fillOpacity": {"value": 0.5}
  }
}
```

## Bar Chart (Vertical)

```json
{
  "$schema": "https://vega.github.io/schema/vega/v6.json",
  "data": [{"name": "dataset"}],
  "padding": 5,
  "width": {"signal": "pbiContainerWidth - 25"},
  "height": {"signal": "pbiContainerHeight - 27"},
  "scales": [
    {
      "name": "xscale",
      "type": "band",
      "domain": {"data": "dataset", "field": "Category"},
      "range": "width",
      "padding": 0.1,
      "round": true
    },
    {
      "name": "yscale",
      "type": "linear",
      "domain": {"data": "dataset", "field": "Sales"},
      "range": "height",
      "nice": true,
      "zero": true
    }
  ],
  "axes": [
    {"orient": "bottom", "scale": "xscale"},
    {"orient": "left", "scale": "yscale"}
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
          "cornerRadiusTopLeft": {"value": 4},
          "cornerRadiusTopRight": {"value": 4}
        },
        "update": {
          "fill": {"signal": "pbiColor(0)"}
        },
        "hover": {
          "fill": {"signal": "pbiColor(0, -0.3)"}
        }
      }
    }
  ]
}
```

## Bar Chart (Horizontal)

```json
{
  "$schema": "https://vega.github.io/schema/vega/v6.json",
  "data": [{"name": "dataset"}],
  "padding": 5,
  "width": {"signal": "pbiContainerWidth - 25"},
  "height": {"signal": "pbiContainerHeight - 27"},
  "scales": [
    {
      "name": "yscale",
      "type": "band",
      "domain": {"data": "dataset", "field": "Category", "sort": {"op": "max", "field": "Sales", "order": "descending"}},
      "range": "height",
      "padding": 0.1
    },
    {
      "name": "xscale",
      "type": "linear",
      "domain": {"data": "dataset", "field": "Sales"},
      "range": "width",
      "nice": true,
      "zero": true
    }
  ],
  "axes": [
    {"orient": "bottom", "scale": "xscale"},
    {"orient": "left", "scale": "yscale"}
  ],
  "marks": [
    {
      "type": "rect",
      "from": {"data": "dataset"},
      "encode": {
        "enter": {
          "y": {"scale": "yscale", "field": "Category"},
          "height": {"scale": "yscale", "band": 1},
          "x": {"scale": "xscale", "field": "Sales"},
          "x2": {"scale": "xscale", "value": 0},
          "cornerRadiusTopRight": {"value": 4},
          "cornerRadiusBottomRight": {"value": 4}
        },
        "update": {
          "fill": {"signal": "pbiColor(0)"}
        },
        "hover": {
          "fill": {"signal": "pbiColor(0, -0.3)"}
        }
      }
    }
  ]
}
```

## Line Chart (Multi-Series)

```json
{
  "$schema": "https://vega.github.io/schema/vega/v6.json",
  "data": [{"name": "dataset"}],
  "padding": 5,
  "width": {"signal": "pbiContainerWidth - 25"},
  "height": {"signal": "pbiContainerHeight - 27"},
  "scales": [
    {
      "name": "x",
      "type": "point",
      "domain": {"data": "dataset", "field": "Date"},
      "range": "width"
    },
    {
      "name": "y",
      "type": "linear",
      "domain": {"data": "dataset", "field": "Value"},
      "range": "height",
      "nice": true,
      "zero": true
    },
    {
      "name": "color",
      "type": "ordinal",
      "domain": {"data": "dataset", "field": "Series"},
      "range": {"scheme": "pbiColorNominal"}
    }
  ],
  "axes": [
    {"orient": "bottom", "scale": "x"},
    {"orient": "left", "scale": "y"}
  ],
  "legends": [
    {"stroke": "color", "orient": "top", "direction": "horizontal"}
  ],
  "marks": [
    {
      "type": "group",
      "from": {
        "facet": {
          "name": "series",
          "data": "dataset",
          "groupby": "Series"
        }
      },
      "marks": [
        {
          "type": "line",
          "from": {"data": "series"},
          "encode": {
            "enter": {
              "x": {"scale": "x", "field": "Date"},
              "y": {"scale": "y", "field": "Value"},
              "stroke": {"scale": "color", "field": "Series"},
              "strokeWidth": {"value": 2}
            },
            "update": {
              "interpolate": {"value": "monotone"},
              "strokeOpacity": {"value": 1}
            },
            "hover": {
              "strokeOpacity": {"value": 0.5}
            }
          }
        }
      ]
    }
  ]
}
```

## Scatter Plot

```json
{
  "$schema": "https://vega.github.io/schema/vega/v6.json",
  "data": [{"name": "dataset"}],
  "padding": 5,
  "width": {"signal": "pbiContainerWidth - 25"},
  "height": {"signal": "pbiContainerHeight - 27"},
  "scales": [
    {
      "name": "x",
      "type": "linear",
      "domain": {"data": "dataset", "field": "Revenue"},
      "range": "width",
      "nice": true,
      "zero": true
    },
    {
      "name": "y",
      "type": "linear",
      "domain": {"data": "dataset", "field": "Profit"},
      "range": "height",
      "nice": true,
      "zero": true
    },
    {
      "name": "size",
      "type": "linear",
      "domain": {"data": "dataset", "field": "Quantity"},
      "range": [16, 400],
      "zero": true
    },
    {
      "name": "color",
      "type": "ordinal",
      "domain": {"data": "dataset", "field": "Category"},
      "range": {"scheme": "pbiColorNominal"}
    }
  ],
  "axes": [
    {"orient": "bottom", "scale": "x", "grid": true, "domain": false, "title": "Revenue"},
    {"orient": "left", "scale": "y", "grid": true, "domain": false, "title": "Profit"}
  ],
  "marks": [
    {
      "type": "symbol",
      "from": {"data": "dataset"},
      "encode": {
        "enter": {
          "x": {"scale": "x", "field": "Revenue"},
          "y": {"scale": "y", "field": "Profit"},
          "size": {"scale": "size", "field": "Quantity"},
          "shape": {"value": "circle"},
          "fill": {"scale": "color", "field": "Category"},
          "opacity": {"value": 0.7},
          "tooltip": {"signal": "datum"}
        },
        "hover": {
          "opacity": {"value": 1},
          "strokeWidth": {"value": 2},
          "stroke": {"value": "#333"}
        }
      }
    }
  ]
}
```

## Donut Chart

```json
{
  "$schema": "https://vega.github.io/schema/vega/v6.json",
  "data": [
    {
      "name": "dataset",
      "transform": [
        {"type": "pie", "field": "Sales", "sort": true}
      ]
    }
  ],
  "width": {"signal": "pbiContainerWidth"},
  "height": {"signal": "pbiContainerHeight"},
  "autosize": "none",
  "scales": [
    {
      "name": "color",
      "type": "ordinal",
      "domain": {"data": "dataset", "field": "Category"},
      "range": {"scheme": "pbiColorNominal"}
    }
  ],
  "legends": [
    {"fill": "color", "orient": "right"}
  ],
  "marks": [
    {
      "type": "arc",
      "from": {"data": "dataset"},
      "encode": {
        "enter": {
          "x": {"signal": "pbiContainerWidth / 2"},
          "y": {"signal": "pbiContainerHeight / 2"},
          "fill": {"scale": "color", "field": "Category"},
          "startAngle": {"field": "startAngle"},
          "endAngle": {"field": "endAngle"},
          "innerRadius": {"signal": "min(pbiContainerWidth, pbiContainerHeight) * 0.25"},
          "outerRadius": {"signal": "min(pbiContainerWidth, pbiContainerHeight) * 0.45"},
          "cornerRadius": {"value": 2},
          "tooltip": {"signal": "datum"}
        },
        "update": {
          "fillOpacity": {"value": 1}
        },
        "hover": {
          "fillOpacity": {"value": 0.8}
        }
      }
    }
  ]
}
```

## Stacked Bar Chart

```json
{
  "$schema": "https://vega.github.io/schema/vega/v6.json",
  "data": [
    {
      "name": "dataset",
      "transform": [
        {
          "type": "stack",
          "groupby": ["Date"],
          "sort": {"field": "Region"},
          "field": "Sales"
        }
      ]
    }
  ],
  "padding": 5,
  "width": {"signal": "pbiContainerWidth - 25"},
  "height": {"signal": "pbiContainerHeight - 27"},
  "scales": [
    {
      "name": "x",
      "type": "band",
      "domain": {"data": "dataset", "field": "Date"},
      "range": "width"
    },
    {
      "name": "y",
      "type": "linear",
      "domain": {"data": "dataset", "field": "y1"},
      "range": "height",
      "nice": true,
      "zero": true
    },
    {
      "name": "color",
      "type": "ordinal",
      "domain": {"data": "dataset", "field": "Region"},
      "range": {"scheme": "pbiColorNominal"}
    }
  ],
  "axes": [
    {"orient": "bottom", "scale": "x"},
    {"orient": "left", "scale": "y"}
  ],
  "legends": [
    {"fill": "color", "orient": "top", "direction": "horizontal"}
  ],
  "marks": [
    {
      "type": "rect",
      "from": {"data": "dataset"},
      "encode": {
        "enter": {
          "x": {"scale": "x", "field": "Date"},
          "width": {"scale": "x", "band": 1, "offset": -1},
          "y": {"scale": "y", "field": "y0"},
          "y2": {"scale": "y", "field": "y1"},
          "fill": {"scale": "color", "field": "Region"}
        },
        "update": {
          "fillOpacity": {"value": 1}
        },
        "hover": {
          "fillOpacity": {"value": 0.7}
        }
      }
    }
  ]
}
```

## Heatmap

```json
{
  "$schema": "https://vega.github.io/schema/vega/v6.json",
  "data": [{"name": "dataset"}],
  "padding": 5,
  "width": {"signal": "pbiContainerWidth - 25"},
  "height": {"signal": "pbiContainerHeight - 27"},
  "scales": [
    {
      "name": "x",
      "type": "band",
      "domain": {"data": "dataset", "field": "Day"},
      "range": "width"
    },
    {
      "name": "y",
      "type": "band",
      "domain": {"data": "dataset", "field": "Hour"},
      "range": "height"
    },
    {
      "name": "color",
      "type": "linear",
      "domain": {"data": "dataset", "field": "Value"},
      "range": {"scheme": "pbiColorLinear"},
      "zero": false,
      "nice": true
    }
  ],
  "axes": [
    {"orient": "bottom", "scale": "x", "domain": false, "ticks": false},
    {"orient": "left", "scale": "y", "domain": false, "ticks": false}
  ],
  "legends": [
    {"fill": "color", "type": "gradient", "gradientLength": {"signal": "height - 16"}}
  ],
  "marks": [
    {
      "type": "rect",
      "from": {"data": "dataset"},
      "encode": {
        "enter": {
          "x": {"scale": "x", "field": "Day"},
          "width": {"scale": "x", "band": 1},
          "y": {"scale": "y", "field": "Hour"},
          "height": {"scale": "y", "band": 1},
          "fill": {"scale": "color", "field": "Value"},
          "tooltip": {"signal": "datum"}
        }
      }
    }
  ]
}
```

## Area Chart

```json
{
  "$schema": "https://vega.github.io/schema/vega/v6.json",
  "data": [{"name": "dataset"}],
  "padding": 5,
  "width": {"signal": "pbiContainerWidth - 25"},
  "height": {"signal": "pbiContainerHeight - 27"},
  "scales": [
    {
      "name": "x",
      "type": "point",
      "domain": {"data": "dataset", "field": "Date"},
      "range": "width"
    },
    {
      "name": "y",
      "type": "linear",
      "domain": {"data": "dataset", "field": "Value"},
      "range": "height",
      "nice": true,
      "zero": true
    }
  ],
  "axes": [
    {"orient": "bottom", "scale": "x"},
    {"orient": "left", "scale": "y"}
  ],
  "marks": [
    {
      "type": "area",
      "from": {"data": "dataset"},
      "encode": {
        "enter": {
          "x": {"scale": "x", "field": "Date"},
          "y": {"scale": "y", "field": "Value"},
          "y2": {"scale": "y", "value": 0},
          "fill": {"signal": "pbiColor(0)"},
          "interpolate": {"value": "monotone"}
        },
        "update": {
          "fillOpacity": {"value": 0.6}
        },
        "hover": {
          "fillOpacity": {"value": 0.3}
        }
      }
    },
    {
      "type": "line",
      "from": {"data": "dataset"},
      "encode": {
        "enter": {
          "x": {"scale": "x", "field": "Date"},
          "y": {"scale": "y", "field": "Value"},
          "stroke": {"signal": "pbiColor(0)"},
          "strokeWidth": {"value": 2},
          "interpolate": {"value": "monotone"}
        }
      }
    }
  ]
}
```

## Lollipop Chart

```json
{
  "$schema": "https://vega.github.io/schema/vega/v6.json",
  "data": [{"name": "dataset"}],
  "padding": 5,
  "width": {"signal": "pbiContainerWidth - 25"},
  "height": {"signal": "pbiContainerHeight - 27"},
  "scales": [
    {
      "name": "yscale",
      "type": "band",
      "domain": {"data": "dataset", "field": "Category", "sort": {"op": "max", "field": "Value", "order": "descending"}},
      "range": "height",
      "padding": 0.3
    },
    {
      "name": "xscale",
      "type": "linear",
      "domain": {"data": "dataset", "field": "Value"},
      "range": "width",
      "nice": true,
      "zero": true
    }
  ],
  "axes": [
    {"orient": "bottom", "scale": "xscale"},
    {"orient": "left", "scale": "yscale", "ticks": false, "domain": false}
  ],
  "marks": [
    {
      "type": "rule",
      "from": {"data": "dataset"},
      "encode": {
        "enter": {
          "y": {"scale": "yscale", "field": "Category", "band": 0.5},
          "x": {"scale": "xscale", "value": 0},
          "x2": {"scale": "xscale", "field": "Value"},
          "stroke": {"signal": "pbiColor(0)"},
          "strokeWidth": {"value": 2}
        }
      }
    },
    {
      "type": "symbol",
      "from": {"data": "dataset"},
      "encode": {
        "enter": {
          "y": {"scale": "yscale", "field": "Category", "band": 0.5},
          "x": {"scale": "xscale", "field": "Value"},
          "fill": {"signal": "pbiColor(0)"},
          "size": {"value": 100},
          "shape": {"value": "circle"}
        }
      }
    }
  ]
}
```

## Cross-Filtering Pattern (Vega)

When `enableSelection` is true, use `__selected__` to control mark opacity:

```json
"marks": [
  {
    "type": "rect",
    "from": {"data": "dataset"},
    "encode": {
      "update": {
        "fillOpacity": [
          {"test": "datum.__selected__ == 'off'", "value": 0.3},
          {"value": 1}
        ]
      }
    }
  }
]
```

## Field Parameters (Consolidated, Deneb 2.0)

With `stateManagement.consolidateFieldParameters` on, a field parameter arrives as ONE array-valued column named after the parameter (its display name, not a component's), one entry per selected component in data-view order, plus companion arrays: `<Parameter>__names` (component display names, opt-in) and `__highlight`, `__highlightStatus`, `__highlightComparator`, `__format`, `__formatted` (all arrays). Use a `flatten` transform to get one row per component; `__row__` is preserved, so tooltips and cross-filtering keep resolving. Pattern from the Deneb docs (`field-parameters.md`, "Working with Array Data"):

```json
{
  "data": [
    {"name": "dataset"},
    {
      "name": "flattened",
      "source": "dataset",
      "transform": [
        {"type": "flatten", "fields": ["Metric", "Metric__names"]}
      ]
    }
  ],
  "scales": [
    {"name": "x", "type": "linear", "domain": {"data": "flattened", "field": "Metric"}, "range": "width", "nice": true, "zero": true},
    {"name": "y", "type": "band", "domain": {"data": "flattened", "field": "Metric__names"}, "range": "height", "padding": 0.2},
    {"name": "color", "type": "ordinal", "domain": {"data": "flattened", "field": "Metric__names"}, "range": {"scheme": "pbiColorNominal"}}
  ],
  "axes": [
    {"orient": "bottom", "scale": "x"},
    {"orient": "left", "scale": "y"}
  ],
  "marks": [
    {
      "type": "rect",
      "from": {"data": "flattened"},
      "encode": {
        "update": {
          "y": {"scale": "y", "field": "Metric__names"},
          "height": {"scale": "y", "band": 1},
          "x": {"scale": "x", "value": 0},
          "x2": {"scale": "x", "field": "Metric"},
          "fill": {"scale": "color", "field": "Metric__names"},
          "tooltip": {"signal": "datum"}
        }
      }
    }
  ]
}
```

Rules that bite:

- Reference the parameter's display name (`Metric`), never a component's; a single-select slicer gives one-element arrays, which Vega flattens the same way
- `Metric__names` is opt-in: set `names: true` for the parameter's entry in `supportFieldConfiguration`, or the field is absent and the `y` scale domain is empty
- Consolidation is 2.0-only. A visual.json with a real spec, no `denebMetaVersion` and no `supportFieldConfiguration` is classified as a migrated 1.x project on first open under 2.0 and consolidation is pinned OFF, so `flatten` on the parameter name finds nothing (a configuration without the version stamp is the half-stamped row in `references/pbir-structure.md`, which is not legacy). Stamp `denebMetaVersion '2'`, `consolidateFieldParameters true` and an explicit `supportFieldConfiguration` together (never one of them alone), and expect pass-through (ordinary columns and measures) on 1.9.x. See [deneb-2-migration.md](deneb-2-migration.md#authoring-rules-during-the-transition)
- Component order follows the data view, not the parameter table; there is no custom sort
- In PBIR the parameter's currently selected component field(s) are bound as ordinary projections, each carrying a `displayName` (in the Deneb sample workbook Desktop wrote the component's own name, `Species`, on one visual and the DAX alias, `Series`, on the other, so it is the label the component is expanded under, not the parameter's name), plus a hand-authored `visual.query.queryState.dataset.fieldParameters[]` entry whose `parameterExpr` names the parameter table's column and whose `index`/`length` cover those component projections; the parameter table's column itself is not a projection. `pbir visuals bind` has no field-parameter option, so that entry is hand-authored (pbir 0.9.29, Verified 2026-09-08). The observed Desktop-saved shape is in the [Template Round-Trip section of advanced-patterns.md](advanced-patterns.md#template-round-trip-terminal-import)
  - Retest: `pbir visuals bind --help` and look for a field-parameter option

## Formatting with `pbiFormat`

`pbiFormat(value, format, options = {})` applies a Power BI format string (not d3) in the report locale; `pbiFormatAutoUnit(value, format?)` picks the nearest display unit (K, M, bn) like the Auto unit does. Both are Vega expression functions registered by Deneb (since well before 2.0), so they work in any `signal` expression, including axis label encodes:

```json
"axes": [
  {
    "orient": "left",
    "scale": "yscale",
    "encode": {
      "labels": {
        "update": {
          "text": {"signal": "pbiFormat(datum.value, '$#0,,,.0bn')"}
        }
      }
    }
  }
],
"marks": [
  {
    "type": "text",
    "from": {"data": "dataset"},
    "encode": {
      "update": {
        "text": {"signal": "pbiFormatAutoUnit(datum['Sales'])"},
        "tooltip": {"signal": "{'Sales': pbiFormat(datum['Sales'], {format: '#,0.0', value: 1e6, cultureSelector: 'en-GB'})}"}
      }
    }
  }
]
```

`options` accepts any `ValueFormatterOptions` key: `format` (overrides the positional string), `precision`, `value` (1e3, 1e6, 1e9, 1e12 or a live value to pick the unit), `cultureSelector` (overrides the report locale). When a measure's own model format string is wanted, read it from `datum['Sales__format']` (present on migrated and 1.9 visuals; opt-in on new 2.0 visuals) or use the pre-formatted `datum['Sales__formatted']` directly. Offline rendering with the deneb-pbir renderer only approximates this function; treat its text output as a shape check, not as Power BI formatting.

## Available Transforms

Key Vega transforms useful in Deneb:

| Transform | Purpose |
|-----------|---------|
| `aggregate` | Group and summarize data |
| `bin` | Discretize numeric values |
| `collect` | Sort data objects |
| `filter` | Filter with predicate expression |
| `flatten` | Expand array fields; the transform for consolidated field parameters (`__row__` survives it) |
| `fold` | Pivot columns to key/value pairs |
| `formula` | Compute derived fields |
| `joinaggregate` | Add aggregate values without grouping |
| `lookup` | Join datasets by key |
| `pie` | Compute angular layout |
| `stack` | Compute stacked positions |
| `window` | Running calculations (rank, lag, lead) |
| `wordcloud` | Word cloud layout |
| `force` | Force-directed layout |
| `tree` | Tree layout (node-link) |
| `treemap` | Treemap layout |
| `voronoi` | Voronoi diagram |

## Scale Types Quick Reference

| Type | Domain | Range | Use |
|------|--------|-------|-----|
| `linear` | Continuous | Continuous | Quantitative axes |
| `log` | Continuous (>0) | Continuous | Exponential data |
| `pow` | Continuous | Continuous | Power transforms |
| `time` / `utc` | Temporal | Continuous | Date axes |
| `band` | Discrete | Continuous | Bar chart categories |
| `point` | Discrete | Continuous | Scatter/line categories |
| `ordinal` | Discrete | Discrete | Color by category |
| `quantize` | Continuous | Discrete | Choropleth bins |
| `threshold` | Arbitrary cuts | Discrete | Custom breakpoints |

## Bullet Chart (Faceted with Target)

Faceted bar + tick mark pattern adapted from a real Power BI report. Each row shows a category with a value bar and a prior-year target tick:

```json
{
  "$schema": "https://vega.github.io/schema/vega/v6.json",
  "data": [
    {
      "name": "dataset",
      "transform": [
        {"type": "window", "ops": ["rank"], "as": ["rank"], "sort": {"field": "Value", "order": "descending"}},
        {"type": "filter", "expr": "datum.rank <= 10"}
      ]
    },
    {
      "name": "faceted",
      "source": "dataset",
      "transform": [
        {"type": "collect", "sort": {"field": "Value", "order": "descending"}}
      ]
    }
  ],
  "width": {"signal": "pbiContainerWidth - 25"},
  "height": {"signal": "pbiContainerHeight - 27"},
  "padding": 5,
  "scales": [
    {
      "name": "yscale",
      "type": "band",
      "domain": {"data": "faceted", "field": "Category"},
      "range": "height",
      "padding": 0.3
    },
    {
      "name": "xscale",
      "type": "linear",
      "domain": {"data": "faceted", "fields": ["Value", "Target"]},
      "range": "width",
      "nice": true,
      "zero": true
    }
  ],
  "axes": [
    {"orient": "bottom", "scale": "xscale", "tickCount": 5},
    {"orient": "left", "scale": "yscale", "ticks": false, "domain": false}
  ],
  "marks": [
    {
      "type": "rect",
      "from": {"data": "faceted"},
      "encode": {
        "enter": {
          "y": {"scale": "yscale", "field": "Category", "band": 0.25},
          "height": {"scale": "yscale", "band": 0.5},
          "x": {"scale": "xscale", "value": 0},
          "x2": {"scale": "xscale", "field": "Value"},
          "fill": {"signal": "pbiColor(0, 0.7)"},
          "cornerRadiusTopRight": {"value": 2},
          "cornerRadiusBottomRight": {"value": 2}
        }
      }
    },
    {
      "type": "rule",
      "from": {"data": "faceted"},
      "encode": {
        "enter": {
          "y": {"scale": "yscale", "field": "Category", "band": 0.1},
          "y2": {"scale": "yscale", "field": "Category", "band": 0.9},
          "x": {"scale": "xscale", "field": "Target"},
          "stroke": {"signal": "pbiColor(0, -0.5)"},
          "strokeWidth": {"value": 2}
        }
      }
    },
    {
      "type": "text",
      "from": {"data": "faceted"},
      "encode": {
        "enter": {
          "y": {"scale": "yscale", "field": "Category", "band": 0.5},
          "x": {"scale": "xscale", "field": "Value", "offset": 5},
          "text": {"signal": "format(datum.Value, ',.0f')"},
          "fill": {"signal": "pbiColor(0, -0.3)"},
          "baseline": {"value": "middle"},
          "fontSize": {"value": 10}
        }
      }
    }
  ]
}
```

Fields: `Category` (nominal), `Value` (quantitative -- current), `Target` (quantitative -- comparison).

## KPI Card (Layered Text)

Multi-line KPI display showing a headline value, subtitle, and percentage change:

```json
{
  "$schema": "https://vega.github.io/schema/vega/v6.json",
  "data": [
    {
      "name": "dataset",
      "transform": [
        {"type": "formula", "as": "change", "expr": "(datum.Value - datum.Target) / datum.Target"}
      ]
    }
  ],
  "width": {"signal": "pbiContainerWidth"},
  "height": {"signal": "pbiContainerHeight"},
  "autosize": "none",
  "marks": [
    {
      "type": "text",
      "from": {"data": "dataset"},
      "encode": {
        "enter": {
          "x": {"signal": "width / 2"},
          "y": {"value": 30},
          "text": {"value": "Value vs Target"},
          "fill": {"value": "#666666"},
          "fontSize": {"value": 14},
          "align": {"value": "center"},
          "baseline": {"value": "middle"}
        }
      }
    },
    {
      "type": "text",
      "from": {"data": "dataset"},
      "encode": {
        "enter": {
          "x": {"signal": "width / 2"},
          "y": {"signal": "height / 2"},
          "text": {"signal": "format(datum.Value, ',.0f')"},
          "fill": [
            {"test": "datum.change >= 0", "signal": "pbiColor(0)"},
            {"signal": "pbiColor('negative')"}
          ],
          "fontSize": {"value": 48},
          "fontWeight": {"value": "bold"},
          "align": {"value": "center"},
          "baseline": {"value": "middle"}
        }
      }
    },
    {
      "type": "text",
      "from": {"data": "dataset"},
      "encode": {
        "enter": {
          "x": {"signal": "width / 2"},
          "y": {"signal": "height / 2 + 45"},
          "text": {"signal": "format(datum.change, '+.1%')"},
          "fill": [
            {"test": "datum.change >= 0", "signal": "pbiColor(0)"},
            {"signal": "pbiColor('negative')"}
          ],
          "fontSize": {"value": 16},
          "align": {"value": "center"},
          "baseline": {"value": "middle"}
        }
      }
    }
  ]
}
```

Fields: `Value` (quantitative -- current), `Target` (quantitative -- comparison).

## Standard Config

Recommended config for all Vega and Vega-Lite specs in Power BI:

```json
{
  "autosize": {"type": "fit", "contains": "padding"},
  "view": {"stroke": "transparent"},
  "font": "Segoe UI",
  "axis": {
    "ticks": false,
    "grid": false,
    "domain": false,
    "labelFontSize": 11,
    "titleFontSize": 12
  },
  "axisQuantitative": {
    "tickCount": 5,
    "grid": true,
    "gridColor": "#E8E8E8",
    "gridDash": [2, 4]
  },
  "legend": {
    "orient": "top",
    "labelFontSize": 11
  },
  "title": {
    "fontSize": 14,
    "font": "Segoe UI Semibold",
    "anchor": "start"
  }
}
```
