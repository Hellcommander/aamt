#!/usr/bin/env python3
"""
Hammerwatch 2 / HoH2 VFX sheets without Stable Diffusion.

Reference-compose: cut frames from unpacked game art, recolor, optional glow,
export horizontal strips under GeneratedAssets/.

Usage:
  python generate_hw2_vfx_nonsd.py --preset soul_skull
  python generate_hw2_vfx_nonsd.py --preset all --out GeneratedAssets
"""

from __future__ import annotations

import argparse
import math
import os
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

RGB = Tuple[int, int, int]
RGBA = Tuple[int, int, int, int]

_TOOLS = Path(__file__).resolve().parent
_DEFAULT_HOH2 = Path(r"F:\SteamLibrary\steamapps\common\Heroes of Hammerwatch 2")
_DEFAULT_HW2 = Path(r"F:\SteamLibrary\steamapps\common\Hammerwatch 2")


def _candidate_roots() -> List[Path]:
	roots: List[Path] = []
	env = os.environ.get("HOH2_ROOT") or os.environ.get("HW2_UNPACK_ROOT")
	if env:
		roots.append(Path(env))
	for base in (_DEFAULT_HOH2, _DEFAULT_HW2):
		for name in ("unpacked_assets_143", "unpacked_assets_143-1", "unpacked_assets"):
			roots.append(base / name)
	# de-dupe while preserving order
	seen = set()
	out: List[Path] = []
	for r in roots:
		key = str(r.resolve()) if r.exists() else str(r)
		if key in seen:
			continue
		seen.add(key)
		out.append(r)
	return out


def resolve_asset(*relative_parts: str) -> Path:
	rel = Path(*relative_parts)
	for root in _candidate_roots():
		cand = root / rel
		if cand.is_file():
			return cand
	tried = "\n  ".join(str(r / rel) for r in _candidate_roots()[:6])
	raise FileNotFoundError(f"Missing reference asset {rel}. Tried:\n  {tried}")


def _make_strip(frames: Sequence[Image.Image]) -> Image.Image:
	w, h = frames[0].size
	out = Image.new("RGBA", (w * len(frames), h), (0, 0, 0, 0))
	for i, fr in enumerate(frames):
		if fr.size != (w, h):
			fr = fr.resize((w, h), Image.Resampling.NEAREST)
		out.paste(fr, (i * w, 0), fr)
	return out


def _slice_grid(
	sheet: Image.Image,
	frame_w: int,
	frame_h: int,
	count: int,
	origin: Tuple[int, int] = (0, 0),
	row: int = 0,
) -> List[Image.Image]:
	ox, oy = origin
	frames: List[Image.Image] = []
	for i in range(count):
		x = ox + i * frame_w
		y = oy + row * frame_h
		frames.append(sheet.crop((x, y, x + frame_w, y + frame_h)).convert("RGBA"))
	return frames


def _slice_rects(sheet: Image.Image, rects: Sequence[Tuple[int, int, int, int]]) -> List[Image.Image]:
	return [sheet.crop((x, y, x + w, y + h)).convert("RGBA") for x, y, w, h in rects]


def _fit_canvas(img: Image.Image, size: int, scale_up: bool = True) -> Image.Image:
	"""Center sprite on a square canvas. Optionally NEAREST-upscale to fill."""
	canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
	src = img.convert("RGBA")
	if src.width != size or src.height != size:
		if scale_up or src.width > size or src.height > size:
			scale = min(size / max(1, src.width), size / max(1, src.height))
			nw = max(1, int(round(src.width * scale)))
			nh = max(1, int(round(src.height * scale)))
			src = src.resize((nw, nh), Image.Resampling.NEAREST)
	ox = (size - src.width) // 2
	oy = (size - src.height) // 2
	canvas.paste(src, (ox, oy), src)
	return canvas


def _tint_luma(img: Image.Image, tint: RGB, strength: float = 0.55) -> Image.Image:
	out = img.convert("RGBA")
	tr, tg, tb = tint
	px = out.load()
	w, h = out.size
	for y in range(h):
		for x in range(w):
			r, g, b, a = px[x, y]
			if a < 8:
				continue
			lum = (r * 0.3 + g * 0.59 + b * 0.11) / 255.0
			keep = 1.0 - strength
			nr = int(min(255, r * keep + tr * lum * strength + tr * 0.08))
			ng = int(min(255, g * keep + tg * lum * strength + tg * 0.06))
			nb = int(min(255, b * keep + tb * lum * strength + tb * 0.08))
			px[x, y] = (nr, ng, nb, a)
	return out


def _palette_shift(img: Image.Image, from_hue_bias: RGB, to_rgb: RGB, amount: float = 0.7) -> Image.Image:
	"""Shift mid/high luminance toward target while preserving silhouette."""
	return _tint_luma(img, to_rgb, strength=amount)


def _add_aura(img: Image.Image, color: RGB, radius: int = 2, alpha: int = 90) -> Image.Image:
	base = img.convert("RGBA")
	glow = base.filter(ImageFilter.MaxFilter(size=max(3, radius * 2 + 1)))
	glow = glow.filter(ImageFilter.GaussianBlur(radius=max(1, radius)))
	px = glow.load()
	cr, cg, cb = color
	w, h = glow.size
	for y in range(h):
		for x in range(w):
			r, g, b, a = px[x, y]
			if a < 8:
				continue
			px[x, y] = (cr, cg, cb, min(alpha, a))
	out = Image.new("RGBA", base.size, (0, 0, 0, 0))
	out = Image.alpha_composite(out, glow)
	out = Image.alpha_composite(out, base)
	return out


def _pulse_variant(img: Image.Image, index: int, total: int) -> Image.Image:
	"""Slight brightness/scale pulse across animation frames."""
	t = index / max(1, total - 1)
	bright = 0.92 + 0.16 * (0.5 - abs(t - 0.5) * 2)  # mid frames brighter
	out = ImageEnhance.Brightness(img).enhance(bright)
	# optional 1px expand on even frames via aura flicker
	if index % 2 == 1:
		out = _add_aura(out, (180, 120, 255), radius=1, alpha=50)
	return out


def _earth_tint(img: Image.Image) -> Image.Image:
	return _tint_luma(img, (160, 120, 70), strength=0.65)


def build_soul_skull(frame_size: int = 64, frames: int = 8) -> Tuple[List[Image.Image], Dict[str, Any]]:
	path = resolve_asset("actors", "bosses", "boss_wraith", "projectiles", "skull_projectile.png")
	sheet = Image.open(path)
	# 256x32 → eight 32x32 cells
	src_frames = _slice_grid(sheet, 32, 32, min(frames, 8))
	if frames > len(src_frames):
		# cycle
		src_frames = [src_frames[i % len(src_frames)] for i in range(frames)]
	out: List[Image.Image] = []
	for i, fr in enumerate(src_frames[:frames]):
		fitted = _fit_canvas(fr, frame_size)
		tinted = _tint_luma(fitted, (170, 90, 255), strength=0.5)
		# cyan eye-ish boost on bright pixels
		tinted = _add_aura(tinted, (100, 220, 255), radius=2, alpha=70)
		tinted = _pulse_variant(tinted, i, frames)
		tinted = ImageEnhance.Contrast(tinted).enhance(1.1)
		out.append(tinted)
	meta = {"source": str(path), "src_frame": "32x32", "method": "reference-compose"}
	return out, meta


def build_stone_spikes(frame_size: int = 64, frames: int = 8) -> Tuple[List[Image.Image], Dict[str, Any]]:
	path = resolve_asset("effects", "spritesheets", "groundspikes.png")
	sheet = Image.open(path)
	# Top-row 14x15 cells; source anim retracts to nearly empty — keep solid frames
	# and ping-pong emerge (empty→full→hold) so every output frame stays readable.
	all_rects = [(i * 14, 0, 14, 15) for i in range(9)]
	all_src = _slice_rects(sheet, all_rects)
	# Prefer frames with enough ink (emerge half is indices 0..3 in practice)
	solid = [fr for fr in all_src if sum(1 for p in fr.getdata() if p[3] > 8) >= 40]
	if not solid:
		solid = all_src[:4]
	# Build emerge sequence: thinnest solid → fullest, then pulse on fullest
	solid_sorted = sorted(
		solid,
		key=lambda fr: sum(1 for p in fr.getdata() if p[3] > 8),
	)
	seq: List[Image.Image] = []
	# ramp up
	seq.extend(solid_sorted)
	# hold / pulse on densest
	seq.extend([solid_sorted[-1]] * max(1, frames - len(seq)))
	out: List[Image.Image] = []
	for i in range(frames):
		fr = seq[i % len(seq)]
		fitted = _fit_canvas(fr, frame_size)
		earth = _earth_tint(fitted)
		earth = _tint_luma(earth, (140, 130, 110), strength=0.25)
		earth = _add_aura(earth, (110, 85, 45), radius=2, alpha=55)
		earth = ImageEnhance.Contrast(earth).enhance(1.2)
		earth = _pulse_variant(earth, i, frames)
		out.append(earth)
	meta = {"source": str(path), "src_frame": "14x15-solid-ping", "method": "reference-compose"}
	return out, meta


def build_tremor_ring(frame_size: int = 96, frames: int = 4) -> Tuple[List[Image.Image], Dict[str, Any]]:
	path = resolve_asset("effects", "spritesheets", "effects.png")
	sheet = Image.open(path)
	ring = sheet.crop((372, 719, 372 + 48, 719 + 48)).convert("RGBA")
	# denser debris: take a padded chip strip and slice
	chip_strip = sheet.crop((210, 740, 270, 780)).convert("RGBA")
	chips = [
		chip_strip.crop((8, 7, 20, 19)),
		chip_strip.crop((21, 7, 33, 19)),
		chip_strip.crop((34, 7, 46, 19)),
		chip_strip.crop((8, 20, 20, 32)),
	]
	out: List[Image.Image] = []
	cx = cy = frame_size / 2
	for i in range(frames):
		canvas = Image.new("RGBA", (frame_size, frame_size), (0, 0, 0, 0))
		t = i / max(1, frames - 1)
		# Expanding shockwave: reference ring scaled large + drawn earth rings for body
		rw = max(40, int(frame_size * (0.45 + 0.5 * t)))
		ring_s = ring.resize((rw, rw), Image.Resampling.NEAREST)
		ring_s = _earth_tint(ring_s)
		ring_s = _add_aura(ring_s, (150, 110, 60), radius=3, alpha=100)
		# mild outer fade only (keep readable)
		fade = int(255 * (1.0 - 0.25 * t))
		px = ring_s.load()
		for y in range(ring_s.height):
			for x in range(ring_s.width):
				r, g, b, a = px[x, y]
				if a < 8:
					continue
				px[x, y] = (r, g, b, min(255, int(a * fade / 255) + 40))
		ox = (frame_size - rw) // 2
		oy = (frame_size - rw) // 2
		canvas.paste(ring_s, (ox, oy), ring_s)

		# Reinforce silhouette with 2 concentric ellipses (pixel-ish via thick stroke)
		overlay = Image.new("RGBA", (frame_size, frame_size), (0, 0, 0, 0))
		draw = ImageDraw.Draw(overlay)
		rad = rw * 0.42
		for k, col in enumerate([(160, 120, 70, 160), (90, 70, 40, 110)]):
			rr = rad * (1.0 - 0.12 * k)
			bbox = [cx - rr, cy - rr, cx + rr, cy + rr]
			draw.ellipse(bbox, outline=col, width=max(2, frame_size // 32))
		canvas = Image.alpha_composite(canvas, overlay)

		# Scatter several chips around the ring
		for j, chip in enumerate(chips):
			cs = max(10, frame_size // 8)
			ch = _earth_tint(_fit_canvas(chip, cs))
			ang = (j / len(chips) + t * 0.15) * 6.28318
			px_ = int(cx + math.cos(ang) * (rw * 0.38) - cs / 2)
			py_ = int(cy + math.sin(ang) * (rw * 0.28) - cs / 2)
			canvas.paste(ch, (px_, py_), ch)

		canvas = ImageEnhance.Contrast(canvas).enhance(1.2)
		out.append(canvas)
	meta = {"source": str(path), "src_rects": "tremor ring+chips+stroke", "method": "reference-compose"}
	return out, meta


PRESETS: Dict[str, Dict[str, Any]] = {
	"soul_skull": {
		"builder": build_soul_skull,
		"frame_size": 64,
		"frames": 8,
		"default_out": "GeneratedAssets/eldritchsoul",
	},
	"stone_spikes": {
		"builder": build_stone_spikes,
		"frame_size": 64,
		"frames": 8,
		"default_out": "GeneratedAssets/druidic_earth",
	},
	"tremor_ring": {
		"builder": build_tremor_ring,
		"frame_size": 96,
		"frames": 4,
		"default_out": "GeneratedAssets/druidic_earth",
	},
}


def generate_preset(
	name: str,
	out_dir: Path,
	frame_size: Optional[int] = None,
	frames: Optional[int] = None,
) -> Path:
	if name not in PRESETS:
		raise KeyError(name)
	spec = PRESETS[name]
	builder: Callable[..., Tuple[List[Image.Image], Dict[str, Any]]] = spec["builder"]
	fs = int(frame_size if frame_size is not None else spec["frame_size"])
	nf = int(frames if frames is not None else spec["frames"])

	frame_list, meta = builder(frame_size=fs, frames=nf)
	out_dir.mkdir(parents=True, exist_ok=True)
	src_dir = out_dir / "Source" / name
	src_dir.mkdir(parents=True, exist_ok=True)

	for i, fr in enumerate(frame_list):
		fr.save(src_dir / f"frame_{i:02d}.png")

	strip = _make_strip(frame_list)
	out_path = out_dir / f"{name}.png"
	strip.save(out_path)

	meta_path = out_dir / f"{name}.meta.txt"
	meta_lines = [
		f"name={name}",
		f"frame_size={fs}",
		f"frames={len(frame_list)}",
		f"sheet={strip.size[0]}x{strip.size[1]}",
		"method=nonsd-reference-compose",
		f"source={meta.get('source', '')}",
		f"src_frame={meta.get('src_frame', meta.get('src_rects', ''))}",
		"sd=0",
	]
	meta_path.write_text("\n".join(meta_lines) + "\n", encoding="utf-8")
	print(f"[{name}] wrote {out_path} ({strip.size[0]}x{strip.size[1]}) frames={len(frame_list)} @ {fs}")
	return out_path


def main() -> int:
	ap = argparse.ArgumentParser(description="HW2/HoH2 VFX sheets via reference compose (no SD)")
	ap.add_argument("--preset", default="soul_skull", help="preset name or 'all'")
	ap.add_argument("--out", default="", help="output directory (default per preset)")
	ap.add_argument("--frame-size", type=int, default=0, help="override frame size")
	ap.add_argument("--frames", type=int, default=0, help="override frame count")
	ap.add_argument("--list", action="store_true", help="list presets and exit")
	args = ap.parse_args()

	if args.list:
		for k, v in PRESETS.items():
			print(f"{k}: frame_size={v['frame_size']} frames={v['frames']} -> {v['default_out']}")
		return 0

	names = list(PRESETS.keys()) if args.preset == "all" else [args.preset]
	fs = args.frame_size if args.frame_size > 0 else None
	nf = args.frames if args.frames > 0 else None

	for name in names:
		if name not in PRESETS:
			print(f"Unknown preset: {name}. Use --list.", flush=True)
			return 1
		out = Path(args.out) if args.out else _TOOLS / PRESETS[name]["default_out"]
		if not out.is_absolute():
			out = _TOOLS / out
		try:
			generate_preset(name, out, frame_size=fs, frames=nf)
		except FileNotFoundError as exc:
			print(f"ERROR: {exc}", flush=True)
			return 1
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
