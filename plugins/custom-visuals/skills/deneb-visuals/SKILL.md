---
name: deneb-visuals
version: 26.40.3
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

A Vega-Lite spec that outgrows Vega-Lite can be converted in the 2.0 editor, one way only, so extract it first: [`references/editions-and-editor.md`](references/editions-and-editor.md#convert-a-vega-lite-spec-to-vega).

## Visual Identity

- **visualType:** `deneb7E15AEF80B9E4D4F8E12924291ECE89A` (the AppSource, certified edition: the one this skill assumes)
- **Other editions and the current build:** the Standalone, Alpha and Beta GUIDs, why moving a visual between editions is a rebuild, and the bundled versions (Deneb 2.0.0.0: Vega 6.4.0 / Vega-Lite 6.4.3, so `v6.json` schema URLs) are in [`references/editions-and-editor.md`](references/editions-and-editor.md#editions-and-builds).
- **Data role:** Single `dataset` role (all fields go into one "Values" well)
- **Default row window:** 30,000 rows in 2.0, 10,000 in 1.9 and earlier. `dataLimit.override` fetches more in 10,000-row batches during report viewing only, not in PDF or PowerPoint export.
- **Provider:** `vegaLite` (default) or `vega` (when Vega-specific features needed)
- **Render modes:** `svg` (default, sharp text) or `canvas` (better for large datasets)
- **2.0 options, off by default:** continuous view (`dataLimit.enableIncrementalDataUpdates`) and canvas `stateManagement.scaleToZoom`; see `references/capabilities.md`.

## Deneb 2.0 and the transition

Deneb 1.9 and 2.0.0.0 are both live. Until a report is confirmed on 2.0, author for both: the container signals follow the visual.json's `developer.version` stamp, `$schema` never goes inside `jsonSpec`, and a hand-authored visual leaves the 2.0 stamps out unless the spec needs them. The rules, the compatibility matrix, what 2.0 rewrites on first open and the audit and migrate commands are in [`references/deneb-2-migration.md`](references/deneb-2-migration.md#authoring-rules-during-the-transition).

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

- One line, root `$schema` removed, inner `"` escaped as `\"`, the whole wrapped in `'...'`; field names with spaces in expressions use doubled single quotes (`datum[''Sales Amount'']`). `deneb_spec.py embed` does all of it; `examples/visual/` has real files

### Step 3b: Review

Before presenting the spec to the user, dispatch the `deneb-reviewer` agent to validate syntax and provide design feedback.

### Step 4: Validate

Validate JSON syntax with `jq empty <visual.json>`, then run `python deneb_spec.py audit <visual.json>` (`deneb-pbir` skill) for a one-line 2.0 readiness verdict (build stamp, provider, signal family, embedded `$schema`, leftovers, context menu, field configuration). Then inspect the visual.json to confirm spec content and field bindings.

With Desktop open, finish in the 2.0 debug pane (Source tab Ctrl+Alt+6, Data tab Ctrl+Alt+7); without it, render offline with the `deneb-pbir` skill's `render.mjs`. What each tab shows: [`references/editions-and-editor.md`](references/editions-and-editor.md#the-20-debug-pane).

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

An apostrophe inside a data string is different: a colour domain listing `Queen's Pawn Game` must carry it doubled (`Queen''s Pawn Game`) in the stored literal. When generating the literal from a spec object, double every single quote, `"'" + json.dumps(spec).replace("'", "''") + "'"`, which also produces the field-name form above; Power BI un-doubles on load.

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

- How 2.x rewrites the legacy names, and the six `denebContainer` properties: [`references/editions-and-editor.md`](references/editions-and-editor.md#container-signals).
- **Which to use:** `denebContainer.*` only when the visual.json carries `developer.version` 2.0.0.0 or later; otherwise the legacy pair ([transition rules](references/deneb-2-migration.md#authoring-rules-during-the-transition)).

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
| `pbiColor("bad")` | The only two aliases | `"bad"` = `"negative"`, `"good"` = `"positive"`; `"neutral"` is its own name, not `"middle"` |
| `pbiColorNominal` | Categorical palette (distinct) | `"range": {"scheme": "pbiColorNominal"}` |
| `pbiColorOrdinal` | Ordinal palette (ordered categories) | `"range": {"scheme": "pbiColorOrdinal"}` |
| `pbiColorLinear` | Continuous gradient | `"range": {"scheme": "pbiColorLinear"}` |
| `pbiColorDivergent` | Divergent gradient | `"range": {"scheme": "pbiColorDivergent"}` |

Those eight names are the whole set; an unknown name lands on theme color 1 ([`references/expression-functions.md`](references/expression-functions.md#pbicolor-names)).

### Expression functions

Deneb registers six Vega expression functions: `pbiColor`, `pbiFormat`, `pbiFormatAutoUnit`, `pbiPatternSVG`, `pbiCrossFilterApply` and `pbiCrossFilterClear`. `pbiFormat` takes a Power BI format string, not d3; in Vega-Lite set `"formatType": "pbiFormat"` wherever `format` is accepted. Signatures, the 2.0 locale trimming and the canvas limit on patterns are in [`references/expression-functions.md`](references/expression-functions.md).

## Interactivity

Enable interactivity via the `vega` objects in visual.json:

| Feature | Property | Default | Notes |
|---------|----------|---------|-------|
| Tooltips | `enableTooltips` | `true` | Vega: `"tooltip": {"signal": "datum"}` in encode. Vega-Lite: `"mark": {"tooltip": true}`. Report-page tooltips need `__row__` in the datum. `tooltipDelay` (ms, default 0) exists. Sentence-template tooltips need the fields listed explicitly ([reference](references/interactivity-and-runtime-fields.md#sentence-template-tooltips)) |
| Context menu shown | `enableContextMenu` | `true` | 2.0: whether the Power BI right-click menu appears at all; `false` swallows right-click so the spec can own it. Pre-2.0 it meant "no data-point resolution" |
| Context menu data points | `enableContextMenuSelector` | `true` | New in 2.0. Whether Deneb resolves the clicked datum for drill-through. Lives under `objects.vega` |
| Cross-filtering | `enableSelection` | `false` | Requires `__selected__` handling |
| Cross-highlighting | `enableHighlight` | `false` | Measures get `<field>__highlight`; status and comparator are opt-in on 2.0-stamped visuals |

**Context menu:** never author `enableContextMenu false` unless the menu should be suppressed under 2.0; for a menu without data-point resolution write `enableContextMenu true` + `enableContextMenuSelector false`. Why, and the sentence-template tooltip note: [`references/interactivity-and-runtime-fields.md`](references/interactivity-and-runtime-fields.md).

### Cross-Filtering

When `enableSelection` is true, handle `__selected__` (`"on"`, `"off"`, `"neutral"`) in encode blocks. Selection modes: `simple` (auto-resolves, `selectionMaxDataPoints` 1-250, default 50) or `advanced` (Vega only; required for brush/lasso/region selection, supports up to 2500 via `options.limit`, and exposes the expression functions `pbiCrossFilterApply(event, filter?, options?)` and `pbiCrossFilterClear()`, called from a signal's `update` expression). See `references/vega-patterns.md` for the simple pattern and `references/advanced-patterns.md` for the advanced API.

### Cross-Highlighting

Use layered marks -- background at reduced opacity, foreground shows `<field>__highlight` values. See `references/vega-patterns.md` for details.

### Special Runtime Fields

Deneb injects runtime fields into each dataset row. See `references/capabilities.md` for the full table.

Key fields: `__row__` (zero-based row index, always present, replaces removed `__identity__`), `__selected__` (selection state, only when `enableSelection` is on), `<field>__highlight` + `<field>__highlightStatus` + `<field>__highlightComparator` (cross-highlighting, measures only), `<field>__formatted` (pre-formatted value string), `<field>__format` (Power BI format string), `<parameter>__names` (component display names of a consolidated field parameter, 2.0).

Which per-field ones exist depends on whether the visual is unstamped, migrated or stamped 2.0, and consolidated field parameters make them arrays: [`references/interactivity-and-runtime-fields.md`](references/interactivity-and-runtime-fields.md#which-supporting-fields-exist).

> **Breaking change in 1.9:** `__identity__` and `__key__` were removed. Replace any `datum.__identity__` with `datum.__row__`.

## Field parameters (2.0)

With consolidation on, Deneb 2.0 merges a field parameter's components into one array column named after the parameter, unpacked with a `flatten` transform. It is off for migrated and unstamped visuals, and 2.0 only. The PBIR shape, the stamps that turn it on and the Vega form are in [`references/field-parameters.md`](references/field-parameters.md).

## Images and external resources

Deneb **cannot fetch anything** (an image, a dataset, a font) outside the uncertified standalone build, and a blocked resource renders blank with no error. `data:` URIs work, but `data:image/svg+xml;utf8,` is **rejected**: emit `;charset=utf-8,`. Details: [`references/images-and-external-resources.md`](references/images-and-external-resources.md).

## Gotchas (hard-won)

Read [`references/gotchas.md`](references/gotchas.md) and [`references/silent-traps.md`](references/silent-traps.md) before debugging a Deneb visual that renders blank, wrong or clipped. The ones that bite most:

- Dataset field names are the **display** names from the Values well; `nativeQueryRef` is not a rename.
- Cross-filtering out of a Deneb visual does not work like a native visual: put a native slicer beside it.
- Edit an existing spec with the `deneb-pbir` round-trip tooling, never by hand.
- No literal `width`/`height` in a spec: `autosize: fit` sizes it from the container.

## Best Practices

1. **Use Vega-Lite** for new visuals unless Vega-specific features are needed (signals, events, force layouts)
2. **Always use `autosize: fit`** in config for responsive Power BI sizing
3. **Use the container signals** for responsive Vega specs (see Responsive Sizing above)
4. **Use theme colors** (`pbiColor`, `pbiColorNominal`) instead of hex values
5. **Use `enter`/`update`/`hover`** encode blocks for clean state management (Vega only)
6. **Enable tooltips** with `"tooltip": {"signal": "datum"}` on marks
7. **Performance** -- aggregate in DAX first, bind only the fields the spec reads, prefer `renderMode: canvas` for many marks, and only then raise `dataLimit.override`. See `references/advanced-patterns.md` for the full lever order
8. **Test field names** -- verify the projection's display label (`displayName` when set, otherwise `nativeQueryRef`) matches spec field references
9. **Avoid external data** -- AppSource certification prevents loading external URLs
10. **Escaping depends on context** -- double quotes in standalone specs, doubled single quotes in PBIR visual.json (see escaping rules above)
11. **Title it in the container or the spec, never in a textbox above it**, and use one, not both. A spec title takes its font from the spec's `config`, not the theme ([`references/gotchas.md`](references/gotchas.md#titles)).

## When to Use Deneb

Deneb is the preferred choice for **advanced custom visuals** that need interactivity (cross-filtering, tooltips, hover effects) and go beyond what native Power BI visuals offer. Use Deneb when you need:

- Custom chart types not available natively (bullet charts, beeswarms, sankeys, etc.)
- Fine-grained control over visual encoding, animation, and interactivity
- Vector-based rendering (crisp at any size)

Absence from the native set means Deneb can draw the form, not that it suits the reader (the form gate is `pbi-report-design`'s `references/chart-selection.md`).

**The house split: native visuals for anything people interact with, Deneb for display-only KPIs.** Charts, tables and slicers people click stay native. A KPI nobody clicks is where Deneb earns its place: one tile can combine figures that would otherwise take four cards. Do not turn an interactive visual into static Deneb art.

**Use SVG measures instead** for simple inline graphics in tables/cards (sparklines, data bars, progress bars) where interactivity is not needed. **Use Python/R instead** for statistical visualizations (distribution analysis, regression, correlation) where the focus is analytical rigor over interactivity.

## References

- **`references/community-examples.md`** -- 170+ community templates organized by chart type, with author citations and direct links
- **`references/vega-patterns.md`** -- Vega chart patterns (bar, line, scatter, donut, stacked, heatmap, area, lollipop, bullet, KPI card), standard config, transforms and scales reference
- **`references/vega-lite-patterns.md`** -- Vega-Lite chart patterns (for editing existing Vega-Lite visuals only)
- **`references/pbir-structure.md`** -- PBIR JSON structure (literal encoding, query state, the field-naming contract of `displayName` vs `nativeQueryRef` and its all-blank-skeleton failure, interactivity example)
- **`references/capabilities.md`** -- Full Deneb 2.0 object properties reference (with 1.9 deltas), template format (`usermeta` v2 schema, v1 legacy shape) and the supporting-fields defaults matrix
- **`references/deneb-2-migration.md`** -- Deneb 2.0 migration and compatibility: timeline, what 2.0 changes on first open, compatibility matrix, authoring rules during the transition, audit/migrate commands, docs errors and unverified claims, the dated follow-up for flipping the defaults
- **`references/silent-traps.md`** -- Silent failures: report-page tooltip row resolution and hover bands, the container clip rect and the padded re-render that catches it, field-well grain, the `dataset` entry's `format`, certified loader, template placeholders, Vega-Lite compiler traps, Vega rendering traps, rendering outside Deneb
- **`references/gotchas.md`** -- Hard-won gotchas: field names, cross-filtering out, Vega-Lite offsets and `fontWeight`, size signals, hierarchy sort, keyboard focus, tooltips, titles
- **`references/editions-and-editor.md`** -- Editions and GUIDs, bundled Vega versions, Vega-Lite to Vega, container-signal rewriting, the 2.0 debug pane
- **`references/expression-functions.md`** -- The six expression functions, `pbiFormat` in Vega-Lite, locale trimming, `pbiColor` names
- **`references/interactivity-and-runtime-fields.md`** -- Sentence-template tooltips, the context menu, which supporting fields exist
- **`references/field-parameters.md`** -- Field-parameter consolidation in 2.0: arrays, `flatten`, the PBIR shape, the stamps
- **`references/images-and-external-resources.md`** -- Why Deneb fetches nothing, and which `data:` URI prefixes load
- **`references/advanced-patterns.md`** -- Advanced cross-filtering (Vega expression functions `pbiCrossFilterApply`/`pbiCrossFilterClear`), performance engineering lever order, and community template round-trip from the terminal
- **`examples/visual/bullet-chart.json`** -- PBIR visual.json: faceted bullet chart with conditional indicators and cross-filtering (Vega-Lite)
- **`examples/visual/kpi-card.json`** -- PBIR visual.json: KPI card with layered text and conditional % change coloring (Vega-Lite)
- **`examples/visual/trend-line.json`** -- PBIR visual.json: dual-series line chart with fold transform and color/legend mapping (Vega-Lite)
- **`examples/visual/ytd-comparison.json`** -- PBIR visual.json: YTD vs target with dashed lines, endpoint labels, number formatting, and rank-based filtering (Vega-Lite)
- **`examples/spec/vega/`** -- Standalone Vega spec files (bar-chart, line-chart) -- ready to inject into visual.json after escaping
- **`examples/spec/vega-lite/`** -- Standalone Vega-Lite spec files (bullet-chart, kpi-card) -- ready to inject after escaping
- **`examples/standard-config.json`** -- Standard config for all Deneb specs

## Fetching Docs

To retrieve current Power BI custom visual docs, use `microsoft_docs_search` + `microsoft_docs_fetch` (MCP) if available, otherwise search https://learn.microsoft.com and fetch the relevant pages. Search based on the user's request and run multiple searches as needed to ensure sufficient context before proceeding. Note: Vega/Vega-Lite docs live at vega.github.io (not MS Learn) -- use `WebFetch` for those.

## Related Skills

- **`performant-matrix`** -- diagnose a slow matrix before assuming Deneb; the bridge/native/Deneb decision
- **`deneb-pbir`** -- round-trip tooling for an existing spec: `deneb_spec.py extract` / `embed` / `audit` / `migrate`, and the offline renderer `render.mjs` to verify without Power BI
- **`pbir-format`** (pbip plugin) -- PBIR JSON format reference
- **`pbi-report-design`** -- Layout and design best practices
- **`r-visuals`** -- R Script visuals (ggplot2)
- **`python-visuals`** -- Python Script visuals (matplotlib)
- **`svg-visuals`** -- SVG via DAX measures (lightweight inline graphics)
