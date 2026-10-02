# Desktop Process Lifecycle

**Power BI Desktop only, so Windows only.** Everything here is about the Desktop *process*: when it
holds a file, when it writes, when it reverts your edits, and how to make it pick up a change on
disk. None of it applies to the Analysis Services connection the rest of this skill drives, and none
of it applies where Desktop is not installed.

Where Desktop is unavailable (Linux, macOS outside a VM, a Codespace, CI), two substitutes cover
most of what an agent actually wants from it:

- **Seeing the report render**: render server-side with the `ExportTo` API instead (fabric-cli
  `references/reports.md`). It runs on trial capacity and renders certified custom visuals.
- **Knowing the model parses**: validate the TMDL offline with the binary bundled in the `pbip`
  plugin, `plugins/pbip/hooks/bin/tmdl-validate-<platform>` (`linux-x64`, `darwin-arm64`,
  `darwin-x64`, `windows-x64.exe`). It runs standalone on a path, no hook payload and no runtime
  needed: `tmdl-validate-linux-x64 <path>` prints `Valid TMDL (0 errors, 0 warnings)` or the errors.
  For a full parse-and-bind round trip of a whole `definition/` folder, see
  [load-tmdl-files.md](./load-tmdl-files.md).

## Check for an open Desktop instance before bulk-editing

Run `pbir desktop list` before any bulk edit of a PBIP. If Desktop is holding the project open,
coordinate with the user first: file locks stall edits, and the canvas state Desktop holds in memory
can have drifted from what is on disk. Where `pbir` is unavailable, `Get-Process PBIDesktop` plus the
port correlation in SKILL.md section 2a answers the same question.

For a generated edit, make the check part of the generator: guard it with a window-title or process
check so it refuses to run rather than racing Desktop.

## First open of a hand-authored PBIP shows no data

Desktop reports "Some of the tables have incomplete or no data" and does not auto-import. Nothing is
broken and reopening does not help: a hand-written model has never had its data image built. A
**forked** PBIP copied without `.pbi\cache.abf` behaves the same way: import tables are empty, and
every data-fed visual, Deneb included, draws only its static chrome (no marks, an empty category
axis). An empty Deneb visual straight after a fork is almost always this, not a spec bug, so refresh
before judging it. A model whose tables are inline `#table` partitions always refreshes, since it
needs no source. Refresh
through TOM against the running instance instead, see
[refresh-model.md](./refresh-model.md#hand-authored-pbip-no-data-on-first-open).

## The governing rule

**Do not leave Desktop's in-memory copy and the disk copy diverging.** That is the rule. "Close
Desktop before editing on disk" was one way of enforcing it, and is no longer the only one: after any
on-disk edit, either apply it into the running instance (next section) or close Desktop, before
touching the canvas again.

Divergence is what costs work. The two failure modes it produces are in the two sections after this
one: Desktop reverting your edits on close, and a truncated data cache from a force-kill.

## Desktop 26.08+ applies external changes in place

Edit PBIR or TMDL on disk while Desktop is **open** and a banner appears:

> This project's files were changed externally. Apply to view the latest changes.

with an **Apply external changes** button. Clicking it reloads the project in place. New pages, new
visuals, new measures and a new calculation group all came through without a restart. This retires
the close-and-reopen ritual for on-disk model edits.

It is a plain WPF button, so it is scriptable through the UIAutomationClient assemblies:

```powershell
$el = $root.FindFirst('Descendants', (New-Object Windows.Automation.PropertyCondition(
        [Windows.Automation.AutomationElement]::NameProperty, 'Apply external changes')))
$el.GetCurrentPattern([Windows.Automation.InvokePattern]::Pattern).Invoke()
```

Feature symbols in `Microsoft.PowerBI.Client.Windows.dll`: `ExternalChangesTracker`, `PBIPReload`,
`ProjectExternalChangesDetected`.

Limits: it is **PBIP/PBIR only** ("Reload is only supported for PBIP/PBIR files"), and Desktop warns
that applying "may overwrite your unsaved edits in Power BI Desktop", so land the canvas work first.

Search for the button from Desktop's **main window** element, not from the desktop root: the banner,
like the "Do you want to save your changes?" prompt, is drawn as a child inside the main window
rather than as a top-level window. On one build (2026-09-12) no invokable button was found at all,
and the banner had to be clicked by position, with coordinates read off a scaled screenshot. The
apply keeps the loaded data; measure edits show at once because measures evaluate at query time,
while a Power Query change still needs a refresh (see "A Power Query change empties its table" below).

If no banner appears after an on-disk edit, the build predates the feature: fall back to closing and
reopening, or to live TOM `SaveChanges()` for model changes. This is a *different* feature from the
`pbir` local API preview, and does not depend on it. See
[desktop-bridge.md](./desktop-bridge.md#apply-external-changes-is-not-the-pbir-local-api).
(Observed on Desktop 2.157.879.0, 26.08. Verified 2026-08-28.)
Retest: edit a `.tmdl` file of an open PBIP on disk and watch for the banner, or
`Get-Process PBIDesktop | Select-Object -ExpandProperty MainModule | Select-Object FileVersion`.

## Desktop silently reverts on-disk edits it had in memory

Desktop re-serializes the report and the model on save and on close. Edits made on disk while Desktop
is open, and never applied, are **silently reverted when Desktop closes**.

The evidence: a new measure added to `00_Measures.tmdl` vanished (the measure count went from 238
back to 237), a rebuilt `visual.json` reverted to its old query state, and two textboxes reverted. A
brand new `.tmdl` file that Desktop had never loaded **survived**. Everything Desktop held in memory
did not. That is the discriminator that makes this diagnosable: new files live, touched files die.

There is no warning and no error. The next query just fails with "The value for 'X' cannot be
determined". (Verified 2026-08-24.)

So: after any Desktop close, re-read the files from disk and confirm the edit is still there. On
26.08+ click **Apply external changes** rather than leaving the two copies diverged in the first
place.

## A field Desktop saw deleted stays broken until a reload

Desktop resolves a visual's field references when it **loads the report or applies a change**, not
on every render. If a measure disappears from the TMDL while Desktop is watching the folder (a
generator that deletes and re-inserts its block, a half-written file), Desktop can apply the model in
that window, drop the measure, and flag the visual with "Something's wrong with one or more fields.
See details". Putting the measure back fixes the model and **leaves the visual broken**: it survives a
re-render, a page revisit and a save, because a save writes the definition out and never reads it
back. Only a reload of the PBIP rebinds it.

So a field error that every offline check refutes is not proof of a broken report definition. Ask
whether the field was ever missing while Desktop was running: compare the process start time
(`Get-Process PBIDesktop | Select-Object StartTime`) with when the measure was written, and look for
a generator re-run in between. The generator side of this is in `pbip:tmdl`
`references/authoring-gotchas.md`, "Generators must strip by object name". (Verified 2026-09-12.)

## Two Desktop instances on one project

`Start-Process` on a `.pbip` whose project has auto-recovery enabled can leave **two** `PBIDesktop`
processes on the same project, each with its own `msmdsrv` port, one holding a stale model. A
port-scan loop that keeps the last port to answer can query the stale one and report every new
measure as broken. Run `pbir desktop list` first (one row per instance); without `pbir`, match each
port to its parent `PBIDesktop` PID (SKILL.md section 2a), or pick the port whose model has the most
measures. Then ask the user to close the extra instance. (Verified 2026-09-11.)

## A Power Query change empties its table until refreshed

After a column is added to a table's Power Query, the table is empty until it is refreshed: every
measure over it returns blank and `SUMMARIZECOLUMNS` drops the rows entirely, so a query returns a bare
header. That reads as a broken measure and is not. Refresh the table (`RequestRefresh` plus
`SaveChanges()`, or Refresh in Desktop) before concluding anything.

## A TOM refresh races Desktop's own UI

A programmatic data refresh (`Model.RequestRefresh(Full)` plus `SaveChanges()`) against the engine of
an **open** Desktop repeatedly collided with Desktop reacting to the same change: a Mashup "Could not
find a PackageSession" error, a banner saying calculation groups or relationships "need to be
manually refreshed" that never cleared, outright crashes, and a next launch that opened blank as
"Untitled". `pbir desktop refresh` interleaved with the TOM refresh made it worse.

- Prefer asking the user to click **Refresh** (or the banner's **Refresh now**) and save.
- If you must refresh programmatically, do it once, on a freshly opened and idle instance, and do not
  interleave a report reload with it.
- Verify without cycling Desktop: validate the files offline (`pbir validate`, `validate_pbip.py`)
  and check values with a DAX query.
- After calculation groups are added, Desktop shows "calculation groups need to be manually
  refreshed" while visuals already compute correctly; let the user clear it the same way.

## Never force-kill Desktop after a save

The title bar drops its `*` as soon as the **definition** is written, but Desktop keeps streaming the
data image to `.pbi\cache.abf` for tens of seconds afterwards. A 257 MB cache on a 75M-row model did
not even appear on disk until roughly 30 seconds after Ctrl+S.

Killing the process in that window truncates the file, and the next open dies with
`DecoderCorruptedData` and "The Decoder Fetch Uncompressed Data failed with error code 9". That reads
like model corruption but is not: the TMDL is untouched.

**Recovery:** rename or delete `.pbi\cache.abf`, reopen, run a full refresh.

**Prevention:** after Ctrl+S, poll `cache.abf` until its size is unchanged across about three
consecutive checks **and** the title bar has no `*`, then close gracefully.

```powershell
$cache = Join-Path $projectDir ".pbi\cache.abf"
$last = -1; $stable = 0
while ($stable -lt 3) {
    $size = if (Test-Path $cache) { (Get-Item $cache).Length } else { 0 }
    if ($size -eq $last -and $size -gt 0) { $stable++ } else { $stable = 0 }
    $last = $size
    Start-Sleep -Seconds 5
}
```

(Verified 2026-08-24.)

## CloseMainWindow() is not reliable on Desktop

`CloseMainWindow()` can be accepted, do nothing, and leave the process with `Responding=True` and its
title unchanged for minutes. Seen across three attempts totalling about 10 minutes. (Verified
2026-08-24.)

Do **not** escalate to `Stop-Process -Force`. That is the `cache.abf` corruption path above, and the
two facts are one rule: a hung polite close is not a licence to kill the process. Ask the user to
close Desktop, and check that `cache.abf` has stopped growing first so you can tell them it is safe.

The failure is specific to a Desktop window that is **not in the foreground**: `CloseMainWindow()`,
`WM_CLOSE` and invoking the title bar's Close button all did nothing, and no save prompt appeared to
answer, while Desktop sat behind another window. On a scratch file of your own, what worked was
invoking the quick-access **Save** through UI Automation, waiting for `cache.abf` to settle (above),
then ending the process. Never do that to the user's own file without asking. The UI Automation
routes are in [desktop-ui-automation.md](./desktop-ui-automation.md).
