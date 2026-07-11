# Color Generation Engine

Complete algorithms for generating the 37-color semantic map, data color palette, and filter pane colors from the client's brand inputs (primary, secondary, tertiary hex colors).

## Convert Input to HSL

Convert the primary hex to HSL(H, S, L). All palette generation works in HSL space.

## Generate the 37-Color Semantic Map

From the primary and secondary colors, generate ALL 37 colors needed by the Power BI theme. Every color has a specific semantic role.

**IMPORTANT**: Power BI only accepts 6-digit hex strings (`#RRGGBB`). No alpha, no rgb(), no CSS variables.

### BACKGROUNDS (4 colors)

Calculate from primary hue with very low saturation. The background mode (`light` or `dark`) fundamentally changes these:

**LIGHT MODE:**

| Role | ID | Calculation | Example |
|------|----|-------------|---------|
| Main background | `bg1` | HSL(H_primary, 3%, 99%) | `#fcfcfd` |
| Secondary background | `bg2` | HSL(H_primary, 4%, 98%) | `#f9f9fb` |
| Tertiary background / outspace | `bg3` | HSL(H_primary, 5%, 95%) | `#f0f0f3` |
| Surface white | `white` | Always `#ffffff` | `#ffffff` |

**DARK MODE:**

| Role | ID | Calculation | Example |
|------|----|-------------|---------|
| Main background | `bg1` | HSL(H_primary, 8%, 8%) | `#141618` |
| Secondary background | `bg2` | HSL(H_primary, 7%, 12%) | `#1e2023` |
| Tertiary background / outspace | `bg3` | HSL(H_primary, 6%, 16%) | `#272a2d` |
| Surface | `white` | HSL(H_primary, 6%, 20%) | `#303336` |

### TEXT HIERARCHY (5 colors)

**LIGHT MODE** — dark text on light backgrounds:

| Role | ID | Calculation |
|------|----|-------------|
| Near-black headers | `text_black` | HSL(H_primary, 15%, 9%) |
| Primary text / foreground | `text_primary` | HSL(H_primary, 12%, 12%) |
| Dark text (filters) | `text_dark` | HSL(H_primary, 14%, 18%) |
| Secondary text | `text_secondary` | HSL(H_primary, 5%, 40%) |
| Muted text | `text_muted` | HSL(H_primary, 3%, 53%) |

**DARK MODE** — light text on dark backgrounds:

| Role | ID | Calculation |
|------|----|-------------|
| Near-white headers | `text_black` | HSL(H_primary, 5%, 97%) |
| Primary text / foreground | `text_primary` | HSL(H_primary, 5%, 93%) |
| Light text (filters) | `text_dark` | HSL(H_primary, 4%, 85%) |
| Secondary text | `text_secondary` | HSL(H_primary, 4%, 60%) |
| Muted text | `text_muted` | HSL(H_primary, 3%, 45%) |

### BORDERS & CHROME (6 colors)

Neutral tones derived from primary hue:

| Role | ID | Calculation |
|------|----|-------------|
| Primary border / tableAccent | `border_primary` | HSL(H_primary, 4%, 82%) |
| Subtle border | `border_subtle` | HSL(H_primary, 3%, 87%) |
| Light gridline | `border_light` | HSL(H_primary, 4%, 89%) |
| Chrome border | `border_chrome` | HSL(H_primary, 6%, 89%) |
| Disabled border | `border_disabled` | HSL(H_primary, 8%, 69%) |
| Drop shadow | `shadow_color` | HSL(H_primary, 5%, 76%) |

### ACCENT FAMILY (5 colors — from SECONDARY color)

The accent family drives badges, buttons, interactive highlights, and brand emphasis. It is ALWAYS derived from the SECONDARY (accent) color, since that is the client's chosen highlight color:

| Role | ID | Calculation |
|------|----|-------------|
| Accent tint background | `accent_50` | HSL(H_secondary, S*0.9, 97%) — light mode / HSL(H_secondary, S*0.3, 15%) — dark mode |
| Accent light border | `accent_200` | HSL(H_secondary, S*0.85, 87%) — light mode / HSL(H_secondary, S*0.5, 25%) — dark mode |
| Accent medium | `accent_400` | HSL(H_secondary, S*0.8, 65%) |
| Accent main | `accent_500` | The SECONDARY color itself |
| Accent dark / pressed | `accent_700` | HSL(H_secondary, S*1.1, L*0.65) |

The accent family is used for:
- Badge background (`accent_50`), border (`accent_400`), text (`accent_700`)
- Brand button fill (`accent_500`), hover (`accent_700`)
- Feature section title highlight
- Selection states in navigators

### DISABLED (2 colors)

| Role | ID | Calculation |
|------|----|-------------|
| Disabled text | `disabled_text` | HSL(H_primary, 7%, 58%) |
| Reference line | `ref_line` | HSL(H_primary, 2%, 37%) |

### SEMANTIC STATUS (3 colors)

| Role | ID | Default | Notes |
|------|----|---------|-------|
| Good / positive | `good` | `#22c55e` | Keep green family, adjust if primary is green |
| Bad / negative | `bad` | `#ef4444` | Keep red family, adjust if primary is red |
| Neutral / warning | `warn` | Use secondary color if warm, else `#f59e0b` | |

### DATA COLORS (8 colors)

This is the MOST VISIBLE part of the theme. The 8 colors MUST be rooted in the client's actual brand colors, NOT random rainbow colors.

**Algorithm — Brand-Anchored Palette:**

The first 3 colors come DIRECTLY from the client's input:

```
dataColor[0] = SECONDARY color (the accent — most used in charts)
dataColor[1] = TERTIARY color (support color — second most used)
dataColor[2] = PRIMARY color (if light enough for charts, else a lighter shade of primary at L=45-55%)
```

The remaining 5 are DERIVED from the client's 3 colors by:

```
dataColor[3] = Shift secondary hue +40°, keep similar saturation/lightness
dataColor[4] = Shift tertiary hue -40°, keep similar saturation/lightness
dataColor[5] = Midpoint blend of secondary + tertiary (average hue, S, L)
dataColor[6] = Shift secondary hue +120°, desaturate 15%
dataColor[7] = Shift tertiary hue +120°, desaturate 15%
```

**Rules:**
- All 8 colors must be perceptually distinct (no two within 25 degrees hue AND similar lightness)
- If any derived color clashes with another, shift its hue by +30 degrees until distinct
- Maintain consistent lightness band: L=45-65% for light mode, L=55-75% for dark mode
- For dark mode: all dataColors must be visible on dark backgrounds (L >= 50%)
- For light mode: all dataColors must be visible on light backgrounds (L <= 65%)
- The palette should feel COHESIVE — like it belongs to one brand, not a rainbow
- Test: the first 3 colors should be immediately recognizable as the client's brand

## Filter Pane Colors (4 colors — derived, subtle)

These are semi-independent from the main palette:

| Role | Calculation |
|------|-------------|
| Filter bg | Slightly lighter than bg2 |
| Filter text | Slightly darker than text_dark |
| Filter checkbox area | Same as bg2 |
| Outspace pane text | Same as text_secondary, darker |
