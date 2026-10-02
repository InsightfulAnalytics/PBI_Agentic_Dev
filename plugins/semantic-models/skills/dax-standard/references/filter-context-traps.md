# Filter-context traps

Measures that are correct in a clean context and wrong in the one a report actually hands them. None
of these errors: each returns a plausible number or a blank, so the check is to evaluate the measure
under the context the visual produces, not under no filters at all.

## A second calendar's relationship does not cancel the first

`USERELATIONSHIP` swaps which relationship is active **between the same pair of tables**. It does
nothing to a relationship from a **different** table. With two calendar tables both related to one
fact (a connected `'Calendar'` and a disconnected-style `'Calendar Axis'` reached through an inactive
relationship), both filters apply at once inside the `CALCULATE`.

The trap shows on a "show the whole period while hovering one member" tooltip: the hovered week
arrives as a `'Calendar'` filter, intersects with the tooltip's axis on `'Calendar Axis'`, and every
week but the hovered one evaluates to blank and drops out.

```dax
Units All Weeks =
VAR __Period = VALUES ( 'Calendar'[Period] )          -- capture before removing
RETURN
    CALCULATE (
        [Units],
        REMOVEFILTERS ( 'Calendar' ),
        KEEPFILTERS ( TREATAS ( __Period, 'Calendar Axis'[Period] ) ),
        USERELATIONSHIP ( 'Calendar Axis'[Date], 'Fact'[Week Commencing] )
    )
```

`REMOVEFILTERS` the connected calendar, and re-project the grain you want to keep onto the other one
with `TREATAS`, captured before the removal. A hard-coded visual-level filter on the connected
calendar (a fixed period) would then pin `VALUES()` regardless of the slicer, so remove those too.

## A calculation item that slices the calendar can block time intelligence

A calculation item wraps the measure from the outside, so its filter lands first, and the measure's
own time intelligence runs inside it. Time intelligence shifts the period it works on; any other
calendar filter it does not shift survives and intersects with the shifted period.

- A **plain column filter on a year-relative column** is fine: `'Calendar'[Fiscal Period] = 1`
  under a prior-year measure still means "period 1 of last year".
- A **whole-table `FILTER ( 'Calendar', ... )`** returns calendar rows, an arbitrarily shaped filter
  over every column including the date, and pins the current year's dates. Prior year ∩ this year's
  period-1 dates is empty.
- An **absolute column** (a month offset from today, a "is current year" flag) is not shifted either,
  so "offset <= 0" under a prior-year measure returns the wrong span.

The tell: the this-year column is right and the last-year column is blank. Write calculation items
that slice the calendar with single, year-relative columns:

```dax
CALCULATE (
    SELECTEDMEASURE (),
    ALLEXCEPT ( 'Calendar', 'Calendar'[Fiscal Year] ),
    'Calendar'[Fiscal Period] = 1
)
```

For year-to-date and year-to-go items, compare `Fiscal Period` with the current period (computed with
the calendar's filters removed) rather than filtering an absolute offset column.

## A report-page tooltip inherits every projected column

The tooltip page is filtered by all of the raising visual's projected columns, not just the hovered
mark. The basic trap and its `ALL` fix are in `reports:pbir-cli` `references/interactions.md`. Two
refinements:

- **`REMOVEFILTERS` on the one column you mean is not enough when another projected column is one to
  one with it.** A rank-among-the-languages measure did
  `CALCULATETABLE ( VALUES ( 'Mix'[Language] ), REMOVEFILTERS ( 'Mix'[Language] ) )`, but the panel
  also projected `'Mix'[Series Colour]`, which is one to one with Language, so the set stayed pinned
  to the hovered language by its colour and the measure returned 1 on every hover. A presentation
  column carries the dimension's identity as well as the key does. Rebuild from `ALL ( table )` and
  re-apply only the filters you can name:

  ```dax
  VAR __Year     = SELECTEDVALUE ( 'Mix'[Year] )      -- read in the outer context: still the hover
  VAR __ThisYear = FILTER ( ALL ( 'Mix' ), 'Mix'[Year] = __Year )
  ```

- **Test under the inherited filter.** Evaluate the measure with the presentation columns filtered,
  `CALCULATETABLE ( SUMMARIZECOLUMNS ( ... ), TREATAS ( { "#1971C2" }, 'Mix'[Series Colour] ) )`, or
  iterate over every projected column and compare with the value computed with no filters. A test
  that filters only the key passes while the shipped tooltip is wrong.

Check the raising visual's projections before writing any tooltip measure: a visual projecting only
its own axis columns is safe; one projecting fact or presentation columns is not.

## A breakdown that must ignore its own slicer

A win-rate or mix breakdown shown beside a slicer on the same dimension (or a calculation-group
slicer) gets filtered by that slicer and collapses to the selected member. Name the member explicitly
and remove the slicer's filter:

```dax
White Win % =
CALCULATE ( [Win %], REMOVEFILTERS ( 'Winner' ), 'Winner'[Winner] = "White" )
```

Bind such breakdowns as separate scalar measures rather than putting the dimension on the axis, so a
calculation group in the slicer cannot also drop the category rows.

Calculation groups used as slicers compose: picking an item in each wraps `SELECTEDMEASURE()` once
per group, so every selection applies at once, provided each group has its own `precedence`
(`semantic-model` `references/calculation-groups.md`). A "single select with All on top" slicer is a
calculation group whose first item is plain `SELECTEDMEASURE()` (the "All" item), bound to a
single-select slicer on the group's name column sorted by its ordinal.

## A variable named after a DAX keyword

`VAR Rows = ...` parses, round-trips through TMDL and passes `pbir validate --fields`; nothing offline
compiles DAX. The measure fails only when a visual first asks for it ("Something's wrong with one or
more fields"), possibly sessions later. The `__` prefix rule in SKILL.md exists to prevent exactly
this; audit variable names against the DAX keyword list when a measure was written without it.
