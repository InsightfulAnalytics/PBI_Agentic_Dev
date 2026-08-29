# Top Strip pass 4 (2026-08-26): restore navigator text WRAPPING.
#
# There is no wrap property -- navigator text wraps AUTOMATICALLY when the button is
# tall enough (empirically proven: Tim's earlier screenshot showed two-line buttons
# at ~76px tall; adding the title squeezed them and text fell back to ellipsis).
# Fix: single auto row (drop the rowCount/columnCount grid), and grow the visual to
# fill the strip so the title + one tall button row fit.
#
# The category rename moved into the parquet itself (generate_demo_data.py +
# in-place rewrite) -- Products.tmdl stays a plain Source, so Desktop shows no
# "pending query changes" banner; a Products refresh alone picks it up.
#
# Idempotent. POWER BI DESKTOP (PL Bridge) MUST BE CLOSED.
import json
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "PL Bridge Demo.Report" / "definition" / "pages" / "f88c66924ae95c178089"
seed = lambda s: uuid.uuid5(uuid.NAMESPACE_URL, "plbridge/topstrip/" + s).hex[:20]
NAV = seed("visual/80c6d09e066318d68716")

probe = ("if (Get-Process PBIDesktop -EA SilentlyContinue | "
         "Where-Object { $_.MainWindowTitle -match 'PL Bridge' }) { exit 1 } else { exit 0 }")
if subprocess.run(["powershell", "-NoProfile", "-Command", probe],
                  capture_output=True).returncode != 0:
    sys.exit("ABORT: the PL Bridge Desktop instance is running - close it first.")

lit = lambda v: {"expr": {"Literal": {"Value": v}}}
nav_path = PAGE / "visuals" / NAV / "visual.json"
nav = json.loads(nav_path.read_text(encoding="utf-8"))
nav["position"].update(y=14, height=102)
nav["visual"]["objects"]["layout"] = [{"properties": {
    "orientation": lit("1D"),          # horizontal, single row -- tall buttons wrap
    "cellPadding": lit("4L")}}]
nav_path.write_text(json.dumps(nav, indent=2, ensure_ascii=False), encoding="utf-8")
print("navigator: y14 h102, single-row horizontal layout -> tall buttons, text wraps")
