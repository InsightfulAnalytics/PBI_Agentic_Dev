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

Notice dated 2026-07-29.
