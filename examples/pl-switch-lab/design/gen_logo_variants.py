"""Recolour Logo-Timothy-Osborn.jpg onto transparency, in light palettes that read
on the navy side panel (#071A38 -> #164080), in three layouts.

Unmattes each pixel against white along the line to whichever brand ink it lies
nearest, so anti-aliased edges keep their softness with no white fringe."""
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "logo"
SRC = ROOT.parent / "Logo-Timothy-Osborn.jpg"

WHITE = np.array([255.0, 255.0, 255.0])
INKS = np.array([[59.0, 90.0, 119.0],     # 0 navy  #3B5A77 -> bars + letterforms
                 [93.0, 142.0, 202.0]])   # 1 blue  #5D8ECA -> swoosh + arrow + text shadow
SCALE = 4
ALPHA_FLOOR = 0.06        # kills JPEG chroma-ringing halos, which glow on a dark panel

# (name, label, ink rgba, swoosh rgba)
# The wordmark's original light-blue drop shadow is dropped everywhere: it existed to
# lift DARK letters off white. Inverted it just doubles the light letters into a blur.
PALETTES = [
    ("ice",    "Ice",    (234, 242, 251, 1.00), (142, 202, 230, 1.00)),
    ("signal", "Signal", (255, 255, 255, 1.00), (255, 183,   3, 1.00)),
    ("sky",    "Sky",    (184, 217, 242, 1.00), ( 93, 169, 233, 1.00)),
    ("mono",   "Mono",   (255, 255, 255, 1.00), (255, 255, 255, 0.70)),
]
# The wordmark carries a soft pale-blue drop shadow that unmattes to LOW-alpha ink,
# not to the blue class. Alpha there is cleanly bimodal (letters >0.9, shadow ~0.35),
# so a smoothstep across the empty 0.50-0.80 valley drops it and keeps a soft edge.
SHADOW_CUT = (0.50, 0.80)


def harden(a, lo, hi):
    t = np.clip((a - lo) / (hi - lo), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def split_rows(gray, cut=215):
    """Row bands of ink, used to separate the mark from the wordmark."""
    ink = gray < cut
    rows = ink.any(axis=1)
    bands, start = [], None
    for i, on in enumerate(rows):
        if on and start is None:
            start = i
        elif not on and start is not None:
            bands.append((start, i))
            start = None
    if start is not None:
        bands.append((start, len(rows)))
    return bands, ink


def unmatte(rgb):
    """-> (alpha HxW float, class HxW int). Projects each pixel onto white->ink."""
    d = rgb - WHITE                                   # H,W,3
    best_a = None
    best_res = None
    best_k = None
    for k, ink in enumerate(INKS):
        v = ink - WHITE
        a = np.clip((d @ v) / (v @ v), 0.0, 1.0)
        res = np.linalg.norm(d - a[..., None] * v, axis=-1)
        if best_res is None:
            best_a, best_res, best_k = a, res, np.zeros(a.shape, int)
        else:
            take = res < best_res
            best_a = np.where(take, a, best_a)
            best_k = np.where(take, k, best_k)
            best_res = np.where(take, res, best_res)
    a = np.clip((best_a - ALPHA_FLOOR) / (1 - ALPHA_FLOOR), 0.0, 1.0)
    return a, best_k


def tint(alpha, cls, ink, accent):
    h, w = alpha.shape
    out = np.zeros((h, w, 4), float)
    for k, col in ((0, ink), (1, accent)):
        sel = cls == k
        out[sel, 0:3] = col[:3]
        out[sel, 3] = alpha[sel] * col[3] * 255.0
    return Image.fromarray(np.round(out).astype("uint8"), "RGBA")


def trim(im):
    return im.crop(im.getchannel("A").getbbox())


def compose(size, parts):
    """parts = [(image, (x, y)), ...] on a transparent canvas."""
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    for im, xy in parts:
        canvas.alpha_composite(im, xy)
    return canvas


def main():
    OUT.mkdir(exist_ok=True)
    src = Image.open(SRC).convert("RGB")
    gray = np.asarray(src.convert("L")).astype(float)
    bands, _ = split_rows(gray)
    assert len(bands) == 2, f"expected mark + wordmark bands, got {bands}"
    (m0, m1), (w0, w1) = bands

    big = src.resize((src.width * SCALE, src.height * SCALE), Image.LANCZOS)
    rgb = np.asarray(big).astype(float)
    alpha, cls = unmatte(rgb)

    manifest = []
    for key, label, ink, accent in PALETTES:
        marked = tint(alpha, cls, np.array(ink, float), np.array(accent, float))
        worded = tint(harden(alpha, *SHADOW_CUT), cls,
                      np.array(ink, float), np.array(accent, float))
        mark = trim(marked.crop((0, m0 * SCALE, marked.width, m1 * SCALE)))
        word = trim(worded.crop((0, w0 * SCALE, worded.width, w1 * SCALE)))

        gap_v = int(round(mark.height * 0.16))
        sw = max(mark.width, word.width)
        stacked = compose(
            (sw, mark.height + gap_v + word.height),
            [(mark, ((sw - mark.width) // 2, 0)),
             (word, ((sw - word.width) // 2, mark.height + gap_v))],
        )

        gap_h = int(round(mark.width * 0.18))
        hh = max(mark.height, word.height)
        horizontal = compose(
            (mark.width + gap_h + word.width, hh),
            [(mark, (0, (hh - mark.height) // 2)),
             (word, (mark.width + gap_h, (hh - word.height) // 2))],
        )

        for layout, im in (("stacked", stacked), ("horizontal", horizontal), ("mark", mark)):
            path = OUT / f"binexus-{key}-{layout}.png"
            im.save(path)
            manifest.append((key, label, layout, path, im.size))
            print(f"{path.name:34} {im.size[0]:4}x{im.size[1]:<4}  {path.stat().st_size/1024:6.1f} KB")

    # sanity: transparent corner, opaque ink somewhere, no stray mid-alpha halo mass
    chk = Image.open(OUT / "binexus-ice-stacked.png").convert("RGBA")
    a = np.asarray(chk)[..., 3]
    assert a[0, 0] == 0, "top-left corner must be transparent"
    assert a.max() == 255, "logo must contain fully opaque pixels"
    assert (a > 0).mean() < 0.6, "too much coverage - background probably not removed"
    print(f"\nOK  coverage {(a > 0).mean():.1%}  files {len(manifest)}")


if __name__ == "__main__":
    main()
