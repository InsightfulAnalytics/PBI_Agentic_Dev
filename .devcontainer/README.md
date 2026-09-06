# Using these skills from a Codespace

The Power BI knowledge in this marketplace was written on Windows, next to Power BI Desktop. Most
of it is not about Windows at all: it is about TMDL, the PBIR JSON schemas, and the Fabric and
Power BI REST APIs, all of which behave identically from a Linux container. This directory makes
that knowledge reachable there.

There are two situations. Pick the one that matches where you are working.

## 1. A Codespace on this repository

Nothing to do. `devcontainer.json` here installs Claude Code, runs
[`scripts/bootstrap-agent-env.sh`](../scripts/bootstrap-agent-env.sh), and sets
`PBI_MARKETPLACE_ROOT` to the checkout. Open a Codespace and the skills are registered.

## 2. A Codespace on a Power BI project repository

This is the common case: the work happens in a repo containing a `.pbip` project, not in the
marketplace. Add a `.devcontainer/devcontainer.json` to that repo:

```jsonc
{
  "name": "pbi-project",
  "image": "mcr.microsoft.com/devcontainers/python:1-3.12-bookworm",
  "features": {
    "ghcr.io/devcontainers/features/node:1": { "version": "22" },
    "ghcr.io/devcontainers/features/azure-cli:1": {},
    "ghcr.io/devcontainers/features/github-cli:1": {}
  },
  "postCreateCommand": "npm install -g @anthropic-ai/claude-code && git clone --depth 1 --branch main https://github.com/InsightfulAnalytics/PBI_Agentic_Dev.git \"$HOME/.pbi-agentic-dev\" && bash \"$HOME/.pbi-agentic-dev/scripts/bootstrap-agent-env.sh\"",
  "postStartCommand": "bash \"$HOME/.pbi-agentic-dev/scripts/bootstrap-agent-env.sh\" --refresh",
  "remoteEnv": { "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1" }
}
```

The clone is explicit rather than `curl ... | bash`, so you can see what runs and pin `--branch` to
a tag when you want a fixed version. Pinning to a tag also stops a marketplace change from altering
a project container without warning.

Run it by hand on an existing container, or on any Linux or macOS machine:

```bash
git clone --depth 1 https://github.com/InsightfulAnalytics/PBI_Agentic_Dev.git ~/.pbi-agentic-dev
bash ~/.pbi-agentic-dev/scripts/bootstrap-agent-env.sh
```

## Why a writable clone rather than a plugin install

A `directory`-source marketplace attaches its plugins live from the folder: no per-commit cache, no
version bump, no `plugin update` to pick an edit up. That matters twice over.

- Editing a skill takes effect immediately, which is what you want while working.
- The clone is a git working copy, so a new learning can actually be committed. The plugin cache is
  not a working copy, and an edit there is discarded by the next update. This is why
  `PBI_MARKETPLACE_ROOT` exists and why [`scripts/record-learning.sh`](../scripts/record-learning.sh)
  refuses to run without it. See [`LEARNINGS.md`](../LEARNINGS.md).

## What works on Linux, and what does not

`scripts/bootstrap-agent-env.sh` prints this as a capability report on every container start, and
writes it to `.bootstrap-report.txt`. It is repeated here because knowing it before the first turn
saves more time than anything else in this directory.

| | Linux Codespace | Windows with Desktop |
|---|---|---|
| `fab` (Fabric CLI) | yes | yes |
| `te` (Tabular Editor CLI) | yes | yes |
| `az` | yes | yes |
| TMDL validation | yes, `plugins/pbip/hooks/bin/tmdl-validate-linux-x64`, bundled, runs on a path | yes |
| Fabric and Power BI REST APIs | yes | yes |
| Server-side report render (`ExportTo` to PDF, then pymupdf to PNG) | yes | yes |
| `pbir` CLI | **no** | yes |
| Power BI Desktop | **no** | yes |
| ADOMD or TOM against a LOCAL model | **no** | yes |
| ADOMD or TOM against a PUBLISHED model (XMLA, token auth) | yes | yes |
| Windows PowerShell 5.1, DAX Studio, Tabular Editor 2 and 3 | **no** | yes |

### `pbir` is absent, not degraded

Every `pbir-cli` release publishes exactly two wheels, `macosx_11_0_arm64` and `win_amd64`, and no
sdist. On Linux both `pip install pbir-cli` and `uv tool install pbir-cli` fail with
"No matching distribution found for pbir-cli". Do not spend turns on the install.

Instead, on Linux:

- **Author PBIR** by hand from the `pbip:pbir-format` skill's `examples/visuals/` templates. That
  skill exists for exactly this.
- **Validate TMDL** with the bundled `tmdl-validate-linux-x64`.
- **Validate PBIR** with `plugins/pbip/hooks/validate-pbir.sh`, but know what it is: a PostToolUse
  hook that reads a JSON tool-use payload on stdin and requires `jq`. Without `jq` it exits 0 on a
  broken file, which reads as "valid". Treat a clean run as weak evidence, not proof.
- **Publish** with `fab import` (byConnection reports only).
- **See the result** by rendering server-side: `POST groups/{ws}/reports/{id}/ExportTo`, poll, then
  `GET` the file. `fab api` corrupts binary bodies, so fetch the file over raw HTTP with a bearer
  token from `az account get-access-token`. Details in the `fabric-cli` skill's
  `references/reports.md`.

### The Desktop-only skills

`pbi-desktop:connect-pbid`, `reports:pbi-verify-loop` and the `pbir desktop` command group are inert
in a container. They are not broken; there is simply no Desktop and no local `msmdsrv` to talk to.
Each of them now names its headless substitute in the skill itself.
