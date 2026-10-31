// Layout and legibility checks for one rendered page of a Fabric App, run in the browser.
// Inject this file with a browser tool's JavaScript call, then:
//   window.__inspect(options)  -> { page, theme, width, issues: [...] } for the page on screen
//   window.__runAll(names)     -> visits each page through its nav button; poll window.__runOut
//   window.__summary()         -> the run's issues grouped by kind, as text
// options: root (the app's root selector, default "#root"), frame (a card's root selector,
// default VisualContainer's "[data-lyra-selection-boundary]"), emptyText (a RegExp for the app's
// empty-state wording, reported when it appears).
window.__inspectOptions = {};
window.__inspect = (options = window.__inspectOptions) => {
    const FRAME = options.frame ?? "[data-lyra-selection-boundary]";
    const root = document.querySelector(options.root ?? "#root") ?? document.body;
    const issues = [];
    const opacityCache = new Map();
    const effectiveOpacity = (el) => {
        if (!el || el.nodeType !== 1) return 1;
        if (opacityCache.has(el)) return opacityCache.get(el);
        const style = getComputedStyle(el);
        let value = style.display === "none" || style.visibility === "hidden" ? 0 : parseFloat(style.opacity || "1");
        if (el instanceof SVGElement) {
            const fo = parseFloat(style.fillOpacity || "1");
            if (el.tagName === "text" && fo < 0.05) value = 0;
        }
        if (value > 0) value *= effectiveOpacity(el.parentElement);
        opacityCache.set(el, value);
        return value;
    };
    const where = (el) => {
        const frame = el.closest(FRAME);
        if (frame) {
            const title = frame.querySelector("h1, h2, h3, h4, [role='heading']")?.textContent.trim() ?? "?";
            const panel = el.closest("section[aria-label]");
            return `card "${title.slice(0, 70)}"` + (panel && frame.contains(panel) ? ` / panel "${panel.getAttribute("aria-label")}"` : "");
        }
        const section = el.closest("section[aria-label], aside, header, nav, main");
        return section ? section.getAttribute("aria-label") || section.tagName.toLowerCase() : el.tagName.toLowerCase();
    };
    const short = (s) => s.trim().replace(/\s+/g, " ").slice(0, 48);

    // colours, read back from a canvas so any CSS colour space comes out as sRGB
    const canvas = document.createElement("canvas");
    canvas.width = canvas.height = 1;
    const ctx = canvas.getContext("2d", { willReadFrequently: true });
    const rgba = (css) => {
        if (!css || css === "none" || css === "transparent") return [0, 0, 0, 0];
        ctx.clearRect(0, 0, 1, 1);
        ctx.fillStyle = "#000";
        ctx.fillStyle = css;
        ctx.fillRect(0, 0, 1, 1);
        const d = ctx.getImageData(0, 0, 1, 1).data;
        return [d[0], d[1], d[2], d[3] / 255];
    };
    const over = (top, bottom) => {
        const a = top[3];
        return [0, 1, 2].map((i) => top[i] * a + bottom[i] * (1 - a)).concat(1);
    };
    const luminance = ([r, g, b]) => {
        const f = (c) => { c /= 255; return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4; };
        return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
    };
    const contrast = (a, b) => {
        const [l1, l2] = [luminance(a), luminance(b)].sort((x, y) => y - x);
        return (l1 + 0.05) / (l2 + 0.05);
    };
    const pageBackground = rgba(getComputedStyle(document.body).backgroundColor);
    const backgroundOf = (el) => {
        const layers = [];
        for (let node = el; node && node.nodeType === 1; node = node.parentElement) {
            const c = rgba(getComputedStyle(node).backgroundColor);
            if (c[3] > 0) layers.push(c);
            if (c[3] >= 1) break;
        }
        let colour = layers.length && layers[layers.length - 1][3] >= 1 ? layers.pop() : pageBackground;
        while (layers.length) colour = over(layers.pop(), colour);
        return colour;
    };

    // every visible text box: HTML text runs (per line) and SVG text elements
    const boxes = [];
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const range = document.createRange();
    const htmlOwners = new Set();
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
        if (!node.textContent.trim()) continue;
        const el = node.parentElement;
        if (!el || el.closest("svg") || el.closest(".sr-only") || effectiveOpacity(el) < 0.05) continue;
        range.selectNodeContents(node);
        for (const r of range.getClientRects()) {
            if (r.width < 2 || r.height < 2) continue;
            boxes.push({ r, owner: el, text: short(node.textContent) });
        }
        htmlOwners.add(el);
    }
    const svgTexts = [];
    for (const t of root.querySelectorAll("svg text")) {
        if (!t.textContent.trim() || effectiveOpacity(t) < 0.05) continue;
        const r = t.getBoundingClientRect();
        if (r.width < 2 || r.height < 2) continue;
        boxes.push({ r, owner: t, text: short(t.textContent) });
        svgTexts.push({ t, r });
    }

    // 1. text overlapping text
    for (let i = 0; i < boxes.length; i++) {
        const a = boxes[i];
        for (let j = i + 1; j < boxes.length; j++) {
            const b = boxes[j];
            if (a.owner === b.owner || a.owner.contains(b.owner) || b.owner.contains(a.owner)) continue;
            const w = Math.min(a.r.right, b.r.right) - Math.max(a.r.left, b.r.left);
            const h = Math.min(a.r.bottom, b.r.bottom) - Math.max(a.r.top, b.r.top);
            if (w > 2 && h > 3) issues.push({ kind: "text-overlap", where: where(a.owner), detail: `"${a.text}" x "${b.text}" (${Math.round(w)}x${Math.round(h)} px)` });
        }
    }

    // 2. SVG text crossing a mark's edge, clipped by its SVG, truncated, or illegible on its background
    for (const svg of root.querySelectorAll("svg")) {
        const sb = svg.getBoundingClientRect();
        if (sb.width < 20 || sb.height < 20) continue;
        const marks = [...svg.querySelectorAll("g.mark-rect path, g.mark-symbol path, g.mark-arc path, g.mark-area path")]
            .map((p) => ({ p, r: p.getBoundingClientRect(), fill: rgba(getComputedStyle(p).fill), op: effectiveOpacity(p) * parseFloat(getComputedStyle(p).fillOpacity || "1") }))
            .filter((m) => m.op > 0.05 && m.fill[3] > 0.05 && m.r.width > 0 && m.r.height > 0);
        const frame = svg.closest(FRAME);
        const card = frame ? backgroundOf(frame) : pageBackground;
        for (const { t, r } of svgTexts.filter((x) => svg.contains(x.t))) {
            const label = short(t.textContent);
            if (r.left < sb.left - 1 || r.right > sb.right + 1 || r.top < sb.top - 1 || r.bottom > sb.bottom + 1) {
                issues.push({ kind: "svg-text-clipped", where: where(svg), detail: `"${label}"` });
            }
            if (/…$/.test(t.textContent.trim())) issues.push({ kind: "svg-text-truncated", where: where(svg), detail: `"${label}"` });
            const cx = (r.left + r.right) / 2;
            const cy = (r.top + r.bottom) / 2;
            let under;
            for (const m of marks) {
                const w = Math.min(r.right, m.r.right) - Math.max(r.left, m.r.left);
                const h = Math.min(r.bottom, m.r.bottom) - Math.max(r.top, m.r.top);
                if (w <= 0 || h <= 0) continue;
                const inside = r.left >= m.r.left - 1 && r.right <= m.r.right + 1 && r.top >= m.r.top - 1 && r.bottom <= m.r.bottom + 1;
                if (!inside && w > 2 && h > 3) {
                    issues.push({ kind: "svg-text-crosses-mark", where: where(svg), detail: `"${label}" over a ${m.p.closest("g[class*='mark-']").getAttribute("class").match(/mark-(\w+)/)[1]} mark (${Math.round(w)}x${Math.round(h)} px)` });
                }
                if (cx >= m.r.left && cx <= m.r.right && cy >= m.r.top && cy <= m.r.bottom) under = m;
            }
            const fg = rgba(getComputedStyle(t).fill);
            const bg = under ? over([...under.fill.slice(0, 3), under.fill[3] * Math.min(1, under.op)], card) : card;
            const ratio = contrast(over(fg, bg), bg);
            const size = parseFloat(getComputedStyle(t).fontSize) || 11;
            if (ratio < (size >= 24 ? 3 : 4.5)) issues.push({ kind: "svg-low-contrast", where: where(svg), detail: `"${label}" ${ratio.toFixed(2)}:1 at ${size}px` });
        }
        if (frame) {
            const fb = frame.getBoundingClientRect();
            if (sb.right > fb.right + 1 || sb.bottom > fb.bottom + 1 || sb.left < fb.left - 1) issues.push({ kind: "chart-overflows-card", where: where(svg), detail: `${Math.round(sb.width)}x${Math.round(sb.height)}` });
            if (sb.height < 40 && svg.querySelector("g.mark-rect, g.mark-symbol, g.mark-line")) issues.push({ kind: "chart-too-small", where: where(svg), detail: `${Math.round(sb.width)}x${Math.round(sb.height)}` });
        }
    }

    // 3. HTML text contrast, and text cut off by its box
    for (const el of htmlOwners) {
        const style = getComputedStyle(el);
        const bg = backgroundOf(el);
        const fg = rgba(style.color);
        const alpha = fg[3] * effectiveOpacity(el);
        const ratio = contrast(over([fg[0], fg[1], fg[2], alpha], bg), bg);
        const size = parseFloat(style.fontSize);
        const large = size >= 24 || (size >= 18.66 && parseInt(style.fontWeight, 10) >= 700);
        if (ratio < (large ? 3 : 4.5)) {
            const disabled = el.closest(":disabled, [aria-disabled='true']") || effectiveOpacity(el) < 0.95;
            issues.push({ kind: disabled ? "low-contrast-disabled" : "low-contrast", where: where(el), detail: `"${short(el.textContent)}" ${ratio.toFixed(2)}:1 at ${size}px` });
        }
        if (size < 12) issues.push({ kind: "text-under-12px", where: where(el), detail: `"${short(el.textContent)}" ${size}px` });
    }
    for (const el of root.querySelectorAll("*")) {
        if (el.closest("svg")) continue;
        const style = getComputedStyle(el);
        const clips = ["hidden", "clip"].includes(style.overflowX) || style.textOverflow === "ellipsis";
        if (el.clientWidth <= 1 || el.clientHeight <= 1) continue;
        if (clips && el.scrollWidth > el.clientWidth + 1 && el.textContent.trim() && effectiveOpacity(el) > 0.05) {
            // cut only when a text run inside actually crosses the clipping box
            const box = el.getBoundingClientRect();
            const inner = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
            for (let node = inner.nextNode(); node; node = inner.nextNode()) {
                if (!node.textContent.trim() || node.parentElement.closest("svg")) continue;
                range.selectNodeContents(node);
                const crossing = [...range.getClientRects()].some((r) => r.width > 0 && (r.right > box.right + 1 || r.left < box.left - 1));
                if (crossing) {
                    issues.push({ kind: "html-text-cut", where: where(el), detail: `"${short(node.textContent)}" in a ${Math.round(box.width)} px box` });
                    break;
                }
            }
        }
    }

    // 4. page-level problems
    if (document.documentElement.scrollWidth > innerWidth + 1) issues.push({ kind: "page-scrolls-sideways", where: "page", detail: `${document.documentElement.scrollWidth} > ${innerWidth}` });
    const text = root.innerText;
    for (const m of text.matchAll(/(.{0,30})\b(NaN|undefined|null|Infinity|\[object \w+\]|n\/a)\b(.{0,30})/g)) {
        issues.push({ kind: "bad-value", where: "page", detail: short(m[0]) });
    }
    for (const el of root.querySelectorAll("[role='alert']")) issues.push({ kind: "error-state", where: where(el), detail: short(el.textContent) });
    if (options.emptyText && options.emptyText.test(text)) issues.push({ kind: "empty-state", where: "page", detail: `text matches ${options.emptyText}` });
    if (root.querySelector("[aria-busy='true']")) issues.push({ kind: "still-loading", where: "page", detail: "aria-busy present" });

    // de-duplicate
    const seen = new Set();
    const unique = issues.filter((issue) => {
        const key = `${issue.kind}|${issue.where}|${issue.detail}`;
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
    });
    const current = [...document.querySelectorAll("nav button[aria-current='page'], aside button[aria-current='page']")][0];
    return {
        page: current?.textContent.trim() ?? "?",
        theme: document.documentElement.classList.contains("dark") ? "dark" : "light",
        width: innerWidth,
        issues: unique,
    };
};

// Visits each named page through the rail, waits for its data, and inspects it. Poll
// window.__runOut until done is true.
window.__runAll = (names) => {
    window.__runOut = { done: false, results: [] };
    (async () => {
        for (const name of names) {
            const button = [...document.querySelectorAll("nav button")].find((b) => b.textContent.trim() === name);
            if (!button) {
                window.__runOut.results.push({ page: name, error: "no nav button" });
                continue;
            }
            button.click();
            const start = performance.now();
            await new Promise((r) => setTimeout(r, 1200));
            while (performance.now() - start < 20000 && document.querySelector("[aria-busy='true']")) {
                await new Promise((r) => setTimeout(r, 400));
            }
            await new Promise((r) => setTimeout(r, 1200));
            try {
                window.__runOut.results.push(window.__inspect());
            } catch (error) {
                window.__runOut.results.push({ page: name, error: String(error) });
            }
        }
        window.__runOut.done = true;
    })();
    return "started";
};

// Groups the run's issues by kind for reading.
window.__summary = () => {
    const lines = [];
    for (const result of window.__runOut.results) {
        if (result.error) {
            lines.push(`${result.page}: ERROR ${result.error}`);
            continue;
        }
        const kinds = {};
        for (const issue of result.issues) (kinds[issue.kind] ??= []).push(`${issue.where} :: ${issue.detail}`);
        lines.push(`== ${result.page} (${result.theme}, ${result.width}px): ${result.issues.length} issues`);
        for (const [kind, items] of Object.entries(kinds)) {
            lines.push(`  ${kind} (${items.length})`);
            for (const item of items.slice(0, 12)) lines.push(`    ${item}`);
        }
    }
    return lines.join("\n");
};
