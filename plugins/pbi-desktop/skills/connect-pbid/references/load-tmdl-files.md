# Loading TMDL / BIM Files into TOM

Load a local semantic model definition (TMDL folder or BIM file) into TOM for programmatic inspection and modification; no running Analysis Services instance required.

## Via Tabular Editor CLI (cross-platform)

Tabular Editor (TE2 or TE3) can load TMDL and BIM natively. Use the CLI (`TabularEditor.exe` on Windows, or the TE3 cross-platform binary) for scripted model inspection and modification.

### Load and inspect

```bash
# Open a TMDL folder in Tabular Editor (GUI)
TabularEditor.exe ./MyModel.SemanticModel/definition

# Open a BIM file in Tabular Editor (GUI)
TabularEditor.exe ./model.bim
```

To inspect model objects programmatically, read the TMDL files directly:

```bash
# List tables
ls ./MyModel.SemanticModel/definition/tables/*.tmdl

# Read a specific table definition (columns, measures, partitions)
cat ./MyModel.SemanticModel/definition/tables/Sales.tmdl

# Find a measure expression
grep -A5 "measure 'Total Revenue'" ./MyModel.SemanticModel/definition/tables/Sales.tmdl
```

### Modify and save

Edit TMDL files directly, or use Tabular Editor:

```bash
# Open in Tabular Editor, make changes, and save
TabularEditor.exe ./MyModel.SemanticModel/definition

# Or edit TMDL files directly; e.g. add a measure to Sales.tmdl:
#   measure 'YTD Revenue' = TOTALYTD([Total Revenue], 'Date'[Date])

# Convert between formats using Tabular Editor CLI (TE2)
TabularEditor.exe ./model.bim -S ./tmdl-out -F TMDL
TabularEditor.exe ./definition -S ./output/model.bim
```

### Deploy to Fabric

```bash
# Deploy local TMDL to a remote workspace via fab CLI
fab import "My Workspace.Workspace/My Model.SemanticModel" -i ./MyModel.SemanticModel -f
```

### Connect to remote model and save locally

```bash
# Export via fab CLI
fab export "My Workspace.Workspace/My Model.SemanticModel" -o ./local-copy -f
```

## Via PowerShell + TOM (Windows)

On Windows, load TMDL/BIM directly via the TOM .NET assemblies. This avoids any running AS instance; TOM deserializes the files into an in-memory Database object.

### Prerequisites

The TOM assemblies, loaded by a host that can load that build. **Probe for an installed copy before
running `nuget install`, and check the build's target framework against the host**: a `net45` or
`net472` build loads under Windows PowerShell 5.1, a `net6.0` or `net8.0` build needs `pwsh` 7 or a
`net8.0` project. See [assembly-discovery.md](./assembly-discovery.md) for the probe, the tool
table and the `ReflectionTypeLoadException` this prevents.

If nothing is installed, the NuGet fallback in SKILL.md section 1 lays the assemblies out under
`$env:TEMP\tom_nuget\<package>\lib\net45\`:

```powershell
$basePath = "<the lib\<tfm> folder the probe found, or the NuGet layout above>"
Add-Type -Path "$basePath\Microsoft.AnalysisServices.Core.dll"
Add-Type -Path "$basePath\Microsoft.AnalysisServices.Tabular.dll"
Add-Type -Path "$basePath\Microsoft.AnalysisServices.Tabular.Json.dll"
```

### Load TMDL folder

```powershell
$tmdlPath = "C:\Projects\MyModel.SemanticModel\definition"
$db = [Microsoft.AnalysisServices.Tabular.TmdlSerializer]::DeserializeDatabaseFromFolder($tmdlPath)
$model = $db.Model

Write-Output "Loaded: $($db.Name) (compat $($db.CompatibilityLevel))"
Write-Output "Tables: $($model.Tables.Count)"
```

### Offline validation before a Desktop open

`DeserializeDatabaseFromFolder` is also the cheapest possible pre-flight check. It parses a whole
`definition/` folder in seconds and reports syntax errors that would otherwise surface after a
multi-minute Desktop open, or worse, not at all.

**Do not accept "it parsed" as the check.** A generator can emit TMDL that parses clean while silently
dropping metadata: a measure expression written at the same indent level as its properties makes the
parser read `displayFolder:` and every following line as more DAX, the `formatStringDefinition` child
object disappears, and nothing complains. Deserialize and assert the round trip:

```powershell
$db    = [Microsoft.AnalysisServices.Tabular.TmdlSerializer]::DeserializeDatabaseFromFolder($tmdlPath)
$model = $db.Model
$measures = $model.Tables | ForEach-Object { $_.Measures }

# 1. count: did the generator add what it claimed, and only that?
Write-Output "measures: $(@($measures).Count)"

# 2. did the dynamic format strings survive?
Write-Output "with formatStringDefinition: $(@($measures | Where-Object { $_.FormatStringDefinition -ne $null }).Count)"

# 3. spot-check an expression, which is where a bad indent shows as swallowed properties
Write-Output $model.Tables["Sales"].Measures["Total Revenue"].Expression
```

Run the generator twice and assert the counts match, as an idempotency test.

Two limits. This validates **parse and bind only**: it says nothing about whether the DAX returns the
right number, and it cannot run a query (no engine). And it is not the only route: the `pbip` plugin
bundles a standalone validator, `plugins/pbip/hooks/bin/tmdl-validate-<platform>`, which takes a path
and needs no .NET assemblies at all, so it is the answer on Linux, macOS and CI.

### Load BIM file

```powershell
$bimPath = "C:\Projects\model.bim"
$json = [System.IO.File]::ReadAllText($bimPath)
$db = [Microsoft.AnalysisServices.Tabular.JsonSerializer]::DeserializeDatabase($json)
$model = $db.Model

Write-Output "Loaded: $($db.Name) (compat $($db.CompatibilityLevel))"
Write-Output "Tables: $($model.Tables.Count)"
```

### Inspect the loaded model

Once loaded, the `$model` object has the same TOM API as a live connection:

```powershell
# List tables
foreach ($table in $model.Tables) {
    Write-Output "$($table.Name): $($table.Columns.Count) cols, $($table.Measures.Count) measures"
}

# Read a measure
$m = $model.Tables["Sales"].Measures["Total Revenue"]
Write-Output "$($m.Name) = $($m.Expression)"

# List relationships
foreach ($rel in $model.Relationships) {
    $r = [Microsoft.AnalysisServices.Tabular.SingleColumnRelationship]$rel
    Write-Output "$($r.FromTable.Name)[$($r.FromColumn.Name)] -> $($r.ToTable.Name)[$($r.ToColumn.Name)]"
}
```

### Modify and save back

```powershell
# Add a measure
$measure = New-Object Microsoft.AnalysisServices.Tabular.Measure
$measure.Name = "YTD Revenue"
$measure.Expression = "TOTALYTD([Total Revenue], 'Date'[Date])"
$model.Tables["Sales"].Measures.Add($measure)

# Save back to TMDL
[Microsoft.AnalysisServices.Tabular.TmdlSerializer]::SerializeDatabaseToFolder($db, $tmdlPath)

# Or save as BIM
$json = [Microsoft.AnalysisServices.Tabular.JsonSerializer]::SerializeDatabase($db)
[System.IO.File]::WriteAllText("C:\export\model.bim", $json)
```

### Deploy the modified model

After modifying the in-memory model, serialize it back to TMDL, then deploy the folder to a remote workspace via the fab CLI:

```powershell
[Microsoft.AnalysisServices.Tabular.TmdlSerializer]::SerializeDatabaseToFolder($db, $tmdlPath)
fab import "WorkspaceName.Workspace/ModelName.SemanticModel" -i $tmdlPath -f
```

## Key Differences: Live Connection vs Local Files

| | Live connection (localhost) | Local files (TMDL/BIM) |
|---|---|---|
| **Source** | Running `msmdsrv.exe` process | Files on disk |
| **SaveChanges** | Writes to AS engine instantly | Must serialize back to disk |
| **Refresh** | Can trigger data refresh | No data; schema only |
| **DAX queries** | Yes (via ADOMD.NET) | No (no engine running) |
| **DMV queries** | Yes | No |
| **Undo** | `UndoLocalChanges()` discards unsaved | Revert files via git |
| **Deploy** | Already live | Needs `fab import` |

## Common Patterns

### Round-trip: pull, modify, push

```bash
# Pull from Fabric
fab export "Prod.Workspace/Sales.SemanticModel" -o ./working -f

# Modify locally (edit TMDL files directly or open in Tabular Editor)
# e.g. add to ./working/Sales.SemanticModel/definition/tables/Sales.tmdl:
#   measure 'New KPI' = DIVIDE([Revenue], [Target])

# Push back
fab import "Prod.Workspace/Sales.SemanticModel" -i ./working/Sales.SemanticModel -f
```

### Convert between formats

```bash
# BIM to TMDL (using Tabular Editor CLI)
TabularEditor.exe ./model.bim -S ./tmdl-output -F TMDL

# TMDL to BIM (using Tabular Editor CLI)
TabularEditor.exe ./definition -S ./output/model.bim
```
