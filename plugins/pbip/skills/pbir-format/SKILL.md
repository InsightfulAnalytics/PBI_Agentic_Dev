---
name: pbir-format
version: 26.26
description: Format reference for Power BI Enhanced Report (PBIR) JSON schemas and patterns. Automatically invoke on any PBIR metadata format question (visual.json properties, extension measures, themes, page structure) and on the symptoms hand-authored PBIR produces, a formatting change that did nothing, a visual that renders empty or shows only its first column, an Issues were found dialog, or Missing_References after publishing.
---

# PBIR Format Reference

Skill that teaches Claude about the Power BI Enhanced Report (PBIR) JSON format to read and use it. Doesn't support legacy `report.json` or `layout` report metadata. To convert from legacy to PBIR format, users have to open and save their reports in Power BI Desktop.

Follow within reason the [mental model](./important/MENTAL-MODEL.md) when working with reports.

**WARNING:** The PBIR format is brittle and easily corrupted. Direct JSON file modification can lead to corruption. Prefer using the `pbir` CLI tool if available (`uv tool install pbir-cli` or `pip install pbir-cli`, macOS and Windows only; there is no Linux build), as it has built-in safeguards against breaking report files. Only fall back to direct JSON modification if the user explicitly requests it or if `pbir` is not available.

## General, critical guidance

- **Check examples:** Check [examples](./examples/) for a valid report
- **Take a backup:** Make a copy of the report before modifying it
- **PBIX vs PBIP vs PBIR:** So long as report metadata is in PBIR format, any of these formats works. PBIX is just a zip file; unzip and rezip to work with it. Do not work with PBIT (Power BI Template) file types. Note that PBIP and PBIX contain PBIR, but a "thin" report can be PBIR only.
- **Valid JSON vs. Rendering JSON:** Valid JSON does not guarantee rendering. A visual might not render if the bound field is invalid (missing, wrong table, or misspelled) in the visual.json, if the visual elements are cropped by their container, if a model performance issue causes the dax query to time out, if a model data quality issue results in (Blank) or empty values, etc. Check whether a visual rendered using tools like the chrome or chrome devTools MCP server if the report was published to Power BI, but it's often faster to just ask the user to check in Power BI Desktop or the browser. Where there is no user and no Desktop (a Linux session, a container, CI), publish and render server-side with the `ExportTo` REST API rather than calling the edit done on a green validate; the recipe is in `fabric-cli:fabric-cli`, `references/reports.md`.
- **A clean `pbir validate` is necessary, not sufficient:** it is a schema and reference checker. A UTF-8 BOM, duplicate filter names across pages, a missing `"Schema": "extension"`, a format property nested inside `show`, and `active: true` on a `tableEx` projection all pass it and all break the report. The enumerated list is in [validation.md](./references/validation.md); treat the first Desktop or service open after a hand edit as part of the change.
- **Never write a UTF-8 BOM:** it breaks Desktop file-open for PBIR and TMDL alike, with an "Issues were found" dialog, the title reverting to "Untitled - Power BI Desktop", and an empty model. Windows PowerShell 5.1's `Set-Content -Encoding utf8` emits one, so the usual advice is inverted here: write from Python, or use `-Encoding utf8NoBOM` on PowerShell 7 and later. Check with `head -c 3 file.json | xxd`.
- **Hierarchical formatting cascade:** In Power BI reports, formatting is determined by the following order of operations: defaults --> Theme wildcards (*) --> Theme visualTypes --> bespoke visual.json configuration. Theme overwrites defaults, visualType overrides wildcards in themes, and visual.json overrides all theme formatting. Prefer putting as much of the formatting in the theme as possible over bespoke visual.json formatting because then changes only need to happen in one place
- **PBIR files are strict JSON:** No comments allowed. Every PBIR schema is also `additionalProperties: false`, so an invented or misplaced key breaks Desktop file-open instead of being ignored; see [schemas.md](./references/schemas.md)
- **DON'T MAKE ASSUMPTIONS:** Check the Microsoft documentation and other reputable resources for context if needed, or ask the user.

## Report Structure

```
Report.Report/
+-- .pbi/localSettings.json                # Local-only, gitignored
+-- .platform                              # Fabric Git integration
+-- definition.pbir                        # Semantic model connection (byPath or byConnection) can open this file in Power BI Desktop to open the report
+-- mobileState.json                       # PBIR-Legacy artifact only; current PBIR stores phone layout per-visual in mobile.json
+-- semanticModelDiagramLayout.json        # Model diagrams
+-- CustomVisuals/                         # Private custom visuals only
+-- definition/
|   +-- version.json                       # REQUIRED -- PBIR version
|   +-- report.json                        # REQUIRED -- report-level config, including theme, report filters, settings
|   +-- reportExtensions.json              # Extension measures and visual calculations (report- and visual-level DAX)
|   +-- pages/
|   |   +-- pages.json                     # Page order, active page
|   |   +-- [PageName]/                    # Power BI Desktop may generate names with spaces; recommend no spaces for human-authored names
|   |       +-- page.json                  # Page-level properties, including size, background, filters
|   |       +-- visuals/
|   |           +-- [VisualName]/
|   |               +-- visual.json        # Visual config, formatting, and field data bindings <-- most important and complex file for report dev and formatting
|   |               +-- mobile.json        # Mobile formatting of the visual (niche)
|   +-- bookmarks/                         # Bookmarks are a bad practice and should be avoided if possible!
|       +-- bookmarks.json                 # Bookmark order and groups
|       +-- [id].bookmark.json             # Individual bookmark state containing a snapshot of the report basically
+-- StaticResources/
    +-- RegisteredResources/               # Custom themes, images
        +-- [ThemeName].json               # Custom theme <-- second most important and complex file for formatting
    +-- SharedResources/BaseThemes/        # Microsoft base themes
```


## Rules

Follow within reason the [mental model](./important/MENTAL-MODEL.md) when reviewing or providing feedback on reports.

### Modifying a report

1. Understand the user's request. Ask questions if necessary to clarify the business context -- focus on the business process, the users, and the model
2. Explore the report efficiently to locate relevant pages and visuals
3. Check the connected semantic model. For thin reports (`byConnection`), use `fab`, `pbir`, or `te` CLI tools to explore the model. For `byPath`, connect to the local model in Power BI Desktop. Understanding the model reveals available fields and calculation logic
4. Identify the appropriate visuals and pages to modify. Ask the user for clarification if needed
5. Plan modifications with the correct PBIR structure and property values

### Creating a report

1. Same workflow as modifying, except files are generated from scratch. Use `pbir new` if the `pbir` CLI is available; otherwise, check the example reports thoroughly
2. Ensure `definition.pbir` is configured properly (byPath or byConnection)
3. Use a theme.json file. Recommended: [the SQLBI/Data Goblins theme](./examples/K201-MonthSlicer.Report/StaticResources/RegisteredResources/SqlbiDataGoblinTheme.json)
4. Add appropriate filters to `report.json` or `page.json`; see [filter pane reference](references/filter-pane.md)

### Additional validation

For detailed report design guidance (layout, spacing, visual hierarchy, color, accessibility), see the **`pbi-report-design`** skill. Key rules enforced during validation:

- Use a custom theme; push formatting to the theme over bespoke visual.json unless the user specifies otherwise
- Visuals must not overlap; maintain equal spacing between visuals and page edges
- Every page needs a title (textbox or background image). Ensure textboxes are tall enough to render (24-28 pt)
- Follow the 3-30-300 rule: KPIs/cards at top, breakdowns in middle, detail at bottom. Maximum 2-3 slicers per page; use the filter pane for additional filtering
- Prefer Deneb, Python, or R custom visuals over SVG or heavily customized core visuals -- balance elegance against technical debt
- Use report extensions (thin report measures, visual calculations) only when model measures are not feasible
- Centralize conditional formatting in extension or model measures referencing theme semantic colors (`"bad"`, `"good"`)
- Use consistent colors to direct attention, not to decorate. Avoid pie charts beyond 5 categories
- Sort visuals logically (typically descending by measure). Start chart axes at zero unless there is an explicit reason not to
- Use consistent fonts. Set `altText` for accessibility. Name visuals descriptively (`revenue_bar_chart` not `a1b2c3d4`)
- Eliminate redundant visuals. Consider the "Apply" button on high-cardinality slicers
- See the [Data Goblins report checklist](https://data-goblins.com/report-checklist) for pre-deployment validation


## What to Read for Common Tasks

| Task | Read |
|------|------|
| Add or modify a visual | **`references/visual-json.md`** -- expression syntax, field references, query roles, position, objects vs visualContainerObjects, selectors |
| Change formatting or colors | **`references/visual-container-formatting.md`** (container chrome) + **`references/theme.md`** (theme-level formatting). Prefer theme changes over bespoke visual formatting |
| Add conditional formatting | **`references/schema-patterns/conditional-formatting.md`** + **`references/measures.md`** (extension measures for CF) |
| Add or configure filters | **`references/filter-pane.md`** -- all 7 filter types, default values, filter discovery |
| Work with the theme | **`references/theme.md`** -- inheritance, wildcards, visual-type overrides, filter pane styling, inspecting and modifying with jq |
| Push visual formatting to theme | **`references/theme.md`** -- promote bespoke visual formatting into theme defaults for that visual type (copy from visual.json `objects`/`visualContainerObjects` into theme `visualStyles`) |
| Change page layout/background | **`references/page.md`** -- dimensions, background, wallpaper, visualInteractions |
| Create a tooltip page | **`references/page.md`** -- tooltip page setup (type, size, visibility) + visualTooltip opt-in on visuals |
| Create a drillthrough page | **`references/page.md`** -- drillthrough filter in page filterConfig |
| Change report settings | **`references/report.md`** -- themeCollection, resourcePackages, settings, outspacePane |
| Hand-author a report.json from scratch | **`references/report.md`** -- Hand-authoring report.json: `themeCollection` is required on schema 3.3.0 and needs a populated `baseTheme` plus its `resourcePackages` entry |
| Add extension measures | **`references/measures.md`** -- reportExtensions.json structure, DAX patterns, referencing |
| Add annotations / metadata | **`references/annotations.md`** -- custom name-value metadata on reports, pages, and visuals for deployment scripts, documentation, and external tooling |
| Add images or SVGs | **`references/images.md`** -- RegisteredResources, base64 in themes, SVG measures |
| Add or modify textboxes | **`references/textbox.md`** -- paragraphs, textRuns, textStyle |
| Sort a visual | **`references/sort-visuals.md`** -- sortDefinition inside query; an extension measure in a sort needs `"Schema": "extension"` too |
| Bind a field parameter | **`references/visual-json.md`** -- Field Parameters: expanded projections plus the sibling `fieldParameters` array; measure wells only |
| Clone a page or a visual | **`references/page.md`** -- regenerate every `name` id, `filterConfig` filter names included, then grep `definition/bookmarks/` |
| Add or remove a page or visual by hand | **`references/pbir-structure.md`** -- visuals are discovered from their folders; pages must also be listed in `pages.json` `pageOrder` |
| Format a slicer (dropdown, header, height) | **`references/visual-json.md`** -- Slicer Formatting: `objects.data` mode, the slicer object set, the 76px floor |
| Set an axis title | **`references/visual-json.md`** -- Axis Titles: the property is `titleText`, not `axisTitle` |
| A formatting change did nothing | **`references/visual-container-formatting.md`** (What Goes Wrong) + **`references/schema-patterns/selectors.md`** (a missing `{"id": "default"}` selector) |
| Write PBIR or TMDL from a script | **`references/validation.md`** -- no UTF-8 BOM, and what a clean validate does not prove |
| Sync slicers across pages | **`references/visual-json.md`** -- syncGroup (groupName, fieldChanges, filterChanges) |
| Edit visual interactions | **`references/visual-json.md`** + **`references/page.md`** -- visualInteractions in page.json (NoFilter, Filter, Highlight) |
| Change table/matrix column widths | **`references/visual-json.md`** -- columnWidth with metadata selector |
| Group visuals | **`references/visual-json.md`** -- visualGroup, parentGroupName, groupMode |
| Hide visuals or fields | **`references/visual-json.md`** -- isHidden at root level, query projection control |
| Format chart elements (labels, markers, lines) | **`references/visual-json.md`** -- labels, markers, lineStyles, dataPoint |
| Add analytics lines (reference, trend, error, forecast) | **`references/visual-json.md`** -- y1AxisReferenceLine, trend, error, forecast |
| Work with bookmarks | **`references/bookmarks.md`** -- bookmark state, filter snapshots, visual show/hide |
| Find model fields | **`references/semantic-model/finding-fields.md`** -- pbir model, te, fab commands |
| Rebind to different model | **`references/semantic-model/report-rebinding.md`** -- byPath vs byConnection conversion |
| Understand schema versions | **`references/schemas.md`** -- all schema types and current versions |
| Validate or check conformance | **`references/validation.md`** -- conformance dimensions, `pbir validate` categories, name and required-field rules, audit and discovery commands, what a clean validate does not prove, and how to verify rendering with or without Desktop |
| Understand how visuals generate DAX queries | **`references/semantic-model/inferring-queries-from-visuals.md`** -- visual metadata → SUMMARIZECOLUMNS mapping, data roles, IGNORE() context |
| Build or verify DAX query patterns | **`references/semantic-model/model-queries.md`** -- SUMMARIZECOLUMNS patterns, ROW(), query execution methods |
| Rename a table or field across visual JSON | **`references/rename-patterns.md`** -- Entity/Property/queryRef patterns in visual.json, filterConfig, reportExtensions |
| Fix broken field references after model changes | **`references/how-to/fix-broken-field-references.md`** -- diagnosis, repair workflow for renamed/moved/removed fields, slicer value pitfalls |
| Convert legacy report.json to PBIR format | **`references/how-to/convert-legacy-to-pbir.md`** -- format differences, step-by-step conversion, projections-to-queryState mapping, validation |
| Understand reportExtensions.json schema | **`references/report-extensions.md`** -- file schema structure, entities, visual calculations; see `references/measures.md` for DAX authoring patterns |
| Set dynamic (measure-driven) alt text | **`references/visual-container-formatting.md`** -- altText as a Measure expression under visualContainerObjects.general |
| Add a dynamic text run to a textbox | **`references/textbox.md`** -- measure-bound textRuns; round-trip from Desktop required |
| Understand drill-down cross-filter behavior | **`references/visual-json.md`** -- drillFilterOtherVisuals vs visualInteractions |
| Register a custom visual (AppSource, org-store, private .pbiviz) | **`references/report.md`** -- publicCustomVisuals, organizationCustomVisuals, resourcePackages |
| Understand schema version coupling | **`references/schemas.md`** -- parent/embedded schema sets, copying fragments between reports |
| Set up mobile (phone) layout | **`references/pbir-structure.md`** -- mobile.json per-visual, coordinate space, git hygiene |
| Git hygiene for a PBIR project | **`references/pbir-structure.md`** -- what to track, ignore, and leave to Desktop |

## definition.pbir

A report must be connected to a semantic model. There are two ways to do this:

- **byPath** -- Local PBIP reference/thick report: `{"byPath": {"path": "../Model.SemanticModel"}}` (schema 2.0.0)
- **byConnection** -- Remote/thin report: `{"byConnection": {"connectionString": "Data Source=powerbi://..."}}` (schema 2.0.0)

## Related Skills

- **`pbip`** -- PBIP project operations: rename cascades, project forking, report JSON patterns
- **`tmdl`** -- TMDL file format, authoring, and editing

## References

**Fetching Docs:** To retrieve current Power BI developer/report format docs, use `microsoft_docs_search` + `microsoft_docs_fetch` (MCP) if available, otherwise `mslearn search` + `mslearn fetch` (CLI). Search based on the user's request and run multiple searches as needed to ensure sufficient context before proceeding.

**Examples:**
- **`examples/K201-MonthSlicer.Report/`** -- Real PBIR report with 7 visual types (slicer, advancedSlicerVisual, kpi, lineChart, scatterChart, tableEx, textbox), extension measures, bookmarks, conditional formatting
- **`examples/visuals/`** -- 54 standalone visual.json examples; see `examples/visuals/__index.md` for a catalog. Split into `default/` (minimal, theme-only) and `formatted/` (bespoke formatting, conditional formatting, gradients, filters)

**Core references:**
- **`references/visual-json.md`** -- visual.json: expressions, field refs, query roles, position, objects vs vCO, selectors, sorting, filters, drill-down propagation
- **`references/desktop-bridge.md`** -- Verifying PBIR edits on the canvas via `pbir desktop` reload + screenshot; preview setting; locating the open PBIP
- **`references/pbir-structure.md`** -- PBIR folder structure, adding or removing a page or visual by hand (folder discovery vs `pages.json` `pageOrder`), mobile.json storage mechanics, git hygiene
- **`references/schemas.md`** -- Schema versions, URLs, and embedded schema coupling
- **`references/validation.md`** -- Conformance dimensions and how to validate (schema, names and ids, required fields, fields, enums, roles, layout, theme, semantic); `pbir validate` categories; audit and discovery commands; the failures a clean validate misses, the no-BOM rule, and verifying the render with or without Desktop
- **`references/enumerations.md`** -- Valid property enumerations
- **`references/version-json.md`** -- version.json format (concise)
- **`references/platform.md`** -- .platform file format (concise)
- **`references/bookmarks.md`** -- Bookmark structure and state snapshots

**Formatting & expressions:**
- **`references/theme.md`** -- Theme wildcards, inheritance, color system, filter pane styling, visual-type overrides, and whether the base theme file exists on disk. Includes jq patterns for inspecting and modifying theme JSON directly
- **`references/schema-patterns/`** -- Expressions, selectors, conditional formatting, visual calculations
- **`references/visual-container-formatting.md`** -- objects vs visualContainerObjects deep-dive; dynamic (measure-driven) altText
- **`references/measures-vs-literals.md`** -- When to use measure expressions vs literal values
- **`references/measures.md`** -- Extension measure patterns

**Visual & page configuration:**
- **`references/textbox.md`** -- Textbox visual format; dynamic (measure-bound) text runs
- **`references/page.md`** -- Page configuration and backgrounds; cloning a page or a visual without duplicating ids
- **`references/report.md`** -- Report-level settings; hand-authoring a report.json from scratch (a populated `themeCollection` is required on schema 3.3.0); custom visual registration (AppSource, org-store, private .pbiviz)
- **`references/wallpaper.md`** -- Report wallpaper/canvas background
- **`references/filter-pane.md`** -- Filter pane formatting
- **`references/sort-visuals.md`** -- Visual sort configuration; extension measures in sortDefinition
- **`references/images.md`** -- Static images, base64 in themes, SVG measures
- **`references/report-extensions.md`** -- reportExtensions.json format; the two-key `references` block (`measures`, `unrecognizedReferences`, and no `columns` array)
- **`references/annotations.md`** -- Custom metadata on reports, pages, and visuals

**Semantic model integration:**
- **`references/semantic-model/`** -- Field references, model structure, report rebinding, query inference

**How-to guides:**
- **`references/how-to/`** -- Advanced conditional formatting, SVG in visuals, fix broken field references, convert legacy to PBIR
