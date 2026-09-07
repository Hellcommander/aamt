#!/usr/bin/env python3
"""HW2 skill icons via SD (icons only — not projectiles)."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps

_SHARED = Path(__file__).resolve().parent.parent / "Shared"
if str(_SHARED) not in sys.path:
	sys.path.insert(0, str(_SHARED))

from sd_http_client import detect_server, generate_image, plan_native_size  # type: ignore

QUALITY = {
	"draft": 18,
	"standard": 26,
	"high": 32,
	"ultra": 40,
}

NEGATIVE = (
	"text, watermark, logo, letters, photograph, photorealistic, blurry, "
	"cluttered, full character body, landscape, ui chrome"
)


def _knockout(img: Image.Image, threshold: int = 28) -> Image.Image:
	rgba = img.convert("RGBA")
	px = rgba.load()
	for y in range(rgba.height):
		for x in range(rgba.width):
			r, g, b, a = px[x, y]
			if r <= threshold and g <= threshold and b <= threshold:
				px[x, y] = (0, 0, 0, 0)
	return rgba


def main() -> int:
	ap = argparse.ArgumentParser()
	ap.add_argument("--name", required=True)
	ap.add_argument("--description", required=True)
	ap.add_argument("--out-dir", default="GeneratedAssets/icons")
	ap.add_argument("--size", type=int, default=32)
	ap.add_argument("--quality", default="standard", choices=list(QUALITY))
	ap.add_argument("--seed", type=int, default=42)
	args = ap.parse_args()

	server = detect_server()
	if not server:
		print("ERROR: no SD server (:1338). Start Start-StableDiffusionServer.ps1", file=sys.stderr)
		return 1

	safe = re.sub(r"[^\w\-]+", "_", args.name).lower()
	out_dir = Path(args.out_dir)
	out_dir.mkdir(parents=True, exist_ok=True)
	raw_path = out_dir / f"{safe}_raw.png"
	out_path = out_dir / f"{safe}.png"

	# Generate with enough pixels for SD coherence, then deliver at icon size.
	gen = max(128, int(round(args.size / 16) * 16))
	gw, gh, _ = plan_native_size(gen, gen, kind="icon")
	prompt = (
		f"fantasy skill icon for Hammerwatch 2, {args.description}, "
		"centered single symbol, pure black background, crisp readable silhouette, "
		"limited palette, game UI icon, no text, no watermark"
	)
	print(f"[icon] {safe} SD {gw}x{gh} -> {args.size}x{args.size}")
	generate_image(
		prompt,
		raw_path,
		api_url=server,
		negative_prompt=NEGATIVE,
		width=gw,
		height=gh,
		steps=QUALITY[args.quality],
		guidance_scale=7.0,
		seed=args.seed,
	)
	img = _knockout(Image.open(raw_path))
	img = ImageEnhance.Contrast(img).enhance(1.15)
	img = ImageOps.contain(img, (args.size, args.size), method=Image.Resampling.LANCZOS)
	canvas = Image.new("RGBA", (args.size, args.size), (0, 0, 0, 0))
	canvas.paste(img, ((args.size - img.width) // 2, (args.size - img.height) // 2), img)
	canvas.save(out_path)
	print(f"wrote {out_path}")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
