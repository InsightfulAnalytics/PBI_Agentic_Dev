# PBI Theme Gen

[![Version](https://img.shields.io/badge/version-1.1.0-201d15.svg)](#) [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE) [![Agent Skill](https://img.shields.io/badge/agent-skill-d97757.svg)](./SKILL.md) [![Power BI](https://img.shields.io/badge/Power%20BI-themes-F2C811.svg)](#)


**Generate complete Power BI Desktop themes from brand colors using Claude AI.**

A Claude Skill that turns 3 brand colors into a production-ready Power BI theme — with branded canvas backgrounds, design tokens, HTML visual examples, and a PDF design system document.

## What it does

Give Claude your brand colors. Get 4 production-ready files:

| Output | Description |
|--------|-------------|
| `{brand}-pbi-theme.json` | Complete Power BI theme (~5,800 lines) ready to import |
| `{brand}-design-system.pdf` | A4 print-ready design system reference document |
| `{brand}-tokens.css` | CSS custom properties for HTML visuals in Power BI |
| `{brand}-html-visual-example.dax` | 3 DAX measures for branded HTML visuals |

## Features

- **37-Color Semantic Engine** — backgrounds, text hierarchy, borders, accent family, and 8 chart data colors derived from your 3 brand inputs
- **5 Canvas Background Layouts** — header only, header+filters, full layout with sidebar, or minimalist sidebar. SVG backgrounds with optional logo embedding
- **21 Shape Presets** — badges, headers, dividers, accent bars, info cards, dark cards, metric highlights
- **9 Button Presets** — brand, soft, surface, outline, dark, with hover states
- **WCAG Accessibility** — protanopia, deuteranopia, tritanopia, achromatopsia, low vision, WCAG AA/AAA
- **Light & Dark Mode** — complete color architecture for both
- **Resolution-Aware Fonts** — scales for 1280x720, 1920x1080, or custom
- **HTML Visual Templates** — responsive DAX-generated visuals using brand tokens
- **Logo Embedding** — paste your SVG logo, it gets embedded in the canvas background

## Installation

### Claude Code

```bash
git clone https://github.com/gusbavia/pbi-theme.git
cp -r pbi-theme ~/.claude/skills/          # global, every project
# or into a single project: cp -r pbi-theme your-project/.claude/skills/
```

Then just ask in plain language (the skill triggers from your phrasing), or invoke it explicitly with `@pbi-theme`.

### Claude.ai

Download this repository as a ZIP, then **Settings > Capabilities > Skills > Upload skill**.

## How it works

1. **Answer 8 questions** — colors, light/dark, resolution, layout, accessibility, borders, name, logo
2. **Color engine runs** — 37 semantic colors derived via HSL algorithms
3. **Layout applied** — mood settings, border style, font scaling
4. **Theme generated** — 5,800-line JSON with 27 visual types
5. **SVG background** — canvas layout + logo rendered as base64
6. **4 files delivered** — JSON + PDF + CSS + DAX

## Requirements

- Claude.ai or Claude Code
- Microsoft Edge or Google Chrome (for PDF generation)
- Power BI Desktop (to import the theme)

## License

MIT License - see [LICENSE](LICENSE) for details.

Copyright (c) 2026 Gus Bavia

## Companion skill

This skill pairs with **[pbi-project-hub](https://github.com/gusbavia/pbi-project-hub)** — the full project delivery system for Power BI consultants. When you reach the *Design System* phase in a project hub engagement, invoke `pbi-theme` to generate the production theme. Outputs (JSON · CSS · DAX · PDF) drop directly into `Clients/{name}/02_Design_System/`.

## Author

**Gus Bavia** — Power BI World Champion 2026

- LinkedIn: [gusbavia](https://linkedin.com/in/gusbavia)
