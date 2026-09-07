# Validating PBIR conformance

PBIR is conformant when it passes every dimension below, not just JSON schema. Prefer
`pbir validate` (it checks all of these at once); when editing JSON directly, hand-author
to these rules.

## Validate with the CLI

```bash
pbir validate "Report.Report"            # structure + schema
pbir validate "Report.Report" --all      # + fields + QA + semantic
pbir validate "Report.Report" --fields   # + field references resolve in the model
pbir validate "Report.Report" --qa       # + quality rules (overlap, hidden, filters, counts, layout, role cardinality)
pbir validate "Report.Report" --semantic # + visual type ids / objects / vCO names vs the core visual catalog
pbir validate "Report.Report" --strict   # promote field/QA/semantic warnings to errors
pbir validate "Report.Report" --json     # machine-readable
```

The same checks run implicitly on every `pbir` mutation. To bypass a check deliberately,
use the global flag before the subcommand: `--skip <category>` (repeatable,
comma-separated) or `--rawdog` (skip all). Categories: `structure`, `schema`,
`schema-version`, `fields`, `enums`, `qa`, `roles`, `layout`, `theme`.

## The conformance dimensions

- **structure** -- folder layout matches the PBIR tree and required files are present (version.json, report.json, pages/pages.json, each page.json, each visual.json).
- **schema** -- each file validates against its `$schema`, and the `$schema` URL is well-formed and points at a known version.
- **schema-version** -- parent and embedded schema versions form a compatible set; do not mix versions across the report (see `schemas.md`).
- **required fields** -- per file type:
  - `definition.pbir`: `$schema`, `version`, `datasetReference` (with `byPath` or `byConnection`)
  - `version.json`: `$schema`, `version`
  - `report.json`: `$schema`, `themeCollection`
  - `pages/pages.json`: `$schema`, `pageOrder`
  - `page.json`: `$schema`, `name`, `displayName`, `displayOption`
  - `visual.json`: `$schema`, `name`, `position`, and one of `visual` or `visualGroup`
- **name + id** -- every `name` matches `[a-zA-Z0-9_][a-zA-Z0-9_-]*` (no spaces, no leading hyphen), is unique among siblings, and matches its folder name. Spaces in page/visual folder names deploy but do not render.
- **fields** -- every field reference (Entity/Property, queryRef, filter, sort, conditional formatting) resolves to a real table/column/measure of the right kind in the connected model. Discover with `pbir fields list` and `pbir model`.
- **enums** -- enumerated properties use allowed values only (see `enumerations.md`); discover allowed values with `pbir schema describe <type> <object>`.
- **roles** -- data roles bound on a visual exist for that visual type and respect cardinality (single vs multiple). Discover with `pbir schema roles <type>`.
- **qa** -- quality heuristics: visuals on-canvas and non-overlapping, no stray hidden visuals, sane field counts, layout and role-cardinality checks.
- **layout** -- positions sit within the page canvas and sizes are non-negative.
- **theme** -- theme JSON is structurally valid and referenced colors and text classes resolve.
- **semantic** -- `visualType` ids, per-type `objects` names, and the 15 `visualContainerObjects` names match the core visual catalog the CLI bundles (advisory; custom visuals use arbitrary ids). See `visual-container-formatting.md`.

## Discover and audit before authoring

- `pbir schema describe <type>` then `pbir schema describe <type> <object>` -- valid objects, properties, allowed values, and ranges for a visual type.
- `pbir schema roles <type>` -- the canonical data roles a visual type accepts.
- `pbir color list "Report.Report"` -- every hard-coded color literal and where it is used (audit before re-coloring).
- `pbir fonts list "Report.Report"` -- font families, sizes, and weights across the report and theme.

## What a clean validate does not prove

`pbir validate` is a schema and reference checker. Power BI Desktop and the Power BI service both
reject, or silently mis-render, things it passes. Every row below validates clean:

| Passes `pbir validate` | What actually happens | Rule |
|---|---|---|
| a UTF-8 BOM on any PBIR or TMDL file | Desktop opens with an "Issues were found" dialog, the title reverts to "Untitled - Power BI Desktop", and the model loads empty | below |
| duplicate `filterConfig` filter `name` values across pages | the same dialog and the same empty model | [page.md](./page.md), "Cloning a page or a visual" |
| an extension-measure reference with no `"Schema": "extension"` | the published report errors per visual with `Missing_References` | [measures.md](./measures.md), "Every reference needs the tag, sorts included" |
| a format property nested inside `show` instead of beside it | the setting does nothing at all | [visual-container-formatting.md](./visual-container-formatting.md), "What Goes Wrong" |
| a `cardVisual` `value` entry with no `"selector": {"id": "default"}` | the card renders at its default size and overflows | [schema-patterns/selectors.md](./schema-patterns/selectors.md), "A state-based visual ignores a property with no selector" |
| `active: true` on a `tableEx` projection | Desktop renders that one column and drops every later one | [visual-json.md](./visual-json.md), "`active` by visual type" |
| `active` missing from a `pivotTable` row level | the matrix collapses to one column with expanders | the same section |
| a slicer's `mode` set on `general` instead of `data` | the slicer stays a vertical list | [visual-json.md](./visual-json.md), "Slicer Formatting" |
| `axisTitle` in place of `titleText` | the axis title falls back to a concatenation of every measure on that axis | [visual-json.md](./visual-json.md), "Axis Titles" |
| a malformed dynamic text run in a textbox | the run renders as literal text | [textbox.md](./textbox.md) |

### Never write a UTF-8 BOM into PBIR or TMDL

A single `EF BB BF` at the head of `pages.json` made Desktop open with an "Issues were found"
dialog, the title bar revert to "Untitled - Power BI Desktop", and the model load empty. That is the
same symptom duplicate filter names produce, so it is easy to misdiagnose as model corruption.
`pbir validate --fields --qa` passed clean on the BOM'd file; only Desktop caught it.
Verified 2026-08-25.

The usual advice to pass `-Encoding utf8` is **inverted** here: Windows PowerShell 5.1's
`Set-Content -Encoding utf8` emits a BOM. Write PBIR and TMDL from Python
(`path.write_text(..., encoding="utf-8")` emits none), or use `-Encoding utf8NoBOM` on PowerShell 7
and later.

Retest: `Set-Content t.json -Encoding utf8 -Value '{}'; head -c 3 t.json | xxd`. `efbbbf` means that
shell still writes a BOM; anything else means it does not. The Python route is safe either way.

Cheap check after any PowerShell touch, over both extensions:

```bash
head -c 3 file.json | xxd          # efbbbf means a BOM is present
```

Sweeping a whole project, PBIR and TMDL together:

```bash
python - <<'PY'
import pathlib
for p in pathlib.Path(".").rglob("*"):
    if p.is_file() and p.suffix.lower() in {".json", ".tmdl", ".pbir", ".pbip"}:
        if p.read_bytes()[:3] == b"\xef\xbb\xbf":
            print("BOM:", p)
PY
```

## Verify rendering: the first open is part of the change

JSON conformance does not guarantee a visual renders, so treat the first Desktop or service open
after a hand edit as part of the change rather than as a follow-up, and budget for it.

- **Desktop is running:** reload and screenshot the open instance and inspect the PNG; see
  `desktop-bridge.md`, or the `reports:pbi-verify-loop` skill, which captures until two consecutive
  screenshots match instead of guessing a sleep.
- **No Desktop (a Linux session, a container, CI):** publish and render server-side. Export the
  report to PDF through the Power BI REST API, then rasterize the PDF. The recipe is in
  `fabric-cli:fabric-cli`, `references/reports.md`. This is also the only route that exercises the
  service's reference resolution, which is what surfaces the `Missing_References` failure above.
