# CALCULATE, Performance, and the Optimisation Skill

Where `CALCULATE` fits in a codebase whose default is explicit `FILTER` + X-aggregators, and
how this skill hands off to `semantic-models:dax-optimisation`.

## What CALCULATE actually is

Microsoft classifies `CALCULATE` as a **filter function**. It evaluates an expression under a
modified filter context: `CALCULATE( <expr>, <filter(s)> )`. That is to say — "filter
something, then calculate over it", which is precisely what the house pattern does explicitly
with `FILTER` and an X-aggregator. The engine also invokes CALCULATE implicitly behind every
measure reference (context transition). None of that is in dispute; the argument is only about
whether you should **write** it yourself by default.

## Why it is not the default here

1. **Rules that have to be memorised rather than read.** With nested CALCULATEs the
   **innermost** filter overrides the outer — not intersect, not blank. `KEEPFILTERS` changes
   that to an intersection. Nothing in the code says so.
2. **A mini-language of filter modifiers** — `REMOVEFILTERS`, `ALL`, `ALLEXCEPT`,
   `ALLNOBLANKROW`, `KEEPFILTERS`, `USERELATIONSHIP`, `CROSSFILTER` — most of them usable
   *only* inside CALCULATE, with combinatorially many interactions.
3. **It cannot be stepped through.** Nested CALCULATEs cannot be split into separate steps
   without changing the result, so there is no way to watch what one does. The house pattern
   debugs by swapping the `RETURN` (see [`method.md`](method.md) §6). This is the reason that
   actually matters day to day.

## When CALCULATE *is* the right call

There is no prize for avoiding it. Reasonable uses:

- **Time intelligence.** The standing exception — over a properly formed date table, write
  `CALCULATE ( [Base], DATEADD ( DimDate[Date], -1, YEAR ) )` and `DATESYTD`. See
  [`../SKILL.md`](../SKILL.md) and [`dates-and-time.md`](dates-and-time.md).
- **A correct base measure that needs one simple, modified context.**
  `CALCULATE( [Base], <one column predicate> )` beats copying a block of DAX and re-editing it.
- **A modifier interaction you actually understand** and can explain in the measure's comment.
- **A profiled rewrite that measurably wins.** Rare, but real — and it is evidence, not taste.
- **As step 3 of the house pattern**, when the thing being reduced is an existing measure or a
  non-additive aggregation. `CALCULATE( [Measure], __Table )` is both more correct and usually
  faster than `SUMX( __Table, [Measure] )`, which context-transitions per row and then *adds* the
  results — meaningless for a ratio, double-counting for a `DISTINCTCOUNT`. This does not make
  CALCULATE the default terminator: computed columns and row-level expressions cannot move into
  it at all. See [Step 3 is not always an X-aggregator](../SKILL.md#step-3-is-not-always-an-x-aggregator)
  for the full decision table and the `KEEPFILTERS` guard.

Rule of thumb: **a single, simple column predicate over a base measure** is the safe and
readable use. Stacked filter modifiers are where it stops being readable.

## Performance: readability is not the trade

Written well, the two forms usually compile to the same query plan — the formula engine only
needs the DAX to lead it toward a good plan, and two differently-written measures frequently
arrive at the same one. Readability and debuggability are therefore a free choice in the
typical case, not something paid for in speed.

"Usually" is not "always". Some measures need restructuring to get a good plan no matter which
style they are written in. That is a profiling finding, and it is the moment to hand off to
`semantic-models:dax-optimisation` — not a reason to pre-emptively write something harder to
read.

## The FE/SE model (shared vocabulary with the optimisation skill)

- **Storage Engine (SE)** — VertiPaq, columnar, multi-threaded C++. Scans columns (not rows),
  applies filters, does basic `SUM`/`COUNT`/`MIN`/`MAX`. Fast. **Push work here.**
- **Formula Engine (FE)** — single-threaded .NET. Parses DAX, manages context and context
  transition, calls the SE via internal **xmSQL**, and handles the row-by-row work
  (`FILTER`, `ADDCOLUMNS`, iterators) the SE cannot take. Slower.
- Optimization ≈ **rewrite so more work lands in the SE and less in the FE.**

Tools: **Performance Analyzer** (built in — watch the *DAX query* time), **DAX Studio**
(server timings, query plans, xmSQL), **DAX query view** with `EVALUATEANDLOG`, and
best-practice linters. The optimisation skill covers trace capture in depth; in this
environment prefer `te query` or `pbi-desktop:connect-pbid` over manual tooling.

## Debugging toolbox

- **Peel the measure apart with VARs** and swap the `RETURN` — the core technique.
- **`TOCSV`** to view an intermediate table in a visual; **`EVALUATEANDLOG`** to log it.
- **Handle errors** with `DIVIDE( …, …, BLANK() )`, `IFERROR`, `ISBLANK`, and the knowledge
  that `0 = BLANK()` is true while `0 == BLANK()` is false.
- **Circular dependencies** usually come from calculated columns referencing each other, or
  measures pulled into column context — break the chain or move the logic into a measure.
- **Inspect the filter context** by returning what is in scope:
  `CONCATENATEX( VALUES( Dim[Col] ), Dim[Col], ", " )`.
- **Validate against real data before trusting the number** — run it with
  `pbi-desktop:connect-pbid` or `te query` rather than eyeballing the DAX.

---

## Reconciliation: this skill ↔ `semantic-models:dax-optimisation` (perf skill)

Both touch DAX, take **opposite default stances on CALCULATE**, and must not undercut each
other. They have different jobs:

| | **dax-standard** (this skill) | **semantic-models:dax-optimisation** (perf skill) |
|---|---|---|
| Goal | *Write* readable, debuggable measures | *Tune* slow/existing measures |
| Default | Avoid CALCULATE; FILTER + X-aggregators + VARs | CALCULATE/CALCULATETABLE/context-transition as tools |
| Trigger | "write a measure", "rewrite this measure", "make this readable" | "optimize DAX", "slow query", "server timings" |
| Catalog | The pattern, the house style, and worked recipes | Tiered perf patterns DAX001–DAX021, QRY001–QRY004, model/Direct-Lake |

**How to use them together (no conflict):**

1. **Author table-first.** Default to this skill for any *new* measure.
2. **Only optimize what's measurably slow.** Don't pre-optimize. If a measure is fine, leave
   it readable.
3. **When profiling says it's slow**, switch to the perf skill. Its CALCULATE-based patterns
   (e.g. *DAX001* simple column predicates as CALCULATE args, *DAX005* push SUMMARIZE inputs
   into CALCULATETABLE, *DAX008* context transition in iterators, *DAX010* CALCULATETABLE
   table filters) are legitimate, targeted optimizations — **not** a contradiction of the
   house style, just a different objective (best query plan, over best readability).
4. **Keep the readable version.** When a CALCULATE rewrite wins on timings, retain the
   readable version in a comment so the intent stays legible.
5. **Shared ground both agree on:** push work to the SE; cache repeated tables/expressions in
   VARs; set the right grain; keep iterators SE-friendly; filter on precomputed integer/
   boolean columns. The house pattern lands on most of these already.

Net: **authoring = this skill; performance tuning = the perf skill.** The CALCULATE
"disagreement" is a difference of *purpose*, and the two compose cleanly when you author for
clarity and optimize only on evidence.
