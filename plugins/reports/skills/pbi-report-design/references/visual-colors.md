# Visual Colors

How Power BI applies color: theme color expressions, the theme's semantic color names, the selectors that give one series the emphasis, other emphasis channels, and the conditional-formatting basis. Color standards (palettes, status colors, contrast, how many hues, color vision deficiency) are not set here: take them from the design system in use, and where none is loaded, hold to WCAG 2.2 AA (`SKILL.md`, *Standards this skill does not set*).

## Theme Colors

### Use Theme Colors

Prefer theme colors over hex codes:

```json
// Good - uses theme color: ColorId is the dataColors index + 2 (0 is the background, 1 the foreground)
"expr": {"ThemeDataColor": {"ColorId": 2, "Percent": 0}}

// Avoid in visuals - use only in extension measures
"expr": {"Literal": {"Value": "'#118DFF'"}}
```

### Semantic Colors

Use these theme color names in extension measures:

| Color Name | Meaning |
|------------|---------|
| `"good"` | Positive, on-target |
| `"bad"` | Negative, off-target |
| `"neutral"` | Unchanged, baseline |
| `"minColor"` | Gradient minimum |
| `"midColor"` | Gradient midpoint |
| `"maxColor"` | Gradient maximum |

A conditional-formatting rule or measure that returns one of these for a font color paints text with it, so the theme's values must work as text as well as fills.

### Extension Measure Pattern

```dax
// Return theme color names, not hex codes
Color Measure =
IF([Value] >= [Target], "good",
IF([Value] >= [Target] * 0.9, "neutral", "bad"))
```

## Emphasis: One Focal Series, Everything Else Neutral

Power BI has no "gray out the rest" switch. A PBIR selector either names one target or matches every point: `field(<Table.Measure>)` writes `selector.metadata` and targets one bound measure series, `series(<Table.Column>=<Value>)` writes `selector.data[].scopeId` and targets one category value, `id(N)` targets one reference line, and `dataViewWildcard` matches all series or all points at once. There is no "everything except" token. So the neutral is the base and the accent is the exception: write the neutral unscoped across the whole series set, then override the one series that carries the point.

```bash
pbir set "Page.Page/Visual.Visual.dataPoint.fill" --value "<neutral>"
pbir set "Page.Page/Visual.Visual.dataPoint.series(Product.Category=Bikes).fill" --value "<accent>"
```

The two entries coexist. An unscoped `dataPoint.fill` written after a scoped one does not clobber it; `pbir` keeps the unscoped entry as the base and the scoped entry still wins. Take both values from the locked identity in `references/design-identity.md` rather than picking a gray here.

Which selector to reach for:

- one category value inside one measure (the sorted-bar case): `series(<Table.Column>=<Value>)`
- one measure out of several bound to the same chart (the multi-measure line case): `field(<Table.Measure>)`

Where the focal category is data-dependent, drive the fill from a measure that returns the accent for the focal category and `"neutral"` for the rest, per the extension-measure pattern above. `references/tooltips-and-annotations.md` covers why the measure-driven form is the robust one when the series set can change:

```bash
pbir visuals cf "Page.Page/Visual.Visual" --measure "dataPoint.fill _Fmt.HighlightColor"
```

## Contrast Channels Beyond Hue

When something has to stand out and the visual's one accent hue is already spent, change a channel other than color. Each row below names the PBIR property first and its perceptual effect second. Every row takes the same `field()` or `series()` selector as the section above, so it applies to one series and leaves the rest on theme defaults.

| PBIR property or command | Channel | Note |
|---|---|---|
| `dataPoint.fill` | color | the accent; one per visual per `references/design-identity.md` |
| `lineStyles.field(X).strokeWidth` | line weight | thicken the focal line and leave the others at the theme value |
| `lineStyles.field(X).lineStyle` | line style | dash the context series and leave the focal one solid |
| `labels.field(X).bold`, `labels.field(X).color` | text weight | label one series, not all; `labels` names it `color`, not `fontColor`. A textbox run uses `textStyle.fontWeight` instead (`references/page-titles.md`) |
| `lineStyles.field(X).showMarker` | added mark | markers on one series, bare lines everywhere else |
| `y1AxisReferenceLine.id(N).dataLabelShow` | added element | `pbir visuals reference-line add` first, then style the returned id |
| `pbir visuals resize` | size | the visual that matters more is larger; the zones are in `references/layout-guidelines.md` |

Spend one of these per visual. Weight plus fade plus a marker on the same series is three claims made for one point.

## Choosing the CF Basis

Pick the basis before touching `pbir visuals cf`; picking wrong produces valid JSON that misleads readers.

Each basis encodes a claim about the data:

- **Gradient:** the measure is continuous and comparable across rows ("more is darker"). Valid only for a magnitude on a single scale. A signed variance with no explicit center miscolors the midpoint and re-stretches on every refresh.
- **Rules:** discrete business-defined bands (RAG, SLA met/missed) whose cut points come from policy, not the data's min/max. These survive refresh without shifting.
- **Field value (measure-driven):** the color or icon is itself data that a measure computed. Most flexible; prefer it for anything non-trivial. Rule: if the logic has more than two thresholds or depends on another measure, make it measure-driven rather than an inline rules array.
- **Icons:** a status faster to scan than a number. Use sparingly on a triage/status column; never on the primary value column.

Apply CF to the secondary signal (variance, gap, status), not the headline value. Data bars on the one primary magnitude, color scale on the variance column; never both on the same column.

Prefer theme tokens over hex in every basis (`pbir visuals cf ... --theme-colors` to convert existing hex assignments).

### CF Pitfalls

- A signed-measure gradient with no center colors zero as mid-gray noise; set the center explicitly to 0 or use rules
- `IconOnly` hides the number; only use it where the number itself is irrelevant
- Overlapping or gappy rule bounds silently leave rows uncolored; promote fiddly logic to a measure you can test with `pbir model -q`

## Conditional Formatting Colors

### Best Practices

1. **Theme tokens over hex** -- use `--theme-colors` to convert existing hex CF assignments to tokens; changing the theme then cascades everywhere
2. **Measure-driven conversion** -- use `--to-measure` to promote built-in gradient/rules CF to a measure expression; logic becomes testable and versionable
3. **Sparingly applied** -- CF should highlight exceptions; formatting every column means nothing stands out
4. **Theme-first** -- check that `good`, `bad`, and `neutral` sentiment colors exist in the theme before applying CF; add them if missing, from the design system's status colors

### Positive/Negative Pattern

```json
// In extension measure (preferred)
"expression": "IF([Value] >= 0, \"good\", \"bad\")"
```

The theme's `good`, `bad` and `neutral` keys hold the actual colors.

### Data Bars

Data bars provide magnitude scanning in tables/matrices. Apply to primary measure columns.
