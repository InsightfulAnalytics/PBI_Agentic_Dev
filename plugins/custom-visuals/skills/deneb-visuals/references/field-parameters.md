# Field parameters (Deneb 2.0)

Moved out of [SKILL.md](../SKILL.md) so the skill body stays under the compaction budget.

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
