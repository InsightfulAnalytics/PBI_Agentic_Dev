# Advanced Theme Features

Covers named style presets, the base theme layering model, organizational theme distribution, and mobile-only formatting overrides.

---

## Named Style Presets

A native theme-file feature distinct from the `pbir visuals preset` CLI command (which stamps formatting onto a visual instance). Theme named presets surface a Style dropdown in the Format pane so report authors can pick a pre-built visual look per-visual; they are the file-based way to ship multiple branded table looks or chart variants.

Structure: add a named key alongside `"*"` inside a visual-type section. The key name is what appears in the dropdown:

```json
"columnChart": {
  "*": {
    "stylePreset": [{ "name": "Brand Bottom Legend" }],
    "legend": [{ "position": "BottomCenter", "show": true }]
  },
  "Brand Bottom Legend": {
    "legend": [{ "position": "BottomCenter" }]
  },
  "Brand Right Legend": {
    "legend": [{ "position": "Right" }]
  }
}
```

Key mechanics:
- A named preset inherits from `"*"` for its type; put shared formatting in `"*"` and only deltas in each preset name
- `"*" -> stylePreset -> [{name}]` sets which preset is the post-import default
- Presets are scoped to one visual type; you cannot define a cross-type preset
- A `visual.json` referencing a deleted preset name shows a "can't be found" error and falls back to `"*"`; grep for preset references before renaming or deleting

```bash
# Check for visual.json references to a named preset before deleting it
# (a visual stores its choice in visualContainerObjects.stylePreset[].properties.name)
grep -rn -A6 "\"stylePreset\"" Report.Report/definition/pages/
```

Selecting a preset on visuals and authoring presets with `pbir` (`theme set-formatting`, `theme push-visual --preset`, and where the 0.9.x CLI writes the wrong shape): see `style-presets.md`. Where the CLI cannot write the preset cleanly, edit the visual-type file in the serialized `.Theme` folder and rebuild.

---

## Base Theme and the Layering Model

The cascade described in SKILL.md has a hidden first layer: a base theme Microsoft ships with Desktop that establishes factory defaults for every property. This base is frozen at report creation time; a report keeps its original base indefinitely (Desktop shows a banner in Customize Theme when a newer base is available).

```
Base theme (Microsoft-managed, frozen at creation)
  |
Custom theme (your JSON; overrides only what it sets)
  |
Theme visual-type overrides
  |
Visual-level overrides (visual.json)
```

This explains three behaviors:
- Two reports with the same custom theme may render differently if created months apart (frozen bases differ)
- "Reset to default" reverts only to the custom theme's values; for keys the custom theme does not set, the base takes effect (not truly blank)
- A minimal custom theme (just `dataColors` and a name) is fragile: almost every formatting decision falls through to a base you cannot pin or version-control in PBIR

The defense is completeness: set the wildcard and structural keys explicitly so the base is effectively displaced. A theme that fully specifies its intended defaults is portable across base versions.

Completeness has to reach the base's own `visualStyles`, because two of a custom theme's levers sit below them:

- **Text classes lose to the base theme's visualStyles sizes.** A text class sets a role's size only where no `visualStyles` entry, the base's included, sets that property. Fluent2-CY26SU10 sets 44 font sizes (axis labels and axis titles 10.5, visual title 15, `cardVisual` label 12, button slicer values 10.5, button and navigator text 10.5, among them), and a custom theme whose text classes asked for other sizes left every one of them unchanged. Table and matrix text, legends, data labels, card values and the classic slicer, which the base does not size, followed the text classes. Restate each base size in the custom theme's `visualStyles`.
- **Literal colors in the base's visualStyles beat the custom color slots.** Gridlines stayed `#F0F0F0` under a custom theme that set `thirdLevelElements`, which is how a dark custom theme ends up with light gridlines and light card outlines. Restate every literal hex the base holds (23 in Fluent2-CY26SU10).
- **Across layers, a custom wildcard beats a base visual-type entry.** Wildcard `background`, `border` and `padding` in a custom theme reached the page navigator, which the base switches off for its own type. Add a visual-type entry to the custom theme to switch them back.

Desktop writes the base as a readable snapshot in `StaticResources/SharedResources/BaseThemes/`, so list what to restate from it: every `fontSize` and every `#rrggbb` under `visualStyles`.

(Observed with base Fluent2-CY26SU10 on Desktop 2.159.883.0, 26.10, sizes measured from rendered text. Verified 2026-10-29.)
Retest: in a custom theme that sets no `visualStyles` sizes, set `textClasses.label.fontSize` to 14, then compare an axis label with a table cell in a `pbir desktop screenshot`.

Side effect of "reset to default": clearing `objects`/`visualContainerObjects` via `pbir visuals clear-formatting` strips data-bound items, CF rules, button/image actions, and URL/field-bound images along with chrome overrides. The CLI's `--keep-cf` guards conditional formatting but a blanket clear removes more than chrome. Audit before batch-clearing on reports with rich interactive content.

---

## Organizational Themes

The tenant-level distribution mechanism for one corporate look across hundreds of reports. A Fabric tenant admin uploads validated theme JSON in the admin portal; those themes appear in the Themes dropdown for every author in Desktop and Service.

Key behaviors:
- Applying an org theme removes any existing custom theme and replaces it wholesale; org theme and a hand-authored custom theme are mutually exclusive on one report
- The admin portal runs the same schema validation as Desktop import, plus a unique-name constraint; a theme failing `pbir theme validate` also fails org upload
- An agent cannot publish to the gallery from the terminal (admin-portal only)

Authoring for org deployment: write valid JSON, name it uniquely, and make it complete enough to stand alone (no reliance on a local base the recipients will not have). `pbir theme validate` is the pre-upload gate.

For compliance audits: the right question becomes "does this report match the org theme?" rather than only "is the JSON internally consistent?". Compare with:

```bash
# Download the org theme from any report that has it applied, then diff
pbir theme diff "Report.Report" "OrgTheme.json"
```

Scriptable theme deployment: `sempy_labs.report` (Semantic Link Labs) is the closest path to programmatic theme application across a workspace without the admin portal.

---

## Mobile-Only Formatting Overrides

`mobile.json` accepts its own `objects` and `visualContainerObjects` alongside the required `position` block. This means the phone copy of a visual can be formatted differently from the web copy without touching the desktop visual.

The cascade on phone:

```
Theme defaults
  -> Theme wildcard/visual-type
  -> visual.json overrides
  -> mobile.json overrides  (most specific; portrait only)
```

Practical use: a card showing a 28pt callout on desktop can show 16pt on phone via a `mobile.json` with only a `fontSize` override in its `objects` block. Strip non-essential chrome per Microsoft's mobile guidelines: axis titles, gridlines, and legends rarely survive portrait width.

```json
{
  "$schema": "...",
  "position": { "x": 0, "y": 0, "z": 0, "width": 320, "height": 80 },
  "objects": {
    "title": [{ "properties": { "fontSize": { "expr": { "Literal": { "Value": "10" } } } } }]
  }
}
```

Rules to keep overrides minimal:
- Store only properties that must differ from the desktop; every omitted property inherits from the desktop visual
- A change that applies on all surfaces (brand colors, shared typography) goes in the theme, not `mobile.json`; otherwise you reintroduce per-visual override sprawl
- Duplicating the full desktop `objects` into `mobile.json` is an anti-pattern: it doubles the maintenance surface and drifts; store deltas only

Cascade trap: a desktop-visual formatting fix does not propagate to any property already pinned in `mobile.json`; the mobile value wins on phone. After editing a visual's desktop formatting, check whether a corresponding `mobile.json` override needs updating.
