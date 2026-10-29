---
name: fabric-app-workflow
version: 26.40.3
description: The authoring conventions for a Fabric / Rayfin data app over a published semantic model (how query+spec+factory files are organised, the mockup→wire-spec→production pipeline, the Claude Design ZIP handoff, reusable Sparkline props, and matrix/table UI gotchas). Invoke when adding a new chart/visual to a Fabric App, asking "where do DAX queries live", "how do I wire a Vega spec", "where do I put a new query", working with `mockups/`, `.vl.json5` / `.jsonc` specs, `npm run mockups:watch` / `wire-spec` / `import-design`, the `src/queries/<domain>/` triplet pattern, building a reusable Sparkline component, or fighting matrix/table column widths and `replace_all` indentation edits.
---

# Fabric App authoring workflow

Conventions for building visuals in a Rayfin Fabric App over a published semantic model.
Pairs with `rayfin-fabric-cli` (CLI/deploy gotchas) and `vega-lite-app-gotchas` (spec traps).

## Single-DAX-file triplet: `src/queries/<domain>/`

Each visual gets three files under a domain folder:

- `<name>.dax`: the raw DAX (never inline DAX in components)
- `<name>.json`: the Vega-Lite spec
- `<name>.ts`: a **factory** exporting `{ connection, query, columnMetadata, vegaLiteSpec }`

The factory is where you parameterize the spec or query, e.g. accept a `categories?: string[]`
and inject a `FILTER` clause. **Components consume the factory function, not the raw files.**
Confirm `columnMetadata` keys from real CLI output:

```powershell
npx fabric-app-data query semanticModel <alias> -q "EVALUATE ..."
```

## Mockup → wire-spec → production pipeline

1. Hand-author a `.vl.json5` (or `.jsonc`) in `mockups/` using **inline preview data**.
2. `npm run mockups:watch` compiles each to `mockups/.preview/<name>_nc.vl.json` (clean JSON
   for Vega Viewer / vega-embed) so you can eyeball it before wiring.
3. Once the spec looks right:
   `npm run wire-spec -- mockups/<name>.vl.json5 --domain <d> --name <n>` scaffolds the
   `.dax` / `.ts` / `.json` triplet.
4. Fill in the DAX and the `columnMetadata` keys from a CLI query output.

Start specs from the 60 `deneb-templates/` references where possible: copy, rename to
`.vl.json5` / `.jsonc`, adapt to the data shape, let the watcher preview it.

## Claude Design handoff (HTML/CSS prototype → mockups)

1. Save the Claude Design export ZIP anywhere on disk.
2. `npm run import-design -- --zip "path/to/export.zip"` extracts to
   `design-imports/<name>/` and generates a `manifest.json`.
3. Process the manifest: each `<script id="data-manifest">` visual becomes a mockup spec + a
   DAX query.
4. See `design-system/HANDOFF-CONTEXT.md` for the full copy-paste block.

## Reusable Sparkline component props

When reusing a Sparkline across pages with different value scales, parameterize rather than
fork the component:

- `labelTitle?: string` (default `"Period"`): lets each consumer rename the tooltip x-axis
  label without breaking the others.
- `tooltipFormat?: (value: number) => string`: if supplied, pre-compute a `valueTip` string
  in the data table and reference it as a `nominal` field in the tooltip. Sidesteps the
  d3-format mixed-units problem (see `vega-lite-app-gotchas` #3) entirely.

## Matrix / table UI gotchas

- **Column widths:** `tableLayout: "fixed"` with an explicit `width` on every `<th>` is the
  only reliable way to control widths. Mix pixel and percent widths cautiously.
- **Nudging content within a column:** instead of resizing, add `paddingLeft`/`paddingRight`
  to the `<td>` (and the matching `<th>`); it pushes content without breaking the layout math.
- **`replace_all` respects indentation:** if the same line appears at two indent levels (e.g.
  a per-row cell vs a total-row cell), one `old_string` only matches one of them. **Grep after
  a `replace_all`** to confirm every intended occurrence was actually hit.
