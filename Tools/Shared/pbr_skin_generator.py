#!/usr/bin/env python3
"""
Shared PBR skin map generator for AAMT (Elin / Qud / others).

Produces a Unity-friendly texture set:
  {name}_diffuse.png   — base color (SD3.5 required)
  {name}_normal.png    — tangent normal derived from SD albedo
  {name}_roughness.png — roughness derived from SD albedo
  {name}_metallic.png  — metallic derived from SD albedo
  {name}_emission.png  — emission (optional glow)

Always writes Unity .meta beside each PNG (no Editor required).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

_SHARED = Path(__file__).resolve().parent
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from unity_meta import write_texture_meta  # noqa: E402

try:
    from sd_http_client import detect_server, generate_image
    _SD_OK = True
except Exception:
    detect_server = None  # type: ignore
    generate_image = None  # type: ignore
    _SD_OK = False

QUALITY = {
    # draft SD size clamped to 512: SD3.5 Medium degrades below ~512 short side
    "draft":    {"size": 512, "steps": 18, "guidance": 6.5},
    "standard": {"size": 512, "steps": 26, "guidance": 7.0},
    "high":     {"size": 768, "steps": 32, "guidance": 7.0},
    "ultra":    {"size": 1024, "steps": 40, "guidance": 7.5},
}


def _snap16(n: int) -> int:
    return max(256, int(round(n / 16.0)) * 16)


def _hex_rgb(h: str) -> Tuple[int, int, int]:
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def build_skin_prompt(spec: Dict[str, Any]) -> Tuple[str, str]:
    theme = str(spec.get("theme") or spec.get("system") or "fantasy material")
    colors = spec.get("colors") or spec.get("palette") or []
    color_hint = ", ".join(c for c in colors if isinstance(c, str))[:80]
    style = str(spec.get("style") or "stylized")
    pattern = str(spec.get("pattern") or "organic")
    desc = str(spec.get("description") or "").strip()
    prompt = (
        f"no text, no logo, no watermark, seamless tileable PBR base color texture, "
        f"{pattern} {theme}, {desc}, colors {color_hint}, {style}, "
        f"even flat lighting, top-down, physically based albedo, high detail"
    )
    negative = (
        "text, logo, watermark, letters, ui, frame, border, seams, "
        "harsh shadows, directional light, vignette, 3d render of object, "
        "blurry, lowres, jpeg artifacts, photograph"
    )
    prompt = ", ".join(p.strip() for p in prompt.split(",") if p.strip())
    return prompt, negative


def _procedural_diffuse(size: int, spec: Dict[str, Any], seed: int = 0) -> Image.Image:
    import random

    rng = random.Random(seed)
    colors = []
    for c in spec.get("colors") or spec.get("palette") or []:
        if isinstance(c, str) and c.startswith("#"):
            colors.append(_hex_rgb(c))
    if len(colors) < 2:
        colors = [(40, 60, 90), (80, 120, 160), (200, 220, 240)]
    img = Image.new("RGB", (size, size))
    px = img.load()
    cell = max(4, size // 16)
    for y in range(0, size, cell):
        for x in range(0, size, cell):
            t = ((x + seed) / size + (y + seed * 3) / size) * 0.5 + rng.random() * 0.2
            t = max(0.0, min(0.999, t))
            i = int(t * (len(colors) - 1))
            c1, c2 = colors[i], colors[min(i + 1, len(colors) - 1)]
            local = t * (len(colors) - 1) - i
            col = tuple(int(a + (b - a) * local) for a, b in zip(c1, c2))
            for yy in range(y, min(y + cell, size)):
                for xx in range(x, min(x + cell, size)):
                    n = int((rng.random() - 0.5) * 16)
                    px[xx, yy] = tuple(max(0, min(255, c + n)) for c in col)
    img = img.filter(ImageFilter.SMOOTH_MORE)
    return ImageEnhance.Contrast(img).enhance(1.05)


def _sd_diffuse(size: int, spec: Dict[str, Any], seed: int, steps: int, guidance: float) -> Optional[Image.Image]:
    prompt, negative = build_skin_prompt(spec)
    tmp = Path(tempfile.gettempdir()) / f"aamt_skin_{abs(seed) % 10_000_000}_{size}.png"
    try:
        from ai_resources import make_image
        from sd_http_client import plan_sd_size

        gw, gh, plan_steps = plan_sd_size(size, size, "texture")
        kw: Dict[str, Any] = {
            "negative_prompt": negative,
            "width": gw,
            "height": gh,
            "steps": max(int(steps), int(plan_steps)),
            "guidance_scale": guidance,
            "seed": seed,
        }
        ref = spec.get("referenceImage") or spec.get("reference_image")
        if ref:
            kw["reference_image"] = str(ref)
            kw["image_strength"] = float(spec.get("imageStrength", spec.get("image_strength", 0.5)))
        make_image(prompt, tmp, **kw)
    except Exception:
        if not (_SD_OK and generate_image):
            return None
        api = os.environ.get("AAMT_SD_API_URL") or (detect_server() if detect_server else None)
        if not api:
            return None
        try:
            kw2: Dict[str, Any] = {
                "prompt": prompt,
                "output_path": tmp,
                "api_url": api,
                "negative_prompt": negative,
                "width": size,
                "height": size,
                "steps": steps,
                "guidance_scale": guidance,
                "seed": seed,
            }
            ref = spec.get("referenceImage") or spec.get("reference_image")
            if ref:
                kw2["reference_image"] = str(ref)
                kw2["image_strength"] = float(
                    spec.get("imageStrength", spec.get("image_strength", 0.5))
                )
            generate_image(**kw2)
        except Exception as exc:
            print(f"[PBR] SD diffuse failed; procedural: {exc}", file=sys.stderr)
            return None
    try:
        if not tmp.exists():
            return None
        img = Image.open(tmp).convert("RGB")
        try:
            tmp.unlink()
        except OSError:
            pass
        if img.size != (size, size):
            img = img.resize((size, size), Image.Resampling.LANCZOS)
        return ImageEnhance.Sharpness(img).enhance(1.08)
    except Exception as exc:
        print(f"[PBR] SD diffuse failed; procedural: {exc}", file=sys.stderr)
        return None


def _normal_from_diffuse(diffuse: Image.Image, strength: float = 2.0) -> Image.Image:
    """Sobel-ish normal from luma (OpenGL-style: +Y up)."""
    gray = ImageOps.grayscale(diffuse)
    w, h = gray.size
    src = gray.load()
    out = Image.new("RGB", (w, h))
    dst = out.load()
    for y in range(h):
        for x in range(w):
            l = src[max(0, x - 1), y]
            r = src[min(w - 1, x + 1), y]
            u = src[x, max(0, y - 1)]
            d = src[x, min(h - 1, y + 1)]
            dx = (r - l) / 255.0 * strength
            dy = (d - u) / 255.0 * strength
            dz = 1.0
            inv = 1.0 / max(1e-6, (dx * dx + dy * dy + dz * dz) ** 0.5)
            nx, ny, nz = dx * inv, -dy * inv, dz * inv
            dst[x, y] = (
                int((nx * 0.5 + 0.5) * 255),
                int((ny * 0.5 + 0.5) * 255),
                int((nz * 0.5 + 0.5) * 255),
            )
    return out


def _roughness_from_diffuse(diffuse: Image.Image, base: float = 0.55) -> Image.Image:
    gray = ImageOps.grayscale(diffuse)
    # Invert slightly: brighter = smoother (lower roughness)
    inv = ImageOps.invert(gray)
    inv = ImageEnhance.Contrast(inv).enhance(0.85)
    # Bias toward mid roughness
    return Image.blend(inv, Image.new("L", inv.size, int(base * 255)), 0.35)


def _metallic_from_diffuse(diffuse: Image.Image, amount: float = 0.15) -> Image.Image:
    gray = ImageOps.grayscale(diffuse)
    # Keep mostly non-metal; lift a bit on bright areas
    boosted = ImageEnhance.Contrast(gray).enhance(1.4)
    return Image.blend(Image.new("L", gray.size, 0), boosted, amount)


def _emission_from_diffuse(diffuse: Image.Image, glow: bool = False) -> Image.Image:
    if not glow:
        return Image.new("RGB", diffuse.size, (0, 0, 0))
    # Keep only brighter hues as soft emission
    hsv = diffuse.convert("HSV")
    h, s, v = hsv.split()
    mask = v.point(lambda p: 255 if p > 180 else 0)
    em = Image.composite(diffuse, Image.new("RGB", diffuse.size, (0, 0, 0)), mask)
    return em.filter(ImageFilter.GaussianBlur(radius=max(1, diffuse.size[0] // 64)))


def _pack_metallic_gloss(metallic: Image.Image, roughness: Image.Image) -> Image.Image:
    """
    Unity Standard _MetallicGlossMap: R = metallic, A = smoothness (1 - roughness).
    G/B unused (zero).
    """
    metal_l = ImageOps.grayscale(metallic)
    rough_l = ImageOps.grayscale(roughness)
    smooth_l = ImageOps.invert(rough_l)
    zero = Image.new("L", metal_l.size, 0)
    return Image.merge("RGBA", (metal_l, zero, zero, smooth_l))


def generate_pbr_skin_set(
    output_dir: Path | str,
    name: str,
    spec: Optional[Dict[str, Any]] = None,
    *,
    quality: str = "standard",
    size: Optional[int] = None,
    use_sd: bool = True,
    seed: int = 17,
    glow: bool = False,
    allow_procedural: bool = False,
) -> Dict[str, Path]:
    """
    Write a full PBR map set under output_dir. Returns map name -> path.
    """
    spec = dict(spec or {})
    tier = QUALITY.get(quality, QUALITY["standard"])
    sz = _snap16(int(size if size else tier["size"]))
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    diffuse = None
    source = "sd"
    if not use_sd and not allow_procedural:
        raise RuntimeError("SD is required for PBR skins (procedural noise skins are disabled)")
    if use_sd:
        diffuse = _sd_diffuse(sz, spec, seed=seed, steps=int(tier["steps"]), guidance=float(tier["guidance"]))
        if diffuse is not None:
            source = "sd"
    if diffuse is None:
        if not allow_procedural:
            raise RuntimeError("SD diffuse failed; refusing procedural skin")
        diffuse = _procedural_diffuse(sz, spec, seed=seed)
        source = "procedural"

    metallic = _metallic_from_diffuse(diffuse).convert("RGB")
    roughness = _roughness_from_diffuse(diffuse).convert("RGB")
    maps = {
        "diffuse": diffuse,
        "normal": _normal_from_diffuse(diffuse),
        "roughness": roughness,
        "metallic": metallic,
        "metallicgloss": _pack_metallic_gloss(metallic, roughness),
        "emission": _emission_from_diffuse(diffuse, glow=glow or bool(spec.get("glow"))),
    }

    paths: Dict[str, Path] = {}
    for key, img in maps.items():
        path = out_dir / f"{name}_{key}.png"
        img.save(path, "PNG", compress_level=6)
        kind = "normal" if key == "normal" else "default"
        write_texture_meta(
            path,
            kind=kind,
            srgb=(key == "diffuse"),
            generate_mipmaps=True,
            wrap_mode=1,
            overwrite=True,
        )
        paths[key] = path
        print(f"[PBR] {key}: {path} ({source if key == 'diffuse' else 'from-sd-albedo'})")

    # Sidecar registry for Blender / Unity batch consumers
    registry = {
        "name": name,
        "size": [sz, sz],
        "quality": quality,
        "diffuseSource": source,
        "maps": {k: p.name for k, p in paths.items()},
        "spec": {k: spec.get(k) for k in ("theme", "system", "style", "pattern", "colors") if k in spec},
    }
    reg_path = out_dir / f"{name}_pbr.json"
    reg_path.write_text(json.dumps(registry, indent=2), encoding="utf-8")
    paths["registry"] = reg_path
    return paths


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate PBR skin maps for Unity")
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--name", required=True, help="Base filename stem")
    ap.add_argument("--spec", default=None, help="Optional JSON spec path")
    ap.add_argument("--quality", choices=list(QUALITY.keys()), default="standard")
    ap.add_argument("--size", type=int, default=None)
    ap.add_argument("--seed", type=int, default=17)
    ap.add_argument("--no-sd", action="store_true")
    ap.add_argument("--glow", action="store_true")
    ap.add_argument("--theme", default="")
    ap.add_argument("--colors", default="", help="Comma-separated hex colors")
    args = ap.parse_args()

    spec: Dict[str, Any] = {}
    if args.spec and Path(args.spec).exists():
        spec = json.loads(Path(args.spec).read_text(encoding="utf-8-sig"))
    if args.theme:
        spec["theme"] = args.theme
    if args.colors:
        spec["colors"] = [c.strip() for c in args.colors.split(",") if c.strip()]
    if args.glow:
        spec["glow"] = True

    generate_pbr_skin_set(
        args.output_dir,
        args.name,
        spec,
        quality=args.quality,
        size=args.size,
        use_sd=not args.no_sd,
        seed=args.seed,
        glow=args.glow,
        allow_procedural=False,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
