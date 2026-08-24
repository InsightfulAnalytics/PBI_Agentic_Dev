# Dates, Offsets, and Duration

**Read the standing exception in [`../SKILL.md`](../SKILL.md) first.** With a properly formed
date table — the `semantic-models:date-table` DimDate qualifies — prior-period and to-date
measures are written the conventional way, `CALCULATE` + `DATEADD` / `DATESYTD`. That is the
default here.

This reference covers the cases that default does not reach:

- **Non-standard calendars.** The built-in time-intelligence functions assume a standard
  Gregorian calendar. Fiscal years that do not start in January, 4-4-5 / 4-5-4 retail
  calendars and 13-period calendars either break or quietly return the wrong period.
- **Boundaries the built-ins will not express.** "YTD but excluding today because today is
  incomplete", "rolling 12 months ending at the *selected* month", "last year aligned by
  weekday, not by date". `DATESYTD` gives you what it gives you.
- **Models with no usable date table.** Fix the model if you can; use this if you cannot.

The technique in all three cases is the same one DimDate already ships: **offset columns**.

## Dates are integers

A date is the number of days since 1899-12-30 — `DATE( 1899, 12, 30 ) * 1 = 0`. So date
arithmetic is just arithmetic: `[Date] + 1` is tomorrow, `DateA - DateB` is a day count.
No function needed to add N days.

## Offset columns — the number line

An offset is a number line centred on the current period: **0 = now**, negative = past,
positive = future.

```
… -3   -2   -1    0    +1   +2 …
                  ↑ current period
```

DimDate ships these (see the `date-table` skill's `references/column-reference.md`):

| Column | `0` means | Type |
|---|---|---|
| `YearOffset` | this calendar year | int64 |
| `QuarterOffset` | this quarter | int64 |
| `MonthOffset` | this month | int64 |
| `WeekOffset` | this week | int64 |
| `DayOffset` | today | double |
| `FYearOffset` | this fiscal year | int64 |

Because they are precomputed integer columns, every filter over them is a simple integer
comparison — storage-engine work, not formula-engine work.

Rolling your own (custom calendar, or a model whose date table has no offsets — prefer
adding the column in Power Query over computing it in DAX):

```DAX
Year Offset = YEAR( [Date] ) - YEAR( TODAY() )
```

A **general offset** counts distinct periods between a row's period and the current one, so
it stays correct on calendars with irregular period lengths:

```DAX
Month Offset =
    VAR __Today   = TODAY()
    VAR __Current = YEAR( __Today ) * 100 + MONTH( __Today )              -- e.g. 202506
    VAR __Periods = SUMMARIZE( ADDCOLUMNS( DimDate, "__p", YEAR( [Date] ) * 100 + MONTH( [Date] ) ), [__p] )
    VAR __Row     = YEAR( [Date] ) * 100 + MONTH( [Date] )
    VAR __Result =
        IF (
            __Row < __Current,
            -COUNTROWS( FILTER( __Periods, [__p] >= __Row && [__p] < __Current ) ),
             COUNTROWS( FILTER( __Periods, [__p] <= __Row && [__p] > __Current ) )
        )
    RETURN
        __Result
```

Once the offsets exist, **every period calculation is a `FILTER` on an offset** plus the
standard pattern.

## Period-to-date

Filter the calendar to the current period and up to today, set the grain, aggregate:

```DAX
Year To Date =
    // Today's date, so the current period stops at the right place.
    VAR __Today = TODAY()
    // Every day of the current year up to and including today.
    VAR __Table =
        SUMMARIZE (
            FILTER (
                DimDate,
                DimDate[Date] <= __Today
                    && DimDate[YearOffset] = 0
            ),
            DimDate[Date],
            "__v", SUM ( Sales[Amount] )
        )
    VAR __Result = SUMX ( __Table, [__v] )
    RETURN
        __Result
```

- **Exclude today** (incomplete day): change `<=` to `<`. This is the flexibility the
  built-ins cannot give you.
- **QTD / MTD / WTD:** swap the offset column (`QuarterOffset` / `MonthOffset` /
  `WeekOffset` = 0).
- **Fiscal YTD:** `FYearOffset = 0`.
- To make it work **for every row of a visual** rather than only the current period, read the
  row's offset instead of hard-coding `0` —
  `VAR __Offset = IF( HASONEVALUE( DimDate[Year] ), MAX( DimDate[YearOffset] ), 0 )` — and
  build the period end date from it.

## Previous period, rolling windows

- **Previous period:** filter to `offset = -1` instead of `0`.
- **Period over period:** current and previous as two table VARs, then subtract or `DIVIDE`.
- **Rolling N periods:** filter the offset to a range —
  `DimDate[MonthOffset] > -12 && DimDate[MonthOffset] <= 0` for trailing twelve months.
- **Prior-period-to-date:** DimDate ships `IsPYTD` and `IsPFYTD` boolean flags, so
  prior-year-to-date is a single boolean filter rather than a nested time-intelligence call.

## Time and duration

- **Time is the fractional part** of the date number: a day is `1.0`, so an hour is `1/24`.
  Build time tables with `GENERATESERIES`; add and subtract durations as fractions of a day.
- **Decimal to components:** `* 24`, `* 1440`, `* 86400` for hours/minutes/seconds, then
  `INT` and `MOD` to break a duration into an `H:MM:SS` breakdown.
- **Net working duration** (the DAX answer to `NETWORKDAYS`): filter DimDate on
  `IsBusinessDay = TRUE()` between the two dates and `COUNTROWS` it. The holiday list lives
  in the date table, not in the measure.
- **Shifts, time zones, Unix timestamps, milliseconds:** arithmetic on the underlying number,
  not special functions. Unix epoch is seconds since 1970-01-01; convert into the 1899-12-30
  base with arithmetic.

> Formatting a duration for display is a **format-string** problem, not a measure problem —
> keep the measure numeric and use a dynamic format string. See the number-formatting section
> of [`../SKILL.md`](../SKILL.md).
