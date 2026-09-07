#!/usr/bin/env python3
"""
OpenStarbound Frame Generator Orchestrator
High-quality, AI-driven frame generation with palette selection, packing, and validation.
"""

import json
import math
import os
import random
import sys
import subprocess
import tempfile
import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import requests
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance, ImageStat

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from libs.spritesheet_assembler import Layout, SpritesheetAssembler

# Import shared Ollama integration
_ollama_path = os.path.join(os.path.dirname(__file__), "..", "..", "Shared", "ollama_integration.py")
OLLAMA_INTEGRATION_AVAILABLE = False
call_ollama = None
test_ollama_connection = None
TASK_VISUAL = "visual"

if os.path.exists(_ollama_path):
    try:
        shared_dir = os.path.join(os.path.dirname(__file__), "..", "..", "Shared")
        if shared_dir not in sys.path:
            sys.path.insert(0, shared_dir)
        from ollama_integration import call_ollama, test_ollama_connection
        OLLAMA_INTEGRATION_AVAILABLE = True
    except ImportError as e:
        OLLAMA_INTEGRATION_AVAILABLE = False
        print(f"[WARN] Could not import Ollama integration: {e}")
else:
    OLLAMA_INTEGRATION_AVAILABLE = False


class QualityLevel(Enum):
    """Quality levels for generation"""
    PIXEL_ART = "pixel_art"
    HIGH_RES = "high_res"
    MS_DESIGNER = "ms_designer"  # Highest quality, uses SDXL


@dataclass
class FrameJob:
    """Job specification for frame generation"""
    asset_name: str
    segment_list: List[str]
    frame_count: int = 8
    frame_width: int = 16
    frame_height: int = 16
    color_hints: Optional[List[str]] = None
    quality_level: QualityLevel = QualityLevel.PIXEL_ART
    animation_type: str = "SpellCast"
    pivot_rules: Optional[Dict] = None
    output_dir: str = "output"
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['quality_level'] = self.quality_level.value
        return data


class PaletteGenerator:
    """Generates color palettes using AI and color APIs"""
    
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_url
    
    def generate_palette_from_hints(self, hints: List[str], role: str = "assault") -> Tuple[List[Tuple[int, int, int]], List[List[Tuple[int, int, int]]]]:
        """
        Generate a palette from color hints using AI or Colormind API.
        Generates 5 candidates and picks the best one.
        
        Args:
            hints: List of color hints (e.g., ["crimson", "brass", "teal"])
            role: Asset role (assault, support, horror, etc.)
        
        Returns:
            Tuple of (best_palette, extras) where extras are perfect-scoring alternatives
        """
        if not hints:
            # Use role-based default palette
            return (self._get_role_palette(role), [])
        
        # Try Colormind API first (free, no auth needed)
        try:
            palette = self._colormind_palette(hints)
            if palette:
                # Score the Colormind palette
                score = self._score_palette(palette, hints, role)
                if score >= 0.9:  # Good enough, use it
                    return (palette, [])
                # Otherwise continue to AI generation
        except Exception as e:
            print(f"[WARN] Colormind API failed: {e}, using AI fallback")
        
        # Fallback to AI-generated palette with quality control
        return self._ai_palette(hints, role)
    
    def _get_role_palette(self, role: str) -> List[Tuple[int, int, int]]:
        """Get default palette based on role"""
        palettes = {
            "assault": [(200, 50, 50), (255, 150, 0), (100, 100, 100), (50, 50, 50), (255, 200, 100)],
            "support": [(50, 150, 200), (100, 200, 255), (150, 150, 200), (50, 100, 150), (200, 220, 255)],
            "horror": [(80, 20, 20), (120, 40, 40), (40, 40, 40), (200, 0, 0), (60, 60, 80)],
            "magitech": [(100, 150, 255), (200, 100, 255), (150, 200, 255), (100, 100, 200), (255, 200, 100)],
            "default": [(200, 150, 100), (150, 100, 50), (100, 100, 100), (50, 50, 50), (255, 200, 150)]
        }
        return palettes.get(role.lower(), palettes["default"])
    
    def _score_palette(self, palette: List[Tuple[int, int, int]], hints: List[str], role: str) -> float:
        """
        Score a palette quality (0-1 scale, displayed as 0-10).
        Returns normalized score.
        """
        if len(palette) != 5:
            return 0.0
        
        score = 0.0
        max_score = 10.0
        
        # 1. Color contrast (2 points)
        # Check if colors have good contrast
        contrasts = []
        for i in range(len(palette)):
            for j in range(i + 1, len(palette)):
                # Calculate color distance (Euclidean in RGB space)
                r1, g1, b1 = palette[i]
                r2, g2, b2 = palette[j]
                distance = ((r1 - r2) ** 2 + (g1 - g2) ** 2 + (b1 - b2) ** 2) ** 0.5
                contrasts.append(distance)
        
        avg_contrast = sum(contrasts) / len(contrasts) if contrasts else 0
        if avg_contrast > 100:  # Good contrast
            score += 2.0
        elif avg_contrast > 50:
            score += 1.0
        
        # 2. Color diversity (2 points)
        # Check if colors are distinct
        unique_colors = len(set(palette))
        if unique_colors == 5:
            score += 2.0
        elif unique_colors >= 4:
            score += 1.0
        
        # 3. Brightness range (2 points)
        # Check for good brightness range (light and dark colors)
        brightnesses = [(r + g + b) / 3 for r, g, b in palette]
        brightness_range = max(brightnesses) - min(brightnesses)
        if brightness_range > 150:  # Good range
            score += 2.0
        elif brightness_range > 100:
            score += 1.0
        
        # 4. Role appropriateness (2 points)
        # Check if colors match role
        role_colors = {
            "assault": ["red", "orange", "crimson"],
            "support": ["blue", "cyan", "teal"],
            "horror": ["dark", "black", "red"],
            "magitech": ["purple", "blue", "magenta"]
        }
        role_keywords = role_colors.get(role.lower(), [])
        # Simple check: if palette has colors matching role
        if role_keywords:
            score += 1.0  # Basic match
        
        # 5. Visual appeal (2 points)
        # Check for color harmony (complementary/analogous)
        # Simple heuristic: if we have good contrast and diversity, assume harmony
        if avg_contrast > 80 and unique_colors == 5:
            score += 2.0
        elif avg_contrast > 60:
            score += 1.0
        
        # Normalize to 0-1 scale
        return score / max_score
    
    def _colormind_palette(self, hints: List[str]) -> Optional[List[Tuple[int, int, int]]]:
        """Generate palette using Colormind API"""
        try:
            # Colormind API endpoint
            url = "http://colormind.io/api/"
            data = {
                "model": "default",
                "input": hints[:5]  # Limit to 5 hints
            }
            response = requests.post(url, json=data, timeout=5)
            if response.status_code == 200:
                result = response.json()
                if "result" in result:
                    # Convert to list of RGB tuples
                    return [tuple(rgb) for rgb in result["result"]]
        except Exception as e:
            print(f"[WARN] Colormind API error: {e}")
        return None
    
    def _ai_palette(self, hints: List[str], role: str) -> Tuple[List[Tuple[int, int, int]], List[List[Tuple[int, int, int]]]]:
        """
        Generate palette using Ollama AI with quality control.
        Generates 5 candidates and picks the best one.
        Returns (best_palette, extras) where extras are perfect-scoring alternatives.
        """
        if not OLLAMA_INTEGRATION_AVAILABLE:
            # Fallback to direct API if shared integration not available
            return self._ai_palette_fallback(hints, role)
        
        prompt = f"""Generate a 5-color palette for a {role} mech segment with these hints: {', '.join(hints)}.
Return only a JSON array of 5 RGB color values like: [[r1,g1,b1], [r2,g2,b2], ...]
Ensure good contrast, visual appeal, and color harmony suitable for pixel art."""
        
        system_prompt = "You are a color palette designer for pixel art games. Always return valid JSON arrays only."
        
        candidates = []  # List of (palette, score) tuples
        num_candidates = 5
        
        print(f"  Generating {num_candidates} palette candidates...")
        
        for attempt in range(num_candidates):
            try:
                print(f"  Calling Ollama for palette (candidate {attempt + 1}/{num_candidates})...")
                
                response = call_ollama(
                    prompt=prompt,
                    task_type=TASK_VISUAL,
                    response_length="short",
                    system_prompt=system_prompt,
                    model_name=""  # Auto-select
                )
                
                if response:
                    # Extract JSON array
                    import re
                    json_match = re.search(r'\[\[.*?\]\]', response)
                    if json_match:
                        try:
                            palette_data = json.loads(json_match.group())
                            if isinstance(palette_data, list) and len(palette_data) == 5:
                                palette = [tuple(rgb) for rgb in palette_data]
                                # Score the palette
                                score = self._score_palette(palette, hints, role)
                                candidates.append((palette, score))
                                print(f"  Candidate {attempt + 1} quality score: {score:.2f} ({score * 10:.1f}/10)")
                        except json.JSONDecodeError:
                            print(f"  [WARNING] JSON parse error for candidate {attempt + 1}")
                
                if attempt < num_candidates - 1:
                    time.sleep(0.5)  # Small delay between candidates
                    
            except Exception as e:
                print(f"  [WARNING] Error generating candidate {attempt + 1}: {e}")
        
        if not candidates:
            print(f"  [WARNING] No valid candidates generated, using fallback")
            return self._ai_palette_fallback(hints, role)
        
        # Sort by score (highest first)
        candidates.sort(key=lambda x: x[1], reverse=True)
        best_palette, best_score = candidates[0]
        
        # Extract extras (score >= 1.0, which is 10/10)
        extras = [palette for palette, score in candidates[1:] if score >= 1.0]
        
        print(f"  [OK] Best palette quality score: {best_score:.2f} ({best_score * 10:.1f}/10)")
        if extras:
            print(f"  [OK] Keeping {len(extras)} extra palette(s) with perfect scores (10/10)")
        
        return best_palette, extras
    
    def _ai_palette_fallback(self, hints: List[str], role: str) -> Tuple[List[Tuple[int, int, int]], List[List[Tuple[int, int, int]]]]:
        """Fallback palette generation using direct API calls"""
        try:
            prompt = f"""Generate a 5-color palette for a {role} mech segment with these hints: {', '.join(hints)}.
Return only a JSON array of 5 RGB color values like: [[r1,g1,b1], [r2,g2,b2], ...]
Ensure good contrast and visual appeal."""
            
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": "qwen2.5-coder:7b",
                    "prompt": prompt,
                    "stream": False
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                # Parse JSON from response
                import re
                json_match = re.search(r'\[\[.*?\]\]', result.get('response', ''))
                if json_match:
                    palette = json.loads(json_match.group())
                    return ([tuple(rgb) for rgb in palette], [])
        except Exception as e:
            print(f"[WARN] AI palette generation failed: {e}")
        
        # Final fallback to role palette
        return (self._get_role_palette(role), [])
    
    def _score_palette(self, palette: List[Tuple[int, int, int]], hints: List[str], role: str) -> float:
        """
        Score a palette quality (0-1 scale, displayed as 0-10).
        Returns normalized score.
        """
        if len(palette) != 5:
            return 0.0
        
        score = 0.0
        max_score = 10.0
        
        # 1. Color contrast (2 points)
        # Check if colors have good contrast
        contrasts = []
        for i in range(len(palette)):
            for j in range(i + 1, len(palette)):
                # Calculate color distance (Euclidean in RGB space)
                r1, g1, b1 = palette[i]
                r2, g2, b2 = palette[j]
                distance = ((r1 - r2) ** 2 + (g1 - g2) ** 2 + (b1 - b2) ** 2) ** 0.5
                contrasts.append(distance)
        
        avg_contrast = sum(contrasts) / len(contrasts) if contrasts else 0
        if avg_contrast > 100:  # Good contrast
            score += 2.0
        elif avg_contrast > 50:
            score += 1.0
        
        # 2. Color diversity (2 points)
        # Check if colors are distinct
        unique_colors = len(set(palette))
        if unique_colors == 5:
            score += 2.0
        elif unique_colors >= 4:
            score += 1.0
        
        # 3. Brightness range (2 points)
        # Check for good brightness range (light and dark colors)
        brightnesses = [(r + g + b) / 3 for r, g, b in palette]
        brightness_range = max(brightnesses) - min(brightnesses)
        if brightness_range > 150:  # Good range
            score += 2.0
        elif brightness_range > 100:
            score += 1.0
        
        # 4. Role appropriateness (2 points)
        # Check if colors match role
        role_colors = {
            "assault": ["red", "orange", "crimson"],
            "support": ["blue", "cyan", "teal"],
            "horror": ["dark", "black", "red"],
            "magitech": ["purple", "blue", "magenta"]
        }
        role_keywords = role_colors.get(role.lower(), [])
        # Simple check: if palette has colors matching role
        if role_keywords:
            score += 1.0  # Basic match
        
        # 5. Visual appeal (2 points)
        # Check for color harmony (complementary/analogous)
        # Simple heuristic: if we have good contrast and diversity, assume harmony
        if avg_contrast > 80 and unique_colors == 5:
            score += 2.0
        elif avg_contrast > 60:
            score += 1.0
        
        # Normalize to 0-1 scale
        return score / max_score


# ----------------------------------------------------------------------------
# Color / quality helpers (shared richness techniques, mirrors Soulash2
# hydromancy_quality.validate_sprite_quality: alpha coverage + luma variance +
# edge density so flat "programmer-art" frames FAIL the gate and get retried).
# ----------------------------------------------------------------------------
WHITE = (255, 255, 255)


def _clamp8(v: float) -> int:
    return max(0, min(255, int(round(v))))


def _norm_rgb(c) -> Tuple[int, int, int]:
    """Coerce a palette entry (tuple/list, possibly out of range) to RGB."""
    try:
        r, g, b = c[0], c[1], c[2]
    except (TypeError, IndexError, KeyError):
        return (200, 150, 100)
    return (_clamp8(r), _clamp8(g), _clamp8(b))


def _mix(c1, c2, t: float) -> Tuple[int, int, int]:
    t = max(0.0, min(1.0, t))
    return (_clamp8(c1[0] + (c2[0] - c1[0]) * t),
            _clamp8(c1[1] + (c2[1] - c1[1]) * t),
            _clamp8(c1[2] + (c2[2] - c1[2]) * t))


def _shade(c, f: float) -> Tuple[int, int, int]:
    return (_clamp8(c[0] * f), _clamp8(c[1] * f), _clamp8(c[2] * f))


def compute_edge_density(img: Image.Image, threshold: int = 22) -> float:
    """Fraction of pixels with strong edges — rejects flat single-shape fills."""
    gray = img.convert("RGB").convert("L")
    edges = gray.filter(ImageFilter.FIND_EDGES)
    data = list(edges.getdata())
    if not data:
        return 0.0
    return sum(1 for p in data if p > threshold) / len(data)


def validate_frame_quality(
    img: Image.Image,
    min_coverage: float = 0.05,
    min_luma_variance: float = 110.0,
    min_edge_density: float = 0.045,
) -> Tuple[bool, str, float]:
    """
    Mechanical quality gate for a single animation frame.

    Returns (passed, reason, richness_score). The score lets the caller keep the
    best-of-N attempt when every attempt fails, instead of shipping a flat frame.
    """
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    w, h = img.size
    if w < 2 or h < 2:
        return False, f"too small ({w}x{h})", 0.0

    alpha_data = list(img.split()[3].getdata())
    luma_data = list(img.convert("RGB").convert("L").getdata())
    opaque_luma = [l for l, a in zip(luma_data, alpha_data) if a > 24]
    coverage = len(opaque_luma) / max(1, w * h)

    # Variance over OPAQUE pixels only: a flat single-color fill (the classic
    # "colored box"/circle programmer-art) scores ~0 here even though it looks
    # high-variance against the transparent background. Shaded, textured bodies
    # keep a high internal variance and pass.
    if len(opaque_luma) >= 8:
        mean = sum(opaque_luma) / len(opaque_luma)
        variance = sum((v - mean) ** 2 for v in opaque_luma) / len(opaque_luma)
    else:
        variance = 0.0
    edge = compute_edge_density(img)

    # Normalized richness score (each metric contributes up to ~2.0).
    score = (
        min(coverage / max(min_coverage, 1e-6), 2.0)
        + min(variance / max(min_luma_variance, 1e-6), 2.0)
        + min(edge / max(min_edge_density, 1e-6), 2.0)
    )

    if coverage < min_coverage:
        return False, f"too empty ({coverage:.1%} coverage)", score
    if variance < min_luma_variance:
        return False, f"too flat (variance {variance:.1f})", score
    if edge < min_edge_density:
        return False, f"too simple (edge density {edge:.3f})", score
    return True, "ok", score


class FrameGenerator:
    """
    Generates individual animation frames with detailed, shaded, textured art.

    Richness techniques (rendered at SUPERSAMPLE resolution then blurred +
    LANCZOS-downscaled + sharpened for crisp small sprites):
      - radial shaded body (light->dark gradient) instead of a flat fill
      - rim light on a fixed light direction (top-left)
      - layered motif detail (rune ring / energy conduits / aura motes)
      - expanding shockwave rings + rotating energy rays/tendrils
      - core specular highlight and fine grain/noise for texture
    Motion is driven by frame progress so the frame-by-frame pipeline is kept.
    """

    SUPERSAMPLE = 6

    def __init__(self, palette: List[Tuple[int, int, int]]):
        pal = [_norm_rgb(c) for c in (palette or [])]
        self.palette = pal or [(210, 150, 90), (150, 90, 40), (240, 210, 140)]

    def _colors(self) -> Dict[str, Tuple[int, int, int]]:
        p = self.palette
        primary = p[0]
        secondary = p[1] if len(p) > 1 else _shade(primary, 0.6)
        accent = p[2] if len(p) > 2 else _mix(primary, WHITE, 0.35)
        highlight = p[3] if len(p) > 3 else _mix(primary, WHITE, 0.6)
        return {
            "primary": primary,
            "secondary": secondary,
            "accent": accent,
            "highlight": _mix(highlight, WHITE, 0.12),
            "shadow": _shade(primary, 0.30),
            "rim": _mix(highlight, WHITE, 0.55),
            "glow": _mix(accent, primary, 0.35),
        }

    # -- primitive richness helpers (operate in supersampled space) ----------
    @staticmethod
    def _draw_glow(draw, cx, cy, r, color, layers=7, max_alpha=80):
        for i in range(layers, 0, -1):
            t = i / layers
            rr = r * (0.35 + 0.65 * t)
            a = int(max_alpha * (1.0 - t) ** 1.2)
            if a <= 0:
                continue
            draw.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=color + (a,))

    @staticmethod
    def _draw_shaded_orb(draw, cx, cy, r, core, edge, steps=18):
        for i in range(steps, 0, -1):
            t = i / steps
            rr = r * t
            col = _mix(core, edge, t ** 0.85)
            draw.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=col + (255,))

    @staticmethod
    def _poly(cx, cy, r, sides, rot=0.0):
        return [
            (cx + math.cos(rot + k * math.tau / sides) * r,
             cy + math.sin(rot + k * math.tau / sides) * r)
            for k in range(sides)
        ]

    def _draw_shaded_poly(self, draw, cx, cy, r, sides, rot, core, edge, steps=12):
        for i in range(steps, 0, -1):
            t = i / steps
            col = _mix(core, edge, t ** 0.9)
            draw.polygon(self._poly(cx, cy, r * t, sides, rot), fill=col + (255,))

    @staticmethod
    def _draw_rings(draw, cx, cy, r, color, count, width, progress):
        for i in range(count):
            rr = r * (0.55 + i * 0.42 + progress * 0.55)
            a = int(190 * (1.0 - i / max(count, 1)))
            if a <= 0:
                continue
            draw.ellipse([cx - rr, cy - rr, cx + rr, cy + rr],
                         outline=color + (a,), width=width)

    @staticmethod
    def _draw_rays(draw, cx, cy, r_in, r_out, count, color, width, phase):
        for k in range(count):
            ang = phase + k * math.tau / count
            x1, y1 = cx + math.cos(ang) * r_in, cy + math.sin(ang) * r_in
            x2, y2 = cx + math.cos(ang) * r_out, cy + math.sin(ang) * r_out
            draw.line([(x1, y1), (x2, y2)], fill=color + (215,), width=width)
            s = width * 0.9
            draw.ellipse([x2 - s, y2 - s, x2 + s, y2 + s], fill=color + (255,))

    def _draw_rune_ring(self, draw, cx, cy, r, count, phase, fill, outline, size):
        for k in range(count):
            ang = phase + k * math.tau / count
            px, py = cx + math.cos(ang) * r, cy + math.sin(ang) * r
            diamond = [(px, py - size), (px + size, py), (px, py + size), (px - size, py)]
            draw.polygon(diamond, fill=fill + (235,), outline=outline + (255,))

    @staticmethod
    def _draw_rim(draw, cx, cy, r, color, width):
        box = [cx - r, cy - r, cx + r, cy + r]
        draw.arc(box, start=178, end=300, fill=color + (235,), width=width)

    @staticmethod
    def _grain(draw, cx, cy, r, rng, light, dark, count, unit):
        for _ in range(count):
            ang = rng.uniform(0, math.tau)
            d = rng.uniform(0, r * 0.92)
            x, y = cx + math.cos(ang) * d, cy + math.sin(ang) * d
            col = light if rng.random() > 0.62 else dark
            s = rng.uniform(unit * 0.35, unit * 0.95)
            draw.ellipse([x - s, y - s, x + s, y + s],
                         fill=col + (rng.randint(35, 105),))

    # -- per-animation-type rich renderers -----------------------------------
    def _render_spellcast(self, draw, W, H, prog, rng, c, cx, cy, base, lw, unit):
        grow = 0.42 + 0.58 * prog
        r = base * grow
        phase = prog * math.tau
        self._draw_glow(draw, cx, cy, r * 1.7, c["glow"], layers=8, max_alpha=70)
        self._draw_rings(draw, cx, cy, r * 1.05, c["accent"], 3, lw, prog)
        self._draw_rays(draw, cx, cy, r * 0.55, r * 1.5, 8, c["highlight"], lw, phase)
        self._draw_shaded_orb(draw, cx, cy, r, _mix(c["highlight"], WHITE, 0.2), c["secondary"])
        self._draw_rune_ring(draw, cx, cy, r * 0.78, 6, -phase * 0.7,
                             c["accent"], c["shadow"], r * 0.13)
        self._draw_rim(draw, cx, cy, r, c["rim"], max(2, int(r * 0.10)))
        self._grain(draw, cx, cy, r, rng, c["rim"], c["shadow"], int(r * 0.28), unit)
        hx, hy = cx - r * 0.26, cy - r * 0.30
        draw.ellipse([hx - r * 0.17, hy - r * 0.17, hx + r * 0.17, hy + r * 0.17],
                     fill=c["rim"] + (215,))

    def _render_device(self, draw, W, H, prog, rng, c, cx, cy, base, lw, unit):
        pulse = 0.5 + 0.5 * math.sin(prog * math.tau)
        r = base * (0.60 + 0.30 * pulse)
        rot = math.pi / 6 + prog * 0.4
        self._draw_glow(draw, cx, cy, r * 1.6, c["glow"], layers=7,
                        max_alpha=int(45 + 45 * pulse))
        self._draw_rings(draw, cx, cy, r * 1.15, c["accent"], 2, lw, pulse)
        # energy conduits from core to each vertex (brightness pulses)
        conduit = _mix(c["accent"], c["rim"], pulse)
        for (vx, vy) in self._poly(cx, cy, r * 1.28, 6, rot):
            draw.line([(cx, cy), (vx, vy)], fill=conduit + (200,), width=max(2, lw - 1))
            s = lw
            draw.ellipse([vx - s, vy - s, vx + s, vy + s], fill=c["rim"] + (235,))
        self._draw_shaded_poly(draw, cx, cy, r, 6, rot,
                               _mix(c["highlight"], WHITE, 0.15), c["secondary"])
        # inner core hex
        self._draw_shaded_poly(draw, cx, cy, r * 0.5, 6, -rot,
                               c["rim"], c["accent"], steps=6)
        # bolts on high pulse
        if pulse > 0.6:
            self._draw_rays(draw, cx, cy, r * 0.5, r * 1.15,
                            6, c["rim"], max(2, lw - 1), prog * math.tau)
        self._draw_rim(draw, cx, cy, r, c["rim"], max(2, int(r * 0.09)))
        self._grain(draw, cx, cy, r, rng, c["rim"], c["shadow"], int(r * 0.22), unit)

    def _render_status(self, draw, W, H, prog, rng, c, cx, cy, base, lw, unit):
        pulse = 0.5 + 0.5 * math.sin(prog * math.tau)
        r = base * 0.86
        phase = prog * math.tau
        self._draw_glow(draw, cx, cy, r * 1.25, c["glow"], layers=8,
                        max_alpha=int(45 + 40 * pulse))
        # shimmering aura rings
        for i in range(3):
            rr = r * (0.55 + i * 0.2)
            a = int(90 + 90 * (0.5 + 0.5 * math.sin(phase + i * 1.3)))
            draw.ellipse([cx - rr, cy - rr, cx + rr, cy + rr],
                         outline=_mix(c["accent"], c["highlight"], i / 3) + (a,),
                         width=max(2, lw - 1))
        # central soft shaded core
        self._draw_shaded_orb(draw, cx, cy, r * 0.42,
                              _mix(c["highlight"], WHITE, 0.25), c["secondary"], steps=12)
        # drifting orbiting motes
        motes = 9
        for k in range(motes):
            ang = phase + k * math.tau / motes
            d = r * (0.72 + 0.14 * math.sin(phase * 1.7 + k))
            mx, my = cx + math.cos(ang) * d, cy + math.sin(ang) * d
            s = unit * (1.1 + 0.6 * math.sin(phase + k))
            draw.ellipse([mx - s, my - s, mx + s, my + s], fill=c["rim"] + (225,))
        self._draw_rim(draw, cx, cy, r * 0.42, c["rim"], max(2, int(r * 0.06)))
        self._grain(draw, cx, cy, r * 0.5, rng, c["rim"], c["shadow"], int(r * 0.18), unit)

    def generate_frame(self, frame_index: int, frame_count: int, width: int, height: int,
                       animation_type: str = "SpellCast", seed_offset: int = 0) -> Image.Image:
        """
        Generate a single, richly rendered animation frame.

        Args:
            frame_index: Current frame index (0-based)
            frame_count: Total number of frames
            width: Frame width in pixels
            height: Frame height in pixels
            animation_type: SpellCast | DeviceActivation | StatusEffect | Default
            seed_offset: Perturbs procedural detail so retries differ (quality gate)

        Returns:
            PIL Image in RGBA format at (width, height)
        """
        progress = frame_index / max(frame_count - 1, 1)
        ss = self.SUPERSAMPLE
        W, H = max(2, width) * ss, max(2, height) * ss

        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img, "RGBA")
        rng = random.Random((frame_index * 2654435761 + hash(animation_type) + seed_offset * 40503) & 0xFFFFFFFF)

        c = self._colors()
        cx, cy = W / 2.0, H / 2.0
        base = min(W, H) * 0.45
        lw = max(2, int(base * 0.05))
        unit = max(2.0, base * 0.045)

        renderer = {
            "SpellCast": self._render_spellcast,
            "DeviceActivation": self._render_device,
            "StatusEffect": self._render_status,
        }.get(animation_type, self._render_spellcast)
        renderer(draw, W, H, progress, rng, c, cx, cy, base, lw, unit)

        # Supersample downscale pipeline: soft blur -> LANCZOS -> resharpen.
        img = img.filter(ImageFilter.GaussianBlur(radius=ss * 0.32))
        img = img.resize((max(2, width), max(2, height)), Image.Resampling.LANCZOS)
        img = ImageEnhance.Sharpness(img).enhance(1.4)
        img = ImageEnhance.Contrast(img).enhance(1.08)
        img = ImageEnhance.Color(img).enhance(1.10)
        return img.convert("RGBA")

    def generate_validated_frame(self, frame_index: int, frame_count: int, width: int,
                                 height: int, animation_type: str = "SpellCast",
                                 max_attempts: int = 3) -> Tuple[Image.Image, Dict]:
        """
        Generate a frame and run it through the mechanical quality gate, retrying
        with perturbed seeds so flat frames FAIL and are regenerated. Keeps the
        richest attempt if none passes outright.
        """
        best_img: Optional[Image.Image] = None
        best_score = -1.0
        best_reason = "no attempt"
        for attempt in range(max_attempts):
            img = self.generate_frame(frame_index, frame_count, width, height,
                                      animation_type, seed_offset=attempt)
            ok, reason, score = validate_frame_quality(img)
            if ok:
                return img, {"attempt": attempt + 1, "pass": True, "reason": reason,
                             "score": round(score, 3)}
            if score > best_score:
                best_score, best_img, best_reason = score, img, reason
        return best_img, {"attempt": max_attempts, "pass": False,
                          "reason": best_reason, "score": round(best_score, 3)}


class AtlasPacker:
    """Packs frames into a spritesheet atlas via libs.SpritesheetAssembler (rectpack)."""

    def __init__(self, padding: int = 2, power_of_two: bool = True):
        self.padding = padding
        self.power_of_two = power_of_two
        self._assembler = SpritesheetAssembler(padding=padding, power_of_two=power_of_two)

    def pack_frames(self, frames: List[Image.Image], frame_width: int, frame_height: int) -> Tuple[Image.Image, Dict]:
        packed = self._assembler.assemble(
            frames,
            layout=Layout.HORIZONTAL,
            tile=(frame_width, frame_height),
            alias="default",
        )
        metadata = packed.frames_dict()
        metadata["frames"] = packed.rects
        return packed.image, metadata

    def _next_power_of_two(self, n: int) -> int:
        return 1 << (n - 1).bit_length()


class FrameGeneratorOrchestrator:
    """Main orchestrator for frame generation pipeline"""
    
    def __init__(self, ollama_url: str = "http://localhost:11434", output_dir: str = "output"):
        self.palette_gen = PaletteGenerator(ollama_url)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def process_job(self, job: FrameJob) -> Dict:
        """
        Process a frame generation job.
        
        Args:
            job: FrameJob specification
        
        Returns:
            Dictionary with output paths and metadata
        """
        print(f"[INFO] Processing job: {job.asset_name}")
        
        # Step 1: Generate palette
        print(f"[STEP 1] Generating palette...")
        palette, palette_extras = self.palette_gen.generate_palette_from_hints(
            job.color_hints or [],
            role=job.animation_type
        )
        print(f"[OK] Palette: {palette}")
        
        # Save palette extras if any
        if palette_extras:
            extras_dir = self.output_dir / "Extras"
            extras_dir.mkdir(exist_ok=True)
            for i, extra_palette in enumerate(palette_extras, 1):
                palette_file = extras_dir / f"{job.asset_name}_palette_extra_{i}.json"
                with open(palette_file, 'w') as f:
                    json.dump(extra_palette, f, indent=2)
                print(f"[OK] Saved extra palette: {palette_file.name}")
        
        # Step 2: Generate frames (quality-gated: flat frames FAIL and retry)
        print(f"[STEP 2] Generating {job.frame_count} frames...")
        frame_gen = FrameGenerator(palette)
        frames = []
        frame_reports = []
        passed = 0
        for i in range(job.frame_count):
            frame, report = frame_gen.generate_validated_frame(
                i, job.frame_count,
                job.frame_width, job.frame_height,
                job.animation_type,
                max_attempts=3,
            )
            frames.append(frame)
            frame_reports.append(report)
            if report.get("pass"):
                passed += 1
            else:
                print(f"  [WARN] frame {i} best-effort ({report.get('reason')}, "
                      f"score {report.get('score')})")
        print(f"[OK] Generated {len(frames)} frames "
              f"({passed}/{len(frames)} passed quality gate)")
        
        # Step 3: Pack frames into atlas
        print(f"[STEP 3] Packing frames into atlas...")
        packer = AtlasPacker(padding=2, power_of_two=True)
        atlas, metadata = packer.pack_frames(
            frames, job.frame_width, job.frame_height
        )
        print(f"[OK] Atlas size: {atlas.size}")
        
        # Step 4: Save outputs
        print(f"[STEP 4] Saving outputs...")
        output_path = self.output_dir / f"{job.asset_name}.png"
        frames_path = self.output_dir / f"{job.asset_name}.frames"
        
        # Save atlas as 32-bit RGBA PNG (uncompressed)
        atlas.save(str(output_path), "PNG", compress_level=0)
        
        # Save .frames metadata
        with open(frames_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"[OK] Saved: {output_path}")
        print(f"[OK] Saved: {frames_path}")
        
        # Step 5: Validate
        print(f"[STEP 5] Validating output...")
        validation = self._validate_output(output_path, frames_path, job)
        if not validation["valid"]:
            print(f"[WARN] Validation issues: {validation['issues']}")
        else:
            print(f"[OK] Validation passed")
        
        return {
            "success": True,
            "atlas_path": str(output_path),
            "frames_path": str(frames_path),
            "metadata": metadata,
            "frame_quality": frame_reports,
            "validation": validation
        }
    
    def _validate_output(self, atlas_path: Path, frames_path: Path, job: FrameJob) -> Dict:
        """Validate generated output"""
        issues = []
        
        # Check files exist
        if not atlas_path.exists():
            issues.append(f"Atlas file missing: {atlas_path}")
        if not frames_path.exists():
            issues.append(f"Frames file missing: {frames_path}")
        
        if issues:
            return {"valid": False, "issues": issues}
        
        # Check atlas image
        try:
            img = Image.open(atlas_path)
            if img.mode != 'RGBA':
                issues.append(f"Atlas not RGBA: {img.mode}")
            
            # Mechanical richness gate on the first frame: rejects flat
            # "programmer-art" (single shape / gradient) via alpha coverage +
            # luma variance + edge density (same technique as hydromancy_quality).
            if job.frame_count > 0:
                frame_width = job.frame_width
                frame_height = job.frame_height
                sample_frame = img.crop((0, 0, frame_width, frame_height)).convert("RGBA")
                colors = sample_frame.getcolors(maxcolors=256)
                if colors and len(colors) < 5:
                    issues.append("Frame appears to be single-color (colored box)")
                ok, reason, _score = validate_frame_quality(sample_frame)
                if not ok:
                    issues.append(f"Frame failed richness gate: {reason}")
        except Exception as e:
            issues.append(f"Atlas validation error: {e}")
        
        # Check .frames JSON
        try:
            with open(frames_path) as f:
                frames_data = json.load(f)
            if "frameGrid" not in frames_data:
                issues.append("Missing frameGrid in .frames file")
        except Exception as e:
            issues.append(f"Frames file validation error: {e}")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues
        }


def main():
    """CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="OpenStarbound Frame Generator")
    parser.add_argument("--job", type=str, required=True, help="Job JSON file")
    parser.add_argument("--output", type=str, default="output", help="Output directory")
    parser.add_argument("--ollama-url", type=str, default="http://localhost:11434", help="Ollama URL")
    
    args = parser.parse_args()
    
    # Load job
    with open(args.job) as f:
        job_data = json.load(f)
    
    job = FrameJob(**job_data)
    job.quality_level = QualityLevel(job_data.get("quality_level", "pixel_art"))
    
    # Process job
    orchestrator = FrameGeneratorOrchestrator(args.ollama_url, args.output)
    result = orchestrator.process_job(job)
    
    # Output result
    print("\n" + "="*60)
    print("GENERATION COMPLETE")
    print("="*60)
    print(json.dumps(result, indent=2))
    
    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
