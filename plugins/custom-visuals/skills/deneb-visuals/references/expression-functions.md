# Deneb expression functions

Moved out of [SKILL.md](../SKILL.md) so the skill body stays under the compaction budget.

## pbiColor names

Those eight names (`min`, `middle`, `max`, `negative`, `bad`, `positive`, `good`, `neutral`) are the whole set; an unknown name falls through to an index lookup and lands on theme color 1 (Verified 2026-09-08 from `getNamedColors` in `packages/vega-runtime/src/lib/extensibility/scheme/powerbi.ts` on Deneb main at cd23465, three commits past tag `2.0.0.0`; read from source, not from a running theme).
Retest: in a Deneb visual, fill four marks with `pbiColor('neutral')`, `pbiColor('middle')`, `pbiColor('good')` and `pbiColor('nonsense')` under a theme whose sentiment and divergent colors differ, and compare.

## pbiColorDivergent misses the middle color

The `pbiColorDivergent` scheme is a basis spline through the theme's minimum, center and maximum divergent colors (`pbiColor` names `min`, `middle`, `max`), not a ramp through them: at its midpoint each RGB channel is (min + 4 x middle + max) / 6, which is what d3's `interpolateRgbBasis` gives, so no value ever gets the center color. Under `domainMid: 0`, with min `#b95115`, center `#f2f4f7` and max `#184f90`, a cell at 0 rendered `#c4bdc0` instead of the near-white center; the ends were exact. When the center color matters (a neutral zero, a diverging heatmap), give the scale an explicit three-color `range` with `domainMid`, which interpolates through each stop. `pbiColorNominal` returned the theme's `dataColors` exactly. (Observed with Deneb 2.0.1.0 on Desktop 26.10, from rendered pixels, not from the source. Verified 2026-10-29.)
Retest: a heatmap with `"scale": {"scheme": "pbiColorDivergent", "domainMid": 0}` and one cell at 0; sample that cell's pixel and compare it with the theme's center color.

## The six functions

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
