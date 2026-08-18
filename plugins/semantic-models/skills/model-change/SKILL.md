---
name: model-change
version: 26.25
description: The end-to-end pipeline for changing a semantic model in a local PBIP — confirm the field exists, author, land it in TMDL, validate offline, then prove it against real data. Invoke on "change the model", "add a measure", "add a column", "fix the model", "the number is wrong", "this measure is wrong", "add a relationship", "set up RLS", "add a calculation group", "add a date table", "rename a field", "the model won't open", or any request that ends with a .tmdl file changing. Sequences connect-pbid, power-query, date-table, semantic-model, dax-no-calculate, tmdl, dax and refresh-semantic-model, and carries the Desktop-breaking gotchas that a single-skill route misses.
---

# Model change pipeline

Every model change follows the same five steps. Skipping step 1 is how you author a measure
against a column that doesn't exist; skipping step 4 is how Desktop refuses to open the
project afterwards.

**"Change the model" means the local PBIP via direct TMDL edits** — not the live Fabric
model — unless the user says otherwise. Confirm which model before touching anything if
there is any doubt.

## 0. Before anything

- `pbir desktop list` — is Desktop holding this project open? If it is, **coordinate with
  the user first.** Desktop keeps its own in-memory copy and re-serialises on save, so it
  will clobber disk edits.
- Tim nudges layout inside Desktop between turns. Re-read from disk at task start; never
  reuse positions or definitions remembered from earlier in the conversation.

## 1. Confirm the shape — don't author blind

Load `pbi-desktop:connect-pbid` and query the live instance. The point is to prove the
table, column or measure you are about to reference actually exists and holds what you think.

- `pbir model -q` fails on this machine (the local-API preview is off). Go straight to the
  direct ADOMD path in that skill — DAX Studio's `Microsoft.AnalysisServices.AdomdClient.dll`
  is the one that loads under PowerShell 5.1. Tabular Editor 3's is .NET 8 and throws.
- If Desktop isn't open, read the TMDL under `<Model>.SemanticModel/definition/tables/`.

## 2. Author

Pick the skill that matches the change:

| Change | Skill |
|---|---|
| Measure / calculation | `dax-no-calculate` |
| Partition M, folding, a new source | `semantic-models:power-query` |
| Relationships, RLS, calc groups, star-schema fixes, model quality | `semantic-models:semantic-model` |
| A date/calendar table | `semantic-models:date-table` — don't hand-copy from `Date Table Template` |
| Renaming across the project | `pbip:pbip` (the rename cascades into PBIR) |

DAX house style: expression starts on **line 2** after the `=`; short lines; the explanatory
comment goes **after** the measure name, not above it; prefer `DATEADD` over
`SAMEPERIODLASTYEAR`. Never leave a measure in an error state.

## 3. Land it in TMDL

Load `pbip:tmdl`. Prefer the Edit tool over script-patching — checkpoint/rewind only restores
files changed via Write/Edit, so a python-patched `.tmdl` cannot be rolled back.

Three ways to break Desktop's file-open, all of which pass a casual read:

- **A calculation group requires `discourageImplicitMeasures`** on the model in `model.tmdl`.
  Without it Desktop refuses to load the whole project. Check this **every** time a calc group
  is added, then grep the report pages for bare column projections that relied on implicit
  aggregation.
- **Never leave a blank line after a `///` description.** A dangling description is
  `Unexpected line type: Empty!` and breaks both Desktop and the modeling MCP. `///` lines sit
  directly above the object they describe — never as standalone section banners.
- Blank lines *between sibling objects* are fine and expected. The failures come only from the
  two bad spots: after a `///`, or breaking a multi-line expression's indentation.

Prefer `///` doc comments over explicit `description` properties — `///` is what Desktop
serialises, so round-trip diffs stay stable.

## 4. Validate offline, before Desktop

Cheapest first, and it catches syntax errors in seconds rather than after a slow file-open:

- `TmdlSerializer::DeserializeDatabaseFromFolder(<definition>)` via DAX Studio's
  `Microsoft.AnalysisServices.Tabular.dll` parses the folder and lists tables, columns and
  measures. TE3's DLL is .NET 8 and will not load under PS 5.1.
- An offline `ConnectFolder` connection validates parse and bind only — **it cannot run DAX.**
  Offline-clean is not query-correct.

## 5. Prove it against real data

Desktop holds its own in-memory copy, so a TMDL edit on disk is invisible to a query until
close-and-reopen. Don't reopen just to test:

> Redefine the measure in the query with `DEFINE MEASURE '<Table>'[X new] = …` and select the
> old and new side by side in one `ROW()`. That proves the fix against real data with zero
> risk to the model.

Testing an `ALLSELECTED` measure? Don't sample rows with `FILTER(VALUES(...))` — the filter
propagates into `ALLSELECTED` and changes the answer. Build the full axis with
`ADDCOLUMNS(VALUES(...), ...)` first, then `FILTER` the result.

PowerShell quoting: bracketed names and `{}` break PS string parsing. Pass DAX via
single-quoted here-strings (`@'...'@`).

## Wrap-up

- Slow measure? *Now* load `semantic-models:dax` — it is for tuning, not authoring.
- Model-wide audit? `tabular-editor:te-cli` / `bpa-rules`.
- Needs a refresh? `semantic-models:refresh-semantic-model`. For a hand-authored PBIP whose
  first open shows "incomplete or no data", refresh through TOM
  (`$db.Model.RequestRefresh('Full')` + `SaveChanges()`) — the local-API preview is off, so
  `pbir desktop refresh` is unavailable.
- Report visuals affected by the change? Hand over to `reports:pbir-cli`, and verify with
  `reports:pbi-verify-loop`.
- After fixing a nontrivial error, record the root cause in the project's note under
  `Vault\Projects\<project>\` and add its row to `Vault\Projects\index.md`.
