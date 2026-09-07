---
name: connect-pbid
version: 26.25
description: TOM and ADOMD.NET guidance via PowerShell for connecting to Power BI Desktop's local Analysis Services instance. Covers model enumeration, DAX queries, metadata modification, annotations, calendar definitions, field parameters, query tracing, DAX library package management (daxlib.org), and the Desktop Bridge for reloading and screenshotting the report canvas. Automatically invoke when the user mentions "Power BI Desktop", "Analysis Services port", "TOM", "ADOMD", "daxlib", "DAX library", "DAX UDF package", or asks to "connect to PBI Desktop", "query PBI Desktop with DAX", "modify PBI Desktop model", "add a measure to PBI", "capture visual queries", "create a field parameter", "validate DAX", "intercept DAX queries", "install daxlib", "add DAX SVG", "add IBCS", "reload the report canvas", "screenshot a report page", "Desktop Bridge", or to work with the model and report in Power BI Desktop together.
---

# Connect to Power BI Desktop (Local Analysis Services)

> **CRITICAL:** When you hit a mistake, a surprise, or a non-obvious behaviour while using this
> skill, record it in this skill folder: the `references/` file that owns the topic, or `SKILL.md`
> itself when the agent must know it before opening any reference. Write active reference notes,
> not a history of events (good: "QueryGroup returns an object; access `.Folder` for the name
> string"). Omit anything the skill already documents.
>
> There is no length cap, because the destination is a progressive-disclosure reference rather than
> an always-loaded memory file. There is a discipline instead: **one fact, one place.** Correct a
> stale entry, move a still-true entry that is in the wrong file, and **never delete a verified fact
> to make room.** The previous destination for these notes carried a 1500-character cap plus "prune
> stale entries when adding new ones", which functioned as a standing instruction to destroy
> verified knowledge. A per-agent memory file now holds machine-local facts only, per the boundary
> rule below: which assembly is installed here, whether a preview toggle is on. Everything else
> ships with the plugin.

<!-- boundary-rule:begin -->
## Where a new learning goes

Three questions, in order. Stop at the first yes.

**1. Is it true only because of how THIS machine is set up right now?**
An installed path, which identity you are logged in as, a preview toggle, a console codepage, which
build happens to be installed. Then it is machine-local.

Before accepting that answer, try to generalise it. Most machine-local facts are the residue of a
search that succeeded once, and the search is the portable part:

| Instead of recording | Record |
| --- | --- |
| the path where you found a DLL | the probe that finds it, and how to tell which host can load it |
| that a preview toggle is off here | the verbatim symptom string, and the route that works regardless |
| which account has rights here | the check that reveals the mismatch |
| that a script cannot find a binary | a fix to the script |

If the generalised form survives, it is not machine-local: take it to question 2 or 3. If nothing
survives, because the fact is about one machine, one tenant or one person, write it to the agent's
own memory file and nowhere else. It would mislead an agent anywhere else, and this repository is
public.

**A Codespace has no legitimate machine-local layer.** A fact about a Codespace is true of every
Codespace built from the same devcontainer, which makes it a fact about that image. Commit it.
Never start a memory file inside a container.

**2. Is it true only where Power BI Desktop runs, only in a Windows shell, or only at some tool
version?**
Then it is portable knowledge with a boundary. It goes in this skill's `references/`, with the
boundary in the sentence:

- Platform: open or close with the scope. "On a cp1252 Windows console ... Linux and macOS never
  hit this." "Power BI Desktop only."
- Version: write the symptom and the check as the instruction, never the version. "If `fab find`
  errors, run `fab --version` before assuming a syntax problem." Put the version and date you
  observed in brackets at the end, never in the imperative. A version in the imperative rots into a
  lie; a version in brackets rots into a footnote.
- A dated or version-pinned claim also carries a `Retest:` line naming the one command that settles
  it, plus a `Verified <date>` stamp. `scripts/check-skill-hygiene.py` reports the stale ones and
  fails on a version claim with no `Retest:`.

**A scoped statement that is a ROUTE is not finished until it names the substitute in the same
sentence.** "`pbir desktop screenshot` is Windows and Desktop only" leaves a Linux agent stuck.
"`pbir desktop screenshot` is Windows and Desktop only; where Desktop is unavailable, render
server-side with the `ExportTo` API (fabric-cli `references/reports.md`)" does not.

**3. Otherwise it is a fact about the file format, the product, or the service API.**
True everywhere, including a Codespace with no Desktop and no Windows. It goes in this skill's
`references/` with no qualifier, or in `SKILL.md` when the agent must know it before opening any
reference. This is the default and where most learnings land.

### Two tests that settle almost every case

- *Would this sentence still be true in a Linux Codespace with no Power BI Desktop?* Yes means
  question 3. No, but only because Desktop is missing, means question 2. No, because the sentence
  names a path, a version or a toggle, means question 1, so run the generalisation table first.
- *Could anyone else running this plugin act on it?* If not, question 1.

### When torn, file it in the more public place

An over-cautious scope clause on a portable fact costs a reader one clause. A machine-local fact
shipped as product knowledge misleads everyone who installs the plugin.

### Where to write it

If `PBI_MARKETPLACE_ROOT` is set, a writable clone of this marketplace is on the machine:
`bash "$PBI_MARKETPLACE_ROOT/scripts/record-learning.sh"` writes the note, runs the hygiene scan,
commits to a branch and opens a pull request.

If it is unset, the skills are loading from a read-only plugin cache and an edit there is discarded
by the next `plugin update`. Write the note to the agent's memory file instead, and say plainly in
the note that it still needs promoting into the plugin.

Nothing portable belongs in `~/.claude/rules/`, `.cursor/rules/` or `.github/instructions/`. Those
are per-machine and per-user.
<!-- boundary-rule:end -->

> **Note:** No MCP server required; do not use this skill with MCP servers or CLI tools. Use this skill to execute PowerShell commands directly via Bash to connect to Power BI Desktop's local Analysis Services instance.

Expert guidance for connecting to Power BI Desktop's local tabular model via the Tabular Object Model (TOM) and ADOMD.NET in PowerShell. Covers connection, enumeration, DAX queries, query traces, and full model modification.


## When to Use This Skill

Activate only when the Tabular Editor CLI or a Power BI MCP server is unavailable. TOM is more reliable than direct TMDL editing because it validates changes against the engine and applies them atomically.

**WARNING:** This skill does NOT support remote models via the XMLA endpoint. For Direct Lake models or models hosted in Fabric, use the Tabular Editor CLI or a Power BI MCP server instead; the local Analysis Services proxy does not expose Direct Lake databases to external TOM/ADOMD.NET connections.

## Model and report: routing

Power BI Desktop exposes the model and the report as two separate local surfaces. This skill owns the model surface and report-canvas verification, and routes report authoring to the right skill:

- **Model** (tables, columns, measures, relationships, roles, calculation groups, refresh): this skill, via TOM/ADOMD over the local Analysis Services instance. For model edits, prefer the `te` CLI or a model MCP when available; fall back to this skill's TOM when they are not (see "When to Use This Skill").
- **Report-canvas verification** (reload after edits, screenshot pages): this skill, the raw Desktop Bridge named-pipe API (section 13).
- **Report authoring** (visuals, pages, formatting, filters, bookmarks, themes): the `pbir-cli` skill in the reports plugin (it drives the `pbir` CLI). The Desktop Bridge here only reloads and screenshots; it never edits visuals. Route every visual or page change to `pbir-cli`.
- **Report JSON edited directly** (only when `pbir` is unavailable): the `pbir-format` skill in the pbip plugin.

Full loop on an open PBIP: change the model with TOM here, change visuals with `pbir-cli`, then reload and screenshot with the Desktop Bridge here to verify, and iterate.


## Critical

- Power BI Desktop must be open with a model loaded before connecting; if there are errors it is likely due to a "thin report" connected to a remote model, or a Direct Lake model (which uses a remote proxy that blocks external connections)
- The local Analysis Services instance only accepts connections from `localhost`
- Multiple PBI Desktop files open means multiple `msmdsrv.exe` processes on different ports. Connect to each port, read `$server.Databases[0].Name`, and ask the user which model to work with if more than one is found. When the `pbir` CLI is installed, prefer `pbir desktop list` to map each Desktop PID to the exact file it has open (see Section 2a)
- A workspace engine reporting `Databases: 0` belongs to a thin report (live connection to a remote model); there is no local model to connect to. Query thin reports through their remote model instead (`pbir model -q` routes there automatically)
- Always use a timeout of 60000ms or higher for PowerShell commands via Bash
- **Shell escaping**: Bash eats PowerShell `$` variables (`$env:TEMP`, `$server`, etc.) silently. Two options: (1) single-quote the `-Command` arg so Bash passes `$` literally to PowerShell; (2) write a `.ps1` file with a heredoc (single-quoted delimiter preserves `$`) and use `-File`. On macOS via Parallels, the `prlctl` -> `cmd.exe` -> `powershell.exe` chain adds extra escaping layers; `.ps1` files are more reliable for complex scripts but inline `-Command` with single quotes works for short commands.
- **Pass DAX into PowerShell as a single-quoted here-string.** A bracketed measure name (`[Total Revenue]`) parses as an attribute or type literal and `{}` as a script block, so DAX in an ordinary PowerShell string breaks. `@'...'@` is fully literal and fixes both; the closing `'@` must sit at column 0 on its own line or it is a parse error. Use `@'...'@`, not `@"..."@`, unless variable expansion is genuinely wanted. When the DAX has to go on a command line rather than into a variable, `--%` is the stop-parsing token (Windows PowerShell 5.1; omit it in bash or PowerShell 7+).
- **Always use `-ExecutionPolicy Bypass`** when running PowerShell commands or scripts. Windows blocks unsigned scripts by default.
- **Script file location** -- persistent scripts should go in the agent harness's scripts directory for the project (`.claude/scripts/`, `.github/scripts/`, `.cursor/scripts/`, `.gemini/scripts/`, etc. depending on the harness). Ephemeral or throwaway scripts should go in a project `tmp/` directory (which should be `.gitignored`). Do not write scripts to `./` root or `/tmp/`.
- **The Desktop process has its own rules, and two of them destroy work.** An on-disk edit made while Desktop holds the project is silently reverted when Desktop closes, and force-killing Desktop after a save truncates `.pbi\cache.abf` mid-write (the next open then fails with `DecoderCorruptedData`, which reads like model corruption and is not). Check `pbir desktop list` before any bulk edit, and read [desktop-lifecycle.md](./references/desktop-lifecycle.md) before closing, killing or editing around an open instance. Windows and Desktop only; where Desktop is unavailable, that file names the server-side render and offline-validate substitutes.
- Do not modify model metadata without explicit user direction
- Always call `$model.SaveChanges()` to persist modifications; without it, changes are discarded
- For macOS users running PBI Desktop in Parallels, see [parallels-macos.md](./references/parallels-macos.md)
- **Validation hooks** are active for this plugin; they validate DAX references, enforce measure metadata, check referential integrity, and report compatibility level upgrade opportunities. Toggle checks in `hooks/config.yaml`.


## 1. Prerequisites

| Requirement | Description |
|-------------|-------------|
| **Power BI Desktop** | Open with a model loaded (`.pbix` or `.pbip`) |
| **PowerShell** | Available on the machine running PBI Desktop |
| **NuGet CLI** | For package installation (`winget install Microsoft.NuGet`), only if the probe below finds nothing |
| **TOM NuGet Package** | `Microsoft.AnalysisServices.retail.amd64` -- model metadata |
| **ADOMD.NET Package** | `Microsoft.AnalysisServices.AdomdClient.retail.amd64` -- DAX queries |

**Probe before installing.** A Windows machine running Power BI tooling has usually shipped these assemblies already, and reusing one avoids a NuGet dependency the machine may not have. Probe `$env:ProgramFiles` for `Microsoft.AnalysisServices.AdomdClient.dll` and `Microsoft.AnalysisServices.Tabular.dll`, then check the hit's target framework against the host that will load it: see [assembly-discovery.md](./references/assembly-discovery.md).

Install both packages only if the probe finds nothing usable:

```powershell
$pkgDir = "$env:TEMP\tom_nuget"
if (-not (Test-Path "$pkgDir\Microsoft.AnalysisServices.retail.amd64")) {
    nuget install Microsoft.AnalysisServices.retail.amd64 -OutputDirectory $pkgDir -ExcludeVersion
}
if (-not (Test-Path "$pkgDir\Microsoft.AnalysisServices.AdomdClient.retail.amd64")) {
    nuget install Microsoft.AnalysisServices.AdomdClient.retail.amd64 -OutputDirectory $pkgDir -ExcludeVersion
}
```

Packages install DLLs under `lib\net45\`. Load with `Add-Type -Path`.

> **If a TOM operation fails** with a compatibility level error or missing type, the `.retail.amd64` package may be too old. The newer unified `Microsoft.AnalysisServices` package ships more recent TOM features, but it needs a matching host: `pwsh` 7 or a `net8.0` project, never Windows PowerShell 5.1, which throws `ReflectionTypeLoadException: Unable to load one or more of the requested types` on a .NET 8 assembly. See [assembly-discovery.md](./references/assembly-discovery.md) for the host/framework table and [daxlib.md](./references/daxlib.md) for package differences.


## 2. Quickstart

Find the port, load TOM, connect, enumerate -- in one script:

```powershell
# Find ports. Get-NetTCPConnection returns objects with a typed OwningProcess and
# LocalPort, so no text splitting and no IPv4/IPv6 de-duplication is needed.
# An empty $ports is the correct signal that Desktop is not open.
$pids  = (Get-Process msmdsrv -ErrorAction SilentlyContinue).Id
$ports = Get-NetTCPConnection -State Listen |
    Where-Object { $pids -contains $_.OwningProcess } |
    Select-Object -ExpandProperty LocalPort -Unique

# Load TOM. Substitute the lib\<tfm> folder the section 1 probe found, if it found one
# (see references/assembly-discovery.md); otherwise this is the NuGet layout.
$basePath = "$env:TEMP\tom_nuget\Microsoft.AnalysisServices.retail.amd64\lib\net45"
Add-Type -Path "$basePath\Microsoft.AnalysisServices.Core.dll"
Add-Type -Path "$basePath\Microsoft.AnalysisServices.Tabular.dll"

# Connect to the first port that hosts a model; skip thin-report engines (0 databases)
$server = New-Object Microsoft.AnalysisServices.Tabular.Server
foreach ($p in $ports) {
    $server.Connect("Data Source=localhost:$p")
    if ($server.Databases.Count -eq 0) {
        Write-Output "localhost:$p hosts no model (thin report); trying next port"
        $server.Disconnect()
        continue
    }
    break
}
$model = $server.Databases[0].Model

# Enumerate
foreach ($table in $model.Tables) {
    Write-Output "TABLE: [$($table.Name)] ($($table.Columns.Count) cols, $($table.Measures.Count) measures)"
}
Write-Output "Relationships: $($model.Relationships.Count)"

$server.Disconnect()
```

**Port discovery methods:**

| Method | Install Type | Command |
|--------|-------------|---------|
| Port file | Non-Store PBI Desktop | `Get-Content "$env:LOCALAPPDATA\Microsoft\Power BI Desktop\AnalysisServicesWorkspaces\*\Data\msmdsrv.port.txt"` |
| Port file | Store PBI Desktop | `Get-Content "$env:LOCALAPPDATA\Packages\Microsoft.MicrosoftPowerBIDesktop_*\LocalState\AnalysisServicesWorkspaces\*\Data\msmdsrv.port.txt"` |
| Listening ports | Any | `$pids = (Get-Process msmdsrv -ErrorAction SilentlyContinue).Id; Get-NetTCPConnection -State Listen \| Where-Object { $pids -contains $_.OwningProcess }` |

Prefer `Get-NetTCPConnection` over parsing `netstat -ano` text: it is the same cmdlet section 2a uses to map ports to PIDs, and it avoids both the positional whitespace splitting and the duplicate IPv4/IPv6 rows netstat prints per port.


## 2a. Correlating Ports to Reports (Multiple Instances)

A port alone does not identify the report it serves; correlate before connecting to avoid modifying the wrong model. With the `pbir` CLI and Desktop's "external tool access" preview feature enabled, `pbir desktop list` shows each Desktop PID with the exact file it has open. Map ports to those PIDs through the process tree (each `msmdsrv.exe` is a child of its `PBIDesktop.exe`):

```powershell
$conns = Get-NetTCPConnection -State Listen
foreach ($proc in Get-Process msmdsrv -ErrorAction SilentlyContinue) {
    $port = ($conns | Where-Object OwningProcess -eq $proc.Id | Select-Object -First 1).LocalPort
    $parent = (Get-WmiObject Win32_Process -Filter "ProcessId=$($proc.Id)").ParentProcessId
    Write-Output "port $port -> msmdsrv $($proc.Id) -> PBIDesktop $parent"
}
```

An engine reporting `Databases: 0` is a thin report's workspace; no local model exists. Query the remote model instead (`pbir model -q` routes there automatically).


## 3. Loading TOM, Connecting, and Saving Changes

### Load Assemblies

```powershell
# Or the lib\<tfm> folder the section 1 probe found: see references/assembly-discovery.md
$basePath = "$env:TEMP\tom_nuget\Microsoft.AnalysisServices.retail.amd64\lib\net45"
Add-Type -Path "$basePath\Microsoft.AnalysisServices.Core.dll"
Add-Type -Path "$basePath\Microsoft.AnalysisServices.Tabular.dll"
Add-Type -Path "$basePath\Microsoft.AnalysisServices.Tabular.Json.dll"
```

### Connect

```powershell
$server = New-Object Microsoft.AnalysisServices.Tabular.Server
$server.Connect("Data Source=localhost:<PORT>")

# PBI Desktop always has exactly one database
$db = $server.Databases[0]
$model = $db.Model
```

### Save Changes

Only save after all changes are made. After modifications, persist with:

```powershell
$model.SaveChanges()
```

Changes appear immediately in PBI Desktop. The user cannot undo with `Ctrl+Z` in Power BI, which is a disadvantage of this approach.

### Disconnect

**IMPORTANT:** Remember to disconnect after modifications are done. NEVER remain connected, which can lead to orphaned processes.

```powershell
$server.Disconnect()
```

### Connection Properties

```powershell
Write-Output "Server: $($server.Name)"
Write-Output "Version: $($server.Version)"
Write-Output "Database: $($db.Name)"
Write-Output "Compatibility: $($db.CompatibilityLevel)"
```


## 4. Refreshing the Model

Trigger a data refresh via TMSL (Tabular Model Scripting Language) or TOM's `RequestRefresh` API. This re-executes Power Query/M expressions and reloads data into the VertiPaq engine.

```powershell
# Full refresh of a single table via TMSL
$dbName = $server.Databases[0].Name
$tmsl = '{ "refresh": { "type": "full", "objects": [{ "database": "' + $dbName + '", "table": "Sales" }] } }'
$server.Execute($tmsl)

# Or via TOM RequestRefresh API
$model.Tables["Sales"].RequestRefresh([Microsoft.AnalysisServices.Tabular.RefreshType]::Full)
$model.SaveChanges()
```

| Refresh Type | Behaviour |
|-------------|-----------|
| `full` | Drop data, re-query source, recalculate DAX |
| `calculate` | Recalculate DAX only (no source query) |
| `automatic` | Engine decides per-partition what's needed |
| `dataOnly` | Re-query source but skip DAX recalculation |

For detailed examples and all refresh methods, see [refresh-model.md](./references/refresh-model.md).


## 5. Querying with DAX

### Load ADOMD.NET

```powershell
Add-Type -Path "$env:TEMP\tom_nuget\Microsoft.AnalysisServices.AdomdClient.retail.amd64\lib\net45\Microsoft.AnalysisServices.AdomdClient.dll"
```

### Open a Connection

```powershell
$conn = New-Object Microsoft.AnalysisServices.AdomdClient.AdomdConnection
$conn.ConnectionString = "Data Source=localhost:<PORT>"
$conn.Open()
```

### Execute a Query

All queries should preferably use `SUMMARIZECOLUMNS`.
Check `dax.guide` online for information about DAX functions, if necessary.

**Important:** ADOMD.NET returns fully-qualified column names without quotes around the table name (e.g., `Brands[Brand Class]` not `Brand Class`; measure projections come back as `[@Alias]`). Do not access columns by short name (`$reader["Brand Class"]`) -- it fails silently and returns blank. Use `$reader.GetName($i)` to discover column names, then access by index:

```powershell
$cmd = $conn.CreateCommand()
$cmd.CommandText = "EVALUATE SUMMARIZECOLUMNS('Table'[Column], ""@MeasureName"", [Measure])"

$reader = $cmd.ExecuteReader()

# Always iterate by index and use GetName() to map columns
while ($reader.Read()) {
    for ($i = 0; $i -lt $reader.FieldCount; $i++) {
        Write-Output "$($reader.GetName($i)): $($reader.GetValue($i))"
    }
    Write-Output "---"
}
$reader.Close()
```

### DAX Rules

- **Always fully qualify column references** with single-quoted table names: `'Sales'[Amount]`, not `[Amount]`. This applies everywhere -- measures, calculated columns, queries. Unqualified columns cause ambiguity errors.
- Table names are **always** single-quoted in DAX: `'Sales'[Amount]`, `'D&D 5E Monsters'[CR]`. Even simple names like `Sales` should be quoted as `'Sales'` for consistency.
- **Measure references are the only exception** -- they are always unqualified: `[Total Revenue]`
- String literals in DAX use double quotes, escaped as `""` inside PowerShell here-strings

### Query Patterns

```powershell
# Full table scan
$cmd.CommandText = "EVALUATE 'Sales'"

# Filtered with CALCULATETABLE
$cmd.CommandText = "EVALUATE CALCULATETABLE('Sales', 'Sales'[Region] = ""West"")"

# Aggregation
$cmd.CommandText = "EVALUATE SUMMARIZECOLUMNS('Date'[Year], ""@Total"", SUM('Sales'[Amount]))"

# Scalar via ROW
$cmd.CommandText = "EVALUATE ROW(""Result"", COUNTROWS('Sales'))"

# DMV queries (model metadata via SQL-like syntax)
$cmd.CommandText = "SELECT * FROM `$SYSTEM.TMSCHEMA_TABLES"
$cmd.CommandText = "SELECT * FROM `$SYSTEM.TMSCHEMA_MEASURES"
$cmd.CommandText = "SELECT * FROM `$SYSTEM.TMSCHEMA_COLUMNS"
$cmd.CommandText = "SELECT * FROM `$SYSTEM.TMSCHEMA_RELATIONSHIPS"
```

### Close Connection

```powershell
$conn.Close()
```


## 6. Modifying a Semantic Model

All modifications require a TOM connection (section 3). Call `$model.SaveChanges()` after each batch of changes.

### A. CRUD by Object Type

For full CRUD examples of every object type, see [tom-object-types.md](./references/tom-object-types.md).

**Common object types and their TOM collections** (not exhaustive -- see [Microsoft TOM API docs](https://learn.microsoft.com/en-us/dotnet/api/microsoft.analysisservices.tabular) for the full namespace):

| Object | Collection | Create | Read | Update | Delete |
|--------|-----------|--------|------|--------|--------|
| Table | `$model.Tables` | `New-Object ...Table` | `$model.Tables["Name"]` | Set properties | `.Remove($obj)` |
| Column | `$table.Columns` | `New-Object ...DataColumn` | `$table.Columns["Name"]` | Set properties | `.Remove($obj)` |
| Measure | `$table.Measures` | `New-Object ...Measure` | `$table.Measures["Name"]` | Set properties | `.Remove($obj)` |
| Calculated Column | `$table.Columns` | `New-Object ...CalculatedColumn` | Filter by type | Set `.Expression` | `.Remove($obj)` |
| Calculated Table | `$model.Tables` | Table + calculated partition | Check partition type | Set partition expr | `.Remove($obj)` |
| Relationship | `$model.Relationships` | `New-Object ...SingleColumnRelationship` | Index or filter | Set properties | `.Remove($obj)` |
| Hierarchy | `$table.Hierarchies` | `New-Object ...Hierarchy` | `$table.Hierarchies["Name"]` | Modify levels | `.Remove($obj)` |
| Role | `$model.Roles` | `New-Object ...ModelRole` | `$model.Roles["Name"]` | Set permissions | `.Remove($obj)` |
| Perspective | `$model.Perspectives` | `New-Object ...Perspective` | `$model.Perspectives["Name"]` | Toggle membership | `.Remove($obj)` |
| Culture | `$model.Cultures` | `New-Object ...Culture` | `$model.Cultures["en-US"]` | Set translations | `.Remove($obj)` |
| Partition | `$table.Partitions` | `New-Object ...Partition` | `$table.Partitions["Name"]` | Set source/expression | `.Remove($obj)` |
| Annotation | Any object | `$obj.Annotations.Add(...)` | `$obj.Annotations["Key"]` | Set `.Value` | `.Remove($obj)` |
| Expression | `$model.Expressions` | `New-Object ...NamedExpression` | `$model.Expressions["Name"]` | Set `.Expression` | `.Remove($obj)` |
| Data Source | `$model.DataSources` | `New-Object ...StructuredDataSource` | `$model.DataSources["Name"]` | Set connection | `.Remove($obj)` |
| Calculation Group | `$model.Tables` | Table with `CalculationGroup` | Filter by type | Add/remove items | `.Remove($obj)` |

**Quick examples (inline):**

```powershell
# Add a measure
$m = New-Object Microsoft.AnalysisServices.Tabular.Measure
$m.Name = "Total Revenue"
$m.Expression = "SUM(Sales[Amount])"
$m.FormatString = "`$#,0"
$m.Description = "Sum of all sales amounts"
$model.Tables["Sales"].Measures.Add($m)

# Add a relationship
$rel = New-Object Microsoft.AnalysisServices.Tabular.SingleColumnRelationship
$rel.Name = "Sales_to_Date"
$rel.FromColumn = $model.Tables["Sales"].Columns["DateKey"]
$rel.ToColumn = $model.Tables["Date"].Columns["DateKey"]
$rel.FromCardinality = [Microsoft.AnalysisServices.Tabular.RelationshipEndCardinality]::Many
$rel.ToCardinality = [Microsoft.AnalysisServices.Tabular.RelationshipEndCardinality]::One
$model.Relationships.Add($rel)

# Rename a column
$model.Tables["Sales"].Columns["amt"].Name = "Amount"

# Hide a table
$model.Tables["Bridge"].IsHidden = $true

# Delete a measure
$m = $model.Tables["Sales"].Measures["Old Measure"]
$model.Tables["Sales"].Measures.Remove($m)

# Add a role with RLS
$role = New-Object Microsoft.AnalysisServices.Tabular.ModelRole
$role.Name = "Region Filter"
$role.ModelPermission = [Microsoft.AnalysisServices.Tabular.ModelPermission]::Read
$model.Roles.Add($role)
$tp = New-Object Microsoft.AnalysisServices.Tabular.TablePermission
$tp.Table = $model.Tables["Sales"]
$tp.FilterExpression = "[Region] = USERNAME()"
$role.TablePermissions.Add($tp)

$model.SaveChanges()
```

### B. Discovering Object Types, Properties, and Setting Values

For complete TOM object type tables, PowerShell reflection patterns for discovering properties and enum values, and reading/setting property examples, see **`references/tom-object-types.md`**.


## 7. Validating DAX Expressions

Before saving measure/column expressions, validate them by test-executing against the live model. This catches syntax errors, missing column references, and circular dependencies without persisting bad metadata.

**Validating a *rewrite* takes more than this.** Desktop holds its own in-memory copy of the model,
so an `EVALUATE` issued straight after a TMDL edit on disk returns the **old** result and the rewrite
looks like it did nothing. Redefine the candidate in the query with `DEFINE MEASURE` and select the
live measure and the candidate side by side in one `ROW()`: see
[dax-expressions.md](./references/dax-expressions.md#testing-a-rewritten-measure-before-desktop-picks-up-the-disk-edit).
Watch the harness too, a `FILTER ( VALUES ( ... ) )` used to sample rows silently redefines an
`ALLSELECTED` measure ([dax-pitfalls.md](./references/dax-pitfalls.md#traps-in-the-test-query-itself)).

```powershell
# Validate a DAX expression before adding it as a measure
$testExpr = "SUM('Sales'[Amount]) / COUNTROWS('Sales')"
$cmd = $conn.CreateCommand()
$cmd.CommandText = "EVALUATE ROW(`"@Test`", $testExpr)"
try {
    $reader = $cmd.ExecuteReader()
    $reader.Close()
    Write-Output "VALID"
} catch {
    Write-Output "INVALID: $($_.Exception.Message)"
}
```

For calculated table expressions, wrap in `COUNTROWS`:

```powershell
$tableExpr = "CALENDAR(DATE(2020,1,1), DATE(2030,12,31))"
$cmd.CommandText = "EVALUATE ROW(`"@Count`", COUNTROWS($tableExpr))"
```

For filter expressions (RLS), test with `CALCULATETABLE`:

```powershell
$filterExpr = "'Sales'[Region] = `"West`""
$cmd.CommandText = "EVALUATE CALCULATETABLE(ROW(`"@OK`", 1), $filterExpr)"
```


## 8. Transactions and Rollback

`SaveChanges()` applies all pending modifications in a single implicit transaction. If any object fails validation, the entire batch rolls back automatically.

For multi-step workflows where inspection or rollback is needed before committing:

```powershell
try {
    # Make changes (not yet persisted)
    $model.Tables["Sales"].Measures["Revenue"].Name = "Total Revenue"
    $model.Tables["Sales"].Measures["Cost"].Name = "Total Cost"

    # Inspect before committing (changes are local to this connection)
    foreach ($m in $model.Tables["Sales"].Measures) {
        Write-Output "  [$($m.Name)]"
    }

    # Commit all changes atomically
    $model.SaveChanges()
    Write-Output "Committed"
} catch {
    # Discard all uncommitted changes
    $model.UndoLocalChanges()
    Write-Output "Rolled back: $($_.Exception.Message)"
}
```

`UndoLocalChanges()` discards all modifications made since the last `SaveChanges()`. This is the rollback mechanism for PBI Desktop; there is no explicit begin/commit transaction API on the local Analysis Services instance.


## 9. Model Validation

### Validate Before Saving

The TOM API does not expose a public `Validate()` method. Validation happens implicitly during `SaveChanges()` (which rolls back the entire batch on failure). For pre-save validation, inspect objects manually:

```powershell
# Check measures have valid expressions (non-empty)
foreach ($m in ($model.Tables | ForEach-Object { $_.Measures }) ) {
    if ([string]::IsNullOrWhiteSpace($m.Expression)) {
        Write-Output "WARNING: Measure [$($m.Name)] in [$($m.Table.Name)] has no expression"
    }
}

# Check relationships reference valid columns
foreach ($rel in $model.Relationships) {
    $sr = [Microsoft.AnalysisServices.Tabular.SingleColumnRelationship]$rel
    if ($sr.FromColumn -eq $null -or $sr.ToColumn -eq $null) {
        Write-Output "WARNING: Relationship [$($sr.Name)] has null column references"
    }
}

# Check for duplicate measure names across tables
$names = @{}
foreach ($m in ($model.Tables | ForEach-Object { $_.Measures })) {
    if ($names.ContainsKey($m.Name)) {
        Write-Output "WARNING: Duplicate measure name [$($m.Name)] in [$($m.Table.Name)] and [$($names[$m.Name])]"
    }
    $names[$m.Name] = $m.Table.Name
}
```

## 10. Finding the File Path and Editing Metadata Files

### Find the Open File Path

TOM does not expose the `.pbix`/`.pbip` file path directly.

**Primary method, the Desktop bridge:** `pbir desktop list` reports the exact file each running instance has open (requires the `pbir` CLI and the "external tool access" preview feature; see Section 2a). Use the methods below only when that is unavailable.

**Fallback, FileHistory in User.zip (works for Store and non-Store):**

```powershell
# Read the most recently opened file from PBI Desktop's settings
$userZip = "$env:USERPROFILE\Microsoft\Power BI Desktop Store App\User.zip"
# For non-Store installs: "$env:LOCALAPPDATA\Microsoft\Power BI Desktop\User.zip"

Add-Type -Assembly System.IO.Compression.FileSystem
$z = [System.IO.Compression.ZipFile]::OpenRead($userZip)
$entry = $z.Entries | Where-Object { $_.Name -eq 'Settings.xml' }
$reader = New-Object System.IO.StreamReader($entry.Open())
$content = $reader.ReadToEnd()
$reader.Close()
$z.Dispose()

# Extract FileHistory entries (ordered by lastAccessedDate, most recent first)
$history = ($content -split '(?=<Entry)' | Where-Object { $_ -match 'FileHistory' })[0]
$json = [regex]::Match($history, 'Value="s\[(.*?)\]"').Groups[1].Value -replace '&quot;', '"'
$files = $json | ConvertFrom-Json
$files | Select-Object filePath, lastAccessedDate | Format-Table -AutoSize
```

The first entry is the most recently opened file. Files on the Mac (via Parallels) appear as `\\Mac\Home\...` paths.

> **Limitation:** This is an imperfect method: it reads recent file history, not the currently open file. If multiple PBI Desktop instances are open, or the most recently accessed file in history isn't the one currently open, the result may be wrong. Confirm with the user if there is any ambiguity.

**Fallback, window title (non-Store PBI Desktop only):**

```powershell
Get-Process PBIDesktop -ErrorAction SilentlyContinue | Select-Object Id, MainWindowTitle
```

> **Note:** Store PBI Desktop (from Microsoft Store / WindowsApps) does not expose the file path in the window title. Use the User.zip method above instead.

**Fallback, msmdsrv command line (gives workspace path, not file path):**

```powershell
# Useful for finding the port; does NOT reveal the source file path
(Get-WmiObject Win32_Process -Filter "Name='msmdsrv.exe'").CommandLine
```

### Editing PBIP Metadata Files (Connection, Report, Model)

For `.pbip` projects, metadata files are human-readable JSON/TMDL on disk and can be read and modified directly.

**Common targets:**

| File | Purpose | Skill |
|------|---------|-------|
| `<Name>.Report/definition.pbir` | Report-to-model connection (`byPath` or `byConnection`) | `pbip` |
| `<Name>.Report/definition/report.json` | Report-level settings, theme, filters | `pbir-format` |
| `<Name>.SemanticModel/definition/*.tmdl` | Model metadata (tables, measures, relationships) | `tmdl` |
| `<Name>.SemanticModel/definition/expressions.tmdl` | M/Power Query shared expressions and parameters | `tmdl` |

For syntax, structure, and editing patterns for these files, load the relevant skill from the **pbip plugin**:
- **`pbip`** -- project structure, file types, `.pbir` connection, forking
- **`pbir-format`** -- `report.json`, `visual.json`, themes, filters, PBIR JSON schemas
- **`tmdl`** -- TMDL syntax, measures, columns, roles, relationships

### Reloading External File Edits

The rule is **do not leave Desktop's in-memory copy and the disk copy diverging**. An edit made on disk while Desktop holds the project, and never applied, is silently reverted when Desktop closes: it takes the model too, it produces no warning, and the eventual symptom is a query failing with "The value for 'X' cannot be determined". So after any on-disk edit, apply it into the running instance before touching the canvas again. In order of preference:

1. **TOM modifications** (`$model.SaveChanges()`) apply to the running instance immediately. Prefer this for model metadata; nothing on disk diverges in the first place.
2. **Apply external changes** (Desktop 26.08+, PBIP/PBIR only). Edit PBIR or TMDL on disk and Desktop shows a banner with an **Apply external changes** button that reloads the whole project in place, model included. It is a plain WPF button and is scriptable through UIAutomation. It does not depend on the local-API preview feature, so it works where the Desktop Bridge does not.
3. **PBIR report-definition edits** (pages, visuals) hot-reload into the open canvas with `pbir desktop refresh "Report.Report"` (PBIP/PBIR only, not `.pbix`; requires the preview feature; the Desktop Bridge `file.reload/v1` method, see section 13). Theme JSON edits under StaticResources do NOT hot-reload. If the instance has unsaved changes, Desktop saves first and may overwrite the on-disk edit.
4. **Everything else** (theme files, `.pbix`, a Desktop build older than 26.08): close Power BI Desktop, edit, reopen. Close it gracefully; never `Stop-Process -Force` after a save.

For the banner's scripted invoke, the silent-revert evidence, the `cache.abf` truncation that a force-kill causes, and the pre-edit check for an open instance, see [desktop-lifecycle.md](./references/desktop-lifecycle.md), which also carries the observed Desktop build behind the 26.08+ claim.
Retest: edit a `.tmdl` file of an open PBIP on disk and watch for the banner, or read `Get-Process PBIDesktop | Select-Object -ExpandProperty MainModule | Select-Object FileVersion`.

### Microsoft Documentation

| Topic | URL |
|-------|-----|
| **TOM API Reference** | `learn.microsoft.com/en-us/dotnet/api/microsoft.analysisservices.tabular` |
| **TOM Overview** | `learn.microsoft.com/en-us/analysis-services/tom/introduction-to-the-tabular-object-model-tom-in-analysis-services-amo` |
| **ADOMD.NET Reference** | `learn.microsoft.com/en-us/dotnet/api/microsoft.analysisservices.adomdclient` |
| **Client Libraries** | `learn.microsoft.com/en-us/analysis-services/client-libraries` |
| **DMV Reference** | `learn.microsoft.com/en-us/analysis-services/instances/use-dynamic-management-views-dmvs-to-monitor-analysis-services` |
| **DAX Reference** | `dax.guide` |
| **Compatibility Levels** | `learn.microsoft.com/en-us/analysis-services/tabular-models/compatibility-level-for-tabular-models-in-analysis-services` |

To retrieve current TOM/ADOMD.NET reference docs, use `microsoft_docs_search` + `microsoft_docs_fetch` (MCP) if available, otherwise `mslearn search` + `mslearn fetch` (CLI). Search based on the user's request and run multiple searches as needed to ensure sufficient context before proceeding.


## 11. Debugging DAX with EVALUATEANDLOG

`EVALUATEANDLOG(<Value>, [Label], [MaxRows])` wraps any DAX expression, returns it unchanged, and emits intermediate results as JSON via a trace event. Works in PBI Desktop only.

**Programmatic capture** via the TOM Trace API eliminates the need for external tools (DAX Debug Output, SQL Server Profiler, DAX Studio). Subscribe to the `DAXEvaluationLog` trace event (enum ID 135), capture events with a synchronized `ArrayList` via `Register-ObjectEvent`, and parse the JSON from `$Event.SourceEventArgs.TextData`.

**Critical implementation detail:** `Register-ObjectEvent -Action` runs in a separate PowerShell runspace. `$global:` variables inside the action block do not share scope. Pass a synchronized collection via `-MessageData`:

```powershell
$evalEvents = [System.Collections.ArrayList]::Synchronized((New-Object System.Collections.ArrayList))
$job = Register-ObjectEvent -InputObject $trace -EventName "OnEvent" -MessageData $evalEvents -Action {
    $Event.MessageData.Add($Event.SourceEventArgs) | Out-Null
}
```

**Trace delivery is asynchronous**: `DAXEvaluationLog` events typically arrive 2-3.5 seconds after the query returns, so a short fixed sleep misses them. Poll the captured-event count (up to ~10s in 500ms steps) before reading results. Warm-cache runs still emit the event; do not rely on cache clearing to make it fire. Clear the VertiPaq cache only when cold-cache timings are needed:

```powershell
$server.Execute('{ "clearCache": { "object": { "database": "' + $db.Name + '" } } }') | Out-Null
```

**Common debugging patterns:**

| Pattern | Approach |
|---------|----------|
| Measure chain decomposition | Wrap each intermediate step: `EVALUATEANDLOG([Step1], "Label1")` |
| Filter context inspection | Trace CALCULATE with vs without ALL/REMOVEFILTERS |
| BLANK vs zero detection | Trace the value before a comparison; BLANK = 0 is TRUE in DAX |
| Variable context trap | Trace VAR value alongside CALCULATE result; proves VAR is not re-evaluated |
| Grand total diagnosis | Trace numerator + denominator at row vs total grain |
| Table expression inspection | Wrap CALCULATETABLE result; trace shows actual rows feeding an aggregate |

For full setup, JSON payload structure, event batching behavior, and all debugging patterns, see [evaluateandlog-debugging.md](./references/evaluateandlog-debugging.md).


## 12. Performance Profiling

Programmatic equivalent of DAX Studio's Server Timings. Subscribe to `QueryEnd`, `VertiPaqSEQueryEnd`, and `VertiPaqSEQueryCacheMatch` trace events to measure Formula Engine (FE) vs Storage Engine (SE) time per query.

**Key formula:** FE time = Total duration - sum(SE scan durations)

**Important:** `VertiPaqSEQueryCacheMatch` does NOT support `Duration` or `CpuTime` columns; adding them causes `$trace.Update()` to throw. Only add `TextData` + `EventClass` for cache match events.

**Workflow:**
1. Create trace with performance events (see reference for column compatibility)
2. Clear cache (TMSL `clearCache`) for cold timings
3. Execute DAX via ADOMD.NET
4. Parse trace events: `QueryEnd` for total, `VertiPaqSEQueryEnd` for per-scan SE durations
5. Compare cold vs warm cache to measure cache benefit

**Statistical sampling:** Single measurements are noisy. Always take 6-12 samples and compare medians (not means) before and after a change. If ranges overlap significantly, the difference is likely noise. Discard the first cold-cache run as warm-up. See the reference for a `Measure-QueryMedian` helper.

**Visual query profiling:** Construct SUMMARIZECOLUMNS queries from PBIR `visual.json` definitions. Column projections become group-by columns; measure projections become measure references; `Aggregation.Function` maps to SUM (0), MIN (1), MAX (2), COUNT (3), AVERAGE (4).

For full setup, timing interpretation, sampling patterns, and PBIR-to-DAX translation, see [performance-profiling.md](./references/performance-profiling.md).


## 13. Working with the Report Canvas (Desktop Bridge)

The TOM connection above drives the **model**: tables, measures, relationships, roles, refresh. It cannot touch the **report canvas** (pages and visuals). Power BI Desktop exposes a second, separate local API for that: the **Desktop Bridge**, a per-process JSON-RPC server on the Windows named pipe `\\.\pipe\pbi-desktop-bridge-<PID>`. Pair the two to change the model and immediately confirm the report re-renders.

When the `pbir` CLI is installed, it wraps this same pipe; prefer it over driving the pipe raw:

```powershell
pbir desktop list                                                             # PID + open file per instance
pbir model --% "Report.Report" -q "EVALUATE ROW(""Check"", [New Measure])"   # engine-level check
pbir desktop refresh "Report.Report"                                          # reload on-disk PBIR into the canvas
pbir desktop screenshot "Report.Report/Page Name.Page" -o verify.png          # inspect rendering
```

The `--%` stop-parsing token prevents Windows PowerShell 5.1 from stripping the embedded quotes; omit it in bash or PowerShell 7+.

Without `pbir`, drive the pipe raw from PowerShell, the same way this skill drives TOM/ADOMD. It requires the Desktop bridge **preview setting** enabled (File > Options and settings > Options > Preview features, then restart). Auto-discover the PID by enumerating the pipe directory; then over JSON-RPC: `application.state.get/v1` returns the open file path (`currentFilePath`, so the bridge can locate the PBIP on disk), `file.reload/v1` reloads the on-disk PBIR into the canvas, and `report.snapshot.capture/v1` returns a page PNG.

Model-plus-report loop: edit the model with TOM and `$model.SaveChanges()` (applies live), then `reload` and `screenshot` the report to confirm visuals reflect the change (a renamed measure, a new format string, a repaired relationship). On-disk **report** (PBIR) edits are picked up by `reload`; on-disk **model** (TMDL) edits are not, so apply them with live TOM `SaveChanges()` or with the **Apply external changes** banner on Desktop 26.08+ (see [desktop-lifecycle.md](./references/desktop-lifecycle.md) for the observed build and the retest). Theme files under StaticResources still need a reopen. The bridge drives the Windows app, so on macOS run it inside the Parallels VM (see [parallels-macos.md](./references/parallels-macos.md)).

For the full command set, PID selection, the JSON-RPC method surface (`bridge.manifest`, `application.state.get/v1`, `file.reload/v1`, `report.snapshot.capture/v1`), and how it complements the Analysis Services local API, see [desktop-bridge.md](./references/desktop-bridge.md). To CHANGE visuals, pages, formatting, filters, or bookmarks, route to the `pbir-cli` skill (reports plugin); the Desktop Bridge here only reloads and screenshots, it never edits the report.

Alternative path (only if driving the raw pipe runs into trouble, framing, encoding, or a build that changed a param shape): use the `pbir desktop` commands (reports plugin `pbir-cli` skill), which wrap these same methods. See [desktop-bridge.md](./references/desktop-bridge.md).


## References

**Skill references:**

- [TOM Object Types CRUD](./references/tom-object-types.md) - Full CRUD examples for every object type including UDFs, Direct Lake, KPI note
- [Annotations and Extended Properties](./references/annotations.md) - Standard PBI annotations, Tabular Editor table groups, auto date/time, field parameters, query groups, custom annotations
- [Calendar Column Groups](./references/calendar-column-groups.md) - Gregorian, fiscal, and ISO week-based calendar definitions via TOM; time units, primary/associated columns
- [DAX Expression Locations](./references/dax-expressions.md) - Where DAX appears in a model: measures, calculated columns/tables, calc items, format strings, detail rows, RLS, UDFs. Also how to prove a rewritten measure with `DEFINE MEASURE` before landing the TMDL edit
- [DAX Pitfalls](./references/dax-pitfalls.md) - Deprecated/not-recommended functions, non-existent functions agents hallucinate from SQL/Python/M, common syntax mistakes, BLANK vs NULL, and the traps in the *test query* that make a correct measure look broken
- [EVALUATEANDLOG Debugging](./references/evaluateandlog-debugging.md) - Programmatic DAX debugging via TOM Trace API; capture intermediate results, cache clearing, six debugging patterns for common DAX issues
- [Performance Profiling](./references/performance-profiling.md) - DAX Server Timings via Trace API; FE/SE time split, cold/warm cache comparison, PBIR visual-to-DAX translation, trace event column compatibility
- [Query Listener](./references/query-listener.md) - Capture live visual DAX queries via DMV polling; interpret query structure, timings, filter patterns
- [Export Model](./references/export-model.md) - Export to BIM/TMDL via Tabular Editor CLI, fab CLI, or TOM serializer
- [Loading TMDL/BIM Files](./references/load-tmdl-files.md) - Load local TMDL folders or BIM files into TOM offline; inspect, modify, serialize back, deploy via fab CLI. Also the seconds-not-minutes validation gate to run before a Desktop open, and why "it parsed" is not the check
- [VertiPaq Statistics](./references/vertipaq-stats.md) - Column cardinality, dictionary/data size, memory by table, server timings via DMVs
- [Refresh Model](./references/refresh-model.md) - All refresh methods (TMSL, TOM RequestRefresh, ADOMD.NET), including the hand-authored PBIP that opens with "Some of the tables have incomplete or no data"
- [macOS + Parallels Guide](./references/parallels-macos.md) - Connecting from macOS when PBI Desktop runs in a Parallels VM
- [DAX Library Packages](./references/daxlib.md) - Installing reusable DAX UDF packages from daxlib.org; DaxLib.SVG, PowerofBI.IBCS, package structure, annotations
- [Desktop Bridge (report canvas)](./references/desktop-bridge.md) - Reload + screenshot the open report canvas over the raw named-pipe JSON-RPC API (PowerShell; or the `pbir desktop` commands); pairing model (TOM) edits with report verification. Also: the pipe-present-but-broken symptom, what to do when the local-API preview is off, and how the bridge differs from Apply external changes
- [Desktop Process Lifecycle](./references/desktop-lifecycle.md) - Windows and Desktop only. Check before bulk-editing, Apply external changes on 26.08+, the silent revert of on-disk edits, the `cache.abf` truncation a force-kill causes, and why `CloseMainWindow()` is not the escalation. Names the headless substitutes for a machine with no Desktop
- [Assembly Discovery](./references/assembly-discovery.md) - Probe for an installed ADOMD.NET or TOM assembly before running `nuget install`, then match its target framework to the host (`net45`/`net472` under Windows PowerShell 5.1, `net6.0`/`net8.0` under `pwsh` 7 or a `net8.0` project). Covers the `ReflectionTypeLoadException` misdiagnosis and the Linux/macOS routes

**CLI tools at the skill root:**

- **`daxlib`** -- CLI for browsing, downloading, and installing DAX library packages from daxlib.org. Script at `daxlib.sh` (requires bash + jq). Model operations (add/update/remove) call `scripts/daxlib-tom/` via `dotnet run` (requires .NET 8 SDK). On macOS, model operations route through Parallels automatically. See [daxlib.md](./references/daxlib.md) for full command reference.

**Agents:**

- **`query-listener`** -- Dispatch to capture live visual DAX queries in real time; polls `DISCOVER_SESSIONS` and reports query text + timings

**Example scripts in `scripts/`:**

- `connect-and-enumerate.ps1` - Connect to PBI Desktop and list all tables, columns, measures, relationships
- `explore-model.ps1` - Hierarchical metadata enumeration (tables, columns, measures, hierarchies, partitions, relationships, roles, perspectives, cultures, expressions, data sources)
- `query-dax.ps1` - Execute DAX queries via ADOMD.NET with formatted output
- `refresh-table.ps1` - Refresh a table or entire model via TMSL with configurable refresh type
- `modify-tom-objects.ps1` - Create table, rename measures, set folders/formats, hide columns, create relationship (with undo)
- `create-field-parameter.ps1` - Create a field parameter table from a list of measures with all required metadata
- `debug-dax.ps1` - Debug DAX with EVALUATEANDLOG trace capture and performance timings; auto-detects port, enumerates model measures, provides `Invoke-DebugQuery` helper
- `load-tmdl.ps1` - Load a local TMDL folder or BIM file into TOM offline (no running engine), enumerate the model, optionally add a measure and save back
- `connect-from-mac.sh` - macOS wrapper that runs PowerShell scripts in a Parallels VM via `prlctl exec`

**External references:**

- [TOM API Docs](https://learn.microsoft.com/en-us/dotnet/api/microsoft.analysisservices.tabular)
- [ADOMD.NET Docs](https://learn.microsoft.com/en-us/dotnet/api/microsoft.analysisservices.adomdclient)
- [Analysis Services Client Libraries](https://learn.microsoft.com/en-us/analysis-services/client-libraries)
- [DAX Guide](https://dax.guide) - use `dax.guide/<function>/` for individual function reference
