#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Space Whale Texture Generator for Rigging
Generates proper textures compatible with Blender rigging system for final spritesheet rendering.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple
import math
from concurrent.futures import ThreadPoolExecutor, as_completed
from multiprocessing import cpu_count
import threading

# Fix Windows console encoding for Unicode characters
if sys.platform == 'win32':
    try:
        # Try to set UTF-8 encoding for console output
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, ValueError):
        # Fallback: use ASCII-safe characters
        pass

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageChops, ImageEnhance
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("WARNING: PIL/Pillow not available. Install with: pip install Pillow")
    print("Texture generation will be limited.")

# Shared AI pipeline (SD3.5 :1338 via tx_ai_pipeline / ai_resources).
# Diffuse comes from SD when the image stage is up; other maps stay procedural
# because SD cannot produce reliable tangent-space normals / data maps.
_TX = Path(__file__).resolve().parent
if str(_TX) not in sys.path:
    sys.path.insert(0, str(_TX))
try:
    import tx_ai_pipeline as tx  # type: ignore
    _SD_AVAILABLE = True
except Exception:
    tx = None  # type: ignore
    _SD_AVAILABLE = False
detect_server = None  # type: ignore
generate_image = None  # type: ignore

# Quality tiers: base square texture size + SD sampling budget. Defaults stay
# VRAM/time friendly (standard=512) so full asset batches finish; bump to
# high/ultra for hero assets. Sizes are /16 (SD3.5 snaps to /16 anyway).
TEXTURE_QUALITY = {
    "draft":    {"size": 384,  "steps": 18, "guidance": 6.5},
    "standard": {"size": 512,  "steps": 26, "guidance": 7.0},
    "high":     {"size": 768,  "steps": 32, "guidance": 7.0},
    "ultra":    {"size": 1024, "steps": 40, "guidance": 7.5},
}

# Content-aware sizing: bigger structural modules deserve bigger textures;
# small appendages can stay small to save VRAM/time. Multiplies the tier size.
_LARGE_MODULE_HINTS = ("head", "body", "core", "hull", "torso", "main", "mid", "chest")
_SMALL_MODULE_HINTS = ("fin", "drone", "spike", "antenna", "sensor", "tip", "vent", "small")

# The SD server serializes generation on one GPU, so flooding it with 32 parallel
# requests just holds sockets. Cap concurrent SD calls (procedural maps stay
# fully parallel). Override with SD_TEXTURE_CONCURRENCY.
_SD_SEMAPHORE = threading.Semaphore(max(1, int(os.environ.get("SD_TEXTURE_CONCURRENCY", "1"))))


class SpaceWhaleTextureGenerator:
    """Generates textures for space whale rigging system."""
    
    def __init__(self, visual_registry_path: str, skinning_registry_path: str):
        with open(visual_registry_path, 'r', encoding='utf-8') as f:
            self.visual_registry = json.load(f)
        
        with open(skinning_registry_path, 'r', encoding='utf-8') as f:
            self.skinning_registry = json.load(f)
        
        self.palette = self.visual_registry.get('visualLanguage', {}).get('colorPalettes', {}).get('primary', {})
        self.materials = self.visual_registry.get('visualLanguage', {}).get('materials', {})
        self.bone_structure = self.skinning_registry.get('boneStructure', {})

        # SD diffuse config (set by configure_sd(); safe procedural defaults).
        self.use_sd = False
        self.sd_api_url = None
        self.quality = "standard"
        self.base_size = TEXTURE_QUALITY["standard"]["size"]
        self.sd_steps = TEXTURE_QUALITY["standard"]["steps"]
        self.sd_guidance = TEXTURE_QUALITY["standard"]["guidance"]
        self.max_size = 1024
        self.min_size = 256

    def configure_sd(self, *, use_sd: bool, api_url=None, quality: str = "standard",
                     base_size=None, sd_steps=None, guidance=None,
                     max_size: int = 1024, min_size: int = 256):
        """Set SD/quality options. base_size overrides the tier size when given."""
        tier = TEXTURE_QUALITY.get(quality, TEXTURE_QUALITY["standard"])
        self.use_sd = bool(use_sd)
        self.sd_api_url = api_url
        self.quality = quality
        self.base_size = int(base_size if base_size else tier["size"])
        self.sd_steps = int(sd_steps if sd_steps else tier["steps"])
        self.sd_guidance = float(guidance if guidance else tier["guidance"])
        self.max_size = int(max_size)
        self.min_size = int(min_size)

    def _sd_config_dict(self) -> Dict:
        """Scalar config snapshot for thread-local copies (deep-copy safe)."""
        return {
            "use_sd": self.use_sd, "sd_api_url": self.sd_api_url, "quality": self.quality,
            "base_size": self.base_size, "sd_steps": self.sd_steps,
            "sd_guidance": self.sd_guidance, "max_size": self.max_size, "min_size": self.min_size,
        }

    def hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    @staticmethod
    def _lerp_rgb(a: Tuple[int, int, int], b: Tuple[int, int, int], t: float) -> Tuple[int, int, int]:
        return tuple(int(ca + (cb - ca) * t) for ca, cb in zip(a, b))

    def _multi_octave_mottle(self, size: Tuple[int, int], seed: int) -> "Image.Image":
        """Fast multi-octave value noise ('L' image) built by upscaling small
        random grids — gives organic, layered blotches without slow per-pixel
        Python loops. Used as a per-pixel blend mask for the diffuse map."""
        import random
        rng = random.Random(seed)
        mottle = Image.new('L', size, 128)
        for cells, weight in ((5, 0.55), (13, 0.30), (37, 0.20), (97, 0.12)):
            small = Image.new('L', (cells, cells))
            small.putdata([rng.randint(0, 255) for _ in range(cells * cells)])
            up = small.resize(size, Image.Resampling.BILINEAR)
            mottle = Image.blend(mottle, up, weight)
        return mottle.filter(ImageFilter.GaussianBlur(radius=max(1, size[0] // 256)))

    def _snap16(self, n: int) -> int:
        n = int(round(n / 16.0)) * 16
        return max(self.min_size, min(self.max_size, n))

    def resolve_module_size(self, module_config: Dict) -> Tuple[int, int]:
        """Content-aware square texture size: bigger modules -> bigger textures."""
        blob = f"{module_config.get('name', '')} {module_config.get('type', '')}".lower()
        scale = 0.75
        if any(h in blob for h in _LARGE_MODULE_HINTS):
            scale = 1.0
        elif any(h in blob for h in _SMALL_MODULE_HINTS):
            scale = 0.5
        # Explicit override wins: a module may declare its own texelScale.
        try:
            scale = float(module_config.get('texelScale', scale))
        except (TypeError, ValueError):
            pass
        s = self._snap16(self.base_size * scale)
        return (s, s)

    def _build_sd_prompt(self, module_type: str) -> Tuple[str, str]:
        """Prompt/negative for an SD diffuse skin from palette + material data."""
        base = self.palette.get('baseColor', '#1a2a3a')
        carapace = self.palette.get('carapaceColor', '#2a3a4a')
        vein = self.palette.get('veinColor', '#66ccff')
        skin = ""
        try:
            props = (self.materials.get('bioluminescentSkin', {}) or {}).get('properties', {})
            if isinstance(props, dict):
                skin = " ".join(str(v) for v in props.values() if isinstance(v, str))[:80]
        except Exception:
            skin = ""
        # 'no text' front-loaded; flat/even lighting + seamless so it bakes as a
        # base-color map, not lit concept art. Colors described by hex hints.
        prompt = (
            f"no text, no logo, no watermark, seamless tileable texture, "
            f"organic bioluminescent creature carapace skin, {module_type} section, "
            f"base color {base}, plating {carapace}, glowing veins {vein}, "
            f"{skin}, wet leathery scales, even flat lighting, top-down, "
            f"PBR base color map, high detail"
        )
        negative = (
            "text, logo, watermark, letters, ui, frame, border, seams, "
            "harsh shadows, strong directional light, specular glare, vignette, "
            "blurry, lowres, jpeg artifacts, photograph, hands, face"
        )
        return prompt, negative

    def generate_diffuse_texture_sd(self, size: Tuple[int, int], module_type: str):
        """SD diffuse -> PIL Image, or None on any failure (caller falls back)."""
        if not (self.use_sd and _SD_AVAILABLE and tx and PIL_AVAILABLE):
            return None
        import tempfile
        prompt, negative = self._build_sd_prompt(module_type)
        seed = (abs(hash(module_type)) % 100000) + 17
        w, h = size
        tmp = Path(tempfile.gettempdir()) / f"sw_sd_{module_type}_{seed}_{w}x{h}.png"
        try:
            with _SD_SEMAPHORE:
                path = tx.generate_image(
                    prompt,
                    tmp,
                    kind="texture",
                    width=w,
                    height=h,
                    negative_prompt=negative,
                    seed=seed,
                    steps=self.sd_steps,
                    guidance_scale=self.sd_guidance,
                    autostart=True,
                )
            if not path or not path.exists():
                return None
            img = Image.open(path).convert('RGB')
            if img.size != size:
                img = img.resize(size, Image.Resampling.LANCZOS)
            # Match procedural finishing so SD/procedural diffuse read consistently.
            img = ImageEnhance.Sharpness(img).enhance(1.08)
            img = ImageEnhance.Contrast(img).enhance(1.03)
            try:
                tmp.unlink()
            except OSError:
                pass
            return img
        except Exception as exc:
            print(f"    [SD] diffuse failed ({module_type}): {exc}")
            return None

    def generate_diffuse_texture(self, size: Tuple[int, int], module_type: str) -> Image.Image:
        """Generate a RICH diffuse (base color) texture map for a module.

        This texture wraps the 3D mesh (mesh material), so richer detail here =
        a better-looking baked spritesheet. Instead of a near-flat base fill,
        we layer: base<->carapace organic mottling, directional gradient
        shading (light from top), faint bioluminescent vein tinting, and fine
        grain — the same richness techniques used elsewhere, applied via fast
        C-level PIL compositing.
        """
        base_rgb = self.hex_to_rgb(self.palette.get('baseColor', '#1a2a3a'))
        if not PIL_AVAILABLE:
            return Image.new('RGB', size, base_rgb)

        width, height = size
        carapace_rgb = self.hex_to_rgb(self.palette.get('carapaceColor', '#2a3a4a'))
        vein_rgb = self.hex_to_rgb(self.palette.get('veinColor', '#66ccff'))
        # Highlight/shadow tones derived from the base color for shading depth.
        light_rgb = self._lerp_rgb(carapace_rgb, (255, 255, 255), 0.25)
        dark_rgb = self._lerp_rgb(base_rgb, (0, 0, 0), 0.45)

        seed = (abs(hash(module_type)) % 100000) + 17

        # --- Layer 1: organic base<->carapace mottling (per-pixel blend) ---
        base_img = Image.new('RGB', size, base_rgb)
        carapace_img = Image.new('RGB', size, carapace_rgb)
        mottle = self._multi_octave_mottle(size, seed)
        img = Image.composite(carapace_img, base_img, mottle)

        # --- Layer 2: directional gradient shading (top lit, bottom shaded) ---
        grad = Image.new('L', (1, height))
        grad.putdata([int(200 - (y / max(1, height - 1)) * 120) for y in range(height)])
        grad = grad.resize(size)
        light_img = Image.new('RGB', size, light_rgb)
        dark_img = Image.new('RGB', size, dark_rgb)
        shade = Image.composite(light_img, dark_img, grad)
        img = Image.blend(img, shade, 0.28)

        # --- Layer 3: faint bioluminescent vein streaks (adds read/interest) ---
        veins = Image.new('L', size, 0)
        vdraw = ImageDraw.Draw(veins)
        cx = width // 2
        for y in range(height):
            x = cx + int(math.sin(y * 0.03) * width * 0.18 + math.sin(y * 0.11) * width * 0.05)
            for off in range(-2, 3):
                px = x + off
                if 0 <= px < width:
                    vdraw.point((px, y), fill=max(0, 90 - abs(off) * 30))
        for branch in range(4):
            by = int(height * (0.15 + branch * 0.22))
            bx = cx + int(math.sin(by * 0.07) * width * 0.2)
            for i in range(width // 4):
                px = bx + int(math.cos(i * 0.2 + branch) * i)
                py = by + int(math.sin(i * 0.15) * i * 0.4)
                if 0 <= px < width and 0 <= py < height:
                    vdraw.point((px, py), fill=max(0, 70 - i))
        veins = veins.filter(ImageFilter.GaussianBlur(radius=1.5))
        vein_img = Image.new('RGB', size, vein_rgb)
        img = Image.composite(vein_img, img, veins)

        # --- Layer 4: fine film grain for surface tactility ---
        try:
            grain = Image.effect_noise(size, 14).convert('L')
            grain_rgb = Image.merge('RGB', (grain, grain, grain))
            img = ImageChops.overlay(img, grain_rgb)
            img = Image.blend(Image.new('RGB', size, base_rgb), img, 0.9)
        except Exception:
            pass

        # Subtle sharpen so detail survives Blender's texture sampling.
        img = ImageEnhance.Sharpness(img).enhance(1.12)
        img = ImageEnhance.Contrast(img).enhance(1.05)
        return img
    
    def generate_emission_texture(self, size: Tuple[int, int], module_type: str) -> Image.Image:
        """Generate emission (glow) texture showing vein network."""
        img = Image.new('RGB', size, (0, 0, 0))
        
        if not PIL_AVAILABLE:
            return img
        
        draw = ImageDraw.Draw(img)
        width, height = size
        
        # Draw vein network pattern
        vein_color = self.hex_to_rgb(self.palette.get('veinColor', '#66ccff'))
        
        # Create flowing vein pattern
        center_x, center_y = width // 2, height // 2
        
        # Main vein along center
        for y in range(height):
            x = center_x + int(math.sin(y * 0.1) * 10)
            for offset in range(-2, 3):
                if 0 <= x + offset < width:
                    intensity = int(255 * (1.0 - abs(offset) / 3.0))
                    color = tuple(min(255, int(c * intensity / 255)) for c in vein_color)
                    draw.point((x + offset, y), fill=color)
        
        # Branching veins
        for branch_y in range(0, height, height // 6):
            branch_x = center_x + int(math.sin(branch_y * 0.15) * 15)
            for i in range(20):
                x = branch_x + int(math.cos(i * 0.3) * i)
                y = branch_y + i
                if 0 <= x < width and 0 <= y < height:
                    intensity = int(255 * (1.0 - i / 20.0))
                    color = tuple(min(255, int(c * intensity / 255)) for c in vein_color)
                    draw.point((x, y), fill=color)
        
        return img
    
    def generate_normal_texture(self, size: Tuple[int, int], module_type: str) -> Image.Image:
        """Generate normal map for surface detail."""
        img = Image.new('RGB', size, (128, 128, 255))  # Default normal (flat)
        
        if not PIL_AVAILABLE:
            return img
        
        draw = ImageDraw.Draw(img)
        width, height = size
        
        # Add subtle surface variation
        for y in range(height):
            for x in range(width):
                # Calculate normal based on organic wrinkles
                nx = int(128 + math.sin(x * 0.05) * 10)
                ny = int(128 + math.cos(y * 0.05) * 10)
                nz = int(255 - abs(math.sin(x * 0.05) + math.cos(y * 0.05)) * 5)
                
                draw.point((x, y), fill=(nx, ny, nz))
        
        return img
    
    def generate_roughness_texture(self, size: Tuple[int, int], module_type: str) -> Image.Image:
        """Generate roughness map (smooth organic skin)."""
        # Bioluminescent skin is smooth/glossy
        roughness_value = int(255 * 0.3)  # 30% roughness (70% smooth)
        img = Image.new('L', size, roughness_value)
        return img
    
    def generate_metallic_texture(self, size: Tuple[int, int], module_type: str) -> Image.Image:
        """Generate metallic map (non-metallic organic material)."""
        # Organic skin is non-metallic
        img = Image.new('L', size, 0)  # 0 = non-metallic
        return img
    
    def generate_module_textures(self, module_config: Dict, output_dir: Path, texture_size: Tuple[int, int] = None):
        """Generate all texture maps for a module."""
        # Ensure required attributes exist (for thread-safe instances created with __new__)
        if not hasattr(self, 'visual_registry') or not hasattr(self, 'skinning_registry'):
            raise ValueError("SpaceWhaleTextureGenerator instance not properly initialized. Required attributes missing.")
        if not hasattr(self, 'palette'):
            # Initialize palette from visual_registry if missing
            self.palette = self.visual_registry.get('visualLanguage', {}).get('colorPalettes', {}).get('primary', {})
        if not hasattr(self, 'materials'):
            self.materials = self.visual_registry.get('visualLanguage', {}).get('materials', {})
        if not hasattr(self, 'bone_structure'):
            self.bone_structure = self.skinning_registry.get('boneStructure', {})
        # SD/quality config may be missing on thread-local __new__ instances.
        for attr, default in (('use_sd', False), ('sd_api_url', None), ('quality', 'standard'),
                              ('base_size', 512), ('sd_steps', 26), ('sd_guidance', 7.0),
                              ('max_size', 1024), ('min_size', 256)):
            if not hasattr(self, attr):
                setattr(self, attr, default)

        module_type = module_config.get('type', 'mid')
        module_name = module_config.get('name', 'module')

        # Content-aware size unless an explicit override was passed.
        if texture_size is None:
            texture_size = self.resolve_module_size(module_config)

        module_dir = output_dir / module_name
        module_dir.mkdir(parents=True, exist_ok=True)

        src = "SD"
        print(f"  Generating textures for {module_name} ({module_type}) "
              f"@ {texture_size[0]}x{texture_size[1]} diffuse={src}...")

        diffuse = self.generate_diffuse_texture_sd(texture_size, module_type)
        if diffuse is None:
            raise RuntimeError(
                f"SD diffuse failed for {module_name}; procedural skins are disabled"
            )

        from pbr_skin_generator import (
            _emission_from_diffuse,
            _metallic_from_diffuse,
            _normal_from_diffuse,
            _roughness_from_diffuse,
        )

        textures = {
            'diffuse': diffuse,
            'emission': _emission_from_diffuse(diffuse, glow=True),
            'normal': _normal_from_diffuse(diffuse),
            'roughness': _roughness_from_diffuse(diffuse),
            'metallic': _metallic_from_diffuse(diffuse),
        }
        
        # Save textures
        for map_type, img in textures.items():
            file_path = module_dir / f"{module_name}_{map_type}.png"
            img.save(file_path, 'PNG')
            print(f"    Saved: {file_path.name}")
        
        # Create texture registry entry
        texture_registry = {
            'module': module_name,
            'type': module_type,
            'textures': {
                'diffuse': f"{module_name}/{module_name}_diffuse.png",
                'emission': f"{module_name}/{module_name}_emission.png",
                'normal': f"{module_name}/{module_name}_normal.png",
                'roughness': f"{module_name}/{module_name}_roughness.png",
                'metallic': f"{module_name}/{module_name}_metallic.png"
            },
            'size': texture_size,
            'uvMapping': {
                'method': 'automatic',
                'seams': 'minimal',
                'description': 'UV mapped for rigging compatibility'
            }
        }
        
        return texture_registry
    
    def generate_all_textures(self, ship_config: Dict, output_dir: Path):
        """Generate textures for all modules in the ship (multithreaded)."""
        modules = ship_config.get('visual', {}).get('modules', [])
        
        print(f"Generating textures for {len(modules)} modules using multithreading...")
        print("")
        
        # Determine optimal thread count (up to 32 cores). With SD on, the GPU
        # server serializes anyway (guarded by _SD_SEMAPHORE), so keep a modest
        # pool to overlap procedural maps without holding many open SD sockets.
        if self.use_sd:
            max_workers = min(4, cpu_count(), len(modules))
        else:
            max_workers = min(32, cpu_count(), len(modules))
        print(f"Using {max_workers} worker threads")
        
        # Thread-safe collections
        texture_registries = []
        results_lock = threading.Lock()
        progress_lock = threading.Lock()
        
        # Store instance data for thread-safe access
        visual_registry_copy = json.loads(json.dumps(self.visual_registry))
        skinning_registry_copy = json.loads(json.dumps(self.skinning_registry))
        palette_copy = json.loads(json.dumps(self.palette))
        materials_copy = json.loads(json.dumps(self.materials))
        bone_structure_copy = json.loads(json.dumps(self.bone_structure))
        sd_config = self._sd_config_dict()
        
        def generate_module_textures_thread_safe(module: Dict) -> Dict:
            """Generate textures for a single module (thread-safe)."""
            try:
                # Create a thread-local generator instance by copying instance data
                # We can't call __init__ without file paths, so we create a minimal instance
                thread_generator = type(self).__new__(type(self))
                # Copy all required attributes (thread-safe deep copy)
                thread_generator.visual_registry = json.loads(json.dumps(visual_registry_copy))
                thread_generator.skinning_registry = json.loads(json.dumps(skinning_registry_copy))
                thread_generator.palette = json.loads(json.dumps(palette_copy))
                thread_generator.materials = json.loads(json.dumps(materials_copy))
                thread_generator.bone_structure = json.loads(json.dumps(bone_structure_copy))
                # Propagate SD/quality config (scalars) to the thread-local instance.
                for _k, _v in sd_config.items():
                    setattr(thread_generator, _k, _v)

                # Generate textures using the thread-local instance
                registry = thread_generator.generate_module_textures(module, output_dir)
                
                with progress_lock:
                    # Use ASCII-safe checkmark for Windows compatibility
                    checkmark = "[OK]" if sys.platform == 'win32' and not hasattr(sys.stdout, 'reconfigure') else "✓"
                    try:
                        print(f"  {checkmark} {module.get('name', 'module')} textures generated")
                    except UnicodeEncodeError:
                        print(f"  [OK] {module.get('name', 'module')} textures generated")
                
                return registry
            except Exception as e:
                with progress_lock:
                    print(f"  [ERROR] Error generating textures for {module.get('name', 'module')}: {e}")
                return None
        
        # Generate textures in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(generate_module_textures_thread_safe, module): module for module in modules}
            
            for future in as_completed(futures):
                try:
                    registry = future.result()
                    if registry:
                        with results_lock:
                            texture_registries.append(registry)
                except Exception as e:
                    module = futures[future]
                    print(f"  [ERROR] Failed to generate textures for {module.get('name', 'unknown')}: {e}")
        
        print("")
        
        # Save master texture registry
        master_registry = {
            'version': '1.1.0',
            'description': 'Space Whale texture registry for rigging and spritesheet generation',
            'shipId': ship_config.get('id', 'unknown'),
            'textureSize': [self.base_size, self.base_size],
            'quality': self.quality,
            'diffuseSource': 'sd' if self.use_sd else 'procedural',
            'modules': texture_registries,
            'usage': {
                'rigging': 'Load textures in Blender with rigging setup',
                'spritesheet': 'Use textures when rendering 120 facings',
                'materialSetup': 'Apply textures to materials for bioluminescent effect'
            }
        }
        
        registry_path = output_dir / "texture_registry.json"
        with open(registry_path, 'w', encoding='utf-8') as f:
            json.dump(master_registry, f, indent=2, ensure_ascii=False)
        
        print(f"Texture registry saved: {registry_path}")
        return master_registry

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate textures for Space Whale rigging')
    parser.add_argument('--ship-registry', default='space_whale_ship_example.json', help='Ship registry JSON')
    parser.add_argument('--visual-registry', default='space_whale_visual_language_registry.json', help='Visual language registry')
    parser.add_argument('--skinning-registry', default='space_whale_skinning_registry.json', help='Skinning registry')
    parser.add_argument('--output', default='Output/SpaceWhaleTextures', help='Output directory')
    parser.add_argument('--texture-size', type=int, nargs=2, default=None,
                        help='Explicit base texture size (width height); overrides --texture-quality')
    parser.add_argument('--texture-quality', choices=list(TEXTURE_QUALITY.keys()), default='standard',
                        help='Diffuse quality tier: draft(384)/standard(512)/high(768)/ultra(1024)')
    parser.add_argument('--sd', choices=['auto', 'on', 'off'], default='auto',
                        help='Use local Stable Diffusion for diffuse: auto=use if server up, on=require, off=procedural')
    parser.add_argument('--sd-steps', type=int, default=None, help='Override SD sampling steps')
    parser.add_argument('--guidance', type=float, default=None, help='Override SD guidance scale')
    parser.add_argument('--max-texture-size', type=int, default=1024,
                        help='VRAM cap: clamp any module texture to this (default 1024)')
    parser.add_argument('--api-url', default=None, help='Explicit SD API URL (else auto-detect)')

    args = parser.parse_args()
    
    # Check for PIL/Pillow dependency
    if not PIL_AVAILABLE:
        print("ERROR: PIL/Pillow is required for texture generation")
        print("Please install with: pip install Pillow")
        return 1
    
    # Load ship config
    try:
        with open(args.ship_registry, 'r', encoding='utf-8') as f:
            ship_data = json.load(f)
            # Handle both formats: {'ships': [...]} and direct ship object
            if isinstance(ship_data, dict) and 'ships' in ship_data:
                ships = ship_data.get('ships', [])
            elif isinstance(ship_data, dict) and 'id' in ship_data:
                # Single ship object
                ships = [ship_data]
            elif isinstance(ship_data, list):
                ships = ship_data
            else:
                ships = []
    except FileNotFoundError:
        print(f"ERROR: Ship registry file not found: {args.ship_registry}")
        return
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in ship registry: {e}")
        return
    except Exception as e:
        print(f"ERROR: Failed to load ship registry: {e}")
        return
    
    if not ships:
        print("ERROR: No ships found in registry")
        print(f"  Registry file: {args.ship_registry}")
        print(f"  File exists: {os.path.exists(args.ship_registry)}")
        return
    
    # Use first ship (or could iterate over all)
    ship = ships[0]
    
    # Create generator
    generator = SpaceWhaleTextureGenerator(args.visual_registry, args.skinning_registry)

    # Resolve SD usage via Shared/ai_resources (starts :1338 when auto/on).
    api_url = args.api_url
    use_sd = False
    if args.sd == 'off':
        print("ERROR: procedural textures are disabled. Use --sd auto or --sd on.")
        return
    if args.sd != 'off' and _SD_AVAILABLE and tx:
        try:
            prepared = tx.prepare(image=True, mesh=True, keep_server=False)
            use_sd = bool((prepared.get("image") or {}).get("ready")) or tx.image_ready()
            if use_sd:
                api_url = api_url or (prepared.get("image") or {}).get("endpoint")
        except Exception as exc:
            print(f"[WARN] Shared image stage: {exc}")
            use_sd = False
        if not use_sd:
            print("ERROR: Shared image stage is down. "
                  "Run: python Transcendence\\tx_ai_pipeline.py session")
            return
    elif args.sd == 'on' and not _SD_AVAILABLE:
        print("ERROR: --sd on requested but tx_ai_pipeline/Shared is unavailable.")
        return

    base_size = args.texture_size[0] if args.texture_size else None
    generator.configure_sd(
        use_sd=use_sd,
        api_url=api_url,
        quality=args.texture_quality,
        base_size=base_size,
        sd_steps=args.sd_steps,
        guidance=args.guidance,
        max_size=args.max_texture_size,
    )

    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Space Whale Texture Generator for Rigging")
    print("=" * 60)
    print(f"Ship: {ship.get('id', 'unknown')}")
    print(f"Output: {output_dir}")
    print(f"Quality: {generator.quality}  base={generator.base_size}px  "
          f"cap={generator.max_size}px")
    print(f"Diffuse source: Stable Diffusion @ {api_url}")
    print("")

    try:
        registry = generator.generate_all_textures(ship, output_dir)
    finally:
        if tx:
            tx.release()
    
    print("")
    print("=" * 60)
    print("Texture Generation Complete!")
    print("=" * 60)
    print(f"\nGenerated {len(registry['modules'])} module texture sets")
    print(f"Each module has 5 texture maps:")
    print("  - Diffuse (base color)")
    print("  - Emission (glow/veins)")
    print("  - Normal (surface detail)")
    print("  - Roughness (smoothness)")
    print("  - Metallic (material type)")
    print(f"\nTextures ready for Blender rigging and spritesheet generation!")
    
    return 0

if __name__ == "__main__":
    main()

