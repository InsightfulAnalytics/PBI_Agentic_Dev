# Fast Rendered-Dashboard Loop

Validation proves PBIR structure; it does not prove that Power BI rendered the
intended selector, density, text height, or visual hierarchy. For high-fidelity
dashboard work, use short publishable batches.

```bash
# Discover actual capability names and effective formatting first
pbir schema describe cardVisual label
pbir visuals format "Report.Report/Page.Page/Card.Visual" -p label -v

# Apply one coherent batch, validate, and execute affected visual queries
pbir validate "Report.Report"
pbir visuals test "Report.Report/Page.Page/Changed.Visual"

# Publish when Desktop is unavailable or the user is watching progress
pbir publish "Report.Report" "Sandbox.Workspace/Report.Report" -f
```

Once the user authorizes regular publishing, publish after each coherent visual
batch. Preserve a before-state first with `pbir backup` when comparison matters.

Renderer-sensitive shortcuts:

- New Card: use the visual-container title or the internal `label`, not both.
  Plain-path writes route known objects to the renderer-required selector.
- Table/matrix with SVG measures: native values do not expose vertical
  alignment. Use `pbir visuals table-density` to make rows optically centered.
- Latest-only line label: bind a sparse measure that returns only the latest
  selected period, then format its `lineStyles.field(...)` and
  `labels.field(...)` entries. See `references/visualTypes/lineChart.md`.

With Desktop on Windows, refresh and capture after each meaningful batch. On
macOS/Linux, or when the bridge is unavailable, validate, publish to the agreed
sandbox target, and inspect the service render.
