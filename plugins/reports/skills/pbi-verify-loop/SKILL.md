---
name: pbi-verify-loop
version: 26.25
description: Visually verify Power BI report edits against a running Power BI Desktop instance — refresh the canvas from disk, wait until rendering is stable (no guessed sleeps), screenshot the page, and optionally diff against a mockup. Use after ANY edit to PBIR visual.json / pages / theme when Desktop is open, and whenever the user asks to "check the report", "verify the change", "screenshot the page", or a mockup comparison is needed. Replaces hand-rolled refresh + Start-Sleep + screenshot loops.
---

# PBI verify loop

One command replaces the `pbir desktop refresh` → `Start-Sleep <guess>` → `pbir desktop screenshot` cycle:

```bash
python "${CLAUDE_PLUGIN_ROOT}/skills/pbi-verify-loop/scripts/verify_page.py" \
  "MyReport.Report/ReportSection1.Page" -o "<scratchpad>/page.png"
```

The script refreshes the report from disk, then captures repeatedly (every 3s, up to 45s) until two consecutive screenshots are byte-identical — that is the "settled" signal. It prints JSON (`output`, `captures`, `stable`) and exits 0 when stable, 2 on timeout (last capture still written — inspect it anyway).

## Options

| Flag | Use |
|---|---|
| `--model` | Also re-apply the TMDL model (`refresh -m`) — needed after model.tmdl/measure edits |
| `--no-refresh` | Just settle+capture (e.g. after the user changed something in Desktop) |
| `--compare mockup.png` | Diff final capture vs a reference; writes `<out>-vs-ref.png` side-by-side and reports `diff_ratio` + `diff_bbox` |
| `--region x,y,w,h` | Crop both images to a region before comparing (verify one visual, ignore the rest) |
| `--scale 1-3` | Render scale (default 2) |
| `--timeout` / `--interval` | Stability polling knobs (default 45s / 3s) |

## Workflow

1. Edit PBIR/TMDL files on disk (per `~/.claude/rules/tmdl-pbir-authoring.md`).
2. Run `pbir validate` if visual.json was touched.
3. Run this script; **Read the output PNG** and judge the change visually before telling the user it's done.
4. For mockup-driven work (Claude Design), pass `--compare` with the mockup and check `diff_ratio` — but always eyeball the side-by-side too; pixel diffs can't judge intent.

## Preconditions & gotchas

- Power BI Desktop must be running with the report open, and the preview feature **"external tool access to Power BI Desktop through secure local APIs"** enabled (Options → Preview features, restart Desktop). Check with `pbir desktop list` — if it errors or shows nothing, tell the user to enable/restart rather than retrying.
- **`pbir desktop list` first, always**: if the instance shows `Unsaved: yes`, a refresh reloads from disk and can clobber Tim's unsaved in-Desktop tweaks — use `--no-refresh` or ask him to save first.
- Page path form is `Report.Report/PageName.Page` (folder names from `definition/pages/`), not display names. Omit the page to capture the first page.
- Full-flag reference for `pbir desktop`: see `~/.claude/rules/tmdl-pbir-authoring.md` (no `--out`, `--settle` is `--all`-only).
- If the capture never stabilizes (exit 2), something is animating or Desktop is stuck refreshing — check `pbir desktop list` for unsaved/busy state instead of raising the timeout blindly.
