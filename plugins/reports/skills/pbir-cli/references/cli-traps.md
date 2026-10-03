# pbir CLI traps

Commands that exit 0 and did something other than what was asked, or that report a fault that is not
there. The relative-path hijack by an active connection is the biggest of these and lives in
[cli-reference.md](./cli-reference.md), "Report Creation and Management"; this file carries the rest.

Every item was observed on pbir 0.9.x under Windows between July and October 2026. Before relying
on one, run the command's `--help` and check whether a newer release changed it.

## `pbir desktop`

**`pbir desktop screenshot <report>` renders the first page whatever page you pass.** Handing it one
page path (or a `page.json`) does not switch pages, so a per-page sweep built on it silently
captures page one every time. Use `--all` and take the file you want, or select the page tab first
through UI Automation (`pbi-desktop:connect-pbid` `references/desktop-ui-automation.md`), which works
on a background window.

Retest: `pbir desktop screenshot "<Report>.Report/<second page>.Page" -o p2.png` on a report whose
pages look different, and compare `p2.png` with page one.

**`pbir desktop list` truncates the Open File column with an ellipsis.** A project deep in a tree
shows as `...\.scratch\report-ha…`, so the report's own name is never in the output, and a wait loop
that greps for it hangs until its timeout instead of failing:

```bash
# Never matches. Runs until the timeout, whatever Desktop is doing.
until pbir desktop list | grep -qi "MyReport"; do sleep 3; done
```

Wait on something the table does print, such as the PID, and do not anchor the pattern to the start
of the line: the table is drawn with box-drawing characters, three bytes each in UTF-8, so `^. ` in a
byte-oriented grep never fires.

```bash
until pbir desktop list 2>/dev/null | grep -qE '[0-9]{4,6}'; do sleep 3; done
```

**A row in that table means Desktop has a window, not that the report has loaded.** A screenshot
fired the moment the row appeared failed with
`application.state.get/v1: Another operation is already in progress`. Retry the operation you
actually want in a loop instead of waiting on the list and firing once. There is no `--json` or
`--no-truncate` on `list` to lean on.

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
  own `filterConfig`.
- **`pbir add page "<Report>.Report/<Folder>.Page" -n "<Display>"` also creates a default title
  textbox** (folder `Title`). Remove it when the page gets its own header. The page folder on disk is
  a hash, not the path segment you typed.
- **pbir addresses pages and visuals by display name** (`"<Report>/Opening Tooltip.Page"`), not by
  the hash folder. A glob through a page path that contains spaces (`".../Opening Tooltip.Page/*.Visual"`)
  matched no visuals; operate per visual instead.
- **`pbir set ...visualTooltip.*` fails on a custom visual** with `Unknown component: visualTooltip`,
  because custom visuals are not in the core catalog. Edit the visual.json directly
  (`pbip:pbir-format` `references/page.md`, Tooltip Pages). `pbir pages set-tooltip` sets the page's
  `type` and `displayOption`; set `visibility` to `HiddenInViewMode` separately.
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
  Verified 2026-10-03.)

  Retest: `pbir visuals title "<Visual>" --text "It's"`, then read the `title` entry in that
  visual.json.

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
