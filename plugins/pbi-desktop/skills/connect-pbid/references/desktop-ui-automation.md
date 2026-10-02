# Driving Desktop's UI without stealing the foreground

**Power BI Desktop only, so Windows only.** Some Desktop features have no API at all: Performance
Analyzer, Export data, Show as a table, switching the visible page when the local-API preview is off.
They can still be driven end to end through Windows UI Automation (the `UIAutomationClient`
assemblies), and none of the routes below needs Desktop in the foreground.

**Never use SendKeys or coordinate clicks against Desktop when a UIA route exists.** Windows blocks
`SetForegroundWindow` from a background process, so keystrokes and clicks land in whatever window the
user has in front. That failure is silent: one sweep typed a file path into an editor's chat box
before anyone noticed. A coordinate click is the last resort, only for an element UIA cannot see.

Where Desktop is unavailable, render server-side with the `ExportTo` API instead
(`fabric-cli:fabric-cli`, `references/reports.md`).

(Routes observed on Desktop 26.08, September 2026.)

## Finding things

Search from Desktop's **main window** element. Banners, the save prompt and the Save As dialog are
children inside the main window in the UIA tree, not top-level windows, so a search from the process
root or the desktop root finds nothing and looks like the control does not exist.

Element names often carry trailing spaces. Match on `Name.Trim()`.

## Switching the visible page

`SelectionItemPattern.Select()` on the page tab, matched on the page's `displayName`. It works on a
background window. Use it before a screenshot or a Performance Analyzer pass of any page but the
first: `pbir desktop screenshot <report>` renders the first page whatever path it is given (see
`reports:pbir-cli` `references/cli-traps.md`).

## Performance Analyzer, end to end

1. Switch to the page (above).
2. The pane's buttons (Start recording, Refresh visuals, Stop, Clear, Export) all take
   `InvokePattern`, in the background.
3. Detect completion by polling the count of `TreeItem` elements in the pane until it stops growing,
   not with a fixed sleep.
4. Export opens a Save As dialog: set the path with `WM_SETTEXT` on control id **1001** (the file
   name box) and press `BM_CLICK` on control id **1** (Save). The dialog is a child of the Desktop
   window, so find it from the main window.
5. The export is written with a **UTF-8 BOM**. Read it with `encoding="utf-8-sig"` in Python.

What Performance Analyzer's numbers mean, and how they compare with a DAX harness, is in
`custom-visuals:performant-matrix`, `references/per-cell-tax.md`.

## A visual's own menu (Export data, Show as a table)

1. `InvokePattern` on the visual's `Group` element selects it. Only then does its header expose the
   "More options" button.
2. "More options" takes `ExpandCollapsePattern.Expand()`, not Invoke.
3. The menu items take `InvokePattern`. Export data's Save As is the same 1001/1 dialog as above.

Format pane labels can be searched by `ValuePattern.SetValue` on the pane's search box.

## Clicking in edit mode

In Desktop edit mode a button's navigation or bookmark action fires only on **Ctrl+click**; a plain
click selects the button. Clicking into a textbox opens it for editing: leave by switching page, not
with Escape, which leaves the editing toolbar up. Do not click into a visual just to deselect.

## Closing a background Desktop

See [desktop-lifecycle.md](./desktop-lifecycle.md), "CloseMainWindow() is not reliable on Desktop":
the polite close routes all do nothing while Desktop is behind another window, and the escalation
must respect the `cache.abf` rule.
