# Deneb editions, builds and the 2.0 editor

Moved out of [SKILL.md](../SKILL.md) so the skill body stays under the compaction budget.

## Editions and builds

- **Other editions:** Standalone `STANDALONEdeneb7E15AEF80B9E4D4F8E12924291ECE89A`, Alpha `ALPHAdeneb7E15AEF80B9E4D4F8E12924291ECE89A`, Beta `BETAdeneb7E15AEF80B9E4D4F8E12924291ECE89A`. None of the three is served from AppSource, so the edition's `.pbiviz` has to be unzipped into `/CustomVisuals/{GUID}/` in the PBIP assets and source-controlled with the report. Persisted properties do not carry across GUIDs: Deneb classifies a payload arriving under a different packaging-channel GUID as an empty one (a fresh visual, not a legacy project), so no migration runs on it. For an agent, moving a visual between editions is a rebuild, not a `visualType` swap: carry `objects.vega` and any `stateManagement` stamps over yourself, then open the result and confirm the spec survived (Verified 2026-09-08 from the PBIR guide's "Other Visual Editions" section and `src/lib/persistence/state-management-migration.ts` lines 179-181 on Deneb main at cd23465, three commits past tag `2.0.0.0`; read from source and docs, not reproduced in Desktop, and the cross-GUID note is written about `.pbix` state rather than a hand-edited PBIR file).
  Retest: copy a working visual.json, change `visualType` to the Standalone GUID with that edition's `.pbiviz` extracted under `/CustomVisuals/`, open in Desktop and check whether the spec and the `stateManagement` stamps are still there.
- **Current build:** Deneb 2.0.0.0 on custom visuals API 5.11.0, bundling Vega 6.4.0 / Vega-Lite 6.4.3. The 1.9.x builds bundled Vega 6.2.0 / Vega-Lite 6.4.1. Vega 6 has been bundled since 1.8, so standalone spec files use `v6.json` schema URLs (Verified 2026-09-08 against `pbiviz.json` and `package.json` on Deneb main at cd23465, 2026-09-04, three commits past tag `2.0.0.0`; neither file changed between the two).
  Retest: `gh release view 2.0.0.0 -R deneb-viz/deneb --json tagName,publishedAt` and read `dependencies.vega` / `vega-lite` in the tag's `package.json`.

## Convert a Vega-Lite spec to Vega

When a Vega-Lite spec outgrows Vega-Lite there is an escape hatch: the 2.0 editor's Compiled Vega pane (Vega-Lite specs only) offers "Convert my spec to Vega", which replaces the spec with its compiled Vega equivalent, switches the provider, and cannot be undone. The compiled output drops the root `$schema` and the spec's `config` block, though the Config editor keeps its own contents. Extract the Vega-Lite spec to a file first (`deneb_spec.py extract`, `deneb-pbir` skill): Deneb cannot recover it afterwards (Verified 2026-09-08 from the Deneb docs site `getting-started/visual-editor.mdx`; read from the docs, not run in Desktop).
Retest: in a Deneb 2.0.0.0 editor, open a Vega-Lite spec that carries its own `config`, run Compiled Vega then "Convert my spec to Vega", and diff the result.

## Container signals

Detail for [Responsive Sizing](../SKILL.md#responsive-sizing-vega) in SKILL.md.

- `pbiContainerWidth`, `pbiContainerHeight` and the `pbiContainer` object are the pre-2.0 names. They work natively on 1.9 and on every 2.x build, where Deneb rewrites them to `denebContainer` over the raw spec text with word-boundary regexes and logs one warning per session (removal target 3.0). The rewrite is textual, so the same names inside a title or tooltip string are rewritten too.
- `denebContainer` is the 2.0 signal (Vega) or param (Vega-Lite, readable from any `expr`): an object with six numeric properties, `width`, `height`, `scrollWidth`, `scrollHeight`, `scrollTop`, `scrollLeft`. It does not exist on 1.9, where a spec that references it is expected to fail parsing: that failure is inferred from Vega's parser and has not been reproduced in a 1.9.1 Desktop, so see the "`denebContainer` fails to parse on Deneb 1.9" gotcha below before relying on the exact symptom.

## The 2.0 debug pane

With Desktop open, finish in the 2.0 debug pane: the Source tab (Ctrl+Alt+6) shows the Deneb dataset as it arrives, before any Vega transform, so it is where you confirm that the supporting fields the spec reads are actually present and that a consolidated field parameter really is arriving as arrays; the Data tab (Ctrl+Alt+7) shows the Vega named datasets after transforms, which is where a `flatten` is checked. Without Desktop, render offline with the `deneb-pbir` skill's `render.mjs` instead, which sees neither tab's contents (Verified 2026-09-08 from `getting-started/visual-editor.mdx` and the 2.0.0 changelog on the Deneb docs site, where the Source tab and its shortcut are listed as new in 2.0; read from the docs, not run in Desktop).
Retest: open a Deneb 2.0.0.0 visual in Desktop and press Ctrl+Alt+6 then Ctrl+Alt+7.
