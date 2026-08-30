# PL Switch Lab

A purpose-built Power BI lab where one financial statement is implemented nine different ways over
the same 74,876,172-row fact table. Each build renders the same numbers, tied out cell for cell,
so the only thing that varies between them is the technique: `SWITCH` dispatch, a physical bridge
table, a field parameter, one calculation group, two calculation groups, or a Deneb grid. All nine
were measured in Performance Analyzer on the same machine on the same afternoon under one protocol,
and the results are the whole point of the repository.

The method these builds exist to prove is written up in [`docs/performance/`](docs/performance/).
This file is about getting the report open on your own machine.

## Results

Fact table 74,876,172 rows. Power BI Desktop 2.157.879.0 (26.08). Measured 2026-08-28. Cold is
after an XMLA `ClearCache`; warm is the immediately following `Refresh visuals`. These are the
statement visual only, not the page total.

| # | Page | Technique | Visual | Cold | Warm |
|---|---|---|---|---|---|
| 1 | P&L Accounts SWITCH | `SWITCH` over a disconnected row table | `tableEx` | **4,815 ms** | **4,594 ms** |
| 2 | P&L Accounts Fast Bridge | physical bridge table + relationship | `tableEx` | **348 ms** | **319 ms** |
| 3 | P&L Accounts Deneb | Deneb grid, 6 base measures | Deneb | **294 ms** | **160 ms** |
| 4 | Odd Rows P&L | field parameter rows x calculation group columns | `pivotTable` | **6,317 ms** | **5,634 ms** |
| 5 | Odd Rows P&L - SWITCH | `SWITCH` rows x 14 shipped measures | `tableEx` | **1,680 ms** | **1,303 ms** |
| 6 | Odd Rows P&L - 2 Calc Groups | calculation group on rows AND columns | `pivotTable` | **7,530 ms** | **7,238 ms** |
| 7 | Odd Rows P&L - Deneb | Deneb grid, 10 base measures | Deneb | **419 ms** | **318 ms** |
| 8 | Monthly P&L - Calc Group | 15-item calculation group x 28 measures | `pivotTable` | **12,412 ms** | **11,823 ms** |
| 9 | Monthly P&L - Deneb | Deneb grid, 12 rows x 10 measures | Deneb | **332 ms** | **170 ms** |

Three comparisons come out of that table, and only one of them is the obvious one.

**Pages 1-3, rows that are a set of accounts.** The bridge table is 13.8x cold and 14.4x warm
against `SWITCH`, and it is still a native `tableEx`. Deneb is 294 ms against the bridge's 348 ms.
The bridge wins on effort, not on time: it keeps native sort, drill and export, and it is a one-off
model change every future visual inherits.

**Pages 4-7, rows that are not a set of accounts.** Eight of the thirteen rows are ratios, per-unit
metrics and a distinct count, so no set of accounts produces them and the bridge is unavailable.
Here the counter-intuitive result: replacing the 13-branch `SWITCH` with a second calculation group
on the rows took the same 182 cells from 1,680 ms to 7,530 ms, 4.5x **worse**. Cost is
instantiation count, not branch count.

**Pages 8-9, the monthly matrix.** 12,412 ms to 332 ms, 37.4x cold and 69.5x warm. The DAX query
behind the slow page costs 2,178 ms cold. The other 10,234 ms is per-cell format strings and
render, and no `EVALUATE` will ever show it to you: 82% of that visual's cost is invisible to a
DAX benchmark.

Full protocol, the page chrome breakdown and the caveats are in
[`docs/performance/08-measured-results.md`](docs/performance/08-measured-results.md).

## Quick start

The data is not in this repository. You generate it, then you **set the `DataFolder` parameter in
the model to point at it**. If you skip that one step, Refresh fails immediately with
`DataSource.Error` and nothing in the report will ever show a number. It is the only step people
miss, so it is repeated below as step 4.

```bash
git clone <repo-url>
cd "PL Switch Lab"
pip install -r requirements.txt
python scripts/demo/generate_demo_data.py
```

**1. Clone somewhere short.** A PBIP is a deep folder tree and Windows still enforces a 260
character path limit. Clone to something like `C:\lab\PL Switch Lab`, not four levels down inside
`Documents`. When this bites, files go missing silently rather than erroring.

**2. Install the two dependencies.** `numpy` and `pyarrow`, nothing else. See
[Requirements](#requirements) for the versions this was verified on.

**3. Generate the data.** `python scripts/demo/generate_demo_data.py` takes about 29 seconds and
writes about 314 MB into `data/demo/`. Have the disk space free before you start. It prints a
row count per month, then a full-company P&L sanity table, then a `pl_lines.csv` round-trip
self-check. The expected row count is 74,876,172, which is what every number above was
measured against; the script warns if it lands outside 70-80M.

**4. Open `PL Bridge Demo.pbip` and set the `DataFolder` parameter.** Home ribbon, Transform data,
Edit parameters (or Transform data, Data source settings). Set it to the absolute path of the
`data/demo` folder the generator just wrote, with no trailing backslash, for example
`C:\lab\PL Switch Lab\data\demo`. Five table partitions read from it.

If you would rather not use the ribbon, or you are scripting the install, the parameter is a
plain literal on one line of `PL Bridge Demo.SemanticModel/definition/expressions.tmdl`:

```
expression DataFolder = "C:\lab\PL Switch Lab\data\demo" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]
```

Edit that string before you first open the project. Save as UTF-8 with no byte order mark, as the
[Known limits](#known-limits) section warns.

**5. Refresh.** Every visual will be blank on first open, with a banner reading *"Some of the
tables have incomplete or no data"*. That is expected and correct: a PBIP with no cached data
opens with the full model definition and no rows in it. Hit Refresh. You may get a privacy level
prompt for the local folder the first time.

If you are scripting the install, the refresh can be driven headlessly against the local engine
instead of through the ribbon. Discover the Analysis Services port the way
[`docs/performance/tools/run_dax.ps1`](docs/performance/tools/run_dax.ps1) does, then:

```powershell
Add-Type -Path "C:\Program Files\DAX Studio\bin\Microsoft.AnalysisServices.Tabular.dll"
$srv = New-Object Microsoft.AnalysisServices.Tabular.Server
$srv.Connect("Data Source=localhost:$port")
$srv.Databases[0].Model.RequestRefresh('Full')
$srv.Databases[0].Model.SaveChanges()
```

That populated all 15 partitions in 92 seconds here, with no privacy level prompt. Use the DAX
Studio copy of the DLL as shown: the Tabular Editor 3 copy is .NET 8 and will not load under
Windows PowerShell 5.1.

Then start on page 1 and work left to right. Pages 1 and 2 are the same statement, and the
difference between them is the entire argument.

## Why the data is not in the repository

`data/demo/financials.parquet` is 314,445,742 bytes. GitHub rejects any file over 100 MB, so it
cannot be committed at all, and Git LFS would bill this account for every stranger's clone.

The generator is deterministic instead. `SEED = 42`, a fixed draw order, and `numpy` plus `pyarrow`
as the only dependencies: running it on another machine reproduces the same bytes, not merely
similar data. `financials.parquet` has MD5 `190bc0c70a910fdbbf3680d67fabf35b`, and if yours
matches, you are measuring the same model that produced the table above.

One honest caveat on that: byte-for-byte reproducibility rests on NumPy keeping its PCG64 random
stream compatible across versions. That guarantee has held, but nothing in this repository asserts
it, so a future NumPy could quietly change the data underneath the published numbers. If the MD5
does not match, the report will still work; only the exact figures become yours rather than mine.

## Reproducing the measurements

Reproducing the results table needs all five of these, because each one moved a result by more
than the differences being reported:

1. **Performance Analyzer, `Refresh visuals`.** Not a page click. Revisiting a page can serve from
   the report canvas cache and log a misleading 0 ms.
2. **`YEAR = 2026` selected, MONTH / CHANNEL / CATEGORY all clear, on every page.** Read the
   warning below before you do anything else.
3. **`ClearCache` over XMLA before each page**, so run 1 is genuinely cold rather than warmed by
   whatever the previous page touched.
4. **Two runs per page**, cold then warm, with the Performance Analyzer log cleared between them.
5. **One visual read per page**, the statement itself. On the fast pages the slicers and textboxes
   are most of the page total, so quoting a page total flatters the slow pages.

**The slicer warning, which is the thing that will get you.** The four rail slicers are cloned per
page, not synced. Nothing propagates a selection from one page to the next, and nothing tells you
they disagree. A stray `MONTH = Jun` left on one page compares a twelfth of the data against all
of it, and the comparison is then worthless while still looking entirely plausible. This is not
hypothetical: it is the difference between the 9,133 ms this document set used to quote for the
monthly matrix and the 12,412 ms it quotes now. Set the rail page by page and verify it before
every run.

`scripts/demo/pa_sweep.ps1` automates the whole sequence. It drives Power BI Desktop through UI
Automation, normalises the rail on each page, clears the engine cache, runs cold then warm, reads
the durations back out of the Performance Analyzer pane and writes one CSV row per visual per run.
Desktop must already be open on this project.

```powershell
.\scripts\demo\pa_sweep.ps1 `
  -Pages 'P&L Accounts SWITCH','P&L Accounts Fast Bridge','P&L Accounts Deneb' `
  -ClearCache -OutCsv .\pa_results.csv
```

For query-level rather than visual-level timing,
[`docs/performance/tools/run_dax.ps1`](docs/performance/tools/run_dax.ps1) times a `.dax` file
against the open model over ADOMD and reports cold and warm. The `.dax` files behind each page
live in `scripts/demo/`.

## What is in the repository

```
PL Bridge Demo.pbip               the project file: this is what you open
PL Bridge Demo.SemanticModel/     model definition in TMDL
  definition/tables/              15 tables, including the three calculation groups
  definition/functions.tmdl       DAX user-defined functions (format string helpers)
  definition/expressions.tmdl     the DataFolder parameter lives here
PL Bridge Demo.Report/            report definition in PBIR
  definition/pages/               the nine pages, one folder each
docs/performance/                 the method, eight documents
  README.md                       start here: the three costs and the evidence status
  01-diagnosing-slow-matrices.md  separating the three costs with a subtraction
  02-bridge-method.md             the structural model fix, and when it does not apply
  03-format-string-and-cf-tax.md  the per-cell costs a DAX benchmark cannot see
  04-deneb-grid-template.md       the grid implementation spec
  05, 07                          two case studies and the lab reproduction
  06-pbir-build-playbook.md       operational rules for editing report files safely
  08-measured-results.md          all nine pages under one protocol: the table to quote
  tools/                          run_dax.ps1 and render_local.mjs, self-contained
scripts/demo/                     the data generator, the page builders, the DAX probes,
                                  pa_sweep.ps1 and validate_model.ps1
scripts/demo/deneb/               the three Deneb grid specs and their offline renderers
scripts/demo/scaling/             the isolation probes behind the scan-count finding
design/                           report chrome: logo, side panel SVGs, layout scripts
DEMO-SPEC.md                      the specification the model and the data were built from
data/                             empty until you run the generator; ignored by git
```

## Requirements

- **Windows.** Power BI Desktop is Windows only, and `pa_sweep.ps1` drives it through Windows UI
  Automation. Nothing here runs on macOS or Linux.
- **Power BI Desktop 26.08 or later.** The model ships DAX user-defined functions in
  `definition/functions.tmdl` and sits at compatibility level 1702. UDF support arrived in 26.06;
  everything here was built and measured on 2.157.879.0 (26.08). An older Desktop will not open the
  model.
- **Python 3, with `numpy` and `pyarrow`.** Verified on Python 3.14.6, numpy 2.4.6, pyarrow 25.0.0.
  Nothing else is imported.
- **About 314 MB of free disk for the generated data**, plus room for Power BI Desktop's own cache
  once you refresh. The compressed in-memory image of this model is another 269 MB.

## Known limits

**Your timings will not match mine, and should not.** Every number in this repository came off one
machine, in one session, on one model. They are a set of ratios measured under controlled
conditions, not a distribution across hardware. The ordering of the nine builds is the durable
finding; the absolute milliseconds are not.

**The base measures are the floor.** The fast builds remove row dispatch, per-cell format strings
and per-cell conditional formatting. They do not make `SUM` over 74.9M rows faster. On this model
that floor is 17 ms warm. On a model whose base measures cost 800 ms, 800 ms is what you get, and
no visual technique goes below it.

**This is not a claim that Deneb is always faster.** Page 2 is a native `tableEx` at 348 ms,
because the bridge removed the dispatch from the model rather than from the visual. When the
statement rows are a filterable set of accounts, fix the model and keep the native visual.

**If you edit the PBIR or TMDL files by hand, save as UTF-8 without a byte order mark.** A BOM on
`pages.json` makes Desktop open with an "Issues were found" dialog and an empty model, which reads
exactly like model corruption and is not. PowerShell 5.1's `Set-Content -Encoding utf8` writes a
BOM; use `utf8NoBOM` on PowerShell 7, or write from Python.

**Do not force-kill Power BI Desktop after a save.** The title bar drops its asterisk as soon as
the definition is written, but Desktop keeps streaming the data image to `.pbi\cache.abf` for tens
of seconds afterwards, and on a model this size that file is large. Killing it mid-write truncates
the cache and the next open fails with a decoder error. Close it gracefully. If it does happen,
delete `.pbi\cache.abf` and refresh again; the model definition is untouched.

## Licence

MIT. See [LICENSE](LICENSE).

This directory is licensed separately from the rest of the repository, which is GPL-3.0.

Two pieces of community code are redistributed inside the semantic model, and both carry
their attribution inline. Keep those headers if you copy the model elsewhere.

- **Extended Date Table (`fnDateTable` Power Query M function)**, in `expressions.tmdl`.
  Original author Melissa de Korte, published on the Enterprise DNA forum.
- **`Dates Selected` measure**, in `00_Measures.tmdl`. Rick de Groot, Datahub,
  "Showing period selections in Power BI".

Neither carries an explicit licence; both were published freely by their authors.

## Attribution

Built by Timothy Osborn. The method and the measurements are written up in
[`docs/performance/`](docs/performance/), and the accompanying article is linked from the
repository README.
