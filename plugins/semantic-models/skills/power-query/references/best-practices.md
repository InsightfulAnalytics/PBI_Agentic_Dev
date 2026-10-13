# Power Query Best Practices for Semantic Models

Practical guidance for writing performant, maintainable M expressions in semantic model partitions.

## Safe Pattern for Writing M

When writing or generating M expressions for import partitions, follow this order to maximize query folding:

```
let
    source = Sql.Database(SqlEndpoint, Database),
    data = source{[Schema = "dbo", Item = "MyTable"]}[Data],
    // 1. Filter rows (folds to WHERE)
    filtered = Table.SelectRows(data, each [IsActive] = true),
    // 2. Select columns (folds to SELECT)
    selected = Table.SelectColumns(filtered, {"Id", "Date", "Amount"}),
    // 3. Set types (folds to CAST)
    typed = Table.TransformColumnTypes(selected, {{"Amount", Currency.Type}}),
    // 4. Sort if needed (folds to ORDER BY)
    sorted = Table.Sort(typed, {{"Date", Order.Descending}}),
    // 5. Non-foldable transforms LAST
    added = Table.AddColumn(sorted, "Category", each if [Amount] > 1000 then "High" else "Low")
in
    added
```

If the transform logic is too complex for M, use `Value.NativeQuery` to pass native SQL directly:

```
let
    source = Sql.Database(SqlEndpoint, Database),
    data = Value.NativeQuery(
        source, "SELECT Id, Date, Amount FROM dbo.MyTable WHERE IsActive = 1", null, [EnableFolding = true]
    )
in
    data
```

`EnableFolding=true` allows subsequent M steps to fold on top of the native query result.

## Query Folding

Query folding translates M steps into native data source queries (SQL, OData, etc.). When folding works, the data source does the heavy lifting. When it breaks, the mashup engine pulls all data into memory and processes it locally.

### Why It Matters

- A folded query against a 10M row table sends `SELECT TOP 1000 ... WHERE ...` to SQL Server; fast
- A non-folded query pulls all 10M rows into the mashup engine, then filters locally; slow and memory-heavy
- For large tables, broken folding often causes refresh timeouts or out-of-memory errors

### Steps That Fold (SQL Sources)

| M Function | SQL Equivalent |
|------------|---------------|
| `Table.SelectColumns` | `SELECT col1, col2` |
| `Table.RemoveColumns` | `SELECT` (excluding columns) |
| `Table.SelectRows` | `WHERE` |
| `Table.Sort` | `ORDER BY` |
| `Table.FirstN` | `TOP N` |
| `Table.Group` | `GROUP BY` |
| `Table.TransformColumnTypes` | `CAST` |
| `Table.RenameColumns` | `AS` alias |
| `Table.ExpandTableColumn` | `JOIN` |
| `Table.NestedJoin` | `JOIN` |
| `Table.Distinct` | `DISTINCT` |
| `Table.Skip` | `OFFSET` |

### Operations That Break Folding

Once folding breaks, all subsequent steps also run locally. This list applies primarily to SQL Server via `Sql.Database`; other sources may differ.

**Table construction / materialization:**
- `Table.Buffer` -- forces full data load to memory
- `List.Buffer` -- forces full list load to memory
- `Table.StopFolding` -- explicitly stops folding
- `#table` constructor, `Table.FromList`, `Table.FromRecords`, `Table.FromRows`, `Table.FromValue`, `Table.FromColumns` -- creates table locally

**Row position / index operations:**
- `Table.AddIndexColumn` -- no SQL row index equivalent
- `Table.LastN` / `Table.RemoveLastN` -- no SQL BOTTOM N
- `Table.Range` (mid-range), `Table.Repeat`, `Table.AlternateRows` -- no SQL equivalent
- `Table.InsertRows`, `Table.RemoveRows` (by position) -- positional, not predicate-based
- `Table.ReverseRows` -- no SQL row-reverse
- `Table.FindText` -- full-text search not translatable

**Text functions (inside `Table.TransformColumns` or `Table.AddColumn`):**
- `Text.Proper` / "Capitalize Each Word"
- `Text.Combine` (multi-column merge), `Text.Insert`, `Text.Remove`, `Text.RemoveRange`
- `Text.Select`, `Text.Split`, `Text.SplitAny`
- `Text.BeforeDelimiter`, `Text.AfterDelimiter`, `Text.BetweenDelimiters`
- `Text.PadStart`, `Text.PadEnd`, `Text.Reverse`, `Text.Format`
- `Text.ToList`, `Text.Clean`
- `Text.From` with format/culture arguments

**Column splitting / combining:**
- `Table.SplitColumn`, `Table.CombineColumns`, all `Splitter.*` functions

**Pivot / transpose / structure:**
- `Table.Transpose`, `Table.DemoteHeaders`, `Table.PromoteHeaders`

**Fill / imputation:**
- `Table.FillDown`, `Table.FillUp` -- requires stateful row scanning

**Error handling:**
- `Table.RemoveRowsWithErrors`, `Table.SelectRowsWithErrors`
- `try...otherwise` in row context

**Schema / metadata:**
- `Table.Schema`, `Table.ColumnNames`, `Value.Type`, `Type.Is`

**Custom functions / iteration:**
- User-defined `(x) => ...` lambdas in row context
- `Table.TransformRows` -- arbitrary M function per row
- `List.Generate`, `List.Accumulate` -- iterative; no SQL equivalent
- `List.Transform` with complex logic

**Record / list / structured columns:**
- `Table.ExpandListColumn`, `Table.ExpandRecordColumn` (except after same-source NestedJoin)
- `Record.*` functions, `Table.ToRecords`, `Table.ToRows`, `Table.ToList`, `Table.Column`

**Date/time in row context:**
- `Date.ToText` / `DateTime.ToText` / `Duration.ToText` with format strings
- `Date.IsInCurrentMonth`, `Date.IsInCurrentWeek` and similar relative date filters
- `Date.DayOfWeekName`, `Date.MonthName` -- locale-dependent

**Miscellaneous:**
- `Table.Profile` -- statistical summary; local only
- `Table.Max`, `Table.Min` (returning row) -- returns record not table
- `Table.Contains`, `Table.ContainsAll`, `Table.ContainsAny`, `Table.IsDistinct` -- returns boolean

### Operations That Sometimes Fold

These fold under certain conditions:

- `Table.AddColumn` -- folds if expression uses only SQL-translatable functions (arithmetic, `Text.Upper`); breaks with complex M logic
- `Table.TransformColumns` -- folds for `Text.Upper`, `Text.Lower`, `Text.Trim`, `Number.Round`; breaks for `Text.Proper`, complex lambdas
- `Table.TransformColumnTypes` -- folds for compatible casts (int to decimal); breaks for locale-specific or M-only types
- `Table.ReplaceValue` -- folds with simple literal replacement; breaks with patterns
- `Table.Pivot` / `Table.Unpivot` -- folds on SQL Server (PIVOT/UNPIVOT support); breaks on other sources
- `Table.NestedJoin` -- folds when both sources are the same SQL connection; breaks across different sources
- `Table.Combine` / append -- folds as UNION ALL when all inputs are same SQL source
- `Table.SelectRows` with `Text.Contains` -- folds as `LIKE '%value%'` on SQL Server
- `Table.Group` -- folds with standard aggregations (`List.Sum`, `List.Count`, `List.Average`); breaks with custom functions
- `Value.NativeQuery` -- subsequent steps fold only if `EnableFolding=true` is set
- `Text.Start` / `Text.End` -- often fold as `LEFT()` / `RIGHT()`; `Text.Middle` often does not
- `Date.Year`, `Date.Month`, `Date.Day` -- fold as `YEAR()`, `MONTH()`, `DAY()`
- `Date.AddDays` / `Date.AddMonths` -- fold as `DATEADD()`

### Environmental Fold-Breakers

Not functions, but conditions that prevent folding:

- Merging/appending queries from different data sources
- Incompatible data privacy levels between sources (Data Privacy Firewall intervenes)
- Source is a flat file (CSV, Excel, JSON, XML) -- no query engine
- Source is `Web.Contents` / API -- no SQL engine
- Custom SQL without `EnableFolding=true`
- Any step after a fold-breaking step (chain is broken; cannot re-fold)

### Folding Strategy

**Rule:** Do all foldable work first, then do non-foldable work.

```
let
    source = Sql.Database(SqlEndpoint, Database),
    data = source{[Schema = "dbo", Item = "Orders"]}[Data],
    // FOLDABLE: These translate to SQL
    filtered_rows = Table.SelectRows(data, each [Year] >= 2023),
    selected_columns = Table.SelectColumns(filtered_rows, {"OrderId", "Date", "Amount", "CustomerId", "Status"}),
    set_types = Table.TransformColumnTypes(selected_columns, {{"Amount", Currency.Type}, {"Date", type date}}),
    // NON-FOLDABLE: These run in the mashup engine
    added_category = Table.AddColumn(
        set_types, "AmountBucket", each if [Amount] > 10000 then "Large" else "Small", type text
    )
in
    added_category
```

### Verifying Folding

In Power Query Online or Desktop, right-click a step and check "View Native Query". If greyed out, the step doesn't fold.

Programmatically: execute the expression via the `executeQuery` API. If a query on a large table completes well within the timeout, folding is likely working. If it times out or is slow, folding may be broken.

## Column Pruning

Remove columns as early as possible. Every column not removed travels through every subsequent step.

```
// Good: remove columns immediately after navigation
data = source{[Schema = "dbo", Item = "Orders"]}[Data],
selected = Table.SelectColumns(data, {"OrderId", "Date", "Amount"}),
...

// Bad: remove columns at the end after all transforms
...
final = Table.RemoveColumns(transformed, {"Col1", "Col2", "Col3", ...})
```

Early column pruning folds to SQL `SELECT`, reducing data transfer from the source.

## Row Filtering

Filter rows early for the same reason. A `Table.SelectRows` immediately after navigation folds to `WHERE`:

```
data = source{[Schema = "dbo", Item = "Orders"]}[Data],
filtered = Table.SelectRows(data, each [IsActive] = true and [Year] >= 2023),
```

This is especially important for incremental refresh, where `RangeStart`/`RangeEnd` filters must fold to be effective.

## Type Handling

### Apply Types Early

`Table.TransformColumnTypes` folds to `CAST` in SQL. Apply it right after column selection:

```
selected = Table.SelectColumns(data, {"OrderId", "Date", "Amount"}),
typed = Table.TransformColumnTypes(
    selected, {{"OrderId", Int64.Type}, {"Date", type date}, {"Amount", Currency.Type}}
),
```

### Avoid Implicit Type Detection

Never use `Table.TransformColumnTypes` with `Replacer.ReplaceValue` or locale-dependent conversions on large datasets. These don't fold and can introduce unexpected nulls.

### Common Type Mappings

| M Type | Use for |
|--------|---------|
| `Int64.Type` | Integer keys, counts |
| `type text` | Strings |
| `type date` | Date-only columns |
| `type datetime` | DateTime columns |
| `type datetimezone` | DateTime with timezone |
| `Currency.Type` | Financial amounts (fixed decimal) |
| `type logical` | Boolean flags |
| `Percentage.Type` | Rates, percentages |

## Keys: Power Query is case-sensitive, the model is not

Power Query (and `Table.Group`, `Table.Join`, and pandas upstream of it) compares text
**case-sensitively**; the tabular engine's default collation does not. A key that has N distinct values
in M can have N-1 once loaded, and if it is the one side of a relationship the refresh fails with
"contains a duplicate value", naming the value but not the cause. Source data supplies these: one
title published as both `A Woman With No Filter` and `A Woman with No Filter`.

Case-fold (`Text.Lower`) any key built in Power Query that is the one side of a relationship or a
primary key. Fold only those keys: leave display columns as published, because folding a column
nothing relates on can silently change published row counts.

## The privacy firewall and a secret read from a file

M that reads a secret from a local file and passes it as a header to `Web.Contents` trips the data
privacy firewall ("references other queries or steps, so it may not directly access a data source").
Set `fastCombine` under `dataAccessOptions` in `model.tmdl`: the project-level equivalent of "Ignore
the Privacy Levels", which travels with the PBIP instead of living in one machine's Desktop options.
Keep the secret file itself out of source control.

## Anti-Patterns

### Pulling Entire Tables Then Filtering

```
// Anti-pattern: filter after all transforms
data = source{[Schema = "dbo", Item = "BigTable"]}[Data],
added_column = Table.AddColumn(data, ...),  // breaks folding
filtered = Table.SelectRows(added_column, each [Year] >= 2023)
// Filter runs locally on ALL rows
```

### Using Table.Buffer Unnecessarily

`Table.Buffer` forces the entire table into memory. Only use when the same table is referenced multiple times and re-evaluation would be expensive.

### Referencing Other Queries

Cross-query references (accessing a column from a different query) break folding and can cause cascading performance issues.

### Excessive Step Count

Each step adds overhead. Combine related operations where natural; don't create a separate step for each individual column rename when `Table.RenameColumns` handles multiples:

```
// Good: one step for all renames
renamed = Table.RenameColumns(data, {{"OldName1", "NewName1"}, {"OldName2", "NewName2"}})

// Bad: separate step per rename
renamed1 = Table.RenameColumns(data, {{"OldName1", "NewName1"}}),
renamed2 = Table.RenameColumns(renamed1, {{"OldName2", "NewName2"}})
```

## Naming Conventions

Steps, variables and functions are snake_case and parameters PascalCase, with no spaces in either.
The full rule, including renaming spaced names in existing M, is **Naming** in `SKILL.md`.

## Error Handling

For production partitions, avoid `try...otherwise` patterns that silently swallow errors. A failed refresh is better than silently loading wrong data.

If error handling is necessary (e.g., optional columns), make it explicit and narrow:

```
safe_amount = Table.TransformColumns(
    data, {{"Amount", each try Number.FromText(_) otherwise null, type number}}
)
```
