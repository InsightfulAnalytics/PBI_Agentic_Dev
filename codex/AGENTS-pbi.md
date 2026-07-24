# Power BI / Fabric agentic development (power-bi-agentic-dev)

Skills for Power BI and Microsoft Fabric work are installed at `{{SKILLS_DIR}}`.
They come from the Claude Code plugin marketplace cloned at `{{REPO}}` — treat that
clone as the runtime store: bundled scripts, binaries, theme libraries, and reviewer
checklists live there and are referenced by absolute path below.

## Skill routing

Codex should auto-activate these from their descriptions; this table is the backstop
index. Invoke explicitly with `$<name>` when a match is obvious.

| Area | Skill | Use when |
|---|---|---|
| Model | `semantic-model` | Any semantic model/dataset work: design, build, measures, relationships, RLS, calc groups, review, audit. Drives `te` CLI first, then TOM, then TMDL |
| Model | `date-table` | Add the standard 58-column DimDate + `Dates Selected` title measure to a PBIP model |
| Model | `dax` | DAX performance only: slow measures, server timings, anti-patterns (not authoring) |
| Model | `power-query` | M expressions, partition queries, query folding, testing/previewing partitions |
| Model | `refresh-semantic-model` | Refresh a model/dataset; schedules, refresh troubleshooting |
| Model | `lineage-analysis` | Downstream reports, impact analysis, cross-workspace lineage |
| Model | `standardize-naming-conventions` | Rename/standardize model object names |
| PBIP | `pbip` | PBIP project structure, PBIX→PBIP conversion, cascade renames, forking |
| PBIP | `tmdl` | Direct TMDL file authoring/editing, TMDL syntax, BIM→TMDL |
| PBIP | `pbir-format` | PBIR JSON reference: visual.json, report.json, themes, filters, extension measures, bookmarks |
| Report | `pbir-cli` | Create/explore/format/validate/publish reports via the `pbir` CLI; Desktop canvas refresh + screenshots |
| Report | `create-pbi-report` | End-to-end new-report build workflow (discovery → pages → visuals → publish) |
| Report | `pbi-report-design` | Design decisions: hierarchy, layout, color, chart selection, accessibility |
| Report | `pbi-verify-loop` | Visually verify report edits: refresh → settle → screenshot (→ mockup diff) |
| Report | `power-bi-theme` | Browse/compare/apply preset themes from the bundled gallery |
| Report | `modifying-theme-json` | Design, edit, enforce, audit report theme JSON |
| Report | `review-report` | Review report quality, usage metrics, best practices |
| Visuals | `deneb-visuals` | Author Deneb Vega/Vega-Lite specs, interactivity, theme integration |
| Visuals | `deneb-pbir` | Extract/embed/offline-render a Deneb spec in visual.json |
| Visuals | `python-visuals` / `r-visuals` / `svg-visuals` | Python (matplotlib), R (ggplot2), or SVG-measure visuals in reports |
| Visuals | `powerbi-custom-visuals` | Develop/build/package .pbiviz custom visuals |
| Desktop | `connect-pbid` | TOM/ADOMD against a running Power BI Desktop: DAX queries, model metadata edits, Desktop Bridge reload/screenshot |
| TE | `te-cli` | Cross-platform Tabular Editor CLI (`te`, preview) |
| TE | `te2-cli` | Tabular Editor 2 CLI (`TabularEditor.exe`): deploy, script, BPA, CI/CD |
| TE | `c-sharp-scripting` | C# scripts/macros against semantic models (TE2/TE3) |
| TE | `bpa-rules` | Author Best Practice Analyzer rules (guided discovery + Dynamic LINQ) |
| TE | `te-docs` | Tabular Editor docs search; TE3 config files (.tmuo, Preferences.json, Layouts.json) |
| Fabric | `fabric-cli` | Fabric CLI (`fab`) for any remote Power BI Service / Fabric operation |
| Fabric | `audit-tenant-settings` | Audit Fabric/Power BI tenant settings, delegated overrides, security groups |
| Fabric | `executing-spark` | Run Python/PySpark on Fabric Spark via Livy (no notebook artifact) |
| Fabric | `using-duckdb` | Query lakehouse/warehouse Delta data with DuckDB |
| RDL | `paginated-report` | Author, validate, publish, render paginated (RDL) reports |
| Task | `audit-context` | Review/critique AGENTS.md, CLAUDE.md, memory and context files |
| Task | `migrating-fabric-trial-capacities` | Migrate workspaces from trial capacity to a production capacity |
| Task | `suggest-rule` | Generate a BPA rule from a description or model analysis |

Not installed for Codex: `claude-design-handoff` (bound to Anthropic's Claude Design API).

## Reading the skills' Claude Code vocabulary

These skills were written for Claude Code. Translate as follows:

- **`plugin:skill` references** (e.g. "use the `pbip:tmdl` skill", `reports:pbir-cli`) → the
  installed skill named after the colon (`tmdl`, `pbir-cli`).
- **"Dispatch/invoke the X agent" or "subagent"** → there are no subagents here. Read the
  agent definition below and perform its review yourself, inline, as a checklist:

  | Agent | Checklist file |
  |---|---|
  | deneb-reviewer | `{{REPO}}/plugins/reports/agents/deneb-reviewer.agent.md` |
  | python-reviewer | `{{REPO}}/plugins/reports/agents/python-reviewer.agent.md` |
  | r-reviewer | `{{REPO}}/plugins/reports/agents/r-reviewer.agent.md` |
  | svg-reviewer | `{{REPO}}/plugins/reports/agents/svg-reviewer.agent.md` |
  | pbip-validator | `{{REPO}}/plugins/pbip/agents/pbip-validator.agent.md` |
  | semantic-model-auditor | `{{REPO}}/plugins/semantic-models/agents/semantic-model-auditor.agent.md` |
  | query-listener | `{{REPO}}/plugins/pbi-desktop/agents/query-listener.agent.md` |
  | bpa-expression-helper | `{{REPO}}/plugins/tabular-editor/agents/bpa-expression-helper.agent.md` |

- **`AskUserQuestion`** → ask the user the questions directly in chat (numbered options)
  and wait for answers before proceeding.
- **`${CLAUDE_PLUGIN_ROOT}`** → the plugin's root in the clone: `{{REPO}}/plugins/<plugin>`.
  (Copy-mode installs already have this rewritten; junction installs read it literally.)
- **`${CLAUDE_PROJECT_DIR}`** → the current project/workspace root.
- **"/skill-name" slash commands** → `$skill-name` mentions in Codex.
- **Hook references** ("hooks will validate…") → hooks do not run under Codex; apply the
  validation rules below yourself.

## Validation rules (replaces Claude Code auto-hooks — treat as mandatory)

In Claude Code these run automatically after every edit. Under Codex **you must run them
yourself** after changing matching files, and fix what they report:

| After changing | Run |
|---|---|
| `*.tmdl` | `{{REPO}}/plugins/pbip/hooks/bin/tmdl-validate-windows-x64.exe "<file>"` (macOS: `tmdl-validate-darwin-arm64`; Linux: `tmdl-validate-linux-x64`) |
| anything under `*.Report/` | `pbir validate "<Name>.Report"` (pbir CLI), or full project: `python "{{REPO}}/plugins/pbip/skills/pbip/scripts/validate_pbip.py" "<project dir>"` |
| `definition.pbir` | `python "{{REPO}}/plugins/pbip/skills/pbip/scripts/validate_pbip.py" "<project dir>"` (checks byPath/byConnection binding) |
| `*.rdl` | `python "{{REPO}}/plugins/paginated-reports/skills/paginated-report/scripts/validate_rdl.py" "<file>"` |
| TOM model changes via connect-pbid (after SaveChanges) | `powershell -File "{{REPO}}/plugins/pbi-desktop/hooks/check-referential-integrity.ps1" -Port <AS port>` |

The tmdl-validate binaries are unsigned; corporate AV may flag them (they are a small
offline Rust linter — see `{{REPO}}/plugins/pbip/hooks/README.md`). If unavailable, fall
back to opening the project in Power BI Desktop to surface TMDL errors.

## Tool prerequisites

Skills assume these CLIs; install on first need:

| Tool | Install | Used by |
|---|---|---|
| `pbir` | `pip install pbir-cli` | pbir-cli, create-pbi-report, themes, verify-loop |
| `fab` | `pip install ms-fabric-cli` (or `uv tool install`) | fabric-cli, fabric-admin, refresh, lineage |
| `te` | see `{{REPO}}/plugins/tabular-editor/skills/te-cli/references/get-te-cli.md` | semantic-model, te-cli |
| `TabularEditor.exe` | tabulareditor.com (TE2 free) | te2-cli, c-sharp-scripting |
| `pbiviz` | `npm i -g powerbi-visuals-tools` | powerbi-custom-visuals |
| `python` + `uv` | python.org / astral.sh | validators, audit-tenant-settings, gallery scripts |
| `node`/`npx` | nodejs.org | deneb-pbir renderer, pbiviz |
| `jq` | winget/brew | some helper scripts |
| PowerShell 5+ | ships with Windows | connect-pbid (TOM/ADOMD auto-downloaded on first use) |

## Windows console note

`fab` and `pbir` print Unicode glyphs that break on cp1252 consoles. Before running them
in a bash-style shell: `export PYTHONIOENCODING=utf-8 PYTHONUTF8=1` (PowerShell:
`$env:PYTHONIOENCODING='utf-8'; $env:PYTHONUTF8='1'`).
