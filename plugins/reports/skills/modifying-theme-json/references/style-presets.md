# Style presets in themes

A style preset is a named formatting bundle for one visual type, defined in the theme. Authors pick it from **Format visual > Style presets** for any visual of that type. Use presets when an organization needs a few sanctioned looks for the same visual type (compact vs. banded tables, bar charts with or without data labels) instead of one default plus per-visual overrides.

These are not the `pbir visuals preset` bundles (`minimal`, `bold`, ...). Those write overrides onto visuals; theme style presets live in the theme and every visual that selects one inherits it.

## Structure

The second key under `visualStyles.<visualType>` is the preset name. `"*"` is the default style; any other key is a named preset.

```json
{
  "name": "Contoso",
  "visualStyles": {
    "tableEx": {
      "*": {
        "stylePreset": [{ "name": "Compact" }],
        "columnHeaders": [{ "fontFamily": "Segoe UI Semibold", "fontSize": 10 }],
        "grid": [{ "gridHorizontal": true, "gridHorizontalColor": { "solid": { "color": "#E0E0E0" } } }]
      },
      "Compact": {
        "grid": [{ "rowPadding": 1, "textSize": 9 }]
      },
      "Banded": {
        "grid": [{ "gridHorizontal": false, "rowPadding": 4 }],
        "values": [{ "backColorSecondary": { "solid": { "color": "#F5F5F5" } } }]
      }
    }
  }
}
```

Validates against the Power BI report theme schema (2.155 to 2.157). Rules:

- A named preset inherits from the type's `"*"` style. Put shared formatting in `"*"`; put only the differences in each preset
- `stylePreset` inside `"*"` sets the preset new visuals of that type start with. The schema rejects `stylePreset` inside a named preset
- A preset takes the same cards and properties as `"*"`, including `$id` state entries (`default`, `hover`, `selected`) on buttons and navigators
- Values are plain theme values (`1`, `true`, `{ "solid": { "color": "#E0E0E0" } }`), never PBIR `{ "expr": { "Literal": ... } }` literals
- Presets are per visual type. A `Compact` preset on `tableEx` does nothing for `pivotTable`; define it on both if both need it
- `examples/Fluent2-CY26SU03.json` shows Microsoft's own presets: `tableEx`/`pivotTable` `Minimal`, chart `Data labels`, `actionButton` `Outline`, `slicer` `Tile`

The full cascade with presets:

```text
Power BI defaults
  -> theme wildcard defaults        visualStyles."*"."*"
  -> theme visual-type defaults     visualStyles.<type>."*"
  -> selected style preset          visualStyles.<type>.<preset>
  -> visual instance overrides
```

## How a visual selects a preset

The visual stores the preset name in `visualContainerObjects.stylePreset`. Set it through `pbir`:

```bash
pbir set "Report.Report/Page.Page/Table.Visual.stylePreset.name" --value "Compact"
pbir set "Report.Report/**/*.Visual.stylePreset.name" --value "Compact" --where visual_type=tableEx --dry-run
pbir set "Report.Report/**/*.Visual.stylePreset.name" --value "Compact" --where visual_type=tableEx -f
```

Always filter bulk selection with `--where visual_type=<type>`; a bare glob sets the name on every visual type. When a visual names a preset the theme no longer defines (renamed preset, swapped theme), Desktop shows an author-only "style preset can't be found" error on that visual. Keep preset names stable across theme versions, and after a theme swap list which presets visuals still reference.

## Author presets through `pbir`

```bash
# Default preset for new visuals of a type
pbir theme set-formatting "Report.Report" "tableEx.*.stylePreset.name" --value "Compact"

# Promote a formatted visual into a named preset; leave its own stylePreset out
pbir theme push-visual "Report.Report/Page.Page/Table.Visual" --preset "Compact" --components grid,values --dry-run
pbir theme push-visual "Report.Report/Page.Page/Table.Visual" --preset "Compact" --components grid,values

pbir theme validate "Report.Report"
```

- pbir-cli 1.0: `pbir theme set-formatting "Report.Report" "tableEx.Compact.grid.rowPadding" --value 2` writes the named preset, and card states go in `--state`. In 0.9.x the second path segment is a state id, so the same path writes a `{"$id": "Compact"}` entry into the default style instead
- pbir-cli 1.0: `push-visual` writes plain theme values and leaves the visual's `stylePreset` out of a named preset. In 0.9.x it copies `expr` literals and `stylePreset`, which `pbir theme validate` rejects; treat that as a failed push and do not hand-edit the theme

Reload the report in Desktop and check the **Style presets** dropdown on one visual of the type before relying on the presets.
