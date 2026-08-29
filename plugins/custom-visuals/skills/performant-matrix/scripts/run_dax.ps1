<#
.SYNOPSIS
  Time a DAX query against a local Power BI Desktop model over ADOMD.NET.

.DESCRIPTION
  The DAX-only half of the diagnostic in ../references/diagnosing.md. Performance Analyzer
  gives you the visual's total; this gives you the query underneath it. The difference is
  the per-cell tax (dynamic format strings + conditional-formatting measures), which an
  EVALUATE never pays.

  Discovers the Analysis Services port automatically from the msmdsrv processes that Desktop
  starts. With more than one Desktop instance open, pass -Port explicitly.

  Also probes for a usable ADOMD client DLL rather than assuming one path. What matters is
  that the DLL is a .NET FRAMEWORK build: Windows PowerShell 5.1 cannot load a .NET 8 one,
  and Add-Type throws ReflectionTypeLoadException ("Unable to load one or more of the
  requested types") when handed one. That error means the wrong build, not a missing ADOMD.
  The Tabular Editor 3 copy is .NET 8 and is deliberately not probed.

  Windows PowerShell 5.1 compatible.

.PARAMETER QueryFile
  Path to a .dax file holding one EVALUATE statement. Pin the slicer context inside it with
  CALCULATETABLE, or you are not measuring what the visual measures.

.PARAMETER Runs
  How many times to execute. Run at least twice: the first is cold, the rest warm. On a
  formula-engine-bound plan warm stays close to cold, and that similarity is the fingerprint.

.PARAMETER Port
  Analysis Services port. Omit to auto-discover.

.PARAMETER Rows
  How many result rows to print (default 200). Set 0 to time only.

.PARAMETER AdomdDll
  Full path to Microsoft.AnalysisServices.AdomdClient.dll. Omit to probe the usual locations.
  The ADOMD_DLL environment variable is honoured as a second override.

.EXAMPLE
  .\run_dax.ps1 -QueryFile .\dispatch.dax -Runs 2

.EXAMPLE
  .\run_dax.ps1 -QueryFile .\flat.dax -Runs 3 -Port 55599 -Rows 0
#>
param(
    [Parameter(Mandatory = $true)][string]$QueryFile,
    [int]$Runs = 2,
    [int]$Port = 0,
    [int]$Rows = 200,
    [string]$AdomdDll = ""
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path $QueryFile)) { throw "Query file not found: $QueryFile" }

# ---------------------------------------------------------------- ADOMD discovery
function Resolve-AdomdDll {
    param([string]$Explicit)

    $candidates = New-Object System.Collections.Generic.List[string]

    if ($Explicit)      { $candidates.Add($Explicit) }
    if ($env:ADOMD_DLL) { $candidates.Add($env:ADOMD_DLL) }

    # Bases, skipping any the environment does not define (32-bit hosts, odd images).
    $bases = @($env:ProgramFiles, ${env:ProgramFiles(x86)}, $env:LOCALAPPDATA) | Where-Object { $_ }

    # The official redistributable (ADOMD.NET client libraries). Highest version first.
    foreach ($base in $bases) {
        $root = Join-Path $base 'Microsoft.NET\ADOMD.NET'
        if (Test-Path $root) {
            Get-ChildItem -Path $root -Directory -ErrorAction SilentlyContinue |
                Sort-Object Name -Descending |
                ForEach-Object {
                    $candidates.Add((Join-Path $_.FullName 'Microsoft.AnalysisServices.AdomdClient.dll'))
                }
        }
    }

    # Tools that ship a .NET Framework copy alongside themselves. None needs to be running.
    foreach ($base in $bases) {
        $candidates.Add((Join-Path $base 'DAX Studio\bin\Microsoft.AnalysisServices.AdomdClient.dll'))
        $candidates.Add((Join-Path $base 'DaxStudio\bin\Microsoft.AnalysisServices.AdomdClient.dll'))
    }

    $rejected = New-Object System.Collections.Generic.List[string]
    $seen     = New-Object System.Collections.Generic.HashSet[string]

    foreach ($path in $candidates) {
        if (-not $path) { continue }
        if (-not $seen.Add($path.ToLowerInvariant())) { continue }
        if (-not (Test-Path $path)) { continue }
        try {
            Add-Type -Path $path
            return $path
        }
        catch {
            $rejected.Add(("  {0}`n      {1}" -f $path, $_.Exception.Message))
        }
    }

    $detail = if ($rejected.Count -gt 0) {
        "Found but could not load:`n" + ($rejected -join "`n") + "`n`nA ReflectionTypeLoadException here means the copy is a .NET 8 build (Tabular Editor 3 ships one). Windows PowerShell 5.1 needs a .NET Framework build.`n"
    } else {
        "No copy of Microsoft.AnalysisServices.AdomdClient.dll was found in any probed location.`n"
    }

    throw @"
No usable ADOMD.NET client DLL.

$detail
Probed:
  `$env:ADOMD_DLL
  %ProgramFiles%\Microsoft.NET\ADOMD.NET\<version>\
  %ProgramFiles(x86)%\Microsoft.NET\ADOMD.NET\<version>\
  %ProgramFiles%\DAX Studio\bin\
  %ProgramFiles(x86)%\DAX Studio\bin\
  %LOCALAPPDATA%\DaxStudio\bin\

Fix by installing either of:
  * ADOMD.NET client libraries (Microsoft, "Analysis Services client libraries",
    x64 MSI: x64_SQLAS_ADOMD.msi) -- the smallest install, no UI, no dependency on any tool.
    https://learn.microsoft.com/analysis-services/client-libraries
  * DAX Studio (https://daxstudio.org) -- ships a .NET Framework copy in its bin folder.
    You never have to open it.

Or pass -AdomdDll with the full path to a .NET Framework build, or set `$env:ADOMD_DLL.
"@
}

$dllPath = Resolve-AdomdDll -Explicit $AdomdDll
Write-Output "ADOMD: $dllPath"

# ---------------------------------------------------------------- port discovery
if ($Port -eq 0) {
    $msmd = Get-Process msmdsrv -ErrorAction SilentlyContinue
    if (-not $msmd) { throw "No msmdsrv process found - is a Power BI Desktop file open?" }
    $procIds = $msmd.Id
    # Get-NetTCPConnection avoids the IPv4/IPv6 duplicate rows netstat produces
    $ports = Get-NetTCPConnection -State Listen |
             Where-Object { $procIds -contains $_.OwningProcess } |
             Select-Object -ExpandProperty LocalPort -Unique
    if (-not $ports) { throw "msmdsrv is running but no listening port was found." }
    $ports = @($ports)
    if ($ports.Count -gt 1) {
        Write-Warning "Multiple Desktop instances listening on ports: $($ports -join ', '). Using $($ports[0]). Pass -Port to choose."
    }
    $Port = $ports[0]
}
Write-Output "Data Source=localhost:$Port"

$conn = New-Object Microsoft.AnalysisServices.AdomdClient.AdomdConnection("Data Source=localhost:$Port")
$conn.Open()

$dax = Get-Content $QueryFile -Raw -Encoding UTF8
$lastRows = New-Object System.Collections.Generic.List[string]

try {
    for ($i = 0; $i -lt $Runs; $i++) {
        $cmd = $conn.CreateCommand()
        $cmd.CommandText = $dax
        $cmd.CommandTimeout = 600

        $sw = [System.Diagnostics.Stopwatch]::StartNew()
        $reader = $cmd.ExecuteReader()
        $rowCount = 0
        $colCount = $reader.FieldCount
        $lastRows.Clear()

        while ($reader.Read()) {
            if ($rowCount -lt $Rows) {
                $vals = for ($c = 0; $c -lt $colCount; $c++) {
                    "$($reader.GetName($c))=$($reader.GetValue($c))"
                }
                $lastRows.Add(($vals -join " | "))
            }
            $rowCount++
        }
        $reader.Close()
        $sw.Stop()

        $label = if ($i -eq 0) { "cold" } else { "warm" }
        Write-Output ("RUN {0} ({1}): {2} ms, {3} rows x {4} cols" -f ($i + 1), $label, $sw.ElapsedMilliseconds, $rowCount, $colCount)
    }
}
finally {
    $conn.Close()
}

if ($Rows -gt 0) {
    Write-Output "--- rows (last run, first $Rows) ---"
    $lastRows | ForEach-Object { Write-Output $_ }
}
