#!/usr/bin/env node
// Format Power Query M with Microsoft's powerquery-formatter, the formatter behind the
// VS Code Power Query extension (https://github.com/microsoft/powerquery-formatter), in the
// house layout: 60-character lines, every `let` one binding per line, comments on their own line.
//
//   node format_m.js [--check] [--width N] <path>...   .tmdl, .pq, .m, .pqm files or folders
//   node format_m.js [--width N] -                     M on stdin, formatted M on stdout
//
// In a .tmdl file it formats the multi-line M blocks only: `expression <name> =` shared
// expressions, `source =` under an M partition, and `sourceExpression =` / `pollingExpression =`
// under a refreshPolicy. One-line parameters, DAX and text literals spanning lines are left alone,
// and ``` fences stay. Exit codes: 0 done, 1 --check found unformatted M, 2 an expression failed
// to parse (that block is left as is).

const fs = require("fs");
const path = require("path");

// The formatter estimates an `if` 4 characters short, a `let` 2 short, and a binary operation
// with its operator's length in place of the two spaces around it. An expression just past the
// width then stays on one line and a call inside it breaks instead. Load its length module with
// those counts corrected, before the formatter itself.
function loadCorrectedLinearLength(internal) {
    const Module = require("module");
    const file = require.resolve(`${internal}/passes/utils/linearLength`);
    const source = fs.readFileSync(file, "utf8");
    const corrected = source
        .replace("sumLinearLengths(state, trace.id, 1, node.ifConstant", "sumLinearLengths(state, trace.id, 5, node.ifConstant")
        .replace("sumLinearLengths(state, trace.id, 1, node.letConstant", "sumLinearLengths(state, trace.id, 3, node.letConstant")
        .replace(
            "sumLinearLengths(state, correlationId, node.operatorConstant.constantKind.length, node.left",
            "sumLinearLengths(state, correlationId, 2, node.left",
        );
    if (corrected === source) return;
    const loaded = new Module(file, module);
    loaded.filename = file;
    loaded.paths = Module._nodeModulePaths(path.dirname(file));
    loaded._compile(corrected, file);
    loaded.loaded = true;
    require.cache[file] = loaded;
}

let F;
let PQP;
let preProcess;
let themes;
try {
    const internal = "@microsoft/powerquery-formatter/lib/powerquery-formatter";
    loadCorrectedLinearLength(internal);
    F = require("@microsoft/powerquery-formatter");
    PQP = require("@microsoft/powerquery-parser");
    preProcess = require(`${internal}/passes/preProcessParameter`);
    themes = { ...require(`${internal}/themes`), ...require(`${internal}/themes/constants`) };
} catch {
    console.error(`powerquery-formatter is not installed. Run once: ( cd "${__dirname}" && npm install )`);
    process.exit(2);
}

const M_EXTENSIONS = new Set([".pq", ".m", ".pqm"]);
const DEFAULT_WIDTH = 60;
const BOM = String.fromCharCode(0xfeff);

// House layout on top of the formatter. A `let` always puts one binding per line and `in` on its
// own line, however short, and so does everything that encloses a `let`. A record breaks across
// lines only when it is too long (or holds another record), never because its source did, so the
// layout depends on the code alone. The formatter has no settings for either, so the pass that
// sets forceBlockMode is wrapped. package.json pins the formatter, so the internal path holds.
const tryPreProcessParameter = preProcess.tryPreProcessParameter;
preProcess.tryPreProcessParameter = async (ast, nodeIdMapCollection, ...rest) => {
    const result = await tryPreProcessParameter(ast, nodeIdMapCollection, ...rest);
    if (result.kind === PQP.ResultKind.Ok) {
        unforceSourceLayoutRecords(nodeIdMapCollection, result.value.parametersMap);
        forceLetBlocks(nodeIdMapCollection, result.value.parametersMap);
    }
    return result;
};

// A call or parameter list that has to break puts one item per line, never several packed onto
// one continuation line. A record argument stays on one line when it fits, as a list does,
// instead of breaking whenever the call around it breaks. A `try` that breaks starts its
// `otherwise` or `catch` on a line of its own, rather than leaving `x otherwise y` under `try`.
const { NodeKind } = PQP.Language.Ast;
themes.SyncThemeRegistry.defaultInstance.setTheme({
    name: "house",
    settings: [
        ...themes.defaultTheme.settings,
        {
            scope: [`${NodeKind.InvokeExpression}> ${NodeKind.ArrayWrapper}`, `${NodeKind.ParameterList}> ${NodeKind.ArrayWrapper}`],
            parameters: { ignoreInline: true },
        },
        {
            scope: [`${NodeKind.Csv}> ${NodeKind.RecordExpression}`, `${NodeKind.Csv}> ${NodeKind.RecordLiteral}`],
            parameters: { inheritParentMode: false },
        },
        {
            scope: [
                `${NodeKind.ErrorHandlingExpression}> ${NodeKind.OtherwiseExpression}`,
                `${NodeKind.ErrorHandlingExpression}> ${NodeKind.CatchExpression}`,
            ],
            parameters: { inheritParentMode: true },
        },
        {
            scope: ["constant.language.catch"],
            parameters: { leftPadding: true, rightPadding: true, blockCloser: "L" },
        },
    ],
});

function unforceSourceLayoutRecords(collection, parameters) {
    for (const kind of [NodeKind.RecordExpression, NodeKind.RecordLiteral]) {
        for (const id of collection.idsByNodeKind.get(kind) || []) {
            const node = collection.astNodeById.get(id);
            const holdsRecord = node.content.elements.some((csv) => csv.node.value.kind === NodeKind.RecordExpression);
            if (holdsRecord) continue;
            for (const target of [node, node.content]) {
                const parameter = parameters.get(target.id);
                if (parameter && parameter.forceBlockMode) parameters.set(target.id, { ...parameter, forceBlockMode: false });
            }
        }
    }
}

function forceLetBlocks(collection, parameters) {
    const force = (id) => parameters.set(id, { ...(parameters.get(id) || {}), forceBlockMode: true });
    const letIds = collection.idsByNodeKind.get(NodeKind.LetExpression) || [];
    for (const id of letIds) {
        force(collection.astNodeById.get(id).variableList.id);
        for (let node = collection.astNodeById.get(id); node; ) {
            force(node.id);
            node = PQP.Parser.NodeIdMapUtils.parentAst(collection, node.id);
        }
    }
}

function parseArgs(argv) {
    const opts = { check: false, width: DEFAULT_WIDTH, paths: [] };
    for (let i = 0; i < argv.length; i++) {
        const arg = argv[i];
        if (arg === "--check") opts.check = true;
        else if (arg === "--width") opts.width = Number(argv[++i]);
        else if (arg === "-h" || arg === "--help") {
            console.log(fs.readFileSync(__filename, "utf8").split("\n").slice(1, 13).join("\n"));
            process.exit(0);
        } else opts.paths.push(arg);
    }
    if (!opts.paths.length || !(opts.width > 0)) {
        console.error("usage: node format_m.js [--check] [--width N] <path>... | -");
        process.exit(2);
    }
    return opts;
}

async function formatM(text, width) {
    const settings = { ...F.DefaultSettings, maxWidth: width, newlineLiteral: "\n" };
    const result = await F.tryFormat(settings, liftTrailingComments(text.replace(/\r\n/g, "\n")));
    if (result.kind !== "Ok") return { error: (result.error && result.error.message) || String(result.error) };
    return { text: result.value.replace(/\s+$/, "") };
}

// The formatter attaches a comment to the token after it, so a comment at the end of a line would
// drop onto the next line and read as a note on the next step. Lift each one onto its own line
// above the code it follows, which keeps it with that code.
function liftTrailingComments(text) {
    const lexed = PQP.TaskUtils.tryLex(PQP.DefaultSettings, text);
    if (!PQP.TaskUtils.isOk(lexed)) return text;
    const { tokens, comments } = lexed.lexerSnapshot;
    const trailing = comments.filter(
        (c) =>
            c.kind === "Line" &&
            tokens.some(
                (t) =>
                    t.positionStart.lineNumber === c.positionStart.lineNumber &&
                    t.positionStart.codeUnit < c.positionStart.codeUnit,
            ),
    );
    const lines = text.split("\n");
    for (const c of trailing.reverse()) {
        const n = c.positionStart.lineNumber;
        const indent = lines[n].match(/^\s*/)[0];
        lines.splice(n, 1, indent + c.data, lines[n].slice(0, c.positionStart.lineCodeUnit).trimEnd());
    }
    return lines.join("\n");
}

const tabsOf = (line) => line.match(/^\t*/)[0].length;
const isBlank = (line) => line.trim() === "";

// True when a text literal spans lines. TMDL re-indents every line of an unfenced block, which
// would change such a literal's value, so blocks holding one are left alone.
function hasMultilineText(m) {
    let inText = false;
    for (let i = 0; i < m.length; i++) {
        const c = m[i];
        if (inText) {
            if (c === '"' && m[i + 1] === '"') i++;
            else if (c === '"') inText = false;
            else if (c === "\n") return true;
        } else if (c === "/" && m[i + 1] === "/") {
            const eol = m.indexOf("\n", i);
            i = eol < 0 ? m.length : eol;
        } else if (c === "/" && m[i + 1] === "*") {
            const close = m.indexOf("*/", i + 2);
            i = close < 0 ? m.length : close + 1;
        } else if (c === '"') inText = true;
    }
    return false;
}

// Locate the M blocks in a TMDL file. Lines start..end-1 hold the M. A fenced block (`= ````
// ... ```) is read verbatim by TMDL; its fences stay where they are and only the M between moves.
function findTmdlBlocks(lines) {
    const blocks = [];
    const lastAtDepth = [];
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        if (isBlank(line)) continue;
        const depth = tabsOf(line);
        lastAtDepth[depth] = line.trim();
        lastAtDepth.length = depth + 1;

        let name = null;
        let propertyDepth = depth;
        const prop = line.match(/^\t*(source|sourceExpression|pollingExpression)\s*=\s*(```)?\s*$/);
        const expr = depth === 0 && line.match(/^(expression\s+.+?)\s*=\s*(```)?\s*$/);
        if (expr) {
            name = expr[1];
            propertyDepth = 1;
        } else if (prop && depth > 0) {
            const parent = lastAtDepth[depth - 1] || "";
            const isMPartition = prop[1] === "source" && /^partition\s.+=\s*m$/.test(parent);
            const isPolicy = prop[1] !== "source" && parent === "refreshPolicy";
            if (isMPartition || isPolicy) name = `${parent.replace(/\s*=\s*m$/, "")} ${prop[1]}`;
        }
        if (!name) continue;
        const fenced = /```\s*$/.test(line);

        if (fenced) {
            let close = i + 1;
            while (close < lines.length && lines[close].trim() !== "```") close++;
            if (close >= lines.length) continue;
            const content = lines.slice(i + 1, close).filter((l) => !isBlank(l));
            const tabs = content.length ? Math.min(...content.map(tabsOf)) : 0;
            blocks.push({ name, start: i + 1, end: close, tabs });
            i = close;
            continue;
        }

        let first = i + 1;
        while (first < lines.length && isBlank(lines[first])) first++;
        if (first >= lines.length) continue;
        const tabs = tabsOf(lines[first]);
        if (tabs <= propertyDepth) continue;

        let end = first;
        while (end < lines.length && (isBlank(lines[end]) || tabsOf(lines[end]) >= tabs)) end++;
        const ragged = end < lines.length && tabsOf(lines[end]) > propertyDepth;
        while (end > first && isBlank(lines[end - 1])) end--;
        blocks.push({ name, start: first, end, tabs, ragged });
        i = end - 1;
    }
    return blocks;
}

async function formatTmdl(text, width) {
    const newline = text.includes("\r\n") ? "\r\n" : "\n";
    const lines = text.split(/\r?\n/);
    const report = { changed: [], errors: [], skipped: [], total: 0 };
    const blocks = findTmdlBlocks(lines);
    // Replace from the bottom so earlier line numbers stay valid.
    for (const block of blocks.reverse()) {
        report.total++;
        if (block.ragged) {
            report.skipped.push(`${block.name} (irregular indentation)`);
            continue;
        }
        const original = lines.slice(block.start, block.end);
        const body = original.map((l) => (isBlank(l) ? "" : l.slice(block.tabs)));
        const formatted = await formatM(body.join("\n"), width);
        if (formatted.error) {
            report.errors.push(`${block.name}: ${formatted.error}`);
            continue;
        }
        if (hasMultilineText(formatted.text)) {
            report.skipped.push(`${block.name} (multi-line text literal)`);
            continue;
        }
        const prefix = "\t".repeat(block.tabs);
        const out = formatted.text.split("\n").map((l) => (l.trim() ? prefix + l.trimEnd() : ""));
        if (out.join("\n") === original.join("\n")) continue;
        report.changed.push(block.name);
        lines.splice(block.start, block.end - block.start, ...out);
    }
    report.changed.reverse();
    return { text: lines.join(newline), report };
}

async function formatFile(file, opts) {
    const raw = fs.readFileSync(file, "utf8");
    const bom = raw.startsWith(BOM) ? BOM : "";
    const original = raw.slice(bom.length);
    let result;
    if (path.extname(file).toLowerCase() === ".tmdl") {
        result = await formatTmdl(original, opts.width);
    } else {
        const newline = original.includes("\r\n") ? "\r\n" : "\n";
        const formatted = await formatM(original, opts.width);
        const report = { changed: [], errors: [], skipped: [], total: 1 };
        if (formatted.error) report.errors.push(formatted.error);
        const text = formatted.error ? original : formatted.text.split("\n").join(newline) + newline;
        if (!formatted.error && text !== original) report.changed.push("expression");
        result = { text, report };
    }
    const { report } = result;
    if (!opts.check && result.text !== original) fs.writeFileSync(file, bom + result.text, "utf8");
    const verb = opts.check ? "unformatted" : "formatted";
    const parts = [`${report.changed.length} of ${report.total} M block(s) ${verb}`];
    if (report.changed.length && report.total > 1) parts.push(report.changed.join(", "));
    if (report.total) console.log(`${file}: ${parts.join(": ")}`);
    for (const s of report.skipped) console.log(`${file}: skipped ${s}`);
    for (const e of report.errors) console.error(`${file}: PARSE ERROR, left as is: ${e}`);
    return report;
}

function collectFiles(target, out) {
    const stat = fs.statSync(target);
    if (stat.isFile()) {
        out.push(target);
        return;
    }
    for (const entry of fs.readdirSync(target, { withFileTypes: true })) {
        if (entry.name === "node_modules" || entry.name.startsWith(".")) continue;
        const full = path.join(target, entry.name);
        const ext = path.extname(entry.name).toLowerCase();
        if (entry.isDirectory()) collectFiles(full, out);
        else if (ext === ".tmdl" || M_EXTENSIONS.has(ext)) out.push(full);
    }
}

async function main() {
    const opts = parseArgs(process.argv.slice(2));
    if (opts.paths.length === 1 && opts.paths[0] === "-") {
        const formatted = await formatM(fs.readFileSync(0, "utf8"), opts.width);
        if (formatted.error) {
            console.error(`PARSE ERROR: ${formatted.error}`);
            process.exit(2);
        }
        process.stdout.write(formatted.text + "\n");
        return;
    }
    const files = [];
    for (const p of opts.paths) collectFiles(p, files);
    let changed = 0;
    let errors = 0;
    for (const file of files) {
        const report = await formatFile(file, opts);
        changed += report.changed.length;
        errors += report.errors.length;
    }
    if (errors) process.exit(2);
    if (opts.check && changed) process.exit(1);
}

main().catch((err) => {
    console.error(err.stack || String(err));
    process.exit(2);
});
