#!/usr/bin/env python3
"""
Quality pipeline for Space-Time Vortex asset generation.

- Robust Ollama JSON parsing with repair + disk cache
- SD3 design-draft palette sampling for color consistency
- Unified master art direction across all assets
- Sprite finalize: sharpen, contrast, alpha cleanup (Qud-ready PNGs)
- Animation temporal smoothing + validation gates
- Optional ImageMagick post-process (Tools/Shared)
"""

from __future__ import annotations

import json
import math
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from PIL import Image, ImageChops, ImageEnhance, ImageFilter, ImageStat

# Shared cache (optional)
_shared_dir = Path(__file__).resolve().parent.parent / "Shared"
if str(_shared_dir) not in sys.path:
    sys.path.insert(0, str(_shared_dir))

try:
    from cache_manager import get_cache, CacheManager  # type: ignore
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False
    CacheManager = None  # type: ignore
    get_cache = None  # type: ignore

QUD_ART_SYSTEM = (
    "You are a senior art director for Caves of Qud, a roguelike with organic biotech "
    "and surreal sci-fi aesthetics. Design cohesive pixel-art color palettes for "
    "space-time distortion effects. Return ONLY valid JSON — no markdown, no commentary."
)

DRAFT_MAP = {
    "icon": "icon_design_draft.png",
    "black_hole": "black_hole_design_draft.png",
    "white_hole": "white_hole_design_draft.png",
}


def parse_ollama_json(response: str, asset_type: str = "asset") -> Dict[str, Any]:
    """Extract and parse JSON from an Ollama response, with light repair."""
    if not response or not response.strip():
        raise ValueError(f"Empty Ollama response for {asset_type}")

    text = response.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL | re.IGNORECASE)
    if fence:
        text = fence.group(1)
    else:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start < 0 or end <= start:
            raise ValueError(f"No JSON object in Ollama response for {asset_type}")
        text = text[start:end]

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        repaired = re.sub(r",\s*}", "}", text)
        repaired = re.sub(r",\s*]", "]", repaired)
        repaired = re.sub(r"(\w+)\s*:", r'"\1":', repaired)
        repaired = re.sub(r'""(\w+)"":', r'"\1":', repaired)
        return json.loads(repaired)


def repair_ollama_json(
    broken: str,
    asset_type: str,
    call_ollama: Callable[..., str],
) -> Dict[str, Any]:
    """Ask Ollama to fix malformed JSON."""
    fix_prompt = (
        f"Fix this broken JSON for a {asset_type} design spec. Return ONLY the corrected JSON object:\n\n"
        f"{broken[:4000]}"
    )
    fixed = call_ollama(
        prompt=fix_prompt,
        task_type="code",
        response_length="standard",
        system_prompt="Return valid JSON only. No markdown.",
        model_name=None,
    )
    return parse_ollama_json(fixed, asset_type)


def call_ollama_design_cached(
    call_ollama: Callable[..., str],
    prompt: str,
    asset_type: str,
    task_type: str = "analysis",
    cache: Optional[Any] = None,
    use_cache: bool = True,
    max_retries: int = 2,
) -> Dict[str, Any]:
    """Call Ollama for design JSON with cache + retries + repair."""
    if use_cache and cache is not None:
        cached = cache.get(
            "vortex_ollama_json",
            prompt=prompt,
            task_type=task_type,
            asset_type=asset_type,
            ttl=86400 * 7,
            use_disk=True,
        )
        if cached is not None:
            print(f"  [CACHE] Using cached design for {asset_type}")
            return cached

    last_error = None
    for attempt in range(max_retries):
        try:
            if attempt:
                print(f"    (retry {attempt + 1}/{max_retries})")
            response = call_ollama(
                prompt=prompt,
                task_type=task_type,
                response_length="standard",
                system_prompt=QUD_ART_SYSTEM,
                model_name=None,
            )
            design = parse_ollama_json(response, asset_type)
            if use_cache and cache is not None:
                cache.set(
                    "vortex_ollama_json",
                    value=design,
                    prompt=prompt,
                    task_type=task_type,
                    asset_type=asset_type,
                    use_disk=True,
                )
            return design
        except (ValueError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt < max_retries - 1 and response:
                try:
                    return repair_ollama_json(response, asset_type, call_ollama)
                except Exception:
                    continue
    raise ValueError(f"Failed to get valid JSON for {asset_type}: {last_error}")


def _rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def sample_draft_palette(draft_path: Path, sample_count: int = 12) -> List[str]:
    """Extract dominant hex colors from an SD3 design draft PNG."""
    if not draft_path.exists():
        return []
    try:
        with Image.open(draft_path) as img:
            img = img.convert("RGBA").resize((64, 64), Image.Resampling.LANCZOS)
            pixels = [
                p[:3]
                for p in img.getdata()
                if len(p) >= 4 and p[3] > 40
            ]
        if not pixels:
            return []
        # Quantize to reduce noise
        quantized = Counter(
            (r // 16 * 16, g // 16 * 16, b // 16 * 16) for r, g, b in pixels
        )
        top = [rgb for rgb, _ in quantized.most_common(sample_count)]
        return [_rgb_to_hex(c) for c in top]
    except Exception:
        return []


def merge_draft_palette(design: Dict[str, Any], draft_colors: List[str], weight: float = 0.35) -> Dict[str, Any]:
    """Blend draft palette colors into an AI design's colorScheme."""
    if not draft_colors:
        return design
    cs = dict(design.get("colorScheme") or {})
    keys = list(cs.keys())
    for i, key in enumerate(keys):
        if i < len(draft_colors):
            cs[key] = draft_colors[i]
    design = dict(design)
    design["colorScheme"] = cs
    design["_draftInfluence"] = round(weight, 2)
    return design


def merge_master_palette(design: Dict[str, Any], master: Dict[str, Any]) -> Dict[str, Any]:
    """Apply unified art-direction palette keys where compatible."""
    if not master:
        return design
    master_cs = master.get("colorScheme") or master.get("palette") or {}
    if not master_cs:
        return design
    cs = dict(design.get("colorScheme") or {})
    theme = master.get("theme", {})
    # Map semantic roles
    role_map = {
        "void": master_cs.get("void") or master_cs.get("dark"),
        "primary": master_cs.get("primary") or master_cs.get("vortex"),
        "glow": master_cs.get("glow") or master_cs.get("accent"),
        "outline": master_cs.get("outline") or master_cs.get("edge"),
        "secondary": master_cs.get("secondary"),
        "center": master_cs.get("bright") or master_cs.get("rupture"),
        "core": master_cs.get("core") or master_cs.get("bright"),
        "rays": master_cs.get("rays") or master_cs.get("accent"),
        "eventHorizon": master_cs.get("horizon") or master_cs.get("dark"),
        "accretionDisk": master_cs.get("disk") or master_cs.get("primary"),
    }
    for key, value in role_map.items():
        if value and key in cs:
            cs[key] = value
    design = dict(design)
    design["colorScheme"] = cs
    if theme:
        design["theme"] = {**(design.get("theme") or {}), **theme}
    return design


def finalize_qud_sprite(
    img: Image.Image,
    target_size: Optional[Tuple[int, int]] = None,
    sharpen: float = 1.32,
    contrast: float = 1.10,
    saturation: float = 1.06,
) -> Image.Image:
    """Downscale + polish for crisp Qud tile sprites."""
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    # Gentle pre-blur at supersampled res, then downscale
    img = img.filter(ImageFilter.GaussianBlur(radius=0.6))

    if target_size and img.size != target_size:
        img = img.resize(target_size, Image.Resampling.LANCZOS)

    # Clean fringe alpha
    r, g, b, a = img.split()
    a = a.point(lambda p: 0 if p < 8 else (255 if p > 248 else p))
    img = Image.merge("RGBA", (r, g, b, a))

    img = ImageEnhance.Sharpness(img).enhance(sharpen)
    img = ImageEnhance.Contrast(img).enhance(contrast)
    img = ImageEnhance.Color(img).enhance(saturation)
    return img


def compute_edge_density(img: Image.Image) -> float:
    """Fraction of pixels with strong edges — rejects flat geometric fills."""
    gray = img.convert("RGB").convert("L")
    edges = gray.filter(ImageFilter.FIND_EDGES)
    data = list(edges.getdata())
    if not data:
        return 0.0
    strong = sum(1 for p in data if p > 28)
    return strong / len(data)


def validate_sprite_quality(
    img: Image.Image,
    min_nontransparent_ratio: float = 0.04,
    min_luma_variance: float = 120.0,
    min_edge_density: float = 0.0,
) -> Tuple[bool, str]:
    """Reject empty, flat, or nearly invisible sprites."""
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    w, h = img.size
    if w < 4 or h < 4:
        return False, f"too small ({w}x{h})"

    alpha = img.split()[3]
    opaque = sum(1 for p in alpha.getdata() if p > 16)
    ratio = opaque / max(1, w * h)
    if ratio < min_nontransparent_ratio:
        return False, f"too transparent ({ratio:.1%} coverage)"

    rgb = img.convert("RGB")
    luma = rgb.convert("L")
    lstat = ImageStat.Stat(luma)
    if lstat.var[0] < min_luma_variance:
        return False, f"too flat (variance {lstat.var[0]:.1f})"

    if min_edge_density > 0:
        edge = compute_edge_density(img)
        if edge < min_edge_density:
            return False, f"too simple (edge density {edge:.3f} < {min_edge_density:.3f})"

    return True, "ok"


def smooth_animation_frames(frames: List[Image.Image], blend: float = 0.12) -> List[Image.Image]:
    """Light temporal blend so adjacent frames don't pop."""
    if len(frames) < 2 or blend <= 0:
        return frames
    out = [frames[0]]
    for i in range(1, len(frames)):
        prev = frames[i - 1].convert("RGBA")
        curr = frames[i].convert("RGBA")
        mixed = ImageChops.blend(prev, curr, blend)
        out.append(mixed)
    out[0] = frames[0]
    return out


def run_imagemagick_qud(shared_dir: Path, image_path: Path) -> bool:
    """Optional ImageMagick polish via Shared module."""
    module = shared_dir / "ImageMagickPostProcessor.psm1"
    if not module.exists() or not image_path.exists():
        return False
    escaped = str(image_path).replace("'", "''")
    ps = (
        f"Import-Module '{module}' -ErrorAction SilentlyContinue; "
        f"Process-AIGeneratedImage -InputPath '{escaped}' -OutputPath '{escaped}' "
        f"-GameType 'Qud' -Quality 'high'"
    )
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
            check=False,
            capture_output=True,
            timeout=60,
        )
        return True
    except Exception:
        return False


def save_qud_sprite(
    img: Image.Image,
    path: Path,
    target_size: Optional[Tuple[int, int]] = None,
    shared_dir: Optional[Path] = None,
    use_imagemagick: bool = True,
    validate: bool = True,
    strict_quality: bool = False,
    min_edge_density: float = 0.0,
) -> bool:
    """Finalize, validate, save PNG. Returns False when strict_quality rejects output."""
    path.parent.mkdir(parents=True, exist_ok=True)
    final = finalize_qud_sprite(img, target_size=target_size)
    if validate:
        edge_gate = min_edge_density
        if edge_gate <= 0 and max(final.size) <= 32:
            edge_gate = 0.045
        elif edge_gate <= 0 and max(final.size) <= 96:
            edge_gate = 0.035
        ok, reason = validate_sprite_quality(final, min_edge_density=edge_gate)
        if not ok:
            print(f"    [QUALITY WARN] {path.name}: {reason}")
            if strict_quality:
                return False
    final.save(path, "PNG", optimize=True)
    if use_imagemagick and shared_dir:
        run_imagemagick_qud(shared_dir, path)
    return path.exists() and path.stat().st_size > 0


MASTER_ART_PROMPT = """Create a UNIFIED art direction for the Space-Time Vortex mutation in Caves of Qud.
Return ONLY valid JSON:
{
  "theme": {
    "mood": "surreal dimensional horror",
    "style": "organic biotech meets cosmic distortion",
    "contrast": "dark singularity vs blinding rupture"
  },
  "colorScheme": {
    "primary": "#4a6ab8",
    "secondary": "#7b5aa0",
    "accent": "#40c0d0",
    "glow": "#6090e0",
    "dark": "#080818",
    "horizon": "#1a2850",
    "disk": "#304878",
    "edge": "#203050",
    "bright": "#fff8e8",
    "rupture": "#ffd060",
    "void": "#000008"
  },
  "notes": "Mental mutation — impossible colors, not realistic astrophysics"
}"""

BATCH_PARTICLE_PROMPT = """Design ALL particle sprites for Space-Time Vortex in ONE cohesive set.
Return ONLY valid JSON with this exact structure:
{
  "particles": {
    "spark_blue": {"colorScheme": {"primary": "#4080c0", "glow": "#60a0e0", "outline": "#204060"}},
    "spark_cyan": {"colorScheme": {"primary": "#40c0d0", "glow": "#80e0f0", "outline": "#206060"}},
    "swirl_blue": {"colorScheme": {"primary": "#5080c8", "glow": "#70a8e8", "outline": "#284868"}},
    "swirl_white": {"colorScheme": {"primary": "#c0d8f0", "glow": "#e8f4ff", "outline": "#8098b0"}},
    "dot_yellow": {"colorScheme": {"primary": "#ffd040", "glow": "#ffe880", "outline": "#b08000"}},
    "dot_orange": {"colorScheme": {"primary": "#ff9040", "glow": "#ffb060", "outline": "#b04000"}}
  }
}
Vortex particles use blue/cyan; rupture particles use yellow/orange. Return JSON ONLY."""


class VortexQualityPipeline:
    """Orchestrates design consistency and export quality."""

    def __init__(
        self,
        mod_path: Path,
        shared_dir: Optional[Path] = None,
        use_cache: bool = True,
        use_drafts: bool = True,
        quality: str = "full",
    ):
        self.mod_path = Path(mod_path)
        self.shared_dir = shared_dir or (_shared_dir)
        self.use_cache = use_cache and CACHE_AVAILABLE
        self.use_drafts = use_drafts
        self.quality = quality
        self.drafts_dir = self.mod_path / "DesignDrafts"
        self.specs_dir = self.mod_path / "DesignSpecs"
        self.specs_dir.mkdir(exist_ok=True)
        self.cache = (
            get_cache(
                cache_dir=self.specs_dir / ".cache",
                enable_disk_cache=True,
                verbose=False,
            )
            if self.use_cache and get_cache
            else None
        )
        self._master: Optional[Dict[str, Any]] = None

    def get_master_art_direction(self, call_ollama: Callable[..., str]) -> Dict[str, Any]:
        if self._master:
            return self._master
        spec_path = self.specs_dir / "master_art_direction.json"
        if spec_path.exists():
            try:
                self._master = json.loads(spec_path.read_text(encoding="utf-8"))
                print("  [OK] Loaded cached master art direction")
                return self._master
            except Exception:
                pass
        print("  Getting unified master art direction (1 Ollama call)...")
        self._master = call_ollama_design_cached(
            call_ollama, MASTER_ART_PROMPT, "master art direction", "visual", self.cache, self.use_cache
        )
        spec_path.write_text(json.dumps(self._master, indent=2), encoding="utf-8")
        return self._master

    def get_design(
        self,
        call_ollama: Callable[..., str],
        prompt: str,
        asset_type: str,
        task_type: str = "analysis",
        draft_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        design = call_ollama_design_cached(
            call_ollama, prompt, asset_type, task_type, self.cache, self.use_cache
        )
        if self._master:
            design = merge_master_palette(design, self._master)
        if self.use_drafts and draft_key:
            draft_file = self.drafts_dir / DRAFT_MAP.get(draft_key, "")
            colors = sample_draft_palette(draft_file)
            design = merge_draft_palette(design, colors)
        return design

    def get_batch_particle_designs(self, call_ollama: Callable[..., str]) -> Dict[Tuple[str, str], Dict]:
        """One Ollama call for all 6 particle types."""
        spec_path = self.specs_dir / "particle_designs.json"
        if spec_path.exists() and not self.use_cache:
            pass
        elif spec_path.exists():
            try:
                data = json.loads(spec_path.read_text(encoding="utf-8"))
                particles = data.get("particles", data)
                result = {}
                for key, design in particles.items():
                    parts = key.split("_", 1)
                    if len(parts) == 2:
                        result[(parts[0], parts[1])] = design
                if len(result) >= 6:
                    print("  [OK] Loaded cached batch particle designs")
                    return result
            except Exception:
                pass

        print("  Getting batch particle designs (1 Ollama call for all 6 types)...")
        batch = call_ollama_design_cached(
            call_ollama, BATCH_PARTICLE_PROMPT, "particle batch", "visual", self.cache, self.use_cache
        )
        particles = batch.get("particles", batch)
        result = {}
        for key, design in particles.items():
            parts = key.split("_", 1)
            if len(parts) == 2:
                d = dict(design)
                if self._master:
                    d = merge_master_palette(d, self._master)
                result[(parts[0], parts[1])] = d
        spec_path.write_text(json.dumps({"particles": particles}, indent=2), encoding="utf-8")
        return result

    def save_design_specs(self, specs: Dict[str, Any]) -> None:
        path = self.specs_dir / "vortex_designs.json"
        path.write_text(json.dumps(specs, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  [OK] Design specs saved: {path.name}")

    def export_sprite(self, img: Image.Image, path: Path, size: Optional[Tuple[int, int]] = None) -> bool:
        use_im = self.quality in ("full", "mechanical")
        return save_qud_sprite(
            img,
            path,
            target_size=size,
            shared_dir=self.shared_dir if use_im else None,
            use_imagemagick=use_im,
            validate=self.quality != "fast",
            strict_quality=self.quality == "full",
        )

    def export_animation(
        self,
        frames: List[Image.Image],
        path_template: str,
        size: Tuple[int, int],
        smooth: bool = True,
    ) -> int:
        if smooth and self.quality == "full":
            frames = smooth_animation_frames(frames, blend=0.10)
        saved = 0
        for i, frame in enumerate(frames):
            path = Path(path_template.format(i=i))
            if self.export_sprite(frame, path, size=size):
                saved += 1
        return saved
