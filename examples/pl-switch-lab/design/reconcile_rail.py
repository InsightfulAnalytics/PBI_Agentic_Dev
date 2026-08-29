# Reconciles the side-panel rail on "Duplicate of P&L - Deneb" with what Tim had
# already placed there before the rail was applied (found 2026-08-25):
#
#   - his BI Nexus logo image        -> becomes the brand block, on a white rounded
#                                       plate (the JPG has a white ground; on navy it
#                                       must sit on a deliberate chip, not float)
#   - four advancedSlicerVisuals     -> their FIELD choices win (Year, Month Name
#     (Year / Month Name Short /        Short, Channel, Category) but the visuals are
#      Channel / Category)             replaced: the new-style slicer has no Dropdown
#                                       mode and its tile layout cannot fit the rail.
#                                       Old-style dropdown slicers instead.
#   - my generic Month/State/Category rail slicers -> deleted (superseded)
#   - my "P&L BRIDGE" wordmark textbox -> deleted (the logo IS the brand)
#   - the page's inherited Year=2026 pin -> removed, so the Year slicer actually works
#     (Time Period = 'Selected Period' stays pinned; the fast measures dispatch on it)
#
# Idempotent. POWER BI DESKTOP (PL Bridge) MUST BE CLOSED.
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

target = None
for pj in PAGES.glob("*/page.json"):
    d = json.loads(pj.read_text(encoding="utf-8"))
    if "Duplicate of P&L - Deneb" in d.get("displayName", ""):
        target, page = pj.parent, d
        break
if not target:
    sys.exit("ABORT: duplicate page not found")
print("target:", target.name)

gid = lambda s: uuid.uuid5(uuid.NAMESPACE_URL, "plbridge/sidepanel/" + s).hex[:20]
lit = lambda v: {"expr": {"Literal": {"Value": v}}}
solid = lambda h: {"solid": {"color": lit(f"'{h}'")}}
VC = ("https://developer.microsoft.com/json-schemas/fabric/item/report/definition"
      "/visualContainer/2.12.0/schema.json")

import shutil

# ---------------------------------------------------------------- deletions
DROP_NAMES = {gid("slicer/Month"), gid("slicer/State"), gid("slicer/Category"),
              gid("brand")}
dropped = 0
for vj in list((target / "visuals").glob("*/visual.json")):
    v = json.loads(vj.read_text(encoding="utf-8"))
    vt = v.get("visual", {}).get("visualType", "")
    if v["name"] in DROP_NAMES or vt == "advancedSlicerVisual":
        shutil.rmtree(vj.parent)
        dropped += 1
print(f"dropped {dropped} superseded visuals")

# ---------------------------------------------------------------- logo as brand block
for vj in (target / "visuals").glob("*/visual.json"):
    v = json.loads(vj.read_text(encoding="utf-8"))
    if v.get("visual", {}).get("visualType") == "image":
        # centered in the rail (16..296), seated on a white plate above the gold rule (y=120)
        v["position"].update(x=92, y=14, width=129, height=95, z=110)
        vco = v["visual"].setdefault("visualContainerObjects", {})
        vco["background"] = [{"properties": {
            "show": lit("true"), "color": solid("#FFFFFF"), "transparency": lit("0D")}}]
        vco["border"] = [{"properties": {
            "show": lit("true"), "color": solid("#FFFFFF"), "radius": lit("8D")}}]
        vco["visualHeader"] = [{"properties": {"show": lit("false")}}]
        vj.write_text(json.dumps(v, indent=2, ensure_ascii=False), encoding="utf-8")
        print("logo repositioned onto the brand plate")
        break

# ---------------------------------------------------------------- the four dropdowns
SLICERS = [  # (entity, property, header label)
    ("DimDate", "Year", "Year"),
    ("DimDate", "Month Name Short", "Month"),
    ("Stores", "Channel", "Channel"),
    ("Products", "Category", "Category"),
]
T_SUB, T_WHITE = "#8ECAE6", "#FFFFFF"
y = 502
for entity, prop, label in SLICERS:
    s = {
        "$schema": VC, "name": gid("slicer2/" + label),
        "position": {"x": 40, "y": y, "z": 110, "height": 82, "width": 232},
        "visual": {
            "visualType": "slicer",
            "query": {"queryState": {"Values": {"projections": [{
                "field": {"Column": {"Expression": {"SourceRef": {"Entity": entity}},
                                     "Property": prop}},
                "queryRef": f"{entity}.{prop}",
                "nativeQueryRef": prop,
                "active": True,
            }]}}},
            "objects": {
                "data": [{"properties": {"mode": lit("'Dropdown'")}}],
                "header": [{"properties": {
                    "show": lit("true"), "text": lit(f"'{label}'"),
                    "fontColor": solid(T_SUB), "textSize": lit("9D"),
                    "fontFamily": lit("'Segoe UI'")}}],
                "items": [{"properties": {
                    "fontColor": solid(T_WHITE), "textSize": lit("10D"),
                    "fontFamily": lit("'Segoe UI'")}}],
            },
            "visualContainerObjects": {
                "background": [{"properties": {"show": lit("false")}}],
                "border": [{"properties": {"show": lit("false")}}],
                "visualHeader": [{"properties": {"show": lit("false")}}],
            },
            "drillFilterOtherVisuals": True,
        },
    }
    d = target / "visuals" / s["name"]
    d.mkdir(parents=True, exist_ok=True)
    (d / "visual.json").write_text(json.dumps(s, indent=2, ensure_ascii=False),
                                   encoding="utf-8")
    y += 94
print("4 rail dropdowns written (Year / Month / Channel / Category)")

# ---------------------------------------------------------------- unpin Year
fc = page.get("filterConfig", {})
before = len(fc.get("filters", []))
fc["filters"] = [f for f in fc.get("filters", [])
                 if f.get("field", {}).get("Column", {}).get("Property") != "Year"]
if len(fc["filters"]) != before:
    print("Year pin removed from the page filter (Time Period stays pinned)")
(target / "page.json").write_text(json.dumps(page, indent=2, ensure_ascii=False),
                                  encoding="utf-8")

# ---------------------------------------------------------------- footnote refresh
fn = target / "visuals" / gid("footnotes") / "visual.json"
if fn.exists():
    v = json.loads(fn.read_text(encoding="utf-8"))
    paras = v["visual"]["objects"]["general"][0]["properties"]["paragraphs"]
    if len(paras) == 2:
        paras[1]["textRuns"][0]["value"] = "Selected Period basis"
        fn.write_text(json.dumps(v, indent=2, ensure_ascii=False), encoding="utf-8")
        print("footnote updated (Year is a selection now, not a pin)")
print("done")
