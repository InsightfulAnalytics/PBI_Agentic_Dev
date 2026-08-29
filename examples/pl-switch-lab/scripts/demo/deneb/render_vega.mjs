// Offline Vega (not Vega-Lite) -> PNG. The grid specs in this folder are plain Vega, so
// render_local.mjs -- which compiles Vega-Lite first -- rejects them.
//
// Usage: node render_vega.mjs <spec.vg.json> <out.png> [width] [height]
// The spec is expected to carry inline data (the *.preview.vg.json variant).
import { readFileSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";

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
const sharp = (await import(pathToFileURL(req.resolve("sharp")).href)).default;

// Deneb injects these at render time; offline they only need to return something plausible.
const PALETTE = ["#118DFF", "#12239E", "#E66C37", "#6B007B", "#E044A7", "#744EC2", "#D9B300", "#D64550"];
const SENTIMENT = { min: "#FD625E", middle: "#F2C80F", max: "#01B8AA", negative: "#FD625E",
                    positive: "#01B8AA", neutral: "#F2C80F", bad: "#FD625E", good: "#01B8AA" };
vega.expressionFunction("pbiColor", (i) =>
  typeof i === "string" ? SENTIMENT[i] ?? PALETTE[0] : PALETTE[(Number(i) || 0) % PALETTE.length]);
vega.expressionFunction("pbiFormat", (v) => String(v));
vega.expressionFunction("pbiPatternSVG", () => "");

const [specPath, outPath, w, h] = process.argv.slice(2);
if (!specPath || !outPath) {
  console.error("usage: node render_vega.mjs <spec.vg.json> <out.png> [width] [height]");
  process.exit(1);
}
const spec = JSON.parse(readFileSync(specPath, "utf8"));
if (w) spec.width = Number(w);
if (h) spec.height = Number(h);

const view = new vega.View(vega.parse(spec), { renderer: "none" });
await view.runAsync();
const svg = await view.toSVG();
if (outPath.endsWith(".svg")) writeFileSync(outPath, svg, "utf8");
else await sharp(Buffer.from(svg), { density: 96 }).png().toFile(outPath);
console.log(`wrote ${outPath} (${spec.width}x${spec.height})`);
