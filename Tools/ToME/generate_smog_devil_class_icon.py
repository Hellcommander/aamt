#!/usr/bin/env python3
"""Regenerate Smog Devil class icon as steam+arcane magic (steam-staff), not melee."""
from __future__ import annotations

import base64
import json
import shutil
import sys
import urllib.request
from pathlib import Path

from PIL import Image

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS.parent / "Shared"))

from generate_class_icons import (  # noqa: E402
    NEGATIVE,
    OUTPUT,
    _compose_class_icon,
    _load_masks,
)
from sd_http_client import detect_server  # noqa: E402
from tome_sd_client import generate_sd_image  # noqa: E402

STEM = "smog_devil"
MOD_ICONS = Path(
    r"F:\SteamLibrary\steamapps\common\TalesMajEyal\game\addons\tome-smog-devil-class\data\gfx\class-icons"
)
CAND = OUTPUT / "candidates" / STEM

# Magic-oriented ToME refs (staff / orb / arcane), NOT sawbutcher melee
REFS = {
    "alchemist": Path(
        r"F:\SteamLibrary\steamapps\common\TalesMajEyal\game\source\tome-gfx\data\gfx\class-icons\alchemist_128_bg.png"
    ),
    "archmage": Path(
        r"F:\SteamLibrary\steamapps\common\TalesMajEyal\game\source\tome-gfx\data\gfx\class-icons\archmage_128_bg.png"
    ),
    "annihilator": Path(r"C:\Users\Arend\AppData\Local\Temp\tome_class_icon_refs\annihilator_128_bg.png"),
    "psyshot": Path(
        r"F:\SteamLibrary\steamapps\common\TalesMajEyal\game\source\tome-gfx\data\gfx\class-icons\psyshot_128_bg.png"
    ),
}

JOBS = [
    # txt2img — explicit steam-staff mage
    {
        "variation": 10,
        "mode": "txt",
        "seed": 73001,
        "prompt": (
            "Tales of Maj'Eyal class icon, painted dark fantasy UI icon, bold black outlines, "
            "flat matte black background, no circle vignette, no shield frame, "
            "STEAM-STAFF MAGE class NOT melee: centered brass-and-iron steamtech wizard staff "
            "with pressure gauges and pipe vents, tip glowing with violet arcane gem, "
            "thick toxic gray-green smog and white steam billowing from the vents, "
            "small horned devil silhouette forming inside the smog cloud behind the staff, "
            "palette soot black, brass gold, toxic teal, arcane violet, "
            "high contrast readable at 32 pixels, no sword no axe no saw no melee weapon, no text no logo"
        ),
    },
    {
        "variation": 11,
        "mode": "txt",
        "seed": 73017,
        "prompt": (
            "ToME RPG subclass icon like alchemist and archmage icons, magic caster emblem, "
            "hooded smog devil warlock portrait with brass devil horns and glowing teal eyes, "
            "holding a vertical steam-staff topped with a refined arcane gem, "
            "industrial smog and arcane sparks swirling, corrupt vim purple mixed with steam white, "
            "black background, bold outlines, NOT a warrior, no blades, no text"
        ),
    },
    {
        "variation": 12,
        "mode": "txt",
        "seed": 73033,
        "prompt": (
            "fantasy RPG class icon Tales of Maj'Eyal, steam and arcane magic theme, "
            "steamtech mage staff crossed with a focus lens monocle, wrapped in green toxic smog, "
            "devilish brass horns motif, violet mana glow, black background, painted comic style, no melee weapons, no text"
        ),
    },
    # img2img from alchemist / archmage / annihilator (staff+orb magic tech)
    {
        "variation": 13,
        "mode": "i2i",
        "seed": 73101,
        "strength": 0.74,
        "ref": "alchemist",
        "prompt": (
            "Tales of Maj'Eyal class icon same painted style as reference, black background, "
            "smog devil steam-arcane mage: brass steam-staff with venting toxic green smog, "
            "violet arcane crystal focus, horned devil face formed of steam behind the staff, "
            "magic caster icon not melee, no swords no saws, no text"
        ),
    },
    {
        "variation": 14,
        "mode": "i2i",
        "seed": 73119,
        "strength": 0.70,
        "ref": "archmage",
        "prompt": (
            "Tales of Maj'Eyal class icon same painted style as reference, black background, "
            "smog devil: arcane steam warlock with steam-staff and choking industrial smog, "
            "teal toxic vapor, brass pipes, violet mana, devil horns, spellcaster emblem, no melee weapons, no text"
        ),
    },
    {
        "variation": 15,
        "mode": "i2i",
        "seed": 73137,
        "strength": 0.72,
        "ref": "annihilator",
        "prompt": (
            "Tales of Maj'Eyal class icon same painted style as reference, black background, "
            "replace guns with a single ornate steam-staff and focus lens, toxic smog clouds, "
            "arcane violet orb on staff tip, devilish steamtech mage emblem, no firearms no melee blades, no text"
        ),
    },
]


def prepare_ref(path: Path, size: int = 512) -> str:
    im = Image.open(path).convert("RGBA")
    bg = Image.new("RGBA", im.size, (0, 0, 0, 255))
    bg.alpha_composite(im)
    rgb = bg.convert("RGB").resize((size, size), Image.Resampling.LANCZOS)
    tmp = OUTPUT / "raw" / f"_ref_{path.stem}_{size}.png"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    rgb.save(tmp)
    return base64.b64encode(tmp.read_bytes()).decode("ascii")


def run_i2i(job: dict, api_url: str) -> Path:
    out = OUTPUT / "raw" / f"{STEM}_v{job['variation']}_s{job['seed']}_i2i.png"
    if out.exists():
        out.unlink()
    body = {
        "prompt": job["prompt"],
        "negative_prompt": NEGATIVE
        + ", sword, greatsword, axe, saw blade, buzzsaw, dagger, melee weapon, warrior, armored knight",
        "width": 512,
        "height": 512,
        "size": "512x512",
        "steps": 28,
        "guidance_scale": 7.2,
        "seed": job["seed"],
        "n": 1,
        "image": prepare_ref(REFS[job["ref"]], 512),
        "strength": job["strength"],
        "response_format": "b64_json",
    }
    req = urllib.request.Request(
        api_url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=900) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    item = (payload.get("data") or [None])[0]
    if not item:
        raise RuntimeError(f"no image: {list(payload.keys())}")
    if "b64_json" in item:
        out.write_bytes(base64.b64decode(item["b64_json"]))
    else:
        raise RuntimeError(f"unexpected keys: {list(item.keys())}")
    return out


def finalize_candidate(variation: int, seed: int, raw_path: Path, prompt: str, mask128, mask32, extra: dict):
    CAND.mkdir(parents=True, exist_ok=True)
    raw = Image.open(raw_path)
    icon128 = _compose_class_icon(raw, mask128, 128)
    icon32 = _compose_class_icon(icon128.convert("RGB"), mask32, 32)
    p128 = CAND / f"{STEM}_128_bg_v{variation}.png"
    p32 = CAND / f"{STEM}_32_bg_v{variation}.png"
    icon128.save(p128)
    icon32.save(p32)
    meta = {
        "ok": True,
        "class": "smog_devil",
        "variation": variation,
        "seed": seed,
        "prompt": prompt,
        "path_128": str(p128),
        "path_32": str(p32),
        "theme": "steam+arcane magic staff, not melee",
        **extra,
    }
    p128.with_suffix(".meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print("OK", p128.name)
    return p128, p32


def install(variation: int):
    p128 = CAND / f"{STEM}_128_bg_v{variation}.png"
    p32 = CAND / f"{STEM}_32_bg_v{variation}.png"
    if not p128.exists() or not p32.exists():
        raise SystemExit(f"missing variation {variation}")
    final = OUTPUT / "final"
    final.mkdir(parents=True, exist_ok=True)
    shutil.copy2(p128, final / f"{STEM}_128_bg.png")
    shutil.copy2(p32, final / f"{STEM}_32_bg.png")
    MOD_ICONS.mkdir(parents=True, exist_ok=True)
    shutil.copy2(p128, MOD_ICONS / f"{STEM}_128_bg.png")
    shutil.copy2(p32, MOD_ICONS / f"{STEM}_32_bg.png")
    print(f"Installed variation {variation} -> {MOD_ICONS}")


def main() -> int:
    api = detect_server(verbose=True)
    if not api:
        print("SD not ready")
        return 1
    mask128, mask32 = _load_masks()
    neg = NEGATIVE + ", sword, greatsword, axe, saw blade, buzzsaw, dagger, melee weapon, warrior"

    for job in JOBS:
        v, seed = job["variation"], job["seed"]
        print(f"\n=== smog_devil v{v} mode={job['mode']} seed={seed} ===")
        try:
            if job["mode"] == "txt":
                raw = OUTPUT / "raw" / f"{STEM}_v{v}_s{seed}.png"
                if raw.exists():
                    raw.unlink()
                result = generate_sd_image(
                    job["prompt"],
                    raw,
                    negative_prompt=neg,
                    delivery_w=128,
                    delivery_h=128,
                    kind="icon",
                    seed=seed,
                    guidance_scale=7.4,
                    lock_label=f"class_icon_{STEM}_{v}",
                )
                if not result.ok:
                    print("FAIL", result.error)
                    continue
                raw_path = Path(result.output_path)
                extra = {"mode": "txt2img"}
            else:
                raw_path = run_i2i(job, api)
                extra = {"mode": "img2img", "ref": job["ref"], "strength": job["strength"]}
            finalize_candidate(v, seed, raw_path, job["prompt"], mask128, mask32, extra)
        except Exception as exc:
            print("FAIL", exc)

    print("\nCandidates ready in", CAND)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
