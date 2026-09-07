---
name: pbir-cli
description: This skill should be used whenever the user mentions "pbir", "pbir-cli", "Power BI reports", or "PBI reports", works with .pbir, .pbip, or .pbix files, or wants to refresh, screenshot, or visually verify a report that is open in Power BI Desktop. Covers creating, exploring, formatting, validating, and publishing Power BI reports through the pbir CLI and object model, plus driving Power BI Desktop (canvas reload, page screenshots) and querying connected or local semantic models.
---

# Working with Power BI reports using `pbir`

CLI for exploring, building, managing, formatting Power BI reports. All commands use `pbir`.

**IMPORTANT:** ALWAYS use `pbir` CLI commands to inspect and modify reports. NEVER write, replace, copy, or patch report JSON files directly on Windows or macOS. If the CLI does not expose a required mutation, stop and report the missing capability; do not fall back to file editing. Reading JSON through `pbir cat`, `pbir get`, or read-only examples is allowed. The sole exception is Linux, where `pbir` cannot be installed at all and hand-authoring is the only route; see "When `pbir` is missing".

**IMPORTANT:** FIRST Read and adhere to the mental model in [MENTAL-MODEL.md](important/MENTAL-MODEL.md).

## When `pbir` is missing

Install it with `uv tool install pbir-cli` (or `pip install pbir-cli`). That is the route to
use in every ordinary case, including when the command is missing entirely.

Not on Linux. Every `pbir-cli` release publishes exactly two wheels, `macosx_11_0_arm64` and
`win_amd64`, and no sdist, so both commands fail there with "No matching distribution found
for pbir-cli". There is no Linux build to fall back to, so do not retry the install. Work
without the CLI instead: hand-author PBIR JSON from the `pbip:pbir-format` skill's
`examples/visuals/` templates, check every file's JSON syntax with `jq empty` and its
structure against that skill's `references/validation.md`, then with the user's permission
publish the report to a sandbox workspace with `fab import` (byConnection reports only;
always pass `-f`, see the `fabric-cli` skill's `references/import-download-deploy.md`), and
inspect the rendering by exporting it server-side through the Power BI ExportTo API (the
submit, poll and download sequence in that skill's `references/paginated-reports.md` applies
to Power BI reports too).

`bin/fetch.sh` downloads a self-contained portable build as an alternative to installing
(macOS and Windows only). Reach for it **only** when `pbir` is not installed *and* installing
it is not possible: no network access to PyPI, no Python, or a locked-down machine that
forbids installs. A portable build does not update with `uv tool upgrade`, so preferring it
when a normal install would have worked leaves the user on a stale CLI. If an install failed,
fix the install rather than routing around it.

## Keeping `pbir` current

Resolve the binary before choosing an upgrade command, because `pbir` is not always a `uv` tool:

```bash
pbir --version
which pbir      # PowerShell: (Get-Command pbir).Source
```

If the resolved path sits under a `uv` tools directory, upgrade with `uv tool upgrade pbir-cli`; if
it sits under a Python scripts directory, upgrade with `pip install --upgrade pbir-cli`. The wrong
command reports success and changes nothing, which leaves the agent believing it is on a newer CLI
than it is: that is the failure mode behind every "this documented flag does not exist" dead end.
Honor any user-pinned version, and upgrade only when required or requested. A portable build from
`bin/fetch.sh` is updated by re-fetching it, not by either package manager.

## Keeping the Fabric CLI current

When publishing to Fabric (`pbir publish`) alongside the `fabric-cli` plugin, check the installed Fabric CLI (`fab`) if publishing reports a compatibility problem. Upgrade with `uv tool upgrade ms-fabric-cli` only when required or requested, and honor any user-pinned version.

## Learning from Mistakes

Durable learnings go in this skill folder, where they ship with the plugin and reach every machine
that installs it. A per-agent memory file does not travel, so it is the last resort.

- **True on any machine** (a PBIR shape, a CLI contract, a service behaviour): the matching
  `references/*.md` file. The `## Reference Files` list at the end is the index.
- **True only on some platform or at some version** (a Windows console codepage, a Desktop-only
  command, a flag that needs a minimum `pbir` version): same destination, with the scope in the
  sentence and a substitute named for any scoped route, per the boundary rule below.
- **True only on this machine** (where `pbir` is installed here, a local path, a preview toggle):
  the agent's own memory file. Claude Code `~/.claude/rules/pbir-cli.md`, Cursor
  `.cursor/rules/pbir-cli.mdc`, Copilot `.github/instructions/pbir-cli.instructions.md`. Generalise
  first: most machine-local facts have a portable procedure hiding inside them.

Keep entries concise and generalisable. This is not a change log. Prune redundancy, and link out to
references and examples rather than restating them.

<!-- boundary-rule:begin -->
## Where a new learning goes

Three questions, in order. Stop at the first yes.

**1. Is it true only because of how THIS machine is set up right now?**
An installed path, which identity you are logged in as, a preview toggle, a console codepage, which
build happens to be installed. Then it is machine-local.

Before accepting that answer, try to generalise it. Most machine-local facts are the residue of a
search that succeeded once, and the search is the portable part:

| Instead of recording | Record |
| --- | --- |
| the path where you found a DLL | the probe that finds it, and how to tell which host can load it |
| that a preview toggle is off here | the verbatim symptom string, and the route that works regardless |
| which account has rights here | the check that reveals the mismatch |
| that a script cannot find a binary | a fix to the script |

If the generalised form survives, it is not machine-local: take it to question 2 or 3. If nothing
survives, because the fact is about one machine, one tenant or one person, write it to the agent's
own memory file and nowhere else. It would mislead an agent anywhere else, and this repository is
public.

**A Codespace has no legitimate machine-local layer.** A fact about a Codespace is true of every
Codespace built from the same devcontainer, which makes it a fact about that image. Commit it.
Never start a memory file inside a container.

**2. Is it true only where Power BI Desktop runs, only in a Windows shell, or only at some tool
version?**
Then it is portable knowledge with a boundary. It goes in this skill's `references/`, with the
boundary in the sentence:

- Platform: open or close with the scope. "On a cp1252 Windows console ... Linux and macOS never
  hit this." "Power BI Desktop only."
- Version: write the symptom and the check as the instruction, never the version. "If `fab find`
  errors, run `fab --version` before assuming a syntax problem." Put the version and date you
  observed in brackets at the end, never in the imperative. A version in the imperative rots into a
  lie; a version in brackets rots into a footnote.
- A dated or version-pinned claim also carries a `Retest:` line naming the one command that settles
  it, plus a `Verified <date>` stamp. `scripts/check-skill-hygiene.py` reports the stale ones and
  fails on a version claim with no `Retest:`.

**A scoped statement that is a ROUTE is not finished until it names the substitute in the same
sentence.** "`pbir desktop screenshot` is Windows and Desktop only" leaves a Linux agent stuck.
"`pbir desktop screenshot` is Windows and Desktop only; where Desktop is unavailable, render
server-side with the `ExportTo` API (fabric-cli `references/reports.md`)" does not.

**3. Otherwise it is a fact about the file format, the product, or the service API.**
True everywhere, including a Codespace with no Desktop and no Windows. It goes in this skill's
`references/` with no qualifier, or in `SKILL.md` when the agent must know it before opening any
reference. This is the default and where most learnings land.

### Two tests that settle almost every case

- *Would this sentence still be true in a Linux Codespace with no Power BI Desktop?* Yes means
  question 3. No, but only because Desktop is missing, means question 2. No, because the sentence
  names a path, a version or a toggle, means question 1, so run the generalisation table first.
- *Could anyone else running this plugin act on it?* If not, question 1.

### When torn, file it in the more public place

An over-cautious scope clause on a portable fact costs a reader one clause. A machine-local fact
shipped as product knowledge misleads everyone who installs the plugin.

### Where to write it

If `PBI_MARKETPLACE_ROOT` is set, a writable clone of this marketplace is on the machine:
`bash "$PBI_MARKETPLACE_ROOT/scripts/record-learning.sh"` writes the note, runs the hygiene scan,
commits to a branch and opens a pull request.

If it is unset, the skills are loading from a read-only plugin cache and an edit there is discarded
by the next `plugin update`. Write the note to the agent's memory file instead, and say plainly in
the note that it still needs promoting into the plugin.

Nothing portable belongs in `~/.claude/rules/`, `.cursor/rules/` or `.github/instructions/`. Those
are per-machine and per-user.
<!-- boundary-rule:end -->

## How to use `pbir`

### General workflow

1. Explore the report. The report must be in PBIR format: pbip, pbir-only, or pbix-with-PBIR-metadata. Prefer pbir or pbip. Whenever the user mentions Power BI Desktop or says the report is open in Desktop, run `pbir desktop list` FIRST: it maps each running instance to the file it has open (locating the report on disk) and confirms the bridge works before any edits begin. `pbir desktop` is Windows-only; on macOS and Linux do not use it (every invocation fails). On macOS, deploy with `pbir publish` to a sandbox workspace in Fabric instead and verify the rendered report in the browser via the Chrome MCP tools. On Linux there is no `pbir` at all (see "When `pbir` is missing"): with the user's permission publish the byConnection report to a sandbox workspace with `fab import`, then verify by rendering it server-side through the Power BI ExportTo API.
2. Identify the model. Reports generally should be thin reports connected to a remote model in Power BI or Fabric.
3. Clarify intent. For vague or open-ended instructions, consult **`references/vague-prompts.md`** and use `AskUserQuestion` to understand expectations and report context before mutating anything.
4. Plan changes. For new reports, pages, or visuals, draft a wireframe or mock-up for the user to approve before building.
5. Make changes. Reach for relevant files in `references/`, `examples/`, and related skills like `pbi-report-design`.
6. Validate. Mutating commands validate their own writes. Run explicit `pbir validate` after a coherent batch of changes and before completion; use narrower checks while iterating and `--all` for the final confidence pass. For visual confirmation, prefer the local loop when the report is open in Power BI Desktop: `pbir desktop refresh` then `pbir desktop screenshot` and inspect the PNG (see "Desktop Integration" below). Otherwise ask permission to publish to a sandbox workspace with `pbir publish` and inspect rendering via Chrome MCP, devtools CLI, or Playwright.
7. Iterate. Expect multiple rounds. Push back on one-shot expectations from vague prompts.
8. Record learnings. Route each one by the rule in **Learning from Mistakes** above.

### Path syntax

`pbir` uses a filesystem paradigm for identifying reports, pages, visuals etc. and glob syntax for bulk operations.

Format: `ReportName.Report/PageName.Page/VisualName.Visual`

- Type suffixes (`.Report`, `.Page`, `.Visual`) are required
- Quote paths with spaces: `"My Report.Report/Dashboard.Page"`
- Use glob patterns for bulk operations: `"Report.Report/**/*.Visual"` (requires `--force/-f` for `set` and `rm`)
  - `*.Visual`; all visuals on current page
  - `Page.Page/*.Visual`; all visuals on a specific page
  - `**/*.Visual`; all visuals across all pages
  - `**/card*.Visual`; visuals whose name starts with "card"
  - `**/*.Report/**/*.Visual`; all visuals across all reports
- Properties via `get` or `set` and dot notation: `"Report.Report/Page.Page/Visual.Visual.title.fontSize"`
- Filters/bookmarks: `"Report.Report/filter:Name"`, `"Report.Report/bookmark:Name"`
- If multiple reports match, disambiguate with parent folder prefix
- Absolute filesystem paths work too: `"C:\Reports\Sales.Report"`, `"C:\Reports\Flash.pbix"` (globs do not combine with absolute paths)
- Workspace destinations use `.Workspace` suffix: `"My Workspace.Workspace/Report.Report"`


## Critical Rules

Follow all rules below.

0. **ASK user for clarifications and push back on one-shot prompt requests.** Pursue an iterative multi-step way-of-working

1. **CHECK references before starting work.** Identify relevant [references](references/) and [examples](examples/) that can help you understand the user requirements

2. **NEVER edit report JSON files directly on Windows or macOS.** Always use `pbir` CLI commands. Use `pbir cat` or `pbir get` to inspect JSON or properties; use `pbir set` for any property not covered by a dedicated command. The sole exception is Linux, where `pbir` cannot be installed at all and hand-authoring is the only route (see "When `pbir` is missing").

3. **Discover before setting.** Run `pbir schema describe <type>` to list a visual type's objects, then `pbir schema describe <type> <object>` for property names, types, ranges, and enums before formatting. Do not guess property names

4. **Theme-first formatting.** Check `pbir visuals format` before applying bespoke formatting; the theme may already set the property. Prefer `pbir theme set-formatting` for changes that apply to all visuals of a type. Reserve `pbir visuals title/background/border` for one-off overrides

5. **Validate proportionally.** Mutating commands already validate their writes. Run `pbir validate "Report.Report"` after each coherent batch and before completion. Use `--qa` for overlap/overflow checks, `--fields` for model field verification, and `--all` for the final confidence pass. On Linux, where `pbir` cannot be installed, check every changed file with `jq empty` and against the `pbip:pbir-format` skill's `references/validation.md` instead

6. **Verify rendering through the Desktop bridge.** When the report is open in Power BI Desktop, run `pbir desktop refresh` after every change unless the user asks not to, then `pbir desktop screenshot` and inspect the PNG after every meaningful change. Validation cannot catch rendering problems (overlap, truncation, wrong field, illegible formatting); the screenshot is the only proof a change rendered as intended. When a request involves many changes, ask the user up front whether to refresh after each step (so they watch progress in the canvas) or once at the end. Check availability once with `pbir desktop list` before starting the loop; if the bridge is unavailable, do not retry it after every change (see "When the bridge is unavailable" below)


## Core Workflows

### Exploration and Analysis

Understand existing reports before modifying. **Always check page dimensions and existing visual positions before adding or resizing visuals** setting position/size without knowing the page dimensions causes errors. Read those positions off disk at the start of every task, and again after any pause in which the user had the report open in Desktop: a Desktop save writes canvas nudges back into `visual.json`, so coordinates remembered from earlier in the conversation can silently undo hand adjustments the user just made.

```bash
pbir desktop list                                # FIRST if Desktop is mentioned: instances (PID, open file)
pbir ls                                          # Find all reports
pbir ls "Report.Report"                          # List pages/filters/theme
pbir tree "Report.Report" -v                     # Full structure with fields
pbir validate "Report.Report"                    # Health check
pbir get "Report.Report"                         # Report properties
pbir pages json "Report.Report/Page.Page"        # Check page width/height
```

For deeper exploration, consult **`references/exploration.md`**.

### Model Discovery (Required Before Binding Fields)

Always query the connected model to discover correct table/column/measure names. Never guess field names.

```bash
pbir model "Report.Report"                       # Connection info (workspace, model, thick/thin)
pbir model "Report.Report" -d                    # All tables, columns, measures
pbir model "Report.Report" -d -t Sales           # Filter to specific table
pbir model "Report.Report" -q "EVALUATE VALUES('Geography'[Region])"  # Check field values
pbir model "Report.Report" -q "EVALUATE ROW(\"Revenue\", [Total Revenue])"  # Test a measure
pbir fields list "Report.Report"                 # Fields already in use across report
```

Routing depends on the report's model reference: thin reports (`byConnection`) query the Power BI / Fabric service; thick reports (`byPath`) query the local Analysis Services engine of the Power BI Desktop instance that has the report open, so `-q` and `-d` work fully offline against live model state. Local queries need the .NET Framework ADOMD client (found automatically from DAX Studio or Desktop installs; override with `PBIR_ADOMD_DIR`).

When `-d` fails with `failed to load model schema` or `Could not retrieve model definition`, the schema route is broken rather than the report: on a `byConnection` report the schema comes through the Fabric CLI, so check `fab --version` first. `-q` still works, and a local `byPath` model is unaffected. Measure-bound visuals keep working while column-bound projections do not, and `--skip fields` does not help. See "When the model schema will not load" in **`references/fields-and-bindings.md`** before changing approach.

For full model query patterns and field binding workflows, consult **`references/fields-and-bindings.md`**.

### Semantic Model + Report Workflows (`te` + `pbir`)

When work crosses both layers, use Tabular Editor CLI (`te`) for semantic-model mutations and `pbir` for report mutations. Model object identity is the boundary: modern `te mv` cascades references inside the model, but report bindings still retain the old `Table.Field` and must be updated with `pbir`.

```powershell
te connect "Sales Workspace" "Sales Model"
te mv "'Actuals'[Actuals MTD]" "'Actuals'[Sales MTD]" --save
te validate --errors-only
pbir fields replace "Sales Flash Report.Report" --from "Actuals.Actuals MTD" --to "Actuals.Sales MTD" --dry-run
pbir fields replace "Sales Flash Report.Report" --from "Actuals.Actuals MTD" --to "Actuals.Sales MTD"
pbir validate "Sales Flash Report.Report" --fields
pbir desktop refresh "Sales Flash Report.Report"
```

Use `te deps --downstream` plus `pbir fields find` before a rename, `pbir fields replace-table` after a table rename, and no report rewrite for metadata-only changes such as format strings or descriptions. For renames, moves, additions, deletions, deploy/rebind order, and final gates, consult **`references/te-cli-tandem.md`**.

### Desktop Integration (Refresh and Screenshot)

When the report is open in Power BI Desktop (Windows, with the "external tool access" preview feature enabled), drive the running instance directly. This is the fastest way to visually verify changes; no publishing required.

```bash
pbir desktop list                                     # Running instances (PID, open file, unsaved state, pages); `status` is an alias
pbir desktop refresh "Report.Report"                  # Reload on-disk definition into the canvas (`reload` is an alias)
pbir desktop refresh "Report.Report" -m               # --model: also re-apply the model (TMDL) definition
pbir desktop screenshot "Report.Report/Page.Page" -o verify.png
pbir desktop screenshot "Report.Report" --all         # Every page -> ./screenshots (--output-dir to set; --settle <ms> before first capture)
```

The edit-verify loop: mutate with `pbir set`/`add`, then `pbir desktop refresh`, then `pbir desktop screenshot`, then read the PNG. Inspect the rendered page after every meaningful change; screenshots catch what validation cannot (overlap, truncation, wrong field, illegible formatting). Set `PBIR_DESKTOP_AUTO_REFRESH=1` to fold the refresh step into every save. `--scale` is clamped to 1-3 (default 2); `--pid` targets a specific instance when several are open.

Screenshots need the Desktop window in the Report view. Refreshing an instance with unsaved changes makes Desktop save first, rewriting the whole definition on disk. PBIX files support screenshot but not refresh. For requirements, multi-instance behavior, and troubleshooting, consult **`references/desktop-integration.md`**.

Do not guess a sleep between refresh and screenshot: `--settle` only applies with `--all`, and there is no `--out` (the single-page flag is `-o/--output`). For a single page, use the **`reports:pbi-verify-loop`** skill, which refreshes and then captures until two consecutive screenshots match.

**When the bridge is unavailable.** `pbir desktop` commands are Windows-only: on macOS and Linux do not use them at all; every invocation fails before reaching Desktop. On Windows, `pbir desktop list` distinguishes the cases: the bridge is unreachable when the preview feature is off ("Enable external tool access to Power BI Desktop through secure local APIs" under File > Options and settings > Options > Preview features, then restart Desktop), and it reports when no running instance has the target report open. If the preview feature is off, relay the enable steps to the user once and ask whether they want to turn it on; do not keep retrying bridge commands meanwhile. Until the bridge works, and always on macOS, verify with `pbir validate --all`, then with the user's permission deploy with `pbir publish` to a sandbox workspace in Fabric and inspect the rendered report in the browser through the Chrome MCP tools. On Linux `pbir` cannot be installed at all, so check the changed JSON with `jq empty` and against the `pbip:pbir-format` skill's `references/validation.md`, then with the user's permission publish the byConnection report to a sandbox workspace with `fab import` (always pass `-f`), and inspect the rendering by exporting it server-side through the Power BI ExportTo API.

### Creating Reports

New reports include out of the box:
- The **sqlbi** theme (professional colors, typography). Do not run `pbir theme apply-template` unless the user requests a different theme
- A default **Page 1** with a **textbox** visual for the page title at position (20,20) height 90. Do not add a new textbox; rename the existing page instead. Place subsequent visuals at `y:120` or below to avoid overlapping the title textbox. Use `--no-title` on `pbir new report` to skip the default title textbox when the user wants a clean canvas

Connection: pass `--connection "Workspace/Model.SemanticModel"`, or set an active connection first with `pbir connect` (optionally `pbir profile` / `pbir connect --profile <name>` to switch between saved connections). When an active connection is set, the connection flag can be omitted. The connection has to be a tenant model: the command cannot be pointed at a local sibling `.SemanticModel`, so create against the workspace copy and then `pbir report rebind --local` (see `references/create-new-report.md`).

```bash
pbir new report "Sales.Report" -c "Workspace/Model.SemanticModel"
pbir pages rename "Sales.Report/Page 1.Page" --to "Overview" -f   # Rename default page (new name via --to)
pbir add visual card "Sales.Report/Overview.Page" --title "Revenue" -d "Values:Sales.Revenue" --y 120
pbir add filter Date Year -r "Sales.Report"
pbir validate "Sales.Report"
```

Data-role names in `-d "Role:Table.Field"` (e.g. `Values`, `Category`, `Y`, `Series`, `Indicator`) come from the visual type's capability schema. Run `pbir add visual --list` or `pbir visuals bind --list-roles` to discover the roles for unfamiliar visual types. The CLI matches role names case-insensitively, so `Values:` and `values:` both work.

For step-by-step creation guidance, use the **`create-pbi-report`** skill.

### Adding and Formatting Visuals

**Formatting hierarchy**: base theme -> custom theme -> visual-type defaults -> individual visual overrides. Always check and prefer theme-level formatting before applying bespoke visual formatting. Use `pbir visuals format` to see the full cascade with source labels (default/wildcard/visualType/visual).

```bash
# Add a visual with data binding (role names match the visual capability list)
pbir add visual card "Report.Report/Page.Page" --title "Total Sales" -d "Values:Sales.Revenue"

# ALWAYS check theme cascade first; see what formatting already applies
pbir visuals format "Report.Report/Page.Page/Visual.Visual"

# Set formatting in the THEME (preferred; applies to all visuals of this type)
pbir theme set-formatting "Report.Report" "card.*.border.radius" --value 8

# Only format bespoke if genuinely one-off
pbir visuals title "Report.Report/Page.Page/Visual.Visual" --text "Revenue" --fontSize 14 --show

# Bind more fields
pbir visuals bind "Report.Report/Page.Page/Visual.Visual" -a "Category:Products.ProductName"

# Validate after changes
pbir validate "Report.Report"

# If the report is open in Desktop, confirm the rendering
pbir desktop refresh "Report.Report"
pbir desktop screenshot "Report.Report/Page.Page" -o verify.png   # then Read verify.png
```

For bulk visual creation, see **`references/add-new-visual.md`**.
For formatting workflows, consult **`references/format-visuals.md`** (theme-first approach, property discovery, glob patterns).

### Visual Groups

Visual groups bind multiple visuals so they move and scale together. Use them when a set of visuals should behave as a single unit (a header strip, a KPI row, a chart-plus-annotation pair).

```bash
pbir visuals group "Report.Report/Page.Page" --list                       # List groups on page
pbir visuals group "Report.Report/Page.Page" --create "KPI Group"         # Create empty group
pbir visuals group "Report.Report/Page.Page/Group.Visual" --add "Card.Visual" --add "KPI.Visual"
pbir visuals group "Report.Report/Page.Page/Group.Visual" --remove "Card.Visual"
pbir visuals group "Report.Report/Page.Page/Visual.Visual" --ungroup      # Remove this visual from its group
pbir visuals group "Report.Report/Page.Page/Group.Visual" --ungroup       # Ungroup all members and delete the group
```

Default mode is `ScaleMode`; override with `--mode` if a different behavior is needed.

### Style Presets

Style presets apply a curated bundle of formatting in one step. Use a preset when the user wants a consistent look across many visuals without specifying every property.

```bash
pbir visuals preset --list                                        # Available presets
pbir visuals preset "Report.Report/Page.Page/Visual.Visual" --name minimal
pbir visuals preset "Report.Report/**/*.Visual" --name presentation
```

Presets are themed; pair them with `pbir theme apply-template` for full visual consistency.

### Property Discovery (Required Before Formatting)

Every visual type has dozens of objects with hundreds of properties. Use the schema discovery workflow to find the right object and property name before setting values. Do not guess property names.

```bash
# Step 1: What objects exist for this visual type? (objects + property counts)
pbir schema describe "lineChart"

# Step 2: What properties does an object have? (includes types, ranges, enums, descriptions)
pbir schema describe "lineChart" "lineStyles"

# Step 3: What's currently set on a live visual? (shows source: default/wildcard/visualType/visual)
pbir visuals format "Report.Report/Page.Page/Visual.Visual"
pbir visuals format "Report.Report/Page.Page/Visual.Visual" -v   # Include unset (None) properties
pbir visuals format "Report.Report/Page.Page/Visual.Visual" -p lineStyles  # Filter to object

# Step 4: Fuzzy search for a property by name
pbir visuals properties -s "marker"
```

For built-in visuals, the authoritative list of valid type ids and per-type `objects` names comes from Microsoft's core visual catalog (bundled and pinned by the CLI). Use it to confirm a type or object name exists before authoring:

```bash
pbir schema types                       # Built-in visual + entity type ids (--vco for universal container objects, --selectors for selector objects)
pbir schema describe "barChart"         # Valid objects + their properties for one type
pbir schema roles "barChart"            # Data roles the type accepts (required? multiple? Column/Measure)
pbir schema describe "tableEx" --json   # Full JSON for agent consumption
```

`pbir schema describe` draws from this core catalog (the authority `pbir set` enforces) and enriches it with the theme schema for value ranges and enums. Custom visuals are out of scope for the catalog.

Schema descriptions include practical usage notes (e.g., error bars as target lines, title.text supporting measure-driven dynamic values). Use `--json` output for full descriptions.

For a complete offline reference of every property for every visual type, consult **`references/property-catalogue.md`** (49 types, 15 universal containers, 12,600+ property slots).

### Bulk Modification (Glob Patterns)

```bash
# Set property on ALL visuals in report (glob requires -f)
pbir set "Report.Report/**/*.Visual.title.show" --value false -f

# Find all card visuals
pbir find "Report.Report/**/card*.Visual"

# Format all visuals on a page
pbir visuals title "Report.Report/Page.Page" --show --fontSize 12
```

### Conditional Bulk Ops (--where)

`--where` filters which visuals a glob operation targets. Available on `set` and all `visuals` property commands.

```bash
pbir set "Report.Report/**/*.Visual.title.fontSize" --value 16 --where "visual_type=card" -f
pbir visuals legend "Report.Report/**/*.Visual" --show --where "width__gt=400"
pbir visuals resize "Report.Report/**/*.Visual" --width 350 --height 250 --where "visual_type=card"
```

Predicate operators: `=`, `__lt`, `__gt`, `__lte`, `__gte`, `__in=a|b|c`, `__contains`, `__icontains`. Combine with commas (ANDed): `--where "visual_type=card,width__gt=300"`. Full operator list in **`references/format-visuals.md`**.

### Conditional Formatting

```bash
# Find out what a container accepts before writing to it
pbir schema describe barChart.dataPoint          # "Conditional formatting:" line at the bottom

# Create CF (structural; use pbir visuals cf)
pbir visuals cf "Visual" --measure "labels.color _Fmt.StatusColor"
pbir visuals cf "Visual" --gradient --field "Table.Field" --min-color bad --max-color good
pbir visuals cf "Visual" --data-bars --field "Table.Field"
pbir visuals cf "Visual" --image --field "_SVG.Bullet"          # measure-driven image or SVG

# Read / edit / remove CF (dot-path; use pbir set / pbir get)
pbir get "Visual.dataPoint.fill.cf"                             # summary
pbir set "Visual.dataPoint.fill.cf.gradient.min.color" --value "bad"
pbir set "Visual.dataPoint.fill.cf" --remove                    # or --clear
pbir get "Report.Report/**/*.Visual.**.cf"                       # bulk read
```

CF reaches well past data point colors: titles, subtitles, borders, tooltips, axis
bounds, reference-line values, data-label text, and error-bar styling all accept a
measure. `pbir schema describe <type>.<container>` is the authoritative answer for
any one container, and a starred property there was confirmed against a rendered
report rather than inferred from the catalog.

When the field driving the format is not the field being formatted (a grid column
coloured by a helper measure, a combo chart's secondary series), name the target
with `--target-field`, otherwise the entry scopes to the driver and Desktop renders
it on the wrong column:

```bash
pbir visuals cf "Grid.Visual" --rules --field "Sales.Margin %" --rule "lt 0 bad" \
  --on values.backColor --target-field "Sales.Revenue"
```

For gradient/rules/icons/data bars/image options, copy/remove/convert, and best practices, consult **`references/conditional-formatting.md`**.

### Visual Actions, Bookmarks, Drillthrough

```bash
pbir visuals action "Visual" --type PageNavigation --target "Details"  # Set action
pbir add bookmark "Report.Report" "Q1 View"                           # Create bookmark
pbir bookmarks page "Report.Report" "Q1 View" "Details"               # Set bookmark target page
pbir pages drillthrough "Report/Details.Page" --table T --field F     # Add drillthrough
pbir pages set-tooltip "Report/Tooltip.Page"                          # Configure tooltip
```

For bookmark management, consult **`references/bookmarks.md`**.

### Filters

```bash
pbir add filter Table Field -r "Report.Report"                        # Categorical
pbir add filter T F -r "R.Report" --type TopN --n 10 --by-table T2 --by-field F2  # TopN
pbir add filter T F -r "R.Report" --type Advanced --operator GreaterThan --values 1000
pbir add filter Date Date -r "R.Report" --type RelativeDate --period Last30Days
```

Filter creation validates the field against the connected semantic model. If validation cannot resolve (missing connection, model unreachable), the command fails closed rather than producing an unverified filter. Use `--no-validate` only when the user explicitly needs to bypass this.

To change filter type, remove and recreate. For full filter reference, consult **`references/filters.md`**.

### Auditing Reports

```bash
pbir validate "Report.Report"                       # Structure, schema, fields, QA (use --all)
pbir bpa run "Report.Report"                        # Best Practice Analyzer rule sweep
pbir bpa run "Report.Report" --fix --save           # Apply safe automatic fixes
pbir tree "Report.Report" -v                        # Structure + field bindings
pbir theme colors "Report.Report"                   # Palette and usage
pbir color list "Report.Report"                     # Every hard-coded color literal and where it is used
pbir fields list "Report.Report"                    # Fields in use
pbir dax measures list "Report.Report"              # Extension measures
pbir filters list "Report.Report"                   # Filters at every scope
```

BPA rules are managed with `pbir bpa rules list/ignore/unignore`; ignored rules are scoped per report. For the comprehensive audit checklist, consult **`references/audit-report.md`**.


## Command Reference

The full command reference lives in **`references/cli-reference.md`**. Always run `pbir <command> --help` before using an unfamiliar command; the help text is authoritative for flag names and defaults.

Quick map of command groups:

```yaml
Getting started:     config, connect (+ --profile), profile, new
Browse and query:    ls (+ --tree), find, get, cat, model     # `tree` is an alias of `ls --tree`
Modify:              set, add, mv, cp, rm, visuals, pages
Data:                fields, filters, dax, bookmarks, annotations
Theme and style:     theme (colors, fonts, set-colors, set-fonts, set-formatting, apply-template), color (list, replace), fonts (list, replace, clear, available)
Schema discovery:    schema (= capabilities) (types, describe, roles, status, upgrade), visuals properties, visuals format
Workflow ops:        validate, backup, restore, publish, download, batch, open, bpa, usage
Desktop (Windows):   desktop (list/status, refresh/reload, screenshot)
```

Notes on the less-obvious groups:

- **connect / profile**: `pbir connect "Report.Report"` sets the active context so subsequent commands can omit the report path. `pbir profile` saves and switches named connections (`pbir connect --profile dev`).
- **visuals group**: visual groups let users scale and position multiple visuals together. See "Visual groups" workflow below.
- **visuals preset**: named style presets (`minimal`, `bold`, `clean`, `emphasis`, `presentation`) apply curated formatting in one step.
- **bpa**: Best Practice Analyzer. `pbir bpa run "Report.Report"` reports rule violations; `--fix --save` applies safe fixes. `pbir bpa rules list/ignore/unignore` manages the rule set.
- **color**: `pbir color list` enumerates every hard-coded color literal and where it is used; `pbir color replace --from <hex> --to <hex>` swaps one across the report (scope with `--theme`/`--report`). Distinct from the `theme` group, which edits the theme JSON rather than inline literals.
- **fonts**: the typography mirror of `color`. `pbir fonts list` audits families/sizes/weights across report + theme; `pbir fonts replace --from --to` swaps a family everywhere; `pbir fonts clear` drops per-visual font/format overrides so the theme default applies. To set the theme's own fonts, use `pbir theme set-fonts`.
- **usage**: `pbir usage "Report.Report"` (or a workspace / published report) pulls views, viewers, pages, and load times from the Power BI service via your `az login` token. `--model` adds the workspace usage metrics model for richer detail (Contributor+, generates a hidden model). Relies on undocumented service telemetry.

## Global Flags

Top-level flags; place before the subcommand: `pbir -q new report ...`, NOT `pbir new report -q ...`

```yaml
-q / --quiet: suppress animations, tips, spinners (agent-friendly)
--output-format text|json: structured stdout for commands that support it
--error-format text|json: structured stderr where supported
--debug: enable tracebacks and timing
--rawdog: skip EVERY validation check (umbrella for --skip all)
--skip <category>: skip validation categories (repeatable, comma-separated): structure, schema, schema-version, fields, enums, qa, roles, layout, theme
```

`pbir` validates implicitly on mutations. `--skip`/`--rawdog` relax that for deliberate cases, e.g. `pbir --skip fields set ...` to author a visual whose field is not in the model yet. They are global, so they go before the subcommand. Prefer fixing the underlying issue over `--rawdog`. They skip *validation* only: neither bypasses the model schema **load** that authoring a column reference needs, so neither rescues a `failed to load model schema` (see `references/fields-and-bindings.md`).

Command-specific output flags such as `--json` or `-F json`, and mutation flags such as `-f/--force`, go after the relevant subcommand. Check `pbir <command> --help`; they are not global flags.


## Common Mistakes

- **Role names are case-insensitive but should match the capability list.** Use `pbir add visual --list` or `pbir visuals bind --list-roles` to discover role identifiers (e.g. `Values`, `Category`, `Y`, `Series`) for the target visual type.
- **`pbir cat` does not support filters or bookmarks.** Use `pbir filters list --json` or `pbir bookmarks json` instead.
- **`pbir publish` uses positional args**, not `--workspace`. Correct: `pbir publish "Report.Report" "Workspace.Workspace/Report.Report" -f`.
- **`pbir filters list` has no `-v` flag.** Use `--json` for detailed output.
- **Do not convert to PBIX then publish the PBIR folder.** If converting to PBIX, publish the `.pbix` file directly. If publishing PBIR, skip conversion entirely.
- **Renaming a page moves its folder, whichever route you take.** `pbir pages rename ... --to` renames the folder only, leaving the page ID and display name untouched; `pbir set "<page>.displayName"` changes the display name *and* renames the folder to match. So every path built from the old page name is stale afterwards; recompute them, or rename first and derive later paths from the new name.
- **DMV queries fail against service-connected models.** For thin reports (`byConnection`), `pbir model -q` runs EVALUATE DAX only; `INFO.TABLES()` and other DMVs return 400 from the service, and schema comes from TMDL. Use `pbir model -d` for schema introspection. Thick reports (`byPath`) open in Desktop query the local engine instead, where the live schema is used.
- **`pbir desktop refresh` does not work on PBIX files.** Desktop only reloads PBIP/PBIR definitions from disk; PBIX instances support `pbir desktop screenshot` only.
- **Always run `pbir <command> --help`** before using an unfamiliar command to confirm exact syntax.


## User Interaction

Use `AskUserQuestion` to interview the user before executing. This is important for:

- **Visual design**: What story should the visual tell? What comparisons matter?
- **Formatting intent**: One-off bespoke or theme-level change for all visuals of this type?
- **Complex requirements**: Deneb vs core visual, CF logic, page layout; discuss trade-offs first
- **Ambiguous field mapping**: When the model has multiple plausible fields, discuss intent
- **Refresh cadence**: For multi-change requests with Desktop open, ask whether to `pbir desktop refresh` after each step (visible progress) or once at the end
- **Clearing formatting**: ALWAYS confirm before `pbir visuals clear-formatting`; it is irreversible


## Validation

Mutating commands validate their own writes. Run `pbir validate "Report.Report"` after a coherent batch of changes and before completion. This catches broken field references, invalid JSON, schema violations, and structural issues without repeating a full report scan after every small command.

```yaml
(no flags): structure + schema validation
--fields: also validate fields exist in model with correct types (Column/Measure)
--qa: also run quality-assurance rules (overlap/overflow, hidden visuals, visual filters, field counts, layout and role-cardinality heuristics, and color-contrast checks where the installed build has them)
--semantic: also check visual type ids + objects/visualContainerObjects names against the core visual catalog
--all: structure + schema + fields + QA + semantic
--strict: promote field/QA/semantic warnings to errors
--json / --tree: output format
--allow-download-schemas: download missing schemas on the fly
```

The same checks run implicitly on mutations. To bypass a category deliberately, use the global flags before the subcommand: `--skip <category>` (`structure, schema, schema-version, fields, enums, qa, roles, layout, theme`; repeatable, comma-separated) or `--rawdog` (skip all). Prefer fixing the cause over skipping.

`--semantic` is backed by the core visual catalog bundled and pinned by the CLI. It flags unrecognized `visualType`, `objects`, and `visualContainerObjects` names as advisory warnings (info for unlisted properties); `--strict` makes them errors. The catalog is preview and may lag the product, so unknown but plausible names and custom visuals can still be valid. Treat semantic findings as a quick authoring check, not a hard gate.

**Schema version errors**: Fix with `pbir schema fetch --yes` then `pbir schema upgrade "Report.Report"`.

`pbir validate` checks structure, not rendering. When the report is open in Power BI Desktop, follow every validation with the bridge loop: `pbir desktop refresh`, `pbir desktop screenshot`, then read the PNG. Do not report a change as complete without having seen it render.


## Reference Files

```yaml
references/cli-reference.md: full syntax for any command with all flags; Windows console encoding
references/exploration.md: exploring an unfamiliar report systematically
references/desktop-integration.md: driving Power BI Desktop; canvas refresh, page screenshots, auto-refresh, local model queries, troubleshooting
references/create-new-report.md: building a report from scratch
references/add-new-visual.md: adding visuals, layout patterns, bulk creation
references/add-image.md: image visuals from file, URL, or a measure; the ImageUrl measure contract
references/visual-groups.md: visual groups (create, add/remove members, ungroup)
references/visual-presets.md: style presets (minimal, bold, clean, emphasis, presentation)
references/fields-and-bindings.md: field binding, Column vs Measure types, swapping fields, rebinding
references/te-cli-tandem.md: coordinated semantic-model and report changes with te + pbir; renames, moves, additions, removals, validation order
references/format-visuals.md: formatting workflow, property discovery, glob patterns, --where predicates
references/conditional-formatting.md: CF types, measure-based CF, copy/remove/update/convert
references/reference-lines.md: reference-line entries on chart axes; pbir visuals reference-line and styling via pbir set
references/error-bars.md: error bars and bullet markers on chart visuals; pbir visuals error-bars and styling via pbir set
references/modifying-theme.md: theme inspection, colors, text classes, fonts
references/apply-theme.md: applying/copying/saving theme templates
references/converting-reports.md: format conversion, thick/thin split, merge, rebind
references/thin-report-measures.md: extension measures for CF, conditional rendering
references/visual-calculations.md: visual calculations (RUNNINGSUM, RANK, etc.)
references/filters.md: filter types (Categorical, TopN, Advanced, RelativeDate), management, pane styling
references/bookmarks.md: bookmark management, copying, button references
references/audit-report.md: report quality audit checklist
references/bpa.md: Best Practice Analyzer; running rules, applying safe fixes, managing the rule set
references/vague-prompts.md: handling underspecified prompts; targeted questions, sensible defaults
references/property-catalogue.md: offline property index (49 types, 15 containers, 12,600+ slots)
references/visualTypes/*.md: per-visual-type design rules, CLI commands, and best practices
examples/visuals/default/*.json: read-only examples of minimal visual structures with theme defaults
examples/visuals/formatted/*.json: read-only examples of formatting, CF, filters, and advanced patterns; reproduce them with CLI commands, never by copying JSON into a report
```


## Related Skills

- `pbi-report-design`: Use for design best practices and guidelines for reports
- `pbip-format`: Use for understanding PBIP structure, not for bypassing `pbir` report mutations, except on Linux where `pbir` cannot be installed and hand-authoring is the only route
- `create-pbi-report`: Use to follow step-by-step instructions for creating new reports
