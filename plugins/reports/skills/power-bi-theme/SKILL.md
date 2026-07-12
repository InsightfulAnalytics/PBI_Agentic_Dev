---
name: power-bi-theme
version: 26.25
description: Browse, visually compare, and apply Power BI report themes. Use when the user wants to "pick a theme", "choose a Power BI theme", "see all my themes", "preview themes", "compare themes", "open the theme gallery", or "apply a theme to my report/PBIP". Generates a visual HTML gallery of every theme in the library (each rendered as a mock report) so the user can choose by sight, then delegates apply to reports:modifying-theme-json. This skill BROWSES/CHOOSES a preset theme; for editing/enforcing a theme on a live report use reports:modifying-theme-json.
---

# Power BI Theme

A general-purpose skill for choosing a Power BI report theme **visually** and applying
it to a project. It ships with a library of starter theme JSON files and a generator
that renders every theme as a realistic mock report so the user can pick by sight,
not by reading hex codes.

## Layout

```
power-bi-theme/
  themes/                       # The theme library (one .json per theme). Add more here.
  scripts/generate_gallery.py   # Scans a themes folder -> self-contained gallery.html
  reference/apply-to-pbip.md    # Full apply + enforce + validate workflow & manual fallback
```

The library is general-use: it is **not** tied to any one project. New `*.json` themes
dropped into `themes/` (or any folder passed with `--themes-dir`) appear automatically.

## Workflow

### Step 1 — Generate and open the visual gallery

```bash
python "${CLAUDE_PLUGIN_ROOT}/skills/power-bi-theme/scripts/generate_gallery.py" --open
```

This scans `themes/`, renders each theme as a mock Power BI report (page background,
KPI cards, bar chart, donut, and the full data-color strip — all using that theme's own
colors), writes `themes/powerbi-theme-gallery.html`, and opens it in the browser.

- The gallery has **Dark / Light filters** and a **search box**.
- Add project-local themes to the comparison with `--themes-dir "<folder>"` (it scans
  recursively for any JSON containing a `dataColors` array).
- Custom output path: `--output "<path>.html"`.

Tell the user: *browse the gallery, click **Use this theme** on your favorite, then tell
me which one.* The button copies `Apply Power BI theme: <name>` to the clipboard.

### Step 2 — User picks a theme

The user names a theme (e.g. *"Apply Power BI theme: Theme 7 - Dark"*). Locate the
matching file in the library:

```bash
# find the file whose "name" matches, or by filename
ls "${CLAUDE_PLUGIN_ROOT}/skills/power-bi-theme/themes/" | grep -i "theme 7 - dark"
```

If the name is ambiguous (Dark vs Light), confirm which variant.

### Step 3 — Apply to the current PBIP / PBIR project

Applying is owned by the **`reports:modifying-theme-json`** skill — do not duplicate the
apply logic here. Hand it two things and follow its Apply / Enforce / Validate workflow:

- the chosen library JSON: `${CLAUDE_PLUGIN_ROOT}/skills/power-bi-theme/themes/<name>.json`
- the target report folder (`*.Report` containing `definition/report.json`; ask the user
  for its path if none is in the working directory)

That skill registers the template, applies it, clears stale visual-level overrides
(keeping CF), validates, and covers the **close-and-reopen-in-Desktop** requirement
(Desktop reads custom themes from `RegisteredResources` only at open).

Manual fallback if neither the `pbir` CLI nor that skill is available:
`reference/apply-to-pbip.md`.

## Notes

- **Dark vs Light** is inferred from each theme's page-background luminance, so the badge
  is correct even if the filename doesn't say "Dark"/"Light".
- The gallery is fully self-contained (theme data is embedded) — it works by double-click,
  no server, and can be shared as a single HTML file.
- For deep theme *authoring/auditing* (visualStyles cascade, compliance, re-theming),
  defer to the `reports:modifying-theme-json` and `reports:pbir-cli` skills; this skill is
  focused on **choosing** a theme and dropping it into a project.
