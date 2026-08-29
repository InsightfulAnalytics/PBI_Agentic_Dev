"""Model objects for the Monthly P&L scenario -- the lab reproduction of the field case in
docs/performance/05-case-unrenderable-matrix.md.

Builds, idempotently:

  1. 'Period View'  -- a 15-item calculation group for the COLUMN axis:
                       Jan..Dec, YTD, YTG, Full Year. Each item is a filter rewrite over
                       DimDate, which is what stops the engine collapsing the twelve month
                       items into one GROUP BY scan.
  2. 28 measures    -- 21 real + 7 blank section titles, for the ROW axis (values on rows).
                       21 of them carry a self-referencing formatStringDefinition, so every
                       rendered cell evaluates its measure a second time.

15 items x 28 measures = 420 dispatched cell evaluations, 21 x 15 = 315 of them paying the
per-cell format-string tax. Same arithmetic as the field matrix, on a 74.9M-row fact.

Only 10 of the 28 are irreducible -- the Act/LY pair for Income, COGS, GP, Opex and Net
Profit. The other 11 are ratios and variances of those, and the 15 columns are twelve month
buckets plus three aggregates of them. That is what the Deneb page queries instead: 12 rows
x 10 measures, everything else derived client-side.

Strips its own objects BY NAME before reinserting (Desktop reorders measures on save, so a
line-range strip captured from an earlier layout silently duplicates the file). Run twice as
an idempotency test: the measure count must not move.

POWER BI DESKTOP MUST BE CLOSED -- it silently reverts on-disk edits when it closes.
"""
import re
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEF = ROOT / "PL Bridge Demo.SemanticModel" / "definition"
MEASURES = DEF / "tables" / "00_Measures.tmdl"
PERIOD_VIEW = DEF / "tables" / "Period View.tmdl"
MODEL = DEF / "model.tmdl"

PREFIX = "MP "          # every object this script owns starts with it
FOLDER = "09 Monthly P&L"
T = "\t"

def require_desktop_closed():
    """Desktop silently reverts on-disk edits when it closes, so refuse to write while it
    holds the project. Scoped by window title: other Desktop instances are fine."""
    probe = ("if (Get-Process PBIDesktop -EA SilentlyContinue | "
             "Where-Object { $_.MainWindowTitle -match 'PL Bridge' }) { exit 1 } else { exit 0 }")
    if subprocess.run(["powershell", "-NoProfile", "-Command", probe],
                      capture_output=True).returncode != 0:
        sys.exit("ABORT: the PL Bridge Desktop instance is running - close it first.")


def tag(kind, name):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"plbridge/monthly/{kind}/{name}"))


# ---------------------------------------------------------------- 1. calculation group
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# The current period, found the way the field matrix's calc items find it: a REMOVEFILTERS
# probe for the month whose offset is 0. This is dispatch DAX -- it is one of the things the
# Deneb rebuild has to reproduce without asking the engine for anything extra.
CUR_P = f"""{T*3}VAR __CurP =
{T*4}CALCULATE (
{T*5}MAX ( 'DimDate'[MonthOfYear] ),
{T*5}REMOVEFILTERS ( 'DimDate' ),
{T*5}'DimDate'[MonthOffset] = 0
{T*4})
{T*3}RETURN"""


def month_item(name, n):
    return (f"{T*2}calculationItem {name} =\n{T*3}\n"
            f"{T*3}CALCULATE (\n"
            f"{T*4}SELECTEDMEASURE ( ),\n"
            f"{T*4}ALLEXCEPT ( 'DimDate', 'DimDate'[Year] ),\n"
            f"{T*4}'DimDate'[MonthOfYear] = {n}\n"
            f"{T*3})\n")


def cumulative_item(name, op):
    return (f"{T*2}calculationItem {name} =\n{T*3}\n"
            f"{CUR_P}\n"
            f"{T*4}CALCULATE (\n"
            f"{T*5}SELECTEDMEASURE ( ),\n"
            f"{T*5}ALLEXCEPT ( 'DimDate', 'DimDate'[Year] ),\n"
            f"{T*5}'DimDate'[MonthOfYear] {op} __CurP\n"
            f"{T*4})\n")


def build_period_view():
    # Declaration order IS the ordinal -- Desktop strips an explicit `ordinal:` on save.
    items = [month_item(m, i + 1) for i, m in enumerate(MONTHS)]
    items.append(cumulative_item("YTD", "<="))
    items.append(cumulative_item("YTG", ">"))
    items.append(f"{T*2}calculationItem 'Full Year' =\n{T*3}\n"
                 f"{T*3}CALCULATE ( SELECTEDMEASURE ( ), ALLEXCEPT ( 'DimDate', 'DimDate'[Year] ) )\n")

    return (
        f"table 'Period View'\n"
        f"{T}lineageTag: {tag('table', 'Period View')}\n"
        f"\n"
        f"{T}calculationGroup\n"
        f"{T*2}precedence: 20\n"
        f"\n"
        + "\n".join(items) +
        f"\n"
        f"{T}column 'Period View'\n"
        f"{T*2}dataType: string\n"
        f"{T*2}lineageTag: {tag('column', 'Period View')}\n"
        f"{T*2}summarizeBy: none\n"
        f"{T*2}sourceColumn: Name\n"
        f"{T*2}sortByColumn: Ordinal\n"
        f"\n"
        f"{T*2}annotation SummarizationSetBy = Automatic\n"
        f"\n"
        f"{T}column Ordinal\n"
        f"{T*2}dataType: int64\n"
        f"{T*2}isHidden\n"
        f"{T*2}formatString: 0\n"
        f"{T*2}lineageTag: {tag('column', 'Ordinal')}\n"
        f"{T*2}summarizeBy: none\n"
        f"{T*2}sourceColumn: Ordinal\n"
        f"\n"
        f"{T*2}annotation SummarizationSetBy = Automatic\n"
    )


# ---------------------------------------------------------------- 2. the 28 row measures
# (name, dax, fmt, doc). fmt: "money" | "pct" | None (section title).
#
# The five statement lines come off the P&L Lines bridge, so each base measure is one
# filtered scan -- the point being that the slow page is slow because of the dispatch, not
# because the measures underneath it are badly written. Scenario is baked in and time is
# not: the calculation group owns the period, exactly as the field matrix does.
BASE = [
    ("Income", "NM Total Income",             "Total Income"),
    ("COGS",   "NM Total Cost of Sales",      "Total Cost of Sales"),
    ("GP",     "NM Gross Profit",             "Gross Profit"),
    ("Opex",   "NM Total Operating Expenses", "Total Operating Expenses"),
    ("NP",     "NM Net Profit",               "Net Profit"),
]

SPEC = []
for key, src, label in BASE:
    SPEC.append((f"{PREFIX}{key} Act",
                 f'CALCULATE ( [{src}], \'Financials\'[Scenario] = "Actual" )',
                 "money", f"{label}, actual. Scenario-specific, period-agnostic: the calculation group owns the period."))
    SPEC.append((f"{PREFIX}{key} LY",
                 f"CALCULATE ( [{PREFIX}{key} Act], DATEADD ( 'DimDate'[Date], -1, YEAR ) )",
                 "money", f"{label}, same period last year."))

DERIVED = [
    ("Income Var %", "DIVIDE ( [MP Income Act] - [MP Income LY], [MP Income LY] )",
     "Income growth on last year. Blank Act over a real LY is -100%, matching DAX's blank-as-zero subtraction."),
    ("COGS Var %", "DIVIDE ( [MP COGS Act] - [MP COGS LY], [MP COGS LY] )",
     "Cost of sales movement on last year. Both sides are negative, so the sign reads as cost growth."),
    ("GP Var %", "DIVIDE ( [MP GP Act] - [MP GP LY], [MP GP LY] )",
     "Gross profit growth on last year."),
    ("GM % Act", "DIVIDE ( [MP GP Act], [MP Income Act] )", "Gross margin, actual."),
    ("GM % LY", "DIVIDE ( [MP GP LY], [MP Income LY] )", "Gross margin, last year."),
    ("GM % Var bps", "[MP GM % Act] - [MP GM % LY]",
     "Gross margin movement in points. A difference, not a ratio -- blank only if both sides are blank."),
    ("Opex Var %", "DIVIDE ( [MP Opex Act] - [MP Opex LY], [MP Opex LY] )",
     "Operating expense movement on last year."),
    ("Opex % Act", "DIVIDE ( -1 * [MP Opex Act], [MP Income Act] )",
     "Operating expenses as a positive share of income. -1 * BLANK() is BLANK, so the blank survives the sign flip."),
    ("Opex % LY", "DIVIDE ( -1 * [MP Opex LY], [MP Income LY] )",
     "Operating expense ratio, last year."),
    ("Opex % Var bps", "[MP Opex % Act] - [MP Opex % LY]",
     "Operating expense ratio movement in points."),
    ("NP Var %", "DIVIDE ( [MP NP Act] - [MP NP LY], [MP NP LY] )",
     "Net profit growth on last year."),
]
for name, dax, doc in DERIVED:
    SPEC.append((f"{PREFIX}{name}", dax, "pct", doc))

SECTIONS = ["Income", "Cost of Sales", "Gross Profit", "Gross Margin",
            "Operating Expenses", "Cost Ratio", "Net Profit"]
for s in SECTIONS:
    SPEC.append((f"{PREFIX}Sec {s}", "BLANK ( )", None,
                 f"Section band: renders as the '{s}' caption row and returns nothing. "
                 f"Still a measure the dispatch plan has to be able to produce, in all 15 columns."))

assert len([s for s in SPEC if s[2] is not None]) == 21, "expected 21 real rows"
assert len(SPEC) == 28, "expected 28 measures"


def measure_block(name, dax, fmt, doc):
    """`///` doc lines carry the SAME indent as the measure, and no blank line may follow
    them. formatStringDefinition is a CHILD OBJECT: after the scalar properties, separated
    by a blank line, expression inline. A measure may not carry both formatString and
    formatStringDefinition -- Desktop refuses the whole project."""
    # The expression body sits ONE INDENT DEEPER than the properties (3 tabs vs 2). At the
    # same level the parser reads `displayFolder:` and everything after it as more DAX: the
    # file still parses, the format string vanishes, and Desktop chokes on the expression.
    out = [f"{T}/// {doc}",
           f"{T}measure '{name}' =",
           f"{T*3}",
           f"{T*3}{dax}",
           f"{T*2}displayFolder: {FOLDER}",
           f"{T*2}lineageTag: {tag('measure', name)}"]
    if fmt == "money":
        # Self-referencing: choosing between $x.xM / $x.xK / plain re-evaluates the measure
        # once per rendered cell, through the calculation item. This is cost (b).
        out += ["", f"{T*2}formatStringDefinition = Fmt.Money ( [{name}] )"]
    elif fmt == "pct":
        out += ["", f'{T*2}formatStringDefinition = IF ( ABS ( [{name}] ) >= 1, "0%;(0%)", "0.0%;(0.0%)" )']
    return "\n".join(out) + "\n"


def patch_measures():
    """Parse 00_Measures.tmdl into named blocks, drop the ones this script owns, append
    fresh ones. Never strip by line position."""
    text = MEASURES.read_text(encoding="utf-8")
    lines = text.split("\n")

    # A measure block starts at its `///` doc line if it has one, else at `\tmeasure`.
    starts = [i for i, l in enumerate(lines) if re.match(r"^\tmeasure ", l)]
    if not starts:
        sys.exit("ABORT: no measures found - wrong file?")
    tail_start = next(i for i, l in enumerate(lines)
                      if re.match(r"^\tpartition ", l))

    def block_start(i):
        j = i
        while j > 0 and lines[j - 1].startswith(f"{T}///"):
            j -= 1
        return j

    bounds = []
    for n, i in enumerate(starts):
        end = block_start(starts[n + 1]) if n + 1 < len(starts) else tail_start
        name = re.match(r"^\tmeasure '?([^'=]+?)'? =", lines[i]).group(1).strip()
        bounds.append((name, block_start(i), end))

    before = len(bounds)
    kept = [(n, s, e) for n, s, e in bounds if not n.startswith(PREFIX)]
    dropped = before - len(kept)

    head = lines[:bounds[0][1]]
    body = []
    for _, s, e in kept:
        body += lines[s:e]
    for name, dax, fmt, doc in SPEC:
        body += measure_block(name, dax, fmt, doc).split("\n")[:-1]
        # A trailing blank line is what CLOSES the formatStringDefinition child object.
        # Without it the parser silently drops the whole thing -- the file still parses, the
        # measure still works, and every cell quietly falls back to the default format.
        body.append("")
    tail = lines[tail_start:]

    out = "\n".join(head + body + tail)
    MEASURES.write_text(out, encoding="utf-8")
    after = len(re.findall(r"^\tmeasure ", out, re.M))
    print(f"measures      : {before} -> {after}  (dropped {dropped} {PREFIX.strip()}*, added {len(SPEC)})")
    assert after == len(kept) + len(SPEC), "measure count does not reconcile"


def patch_model_ref():
    text = MODEL.read_text(encoding="utf-8")
    if "ref table 'Period View'" in text:
        print("model.tmdl    : ref already present")
        return
    text = text.replace("ref table 'P&L View'\n",
                        "ref table 'P&L View'\nref table 'Period View'\n")
    MODEL.write_text(text, encoding="utf-8")
    print("model.tmdl    : added ref table 'Period View'")


if __name__ == "__main__":
    require_desktop_closed()
    PERIOD_VIEW.write_text(build_period_view(), encoding="utf-8")
    print(f"Period View   : 15 calculation items written")
    patch_measures()
    patch_model_ref()
    print(f"\ndispatch load : 15 items x 28 measures = {15*28} cell evaluations, "
          f"{21*15} of them paying the format-string tax")
