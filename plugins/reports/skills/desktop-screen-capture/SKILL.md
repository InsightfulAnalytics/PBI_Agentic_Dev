---
name: desktop-screen-capture
version: 26.26
description: Screenshot what is actually on a Windows screen, the whole virtual desktop or one window located by title, and save a PNG the agent can Read. Use whenever you need to SEE a GUI: Power BI Desktop, a dialog, a driver or display symptom, a browser. Use especially when `pbir desktop screenshot` or the connect-pbid Desktop Bridge is unavailable because the "Enable external tool access to Power BI Desktop through secure local APIs" preview is off. Triggers include "what's on screen", "screenshot Power BI", "look at my screen", "can you see the dialog", "screenshot that window".
---

# Desktop screen capture

Captures the real screen on Windows and writes a PNG. Use the bundled script; do **not** hand-author
`Add-Type` / `Bitmap` / `CopyFromScreen` inline. That was being rewritten from scratch every time,
which is the entire reason this skill exists.

**Windows only.** There is no screen to capture on Linux or in a container, and no Power BI Desktop
there either. To see a Power BI report headlessly, render it server-side instead: `POST
groups/{ws}/reports/{id}/ExportTo`, poll, then `GET` the file, and convert the PDF to PNG with
`pymupdf`. The sequence is in the `fabric-cli:fabric-cli` skill's `references/reports.md`. Note that
`fab api` corrupts binary bodies, so fetch the file over raw HTTP with an `az` bearer token.

## Usage

```powershell
# whole virtual desktop (all monitors)
powershell -NoProfile -ExecutionPolicy Bypass -File "${CLAUDE_PLUGIN_ROOT}/skills/desktop-screen-capture/scripts/capture.ps1" -Out "shot.png"

# one window, matched on a substring of its title (case-insensitive)
... -File "<script>" -Title "Power BI Desktop" -Out "pbi.png"

# one window, matched by process name
... -File "<script>" -Process obsidian -Out "obs.png"

# list candidate windows without capturing
... -File "<script>" -List
```

Then `Read` the PNG path it prints.

Write captures to the session scratchpad, not the project. They are throwaway.

## Flags

| Flag | Meaning |
|---|---|
| `-Out <path>` | Output PNG. Default: `capture-<HHmmss>.png` in the current directory. |
| `-Title <substr>` | Capture the first visible window whose title contains this. |
| `-Process <name>` | Capture the main window of this process (no `.exe`). |
| `-List` | Print visible windows (PID, process, title, bounds) and exit. Use this first when a match fails. |
| `-NoActivate` | Skip bringing the window to the front. Default is to activate, because an occluded window captures whatever is drawn on top of it. |
| `-Scale <n>` | Downscale by factor n (2 = half size). Use on 4K captures to keep the image readable to the model. |
| `-Delay <ms>` | Wait before capturing. Use after activating something that animates or renders lazily. |

## Behaviour that matters

- **DPI**: the script calls `SetProcessDpiAwareness` before measuring. Without it Windows reports
  the wrong coordinates on a scaled display and you capture a cropped or offset region. This is the
  most common cause of a screenshot that looks wrong.
- **Multi-monitor**: `-Out` with no target captures the full virtual screen, including negative
  coordinates from a monitor placed left of or above the primary. It does not assume the primary
  display is the origin.
- **Activation**: a window that is not foreground captures whatever is drawn over it. The script
  activates first and waits for the window to actually come forward rather than sleeping a guessed
  interval. `-NoActivate` opts out when you deliberately want the occluded state.
- **Minimised windows** cannot be captured. The script restores them first, or errors clearly.

## When NOT to use this

- **The Power BI report canvas, where the local-API preview is on.** `reports:pbi-verify-loop` is
  better: it refreshes the canvas from disk and waits for a stable render instead of guessing a
  sleep. This skill is the fallback for machines where that preview is off, which is a per-machine
  toggle. Check `pbir desktop list` before assuming either way.
- **A published report in the Service.** Render server-side with `ExportTo` as described above. No
  GUI needed and it works headless.
- **Web pages you control.** Drive a real browser instead.

## Verify

`scripts/capture.ps1 -SelfTest` captures the desktop to a temp file, asserts the PNG is non-trivial
(over 10 KB, decodes, dimensions match the requested region), deletes it, and prints PASS or FAIL.
