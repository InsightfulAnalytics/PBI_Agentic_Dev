# Layout Templates

Mood-based layout decisions, border style overrides, SVG background templates for all 5 canvas layouts (A/B/C/D/E) in both light and dark mode, logo embedding instructions, and resolution dimensions.

## Layout Decisions by Mood

The mood affects structural properties across ALL visuals. If the user chose a custom border style (question 7), override the border.show and border.radius values from the mood table below.

### Border Style Overrides (from user input)

| Option | border.show | border.radius | border color |
|--------|------------|---------------|-------------|
| `default` | true | 6px | `{border_primary}` |
| `rounded` | true | 12px | `{border_light}` (softer) |
| `sharp` | true | 0px | `{border_primary}` |
| `none` | false | 8px | n/a |
| Custom | from user | from user | `{border_primary}` |

### Global Wildcard (`visualStyles.*.*.`)

Note: `dark` is NOT a mood — it is a background mode. Mood controls layout/density, background mode controls colors.

| Property | professional | bold | minimal |
|----------|-------------|------|---------|
| `padding` (top/bottom/left/right) | 16 | 12 | 20 |
| `border.show` | true | true | false |
| `border.radius` | 6 | 4 | 10 |
| `title.show` | true | true | true |
| `subTitle.show` | true | false | true |
| `legend.show` | true | true | true |
| `legend.position` | "Top" | "Top" | "Bottom" |
| `divider.show` | false | false | false |
| `divider.style` | "dashed" | "solid" | "dashed" |
| `plotArea.transparency` | 80 | 50 | 90 |
| `dataPoint.transparency` | 80 | 40 | 85 |
| `dropShadow.show` | false | true | false |
| `dropShadow.preset` | "Bottom" | "BottomRight" | "Bottom" |
| `lineStyles.strokeWidth` | 1.5 | 2.5 | 1 |
| `valueAxis.gridlineShow` | true | false | true |
| `valueAxis.gridlineStyle` | "solid" | "solid" | "dashed" |
| `valueAxis.gridlineThickness` | 1 | 1 | 0.5 |
| `valueAxis.showAxisTitle` | false | true | false |
| `categoryAxis.show` | true | true | true |
| `categoryAxis.showAxisTitle` | false | true | false |
| `spacing.verticalSpacing` | 0 | 0 | 4 |
| `spacing.spaceBelowSubTitle` | 4 | 0 | 8 |
| `grid.rowPadding` | 4 | 2 | 6 |

### Table Variants

| Property | professional | bold | minimal |
|----------|-------------|------|---------|
| Table Airy `rowPadding` | 8 | 6 | 10 |
| Table Compact `rowPadding` | 4 | 2 | 4 |
| Table Compact grid weight | 0.25 | 0.5 | 0.25 |

### Action Button Presets

The "Brand" button variant uses:
- Background: `accent_500`
- Text: `white` (or `text_primary` if accent is light)
- Hover: `accent_700`
- Border radius: matches mood

The "Brand Soft" variant uses:
- Background: `accent_50`
- Text: `accent_700`
- Hover background: `accent_200`

### Font Selection by Mood

| Mood | Primary Font | Font for emphasis |
|------|-------------|-------------------|
| professional | Segoe UI | Segoe UI Semibold |
| bold | DIN | Segoe UI Semibold |
| minimal | Segoe UI Light | Segoe UI |

**IMPORTANT**: Power BI can only reliably use system-installed fonts. Always use Segoe UI family as the base. Only use DIN, Arial, Calibri if specifically appropriate.

## Structured SVG Background

Generate a clean, branded SVG background that gives the report a professional layout structure out of the box. This SVG is embedded as base64 in the page background and renders automatically when the user imports the theme.

**IMPORTANT RULES for the rest of the theme:**
- NO SVG patterns (dot grids, diagonal stripes, noise textures) anywhere
- NO `sourceFile` with embedded SVG logos in the image visual
- NO external URLs (third-party domains, etc.) in any icon or image property
- The ONLY embedded SVG allowed is the page background layout below

### SVG Background Design Principles

The SVG creates a structured report layout with zones for title, filters, navigation, and content. The base is always `{bg3}` (light gray), and the zones are `{white}` (white panels) creating visual separation.

**CRITICAL SVG RULES:**
- Always include `preserveAspectRatio="xMidYMid slice"` in the `<svg>` tag
- Use percentage widths (`100%`) for full-width elements
- Use fixed pixel values for heights and sidebar widths
- `scaling` must be `"Fit"` in the JSON

**Design principles:**
- Base fill: `{bg3}` (light gray) — this is the "canvas" color visible between panels
- Panels: `{white}` — white rectangles that create zones for visuals
- Title header: `{text_primary}` (dark) — strong contrast at top for branding
- Filter bar: `{white}` — clean space for slicers/filters
- Sidebar: `{white}` — navigation area
- Spacing between panels: 8px gaps create subtle gray lines of separation

### VALIDATED Layout SVG Templates

**IMPORTANT DESIGN RULES (validated in Power BI Desktop):**
- Always use `preserveAspectRatio="xMidYMid slice"` on the `<svg>` tag
- Panels are FLUSH (no gaps) — the color difference between panels IS the separator
- Use thin 1px lines (`{border_primary}` or `{border_light}`) for subtle separation
- Canvas area uses `{bg2}` (off-white/off-dark) NOT `{white}` — so visual cards stand out on it
- Header and filter bars use `{white}` in light mode
- Sidebar width: 200px fixed
- Header height: 56px, Filter bar height: 48px

### Layout A — Simple (header + line + canvas)

LIGHT:
```svg
<svg viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg">
  <rect width="100%" height="100%" fill="{bg2}"/>
  <rect width="100%" height="56" fill="{white}"/>
  <rect y="56" width="100%" height="1" fill="{border_primary}"/>
</svg>
```

DARK:
```svg
<svg viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg">
  <rect width="100%" height="100%" fill="{bg1}"/>
  <rect width="100%" height="56" fill="{bg2}"/>
  <rect y="56" width="100%" height="1" fill="{border_primary}"/>
  <rect y="57" width="100%" height="2" fill="{accent_500}" opacity="0.3"/>
</svg>
```

### Layout B — Header + Filters (DEFAULT)

LIGHT:
```svg
<svg viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg">
  <rect width="100%" height="100%" fill="{bg2}"/>
  <rect width="100%" height="56" fill="{white}"/>
  <rect y="56" width="100%" height="1" fill="{border_primary}"/>
  <rect y="57" width="100%" height="48" fill="{white}"/>
  <rect y="105" width="100%" height="1" fill="{border_light}"/>
</svg>
```

DARK:
```svg
<svg viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg">
  <rect width="100%" height="100%" fill="{bg1}"/>
  <rect width="100%" height="56" fill="{bg2}"/>
  <rect y="56" width="100%" height="1" fill="{border_primary}"/>
  <rect y="57" width="100%" height="2" fill="{accent_500}" opacity="0.3"/>
  <rect y="59" width="100%" height="48" fill="{bg2}"/>
  <rect y="107" width="100%" height="1" fill="{border_primary}"/>
</svg>
```

### Layout C — Header + Filters + Sidebar

LIGHT:
```svg
<svg viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg">
  <rect width="100%" height="100%" fill="{bg2}"/>
  <rect width="100%" height="56" fill="{white}"/>
  <rect y="56" width="100%" height="1" fill="{border_primary}"/>
  <rect y="57" width="100%" height="48" fill="{white}"/>
  <rect y="105" width="100%" height="1" fill="{border_light}"/>
  <rect x="0" y="106" width="200" height="{H-106}" fill="{white}"/>
  <rect x="200" y="106" width="1" height="{H-106}" fill="{border_light}"/>
</svg>
```

DARK:
```svg
<svg viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg">
  <rect width="100%" height="100%" fill="{bg1}"/>
  <rect width="100%" height="56" fill="{bg2}"/>
  <rect y="56" width="100%" height="1" fill="{border_primary}"/>
  <rect y="57" width="100%" height="2" fill="{accent_500}" opacity="0.3"/>
  <rect y="59" width="100%" height="48" fill="{bg2}"/>
  <rect y="107" width="100%" height="1" fill="{border_primary}"/>
  <rect x="0" y="108" width="200" height="{H-108}" fill="{bg2}"/>
  <rect x="200" y="108" width="1" height="{H-108}" fill="{border_primary}"/>
</svg>
```

### Layout D — Header + Sidebar

LIGHT:
```svg
<svg viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg">
  <rect width="100%" height="100%" fill="{bg2}"/>
  <rect width="100%" height="56" fill="{white}"/>
  <rect y="56" width="100%" height="1" fill="{border_primary}"/>
  <rect x="0" y="57" width="200" height="{H-57}" fill="{white}"/>
  <rect x="200" y="57" width="1" height="{H-57}" fill="{border_light}"/>
</svg>
```

DARK:
```svg
<svg viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg">
  <rect width="100%" height="100%" fill="{bg1}"/>
  <rect width="100%" height="56" fill="{bg2}"/>
  <rect y="56" width="100%" height="1" fill="{border_primary}"/>
  <rect y="57" width="100%" height="2" fill="{accent_500}" opacity="0.3"/>
  <rect x="0" y="59" width="200" height="{H-59}" fill="{bg2}"/>
  <rect x="200" y="59" width="1" height="{H-59}" fill="{border_primary}"/>
</svg>
```

### Layout E — Sidebar only (clean, minimalist)

LIGHT:
```svg
<svg viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg">
  <rect width="100%" height="100%" fill="{bg2}"/>
  <rect x="0" y="0" width="200" height="{H}" fill="{white}"/>
  <rect x="200" y="0" width="1" height="{H}" fill="{border_light}"/>
  <rect x="201" y="56" width="{W-201}" height="1" fill="{border_light}"/>
</svg>
```

DARK:
```svg
<svg viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg">
  <rect width="100%" height="100%" fill="{bg1}"/>
  <rect x="0" y="0" width="200" height="{H}" fill="{bg2}"/>
  <rect x="200" y="0" width="1" height="{H}" fill="{border_primary}"/>
  <rect x="201" y="56" width="{W-201}" height="1" fill="{border_primary}"/>
  <rect x="0" y="0" width="200" height="2" fill="{accent_500}" opacity="0.3"/>
</svg>
```

## Logo Embedding

If the user provides an SVG logo, embed it inside the background SVG using a `<g>` transform:

**Logo is ALWAYS left-aligned, never centered.** This is the professional standard.

**For ALL layouts:**
- Place logo in the top-left corner with left padding
- Left padding: 24px (sidebar layouts) or 24px (header layouts)
- Center vertically in header zone (56px): `y = (56 - rendered_height) / 2`
- Example: `<g transform="translate(24, {y}) scale({scale})"> {logo_paths} </g>`

**Scale calculation:**
- Read the logo's original width from its viewBox or width attribute
- Target max width: 90px (sidebar) or 120px (header)
- Scale = target_width / original_width
- Verify rendered height fits: original_height * scale < 40px (leave padding)

**If no logo provided:** Generate the SVG without the `<g>` logo group. The user can add their logo manually as a Power BI Image visual on top of the background.

## How to Embed in the Theme JSON

1. Build the SVG string with calculated color values (replace `{bg3}`, `{white}`, `{text_primary}`, etc.)
2. Replace `{W}` and `{H}` with the resolution dimensions
3. Calculate panel heights: `{H-64}`, `{H-120}`, `{W-208}` etc.
4. Encode the final SVG to base64
5. Place in the page background:

```json
"page": {
  "*": {
    "background": [{
      "color": { "solid": { "color": "{bg2}" } },
      "transparency": 0,
      "image": {
        "url": "data:image/svg+xml;base64,{BASE64_ENCODED_SVG}",
        "name": "brand-layout-bg",
        "scaling": "Fit"
      }
    }]
  }
}
```

**IMPORTANT**: The page background `color` should be `{bg2}` (the canvas base) — this ensures that if the SVG fails to load, the user still sees the correct canvas color as fallback.

## Resolution Dimensions Table

| Option | Width | Height | Use case |
|--------|-------|--------|----------|
| 16:9 (default) | 1280 | 720 | Standard Power BI reports |
| 16:9 HD | 1920 | 1080 | Full HD screens, embedded dashboards |
| 4:3 | 1440 | 1080 | Presentations, projectors |
| Custom | user-defined | user-defined | Special layouts |
