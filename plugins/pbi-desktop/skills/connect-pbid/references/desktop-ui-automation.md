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

(Routes observed on Desktop 26.08, September 2026; the theme, page view and close routes on 26.10,
October 2026.)

## Finding things

Search from Desktop's **main window** element. Banners and the Save As and Open dialogs are
children inside the main window in the UIA tree, not top-level windows, so a search from the process
root or the desktop root finds nothing and looks like the control does not exist. The save prompt
raised by closing Desktop is the exception on 26.10: see "Closing a background Desktop" below.

Element names often carry trailing spaces. Match on `Name.Trim()`.

The ribbon can be missing from the tree straight after a report opens: poll for the tab rather than
failing on the first search.
Ribbon tabs (`design`, `view`) are `TabItem`s that take `SelectionItemPattern.Select()`; the
quick-access **Save** is a `Button` with AutomationId `save`.

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

## Importing a theme through Desktop

Desktop's own import is the route that shows what Desktop does to a theme file (it rewrites some
of it on import; see `reports:modifying-theme-json` `references/theme-authoring.md`, Data Colors).

1. Select the `design` tab, then invoke **Import theme** (`Button`, AutomationId `browseForThemes`).
2. The Open dialog (class `#32770`) is a child of the main window, but its file name box is not in
   the UIA tree. Reach it through Win32: `GetDlgItem(dialog, 1148)`, its `ComboBox` child, that
   control's `Edit` child; `WM_SETTEXT` the path, then `BM_CLICK` control id **1** (Open).
3. Desktop reports "File successfully added"; invoke **Got it** to dismiss it.
4. The theme is in memory only until you invoke the quick-access **Save**.

## Page view: Actual size for 1:1 renders

`pbir desktop screenshot` draws the page at the canvas zoom times `--scale`, never 1:1 (`reports:pbir-cli`
`references/desktop-integration.md`). For a render at one screen pixel per page pixel:

1. Select the `view` tab and expand **Page view** (`Button`, AutomationId `pageLayoutFlyout`,
   `ExpandCollapsePattern`).
2. Toggle the **Actual size** `CheckBox` (`TogglePattern`). **Fit to page** and **Fit to width** are
   check boxes too; a search for "Fit to page" also finds the status bar's `fitToPageButton`.
3. Capture the window with `PrintWindow` and flag `PW_RENDERFULLCONTENT` (2), which works with the
   window in the background, then crop the page out of it. Maximise the window first
   (`WindowPattern.SetWindowVisualState`) so a 1280-px page fits.

## Clicking in edit mode

In Desktop edit mode a button's navigation or bookmark action fires only on **Ctrl+click**; a plain
click selects the button. Clicking into a textbox opens it for editing: leave by switching page, not
with Escape, which leaves the editing toolbar up. Do not click into a visual just to deselect.

## Closing a background Desktop

See [desktop-lifecycle.md](./desktop-lifecycle.md), "CloseMainWindow() is not reliable on Desktop":
on 26.10 `WindowPattern.Close()` raises a save prompt that UI Automation cannot see, answered with
posted mouse messages, and any escalation must respect the `cache.abf` rule.
