---
name: power-query
version: 26.40.3
description: Author, validate, and test Power Query M expressions in semantic model partitions. Automatically invoke when the user mentions "Power Query", "M code", "M expression", "partition expression", "query folding", or asks to "write Power Query", "fix Power Query", "test a partition", "preview partition data", "debug Power Query step", "optimize Power Query".
---

# Power Query for Semantic Models

Author, validate, and test Power Query M expressions in semantic model import partitions. Covers writing correct M code, preserving query folding, validating expressions, and testing them by executing against real data sources.

## Partition Expressions

Each import table in a semantic model has a partition with an M expression defining what data gets loaded during refresh. The expression typically connects to a data source, navigates to a table/view, and applies transformations.

### Structure of a Partition Expression

```
let
    source = Sql.Database(SqlEndpoint, Database),
    data = source{[Schema="dbo", Item="Orders"]}[Data],
    removed_columns = Table.RemoveColumns(data, {"InternalId"}),
    changed_type = Table.TransformColumnTypes(removed_columns, {{"Amount", Currency.Type}})
in
    changed_type
```

Key elements:
- **Parameters**: `SqlEndpoint`, `Database` are shared M parameters defined at the model level
- **Navigation**: `source{[Schema="dbo", Item="Orders"]}[Data]` navigates to a specific table
- **Steps**: Each step is a named variable in the `let...in` chain, named in snake_case (see **Naming** below)

### Extracting Expressions

```bash
# Get partition expression from TMDL via fab
fab get "<Workspace>.Workspace/<Model>.SemanticModel" -f \
  -q "definition.parts[?path=='definition/tables/<Table>.tmdl'].payload"

# Get shared M parameters
fab get "<Workspace>.Workspace/<Model>.SemanticModel" -f \
  -q "definition.parts[?path=='definition/expressions.tmdl'].payload"
```

## Writing M Expressions

### Naming: snake_case identifiers

Name every step, `let` variable, custom function and function argument in lowercase snake_case:
letters, digits and underscores, starting with a letter (`added_column`, `filtered_active`,
`fn_clean_text`). A snake_case name is a plain identifier, so every reference to it is bare. A name
with a space has to be written `#"Added Column"` at its definition and at every reference.

- Describe the transformation (`removed_duplicates`), not the position (`custom1`, `step1`).
- Pick a name that is not an M keyword. `type`, `error`, `each`, `in`, `let`, `if`, `try`, `meta`,
  `null`, `section` and `shared` still need `#"..."`, so write `typed` or `errors_removed`.
- Parameters are PascalCase with no spaces (`SqlEndpoint`, `DatabaseName`). `RangeStart` and
  `RangeEnd` keep that exact spelling: incremental refresh looks them up by name.

**Existing M.** Whenever you read or edit an expression that names a step, variable or function
with a space (`#"Added Custom"`, `#"fn Clean Text"`), rename it to snake_case (`added_custom`,
`fn_clean_text`) in the same edit:

1. Replace the quoted name at its definition, at every later step that references it, and in the
   `in` clause. M is case-sensitive, and one missed reference fails the whole query with
   `The name 'x' wasn't recognized`.
2. For a shared function or query in `expressions.tmdl`, also rename its declaration
   (`expression 'fn Clean Text'` becomes `expression fn_clean_text`) and every caller: search the
   whole `definition/` folder for the old `#"..."` form.
3. Validate the renamed expression (see **Validating M Expressions**) before calling it done.

These names are owned outside the expression and keep their spaces:

- **Column names.** Text literals (`"Order Date"`) and field access (`[Order Date]`,
  `[#"Week & Year"]`) name model columns; renaming them changes the model.
- **Table names.** A query that references another loaded table writes `#"Dim Customer"`. That is
  the model table's name: rename it only through a model rename (`pbip:pbip`), when asked.
- **Parameters of a published model.** Ask before renaming one that has a space: the Service stores
  its value, and deployment rules bind to it, by name.

### Query Folding

Query folding is the most important performance concept. The M engine translates compatible steps into native data source queries (e.g., SQL). When folding breaks, subsequent steps run in the mashup engine, pulling all data into memory first.

**Steps that typically fold** (for SQL sources):
- `Table.SelectColumns` / `Table.RemoveColumns` -> `SELECT`
- `Table.SelectRows` -> `WHERE`
- `Table.Sort` -> `ORDER BY`
- `Table.FirstN` -> `TOP`
- `Table.Group` -> `GROUP BY`
- `Table.RenameColumns` -> `AS` aliases

**Steps that may or may not fold** (source-dependent):
- `Table.TransformColumnTypes` -- frequently breaks folding for text-to-numeric/date conversions on SQL Server sources. Use `Table.TransformColumns` with explicit conversion functions (e.g., `Number.From`) as a more reliable foldable alternative.

**Steps that break folding:**
- `Table.AddColumn` with custom M functions (not translatable to SQL)
- `Table.Buffer` (forces materialization; prefer `Table.StopFolding` to stop folding without the memory overhead)
- `Table.LastN` (no SQL equivalent without subquery)
- `Table.Combine` across different data sources (cross-database folding within the same SQL Server is possible via `EnableCrossDatabaseFolding`)
- Complex `each` expressions with M-specific logic
- Any step after a fold-breaking step

**Best practice:** Apply folding-compatible steps (filter, select, type) early; add custom columns and M-only transforms after all foldable work is done.

### Column Pruning and Row Filtering

Remove unused columns and filter rows as early as possible:

```
let
    source = Sql.Database(SqlEndpoint, Database),
    data = source{[Schema="dbo", Item="Orders"]}[Data],
    // Filter and select BEFORE any custom transforms
    filtered = Table.SelectRows(data, each [Status] <> "Cancelled"),
    selected = Table.SelectColumns(filtered, {"OrderId", "Date", "Amount", "CustomerId"})
in
    selected
```

These steps fold to SQL: `SELECT OrderId, Date, Amount, CustomerId FROM dbo.Orders WHERE Status <> 'Cancelled'`

### Type Handling

- Apply `Table.TransformColumnTypes` early (folds to `CAST` in SQL)
- Use explicit M types: `Int64.Type`, `type text`, `type date`, `Currency.Type`, `type logical`
- Avoid implicit type inference on large datasets

## Validating M Expressions

Two approaches to validate that an M expression is syntactically correct and produces expected results:

### 1. Execute via the Power Query API (Recommended)

Test the expression by running it against real data. This validates syntax, data source connectivity, and transformation correctness in one step.

The full workflow, run by the bundled `examples/execute_m.py`:

1. Create or reuse a runner dataflow in the workspace
2. Bind the data source connection to the runner
3. Wrap the expression in a section document, inline parameters
4. Execute via `POST /v1/workspaces/{wsId}/dataflows/{dfId}/executeQuery`
5. Parse the Arrow response to verify data

```bash
MASHUP='section Section1;
shared SqlEndpoint = "myserver.database.windows.net";
shared Database = "MyDB";
shared Result = let
    source = Sql.Database(SqlEndpoint, Database),
    data = Table.FirstN(source{[Schema="dbo",Item="Orders"]}[Data], 10)
in data;'

curl -s -o result.bin -X POST ".../executeQuery" \
  -H "Authorization: Bearer ${TOKEN}" -H "Content-Type: application/json" \
  -d "$(jq -n --arg m "$MASHUP" '{queryName:"Result",customMashupDocument:$m}')"
```

See **`references/validation.md`** for step-by-step instructions and error handling.

### 2. Save the Partition via XMLA / TOM

Write the expression back to the model; Analysis Services validates the M syntax on save. This doesn't execute the query but catches structural errors:

- Missing or mismatched `let`/`in`
- Undefined step references
- Invalid function calls
- Type mismatches in `TransformColumnTypes`

```bash
# Edit the TMDL partition source directly and deploy via fab import,
# or use the XMLA endpoint with Tabular Editor or SSMS to modify
# the partition expression on the deployed model.
```

AS returns an error if the expression is malformed. This is faster than a full execute but doesn't catch runtime errors (wrong column names, data source issues).

### Choosing a Validation Approach

| Need | Use |
|------|-----|
| Full data validation (correct columns, types, values) | Execute via API |
| Quick syntax check | Save to model via XMLA/TOM |
| Step-by-step debugging | Execute with truncated `in` clause |
| Performance testing (check folding) | Execute with full data, observe timing |

## Previewing Partition Steps

See the data at any point in the transformation chain by truncating the `let...in`:

```
-- See raw source data (all columns)
in data;

-- See after column removal
in removed_columns;

-- See final result
in changed_type;
```

Add `Table.FirstN(stepName, 100)` before the `in` to limit rows for large tables. See **`references/validation.md`** for the complete procedure.

## Common Patterns

### Incremental Refresh Partitions

Incremental refresh partitions use `RangeStart` and `RangeEnd` parameters:

```
let
    source = Sql.Database(SqlEndpoint, Database),
    data = source{[Schema="dbo", Item="Orders"]}[Data],
    filtered = Table.SelectRows(data, each
        [OrderDate] >= RangeStart and [OrderDate] < RangeEnd)
in
    filtered
```

When testing, inline concrete date values for `RangeStart` and `RangeEnd`.

### Lakehouse Sources

```
let
    source = Lakehouse.Contents(null),
    lakehouse = source{[Id="lakehouse-guid"]}[Data],
    data = lakehouse{[Id="table-name", ItemKind="Table"]}[Data]
in
    data
```

### SQL with Native Query

For complex SQL that can't be expressed in M:

```
let
    source = Sql.Database("server", "db"),
    data = Value.NativeQuery(source, "SELECT * FROM dbo.MyView WHERE Year = 2024", null, [EnableFolding=true])
in
    data
```

`Value.NativeQuery` with `EnableFolding=true` allows subsequent M steps to fold on top of the native query.

## References

- **`references/validation.md`** -- Detailed validation workflow with executeQuery API, step preview, error handling
- **`references/best-practices.md`** -- Query folding guidance, fold-breaker list, anti-patterns, performance tips
- **`examples/execute_m.py`** -- Python script to execute M expressions via the Fabric API (CLI tool)
- **`examples/preview_partition.py`** -- Python script to preview partition data at any step (uses `fab get` + `execute_m.py`)
- [Power Query M Reference](https://learn.microsoft.com/en-us/powerquery-m/)
- [Query Folding Guidance](https://learn.microsoft.com/en-us/power-bi/guidance/power-query-folding)
