---
name: claude-design-handoff
version: 26.25
description: Import and implement a Claude Design handoff (an api.anthropic.com/v1/design/... URL, a claude.ai/design link, or a design ZIP) into a Fabric App or Power BI report, and author the reverse handoff brief back to Claude Design. Use whenever the user pastes a design URL, says "fetch this design file and implement", "import the design", mentions a Claude Design handoff/mockup, or asks for a design brief for Claude Design. Encodes the extraction, delta-application, and cleanup rules that repeatedly went wrong when done ad hoc.
---

# Claude Design handoff

The recurring loop: user pastes a design URL → fetch ZIP → extract → read README → implement the delta → verify → (deploy) → optionally write a brief for the next design round. These rules exist because each step has failed before.

## 1. Fetch & extract — route by target

- **Fabric App target:** don't extract by hand — pass the downloaded ZIP to the project's importer: `npm run import-design -- --zip <path>` (extracts to `design-imports/<name>/` and generates the manifest; conventions in the `fabric-app-workflow` skill). Manual extraction is only for peeking at the README before importing.
- **Power BI report target (or README inspection):** extract into the **session scratchpad dir** (or `design-tmp/` under the project), always a **Windows-absolute path**. Never `/tmp/...` — files land somewhere the Read/Grep tools can't see.
- Unzip with `Expand-Archive` (PowerShell) or `python -m zipfile -e handoff.zip <dest>`. **Never Git Bash `tar`** — it parses `C:\...` as a remote host ("Cannot connect to C").
- Read the ZIP's **README first**, then inventory the contents (ui_kits, tokens, pages) before touching project files.

## 2. Apply the DELTA only — preserve existing chrome

The #1 repeated correction: handoffs arrive containing stale or foreign design-system elements. Applying them wholesale clobbers the app's existing shell.

- Implement only what the current request is about (the new page, the changed chart, the updated tokens).
- **Never replace** the app's existing left nav, page header, header-row filter pane, or global layout unless the user explicitly asks — even if the handoff includes its own versions of them.
- When a handoff component conflicts with the house design system, keep the house version and adapt the new component to it (for Fabric Apps, follow the `fabric-app-workflow` skill's conventions and `import-design` flow).
- Scope-of-change discipline: if a shared component (tooltip, card, axis config) is edited for one chart, check which other charts consume it before saving.

## 3. Verify before claiming done

- Fabric App: typecheck with `npx tsc -b` (build mode — plain `tsc --noEmit` skips the project-referenced `rayfin/` code and can pass on broken TS; the rayfin build itself uses `--noCheck`), then deploy per project convention and confirm the change is visible at the live URL.
- Power BI report: `pbir validate`, then the `pbi-verify-loop` skill (screenshot vs the design mockup with `--compare`).

## 4. Cleanup — deferred, not forced

Extraction folders often keep a file lock (a process holds `design-tmp/...`) — `rm -rf` retries have failed 3x in a row before. Don't fight it: attempt one delete at the END of the session; if locked, leave it in the scratchpad (auto-cleaned) and say so.

## 5. Reverse handoff: the design brief

When the user asks to "advise Claude Design of these changes" or requests the next design round, write a markdown brief into the project's `design-system/` folder using `templates/design-brief-template.md`. Name it `<TOPIC>-BRIEF.md` (matches existing `BUDGET-ADDITIONS-BRIEF.md` convention).

## Boilerplate the user usually types (do it unprompted)

- If the URL is a `claude.ai/design` link, the Claude Design MCP connector may need `/design-login` first — check connection before failing.
- After implementing a requested change that typechecks, deploy per the CLAUDE.md convention (cd to app dir → `npx rayfin up` → report the live fabricapps.net URL) without waiting to be asked; "deploy" is also Tim's one-word command for exactly that sequence.
