---
name: organize-semantic-model
version: 26.40.3
description: Organize a Power BI or Analysis Services semantic model end to end so it is ready for report authors, Excel users and Copilot - table groups, display folders, Title Case business names and naming conventions, hierarchies, sort-by columns, hiding, Analyze in Excel (IsAvailableInMDX), descriptions, format strings, data categories, context annotations, DAX formatting and UDFs, calculated-object justification, duplicate removal, perspectives, translations and security roles. Use whenever the user asks to "organize", "tidy", "clean up", "polish", "prepare", "standardize" or "make report-ready" a model or one table in it (for example "organize the date table"), to "fix naming conventions", "rename fields", "make names human readable" or "fix abbreviations", even when they name only one of these aspects, and whenever a model is driven through the Tabular Editor 3 MCP or the te CLI for that purpose. Not for DAX performance tuning (dax-optimisation skill) or model design and star-schema changes (semantic-model skill).
---

# Organize a semantic model

[Workflow] Organizing is a set of passes over the same objects. Doing only one or two of them (folders and sorting, say) leaves the model looking finished while names, descriptions and formats are still raw, so run every pass unless the user narrows the scope, and say which passes were skipped and why.

## Tooling

- Tabular Editor 3 MCP: call `get_workspace_info` first and confirm the model title with the user if it is not the one they named. Read with `get_model_overview` and `get_object_details`; write with `execute_csharp_script`
- `te` CLI (the `te-cli` skill) when there is no TE3 instance, for example against PBIP/TMDL on disk
- One script per pass. Each `execute_csharp_script` call is one undo step and returns a property-level diff, so per-pass scripts keep every change reviewable and individually revertible
- Read the returned diff after every script. Confirm each property you meant to set appears, and nothing you did not mean to touch. A property missing from the diff was already at that value, except annotations: the diff does not list annotation changes (`TableGroup`, `context`), so read those back with a second script
- `execute_dax_query` only exists while the TE3 MCP server has model data read permission. If it disappears mid-session, the client's tool list is stale; reconnect the server (`/mcp`). A calculated table that was never recalculated returns no data until it is refreshed
- Ask the user to close TE3 DAX editor tabs for objects a script will change. A script that edits an object while its editor is open and parsing has crashed TE3 (`IndexOutOfRangeException` in `ScrollbarIndicatorsController`)
- Nothing is saved or deployed by the MCP. On a live connection, saving writes to the server, so leave saving to the user

## Pass 0: inventory and lineage

Before changing anything:

1. Record the starting state: tables, columns, measures, functions, existing display folders, table groups, hierarchies, cultures, perspectives, roles and annotations
2. Find downstream consumers with the `lineage-analysis` skill (or `fab` through the `fabric-cli` skill): reports bound to the model in every workspace, and composite models on top of it. Renames, deletions and the Analyze in Excel pass all depend on this
3. Note the cultures. Some TE operations write translated captions automatically (adding a hierarchy does), and renames leave existing translations pointing at the new object

## Pass 1: table groups and display folders

- Table groups: set `table.TableGroup` (stored as the `TabularEditor_TableGroup` annotation). Use role-based groups such as `Facts`, `Dimensions`, `Measures`, `Calculation Groups`, `Parameters`. Groups only show in Tabular Editor; they do not reach Power BI, which is why table names must not carry `DIM_`/`FACT_` prefixes instead
- Display folders: put every visible column and measure in a folder. Aim for 3 to 5 top-level folders per table. More than 5 means the table mixes subjects or the folders are too fine. Keep a larger existing structure if it predates the session; do not flatten the user's own work
- Nest with `/` only (`Keys/Technical`); one level is usually enough
- Folders on hidden objects are invisible to users. Set them so a later unhide lands somewhere sensible, but do not spend top-level folders on them

## Pass 2: names

Title Case business names for tables, columns, measures and hierarchies (`Order Date`, `Net Sales`, `Days of Supply`), acronyms in capitals, no programming conventions, no technical prefixes, no unexplained abbreviations, and one consistent syntax for aggregations, units, periods and comparisons. The full rule set, the measure name construction order and the terminology questions to ask first are in `references/naming-rules.md`.

- Conformed nomenclature: one concept, one word, everywhere. `Customer Key`, `Customer`, `Cust` for the same thing across tables collapse to one form; qualifiers that carry meaning (`Billing Date`, `Order Date`) stay. Pick singular or plural table names once
- Calculated table columns bind to the expression's output through `SourceColumn`. Renaming the column object is enough while `SourceColumn` still matches an expression column; when the expression's names change, keep `SourceColumn` in step or the column is dropped on recalculation
- Renaming in Tabular Editor carries relationships, sort-by columns, hierarchy levels, translations and perspective membership along, and renames a calculated table's partition with the table
- Before renaming, show the user the old-to-new map and warn that renames break report visuals, filters, bookmarks and field parameters bound to the old names. Pass 0 found the consumers; offer to rebind them with the `pbir-cli` skill (local PBIR) or `fabric-cli` (service). Do not apply renames to a model with bound reports without that go-ahead. `refactoring-renaming.md` in the `semantic-model` skill has the full procedure

## Pass 3: hierarchies

Add the natural drill paths: calendar (Year > Quarter > Month > Date), fiscal calendar if one exists, geography (Country > Region > City), product (Category > Subcategory > Product), organization. Skip a hierarchy whose levels are not truly nested.

## Pass 4: sort order

Every text column with a non-alphabetical natural order gets a `SortByColumn`: month names by month number, month labels (`Mar 2025`) by a year-month key, weekday names by weekday number, statuses and buckets by an explicit order column. The sort key must have exactly one value per sort value, or refresh fails.

## Pass 5: hiding

Hide what report authors should not drag into a visual: surrogate and foreign keys, sort keys, technical columns, and numeric fact columns meant to be aggregated only through a measure (hide them and make sure the measure exists). Hide tables that only support relationships or measures. Do not hide a column a hierarchy or visible slicer needs.

## Pass 6: Analyze in Excel

`IsAvailableInMDX = false` removes a column's attribute hierarchy: less processing and memory, and the column disappears from Excel PivotTables and other MDX clients.

- Candidates are the TE3 BPA rule `TE3_BUILT_IN_SET_ISAVAILABLEINMDX_FALSE`: hidden columns not used for sorting, in hierarchies, variations or calendars, without a sort-by column of their own, and not in a Direct Lake table. Run it with `get_bpa_rule_results`
- Excel usage does not show up as a bound report. Check connected Excel workbooks in the lineage results and, with admin access, `AnalyzedByExternalApplication` events in the activity log. If Excel or other MDX use exists, tell the user which columns it would affect instead of disabling them silently

## Pass 7: descriptions

Every visible table, column, measure, hierarchy and function gets a description unless the name and metadata already say everything. As few words as possible, as many as necessary: only what the name does not already say (format, an example value, grain, exclusions, unit or currency, an acronym spelled out, what a measure aggregates). Never restate what the metadata already shows: the name, object type, table, source column, data type, format string, sort-by column, hierarchy levels, relationships or calculated status. A description or annotation that adds nothing beyond those stays empty.

Write descriptions and `context` annotations about 80% of the way to ASD-STE100 Simplified Technical English: short sentences, one fact per sentence, simple common words, active voice and present tense, no Latin abbreviations (`Example:`, not `e.g.`). Leave field names, product names, codes and format patterns as they are. In descriptions, put two or more facts on separate lines as `- ` bullets; one fact stays a single line.

- `Month Label`: "Example: Mar 2025"
- `Month Sort`: "- Format: YYYYMM\n- Example: 202503"
- `Net Sales`: "Invoice value after discounts and returns.\n- Local currency\n- Does not include freight or taxes"

## Pass 8: format strings

Format every visible measure and numeric column: separators, currency, percentage, decimals that match the data. Use a format string expression (`FormatStringDefinition`) when the format depends on context, such as the selected currency. Date formats are case-sensitive: `MM` is month and `mm` is minutes, so `yyyy-MM-dd`, never `yyyy-mm-dd`.

## Pass 9: data categories

Set `DataCategory` where it changes client behavior: geography (`Country`, `StateOrProvince`, `City`, `PostalCode`, `County`, `Continent`, `Latitude`, `Longitude`, `Place`), `WebUrl`, `ImageUrl`, `Barcode`. The date table gets table-level `DataCategory = "Time"` and its date column `IsKey = true`.

## Pass 10: context annotation

Add an annotation named `context` (`obj.SetAnnotation("context", "...")`) to objects whose purpose neither a reader nor the metadata reveals: role-playing keys, helper tables, columns that exist for RLS or a calculation group, disconnected parameter tables, anything kept for a downstream dependency. A sort key needs none; `SortByColumn` already says what it sorts. A few words in the pass 7 style on why it exists, for example "Kept for the Finance export; not used in reports."

## Pass 11: calculated tables and columns

Each DAX calculated table and calculated column must justify itself in its `context` annotation, in one short sentence: why it is calculated in the model, why it must exist, and why it cannot come from the source (for example: derived from several fact tables at refresh time, depends on model relationships, or the source is a read-only view). If no reason holds, recommend moving it upstream rather than inventing one.

## Pass 12: DAX code

Every DAX expression in the model follows the `dax-standard` skill, the house style. Load it before this pass. Where TE3's formatter or its code actions disagree with `dax-standard`, `dax-standard` wins.

- Lay out every measure, calculated column, calculated table, calculation item and function expression in the house layout: the body starts on the second line (in TMDL, a blank line right after `=`), one `VAR`, function or argument per line, one flat list of `VAR`s, and the last step is `VAR __Result` with `RETURN __Result`. Do not run `obj.FormatDax()`: it applies DAX Formatter's layout, not the house layout
- Prefix every variable with `__` (`VAR __StartDate`) and every temporary column created by `ADDCOLUMNS`, `ROW`, `SELECTCOLUMNS` or `SUMMARIZECOLUMNS` with `@` (`"@BusinessDate"`, referenced as `[@BusinessDate]`), so neither can be mistaken for a model table or column
- Put a `//` line before each step that says what it does, inside the expression, as `dax-standard` does. Keep the `///` description separate
- Apply TE3's code actions by hand, but only where they keep the table-first shape. The editor shows them (DR001 to DR014, RW001 to RW003 on docs.tabulareditor.com/en/features/code-actions.html), but the MCP exposes neither the actions nor their lint markers, so an agent has to check for them. Apply: `VALUES` instead of single-column `SUMMARIZE`, `DISTINCTCOUNT`, `COALESCE`, `ISBLANK`, `IN` instead of chained `||` equalities, constant aggregations moved into variables, no unused variables, and a plain aggregator for a single-column iterator over a model table (`SUMX ( Sales, Sales[Amount] )` becomes `SUM ( Sales[Amount] )`). Do not apply: a scalar predicate in place of a `FILTER` that builds a table `VAR`, or anything that folds a table `VAR` away. The table `VAR` is the step that can be returned and inspected
- Layout, prefixes and comments change no result. Restructuring a measure into the table-first shape, or flattening nested `VAR` blocks, can. Propose those per measure, and prove each with the comparison query under "Keep the VARs flat" in `dax-standard`. Time intelligence keeps `CALCULATE` with `DATEADD` (the standing exception in `dax-standard`)

## Pass 13: user-defined functions

Look for logic repeated across measures that one UDF could carry, propose it with the measures it replaces, and on approval create it with a compound name, type hints, and `///` plus parameter comments. Syntax, naming, documentation layers and worked examples are in `references/udfs.md`.

The `dax-standard` house style holds here too:

- A function body is laid out like a measure: `__` variables, one flat list of `VAR`s, a `//` line per step, and `RETURN __Result`
- Formatting logic goes in one `Fmt.*` function per convention (scaled, currency, percent, duration), called from each measure's `formatStringDefinition`, as `dax-standard` describes under "Number formatting"
- A measure moved onto a UDF keeps its `VAR`s flat. Never pass a `VAR … RETURN` block as an `EXPR` argument; give the wrapper a table twin instead, as "Keep the VARs flat" in `dax-standard` shows
- Before one function calls another, read the UDF load traps in `pbip:tmdl` `references/authoring-gotchas.md`. After any function change, run `EVALUATE INFO.USERDEFINEDFUNCTIONS()` and read `ErrorMessage`; `te validate` passing is not enough

## Pass 14: duplicates

A field that duplicates another (same values under a different name, a second copy of a key, an unused measure that repeats another's logic) can be deleted only if nothing uses it: no model dependency (`ReferencedBy` empty), no RLS or perspective reliance, and no report, Excel workbook or composite model in the pass 0 lineage. List deletions for the user before applying them.

## Pass 15: perspectives, translations and roles

- Perspectives: every perspective's membership is deliberate and current. New objects are excluded from existing perspectives by default, so add what belongs, and include the columns a visible measure needs
- Translations: every culture covers every visible table, column, measure, hierarchy and display folder, with captions and descriptions. A partial culture shows users a mix of languages; report the gaps and fill them where the user can supply or approve the wording
- Roles: if security roles exist, each has its table permissions and filter expressions set, members assigned where the model defines them, and object-level security consistent with what pass 5 hid. Do not create or loosen security without the user

## Finish

1. Run the BPA (`get_bpa_rule_results`) and fix what the passes introduced
2. Run a small DAX query per changed table (`execute_dax_query`) to confirm sorting, formats and hierarchies behave
3. Report per pass: what changed, what was already right, what was skipped and why, every rename and deletion with its downstream impact
4. Tell the user the model is not saved, and that undo in TE3 is one Ctrl+Z per script
