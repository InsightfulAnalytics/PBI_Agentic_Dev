<#
.SYNOPSIS
  Time a DAX query against a local Power BI Desktop model over ADOMD.NET.

.DESCRIPTION
  The DAX-only half of the diagnostic in ../01-diagnosing-slow-matrices.md. Performance
  Analyzer gives you the visual's total; this gives you the query underneath it. The
  difference is the per-cell tax (dynamic format strings + conditional-formatting measures),
  which an EVALUATE never pays.

  Discovers the Analysis Services port automatically from the msmdsrv processes that Desktop
  starts. With more than one Desktop instance open, pass -Port explicitly.

  Windows PowerShell 5.1. Do NOT use the Tabular Editor 3 copy of the ADOMD client -- it is
  .NET 8 and Add-Type throws ReflectionTypeLoadException under 5.1. The DAX Studio copy is
  .NET Framework and loads cleanly.

.PARAMETER QueryFile
  Path to a .dax file holding one EVALUATE statement. Pin the slicer context inside it with
  CALCULATETABLE or you are not measuring what the visual measures.

.PARAMETER Runs
  How many times to execute. Run at least twice: the first is cold, the rest warm. On a
  formula-engine-bound plan warm stays close to cold, and that similarity is the fingerprint.

.PARAMETER Port
  Analysis Services port. Omit to auto-discover.

.PARAMETER Rows
  How many result rows to print (default 200). Set 0 to time only.

.EXAMPLE
  .\run_dax.ps1 -QueryFile .\switch_dispatch.dax -Runs 2

.EXAMPLE
  .\run_dax.ps1 -QueryFile .\flat.dax -Runs 3 -Port 55599 -Rows 0
#>
param(
    [Parameter(Mandatory = $true)][string]$QueryFile,
    [int]$Runs = 2,
    [int]$Port = 0,
    [int]$Rows = 200,
    [string]$AdomdDll = "C:\Program Files\DAX Studio\bin\Microsoft.AnalysisServices.AdomdClient.dll"
)

if (-not (Test-Path $QueryFile)) { throw "Query file not found: $QueryFile" }
if (-not (Test-Path $AdomdDll)) {
    throw @"
ADOMD client not found at:
  $AdomdDll
Install DAX Studio, or pass -AdomdDll pointing at a .NET FRAMEWORK build of
Microsoft.AnalysisServices.AdomdClient.dll. The Tabular Editor 3 copy is .NET 8 and will not
load under Windows PowerShell 5.1.
"@
}

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
    if ($ports.Count -gt 1) {
        Write-Warning "Multiple Desktop instances listening on ports: $($ports -join ', '). Using $($ports[0]). Pass -Port to choose."
    }
    $Port = $ports[0]
}
Write-Output "Data Source=localhost:$Port"

Add-Type -Path $AdomdDll
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
