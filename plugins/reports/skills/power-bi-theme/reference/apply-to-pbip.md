# Applying a Gallery Theme to a PBIP / PBIR Project

How a chosen theme from the library gets registered and applied to a Power BI project.

## Where a custom theme lives in a PBIP report

```
MyReport.Report/
  definition/report.json                       # themeCollection + resourcePackages
  StaticResources/RegisteredResources/<file>   # the custom theme JSON itself
```

- `definition/report.json -> themeCollection.customTheme.name` names the active custom theme.
- The theme file sits in `StaticResources/RegisteredResources/` and is listed in the
  `RegisteredResources` resource package inside `report.json`.

## Preferred: `pbir` CLI (handles all wiring)

```bash
# 1. Register the library theme JSON as a named template
pbir theme create-template --new-template "${CLAUDE_PLUGIN_ROOT}/skills/power-bi-theme/themes/Theme 7 - Dark.json" \
  --name "theme-7-dark" --description "From Power BI theme gallery"

# 2. Apply it to the report (copies into RegisteredResources, updates report.json)
pbir theme apply-template "MyReport.Report" theme-7-dark -f

# 3. Enforce: clear stale visual-level overrides, preserving conditional formatting
pbir visuals clear-formatting "MyReport.Report/**/*.Visual" --keep-cf -f

# 4. Validate
pbir validate "MyReport.Report"
```

`list-templates` shows registered templates; re-run `create-template ... --update-template`
to refresh a template from an edited source file.

## Manual fallback (no `pbir` CLI)

1. **Copy** the theme JSON into `MyReport.Report/StaticResources/RegisteredResources/`.
   Give it a stable filename, e.g. `Theme7Dark.json`.

2. **Register it** in `MyReport.Report/definition/report.json` under the
   `RegisteredResources` package (create the package if absent):

   ```json
   "resourcePackages": [
     {
       "name": "RegisteredResources",
       "type": "RegisteredResources",
       "items": [
         { "name": "Theme7Dark.json", "path": "Theme7Dark.json", "type": "CustomTheme" }
       ]
     }
   ]
   ```

3. **Activate it** by setting the custom theme in `report.json`:

   ```json
   "themeCollection": {
     "baseTheme": { "name": "CY24SU10" },
     "customTheme": { "name": "Theme7Dark.json" }
   }
   ```

4. **Validate** the JSON (`jq empty report.json`) and confirm the `customTheme.name`
   exactly matches the registered item `name`.

> Back up `report.json` before editing. Legacy single-file reports keep `themeCollection`
> and `resourcePackages` in `MyReport.Report/report.json` instead of `definition/report.json`
> — same keys, different location.

## Why a Desktop reload (not just refresh) is required

Power BI Desktop reads custom themes from `RegisteredResources` **only when the file is
opened**. A canvas/definition refresh re-reads pages and visuals but not StaticResources,
so theme changes will not appear until you **close and reopen** the report in Desktop.

## After applying

- Visual-level overrides in each `visual.json` (`objects` / `visualContainerObjects`) win
  over the theme. If the new theme doesn't fully show, clear those overrides (step 3 above).
- When switching between a dark and a light theme, watch for hardcoded text colors that
  were readable under the old background but become invisible under the new one. The
  `reports:modifying-theme-json` skill's re-theming workflow handles this polarity sweep.
