---
name: deneb-visuals
version: 26.26
description: Deneb visual creation, Vega/Vega-Lite spec authoring, and Deneb best practices for PBIR reports. Automatically invoke whenever the user mentions "Deneb" in any context, or asks about Vega/Vega-Lite specs in Power BI, Deneb cross-filtering, Deneb interactivity, pbiColor theme integration, Deneb field name escaping, or Deneb rendering issues.
---

# Deneb Visuals in Power BI (PBIR)

> **Report modification requires tooling.** Two paths exist:
> 1. **`pbir` CLI (preferred)** -- use the `pbir` command and the `pbir-cli` skill. Install with `uv tool install pbir-cli` or `pip install pbir-cli` on macOS or Windows; neither works on Linux, where path 2 is the only option. Check availability with `pbir --version`.
> 2. **Direct JSON modification** -- if `pbir` is not available, use the `pbir-format` skill (pbip plugin) for PBIR JSON structure and patterns. Validate every change with `jq empty <file.json>`.
>
> If neither the `pbir-cli` skill nor the `pbir-format` skill is loaded, ask the user to install the appropriate plugin before proceeding with report modifications.

Deneb is a certified custom visual for Power BI that enables Vega and Vega-Lite declarative visualization specs directly inside reports. Author specs using this skill.

## Provider Policy

**Prefer Vega-Lite** for new Deneb visuals unless specific Vega-only features are required (signals, event streams, custom projections, force/voronoi layouts). Vega-Lite is more concise, easier to maintain, and covers most chart types. For advanced Vega features, see `references/vega-patterns.md` and the [Vega documentation](https://vega.github.io/vega/docs/).

When a Vega-Lite spec outgrows Vega-Lite there is an escape hatch: the 2.0 editor's Compiled Vega pane (Vega-Lite specs only) offers "Convert my spec to Vega", which replaces the spec with its compiled Vega equivalent, switches the provider, and cannot be undone. The compiled output drops the root `$schema` and the spec's `config` block, though the Config editor keeps its own contents. Extract the Vega-Lite spec to a file first (`deneb_spec.py extract`, `deneb-pbir` skill): Deneb cannot recover it afterwards (Verified 2026-09-08 from the Deneb docs site `getting-started/visual-editor.mdx`; read from the docs, not run in Desktop).
Retest: in a Deneb 2.0.0.0 editor, open a Vega-Lite spec that carries its own `config`, run Compiled Vega then "Convert my spec to Vega", and diff the result.

## Visual Identity

- **visualType:** `deneb7E15AEF80B9E4D4F8E12924291ECE89A` (the AppSource, certified edition: the one this skill assumes)
- **Other editions:** Standalone `STANDALONEdeneb7E15AEF80B9E4D4F8E12924291ECE89A`, Alpha `ALPHAdeneb7E15AEF80B9E4D4F8E12924291ECE89A`, Beta `BETAdeneb7E15AEF80B9E4D4F8E12924291ECE89A`. None of the three is served from AppSource, so the edition's `.pbiviz` has to be unzipped into `/CustomVisuals/{GUID}/` in the PBIP assets and source-controlled with the report. Persisted properties do not carry across GUIDs: Deneb classifies a payload arriving under a different packaging-channel GUID as an empty one (a fresh visual, not a legacy project), so no migration runs on it. For an agent, moving a visual between editions is a rebuild, not a `visualType` swap: carry `objects.vega` and any `stateManagement` stamps over yourself, then open the result and confirm the spec survived (Verified 2026-09-08 from the PBIR guide's "Other Visual Editions" section and `src/lib/persistence/state-management-migration.ts` lines 179-181 on Deneb main at cd23465, three commits past tag `2.0.0.0`; read from source and docs, not reproduced in Desktop, and the cross-GUID note is written about `.pbix` state rather than a hand-edited PBIR file).
  Retest: copy a working visual.json, change `visualType` to the Standalone GUID with that edition's `.pbiviz` extracted under `/CustomVisuals/`, open in Desktop and check whether the spec and the `stateManagement` stamps are still there.
- **Current build:** Deneb 2.0.0.0 on custom visuals API 5.11.0, bundling Vega 6.4.0 / Vega-Lite 6.4.3. The 1.9.x builds bundled Vega 6.2.0 / Vega-Lite 6.4.1. Vega 6 has been bundled since 1.8, so standalone spec files use `v6.json` schema URLs (Verified 2026-09-08 against `pbiviz.json` and `package.json` on Deneb main at cd23465, 2026-09-04, three commits past tag `2.0.0.0`; neither file changed between the two).
  Retest: `gh release view 2.0.0.0 -R deneb-viz/deneb --json tagName,publishedAt` and read `dependencies.vega` / `vega-lite` in the tag's `package.json`.
- **Data role:** Single `dataset` role (all fields go into one "Values" well)
- **Default row window:** 30,000 rows in 2.0, 10,000 in 1.9 and earlier. `dataLimit.override` still fetches more in 10,000-row batches, but only while a report is being viewed: Microsoft no longer guarantees the extra fetches during PDF or PowerPoint export, so treat override as report-viewing only.
- **Provider:** `vegaLite` (default) or `vega` (when Vega-specific features needed)
- **Render modes:** `svg` (default, sharp text) or `canvas` (better for large datasets)
- **Continuous view (2.0):** `dataLimit.enableIncrementalDataUpdates` patches data into the live view instead of recompiling, preserving zoom, pan and selection state, up to `incrementalUpdateThreshold` rows (default 500, ceiling 5,000). Off by default; see `references/capabilities.md`.
- **Canvas scaling (2.0):** `stateManagement.scaleToZoom` multiplies canvas resolution by the report zoom. Canvas only, off by default; see `references/capabilities.md`.

## Deneb 2.0 and the transition

Two Deneb versions are live at once. Deneb 2.0.0.0 was published on GitHub on 2026-09-08; the AppSource rollout that updates every report in the wild was estimated at around 2026-09-24 and may vary by region (Verified 2026-09-08, release post on the Deneb docs site).
Retest: `gh release list -R deneb-viz/deneb --limit 3` and the AppSource listing's version number.

Until a report is confirmed on 2.0, author for both:

- **Container signals.** Read `developer.version` in the visual.json. A 2.0.0.0 or later stamp means the visual was saved by 2.0: use `denebContainer.width` / `denebContainer.height`. A 1.x stamp, no stamp, or an unconfirmed target environment: keep `pbiContainerWidth` / `pbiContainerHeight`, which 1.9 understands natively and 2.x rewrites at parse time. Flip either way with `deneb_spec.py migrate --signals modern|legacy` (`deneb-pbir` skill).
- **`$schema` never goes inside `jsonSpec`.** Keep it in standalone spec files only. The 2.0 editor flags a root `$schema` with a warning and a Quick Fix because the certified visual cannot fetch it; `deneb_spec.py embed` strips it and `extract` adds a v6 one back.
- **Stamps are opt-in.** Hand-authored visuals omit `developer.version`, `vega.version` and the `stateManagement` 2.0 properties unless the spec needs consolidated field parameters or a lean dataset. See "Compatible shape for a hand-authored visual" in `references/pbir-structure.md`.

The full compatibility story, what 2.0 rewrites on first open, the audit and migrate commands and the docs errors found so far live in [`references/deneb-2-migration.md`](references/deneb-2-migration.md): [compatibility matrix](references/deneb-2-migration.md#compatibility-matrix), [authoring rules during the transition](references/deneb-2-migration.md#authoring-rules-during-the-transition), [audit and migrate a visual](references/deneb-2-migration.md#audit-and-migrate-a-visual), [docs errors and unverified claims](references/deneb-2-migration.md#docs-errors-and-unverified-claims).

## Custom Visual Registration (Required)

Register `deneb7E15AEF80B9E4D4F8E12924291ECE89A` in `report.json` `publicCustomVisuals` array manually. Without this, the visual shows "Can't display this visual."

For more information, use the `pbir-format` skill and check the `report.md` reference.

```json
{
  "publicCustomVisuals": ["deneb7E15AEF80B9E4D4F8E12924291ECE89A"]
}
```

## Workflow: Creating a Deneb Visual

### Step 1: Add the Visual

Create the visual.json file manually (see `pbir-format` skill in the pbip plugin for JSON structure) with `visualType: deneb7E15AEF80B9E4D4F8E12924291ECE89A`, field bindings for the columns and measures you need, and position/size as required.

All fields bind to the single `dataset` role. Use `Table.Column` for columns and `Table.Measure` for measures. Field names in bindings must match those used in the Vega/Vega-Lite spec.

### Step 2: Write the Spec

Create a Vega-Lite (or Vega) JSON spec file. Key difference:

- **Vega-Lite:** `"data": {"name": "dataset"}` (object)
- **Vega:** `"data": [{"name": "dataset"}]` (array)

```json
{
  "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
  "data": {"name": "dataset"},
  "mark": {"type": "bar", "tooltip": true},
  "encoding": {
    "y": {"field": "Category", "type": "nominal"},
    "x": {"field": "Value", "type": "quantitative"}
  }
}
```

See `examples/spec/` for complete spec files (Vega and Vega-Lite) and `examples/visual/` for full PBIR visual.json files. Field names in the spec must match the display label in the Values well: `displayName` when the projection sets one, otherwise `nativeQueryRef` (which is the field's real native name in the model). See the field-naming contract in `references/pbir-structure.md`.

### Step 3: Inject the Spec

Set the spec and config in the visual's `objects.vega[0].properties` as single-quoted DAX literal strings. The `jsonSpec` property holds the Vega spec (stringified JSON), `jsonConfig` holds the config, and `provider` is set to `'vega'` or `'vegaLite'`. See the PBIR structure reference (`references/pbir-structure.md`) for the full encoding pattern.

**Escaping rules for visual.json injection:**

The spec JSON must be stringified into a single line and wrapped in single quotes inside the `expr.Literal.Value`:

```json
"jsonSpec": {"expr": {"Literal": {"Value": "'{\"data\":[{\"name\":\"dataset\"}],\"marks\":[...]}'" }}}
```

- The entire JSON spec is flattened to one line, with the root `$schema` removed first (it belongs in the standalone file only; `deneb_spec.py embed` strips it for you)
- All inner double quotes (`"`) become `\"` (standard JSON string escaping)
- The stringified JSON is wrapped in single quotes: `'...'`
- Field names with spaces inside Vega expressions use doubled single quotes: `datum[''Sales Amount'']`
- See `examples/visual/` for complete real-world visual.json files showing this encoding

### Step 3b: Review

Before presenting the spec to the user, dispatch the `deneb-reviewer` agent to validate syntax and provide design feedback.

### Step 4: Validate

Validate JSON syntax with `jq empty <visual.json>`, then run `python deneb_spec.py audit <visual.json>` (`deneb-pbir` skill) to get the Deneb build stamp, provider, legacy versus `denebContainer` signal references, a root `$schema` inside the literal, `__identity__`/`__key__` leftovers, an `enableContextMenu false` warning and the `supportFieldConfiguration` parse check in one verdict line. Then inspect the visual.json to confirm spec content and field bindings.

With Desktop open, finish in the 2.0 debug pane: the Source tab (Ctrl+Alt+6) shows the Deneb dataset as it arrives, before any Vega transform, so it is where you confirm that the supporting fields the spec reads are actually present and that a consolidated field parameter really is arriving as arrays; the Data tab (Ctrl+Alt+7) shows the Vega named datasets after transforms, which is where a `flatten` is checked. Without Desktop, render offline with the `deneb-pbir` skill's `render.mjs` instead, which sees neither tab's contents (Verified 2026-09-08 from `getting-started/visual-editor.mdx` and the 2.0.0 changelog on the Deneb docs site, where the Source tab and its shortcut are listed as new in 2.0; read from the docs, not run in Desktop).
Retest: open a Deneb 2.0.0.0 visual in Desktop and press Ctrl+Alt+6 then Ctrl+Alt+7.

## Spec Authoring Rules

### Data Binding

- Vega: `"data": [{"name": "dataset"}]` (array form)
- Vega-Lite: `"data": {"name": "dataset"}` (object form)
- Fields reference display names. Special characters (`.`, `[`, `]`, `\`, `"`) become `_`
- Spaces are NOT replaced -- field names keep their spaces (e.g., `"Order Lines"`)

### Field Name Escaping in Expressions (Critical)

Escaping depends on whether the spec is standalone or injected into a PBIR visual.json:

**Standalone spec files** (in `examples/spec/`): use double quotes with JSON escaping:

```json
{"calculate": "datum[\"Order Lines\"] - datum[\"Order Lines (PY)\"]", "as": "diff"}
```

**Inside PBIR visual.json** (in `examples/visual/`): the entire spec is a single-quoted DAX literal string. Field names with spaces use doubled single quotes (`''`):

```
datum[''Order Lines''] - datum[''Order Lines (PY)'']
```

Single quotes that are NOT part of field name escaping (e.g., string literals in filter expressions like `datum.Series == 'Actuals'`) work as-is because they don't conflict with the outer single-quote wrapper.

### Responsive Sizing (Vega)

Use Deneb's built-in signals for responsive container sizing. Two names exist for the same thing:

```json
"width": {"signal": "pbiContainerWidth - 25"},
"height": {"signal": "pbiContainerHeight - 27"}
```

```json
"width": {"signal": "denebContainer.width - 25"},
"height": {"signal": "denebContainer.height - 27"}
```

The offsets account for padding. For absolute positioning of text marks, use `{"signal": "width"}` instead of hardcoded pixel values.

- `pbiContainerWidth`, `pbiContainerHeight` and the `pbiContainer` object are the pre-2.0 names. They work natively on 1.9 and on every 2.x build, where Deneb rewrites them to `denebContainer` over the raw spec text with word-boundary regexes and logs one warning per session (removal target 3.0). The rewrite is textual, so the same names inside a title or tooltip string are rewritten too.
- `denebContainer` is the 2.0 signal (Vega) or param (Vega-Lite, readable from any `expr`): an object with six numeric properties, `width`, `height`, `scrollWidth`, `scrollHeight`, `scrollTop`, `scrollLeft`. It does not exist on 1.9, where a spec that references it is expected to fail parsing: that failure is inferred from Vega's parser and has not been reproduced in a 1.9.1 Desktop, so see the "`denebContainer` fails to parse on Deneb 1.9" gotcha below before relying on the exact symptom.
- **Rule during the transition:** `developer.version` 2.0.0.0 or later in the visual.json means use `denebContainer.*`; a 1.x stamp, no stamp, or an unconfirmed environment means keep the legacy pair. The pattern files and examples keep the legacy pair for now; see [authoring rules during the transition](references/deneb-2-migration.md#authoring-rules-during-the-transition).

### Config (Separate from Spec)

Always provide a config file for consistent styling. See the Standard Config section in `references/vega-patterns.md`. Key settings: `autosize: fit`, `view.stroke: transparent`, `font: Segoe UI`.

## Theme Integration

Use Power BI theme colors instead of hardcoded hex values:

| Function/Scheme | Purpose | Usage in Vega |
|-----------------|---------|---------------|
| `pbiColor(index)` | Theme color by index (0-based) | `{"signal": "pbiColor(0)"}` |
| `pbiColor(0, -0.3)` | Darken theme color by 30% | Shade: -1 (dark) to 1 (light) |
| `pbiColor("negative")` | Sentiment colors | `"negative"`, `"neutral"`, `"positive"` |
| `pbiColor("min")` | Divergent colors | `"min"`, `"middle"`, `"max"` |
| `pbiColor("bad")` | The only two aliases | `"bad"` = `"negative"`, `"good"` = `"positive"`. `"neutral"` is a registered name of its own (the theme's sentiment neutral), not an alias for `"middle"`; the default theme merely gives both the same color |
| `pbiColorNominal` | Categorical palette (distinct) | `"range": {"scheme": "pbiColorNominal"}` |
| `pbiColorOrdinal` | Ordinal palette (ordered categories) | `"range": {"scheme": "pbiColorOrdinal"}` |
| `pbiColorLinear` | Continuous gradient | `"range": {"scheme": "pbiColorLinear"}` |
| `pbiColorDivergent` | Divergent gradient | `"range": {"scheme": "pbiColorDivergent"}` |

Those eight names (`min`, `middle`, `max`, `negative`, `bad`, `positive`, `good`, `neutral`) are the whole set; an unknown name falls through to an index lookup and lands on theme color 1 (Verified 2026-09-08 from `getNamedColors` in `packages/vega-runtime/src/lib/extensibility/scheme/powerbi.ts` on Deneb main at cd23465, three commits past tag `2.0.0.0`; read from source, not from a running theme).
Retest: in a Deneb visual, fill four marks with `pbiColor('neutral')`, `pbiColor('middle')`, `pbiColor('good')` and `pbiColor('nonsense')` under a theme whose sentiment and divergent colors differ, and compare.

### Expression functions

Deneb registers exactly six Vega expression functions: `pbiColor`, `pbiFormat`, `pbiFormatAutoUnit`, `pbiPatternSVG`, `pbiCrossFilterApply` and `pbiCrossFilterClear`. None is new in 2.0. The formatting and pattern ones:

| Function | Purpose | Example |
|----------|---------|---------|
| `pbiFormat(value, format, options?)` | Format with a Power BI format string (not d3), in the report locale unless `options.cultureSelector` overrides it. 2.0 bundles only the locales Microsoft supports for custom visuals, so a locale that formatted under 1.9 can stop resolving: check the output before assuming the format string is at fault | `{"signal": "pbiFormat(datum['$ Sales'], '$#0,,,.0bn')"}` |
| `pbiFormat(value, options)` | Same, options object only: `format`, `precision`, `value` (1e3, 1e6, 1e9, 1e12 picks the unit), `cultureSelector` | `pbiFormat(datum.value, {format: '#0.0', value: 1e9})` |
| `pbiFormatAutoUnit(value, format?, options?)` | As `pbiFormat` but picks the nearest unit (K, M, bn) the way the Auto display unit does | `{"signal": "pbiFormatAutoUnit(datum['$ Sales'])"}` |
| `pbiPatternSVG(pattern, foreground?, background?)` | SVG pattern fill from Deneb's built-in set (`diagonal-stripe-1` to `-6`, `dots-1` to `-9`, `circles-*`, `horizontal-stripe-*`, `vertical-stripe-*`, `crosshatch`, `houndstooth`, intensity suffixes `-10` to `-90`). SVG renderer only: under `canvas` the mark gets no fill | `{"expr": "pbiPatternSVG('diagonal-stripe-3', '#DA9A0F', '#333333')"}` |

In Vega-Lite the same formatters are custom format types: wherever `format` is accepted, set `"formatType": "pbiFormat"` (or `"pbiFormatAutoUnit"`) and give a Power BI format string, e.g. `{"axis": {"format": "$#0,,,.0bn", "formatType": "pbiFormat"}}` or `{"axis": {"format": "MMM yyyy", "formatType": "pbiFormat"}}`. Deneb sets `customFormatTypes: true` in the config for you; the offline renderer in the `deneb-pbir` skill does the same, but its `pbiFormat` output is an approximation, not Power BI's formatter.

The locale trimming behind that `pbiFormat` caveat landed in 2.0 (deneb-viz/deneb#593, to shrink the package): only the locales Microsoft lists as supported for custom visuals are bundled now, and the release notes invite an issue if one that used to work has gone (Verified 2026-09-08 from the 2.0.0 changelog on the Deneb docs site; read from the docs, not tested in a report set to a trimmed locale).
Retest: set the report (or `developer.locale`) to the locale in question, format the same measure with `pbiFormat` and with Power BI's own formatting, and compare.

## Interactivity

Enable interactivity via the `vega` objects in visual.json:

| Feature | Property | Default | Notes |
|---------|----------|---------|-------|
| Tooltips | `enableTooltips` | `true` | Vega: `"tooltip": {"signal": "datum"}` in encode. Vega-Lite: `"mark": {"tooltip": true}`. Report-page tooltips need `__row__` in the datum. `tooltipDelay` (ms, default 0) exists. Sentence-template tooltips (Power BI, June 2026) read only fields that are explicit members of the tooltip datum, so enumerate them: an explicit `tooltip` encoding channel in Vega-Lite, or an `encode` entry that lists them in Vega. The sentence itself is a Power BI container property, so it does not travel with a Deneb template |
| Context menu shown | `enableContextMenu` | `true` | 2.0: whether the Power BI right-click menu appears at all; `false` swallows right-click so the spec can own it. Pre-2.0 it meant "no data-point resolution" |
| Context menu data points | `enableContextMenuSelector` | `true` | New in 2.0. Whether Deneb resolves the clicked datum for drill-through. Lives under `objects.vega` |
| Cross-filtering | `enableSelection` | `false` | Requires `__selected__` handling |
| Cross-highlighting | `enableHighlight` | `false` | Measures get `<field>__highlight`; status and comparator are opt-in on 2.0-stamped visuals |

The sentence-template rule above comes from Deneb's own tooltip page and is the only guidance available so far (Verified 2026-09-08 from `interactivity/tooltips.md` on the Deneb docs site, describing the Power BI June 2026 feature; not built in Desktop).
Retest: give a Deneb visual a sentence-template tooltip naming two fields, hover a mark with `"tooltip": true` on the mark, then again with an explicit `tooltip` channel listing both fields.

**Authoring rule for the context menu:** a visual that wants the menu without data-point resolution sets `enableContextMenu true` + `enableContextMenuSelector false` explicitly. Never author `enableContextMenu false` unless the intent is to suppress the menu under 2.0, and accept that 1.9 reads the same value as "menu shown, no resolution". Deneb only remaps an old `enableContextMenu false` to the new pair when the file carries both `developer.version` (below 2.0.0) and `vega.version`; a hand-authored visual with no stamps is honoured literally.

### Cross-Filtering

When `enableSelection` is true, handle `__selected__` (`"on"`, `"off"`, `"neutral"`) in encode blocks. Selection modes: `simple` (auto-resolves, `selectionMaxDataPoints` 1-250, default 50) or `advanced` (Vega only; required for brush/lasso/region selection, supports up to 2500 via `options.limit`, and exposes the expression functions `pbiCrossFilterApply(event, filter?, options?)` and `pbiCrossFilterClear()`, called from a signal's `update` expression). See `references/vega-patterns.md` for the simple pattern and `references/advanced-patterns.md` for the advanced API.

### Cross-Highlighting

Use layered marks -- background at reduced opacity, foreground shows `<field>__highlight` values. See `references/vega-patterns.md` for details.

### Special Runtime Fields

Deneb injects runtime fields into each dataset row. See `references/capabilities.md` for the full table.

Key fields: `__row__` (zero-based row index, always present, replaces removed `__identity__`), `__selected__` (selection state, only when `enableSelection` is on), `<field>__highlight` + `<field>__highlightStatus` + `<field>__highlightComparator` (cross-highlighting, measures only), `<field>__formatted` (pre-formatted value string), `<field>__format` (Power BI format string), `<parameter>__names` (component display names of a consolidated field parameter, 2.0).

Which of the per-field ones exist depends on how the visual is classified under 2.0:

- **Unstamped or migrated** (real spec, no `denebMetaVersion`): Deneb stamps the pre-2.0 set on first open. Measures get `__format` and `__formatted`, plus the highlight trio only if `enableHighlight` was already true at that moment; columns get none. The stamped entries are then frozen, so switching cross-highlight on later does not add `__highlight` until the flag is ticked in the Supporting fields pane or in `supportFieldConfiguration`. If the spec reads `__highlight`, author `enableHighlight true` before the file is first opened under 2.0 (Verified 2026-09-08 from `resolve-defaults.ts` lines 31-39 and `build-processing-plan.ts` lines 128-153 on Deneb main at cd23465, three commits past tag `2.0.0.0`, where neither file changed; not observed in Desktop).
  Retest: migrate a 1.9 visual with highlight off, enable "Expose cross-highlight values", check the debug Source tab for `__highlight` columns.
- **Stamped 2.0** (`denebMetaVersion '2'`): lean role defaults. Measures get `__highlight` only when `enableHighlight` is on; `__highlightStatus`, `__highlightComparator`, `__format` and `__formatted` are opt-in per field through `supportFieldConfiguration`, for columns as well as measures. Field parameters get `__highlight` under the same condition and nothing else, `__names` included.
- **Consolidated field parameters** make every companion an array (one entry per component) instead of a scalar.

The 1.9 behaviour was "every supporting field Deneb can add is present". The defaults matrix is in `references/capabilities.md`.

> **Breaking change in 1.9:** `__identity__` and `__key__` were removed. Replace any `datum.__identity__` with `datum.__row__`.

## Field parameters (2.0)

Deneb 2.0 detects a field parameter from the model metadata and, with **consolidation** on, merges its components into ONE array-valued column named after the parameter (its display name, not the component's), with matching array companions `<parameter>__names`, `__highlight`, `__highlightStatus`, `__highlightComparator`, `__format`, `__formatted`. Component order follows the data view. Unpack with a `flatten` transform; `__row__` survives it so tooltips and cross-filtering keep resolving:

```json
"transform": [{"flatten": ["Metric", "Metric__names"]}],
"encoding": {
  "x": {"field": "Metric", "type": "quantitative"},
  "color": {"field": "Metric__names", "type": "nominal"}
}
```

In Vega the same is `{"type": "flatten", "fields": ["Metric", "Metric__names"]}` on a derived dataset. `__names` is opt-in: set `"names": true` in the parameter's `supportFieldConfiguration` entry.

- **PBIR switches:** in a Desktop-saved visual the `dataset` projections hold the parameter's currently expanded component field(s), not the parameter column itself, and a sibling `queryState.dataset.fieldParameters[]` entry names the parameter and points `index`/`length` at that slice (shape in `references/pbir-structure.md`); the only Deneb-side switch is `stateManagement.consolidateFieldParameters`. `pbir visuals bind` has no field-parameter option, so hand-author that entry (Verified 2026-09-08 with pbir 0.9.29).
  Retest: `pbir visuals bind --help` and look for a parameter or field-parameter flag.
- **Default for migrated and unstamped visuals is pass-through:** the first-open stamp pins `consolidateFieldParameters false`, components arrive as ordinary columns and measures, and a `flatten` on the parameter name finds nothing. To get consolidation, stamp `denebMetaVersion '2'`, `consolidateFieldParameters true` and an explicit `supportFieldConfiguration` together (never one of them alone: with `denebMetaVersion` or a non-empty configuration present and the flag absent, Deneb's code default is `true`, which is not the `false` the PBIR guide documents).
- A consolidated-parameter spec is 2.0-only; 1.9 has no consolidation and always passes components through. "Treat as field parameter" (`treatAsParameter` flag) wraps a normal field in a one-element array so a `flatten` spec can be tested without a real parameter.

## Gotchas (hard-won)

- **Dataset field names are the DISPLAY names from the Values well, and `nativeQueryRef` is not a rename.** To feed a spec expecting `datum['Amount']` from a measure named `NM Amount`, the projection must carry `"nativeQueryRef": "NM Amount", "displayName": "Amount"`. Getting this wrong fails silently: the query runs, the fields arrive under their native names, every spec reference is undefined, and a null-guarded spec renders an intact skeleton with all-blank cells (axes with explicit scale domains draw even with zero rows). Nothing errors. (Verified 2026-08-24, PL Bridge Demo.)

- **Cross-filtering OUT of a Deneb visual does not behave like a native visual.** An in-visual "slicer" built from Vega signals will not filter the rest of the report. For report-level filtering, place a native slicer next to the Deneb visual and treat Deneb selection as internal to the visual unless `enableSelection` is explicitly configured and tested.
- **Deneb's native tooltip cannot be styled per-point.** For colored/conditional tooltips, build custom Vega tooltip marks inside the spec.
- **`jq empty` / `pbir validate` is necessary but not sufficient.** The final check is Desktop/Service rendering; use the `pbi-verify-loop` skill when Desktop is open.
- **Editing an existing spec: use round-trip tooling, not hand-edits.** The spec is a single-quote-wrapped PBIR literal (embedded `'` doubled). Extract → edit → offline-render → embed via the `deneb-pbir` skill's `deneb_spec.py` + offline renderer; never hand-edit the literal string.
- **Vega-Lite: the `xOffset`/`yOffset` *encoding channel* re-anchors marks to the start of the band.** Any layer carrying an offset encoding is positioned from the band's edge instead of its centre, so it drifts half a band away from its own axis labels, and away from any layer that lacks the offset. `axis.bandPosition: 0`, `y.band: 0.5` and `"scale": null` on the offset all fail to correct it. Use **`mark.xOffset` / `mark.yOffset` with a datum expression** instead, `{"expr": "(datum.Rank - (datum.N + 1) / 2) * 11"}`, which is a plain pixel shift with no re-anchoring, and is resolution-independent so it survives Deneb's autosize. This is the way to dodge tied points apart so none hides behind another.
- **Vega-Lite: `fontWeight` is a mark property, not an encoding channel.** Put it inside an `encoding` block and the spec compiles with only a warning, then the channel is silently dropped: the text renders at the default weight, and no error appears in Deneb, in Desktop, or in an offline render. In full Vega it is a normal mark property inside an `encode` block, which is why `references/vega-patterns.md` sets `"fontWeight": {"value": "bold"}` legitimately; the restriction is Vega-Lite's alone. To make weight depend on the data, split the text mark into two layers and filter each:

  ```json
  "layer": [
    {"transform": [{"filter": "datum.isTotal"}],
     "mark": {"type": "text", "fontWeight": "bold"}},
    {"transform": [{"filter": "!datum.isTotal"}],
     "mark": {"type": "text", "fontWeight": "normal"}}
  ]
  ```

  The layer split is required, not a workaround to tidy away into `"mark": {"type": "text", "fontWeight": {"expr": "datum.isTotal ? 'bold' : 'normal'"}}`: a Vega-Lite mark-property expression has no per-row `datum` in scope, so that form cannot see the field it tests.
- **Don't put a literal `width`/`height` in a Deneb spec; a user signal of that name is a different thing.** With `autosize: fit` in the config, Deneb sizes the view from the container; a literal `"width": 400` fights it and produces a scrollbar inside the visual. Keep the spec size-free and inject dimensions only when rendering offline. A signal (Vega) or param (Vega-Lite) *named* `width` or `height` is now honoured instead of overwritten: 2.0 injects its container sizing only when the spec's `width` is null and no user signal called `width` exists, and the same test for `height`. That is bug fix #417, where a custom `width`/`height` signal used to break compilation (Verified 2026-09-08 from `packages/vega-runtime/src/lib/spec-processing/patch-vega.ts` lines 36-78 on Deneb main at cd23465, three commits past tag `2.0.0.0`, where that file did not change; not reproduced in Desktop). On 1.9 keep such a signal out of the spec.
  Retest: add `{"name": "width", "update": "pbiContainerWidth - 40"}` to a Vega spec's `signals` (legacy name, so both builds understand it), open the visual under Deneb 2.0.0.0 and then 1.9.1.0, and compare the Logs pane.
- **Report-page tooltips: `visualTooltip.type` is `'Canvas'`, not `'ReportPage'`.** See the `pbir-format` skill's `references/page.md`. Deneb honours the Power BI tooltip service, but with the wrong enum value nothing ever appears.
- **The 2.0 changelog's PBIR table names a property path that does not exist.** It says `objects.interactivity.enableContextMenuSelector`; there is no `interactivity` object in Deneb's capabilities. The property lives under `objects.vega`, next to `enableContextMenu` (the capabilities file, the PBIR guide and the sample workbook all agree). Copying the changelog path into a visual.json produces a property Deneb never reads.
- **`enableContextMenu false` in an unstamped visual.json hides the menu under 2.0.** The pre-2.0 meaning was "menu shown, no data-point resolution". Deneb 2.0 only remaps that old value when the file carries both `developer.version` (below 2.0.0) and `vega.version`; a hand-authored visual with neither takes the unversioned path, gets version stamps only, and is then honoured literally: right-click is swallowed and drill-through is gone. Write `enableContextMenu true` + `enableContextMenuSelector false` instead (Verified 2026-09-08 from `src/lib/persistence/migration.ts` lines 306-313 and 352-361 on Deneb main at cd23465, three commits past tag `2.0.0.0`, where that file did not change; not reproduced in Desktop).
  Retest: hand-author `enableContextMenu false` with no stamps, open in Desktop with Deneb 2.0.0.0, right-click the visual.
- **`denebContainer` fails to parse on Deneb 1.9.** Vega rejects the spec with `Unrecognized signal name: "denebContainer"` because 1.9 never defines it; the visual renders nothing. The offline renderer throws the same error under Vega 6.2.0 (the 1.9 bundle), and `render.mjs --deneb 1.9` exits 2 on any `denebContainer` reference. Until the report is confirmed on 2.0, keep `pbiContainerWidth` / `pbiContainerHeight` (inferred from Vega's parser behaviour, Verified 2026-09-08 offline; not reproduced in a 1.9.1 Desktop).
  Retest: in a Desktop running Deneb 1.9.1.0, set a Vega visual's `width` to `{"signal": "denebContainer.width"}` and read the Logs pane.

## Best Practices

1. **Use Vega-Lite** for new visuals unless Vega-specific features are needed (signals, events, force layouts)
2. **Always use `autosize: fit`** in config for responsive Power BI sizing
3. **Use the container signals** for responsive Vega specs: `denebContainer.width`/`denebContainer.height` when the visual.json carries `developer.version` 2.0.0.0 or later, otherwise `pbiContainerWidth`/`pbiContainerHeight` (see Responsive Sizing above)
4. **Use theme colors** (`pbiColor`, `pbiColorNominal`) instead of hex values
5. **Use `enter`/`update`/`hover`** encode blocks for clean state management (Vega only)
6. **Enable tooltips** with `"tooltip": {"signal": "datum"}` on marks
7. **Performance** -- aggregate in DAX first, bind only the fields the spec reads and (on 2.0-stamped visuals) switch off supporting fields it does not read, prefer `renderMode: canvas` for many marks, consider continuous view for slicer-driven updates, and only then raise `dataLimit.override` (30,000-row window in 2.0, override is report-viewing only). See `references/advanced-patterns.md` for the full lever order
8. **Test field names** -- verify the projection's display label (`displayName` when set, otherwise `nativeQueryRef`) matches spec field references
9. **Avoid external data** -- AppSource certification prevents loading external URLs
10. **Escaping depends on context** -- double quotes in standalone specs, doubled single quotes in PBIR visual.json (see escaping rules above)

## When to Use Deneb

Deneb is the preferred choice for **advanced custom visuals** that need interactivity (cross-filtering, tooltips, hover effects) and go beyond what native Power BI visuals offer. Use Deneb when you need:

- Custom chart types not available natively (bullet charts, beeswarms, sankeys, etc.)
- Fine-grained control over visual encoding, animation, and interactivity
- Vector-based rendering (crisp at any size)

**Use SVG measures instead** for simple inline graphics in tables/cards (sparklines, data bars, progress bars) where interactivity is not needed. **Use Python/R instead** for statistical visualizations (distribution analysis, regression, correlation) where the focus is analytical rigor over interactivity.

## References

- **`references/community-examples.md`** -- 170+ community templates organized by chart type, with author citations and direct links
- **`references/vega-patterns.md`** -- Vega chart patterns (bar, line, scatter, donut, stacked, heatmap, area, lollipop, bullet, KPI card), standard config, transforms and scales reference
- **`references/vega-lite-patterns.md`** -- Vega-Lite chart patterns (for editing existing Vega-Lite visuals only)
- **`references/pbir-structure.md`** -- PBIR JSON structure (literal encoding, query state, the field-naming contract of `displayName` vs `nativeQueryRef` and its all-blank-skeleton failure, interactivity example)
- **`references/capabilities.md`** -- Full Deneb 2.0 object properties reference (with 1.9 deltas), template format (`usermeta` v2 schema, v1 legacy shape) and the supporting-fields defaults matrix
- **`references/deneb-2-migration.md`** -- Deneb 2.0 migration and compatibility: timeline, what 2.0 changes on first open, compatibility matrix, authoring rules during the transition, audit/migrate commands, docs errors and unverified claims, the dated follow-up for flipping the defaults
- **`references/advanced-patterns.md`** -- Advanced cross-filtering (Vega expression functions `pbiCrossFilterApply`/`pbiCrossFilterClear`), performance engineering lever order, and community template round-trip from the terminal
- **`examples/visual/bullet-chart.json`** -- PBIR visual.json: faceted bullet chart with conditional indicators and cross-filtering (Vega-Lite)
- **`examples/visual/kpi-card.json`** -- PBIR visual.json: KPI card with layered text and conditional % change coloring (Vega-Lite)
- **`examples/visual/trend-line.json`** -- PBIR visual.json: dual-series line chart with fold transform and color/legend mapping (Vega-Lite)
- **`examples/visual/ytd-comparison.json`** -- PBIR visual.json: YTD vs target with dashed lines, endpoint labels, number formatting, and rank-based filtering (Vega-Lite)
- **`examples/spec/vega/`** -- Standalone Vega spec files (bar-chart, line-chart) -- ready to inject into visual.json after escaping
- **`examples/spec/vega-lite/`** -- Standalone Vega-Lite spec files (bullet-chart, kpi-card) -- ready to inject after escaping
- **`examples/standard-config.json`** -- Standard config for all Deneb specs

## Fetching Docs

To retrieve current Power BI custom visual docs, use `microsoft_docs_search` + `microsoft_docs_fetch` (MCP) if available, otherwise `mslearn search` + `mslearn fetch` (CLI). Search based on the user's request and run multiple searches as needed to ensure sufficient context before proceeding. Note: Vega/Vega-Lite docs live at vega.github.io (not MS Learn) -- use `WebFetch` for those.

## Related Skills

- **`performant-matrix`** -- diagnose a slow matrix before assuming Deneb; the bridge/native/Deneb decision
- **`deneb-pbir`** -- round-trip tooling for editing an existing spec: `deneb_spec.py extract <visual.json> -o spec.json` / `embed [--keep-schema]` for the literal, `audit` for the one-line 2.0 readiness verdict, `migrate [--signals modern|legacy] [--strip-schema] [--dry-run]` to flip container signal names, and the offline Vega to PNG/SVG renderer (`render.mjs`, with `--width`/`--height` for the container size and `--deneb 1.9|2.0` to fail fast on the wrong signal names) to verify without Power BI
- **`pbir-format`** (pbip plugin) -- PBIR JSON format reference
- **`pbi-report-design`** -- Layout and design best practices
- **`r-visuals`** -- R Script visuals (ggplot2)
- **`python-visuals`** -- Python Script visuals (matplotlib)
- **`svg-visuals`** -- SVG via DAX measures (lightweight inline graphics)
