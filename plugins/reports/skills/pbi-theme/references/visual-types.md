# Visual Types Reference

Complete list of all 27 visual types with their presets, textClasses with font scaling, color replacement map for visualStyles, named shape definitions, top-level JSON structure, and ThemeDataColor expression rules.

## Top-Level JSON Structure

```json
{
  "name": "{Brand Name} — {Mood}",
  "dataColors": ["{8 hex colors}"],
  "background": "{bg1}",
  "foreground": "{text_primary}",
  "tableAccent": "{border_primary}",
  "firstLevelElements": "{text_primary}",
  "secondLevelElements": "{text_secondary}",
  "thirdLevelElements": "{text_muted}",
  "secondaryBackground": "{bg2}",
  "good": "{good}",
  "bad": "{bad}",
  "neutral": "{warn}",
  "maximum": "{accent_500}",
  "minimum": "{bg1}",
  "textClasses": { ... },
  "visualStyles": { ... }
}
```

## textClasses (13 classes)

**Font sizes scale with resolution.** Larger resolutions need slightly larger fonts to maintain readability:

| Text Class | 1280x720 | 1920x1080 | 1440x1080 |
|-----------|----------|-----------|-----------|
| callout (KPI values) | 21pt | 28pt | 24pt |
| title | inherit | inherit | inherit |
| largeLabel | 12pt | 14pt | 13pt |
| largeTitle | 12pt | 14pt | 13pt |
| Hero Section title | 36pt | 48pt | 42pt |
| Hero Section subtitle | 15pt | 18pt | 16pt |
| Section Header | 13pt | 15pt | 14pt |
| Section Header Large | 18pt | 22pt | 20pt |
| Report Header title | 18pt | 22pt | 20pt |
| Report Header subtitle | 13pt | 15pt | 14pt |
| Heading 1 | 27pt | 34pt | 30pt |
| Heading 2 | 22.5pt | 28pt | 25pt |
| Heading 3 | 18pt | 22pt | 20pt |
| Heading 4 | 15pt | 18pt | 16pt |

Scale formula: `size_new = size_base * (resolution_height / 720)`. Round to nearest 0.5pt.

Generate ALL 13 text classes. The 4 primary classes must always have explicit values:

```json
"textClasses": {
  "callout": {
    "color": "{text_primary}",
    "fontFace": "{primary_font}",
    "fontSize": 21,
    "fontWeight": "700"
  },
  "title": {
    "color": "{text_primary}",
    "fontFace": "{primary_font}",
    "fontWeight": "600"
  },
  "header": {
    "fontFace": "{primary_font}"
  },
  "label": {
    "fontFace": "{primary_font}"
  },
  "largeLabel": {
    "color": "{text_secondary}",
    "fontFace": "{primary_font}",
    "fontSize": 12
  },
  "largeTitle": {
    "color": "{text_primary}",
    "fontFace": "{primary_font}",
    "fontSize": 12,
    "fontWeight": "600"
  },
  "lightLabel": {
    "color": "{text_secondary}",
    "fontFace": "{primary_font}"
  },
  "smallLabel": {
    "fontFace": "{primary_font}"
  },
  "boldLabel": {
    "fontFace": "{primary_font}"
  },
  "semiboldLabel": {
    "fontFace": "{primary_font}"
  },
  "dataTitle": {
    "fontFace": "{primary_font}"
  },
  "smallDataLabel": {
    "fontFace": "{primary_font}"
  },
  "largeLightLabel": {
    "fontFace": "{primary_font}"
  },
  "smallLightLabel": {
    "color": "{text_secondary}",
    "fontFace": "{primary_font}"
  }
}
```

## Color Replacement Map for visualStyles

**Color replacement rules — apply throughout the ENTIRE visualStyles tree:**

| Base hex value | Replace with |
|--------------------------|-------------|
| `#fcfcfd` | `{bg1}` |
| `#f9f9fb` | `{bg2}` |
| `#f0f0f3` | `{bg3}` |
| `#ffffff` | `{white}` |
| `#FFFFFF` | `{white}` |
| `#1c2024` | `{text_primary}` |
| `#14171c` | `{text_black}` |
| `#14171C` | `{text_black}` |
| `#3c4653` | `{text_dark}` |
| `#3C4653` | `{text_dark}` |
| `#60646c` | `{text_secondary}` |
| `#80838d` | `{text_muted}` |
| `#8390a2` | `{disabled_text}` |
| `#cdced6` | `{border_primary}` |
| `#d9d9e0` | `{border_subtle}` |
| `#e0e1e6` | `{border_light}` |
| `#e0e3e8` | `{border_chrome}` |
| `#E0E3E8` | `{border_chrome}` |
| `#a2acb9` | `{border_disabled}` |
| `#A2ACB9` | `{border_disabled}` |
| `#b9bbc6` | `{shadow_color}` |
| `#3b82f6` | `{accent_500}` |
| `#1d4ed8` | `{accent_700}` |
| `#60a5fa` | `{accent_400}` |
| `#bfdbfe` | `{accent_200}` |
| `#eff6ff` | `{accent_50}` |
| `#605e5c` | `{ref_line}` |
| `#ef4444` | `{bad}` |
| `#22c55e` | `{good}` |
| `#f59e0b` | `{warn}` |
| `#505d6f` | `{text_dark}` |
| `#505D6F` | `{text_dark}` |
| `#f5f7f8` | `{bg2}` |
| `#F5F7F8` | `{bg2}` |
| `#eff1f3` | `{bg3}` |

**Structural properties** (padding, border.radius, show/hide, etc.) use the mood table from layout-templates.md.

## Named Shapes

Generate ALL named shape presets with brand colors. Key shapes:

- **Brand Color**: `fill.fillColor` -> `{accent_500}`
- **Badge**: background -> `{accent_50}`, border -> `{accent_400}`, text -> `{accent_700}`, shadow -> `{accent_400}`
- **Feature Section**: title fontColor -> `{accent_500}`, subtitle fontColor -> `{text_primary}`
- **Nav Bar BG**: background -> `{bg3}`, title background -> `{bg1}`
- **Background Tertiary**: color -> `{bg3}`
- **Background Secondary**: color -> `{bg2}`
- **Dividers**: outline lineColor -> `{border_primary}`
- **Report Header / Section Header**: Use text hierarchy colors
- **Accent Bar Top**: `fill` -> `{accent_500}`, no border, no outline, zero padding. Thin horizontal bar for top decoration.
- **Accent Bar Left**: Same as Top but used vertically. `fill` -> `{accent_500}`.
- **Info Card**: background -> `{accent_50}`, border -> `{accent_400}`, title color -> `{accent_700}`, subtitle -> `{text_secondary}`. Soft branded callout card.
- **Dark Card**: background -> `{text_primary}`, title color -> `{white}`, subtitle -> `{text_muted}`. High contrast inverted card.
- **Metric Highlight**: background -> `{white}`, left outline -> `{accent_500}` weight 3, border -> `{border_light}`. Card with accent left bar for KPI emphasis.
- **Separator Accent**: line shape, outline -> `{accent_500}` weight 2. Colored divider.
- **Separator Light**: line shape, outline -> `{border_light}` weight 0.5. Subtle divider.
- **Accent Outline** (actionButton): white fill, accent border, accent text, hover -> accent_50.
- **Dark** (actionButton): text_primary fill, white text, hover -> slightly lighter.

## Complete Visual Types to Include

Generate visualStyles for ALL of these visual types (generate the complete structure with color/layout replacements):

```
* (global wildcard)
kpi (*, Basic)
map (*)
page (*)
group (*)
image (*)
shape (*, Nav Bar BG, Brand Color, Hero Section, Report Header, Section Header,
       Feature Section, Divider - Vertical, Background Tertiary, Background Secondary,
       Divider - Horizontal, Section Header Large, Report Header Inversed, Badge,
       Accent Bar Top, Accent Bar Left, Info Card, Dark Card, Metric Highlight,
       Separator Accent, Separator Light)
slicer (*)
tableEx (*, Table Airy, Table Compact)
textbox (*, Muted, Heading 1, Heading 2, Heading 3, Heading 4, Text Secondary)
barChart (*)
areaChart (*)
filledMap (*)
lineChart (*, Bold Data color 1)
cardVisual (*)
donutChart (*)
listSlicer (*)
pivotTable (*, Colors, Financials)
columnChart (*)
actionButton (*, Icon, Brand, Brand Soft, Placeholder, Subtle Shadow, Surface, Accent Outline, Dark)
multiRowCard (*)
pageNavigator (*, Underline, Default Rounded, Sidebar Navigation, Sidebar Navigation 1)
waterfallChart (*)
bookmarkNavigator (*, Tabs, Underline, Default Rounded, Sidebar Navigation, Sidebar Navigation 1)
advancedSlicerVisual (*, Grid, Stacked Cards, Horizontal Filter)
clusteredColumnChart (*)
```

## ThemeDataColor Expressions

Maintain ALL ThemeDataColor expressions as-is. They reference `dataColors` by index, and since we generate the dataColors array, the expressions automatically point to the right colors. Do NOT replace ThemeDataColor expressions with hardcoded hex values.

The expressions look like this — keep them exactly:

```json
{
  "expr": {
    "ThemeDataColor": {
      "ColorId": 2,
      "Percent": 0
    }
  }
}
```
