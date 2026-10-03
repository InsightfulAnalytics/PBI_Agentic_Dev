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

## A Visual's Own Title and Subtitle

The page title above is a textbox. A visual's title is not. Its container already carries `title`
and `subTitle` stacked, with a `divider` between them, so give a visual its title and subtitle
through those slots and never through a separate textbox placed above it or laid over its top. A
Deneb visual can use the same slots, or its spec's `title` with `subtitle` (`custom-visuals:deneb-visuals`).

The slot moves and resizes with the visual, themes from the container wildcards, travels with it
when it is copied to another page, and adds no extra `tabOrder` stop for a screen reader to
announce. A textbox above a visual does none of those, and drifts out of line the first time the
visual is nudged.

A textbox is still right for what the slots cannot do:

- the page title
- a section header over several visuals
- a callout or note
- a line that mixes formatting inside it, such as a bold run or a measure value inside static text
- text that belongs to no single visual

### When the subtitle earns its place

The default stays subtitle off; `cards-and-kpis.md` owns that rule and the command for it. Turn it
on when the visual has something to say that its title cannot carry. The commonest case is a visual
whose title asserts a finding. The same gate applies here as to a page headline, so a literal
asserted title belongs on a `narrative` page; anywhere else the title is either subject-only or
driven by a measure that recomputes the claim (the insight test in `SKILL.md`). The finding goes in
`title`, and what is on screen (measure, grain, period) goes in `subTitle`, so the claim does not
have to carry the naming as well. A one-line reading key ("Number = weeks on promotion. Highlight =
peak band.") also belongs in the subtitle, though a form that needs one is paying the cost
`chart-selection.md` counts against leaving the default vocabulary.

```bash
pbir visuals title "Page.Page/Hero.Visual" --text "Additions have halved since 2019"
pbir visuals subtitle "Page.Page/Hero.Visual" --text "Titles added per year, 2015 to 2024" --show
pbir visuals divider "Page.Page/Hero.Visual" --show
```

An apostrophe in that text has to be passed doubled (`--text "Each store''s sales"`): pbir writes the
text into a single-quoted literal without escaping it (`reports:pbir-cli` `references/cli-traps.md`).
`pbir add title` and `pbir add subtitle` do something else: they add page-level textboxes, and never
set a visual's title. The PBIR the commands write, for hand-checking a diff, is in `pbip:pbir-format`
`references/visual-container-formatting.md`, "Title and subtitle text".

A subtitle is one paragraph. It is also usually the smallest text on the page, so it stays at the
12pt floor in `SKILL.md` or above, in the theme and in any per-visual override.

### Style the slots once, in the theme

Set the title and subtitle type in the theme's `visualStyles["*"]["*"]`, not per visual. When only
some visuals carry a title, set `show: false` there too, so only the visuals that set `show: true`
get one:

```json
"title": [{ "show": false, "fontFamily": "Segoe UI Semibold", "fontSize": 18,
            "fontColor": { "solid": { "color": "#252423" } }, "alignment": "left", "titleWrap": true }],
"subTitle": [{ "show": false, "fontFamily": "Segoe UI", "fontSize": 12,
               "fontColor": { "solid": { "color": "#605E5C" } }, "alignment": "left", "titleWrap": true }]
```

A visual left untitled that way needs alt text (see "Title visibility and alt text" below), or a
screen reader announces it by its auto name. The CLI sets them one property at a time:

```bash
pbir theme set-formatting "Report.Report" "*.*.subTitle.fontSize" --value 12
```

### Moving an existing title textbox into the visual

1. Copy the textbox's text into the visual's `title` (and `subTitle`) with `pbir visuals title` and
   `pbir visuals subtitle`, then delete the textbox with `pbir rm "<Textbox>.Visual" -f`.
2. Move the visual up to the textbox's old `y` (`pbir visuals position`), so the page keeps its
   rhythm.
3. Move it left or right to the textbox's `x`, so the new title starts where the old one did. The
   visual's body then sits at that `x` too, which can leave the left and right margins inside a card
   unequal: accept that, or move the card's accent or background shape to match.
4. A two-paragraph textbox becomes one run of subtitle text. Rewrite it as one or two short
   sentences rather than joining the paragraphs.
5. Alt text stays where it was, in `visualContainerObjects.general.altText`. Moving the title does
   not touch it.

### Checking a finished page

`scripts/find_title_textboxes.py` flags every textbox that acts as one visual's title: it ends at
most 24px above a single data visual (not a shape, image or button) and spans at least half that
visual's width, or it overlaps the visual's top edge. The overlap case matters: a check that looks
only above the visual misses the textbox laid over the top. A textbox above two or more visuals is a
section header and is not flagged. A page title over a page's one main visual looks the same, so the
highest textbox on a page is listed but marked as a likely page title, and does not fail the run.

```bash
python scripts/find_title_textboxes.py "Report.Report"          # exit 1: a textbox to move
python scripts/find_title_textboxes.py "Report.Report" --json
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

Read a visual's title, with where each setting comes from:
```bash
pbir visuals format "Report.Report/MyPage.Page/Visual.Visual" -p title
```

### Title visibility and alt text

A hidden title (`title.show=false`) makes the reader fall back to a worthless auto name ("chart 4"). If the title is hidden for layout reasons, supply descriptive alt text on the visual's `visualContainerObjects.general[].properties.altText` instead. Writing it under `objects.general` is valid JSON that no screen reader reads.

Decorative textboxes (section headers) should be removed from the tab order (set `tabOrder` to -1) so readers skip them rather than announcing them as navigation stops.

## Best Practices

1. **Consistent positioning** - Same x, y across all pages
2. **Consistent sizing** - Same width, height, font size
3. **Descriptive text, unless the claim is pinned** - Name the subject and spell out abbreviations. A literal headline states the finding only on a `narrative` page (see `page-shapes.md`), because the other four shapes are re-filtered surfaces where fixed words go stale on the first slicer click. A measure-driven title recomputes with the filters, so it may assert on any shape; the two routes are in `SKILL.md`, under the insight test
4. **Avoid redundancy** - Don't repeat report name if obvious
5. **Consider mobile** - Ensure readable on smaller screens; see `mobile.md`
