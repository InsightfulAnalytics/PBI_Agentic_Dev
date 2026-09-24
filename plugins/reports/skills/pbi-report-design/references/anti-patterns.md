# Anti-Patterns: Defaults to Refuse

These are the choices a model reaches for because they look plausible, not because they are right; attractor states that satisfy the literal request while defeating the reader. This list is cross-cutting and whole-report. It does not replace the per-visual anti-pattern tables in `references/cards-and-kpis.md` and `references/tables-and-matrices.md`; it sits alongside them.

When a user asks for one of these, do not silently comply. Refuse and redirect: name the better option in the skill's voice, explain the cost in one line, and offer the repair. The user can still override; the point is that they choose it knowingly.

Each entry: the attractor, why it loses (tied to a canon principle), and the repair with the `pbir` move where one exists.

Most of the repairs below take something away, and removal is only the first of two passes. Freeing attention is not the same as spending it, so a page that has only been stripped is not finished. Check 6 of the closing gate in `references/quality-gate.md` is where the spend is verified.

## gauge-as-KPI

A gauge spends a large area encoding one value on a curved scale that the eye reads worse than a straight one (Cleveland-McGill: position on a common scale beats angle). Repair: a `kpi` or `card` with a target and an explicit gap. Swap the type and bind the target role; see `references/chart-selection.md` for the value-vs-target routing.

## monochrome categorical bars

One hue across unordered categories spends the color channel and returns nothing; hue carries no information when every bar is the same. The inverse costs the same: every series at full saturation with no neutral context spends the channel on all of them at once, so nothing stands out. Repair: sort by value descending and let bar length do the comparing, then set the unscoped `dataPoint.fill` to the neutral and override only the series the title names. This is the single-accent rule from `references/design-identity.md` applied to a bar chart.

```bash
pbir visuals sort "Page/Visual.Visual" -f "<Table.Measure>" -d Descending
```

The neutral-base-then-scoped-accent commands, the selector to pick for a category value versus a measure series, and the measure-driven fill for a focal category that moves with the data are in `references/visual-colors.md`.

## missing sort

Categorical bars left in load or alphabetical order defeat the length comparison that is the chart's only reason to exist; the reader cannot rank what is not ranked. Repair: sort by the measure descending unless the axis is genuinely time-ordered. Sorting is discussed further in `references/chart-selection.md`.

```bash
pbir visuals sort "Page/Visual.Visual" -f "<Table.Measure>" -d Descending
```

## too many cards

A wall of bare cards is data without a question; ten numbers with no hierarchy ask the reader to find the point themselves. Repair: cap the card row to the few that drive a decision (the "20% change test" in `references/cards-and-kpis.md`), and demote the rest into one table or chart. This is also a page-shape signal: a card wall usually means a summary page that never decided what it summarizes.

## raw field names as titles

`Sum of SalesAmount` as a visual title narrates the query, not the question. A title should state what the visual answers so the reader knows why it is there. Repair: rewrite the visual title to the question ("Sales vs target, by region"); leave the underlying model field name untouched, the title is a report-side string.

```bash
pbir set "Page/Visual.Visual.title.text" --value "Sales vs target, by region"
```

## inline hex instead of theme references

A literal hex value in `visual.json` pins a color to one visual; the identity stops propagating and a re-theme leaves it stranded. Repair: use a `ThemeDataColor` or a semantic token so the color cites the identity and re-themes cleanly. The theme-vs-hex decision and the conversion path live in `references/visual-colors.md`. One property has no token form: a textbox text run's `textStyle.color` takes a literal hex only, so an accented word in a title is a declared exception that has to be re-checked on a re-theme (`references/page-titles.md`).

```bash
pbir visuals cf "Page/Visual.Visual" --theme-colors "dataPoint.fill"    # convert existing hex assignments to tokens
```

## off-grid drift

Positions that are not on the grid unit, and gaps that are close but not equal, read as sloppy even at a 4-8px difference; the eye catches the misalignment before it reads the data. Repair: snap every position to the grid unit and recompute gaps arithmetically from margin, gap, and canvas size. The arithmetic and the continuous-gutter rule are in `references/layout-guidelines.md`.

## dual y-axis abuse

Two unrelated measures on two independent scales invite a false reading: the lines cross or diverge by axis choice, not by the data. Repair: use a second axis only when two genuinely different units share one category axis. Otherwise split into two visuals, or index both measures to a common base so one axis serves both.

## 3D anything

Perspective distorts the length and area the reader is trying to compare; a 3D bar is taller or shorter by viewing angle, not by value. Repair: flat 2D, always. There is no analytical task a 3D chart does better than its flat version.

## pie beyond a few slices

A pie forces angle and area, the weakest channels, and past roughly four parts the slices stop being distinguishable. Repair: a sorted bar chart with the long tail grouped into "Other". The slice-count threshold and the Top-N-plus-Other pattern are in `references/chart-selection.md`.

```bash
pbir set "Page/Visual.Visual.visualType" --value "clusteredBarChart"   # swapping the type may need fields rebound to the new roles
```

## exotic build path for a core form

A Deneb spec, an SVG-via-DAX measure, or a Python/R script that compiles to a plain bar, line, or scatter takes on a dependency for a form a core visual already draws. The convenience is the author's, one spec away; the cost is the report's, permanently. Repair: read the spec back, decide what it actually draws, and rebuild on the core type.

```bash
# deneb_spec.py ships with the deneb-pbir skill
python deneb_spec.py extract "<...>/visual.json" -o spec.json   # then read the top-level mark / marks[].type
```

A `bar` or `line` mark with one x/y encoding and no layer, facet, transform, or signal is a `clusteredBarChart` or a `lineChart` written the long way. Two things make this a rebuild rather than a `visualType` swap: Deneb binds every field to a single `dataset` role, which does not map to the Category and Y roles the core type expects, and the visual's GUID has to come out of the `report.json` `publicCustomVisuals` array once nothing references it. Weigh the cost of staying on the spec too: on a core type, sorting, data labels, and the single accent come from `pbir visuals sort`, `labels`, and `dataPoint`, which is what every other repair in this file writes; inside a spec each of them is hand-written into the encoding. The build-path ranking, and the cases that genuinely earn the exotic path, are in `references/custom-visuals.md`.

## two hues for one quantity

Two series drawn side by side in two unrelated hues assert that they are two different things. When they are two parts of one quantity (this year and last, plan and actual, two segments of one total) the hue difference is a claim the data does not make, and the clustered form doubles the bar count to say it. Repair: restructure before deleting anything. Swap to the stacked variant so the total is readable, then color the pair from one `ColorId` at two `Percent` values instead of two `ColorId`s.

`pbir set` cannot reach `visualType` at all; any path that is not `component.property` is rejected. The retype is an edit to `visualType` in `visual.json`, then a rebind. Write the id Power BI stores: the stacked column chart is `columnChart` and the stacked bar chart is `barChart`. `stackedColumnChart` and `stackedBarChart` are aliases `pbir schema describe` resolves for you, not values that belong in the file.

```bash
pbir schema describe stackedColumnChart                   # prints the id pbir reads and writes
pbir schema roles columnChart                             # Category, Y, Series: the roles to rebind into
pbir visuals bind "Page/Visual.Visual" --list-roles       # again after the edit, so a dropped binding surfaces
```

Each series carries one of these as the `expr` under its `dataPoint.fill.solid.color`:

```json
{"ThemeDataColor": {"ColorId": 1, "Percent": 0}}
{"ThemeDataColor": {"ColorId": 1, "Percent": -0.35}}
```

`Percent` is a tint/shade adjustment on the theme color (-1.0 to 1.0; negative darker, positive lighter, 0 exact), so the pair stays one hue and still re-themes. State the cost out loud before swapping: stacking makes the total comparable and the upper segment not, because only the bottom segment sits on a common baseline. Stack when the question is composition; keep the clustered form when the second series is the thing being compared.
