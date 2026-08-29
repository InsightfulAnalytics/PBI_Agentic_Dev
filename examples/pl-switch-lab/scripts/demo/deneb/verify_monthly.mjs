// Diff every cell of the Monthly P&L Deneb grid against an independent Python recomputation
// (monthly-pl.expected.json, written by gen_monthly_spec.py). Two implementations of the same
// DAX rules; the gate is zero mismatches.
//
// Deps resolve from the deneb-pbir plugin renderer's node_modules, same as render_local.mjs
// beside this file (ESM-only: dynamic import, never require).
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { fileURLToPath, pathToFileURL } from "node:url";
import { dirname, join } from "node:path";

const HERE = dirname(fileURLToPath(import.meta.url));
// The Vega/sharp runtime lives in the deneb-pbir skill's renderer package, whose location
// depends on where the plugin marketplace is installed. Point DENEB_RENDERER_PKG at that
// package.json; there is no sensible default that works on another machine.
if (!process.env.DENEB_RENDERER_PKG) {
  throw new Error(
    "Set DENEB_RENDERER_PKG to the path of " +
    "plugins/custom-visuals/skills/deneb-pbir/renderer/package.json in your plugin checkout."
  );
}
const req = createRequire(pathToFileURL(process.env.DENEB_RENDERER_PKG).href);
const vega = await import(pathToFileURL(req.resolve("vega")).href);

const spec = JSON.parse(readFileSync(join(HERE, "monthly-pl.preview.vg.json"), "utf8"));
const expected = JSON.parse(readFileSync(join(HERE, "monthly-pl.expected.json"), "utf8"));

const view = new vega.View(vega.parse(spec), { renderer: "none" });
await view.runAsync();
const cells = view.data("cells");

const got = new Map(cells.map((c) => [`${c.rowIdx}|${c.colIdx}`, c]));
let bad = 0;
const close = (a, b) =>
  (a == null && b == null) ||
  (a != null && b != null && Math.abs(a - b) <= 1e-9 * Math.max(1, Math.abs(a), Math.abs(b)));

for (const e of expected) {
  const c = got.get(`${e.rowIdx}|${e.colIdx}`);
  if (!c) {
    console.log(`MISSING cell r${e.rowIdx} c${e.colIdx} (${e.key})`);
    bad++;
    continue;
  }
  if (!close(c.value ?? null, e.value ?? null)) {
    console.log(`DIFF ${e.key} r${e.rowIdx} c${e.colIdx}: spec=${c.value} expected=${e.value}`);
    bad++;
  }
}
if (cells.length !== expected.length) {
  console.log(`COUNT spec=${cells.length} expected=${expected.length}`);
  bad++;
}

// Regression guard. If MonthOffset ever stops arriving -- dropped projection, or it goes back
// into the GROUP BY on a model where DATEADD blanks it -- the current month is unknowable and
// YTD/YTG must both come back EMPTY. The failure this catches is the silent one: null coercing
// to 0 so that `Month > curP` is true for every month and YTG renders the full year, which
// looks entirely plausible on the canvas.
{
  const stripped = JSON.parse(JSON.stringify(spec));
  const ds = stripped.data.find((d) => d.name === "dataset");
  ds.values = ds.values.map(({ MonthOffset, ...rest }) => rest);
  const v2 = new vega.View(vega.parse(stripped), { renderer: "none" });
  await v2.runAsync();
  const leaked = v2.data("cells").filter((c) => (c.colIdx === 12 || c.colIdx === 13) && c.value != null);
  if (leaked.length) {
    console.log(
      `GUARD FAIL: ${leaked.length} YTD/YTG cells populated with no MonthOffset` +
        ` (e.g. col ${leaked[0].colIdx} ${leaked[0].key}=${leaked[0].value})`
    );
    bad++;
  } else {
    const fy = v2.data("cells").filter((c) => c.colIdx === 14 && c.value != null).length;
    console.log(`guard ok : no MonthOffset -> YTD/YTG blank, FY still populated (${fy} FY cells)`);
  }
}

// Spot-check the formatter against the DAX rules it reimplements: Fmt.Money thresholds and
// the dynamic percent rule, with negatives in accounting parentheses.
{
  const byKey = (r, c) => got.get(`${r}|${c}`);
  const samples = [
    [1, 0, /^\$[\d,]+\.\dM$/],   // Total Income, Jan  -> $xxx.xM
    [2, 0, /^\$[\d,]+\.\dM$/],   // Total Income LY, Jan
    [5, 0, /^\(\$[\d,]+\.\dM\)$/], // Total Cost of Sales, Jan -> negative, parenthesised
    [13, 0, /^\d+\.\d%$/],       // Gross Margin %, Jan
  ];
  for (const [r, c, re] of samples) {
    const cell = byKey(r, c);
    if (!cell || !re.test(cell.fmtd)) {
      console.log(`FORMAT r${r} c${c}: got ${JSON.stringify(cell && cell.fmtd)}, expected ${re}`);
      bad++;
    }
  }
}

console.log(`BADDIFF ${bad} (cells ${cells.length})`);
process.exit(bad === 0 ? 0 : 1);
