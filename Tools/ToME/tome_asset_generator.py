#!/usr/bin/env python3
"""
Tales of Maj'Eyal (T-Engine4) Asset Generator
A deterministic, mod-friendly asset generator that produces ready-to-drop ToME mod packages.
"""

import json
import os
import sys
import hashlib
import random
import math
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import tempfile
import shutil

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("WARNING: PIL/Pillow not available. Install with: pip install Pillow")
    print("Sprite generation will be limited.")


class AssetType(Enum):
    """Types of assets that can be generated."""
    SPELL = "spell"
    ACTOR = "actor"
    ITEM = "item"
    VFX = "vfx"
    PROJECTILE = "projectile"


class ShapeModule(Enum):
    """Shape composition modules for parameter patching."""
    RING = "ring"
    INK_BLEED = "ink_bleed"
    BOLT = "bolt"
    NOVA = "nova"
    BEAM = "beam"
    WALL = "wall"
    CLOUD = "cloud"
    SPHERE = "sphere"
    CUBE = "cube"
    SPIRAL = "spiral"


@dataclass
class SpriteMetadata:
    """Metadata for a spritesheet."""
    frame_width: int
    frame_height: int
    frames: int
    fps: int
    anchor_x: int
    anchor_y: int
    loop: bool
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class BalanceScore:
    """Balance scoring for generated content."""
    damage: float
    area: float
    duration: float
    control: float
    cost: float
    total_score: float
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class VFXMetadata:
    """VFX and particle effect metadata."""
    particle_count: int
    lifetime: float
    color_ramp: List[Tuple[int, int, int]]
    blend_mode: str
    animation_curve: List[float]
    
    def to_dict(self) -> Dict:
        return {
            'particle_count': self.particle_count,
            'lifetime': self.lifetime,
            'color_ramp': self.color_ramp,
            'blend_mode': self.blend_mode,
            'animation_curve': self.animation_curve
        }


class DeterministicRNG:
    """Deterministic pseudo-random number generator for reproducible results."""
    
    def __init__(self, seed: int):
        self.seed = seed
        self.rng = random.Random(seed)
    
    def random(self) -> float:
        """Return a random float in [0.0, 1.0)."""
        return self.rng.random()
    
    def randint(self, a: int, b: int) -> int:
        """Return a random integer in [a, b]."""
        return self.rng.randint(a, b)
    
    def choice(self, seq: List) -> Any:
        """Return a random element from seq."""
        return self.rng.choice(seq)
    
    def uniform(self, a: float, b: float) -> float:
        """Return a random float in [a, b)."""
        return self.rng.uniform(a, b)
    
    def gauss(self, mu: float, sigma: float) -> float:
        """Return a random float from a Gaussian distribution."""
        return self.rng.gauss(mu, sigma)


class ToMEAssetGenerator:
    """Main asset generator for Tales of Maj'Eyal mods."""
    
    # Engine limits
    MAX_FRAMES = 32
    MAX_SPRITE_SIZE = 256
    MAX_DAMAGE = 1000
    MAX_RADIUS = 10
    MAX_DURATION = 20
    
    def __init__(self, output_dir: str, mod_name: str = "tomegen_mod"):
        self.output_dir = Path(output_dir)
        self.mod_name = mod_name
        self.mod_path = self.output_dir / "mods" / mod_name
        self.data_path = self.mod_path / "data"
        self.preview_path = self.mod_path / "preview"
        
        # Create directory structure
        self._create_directory_structure()
        
        # Asset registry
        self.assets = []
        
        # Validation flags
        self.validation_errors = []
        self.validation_warnings = []
    
    def _create_directory_structure(self):
        """Create the ToME mod directory structure."""
        dirs = [
            self.data_path / "gfx" / "sprites",
            self.data_path / "lua" / "talents",
            self.data_path / "lua" / "entities",
            self.data_path / "lua" / "items",
            self.data_path / "locale" / "en",
            self.preview_path
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)
    
    def generate(
        self,
        template: AssetType,
        shapes: List[ShapeModule],
        seed: int,
        variant: str = ""
    ) -> Dict:
        """Generate a complete asset package."""
        rng = DeterministicRNG(seed)
        
        # Generate unique identifier
        asset_id = f"gen_{template.value}_{seed:05d}"
        if variant:
            asset_id += f"_{variant}"
        
        # Generate parameters from template and shapes
        params = self._generate_parameters(template, shapes, rng)
        
        # Validate parameters
        validation_result = self._validate_parameters(params, template)
        if not validation_result['valid']:
            self.validation_errors.extend(validation_result['errors'])
            self.validation_warnings.extend(validation_result['warnings'])
            if validation_result['blocking']:
                raise ValueError(f"Validation failed for {asset_id}: {validation_result['errors']}")
        
        # Generate sprite
        sprite_path, sprite_meta = self._generate_sprite(asset_id, template, params, rng)
        
        # Generate icon
        icon_path = self._generate_icon(asset_id, sprite_path, rng)
        
        # Generate VFX metadata
        vfx_meta = self._generate_vfx_metadata(template, params, rng)
        
        # Generate Lua stubs
        lua_stubs = self._generate_lua_stubs(asset_id, template, params, sprite_meta, vfx_meta)
        
        # Generate localization
        locale_file = self._generate_localization(asset_id, template, params, rng)
        
        # Calculate balance score
        balance = self._calculate_balance_score(params, template)
        
        # Generate preview
        preview_path = self._generate_preview(asset_id, sprite_path, sprite_meta, params)
        
        # Create asset record
        asset = {
            'id': asset_id,
            'template': template.value,
            'shapes': [s.value for s in shapes],
            'seed': seed,
            'variant': variant,
            'sprite': str(sprite_path.relative_to(self.mod_path)),
            'icon': str(icon_path.relative_to(self.mod_path)) if icon_path else None,
            'metadata': sprite_meta.to_dict(),
            'vfx': vfx_meta.to_dict(),
            'balance': balance.to_dict(),
            'lua_files': lua_stubs,
            'locale_file': str(locale_file.relative_to(self.mod_path)),
            'preview': str(preview_path.relative_to(self.mod_path))
        }
        
        self.assets.append(asset)
        
        # Check balance score and flag outliers
        if balance.total_score > 0.9 or balance.total_score < 0.1:
            self.validation_warnings.append(
                f"{asset_id}: Balance score {balance.total_score:.2f} is outside normal range (0.1-0.9)"
            )
        
        return asset
    
    def _validate_parameters(self, params: Dict, template: AssetType) -> Dict:
        """Validate generated parameters against engine limits and safety rules."""
        errors = []
        warnings = []
        blocking = False
        
        # Check frame limits
        frames = params.get('frames', 0)
        if frames > self.MAX_FRAMES:
            errors.append(f"Frames {frames} exceeds maximum {self.MAX_FRAMES}")
            blocking = True
            params['frames'] = self.MAX_FRAMES
        
        if frames < 1:
            errors.append("Frames must be at least 1")
            blocking = True
            params['frames'] = 1
        
        # Check sprite size
        frame_size = max(params.get('frame_width', 64), params.get('frame_height', 64))
        if frame_size > self.MAX_SPRITE_SIZE:
            errors.append(f"Sprite size {frame_size} exceeds maximum {self.MAX_SPRITE_SIZE}")
            blocking = True
        
        # Check damage
        damage = params.get('damage', 0)
        if damage > self.MAX_DAMAGE:
            warnings.append(f"Damage {damage:.1f} exceeds recommended maximum {self.MAX_DAMAGE}")
            params['damage'] = min(damage, self.MAX_DAMAGE)
        
        # Check radius
        radius = params.get('radius', 0)
        if radius > self.MAX_RADIUS:
            warnings.append(f"Radius {radius} exceeds recommended maximum {self.MAX_RADIUS}")
            params['radius'] = min(radius, self.MAX_RADIUS)
        
        # Check duration
        duration = params.get('duration', 0)
        if duration > self.MAX_DURATION:
            warnings.append(f"Duration {duration} exceeds recommended maximum {self.MAX_DURATION}")
            params['duration'] = min(duration, self.MAX_DURATION)
        
        # Check cooldown and mana (sanity checks)
        cooldown = params.get('cooldown', 0)
        if cooldown < 0:
            errors.append("Cooldown cannot be negative")
            blocking = True
            params['cooldown'] = max(0, cooldown)
        
        mana = params.get('mana', 0)
        if mana < 0:
            errors.append("Mana cost cannot be negative")
            blocking = True
            params['mana'] = max(0, mana)
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'blocking': blocking
        }
    
    def _generate_parameters(
        self,
        template: AssetType,
        shapes: List[ShapeModule],
        rng: DeterministicRNG
    ) -> Dict:
        """Generate parameters from template and shape modules."""
        params = {
            'damage': 0.0,
            'radius': 0,
            'duration': 0,
            'cooldown': 10,
            'mana': 18,
            'range': 6,
            'frames': 8,
            'fps': 12,
            'color': (255, 200, 100),
            'intensity': 1.0
        }
        
        # Base template parameters
        if template == AssetType.SPELL:
            params['damage'] = rng.uniform(20, 60)
            params['radius'] = rng.randint(1, 3)
            params['cooldown'] = rng.randint(8, 15)
            params['mana'] = rng.randint(15, 30)
            params['range'] = rng.randint(4, 8)
        elif template == AssetType.ACTOR:
            params['frames'] = rng.randint(4, 12)
            params['fps'] = rng.randint(8, 16)
        elif template == AssetType.ITEM:
            params['frames'] = 1  # Static items
        elif template == AssetType.VFX:
            params['frames'] = rng.randint(6, 16)
            params['fps'] = rng.randint(10, 20)
        
        # Apply shape modifiers
        for shape in shapes:
            if shape == ShapeModule.RING:
                params['radius'] = max(1, params['radius'] + rng.randint(1, 2))
                params['damage'] *= 0.8  # Ring is area effect
            elif shape == ShapeModule.INK_BLEED:
                params['duration'] = rng.randint(3, 8)
                params['damage'] *= 0.6  # DoT effect
            elif shape == ShapeModule.BOLT:
                params['range'] = max(6, params['range'] + rng.randint(2, 4))
                params['damage'] *= 1.2  # Single target
            elif shape == ShapeModule.NOVA:
                params['radius'] = max(3, params['radius'] + rng.randint(2, 4))
                params['damage'] *= 0.7
            elif shape == ShapeModule.BEAM:
                params['range'] = max(8, params['range'] + rng.randint(4, 6))
                params['damage'] *= 1.1
        
        # Generate color palette
        color_schemes = [
            ((255, 100, 100), (255, 200, 100)),  # Fire
            ((100, 150, 255), (150, 200, 255)),  # Ice
            ((150, 255, 150), (200, 255, 200)),  # Nature
            ((200, 100, 255), (255, 150, 255)),  # Arcane
            ((255, 200, 100), (255, 255, 150)),  # Light
            ((100, 100, 150), (150, 150, 200)),  # Dark
        ]
        base_color, glow_color = rng.choice(color_schemes)
        params['color'] = base_color
        params['glow_color'] = glow_color
        
        return params
    
    def _generate_sprite(
        self,
        asset_id: str,
        template: AssetType,
        params: Dict,
        rng: DeterministicRNG
    ) -> Tuple[Path, SpriteMetadata]:
        """Generate a spritesheet PNG and metadata."""
        frame_width = 64
        frame_height = 64
        frames = params['frames']
        fps = params['fps']
        
        # Create spritesheet
        sheet_width = frame_width * frames
        sheet_height = frame_height
        
        if not PIL_AVAILABLE:
            raise RuntimeError(
                "Pillow is required for ToME sprite generation. Install with: pip install Pillow"
            )
        sheet = Image.new('RGBA', (sheet_width, sheet_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(sheet)
        
        for frame in range(frames):
            x_offset = frame * frame_width
            progress = frame / max(1, frames - 1)
            
            # Draw frame based on template (procedural PIL art; AI is an optional upgrade elsewhere)
            if template == AssetType.SPELL:
                self._draw_spell_frame(draw, x_offset, frame_width, frame_height, params, progress, rng)
            elif template == AssetType.ACTOR:
                self._draw_actor_frame(draw, x_offset, frame_width, frame_height, params, progress, rng)
            elif template == AssetType.VFX:
                self._draw_vfx_frame(draw, x_offset, frame_width, frame_height, params, progress, rng)
            else:
                self._draw_generic_frame(draw, x_offset, frame_width, frame_height, params, progress, rng)
        # Save sprite
        sprite_path = self.data_path / "gfx" / "sprites" / f"{asset_id}.png"
        sheet.save(sprite_path, 'PNG')
        
        # Create metadata
        metadata = SpriteMetadata(
            frame_width=frame_width,
            frame_height=frame_height,
            frames=frames,
            fps=fps,
            anchor_x=frame_width // 2,
            anchor_y=frame_height - 8,  # Bottom-center
            loop=True
        )
        
        # Save metadata
        meta_path = self.data_path / "gfx" / "sprites" / f"{asset_id}.meta.json"
        with open(meta_path, 'w') as f:
            json.dump(metadata.to_dict(), f, indent=2)
        
        return sprite_path, metadata
    
    def _draw_spell_frame(
        self,
        draw: ImageDraw.Draw,
        x_offset: int,
        width: int,
        height: int,
        params: Dict,
        progress: float,
        rng: DeterministicRNG
    ):
        """Draw a spell effect frame."""
        center_x = x_offset + width // 2
        center_y = height // 2
        
        color = params['color']
        glow_color = params['glow_color']
        
        # Animated spell effect
        radius = int(20 + 10 * math.sin(progress * math.pi * 2))
        
        # Outer glow (use Image.alpha_composite for proper blending)
        base_img = draw._image if hasattr(draw, '_image') else None
        if base_img:
            for i in range(3):
                r = radius + i * 3
                alpha = int(255 * (1 - i / 3) * 0.4)  # Fade out
                glow_rgb = tuple(int(c * alpha / 255) for c in glow_color)
                glow_img = Image.new('RGBA', (r*2+2, r*2+2), (0, 0, 0, 0))
                glow_draw = ImageDraw.Draw(glow_img)
                glow_draw.ellipse([0, 0, r*2+1, r*2+1], fill=(*glow_rgb, alpha))
                base_img.paste(glow_img, (center_x - r, center_y - r), glow_img)
            
            # Core
            core_img = Image.new('RGBA', (radius+2, radius+2), (0, 0, 0, 0))
            core_draw = ImageDraw.Draw(core_img)
            core_draw.ellipse([0, 0, radius+1, radius+1], fill=(*color, 255))
            base_img.paste(core_img, (center_x - radius // 2, center_y - radius // 2), core_img)
        else:
            # Fallback: simple RGB drawing
            for i in range(3):
                r = radius + i * 3
                glow_rgb = tuple(int(c * 0.4) for c in glow_color)
                draw.ellipse([center_x - r, center_y - r, center_x + r, center_y + r], fill=glow_rgb)
            draw.ellipse([center_x - radius // 2, center_y - radius // 2,
                         center_x + radius // 2, center_y + radius // 2], fill=color)
    
    def _draw_actor_frame(
        self,
        draw: ImageDraw.Draw,
        x_offset: int,
        width: int,
        height: int,
        params: Dict,
        progress: float,
        rng: DeterministicRNG
    ):
        """Draw an actor frame."""
        center_x = width // 2
        center_y = height - 16  # Ground level
        
        color = params['color']
        actor_color = (*color, 255)
        
        # Simple character silhouette
        base_img = draw._image if hasattr(draw, '_image') else None
        body_height = int(30 + 5 * math.sin(progress * math.pi * 2))
        
        if base_img:
            # Body
            body_img = Image.new('RGBA', (24, body_height), (0, 0, 0, 0))
            body_draw = ImageDraw.Draw(body_img)
            body_draw.ellipse([0, 0, 24, body_height], fill=actor_color)
            base_img.paste(body_img, (center_x - 12, center_y - body_height), body_img)
            
            # Head
            head_img = Image.new('RGBA', (16, 12), (0, 0, 0, 0))
            head_draw = ImageDraw.Draw(head_img)
            head_draw.ellipse([0, 0, 16, 12], fill=actor_color)
            base_img.paste(head_img, (center_x - 8, center_y - body_height - 12), head_img)
        else:
            # Fallback
            draw.ellipse([center_x - 12, center_y - body_height, center_x + 12, center_y], fill=color)
            draw.ellipse([center_x - 8, center_y - body_height - 12, center_x + 8, center_y - body_height], fill=color)
    
    def _draw_vfx_frame(
        self,
        draw: ImageDraw.Draw,
        x_offset: int,
        width: int,
        height: int,
        params: Dict,
        progress: float,
        rng: DeterministicRNG
    ):
        """Draw a VFX frame."""
        center_x = width // 2
        center_y = height // 2
        
        color = params['color']
        glow_color = params['glow_color']
        
        # Particle effect
        base_img = draw._image if hasattr(draw, '_image') else None
        particle_count = 8
        
        if base_img:
            for i in range(particle_count):
                angle = (i / particle_count + progress) * math.pi * 2
                distance = 15 + 10 * progress
                x = center_x + int(math.cos(angle) * distance)
                y = center_y + int(math.sin(angle) * distance)
                
                size = max(2, int(3 + 2 * (1 - progress)))
                alpha = int(255 * (1 - progress))
                particle_rgb = tuple(int(c * alpha / 255) for c in glow_color)
                particle_img = Image.new('RGBA', (size*2+2, size*2+2), (0, 0, 0, 0))
                particle_draw = ImageDraw.Draw(particle_img)
                particle_draw.ellipse([0, 0, size*2+1, size*2+1], fill=(*particle_rgb, alpha))
                base_img.paste(particle_img, (x - size, y - size), particle_img)
        else:
            # Fallback
            for i in range(particle_count):
                angle = (i / particle_count + progress) * math.pi * 2
                distance = 15 + 10 * progress
                x = center_x + int(math.cos(angle) * distance)
                y = center_y + int(math.sin(angle) * distance)
                size = max(2, int(3 + 2 * (1 - progress)))
                particle_rgb = tuple(int(c * 0.5) for c in glow_color)
                draw.ellipse([x - size, y - size, x + size, y + size], fill=particle_rgb)
    
    def _draw_generic_frame(
        self,
        draw: ImageDraw.Draw,
        x_offset: int,
        width: int,
        height: int,
        params: Dict,
        progress: float,
        rng: DeterministicRNG
    ):
        """Draw a generic frame."""
        center_x = width // 2
        center_y = height // 2
        
        color = params['color']
        generic_color = (*color, 255)
        
        # Simple circle
        base_img = draw._image if hasattr(draw, '_image') else None
        radius = 20
        
        if base_img:
            circle_img = Image.new('RGBA', (radius*2+2, radius*2+2), (0, 0, 0, 0))
            circle_draw = ImageDraw.Draw(circle_img)
            circle_draw.ellipse([0, 0, radius*2+1, radius*2+1], fill=generic_color)
            base_img.paste(circle_img, (center_x - radius, center_y - radius), circle_img)
        else:
            # Fallback
            draw.ellipse([center_x - radius, center_y - radius, center_x + radius, center_y + radius], fill=color)
    
    def _generate_icon(
        self,
        asset_id: str,
        sprite_path: Path,
        rng: DeterministicRNG
    ) -> Optional[Path]:
        """Generate icon from sprite."""
        if not PIL_AVAILABLE:
            return None
        
        try:
            sprite = Image.open(sprite_path)
            # Extract first frame
            meta_path = sprite_path.parent / f"{asset_id}.meta.json"
            if meta_path.exists():
                with open(meta_path) as f:
                    meta = json.load(f)
                frame_width = meta['frame_width']
                frame_height = meta['frame_height']
                icon = sprite.crop((0, 0, frame_width, frame_height))
            else:
                icon = sprite.crop((0, 0, 64, 64))
            
            # Resize to 64x64
            icon = icon.resize((64, 64), Image.Resampling.LANCZOS)
            
            icon_path = self.data_path / "gfx" / "sprites" / f"icon_{asset_id}_64.png"
            icon.save(icon_path, 'PNG')
            return icon_path
        except Exception as e:
            print(f"Warning: Could not generate icon: {e}")
            return None
    
    def _generate_vfx_metadata(
        self,
        template: AssetType,
        params: Dict,
        rng: DeterministicRNG
    ) -> VFXMetadata:
        """Generate VFX/particle metadata."""
        color = params['color']
        glow_color = params['glow_color']
        
        # Create color ramp
        color_ramp = [
            tuple(int(c * 0.3) for c in color),  # Dark
            color,  # Mid
            glow_color  # Bright
        ]
        
        # Animation curve (ease in/out)
        frames = params['frames']
        animation_curve = []
        for i in range(frames):
            t = i / max(1, frames - 1)
            # Ease in-out curve
            curve = t * t * (3 - 2 * t)
            animation_curve.append(curve)
        
        return VFXMetadata(
            particle_count=rng.randint(10, 50),
            lifetime=params.get('duration', 3.0),
            color_ramp=color_ramp,
            blend_mode="additive",
            animation_curve=animation_curve
        )
    
    def _generate_lua_stubs(
        self,
        asset_id: str,
        template: AssetType,
        params: Dict,
        sprite_meta: SpriteMetadata,
        vfx_meta: VFXMetadata
    ) -> Dict[str, Path]:
        """Generate safe Lua stub files."""
        stubs = {}
        
        if template == AssetType.SPELL:
            stub_path = self.data_path / "lua" / "talents" / f"{asset_id}.lua"
            stub_content = self._generate_talent_stub(asset_id, params, sprite_meta, vfx_meta)
            with open(stub_path, 'w', encoding='utf-8') as f:
                f.write(stub_content)
            stubs['talent'] = stub_path
        
        elif template == AssetType.ACTOR:
            stub_path = self.data_path / "lua" / "entities" / f"{asset_id}.lua"
            stub_content = self._generate_entity_stub(asset_id, params, sprite_meta)
            with open(stub_path, 'w', encoding='utf-8') as f:
                f.write(stub_content)
            stubs['entity'] = stub_path
        
        elif template == AssetType.ITEM:
            stub_path = self.data_path / "lua" / "items" / f"{asset_id}.lua"
            stub_content = self._generate_item_stub(asset_id, params, sprite_meta)
            with open(stub_path, 'w', encoding='utf-8') as f:
                f.write(stub_content)
            stubs['item'] = stub_path
        
        return stubs
    
    def _generate_talent_stub(
        self,
        asset_id: str,
        params: Dict,
        sprite_meta: SpriteMetadata,
        vfx_meta: VFXMetadata
    ) -> str:
        """Generate a safe talent Lua stub."""
        # Sanitize names to prevent code injection
        name = asset_id.replace('_', ' ').title().replace('<', '').replace('>', '')
        short_name = asset_id.upper().replace('<', '').replace('>', '').replace('"', '').replace("'", '')
        
        # Validate numeric parameters
        cooldown = max(0, int(params.get('cooldown', 10)))
        mana = max(0, int(params.get('mana', 18)))
        damage = max(0, float(params.get('damage', 0)))
        range_val = max(1, int(params.get('range', 6)))
        
        # Generate safe action function (only uses preapproved engine functions)
        action_code = f"""  action = function(self, t)
    -- Generated talent action (safe, validated)
    local proj = game.zone:makeEntityByName(game.level, "projectile", "{asset_id}_proj")
    if proj then
      proj.x, proj.y = self.x, self.y
      game:playSoundNear(self, "talents/spell_generic")
      game.zone:addEntity(game.level, proj)
    end
    return true
  end,"""
        
        stub = f"""local _M = loadPrevious(...)

newTalent{{
  name = "Gen: {name}",
  short_name = "{short_name}",
  type = {{"spell/arcane", 1}},
  points = 5,
  cooldown = {cooldown},
  mana = {mana},
  tactical = {{ ATTACK = 2 }},
{action_code}
  info = function(self, t)
    return ([[Generated spell talent. Damage: {damage:.1f}, Range: {range_val}]])
  end,
}}
"""
        return stub
    
    def _generate_entity_stub(
        self,
        asset_id: str,
        params: Dict,
        sprite_meta: SpriteMetadata
    ) -> str:
        """Generate a safe entity Lua stub."""
        # Sanitize names
        name = asset_id.replace('_', ' ').title().replace('<', '').replace('>', '')
        safe_id = asset_id.replace('"', '').replace("'", '')
        
        stub = f"""local _M = loadPrevious(...)

newEntity{{
  define_as = "{safe_id}",
  type = "actor",
  display = {{image="gfx/sprites/{safe_id}.png"}},
  desc = [[Generated actor entity.]],
  name = "{name}",
  body = {{ INVEN = 10 }},
  stats = {{
    str = 10,
    con = 10,
    dex = 10,
    mag = 10,
    wil = 10,
    cun = 10,
  }},
}}
"""
        return stub
    
    def _generate_item_stub(
        self,
        asset_id: str,
        params: Dict,
        sprite_meta: SpriteMetadata
    ) -> str:
        """Generate a safe item Lua stub."""
        # Sanitize names
        name = asset_id.replace('_', ' ').title().replace('<', '').replace('>', '')
        safe_id = asset_id.replace('"', '').replace("'", '')
        
        stub = f"""local _M = loadPrevious(...)

newEntity{{
  define_as = "{safe_id}",
  type = "object",
  subtype = "misc",
  display = {{image="gfx/sprites/{safe_id}.png"}},
  name = "{name}",
  desc = [[Generated item.]],
  image = "gfx/sprites/{safe_id}.png",
}}
"""
        return stub
    
    def _generate_localization(
        self,
        asset_id: str,
        template: AssetType,
        params: Dict,
        rng: DeterministicRNG
    ) -> Path:
        """Generate localization file."""
        # Sanitize names
        name = asset_id.replace('_', ' ').title().replace('<', '').replace('>', '')
        safe_id = asset_id.replace('"', '').replace("'", '').replace('\\', '')
        
        # Generate flavor text (predefined, safe)
        flavor_texts = [
            "A mysterious power flows through you.",
            "The arcane energies coalesce into form.",
            "Ancient magic awakens at your command.",
            "Reality bends to your will.",
            "The void whispers secrets to you.",
        ]
        flavor = rng.choice(flavor_texts)
        
        content = f"""local _M = loadPrevious(...)

return {{
  ["{safe_id}"] = {{
    name = "{name}",
    desc = [[Generated {template.value} talent.]],
    lore = [[{flavor}]],
  }},
}}
"""
        
        locale_path = self.data_path / "locale" / "en" / f"{safe_id}.lua"
        with open(locale_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return locale_path
    
    def _calculate_balance_score(
        self,
        params: Dict,
        template: AssetType
    ) -> BalanceScore:
        """Calculate balance score for generated content."""
        damage = params.get('damage', 0)
        area = params.get('radius', 0) ** 2 * math.pi  # Area of effect
        duration = params.get('duration', 0)
        control = 1.0 if duration > 0 else 0.0
        cost = params.get('mana', 0) + (params.get('cooldown', 0) * 2)
        
        # Normalize scores
        damage_score = min(1.0, damage / 100.0)
        area_score = min(1.0, area / 50.0)
        duration_score = min(1.0, duration / 10.0)
        control_score = control
        cost_score = min(1.0, cost / 50.0)
        
        # Weighted total
        total = (
            damage_score * 0.3 +
            area_score * 0.2 +
            duration_score * 0.15 +
            control_score * 0.15 +
            cost_score * 0.2
        )
        
        return BalanceScore(
            damage=damage_score,
            area=area_score,
            duration=duration_score,
            control=control_score,
            cost=cost_score,
            total_score=total
        )
    
    def _generate_preview(
        self,
        asset_id: str,
        sprite_path: Path,
        sprite_meta: SpriteMetadata,
        params: Dict
    ) -> Path:
        """Generate preview PNG (requires Pillow; always writes a real image)."""
        if not PIL_AVAILABLE:
            raise RuntimeError(
                "Pillow is required for ToME preview generation. Install with: pip install Pillow"
            )
        
        try:
            sprite = Image.open(sprite_path)
            # Extract first frame
            frame = sprite.crop((0, 0, sprite_meta.frame_width, sprite_meta.frame_height))
            # Resize for preview
            preview = frame.resize((200, 200), Image.Resampling.LANCZOS)
            
            preview_path = self.preview_path / f"{asset_id}_preview.png"
            preview.save(preview_path)
            return preview_path
        except Exception as e:
            print(f"Warning: Could not generate preview from sprite: {e}; writing procedural preview")
            preview_path = self.preview_path / f"{asset_id}_preview.png"
            img = Image.new('RGBA', (200, 200), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.ellipse([40, 40, 160, 160], fill=(128, 160, 220, 255))
            img.save(preview_path)
            return preview_path
    
    def generate_manifest(self) -> Path:
        """Generate manifest.json for the mod."""
        # Calculate hashes
        def file_hash(path: Path) -> str:
            if not path.exists():
                return ""
            with open(path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        
        manifest = {
            'mod_name': self.mod_name,
            'version': '1.0.0',
            'generator': 'tome_asset_generator',
            'assets': [],
            'export_hashes': {}
        }
        
        for asset in self.assets:
            asset_entry = {
                'id': asset['id'],
                'template': asset['template'],
                'shapes': asset['shapes'],
                'seed': asset['seed'],
                'balance_score': asset['balance']['total_score'],
                'tags': [asset['template']] + asset['shapes']
            }
            manifest['assets'].append(asset_entry)
            
            # Add file hashes
            sprite_path = self.mod_path / asset['sprite']
            if sprite_path.exists():
                manifest['export_hashes'][asset['sprite']] = file_hash(sprite_path)
        
        manifest_path = self.mod_path / "manifest.json"
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        
        return manifest_path
    
    def generate_preview_html(self) -> Path:
        """Generate HTML preview page."""
        html = """<!DOCTYPE html>
<html>
<head>
    <title>ToME Asset Generator Preview</title>
    <style>
        body { font-family: sans-serif; margin: 20px; background: #1a1a1a; color: #fff; }
        .asset { margin: 20px; padding: 15px; background: #2a2a2a; border-radius: 5px; }
        .asset h3 { margin-top: 0; }
        .preview-img { max-width: 200px; margin: 10px 0; }
        .metadata { font-family: monospace; font-size: 12px; background: #1a1a1a; padding: 10px; border-radius: 3px; }
        .balance { color: #4CAF50; }
    </style>
</head>
<body>
    <h1>ToME Asset Generator Preview</h1>
    <p>Generated assets for mod: <strong>""" + self.mod_name + """</strong></p>
"""
        
        for asset in self.assets:
            html += f"""
    <div class="asset">
        <h3>{asset['id']}</h3>
        <p><strong>Template:</strong> {asset['template']} | <strong>Shapes:</strong> {', '.join(asset['shapes'])}</p>
        <img src="{asset['preview']}" class="preview-img" alt="{asset['id']}">
        <div class="metadata">
            <p><strong>Balance Score:</strong> <span class="balance">{asset['balance']['total_score']:.2f}</span></p>
            <p><strong>Frames:</strong> {asset['metadata']['frames']} @ {asset['metadata']['fps']} fps</p>
            <p><strong>Seed:</strong> {asset['seed']}</p>
        </div>
    </div>
"""
        
        html += """
</body>
</html>
"""
        
        html_path = self.preview_path / "preview.html"
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        return html_path

