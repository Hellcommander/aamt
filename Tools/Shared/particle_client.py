#!/usr/bin/env python3
"""Particle stage: a text description -> a game-ready particle texture (animated flipbook or a set of sprites) plus a
ready-to-use emitter layer for it. Nothing is drawn procedurally: every pixel comes from the image and video models.

  keyframe  SD3.5 (:1338)    the effect at its peak on pure black (glows, fire, smoke), or solid
                             pieces on a plain backdrop (debris)                          key.png / key_<n>.png
  video     Wan2.2-TI2V-5B   key.png set in motion ("flares outward, breaks up, fades")  clip.mp4
  sheet     fx_frames.py     alpha from brightness (or a BiRefNet cut-out for solid pieces), one shared crop,
                             frames picked (one-shots) or a cycle cut and cross-faded (loops), packed into a
                             flipbook atlas, frame 0 top-left                              <name>.png, _preview.png, .gif
  effect                     a particle-effect entry using the atlas (Chimera's "particles" schema: texture, grid,
                             blend, layer motion); other engines read grid/blend from <name>_sheet.json  <name>_effect.json

    python particle_client.py --status
    python particle_client.py --presets
    python particle_client.py fx_out --preset explosion --name green_blast --desc "a burst of green plasma fire"
    python particle_client.py fx_out --recipes recipes.json [--only video,sheet] [--redo sheet]

recipes.json: [{"name": "green_blast", "preset": "explosion", "desc": "...", "motion": "...", "seed": 3,
                "layer": {"color": "#A0FF80"}}, ...]   (any preset field can be overridden per recipe)

Weights are fetched on first use as plain folders under <HF_HOME>/local (WinError 1314 rules out hub symlinks):
Wan2.2-TI2V-5B (Diffusers parts + the Q8_0 GGUF transformer, shared with the animate stage) and BiRefNet (MIT) for
cut-outs, whose model code also needs timm and kornia in the animation venv (installed with uv when missing).
Every GPU step takes the AAMT GPU lock; SD and TRELLIS are stopped before video unless AAMT_KEEP_SERVERS=1.
Budget on the 11 GB 2080 Ti: keyframe ~20 s, clip ~1-2 min at 480x480, sheet seconds. See PARTICLES.md.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

_SHARED = Path(__file__).resolve().parent
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from anim_client import _env, _free_gpu, _py, _run  # noqa: E402  (same venv, env and server handling)

try:
    from gpu_hub import acquire_gpu
except Exception:  # pragma: no cover
    from contextlib import contextmanager

    @contextmanager
    def acquire_gpu(label, timeout=None, poll=2.0, enabled=True):  # type: ignore
        yield

_FX = _SHARED / "particles"
_WAN = _SHARED / "anim" / "wan_video.py"
LOCAL = Path(os.environ.get("HF_HOME") or r"D:\hf-cache") / "local"
VIDEO_SIZE = int(os.environ.get("AAMT_PARTICLE_VIDEO_SIZE") or 480)  # square; multiple of 32. 480^2 ~ 640x352's cost

KEY_BLACK = ("{desc}. A single visual effect element, centred with empty space around it, isolated on a pure black "
             "background, glowing, game VFX, high detail, no ground, no scenery, no text")
KEY_BACKDROP = ("{desc}. A single object, centred with empty space around it, isolated on a plain flat light grey "
                "background, studio lighting, no shadow, high detail, no text")
KEY_NEGATIVE = ("text, watermark, signature, border, frame, ground, floor, horizon, landscape, scenery, room, people, "
                "character, cropped, cut off, multiple separate objects, busy background")
# No "fades into darkness": Wan answers that with a hard cut to a new, half-invented scene. The clip keeps the effect
# alive and the sheet's own fade ends it.
VIDEO_SUFFIX = (" The effect stays centred in the frame. Pure black background, static camera, nothing else in frame.")
VIDEO_NEGATIVE = ("text, watermark, subtitles, worst quality, low quality, jpeg artifacts, blurry, camera movement, "
                  "camera pan, zoom, cut, scene change, background scenery, ground, floor, people, characters, "
                  "frame border, static image, frozen")

# Each preset: the image prompt (desc), what the clip does (motion), how the sheet is cut, and the emitter layer it
# suits. Colours in "layer" tint the texture: white-tinted sheets take the palette, baked ones keep their own colour.
PRESETS: Dict[str, Dict[str, Any]] = {
    "explosion": {
        "kind": "flipbook", "blend": "add", "tint": "baked", "grow_in": 3, "grid": [6, 6],
        "desc": "a violent fiery explosion, a billowing fireball of orange and yellow flame with glowing embers",
        "motion": "The fireball erupts outward violently, flames roll and churn as it keeps swelling, slowly "
                  "darkening into billowing smoke with glowing embers. Continuous, energetic motion.",
        "layer": {"count": 1, "life": [0.9], "speed": [0], "size": [2.4], "sizeCurve": "flat", "shape": "point",
                  "color": "#FFFFFF"},
    },
    "impact": {
        "kind": "flipbook", "blend": "add", "tint": "white", "grow_in": 1, "grid": [5, 5],
        "desc": "a bright energy impact flash, a burst of white light with radiating spikes and sparks",
        "motion": "The impact flash bursts outward, sparks streak away from the centre and the light spreads and "
                  "dims. Very fast, continuous motion.",
        "layer": {"count": 1, "life": [0.35], "speed": [0], "size": [1.6], "sizeCurve": "flat", "shape": "point",
                  "color": "#FFE08A"},
    },
    "smoke_puff": {
        "kind": "flipbook", "blend": "alpha", "tint": "white", "gamma": 0.8, "grid": [6, 6],
        "desc": "a small round puff of thick white smoke, a soft billowing cloud of vapour, the whole cloud visible "
                "with black space on every side",
        "motion": "The smoke cloud slowly billows and rolls outward, expanding and thinning, wisps curling at "
                  "its edges. Continuous gentle motion.",
        "layer": {"count": 6, "life": [1.2, 1.8], "speed": [0.3, 0.8], "size": [0.9, 1.5], "sizeCurve": "grow",
                  "spin": [-40, 40], "shape": "hemisphere", "radius": 0.4, "color": "#B8B8C0", "alpha": 0.7},
    },
    "electric": {
        "kind": "flipbook", "blend": "add", "tint": "white", "grid": [4, 4],
        "desc": "a crackling burst of blue-white electricity, jagged branching lightning arcs",
        "motion": "Electric arcs flicker and jump rapidly, branching and crackling with bright flashes, each "
                  "arc changing shape every moment. Fast, energetic motion.",
        "layer": {"count": 3, "life": [0.16, 0.28], "speed": [0], "size": [0.9, 1.4], "randomFrame": True,
                  "sizeCurve": "flat", "shape": "sphere", "radius": 0.25, "color": "#9FD8FF"},
    },
    "magic_burst": {
        "kind": "flipbook", "blend": "add", "tint": "white", "grow_in": 2, "grid": [6, 6],
        "desc": "a radiant burst of magical energy, swirling glowing light with sparkles and wisps",
        "motion": "The magical energy flares outward in a swirling ring of light while sparkles spiral away from "
                  "the centre. Continuous, flowing motion.",
        "layer": {"count": 1, "life": [0.8], "speed": [0], "size": [2.0], "sizeCurve": "flat", "shape": "point",
                  "color": "#C080FF"},
    },
    "flame_loop": {
        "kind": "flipbook", "blend": "add", "tint": "baked", "loop": True, "grid": [6, 6],
        "desc": "a single burning flame, a tall flickering tongue of orange fire",
        "motion": "The flame flickers and dances, licking upward continuously and steadily in place.",
        "layer": {"count": 0, "rate": 10, "duration": 1.0, "life": [0.5, 0.8], "speed": [0.3, 0.6],
                  "size": [0.6, 0.9], "sizeCurve": "pulse", "shape": "disc", "radius": 0.25, "color": "#FFFFFF"},
    },
    "energy_orb": {
        "kind": "flipbook", "blend": "add", "tint": "white", "loop": True, "grid": [6, 6],
        "desc": "a glowing orb of crackling plasma energy with swirling filaments",
        "motion": "The orb pulses and swirls in place, energy filaments churning around its surface continuously.",
        "layer": {"count": 1, "life": [1.0], "speed": [0], "size": [1.0], "sizeCurve": "pop", "shape": "point",
                  "color": "#6FE3FF"},
    },
    "shards": {
        "kind": "sprites", "blend": "alpha", "tint": "baked", "matte": "birefnet", "count": 4, "grid": [2, 2],
        "desc": "a single jagged shard of broken dark stone, sharp angular rock fragment",
        "layer": {"count": 14, "life": [0.6, 1.0], "speed": [2.5, 4.5], "size": [0.12, 0.24], "gravity": 1.5,
                  "spin": [-360, 360], "randomFrame": True, "shape": "hemisphere", "radius": 0.2, "color": "#FFFFFF"},
    },
    "glyph": {
        "kind": "sprites", "blend": "add", "tint": "white", "count": 4, "grid": [2, 2],
        "desc": "a glowing magic rune circle, an intricate arcane sigil drawn in lines of light, seen from directly above",
        "layer": {"count": 1, "life": [0.9], "speed": [0], "size": [2.4], "sizeCurve": "pop", "flat": True,
                  "ground": True, "spin": [-30, 30], "randomFrame": True, "shape": "point", "color": "#FFE090"},
    },
}


# ---- installs -------------------------------------------------------------------------------------------------------

def _venv_has(*mods: str) -> bool:
    code = "import importlib.util,sys; sys.exit(0 if all(importlib.util.find_spec(m) for m in sys.argv[1:]) else 1)"
    return subprocess.run([str(_py()), "-I", "-c", code, *mods], env=_env(), capture_output=True).returncode == 0


def _venv_download(code: str, label: str) -> None:
    _run([_py(), "-I", "-c", code], label, timeout=6 * 3600)


def status() -> Dict[str, Any]:
    return {
        "anim_venv": _py().exists(),
        "wan": (LOCAL / "Wan2.2-TI2V-5B-Diffusers" / "model_index.json").exists()
               and (LOCAL / "Wan2.2-TI2V-5B-GGUF" / "Wan2.2-TI2V-5B-Q8_0.gguf").exists(),
        "birefnet": (LOCAL / "BiRefNet" / "model.safetensors").exists(),
        "matte_deps": _py().exists() and _venv_has("timm", "kornia"),
    }


def ensure_video() -> None:
    """Wan2.2-TI2V-5B: the Diffusers repo without its 20 GB fp32 transformer, plus the Q8_0 GGUF transformer."""
    if not _py().exists():
        raise RuntimeError(f"animation venv missing: {_py()} (see ANIMATION.md)")
    if status()["wan"]:
        return
    _venv_download(
        "from huggingface_hub import snapshot_download, hf_hub_download\n"
        f"snapshot_download('Wan-AI/Wan2.2-TI2V-5B-Diffusers', local_dir=r'{LOCAL / 'Wan2.2-TI2V-5B-Diffusers'}',"
        " ignore_patterns=['transformer/*'])\n"
        "hf_hub_download('QuantStack/Wan2.2-TI2V-5B-GGUF', 'Wan2.2-TI2V-5B-Q8_0.gguf',"
        f" local_dir=r'{LOCAL / 'Wan2.2-TI2V-5B-GGUF'}')\n", "download Wan2.2-TI2V-5B")


def ensure_matte() -> None:
    """BiRefNet weights + code, and the packages that code imports."""
    if not _venv_has("timm", "kornia"):
        uv = shutil.which("uv") or str(Path.home() / ".local" / "bin" / "uv.exe")
        _run([uv, "pip", "install", "--python", _py(), "timm", "kornia"], "install timm + kornia", timeout=1800)
    if not status()["birefnet"]:
        _venv_download(f"import sys; sys.path.insert(0, r'{_FX}'); import matte; print(matte.download())",
                       "download BiRefNet")


# ---- recipe ---------------------------------------------------------------------------------------------------------

def recipe(r: Dict[str, Any]) -> Dict[str, Any]:
    """A recipe merged over its preset; layer dicts merge key by key."""
    base = copy.deepcopy(PRESETS[r.get("preset", "explosion")])
    layer = {**base.get("layer", {}), **r.get("layer", {})}
    base.update({k: v for k, v in r.items() if k != "layer"})
    base["layer"] = layer
    base.setdefault("matte", "luma")
    base.setdefault("seed", 1)
    if not base.get("name"):
        raise ValueError("a recipe needs a name")
    return base


def _key_prompt(r: Dict[str, Any]) -> str:
    return (KEY_BACKDROP if r["matte"] == "birefnet" else KEY_BLACK).format(desc=r["desc"].rstrip(". "))


# ---- stages ---------------------------------------------------------------------------------------------------------

KEY_TRIES = 4


def _edge_touch(png: Path) -> float:
    """Mean brightness of the outer 3% of a key drawn on black: high means the effect runs off the canvas and would
    end in a straight line."""
    import numpy as np
    from PIL import Image

    v = np.asarray(Image.open(png).convert("RGB"), np.float32).max(-1) / 255.0
    b = max(2, v.shape[0] * 3 // 100)
    return float(np.concatenate([v[:b].ravel(), v[-b:].ravel(), v[:, :b].ravel(), v[:, -b:].ravel()]).mean())


def keyframes(rs: List[Dict[str, Any]], work: Path, redo: bool = False) -> None:
    from ai_resources import make_image

    for r in rs:
        w = work / r["name"]
        w.mkdir(parents=True, exist_ok=True)
        n = int(r.get("count", 1)) if r["kind"] == "sprites" else 1
        for i in range(n):
            out = w / (f"key_{i}.png" if r["kind"] == "sprites" else "key.png")
            if out.exists() and not redo:
                continue
            for attempt in range(KEY_TRIES):
                make_image(_key_prompt(r), out, negative_prompt=KEY_NEGATIVE, width=1024, height=1024, steps=28,
                           guidance_scale=6.0, seed=int(r["seed"]) * 100 + i + 1000 * attempt)
                edge = _edge_touch(out)
                if r["matte"] == "birefnet" or edge < 0.12:
                    break
                print(f"[FX] {out.parent.name}/{out.name} runs off the canvas (edge {edge:.2f}), re-drawing",
                      file=sys.stderr, flush=True)


def _framed_key(w: Path, scale: float) -> Path:
    """key.png shrunk onto black (key_video.png): SD fills the canvas, and an effect touching the frame edge has no room
    to grow and gets cut off flat."""
    from PIL import Image

    from PIL import ImageDraw, ImageFilter

    out = w / "key_video.png"
    im = Image.open(w / "key.png").convert("RGB")
    n = round(im.width * scale)
    canvas = Image.new("RGB", im.size, (0, 0, 0))
    small = im.resize((n, n), Image.LANCZOS)
    f = max(4, n // 16)  # feather the key's own border too, in case it still touches its edge
    mask = Image.new("L", (n, n), 0)
    ImageDraw.Draw(mask).rectangle([f, f, n - 1 - f, n - 1 - f], fill=255)
    canvas.paste(small, ((im.width - n) // 2, (im.height - n) // 2), mask.filter(ImageFilter.GaussianBlur(f / 2)))
    canvas.save(out)
    return out


def videos(rs: List[Dict[str, Any]], work: Path, redo: bool = False, steps: int = 20) -> None:
    jobs = []
    for r in rs:
        if r["kind"] != "flipbook":
            continue
        w = work / r["name"]
        if (w / "clip.mp4").exists() and not redo:
            continue
        jobs.append({"image": str(_framed_key(w, float(r.get("key_scale", 0.72)))), "prompt": r["motion"].rstrip() + VIDEO_SUFFIX,
                     "out": str(w / "clip.mp4"), "frames": int(r.get("frames", 49)), "seed": int(r["seed"])})
    if not jobs:
        return
    ensure_video()
    _free_gpu()
    spec = work / "_video_jobs.json"
    spec.write_text(json.dumps({"width": VIDEO_SIZE, "height": VIDEO_SIZE, "model": "base", "steps": steps,
                                "guidance": 5.0, "negative": VIDEO_NEGATIVE, "jobs": jobs},
                               indent=1), encoding="utf-8")
    with acquire_gpu(f"Wan2.2 particles x{len(jobs)}"):
        out = _run([_py(), "-I", _WAN, "--jobs", spec], f"particle video x{len(jobs)}", timeout=6 * 3600)
    bad = [json.loads(l) for l in out.splitlines() if l.startswith('{"ok": false')]
    if bad:
        raise RuntimeError(f"video failed: {bad}")


def sheets(rs: List[Dict[str, Any]], work: Path, out_dir: Path, cell: int = 128) -> List[Dict[str, Any]]:
    jobs = []
    for r in rs:
        w = work / r["name"]
        job = {"mode": r["kind"], "out": str(out_dir / f"{r['name']}.png"), "grid": r["grid"],
               "cell": int(r.get("cell", cell)), "matte": r["matte"], "tint": r["tint"], "blend": r["blend"],
               "loop": bool(r.get("loop")), "grow_in": int(r.get("grow_in", 0)), "gamma": float(r.get("gamma", 1.0)),
               "fade": float(r.get("fade", 0.25))}
        if r["kind"] == "sprites":
            job["images"] = [str(p) for p in sorted(w.glob("key_*.png"))]
        else:
            job["video"] = str(w / "clip.mp4")
        jobs.append(job)
    if any(j["matte"] == "birefnet" for j in jobs):
        ensure_matte()
        _free_gpu()
    spec = work / "_sheet_jobs.json"
    spec.write_text(json.dumps({"jobs": jobs}, indent=1), encoding="utf-8")
    with acquire_gpu(f"particle sheets x{len(jobs)}", enabled=any(j["matte"] == "birefnet" for j in jobs)):
        out = _run([_py(), "-I", _FX / "fx_frames.py", "--jobs", spec], f"particle sheets x{len(jobs)}")
    res = [json.loads(l) for l in out.splitlines() if l.startswith("{")]
    bad = [x for x in res if not x.get("ok")]
    if bad:
        raise RuntimeError(f"sheet failed: {bad}")
    return res


def effect(r: Dict[str, Any], sheet: Dict[str, Any], texture: Optional[str] = None) -> Dict[str, Any]:
    """The emitter entry for this texture, in Chimera's particle-effect schema (see the Chimera class loader's
    CustomVfx.cs): id, layers[] with texture/grid/blend plus the preset's motion. `texture` is the path the game
    should load, relative to the data file (default: the bare file name)."""
    layer = {"texture": texture or Path(sheet["out"]).name, "blend": r["blend"]}
    grid = sheet["grid"]
    if grid[0] * grid[1] > 1:
        layer["grid"] = grid
    layer.update(r["layer"])
    fx = {"id": r.get("id") or f"fx_{r['name']}", "layers": [layer]}
    if r.get("light"):
        fx["light"] = r["light"]
    return fx


def make_particles(recipes: List[Dict[str, Any]], out_dir: Path, *, work: Optional[Path] = None,
                   only: Optional[List[str]] = None, redo: Optional[List[str]] = None, cell: int = 128,
                   steps: int = 20) -> List[Dict[str, Any]]:
    """Recipes -> <out_dir>/<name>.png atlases + <name>_effect.json emitters. Each stage is cached in
    work/<name>/ (key.png, clip.mp4); `only`/`redo` take stage names: key, video, sheet."""
    out_dir = Path(out_dir)
    work = Path(work or out_dir / "_work")
    rs = [recipe(r) for r in recipes]
    only, redo = set(only or ["key", "video", "sheet"]), set(redo or [])
    if "key" in only:
        keyframes(rs, work, "key" in redo)
    if "video" in only:
        videos(rs, work, "video" in redo, steps=steps)
    results = []
    if "sheet" in only:
        out_dir.mkdir(parents=True, exist_ok=True)
        for r, sh in zip(rs, sheets(rs, work, out_dir, cell)):
            fx = effect(r, sh)
            p = out_dir / f"{r['name']}_effect.json"
            p.write_text(json.dumps(fx, indent=1), encoding="utf-8")
            results.append({"name": r["name"], "texture": sh["out"], "effect": str(p), "sheet": sh,
                            "preview": str(Path(sh["out"]).with_name(r["name"] + "_preview.png")),
                            "gif": str(Path(sh["out"]).with_suffix(".gif"))})
    return results


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out_dir", nargs="?")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--presets", action="store_true")
    ap.add_argument("--recipes", help="JSON list of recipes")
    ap.add_argument("--preset", default="explosion", choices=sorted(PRESETS))
    ap.add_argument("--name")
    ap.add_argument("--desc")
    ap.add_argument("--motion")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--work")
    ap.add_argument("--only", help="comma list of key,video,sheet")
    ap.add_argument("--redo", help="comma list of key,video,sheet")
    ap.add_argument("--cell", type=int, default=128)
    ap.add_argument("--steps", type=int, default=20)
    ap.add_argument("--install", action="store_true", help="fetch every weight and package the stage can use, then exit")
    a = ap.parse_args(argv)
    if a.status:
        print(json.dumps(status(), indent=1))
        return 0
    if a.presets:
        for k, v in PRESETS.items():
            print(f"{k:12} {v['kind']:9} {v['blend']:5} {v['tint']:6} {'loop' if v.get('loop') else '':5} {v['desc']}")
        return 0
    if a.install:
        ensure_video()
        ensure_matte()
        print(json.dumps(status(), indent=1))
        return 0
    if not a.out_dir:
        ap.error("out_dir is required")
    if a.recipes:
        recipes = json.loads(Path(a.recipes).read_text(encoding="utf-8"))
    else:
        if not a.name:
            ap.error("--name (or --recipes) is required")
        r = {"name": a.name, "preset": a.preset, "seed": a.seed}
        if a.desc:
            r["desc"] = a.desc
        if a.motion:
            r["motion"] = a.motion
        recipes = [r]
    res = make_particles(recipes, Path(a.out_dir), work=Path(a.work) if a.work else None,
                         only=a.only.split(",") if a.only else None, redo=a.redo.split(",") if a.redo else None,
                         cell=a.cell, steps=a.steps)
    for x in res:
        print(json.dumps({k: x[k] for k in ("name", "texture", "effect", "preview", "gif")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
