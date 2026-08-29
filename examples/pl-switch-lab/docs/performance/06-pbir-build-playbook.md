# PBIR build playbook: doing this safely on a real report

The operational half of this doc set. [01-diagnosing-slow-matrices.md](01-diagnosing-slow-matrices.md)
tells you what to change; [02-bridge-method.md](02-bridge-method.md),
[03-format-string-and-cf-tax.md](03-format-string-and-cf-tax.md) and
[04-deneb-grid-template.md](04-deneb-grid-template.md) tell you what to build. This file is the set of
rules that keep the rebuild from destroying the report you are rebuilding. Every rule below broke
something at least once, and most of them broke it *silently*: no error, no dialog, no failed
validation, just a report that is subtly wrong the next time someone opens it.

Scale of the thing you are editing, from `pbir validate "<Report>.Report"` on 2026-08-27:
**108 pages, 1570 visuals**. You are not going to eyeball a diff of that. Everything here assumes
generated, re-runnable edits with machine checks around them.

## Desktop must be closed. This is rule zero

Power BI Desktop holds its own in-memory copy of the report and the model, and it re-serialises that
copy to disk when it saves or closes. Anything you wrote to disk while Desktop was running is
overwritten by what Desktop remembers. There is no merge, no prompt, and no error.

Confirmed the hard way on 2026-08-24 (PL Bridge Demo): edits made while Desktop was open were
silently reverted on close. A new measure in `00_Measures.tmdl` vanished: the file went **238 → 237**
measures: a rebuilt `visual.json` reverted to its old query state, and two textboxes reverted. The
only thing that survived was a brand-new `.tmdl` file Desktop had never loaded. Nothing Desktop had
in memory did.

The failure does not surface at close. It surfaces later, when a visual queries a measure that no
longer exists and Desktop reports *"The value for 'X' cannot be determined"*. By then you have
usually blamed your DAX.

The guard goes at the top of every generator, before it touches anything. Scope it by window title
so it does not trip on an unrelated Desktop instance: Tim usually has two or three projects open:

```powershell
if (Get-Process PBIDesktop -EA SilentlyContinue |
    Where-Object { $_.MainWindowTitle -like '*<Report>*' }) { exit 1 } else { exit 0 }
```

The wildcard match is deliberate: with unsaved changes the title is
`<Report>* - Power BI Desktop`, and an equality test would miss exactly the dangerous case.
Use `-like`, not `-match`. `-match` is the regular-expression operator, and with the pattern above
it does not even run: a leading `*` throws *"Quantifier {x,y} following nothing"*. That failure is
at least loud. The quiet one is the fix you would reach for next: drop the asterisks, and a project
name containing `.` or `+` is a regex that matches titles other than its own, on a guard whose whole
job is to be trustworthy.

The Python wrapper that every build script calls first:

```python
import subprocess
import sys

PROJECT = "<Report>"                        # the project name, as it appears in the title bar
_ESC = PROJECT.replace("'", "''")          # single quotes double up inside a PS single-quoted string
GUARD = ("if (Get-Process PBIDesktop -EA SilentlyContinue | "
         f"Where-Object {{ $_.MainWindowTitle -like '*{_ESC}*' }}) "
         "{ exit 1 } else { exit 0 }")


def require_desktop_closed():
    if subprocess.run(["powershell", "-NoProfile", "-Command", GUARD],
                      capture_output=True).returncode != 0:
        sys.exit(f"ABORT: Power BI Desktop has {PROJECT} open - it will revert these edits on close.")
```

Call it unconditionally, not behind a `--force`. `pbir desktop list` is the quick human check: it
prints the PID, the open file, and whether there are unsaved changes.

If you *did* edit with Desktop open, do not trust the file system. Re-read every file you wrote after
Desktop closes and confirm your change is still there.

## Never force-kill Desktop after a save

The title bar drops its `*` as soon as the report *definition* is written. Desktop is not finished:
it keeps streaming the data image to `.pbi\cache.abf` for tens of seconds afterwards. On a 75M-row
model a 257 MB cache did not even appear on disk until roughly 30 seconds after Ctrl+S.

Kill it in that window and you truncate `cache.abf`. The next open dies with `DecoderCorruptedData` /
*"The Decoder Fetch Uncompressed Data failed with error code 9"*, which reads exactly like model
corruption and is not.

Recovery is cheap once you know: delete or rename `.pbi\cache.abf`, reopen (the TMDL is
untouched), and do a full refresh.

Prevention is a poll on the cache file plus a clean title:

```powershell
$abf  = "<client-repo>\<Report>.SemanticModel\.pbi\cache.abf"
$last = -1; $stable = 0
while ($stable -lt 3) {
  Start-Sleep -Seconds 5
  $f = Get-Item $abf -EA SilentlyContinue
  # absent is NOT stable - not existing yet is the window this poll exists to survive
  if (-not $f) { $stable = 0; $last = -1; continue }
  if ($f.Length -eq $last) { $stable++ } else { $stable = 0; $last = $f.Length }
}
"cache.abf stable at $last bytes - safe to close"
```

Test the item, not its `.Length`. Under Windows PowerShell 5.1
`(Get-Item $missing -EA SilentlyContinue).Length` evaluates to **`0`**, not `$null`, so a poll
written that way reads a steady 0 every iteration, counts three in a row, and prints "safe to close"
about twenty seconds in: inside the exact window where the file has not been created yet, which is
the one moment the whole poll exists to catch.

`CloseMainWindow()` is not a workaround. On 2026-08-24 it was accepted three times across roughly ten
minutes, did nothing, and left the process `Responding = True` with its title unchanged. Do not
escalate from there to `Stop-Process -Force`; that is the corruption path. Confirm `cache.abf` is
stable, then ask the user to close Desktop.

## Idempotent generators

Assume every build script will be run five times: once to see what it does, three times while you
fix the layout, once more after you rebase. If a re-run appends instead of replacing, run four is a
report with four copies of your page and a model with four copies of your measures.

Three properties make a generator safe.

**Seed every id from `uuid5` over a stable string.** Never `uuid4`, never a counter. Same input,
same id, so a re-run overwrites the same objects rather than minting new ones:

```python
import uuid

def gid(kind, key):
    """Stable 20-hex PBIR id. Same (kind, key) always yields the same id."""
    return uuid.uuid5(uuid.NAMESPACE_URL, f"field/dispatch/{kind}/{key}").hex[:20]

def tag(name):
    """Stable TMDL lineageTag (full uuid form)."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "field/dispatch/" + name))
```

**Strip existing blocks by object NAME, never by line position.** Desktop re-serialises TMDL on save
and reorders measures while doing it, so a `(start, end)` line pair captured from an earlier layout
can invert. `lines[:start] + lines[end:]` then duplicates everything between them instead of removing
it. That happened on 2026-08-24: a measures table went from **223 to 432 measures**, half the file
doubled, and the TMDL still parsed clean: nothing in the toolchain complained at all.

Parse into named blocks, drop the ones you own, reinsert, assert the count:

```python
import re

DECL = re.compile(r"\tmeasure (?:'([^']+)'|([^\s=]+))")

lines = OUT.read_text(encoding="utf-8").replace("\r\n", "\n").split("\n")
decl = [i for i, l in enumerate(lines) if l.startswith("\tmeasure ")]
part = next(i for i, l in enumerate(lines) if l.startswith("\tpartition "))

def block_start(i):
    # a /// doc comment belongs to the measure below it - take it with the block
    while i > 0 and lines[i - 1].startswith("\t///"):
        i -= 1
    return i

def mname(line):
    m = DECL.match(line)
    return m.group(1) or m.group(2)                # quoted or bare declaration

blocks = []
for k, i in enumerate(decl):
    s = block_start(i)
    e = block_start(decl[k + 1]) if k + 1 < len(decl) else part
    blocks.append((mname(lines[i]), lines[s:e]))

mine = {name for name, *_ in MEASURES}
before = len(blocks)
blocks = [b for b in blocks if b[0] not in mine]
print(f"stripped {before - len(blocks)} existing")

out = head + new + [l for _, b in blocks for l in b] + lines[part:]
total = sum(1 for l in out if l.startswith("\tmeasure "))
assert total == len(blocks) + len(MEASURES), f"drift: {total}"
```

Match `\tmeasure `, not `\tmeasure '`. TMDL quotes a measure name only when it needs to, and this
model uses both forms: `Measures All.tmdl` has 1,724 declarations, of which 7 are bare. They are
the sort of name that never needed quoting: single words, camelCase helpers, and one obvious
leftover from a rename. Key on the quote and those 7 never start a block; their bodies get
absorbed into the preceding quoted measure's block, and if that measure is one your generator
owns, the strip deletes them with it. The failure is silent
twice over, because a count that also keys on the quote reconciles perfectly while 7 measures are
missing.

The assert is the whole point. A generator without a final count assertion is a generator that will
double a file and tell you it succeeded, and one whose assert counts a narrower pattern than its
parser will tell you that too.

**Run it twice as the test.** Byte-identical output on the second run, or it is not idempotent.
Hash **both** trees: the doubling failure above is a TMDL failure, and a generator that duplicates
measures in the SemanticModel passes a report-only hash without a flicker. Run from the project root,
with `$gen` pointing at your generator:

```powershell
$gen = ".\build.py"

function Get-DefnHash {
  (Get-ChildItem -Recurse -File ".\<Report>.Report\definition",
                                ".\<Report>.SemanticModel\definition" |
   Get-FileHash | Select-Object -Expand Hash) -join ''
}

python $gen; $a = Get-DefnHash
python $gen; $b = Get-DefnHash
if ($a -ne $b) { throw "generator is not idempotent" } else { "idempotent" }
```

Three TMDL authoring traps that bite generators specifically, because they build blocks as lists of
strings:

- `///` doc comments must carry the **same indent** as the object they describe. A `///` at column 0
  above a tab-indented `measure` fails with `TMDL Format Error / Parsing error type - Indentation`,
  and the error names the *measure* line, not the comment.
- Never leave a blank line **after** a `///` line. That is a dangling description
  (`Unexpected line type: Empty!`) and it breaks Desktop open. Blank lines *between* sibling objects
  are fine and are what Desktop itself emits.
- `formatStringDefinition = <dax>` is a child object, not a property: it goes **after** the scalar
  properties, blank-line separated, expression inline on one line. A measure may not carry both
  `formatString:` and `formatStringDefinition`: Desktop refuses the whole project with "not
  supported scenario". Relevant here because the existing `[Row Amount]` carries a dynamic format
  string whose first line is `VAR _VALUE = ABS([Row Amount])`; see
  [03-format-string-and-cf-tax.md](03-format-string-and-cf-tax.md) before you copy that pattern
  forward.

## Cloning a page

The safe way to build a faster version of the diagnosed matrix is to clone the page, rebuild the
clone, and compare side by side before anything is deleted. Cloning is also the single most reliable
way to make Desktop refuse to open the report.

When you copy a page folder you must regenerate:

1. the **page folder name** and the `name` inside `page.json`,
2. every **visual folder name** and the `name` inside each `visual.json`,
3. every **`filterConfig` filter name**: page level *and* visual level,
4. any id that cross-references the above (group memberships, bookmark targets, sort references).

On PL Switch Lab (2026-08-23) a clone that kept its source page's filter names made Desktop open with
an **"Issues were found"** dialog, load an empty model (0 tables), and revert the title bar to
**"Untitled - Power BI Desktop"**. `pbir validate` does not catch it. That symptom is shared with the
BOM problem below, which is what makes it expensive to diagnose: you will spend an hour on the
wrong one.

Duplication alone is not the whole trigger: the field report's Desktop-authored baseline is full of
duplicate filter names (census below) and opens fine. What separates the two cases is not
established here. Regenerate the names anyway: it is one line of code against a failure that
costs an afternoon and looks like something else.

The remap, seeded so a re-run of the clone lands on the same ids:

```python
import json
import shutil
import uuid
from pathlib import Path

SRC = Path(r"...\definition\pages\<source-page-id>")   # the dashboard page
DST_KEY = "statement-deneb"


def rid(kind, key):
    return uuid.uuid5(uuid.NAMESPACE_URL, f"field/{DST_KEY}/{kind}/{key}").hex[:20]


def remap_ids(node, scope):
    """Items 2 and 3 only, inside ONE loaded page.json or visual.json: filter names, and the
    `name` on a visual container. The page id (item 1) and cross-file references (item 4) are
    not reachable from inside a single document - clone_page and a second pass do those."""
    if isinstance(node, dict):
        if isinstance(node.get("filters"), list):
            for i, f in enumerate(node["filters"]):
                if "name" in f:
                    f["name"] = rid("filter", f"{scope}/{i}/{f.get('displayName', '')}")
        if "name" in node and "visual" in node:            # a visual container
            node["name"] = rid("visual", scope)
        for v in node.values():
            remap_ids(v, scope)
    elif isinstance(node, list):
        for v in node:
            remap_ids(v, scope)


def clone_page(src: Path) -> str:
    page_id = rid("page", "root")
    dst = src.parent / page_id
    if dst.exists():
        shutil.rmtree(dst)                                 # same id every run, so re-runs replace
    shutil.copytree(src, dst)

    pj = dst / "page.json"
    doc = json.loads(pj.read_text(encoding="utf-8"))
    doc["name"] = page_id                                  # item 1 - folder name AND this must match
    doc["displayName"] = doc["displayName"] + " (Deneb)"
    remap_ids(doc, "page")
    pj.write_text(json.dumps(doc, indent=2), encoding="utf-8")

    for vdir in sorted((dst / "visuals").iterdir()):
        vj = vdir / "visual.json"
        doc = json.loads(vj.read_text(encoding="utf-8"))
        remap_ids(doc, vdir.name)                          # scope by SOURCE folder name
        vj.write_text(json.dumps(doc, indent=2), encoding="utf-8")
        vdir.rename(vdir.parent / doc["name"])             # folder name must equal the visual name

    meta_path = src.parent / "pages.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if page_id not in meta["pageOrder"]:
        meta["pageOrder"].insert(meta["pageOrder"].index(src.name) + 1, page_id)
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return page_id
```

Scope each visual by its **source folder name**, not by an enumeration index, so inserting a visual
later does not renumber everything downstream.

That is items 1-3. Item 4 lives outside the page folder and needs its own pass over the same `rid()`
mapping : `definition/bookmarks/*.bookmark.json` is the one that bites, because a bookmark pins
visual ids and the clone inherits every one of them. On the field report the source page was
referenced by one bookmark. Grep the bookmarks folder for the source page id before you assume
there is nothing to do.

Then check your work. Important caveat before you write the check as a hard gate: the field report's
Desktop-authored baseline **already contains duplicate filter names**. A census of
`definition/pages/**/*.json` on 2026-08-27 found **1,108 filter entries carrying 243 distinct names**,
of which **104 names are used more than once: 99 spanning multiple pages and 5 repeated inside a
single page**. That is the state the report was in when the diagnosed matrix was measured live in
Desktop on 2026-08-26, so this baseline is demonstrably not in the failure state.

The operational consequence: a report-wide duplicate scan on the field report returns 104 hits of pure
noise. Baseline it, then fail only on names whose entry count your generator raised.

```python
import collections
import json
from pathlib import Path

def census(defn: Path):
    seen = collections.defaultdict(list)
    for p in (defn / "pages").rglob("*.json"):
        page = p.relative_to(defn / "pages").parts[0]
        def walk(o):
            if isinstance(o, dict):
                for f in (o.get("filters") or []) if isinstance(o.get("filters"), list) else []:
                    if isinstance(f, dict) and "name" in f:
                        seen[f["name"]].append((page, str(p)))
                for v in o.values():
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)
        walk(json.loads(p.read_text(encoding="utf-8")))
    return seen

# run before the build and save `before`; run again after; compare PER-NAME COUNTS
after = census(DEFN)
grew = {k: (len(before.get(k, [])), len(v)) for k, v in after.items()
        if len(v) > 1 and len(v) > len(before.get(k, []))}
assert not grew, f"clone introduced duplicate filter names: {sorted(grew)}"
```

Compare counts, not name sets. Subtracting a baseline *set* of duplicated names looks equivalent and
is not: 104 of the 243 names are already duplicated, so if the remap misses a filter whose name is
one of those 104 (the likeliest miss on a clone, since the clone inherits its source page's
names), that name's count rises but the name was already in the baseline set, gets subtracted out, and the
gate passes. The count test also ignores a genuinely new name used once, which is what a correct
clone produces.

## Extension measures

Report-level measures live in `<report>.Report/definition/reportExtensions.json`. This report has no
such file today, so the first generator run creates it rather than editing something Desktop may be
holding. That is a one-run reprieve, not an exemption: from run two onward the file exists, Desktop
has read it, and rule zero applies to it like everything else.

Use them when the measure is presentation-only (a colour string, a label, a Deneb-side helper) so
the semantic model does not accumulate report furniture. The diagnosed matrix carries four
conditional-formatting colour measures : `[Row Highlight]`,
`[Row Highlight Text]`, `[Colour Main]`,
`[Colour Rates]`. They are scoped per measure, not per cell: each entry in
`visual.objects.values` is keyed by a `metadata` selector naming one measure column, so a given cell
pays at most a `backColor` and a `fontColor`, never all four. See
[03-format-string-and-cf-tax.md](03-format-string-and-cf-tax.md) for what that costs.

The file shape:

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/reportExtension/1.0.0/schema.json",
  "name": "extension",
  "entities": [
    {
      "name": "Statement Rows",
      "measures": [
        {
          "name": "Grid Cell Colour",
          "dataType": "Text",
          "expression": "IF ( [Row Comparison] < 0, \"#D64554\", \"#118DFF\" )",
          "references": {
            "measures": [
              { "entity": "Measures All", "name": "Row Comparison" }
            ]
          }
        }
      ]
    }
  ]
}
```

Written readably, that expression is:

```dax
IF ( [Row Comparison] < 0, "#D64554", "#118DFF" )
```

The two `entity` values in that file are not the same thing and are easy to conflate. The outer one
(`entities[].name`) is the table the *extension* measure hangs off : `Statement Rows`, chosen
because that is what the grid groups by. The one under `references.measures` names the table the
referenced *model* measure actually lives on, and `[Row Comparison]` lives on `'Measures All'`;
`Statement Rows` is a hidden columns-only table (`Order`, `Items`, `Category`, …) with no measures
at all. Check the TMDL rather than assuming the two match.

Four rules, all of which have cost a debugging session:

**`"Schema": "extension"` is mandatory in every visual reference.** Any `Measure` reference in a
`visual.json` that points at an extension measure must carry it inside the `SourceRef`: in
`queryState` projections *and* in `sortDefinition` sorts:

```json
{
  "field": {
    "Measure": {
      "Expression": { "SourceRef": { "Schema": "extension", "Entity": "Statement Rows" } },
      "Property": "Grid Cell Colour"
    }
  },
  "queryRef": "Statement Rows.Grid Cell Colour",
  "nativeQueryRef": "Grid Cell Colour"
}
```

Without it the service resolves the name against the *model* table, finds nothing, and the published
report errors per visual with **Missing_References** / *"Something's wrong with one or more fields or
you don't have required permissions"*. Fixing one visual just surfaces the next. Neither
`pbir add visual` nor hand-authored JSON adds the tag for you, `pbir validate` does not catch it, and
a raw `EVALUATE` of the same DAX works fine: only the published report reveals it. Assert it in the
build:

```python
def assert_extension_tagged(visual_json, ext_names):
    def walk(o):
        if isinstance(o, dict):
            m = o.get("Measure")
            if m and m.get("Property") in ext_names:
                src = m["Expression"]["SourceRef"]
                assert src.get("Schema") == "extension", f"untagged extension ref: {m['Property']}"
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(visual_json)
```

**`dataType` comes from a fixed enum**: Binary, Boolean, Date, DateTime, DateTimeZone, Decimal,
Double, Duration, Integer, Json, None, Null, Text, Time, Variant. `Integer` is valid; `Int64` is
not, despite appearing in some docs : `pbir validate` rejects it and publish fails.

**`references` supports `measures` only.** There is no `columns` array in the schema. A measure that
references only columns gets `"references": { "unrecognizedReferences": true }` instead.

**`pbir dax measures add` requires single-quoted table names** in the DAX (`'Accounts'[Code]`,
not `Accounts[Code]`), and it omits the `references` block entirely: add it yourself.

## Encoding: the BOM will cost you an afternoon

Never write PBIR or TMDL from Windows PowerShell 5.1 with `Set-Content -Encoding utf8`. PS 5.1 emits
a UTF-8 **BOM**, and a single `EF BB BF` breaks Desktop open. Verified 2026-08-25: a BOM on
`pages.json` produced the "Issues were found" dialog, the title reverted to
"Untitled - Power BI Desktop", and the model loaded empty: the same symptom as the duplicate filter
name bug, from a completely unrelated cause. `pbir validate --fields --qa` passed clean on the BOM'd
file. Only Desktop caught it.

This inverts the usual advice to always pass `-Encoding utf8`. For PBIR and TMDL:

- write from Python : `Path(...).write_text(s, encoding="utf-8")` emits no BOM,
- or use `-Encoding utf8NoBOM`, which requires PowerShell 7+,
- never `>`, `>>`, or `Out-File` from 5.1 onto a PBIR or TMDL file.

The cheap check after any PowerShell touch:

```bash
head -c 3 "definition/pages/<source-page-id>/page.json" | xxd
```

And the sweep worth running before every Desktop open, because it costs nothing:

```python
from pathlib import Path

ROOTS = [Path("<Report>.Report/definition"),
         Path("<Report>.SemanticModel/definition")]

bad = [p for root in ROOTS for p in root.rglob("*")
       if p.suffix in (".json", ".tmdl") and p.read_bytes()[:3] == b"\xef\xbb\xbf"]
assert not bad, f"BOM found in: {bad}"
```

Both trees, both extensions. The rule above is about PBIR *and* TMDL, so a sweep that only globs
`*.json` under the `.Report` folder cannot see the TMDL case it was written to catch.

## Validation and its limits

`pbir validate` is a schema checker. It is fast, it is worth running after every edit, and passing it
is necessary but nowhere near sufficient.

Baseline on the field report, 2026-08-27, before any performance work:

| Result | Count |
|---|---|
| Pages | 108 |
| Visuals | 1570 |
| Errors | 6 |
| Warnings | 524 |
| `SCHEMA_DEGRADED` | 511 |
| `PAGE_DIR_NOT_IN_ORDER` | 11 |
| `RENDER_REQUIRED_ROLE_MISSING` | 2 |

**All 6 errors are pre-existing false positives**, and they matter operationally: if you run validate
for the first time after your change, you will assume you caused them. They are all
`SCHEMA_ERROR / Additional properties are not allowed` on `visual.visualContainerObjects`, raised
because Desktop writes newer properties than the installed pbir's bundled schema knows about. Every
one is on a visual Desktop itself wrote:

The shape of that list, with the pages, visuals and ids left out:

- **2 errors on the page this work was about**, both on chart visuals, both for
  `spaceAbovePlotArea`.
- **4 errors on three unrelated pages nobody was touching**: two Deneb visuals, a `tableEx` and a
  `pivotTable`, flagged for `showCopilotSummaryButton`, `showChartSpecificTooltips` and
  `showTooltipFieldsOnly`.

Yours will be a different list on different pages. The shape is the point: a report this size has
errors before you arrive, most of them nowhere near your change, and two thirds of the ones here
were on pages the work never opened.

Triage errors **by location** before assuming your change broke something. Do not "fix" these by
deleting the properties: Desktop put them there and will put them back. Capture the baseline as a
file and diff against it:

```powershell
pbir validate "<Report>.Report" --json -o .\docs\performance\validate-baseline.json
```

What validate does **not** catch, all of which have shipped broken at least once:

- a UTF-8 BOM (passes clean, Desktop refuses the file)
- duplicate `filterConfig` filter names on a cloned page
- a missing `"Schema": "extension"` on an extension-measure reference (Missing_References, service only)
- the Deneb `displayName` trap: Deneb names dataset fields by the **display name in the Values well**,
  not by `nativeQueryRef`. A wrong `nativeQueryRef` fails silently: the query runs, every spec
  reference is undefined, and a null-guarded spec renders an intact skeleton with all-blank cells.
  No error in Desktop, in validate, or in Deneb's log. See
  [04-deneb-grid-template.md](04-deneb-grid-template.md).
- mis-nested format properties. Siblings must sit beside `show`, not inside it:
  `"show": {"expr": {...}, "text": {...}}` swallows `text` and the title simply never appears.
- `active: true` on a `tableEx` projection. With `active` on only the first projection Desktop renders
  that column and silently drops every later one. (`active` is a `pivotTable` row-level property,
  where it must be on **every** projection.)

And a timing caveat that validate cannot see and neither can a DAX benchmark: dynamic format strings
are evaluated per cell by the visual and never by an `EVALUATE` run. On the PL Bridge Demo lab, 182
cells went from **622 ms to 1,270 ms warm** purely from adding a dynamic format string that references
its own measure. If a visual is much slower than `tools/run_dax.ps1` says it should be, suspect that
before you suspect the render layer: [03-format-string-and-cf-tax.md](03-format-string-and-cf-tax.md)
has the detail.

The first Desktop open after any hand-edit is part of the change, not a follow-up. Budget for it.

## Pre-flight checklist

Tick every line before the generator runs.

- [ ] `pbir desktop list`: the target project is **not** open. If it is, close it (gracefully) and
      confirm `.pbi\cache.abf` has stopped growing first.
- [ ] Baseline captured: `pbir validate "<Report>.Report" --json -o validate-baseline.json`
      (expect 6 errors / 524 warnings on the field report today).
- [ ] Filter-name census saved, so the post-flight diff has something to compare against
      (243 distinct names, 104 already duplicated).
- [ ] Baseline timing captured with `tools/run_dax.ps1` under the pinned filter context, so the
      "after" number is comparable: for the diagnosed matrix that context is
      `Calendar[Fiscal Year]=2025`, `'Dim Period'[Main]="FY"`,
      `'Dim Comparison'[Comparison]="PY"`, `'Param - Measure Set'[Selection]="All Measures"`.
- [ ] Work on a **cloned page**, not the live one. The original stays untouched until the clone is
      tied out.
- [ ] Every generator starts with `require_desktop_closed()`.
- [ ] Every id is `uuid5`-seeded; nothing uses `uuid4` or a counter.
- [ ] Every TMDL patch strips by object name and asserts a final count.
- [ ] Nothing in the pipeline writes PBIR or TMDL through PowerShell 5.1.

## Post-flight checklist

- [ ] Generator run **twice**; second run is byte-identical.
- [ ] BOM sweep clean over `definition/**/*.json` and the `.SemanticModel` TMDL.
- [ ] `pbir validate` diffed against the baseline: same 6 errors, no new ones. Any new error is yours.
- [ ] Filter-name census diffed: no *new* duplicate names.
- [ ] Every extension-measure reference in every touched `visual.json` carries
      `"Schema": "extension"`, in `queryState` and in `sortDefinition`.
- [ ] Measure count in each touched `.tmdl` matches the asserted expectation (no silent doubling).
- [ ] Desktop opened once, by hand: real title in the title bar (not "Untitled"), no "Issues were
      found" dialog, model loads with its tables, the cloned page renders.
- [ ] Re-timed under the same pinned filter context, warm and cold, and the numbers written down next
      to the baseline.
- [ ] Tied out cell-for-cell against the original page before the original is touched. Two worked
      examples of what "tied out" means: the flat base-measure query's 36 ALLSELECTED total values
      diffed against the shipping matrix's own subtotal row, 0 mismatches; and the PL Bridge Demo
      lab, 27 rows × 14 columns, zero mismatches. A faster wrong number is worse than a slow right
      one.
- [ ] Desktop closed gracefully, `cache.abf` stable across three consecutive size checks, and the
      files you wrote re-read from disk to confirm they survived the close.
