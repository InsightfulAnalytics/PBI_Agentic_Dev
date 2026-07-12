<h1 align="center">power-bi-agentic-development-tim</h1>

<p align="center">
  A personalized fork of Kurt Buhler's Power BI &amp; Microsoft Fabric skills marketplace <br></br>
  <i>Teach AI agents like Claude Code or GitHub Copilot to work with Power BI and Microsoft Fabric</i>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-26.25-blue" alt="Version">
  <img src="https://img.shields.io/badge/Power_BI-F2C811?logo=powerbi&logoColor=000" alt="Power BI">
  <img src="https://img.shields.io/badge/Microsoft_Fabric-008272" alt="Microsoft Fabric">
  <img src="https://img.shields.io/badge/Tabular_Editor-2E7D32" alt="Tabular Editor">
  <img src="https://img.shields.io/badge/license-GPL--3.0-green" alt="License">
</p>

> [!NOTE]
> This is **Tim's personalized fork** of [`data-goblin/power-bi-agentic-development`](https://github.com/data-goblin/power-bi-agentic-development), renamed to `power-bi-agentic-development-tim` so it can coexist with the original. It carries the upstream plugins plus additional personal skills, and tracks Kurt's releases selectively rather than following his weekly cadence. Full credit for the original work goes to Kurt Buhler — see [Attribution](#attribution).

---

### What is agentic development?

- *Agentic development* is when you use AI agents to help build, manage, and optimize artifacts and software — semantic models, reports, and everything around them (workspaces, deployment pipelines, and processes).
- A *marketplace* hosts *plugins* you can install. A plugin is a bundle of resources that help coding agents perform better: skills, subagents, hooks, and MCP servers focused on a topic or task.
- This marketplace is focused on making your agent work well with **Power BI and Fabric** — Power BI skills, Fabric skills, subagents, and hooks for coding agents.

## Installation

Add the marketplace in Claude Code — run this in the terminal:

```bash
claude plugin marketplace add InsightfulAnalytics/PBI_Agentic_Dev
```

This registers the marketplace under the name **`power-bi-agentic-development-tim`** (from the repo's `.claude-plugin/marketplace.json`). Install commands below reference that name.

### Claude Code

After adding the marketplace, install plugins interactively via `/plugin` → **Marketplaces** → select `power-bi-agentic-development-tim` → install the plugins you want. You can also enable auto-update per marketplace there.

Or install from the command line:

```bash
claude plugin install semantic-models@power-bi-agentic-development-tim
claude plugin install reports@power-bi-agentic-development-tim
claude plugin install pbip@power-bi-agentic-development-tim
claude plugin install custom-visuals@power-bi-agentic-development-tim
claude plugin install tabular-editor@power-bi-agentic-development-tim
claude plugin install pbi-desktop@power-bi-agentic-development-tim
claude plugin install fabric-cli@power-bi-agentic-development-tim
claude plugin install fabric-admin@power-bi-agentic-development-tim
claude plugin install paginated-reports@power-bi-agentic-development-tim
claude plugin install etl@power-bi-agentic-development-tim
```

Verify what's installed with `claude plugin list`, and inspect a plugin's contents and token cost with `claude plugin details <plugin>`.

### Copilot CLI

The standalone [Copilot CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli) supports plugin installation from GitHub repos. Copilot CLI reads the same `.claude-plugin/marketplace.json` manifest this repo uses, so the marketplace and child-plugin layout works without modification.

<details>
<summary><strong>Windows long paths</strong></summary>

TMDL files can produce repository-relative paths over 260 characters. Windows' legacy MAX_PATH blocks `git clone` from writing them unless long path support is enabled at both the OS and git level. Without this, `copilot plugin install` aborts with `Filename too long`.

See [`useful-stuff/agent-scripts/enable-windows-longpaths.ps1`](useful-stuff/agent-scripts/enable-windows-longpaths.ps1) for an example script you can run from an elevated PowerShell session to enable long paths (a reboot is recommended after the registry change). This is a Windows OS limitation, documented at [Maximum Path Length Limitation](https://learn.microsoft.com/en-us/windows/win32/fileio/maximum-file-path-limitation).

Also set the git-level flag:

```powershell
git config --system core.longpaths true
```

</details>

<details>
<summary><strong>Additional installation instructions (Copilot CLI)</strong></summary>

This repository is an [Anthropic-format plugin marketplace](https://code.claude.com/docs/en/plugin-marketplaces) (a set of plugins), not a single distributable plugin, so the root `.claude-plugin/` contains only `marketplace.json`. Two documented install paths work:

**1. Register the marketplace once, then install named child plugins:**

```bash
copilot plugin marketplace add InsightfulAnalytics/PBI_Agentic_Dev
copilot plugin install tabular-editor@power-bi-agentic-development-tim
```

**2. Or install a single plugin directly from its subdirectory, no marketplace registration needed:**

```bash
copilot plugin install InsightfulAnalytics/PBI_Agentic_Dev:plugins/pbip
```

Both forms are documented in the [Copilot CLI plugin reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-plugin-reference) and the [plugins how-to](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/plugins-finding-installing). Inside an interactive Copilot session, `/plugin install PLUGIN-NAME@power-bi-agentic-development-tim` is the equivalent of (1). The bare `copilot plugin install InsightfulAnalytics/PBI_Agentic_Dev` (no qualifier) will not install anything useful, because the root is a marketplace catalog, not a plugin.

</details>

<details>
<summary><strong>Verify installation in Copilot CLI</strong></summary>

Inside Copilot CLI:

```
/env                    # Loaded instructions, MCP servers, skills, agents, plugins, LSPs, extensions
/plugin list            # Installed plugins
/skills list            # Available skills
/skills info pbip       # Details for a specific skill
/agent                  # Browse installed agents
```

</details>

<details>
<summary><strong>Compatibility notes</strong></summary>

- **Skills** load identically; Copilot CLI reads `skills/<name>/SKILL.md`.
- **Agents** use the `*.agent.md` extension required by Copilot CLI's documented convention. Claude Code matches any `*.md` file in `agents/`, so the dual extension works in both tools.
- **MCP servers** load from `.mcp.json` (plugin root) or `.github/mcp.json`. The plugins in this repo do not currently ship MCP servers.
- **Hooks** are registered via `hooks.json` and reference scripts using `${CLAUDE_PLUGIN_ROOT}`. Copilot CLI **≥ 1.0.26** (2026-04-14) sets `CLAUDE_PLUGIN_ROOT` for plugin hooks ([changelog](https://github.com/github/copilot-cli/blob/main/changelog.md)); older builds do not, which causes hook commands to resolve to broken paths. Run `copilot update` if hooks fail to fire. Native Windows bash users may also hit a separate path-format bug tracked upstream at [claude-code#11984](https://github.com/anthropics/claude-code/issues/11984).

</details>

## Overview

The repo contains **skills**, **agents**, and **hooks**.

- **Skills** teach agents domain knowledge and workflows. They activate automatically based on task context, or can be invoked manually with `/skill-name`. In Claude Code, skills and commands have coalesced; commands are simply more prescriptive skill workflows.
- **Agents** are autonomous subprocesses that handle complex, multi-step tasks independently; typically used for review and validation.
- **Hooks** run automatically after tool use to validate files and catch errors early. They are deterministic — they fire when a specific pattern is matched, not by LLM judgment.

Hook checks can be individually toggled via config files. Set any check to `false` to disable it:
- `plugins/pbip/hooks/config.yaml` — PBIR, TMDL, and report-binding validation
- `plugins/pbi-desktop/hooks/config.yaml` — DAX references, measure metadata, referential integrity, metadata cache
- `plugins/paginated-reports/hooks/config.yaml` — RDL validation

### Available plugins

> [!WARNING]
> Don't install every plugin. Each skill competes for the agent's attention and context window, so install a plugin only when you need it and remove it when you don't. Prefer installing plugins scoped to a project rather than to your user, so each project carries only the skills it actually uses.

<details>
<summary>📊 <strong>semantic-models</strong> &ensp; DAX, Power Query, naming, lineage, refresh, and model auditing</summary>

| Type | Name | Description |
|------|------|-------------|
| Skill | [`semantic-model`](plugins/semantic-models/skills/semantic-model/) | Design, build, refresh, and review semantic models through a `te`-first tool cascade |
| Skill | [`dax`](plugins/semantic-models/skills/dax/) | Debug and optimize DAX performance (server timings, anti-patterns, tuning) |
| Skill | [`dax-no-calculate`](plugins/semantic-models/skills/dax-no-calculate/) | Author readable DAX in the "No CALCULATE" (*DAX For Humans*) style |
| Skill | [`power-query`](plugins/semantic-models/skills/power-query/) | Write M expressions, debug query folding, execute M locally or via Fabric API |
| Skill | [`standardize-naming-conventions`](plugins/semantic-models/skills/standardize-naming-conventions/) | Audit and standardize naming conventions in semantic models |
| Skill | [`refresh-semantic-model`](plugins/semantic-models/skills/refresh-semantic-model/) | Trigger or troubleshoot refreshes |
| Skill | [`lineage-analysis`](plugins/semantic-models/skills/lineage-analysis/) | Trace downstream reports from a semantic model across workspaces |
| Agent | [`semantic-model-auditor`](plugins/semantic-models/agents/semantic-model-auditor.agent.md) | Audit semantic models for quality, memory, DAX, and design issues |

</details>

<details>
<summary>📈 <strong>reports</strong> &ensp; Report authoring, themes, visual verification, design, and review</summary>

| Type | Name | Description |
|------|------|-------------|
| Skill | [`pbir-cli`](plugins/reports/skills/pbir-cli/) | Programmatic report manipulation via the [`pbir` CLI](https://github.com/maxanatsko/pbir.tools), including live Power BI Desktop refresh and page screenshots |
| Skill | [`create-pbi-report`](plugins/reports/skills/create-pbi-report/) | End-to-end workflow for building a report from scratch with the pbir CLI |
| Skill | [`pbi-verify-loop`](plugins/reports/skills/pbi-verify-loop/) | Refresh → settle → screenshot loop to visually verify report edits (optional mockup diff) |
| Skill | [`power-bi-theme`](plugins/reports/skills/power-bi-theme/) | Browse a preset-theme gallery and apply a chosen theme to a report |
| Skill | [`modifying-theme-json`](plugins/reports/skills/modifying-theme-json/) | Edit, enforce, audit, and re-theme report theme JSON |
| Skill | [`claude-design-handoff`](plugins/reports/skills/claude-design-handoff/) | Import and implement a Claude Design handoff into a report or Fabric App |
| Skill | [`pbi-report-design`](plugins/reports/skills/pbi-report-design/) *(WIP)* | Power BI report best practices, design, and style |
| Skill | [`review-report`](plugins/reports/skills/review-report/) *(WIP)* | Review Power BI reports for usage metrics and best practices |
| Agent | [`deneb-reviewer`](plugins/reports/agents/deneb-reviewer.agent.md) | Review Deneb specs for Vega/Vega-Lite syntax and conventions |
| Agent | [`svg-reviewer`](plugins/reports/agents/svg-reviewer.agent.md) | Review SVG DAX measures for syntax and design quality |
| Agent | [`r-reviewer`](plugins/reports/agents/r-reviewer.agent.md) | Review R visual scripts (ggplot2) for Power BI conventions |
| Agent | [`python-reviewer`](plugins/reports/agents/python-reviewer.agent.md) | Review Python visual scripts (matplotlib/seaborn) for Power BI conventions |

</details>

<details>
<summary>🎨 <strong>custom-visuals</strong> &ensp; Deneb, Python, R, SVG, and pbiviz custom visuals</summary>

| Type | Name | Description |
|------|------|-------------|
| Skill | [`deneb-visuals`](plugins/custom-visuals/skills/deneb-visuals/) | Author Deneb visuals with Vega and Vega-Lite specs |
| Skill | [`deneb-pbir`](plugins/custom-visuals/skills/deneb-pbir/) | Round-trip tooling: extract/embed a Deneb spec in visual.json and offline-render it |
| Skill | [`python-visuals`](plugins/custom-visuals/skills/python-visuals/) | Custom Python visuals (matplotlib/seaborn) in Power BI reports |
| Skill | [`r-visuals`](plugins/custom-visuals/skills/r-visuals/) | Custom R visuals (ggplot2) in Power BI reports |
| Skill | [`svg-visuals`](plugins/custom-visuals/skills/svg-visuals/) | SVG visuals via DAX measures in Power BI reports |
| Skill | [`powerbi-custom-visuals`](plugins/custom-visuals/skills/powerbi-custom-visuals/) | Develop, build, and package `.pbiviz` custom visuals with the pbiviz toolchain |

</details>

<details>
<summary>📁 <strong>pbip</strong> &ensp; Author and validate TMDL, PBIR, and PBIP project files</summary>

| Type | Name | Description |
|------|------|-------------|
| Skill | [`pbip`](plugins/pbip/skills/pbip/) | Power BI Project (PBIP) format, structure, and file types |
| Skill | [`tmdl`](plugins/pbip/skills/tmdl/) | Author and edit TMDL files directly |
| Skill | [`pbir-format`](plugins/pbip/skills/pbir-format/) | Author and edit PBIR metadata files directly (visual.json, report.json, themes, filters, report extensions, visual calculations) |
| Agent | [`pbip-validator`](plugins/pbip/agents/pbip-validator.agent.md) | Validate PBIP project structure, TMDL syntax, and PBIR schemas |
| Hook | PBIR validation | Validates PBIR structure, required fields, naming conventions, and schema URLs |
| Hook | Report binding validation | Validates semantic model binding (byPath directory exists; byConnection model exists via `fab exists`) |
| Hook | TMDL validation | Validates TMDL structural syntax |

</details>

<details>
<summary>🧮 <strong>tabular-editor</strong> &ensp; BPA rules, C# scripting, and CLI automation for Tabular Editor</summary>

| Type | Name | Description |
|------|------|-------------|
| Skill | [`bpa-rules`](plugins/tabular-editor/skills/bpa-rules/) | Create and improve Best Practice Analyzer rules for models |
| Skill | [`c-sharp-scripting`](plugins/tabular-editor/skills/c-sharp-scripting/) | C# scripting and macros for TE |
| Skill | [`te-cli`](plugins/tabular-editor/skills/te-cli/) | Cross-platform Tabular Editor CLI (`te`, preview) for semantic models from the terminal |
| Skill | [`te2-cli`](plugins/tabular-editor/skills/te2-cli/) | Tabular Editor 2 CLI usage and automation (not TE3) |
| Skill | [`te-docs`](plugins/tabular-editor/skills/te-docs/) | Tabular Editor documentation search, TE3 config files. Uses [`pbi-search`](https://github.com/data-goblin/pbi-search) CLI |
| Command | [`/suggest-rule`](plugins/tabular-editor/commands/suggest-rule.md) | Generate BPA rules from descriptions |
| Agent | [`bpa-expression-helper`](plugins/tabular-editor/agents/bpa-expression-helper.agent.md) | Debug and improve BPA rule expressions |

</details>

<details>
<summary>🖥️ <strong>pbi-desktop</strong> &ensp; Connect to, query, and modify models in Power BI Desktop</summary>

| Type | Name | Description |
|------|------|-------------|
| Skill | [`connect-pbid`](plugins/pbi-desktop/skills/connect-pbid/) | Explore, query, and modify a model in Power BI Desktop, and reload/screenshot the report canvas via the Desktop Bridge |
| Agent | [`query-listener`](plugins/pbi-desktop/agents/query-listener.agent.md) | Capture DAX queries from Power BI Desktop visuals in real time |
| Hook | DAX reference validation | Validates table, column, and measure references against the connected model; suggests corrections |
| Hook | Measure metadata enforcement | Blocks adding measures without DisplayFolder, Description, and FormatString |
| Hook | Referential integrity check | Reports unmatched many-side keys after relationship or column changes |
| Hook | Metadata cache refresh | Auto-snapshots model metadata on TOM connect or model modification |
| Hook | Compatibility level check | Reports features available by upgrading; optional auto-upgrade |

</details>

<details>
<summary>⚡ <strong>fabric-cli</strong> &ensp; Remote operations via Fabric CLI; works on Pro, PPU, or Fabric</summary>

| Type | Name | Description |
|------|------|-------------|
| Skill | [`fabric-cli`](plugins/fabric-cli/skills/fabric-cli/) | Fabric CLI (`fab`) for any remote operation in Power BI or Fabric (works fully on Pro/PPU; Fabric not required) |
| Command | [`/audit-context`](plugins/fabric-cli/commands/audit-context.md) | Review project context files (CLAUDE.md, agents.md, memory files) |
| Command | [`/migrating-fabric-trial-capacities`](plugins/fabric-cli/commands/migrating-fabric-trial-capacities.md) | Migrate workspaces from trial to production capacity |

</details>

<details>
<summary>🛡️ <strong>fabric-admin</strong> &ensp; Tenant settings audits and governance; requires fabric-cli</summary>

| Type | Name | Description |
|------|------|-------------|
| Skill | [`audit-tenant-settings`](plugins/fabric-admin/skills/audit-tenant-settings/) | Audit Fabric and Power BI tenant settings, delegated overrides, and Entra security group membership |

</details>

<details>
<summary>🧾 <strong>paginated-reports</strong> &ensp; Author, validate, publish, and test paginated (RDL) reports</summary>

| Type | Name | Description |
|------|------|-------------|
| Skill | [`paginated-report`](plugins/paginated-reports/skills/paginated-report/) | Author, validate, publish, and render Power BI paginated reports (RDL) |
| Hook | RDL validation | Validates RDL structure on edit |

</details>

<details>
<summary>🔀 <strong>etl</strong> &ensp; Execute code and queries on Fabric compute: Spark via Livy and DuckDB</summary>

| Type | Name | Description |
|------|------|-------------|
| Skill | [`executing-spark`](plugins/etl/skills/executing-spark/) | Run Python/PySpark on Fabric Spark compute via ephemeral Livy sessions (no notebook artifact) |
| Skill | [`using-duckdb`](plugins/etl/skills/using-duckdb/) | Query Fabric lakehouse/warehouse Delta data with DuckDB, locally or in a Fabric notebook |

</details>

## Useful stuff

General-purpose agent resources that don't fit into a plugin: defensive hooks, patterns, and tools. See [`useful-stuff/`](useful-stuff/).

## Use or re-use of these skills

These plugins are licensed **GPL-3.0** and intended for free community use.

This is a fork; the original work is Kurt Buhler's. If you copy these skills — manually or by using an agent to rewrite them — you must retain attribution and a link to the [original project](https://github.com/data-goblin/power-bi-agentic-development), per the license.

<br>

---

<p align="center">
  <em>Built with assistance from <a href="https://claude.ai/claude-code">Claude Code</a>. AI-generated code has been reviewed but may contain errors. Use at your own risk.</em>
</p>

## Attribution

<p align="center">
  A personalized fork maintained by <strong>Tim · InsightfulAnalytics</strong>.<br>
  Original work by <a href="https://github.com/data-goblin">Kurt Buhler</a> · <a href="https://data-goblins.com">Data Goblins</a> · part of <a href="https://tabulareditor.com">Tabular Editor</a>.
</p>
