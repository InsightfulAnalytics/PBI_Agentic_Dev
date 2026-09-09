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

The `$schema` at the top is the PBIR visual-container schema and stays. The `jsonSpec` literal carries no Vega `$schema`: it belongs in a standalone spec file only, and the 2.0 editor warns on it. This minimal shape also omits `developer.version`, `vega.version` and every `stateManagement` property on purpose; see "Compatible shape for a hand-authored visual" below.

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

Deneb parses using JSONC (comments are supported inside the spec string). Strip a root `$schema` before embedding (`deneb_spec.py embed` does this unless `--keep-schema` is passed); `jsonConfig` is the Config editor content and takes no `$schema` either.

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

### Deneb 2.0 properties

The properties new in 2.0 use the same three literal forms. Shapes below match what Deneb 2.0.0.0 wrote into the `deneb-viz/powerbi-sample-workbook` visuals (Verified 2026-09-08; `enableContextMenuSelector`, `scaleToZoom`, `scrollbarWidth` and the two `dataLimit` ones were not written by that save and are shown with their documented defaults).
Retest: open `deneb_power_bi_sample_workbook.Report/definition/pages/0fdebb925d869a9a2237/visuals/3ec60b103b36a08e268a/visual.json` at `deneb-viz/powerbi-sample-workbook` main and diff `objects.stateManagement`.

`objects.vega`:

```json
{"enableContextMenu": {"expr": {"Literal": {"Value": "true"}}}}
{"enableContextMenuSelector": {"expr": {"Literal": {"Value": "false"}}}}
```

`objects.stateManagement`. `supportFieldConfiguration` is a text literal holding JSON: the inner double quotes are escaped as `\"` for the JSON file, and the whole map sits inside the single quotes. Keys are the encoded display names (`\`, `"`, `.`, `[`, `]` replaced by `_`), one entry per field you want to pin, each with the five base flags explicit; `names` and `treatAsParameter` are optional:

```json
{
  "denebMetaVersion": {"expr": {"Literal": {"Value": "'2'"}}},
  "consolidateFieldParameters": {"expr": {"Literal": {"Value": "true"}}},
  "scaleToZoom": {"expr": {"Literal": {"Value": "false"}}},
  "supportFieldConfiguration": {
    "expr": {
      "Literal": {
        "Value": "'{\"Product\":{\"highlight\":false,\"highlightStatus\":false,\"highlightComparator\":false,\"format\":false,\"formatted\":false,\"names\":false},\"$ Sales\":{\"highlight\":true,\"highlightStatus\":false,\"highlightComparator\":false,\"format\":true,\"formatted\":true,\"names\":false}}'"
      }
    }
  }
}
```

`objects.dataLimit` (continuous view) and `objects.display`:

```json
{"enableIncrementalDataUpdates": {"expr": {"Literal": {"Value": "true"}}}}
{"incrementalUpdateThreshold": {"expr": {"Literal": {"Value": "500D"}}}}
{"scrollbarWidth": {"expr": {"Literal": {"Value": "10D"}}}}
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

### Field Parameters

The observed PBIR shape has two parts, and the parameter column itself appears in neither as a projection. The `projections` list holds the parameter's currently expanded component field(s) exactly as Desktop saves them (in the sample workbook, `penguins.Species`, a plain `Column` projection with a `displayName`); a sibling `fieldParameters` array under `queryState.dataset` names the parameter table and column, and its `index` and `length` address the slice of `projections` those components occupy (`index 1, length 1` there: one component at position 1). Deneb reads the parameter metadata from the data view and needs no Deneb-side binding beyond `stateManagement.consolidateFieldParameters`. To hand-author one, copy that shape: write the component(s) as ordinary projections, add the `fieldParameters` entry, and point `index`/`length` at the positions you gave the components. Writing the parameter column itself as a projection is untested, and how `index`/`length` behave for a multi-select parameter is unknown (observed in one Deneb 2.0.0.0 save of the `deneb-viz/powerbi-sample-workbook`, Verified 2026-09-08; not confirmed as a general authoring recipe).
Retest: bind a field parameter to a Deneb visual in Desktop, save as PBIP and diff `queryState.dataset` against the block below; then hand-author the same visual with the parameter column as the projection instead and confirm whether Desktop opens it.

```json
"fieldParameters": [
  {
    "parameterExpr": {
      "Column": {
        "Expression": {"SourceRef": {"Entity": "Penguin Variables"}},
        "Property": "Penguin Variables"
      }
    },
    "index": 1,
    "length": 1
  }
]
```

The spec references the parameter's display name (`"Penguin Variables"`), not the component's. Whether the components arrive as one array-valued column or as separate fields is decided by `stateManagement.consolidateFieldParameters` (see the compatible shape below and `SKILL.md`).

## Object Properties

For the full list of Deneb object properties (`vega`, `display`, `dataLimit`, `editor`, `stateManagement`, `developer`), see `references/capabilities.md`. This file focuses on PBIR literal encoding.

All properties are stored under `objects.<objectName>[0].properties` and use the literal encoding rules above.

## What Deneb stamps on first open

Deneb 2.0 writes into visual.json only what the user touched or what a migration owns; nothing else gets a default written back. Three independent mechanisms run when a visual is opened under 2.0, and which ones fire depends on the file's stamps (Verified 2026-09-08 from `src/lib/persistence/migration.ts`, `state-management-migration.ts` and `src/lib/dataset/processing.ts` on Deneb main at cd23465, three commits past tag `2.0.0.0`, where none of the three changed; not observed in Desktop).
Retest: open each of the three shapes below in Desktop with Deneb 2.0.0.0, save, and diff `visual.json`.

| File as authored | Version stamps and context menu | `stateManagement` |
|------------------|--------------------------------|-------------------|
| **Unversioned**: real `jsonSpec`, missing `developer.version` and/or `vega.version` ("versioned" needs both), no `denebMetaVersion` | Writes `developer.version '2.0.0.0'` and `vega.version` (`'6.4.3'` for vegaLite, `'6.4.0'` for vega). No context-menu remap, no version-change dialog | Legacy stamp: `supportFieldConfiguration` with an entry for every bound field (columns all false; measures `format` and `formatted` true, the highlight trio true only if `enableHighlight` was already true), `denebMetaVersion '2'`, `consolidateFieldParameters false`. Written once, after the first successful row build |
| **1.x-stamped**: `developer.version '1.9.1.0'` + `vega.version '6.4.1'`, no `denebMetaVersion` | Updates both stamps, shows the version-change dialog, and remaps `enableContextMenu false` (with `enableContextMenuSelector` still at its default) to `enableContextMenu true` + `enableContextMenuSelector false` | Same legacy stamp as above |
| **2.0-stamped**: `developer.version '2.0.0.0'`, `vega.version '6.4.3'`, `denebMetaVersion '2'` | Nothing | Nothing (`current`) |
| **Half-stamped**: non-empty `supportFieldConfiguration` but no `denebMetaVersion` | As the unversioned or 1.x row | Not legacy: writes `denebMetaVersion '2'`, fills unlisted fields with the lean 2.0 defaults under your entries, and `consolidateFieldParameters` becomes the file's value or, when absent, `true` |

`viewportHeight` / `viewportWidth` are refreshed whenever the live size differs from the stored one. A `developer.version '2.0.0.0'` copied by hand without `denebMetaVersion` does not stop the legacy stamp: the two gates are independent.

**Edit mode versus read mode.** All of the above is persisted only while the report is in edit mode (Desktop editing view, Service edit mode). In read mode (`viewMode` View, i.e. Service consumption) the same migrations run in memory on every update and nothing is written, so a report published straight from a hand-authored PBIP keeps its unstamped visual.json until someone saves it from an editor. Whether Desktop's own Reading view takes the read-mode path is unverified: the code gates on the host's `viewMode` value only.
Retest: open a hand-authored visual in Desktop Reading view, switch back to Editing view without touching it, save, and diff `visual.json`.

## Compatible shape for a hand-authored visual

During the 1.9 to 2.0 transition the most compatible visual.json is the minimal one at the top of this file: a real `jsonSpec`, `jsonConfig`, `provider`, the interactivity booleans you need, and **none** of `developer.version`, `vega.version`, `denebMetaVersion`, `supportFieldConfiguration`, `consolidateFieldParameters`. Deneb 1.9 sees nothing it does not know; Deneb 2.0 treats it as a migrated 1.x project (measures get `__format` and `__formatted`, plus the highlight trio only if `enableHighlight` was already true when the stamp was written, columns get nothing, field parameters pass through), then stamps it on first save from an editor. The first-open table above is the detail.

- **Container signals:** keep `pbiContainerWidth` / `pbiContainerHeight` in that shape; 2.0 rewrites them at parse time and 1.9 needs them. Use `denebContainer.*` only when the file already carries `developer.version` 2.0.0.0 or later.
- **Context menu:** want the menu without data-point resolution? Author `enableContextMenu true` + `enableContextMenuSelector false`. Never author `enableContextMenu false` unless the intent is to suppress the menu under 2.0; an unstamped file is not remapped, so 2.0 hides the menu while 1.9 reads the same value as "no resolution". (On 1.9 the extra `enableContextMenuSelector` property is simply undeclared; see the tolerance note below.)
- **Cross-highlight:** if the spec reads `__highlight`, author `enableHighlight true` before the file is first opened under 2.0. The legacy stamp freezes the trio at that moment and switching highlight on later does not add the companions.
- **Opt in to 2.0 semantics** (consolidated field parameters, a lean dataset) by stamping all three together: `denebMetaVersion '2'`, `consolidateFieldParameters true` (or `false`), and an explicit `supportFieldConfiguration` with an entry, five flags each, for every field whose companions the spec reads (plus `"names": true` on a parameter whose `__names` you flatten). Never stamp one of them alone: with `denebMetaVersion` or a non-empty configuration present and `consolidateFieldParameters` absent, the code default is `true` and unlisted fields get the lean defaults, which is not the "false if omitted" the PBIR guide documents. Such a file is 2.0-only in behaviour.

Whether Deneb 1.9.1 tolerates the 2.0-only properties (`denebMetaVersion`, `supportFieldConfiguration`, `consolidateFieldParameters`, `scaleToZoom`, `enableContextMenuSelector`, `enableIncrementalDataUpdates`, `incrementalUpdateThreshold`, `scrollbarWidth`) in a visual.json is UNVERIFIED as of 2026-09-08: Power BI generally ignores object properties a visual does not declare, but nobody has opened such a file under 1.9.1 here, so do not rely on it without the check below.
Retest: open a visual.json carrying all three `stateManagement` stamps in a Desktop running Deneb 1.9.1.0 and confirm it renders pass-through with no property error in the Logs pane.

The full matrix and the audit and migrate commands are in [`references/deneb-2-migration.md`](deneb-2-migration.md#compatibility-matrix).

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
          "enableContextMenuSelector": {
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
