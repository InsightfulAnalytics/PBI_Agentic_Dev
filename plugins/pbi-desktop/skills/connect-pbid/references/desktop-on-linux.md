# Power BI Desktop on Linux (under Wine, through powerbi-linux)

The community project [powerbi-linux](https://github.com/cavallaro88/powerbi-linux) installs the
Windows build of Power BI Desktop into a managed Wine prefix and runs it as a systemd user session.
With it, a Linux host needs no Windows machine for the open, refresh, edit, verify loop. What
differs from Windows is which tools can reach Desktop.
(Desktop 2.159.1231.0, Wine 11.18, Hyprland. Verified 2026-11-18.)
Retest: `pbi-linux doctor`, then open a PBIP with `pbi-linux open` and run `pbir desktop list --json`
and `scripts/linux/pbid-dax.sh --port`.

## What reaches Desktop, and what does not

| Need | Windows | Linux under Wine |
|---|---|---|
| Open a project | double-click, `Start-Process` | `pbi-linux open "<file>.pbip"` |
| Is Desktop running | `pbir desktop list`, `Get-Process` | `pbir desktop list`; stock: `systemctl --user is-active pbi-linux-session.service` |
| DAX against the open model | `pbir model -q`, `query-dax.ps1` | `pbir model -q`; stock: `scripts/linux/pbid-dax.sh '<DAX>'` |
| Model edit | TOM `SaveChanges()` | edit TMDL on disk, then Apply external changes |
| Reload the canvas | `pbir desktop refresh` | `pbir desktop refresh`; stock: Apply external changes (below) |
| Screenshot | `pbir desktop screenshot` | `pbir desktop screenshot`; stock: screenshot the window (below) |
| Refresh data | the Refresh button | the Refresh button, clicked over CDP (below) |
| Validate, read, write PBIR | `pbir` | `pbir` (the `reports:pbir-cli` skill's `references/linux-wine.md`) |

"Stock" is a powerbi-linux runtime without the named pipe listing patch: there `pbir` cannot find
Desktop's pipe and `pbir desktop list` answers `not_connected` (`reports:pbir-cli`
`references/linux-wine.md`, "The Desktop bridge"). `pbid-dax.sh` works on either runtime.

Not available: PowerShell 5.1 and so every `.ps1` in this skill, UI Automation, `te --local`, DAX
Studio, Tabular Editor's GUI.

The `te` CLI's Linux build works on TMDL files (`te -m "<name>.SemanticModel" ls`, `validate`,
`bpa run`) but cannot reach Desktop: `--local` is Windows-only, and `-s localhost:<port> -d <database>`
fails with "This feature is supported for a .NET Core client only on Windows systems". For DAX against
the open model use `pbir model -q` or `pbid-dax.sh`. (te 0.8.1.1. Verified 2026-11-18.)
Retest: `te -s localhost:<port> -d <database> query -q 'EVALUATE ROW("x", 1)'`, with the port from
`scripts/linux/pbid-dax.sh --port` and the database the GUID in the `<guid>.<n>.db` folder name under the
profile's newest `AppData/Local/Microsoft/Power BI Desktop/AnalysisServicesWorkspaces/*/Data`.

## Paths and drives

Desktop sees the Linux filesystem as `Z:\`. An M parameter that holds a Windows path
(`W:\data\rules.csv`) resolves only if the prefix maps that drive: add a symlink in the profile's
`dosdevices` folder (`ln -s /path/to/work "<prefix>/dosdevices/w:"`; `<prefix>` is the `prefix`
value in `~/.local/share/powerbi-linux/active.json`). `winepath -w` then returns `W:\...`, and
Desktop opens the project under the same path it has on Windows. A new profile needs the link again.

## Open, and keep the window out of the way

```bash
env $(env | grep -o '^CLAUDE[A-Z_]*' | sed 's/^/-u /') pbi-linux open --diagnostics "/abs/path/Name.pbip"
systemctl --user stop pbi-linux-session.service      # close Desktop
```

`--diagnostics` opens a Chrome DevTools port for Desktop's WebView, which is the only way to click
anything from a script. The port is the first line of
`<prefix>/drive_c/users/<user>/AppData/Local/Microsoft/Power BI Desktop/WebView2/EBWebView/DevToolsActivePort`;
`http://127.0.0.1:<port>/json/list` names the pages (`reportView.html` is the report canvas,
`desktopDialogHost.html` a modal dialog). Without `--diagnostics` Desktop runs the same, but the
user does the clicking.

The window opens on the focused workspace. On Hyprland, a headless output keeps it off the user's
monitors and still renders, where a hidden workspace gets no frames:

```bash
hyprctl output create headless pbitest
hyprctl eval 'hl.monitor({ output = "pbitest", mode = "2560x1440@60", position = "20000x0", scale = 1 })'
# move each Desktop window to that output's workspace as it appears, then:
grim -o pbitest shot.png
hyprctl output remove pbitest
```

On a visible workspace, `grim -g "<x>,<y> <w>x<h>"` with the geometry from `hyprctl clients -j`
(class `pbidesktop.exe`).

## Clicking over CDP

Send `Runtime.evaluate` to the page's `webSocketDebuggerUrl` (any WebSocket client; pass no Origin
header).

- Refresh: the "Refresh now" banner button, or `button[data-unique-id=Ribbon-refreshQueriesSplit]`.
- Save: `button[aria-label=Save]`.
- A page tab: `[role=tab]` whose text is the page's display name. Call `element.click()`; a tab
  scrolled out of view has negative coordinates and a synthetic mouse click misses it.
- Wrap injected code in `try/catch`. An uncaught error in the page opens Desktop's "Something went
  wrong" dialog.

Never run a data refresh from outside (TMSL, TOM): the visuals are not told and keep the old data.

## Apply external changes needs a nudge

Desktop under Wine raises the "Apply external changes" banner only when a file directly inside
`<name>.Report` or `<name>.SemanticModel` is written. An edit deeper down (a `visual.json`,
`pages.json`, a `.tmdl` file) raises nothing, and neither does `touch`. After the last on-disk edit,
rewrite a top-level file with the same bytes:

```bash
python3 -c 'import sys,pathlib; p=pathlib.Path(sys.argv[1]); p.write_bytes(p.read_bytes())' \
  "<name>.Report/definition.pbir"          # or <name>.SemanticModel/definition.pbism
```

The banner appears at once. Click "Apply external changes" in `reportView.html`; when Desktop
holds unsaved edits a confirmation follows in `desktopDialogHost.html` with a button of the same
name. A report edit, a new page and a new TMDL measure all came through this way. Where `pbir`
reaches Desktop, `pbir desktop refresh` reloads report edits without the nudge; keep the nudge for
TMDL edits.
Retest: edit a `visual.json` of an open PBIP and watch for the banner for 20 seconds.

## Traps

- A project last saved by Desktop on Windows opened with "Some of the tables have incomplete or no
  data" and blank visuals until the first refresh.
- A save from a profile that has never been signed in drops `$schema` from four project files, and
  `pbir validate` then fails. Two registry values fix it: see `reports:pbir-cli`
  `references/linux-wine.md`.
- Do not attach `winedbg` to a hung Desktop: it blocks on the loader lock, and stopping it ends
  Desktop and the session. Take stacks with `sudo eu-stack -p <linux pid>`.
- A second `wine` process in Desktop's prefix while the session is stopped lingers a few seconds
  and makes the next `pbi-linux open` refuse to start. Run tools there only while Desktop is up.
