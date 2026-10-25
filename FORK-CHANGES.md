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
- Harvested upstream 26.40.4 (2026-10-12) without `databricks-cli` and `goblin-mode`: the pane
  updates (taken whole, with upstream's removal of the pane unit tests), the new
  `organize-semantic-model` skill in place of `standardize-naming-conventions`, the `pbir-cli`
  doc fixes, the `fabric-cli` T-SQL route without the `fabric-sql` MCP, and the TE3 UI font-size
  script. `organize-semantic-model` names `dax-optimisation` where upstream names a `dax` skill
  the fork does not have, and its DAX passes (12 and 13) follow the `dax-standard` house style:
  `__` variables in place of upstream's `_`, the house layout instead of `FormatDax()`, a comment
  on every step, only the TE3 code actions that keep the table-first shape, and UDF bodies laid
  out like measures.
- Added an M naming rule to `semantic-models/power-query` (2026-10-13): steps, variables and
  functions are snake_case, so no reference needs `#"..."`, and an agent that meets a spaced name
  in existing M renames it with every reference. The skill's examples, those in its
  `references/{best-practices,validation}.md` and the `date-table` helper expressions follow it.
  So does the advice for an M expression that collides with a table name: `tmdl/SKILL.md`, the
  `pbip-validator` agent and `validate_pbip.py` now suggest `<name>_query` in place of
  `#"<Name> Query"`.
- Added M formatting to `semantic-models/power-query` (2026-10-13): M is laid out by Microsoft's
  MIT-licensed `powerquery-formatter` in a house layout. `formatter/format_m.js` runs it over `.pq`
  and `.m` files, stdin, and the M blocks in TMDL (shared expressions, M partitions, refresh-policy
  expressions), keeping fences and leaving DAX and multi-line text literals alone. On top of the
  formatter it uses 60-character lines, puts every `let` one binding per line, breaks a call or
  parameter list one item per line, lifts end-of-line comments onto their own line, ignores the
  source's record line breaks, and corrects three line-length estimates the formatter gets wrong.
  The skill's examples are its output, with their `--` comments corrected to M's `//`.
- Harvested part of upstream 26.40.5 to 26.40.7 (2026-10-18): the Fabric pane pins the workspaces
  Claude works in to the top of its tree, taken whole, and `fabric-cli/SKILL.md` takes upstream's
  plain-statement gotchas and first-use rule and drops its *When to use* section, keeping the
  fork's learnings block. The fork keeps the Microsoft Learn MCP server upstream removed; the
  skills that named the `mslearn` CLI as its fallback now name learn.microsoft.com instead.
  `dax-standard` states its reference rule (`Table[Column]`, the table quoted only where DAX
  requires it, measures as `[Measure]`) in place of upstream's always-quoted `'Table'[Column]`.
- Added "filter the dimension, not the fact" to `dax-standard` (2026-10-19): measures filter and
  group by the dimension column a fact relates to, never the fact's copy of it, with the slicer
  check before moving an existing filter, the exceptions and a review checklist in the new
  `references/filter-dimensions-not-facts.md`. Measures assume referential integrity: a missing
  dimension key is tested with a query and proven, never assumed or hedged against. A dimension-like column that sits only on the fact
  gets a proposed dimension, built in the source or Power Query once the user agrees, and every
  reply says which column carries the filter. The skill's examples that filtered a fact attribute
  (`method.md`, `core-functions.md`, `business-recipes.md`, `advanced-patterns.md`, the `Net Sales %`
  worked example) now filter the dimension.
- Switched off the `pbi-desktop` validation hooks (2026-10-23): `hooks/hooks.json` registers none
  and `hooks/config.yaml` sets `all_hooks_enabled: false`. Their `Bash` matchers never saw the
  PowerShell that runs TOM work on Windows, and they needed `jq` and a `tom_nuget` folder this
  machine never had, so they validated nothing while spawning bash on every matching Bash call.
  `connect-pbid/SKILL.md` and `hooks/README.md` say so.
- Took `powerbi-custom-visuals` out of the model's listing (2026-10-24):
  `disable-model-invocation: true` in its frontmatter. The maintainer no longer builds pbiviz
  visuals, so the global `powerbi-visuals-tools` is uninstalled and the plugin's `pbiviz` MCP server
  is denied in the maintainer's user settings. `/custom-visuals:powerbi-custom-visuals` still runs
  it. Plugin skills ignore `skillOverrides`, so a frontmatter line is the only switch.
- Cut the listing and the bodies a compaction truncates (2026-10-24). After a compaction an invoked
  skill is re-attached up to about 20,000 chars and the tail, usually the reference index, is
  dropped. Only fork-written text moved, and only into new fork-owned `references/` files, with one
  routing line left behind, so upstream's lines stay where a harvest expects them:
  - `dax-standard` 34,845 to 18,857 chars: `references/{flat-vars,house-style,number-formatting,tables-from-power-query}.md`,
    and *What cannot move into CALCULATE* appended to `references/calculate-and-performance.md`.
  - `deneb-visuals` 45,966 to 23,015: `references/{gotchas,editions-and-editor,expression-functions,interactivity-and-runtime-fields,field-parameters,images-and-external-resources}.md`.
    The rest is upstream text and the fork's edits to upstream lines; going lower means moving upstream text.
  - `performant-matrix` 21,933 to 17,895: `references/{consultation-block,gotchas}.md`.
    `deneb-pbir` 19,482 to 13,730: `references/audit-report.md`. `modifying-theme-json` 19,813 to
    18,419: `references/schema-and-docs.md`.
  - The 4,392-char boundary-rule block left `fabric-cli`, `connect-pbid` and `pbir-cli` for a
    `references/where-learnings-go.md` in each, with a one-line pointer in the body.
    `scripts/sync-boundary-rule.py`, `scripts/check-skill-hygiene.py` and the allow globs in
    `.github/denylist-patterns.txt` follow the copies there.
  - Descriptions of fork-owned skills cut to 400 chars or less: `dax-standard`, `deneb-pbir`,
    `performant-matrix`, `model-change`, `date-table`, `power-bi-theme`, `pbi-verify-loop`,
    `desktop-screen-capture`; `modifying-theme-json` too. `fabric-cli` is back on the fork's
    240-char description after the 26.40.5 harvest brought upstream's 607 back.
  - `disable-model-invocation: true` on `python-visuals`, `r-visuals` and the `audit-context`,
    `migrating-fabric-trial-capacities` and `pbi-plan` commands: nothing the maintainer runs
    routes to them by model invocation, and each still runs as a slash command.
  - `plugins/pbip/hooks/session-context.md` 3,540 to 2,991 chars: the header paragraph, the
    tenant-settings and paginated clauses and the tooltip line (which `pbir-cli` routes) are gone;
    the Desktop rules are unchanged.
  - `scripts/check-skill-hygiene.py` job 6 warns on a SKILL.md over 19,000 chars, a reference
    index that starts past char 19,000, and a description plus `when_to_use` over 400 chars
    (skipped for a `disable-model-invocation` skill), so a harvest cannot quietly undo this.

### Fork-owned files, for upstream harvest resolution

New files, so they merge at file granularity even though upstream owns the containing directory:

- `LEARNINGS.md`, `CHANGELOG.md`, `.devcontainer/**`
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
- `plugins/semantic-models/skills/dax-standard/references/{flat-vars,house-style,number-formatting,tables-from-power-query}.md`
- `plugins/custom-visuals/skills/deneb-visuals/references/{gotchas,editions-and-editor,expression-functions,interactivity-and-runtime-fields,field-parameters,images-and-external-resources}.md`
- `plugins/custom-visuals/skills/performant-matrix/references/{consultation-block,gotchas}.md`
  (the whole `performant-matrix` and `deneb-pbir` skills are fork-owned)
- `plugins/custom-visuals/skills/deneb-pbir/references/audit-report.md`
- `plugins/reports/skills/modifying-theme-json/references/schema-and-docs.md`
- `plugins/{fabric-cli/skills/fabric-cli,pbi-desktop/skills/connect-pbid,reports/skills/pbir-cli}/references/where-learnings-go.md`
- `plugins/semantic-models/skills/semantic-model/references/synthetic-datasets.md`
- `plugins/reports/skills/pbi-report-design/scripts/find_title_textboxes.py`
- `plugins/fabric-cli/skills/fabric-cli/references/{consumer-access.md,usage-and-lineage.md}`
- `plugins/semantic-models/skills/power-query/formatter/{format_m.js,package.json,package-lock.json}`
- `scripts/{bootstrap-agent-env.sh,record-learning.sh,check-skill-hygiene.py,sync-boundary-rule.py,denylist-add.py}`
- `.github/denylist-hashes.txt`, `.github/denylist-patterns.txt`

Modified upstream-authored files, which **will** conflict on a harvest:

- `.github/workflows/validate-plugins.yml` (widened path filters, added the hygiene and
  boundary-rule steps)
- The learnings instruction in `fabric-cli/SKILL.md`, `connect-pbid/SKILL.md` and
  `pbir-cli/SKILL.md`: a one-line pointer to the skill's `references/where-learnings-go.md`, which
  carries the `<!-- boundary-rule:begin -->` block. Keep the pointer in place of any learnings
  block upstream adds, and re-run `python scripts/sync-boundary-rule.py`.
- `fabric-cli/SKILL.md`'s 240-char `description`. Upstream's runs to 607; keep the fork's.
- The `disable-model-invocation: true` lines in `python-visuals/SKILL.md`, `r-visuals/SKILL.md`
  and `fabric-cli/commands/migrating-fabric-trial-capacities.md`. Keep them when taking upstream
  frontmatter changes.
- Bodies that diverge far beyond link edits (`git diff -w --ignore-cr-at-eol --numstat 97410b1 --
  "plugins/*/skills/*/SKILL.md"`, 2026-10-24): `modifying-theme-json` (+271/-84; upstream has since
  rewritten it CLI-only at 6,684 chars, so a harvest is a rewrite, not a merge), `pbip` (+151/-19),
  `power-query` (+144/-42), `deneb-visuals` (+108/-42, after the split above), `pbir-cli`
  (+103/-56), `tmdl` (+95/-51), `connect-pbid` (+72/-37), `pbi-report-design` (+62/-19),
  `create-pbi-report` (+51/-11), `fabric-cli` (+49/-20) and `svg-visuals` (+32/-6). Harvest these
  hunk by hunk.
- `plugins/pbip/hooks/{hooks.json,config.yaml,README.md}`: the `SessionStart` entry, the
  `session_context` toggle and its table row, and README's trigger column, which says Write and
  Edit only (upstream's says Bash too, but its `hooks.json` registers no Bash matcher). Keep them
  when taking upstream hook changes.
- `plugins/pbi-desktop/hooks/{hooks.json,config.yaml,README.md}` and the *Validation hooks* line in
  `connect-pbid/SKILL.md`: the hooks are off. Keep `"hooks": {}` when taking upstream hook changes.
- The `disable-model-invocation: true` line in `custom-visuals/skills/powerbi-custom-visuals/SKILL.md`.
  Keep it when taking upstream frontmatter changes.
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
- The `visualInteractions` type names (`DataFilter`, `HighlightFilter`, `NoFilter`, `Default`;
  upstream says `Filter` and `Highlight`, which break Desktop) in `pbir-format/SKILL.md`, its
  `references/{page,visual-json}.md`, `references/how-to/{convert-legacy-to-pbir,fix-broken-field-references}.md`
  and `scripts/convert_legacy_to_pbir.py`, which now converts legacy types 1 and 2 as well as 3.
  Keep the fork's lines until upstream uses the schema's names. Upstream's CLI-only rewrite
  (`42fd294`) deletes the script and the how-to text; taking it drops those hunks.
- The M naming and formatting rules: `power-query/SKILL.md` (the description's last trigger, the
  **Naming** and **Formatting** sections, the `format_m.js` reference line and every example) and
  the examples in its `references/{best-practices,validation}.md`; the name-collision advice in
  `tmdl/SKILL.md`, `agents/pbip-validator.agent.md` and `pbip/scripts/validate_pbip.py`. Keep the
  fork's snake_case names and formatter layout when taking upstream changes to these files, and
  the two `formatter/` lines in `.gitignore`.
- `organize-semantic-model/SKILL.md`: the `version:` line, `dax-optimisation` in the
  description, and passes 12 and 13, rewritten to defer to `dax-standard`; plus the body-comment
  line in its `references/udfs.md`. Keep the fork's versions.
- The docs-lookup line in the skills that fetch Microsoft Learn (`deneb-visuals`, `python-visuals`,
  `r-visuals`, `connect-pbid`, `pbip`, `pbir-format`, `tmdl`, `bpa-rules`, `c-sharp-scripting`,
  `te2-cli`, `te-docs`, `audit-tenant-settings`, `fabric-cli` and its `references/{admin,reference}.md`),
  plus `fabric-cli/.mcp.json`: the fork names the Microsoft Learn MCP first. Keep the fork's lines.
- `useful-stuff/themes/*.json` (every font line) and the font note in
  `useful-stuff/themes/README.md`. After taking upstream changes to a theme, replace the
  `'JetBrainsMono Nerd Font', 'JetBrains Mono', Consolas, monospace` stack with `Consolas` again.

The defect fixes in the `fix: correct skill content that currently makes agents fail` commit touch
upstream-authored content and should be offered upstream, which turns a future harvest of those
hunks into a no-op instead of a conflict.

Notice dated 2026-07-29.
