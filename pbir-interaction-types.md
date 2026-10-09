# fix: visualInteractions types are DataFilter, HighlightFilter and NoFilter

`pbip:pbir-format` gives the `type` of a PBIR `visualInteractions` entry as `"NoFilter"`,
`"Filter"` or `"Highlight"`. The last two aren't valid values. The page schema allows `"DataFilter"`,
`"HighlightFilter"`, `"NoFilter"` and `"Default"`, and a report that uses `"Highlight"` fails to
open in Power BI Desktop. This PR corrects the names wherever the plugin states them.

Line numbers below are from `main` at f8d3580.

## What happened

An agent following `references/page.md` wrote twelve `"type": "Highlight"` entries into a
page.json, so that four visuals would cross-highlight each other. Power BI Desktop then would not
open the report: "Something went wrong. Failed to load the report." Changing the twelve entries to
`"HighlightFilter"` fixed it. Validating that page.json against its `$schema` reports each entry as
`'Highlight' is not valid under any of the given schemas`.

## Evidence

- **The schema.** The page schema's `VisualInteractionFilterType` allows exactly four values, and
  every published version from 1.0.0 to 2.1.0 has the same four (checked 2026-10-09):

  | Value | Schema description | Desktop's Edit interactions icon |
  | --- | --- | --- |
  | `DataFilter` | Data point selection is added as a filter to the target visual. | Filter |
  | `HighlightFilter` | Data point selection is added as a highlight to the target visual. | Highlight |
  | `NoFilter` | Data point selection is ignored by the target visual. | None |
  | `Default` | The target visual type determines if it should accept the interaction as a highlight or as a filter. | (not set) |

- **Desktop's own files.** A Desktop-saved report with interactions on 27 pages holds 77
  `NoFilter`, 16 `DataFilter` and 6 `HighlightFilter` entries, and no `Default`, `Filter` or
  `Highlight` ones.
- **Where the wrong names came from.** Desktop's Edit interactions icons are called Filter,
  Highlight and None (Microsoft Learn, "Change how visuals interact in a Power BI report"). The
  docs give the icon names, not the values the file stores.

## Changes

### 1. `pbip:pbir-format` `references/page.md`, line 36

This is the main fix. Replace:

```markdown
Types: `"NoFilter"` (disable cross-filter), `"Filter"`, `"Highlight"`.
```

with:

```markdown
`type` takes one of the four values of the page schema's `VisualInteractionFilterType`:

| `type` | Edit interactions icon | The target visual |
| --- | --- | --- |
| `"DataFilter"` | Filter | shows only the data that matches the selection |
| `"HighlightFilter"` | Highlight | keeps all its data and highlights the part that matches |
| `"NoFilter"` | None | ignores the selection |
| `"Default"` | (not set) | highlights or filters, as its visual type decides |

`"Filter"` and `"Highlight"` are the icon names, not values. Any other value is a schema error,
and a report with `"Highlight"` entries fails to open in Power BI Desktop with "Something went
wrong. Failed to load the report." Desktop-saved files hold `DataFilter`, `HighlightFilter` and
`NoFilter` entries, and no `Default` ones. Line charts, scatter charts and maps can only be
filtered, so don't give them `"HighlightFilter"`. [Page schema 1.0.0 to 2.1.0. Verified 2026-10-09.]

Retest: `curl -s https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json | python3 -c "import json,sys; print([a['const'] for a in json.load(sys.stdin)['definitions']['VisualInteractionFilterType']['anyOf']])"`
```

### 2. `pbip:pbir-format` `references/visual-json.md`, lines 354 to 356 and 373

Replace line 354 and the paragraph after it:

```markdown
Types: `"NoFilter"` (disable cross-filter), `"Filter"` (cross-filter), `"Highlight"` (cross-highlight).

Only interactions that deviate from the default need to be listed. By default, all visuals cross-filter each other.
```

with:

```markdown
`type` is `"DataFilter"`, `"HighlightFilter"`, `"NoFilter"` or `"Default"`. Any other value is a
schema error, and a report with `"Highlight"` entries fails to open in Power BI Desktop. See
[page.md, visualInteractions](page.md#visualinteractions) for what each does.

List only the pairs that should differ from the default. By default a click cross-highlights
visuals such as column and bar charts, and cross-filters line charts, scatter charts and maps.
`defaultFilterActionIsDataFilter: true` in report.json makes clicks filter instead of highlight.
```

The old "all visuals cross-filter each other" was also wrong: Microsoft Learn says visuals
cross-filter and cross-highlight by default, and the report schema describes
`defaultFilterActionIsDataFilter` as applying the selection "as a filter instead of a highlight".

On line 373, replace `(NoFilter/Filter/Highlight)` with `(DataFilter/HighlightFilter/NoFilter)`.

### 3. `pbip:pbir-format` `SKILL.md`, line 125

In the "Edit visual interactions" row, replace `(NoFilter, Filter, Highlight)` with
`(DataFilter, HighlightFilter, NoFilter)`.

### 4. The legacy conversion how-to and script

- `references/how-to/convert-legacy-to-pbir.md`: lines 62, 158, 161 and 254.
- `references/how-to/fix-broken-field-references.md`: line 155.
- `scripts/convert_legacy_to_pbir.py`: lines 698 to 709.

These say PBIR stores only `NoFilter` entries, and that `"Filter"` must be left out because it
causes schema errors. `"Filter"` fails only because it isn't a value. `"DataFilter"` and
`"HighlightFilter"` are valid, and Desktop writes them. The script converts only legacy type 3, so
a converted report loses every explicit Filter and Highlight interaction. That is harmless only
where the dropped setting happens to match the default.

Upstream commit 42fd294 (2026-07-16, "keep Power BI workflows CLI-only") rewrote this how-to
around `pbir report convert`. The same commit deleted the script and took the interactions note
out of `fix-broken-field-references.md`. Taking upstream's versions at the next harvest removes all
of these lines. To fix them here instead:

- Line 62: replace `(only NoFilter entries; Filter is default)` with
  `(DataFilter, HighlightFilter and NoFilter entries, one per pair that differs from the default)`.
- Line 158: replace `(convert type 3 -> "NoFilter", omit type 1)` with
  `(convert type 1 -> "DataFilter", 2 -> "HighlightFilter", 3 -> "NoFilter")`.
- Line 161: replace the paragraph with `**Visual interactions**: write each legacy relationship with
  its PBIR type. The schema has no "Filter" or "Highlight" value, so writing either fails
  validation.`
- Line 254: replace the bullet with `"Filter" or "Highlight" as a visualInteractions type (use
  "DataFilter" or "HighlightFilter")`.
- `fix-broken-field-references.md` line 155: replace the last sentence with `Convert all three
  types, not only NoFilter (see convert-legacy-to-pbir.md).`
- The script: write `"DataFilter"` for type 1 and `"HighlightFilter"` for type 2, as well as
  `"NoFilter"` for type 3, and update the comment on line 699.

Before changing the script, check the legacy codes against a legacy report. The mapping (1
Filter, 2 Highlight, 3 NoFilter) comes from line 33 and the script's comment, and nobody
re-checked it for this PR.

### 5. `FORK-CHANGES.md`

Under "Modified upstream-authored files", record the type-name fix in `pbir-format/SKILL.md` and
`references/{page,visual-json}.md`, plus the how-to files and script if they are fixed here. A
harvest then keeps the fix until upstream has it.

## Upstream

Upstream `main` (data-goblin/power-bi-agentic-development) has the same wrong names, checked
2026-10-09:

- `references/page.md` line 36
- `references/visual-json.md` lines 261 and 280
- `SKILL.md` line 120

`CONTRIBUTING.md` sends fixes to upstream-authored content upstream, so open the same fix there too.

## Checks

```bash
python scripts/check-skill-hygiene.py
bash scripts/validate-plugins.sh
```
