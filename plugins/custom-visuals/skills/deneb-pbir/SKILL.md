---
name: deneb-pbir
version: 26.26
description: Round-trip TOOLING for Deneb specs in PBIR. Extract/embed the Vega/Vega-Lite spec in visual.json and offline-render it (Vega→PNG/SVG) to verify without Power BI. Use whenever a task touches a Deneb visual's spec ("edit the Deneb visual", "change the Vega spec", "fix the Deneb chart", patching jsonSpec in visual.json), or when a Deneb spec needs rendering/verification without Power BI. Also audits a visual's Deneb build stamp, 2.0-only properties and container signal names, and migrates pbiContainer* / denebContainer references in place. Replaces the ad-hoc inline python patch scripts and per-session npm installs used previously. Spec authoring rules, theme colors, and interactivity live in the custom-visuals:deneb-visuals skill.
---

# Deneb specs in PBIR

Deneb stores its spec inside `visual.json` at `visual.objects.vega[0].properties.jsonSpec.expr.Literal.Value`, a single-quote-wrapped PBIR string literal with embedded `'` doubled. Never hand-edit that string; use the scripts.

> The general guidance to prefer the Edit tool for PBIR files exists because editor checkpoint/rewind can only revert Edit/Write changes, not script writes. This skill's scripted spec-embedding is a safe exception: `embed` script-patches visual.json but writes a `.bak` beside it, which substitutes for checkpoint protection. Restore from the `.bak` instead of relying on rewind.

## Version check before editing

Deneb 2.0 renamed the container signals (`pbiContainerWidth` / `pbiContainerHeight` became `denebContainer.width` / `.height`) and changed what a first open writes into `visual.json`, while reports in the wild stay on 1.9.1 until AppSource pushes 2.0 (GitHub release 2026-09-08, AppSource rollout expected around 2026-09-24; Verified 2026-09-08). So, before touching a spec, run the audit and read `developer.version`:

```bash
S="${CLAUDE_PLUGIN_ROOT}/skills/deneb-pbir/scripts/deneb_spec.py"
python "$S" audit "<...>/visuals/myDeneb/visual.json"
```

Then apply the rule in [deneb-2-migration.md, Authoring rules during the transition](../deneb-visuals/references/deneb-2-migration.md#authoring-rules-during-the-transition): a visual stamped `2.0.0.0` or later uses `denebContainer.*`; a `1.x` stamp, an unstamped file, or a target environment not confirmed on 2.0 keeps the legacy names (2.0 rewrites them at parse time; 1.9 cannot parse `denebContainer`, which is inferred from Vega's parser rather than observed in a 1.9.1 Desktop: see the `--deneb 1.9` bullet under the renderer). Flip either way with `migrate --signals` (below).

- Retest: `gh release list -R deneb-viz/deneb --limit 3` for the current stable tag, and the Deneb blog for the AppSource date.

## Edit loop

```bash
S="${CLAUDE_PLUGIN_ROOT}/skills/deneb-pbir/scripts/deneb_spec.py"
# 0. audit: which Deneb saved it, which signal names it may use (see above)
python "$S" audit "<...>/visuals/myDeneb/visual.json"
# 1. extract to a real JSON file (also validates it parses; adds a v6 $schema for the provider if the spec has none)
python "$S" extract "<...>/visuals/myDeneb/visual.json" -o spec.json --config config.json
# 2. edit spec.json normally (Edit tool, full JSON, no escaping)
# 3. verify offline BEFORE touching the report (see renderer below)
# 4. embed back (re-validates, strips the root $schema, writes visual.json + .bak)
python "$S" embed "<...>/visuals/myDeneb/visual.json" --spec spec.json
# 5. pbir validate, then the pbi-verify-loop skill if Desktop is open
```

`provider` in the same properties block says which grammar (`vega` / `vegaLite`); don't mix schema URLs.

`$schema` never goes inside `jsonSpec`: Deneb 2.0 flags a root `$schema` in the Specification editor with a warning and a Quick Fix (the certified visual cannot fetch it and it disables autocomplete), and it does nothing for rendering. `extract` adds `https://vega.github.io/schema/vega/v6.json` or `.../vega-lite/v6.json` (matching `provider`) to the standalone file so editors and the renderer can use it; `embed` strips a root `$schema` again unless you pass `--keep-schema`.

Comments: Deneb's editors accept JSONC and blank the `//` and `/* */` comments before `JSON.parse` (`packages/utils/src/lib/jsonc.ts`), so a saved `jsonSpec` may carry them (the upstream `bullet-chart` example does). Every command here, and the renderer, strips them the same way when strict JSON fails; `extract` and `embed` then write plain JSON, so comments do not survive an extract-edit-embed round trip, and `embed` re-serialises with indent 2, so a compact one-line literal comes back multi-line (same content). `migrate` rewrites the text in place and keeps both comments and layout.

## Offline renderer (one-time `npm install`, then reuse)

First use only: install the renderer deps once (they're gitignored, not shipped in the repo):

```bash
( cd "${CLAUDE_PLUGIN_ROOT}/skills/deneb-pbir/renderer" && npm install )
```

Then render (deps resolve from `renderer/node_modules`; do NOT reinstall per session):

```bash
node "${CLAUDE_PLUGIN_ROOT}/skills/deneb-pbir/renderer/render.mjs" spec.json out.png \
  [--data rows.json] [--data-name dataset] [--scale 2] [--provider vega|vegaLite] \
  [--width 600] [--height 400] [--deneb 1.9|2.0] [--strict]
# --strict is a 2.0-only gate; it is refused with --deneb 1.9
```

- Dependencies (vega, vega-lite, sharp) install into `renderer/node_modules` (gitignored) and resolve from anywhere once installed. `package.json` pins vega and vega-lite exactly to the Deneb 2.0.0.0 bundle (vega 6.4.0, vega-lite 6.4.3; 1.9.x shipped 6.2.0 / 6.4.1), so a spec that renders here parses under 2.0 (Verified 2026-09-08 against Deneb's `package.json` at tag `2.0.0.0`).
- Retest: `node -e "import('vega').then(v=>console.log(v.version));import('vega-lite').then(v=>console.log(v.version))"` from the renderer folder, compared with `vega` and `vega-lite` in `https://github.com/deneb-viz/deneb/blob/<tag>/package.json`.
- Deneb specs get data from Power BI at runtime, so an offline render of the bare spec shows only static chrome. Pass `--data` with a JSON array of sample rows shaped like the visual's field mapping (dataset name defaults to `dataset`, Deneb's convention).
- Grammar is detected from `$schema` (fallback: mark/encoding heuristic). If the spec has no `$schema`, pass `--provider` with the value from the visual's `provider` property. JSONC comments are blanked before parsing, as Deneb does (the result line's `notes` says when that happened).
- `--width` / `--height` simulate the Deneb container (default 600 x 400). They seed the container signals the spec references and does not define itself (`denebContainer`, `pbiContainer`, `pbiContainerWidth`, `pbiContainerHeight`; Vega gets them prepended to `signals`, Vega-Lite to top-level `params`) and, like Deneb, size a spec that has no `width` / `height`: Vega gets `denebContainer.width` / `.height`, a standard-layout Vega-Lite spec gets `"container"` pinned to those values. Consequence: an unsized Vega-Lite spec renders at 600 x 400 rather than Vega-Lite's 200 px default (the `kpi-card` example PNG is 1200 x 800 at scale 2, it used to be 400 x 400), which is what Deneb shows in a 600 x 400 container.
- The `denebContainer` value carries all six properties. `scrollWidth` / `scrollHeight` are seeded with the container size: Deneb seeds them 0 at compile time and its container observer overwrites them after the first render, and there is no observer offline, so a spec that positions against `scrollHeight` draws inside the container instead of at 0. `scrollTop` / `scrollLeft` stay 0 like Deneb.
- Deneb runtime shims, so a real spec parses and draws: `pbiColor` (Power BI default palette, Deneb's shade algorithm, the named sentiment and divergent colours), `pbiFormat` and `pbiFormatAutoUnit` (a best-effort approximation of a Power BI format string: named formats, prefix/suffix, `%`, decimals, grouping and scaling commas; no locale, no date formats, first `;` section only; never throws), `pbiPatternSVG` (returns the foreground colour, there are no pattern defs offline), `pbiCrossFilterApply` / `pbiCrossFilterClear` (no-ops, what Deneb does without a host), and the `pbiColorNominal` / `pbiColorOrdinal` / `pbiColorLinear` / `pbiColorDivergent` schemes. `customFormatTypes: true` is merged into the Vega-Lite config like Deneb does, so `formatType: "pbiFormat"` is honoured. Rendered text from `pbiFormat` is NOT Power BI's formatter output; check number formatting in Desktop.
- `--deneb 1.9` exits 2 when the spec references `denebContainer`, which 1.9.x does not define (offline, vega throws `Unrecognized signal name: "denebContainer"`; that failure mode is inferred from Vega's parser and not yet reproduced in a 1.9.1 Desktop, Verified 2026-09-08 offline only). `--deneb 2.0` prints Deneb's deprecation warning for legacy names, rewrites them over the raw text exactly as Deneb 2.0 does at parse time, and exits 0. `--strict` is a 2.0-readiness gate for CI: any legacy reference exits 2, and because a 1.9 target needs exactly those names, `--deneb 1.9 --strict` is refused with a usage error (exit 1) rather than a misleading "legacy signals found" failure. Detection runs on the raw text before parsing, so a legacy name inside a plain string (a title, a tooltip) is counted and rewritten too, as in Deneb.
- Retest: paste `{"signal": "denebContainer.width"}` as `width` into a Vega visual in a Desktop running Deneb 1.9.1.0 and read the log pane.
- The JSON result line carries `compiled`, `vega`, `vegaLite`, `container`, `deneb`, `strict`, `injectedSignals`, `responsiveSizing`, `legacySignalReferences` and `denebContainerReferences` (counts as found in the file, before any `--deneb 2.0` rewrite) and `notes`, so an agent can read the verdict without parsing stderr.
- `--scale` alone controls PNG size (spec pixels × scale). `.svg` output extension skips sharp entirely.
- If writing any OTHER inline node script against vega: the packages are ESM-only, so use dynamic `import()`, never `require()`.

## Audit and migrate

`audit <visual.json | spec.json>` exits 0 whenever the file parses (it reports, it never fails a spec; a non-JSON file or a malformed `jsonSpec` literal exits 1 with an `ERROR:` line and no verdict) and ends with a `verdict:` line; `--json` prints the same report as JSON. A file with `visual.objects.vega` is treated as a PBIR visual, anything else as a bare spec or template. It reports:

- `developer.version` (the Deneb build that last saved the visual), `provider` and `vega.version`, and whether the visual is versioned. Deneb treats a visual as versioned only when BOTH stamps are present; a half-stamped file takes the unversioned path, which stamps versions and never remaps the context menu (`src/lib/persistence/migration.ts`, `isVersionedSpec`).
- `denebMetaVersion`, `consolidateFieldParameters`, `supportFieldConfiguration` (parse check: each listed field needs all five base flags, a missing flag reads as `false`), and every 2.0-only property present: `vega.enableContextMenuSelector`, `display.scrollbarWidth`, `dataLimit.enableIncrementalDataUpdates`, `dataLimit.incrementalUpdateThreshold`, `stateManagement.supportFieldConfiguration`, `denebMetaVersion`, `scaleToZoom`, `consolidateFieldParameters`. Whether 1.9.1 tolerates those properties in a `visual.json` is unverified, so the verdict says so whenever any of them is present.
- Retest: open a `visual.json` carrying `denebMetaVersion '2'` in a Desktop running Deneb 1.9.1.0 and confirm it renders without a property error.
- The stamping trap: `denebMetaVersion` or `supportFieldConfiguration` present without `consolidateFieldParameters`. Deneb 2.0 then defaults consolidation ON for that visual (`src/lib/persistence/model/constants.ts` line 57, `src/lib/state/project-sync-mappings.ts` lines 225-228); stamp all three together or none of them.
- The highlight trap: the spec reads `__highlight` / `__highlightStatus` / `__highlightComparator` while `enableHighlight` is not `true`. Deneb then emits no `__highlight` fields, and on an unstamped visual the 2.0 first-open stamp writes `highlight: false` for every measure and freezes it (`packages/data-core/src/lib/support-fields/resolve-defaults.ts` lines 31-39; the entries are then used verbatim by `build-processing-plan.ts` lines 128-153), so switching `enableHighlight` on later does not bring the fields back until the companion is ticked in the Supporting Fields: dataset section of the Project setup pane (read from source, not observed in Desktop). Author `enableHighlight true` before the file is first opened under 2.0, or stamp an explicit `supportFieldConfiguration`.
- Retest: migrate a 1.9 visual with `enableHighlight false`, switch cross-highlight on, then check the debug pane Source tab for `__highlight` columns.
- Supporting fields the spec reads (`<field>__formatted`, `__format`, `__highlight*`, `__names`) whose flag is `false` or missing in `supportFieldConfiguration`: they arrive `undefined` under 2.0. Keys are the encoded display names (`\ " . [ ]` become `_`), which are also the column names the spec sees.
- `enableContextMenu false`: under 2.0 that hides the Power BI menu on an unstamped or 2.0-stamped visual (only a visual carrying both stamps below 2.0.0, and `enableContextMenuSelector` still at its default `true`, is remapped on open); 1.9 read the same value as "menu shown, no data-point resolution". Author `enableContextMenu true` + `enableContextMenuSelector false` for the old meaning (read from `src/lib/persistence/migration.ts` lines 306-313 and 352-361, not reproduced in Desktop).
- Retest: hand-author `enableContextMenu false` with no stamps, open in Desktop with Deneb 2.0.0.0, right-click the visual.
- `query.queryState.dataset.fieldParameters[]` entries (parameter table, property, `index` / `length` into `projections`) and whether 2.0 treats them as consolidated (`consolidateFieldParameters true`, or absent with `denebMetaVersion` or `supportFieldConfiguration` present, the code default) or pass-through (`false`, or a fully unstamped file that the legacy migration pins to `false`). `pbir visuals bind` has no field-parameter option (pbir 0.9.29, Verified 2026-09-08), so that block is hand-authored from the shape the sample workbook shows.
- Retest: `pbir visuals bind --help` for a parameter option; the observed `fieldParameters` JSON is in [pbir-structure.md, Field Parameters](../deneb-visuals/references/pbir-structure.md#field-parameters), and the hand-authoring steps are in [advanced-patterns.md, Template Round-Trip (Terminal Import)](../deneb-visuals/references/advanced-patterns.md#template-round-trip-terminal-import), step 7.
- Legacy `pbiContainerWidth` / `pbiContainerHeight` / `pbiContainer` and `denebContainer` reference counts (the same word-boundary regexes as Deneb, so a name inside a title string counts), a root `$schema`, `__identity__` / `__key__` leftovers (removed in 1.9; use `__row__`), and for a template whether `usermeta` is v1 (`usermeta.dataset` array, or keys that are not `__dataset.N__`) or v2. Deneb 2.0 migrates v1 index keys (`__0__`) on import but not custom keys such as `__category__`; convert those offline (inferred from `packages/json-processing/src/template-usermeta.ts` lines 304-350 and its tests, unverified in the UI; matrix Retest (3) in [deneb-2-migration.md, Compatibility matrix](../deneb-visuals/references/deneb-2-migration.md#compatibility-matrix)).
- Retest: import a v1 template with a custom key through the 2.0 Create New Specification dialog and read the imported spec for the raw key.

`audit` reports a template's `usermeta` shape and keys; it does not validate them against the published v2 JSON schema, and this skill's tooling carries no `jsonschema` dependency on purpose. Validate separately with the Python `jsonschema` route documented in [capabilities.md, Template Format (v2)](../deneb-visuals/references/capabilities.md#template-format-v2): `python -c "import json,jsonschema;from jsonschema import Draft7Validator as V;s=json.load(open('deneb-template-usermeta-v2.json'));t=json.load(open('template.json'));print(list(V(s).iter_errors(t['usermeta'])))"`, which expects `[]`, against `https://deneb-viz.github.io/schema/deneb-template-usermeta-v2.json`.

`migrate <visual.json | spec.json> [--signals modern|legacy] [--strip-schema] [--dry-run]` writes a `.bak` first and refuses when nothing would change. `--signals modern` rewrites `pbiContainerWidth` to `denebContainer.width`, `pbiContainerHeight` to `denebContainer.height`, then bare `pbiContainer` to `denebContainer` (Deneb 2.0's order); `--signals legacy` is the exact reverse, so modern then legacy returns the original literal byte for byte. On a visual.json the rewrite is applied to the `jsonSpec` literal text and the rest of the file stays byte-identical. `--strip-schema` cuts the root `$schema` member out of the text and only re-serialises the spec (indent 2) when a textual cut is not possible.

## Authoring rules & gotchas: see deneb-visuals

Spec authoring rules (theme `pbiColor`, escaping, interactivity, responsive sizing) and the hard-won Deneb gotchas (cross-filter-out, per-point tooltips, validate-not-sufficient) live in the **`custom-visuals:deneb-visuals`** skill; the 1.9 to 2.0 compatibility matrix, what 2.0 writes on first open and the stamping rules are in its [deneb-2-migration.md](../deneb-visuals/references/deneb-2-migration.md). This skill is the round-trip *tooling* only (audit / extract / embed / migrate / offline-render).

- A sensible default `jsonConfig`: `{"background":"transparent","view":{"stroke":"transparent"},"font":"Segoe UI"}`. Whatever config you settle on, keep `jsonConfig` consistent across the report's existing Deneb visuals.

## Related Skills

- **`performant-matrix`** -- diagnose a slow matrix before assuming Deneb; the bridge/native/Deneb decision
