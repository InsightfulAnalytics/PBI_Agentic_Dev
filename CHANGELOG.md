# Changelog

Releases of this fork, newest first. The version tracks the upstream release last harvested;
the git tag and GitHub Release are named `fork-v<version>`, because upstream's own `v<version>`
tags share the namespace. Upstream's notes are in [release-notes/](release-notes/), and the full
list of fork modifications is in [FORK-CHANGES.md](FORK-CHANGES.md).

To update an installed copy:

```powershell
claude plugin marketplace update power-bi-agentic-dev
claude plugin update <plugin>@power-bi-agentic-dev
```

## 26.40.3 (2026-10-07)

First release since 26.26 (2026-09-07). Every plugin moves to 26.40.3.

### Watch for

- `reports`: the `claude-design-handoff` skill is retired. Design handoffs (a Claude Design URL or
  ZIP) now route to `pbi-report-design`.
- `fabric-data-app`: the pane command is `/fabric-app-pane`.
- `pbir-cli` is documented against pbir 0.9.32. `pbir setup`, the old `visuals cf` flags and
  `visuals format-field` / `format-state` are gone from the CLI (0.9.30); the skill keeps rewrite
  tables for old scripts.
- `te-cli` and `semantic-model` use the current `te` syntax: `--model` for the model, `-p Name=Value`
  for properties, and every mutation is a dry run until `--save` (or `--execute` for deploy and
  refresh).
- `pbi-desktop`: the compatibility-level auto-upgrade hook is opt-in and asks before it runs.

### New

- `pbip`: a SessionStart hook prints the skill routing table and the Power BI Desktop rules in
  every session where the plugin is enabled. Toggle it with `session_context` in
  `plugins/pbip/hooks/config.yaml`.
- `reports`: `pbi-plan` (a multi-session build plan as numbered tickets with an HTML plan board),
  `desktop-screen-capture`, and `close-plan.py` for sweeping a report's tooltip pages and
  navigation.
- `fabric-cli`: capacity-unit cost and capacity impact estimates before an operation, workspace
  task flows (`task_flow.py`), and the `/fabric-pane` sidebar. `reports` gains `/report-pane`.
- `fabric-admin`: the `fabric-capacity` skill, for Capacity Metrics queries and starting or pausing
  a capacity.
- `fabric-data-app`: a new plugin holding the data app pane.
- `tabular-editor`: registers the Tabular Editor 3 MCP server (3.27.0+, with Tools > MCP Server
  started in TE3).
- `svg-visuals`: a template matrix of which SVG pattern fits which host, with the verified PBIR
  wiring for image visuals, new card images and per-button slicer images.
- 22 report themes in `useful-stuff/themes/` (from upstream's Omarchy ports), set to Consolas.
- Copilot CLI hook wiring for `pbip`, `pbi-desktop` and `paginated-reports`, so a Windows machine
  without Git Bash on `PATH` no longer has every tool call denied.

### Changed

- `dax-standard`:
  - A measure's VARs stay in one flat list, with the flat form of each nested shape.
  - Tables are built in Power Query, not as DAX calculated tables, including how to convert one
    in TMDL.
  - A user-defined function change is proven only by `INFO.USERDEFINEDFUNCTIONS()`.
  - New reference: filter-context traps.
- `pbi-report-design`:
  - Storytelling rules: titles that answer the page's question, one accent per visual, and a
    closed chart vocabulary.
  - The insight test.
  - A visual's title goes in its own title and subtitle slots, never a textbox above it, with
    `find_title_textboxes.py` to find offenders.
- `create-pbi-report` `interactivity.md`: slicers always filter each other.
- New references for silent failures: PBIR render traps, Deneb traps, `pbir` CLI traps, Desktop
  UI Automation, consumer access and usage telemetry in the Service, data triage before planning,
  and synthetic demo datasets.
- `pbir-cli` adds references for reviewing a user's manual edits, table density and card
  references; `modifying-theme-json` adds style presets.
- Desktop 26.08+ applies external changes from a banner, so close-and-reopen is no longer the
  default after a disk edit.
- `deneb-visuals` reviewed for Deneb 2.0, and records Deneb's external-resource and data URI
  limits.

### Fixed

- PBIR sync groups: sync is `visual.syncGroup` on each copy of the slicer, not a `report.json`
  group.
- The bookmark `display` table listed a `"visible"` mode the schema rejects.
- `modifying-theme-json` greps for `"stylePreset"`, the key a visual actually writes.
- Hook and script fixes from upstream: `-Port` passed as real PowerShell arguments, UTF-8 stdin in
  hook runners, bearer tokens kept out of the process list, `refresh_model.py` failing on HTTP
  errors, `create_direct_lake_model` refusing to overwrite, and `execute_dax` keeping columns
  missing from the first row.
