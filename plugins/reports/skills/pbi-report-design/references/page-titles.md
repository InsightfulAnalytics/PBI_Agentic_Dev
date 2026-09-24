# Page Titles

Guidelines for implementing page titles in Power BI reports.

## Why Page Titles Matter

- Provide context for report consumers
- Improve navigation and orientation
- Support accessibility (screen readers)
- Professional appearance

## Implementation Options

### Option 1: Textbox Visual (Recommended)

```json
{
  "name": "title-guid",
  "position": {
    "x": 24,
    "y": 24,
    "z": 1000,
    "width": 500,
    "height": 48
  },
  "visual": {
    "visualType": "textbox",
    "objects": {
      "general": [{
        "properties": {
          "paragraphs": {
            "expr": {
              "Literal": {
                "Value": "[{\"textRuns\":[{\"value\":\"Sales Overview\",\"textStyle\":{\"fontSize\":\"24pt\",\"fontWeight\":\"bold\"}}]}]"
              }
            }
          }
        }
      }]
    },
    "visualContainerObjects": {
      "background": [{"properties": {"show": {"expr": {"Literal": {"Value": "false"}}}}}],
      "border": [{"properties": {"show": {"expr": {"Literal": {"Value": "false"}}}}}],
      "title": [{"properties": {"show": {"expr": {"Literal": {"Value": "false"}}}}}]
    }
  }
}
```

### Option 2: Shape with Text

Use a rectangle shape with text overlay for styled backgrounds.

### Option 3: Card Visual

For dynamic titles that include measure values.

## Title Specifications

### Standard Title

```
Position:  x: 24, y: 24
Size:      width: 400-600px, height: 48-64px
Font:      24pt, bold
Color:     Dark gray (#333) or theme foreground
Alignment: Left
```

### With Subtitle

```
Title:    x: 24, y: 24, height: 40px, font: 24pt bold
Subtitle: x: 24, y: 64, height: 32px, font: 14pt regular
```

### Full-Width Title Bar

```
Position:  x: 0, y: 0
Size:      width: 1920px, height: 72px
Background: Theme color or gradient
```

## Dynamic Titles

### Include Current Filter Context

```dax
Title Text =
"Sales by Region - " &
SELECTEDVALUE('Date'[Year], "All Years")
```

### Include Last Refresh

```dax
Title Text =
"Sales Dashboard - Updated: " &
FORMAT(MAX('Refresh Log'[Timestamp]), "MMM DD, YYYY")
```

## Textbox Paragraph Structure

Textbox content uses a specific JSON structure:

```json
{
  "paragraphs": {
    "expr": {
      "Literal": {
        "Value": "[{\"textRuns\":[{\"value\":\"Title Text\",\"textStyle\":{\"fontSize\":\"24pt\",\"fontWeight\":\"bold\",\"color\":\"#333333\"}}]}]"
      }
    }
  }
}
```

### Multiple Runs (Mixed Formatting)

```json
[{
  "textRuns": [
    {"value": "Sales ", "textStyle": {"fontSize": "24pt"}},
    {"value": "Overview", "textStyle": {"fontSize": "24pt", "fontWeight": "bold"}}
  ]
}]
```

Per-run styling is what lets the accent follow the words. Where one focal series carries the accent
hue, put the noun naming that series in its own run and give it the same hue through
`textStyle.color`; a title whose accented noun and accented marks disagree points the reader at the
wrong marks. `textStyle.color` takes a literal hex, not a `ThemeDataColor`, so it is an inline-hex
exception to `anti-patterns.md` and has to be re-checked on a re-theme.

### Multiple Paragraphs

```json
[
  {"textRuns": [{"value": "Main Title", "textStyle": {"fontSize": "24pt"}}]},
  {"textRuns": [{"value": "Subtitle here", "textStyle": {"fontSize": "14pt"}}]}
]
```

## Creating Title Textboxes

```bash
pbir add title "Report.Report/Page.Page" "Overview" --width 500
```

Use `pbir add subtitle` when the page genuinely needs a second line. Never hand-author the
textbox JSON.

## The Visual Container's Second Text Slot

The page title above is a textbox. A visual does not need one: its container already carries
`title` and `subTitle` stacked, with a `divider` between them, so the two-layer title is native
rather than a floating textbox laid on top.

The default stays subtitle off; `cards-and-kpis.md` owns that rule and the command for it. Turn it
on for the one case that earns it: a visual whose title asserts a finding. The same gate applies
here as to a page headline, so a literal asserted title belongs on a `narrative` page; anywhere
else the title is either subject-only or driven by a measure that recomputes the claim (the
insight test in `SKILL.md`). The finding goes in `title`, and what is on screen (measure, grain,
period) goes in `subTitle`, so the claim does not have to carry the naming as well.

```bash
pbir visuals title "Page.Page/Hero.Visual" --text "Additions have halved since 2019"
pbir visuals subtitle "Page.Page/Hero.Visual" --text "Titles added per year, 2015 to 2024" --show
pbir visuals divider "Page.Page/Hero.Visual" --show
```

Prefer the slot over a second textbox: it moves and resizes with the visual, it themes from the
container wildcards, and it adds no extra `tabOrder` stop for a screen reader to announce. Set its
type size in the theme, not per visual:

```bash
pbir theme set-formatting "Report.Report" "*.*.subTitle.fontSize" --value 11
```

## Theme Considerations

### Disable Container Properties

For titles, typically disable:

- Background
- Border
- Title (visual title)
- Drop shadow

### In Theme Wildcards

```json
"visualStyles": {
  "textbox": {
    "*": {
      "title": [{"show": false}],
      "background": [{"show": false}],
      "border": [{"show": false}],
      "dropShadow": [{"show": false}]
    }
  }
}
```

## Accessible Titles

A screen reader speaks a visual's title and type before any alt text. This means an acronym or jargon title is unintelligible spoken aloud; the accessibility constraint is stronger than the visual-design constraint.

- Spell out the subject ("Current year sales vs prior year", not "CY Sales vs PY")
- Reserve abbreviations for axis labels inside the chart, not the title
- Do not encode the chart type in the title; the reader announces it already
- A dynamic measure-bound title is spoken on every filter change; keep it a plain readable phrase with no glyphs or unit-suffix soup

Scan titles across a page:
```bash
pbir visuals format "MyPage/*" -p title.text
```

### Title visibility and alt text

A hidden title (`title.show=false`) makes the reader fall back to a worthless auto name ("chart 4"). If the title is hidden for layout reasons, supply descriptive alt text on the visual's `visualContainerObjects.general[].properties.altText` instead. Writing it under `objects.general` is valid JSON that no screen reader reads.

Decorative title textboxes (section headers, visual labels) should be removed from the tab order (set `tabOrder` to -1) so readers skip them rather than announcing them as navigation stops.

## Best Practices

1. **Consistent positioning** - Same x, y across all pages
2. **Consistent sizing** - Same width, height, font size
3. **Descriptive text, unless the claim is pinned** - Name the subject and spell out abbreviations. A literal headline states the finding only on a `narrative` page (see `page-shapes.md`), because the other four shapes are re-filtered surfaces where fixed words go stale on the first slicer click. A measure-driven title recomputes with the filters, so it may assert on any shape; the two routes are in `SKILL.md`, under the insight test
4. **Avoid redundancy** - Don't repeat report name if obvious
5. **Consider mobile** - Ensure readable on smaller screens; see `mobile.md`
