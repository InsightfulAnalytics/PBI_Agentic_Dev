# Restyles the "P&L - Deneb Top Strip" page (f88c66924ae95c178089) per Tim's
# 2026-08-26 direction -- THIS PAGE ONLY:
#
#   1. page navigation moves onto the top strip as a 6x2 BUTTON GRID.
#      pageNavigator text cannot wrap (schema-verified: text has 13 props, no
#      wordWrap) -- the solve is layout-level: two rows of wide buttons
#      (layout.rowCount/columnCount) so names fit on one line, and the old
#      "Duplicate of P&L - Deneb" test page hidden from the nav (pages.showPage).
#   2. the four rail dropdowns become BUTTON slicers (advancedSlicerVisual,
#      style Cards) filling the rail below the gold line. State contract copied
#      from Desktop-serialized examples: selectors default / interaction:hover /
#      selection:selected. Navy-rail styling: translucent white chips, light-blue
#      text; selected = solid gold + ink text.
#   3. REPORT SECTIONS label deleted (nav left the rail); KEY SELECTIONS moves up.
#   4. title textbox narrows so the nav fits beside it on the strip.
#
# Idempotent. POWER BI DESKTOP (PL Bridge) MUST BE CLOSED.
import json
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "PL Bridge Demo.Report" / "definition" / "pages" / "f88c66924ae95c178089"
VC = ("https://developer.microsoft.com/json-schemas/fabric/item/report/definition"
      "/visualContainer/2.9.0/schema.json")

seed = lambda s: uuid.uuid5(uuid.NAMESPACE_URL, "plbridge/topstrip/" + s).hex[:20]
NAV = seed("visual/80c6d09e066318d68716")        # the cloned pageNavigator
SECTIONS_TB = seed("visual/8b9961a1e00c5513b7db")  # "REPORT SECTIONS" label
KEYSEL_TB = seed("visual/00fb052bfc0b5a6b82b2")    # "KEY SELECTIONS" label
TITLE_TB = seed("visual/f6421a5b31eb8382e244")     # page title on the strip
HIDDEN_FROM_NAV = ["a166625774b3ef84e99f"]         # Duplicate of P&L - Deneb

probe = ("if (Get-Process PBIDesktop -EA SilentlyContinue | "
         "Where-Object { $_.MainWindowTitle -match 'PL Bridge' }) { exit 1 } else { exit 0 }")
if subprocess.run(["powershell", "-NoProfile", "-Command", probe],
                  capture_output=True).returncode != 0:
    sys.exit("ABORT: the PL Bridge Desktop instance is running - close it first.")
if not PAGE.exists():
    sys.exit("ABORT: Top Strip page not found - run build_top_strip_page.py first.")

lit = lambda v: {"expr": {"Literal": {"Value": v}}}
solid = lambda h: {"solid": {"color": lit(f"'{h}'")}}
read = lambda p: json.loads(p.read_text(encoding="utf-8"))
def write(p, obj):
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")

ITEM, WHITE, INK, SUB, GOLD = "#B8D9F2", "#FFFFFF", "#0B1E3F", "#8ECAE6", "#FFB703"
SEGOE = "Segoe UI"

# ------------------------------------------------ 1. navigator onto the strip
nav_path = PAGE / "visuals" / NAV / "visual.json"
nav = read(nav_path)
nav["position"].update(x=1016, y=18, width=928, height=84, z=110)
obj = nav["visual"]["objects"]
obj["layout"] = [{"properties": {
    "orientation": lit("2D"),
    "rowCount": lit("2L"), "columnCount": lit("6L"),
    "cellPadding": lit("4L")}}]
pages = [e for e in obj.get("pages", [])
         if e.get("selector", {}).get("id") not in HIDDEN_FROM_NAV]
for pid in HIDDEN_FROM_NAV:
    pages.append({"properties": {"showPage": lit("false")}, "selector": {"id": pid}})
obj["pages"] = pages
for entry in obj.get("text", []):
    if "selector" not in entry:      # the un-selectored base entry from fix_rail_v4
        entry["properties"]["fontSize"] = lit("9.5D")
write(nav_path, nav)
print("navigator  : onto the strip, 6x2 grid, duplicate page hidden from nav")

# ------------------------------------------------ 2. rail labels + title
if (PAGE / "visuals" / SECTIONS_TB).exists():
    shutil.rmtree(PAGE / "visuals" / SECTIONS_TB)
    print("deleted    : REPORT SECTIONS label")
ks_path = PAGE / "visuals" / KEYSEL_TB / "visual.json"
if ks_path.exists():
    ks = read(ks_path)
    ks["position"].update(y=132, height=24)
    write(ks_path, ks)
t_path = PAGE / "visuals" / TITLE_TB / "visual.json"
t = read(t_path)
t["position"].update(width=660)
write(t_path, t)
print("labels     : KEY SELECTIONS -> y132, title width -> 660")

# ------------------------------------------------ 3. button slicers on the rail
# drop the old dropdown slicers (any classic slicer on this page is one of ours)
dropped = 0
for vj in list((PAGE / "visuals").glob("*/visual.json")):
    if read(vj).get("visual", {}).get("visualType") == "slicer":
        shutil.rmtree(vj.parent)
        dropped += 1
print(f"dropped    : {dropped} dropdown slicers")

SLICERS = [  # (entity, property, title, y, height, cols, rows)
    ("DimDate", "Year",             "YEAR",     162, 96,  3, 1),
    ("DimDate", "Month Name Short", "MONTH",    270, 188, 4, 3),
    ("Stores", "Channel",           "CHANNEL",  470, 96,  3, 1),
    ("Products", "Category",        "CATEGORY", 578, 264, 2, 5),
]
for entity, prop, title, y, h, cols, rows in SLICERS:
    name = seed("btnslicer/" + prop)
    v = {
        "$schema": VC, "name": name,
        "position": {"x": 40, "y": y, "z": 110, "width": 232, "height": h},
        "visual": {
            "visualType": "advancedSlicerVisual",
            "query": {"queryState": {"Values": {"projections": [{
                "field": {"Column": {"Expression": {"SourceRef": {"Entity": entity}},
                                     "Property": prop}},
                "queryRef": f"{entity}.{prop}",
                "nativeQueryRef": prop,
            }]}}},
            "objects": {
                "layout": [{"properties": {
                    "style": lit("'Cards'"),
                    "rowCount": lit(f"{rows}L"), "columnCount": lit(f"{cols}L"),
                    "cellPadding": lit("4L")}}],
                "shapeCustomRectangle": [{"properties": {
                    "tileShape": lit("'rectangleRoundedByPixel'"),
                    "rectangleRoundedCurve": lit("8L"),
                    "rectangleRoundedCurveCustomStyle": lit("false")},
                    "selector": {"id": "default"}}],
                "fillCustom": [
                    {"properties": {"show": lit("true")}},
                    {"properties": {"fillColor": solid(WHITE), "transparency": lit("92D")},
                     "selector": {"id": "default"}},
                    {"properties": {"fillColor": solid(WHITE), "transparency": lit("84D")},
                     "selector": {"id": "interaction:hover"}},
                    {"properties": {"show": lit("true"), "fillColor": solid(GOLD),
                                    "transparency": lit("0D")},
                     "selector": {"id": "selection:selected"}},
                ],
                "value": [
                    {"properties": {
                        "fontColor": solid(ITEM), "fontSize": lit("10D"),
                        "fontFamily": lit(f"'{SEGOE}'"),
                        "horizontalAlignment": lit("'center'")},
                     "selector": {"id": "default"}},
                    {"properties": {"fontColor": solid(INK), "bold": lit("true")},
                     "selector": {"id": "selection:selected"}},
                ],
                "outline": [{"properties": {"show": lit("false")},
                             "selector": {"id": "default"}}],
                "selectionIcon": [{"properties": {"show": lit("false")}}],
                "label": [{"properties": {"show": lit("false")},
                           "selector": {"id": "default"}}],
                "padding": [{"properties": {"paddingSelection": lit("'Narrow'")},
                             "selector": {"id": "default"}}],
            },
            "visualContainerObjects": {
                "title": [{"properties": {
                    "show": lit("true"), "text": lit(f"'{title}'"),
                    "fontColor": solid(SUB), "fontSize": lit("9D"),
                    "fontFamily": lit(f"'{SEGOE}'"), "bold": lit("true"),
                    "alignment": lit("'left'")}}],
                "background": [{"properties": {"show": lit("false")}}],
                "border": [{"properties": {"show": lit("false")}}],
                "visualHeader": [{"properties": {"show": lit("false")}}],
                "dropShadow": [{"properties": {"show": lit("false")}}],
            },
            "drillFilterOtherVisuals": True,
        },
    }
    d = PAGE / "visuals" / name
    d.mkdir(parents=True, exist_ok=True)
    write(d / "visual.json", v)
print(f"slicers    : {len(SLICERS)} button slicers written (Cards, gold selected state)")
print("done")
