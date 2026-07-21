---
name: date-table
version: 26.25
description: Drop a complete, ready-to-use date dimension into a PBIP semantic model -- an extended DimDate table (58 columns; calendar, ISO week, fiscal, and to-date flags) built by a bundled Power Query function, plus the "Dates Selected" DAX measure that renders the current date selection as a report title. Automatically invoke when the user asks to "add a date table", "add a calendar table", "create DimDate", "set up a date dimension", "add my standard date table", "mark as date table", "add a fiscal calendar", or wants a title measure showing the selected date period.
---

# Date table

Adds a fully-formed date dimension to a Power BI Project (PBIP) semantic model, plus the
companion measure that turns the current date selection into a readable report title
(`Selected Period: Jan - Mar 2024`).

The assets are TMDL, so this works on a PBIP folder on disk with no Power BI Desktop,
Tabular Editor, or network access required.

## Attribution

The two substantial pieces of code here are community work, redistributed with credit.
Keep the attribution headers in the TMDL when you copy these assets anywhere.

| Asset | Author | Source |
|---|---|---|
| `FunctionDateTable` (Extended Date Table M function) | Melissa de Korte | [Enterprise DNA forum](https://forum.enterprisedna.co/t/extended-date-table-power-query-m-function/6390) · [gist](https://gist.github.com/m-dekorte/12b53faee9cc1a616fa23f15b1b4a173) · taken from [Brian Julius's mirror](https://gist.github.com/bjulius/24533d0a6eb4110fcebbb3c19e70ae44) |
| `Dates Selected` measure | Rick de Groot / Datahub | [Showing period selections in Power BI](https://datahub.nl/showing-period-selections-in-power-bi/) |

Neither is published under an explicit licence; both were shared freely by their authors.
The column renames, added columns, and removed ISO columns in the bundled version are
local modifications -- see `references/column-reference.md`.

## What gets added

| File | Contents |
|---|---|
| `definition/tables/DimDate.tmdl` | The date table: 58 columns, sort-by columns and format strings already set, plumbing columns tucked into a `zOther` display folder |
| `definition/expressions.tmdl` | `FunctionDateTable`, the M function that generates the rows |
| `definition/tables/Measure Table.tmdl` | The `Dates Selected` measure (table created if it does not exist) |
| `definition/model.tmdl` | `ref table` entries and the `PBI_QueryOrder` annotation |

Optional helper expressions (`--include-helpers`): `Year_Variable` (current year + 2) and
`TodayDate`.

## Workflow

### 1. Find the model

Ask for the PBIP path if it is not obvious from context. The script accepts the
`.SemanticModel` folder, its `definition` folder, the `.pbip` file, or the project root.

**Before writing anything, check Power BI Desktop does not have the project open** --
run `pbir desktop list`. If it does, tell the user to close it first; Desktop holds file
locks and will overwrite disk changes from its in-memory copy.

### 2. Confirm the calendar parameters

Do not guess these. Ask with `AskUserQuestion` unless the user already said:

- **Date range.** Default `--start 2021-01-01`. For the end, either a fixed
  `--end yyyy-mm-dd` (defaults to 31 Dec of the current year + 2) or `--dynamic-end`,
  which ends at 31 Dec of `Year_Variable` so the table extends itself every year without
  an edit. `--dynamic-end` adds the helper expressions automatically.
  The range must cover every date in every fact table, with no gaps.
- **Fiscal year start month.** Default `7` (July -- Australian/NZ convention).
  Use `1` for a calendar fiscal year, `4` for UK, `10` for US federal.
- **Week start.** `--week-start 1` (default) numbers Monday as 1; `0` numbers Sunday as 0.

### 3. Run the script

```bash
python scripts/add_date_table.py --model "<path to project>" --dry-run
python scripts/add_date_table.py --model "<path to project>" --fy-start-month 7 --dynamic-end
```

Useful flags:

| Flag | Effect |
|---|---|
| `--table-name` | Name the table something other than `DimDate` (the measure's DAX is rewritten to match) |
| `--measure-table` | Put `Dates Selected` in an existing measure table instead of creating `Measure Table` |
| `--no-measure` | Date table only |
| `--mark-as-date-table` | Sets `dataCategory: Time` on the table and `isKey` on `[Date]` |
| `--include-helpers` | Also add `Year_Variable` and `TodayDate` |
| `--holidays` | An M list expression, e.g. `"PublicHolidays[Date]"`, to populate `IsHoliday` / `IsBusinessDay` / `Day Type` |
| `--dry-run` | Report what would change, write nothing |

The script is idempotent -- re-running it reports what is already present and leaves it
alone. Every `lineageTag` in the injected TMDL is regenerated, so the same assets can go
into any number of models without collisions.

### 4. Wire it up

The script does not create relationships -- it cannot know your fact tables. After it runs:

1. Add relationships from each fact table's date column to `DimDate[Date]`, single
   direction, many-to-one. Edit `definition/relationships.tmdl` directly (see the
   `pbip:tmdl` skill) or let the user do it in Desktop.
2. Consider `--mark-as-date-table`. It is off by default because it is only correct once
   `[Date]` is genuinely unique and contiguous, and because it disables Power BI's
   auto date/time hierarchies for that column. Turn it on if the user wants DAX time
   intelligence (`DATESYTD`, `DATEADD`) to work against this table.
3. Hide `DimDate[Date]` from report view only if a friendlier column is exposed --
   report authors usually still need it for the axis.

### 5. Verify

```bash
python ../../../pbip/skills/pbip/scripts/validate_pbip.py "<path to .pbip>"
```

Then have the user open the project in Power BI Desktop and refresh `DimDate`. The M
function runs entirely in memory -- there is no data source to authorize, so the refresh
should succeed with no credential prompt.

If `--dynamic-end` was used, confirm `Year_Variable` refreshes before `DimDate`; the
`PBI_QueryOrder` annotation the script writes puts it in the right order.

## The `Dates Selected` measure

Returns a string describing whatever the date slicers currently select:

| Selection | Returns |
|---|---|
| Complete years | `Selected Period: 2023 - 2025` |
| Non-adjacent years | `Selected Period: 2021 \| 2024` |
| Complete months in one year | `Selected Period: Jan - Mar` |
| Complete months across years | `Selected Period: Nov 2023 - Feb 2024` |
| A single day | `Selected Period: 14 Mar 2024` |
| A partial, non-contiguous range | `Selected Period: a range of dates in Mar 2024` |
| Nothing resolvable | `Selected Period: See Date Slicers` |

Drop it in a card visual at the top of a page. Two strings near the top of the DAX are
meant to be edited: `__PeriodPrefix` (default `"Selected Period: "`) and `__DiverseDates`
(default `"a range of dates in "`).

**It is coupled to the bundled DimDate.** It reads `[Date]`, `[Year]`, `[Start Of Month]`,
`[Days in Year]` and `[Days In Month]`. If you point it at a different date table, add
those columns first or rewrite the references.

## Gotchas

- **`IsHoliday` is the string `"Unknown"`, not a boolean**, unless a holiday list was
  passed via `--holidays`. `IsBusinessDay` still works (it tests `<> true`), but do not
  write DAX assuming `IsHoliday` is boolean.
- **The ISO columns are gone.** The bundled function removes `ISO Year`,
  `ISO Weeknumber` and friends in its last step; the `Week & Year` / `WeeknYear` columns
  carry the ISO logic instead. Do not reintroduce a newer upstream copy of the function
  without re-applying the local modifications -- `Dates Selected` will break.
- **`FQuarternYear` and `FPeriodnYear` are `double`, not `int64`.** Harmless as sort keys,
  but they show a general number format if you drag them onto a visual.
- **`Month Initial` and `Weekday Initial` contain zero-width spaces** (U+200B) as padding
  so the twelve month initials stay distinct values. String comparisons against them
  will not match a plain `"J"`.
- **Do not hand-edit the M function's indentation.** It lives inside a TMDL triple-backtick
  block where indentation is significant; a reflowed line breaks Desktop's file open.
  See `~/.claude/rules/tmdl-pbir-authoring.md`.

## Reference

- `references/column-reference.md` -- all 58 columns, grouped, with the local
  modifications vs. upstream listed at the end.
- `assets/` -- the raw TMDL fragments, if you want to paste rather than run the script.
