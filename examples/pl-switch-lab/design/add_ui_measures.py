# Adds [UI Transparent] to 00_Measures -- a text measure returning an 8-digit hex with a
# zero alpha channel ("#FFFFFF00"). Bound via conditional formatting wherever a format
# card offers no static transparency (Tim's slicer-header background trick, 2026-08-25):
# the static color picker cannot express alpha, but a field-driven color can.
#
# Idempotent (name-based strip). Power BI Desktop (PL Bridge) must be closed.
import re
import subprocess
import sys
import uuid
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "PL Bridge Demo.SemanticModel" / "definition" / "tables" / "00_Measures.tmdl"

probe = ("if (Get-Process PBIDesktop -EA SilentlyContinue | "
         "Where-Object { $_.MainWindowTitle -match 'PL Bridge' }) { exit 1 } else { exit 0 }")
if subprocess.run(["powershell", "-NoProfile", "-Command", probe],
                  capture_output=True).returncode != 0:
    sys.exit("ABORT: the PL Bridge Desktop instance is running - close it first.")

NAME = "UI Transparent"
block = [
    "\t/// Fully transparent fill for conditional-formatting slots whose static color",
    "\t/// picker has no alpha (slicer header backgrounds, etc). 8-digit hex, alpha 00.",
    f"\tmeasure '{NAME}' =",
    "",
    '\t\t\t"#FFFFFF00"',
    "\t\tdisplayFolder: 08 UI",
    f"\t\tlineageTag: {uuid.uuid5(uuid.NAMESPACE_URL, 'plbridgedemo/' + NAME)}",
    "",
]

lines = OUT.read_text(encoding="utf-8").replace("\r\n", "\n").split("\n")
decl = [i for i, l in enumerate(lines) if l.startswith("\tmeasure '")]
part = next(i for i, l in enumerate(lines) if l.startswith("\tpartition 00_Measures-"))

def block_start(i):
    while i > 0 and lines[i - 1].startswith("\t///"):
        i -= 1
    return i

blocks = []
for k, i in enumerate(decl):
    s = block_start(i)
    e = block_start(decl[k + 1]) if k + 1 < len(decl) else part
    blocks.append((re.match(r"\tmeasure '([^']+)'", lines[i]).group(1), lines[s:e]))

before = len(blocks)
blocks = [b for b in blocks if b[0] != NAME]
print(f"stripped {before - len(blocks)} existing '{NAME}'")

head = lines[: block_start(decl[0])]
out = head + block + [l for _, b in blocks for l in b] + lines[part:]
OUT.write_text("\n".join(out), encoding="utf-8", newline="\r\n")
total = sum(1 for l in out if l.startswith("\tmeasure '"))
assert total == len(blocks) + 1
print(f"OK: 00_Measures now defines {total} measures")
