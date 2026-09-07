# Fields and Bindings

Complete guide to managing field bindings in visuals, swapping fields across reports, and rebinding reports to different semantic models.

## Inspecting Field Usage

```bash
pbir fields list "Report.Report"                 # All fields used across the report
pbir fields find "Sales.Revenue" "Report.Report"  # Where a specific field is used
pbir tree "Report.Report" -v                     # Visual tree with field bindings
```

## Discovering Model Fields

Before binding fields, query the connected semantic model to discover correct table names, column names, and measure names. Never guess or invent field names.

### Model Definition (Structure)

```bash
# Full model definition -- all tables, columns, measures, relationships
pbir model "Report.Report" -d

# Filter to a specific table (saves tokens for large models)
pbir model "Report.Report" -d -t Sales
pbir model "Report.Report" -d -t Date

# Full TMDL output (includes partition queries, annotations, etc.)
pbir model "Report.Report" -d -v

# Save definition to file for reference
pbir model "Report.Report" -d -o model.json

# Pipe to grep for quick lookup
pbir model "Report.Report" -d | grep -i "revenue"
```

### When the model schema will not load

`pbir model -d` can fail with `failed to load model schema` or `Could not retrieve model
definition`. For a report bound to a **published** model (`byConnection`), the schema is fetched by
shelling out to the Fabric CLI, `fab get <model> -q definition -f`. A `fab` build that does not
accept `-f` answers `unknown shorthand flag: -f`, and that is what `pbir` is reporting. Putting a
`fab` shim earlier on PATH does not intercept the call, because `pbir` resolves the real
executable.

**Scope correction, and the reason not to abandon the task: this only bites `byConnection`
reports.** For a local `byPath` PBIP, `pbir` reads the model's TMDL straight off disk. `pbir model
-d` prints the full schema and `pbir validate --fields` resolves every projection, measures and
columns alike, with no `fab` call at all. Column-bound visuals are blocked only when the report
points at a workspace model.

When it does bite, the damage is uneven. `pbir add visual` still works for **measure**-bound
visuals such as cards and chart `Y`, because extension measures are read from
`reportExtensions.json` without the model schema. It fails for any **column**-bound projection:
slicers, table columns, chart `Category` and axis fields. `--skip fields` and `--rawdog` do not
help, and reaching for them is the wrong reflex here: the schema *load* is what authoring a column
reference requires, and that is a different step from validation. `pbir publish` is unaffected,
because the import path never loads the schema.

Work through it in this order:

1. **Check the Fabric CLI first.** `fab --version`, then upgrade (`uv tool upgrade
   ms-fabric-cli`) and retry. A `fab` that accepts `-f` on `get` fixes the root cause and every
   column binding starts working again.
2. **Verify the field names you need with the DAX path**, which works even when `-d` does not:
   `pbir model "Report.Report" -q "EVALUATE TOPN(5, 'Sales')"`, or `EVALUATE VALUES('Geography'[Region])`
   for one column. Do this before authoring anything, so every name that reaches a visual is
   known-good rather than guessed.
3. **Bind against the local model instead.** If the semantic model is available on disk, point the
   report at it and the `fab` route drops out entirely: `pbir report rebind "Report.Report" --local
   "../Model.SemanticModel"`, or `pbir report merge-to-thick` for a full thick PBIP. Both are in
   `converting-reports.md`. Rebind back to the workspace model before publishing.
4. **Only if none of that applies**, and the report must stay `byConnection` on a `fab` that cannot
   move, say so rather than patching JSON from here: this skill's rule against editing report JSON
   directly still stands. Hand-authoring a projection is the `pbip:pbir-format` skill's job, and
   `references/semantic-model/field-references.md` there carries the column contract
   (`Column` expression, `queryRef`, `nativeQueryRef`); do not reach for this skill's own
   `examples/visuals/default/` templates and write the file from here instead. If that skill does
   write one, its `$schema` line should be read out of a visual `pbir` created in the same report
   rather than hard-coded to a version, and the file then comes back here for `pbir validate` and
   the render check.

[`fab get --help` lists no `-f` flag on fab 0.1.10. Verified 2026-09-07.]
Retest: `fab get --help`

### DAX Queries (Values and Verification)

Query the model to verify field values, check cardinality, and understand data before binding.

```bash
# Check distinct values in a column (useful before creating slicers)
pbir model "Report.Report" -q "EVALUATE VALUES('Geography'[Region])"

# Check cardinality -- how many distinct values
pbir model "Report.Report" -q "EVALUATE ROW(\"Count\", DISTINCTCOUNT('Products'[Category]))"

# Preview table data
pbir model "Report.Report" -q "EVALUATE TOPN(5, 'Sales')"

# Test a measure
pbir model "Report.Report" -q "EVALUATE ROW(\"Revenue\", [Total Revenue])"

# Check date range
pbir model "Report.Report" -q "EVALUATE ROW(\"Min\", MIN('Date'[Date]), \"Max\", MAX('Date'[Date]))"

# JSON output for programmatic use
pbir model "Report.Report" -q "EVALUATE VALUES('Sales'[Region])" -F json

# Test connectivity
pbir model "Report.Report" -q "EVALUATE ROW(\"Test\", 1)"
```

### Model Info (Connection)

```bash
# Connection details: workspace, model name, model ID, thick/thin
pbir model "Report.Report"

# List all reports and their model connections
pbir model

# Cache all model definitions (useful before working on multiple reports)
pbir model --cache
```

### Workflow: Choose Fields for a Visual

1. **Get model structure**: `pbir model "Report.Report" -d` to see all tables and fields
2. **Filter to relevant table**: `pbir model "Report.Report" -d -t Sales` to focus
3. **Verify values**: `pbir model "Report.Report" -q "EVALUATE VALUES('Table'[Column])"` to check cardinality and values
4. **Check existing usage**: `pbir fields list "Report.Report"` to see what fields are already in use
5. **Use `AskUserQuestion`** to discuss field choices when the model has multiple plausible fields for the user's intent

## Field Types: Column vs Measure

Every field binding in Power BI has a type -- Column, Measure, or Hierarchy. The type determines the JSON key used in the visual's `queryState` projections:

- **Column**: `{"Column": {"Expression": {"SourceRef": {"Entity": "Table"}}, "Property": "Field"}}`
- **Measure**: `{"Measure": {"Expression": {"SourceRef": {"Entity": "Table"}}, "Property": "Field"}}`

**A field bound with the wrong type will fail at runtime in Power BI Desktop** ("something is wrong with one or more fields") even though it passes JSON schema validation. This is a semantic error, not a structural one.

### How to Specify Field Type

**CLI (`pbir visuals bind`)**: Use the `-t` flag:
```bash
pbir visuals bind "Visual.Visual" -a "Values:Sales.Revenue" -t Measure
pbir visuals bind "Visual.Visual" -a "Category:Date.Month" -t Column
```

**CLI (`pbir add visual`)**: The `-d` flag auto-detects type from the model when possible. If the model is unavailable, explicitly specify with `-t`:
```bash
pbir add visual card "Page.Page" -d "Values:Sales.Revenue"
```

**Python object model (`Field()`)**: Set `kind` parameter:
```python
Field("Sales", "Revenue", kind=1)     # Measure (kind=1)
Field("Date", "Month", kind=0)        # Column (kind=0)
Field("Date", "Month")                # Column (default when kind not set)
```

### Common Pitfall

`Field("Table", "MeasureName")` without `kind=1` creates a **Column** binding even if the field is a measure in the model. This is the most common source of binding errors. Always check the model to determine whether a field is a column or measure, and set `kind` accordingly.

### Fixing Wrong Field Types

To fix a field bound as the wrong type, clear the role and re-add with the correct type:
```bash
# Fix: change Column to Measure
pbir visuals bind "Visual.Visual" -c "Values"
pbir visuals bind "Visual.Visual" -a "Values:Sales.Revenue" -t Measure

# Verify
pbir visuals bind "Visual.Visual" --show
```

Do NOT attempt to fix field types by editing the visual JSON directly. Use `pbir visuals bind` -- it handles the full binding structure (queryState projections, queryRefs, nativeQueryRefs).

## Binding Fields to Visuals

### During Creation

```bash
# Bind fields at creation time with -d flag (role:Table.Field)
pbir add visual card "Page.Page" --title "Revenue" -d "Values:Sales.Revenue"
pbir add visual lineChart "Page.Page" --title "Trend" \
  -d "Category:Date.Month" -d "Y:Sales.Revenue"
```

### After Creation

```bash
# Show current bindings
pbir visuals bind "Report.Report/Page.Page/Visual.Visual" --show

# List available data roles for the visual type
pbir visuals bind "Report.Report/Page.Page/Visual.Visual" --list-roles

# Add a field to a role
pbir visuals bind "Visual.Visual" -a "Category:Date.Month"
pbir visuals bind "Visual.Visual" -a "Y:Sales.Revenue" -t Measure
pbir visuals bind "Visual.Visual" -a "Legend:Products.Category" -t Column

# Remove a field from a role
pbir visuals bind "Visual.Visual" -r "Y:Sales.Revenue"

# Clear all bindings from a role
pbir visuals bind "Visual.Visual" -c "Legend"
```

### Flags

| Flag | Purpose |
|------|---------|
| `-a` / `--add` | Add field binding (`Role:Table.Field`) |
| `-r` / `--remove` | Remove field binding (`Role:Table.Field`) |
| `-c` / `--clear` | Clear all fields from a role |
| `-t` / `--type` | Field type: `Column` or `Measure` |
| `-l` / `--list-roles` | Show available data roles for the visual type |
| `-s` / `--show` | Show current bindings |

### Data Roles by Visual Type

Key types and their primary data roles:

- **card**: Values
- **cardVisual**: Data
- **lineChart / barChart / columnChart**: Category, Y (Legend, SmallMultiples)
- **clusteredBarChart / clusteredColumnChart**: Category, Y (Legend, SmallMultiples)
- **lineClusteredColumnComboChart**: Category, ColumnY, LineY (Legend)
- **tableEx**: Values
- **pivotTable** (matrix): Values (Rows, Columns)
- **slicer / advancedSlicerVisual**: Values
- **donutChart / pieChart**: Category, Values (Legend)
- **scatterChart**: X, Y (Category, Size, Legend)
- **treemap**: Category, Values (Details)
- **gauge**: Value (TargetValue, MinValue, MaxValue)

Use `pbir visuals bind "Visual.Visual" --list-roles` to discover roles for any visual type.

## Swapping Fields in Visuals

### Replace a Field Across the Report

Replace every occurrence of one field with another. Useful when renaming model columns or switching between similar measures.

```bash
# Dry run first -- see what would change
pbir fields replace "Report.Report" --from "Sales.Revenue" --to "Sales.NetRevenue" --dry-run

# Apply the replacement
pbir fields replace "Report.Report" --from "Sales.Revenue" --to "Sales.NetRevenue"

# Skip validation (if model not available locally)
pbir fields replace "Report.Report" --from "Sales.Revenue" --to "Sales.NetRevenue" --skip-validation
```

### Add a Field to Specific Visuals

```bash
# Add field to a specific visual's bucket
pbir fields add "Report.Report/Page.Page/Visual.Visual" \
  -f "Sales.Revenue" -b "Y" -t Measure

# Dry run
pbir fields add "Report.Report/Page.Page/Visual.Visual" \
  -f "Sales.Revenue" -b "Y" -t Measure --dry-run
```

### Rename Fields

```bash
# List current field mappings
pbir fields rename "Report.Report" --list

# Rename a field reference across the report
pbir fields rename "Report.Report" "Sales.OldName" "Sales.NewName"

# Dry run
pbir fields rename "Report.Report" "Sales.OldName" "Sales.NewName" --dry-run
```

### Clear Fields

```bash
# Remove all field bindings from visuals in the report
pbir rm "Report.Report" --fields -f

# Remove one field from one visual's role
pbir visuals bind "Visual.Visual" -c "Values"
```

## Rebinding Reports to Different Models

Rebinding changes which semantic model a report connects to. This is necessary when migrating reports between workspaces, switching from dev to prod models, or consolidating models.

### Check Current Binding

```bash
pbir model "Report.Report"                       # Current model connection
pbir model "Report.Report" -d                    # Model tables and columns
```

### Rebind to a Workspace Model

```bash
# Rebind to a model in a Fabric workspace
pbir report rebind "Report.Report" "TargetWorkspace/Sales.SemanticModel"

# Rebind to a model by ID
pbir report rebind "Report.Report" --model-id "abc-123-def"
```

### Rebind to a Local Model

```bash
# Rebind to a local PBIP semantic model
pbir report rebind "Report.Report" --local "path/to/Model.SemanticModel"
```

### Field Mapping After Rebind

After rebinding to a model with different field names, use `pbir fields replace` to update references:

```bash
# Check which fields are broken (not in new model)
pbir validate "Report.Report"

# Replace old field references with new ones
pbir fields replace "Report.Report" --from "OldTable.OldColumn" --to "NewTable.NewColumn"
pbir fields replace "Report.Report" --from "OldTable.OldMeasure" --to "NewTable.NewMeasure"
```

## Recommended Workflow: Rebinding

1. **Inspect**: `pbir model "Report.Report" -d` to understand current model
2. **Rebind**: `pbir report rebind "Report.Report" "Workspace/Model.SemanticModel"`
3. **Validate**: `pbir validate "Report.Report"` to find broken fields
4. **Fix**: `pbir fields replace` for each broken field mapping
5. **Verify**: `pbir fields list "Report.Report"` to confirm all fields resolve
6. **Validate again**: `pbir validate "Report.Report"` to confirm clean state

## Recommended Workflow: Swapping Fields

1. **Discover**: `pbir fields find "Table.OldField" "Report.Report"` to see all usages
2. **Dry run**: `pbir fields replace "Report.Report" --from "Table.OldField" --to "Table.NewField" --dry-run`
3. **Apply**: Remove `--dry-run` to execute
4. **Validate**: `pbir validate "Report.Report"`

## Show-All and Field Hidden

```bash
# Show empty subcategory rows for a role
pbir visuals show-all "Visual" --role Category

# Disable show-all
pbir visuals show-all "Visual" --role Category --off

# Hide a field in the field well (field stays bound, just hidden in UI)
pbir visuals field-hidden "Visual" --role Y --field "Invoices.Net Invoice Value"

# Show a hidden field
pbir visuals field-hidden "Visual" --role Y --field "Invoices.Net Invoice Value" --show
```
