# Generates the design-canvas artboards for the side-panel color decision.
#
# The first canvas referenced side_panel.svg as a CSS background and the rail did not
# render in the published canvas, so every option here draws the chrome in plain CSS --
# nothing to resolve, nothing to fail silently. The shipped PBIR asset stays an SVG;
# these artboards are the color decision only, and each option's CSS gradient is the
# exact recipe its SVG will use.
#
# Six options, one axis (rail color), stable identities A..F.
import json
from pathlib import Path

HERE = Path(__file__).parent

OPTIONS = [
    dict(key="A", file="Main", name="Deep Navy + Gold",
         rail="linear-gradient(to top, #071A38 0%, #0B2C5B 45%, #164080 100%)",
         accent="#FFB703", white="#FFFFFF", item="#B8D9F2", head="#5DA9E9",
         sub="#8ECAE6", foot="rgba(184,217,242,0.62)", box="rgba(255,255,255,0.30)",
         activefill="rgba(255,255,255,0.10)", light=False,
         note="the theme's own deep-navy family; gold tableAccent as the one signature"),
    dict(key="B", file="OptionB", name="Ink + Blue",
         rail="#0B1E3F",
         accent="#1E6FD9", white="#FFFFFF", item="#B8D9F2", head="#5DA9E9",
         sub="#8ECAE6", foot="rgba(184,217,242,0.62)", box="rgba(255,255,255,0.30)",
         activefill="rgba(255,255,255,0.10)", light=False,
         note="flat ink, single blue family, quietest"),
    dict(key="C", file="OptionC", name="Forge Slate",
         rail="linear-gradient(to top, #263143 0%, #2A374A 54%, #43546D 100%)",
         accent="#FFB703", white="#FFFFFF", item="#C2CBD9", head="#8B9AB5",
         sub="#9FADC4", foot="rgba(194,203,217,0.62)", box="rgba(255,255,255,0.28)",
         activefill="rgba(255,255,255,0.10)", light=False,
         note="the original Data Vis Forge slate, desaturated; least tied to the theme"),
    dict(key="D", file="OptionD", name="Royal Blue",
         rail="linear-gradient(to top, #0B3D91 0%, #155CC0 55%, #1E6FD9 100%)",
         accent="#FFB703", white="#FFFFFF", item="#D6E7F9", head="#9CC5EF",
         sub="#B8D9F2", foot="rgba(214,231,249,0.65)", box="rgba(255,255,255,0.35)",
         activefill="rgba(255,255,255,0.14)", light=False,
         note="the theme's primary blue at full strength; boldest, most Claude"),
    dict(key="E", file="OptionE", name="Graphite + Gold",
         rail="linear-gradient(to top, #16191B 0%, #23282B 50%, #32393D 100%)",
         accent="#FFB703", white="#FFFFFF", item="#C3CDD6", head="#8FA0AD",
         sub="#9AA8B5", foot="rgba(195,205,214,0.6)", box="rgba(255,255,255,0.26)",
         activefill="rgba(255,255,255,0.09)", light=False,
         note="neutral dark: the rail recedes and the blue data colors own the canvas"),
    dict(key="F", file="OptionF", name="Paper (light)",
         rail="linear-gradient(to top, #E9EFF8 0%, #F1F5FB 100%)",
         accent="#0B3D91", white="#0B1E3F", item="#33517A", head="#7A8FB0",
         sub="#5B6B84", foot="rgba(51,81,122,0.55)", box="rgba(11,30,63,0.28)",
         activefill="rgba(11,61,145,0.08)", light=True,
         note="the contrarian option: light rail, ink text, navy marker; no dark block at all"),
]

CHEV_DARK = ('<svg width="12" height="12" viewBox="0 0 16 16" fill="none">'
             '<path d="M3 6l5 5 5-5" stroke="{c}" stroke-width="1.5" '
             'stroke-linecap="round" stroke-linejoin="round"/></svg>')


def nav_item(label, o, active=False):
    if active:
        return (f'<div style="display: flex; align-items: center; height: 40px; '
                f'padding: 0 14px; border-radius: 8px; background: {o["activefill"]}; '
                f'border-left: 3px solid {o["accent"]}; color: {o["white"]}; '
                f'font-size: 13px; font-weight: 600;">{label}</div>')
    return (f'<div style="display: flex; align-items: center; height: 40px; '
            f'padding: 0 14px; border-radius: 8px; color: {o["item"]}; '
            f'font-size: 13px;">{label}</div>')


def dropdown(label, o):
    chev = CHEV_DARK.format(c=o["sub"])
    return f'''<div style="display: flex; flex-direction: column; gap: 6px;">
      <div style="font-size: 11px; color: {o["sub"]};">{label}</div>
      <div style="display: flex; align-items: center; justify-content: space-between; height: 38px; padding: 0 12px; border: 1px solid {o["box"]}; border-radius: 6px; color: {o["white"]}; font-size: 12.5px;">
        <span>All</span>
        {chev}
      </div>
    </div>'''


def artboard(o):
    seam = "#D8E2EF" if o["light"] else "#FFFFFF"
    sheen = ("" if o["light"] else
             '<div style="position: absolute; left: 16px; top: 16px; width: 72px; '
             'height: 968px; background: linear-gradient(to right, '
             'rgba(255,255,255,0.05), rgba(255,255,255,0)); '
             'border-radius: 24px 0 0 24px;"></div>')
    return f'''<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <script src="./support.js"></script>
</head>
<body>
<x-dc>
<helmet>
  <style>
    body {{ margin: 0; font-family: 'Segoe UI', system-ui, sans-serif; }}
    a {{ color: #1E6FD9; }} a:hover {{ color: #0B3D91; }}
  </style>
</helmet>
<div style="position: relative; width: 2000px; height: 1000px; background: #FFFFFF; overflow: hidden;">
  <!-- canvas card -->
  <div style="position: absolute; left: 16px; top: 16px; width: 1968px; height: 968px; background: #F7F9FC; border-radius: 24px; border: 3px solid #FFFFFF;"></div>
  <!-- rail -->
  <div style="position: absolute; left: 16px; top: 16px; width: 280px; height: 968px; background: {o["rail"]}; border-radius: 24px 0 0 24px; border-right: 2px solid {seam};"></div>
  {sheen}
  <!-- brand rule -->
  <div style="position: absolute; left: 40px; top: 120px; width: 232px; height: 3px; border-radius: 2px; background: {o["accent"]};"></div>

  <!-- brand block -->
  <div style="position: absolute; left: 40px; top: 40px; width: 232px; display: flex; flex-direction: column; gap: 4px;">
    <div style="font-size: 21px; font-weight: 700; color: {o["white"]}; letter-spacing: 0.5px;">P&amp;L BRIDGE</div>
    <div style="font-size: 11px; color: {o["sub"]};">Fast financial statements</div>
  </div>

  <!-- report sections -->
  <div style="position: absolute; left: 40px; top: 152px; width: 232px; display: flex; flex-direction: column; gap: 20px;">
    <div style="font-size: 11px; font-weight: 600; letter-spacing: 1.6px; color: {o["head"]};">REPORT SECTIONS</div>
    <div style="display: flex; flex-direction: column; gap: 8px;">
      {nav_item("Overview", o)}
      {nav_item("Classic SWITCH", o)}
      {nav_item("Fast Bridge", o)}
      {nav_item("P&amp;L Deneb", o, active=True)}
      {nav_item("Odd Rows Deneb", o)}
    </div>
  </div>

  <!-- key selections -->
  <div style="position: absolute; left: 40px; top: 480px; width: 232px; display: flex; flex-direction: column; gap: 18px;">
    <div style="font-size: 11px; font-weight: 600; letter-spacing: 1.6px; color: {o["head"]};">KEY SELECTIONS</div>
    {dropdown("Month", o)}
    {dropdown("State", o)}
    {dropdown("Category", o)}
  </div>

  <!-- footnotes -->
  <div style="position: absolute; left: 40px; bottom: 36px; width: 232px; display: flex; flex-direction: column; gap: 4px;">
    <div style="font-size: 10.5px; color: {o["foot"]};">Brightside Home &amp; Living (synthetic)</div>
    <div style="font-size: 10.5px; color: {o["foot"]};">Year 2026, Selected Period</div>
  </div>

  <!-- main canvas -->
  <div style="position: absolute; left: 336px; top: 44px; width: 1600px; display: flex; flex-direction: column; gap: 4px;">
    <div style="font-size: 26px; font-weight: 600; color: #0B1E3F;">P&amp;L - Deneb</div>
    <div style="font-size: 13px; color: #5B6B84;">the classic 27-line statement, 378 cells from a 27-row query. Identical numbers to the Classic SWITCH page, at a fraction of the cost</div>
  </div>

  <div style="position: absolute; left: 336px; top: 140px; width: 1608px; height: 700px; background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; display: flex; align-items: center; justify-content: center; overflow: hidden;">
    <img src="statement_thumb.jpg" style="width: 1560px; max-width: 100%;" alt="The 27-line P&amp;L statement rendered by the Deneb visual">
  </div>

  <div style="position: absolute; left: 336px; top: 872px; width: 1608px; font-size: 11.5px; color: #5B6B84;">
    Engine query: 27 bridge lines x 6 base measures, ~15 ms warm. The Classic SWITCH page computes the identical grid in ~2,400 ms.
  </div>
</div>
</x-dc>
</body>
</html>
'''


for o in OPTIONS:
    (HERE / f"{o['file']}.dc.html").write_text(artboard(o), encoding="utf-8")
    print(f"wrote {o['file']}.dc.html  ({o['key']} - {o['name']})")

# canvas: 2 columns x 3 rows, notes in a right-hand column
GX, GY = 2200, 1220
canvas = {
    "artboards": [
        {"file": f"{o['file']}.dc.html",
         "x": (i % 2) * GX, "y": (i // 2) * GY, "w": 2000, "h": 1000,
         "title": f"{o['key']} - {o['name']}"}
        for i, o in enumerate(OPTIONS)
    ],
    "annotations": [
        {"id": "brief", "x": 4480, "y": 0, "w": 340,
         "text": "Side-panel color options for PL Bridge Demo - one axis, six rails. "
                 "Everything else is held constant so only the rail color is being chosen.\n\n"
                 "A - Deep Navy + Gold: " + OPTIONS[0]["note"] + "\n"
                 "B - Ink + Blue: " + OPTIONS[1]["note"] + "\n"
                 "C - Forge Slate: " + OPTIONS[2]["note"] + "\n"
                 "D - Royal Blue: " + OPTIONS[3]["note"] + "\n"
                 "E - Graphite + Gold: " + OPTIONS[4]["note"] + "\n"
                 "F - Paper (light): " + OPTIONS[5]["note"]},
        {"id": "next", "x": 4480, "y": 560, "w": 340,
         "text": "Pick a letter and the matching SVG ships to the Duplicate of P&L - Deneb "
                 "page: SVG chrome as the page background, nav buttons / slicers / labels as "
                 "real Power BI visuals on top. Mixing is fine too - e.g. rail from C with "
                 "the gold accent from A."},
    ],
    "launch": {"view": "canvas"},
}
(HERE / "canvas.json").write_text(json.dumps(canvas, indent=1), encoding="utf-8")
print("wrote canvas.json (2x3 grid + notes)")
