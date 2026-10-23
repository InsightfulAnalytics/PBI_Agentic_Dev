# Interactivity and runtime fields: the 2.0 detail

Moved out of [SKILL.md](../SKILL.md) so the skill body stays under the compaction budget.

## Sentence-template tooltips

Sentence-template tooltips (Power BI, June 2026) read only fields that are explicit members of the tooltip datum, so enumerate them: an explicit `tooltip` encoding channel in Vega-Lite, or an `encode` entry that lists them in Vega. The sentence itself is a Power BI container property, so it does not travel with a Deneb template.

The sentence-template rule above comes from Deneb's own tooltip page and is the only guidance available so far (Verified 2026-09-08 from `interactivity/tooltips.md` on the Deneb docs site, describing the Power BI June 2026 feature; not built in Desktop).
Retest: give a Deneb visual a sentence-template tooltip naming two fields, hover a mark with `"tooltip": true` on the mark, then again with an explicit `tooltip` channel listing both fields.

## Context menu

**Authoring rule for the context menu:** a visual that wants the menu without data-point resolution sets `enableContextMenu true` + `enableContextMenuSelector false` explicitly. Never author `enableContextMenu false` unless the intent is to suppress the menu under 2.0, and accept that 1.9 reads the same value as "menu shown, no resolution". Deneb only remaps an old `enableContextMenu false` to the new pair when the file carries both `developer.version` (below 2.0.0) and `vega.version`; a hand-authored visual with no stamps is honoured literally.

## Which supporting fields exist

Which of the per-field ones exist depends on how the visual is classified under 2.0:

- **Unstamped or migrated** (real spec, no `denebMetaVersion`): Deneb stamps the pre-2.0 set on first open. Measures get `__format` and `__formatted`, plus the highlight trio only if `enableHighlight` was already true at that moment; columns get none. The stamped entries are then frozen, so switching cross-highlight on later does not add `__highlight` until the flag is ticked in the Supporting fields pane or in `supportFieldConfiguration`. If the spec reads `__highlight`, author `enableHighlight true` before the file is first opened under 2.0 (Verified 2026-09-08 from `resolve-defaults.ts` lines 31-39 and `build-processing-plan.ts` lines 128-153 on Deneb main at cd23465, three commits past tag `2.0.0.0`, where neither file changed; not observed in Desktop).
  Retest: migrate a 1.9 visual with highlight off, enable "Expose cross-highlight values", check the debug Source tab for `__highlight` columns.
- **Stamped 2.0** (`denebMetaVersion '2'`): lean role defaults. Measures get `__highlight` only when `enableHighlight` is on; `__highlightStatus`, `__highlightComparator`, `__format` and `__formatted` are opt-in per field through `supportFieldConfiguration`, for columns as well as measures. Field parameters get `__highlight` under the same condition and nothing else, `__names` included.
- **Consolidated field parameters** make every companion an array (one entry per component) instead of a scalar.

The 1.9 behaviour was "every supporting field Deneb can add is present". The defaults matrix is in `references/capabilities.md`.
