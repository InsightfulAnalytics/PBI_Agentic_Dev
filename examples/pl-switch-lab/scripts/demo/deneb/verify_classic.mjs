// Numeric gate for the CLASSIC Deneb P&L spec (pl_classic_spec.json).
//
// Feeds the spec a 27-row dataset, runs every transform, and diffs all 378 cells
// against an INDEPENDENT JS implementation of the column formulas. With synthetic
// data this proves the transform chain; with the real model extract it proves the
// whole path (the fast measures already tie out against the Classic SWITCH page
// via demo_tieout.dax, so agreeing with them = agreeing with the SWITCH page).
//
// Usage: node verify_classic.mjs <spec.json> <rows.json>
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';

// The Vega and sharp runtimes live in the deneb-pbir skill's renderer package, whose location
// depends on where the plugin marketplace is installed. Point DENEB_RENDERER_PKG at that
// package.json; no default works on another machine.
if (!process.env.DENEB_RENDERER_PKG) {
  throw new Error(
    'Set DENEB_RENDERER_PKG to the path of ' +
    'plugins/custom-visuals/skills/deneb-pbir/renderer/package.json in your plugin checkout.'
  );
}
const require = createRequire(pathToFileURL(process.env.DENEB_RENDERER_PKG).href);
const vega = await import(pathToFileURL(require.resolve('vega')).href);
const vegaLite = await import(pathToFileURL(require.resolve('vega-lite')).href);

// Deneb-injected expression functions -- vanilla Vega throws on them otherwise
vega.expressionFunction('pbiColor', () => '#118DFF');
vega.expressionFunction('pbiFormat', (v) => String(v));
vega.expressionFunction('pbiPatternSVG', () => '');

const [specPath, rowsPath] = process.argv.slice(2);
const rows = JSON.parse(readFileSync(rowsPath, 'utf8'));
console.log(`dataset: ${rows.length} rows`);
if (rows.length !== 27) console.log(`  WARNING: expected 27 rows`);

// ---- independent expected values ----
const COLS = ['Actual', 'Budget', 'Var', 'Var %', 'LY', 'vs LY', 'vs LY %',
  'YTD Actual', 'YTD Budget', 'YTD Var', 'YTD Var %', 'YTD LY',
  'YTD vs LY', 'YTD vs LY %'];
const expected = new Map();
for (const r of rows) {
  const A = r['Actual'], B = r['Budget'], L = r['LY'];
  const YA = r['YTD Actual'], YB = r['YTD Budget'], YL = r['YTD LY'];
  const e = {
    'Actual': A, 'Budget': B, 'LY': L,
    'Var': A - B, 'Var %': (A - B) / B,
    'vs LY': A - L, 'vs LY %': (A - L) / L,
    'YTD Actual': YA, 'YTD Budget': YB, 'YTD LY': YL,
    'YTD Var': YA - YB, 'YTD Var %': (YA - YB) / YB,
    'YTD vs LY': YA - YL, 'YTD vs LY %': (YA - YL) / YL,
  };
  for (const c of COLS) expected.set(`${r.Line}\u0000${c}`, e[c]);
}

// ---- run the spec ----
const spec = JSON.parse(readFileSync(specPath, 'utf8'));
spec.data = { name: 'dataset', values: rows };
const compiled = vegaLite.compile(spec, { config: {} }).spec;
const view = new vega.View(vega.parse(compiled), { renderer: 'none' });
await view.runAsync();

// find the dataset carrying (Line, column, value) triples
const lineSet = new Set(rows.map((r) => r.Line));
const colSet = new Set(COLS);
let best = null;
for (const d of compiled.data.map((x) => x.name)) {
  let data;
  try { data = view.data(d); } catch { continue; }
  if (!Array.isArray(data) || !data.length) continue;
  const keys = Object.keys(data[0]);
  if (!keys.includes('column') || !keys.includes('value') || !keys.includes('Line')) continue;
  const cells = data.filter((x) => lineSet.has(x.Line) && colSet.has(x.column)).length;
  if (!best || cells > best.cells) best = { name: d, cells, data };
}
if (!best) { console.log('no grid dataset found'); process.exit(2); }
console.log(`grid found in "${best.name}": ${best.cells} cells`);

let bad = 0, missing = 0;
for (const [key, want] of expected) {
  const [line, col] = key.split('\u0000');
  const hit = best.data.find((x) => x.Line === line && x.column === col);
  if (!hit) { missing++; continue; }
  const got = hit.value;
  const bothDead = (!isFinite(want) || want == null) && (!isFinite(got) || got == null);
  if (bothDead) continue;
  if (got == null || !isFinite(got)
      || Math.abs(got - want) > Math.max(1e-6, Math.abs(want) * 1e-9)) {
    if (bad < 12) console.log(`  DIFF ${line.trim()} / ${col}: got ${got}  want ${want}`);
    bad++;
  }
}
console.log(`\nCLASSIC SPEC vs INDEPENDENT CALC: ${expected.size} cells | BADDIFF=${bad} | MISSING=${missing}`);
process.exit(bad || missing ? 1 : 0);
