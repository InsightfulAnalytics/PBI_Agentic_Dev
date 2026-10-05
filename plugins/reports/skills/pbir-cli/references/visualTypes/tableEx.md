# tableEx

Use `tableEx` for flat operational detail and `pivotTable` for hierarchy. Prefer a few decision-useful columns over a wide data dump.

## Renderer constraints

Power BI exposes horizontal alignment for native table values, but not vertical alignment. An SVG/image measure sets the row height, so ordinary text can appear top-heavy beside a 40-50px image even though the JSON is valid. Do not invent `values.verticalAlignment`.

Use the density helper to optically center the row. Choose one column-sizing
mode based on the layout:

```bash
# Fill all available width
pbir visuals table-density "Report.Report/Page.Page/Table.Visual" \
  --preset compact --row-padding 0 --image-height 30 --stretch-columns

# Size from rendered content (the mode Desktop often writes after manual sizing)
pbir visuals table-density "Report.Report/Page.Page/Table.Visual" \
  --preset compact --row-padding 0 --image-height 30 --fit-columns-to-content
```

Equivalent explicit properties:

```bash
pbir set "Table.Visual.grid.rowPadding" --value 0
pbir set "Table.Visual.grid.imageHeight" --value 30
pbir set "Table.Visual.columnHeaders.autoSizeColumnWidth" --value false
pbir set "Table.Visual.columnHeaders.customColumnWidth" --value false
pbir set "Table.Visual.columnHeaders.columnAdjustment" --value growToFit
```

`growToFit` fills the visual width. `fitToContent` sizes each column from its
rendered contents and removes stale custom-width mode. The flags are mutually
exclusive. `fixedWidth` preserves per-field `columnWidth` overrides.

## Practical rules

1. Rename technical headers locally or report-wide to short reader language (`Order Lines` -> `Lines`, `OTD % (Lines)` -> `OTD`).
2. Use 11-12pt values and 10-11pt headers for a 1280x720 presentation canvas.
3. Make horizontal gridlines white or extremely subtle; disable vertical gridlines.
4. Reserve status color for exceptions. Neutral rows stay slate/gray; failing values may use pastel rose backgrounds with dark rose text.
5. If an SVG carries the comparison, include an accessible `<title>` and `<desc>` and keep the native numeric columns available.
6. Execute the visual query after changing TopN, sorting, or extension measures; schema validation does not prove the intended rows are returned.
