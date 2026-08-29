// Local Vega-Lite -> PNG renderer that stubs Deneb's injected runtime.
//
// The shared plugin renderer (custom-visuals/skills/deneb-pbir/renderer/render.mjs) throws
// "Unrecognized function: pbiColor" on any spec that uses Deneb's theme helpers, which makes
// a perfectly valid spec look broken offline. This wrapper registers the same stubs
// verify_spec.mjs uses, then renders.
//
// Also injects width/height, which the shipped spec deliberately omits (Deneb sizes from the
// container via autosize:fit; explicit dimensions there produce inner scrollbars).
//
// Usage: node render_local.mjs <spec.json> <config.json> <rows.json> <out.png> [w] [h]
import { readFileSync, writeFileSync } from 'node:fs';
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
const sharp = (await import(pathToFileURL(require.resolve('sharp')).href)).default;

const PBI_PALETTE = ['#118DFF', '#12239E', '#E66C37', '#6B007B', '#E044A7',
                     '#744EC2', '#D9B300', '#D64550'];
const SENTIMENT = { min: '#FD625E', middle: '#F2C80F', max: '#01B8AA',
                    negative: '#FD625E', positive: '#01B8AA', neutral: '#F2C80F',
                    bad: '#FD625E', good: '#01B8AA' };
vega.expressionFunction('pbiColor', (i) =>
  typeof i === 'string'
    ? (SENTIMENT[i] ?? PBI_PALETTE[0])
    : PBI_PALETTE[(Number(i) || 0) % PBI_PALETTE.length]);
vega.expressionFunction('pbiFormat', (v) => String(v));
vega.expressionFunction('pbiPatternSVG', () => '');

const [specPath, cfgPath, rowsPath, outPath, w = '1860', h = '520'] = process.argv.slice(2);

const spec = JSON.parse(readFileSync(specPath, 'utf8'));
spec.width = Number(w);
spec.height = Number(h);
spec.config = JSON.parse(readFileSync(cfgPath, 'utf8'));
spec.data = { name: 'dataset', values: JSON.parse(readFileSync(rowsPath, 'utf8')) };

const compiled = vegaLite.compile(spec, { config: spec.config }).spec;
const view = new vega.View(vega.parse(compiled), { renderer: 'none' });
await view.runAsync();
const svg = await view.toSVG();
await sharp(Buffer.from(svg), { density: 96 }).png().toFile(outPath);
console.log(`wrote ${outPath}`);
