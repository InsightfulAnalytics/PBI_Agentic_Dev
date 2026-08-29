"""Repair the semantic model after the Odd Rows rename was clobbered by a live Desktop.

WHAT WENT WRONG. The rename was applied to disk three times while Power BI Desktop held the
project open. Each time, Desktop wrote its own in-memory model back over the .tmdl files --
so the report and the generator scripts moved to the new names while the model kept snapping
back, and on the last pass Desktop dropped the field-parameter table from the model
altogether and serialized it away. Disk was left with:

  - 'P&L Odd Rows'          the disconnected Line/Sort axis        (correct)
  - 26 references in 00_Measures.tmdl to 'P&L Odd Rows Switch'     (a table that no longer exists)
  - the field-parameter table                                      (GONE)

"Apply external changes" reloads a REPORT reliably. A table RENAME is a different animal: the
reload can leave the model half-applied, and Desktop's next save then overwrites the file. Do
model renames with Desktop CLOSED.

WHAT THIS DOES. Restores the model from the pre-rename backup and re-applies the rename in one
pass, with the mapping the report and the scripts already expect:

    'P&L Nightmare Rows'  ->  'P&L Odd Rows'         the axis the visuals bind (Line, Sort)
    'P&L Nightmare'       ->  'P&L Odd Rows Fields'  the field-parameter table
    'Nightmare Line*'     ->  'Odd Rows Line*'
    '06/07 Nightmare ...' ->  '06/07 Odd Rows ...'

Nothing outside the semantic model is touched -- the report, the scripts and the docs are
already correct.
"""
import os
import pathlib, re, shutil, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEF = ROOT / "PL Bridge Demo.SemanticModel" / "definition"
# A copy of definition/ taken BEFORE the rename. This script is a one-shot recovery tool, so
# the backup is wherever you put it: pass it as the first argument, or set PL_MODEL_BACKUP.
BACKUP = pathlib.Path(
    sys.argv[1] if len(sys.argv) > 1
    else os.environ.get("PL_MODEL_BACKUP", "model_pre_rename"))

# longest first, and the disconnected axis is parked so the shorter pattern cannot eat it
RENAMES = [
    ("P&L Nightmare Rows", "@@AXIS@@"),
    ("P&L Nightmare",      "P&L Odd Rows Fields"),
    ("@@AXIS@@",           "P&L Odd Rows"),
    ("Nightmare Line Fields", "Odd Rows Line Fields"),
    ("Nightmare Line Order",  "Odd Rows Line Order"),
    ("Nightmare Line",        "Odd Rows Line"),
    # the linguistic-schema key in cultures/en-US.tmdl is an IDENTIFIER, not prose: a blanket
    # word swap turns pl_nightmare_rows.line into "pl_odd rows_rows.line" -- a space inside a
    # key, which pbir validate never looks at and Desktop does.
    ("pl_nightmare_rows.line", "pl_odd_rows.line"),
    ("06 Nightmare P&L",      "06 Odd Rows P&L"),
    ("07 Nightmare SWITCH",   "07 Odd Rows SWITCH"),
    ("Nightmare P&L",         "Odd Rows P&L"),
    ("nightmare",             "odd rows"),
    ("Nightmare",             "Odd Rows"),
]

# what the REPORT binds -- the repair has to satisfy this or the visuals error again
REPORT_NEEDS = {("P&L Odd Rows", "Line")}


def desktop_is_open():
    probe = ("if (Get-Process PBIDesktop -EA SilentlyContinue | "
             "Where-Object { $_.MainWindowTitle -match 'PL Bridge' }) { exit 1 } else { exit 0 }")
    return subprocess.run(["powershell", "-NoProfile", "-Command", probe],
                          capture_output=True).returncode != 0


def main():
    if desktop_is_open():
        sys.exit("ABORT: close Power BI Desktop first. It is what broke this -- a live Desktop "
                 "writes its in-memory model back over on-disk TMDL edits, and a table rename "
                 "is exactly the case where the reload does not take.")
    if not BACKUP.is_dir():
        sys.exit(f"ABORT: backup not found at {BACKUP}")

    # 1. restore. Replace the CONTENTS rather than the folder: VS Code's file watcher keeps a
    # handle on `definition\` itself, so rmtree on the directory fails with WinError 32 even
    # with Desktop closed.
    for child in DEF.iterdir():
        shutil.rmtree(child) if child.is_dir() else child.unlink()
    for src in BACKUP.iterdir():
        dst = DEF / src.name
        shutil.copytree(src, dst) if src.is_dir() else shutil.copy2(src, dst)
    print(f"restored model from {BACKUP.name}: "
          f"{len(list((DEF / 'tables').glob('*.tmdl')))} tables")

    # 2. rename, in content
    n = 0
    for p in DEF.rglob("*.tmdl"):
        t0 = t = p.read_text(encoding="utf-8")
        for a, b in RENAMES:
            t = t.replace(a, b)
        if t != t0:
            p.write_text(t, encoding="utf-8")   # pathlib = no BOM; a BOM breaks Desktop open
            n += 1
    print(f"renamed inside {n} model files")

    # 3. rename the files to match the table they declare
    tables = DEF / "tables"
    for old, new in (("P&L Nightmare Rows.tmdl", "P&L Odd Rows.tmdl"),
                     ("P&L Nightmare.tmdl", "P&L Odd Rows Fields.tmdl")):
        if (tables / old).exists():
            shutil.move(str(tables / old), str(tables / new))
            print(f"renamed file  : {old}  ->  {new}")

    # 4. assert the invariants rather than hoping
    declared = {}
    for f in tables.glob("*.tmdl"):
        head = f.read_text(encoding="utf-8").split("\n", 1)[0]
        m = re.match(r"table '?([^'\n]+?)'?$", head.strip())
        if m:
            declared[m.group(1)] = f

    print("\ntables now:")
    for name in sorted(declared):
        if "Odd" in name:
            cols = [l.strip().split(" ", 1)[1].strip("'")
                    for l in declared[name].read_text(encoding="utf-8").split("\n")
                    if l.startswith("\tcolumn ")]
            print(f"   {name:24s} <- {declared[name].name:28s} cols={cols}")

    problems = []
    for tbl, col in REPORT_NEEDS:
        if tbl not in declared:
            problems.append(f"the report binds {tbl}[{col}] but no such table exists")
        elif f"\tcolumn {col}\n" not in declared[tbl].read_text(encoding="utf-8"):
            problems.append(f"the report binds {tbl}[{col}] but that column is not in {tbl}")

    stale = []
    for p in DEF.rglob("*.tmdl"):
        for i, line in enumerate(p.read_text(encoding="utf-8").split("\n"), 1):
            if re.search(r"nightmare|P&L Odd Rows Switch", line, re.I):
                stale.append(f"{p.name}:{i}: {line.strip()[:100]}")
    # every quoted table reference must resolve
    dangling = set()
    for p in DEF.rglob("*.tmdl"):
        for m in re.finditer(r"'(P&L [^']+)'\[", p.read_text(encoding="utf-8")):
            if m.group(1) not in declared:
                dangling.add(f"{p.name}: '{m.group(1)}'")

    print(f"\nstale 'nightmare' / 'Switch' references : {len(stale)}")
    for s in stale[:10]:
        print("   ", s)
    print(f"dangling table references               : {len(dangling)}")
    for d in sorted(dangling):
        print("   ", d)
    print(f"report-binding problems                 : {len(problems)}")
    for x in problems:
        print("   ", x)

    if stale or dangling or problems:
        sys.exit("\nREPAIR INCOMPLETE - see above")
    print("\nrepair OK. Now: pbir validate --fields, then reopen Desktop and Refresh.")


if __name__ == "__main__":
    main()
