#!/usr/bin/env python3
"""
UNIFIED Space-Time Vortex Asset Generator (AI-Powered)
Merges all improvements from multiple generator scripts into one unified solution.

Features:
- 4x supersampling with LANCZOS anti-aliasing
- 16-frame ultra-smooth animations
- Multi-AI support (math AI + visual AI)
- HSV color space for vibrant gradients
- Multiple layered effects (5+ layers per frame)
- High-resolution support (64x64, 96x96) for tile scaling mods
- Audio generation support (white hole sounds)
- Model router integration for automatic model selection
- All asset types: icons, animations, particles, overlays, ability icons, warning markers

Creates cinema-quality animated sprites for Caves of Qud
"""

import os
import sys
import json
import time
import re
from pathlib import Path
from typing import Tuple, Dict, Optional
from PIL import Image, ImageDraw, ImageFilter
import math
import colorsys

# Native Qud cell size (vanilla Mutations/spacetime_vortex.bmp). Truecolor RGBA — dual-tone tinting not required.
QUD_TILE = (16, 24)
QUD_PARTICLE = (16, 16)

# Quality pipeline (caching, drafts, post-process, validation)
try:
    from vortex_quality import VortexQualityPipeline, finalize_qud_sprite
    VORTEX_QUALITY_AVAILABLE = True
except ImportError:
    VORTEX_QUALITY_AVAILABLE = False
    VortexQualityPipeline = None
    finalize_qud_sprite = None

try:
    from qud_procedural_render import (
        render_rich_ability_icon,
        render_rich_distortion_overlay,
        render_rich_particle,
        render_rich_warning_marker,
    )
    QUD_PROCEDURAL_AVAILABLE = True
except ImportError:
    QUD_PROCEDURAL_AVAILABLE = False
    render_rich_ability_icon = None
    render_rich_distortion_overlay = None
    render_rich_particle = None
    render_rich_warning_marker = None

try:
    from qud_sd_client import generate_sd_draft, get_sd_api_url
    QUD_SD_AVAILABLE = True
except ImportError:
    QUD_SD_AVAILABLE = False
    generate_sd_draft = None  # type: ignore
    get_sd_api_url = None  # type: ignore

# Import Ollama integration
_ollama_path = os.path.join(os.path.dirname(__file__), "..", "Shared", "ollama_integration.py")
OLLAMA_INTEGRATION_AVAILABLE = False
call_ollama = None
test_ollama_connection = None
TASK_VISUAL = "visual"

if os.path.exists(_ollama_path):
    try:
        shared_dir = os.path.join(os.path.dirname(__file__), "..", "Shared")
        if shared_dir not in sys.path:
            sys.path.insert(0, shared_dir)
        from ollama_integration import call_ollama, test_ollama_connection
        OLLAMA_INTEGRATION_AVAILABLE = True
    except ImportError as e:
        OLLAMA_INTEGRATION_AVAILABLE = False
        print(f"Warning: Could not import Ollama integration: {e}")

# Import model router if available
_model_router_path = os.path.join(os.path.dirname(__file__), "..", "Common", "ollama_model_router.py")
MODEL_ROUTER_AVAILABLE = False
get_visual_model = None
if os.path.exists(_model_router_path):
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "Common"))
        from ollama_model_router import get_visual_model, TASK_VISUAL
        MODEL_ROUTER_AVAILABLE = True
    except ImportError:
        MODEL_ROUTER_AVAILABLE = False
        get_visual_model = None
else:
    MODEL_ROUTER_AVAILABLE = False
    get_visual_model = None

# Import audio generator for white hole sounds (optional)
_audio_gen_path = os.path.join(os.path.dirname(__file__), "qud_audio_generator.py")
AUDIO_GENERATOR_AVAILABLE = False
QudAudioGenerator = None
np = None
sf = None
try:
    import numpy as np
    import soundfile as sf
    if os.path.exists(_audio_gen_path):
        try:
            sys.path.insert(0, os.path.dirname(__file__))
            from qud_audio_generator import QudAudioGenerator
            AUDIO_GENERATOR_AVAILABLE = True
        except ImportError:
            AUDIO_GENERATOR_AVAILABLE = False
except ImportError:
    AUDIO_GENERATOR_AVAILABLE = False

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except:
        pass


class ProfessionalVortexGenerator:
    """Professional-grade vortex asset generator with AI design + advanced rendering."""
    
    def __init__(
        self,
        mod_path: Path,
        ollama_url: str = "http://localhost:11434",
        model: str = None,
        use_cache: bool = True,
        use_drafts: bool = True,
        quality: str = "full",
    ):
        self.mod_path = Path(mod_path)
        self.textures_path = self.mod_path / "Textures"
        self.visuals_path = self.mod_path / "Visuals"
        self.sounds_path = self.mod_path / "Sounds"
        self.textures_path.mkdir(exist_ok=True)
        self.visuals_path.mkdir(exist_ok=True)
        self.sounds_path.mkdir(exist_ok=True)
        
        self.ollama_url = ollama_url
        self.use_cache = use_cache
        self.use_drafts = use_drafts
        self.quality = quality
        self.prefer_sd = True
        self._sd_checked = False
        self._sd_available = False

        self.quality_pipeline = None
        if VORTEX_QUALITY_AVAILABLE and VortexQualityPipeline is not None:
            self.quality_pipeline = VortexQualityPipeline(
                mod_path=self.mod_path,
                use_cache=use_cache,
                use_drafts=use_drafts,
                quality=quality,
            )
            print(f"  [OK] Quality pipeline: cache={use_cache}, drafts={use_drafts}, quality={quality}")
        
        # Performance optimization caches
        self._color_cache = {}  # Cache hex -> RGB conversions
        self._hsv_cache = {}  # Cache HSV -> RGB conversions (rounded to avoid float precision issues)
        self._frame_cache = {}  # Cache rendered frames for reuse
        self._gradient_cache = {}  # Cache radial gradients
        
        # Initialize audio generator if available (optional)
        self.audio_gen = None
        if AUDIO_GENERATOR_AVAILABLE:
            try:
                self.audio_gen = QudAudioGenerator()
                print("  [OK] Audio generator available for white hole sounds")
            except Exception as e:
                print(f"  [WARN] Could not initialize audio generator: {e}")
        
        if model is None:
            preferred_visual_model = "wizardlm-uncensored:latest"
            if OLLAMA_INTEGRATION_AVAILABLE:
                available_models = self._get_available_models()
                if preferred_visual_model in available_models:
                    model = preferred_visual_model
                elif available_models:
                    wizardlm_models = [m for m in available_models if 'wizardlm' in m.lower() and 'uncensored' in m.lower()]
                    if not wizardlm_models:
                        wizardlm_models = [m for m in available_models if 'wizardlm' in m.lower()]
                    if wizardlm_models:
                        model = wizardlm_models[0]
                    elif MODEL_ROUTER_AVAILABLE and get_visual_model:
                        try:
                            model = get_visual_model()
                            print(f"  [OK] Using model router selected model: {model}")
                        except:
                            model = available_models[0]
                    else:
                        model = available_models[0]
                elif MODEL_ROUTER_AVAILABLE and get_visual_model:
                    try:
                        model = get_visual_model()
                        print(f"  [OK] Using model router selected model: {model}")
                    except:
                        model = preferred_visual_model
                else:
                    model = preferred_visual_model
            else:
                model = preferred_visual_model
        self.model = model
        
        # Test Ollama connection - REQUIRED for high-quality AI assets
        if OLLAMA_INTEGRATION_AVAILABLE:
            print("Testing Ollama connection for AI design generation...")
            try:
                self.ollama_available = test_ollama_connection()
                if not self.ollama_available:
                    raise RuntimeError(
                        "Ollama is not available. Please start Ollama before running this script.\n"
                        "  Start Ollama: ollama serve\n"
                        "  Verify connection: curl http://localhost:11434/api/tags"
                    )
                print(f"  [OK] Using Ollama model: {self.model}")
            except Exception as e:
                if isinstance(e, RuntimeError):
                    raise
                raise RuntimeError(
                    f"Failed to connect to Ollama: {e}\n"
                    "  Please ensure Ollama is running: ollama serve\n"
                    "  Check Ollama URL: " + self.ollama_url
                )
        else:
            raise RuntimeError(
                "Ollama integration module not found. Cannot generate AI-designed assets without Ollama.\n"
                "  Please ensure OllamaIntegration.psm1 or equivalent is available."
            )
    
    def _get_available_models(self):
        """Get list of available Ollama models."""
        try:
            import requests
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=3)
            if response.status_code == 200:
                data = response.json()
                return [model["name"] for model in data.get("models", [])]
        except:
            pass
        return []
    
    def _call_ollama_design(
        self,
        prompt: str,
        asset_type: str,
        use_math_ai: bool = True,
        draft_key: str = None,
    ) -> Dict:
        """Call Ollama for design JSON via quality pipeline (cache, repair, draft palettes)."""
        if not OLLAMA_INTEGRATION_AVAILABLE:
            raise RuntimeError("Ollama integration not available. Cannot generate AI designs.")
        if not self.ollama_available:
            raise RuntimeError("Ollama connection not established. Please ensure Ollama is running.")

        task_type = "analysis" if use_math_ai else "visual"
        ai_type = "math-focused AI" if use_math_ai else "visual AI"

        if self.quality_pipeline is not None:
            print(f"  Calling {ai_type} for {asset_type} design specs...")
            start_time = time.time()
            design = self.quality_pipeline.get_design(
                call_ollama, prompt, asset_type, task_type, draft_key=draft_key
            )
            print(f"  {ai_type} design received in {time.time() - start_time:.1f}s")
            print(f"  [OK] AI design specs generated (colors, patterns, style)")
            return design

        return self._call_ollama_design_legacy(prompt, asset_type, use_math_ai)

    def _call_ollama_design_legacy(self, prompt: str, asset_type: str, use_math_ai: bool = True) -> Dict:
        """Legacy Ollama design call without quality pipeline."""
        task_type = "analysis" if use_math_ai else "visual"
        ai_type = "math-focused AI" if use_math_ai else "visual AI (wizardlm-uncensored)"
        max_retries = 2
        for attempt in range(max_retries):
            try:
                print(f"  Calling {ai_type} for {asset_type} design specs...")
                if attempt > 0:
                    print(f"    (Retry attempt {attempt + 1}/{max_retries})")
                start_time = time.time()
                response = call_ollama(
                    prompt=prompt,
                    task_type=task_type,
                    response_length="standard",
                    system_prompt="You are a pixel art designer specializing in roguelike game assets. Design color schemes and visual patterns. Always return valid JSON only.",
                    model_name=None,
                )
                elapsed = time.time() - start_time
                print(f"  {ai_type} design received in {elapsed:.1f} seconds")
                if not response:
                    raise ValueError("Ollama returned empty response")
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                if json_start < 0 or json_end <= json_start:
                    raise ValueError("Could not find JSON in Ollama response")
                json_str = response[json_start:json_end]
                json_str = re.sub(r'(\w+):', r'"\1":', json_str)
                json_str = re.sub(r'""(\w+)"":', r'"\1":', json_str)
                design = json.loads(json_str)
                print(f"  [OK] AI design specs generated (colors, patterns, style)")
                return design
            except (ValueError, json.JSONDecodeError) as ve:
                if attempt < max_retries - 1:
                    print(f"  WARNING: {ve}, retrying...")
                    time.sleep(1)
                    continue
                raise
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"  WARNING: {e}, retrying...")
                    time.sleep(1)
                    continue
                raise RuntimeError(f"Failed to generate {asset_type} design: {e}")
        raise RuntimeError(f"Failed to generate {asset_type} design")
    
    def _optimize_image(self, img: Image.Image, use_ai_optimization: bool = True) -> Image.Image:
        """Apply final polish before downscale (supersampled render pass)."""
        if finalize_qud_sprite is not None:
            return finalize_qud_sprite(img, target_size=img.size, sharpen=1.15, contrast=1.05)
        img = img.filter(ImageFilter.SMOOTH_MORE)
        return img

    def _save_sprite(self, img: Image.Image, path: Path, size: Tuple[int, int] = None) -> bool:
        """Save through quality pipeline (validate + optional ImageMagick)."""
        if self.quality_pipeline is not None:
            return self.quality_pipeline.export_sprite(img, path, size=size)
        path.parent.mkdir(parents=True, exist_ok=True)
        out = img if size is None else img.resize(size, Image.LANCZOS)
        out.save(path, "PNG")
        return path.exists()

    def _sd_server_up(self) -> bool:
        if not self.prefer_sd or not QUD_SD_AVAILABLE or get_sd_api_url is None:
            return False
        if not self._sd_checked:
            self._sd_checked = True
            try:
                self._sd_available = bool(get_sd_api_url(verbose=False))
            except Exception:
                self._sd_available = False
            if self._sd_available:
                print("  [OK] Local SD server detected — prefer SD for static UI icons")
            else:
                print("  [INFO] No local SD server — procedural icons")
        return self._sd_available

    def _try_sd_static_icon(
        self,
        label: str,
        design: Dict,
        size: Tuple[int, int],
        *,
        subject: str,
    ) -> Optional[Image.Image]:
        """Prefer local SD for static icons when the server is up; else None (caller falls back)."""
        if not self._sd_server_up() or generate_sd_draft is None:
            return None
        cs = design.get("colorScheme") or {}
        colors = ", ".join(
            str(cs.get(k)) for k in ("primary", "secondary", "glow", "outline") if cs.get(k)
        )
        shape = (design.get("shape") or {}).get("type") or (design.get("symbol") or {}).get("shape") or "icon"
        prompt = (
            f"Caves of Qud pixel art UI icon, {subject}, {shape}, colors {colors}, "
            f"transparent background, centered, crisp edges, no text, no watermark, game UI sprite"
        )
        negative = "text, logo, watermark, photo, blurry, 3d render, cluttered background"
        drafts = self.mod_path / "DesignDrafts" / "sd_finals"
        drafts.mkdir(parents=True, exist_ok=True)
        out = drafts / f"{label}_sd.png"
        try:
            result = generate_sd_draft(
                prompt,
                out,
                negative_prompt=negative,
                width=512,
                height=512,
                steps=22,
                guidance_scale=7.0,
                lock_label=f"vortex_{label}",
            )
            if not result.ok or not result.output_path or not result.output_path.exists():
                return None
            img = Image.open(result.output_path).convert("RGBA")
            if img.size != size:
                img = img.resize(size, Image.LANCZOS)
            print(f"   [SD] {label} from local Stable Diffusion")
            return img
        except Exception as exc:
            print(f"   [WARN] SD icon '{label}' failed ({exc}); procedural fallback")
            return None
    
    def hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        """Convert hex color to RGB tuple with caching for performance."""
        # Normalize hex color (remove #, lowercase)
        hex_normalized = hex_color.lstrip('#').lower()
        
        # Check cache first
        if hex_normalized in self._color_cache:
            return self._color_cache[hex_normalized]
        
        # Convert and cache
        rgb = tuple(int(hex_normalized[i:i+2], 16) for i in (0, 2, 4))
        self._color_cache[hex_normalized] = rgb
        return rgb
    
    def _hsv_to_rgb_cached(self, h: float, s: float, v: float) -> Tuple[int, int, int]:
        """Convert HSV to RGB with caching for performance.
        
        Rounds HSV values to reduce cache misses from float precision issues.
        """
        # Round to 3 decimal places to avoid float precision cache misses
        h_rounded = round(h, 3)
        s_rounded = round(s, 3)
        v_rounded = round(v, 3)
        cache_key = (h_rounded, s_rounded, v_rounded)
        
        if cache_key in self._hsv_cache:
            return self._hsv_cache[cache_key]
        
        rgb = colorsys.hsv_to_rgb(h, s, v)
        rgb_int = tuple(int(c * 255) for c in rgb)
        self._hsv_cache[cache_key] = rgb_int
        return rgb_int
    
    def create_radial_gradient(self, size: Tuple[int, int], color_inner: Tuple[int, int, int],
                              color_outer: Tuple[int, int, int], alpha_inner: int = 255,
                              alpha_outer: int = 0) -> Image.Image:
        """Create smooth radial gradient using supersampling with caching."""
        # Create cache key
        cache_key = (size, color_inner, color_outer, alpha_inner, alpha_outer)
        if cache_key in self._gradient_cache:
            return self._gradient_cache[cache_key].copy()
        
        # Render at 2x resolution for smoothness
        img = Image.new('RGBA', (size[0] * 2, size[1] * 2), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        cx, cy = size[0], size[1]  # 2x center
        max_radius = min(cx, cy)
        
        # Draw many concentric circles for smooth gradient
        for r in range(max_radius, 0, -1):
            t = 1 - (r / max_radius)
            
            # Smooth color interpolation
            color = tuple(
                int(color_outer[i] * (1 - t) + color_inner[i] * t)
                for i in range(3)
            )
            alpha = int(alpha_outer * (1 - t) + alpha_inner * t)
            
            draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                        fill=(*color, alpha), outline=None)
        
        # Downscale with anti-aliasing
        result = img.resize(size, Image.LANCZOS)
        
        # Cache the result
        self._gradient_cache[cache_key] = result.copy()
        return result
    
    def render_professional_black_hole_with_design(self, design: Dict, frame: int, total_frames: int = 16,
                                      output_size: Tuple[int, int] = QUD_TILE) -> Image.Image:
        """Render professional quality space-time vortex using AI design with frame caching."""
        # Check frame cache (use design hash + frame as key)
        design_hash = hash(str(sorted(design.items())))
        cache_key = (design_hash, frame, total_frames, output_size, 'black_hole')
        
        if cache_key in self._frame_cache:
            return self._frame_cache[cache_key].copy()
        
        # Extract colors from AI design (cached via hex_to_rgb)
        cs = design.get('colorScheme', {})
        void_color = self.hex_to_rgb(cs.get('void', '#000000'))
        event_horizon = self.hex_to_rgb(cs.get('eventHorizon', '#142850'))
        accretion = self.hex_to_rgb(cs.get('accretionDisk', '#2a4a80'))
        glow = self.hex_to_rgb(cs.get('glow', '#4a80c0'))
        outline = self.hex_to_rgb(cs.get('outline', '#1a3050'))
        
        # Render at 4x resolution
        render_size = (output_size[0] * 4, output_size[1] * 4)
        img = Image.new('RGBA', render_size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        cx, cy = render_size[0] // 2, render_size[1] // 2
        rotation = (frame / total_frames) * (2 * math.pi)
        pulse = math.sin(frame * 2 * math.pi / total_frames)
        
        # LAYER 1: Outer space-time distortion glow (using AI glow color)
        for i in range(25, 0, -1):
            radius = int(cx * 0.95 - i * 3)
            if radius > 0:
                t = i / 25
                color = tuple(int(glow[j] * (1 - t * 0.5)) for j in range(3))
                alpha = int(25 * (1 - t))
                draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius],
                           fill=(*color, alpha), outline=None)
        
        # LAYER 2: Rotating space-time spiral (using AI accretion disk color)
        shape = design.get('shape', {})
        arms = shape.get('spiralArms', 3)
        for arm in range(arms):
            arm_angle = (2 * math.pi * arm / arms) + rotation
            
            for i in range(250):
                t = i / 250
                angle = arm_angle + (t * 12 * math.pi)
                radius = t * (cx * 0.7) * math.exp(t * 0.4)
                
                x = int(cx + radius * math.cos(angle))
                y = int(cy + radius * math.sin(angle))
                
                if 0 <= x < render_size[0] and 0 <= y < render_size[1]:
                    color = tuple(int(accretion[j] * (1 - t * 0.3) + event_horizon[j] * (t * 0.3)) for j in range(3))
                    thickness = int(10 * (1 - t * 0.7))
                    draw.ellipse([x - thickness, y - thickness, x + thickness, y + thickness],
                               fill=color, outline=None)
                    
                    if t < 0.75:
                        glow_size = thickness + 5
                        glow_alpha = int(80 * (1 - t))
                        glow_color = tuple(min(255, int(c * 1.3)) for c in color)
                        draw.ellipse([x - glow_size, y - glow_size, x + glow_size, y + glow_size],
                                   fill=(*glow_color, glow_alpha), outline=None)
        
        # LAYER 3: Event horizon rings (using AI event horizon color)
        for i in range(10, 0, -1):
            ring_pulse = 1.0 + (0.05 * math.sin(rotation * 2 + i * math.pi / 10))
            radius = int((cx * 0.6 - i * 10) * ring_pulse)
            
            if radius > 0:
                alpha = int(180 * (1 - i / 10))
                ring_color = (*event_horizon, alpha)
                draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius],
                           fill=None, outline=ring_color, width=5)
        
        # LAYER 4: Dark vortex core (using AI void color)
        core_size = 18
        core_pulse = int(core_size + 4 * pulse)
        
        draw.ellipse([cx - core_pulse - 6, cy - core_pulse - 6, cx + core_pulse + 6, cy + core_pulse + 6],
                    fill=(*glow, 60), outline=None)
        
        draw.ellipse([cx - core_size, cy - core_size, cx + core_size, cy + core_size],
                    fill=void_color, outline=outline, width=4)
        
        inner_size = 10
        draw.ellipse([cx - inner_size, cy - inner_size, cx + inner_size, cy + inner_size],
                    fill=(0, 0, 0), outline=outline, width=2)
        
        # Apply mathematical rendering + AI optimization
        img = self._optimize_image(img, use_ai_optimization=True)
        result = img.resize(output_size, Image.LANCZOS)
        
        # Cache the result
        self._frame_cache[cache_key] = result.copy()
        return result
    
    def render_professional_black_hole(self, frame: int, total_frames: int = 16,
                                      output_size: Tuple[int, int] = (64, 64)) -> Image.Image:
        """Render PROFESSIONAL quality space-time vortex with dark center and distortion effects."""
        # Render at 4x resolution for maximum quality
        render_size = (output_size[0] * 4, output_size[1] * 4)
        img = Image.new('RGBA', render_size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        cx, cy = render_size[0] // 2, render_size[1] // 2
        rotation = (frame / total_frames) * (2 * math.pi)
        pulse = math.sin(frame * 2 * math.pi / total_frames)
        
        # LAYER 1: Outer space-time distortion glow (gravitational lensing effect)
        for i in range(25, 0, -1):
            radius = int(cx * 0.95 - i * 3)
            if radius > 0:
                # Blue-white distortion gradient (space-time warping light)
                hue = 0.55 + (i / 300)  # Blue to cyan
                sat = 0.4 - (i / 100)
                val = 0.3 + (i / 100)
                color = self._hsv_to_rgb_cached(hue, sat, val)
                alpha = int(25 * (1 - i / 25))
                
                draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius],
                           fill=(*color, alpha), outline=None)
        
        # LAYER 2: Rotating space-time spiral (warped reality)
        for arm in range(3):
            arm_angle = (2 * math.pi * arm / 3) + rotation
            
            # Draw logarithmic spiral showing space-time distortion
            for i in range(250):
                t = i / 250
                
                # Logarithmic spiral for space-time warping
                angle = arm_angle + (t * 12 * math.pi)
                radius = t * (cx * 0.7) * math.exp(t * 0.4)
                
                x = int(cx + radius * math.cos(angle))
                y = int(cy + radius * math.sin(angle))
                
                if 0 <= x < render_size[0] and 0 <= y < render_size[1]:
                    # Blue-white gradient (warped light)
                    hue = 0.55 - (t * 0.1)  # Cyan to blue
                    sat = 0.5 + (t * 0.3)
                    val = 0.4 + (t * 0.5)
                    rgb = colorsys.hsv_to_rgb(hue, sat, val)
                    color = tuple(int(c * 255) for c in rgb)
                    
                    # Variable thickness
                    thickness = int(10 * (1 - t * 0.7))
                    
                    # Core spiral with glow
                    draw.ellipse([x - thickness, y - thickness, x + thickness, y + thickness],
                               fill=color, outline=None)
                    
                    # Distortion glow
                    if t < 0.75:
                        glow_size = thickness + 5
                        glow_alpha = int(80 * (1 - t))
                        glow_color = tuple(min(255, int(c * 1.3)) for c in color)
                        draw.ellipse([x - glow_size, y - glow_size, x + glow_size, y + glow_size],
                                   fill=(*glow_color, glow_alpha), outline=None)
        
        # LAYER 3: Reality fragments (distorted space-time being pulled in)
        particle_count = 60
        for i in range(particle_count):
            angle = (2 * math.pi * i / particle_count) + rotation * 1.2
            dist_var = 0.4 + (i % 6) * 0.08
            radius = cx * dist_var
            
            x = int(cx + radius * math.cos(angle))
            y = int(cy + radius * math.sin(angle))
            
            if 0 <= x < render_size[0] and 0 <= y < render_size[1]:
                # Blue-white particles (warped light, distorted space)
                brightness = 0.4 + (i % 5) * 0.1
                color = (int(100 * brightness), int(150 * brightness), int(220 * brightness))
                size = 2 + (i % 2)
                
                draw.ellipse([x - size, y - size, x + size, y + size],
                           fill=color, outline=None)
        
        # LAYER 4: Event horizon rings (space-time boundary)
        for i in range(10, 0, -1):
            ring_pulse = 1.0 + (0.05 * math.sin(rotation * 2 + i * math.pi / 10))
            radius = int((cx * 0.6 - i * 10) * ring_pulse)
            
            if radius > 0:
                # Dark blue rings (space-time boundary)
                alpha = int(180 * (1 - i / 10))
                ring_color = (30, 60, 120, alpha)
                
                draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius],
                           fill=None, outline=ring_color, width=5)
        
        # LAYER 5: Dark vortex core (the singularity)
        core_size = 18
        core_pulse = int(core_size + 4 * pulse)
        
        # Outer core distortion glow (subtle blue)
        draw.ellipse([cx - core_pulse - 6, cy - core_pulse - 6, cx + core_pulse + 6, cy + core_pulse + 6],
                    fill=(40, 80, 150, 60), outline=None)
        
        # Core (dark, almost black)
        draw.ellipse([cx - core_size, cy - core_size, cx + core_size, cy + core_size],
                    fill=(5, 10, 20), outline=(50, 100, 180), width=4)
        
        # Inner singularity (pure black void)
        inner_size = 10
        draw.ellipse([cx - inner_size, cy - inner_size, cx + inner_size, cy + inner_size],
                    fill=(0, 0, 0), outline=(30, 60, 120), width=2)
        
        # Apply mathematical rendering + AI image optimization
        img = self._optimize_image(img, use_ai_optimization=True)
        img = img.resize(output_size, Image.LANCZOS)
        
        return img
    
    def render_professional_white_hole_with_design(self, design: Dict, frame: int, total_frames: int = 16,
                                      output_size: Tuple[int, int] = (64, 64)) -> Image.Image:
        """Render professional quality space-time rupture using AI design with frame caching."""
        # Check frame cache
        design_hash = hash(str(sorted(design.items())))
        cache_key = (design_hash, frame, total_frames, output_size, 'white_hole')
        
        if cache_key in self._frame_cache:
            return self._frame_cache[cache_key].copy()
        
        # Extract colors from AI design (cached via hex_to_rgb)
        cs = design.get('colorScheme', {})
        center = self.hex_to_rgb(cs.get('center', '#ffffff'))
        core = self.hex_to_rgb(cs.get('core', '#fff8e0'))
        rays = self.hex_to_rgb(cs.get('rays', '#ffd080'))
        glow = self.hex_to_rgb(cs.get('glow', '#ffb040'))
        outline = self.hex_to_rgb(cs.get('outline', '#ff8000'))
        
        # Render at 4x resolution
        render_size = (output_size[0] * 4, output_size[1] * 4)
        img = Image.new('RGBA', render_size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        cx, cy = render_size[0] // 2, render_size[1] // 2
        rotation = (frame / total_frames) * (-2 * math.pi)
        pulse = math.sin(frame * 2 * math.pi / total_frames)
        
        # LAYER 1: Explosive outer energy burst (using AI glow color)
        for i in range(25, 0, -1):
            radius = int(cx * 0.95 - i * 3)
            if radius > 0:
                t = i / 25
                color = tuple(int(glow[j] * (1 - t * 0.3) + center[j] * (t * 0.3)) for j in range(3))
                alpha = int(40 * (1 - t))
                draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius],
                           fill=(*color, alpha), outline=None)
        
        # LAYER 2: Rotating energy rays (using AI rays color)
        shape = design.get('shape', {})
        ray_count = shape.get('rays', 24)
        for ray_idx in range(ray_count):
            angle = (2 * math.pi * ray_idx / ray_count) + rotation
            
            for dist in range(0, int(cx * 0.85), 3):
                t = dist / (cx * 0.85)
                
                x = int(cx + dist * math.cos(angle))
                y = int(cy + dist * math.sin(angle))
                
                if 0 <= x < render_size[0] and 0 <= y < render_size[1]:
                    if t < 0.3:
                        color = center
                    elif t < 0.6:
                        color = tuple(int(core[j] * (1 - (t-0.3)/0.3) + rays[j] * ((t-0.3)/0.3)) for j in range(3))
                    else:
                        color = tuple(int(rays[j] * (1 - (t-0.6)/0.4) + glow[j] * ((t-0.6)/0.4)) for j in range(3))
                    
                    thickness = int(18 * (1 - t * 0.85))
                    alpha = int(255 * (1 - t * 0.7))
                    draw.ellipse([x - thickness, y - thickness, x + thickness, y + thickness],
                               fill=(*color, alpha), outline=None)
                    
                    if t < 0.65:
                        glow_size = thickness + 6
                        glow_alpha = int(140 * (1 - t))
                        glow_color = tuple(min(255, int(c * 1.2)) for c in color)
                        draw.ellipse([x - glow_size, y - glow_size, x + glow_size, y + glow_size],
                                   fill=(*glow_color, glow_alpha), outline=None)
        
        # LAYER 3: Expanding energy burst rings (using AI colors)
        for i in range(10, 0, -1):
            ring_pulse = 1.0 + (0.12 * math.sin(rotation * 2 + i * math.pi / 10))
            radius = int((cx * 0.65 - i * 10) * ring_pulse)
            
            if radius > 0:
                t = 1 - (i / 10)
                color = tuple(int(rays[j] * (1 - t) + glow[j] * t) for j in range(3))
                alpha = int(220 * (1 - i / 10))
                ring_color = (*color, alpha)
                draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius],
                           fill=None, outline=ring_color, width=5)
        
        # LAYER 4: Brilliant white-hot core (using AI center/core colors)
        core_size = 22
        core_pulse = int(core_size + 7 * pulse)
        
        draw.ellipse([cx - core_pulse - 12, cy - core_pulse - 12, cx + core_pulse + 12, cy + core_pulse + 12],
                    fill=(*glow, 90), outline=None)
        
        draw.ellipse([cx - core_pulse - 6, cy - core_pulse - 6, cx + core_pulse + 6, cy + core_pulse + 6],
                    fill=(*core, 120), outline=None)
        
        draw.ellipse([cx - core_size, cy - core_size, cx + core_size, cy + core_size],
                    fill=center, outline=outline, width=5)
        
        inner_size = 12
        draw.ellipse([cx - inner_size, cy - inner_size, cx + inner_size, cy + inner_size],
                    fill=center, outline=outline, width=3)
        
        hotspot_size = 6
        draw.ellipse([cx - hotspot_size, cy - hotspot_size, cx + hotspot_size, cy + hotspot_size],
                    fill=center, outline=None)
        
        # Apply mathematical rendering + AI optimization
        img = self._optimize_image(img, use_ai_optimization=True)
        result = img.resize(output_size, Image.LANCZOS)
        
        # Cache the result
        self._frame_cache[cache_key] = result.copy()
        return result
    
    def render_professional_white_hole(self, frame: int, total_frames: int = 16,
                                      output_size: Tuple[int, int] = (64, 64)) -> Image.Image:
        """Render PROFESSIONAL quality space-time rupture with explosive energy burst."""
        # Render at 4x resolution
        render_size = (output_size[0] * 4, output_size[1] * 4)
        img = Image.new('RGBA', render_size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        cx, cy = render_size[0] // 2, render_size[1] // 2
        rotation = (frame / total_frames) * (-2 * math.pi)  # Counter-rotation
        pulse = math.sin(frame * 2 * math.pi / total_frames)
        
        # LAYER 1: Explosive outer energy burst (yellow-white)
        for i in range(25, 0, -1):
            radius = int(cx * 0.95 - i * 3)
            if radius > 0:
                # Yellow to white gradient (explosive energy)
                hue = 0.15 - (i / 300)  # Yellow to warm white
                sat = 0.6 - (i / 50)
                val = 0.95 + (i / 500)
                color = self._hsv_to_rgb_cached(hue, sat, val)
                alpha = int(40 * (1 - i / 25))
                
                draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius],
                           fill=(*color, alpha), outline=None)
        
        # LAYER 2: Rotating energy rays (explosive burst)
        for ray_idx in range(24):
            angle = (2 * math.pi * ray_idx / 24) + rotation
            
            # Draw thick, explosive ray
            for dist in range(0, int(cx * 0.85), 3):
                t = dist / (cx * 0.85)
                
                x = int(cx + dist * math.cos(angle))
                y = int(cy + dist * math.sin(angle))
                
                if 0 <= x < render_size[0] and 0 <= y < render_size[1]:
                    # White-yellow-orange gradient (explosive energy)
                    if t < 0.3:
                        # Inner white hot
                        hue = 0.1
                        sat = 0.2
                        val = 1.0
                    elif t < 0.6:
                        # Mid yellow-orange
                        hue = 0.12 + (t * 0.08)
                        sat = 0.7 + (t * 0.2)
                        val = 0.95 - (t * 0.2)
                    else:
                        # Outer orange-red
                        hue = 0.08 + (t * 0.04)
                        sat = 0.8
                        val = 0.8 - (t * 0.4)
                    
                    rgb = colorsys.hsv_to_rgb(hue, sat, val)
                    color = tuple(int(c * 255) for c in rgb)
                    
                    # Tapered thickness
                    thickness = int(18 * (1 - t * 0.85))
                    alpha = int(255 * (1 - t * 0.7))
                    
                    # Main ray
                    draw.ellipse([x - thickness, y - thickness, x + thickness, y + thickness],
                               fill=(*color, alpha), outline=None)
                    
                    # Ray glow
                    if t < 0.65:
                        glow_size = thickness + 6
                        glow_alpha = int(140 * (1 - t))
                        glow_color = (255, int(220 * (1 - t * 0.3)), int(150 * (1 - t * 0.5)))
                        draw.ellipse([x - glow_size, y - glow_size, x + glow_size, y + glow_size],
                                   fill=(*glow_color, glow_alpha), outline=None)
        
        # LAYER 3: Expelled energy fragments (matter/energy being ejected)
        particle_count = 50
        for i in range(particle_count):
            angle = (2 * math.pi * i / particle_count) + rotation * 0.8
            dist_var = 0.3 + (i % 8) * 0.07
            radius = cx * dist_var
            
            x = int(cx + radius * math.cos(angle))
            y = int(cy + radius * math.sin(angle))
            
            if 0 <= x < render_size[0] and 0 <= y < render_size[1]:
                # Yellow-orange-white particles (expelled energy/matter)
                brightness = 0.6 + (i % 4) * 0.1
                # Mix yellow-orange based on distance
                t = dist_var - 0.3
                r = int(255 * brightness)
                g = int((200 + t * 50) * brightness)
                b = int((100 + t * 30) * brightness)
                color = (r, g, b)
                size = 2 + (i % 3)
                
                draw.ellipse([x - size, y - size, x + size, y + size],
                           fill=color, outline=None)
        
        # LAYER 4: Expanding energy burst rings
        for i in range(10, 0, -1):
            ring_pulse = 1.0 + (0.12 * math.sin(rotation * 2 + i * math.pi / 10))
            radius = int((cx * 0.65 - i * 10) * ring_pulse)
            
            if radius > 0:
                # Yellow-orange energy rings
                t = 1 - (i / 10)
                hue = 0.1 + (t * 0.05)  # Yellow to orange
                sat = 0.7 + (t * 0.2)
                val = 0.9
                color = self._hsv_to_rgb_cached(hue, sat, val)
                alpha = int(220 * (1 - i / 10))
                ring_color = (*color, alpha)
                
                draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius],
                           fill=None, outline=ring_color, width=5)
        
        # LAYER 5: Brilliant white-hot core
        core_size = 22
        core_pulse = int(core_size + 7 * pulse)
        
        # Outer core glow (yellow-orange)
        draw.ellipse([cx - core_pulse - 12, cy - core_pulse - 12, cx + core_pulse + 12, cy + core_pulse + 12],
                    fill=(255, 220, 150, 90), outline=None)
        
        # Mid core glow (warm white)
        draw.ellipse([cx - core_pulse - 6, cy - core_pulse - 6, cx + core_pulse + 6, cy + core_pulse + 6],
                    fill=(255, 240, 200, 120), outline=None)
        
        # Core (brilliant white)
        draw.ellipse([cx - core_size, cy - core_size, cx + core_size, cy + core_size],
                    fill=(255, 255, 255), outline=(255, 200, 100), width=5)
        
        # Inner brilliance (pure white hot)
        inner_size = 12
        draw.ellipse([cx - inner_size, cy - inner_size, cx + inner_size, cy + inner_size],
                    fill=(255, 255, 255), outline=(255, 230, 150), width=3)
        
        # Central hotspot
        hotspot_size = 6
        draw.ellipse([cx - hotspot_size, cy - hotspot_size, cx + hotspot_size, cy + hotspot_size],
                    fill=(255, 255, 255), outline=None)
        
        # Apply mathematical rendering + AI image optimization
        img = self._optimize_image(img, use_ai_optimization=True)
        img = img.resize(output_size, Image.LANCZOS)
        
        return img
    
    def render_professional_icon_with_design(self, design: Dict, output_size: Tuple[int, int] = QUD_TILE) -> Image.Image:
        """Render professional quality mutation icon using AI design."""
        sd_img = self._try_sd_static_icon(
            "mutation_icon",
            design or {},
            output_size,
            subject="space-time vortex mutation ability icon spiral singularity",
        )
        if sd_img is not None:
            return sd_img
        # Check frame cache
        design_hash = hash(str(sorted(design.items())))
        cache_key = (design_hash, 0, 1, output_size, 'icon')
        
        if cache_key in self._frame_cache:
            return self._frame_cache[cache_key].copy()
        
        # Extract colors from AI design
        cs = design.get('colorScheme', {})
        primary = self.hex_to_rgb(cs.get('primary', '#4a90e2'))
        secondary = self.hex_to_rgb(cs.get('secondary', '#7bb3f0'))
        glow = self.hex_to_rgb(cs.get('glow', '#00ffff'))
        void = self.hex_to_rgb(cs.get('void', '#000033'))
        outline = self.hex_to_rgb(cs.get('outline', '#1a1a4a'))
        
        # Render at 4x resolution
        render_size = (output_size[0] * 4, output_size[1] * 4)
        img = Image.new('RGBA', render_size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        cx, cy = render_size[0] // 2, render_size[1] // 2
        
        # LAYER 1: Outer glow (using AI glow color)
        for i in range(30, 0, -1):
            radius = int(cx * 0.95 - i * 3)
            if radius > 0:
                t = i / 30
                color = tuple(int(glow[j] * (1 - t) + primary[j] * t) for j in range(3))
                alpha = int(30 * (1 - t))
                draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius],
                           fill=(*color, alpha), outline=None)
        
        # LAYER 2: Spiral vortex symbol (using AI primary/secondary colors)
        for arm in range(2):
            arm_angle = (math.pi * arm)
            for i in range(150):
                t = i / 150
                angle = arm_angle + (t * 6 * math.pi)
                radius = t * (cx * 0.6) * math.exp(t * 0.3)
                x = int(cx + radius * math.cos(angle))
                y = int(cy + radius * math.sin(angle))
                
                if 0 <= x < render_size[0] and 0 <= y < render_size[1]:
                    color = tuple(int(primary[j] * (1 - t) + secondary[j] * t) for j in range(3))
                    thickness = int(8 * (1 - t * 0.7))
                    draw.ellipse([x - thickness, y - thickness, x + thickness, y + thickness],
                               fill=color, outline=None)
        
        # LAYER 3: Central symbol (using AI void/outline colors)
        core_size = 25
        draw.ellipse([cx - core_size, cy - core_size, cx + core_size, cy + core_size],
                    fill=void, outline=outline, width=6)
        
        inner_size = 15
        draw.ellipse([cx - inner_size, cy - inner_size, cx + inner_size, cy + inner_size],
                    fill=(0, 0, 0), outline=outline, width=3)
        
        # Apply mathematical rendering + AI optimization
        img = self._optimize_image(img, use_ai_optimization=True)
        result = img.resize(output_size, Image.LANCZOS)
        
        # Cache the result
        self._frame_cache[cache_key] = result.copy()
        return result
    
    def render_professional_icon(self, output_size: Tuple[int, int] = (96, 96)) -> Image.Image:
        """Render professional quality mutation icon."""
        # Render at 4x resolution
        render_size = (output_size[0] * 4, output_size[1] * 4)
        img = Image.new('RGBA', render_size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        cx, cy = render_size[0] // 2, render_size[1] // 2
        
        # LAYER 1: Outer glow (blue-white space-time distortion)
        for i in range(30, 0, -1):
            radius = int(cx * 0.95 - i * 3)
            if radius > 0:
                hue = 0.55 + (i / 400)
                sat = 0.3 - (i / 100)
                val = 0.4 + (i / 120)
                color = self._hsv_to_rgb_cached(hue, sat, val)
                alpha = int(30 * (1 - i / 30))
                draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius],
                           fill=(*color, alpha), outline=None)
        
        # LAYER 2: Spiral vortex symbol (simplified for icon)
        for arm in range(2):
            arm_angle = (math.pi * arm)
            for i in range(150):
                t = i / 150
                angle = arm_angle + (t * 6 * math.pi)
                radius = t * (cx * 0.6) * math.exp(t * 0.3)
                x = int(cx + radius * math.cos(angle))
                y = int(cy + radius * math.sin(angle))
                
                if 0 <= x < render_size[0] and 0 <= y < render_size[1]:
                    hue = 0.55 - (t * 0.1)
                    sat = 0.5 + (t * 0.3)
                    val = 0.5 + (t * 0.4)
                    rgb = colorsys.hsv_to_rgb(hue, sat, val)
                    color = tuple(int(c * 255) for c in rgb)
                    thickness = int(8 * (1 - t * 0.7))
                    draw.ellipse([x - thickness, y - thickness, x + thickness, y + thickness],
                               fill=color, outline=None)
        
        # LAYER 3: Central symbol (vortex core)
        core_size = 25
        draw.ellipse([cx - core_size, cy - core_size, cx + core_size, cy + core_size],
                    fill=(20, 40, 80), outline=(80, 150, 220), width=6)
        
        inner_size = 15
        draw.ellipse([cx - inner_size, cy - inner_size, cx + inner_size, cy + inner_size],
                    fill=(0, 0, 0), outline=(50, 100, 180), width=3)
        
        # Apply mathematical rendering + AI optimization
        img = self._optimize_image(img, use_ai_optimization=True)
        result = img.resize(output_size, Image.LANCZOS)
        
        # Cache the result (fallback icon path — no design hash)
        fallback_key = (0, 1, output_size, 'icon_fallback')
        self._frame_cache[fallback_key] = result.copy()
        return result
    
    def render_animated_spark(self, color: Tuple[int, int, int], frame: int, total_frames: int, size: Tuple[int, int]) -> Image.Image:
        """Render animated spark particle."""
        if QUD_PROCEDURAL_AVAILABLE and render_rich_particle is not None:
            return render_rich_particle("spark", color, frame, total_frames, size, seed=frame)
        img = Image.new('RGBA', size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        cx, cy = size[0] // 2, size[1] // 2
        rotation = (frame / total_frames) * (2 * math.pi)
        pulse = 0.7 + (0.3 * math.sin(frame * math.pi / 4))
        
        for i in range(4):
            angle = rotation + (i * math.pi / 2)
            length = int(6 * pulse)
            x = int(cx + length * math.cos(angle))
            y = int(cy + length * math.sin(angle))
            draw.line([cx, cy, x, y], fill=(*color, 200), width=2)
        
        center_size = int(2 * pulse)
        draw.ellipse([cx - center_size, cy - center_size, cx + center_size, cy + center_size],
                    fill=(*color, 255), outline=None)
        return img
    
    def render_animated_swirl(self, color: Tuple[int, int, int], frame: int, total_frames: int, size: Tuple[int, int]) -> Image.Image:
        """Render animated swirl particle."""
        if QUD_PROCEDURAL_AVAILABLE and render_rich_particle is not None:
            return render_rich_particle("swirl", color, frame, total_frames, size, seed=frame + 3)
        img = Image.new('RGBA', size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        cx, cy = size[0] // 2, size[1] // 2
        rotation = (frame / total_frames) * (2 * math.pi)
        
        for i in range(12):
            t = i / 12
            angle = rotation + (t * 4 * math.pi)
            radius = t * 6
            x = int(cx + radius * math.cos(angle))
            y = int(cy + radius * math.sin(angle))
            if 0 <= x < size[0] and 0 <= y < size[1]:
                alpha = int(255 * (1 - t))
                draw.ellipse([x - 1, y - 1, x + 1, y + 1], fill=(*color, alpha), outline=None)
        return img
    
    def render_animated_dot(self, color: Tuple[int, int, int], frame: int, total_frames: int, size: Tuple[int, int]) -> Image.Image:
        """Render animated pulsing dot particle."""
        if QUD_PROCEDURAL_AVAILABLE and render_rich_particle is not None:
            return render_rich_particle("dot", color, frame, total_frames, size, seed=frame + 5)
        img = Image.new('RGBA', size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        cx, cy = size[0] // 2, size[1] // 2
        pulse = 0.5 + (0.5 * math.sin(frame * math.pi / 4))
        dot_size = int(4 * pulse)
        glow_size = int(6 * pulse)
        alpha = int(100 * pulse)
        
        draw.ellipse([cx - glow_size, cy - glow_size, cx + glow_size, cy + glow_size],
                    fill=(*color, alpha), outline=None)
        draw.ellipse([cx - dot_size, cy - dot_size, cx + dot_size, cy + dot_size],
                    fill=(*color, 255), outline=None)
        return img
    
    def render_distortion_overlay(self, variant: int, size: Tuple[int, int]) -> Image.Image:
        """Render space-time distortion overlay."""
        if QUD_PROCEDURAL_AVAILABLE and render_rich_distortion_overlay is not None:
            return render_rich_distortion_overlay(None, variant, size, seed=variant)
        img = Image.new('RGBA', size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        cx, cy = size[0] // 2, size[1] // 2
        
        # Wavy distortion pattern (blue-white for space-time warping)
        for y in range(size[1]):
            wave = int(4 * math.sin((y + variant * 3) * math.pi / 8))
            x_start = cx + wave - 1
            x_end = cx + wave + 1
            alpha = int(60 * abs(math.sin(y * math.pi / size[1])))
            color = (100, 150, 220, alpha)  # Blue-white distortion
            draw.line([(x_start, y), (x_end, y)], fill=color, width=1)
        return img
    
    def render_distortion_overlay_with_design(self, design: Dict, variant: int, size: Tuple[int, int]) -> Image.Image:
        """Render space-time distortion overlay using AI design."""
        if QUD_PROCEDURAL_AVAILABLE and render_rich_distortion_overlay is not None:
            return render_rich_distortion_overlay(design, variant, size, seed=variant)
        cs = design.get('colorScheme', {})
        primary = self.hex_to_rgb(cs.get('primary', '#6496c8'))
        secondary = self.hex_to_rgb(cs.get('secondary', '#8cb4e0'))
        glow = self.hex_to_rgb(cs.get('glow', '#a0c0f0'))
        alpha_val = cs.get('alpha', 80)
        
        img = Image.new('RGBA', size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        cx, cy = size[0] // 2, size[1] // 2
        
        # Wavy distortion pattern using AI colors
        for y in range(size[1]):
            wave = int(4 * math.sin((y + variant * 3) * math.pi / 8))
            x_start = cx + wave - 1
            x_end = cx + wave + 1
            t = abs(math.sin(y * math.pi / size[1]))
            color = tuple(int(primary[j] * (1 - t) + glow[j] * t) for j in range(3))
            alpha = int(alpha_val * t)
            draw.line([(x_start, y), (x_end, y)], fill=(*color, alpha), width=1)
        return img
    
    def render_ability_icon(self, is_aggressive: bool, size: Tuple[int, int]) -> Image.Image:
        """Render ability icon (aggressive or defensive)."""
        if QUD_PROCEDURAL_AVAILABLE and render_rich_ability_icon is not None:
            return render_rich_ability_icon(None, is_aggressive, size)
        render_size = (size[0] * 2, size[1] * 2)
        img = Image.new('RGBA', render_size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        cx, cy = render_size[0] // 2, render_size[1] // 2
        
        if is_aggressive:
            # Orange-red diamond for aggressive
            color = (255, 150, 50)
            outline = (255, 100, 0)
            points = [
                (cx, cy - 20), (cx + 20, cy),
                (cx, cy + 20), (cx - 20, cy)
            ]
        else:
            # Blue circular shield for defensive
            color = (50, 150, 255)
            outline = (0, 100, 200)
            radius = 20
            draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius],
                        fill=(*color, 200), outline=outline, width=3)
            return img.resize(size, Image.LANCZOS)
        
        draw.polygon(points, fill=(*color, 200), outline=outline)
        return img.resize(size, Image.LANCZOS)
    
    def render_ability_icon_with_design(self, design: Dict, is_aggressive: bool, size: Tuple[int, int]) -> Image.Image:
        """Render ability icon using AI design (local SD preferred when server is up)."""
        label = "ability_aggressive" if is_aggressive else "ability_defensive"
        subject = (
            "aggressive offensive orange-red diamond ability icon"
            if is_aggressive
            else "defensive blue circular shield ability icon"
        )
        sd_img = self._try_sd_static_icon(label, design or {}, size, subject=subject)
        if sd_img is not None:
            return sd_img
        if QUD_PROCEDURAL_AVAILABLE and render_rich_ability_icon is not None:
            return render_rich_ability_icon(design, is_aggressive, size)
        cs = design.get('colorScheme', {})
        primary = self.hex_to_rgb(cs.get('primary', '#ff8000' if is_aggressive else '#3280ff'))
        secondary = self.hex_to_rgb(cs.get('secondary', '#ff4000' if is_aggressive else '#50a0ff'))
        glow = self.hex_to_rgb(cs.get('glow', '#ffa040' if is_aggressive else '#78c0ff'))
        outline = self.hex_to_rgb(cs.get('outline', '#cc0000' if is_aggressive else '#1a50cc'))
        
        render_size = (size[0] * 2, size[1] * 2)
        img = Image.new('RGBA', render_size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        cx, cy = render_size[0] // 2, render_size[1] // 2
        
        shape = design.get('shape', {})
        shape_type = shape.get('type', 'diamond' if is_aggressive else 'circle')
        
        if shape_type == 'diamond' or is_aggressive:
            # Diamond shape using AI colors
            points = [
                (cx, cy - 20), (cx + 20, cy),
                (cx, cy + 20), (cx - 20, cy)
            ]
            draw.polygon(points, fill=(*primary, 200), outline=outline, width=3)
            # Add glow
            for i in range(3):
                offset = i * 2
                glow_points = [
                    (cx, cy - 20 - offset), (cx + 20 + offset, cy),
                    (cx, cy + 20 + offset), (cx - 20 - offset, cy)
                ]
                alpha = int(50 * (1 - i / 3))
                draw.polygon(glow_points, fill=(*glow, alpha), outline=None)
        else:
            # Circle/shield shape using AI colors
            radius = 20
            draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius],
                        fill=(*primary, 200), outline=outline, width=3)
            # Add glow
            for i in range(3):
                glow_radius = radius + i * 2
                alpha = int(50 * (1 - i / 3))
                draw.ellipse([cx - glow_radius, cy - glow_radius, cx + glow_radius, cy + glow_radius],
                            fill=(*glow, alpha), outline=None)
        
        return img.resize(size, Image.LANCZOS)
    
    def render_warning_marker(self, size: Tuple[int, int]) -> Image.Image:
        """Render warning marker for pre-spawn indicators."""
        if QUD_PROCEDURAL_AVAILABLE and render_rich_warning_marker is not None:
            return render_rich_warning_marker(None, size)
        img = Image.new('RGBA', size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        cx, cy = size[0] // 2, size[1] // 2
        
        # Yellow-orange warning rings
        draw.ellipse([2, 2, size[0]-2, size[1]-2], 
                    fill=(255, 200, 0, 128), outline=(255, 150, 0), width=2)
        draw.ellipse([6, 6, size[0]-6, size[1]-6],
                    fill=(255, 180, 0, 100), outline=(255, 120, 0), width=1)
        draw.ellipse([cx - 5, cy - 5, cx + 5, cy + 5],
                    fill=(255, 100, 0), outline=(255, 200, 0), width=1)
        return img
    
    def render_warning_marker_with_design(self, design: Dict, size: Tuple[int, int]) -> Image.Image:
        """Render warning marker using AI design (local SD preferred when server is up)."""
        sd_img = self._try_sd_static_icon(
            "warning_marker",
            design or {},
            size,
            subject="yellow orange caution warning marker exclamation UI icon",
        )
        if sd_img is not None:
            return sd_img
        if QUD_PROCEDURAL_AVAILABLE and render_rich_warning_marker is not None:
            return render_rich_warning_marker(design, size)
        cs = design.get('colorScheme', {})
        primary = self.hex_to_rgb(cs.get('primary', '#ffc800'))
        secondary = self.hex_to_rgb(cs.get('secondary', '#ff9000'))
        glow = self.hex_to_rgb(cs.get('glow', '#ffe040'))
        outline = self.hex_to_rgb(cs.get('outline', '#cc8000'))
        
        img = Image.new('RGBA', size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        cx, cy = size[0] // 2, size[1] // 2
        
        # Warning rings using AI colors
        draw.ellipse([2, 2, size[0]-2, size[1]-2], 
                    fill=(*primary, 128), outline=outline, width=2)
        draw.ellipse([6, 6, size[0]-6, size[1]-6],
                    fill=(*secondary, 100), outline=outline, width=1)
        draw.ellipse([cx - 5, cy - 5, cx + 5, cy + 5],
                    fill=secondary, outline=glow, width=1)
        
        # Exclamation mark symbol
        symbol = design.get('symbol', {})
        if symbol.get('type') == 'exclamation':
            # Draw exclamation mark
            draw.rectangle([cx - 2, cy - 8, cx + 2, cy - 2], fill=glow)
            draw.ellipse([cx - 2, cy, cx + 2, cy + 4], fill=glow)
        
        return img
    
    def _generate_white_hole_ambient(self):
        """Generate ambient bed: low harmonic drone with slow pitch modulation and metallic undertones."""
        if not AUDIO_GENERATOR_AVAILABLE or np is None or self.audio_gen is None:
            return None
        
        duration = 10.0  # Loopable ambient
        t = np.linspace(0, duration, int(self.audio_gen.sample_rate * duration))
        
        # Low harmonic drone (base frequency ~60Hz)
        base_freq = 60
        signal = 0.3 * np.sin(2 * np.pi * base_freq * t)
        signal += 0.2 * np.sin(2 * np.pi * base_freq * 2 * t)  # Harmonic
        signal += 0.15 * np.sin(2 * np.pi * base_freq * 3 * t)  # Harmonic
        
        # Slow pitch modulation (vast energy implication)
        pitch_mod = 1.0 + 0.05 * np.sin(2 * np.pi * 0.1 * t)  # Very slow modulation
        signal = signal * pitch_mod
        
        # Metallic undertones (higher frequencies)
        metallic = 0.1 * np.sin(2 * np.pi * 200 * t)
        metallic += 0.05 * np.sin(2 * np.pi * 400 * t)
        signal += metallic
        
        # Subtle envelope to prevent clicks
        envelope = 0.5 + 0.5 * np.sin(2 * np.pi * 0.05 * t)  # Very slow fade
        signal *= envelope
        
        # Normalize
        signal = signal / (np.max(np.abs(signal)) + 1e-8) * 0.4
        
        return signal
    
    def _generate_white_hole_active(self):
        """Generate active voice: sharp whoosh with crystalline chimes and reversed reverb hits."""
        if not AUDIO_GENERATOR_AVAILABLE or np is None or self.audio_gen is None:
            return None
        
        duration = 2.0
        t = np.linspace(0, duration, int(self.audio_gen.sample_rate * duration))
        
        # Sharp whoosh (expulsion sound)
        whoosh_freq = 300
        whoosh = np.sin(2 * np.pi * whoosh_freq * t)
        whoosh += 0.6 * np.sin(2 * np.pi * whoosh_freq * 2 * t)
        whoosh_envelope = np.exp(-t * 3) * (1 - np.exp(-t * 20))
        whoosh *= whoosh_envelope
        
        # Crystalline chimes (high frequencies)
        chime_times = [0.1, 0.3, 0.5, 0.7]
        chimes = np.zeros(len(t))
        np.random.seed(42)  # Consistent chimes
        for chime_time in chime_times:
            chime_idx = int(chime_time * self.audio_gen.sample_rate)
            if chime_idx < len(t):
                chime_duration = 0.3
                chime_t = np.linspace(0, chime_duration, int(self.audio_gen.sample_rate * chime_duration))
                chime_freq = 800 + 200 * np.random.random()
                chime = np.sin(2 * np.pi * chime_freq * chime_t)
                chime *= np.exp(-chime_t * 5)
                if chime_idx + len(chime) <= len(chimes):
                    chimes[chime_idx:chime_idx + len(chime)] += chime * 0.3
        
        # Reversed reverb hits (time-weirdness)
        reverb_hits = np.zeros(len(t))
        np.random.seed(43)  # Consistent reverb
        for hit_time in [0.2, 0.6, 1.0]:
            hit_idx = int(hit_time * self.audio_gen.sample_rate)
            if hit_idx < len(t):
                hit_duration = 0.4
                hit_t = np.linspace(0, hit_duration, int(self.audio_gen.sample_rate * hit_duration))
                # Reverse envelope (starts quiet, gets loud - reversed reverb)
                hit = np.random.normal(0, 0.1, len(hit_t))
                hit_envelope = 1 - np.exp(-hit_t * 3)  # Reverse of normal
                hit *= hit_envelope
                if hit_idx + len(hit) <= len(reverb_hits):
                    reverb_hits[hit_idx:hit_idx + len(hit)] += hit
        
        signal = whoosh + chimes + reverb_hits
        
        # Normalize
        signal = signal / (np.max(np.abs(signal)) + 1e-8) * 0.7
        
        return signal
    
    def _generate_white_hole_ejection(self):
        """Generate ejection sound: whoosh with Doppler effect (pitch sweep)."""
        if not AUDIO_GENERATOR_AVAILABLE or np is None or self.audio_gen is None:
            return None
        
        duration = 1.5
        t = np.linspace(0, duration, int(self.audio_gen.sample_rate * duration))
        
        # Doppler sweep: pitch starts high, drops (object moving away)
        start_freq = 600
        end_freq = 200
        freq_sweep = start_freq + (end_freq - start_freq) * (t / duration)
        
        # Whoosh with frequency sweep
        signal = np.sin(2 * np.pi * freq_sweep * t)
        signal += 0.5 * np.sin(2 * np.pi * freq_sweep * 2 * t)
        
        # Envelope: quick attack, slower decay
        envelope = np.exp(-t * 2) * (1 - np.exp(-t * 30))
        signal *= envelope
        
        # Add blue-shifted particle sounds
        particle_times = [0.1, 0.3, 0.5, 0.7, 0.9]
        np.random.seed(44)  # Consistent particles
        for particle_time in particle_times:
            particle_idx = int(particle_time * self.audio_gen.sample_rate)
            if particle_idx < len(t):
                particle_duration = 0.2
                particle_t = np.linspace(0, particle_duration, int(self.audio_gen.sample_rate * particle_duration))
                particle_freq = 1000 + 500 * np.random.random()  # High frequency (blue-shifted)
                particle = np.sin(2 * np.pi * particle_freq * particle_t)
                particle *= np.exp(-particle_t * 8)
                if particle_idx + len(particle) <= len(signal):
                    signal[particle_idx:particle_idx + len(particle)] += particle * 0.2
        
        # Normalize
        signal = signal / (np.max(np.abs(signal)) + 1e-8) * 0.6
        
        return signal
    
    def generate_all(self):
        """Generate all professional quality assets using AI design + 4x supersampling."""
        print("=" * 70)
        print("PROFESSIONAL QUALITY VORTEX ASSET GENERATOR")
        print("MULTI-AI POWERED: MATH AI + VISUAL AI")
        print("=" * 70)
        print("• Math-focused AI (analysis): Design specs (geometry, patterns, math)")
        print("• Visual AI (wizardlm-uncensored): Aesthetics optimization")
        print("• Mathematical rendering: Precise geometry, spirals, rotations")
        print("• 4x supersampling with LANCZOS anti-aliasing")
        print("• 16 frames per animation for ultra-smooth playback")
        print()
        
        # Get AI designs from Ollama using multi-AI support
        print("Phase 1: Getting AI design specifications (multi-AI)...")
        print("  • Master art direction: unified palette across all assets")
        print("  • Math-focused AI: geometry and pattern specs")
        print("  • Visual AI: aesthetics and particle colors")
        print("  • SD3 design drafts: optional palette hints from DesignDrafts/")
        print()

        if self.quality_pipeline is not None:
            self.quality_pipeline.get_master_art_direction(call_ollama)
        
        # Use math-focused AI (analysis) for design specifications
        icon_design = self._call_ollama_design("""Design a Space-Time Vortex icon for Caves of Qud.
Return ONLY valid JSON:
{
  "symbol": {"shape": "spiral singularity", "complexity": "high"},
  "colorScheme": {
    "primary": "#4a90e2",
    "secondary": "#7bb3f0", 
    "glow": "#00ffff",
    "void": "#000033",
    "outline": "#1a1a4a"
  }
}
Use blue/purple colors for mental mutation. Return JSON ONLY.""", "icon", use_math_ai=True, draft_key="icon")
        
        black_hole_design = self._call_ollama_design("""Design a space-time vortex (black hole) visual.
Return ONLY valid JSON:
{
  "shape": {"type": "spiral singularity", "spiralArms": 3, "spiralDirection": "clockwise"},
  "colorScheme": {
    "void": "#000000",
    "eventHorizon": "#142850",
    "accretionDisk": "#2a4a80",
    "glow": "#4a80c0",
    "outline": "#1a3050"
  }
}
Use dark blue/black colors for space-time distortion. Return JSON ONLY.""", "black hole", use_math_ai=True, draft_key="black_hole")
        
        white_hole_design = self._call_ollama_design("""Design a space-time rupture (white hole) visual.
Return ONLY valid JSON:
{
  "shape": {"type": "outward spiral rupture", "spiralArms": 2, "spiralDirection": "counterclockwise"},
  "colorScheme": {
    "center": "#ffffff",
    "core": "#fff8e0",
    "rays": "#ffd080",
    "glow": "#ffb040",
    "outline": "#ff8000"
  }
}
Use white/yellow/orange. Prefer hooked/outward SPIRALS — never radial sawblade rays or gear teeth. Return JSON ONLY.""", "white hole", use_math_ai=True, draft_key="white_hole")
        
        # Batch particle designs (1 Ollama call instead of 6)
        print("Getting batch particle designs + remaining asset specs...")
        print()
        
        particle_designs = {}
        if self.quality_pipeline is not None:
            particle_designs = self.quality_pipeline.get_batch_particle_designs(call_ollama)
        else:
            particle_configs = [
                ("spark", "blue"), ("spark", "cyan"), ("swirl", "blue"),
                ("swirl", "white"), ("dot", "yellow"), ("dot", "orange"),
            ]
            for ptype, color_name in particle_configs:
                particle_designs[(ptype, color_name)] = self._call_ollama_design(
                    f"""Design a {ptype} particle ({color_name}) for Space-Time Vortex.
Return ONLY valid JSON with colorScheme.primary, colorScheme.glow, colorScheme.outline.""",
                    f"{ptype}_{color_name} particle", use_math_ai=False
                )
        
        # Distortion overlay designs
        distortion_design = self._call_ollama_design("""Design a space-time distortion overlay texture.
Return ONLY valid JSON:
{
  "colorScheme": {
    "primary": "#6496c8",
    "secondary": "#8cb4e0",
    "glow": "#a0c0f0",
    "alpha": 80
  },
  "pattern": {
    "type": "wavy",
    "intensity": "medium",
    "frequency": "high"
  }
}
Use blue-white colors for space-time warping effect. Return JSON ONLY.""", "distortion overlay", use_math_ai=False)
        
        # Ability icon designs
        aggressive_icon_design = self._call_ollama_design("""Design an aggressive ability icon for Space-Time Vortex.
Return ONLY valid JSON:
{
  "shape": {
    "type": "diamond",
    "style": "sharp"
  },
  "colorScheme": {
    "primary": "#ff8000",
    "secondary": "#ff4000",
    "glow": "#ffa040",
    "outline": "#cc0000"
  }
}
Use orange/red colors for aggressive/offensive mode. Return JSON ONLY.""", "aggressive ability icon", use_math_ai=False)
        
        defensive_icon_design = self._call_ollama_design("""Design a defensive ability icon for Space-Time Vortex.
Return ONLY valid JSON:
{
  "shape": {
    "type": "circle",
    "style": "shield"
  },
  "colorScheme": {
    "primary": "#3280ff",
    "secondary": "#50a0ff",
    "glow": "#78c0ff",
    "outline": "#1a50cc"
  }
}
Use blue colors for defensive/protective mode. Return JSON ONLY.""", "defensive ability icon", use_math_ai=False)
        
        # Warning marker design
        warning_design = self._call_ollama_design("""Design a warning marker for space-time vortex pre-spawn indicator.
Return ONLY valid JSON:
{
  "colorScheme": {
    "primary": "#ffc800",
    "secondary": "#ff9000",
    "glow": "#ffe040",
    "outline": "#cc8000"
  },
  "symbol": {
    "type": "exclamation",
    "style": "bold"
  }
}
Use yellow/orange colors for warning/caution. Return JSON ONLY.""", "warning marker", use_math_ai=False)

        if self.quality_pipeline is not None:
            self.quality_pipeline.save_design_specs({
                "icon": icon_design,
                "black_hole": black_hole_design,
                "white_hole": white_hole_design,
                "particles": {f"{k[0]}_{k[1]}": v for k, v in particle_designs.items()},
                "distortion": distortion_design,
                "aggressive_icon": aggressive_icon_design,
                "defensive_icon": defensive_icon_design,
                "warning": warning_design,
            })
        
        print()
        print("Phase 2: Mathematical rendering with AI design specs...")
        print("  (Using precise math for geometry, spirals, rotations)")
        print()
        print("Phase 3: Image optimization with visual AI (wizardlm-uncensored)...")
        print()
        
        # Track generation progress and errors
        generation_errors = []
        
        # Generate mutation icon (using AI design)
        icon = None
        try:
            print("0. Rendering MUTATION ICON (16x24 truecolor, AI-designed)...")
            icon = self.render_professional_icon_with_design(icon_design, QUD_TILE)
            icon_path = self.textures_path / "Space-Time Vortex_icon.png"
            self._save_sprite(icon, icon_path)
            self._save_sprite(icon, self.visuals_path / "Space-Time Vortex_icon.png")
            if not icon_path.exists() or icon_path.stat().st_size == 0:
                raise IOError(f"Failed to save icon: {icon_path}")
            print(f"   [OK] Created: {icon_path.name}")
        except Exception as e:
            error_msg = f"Failed to generate mutation icon: {e}"
            print(f"   [ERROR] {error_msg}")
            generation_errors.append(error_msg)
        finally:
            if icon is not None:
                icon.close()
                del icon
        print("   [OK] Icon saved")
        print()
        
        # Generate black hole animation (using AI design + temporal smoothing)
        main = None
        try:
            print("1. Rendering BLACK HOLE (16 frames, 16x24 truecolor, AI-designed)...")
            target_size = QUD_TILE
            bh_frames = []
            for i in range(16):
                bh_frames.append(
                    self.render_professional_black_hole_with_design(black_hole_design, i, 16, target_size)
                )
            if self.quality_pipeline is not None and self.quality == "full":
                from vortex_quality import smooth_animation_frames
                bh_frames = smooth_animation_frames(bh_frames, blend=0.10)
            main = bh_frames[8].copy() if len(bh_frames) > 8 else bh_frames[0].copy()
            for i, frame in enumerate(bh_frames):
                self._save_sprite(frame, self.textures_path / f"BlackHole_frame{i:02d}.png")
                frame.close()
                if i % 4 == 3:
                    print(f"   [OK] Frames {i-2:02d}-{i:02d} rendered")
            self._save_sprite(main, self.textures_path / "BlackHole_visual.png")
            self._save_sprite(main, self.visuals_path / "BlackHole_visual.png")
            print("   [OK] Main visual saved")
        except Exception as e:
            error_msg = f"Failed to generate black hole animation: {e}"
            print(f"   [ERROR] {error_msg}")
            generation_errors.append(error_msg)
        finally:
            if main is not None:
                main.close()
                del main
        
        # Generate white hole animation (using AI design + temporal smoothing)
        main = None
        try:
            print()
            print("2. Rendering WHITE HOLE (16 frames, 16x24 truecolor, AI-designed)...")
            wh_frames = []
            for i in range(16):
                wh_frames.append(
                    self.render_professional_white_hole_with_design(white_hole_design, i, 16, target_size)
                )
            if self.quality_pipeline is not None and self.quality == "full":
                from vortex_quality import smooth_animation_frames
                wh_frames = smooth_animation_frames(wh_frames, blend=0.10)
            main = wh_frames[8].copy() if len(wh_frames) > 8 else wh_frames[0].copy()
            for i, frame in enumerate(wh_frames):
                self._save_sprite(frame, self.textures_path / f"WhiteHole_frame{i:02d}.png")
                frame.close()
                if i % 4 == 3:
                    print(f"   [OK] Frames {i-2:02d}-{i:02d} rendered")
            self._save_sprite(main, self.textures_path / "WhiteHole_visual.png")
            self._save_sprite(main, self.visuals_path / "WhiteHole_visual.png")
            print("   [OK] Main visual saved")
        except Exception as e:
            error_msg = f"Failed to generate white hole animation: {e}"
            print(f"   [ERROR] {error_msg}")
            generation_errors.append(error_msg)
        finally:
            if main is not None:
                main.close()
                del main
        
        # Generate animated particles (using AI designs)
        print()
        print("3. Rendering ANIMATED PARTICLES (8 frames each, 16x16, AI-designed)...")
        particle_count = 0
        for (ptype, color_name), design in particle_designs.items():
            cs = design.get('colorScheme', {})
            primary = self.hex_to_rgb(cs.get('primary', '#6496c8'))
            p_frames = []
            for frame_idx in range(8):
                if ptype == "spark":
                    p_frames.append(self.render_animated_spark(primary, frame_idx, 8, (16, 16)))
                elif ptype == "swirl":
                    p_frames.append(self.render_animated_swirl(primary, frame_idx, 8, (16, 16)))
                else:
                    p_frames.append(self.render_animated_dot(primary, frame_idx, 8, (16, 16)))
            if self.quality_pipeline is not None and self.quality == "full":
                from vortex_quality import smooth_animation_frames
                p_frames = smooth_animation_frames(p_frames, blend=0.08)
            for frame_idx, particle in enumerate(p_frames):
                particle_path = self.textures_path / f"VortexParticle_{ptype}_{color_name}_frame{frame_idx:02d}.png"
                self._save_sprite(particle, particle_path)
                particle.close()
                particle_count += 1
        print(f"   [OK] Created {particle_count} particle frames (6 types x 8 frames, AI-designed)")
        
        # Generate distortion overlays (using AI design)
        print()
        print("4. Rendering DISTORTION OVERLAYS (32x32, AI-designed)...")
        for i in range(3):
            distortion = None
            try:
                distortion = self.render_distortion_overlay_with_design(distortion_design, i, QUD_TILE)
                distortion_path = self.textures_path / f"VortexDistortion_{i:02d}.png"
                self._save_sprite(distortion, distortion_path)
            finally:
                if distortion is not None:
                    distortion.close()
                    del distortion
        print("   [OK] Created 3 distortion overlays (AI-designed)")
        
        # Generate ability icons (using AI designs)
        print()
        print("5. Rendering ABILITY ICONS (64x64, AI-designed)...")
        aggressive_icon = None
        defensive_icon = None
        try:
            aggressive_icon = self.render_ability_icon_with_design(aggressive_icon_design, True, QUD_TILE)
            self._save_sprite(aggressive_icon, self.textures_path / "VortexAbility_Aggressive.png")
            defensive_icon = self.render_ability_icon_with_design(defensive_icon_design, False, QUD_TILE)
            self._save_sprite(defensive_icon, self.textures_path / "VortexAbility_Defensive.png")
            print("   [OK] Created 2 ability icons (AI-designed)")
        finally:
            if aggressive_icon is not None:
                aggressive_icon.close()
                del aggressive_icon
            if defensive_icon is not None:
                defensive_icon.close()
                del defensive_icon
        
        # Generate warning marker (using AI design)
        print()
        print("6. Rendering WARNING MARKER (64x64, AI-designed)...")
        warning = None
        try:
            warning = self.render_warning_marker_with_design(warning_design, QUD_TILE)
            self._save_sprite(warning, self.textures_path / "VortexWarning_marker.png")
            print("   [OK] Created warning marker (AI-designed)")
        finally:
            if warning is not None:
                warning.close()
                del warning
        
        # Generate white hole sounds (optional, if audio generator available)
        sounds_created = 0
        if AUDIO_GENERATOR_AVAILABLE and self.audio_gen and np is not None and sf is not None:
            print()
            print("7. Generating WHITE HOLE SOUNDS (optional)...")
            try:
                # Generate white hole ambient sound
                ambient_sound = self._generate_white_hole_ambient()
                if ambient_sound is not None:
                    ambient_path = self.sounds_path / "WhiteHole_ambient.ogg"
                    sf.write(str(ambient_path), ambient_sound, self.audio_gen.sample_rate)
                    print(f"   ✓ Created: {ambient_path.name}")
                    sounds_created += 1
                
                # Generate white hole active sound
                active_sound = self._generate_white_hole_active()
                if active_sound is not None:
                    active_path = self.sounds_path / "WhiteHole_active.ogg"
                    sf.write(str(active_path), active_sound, self.audio_gen.sample_rate)
                    print(f"   ✓ Created: {active_path.name}")
                    sounds_created += 1
                
                # Generate white hole ejection sound
                ejection_sound = self._generate_white_hole_ejection()
                if ejection_sound is not None:
                    ejection_path = self.sounds_path / "WhiteHole_ejection.ogg"
                    sf.write(str(ejection_path), ejection_sound, self.audio_gen.sample_rate)
                    print(f"   ✓ Created: {ejection_path.name}")
                    sounds_created += 1
                
                if sounds_created > 0:
                    print(f"   ✓ Created {sounds_created} white hole sound(s)")
            except Exception as e:
                print(f"   [WARN] Audio generation failed: {e}")
                print("   Continuing without audio files...")
                import traceback
                traceback.print_exc()
        elif not AUDIO_GENERATOR_AVAILABLE:
            print()
            print("7. Skipping sound generation (audio generator not available)")
            print("   [INFO] Install dependencies: pip install numpy soundfile")
        
        print()
        print("=" * 70)
        # Clear caches after generation to free memory
        # Also close any cached images before clearing
        for cached_img in self._frame_cache.values():
            try:
                cached_img.close()
            except:
                pass
        for cached_img in self._gradient_cache.values():
            try:
                cached_img.close()
            except:
                pass
        
        self._color_cache.clear()
        self._hsv_cache.clear()
        self._frame_cache.clear()
        self._gradient_cache.clear()
        
        # Force garbage collection if available
        try:
            import gc
            gc.collect()
        except:
            pass
        
        total_assets = 1 + 17 + 17 + particle_count + 3 + 2 + 1 + sounds_created
        if generation_errors:
            print(f"⚠ PARTIAL COMPLETE - {total_assets} assets generated with {len(generation_errors)} error(s)")
        else:
            print(f"✓ COMPLETE - {total_assets} professional-quality assets generated")
        print("  • 1 mutation icon (96x96)")
        print("  • 16 black hole frames + 1 visual (64x64)")
        print("  • 16 white hole frames + 1 visual (64x64)")
        print(f"  • {particle_count} animated particle frames (16x16)")
        print("  • 3 distortion overlays (32x32)")
        print("  • 2 ability icons (64x64)")
        print("  • 1 warning marker (64x64)")
        if sounds_created > 0:
            print(f"  • {sounds_created} white hole sound(s) (optional)")
        print("=" * 70)
        
        if generation_errors:
            print()
            print("⚠ Generation Errors:")
            for i, error in enumerate(generation_errors, 1):
                print(f"  {i}. {error}")
            print()
        
        print()
        print("Features:")
        print("  • 4x supersampling with LANCZOS downscaling")
        print("  • HSV color space for vibrant gradients")
        print("  • Multiple layered effects (5 layers per frame)")
        print("  • Particle systems and accretion disks")
        print("  • Professional smooth filtering")
        print("  • 16-frame ultra-smooth animation")
        print()
        
        if generation_errors:
            raise RuntimeError(f"Generation completed with {len(generation_errors)} error(s). See details above.")

        # Wire generated PNGs into mod XML (ObjectBlueprints, Mutations.xml)
        print()
        print("Phase 4: Applying mod integration (XML tile references)...")
        try:
            from vortex_mod_integration import apply_mod_integration
            found, integration_msgs = apply_mod_integration(self.mod_path)
            for msg in integration_msgs:
                print(f"   - {msg}")
            if found:
                print("   ✓ Mod XML updated for generated textures")
            else:
                print("   [WARN] No textures detected for integration")
        except Exception as e:
            print(f"   [WARN] Mod integration skipped: {e}")

        # Bridge Textures/ → Assets/Resources + .meta (Editor not required)
        print()
        print("Phase 5: Unity texture export (.meta)...")
        try:
            from export_textures_to_unity import export_textures
            n = export_textures(self.mod_path, overwrite_meta=False)
            print(f"   ✓ Exported {n} textures into Assets/Resources")
        except Exception as e:
            print(f"   [WARN] Unity texture bridge skipped: {e}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Unified Space-Time Vortex Asset Generator (AI-Powered)",
        epilog="This generator includes all improvements: 4x supersampling, 16-frame animations, "
               "multi-AI support, audio generation, and high-resolution support."
    )
    parser.add_argument("mod_path", help="Path to mod directory")
    parser.add_argument("--ollama-url", default="http://localhost:11434",
                       help="Ollama server URL (default: http://localhost:11434)")
    parser.add_argument("--model", default=None,
                       help="Specific Ollama model to use (default: auto-select)")
    parser.add_argument("--integration-only", action="store_true",
                       help="Only run vortex_mod_integration.py (no asset generation)")
    parser.add_argument("--no-cache", action="store_true",
                       help="Skip Ollama design cache (force fresh AI calls)")
    parser.add_argument("--no-drafts", action="store_true",
                       help="Ignore SD3 design drafts in DesignDrafts/")
    parser.add_argument("--quality", choices=["fast", "mechanical", "full"], default="full",
                       help="Export quality: fast (minimal), mechanical (validate), full (smooth+IM)")
    parser.add_argument("--reprocess-existing", action="store_true",
                       help="Re-polish PNGs in Textures/ (sharpen, validate, ImageMagick) without Ollama")
    args = parser.parse_args()
    
    mod_path = Path(args.mod_path)
    if not mod_path.exists():
        print(f"ERROR: Mod path not found: {mod_path}")
        print(f"Please ensure the mod directory exists before running the generator.")
        return 1
    
    if not mod_path.is_dir():
        print(f"ERROR: Mod path is not a directory: {mod_path}")
        return 1

    if args.integration_only:
        try:
            from vortex_mod_integration import apply_mod_integration
            found, messages = apply_mod_integration(mod_path)
            for msg in messages:
                print(f"  - {msg}")
            return 0
        except Exception as e:
            print(f"ERROR: {e}")
            return 1

    if args.reprocess_existing:
        try:
            from vortex_quality import save_qud_sprite, VortexQualityPipeline
            textures = mod_path / "Textures"
            if not textures.exists():
                print("ERROR: No Textures/ folder found")
                return 1
            pipeline = VortexQualityPipeline(mod_path, use_cache=False, quality=args.quality)
            count = 0
            for png in sorted(textures.glob("*.png")):
                with Image.open(png) as img:
                    if pipeline.export_sprite(img, png):
                        count += 1
                        print(f"  [OK] {png.name}")
            print(f"\nReprocessed {count} PNG(s)")
            from vortex_mod_integration import apply_mod_integration
            apply_mod_integration(mod_path)
            return 0
        except Exception as e:
            print(f"ERROR: {e}")
            return 1
    
    try:
        print("=" * 70)
        print("Unified Space-Time Vortex Asset Generator")
        print("=" * 70)
        print()
        
        generator = ProfessionalVortexGenerator(
            mod_path,
            ollama_url=args.ollama_url,
            model=args.model,
            use_cache=not args.no_cache,
            use_drafts=not args.no_drafts,
            quality=args.quality,
        )
        generator.generate_all()
        
        print()
        print("=" * 70)
        print("Generation complete!")
        print("=" * 70)
        return 0
    except KeyboardInterrupt:
        print("\n\nGeneration cancelled by user.")
        return 130
    except RuntimeError as e:
        print(f"\nERROR: {e}")
        print("\nTroubleshooting:")
        print("  1. Ensure Ollama is running: ollama serve")
        print("  2. Check that required models are installed")
        print("  3. Verify the mod path is correct")
        return 1
    except ImportError as e:
        print(f"\nERROR: Missing required dependency: {e}")
        print("\nPlease install required packages:")
        print("  pip install pillow")
        if "numpy" in str(e) or "soundfile" in str(e):
            print("  pip install numpy soundfile  # (optional, for audio generation)")
        return 1
    except Exception as e:
        print(f"\nERROR: Unexpected error occurred: {e}")
        import traceback
        print("\nFull traceback:")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
