# Rebuilds page 6 "Odd Rows P&L" to candidate D: rows = 'P&L Odd Rows'[Line]
# (a grouped column), columns = the 14-item 'P&L View' calculation group, values = the
# single [NM Row Value] dispatch measure. Replaces the field-parameter design, which
# expanded to 13 separate measure projections and cost 803 ms warm against D's 489 ms.
# Idempotent. Run gen_row_value_measure.py first (it creates [NM Row Value]).
#
# POWER BI DESKTOP MUST BE CLOSED. Desktop re-serialises the whole project on close and
# will silently revert both this file and the new measure (seen 2026-08-24).
import json
import sys
from pathlib import Path

PAGE = Path(__file__).resolve().parents[2] / "PL Bridge Demo.Report" / "definition" / "pages" / "20b3cf7cd78c4158a2ed"
MATRIX = PAGE / "visuals" / "0d10bb9f25e44473ba5a" / "visual.json"
HEADER = PAGE / "visuals" / "0124afebb025434b9d3b" / "visual.json"
WHY    = PAGE / "visuals" / "82a69ea5bddd4f0bbde3" / "visual.json"

import subprocess
if subprocess.run(["powershell", "-NoProfile", "-Command",
                   "if (Get-Process PBIDesktop -EA SilentlyContinue) { exit 1 } else { exit 0 }"],
                  capture_output=True).returncode != 0:
    sys.exit("ABORT: Power BI Desktop is running - it will revert these edits on close.")

SEMI = "'Segoe UI Semibold', wf_segoe-ui_semibold, helvetica, arial, sans-serif"
REG  = "'Segoe UI', wf_segoe-ui_normal, helvetica, arial, sans-serif"

# ---------------------------------------------------------------- matrix
v = json.loads(MATRIX.read_text(encoding="utf-8"))
qs = v["visual"]["query"]["queryState"]
qs["Rows"] = {"projections": [{
    "field": {"Column": {"Expression": {"SourceRef": {"Entity": "P&L Odd Rows"}},
                         "Property": "Line"}},
    "queryRef": "P&L Odd Rows.Line",
    "nativeQueryRef": "Line",
    # pivotTable row levels need active:true on EVERY level, or Desktop renders one
    # column with expanders and silently drops the rest.
    "active": True,
}]}
qs["Values"] = {"projections": [{
    "field": {"Measure": {"Expression": {"SourceRef": {"Entity": "00_Measures"}},
                          "Property": "NM Row Value"}},
    "queryRef": "00_Measures.NM Row Value",
    "nativeQueryRef": "NM Row Value",
}]}
# valuesOnRow existed only to turn the field-parameter measure well into a row axis.
# The rows are a real column now; leaving it transposes the matrix.
v["visual"]["objects"].pop("values", None)
MATRIX.write_text(json.dumps(v, indent=2, ensure_ascii=False), encoding="utf-8")

# ---------------------------------------------------------------- narrative
def set_text(path, paras):
    j = json.loads(path.read_text(encoding="utf-8"))
    j["visual"]["objects"]["general"][0]["properties"]["paragraphs"] = [
        {"textRuns": [{"value": t, "textStyle": {"fontFamily": f, "fontSize": s}}]}
        for t, f, s in paras]
    path.write_text(json.dumps(j, indent=2, ensure_ascii=False), encoding="utf-8")

set_text(HEADER, [
    ("Odd Rows P&L \u2014 13 lines x 14 columns from ONE measure", SEMI, "20pt"),
    ("many odd rows (ratios, per-unit, a count) x many column variants (LY / Budget / "
     "variances, period and YTD) \u2014 182 cells from 1 dispatch measure + 14 calculation items",
     REG, "11pt"),
])
set_text(WHY, [
    ("Why these rows are awkward", SEMI, "14pt"),
    ("Eight of the 13 rows are lines no set of accounts can express \u2014 four ratios, three "
     "per-unit metrics and a distinct count. The 14 columns are scenario/time variants, not a "
     "dimension.", REG, "10pt"),
    ("What costs time is neither SWITCH nor the calculation group. It is how many INDEPENDENT "
     "expressions the query carries: cost tracks (measure columns x calculation items), about "
     "4 ms each on this model. Thirteen row measures x 14 items = 182 scans. One dispatch "
     "measure x 14 items = 14.", REG, "10pt"),
    ("Same 182 cells, same leaf measures, same numbers \u2014 collapsing thirteen row measures "
     "into one SWITCH cuts the query ~40%.", REG, "10pt"),
    ("Measured, 75M rows, all tied out at 182/182:", SEMI, "10pt"),
    ("13 measures via field parameter   1,269 ms cold / 812 ms warm\n"
     "14 SWITCH measures (page 7)       1,125 ms cold / 724 ms warm\n"
     "2nd calculation group as rows     1,030 ms cold / 641 ms warm\n"
     "1 SWITCH measure (this page)        981 ms cold / 597 ms warm", REG, "10pt"),
    ("Note the ordering: removing SWITCH entirely \u2014 a second calculation group on rows \u2014 "
     "is SLOWER than one shallow SWITCH. Cost is instantiation count, not branch count. "
     "Put the rows on a GROUPED column instead and it drops to 26 ms; that needs Deneb.",
     REG, "10pt"),
])
print("page 6 rebuilt: rows=P&L Odd Rows.Line, values=[NM Row Value], 2 textboxes updated")
