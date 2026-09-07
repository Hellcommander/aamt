#!/usr/bin/env python3
"""
Hammerwatch 2 / HoH2 projectile & VFX sheet generator.

Default: non-SD reference compose (generate_hw2_vfx_nonsd.py).
Optional: --sd for experimental Stable Diffusion generation (icons use Generate-SkillIcons.ps1).

Usage:
  python generate_hw2_vfx.py --preset soul_skull
  python generate_hw2_vfx.py --preset all
  python generate_hw2_vfx.py --sd --preset soul_skull --quality high
"""

from __future__ import annotations

import argparse
import runpy
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_HERE = Path(__file__).resolve().parent
_NONSD = _HERE / "generate_hw2_vfx_nonsd.py"


def _run_nonsd(argv: List[str]) -> int:
	# Rebuild argv for nonsd script (drop --sd / --quality / --seed)
	sys.argv = [str(_NONSD)] + argv
	try:
		runpy.run_path(str(_NONSD), run_name="__main__")
	except SystemExit as exc:
		code = exc.code
		return int(code) if isinstance(code, int) else (0 if code is None else 1)
	return 0


def _run_sd(argv_ns: argparse.Namespace) -> int:
	from PIL import Image, ImageEnhance, ImageFilter

	_SHARED = _HERE.parent / "Shared"
	if str(_SHARED) not in sys.path:
		sys.path.insert(0, str(_SHARED))

	from sd_http_client import detect_server, generate_image, plan_native_size  # type: ignore

	QUALITY = {
		"draft": {"steps": 18, "guidance": 6.5},
		"standard": {"steps": 26, "guidance": 7.0},
		"high": {"steps": 32, "guidance": 7.0},
		"ultra": {"steps": 40, "guidance": 7.5},
	}
	NEGATIVE = (
		"text, watermark, logo, letters, ui, frame, border, photograph, photorealistic, "
		"3d render, blurry, jpeg artifacts, noisy background, cluttered, "
		"human body, hands, face portrait, complex scene, landscape, "
		"high resolution photo, 4k, 8k"
	)
	PRESETS: Dict[str, Dict[str, Any]] = {
		"soul_skull": {
			"prompt": (
				"Hammerwatch 2 top-down pixel game projectile sprite, single ethereal floating skull, "
				"violet and poison-green soulfire eyes, bone white skull with purple necrotic aura, "
				"centered on pure black background, crisp chunky pixel art, limited palette"
			),
			"frame_size": 128,
			"frames": 4,
			"tint": (180, 90, 255),
		},
		"soul_tendril": {
			"prompt": (
				"Hammerwatch 2 top-down pixel game projectile, single dark violet shadow tendril whip, "
				"centered on pure black background, crisp chunky pixel art, limited palette"
			),
			"frame_size": 128,
			"frames": 4,
			"tint": (120, 60, 200),
		},
		"soul_ray": {
			"prompt": (
				"Hammerwatch 2 top-down pixel game beam segment, necrotic soul ray core, "
				"centered on pure black background, crisp pixel art VFX"
			),
			"frame_size": 128,
			"frames": 4,
			"tint": (140, 255, 120),
		},
		"soulburst": {
			"prompt": (
				"Hammerwatch 2 top-down pixel game impact explosion, circular soulburst ring, "
				"centered on pure black background, crisp pixel art VFX"
			),
			"frame_size": 192,
			"frames": 4,
			"tint": (200, 80, 255),
		},
		"soul_impact": {
			"prompt": (
				"Hammerwatch 2 top-down pixel game hit spark, small soul essence impact puff, "
				"centered on pure black background, crisp pixel art"
			),
			"frame_size": 96,
			"frames": 4,
			"tint": (160, 120, 255),
		},
	}

	def _knockout_black(img: Image.Image, threshold: int = 28) -> Image.Image:
		rgba = img.convert("RGBA")
		px = rgba.load()
		w, h = rgba.size
		for y in range(h):
			for x in range(w):
				r, g, b, a = px[x, y]
				if r <= threshold and g <= threshold and b <= threshold:
					px[x, y] = (0, 0, 0, 0)
				elif min(r, g, b) < 40 and (r + g + b) < threshold * 4:
					px[x, y] = (r, g, b, max(0, a - 160))
		return rgba

	def _finish_native_frame(
		img: Image.Image,
		size: int,
		tint: Optional[Tuple[int, int, int]],
	) -> Image.Image:
		cut = _knockout_black(img)
		if cut.size != (size, size):
			canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
			src = cut
			if src.width > size or src.height > size:
				src = src.resize((size, size), Image.Resampling.NEAREST)
			ox = (size - src.width) // 2
			oy = (size - src.height) // 2
			canvas.paste(src, (max(0, ox), max(0, oy)), src)
			cut = canvas
		cut = ImageEnhance.Contrast(cut).enhance(1.12)
		cut = ImageEnhance.Color(cut).enhance(1.08)
		cut = cut.filter(ImageFilter.SHARPEN)
		if tint:
			tr, tg, tb = tint
			px = cut.load()
			for y in range(cut.height):
				for x in range(cut.width):
					r, g, b, a = px[x, y]
					if a < 8:
						continue
					lum = (r * 0.3 + g * 0.59 + b * 0.11) / 255.0
					nr = int(min(255, r * 0.55 + tr * lum * 0.55 + tr * 0.1))
					ng = int(min(255, g * 0.55 + tg * lum * 0.55 + tg * 0.08))
					nb = int(min(255, b * 0.55 + tb * lum * 0.55 + tb * 0.1))
					px[x, y] = (nr, ng, nb, a)
		return cut

	def _make_strip(frames: List[Image.Image]) -> Image.Image:
		w = frames[0].width
		h = frames[0].height
		out = Image.new("RGBA", (w * len(frames), h), (0, 0, 0, 0))
		for i, fr in enumerate(frames):
			out.paste(fr, (i * w, 0), fr)
		return out

	def _variant_prompt(base: str, index: int, total: int, frame_size: int) -> str:
		angles = [
			"facing slightly left",
			"facing slightly right",
			"tilted forward",
			"tilted back",
			"pulsing brighter aura",
			"wispy trailing particles",
			"more intense glow",
			"subtle motion blur trails",
		]
		hint = angles[index % len(angles)]
		return (
			f"{base}, animation frame {index + 1} of {total}, {hint}, "
			f"exact {frame_size}x{frame_size} pixel sprite, drawn at final game resolution"
		)

	server = detect_server()
	if not server:
		print("ERROR: --sd requested but no SD server on localhost (:1338).", file=sys.stderr)
		print("Prefer non-SD: omit --sd. Or start Tools\\Start-StableDiffusionServer.ps1", file=sys.stderr)
		return 1
	print(f"SD server: {server} (experimental; default path is non-SD)")

	quality = argv_ns.quality
	q = QUALITY.get(quality, QUALITY["standard"])
	out_dir = Path(argv_ns.out) if argv_ns.out else _HERE / "GeneratedAssets/eldritchsoul"
	if not out_dir.is_absolute():
		out_dir = _HERE / out_dir

	names = list(PRESETS.keys()) if argv_ns.preset == "all" else [argv_ns.preset]
	if argv_ns.prompt and argv_ns.name:
		PRESETS[argv_ns.name] = {
			"prompt": argv_ns.prompt,
			"frame_size": argv_ns.frame_size,
			"frames": argv_ns.frames,
			"tint": (170, 100, 255),
		}
		names = [argv_ns.name]

	for name in names:
		if name not in PRESETS:
			print(f"Unknown SD preset: {name}", file=sys.stderr)
			return 1
		spec = PRESETS[name]
		frame_size = int(spec["frame_size"])
		n_frames = int(spec["frames"])
		tint = spec.get("tint")
		gw, gh, _ = plan_native_size(frame_size, frame_size, kind="sprite")
		steps = int(q["steps"])
		guidance = float(q["guidance"])
		out_dir.mkdir(parents=True, exist_ok=True)
		src_dir = out_dir / "Source" / name
		src_dir.mkdir(parents=True, exist_ok=True)
		frames: List[Image.Image] = []
		for i in range(n_frames):
			prompt = _variant_prompt(spec["prompt"], i, n_frames, gw)
			print(f"[{name}] SD native frame {i + 1}/{n_frames} @ {gw}x{gh}")
			use_seed = (argv_ns.seed + i * 17) if argv_ns.seed else 0
			src_path = src_dir / f"frame_{i:02d}_raw.png"
			generate_image(
				prompt,
				src_path,
				api_url=server,
				negative_prompt=NEGATIVE,
				width=gw,
				height=gh,
				steps=steps,
				guidance_scale=guidance,
				seed=use_seed,
			)
			finished = _finish_native_frame(Image.open(src_path), gw, tint)
			frames.append(finished)
			finished.save(src_dir / f"frame_{i:02d}_native.png")
		strip = _make_strip(frames)
		out_path = out_dir / f"{name}.png"
		strip.save(out_path)
		(out_dir / f"{name}.meta.txt").write_text(
			f"name={name}\nframe_size={gw}\nframes={n_frames}\n"
			f"sheet={strip.size[0]}x{strip.size[1]}\nquality={quality}\nnative=1\nsd=1\n",
			encoding="utf-8",
		)
		print(f"[{name}] wrote {out_path}")
	return 0


def main() -> int:
	ap = argparse.ArgumentParser(
		description="HW2 VFX sheets (default: non-SD reference compose)"
	)
	ap.add_argument("--preset", default="soul_skull", help="preset name or 'all'")
	ap.add_argument("--out", default="", help="output directory")
	ap.add_argument("--frame-size", type=int, default=0)
	ap.add_argument("--frames", type=int, default=0)
	ap.add_argument("--list", action="store_true")
	ap.add_argument(
		"--sd",
		action="store_true",
		help="Use Stable Diffusion (experimental). Default is non-SD compose.",
	)
	ap.add_argument("--quality", default="standard", choices=["draft", "standard", "high", "ultra"])
	ap.add_argument("--seed", type=int, default=42)
	ap.add_argument("--name", default="")
	ap.add_argument("--prompt", default="")
	args, unknown = ap.parse_known_args()

	if not args.sd:
		fwd: List[str] = []
		if args.list:
			fwd.append("--list")
		else:
			fwd.extend(["--preset", args.preset])
			if args.out:
				fwd.extend(["--out", args.out])
			if args.frame_size > 0:
				fwd.extend(["--frame-size", str(args.frame_size)])
			if args.frames > 0:
				fwd.extend(["--frames", str(args.frames)])
		fwd.extend(unknown)
		return _run_nonsd(fwd)

	return _run_sd(args)


if __name__ == "__main__":
	raise SystemExit(main())
