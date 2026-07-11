---
name: pbi-theme
version: 26.25
description: Generate complete Power BI Desktop theme files from brand colors. Creates production-ready JSON themes with branded canvas backgrounds, CSS design tokens, DAX HTML visual examples, and A4 PDF design system documents. Runs standalone or chained with pbi-lifecycle (auto-saves into the client's Global Theme/pbi-theme/ folder when invoked inside a lifecycle-managed project). Use when user asks to create a Power BI theme, PBI theme, dashboard theme, report branding, or Power BI color palette. Triggers on "create theme", "Power BI branding", "theme generator", "branded dashboard". Supports light/dark mode, 5 canvas layouts with logo embedding, WCAG accessibility, and 21 shape presets. This skill GENERATES a bespoke theme from brand colors — for BROWSING/APPLYING an existing preset theme from a gallery use power-bi-theme, and for editing/enforcing a theme on a live report use reports:modifying-theme-json. Do NOT use for general web design, CSS frameworks, or non-Power BI visualization tools.
license: MIT
metadata:
  author: Gus Bavia
  version: 1.1.0
  category: data-visualization
  tags: [power-bi, theme, design-system, data-visualization, branding]
  companions: [pbi-lifecycle, pbi-project-hub]
  support: https://linkedin.com/in/gusbavia
---

# Power BI Theme Generator

Generate a complete Power BI Desktop theme JSON file (~5800 lines) from the client's brand colors. The output is a production-ready `.json` theme importable via View > Themes > Browse in Power BI Desktop, plus a design system PDF, CSS tokens, and DAX HTML visual examples.

Input: **$ARGUMENTS**

## 0. Mode triage — ALWAYS THE FIRST QUESTION

This skill runs in one of three modes. Ask the user up front, before the colour/layout questionnaire. Do not skip — the mode decides where the output files land.

```
This theme is for:
  1. Standalone — I'll save the output where you tell me (default: current working directory)
  2. pbi-lifecycle project — output goes to <Client>/Global Theme/pbi-theme/
  3. pbi-project-hub engagement — output goes to Clients/{name}/02_Design_System/

Type 1, 2, or 3.
```

If the user's invocation already implies the mode (e.g. they pasted a path that contains `Global Theme/`, or they said "use the lifecycle theme path"), the agent may infer the mode and skip the prompt.

### Mode 1 · Standalone

- Ask the user where to save the files (default: current working directory).
- Use the brand name they provide for file naming.
- Output goes flat into the chosen folder.

### Mode 2 · pbi-lifecycle integration

- Ask: *"Paste any path inside the lifecycle-managed client (the project folder, the Power BI Repository folder, or the client root itself). I'll find `Global Theme/` automatically."*
- Resolve the **client root** by walking up from the path the user provided until you find a sibling folder named `Global Theme` (or `ClientTheme` for older lifecycle versions). The client root is the folder that contains both `Global Theme/` and `Power BI Repository/`.
- If `Global Theme/` is not found within 5 parent levels of the provided path, stop and ask the user to confirm the client root manually. Do not guess.
- Inside `Global Theme/`, the lifecycle skill creates three subfolders: `logo/`, `brand-guideline/`, `pbi-theme/`. The output of THIS skill goes into `Global Theme/pbi-theme/`, organized in four subfolders by file category:

  ```
  Global Theme/pbi-theme/
    theme/                  ← {brand}-pbi-theme.json + {brand}-canvas-background.svg
                              (the importable artifacts — View > Themes > Browse)
    design-system/          ← {brand}-design-system.pdf
                              (shareable A4 documentation)
    design-tokens/          ← {brand}-tokens.css
                              (CSS custom properties for HTML visuals)
    html-visual-style/      ← {brand}-html-visual-example.dax
                              (DAX example using the tokens)
  ```

- If any of the four category subfolders does not exist yet (older lifecycle version or manual client setup), create the missing ones before writing. Never delete or modify anything that already exists.
- Read-only on everything else under the client root. Never touch `Power BI Repository/`, `Global Info/`, `Global Theme/logo/`, `Global Theme/brand-guideline/`, or any pre-existing file in the four category subfolders. The skill only writes net-new files; if a `{brand}-pbi-theme.json` already exists in `theme/`, ask the operator before overwriting (offer to suffix with a version number, e.g. `{brand}-pbi-theme-v2.json`).

### Mode 3 · pbi-project-hub engagement (legacy companion)

- The user will typically already have a client folder at `Clients/{name}/`.
- Generate outputs directly into `Clients/{name}/02_Design_System/`.
- Use the client name from the project-hub context to name the files.
- Cross-link: the project-hub's `brand-guide.md` should reference the theme outputs.
- Detect by checking for a `Clients/{name}/02_Design_System/` path in $ARGUMENTS or nearby working files. If present, use that path.

### Output file list (same in every mode)

Whatever the mode, this skill always writes the same five files (and only these five):

1. `{brand}-pbi-theme.json`
2. `{brand}-canvas-background.svg`
3. `{brand}-design-system.pdf`
4. `{brand}-tokens.css`
5. `{brand}-html-visual-example.dax`

**Where each file lands:**

| Mode | File | Destination |
|---|---|---|
| 1 (standalone) | all 5 | flat in the chosen folder |
| 2 (lifecycle) | `{brand}-pbi-theme.json` | `Global Theme/pbi-theme/theme/` |
| 2 (lifecycle) | `{brand}-canvas-background.svg` | `Global Theme/pbi-theme/theme/` |
| 2 (lifecycle) | `{brand}-design-system.pdf` | `Global Theme/pbi-theme/design-system/` |
| 2 (lifecycle) | `{brand}-tokens.css` | `Global Theme/pbi-theme/design-tokens/` |
| 2 (lifecycle) | `{brand}-html-visual-example.dax` | `Global Theme/pbi-theme/html-visual-style/` |
| 3 (project-hub) | all 5 | flat in `Clients/{name}/02_Design_System/` |

The skill never writes a `logo.svg`, `brand-guideline.pdf`, `theme.json` (without the `{brand}-pbi-` prefix), or any other file. Subfolders like `logo/` and `brand-guideline/` exist for the operator's own assets and are not populated by this skill.

## 1. Collect Inputs — MANDATORY QUESTIONNAIRE

**IMPORTANT**: If the user has NOT provided all required inputs, you MUST ask before generating.

Present this questionnaire EXACTLY (copy-paste it, do not rephrase):

To create your Power BI theme, I need a few details:

1. **3 brand colors** (hex):
   - Primary (main brand color): e.g. #20252e
   - Secondary (accent/highlight): e.g. #f5b833
   - Tertiary (support/complementary): e.g. #3b82f6

2. **Report background**: `light` or `dark`?
   - Light: light background, dark text (corporate standard)
   - Dark: dark background, light text (modern dashboards)

3. **Report resolution**:
   - `16:9` — 1280x720px (Power BI default, recommended)
   - `16:9 HD` — 1920x1080px (full HD, large screens)
   - `4:3` — 1440x1080px (presentations, projectors)
   - Or custom dimensions: e.g. 1600x900

4. **Canvas background layout**:

   **A) Simple** — title header only
   ```
   ┌──────────────────────────────┐
   │  TITLE HEADER                │
   ├──────────────────────────────┤
   │                              │
   │        CANVAS                │
   │                              │
   └──────────────────────────────┘
   ```

   **B) Header + Filters** — title header + filter bar
   ```
   ┌──────────────────────────────┐
   │  TITLE HEADER                │
   ├──────────────────────────────┤
   │  FILTER BAR                  │
   ├──────────────────────────────┤
   │                              │
   │        CANVAS                │
   │                              │
   └──────────────────────────────┘
   ```

   **C) Header + Filters + Sidebar** — full layout
   ```
   ┌──────────────────────────────┐
   │  TITLE HEADER                │
   ├──────────────────────────────┤
   │  FILTER BAR                  │
   ├──────┬───────────────────────┤
   │      │                       │
   │ NAV  │     CANVAS            │
   │      │                       │
   └──────┴───────────────────────┘
   ```

   **D) Header + Sidebar** — no filter bar
   ```
   ┌──────────────────────────────┐
   │  TITLE HEADER                │
   ├──────┬───────────────────────┤
   │      │                       │
   │ NAV  │     CANVAS            │
   │      │                       │
   └──────┴───────────────────────┘
   ```

   **E) Sidebar only** — clean, minimalist
   ```
   ┌──────┬───────────────────────┐
   │      │  TITLE                │
   │      ├─ line ────────────────┤
   │ NAV  │                       │
   │      │     CANVAS            │
   │      │                       │
   └──────┴───────────────────────┘
   ```

5. **Brand name** (for the theme title): e.g. "Acme Corp"

6. **Accessibility** (optional):
   - `none` — default palette, no restrictions
   - `protanopia` — red-blind (~1.3% of men)
   - `deuteranopia` — green-blind (~6% of men, most common)
   - `tritanopia` — blue-blind (rare, ~0.01%)
   - `achromatopsia` — no color vision, luminance only
   - `low-vision` — enhanced contrast (WCAG AAA, minimum 7:1 ratio)
   - `wcag-aa` — WCAG AA compliance (minimum 4.5:1 text, 3:1 graphics)
   - `wcag-aaa` — WCAG AAA compliance (minimum 7:1 text, 4.5:1 graphics)

7. **Borders and corners** (optional):
   - `default` — border radius 6px, subtle visible borders (recommended)
   - `rounded` — border radius 12px, soft borders
   - `sharp` — border radius 0px, solid borders
   - `none` — border radius 8px, no visible borders
   - Or custom: e.g. "radius 10px, no borders"

8. **Brand logo** (optional):
   - Paste your SVG logo in the chat and it will be embedded in the background
   - Logo is left-aligned at the top (sidebar or header area)
   - If not provided, the theme is generated without a logo

9. **What would you like me to generate?**
   - `all` — everything: theme JSON + SVG background + design system PDF + CSS tokens + DAX examples (default)
   - `theme-only` — just the Power BI theme JSON + SVG background
   - `theme+pdf` — theme JSON + SVG + design system PDF
   - Or tell me exactly what you need

If you only have 1-2 colors, just tell me and I can help!

If the user provides only 1-2 colors, suggest complementary options with hex codes for them to approve before proceeding. If resolution is not specified, default to 1280x720 (16:9 standard). If layout is not specified, default to B (Header + Filters).

### Required Inputs:
- **Primary color** (required): The main brand color as hex — used for text, headers, or main identity
- **Secondary color** (required): Accent/highlight color — used for dataColor[0], buttons, badges, emphasis
- **Tertiary color** (required): Support color — used for dataColor[1] and chart variety
- **Background mode** (required): `light` or `dark` — fundamentally changes the entire color architecture
- **Resolution** (optional): Report canvas dimensions. Default: `1280x720`. Affects the SVG background layout.
- **Layout** (optional): Canvas background layout: `A` | `B` | `C` | `D` | `E`. Default: `B`.
- **Brand name** (optional): Used in theme `name` field and file naming. Default: "Custom Theme"
- **Accessibility** (optional): Color accessibility mode. Default: `none`. Options: `protanopia`, `deuteranopia`, `tritanopia`, `achromatopsia`, `low-vision`, `wcag-aa`, `wcag-aaa`.
- **Logo** (optional): SVG logo provided by the user. Embedded in the canvas background SVG. If not provided, generate without logo.
- **Mood** (optional): `professional` | `bold` | `minimal`. Default: `professional`. Controls layout density, not colors.

## 2. Core Workflow

### Step 1: Collect Inputs
Present the questionnaire above. Do not proceed until all required inputs are provided.

### Step 2: Generate Color Palette
Convert the primary hex to HSL. Generate the full 37-color semantic map from the three brand colors.

See **[references/color-engine.md](references/color-engine.md)** for the complete algorithm:
- Backgrounds (4 colors) — light and dark mode calculations
- Text hierarchy (5 colors) — light and dark mode
- Borders and chrome (6 colors)
- Accent family (5 colors from secondary)
- Disabled states (2 colors)
- Semantic status (3 colors)
- Data colors (8 colors) — brand-anchored algorithm
- Filter pane colors (4 derived)

See **[references/accessibility.md](references/accessibility.md)** for WCAG contrast ratios and color blindness adjustment rules applied after palette generation.

### Step 3: Apply Layout Settings by Mood
Apply structural properties (padding, border radius, shadows, gridlines, font selection) based on the chosen mood. If the user chose a custom border style, override accordingly.

See **[references/layout-templates.md](references/layout-templates.md)** for mood tables (professional/bold/minimal), border style overrides, table variants, action button presets, and font selection.

### Step 4: Generate Theme JSON
Build the complete theme JSON with:
- Top-level structure (name, dataColors, background, foreground, tableAccent, etc.)
- All 13 textClasses with resolution-scaled font sizes
- Complete visualStyles for all 27 visual types with presets
- Named shapes with brand colors
- ThemeDataColor expressions preserved as-is

See **[references/visual-types.md](references/visual-types.md)** for the complete list of visual types, textClasses with font scaling, color replacement map, and named shape definitions.

### Step 5: Generate SVG Canvas Background

CRITICAL: You MUST generate an SVG background and embed it as base64 in the theme JSON at `visualStyles.page.*.background[0].image`. This is what gives the report a structured layout when imported.

Always use `preserveAspectRatio="xMidYMid slice"` and `scaling: "Fit"`.

Example for Layout B (Header + Filters), light mode, 1280x720:
```svg
<svg viewBox="0 0 1280 720" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg">
  <rect width="100%" height="100%" fill="{bg2}"/>
  <rect width="100%" height="56" fill="{white}"/>
  <rect y="56" width="100%" height="1" fill="{border_primary}"/>
  <rect y="57" width="100%" height="48" fill="{white}"/>
  <rect y="105" width="100%" height="1" fill="{border_light}"/>
</svg>
```

If the user provided a logo SVG, embed it inside the background SVG using `<g transform="translate(24, 14) scale(0.45)">`.

See **[references/layout-templates.md](references/layout-templates.md)** for all 5 layout SVGs (A-E) in light/dark mode.

### Step 6: Generate Outputs
Produce the output files based on the user's choice (question 9). Default: all 4 files.

CRITICAL: You MUST read **[references/layout-templates.md](references/layout-templates.md)** and **[references/visual-types.md](references/visual-types.md)** before generating. Do not improvise the theme structure.

## 3. Output Files

**LANGUAGE RULE**: ALL output files (JSON, HTML, CSS, DAX, SVG) MUST be in English regardless of what language the user speaks. Labels like "background", "foreground", "How to Import", "Design System Reference", section titles, comments — everything in English. The only exception is if the user explicitly asks for a specific language.

**STRUCTURE RULE**: Follow the exact templates defined below. Do NOT improvise different HTML structures, CSS frameworks, or alternative layouts. The design system HTML must match the 2-page A4 format described below exactly.

Generate up to 5 files (based on user's choice in question 9):

1. **`{brand}-pbi-theme.json`** — The complete Power BI theme (ready to import via View > Themes > Browse)
2. **`{brand}-canvas-background.svg`** — The SVG canvas background as a standalone file (for manual use or editing)
3. **`{brand}-design-system.pdf`** — Design system reference document (A4, print-ready, shareable by email)
4. **`{brand}-tokens.css`** — CSS custom properties for HTML visuals inside Power BI
5. **`{brand}-html-visual-example.dax`** — DAX measures with HTML visual examples using the brand tokens

Note: The SVG is also embedded inside the theme JSON, but providing it separately lets the user edit it, use it in other tools, or apply it manually in Power BI.

### PDF Generation

Generate the design system HTML as a 2-page A4 document with `@page { size: A4; margin: 0 }` and `@media print` rules. Always include footer credit on the last page:

**Design System HTML MUST follow this exact structure (2-page A4 document):**

Page 1:
- Header: brand logo (left) + "Power BI Theme" title (right) + "LIGHT MODE · PROFESSIONAL" badge
- Canvas Background preview (aspect-ratio 16/9 showing the SVG layout)
- Brand Colors (3 swatches: primary, secondary, tertiary)
- Accent Family (5 tone swatches: 50, 200, 400, 500, 700)
- Data Colors (8 swatches in a row)
- Component preview (2 KPI cards + bar chart using data colors)
- Footer: "{Brand Name} · Design System v1.0" + "Page 1 of 2"

Page 2:
- Small header: brand logo + "Technical Reference"
- Structural Colors table (background, foreground, secondaryBackground, etc.)
- Semantic Colors (Good, Bad, Neutral cards)
- Surfaces (bg1, bg2, bg3, white swatches)
- Layout Properties table (padding, border radius, gridline, font, etc.)
- UI Components (buttons: Brand/Soft/Surface, badges: Active/Healthy/Alert, navigation pills)
- How to Import (4 steps)
- Delivered Files table
- Footer: "{Brand Name} · Design System v1.0" + "by Gus Bavia · linkedin.com/in/gusbavia"

Use Inter + JetBrains Mono from Google Fonts. A4 format with `@page { size: A4; margin: 0 }`. Professional, minimal design — NOT generic Bootstrap/Tailwind look.

**Interactive feature:** Every color swatch in the HTML must be clickable — clicking copies the hex value to the clipboard. Add this JavaScript at the bottom of the HTML:

```javascript
document.querySelectorAll('.color-swatch, [data-hex]').forEach(el => {
  el.style.cursor = 'pointer';
  el.title = 'Click to copy';
  el.addEventListener('click', () => {
    const hex = el.dataset.hex || el.querySelector('.hex,.swatch-hex')?.textContent || '';
    if (hex) {
      navigator.clipboard.writeText(hex).then(() => {
        const orig = el.style.outline;
        el.style.outline = '2px solid #22c55e';
        setTimeout(() => el.style.outline = orig, 600);
      });
    }
  });
});
```

Add `data-hex="#hexvalue"` attribute to every color swatch element. On click, briefly flash a green outline as visual feedback that the color was copied.

Then convert to PDF using a headless browser. Try in this order:

1. **Microsoft Edge** (most common on Windows):
```bash
"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --headless --disable-gpu --no-margins --print-background --print-to-pdf="{brand}-design-system.pdf" "file:///{path}/{brand}-powerbi-preview.html"
```

2. **Google Chrome** (fallback):
```bash
chrome --headless --disable-gpu --no-margins --print-background --print-to-pdf="{brand}-design-system.pdf" "file:///{path}/{brand}-powerbi-preview.html"
```

3. **No browser available**: Keep the HTML file and instruct the user: "Open the HTML file in your browser and press Ctrl+P > Save as PDF."

Keep the HTML file alongside the PDF — it serves as the source for regeneration.

### CSS Tokens File

Generate a `{brand}-tokens.css` with ALL design tokens as CSS custom properties:

```css
:root {
  /* Brand Colors */
  --brand-primary: {primary_color};
  --brand-secondary: {secondary_color};
  --brand-tertiary: {tertiary_color};

  /* Data Colors */
  --data-1: {dataColor[0]};
  --data-2: {dataColor[1]};
  /* ... through --data-8 */

  /* Backgrounds */
  --bg-primary: {bg1};
  --bg-secondary: {bg2};
  --bg-tertiary: {bg3};
  --bg-surface: {white};

  /* Text */
  --text-primary: {text_primary};
  --text-secondary: {text_secondary};
  --text-muted: {text_muted};

  /* Borders */
  --border-primary: {border_primary};
  --border-light: {border_light};

  /* Accent */
  --accent-50 through --accent-700

  /* Semantic */
  --color-good / --color-bad / --color-neutral

  /* Layout */
  --radius: {border_radius}px;
  --padding: {padding}px;
  --font-primary: 'Segoe UI', sans-serif;
}
```

### HTML Visual Examples (DAX)

Generate a `{brand}-html-visual-example.dax` file with 3 ready-to-use DAX measures:

1. **KPI Card** — branded card with value, label, change indicator (green/red), using the theme's exact colors
2. **Status Badge** — dynamic badge that changes color based on status (Active/Warning/Critical), using accent and semantic colors
3. **Progress Bar** — horizontal sparkline bar with dynamic color based on percentage, using data colors

Each measure returns an HTML string that uses the brand tokens inline. Include instructions at the top of the file explaining how to use with the "HTML Content" visual from AppSource.

**IMPORTANT:** All hex colors in the DAX HTML must match EXACTLY the colors in the theme JSON. Use the same values — never hardcode different colors.

For advanced HTML visual generation patterns, see **[references/html-visuals.md](references/html-visuals.md)**.

## 4. HTML Preview

After generating the JSON, create an HTML file named `{brand}-powerbi-preview.html` that shows:

1. **Header** — Brand name, mood, primary/secondary colors
2. **Data Colors** — 8 swatches in a row with hex values
3. **Structural Colors** — background, foreground, first/second/thirdLevelElements, tableAccent
4. **Semantic Colors** — good, bad, neutral, maximum, minimum
5. **Text Classes** — Sample text for each of the 13 classes with their font/size/weight/color
6. **Layout Properties** — Table showing padding, border radius, shadow, gridline settings
7. **Named Shapes Preview** — Visual representation of Badge, Brand Color button, Nav Bar, Headers
8. **Light/Dark surface comparison** — Shows background layers and text hierarchy
9. **Accessibility Check** — Contrast ratios for text_primary on bg1, text_secondary on bg1, accent on white
10. **Import Instructions** — Step-by-step how to import in Power BI Desktop

Preview design: use the theme's own colors, clean professional layout, no external dependencies (inline CSS), Google Fonts `Inter` for browser viewing only, toggle for simulating light/dark background.

## 5. Validation Checklist

Before delivering, verify:
- [ ] JSON is valid (no trailing commas, proper nesting)
- [ ] All 37 color slots are filled with valid 6-digit hex
- [ ] `dataColors` has exactly 8 entries
- [ ] `dataColors[0]` is the client's SECONDARY color
- [ ] `dataColors[1]` is the client's TERTIARY color
- [ ] `dataColors[2]` is derived from the client's PRIMARY color
- [ ] All 8 dataColors feel cohesive and brand-aligned (NOT random rainbow)
- [ ] All 13 `textClasses` are present
- [ ] All `visualStyles` color properties use `{ "solid": { "color": "#hex" } }` wrapper
- [ ] ThemeDataColor expressions are preserved (not replaced with hex)
- [ ] Page background has the branded SVG layout (header bar + canvas) as base64
- [ ] NO other embedded SVGs anywhere else (no patterns, no logos, no textures)
- [ ] NO external URLs (third-party domains, etc.) in any image/icon property
- [ ] SVG dimensions match the client's chosen resolution
- [ ] `name` field is set
- [ ] No CSS variables, no rgb(), no alpha channels
- [ ] Mood-specific layout values are applied
- [ ] Background mode (light/dark) is correctly applied to ALL bg/text/border colors
- [ ] Border radius matches mood
- [ ] Both files are generated (JSON + HTML preview)
- [ ] If accessibility mode is active: all contrast ratios meet the required WCAG level
- [ ] If color blindness mode is active: dataColors are distinguishable under the selected deficiency
- [ ] If low-vision: stroke widths and font sizes are increased
- [ ] HTML preview includes accessibility section with compliance badge (if applicable)

## 6. Post-Generation Customization

After the theme is generated, the user can ask for adjustments without regenerating everything.

### What CAN be changed independently:
- **Canvas background layout** — swap between layouts A/B/C/D/E without regenerating the full theme
- **Logo** — add, remove, or reposition the logo in the background SVG
- **Border style** — change radius, show/hide borders
- **Individual dataColors** — swap one or more colors
- **Font sizes** — scale up/down for different resolutions
- **Sidebar width** — default is 200px, can be adjusted (160px-280px)
- **Header height** — default is 56px, can be adjusted (40px-80px)
- **Filter bar height** — default is 48px, can be adjusted (36px-64px)
- **Accent family** — regenerate from a different source color
- **Semantic colors** — swap good/bad/neutral colors
- **Named shapes** — add custom SVG icons to action buttons
- **Image presets** — replace the Logo image visual with custom SVG content

### What CANNOT be done via theme JSON:
- Set page size/dimensions (must be set manually in Power BI per page)
- Add background images via import (only the page background SVG works — validated)
- Set conditional formatting rules (these are per-visual, not theme-level)
- Control slicer dropdown behavior fully (limited theme support)
- Embed custom web fonts (must use system-installed fonts)
- Create dark/light mode toggle (need two separate theme files)
- Set wallpaper images for the outspace area (only solid color)

### Example follow-up requests:
- "Switch layout to sidebar" — Update only the SVG background, keep all colors
- "Make borders more rounded" — Update border.radius across all visualStyles
- "Logo is too big" — Adjust the scale factor in the SVG
- "Try dark mode" — Generate a second theme file with inverted colors
- "Add an SVG icon to the Brand button" — Embed SVG in actionButton.Brand.icon
- "Change chart color 4 to purple" — Update dataColors[3] only
- "Generate for 1920x1080" — Scale fonts, regenerate SVG background with new dimensions

For advanced HTML visual patterns after theme generation, see **[references/html-visuals.md](references/html-visuals.md)**.

## 7. Important Notes

- The JSON MUST be valid and importable in Power BI Desktop without errors
- Power BI silently ignores invalid properties, so correctness matters for the theme to actually apply
- Keep the `@brand` reference in shape "Brand Color" background — it is a Power BI dynamic token
- Fonts: ONLY use Segoe UI, Segoe UI Semibold, Segoe UI Light, DIN, Arial, Calibri — these are guaranteed to be available
- The HTML preview is for browser viewing only and CAN use web fonts
- Always test mental model: "if I import this JSON in PBI Desktop, will every color show correctly?"
- Background colors (bg1, bg2, bg3) are ALWAYS derived from the client's primary hue — never fixed gray. They carry a subtle brand tint.
- Border colors are also derived from the client's primary hue — never generic gray.
- Font sizes must be scaled based on the resolution (see references/visual-types.md for the scaling table).
- The JSON MUST include `{ "solid": { "color": "#hex" } }` wrappers on all visualStyles color properties.
- Power BI only accepts 6-digit hex strings (`#RRGGBB`). No alpha, no rgb(), no CSS variables.

## Performance Notes
- Take your time to do this thoroughly
- Quality is more important than speed
- Do not skip validation steps
