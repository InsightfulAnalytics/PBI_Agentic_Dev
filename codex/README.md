# Using this marketplace with OpenAI Codex

Codex supports the same open [Agent Skills standard](https://learn.chatgpt.com/docs/build-skills)
(SKILL.md) that these plugins use for Claude Code, so the skills work in Codex too. This
directory is the compatibility layer: an installer that projects the skills into Codex's
discovery location, plus an AGENTS.md adapter for the parts Codex does differently
(no plugin hooks on file edits, no subagents, no slash commands).

**Nothing here changes how Claude Code uses the repo.** The Claude plugins in `plugins/`
are the source of truth; Codex reads projected copies (or links) plus your cloned repo.

## Install (user scope — recommended)

Requirements: Python 3.9+, git, a clone of this repo (keep it — it's the runtime store
for bundled scripts and binaries).

```bash
git clone https://github.com/InsightfulAnalytics/PBI_Agentic_Dev.git
cd PBI_Agentic_Dev
python codex/install.py --check     # dry run: see what would happen
python codex/install.py             # skills -> ~/.agents/skills, adapter -> ~/.codex/AGENTS.md
python codex/install.py --mcp      # optional: also merge MCP servers into ~/.codex/config.toml
```

Then start `codex` and run `/skills` — you should see the Power BI skills listed. Invoke
one explicitly with `$<name>` (e.g. `$tmdl`), or just describe a Power BI task and let
description matching activate them.

### What gets installed

| What | Where | Notes |
|---|---|---|
| 34 plugin skills + 3 task skills | `~/.agents/skills/<name>/` | `claude-design-handoff` excluded (Anthropic-API-bound); ported slash commands: `audit-context`, `migrating-fabric-trial-capacities`, `suggest-rule` |
| AGENTS.md adapter block | `~/.codex/AGENTS.md` (honors `$CODEX_HOME`) | routing table, Claude-vocabulary translation, validation rules, tool prerequisites — between `pbi-agentic-dev` sentinel comments |
| MCP servers (`--mcp` only) | `~/.codex/config.toml` | `microsoft-learn` (HTTP), `pbiviz` (npx stdio) — mirrors the plugins' `.mcp.json` files |
| Manifest | `~/.agents/skills/.pbi-agentic-dev-manifest.json` | enables clean update/uninstall |

In copy mode (default) every `${CLAUDE_PLUGIN_ROOT}` in the copies is rewritten to the
absolute plugin path inside your clone, so bundled scripts, theme libraries, and the
`tmdl-validate` binaries resolve. Don't delete or move the clone; if you move it, re-run
the installer.

## Options

```text
--mode junction     link skill dirs instead of copying (Windows junction / POSIX symlink).
                    Live-tracks the repo: git pull updates skills with no re-run. No token
                    rewriting happens; the AGENTS.md adapter explains ${CLAUDE_PLUGIN_ROOT}.
--project DIR       install into DIR/.agents/skills (project scope) instead of user scope.
                    Pair with codex/AGENTS-project-template.md for the project's AGENTS.md.
--prefix pbi-       namespace the installed skill names (copy mode only).
--include-all       also install the excluded skills.
--force             replace same-named skill dirs the installer didn't create.
--skip-agents-md    don't touch ~/.codex/AGENTS.md.
--uninstall         remove installed skills + AGENTS.md block + MCP block (via manifest).
```

## Updating

```bash
git pull                       # or after harvesting upstream changes
python codex/install.py        # idempotent: refreshes copies, prunes removed skills,
                               # updates the AGENTS.md block in place
```

Junction-mode installs only need a re-run when skills are added/removed or the adapter
template changes.

## Work machines and Codex cloud

- **Work laptop, no user-scope control**: clone the repo, then
  `python codex/install.py --project <your-pbi-project>` and drop
  [`AGENTS-project-template.md`](AGENTS-project-template.md) into the project as `AGENTS.md`.
- **Codex cloud/web**: commit `.agents/skills/` into the project repo (project-scope install,
  then commit). Skill knowledge works; bundled binaries/scripts from the clone won't exist
  in the cloud sandbox — the template's caveat section covers the fallbacks.

## What's different from Claude Code

| Claude Code | Under Codex |
|---|---|
| Hooks auto-validate TMDL/PBIR/RDL after every edit | No file-edit hooks. The AGENTS.md block instructs Codex to run the validators after edits — verify it actually does on nontrivial changes |
| Subagents (8 reviewers/validators) run as separate processes | Codex performs the same review inline, using the `*.agent.md` files as checklists |
| Slash commands (`/suggest-rule`, …) | Ported as skills: `$suggest-rule`, `$audit-context`, `$migrating-fabric-trial-capacities` |
| `claude-design-handoff` skill | Not installed (needs Anthropic's Claude Design API) |
| Plugin marketplace manages versions/updates | `git pull` + re-run the installer |

## Troubleshooting

- **Skills don't appear in `/skills`**: check `~/.agents/skills/<name>/SKILL.md` exists;
  junction mode — verify your Codex build follows directory links, else reinstall with
  `--mode copy`.
- **Descriptions look truncated / a skill never triggers**: Codex budgets the skills list
  (~2% of context; 8,000 chars fallback) and these descriptions total ~13k chars, so some
  shortening is expected — the AGENTS.md routing table is the backstop, and `$<name>`
  always works. `install.py --check` reports the size.
- **AV flags `tmdl-validate-*.exe`**: known false positive (unsigned Rust linter);
  see `plugins/pbip/hooks/README.md`. Fall back to Desktop-open validation.
- **`fab`/`pbir` Unicode errors on Windows**: `export PYTHONIOENCODING=utf-8 PYTHONUTF8=1`.
- **`npx` MCP server times out on Windows**: uncomment `startup_timeout_sec = 60` in the
  merged block in `~/.codex/config.toml`.
