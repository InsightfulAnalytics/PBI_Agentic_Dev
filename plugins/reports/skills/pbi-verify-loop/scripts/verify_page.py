"""Refresh a report in Power BI Desktop, wait until the canvas is stable, screenshot it.

Replaces the hand-rolled `refresh -> Start-Sleep <guess> -> screenshot` loop with
stability polling: capture repeatedly until two consecutive screenshots match.
When refreshing, a pre-refresh baseline capture is taken so a too-fast "stable"
result on the OLD canvas is not mistaken for the refreshed one.

Usage:
  python verify_page.py "Report.Report/Page.Page" --output out.png
  python verify_page.py "C:/path/My.Report" -o out.png --model      # also re-apply TMDL
  python verify_page.py "R.Report/P.Page" -o out.png --compare mockup.png --region 40,120,600,400

--region coordinates are in CAPTURE pixels (i.e. after --scale; default scale 2 doubles them).
Exit codes: 0 = stable capture written; 2 = timed out (last capture still written); 1 = hard error.
Requires: pbir CLI on PATH, Power BI Desktop running with the report open,
Desktop preview feature "external tool access" enabled. Pillow needed only for --compare.
"""
import argparse, hashlib, json, os, re, subprocess, sys, tempfile, time, shutil

def run(cmd, check=True):
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=env)
    if check and p.returncode != 0:
        sys.exit(f"ERROR running {' '.join(cmd)} (exit {p.returncode}):\n{p.stdout}\n{p.stderr}")
    return p

def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def report_root(path):
    """Everything up to and including the first segment ending in .Report."""
    m = re.match(r"(.*?\.Report)(?=/|$)", path.replace("\\", "/"), re.IGNORECASE)
    if not m:
        sys.exit(f'ERROR: no ".Report" segment found in path: {path}')
    return m.group(1)

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", help='Report or page path, e.g. "Name.Report" or "Name.Report/Page.Page"')
    ap.add_argument("-o", "--output", required=True, help="Final PNG path")
    ap.add_argument("--model", action="store_true", help="Pass -m to refresh (re-apply TMDL model)")
    ap.add_argument("--no-refresh", action="store_true", help="Skip the refresh step, just settle+capture")
    ap.add_argument("--scale", type=int, default=2, help="Render scale 1-3 (default 2)")
    ap.add_argument("--timeout", type=float, default=45, help="Max seconds to wait for stability (default 45)")
    ap.add_argument("--interval", type=float, default=3, help="Seconds between captures (default 3)")
    ap.add_argument("--compare", help="Mockup/reference PNG to diff against the final capture")
    ap.add_argument("--region", help="x,y,w,h crop in CAPTURE pixels, applied to both images before comparing")
    args = ap.parse_args()

    tmpdir = tempfile.mkdtemp(prefix="pbi-verify-")
    last = os.path.join(tmpdir, "cap.png")
    shot = lambda: run(["pbir", "desktop", "screenshot", args.path, "-o", last,
                        "--scale", str(args.scale)])

    baseline_hash = None
    if not args.no_refresh:
        shot()                       # pre-refresh baseline: detect when the refresh lands
        baseline_hash = sha(last)
        cmd = ["pbir", "desktop", "refresh", report_root(args.path)]
        if args.model:
            cmd.append("-m")
        run(cmd)

    prev_hash, stable, captures = None, False, 0
    deadline = time.time() + args.timeout
    grace = time.time() + args.timeout / 2   # how long we insist on seeing a change post-refresh
    waiting_for_change = baseline_hash is not None
    try:
        while time.time() < deadline:
            shot()
            captures += 1
            h = sha(last)
            if waiting_for_change:
                if h != baseline_hash or time.time() >= grace:
                    # canvas changed — or it legitimately looks the same; fall back to stability
                    waiting_for_change = False
                    prev_hash = h
                time.sleep(args.interval)
                continue
            if h == prev_hash:
                stable = True
                break
            prev_hash = h
            time.sleep(args.interval)

        final_hash = sha(last)
        out_dir = os.path.dirname(os.path.abspath(args.output))
        os.makedirs(out_dir, exist_ok=True)
        shutil.copyfile(last, args.output)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    result = {"output": os.path.abspath(args.output), "captures": captures, "stable": stable,
              "changed_from_baseline": (final_hash != baseline_hash) if baseline_hash else None}

    if args.compare:
        try:
            from PIL import Image, ImageChops
        except ImportError:
            sys.exit("ERROR: --compare requires Pillow (pip install pillow)")
        a = Image.open(args.output).convert("RGB")
        b = Image.open(args.compare).convert("RGB")
        if b.size != a.size:
            b = b.resize(a.size)     # align reference to capture resolution BEFORE any crop
        if args.region:
            x, y, w, h = (int(v) for v in args.region.split(","))
            if x < 0 or y < 0 or x + w > a.size[0] or y + h > a.size[1]:
                sys.exit(f"ERROR: --region {args.region} outside capture bounds {a.size} "
                         f"(region coords are capture pixels; --scale was {args.scale})")
            a, b = a.crop((x, y, x + w, y + h)), b.crop((x, y, x + w, y + h))
        diff = ImageChops.difference(a, b)
        r_, g_, b_ = diff.split()
        combined = ImageChops.lighter(ImageChops.lighter(r_, g_), b_)   # per-channel max: catches chroma-only shifts
        hist = combined.histogram()
        changed = sum(hist[8:])      # pixels where any channel differs by >= 8
        ratio = changed / (a.size[0] * a.size[1])
        side = Image.new("RGB", (a.size[0] * 2 + 8, a.size[1]), (255, 255, 255))
        side.paste(a, (0, 0)); side.paste(b, (a.size[0] + 8, 0))
        comp_path = os.path.splitext(args.output)[0] + "-vs-ref.png"
        side.save(comp_path)
        result.update({"diff_ratio": round(ratio, 4), "diff_bbox": combined.getbbox(),
                       "side_by_side": comp_path})

    print(json.dumps(result, indent=2))
    sys.exit(0 if stable else 2)

if __name__ == "__main__":
    main()
