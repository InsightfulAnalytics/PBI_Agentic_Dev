# Time a DAX query against the running Power BI Desktop instance via ADOMD.
# Runs: 1 cold (fresh cache after ClearCache), then warm repeats.
# Windows PowerShell 5.1. DAX Studio DLLs (TE3's are .NET 8 and fail under PS 5.1).
param(
    [int]$Port = 0,
    [string]$QueryFile = (Join-Path $PSScriptRoot "demo\demo_slow_query.dax"),
    [int]$WarmRuns = 2
)

$ErrorActionPreference = 'Stop'
Add-Type -Path "C:\Program Files\DAX Studio\bin\Microsoft.AnalysisServices.AdomdClient.dll"
Add-Type -Path "C:\Program Files\DAX Studio\bin\Microsoft.AnalysisServices.Tabular.dll"

if ($Port -eq 0) {
    $pids = (Get-Process msmdsrv).Id
    $Port = (Get-NetTCPConnection -State Listen | Where-Object { $pids -contains $_.OwningProcess } |
        Select-Object -First 1 -ExpandProperty LocalPort)
}
$query = [System.IO.File]::ReadAllText($QueryFile)

# Database id for ClearCache
$srv = New-Object Microsoft.AnalysisServices.Tabular.Server
$srv.Connect("Data Source=localhost:$Port")
$dbid = $srv.Databases[0].ID

function Clear-ASCache {
    $xmla = '<ClearCache xmlns="http://schemas.microsoft.com/analysisservices/2003/engine"><Object><DatabaseID>' + $dbid + '</DatabaseID></Object></ClearCache>'
    $srv.Execute($xmla) | Out-Null
}

$conn = New-Object Microsoft.AnalysisServices.AdomdClient.AdomdConnection("Data Source=localhost:$Port")
$conn.Open()

function Invoke-Timed([string]$label) {
    $cmd = $conn.CreateCommand()
    $cmd.CommandText = $query
    $cmd.CommandTimeout = 600
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $rdr = $cmd.ExecuteReader()
    $rows = 0
    while ($rdr.Read()) { $rows++ }
    $rdr.Close()
    $sw.Stop()
    Write-Host ("{0}: {1:n0} ms  ({2} rows)" -f $label, $sw.Elapsed.TotalMilliseconds, $rows)
    return $sw.Elapsed.TotalMilliseconds
}

Clear-ASCache
Invoke-Timed "COLD (cache cleared)" | Out-Null
for ($i = 1; $i -le $WarmRuns; $i++) { Invoke-Timed "WARM run $i" | Out-Null }

$conn.Close()
$srv.Disconnect()
