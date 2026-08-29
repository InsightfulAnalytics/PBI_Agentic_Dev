# PBIR build safety: rebuilding a matrix without breaking the report

The rules that keep the rebuild from destroying the report you are rebuilding. Every one of them
broke something at least once, and most of them broke it *silently*: no error, no dialog, no failed
validation, just a report that is subtly wrong the next time someone opens it.

Assume the report is large. The field report this came from was 108 pages and 1,570 visuals. You
are not going to eyeball a diff of that, so everything here assumes generated, re-runnable edits
with machine checks around them.

## Assumed known, not repeated here

These live in the agent's standing TMDL/PBIR authoring rules. Pointers only, so you know they exist
and can go read them before you trip over one:

- **Desktop must be closed.** It re-serialises its in-memory copy over your disk edits on save or
  close, silently. Guard every generator with a window-title check before it touches anything.
- **Never force-kill Desktop after a save.** `cache.abf` is still being written for tens of seconds
  after the title bar drops its `*`; killing in that window corrupts it.
- **Idempotent generators.** Seed ids from `uuid5`, strip TMDL blocks by object *name* never by line
  position, assert a final count, and run the generator twice as the test.
- **TMDL indentation.** A measure's expression is one level deeper than its properties;
  `formatStringDefinition` is a child object after the scalar properties, blank-line separated; no
  blank line after a `///`.
- **Cloning regenerates every id**, including `filterConfig` filter names, page and visual folder
  names, and anything cross-referencing them.
- **Never write PBIR or TMDL from PowerShell 5.1** (`Set-Content -Encoding utf8` emits a BOM, which
  breaks Desktop open). Write from Python.
- **`"Schema": "extension"`** is mandatory in every visual reference to a report-level extension
  measure, in `queryState` *and* `sortDefinition`, or the published report errors with
  `Missing_References`.

## Clone and compare: the workflow

The safe way to build a faster version of a slow matrix is to **clone the page, rebuild the clone,
and compare side by side before anything is deleted.** The original stays untouched until the clone
is tied out. That is the whole discipline, and it is also what makes the before/after measurement
possible at all, since both versions sit in one report under one filter context.

Cloning is also the single most reliable way to make Desktop refuse to open the report, so the
remap below is not optional. Seed it so a re-run of the clone lands on the same ids:

```python
import json, shutil, uuid
from pathlib import Path

SRC = Path(r"...\definition\pages\<source-page-id>")
DST_KEY = "statement-rebuild"


def rid(kind, key):
    return uuid.uuid5(uuid.NAMESPACE_URL, f"{DST_KEY}/{kind}/{key}").hex[:20]


def remap_ids(node, scope):
    """Filter names and the visual container `name`, inside ONE loaded document."""
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
    doc["name"] = page_id                                  # folder name AND this must match
    doc["displayName"] = doc["displayName"] + " (rebuild)"
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
later does not renumber everything downstream. That covers the page id, the visual ids and the
filter names inside the page folder. Ids that cross-reference the page live *outside* it and need
their own pass over the same `rid()` mapping: `definition/bookmarks/*.bookmark.json` is the one that
bites, because a bookmark pins visual ids and the clone inherits every one of them. Grep the
bookmarks folder for the source page id before you assume there is nothing to do.

## The filter-name census: compare counts, not name sets

Then check your work, and read this before you write the check as a hard gate.

A Desktop-authored report of any age **already contains duplicate filter names**. A census of
`definition/pages/**/*.json` on the field report found **1,108 filter entries carrying 243 distinct
names, of which 104 names are used more than once**: 99 spanning multiple pages and 5 repeated
inside a single page. That is the state the report was in while the diagnosed matrix was being
measured live in Desktop, so this baseline is demonstrably not in the failure state. A report-wide
duplicate scan therefore returns 104 hits of pure noise: baseline it, then fail only on names whose
entry count your generator raised.

```python
import collections, json
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

**Compare counts, not name sets.** Subtracting a baseline *set* of duplicated names looks
equivalent and is not. 104 of the 243 names are already duplicated, so if the remap misses a filter
whose name is one of those 104 (the likeliest miss on a clone, since the clone inherits its source
page's names), that name's count rises, but the name was already in the baseline set, gets
subtracted out, and the gate passes. The count test also correctly ignores a genuinely new name
used once, which is what a correct clone produces.

## Validation and its limits

`pbir validate` is a schema checker. Fast, worth running after every edit, and passing it is
necessary but nowhere near sufficient.

**Capture a baseline before you change anything**, because a report this size has errors before you
arrive:

```powershell
pbir validate "<Report>.Report" --json -o .\validate-baseline.json
```

The field report's baseline was 108 pages, 1,570 visuals, **6 errors and 524 warnings** (511
`SCHEMA_DEGRADED`, 11 `PAGE_DIR_NOT_IN_ORDER`, 2 `RENDER_REQUIRED_ROLE_MISSING`). All 6 errors were
pre-existing false positives: `SCHEMA_ERROR / Additional properties are not allowed` on
`visual.visualContainerObjects`, raised because Desktop writes newer properties than the installed
pbir's bundled schema knows about. Every one was on a visual Desktop itself wrote, and only two of
the six were on the page the work was about.

Yours will be a different list. The shape is the point:

- **Triage by location before assuming your change broke something.** If you run validate for the
  first time *after* your change, you will assume you caused all of it.
- **Do not "fix" these by deleting the properties.** Desktop put them there and will put them back.
- **Diff against the captured baseline.** Same errors, no new ones. Any new error is yours.

What validate does **not** catch, all of which have shipped broken at least once:

- a UTF-8 BOM (passes clean, Desktop refuses the file)
- duplicate `filterConfig` filter names on a cloned page
- a missing `"Schema": "extension"` on an extension-measure reference (service only)
- the Deneb `displayName` trap: Deneb names dataset fields by the **display name in the Values
  well**, not by `nativeQueryRef`. A wrong `nativeQueryRef` fails silently, the query runs, every
  spec reference is undefined, and a null-guarded spec renders an intact skeleton with all-blank
  cells. No error in Desktop, in validate, or in Deneb's log.
- mis-nested format properties. Siblings must sit beside `show`, not inside it:
  `"show": {"expr": {...}, "text": {...}}` swallows `text` and the title simply never appears.
- `active: true` on a `tableEx` projection. With `active` on only the first projection Desktop
  renders that column and silently drops every later one. (`active` is a `pivotTable` row-level
  property, where it must be on **every** projection.)

And one timing caveat neither validate nor a DAX benchmark can see: dynamic format strings are
evaluated per cell by the visual and never by an `EVALUATE`. 182 cells went from **622 ms to
1,270 ms warm** purely from adding a format string that references its own measure.

The first Desktop open after any hand-edit is part of the change, not a follow-up. Budget for it.

## Pre-flight checklist

Tick every line before the generator runs.

- [ ] `pbir desktop list`: the target project is **not** open. If it is, close it gracefully and
      confirm `.pbi\cache.abf` has stopped growing first.
- [ ] Baseline captured: `pbir validate "<Report>.Report" --json -o validate-baseline.json`, and its
      error and warning counts written down.
- [ ] Filter-name census saved, so the post-flight diff has something to compare against.
- [ ] Baseline timing captured under the **pinned filter context**, so the "after" number is
      comparable. Write down every slicer selection, including the ones you left clear.
- [ ] Work on a **cloned page**, not the live one.
- [ ] Every generator starts with its Desktop-closed guard.
- [ ] Every id is `uuid5`-seeded; nothing uses `uuid4` or a counter.
- [ ] Every TMDL patch strips by object name and asserts a final count.
- [ ] Nothing in the pipeline writes PBIR or TMDL through PowerShell 5.1.

## Post-flight checklist

- [ ] Generator run **twice**; second run is byte-identical. Hash **both** trees, report and model:
      a generator that doubles measures passes a report-only hash without a flicker.
- [ ] BOM sweep clean over `definition/**/*.json` **and** the `.SemanticModel` TMDL. Both trees,
      both extensions.
- [ ] `pbir validate` diffed against the baseline: same errors, no new ones.
- [ ] Filter-name census diffed: no *new* duplicate names, by count.
- [ ] Every extension-measure reference in every touched `visual.json` carries
      `"Schema": "extension"`, in `queryState` and in `sortDefinition`.
- [ ] Measure count in each touched `.tmdl` matches the asserted expectation (no silent doubling).
- [ ] Desktop opened once, by hand: real title in the title bar (not "Untitled"), no "Issues were
      found" dialog, model loads with its tables, the cloned page renders.
- [ ] Re-timed under the same pinned filter context, warm and cold, written down next to the
      baseline.
- [ ] **Tied out cell-for-cell against the original page before the original is touched.** Two
      worked examples of what "tied out" means: a flat base-measure query's 36 `ALLSELECTED` total
      values diffed against the shipping matrix's own subtotal row, 0 mismatches; and a 27 row x
      14 column rebuild, zero mismatches. A faster wrong number is worse than a slow right one.
- [ ] Desktop closed gracefully, `cache.abf` stable across three consecutive size checks, and the
      files you wrote re-read from disk to confirm they survived the close.
