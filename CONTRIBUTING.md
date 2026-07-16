# Contributing

This repository is a **personalized fork** of Kurt Buhler's [`power-bi-agentic-development`](https://github.com/data-goblin/power-bi-agentic-development). Where a contribution belongs depends on what it touches.

## Substantive skill work → upstream

New skills, new subagents, and improvements to upstream-authored skill content should be contributed to the original project at [data-goblin/power-bi-agentic-development](https://github.com/data-goblin/power-bi-agentic-development), following its contribution policy. That way the whole community benefits, and this fork picks the changes up as it tracks upstream releases.

## Fork-specific contributions → here

Issues and PRs are welcome in this repo for things that only exist here:

- Broken links, typos, or errors in the fork's own docs (README, PERSONALIZING.md, FORK-CHANGES.md, this file)
- Fixes to the fork-maintained skills: `pbi-verify-loop`, `power-bi-theme`, `claude-design-handoff` (reports), `deneb-pbir` (custom-visuals), and `dax-no-calculate` (semantic-models)
- Problems with this fork's marketplace packaging (`marketplace.json`, plugin manifests)

If you're unsure where something belongs, open an issue and ask.

## PR guidelines

- Test your change locally with `claude --plugin-dir /path/to/plugin` before submitting
- Do not commit memory files (`.claude/`, `.cursor/`, `.github/instructions/`) or changes unrelated to your contribution
- Do not bump plugin versions; the maintainer handles version bumps at release time via `scripts/bump_release_version.py`
- PRs should target `main` and have a concise title prefixed with `feat:`, `fix:`, `docs:`, etc.
