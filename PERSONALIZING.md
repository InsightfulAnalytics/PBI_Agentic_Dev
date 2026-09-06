# Personalizing this marketplace

This is **Tim's personal fork** of Kurt Buhler's [`power-bi-agentic-development`](https://github.com/data-goblin/power-bi-agentic-development) marketplace, renamed to **`power-bi-agentic-dev`** so it can coexist with the original in Claude Code.

On the maintainer's machine, Claude Code loads the Power BI skills from a local clone of **this repo** (via a `directory`-source marketplace), with all 10 plugins enabled. The upstream `data-goblin/power-bi-agentic-development` marketplace stays *registered* (so upstream updates can be harvested — see [Tracking upstream](#tracking-upstream-kurts-updates)), but its plugins are not enabled; the previously-disabled upstream toggles and the on-disk cache were removed on 2026-07-12.

This fork also **owns Tim's personal Power BI add-in skills**, migrated in from `~/.claude/skills` so they're version-controlled here: `pbi-verify-loop` / `power-bi-theme` / `claude-design-handoff` / `workout-wednesday` (reports — `workout-wednesday` migrated 2026-07-29, de-personalized and with the LinkedIn-draft step dropped), `deneb-pbir` (custom-visuals), and `date-table` (semantic-models — the standard DimDate template, migrated from `PBI Projects\Date Table Template` on 2026-07-21; it bundles third-party community code, credited in [ATTRIBUTIONS.md](ATTRIBUTIONS.md)), and `dax-standard` (semantic-models — the house DAX authoring style, migrated 2026-08-24), and `performant-matrix` (custom-visuals, authored in the fork 2026-08-29).

## How Claude actually loads these skills (important)

**Corrected 2026-09-07.** This section previously said skills are copied into a per-commit cache and
that an edit does nothing until you commit and bump the version. That is true of a `github` or `git`
source. It is **not** true of the `directory` source this fork is registered as, which is how the
maintainer's machine runs it.

A `directory`-source marketplace attaches its plugins **live from the folder**. Editing a file here
takes effect on the next Claude Code start: no commit, no version bump, no `plugin update`.

The evidence, on a machine where all 10 plugins are loaded:

- `~/.claude/plugins/known_marketplaces.json` records `power-bi-agentic-dev` as
  `{"source": "directory"}` with `installLocation` pointing at the repo folder itself, not at a cache.
- `~/.claude/plugins/installed_plugins.json` contains **zero** `@power-bi-agentic-dev` entries, and
  `settings.json` `enabledPlugins` lists none of them either. There is no install record, because
  there was no install.
- `custom-visuals`, `etl`, `fabric-admin` and `paginated-reports` have **no cache directory at all**,
  and every one of their skills is loaded.
- Six plugins do have a stale cache directory left over from an earlier `github`-source
  registration. They are keyed by **version** (`reports/26.25`, `pbip/26.25.1`), not by commit SHA as
  this file used to claim. The `reports` cache at `26.25` contains 5 skills; the repo has 9; all 9
  are loaded. A plugin serving skills from a directory that does not contain them is not being
  served from that directory.

So there are two loading models, and which one applies depends on how the marketplace is registered:

| Registered as | How skills load | To ship a change |
|---|---|---|
| `directory` (a local path) | live from the folder | save the file, restart Claude Code |
| `github` or `git` | copied into `~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/` | commit, bump the version, `plugin update` |

A Codespace bootstrapped by [`scripts/bootstrap-agent-env.sh`](scripts/bootstrap-agent-env.sh) clones
the repo and registers it as a **`directory`** source, so it gets the live model too. That is
deliberate: a live clone is a git working copy, which is what makes
[`scripts/record-learning.sh`](scripts/record-learning.sh) able to commit a new learning at all.
See [`.devcontainer/README.md`](.devcontainer/README.md).

> **If you move or rename this repo folder**, the marketplace registration breaks (Claude Code can no
> longer find the `directory` source and its plugins silently stop attaching). Fix the path in **two**
> places, then restart Claude Code:
> - `~/.claude/settings.json` -> `extraKnownMarketplaces."power-bi-agentic-dev".source.path`
> - `~/.claude/plugins/known_marketplaces.json` -> `"power-bi-agentic-dev"` -> `source.path` **and**
>   `installLocation`
>
> With a `directory` source, `installLocation` **is** the repo folder, so both entries must change.
> (The local folder **and** the GitHub repo were renamed from `PBI_Automated_Development` on
> 2026-07-12; the paths above were corrected then.)

## Personalizing a skill

On this machine, with the `directory` registration:

1. **Edit** the skill files under `plugins/<plugin>/skills/<skill>/`.
2. **Restart Claude Code.** That is the whole loop.
3. Before committing, run the checks:
   ```powershell
   bash scripts/validate-plugins.sh
   python scripts/check-skill-hygiene.py
   ```

Read [`LEARNINGS.md`](LEARNINGS.md) before adding a fact to a skill. It carries the rule for deciding
whether something is portable product knowledge, platform- or version-scoped knowledge, or genuinely
machine-local (in which case it does not belong in this public repo at all).

## Publishing a change to consumers

The version bump is not what makes a change reach *you*; it is what makes it reach anyone installing
from GitHub, including a `github`-source Codespace.

1. **Bump the version** in `plugins/<plugin>/.claude-plugin/plugin.json`, or run
   `python scripts/bump_release_version.py <old> <new>` to move the marketplace, every plugin
   manifest and every `SKILL.md` `version:` line together.
2. **Commit and push.**
3. Consumers pick it up with:
   ```powershell
   claude plugin marketplace update power-bi-agentic-dev
   claude plugin update <plugin>@power-bi-agentic-dev
   ```

> `scripts/bump_release_version.py` exits 1 if no `SKILL.md` matched the old version, so the three
> manifests currently at `26.25.1` while the `SKILL.md` files are at `26.25` need reconciling before
> the next release bump.

The 10 plugins you can personalize:
`semantic-models`, `reports`, `pbip`, `custom-visuals`, `tabular-editor`, `pbi-desktop`, `fabric-cli`,
`fabric-admin`, `paginated-reports`, `etl`.

## Using with OpenAI Codex

The `codex/` directory projects these same skills into OpenAI Codex (which reads the open Agent Skills standard). Run `python codex/install.py` — see [codex/README.md](codex/README.md). Codex reads copies in `~/.agents/skills` plus this clone; Claude Code's marketplace loading above is untouched. After harvesting upstream changes, re-run the installer to refresh the copies (junction-mode installs pick changes up automatically).

## Back up / publish to GitHub

The maintainer's local clone is wired to this **public** GitHub repo as `origin`:

```
origin    https://github.com/InsightfulAnalytics/PBI_Agentic_Dev.git
```

So publishing new personalization commits is just:

```powershell
cd "<local-clone-path>"
git push
```

(If you fork this repo for your own personalization, point `origin` at your fork instead.)

## Tracking upstream (Kurt's updates)

An `upstream` remote is configured, pointing at the original marketplace:

```
upstream  https://github.com/data-goblin/power-bi-agentic-development.git
```

To review and harvest Kurt's new work manually:

```powershell
cd "<local-clone-path>"
git fetch upstream
git log --oneline HEAD..upstream/main          # new upstream commits since you diverged
git cherry-pick <sha>                          # bring in a specific value-add commit
```

The maintainer also runs a weekly scheduled agent that checks upstream for new commits and reports them classified value-add vs noise.

Avoid a blanket `git merge upstream/main` — the fork has diverged (renamed marketplace, migrated personal skills, deleted skills), so cherry-picking specific commits is cleaner than a full merge.

## Revert to the original data-goblin skills

If the upstream marketplace is registered alongside this fork (as on the maintainer's machine), you can re-enable its plugins and disable this fork's:

```powershell
$plugins = 'tabular-editor','pbi-desktop','pbip','semantic-models','reports','fabric-cli'
foreach ($p in $plugins) {
  claude plugin enable  "$p@power-bi-agentic-development"
  claude plugin disable "$p@power-bi-agentic-dev"
}
```

Restart Claude Code. To undo, swap `enable`/`disable`. Note: skills unique to this fork (the migrated personal add-ins above, plus `custom-visuals`/`etl`/`paginated-reports`/`fabric-admin` content) have no upstream equivalent, so reverting loses them.
