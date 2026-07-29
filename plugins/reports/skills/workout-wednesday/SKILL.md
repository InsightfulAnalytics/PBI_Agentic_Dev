---
name: workout-wednesday
version: 26.25
description: End-to-end pipeline for a Power BI Workout Wednesday challenge — from a pasted challenge link to a built PBIP report, visually verified against the original and published to a Fabric workspace. Use when the user pastes a workout-wednesday.com challenge link, says "this week's Workout Wednesday", "WW week N", or asks to build or publish a WW challenge solution.
---

# Workout Wednesday pipeline

[Workout Wednesday](https://www.workout-wednesday.com/) publishes a weekly Power BI
challenge: a requirements page, a source dataset, and a screenshot of the target
visualization. Same shape every week, so the build follows one repeatable pipeline.

**Target flow: one challenge link in → a verified, published report out.** Ask the user
only what the challenge page doesn't answer.

## 0. Parse the challenge

- WebFetch the challenge link. Extract three things: the **requirements** (the numbered
  list of what the solution must do), the **data source** link (usually an `.xlsx`/`.csv`
  download or a public Power BI dataset), and the **screenshot** of the original viz.
- Note the challenge author and week number — they belong in the project notes.
- Download the source data into the project folder (see layout below), not to a temp
  directory. On Windows, never download to a POSIX `/tmp` path — it won't be readable
  by later steps.
- If the requirements are ambiguous (they often leave interaction behavior implicit),
  list your reading of them back to the user before building rather than guessing twice.

## 1. Project layout

Each challenge gets its own subdirectory under a `Workout Wednesday` parent:

```
<projects root>/Workout Wednesday/<Challenge Name>/
  <Challenge Name>.Report/          PBIR report
  <Challenge Name>.SemanticModel/   TMDL model
  <Challenge Name>.pbip
  data/                             downloaded source files
  scripts/                          spec builders / data prep, if needed
  notes.md                          requirements, challenge link, author credit
```

**Scaffold by forking the closest existing WW project** if one exists — the model is
usually a single flat table and the report a single page, so a fork gets you to "build the
visual" fastest. Otherwise use the `reports:create-pbi-report` skill, passing an
**absolute** report path to `pbir new report` (a previously-active report can otherwise
hijack a relative path — see the `reports:pbir-cli` skill).

The project **must be enhanced PBIR** — confirm
`definition/pages/<page>/visuals/<visual>/visual.json` files exist. The Deneb round-trip,
`pbir validate`, and verify-loop steps all operate on enhanced PBIR and do nothing useful
against PBIR-Legacy's single `report.json`.

## 2. Build

- **Model:** typically one flat table or a small star, loaded from the downloaded file.
  Author TMDL directly per the `pbip:tmdl` skill; the `pbip:pbir-format` skill covers the
  visual JSON. If the challenge is date-driven, the `semantic-models:date-table` skill
  drops in a full date dimension rather than hand-rolling one.
- **Visuals:** most WW challenges exist precisely because a native visual can't do it, so
  expect Deneb — author the spec with `custom-visuals:deneb-visuals` and use
  `custom-visuals:deneb-pbir` to extract/patch/embed it in `visual.json` and
  **offline-render it with sample data before ever opening Desktop**. Native visuals go
  through `reports:pbir-cli`.
- **Design round (optional):** a mockup via Claude Design, imported with the
  `reports:claude-design-handoff` skill.
- **Reconcile against the challenge source before calling it done.** The recurring failure
  mode is a report that looks right and is wrong: colors mapped to the wrong categories,
  groupings that don't match the original, totals that don't tie out. Check each
  requirement off the list explicitly.

## 3. Verify

- Run `pbir validate` after any hand-edited `visual.json`.
- Run the `reports:pbi-verify-loop` skill to refresh Desktop from disk, wait for the
  canvas to settle, and screenshot the page. Pass `--compare <original-viz.png>` to diff
  against the challenge's screenshot where the layouts are close enough for a pixel diff
  to mean anything.
- **Read the screenshot yourself**, then have the user eyeball it. They decide when it
  matches the challenge — a low diff ratio doesn't.

## 4. Publish

```bash
pbir publish "<Challenge Name>.Report" "<Workspace>.Workspace/<Challenge Name>.Report" -f
```

This import path works independently of the `fab` schema-load issue noted in the
`reports:pbir-cli` skill. **Confirm the report is live in the workspace before reporting
success** — check it with `fab ls "<Workspace>.Workspace"` or open the service URL.

## Wrap-up

Write the challenge link, author credit, requirements, and anything non-obvious about the
solution into the project's `notes.md`. Any new Deneb/Vega technique or gotcha that
generalizes beyond this one challenge belongs in the `custom-visuals:deneb-pbir` or
`custom-visuals:deneb-visuals` skill, not just the project notes.
