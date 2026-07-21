#!/usr/bin/env python
"""Add the extended DimDate date table (and the 'Dates Selected' measure) to a PBIP semantic model.

Injects, into <model>.SemanticModel/definition/:
  * expressions.tmdl  -- the FunctionDateTable M function (created if absent)
  * tables/DimDate.tmdl -- the date dimension, with its partition arguments patched
  * tables/<measure table>.tmdl -- the 'Dates Selected' measure (table created if absent)
  * model.tmdl        -- 'ref table' entries and the PBI_QueryOrder annotation

Every lineageTag in the injected TMDL is regenerated, so the assets can be added to
any number of models without collisions.

Attribution for the bundled code is in ../SKILL.md and the repo's ATTRIBUTIONS.md.

Usage:
    python add_date_table.py --model "C:/proj/My Model.SemanticModel"
    python add_date_table.py --model . --start 2015-01-01 --dynamic-end --fy-start-month 7
    python add_date_table.py --model . --dry-run
"""

from __future__ import annotations

import argparse
import datetime as dt
import io
import re
import sys
import uuid
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / "assets"

DATE_TABLE_ASSET = ASSETS / "DimDate.tmdl"
FUNCTION_ASSET = ASSETS / "FunctionDateTable.tmdl"
MEASURE_ASSET = ASSETS / "DatesSelected.measure.tmdl"
MEASURE_TABLE_ASSET = ASSETS / "MeasureTable.tmdl"
HELPERS_ASSET = ASSETS / "helper-expressions.tmdl"

# [ \t] rather than \s -- \s would swallow the following blank line and TMDL is
# indentation- and blank-line-sensitive.
LINEAGE_RE = re.compile(r"(?m)^([ \t]*lineageTag:[ \t]*)[0-9a-fA-F-]{36}[ \t]*$")
PARTITION_CALL_RE = re.compile(
    r"FunctionDateTable\(\s*#date\([^)]*\)\s*,\s*(?:#date\([^)]*\)|Year_Variable[^,]*|[^,]+)\s*,"
    r"\s*[^,]+,\s*[^,]+,\s*[^)]+\)"
)


# --------------------------------------------------------------------------- io


def read(path: Path) -> str:
    return io.open(path, encoding="utf-8-sig").read()


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # TMDL files Power BI Desktop writes are UTF-8 with CRLF; match that.
    io.open(path, "w", encoding="utf-8", newline="\r\n").write(text.replace("\r\n", "\n"))


def fresh_lineage_tags(text: str) -> str:
    return LINEAGE_RE.sub(lambda m: f"{m.group(1)}{uuid.uuid4()}", text)


# ------------------------------------------------------------------ model paths


def resolve_definition(model_arg: str) -> Path:
    """Accept a .SemanticModel folder, its definition folder, a .pbip, or a project root."""
    p = Path(model_arg).resolve()

    if p.is_file() and p.suffix.lower() == ".pbip":
        p = p.parent
    if p.is_file():
        p = p.parent

    if p.name == "definition" and (p / "model.tmdl").exists():
        return p
    if (p / "definition" / "model.tmdl").exists():
        return p / "definition"

    candidates = sorted(p.glob("*.SemanticModel/definition/model.tmdl"))
    if len(candidates) == 1:
        return candidates[0].parent
    if len(candidates) > 1:
        names = ", ".join(c.parent.parent.name for c in candidates)
        raise SystemExit(f"Several semantic models under {p}: {names}. Pass --model explicitly.")

    raise SystemExit(f"No semantic model definition found at or under {p}")


# --------------------------------------------------------------- the date table


def build_date_table(args) -> str:
    text = read(DATE_TABLE_ASSET)

    end = "Year_Variable, 12, 31" if args.dynamic_end else _date_args(args.end)
    call = (
        f"FunctionDateTable(#date({_date_args(args.start)}), #date({end}), "
        f"{args.fy_start_month}, {args.holidays}, {args.week_start})"
    )
    text, n = PARTITION_CALL_RE.subn(call, text)
    if n != 1:
        raise SystemExit(
            f"Expected exactly one FunctionDateTable(...) call in {DATE_TABLE_ASSET.name}, found {n}"
        )

    if args.table_name != "DimDate":
        text = re.sub(r"(?m)^table DimDate$", f"table {quote(args.table_name)}", text)
        text = re.sub(r"(?m)^(\tpartition )DimDate( = m)$", rf"\1{quote(args.table_name)}\2", text)

    if args.mark_as_date_table:
        text = mark_as_date_table(text)

    return fresh_lineage_tags(text)


def _date_args(iso: str) -> str:
    d = dt.date.fromisoformat(iso)
    return f"{d.year}, {d.month}, {d.day}"


def quote(name: str) -> str:
    """TMDL object names need single quotes when they are not simple identifiers."""
    return name if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) else f"'{name}'"


def mark_as_date_table(text: str) -> str:
    """Set dataCategory: Time on the table and isKey on the Date column."""
    lines = text.split("\n")
    out: list[str] = []
    for i, line in enumerate(lines):
        out.append(line)
        if re.match(r"^table\s", line):
            out.append("\tdataCategory: Time")
        elif line == "\tcolumn Date":
            # isKey goes with the other column properties, after dataType.
            pass
    text = "\n".join(out)
    text = text.replace(
        "\tcolumn Date\n\t\tdataType: dateTime\n",
        "\tcolumn Date\n\t\tdataType: dateTime\n\t\tisKey\n",
        1,
    )
    return text


# ------------------------------------------------------------------ expressions


def inject_expressions(definition: Path, args, changes: list[str]) -> None:
    path = definition / "expressions.tmdl"
    existing = read(path) if path.exists() else ""

    blocks: list[str] = []
    if re.search(r"(?m)^expression FunctionDateTable\b", existing):
        changes.append("expressions.tmdl: FunctionDateTable already present, left alone")
    else:
        blocks.append(fresh_lineage_tags(read(FUNCTION_ASSET)))
        changes.append("expressions.tmdl: added FunctionDateTable")

    want_helpers = args.include_helpers or args.dynamic_end
    if want_helpers:
        helpers = read(HELPERS_ASSET)
        for name in ("Year_Variable", "TodayDate"):
            if re.search(rf"(?m)^expression {name}\b", existing):
                changes.append(f"expressions.tmdl: {name} already present, left alone")
                helpers = drop_expression(helpers, name)
        if helpers.strip():
            blocks.append(fresh_lineage_tags(helpers))
            changes.append("expressions.tmdl: added helper expressions")

    if not blocks:
        return

    parts = ([existing.rstrip("\n"), ""] if existing.strip() else []) + [b.rstrip("\n") for b in blocks]
    write(path, "\n\n".join(p for p in parts if p is not None) + "\n")


def drop_expression(text: str, name: str) -> str:
    """Remove a single `expression <name> ...` block from a TMDL expressions file."""
    lines = text.split("\n")
    start = next((i for i, l in enumerate(lines) if re.match(rf"^expression {name}\b", l)), None)
    if start is None:
        return text
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if re.match(r"^expression\s", lines[i]):
            end = i
            break
    return "\n".join(lines[:start] + lines[end:])


# --------------------------------------------------------------- measure table


def inject_measure(definition: Path, args, changes: list[str]) -> None:
    tables = definition / "tables"
    path = tables / f"{args.measure_table}.tmdl"
    measure = fresh_lineage_tags(read(MEASURE_ASSET)).rstrip("\n")

    if args.table_name != "DimDate":
        measure = measure.replace("'DimDate'", f"'{args.table_name}'")
        measure = re.sub(r"\bDimDate\b(?!')", args.table_name, measure)

    if path.exists():
        text = read(path)
        if re.search(r"(?m)^\tmeasure 'Dates Selected'", text):
            changes.append(f"{path.name}: 'Dates Selected' already present, left alone")
            return
        lines = text.split("\n")
        # Insert after the table header's lineageTag line.
        anchor = next(
            (i for i, l in enumerate(lines) if re.match(r"^\tlineageTag:", l)),
            0,
        )
        lines = lines[: anchor + 1] + ["", measure] + lines[anchor + 1 :]
        write(path, "\n".join(lines))
        changes.append(f"{path.name}: added 'Dates Selected'")
        return

    shell = fresh_lineage_tags(read(MEASURE_TABLE_ASSET))
    if args.measure_table != "Measure Table":
        shell = shell.replace("'Measure Table'", quote(args.measure_table))
    lines = shell.split("\n")
    anchor = next(i for i, l in enumerate(lines) if re.match(r"^\tlineageTag:", l))
    lines = lines[: anchor + 1] + ["", measure] + lines[anchor + 1 :]
    write(path, "\n".join(lines))
    changes.append(f"{path.name}: created, with 'Dates Selected'")


# ------------------------------------------------------------------- model.tmdl


def patch_model(definition: Path, args, changes: list[str], query_order: list[str]) -> None:
    path = definition / "model.tmdl"
    lines = read(path).rstrip("\n").split("\n")

    refs = [args.table_name]
    if not args.no_measure:
        refs.append(args.measure_table)

    missing = [n for n in refs if not any(l.strip() == f"ref table {quote(n)}" for l in lines)]
    if missing:
        block = [f"ref table {quote(n)}" for n in missing]
        last_ref = max((i for i, l in enumerate(lines) if l.startswith("ref table ")), default=None)
        if last_ref is not None:
            lines[last_ref + 1 : last_ref + 1] = block
        else:
            # No ref table lines yet: put the block before ref cultureInfo, or at the end.
            at = next((i for i, l in enumerate(lines) if l.startswith("ref ")), len(lines))
            lines[at:at] = block + [""]
            if at > 0 and lines[at - 1].strip():
                lines.insert(at, "")
        changes.append("model.tmdl: added ref table " + ", ".join(missing))

    text = "\n".join(lines) + "\n"
    text = patch_query_order(text, query_order, changes)
    write(path, text)


def patch_query_order(text: str, tables: list[str], changes: list[str]) -> str:
    m = re.search(r'(?m)^annotation PBI_QueryOrder = \[(.*)\]$', text)
    if not m:
        return text
    current = re.findall(r'"([^"]*)"', m.group(1))
    wanted = [t for t in tables if t not in current]
    if not wanted:
        return text
    new = wanted + current
    changes.append("model.tmdl: updated PBI_QueryOrder")
    body = ",".join(f'"{n}"' for n in new)
    return text[: m.start()] + f"annotation PBI_QueryOrder = [{body}]" + text[m.end() :]


# ------------------------------------------------------------------------- main


def main(argv=None) -> int:
    default_end = f"{dt.date.today().year + 2}-12-31"

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True, help="Path to the .SemanticModel folder, its definition folder, a .pbip, or the project root")
    ap.add_argument("--table-name", default="DimDate", help="Name for the date table (default: DimDate)")
    ap.add_argument("--measure-table", default="Measure Table", help="Table the 'Dates Selected' measure lands in (created if absent)")
    ap.add_argument("--start", default="2021-01-01", help="First date, ISO yyyy-mm-dd (default: 2021-01-01)")
    ap.add_argument("--end", default=default_end, help=f"Last date, ISO yyyy-mm-dd (default: {default_end})")
    ap.add_argument("--dynamic-end", action="store_true", help="End at 31 Dec of Year_Variable (current year + 2) instead of a fixed --end; adds the helper expressions")
    ap.add_argument("--fy-start-month", type=int, default=7, choices=range(1, 13), metavar="1-12", help="Fiscal year start month (default: 7)")
    ap.add_argument("--week-start", type=int, default=1, choices=(0, 1), help="DayOfWeek base: 0 = Sunday-as-0, 1 = Monday-as-1 (default: 1)")
    ap.add_argument("--holidays", default="null", help="M list expression for holidays, or null (default: null)")
    ap.add_argument("--include-helpers", action="store_true", help="Also add the Year_Variable and TodayDate expressions")
    ap.add_argument("--mark-as-date-table", action="store_true", help="Set dataCategory: Time and mark [Date] as the key column")
    ap.add_argument("--no-measure", action="store_true", help="Add the date table only, skip the 'Dates Selected' measure")
    ap.add_argument("--dry-run", action="store_true", help="Report what would change without writing")
    args = ap.parse_args(argv)

    for asset in (DATE_TABLE_ASSET, FUNCTION_ASSET, MEASURE_ASSET, MEASURE_TABLE_ASSET, HELPERS_ASSET):
        if not asset.exists():
            raise SystemExit(f"Missing asset: {asset}")

    definition = resolve_definition(args.model)
    table_path = definition / "tables" / f"{args.table_name}.tmdl"
    measure_path = definition / "tables" / f"{args.measure_table}.tmdl"
    measure_table_is_new = not measure_path.exists()

    if args.dry_run:
        print(f"Model definition : {definition}")
        print(f"Would write      : {table_path}")
        print(f"Would update     : {definition / 'expressions.tmdl'}")
        if not args.no_measure:
            verb = "create" if measure_table_is_new else "update"
            print(f"Would {verb}     : {measure_path}")
        print(f"Would update     : {definition / 'model.tmdl'}")
        return 0

    changes: list[str] = []

    if table_path.exists():
        changes.append(f"{table_path.name}: already exists, left alone")
    else:
        write(table_path, build_date_table(args))
        changes.append(f"{table_path.name}: created")

    inject_expressions(definition, args, changes)

    if not args.no_measure:
        inject_measure(definition, args, changes)

    query_order = [args.table_name]
    if not args.no_measure:
        query_order.append(args.measure_table)
    if args.include_helpers or args.dynamic_end:
        query_order += ["Year_Variable", "TodayDate"]
    query_order.append("FunctionDateTable")

    patch_model(definition, args, changes, query_order)

    print(f"Model definition: {definition}")
    for c in changes:
        print(f"  - {c}")
    print(
        f"\nNext: add relationships from your fact tables to {args.table_name}[Date], then open"
        f"\nthe project in Power BI Desktop and refresh {args.table_name}."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
