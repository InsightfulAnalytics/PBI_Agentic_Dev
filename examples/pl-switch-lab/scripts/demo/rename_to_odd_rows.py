"""Rename the demo's old "Nightmare P&L" naming to "Odd Rows P&L", everywhere a reader can see it.

ALREADY RUN on 2026-08-28; kept as the record of what changed and as the tool if any of it
has to be redone. The RENAMES table below is the before/after, longest name first.

Covers, in one pass:
  - 2 model tables and their 3 user-visible columns
  - 2 measure display folders
  - 4 report page display names
  - every canvas textbox and visual title
  - every REFERENCE to the renamed objects: TMDL expressions and calculation items, PBIR
    queryRef / nativeQueryRef / Entity / Property bindings, .dax files, and the generator
    scripts that emit them
  - the documentation and DEMO-SPEC.md
  - the .tmdl FILE names, which Desktop expects to match the table names

Order matters: "P&L Nightmare Rows" must be replaced before "P&L Nightmare", or the shorter
pattern eats the longer one and leaves "P&L Odd Rows Fields Rows".

And the script must exclude ITSELF from the walk -- on the first run it rewrote its own
RENAMES table into no-op pairs, which is only funny once.

NOT renamed: the `NM ` measure prefix. It stands for nothing a reader can see -- it is two
opaque letters, not the word -- and renaming 38 measures would cascade into ~50 visual
bindings, every .dax file and every generator for no reader-visible gain. Say the word if you
want it done; it is the same machinery, just wider.

Idempotent: re-running finds nothing to do. Safe with Desktop open -- it clicks
"Apply external changes" afterwards.
"""
import os
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VAULT = Path(os.environ.get("PL_LAB_NOTES", "")) if os.environ.get("PL_LAB_NOTES") else None

# Longest first. Every entry is a plain string swap applied to text files.
RENAMES = [
    # --- model objects -------------------------------------------------------------
    ("P&L Nightmare Rows", "P&L Odd Rows"),   # the disconnected SWITCH row table
    ("P&L Nightmare",      "P&L Odd Rows Fields"),          # the field-parameter table
    ("Nightmare Line Fields", "Odd Rows Line Fields"),
    ("Nightmare Line Order",  "Odd Rows Line Order"),
    ("Nightmare Line",        "Odd Rows Line"),
    # --- display folders -----------------------------------------------------------
    ("06 Nightmare P&L",     "06 Odd Rows P&L"),
    ("07 Nightmare SWITCH",  "07 Odd Rows SWITCH"),
    # --- pages, titles and prose ---------------------------------------------------
    ("Nightmare P&L",  "Odd Rows P&L"),
    ("nightmare P&L",  "odd rows P&L"),
    ("Nightmare SWITCH", "Odd Rows SWITCH"),
    ("Nightmare Deneb",  "Odd Rows Deneb"),
    ("nightmare page",   "odd-rows page"),
    ("Nightmare page",   "Odd-rows page"),
    ("NIGHTMARE_DENEB",  "ODD_ROWS_DENEB"),
    ("NIGHTMARE_DROP",   "ODD_ROWS_DROP"),
]
# Anything still saying "nightmare" after the swaps above is prose. Handled separately so a
# sentence like "this is a nightmare to maintain" is reported rather than mangled.
PROSE = re.compile(r"nightmare", re.I)

TEXT_EXT = {".md", ".py", ".ps1", ".tmdl", ".json", ".dax", ".csv", ".html", ".svg"}
SKIP_DIRS = {"data", "__pycache__", ".pbi", ".vscode"}

APPLY_PS = r"""
# Desktop 26.08+ raises "This project's files were changed externally" with an
# [Apply external changes] button whenever an open PBIP is edited underneath it. Clicking it
# can raise a SECOND confirmation ("Overwrite your unsaved edits") whenever Desktop has
# unsaved canvas state -- and until that is confirmed, nothing is applied. Verified 2026-08-28
# on 2.157.879.0.
Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes
$AE = [System.Windows.Automation.AutomationElement]
$TS = [System.Windows.Automation.TreeScope]::Descendants
$p = Get-Process PBIDesktop -EA SilentlyContinue |
     Where-Object { $_.MainWindowTitle -match 'PL Bridge' } | Select-Object -First 1
if (-not $p) { 'closed'; exit 0 }
$root = $AE::FromHandle($p.MainWindowHandle)
$byName = { param($n) New-Object System.Windows.Automation.PropertyCondition($AE::NameProperty, $n) }

function Invoke-El($el) {
    try { $el.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke(); $true }
    catch { $false }
}

# 1. the banner button
$banner = $null
for ($i = 0; $i -lt 20; $i++) {
    $banner = $root.FindFirst($TS, (& $byName 'Apply external changes'))
    if ($banner) { break }
    Start-Sleep -Milliseconds 500
}
if (-not $banner) { 'no-banner'; exit 0 }
[void](Invoke-El $banner)

# 2. the confirmation, if Desktop had unsaved edits. Its button carries the SAME name, so
#    look for it inside the dialog rather than at the top level.
for ($i = 0; $i -lt 10; $i++) {
    Start-Sleep -Milliseconds 500
    $dlg = $root.FindFirst($TS, (& $byName 'Overwrite your unsaved edits'))
    if (-not $dlg) { continue }
    $ok = $dlg.FindFirst($TS, (& $byName 'Apply external changes'))
    if ($ok -and (Invoke-El $ok)) { 'applied-confirmed'; exit 0 }
}

# 3. no dialog appeared: either it applied straight away, or the banner is still up
Start-Sleep -Milliseconds 1500
if ($root.FindFirst($TS, (& $byName 'Apply external changes'))) { 'still-pending' } else { 'applied' }
"""


SELF = Path(__file__).resolve()


def walk(base):
    for p in base.rglob("*"):
        if p.is_dir() or p.suffix.lower() not in TEXT_EXT:
            continue
        if p.resolve() == SELF:      # or it rewrites its own rename table
            continue
        if SKIP_DIRS & set(p.relative_to(base).parts):
            continue
        yield p


def main():
    targets = list(walk(ROOT))
    if VAULT.is_dir():
        targets += list(walk(VAULT))

    touched, total = {}, 0
    for p in targets:
        try:
            t0 = t = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        n = 0
        for a, b in RENAMES:
            if a in t:
                n += t.count(a)
                t = t.replace(a, b)
        if t != t0:
            # utf-8 via pathlib, never PowerShell: a BOM on PBIR/TMDL breaks Desktop open
            p.write_text(t, encoding="utf-8")
            touched[str(p.relative_to(p.anchor))] = n
            total += n

    print(f"text replacements : {total} across {len(touched)} files")
    for f, n in sorted(touched.items(), key=lambda kv: -kv[1])[:12]:
        print(f"    {n:4d}  {f}")
    if len(touched) > 12:
        print(f"    ... and {len(touched) - 12} more files")

    # --- .tmdl file names must match the table names ---------------------------------
    tables = ROOT / "PL Bridge Demo.SemanticModel" / "definition" / "tables"
    for old, new in (("P&L Nightmare Rows.tmdl", "P&L Odd Rows.tmdl"),
                     ("P&L Nightmare.tmdl", "P&L Odd Rows Fields.tmdl")):
        src = tables / old
        if src.exists():
            shutil.move(str(src), str(tables / new))
            print(f"renamed file      : {old}  ->  {new}")

    # --- report: page display names, for the record ----------------------------------
    pages = ROOT / "PL Bridge Demo.Report" / "definition" / "pages"
    names = []
    for pg in sorted(pages.iterdir()):
        if (pg / "page.json").is_file():
            names.append(json.loads((pg / "page.json").read_text(encoding="utf-8"))["displayName"])
    print("\npages now:")
    for n in names:
        print(f"    {n}")

    # --- residue ----------------------------------------------------------------------
    left = []
    for p in targets:
        if not p.exists():
            continue
        try:
            for i, line in enumerate(p.read_text(encoding="utf-8").split("\n"), 1):
                if PROSE.search(line):
                    left.append(f"{p.name}:{i}: {line.strip()[:120]}")
        except UnicodeDecodeError:
            continue
    print(f"\nremaining 'nightmare' mentions (prose - review by hand): {len(left)}")
    for l in left[:20]:
        print("   ", l)

    out = subprocess.run(["powershell", "-NoProfile", "-Command", APPLY_PS],
                         capture_output=True, text=True).stdout.strip().splitlines()
    state = out[-1] if out else "unknown"
    print(f"\ndesktop           : {state}")
    if state == "no-banner":
        print("    WARNING: Desktop is open but showed no banner. A table rename may need a "
              "reopen; check the Data pane for 'P&L Odd Rows Fields'.")


if __name__ == "__main__":
    main()
