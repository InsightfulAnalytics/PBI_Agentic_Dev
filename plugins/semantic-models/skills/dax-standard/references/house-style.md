# House style: the TMDL details and a worked example

Detail for [House style](../SKILL.md#house-style-short-lines-comments-body-on-the-second-line)
in SKILL.md.

## The blank line after `=`

**Verified safe (2026-07-22):** a blank line *immediately after* `=`, before the body, does NOT
trigger the `InvalidLineType: Empty` that the `pbip:tmdl` skill's `references/authoring-gotchas.md`
warns about. Power BI Desktop opens it cleanly. That warning is about a blank line *breaking the middle* of a
multi-line expression (between two body lines), which is a different thing. Do not blank-line
inside the body; do blank-line right after `=`.

**Durability caveat:** Power BI Desktop's own serializer writes *single-line* expressions inline
(`measure X = expr`) when it re-saves a model. So one-liners you format as body-on-line-2 can
revert to inline after a Desktop save. Multi-line measures keep the blank-line/body-on-line-2 form
(it is Desktop's own canonical form for them). Author on disk in the line-2 form regardless; just
know a Desktop round-trip may re-inline the trivial one-liners.

## Worked example

Worked example in this house style:

```DAX
Net Sales % =
    // Keep every order status except Cancelled ...
    VAR __Statuses =
        FILTER (
            ALL ( 'Order Status'[Status] ),
            'Order Status'[Status] <> "Cancelled"
        )
    // ... take the sales of those orders ...
    VAR __NetSales =
        CALCULATE (
            [Total Sales],
            KEEPFILTERS ( __Statuses )
        )
    // ... and express them as a share of all sales
    VAR __Result =
        DIVIDE (
            __NetSales,
            [Total Sales]
        )
    RETURN
        __Result
```

The same measure in a **TMDL** file — note the **blank line right after `=`**, and the body indented
two levels deeper than the `measure` declaration. The blank line is what makes the editor show the
body on line 2:

```tmdl
/// Cancelled-adjusted sales as a share of all sales.
measure 'Net Sales %' =

		// keep every order status except Cancelled ...
		VAR __Statuses =
		    FILTER (
		        ALL ( 'Order Status'[Status] ),
		        'Order Status'[Status] <> "Cancelled"
		    )
		// ... take the sales of those orders ...
		VAR __NetSales =
		    CALCULATE (
		        [Total Sales],
		        KEEPFILTERS ( __Statuses )
		    )
		// ... and express them as a share of all sales
		VAR __Result =
		    DIVIDE (
		        __NetSales,
		        [Total Sales]
		    )
		RETURN
		    __Result
	formatString: 0.0%
```

Single-expression measures get the same treatment — `=`, a blank line, then the call:

```tmdl
/// One row per order; count them.
measure 'Total Orders' =

		COUNTROWS ( Sales )
	formatString: #,##0
```
