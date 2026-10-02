# Warehouse Operations

Guide for managing Fabric warehouses; creating, browsing, querying via DuckDB, and loading data.

## Creating a Warehouse

```bash
fab mkdir "ws.Workspace/MyWarehouse.Warehouse"
```

## Properties

```bash
fab get "ws.Workspace/MyWarehouse.Warehouse" -q "properties"
```

Returns `connectionInfo` (SQL endpoint), `connectionString`, `createdDate`, `collationType`.

## Browsing Contents

```bash
fab ls "ws.Workspace/MyWarehouse.Warehouse"           # Top-level (Tables, Files)
fab ls "ws.Workspace/MyWarehouse.Warehouse/Tables/dbo" # Tables in schema
fab table schema "ws.Workspace/MyWarehouse.Warehouse/Tables/dbo/orders"
```

## Querying with DuckDB

Warehouse tables are stored as Delta Lake in OneLake:

```bash
WS_ID=$(fab get "ws.Workspace" -q "id" | tr -d '"')
WH_ID=$(fab get "ws.Workspace/MyWarehouse.Warehouse" -q "id" | tr -d '"')

duckdb -c "
LOAD delta; LOAD azure;
CREATE SECRET (TYPE azure, PROVIDER credential_chain, CHAIN 'cli');
SELECT * FROM delta_scan('abfss://${WS_ID}@onelake.dfs.fabric.microsoft.com/${WH_ID}/Tables/dbo/orders') LIMIT 10;
"
```

## Loading Data

Warehouses do not support `fab cp` to Files or `fab table load`. Load via:

### T-SQL (SSMS or Fabric Portal)

```sql
CREATE TABLE dbo.orders AS
SELECT * FROM OPENROWSET(BULK 'https://storage.blob.core.windows.net/data/orders.parquet');
```

### Python Notebook via notebookutils.data

```python
with notebookutils.data.connect_to_artifact('WarehouseName') as conn:
    conn.query('CREATE TABLE dbo.test (id INT, name VARCHAR(100))')
    conn.query("INSERT INTO dbo.test VALUES (1, 'hello')")
    df = conn.query('SELECT * FROM dbo.test')
```

### PySpark Notebook via synapsesql

```python
import com.microsoft.spark.fabric
from com.microsoft.spark.fabric.Constants import Constants
df.write.synapsesql("WarehouseName.dbo.table", mode="overwrite")
```

Requires Runtime 1.3+. Known to produce opaque errors from `fab job run`; use `fab open` to check Spark logs.

### Upsert from a Dataflow: insert new, update changed, keep deleted

A Dataflow Gen2 destination has no upsert: Append duplicates and Replace mirrors the source, so rows
deleted at the source vanish. To keep them, stage and merge:

1. The Dataflow loads a **staging** table with update method **Replace**, so staging always mirrors
   the current source.
2. A stored procedure runs `MERGE target USING staging ON <key>` with `WHEN MATCHED ... UPDATE` and
   `WHEN NOT MATCHED BY TARGET ... INSERT`, and deliberately **no** `WHEN NOT MATCHED BY SOURCE ...
   DELETE`. That omission is what keeps rows removed from the source.
3. A pipeline runs the Dataflow activity, then on success the Stored procedure activity.

**If target rows still disappear**, something other than the `MERGE` is writing the target: a
no-DELETE `MERGE` cannot remove a row. The usual cause is the Dataflow's destination still pointing
at the **target** table with Replace, bypassing staging entirely. Check staging straight after a
refresh; empty staging means the Dataflow is not feeding it.

- An empty staging table makes the `MERGE` a silent no-op; guard against it in the procedure.
- Fabric does not enforce primary keys or `UNIQUE` (`NOT ENFORCED` only), so key uniqueness in
  staging is the procedure's job.
- A Warehouse Dataflow destination defaults to Append (a Lakehouse to Replace). A Lakehouse SQL
  endpoint is read-only, so the Lakehouse equivalent is a Spark `MERGE INTO` in a notebook.

## Key Differences from Lakehouse

| Feature | Lakehouse | Warehouse |
|---------|-----------|-----------|
| File upload (`fab cp`) | Supported | Not supported |
| `fab table load` | Supported | Not supported |
| Shortcuts (`fab ln`) | Supported | Not supported |
| T-SQL DDL/DML | Read-only (SQL endpoint) | Full support |
| DuckDB `delta_scan` | Yes | Yes |

## Deleting

```bash
fab rm "ws.Workspace/MyWarehouse.Warehouse" -f
```

Recovery depends on the tenant Item Recovery setting; see [reference.md > Recovering deleted items](reference.md#recovering-deleted-items).
