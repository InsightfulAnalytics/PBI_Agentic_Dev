# Layout Example and Time Granularity

## Executive Dashboard Layout (1920x1080, margin=36, gap=24)

1920x1080 is the default page size. The numbers below are the 1280x720 layout scaled by 1.5 --
useful to know if you ever have to convert an existing report, since a clean 1.5x preserves the
composition exactly (font sizes included).

```bash
# Page title textbox
pbir add visual textbox "Sales.Report/Overview.Page" \
  --x 36 --y 24 --width 1848 --height 84

# KPI visuals with targets and trend lines (y=132, h=240)
# 3 KPIs: each w=600, gaps: 36 + 600 + 24 + 600 + 24 + 600 + 36 = 1920
pbir add visual kpi "Sales.Report/Overview.Page" --title "Revenue" \
  -d "Indicator:Invoices.Turnover" -d "Goal:Invoices.Turnover 1YP" \
  -d "TrendLine:Date.Calendar Month (ie Jan)" \
  --x 36 --y 132 --width 600 --height 240

pbir add visual kpi "Sales.Report/Overview.Page" --title "Order Lines" \
  -d "Indicator:Orders.Order Lines" -d "Goal:Orders.Order Lines 1YP" \
  -d "TrendLine:Date.Calendar Month (ie Jan)" \
  --x 660 --y 132 --width 600 --height 240

pbir add visual kpi "Sales.Report/Overview.Page" --title "Margin %" \
  -d "Indicator:Invoices.Selling Margin (%)" -d "Goal:Invoices.Selling Margin (%) 1YP" \
  -d "TrendLine:Date.Calendar Month (ie Jan)" \
  --x 1284 --y 132 --width 600 --height 240

# Trend chart (left, y=396, h=330)
pbir add visual lineChart "Sales.Report/Overview.Page" --title "Monthly Trend" \
  --x 36 --y 396 --width 912 --height 330

pbir visuals bind "Sales.Report/Overview.Page/Monthly Trend.Visual" \
  -a "Category:Date.Calendar Month (ie Jan)" -a "Y:Invoices.Turnover"

# Breakdown chart (right, y=396, h=330)
pbir add visual barChart "Sales.Report/Overview.Page" --title "by Region" \
  -d "Category:Regions.Territory" -d "Y:Invoices.Turnover" \
  --x 972 --y 396 --width 912 --height 330

# Detail table (full width, y=750, h=294)
pbir add visual tableEx "Sales.Report/Overview.Page" --title "Detail by Account" \
  --x 36 --y 750 --width 1848 --height 294

pbir visuals bind "Sales.Report/Overview.Page/Detail by Account.Visual" \
  -a "Values:Customers.Key Account Name" -a "Values:Products.Product Name" \
  -a "Values:Invoices.Turnover" -a "Values:Orders.Order Lines"
```

## Spacing Verification

```
Title bottom:  24+84  = 108.  Gap to KPIs:    132-108 = 24  [ok]
KPI bottom:    132+240= 372.  Gap to charts:  396-372 = 24  [ok]
Chart bottom:  396+330= 726.  Gap to table:   750-726 = 24  [ok]
Table bottom:  750+294= 1044. Bottom margin:  1080-1044 = 36 [ok]
Left margin:   36.  Right edge: 36+1848=1884.  Right margin: 1920-1884 = 36 [ok]
```

## Sizing tables to their row count

A `tableEx` silently truncates rows to fit its height -- no scrollbar hint, no error. A table that
shows 3 of 6 categories plus a correct-looking grand total is the worst kind of wrong, because it
reads as complete. Size tables for `expected rows + header + total`, then check the rendered row
count against the real one. At 1920x1080 budget roughly 28-30px per row.

## KPI Targets

Use prior-year measures as targets when available. If none exist, add the measure to the semantic model via Tabular Editor or by editing the TMDL files directly:

```
# In the relevant table's .tmdl file, add:
measure 'Measure 1YP' = CALCULATE([Measure], DATEADD('Date'[Date], -1, YEAR))
```

If no clear target exists, ask the user via `AskUserQuestion`.

## Inferring Time Granularity from Filter Context

When adding trend visuals, infer the appropriate time axis from active filters:

```yaml
Year (e.g. 2021):   Monthly    # Date.Calendar Month (ie Jan) or Date.Calendar Month Year (ie Jan 21)
Quarter:            Monthly or Weekly  # Date.Calendar Month or Date.Calendar Week EU (ie WK25)
Month:              Daily or Weekly    # Date.Date or Date.Calendar Week EU (ie WK25)
No date filter:     Monthly or Quarterly  # Date.Calendar Month Year or Date.Calendar Quarter Year
```

If unsure, default to monthly granularity -- it works well for most business reporting contexts.

## Title Hierarchy

Distribute meaning across the title hierarchy to avoid redundancy:

- **Page title** (textbox): The subject/metric (e.g., "Order Lines")
- **Visual titles**: Additional context that differentiates the visual (e.g., "by Key Account", "Monthly Trend", "Detail by Account")
- **Subtitles**: Almost always redundant -- hide by default when `--title` is set

Bad: Page title "Order Lines by Key Account" + visual title "Order Lines by Key Account" + subtitle "Order Lines by Key Account Name" -- says the same thing three times.

Good: Page title "Order Lines" + visual titles "by Key Account", "Monthly Trend", "On-Time Delivery" -- each adds unique information.

Hide subtitles explicitly:

```bash
pbir visuals subtitle "Report.Report/Page.Page/Visual.Visual" --no-show
```

Hide axis titles when the axis label is self-evident (e.g., month names on x-axis don't need a "Month" axis title). Hide category labels on cards when the visual title already describes the metric.
