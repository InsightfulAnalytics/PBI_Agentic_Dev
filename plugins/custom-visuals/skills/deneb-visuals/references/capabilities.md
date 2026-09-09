# Deneb Capabilities and Template Format

## Visual Capabilities

### Data Roles

Single data role -- all columns and measures go into one "Values" well:

```json
{
  "dataRoles": [{"displayName": "Values", "name": "dataset", "kind": "GroupingOrMeasure"}],
  "dataViewMappings": [{
    "categorical": {
      "categories": {"select": [{"bind": {"to": "dataset"}}], "dataReductionAlgorithm": {"window": {"count": 30000}}},
      "values": {"select": [{"bind": {"to": "dataset"}}]}
    }
  }]
}
```

The window is 30,000 rows in Deneb 2.0 (the most a custom visual can request) and was 10,000 in 1.9 and earlier. `dataLimit.override` still asks for more in batches of 10,000, but Microsoft no longer guarantees those extra fetches during PDF or PowerPoint export, so override is for report viewing only (Verified 2026-09-08 against the `capabilities.json` inside the shipped `deneb.2.0.0.0.pbiviz` package and the tag `1.9.1.0` copy).
Retest: `gh api repos/deneb-viz/deneb/contents/capabilities.json?ref=2.0.0.0 --jq .content | base64 -d | grep -A2 window`.

### Supported Features

| Feature | Value |
|---------|-------|
| Landing page | Yes |
| Multi-visual selection | Yes |
| Empty data view | No |
| Cross-highlighting | Yes |
| Keyboard focus | Yes (`supportsKeyboardFocus`, new in 2.0: Enter moves focus into the visual, Esc returns; Vega marks are not tabbable) |
| Default title | Suppressed |
| Advanced edit mode | Level 2 |
| Enhanced tooltips | Yes (default + canvas) |
| Privileges | `ExportContent` (essential) |

### Object Properties Reference

The full set from Deneb 2.0's `capabilities.json`. "Default" is the value Deneb uses when the property is absent from visual.json. "2.0" marks a property that did not exist in 1.9.1; nothing was removed between the two (Verified 2026-09-08 by diffing the tag `1.9.1.0` `capabilities.json` against the copy inside the shipped `deneb.2.0.0.0.pbiviz` package; Deneb main at cd23465, three commits past tag `2.0.0.0`, differs from the package only by the one property marked "main only" below).
Retest: `git diff 1.9.1.0 2.0.0.0 -- capabilities.json` in a full clone of `deneb-viz/deneb`.

Literal encoding for each type is in `references/pbir-structure.md`. Every property sits under `visual.objects.<object>[0].properties.<name>.expr.Literal.Value`.

#### `vega` object (core)

| Property | Type | Default | 2.0 | Description |
|----------|------|---------|-----|-------------|
| `jsonSpec` | text | `'{}'` | | Vega/Vega-Lite specification JSON (no root `$schema`) |
| `jsonConfig` | text | `'{}'` | | Vega/Vega-Lite config JSON |
| `provider` | `vegaLite` / `vega` | `vegaLite` | | Language provider |
| `version` | text | managed | | Provider version stamp. 2.0 writes `'6.4.3'` (vegaLite) or `'6.4.0'` (vega); 1.9.1 wrote `'6.4.1'` / `'6.2.0'`. Omit in hand-authored files |
| `logLevel` | enum 0-4 | `3D` | | none/error/warn/info/debug (the PBIR guide lists only 0-3; 4 exists in both 1.9.1 and 2.0) |
| `renderMode` | `svg` / `canvas` | `svg` | | Rendering engine |
| `enableTooltips` | bool | `true` | | Power BI tooltips |
| `enableContextMenu` | bool | `true` | semantics changed | 2.0: whether the Power BI right-click menu appears at all (`false` swallows right-click). Pre-2.0: whether data points were resolved for it |
| `enableContextMenuSelector` | bool | `true` | new | Whether Deneb resolves the clicked datum for drill-through. Only meaningful while the menu is enabled. Under `objects.vega`, not the `objects.interactivity` the 2.0 changelog table prints |
| `enableHighlight` | bool | `false` | | Cross-highlighting (measures only) |
| `enableSelection` | bool | `false` | | Cross-filtering; adds `__selected__` to every row |
| `selectionMode` | `simple` / `advanced` | `simple` | | Selection management |
| `selectionMaxDataPoints` | numeric | `50D` | | Max selectable points; UI 1-250; advanced mode `options.limit` up to 2500 |
| `tooltipDelay` | numeric | `0D` | | Tooltip display delay, 0-10000 ms. Not in the PBIR guide |

#### `display` object

| Property | Type | Default | 2.0 | Description |
|----------|------|---------|-----|-------------|
| `scrollbarColor` | solid color | `#000000` | | Scrollbar fill color |
| `scrollbarOpacity` | integer | `20D` | | 0-100 |
| `scrollbarRadius` | integer | `0D` | range widened | 0-8 in 2.0; the maximum was 3 before |
| `scrollbarWidth` | integer | `10D` | new | 8-16 px (the PBIR guide says "8D upwards"; the code caps at 16) |
| `scrollEventThrottle` | numeric | `5D` | | 0-1000 ms between `denebContainer` scroll updates |

#### `dataLimit` object

| Property | Type | Default | 2.0 | Description |
|----------|------|---------|-----|-------------|
| `override` | bool | `false` | | Fetch beyond the 30,000-row window (10,000 in 1.9) in 10,000-row batches; report viewing only, not guaranteed during export |
| `showCustomVisualNotes` | bool | `true` | | Show custom visual notes |
| `enableIncrementalDataUpdates` | bool | `false` | new | Continuous view: patch data into the live Vega view instead of recompiling, keeping zoom, pan, facet page, signal and selection state. Falls back to a recompile, with a Logs-pane warning, for ineligible specs (e.g. force transforms with aggregates) |
| `incrementalUpdateThreshold` | numeric | `500D` | new | Largest updated dataset (rows) that is patched rather than recompiled; 5-5000, the ceiling is hard. Row count is a poor cost proxy (wide rows and heavy transforms dominate), so test under realistic slicing and lower it if the visual gets suspended |

#### `stateManagement` object

Deneb manages the first two on every update and the last four on first open or when the Project setup pane is used. See `references/pbir-structure.md` for when to author them by hand.

| Property | Type | Default | 2.0 | Description |
|----------|------|---------|-----|-------------|
| `viewportHeight` | numeric | managed | | Current viewport height |
| `viewportWidth` | numeric | managed | | Current viewport width |
| `supportFieldConfiguration` | text | `''` (empty map) | new | JSON map of per-field supporting-field flags, keyed by the encoded display name (`\ " . [ ]` replaced by `_`). Each entry carries `highlight`, `highlightStatus`, `highlightComparator`, `format`, `formatted` as explicit booleans, optionally `names` and `treatAsParameter`. Unparseable text degrades to an empty map with a warning |
| `denebMetaVersion` | text | `''` (version 0) | new | Project metadata version. Absent or empty plus a real `jsonSpec` classifies the visual as a legacy project to migrate; `'2'` is what 2.0 stamps. A non-integer value blocks migration |
| `scaleToZoom` | bool | `false` | new | Canvas only: multiply the canvas resolution by the report (and editor preview) zoom to reduce blur |
| `consolidateFieldParameters` | bool | `true` when absent (code); `false` is what the legacy migration pins | new | Merge a field parameter's components into one array-valued column. The PBIR guide's "false if omitted" describes the migrated outcome, not the code default: stamp it explicitly whenever `denebMetaVersion` or `supportFieldConfiguration` is present |

#### `editor` object (Advanced Editor preferences, no rendering effect)

| Property | Type | Default | 2.0 | Description |
|----------|------|---------|-----|-------------|
| `theme` | `dark` / `light` | `light` | | Editor color theme |
| `backgroundPassThrough` | bool | `true` | | Show the report background behind the preview. Capitalised `T` is the capabilities spelling; the PBIR guide's `backgroundPassthrough` is wrong for visual.json |
| `position` | `left` / `right` | `left` | | Editor pane position |
| `fontSize` | fontSize | `10D` | | 8-30 |
| `wordWrap` | bool | `true` | | Enable word wrap |
| `showLineNumbers` | bool | `true` | | Show line numbers |
| `showViewportMarker` | bool | `true` | | Outline the report viewport in the preview |
| `previewScrollbars` | bool | `true` | | Show scrollbars on overflow in the preview |
| `debugTableRowsPerPage` | numeric | `50D` | | 10, 25, 50, 100, 150 or 200 |
| `debouncePeriod` | numeric | `700D` in code (the PBIR guide says 300) | | Auto-apply debounce, 0-1000 ms |
| `formattingMaxLineLength` | numeric | `80D` | main only | 40-200. Declared on the `main` branch after the 2.0.0.0 release; NOT in the 2.0.0.0 package, so do not author it |

#### `developer` object

| Property | Type | Default | 2.0 | Description |
|----------|------|---------|-----|-------------|
| `version` | text | absent = unversioned | | Deneb build stamp, `'2.0.0.0'` once 2.0 has saved the visual. A visual is "versioned" only when both this and `vega.version` are present; the PBIR guide's "assumed current if omitted" is not what the code does |
| `locale` | enum | `en-US` | | `en-US`, `en-GB`, `de-DE`, `fr-FR` (editor preview locale) |

#### `general` object

| Property | Type | Default | 2.0 | Description |
|----------|------|---------|-----|-------------|
| `formatString` | formatString | -- | | Declared for Power BI's own formatting; Deneb neither reads nor writes it |

## Template Format (v2)

Templates are valid Vega/Vega-Lite JSON files with a `usermeta` object. Deneb 2.0 exports `metaVersion` 2 and still imports v1 (see the legacy subsection). Schemas: `https://deneb-viz.github.io/schema/deneb-template-usermeta-v2.json` (current) and `https://deneb-viz.github.io/schema/deneb-template-usermeta-v1.json` (legacy). Exported templates carry a root `$schema` for the bundled major version (`https://vega.github.io/schema/vega/v6.json` or `.../vega-lite/v6.json`); import strips `$schema` and `usermeta` from the spec body.

### Structure (minimal, validates against the published v2 schema)

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
      "name": "Minimal bar chart",
      "description": "One category column and one measure, drawn as a bar chart.",
      "author": "Example author",
      "uuid": "3f2c8a1e-6b7d-4c2a-9e1f-0a1b2c3d4e5f",
      "generated": "2026-09-08T00:00:00.000Z"
    },
    "datasets": {
      "dataset": [
        {"key": "__dataset.0__", "name": "Category", "description": "Category for the y-axis.", "kind": "column", "type": "text"},
        {"key": "__dataset.1__", "name": "Measure", "description": "Measure for the bar length.", "kind": "measure", "type": "numeric"}
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
    "config": "{}"
  },
  "data": {"name": "dataset"},
  "mark": {"type": "bar"},
  "encoding": {
    "y": {"field": "__dataset.0__", "type": "nominal"},
    "x": {"field": "__dataset.1__", "type": "quantitative"}
  }
}
```

Verified 2026-09-08 with Python `jsonschema` 4.26.0 against the published v2 schema (`date-time` and `uri` formats were not enforced in that run).
Retest: `python -c "import json,jsonschema;from jsonschema import Draft7Validator as V;s=json.load(open('deneb-template-usermeta-v2.json'));t=json.load(open('template.json'));print(list(V(s).iter_errors(t['usermeta'])))"` (expects `[]`).

`usermeta` allows no extra properties; `deneb`, `information` and `datasets` are required.

### `usermeta.deneb` (required)

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `build` | string | Yes | Deneb build that exported the template (informational) |
| `metaVersion` | number 1-2 | Yes | `2` for new templates; `1` is accepted and migrated on import, and is NOT bumped |
| `provider` | enum | Yes | `"vega"` or `"vegaLite"`. When missing, the code falls back to `vega` |
| `providerVersion` | string | Yes | Vega/Vega-Lite version; 2.0 stamps `6.4.0` / `6.4.3`. A missing value is patched on import with the legacy `5.21.0` / `5.1.1` |

### `usermeta.information` (required)

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `name` | string (max 100) | Yes | Template display name |
| `author` | string (max 100) | Yes | Creator identifier |
| `description` | string (max 300) | No | Detailed description |
| `uuid` | lowercase UUID v4 | Yes | Unique template ID |
| `generated` | date-time | Yes | UTC timestamp |
| `supportUri`, `videoUri` | URI | No | Reserved, unused by Deneb |
| `previewImageBase64PNG` | string | No | Base64 preview (150 x 150 px by convention) |

The published schema sets `additionalProperties: false` here even though the docs say the object can be extended; write nothing extra.

### `usermeta.datasets` (required, record keyed by dataset name)

Only the `dataset` key is surfaced by the UI. Each value is an array of placeholder entries (`datasets.dataset` may be `[]`):

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `key` | string `^__[a-zA-Z0-9_]+\.\d+__$` (max 30) | Yes | Placeholder key in the spec: `__dataset.0__`, `__dataset.1__`, ... in dataset order. Custom names such as `__category__` are rejected by v2 |
| `name` | string (max 150) | Yes | Display name in the assignment UI; a recipient field with exactly this name is pre-selected |
| `kind` | `column` / `measure` / `parameter` / `any` | No (schema) | Informational for `column`/`measure`/`any`. `parameter` marks a consolidated field parameter: assigning a regular field to that slot sets `treatAsParameter` and switches consolidation on. Exported parameters are one entry, not one per component |
| `type` | `bool` / `dateTime` / `numeric` / `other` / `text` | Yes | Data type (guidance only) |
| `description` | string (max 300) | No | Usage description |
| `supportFieldConfiguration` | object | No | The same flag object as the PBIR `stateManagement.supportFieldConfiguration` entry, without the text wrapping: `highlight`, `highlightStatus`, `highlightComparator`, `format`, `formatted` (all required by the published schema; Deneb itself accepts a partial object on import and writes the full five on export), optional `names`, `treatAsParameter`. Present only when the field differs from the role defaults. Re-keyed by the supplied field name on import |

`suppliedObjectKey`, `suppliedObjectName` and `namePlaceholder` are import-time working state; do not author them.

### `usermeta.interactivity` (optional)

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `tooltip` | bool | Yes | Enable tooltips |
| `contextMenu` | bool | Yes | 2.0: show the Power BI context menu at all |
| `contextMenuSelector` | bool | No (default `true`) | Resolve the data point for drill-through. Leaving it out marks the template as legacy: `contextMenu: false` without it imports as menu on + selector off |
| `selection` | bool | Yes | Enable cross-filtering |
| `selectionMode` | `simple` / `advanced` | No (default `simple`) | Selection mode |
| `highlight` | bool | No (default `false`) | Enable cross-highlighting |
| `dataPointLimit` | 1-250 | Yes | Maps to `selectionMaxDataPoints` |

The 2.0 changelog table calls the template key `interactivity.enableContextMenu`; the schema key is `contextMenu`. When the whole object is absent the code imports with tooltips OFF, menu on with selector off, highlight and selection OFF (unverified in the UI; the docs say "Deneb's defaults are used", which would be tooltips on).
Retest: import a template with no `interactivity` block through Create New Specification and read `enableTooltips` from the saved visual.json (Verified 2026-09-08 from `create-button.tsx` and `context-menu-migration.ts` on Deneb main at cd23465, three commits past tag `2.0.0.0`, where neither file changed; source only).

### `usermeta.config` (optional)

A STRING holding the Config editor content (JSON or JSONC), `{}` assumed when absent. Pre-1.7 templates carried an object at the spec's top-level `config`; import moves it here.

### v1 (legacy)

The v1 shape (`metaVersion` 1) had `usermeta.dataset` as a flat array with free-form keys matching `^__[a-zA-Z0-9]+__$` (Deneb's own exporter wrote `__0__`, `__1__`, ...; community templates also used names like `__category__`), `name` capped at 30, `kind` limited to `any` / `column` / `measure`, no per-entry `supportFieldConfiguration`, and `interactivity` without `contextMenuSelector` or `selectionMode`. Deneb 2.0 migrates it on import: `usermeta.dataset` becomes `usermeta.datasets.dataset` with keys rewritten to `__dataset.<index>__` by array position, and every `__<index>__` in the spec text is rewritten to match. Custom keys are renamed in the metadata but NOT rewritten in the spec body by that code path, so a `__category__` template needs converting offline first (inferred from source, unverified in the UI). A v1 template creates a project with `denebMetaVersion` 1, so it gets the migrated-project supporting-field defaults (all on for measures) and consolidation off. The terminal recipe is in `references/advanced-patterns.md`.
Retest: import a v1 template with custom keys through the 2.0 Create New Specification dialog and inspect the resulting spec for the raw keys (Verified 2026-09-08 from `template-usermeta.ts` `getTemplateResolvedForLegacyDataset` on Deneb main at cd23465, three commits past tag `2.0.0.0`; the post-tag change to that file only threads a formatting line-length option through neighbouring functions and leaves the legacy-dataset resolution untouched).

## Special Fields

Deneb adds these fields to the dataset at runtime. Row-level fields are always scalar; per-field companions are scalar for a regular field and an array (one entry per component, in data-view order) for a consolidated field parameter:

| Field | Purpose |
|-------|---------|
| `__row__` | Zero-based row index, always present. Its presence in a datum is what lets Power BI resolve row context for tooltips, the context menu and cross-filtering. Survives a `flatten` transform. Replaces `__identity__` (removed in 1.9) |
| `__selected__` | Selection state: `"on"`, `"off"`, or `"neutral"`. Only present when `enableSelection` is true |
| `<field>__highlight` | Cross-highlight value for a measure (equals the base value when no highlight is active); array for a parameter, where column components pass their base value through |
| `<field>__highlightStatus` | Highlight state: `"neutral"` with no active highlight, `"off"` when the base value is null but the highlight value is not, otherwise `"on"`. A row whose highlight value is null (outside the highlighted subset) reads `"on"` in the shipped 2.0.0.0 and `"off"` only on Deneb main after the tag (see below) |
| `<field>__highlightComparator` | Pre-computed comparison: `"eq"`, `"lt"`, `"gt"`, `"neq"` (highlight vs original; `"neq"` for text). A null highlight value gives `"neq"` only on Deneb main after the tag; in the shipped 2.0.0.0 null coerces to 0, so the result follows the base value's sign: `"lt"` for a positive base, `"gt"` for a negative one, `"neq"` for zero (see below) |
| `<field>__format` | The Power BI format string, resolved per row (dynamic format strings and calculation-group formats work), e.g. `"$#,0.00"` |
| `<field>__formatted` | The base value formatted with that row's format string in the visual's locale |
| `<parameter>__names` | Component display names of a consolidated field parameter, e.g. `["$ Sales", "$ Profit"]`; the same array on every row. Field parameters only, new in 2.0 |

The null-highlight cases differ between the shipped build and current source. `packages/data-core/src/lib/value/highlight.ts` at tag `2.0.0.0` has no null-comparator guard; commit b513045 on main (2026-09-04, "correct __highlightStatus and __highlightComparator for un-highlighted rows", deneb-viz/deneb#753) adds the `"off"` and `"neq"` results described above, so they will only reach reports with the next release (Verified 2026-09-08 with `gh api repos/deneb-viz/deneb/compare/2.0.0.0...main` and the tag's copy of that file). Until then, do not branch spec logic on those two companions for un-highlighted rows; test `__highlight` for null instead.
Retest: under the AppSource 2.0.0.0 build, cross-highlight from another visual so at least one row has a null highlight value, and read `__highlightStatus` / `__highlightComparator` for that row in the debug Source tab (Ctrl+Alt+6).

Highlight companions never exist for columns (Power BI does not highlight columns). From 2.0 a column can opt in to `__format` / `__formatted`.

### Defaults: which companions exist

Which companions are generated depends on the field's role and on how the visual is classified (Verified 2026-09-08 from `resolve-defaults.ts` lines 20-60 on Deneb main at cd23465, three commits past tag `2.0.0.0`, where that file did not change; "XH" means `enableHighlight` is on).
Retest: bind one column and one measure to a fresh 2.0 visual and read the debug Source tab (Ctrl+Alt+6).

**New 2.0 project** (`denebMetaVersion` `'2'`, or a factory-default spec):

| Companion | Column | Measure | Field parameter (consolidated) |
|-----------|--------|---------|-------------------------------|
| `__highlight` | unavailable | on if XH, else off | on if XH, else off |
| `__highlightStatus` | unavailable | off | off |
| `__highlightComparator` | unavailable | off | off |
| `__format` | off | off | off |
| `__formatted` | off | off | off |
| `__names` | unavailable | unavailable | off (opt-in) |
| `treatAsParameter` | off (offered only with consolidation on) | off | unavailable |

The 2.0 changelog's table prints the parameter `__highlight` default as disabled; the source and the field-parameters page say on when cross-highlight is enabled.

**Migrated or unstamped project** (real spec, no `denebMetaVersion`), stamped into `supportFieldConfiguration` on first open and then frozen:

| Companion | Column | Measure |
|-----------|--------|---------|
| `__highlight`, `__highlightStatus`, `__highlightComparator` | unavailable | all three on if XH was on at stamp time, else off |
| `__format`, `__formatted` | off | on |
| Field parameters | pass-through (consolidation pinned `false`, no arrays) | |

**Deneb 1.9.x** (no configuration existed): measures got the highlight trio when XH was on and `__format` / `__formatted` for what the 1.9 docs call numeric or date/time-based measures (`formatting-values.md`; the text-measure case was not checked, see Retest (5) in [deneb-2-migration.md, Compatibility matrix](deneb-2-migration.md#compatibility-matrix)); columns got none; `__row__` always, `__selected__` when selection was on.

Practical reading: a spec written against 1.9 that reads `datum['Sales__formatted']` keeps working on a migrated visual, but returns `undefined` in a brand-new 2.0 visual until the flag is switched on in the Supporting fields pane or in `supportFieldConfiguration`.

> **Breaking change in 1.9:** `__identity__` and `__key__` were removed. Any spec using `datum.__identity__` must be updated to `datum.__row__`.

## Community Resources

| Resource | URL |
|----------|-----|
| Deneb documentation | https://deneb.guide |
| Deneb GitHub | https://github.com/deneb-viz/deneb |
| Kerry Kolosko templates | https://kerrykolosko.com/portfolio/ |
| PBI-David/Deneb-Showcase | https://github.com/PBI-David/Deneb-Showcase |
| PBIQueryous/Deneb | https://github.com/PBIQueryous/Deneb |
| avatorl/Deneb-Vega-Templates | https://github.com/avatorl/Deneb-Vega-Templates |
| Vega-Lite docs | https://vega.github.io/vega-lite/ |
