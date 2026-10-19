# Filter the dimension, not the fact

When a measure narrows rows by an attribute, filter the dimension column that the fact table relates
to, not the fact table and not the fact's copy of the key. Group by dimension columns too, including
the calendar's own period columns, rather than by the fact's date or key columns.

This holds whenever a dimension carries the attribute. When none does but the column belongs in one,
[propose the dimension](#no-dimension-yet-propose-one). The cases where the fact is the right place
are listed at the end, under [When the fact is the right place](#when-the-fact-is-the-right-place).
Whichever case applies, say it in the reply: SKILL.md
[Filter the dimension, not the fact](../SKILL.md#filter-the-dimension-not-the-fact).

## Why

- **Speed.** A dimension holds each value once, but the fact holds it once per row. A dimension
  filter is resolved over the dimension's few rows and reaches the fact as a join on the relationship
  key. The storage engine is built for that join and can cache it across queries. A filter on the
  fact column has to be resolved against the fact column itself, and `FILTER ( Fact, … )` builds a
  table of fact rows.
- **Scope.** Used as a `CALCULATE` filter, `FILTER ( Fact, … )` is a table filter. It constrains
  every column of the expanded fact table, related dimensions included, not only the column you
  meant.
- **Readability.** The dimension column is the business attribute, the same one the slicers and
  visuals use. `Dim_Pricing_Type[Pricing Type] <> BLANK ()` says what it means. Searching for the
  dimension column also finds every measure that filters by it.

## Find the dimension first

Before writing a filter on `Fact[Col]`, list the fact's relationships:

```bash
grep -n -A1 "fromColumn: Fact_Sales\." definition/relationships.tmdl
#   fromColumn: Fact_Sales.'Pricing Type'
#   toColumn: Dim_Pricing_Type.'Pricing Type'
```

The `toColumn` is the column to filter. A relationship marked `isActive: false` does not carry a
filter on its own; see the exceptions.

No relationship from the column means no dimension carries it yet. Decide which kind of column it
is: a dimension-like column gets [a proposed dimension](#no-dimension-yet-propose-one), anything
else is [an exception](#when-the-fact-is-the-right-place).

## No dimension yet: propose one

A column is **dimension-like** when it describes the row rather than measuring it, and people would
slice or group by it:

- It holds text or a code, not an amount or a quantity.
- It has few distinct values against the fact's row count, each repeated across many rows:
  `Pricing Type`, `Status`, `Channel`, `Region`, `Unit of Measure`.
- Companions often sit beside it on the fact: a code and its description, a region and its country.
  They belong in the same dimension.

An order or invoice number, unique or nearly unique per transaction, is a degenerate attribute and
stays on the fact. A date column belongs to the calendar: relate it to the model's date table, or add
one with `semantic-models:date-table`.

When the column is dimension-like and no dimension carries it, propose a dimension and wait for the
user's answer before building it. The proposal names:

- **The table and its columns.** `Dim_<Attribute>` (or the model's own naming convention), holding
  the attribute plus any companion, sort-order or description column the fact carries beside it.
- **Where it is built.** In the source (a view, a lakehouse table) or in Power Query, never as a DAX
  calculated table ([Tables come from Power Query, not DAX](../SKILL.md#tables-come-from-power-query-not-dax)).
  In Power Query, reference the fact's query, keep the attribute columns and remove duplicates. That
  re-reads the source on every refresh, so a source-side table is better where the user owns the
  source.
- **The relationship.** Many-to-one from `Fact[Col]` to `Dim_<Attribute>[Col]`, single direction.
- **What moves.** Hide `Fact[Col]` so slicers and visuals bind to the dimension, and list the
  measures, slicers and visuals that switch to it.

Until the user agrees, write the measure against the fact column as a column filter, such as
`KEEPFILTERS ( Fact_Sales[Status] <> "Cancelled" )`, with a `//` comment naming the proposed
dimension, so the later switch is one edit. A new dimension is a model change: build it through
`semantic-models:model-change`, then move the measure's filter to it.

## Patterns

### A column filter on a fact attribute

```dax
-- don't
VAR __Promo =
    FILTER (
        ALL ( Fact_Sales[Pricing Type] ),
        Fact_Sales[Pricing Type] <> BLANK ()
    )

-- do: the same test on the dimension; the relationship carries it to the fact
VAR __Promo =
    FILTER (
        ALL ( Dim_Pricing_Type[Pricing Type] ),
        Dim_Pricing_Type[Pricing Type] <> BLANK ()
    )
VAR __Result =
    CALCULATE (
        [Trading Weeks],
        KEEPFILTERS ( __Promo )
    )
```

### A FILTER over the fact with RELATED

```dax
-- don't: iterates the fact, and as a filter it constrains the whole expanded table
VAR __Rows =
    FILTER (
        Fact_Sales,
        RELATED ( Dim_Product[Unit of Measure] ) <> "SGL"
    )

-- do: filter the dimension, then build what you need from the fact under it
VAR __NonSingles =
    FILTER (
        ALL ( Dim_Product[Unit of Measure] ),
        Dim_Product[Unit of Measure] <> "SGL"
    )
VAR __Weeks =
    CALCULATETABLE (
        SUMMARIZE (
            Fact_Sales,
            Dim_Customer[Customer],
            Dim_Product[Product],
            Calendar[Fiscal StartOfWeek]
        ),
        KEEPFILTERS ( __NonSingles )
    )
```

### Grouping by the fact's date or key

```dax
-- don't
SUMMARIZE ( Fact_Sales, Dim_Customer[Customer], Fact_Sales[Week Commencing] )

-- do: the calendar's week column
SUMMARIZE ( Fact_Sales, Dim_Customer[Customer], Calendar[Fiscal StartOfWeek] )
```

`SUMMARIZE ( Fact, Dim[a], Dim[b] )` is fine. It lists the combinations that have fact rows, grouped
by dimension columns. That is grouping, not filtering.

### Calendar-based time intelligence

When the model defines a calendar (`calendar` in the date table's TMDL), group and filter only on
the columns that calendar tags. `DATEADD` and `SAMEPERIODLASTYEAR` shift the tagged columns and leave
every other filter on the calendar table exactly as it was. Suppose an untagged column identifies an
absolute period, such as a date, an offset or an "is current year" flag. Its filter survives the
shift and intersects the shifted period, so the last-year number comes back blank or wrong.

For a week grain, use the column the calendar tags for weeks, not the fact's date.

## Check before you switch

Moving a filter from the fact to the dimension can change the number in two ways.

1. **Values missing from the dimension.** A fact row whose key has no match in the dimension belongs
   to the blank member. A dimension filter that excludes blank drops that row, where the fact filter
   kept it. Find such values first:

   ```dax
   EVALUATE
   EXCEPT (
       DISTINCT ( Fact_Sales[Pricing Type] ),
       DISTINCT ( Dim_Pricing_Type[Pricing Type] )
   )
   ```

   A row back is a referential-integrity gap. Fix it upstream, or say in the measure's comment that
   those rows now drop out.

2. **Slicers on the same column.** A slicer on `Dim_Pricing_Type[Pricing Type]` never touched a
   fact-column filter, because the two sat on different columns. Once the measure filters the
   dimension column, a `CALCULATE` filter replaces the slicer's selection unless it is wrapped in
   `KEEPFILTERS`. Decide which you want and say so in the comment.

Prove the switch the way this skill proves any rewrite. Define the old body as a query measure, then
compare it with the new one over the cells the report shows (**Prove a flattened measure**, under
[Keep the VARs flat](../SKILL.md#keep-the-vars-flat)).

## When the fact is the right place

"Whenever a dimension carries the attribute" leaves three cases where you filter the fact:

- **No dimension carries the attribute, and none should.** A numeric condition (`Fact_Sales[Qty] > 0`),
  a comparison of two columns on the same row (`Orders[Delivered] <= Orders[Promised]`) or a
  degenerate attribute (an order number) has nowhere else to live. As a `CALCULATE` filter, use a
  column filter, such as `KEEPFILTERS ( Fact_Sales[Qty] > 0 )`, never `FILTER ( Fact_Sales, … )`. As
  the rows an X-aggregator iterates, `FILTER ( Fact_Sales, Fact_Sales[Qty] > 0 )` is step 2 of the
  core pattern and stays. A dimension-like attribute is not this case:
  [propose a dimension](#no-dimension-yet-propose-one).
- **A very large dimension.** `tabular-editor:te-cli` `references/semantic-modeling-practices.md`
  puts the cut-off at about 131K rows. Above that, the dimension filter's index is not cached and
  filtering the fact can be cheaper. Measure with server timings (`semantic-models:dax-optimisation`)
  before you choose the fact.
- **An inactive relationship.** A dimension filter reaches the fact only through an active
  relationship. If the measure needs the inactive one, add `USERELATIONSHIP`, or filter the fact
  column and say why in the comment.

## Review checklist

Flag any of these when writing or reviewing a measure:

- `FILTER ( <fact table>, … )` used as a `CALCULATE` filter, or iterating the fact on a condition a
  dimension carries or should carry.
- `ALL ( <fact>[col] )`, or a boolean filter on `<fact>[col]`, when `relationships.tmdl` has
  `fromColumn: <fact>.<col>`.
- `RELATED ( <dimension>[…] )` inside a `FILTER` over the fact.
- `SUMMARIZE`, `GROUPBY` or `SUMMARIZECOLUMNS` grouping by the fact's date or key column instead of
  the dimension's.
- A filter or grouping on a dimension-like fact column that no dimension carries: propose the
  dimension.
- A time-intelligence measure that filters a calendar-table column the calendar does not tag.
