# SVG Template Matrix

Which SVG pattern fits which host, how each host is wired in PBIR, and the one-step commands that add a pattern as a thin report (extension) measure. Wiring below was verified by rendering in the Power BI service on 2026-09-19.

## Pick a pattern

```yaml
bullet:     actual bar + target tick + variance %; bar grey on or above target, crimson below (only problems draw the eye)
            hosts: matrix/table cell, card image
progress:   rounded track filled to actual / target, with the %
            hosts: cell, card, button slicer
pill:       variance % in a soft green or red pill with an arrow
            hosts: cell, card, button slicer (on a Budget / Forecast / 1YP slicer each button shows its own gap)
sparkline:  the actual over an axis column (month number or date), last point marked
            hosts: cell, card, button slicer
dumbbell:   actual and target as two dots joined by a line
            hosts: cell
diverging:  variance % as a bar left (below target) or right (above) of a center line
            hosts: cell
delta:      IBCS absolute variance: a bar from a zero line, green or red, the signed difference (K/M/bn) on the other side of zero
            hosts: cell
pin:        IBCS relative variance: a line from zero ending in a dot, green or red, the % on the other side of zero
            hosts: cell (prefer delta and pin to a dumbbell, which cannot show a few % on a wide range)
gauge:      thin arc in the metric color, dark target tick and label, value in Segoe
            hosts: image visual (prefer it to the native gauge, which has no arc thickness and falls back to DIN)
```

Choose by the question the reader asks of that spot:

- "Where am I against target?" in a row: bullet (magnitude matters), or delta and pin (only the gap matters)
- "How far through the goal?": progress
- "Better or worse, by how much?" in little space: pill
- "Which way is it moving?": sparkline
- One headline number against one target: gauge on a card

## Wire it into the host

### Table or matrix cell

- Bind the measure to `Values` like any measure; rename the column header with a projection display name
- Set `grid.imageWidth` and `grid.imageHeight` on the visual (110 x 24 suits the patterns above; it is one size for every image column of the visual, and wider stretches a sparkline flat)
- Scale row bars against the largest row at the same level of the host's row fields, or subtotals dwarf detail rows:

```dax
VAR _max =
    SWITCH ( TRUE (),
        ISINSCOPE ( 'Products'[Subtype] ), MAXX ( CROSSJOIN ( ALLSELECTED ( 'Products'[Type] ), ALLSELECTED ( 'Products'[Subtype] ) ), CALCULATE ( MAX ( [Actual], [Target] ) ) ),
        ISINSCOPE ( 'Products'[Type] ), MAXX ( ALLSELECTED ( 'Products'[Type] ), CALCULATE ( MAX ( [Actual], [Target] ) ) ),
        MAX ( [Actual], [Target] ) ) * 1.08
```

- Because the scale depends on the host's rows, write one measure per host (name it after the row field, e.g. `Actual bullet by Key Account`)
- Add a `<desc>` sort key so the image column sorts by the value it shows

### Image visual (an SVG on its own)

A card is for a number; an SVG with nothing else (a gauge, a chart drawn in DAX) goes in an image visual, `visualType: "image"`, reading the measure through "Select from data":

```json
"image": [{
  "properties": {
    "sourceType": {"expr": {"Literal": {"Value": "'imageData'"}}},
    "sourceField": {"expr": {"Measure": {"Expression": {"SourceRef": {"Schema": "extension", "Entity": "Sales"}}, "Property": "Revenue gauge"}}},
    "transparency": {"expr": {"Literal": {"Value": "0D"}}}
  }
}]
```

No selector on the entry, and no `query` on the visual: an image visual with an empty `"query": {"queryState": {}}` renders blank.

### New card (`cardVisual`) image area

The card's own image area is the `image` object; the callout image is `cardImage`. For an SVG that fills the card:

```json
"image": [{
  "properties": {
    "show": {"expr": {"Literal": {"Value": "true"}}},
    "imageType": {"expr": {"Literal": {"Value": "'imageUrl'"}}},
    "imageUrl": {"expr": {"Measure": {"Expression": {"SourceRef": {"Schema": "extension", "Entity": "Sales"}}, "Property": "Revenue gauge"}}},
    "position": {"expr": {"Literal": {"Value": "'Top'"}}},
    "fit": {"expr": {"Literal": {"Value": "'Fit'"}}}
  },
  "selector": {"id": "default"}
}]
```

To show only the SVG, hide the card's value and label. Their selectors differ: the value switch takes effect without a selector, the label switch with `{"id": "default"}`.

### Button slicer (`advancedSlicerVisual`) per-button image

A static image applies to all buttons; a per-button image comes from a measure through the image "Select from data" slot. The measure is evaluated in each button's context, so it can differ per button:

```json
"image": [
  {"properties": {"show": {"expr": {"Literal": {"Value": "true"}}}, "sourceType": {"expr": {"Literal": {"Value": "'imageData'"}}}}, "selector": {"id": "default"}},
  {"properties": {"image": {"expr": {"Measure": {"Expression": {"SourceRef": {"Schema": "extension", "Entity": "Sales"}}, "Property": "Target pill"}}}},
   "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}], "id": "default", "hierarchyMatching": 1}}
]
```

Without `id` and `hierarchyMatching` on the second selector the service ignores the slot.

## One step with pbir

```bash
pbir visuals svg --list
pbir visuals svg "Report.Report/Page.Page/Matrix.Visual" -p bullet -a "Sales.Actual YTD.Measure" -t "Sales.Target YTD.Measure" --header "vs target"
pbir visuals svg "Report.Report/Page.Page/Matrix.Visual" -p sparkline -a "Sales.Actual.Measure" --axis "Date.Month Number.Column" --header "trend"
pbir visuals svg "Report.Report/Page.Page/Targets.Visual" -p pill -a "Sales.Actual YTD.Measure" -t "Sales.Target YTD.Measure"
pbir add gauge-card "Report.Report/Page.Page" -v "Sales.Actual YTD.Measure" --target "Sales.Target YTD.Measure" --color "#2A7F8C"
```

Each writes a thin report measure (ImageUrl data category) and wires it into the host as above. The pbir MCP has the same operations: `pbi_visual(operation="add_svg")` and `pbi_visual(operation="create_gauge_card")`.

## Pitfalls seen in practice

- Colors are plain `#` hex. The service encodes the data URI itself, so `%23` breaks every color
- Measure names are unique across the model, case-insensitively: "Turnover vs budget color" clashes with "Turnover vs Budget color"
- A measure-only chart with blank future months drops those months even with "show items with no data"; return 0 and give the measure a format with an empty zero section (`#,##0;-#,##0;""`)
- Sentiment colors (green, red) are for good and bad only; use the metric's own color or neutral grey for everything else
