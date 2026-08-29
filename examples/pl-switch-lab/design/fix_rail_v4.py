# Fourth pass on the "Duplicate of P&L - Deneb" rail (2026-08-25):
#
#   1. NAVIGATOR TEXT WAS INVISIBLE. Two repairs, belt and braces:
#      - restore the `layout` object my v3 wholesale-replace clobbered (base-theme
#        shape: orientation 2 = auto, which stacks vertically in a tall frame) and a
#        soft `shape.roundEdge`
#      - put the light text color in an UN-SELECTORED base text entry (applies to every
#        state) as well as the per-state entries, and lead text/fill with an explicit
#        un-selectored `show: true`, matching the shape every working themed example
#        uses. The base Fluent2 theme colors navigator text `foreground` (ink) -- on the
#        navy rail that is invisible if a selector-scoped override fails to land.
#   2. SLICER HEADER BACKGROUNDS -> fully transparent via Tim's measure trick: the
#      header background is bound to [UI Transparent] ("#FFFFFF00") by conditional
#      formatting, because the static picker cannot express alpha.
#
# Run add_ui_measures.py FIRST (creates the measure). Idempotent. Desktop closed.
import json
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

# the measure must exist or every bound header silently breaks at render
tmdl = (ROOT / "PL Bridge Demo.SemanticModel" / "definition" / "tables"
        / "00_Measures.tmdl").read_text(encoding="utf-8")
if "measure 'UI Transparent'" not in tmdl:
    sys.exit("ABORT: [UI Transparent] not in the model - run add_ui_measures.py first.")

target = None
for pj in PAGES.glob("*/page.json"):
    d = json.loads(pj.read_text(encoding="utf-8"))
    if "Duplicate of P&L - Deneb" in d.get("displayName", ""):
        target = pj.parent
        break
if not target:
    sys.exit("ABORT: duplicate page not found")

lit = lambda v: {"expr": {"Literal": {"Value": v}}}
solid = lambda h: {"solid": {"color": lit(f"'{h}'")}}
TRANSPARENT = {"solid": {"color": {"expr": {"Measure": {
    "Expression": {"SourceRef": {"Entity": "00_Measures"}},
    "Property": "UI Transparent"}}}}}

ITEM, WHITE, INK, SUB = "#B8D9F2", "#FFFFFF", "#0B1E3F", "#8ECAE6"
SEGOE = "Segoe UI"

# ---------------------------------------------------------------- 1. navigator repair
for vj in (target / "visuals").glob("*/visual.json"):
    v = json.loads(vj.read_text(encoding="utf-8"))
    if v.get("visual", {}).get("visualType") != "pageNavigator":
        continue
    v["visual"]["objects"] = {
        "layout": [{"properties": {
            "orientation": lit("2D"),      # auto: stacks vertically in a tall frame
            "cellPadding": lit("4L")}}],
        "shape": [{"properties": {"roundEdge": lit("8L")},
                   "selector": {"id": "default"}}],
        "fill": [
            {"properties": {"show": lit("true")}},
            {"properties": {"fillColor": solid(WHITE), "transparency": lit("100D")},
             "selector": {"id": "default"}},
            {"properties": {"fillColor": solid(WHITE), "transparency": lit("94D")},
             "selector": {"id": "hover"}},
            {"properties": {"fillColor": solid(WHITE), "transparency": lit("88D")},
             "selector": {"id": "press"}},
            {"properties": {"fillColor": solid(WHITE), "transparency": lit("90D")},
             "selector": {"id": "selected"}},
        ],
        "outline": [{"properties": {"show": lit("false")}}],
        "text": [
            # un-selectored base: applies whatever happens with per-state merging
            {"properties": {
                "show": lit("true"),
                "fontColor": solid(ITEM), "fontSize": lit("10D"),
                "fontFamily": lit(f"'{SEGOE}'")}},
            {"properties": {"fontColor": solid(ITEM)},
             "selector": {"id": "default"}},
            {"properties": {"fontColor": solid(WHITE)},
             "selector": {"id": "hover"}},
            {"properties": {"fontColor": solid(WHITE), "bold": lit("true")},
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
    print("navigator repaired: layout restored, base text entry added")
    break

# ---------------------------------------------------------------- 2. slicer headers
fixed = 0
for vj in (target / "visuals").glob("*/visual.json"):
    v = json.loads(vj.read_text(encoding="utf-8"))
    if v.get("visual", {}).get("visualType") != "slicer":
        continue
    obj = v["visual"].setdefault("objects", {})
    hdr = obj.get("header", [{"properties": {}}])
    props = hdr[0].setdefault("properties", {})
    props["background"] = TRANSPARENT
    props["fontColor"] = solid(SUB)
    props["show"] = lit("true")
    obj["header"] = hdr
    vj.write_text(json.dumps(v, indent=2, ensure_ascii=False), encoding="utf-8")
    fixed += 1
print(f"slicer headers bound to [UI Transparent] on {fixed} slicers")
print("done")
