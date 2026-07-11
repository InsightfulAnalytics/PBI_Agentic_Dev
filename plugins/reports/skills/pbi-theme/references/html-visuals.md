# HTML Visual Generation

Instructions for generating custom HTML visuals for Power BI using the "HTML Content" visual from AppSource, aligned with the brand tokens from the generated theme.

## Token Embedding in DAX

Since HTML Content visuals cannot load external CSS files, tokens must be embedded as DAX variables at the top of each measure:

```dax
MyVisual =
// Brand tokens (from {brand}-tokens.css)
VAR _Primary = "{brand_primary}"
VAR _Secondary = "{brand_secondary}"
VAR _TextPrimary = "{text_primary}"
VAR _TextSecondary = "{text_secondary}"
VAR _TextMuted = "{text_muted}"
VAR _BgSurface = "{white}"
VAR _BgCanvas = "{bg2}"
VAR _Border = "{border_primary}"
VAR _BorderLight = "{border_light}"
VAR _Accent50 = "{accent_50}"
VAR _Accent500 = "{accent_500}"
VAR _Accent700 = "{accent_700}"
VAR _Good = "{good}"
VAR _Bad = "{bad}"
VAR _Warn = "{warn}"
VAR _Radius = "6px"
VAR _Font = "'Segoe UI', system-ui, sans-serif"
// ... data variables below
RETURN "..."
```

## Responsive Design Rules

ALL HTML visuals MUST be fully responsive:

```css
html, body {
  overflow: hidden !important;
  margin: 0; padding: 0;
  height: 100vh; width: 100%;
  background: transparent !important;
  font-family: 'Segoe UI', system-ui, sans-serif;
}
```

**Key patterns:**
- `height: 100vh` + `width: 100%` on root container
- `flex: 1` for cards in a row
- `font-size` in px (not rem/em)
- `box-sizing: border-box` on everything
- Never fixed widths on cards

## Visual Types

Offer these patterns when users ask for HTML visuals:
- **KPI Cards** — row of 3-5 cards with label, value, delta (SVG arrows), hover tooltip
- **Status Badges** — dynamic bg/border based on status, accent + semantic colors
- **Progress Bars** — horizontal bar with color thresholds
- **Data Cards with Image** — background image + gradient overlay + hover insight
- **Metric Comparison** — side-by-side values with visual bars

## SVG Icons

Inline SVG icons using `currentColor` for theme consistency:

```html
<!-- Trend Up -->
<svg width='14' height='14' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><polyline points='22 7 13.5 15.5 8.5 10.5 2 17'/><polyline points='16 7 22 7 22 13'/></svg>

<!-- Trend Down -->
<svg width='14' height='14' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><polyline points='22 17 13.5 8.5 8.5 13.5 2 7'/><polyline points='16 17 22 17 22 11'/></svg>

<!-- Check / Alert / Flag / Lightbulb — same pattern with currentColor -->
```

## Hover and Interaction

```css
.card { position: relative; overflow: hidden; cursor: pointer; }
.overlay { position: absolute; top:0; left:0; width:100%; height:100%; opacity:0; transition: opacity 0.3s; pointer-events:none; }
.card:hover .overlay { opacity:1; pointer-events:auto; }
.card:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
```

## Quality Standards

Every HTML visual must:
- [ ] Use ONLY brand token colors
- [ ] Be fully responsive (100vh + 100% + flex)
- [ ] Set `background: transparent !important` on body
- [ ] Set `overflow: hidden !important` on html/body
- [ ] Work without external CSS/JS dependencies
- [ ] Use `currentColor` on SVG icons
- [ ] Use DAX variables for ALL dynamic values
