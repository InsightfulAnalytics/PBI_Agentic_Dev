# Applies the Forge-style side panel to the "Duplicate of P&L - Deneb" test page.
#
#   python apply_side_panel.py            Direction A: navy gradient rail + gold accent
#   python apply_side_panel.py --ink      Direction B: flat ink rail + blue accent
#   python apply_side_panel.py --dry-run
#
# What it does (idempotent -- all ids are uuid5-seeded, re-running overwrites in place):
#   1. registers design/side_panel[_ink].svg as a RegisteredResources item in report.json
#   2. sets it as the test page's background (Fill, 0% transparency)
#   3. moves the page's existing visuals (title / Deneb statement / footer) into the
#      canvas area right of the 280px rail, and gives the statement a white card
#   4. builds the rail: brand block, REPORT SECTIONS nav (5 page-navigation buttons +
#      a gold active marker), KEY SELECTIONS (Month / State / Category dropdown
#      slicers restyled white-on-navy, cloned from the Fast Bridge page's proven
#      column bindings), and a footnote block
#
# POWER BI DESKTOP MUST BE CLOSED -- it re-serialises the project on close and reverts
# disk edits made while it runs (seen twice on this project).
import copy
import json
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "PL Bridge Demo.Report"
DEF = REPORT / "definition"
PAGES = DEF / "pages"
DESIGN = ROOT / "design"

INK = "--ink" in sys.argv
DRY = "--dry-run" in sys.argv

SVG_SRC = DESIGN / ("side_panel_ink.svg" if INK else "side_panel.svg")
SVG_RES = "side_panel_ink.svg" if INK else "side_panel.svg"
ACCENT = "#1E6FD9" if INK else "#FFB703"     # active marker; matches the SVG's brand rule

# rail text palette (Claude Design family)
T_WHITE = "#FFFFFF"
T_HEAD = "#5DA9E9"      # section header caps
T_ITEM = "#B8D9F2"      # inactive nav / labels
T_SUB = "#8ECAE6"       # brand subtitle / slicer headers
T_FOOT = "#6E89AC"      # footnotes (muted, no alpha support in textboxes)

SEGOE = "Segoe UI"
SEGOE_SB = "Segoe UI Semibold"

if not DRY:
    # only the instance holding THIS project is dangerous; another project's Desktop is fine
    probe = ("if (Get-Process PBIDesktop -EA SilentlyContinue | "
             "Where-Object { $_.MainWindowTitle -match 'PL Bridge' }) { exit 1 } else { exit 0 }")
    if subprocess.run(["powershell", "-NoProfile", "-Command", probe],
                      capture_output=True).returncode != 0:
        sys.exit("ABORT: Power BI Desktop is running - close it first.")

# ---------------------------------------------------------------- find the test page
target = None
for pj in PAGES.glob("*/page.json"):
    d = json.loads(pj.read_text(encoding="utf-8"))
    if "Duplicate of P&L - Deneb" in d.get("displayName", ""):
        target = pj.parent
        page = d
        break
if not target:
    sys.exit("ABORT: no page named 'Duplicate of P&L - Deneb' on disk yet - "
             "duplicate the page in Desktop and close it (saving) first.")
print(f"target page: {target.name}  ({page['displayName']})")

gid = lambda s: uuid.uuid5(uuid.NAMESPACE_URL, "plbridge/sidepanel/" + s).hex[:20]
lit = lambda v: {"expr": {"Literal": {"Value": v}}}
solid = lambda hexc: {"solid": {"color": lit(f"'{hexc}'")}}

if DRY:
    print(f"DRY RUN: would register {SVG_RES}, restyle {target.name}, accent {ACCENT}")
    sys.exit(0)

# ---------------------------------------------------------------- 1. register the SVG
shutil.copy(SVG_SRC, REPORT / "StaticResources" / "RegisteredResources" / SVG_RES)
rj = DEF / "report.json"
rep = json.loads(rj.read_text(encoding="utf-8"))
for pkg in rep["resourcePackages"]:
    if pkg["name"] == "RegisteredResources":
        if not any(i["name"] == SVG_RES for i in pkg["items"]):
            pkg["items"].append({"name": SVG_RES, "path": SVG_RES, "type": "Image"})
        break
rj.write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"registered {SVG_RES}")

# ---------------------------------------------------------------- 2. page background
page.setdefault("objects", {})["background"] = [{
    "properties": {
        "image": {"image": {
            "name": lit(f"'{SVG_RES}'"),
            "url": {"expr": {"ResourcePackageItem": {
                "PackageName": "RegisteredResources", "PackageType": 1,
                "ItemName": SVG_RES}}},
            "scaling": lit("'Fill'"),
        }},
        "transparency": lit("0D"),
    }
}]
(target / "page.json").write_text(json.dumps(page, indent=2, ensure_ascii=False),
                                  encoding="utf-8")
print("page background set")

# ---------------------------------------------------------------- 3. move existing visuals
# canvas content column: x336 .. 1944 (rail edge 296 + 40 padding, card edge 1984 - 40)
moved = 0
for vj in (target / "visuals").glob("*/visual.json"):
    v = json.loads(vj.read_text(encoding="utf-8"))
    vt = v.get("visual", {}).get("visualType", "")
    pos = v["position"]
    if vt == "textbox" and pos["y"] < 110:                       # the title strip
        pos.update(x=336, y=36, width=1400, height=84)
    elif vt.startswith("deneb"):                                 # the statement
        pos.update(x=336, y=132, width=1608, height=740)
        vco = v["visual"].setdefault("visualContainerObjects", {})
        vco["background"] = [{"properties": {
            "show": lit("true"), "color": solid("#FFFFFF"), "transparency": lit("0D")}}]
        vco["border"] = [{"properties": {
            "show": lit("true"), "color": solid("#E2E8F0"), "radius": lit("12D")}}]
    elif vt == "textbox" and pos["y"] > 880:                     # the footer strip
        pos.update(x=336, y=892, width=1608, height=40)
    else:
        continue
    vj.write_text(json.dumps(v, indent=2, ensure_ascii=False), encoding="utf-8")
    moved += 1
print(f"moved {moved} existing visuals into the canvas column")

# ---------------------------------------------------------------- 4. rail visuals
VC = ("https://developer.microsoft.com/json-schemas/fabric/item/report/definition"
      "/visualContainer/2.12.0/schema.json")

def write_visual(v):
    d = target / "visuals" / v["name"]
    d.mkdir(parents=True, exist_ok=True)
    (d / "visual.json").write_text(json.dumps(v, indent=2, ensure_ascii=False),
                                   encoding="utf-8")

def textbox(seed, x, y, w, h, paras, z):
    runs = [{"textRuns": [{"value": t, "textStyle": s}]} for t, s in paras]
    return {"$schema": VC, "name": gid(seed),
            "position": {"x": x, "y": y, "z": z, "height": h, "width": w},
            "visual": {"visualType": "textbox",
                       "objects": {"general": [{"properties": {"paragraphs": runs}}]},
                       "drillFilterOtherVisuals": True}}

# brand block (the SVG's gold rule sits at y=120)
write_visual(textbox("brand", 40, 34, 232, 62, [
    ("P&L BRIDGE", {"fontFamily": SEGOE_SB, "fontSize": "16pt", "color": T_WHITE}),
    ("Fast financial statements", {"fontFamily": SEGOE, "fontSize": "9pt", "color": T_SUB}),
], 100))

# section headers
write_visual(textbox("hdr-sections", 40, 150, 232, 24, [
    ("REPORT SECTIONS", {"fontFamily": SEGOE_SB, "fontSize": "9pt", "color": T_HEAD}),
], 100))
write_visual(textbox("hdr-selections", 40, 470, 232, 24, [
    ("KEY SELECTIONS", {"fontFamily": SEGOE_SB, "fontSize": "9pt", "color": T_HEAD}),
], 100))

# nav buttons -> real pages
NAV = [
    ("Overview", "97a3709ce8674f258672", False),
    ("Classic SWITCH", "a24ea46aa1eb4b549c33", False),
    ("Fast Bridge", "b21669a248904517a392", False),
    ("P&L Deneb", "651701ace98657389c2a", True),
    ("Odd Rows Deneb", "a7920d23ea7852528ab4", False),
]
y = 184
for label, dest, active in NAV:
    btn = {
        "$schema": VC, "name": gid("nav/" + label),
        "position": {"x": 40, "y": y, "z": 110, "height": 40, "width": 232},
        "visual": {
            "visualType": "actionButton",
            "objects": {
                "icon": [{"properties": {"shapeType": lit("'blank'")},
                          "selector": {"id": "default"}},
                         {"properties": {"show": lit("false")}}],
                "outline": [{"properties": {"show": lit("false")}}],
                "fill": [
                    {"properties": {"show": lit("true" if active else "false")}},
                    {"properties": {"fillColor": solid("#FFFFFF"),
                                    "transparency": lit("90D")},
                     "selector": {"id": "default"}},
                ],
                "text": [
                    {"properties": {"show": lit("true")}},
                    {"properties": {
                        "text": lit(f"'  {label}'"),
                        "fontColor": solid(T_WHITE if active else T_ITEM),
                        "fontSize": lit("10D"),
                        "bold": lit("true" if active else "false"),
                        "horizontalAlignment": lit("'left'"),
                        "fontFamily": lit(f"'{SEGOE}'"),
                    }, "selector": {"id": "default"}},
                ],
                "visualLink": [{"properties": {
                    "show": lit("true"),
                    "type": lit("'PageNavigation'"),
                    "navigationSection": lit(f"'{dest}'"),
                    "tooltip": lit(f"'Go to {label}'"),
                }}],
            },
            "visualContainerObjects": {
                "border": [{"properties": {"show": lit("false")}}],
                "dropShadow": [{"properties": {"show": lit("false")}}],
                "visualHeader": [{"properties": {"show": lit("false")}}],
            },
            "drillFilterOtherVisuals": True,
        },
    }
    write_visual(btn)
    if active:
        # the gold (or blue) active marker bar over the button's left edge
        write_visual({
            "$schema": VC, "name": gid("nav-marker"),
            "position": {"x": 40, "y": y, "z": 120, "height": 40, "width": 3},
            "visual": {"visualType": "shape",
                       "objects": {
                           "shape": [{"properties": {"tileShape": lit("'rectangle'")}}],
                           "fill": [{"properties": {
                               "fillColor": solid(ACCENT), "show": lit("true"),
                               "transparency": lit("0D")}}],
                           "outline": [{"properties": {"show": lit("false")}}],
                       },
                       "visualContainerObjects": {
                           "border": [{"properties": {"show": lit("false")}}],
                           "visualHeader": [{"properties": {"show": lit("false")}}],
                       },
                       "drillFilterOtherVisuals": True},
        })
    y += 48

# slicers: clone the Fast Bridge page's proven column bindings, restyle for the rail
SRC_PAGE = PAGES / "b21669a248904517a392" / "visuals"
want = {"DimDate.Month": "Month", "Stores.State": "State", "Products.Category": "Category"}
slicer_srcs = {}
for vj in SRC_PAGE.glob("*/visual.json"):
    v = json.loads(vj.read_text(encoding="utf-8"))
    if v.get("visual", {}).get("visualType") != "slicer":
        continue
    qs = v["visual"]["query"]["queryState"]
    for b in qs.values():
        for p in b.get("projections", []):
            if p["queryRef"] in want:
                slicer_srcs[p["queryRef"]] = v
assert len(slicer_srcs) == 3, f"expected 3 source slicers, found {list(slicer_srcs)}"

y = 502
for ref, label in want.items():
    s = copy.deepcopy(slicer_srcs[ref])
    s["name"] = gid("slicer/" + label)
    s["position"] = {"x": 40, "y": y, "z": 110, "height": 82, "width": 232}
    obj = s["visual"].setdefault("objects", {})
    obj["data"] = [{"properties": {"mode": lit("'Dropdown'")}}]
    obj["header"] = [{"properties": {
        "show": lit("true"), "text": lit(f"'{label}'"),
        "fontColor": solid(T_SUB), "textSize": lit("9D"),
        "fontFamily": lit(f"'{SEGOE}'"),
    }}]
    obj["items"] = [{"properties": {
        "fontColor": solid(T_WHITE), "textSize": lit("10D"),
        "fontFamily": lit(f"'{SEGOE}'"),
    }}]
    s["visual"]["visualContainerObjects"] = {
        "background": [{"properties": {"show": lit("false")}}],
        "border": [{"properties": {"show": lit("false")}}],
        "visualHeader": [{"properties": {"show": lit("false")}}],
    }
    write_visual(s)
    y += 94

# footnotes
write_visual(textbox("footnotes", 40, 902, 232, 56, [
    ("Brightside Home & Living (synthetic)",
     {"fontFamily": SEGOE, "fontSize": "8pt", "color": T_FOOT}),
    ("Year 2026, Selected Period",
     {"fontFamily": SEGOE, "fontSize": "8pt", "color": T_FOOT}),
], 100))

print("rail built: brand, 2 headers, 5 nav buttons + marker, 3 slicers, footnotes")
print("done - validate with: pbir validate \"PL Bridge Demo.Report\"")
