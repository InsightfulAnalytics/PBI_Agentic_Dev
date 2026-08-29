"""Inline every logo PNG into logo_review.tpl.html as a data URI -> logo_review.html.

The Artifact CSP blocks external hosts, so the review page has to be self-contained.
PNGs are downscaled to 700px on the long edge for embedding; the full-resolution
files in design/logo/ stay untouched and are what actually gets used in the report.
"""
import base64
import io
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
LOGO = ROOT / "logo"
TPL = ROOT / "logo_review.tpl.html"
OUT = ROOT / "logo_review.html"
EMBED_MAX = 700

PALETTES = ["ice", "signal", "sky", "mono"]
LAYOUTS = ["stacked", "horizontal", "mark"]


def data_uri(path, max_edge=EMBED_MAX):
    im = Image.open(path)
    full = im.size
    if max(im.size) > max_edge:
        s = max_edge / max(im.size)
        im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    buf = io.BytesIO()
    if im.mode == "RGBA":
        im.save(buf, "PNG", optimize=True)
        mime = "image/png"
    else:
        im.convert("RGB").save(buf, "JPEG", quality=88, optimize=True)
        mime = "image/jpeg"
    return f"data:{mime};base64," + base64.b64encode(buf.getvalue()).decode(), full


def main():
    data, dims = {}, {}
    for p in PALETTES:
        for l in LAYOUTS:
            key = f"{p}-{l}"
            src = LOGO / f"binexus-{key}.png"
            assert src.exists(), f"missing {src}"
            uri, full = data_uri(src)
            data[key] = uri
            dims[key] = f"{full[0]} x {full[1]}"

    src_uri, _ = data_uri(ROOT.parent / "Logo-Timothy-Osborn.jpg", 420)

    html = TPL.read_text(encoding="utf-8")
    assert "__IMAGES__" in html and "__SRC__" in html, "template placeholders missing"
    html = html.replace("__IMAGES__", json.dumps({"data": data, "dims": dims}))
    html = html.replace("__SRC__", src_uri)
    OUT.write_text(html, encoding="utf-8")

    kb = OUT.stat().st_size / 1024
    print(f"{OUT.name}  {kb:,.0f} KB  ({len(data)} marks embedded)")
    assert kb < 16 * 1024, "over the 16 MB artifact ceiling"
    assert "__IMAGES__" not in html and "__SRC__" not in html


if __name__ == "__main__":
    main()
