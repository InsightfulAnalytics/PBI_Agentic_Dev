# Power BI: skill routing and Desktop rules

## Route to a skill before hand-rolling

At the start of each phase of Power BI work, say which skills you will load, so the user can add
one you missed.

- Change a semantic model in a local PBIP (measure, column, relationship, RLS, calc group, rename):
  `semantic-models:model-change`, which sequences the rest. Model design, build, refresh or review:
  `semantic-models:semantic-model`. Direct TMDL edits: `pbip:tmdl`. Organize or tidy a whole model
  (folders, names, descriptions, formats): `semantic-models:organize-semantic-model`
- Write, review, rewrite or format a DAX measure: `semantic-models:dax-standard` (house style). Only a
  measurably slow one: `semantic-models:dax-optimisation`. A slow matrix or P&L grid:
  `custom-visuals:performant-matrix`
- Date table for a new model: `semantic-models:date-table`, never a hand copy of another project's
- Report or visual work in .pbip/.pbir: `reports:pbir-cli`; a new report `reports:create-pbi-report`
- Queries or TOM against live Desktop: `pbi-desktop:connect-pbid`; never hand-roll ADOMD or TOM
- Screenshots after report edits: `reports:pbi-verify-loop` (`reports:desktop-screen-capture` if the
  local-API preview is off)
- Deneb or Vega: `custom-visuals:deneb-visuals` (author), `custom-visuals:deneb-pbir` (edit, render)
- Claude Design URL or ZIP handoff, report design questions: `reports:pbi-report-design`
- Themes: `reports:power-bi-theme` (presets), `reports:modifying-theme-json` (edit or enforce)
- New PBIP project: `pbip:pbip` for structure, one project per folder; scaffold folders and git
  by hand
- Power BI Service, workspaces, the `fab` CLI: `fabric-cli:fabric-cli`
- Multi-session build plans: `/pbi-plan`, user-invoked only, never for single-page changes
- A dataset you did not build: triage it for fabrication before planning, `reports:pbi-plan`
  `references/data-triage.md`

Before hand-authoring TMDL or PBIR JSON, read `pbip:tmdl` `references/authoring-gotchas.md` and
`pbip:pbir-format` `references/validation.md`.

## Desktop rules

- One Desktop instance per PBIP. Run `pbir desktop list` before the first write, and again before
  any git command that rewrites files (switch, pull, merge, stash).
- Batch every PBIR write for a page, then apply once.
- A Desktop save re-serializes the whole report and never reads back. If Desktop holds pending
  canvas changes when you edit on disk, apply the external change first or ask the user to close
  without saving, and say which.
- Desktop 26.08+ raises an "Apply external changes" banner, so close-and-reopen is not the default
  after a disk edit. Exceptions: `pbi-desktop:connect-pbid` `references/desktop-lifecycle.md`.
- Never run a programmatic data refresh (TOM `RequestRefresh`) against a model Desktop has open
  and in use: it races Desktop's own UI. Ask the user to click Refresh, or refresh once on a
  freshly opened, idle instance. Same reference, "A TOM refresh races Desktop's own UI".
