# Keep the VARs flat: the nested shapes and their flat forms

Detail for [Keep the VARs flat](../SKILL.md#keep-the-vars-flat): a measure is one flat list of
`VAR`s, then `RETURN __Result`, with no `VAR … RETURN` block inside a function argument.

Three nested shapes turn up. Each has a flat form that returns the same number.

**1. A block passed to a wrapper that sets the filter context.** A UDF such as
`ProductSet.Focus ( valueExpr : EXPR ) => CALCULATE ( valueExpr, <set filter> )` invites passing it
a whole calculation:

```DAX
-- nested: none of the steps can be returned
Margin per Litre =
    VAR __Result =
        ProductSet.Focus (
            VAR __Rows   = FILTER ( Sales, NOT ISBLANK ( Sales[Margin per Unit] ) )
            VAR __Margin = SUMX ( __Rows, Sales[Units] * Sales[Margin per Unit] )
            VAR __Litres = SUMX ( __Rows, Sales[Litres] )
            RETURN
                DIVIDE ( __Margin, __Litres )
        )
    RETURN
        __Result
```

Give the wrapper a table twin that applies the same filters with `CALCULATETABLE`. Build the table
VAR through the twin, and the steps after it stand at the top level:

```DAX
-- functions.tmdl: the twin, next to the wrapper
ProductSet.FocusTable = ( tableExpr : EXPR ) =>
    CALCULATETABLE ( tableExpr, <same set filter> )

-- flat
Margin per Litre =
    VAR __Rows =
        ProductSet.FocusTable (
            FILTER ( Sales, NOT ISBLANK ( Sales[Margin per Unit] ) )
        )
    VAR __Margin = SUMX ( __Rows, Sales[Units] * Sales[Margin per Unit] )
    VAR __Litres = SUMX ( __Rows, Sales[Litres] )
    VAR __Result = DIVIDE ( __Margin, __Litres )
    RETURN
        __Result
```

The number is the same because nothing after `__Rows` reads the filter context. An X-aggregator
over a table VAR, with a row expression of columns only, depends on the rows alone. A step that does
read the context (a measure reference, a plain `SUM`, `CALCULATE`, `ALLSELECTED`) would see the outer
context once it leaves the wrapper. Give that step the scalar wrapper of its own, still at the top
level: `VAR __Total = ProductSet.Focus ( [Total Sales] )`. A bare
`CALCULATE ( <VAR block>, <filters> )` flattens the same way: build the table with
`CALCULATETABLE ( …, <filters> )` and aggregate it outside.

Call the twin only from measures. A function that calls a newly added function can fail to load
(see the UDF load traps in [number-formatting.md](number-formatting.md#the-udf-write-the-formatting-convention-once)).

**2. A block inside an iterator's row expression.**

```DAX
-- nested: __Text and __Cut cannot be inspected
VAR __Chips =
    ADDCOLUMNS (
        __Picks,
        "@Label",
            VAR __Text = CONVERT ( Product[Name], STRING )
            VAR __Cut  = IF ( LEN ( __Text ) > 20, LEFT ( __Text, 19 ) & "…", __Text )
            RETURN
                SUBSTITUTE ( __Cut, "&", "&amp;" )
    )
```

Make each step a computed column in a table VAR of its own. Returning any of them shows that step
for every row:

```DAX
VAR __Texts = ADDCOLUMNS ( __Picks, "@Text", CONVERT ( Product[Name], STRING ) )
VAR __Cuts  = ADDCOLUMNS ( __Texts, "@Cut", IF ( LEN ( [@Text] ) > 20, LEFT ( [@Text], 19 ) & "…", [@Text] ) )
VAR __Chips = ADDCOLUMNS ( __Cuts, "@Label", SUBSTITUTE ( [@Cut], "&", "&amp;" ) )
```

**3. A VAR that captures a row value only to put a filter back.**

```DAX
-- nested: removes every Customer filter, then puts the row's region back
"@Region Sales",
    VAR __Region = Customer[Region]
    RETURN
        CALCULATE ( [Sales], REMOVEFILTERS ( Customer ), Customer[Region] = __Region )
```

Context transition already filters the row's region. Remove only the filters you mean to drop, and
the region stays:

```DAX
"@Region Sales",
    CALCULATE ( [Sales], ALLEXCEPT ( Customer, Customer[Region] ) )
```

**The nested VAR that stays.** When the inner expression iterates a table that has the same column
as the outer row, the inner row context hides the outer value. Capturing it first is the job
`EARLIER` used to do, and a VAR does it more clearly. Keep the block to that one capture:

```DAX
"@Sales To Date",
    VAR __Date = [Date]
    RETURN
        SUMX ( FILTER ( __Days, [Date] <= __Date ), [@Sales] )
```

**Prove a flattened measure.** When you flatten an existing measure, compare the old body with the
new measure in DAX query view, over the cells the report shows. No rows back means no cell changed:

```DAX
DEFINE
    MEASURE Sales[Old Margin per Litre] = <the old, nested body>
EVALUATE
    FILTER (
        ADDCOLUMNS (
            CROSSJOIN ( VALUES ( Store[Region] ), VALUES ( Product[Category] ) ),
            "@New", [Margin per Litre],
            "@Old", [Old Margin per Litre]
        ),
        ISBLANK ( [@New] ) <> ISBLANK ( [@Old] )
            || ABS ( [@New] - [@Old] ) > 1E-9 * MAX ( 1, ABS ( [@Old] ) )
    )
```
