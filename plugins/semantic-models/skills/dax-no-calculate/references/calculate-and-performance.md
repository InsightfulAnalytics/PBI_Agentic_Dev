# CALCULATE, Performance, and Coexisting with the Perf Skill

From *DAX For Humans* Ch. 15 (Optimizing Performance) and Ch. 16 (AI, Debugging, and
CALCULATE) — plus the explicit reconciliation between this authoring skill and the
`semantic-models:dax` performance-optimization skill.

## What CALCULATE actually is

Microsoft itself classifies `CALCULATE` as a **filter function**. It evaluates an
expression under a modified filter context: `CALCULATE( <expr>, <filter(s)> )`. In other
words, it is shorthand for "filter something, then calculate over it" — exactly what the
No-CALCULATE pattern does explicitly with `FILTER` + an X-aggregator. CALCULATE *is used
by the engine* behind every measure (context transition); the book's argument is only that
you rarely need to **write** it yourself.

## Why the book argues against writing CALCULATE

1. **Arbitrary rules.** Nested CALCULATEs: the **innermost** filter overrides the outer (not
   intersect, not mutually-exclusive blank). `KEEPFILTERS` changes that to an intersection.
   These rules must simply be memorized.
2. **A mini-language of filter modifiers** — `REMOVEFILTERS`, `ALL`, `ALLEXCEPT`,
   `ALLNOBLANKROW`, `KEEPFILTERS`, `USERELATIONSHIP`, `CROSSFILTER` — most usable *only*
   inside CALCULATE, with combinatorially many interactions.
3. **Impenetrable to debug.** You can't split nested CALCULATEs into separate steps without
   changing the result, so there's no native way to watch what it does. The No-CALCULATE
   pattern, by contrast, debugs by swapping the `RETURN` (see [`method.md`](method.md) §6).

## When CALCULATE *is* worth using

The book is not dogmatic ("there is no No-CALCULATE police"). Reasonable uses:

- You already have a correct **base measure** and just need it in a **slightly modified
  context** — `CALCULATE( [Base], <one simple filter> )` avoids copying and re-editing a
  block of DAX.
- You genuinely understand the filter-modifier interaction you need.
- A profiled rewrite shows a CALCULATE form generates a materially better query plan (rare,
  but it happens — see below).

Rule of thumb: **simple, single, column-predicate filters** on a base measure are the safe,
readable use of CALCULATE. Stacked filter modifiers are where it gets "wonky."

## The performance claim

The book reports experiments (including reconstructing other developers' measures, tested up
to 20M rows) finding **no statistically significant performance difference** between
No-CALCULATE and CALCULATE versions. The reason: the **Formula Engine** only needs your DAX
to lead it toward a good query plan; two differently-written measures can compile to the
*same* plan. So readability/debuggability is a free choice, not a performance sacrifice —
*in the typical case*.

## The FE/SE model (shared vocabulary with the perf skill)

- **Storage Engine (SE)** — VertiPaq columnar, multi-threaded C++. Scans columns (not rows),
  applies filters, does basic `SUM/COUNT/MIN/MAX`. Fast. **Push work here.**
- **Formula Engine (FE)** — single-threaded .NET. Parses DAX, manages context/context
  transition, calls the SE via internal **xmSQL**, and handles row-by-row work (`FILTER`,
  `ADDCOLUMNS`, iterators) the SE can't delegate. Slower.
- Optimization ≈ **rewrite so more work happens in the SE and less in the FE.**

Tools: **Performance Analyzer** (built-in; watch the *DAX query* time), **DAX Studio** (server
timings, query plans, xmSQL), **DAX query view** + **`EVALUATEANDLOG`**, and best-practice
linters. (The perf skill covers trace capture in depth.)

Note the nuance the book itself shows: No-CALCULATE is usually equal, but **not magic** — its
Ch. 15 examples include cases where simple measures need restructuring to get a good plan
(sometimes the FE can't find an optimal plan regardless of CALCULATE-or-not). That's exactly
when you hand off to the perf skill.

## Using AI to write DAX (Ch. 16)

The book's high-accuracy workflow (credited to patron Brian Julius): **give the chatbot your
model's structure**, not just a prose prompt.

1. Export the model definition — a **BIM** file (via Power BI **Project (.pbip)** save → the
   `model.bim` inside `*.SemanticModel`, or via **Tabular Editor 2** `File ▸ Save As`).
   Optionally trim bloat (linguistic metadata) to cut ~80% of size.
2. Provide the BIM as context and describe the visual (axes/legend) and the exact metric
   semantics.
3. **Iterate** — the book's worked example goes from a reasonable-but-wrong answer to correct
   in two turns by clarifying the rule (e.g. "active = Start ≤ hour AND End > hour").
4. A human still validates business logic and context.

(In *this* environment, prefer running/validating generated DAX against the live model with
the `pbi-desktop:connect-pbid` skill and `EVALUATEANDLOG`, rather than copy-paste.)

## Debugging toolbox (Ch. 16)

- **Peel apart with VARs** and swap the `RETURN` (the core technique).
- **`TOCSV`** to view intermediate tables; **`EVALUATEANDLOG`** to log them.
- **Handle errors** with `DIVIDE(…, …, BLANK())`, `IFERROR`, `ISBLANK`, and the `0 = BLANK()`
  knowledge.
- **Circular dependencies** — usually from calculated columns referencing each other or
  measures pulled into column context; break the chain or move logic to a measure.
- **Inspect the filter context** — return what's in scope (`CONCATENATEX( VALUES(col), … )`)
  to see what the engine thinks is filtered.

---

## Reconciliation: this skill ↔ `semantic-models:dax` (perf skill)

Both touch DAX, take **opposite default stances on CALCULATE**, and must not undercut each
other. They have different jobs:

| | **dax-no-calculate** (this skill) | **semantic-models:dax** (perf skill) |
|---|---|---|
| Goal | *Write* readable, debuggable measures | *Tune* slow/existing measures |
| Default | Avoid CALCULATE; FILTER + X-aggregators + VARs | CALCULATE/CALCULATETABLE/context-transition as tools |
| Trigger | "write a measure", "No CALCULATE", "make this readable" | "optimize DAX", "slow query", "server timings" |
| Catalog | Method + recipes (Ch. 1–16) | Tiered perf patterns DAX001–DAX021, QRY001–QRY004, model/Direct-Lake |

**How to use them together (no conflict):**

1. **Author first in No-CALCULATE style.** Default to this skill for any *new* measure.
2. **Only optimize what's measurably slow.** Don't pre-optimize. If a measure is fine, leave
   it readable.
3. **When profiling says it's slow**, switch to the perf skill. Its CALCULATE-based patterns
   (e.g. *DAX001* simple column predicates as CALCULATE args, *DAX005* push SUMMARIZE inputs
   into CALCULATETABLE, *DAX008* context transition in iterators, *DAX010* CALCULATETABLE
   table filters) are legitimate, targeted optimizations — **not** a contradiction of the No
   CALCULATE philosophy, just a different objective (best query plan over best readability).
4. **Keep the readable version.** When a CALCULATE rewrite wins on timings, retain the
   No-CALCULATE version in a comment so the intent stays debuggable.
5. **Shared ground both agree on:** push work to the SE; cache repeated tables/expressions in
   VARs; set the right grain; keep iterators SE-friendly; filter on precomputed integer/
   boolean columns. The No-CALCULATE pattern naturally lands on most of these already.

Net: **authoring = this skill; performance tuning = the perf skill.** The CALCULATE
"disagreement" is a difference of *purpose*, and the two compose cleanly when you author for
clarity and optimize only on evidence.
