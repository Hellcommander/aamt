#!/usr/bin/env python3
"""
Broodmother Mutation Asset Generator (Ollama + SD3.5 draft pipeline)

This is a remake of the earlier Broodmother generator:
- No procedural "basic shapes" rendering for final assets.
- Uses Tools/Shared Ollama integration to generate rich design + prompt packs.
- Optionally generates *design drafts* using SD3.5 (via Tools/Shared StableDiffusionIntegration.psm1),
  then exports downscaled game-ready images (PNG) to the mod folders.

Design intent:
- SD3.5 drafts are high-res concept renders to improve quality and consistency.
- Final exports are derived from drafts (crop + resize + light post-processing), not hand-drawn shapes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PIL import Image, ImageEnhance, ImageDraw, ImageFont, ImageFilter

# Fix Windows console encoding
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

# ---- Shared Ollama integration (REQUIRED) ----
_shared_dir = Path(__file__).resolve().parent.parent / "Shared"
_ollama_path = _shared_dir / "ollama_integration.py"
if not _ollama_path.exists():
    raise RuntimeError(f"Shared Ollama integration not found: {_ollama_path}")

if str(_shared_dir) not in sys.path:
    sys.path.insert(0, str(_shared_dir))

from ollama_integration import (
    call_ollama,
    test_ollama_connection,
    ensure_model_loaded,
    unload_model,
    swap_model,
    get_loaded_models,
    unload_all_models,
    get_current_model,
    get_available_models,
)  # type: ignore

# Biomutation / Broodmother content must not be sanitized by filtered chat models.
# Prefer wizardlm-uncensored for all prompt-pack / art-director Ollama calls.
DEFAULT_OLLAMA_MODEL = "wizardlm-uncensored:latest"
OLLAMA_MODEL = DEFAULT_OLLAMA_MODEL

# Import event bus for parallel processing
_event_bus_path = _shared_dir / "event_bus.py"
if _event_bus_path.exists():
    try:
        sys.path.insert(0, str(_shared_dir))
        from event_bus import EventBus, EventType, Event, EventResult  # type: ignore
        EVENT_BUS_AVAILABLE = True
    except ImportError:
        EVENT_BUS_AVAILABLE = False
else:
    EVENT_BUS_AVAILABLE = False

# Import cache manager
_cache_path = _shared_dir / "cache_manager.py"
if _cache_path.exists():
    try:
        sys.path.insert(0, str(_shared_dir))
        from cache_manager import get_cache, CacheManager  # type: ignore
        CACHE_AVAILABLE = True
    except ImportError:
        CACHE_AVAILABLE = False
else:
    CACHE_AVAILABLE = False

# Import multi-agent art director
_multi_agent_path = _shared_dir / "multi_agent_art_director.py"
if _multi_agent_path.exists():
    try:
        sys.path.insert(0, str(_shared_dir))
        from multi_agent_art_director import (
            MultiAgentArtDirector,
            AgentRole,
            AggregatedFeedback,
        )  # type: ignore
        MULTI_AGENT_AVAILABLE = True
    except ImportError:
        MULTI_AGENT_AVAILABLE = False
        MultiAgentArtDirector = None
        AgentRole = None
        AggregatedFeedback = None
else:
    MULTI_AGENT_AVAILABLE = False
    MultiAgentArtDirector = None
    AgentRole = None
    AggregatedFeedback = None

# Optional audio generator
_audio_gen_path = Path(__file__).parent / "qud_audio_generator.py"
AUDIO_GENERATOR_AVAILABLE = False
QudAudioGenerator = None
np = None
sf = None
try:
    import numpy as np
    import soundfile as sf
    if _audio_gen_path.exists():
        try:
            sys.path.insert(0, str(Path(__file__).parent))
            from qud_audio_generator import QudAudioGenerator
            AUDIO_GENERATOR_AVAILABLE = True
        except ImportError:
            AUDIO_GENERATOR_AVAILABLE = False
except ImportError:
    AUDIO_GENERATOR_AVAILABLE = False


@dataclass(frozen=True)
class Sd35Params:
    prompt: str
    negative_prompt: str
    # 512x768 (2:3) matches vanilla CoQ 16x24 tiles. T5 + fp16 + model_cpu_offload
    # on the server (full-GPU+T5 thrashes 11GB WDDM). Avoid 1024².
    width: int = 512
    height: int = 768
    steps: int = 12
    guidance_scale: float = 7.0
    seed: int = 0
    enhance_with_ollama: bool = False  # Keep False: Ollama+SD fight for 11GB VRAM and hang the client
    auto_start_server: bool = True


@dataclass(frozen=True)
class AssetJob:
    asset_id: str
    sd35: Sd35Params
    draft_path: Path
    export_paths: List[Tuple[Path, Tuple[int, int]]]  # (path, size)
    meta: Dict


def _write_json(path: Path, data: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# All SD job prompt keys (34). Combined keys like "ui_a / ui_b" are never valid.
REQUIRED_PROMPT_KEYS: List[str] = [
    "icon",
    "sack",
    "broodling_ground",
    "broodling_flying",
    "broodling_crystal",
    "broodling_phantom",
    "broodling_bombardier",
    "broodling_symbiote",
    "broodling_tunneler",
    "broodling_mimic",
    "broodling_shard",
    "broodling_swarmling",
    "broodling_voidling",
    "broodling_fluxling",
    "broodling_leechling",
    "broodling_mindling",
    "broodling_glowling",
    "broodling_rustling",
    "broodling_necroling",
    "broodling_thornling",
    "broodling_mandibore",
    "preview",
    "texture_carapace",
    "texture_membrane",
    "texture_biometal",
    "texture_chitin",
    "ui_biomod_chip",
    "ui_birth_badge",
    "ui_evolution_node",
    "ui_swarm_frame",
    "ui_panel",
    "ui_button",
    "ui_menu_row",
    "ui_status_strip",
    "ui_tier_pip",
]

_UI_TEXTURE_PROMPT_KEYS = {
    k
    for k in REQUIRED_PROMPT_KEYS
    if k.startswith("ui_") or k.startswith("texture_") or k == "preview"
}

# Truecolor only where the 18-color / ≤3-per-tile rule cannot sell the role
# (shimmer, phase, prism, psychic glow). Everything else exports as classic Qud palette.
TRUECOLOR_CREATURE_KEYS = frozenset(
    {
        "broodling_glowling",
        "broodling_fluxling",
        "broodling_voidling",
        "broodling_crystal",
        "broodling_shard",
        "broodling_phantom",
        "broodling_mindling",
        "broodling_necroling",
    }
)

# Inventory-facing mutation gear (64x96): needs membrane/vein readability — not 3-color flat.
TRUECOLOR_GEAR_KEYS = frozenset({"icon", "sack"})

# Curated visual recipes from ObjectBlueprints (Broodling_Sack Description).
# Weak Ollama one-liners + conflicting "flat 3-color" locks produced tech-panel trash.
CURATED_PROMPT_SEEDS: Dict[str, Dict[str, str]] = {
    "icon": {
        "prompt": (
            "Caves of Qud body-horror mutation icon: almost armor-like brood-sack pauldron on the "
            "upper back, layered overlapping chitin armor plates and carapace segments fused to "
            "spine and scapulae, only a wet magenta membrane visible between plate gaps, larval "
            "broodling shapes inside, armored side hatch port with a fleshy birthing slit for "
            "emergence, vent slits exhaling heat shimmer and green-amber miasma, biometal rivets "
            "and sutures, living organic armor not a backpack, centered dark void, bold silhouette"
        ),
        "negative_prompt": (
            "soft floppy sack only, clean medical organ, cute pouch, school backpack, zipper, "
            "cloth fabric, bare membrane balloon with no plates, cyberpunk HUD frame, rectangular "
            "tech panel, circuit border, glowing eye core, door, portal, fractal noise fill, "
            "motherboard, neon rim, friendly cartoon, anime, watermark, text, collage, white "
            "background, sterile lab, sealed smooth egg no opening"
        ),
    },
    "sack": {
        "prompt": (
            "Caves of Qud body-horror back equipment, side three-quarter view: almost armor-like "
            "broodling sack as fused back armor, heavy layered chitin carapace plates like a "
            "pauldron or shell, protective plating over a hot pulsing membrane core, broodlings "
            "as dark silhouettes in plate gaps, armored side hatch port with fleshy orifice for "
            "broodlings to crawl out, gland vents releasing heat distortion and poisonous miasma, "
            "steam and spore haze, magenta veins between plates, biometal clamps into shoulders, "
            "grotesque organic armor biomutation, single subject, dark void, inventory-readable"
        ),
        "negative_prompt": (
            "soft unarmored balloon sack, school backpack, zipper, fabric cloth pack, camping gear, "
            "bare translucent membrane with no chitin plates, cyberpunk frame, rectangular UI panel, "
            "glowing eye, circuit border, fractal fill, cute cartoon, anime, watermark, text, "
            "photorealistic face, white background, busy scene, friendly mascot, fully sealed "
            "with no hatch or opening"
        ),
    },
    "preview": {
        "prompt": (
            "Caves of Qud workshop preview: three giant ant broodlings ripping a humanoid corpse "
            "apart in the center foreground, the corpse must be clearly visible with torn open "
            "torso ribs and spilling guts, ants gripping flesh with heavy mandibles and clawed "
            "forelegs, ichor spray and sinew strands, clear ant anatomy head thorax abdomen six "
            "jointed legs antennae, layered magenta-violet and amber chitin armor plates, bright "
            "readable midtones, umber cave ground, soft rim light, pack feeding frenzy body "
            "horror, no UI chrome"
        ),
        "negative_prompt": (
            "no corpse, empty ground, idle standing pose, portrait lineup, near-black void fill, "
            "monochrome blood-red only, worm tentacle stalk, abstract blob monsters, cute ants, "
            "cartoon insects, Disney, anime, school backpack, tech HUD, neon rim, cyberpunk "
            "panel, glowing eye core, watermark, text, logo, collage of tiny sprites, white "
            "background, sterile lab, peaceful grazing, friendly mascot, photorealistic human "
            "face closeup, busy cityscape"
        ),
    },
}


def _asset_uses_truecolor(prompt_key: str) -> bool:
    """UI materials/preview/sack/icon + shimmer roles. Map-worn tiles stay palette."""
    # Carapace is an on-map/worn tile — hi-res/truecolor is wasted after cell downscale.
    if prompt_key == "texture_carapace":
        return False
    if prompt_key in TRUECOLOR_GEAR_KEYS:
        return True
    if prompt_key in _UI_TEXTURE_PROMPT_KEYS or prompt_key == "preview":
        return True
    return prompt_key in TRUECOLOR_CREATURE_KEYS


def _apply_curated_prompt_seeds(spec: Dict) -> Dict:
    """Force sack/icon/preview recipes so SD cannot invent tech-panel or collage nonsense."""
    out = dict(spec) if isinstance(spec, dict) else {}
    for key, seed in CURATED_PROMPT_SEEDS.items():
        out[key] = {
            "prompt": seed["prompt"],
            "negative_prompt": seed["negative_prompt"],
        }
    return out


def _prompt_entry_complete(entry: object) -> bool:
    if not isinstance(entry, dict):
        return False
    return bool(str(entry.get("prompt", "")).strip() and str(entry.get("negative_prompt", "")).strip())


def _prompt_pack_complete(spec: object) -> bool:
    if not isinstance(spec, dict):
        return False
    for key in REQUIRED_PROMPT_KEYS:
        if " / " in key:
            return False
        if not _prompt_entry_complete(spec.get(key)):
            return False
    return True


def _merge_prompt_pack(existing: Optional[Dict], incoming: Optional[Dict]) -> Dict:
    """
    Merge Ollama/new pack into existing. Never wipe complete UI/texture keys.
    Drops mangled combined keys ("a / b"). Creature keys from incoming overwrite when valid.
    """
    merged: Dict = {}
    if isinstance(existing, dict):
        for k, v in existing.items():
            if " / " in str(k):
                continue
            if k in ("theme", "note") or _prompt_entry_complete(v):
                merged[k] = v
    if isinstance(incoming, dict):
        for k, v in incoming.items():
            if " / " in str(k):
                continue
            if k in ("theme", "note"):
                merged[k] = v
                continue
            if not _prompt_entry_complete(v):
                continue
            if k in _UI_TEXTURE_PROMPT_KEYS and _prompt_entry_complete(merged.get(k)):
                # Preserve curated UI/texture; only fill gaps.
                continue
            if k in CURATED_PROMPT_SEEDS:
                # Sack/icon/preview recipes are locked in code — never let weak Ollama overwrite.
                continue
            merged[k] = v
    if "theme" not in merged:
        merged["theme"] = "biomutation"
    return _apply_curated_prompt_seeds(merged)


def _center_crop_square(img: Image.Image) -> Image.Image:
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    return img.crop((left, top, left + side, top + side))


# Official CoQ tile palette (https://wiki.cavesofqud.com/wiki/Visual_Style)
COQ_PALETTE_RGB: List[Tuple[int, int, int]] = [
    (0xA6, 0x4A, 0x2E),  # r dark red
    (0xD7, 0x42, 0x00),  # R red
    (0xF1, 0x5F, 0x22),  # o dark orange
    (0xE9, 0x9F, 0x10),  # O orange
    (0x98, 0x87, 0x5F),  # w brown
    (0xCF, 0xC0, 0x41),  # W gold
    (0x00, 0x94, 0x03),  # g dark green
    (0x00, 0xC4, 0x20),  # G green
    (0x00, 0x48, 0xBD),  # b dark blue
    (0x00, 0x96, 0xFF),  # B blue
    (0x40, 0xA4, 0xB9),  # c dark cyan
    (0x77, 0xBF, 0xCF),  # C cyan
    (0xB1, 0x54, 0xCF),  # m dark magenta
    (0xDA, 0x5B, 0xD6),  # M magenta
    (0x0F, 0x3B, 0x3A),  # k qud viridian (usual tile bg)
    (0x15, 0x53, 0x52),  # K dark grey
    (0xB1, 0xC9, 0xC3),  # y grey
    (0xFF, 0xFF, 0xFF),  # Y white
]
COQ_BG = (0x0F, 0x3B, 0x3A)  # k


def _largest_seed_component(seed: Image.Image) -> Image.Image:
    """Drop sparkles/vignette so the crop bbox is the actual creature."""
    w, h = seed.size
    sp = seed.load()
    seen = [[False] * w for _ in range(h)]
    best: list[tuple[int, int]] = []
    for y in range(h):
        for x in range(w):
            if sp[x, y] < 128 or seen[y][x]:
                continue
            stack = [(x, y)]
            seen[y][x] = True
            cells: list[tuple[int, int]] = []
            while stack:
                cx, cy = stack.pop()
                cells.append((cx, cy))
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < w and 0 <= ny < h and sp[nx, ny] >= 128 and not seen[ny][nx]:
                        seen[ny][nx] = True
                        stack.append((nx, ny))
            if len(cells) > len(best):
                best = cells
    out = Image.new("L", (w, h), 0)
    op = out.load()
    for x, y in best:
        op[x, y] = 255
    return out


def _isolate_subject(img: Image.Image) -> Image.Image:
    """Crop Unity/SD void and keep black carapace that sits on a black canvas.

    Highlight seeds (chroma/luma) mark the creature; dilate so dark plates stay
    opaque; lift near-black body pixels so they silhouette in a CoQ cell.
    """
    rgba = img.convert("RGBA")
    w, h = rgba.size
    px = rgba.load()
    seed = Image.new("L", (w, h), 0)
    sp = seed.load()
    x0, y0, x1, y1 = w, h, 0, 0
    sr = sg = sb = n = 0
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a < 16:
                continue
            luma = (r + g + b) / 3.0
            chroma = max(r, g, b) - min(r, g, b)
            if luma < 26 and chroma < 12:
                continue
            sp[x, y] = 255
            sr += r
            sg += g
            sb += b
            n += 1
            if x < x0:
                x0 = x
            if y < y0:
                y0 = y
            if x >= x1:
                x1 = x + 1
            if y >= y1:
                y1 = y + 1
    if n == 0:
        return rgba
    seed = _largest_seed_component(seed.filter(ImageFilter.MaxFilter(5)))
    sp = seed.load()
    x0, y0, x1, y1 = w, h, 0, 0
    sr = sg = sb = n = 0
    for y in range(h):
        for x in range(w):
            if sp[x, y] < 128:
                continue
            r, g, b, a = px[x, y]
            sr += r
            sg += g
            sb += b
            n += 1
            if x < x0:
                x0 = x
            if y < y0:
                y0 = y
            if x >= x1:
                x1 = x + 1
            if y >= y1:
                y1 = y + 1
    if n == 0:
        return rgba
    k = max(5, min(21, (max(w, h) // 40) | 1))
    if k % 2 == 0:
        k += 1
    dilated = seed.filter(ImageFilter.MaxFilter(k))
    dp = dilated.load()
    pad = max(2, int(round(max(x1 - x0, y1 - y0) * 0.03)))
    x0 = max(0, x0 - pad)
    y0 = max(0, y0 - pad)
    x1 = min(w, x1 + pad)
    y1 = min(h, y1 + pad)
    lift = (
        max(16, min(56, int(sr / n * 0.28))),
        max(16, min(56, int(sg / n * 0.28))),
        max(16, min(56, int(sb / n * 0.28))),
    )
    out = Image.new("RGBA", (x1 - x0, y1 - y0), (0, 0, 0, 0))
    op = out.load()
    for y in range(y0, y1):
        for x in range(x0, x1):
            if dp[x, y] < 128:
                continue
            r, g, b, a = px[x, y]
            if (r + g + b) / 3.0 < 24:
                r, g, b = lift
            op[x - x0, y - y0] = (r, g, b, 255)
    return out


def _fit_subject_to_tile(
    img: Image.Image,
    tw: int,
    th: int,
    *,
    bottom_align: bool = True,
    margin: int = 1,
) -> Image.Image:
    """Crop void, then contain-fit into tw×th. Bottom-align so ground bugs don't float."""
    cropped = _isolate_subject(img)
    cw, ch = cropped.size
    if cw <= 0 or ch <= 0:
        return img.convert("RGBA").resize((tw, th), Image.Resampling.LANCZOS)
    inner_w = max(1, tw - margin * 2)
    inner_h = max(1, th - margin * 2)
    scale = min(inner_w / cw, inner_h / ch)
    nw = max(1, int(round(cw * scale)))
    nh = max(1, int(round(ch * scale)))
    scaled = cropped.resize((nw, nh), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    ox = (tw - nw) // 2
    oy = (th - nh - margin) if bottom_align else (th - nh) // 2
    if oy < margin:
        oy = margin
    canvas.paste(scaled, (ox, oy), scaled)
    return canvas


def _center_crop_to_aspect(img: Image.Image, aspect: float) -> Image.Image:
    """Crop centered to width/height = aspect (e.g. 16/24)."""
    w, h = img.size
    if w <= 0 or h <= 0 or aspect <= 0:
        return img
    cur = w / h
    if abs(cur - aspect) < 0.01:
        return img
    if cur > aspect:
        new_w = max(1, int(round(h * aspect)))
        left = (w - new_w) // 2
        return img.crop((left, 0, left + new_w, h))
    new_h = max(1, int(round(w / aspect)))
    top = (h - new_h) // 2
    return img.crop((0, top, w, top + new_h))


def _nearest_coq_color(rgb: Tuple[int, int, int]) -> Tuple[int, int, int]:
    r, g, b = rgb
    best = COQ_PALETTE_RGB[0]
    best_d = 1e18
    for pr, pg, pb in COQ_PALETTE_RGB:
        d = (r - pr) * (r - pr) + (g - pg) * (g - pg) + (b - pb) * (b - pb)
        if d < best_d:
            best_d = d
            best = (pr, pg, pb)
    return best


def _quantize_to_qud_tile_palette(img: Image.Image, max_fg: int = 2) -> Image.Image:
    """
    Map to official 18-color palette; keep bg (k) + up to max_fg foreground colors.
    Matches wiki: each tile uses up to 3 palette colors (primary, detail, background).

    Uses luminance bands so dark CLIP drafts still get a readable silhouette instead of
    collapsing to a solid viridian (k) blob.
    """
    rgba = img.convert("RGBA")
    # Punch mid/high values so near-black drafts still separate into bands.
    boosted = ImageEnhance.Contrast(rgba).enhance(1.65)
    boosted = ImageEnhance.Brightness(boosted).enhance(1.25)
    px = list(boosted.getdata())

    samples: List[Tuple[int, int, int, int, float]] = []  # r,g,b,a,luma
    for r, g, b, a in px:
        if a < 16:
            samples.append((r, g, b, 0, 0.0))
            continue
        luma = 0.2126 * r + 0.7152 * g + 0.0722 * b
        samples.append((r, g, b, 255, luma))

    # Prefer lit pixels; fall back to any opaque so near-black CLIP drafts still band.
    fg_lumas = [L for *_, a, L in samples if a >= 16 and L > 8.0]
    if not fg_lumas:
        fg_lumas = [L for *_, a, L in samples if a >= 16]
    if not fg_lumas:
        # No opaque pixels at all — keep a tiny magenta speck so the tile isn't empty.
        out = Image.new("RGBA", rgba.size, (*COQ_BG, 255))
        if out.size[0] > 2 and out.size[1] > 2:
            out.putpixel((out.size[0] // 2, out.size[1] // 2), (0xDA, 0x5B, 0xD6, 255))
        return out

    fg_sorted = sorted(fg_lumas)
    # Wider bands on tiny 16x24 so mid/detail survive Lanczos soften.
    t_lo = fg_sorted[max(0, int(len(fg_sorted) * 0.22))]
    t_hi = fg_sorted[min(len(fg_sorted) - 1, int(len(fg_sorted) * 0.62))]
    if t_hi <= t_lo:
        t_hi = t_lo + max(1.0, (fg_sorted[-1] - fg_sorted[0]) * 0.25 + 1.0)

    mid_rgb: List[Tuple[int, int, int]] = []
    hi_rgb: List[Tuple[int, int, int]] = []
    for r, g, b, a, L in samples:
        if a < 16 or L <= t_lo:
            continue
        if L >= t_hi:
            hi_rgb.append((r, g, b))
        else:
            mid_rgb.append((r, g, b))

    def _avg_nearest(rgbs: List[Tuple[int, int, int]], fallback: Tuple[int, int, int]) -> Tuple[int, int, int]:
        if not rgbs:
            return fallback
        ar = sum(c[0] for c in rgbs) // len(rgbs)
        ag = sum(c[1] for c in rgbs) // len(rgbs)
        ab = sum(c[2] for c in rgbs) // len(rgbs)
        return _nearest_coq_color((ar, ag, ab))

    # Prefer magenta / cyan biomutation tells if nearest lands on bg.
    primary = _avg_nearest(mid_rgb or hi_rgb, (0xDA, 0x5B, 0xD6))  # M
    detail = _avg_nearest(hi_rgb or mid_rgb, (0x77, 0xBF, 0xCF))  # C
    if primary == COQ_BG:
        primary = (0xDA, 0x5B, 0xD6)
    if detail == COQ_BG or detail == primary:
        detail = (0x77, 0xBF, 0xCF) if primary != (0x77, 0xBF, 0xCF) else (0xCF, 0xC0, 0x41)

    if max_fg < 2:
        detail = primary

    out_px: List[Tuple[int, int, int, int]] = []
    for _r, _g, _b, a, L in samples:
        if a < 16:
            out_px.append((*COQ_BG, 0))
            continue
        if L <= t_lo:
            out_px.append((*COQ_BG, 255))
            continue
        if L >= t_hi:
            out_px.append((*detail, 255))
        else:
            out_px.append((*primary, 255))

    out = Image.new("RGBA", rgba.size)
    out.putdata(out_px)
    return out


def _export_from_draft(
    draft_path: Path,
    out_path: Path,
    size: Tuple[int, int],
    *,
    truecolor: bool = False,
) -> bool:
    if not draft_path.exists():
        return False
    out_path.parent.mkdir(parents=True, exist_ok=True)

    tw, th = size
    with Image.open(draft_path) as img:
        img = img.convert("RGBA")
        # Square UI/preview: center crop. 2:3 creature/gear tiles: crop void and
        # fill the cell so thin stingers don't Lanczos into a magenta smear.
        if tw == th:
            img = _center_crop_square(img)
            img = img.resize(size, Image.Resampling.LANCZOS)
        else:
            stem = draft_path.stem.lower()
            flying = any(k in stem for k in ("flying", "prismfly", "glowling", "phantom"))
            img = _fit_subject_to_tile(img, tw, th, bottom_align=not flying)
        img = ImageEnhance.Sharpness(img).enhance(1.45)
        img = ImageEnhance.Contrast(img).enhance(1.2)
        # Classic tiles/icons: wiki Visual_Style — bg + ≤2 fg from the 18-color palette.
        # Truecolor only for shimmer/phase roles + UI materials (caller sets flag).
        if not truecolor:
            img = _quantize_to_qud_tile_palette(img, max_fg=2)
        img.save(out_path, "PNG")
    return out_path.exists() and out_path.stat().st_size > 0


def _powershell_escape_single_quoted(s: str) -> str:
    # PowerShell single-quoted string escapes single quote by doubling it.
    return s.replace("'", "''")


def _run_imagemagick_postprocess_qud(shared_dir: Path, image_path: Path) -> None:
    """
    Optional: post-process using Tools/Shared ImageMagickPostProcessor.psm1 for consistent PNG settings.
    If ImageMagick isn't available, the module will just warn and skip.
    """
    module_path = shared_dir / "ImageMagickPostProcessor.psm1"
    if not module_path.exists():
        return
    if not image_path.exists():
        return

    ps = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        (
            "& {"
            f"Import-Module '{_powershell_escape_single_quoted(str(module_path))}' -DisableNameChecking -Force;"
            "if (-not (Get-Command Process-AIGeneratedImage -ErrorAction SilentlyContinue)) {"
            "  return;"
            "}"
            f"$null = Process-AIGeneratedImage -InputPath '{_powershell_escape_single_quoted(str(image_path))}' "
            f"-OutputPath '{_powershell_escape_single_quoted(str(image_path))}' -GameType 'Qud' -Quality 'high';"
            "}"
        ),
    ]
    subprocess.run(ps, capture_output=True, text=True)


def _check_sd35_available(sd_module_path: Path) -> bool:
    """Check if SD3.5 server is available via the module."""
    if not sd_module_path.exists():
        return False
    ps = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        (
            "& {"
            f"Import-Module '{_powershell_escape_single_quoted(str(sd_module_path))}' -DisableNameChecking -Force -ErrorAction SilentlyContinue;"
            "if (-not (Get-Command Test-StableDiffusionConnection -ErrorAction SilentlyContinue)) {"
            "  exit 1;"
            "}"
            "$result = Test-StableDiffusionConnection;"
            "if ($result) { exit 0; } else { exit 1; }"
            "}"
        ),
    ]
    proc = subprocess.run(ps, capture_output=True, text=True, timeout=10)
    return proc.returncode == 0


def _run_sd35_generate_single(
    sd_module_path: Path,
    params: Sd35Params,
    output_path: Path,
    verbose: bool = False,
    cache: Optional[CacheManager] = None,
) -> bool:
    """
    Generate a single draft image using Tools/Shared StableDiffusionIntegration.psm1.
    This is the base function that generates one draft - iterative refinement is handled
    by the event bus system with parallel art director reviews.
    
    Returns True if successful, False if SD3.5 unavailable (graceful fallback).
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Check cache for file existence (with file size check)
    if cache is not None:
        cached_exists = cache.get("file_exists", path=str(output_path), ttl=60, use_disk=False)  # 1 minute TTL
        if cached_exists and output_path.exists():
            file_size = output_path.stat().st_size
            if file_size > 0:
                if verbose:
                    print(f"    [SKIP] Draft already exists: {output_path.name}")
                return True
    
    # Check file directly
    if output_path.exists() and output_path.stat().st_size > 0:
        if cache is not None:
            cache.set("file_exists", path=str(output_path), value=True, ttl=60, use_disk=False)
        if verbose:
            print(f"    [SKIP] Draft already exists: {output_path.name}")
        return True

    # Prefer Python sd_http_client (finite timeout, salvage, single-flight lock; never auto-starts SD)
    try:
        from qud_sd_client import generate_sd_draft, SD_AVAILABLE

        if SD_AVAILABLE:
            if verbose:
                print(f"    [GEN] Generating SD draft via sd_http_client...")
            sd_result = generate_sd_draft(
                prompt=params.prompt,
                output_path=output_path,
                negative_prompt=params.negative_prompt,
                width=params.width,
                height=params.height,
                steps=params.steps,
                guidance_scale=params.guidance_scale,
                seed=params.seed,
                lock_label=f"broodmother:{output_path.name}",
            )
            if sd_result.ok and output_path.exists() and output_path.stat().st_size > 0:
                if verbose:
                    print(f"    [OK] Draft created: {output_path.stat().st_size / 1024:.1f} KB (sd_http_client)")
                if cache is not None:
                    cache.set("file_exists", path=str(output_path), value=True, ttl=3600, use_disk=False)
                return True
            if verbose and sd_result.error:
                print(f"    [WARN] sd_http_client: {sd_result.error}; trying PowerShell fallback")
    except ImportError:
        if verbose:
            print(f"    [INFO] qud_sd_client unavailable; using PowerShell SD module")

    if not sd_module_path.exists():
        if verbose:
            print(f"    [WARN] SD3.5 module not found: {sd_module_path}")
        return False

    # Check if SD3.5 server is available before attempting
    if not _check_sd35_available(sd_module_path):
        if verbose:
            print(f"    [WARN] SD3.5 server not available; skipping draft generation")
        return False

    if verbose:
        print(f"    [GEN] Generating SD3.5 draft...")
        print(f"    [GEN] Output path: {output_path}")
        print(f"    [GEN] Prompt length: {len(params.prompt)} chars")
    
    # Generate single draft
    ps = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        (
            "& {"
            f"Import-Module '{_powershell_escape_single_quoted(str(sd_module_path))}' -DisableNameChecking -Force;"
            "if (-not (Get-Command Generate-AssetImageWithSD3 -ErrorAction SilentlyContinue)) {"
            "  throw 'Generate-AssetImageWithSD3 not found after module import';"
            "}"
            f"try {{ "
            f"$result = Generate-AssetImageWithSD3 "
            f"-Prompt '{_powershell_escape_single_quoted(params.prompt)}' "
            f"-OutputPath '{_powershell_escape_single_quoted(str(output_path))}' "
            f"-NegativePrompt '{_powershell_escape_single_quoted(params.negative_prompt)}' "
            f"-Width {params.width} -Height {params.height} "
            f"-Steps {params.steps} -GuidanceScale {params.guidance_scale} "
            f"-Seed {params.seed} "
            f"-EnhanceWithOllama:${str(params.enhance_with_ollama).lower()} "
            f"-AutoStartServer:$false;"
            f"if (-not (Test-Path '{_powershell_escape_single_quoted(str(output_path))}')) {{ "
            f"  Write-Error 'Generated file does not exist: {_powershell_escape_single_quoted(str(output_path))}'; "
            f"  exit 1; "
            f"}} "
            f"$fileInfo = Get-Item '{_powershell_escape_single_quoted(str(output_path))}'; "
            f"if ($fileInfo.Length -eq 0) {{ "
            f"  Write-Error 'Generated file is empty (0 bytes)'; "
            f"  exit 1; "
            f"}} "
            f"Write-Host \"[OK] File generated successfully: $($fileInfo.Length) bytes at {_powershell_escape_single_quoted(str(output_path))}\"; "
            f"}} catch {{ "
            f"  Write-Error \"SD3.5 generation failed: $_\"; "
            f"  exit 1; "
            f"}}"
            "}"
        ),
    ]
    
    # Run with timeout (SD3.5 can take a while)
    try:
        # Match sd_http_client read budget (CPU-spill worst case can exceed 1h).
        proc = subprocess.run(ps, capture_output=True, text=True, timeout=9000)
        if proc.returncode != 0:
            if verbose:
                error_output = proc.stderr if proc.stderr else proc.stdout
                print(f"    [ERROR] SD3.5 generation failed (exit code {proc.returncode})")
                if error_output:
                    # Show last few lines of error
                    error_lines = error_output.strip().split('\n')
                    print(f"    [ERROR] Last error lines:")
                    for line in error_lines[-5:]:
                        if line.strip():
                            print(f"      {line}")
            return False
    except subprocess.TimeoutExpired:
        if verbose:
            print(f"    [ERROR] SD3.5 generation timed out (>9000s)")
        return False
    
    # Verify file was created and has content
    if not output_path.exists():
        if verbose:
            print(f"    [ERROR] SD3.5 produced no file at: {output_path}")
            print(f"    [ERROR] Check SD3.5 server logs for errors")
        return False
    
    file_size = output_path.stat().st_size
    if file_size == 0:
        if verbose:
            print(f"    [ERROR] SD3.5 produced empty file (0 bytes)")
            print(f"    [ERROR] This usually means:")
            print(f"    [ERROR]   1. SD3.5 server returned an error response")
            print(f"    [ERROR]   2. Image decoding failed")
            print(f"    [ERROR]   3. File write permission issue")
            print(f"    [ERROR] Check SD3.5 server logs for details")
        # Delete the empty file
        try:
            output_path.unlink()
        except:
            pass
        return False
    
    if verbose:
        size_kb = output_path.stat().st_size / 1024
        print(f"    [OK] Draft created: {size_kb:.1f} KB")
    
    # Update cache
    if cache is not None:
        cache.set("file_exists", path=str(output_path), value=True, ttl=3600, use_disk=False)
    
    return True


def _art_director_review(
    image_path: Path,
    original_prompt: str,
    asset_type: str,
    iteration: int = 0,
    previous_feedback: Optional[str] = None,
    verbose: bool = False,
    cache: Optional[CacheManager] = None
) -> Dict:
    """
    Art director AI reviews a generated asset and provides critique/feedback.
    
    Uses a specialized "art director" model to analyze the image and provide:
    - Quality assessment (score 0-100)
    - Specific issues/strengths
    - Refined prompt suggestions
    - Whether another iteration is needed
    
    Args:
        image_path: Path to the generated image
        original_prompt: Original SD3.5 prompt used
        asset_type: Type of asset (icon, equipment, creature, etc.)
        iteration: Current iteration number (0 = first draft)
        previous_feedback: Feedback from previous iteration (if any)
        verbose: Verbose output
        cache: Cache manager for responses
    
    Returns:
        Dict with keys: quality_score, needs_refinement, feedback, refined_prompt, refined_negative_prompt
    """
    if not image_path.exists():
        return {
            "quality_score": 0,
            "needs_refinement": True,
            "feedback": "Image file not found",
            "refined_prompt": original_prompt,
            "refined_negative_prompt": ""
        }
    
    # Check cache
    cache_key = f"art_director_{image_path.name}_{iteration}"
    if cache is not None:
        cached = cache.get(
            "art_director_review",
            image_path=str(image_path),
            original_prompt=original_prompt,
            asset_type=asset_type,
            iteration=iteration,
            previous_feedback=previous_feedback,
            ttl=3600 * 24,  # 24 hour TTL
            use_disk=True
        )
        if cached is not None:
            if verbose:
                print(f"    [CACHE] Using cached art director review")
            return cached
    
    # Read image metadata for context
    try:
        with Image.open(image_path) as img:
            width, height = img.size
            mode = img.mode
    except Exception as e:
        if verbose:
            print(f"    [WARN] Could not read image metadata: {e}")
        width, height = 1024, 1024
        mode = "RGB"
    
    # Build art director prompt
    system_prompt = (
        "You are an expert art director for Caves of Qud, a roguelike game with a unique organic biotech aesthetic. "
        "Your role is to critique generated game assets and provide actionable feedback to improve quality.\n\n"
        "Analyze the generated asset and provide:\n"
        "1. Quality score (0-100): Overall assessment of the asset's quality, detail, and game-readiness\n"
        "2. Needs refinement (true/false): Whether another iteration is needed\n"
        "3. Feedback: Specific critique of what works well and what needs improvement\n"
        "4. Refined prompt: Improved SD3.5 prompt incorporating your feedback\n"
        "5. Refined negative prompt: Enhanced negative prompt to avoid issues\n\n"
        "Focus on:\n"
        "- Organic, intricate biological details (no simple shapes)\n"
        "- Caves of Qud's unique aesthetic (organic biotech, magenta/purple tones, chitinous textures)\n"
        "- Game asset requirements (readable at small sizes, clear silhouette, appropriate detail level)\n"
        "- Technical quality (composition, lighting, detail clarity)\n\n"
        "Return ONLY valid JSON."
    )
    
    prompt_text = (
        f"Review this {asset_type} asset for Caves of Qud.\n\n"
        f"Original prompt: {original_prompt}\n\n"
        f"Image details: {width}x{height} {mode}\n"
    )
    
    if iteration > 0 and previous_feedback:
        prompt_text += (
            f"\nThis is iteration {iteration + 1}. Previous feedback:\n{previous_feedback}\n\n"
            "Assess if the refinement addressed the previous issues and provide new feedback if needed.\n"
        )
    else:
        prompt_text += "\nThis is the first draft. Provide initial critique and refinement suggestions.\n"
    
    prompt_text += (
        "\nReturn JSON with keys:\n"
        "- quality_score: integer 0-100\n"
        "- needs_refinement: boolean\n"
        "- feedback: string with specific critique\n"
        "- refined_prompt: string with improved prompt\n"
        "- refined_negative_prompt: string with enhanced negative prompt\n"
    )
    
    # Text-only critique (no image bytes). Prefer dark_tone/wizardlm — "visual" can
    # escalate/hang for ~30m waiting on a vision path that never receives pixels.
    review_result = _ollama_json(
        prompt=prompt_text,
        system_prompt=system_prompt,
        task_type="dark_tone",
        verbose=verbose,
        cache=cache,
        asset_type=f"{asset_type} art director review",
        timeout_seconds=180,
        model_name=OLLAMA_MODEL,
    )
    
    # Ensure all required fields exist
    result = {
        "quality_score": review_result.get("quality_score", 50),
        "needs_refinement": review_result.get("needs_refinement", True),
        "feedback": review_result.get("feedback", "No feedback provided"),
        "refined_prompt": review_result.get("refined_prompt", original_prompt),
        "refined_negative_prompt": review_result.get("refined_negative_prompt", ""),
    }
    
    # Cache the result
    if cache is not None:
        cache.set(
            "art_director_review",
            image_path=str(image_path),
            original_prompt=original_prompt,
            asset_type=asset_type,
            iteration=iteration,
            previous_feedback=previous_feedback,
            value=result,
            ttl=3600 * 24,
            use_disk=True
        )
    
    return result


def _resolve_ollama_model(requested: str = "") -> str:
    """Prefer wizardlm-uncensored (no filters). Fall back only if not installed."""
    want = (requested or OLLAMA_MODEL or DEFAULT_OLLAMA_MODEL).strip() or DEFAULT_OLLAMA_MODEL
    available = [str(m) for m in (get_available_models() or [])]
    if want in available:
        return want
    # Match tag variants (wizardlm-uncensored / wizardlm-uncensored:latest)
    stem = want.split(":")[0].lower()
    for name in available:
        if name.lower() == stem or name.lower().startswith(stem + ":"):
            return name
    for name in available:
        if "wizardlm-uncensored" in name.lower():
            return name
    print(f"    [WARN] Requested model '{want}' not in ollama list; will still request it")
    return want


def _extract_json_object(text: str) -> str:
    """Pull the outermost {...} from an LLM reply (strip markdown fences)."""
    if not text:
        return ""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start < 0 or end <= start:
        return ""
    return cleaned[start : end + 1]


def _sanitize_llm_json(json_str: str) -> str:
    """
    Fix common LLM JSON damage without mangling string contents.
    Do NOT run bare (\\w+): quoting — that corrupts colons inside prompt strings.
    """
    s = json_str.strip()
    # Smart quotes -> ASCII
    s = s.replace("\u201c", '"').replace("\u201d", '"').replace("\u2018", "'").replace("\u2019", "'")
    # Trailing commas before } or ]
    s = re.sub(r",\s*([}\]])", r"\1", s)
    # Invalid JSON escapes inside strings: turn lone backslashes into \\
    # (keep valid \\ \" \/ \b \f \n \r \t \uXXXX)
    def _fix_string_escapes(match: re.Match) -> str:
        body = match.group(0)
        out = []
        i = 1  # skip opening quote
        end = len(body) - 1
        out.append('"')
        while i < end:
            ch = body[i]
            if ch == "\\" and i + 1 < end:
                nxt = body[i + 1]
                if nxt in '"\\/bfnrt':
                    out.append(ch)
                    out.append(nxt)
                    i += 2
                    continue
                if nxt == "u" and i + 5 < end and all(
                    c in "0123456789abcdefABCDEF" for c in body[i + 2 : i + 6]
                ):
                    out.append(body[i : i + 6])
                    i += 6
                    continue
                # Invalid escape — escape the backslash
                out.append("\\\\")
                i += 1
                continue
            if ch == "\\":
                out.append("\\\\")
                i += 1
                continue
            out.append(ch)
            i += 1
        out.append('"')
        return "".join(out)

    s = re.sub(r'"(?:\\.|[^"\\])*"', _fix_string_escapes, s)
    return s


def _loads_llm_json(text: str) -> Dict:
    """Parse JSON from an LLM reply with sanitization retries."""
    raw = _extract_json_object(text)
    if not raw:
        raise ValueError("Could not find JSON object in response")
    attempts = [raw, _sanitize_llm_json(raw)]
    last_err: Exception | None = None
    for candidate in attempts:
        try:
            result = json.loads(candidate)
            if isinstance(result, dict):
                return result
            raise ValueError("JSON root was not an object")
        except Exception as exc:  # noqa: BLE001 — collect then raise
            last_err = exc
    assert last_err is not None
    raise last_err


def _ollama_json(
    prompt: str,
    system_prompt: str,
    task_type: str = "visual",
    verbose: bool = False,
    cache: Optional[CacheManager] = None,
    asset_type: str = "asset",
    timeout_seconds: int = 300,
    model_name: str = "",
) -> Dict:
    """
    Call Ollama to generate JSON, with proper model management and caching.
    Always uses wizardlm-uncensored by default (uncensored biomutation prompts).
    """
    resolved_model = _resolve_ollama_model(model_name)

    # Try cache first
    if cache is not None:
        cached = cache.get(
            "ollama_json",
            prompt=prompt,
            system_prompt=system_prompt,
            task_type=task_type,
            model_name=resolved_model,
            ttl=3600 * 24,  # 24 hour TTL for prompts
            use_disk=True
        )
        if cached is not None:
            print(f"    [CACHE] Using cached Ollama response for {asset_type} (Ollama not called)")
            if verbose:
                print(f"    [CACHE] To force Ollama call, use --no-cache flag")
            return cached
    
    # Determine AI type label (matching Vortex pattern)
    ai_type_map = {
        "visual": "visual AI",
        "analysis": "math-focused AI",
        "code": "code AI",
        "simple": "simple AI"
    }
    ai_type = ai_type_map.get(task_type, f"{task_type} AI")
    
    print(f"    Calling {ai_type} for {asset_type} design specs...")
    print(f"    [MODEL] Forcing uncensored model: {resolved_model}")
    
    # Pre-check models before calling Ollama to avoid hangs
    try:
        # Get available models to verify the model exists locally
        available_models = get_available_models()
        if not available_models:
            print(f"    [ERROR] No models found in Ollama!")
            print(f"    [ERROR] Install models with: ollama pull wizardlm-uncensored:latest")
            print(f"    [ERROR] Or use --load-existing to skip Ollama calls")
            raise RuntimeError("No Ollama models available. Install models first or use --load-existing")
        
        # Check if models are currently loading/downloading
        import requests
        try:
            ps_response = requests.get("http://localhost:11434/api/ps", timeout=3)
            if ps_response.status_code == 200:
                ps_data = ps_response.json()
                models_info = ps_data.get("models", [])
                loading_models = []
                loaded_models = []
                for m in models_info:
                    name = m.get("name", "unknown")
                    size_vram = m.get("size_vram", 0) or 0
                    size_total = m.get("size", 0) or 0
                    # Hybrid: size>0 with size_vram==0 means weights in system RAM, not "downloading".
                    if size_total > 0 and size_vram == 0:
                        loaded_models.append(name)
                        if verbose:
                            size_mb = size_total / (1024 * 1024)
                            print(f"    [INFO] Model {name} resident in system RAM ({size_mb:.1f} MB; hybrid OK)")
                    elif size_vram == 0 and size_total == 0:
                        loading_models.append(name)
                    else:
                        loaded_models.append(name)
                        size_mb = size_vram / (1024 * 1024)
                        if verbose:
                            print(f"    [INFO] Model {name} loaded ({size_mb:.1f} MB VRAM)")
                
                if loading_models:
                    print(f"    [WARN] Models mapping into memory (not necessarily downloading): {', '.join(loading_models)}")
                    print(f"    [WARN] Options:")
                    print(f"    [WARN]   1. Wait — local load into VRAM/RAM can take several minutes")
                    print(f"    [WARN]   2. Use --load-existing to skip Ollama calls")
                    print(f"    [WARN]   3. Increase timeout: --ollama-timeout 1800")
                    # Don't fail, but warn the user
                elif loaded_models:
                    print(f"    [INFO] Models already loaded: {', '.join(loaded_models)}")
                else:
                    print(f"    [INFO] No models currently loaded (will load from local disk on first request)")
                    if available_models:
                        print(f"    [INFO] Available models: {len(available_models)} (e.g., {', '.join(available_models[:3])})")
        except requests.exceptions.RequestException as e:
            if verbose:
                print(f"    [WARN] Could not check Ollama model status: {e}")
    except RuntimeError:
        raise  # Re-raise critical errors
    except Exception:
        pass  # Non-critical, continue anyway
    
    print(f"    [INFO] Generation may take a few minutes (hybrid: VRAM + system RAM). If stuck, check:")
    print(f"    [INFO]   1. ollama ps  (resident model — size_vram=0 with size>0 is RAM spill, not a download)")
    print(f"    [INFO]   2. Free VRAM / that wizardlm is already installed (ollama list)")
    print(f"    [INFO]   3. Ollama service is responsive")
    ollama_start = time.time()
    
    # Wrapper function to call Ollama with timeout and progress feedback
    def _call_ollama_with_timeout() -> str:
        """Call Ollama with a timeout to prevent indefinite hangs."""
        import threading  # Import at function start to avoid UnboundLocalError
        
        # Use the provided timeout (default is 600s = 10 minutes to account for model loading)
        # The shared module's ensure_model_loaded has a 10-minute timeout, so we need at least that
        effective_timeout = timeout_seconds
        
        def _call():
            return call_ollama(
                prompt=prompt,
                task_type=task_type,
                response_length="detailed",
                system_prompt=system_prompt,
                model_name=resolved_model,  # wizardlm-uncensored — no content filters
                auto_escalate=False,  # stay on uncensored; do not fall back to filtered models
                verbose=verbose,
            )
        
        # Start progress feedback in a separate thread with model status checks
        progress_stop = threading.Event()
        model_still_loading = threading.Event()
        elapsed_time = [0]  # Use list for mutable int in nested function
        
        def _progress_feedback():
            elapsed = 0
            last_status_check = 0
            while not progress_stop.is_set():
                time.sleep(10)  # Check every 10 seconds
                if not progress_stop.is_set():
                    elapsed += 10
                    elapsed_time[0] = elapsed
                    if elapsed % 30 == 0:  # Every 30 seconds
                        print(f"    [INFO] Still processing... ({elapsed}s elapsed, timeout: {effective_timeout}s)")
                        if elapsed >= 60:
                            print(f"    [INFO] Waiting on Ollama tokens (VRAM fill + low util during load is normal)")
                        # Check Ollama status every 30 seconds
                        if elapsed - last_status_check >= 30:
                            last_status_check = elapsed
                            try:
                                import requests
                                ps_response = requests.get("http://localhost:11434/api/ps", timeout=2)
                                if ps_response.status_code == 200:
                                    ps_data = ps_response.json()
                                    models_info = ps_data.get("models", [])
                                    for m in models_info:
                                        name = m.get("name", "unknown")
                                        size_vram = m.get("size_vram", 0) or 0
                                        size_total = m.get("size", 0) or 0
                                        if size_total > 0 and size_vram == 0:
                                            size_mb = size_total / (1024 * 1024)
                                            print(
                                                f"    [STATUS] {name} resident in system RAM "
                                                f"({size_mb:.0f} MB) — hybrid spill, not downloading"
                                            )
                                        elif size_vram > 0:
                                            size_mb = size_vram / (1024 * 1024)
                                            print(f"    [STATUS] {name} on VRAM ({size_mb:.0f} MB)")
                                        else:
                                            print(f"    [STATUS] {name} still mapping weights into memory...")
                                            model_still_loading.set()
                            except Exception:
                                pass  # Non-critical status check
        
        progress_thread = threading.Thread(target=_progress_feedback, daemon=True)
        progress_thread.start()
        
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_call)
                try:
                    # Use effective timeout (at least 10 minutes to account for model loading)
                    response = future.result(timeout=effective_timeout)
                    progress_stop.set()
                    return response
                except FutureTimeoutError as e:
                    progress_stop.set()
                    used_timeout = effective_timeout
                    elapsed = elapsed_time[0]
                    print(f"\n    [ERROR] Ollama call timed out after {used_timeout} seconds ({used_timeout // 60} minutes)")
                    print(f"    [ERROR] Elapsed time: {elapsed} seconds")
                    print(f"    [ERROR] This usually means:")
                    if model_still_loading.is_set():
                        print(f"    [ERROR]   - Model weights still mapping into VRAM/RAM (not a download if ollama list shows it)")
                    else:
                        print(f"    [ERROR]   - Generation hung or Ollama overloaded")
                        print(f"    [ERROR]   - Hybrid spill may be slow on first long reply")
                    print(f"    [ERROR]")
                    print(f"    [ERROR] To fix:")
                    print(f"    [ERROR]   1. Confirm local model: ollama list  (no pull if already listed)")
                    print(f"    [ERROR]   2. Check residency: ollama ps")
                    print(f"    [ERROR]   3. Use existing prompts: --load-existing (skips Ollama)")
                    print(f"    [ERROR]   4. Increase timeout: --ollama-timeout 1800")
                    raise RuntimeError(f"Ollama call timed out after {used_timeout} seconds")
        finally:
            progress_stop.set()    
    max_retries = 2
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                print(f"    (Retry attempt {attempt + 1}/{max_retries})")
            
            # Use timeout wrapper (configurable timeout, should be enough for model loading + generation)
            response = _call_ollama_with_timeout()
            
            ollama_elapsed = time.time() - ollama_start
            print(f"    {ai_type} design received in {ollama_elapsed:.1f} seconds")
            
            if not response:
                if attempt < max_retries - 1:
                    print(f"    WARNING: Ollama returned empty response, retrying...")
                    time.sleep(1)
                    continue
                raise RuntimeError("Ollama returned empty response")
            
            break  # Success, exit retry loop
            
        except RuntimeError as e:
            if "timed out" in str(e):
                # Don't retry on timeout, it's a system issue
                raise
            if attempt < max_retries - 1:
                print(f"    WARNING: Ollama call failed: {e}, retrying...")
                time.sleep(1)
                continue
            else:
                raise RuntimeError(f"Failed to generate {asset_type} design after {max_retries} attempts: {e}")
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"    WARNING: Ollama call failed: {e}, retrying...")
                time.sleep(1)
                continue
            else:
                raise RuntimeError(f"Failed to generate {asset_type} design after {max_retries} attempts: {e}")

    # Extract JSON object from response (matching Vortex pattern)
    json_start = response.find('{')
    json_end = response.rfind('}') + 1
    if json_start < 0 or json_end <= json_start:
        raise ValueError(f"Could not find JSON in Ollama response for {asset_type}")
    
    json_str = _sanitize_ollama_json_text(response[json_start:json_end])
    
    try:
        result = json.loads(json_str)
        print(f"    [OK] AI design specs generated for {asset_type} (colors, patterns, style)")
        
        # Cache successful result
        if cache is not None:
            cache.set(
                "ollama_json",
                prompt=prompt,
                system_prompt=system_prompt,
                task_type=task_type,
                model_name=resolved_model,
                value=result,
                ttl=3600 * 24,  # 24 hour TTL
                use_disk=True
            )
        return result
    except json.JSONDecodeError as je:
        error_msg = f"Invalid JSON from Ollama for {asset_type}: {je}"
        print(f"    WARNING: {error_msg}, attempting local sanitize + repair...")

        # Second local pass (sometimes trailing commas / fences remain)
        try:
            result = json.loads(_sanitize_ollama_json_text(json_str))
            print(f"    [OK] JSON sanitized locally for {asset_type}")
            return result
        except Exception:
            pass
        
        # Repair on the same uncensored model — do not swap to filtered "simple" models
        try:
            repair = call_ollama(
                prompt=(
                    "Fix into strict valid JSON only. Escape backslashes. No markdown.\n\n"
                    + json_str[:12000]
                ),
                task_type="visual",
                response_length="short",
                system_prompt="Return ONLY valid JSON. No markdown. No commentary.",
                model_name=resolved_model,
                auto_escalate=False,
                verbose=verbose,
            )
            if not repair:
                raise RuntimeError("JSON repair attempt failed")
            
            s2 = repair.find("{")
            e2 = repair.rfind("}") + 1
            if s2 < 0 or e2 <= s2:
                raise RuntimeError("Repaired response did not contain JSON")
            
            result = json.loads(_sanitize_ollama_json_text(repair[s2:e2]))
            print(f"    [OK] JSON repaired and parsed successfully for {asset_type}")
            return result
        except Exception as repair_error:
            raise ValueError(f"{error_msg}. Repair also failed: {repair_error}")


def _sanitize_ollama_json_text(text: str) -> str:
    """Fix common LLM JSON defects without mangling string contents."""
    s = text.strip()
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\s*", "", s, flags=re.IGNORECASE)
        s = re.sub(r"\s*```$", "", s)
    s = s.replace("\u201c", '"').replace("\u201d", '"').replace("\u2018", "'").replace("\u2019", "'")
    # Trailing commas before } or ]
    s = re.sub(r",\s*([}\]])", r"\1", s)
    # Invalid escapes like \m \x (keep valid JSON escapes)
    def _fix_esc(m: re.Match) -> str:
        ch = m.group(1)
        if ch in '"\\/bfnrtu':
            return m.group(0)
        return "\\\\" + ch
    s = re.sub(r"\\(.)", _fix_esc, s)
    return s


def build_jobs(
    mod_path: Path,
    draft_dir: Path,
    load_existing: bool = False,
    cache: Optional[CacheManager] = None,
    tile_size: Tuple[int, int] = (16, 24),
    icon_size: Tuple[int, int] = (16, 24),
    high_detail: bool = False,
    ollama_timeout: int = 300,
    force_prompt_pack: bool = False,
) -> List[AssetJob]:
    """
    Define what we generate. This is intentionally small and high-signal:
    - Mutation icon
    - Broodling sack tile + icon
    - A few representative broodlings (matches previous script)
    - Workshop preview (composed from other assets)

    Default tile/icon size is vanilla CoQ 16x24.
    
    If load_existing=True, tries to load job specs from draft_dir first.
    If an existing prompt_pack.json is already complete (34/34), reuse it and
    skip Ollama unless force_prompt_pack=True.
    """
    tile_w, tile_h = tile_size
    icon_w, icon_h = icon_size
    textures = mod_path / "Textures"
    equipment = textures / "Equipment"
    creatures = textures / "Creatures"

    # Try loading existing prompt pack if available
    prompt_pack_path = draft_dir / "prompt_pack.json"
    prompt_spec = None
    existing_pack: Optional[Dict] = None

    if prompt_pack_path.exists():
        try:
            existing_pack = json.loads(prompt_pack_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"  [WARN] Could not read existing prompt pack: {e}")
            existing_pack = None

    if load_existing and existing_pack is not None:
        prompt_spec = existing_pack
        print(f"  [OK] Loaded existing prompt pack from {prompt_pack_path.name}")
    elif (
        not force_prompt_pack
        and existing_pack is not None
        and _prompt_pack_complete(existing_pack)
    ):
        # Complete pack: never burn Ollama time just because --no-cache / SkipSD35.
        prompt_spec = existing_pack
        print("  [OK] Reusing complete prompt_pack.json (skip Ollama)")
        print("       Pass --force-prompt-pack to regenerate with Ollama.")

    # Generate new prompt pack if not loaded / not reused
    if prompt_spec is None:
        print("  Generating prompt pack with Ollama...")
        print("  Note: Classic Qud ≤3-color tiles by default; truecolor only for glow/flux/void/crystal/etc.")
        print("  [OLLAMA] Calling Ollama API to generate prompts (this may take 30-60 seconds)...")
        # Prompts are created via Ollama to avoid "basic shape" artifacts and to enforce organic complexity.
        # Use "visual" task type - this will swap to the visual model automatically
        system = (
            "You are a game art director for Caves of Qud. "
            "Create SD3.5-ready prompts for concept renders downscaled to 16x24 tiles. "
            "Avoid 'simple shapes' or geometric descriptions. Prefer organic biological detail. "
            "DEFAULT: design for the official 18-color Qud palette with at most 3 colors per tile "
            "(primary, detail, viridian-black #0f3b3a background) — flat graphic, not neon gradients. "
            "True-color / soft gradients ONLY for glowling, fluxling, voidling, crystal, shard, "
            "phantom, mindling, necroling (and UI materials). "
            "Return ONLY valid JSON. Use SEPARATE keys for each asset — never combine keys with ' / '."
        )
        
        resolution_note = ""
        if high_detail:
            resolution_note = (
                f"\n\nIMPORTANT: These assets will be exported at {tile_w}x{tile_h} (tiles) and {icon_w}x{icon_h} (icons) "
                "for use with the Tile size scaling mod. Include EXTRA fine detail, intricate textures, and subtle variations "
                "that will be visible at higher resolution. The assets will be automatically scaled down by the game, so maximize detail.\n"
            )

        # Unique broodlings must match ObjectBlueprints.xml Tile="Textures/Creatures/..."
        unique_keys = [
            "broodling_crystal", "broodling_phantom", "broodling_bombardier",
            "broodling_symbiote", "broodling_tunneler", "broodling_mimic",
            "broodling_shard", "broodling_swarmling", "broodling_voidling",
            "broodling_fluxling", "broodling_leechling", "broodling_mindling",
            "broodling_glowling", "broodling_rustling", "broodling_necroling",
            "broodling_thornling", "broodling_mandibore",
        ]
        keys_csv = ", ".join(REQUIRED_PROMPT_KEYS)
        ollama_spec = None
        try:
            ollama_spec = _ollama_json(
            prompt=(
                "Create a detailed prompt pack for the Broodmother Mutation mod assets.\n"
                f"Return JSON with EXACTLY these separate keys (never combine with slash): {keys_csv}.\n"
                "Each value must be an object: {prompt, negative_prompt}.\n"
                "Keep each prompt under 60 words. Use only ASCII. No backslashes.\n\n"
                "THEME LOCK — BIOMUTATION (mandatory in every prompt):\n"
                "Living biomutation aesthetic: veined magenta membranes, arthropod chitin, "
                "ichor, biometal filaments, glandular organs, molt plates, hive pheromone sheen. "
                "Caves of Qud organic terminal mood (muted earth + sparse magenta accents). "
                "NOT cute cartoon, NOT anime, NOT purple neon HUD, NOT simple geometric shapes.\n\n"
                "Requirements:\n"
                "- icon: almost armor-like brood-sack pauldron on the back, layered chitin plates, "
                "side hatch port, heat + miasma — NEVER soft balloon-only sack or tech panel/eye/HUD\n"
                "- sack: side view of armored back-sack (carapace plates like a shell/pauldron) with "
                "side hatch orifice, heat/miasma — NOT cloth backpack or unplated membrane blob\n"
                "- broodling_ground: Arthropod minion ant/scorpion hybrid, loyal defender, multi-color magenta/cyan/amber\n"
                "- broodling_flying: Winged dragonfly/wasp hybrid, iridescent membranes, cyan/magenta\n"
                "- broodling_crystal: Faceted crystalline arthropod, prismatic cyan/white facets, deep purple core\n"
                "- broodling_phantom: Semi-transparent phased broodling, spectral blue/violet ghost membranes\n"
                "- broodling_bombardier: Artillery beetle with swollen explosive abdomen, red/amber warning markings\n"
                "- broodling_symbiote: Support healer with green tendrils and symbiotic glands\n"
                "- broodling_tunneler: Burrowing mandibled arthropod, ochre dirt-stained chitin\n"
                "- broodling_mimic: Chameleonic shape-shifting broodling, shifting magenta patterns\n"
                "- broodling_shard: Fragile crystalline fragment creature, cyan shards\n"
                "- broodling_swarmling: Tiny mite-like rapid-reproduction broodling, dense magenta\n"
                "- broodling_voidling: Reality-flicker void arthropod, black core with violet rifts\n"
                "- broodling_fluxling: Chaotic elemental energy broodling, gold/electric flux arcs\n"
                "- broodling_leechling: Distended life-drain leech broodling, deep red proboscis\n"
                "- broodling_mindling: Enlarged psychic cranium broodling, cyan cerebral sac\n"
                "- broodling_glowling: Bioluminescent exploration broodling, soft gold glow organs\n"
                "- broodling_rustling: Corrosive acid-stained rust broodling, orange oxidized residue\n"
                "- broodling_necroling: Fungal corpse-reanimator, grey-green spores and decay\n"
                "- broodling_thornling: Spiny defensive living shield, green chitinous spines\n"
                "- broodling_mandibore: Ant-like digger with antennae, drill mandibles, arched paralyzing stinger, lime/black\n"
                "- preview: three giant ant-like broodlings ripping apart a corpse, umber void "
                "(Workshop scene — NOT a tile collage)\n"
                "- texture_carapace: Chitin armor tile\n"
                "- texture_membrane: tileable veined membrane surface\n"
                "- texture_biometal: tileable biometal filament surface\n"
                "- texture_chitin: tileable arthropod chitin surface\n"
                "- ui_biomod_chip: Spring UI biomod gland chip icon\n"
                "- ui_birth_badge: Spring UI birth-select badge\n"
                "- ui_evolution_node: Spring UI evolution neural node\n"
                "- ui_swarm_frame: Spring UI swarm portrait frame\n"
                "- ui_panel: CoQ terminal UI panel chrome\n"
                "- ui_button: CoQ terminal UI chitin button\n"
                "- ui_menu_row: CoQ terminal UI list row strip\n"
                "- ui_status_strip: CoQ terminal UI status underline\n"
                "- ui_tier_pip: CoQ terminal UI magenta tier gem\n\n"
                "IMPORTANT: PNG tiles support UNLIMITED colors. Use 3-5+ colors, gradients, accents.\n"
                "Style: Caves of Qud roguelike sprite readable at tiny size after downscale; "
                "organic biotech biomutation; high detail; no simple shapes.\n"
                "Make prompts suitable for SD3.5 concept drafts at 1024x1024.\n"
                + resolution_note
            ),
            system_prompt=system,
            task_type="visual",
            verbose=False,  # Set to True for debug output
            cache=cache,
            asset_type="prompt pack",
            timeout_seconds=ollama_timeout
            )
        except Exception as ollama_pack_err:
            if existing_pack is not None:
                print(f"  [WARN] Ollama prompt pack failed: {ollama_pack_err}")
                print(f"  [WARN] Falling back to existing {prompt_pack_path.name}")
                ollama_spec = None
                prompt_spec = existing_pack
            else:
                raise
        if prompt_spec is None:
            # Merge Ollama into existing so UI/texture keys are never wiped.
            prompt_spec = _merge_prompt_pack(existing_pack, ollama_spec if isinstance(ollama_spec, dict) else None)
            if not _prompt_pack_complete(prompt_spec):
                missing = [k for k in REQUIRED_PROMPT_KEYS if not _prompt_entry_complete(prompt_spec.get(k))]
                print(f"  [WARN] Prompt pack incomplete after merge; missing: {', '.join(missing)}")

    # Always re-lock sack/icon visual recipes (mod pack may still hold tech-panel trash).
    if isinstance(prompt_spec, dict):
        prompt_spec = _apply_curated_prompt_seeds(prompt_spec)
        print("  [OK] Locked curated brood-sack / mutation-icon visual recipes")

    def get_pp(key: str) -> Sd35Params:
        entry = prompt_spec.get(key) or {}
        prompt = str(entry.get("prompt", "")).strip()
        # Map tiles: classic Visual_Style. Truecolor only for shimmer roles / UI materials.
        if _asset_uses_truecolor(key):
            style_lock = (
                "Caves of Qud concept art: 16x24 aspect, bold readable silhouette, "
                "true-color PNG with soft role-appropriate glow or prism gradients "
                "(magenta #da5bd6 / cyan #77bfcf / gold #cfc041 on #0f3b3a), "
                "biomutation arthropod, not neon cyberpunk UI"
            )
        else:
            style_lock = (
                "Caves of Qud tile concept art: 16x24 aspect, bold readable silhouette, "
                "flat graphic official 18-color Qud palette, at most 3 colors "
                "(primary + detail + viridian-black #0f3b3a background), "
                "no soft gradients, no neon, biomutation arthropod chitin"
            )
        if prompt and "visual style" not in prompt.lower() and "16x24" not in prompt.lower():
            prompt = f"{prompt}. {style_lock}"
        if key not in _UI_TEXTURE_PROMPT_KEYS and key != "preview":
            if "silhouette" not in prompt.lower():
                prompt = (
                    f"{prompt}. single centered subject, clear limbs or body masses, "
                    "dark void background, readable after downscale to 16x24 pixels"
                )
        neg = str(
            entry.get(
                "negative_prompt",
                "blurry, low quality, text, watermark, photorealistic, 3d render, "
                "anime, cute cartoon, neon cyberpunk UI, purple glow dashboard, "
                "busy background, collage, white background, soft focus, watercolor, "
                "noisy fractal fill, champion rim badge",
            )
        ).strip()
        # Tall 2:3 for creature/equipment; square for textures/UI/preview.
        if key in _UI_TEXTURE_PROMPT_KEYS or key == "preview":
            return Sd35Params(prompt=prompt, negative_prompt=neg, width=512, height=512, steps=12)
        return Sd35Params(prompt=prompt, negative_prompt=neg)

    def _job_meta(kind: str, prompt_key: str, **extra) -> Dict:
        m = {"type": kind, "theme": "biomutation", "prompt_key": prompt_key, "truecolor": _asset_uses_truecolor(prompt_key)}
        m.update(extra)
        return m

    # (prompt_key, asset_id, filename, tier_or_none)
    unique_creature_jobs = [
        ("broodling_crystal", "BroodlingCrystal_T4", "BroodlingCrystal_T4.png", 4),
        ("broodling_phantom", "BroodlingPhantom_T5", "BroodlingPhantom_T5.png", 5),
        ("broodling_bombardier", "BroodlingBombardier_T4", "BroodlingBombardier_T4.png", 4),
        ("broodling_symbiote", "BroodlingSymbiote_T3", "BroodlingSymbiote_T3.png", 3),
        ("broodling_tunneler", "BroodlingTunneler_T3", "BroodlingTunneler_T3.png", 3),
        ("broodling_mimic", "BroodlingMimic_T5", "BroodlingMimic_T5.png", 5),
        ("broodling_shard", "BroodlingShard_T4", "BroodlingShard_T4.png", 4),
        ("broodling_swarmling", "BroodlingSwarmling_T2", "BroodlingSwarmling_T2.png", 2),
        ("broodling_voidling", "BroodlingVoidling_T6", "BroodlingVoidling_T6.png", 6),
        ("broodling_fluxling", "BroodlingFluxling_T3", "BroodlingFluxling_T3.png", 3),
        ("broodling_leechling", "BroodlingLeechling_T4", "BroodlingLeechling_T4.png", 4),
        ("broodling_mindling", "BroodlingMindling_T5", "BroodlingMindling_T5.png", 5),
        ("broodling_glowling", "BroodlingGlowling_T2", "BroodlingGlowling_T2.png", 2),
        ("broodling_rustling", "BroodlingRustling_T4", "BroodlingRustling_T4.png", 4),
        ("broodling_necroling", "BroodlingNecroling_T6", "BroodlingNecroling_T6.png", 6),
        ("broodling_thornling", "BroodlingThornling_T3", "BroodlingThornling_T3.png", 3),
        ("broodling_mandibore", "BroodlingMandibore_T4", "BroodlingMandibore_T4.png", 4),
    ]

    # Creature map bodies: 16x24 (hi-res just downscales on grid — no inventory win).
    # Dual-view gear (inventory + ground/worn): 32x48 / 48x72 / 64x96 — ITS rescales
    # on the map; inventory/look UI keeps the extra detail.
    map_w, map_h = tile_w, tile_h
    inv_w, inv_h = icon_w, icon_h  # default 64x96

    jobs: List[AssetJob] = [
        AssetJob(
            asset_id="broodmother_icon",
            sd35=get_pp("icon"),
            draft_path=draft_dir / "icon_design_draft.png",
            export_paths=[(textures / "Broodmother_icon.png", (inv_w, inv_h))],
            meta=_job_meta("icon", "icon"),
        ),
        AssetJob(
            asset_id="broodling_sack",
            sd35=get_pp("sack"),
            draft_path=draft_dir / "sack_design_draft.png",
            export_paths=[
                # Same texture for worn/ground + inventory — ITS downscales on map.
                (equipment / "Broodling_Sack_tile.png", (inv_w, inv_h)),
                (equipment / "Broodling_Sack_icon.png", (inv_w, inv_h)),
                (mod_path / "Items" / "sw_broodmother_back.png", (inv_w, inv_h)),
            ],
            meta=_job_meta("equipment", "sack"),
        ),
        AssetJob(
            asset_id="broodling_ground",
            sd35=get_pp("broodling_ground"),
            draft_path=draft_dir / "broodling_ground_design_draft.png",
            export_paths=[
                (creatures / "sw_broodling_ground.png", (map_w, map_h)),
                (mod_path / "Creatures" / "sw_broodling_ground.png", (map_w, map_h)),
            ],
            meta=_job_meta("creature", "broodling_ground", variant="ground"),
        ),
        AssetJob(
            asset_id="broodling_flying",
            sd35=get_pp("broodling_flying"),
            draft_path=draft_dir / "broodling_flying_design_draft.png",
            export_paths=[
                (creatures / "sw_broodling_flying.png", (map_w, map_h)),
                (mod_path / "Creatures" / "sw_broodling_flying.png", (map_w, map_h)),
            ],
            meta=_job_meta("creature", "broodling_flying", variant="flying"),
        ),
    ]

    for prompt_key, asset_id, filename, tier in unique_creature_jobs:
        jobs.append(
            AssetJob(
                asset_id=asset_id,
                sd35=get_pp(prompt_key),
                draft_path=draft_dir / f"{asset_id}_design_draft.png",
                export_paths=[(creatures / filename, (map_w, map_h))],
                meta=_job_meta("creature", prompt_key, tier=tier),
            )
        )

    # --- Extra textures + Spring UI icons (mod UI/ + Unity Art mirror) ---
    ui_dir = mod_path / "UI"
    ui_icons = ui_dir / "Icons"
    tex_extra = textures / "Materials"
    unity_art = Path(
        r"C:\Users\Arend\AppData\LocalLow\Freehold Games\CavesOfQud"
        r"\Broodmother Mutation UI\Broodmother Mutation UI work"
        r"\Assets\Arendeth_UI\Art\Broodmother"
    )
    unity_icons = unity_art / "Icons"
    unity_tex = unity_art / "Textures"

    def _ui_exports(name: str, size: Tuple[int, int], *, icon: bool = True) -> List[Tuple[Path, Tuple[int, int]]]:
        paths: List[Tuple[Path, Tuple[int, int]]] = []
        if icon:
            paths.append((ui_icons / f"{name}.png", size))
            paths.append((unity_icons / f"{name}.png", size))
        else:
            paths.append((tex_extra / f"{name}.png", size))
            paths.append((unity_tex / f"{name}.png", size))
        return paths

    texture_ui_jobs = [
        ("preview", "workshop_preview", [(mod_path / "preview.png", (512, 512))], "preview"),
        # Dual-view item (inventory + ground/worn): hi-res; ITS rescales on map.
        ("texture_carapace", "texture_carapace", [
            (equipment / "sw_carapace.png", (inv_w, inv_h)),
            (mod_path / "Items" / "sw_carapace.png", (inv_w, inv_h)),
            (unity_tex / "sw_carapace.png", (inv_w, inv_h)),
        ], "texture"),
        ("texture_membrane", "texture_membrane", _ui_exports("texture_membrane", (256, 256), icon=False), "texture"),
        ("texture_biometal", "texture_biometal", _ui_exports("texture_biometal", (256, 256), icon=False), "texture"),
        ("texture_chitin", "texture_chitin", _ui_exports("texture_chitin", (256, 256), icon=False), "texture"),
        ("ui_biomod_chip", "ui_biomod_chip", _ui_exports("ui_biomod_chip", (inv_w, inv_h)), "ui"),
        ("ui_birth_badge", "ui_birth_badge", _ui_exports("ui_birth_badge", (inv_w, inv_h)), "ui"),
        ("ui_evolution_node", "ui_evolution_node", _ui_exports("ui_evolution_node", (inv_w, inv_h)), "ui"),
        ("ui_swarm_frame", "ui_swarm_frame", _ui_exports("ui_swarm_frame", (128, 128)), "ui"),
        ("ui_panel", "ui_panel", _ui_exports("ui_panel", (256, 256), icon=False), "ui"),
        ("ui_button", "ui_button", _ui_exports("ui_button", (inv_w, inv_h)), "ui"),
        ("ui_menu_row", "ui_menu_row", _ui_exports("ui_menu_row", (256, 64), icon=False), "ui"),
        ("ui_status_strip", "ui_status_strip", _ui_exports("ui_status_strip", (256, 32), icon=False), "ui"),
        ("ui_tier_pip", "ui_tier_pip", _ui_exports("ui_tier_pip", (32, 32)), "ui"),
    ]

    for prompt_key, asset_id, export_paths, kind in texture_ui_jobs:
        if not (prompt_spec.get(prompt_key) or {}).get("prompt"):
            print(f"  [WARN] Missing prompt key '{prompt_key}' — skipping {asset_id}")
            continue
        jobs.append(
            AssetJob(
                asset_id=asset_id,
                sd35=get_pp(prompt_key),
                draft_path=draft_dir / f"{asset_id}_design_draft.png",
                export_paths=export_paths,
                meta=_job_meta(kind, prompt_key),
            )
        )

    # Persist merged pack (never drop curated UI/texture keys).
    if isinstance(prompt_spec, dict):
        if existing_pack is not None and prompt_spec is not existing_pack:
            prompt_spec = _merge_prompt_pack(existing_pack, prompt_spec)
        _write_json(draft_dir / "prompt_pack.json", prompt_spec)
    # Always mirror theme metadata for Unity AI consumers.
    _write_json(
        draft_dir / "biomutation_theme_meta.json",
        {
            "theme": "biomutation",
            "job_count": len(jobs),
            "prompt_key_count": sum(
                1 for k in REQUIRED_PROMPT_KEYS if _prompt_entry_complete((prompt_spec or {}).get(k))
            ),
            "prompt_keys": list(REQUIRED_PROMPT_KEYS),
            "unique_creatures": [j[1] for j in unique_creature_jobs],
            "ui_keys": [j[0] for j in texture_ui_jobs if str(j[3]) == "ui"],
            "texture_keys": [j[0] for j in texture_ui_jobs if str(j[3]) in ("texture", "preview")],
            "unity_docs": "Broodmother Mutation UI/.../Docs/BIOMUTATION_THEME_MATERIALS.md",
        },
    )
    return jobs


def _generate_broodmother_audio(mod_path: Path, sounds_path: Path, verbose: bool = False) -> int:
    """Generate optional audio assets for Broodmother mutation."""
    if not AUDIO_GENERATOR_AVAILABLE or QudAudioGenerator is None:
        if verbose:
            print("  [SKIP] Audio generation (dependencies not available)")
        return 0
    
    sounds_path.mkdir(parents=True, exist_ok=True)
    sounds_created = 0
    
    try:
        audio_gen = QudAudioGenerator()
        
        # Gestation/birth sound
        gestation = audio_gen.generate_spawn_sound(creature_type="organic", duration=2.5, seed=50)
        if gestation is not None:
            gestation_path = sounds_path / "Broodmother_gestation.ogg"
            sf.write(str(gestation_path), gestation, audio_gen.sample_rate)
            sounds_created += 1
            if verbose:
                print(f"    [OK] Created: {gestation_path.name}")
        
        # Hatch sound
        hatch = audio_gen.generate_spawn_sound(creature_type="organic", duration=1.2, seed=51)
        if hatch is not None:
            hatch_path = sounds_path / "Broodling_hatch.ogg"
            sf.write(str(hatch_path), hatch, audio_gen.sample_rate)
            sounds_created += 1
            if verbose:
                print(f"    [OK] Created: {hatch_path.name}")
        
        # Chirp/squeak
        chirp = audio_gen.generate_attack_sound(creature_type="small", duration=0.4, seed=53)
        if chirp is not None:
            chirp_path = sounds_path / "Broodling_chirp.ogg"
            sf.write(str(chirp_path), chirp, audio_gen.sample_rate)
            sounds_created += 1
            if verbose:
                print(f"    [OK] Created: {chirp_path.name}")
        
    except Exception as e:
        if verbose:
            print(f"    [WARN] Audio generation failed: {e}")
    
    return sounds_created


def _compose_preview_image(
    mod_path: Path,
    icon_path: Path,
    sack_path: Path,
    creature_paths: List[Path],
    preview_path: Path,
    verbose: bool = False
) -> bool:
    """
    Compose a preview image from generated assets.
    Arranges icon, sack, and creature sprites in a grid layout.
    """
    try:
        # Check if required assets exist
        if not icon_path.exists():
            if verbose:
                print(f"    [WARN] Icon not found: {icon_path.name}, skipping preview")
            return False
        
        # Load icon
        icon = Image.open(icon_path).convert("RGBA")
        
        # Calculate grid dimensions
        # Layout: Icon at top center, sack below, creatures in a row
        cell_size = max(icon.size[0], icon.size[1], 128)  # Use largest dimension or 128px minimum
        padding = 16
        
        # Count available creatures
        available_creatures = [p for p in creature_paths if p.exists()]
        num_creatures = len(available_creatures)
        
        # Calculate canvas size
        # Top row: icon (centered)
        # Middle row: sack (centered)
        # Bottom row: creatures (centered)
        rows = 3 if sack_path.exists() else 2
        cols = max(1, num_creatures) if rows == 3 else 1
        
        canvas_width = cell_size * cols + padding * (cols + 1)
        canvas_height = cell_size * rows + padding * (rows + 1)
        
        # Create canvas with transparent background
        canvas = Image.new("RGBA", (canvas_width, canvas_height), (0, 0, 0, 0))
        
        # Draw icon (top center)
        icon_x = (canvas_width - icon.size[0]) // 2
        icon_y = padding
        canvas.paste(icon, (icon_x, icon_y), icon)
        
        # Draw sack (middle center, if exists)
        if sack_path.exists():
            sack = Image.open(sack_path).convert("RGBA")
            sack_x = (canvas_width - sack.size[0]) // 2
            sack_y = padding + cell_size + padding
            canvas.paste(sack, (sack_x, sack_y), sack)
        
        # Draw creatures (bottom row, centered)
        if available_creatures:
            creature_row_y = padding + cell_size * 2 + padding if sack_path.exists() else padding + cell_size + padding
            total_creature_width = sum(Image.open(p).size[0] for p in available_creatures)
            total_spacing = padding * (num_creatures + 1)
            start_x = (canvas_width - total_creature_width - total_spacing) // 2 + padding
            
            current_x = start_x
            for creature_path in available_creatures:
                creature = Image.open(creature_path).convert("RGBA")
                creature_y = creature_row_y + (cell_size - creature.size[1]) // 2
                canvas.paste(creature, (current_x, creature_y), creature)
                current_x += creature.size[0] + padding
        
        # Save preview
        preview_path.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(preview_path, "PNG")
        
        if verbose:
            print(f"    [OK] Preview composed: {preview_path.name} ({canvas_width}x{canvas_height})")
        
        return preview_path.exists() and preview_path.stat().st_size > 0
        
    except Exception as e:
        if verbose:
            print(f"    [ERROR] Failed to compose preview: {e}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate Broodmother Mutation assets using Ollama + SD3.5 drafts"
    )
    parser.add_argument("mod_path", type=str, help="Path to Broodmother Mutation mod directory")
    parser.add_argument("--skip-sd35", action="store_true", help="Do not generate SD3.5 drafts (export-only if drafts exist)")
    parser.add_argument("--skip-export", action="store_true", help="Do not export final assets (draft-only)")
    parser.add_argument("--draft-dir", type=str, default="DesignDrafts", help="Draft output folder (inside mod)")
    parser.add_argument("--no-postprocess", action="store_true", help="Disable ImageMagick post-processing (Tools/Shared)")
    parser.add_argument("--load-existing", action="store_true", help="Load existing prompt pack/job specs (skip Ollama)")
    parser.add_argument(
        "--force-prompt-pack",
        action="store_true",
        help="Regenerate prompt_pack.json via Ollama even if the existing pack is already complete (34/34)",
    )
    parser.add_argument("--generate-audio", action="store_true", help="Generate optional audio assets")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose progress output")
    parser.add_argument("--unload-models", action="store_true", help="Unload all Ollama models after generation (free VRAM)")
    parser.add_argument("--parallel", action="store_true", help="Use multithreaded event bus for parallel processing")
    parser.add_argument("--max-workers", type=int, default=None, help="Maximum worker threads for parallel processing (default: auto)")
    parser.add_argument("--no-cache", action="store_true", help="Disable caching (force regeneration)")
    parser.add_argument("--cache-dir", type=str, default=None, help="Cache directory (default: ~/.cache/asset_generator)")
    parser.add_argument(
        "--quality-mode",
        choices=["draft", "police", "full"],
        default=None,
        help=(
            "Quality loop tier: draft=SD only (fast); police=heuristic+one Ollama critic+SD retry "
            "(default; catches broken drafts); full=sequential multi-model (slow). "
            "Implied by --art-director (police) / --multi-agent (full) when omitted."
        ),
    )
    parser.add_argument("--art-director", action="store_true", help="Enable art director police loop (same as --quality-mode police)")
    parser.add_argument("--multi-agent", action="store_true", help="Full sequential multi-model review (same as --quality-mode full; slow)")
    parser.add_argument("--max-refinement-iterations", type=int, default=3, help="Maximum refinement iterations (default: 3)")
    parser.add_argument("--quality-threshold", type=int, default=75, help="Quality score threshold to stop refining (0-100, default: 75)")
    parser.add_argument("--no-enable-vision-models", action="store_false", dest="enable_vision_models", help="Disable vision models (LLaVA, Qwen3-VL) for multi-agent mode")
    parser.add_argument("--no-enable-preference-scorer", action="store_false", dest="enable_preference_scorer", help="Disable PickScore/LAION-Aesthetic for preference scoring")
    parser.add_argument(
        "--no-auto-start-sd",
        action="store_true",
        help="Do not auto-start SD3.5 on :1338 (quality loop will skip drafts if server is down)",
    )
    parser.add_argument(
        "--high-detail",
        action="store_true",
        help="Inventory/UI icons at 64x96 (Tile size scaling). Map tiles stay 16x24 — hi-res on-map just downscales.",
    )
    parser.add_argument(
        "--tile-resolution",
        type=int,
        default=None,
        help="Map-tile height (keeps 2:3). Default 24 (16x24). Prefer leaving at 24; on-map hi-res is wasted.",
    )
    parser.add_argument(
        "--icon-resolution",
        type=int,
        default=None,
        help="Inventory/UI icon height (keeps 2:3). Default 96 (64x96) via Tile size scaling / ITS.",
    )
    parser.add_argument("--ollama-timeout", type=int, default=600, help="Timeout for Ollama calls in seconds (default: 600 = 10 minutes). Model loading can take 1-10 minutes, especially if downloading. Increase if models are still downloading.")
    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_OLLAMA_MODEL,
        help=f"Ollama model for prompt packs / art director (default: {DEFAULT_OLLAMA_MODEL}; uncensored, no filters)",
    )
    parser.add_argument(
        "--only",
        type=str,
        default=None,
        help="Comma-separated asset_id filter (e.g. broodmother_icon,broodling_sack,texture_carapace)",
    )
    parser.add_argument(
        "--force-drafts",
        action="store_true",
        help="Delete selected jobs' design_draft PNGs before SD so they regenerate",
    )
    
    # Set defaults for vision models and preference scorer
    parser.set_defaults(enable_vision_models=True, enable_preference_scorer=True)

    args = parser.parse_args()

    # Resolve quality mode: default police so broken drafts are gated+retried.
    # draft = fast opt-out; full = multi-agent; flags imply mode when --quality-mode omitted.
    if args.quality_mode:
        quality_mode = args.quality_mode
    elif args.multi_agent:
        quality_mode = "full"
    elif args.art_director:
        quality_mode = "police"
    else:
        quality_mode = "police"
    args.quality_mode = quality_mode
    if quality_mode == "full":
        args.multi_agent = True
        args.art_director = True
    elif quality_mode == "police":
        args.art_director = True

    # Pin uncensored model for all subsequent _ollama_json / call_ollama sites
    global OLLAMA_MODEL
    OLLAMA_MODEL = _resolve_ollama_model(args.model)
    if args.verbose:
        print(f"[INFO] Ollama model (uncensored): {OLLAMA_MODEL}")
        print(f"[INFO] Quality mode: {quality_mode} (draft=fast, police=critic+retry, full=multi-model slow)")
    # Initialize cache
    cache = None
    if CACHE_AVAILABLE and not args.no_cache:
        cache_dir = Path(args.cache_dir) if args.cache_dir else None
        cache = get_cache(
            max_size=2000,
            default_ttl=3600 * 24,  # 24 hours default
            cache_dir=cache_dir,
            enable_disk_cache=True,
            verbose=args.verbose
        )
        if args.verbose:
            print(f"[INFO] Cache enabled (disk: {cache.cache_dir})")
    elif args.verbose:
        if args.no_cache:
            print("[INFO] Cache disabled (--no-cache)")
        else:
            print("[WARN] Cache not available (cache_manager.py not found)")

    mod_path = Path(args.mod_path)
    if not mod_path.exists():
        print(f"ERROR: Mod path does not exist: {mod_path}")
        return 1

    draft_dir = mod_path / args.draft_dir
    draft_dir.mkdir(parents=True, exist_ok=True)

    # Skip Ollama reachability check when a complete pack will be reused.
    needs_ollama_prompts = True
    if args.load_existing:
        needs_ollama_prompts = False
    elif not args.force_prompt_pack:
        pack_path = draft_dir / "prompt_pack.json"
        if pack_path.exists():
            try:
                if _prompt_pack_complete(json.loads(pack_path.read_text(encoding="utf-8"))):
                    needs_ollama_prompts = False
                    print("[OK] Complete prompt_pack.json present — Ollama not required for prompts")
            except Exception:
                pass

    if needs_ollama_prompts:
        print("[OLLAMA] Testing connection to Ollama server...")
        if not test_ollama_connection():
            print("[ERROR] Ollama connection failed!")
            print("[ERROR] Please ensure:")
            print("[ERROR]   1. Ollama is installed and running")
            print("[ERROR]   2. Ollama service is accessible at http://localhost:11434")
            print("[ERROR]   3. At least one model is installed (e.g., ollama pull llama3.1:8b)")
            print("[ERROR]   4. Check Process Explorer for 'ollama.exe' or 'ollama serve' process")
            raise RuntimeError("Ollama is required but not available. Start Ollama and try again.")
        print("[OK] Ollama connection verified")
        if args.verbose:
            loaded = get_loaded_models()
            if loaded:
                print(f"[INFO] Currently loaded models: {', '.join(loaded)}")
            else:
                print("[INFO] No models currently loaded in memory (will load on first request)")

    shared_dir = Path(__file__).resolve().parent.parent / "Shared"
    sd_module_path = shared_dir / "StableDiffusionIntegration.psm1"
    
    if args.verbose:
        if sd_module_path.exists():
            print(f"[OK] SD3.5 module found: {sd_module_path.name}")
        else:
            print(f"[WARN] SD3.5 module not found (drafts will be skipped)")
    
    # Creature map bodies: 32x48 (subject-cropped). Dual-view gear + UI: 64x96 via
    # Tile size scaling — inventory keeps detail; map/ground ITS-rescales to the cell.
    def _size_from_height(h: int) -> Tuple[int, int]:
        h = max(8, int(h))
        w = max(8, int(round(h * 16 / 24)))
        return (w, h)

    if args.tile_resolution is not None:
        tile_size = _size_from_height(args.tile_resolution)
    else:
        tile_size = (32, 48)

    if args.icon_resolution is not None:
        icon_size = _size_from_height(args.icon_resolution)
    else:
        icon_size = (64, 96)

    if args.verbose:
        print(f"[INFO] Creature map tiles: {tile_size[0]}x{tile_size[1]}")
        print(f"[INFO] Dual-view gear / inventory / UI: {icon_size[0]}x{icon_size[1]} (ITS rescales on map)")
        print("[INFO] Truecolor: glow/flux/void/crystal/shard/phantom/mindling/necroling + UI materials only")
        if args.skip_sd35:
            print("[INFO] --skip-sd35: will build prompt pack / jobs only (no SD drafts)")
        if args.load_existing:
            print("[INFO] --load-existing: using DesignDrafts/prompt_pack.json (no Ollama prompt gen)")
        if args.force_prompt_pack:
            print("[INFO] --force-prompt-pack: will regenerate prompt_pack.json via Ollama")
        print("[INFO] Next: Building Asset Jobs (Ollama may load a model now if prompts are needed)")
        print("[INFO] Note: generator python often shows ~0% CPU while waiting on Ollama load or SD HTTP;")
        print("[INFO]       GPU work is in ollama.exe or SD server.py — check those processes.")

    print("\n=== Building Asset Jobs ===")
    jobs = build_jobs(
        mod_path=mod_path,
        draft_dir=draft_dir,
        load_existing=args.load_existing,
        cache=cache,
        tile_size=tile_size,
        icon_size=icon_size,
        high_detail=bool(args.high_detail or (args.tile_resolution is not None and args.tile_resolution > 24)),
        ollama_timeout=args.ollama_timeout,
        force_prompt_pack=args.force_prompt_pack,
    )

    if args.only:
        only_ids = {x.strip() for x in args.only.split(",") if x.strip()}
        before = len(jobs)
        jobs = [j for j in jobs if j.asset_id in only_ids]
        missing = sorted(only_ids - {j.asset_id for j in jobs})
        print(f"[INFO] --only: {len(jobs)}/{before} jobs matched")
        if missing:
            print(f"[WARN] --only unknown asset_id(s): {', '.join(missing)}")
        if not jobs:
            print("[ERROR] No jobs left after --only filter")
            return 1

    if args.force_drafts:
        cleared = 0
        for job in jobs:
            if job.draft_path.exists():
                try:
                    job.draft_path.unlink()
                    cleared += 1
                    if args.verbose:
                        print(f"  [FORCE] Deleted draft {job.draft_path.name}")
                except OSError as exc:
                    print(f"  [WARN] Could not delete {job.draft_path.name}: {exc}")
        print(f"[INFO] --force-drafts: cleared {cleared} draft PNG(s)")

    results = {"drafts_created": 0, "drafts_skipped": 0, "exports_created": 0, "jobs": [], "sounds_created": 0, "retries": 0, "reviews": 0}
    start = time.time()

    print(f"\n=== Processing {len(jobs)} Asset(s) [quality-mode={args.quality_mode}] ===")

    # Police/full: sequential critique→correct→retry with exclusive SD/Ollama GPU ownership.
    # Parallel event-bus + concurrent Ollama review fights 11GB VRAM — skip it for these modes.
    if args.quality_mode in ("police", "full"):
        try:
            from broodmother_quality_loop import QualityLoopConfig, run_quality_loop
        except ImportError:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from broodmother_quality_loop import QualityLoopConfig, run_quality_loop

        multi_agent_director = None
        if args.quality_mode == "full" and MULTI_AGENT_AVAILABLE:
            try:
                multi_agent_director = MultiAgentArtDirector(
                    ollama_url=os.environ.get("OLLAMA_HOST", "http://localhost:11434"),
                    enable_vision_models=args.enable_vision_models,
                    enable_preference_scorer=args.enable_preference_scorer,
                    verbose=args.verbose,
                )
                if args.verbose:
                    print("[OK] Multi-agent art director (sequential swaps) initialized")
            except Exception as e:
                print(f"[WARN] Multi-agent init failed: {e}; using single critic")
                multi_agent_director = None

        # Persist job specs for re-runs
        for job in jobs:
            _write_json(
                draft_dir / f"{job.asset_id}.job.json",
                {
                    "asset_id": job.asset_id,
                    "sd35": {
                        "prompt": job.sd35.prompt,
                        "negative_prompt": job.sd35.negative_prompt,
                        "width": job.sd35.width,
                        "height": job.sd35.height,
                        "steps": job.sd35.steps,
                        "guidance_scale": job.sd35.guidance_scale,
                        "seed": job.sd35.seed,
                        "enhance_with_ollama": False,
                        "auto_start_server": False,
                    },
                    "draft_path": str(job.draft_path),
                    "exports": [{"path": str(p), "size": list(sz)} for p, sz in job.export_paths],
                    "meta": job.meta,
                },
            )

        print(
            f"\n=== Quality loop ({args.quality_mode}) — "
            "heuristic gate + critique → corrections → SD retry ==="
        )
        if args.quality_mode == "police":
            print("  [INFO] Police: one Ollama critic (wizardlm). Use --quality-mode full for multi-model (slow).")
        else:
            print("  [INFO] Full: sequential multi-model review (vastly slower; exclusive GPU swaps).")

        loop_results = run_quality_loop(
            jobs,
            draft_dir=draft_dir,
            sd_module_path=sd_module_path,
            shared_dir=shared_dir,
            config=QualityLoopConfig(
                mode=args.quality_mode,
                quality_threshold=args.quality_threshold,
                max_refinement_iterations=args.max_refinement_iterations,
                verbose=args.verbose,
                skip_sd35=args.skip_sd35,
                skip_export=args.skip_export,
                no_postprocess=args.no_postprocess,
                auto_start_sd=not args.no_auto_start_sd,
                sd_wait_sec=150,
                enable_vision_models=args.enable_vision_models,
                enable_preference_scorer=args.enable_preference_scorer,
                ollama_model=OLLAMA_MODEL,
            ),
            run_sd_generate=_run_sd35_generate_single,
            art_director_review=_art_director_review,
            export_from_draft=_export_from_draft,
            imagemagick_post=_run_imagemagick_postprocess_qud,
            multi_agent_director=multi_agent_director,
            cache=cache,
        )
        results.update({k: loop_results.get(k, results.get(k)) for k in (
            "drafts_created", "drafts_skipped", "exports_created", "retries", "reviews", "jobs"
        )})
        results["quality_mode"] = args.quality_mode
        results["phase_log"] = loop_results.get("phase_log", [])

        # Skip legacy parallel/sequential draft paths — jump to preview/audio/summary
        _quality_loop_done = True
    else:
        _quality_loop_done = False

    # Initialize multi-agent art director if enabled (legacy parallel path only)
    multi_agent_director = None
    if not _quality_loop_done and args.multi_agent and MULTI_AGENT_AVAILABLE:
        if args.verbose:
            print("[INFO] Initializing multi-agent art director system...")
        try:
            multi_agent_director = MultiAgentArtDirector(
                ollama_url=os.environ.get("OLLAMA_HOST", "http://localhost:11434"),
                enable_vision_models=args.enable_vision_models,
                enable_preference_scorer=args.enable_preference_scorer,
                verbose=args.verbose,
            )
            if args.verbose:
                print("[OK] Multi-agent art director initialized")
                enabled_agents = [role.value for role, config in multi_agent_director.agents.items() if config.enabled]
                print(f"[INFO] Enabled agents: {', '.join(enabled_agents)}")
        except Exception as e:
            if args.verbose:
                print(f"[WARN] Failed to initialize multi-agent director: {e}")
            multi_agent_director = None
    elif args.multi_agent and not MULTI_AGENT_AVAILABLE:
        if args.verbose:
            print("[WARN] Multi-agent art director not available (multi_agent_art_director.py not found)")
    
    # Use event bus for parallel processing if enabled (draft mode / legacy only)
    use_event_bus = (not _quality_loop_done) and args.parallel and EVENT_BUS_AVAILABLE

    if _quality_loop_done:
        pass  # drafts+exports already handled by broodmother_quality_loop
    elif use_event_bus:
        print(f"  [PARALLEL] Using multithreaded event bus ({args.max_workers or 'auto'} workers)")
        # Enable thermal throttling with 75°C max temperature (system slows at 80°C)
        bus = EventBus(
            max_workers=args.max_workers,
            verbose=args.verbose,
            max_temp_c=75.0,
            temp_check_interval=2.0,
            enable_thermal_throttling=True
        )
        
        # Track refinement state per asset
        asset_refinement_state = {}  # asset_id -> {iteration, best_quality, best_path, previous_feedback}
        
        # Make multi_agent_director available to handlers via closure
        handler_multi_agent_director = multi_agent_director
        
        # Register event handlers (closures capture bus, args, and multi_agent_director)
        def handle_sd35_draft(event: Event) -> EventResult:
            """Handle SD3.5 draft generation event - generates single draft, then publishes review."""
            params = Sd35Params(**event.payload["params"])
            output_path = Path(event.payload["output_path"])
            sd_module_path = Path(event.payload["sd_module_path"])
            asset_id = event.payload.get("asset_id", event.job_id)
            asset_type = event.payload.get("asset_type", "asset")
            iteration = event.payload.get("iteration", 0)
            
            # Skip actual generation if this is a completion signal (iteration -1)
            if iteration == -1:
                return EventResult(
                    event_type=EventType.SD35_DRAFT,
                    job_id=event.job_id,
                    success=True,
                    result={"draft_path": str(output_path), "iteration": -1, "completion": True}
                )
            
            try:
                # Generate single draft
                success = _run_sd35_generate_single(
                    sd_module_path=sd_module_path,
                    params=params,
                    output_path=output_path,
                    verbose=args.verbose,
                    cache=cache,
                )
                
                if not success:
                    return EventResult(
                        event_type=EventType.SD35_DRAFT,
                        job_id=event.job_id,
                        success=False,
                        error="SD3.5 generation failed"
                    )
                
                # If art director enabled, publish review event immediately (parallel)
                if args.art_director:
                    review_id = f"{asset_id}_review_iter{iteration}"
                    try:
                        from event_bus import Priority
                        review_priority = Priority.HIGH.value
                    except ImportError:
                        review_priority = 50
                    
                    bus.publish(
                        EventType.ART_DIRECTOR_REVIEW,
                        review_id,
                        {
                            "image_path": str(output_path),
                            "original_prompt": params.prompt,
                            "asset_type": asset_type,
                            "asset_id": asset_id,
                            "iteration": iteration,
                            "final_output_path": str(event.payload.get("final_output_path", output_path)),
                            "params": event.payload["params"],  # Pass through for refinement
                            "sd_module_path": str(sd_module_path),
                        },
                        priority=review_priority,
                        dependencies=[f"{EventType.SD35_DRAFT.value}:{event.job_id}"]  # Review depends on draft
                    )
                    
                    if args.verbose:
                        print(f"    [REVIEW] Published art director review event for {asset_id} (iteration {iteration})")
                
                return EventResult(
                    event_type=EventType.SD35_DRAFT,
                    job_id=event.job_id,
                    success=True,
                    result={"draft_path": str(output_path), "iteration": iteration}
                )
            except Exception as e:
                return EventResult(
                    event_type=EventType.SD35_DRAFT,
                    job_id=event.job_id,
                    success=False,
                    error=str(e)
                )
        
        def handle_art_director_review(event: Event) -> EventResult:
            """Handle art director review - analyzes draft and triggers refinement if needed."""
            image_path = Path(event.payload["image_path"])
            original_prompt = event.payload["original_prompt"]
            asset_type = event.payload["asset_type"]
            asset_id = event.payload["asset_id"]
            iteration = event.payload["iteration"]
            final_output_path = Path(event.payload["final_output_path"])
            params_dict = event.payload["params"]
            sd_module_path = Path(event.payload["sd_module_path"])
            
            # Initialize state if needed
            if asset_id not in asset_refinement_state:
                asset_refinement_state[asset_id] = {
                    "iteration": 0,
                    "best_quality": 0,
                    "best_path": None,
                    "previous_feedback": None
                }
            
            state = asset_refinement_state[asset_id]
            
            try:
                if args.verbose:
                    print(f"    [REVIEW] Art director reviewing {asset_id} (iteration {iteration + 1})...")
                
                # Use multi-agent system if available, otherwise fall back to single agent
                if handler_multi_agent_director is not None:
                    # Multi-agent review (parallel vision models + specialized agents)
                    aggregated_feedback = handler_multi_agent_director.review_asset(
                        image_path=image_path,
                        original_prompt=original_prompt,
                        asset_type=asset_type,
                        iteration=iteration,
                        previous_feedback=state["previous_feedback"],
                        target_style="Caves of Qud roguelike pixel art, organic biotech aesthetic",
                    )
                    
                    quality_score = aggregated_feedback.overall_quality
                    needs_refinement = aggregated_feedback.needs_refinement
                    feedback = aggregated_feedback.creative_director_notes or ""
                    refined_prompt = aggregated_feedback.refined_prompt
                    refined_negative = aggregated_feedback.refined_negative_prompt
                    
                    if args.verbose:
                        print(f"    [MULTI-AGENT] {asset_id}: Quality {quality_score:.1f}/100")
                        if aggregated_feedback.technical_qa:
                            print(f"    [MULTI-AGENT] Technical QA: {aggregated_feedback.technical_qa.overall_score:.2f}/1.0")
                        if aggregated_feedback.composition:
                            print(f"    [MULTI-AGENT] Composition: {aggregated_feedback.composition.overall_score:.2f}/1.0")
                        if aggregated_feedback.preference_score:
                            print(f"    [MULTI-AGENT] Preference: {aggregated_feedback.preference_score.score:.1f}/10")
                        if aggregated_feedback.priority_fixes:
                            print(f"    [MULTI-AGENT] Priority fixes: {', '.join(aggregated_feedback.priority_fixes[:3])}")
                else:
                    # Single-agent review (fallback)
                    review = _art_director_review(
                        image_path=image_path,
                        original_prompt=original_prompt,
                        asset_type=asset_type,
                        iteration=iteration,
                        previous_feedback=state["previous_feedback"],
                        verbose=args.verbose,
                        cache=cache
                    )
                    
                    quality_score = review.get("quality_score", 0)
                    needs_refinement = review.get("needs_refinement", True)
                    feedback = review.get("feedback", "")
                    refined_prompt = review.get("refined_prompt", original_prompt)
                    refined_negative = review.get("refined_negative_prompt", "")
                
                if args.verbose:
                    print(f"    [REVIEW] {asset_id}: Quality {quality_score:.1f}/100 - {'Needs refinement' if needs_refinement else 'Quality threshold met'}")
                    if feedback and args.verbose:
                        print(f"    [REVIEW] Feedback: {feedback[:150]}...")
                
                # Track best iteration
                if quality_score > state["best_quality"]:
                    state["best_quality"] = quality_score
                    state["best_path"] = image_path
                    # Copy best to final output
                    import shutil
                    shutil.copy2(image_path, final_output_path)
                    if args.verbose:
                        print(f"    [REVIEW] {asset_id}: New best quality ({quality_score:.1f}/100), saved to final output")
                
                # Check if we need refinement
                if needs_refinement and quality_score < args.quality_threshold and iteration < args.max_refinement_iterations - 1:
                    # Publish refinement event (use refined prompts from review)
                    # refined_prompt and refined_negative are already set above
                    
                    next_iteration = iteration + 1
                    refinement_id = f"{asset_id}_refine_iter{next_iteration}"
                    
                    # Create refined params
                    refined_params = Sd35Params(
                        prompt=refined_prompt,
                        negative_prompt=refined_negative,
                        width=params_dict.get("width", 512),
                        height=params_dict.get("height", 512),
                        steps=params_dict.get("steps", 12),
                        guidance_scale=params_dict.get("guidance_scale", 7.0),
                        seed=params_dict.get("seed", 0) + next_iteration,  # Vary seed
                        enhance_with_ollama=params_dict.get("enhance_with_ollama", False),
                        auto_start_server=params_dict.get("auto_start_server", False),
                    )
                    
                    # Create iteration-specific output path
                    iter_output = final_output_path.parent / f"{final_output_path.stem}_iter{next_iteration}{final_output_path.suffix}"
                    
                    try:
                        from event_bus import Priority
                        refine_priority = Priority.HIGH.value
                    except ImportError:
                        refine_priority = 50
                    
                    bus.publish(
                        EventType.SD35_REFINE,
                        refinement_id,
                        {
                            "params": {
                                "prompt": refined_params.prompt,
                                "negative_prompt": refined_params.negative_prompt,
                                "width": refined_params.width,
                                "height": refined_params.height,
                                "steps": refined_params.steps,
                                "guidance_scale": refined_params.guidance_scale,
                                "seed": refined_params.seed,
                                "enhance_with_ollama": refined_params.enhance_with_ollama,
                                "auto_start_server": refined_params.auto_start_server,
                            },
                            "output_path": str(iter_output),
                            "final_output_path": str(final_output_path),
                            "sd_module_path": str(sd_module_path),
                            "asset_id": asset_id,
                            "asset_type": asset_type,
                            "iteration": next_iteration,
                        },
                        priority=refine_priority,
                        dependencies=[f"{EventType.ART_DIRECTOR_REVIEW.value}:{event.job_id}"]
                    )
                    
                    # Update state
                    state["iteration"] = next_iteration
                    state["previous_feedback"] = feedback
                    
                    if args.verbose:
                        print(f"    [REFINE] Published refinement event for {asset_id} (iteration {next_iteration + 1})")
                else:
                    # Done refining - use best result
                    if state["best_path"] and state["best_path"] != final_output_path:
                        import shutil
                        shutil.copy2(state["best_path"], final_output_path)
                    if args.verbose:
                        print(f"    [REVIEW] {asset_id}: Final quality {state['best_quality']}/100 (threshold: {args.quality_threshold})")
                    
                    # Publish completion event so exports know the final draft is ready
                    # This allows exports to proceed even if art director was used
                    completion_id = f"{asset_id}_final"
                    try:
                        from event_bus import Priority
                        completion_priority = Priority.NORMAL.value
                    except ImportError:
                        completion_priority = 0
                    
                    # Create a synthetic completion event that exports can depend on
                    # We'll use SD35_DRAFT with a special ID to signal completion
                    bus.publish(
                        EventType.SD35_DRAFT,
                        f"{asset_id}_final",
                        {
                            "params": params_dict,
                            "output_path": str(final_output_path),
                            "final_output_path": str(final_output_path),
                            "sd_module_path": str(sd_module_path),
                            "asset_id": asset_id,
                            "asset_type": asset_type,
                            "iteration": -1,  # Signal this is completion, not a draft
                        },
                        priority=completion_priority,
                        dependencies=[f"{EventType.ART_DIRECTOR_REVIEW.value}:{event.job_id}"]
                    )
                
                return EventResult(
                    event_type=EventType.ART_DIRECTOR_REVIEW,
                    job_id=event.job_id,
                    success=True,
                    result={
                        "quality_score": quality_score,
                        "needs_refinement": needs_refinement,
                        "feedback": feedback,
                        "best_quality": state["best_quality"]
                    }
                )
            except Exception as e:
                if args.verbose:
                    print(f"    [ERROR] Art director review failed: {e}")
                return EventResult(
                    event_type=EventType.ART_DIRECTOR_REVIEW,
                    job_id=event.job_id,
                    success=False,
                    error=str(e)
                )
        
        def handle_sd35_refine(event: Event) -> EventResult:
            """Handle SD3.5 refinement - generates improved draft based on art director feedback."""
            params = Sd35Params(**event.payload["params"])
            output_path = Path(event.payload["output_path"])
            final_output_path = Path(event.payload["final_output_path"])
            sd_module_path = Path(event.payload["sd_module_path"])
            asset_id = event.payload["asset_id"]
            asset_type = event.payload["asset_type"]
            iteration = event.payload["iteration"]
            
            try:
                if args.verbose:
                    print(f"    [REFINE] Generating refined draft for {asset_id} (iteration {iteration + 1})...")
                
                # Generate refined draft
                success = _run_sd35_generate_single(
                    sd_module_path=sd_module_path,
                    params=params,
                    output_path=output_path,
                    verbose=args.verbose,
                    cache=cache,
                )
                
                if not success:
                    return EventResult(
                        event_type=EventType.SD35_REFINE,
                        job_id=event.job_id,
                        success=False,
                        error="Refinement generation failed"
                    )
                
                # Immediately publish review for this refinement
                review_id = f"{asset_id}_review_iter{iteration}"
                try:
                    from event_bus import Priority
                    review_priority = Priority.HIGH.value
                except ImportError:
                    review_priority = 50
                
                bus.publish(
                    EventType.ART_DIRECTOR_REVIEW,
                    review_id,
                    {
                        "image_path": str(output_path),
                        "original_prompt": params.prompt,
                        "asset_type": asset_type,
                        "asset_id": asset_id,
                        "iteration": iteration,
                        "final_output_path": str(final_output_path),
                        "params": event.payload["params"],
                        "sd_module_path": str(sd_module_path),
                    },
                    priority=review_priority,
                    dependencies=[f"{EventType.SD35_REFINE.value}:{event.job_id}"]
                )
                
                if args.verbose:
                    print(f"    [REFINE] Published review for refinement {asset_id} (iteration {iteration + 1})")
                
                return EventResult(
                    event_type=EventType.SD35_REFINE,
                    job_id=event.job_id,
                    success=True,
                    result={"draft_path": str(output_path), "iteration": iteration}
                )
            except Exception as e:
                return EventResult(
                    event_type=EventType.SD35_REFINE,
                    job_id=event.job_id,
                    success=False,
                    error=str(e)
                )
        
        def handle_image_export(event: Event) -> EventResult:
            """Handle image export event."""
            draft_path = Path(event.payload["draft_path"])
            out_path = Path(event.payload["out_path"])
            size = tuple(event.payload["size"])
            truecolor = bool(event.payload.get("truecolor", False))
            
            # Check dependencies (priority inheritance handles boosting, but we still wait)
            if event.dependencies:
                # Wait for dependencies to complete
                max_wait = 1800  # 30 minutes
                wait_start = time.time()
                all_ready = True
                
                for dep_id in event.dependencies:
                    # Parse dependency ID (format: "event_type:job_id")
                    if ':' in dep_id:
                        dep_type_str, dep_job_id = dep_id.split(':', 1)
                        try:
                            dep_type = EventType(dep_type_str)
                        except ValueError:
                            if args.verbose:
                                print(f"    [WARN] Invalid dependency type: {dep_type_str}")
                            continue
                        
                        dep_ready = False
                        poll_interval = 0.5  # Start with 500ms polling
                        while (time.time() - wait_start) < max_wait:
                            dep_result = bus.get_result(dep_type, dep_job_id)
                            if dep_result:
                                if dep_result.success:
                                    dep_ready = True
                                    break
                                else:
                                    # Dependency failed
                                    return EventResult(
                                        event_type=EventType.IMAGE_EXPORT,
                                        job_id=event.job_id,
                                        success=False,
                                        error=f"Dependency {dep_id} failed: {dep_result.error}"
                                    )
                            # Adaptive polling: increase interval if waiting longer (up to 2s)
                            elapsed = time.time() - wait_start
                            if elapsed > 30:
                                poll_interval = min(2.0, poll_interval * 1.1)  # Gradually increase to 2s max
                            time.sleep(poll_interval)
                        
                        if not dep_ready:
                            all_ready = False
                            break
                
                if not all_ready:
                    return EventResult(
                        event_type=EventType.IMAGE_EXPORT,
                        job_id=event.job_id,
                        success=False,
                        error=f"Dependencies not ready after {max_wait}s"
                    )
            
            try:
                ok = _export_from_draft(draft_path, out_path, size, truecolor=truecolor)
                return EventResult(
                    event_type=EventType.IMAGE_EXPORT,
                    job_id=event.job_id,
                    success=ok,
                    result={"export_path": str(out_path), "size": size, "truecolor": truecolor}
                )
            except Exception as e:
                return EventResult(
                    event_type=EventType.IMAGE_EXPORT,
                    job_id=event.job_id,
                    success=False,
                    error=str(e)
                )
        
        def handle_postprocess(event: Event) -> EventResult:
            """Handle image post-processing event."""
            image_path = Path(event.payload["image_path"])
            shared_dir = Path(event.payload["shared_dir"])
            
            try:
                _run_imagemagick_postprocess_qud(shared_dir=shared_dir, image_path=image_path)
                return EventResult(
                    event_type=EventType.IMAGE_POSTPROCESS,
                    job_id=event.job_id,
                    success=True
                )
            except Exception as e:
                return EventResult(
                    event_type=EventType.IMAGE_POSTPROCESS,
                    job_id=event.job_id,
                    success=False,
                    error=str(e)
                )
        
        def handle_job_spec_save(event: Event) -> EventResult:
            """Handle job spec JSON save event."""
            spec_path = Path(event.payload["spec_path"])
            spec_data = event.payload["spec_data"]
            
            try:
                _write_json(spec_path, spec_data)
                return EventResult(
                    event_type=EventType.JOB_SPEC_SAVE,
                    job_id=event.job_id,
                    success=True
                )
            except Exception as e:
                return EventResult(
                    event_type=EventType.JOB_SPEC_SAVE,
                    job_id=event.job_id,
                    success=False,
                    error=str(e)
                )
        
        # Subscribe handlers
        bus.subscribe(EventType.SD35_DRAFT, handle_sd35_draft)
        if args.art_director:
            bus.subscribe(EventType.ART_DIRECTOR_REVIEW, handle_art_director_review)
            bus.subscribe(EventType.SD35_REFINE, handle_sd35_refine)
        bus.subscribe(EventType.IMAGE_EXPORT, handle_image_export)
        bus.subscribe(EventType.IMAGE_POSTPROCESS, handle_postprocess)
        bus.subscribe(EventType.JOB_SPEC_SAVE, handle_job_spec_save)
        
        # Start event bus
        bus.start()
        
        # Publish all events
        for job in jobs:
            # Save job spec (high priority, should complete first)
            job_spec_path = draft_dir / f"{job.asset_id}.job.json"
            # Import Priority enum if available
            try:
                from event_bus import Priority
                job_spec_priority = Priority.HIGH.value
            except ImportError:
                job_spec_priority = 50  # Fallback to HIGH priority value
            
            bus.publish(
                EventType.JOB_SPEC_SAVE,
                f"{job.asset_id}_spec",
                {
                    "spec_path": str(job_spec_path),
                    "spec_data": {
                        "asset_id": job.asset_id,
                        "sd35": {
                            "prompt": job.sd35.prompt,
                            "negative_prompt": job.sd35.negative_prompt,
                            "width": job.sd35.width,
                            "height": job.sd35.height,
                            "steps": job.sd35.steps,
                            "guidance_scale": job.sd35.guidance_scale,
                            "seed": job.sd35.seed,
                            "enhance_with_ollama": job.sd35.enhance_with_ollama,
                            "auto_start_server": job.sd35.auto_start_server,
                        },
                        "draft_path": str(job.draft_path),
                        "exports": [{"path": str(p), "size": list(sz)} for p, sz in job.export_paths],
                        "meta": job.meta,
                    }
                },
                priority=job_spec_priority
            )
            
            # Generate SD3.5 draft (if enabled)
            if not args.skip_sd35 and job.sd35.prompt:
                try:
                    from event_bus import Priority
                    draft_priority = Priority.NORMAL.value
                except ImportError:
                    draft_priority = 0
                
                    # For first iteration, use final output path
                    # For art director mode, iterations will be saved separately
                    first_iter_path = job.draft_path
                    if args.art_director:
                        first_iter_path = job.draft_path.parent / f"{job.draft_path.stem}_iter0{job.draft_path.suffix}"
                    
                    bus.publish(
                        EventType.SD35_DRAFT,
                        job.asset_id,
                        {
                            "params": {
                                "prompt": job.sd35.prompt,
                                "negative_prompt": job.sd35.negative_prompt,
                                "width": job.sd35.width,
                                "height": job.sd35.height,
                                "steps": job.sd35.steps,
                                "guidance_scale": job.sd35.guidance_scale,
                                "seed": job.sd35.seed,
                                "enhance_with_ollama": job.sd35.enhance_with_ollama,
                                "auto_start_server": job.sd35.auto_start_server,
                            },
                            "output_path": str(first_iter_path),
                            "final_output_path": str(job.draft_path),
                            "sd_module_path": str(sd_module_path),
                            "asset_id": job.asset_id,
                            "asset_type": job.meta.get("type", "asset"),
                            "iteration": 0,
                        },
                        priority=draft_priority
                    )
            
            # Export final assets (lower priority, depends on drafts)
            # Note: Exports will check if draft exists, so they can run in parallel
            # but will wait for draft completion if dependency is set
            if not args.skip_export:
                try:
                    from event_bus import Priority
                    export_priority = Priority.LOW.value
                except ImportError:
                    export_priority = -50
                
                for out_path, size in job.export_paths:
                    export_id = f"{job.asset_id}_{out_path.name}"
                    # If art director enabled, wait for final completion event (after all refinements)
                    # Otherwise, wait for initial draft
                    if args.art_director and not args.skip_sd35 and job.sd35.prompt:
                        # Wait for the final completion event (published when refinement is done)
                        depends_on = f"{EventType.SD35_DRAFT.value}:{job.asset_id}_final"
                    else:
                        depends_on = f"{EventType.SD35_DRAFT.value}:{job.asset_id}" if (not args.skip_sd35 and job.sd35.prompt) else None
                    
                    bus.publish(
                        EventType.IMAGE_EXPORT,
                        export_id,
                        {
                            "draft_path": str(job.draft_path),
                            "out_path": str(out_path),
                            "size": size,
                            "truecolor": bool(job.meta.get("truecolor", False)),
                        },
                        priority=export_priority,
                        dependencies=[depends_on] if depends_on else None
                    )
        
        # Wait for SD3.5 drafts to complete first (if generating drafts)
        if not args.skip_sd35:
            if args.verbose:
                print(f"  [PARALLEL] Waiting for {len([j for j in jobs if j.sd35.prompt])} SD3.5 draft(s)...")
            # Wait for all draft events
            for job in jobs:
                if job.sd35.prompt:
                    draft_result = bus.wait_for_event(EventType.SD35_DRAFT, job.asset_id, timeout=1800)
                    if draft_result and args.verbose:
                        status = "OK" if draft_result.success else "FAILED"
                        print(f"    [{status}] Draft: {job.asset_id}")
        
        # Now wait for all exports to complete
        if not args.skip_export:
            if args.verbose:
                export_count = sum(len(j.export_paths) for j in jobs)
                print(f"  [PARALLEL] Waiting for {export_count} export(s)...")
        
        # Wait for all events (drafts + exports) to complete
        bus.wait_for_all(timeout=3600)  # 1 hour max total
        
        # Collect results and publish post-processing events
        postprocess_events = []
        for job in jobs:
            job_result = {"asset_id": job.asset_id, "draft": str(job.draft_path), "exports": []}
            
            # Check SD3.5 draft result
            draft_result = bus.get_result(EventType.SD35_DRAFT, job.asset_id)
            if draft_result:
                if draft_result.success:
                    results["drafts_created"] += 1
                else:
                    results["drafts_skipped"] += 1
            
            # Check export results and queue post-processing
            if not args.skip_export:
                for out_path, size in job.export_paths:
                    export_id = f"{job.asset_id}_{out_path.name}"
                    export_result = bus.get_result(EventType.IMAGE_EXPORT, export_id)
                    if export_result and export_result.success:
                        results["exports_created"] += 1
                        job_result["exports"].append({
                            "path": str(out_path),
                            "size": list(size),
                            "ok": True
                        })
                        
                        # Queue post-processing if enabled
                        if not args.no_postprocess:
                            try:
                                from event_bus import Priority
                                postprocess_priority = Priority.LOW.value
                            except ImportError:
                                postprocess_priority = -50
                            
                            postprocess_id = f"{export_id}_postprocess"
                            bus.publish(
                                EventType.IMAGE_POSTPROCESS,
                                postprocess_id,
                                {
                                    "image_path": str(out_path),
                                    "shared_dir": str(shared_dir),
                                },
                                priority=postprocess_priority,
                                dependencies=[export_id]  # Post-process depends on export
                            )
                            postprocess_events.append(postprocess_id)
                    else:
                        job_result["exports"].append({
                            "path": str(out_path),
                            "size": list(size),
                            "ok": False
                        })
            
            results["jobs"].append(job_result)
        
        # Wait for post-processing to complete (if any)
        if postprocess_events:
            if args.verbose:
                print(f"  [PARALLEL] Waiting for {len(postprocess_events)} post-processing task(s)...")
            bus.wait_for_all(timeout=300)  # 5 minutes for post-processing
        
        # Get final stats
        stats = bus.get_stats()
        if args.verbose:
            print(f"  [PARALLEL] Stats: {stats['events_processed']} processed, "
                  f"{stats['events_failed']} failed, {stats['events_retried']} retried")
        
        # Stop event bus
        bus.stop(wait=True)
        
    else:
        # Sequential processing (original logic)
        if args.parallel and not EVENT_BUS_AVAILABLE:
            print(f"  [WARN] Event bus not available, falling back to sequential processing")
        
        for i, job in enumerate(jobs, 1):
            if args.verbose:
                print(f"\n[{i}/{len(jobs)}] {job.asset_id}")
                # Show current model state
                loaded = get_loaded_models()
                if loaded:
                    print(f"    [INFO] Loaded models: {', '.join(loaded)}")

            job_result = {"asset_id": job.asset_id, "draft": str(job.draft_path), "exports": []}

            # Save per-asset job spec to allow later re-runs without Ollama.
            job_spec_path = draft_dir / f"{job.asset_id}.job.json"
            _write_json(
                job_spec_path,
                {
                    "asset_id": job.asset_id,
                    "sd35": {
                        "prompt": job.sd35.prompt,
                        "negative_prompt": job.sd35.negative_prompt,
                        "width": job.sd35.width,
                        "height": job.sd35.height,
                        "steps": job.sd35.steps,
                        "guidance_scale": job.sd35.guidance_scale,
                        "seed": job.sd35.seed,
                        "enhance_with_ollama": job.sd35.enhance_with_ollama,
                        "auto_start_server": job.sd35.auto_start_server,
                    },
                    "draft_path": str(job.draft_path),
                    "exports": [{"path": str(p), "size": list(sz)} for p, sz in job.export_paths],
                    "meta": job.meta,
                },
            )

            # Generate SD3.5 draft
            if not args.skip_sd35:
                if not job.sd35.prompt:
                    if args.verbose:
                        print(f"    [WARN] Missing SD3.5 prompt for {job.asset_id}")
                else:
                    success = _run_sd35_generate_single(
                        sd_module_path=sd_module_path,
                        params=job.sd35,
                        output_path=job.draft_path,
                        verbose=args.verbose,
                        cache=cache,
                    )
                    if success:
                        results["drafts_created"] += 1
                    else:
                        results["drafts_skipped"] += 1

            # Export final assets
            if not args.skip_export:
                for out_path, size in job.export_paths:
                    ok = _export_from_draft(
                        job.draft_path,
                        out_path,
                        size,
                        truecolor=bool(job.meta.get("truecolor", False)),
                    )
                    job_result["exports"].append({"path": str(out_path), "size": list(size), "ok": ok})
                    if ok:
                        results["exports_created"] += 1
                        if not args.no_postprocess:
                            _run_imagemagick_postprocess_qud(shared_dir=shared_dir, image_path=out_path)
                        if args.verbose:
                            print(f"    [OK] Exported: {out_path.name} ({size[0]}x{size[1]})")

            results["jobs"].append(job_result)

    # Preview: curated SD scene (ants vs corpse) wins over legacy tile collage.
    if not args.skip_export:
        preview_path = mod_path / "preview.png"
        sd_preview_draft = draft_dir / "workshop_preview_design_draft.png"
        if "preview" in CURATED_PROMPT_SEEDS and preview_path.exists() and preview_path.stat().st_size > 1000:
            print("\n=== Workshop Preview ===")
            print("  [OK] Keeping curated SD workshop preview (skip tile collage overwrite)")
        elif "preview" in CURATED_PROMPT_SEEDS and sd_preview_draft.exists() and sd_preview_draft.stat().st_size > 1000:
            print("\n=== Workshop Preview ===")
            print("  [INFO] Exporting curated SD draft to preview.png (skip tile collage)")
            if _export_from_draft(sd_preview_draft, preview_path, (512, 512), truecolor=True):
                results["exports_created"] += 1
        else:
            print("\n=== Composing Preview Image ===")
            icon_path = mod_path / "Textures" / "Broodmother_icon.png"
            sack_path = mod_path / "Textures" / "Equipment" / "Broodling_Sack_tile.png"
            creature_paths = [
                mod_path / "Textures" / "Creatures" / "sw_broodling_ground.png",
                mod_path / "Textures" / "Creatures" / "sw_broodling_flying.png",
                mod_path / "Textures" / "Creatures" / "BroodlingCrystal_T4.png",
                mod_path / "Textures" / "Creatures" / "BroodlingPhantom_T5.png",
                mod_path / "Textures" / "Creatures" / "BroodlingBombardier_T4.png",
                mod_path / "Textures" / "Creatures" / "BroodlingSymbiote_T3.png",
                mod_path / "Textures" / "Creatures" / "BroodlingVoidling_T6.png",
                mod_path / "Textures" / "Creatures" / "BroodlingNecroling_T6.png",
            ]
            if _compose_preview_image(
                mod_path, icon_path, sack_path, creature_paths, preview_path, verbose=args.verbose
            ):
                results["exports_created"] += 1

    # Generate optional audio
    if args.generate_audio:
        print(f"\n=== Generating Audio Assets ===")
        sounds_path = mod_path / "Sounds"
        results["sounds_created"] = _generate_broodmother_audio(mod_path, sounds_path, verbose=args.verbose)

    _write_json(draft_dir / "generation_summary.json", results)
    elapsed = time.time() - start

    # Bridge Textures/ into Assets/Resources + Unity .meta (no Editor required).
    # Matching Unity 6000.0.77f1 can then build AssetBundles via QudUnityAssetGenerator.
    if not args.skip_export and results.get("exports_created", 0) > 0:
        try:
            from export_textures_to_unity import export_textures
            print("\n=== Unity texture export (.meta) ===")
            export_textures(mod_path, overwrite_meta=False)
        except Exception as exc:
            print(f"[WARN] Unity texture bridge skipped: {exc}")

    print("\n" + "=" * 60)
    print("=== Broodmother SD3.5 Draft Pipeline Complete ===")
    print("=" * 60)
    print(f"Quality mode: {results.get('quality_mode', args.quality_mode)}")
    print(f"Drafts created: {results['drafts_created']}")
    if results.get("drafts_skipped", 0) > 0:
        print(f"Drafts skipped: {results['drafts_skipped']} (SD3.5 unavailable)")
    if results.get("reviews", 0) > 0:
        print(f"Reviews: {results['reviews']}")
    if results.get("retries", 0) > 0:
        print(f"SD retries (corrections applied): {results['retries']}")
    print(f"Exports created: {results['exports_created']}")
    if results.get("sounds_created", 0) > 0:
        print(f"Audio created: {results['sounds_created']}")
    print(f"Elapsed: {elapsed:.1f}s")
    print(f"Drafts/specs: {draft_dir}")
    qreport = draft_dir / "quality_loop_report.json"
    if qreport.exists():
        print(f"Quality report: {qreport}")
    if args.verbose:
        print(f"\n[INFO] PNG tile assets support UNLIMITED colors in Caves of Qud.")
        print(f"[INFO] Ensure XML blueprints use <Tile> rendering (not <Color>/<DetailColor>) to enable full color support.")
    
    # Cache statistics
    if cache is not None and args.verbose:
        cache_stats = cache.get_stats()
        print(f"\n=== Cache Statistics ===")
        print(f"Hits: {cache_stats['hits']}, Misses: {cache_stats['misses']}")
        if cache_stats['hits'] + cache_stats['misses'] > 0:
            hit_rate = cache_stats['hits'] / (cache_stats['hits'] + cache_stats['misses']) * 100
            print(f"Hit rate: {hit_rate:.1f}%")
        print(f"Evictions: {cache_stats['evictions']}")
        if cache_stats.get('disk_cache_files', 0) > 0:
            print(f"Disk cache files: {cache_stats['disk_cache_files']}")
    
    # Optional: Unload models to free VRAM
    if args.unload_models:
        print(f"\n=== Unloading Models ===")
        unloaded_count = unload_all_models(verbose=args.verbose)
        if args.verbose:
            print(f"  Freed VRAM by unloading {unloaded_count} model(s)")
    elif args.verbose:
        loaded = get_loaded_models()
        if loaded:
            print(f"\n[INFO] Models still loaded: {', '.join(loaded)}")
            print("[INFO] Use --unload-models to free VRAM after generation")
    
    print("=" * 60)
    return 0

def _cli_main() -> int:
    try:
        return main()
    except KeyboardInterrupt:
        print("\nCancelled.")
        return 130
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(_cli_main())
