# Personalizing this marketplace

This is **Tim's personal fork** of Kurt Buhler's [`power-bi-agentic-development`](https://github.com/data-goblin/power-bi-agentic-development) marketplace, renamed to **`power-bi-agentic-dev`** so it can coexist with the original in Claude Code.

On the maintainer's machine, Claude Code loads the Power BI skills from a local clone of **this repo** (via a `directory`-source marketplace), with all 10 plugins enabled. The upstream `data-goblin/power-bi-agentic-development` marketplace stays *registered* (so upstream updates can be harvested — see [Tracking upstream](#tracking-upstream-kurts-updates)), but its plugins are not enabled; the previously-disabled upstream toggles and the on-disk cache were removed on 2026-07-12.

This fork also **owns Tim's personal Power BI add-in skills**, migrated in from `~/.claude/skills` so they're version-controlled here: `pbi-verify-loop` / `power-bi-theme` / `workout-wednesday` (reports — `workout-wednesday` migrated 2026-07-29, de-personalized and with the LinkedIn-draft step dropped), `deneb-pbir` (custom-visuals), and `date-table` (semantic-models — the standard DimDate template, migrated from `PBI Projects\Date Table Template` on 2026-07-21; it bundles third-party community code, credited in [ATTRIBUTIONS.md](ATTRIBUTIONS.md)), and `dax-standard` (semantic-models — the house DAX authoring style, migrated 2026-08-24), and `performant-matrix` (custom-visuals, authored in the fork 2026-08-29).

- 2026-09-08: the fork updated the Deneb skills and tooling for Deneb 2.0 while keeping 1.9
  compatibility: `custom-visuals/deneb-visuals` (new `references/deneb-2-migration.md`, the 2.0
  property, supporting-field, field-parameter and template v2 facts), `custom-visuals/deneb-pbir`
  (`audit` / `migrate`, renderer shims, the 2.0 Vega bundle), the `reports/deneb-reviewer` agent and
  the `performant-matrix` grid reference. Upstream's `deneb-visuals` was still on 1.9 that day, so a
  future upstream 2.0 update will conflict with these files; harvest it hunk by hunk.
- 2026-09-14: the fork absorbed the Netflix build debrief. `reports/pbi-plan` is new (a ticketed
  build map with an HTML plan board, user-invoked only via `/pbi-plan`; its ticket shape is adapted
  from Matt Pocock's MIT-licensed `wayfinder` / `to-tickets`, see
  [ATTRIBUTIONS.md](ATTRIBUTIONS.md)), and it retires `reports/claude-design-handoff`. New tooling:
  `reports/pbir-cli` gained `scripts/close-plan.py` (a report-surface sweep for tooltip, navigation,
  title, label, axis and alt-text decisions nobody made; advisory by default, `--enforce` to gate a
  ticket) and `references/interactions.md`. Also: Critical Rule 7 in `pbir-cli` (one Desktop,
  batched writes), the insight test in `reports/pbi-report-design`, and the Desktop 26.08+ "Apply
  external changes" correction in `pbip/pbip` and `semantic-models/model-change`, which retires
  close-and-reopen as the default advice.

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

> **When Claude Code refuses the `directory` marketplace.** From Claude Code 2.1.251 (September
> 2026), a `directory` marketplace on a drive Claude Code cannot classify as local was refused
> (seen on an exFAT data drive): every plugin failed with `Plugin source path refused: ./plugins/<name>
> does not stay inside its marketplace directory`, and only `claude plugin list` showed the error; the
> session's skill listing just omitted the skills. A link from another drive to the same folder was
> refused too. The skills-directory loader has no such gate: link each plugin folder to
> `~/.claude/skills/<plugin>` (a directory junction on Windows) and it registers as
> `<plugin>@skills-dir` with its skills, agents and hooks, still live from the repo, toggled by
> `enabledPlugins` under that name. A plugin added to the fork needs its own link.
> Retest: after a Claude Code update, run `claude plugin list` and look for the refusal.

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

The 11 plugins you can personalize:
`semantic-models`, `reports`, `pbip`, `custom-visuals`, `tabular-editor`, `pbi-desktop`, `fabric-cli`,
`fabric-admin`, `paginated-reports`, `etl`, and `fabric-data-app` (harvested 2026-10-05; it holds
only the `/data-app-pane` mod, no skills).

Upstream 26.40 added Claude Code mods: sidebar panes that follow a CLI (`/fabric-pane` in
`fabric-cli`, `/report-pane` in `reports`, `/data-app-pane` in `fabric-data-app`). They live in each
plugin's `hooks/` folder as TypeScript modules, need Claude Code 2.1.287 or newer and the fullscreen
layout, and take their `glyphs`, `follow` and `fontHint` options from the plugin's `userConfig`. On
Windows, set `glyphs` explicitly; auto detection covers only Linux and macOS.

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

### Harvest playbook

Never `git merge upstream/main`. Both sides diverged heavily, and some fork changes also landed
upstream in a refined form, so a merge conflicts on the fork's own deliberate divergences.
Harvest **by area**.

**Per area, decide wholesale or surgical.** Take a skill directory wholesale
(`git checkout upstream/main -- <dir>`) only when the fork's sole divergence there is a change
upstream also merged and then refined. Check with `git log <mergebase>..main -- <path>` against
`git log <mergebase>..upstream/main -- <path>`. Re-derive that set every harvest; a previous
harvest's "only three files differ" does not carry over. Take `plugins/reports/` surgically: it is
the most diverged area. After a wholesale checkout, `git diff --stat upstream/main -- <dir>` should
reduce to exactly the re-apply files below and the files in [FORK-CHANGES.md](FORK-CHANGES.md).

**Re-apply after any import** (upstream reintroduces the pre-fork state):

- The marketplace rename `@power-bi-agentic-development` to `@power-bi-agentic-dev`. Leave the
  `data-goblin/power-bi-agentic-development` GitHub URL alone.
- `pbir-cli/references/cli-reference.md`: the removal of the dead reference to an
  `undocumented-apis.md` rules file that ships with neither repo.
- `pbir-cli/examples/K201-MonthSlicer.Report/definition.pbir`: the sanitized workspace name and
  all-zero semantic model GUID.
- `plugins/{pbip,pbi-desktop,paginated-reports}/.github/plugin/plugin.json` (Copilot CLI
  manifests) carry the fork's repo URL, version and descriptions, like the `.claude-plugin`
  manifests. Skip upstream's version bumps to them.
- `useful-stuff/themes/*.json`: every font line is `Consolas` (see FORK-CHANGES.md).
- `plugins/*/.claude-plugin/plugin.json`: keep the fork's `version`, `repository` and short
  `description`; take upstream's `types`, `userConfig` and keyword changes (the mod options).

**Deliberate exclusions; do not harvest:**

- The `goblin-mode` plugin (beginner onboarding).
- The `databricks-cli` plugin (a Databricks pane; no Databricks work here), and `media/mods/*.gif`,
  which only upstream's README uses.
- Upstream's removal of the theme references from `modifying-theme-json`: the fork's
  `power-bi-theme` delegates to them. The fork keeps its older, longer `modifying-theme-json/SKILL.md`,
  so fold upstream's changes to that file in by hand (26.40.2's style presets went in as a cascade
  note and a link to `references/style-presets.md`).
- Version bumps, README changes and marketplace-rename commits. The fork keeps its own scheme.
- `fabric-cli/.../export_semantic_model_as_pbip.py` stays fork-local.
- Skills removed from the fork on purpose stay removed: `pbi-lifecycle`, `pbi-project-hub`,
  `fabric-app-bootstrap`, `fabric-app-lakehouse-live`, `fabric-app-sqldb-writeback`, `pbi-theme`.

**Gotchas:**

- Upstream documents CLI flags before they ship. Check the installed CLI and PyPI before
  "correcting" upstream's forward-looking text; leaving it alone avoids a permanent divergence.
- `py_compile` drops `__pycache__/` next to imported scripts. It is gitignored; remove it anyway.
- Upstream's syntax sweeps (`te`, `pbir`) fix only the files upstream touched. After harvesting one,
  grep the whole repo for the old forms, including multi-line commands (`-q X -i` on continuation
  lines) and removed verbs.
- Merging by hand on Windows: a tracked file sitting in the working tree as CRLF over an LF blob
  makes `git merge-file` in place report a whole-file conflict. Write the LF blob out first
  (`git show HEAD:<path> > <path>`). In Git Bash, set `MSYS_NO_PATHCONV=1` for
  `git show upstream/main:.claude-plugin/...`, and then pass `git merge-file` Windows-style paths.
- An agent that rewrites a whole markdown file on Windows can write it back as CRLF. `autocrlf`
  hides that from `git diff --stat`, and it lands as a whole-file rewrite that conflicts with every
  later cherry-pick. Before committing a multi-agent change set, compare each changed file's line
  endings with `HEAD`'s:

  ```bash
  python -c "
  import io,subprocess
  for p in subprocess.run(['git','diff','--name-only'],capture_output=True,text=True).stdout.split():
      cur=io.open(p,'rb').read(); head=subprocess.run(['git','show','HEAD:'+p],capture_output=True).stdout
      if (cur.count(b'\r\n')>0)!=(head.count(b'\r\n')>0): print('FLIP:',p)
  "
  ```

**After every harvest:** re-run `python codex/install.py` and its `--check` (see
[codex/README.md](codex/README.md)), then `bash scripts/validate-plugins.sh` and
`python scripts/check-skill-hygiene.py`.

Fixes to upstream-authored text stay fork fixes. This repo is not a GitHub fork of upstream, so
GitHub cannot open a pull request from it; such fixes surface as small conflicts or no-ops on the
next harvest.

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
