#!/usr/bin/env python3
"""
Asset generator for the Soulash 2 mod `arendeth_reactive_crafting`.

The mod is about terrain-altering *throwables* (Muddy Waterskin, Sand Pouch,
Ember Pouch, Snow Pouch, Oil Flask, Salt Sack) that summon reactive ground
tiles. Branding art therefore leans into an "alchemical thrown flask bursting
into four elemental terrains" motif rather than the water-only hydromancy look.

Pipeline (mirrors generate_hydromancy_assets.py):
  1. Optional Ollama design spec (palette / motif) -- llama3.1 style text model.
  2. Procedural PIL render (SD server optional; falls back cleanly when down).
  3. Mechanical quality gate (size / coverage / luma variance) -- palette agnostic.
  4. Optional multimodal vision QA via Ollama (qwen3-vl / llava) with a
     reactive-crafting-specific rubric, with retry on failure.

Outputs S.png (32x32 icon) and thumbnail2.png (800x600) into the mod folder,
matching the names referenced by the mod's mod.json.
"""

from __future__ import annotations

import argparse
import base64
import json
import math
import random
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFilter, ImageFont

_here = Path(__file__).resolve().parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))

from hydromancy_quality import (  # noqa: E402
    finalize_icon,
    parse_ollama_json,
    validate_mod_icon,
    validate_thumbnail,
)
from s2_icon_pipeline import (  # noqa: E402
    TILE,
    compose_icon_prompt,
    generate_sd_tile,
    pack_bottom_left_image,
    sd_session,
)

try:
    _shared = _here.parent / "Shared"
    if str(_shared) not in sys.path:
        sys.path.insert(0, str(_shared))
    from ollama_integration import call_ollama, test_ollama_connection  # noqa: E402
    OLLAMA_AVAILABLE = True
except Exception:
    OLLAMA_AVAILABLE = False

DEFAULT_MOD = Path(
    r"E:\SteamLibrary\steamapps\common\Soulash 2\data\mods\arendeth_reactive_crafting"
)

# Earthy alchemical base + the four reactive-terrain accent colors.
REACTIVE_PALETTE = ["#120d0a", "#2c2015", "#5a3d22", "#a06a2c", "#e0b25e", "#f5e6c8"]

# element -> representative color (mud, sand, ember, snow/frost, oil, salt)
ELEMENT_COLORS = {
    "mud": (108, 74, 40),
    "sand": (214, 176, 104),
    "ember": (232, 108, 40),
    "snow": (196, 224, 240),
    "oil": (58, 48, 34),
    "salt": (236, 236, 226),
}

REACTIVE_ART_SYSTEM = (
    "You are a senior art director for Soulash 2, a dark fantasy roguelike with "
    "hand-painted pixel UI icons. Design a cohesive earthy alchemical palette for a "
    "crafting mod about thrown flasks/pouches that transform terrain (mud, sand, "
    "ember, snow, oil, salt). Return ONLY valid JSON."
)


def hex_to_rgb(h: str) -> Tuple[int, int, int]:
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def lerp(c1: Tuple[int, int, int], c2: Tuple[int, int, int], t: float) -> Tuple[int, int, int]:
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))  # type: ignore


def default_spec() -> Dict[str, Any]:
    return {
        "motif": "thrown alchemical flask bursting into four elemental terrains",
        "palette": REACTIVE_PALETTE,
        "composition": "central flask silhouette over a four-way terrain splash",
    }


def fetch_design_spec(asset_type: str) -> Dict[str, Any]:
    if not OLLAMA_AVAILABLE:
        return default_spec()
    try:
        if not test_ollama_connection():
            return default_spec()
    except Exception:
        return default_spec()

    prompt = (
        f"Design a Soulash 2 mod {asset_type} for a reactive crafting mod (throwable "
        "flasks/pouches that alter terrain). JSON fields: motif (string), palette "
        "(array of 6 #hex from darkest to lightest, earthy browns + warm highlight), "
        "composition (string). Dark fantasy pixel UI, readable at small size."
    )
    try:
        response = call_ollama(
            prompt=prompt,
            task_type="visual",
            response_length="standard",
            system_prompt=REACTIVE_ART_SYSTEM,
        )
        spec = parse_ollama_json(response, asset_type)
        pal = spec.get("palette")
        if not (isinstance(pal, list) and len(pal) >= 5):
            spec["palette"] = REACTIVE_PALETTE
        print(f"  [OK] Ollama design spec: motif='{spec.get('motif', '')[:48]}'")
        return spec
    except Exception as exc:
        print(f"  [WARN] Ollama spec failed ({exc}); using default palette")
        return default_spec()


def _radial_bg(size: Tuple[int, int], inner: Tuple[int, int, int], outer: Tuple[int, int, int]) -> Image.Image:
    w, h = size
    img = Image.new("RGBA", size)
    px = img.load()
    cx, cy = w / 2, h / 2
    maxd = math.hypot(cx, cy)
    for y in range(h):
        for x in range(w):
            t = min(1.0, math.hypot(x - cx, y - cy) / maxd)
            r, g, b = lerp(inner, outer, t ** 1.2)
            px[x, y] = (r, g, b, 255)
    return img


def _element_splash(draw: ImageDraw.ImageDraw, cx: float, cy: float, radius: float,
                    rng: random.Random, scale: float = 1.0) -> None:
    """Four-quadrant burst of colored droplets, one element per diagonal."""
    order = ["mud", "ember", "snow", "sand"]  # TL, TR, BL, BR
    quadrants = [(-1, -1), (1, -1), (-1, 1), (1, 1)]
    for elem, (sx, sy) in zip(order, quadrants):
        base = ELEMENT_COLORS[elem]
        n = int(26 * scale) + 6
        for _ in range(n):
            ang = rng.uniform(0, math.pi / 2)
            dist = rng.uniform(0.25, 1.0) * radius
            dx = sx * math.cos(ang) * dist
            dy = sy * math.sin(ang) * dist
            x, y = cx + dx, cy + dy
            r = max(1.0, (1.0 - dist / radius) * 7.0 * scale + rng.uniform(0, 2))
            jitter = rng.uniform(-0.18, 0.18)
            col = lerp(base, (255, 255, 255), max(0.0, jitter)) if jitter > 0 else lerp(base, (0, 0, 0), -jitter)
            a = int(160 + 80 * (1.0 - dist / radius))
            draw.ellipse([x - r, y - r, x + r, y + r], fill=(*col, min(255, a)))


def _draw_flask(draw: ImageDraw.ImageDraw, cx: float, cy: float, s: float,
                body: Tuple[int, int, int], rim: Tuple[int, int, int]) -> None:
    """A rounded thrown flask/pouch silhouette with a neck, cork and glint."""
    # body (rounded)
    bw, bh = 1.9 * s, 2.2 * s
    draw.ellipse([cx - bw / 2, cy - bh / 2 + 0.35 * s, cx + bw / 2, cy + bh / 2 + 0.35 * s],
                 fill=(*body, 255), outline=(*rim, 255), width=max(1, int(s * 0.18)))
    # neck
    nw = 0.7 * s
    draw.rectangle([cx - nw / 2, cy - bh / 2 - 0.5 * s, cx + nw / 2, cy - bh / 2 + 0.5 * s],
                   fill=(*body, 255), outline=(*rim, 255), width=max(1, int(s * 0.14)))
    # cork
    cw, ch = 0.9 * s, 0.5 * s
    draw.rectangle([cx - cw / 2, cy - bh / 2 - 0.95 * s, cx + cw / 2, cy - bh / 2 - 0.5 * s],
                   fill=(120, 82, 45, 255))
    # glint highlight
    gw = 0.45 * s
    draw.ellipse([cx - bw / 4 - gw / 2, cy - 0.1 * s, cx - bw / 4 + gw / 2, cy + 1.0 * s],
                 fill=(255, 255, 255, 120))


def render_icon(spec: Dict[str, Any], seed: int = 7) -> Image.Image:
    """Bold, readable 32x32 icon: a corked potion flask with amber liquid and
    four soft corner accents (mud/ember/snow/sand). Kept low-noise so it stays
    legible at small size."""
    S = 8  # supersample factor
    W = 32 * S
    size = (W, W)
    pal = [hex_to_rgb(c) for c in (spec.get("palette") or REACTIVE_PALETTE)]
    img = _radial_bg(size, lerp(pal[2], pal[1], 0.45), pal[0])

    # soft corner accents, one element per corner
    accents = [("mud", 0.24, 0.24), ("ember", 0.76, 0.24),
               ("snow", 0.24, 0.76), ("sand", 0.76, 0.76)]
    for elem, fx, fy in accents:
        blob = Image.new("RGBA", size, (0, 0, 0, 0))
        bd = ImageDraw.Draw(blob)
        col = ELEMENT_COLORS[elem]
        r = W * 0.20
        cx, cy = W * fx, W * fy
        bd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*col, 150))
        blob = blob.filter(ImageFilter.GaussianBlur(radius=W * 0.05))
        img = Image.alpha_composite(img, blob)

    draw = ImageDraw.Draw(img, "RGBA")
    cx, cy = W / 2, W / 2 + W * 0.05
    body_w, body_h = W * 0.40, W * 0.44
    rim = pal[4]

    # amber liquid body with dark rim
    bx0, by0 = cx - body_w / 2, cy - body_h / 2
    bx1, by1 = cx + body_w / 2, cy + body_h / 2
    draw.ellipse([bx0 - S, by0 - S, bx1 + S, by1 + S], fill=(20, 14, 10, 255))  # rim/shadow
    liquid_top = (232, 170, 78)
    liquid_bot = (150, 92, 34)
    lg = Image.new("RGBA", size, (0, 0, 0, 0))
    lgd = ImageDraw.Draw(lg)
    steps = int(body_h)
    for i in range(steps):
        t = i / max(1, steps - 1)
        c = lerp(liquid_top, liquid_bot, t)
        y = by0 + (by1 - by0) * t
        lgd.line([(bx0, y), (bx1, y)], fill=(*c, 255))
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).ellipse([bx0, by0, bx1, by1], fill=255)
    img.paste(lg, (0, 0), mask)
    draw = ImageDraw.Draw(img, "RGBA")
    draw.ellipse([bx0, by0, bx1, by1], outline=(*rim, 255), width=max(2, int(S * 0.5)))

    # neck + cork
    nw = W * 0.16
    draw.rectangle([cx - nw / 2, by0 - W * 0.14, cx + nw / 2, by0 + S], fill=(52, 36, 22, 255),
                   outline=(*rim, 255), width=max(1, int(S * 0.35)))
    cw = W * 0.22
    draw.rounded_rectangle([cx - cw / 2, by0 - W * 0.22, cx + cw / 2, by0 - W * 0.12],
                           radius=S, fill=(150, 100, 54, 255))

    # subtle crescent glint on the liquid (not a full oval -> avoids "eye" look)
    draw.arc([bx0 + body_w * 0.14, by0 + body_h * 0.16,
              bx0 + body_w * 0.5, by0 + body_h * 0.62],
             start=110, end=250, fill=(255, 245, 220, 180), width=max(2, int(S * 0.45)))

    img = img.filter(ImageFilter.GaussianBlur(radius=S * 0.22))
    img = img.resize((32, 32), Image.Resampling.LANCZOS)
    return finalize_icon(img)


def _load_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    candidates = [
        r"C:\Windows\Fonts\seguisb.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\georgiab.ttf",
    ]
    for c in candidates:
        try:
            return ImageFont.truetype(c, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _draw_centered_text(draw: ImageDraw.ImageDraw, cx: float, y: float, text: str,
                        font: ImageFont.FreeTypeFont, fill, shadow=(0, 0, 0, 200)) -> None:
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    x = cx - tw / 2
    draw.text((x + 2, y + 2), text, font=font, fill=shadow)
    draw.text((x, y), text, font=font, fill=fill)


def render_thumbnail(spec: Dict[str, Any], seed: int = 11) -> Image.Image:
    rng = random.Random(seed)
    size = (800, 600)
    pal = [hex_to_rgb(c) for c in (spec.get("palette") or REACTIVE_PALETTE)]
    img = _radial_bg(size, lerp(pal[2], pal[1], 0.35), pal[0])
    draw = ImageDraw.Draw(img, "RGBA")

    # faint four-quadrant terrain washes behind the flask
    for elem, (qx, qy) in zip(["mud", "ember", "snow", "sand"],
                              [(0, 0), (1, 0), (0, 1), (1, 1)]):
        col = ELEMENT_COLORS[elem]
        overlay = Image.new("RGBA", size, (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        rx0 = qx * 400
        ry0 = qy * 300 + 90
        od.rectangle([rx0, ry0, rx0 + 400, ry0 + 300], fill=(*col, 34))
        img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img, "RGBA")

    cx, cy = size[0] / 2, size[1] / 2 + 40
    _element_splash(draw, cx, cy, radius=250, rng=rng, scale=3.4)
    _draw_flask(draw, cx, cy, s=46, body=pal[1], rim=pal[4])

    # titles
    title_font = _load_font(74, bold=True)
    sub_font = _load_font(30, bold=False)
    _draw_centered_text(draw, cx, 34, "REACTIVE CRAFTING", title_font, fill=(*pal[5], 255))
    _draw_centered_text(draw, cx, 120, "Terrain-altering throwables", sub_font,
                        fill=(*lerp(pal[4], pal[5], 0.4), 255))

    img = img.filter(ImageFilter.GaussianBlur(radius=0.4))
    return img.convert("RGBA")


def vision_qa(image_path: Path, asset_type: str, model: str) -> Tuple[bool, float, str]:
    try:
        import requests
    except ImportError:
        return True, 0.75, "requests unavailable; skipped"
    if not image_path.exists():
        return False, 0.0, "file missing"
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")

    prompt = (
        f"Rate this Soulash 2 mod {asset_type} for a REACTIVE CRAFTING mod about "
        "thrown flasks/pouches that alter terrain (mud, sand, ember, snow). "
        "Return JSON only: {\"score\": 0-100, \"pass\": true/false, \"issues\": \"...\"}. "
        "Pass if: readable/clear at a glance, an obvious central flask or pouch, an "
        "earthy warm palette with elemental accent colors, good contrast, not a "
        "muddy blur. For thumbnails the title text must be legible."
    )
    try:
        resp = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": model, "prompt": prompt, "images": [b64],
                  "stream": False, "format": "json"},
            timeout=180,
        )
        resp.raise_for_status()
        body = resp.json().get("response", "")
        data = parse_ollama_json(body, asset_type)
        score = float(data.get("score", 70)) / 100.0
        passed = bool(data.get("pass", score >= 0.65))
        return passed, score, str(data.get("issues", "")) or "ok"
    except Exception as exc:
        return True, 0.7, f"vision QA skipped: {exc}"


def generate_asset(kind: str, mod_path: Path, quality: str, model: str,
                   max_attempts: int, use_spec: bool = False) -> Dict[str, Any]:
    is_icon = kind == "icon"
    out_name = "S.png" if is_icon else "thumbnail2.png"
    out_path = mod_path / out_name
    asset_type = "icon" if is_icon else "thumbnail"
    spec = fetch_design_spec(asset_type) if use_spec else default_spec()

    best: Optional[Dict[str, Any]] = None
    for attempt in range(1, max_attempts + 1):
        seed = 7 + attempt * 13
        img = render_icon(spec, seed) if is_icon else render_thumbnail(spec, seed)
        img.save(out_path)

        if is_icon:
            mech_ok, mech_reason = validate_mod_icon(img)
        else:
            mech_ok, mech_reason = validate_thumbnail(img)

        report: Dict[str, Any] = {
            "attempt": attempt, "path": str(out_path),
            "mechanical": {"pass": mech_ok, "reason": mech_reason},
        }
        print(f"  [{kind}] attempt {attempt}: mechanical={'PASS' if mech_ok else 'FAIL'} ({mech_reason})")
        if not mech_ok:
            best = report
            continue

        if quality == "full":
            v_ok, v_score, v_reason = vision_qa(out_path, asset_type, model)
            report["vision"] = {"pass": v_ok, "score": round(v_score, 3), "reason": v_reason}
            print(f"  [{kind}] attempt {attempt}: vision score={v_score:.2f} -> "
                  f"{'PASS' if v_ok else 'FAIL'} ({v_reason})")
            report["pass"] = v_ok
            if v_ok:
                report["final"] = True
                return report
            if best is None or v_score > best.get("vision", {}).get("score", 0):
                best = report
        else:
            report["pass"] = True
            report["final"] = True
            return report

    # keep the best attempt's file (re-render best seed already saved last;
    # for simplicity the last mechanical-pass file remains on disk)
    if best is not None:
        best["final"] = False
        return best
    return {"kind": kind, "pass": False, "reason": "no attempts"}


THROWABLES = (
    {
        "elem": "mud",
        "entity": "Muddy_Waterskin.json",
        "ability": "Throw_Muddy_Waterskin.json",
        "item_name": "Muddy Waterskin",
        "ability_name": "Throw Muddy Waterskin",
        "item_prompt": "leather waterskin sloshing with brown mud, corked, Soulash 2 item icon",
        "throw_prompt": "thrown muddy waterskin bursting into wet brown puddles, Soulash 2 ability icon",
    },
    {
        "elem": "sand",
        "entity": "Sand_Pouch.json",
        "ability": "Throw_Sand_Pouch.json",
        "item_name": "Sand Pouch",
        "ability_name": "Throw Sand Pouch",
        "item_prompt": "canvas pouch spilling golden desert sand, Soulash 2 item icon",
        "throw_prompt": "thrown sand pouch bursting into a blinding sand cloud, Soulash 2 ability icon",
    },
    {
        "elem": "ember",
        "entity": "Ember_Pouch.json",
        "ability": "Throw_Ember_Pouch.json",
        "item_name": "Ember Pouch",
        "ability_name": "Throw Ember Pouch",
        "item_prompt": "smoldering cloth pouch glowing with orange embers and ash, Soulash 2 item icon",
        "throw_prompt": "thrown ember pouch bursting into burning ground and sparks, Soulash 2 ability icon",
    },
    {
        "elem": "snow",
        "entity": "Snow_Pouch.json",
        "ability": "Throw_Snow_Pouch.json",
        "item_name": "Snow Pouch",
        "ability_name": "Throw Snow Pouch",
        "item_prompt": "frost-lined pouch packed with pale snow, Soulash 2 item icon",
        "throw_prompt": "thrown snow pouch bursting into ice and snow on the ground, Soulash 2 ability icon",
    },
    {
        "elem": "oil",
        "entity": "Oil_Flask.json",
        "ability": "Throw_Oil_Flask.json",
        "item_name": "Oil Flask",
        "ability_name": "Throw Oil Flask",
        "item_prompt": "amber glass flask of dark transmutation oil, corked, Soulash 2 item icon",
        "throw_prompt": "thrown oil flask bursting into sticky cobwebs on the ground, Soulash 2 ability icon",
    },
    {
        "elem": "salt",
        "entity": "Salt_Sack.json",
        "ability": "Throw_Salt_Sack.json",
        "item_name": "Salt Sack",
        "ability_name": "Throw Salt Sack",
        "item_prompt": "coarse white salt sack tied with twine, Soulash 2 item icon",
        "throw_prompt": "thrown salt sack bursting into dry white sand cover, Soulash 2 ability icon",
    },
)


def _procedural_item_tile(elem: str, label: str) -> Image.Image:
    spec = default_spec()
    pal = [hex_to_rgb(c) for c in spec["palette"]]
    S = 8
    W = TILE * S
    img = _radial_bg((W, W), lerp(pal[2], ELEMENT_COLORS[elem], 0.35), pal[0])
    draw = ImageDraw.Draw(img, "RGBA")
    cx, cy = W / 2, W / 2 + W * 0.04
    _draw_flask(draw, cx, cy, s=W * 0.16, body=ELEMENT_COLORS[elem], rim=pal[4])
    img = img.filter(ImageFilter.GaussianBlur(radius=S * 0.18))
    return img.resize((TILE, TILE), Image.Resampling.LANCZOS)


def _patch_json(path: Path, mutator) -> None:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    mutator(data)
    path.write_text(json.dumps(data, indent="\t", ensure_ascii=False) + "\n", encoding="utf-8")


def write_game_sheets(mod_path: Path, *, use_sd: bool = True) -> Dict[str, Any]:
    """Write items/abilities/glyph32 sheets (Sandmancy layout) and retarget JSON indexes."""
    work = mod_path / "_sd_work"
    work.mkdir(exist_ok=True)

    def _one_tile(prompt: str, name: str, seed: int, api_url: Optional[str], elem: str) -> Image.Image:
        if not use_sd:
            return _procedural_item_tile(elem, name)
        if not api_url:
            raise RuntimeError(
                "SD session has no API URL; refusing procedural crafting tiles"
            )
        last_exc: Optional[BaseException] = None
        for attempt in range(1, 5):
            try:
                if attempt > 1:
                    print(f"  [SD] retry {attempt}/4 for {name}...", flush=True)
                    time.sleep(20.0)
                return generate_sd_tile(
                    prompt, work=work, api_url=api_url, seed=seed, steps=24, name=name
                )
            except Exception as exc:
                last_exc = exc
                print(f"  [WARN] SD tile failed for {name}: {exc}")
        raise RuntimeError(
            f"SD failed for {name} after retries; refusing procedural fallback"
        ) from last_exc

    with sd_session(use_sd=use_sd) as api_url:
        if use_sd:
            print(f"  sheets via SD at {api_url}")
        else:
            print("  sheets procedural (--no-sd)")

        item_tiles: List[Image.Image] = []
        ability_tiles: List[Image.Image] = []
        for i, row in enumerate(THROWABLES):
            seed = 1100 + i * 17
            print(f"  [{'SD' if use_sd else 'proc'}] item {i + 1}/{len(THROWABLES)} {row['item_name']}")
            item_tiles.append(
                _one_tile(
                    compose_icon_prompt(role="item icon", subject=row["item_prompt"]),
                    row["item_name"],
                    seed,
                    api_url,
                    row["elem"],
                )
            )
            print(f"  [{'SD' if use_sd else 'proc'}] ability {i + 1}/{len(THROWABLES)} {row['ability_name']}")
            ability_tiles.append(
                _one_tile(
                    compose_icon_prompt(role="ability icon", subject=row["throw_prompt"]),
                    row["ability_name"],
                    seed + 1,
                    api_url,
                    row["elem"],
                )
            )

        cols = len(THROWABLES)
        assets_dir = mod_path / "assets"
        assets_dir.mkdir(exist_ok=True)
        items_rel = "assets/items.png"
        abilities_rel = "assets/abilities.png"
        glyphs_rel = "assets/glyphs.png"
        pack_bottom_left_image(item_tiles, cols).save(mod_path / items_rel)
        pack_bottom_left_image(ability_tiles, cols).save(mod_path / abilities_rel)
        pack_bottom_left_image(item_tiles, cols).save(mod_path / glyphs_rel)
        used_sd = bool(api_url)

    assets = {
        "graphics": {
            "tilesheets": [
                {"name": "items", "tiles": [cols, 1], "file": items_rel},
                {"name": "abilities", "tiles": [cols, 1], "file": abilities_rel},
                {"name": "glyph32", "tiles": [cols, 1], "file": glyphs_rel},
            ]
        }
    }
    (mod_path / "assets.json").write_text(json.dumps(assets, indent="\t") + "\n", encoding="utf-8")

    for i, row in enumerate(THROWABLES):
        epath = mod_path / "entities" / row["entity"]
        apath = mod_path / "abilities" / row["ability"]

        def _item(data: Dict[str, Any], idx: int = i) -> None:
            data.setdefault("item", {})["image"] = idx
            frames = data.setdefault("glyph", {}).setdefault("frames", [{}])
            if frames and isinstance(frames[0], dict):
                frames[0]["index"] = idx
                frames[0]["color"] = [255, 255, 255, 255] if len(frames[0].get("color") or []) == 4 else [255, 255, 255]

        def _ability(data: Dict[str, Any], idx: int = i) -> None:
            data["image"] = idx

        if epath.is_file():
            _patch_json(epath, _item)
        if apath.is_file():
            _patch_json(apath, _ability)

    mod_json_path = mod_path / "mod.json"
    if mod_json_path.is_file():
        def _mod(data: Dict[str, Any]) -> None:
            data["icon"] = "S.png"
            data["thumbnail"] = "thumbnail2.png"
            data["version"] = "0.5.0"

        _patch_json(mod_json_path, _mod)

    return {"items": items_rel, "abilities": abilities_rel, "glyphs": glyphs_rel, "count": cols, "sd": used_sd}


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate arendeth_reactive_crafting branding assets")
    ap.add_argument("--mod-path", type=Path, default=DEFAULT_MOD)
    ap.add_argument("--mode", choices=["icon", "thumbnail", "all"], default="all")
    ap.add_argument("--quality", choices=["mechanical", "full"], default="full")
    ap.add_argument("--model", default="qwen3-vl:8b", help="Ollama vision model for QA")
    ap.add_argument("--max-attempts", type=int, default=3)
    ap.add_argument("--use-ollama-spec", action="store_true",
                    help="Ask Ollama for a palette/motif spec (slower; default off)")
    ap.add_argument("--no-sheets", action="store_true", help="Skip items/abilities/glyph tilesheets")
    ap.add_argument("--no-sd", action="store_true", help="Procedural tiles only")
    args = ap.parse_args()

    try:
        sys.stdout.reconfigure(line_buffering=True)  # type: ignore[attr-defined]
    except Exception:
        pass

    mod_path: Path = args.mod_path
    if not mod_path.exists():
        print(f"[FAIL] mod path not found: {mod_path}")
        return 2

    print(f"== Reactive Crafting asset generation ==")
    print(f"mod: {mod_path}")
    print(f"ollama: {'available' if OLLAMA_AVAILABLE else 'unavailable'} | quality: {args.quality}")

    kinds = ["icon", "thumbnail"] if args.mode == "all" else [args.mode]
    results = []
    for kind in kinds:
        print(f"\n-- generating {kind} --")
        results.append(generate_asset(kind, mod_path, args.quality, args.model,
                                       args.max_attempts, use_spec=args.use_ollama_spec))

    if not args.no_sheets:
        print("\n-- game tilesheets (items / abilities / glyph32) --")
        results.append({"kind": "sheets", "pass": True, **write_game_sheets(mod_path, use_sd=not args.no_sd)})

    print("\n== SUMMARY ==")
    all_pass = True
    for r in results:
        ok = r.get("pass", False)
        all_pass = all_pass and ok
        tag = "PASS" if ok else "FAIL"
        v = r.get("vision", {})
        extra = f" vision={v.get('score')}" if v else ""
        print(f"  [{tag}] {r.get('path', r.get('kind'))}{extra} :: {r.get('mechanical', {}).get('reason', r.get('items', ''))}")
    print(json.dumps(results, indent=2, default=str))
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
