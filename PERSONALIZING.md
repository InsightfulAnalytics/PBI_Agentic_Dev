# Personalizing this marketplace

This is **Tim's personal fork** of Kurt Buhler's [`power-bi-agentic-development`](https://github.com/data-goblin/power-bi-agentic-development) marketplace, renamed to **`power-bi-agentic-development-tim`** so it can coexist with the original in Claude Code.

Claude Code is configured to load the Power BI skills from **this repo** (via a local `directory`-source marketplace). The 6 data-goblin plugins are installed but **disabled**; the 6 plugins from this fork are **enabled**.

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
> The per-commit cache under `~/.claude/plugins/cache/` lives outside the repo, so it survives the move — no re-install needed, just correct the path. (This repo was moved from `…\PBI Agentic Development\power-bi-agentic-development-tim` to `…\PBI_Automated_Development` on 2026-07-04; the paths above were corrected then.)

## The personalization loop (verified working)

To personalize a skill and have Claude pick it up:

1. **Edit** the skill files under `plugins/<plugin>/skills/<skill>/` (e.g. `SKILL.md` and its supporting files).
2. **Bump the version** in `plugins/<plugin>/.claude-plugin/plugin.json` — e.g. `"26.25"` → `"26.25.1"`. (This is the trigger; without it, `plugin update` no-ops.)
3. **Commit** the change:
   ```powershell
   cd "B:\VS Code Files\PBI_Automated_Development"
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

The 6 plugins (and their skill folders) you can personalize:
`tabular-editor`, `pbi-desktop`, `pbip`, `semantic-models`, `reports`, `fabric-cli`.
(The repo also contains `paginated-reports`, `fabric-admin`, `custom-visuals`, `etl`, which are not currently installed — install them the same way if you want them.)

## Back up / publish to a private GitHub repo

`gh` (GitHub CLI) 2.96 is installed but you must log in yourself (interactive). In a **fresh** terminal:

```powershell
cd "B:\VS Code Files\PBI_Automated_Development"
gh auth login          # GitHub.com → HTTPS → login with a browser
gh repo create power-bi-agentic-development-tim --private --source . --remote origin --push
```

That creates the **private** repo under your account, wires it as `origin`, and pushes the current history. Afterwards, `git push` publishes new personalization commits.

This fork has **no upstream link** (data-goblin's `origin` was removed). To pull their future updates manually:

```powershell
git remote add upstream https://github.com/data-goblin/power-bi-agentic-development.git
git fetch upstream
git merge upstream/main      # resolve conflicts, keeping your personalizations
```

## Revert to the original data-goblin skills

```powershell
$plugins = 'tabular-editor','pbi-desktop','pbip','semantic-models','reports','fabric-cli'
foreach ($p in $plugins) {
  claude plugin enable  "$p@power-bi-agentic-development"
  claude plugin disable "$p@power-bi-agentic-development-tim"
}
```
Restart Claude Code. To undo, swap `enable`/`disable`.
