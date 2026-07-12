// Render a Vega or Vega-Lite spec to PNG/SVG without Power BI (verify Deneb specs offline).
// Deps resolve against this folder's node_modules — run from anywhere:
//   node "${CLAUDE_PLUGIN_ROOT}/skills/deneb-pbir/renderer/render.mjs" spec.json out.png \
//        [--data rows.json] [--data-name dataset] [--scale N] [--provider vega|vegaLite]
// Deneb specs get their data from Power BI at runtime; pass --data with sample rows
// (JSON array of objects) to fill the named dataset (default name: "dataset").
// --scale alone controls PNG size (spec pixels x scale). --provider overrides grammar
// detection when the spec has no $schema (Deneb's provider property is authoritative).
import { readFileSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import * as vega from 'vega';
import { compile } from 'vega-lite';
import sharp from 'sharp';

const VALUE_FLAGS = new Set(['data', 'data-name', 'scale', 'provider']);
const positional = [];
const opts = {};
const args = process.argv.slice(2);
for (let i = 0; i < args.length; i++) {
  if (args[i].startsWith('--')) {
    const name = args[i].slice(2);
    if (VALUE_FLAGS.has(name)) opts[name] = args[++i];
    else opts[name] = true;
  } else {
    positional.push(args[i]);
  }
}
const [specPath, outPath] = positional;
if (!specPath || !outPath) {
  console.error('Usage: node render.mjs <spec.json> <out.png|out.svg> [--data rows.json] [--data-name dataset] [--scale N] [--provider vega|vegaLite]');
  process.exit(1);
}

const spec = JSON.parse(readFileSync(specPath, 'utf8'));
const looksVL = s => !!(s.mark || s.encoding || s.layer || s.facet || s.hconcat || s.vconcat || s.concat);
const isVL = opts.provider
  ? /lite/i.test(opts.provider)
  : (spec.$schema ? /vega-lite/.test(spec.$schema) : looksVL(spec));
const dataName = opts['data-name'] ?? 'dataset';
const scale = Number(opts.scale ?? 2);

if (opts.data) {
  const values = JSON.parse(readFileSync(opts.data, 'utf8'));
  if (isVL) {
    spec.data = { name: dataName, values };
  } else {
    spec.data = spec.data ?? [];
    const entry = spec.data.find(d => d.name === dataName);
    if (entry) {
      entry.values = values;
      delete entry.url;
    } else {
      spec.data.unshift({ name: dataName, values });
    }
  }
}

const vgSpec = isVL ? compile(spec).spec : spec;
const view = new vega.View(vega.parse(vgSpec), { renderer: 'none' });
const svg = await view.toSVG(scale);
await view.finalize();

if (outPath.endsWith('.svg')) {
  writeFileSync(outPath, svg);
} else {
  await sharp(Buffer.from(svg)).png().toFile(outPath);  // default density: PNG matches the scaled SVG size
}
console.log(JSON.stringify({ out: resolve(outPath), compiled: isVL ? 'vega-lite' : 'vega' }));
