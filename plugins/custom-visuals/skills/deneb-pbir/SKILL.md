---
name: deneb-pbir
version: 26.25
description: Round-trip TOOLING for Deneb specs in PBIR — extract/embed the Vega/Vega-Lite spec in visual.json and offline-render it (Vega→PNG/SVG) to verify without Power BI. Use whenever a task touches a Deneb visual's spec ("edit the Deneb visual", "change the Vega spec", "fix the Deneb chart", patching jsonSpec in visual.json), or when a Deneb spec needs rendering/verification without Power BI. Replaces the ad-hoc inline python patch scripts and per-session npm installs used previously. Spec authoring rules, theme colors, and interactivity live in the custom-visuals:deneb-visuals skill.
---

# Deneb specs in PBIR

Deneb stores its spec inside `visual.json` at `visual.objects.vega[0].properties.jsonSpec.expr.Literal.Value` — a single-quote-wrapped PBIR string literal with embedded `'` doubled. Never hand-edit that string; use the scripts.

> This skill is the sanctioned exception to the CLAUDE.md "prefer Edit for PBIR files" rule: `embed` script-patches visual.json but writes a `.bak` beside it, which substitutes for checkpoint protection (rewind can't revert script writes — restore from the `.bak` instead).

## Edit loop

```bash
S="${CLAUDE_PLUGIN_ROOT}/skills/deneb-pbir/scripts/deneb_spec.py"
# 1. extract to a real JSON file (also validates it parses)
python "$S" extract "<...>/visuals/myDeneb/visual.json" -o spec.json --config config.json
# 2. edit spec.json normally (Edit tool — full JSON, no escaping)
# 3. verify offline BEFORE touching the report (see renderer below)
# 4. embed back (re-validates, writes visual.json + .bak)
python "$S" embed "<...>/visuals/myDeneb/visual.json" --spec spec.json
# 5. pbir validate, then the pbi-verify-loop skill if Desktop is open
```

`provider` in the same properties block says which grammar (`vega` / `vegaLite`) — don't mix schema URLs.

## Offline renderer (one-time `npm install`, then reuse)

First use only — install the renderer deps once (they're gitignored, not shipped in the repo):

```bash
( cd "${CLAUDE_PLUGIN_ROOT}/skills/deneb-pbir/renderer" && npm install )
```

Then render (deps resolve from `renderer/node_modules`; do NOT reinstall per session):

```bash
node "${CLAUDE_PLUGIN_ROOT}/skills/deneb-pbir/renderer/render.mjs" spec.json out.png \
  [--data rows.json] [--data-name dataset] [--scale 2] [--provider vega|vegaLite]
```

- Dependencies (vega, vega-lite, sharp) install into `renderer/node_modules` (gitignored) and resolve from anywhere once installed.
- Deneb specs get data from Power BI at runtime — an offline render of the bare spec shows only static chrome. Pass `--data` with a JSON array of sample rows shaped like the visual's field mapping (dataset name defaults to `dataset`, Deneb's convention).
- Grammar is detected from `$schema` (fallback: mark/encoding heuristic). If the spec has no `$schema`, pass `--provider` with the value from the visual's `provider` property.
- `--scale` alone controls PNG size (spec pixels × scale). `.svg` output extension skips sharp entirely.
- If writing any OTHER inline node script against vega: the packages are ESM-only — dynamic `import()`, never `require()`.

## Authoring rules & gotchas — see deneb-visuals

Spec authoring rules (theme `pbiColor`, escaping, interactivity, responsive sizing) and the hard-won Deneb gotchas (cross-filter-out, per-point tooltips, validate-not-sufficient) live in the **`custom-visuals:deneb-visuals`** skill. This skill is the round-trip *tooling* only (extract / embed / offline-render).

- House config convention: `{"background":"transparent","view":{"stroke":"transparent"},"font":"Segoe UI"}` — keep `jsonConfig` consistent with existing visuals.
- Writing any OTHER inline node script against vega: packages are ESM-only — dynamic `import()`, never `require()`.
