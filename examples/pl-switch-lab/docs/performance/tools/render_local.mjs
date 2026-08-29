// Offline Vega-Lite -> PNG renderer for Deneb specs, with Deneb's injected runtime stubbed.
//
// Why this exists: a Deneb spec that uses Deneb's theme helpers (pbiColor, pbiFormat,
// pbiPatternSVG) throws "Unrecognized function" in a plain Vega renderer, which makes a
// perfectly valid spec look broken offline. This registers the same stubs Deneb injects,
// then renders, so you can look at the grid in seconds instead of reloading Power BI Desktop.
//
// It also injects width/height, which a shipped Deneb spec deliberately omits (Deneb sizes
// from the container via autosize fit; explicit dimensions there produce an inner scrollbar).
//
// Usage:
//   node render_local.mjs <spec.json> <config.json> <rows.json> <out.png> [width] [height]
//
// rows.json is a plain array of objects matching the spec's dataset contract -- the field
// names must be the DISPLAY names the projections carry, not the native measure names.
// See ../04-deneb-grid-template.md.
//
// Dependencies: vega, vega-lite and sharp. Resolution order:
//   1. NODE_PATH / a node_modules beside this file (npm i vega vega-lite sharp)
//   2. DENEB_RENDERER_PKG env var pointing at a package.json that has them
//
// There is deliberately no third fallback. This used to hardcode one machine's plugin
// checkout, which resolved for its author and for nobody else.
import { readFileSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';

function makeRequire() {
  const candidates = [
    import.meta.url,
    process.env.DENEB_RENDERER_PKG
      ? pathToFileURL(process.env.DENEB_RENDERER_PKG).href
      : null,
  ].filter(Boolean);

  for (const base of candidates) {
    try {
      const req = createRequire(base);
      req.resolve('vega');
      req.resolve('vega-lite');
      req.resolve('sharp');
      return req;
    } catch {
      // try the next base
    }
  }
  throw new Error(
    'Could not resolve vega, vega-lite and sharp. Run `npm i vega vega-lite sharp` beside ' +
      'this file, or set DENEB_RENDERER_PKG to a package.json that has them.'
  );
}

const require = makeRequire();
const vega = await import(pathToFileURL(require.resolve('vega')).href);
const vegaLite = await import(pathToFileURL(require.resolve('vega-lite')).href);
const sharp = (await import(pathToFileURL(require.resolve('sharp')).href)).default;

// ---------------------------------------------------------------- Deneb runtime stubs
// Deneb resolves these against the report theme at render time. Offline we only need them
// to return something plausible so the spec compiles and the layout is honest.
const PBI_PALETTE = [
  '#118DFF', '#12239E', '#E66C37', '#6B007B',
  '#E044A7', '#744EC2', '#D9B300', '#D64550',
];
const SENTIMENT = {
  min: '#FD625E', middle: '#F2C80F', max: '#01B8AA',
  negative: '#FD625E', positive: '#01B8AA', neutral: '#F2C80F',
  bad: '#FD625E', good: '#01B8AA',
};
vega.expressionFunction('pbiColor', (i) =>
  typeof i === 'string'
    ? SENTIMENT[i] ?? PBI_PALETTE[0]
    : PBI_PALETTE[(Number(i) || 0) % PBI_PALETTE.length]
);
vega.expressionFunction('pbiFormat', (v) => String(v));
vega.expressionFunction('pbiPatternSVG', () => '');

// ---------------------------------------------------------------- render
const [specPath, cfgPath, rowsPath, outPath, w = '1600', h = '900'] = process.argv.slice(2);
if (!specPath || !cfgPath || !rowsPath || !outPath) {
  console.error(
    'usage: node render_local.mjs <spec.json> <config.json> <rows.json> <out.png> [width] [height]'
  );
  process.exit(1);
}

const spec = JSON.parse(readFileSync(specPath, 'utf8'));
spec.width = Number(w);
spec.height = Number(h);
spec.config = JSON.parse(readFileSync(cfgPath, 'utf8'));

const rows = JSON.parse(readFileSync(rowsPath, 'utf8'));
if (!Array.isArray(rows) || rows.length === 0) {
  console.warn('WARNING: rows.json is empty or not an array - the render will be blank.');
}
spec.data = { name: 'dataset', values: rows };

const compiled = vegaLite.compile(spec, { config: spec.config }).spec;
const view = new vega.View(vega.parse(compiled), { renderer: 'none' });
await view.runAsync();
const svg = await view.toSVG();

if (outPath.endsWith('.svg')) {
  writeFileSync(outPath, svg, 'utf8');
} else {
  await sharp(Buffer.from(svg), { density: 96 }).png().toFile(outPath);
}
console.log(`wrote ${outPath} (${spec.width}x${spec.height}, ${rows.length} dataset rows)`);
