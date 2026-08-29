# Third pass on the "Duplicate of P&L - Deneb" rail (2026-08-25):
#
#   1. styles Tim's pageNavigator for the navy rail -- transparent buttons, light-blue
#      text, selected = white 10% fill + white bold, no outlines. State contract
#      (fill/outline/text with default/hover/press/selected selectors) copied from a
#      real formatted navigator in the Forge layout repository.
#   2. deletes the orphaned gold active-marker shape (the actionButtons it marked were
#      replaced by the navigator).
#   3. fixes slicer CONTRAST: the dropdown chip and its popup render on a white ground,
#      so the item text must be ink, not white. Header text stays light on the navy
#      rail; item text goes ink-on-white with an explicit white item background so the
#      pairing is guaranteed either way.
#
# Idempotent. The PL Bridge Desktop instance must be closed.
import json
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / "PL Bridge Demo.Report" / "definition" / "pages"

probe = ("if (Get-Process PBIDesktop -EA SilentlyContinue | "
         "Where-Object { $_.MainWindowTitle -match 'PL Bridge' }) { exit 1 } else { exit 0 }")
if subprocess.run(["powershell", "-NoProfile", "-Command", probe],
                  capture_output=True).returncode != 0:
    sys.exit("ABORT: the PL Bridge Desktop instance is running - close it first.")

target = None
for pj in PAGES.glob("*/page.json"):
    d = json.loads(pj.read_text(encoding="utf-8"))
    if "Duplicate of P&L - Deneb" in d.get("displayName", ""):
        target = pj.parent
        break
if not target:
    sys.exit("ABORT: duplicate page not found")

gid = lambda s: uuid.uuid5(uuid.NAMESPACE_URL, "plbridge/sidepanel/" + s).hex[:20]
lit = lambda v: {"expr": {"Literal": {"Value": v}}}
solid = lambda h: {"solid": {"color": lit(f"'{h}'")}}

INK = "#0B1E3F"
ITEM = "#B8D9F2"
WHITE = "#FFFFFF"
SEGOE = "Segoe UI"

# ---------------------------------------------------------------- 1. orphaned marker
marker = target / "visuals" / gid("nav-marker")
if marker.exists():
    shutil.rmtree(marker)
    print("orphaned gold marker deleted")

# ---------------------------------------------------------------- 2. the navigator
for vj in (target / "visuals").glob("*/visual.json"):
    v = json.loads(vj.read_text(encoding="utf-8"))
    if v.get("visual", {}).get("visualType") != "pageNavigator":
        continue
    v["position"].update(x=40, y=182, width=232, height=274, z=110)
    v["visual"]["objects"] = {
        "fill": [
            {"properties": {"fillColor": solid(WHITE), "transparency": lit("100D")},
             "selector": {"id": "default"}},
            {"properties": {"fillColor": solid(WHITE), "transparency": lit("94D")},
             "selector": {"id": "hover"}},
            {"properties": {"fillColor": solid(WHITE), "transparency": lit("88D")},
             "selector": {"id": "press"}},
            {"properties": {"fillColor": solid(WHITE), "transparency": lit("90D")},
             "selector": {"id": "selected"}},
        ],
        "outline": [
            {"properties": {"show": lit("false")}},
        ],
        "text": [
            {"properties": {
                "fontColor": solid(ITEM), "fontSize": lit("10D"),
                "fontFamily": lit(f"'{SEGOE}'"), "bold": lit("false")},
             "selector": {"id": "default"}},
            {"properties": {"fontColor": solid(WHITE)},
             "selector": {"id": "hover"}},
            {"properties": {
                "fontColor": solid(WHITE), "bold": lit("true")},
             "selector": {"id": "selected"}},
        ],
    }
    v["visual"]["visualContainerObjects"] = {
        "border": [{"properties": {"show": lit("false")}}],
        "dropShadow": [{"properties": {"show": lit("false")}}],
        "visualHeader": [{"properties": {"show": lit("false")}}],
        "background": [{"properties": {"show": lit("false")}}],
    }
    vj.write_text(json.dumps(v, indent=2, ensure_ascii=False), encoding="utf-8")
    print("pageNavigator styled for the rail")
    break
else:
    sys.exit("ABORT: no pageNavigator found on the page")

# ---------------------------------------------------------------- 3. slicer contrast
fixed = 0
for vj in (target / "visuals").glob("*/visual.json"):
    v = json.loads(vj.read_text(encoding="utf-8"))
    if v.get("visual", {}).get("visualType") != "slicer":
        continue
    obj = v["visual"].setdefault("objects", {})
    # chip + popup ground is white -> ink text on an explicit white item background
    obj["items"] = [{"properties": {
        "fontColor": solid(INK),
        "background": solid(WHITE),
        "textSize": lit("10D"),
        "fontFamily": lit(f"'{SEGOE}'"),
    }}]
    vj.write_text(json.dumps(v, indent=2, ensure_ascii=False), encoding="utf-8")
    fixed += 1
print(f"slicer items recolored ink-on-white on {fixed} slicers (headers stay light-on-navy)")
print("done")
