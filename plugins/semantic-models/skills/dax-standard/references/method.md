# The Method

The foundation of the house style. Every recipe in the other references is an application
of what is here — read this one first.

## 1. Think in DAX — tables, rows, columns (not cells)

Excel thinks in **cells and ranges** (`=B2*C2`, `=SUM(B2:B6)`). DAX thinks in **tables,
and by proxy rows and columns**. You cannot point at "a cell." Instead you **filter a
table down to the row(s) you want, then select a column** from that filtered set.

Internalizing this one idea is what makes the rest easy. Every measure becomes: *which
rows do I want → what do I compute over them.*

## 2. FILTER — explicit filtering

`FILTER( <table>, <condition> )` returns the rows of `<table>` that satisfy the condition.
Combine conditions with the operators (preferred over `AND()`/`OR()` — they read more
naturally):

- `&&` = AND `||` = OR `<>` = not equal
- Group with parentheses: `( a || b ) && c`

```DAX
FILTER( Sales, ( Sales[Region] = "East" || Sales[Region] = "West" ) && Sales[Qty] = 3 )
```

`FILTER` is the workhorse. Anything a `CALCULATE` filter argument does, an explicit
`FILTER` over the right table can do — visibly, and as a step you can inspect.

## 3. X-aggregators — iterate a table, then aggregate

Every plain aggregator has an **X** twin: `SUM/SUMX`, `AVERAGE/AVERAGEX`,
`MIN/MINX`, `MAX/MAXX`, `COUNT/COUNTX`, plus `STDEVX.P/.S`, `VARX.P/.S`, `MEDIANX`,
`RANKX`, `CONCATENATEX`, etc.

- Plain version takes **one column**: `SUM( Sales[Amount] )`.
- X version takes **a table + a row expression**: `SUMX( Sales, Sales[Qty] * Sales[Price] )`.
- `SUM( Sales[Amount] )` is literally syntax sugar for `SUMX( Sales, Sales[Amount] )`.

The X versions are more flexible because the **first argument can be any table
expression** — including a `FILTER(...)` or a table `VAR`. That is what lets you filter
first, then aggregate, with no CALCULATE:

```DAX
MINX( FILTER( Sales, Sales[Region] <> "East" ), Sales[Amount] )
```

## 4. Variables — compose the steps

`VAR name = <expr>` … `RETURN <expr>`. Variables:

- remove duplicated sub-expressions (evaluate a table once, reuse it),
- make each step nameable and readable,
- can help performance (no re-evaluation),
- and — crucially — make the measure **debuggable** (see §6).

Conventions: prefix names with `__`; end with `VAR __Result = …` then `RETURN __Result`;
put no functions after `RETURN`. The `__` convention mirrors how the engine names the
variables in the queries Power BI generates internally (visible via Performance Analyzer).

## 5. The pattern

```DAX
Measure =
    VAR __Input  = <scalars you need from current context>
    VAR __Table  = FILTER( <table>, <conditions using __Input> )   -- filter / group rows
    VAR __Result = <X-aggregator>( __Table, <row expression> )     -- aggregate
    RETURN
        __Result
```

1. **Scalar VAR(s)** — capture values from the current filter context, almost always with
   `MAX( Dim[Col] )` / `SELECTEDVALUE( Dim[Col] )` (a single value "in scope" for the row).
2. **Table VAR** — build the exact set of rows the calculation needs (`FILTER`, often over
   `ALL(...)` to escape the visual's context, and/or `SUMMARIZE` to set the grain).
3. **X-aggregator** — reduce the table to the answer.

Everything scales from here: add more scalar VARs, chain table VARs (filter a filtered
table), add columns with `ADDCOLUMNS`, branch with `SWITCH`. The shape never changes.

### Why `MAX( Dim[Col] )` to read "the current value"
Inside a table/matrix row, a dimension column has one value in context, but DAX still
needs a single-value reducer to read it. `MAX(...)` (or `SELECTEDVALUE(...)`, or
`MIN(...)`) returns that value. This replaces the implicit context transition that
CALCULATE/measure-references rely on.

## 6. Debugging — swap the RETURN

The single biggest practical payoff. Every intermediate is a `VAR`, so to inspect it,
temporarily change what you `RETURN`:

```DAX
    RETURN COUNTROWS( __Table )    -- did the filter keep the rows I expected?
    RETURN TOCSV( __Table )        -- render the actual rows as CSV text in a card/table
    RETURN __Input                 -- what scalar did context give me?
```

`TOCSV( table, [maxRows], [delimiter], [includeHeaders] )` turns a table into text so you
can *see* it in a visual — drop it in a Table visual set to Consolas, which is monospaced
and left-aligns. `EVALUATEANDLOG(...)` logs intermediate tables/values for viewing in DAX
query view or SQL Server Profiler.

This is impossible with CALCULATE: you cannot split nested `CALCULATE` calls into separate
steps without changing the result, so there is no native way to watch what it does.

## 7. The explicit form vs the CALCULATE form

The same calculation, both ways:

```DAX
-- house style
Sales No East =
    VAR __Table  = FILTER( Sales, Sales[Region] <> "East" )
    VAR __Result = SUMX( __Table, Sales[Amount] )
    RETURN __Result

-- CALCULATE
Sales No East C = CALCULATE( SUM( Sales[Amount] ), Sales[Region] <> "East" )
```

Both return the same number. CALCULATE is more compact, but:

- It is a **black box** — its filter argument silently *replaces* context, and you cannot
  step through it.
- It carries a **mini-language** of filter modifiers (`ALL`, `ALLEXCEPT`, `REMOVEFILTERS`,
  `KEEPFILTERS`, `USERELATIONSHIP`, `CROSSFILTER`, …) with interaction rules that have to be
  memorised rather than read off the code (e.g. the innermost nested CALCULATE filter wins;
  `KEEPFILTERS` intersects instead of replacing).

The explicit version trades a little brevity for transparency and debuggability. That trade
is the whole point. (For when CALCULATE *is* the right call, see
[`calculate-and-performance.md`](calculate-and-performance.md).)
