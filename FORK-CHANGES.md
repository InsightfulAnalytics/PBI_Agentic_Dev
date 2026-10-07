# Fork changes

Prominent notice of modifications relative to the upstream project, per GPL-3.0 §5(a).

This repository is a fork of [`data-goblin/power-bi-agentic-development`](https://github.com/data-goblin/power-bi-agentic-development) by Kurt Buhler. Known modifications relative to upstream:

- Renamed the marketplace from `power-bi-agentic-development` to `power-bi-agentic-dev` so both can coexist in Claude Code.
- Removed some upstream-adjacent skills.
- Added fork-maintainer skills to existing plugins (authored by the fork maintainer, not the upstream author):
  - `reports/pbi-verify-loop`
  - `reports/power-bi-theme`
  - `reports/pbi-plan` — plan a multi-session report or model build as a ticketed map with a
    live HTML plan board. Its ticket shape and frontier rule are adapted from Matt Pocock's
    MIT-licensed `wayfinder` / `to-tickets` skills; see [ATTRIBUTIONS.md](ATTRIBUTIONS.md)
  - `reports/workout-wednesday`
  - `custom-visuals/deneb-pbir`
  - `custom-visuals/performant-matrix`
  - `semantic-models/date-table` — bundles third-party community code (see [ATTRIBUTIONS.md](ATTRIBUTIONS.md))
  - `semantic-models/dax-standard`
- Added `examples/pl-switch-lab/`, an original sample Power BI project: one financial statement
  built nine ways and measured. Not derived from upstream, and licensed MIT rather than GPL-3.0
  (see its own LICENSE). Its semantic model redistributes two pieces of community code with
  attribution kept inline; see [ATTRIBUTIONS.md](ATTRIBUTIONS.md).
- Assorted fixes and personalization, documented in [PERSONALIZING.md](PERSONALIZING.md).
- Added an OpenAI Codex compatibility layer under `codex/` (installer, AGENTS.md adapter, ported command-skills); `plugins/` content is unchanged by it.
- Migrated the fork maintainer's local Power BI environment notes into the skills that own each
  topic (TMDL and PBIR authoring gotchas, the `fab` CLI, the `pbir` CLI, the Power BI Desktop
  process lifecycle, and ADOMD assembly discovery), so the knowledge ships with the plugins instead
  of living in one machine's user memory. Also corrected skill content those notes contradicted.
- Added a Codespaces bootstrap (`.devcontainer/`, `scripts/bootstrap-agent-env.sh`) and an in-repo
  learning-capture route (`LEARNINGS.md`, `scripts/record-learning.sh`,
  `scripts/check-skill-hygiene.py`, `scripts/sync-boundary-rule.py`).
- Updated the Deneb skills and tooling for Deneb 2.0 with 1.9 compatibility (2026-09-08):
  `custom-visuals/deneb-visuals` (new `references/deneb-2-migration.md`, the 2.0 properties,
  supporting fields, field parameters and template usermeta v2), `custom-visuals/deneb-pbir`
  (`audit` and `migrate` commands, renderer shims, the 2.0 Vega bundle), the `reports/deneb-reviewer`
  agent and the `performant-matrix` grid reference. Fork-original work; upstream's Deneb skill had
  not been updated for 2.0 at that date.
- Set the Omarchy report themes in `useful-stuff/themes/` (upstream 26.31.4 and 26.31.5) to
  Consolas, a font from Power BI's own list, in place of upstream's JetBrains Mono stack
  (2026-09-25).
- Moved the rest of the fork maintainer's Power BI notes out of per-machine memory and into the
  plugins (2026-10-03): a `pbip` SessionStart hook (`hooks/session-context.sh`) that prints the
  skill routing table and the Power BI Desktop rules in every session where `pbip` is enabled, and
  new references for silent failures: PBIR render traps, Deneb traps, `pbir` CLI traps, DAX
  filter-context traps, Desktop UI Automation, consumer access and usage telemetry in the Service,
  data triage before planning, and synthetic demo datasets. Corrected the bookmark `display` table,
  which listed a `"visible"` mode the schema rejects.
- Registered the Tabular Editor 3 MCP server (3.27.0+, HTTP on `127.0.0.1:42100`) in the
  `tabular-editor` plugin's `.mcp.json`, so it loads only where that plugin is enabled
  (2026-09-26). It connects only while TE3 is open with Tools > MCP Server started.
- Promoted the learnings from a UDF-heavy report build (2026-10-03): a DAX user-defined function
  that calls a newly added function can fail to load in Power BI Desktop while `te validate` passes
  it, so a `functions.tmdl` change is proven only by `INFO.USERDEFINEDFUNCTIONS()` (`tmdl`
  authoring gotchas, `model-change` step 5, `dax-standard`); Tabular Editor 3's false error on
  `TABLE EXPR` before 3.24 (`te-docs`); a visual's title and subtitle go in its container slots,
  never a textbox above it (`pbi-report-design`, `pbir-format`, `deneb-visuals`), with a
  `find_title_textboxes.py` check; and the `pbir` title commands writing apostrophes undoubled
  (`pbir-cli` CLI traps). Corrected the subtitle font size in `page-titles.md` from 11 to the
  canon's 12pt floor, and a `pbir visuals format -p title.text` example the CLI rejects.
- Harvested upstream 26.40.0 to 26.40.2 (2026-10-05) without its `databricks-cli` plugin.
  `pbir-cli/SKILL.md` keeps the fork's `pbi-verify-loop` pointer and Linux route under "Desktop
  Integration" in place of upstream's condensed paragraph. The fork's
  `modifying-theme-json/references/advanced-theme-features.md` now greps for `"stylePreset"`, the key
  a visual actually writes, in place of `"styleName"`. Upstream's new `fabric-cli` `task_flow.py`
  resolves `az` with `shutil.which`, as the fork's other token scripts already do, so it runs on
  Windows.
- Harvested upstream 26.40.3 (2026-10-05): the pane openers in `fabric-cli`, `reports` and
  `fabric-data-app` (shared `hooks/open.ts`, which passes Windows paths and URLs literally to
  ShellExecute and reports launch failures), taken whole since the fork never edits pane code.
  The data app pane command is now `/fabric-app-pane`. `databricks-cli` and `goblin-mode` stay out.
- Promoted three rules from a production model and report build (2026-10-07): `dax-standard` keeps
  a measure's VARs flat (no `VAR … RETURN` block inside a function argument, with the flat form of
  each nested shape and a DAX query that proves a flattened measure unchanged), and builds tables
  in Power Query rather than as DAX calculated tables (with the TMDL conversion and the `cache.abf`
  step it needs); `create-pbi-report` `references/interactivity.md` makes slicers always filter
  each other, with a pointer from `pbi-report-design`. Corrected *Sync groups* in the same file:
  in PBIR, sync is `visual.syncGroup` on each copy of the slicer, not a `report.json` group.

### Fork-owned files, for upstream harvest resolution

New files, so they merge at file granularity even though upstream owns the containing directory:

- `LEARNINGS.md`, `.devcontainer/**`
- `plugins/tabular-editor/.mcp.json`
- `plugins/pbip/skills/tmdl/references/authoring-gotchas.md`
- `plugins/pbi-desktop/skills/connect-pbid/references/desktop-lifecycle.md`
- `plugins/pbi-desktop/skills/connect-pbid/references/assembly-discovery.md`
- `plugins/pbi-desktop/skills/connect-pbid/references/desktop-ui-automation.md`
- `plugins/pbip/hooks/session-context.{md,sh}`
- `plugins/pbip/skills/pbir-format/references/silent-render-traps.md`
- `plugins/custom-visuals/skills/deneb-visuals/references/silent-traps.md`
- `plugins/reports/skills/pbir-cli/references/cli-traps.md`
- `plugins/reports/skills/pbi-plan/references/data-triage.md`
- `plugins/semantic-models/skills/dax-standard/references/filter-context-traps.md`
- `plugins/semantic-models/skills/semantic-model/references/synthetic-datasets.md`
- `plugins/reports/skills/pbi-report-design/scripts/find_title_textboxes.py`
- `plugins/fabric-cli/skills/fabric-cli/references/{consumer-access.md,usage-and-lineage.md}`
- `scripts/{bootstrap-agent-env.sh,record-learning.sh,check-skill-hygiene.py,sync-boundary-rule.py,denylist-add.py}`
- `.github/denylist-hashes.txt`, `.github/denylist-patterns.txt`

Modified upstream-authored files, which **will** conflict on a harvest:

- `.github/workflows/validate-plugins.yml` (widened path filters, added the hygiene and
  boundary-rule steps)
- The learnings instruction in `fabric-cli/SKILL.md`, `connect-pbid/SKILL.md` and
  `pbir-cli/SKILL.md`, each now carrying a `<!-- boundary-rule:begin -->` block. Keep the fork's
  version and re-run `python scripts/sync-boundary-rule.py`.
- `plugins/pbip/hooks/{hooks.json,config.yaml,README.md}`: the `SessionStart` entry, the
  `session_context` toggle and its table row. Keep them when taking upstream hook changes.
- One-line links to the fork-owned references above, added to upstream-authored files:
  `pbir-format/SKILL.md` and its `references/{validation,page,bookmarks}.md`, `pbip/SKILL.md`
  (one project per folder, fork step 6), `deneb-visuals/SKILL.md` (also the native-versus-Deneb
  split, the apostrophe rule and best practice 11 on titles), `pbir-cli/SKILL.md`, `connect-pbid/SKILL.md`, `fabric-cli/SKILL.md`, `semantic-model/SKILL.md`,
  `pbi-report-design/SKILL.md` (two habits after the insight test, the visual-title clause in core
  rule 2, the subtitle floor and the script line), `pbi-report-design/references/{page-titles,quality-gate}.md`
  (the rewritten visual title section and one gate bullet), `pbir-format/references/{textbox,visual-container-formatting}.md`,
  `pbir-cli/references/add-new-visual.md`, `tmdl/SKILL.md` (two pointers to the UDF load trap),
  `te-docs/SKILL.md` (the TE3 diagnostics section and two trigger phrases), and the appended sections in
  `power-query/references/best-practices.md`, `fabric-cli/references/dataflows.md`,
  `fabric-cli/references/warehouses.md` and `fabric-cli/references/reports.md` (the ExportTo 403
  note). Small conflicts; keep both sides.
- `create-pbi-report/references/interactivity.md`: the *Sync groups* rewrite, the new *Slicers
  filter each other* section, and the slicer notes in the query-reduction pitfalls and wiring
  step 1. Plus the matching *Slicers* bullet in `pbi-report-design/SKILL.md`. Keep the fork's
  version of *Sync groups* unless upstream fixes the `report.json` claim itself.
- `useful-stuff/themes/*.json` (every font line) and the font note in
  `useful-stuff/themes/README.md`. After taking upstream changes to a theme, replace the
  `'JetBrainsMono Nerd Font', 'JetBrains Mono', Consolas, monospace` stack with `Consolas` again.

The defect fixes in the `fix: correct skill content that currently makes agents fail` commit touch
upstream-authored content and should be offered upstream, which turns a future harvest of those
hunks into a no-op instead of a conflict.

Notice dated 2026-07-29.
