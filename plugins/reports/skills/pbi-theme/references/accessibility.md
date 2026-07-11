# Accessibility Rules

WCAG contrast ratio requirements and color blindness adjustment rules for the Power BI theme palette. Apply these rules AFTER generating the palette, based on the user's accessibility selection.

## WCAG Contrast Ratios

For `wcag-aa` or `wcag-aaa` modes, verify contrast ratios using the relative luminance formula:
- **Contrast ratio** = (L1 + 0.05) / (L2 + 0.05), where L1 is the lighter color
- **Relative luminance**: L = 0.2126*R + 0.7152*G + 0.0722*B (with linearized sRGB values)

| Element | WCAG AA minimum | WCAG AAA minimum |
|---------|----------------|-----------------|
| Text on background (text_primary on bg1) | 4.5:1 | 7:1 |
| Text on background (text_secondary on bg1) | 4.5:1 | 7:1 |
| Large text (>18pt) on background | 3:1 | 4.5:1 |
| Graphical elements / UI borders | 3:1 | 3:1 |
| DataColors on bg1 (chart labels) | 3:1 | 4.5:1 |
| DataColors on white (chart elements) | 3:1 | 3:1 |

If any color fails the required ratio, adjust its lightness (darker for light mode, lighter for dark mode) until it passes, while preserving the hue.

## Color Blindness Adjustments

For color vision deficiency modes, adjust the dataColors palette to avoid problematic combinations:

### Protanopia (red-blind)
- AVOID: red-green pairs as adjacent dataColors
- Red appears as dark brown/olive — shift reds toward orange (add yellow)
- Ensure dataColors are distinguishable by LIGHTNESS, not just hue
- Safe palette hues: blue, yellow, orange, purple, gray tones

### Deuteranopia (green-blind, MOST COMMON)
- AVOID: red-green pairs, green-brown pairs, green-orange pairs
- Green appears as brownish yellow — shift greens toward cyan/teal
- Ensure adjacent dataColors have >20% lightness difference
- Safe palette hues: blue, orange, yellow, purple, pink, teal

### Tritanopia (blue-blind)
- AVOID: blue-green pairs, yellow-pink pairs
- Blue appears as teal/cyan — shift blues toward darker navy
- Safe palette hues: red, orange, green, magenta, dark blue, gray

### Achromatopsia (no color vision)
- ALL dataColors must be distinguishable by LIGHTNESS ALONE
- Space dataColors evenly across the lightness spectrum (L=25% to L=75%)
- Minimum 10% lightness difference between adjacent colors
- Consider adding texture/pattern differentiation note in the preview

### Low Vision
- Apply WCAG AAA ratios (7:1 for all text)
- Increase border thickness: borderThickness from 1 to 2
- DataColors must have minimum 4.5:1 contrast against their background
- Avoid thin lines: lineStyles.strokeWidth minimum 2.5
- Increase font sizes in textClasses by 1-2pt

## Accessibility Validation in Preview HTML

When accessibility mode is active, add an "Accessibility" section to the HTML preview showing:
- Contrast ratios for all text/background combinations (pass/fail)
- Simulated palette preview for the selected color blindness type
- WCAG compliance badge: "WCAG AA Compliant" or "WCAG AAA Compliant"
- Any adjustments made to the original brand colors (with before/after)
