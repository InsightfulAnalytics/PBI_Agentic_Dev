# Offline TMDL validation for PL Bridge Demo.
# The DAX Studio AMO (19.84.1.0) parser does NOT understand `function` (DAX UDFs),
# so it chokes on definition\functions.tmdl even though Desktop 26.08 accepts it.
# Workaround: parse a copy of definition\ with functions.tmdl removed. Everything
# else (tables, calc groups, measures, relationships) is still validated offline;
# the UDFs themselves can only be validated by opening the project in Desktop.
param(
    [string]$Definition = (Join-Path $PSScriptRoot "..\..\PL Bridge Demo.SemanticModel\definition")
)
$ErrorActionPreference = 'Stop'
Add-Type -Path "C:\Program Files\DAX Studio\bin\Microsoft.AnalysisServices.Tabular.dll"

$tmp = Join-Path $env:TEMP ("tmdlcheck_" + [guid]::NewGuid().ToString('N').Substring(0, 8))
Copy-Item $Definition $tmp -Recurse
$fn = Join-Path $tmp "functions.tmdl"
$hasUdf = Test-Path $fn
if ($hasUdf) { Remove-Item $fn }

try {
    $db = [Microsoft.AnalysisServices.Tabular.TmdlSerializer]::DeserializeDatabaseFromFolder($tmp)
    $m = $db.Model
    "PARSE OK  (compatibilityLevel $($db.CompatibilityLevel))"
    "  tables:        $($m.Tables.Count)"
    "  relationships: $($m.Relationships.Count)"
    $meas = ($m.Tables | ForEach-Object { $_.Measures.Count } | Measure-Object -Sum).Sum
    "  measures:      $meas"
    foreach ($t in $m.Tables | Where-Object { $_.CalculationGroup }) {
        "  calc group '$($t.Name)': $($t.CalculationGroup.CalculationItems.Count) items, precedence $($t.CalculationGroup.Precedence)"
    }
    if ($hasUdf) {
        $u = Select-String -Path $fn.Replace($tmp, $Definition) -Pattern '^function ' | Measure-Object
        "  UDFs:          $($u.Count) in functions.tmdl (NOT validated here -- Desktop is the referee)"
    }
} finally {
    Remove-Item $tmp -Recurse -Force
}
