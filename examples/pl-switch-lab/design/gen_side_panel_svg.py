# Generates the side-panel page background SVG for PL Bridge Demo, in the style of
# a sibling layout-reference project, not shipped
# but recolored to this report's Claude Design theme.
#
# Structure copied from the Forge Template_Background__2 SVGs (verified by reading them):
#   - full-bleed white page
#   - an inset rounded "canvas card" with a white stroke frame
#   - a left rail, rounded on its left corners, filled with a dark radial-ish gradient
#   - an accent line under the rail's brand block
# The Forge SVGs bake NO text -- labels, nav buttons and slicers are report visuals
# layered on top. Same here.
#
# Claude Design palette (StaticResources/RegisteredResources/Claude_Design*.json):
#   ink #0B1E3F | primary #1E6FD9 | deep navy #0B3D91 / #003A70 | gold #FFB703
#   light blues #5DA9E9 #8ECAE6 #B8D9F2 | neutral #94A3B8
#
# Page is 2000 x 1000. Rail width 280 (Forge uses ~13% of page width).
from pathlib import Path

W, H = 2000, 1000
M = 16            # outer white margin
R = 24            # card corner radius
RAIL_W = 280      # rail width, inside the card
BRAND_H = 104     # brand block height on the rail (accent line sits under it)

RAIL_DARK = "#071A38"    # bottom of the gradient -- near-ink navy
RAIL_MID = "#0B2C5B"
RAIL_TOP = "#164080"     # top -- lifted toward #0B3D91/#1E6FD9
GOLD = "#FFB703"
CANVAS = "#F7F9FC"       # cool off-white card, blue family (not the warm #FAFAFC of Forge)
FRAME = "#FFFFFF"

card_x, card_y = M, M
card_w, card_h = W - 2 * M, H - 2 * M

svg = f'''<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" overflow="hidden">
<defs>
  <linearGradient id="rail" x1="0" y1="1" x2="0.55" y2="0">
    <stop offset="0" stop-color="{RAIL_DARK}"/>
    <stop offset="0.45" stop-color="{RAIL_MID}"/>
    <stop offset="1" stop-color="{RAIL_TOP}"/>
  </linearGradient>
  <linearGradient id="railSheen" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#FFFFFF" stop-opacity="0.05"/>
    <stop offset="1" stop-color="#FFFFFF" stop-opacity="0"/>
  </linearGradient>
</defs>
<!-- page -->
<rect x="0" y="0" width="{W}" height="{H}" fill="{FRAME}"/>
<!-- canvas card -->
<rect x="{card_x}" y="{card_y}" width="{card_w}" height="{card_h}" rx="{R}" fill="{CANVAS}" stroke="{FRAME}" stroke-width="3"/>
<!-- rail: left slice of the card, rounded only on the left -->
<path d="M {card_x + R} {card_y}
         L {card_x + RAIL_W} {card_y}
         L {card_x + RAIL_W} {card_y + card_h}
         L {card_x + R} {card_y + card_h}
         Q {card_x} {card_y + card_h} {card_x} {card_y + card_h - R}
         L {card_x} {card_y + R}
         Q {card_x} {card_y} {card_x + R} {card_y} Z"
      fill="url(#rail)"/>
<!-- faint vertical sheen so the rail reads as a surface, not a flat fill -->
<rect x="{card_x}" y="{card_y}" width="72" height="{card_h}" fill="url(#railSheen)"/>
<!-- gold accent rule under the brand block: the report's one signature -->
<line x1="{card_x + 24}" y1="{card_y + BRAND_H}" x2="{card_x + RAIL_W - 24}" y2="{card_y + BRAND_H}"
      stroke="{GOLD}" stroke-width="3" stroke-linecap="round"/>
<!-- hairline seam where rail meets canvas -->
<line x1="{card_x + RAIL_W}" y1="{card_y}" x2="{card_x + RAIL_W}" y2="{card_y + card_h}"
      stroke="#FFFFFF" stroke-width="2" stroke-opacity="0.85"/>
</svg>'''

out = Path(__file__).parent / "side_panel.svg"
out.write_text(svg, encoding="utf-8")
print(f"wrote {out.name}: {W}x{H}, rail {RAIL_W}px, brand block {BRAND_H}px")
