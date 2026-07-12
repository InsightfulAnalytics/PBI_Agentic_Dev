# Time Intelligence Without Time-Intelligence Functions

From *DAX For Humans* Ch. 3 (Dates and Calendars) and Ch. 6 (Time and Duration). This is
the most distinctive part of the method: replace DAX's 30+ "time intelligence" functions
(`TOTALYTD`, `SAMEPERIODLASTYEAR`, `PREVIOUSQUARTER`, `DATEADD`, …) with **offset
columns** + the standard No-CALCULATE pattern.

## Why avoid the built-in time-intelligence functions

- They assume a **standard Gregorian calendar**. They break on custom fiscal calendars
  (e.g. fiscal year starting June 1) and 4-4-5 / 4-5-4 retail calendars.
- They are **inflexible** — e.g. you can't easily say "YTD but excluding today as an
  incomplete day." `TOTALYTD` gives you what it gives you.
- They are opaque (CALCULATE under the hood), so they're hard to debug.

Offsets work identically for standard *and* custom calendars, and are fully transparent.

## Dates are integers

A date is the number of days since 1899-12-30. `DATE(1899,12,30) * 1 = 0`. Therefore you
can do arithmetic directly: `Date + 1` is tomorrow; `DateA - DateB` is a day count. No
special functions needed for "add N days."

## Set up: a measures table + a real date table

- **Measures table:** a blank/empty table to hold measures (blank Power Query query, an
  empty Enter-data query, or `Calculations = { "" }`). Hide its column → it shows a
  calculator icon and sorts to the top.
- **Date table:** the book *demonstrates* `CALENDAR( start, end )` / `CALENDARAUTO()` in DAX
  for teaching, but recommends building the real one in **Power Query (M)** or the source
  (SQL), not DAX. Melissa de Korte's `fnDateTable` M function produces ~60 columns
  including ready-made offset columns (`CurrYearOffset`, `CurrQuarterOffset`,
  `CurrMonthOffset`, `CurrWeekOffset`, `CurrDayOffset`, plus ISO and fiscal variants).

Typical DAX-built calendar columns (for learning): `Year = YEAR([Date])`,
`Month = FORMAT([Date],"mmmm")`, `MonthSort = MONTH([Date])`,
`Weekday = FORMAT([Date],"dddd")`, `WeekdaySort = WEEKDAY([Date],2)`,
`Weeknum = WEEKNUM([Date],2)`, `Day = DAY([Date])`. Set **Sort by column** on text columns
(`Month` → `MonthSort`, `Weekday` → `WeekdaySort`).

## The offset idea

An offset is a number line centered on **today = 0**: past = negative, future = positive.

```
… -3   -2   -1    0    +1   +2 …
              ↑ current period
```

```DAX
Year Offset = YEAR( [Date] ) - YEAR( TODAY() )    -- -1 last year, 0 this year, +1 next year
```

A **general offset** (works for year, month, week — change the part used) counts the
distinct periods between a row's period and the current one. Conceptually:

```DAX
Month Offset =
    VAR __Today   = TODAY()
    VAR __Current = YEAR( __Today ) * 100 + MONTH( __Today )      -- e.g. 202506
    VAR __Periods = SUMMARIZE( ADDCOLUMNS( Date, "__p", YEAR([Date])*100 + MONTH([Date]) ), [__p] )
    VAR __Row     = YEAR( [Date] ) * 100 + MONTH( [Date] )
    VAR __Result  =
        IF( __Row < __Current,
            -COUNTROWS( FILTER( __Periods, [__p] >= __Row && [__p] < __Current ) ),
             COUNTROWS( FILTER( __Periods, [__p] <= __Row && [__p] > __Current ) ) )
    RETURN __Result
```

Once you have offset columns, **every period calculation is just a `FILTER` on the offset**
plus the standard pattern.

## Period-to-date (YTD / QTD / MTD / WTD)

Filter the calendar to the current period (`offset = 0`) and up to today, summarize at the
grain, `SUMX`:

```DAX
Year To Date =
    VAR __Today  = TODAY()
    VAR __Table  = SUMMARIZE(
                       FILTER( Date, Date[Date] <= __Today && Date[CurrYearOffset] = 0 ),
                       Date[Date], "__v", SUM( Sales[Amount] ) )
    VAR __Result = SUMX( __Table, [__v] )
    RETURN __Result
```

- Want to **exclude today** (incomplete day)? Change `<=` to `<`. (Impossible with
  `TOTALYTD` — the inflexibility point.)
- **QTD/MTD/WTD:** swap the offset column (`CurrQuarterOffset` / `CurrMonthOffset` /
  `CurrWeekOffset` = 0) and the period boundary.
- To make it work **for every row of a visual** (not just the current period), read the
  row's offset with `IF( HASONEVALUE( Date[Year] ), MAX( Date[CurrYearOffset] ), 0 )` and
  build the period end date from it, instead of hard-coding `offset = 0`.

## Previous period / previous year / rolling

- **Previous period:** filter to `offset = -1` (year/quarter/month/week) instead of `0`.
- **Period-over-period:** compute current and previous as two table VARs, subtract/divide.
- **Rolling N periods:** filter `offset` to a range, e.g. `Date[CurrMonthOffset] > -12 &&
  Date[CurrMonthOffset] <= 0` for a trailing-12-months window.
- **Previous year-to-date / previous-quarter-to-date** etc. combine a period filter with the
  to-date boundary, all via offsets — same shape throughout.

> Because offsets are precomputed columns, these filters are simple integer comparisons —
> SE-friendly and fast.

## Time and duration (Ch. 6)

- **Time** is the fractional part of a date number (a day = 1.0, so an hour = 1/24). Build
  time tables with `GENERATESERIES`. Add/subtract durations as fractions of a day.
- **Decimal ↔ components:** convert a duration to seconds/minutes/hours with arithmetic
  (`* 24`, `* 1440`, `* 86400`) and `INT`/`MOD` to break out an `H:MM:SS` breakdown.
- **Net work duration** (business hours/days): build or filter a calendar of working
  periods and `SUMX`/`COUNTROWS` over it — the No-CALCULATE answer to `NETWORKDAYS`.
- **Shifts, time zones, Unix timestamps, milliseconds:** all handled with offset/arithmetic
  on the underlying number rather than special functions (Unix epoch = seconds since
  1970-01-01; convert with arithmetic to the 1899-12-30 base).
