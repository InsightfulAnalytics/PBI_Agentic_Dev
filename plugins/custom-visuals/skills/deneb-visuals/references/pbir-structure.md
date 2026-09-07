# Deneb PBIR JSON Structure

Complete reference for how Deneb visuals are represented in PBIR format `visual.json` files.

## Visual Container Structure

Minimal Deneb visual container:

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.4.0/schema.json",
  "name": "2c2722561a0b6c3deded",
  "position": {
    "x": 80,
    "y": 56,
    "z": 0,
    "height": 280,
    "width": 280,
    "tabOrder": 0
  },
  "visual": {
    "visualType": "deneb7E15AEF80B9E4D4F8E12924291ECE89A",
    "query": {
      "queryState": {
        "dataset": {
          "projections": [
            {
              "field": {
                "Column": {
                  "Expression": {
                    "SourceRef": { "Entity": "Product" }
                  },
                  "Property": "Product"
                }
              },
              "queryRef": "Product.Product",
              "nativeQueryRef": "Product"
            },
            {
              "field": {
                "Measure": {
                  "Expression": {
                    "SourceRef": { "Entity": "Financials" }
                  },
                  "Property": "$ Sales"
                }
              },
              "queryRef": "Financials.$ Sales",
              "nativeQueryRef": "$ Sales"
            }
          ]
        }
      }
    },
    "objects": {
      "vega": [
        {
          "properties": {
            "jsonSpec": {
              "expr": {
                "Literal": {
                  "Value": "'{\"data\": {\"name\": \"dataset\"}, \"mark\": {\"type\": \"bar\"}, \"encoding\": {\"y\": {\"field\": \"Product\", \"type\": \"nominal\"}, \"x\": {\"field\": \"$ Sales\", \"type\": \"quantitative\"}}}'"
                }
              }
            },
            "jsonConfig": {
              "expr": {
                "Literal": {
                  "Value": "'{}'"
                }
              }
            }
          }
        }
      ]
    },
    "drillFilterOtherVisuals": true
  }
}
```

## Literal Value Encoding Rules

All Deneb object properties use PBIR literal expressions. The encoding varies by type:

### Booleans

Bare `true` or `false` (no quotes):

```json
{"enableTooltips": {"expr": {"Literal": {"Value": "true"}}}}
```

### Numbers (D-suffix)

Append `D` to numeric values:

```json
{"selectionMaxDataPoints": {"expr": {"Literal": {"Value": "50D"}}}}
{"scrollbarOpacity": {"expr": {"Literal": {"Value": "20D"}}}}
```

### Strings and Enums

Wrap in single quotes:

```json
{"provider": {"expr": {"Literal": {"Value": "'vegaLite'"}}}}
{"renderMode": {"expr": {"Literal": {"Value": "'svg'"}}}}
{"selectionMode": {"expr": {"Literal": {"Value": "'simple'"}}}}
```

### JSON Specs (jsonSpec, jsonConfig)

Stringified JSON wrapped in single quotes. The entire Vega/Vega-Lite spec becomes a single-quoted string:

```json
{"jsonSpec": {"expr": {"Literal": {"Value": "'{\"data\":{\"name\":\"dataset\"},\"mark\":\"bar\"}'"}}}}
```

Deneb parses using JSONC (comments are supported inside the spec string).

### Colors (solid fill structure)

```json
{
  "scrollbarColor": {
    "solid": {
      "color": {
        "expr": {
          "Literal": {"Value": "'#000000'"}
        }
      }
    }
  }
}
```

Or bind to theme:

```json
{
  "scrollbarColor": {
    "solid": {
      "color": {
        "expr": {
          "ThemeDataColor": {"ColorId": 1, "Percent": 0}
        }
      }
    }
  }
}
```

## Query State (Field Bindings)

Fields are bound under `visual.query.queryState.dataset.projections`. Each projection contains:

| Property | Purpose |
|----------|---------|
| `field.Column` or `field.Measure` | Field type and reference |
| `field.*.Expression.SourceRef.Entity` | Table name |
| `field.*.Property` | Column or measure name |
| `queryRef` | Fully qualified reference (`Table.Column`) |
| `nativeQueryRef` | The field's real native name in the model |
| `displayName` | Display label shown in the visual (present when the field is renamed) |

Field names in Vega-Lite encoding channels must match the display label: `displayName` when set, otherwise `nativeQueryRef`.

A renamed field therefore carries all four keys. To feed a spec that references `datum['Amount']` from a measure actually named `NM Amount`, `nativeQueryRef` holds the real model name and `displayName` holds the name the spec sees:

```json
{
  "field": {
    "Measure": {
      "Expression": {"SourceRef": {"Entity": "Financials"}},
      "Property": "NM Amount"
    }
  },
  "queryRef": "Financials.NM Amount",
  "nativeQueryRef": "NM Amount",
  "displayName": "Amount"
}
```

Pointing `nativeQueryRef` at the name the spec wants and omitting `displayName` does not rename anything, and the mistake reports through none of the three channels an agent would check: no error in Power BI Desktop, nothing from `pbir validate`, nothing in Deneb's own log. The query runs, the fields arrive under their native names, every spec reference resolves to undefined, and a null-guarded spec draws an intact skeleton with all-blank cells. Check this pairing before debugging the spec whenever a Deneb visual renders its frame but no marks.

### Sort Definition

```json
{
  "sortDefinition": {
    "sort": [
      {
        "field": {
          "Column": {
            "Expression": {"SourceRef": {"Entity": "TableName"}},
            "Property": "ColumnName"
          }
        },
        "direction": "Ascending"
      }
    ],
    "isDefaultSort": true
  }
}
```

## Object Properties

For the full list of Deneb object properties (`vega`, `display`, `dataLimit`, `editor`, `stateManagement`, `developer`), see `references/capabilities.md`. This file focuses on PBIR literal encoding.

All properties are stored under `objects.<objectName>[0].properties` and use the literal encoding rules above.

## Complete PBIR Interactivity Example

Cross-filtering and tooltips with full PBIR literal encoding:

```json
{
  "objects": {
    "vega": [
      {
        "properties": {
          "jsonSpec": {
            "expr": {"Literal": {"Value": "'{...}'"}}
          },
          "jsonConfig": {
            "expr": {"Literal": {"Value": "'{}'"}}
          },
          "provider": {
            "expr": {"Literal": {"Value": "'vegaLite'"}}
          },
          "renderMode": {
            "expr": {"Literal": {"Value": "'svg'"}}
          },
          "enableTooltips": {
            "expr": {"Literal": {"Value": "true"}}
          },
          "enableContextMenu": {
            "expr": {"Literal": {"Value": "true"}}
          },
          "enableSelection": {
            "expr": {"Literal": {"Value": "true"}}
          },
          "enableHighlight": {
            "expr": {"Literal": {"Value": "false"}}
          },
          "selectionMaxDataPoints": {
            "expr": {"Literal": {"Value": "50D"}}
          },
          "selectionMode": {
            "expr": {"Literal": {"Value": "'simple'"}}
          }
        }
      }
    ]
  }
}
```
