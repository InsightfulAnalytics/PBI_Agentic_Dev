# pbir on Linux through Wine

`pbir-cli` publishes wheels for Windows and macOS arm64 only, and its licence forbids derivative
works, so there is no Linux port. The Windows build runs unchanged under Wine. `bin/install-linux.sh`
sets that up; the installed `pbir` command is the launcher `bin/pbir-wine`.
(pbir 0.9.33 on Wine 11.18, the powerbi-linux runtime. Verified 2026-11-18.)
Retest: `pbir --version`, then `pbir validate "<name>.Report"` on any PBIR report.

## Install and upgrade

```bash
plugins/reports/skills/pbir-cli/bin/install-linux.sh           # latest release
plugins/reports/skills/pbir-cli/bin/install-linux.sh 0.9.33    # a pinned one
pbir --version
```

It needs `curl`, `jq`, `unzip` and a Wine. The powerbi-linux runtime is used when that project is
installed (found through `~/.local/share/powerbi-linux/active.json`), else a system `wine`. The
script downloads the `win_amd64` wheel, checks it against PyPI's SHA-256, unpacks it under
`~/.local/share/pbir-wine/<version>` and installs the launcher as `~/.local/bin/pbir`. Run it again
to upgrade: `uv tool upgrade` and `pip install --upgrade` do nothing for this install.

## What works

Everything that reads or writes report files: `validate` (all flags), `ls`, `tree`, `cat`, `get`,
`set`, `add`, `fields`, `schema`, `config`, and `model -d` (the definition, read from TMDL). A write
produces the same bytes as on Windows: CRLF, no BOM. A cold start costs about a second.

## Paths

- A relative path works as written. An absolute Linux path is rewritten by the launcher to `Z:\...`
  up to its longest existing prefix, so `/home/me/x/Sales.Report/Page 1.Page` and `-o /tmp/new.png`
  both work. `PBIR_WINE_DEBUG=1 pbir ...` prints the rewritten arguments.
- Output uses CRLF line ends. Strip them before comparing a captured value:
  `pbir --version | tr -d '\r'`. `jq` reads the JSON as it is.
- Paths that `pbir` prints are Windows paths (`Z:\home\...`, or a drive letter the Wine prefix maps).

## Two Wine prefixes

- Offline commands run in a private prefix, `~/.local/share/pbir-wine/prefix`, so a busy or hung
  Power BI Desktop cannot hold them up.
- `pbir desktop ...` and `pbir model ...` run inside the powerbi-linux profile while its session is
  active, because a Wine named pipe is visible only inside the prefix that owns it.
- Both prefixes share one `pbir` configuration (`~/.local/share/pbir-wine/config`), and the private
  prefix mirrors the extra drive letters of the powerbi-linux profile.

## What does not work: the Desktop bridge

`pbir desktop list` answers `not_connected` and `pbir model -q` answers "Local model is not open in
Power BI Desktop", even with Desktop open and the Desktop Bridge setting on. Desktop does create
its pipe (`\\.\pipe\pbi-desktop-bridge-<PID>` accepts a connection from inside the prefix). `pbir`
finds it by listing `\\.\pipe\`, and Wine 11.18 cannot list that directory: `FindFirstFileExW` on
`\\.\pipe\*.*` opens the directory and `NtQueryDirectoryFile` then fails. `--pid` does not help; it
filters the same listing. The warning `pbir` prints (enable the preview feature) is wrong here: do
not send the user to Options.

Until Wine can list named pipes, use the substitutes in the `pbi-desktop:connect-pbid` skill's
`references/desktop-on-linux.md`:

| Windows | Linux under Wine |
|---|---|
| `pbir desktop list` | `systemctl --user is-active pbi-linux-session.service`, `hyprctl clients` or the window list |
| `pbir desktop refresh` | rewrite `definition.pbir` in place, then click "Apply external changes" |
| `pbir desktop screenshot` | screenshot the Desktop window |
| `pbir model -q` | `scripts/linux/pbid-dax.sh '<DAX>'` in that skill |

Retest: with Desktop open, `pbir desktop list --json`. Anything but `not_connected` means the
runtime learned to list pipes and this section can go.

## A Desktop save can break `pbir validate`

Power BI Desktop 2.159.1231.0 under powerbi-linux drops the `$schema` line from `<name>.pbip`,
`definition.pbir` and `definition.pbism` on every save, and writes `"version"` in its place in
`.pbi/editorSettings.json`. `pbir validate` then fails with
`SCHEMA_ERROR (root): '$schema' is a required property` on `definition.pbism`. The same files saved
by Desktop on Windows keep the line. After a save on Linux, restore those files from git before
validating or committing:

```bash
git checkout -- "<name>.pbip" "<name>.Report/definition.pbir" \
  "<name>.SemanticModel/definition.pbism" "<name>.SemanticModel/.pbi/editorSettings.json"
```

Desktop reopens the project either way. (Verified 2026-11-18. Cause not established.)
Retest: save an open PBIP from Desktop on Linux and run `git diff --stat`.

## `SCHEMA_DEGRADED` is not a Wine effect

`validate` warns once per visual that schema `visualContainer` 2.11.0 "is not available locally"
and that it used the bundled fallback. That is the bundled schema set of this `pbir` release, the
same on every platform.
