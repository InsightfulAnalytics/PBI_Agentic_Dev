# Top Strip pass 3 (2026-08-26):
#
#   1. Products[Category] value "(Not product-related)" -> "Non-Product", as an M
#      ReplaceValue step in the Products partition (no report/model references to
#      the old value exist -- grepped). NEEDS A PRODUCTS REFRESH in Desktop after
#      reopening (right-click Products in the Data pane -> Refresh data).
#   2. The strip pageNavigator restyled to match the rail's button-slicer chips:
#      translucent white fill, light-blue text, 8px corners; selected = solid gold
#      + ink bold. Plus a visual title "Page Navigation" styled like the slicer
#      headings (background bound to [UI Transparent] -- the theme paints it white).
#
# Idempotent. POWER BI DESKTOP (PL Bridge) MUST BE CLOSED.
import json
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "PL Bridge Demo.Report" / "definition" / "pages" / "f88c66924ae95c178089"
PRODUCTS = ROOT / "PL Bridge Demo.SemanticModel" / "definition" / "tables" / "Products.tmdl"

seed = lambda s: uuid.uuid5(uuid.NAMESPACE_URL, "plbridge/topstrip/" + s).hex[:20]
NAV = seed("visual/80c6d09e066318d68716")

probe = ("if (Get-Process PBIDesktop -EA SilentlyContinue | "
         "Where-Object { $_.MainWindowTitle -match 'PL Bridge' }) { exit 1 } else { exit 0 }")
if subprocess.run(["powershell", "-NoProfile", "-Command", probe],
                  capture_output=True).returncode != 0:
    sys.exit("ABORT: the PL Bridge Desktop instance is running - close it first.")

lit = lambda v: {"expr": {"Literal": {"Value": v}}}
solid = lambda h: {"solid": {"color": lit(f"'{h}'")}}
ITEM, WHITE, INK, SUB, GOLD = "#B8D9F2", "#FFFFFF", "#0B1E3F", "#8ECAE6", "#FFB703"
SEGOE = "Segoe UI"
TRANSPARENT = {"solid": {"color": {"expr": {"Measure": {
    "Expression": {"SourceRef": {"Entity": "00_Measures"}},
    "Property": "UI Transparent"}}}}}

# ------------------------------------------------------------ 1. category rename
txt = PRODUCTS.read_text(encoding="utf-8")
OLD_SRC = '''				let
				    Source = Parquet.Document(File.Contents("B:\\VS Code Files\\PBI Projects\\PL Switch Lab\\data\\demo\\products.parquet"))
				in
				    Source'''
NEW_SRC = '''				let
				    Source = Parquet.Document(File.Contents("B:\\VS Code Files\\PBI Projects\\PL Switch Lab\\data\\demo\\products.parquet")),
				    Renamed = Table.ReplaceValue(Source, "(Not product-related)", "Non-Product", Replacer.ReplaceValue, {"Category"})
				in
				    Renamed'''
if "Non-Product" in txt:
    print("category   : rename step already present")
elif OLD_SRC in txt:
    PRODUCTS.write_text(txt.replace(OLD_SRC, NEW_SRC), encoding="utf-8")
    print("category   : '(Not product-related)' -> 'Non-Product' (M step added)")
else:
    sys.exit("ABORT: Products partition source did not match - inspect manually")

# ------------------------------------------------------------ 2. navigator chips
nav_path = PAGE / "visuals" / NAV / "visual.json"
nav = json.loads(nav_path.read_text(encoding="utf-8"))
nav["position"].update(y=16, height=92)
obj = nav["visual"]["objects"]
obj["fill"] = [
    {"properties": {"show": lit("true")}},
    {"properties": {"fillColor": solid(WHITE), "transparency": lit("92D")},
     "selector": {"id": "default"}},
    {"properties": {"fillColor": solid(WHITE), "transparency": lit("84D")},
     "selector": {"id": "hover"}},
    {"properties": {"fillColor": solid(WHITE), "transparency": lit("80D")},
     "selector": {"id": "press"}},
    {"properties": {"fillColor": solid(GOLD), "transparency": lit("0D")},
     "selector": {"id": "selected"}},
]
obj["text"] = [
    {"properties": {
        "show": lit("true"), "fontColor": solid(ITEM),
        "fontSize": lit("9.5D"), "fontFamily": lit(f"'{SEGOE}'")}},
    {"properties": {"fontColor": solid(ITEM)}, "selector": {"id": "default"}},
    {"properties": {"fontColor": solid(WHITE)}, "selector": {"id": "hover"}},
    {"properties": {"fontColor": solid(INK), "bold": lit("true")},
     "selector": {"id": "selected"}},
]
obj["outline"] = [{"properties": {"show": lit("false")}}]
obj["shape"] = [{"properties": {"roundEdge": lit("8L")}, "selector": {"id": "default"}}]
vco = nav["visual"].setdefault("visualContainerObjects", {})
vco["title"] = [{"properties": {
    "show": lit("true"), "text": lit("'Page Navigation'"),
    "fontColor": solid(SUB), "fontSize": lit("9D"),
    "fontFamily": lit(f"'{SEGOE}'"), "bold": lit("true"),
    "alignment": lit("'left'"),
    "background": TRANSPARENT}}]
nav_path.write_text(json.dumps(nav, indent=2, ensure_ascii=False), encoding="utf-8")
print("navigator  : chip styling (gold selected), title 'Page Navigation', y16 h92")
