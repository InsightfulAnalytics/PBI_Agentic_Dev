# Odd Rows P&L scaling probes

Thirteen scratch queries that isolate *where the time goes* in a 13-row x 14-column P&L.
Run them with `scripts\time_query.ps1 -QueryFile scripts\demo\scaling\<file>.dax`.
They are diagnostics, not shipped benchmarks: the shipped ones are `..\demo_odd_rows_*.dax`.

Measured 2026-08-24, one session, Year 2026 pinned, ~40M-row fact table.

| Probe | What it isolates | Cells | Cold | Warm |
|---|---|---|---|---|
| `probe_1col_nocg` | one bridge filter, no calc group | 1 | 148 ms | **4 ms** |
| `probe_grouped_nocg` | bridge GROUPED, no calc group | 27 | 140 ms | **4 ms** |
| `probe_flat` | 13 copies of the bare base measure x 14 calc items | 182 | 205 ms | **52 ms** |
| `floor_query` | 14 calc-group columns, no row dispatch at all | 13x14 | 177 ms | **29 ms** |
| `floor_bridge_query` | bridge GROUPED x 14 calc items | 27x14 | 237 ms | **48 ms** |
| `probe_1col` | ONE bridge-filtering column x 14 calc items | 14 | 222 ms | 65 ms |
| `probe_5distinct` | 5 distinct bridge filters x 14 calc items | 70 | 598 ms | 320 ms |
| `probe_5rows` | the 5 real account-backed NM measures | 70 | 635 ms | 345 ms |
| `probe_depth1` | 13 **identical** bridge filters x 14 calc items | 182 | 900 ms | 800 ms |
| `probe_8rows` | the 8 ratio / DISTINCTCOUNT NM measures | 112 | 1,198 ms | 770 ms |
| `probe_g2` | grouped axis, 5 lines x 14 items, counts inline | 70 | 727 ms | 165 ms |
| `probe_g3` | grouped axis, amounts only | 70 | 260 ms | 77 ms |
| `probe_g3counts` | the two DISTINCTCOUNTs alone | 14 | 203 ms | 43 ms |

## What they prove

**1. Cost is linear in the number of measure COLUMNS, at ~62 ms per column.**
`probe_1col` 65 ms -> `probe_5distinct` 320 ms -> `probe_depth1` 800 ms is 1 : 5 : 13,
almost exactly. The engine does **not** dedupe: `probe_depth1`'s 13 columns are byte-identical
and still cost 13x. Whether the row is dispatched by SWITCH, by a field parameter, or by an
explicit measure is close to irrelevant: what costs is how many independent measure
expressions the query carries.

**2. Grouping a column is ~free; filtering it is not.**
`floor_bridge_query` puts the bridge on the GROUP BY axis: 378 cells in 48 ms.
`probe_depth1` filters the same bridge column inside CALCULATE: 182 cells in 800 ms.
Half the cells, **17x slower**. Grouped, the storage engine runs one scan per calc item and
buckets by Line. Filtered, it runs one scan per cell.

**3. The calculation-group column axis is nearly free** : `probe_flat` renders 182 cells of a
trivial measure in 52 ms. The 14 column variants are not the problem, and never were.

**4. Therefore the only real lever is getting statement rows onto a grouped axis.**
That is what `..\demo_odd_rows_deneb_query.dax` does, and why it lands at 36 ms warm
against page 6's 1,110 ms.
