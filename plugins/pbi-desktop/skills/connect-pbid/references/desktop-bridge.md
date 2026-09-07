# Desktop Bridge: driving the report canvas over the raw named pipe

Power BI Desktop exposes a second local API beside the Analysis Services engine: a
per-process JSON-RPC server on a Windows named pipe that controls the report canvas
(reload + snapshot). **When the `pbir` CLI is installed, use `pbir desktop list/refresh/screenshot`
instead of anything below; never drive the pipe from PowerShell when `pbir` is available.**
This raw-pipe path exists for machines without `pbir`: PowerShell straight to the pipe,
the same way this skill rawdogs TOM/ADOMD. (The `powerbi-desktop` npm CLI wraps
these same methods; the `pbir-format` and `pbir-cli` skills cover that wrapper path.)

Use it together with the model API: change the model with TOM, then reload and
snapshot the report to confirm the visuals reflect the change.

## The endpoint

- Pipe: `\\.\pipe\pbi-desktop-bridge-<PID>`, one per Desktop process. Discover it by
  enumerating the pipe directory for the prefix; `<PID>` is the PBIDesktop.exe id:

```powershell
[System.IO.Directory]::GetFiles("\\.\pipe\") |
  Where-Object { $_ -match 'pbi-desktop-bridge-(\d+)$' }
```

  The bridge needs its **preview setting enabled**: in Power BI Desktop, File > Options
  and settings > Options > Preview features, turn on the developer-mode / report-bridge
  preview feature and restart Desktop. If no pipe is found, that setting is off or
  Desktop is closed. **Pipe enumeration is not an availability check**, though: a pipe
  can be present and the bridge still drop the client (next section), so confirm with a
  `bridge.manifest` round trip before building a workflow on it.
- Protocol: JSON-RPC 2.0 with LSP-style `Content-Length` framing (vscode-jsonrpc over
  the pipe stream). No initialize handshake; connect and call.

## Symptom: the pipe exists but the client is dropped at handshake

There is a third state between "pipe present" and "pipe absent". The pipe can be
present for every Desktop process while the bridge still drops the client: a raw connect
to `\\.\pipe\pbi-desktop-bridge-<PID>` succeeds, the first write then fails with
**"Pipe is broken"**, and `pbir desktop list` reports that the local API is not reachable.
The bridge is accepting the connection and dropping the client at handshake rather than
refusing it outright. (Observed with the preview toggle in a particular state, not
documented product behaviour.)
Retest: connect to the pipe and call `bridge.manifest`.

So **call `bridge.manifest` first and treat its response as the availability test**. It
is the first call in both clients below for this reason, not as a formality. A pipe that
enumerates proves nothing.

When it fails this way, route around it rather than trying to repair it:

- **Reloads**: the Apply-external-changes banner (Desktop 26.08+) reloads a PBIP in
  place and does not depend on the bridge. See
  [desktop-lifecycle.md](./desktop-lifecycle.md).
- **Screenshots**: render server-side with the `ExportTo` API (fabric-cli
  `references/reports.md`), which needs no local Desktop at all.
- **Model work**: unaffected. The Analysis Services port is independent of the bridge
  (next section).

## When the local API preview is off

`pbir model -q` depends on the same preview feature. With it off, the command fails with:

```
Local model is not open in Power BI Desktop ... enable 'Enable external tool access to Power BI Desktop through secure local APIs'
```

That is a per-machine preview toggle, not a product limitation and not something a
command-line flag works around. **Go straight to ADOMD rather than spending turns fixing
`pbir`.** The direct ADOMD path in SKILL.md connects to the Analysis Services port and
works regardless of the toggle: the XMLA port is always there when Desktop has a model
loaded, the named pipe only when the preview is on.

Treat `pbir desktop list` as worth one attempt, not as a dependency. If it returns
nothing, correlate `msmdsrv` ports to their `PBIDesktop.exe` parents through the process
tree (SKILL.md section 2a) and read `$server.Databases[0].Name` per port.

## Apply-external-changes is not the `pbir` local API

Two separate Desktop features, easily conflated:

| | Desktop Bridge (this file) | Apply external changes |
|---|---|---|
| What it is | The "secure local APIs" preview: a per-process named pipe speaking JSON-RPC 2.0 | A banner and a WPF button in the Desktop UI that reloads a PBIP in place |
| Gated by | The preview setting, per machine | The Desktop build (26.08+) |
| Reloads | PBIR report definition (`file.reload/v1`) | The whole PBIP project, model included |
| Drivable by | `pbir desktop`, or the raw pipe | UIAutomation |

Microsoft documents the bridge at
`https://learn.microsoft.com/power-bi/developer/agentic/power-bi-desktop-bridge-overview`;
the banner's feature symbols live in `Microsoft.PowerBI.Client.Windows.dll`
(`ExternalChangesTracker`, `PBIPReload`, `ProjectExternalChangesDetected`).

The consequence that matters: the banner does **not** depend on the bridge or on that
preview setting, so it stays available on a machine where the bridge is off or broken.
Do not report the canvas as unreachable just because `pbir desktop list` fails. Full
treatment in [desktop-lifecycle.md](./desktop-lifecycle.md).

## Methods (params and returns, as the bridge defines them)

```yaml
bridge.manifest:            {}                                -> capability manifest (call first to confirm availability)
application.state.get/v1:   {}                                -> { currentFilePath, hasUnsavedChanges }
file.reload/v1:             { reloadModelDefinition: false }  -> { success }      # reloads on-disk PBIR into the live canvas
report.snapshot.capture/v1: { pageId, scale }                -> { payload, encoding, pageId, pageDisplayName, mimeType }
```

- `pageId` is the PBIR section id (e.g. `ReportSection1a2b3c`), not the display name.
- `scale` is 1 to 3 (2 is a good default for readable review).
- `report.snapshot.capture/v1` returns the PNG as a base64 string in `payload`
  (`encoding` is `base64`, `mimeType` is `image/png`).
- `file.reload/v1` with `reloadModelDefinition: false` reloads the report definition
  only; this is the canvas refresh after a PBIR edit.

## Raw PowerShell client

```powershell
# 1. connect to the bridge pipe for the target Desktop process
$procId = (Get-Process PBIDesktop -ErrorAction Stop | Select-Object -First 1).Id
$pipe = New-Object System.IO.Pipes.NamedPipeClientStream(".", "pbi-desktop-bridge-$procId",
          [System.IO.Pipes.PipeDirection]::InOut)
$pipe.Connect(5000)

# 2. JSON-RPC over the pipe with LSP Content-Length framing
function Read-Frame($pipe) {
    $win = ""; $one = New-Object byte[] 1; $hdr = New-Object Text.StringBuilder
    while ($true) {
        if ($pipe.Read($one, 0, 1) -le 0) { throw "pipe closed" }
        $c = [char]$one[0]; [void]$hdr.Append($c)
        $win = ($win + $c); if ($win.Length -gt 4) { $win = $win.Substring(1) }
        if ($win -eq "`r`n`r`n") { break }
    }
    $len = [int]([regex]::Match($hdr.ToString(), 'Content-Length:\s*(\d+)').Groups[1].Value)
    $buf = New-Object byte[] $len; $off = 0
    while ($off -lt $len) { $n = $pipe.Read($buf, $off, $len - $off); if ($n -le 0) { throw "eof" }; $off += $n }
    [Text.Encoding]::UTF8.GetString($buf) | ConvertFrom-Json
}
function Invoke-Bridge($pipe, [int]$id, [string]$method, $params) {
    $json   = @{ jsonrpc = "2.0"; id = $id; method = $method; params = $params } | ConvertTo-Json -Compress -Depth 10
    $body   = [Text.Encoding]::UTF8.GetBytes($json)
    $header = [Text.Encoding]::ASCII.GetBytes("Content-Length: $($body.Length)`r`n`r`n")
    $pipe.Write($header, 0, $header.Length); $pipe.Write($body, 0, $body.Length); $pipe.Flush()
    Read-Frame $pipe
}

# 3. calls
Invoke-Bridge $pipe 1 "bridge.manifest" @{} | Out-Null
$state = Invoke-Bridge $pipe 2 "application.state.get/v1" @{}              # confirm $state.currentFilePath matches your PBIP
Invoke-Bridge $pipe 3 "file.reload/v1" @{ reloadModelDefinition = $false } # refresh the canvas after a PBIR edit
$shot  = Invoke-Bridge $pipe 4 "report.snapshot.capture/v1" @{ pageId = "ReportSection1a2b3c"; scale = 2 }
[IO.File]::WriteAllBytes("page.png", [Convert]::FromBase64String($shot.payload))
$pipe.Dispose()
```

The reader reads header bytes one at a time up to `\r\n\r\n`, then exactly
`Content-Length` body bytes; do not wrap the pipe in a buffering `StreamReader`, it
will swallow the next frame's bytes.

## Model-and-report loop, rawdogged

```powershell
# model edit via TOM (this skill's main body), applied live
$model.Tables["Sales"].Measures["Revenue"].FormatString = "\$#,0"
$model.SaveChanges()
# then confirm the report reflects it, no reopen
Invoke-Bridge $pipe 5 "file.reload/v1" @{ reloadModelDefinition = $false }
$shot = Invoke-Bridge $pipe 6 "report.snapshot.capture/v1" @{ pageId = "ReportSection1a2b3c"; scale = 2 }
[IO.File]::WriteAllBytes("sales.png", [Convert]::FromBase64String($shot.payload))
```

On-disk PBIR (report) edits are picked up by `file.reload/v1`. On-disk TMDL (model)
edits are not, so for model changes either apply them into the running instance with
live TOM `SaveChanges()` (preferred here, it is already connected) or click **Apply
external changes** on Desktop 26.08+, which reloads the whole project including the
model. Either way, do not leave the in-memory copy and the disk copy diverging; see
[desktop-lifecycle.md](./desktop-lifecycle.md).

## Locating the open PBIP from the bridge

You do not need the file path in advance. Enumerate the pipe directory to auto-discover
the running Desktop PID, connect, call `bridge.manifest` to confirm the bridge is really
answering (enumeration alone does not, see the handshake symptom above), then call
`application.state.get/v1`; its `currentFilePath` is the open `.pbip`/`.pbix` on disk.
From it you have the project folder and its `.Report` (PBIR) and `.SemanticModel`
siblings, ready to drive with `pbir` / the `pbir-format` skill. This is more reliable than the recent-file-history
method (section 10), which reads history rather than the live instance.

```powershell
$procId = [System.IO.Directory]::GetFiles("\\.\pipe\") |
          ForEach-Object { if ($_ -match 'pbi-desktop-bridge-(\d+)$') { $matches[1] } } |
          Select-Object -First 1
# connect to pbi-desktop-bridge-$procId (above), then:
Invoke-Bridge $pipe 1 "bridge.manifest" @{} | Out-Null      # availability test, not a formality
$state     = Invoke-Bridge $pipe 2 "application.state.get/v1" @{}
$pbip      = $state.currentFilePath                              # e.g. C:\Reports\Sales\Sales.pbip
$reportDir = Join-Path (Split-Path $pbip) ((Split-Path $pbip -LeafBase) + ".Report")
```

## Higher-level wrapper: the pbir CLI

If the raw pipe client misbehaves (framing, encoding, or a build that changed a param
shape), use the `pbir desktop` commands (reports plugin `pbir-cli` skill); they speak the
same methods over the same pipe (the same preview setting must be enabled):

```bash
pbir desktop list                                  # list instances; pick the PID (`status` is an alias)
pbir desktop reload --pid <pid>                    # wraps file.reload/v1
pbir desktop screenshot "<report>/<page>.Page" --pid <pid> -o page.png   # wraps report.snapshot.capture/v1
```

Same endpoint, higher level. The `pbir-cli` skill documents this path in full.

## Notes

- macOS: run inside the Parallels VM, the same path this skill uses for PowerShell;
  see [parallels-macos.md](./parallels-macos.md).
- To CHANGE visuals, pages, or formatting, route to the `pbir-cli` skill; the bridge
  only reloads and snapshots, it never edits the report.
- This is the named-pipe API distinct from the Analysis Services XMLA port this skill
  connects to for the model; the two are independent.
