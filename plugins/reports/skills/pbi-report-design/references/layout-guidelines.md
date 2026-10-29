# Layout Guidelines

Detailed specifications for Power BI report page layouts.

## Page Dimensions

### Standard Page (16:9)

```
Width:  1280px
Height: 720px
```

### Alternative Sizes

| Type | Width | Height | Use Case |
|------|-------|--------|----------|
| Standard | 1280 | 720 | Desktop (PBI default) |
| Full HD | 1920 | 1080 | High-resolution displays, presentations |
| Letter | 816 | 1056 | Print, portrait |
| 4:3 | 1280 | 960 | Legacy displays |
| Custom | Variable | Variable | Specific requirements |

## Margins and Gaps

Margin, gap and grid values come from the design system in use; this skill does not set them (`SKILL.md`, *Standards this skill does not set*). On a fixed PBIR canvas, white space is spent explicitly through the gaps between `position` rectangles, so place by arithmetic, not by eye:

- Reserve the margin first: usable area = `canvas - 2*margin`, on all four sides
- Padding (inside a visual container) and gaps (between visual containers) are different budgets controlled in different places; tightening one does not buy the other

## Visual Zones

### Zone Layout (Detail Gradient)

```
+------------------+------------------+
|       ZONE 1     |      ZONE 1      |
|   KPIs / Cards   |   KPIs / Cards   |  (Important, summary)
+------------------+------------------+
|                                     |
|              ZONE 2                 |
|        Charts / Analysis            |  (Context, trends)
|                                     |
+------------------+------------------+
|                                     |
|              ZONE 3                 |
|        Tables / Details             |  (Drill-down, detail)
|                                     |
+------------------+------------------+
```

### Zone Specifications

| Zone | Purpose | Visual Types |
|------|---------|--------------|
| 1 | Summary | Cards, KPIs, Slicers |
| 2 | Analysis | Charts, Maps |
| 3 | Detail | Tables, Matrix, Lists |

Zone heights split the page's real height inside its margins: read `page.height` first (*Check Page Size Before Modifying* in `SKILL.md`), since a 720px page cannot hold heights sized for 1080.

## Common Visual Sizes

### Cards/KPIs

```
Width:  200-300px
Height: 100-150px
```

### Charts

```
Small:  Width: 400px,  Height: 300px
Medium: Width: 600px,  Height: 400px
Large:  Width: 900px,  Height: 500px
Full:   Width: page width minus both margins, Height: 500px
```

### Tables

```
Width:  Variable (fill available space)
Height: 300-500px
```

### Slicers

```
Horizontal: Width: 200-400px, Height: 60-80px
Vertical:   Width: 150-200px, Height: 200-400px
```

## Title Area

### Page Title Specifications

```
Position: top-left, at the page margin
Width:    400-600px
Height:   48-64px
```

### Subtitle (Optional)

```
Position: below the title
Width:    400-600px
Height:   32-48px
```

## Sample Layouts

### Dashboard Layout

```
+--------------------------------------------------+
|  Title                            [Slicer]       |
+--------+--------+--------+--------+--------------+
|  KPI   |  KPI   |  KPI   |  KPI   |              |
+--------+--------+--------+--------+              +
|                         |                        |
|     Line Chart          |     Bar Chart          |
|                         |                        |
+-------------------------+------------------------+
|                                                  |
|                    Table                         |
|                                                  |
+--------------------------------------------------+
```

### Analysis Layout

```
+--------------------------------------------------+
|  Title                                           |
+-------------------------+------------------------+
|                         |  Slicer                |
|                         +------------------------+
|     Main Chart          |  Supporting Chart 1    |
|                         +------------------------+
|                         |  Supporting Chart 2    |
+-------------------------+------------------------+
|  Detail Table or Additional Analysis             |
+--------------------------------------------------+
```

### KPI Dashboard

```
+--------------------------------------------------+
|  Title                            [Date Slicer]  |
+--------+--------+--------+--------+--------------+
| Big    | Big    | Big    | Big    |              |
| KPI    | KPI    | KPI    | KPI    |              |
+--------+--------+--------+--------+--------------+
|                                                  |
|           Trend Chart (Sparklines)               |
|                                                  |
+--------------------------------------------------+
|                                                  |
|           Comparison Table                       |
|                                                  |
+--------------------------------------------------+
```

## Positioning Rules

### Alignment

1. **Vertical alignment:** Left edges of visuals in same column should align
2. **Horizontal alignment:** Top edges of visuals in same row should align

### Placing a Row

Gaps that are meant to be the same and differ by a few pixels read as misalignment, even when visuals are technically positioned correctly. Calculate positions rather than nudging them.

When calculating positions for a row of visuals:

1. Take the page margin and the gap between visuals from the design system
2. Calculate available content width: `page_width - (2 * margin)`
3. Calculate total gap space: `gap * (num_visuals - 1)`
4. Distribute remaining width proportionally: `(content_width - total_gaps) / num_visuals`

Example for 4 equal visuals on a 1280px page with 24px margins and 16px gaps:
```
content_width = 1280 - 48 = 1232
total_gaps = 16 * 3 = 48
visual_width = (1232 - 48) / 4 = 296

x positions: 24, 336, 648, 960
```

For visuals of different widths (e.g., a KPI + a chart sharing a row), each gap is the value the design system sets for that relation (within a group or between groups). Verify by checking `visual_B.x - (visual_A.x + visual_A.width)` for every adjacent pair.

**Anti-pattern**: Visuals that are close but not quite aligned, or two gaps meant to be the same that differ (16px against 24px). This is visually jarring even at small differences (4-8px).

### Vertical Column Alignment Across Rows (Critical)

When visuals in different rows share a vertical split (e.g., two charts side-by-side below two KPI pairs), the column boundaries must align vertically across rows. The gap between the left visual and right visual in row 2 must line up with the gap in row 1.

```
WRONG (misaligned vertical split):
+------ 600px ------+--16--+---- 600px ----+   Row 1
+------- 616px ------+--16--+--- 584px ----+   Row 2
                     ^       ^
                     These don't align -- looks sloppy

RIGHT (aligned vertical split):
+------ 600px ------+--16--+---- 600px ----+   Row 1
+------ 600px ------+--16--+---- 600px ----+   Row 2
                     ^
                     Same column edge in both rows
```

When calculating (a 1280px page with 32px margins): if row 1 has visual A ending at x=632 and visual B starting at x=648 (16px gap), row 2 must use the same split: visual C ends at x=632, visual D starts at x=648. The widths of C and D will differ from A and B, but the gap position is identical.

This applies to any multi-row layout where visuals share implicit column boundaries. Even if the visuals are different types and sizes, the vertical gutters must form continuous lines from top to bottom of the page.

### Z-Order

- Base visuals: z = 0-999
- Overlays/highlights: z = 1000-1999
- Tooltips/popups: z = 2000+

## Performance Considerations

Opening a page refreshes every visible visual; each emits at least one DAX query. Parallelism is capped (DirectQuery default 10 concurrent connections), so latency grows non-linearly past that cap. Visual COUNT is a proxy; query COST per visual is the actual driver. 12 cheap card visuals are fine; 8 matrices with totals and measure filters may not be.

Visuals that emit more than one query per page load (multipliers):
- Tables/matrices with totals or subtotals (one query per band; DistinctCount and Median are worst)
- Measure filters (two queries)
- Top N filters (two queries; can hit the 1M-row intermediate limit in DirectQuery)
- Field parameters (an extra evaluated-parameters phase)
- Custom/Deneb/Python/R visuals (render phase dominates)

### Exceptions

These do not emit queries and do not count toward visual density:
- Textboxes
- Images
- Shapes
- Buttons
