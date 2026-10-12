# Reviewing Manual Power BI Edits

Use this when a user changes a published report in Power BI and asks what the
CLI or skill can learn from it.

## Safe pull-down workflow

1. Download with `pbir download` into a new temporary directory. Do not overwrite the agent's prior
   working copy before the comparison is complete.
2. Validate the downloaded report and record its page, visual, field, warning,
   and declared-schema counts.
3. Compare page order, positions, visual types, field bindings, filters,
   extension-measure expressions, resources, and **effective formatting**.
4. Use `pbir visuals format --json` for formatting comparisons. It merges theme
   and local layers and identifies the source of each value; raw JSON diffs are
   too noisy for this job.
5. Classify every difference as renderer-relevant, semantic, service metadata,
   or serialization noise before changing anything.
6. Reproduce each renderer-relevant difference with `pbir set ... --dry-run` or
   a dedicated command. If `pbir` rejects a value that Desktop wrote and
   renders, report it as a CLI defect with the property path and value; do not
   work around it by editing JSON.
7. Only after the review, make the downloaded copy the working baseline or
   replace the earlier copy through a recoverable backup workflow.

## Common round-trip noise

- `.platform` display names and other service-owned metadata
- Base theme rewrites and key ordering
- Visual schema URL/version advances
- Literal escaping in custom format strings
- Equivalent selector/order canonicalization

Do not call these user design changes without renderer or semantic evidence.
Normalize format-string escaping before comparing meaning.

Power BI Desktop can declare a visual schema version before that schema is
available from Microsoft's public schema endpoint. Preserve the declared
version, report degraded validation clearly, and do not downgrade solely to
silence a warning.

## New Card (`cardVisual`) lessons

The New Card has separate alignment controls for the card's content flow and
for the image within its area:

- `layout.alignment = top` lifts the whole callout/image/reference-label group.
- `image.verticalAlignment = middle` centers the icon beside the callout.
- Moving the icon with `image.verticalAlignment` alone can make it look too high
  or too low while leaving the group itself misplaced.

New Card objects are frequently selector-scoped. Prefer plain paths on a current
CLI, which route known objects to Desktop's expected selector. If a write reads
back but does not render, compare the selector shape in the manual report before
adding a one-off path or helper.

## Table width modes

Treat the two native table width behaviors as distinct:

- `--stretch-columns`: `autoSizeColumnWidth=false`,
  `columnAdjustment=growToFit`
- `--fit-columns-to-content`: `autoSizeColumnWidth=true`,
  `columnAdjustment=fitToContent`

Use the mode the design requires; they are mutually exclusive. Remove stale
`customColumnWidth` overrides when switching modes.

## Resource cleanup signal

Service/Desktop round trips may remove unreferenced registered resources. After
clearing a page or theme background image, audit `RegisteredResources` for
orphaned assets. Do not delete an asset merely because its filename is absent
from obvious page properties; bookmarks and less-common configuration paths
must also be checked. Remove a confirmed orphan explicitly with
`pbir rm "Report.Report" --image <item_name> -f`, never as a side effect of
another change.
