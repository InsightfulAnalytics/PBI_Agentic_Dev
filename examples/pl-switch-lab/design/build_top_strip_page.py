# Builds "P&L - Deneb Top Strip" -- a comparison twin of "Duplicate of P&L - Deneb"
# whose background is the L-frame chrome (side_panel_top.svg: same navy rail + a
# matching strip across the top), with the page title restyled to sit ON the strip
# (white title, light-blue subtitle). Requested 2026-08-26.
#
#   1. registers design/side_panel_top.svg as a RegisteredResources item
#   2. clones the duplicate page; every visual name and every filterConfig filter
#      name regenerated (uuid5-seeded -- duplicated filter names across pages break
#      Desktop open, verified 2026-08-23)
#   3. sets the clone's background to the new SVG, restyles + repositions the title
#   4. registers the page in pages.json right after the source page
#
# Idempotent: re-running rebuilds the clone from the CURRENT source page state.
# POWER BI DESKTOP (PL Bridge) MUST BE CLOSED.
import json
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "PL Bridge Demo.Report"
PAGES = REPORT / "definition" / "pages"
DESIGN = ROOT / "design"

SRC_PAGE = "a166625774b3ef84e99f"        # Duplicate of P&L - Deneb
SVG_RES = "side_panel_top.svg"
TITLE_SRC = "f6421a5b31eb8382e244"       # the title textbox on the source page

seed = lambda s: uuid.uuid5(uuid.NAMESPACE_URL, "plbridge/topstrip/" + s).hex[:20]
NEW_PAGE = seed("page")

WHITE, SUB = "#FFFFFF", "#B8D9F2"

probe = ("if (Get-Process PBIDesktop -EA SilentlyContinue | "
         "Where-Object { $_.MainWindowTitle -match 'PL Bridge' }) { exit 1 } else { exit 0 }")
if subprocess.run(["powershell", "-NoProfile", "-Command", probe],
                  capture_output=True).returncode != 0:
    sys.exit("ABORT: the PL Bridge Desktop instance is running - close it first.")

read = lambda p: json.loads(p.read_text(encoding="utf-8"))
def write(p, obj):
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")

# ------------------------------------------------------------ 1. the resource
shutil.copy(DESIGN / SVG_RES, REPORT / "StaticResources" / "RegisteredResources" / SVG_RES)
rj_path = REPORT / "definition" / "report.json"
rep = read(rj_path)
for pkg in rep["resourcePackages"]:
    if pkg["name"] == "RegisteredResources":
        pkg["items"] = [i for i in pkg["items"] if i["name"] != SVG_RES]
        pkg["items"].append({"name": SVG_RES, "path": SVG_RES, "type": "Image"})
write(rj_path, rep)
print(f"registered  : {SVG_RES}")

# ------------------------------------------------------------ 2. clone the page
dst = PAGES / NEW_PAGE
if dst.exists():
    shutil.rmtree(dst)
shutil.copytree(PAGES / SRC_PAGE, dst)

renames = {d.name: seed("visual/" + d.name) for d in sorted((dst / "visuals").iterdir())}
for old, new in renames.items():
    (dst / "visuals" / old).rename(dst / "visuals" / new)

def regen_filters(obj, scope):
    n = 0
    for f in obj.get("filterConfig", {}).get("filters", []):
        if "name" in f:
            f["name"] = seed(f"filter/{scope}/{f['name']}")
            n += 1
    return n

nfilt = 0
for vdir in (dst / "visuals").iterdir():
    v = read(vdir / "visual.json")
    v["name"] = vdir.name
    nfilt += regen_filters(v, vdir.name)
    write(vdir / "visual.json", v)

# ------------------------------------------------------------ 3. page + title
lit = lambda v: {"expr": {"Literal": {"Value": v}}}
page = read(dst / "page.json")
page["name"] = NEW_PAGE
page["displayName"] = "P&L - Deneb Top Strip"
nfilt += regen_filters(page, "page")
page.setdefault("objects", {})["background"] = [{"properties": {
    "image": {"image": {
        "name": lit(f"'{SVG_RES}'"),
        "url": {"expr": {"ResourcePackageItem": {
            "PackageName": "RegisteredResources", "PackageType": 1,
            "ItemName": SVG_RES}}},
        "scaling": lit("'Fill'")}},
    "transparency": lit("0D"),
}}]
write(dst / "page.json", page)

title_path = dst / "visuals" / renames[TITLE_SRC] / "visual.json"
tv = read(title_path)
# onto the strip (16..120): white title, light-blue subtitle
tv["position"].update(y=26, height=88)
paras = tv["visual"]["objects"]["general"][0]["properties"]["paragraphs"]
paras[0]["textRuns"][0]["textStyle"]["color"] = WHITE
paras[1]["textRuns"][0]["textStyle"]["color"] = SUB
write(title_path, tv)
print(f"page        : {NEW_PAGE}  '{page['displayName']}'  ({nfilt} filter names regenerated)")
print("title       : restyled white/light-blue, y 36->26 h 84->88")

# ------------------------------------------------------------ 4. pages.json
pj_path = PAGES / "pages.json"
pj = read(pj_path)
order = [p for p in pj["pageOrder"] if p != NEW_PAGE]
order.insert(order.index(SRC_PAGE) + 1, NEW_PAGE)
pj["pageOrder"] = order
write(pj_path, pj)
print(f"pageOrder   : position {order.index(NEW_PAGE) + 1} of {len(order)}")
