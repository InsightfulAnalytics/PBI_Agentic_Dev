# Generates side_panel_top.svg -- the L-frame variant of side_panel.svg: the same
# Deep Navy rail PLUS a matching strip across the top of the canvas, for the
# comparison page "P&L - Deneb Top Strip" (requested 2026-08-26).
#
# Design decisions:
#   - the strip is a separate surface to the RIGHT of the rail (the rail already owns
#     the top-left corner with the brand block); the white hairline seam at the rail
#     edge keeps running full height, separating rail from strip and canvas alike
#   - strip bottom sits at the same y as the rail's gold brand rule (card_y + 104),
#     and carries its own gold rule there -- so the gold reads as one datum line
#     across the whole page, interrupted only by the seam
#   - strip gradient starts at the rail's top color (#164080) at the left so the two
#     surfaces read as one connected chrome, settling darker toward the right
#   - top-right corner rounded 24 to match the canvas card
#
# The page title moves ONTO the strip (white / light-blue text) -- that restyle is
# build_top_strip_page.py's job; this file is chrome only, no text baked in.
from pathlib import Path

W, H = 2000, 1000
M = 16            # outer white margin
R = 24            # card corner radius
RAIL_W = 280      # rail width, inside the card
BRAND_H = 104     # brand block height = strip height (gold rules align)

RAIL_DARK = "#071A38"
RAIL_MID = "#0B2C5B"
RAIL_TOP = "#164080"
GOLD = "#FFB703"
CANVAS = "#F7F9FC"
FRAME = "#FFFFFF"

card_x, card_y = M, M
card_w, card_h = W - 2 * M, H - 2 * M
strip_x = card_x + RAIL_W                 # 296
strip_x2 = card_x + card_w                # 1984
strip_y2 = card_y + BRAND_H               # 120

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
  <linearGradient id="strip" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="{RAIL_TOP}"/>
    <stop offset="1" stop-color="{RAIL_MID}"/>
  </linearGradient>
  <linearGradient id="stripSheen" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#FFFFFF" stop-opacity="0.06"/>
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
<!-- top strip: right of the rail, rounded only at the card's top-right corner -->
<path d="M {strip_x} {card_y}
         L {strip_x2 - R} {card_y}
         Q {strip_x2} {card_y} {strip_x2} {card_y + R}
         L {strip_x2} {strip_y2}
         L {strip_x} {strip_y2} Z"
      fill="url(#strip)"/>
<rect x="{strip_x}" y="{card_y}" width="{strip_x2 - strip_x}" height="40" fill="url(#stripSheen)"/>
<!-- gold accent rules: brand rule on the rail + strip rule, one datum line -->
<line x1="{card_x + 24}" y1="{strip_y2}" x2="{card_x + RAIL_W - 24}" y2="{strip_y2}"
      stroke="{GOLD}" stroke-width="3" stroke-linecap="round"/>
<line x1="{strip_x + 24}" y1="{strip_y2}" x2="{strip_x2 - 24}" y2="{strip_y2}"
      stroke="{GOLD}" stroke-width="3" stroke-linecap="round"/>
<!-- hairline seam where rail meets strip and canvas -->
<line x1="{card_x + RAIL_W}" y1="{card_y}" x2="{card_x + RAIL_W}" y2="{card_y + card_h}"
      stroke="#FFFFFF" stroke-width="2" stroke-opacity="0.85"/>
</svg>'''

out = Path(__file__).parent / "side_panel_top.svg"
out.write_text(svg, encoding="utf-8")
print(f"wrote {out.name}: rail {RAIL_W}px + top strip {strip_x}->{strip_x2} h{BRAND_H}px")
