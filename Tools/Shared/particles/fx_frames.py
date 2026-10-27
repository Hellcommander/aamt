"""Generated footage or stills -> a particle texture: alpha cut, one shared crop, frames picked or looped, packed into a
flipbook atlas (frame 0 top-left, rows left to right, as Unity's texture sheet animation reads it).
Runs in the animation venv (numpy, opencv, PIL); particle_client.py drives it.

    python fx_frames.py --jobs jobs.json

jobs.json: {"jobs": [{
    "mode": "flipbook" | "sprites",
    "video": "clip.mp4"                  flipbook source (or "frames": [png, ...])
    "images": [png, ...]                 sprites: one cell each, for random-frame layers
    "out": "fire_burst.png",
    "grid": [6, 6], "cell": 128,
    "matte": "luma" | "birefnet",        luma: drawn on black, brightness is alpha; birefnet: solid things on a backdrop
    "tint": "baked" | "white",           white: greyscale, so the effect's layer colour tints it in game
    "loop": false,                       true: cut a cycle out of the clip and cross-fade its ends
    "grow_in": 0,                        one-shots: replace the first N frames with frame N scaled up from small
    "gamma": 1.0,                        luma alpha curve (<1 thickens faint glow/smoke)
    "fade": 0.25                         one-shots: fraction of frames at the end that fade to nothing
}]}

Writes <out> (RGBA atlas, straight alpha), <out stem>_preview.png (every frame composited over a dark floor the way
the game blends it), <out stem>.gif and <out stem>_sheet.json (grid, frames, crop, scores). One JSON line per job.
"""
import argparse, json, sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

BG = np.array([0.105, 0.11, 0.13], np.float32)  # preview floor: Chimera's rooms are dark


# ---- reading ----------------------------------------------------------------------------------------------------

def read_video(path):
    cap = cv2.VideoCapture(str(path))
    frames = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        frames.append(cv2.cvtColor(f, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0)
    cap.release()
    if not frames:
        raise RuntimeError(f"no frames in {path}")
    return np.stack(frames)


def read_image(path):
    return np.asarray(Image.open(path).convert("RGB"), np.float32) / 255.0


# ---- alpha --------------------------------------------------------------------------------------------------------

def black_level(frames):
    """The backdrop's brightness: generated 'black' is rarely 0, and video codecs lift it further."""
    v = frames.max(-1)
    return float(np.clip(np.median([np.percentile(f, 8) for f in v]), 0.0, 0.25))


def luma_matte(rgb, black, gamma=1.0):
    """Drawn on black: alpha from the brightest channel above the backdrop; colour un-premultiplied so that
    colour * alpha (how both the additive and the alpha-blended particle shaders use it) gives back the drawing."""
    lift = np.clip((rgb - black) / max(1e-3, 1.0 - black), 0.0, 1.0)
    v = lift.max(-1)
    knee = np.clip((v - 0.025) / 0.06, 0.0, 1.0)  # compression noise near black stays transparent
    a = (v ** gamma) * knee
    col = np.clip(lift / np.maximum(a, 1e-4)[..., None], 0.0, 1.0)
    return col, a


def white(col, a):
    """Greyscale with the brightest solid parts at full white, so the layer colour sets the hue."""
    lum = col @ np.array([0.3, 0.55, 0.15], np.float32)
    ref = np.percentile(lum[a > 0.3], 97) if (a > 0.3).any() else 1.0
    lum = np.clip(lum / max(ref, 1e-3), 0.0, 1.0)
    return np.repeat(lum[..., None], 3, -1)


def cut(frames, job):
    """(T,H,W,3) -> colours (T,H,W,3) and alphas (T,H,W)."""
    if job.get("matte", "luma") == "birefnet":
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import matte
        alphas = np.stack([matte.mask(f) for f in frames])
        matte.free()
        cols = frames.copy()
    else:
        black = black_level(frames)
        pairs = [luma_matte(f, black, float(job.get("gamma", 1.0))) for f in frames]
        cols, alphas = np.stack([p[0] for p in pairs]), np.stack([p[1] for p in pairs])
    if job.get("tint", "baked") == "white":
        cols = np.stack([white(c, a) for c, a in zip(cols, alphas)])
    # Whatever touches the source frame's edge was cut off there: feather it so it doesn't end in a straight line.
    h, w = alphas.shape[1:]
    e = max(4, int(min(h, w) * 0.05))
    ry = np.clip(np.minimum(np.arange(h) + 0.5, h - 0.5 - np.arange(h)) / e, 0, 1)
    rx = np.clip(np.minimum(np.arange(w) + 0.5, w - 0.5 - np.arange(w)) / e, 0, 1)
    alphas = alphas * np.minimum(ry[:, None], rx[None, :])
    return cols, alphas


# ---- framing ------------------------------------------------------------------------------------------------------

def square_box(alpha_union, margin=0.08, thresh=0.04):
    ys, xs = np.nonzero(alpha_union > thresh)
    if len(xs) == 0:
        h, w = alpha_union.shape
        return 0, 0, max(h, w)
    cx, cy = (xs.min() + xs.max() + 1) / 2, (ys.min() + ys.max() + 1) / 2
    side = int(np.ceil(max(xs.max() - xs.min() + 1, ys.max() - ys.min() + 1) * (1 + 2 * margin))) + 4
    return int(round(cx - side / 2)), int(round(cy - side / 2)), side


def crop(img, x0, y0, side):
    """Crop with zero padding where the square runs off the frame."""
    h, w = img.shape[:2]
    out = np.zeros((side, side) + img.shape[2:], img.dtype)
    sx0, sy0, sx1, sy1 = max(0, x0), max(0, y0), min(w, x0 + side), min(h, y0 + side)
    if sx1 > sx0 and sy1 > sy0:
        out[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0] = img[sy0:sy1, sx0:sx1]
    return out


def to_cell(col, a, cell):
    """Resize premultiplied (no dark fringes), then fade the outer pixels so mipmaps don't bleed between cells."""
    pre = cv2.resize(col * a[..., None], (cell, cell), interpolation=cv2.INTER_AREA)
    a2 = cv2.resize(a, (cell, cell), interpolation=cv2.INTER_AREA)
    edge = max(2, cell // 32)
    d = np.minimum(np.arange(cell) + 0.5, cell - 0.5 - np.arange(cell))  # distance to the nearest edge, per axis
    ramp = np.clip(np.minimum(d[None, :], d[:, None]) / edge, 0, 1)
    a2 = a2 * ramp
    col2 = np.clip(pre / np.maximum(a2, 1e-4)[..., None], 0, 1)
    col2[a2 < 1e-3] = 0
    return col2, a2


def scaled(col, a, s):
    """The cell's content shrunk about its centre by s (for grow-in frames)."""
    n = a.shape[0]
    m = max(1, int(round(n * s)))
    o = (n - m) // 2
    c2, a2 = np.zeros_like(col), np.zeros_like(a)
    c2[o:o + m, o:o + m] = cv2.resize(col, (m, m), interpolation=cv2.INTER_AREA)
    a2[o:o + m, o:o + m] = cv2.resize(a, (m, m), interpolation=cv2.INTER_AREA)
    return c2, a2


# ---- timing -------------------------------------------------------------------------------------------------------

def first_cut(cols, alphas, k=5.0):
    """Index of the last frame before the video model cuts to a new picture (one frame-to-frame change far above the
    ones before it), or None. Frames after a cut belong to a different, often half-invented, scene."""
    small = np.stack([cv2.resize(c * a[..., None], (64, 64), interpolation=cv2.INTER_AREA) for c, a in zip(cols, alphas)])
    d = np.abs(np.diff(small, axis=0)).mean((1, 2, 3))
    for t in range(2, len(d)):
        if d[t] > 0.02 and d[t] > k * max(float(np.median(d[max(0, t - 4):t])), 1e-3):
            return t
    return None


def oneshot_positions(alphas, n):
    """From the first frame to where the effect has all but gone, evenly; fractional, so a short stretch still
    fills every cell (sample() blends neighbouring frames)."""
    e = alphas.reshape(len(alphas), -1).sum(1)
    peak = int(e.argmax())
    alive = np.nonzero(e > 0.04 * e[peak])[0]
    end = int(alive.max()) if len(alive) else len(e) - 1
    return np.linspace(0, end, n).tolist(), {"peak": peak, "end": end}


def sample(cols, alphas, positions):
    """Frames at fractional positions, blended premultiplied between the two nearest."""
    oc, oa = [], []
    for x in positions:
        i = int(np.floor(x)); j = min(i + 1, len(cols) - 1); w = x - i
        a = alphas[i] * (1 - w) + alphas[j] * w
        pre = cols[i] * alphas[i][..., None] * (1 - w) + cols[j] * alphas[j][..., None] * w
        oc.append(np.clip(pre / np.maximum(a, 1e-4)[..., None], 0, 1))
        oa.append(a)
    return np.stack(oc), np.stack(oa)


def loop_window(cols, alphas, n_min, fade_k):
    """The stretch [i, j) whose end best matches its start (premultiplied colour, 64 px), long enough, with fade_k
    frames after j to cross-fade from."""
    small = np.stack([cv2.resize(c * a[..., None], (64, 64), interpolation=cv2.INTER_AREA) for c, a in zip(cols, alphas)])
    T = len(small)
    best = None
    for i in range(0, max(1, T // 3)):
        for j in range(i + n_min, T - fade_k + 1):
            d = float(np.abs(small[i] - small[j]).mean())
            if best is None or d < best[0]:
                best = (d, i, j)
    if best is None:  # clip too short for the asked length: use all of it
        return 0, T - fade_k, None
    return best[1], best[2], best[0]


def looped(cols, alphas, i, j, k):
    """Frames i..j-1, the first k blended with the frames just after j so the cycle closes without a pop."""
    oc, oa = [], []
    for m in range(j - i):
        c, a = cols[i + m], alphas[i + m]
        if m < k:
            w = (m + 1) / (k + 1)
            c2, a2 = cols[j + m], alphas[j + m]
            pa = a * w + a2 * (1 - w)
            pc = (c * a[..., None] * w + c2 * a2[..., None] * (1 - w)) / np.maximum(pa, 1e-4)[..., None]
            c, a = pc, pa
        oc.append(c)
        oa.append(a)
    return np.stack(oc), np.stack(oa)


# ---- output -------------------------------------------------------------------------------------------------------

def composite(col, a, blend):
    if blend == "add":
        return np.clip(BG + col * a[..., None], 0, 1)
    return BG * (1 - a[..., None]) + col * a[..., None]


def atlas(cells, grid, cell):
    gx, gy = grid
    out = np.zeros((gy * cell, gx * cell, cells[0].shape[-1]), np.float32)
    for k, c in enumerate(cells[:gx * gy]):
        r, q = divmod(k, gx)
        out[r * cell:(r + 1) * cell, q * cell:(q + 1) * cell] = c
    return out


def save_rgba(path, col, a):
    rgba = np.concatenate([col, a[..., None]], -1)
    Image.fromarray((np.clip(rgba, 0, 1) * 255 + 0.5).astype(np.uint8), "RGBA").save(path)


def run(job):
    out = Path(job["out"])
    out.parent.mkdir(parents=True, exist_ok=True)
    grid = [int(v) for v in job.get("grid", [6, 6])]
    cell = int(job.get("cell", 128))
    n = grid[0] * grid[1]
    mode = job.get("mode", "flipbook")
    blend = job.get("blend", "add")
    info = {"mode": mode, "grid": grid, "cell": cell}

    if mode == "sprites":
        cells_c, cells_a = [], []
        for p in job["images"][:n]:
            c, a = cut(read_image(p)[None], job)
            x0, y0, side = square_box(a[0])
            info.setdefault("coverage", []).append(round(float((a[0] > 0.04).mean()), 3))
            cc, ca = to_cell(crop(c[0], x0, y0, side), crop(a[0], x0, y0, side), cell)
            cells_c.append(cc)
            cells_a.append(ca)
        grid = [grid[0], int(np.ceil(len(cells_c) / grid[0]))]
        info["grid"] = grid
    else:
        frames = read_video(job["video"]) if job.get("video") else np.stack([read_image(p) for p in job["frames"]])
        cols, alphas = cut(frames, job)
        info["source_frames"] = len(frames)
        cut_at = first_cut(cols, alphas)
        if cut_at is not None and cut_at >= 6:
            cols, alphas = cols[:cut_at + 1], alphas[:cut_at + 1]
            info["cut_after"] = cut_at
        if job.get("loop"):
            k = max(2, min(6, len(frames) // 8))
            i, j, d = loop_window(cols, alphas, max(12, len(frames) // 3), k)
            cols, alphas = looped(cols, alphas, i, j, k)
            pos = np.linspace(0, len(cols) - 1, n).tolist()
            info.update(loop={"start": i, "end": j, "seam": None if d is None else round(d, 4)})
        else:
            pos, t = oneshot_positions(alphas, n)
            info.update(t)
        info["frames_used"] = [round(x, 2) for x in pos]
        cols, alphas = sample(cols, alphas, pos)
        x0, y0, side = square_box(alphas.max(0))
        info["crop"] = [x0, y0, side]
        cells = [to_cell(crop(c, x0, y0, side), crop(a, x0, y0, side), cell) for c, a in zip(cols, alphas)]
        cells_c, cells_a = [c for c, _ in cells], [a for _, a in cells]
        if not job.get("loop"):
            g = int(job.get("grow_in", 0))
            for q in range(min(g, n - 1)):
                w = (q + 1) / (g + 1)
                c2, a2 = scaled(cells_c[g], cells_a[g], 0.3 + 0.7 * w)
                cells_c[q], cells_a[q] = c2, a2 * (0.5 + 0.5 * w)
            nf = max(1, int(round(n * float(job.get("fade", 0.25)))))
            for q in range(n - nf, n):
                w = (n - q - 1) / nf  # 1 -> 0 over the last frames
                cells_a[q] = cells_a[q] * (w * w * (3 - 2 * w))

    col = atlas(cells_c, grid, cell)
    a = atlas([x[..., None] for x in cells_a], grid, cell)[..., 0]
    save_rgba(out, col, a)
    comp = [composite(c, x, blend) for c, x in zip(cells_c, cells_a)]
    prev = atlas(comp, grid, cell)
    for r in range(1, grid[1]):
        prev[r * cell, :] = 0.3
    for q in range(1, grid[0]):
        prev[:, q * cell] = 0.3
    Image.fromarray((prev * 255).astype(np.uint8)).save(out.with_name(out.stem + "_preview.png"))
    big = [Image.fromarray((cv2.resize(f, (256, 256), interpolation=cv2.INTER_LINEAR) * 255).astype(np.uint8)) for f in comp]
    ms = 1000 // 24 if mode != "sprites" else 400
    big[0].save(out.with_name(out.stem + ".gif"), save_all=True, append_images=big[1:], duration=ms, loop=0)
    info["coverage_peak"] = round(float(max((x > 0.04).mean() for x in cells_a)), 3)
    out.with_name(out.stem + "_sheet.json").write_text(json.dumps(info, indent=1), encoding="utf-8")
    return {"ok": True, "out": str(out), **info}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", required=True)
    a = ap.parse_args()
    jobs = json.loads(Path(a.jobs).read_text(encoding="utf-8"))["jobs"]
    for job in jobs:
        try:
            print(json.dumps(run(job)), flush=True)
        except Exception as e:  # noqa: BLE001
            import traceback
            traceback.print_exc()
            print(json.dumps({"ok": False, "out": job.get("out"), "error": f"{type(e).__name__}: {e}"[:600]}), flush=True)


if __name__ == "__main__":
    sys.exit(main())
