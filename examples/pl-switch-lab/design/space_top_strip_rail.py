# Top Strip rail pass 2 (2026-08-26, after Tim resized the button slicers in Desktop):
#
#   1. YEAR/MONTH/CHANNEL/CATEGORY heading backgrounds -> transparent. The theme's
#      *.*.title paints an opaque white bar; the static picker has no alpha, but
#      title.background is CF-bindable (schema-verified), so it gets bound to the
#      model's [UI Transparent] measure ("#FFFFFF00") -- Tim's slicer-header trick.
#   2. The four button slicers re-spaced EVENLY down the rail: their CURRENT
#      (Desktop-saved) heights and order are read from disk and redistributed with
#      equal gaps between the KEY SELECTIONS label and the footnotes block.
#
# Touches ONLY title.background and position.y on the four slicers.
# Idempotent. POWER BI DESKTOP (PL Bridge) MUST BE CLOSED.
import json
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "PL Bridge Demo.Report" / "definition" / "pages" / "f88c66924ae95c178089"

seed = lambda s: uuid.uuid5(uuid.NAMESPACE_URL, "plbridge/topstrip/" + s).hex[:20]
KEYSEL_TB = seed("visual/00fb052bfc0b5a6b82b2")
FOOTNOTES_TB = seed("visual/f3ff7506ec1655dd8f69")

probe = ("if (Get-Process PBIDesktop -EA SilentlyContinue | "
         "Where-Object { $_.MainWindowTitle -match 'PL Bridge' }) { exit 1 } else { exit 0 }")
if subprocess.run(["powershell", "-NoProfile", "-Command", probe],
                  capture_output=True).returncode != 0:
    sys.exit("ABORT: the PL Bridge Desktop instance is running - close it first.")

tmdl = (ROOT / "PL Bridge Demo.SemanticModel" / "definition" / "tables"
        / "00_Measures.tmdl").read_text(encoding="utf-8")
if "measure 'UI Transparent'" not in tmdl:
    sys.exit("ABORT: [UI Transparent] not in the model - run add_ui_measures.py first.")

read = lambda p: json.loads(p.read_text(encoding="utf-8"))
def write(p, obj):
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")

TRANSPARENT = {"solid": {"color": {"expr": {"Measure": {
    "Expression": {"SourceRef": {"Entity": "00_Measures"}},
    "Property": "UI Transparent"}}}}}

# ------------------------------------------------------------ collect the pieces
slicers = []
for vj in (PAGE / "visuals").glob("*/visual.json"):
    v = read(vj)
    if v.get("visual", {}).get("visualType") == "advancedSlicerVisual":
        slicers.append((vj, v))
if len(slicers) != 4:
    sys.exit(f"ABORT: expected 4 button slicers, found {len(slicers)}")

keysel = read(PAGE / "visuals" / KEYSEL_TB / "visual.json")
foot = read(PAGE / "visuals" / FOOTNOTES_TB / "visual.json")
top = keysel["position"]["y"] + keysel["position"]["height"]
bottom = foot["position"]["y"]

# ------------------------------------------------------------ 1. transparent headings
for vj, v in slicers:
    vco = v["visual"].setdefault("visualContainerObjects", {})
    entries = vco.setdefault("title", [{"properties": {}}])
    entries[0].setdefault("properties", {})["background"] = TRANSPARENT

# ------------------------------------------------------------ 2. even spacing
slicers.sort(key=lambda t: t[1]["position"]["y"])
heights = [v["position"]["height"] for _, v in slicers]
gap = (bottom - top - sum(heights)) / (len(slicers) + 1)
if gap < 4:
    print(f"WARNING: only {gap:.0f}px gap available - slicers overflow the rail region")
    gap = max(gap, 4)
y = top + gap
for (vj, v), h in zip(slicers, heights):
    v["position"]["y"] = round(y)
    write(vj, v)
    title = v["visual"]["visualContainerObjects"]["title"][0]["properties"]
    label = title.get("text", {}).get("expr", {}).get("Literal", {}).get("Value", "?")
    print(f"  {label:12s} y={round(y):4d} h={h:.0f}  (heading transparent)")
    y += h + gap
print(f"spaced {len(slicers)} slicers: region {top:.0f}..{bottom:.0f}, gap {gap:.1f}px")
