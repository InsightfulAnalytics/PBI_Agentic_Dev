# Silent traps: Deneb, Vega and Vega-Lite

Things that compile, render and warn nowhere, then draw the wrong picture or nothing. Each one cost
a session to find. SKILL.md's Gotchas section covers the field-name contract, escaping, sizing and
the 2.0 transition; this file covers the rest.

Unless a line says otherwise, the Vega and Vega-Lite items were found by offline render against
Vega 6.4.0 / Vega-Lite 6.4.3, the pair Deneb 2.0 bundles (September 2026), and the Deneb items in
Power BI Desktop 26.08.

## Report-page tooltips

Two things must both be right, and the failure looks identical either way: hovering shows the
ordinary dark Power BI tooltip listing fields instead of the tooltip page, with no error and a clean
`pbir validate`.

1. **The page.** Page-level `"type": "Tooltip"`, not `pageBinding`, and the raising visual's
   `visualTooltip.type` is `'Canvas'`. See `pbip:pbir-format` `references/page.md`.
2. **The datum.** Deneb resolves the row from the hovered mark's **datum**, never from the tooltip
   payload (`resolveDatumFromItem` then `getResolvedRowIdentities` in `tooltip.ts`, read on Deneb
   main, September 2026). So:
   - naming `__row__` in a Vega-Lite `tooltip` channel does nothing for resolution; it only prints
     a row number in the fallback tooltip;
   - any tooltip property fires the handler: `"tooltip": true` on the mark, or one field in a
     `tooltip` channel;
   - `__row__` must reach the mark's datum as an in-bounds integer. `calculate`, `joinaggregate`
     and `flatten` keep it; **`aggregate` drops it**, and a mutated value is rejected;
   - `enableTooltips` must be `true`. It is the default, but a hand-authored visual.json carrying
     `false` kills an otherwise correctly wired tooltip page. Conversely, switching the container's
     `visualTooltip.show` off is only half of turning tooltips off: Deneb still calls the host
     tooltip service until `objects.vega[0].properties.enableTooltips` is `false` too.

**A `line` or `area` is one mark for the whole series**, so no row resolves from a hover on it. Add a
per-row hover layer (transparent points, or one `rect` per row as a band) as the last layer, painted
with `fillOpacity: 0`, never `fill: "none"`, which does not hit-test. The pattern and the reasoning
are in `reports:pbir-cli` `references/interactions.md`, "Deneb: a line mark has no per-row hover".

**A hover card drawn inside the spec** (for styling the native tooltip cannot do): a `group` mark
whose children draw `from` a dataset that is empty unless a selection signal is set, so the card
hides itself. Drive the signals from `mouseover` and `mousemove` on the marks; a transparent
`line` with `strokeWidth: 16` named as the hit target gives whole-line hover, and `mousemove`
makes the card follow the cursor. Aggregate inside the card the way the visual's grain demands: a
per-year dataset summed across years, percentages weighted by their counts, never a plain `max`.

## The container is a clip rect

A Deneb visual's container clips its marks. Ink outside it is silently sliced, and neither
`pbir validate` nor a spec review sees it: the spec is right, the geometry is right, and the panel
ships with the top of its biggest number cut off.

- **Never resolve a `pbir validate --qa` VISUAL_OVERLAP advisory by moving a Deneb container.**
  Moving one 6px down to clear a textbox, with its internal offsets reduced by 6 to compensate, put a
  22px figure's baseline 12px from the top under a cap height of about 15px, and the figure shipped
  with 3.4px missing. Move the textbox, widen it, or accept the advisory: a Deneb background is
  transparent, so an overlap with a higher textbox is invisible.
- **The check:** re-render every spec with `"padding": 24` alongside `"autosize": "none"`. Vega does
  not clip the root group, so anything the container would cut is painted into the margin instead.
  Any ink there is a clipped mark. A full-bleed stroke centred on the edge puts half its width
  outside by design, so treat under one pixel as fringe, not failure.
- A composite diff against an artboard cannot see this: it crops each panel to its own container,
  so the missing ink is outside the window it compares.
- Headroom: a text mark's cap height is about 0.70 of its font size above the baseline, and digits
  sit on the cap line. A 26px numeral needs about 19px of container above its baseline, not 13.

## Data shape

**The field well sets the grain, not the spec.** A Values well holding only measures returns
exactly **one fully aggregated row**. A spec that runs `density`, `quantile`, `regression`, `loess`,
`window` or a `q1`/`q3`/`median` aggregate over one row draws one degenerate mark and raises nothing.
Check the `field` wrapper on each projection in the visual's `queryState`: all `Measure` and no
`Column` means one row is coming, whatever the spec asks for. Project a dimension; it needs no
reference in the spec to do its job. A template that declares a column placeholder its body never
reads (one declared only "for grain") still needs that column bound.

**A measure that varies by a column on the visual multiplies the rows.** A grid that puts a week
column on the visual and groups by measure fields turns each line into one row per week, and a
Vega `lookup` on a now-duplicated key resolves to one arbitrary tuple, so whole blocks of values
draw far below the viewport and the week columns look empty. Make the left-hand measures invariant
to that column, `CALCULATE ( [Base], ALLSELECTED ( 'Calendar' ) )` over the **whole** calendar table
when the visual groups by more than one of its columns, and aggregate measure fields rather than
grouping by them.

**The `dataset` entry keeps its `format`.** Deneb hands the rows to a Vega spec as `values` on the
first data entry named `dataset` and keeps everything else on that entry. Vega reads `values` before
`url`, so a demo `url` is harmless, but a `csv`, `tsv` or `dsv` `format` turns the array of objects
into **zero rows**. Strip the demo file's `format` from `dataset` when adapting a template authored
against a CSV. In Vega-Lite, Deneb adds `datasets.dataset` and leaves the spec's own `data` as
authored, so the entry's `format.parse` still runs on Deneb's rows: a date pattern such as
`"date:'%d/%m/%Y'"` turns Deneb's Date objects into null, every row lands on one cell in 1970. Use a
plain `date` or no parse at all. (Read in deneb-viz/deneb, `patchVegaSpecWithData` and
`patchVegaLiteSpecWithData`, September 2026.)

**Deneb hands a dateTime column to the spec as a JavaScript Date; Vega's own `date` parse returns a
number** (milliseconds, through vega-util `toDate`). An offline render fed ISO text therefore sees
timestamps where Deneb sees Dates, and `pbiFormat` prints them differently. Only axis ticks and
`timeUnit` output reach a spec as real Dates in both runtimes. When a date label disagrees between the two, check
what type reached the expression before touching the format.

**Certified Deneb loads no `url` data at all.** A `data` entry with a non-`data:` url resolves to
nothing and the mark draws no rows, quietly; the image half of the same rule is in SKILL.md, "Images
and external resources". Hyperlinks (`href`) go through the host's `launchUrl`, http and https only.
Deneb also renders with Vega's default `autosize` when a spec states none, and its viewer scrolls a
canvas that overflows. (Read in `getVegaLoader`, `apps/deneb/src/lib/vega-embed/loader.ts`, Deneb
main, September 2026.)

**A measure with a dynamic format string may not get a usable `__formatted` companion**: the raw
double printed instead (Deneb 1.9.1, July 2026). Give the column an explicit d3 `format` or format
it in the spec with `pbiFormat` and the measure's format string.

**Template placeholders are replaced only by Deneb's Import template dialog.** Pasting a template
into the JSON editor leaves `__0__` in place, and the chart draws nothing with axis titles reading
`__0__` and `Sum of __1__`, Vega-Lite's auto-titles from the field name. The substitution is a
global text replace of the key with the **display name** of the field in the Values well. A key
declared in `usermeta` but absent from the body is a silent no-op: Deneb still demands every field
be assigned, then substitutes nothing. Keep index keys contiguous from zero. (Read in Deneb's source
at tag 1.9.1.0 and on main, 2026-09-18; the custom-key behaviour is in
[capabilities.md, v1 (legacy)](capabilities.md#v1-legacy).)

**Do not hard-code a categorical colour domain when a slicer can change the member set.** Members
outside the list come out uncoloured: invisible lines, blank legend swatches. Colour by a tie-free
rank measure with a numeric domain (`[1, 5]` for a top five), so any selection's members get
consistent colours, and every visual reading the same measure agrees.

**Pick a dynamic callout in the spec, not in DAX.** For "biggest climber" or "steadiest member"
labels, bind simple per-member measures (first rank, last rank, rank range) and choose the member with
a `window` `row_number` in the spec. Each measure stays checkable with a DAX query, and the selection
logic stays where the chart can see it.

## Vega-Lite compiler traps

All of these compile and render with no warning, except the two that crash, which crash with an
error naming nothing useful.

- **A `rule` mark in a layer with no `encoding` block crashes the compiler.** Give every constant
  rule an encoding, even `{}`.
- **Mark-level `x`/`y`/`width`/`height` on a `rect` compile to `xc`/`yc`**: the pair is read as the
  mark's centre, so the rect lands half its size up and left. Use `datum` encodings on x/x2/y/y2.
  Mark-level `x`/`y` on a `text` mark is fine. Mark-level position constants on other marks can
  blank the visual; position through `encoding` (`"y": {"value": 24}`) or a per-row pixel field with
  `"scale": null`.
- **A `datum` x paired with a `field` x2 crashes**, because x2 inherits its type from x's field
  definition. Keep both channels the same kind; give a constant left edge its own field
  (`{"calculate": "168", "as": "barX"}`). This is the most common way to write a bar panel wrongly.
- **A `color` encoding carrying `field` alongside `condition` and `value` kills the compiler** with
  `Cannot read properties of undefined (reading 'replaceAll')` inside `description()`. A conditional
  colour takes `{"condition": {"test": ..., "value": ...}, "value": ...}` and nothing else; put the
  field the test reads into a `calculate`.
- **A mark-definition `fill` overrides a `color` encoding**, conditions and all. Omit `fill` when the
  layer has a colour condition.
- **A secondary position channel takes no `condition`.** `y2` with a condition compiles and is wrong.
  Compute the override as a field and encode it with `"scale": null`.
- **`order` on an `area` or `line` compiles the mark into a `group` and drops a gradient fill.** It is
  also unnecessary: path marks already draw in x order.
- **`aggregate` with no `groupby` yields exactly one row**, which is how a derived constant line (a
  median) is drawn once. `joinaggregate` gives every row the value instead.
- **A layer with no `data` of its own inherits the bound dataset** and draws once per row. A header
  or annotation layer needs `"data": {"values": [{}]}`.
- **A `point` mark's `size` is its area** in square pixels, `PI * r * r`: a radius of 3.6 is `40.72`.

## Vega rendering traps

- **There is no letter-spacing.** `letterSpacing` is not in the text mark schema and is dropped, in
  Vega and Vega-Lite alike. Tracked type has to come from elsewhere (a background image, an SVG
  measure).
- **Text marks do not wrap.** A long string runs off the mark. Multi-line copy needs an explicit
  separator in the string plus `lineBreak` and `lineHeight` on the mark, so every wrapped string is
  a hand-set break and a wording change can overrun its box with nothing to warn you.
- **`format()` writes U+2212 MINUS SIGN for negatives**, not a hyphen. Wrap it in
  a `replace()` that swaps U+2212 for `-` when matching a design that sets a hyphen.
- **`"autosize": "fit"` with marks positioned from the `width` signal and no x scale is circular**:
  fit sizes the plot from the marks and the marks from `width`, so `width` collapses and every
  right-aligned column piles up at one x. For a table-like layout with no x scale, set
  `"autosize": "none"`, an explicit numeric `width`/`height` a few pixels under the visual's
  recorded `objects.stateManagement` viewport size, `"padding": 0`, and fixed pixel x positions.
  This is the one exception to SKILL.md's "no literal width/height" rule.

## Rendering outside Deneb

For offline checks and for any copy of a spec rendered outside Power BI:

- `formatType: "pbiFormat"` needs `config.customFormatTypes: true`, or Vega-Lite prints the raw number
  (0.978 for 97.8%). Deneb merges it in at runtime and the `deneb-pbir` renderer does the same; a
  hand-rolled renderer must too. `pbiFormatAutoUnit` needs its own stub beside `pbiFormat`, or a spec
  naming it draws nothing.
- Vega's SVG renderer paints the chart background as a style on the `<svg>`. A standalone copy that
  strips styles loses it; paint it back as a rect.
- Vega swallows image load failures. A relative image href resolves against the hosting page. Probe
  each `<image>` href rather than trusting the render.
- An offline renderer without Segoe UI measures text wider than a browser does (about a third wider
  for the fallback font), so an offline `limit` truncation is not evidence of a real one. Measure the
  exact string against the real font instead, for example Pillow's
  `ImageFont.truetype("segoeui.ttf", px).getlength(s)` (`segoeuib.ttf` for bold) on Windows.

## In Desktop

- **A Deneb visual renders blank for a few seconds after `pbir desktop refresh`.** The custom visual
  re-initialises on every report reload; wait about 8 seconds before a screenshot or it captures an
  empty card. Native visuals are ready at once.
