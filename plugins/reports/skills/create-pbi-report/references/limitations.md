
# Limitations of agents using `pbir-cli`

You should inform users of your limitations:

- Connecting to Power BI Desktop; you only work with Power BI report metadata
- Working on report.json or layout json files (legacy format) - users must open their reports and save them with the enhanced report metadata (PBIR). PBIP format is recommended but not necessary.
- Adding new custom visuals from AppSource without their ID. Offer instead to create something with the `svg-visuals`, `deneb-visuals`, `r-visuals`, or `python-visuals` skills (from the custom-visuals plugin, if installed)
- Creating very detailed, bespoke visualizations with the core visuals
