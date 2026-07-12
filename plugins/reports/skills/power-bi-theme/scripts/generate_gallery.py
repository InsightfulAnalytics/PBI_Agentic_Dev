#!/usr/bin/env python3
"""
generate_gallery.py - Build a visual gallery of Power BI themes.

Scans a folder for Power BI theme JSON files (anything with a "dataColors"
array) and emits a single self-contained HTML file. Each theme is rendered as
a realistic mini Power BI report mockup using the theme's own page background,
card backgrounds, foreground color and data-color palette - so you can choose a
theme by sight rather than by reading hex codes.

Usage:
    python generate_gallery.py [--themes-dir DIR] [--output FILE] [--open]

Defaults:
    --themes-dir : the bundled ./themes folder next to this script
    --output     : <themes-dir>/powerbi-theme-gallery.html
"""
import argparse
import json
import os
import re
import sys
import webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.dirname(HERE)


def natural_key(name):
    """Sort 'Theme 2' before 'Theme 10', Dark before Light."""
    parts = re.split(r"(\d+)", name)
    key = [int(p) if p.isdigit() else p.lower() for p in parts]
    return key


def deep_get(d, path, default=None):
    cur = d
    for p in path:
        if isinstance(cur, list):
            try:
                cur = cur[p]
            except (IndexError, TypeError):
                return default
        elif isinstance(cur, dict):
            if p not in cur:
                return default
            cur = cur[p]
        else:
            return default
    return cur


def solid_color(node):
    """Pull a hex color out of a Power BI {color:{solid:{color:...}}} style node."""
    if not isinstance(node, list) or not node:
        return None
    first = node[0]
    return (
        deep_get(first, ["color", "solid", "color"])
        or deep_get(first, ["solid", "color"])
    )


def luminance(hexcolor):
    """Relative luminance 0..1 for a #RRGGBB string; used to decide dark vs light."""
    if not hexcolor:
        return 0.5
    h = hexcolor.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        return 0.5
    try:
        r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    except ValueError:
        return 0.5
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def derive(theme, filename):
    """Extract the handful of fields the preview renderer needs."""
    name = theme.get("name") or os.path.splitext(filename)[0]
    page_bg = (
        solid_color(deep_get(theme, ["visualStyles", "page", "*", "background"]))
        or theme.get("background")
        or "#FFFFFF"
    )
    card_bg = (
        solid_color(deep_get(theme, ["visualStyles", "*", "*", "background"]))
        or theme.get("background")
        or page_bg
    )
    radius = deep_get(theme, ["visualStyles", "*", "*", "border", 0, "radius"], 4) or 4
    fg = theme.get("foreground") or ("#FFFFFF" if luminance(page_bg) < 0.5 else "#252423")
    secondary = theme.get("foregroundNeutralSecondary") or fg
    data_colors = theme.get("dataColors") or []
    is_dark = luminance(page_bg) < 0.5

    return {
        "name": name,
        "file": filename,
        "isDark": is_dark,
        "pageBg": page_bg,
        "cardBg": card_bg,
        "radius": radius,
        "fg": fg,
        "secondary": secondary,
        "dataColors": data_colors,
        "good": theme.get("good"),
        "bad": theme.get("bad"),
        "neutral": theme.get("neutral"),
    }


def collect(themes_dir):
    items = []
    for root, _dirs, files in os.walk(themes_dir):
        for fn in files:
            if not fn.lower().endswith(".json"):
                continue
            full = os.path.join(root, fn)
            try:
                with open(full, "r", encoding="utf-8-sig") as f:
                    data = json.load(f)
            except (json.JSONDecodeError, OSError):
                continue
            if not isinstance(data, dict) or "dataColors" not in data:
                continue  # not a Power BI theme
            d = derive(data, fn)
            d["path"] = os.path.relpath(full, themes_dir).replace("\\", "/")
            items.append(d)
    items.sort(key=lambda x: natural_key(x["name"]))
    return items


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Power BI Theme Gallery</title>
<style>
  :root { --bg:#0f1115; --panel:#171a21; --ink:#e8eaed; --muted:#9aa0aa; --line:#262b35; --accent:#4E7CFF; }
  * { box-sizing: border-box; }
  body { margin:0; font-family: "Segoe UI", system-ui, -apple-system, sans-serif; background:var(--bg); color:var(--ink); }
  header { position:sticky; top:0; z-index:5; background:rgba(15,17,21,.92); backdrop-filter:blur(8px); border-bottom:1px solid var(--line); padding:16px 22px; }
  h1 { margin:0 0 4px; font-size:18px; font-weight:700; letter-spacing:.2px; }
  .sub { color:var(--muted); font-size:12.5px; }
  .controls { display:flex; flex-wrap:wrap; gap:10px; align-items:center; margin-top:12px; }
  .controls input[type=search]{ background:var(--panel); border:1px solid var(--line); color:var(--ink); border-radius:8px; padding:8px 12px; font-size:13px; min-width:240px; outline:none; }
  .controls input[type=search]:focus{ border-color:var(--accent); }
  .seg { display:inline-flex; background:var(--panel); border:1px solid var(--line); border-radius:8px; overflow:hidden; }
  .seg button { background:transparent; color:var(--muted); border:0; padding:8px 14px; font-size:12.5px; cursor:pointer; }
  .seg button.active { background:var(--accent); color:#fff; }
  .count { color:var(--muted); font-size:12.5px; margin-left:auto; }
  .grid { display:grid; grid-template-columns:repeat(auto-fill, minmax(480px,1fr)); gap:24px; padding:24px; }
  .card { border:1px solid var(--line); border-radius:14px; overflow:hidden; background:var(--panel); display:flex; flex-direction:column; transition:transform .12s ease, border-color .12s ease; }
  .card:hover { transform:translateY(-3px); border-color:#3a4150; }
  .preview { padding:18px; min-height:380px; }
  .pv-top { display:flex; justify-content:space-between; align-items:baseline; margin-bottom:13px; }
  .pv-title { font-size:16px; font-weight:700; }
  .pv-sub { font-size:11px; letter-spacing:.4px; text-transform:uppercase; }
  .pv-kpis { display:grid; grid-template-columns:repeat(3,1fr); gap:11px; margin-bottom:12px; }
  .kpi { padding:12px 13px; }
  .kpi .lbl { font-size:9.5px; text-transform:uppercase; letter-spacing:.5px; }
  .kpi .val { font-size:23px; font-weight:700; line-height:1.1; margin-top:4px; }
  .kpi .delta { font-size:11px; font-weight:600; margin-top:3px; }
  .pv-row { display:grid; grid-template-columns:1.4fr 1fr; gap:11px; margin-bottom:11px; }
  .pv-row:last-child { margin-bottom:0; }
  .panel-mini { padding:12px 13px; }
  .panel-mini .ttl { font-size:10.5px; text-transform:uppercase; letter-spacing:.5px; margin-bottom:10px; }
  .bars { display:flex; align-items:flex-end; gap:7px; height:96px; }
  .bars > div { flex:1; border-radius:3px 3px 0 0; }
  .donut { width:96px; height:96px; border-radius:50%; margin:6px auto 0; }
  .lines { width:100%; height:96px; display:block; }
  .legend { display:flex; flex-direction:column; gap:9px; }
  .legend .lrow { display:flex; align-items:center; gap:9px; font-size:12px; }
  .legend .dot { width:12px; height:12px; border-radius:3px; flex:none; }
  .legend .lname { flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .legend .lval { font-variant-numeric:tabular-nums; font-weight:600; }
  .pal-wrap { padding:6px 18px 16px; }
  .pal-ttl { font-size:10px; text-transform:uppercase; letter-spacing:.5px; color:var(--muted); margin:0 0 8px; }
  .swatches { display:grid; grid-template-columns:repeat(16, 1fr); gap:4px; }
  .swatches > span { height:28px; border-radius:4px; }
  .foot { display:flex; align-items:center; gap:8px; padding:11px 14px; border-top:1px solid var(--line); }
  .name { font-size:13px; font-weight:600; }
  .badge { font-size:9.5px; padding:2px 7px; border-radius:20px; border:1px solid var(--line); color:var(--muted); }
  .badge.dark { background:#11151c; }
  .badge.light { background:#f4f6fb; color:#333; border-color:#d6dae3; }
  .use { margin-left:auto; background:var(--accent); color:#fff; border:0; border-radius:8px; padding:7px 12px; font-size:12px; font-weight:600; cursor:pointer; }
  .use:hover { filter:brightness(1.08); }
  .toast { position:fixed; left:50%; bottom:26px; transform:translateX(-50%) translateY(20px); background:#1e2330; border:1px solid #384050; color:var(--ink); padding:12px 18px; border-radius:10px; font-size:13px; opacity:0; pointer-events:none; transition:.2s; box-shadow:0 10px 30px rgba(0,0,0,.4); z-index:20; max-width:520px; }
  .toast.show { opacity:1; transform:translateX(-50%) translateY(0); }
  .toast code { background:#0d1016; padding:2px 7px; border-radius:5px; color:#9ec1ff; }
  .empty { padding:60px; text-align:center; color:var(--muted); }
</style>
</head>
<body>
<header>
  <h1>Power BI Theme Gallery</h1>
  <div class="sub">Each tile is a live mock report rendered with that theme's real colors. Find one you like, click <b>Use this theme</b>, then tell Claude.</div>
  <div class="controls">
    <input id="search" type="search" placeholder="Search theme name...">
    <div class="seg" id="modeSeg">
      <button data-mode="all" class="active">All</button>
      <button data-mode="dark">Dark</button>
      <button data-mode="light">Light</button>
    </div>
    <div class="seg" id="paletteSeg" title="How to order the data-color swatches">
      <button data-sort="hue" class="active">Palette: by color</button>
      <button data-sort="theme">theme order</button>
    </div>
    <span class="count" id="count"></span>
  </div>
</header>
<div class="grid" id="grid"></div>
<div class="empty" id="empty" style="display:none">No themes match your filter.</div>
<div class="toast" id="toast"></div>
<script>
const THEMES = /*__THEMES__*/[]/*__END__*/;
const grid = document.getElementById('grid');
const empty = document.getElementById('empty');
const countEl = document.getElementById('count');
let mode = 'all', query = '', paletteSort = 'hue';

function esc(s){ return (s||'').replace(/[&<>"]/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }
function colorAt(t,i){ const dc=t.dataColors||[]; return dc.length? dc[i%dc.length] : '#888'; }

function hexToHsl(hex){
  let h=(hex||'').replace('#',''); if(h.length===3) h=h.split('').map(c=>c+c).join('');
  const r=parseInt(h.substr(0,2),16)/255, g=parseInt(h.substr(2,2),16)/255, b=parseInt(h.substr(4,2),16)/255;
  const mx=Math.max(r,g,b), mn=Math.min(r,g,b), l=(mx+mn)/2, d=mx-mn; let hue=0, s=0;
  if(d){ s=l>0.5? d/(2-mx-mn): d/(mx+mn);
    hue=(mx===r? (g-b)/d+(g<b?6:0) : mx===g? (b-r)/d+2 : (r-g)/d+4)*60; }
  return {h:hue, s, l};
}
// Order swatches for easy scanning: chromatic colors by hue then lightness, neutrals (greys) last.
function orderedPalette(dc){
  const arr = dc.map((c,i)=>Object.assign({c, i}, hexToHsl(c)));
  if(paletteSort==='theme') return arr;
  const chroma  = arr.filter(x=>x.s>=0.15).sort((a,b)=> a.h-b.h || a.l-b.l);
  const neutral = arr.filter(x=>x.s< 0.15).sort((a,b)=> a.l-b.l);
  return chroma.concat(neutral);
}

function previewHTML(t){
  const dc = t.dataColors||[];
  const good = t.good || colorAt(t,0);
  const bad = t.bad || colorAt(t,2);
  const r = (t.radius||4);
  // bar chart (8 bars)
  const barH = [62,40,75,52,68,34,58,46];
  const bars = barH.map((h,i)=>`<div style="height:${h}%;background:${colorAt(t,i)}"></div>`).join('');
  // donut as conic gradient across first 6 data colors
  const segs = [26,22,17,14,12,9]; let acc=0; const stops=[];
  for(let i=0;i<segs.length;i++){ const from=acc; acc+=segs[i]; stops.push(`${colorAt(t,i)} ${from}% ${acc}%`); }
  const donut = `conic-gradient(${stops.join(',')})`;
  // multi-series line chart
  const series = [[30,45,38,60,55,72,66,85],[52,46,60,48,64,56,68,62],[20,28,24,36,31,44,38,52]];
  const toPts = a => a.map((v,i)=>`${(i/(a.length-1)*100).toFixed(1)},${(36 - v/100*32).toFixed(1)}`).join(' ');
  const lines = series.map((s,i)=>`<polyline fill="none" stroke="${colorAt(t,i)}" stroke-width="2" vector-effect="non-scaling-stroke" stroke-linecap="round" stroke-linejoin="round" points="${toPts(s)}"/>`).join('');
  const lineSvg = `<svg class="lines" viewBox="0 0 100 38" preserveAspectRatio="none">${lines}</svg>`;
  // category legend (more colors, with labels)
  const cats = [['Direct','32%'],['Online','26%'],['Retail','19%'],['Partner','12%'],['Wholesale','7%'],['Other','4%']];
  const legend = cats.map((c,i)=>`<div class="lrow"><span class="dot" style="background:${colorAt(t,i)}"></span><span class="lname" style="color:${t.fg}">${c[0]}</span><span class="lval" style="color:${t.secondary}">${c[1]}</span></div>`).join('');
  // full data color palette (ordered for easy scanning; tooltip keeps original position)
  const palette = orderedPalette(dc).map(x=>`<span style="background:${x.c}" title="#${x.i+1} ${x.c}"></span>`).join('');
  const kpi = (lbl,val,delta,dcol)=>`
    <div class="kpi" style="background:${t.cardBg};border-radius:${r}px">
      <div class="lbl" style="color:${t.secondary}">${lbl}</div>
      <div class="val" style="color:${t.fg}">${val}</div>
      <div class="delta" style="color:${dcol}">${delta}</div>
    </div>`;
  const panel = (title, body)=>`
      <div class="panel-mini" style="background:${t.cardBg};border-radius:${r}px">
        <div class="ttl" style="color:${t.secondary}">${title}</div>
        ${body}
      </div>`;
  return `
  <div class="preview" style="background:${t.pageBg}">
    <div class="pv-top">
      <div class="pv-title" style="color:${t.fg}">Sales Overview</div>
      <div class="pv-sub" style="color:${t.secondary}">FY 2026</div>
    </div>
    <div class="pv-kpis">
      ${kpi('Revenue','$4.2M','&#9650; 12.4%',good)}
      ${kpi('Orders','18.7K','&#9650; 6.1%',good)}
      ${kpi('Churn','3.2%','&#9660; 1.8%',bad)}
    </div>
    <div class="pv-row">
      ${panel('Revenue by Region', `<div class="bars">${bars}</div>`)}
      ${panel('Channel Mix', `<div class="donut" style="background:${donut}"></div>`)}
    </div>
    <div class="pv-row">
      ${panel('Monthly Trend', lineSvg)}
      ${panel('Top Categories', `<div class="legend">${legend}</div>`)}
    </div>
  </div>
  <div class="pal-wrap">
    <div class="pal-ttl">Full data color palette &middot; ${dc.length} colors &middot; ${paletteSort==='theme'?'theme order':'sorted by color'}</div>
    <div class="swatches">${palette}</div>
  </div>`;
}

function render(){
  const list = THEMES.filter(t=>{
    if(mode==='dark' && !t.isDark) return false;
    if(mode==='light' && t.isDark) return false;
    if(query && !t.name.toLowerCase().includes(query)) return false;
    return true;
  });
  countEl.textContent = `${list.length} of ${THEMES.length} themes`;
  empty.style.display = list.length? 'none':'block';
  grid.innerHTML = list.map((t,idx)=>`
    <div class="card">
      ${previewHTML(t)}
      <div class="foot">
        <span class="name">${esc(t.name)}</span>
        <span class="badge ${t.isDark?'dark':'light'}">${t.isDark?'Dark':'Light'}</span>
        <button class="use" data-i="${THEMES.indexOf(t)}">Use this theme</button>
      </div>
    </div>`).join('');
}

let toastTimer;
function showToast(html){
  const el=document.getElementById('toast');
  el.innerHTML=html; el.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer=setTimeout(()=>el.classList.remove('show'), 6000);
}

grid.addEventListener('click', e=>{
  const btn = e.target.closest('.use'); if(!btn) return;
  const t = THEMES[+btn.dataset.i];
  const instruction = `Apply Power BI theme: ${t.name}`;
  navigator.clipboard && navigator.clipboard.writeText(instruction).catch(()=>{});
  showToast(`Copied to clipboard. Paste this to Claude:<br><code>${esc(instruction)}</code><br><span style="color:#9aa0aa;font-size:11px">file: ${esc(t.path)}</span>`);
});

document.getElementById('search').addEventListener('input', e=>{ query=e.target.value.toLowerCase().trim(); render(); });
document.getElementById('modeSeg').addEventListener('click', e=>{
  const b=e.target.closest('button'); if(!b) return;
  mode=b.dataset.mode;
  [...e.currentTarget.children].forEach(c=>c.classList.toggle('active', c===b));
  render();
});
document.getElementById('paletteSeg').addEventListener('click', e=>{
  const b=e.target.closest('button'); if(!b) return;
  paletteSort=b.dataset.sort;
  [...e.currentTarget.children].forEach(c=>c.classList.toggle('active', c===b));
  render();
});
render();
</script>
</body>
</html>"""


def main():
    ap = argparse.ArgumentParser(description="Generate a visual Power BI theme gallery.")
    ap.add_argument("--themes-dir", default=os.path.join(SKILL_ROOT, "themes"),
                    help="Folder to scan for theme JSON files (default: bundled themes).")
    ap.add_argument("--output", default=None,
                    help="Output HTML path (default: <themes-dir>/powerbi-theme-gallery.html).")
    ap.add_argument("--open", action="store_true", help="Open the gallery in the default browser.")
    args = ap.parse_args()

    themes_dir = os.path.abspath(args.themes_dir)
    if not os.path.isdir(themes_dir):
        print(f"ERROR: themes dir not found: {themes_dir}", file=sys.stderr)
        return 2

    items = collect(themes_dir)
    if not items:
        print(f"ERROR: no Power BI theme JSON files found in {themes_dir}", file=sys.stderr)
        return 1

    out = args.output or os.path.join(themes_dir, "powerbi-theme-gallery.html")
    out = os.path.abspath(out)
    html = HTML_TEMPLATE.replace(
        "/*__THEMES__*/[]/*__END__*/",
        json.dumps(items, ensure_ascii=False),
    )
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Gallery written: {out}")
    print(f"Themes rendered: {len(items)}")
    if args.open:
        webbrowser.open("file:///" + out.replace("\\", "/"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
