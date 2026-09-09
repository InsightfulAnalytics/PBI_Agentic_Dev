// Render a Vega or Vega-Lite spec to PNG/SVG without Power BI (verify Deneb specs offline).
// Deps resolve against this folder's node_modules, so run it from anywhere:
//   node "${CLAUDE_PLUGIN_ROOT}/skills/deneb-pbir/renderer/render.mjs" spec.json out.png \
//        [--data rows.json] [--data-name dataset] [--scale N] [--provider vega|vegaLite] \
//        [--width 600] [--height 400] [--deneb 1.9|2.0] [--strict]   (--strict is 2.0 only)
// Deneb specs get their data from Power BI at runtime; pass --data with sample rows
// (JSON array of objects) to fill the named dataset (default name: "dataset").
// --scale alone controls PNG size (spec pixels x scale). --provider overrides grammar
// detection when the spec has no $schema (Deneb's provider property is authoritative).
// --width / --height are the simulated Deneb container (default 600 x 400): they seed the
// denebContainer / pbiContainer* signals and the size of specs that have no width/height.
// --deneb 1.9 fails fast (exit 2) when the spec references denebContainer, which 1.9.x does
// not define; --deneb 2.0 warns about legacy pbiContainer* names and rewrites them over the
// raw text exactly as Deneb 2.0 does at parse time (exit 0). --strict is a 2.0-readiness
// gate for CI: it turns any legacy reference into exit 2, so it is rejected with a usage
// error (exit 1) alongside --deneb 1.9, whose whole point is those legacy names.
// The Deneb runtime shims below (container signals, pbi*
// expression functions, pbiColor* schemes) exist so a real spec parses and draws; they are
// not Power BI's formatter, theme or cross-filter host. JSONC comments in the spec are
// stripped before parsing, as Deneb does. See SKILL.md.
import { readFileSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import * as vega from 'vega';
import { compile, version as vegaLiteVersion } from 'vega-lite';
import sharp from 'sharp';

// ---------------------------------------------------------------- CLI
const VALUE_FLAGS = new Set(['data', 'data-name', 'scale', 'provider', 'width', 'height', 'deneb']);
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
const USAGE = 'Usage: node render.mjs <spec.json> <out.png|out.svg> [--data rows.json] [--data-name dataset] ' +
  '[--scale N] [--provider vega|vegaLite] [--width 600] [--height 400] [--deneb 1.9|2.0] ' +
  '[--strict (2.0-readiness gate; not valid with --deneb 1.9)]';
if (opts.help === true) {
  console.log(USAGE);
  process.exit(0);
}
if (!specPath || !outPath) {
  console.error(USAGE);
  process.exit(1);
}
const width = Number(opts.width ?? 600);
const height = Number(opts.height ?? 400);
if (!(width > 0) || !(height > 0)) {
  console.error(`--width and --height must be positive numbers (got ${opts.width}, ${opts.height})\n${USAGE}`);
  process.exit(1);
}
const deneb = opts.deneb;
if (deneb !== undefined && deneb !== '1.9' && deneb !== '2.0') {
  console.error(`--deneb must be 1.9 or 2.0 (got ${deneb})\n${USAGE}`);
  process.exit(1);
}
const strict = opts.strict === true;
if (strict && deneb === '1.9') {
  console.error(
    `--strict is a 2.0-readiness gate: it fails the spec on any legacy pbiContainer* reference, ` +
    `which is exactly what a --deneb 1.9 target needs. Use --deneb 1.9 on its own to check a ` +
    `1.9 spec, or --strict (with or without --deneb 2.0) to gate a spec on 2.0 readiness.\n${USAGE}`
  );
  process.exit(1);
}

// ---------------------------------------------------------------- Deneb container signals
// Same word-boundary regexes and the same replacement order as Deneb 2.0
// (deneb-src packages/vega-runtime/src/lib/signals/migration.ts). Text scope: a legacy
// name inside a plain string literal (a title, a tooltip) is counted and rewritten too,
// exactly as Deneb does. deneb_spec.py audit and migrate use the same three patterns.
const LEGACY_TO_MODERN = [
  ['pbiContainerWidth', 'denebContainer.width'],
  ['pbiContainerHeight', 'denebContainer.height'],
  ['pbiContainer', 'denebContainer'],
];
const MODERN = 'denebContainer';
const wb = (name) => new RegExp(`\\b${name}\\b`, 'g');
const countRefs = (text, name) => (text.match(wb(name)) ?? []).length;
const rewriteLegacy = (text) => LEGACY_TO_MODERN.reduce((t, [from, to]) => t.replace(wb(from), to), text);

let specText = readFileSync(specPath, 'utf8');
const legacyRefs = LEGACY_TO_MODERN.reduce((n, [name]) => n + countRefs(specText, name), 0);
const modernRefs = countRefs(specText, MODERN);
const notes = [];

if (strict && legacyRefs > 0) {
  console.error(
    `--strict: ${legacyRefs} legacy signal reference(s) (pbiContainer, pbiContainerWidth, pbiContainerHeight) ` +
    `found; Deneb 2.0 deprecates them (removal target 3.0). Flip the file with: ` +
    `deneb_spec.py migrate <file> --signals modern`
  );
  process.exit(2);
}
if (deneb === '1.9' && modernRefs > 0) {
  console.error(
    `denebContainer is not defined in Deneb 1.9.x (${modernRefs} reference(s) found); Vega throws ` +
    `'Unrecognized signal name: "denebContainer"'. Use pbiContainerWidth / pbiContainerHeight for a ` +
    `1.9 target, or flip the spec with: deneb_spec.py migrate <file> --signals legacy`
  );
  process.exit(2);
}
if (deneb === '2.0' && legacyRefs > 0) {
  // Mirror Deneb 2.0: rewrite over the raw text, warn once, carry on.
  console.warn(
    `[Deneb Migration] Deprecated signal 'pbiContainer' detected (${legacyRefs} reference(s)). ` +
    `Deneb 2.0 rewrites these to 'denebContainer' at parse time (removal target 3.0); ` +
    `flip the file with: deneb_spec.py migrate <file> --signals modern`
  );
  specText = rewriteLegacy(specText);
  notes.push(`rewrote ${legacyRefs} legacy signal reference(s) to denebContainer (Deneb 2.0 behaviour)`);
}

// Deneb accepts JSONC in the spec editor and blanks the comments (outside strings, offsets
// kept) before JSON.parse (deneb-src packages/utils/src/lib/jsonc.ts). Same here, so the
// upstream examples that carry // comments render.
function stripJsoncComments(text) {
  let out = '';
  let i = 0;
  let inStr = false;
  while (i < text.length) {
    const ch = text[i];
    if (inStr) {
      out += ch;
      if (ch === '\\' && i + 1 < text.length) { out += text[i + 1]; i += 2; continue; }
      if (ch === '"') inStr = false;
      i++;
    } else if (ch === '"') {
      inStr = true; out += ch; i++;
    } else if (ch === '/' && text[i + 1] === '/') {
      let j = text.indexOf('\n', i); if (j < 0) j = text.length;
      out += ' '.repeat(j - i); i = j;
    } else if (ch === '/' && text[i + 1] === '*') {
      let j = text.indexOf('*/', i + 2); j = j < 0 ? text.length : j + 2;
      out += text.slice(i, j).replace(/[^\r\n]/g, ' '); i = j;
    } else {
      out += ch; i++;
    }
  }
  return out;
}
const parseText = stripJsoncComments(specText);
if (parseText !== specText) notes.push('stripped JSONC comments before parsing (Deneb does the same)');
const spec = JSON.parse(parseText);
const looksVL = (s) => !!(s.mark || s.encoding || s.layer || s.facet || s.hconcat || s.vconcat || s.concat);
const isVL = opts.provider
  ? /lite/i.test(opts.provider)
  : (spec.$schema ? /vega-lite/.test(spec.$schema) : looksVL(spec));
const dataName = opts['data-name'] ?? 'dataset';
const scale = Number(opts.scale ?? 2);

// Deneb seeds the signal at compile time with scroll* = 0 (getDenebContainerSignalFromDimensions
// only passes width/height) and its container observer then overwrites scrollWidth/scrollHeight
// with measured values. There is no observer offline, so scrollWidth/scrollHeight are seeded
// with the container size (a spec that positions against scrollHeight draws inside the
// container instead of at 0). scrollTop and scrollLeft stay 0 like Deneb.
const containerValue = (w, h) => ({ height: h, width: w, scrollHeight: h, scrollWidth: w, scrollTop: 0, scrollLeft: 0 });

// Inject only the container signals the spec references and does not define itself.
// Vega: prepend to `signals`. Vega-Lite: prepend to top-level `params` (a param with a
// `value` compiles to a Vega signal, which is how Deneb injects it: patch-vega-lite.ts).
function injectContainerSignals(target, vl, text, w, h) {
  const key = vl ? 'params' : 'signals';
  const list = Array.isArray(target[key]) ? target[key] : [];
  const defined = new Set(list.map((e) => e && e.name));
  const candidates = [
    [MODERN, containerValue(w, h)],
    ['pbiContainer', containerValue(w, h)],
    ['pbiContainerWidth', w],
    ['pbiContainerHeight', h],
  ];
  const added = candidates
    .filter(([name]) => wb(name).test(text) && !defined.has(name))
    .map(([name, value]) => ({ name, value }));
  if (added.length) target[key] = [...added, ...list];
  return added.map((a) => a.name);
}

// Mirror Deneb's responsive sizing (patch-vega.ts / patch-vega-lite.ts):
// Vega: width/height -> denebContainer.* when missing and no user signal of that name.
// Vega-Lite: width/height -> 'container' for standard layouts; the compiled
// containerSize() lookups are pinned to --width/--height after compile (see below).
function applyResponsiveSizing(target, vl, w, h) {
  const set = [];
  if (vl) {
    if (target.concat || target.hconcat || target.vconcat || target.facet) return set;
    if (target.width === undefined) { target.width = 'container'; set.push('width'); }
    if (target.height === undefined) { target.height = 'container'; set.push('height'); }
    return set;
  }
  const has = (n) => (target.signals ?? []).some((s) => s.name === n);
  if (target.width == null && !has('width')) { target.width = { signal: `${MODERN}.width` }; set.push('width'); }
  if (target.height == null && !has('height')) { target.height = { signal: `${MODERN}.height` }; set.push('height'); }
  if (set.length && !has(MODERN)) {
    target.signals = [{ name: MODERN, value: containerValue(w, h) }, ...(target.signals ?? [])];
  }
  return set;
}

const injected = injectContainerSignals(spec, isVL, specText, width, height);
const sized = applyResponsiveSizing(spec, isVL, width, height);

// ---------------------------------------------------------------- data
if (opts.data) {
  const values = JSON.parse(readFileSync(opts.data, 'utf8'));
  if (isVL) {
    spec.data = { name: dataName, values };
  } else {
    spec.data = spec.data ?? [];
    const entry = spec.data.find((d) => d.name === dataName);
    if (entry) {
      entry.values = values;
      delete entry.url;
    } else {
      spec.data.unshift({ name: dataName, values });
    }
  }
}

// ---------------------------------------------------------------- Deneb expression functions and schemes
// Offline stand-ins so a spec parses and draws. They are NOT Power BI's formatter or theme:
// pbiFormat is a plain approximation of a Power BI format string, pbiPatternSVG returns the
// foreground colour (there are no SVG pattern defs offline), cross-filter calls are no-ops.

// Deneb's own non-Power BI fallback palette: POWERBI_THEME_DEFAULT.colors[0..23]
// (deneb-src packages/powerbi-compat/src/lib/theme/shim.ts).
const PBI_PALETTE = [
  '#118DFF', '#12239E', '#E66C37', '#6B007B', '#E044A7', '#744EC2', '#D9B300', '#D64550',
  '#197278', '#1AAB40', '#15C6F4', '#4092FF', '#FFA058', '#BE5DC9', '#F472D0', '#B5A1FF',
  '#C4A200', '#FF8080', '#00DBBC', '#5BD667', '#0091D5', '#4668C5', '#FF6300', '#99008A',
];
// The eight names getNamedColors registers (scheme/powerbi.ts lines 194-203); no aliases,
// because any other name (minimum, maximum, center, ...) falls through to parseInt(name) || 0
// in Deneb (expressions/color.ts lines 8-13), i.e. theme colour 0, and the same happens here.
// Deneb's default shim has no named entries at all, so in Deneb itself outside Power BI every
// name resolves to colours[0]; the offline values below are the Power BI default theme's
// sentiment and divergent colours so a spec using them draws with plausible colours.
const PBI_NAMED = {
  min: '#DEEFFF',
  middle: '#D9B300',
  max: '#118DFF',
  negative: '#D64554', bad: '#D64554',
  positive: '#1AAB40', good: '#1AAB40',
  neutral: '#D9B300',
};
// Same algorithm as Deneb's shadeColor (deneb-src packages/utils/src/lib/color.ts):
// negative percent darkens toward black, positive lightens toward white.
const shadeColor = (color, percent) => {
  const f = parseInt(color.slice(1), 16);
  const t = percent < 0 ? 0 : 255;
  const p = percent < 0 ? percent * -1 : percent;
  const R = f >> 16;
  const G = (f >> 8) & 0x00ff;
  const B = f & 0x0000ff;
  return `#${(0x1000000 + (Math.round((t - R) * p) + R) * 0x10000 + (Math.round((t - G) * p) + G) * 0x100 + (Math.round((t - B) * p) + B)).toString(16).slice(1)}`;
};
const pbiColor = (value, shadePercent = 0) =>
  shadeColor(PBI_NAMED[`${value}`] ?? PBI_PALETTE[parseInt(`${value}`) || 0] ?? '#000000', shadePercent);

// Best-effort Power BI format string: named formats, prefix/suffix literals, %, decimals,
// grouping and trailing scaling commas. Ignores cultureSelector, date formats and any
// section after the first ';'. Never throws: a value it cannot handle comes back as text.
const group = (s) => s.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
function pbiFormat(value, format, options = {}) {
  try {
    if (format && typeof format === 'object') { options = format; format = options.format ?? null; }
    if (value == null) return '';
    if (value instanceof Date) return value.toISOString().slice(0, 10);
    if (typeof value !== 'number') return String(value);
    let fmt = typeof format === 'string' ? format.split(';')[0].replace(/"/g, '') : '';
    const named = {
      'general number': (v) => String(v),
      'currency': (v) => '$' + group(v.toFixed(2)),
      'fixed': (v) => v.toFixed(2),
      'standard': (v) => group(v.toFixed(2)),
      'percent': (v) => group((v * 100).toFixed(2)) + '%',
      'scientific': (v) => v.toExponential(2),
    };
    const lower = fmt.trim().toLowerCase();
    if (named[lower]) return named[lower](value);
    if (!fmt) return group(String(Math.round(value * 100) / 100));
    const m = fmt.match(/^([^#0,.%]*)([#0,.]*%?[#0,.]*)(.*)$/);
    const prefix = m ? m[1] : '';
    const core = m ? m[2] : fmt;
    const suffix = m ? m[3] : '';
    const percent = core.includes('%');
    const scaling = (core.replace('%', '').match(/,+(?=\.|$)/) ?? [''])[0].length;
    const decimals = (core.split('.')[1] ?? '').replace(/[^0#]/g, '').length;
    const grouped = /[#0],[#0]/.test(core);
    let v = percent ? value * 100 : value;
    v = v / 10 ** (3 * scaling);
    let s = v.toFixed(decimals);
    if (grouped) s = group(s);
    return `${prefix}${s}${percent ? '%' : ''}${suffix}`;
  } catch {
    return String(value);
  }
}
function pbiFormatAutoUnit(value, format, options = {}) {
  try {
    if (typeof value !== 'number') return pbiFormat(value, format, options);
    const abs = Math.abs(value);
    const [div, unit] = abs >= 1e12 ? [1e12, 'T'] : abs >= 1e9 ? [1e9, 'bn'] : abs >= 1e6 ? [1e6, 'M'] : abs >= 1e3 ? [1e3, 'K'] : [1, ''];
    const prefix = (typeof format === 'string' && format.match(/^[^#0,.%]*/)?.[0]) || '';
    return `${prefix}${(value / div).toFixed(div === 1 ? 0 : 2)}${unit}`;
  } catch {
    return String(value);
  }
}
const pbiPatternSVG = (id, fg = '#000000') => fg ?? '#000000';
const pbiCrossFilterApply = () => ({});
const pbiCrossFilterClear = () => undefined;

for (const [name, fn] of [
  ['pbiColor', pbiColor],
  ['pbiFormat', pbiFormat],
  ['pbiFormatAutoUnit', pbiFormatAutoUnit],
  ['pbiPatternSVG', pbiPatternSVG],
  ['pbiCrossFilterApply', pbiCrossFilterApply],
  ['pbiCrossFilterClear', pbiCrossFilterClear],
]) vega.expressionFunction(name, fn);

// Schemes (scheme/powerbi.ts): nominal = palette; ordinal and linear = min -> max ramp;
// divergent = min -> middle -> max ramp. Deneb uses d3 interpolateRgbBasis; vega's own
// interpolateColors (vega-scale) is used here so no extra dependency is needed.
vega.scheme('pbiColorNominal', PBI_PALETTE);
vega.scheme('pbiColorOrdinal', vega.interpolateColors([PBI_NAMED.min, PBI_NAMED.max], 'rgb'));
vega.scheme('pbiColorLinear', vega.interpolateColors([PBI_NAMED.min, PBI_NAMED.max], 'rgb'));
vega.scheme('pbiColorDivergent', vega.interpolateColors([PBI_NAMED.min, PBI_NAMED.middle, PBI_NAMED.max], 'rgb'));

// ---------------------------------------------------------------- compile and render
let vgSpec;
if (isVL) {
  // Vega-Lite drops `formatType: "pbiFormat"` / "pbiFormatAutoUnit" unless
  // config.customFormatTypes is true (Deneb merges it in patch-config.ts).
  spec.config = { ...(spec.config ?? {}), customFormatTypes: true };
  vgSpec = compile(spec).spec;
  // 'container' sizing compiles to init: "isFinite(containerSize()[0]) ? containerSize()[0] : 200".
  // There is no DOM container offline, so pin those signals to --width/--height.
  for (const s of vgSpec.signals ?? []) {
    if ((s.name === 'width' || s.name === 'height') && typeof s.init === 'string' && s.init.includes('containerSize()')) {
      s.value = s.name === 'width' ? width : height;
      delete s.init;
      delete s.on;
    }
  }
} else {
  vgSpec = spec;
}
const view = new vega.View(vega.parse(vgSpec), { renderer: 'none' });
const svg = await view.toSVG(scale);
await view.finalize();

if (outPath.endsWith('.svg')) {
  writeFileSync(outPath, svg);
} else {
  await sharp(Buffer.from(svg)).png().toFile(outPath);  // default density: PNG matches the scaled SVG size
}
console.log(JSON.stringify({
  out: resolve(outPath),
  compiled: isVL ? 'vega-lite' : 'vega',
  vega: vega.version,
  vegaLite: vegaLiteVersion,
  container: { width, height },
  deneb: deneb ?? null,
  strict,
  injectedSignals: injected,
  responsiveSizing: sized,
  legacySignalReferences: legacyRefs,
  denebContainerReferences: modernRefs,
  notes,
}));
