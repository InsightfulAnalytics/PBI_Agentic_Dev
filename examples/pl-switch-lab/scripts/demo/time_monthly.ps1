<#
.SYNOPSIS
  Time the Monthly P&L before/after queries against the open PL Bridge Demo model.

.DESCRIPTION
  Runs the Deneb grid dataset query FIRST and the calculation-group dispatch query SECOND.
  That order is deliberate and it biases AGAINST the result being reported: both queries hit
  the same base measures, so whichever runs second gets a warmed storage engine. Running the
  grid first means the grid's cold number is genuinely cold and the matrix's cold number is
  the contaminated one.

  The warm pair is the fair comparison. Treat the matrix's cold number as a floor.

  Neither number includes the per-cell format-string tax -- an EVALUATE never evaluates a
  formatStringDefinition -- so the VISUAL gap will be larger than the query gap. Measure the
  visuals in Performance Analyzer and subtract; see
  docs/performance/03-format-string-and-cf-tax.md.

.PARAMETER Runs
  Executions per query. 3 gives one cold and two warm.

.PARAMETER Port
  Analysis Services port. Omit to auto-discover (pass it when several Desktops are open).

.EXAMPLE
  .\time_monthly.ps1
  .\time_monthly.ps1 -Runs 3 -Port 53409
#>
param(
    [int]$Runs = 3,
    [int]$Port = 0
)

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$runner = Join-Path $here "..\..\docs\performance\tools\run_dax.ps1"
if (-not (Test-Path $runner)) { throw "run_dax.ps1 not found at $runner" }

$queries = @(
    @{ Label = "Deneb grid dataset      "; File = "monthly_grid.dax" },
    @{ Label = "Calc-group dispatch     "; File = "monthly_dispatch.dax" }
)

$results = @{}
foreach ($q in $queries) {
    $file = Join-Path $here $q.File
    if (-not (Test-Path $file)) { throw "query not found: $file  (run gen_monthly_queries.py)" }
    Write-Output ""
    Write-Output "=== $($q.Label.Trim()) -- $($q.File)"
    $args = @{ QueryFile = $file; Runs = $Runs; Rows = 0 }
    if ($Port -ne 0) { $args.Port = $Port }
    $out = & $runner @args
    $out | ForEach-Object { Write-Output $_ }

    $times = @()
    foreach ($line in $out) {
        if ($line -match 'RUN \d+ \((cold|warm)\): (\d+) ms') { $times += [int]$Matches[2] }
    }
    if ($times.Count -lt 1) { throw "no timings parsed for $($q.File)" }
    $results[$q.File] = @{
        Cold = $times[0]
        Warm = if ($times.Count -gt 1) { ($times[1..($times.Count - 1)] | Measure-Object -Minimum).Minimum } else { $times[0] }
    }
}

$g = $results["monthly_grid.dax"]
$d = $results["monthly_dispatch.dax"]

Write-Output ""
Write-Output "================ query-level comparison (no format-string tax in either) ================"
Write-Output ("{0,-26} {1,10} {2,10}" -f "", "cold", "warm (best)")
Write-Output ("{0,-26} {1,10} {2,10}" -f "Calc-group dispatch", "$($d.Cold) ms", "$($d.Warm) ms")
Write-Output ("{0,-26} {1,10} {2,10}" -f "Deneb grid dataset", "$($g.Cold) ms", "$($g.Warm) ms")
if ($g.Warm -gt 0) {
    Write-Output ("{0,-26} {1,10} {2,10}" -f "speed-up", ("{0:N1}x" -f ($d.Cold / [double]$g.Cold)), ("{0:N1}x" -f ($d.Warm / [double]$g.Warm)))
}
Write-Output ""
Write-Output "Paste-ready row for docs/performance/README.md (fill in the two PA numbers):"
Write-Output ("| Lab - Monthly P&L, calc group -> Deneb | **<PA before> ms** PA / {0} ms query | **<PA after> ms** PA / {1} ms query | warm query {2} ms -> {3} ms. 15 items x 28 measures = 420 dispatched evaluations, 315 of them paying the format-string tax, replaced by one 12-row query. |" -f $d.Cold, $g.Cold, $d.Warm, $g.Warm)
