# Deneb 2.0 migration and compatibility

The backwards-compatibility note for the two-version window in which a report may open under Deneb
1.9.1 on one machine and Deneb 2.0 on another. Everything here was read from the Deneb 2.0 source,
the docs-site `source` branch, the shipped `2.0.0.0` package and the 2.0 sample workbook
(`deneb-viz/powerbi-sample-workbook`) on 2026-09-08. Nothing was reproduced inside a Power BI Desktop; every claim that depends on a live host
says so and carries a `Retest:` line. Spec authoring rules live in `SKILL.md`; the container-signal
patterns are in [vega-patterns.md](vega-patterns.md); the CLI that audits and flips a visual is the
`custom-visuals:deneb-pbir` skill.

## Timeline and how to tell which Deneb you have

Deneb 2.0.0.0 was published on GitHub on 2026-09-08 (tag `2.0.0.0`); the AppSource rollout ETA is
approximately 2026-09-24 and the release post says it varies by location and could land sooner or
later. Verified 2026-09-08 from the release list and the release post.
Retest: `gh release list -R deneb-viz/deneb --limit 3`, then read the "ETA" paragraph of
`blog/2026-09-08-certification-2-0.md` on the docs-site `source` branch.

Until AppSource has pushed 2.0 to a tenant, every report there opens with the previous stable build,
1.9.1.0 (released 2026-03-31). That is the two-version window: a spec written today has to parse on
both builds, because you do not control which one a given viewer's Service or Desktop has. Version 1
receives critical fixes and Vega updates only, no new features (2.0 beta announcement and docs).

**Which Deneb last saved a visual.** Read `visual.objects.developer[0].properties.version` and
`visual.objects.vega[0].properties.version` in the visual's `visual.json`:

| `developer.version` | `vega.version` | Saved by |
| --- | --- | --- |
| `2.0.0.0` | `6.4.3` (provider `vegaLite`) or `6.4.0` (provider `vega`) | Deneb 2.0 |
| `1.9.x.0` | `6.4.1` (`vegaLite`) or `6.2.0` (`vega`) | Deneb 1.9.x |
| `1.8.x.0` | `6.x` (a 1.8.2.0 file carries `6.4.1` for `vegaLite`) | Deneb 1.8.x (Vega 6 has been bundled since 1.8) |
| `1.7.x.0` | `5.x` (for example `5.20.1`) | Deneb 1.7.x |
| absent (either property) | absent | never saved in edit mode by any Deneb, or hand-authored |

Sources: `packages/vega-runtime/src/lib/embed/index.ts` lines 12-21 (the stamp reads the bundled
package versions), `package.json` (Vega 6.4.0, Vega-Lite 6.4.3 in 2.0), the changelog "Vega Updates"
section ("from 6.2.0", "from 6.4.1" for 1.9), and the sample workbook (`developer.version '2.0.0.0'`,
`vega.version '6.4.3'`). A file with only one of the two properties counts as unversioned, not as
current (`src/lib/persistence/migration.ts` lines 428-444), whatever the pbir-guide says about
"assumed to be the current version".

The stamp records the Deneb build of the last **edit-mode** save (Desktop editing, or Service edit
mode). A report consumed in the Service reading view should never write a stamp, because every
persist call is suppressed in read mode (`src/lib/persistence/persist.ts` lines 18-21;
`properties.ts` lines 34-39). That is read from the persist gate in source, not observed in a
Service tenant.
Retest: open a hand-authored visual in the Service with the report in reading view, then confirm in
Desktop that `visual.json` still lacks `developer.version`.
So a file stamped `1.9.1.0` tells you which build last edited it, not which build the Service is
serving today. Whether Desktop's own Reading view takes the same no-persist path is unverified
(the code gates on the host's `viewMode` only, `src/lib/state/display-mode.ts` lines 153-155).
Retest: open a hand-authored visual in Desktop Reading view, return to Editing view without touching
it, save, and diff `visual.json` for a new `developer.version`.

**Which Deneb a Desktop runs.** Open any Deneb visual, save the report, and read `developer.version`
from the saved `visual.json`: an unversioned or 1.x-stamped visual is stamped with the running build
on its first edit-mode open (`migration.ts` lines 449-468 and 475-503). Alternatively open the
Advanced Editor: the status bar re-states the provider and the embedded Vega or Vega-Lite version,
and 6.4.3 / 6.4.0 means 2.0 (docs `getting-started/visual-editor.mdx`, "Status Bar"). A Service
tenant has no file to inspect: open a report there in edit mode, open the Advanced Editor and read
the same status bar.

**What a 3.0 could take away.** Deneb's deprecation ledger lists three compatibility shims that carry
pre-2.0 payloads, all of them removal candidates at 3.0: the legacy container-signal remap, the
context-menu split remap (`CONTEXT_MENU_SPLIT_VERSION = '2.0.0'`), and the `isLegacySpec`
support-field stamping. The ledger's own convention is that a removal target is the earliest release
a symbol may be removed, not a promise, and removal still requires that no supported payload depends
on the shim (`docs/DEPRECATIONS.md`, sections "Deprecated symbols" and "Version-gated compatibility
shims"). The consequence for a report owner is concrete: a `visual.json` that is still unstamped or
1.x-stamped when a 3.0 arrives would never get the context-menu remap or the legacy supporting-field
defaults at all, because both shims fire only on the first open under a build that still carries
them. Open and save every such visual under a 2.x build while one is current, which is what items 1
to 3 of the next section do. Verified 2026-09-08 by reading `docs/DEPRECATIONS.md` on Deneb `main`;
no 3.0 release exists, and no removal date is published.
Retest: `grep -n "Removal target" docs/DEPRECATIONS.md` in a fresh clone of deneb-viz/deneb, and
compare the `version` in its `pbiviz.json` with `2.0.0.0`.

## What 2.0 changes on first open

Four things happen when 2.0 loads a visual (`src/index.ts` lines 373-375 and 607-609). In edit
mode the first three write to `visual.json` once; the viewport stamp (item 4) is re-persisted
whenever the size changes. In read mode all four run in memory on every update and nothing is
written.

1. **Version stamps.** Unversioned file (missing `developer.version` or `vega.version`, spec not
   `{}`): both stamps are written, no other change, no version modal (`migration.ts` lines 449-468).
   File stamped by 1.x: both stamps are rewritten to `2.0.0.0` and `6.4.3` / `6.4.0`, the
   version-change modal is signalled, and the context-menu remap below is evaluated (lines 475-503).
   File already stamped by 2.0: nothing.
2. **Legacy support-field stamping.** A real spec with no `denebMetaVersion` classifies as
   `unversioned-legacy` (`src/lib/persistence/state-management-migration.ts` lines 418-427). If
   `supportFieldConfiguration` is also empty, the first dataview writes, as one merge, a
   `supportFieldConfiguration` entry for **every** bound field keyed by its encoded display name,
   `denebMetaVersion '2'`, and `consolidateFieldParameters false` (`src/lib/dataset/processing.ts`
   lines 262-328 and 568-581). The stamped flags are not "all on": columns get all five flags
   `false`; measures get `format` and `formatted` `true`, and the highlight trio `true` only if
   `enableHighlight` is `true` at that moment (`packages/data-core/src/lib/support-fields/resolve-defaults.ts`
   lines 31-39). Stamped entries are then read verbatim (`build-processing-plan.ts` lines 128-153), so
   a visual migrated with cross-highlight off keeps `highlight: false` on its measures even after the
   property is switched on later. That freeze is read from source, not observed.
   Retest: migrate a 1.9 visual with `enableHighlight false`, then enable cross-highlight and check the
   debug pane Source tab for `__highlight` columns.
   The partial shape is a trap: a file with a non-empty `supportFieldConfiguration` and no
   `denebMetaVersion` is **not** legacy. Unlisted fields get new-project defaults and
   `consolidateFieldParameters` falls back to `true` (`processing.ts` lines 302-314 and 324-327;
   `src/lib/persistence/model/constants.ts` line 57; `src/lib/state/project-sync-mappings.ts` lines
   225-228). Stamp all three properties together or none.
3. **Context-menu remap.** Only when the file carries both stamps, `developer.version` is below
   `2.0.0`, `enableContextMenu` is `false` and `enableContextMenuSelector` is at its default `true`,
   Deneb rewrites to `enableContextMenu true` plus `enableContextMenuSelector false`, preserving the
   pre-2.0 meaning "menu shown, no data-point resolution" (`migration.ts` lines 352-361 and 524-535).
   An unstamped hand-authored file takes the unversioned branch, which has no remap, so its
   `enableContextMenu false` hides the Power BI menu entirely under 2.0.
   Retest: hand-author `enableContextMenu false` with no stamps, open in Desktop with Deneb 2.0.0.0,
   right-click the visual.
4. **Viewport.** `stateManagement.viewportHeight` / `viewportWidth` are persisted whenever they differ
   from the live embed, as before (`src/lib/state/sync.ts` lines 63-124).

Two more rewrites happen at parse and import time rather than at first open:

- **Legacy signal remap at parse.** `pbiContainerWidth`, `pbiContainerHeight` and `pbiContainer` are
  rewritten over the raw spec text with word-boundary regexes to `denebContainer.width`,
  `denebContainer.height` and `denebContainer`, in that order, and one warning per session is logged
  (`packages/vega-runtime/src/lib/signals/migration.ts` lines 65-116 and 122-140; the parse warnings
  also carry `Migrated N legacy pbiContainer signal reference(s) to denebContainer.`). The rewrite is
  textual, so a legacy name inside a title or tooltip string is rewritten too. The release post says
  to update specs "when convenient", which reads as the file keeping its legacy names until the author
  edits them; not traced through the editor's persistence.
  Retest: open a 1.9 visual with `pbiContainerWidth` under 2.0, save without opening the editor, and
  grep the saved `jsonSpec` for `pbiContainer`.
- **Template v1 to v2 on import.** A template with `usermeta.dataset` (array) and no
  `usermeta.datasets` is rewritten to `usermeta.datasets.dataset[]` with keys `__dataset.<i>__` by
  array index, and every `__<i>__` in the whole template text becomes `__dataset.<i>__`
  (`packages/json-processing/src/template-usermeta.ts` lines 304-350). Only index-form keys are
  rewritten in the spec body; a v1 template with custom keys such as `__category__` keeps them in the
  body while its `usermeta` entries are renamed, so the imported spec ships raw placeholders. That is
  read from source and the tests, not seen in the UI.
  Retest: import a v1 template with a custom key through the 2.0 Create New Specification dialog and
  inspect the resulting spec for the raw key.
  `metaVersion` is not bumped on import (test lines 1014-1023), so a project created from a v1
  template carries `denebMetaVersion 1` and gets the legacy stamping in item 2. A missing
  `providerVersion` is patched with `5.21.0` (Vega) or `5.1.1` (Vega-Lite), a pre-1.7 top-level
  `config` object is moved into `usermeta.config`, and the import always applies the signal remap, so
  a template imported through the 2.0 UI comes out with `denebContainer.*` whatever the author wrote
  (lines 255-268 and 357-370).

## Compatibility matrix

| Spec or PBIR feature | Deneb 1.9.1 | Deneb 2.0 | Notes |
| --- | --- | --- | --- |
| `pbiContainerWidth`, `pbiContainerHeight`, `pbiContainer` | Native | Rewritten to `denebContainer.*` at parse, one warning per session | Deprecated, removal target 3.0 (`docs/DEPRECATIONS.md`). Textual rewrite reaches string literals |
| `denebContainer.width` and the other five properties | Fails to parse with `Unrecognized signal name: "denebContainer"` (inferred from Vega's parser, unverified) | Native | The 1.9 failure was reproduced only offline with the 1.9 Vega bundle, see Retest (1) below |
| Root `$schema` inside `jsonSpec` | Accepted, no editor warning; the parsers ignore the key (read from parser behaviour, no 1.9 doc says so) | Editor warning with a Quick Fix; rendering unaffected | Never embed it; standalone files keep a v6 `$schema` |
| `__identity__` / `__key__` | Absent (removed in 1.9) | Absent | Use `__row__` |
| `__format` / `__formatted` reliance | Generated for "numeric or date/time-based" measures, never for columns; that is the 1.9 docs' wording (`formatting-values.md`), and whether a text measure also got them was not checked (Retest (5)) | Unstamped or migrated visual: on for measures. New project or explicit `supportFieldConfiguration`: off unless the flag is on. Columns can opt in | `datum['Sales__formatted']` returns `undefined` in a brand-new 2.0 visual until the flag is on |
| `__highlight`, `__highlightStatus`, `__highlightComparator` | All three for measures when `enableHighlight` is on | Migrated: all three, but only if `enableHighlight` was on at the moment of the stamp, and frozen there. New: `__highlight` when cross-highlight is on, status and comparator opt-in | If the spec reads `__highlight`, author `enableHighlight true` before the first open under 2.0 |
| Field parameter consolidation | Not available; components pass through | Off for migrated visuals (pinned `false`); on for new projects and when `consolidateFieldParameters true` | A consolidated-parameter spec (`flatten` on the parameter name) is 2.0-only |
| `enableContextMenu false` | Menu shown, no data-point resolution | Unstamped file: menu hidden, right-click swallowed. 1.x-stamped file: remapped to menu on + selector off | See rule 4 |
| `enableContextMenuSelector` | Undeclared property (tolerance unverified, Retest (2)) | Data-point resolution switch, default `true` | Under `objects.vega`, not `objects.interactivity` |
| `enableIncrementalDataUpdates`, `incrementalUpdateThreshold` | Undeclared (unverified, Retest (2)) | Continuous view, off by default, threshold 500 (5-5000) | |
| `scaleToZoom` | Undeclared (unverified, Retest (2)) | Canvas only, off by default | |
| `supportFieldConfiguration` | Undeclared (unverified, Retest (2)) | Read on load; stamped by the migration; keys are encoded display names | Never stamp it without `denebMetaVersion` and `consolidateFieldParameters` |
| `denebMetaVersion` | Undeclared (unverified, Retest (2)) | `'2'` when stamped; absent with a real spec means legacy | Same rule |
| Template usermeta v1 (`usermeta.dataset`, `metaVersion 1`) | Native | Accepted and migrated on import; custom keys not rewritten in the body (unverified, Retest (3)) | Projects created from a v1 template get legacy support-field defaults |
| Template usermeta v2 (`usermeta.datasets`, `metaVersion 2`) | Rejected by the v1 schema (`metaVersion` maximum 1, `dataset` required); inferred from `usermeta-v1.json`, unverified (Retest (4)) | Native | Export from 2.0 always writes v2 |
| Row window and `dataLimit.override` | 10,000 rows; override fetches more in batches of 10,000 | 30,000 rows (`capabilities.json` window count); override still batches of 10,000 but is report viewing only | Microsoft no longer guarantees extra fetches during PDF or PowerPoint export (`dataset.md` "Query (Row) Limits") |

Retest lines for the unverified cells (all Verified 2026-09-08 as inferences from source, none run in
a 1.9.1 Desktop):

- Retest: (1) open a Desktop whose Deneb is 1.9.1.0, paste `{"signal": "denebContainer.width"}` as
  `width` in a Vega visual and read the Logs pane for the unrecognised-signal error.
- Retest: (2) hand-author a `visual.json` carrying `enableContextMenuSelector`, `scaleToZoom`,
  `enableIncrementalDataUpdates`, `supportFieldConfiguration` and `denebMetaVersion`, open it in a
  Desktop whose Deneb is 1.9.1.0 and confirm it renders with no property error (Power BI generally
  ignores object properties a visual does not declare, but nobody has opened such a file under 1.9.1).
- Retest: (3) import a v1 template with a custom placeholder key through the 2.0 UI (see the template
  bullet above).
- Retest: (4) import a v2 template through the 1.9.1 Create New Specification dialog and read the
  validation error.
- Retest: (5) bind a text-returning measure to a visual in a Desktop whose Deneb is 1.9.1.0 and check
  the debug pane Source tab for its `__format` and `__formatted` columns, which settles whether 1.9
  gated those fields on the measure's data type as its docs say.

Changes in the bundled Vega and Vega-Lite you may notice after the switch (Vega 6.2.0 to 6.4.0,
Vega-Lite 6.4.1 to 6.4.3; release notes read with `gh release view` on 2026-09-08): legend and title
labels align to the start of the chart frame; stroke bounds expand with join-aware slack, which can
move autosize results by a pixel or two; aggregated field names with dots become underscores; the
`crossfilter` transform's `max` is exclusive; the root element uses `vertical-align: bottom`, about
6 px less container height in Chrome; ordinal scales on continuous schemes honour `range.count`
(relevant to `pbiColorOrdinal` and `pbiColorLinear`, which are interpolators); new `timeunit`
`"auto"`, `tickIndex` in `labelExpr`, `isoweek`, `container:resize`, d3-ease functions. Vega-Lite
6.4.2 and 6.4.3 are fixes only (tooltips with custom format types, legend merging on explicit colour
ranges). Deneb itself trimmed its bundled locales to the list Microsoft supports, which is a package
size saving, so a locale that used to format values through `pbiFormat` may simply be missing on 2.0;
the changelog asks authors whose locale disappeared to raise an issue and it will be added back
(changelog "Performance and Stability", deneb-viz/deneb#593). Whether the height change moves Deneb's
overflow or scrollbar threshold is unverified.
Retest: open a 1.9 visual that fitted without a scrollbar under 2.0 and compare
`denebContainer.scrollHeight` with `denebContainer.height` in the debug pane Signals tab.

## Authoring rules during the transition

1. **Container signals follow the stamp.** The authoring default for responsive sizing stays
   `pbiContainerWidth` / `pbiContainerHeight` (Vega) because they work natively on 1.9.1 and are
   remapped on every 2.x build. Use `denebContainer.width` / `denebContainer.height` only when the
   `visual.json` you are editing carries `developer.version` `2.0.0.0` or later, or the target report
   has been confirmed on 2.0 everywhere it is viewed. A 1.x stamp, or no stamp and an unconfirmed
   target, means keep the legacy names. Never mix the two families in one spec. Flip a finished spec
   with `deneb_spec.py migrate <file> --signals modern` and back with `--signals legacy`. The pattern
   files and examples in this skill keep the legacy names during this phase on purpose.
2. **`$schema` never goes inside `jsonSpec`.** Standalone spec files under `examples/spec/` keep a
   `$schema` with the v6 URLs (`https://vega.github.io/schema/vega/v6.json`,
   `https://vega.github.io/schema/vega-lite/v6.json`) for the offline renderer and editors;
   `deneb_spec.py embed` strips a root `$schema` unless `--keep-schema` is passed, and `extract` adds
   one matching the provider when the extracted spec has none.
3. **Stamps are opt-in, and travel together.** A hand-authored `visual.json` omits
   `developer.version`, `vega.version`, `denebMetaVersion`, `supportFieldConfiguration` and
   `consolidateFieldParameters`. That is the most compatible shape: 1.9.1 sees nothing it does not
   declare, and 2.0 treats it as a migrated project (measures keep `__format` / `__formatted`, field
   parameters pass through). Stamp `denebMetaVersion '2'`, `consolidateFieldParameters true` and an
   explicit `supportFieldConfiguration` (all five base flags per entry, keys encoded with `\ " . [ ]`
   replaced by `_`) only when the spec needs consolidated field parameters or a lean dataset, and
   accept that the file is then 2.0-only in intent. If the spec reads `__highlight`, author
   `enableHighlight true` in the file before it is first opened under 2.0, otherwise the migration
   freezes `highlight: false` on the measures. The 1.9.1 tolerance of the stamped properties is
   unverified (matrix Retest (2) above).
4. **Context menu.** A new visual that wants the Power BI menu without data-point resolution sets
   `enableContextMenu true` and `enableContextMenuSelector false` explicitly. Never author
   `enableContextMenu false` unless the intent is to suppress the menu under 2.0, and accept that
   1.9.1 reads the same file as "menu shown, no resolution".
5. **Row limit wording.** The default window is 30,000 rows on 2.0 and 10,000 on 1.9 and earlier;
   `dataLimit.override` fetches more in batches of 10,000 and is report viewing only. Do not promise a
   row count that only one build delivers.

Formatting helpers and the six expression functions (`pbiColor`, `pbiFormat`, `pbiFormatAutoUnit`,
`pbiPatternSVG`, `pbiCrossFilterApply`, `pbiCrossFilterClear`) are unchanged between 1.9 and 2.0, so
they need no transition rule.

## Audit and migrate a visual

The tooling is `deneb_spec.py` and `render.mjs` in the `custom-visuals:deneb-pbir` skill
(`${CLAUDE_PLUGIN_ROOT}/skills/deneb-pbir/scripts/deneb_spec.py` and
`${CLAUDE_PLUGIN_ROOT}/skills/deneb-pbir/renderer/render.mjs`). The surface below is the one this
skill relies on; the deneb-pbir `SKILL.md` is authoritative for flags and output.

```bash
# What is this visual, and what would 2.0 do to it?
python "${CLAUDE_PLUGIN_ROOT}/skills/deneb-pbir/scripts/deneb_spec.py" audit <visual.json | spec.json>

# Flip the container signal family, strip an embedded $schema, preview first
python "${CLAUDE_PLUGIN_ROOT}/skills/deneb-pbir/scripts/deneb_spec.py" migrate <visual.json | spec.json> --signals modern --dry-run
python "${CLAUDE_PLUGIN_ROOT}/skills/deneb-pbir/scripts/deneb_spec.py" migrate <visual.json | spec.json> --signals legacy
python "${CLAUDE_PLUGIN_ROOT}/skills/deneb-pbir/scripts/deneb_spec.py" migrate <visual.json> --strip-schema

# Round trip (extract adds a v6 $schema when the spec has none; embed strips it unless --keep-schema)
python "${CLAUDE_PLUGIN_ROOT}/skills/deneb-pbir/scripts/deneb_spec.py" extract <visual.json> -o spec.json
python "${CLAUDE_PLUGIN_ROOT}/skills/deneb-pbir/scripts/deneb_spec.py" embed <visual.json> --spec spec.json [--config config.json] [--keep-schema]

# Render offline against a Deneb target
node "${CLAUDE_PLUGIN_ROOT}/skills/deneb-pbir/renderer/render.mjs" spec.json out.png --data rows.json --width 600 --height 400 --deneb 1.9
node "${CLAUDE_PLUGIN_ROOT}/skills/deneb-pbir/renderer/render.mjs" spec.json out.png --data rows.json --deneb 2.0 --strict
```

`audit` prints the Deneb build stamp (`developer.version`), the provider and its version,
`denebMetaVersion`, whether any 2.0-only property is present, legacy signal references (count, with
the same word-boundary regexes Deneb uses) and `denebContainer` references, whether a root `$schema`
is present, `__identity__` / `__key__` references, `enableContextMenu false` with the semantics
warning, a `supportFieldConfiguration` parse check, and usermeta v1 (`usermeta.dataset` array or
keys that are not `__dataset.N__`) when a template is embedded. It exits 0 whenever the file
parses (it reports, it never fails a spec) and ends with a one-line verdict, so read the verdict, not
the exit code; a file that is not JSON or JSONC exits 1 with an `ERROR:` line and no verdict.

`migrate` rewrites in place with a `.bak`, works on a PBIR `visual.json` (rewriting inside the
literal) or on a bare spec or template JSON file, and refuses when nothing would change. `--signals
modern` and `--signals legacy` apply the three regexes in Deneb's order; `--strip-schema` removes a
root `$schema`; `--dry-run` reports the counts without writing.

`render.mjs` injects a `denebContainer` signal (Vega) or param (Vega-Lite) with all six properties,
plus the legacy `pbiContainer`, `pbiContainerWidth` and `pbiContainerHeight`, sized from `--width` and
`--height` (defaults 600 x 400) and only when the spec references them without defining them; it
registers the six expression functions and the four `pbiColor*` schemes with offline stand-ins, so a
real spec parses and draws. `--deneb 1.9` exits 2 when the spec references `denebContainer`;
`--deneb 2.0` warns about legacy names, rewrites them like Deneb and exits 0; `--strict` turns any
legacy reference into exit 2 for CI. Offline `pbiFormat` output is an approximation, not Power BI's
formatter. The renderer's bundle matches Deneb 2.0 (Vega 6.4.0, Vega-Lite 6.4.3). Verified
2026-09-08 against the `--help` output of both scripts and `renderer/package.json` in this
repository; nothing here was run against a Power BI Desktop.
Retest: `python "${CLAUDE_PLUGIN_ROOT}/skills/deneb-pbir/scripts/deneb_spec.py" audit --help` and
`node "${CLAUDE_PLUGIN_ROOT}/skills/deneb-pbir/renderer/render.mjs" --help`, then check `vega` in
`renderer/package.json`.

Typical sequence for an existing 1.9 visual: `audit` it; if it is going to stay on a mixed estate
leave the legacy signals and stamps alone; if the estate is confirmed on 2.0, `migrate --signals
modern`, `audit` again, render with `--deneb 2.0 --strict`, then open in Desktop and save so the
stamps land.

## Docs errors and unverified claims

Docs errors found while cross-checking the 2.0 documentation against `capabilities.json` and source
(Verified 2026-09-08 against the docs-site `source` branch and the Deneb `main` clone of that date).
Retest: `grep -n "objects.interactivity" docs/changelog.md` and `grep -n "10,000" docs/deeper-concepts/pbir-guide.md`
in a fresh clone of the docs-site `source` branch; an empty result means the error was fixed upstream.

- The changelog table "What Affects PBIR and Templating" places `enableContextMenuSelector` under
  `objects.interactivity`. There is no `interactivity` object; the property lives under
  `objects.vega` (`capabilities.json`, the pbir-guide `objects.vega` table, the sample workbook).
- The pbir-guide's `dataLimit.override` remark still says "standard 10,000 row limit"; the 2.0
  window is 30,000 (`capabilities.json` `dataReductionAlgorithm.window.count`, identical in the
  shipped package).
- The pbir-guide spells `backgroundPassthrough`; `capabilities.json` and the settings model spell
  `backgroundPassThrough`, which is what PBIR must use.
- The changelog template column says `interactivity.enableContextMenu`; the template key is
  `interactivity.contextMenu` (`usermeta-v2.json`).
- The pbir-guide lists `logLevel` 0-3; `capabilities.json` enumerates 0-4 (4 = debug) in both 1.9.1
  and 2.0.
- The pbir-guide omits `vega.tooltipDelay` (default 0, 0-10000 ms), `developer.locale`,
  `general.formatString` and the main-only `editor.formattingMaxLineLength`.
- The pbir-guide gives `editor.debouncePeriod` default `300D`; the code default is 700 ms
  (editor-only, no rendering effect).
- The pbir-guide says `consolidateFieldParameters` defaults to `false` if omitted. The code default
  when the property is absent is `true`; `false` arises only from the legacy migration. See rule 3.
- The pbir-guide says `supportFieldConfiguration` keys are display names and that the map is
  sparse; keys are encoded display names (`\ " . [ ]` replaced by `_`), and the migration writes an
  entry for every bound field. Both shapes load.
- The pbir-guide says `scrollbarWidth` is "8D upwards"; the maximum is 16.
- The changelog PBIR table omits `display.scrollbarWidth` and `supportsKeyboardFocus`.
- The changelog defaults table says a field parameter's Highlight value defaults to Disabled; source
  and `field-parameters.md` say it is on when cross-highlight is enabled.
- `field-parameters.md` says templates export the role `field-parameter`; the template JSON value
  is `kind: "parameter"` (v2 schema, `templates.md`).
- `templates.md` says a template with no `interactivity` block gets Deneb's defaults; the create path
  writes tooltips off and the context-menu selector off (`persistOnCreateFromTemplate`). Read from
  source, not seen in the UI.
  Retest: import a v2 template with no `interactivity` block and read `enableTooltips` from the saved
  `visual.json`.

Unverified claims made in this file, each with the check that settles it. Verified 2026-09-08 means
"read from source on that date", not "reproduced in a Desktop".
Retest: each bullet names its own check, or points at the numbered matrix Retest that covers it.

- 1.9.1 fails on `denebContainer` with `Unrecognized signal name`: inferred from Vega's parser and the
  offline renderer under the 1.9 Vega bundle. Matrix Retest (1).
- 1.9.1 tolerates the 2.0-only `stateManagement`, `vega` and `dataLimit` properties in `visual.json`:
  nothing in the sources addresses it. Matrix Retest (2).
- Custom v1 placeholder keys survive import unrewritten. Matrix Retest (3).
- 1.9.1 rejects a v2 template. Matrix Retest (4).
- The Service reading view writes no stamp, and Desktop Reading view takes the same read-mode
  no-persist path. Both read from the persist gate only. Retests in the timeline section.
- Enabling `enableHighlight` after a migration does not add `__highlight` to frozen measure entries.
  Retest in "What 2.0 changes on first open", item 2.
- An unstamped `enableContextMenu false` hides the menu under 2.0. Retest in item 3 of the same
  section.
- The parse-time signal remap does not rewrite the saved `jsonSpec`. Retest in the parse bullet of
  the same section.
- The `queryState.dataset.fieldParameters` block (`parameterExpr`, `index`, `length`) was observed in
  one Desktop-saved sample-workbook visual; whether `pbir visuals bind` can emit it, whether Deneb
  needs it, and how `index` / `length` behave for multi-select parameters are open.
  Retest: bind a field parameter to a Deneb visual in Desktop, save as PBIP, diff `queryState.dataset`
  against the sample workbook visual `3ec60b103b36a08e268a`, then try `pbir visuals bind --help` for
  a field-parameter option.
- In advanced cross-filter mode the default `options.limit` is the constant 50 and the Format-pane
  `selectionMaxDataPoints` is not consulted (source only).
  Retest: set `selectionMaxDataPoints` to 5, call `pbiCrossFilterApply(event, '')` on a 10-row
  filter and check whether the limit banner appears.
- What a brand-new 2.0 visual writes to `supportFieldConfiguration` and `denebMetaVersion` when the
  author never touches the Supporting fields pane: by code, a visual created through the Create New
  Specification dialog in edit mode gets `denebMetaVersion '2'` persisted by the state sync
  (`packages/app-core/src/features/project-create/components/create-button.tsx` lines 103-109 pass
  the template's `metaVersion`, `packages/app-core/src/state/project.ts` lines 165-167 default it to
  2, and the `denebMetaVersion` mapping in `src/lib/state/project-sync-mappings.ts` persists the
  store value that differs from the absent property), while `supportFieldConfiguration` stays absent
  until a flag is edited. A fresh spec is not legacy, so the migration stamp in item 2 never runs.
  Read from source, not observed.
  Retest: create a new Deneb visual in Desktop under 2.0, save without opening the settings pane, and
  read `stateManagement` in `visual.json`.
- Vega 6.4.0's `vertical-align: bottom` root style and the 6.3.0 stroke-bounds change shift Deneb's
  overflow or scrollbar threshold. Retest at the end of the matrix section.
- The sample workbook visuals were migrated from a pre-2.0 workbook rather than authored fresh (their
  `supportFieldConfiguration` matches the legacy stamp exactly). Only the workbook history or its
  author can settle it; treat those files as ground truth for shape, not for what a new visual writes.
- deneb-viz/deneb#676 (1.9.1 visuals rendering blank in one Desktop build for some users) is open
  and not caused by 2.0. Retest: read the issue.

## Follow-up: flipping the defaults after rollout

Once 2.0 is confirmed everywhere a report is viewed, the transition defaults in this skill can flip
to the 2.0 names. The checklist, to be run in one change:

1. Confirm the rollout: open a Deneb visual in the current Desktop, save, and read
   `developer.version 2.0.0.0` from `visual.json`; open the same report in the Service, edit mode,
   and confirm the Advanced Editor status bar shows the 2.0 provider version (6.4.3 or 6.4.0).
   Check the AppSource listing version as well, because a Desktop with a sideloaded developer build
   proves nothing about the Service.
2. Flip the JSON files first. `deneb_spec.py migrate <file> --signals modern` takes the standalone
   specs under `examples/spec/` and the `visual.json` files under `examples/visual/` (it rewrites
   inside the `jsonSpec` literal) directly; `audit` each one afterwards and render every spec with
   `--deneb 2.0 --strict`.
   Then the markdown, which `migrate` cannot read: pointed at a `.md` file it exits 1 with
   `ERROR: <path> is not JSON (nor JSONC)` and writes nothing. Verified 2026-09-08 against a
   scratchpad copy of `vega-patterns.md`.
   Retest: `python "${CLAUDE_PLUGIN_ROOT}/skills/deneb-pbir/scripts/deneb_spec.py" migrate <a copy of
   vega-patterns.md> --signals modern --dry-run` and read the exit code.
   The pattern blocks in [vega-patterns.md](vega-patterns.md) and
   [vega-lite-patterns.md](vega-lite-patterns.md) therefore take one of two routes: extract each
   fenced block to a temporary `.json` file, `migrate` it and paste the result back, or run a
   scripted text substitution over the markdown applying Deneb's three replacements in Deneb's order
   (`pbiContainerWidth` to `denebContainer.width`, then `pbiContainerHeight` to
   `denebContainer.height`, then bare `pbiContainer` to `denebContainer`), each with a word boundary
   so the bare name does not swallow the two longer ones. Either way, re-read the prose around each
   block: it names the signals as well.
3. Update rule 1 in this file and the responsive-sizing rule in `SKILL.md` so `denebContainer.width`
   / `denebContainer.height` become the default, keep the legacy names documented as "accepted until
   3.0", and update checklist item 5 of the `deneb-reviewer` agent to match.
4. Revisit rule 3: once no 1.9.1 viewer remains, stamping `denebMetaVersion '2'` with an explicit
   `supportFieldConfiguration` becomes the recommended shape for new visuals, and the
   `__format` / `__formatted` guidance in the pattern files should say "opt in per field".
5. Re-run the four matrix Retests and remove the "unverified" markers that pass.

Verified 2026-09-08: none of this has been done; the defaults in this skill are still the 1.9-safe
ones, and the AppSource rollout had not started.
Retest: `python "${CLAUDE_PLUGIN_ROOT}/skills/deneb-pbir/scripts/deneb_spec.py" audit` on any
`examples/visual/*.json`; a legacy signal count above zero means the flip has not happened.
