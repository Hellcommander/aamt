#!/usr/bin/env python3
"""Img2img class icons using vanilla ToME icons as style references."""
from __future__ import annotations

import base64
import json
import sys
import urllib.request
from pathlib import Path

from PIL import Image

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS.parent / "Shared"))

from generate_class_icons import (  # noqa: E402
    CLASSES,
    NEGATIVE,
    OUTPUT,
    _compose_class_icon,
    _load_masks,
)
from sd_http_client import detect_server  # noqa: E402

JOBS = [
    {
        "key": "smog_devil",
        "variation": 6,
        "seed": 71201,
        "strength": 0.72,
        "refs": [
            Path(r"F:\SteamLibrary\steamapps\common\TalesMajEyal\game\source\tome-gfx\data\gfx\class-icons\sawbutcher_128_bg.png"),
            Path(r"C:\Users\Arend\AppData\Local\Temp\tome_class_icon_refs\annihilator_128_bg.png"),
        ],
        "prompt": (
            "Tales of Maj'Eyal class icon, same painted style as reference, bold black outlines, "
            "flat matte black background, no vignette circle, "
            "smog devil: horned demonic tinker skull in toxic teal-green and brass, "
            "billowing gray-green industrial smog, steam pipes venting, "
            "iron steam-staff with gauges crossed below, corrupt crimson eye glow, "
            "high contrast readable icon, no text no logo"
        ),
    },
    {
        "key": "smog_devil",
        "variation": 7,
        "seed": 71219,
        "strength": 0.68,
        "refs": [
            Path(r"F:\SteamLibrary\steamapps\common\TalesMajEyal\game\source\tome-gfx\data\gfx\class-icons\shadowblade_128_bg.png"),
            Path(r"F:\SteamLibrary\steamapps\common\TalesMajEyal\game\source\tome-gfx\data\gfx\class-icons\sawbutcher_128_bg.png"),
        ],
        "prompt": (
            "Tales of Maj'Eyal class icon painted dark fantasy style matching reference, "
            "black background, stealthy smog devil face wreathed in toxic steam, "
            "brass devil horns, focus lens, steam-staff silhouette, teal and soot palette, no text"
        ),
    },
    {
        "key": "glutton",
        "variation": 6,
        "seed": 82201,
        "strength": 0.72,
        "refs": [
            Path(r"F:\SteamLibrary\steamapps\common\TalesMajEyal\game\source\tome-gfx\data\gfx\class-icons\corruptor_128_bg.png"),
            Path(r"C:\Users\Arend\AppData\Local\Temp\tome_class_icon_refs\writhing_one_128_bg.png"),
        ],
        "prompt": (
            "Tales of Maj'Eyal class icon, same painted style as reference, bold black outlines, "
            "flat matte black background, no vignette circle, "
            "glutton: bloated fleshy red horror head that is mostly a massive hungry maw, "
            "jagged teeth, neon green bile dripping, void purple throat glow, "
            "eldritch demented devourer, high contrast readable icon, no text no logo"
        ),
    },
    {
        "key": "glutton",
        "variation": 7,
        "seed": 82219,
        "strength": 0.68,
        "refs": [
            Path(r"F:\SteamLibrary\steamapps\common\TalesMajEyal\game\source\tome-gfx\data\gfx\class-icons\corruptor_128_bg.png"),
            Path(r"F:\SteamLibrary\steamapps\common\TalesMajEyal\game\source\tome-gfx\data\gfx\class-icons\oozemancer_128_bg.png"),
        ],
        "prompt": (
            "Tales of Maj'Eyal class icon painted dark fantasy style matching reference, "
            "black background, the Endless Maw: ring of teeth around a dark void stomach, "
            "lime digestive slime dripping, bruised meat-red flesh, purple void, no text"
        ),
    },
]


def _prepare_ref(path: Path, size: int = 512) -> str:
    im = Image.open(path).convert("RGBA")
    # composite onto black so transparent corners become black
    bg = Image.new("RGBA", im.size, (0, 0, 0, 255))
    bg.alpha_composite(im)
    rgb = bg.convert("RGB").resize((size, size), Image.Resampling.LANCZOS)
    tmp = OUTPUT / "raw" / f"_ref_{path.stem}_{size}.png"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    rgb.save(tmp)
    return base64.b64encode(tmp.read_bytes()).decode("ascii")


def generate_img2img(job: dict, api_url: str) -> Path:
    stem = CLASSES[job["key"]]["file_stem"]
    out = OUTPUT / "raw" / f"{stem}_v{job['variation']}_s{job['seed']}_i2i.png"
    if out.exists():
        out.unlink()

    # Use first ref as init image (API takes one image)
    ref_b64 = _prepare_ref(job["refs"][0], 512)
    body = {
        "prompt": job["prompt"],
        "negative_prompt": NEGATIVE,
        "width": 512,
        "height": 512,
        "size": "512x512",
        "steps": 28,
        "guidance_scale": 7.0,
        "seed": job["seed"],
        "n": 1,
        "image": ref_b64,
        "strength": job["strength"],
        "response_format": "b64_json",
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        api_url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    print(f"=== {job['key']} v{job['variation']} img2img strength={job['strength']} ===")
    with urllib.request.urlopen(req, timeout=900) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    images = payload.get("data") or []
    if not images:
        raise RuntimeError(f"no image in response: {list(payload.keys())}")
    item = images[0]
    if "b64_json" in item:
        out.write_bytes(base64.b64decode(item["b64_json"]))
    elif "url" in item and item["url"].startswith("data:"):
        # data URL
        b64 = item["url"].split(",", 1)[1]
        out.write_bytes(base64.b64decode(b64))
    else:
        raise RuntimeError(f"unexpected image payload keys: {list(item.keys())}")
    print("saved", out)
    return out


def main() -> int:
    api = detect_server(verbose=True)
    if not api:
        print("SD not ready")
        return 1
    mask128, mask32 = _load_masks()
    for job in JOBS:
        try:
            raw_path = generate_img2img(job, api)
        except Exception as exc:
            print("FAIL", exc)
            continue
        stem = CLASSES[job["key"]]["file_stem"]
        cand_dir = OUTPUT / "candidates" / stem
        cand_dir.mkdir(parents=True, exist_ok=True)
        raw = Image.open(raw_path)
        icon128 = _compose_class_icon(raw, mask128, 128)
        icon32 = _compose_class_icon(icon128.convert("RGB"), mask32, 32)
        p128 = cand_dir / f"{stem}_128_bg_v{job['variation']}.png"
        p32 = cand_dir / f"{stem}_32_bg_v{job['variation']}.png"
        icon128.save(p128)
        icon32.save(p32)
        meta = {
            "ok": True,
            "class": job["key"],
            "variation": job["variation"],
            "seed": job["seed"],
            "prompt": job["prompt"],
            "strength": job["strength"],
            "refs": [str(p) for p in job["refs"]],
            "path_128": str(p128),
            "path_32": str(p32),
            "mode": "img2img",
        }
        p128.with_suffix(".meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        print("OK", p128.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
