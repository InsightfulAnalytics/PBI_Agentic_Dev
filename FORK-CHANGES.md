# Fork changes

Prominent notice of modifications relative to the upstream project, per GPL-3.0 §5(a).

This repository is a fork of [`data-goblin/power-bi-agentic-development`](https://github.com/data-goblin/power-bi-agentic-development) by Kurt Buhler. Known modifications relative to upstream:

- Renamed the marketplace from `power-bi-agentic-development` to `power-bi-agentic-dev` so both can coexist in Claude Code.
- Removed some upstream-adjacent skills.
- Added fork-maintainer skills to existing plugins (authored by the fork maintainer, not the upstream author):
  - `reports/pbi-verify-loop`
  - `reports/power-bi-theme`
  - `reports/claude-design-handoff`
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

### Fork-owned files, for upstream harvest resolution

New files, so they merge at file granularity even though upstream owns the containing directory:

- `LEARNINGS.md`, `.devcontainer/**`
- `plugins/pbip/skills/tmdl/references/authoring-gotchas.md`
- `plugins/pbi-desktop/skills/connect-pbid/references/desktop-lifecycle.md`
- `plugins/pbi-desktop/skills/connect-pbid/references/assembly-discovery.md`
- `scripts/{bootstrap-agent-env.sh,record-learning.sh,check-skill-hygiene.py,sync-boundary-rule.py,denylist-add.py}`
- `.github/denylist-hashes.txt`, `.github/denylist-patterns.txt`

Modified upstream-authored files, which **will** conflict on a harvest:

- `.github/workflows/validate-plugins.yml` (widened path filters, added the hygiene and
  boundary-rule steps)
- The learnings instruction in `fabric-cli/SKILL.md`, `connect-pbid/SKILL.md` and
  `pbir-cli/SKILL.md`, each now carrying a `<!-- boundary-rule:begin -->` block. Keep the fork's
  version and re-run `python scripts/sync-boundary-rule.py`.

The defect fixes in the `fix: correct skill content that currently makes agents fail` commit touch
upstream-authored content and should be offered upstream, which turns a future harvest of those
hunks into a no-op instead of a conflict.

Notice dated 2026-07-29.
