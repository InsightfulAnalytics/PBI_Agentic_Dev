# pbir CLI traps

Commands that exit 0 and did something other than what was asked, or that report a fault that is not
there. The relative-path hijack by an active connection is the biggest of these and lives in
[cli-reference.md](./cli-reference.md), "Report Creation and Management"; this file carries the rest.

Every item was observed on pbir 0.9.x under Windows between July and October 2026. Items stamped
"still on 0.9.33" were re-run on that release on 27 October 2026, from the CLI side only. Before
relying on one, run the command's `--help` and check whether a newer release changed it.

## `pbir desktop`

**`pbir desktop screenshot <report>` renders the first page whatever page you pass.** Handing it one
page path (or a `page.json`) does not switch pages, so a per-page sweep built on it silently
captures page one every time. Use `--all` and take the file you want, or select the page tab first
through UI Automation (`pbi-desktop:connect-pbid` `references/desktop-ui-automation.md`), which works
on a background window.

Retest: `pbir desktop screenshot "<Report>.Report/<second page>.Page" -o p2.png` on a report whose
pages look different, and compare `p2.png` with page one.

**Never grep the `pbir desktop list` table for a report name.** On 0.9.32 the Open File column cut a
deep path short with an ellipsis (`...\.scratch\report-ha…`); on 0.9.33 it wraps the path across
lines instead, which can split the name just the same. Either way a wait loop that greps for the name
hangs until its timeout instead of failing:

```bash
# Can never match. Runs until the timeout, whatever Desktop is doing.
until pbir desktop list | grep -qi "MyReport"; do sleep 3; done
```

Use `pbir desktop list --json` (0.9.33): a top-level `status` (`ready`, or `not_connected` when no
Desktop is reachable), `connectionErrors`, and per instance `pid`, `currentFilePath`,
`hasUnsavedChanges`, `reportDir` and `pages` (`name`, `displayName`), none of them truncated. Match
the report on `currentFilePath`. (Verified 2026-10-27 with Desktop 26.10 open.)

Retest: `pbir desktop list` with a project open from a deep path, then `pbir desktop list --json`.

**A row in that table means Desktop has a window, not that the report has loaded.** A screenshot
fired the moment the row appeared failed with
`application.state.get/v1: Another operation is already in progress`. Retry the operation you
actually want in a loop instead of waiting on the list and firing once.

**`pbir desktop refresh --model` refuses a model below `compatibilityLevel` 1606**; raise it in
`database.tmdl`. It also re-applies the model definition **without refreshing data**: after a Power
Query change, invoke Desktop's "Refresh now" banner (a plain UI Automation button) or ask the user to.

**A Deneb visual draws blank for a few seconds after `pbir desktop refresh`**, because the custom
visual re-initialises on every reload. Wait about 8 seconds before a screenshot.

## `pbir validate`

**`--fields` resolves names against a compiled model, not against the TMDL you just edited.** With a
thick (`byPath`) report and no compiled model to read, field validation is skipped. With a stale one
it reports `FIELD_NOT_FOUND ... not found in table` for measures that exist: 13 newly hand-added
measures were reported missing while the engine evaluated all of them. The compiled artefact is
rewritten when Desktop saves (`.pbi\cache.abf` changes in the same second), so a hand edit Desktop has
never seen can be invisible to `--fields`.

The symptom does not look like staleness. The fault follows the target path (copy the `.Report` and
`.SemanticModel` elsewhere and the identical trees validate clean, because copying resets every
mtime), and the failing measures are the ones at the tail of the file, which reads like truncation.

**The fix:** open the project in Desktop, refresh and save; the warnings go at once. When `--fields`
disagrees with TMDL you just wrote, suspect the compiled model before the file, and confirm against
the engine with a DAX query (`pbi-desktop:connect-pbid`). `pbir validate` without `--fields` is
unaffected: the schema, QA and overlap checks read the PBIR directly.

Schema-version warnings such as `'2.10.0' not available locally` are harmless fallbacks.

## Adding and setting

- **`pbir add filter <Table> <Field> -r "<...>/Some.Visual"` adds a report-level filter, not a
  visual-level one.** `-r` targets the report whatever path follows it. A stray Top N filter added
  this way silently filtered every visual in the report to one row. It does not show under the
  visual's own filters; find it in `report.json` `filterConfig` and remove it with
  `pbir rm "<Report>.Report/filter:<name>"`. To scope a filter to one visual, set it in that visual's
  own `filterConfig`. (Still on 0.9.33; pbir.tools #74.)
- **`pbir add page "<Report>.Report/<Folder>.Page" -n "<Display>"` also creates a default title
  textbox** (folder `Title`, 480x120 at 20,20), and `pbir add visual` then refuses anything that
  overlaps it unless you pass `--force`. Remove it when the page gets its own header. The page
  folder on disk is a hash, not the path segment you typed. (Still on 0.9.33.)
- **pbir addresses pages and visuals by display name** (`"<Report>/Opening Tooltip.Page"`), not by
  the hash folder. A glob through a page path that contains spaces (`".../Opening Tooltip.Page/*.Visual"`)
  matched no visuals; operate per visual instead.
- **`pbir set ...visualTooltip.*` fails on a custom visual** with `Unknown component: visualTooltip`,
  because custom visuals are not in the core catalog. Edit the visual.json directly
  (`pbip:pbir-format` `references/page.md`, Tooltip Pages). `pbir pages set-tooltip` sets the page's
  `type` and `displayOption`; set `visibility` to `HiddenInViewMode` separately. (Still on 0.9.33.)
- **`pbir visuals title` takes `--show` / `--no-show`.** There is no `--hide` and no `-f`.
- **`pbir add title` and `pbir add subtitle` add page-level textboxes; they never set a visual's
  title.** A visual's own title and subtitle are `pbir visuals title "<Visual>" --text "..." --show`
  and `pbir visuals subtitle`, or `--title` on `pbir add visual`. A textbox standing in for one
  visual's title is a design finding (`reports:pbi-report-design` `references/page-titles.md`).
- **The title commands write an apostrophe undoubled.** `pbir visuals title --text "Each store's
  sales"` stores `'Each store's sales'`, and `pbir visuals subtitle --text` and
  `pbir add visual --title` do the same. A PBIR string literal needs the apostrophe doubled, and
  `pbir validate` reports the broken one as valid. Pass it already doubled,
  `--text "Each store''s sales"`, which pbir stores as `'Each store''s sales'`. In PowerShell, use
  double quotes around the argument so the two apostrophes reach pbir as typed. (pbir 0.9.32.
  Verified 2026-10-03; still on 0.9.33; pbir.tools #72.)

  Retest: `pbir visuals title "<Visual>" --text "It's"`, then read the `title` entry in that
  visual.json.
- **`pbir visuals deneb` has the same undoubled-apostrophe bug, and it breaks the whole visual.**
  It writes `jsonSpec` without doubling the `'` characters, and a Vega spec is full of them (every
  string literal inside an expression). Power BI Desktop then draws nothing where the visual sits:
  no error, no placeholder, not even the spec's static marks. `pbir validate` passes. Embed with
  `deneb_spec.py embed` from the `custom-visuals:deneb-pbir` skill instead, which doubles them.
  (pbir 0.9.32. Verified 2026-10-09; still on 0.9.33; pbir.tools #72.)

  Retest: embed a spec containing `"expr": "'a'"` with `pbir visuals deneb`, then count the `'`
  inside the `jsonSpec` literal: correct output has twice as many as the spec file.
- **`pbir set --value` writes `'` undoubled too, in any string property.** A font stack in Desktop's
  own quoted form, `--value "'Segoe UI Bold', wf_segoe-ui_bold, helvetica, arial, sans-serif"`, is
  stored as `''Segoe UI Bold', wf_segoe-ui_bold, ...'`, a broken literal. Pass a font stack unquoted,
  `--value "Segoe UI Bold, wf_segoe-ui_bold, helvetica, arial, sans-serif"`, which Desktop renders in
  the right face. (pbir 0.9.33. Verified 2026-10-29.)

  Retest: `pbir set "<Visual>.values.fontFamily" --value "'Segoe UI Bold', arial"`, then read
  `fontFamily` in that visual.json.
- **Container formatting on a custom visual is out of reach of `pbir set` and `pbir visuals`.**
  `title`, `padding`, `background`, `border` and `dropShadow` all fail with `Unknown component`,
  with `--rawdog` and with `--skip schema` too; `pbir visuals general --altText` is the one that
  works. Put the defaults in the report theme under the visual's type,
  `visualStyles["<visualType>"]["*"]` (for example `deneb7E15AEF80B9E4D4F8E12924291ECE89A`), apply it
  with `pbir theme create-template` + `apply-template`, and clear visual-level leftovers with
  `pbir visuals clear-formatting "<Visual>" --only-containers -f`. That also clears `altText`, so
  set it again afterwards. (pbir 0.9.32. Verified 2026-10-09; still on 0.9.33; pbir.tools #52, fixed for 1.0.)
- **A slicer's default selection cannot be set.** `pbir set "<Slicer>.general.filter" --json ...`
  fails with `Component 'general' has no property 'filter'. Did you mean: filter, selfFilter?`, with
  or without `--rawdog`. Select the value in Desktop and save, or give the measures a sensible
  fallback for the no-selection state. (pbir 0.9.32. Verified 2026-10-09; still on 0.9.33; pbir.tools #77.)

  Retest: the same `pbir set` with a one-value `In` filter, then read `objects.general` in the
  slicer's visual.json.
- **Two containers fail on core visuals too: a page navigator's `title` and any visual's
  `stylePreset`.** `pbir visuals title "<Navigator>" --no-show` and
  `pbir set "<Navigator>.title.show" --value false` both fail with `Unknown component: title`,
  though `--title` on `pbir add visual` wrote one; the same commands work on a button.
  `pbir set "<Visual>.stylePreset.name" --value "Tab"` fails with `Unknown component: stylePreset`,
  though `pbir schema describe pageNavigator stylePreset` lists `name`. Set the default in the theme
  instead (`visualStyles["pageNavigator"]["*"]`, and `stylePreset` inside `"*"` picks the preset new
  visuals start with; `reports:modifying-theme-json` `references/style-presets.md`), or pick it in
  Desktop and save. (pbir 0.9.33. Verified 2026-10-29.)

  Retest: the two `pbir set` commands above on a page navigator.
- **A text box's `general.paragraphs` needs `--json`.** With `--value '<json>'` pbir stores the whole
  array as one quoted string literal; `--json '[{"textRuns":[{"value":"...","textStyle":{...}}]}]'`
  stores the array. In Windows PowerShell 5.1 the `--json` value does not survive native argument
  passing: a value with spaces splits (`Got unexpected extra argument(s)`), and escaping its double
  quotes did not help. Run that command from Git Bash. (pbir 0.9.33. Verified 2026-10-29.)

  Retest: `pbir set "<Textbox>.general.paragraphs" --value '[{"textRuns":[{"value":"a"}]}]'`, then
  read `paragraphs` in that visual.json.
- **`pbir visuals rename --to`, `pbir mv` and `pbir cp` rename the folder, not the visual.** The
  visual's `name` keeps its old value (`cp` mints a new hex one), so folder and `name` differ. pbir
  treats that as valid; the `pbip:pbir-format` skill expects them equal. To line them up, rename the
  folder to the `name` the JSON already carries. (Still on 0.9.33.)

## Visual types and properties the catalog does not know yet

A built-in visual newer than pbir's core catalog is treated like a custom visual, and only its
position can be changed. If `pbir schema roles <type>` answers `Unknown visual type`, plan for this
before promising a build. The native Gantt was one until 0.9.33.

- **The native Gantt (`ganttChart`) is supported from 0.9.33, with three catches.** Create it with
  `pbir add visual gantt <page> -d "Task:<Table>.<Column>" -d "StartDate:<Table>.<Measure>" ...`;
  `StartDate`, `EndDate` and `Progress` take measures only (a date column is refused with
  `Role 'StartDate' accepts ['Measure']`), and `pbir set`, `pbir visuals cf`, `title` and `subtitle`
  reach its objects. The catches: pbir offers a `TaskId` role that Desktop 26.10's Gantt does not
  declare, so leave it unbound; pbir adds a default sort on `StartDate` **descending**, so set
  `pbir visuals sort "<Gantt>" -f "<Table>.<Start measure>" -d Ascending` for the usual top-down
  timeline; and `bar.color` applies only once `bar.customizeColor` is true. `pbir schema describe
  ganttChart` lists only `general`, though `axis`, `bar`, `row` and the rest set fine. The wells,
  selectors and format shapes that rendered are in `pbip:pbir-format` `references/visual-json.md`,
  "Gantt Chart". (pbir 0.9.33, Desktop 26.10. CLI checked 2026-10-27; a pbir-built Gantt has not
  been rendered yet. pbir.tools #76.)

  Retest: build one with `pbir add visual gantt`, apply it in Desktop and screenshot; compare
  `pbir schema roles ganttChart` with the roles in that section.
- **`listSlicer` dropdown mode works per visual only.** Since 0.9.33,
  `pbir set "<Slicer>.data.dropdownMode" --value true` writes the visual-level shape that rendered
  (`pbip:pbir-format` "Slicer Formatting"); 0.9.32 refused it. The theme route
  (`listSlicer.*.data.dropdownMode`) is accepted, but Desktop 26.10 still drew a list.
- **`pbir visuals border --radius` on a new Card (`cardVisual`) fails** with
  `Component 'border' has no property 'radius'`: the card's own `border` object shadows the container
  one. For a tile with rounded corners, put a rounded shape behind a transparent card. (Still on
  0.9.33; pbir.tools #75.)

## Measure filters and measure-driven shape text

- **`pbir add filter` takes columns only.** A visual-level filter on a measure, such as
  `Release Count is not blank` to hide slicer items with no data, fails with
  `Filter field must be a Column, got Measure`. Set it in Desktop's Filters pane, then `pbir cp` the
  configured visual where it is needed again. (pbir 0.9.32. Verified 2026-10-19; still on 0.9.33; pbir.tools #77.)

  Retest: `pbir add filter "<Table>" "<Measure>" -v "<Visual>" --type Advanced --operator IsNotBlank`.
- **A shape's text from a measure has to go in its default-state entry.** Shapes keep their text
  styling in an `objects.text` entry with `"selector": {"id": "default"}`; `pbir set "<Shape>.text.text"`
  writes there. `pbir visuals cf "<Shape>" --measure "text.text <Table>.<Measure>"` writes the
  measure to a separate entry with no selector, and a literal `text` in the default-state entry wins,
  so the shape keeps showing the literal. This writes the measure where Desktop reads it, and it
  rendered:

  ```bash
  pbir set "<Shape>.text.default.text" --rawdog \
    --json '{"expr":{"Measure":{"Expression":{"SourceRef":{"Entity":"<Table>"}},"Property":"<Measure>"}}}'
  pbir set "<Shape>.text.default.fontColor" --rawdog \
    --json '{"solid":{"color":{"expr":{"Measure":{"Expression":{"SourceRef":{"Entity":"<Table>"}},"Property":"<Colour measure>"}}}}}'
  ```

  Without `--rawdog` the `--json` value is refused as `Expected string, got dict`. A measure added to
  the TMDL must be applied in Desktop first, or `cf` refuses it as not found in the model.
  (pbir 0.9.32, Desktop 26.10. Verified 2026-10-19.)

  Retest: bind a measure with `pbir visuals cf ... --measure "text.text ..."` on a shape cloned from
  one with literal text, then screenshot it.
- **`pbir visuals group --add` keeps the visual's page coordinates**, while the other children of a
  group are positioned relative to it. Run `pbir visuals position` on the child afterwards with
  group-relative values. (pbir 0.9.32. Verified 2026-10-19; still on 0.9.33.)
- **`pbir add filter` appends; it never replaces.** Running the same command twice leaves two
  identical filters on the visual. Read `filterConfig` before adding, or remove the extra one with
  `pbir rm "<Visual>/filter:<name>" -f`. (pbir 0.9.32. Verified 2026-10-19; still on 0.9.33; pbir.tools #74.)

  Retest: run `pbir add filter "<Table>" "<Column>" -v "<Visual>"` twice, then count the entries in
  that visual's `filterConfig.filters`.
- **Shapes have no diamond.** `shape.tileShape` refuses `diamond`. For a milestone-style legend
  marker, set `shape.tileShape` to `rectangle` and `rotation.shapeAngle` to `45`. A
  `rectangleRoundedByPixel` swatch about 22x10 px drew as an oval, so legend swatches want
  `rectangle` too. (pbir 0.9.32, Desktop 26.10. Verified 2026-10-19; `diamond` still refused on
  0.9.33.)

  Retest: `pbir set "<Shape>.shape.tileShape" --value diamond`.
- **A `rectangleRoundedByPixel` shape takes its radius from `shape.rectangleRoundedCurve`**
  ("Rounded corners"), not `shape.roundEdge`. With only `roundEdge` set, values from 2 to 16 all drew
  the same corners of about 15 px. Set the radius with
  `pbir set "<Shape>.shape.rectangleRoundedCurve" --value 9`. (pbir 0.9.32, Desktop 26.10. Verified
  2026-10-19.)

  Retest: set `roundEdge` to 2 on one rounded-by-pixel shape and 16 on another, then screenshot.
- **`pbir visuals action --type PageNavigation --target` writes the target as given.** Desktop
  navigates by the page's `name` (its folder under `definition/pages`), so a display name such as
  `"Release anatomy"` is accepted, validates, and does nothing when clicked. Pass the page's folder
  name, and check that every `navigationSection` matches a page folder. (pbir 0.9.32, Desktop 26.10.
  Verified 2026-10-19.)

  Retest: `pbir visuals action "<Visual>" --type PageNavigation --target "<display name>"`, then
  `pbir visuals action "<Visual>" --show`.

## Bookmarks on a copied page

`pbir cp` copies a page without its bookmarks, and a copied bookmark cannot be pointed at the new
page. `pbir cp "<Report>.Report/bookmark:<name>" "<Report>.Report/bookmark:<new>"` copies one, and
`pbir bookmarks page <report> <bookmark> <page>` then rewrites only `explorationState.activeSection`:
the visual states stay keyed under the source page in `explorationState.sections`, so the bookmark
opens the new page and changes nothing on it. pbir also has no command that puts a bookmark in a
group, which a bookmark navigator reads. A per-page show/hide panel driven by bookmarks therefore
needs its bookmarks made in Desktop on each page (or, where the user allows hand edits, a copy of the
bookmark file with the section key renamed and the group added to `bookmarks.json`).
(pbir 0.9.32. Verified 2026-10-19.)

Retest: copy a bookmark, run `pbir bookmarks page` on it, and read the copy's `sections` keys.

**A copied page's visuals have new names.** `pbir cp` of a page keeps each visual's folder name but
writes a new `name` inside its `visual.json`. pbir paths resolve the folder, while Desktop, bookmarks
(`targetVisualNames`, the `sections` keys) and `parentGroupName` use the inner name. Anything that
refers to a visual from outside pbir must read the `name` field, not the folder. (pbir 0.9.32.
Verified 2026-10-19.)

Retest: `pbir cp` a page, then compare a copied visual's folder name with the `name` in its
`visual.json`.

## `pbir model -q`

**`-F json` fails on any date value** with `Error: Object of type datetime is not JSON serializable`,
whatever the query. Format dates in the query (`FORMAT ( [Start], "yyyy-mm-dd" )`, or `"" & [Measure]`
to stringify every column), or use the default table output. (pbir 0.9.32 and 0.9.33, also with `--json` and
`--output-format json`. Verified 2026-10-27; pbir.tools #78.)

Retest: `pbir model "<Report>.Report" -F json -q "EVALUATE ROW(\"d\", TODAY())"`.

## Publishing

**`pbir publish` on a thick project failed with a bare "Publishing failed".** It publishes the report
only. Import the semantic model first and then a byConnection copy of the report with `fab import`:
`fabric-cli:fabric-cli` `references/import-download-deploy.md`, "Publishing a report over an
API-imported model". The `Fabric CLI: status unavailable` line in pbir's banner was a cosmetic parsing
quirk; `fab` itself was authenticated.

After importing an Import-mode model through the API, run a Service refresh before checking any
visual, then verify with `executeQueries` DAX.

## Checking numbers against Desktop's own exports

A visual's **Export data** includes measures bound only through the Analytics pane, such as an error
bar's upper and lower bounds; **Show as a table** does not show them. When comparing a visual's
numbers with a DAX query, use Export data, or the bound columns go missing from the comparison
(Desktop 2.157.1354.0, September 2026). The UI Automation route to both is in `pbi-desktop:connect-pbid`
`references/desktop-ui-automation.md`.

## Testing pbir itself

To try a command without touching the real configuration, point `PBIR_CONFIG` at a throwaway file
**and** run `pbir connect` only from a scratch directory: `PBIR_CONFIG` redirects the config file but
not the `.pbir/active` marker, which `pbir connect` writes in whatever directory it runs from.
