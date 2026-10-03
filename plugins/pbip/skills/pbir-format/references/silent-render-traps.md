# PBIR that validates and still renders wrong

Every rule in this file passes `pbir validate`, `--semantic` included, because the property names
are real. Only the render was wrong, and only opening the report in Power BI Desktop showed it.
[validation.md](./validation.md) has the shorter list of failures that break a whole report; this
file is the per-visual list.

Three habits catch most of these before they cost a session:

1. **Ask the schema before writing a property.** `pbir schema describe <type> <object>` lists the
   real properties and enums. Then read what a Desktop-authored file does for the same visual type:
   a census across real reports beats any one example.
2. **Walk every cross-reference with a script** (bookmark targets, navigator page ids, tooltip
   `section` names) and count resolved against dangling. Desktop and `pbir validate` both accept any
   string where a reference is expected, so a dangling one is silent.
3. **Render it and look.** For a state-dependent property (hover, press, selected), drive the click
   through UI Automation and diff the pixels; a static screenshot cannot judge a hover. In Desktop
   **edit mode** a button's navigation or bookmark action fires only on **Ctrl+click**.

(Unless a line says otherwise, observed in Power BI Desktop 26.08, September 2026.)

## Slicers

**A hand-authored classic `slicer` keeps a bare `objects` block.** `data` carrying `mode`, and an
empty `general`:

```json
"objects": {
  "data": [{"properties": {"mode": {"expr": {"Literal": {"Value": "'Dropdown'"}}}}}],
  "general": [{"properties": {}}]
}
```

Adding a hand-written `selection.singleSelect` object and a preset selection in the slicer's own
`filterConfig` left a slicer that rendered and took clicks but **stopped filtering other visuals**.
Stripping back to `data` plus `general` restored it at once. Set single-select in the format pane
(one click) rather than hand-authoring it. Prove the model and the receiving visual each work alone
before suspecting the slicer; once both do, the slicer JSON is the only link left. (June 2026
Desktop build.)

**A dropdown slicer's flyout paints itself with `slicer.items.background`.** Unset, the list is
transparent and the report reads straight through it. The flyout also hangs outside the slicer's
container, so give the container `background` `show: true`, white, transparency 0 as well.

**The slicer `header` repeats the field name under a container title that already carries it.**
Turn one of them off. To use the header as the label instead of a separate textbox, set
`header.show`, `header.text`, `header.textSize`, `fontFamily`, `fontColor`, and
`header.showRestatement` to `false`; otherwise the header also prints the current selection.

**Button slicer (`advancedSlicerVisual`):**

- Converting a classic `slicer` is a `visual.visualType` edit; no `pbir` command does it. The
  `Values` role, `general.filter` (default selection) and `selection.singleSelect` carry over.
  Style it with state-keyed entries, one under `"selector": {"id": "default"}` and one under
  `{"id": "selected"}`: `fillCustom.fillColor`, `value.fontColor` and `bold`,
  `shapeCustomRectangle.rectangleRoundedCurve`, `outline.show`. The group label is the container
  `title`, not the old slicer `header`.
- **Vertical fit comes from `layout.columnCount: 1` plus `layout.rowCount` = the item count.** That
  shows every item and sizes the buttons to fill the visual's height, so the visual's own height
  then sets the button height. `cellPadding`, `fixedHeight` and `autoGrid` had no visible effect.
- **`layout.showFixedSize` with `fixedWidth`/`fixedHeight` does not pin a tile size; it wrecks the
  grid.** Every slicer collapsed to one column with a scrollbar, `columnCount` ignored. To make
  every tile the same size whatever the cardinality, size the container instead: zero the four
  `*OuterMargin`s under `customizePadding: true`, put the section label in its own textbox rather
  than the container title, and set height = `rows * tileHeight + (rows - 1) * gap`.
- A theme's wildcard `padding` reaches slicers too. See [Theme wildcards](#theme-wildcards-reach-further-than-expected).

## Buttons, navigators and bookmarks

**Any button state left unset gets Power BI's own hover and press treatment.** That is why a
35%-transparent scrim flashed opaque under the pointer. Emit one selector-less `show: true`, then
the same values again under each of `default`, `hover`, `press` and `selected`. A fill-less button
still needs `show: true` plus `transparency: 100`; `show: false` hands the states back to Power BI.

**`actionButton.icon.shapeType` is a closed enum**: blank, leftArrow, rightArrow, back, reset, help,
information, qna, bookmarks, applyAllSlicers, clearAllSlicers, custom, spinner. A value outside it
renders nothing at all. `custom` plus `icon.image` takes any image:

```json
"image": {"image": {
  "name": {"expr": {"Literal": {"Value": "'icon-filter'"}}},
  "url": {"expr": {"ResourcePackageItem": {"PackageName": "RegisteredResources", "PackageType": 1, "ItemName": "icon-filter.png"}}},
  "scaling": {"expr": {"Literal": {"Value": "'Fit'"}}}
}}
```

The file goes in `StaticResources/RegisteredResources/` and `report.json` lists it under
RegisteredResources with `"type": "Image"`. `icon.lineColor` does not reach a custom image, so bake
the colour into the pixels. When rasterising an icon font glyph (a Material Symbols path, say), centre
it on the glyph's own bounding box, not the viewBox: the glyph can sit a few percent off-centre inside
it. `bookmarkNavigator` has no `icon` object at all, so its mark has to be the bookmark's
`displayName` rendered as text.

**`text.verticalAlignment: 'middle'` centres a button label.** Unset, both `pageNavigator` and
`actionButton` sit the text low. Their side margins default to non-zero, enough to wrap "Clear" in a
48px button, so zero `leftMargin` and `rightMargin`. The margins are number-typed on `pageNavigator`
(`0D`) and integer-typed on `actionButton` (`0L`).

**A `bookmarkNavigator` label can be sized but not nudged.** `bottomMargin` does nothing under any
`verticalAlignment`, a negative `topMargin` clamps to zero, and `topMargin` under
`verticalAlignment: 'top'` moves the label down one report unit per unit. Fix a glyph that sits low
by picking the font size whose line box lands centred, measured rather than guessed.

**One button that toggles a panel open and shut is a `bookmarkNavigator`, not an `actionButton`.**
`visualLink.type` has no deselect half (its enum is Back, Bookmark, Drillthrough, PageNavigation,
Qna, WebUrl, ApplyAllSlicers, ClearAllSlicers, DataFunction). Point the navigator at a bookmark group
of two, Open and Close, with `allowDeselectionBookmark`, `deselectionBookmark` (Close) and
`hideDeselectedBookmark`: the strip renders as one button, select fires Open, deselect fires Close.
Its label is the Open bookmark's `displayName`. It stays in sync when Close fires from somewhere
else (a scrim click), because Close is in the same group.

**`ClearAllSlicers` cannot clear a slicer a bookmark has hidden.** It acts on what is on screen, so a
Clear button on a collapsed panel fires and changes nothing. Verified both ways in Desktop: panel
open, the chart rescales; panel shut, the same click does nothing. Expect `ApplyAllSlicers` to have
the same blind spot (inferred, not tested). The replacement is a **data bookmark**:

- per slicer, one `filters.byExpr` entry naming the column, `type: "Categorical"`, `howCreated: 0`
  and **no condition** (no condition is what "cleared" means), plus `singleVisual.activeProjections`;
- `advancedSlicerVisual` needs `objects: {}`; a dropdown `slicer` needs
  `objects.merge.data[0].properties.mode = 'Dropdown'`;
- `options.applyOnlyToTargetVisuals` with only the slicers listed, no `display` block and no
  `visualContainerGroups`, so it clears without moving the panel. Keep it out of the navigator's
  bookmark group.

The `byExpr` `name` is a 20-hex id that only has to be unique. Read the shape back rather than
guessing it: clear the slicers in Desktop, add a bookmark, save, and read the file.

**A `pageNavigator`'s `pages` selector id is the page's PBIR `name`, not its display name.** That
is the folder under `definition/pages/` and the `name` in `page.json`. A selector naming anything
else is dropped and that button never appears. The block is one selector-less entry carrying
`showHiddenPages` and `showByDefault`, then one `{showPage: true}` per page keyed by name.
`showByDefault` switches between "these pages" and "every page": leave it `true` and list pages as
well, and the listed ones come out twice. Power BI marks the current page's button selected itself.

**A bookmark shows a hidden visual by omitting `display`.** See [bookmarks.md](./bookmarks.md).

## Shapes, textboxes and containers

**A shape's fill colour needs its own entry under `selector: {id: "default"}`; only the bare
`show` switch is selector-less.** Without it every shape renders in theme colour 1. A census of
Desktop-authored reports found 161 of 161 `fill.fillColor` entries carrying that selector and 418 of
418 bare `show` entries carrying none. The general rule is in
[visual-container-formatting.md](./visual-container-formatting.md), "What Goes Wrong".
`roundEdge` and `rectangleRoundedCurve` are both real on a `shape` and both render rounded corners;
swapping one for the other changes nothing.

**A `basicShape` rectangle renders at least about 12px tall.** A "2px" divider draws as a thick bar.
For a hairline rule use a thin `image` visual (a tiny solid PNG, `scaling: 'Fill'`), which honours
the exact box height. A legacy `shapeType: line` did not render at all.

**A textbox draws a vertical scrollbar whenever its content is taller than its container**, and the
`padding` block does not buy the space back. A minimum height that renders clean is
`ceil(pt * 96/72 * 1.45 * lines) + 12` (an 8pt single line needs about 24 to 28px, not 16). A
standalone textbox also carries enough top padding that a 10pt caption clipped to a sliver below
about 48px; put a page subtitle in the page-title textbox as a second paragraph rather than giving it
its own visual. A visual's own subtitle never needs a textbox: it goes in the visual's `subTitle`
slot ([visual-container-formatting.md](./visual-container-formatting.md), "Title and subtitle
text").

**Container objects live under `visualContainerObjects`, never `objects`.** `visualHeader`,
`visualTooltip`, `visualLink`, `title`, `background`, `border` and `padding` written under
`visual.objects` validate, survive a Desktop save untouched, and do nothing. The symptom is a default
tooltip on a panel whose author believed tooltips were off. A theme's
`visualStyles."*"."*".visualHeader[0].show = false` is only a default: set the per-visual property
as well, which is what Desktop writes when a person toggles the card and what survives a theme swap.

**The selection pane name is `visualContainerObjects.title[0].properties.text`.** Keep
`title.show: false` and the visual is named without a title bar.

**A `visualGroup` visual.json has no `visual` key.** Any script that globs `**/visual.json` and
reads `.visual.visualType` throws the moment a page carries a group, and the stack trace points at
whatever the script was doing, not at the group. Filter on the key's presence, not on the path.

**`VisualTopN` written as `{ItemCount: n}` passes `pbir validate` and is ignored by Power BI.** Use a
Top N filter Desktop has written, read back from a saved file.

## Theme wildcards reach further than expected

- **`visualStyles."*"."*".padding` and `dropShadow` apply to `shape` visuals and to slicers.** Chrome
  built from shapes came out inset (a 28px logo drew as a 12px dot, nav labels vanished) and every
  unfilled shape wore a faint shadow outline. Desktop's base theme zeroes `shape.*.padding`; a
  custom theme's `*` overrides that. A slicer that inherits the wildcard loses 8px top and bottom
  and 10px left and right, enough to drop a column out of a tile grid. Write zero `padding` (four
  values) and `dropShadow` off into every generated visual's `visualContainerObjects`, and add a
  `shape` block to the theme.
- **The Fluent2 base theme turns on `cardVisual.*.outline` and `borderCustom` (`$id: default`)**, so a
  new card draws a bordered rectangle inside its container. Turn both off with
  `selector: {id: 'default'}`.
- When a generated page looks inset, framed or double-captioned, diff the custom theme's `*` block
  against the base theme's per-visual blocks before touching the visual. On Windows the base themes
  ship with Desktop under its install folder,
  `bin\WebView2Resources\minerva\sharedresources\BaseThemes\Fluent2-*.json`.

## Project files

**A blank "Untitled" Desktop window with no error means malformed entry-point JSON**, not a TMDL
problem. The usual causes are a wrong `$schema` URL in the `.pbip`
(`fabric/pbip/pbipProperties/1.0.0`, see `pbip:pbip` `references/pbip-file-types.md`) or in
`definition/version.json` (`.../definition/versionMetadata/1.0.0`, see
[version-json.md](./version-json.md)), and a `report.json` with no `themeCollection` (see
[report.md](./report.md)). Copy the entry-point files from a project Desktop has saved and diff,
rather than writing the URLs from memory.

**The base theme is not optional, even when a custom theme is.** On a 2.155 build (June 2026) a
`report.json` with no `baseTheme` failed with "Failed to load the report"
(`System.NullReferenceException` in `ReportViewDocumentProvider.GetEnhancedReportDocument`) while the
model loaded fine. It needs the `themeCollection.baseTheme` entry, the matching `SharedResources`
item in `resourcePackages`, and the theme file itself under
`StaticResources/SharedResources/BaseThemes/`; copy all three from a report the same Desktop build has
saved. An older report with only a `customTheme` can keep opening, because the requirement arrived
with newer builds.

**A Desktop save rewrites the whole report definition.** It bumps `$schema` versions (2.9.0 to
2.12.0 was seen), reorders position keys and drops defaults such as `drillFilterOtherVisuals`. On one
report, nine hand-written tooltip pages, nine Deneb specs and ten `visualTooltip` blocks all
survived a save with only key reordering and `"parameters": []` added to each `pageBinding`. Treat
that as evidence about those structures, not as permission to save freely: diff after any save of a
hand-authored report.
