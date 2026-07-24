<!--
Template: per-project AGENTS.md for Power BI projects worked on with OpenAI Codex.
Use when you can't (or don't want to) install the skills user-globally — e.g. a work
machine, a shared repo, or Codex cloud. Copy into the project root as AGENTS.md (or
append to an existing one), then either:
  a) run `python <repo>/codex/install.py --project <this dir>` to install the skills
     into ./.agents/skills (local machines — Codex discovers them automatically), or
  b) commit ./.agents/skills into the repo (Codex cloud — note the caveat below).
Replace <PBI-AGENTIC-REPO> with the clone path of power-bi-agentic-dev, if present.
-->

# Power BI project — agent instructions

This is a Power BI Project (PBIP): TMDL semantic model files under `*.SemanticModel/definition/`,
PBIR report JSON under `*.Report/definition/`. Power BI / Fabric skills are provided in
`.agents/skills/` (from the power-bi-agentic-dev marketplace) — let them auto-activate, or
invoke with `$<skill-name>`.

## Rules

- **Validate after editing** (no auto-hooks under Codex — run these yourself):
  - `*.tmdl` → `tmdl-validate` (bundled at `<PBI-AGENTIC-REPO>/plugins/pbip/hooks/bin/tmdl-validate-<platform>`), or open in Power BI Desktop to surface errors
  - anything under `*.Report/` → `pbir validate "<Name>.Report"`
  - whole project → `python "<PBI-AGENTIC-REPO>/plugins/pbip/skills/pbip/scripts/validate_pbip.py" .`
- Skills reference Claude Code concepts; translate: `plugin:skill` → the skill named after
  the colon; "dispatch the X agent" → read `<PBI-AGENTIC-REPO>/plugins/*/agents/X.agent.md`
  and do that review inline; `AskUserQuestion` → ask in chat; `${CLAUDE_PLUGIN_ROOT}` →
  `<PBI-AGENTIC-REPO>/plugins/<plugin>`.
- Windows consoles: `export PYTHONIOENCODING=utf-8 PYTHONUTF8=1` before `fab`/`pbir`.

## Codex cloud caveat

If this repo is used from Codex cloud/web, only the committed `.agents/skills/` content is
available — bundled binaries/scripts referenced under `<PBI-AGENTIC-REPO>` won't exist in
the sandbox. The skill knowledge still applies; skip runtime-store commands and validate
with `pbir validate` / Desktop instead.
