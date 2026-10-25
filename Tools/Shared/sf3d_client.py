#!/usr/bin/env python3
"""Stable Fast 3D (SF3D): image -> textured GLB in seconds, as a fast alternative to TRELLIS.

Optimised for agents and batches:
  * one model load per call, however many images (sf3d_batch.py in the SF3D install);
  * frees the shared 11 GB GPU first (stops the SD3.5 and TRELLIS servers unless AAMT_KEEP_SERVERS=1) and holds the
    AAMT GPU lock while it runs;
  * accepts concepts on plain white (cuts them out itself) or RGBA cut-outs;
  * runs in its own venv, so nothing in this interpreter needs torch or sf3d.

Python:
    from ai_resources import make_fast_mesh, make_fast_meshes
    make_fast_mesh("concept.png", "out.glb")                                  # one
    make_fast_meshes([("a.png", "a.glb"), ("b.png", "b.glb")], bake_res=512)  # many, one load
CLI:
    python sf3d_client.py a.png b.png --out-dir meshes [--bake-res 512] [--remesh none|triangle|quad] [--vertex-count N]

When to use which: SF3D is quick (seconds per mesh after a ~30 s load) and good for props and simple shapes;
TRELLIS (make_mesh) is slower but better on complex shapes. Install path: AAMT_SF3D_HOME (default E:\\tools\\stable-fast-3d).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

_SHARED = Path(__file__).resolve().parent
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

try:
    from gpu_hub import acquire_gpu
except Exception:  # hub is optional
    import contextlib

    def acquire_gpu(label, timeout=None, poll=2.0, enabled=True):  # type: ignore
        return contextlib.nullcontext()


def sf3d_home() -> Path:
    return Path(os.environ.get("AAMT_SF3D_HOME") or r"E:\tools\stable-fast-3d")


def _python() -> Path:
    return sf3d_home() / "venv" / "Scripts" / "python.exe"


def available() -> bool:
    return _python().exists() and (sf3d_home() / "sf3d_batch.py").exists()


def _free_gpu() -> None:
    """SD and TRELLIS resident at once with SF3D overflow the card: stop them unless told not to."""
    if os.environ.get("AAMT_KEEP_SERVERS") == "1":
        return
    try:
        from sd_server_lifecycle import stop_sd_server
        stop_sd_server(force=True)
    except Exception as exc:  # noqa: BLE001
        print(f"[SF3D] could not stop SD: {exc}", file=sys.stderr)
    try:
        from trellis_http_client import stop_server
        stop_server(force=True)
    except Exception as exc:  # noqa: BLE001
        print(f"[SF3D] could not stop TRELLIS: {exc}", file=sys.stderr)


def cutout(src: Path, dst: Path) -> Path:
    """An RGBA cut-out: kept as is if it already has transparency, else the plain white backdrop is flooded away
    from the borders (white highlights inside the object survive)."""
    from PIL import Image, ImageChops, ImageDraw, ImageFilter

    img = Image.open(src)
    if img.mode == "RGBA" and img.split()[-1].getextrema()[0] < 250:
        img.save(dst)
        return dst
    rgb = img.convert("RGB")
    r, g, b = rgb.split()
    hi = ImageChops.lighter(ImageChops.lighter(r, g), b)
    lo = ImageChops.darker(ImageChops.darker(r, g), b)
    near = ImageChops.multiply(hi.point(lambda v: 255 if v > 185 else 0), ImageChops.subtract(hi, lo).point(lambda v: 255 if v < 28 else 0))
    w, h = near.size
    for x, y in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1), (w // 2, 0), (w // 2, h - 1), (0, h // 2), (w - 1, h // 2)]:
        if near.getpixel((x, y)) == 255:
            ImageDraw.floodfill(near, (x, y), 128)
    alpha = ImageChops.invert(near.point(lambda v: 255 if v == 128 else 0)).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1.0))
    out = rgb.convert("RGBA")
    out.putalpha(alpha)
    out.save(dst)
    return dst


def generate_fast_meshes(pairs: Sequence[Tuple[Path, Path]], *, bake_res: int = 512, remesh: str = "none",
                         vertex_count: int = -1, foreground_ratio: float = 0.85, timeout: float = 3600) -> List[Dict[str, Any]]:
    """Meshes every (image, output .glb) pair in one SF3D run. Returns one result dict per pair ("ok", "glb"/"error")."""
    if not available():
        raise RuntimeError(f"Stable Fast 3D not found at {sf3d_home()} (set AAMT_SF3D_HOME)")
    pairs = [(Path(i), Path(o)) for i, o in pairs]
    with tempfile.TemporaryDirectory(prefix="aamt_sf3d_") as tmp:
        jobs = []
        for n, (img, out) in enumerate(pairs):
            jobs.append({"image": str(cutout(img, Path(tmp) / f"in{n}.png")), "out": str(out.resolve())})
        spec = Path(tmp) / "jobs.json"
        spec.write_text(json.dumps({"bake_res": bake_res, "remesh": remesh, "vertex_count": vertex_count,
                                    "foreground_ratio": foreground_ratio, "jobs": jobs}), encoding="utf-8")
        _free_gpu()
        env = dict(os.environ)
        env.pop("NoDefaultCurrentDirectoryInExePath", None)  # agent shells set it; breaks child launchers
        with acquire_gpu(f"SF3D x{len(jobs)}"):
            proc = subprocess.run([str(_python()), str(sf3d_home() / "sf3d_batch.py"), "--jobs", str(spec)],
                                  cwd=str(sf3d_home()), env=env, capture_output=True, text=True, timeout=timeout)
    results, by_image = [], {}
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get("summary"):
            print(f"[SF3D] {d.get('done')}/{d.get('of')} meshes, load {d.get('load_s')}s, total {d.get('total_s')}s, peak {d.get('peak_vram_mb')} MB", file=sys.stderr)
        else:
            by_image[d.get("image")] = d
    for job, (img, _) in zip(jobs, pairs):
        r = by_image.get(job["image"]) or {"ok": False, "error": (proc.stderr or "no output")[-400:]}
        r["source"] = str(img)
        results.append(r)
    return results


def generate_fast_mesh(image: Path, output: Path, **kwargs: Any) -> Path:
    """One image -> one .glb. Raises if SF3D fails."""
    r = generate_fast_meshes([(Path(image), Path(output))], **kwargs)[0]
    if not r.get("ok"):
        raise RuntimeError(f"SF3D failed on {image}: {r.get('error')}")
    return Path(output)


def main(argv: Iterable[str] = None) -> int:
    ap = argparse.ArgumentParser(description="Stable Fast 3D: images -> GLBs (one model load)")
    ap.add_argument("images", nargs="+", type=Path)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--bake-res", type=int, default=512)
    ap.add_argument("--remesh", choices=["none", "triangle", "quad"], default="none")
    ap.add_argument("--vertex-count", type=int, default=-1)
    a = ap.parse_args(list(argv) if argv is not None else None)
    a.out_dir.mkdir(parents=True, exist_ok=True)
    res = generate_fast_meshes([(i, a.out_dir / (i.stem + ".glb")) for i in a.images], bake_res=a.bake_res, remesh=a.remesh, vertex_count=a.vertex_count)
    for r in res:
        print(json.dumps(r))
    return 0 if all(r.get("ok") for r in res) else 1


if __name__ == "__main__":
    raise SystemExit(main())
