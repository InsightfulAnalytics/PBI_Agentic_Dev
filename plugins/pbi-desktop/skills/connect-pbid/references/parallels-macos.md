# Connecting from macOS via Parallels

When Power BI Desktop runs in a Parallels Windows VM, Claude Code on the macOS host executes PowerShell commands inside the VM using `prlctl exec`. This introduces path escaping, shared folder routing, and timeout considerations.


## Prerequisites

| Requirement | Description |
|-------------|-------------|
| **Parallels Desktop** | Installed with a Windows VM running |
| **Parallels CLI Tools** | `prlctl` available at `/usr/local/bin/prlctl` |
| **Shared Folders** | macOS `~/Desktop` (or `~/`) shared as `\\Mac\Home\Desktop` in the VM |
| **Power BI Desktop** | Open inside the VM with a model loaded |
| **NuGet** | Available in the VM (`winget install Microsoft.NuGet`) |


## Identify the VM

```bash
prlctl list --all
```

Returns running VMs with UUIDs and names. Use the VM name in all subsequent commands:

```
UUID                                    STATUS    NAME
{e65b134d-...}                          running   Macdows
```


## Find the Analysis Services Port

```bash
# Find msmdsrv.exe PIDs
prlctl exec <VM_NAME> cmd.exe /c "powershell.exe -NoProfile -Command \"(Get-Process msmdsrv -ErrorAction SilentlyContinue).Id\""

# Get listening ports for those PIDs
prlctl exec <VM_NAME> cmd.exe /c "netstat -ano | findstr LISTENING | findstr /R \"<PID1> <PID2>\""
```

Example output:

```
TCP    127.0.0.1:53706    0.0.0.0:0    LISTENING    1876
TCP    127.0.0.1:63431    0.0.0.0:0    LISTENING    9364
```

Each port corresponds to one open `.pbix` file.


## Execute PowerShell Scripts

### Inline Commands (Short)

For short commands, pass PowerShell inline via `prlctl exec`:

```bash
prlctl exec <VM_NAME> cmd.exe /c "powershell.exe -NoProfile -Command \"Get-Process msmdsrv\""
```

### Script Files (Recommended)

For longer scripts, write the `.ps1` file on the macOS host and execute via the Parallels shared folder:

```bash
# 1. Write the script on macOS
cat <<'EOF' > ~/Desktop/my_script.ps1
# PowerShell script content here
Write-Output "Hello from VM"
EOF

# 2. Execute in the VM via shared folder
prlctl exec <VM_NAME> cmd.exe /c "powershell.exe -NoProfile -ExecutionPolicy Bypass -File \"\\\\Mac\\Home\\Desktop\\my_script.ps1\""
```

The shared folder path `\\Mac\Home\Desktop\` maps to `~/Desktop/` on macOS.


## Quote Escaping

Paths with spaces (like `Power BI Desktop`) cause issues when passed through `prlctl exec` -> `cmd.exe` -> `powershell.exe`. Three layers of escaping interact.

**Use Base64-encoded commands for complex inline PowerShell:**

```bash
# 1. Write PowerShell script as plain text
SCRIPT='Get-ChildItem -Path "$env:LOCALAPPDATA\Microsoft\Power BI Desktop" -Recurse'

# 2. Encode to Base64 (UTF-16LE as PowerShell expects)
ENCODED=$(echo -n "$SCRIPT" | iconv -t UTF-16LE | base64)

# 3. Execute
prlctl exec <VM_NAME> cmd.exe /c "powershell.exe -NoProfile -EncodedCommand $ENCODED"
```

**Or use the script file method above to avoid escaping entirely.**


## Timeouts

Parallels VM commands run slower than native execution due to virtualization overhead and shared folder I/O. Always set a generous timeout:

```bash
# In Claude Code Bash tool, use timeout parameter of 120000ms (2 minutes)
# For NuGet installs or large model enumeration, use 180000ms (3 minutes)
```

The default 30-second timeout frequently causes premature termination and terminal corruption.


## TOM NuGet Installation

Install TOM inside the VM (one-time):

```bash
prlctl exec <VM_NAME> cmd.exe /c "powershell.exe -NoProfile -Command \"nuget install Microsoft.AnalysisServices.retail.amd64 -OutputDirectory $env:TEMP\tom_nuget -ExcludeVersion\""
```

The DLLs install under `net45\` (not `net472`). The correct path after install:

```
C:\WINDOWS\TEMP\tom_nuget\Microsoft.AnalysisServices.retail.amd64\lib\net45\
  Microsoft.AnalysisServices.Core.dll
  Microsoft.AnalysisServices.Tabular.dll
  Microsoft.AnalysisServices.Tabular.Json.dll
```


## Full Connection Script

Write this to a `.ps1` file on the macOS host and execute via `prlctl exec`:

```powershell
# Load TOM
$basePath = "$env:TEMP\tom_nuget\Microsoft.AnalysisServices.retail.amd64\lib\net45"
Add-Type -Path "$basePath\Microsoft.AnalysisServices.Core.dll"
Add-Type -Path "$basePath\Microsoft.AnalysisServices.Tabular.dll"

# Connect (replace PORT)
$server = New-Object Microsoft.AnalysisServices.Tabular.Server
$server.Connect("Data Source=localhost:<PORT>")

# Enumerate
foreach ($db in $server.Databases) {
    Write-Output "DATABASE: $($db.Name)"
    $model = $db.Model

    foreach ($table in $model.Tables) {
        Write-Output "  TABLE: [$($table.Name)]"
        foreach ($col in $table.Columns) {
            Write-Output "    [$($col.Name)] $($col.DataType)"
        }
        foreach ($m in $table.Measures) {
            Write-Output "    MEASURE: [$($m.Name)] = $($m.Expression)"
        }
    }

    foreach ($rel in $model.Relationships) {
        $sr = [Microsoft.AnalysisServices.Tabular.SingleColumnRelationship]$rel
        Write-Output "  REL: [$($sr.FromTable.Name)].[$($sr.FromColumn.Name)] -> [$($sr.ToTable.Name)].[$($sr.ToColumn.Name)]"
    }
}

$server.Disconnect()
```

Execute:

```bash
prlctl exec <VM_NAME> cmd.exe /c "powershell.exe -NoProfile -ExecutionPolicy Bypass -File \"\\\\Mac\\Home\\Desktop\\explore_pbi.ps1\""
```


## Known Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| `command not found: powershell.exe` | Calling PowerShell directly from macOS shell | Use `prlctl exec <VM_NAME>` to route through the VM |
| Path with spaces breaks | `Power BI Desktop` in path | Use script files or Base64-encoded commands |
| `net472` filter finds no DLLs | NuGet package only has `net45` | Filter for `net45` or remove framework filter |
| Terminal corruption after timeout | Process killed mid-output | Set timeout to 120000ms+; use `/clear` to recover |
| Port file not found | Windows Store install uses different path | Use the `netstat` port lookup above, or the port-discovery table in SKILL.md section 2 |
| Empty database on port | PBI file open but model not loaded | Check the other port; wait for model to finish loading |


## Quick Reference

```bash
# List VMs
prlctl list --all

# Find PBI ports
prlctl exec <VM> cmd.exe /c "netstat -ano | findstr LISTENING | findstr <PID>"

# Run PowerShell script in VM
prlctl exec <VM> cmd.exe /c "powershell.exe -NoProfile -ExecutionPolicy Bypass -File \"\\\\Mac\\Home\\Desktop\\script.ps1\""

# Install TOM in VM
prlctl exec <VM> cmd.exe /c "nuget install Microsoft.AnalysisServices.retail.amd64 -OutputDirectory %TEMP%\tom_nuget -ExcludeVersion"
```
