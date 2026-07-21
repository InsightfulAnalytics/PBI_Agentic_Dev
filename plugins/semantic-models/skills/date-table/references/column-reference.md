# DimDate column reference

58 columns. Everything in the `zOther` display folder is deliberately pushed to the
bottom of the field list -- those are the plumbing columns (offsets, sort keys, flags).
The seven columns with no display folder are the ones meant for day-to-day report use:

`Date`, `Year`, `Month & Year`, `MonthCompleted`, `Year & Month`, `Month Short & Year`,
`Year Selection`.

## Grain and keys

| Column | Type | Notes |
|---|---|---|
| `Date` | dateTime | The grain. Format `dd-mmm-yy`. Relate fact tables to this. |
| `DateInt` | int64 | `yyyymmdd` integer key, for joins to integer date keys. |

## Year

| Column | Type | Folder | Notes |
|---|---|---|---|
| `Year` | int64 | -- | Calendar year. |
| `YearOffset` | int64 | zOther | 0 = current year, -1 = last year. |
| `YearCompleted` | boolean | zOther | Year has fully elapsed. |
| `Year Selection` | string | -- | `"Current Year"` for the current year, otherwise the year number. Slicer-friendly. |
| `Days in Year` | int64 | zOther | 365/366. Used by the `Dates Selected` measure to detect complete years. |

## Quarter

| Column | Type | Folder | Notes |
|---|---|---|---|
| `QuarterOfYear` | int64 | zOther | 1-4. |
| `Quarter & Year` | string | zOther | `Q1 2024`. |
| `QuarternYear` | int64 | zOther | Sort key. |
| `QuarterOffset` | int64 | zOther | 0 = current quarter. |
| `QuarterCompleted` | boolean | zOther | |

## Month

| Column | Type | Folder | Notes |
|---|---|---|---|
| `MonthOfYear` | int64 | zOther | 1-12. Sort key for `Month` and `Month Name Short`. |
| `Month` | string | zOther | `January`. Sorted by `MonthOfYear`. |
| `Month Name Short` | string | zOther | `Jan`. Sorted by `MonthOfYear`. |
| `Month Initial` | string | zOther | `J`, padded with zero-width spaces so the twelve initials stay distinct. |
| `Month & Year` | string | -- | `Jan 2024`. Sorted by `MonthnYear`. |
| `Month Short & Year` | string | -- | `Jan 24`. |
| `Year & Month` | string | -- | `2024 Jan`. |
| `Month Selection` | string | zOther | `"Current Month"` / `"Prior Month"` / `Jan 24`. Slicer-friendly. |
| `MonthnYear` | int64 | zOther | Sort key. |
| `MonthOffset` | int64 | zOther | 0 = current month. |
| `MonthCompleted` | boolean | -- | |
| `MonthEnding` | dateTime | zOther | Last day of the month. |
| `Start Of Month` | dateTime | zOther | First day of the month. The `Dates Selected` measure keys off this. |
| `Days In Month` | int64 | zOther | Used by `Dates Selected` to detect complete months. |
| `DayOfMonth` | int64 | zOther | 1-31. |

## Week (ISO, Monday-based)

| Column | Type | Folder | Notes |
|---|---|---|---|
| `Week & Year` | string | zOther | `2024-07`. Sorted by `WeeknYear`. |
| `WeeknYear` | int64 | zOther | Sort key. |
| `WeekOffset` | int64 | zOther | 0 = current week. |
| `WeekCompleted` | boolean | zOther | |
| `WeekEnding` | dateTime | zOther | Sunday of that week. |
| `Week Ending Short` | string | zOther | `31-Mar`. |

The raw ISO columns the upstream function emits (`ISO Year`, `ISO Weeknumber`,
`ISO Quarter`, and friends) are **removed** by the final step of the M function --
the week columns above already carry the ISO logic.

## Day

| Column | Type | Folder | Notes |
|---|---|---|---|
| `DayOfWeek` | int64 | zOther | Base set by the `WDStartNum` argument (this template uses 1 = Monday as 1). |
| `DayOfWeekName` | string | zOther | `Monday`. |
| `Weekday Initial` | string | zOther | `M`, zero-width-space padded. |
| `Day & Month` | string | zOther | `31-Mar`. |
| `DayNMonth` | double | zOther | `MMdd` as a number. Set it as the sort column on `Day & Month` if you use that on an axis -- it is not preset. |
| `DayOffset` | double | zOther | Days from today. 0 = today. |
| `Day Type` | string | zOther | `Weekday` / `Weekend` / `Holiday`. |
| `IsWorkingDay` | boolean | zOther | Mon-Fri. |
| `IsHoliday` | string | zOther | `"Unknown"` unless a holiday list was passed to the function. |
| `IsBusinessDay` | boolean | zOther | Working day and not a holiday. |
| `IsAfterToday` | boolean | zOther | Useful for trimming future dates out of visuals. |

## Fiscal

Driven by the `FYStartMonthNum` argument (this template defaults to `7`, i.e. a July
fiscal year start -- the Australian convention).

| Column | Type | Folder | Notes |
|---|---|---|---|
| `FYear` | string | zOther | `FY25`. |
| `FYearOffset` | int64 | zOther | 0 = current fiscal year. |
| `FYear Selection` | string | zOther | `"Current Year"` / `FY24`. Slicer-friendly. |
| `FQuarter` | string | zOther | `FQ1`. |
| `FQuarternYear` | double | zOther | Sort key. |
| `IsCurrentFQ` | boolean | zOther | |
| `Period` | int64 | zOther | Fiscal period 1-12. |
| `FPeriodnYear` | double | zOther | Sort key. |
| `IsCurrentFP` | boolean | zOther | |
| `FWeek` | int64 | zOther | Fiscal week number. |
| `FWeeknYear` | int64 | zOther | Sort key. |
| `IsCurrentFW` | boolean | zOther | |

## To-date flags

| Column | Type | Folder | Notes |
|---|---|---|---|
| `IsPYTD` | boolean | zOther | Same day-of-year range in the prior calendar year. |
| `IsPFYTD` | boolean | zOther | Equivalent range in the prior fiscal year. |

Both let you write prior-period-to-date measures as a simple filter rather than with
time intelligence functions:

```dax
Sales PYTD =
CALCULATE( [Sales], DimDate[IsPYTD] = TRUE() )
```

## Local changes vs. the upstream function

The bundled `FunctionDateTable` differs from Melissa de Korte's original in its final
steps (all inside the M function, after `InsertPFYTD`):

- **Renames:** `Month Name` to `Month`, `MonthShortName` to `Month Name Short`,
  `Fiscal Year` to `FYear`, `FiscalYearOffset` to `FYearOffset`,
  `Fiscal Quarter` to `FQuarter`, `Fiscal Period` to `Period`, `Fiscal Week` to `FWeek`.
- **Added columns:** `Year & Month`, `Month Short & Year`, `Month Selection`,
  `FYear Selection`, `Day & Month`, `Week Ending Short`, `DayNMonth`, `Start Of Month`,
  `DayOffset`, `Days in Year`, `Days In Month`, `Year Selection`.
- **Removed columns:** the nine raw `ISO *` columns and `Fiscal Year & Week`.

If you swap in a newer upstream version of the function you will lose these, and the
`Dates Selected` measure (which reads `Start Of Month`, `Days in Year` and
`Days In Month`) will break.
