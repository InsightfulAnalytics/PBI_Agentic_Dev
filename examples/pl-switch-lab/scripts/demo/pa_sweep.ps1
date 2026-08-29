<#
  Performance Analyzer sweep across the PL Bridge Demo report pages.

  Protocol, identical on every page so the numbers are comparable:
    1. select the page tab and let it render
    2. normalise the slicer rail to YEAR = 2026 and nothing else. The four rail slicers are
       cloned per page, NOT synced, so a stray selection on one page would silently compare
       two different filter contexts.
    3. optionally ClearCache over XMLA, so run 1 is genuinely cold
    4. Performance Analyzer: Clear, then Refresh visuals twice (cold, warm)
    5. read every visual row out of the pane

  Emits one CSV row per visual per run.
#>
param(
    [string[]]$Pages,
    [switch]$ClearCache,
    [string]$OutCsv,
    [int]$SettleMs = 2500,
    [int]$TimeoutSec = 240,
    [int]$MinVisuals = 0
)

Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
$AE  = [System.Windows.Automation.AutomationElement]
$TS  = [System.Windows.Automation.TreeScope]::Descendants
$IP  = [System.Windows.Automation.InvokePattern]::Pattern
$SIP = [System.Windows.Automation.SelectionItemPattern]::Pattern
$TP  = [System.Windows.Automation.TogglePattern]::Pattern

$sig = @'
using System;
using System.Runtime.InteropServices;
public class PWin {
  [DllImport("user32.dll")] public static extern void mouse_event(uint f,uint x,uint y,uint d,int e);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
}
'@
Add-Type $sig

$proc = Get-Process PBIDesktop -EA SilentlyContinue | Where-Object { $_.MainWindowTitle -match 'PL Bridge' } | Select-Object -First 1
if (-not $proc) { throw "PL Bridge Demo is not open in Power BI Desktop." }
$script:hwnd = $proc.MainWindowHandle

function Get-Root { [System.Windows.Automation.AutomationElement]::FromHandle($script:hwnd) }

function Find-Els([string]$Name, [string]$Type) {
    $all = (Get-Root).FindAll($TS, [System.Windows.Automation.Condition]::TrueCondition)
    $out = @()
    foreach ($e in $all) {
        if ($e.Current.Name -ne $Name) { continue }
        $ct = $e.Current.ControlType.ProgrammaticName -replace 'ControlType\.', ''
        if ($Type -and $ct -ne $Type) { continue }
        $out += $e
    }
    return $out
}

function Click-El($e) {
    try { $e.GetCurrentPattern($IP).Invoke(); return $true } catch {}
    $r = $e.Current.BoundingRectangle
    if ($r.Width -le 0) { return $false }
    [void][PWin]::SetForegroundWindow($script:hwnd)
    Start-Sleep -Milliseconds 250
    $px = [int]($r.X + $r.Width / 2)
    $py = [int]($r.Y + $r.Height / 2)
    [System.Windows.Forms.Cursor]::Position = New-Object System.Drawing.Point($px, $py)
    Start-Sleep -Milliseconds 200
    [PWin]::mouse_event(0x0002, 0, 0, 0, 0)
    Start-Sleep -Milliseconds 60
    [PWin]::mouse_event(0x0004, 0, 0, 0, 0)
    return $true
}

function Press-Button([string]$Name) {
    $e = Find-Els $Name 'Button' | Where-Object { -not $_.Current.IsOffscreen } | Select-Object -First 1
    if (-not $e) { return $false }
    [void](Click-El $e)
    return $true
}

$RAIL = @('2024','2025','2026','Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec',
          'Online','Retail','Wholesale','Bathroom','Bedding','Decor','Furniture','Kitchen',
          'Lighting','Non-Product','Outdoor','Storage')

function Get-Rail {
    $all = (Get-Root).FindAll($TS, [System.Windows.Automation.Condition]::TrueCondition)
    $state = @{}
    foreach ($e in $all) {
        $n = $e.Current.Name
        if ($RAIL -notcontains $n) { continue }
        if ($e.Current.IsOffscreen) { continue }
        $ct = $e.Current.ControlType.ProgrammaticName -replace 'ControlType\.', ''
        if ($ct -ne 'Button') { continue }
        if ($e.Current.BoundingRectangle.X -gt 700) { continue }
        try {
            $st = $e.GetCurrentPattern($TP).Current.ToggleState
            $state[$n] = @{ On = ($st -eq 'On'); El = $e }
        } catch {}
    }
    return $state
}

function Normalise-Rail {
    for ($pass = 0; $pass -lt 4; $pass++) {
        $st = Get-Rail
        if ($st.Count -eq 0) { Start-Sleep -Milliseconds 800; continue }
        $bad = @()
        foreach ($k in $st.Keys) {
            $want = ($k -eq '2026')
            if ($st[$k].On -ne $want) { $bad += $k }
        }
        if ($bad.Count -eq 0) {
            return (($st.Keys | Where-Object { $st[$_].On }) -join ',')
        }
        foreach ($k in $bad) {
            [void](Click-El $st[$k].El)
            Start-Sleep -Milliseconds 900
        }
        Start-Sleep -Milliseconds 1500
    }
    $st = Get-Rail
    return (($st.Keys | Where-Object { $st[$_].On }) -join ',')
}

function Read-PA {
    $all = (Get-Root).FindAll($TS, [System.Windows.Automation.Condition]::TrueCondition)
    $rows = @()
    foreach ($e in $all) {
        $ct = $e.Current.ControlType.ProgrammaticName -replace 'ControlType\.', ''
        if ($ct -ne 'TreeItem') { continue }
        if ($e.Current.IsOffscreen) { continue }
        if ($e.Current.Name -match '^Name (?<v>.+?)\. Duration (?<d>[\d,]+)\.?$') {
            $rows += [pscustomobject]@{
                Visual   = $Matches.v
                Duration = [int](($Matches.d) -replace ',', '')
                Y        = [int]$e.Current.BoundingRectangle.Y
            }
        }
    }
    return ($rows | Sort-Object Y)
}

function Wait-Idle {
    $stable = 0
    $prevKey = ''
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Milliseconds $SettleMs
        $rows = Read-PA
        $key = ($rows | ForEach-Object { "$($_.Visual)=$($_.Duration)" }) -join '|'
        # A slow visual has not logged its row YET, so "the list stopped changing" is not the
        # same as "the page finished". Require the expected visual count as well, or a matrix
        # that is still computing gets recorded as absent and the page total reads far too low.
        if ($key -ne '' -and $key -eq $prevKey -and $rows.Count -ge $MinVisuals) {
            $stable++
            if ($stable -ge 3) { return $rows }
        } else {
            $stable = 0
        }
        $prevKey = $key
    }
    Write-Warning "Wait-Idle timed out after $TimeoutSec s"
    return (Read-PA)
}

function Clear-EngineCache {
    $msmd = Get-Process msmdsrv -EA SilentlyContinue
    if (-not $msmd) { return "no msmdsrv" }
    $procIds = $msmd.Id
    $port = Get-NetTCPConnection -State Listen |
            Where-Object { $procIds -contains $_.OwningProcess } |
            Select-Object -ExpandProperty LocalPort -Unique | Select-Object -First 1
    if (-not $port) { return "no port" }
    $dll = "C:\Program Files\DAX Studio\bin\Microsoft.AnalysisServices.AdomdClient.dll"
    Add-Type -Path $dll -EA SilentlyContinue
    $conn = New-Object Microsoft.AnalysisServices.AdomdClient.AdomdConnection("Data Source=localhost:$port")
    $conn.Open()
    $dbid = $conn.Database
    $xmla = "<Batch xmlns='http://schemas.microsoft.com/analysisservices/2003/engine'><ClearCache><Object><DatabaseID>" + $dbid + "</DatabaseID></Object></ClearCache></Batch>"
    $cmd = $conn.CreateCommand()
    $cmd.CommandText = $xmla
    $cmd.CommandTimeout = 300
    [void]$cmd.ExecuteNonQuery()
    $cmd2 = $conn.CreateCommand()
    $cmd2.CommandText = 'EVALUATE ROW("x", 1)'
    $rdr = $cmd2.ExecuteReader()
    while ($rdr.Read()) { }
    $rdr.Close()
    $conn.Close()
    return "cleared (db=$dbid, port=$port)"
}

$results = @()
foreach ($pg in $Pages) {
    Write-Output "=================================================================="
    Write-Output "PAGE: $pg"
    $tab = Find-Els $pg 'TabItem' | Select-Object -First 1
    if (-not $tab) { Write-Warning "tab '$pg' not found"; continue }
    try { $tab.GetCurrentPattern($SIP).Select() } catch { [void](Click-El $tab) }
    Start-Sleep -Seconds 4

    $sel = Normalise-Rail
    Write-Output "  rail: $sel"
    Start-Sleep -Seconds 3

    if ($ClearCache) {
        Write-Output "  cache: $(Clear-EngineCache)"
        Start-Sleep -Seconds 2
    }

    [void](Press-Button 'Clear')
    Start-Sleep -Milliseconds 1200

    foreach ($run in 1, 2) {
        if (-not (Press-Button 'Refresh visuals')) { Write-Warning "no Refresh visuals button"; break }
        $rows = Wait-Idle
        foreach ($r in $rows) {
            $results += [pscustomobject]@{ Page = $pg; Run = $run; Visual = $r.Visual; Duration = $r.Duration; Rail = $sel }
        }
        $tot = ($rows | Measure-Object -Property Duration -Sum).Sum
        Write-Output ("  run {0}:  page total {1} ms across {2} visuals" -f $run, $tot, $rows.Count)
        foreach ($r in ($rows | Sort-Object Duration -Descending)) {
            Write-Output ("      {0,7} ms  {1}" -f $r.Duration, $r.Visual)
        }
        [void](Press-Button 'Clear')
        Start-Sleep -Milliseconds 1000
    }
}

if ($OutCsv) {
    $results | Export-Csv -Path $OutCsv -NoTypeInformation -Encoding UTF8
    Write-Output "wrote $OutCsv"
}
