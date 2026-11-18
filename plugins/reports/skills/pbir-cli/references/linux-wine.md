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

## The Desktop bridge

`pbir` finds Desktop's local API, the pipe `\\.\pipe\pbi-desktop-bridge-<PID>`, by listing
`\\.\pipe\`. Wine 11.18 cannot list that directory, so on a stock powerbi-linux runtime
`pbir desktop list` answers `not_connected` and `pbir model -q` answers "Local model is not open in
Power BI Desktop", even with Desktop open and the Desktop Bridge setting on. The warning `pbir`
prints there (enable the preview feature) is wrong: do not send the user to Options.

A runtime built with `wine-11.18-named-pipe-directory.patch` lists the pipes, and `desktop list`,
`refresh` and `screenshot` then work as on Windows. The patch lives in the
[InsightfulAnalytics fork](https://github.com/InsightfulAnalytics/powerbi-linux) of powerbi-linux,
not in a published runtime. (Local runtime 0.1.7-local.8, Desktop 2.159.1231.0. Verified 2026-11-18.)
Retest: with Desktop open, `pbir desktop list --json` names the instance.

`pbir model -q` also needs an ADOMD.NET client, which on Windows it borrows from DAX Studio, Tabular
Editor 3 or SSMS. For `model` commands the launcher links Desktop's own build of the client
(`Microsoft.PowerBI.AdomdClient.dll`) as
`~/.local/share/pbir-wine/adomd/Microsoft.AnalysisServices.AdomdClient.dll` and points
`PBIR_ADOMD_DIR` at that folder, unless the variable is already set. That reaches the model open in
Desktop; a workspace model over XMLA is untested.

On a stock runtime, use the substitutes in the `pbi-desktop:connect-pbid` skill's
`references/desktop-on-linux.md`:

| Windows | Linux under Wine, stock runtime |
|---|---|
| `pbir desktop list` | `systemctl --user is-active pbi-linux-session.service`, `hyprctl clients` or the window list |
| `pbir desktop refresh` | rewrite `definition.pbir` in place, then click "Apply external changes" |
| `pbir desktop screenshot` | screenshot the Desktop window |
| `pbir model -q` | `scripts/linux/pbid-dax.sh '<DAX>'` in that skill |

## A Desktop save can break `pbir validate`

Power BI Desktop writes `<name>.pbip`, `definition.pbir`, `definition.pbism` and
`.pbi/editorSettings.json` with `$schema` only while its `PbipWithSchema` switch is on. With it off,
a save drops the line (and writes `"version": "1.0"` in `editorSettings.json`), and `pbir validate`
then fails with `SCHEMA_ERROR (root): '$schema' is a required property` on `definition.pbism`. The
switch is the environment variable `PBI_pbipWithSchema` (`1`, `true` or `yes`) when it is set, else
the user setting of that name, else the signed-in account's switch from the Power BI service, which
Desktop then keeps as the user setting. A Desktop that has never been signed in, such as a new
powerbi-linux profile, has it off. A second switch of the same kind, `PbipWithSimplifiedDatasetConnectionString`,
picks `definitionProperties` 2.0.0 over 1.0.0 for `definition.pbir`. Nothing here is a Wine effect.

Turn both on once per Wine profile, with Desktop closed:

```bash
prefix=$(jq -r .prefix ~/.local/share/powerbi-linux/active.json)
runtime=$(jq -r .runtime ~/.local/share/powerbi-linux/active.json)
for v in PBI_pbipWithSchema PBI_pbipWithSimplifiedDatasetConnectionString; do
  WINEPREFIX="$prefix" "$runtime/bin/wine" reg add 'HKCU\Environment' /v "$v" /d 1 /f
done
WINEPREFIX="$prefix" "$runtime/bin/wineserver" -w
```

`powerbi-linux` strips `PBI_*` variables from the environment it starts Desktop with, so a shell
export does not reach Desktop; the registry's user environment does. The next save writes `$schema`
again, and the four files then match a Windows save byte for byte apart from line ends. (Desktop
2.159.1231.0, switches read from its IL, save tested on Linux. Verified 2026-11-18.)
Retest: save an open PBIP from Desktop on Linux and run `git diff --stat`.

## `SCHEMA_DEGRADED` is not a Wine effect

`validate` warns once per visual that schema `visualContainer` 2.11.0 "is not available locally"
and that it used the bundled fallback. That is the bundled schema set of this `pbir` release, the
same on every platform.
