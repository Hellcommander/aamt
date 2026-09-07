#!/usr/bin/env python3
"""
Generate Space-Time Vortex Qud tiles with nerijs/pixel-art-xl.

Best path for 16x24 map tiles (model card + SDXL limits):
  1. Generate at 512x768 (SDXL-usable; still "small" vs 1024)
  2. Nearest /8  -> 64x96  (pixel-art-xl pixelization)
  3. Nearest     -> 16x24  (vanilla Qud map size)

128x192 direct gen is too small for SDXL (blobs). 1024x1536 is heavier on 11GB VRAM.

HF cache defaults to E:\\hf-cache\\hub. Auth stays on default HF_HOME.
"""

from __future__ import annotations

import argparse
import gc
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import torch
from PIL import Image

_DEFAULT_HF_CACHE = Path(r"E:\hf-cache\hub")
_DEFAULT_HF_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("HUGGINGFACE_HUB_CACHE", str(_DEFAULT_HF_CACHE))
os.environ.setdefault("HF_HUB_CACHE", str(_DEFAULT_HF_CACHE))
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

QUD_MAP = (16, 24)
PIXEL_SCALE = 8

# Best default for 16x24: SDXL-usable canvas, then /8 then /4 nearest
MAP_GEN = (512, 768)
ICON_GEN = (512, 512)  # /8 -> 64x64 mutation/UI
ABILITY_GEN = (512, 512)

COMPARE_MAP_SIZES = [
    (256, 384),
    (512, 768),
    (768, 1152),
]

NEGATIVE = (
    "3d render, realistic, photo, blurry, soft, antialiased, gradient smear, "
    "noise, jpeg artifacts, text, watermark, frame, border, UI, "
    "complex background, scenery, landscape, creature, face, body"
)

MAP_PROMPT = (
    "pixel art, Caves of Qud 16x24 sprite, single hooked spacetime vortex spiral, "
    "cyan and white on black void, crisp hard pixels, simple flat colors, "
    "centered silhouette like a curling rift, no scenery"
)


def _to_qud_map(img: Image.Image, final: Tuple[int, int] = QUD_MAP) -> Image.Image:
    """pixel-art-xl /8 nearest, then nearest to exact Qud size."""
    w, h = img.size
    mid_w = max(1, w // PIXEL_SCALE)
    mid_h = max(1, h // PIXEL_SCALE)
    mid = img.resize((mid_w, mid_h), Image.Resampling.NEAREST)
    if mid.size != final:
        mid = mid.resize(final, Image.Resampling.NEAREST)
    return mid.convert("RGBA")


def _to_ui_tile(img: Image.Image) -> Image.Image:
    w, h = img.size
    return img.resize((max(1, w // PIXEL_SCALE), max(1, h // PIXEL_SCALE)), Image.Resampling.NEAREST).convert("RGBA")


def _knockout_bg(img: Image.Image, threshold: int = 28) -> Image.Image:
    img = img.convert("RGBA")
    px = img.load()
    w, h = img.size
    corners = [px[0, 0], px[w - 1, 0], px[0, h - 1], px[w - 1, h - 1]]
    br = sum(c[0] + c[1] + c[2] for c in corners) / 12
    bg = "dark" if br < 128 else "light"
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if bg == "dark" and r < threshold and g < threshold and b < threshold:
                px[x, y] = (r, g, b, 0)
            elif bg == "light" and r > 255 - threshold and g > 255 - threshold and b > 255 - threshold:
                px[x, y] = (r, g, b, 0)
    return img


def _upsample_preview(tile: Image.Image, scale: int = 8) -> Image.Image:
    return tile.resize((tile.width * scale, tile.height * scale), Image.Resampling.NEAREST)


def build_pipelines(device: str = "cuda", need_i2i: bool = False):
    """One SDXL load; optional img2img shares the same weights."""
    from diffusers import DiffusionPipeline, LCMScheduler, StableDiffusionXLImg2ImgPipeline

    model_id = "stabilityai/stable-diffusion-xl-base-1.0"
    lcm_lora_id = "latent-consistency/lcm-lora-sdxl"
    pixel_lora_id = "nerijs/pixel-art-xl"
    dtype = torch.float16 if device == "cuda" else torch.float32

    pipe_t2i = DiffusionPipeline.from_pretrained(
        model_id,
        torch_dtype=dtype,
        variant="fp16" if device == "cuda" else None,
        use_safetensors=True,
    )
    pipe_t2i.scheduler = LCMScheduler.from_config(pipe_t2i.scheduler.config)
    pipe_t2i.load_lora_weights(lcm_lora_id, adapter_name="lcm")
    pipe_t2i.load_lora_weights(pixel_lora_id, adapter_name="pixel")
    pipe_t2i.set_adapters(["lcm", "pixel"], adapter_weights=[1.0, 1.2])
    pipe_t2i.to(device=device, dtype=dtype)
    pipe_t2i.set_progress_bar_config(disable=False)

    pipe_i2i = None
    if need_i2i:
        pipe_i2i = StableDiffusionXLImg2ImgPipeline(**pipe_t2i.components)
        pipe_i2i.scheduler = pipe_t2i.scheduler
        pipe_i2i.to(device=device, dtype=dtype)
        pipe_i2i.set_progress_bar_config(disable=False)
    return pipe_t2i, pipe_i2i


def generate_one(
    pipe,
    prompt: str,
    *,
    width: int,
    height: int,
    seed: int,
    steps: int = 8,
    guidance: float = 1.5,
    init_image: Optional[Image.Image] = None,
    strength: float = 0.55,
) -> Image.Image:
    g = torch.Generator(device=pipe.device).manual_seed(seed)
    kwargs = dict(
        prompt=prompt,
        negative_prompt=NEGATIVE,
        num_inference_steps=steps,
        guidance_scale=guidance,
        generator=g,
    )
    if init_image is not None:
        ref = init_image.convert("RGB").resize((width, height), Image.Resampling.NEAREST)
        kwargs["image"] = ref
        kwargs["strength"] = strength
    else:
        kwargs["width"] = width
        kwargs["height"] = height
    return pipe(**kwargs).images[0]


def load_vanilla_ref() -> Optional[Image.Image]:
    p = Path(r"C:\Users\Arend\AppData\LocalLow\Freehold Games\CavesOfQud\_reports\_vortex_tile_compare\vanilla_spacetime_vortex.png")
    if p.exists():
        return Image.open(p).convert("RGBA")
    return None


def job_list(frames: int) -> List[Dict]:
    jobs: List[Dict] = []
    for i in range(frames):
        ang = int(i * (360 / frames))
        jobs.append(
            {
                "name": f"SpaceTimeVortex_frame{i:02d}.png",
                "kind": "map",
                "seed": 42000 + i,
                "prompt": f"{MAP_PROMPT}, spiral rotated {ang} degrees",
                "use_ref": True,
            }
        )
    for i in range(frames):
        ang = int(i * (360 / frames))
        jobs.append(
            {
                "name": f"BlackHole_frame{i:02d}.png",
                "kind": "map",
                "seed": 43000 + i,
                "prompt": (
                    f"pixel art, Caves of Qud sprite, black hole with thin blue accretion spiral, "
                    f"dark void center, hard pixels, flat colors, centered, rotation {ang}"
                ),
                "use_ref": True,
            }
        )
    for i in range(frames):
        ang = int(i * (360 / frames))
        jobs.append(
            {
                "name": f"WhiteHole_frame{i:02d}.png",
                "kind": "map",
                "seed": 44000 + i,
                "prompt": (
                    f"pixel art, Caves of Qud sprite, white hole bright yellow-white outward spiral, "
                    f"glowing core, hard pixels, flat colors, centered, rotation {ang}"
                ),
                "use_ref": False,
            }
        )
    jobs.extend(
        [
            {
                "name": "Space-Time Vortex_icon.png",
                "kind": "icon",
                "seed": 45001,
                "prompt": "pixel art icon, spacetime vortex spiral, cyan purple white, flat colors, black bg",
                "use_ref": False,
            },
            {
                "name": "VortexAbility_Aggressive.png",
                "kind": "ability",
                "seed": 45002,
                "prompt": "pixel art ability icon, aggressive black hole, red orange spiral, flat colors, black bg",
                "use_ref": False,
            },
            {
                "name": "VortexAbility_Defensive.png",
                "kind": "ability",
                "seed": 45003,
                "prompt": "pixel art ability icon, defensive white hole, blue cyan spiral, flat colors, black bg",
                "use_ref": False,
            },
            {
                "name": "VortexWarning_marker.png",
                "kind": "icon",
                "seed": 45004,
                "prompt": "pixel art warning marker, yellow exclamation tiny vortex, flat colors, black bg",
                "use_ref": False,
            },
        ]
    )
    for i, color in enumerate(("blue", "purple", "cyan")):
        jobs.append(
            {
                "name": f"VortexParticle_spark_{color}_frame00.png",
                "kind": "icon",
                "seed": 46000 + i,
                "prompt": f"pixel art tiny {color} spark fleck, flat colors, black bg",
                "use_ref": False,
            }
        )
    for i, name in enumerate(("swirl_blue", "swirl_white", "dot_yellow", "dot_orange")):
        jobs.append(
            {
                "name": f"VortexParticle_{name}_frame00.png",
                "kind": "icon",
                "seed": 46100 + i,
                "prompt": f"pixel art tiny particle {name.replace('_', ' ')}, flat colors, black bg",
                "use_ref": False,
            }
        )
    for i in range(3):
        jobs.append(
            {
                "name": f"VortexDistortion_{i:02d}.png",
                "kind": "icon",
                "seed": 47000 + i,
                "prompt": f"pixel art subtle cyan spacetime ripple overlay {i}, flat colors, black bg",
                "use_ref": False,
            }
        )
    return jobs


def kind_size(kind: str) -> Tuple[Tuple[int, int], str]:
    if kind == "map":
        return MAP_GEN, "map"
    if kind == "ability":
        return ABILITY_GEN, "ui"
    return ICON_GEN, "ui"


def run_compare(pipe_t2i, pipe_i2i, out: Path, ref: Optional[Image.Image], seed: int = 42000) -> None:
    out.mkdir(parents=True, exist_ok=True)
    print("Comparing map gen sizes for final 16x24 ...")
    for wh in COMPARE_MAP_SIZES:
        label = f"{wh[0]}x{wh[1]}"
        print(f"  t2i {label}")
        try:
            raw = generate_one(pipe_t2i, MAP_PROMPT, width=wh[0], height=wh[1], seed=seed)
            raw.save(out / f"raw_t2i_{label}.png")
            tile = _knockout_bg(_to_qud_map(raw))
            tile.save(out / f"tile16x24_t2i_{label}.png")
            _upsample_preview(tile).save(out / f"preview_t2i_{label}.png")
        except Exception as e:
            print(f"    FAIL t2i {label}: {e}")
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

        if ref is not None and pipe_i2i is not None:
            print(f"  i2i {label} (vanilla silhouette)")
            try:
                raw = generate_one(
                    pipe_i2i,
                    MAP_PROMPT,
                    width=wh[0],
                    height=wh[1],
                    seed=seed + 1,
                    init_image=ref,
                    strength=0.45,
                )
                raw.save(out / f"raw_i2i_{label}.png")
                tile = _knockout_bg(_to_qud_map(raw))
                tile.save(out / f"tile16x24_i2i_{label}.png")
                _upsample_preview(tile).save(out / f"preview_i2i_{label}.png")
            except Exception as e:
                print(f"    FAIL i2i {label}: {e}")
                gc.collect()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
    print(f"Compare writes: {out}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "mod_path",
        nargs="?",
        default=r"C:\Users\Arend\AppData\LocalLow\Freehold Games\CavesOfQud\Mods\Improved and Rebalanced Space Time Vortex",
    )
    ap.add_argument("--frames", type=int, default=16)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--compare", action="store_true", help="Try several sizes; write previews only")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--map-only", action="store_true")
    ap.add_argument("--skip-existing", action="store_true")
    ap.add_argument("--no-ref", action="store_true", help="Disable vanilla img2img for map tiles")
    ap.add_argument("--strength", type=float, default=0.45)
    ap.add_argument("--map-w", type=int, default=MAP_GEN[0])
    ap.add_argument("--map-h", type=int, default=MAP_GEN[1])
    args = ap.parse_args()

    map_gen = (args.map_w, args.map_h)

    mod = Path(args.mod_path)
    textures = mod / "Textures"
    textures.mkdir(parents=True, exist_ok=True)
    drafts = mod / "DesignDrafts" / "pixel_art_xl"
    drafts.mkdir(parents=True, exist_ok=True)
    ref = None if args.no_ref else load_vanilla_ref()

    print(f"Device: {args.device}")
    print(f"Map gen {map_gen} -> /8 nearest -> {QUD_MAP}")
    print(f"Vanilla ref: {'yes' if ref else 'no'}")

    need_i2i = (args.compare or not args.no_ref) and ref is not None
    print("Loading SDXL + LCM + nerijs/pixel-art-xl ...")
    pipe_t2i, pipe_i2i = build_pipelines(args.device, need_i2i=need_i2i)

    if args.compare:
        run_compare(pipe_t2i, pipe_i2i, drafts / "compare_16x24", ref)
        return 0

    jobs = job_list(args.frames)
    if args.smoke:
        jobs = [j for j in jobs if j["name"] == "SpaceTimeVortex_frame00.png"][:1]
    if args.map_only:
        jobs = [j for j in jobs if j["kind"] == "map"]

    ok = 0
    for n, job in enumerate(jobs, 1):
        dest = textures / job["name"]
        if args.skip_existing and dest.exists() and dest.stat().st_size > 0:
            print(f"[{n}/{len(jobs)}] skip {job['name']}")
            ok += 1
            continue

        if job["kind"] == "map":
            gen_wh, mode = map_gen, "map"
        else:
            gen_wh, mode = kind_size(job["kind"])
        use_ref = bool(job.get("use_ref")) and ref is not None and pipe_i2i is not None
        pipe = pipe_i2i if use_ref else pipe_t2i
        print(f"[{n}/{len(jobs)}] {job['name']} gen={gen_wh} mode={'i2i' if use_ref else 't2i'}")
        try:
            raw = generate_one(
                pipe,
                job["prompt"],
                width=gen_wh[0],
                height=gen_wh[1],
                seed=job["seed"],
                init_image=ref if use_ref else None,
                strength=args.strength,
            )
            raw.save(drafts / f"raw_{job['name']}")
            if mode == "map":
                tile = _knockout_bg(_to_qud_map(raw))
            else:
                tile = _knockout_bg(_to_ui_tile(raw))
            tile.save(dest)
            if job["name"].endswith("_frame00.png"):
                tile.save(textures / job["name"].replace("_frame00.png", "_frame.png"))
            ok += 1
        except Exception as e:
            print(f"  FAIL: {e}")
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    print(f"Done: {ok}/{len(jobs)} -> {textures}")
    return 0 if ok == len(jobs) else 1


if __name__ == "__main__":
    sys.exit(main())
