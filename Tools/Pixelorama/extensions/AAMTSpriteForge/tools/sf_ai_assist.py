#!/usr/bin/env python3
"""AAMT Sprite Forge - opt-in "AI assist": one sprite frame -> SD3.5 img2img -> pixel frame.

Called by the Pixelorama panel (AI assist section) or directly by agents:

  python sf_ai_assist.py --in frame.png --out ai.png --prompt "glowing arcane crystal, pixel art" \
      [--strength 0.45] [--steps 24] [--guidance 5] [--seed 0] [--sd-size 512] \
      [--palette pal.gpl] [--status status.json] [--api http://127.0.0.1:1338]

- Uses the GPU: takes the shared AAMT GPU lock (Tools/Shared/gpu_hub.py) around the
  request, checks free VRAM first, and never starts the SD server itself
  (start it with Tools/Start-StableDiffusionServer.ps1).
- Input is a canvas-sized RGBA frame. It is nearest-upscaled onto a white square,
  sent as img2img, box-downscaled back to the canvas size, and re-masked with the
  input's alpha (so the silhouette and Starbound cell size stay intact).
- Writes --out (RGBA PNG) and a JSON status (stdout and --status file). Exit 0 on success.
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

TOOLS_ROOT = Path(__file__).resolve().parents[4]  # .../Tools
SHARED = TOOLS_ROOT / "Shared"
if str(SHARED) not in sys.path:
    sys.path.insert(0, str(SHARED))

try:
    from gpu_hub import acquire_gpu  # type: ignore
except Exception:  # pragma: no cover - toolkit not found: still serialize nothing
    import contextlib

    def acquire_gpu(label, timeout=None, poll=2.0, enabled=True):  # type: ignore
        return contextlib.nullcontext()


def free_vram_mb() -> Optional[int]:
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
            text=True, timeout=15,
        )
        return int(out.strip().splitlines()[0])
    except Exception:
        return None


def sd_status(api: str) -> Dict[str, Any]:
    try:
        with urllib.request.urlopen(api.rstrip("/") + "/ping", timeout=8) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as exc:
        return {"status": "down", "error": str(exc)}


def load_gpl(path: Path) -> List[Tuple[int, int, int]]:
    cols = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or s.startswith("GIMP") or ":" in s:
            continue
        p = s.split()
        if len(p) >= 3 and all(x.isdigit() for x in p[:3]):
            cols.append((int(p[0]), int(p[1]), int(p[2])))
    return cols


def snap(img, pal: List[Tuple[int, int, int]]):
    if not pal:
        return img
    px = img.load()
    cache: Dict[Tuple[int, int, int], Tuple[int, int, int]] = {}
    for y in range(img.height):
        for x in range(img.width):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            k = (r, g, b)
            if k not in cache:
                cache[k] = min(pal, key=lambda c: (c[0] - r) ** 2 * 2 + (c[1] - g) ** 2 * 4 + (c[2] - b) ** 2 * 3)
            px[x, y] = (*cache[k], a)
    return img


def run(args: argparse.Namespace) -> Dict[str, Any]:
    from PIL import Image  # Pillow is a toolkit dependency

    t0 = time.time()
    src = Image.open(args.inp).convert("RGBA")
    w, h = src.size
    st = sd_status(args.api)
    if st.get("status") != "ok":
        return {"ok": False, "error": "SD server not reachable at %s (start Tools\\Start-StableDiffusionServer.ps1)" % args.api, "sd": st}
    # Another helper's SD batch in flight: wait for the server to go idle first.
    waited = 0.0
    while (st.get("generating") or int(st.get("inflight") or 0) > 0) and waited < args.wait_idle:
        time.sleep(5.0)
        waited += 5.0
        st = sd_status(args.api)
    if st.get("generating") or int(st.get("inflight") or 0) > 0:
        return {"ok": False, "error": f"SD server still busy after {waited:.0f}s (another batch running); retry later", "sd": st}
    vram = free_vram_mb()
    if vram is not None and vram < args.min_vram_mb and not st.get("loaded"):
        return {"ok": False, "error": f"only {vram} MB VRAM free (< {args.min_vram_mb}); try again later", "vram_free_mb": vram}

    size = max(64, (args.sd_size // 64) * 64)
    k = max(1, size // max(w, h))
    big = src.resize((w * k, h * k), Image.NEAREST)
    canvas = Image.new("RGBA", (size, size), (255, 255, 255, 255))
    ox, oy = (size - big.width) // 2, (size - big.height) // 2
    canvas.alpha_composite(big, (ox, oy))
    buf = io.BytesIO()
    canvas.convert("RGB").save(buf, "PNG")
    body = {
        "prompt": args.prompt,
        "negative_prompt": args.negative,
        "width": size, "height": size, "size": f"{size}x{size}",
        "steps": args.steps, "guidance_scale": args.guidance, "n": 1,
        "image": base64.b64encode(buf.getvalue()).decode("ascii"),
        "strength": args.strength,
    }
    if args.seed:
        body["seed"] = args.seed
    req = urllib.request.Request(
        args.api.rstrip("/") + "/v1/images/generations",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with acquire_gpu(f"SpriteForge img2img {Path(args.inp).name}", enabled=not args.no_gpu_lock):
        with urllib.request.urlopen(req, timeout=args.timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    b64 = None
    for item in payload.get("data") or []:
        if isinstance(item, dict) and item.get("b64_json"):
            b64 = item["b64_json"]
            break
    if not b64:
        return {"ok": False, "error": f"no image in SD reply (keys {list(payload)})"}
    gen = Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGBA")
    if gen.size != (size, size):
        gen = gen.resize((size, size), Image.LANCZOS)
    region = gen.crop((ox, oy, ox + big.width, oy + big.height))
    small = region.resize((w, h), Image.BOX)
    alpha = src.getchannel("A").point(lambda a: 255 if a > 0 else 0)
    small.putalpha(alpha)
    if args.palette:
        small = snap(small, load_gpl(Path(args.palette)))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    small.save(out)
    raw = out.with_name(out.stem + "_sd_raw.png")
    if args.keep_raw:
        gen.save(raw)
    return {
        "ok": True, "out": str(out), "size": [w, h], "sd_size": size, "upscale": k,
        "strength": args.strength, "steps": args.steps, "seed": args.seed,
        "raw": str(raw) if args.keep_raw else None, "vram_free_mb": vram,
        "secs": round(time.time() - t0, 2), "waited_for_sd_s": waited,
    }


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="AAMT Sprite Forge SD img2img assist (uses GPU)")
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--prompt", default="pixel art game sprite, clean shapes, readable silhouette")
    ap.add_argument("--negative", default="blurry, photo, text, watermark, background clutter")
    ap.add_argument("--strength", type=float, default=0.45)
    ap.add_argument("--steps", type=int, default=24)
    ap.add_argument("--guidance", type=float, default=5.0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--sd-size", type=int, default=512)
    ap.add_argument("--palette", default="")
    ap.add_argument("--api", default="http://127.0.0.1:1338")
    ap.add_argument("--timeout", type=float, default=1800.0)
    ap.add_argument("--min-vram-mb", type=int, default=2048)
    ap.add_argument("--wait-idle", type=float, default=900.0, help="max seconds to wait for a busy SD server")
    ap.add_argument("--keep-raw", action="store_true")
    ap.add_argument("--status", default="")
    ap.add_argument("--no-gpu-lock", action="store_true",
                    help="caller already holds the AAMT GPU lock (e.g. pixelorama_client sf-ai)")
    args = ap.parse_args(argv)
    try:
        result = run(args)
    except urllib.error.URLError as exc:
        result = {"ok": False, "error": f"SD request failed: {exc}"}
    except Exception as exc:  # report, never hang the panel
        result = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    text = json.dumps(result, indent=2)
    if args.status:
        Path(args.status).parent.mkdir(parents=True, exist_ok=True)
        tmp = Path(args.status + ".tmp")
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(args.status)
    print(text)
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
