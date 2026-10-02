---
name: dax-optimisation
version: 26.26
description: DAX performance optimization for semantic models. Automatically invoke when the user asks to "optimize DAX", "fix slow DAX", "DAX performance", "tune a measure", "debug a measure", "DAX anti-patterns", or mentions slow queries, server timings, or a visual that is slower than its DAX query.
---

# DAX Optimisation

Skills and references for writing, debugging, and optimizing DAX in semantic models.

## Optimization

For systematic DAX query performance optimization, read the workflow reference first:

**[`references/dax-performance-optimization.md`](./references/dax-performance-optimization.md)** — Tiered framework (4 tiers), phased workflow, decision guide, and error handling.

Detailed reference files (progressive disclosure — consult as directed by the workflow):

- **[`references/engine-internals.md`](./references/engine-internals.md)** — FE/SE architecture, xmSQL, compression/segments, SE fusion, trace diagnostics
- **[`references/dax-patterns.md`](./references/dax-patterns.md)** — Tier 1 DAX patterns (DAX001–DAX021) + Tier 2 query structure (QRY001–QRY004)
- **[`references/model-optimization.md`](./references/model-optimization.md)** — Tier 3 model patterns (MDL001–MDL009) + Tier 4 Direct Lake (DL001–DL002)

Trace capture and performance profiling:

- **Local models (Power BI Desktop):** Use the Tabular Editor CLI `te query` (see the [`te-cli` skill](../../../tabular-editor/skills/te-cli/)) first; as an alternative, the [`connect-pbid` skill](../../../pbi-desktop/skills/connect-pbid/) covers FE/SE timing (`performance-profiling.md`) and intermediate result inspection (`evaluateandlog-debugging.md`).
- **Remote models (Fabric Service / XMLA):** Run DAX with the Tabular Editor CLI `te query` (`-s <workspace> -d <model>`) against the workspace XMLA endpoint; see the [`te-cli` skill](../../../tabular-editor/skills/te-cli/) (tabular-editor plugin).
- **Power BI Modeling MCP:** also available for trace and query if you prefer an MCP tool; reach for it after the options above.

**Measure before rewriting.** On a 2026 Desktop engine, every classic Tier 1 rewrite on one large P&L
model was measured as performance-neutral although textbook anti-patterns were present: whole-table
`FILTER` arguments converted to `KEEPFILTERS` column predicates (187 sites), repeated sub-expressions
cached in iterators, multi-scan base measures collapsed, iterator domains restricted. Every rewrite
was result-identical and inside the timing noise; the engine already deduplicates repeated
sub-expressions and handles small dimension filters cheaply. So:

1. Benchmark first, per visual: rebuild each visual's query from its PBIR, override the measure under
   test with `DEFINE MEASURE` (A against B in one query file, the model untouched), clear the cache,
   trace cold and warm.
2. Check the storage side before touching DAX (`pbi-desktop:connect-pbid`
   `references/vertipaq-stats.md`). Auto date/time tables are the usual big win: one sentinel date
   such as 9999-12-31 in a date column builds a calendar to the year 9999. Deleting two such tables,
   two dead fact columns and a dead date column took one model from 967 MB to 348 MB.
3. Do not promise a win from pattern-matching an anti-pattern. When the cost is per cell (deep
   measure chains times matrix cells), rewrites inside the chain do not touch it; see
   `custom-visuals:performant-matrix`.

Every capture route above times the DAX query. None of them evaluate a dynamic format string, which a rendered visual pays once per cell, so a visual can cost materially more than the query the harness measures. See [`references/dax-performance-optimization.md`](./references/dax-performance-optimization.md), Trace Capture Methods.

## Related Skills

- [`dax-standard`](../dax-standard/) — Authoring measures in the house style; the default for any *new* measure (this skill is for tuning existing ones)
- [`semantic-model`](../semantic-model/) — Model design, build, and auditing including DAX anti-patterns and best practices
- [`connect-pbid` (pbi-desktop plugin)](../../../pbi-desktop/skills/connect-pbid/) — Trace capture, performance profiling, EVALUATEANDLOG debugging
- [`lineage-analysis`](../lineage-analysis/) — Impact analysis before model changes
