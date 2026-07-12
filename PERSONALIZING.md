# Personalizing this marketplace

This is **Tim's personal fork** of Kurt Buhler's [`power-bi-agentic-development`](https://github.com/data-goblin/power-bi-agentic-development) marketplace, renamed to **`power-bi-agentic-development-tim`** so it can coexist with the original in Claude Code.

Claude Code loads the Power BI skills from **this repo** (via a local `directory`-source marketplace). **All 10 plugins from this fork are enabled.** The upstream `data-goblin/power-bi-agentic-development` marketplace stays *registered* (so you can harvest Kurt's updates — see [Tracking upstream](#tracking-upstream-kurts-updates)), but its plugins are not enabled; the previously-disabled upstream toggles and the on-disk cache were removed on 2026-07-12.

This fork also **owns Tim's personal Power BI add-in skills**, migrated in from `~/.claude/skills` so they're version-controlled here: `dax-no-calculate` (semantic-models), `pbi-verify-loop` / `power-bi-theme` / `claude-design-handoff` (reports), and `deneb-pbir` (custom-visuals).

## How Claude actually loads these skills (important)

Claude does **not** read skills live from this folder. When a plugin is installed, its files are copied into a per-commit cache:

```
C:\Users\timos\.claude\plugins\cache\power-bi-agentic-development-tim\<plugin>\<commit-sha>\
```

The cache is keyed by **git commit SHA**, and `claude plugin update` only re-copies when the plugin's **`version` changes**. So editing a file here does nothing until you **commit** the change **and bump the version**. This was verified end-to-end.

> **If you move or rename this repo folder**, the marketplace registration breaks (Claude Code can no longer find the `directory` source and its plugins silently stop attaching). Fix the path in **two** places, then restart Claude Code:
> - `~/.claude/settings.json` → `extraKnownMarketplaces."power-bi-agentic-development-tim".source.path`
> - `~/.claude/plugins/known_marketplaces.json` → `"power-bi-agentic-development-tim"` → `source.path` **and** `installLocation`
>
> The per-commit cache under `~/.claude/plugins/cache/` lives outside the repo, so it survives the move — no re-install needed, just correct the path. (Current location: `B:\VS Code Files\PBI_Agentic_Dev`. The folder **and** the GitHub repo were renamed from `PBI_Automated_Development` on 2026-07-12; the paths above were corrected then.)

## The personalization loop (verified working)

To personalize a skill and have Claude pick it up:

1. **Edit** the skill files under `plugins/<plugin>/skills/<skill>/` (e.g. `SKILL.md` and its supporting files).
2. **Bump the version** in `plugins/<plugin>/.claude-plugin/plugin.json` — e.g. `"26.25"` → `"26.25.1"`. (This is the trigger; without it, `plugin update` no-ops.)
3. **Commit** the change:
   ```powershell
   cd "B:\VS Code Files\PBI_Agentic_Dev"
   git add -A
   git commit -m "Personalize <plugin>: <what you changed>"
   ```
4. **Refresh the marketplace and plugin:**
   ```powershell
   claude plugin marketplace update power-bi-agentic-development-tim
   claude plugin update <plugin>@power-bi-agentic-development-tim
   ```
5. **Restart Claude Code** for the change to load.

Only the plugin you bumped+updated is re-copied; the others are untouched.

The 10 plugins (and their skill folders) you can personalize:
`semantic-models`, `reports`, `pbip`, `custom-visuals`, `tabular-editor`, `pbi-desktop`, `fabric-cli`, `fabric-admin`, `paginated-reports`, `etl`.

## Back up / publish to GitHub

The repo is already wired to a **private** GitHub repo as `origin`:

```
origin    https://github.com/InsightfulAnalytics/PBI_Agentic_Dev.git
```

So publishing new personalization commits is just:

```powershell
cd "B:\VS Code Files\PBI_Agentic_Dev"
git push
```

## Tracking upstream (Kurt's updates)

An `upstream` remote is configured, pointing at the original marketplace:

```
upstream  https://github.com/data-goblin/power-bi-agentic-development.git
```

To review and harvest Kurt's new work manually:

```powershell
cd "B:\VS Code Files\PBI_Agentic_Dev"
git fetch upstream
git log --oneline HEAD..upstream/main          # new upstream commits since you diverged
git cherry-pick <sha>                          # bring in a specific value-add commit
```

A **weekly cloud routine** `upstream-plugin-watch` (Mondays 09:00 Australia/Sydney) also does this automatically and reports new commits classified value-add vs noise: <https://claude.ai/code/routines/trig_018b4SFz5M21oavUhaWR7L2A>

Avoid a blanket `git merge upstream/main` — the fork has diverged (renamed marketplace, migrated personal skills, deleted skills), so cherry-picking specific commits is cleaner than a full merge.

## Revert to the original data-goblin skills

The upstream marketplace is still registered, so you can re-enable its plugins and disable this fork's:

```powershell
$plugins = 'tabular-editor','pbi-desktop','pbip','semantic-models','reports','fabric-cli'
foreach ($p in $plugins) {
  claude plugin enable  "$p@power-bi-agentic-development"
  claude plugin disable "$p@power-bi-agentic-development-tim"
}
```

Restart Claude Code. To undo, swap `enable`/`disable`. Note: skills unique to this fork (the migrated personal add-ins above, plus `custom-visuals`/`etl`/`paginated-reports`/`fabric-admin` content) have no upstream equivalent, so reverting loses them.
