#!/usr/bin/env python3
"""Generate additional refined class-icon candidates."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

from generate_class_icons import (  # noqa: E402
    CLASSES,
    NEGATIVE,
    OUTPUT,
    _compose_class_icon,
    _load_masks,
)
from tome_sd_client import generate_sd_image  # noqa: E402

EXTRA = {
    "smog_devil": [
        (
            71101,
            "Tales of Maj'Eyal subclass class-icon exactly like sawbutcher annihilator psyshot icons, "
            "painted dark fantasy, bold black ink outlines, centered composition filling most of the square, "
            "flat pure black background no circle frame no vignette, horned ashen devil face half-hidden by "
            "thick gray-green toxic smog, brass steam pipes venting white steam, iron steam-staff with "
            "pressure gauges diagonally across lower half, teal arcane spark and corrupt crimson glow, "
            "high contrast readable at 32 pixels, no text no logo no watermark",
        ),
        (
            71119,
            "ToME class icon style, graphic illustration on matte black, no outer ring, demonic tinker portrait: "
            "soot-stained skin, small brass devil horns, glowing toxic-green eyes, focus-lens monocle, "
            "billowing industrial smog, crossed brass steam-staff behind head, palette soot black brass gold "
            "toxic teal corrupt purple, thick outlines, sharp silhouette",
        ),
        (
            71137,
            "fantasy RPG class icon Tales of Maj'Eyal, black background only, steamtech devil emblem: "
            "green-gray smog skull with brass horns and pipe vents, steam-staff and refined gem, "
            "painted comic dark fantasy, high contrast, centered, no text",
        ),
    ],
    "glutton": [
        (
            82101,
            "Tales of Maj'Eyal subclass class-icon exactly like corruptor writhing_one oozemancer icons, "
            "painted dark fantasy, bold black ink outlines, centered composition filling most of the square, "
            "flat pure black background no circle frame no vignette, bloated fleshy red horror head dominated "
            "by an enormous gaping maw of jagged yellow teeth, neon green bile dripping from chin, "
            "void-purple glow in throat, small hungry eyes, visceral demented glutton aesthetic, "
            "high contrast readable at 32 pixels, no text no logo",
        ),
        (
            82119,
            "ToME class icon style, graphic illustration on matte black, no outer ring, the Endless Maw: "
            "circular ring of sharp teeth around a dark purple void stomach, lime digestive slime dripping down, "
            "bruised meat-red flesh, eldritch hunger symbol, thick outlines, sharp silhouette",
        ),
        (
            82137,
            "fantasy RPG class icon Tales of Maj'Eyal, black background only, gluttonous eldritch devourer face "
            "with huge open mouth and dripping green slime, fleshy red and purple, painted comic dark fantasy, "
            "high contrast, centered, no text",
        ),
    ],
}


def main() -> int:
    mask128, mask32 = _load_masks()
    for key, items in EXTRA.items():
        stem = CLASSES[key]["file_stem"]
        cand_dir = OUTPUT / "candidates" / stem
        cand_dir.mkdir(parents=True, exist_ok=True)
        for i, (seed, prompt) in enumerate(items, start=3):
            raw_path = OUTPUT / "raw" / f"{stem}_v{i}_s{seed}.png"
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            if raw_path.exists():
                raw_path.unlink()
            print(f"\n=== {key} v{i} seed={seed} ===")
            result = generate_sd_image(
                prompt,
                raw_path,
                negative_prompt=NEGATIVE,
                delivery_w=128,
                delivery_h=128,
                kind="icon",
                seed=seed,
                guidance_scale=7.5,
                lock_label=f"class_icon_{stem}_{i}",
            )
            if not result.ok:
                print("FAIL", result.error)
                continue
            raw = Image.open(result.output_path)
            icon128 = _compose_class_icon(raw, mask128, 128)
            icon32 = _compose_class_icon(icon128.convert("RGB"), mask32, 32)
            p128 = cand_dir / f"{stem}_128_bg_v{i}.png"
            p32 = cand_dir / f"{stem}_32_bg_v{i}.png"
            icon128.save(p128)
            icon32.save(p32)
            meta = {
                "ok": True,
                "class": key,
                "variation": i,
                "seed": seed,
                "prompt": prompt,
                "path_128": str(p128),
                "path_32": str(p32),
            }
            p128.with_suffix(".meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
            print("OK", p128.name)
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
