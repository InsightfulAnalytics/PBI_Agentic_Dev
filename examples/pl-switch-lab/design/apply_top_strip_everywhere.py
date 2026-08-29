# Rolls the "P&L - Deneb Top Strip" design out to every remaining report page, and deletes
# the explanation-only pages (2026-08-27, Tim's direction: "replicate the design and slicers
# to all the other report pages, remove description pages").
#
# The rail is CLONED from the template page rather than re-authored, so the design is
# identical by construction and stays identical if Tim nudges the template again:
#   logo, KEY SELECTIONS label, the 4 button slicers (Year / Month / Channel / Category),
#   the footnote block, the SVG background, and the title's position and styling.
# Every cloned visual gets a fresh uuid5-seeded name (duplicate visual or filter names across
# pages make Desktop open with "Issues were found" and an empty model).
#
# No page navigator: Tim removed it from the template as too busy.
#
# Deleted: pages whose only content is teaching material.
#   Bridge Accounts   - the 3-step recipe + sample bridge tables
#   Beyond Accounts   - the field-parameter hybrid write-up
#   plus the "How the Bridge Works" block living below y=1000 on the 2000x2000 Fast Bridge
#   page, which is the same material inlined.
#
# Idempotent: re-running re-clones the rail from the template and re-applies the layout.
# POWER BI DESKTOP (PL Bridge) MUST BE CLOSED.
import copy
import json
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / "PL Bridge Demo.Report" / "definition" / "pages"

TEMPLATE = "f88c66924ae95c178089"          # P&L - Deneb Top Strip
DROP_PAGES = {
    "6f052fb1dae3432863de": "Bridge Accounts",
    "00325cd3c3e742eca279": "Beyond Accounts",
}
# Fast Bridge carries the same teaching block below the fold; these are its ids.
FASTBRIDGE = "b21669a248904517a392"
FASTBRIDGE_DROP = {"b4739841", "09a50f6e", "2fbbafd0", "a7ba594b", "a760d1af", "7df725a5"}
# stray slicers sitting under the new top strip on the Odd Rows Deneb page
ODD_ROWS_DENEB = "a7920d23ea7852528ab4"
ODD_ROWS_DROP = {"f28fe48b", "795c6adb"}

W, H = 2000, 1000
CANVAS_X, CANVAS_W = 336, 1608          # right of the rail seam, inside the card
BODY_TOP, BODY_BOTTOM = 132, 952        # below the strip, above the card's bottom margin
RAIL_EDGE = 200                         # x below this is rail, above is canvas. Deliberately
                                        # loose: Desktop nudges leave x at 335.58, not 336.
TITLE = dict(x=CANVAS_X, y=26, width=1500, height=89)
WHITE, SUB = "#FFFFFF", "#B8D9F2"

probe = ("if (Get-Process PBIDesktop -EA SilentlyContinue | "
         "Where-Object { $_.MainWindowTitle -match 'PL Bridge' }) { exit 1 } else { exit 0 }")
if subprocess.run(["powershell", "-NoProfile", "-Command", probe],
                  capture_output=True).returncode != 0:
    sys.exit("ABORT: the PL Bridge Desktop instance is running - close it first.")

read = lambda p: json.loads(p.read_text(encoding="utf-8"))
def write(p, o): p.write_text(json.dumps(o, indent=2, ensure_ascii=False), encoding="utf-8")
seed = lambda s: uuid.uuid5(uuid.NAMESPACE_URL, "plbridge/rollout/" + s).hex[:20]

DATA_TYPES = {"deneb7E15AEF80B9E4D4F8E12924291ECE89A", "tableEx", "pivotTable"}

# ------------------------------------------------------------------ 1. drop pages
pj = read(PAGES / "pages.json")
for pid, name in DROP_PAGES.items():
    d = PAGES / pid
    if d.exists():
        shutil.rmtree(d)
        print(f"deleted page  : {name}")
pj["pageOrder"] = [p for p in pj["pageOrder"] if p not in DROP_PAGES]
for key in ("activePageName", "landingPageName"):
    if pj.get(key) in DROP_PAGES:
        pj[key] = pj["pageOrder"][0]
        print(f"  {key} repointed to {pj[key]}")
write(PAGES / "pages.json", pj)

# ------------------------------------------------------------------ 2. the template rail
tpl_page = read(PAGES / TEMPLATE / "page.json")
BACKGROUND = copy.deepcopy(tpl_page["objects"]["background"])
TIME_PERIOD_PIN = [f for f in tpl_page.get("filterConfig", {}).get("filters", [])]

rail, title_style = [], None
for vj in sorted((PAGES / TEMPLATE / "visuals").glob("*/visual.json")):
    v = read(vj)
    vt = v["visual"].get("visualType")
    if vt in DATA_TYPES:
        continue                                    # the template's own statement visual
    pos = v["position"]
    if vt == "textbox" and pos["x"] >= RAIL_EDGE:
        if pos["y"] < 200:                          # the page title, on the strip
            try:
                title_style = copy.deepcopy(
                    v["visual"]["objects"]["general"][0]["properties"]["paragraphs"])
            except Exception:
                pass
        continue                                    # canvas-side text is per page
    rail.append(v)
print(f"rail cloned   : {len(rail)} visuals "
      f"({', '.join(sorted({r['visual'].get('visualType','?') for r in rail}))})")
if title_style is None:
    sys.exit("ABORT: could not read the template title's paragraph styling")

def title_colours(paras):
    """Apply the template's white/light-blue title styling to a page's own title text."""
    for i, para in enumerate(paras):
        for run in para.get("textRuns", []):
            st = run.setdefault("textStyle", {})
            st["color"] = WHITE if i == 0 else SUB
            src = title_style[min(i, len(title_style) - 1)]["textRuns"][0].get("textStyle", {})
            for k in ("fontFamily", "fontSize"):
                if k in src:
                    st[k] = src[k]
    return paras

# ------------------------------------------------------------------ 3. each report page
targets = [p for p in pj["pageOrder"] if p != TEMPLATE]
for pid in targets:
    pdir = PAGES / pid
    page = read(pdir / "page.json")
    name = page["displayName"]

    # page-level: size, background, drop the Year pin so the rail slicer drives the year
    page["width"], page["height"] = W, H
    page.setdefault("objects", {})["background"] = copy.deepcopy(BACKGROUND)
    fc = page.setdefault("filterConfig", {}).setdefault("filters", [])
    kept = [f for f in fc
            if (f.get("field", {}).get("Column", {}) or {}).get("Property") != "Year"]
    dropped_year = len(fc) - len(kept)
    page["filterConfig"]["filters"] = kept
    for f in page["filterConfig"]["filters"]:
        if "name" in f:
            f["name"] = seed(f"pagefilter/{pid}/{f['name']}")

    # per-page visual clean-up.
    # NOTE: a target page has NO rail yet, so its visuals cannot be classified by x the way
    # the template's are - everything on it is content. Previously cloned rail visuals are
    # found by their deterministic seeded name instead, which is what makes this idempotent.
    drop = set()
    if pid == FASTBRIDGE:
        drop = FASTBRIDGE_DROP
    elif pid == ODD_ROWS_DENEB:
        drop = ODD_ROWS_DROP
    prior_rail = {seed(f"{pid}/{s['visual'].get('visualType','x')}/{s['name']}") for s in rail}
    removed = 0
    for vdir in list((pdir / "visuals").iterdir()):
        if vdir.name in prior_rail or any(vdir.name.startswith(p) for p in drop):
            shutil.rmtree(vdir)
            removed += 1

    # classify what is left, by role not by position on the page
    main, commentary, footer, titles = [], [], [], []
    for vj in sorted((pdir / "visuals").glob("*/visual.json")):
        v = read(vj)
        vt = v["visual"].get("visualType")
        pos = v["position"]
        if vt in DATA_TYPES:
            main.append((vj, v))
        elif vt == "textbox":
            if pos["y"] < 120:
                titles.append((vj, v))          # page title, moves onto the strip
            elif pos["height"] <= 60:
                footer.append((vj, v))          # one-line caption under the statement
            else:
                commentary.append((vj, v))      # explanatory block, re-flowed below
        elif vt in ("slicer", "advancedSlicerVisual"):
            shutil.rmtree(vj.parent); removed += 1      # rail supersedes page slicers
    commentary.sort(key=lambda t: t[1]["position"]["x"])

    # layout: main visual on top, commentary in one row beneath, all inside the canvas
    if commentary:
        # commentary must keep its ORIGINAL height or the text clips: three boxes across the
        # 1608 canvas are already narrower than they were, so height is the only slack left.
        gap = 16
        row_h = min(max(v["position"]["height"] for _, v in commentary),
                    BODY_BOTTOM - BODY_TOP - 20 - 300)      # leave the visual >= 300
        main_h = BODY_BOTTOM - BODY_TOP - 20 - row_h
        row_y = BODY_TOP + main_h + 20
        each = (CANVAS_W - gap * (len(commentary) - 1)) // len(commentary)
        for i, (vj, v) in enumerate(commentary):
            v["position"].update(x=CANVAS_X + i * (each + gap), y=row_y,
                                 width=each, height=row_h)
            write(vj, v)
    else:
        main_h = 740

    for vj, v in main:
        v["position"].update(x=CANVAS_X, y=BODY_TOP, width=CANVAS_W, height=main_h)
        write(vj, v)
    for vj, v in footer:
        v["position"].update(x=CANVAS_X, y=892, width=CANVAS_W, height=40)
        write(vj, v)
    for vj, v in titles:
        v["position"].update(**TITLE)
        try:
            props = v["visual"]["objects"]["general"][0]["properties"]
            props["paragraphs"] = title_colours(props["paragraphs"])
        except Exception:
            pass
        write(vj, v)

    write(pdir / "page.json", page)      # size, background, filters - easy to forget

    # clone the rail in
    for src in rail:
        v = copy.deepcopy(src)
        role = v["visual"].get("visualType", "x") + "/" + src["name"]
        v["name"] = seed(f"{pid}/{role}")
        for f in v.get("filterConfig", {}).get("filters", []):
            if "name" in f:
                f["name"] = seed(f"visfilter/{pid}/{src['name']}/{f['name']}")
        d = pdir / "visuals" / v["name"]
        d.mkdir(parents=True, exist_ok=True)
        write(d / "visual.json", v)

    print(f"  {name[:30]:32s} main={len(main)} commentary={len(commentary)} "
          f"footer={len(footer)} removed={removed} yearpin={'dropped' if dropped_year else '-'}")

print(f"\ndone: {len(targets)} pages restyled, {len(DROP_PAGES)} deleted, "
      f"{len(pj['pageOrder'])} pages remain")
