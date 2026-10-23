# Tables come from Power Query, not DAX

Detail for [the rule](../SKILL.md#tables-come-from-power-query-not-dax) in SKILL.md: build every
table in the source or in Power Query, and write a DAX calculated table only when no upstream
layer can produce it.

## Why

- **Refresh cost.** A calculated table is rebuilt every time a table it reads is refreshed, in
  the calculate phase after the data load. Every refresh pays for it, it cannot be refreshed
  incrementally, and nothing in it folds to the source.
- **Dependencies.** A table that reads the model (`ALL ( 'Calendar' )`, `MIN ( Sales[Date] )`,
  a UDF) joins the model's dependency graph, a common source of circular dependency errors once
  it gets a relationship or a calculated column.
- **Storage modes.** Direct Lake on SQL endpoints supports no calculated tables apart from the
  ones Desktop generates for calculation groups, what-if parameters and field parameters, and
  Direct Lake on OneLake supports them only in preview. A table built in the source works in
  every storage mode.
- **One home for table logic.** Shaping lives upstream, where other models and tools can read
  it, and the model keeps DAX for what only DAX can do: measures, UDFs and calculation groups.

The three calculated tables that turn up, and their Power Query form:

| DAX calculated table | Power Query partition |
| --- | --- |
| A static list: `DATATABLE ( "Metric", STRING, "Metric Sort", INTEGER, { { "Frequency", 1 }, … } )` | `#table(type table [Metric = text, #"Metric Sort" = Int64.Type], {{"Frequency", 1}, …})` |
| A what-if series: `GENERATESERIES ( 2, 10, 1 )`, scaled | `Table.FromColumns({List.Transform({2..10}, each _ * 0.005)}, type table [Value = number])` |
| A slicer table derived from another table: `DISTINCT ( SELECTCOLUMNS ( FILTER ( ALL ( 'Calendar' ), … ), … ) )` | Reference the other table's query by name, then `Table.SelectRows`, `Table.SelectColumns`, `Table.Distinct` |

A disconnected parameter or selector table works the same from Power Query: the slicer filters
it, and the measure reads the pick with `SELECTEDVALUE ( Param[Value], <default> )`. Integer
steps scaled by a constant, as in the series row, give the same doubles in M as in DAX, so a
slicer's saved literal (`0.02D`) still matches.

When you convert one in TMDL, change `partition … = calculated` to `= m` with a `let … in`
source, drop the brackets from each `sourceColumn` (`[Value]` becomes `Value`), add
`annotation PBI_ResultType = Table`, and add the table to the model's `PBI_QueryOrder`. Keep the
table and column names, which the report binds to, and the lineage tags.

Then close Power BI Desktop and delete the project's `.pbi/cache.abf` before you open it again.
With a cache, Desktop loads the cached model and applies the TMDL over it, and the engine will not
change a partition between calculated and M in place: *Changing the partition type from or to
PartitionType.Calculated is not allowed*. Applying the edit from Desktop's external-changes banner
fails the same way. Without the cache, Desktop opens the whole definition with no data; refresh
to load it.

**When a calculated table is the right call:**

- **Field parameters.** Their rows hold `NAMEOF ( … )` references to model fields, which only
  DAX can write.
- **A table that needs the model's own DAX logic** (a measure, a UDF or a calculation item
  evaluated over the model) and cannot be rebuilt from the source.

Calculation groups are not calculated tables, and this rule does not touch them.
