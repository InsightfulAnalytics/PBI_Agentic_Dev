// Numeric verification for the Deneb P&L spec.
//
// Compiles the Vega-Lite spec, feeds it the REAL 30-row dataset exported from the model,
// runs every transform, then pulls each intermediate dataset back out and looks for one
// that carries the full 13 x 14 grid. Every value found is diffed against _golden_182.csv,
// the snapshot of the shipped page-6 numbers.
//
// This is the gate that matters: a spec can render beautifully and still be arithmetically
// wrong (a ratio-of-differences instead of a difference-of-ratios shows up as plausible
// numbers, not as an error). Rendering a PNG proves nothing about the maths.
//
// Usage: node verify_spec.mjs <spec.json> <dataset.csv> <golden.csv>
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';

// vega / vega-lite are ESM-only, and require.resolve hands back a Windows path that
// import() rejects -- it must be a file:// URL.
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

// Deneb injects its own expression functions into the Vega runtime. Vanilla Vega throws
// "Unrecognized function: pbiColor" on any spec that uses them, so stub them here --
// otherwise a perfectly good Deneb spec looks like a parse failure offline.
const PBI_PALETTE = ['#118DFF', '#12239E', '#E66C37', '#6B007B', '#E044A7',
                     '#744EC2', '#D9B300', '#D64550'];
const SENTIMENT = { min: '#FD625E', middle: '#F2C80F', max: '#01B8AA',
                    negative: '#FD625E', positive: '#01B8AA', neutral: '#F2C80F',
                    bad: '#FD625E', good: '#01B8AA' };
vega.expressionFunction('pbiColor', (i, shade) => {
  const base = typeof i === 'string'
    ? (SENTIMENT[i] ?? PBI_PALETTE[0])
    : PBI_PALETTE[(Number(i) || 0) % PBI_PALETTE.length];
  return base; // shade is ignored offline; only the colour's presence matters here
});
vega.expressionFunction('pbiFormat', (v, f) => String(v));
vega.expressionFunction('pbiPatternSVG', () => '');

const [specPath, dataPath, goldPath] = process.argv.slice(2);

function readCsv(p) {
  const txt = readFileSync(p, 'utf8').replace(/^\uFEFF/, '').trim();
  const rows = [];
  const lines = txt.split(/\r?\n/);
  const split = (l) => {
    const out = []; let cur = ''; let q = false;
    for (let i = 0; i < l.length; i++) {
      const c = l[i];
      if (c === '"') { if (q && l[i + 1] === '"') { cur += '"'; i++; } else q = !q; }
      else if (c === ',' && !q) { out.push(cur); cur = ''; }
      else cur += c;
    }
    out.push(cur); return out;
  };
  const hdr = split(lines[0]);
  for (let i = 1; i < lines.length; i++) {
    const c = split(lines[i]); const o = {};
    hdr.forEach((h, j) => (o[h] = c[j]));
    rows.push(o);
  }
  return rows;
}

// ---- the real dataset, renamed to the display names Deneb hands the spec ----
const raw = readCsv(dataPath);
const dataset = raw.map((r) => ({
  'Line': r['P&L Lines[Line]'],
  'P&L View': r['P&L View[P&L View]'],
  'Amount': Number(r['[Amount]']),
  'Trading Stores': Number(r['[Trading Stores]']),
  'Active Products': Number(r['[Active Products]']),
}));
console.log(`dataset: ${dataset.length} rows`);

const gold = new Map();
for (const g of readCsv(goldPath)) {
  gold.set(`${g.Line}\u0000${g.Item}`, g.Value === '' ? null : Number(g.Value));
}
console.log(`golden : ${gold.size} cells`);

// ---- compile + run ----
const spec = JSON.parse(readFileSync(specPath, 'utf8'));
spec.data = { name: 'dataset', values: dataset };
// the offline runtime needs a size; Deneb supplies one from the container at runtime
const compiled = vegaLite.compile(spec, { config: {} }).spec;

const view = new vega.View(vega.parse(compiled), { renderer: 'none' });
await view.runAsync();

// ---- find whichever internal dataset carries the grid ----
const names = compiled.data.map((d) => d.name);
const ROWS = [
  'Total Income', 'Total Cost of Sales', 'Gross Profit', 'Total Operating Expenses',
  'Net Profit', 'Gross Margin %', 'Net Margin %', 'COGS % of Income', 'Opex % of Income',
  'Income per Trading Store', 'Net Profit per Trading Store', 'Income per Active Product',
  'Trading Stores',
];
const COLS = [
  'Actual', 'LY', 'vs LY', 'vs LY %', 'Budget', 'Var to Budget', 'Var to Budget %',
  'YTD Actual', 'YTD LY', 'YTD vs LY', 'YTD vs LY %', 'YTD Budget',
  'YTD Var to Budget', 'YTD Var to Budget %',
];
const rowSet = new Set(ROWS), colSet = new Set(COLS);

let best = null;
for (const n of names) {
  let d;
  try { d = view.data(n); } catch { continue; }
  if (!Array.isArray(d) || !d.length) continue;
  const keys = Object.keys(d[0]);
  const rowKey = keys.find((k) => d.some((x) => rowSet.has(x[k])));
  const colKey = keys.find((k) => k !== rowKey && d.some((x) => colSet.has(x[k])));
  if (!rowKey || !colKey) continue;
  // After the final fold the row still carries the pre-fold pivot columns ("Actual",
  // "LY", ...), so the first numeric field is NOT the folded value. Exclude anything
  // whose name is itself a row or column label, and prefer a field literally called
  // "value"/"val" if one exists.
  const cand = keys.filter(
    (k) => k !== rowKey && k !== colKey && !rowSet.has(k) && !colSet.has(k)
      && d.some((x) => typeof x[k] === 'number')
  );
  const valKey = cand.find((k) => /^(value|val|v)$/i.test(k)) || cand[0];
  if (!valKey) continue;
  const cells = d.filter((x) => rowSet.has(x[rowKey]) && colSet.has(x[colKey])).length;
  if (!best || cells > best.cells) best = { n, rowKey, colKey, valKey, cells, d };
}

if (!best) {
  console.log('\nNo dataset found carrying (row, column, value) triples.');
  console.log('datasets seen:');
  for (const n of names) {
    let d; try { d = view.data(n); } catch { continue; }
    if (Array.isArray(d) && d.length) {
      console.log(`  ${n}: ${d.length} rows, keys ${JSON.stringify(Object.keys(d[0]))}`);
    }
  }
  process.exit(2);
}

console.log(`\ngrid found in "${best.n}": ${best.cells} cells`
  + ` (row=${best.rowKey}, col=${best.colKey}, value=${best.valKey})`);

let bad = 0, checked = 0, missing = [];
for (const r of ROWS) {
  for (const c of COLS) {
    const hit = best.d.find((x) => x[best.rowKey] === r && x[best.colKey] === c);
    if (!hit) { missing.push(`${r} / ${c}`); continue; }
    const got = hit[best.valKey];
    const want = gold.get(`${r}\u0000${c}`);
    checked++;
    if (want == null && (got == null || !isFinite(got))) continue;
    if (want == null || got == null || !isFinite(got)
        || Math.abs(got - want) > Math.max(1e-6, Math.abs(want) * 1e-9)) {
      if (bad < 15) console.log(`  DIFF ${r} / ${c}: got ${got}  want ${want}`);
      bad++;
    }
  }
}
if (missing.length) {
  console.log(`  MISSING ${missing.length} cells, first: ${missing.slice(0, 5).join(' | ')}`);
}
console.log(`\nDERIVED vs GOLDEN: checked ${checked}/182 | BADDIFF=${bad}`
  + ` | MISSING=${missing.length}`);
process.exit(bad || missing.length ? 1 : 0);
