# Refreshing a Model in Power BI Desktop

Three methods to trigger a data refresh on Power BI Desktop's local Analysis Services instance. All re-execute Power Query/M expressions and reload data into the VertiPaq engine.


## Refresh Types

| Type | TMSL Value | TOM Enum | Behaviour |
|------|-----------|----------|-----------|
| **Full** | `"full"` | `RefreshType.Full` | Drop existing data, re-query source, recompress, recalculate DAX |
| **Calculate** | `"calculate"` | `RefreshType.Calculate` | Recalculate DAX only (no source query, no data reload) |
| **Automatic** | `"automatic"` | `RefreshType.Automatic` | Engine decides per-partition: full if never processed, otherwise calculate |
| **DataOnly** | `"dataOnly"` | `RefreshType.DataOnly` | Re-query source and recompress, skip DAX recalculation |
| **ClearValues** | `"clearValues"` | `RefreshType.ClearValues` | Drop all data from the object without reloading |
| **Defragment** | `"defragment"` | `RefreshType.Defragment` | Recompress existing dictionaries (no source query, no DAX) |

For PBI Desktop, `full` and `calculate` are the most common. `automatic` is a safe default.


## Method 1: TMSL via Server.Execute()

The most flexible method. Supports refreshing databases, tables, and partitions.

```powershell
$dbName = $server.Databases[0].Name

# Full database refresh
$tmsl = @"
{
  "refresh": {
    "type": "full",
    "objects": [{ "database": "$dbName" }]
  }
}
"@
$server.Execute($tmsl)

# Single table refresh
$tmsl = @"
{
  "refresh": {
    "type": "full",
    "objects": [{ "database": "$dbName", "table": "Sales" }]
  }
}
"@
$server.Execute($tmsl)

# Multiple tables in one refresh
$tmsl = @"
{
  "refresh": {
    "type": "full",
    "objects": [
      { "database": "$dbName", "table": "Sales" },
      { "database": "$dbName", "table": "Date" }
    ]
  }
}
"@
$server.Execute($tmsl)

# Single partition
$tmsl = @"
{
  "refresh": {
    "type": "full",
    "objects": [{ "database": "$dbName", "table": "Sales", "partition": "Sales-2024" }]
  }
}
"@
$server.Execute($tmsl)
```

### Reading Execute() Results

`Server.Execute()` returns an `XmlaResultCollection`. Check for errors:

```powershell
$results = $server.Execute($tmsl)
foreach ($r in $results) {
    foreach ($msg in $r.Messages) {
        if ($msg -is [Microsoft.AnalysisServices.XmlaError]) {
            Write-Output "ERROR: $($msg.Description)"
        } elseif ($msg -is [Microsoft.AnalysisServices.XmlaWarning]) {
            Write-Output "WARNING: $($msg.Description)"
        }
    }
}
```


## Method 2: TOM RequestRefresh API

Queues a refresh on the TOM object, then `SaveChanges()` executes it. Simpler syntax for programmatic use.

```powershell
$model = $server.Databases[0].Model

# Refresh a single table
$model.Tables["Sales"].RequestRefresh([Microsoft.AnalysisServices.Tabular.RefreshType]::Full)
$model.SaveChanges()

# Refresh multiple tables
$model.Tables["Sales"].RequestRefresh([Microsoft.AnalysisServices.Tabular.RefreshType]::Full)
$model.Tables["Date"].RequestRefresh([Microsoft.AnalysisServices.Tabular.RefreshType]::Full)
$model.SaveChanges()  # executes both in one transaction

# Refresh a single partition
$model.Tables["Sales"].Partitions["Sales-2024"].RequestRefresh([Microsoft.AnalysisServices.Tabular.RefreshType]::Full)
$model.SaveChanges()

# Refresh entire model
$model.RequestRefresh([Microsoft.AnalysisServices.Tabular.RefreshType]::Full)
$model.SaveChanges()

# Calculate only (recalculate DAX, no source query)
$model.RequestRefresh([Microsoft.AnalysisServices.Tabular.RefreshType]::Calculate)
$model.SaveChanges()
```


## Method 3: XMLA via ADOMD.NET

Execute TMSL through an ADOMD.NET connection using `ExecuteNonQuery()`. Useful when only ADOMD.NET is loaded (no TOM).

```powershell
$conn = New-Object Microsoft.AnalysisServices.AdomdClient.AdomdConnection
$conn.ConnectionString = "Data Source=localhost:<PORT>"
$conn.Open()

$cmd = $conn.CreateCommand()
$cmd.CommandText = @"
{
  "refresh": {
    "type": "full",
    "objects": [{ "database": "<DB_NAME>", "table": "Sales" }]
  }
}
"@
$cmd.ExecuteNonQuery()
$conn.Close()
```

Note: use `ExecuteNonQuery()` for TMSL commands, not `ExecuteReader()` -- TMSL returns XML results, not a rowset.


## Refresh Sequence

When refreshing multiple tables, order matters if there are dependencies:

1. Refresh dimension/lookup tables first (e.g., Date, Products, Customers)
2. Refresh fact tables second (e.g., Sales, Orders)
3. Run a `calculate` refresh at the end to recalculate all DAX

```powershell
$dbName = $server.Databases[0].Name

# Dimensions first
$server.Execute('{ "refresh": { "type": "full", "objects": [{ "database": "' + $dbName + '", "table": "Date" }] } }')
$server.Execute('{ "refresh": { "type": "full", "objects": [{ "database": "' + $dbName + '", "table": "Products" }] } }')

# Facts second
$server.Execute('{ "refresh": { "type": "full", "objects": [{ "database": "' + $dbName + '", "table": "Sales" }] } }')

# Recalculate DAX
$server.Execute('{ "refresh": { "type": "calculate", "objects": [{ "database": "' + $dbName + '" }] } }')
```

Or use a single TMSL command with `"type": "full"` on the entire database, which handles dependencies automatically.


## Hand-Authored PBIP: No Data on First Open

Power BI Desktop shows "Some of the tables have incomplete or no data" and does **not** auto-import on
the first open of a PBIP whose model was written by hand. The data image has never been built and
nothing in the open sequence builds it, so the model looks broken when it is only empty.

Do not go looking for a Desktop command to fix it. Where the secure-local-APIs preview is off,
`pbir desktop refresh` is unavailable and synthesised ribbon clicks do not land. Refresh through TOM
against the running instance instead:

```powershell
$server.Connect("Data Source=localhost:$port")
$model = $server.Databases[0].Model
$model.RequestRefresh([Microsoft.AnalysisServices.Tabular.RefreshType]::Full)
$model.SaveChanges()
```

The same applies to a table created through TOM: after `SaveChanges()` it carries metadata only, and
a full refresh is what executes its M expression and loads data into VertiPaq.


## Important Notes

- **PBI Desktop refreshes are synchronous** -- `Execute()` blocks until the refresh completes
- **Timeouts** -- long refreshes may exceed the default Bash timeout; set 300000ms+ for large models
- **Embedded data** -- `.pbix` files with embedded data (no live connection) will re-evaluate the M expressions that generated the embedded data
- **Errors during refresh** -- check the `XmlaResultCollection` returned by `Execute()` for error messages
- **Ctrl+Z in PBI Desktop** -- refresh operations cannot be undone; the data is replaced in-place
