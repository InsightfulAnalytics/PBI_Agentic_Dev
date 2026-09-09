# Advanced Deneb Patterns

## Advanced Cross-Filtering (Vega only)

Simple selection mode (`selectionMode: simple`) auto-resolves `__selected__` per mark. Advanced mode is required for brush-select, lasso, region-click, or any selection that is not one-mark = one-row. It is **Vega only**; Vega-Lite cannot use it, so plan the provider from the start.

Two Vega expression functions (registered by Deneb, called from a signal's `update` expression; they are not signals themselves):

- `pbiCrossFilterApply(event, filter?, options?)` -- filter the original dataset by the optional predicate and cross-filter on the result; `event` is required as the first arg and must be the bound Vega `event` (anything else is rejected with a Logs-pane warning). `filter` is a Vega `filter` expression evaluated against the base `dataset`; `_{Field Name}_` placeholders are replaced from the clicked datum (strings single-quoted, dates become `toDate(...)`). Returns `{rowNumbers?, multiSelect?, exceedsLimit?, warning?}`; calling it while the visual is still in simple mode logs a warning and returns `{}`
- `pbiCrossFilterClear()` -- clear, no args

`options` keys: `limit` (1-2500, default 50) and `multiSelect` (array of `'ctrl'`, `'shift'`, `'alt'`; default `['ctrl','shift']`):

```json
"update": "pbiCrossFilterApply(event, \"datum['Product'] == _{Product}_\", {limit: 500, multiSelect: ['ctrl']})"
```

Basic point-click pattern:

```json
"signals": [{
  "name": "pbiCrossFilterSelection",
  "value": [],
  "on": [
    {
      "events": {"source": "scope", "type": "mouseup", "markname": "data-point"},
      "update": "pbiCrossFilterApply(event)"
    },
    {
      "events": {
        "source": "view", "type": "mouseup",
        "filter": ["!event.item || event.item.mark.name != 'data-point'"]
      },
      "update": "pbiCrossFilterClear()"
    }
  ]
}]
```

For a brush, bind a Vega `interval` selection and pass its extent into the `filter` argument. The `options.limit` key (1-2500, default 50) overrides the simple-mode 250 cap because you control row resolution. In advanced mode the default limit is the constant 50 from Deneb source, not the Format-pane `selectionMaxDataPoints` value, so set `options.limit` explicitly rather than relying on the pane. That constant was read from `cross-filter.ts` in Deneb source at `main`, three commits past the 2.0.0.0 tag; the file is absent from the diff between the two, so it reads the same at the tag. Never observed in a running Power BI (Verified 2026-09-08).

Retest: set `selectionMaxDataPoints` to 5, call `pbiCrossFilterApply(event, '')` on a 10-row filter and check whether the limit banner appears.

Retest (source only): `gh api repos/deneb-viz/deneb/compare/2.0.0.0...main --jq '.files[].filename' | grep cross-filter` returns nothing while the constant still matches the tag.

Enable it by editing `objects.vega[0].properties` in visual.json (`pbir set` has no route to a custom visual's `objects.*`, see Performance Engineering below):

```json
"selectionMode": {"expr": {"Literal": {"Value": "'advanced'"}}}
```

Pitfalls:

- Switching a working simple-mode visual to advanced silently kills cross-filtering until the signals are authored
- After aggregated marks the resolved data is at a different granularity than the base `dataset`; aliased columns must match original names or rows resolve empty
- A community-reported failure pattern: the visual filters others but never reflects an external filter back into `__selected__`; flag in review. No Deneb version or issue number backs this claim and nothing in the 2.0 docs or source describes it, so treat it as unverified
  - Retest: in advanced mode, cross-filter the Deneb visual from a native slicer and inspect `__selected__` in the debug Source tab

## Performance Engineering

A Deneb visual re-runs the whole Vega dataflow on every interaction (unless continuous view patches the data in, lever 6). Cost scales row count x mark count x per-row field count, and Deneb widens every row with supporting fields: on 1.9.x and on visuals migrated into 2.0 that means every measure's `__format`, `__formatted` and (with cross-highlight on) the highlight trio; a new or explicitly stamped 2.0 visual ships `__row__`, plus `__selected__` when `enableSelection` is on, plus a measure's or a consolidated field parameter's `__highlight` when `enableHighlight` is on (those three are role defaults, so they need no `supportFieldConfiguration` entry; on an explicitly stamped visual an entry that sets `highlight` false still wins, because stamped entries are read verbatim), plus whatever `supportFieldConfiguration` turns on. Apply levers cheapest-first:

1. **Aggregate in DAX, not Vega** -- bind a monthly measure so the model sends ~12 rows; a `transform aggregate` over 50K rows recomputes on every hover. Push grouping to the model or a visual-level Top N filter
2. **Prefer `renderMode: canvas` for many marks** -- SVG creates a DOM node per mark; canvas draws to a bitmap. Keep SVG only when marks are few, selectable text is needed, or the spec uses `pbiPatternSVG` (no fill under canvas). On a high-DPI report or when zoomed, pair canvas with `stateManagement.scaleToZoom` (off by default, canvas only) so the bitmap is drawn at the report zoom factor instead of blurring
3. **Trim marks before raising limits** -- collapse decorative layers first
4. **Drop unused supporting-field bloat** -- version-dependent. On 1.9.x and on migrated (unstamped) visuals under 2.0, every bound measure ships `<measure>__formatted` and `<measure>__format`, so the only lever is to bind fewer measures. On a 2.0-stamped visual (`denebMetaVersion '2'` plus `supportFieldConfiguration`) those fields are opt-in per field, so switch off every flag the spec does not read; a spec that reads `datum['Sales__formatted']` on such a visual gets `undefined` until `formatted: true` is set for that field. Bind only columns and measures the spec uses either way
5. **`dataLimit.override` as a last resort** -- paired with canvas; lifts the default window (30,000 rows in 2.0, 10,000 in 1.9 and earlier) and fetches more in batches of 10,000, but Microsoft no longer guarantees the extra fetches during PDF or PowerPoint export, so it is for report viewing only; the model's own row cap still applies and can truncate silently
6. **Continuous view (2.0)** -- `dataLimit.enableIncrementalDataUpdates` (off by default) patches new data into the live Vega view instead of recompiling, preserving zoom, pan, facet page, signal and selection state across slicer and cross-filter changes. It only applies when the updated dataset has at most `dataLimit.incrementalUpdateThreshold` rows (default 500, range 5-5000, hard ceiling 5,000 regardless of setting); above that, or for specs it cannot patch (e.g. force transforms with aggregates), Deneb falls back to a full recompile and logs a warning. Helps interactive specs with small datasets; row count is not a reliable cost proxy (wide rows, nested values and complex transforms dominate) and Power BI may suspend a visual whose patch takes too long, so test under realistic slicing and lower the threshold or switch it off if responsiveness drops

Set these by editing the visual.json `objects` block directly. `pbir set` has no route to a custom visual's `objects.*`: it accepts only `PATH --value X` on the report, page and visual properties it models, and an `objects.stateManagement[0]...` path is rejected with `Unknown component: objects` (pbir 0.9.29, Verified 2026-09-08). Numbers take the `D` suffix, strings are single-quoted inside the literal (encoding rules in `references/pbir-structure.md`).

Retest: `pbir set --help` for an `objects` or custom-visual property route.

```json
"objects": {
  "vega": [{"properties": {
    "renderMode": {"expr": {"Literal": {"Value": "'canvas'"}}}
  }}],
  "stateManagement": [{"properties": {
    "scaleToZoom": {"expr": {"Literal": {"Value": "true"}}}
  }}],
  "dataLimit": [{"properties": {
    "override": {"expr": {"Literal": {"Value": "true"}}},
    "enableIncrementalDataUpdates": {"expr": {"Literal": {"Value": "true"}}},
    "incrementalUpdateThreshold": {"expr": {"Literal": {"Value": "500D"}}}
  }}]
}
```

The 2.0-only properties (`scaleToZoom`, `enableIncrementalDataUpdates`, `incrementalUpdateThreshold`) are ignored by 1.9.x as far as Power BI's usual handling of undeclared object properties goes, but nobody has opened such a file under Deneb 1.9.1 here, so treat that as unverified.

Retest: open a visual.json carrying `enableIncrementalDataUpdates` in a Desktop running Deneb 1.9.1.0 and confirm it renders without a property error.

Keep the cross-filter `limit` as low as the interaction allows (simple mode caps at 250 for this reason).

Pitfalls:

- `dataLimit.override` does not remove the model-side cap; verify the expected row count actually arrives
- Canvas mode breaks SVG-dependent tooltips and makes text non-selectable; confirm tooltips still fire after switching
- A spec fine in Desktop can stall in a specific browser (Edge has had known rendering issues with large canvas specs); check the audience's browser
- Continuous view shows "active" or "inactive" in the Project setup pane; if a spec you expect to be patched keeps recompiling, read the Logs pane for the fallback reason before lowering the threshold

## Template Round-Trip (Terminal Import)

The Deneb GUI prompts for placeholder mapping on import; from a terminal you substitute manually then embed. A template is a Vega/Vega-Lite spec with a `usermeta` block. Deneb 2.0 writes usermeta v2 (`usermeta.deneb.metaVersion` 2): `usermeta.datasets` is a record keyed by dataset name (only `dataset` is surfaced) holding placeholder entries whose `key` must match `__<dataset>.<index>__` (`__dataset.0__`, `__dataset.1__`, pattern `^__[a-zA-Z0-9_]+\.\d+__$`, max 30 chars). Each entry carries `name` (max 150), optional `description` (max 300), `kind` (`column` | `measure` | `parameter` | `any`, informational, optional), `type` (`bool` | `text` | `numeric` | `dateTime` | `other`) and an optional `supportFieldConfiguration` (the same flag object as the PBIR property, without the text wrapping; all five base flags explicit, `names` and `treatAsParameter` optional). `usermeta.interactivity` maps to PBIR: `tooltip`, `contextMenu`, `contextMenuSelector` (optional, default true), `selection`, `selectionMode` (optional), `highlight` (optional), `dataPointLimit` (1-250). `usermeta.config` is the Config editor content as a STRING (JSON or JSONC), not an object. Schemas: `https://deneb-viz.github.io/schema/deneb-template-usermeta-v2.json` (current) and `...-v1.json` (legacy). The v1 form (`usermeta.dataset` flat array, keys `__0__` or free-form `__category__`, `metaVersion` 1) is still accepted by Deneb and still common in community repos, so the recipe handles both.

Steps (uses `deneb_spec.py` from the `custom-visuals:deneb-pbir` skill):

1. Audit the template as downloaded: `python deneb_spec.py audit template.json`. It reports usermeta v1 vs v2, legacy container signal references, a root `$schema`, and leftover `__identity__` / `__key__`
2. Read the dataset requirements: `usermeta.datasets.dataset` (fall back to `usermeta.dataset` for v1) for each entry's `key`, `name`, `kind`, `type`, `description` and `supportFieldConfiguration`; plus `usermeta.interactivity`, `usermeta.deneb.provider` and the `config` string. Pick one model field per entry: a column for `column`, a measure for `measure`, a field parameter (or a normal field, accepting `treatAsParameter`) for `parameter`. Deneb treats `kind` as informational and lets any field be assigned; binding a measure where a column was intended changes grouping and cardinality and usually gives a wrong picture rather than an error
3. Strip `usermeta` from the spec body (Deneb's object does not consume it). If `usermeta.config` is missing and the spec has a top-level `config` object (pre-1.7 template), move that object out to become the config; otherwise parse the `usermeta.config` string (strip JSONC comments first) into `config.json`
4. Replace each placeholder `key` in the spec TEXT (global replace of the exact key, matching by key, not by array position) with the field's display name with `\ " . [ ]` replaced by `_` (Deneb's encoded name, which is the column name Vega sees). Spaces need no escaping anywhere. Compound tokens such as `__dataset.0____highlight` become `Sales__highlight` in the same pass. Do NOT double apostrophes here: that is the PBIR literal encoding of the whole `jsonSpec` string and `deneb_spec.py embed` applies it. What does matter: an apostrophe in a recipient name breaks any single-quoted `datum['...']` accessor the template used, so prefer double-quoted accessors or names without apostrophes. A v1 template with custom keys (`__category__`) is not rewritten by Deneb's own importer either (only `__N__` index keys are), so do the substitution offline (inferred from source, unverified in the UI; Retest in [capabilities.md, v1 (legacy)](capabilities.md#v1-legacy))
5. Choose the container signal names for the target Deneb: `python deneb_spec.py migrate spec.json --signals legacy` for a report still on 1.9.1, `--signals modern` when the visual will only ever open in 2.0 (`--dry-run` shows the count; `migrate` refuses when nothing would change). Deneb's UI import always rewrites `pbiContainer*` to `denebContainer.*`, which is why an imported-through-the-UI spec will not parse on 1.9.1 (inferred from Vega's parser, not reproduced in a 1.9.1 Desktop; Retest in the [compatibility matrix](deneb-2-migration.md#compatibility-matrix))
6. Fix known template rot: `datum.__identity__` / `datum.__key__` to `datum.__row__`; remove `"data": {"values": [...]}` sample rows and `data.url`; the data source must be `{"name": "dataset"}` (Vega-Lite) or `[{"name": "dataset"}]` (Vega)
7. Add the visual (copy one of `examples/visual/*.json` into the page's `visuals/` folder, as in SKILL.md) and bind the fields to Deneb's single `dataset` role in the order the template expects. The CLI form is `-a "role:Table.Field"` with `-t Column|Measure` (`-r` removes a binding, it does not name the role):

```bash
pbir visuals bind "Report.Report/Page.Page/deneb-bar.Visual" -a "dataset:Sales.OrderDate" -t Column
pbir visuals bind "Report.Report/Page.Page/deneb-bar.Visual" -a "dataset:Sales.Total" -t Measure
pbir visuals bind "Report.Report/Page.Page/deneb-bar.Visual" --show
```

   A `parameter` entry is NOT bound through the parameter table's column. Desktop writes the parameter's currently selected component field(s) as ordinary projections carrying a `displayName` (in the Deneb sample workbook that is the component's own name, `Species`, on one visual and the DAX alias the parameter table gives it, `Series`, on the other, so read it as the label the component is expanded under rather than as the parameter's name), then a `fieldParameters[]` array next to `projections` in `visual.query.queryState.dataset` whose `parameterExpr` names the parameter table's column and whose `index`/`length` cover those component projections (`index` is the first slot, `length` the count). So bind the component with `pbir visuals bind -a "dataset:Sales.Revenue" -t Measure`, then hand-author the `fieldParameters` entry: `pbir visuals bind` cannot write it (pbir 0.9.29, Verified 2026-09-08). The spec references the parameter's display name (`Metric`), never a component's.

   Retest: `pbir visuals bind --help` for a field-parameter option; then bind a field parameter to a Deneb visual in Desktop, save as PBIP and diff `queryState.dataset` against the block below.

```json
"projections": [
  {
    "field": {"Column": {"Expression": {"SourceRef": {"Entity": "Sales"}}, "Property": "OrderDate"}},
    "queryRef": "Sales.OrderDate",
    "nativeQueryRef": "OrderDate"
  },
  {
    "field": {"Measure": {"Expression": {"SourceRef": {"Entity": "Sales"}}, "Property": "Revenue"}},
    "queryRef": "Sales.Revenue",
    "nativeQueryRef": "Revenue",
    "displayName": "Revenue"
  }
],
"fieldParameters": [
  {
    "parameterExpr": {
      "Column": {
        "Expression": {"SourceRef": {"Entity": "Metric"}},
        "Property": "Metric"
      }
    },
    "index": 1,
    "length": 1
  }
]
```

   Here `Metric` is the field parameter and `Sales.Revenue` its currently selected component, sitting at projection slot 1. That shape is observed from one Desktop-saved visual in the Deneb sample workbook (a column component there; the measure form above is inferred), not from a specification; whether Deneb needs it to detect the parameter, and how `index`/`length` behave for a multi-select parameter, is unverified (same Retest as above).

8. Embed (backs up to `.bak`, strips a root `$schema` unless `--keep-schema`, doubles apostrophes for the PBIR literal): `python deneb_spec.py embed <visual.json> --spec spec.json --config config.json`
9. Set the remaining PBIR properties from `usermeta` by editing `objects.*` in visual.json (`pbir set` has no route to them, see Performance Engineering): `vega.provider` from `deneb.provider` (`'vega'` or `'vegaLite'`); `enableTooltips`, `enableHighlight`, `enableSelection`, `selectionMaxDataPoints`, `selectionMode` from `interactivity` (write them explicitly: when a template has no `interactivity` block Deneb's importer sets tooltips OFF and the context-menu selector OFF, read from source, unverified in the UI); `enableContextMenu` / `enableContextMenuSelector` per the remap below. If any entry carried `supportFieldConfiguration`, or a normal field went into a `parameter` slot (add `treatAsParameter: true` for it), stamp all three together: `denebMetaVersion '2'`, `consolidateFieldParameters true` and the full `stateManagement.supportFieldConfiguration` (a text literal holding JSON keyed by the REAL encoded field names, five flags per entry). Never write one of the three without the other two: a non-empty configuration with no `denebMetaVersion` is not treated as legacy, consolidation falls back to the code default `true` and unlisted fields get the lean 2.0 defaults. Otherwise leave all three out; the visual then behaves like a migrated 1.x project (measure `__format` / `__formatted` on, highlight trio on only if `enableHighlight` is true at first open), which is also what a v1 template gets through the UI

   Retest: import a template with no `interactivity` block and read `enableTooltips` from the saved visual.json.

10. Validate and verify: `pbir validate "<Report>"`, `python deneb_spec.py audit <visual.json>` (expect no placeholders, no `$schema`, and no legacy signals if you chose `--signals modern`), then render offline before opening Desktop: `node render.mjs spec.json out.png --data sample.json --deneb 1.9` (or `--deneb 2.0`)

Context-menu remap on import (v1 templates predate `contextMenuSelector`; Deneb 2.0 splits the property):

| Template `interactivity` | Author in PBIR |
|---|---|
| `contextMenu: false`, no `contextMenuSelector` (v1 "no data-point resolution") | `enableContextMenu true` + `enableContextMenuSelector false` |
| `contextMenu: true`, no `contextMenuSelector` | both `true` |
| `interactivity` absent | `enableContextMenu true` + `enableContextMenuSelector false` |
| `contextMenuSelector` present (v2) | copy both values as written |

Never write `enableContextMenu false` from a v1 template: under 2.0 that hides the Power BI menu entirely on an unstamped visual.

Pitfalls:

- `usermeta.deneb.providerVersion` can lag the installed Deneb build (Deneb patches a missing one with `5.21.0` / `5.1.1` on import); the most common break is a leftover `datum.__identity__` (removed in Deneb 1.9); rewrite to `datum.__row__`
- A `metaVersion` 1 template imports with the migrated-project stamp and consolidation pinned off, exactly like an in-place migrated 1.x visual: measures get `__format` and `__formatted`, and the highlight trio only if cross-highlight is on at that moment (columns get nothing), so specs relying on those fields keep working; a v2 template gets 2.0 role defaults (format and formatted OFF unless its entries say otherwise)
- Leaving `usermeta` in `jsonSpec`, or leaving `"data": {"values": [...]}` sample rows, ships stale embedded data; the spec must read `{"name": "dataset"}`
- External `data.url` templates fail AppSource certification and break offline; replace with the `dataset` binding
- A wrong-`kind` binding (measure where a column was intended, or the reverse) passes `pbir validate` and renders, but at the wrong grain; check the row count in the debug Source tab
- Exporting from the 2.0 UI adds a v6 `$schema` and tokenises field names used as bare string literals in expressions (`pluck(data('dataset'), 'Sales')`), which 1.9 exports left as literal names; a 1.9-exported template can therefore still carry a real field name where a placeholder belongs

For the usermeta v2 property table see `references/capabilities.md`; the minimal validated v2 examples are in `references/community-examples.md`.
