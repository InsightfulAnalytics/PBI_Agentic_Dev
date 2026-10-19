# Core Functions

The building blocks the pattern is assembled from. Examples use a generic `Sales` fact with
`Product` / `Date` dimensions — swap in the real table and column names. Attributes are read
and filtered on the dimension, not the fact
([Filter the dimension, not the fact](../SKILL.md#filter-the-dimension-not-the-fact)).

## Looking up values — FILTER + MINX/MAXX (instead of LOOKUPVALUE)

To read one value, filter to the row(s) and reduce with `MINX`/`MAXX`. If the filter
yields a single distinct value, MIN/MAX simply return it.

```DAX
Price For Item =
    VAR __Item   = "Widget"
    VAR __Table  = FILTER( Product, Product[Item] = __Item )
    VAR __Result = MAXX( __Table, Product[List Price] )
    RETURN __Result
```

Prefer this over `LOOKUPVALUE`: it uses functions you already use everywhere else, and it
degrades gracefully — `LOOKUPVALUE` errors when the criteria aren't unique, while
`MINX`/`MAXX` over a `FILTER` just returns the min/max.

**Double lookup** (read a value at a derived key — e.g. value on the latest date):

```DAX
Value On Last Date =
    VAR __MaxDate = MAX( Sales[Date] )
    VAR __Rows    = CALCULATETABLE( Sales, KEEPFILTERS( Date[Date] = __MaxDate ) )
    VAR __Result  = MAXX( __Rows, Sales[Amount] )
    RETURN __Result
```

`MAX( Sales[Date] )` reads the last date that has a sale; the filter that follows sits on the
calendar.

## Removing filters — ALL and ALLSELECTED

- `ALL( table | column )` — removes **all** filters (internal *and* external to the visual);
  brings every row into context.
- `ALLSELECTED( … )` — removes filters **internal** to the visual but keeps external ones
  (e.g. slicers). (A simplification, but holds in most cases.)

**Running total** — filter `ALL` rows up to the current row's date:

```DAX
Running Total =
    VAR __MaxDate = MAX( Date[Date] )
    VAR __Table   = FILTER( ALL( Date ), Date[Date] <= __MaxDate )
    VAR __Result  = SUMX( __Table, [Total Sales] )
    RETURN __Result
```

Swap `ALL` → `ALLSELECTED` to make the running total respect slicer selections.

**Previous row / previous occurrence** — find the latest date strictly before the current
one for the item in context, then look up its value (a double lookup with the date filter
removed):

```DAX
Previous Value =
    VAR __Date     = MAX( Date[Date] )
    VAR __Earlier  = CALCULATETABLE( Sales, REMOVEFILTERS( Date ), Date[Date] < __Date )
    VAR __PrevDate = MAXX( __Earlier, Sales[Date] )
    VAR __Result   = CALCULATE( SUM( Sales[Amount] ), REMOVEFILTERS( Date ), Date[Date] = __PrevDate )
    RETURN __Result
```

The item stays filtered by `Product[Item]` from the visual; only the calendar's filters are
removed and replaced.

> **auto-exist caveat:** if two filters target the same table (e.g. a slicer on
> `Item` and an axis on `Date`, both columns of the fact), Power BI computes only the
> *intersection*, which can surprise you even when you used `ALL`. Slice by the dimension
> columns, as above, or be aware of the model's *Value Filter Behavior* setting.

## Grouping rows — three options

All three produce a grouped table; pick by ergonomics:

```DAX
SUMMARIZE(   Sales, Product[Item], "Total", SUM( Sales[Amount] ) )
GROUPBY(     Sales, Product[Item], "Total", SUMX( CURRENTGROUP(), Sales[Amount] ) )  -- must use X + CURRENTGROUP()
SUMMARIZECOLUMNS( Product[Item], "Total", SUM( Sales[Amount] ) )
```

`SUMMARIZECOLUMNS` is the most efficient/modern for set-the-grain work and is the one used
throughout the recipes. **Caveat:** you cannot reference newly-created columns *within* the
same `SUMMARIZECOLUMNS` — add derived columns with `ADDCOLUMNS` afterward.

## Adding columns — ADDCOLUMNS (and the VAR rewrite)

```DAX
-- nested
ADDCOLUMNS(
    SUMMARIZECOLUMNS( Sales[Item], "Avg Qty", AVERAGE( Sales[Qty] ), "Price", MAX( Sales[Price] ) ),
    "Avg Cost", [Price] * [Avg Qty]
)
-- house-style rewrite (preferred: each step a VAR)
VAR __Summary = SUMMARIZECOLUMNS( Sales[Item], "Avg Qty", AVERAGE( Sales[Qty] ), "Price", MAX( Sales[Price] ) )
VAR __Result  = ADDCOLUMNS( __Summary, "Avg Cost", [Price] * [Avg Qty] )
RETURN __Result
```

## Logical flow — IF, SWITCH, SWITCH TRUE

```DAX
-- nested IFs get messy → use SWITCH on a value
SWITCH( __Item, "A", "Green", "B", "Yellow", "Unknown" )

-- SWITCH TRUE() = readable cascade of arbitrary boolean tests
SWITCH( TRUE(),
    ( __Item = "A" || __Item = "B" ) && __Cost > 10, 1,
    0
)
```

Prefer `&&`/`||` over `AND()`/`OR()`. **Complex Selector** pattern: a measure that returns
1/0 from embedded logic, then filtered to `= 1` in the Filters pane — pushes selection
logic into DAX.

## Information functions

- `HASONEVALUE( col )` — TRUE when exactly one distinct value is in context (e.g. a data
  row, not the Total row). Use it to give totals different behavior.
- `SELECTEDVALUE( col, [alt] )` — the single value in context, or `alt` if not exactly one.
  Cleaner than `IF( HASONEVALUE(...), MAX(...), alt )`.
- `ISINSCOPE( col )` — TRUE when `col` is the current grouping level in a hierarchy. **Order
  matters:** in a `SWITCH(TRUE())`, test from the *bottom* of the hierarchy upward (a higher
  level is "in scope" at lower levels too). Only works for columns actually in the visual.

## Selecting columns, IN, set functions

- `SELECTCOLUMNS( table, "NewName", expr, … )` — keep/rename a subset (perf + clarity).
- `IN` / `CONTAINSROW`: `FILTER( ALL( Product[Item] ), Product[Item] IN { "A", "B" } )`. The `{ … }` table
  constructor builds an inline table; `IN` and `CONTAINSROW( table, value )` are equivalent.
- `DISTINCT` / `VALUES` — distinct rows/values of a column (`VALUES` includes a blank row
  for invalid relationships; `DISTINCT` does not).
- `UNION` (append, same column count), `EXCEPT` (rows in A not in B), `INTERSECT` (rows in
  both), `CROSSJOIN` (Cartesian product). `NATURALINNERJOIN` / `NATURALLEFTOUTERJOIN` for
  joining on matching column names.

## The Measure Totals problem and its fix

Some measures don't total correctly in table/matrix visuals (the Total row recomputes the
expression once over all rows instead of summing the visible rows). Classic case: a measure
with a subtraction/non-additive step.

**Fix pattern** — re-summarize at the visual's grain, then `SUMX` the per-row measure:

```DAX
Total Fixed =
    VAR __Table  = SUMMARIZECOLUMNS( Dim[Item], "__v", [Base Measure] )
    VAR __Result = SUMX( __Table, [__v] )
    RETURN __Result
```

Group by exactly the columns the visual groups by, project the per-row measure as a column,
then sum it. (Debug with `RETURN TOCSV( __Table )`.) For a matrix, include each hierarchy
level you want corrected.
