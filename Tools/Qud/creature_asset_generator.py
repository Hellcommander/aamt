#!/usr/bin/env python3
"""
Creature Asset Generator for Caves of Qud Mods
Generates creature sprites, tiles, and visual assets for modded creatures.
Supports Ollama-powered design generation for higher quality assets.
"""

import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont
import xml.etree.ElementTree as ET

# Try to import Ollama generator
_ollama_gen_path = Path(__file__).parent / "qud_ollama_asset_generator.py"
if _ollama_gen_path.exists():
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from qud_ollama_asset_generator import QudOllamaAssetGenerator
        OLLAMA_AVAILABLE = True
    except ImportError:
        OLLAMA_AVAILABLE = False
else:
    OLLAMA_AVAILABLE = False


class CreatureAssetGenerator:
    """Generates visual assets for creatures."""
    
    # Qud creature color palette
    COLORS = {
        'K': (0, 0, 0),        # Black
        'k': (64, 64, 64),    # Dark gray
        'R': (255, 0, 0),     # Red
        'r': (128, 0, 0),     # Dark red
        'G': (0, 255, 0),     # Green
        'g': (0, 128, 0),     # Dark green
        'Y': (255, 255, 0),   # Yellow
        'y': (128, 128, 0),   # Dark yellow
        'B': (0, 0, 255),     # Blue
        'b': (0, 0, 128),     # Dark blue
        'M': (255, 0, 255),   # Magenta
        'm': (128, 0, 128),   # Dark magenta
        'C': (0, 255, 255),   # Cyan
        'c': (0, 128, 128),   # Dark cyan
        'W': (255, 255, 255), # White
        'w': (192, 192, 192), # Light gray
    }
    
    def __init__(self, mod_path: Path, use_ollama: bool = True, candidates: int = 3, tile_size: int = 48):
        """Initialize creature asset generator.
        
        Args:
            mod_path: Path to mod directory
            use_ollama: Whether to use Ollama for AI-powered design
            candidates: Number of candidate designs to generate
            tile_size: Tile size in pixels (default 48 for high quality, supports tile scaling mod)
        """
        self.mod_path = Path(mod_path)
        self.textures_path = self.mod_path / "Textures"
        self.visuals_path = self.mod_path / "Visuals"
        self.creatures_path = self.textures_path / "Creatures"
        
        # Create directories - Textures is the standard location
        self.textures_path.mkdir(exist_ok=True)
        self.creatures_path.mkdir(parents=True, exist_ok=True)
        
        # Tile size for high quality assets (supports tile scaling mod)
        self.tile_size = tile_size
        
        # Initialize Ollama generator if available
        self.use_ollama = use_ollama and OLLAMA_AVAILABLE
        self.candidates = candidates
        self.ollama_gen = None
        if self.use_ollama:
            try:
                self.ollama_gen = QudOllamaAssetGenerator()
                if not self.ollama_gen.ollama_available:
                    print("  Warning: Ollama not available, using fallback generation")
                    self.use_ollama = False
            except Exception as e:
                print(f"  Warning: Failed to initialize Ollama generator: {e}")
                self.use_ollama = False
    
    def generate_broodling_tile(self, broodling_name: str, tier: int = 1, 
                                 base_creature: str = "ant", 
                                 color_code: str = "&m",
                                 description: str = "") -> Optional[Path]:
        """
        Generate a tile sprite for a broodling.
        Uses Ollama for design if available, falls back to procedural generation.
        
        Args:
            broodling_name: Name of the broodling (e.g., "BroodlingDrone_T1")
            tier: Tier level (1-6)
            base_creature: Base creature type (ant, beetle, etc.)
            color_code: Qud color code
            description: Description for Ollama design generation
        
        Returns:
            Path to generated tile
        """
        tile_path = self.creatures_path / f"{broodling_name}.png"
        
        if tile_path.exists():
            print(f"      [Creature Assets] Skipping {tile_path.name} (already exists)")
            return tile_path
        
        try:
            size = (self.tile_size, self.tile_size)
            
            # Generate description if missing
            if not description:
                description = self._generate_description_from_name(broodling_name, base_creature, tier)
            
            print(f"      [Creature Assets] Generating {broodling_name}...")
            print(f"        Use Ollama: {self.use_ollama}, Ollama Gen: {self.ollama_gen is not None}")
            
            # Try Ollama generation if available - NO FALLBACK, skip if Ollama fails
            if self.use_ollama and self.ollama_gen:
                candidates = []
                print(f"      Generating {self.candidates} Ollama candidates for {broodling_name}...")
                for i in range(self.candidates):
                    try:
                        print(f"        Candidate {i+1}/{self.candidates}...", end=" ", flush=True)
                        design = self.ollama_gen.generate_creature_design(
                            broodling_name, description, base_creature, tier, color_code
                        )
                        if design is None:
                            print(f"[FAIL] Ollama returned None")
                            continue
                        img = self._render_creature_from_design(design, size, base_creature, tier)
                        quality = self.ollama_gen.assess_asset_quality(img)
                        candidates.append({
                            'image': img,
                            'design': design,
                            'quality': quality
                        })
                        print(f"[OK] Score: {quality['score']:.2f}")
                    except Exception as e:
                        print(f"[FAIL] {e}")
                        continue
                
                if candidates:
                    candidates.sort(key=lambda x: x['quality']['score'], reverse=True)
                    best = candidates[0]
                    img = best['image']
                    print(f"      [Creature Assets] Created tile (Ollama, score: {best['quality']['score']:.2f}): {tile_path.name}")
                else:
                    print(f"      [Creature Assets] SKIPPED: All Ollama candidates failed. Will use base game assets instead.")
                    return None
            else:
                print(f"      [Creature Assets] SKIPPED: Ollama not available. Will use base game assets instead.")
                return None
            
            img.save(tile_path, 'PNG')
            return tile_path
            
        except Exception as e:
            print(f"      [Creature Assets] Failed to create tile: {e}")
            return None
    
    def _generate_procedural_creature(self, base_creature: str, color_code: str, tier: int, size: Tuple[int, int]) -> Image.Image:
        """Generate procedural creature (fallback)."""
        img = Image.new('RGBA', size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        color = self._parse_color_code(color_code)
        
        # Draw creature based on type
        if 'ant' in base_creature.lower():
            self._draw_ant(draw, size, color, tier)
        elif 'beetle' in base_creature.lower():
            self._draw_beetle(draw, size, color, tier)
        elif 'moth' in base_creature.lower():
            self._draw_moth(draw, size, color, tier)
        elif 'leech' in base_creature.lower():
            self._draw_leech(draw, size, color, tier)
        else:
            self._draw_generic_insect(draw, size, color, tier)
        
        return img
    
    def _render_creature_from_design(self, design: Dict, size: Tuple[int, int], base_creature: str, tier: int) -> Image.Image:
        """Render creature image from Ollama design specification."""
        img = Image.new('RGBA', size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        center_x, center_y = size[0] // 2, size[1] // 2
        color_scheme = design.get('colorScheme', {})
        primary = self.ollama_gen.hex_to_rgb(color_scheme.get('primary', '#808080'))
        secondary = self.ollama_gen.hex_to_rgb(color_scheme.get('secondary', '#ffffff'))
        outline = self.ollama_gen.hex_to_rgb(color_scheme.get('outline', '#000000'))
        detail = self.ollama_gen.hex_to_rgb(color_scheme.get('detail', '#ffffff'))
        
        shape = design.get('shape', {})
        proportions = shape.get('proportions', {})
        body_type = shape.get('bodyType', 'oval body')
        
        # Enhanced rendering based on design
        tier_mult = design.get('tierAdjustments', {}).get('sizeMultiplier', 1.0 + tier * 0.1)
        
        # Body size based on design
        body_width = int((8 + tier * 2) * tier_mult)
        body_height = int((12 + tier * 2) * tier_mult)
        
        # Draw main body
        if 'segmented' in body_type.lower():
            # Segmented body
            segments = 3
            for i in range(segments):
                seg_y = center_y - body_height//2 + (i * body_height // segments)
                draw.ellipse([center_x - body_width//2, seg_y,
                             center_x + body_width//2, seg_y + body_height//segments],
                            fill=primary, outline=outline, width=1)
        else:
            # Standard oval body
            draw.ellipse([center_x - body_width//2, center_y - body_height//2,
                         center_x + body_width//2, center_y + body_height//2],
                        fill=primary, outline=outline, width=2)
        
        # Head
        head_size = int((6 + tier) * tier_mult)
        head_prop = proportions.get('headSize', 0.3)
        head_y = center_y - body_height//2 - int(head_size * head_prop)
        draw.ellipse([center_x - head_size//2, head_y - head_size//2,
                     center_x + head_size//2, head_y + head_size//2],
                    fill=primary, outline=outline, width=2)
        
        # Appendages (legs, antennae)
        appendages = shape.get('appendages', [])
        if 'legs' in str(appendages).lower():
            leg_count = 6
            leg_length = int((4 + tier) * tier_mult)
            for i in range(leg_count):
                angle = ((i - leg_count/2) / leg_count) * 3.14
                leg_x = center_x + int(angle * 4)
                leg_end_x = leg_x + int(angle * leg_length)
                leg_end_y = center_y + body_height//2 + leg_length
                draw.line([leg_x, center_y + body_height//2, leg_end_x, leg_end_y],
                         fill=primary, width=2)
        
        # Details (eyes, etc.)
        if 'eyes' in str(shape.get('distinctiveFeatures', [])).lower():
            eye_size = 2
            draw.ellipse([center_x - 3, head_y - 2, center_x - 3 + eye_size, head_y - 2 + eye_size],
                        fill=detail)
            draw.ellipse([center_x + 3 - eye_size, head_y - 2, center_x + 3, head_y - 2 + eye_size],
                        fill=detail)
        
        return img
    
    def _draw_ant(self, draw: ImageDraw, size: Tuple[int, int], color: Tuple[int, int, int], tier: int):
        """Draw an ant-like creature."""
        center_x, center_y = size[0] // 2, size[1] // 2
        
        # Body (oval)
        body_width = 8 + (tier * 2)
        body_height = 12 + (tier * 2)
        draw.ellipse([center_x - body_width//2, center_y - body_height//2,
                     center_x + body_width//2, center_y + body_height//2],
                    fill=color, outline=(255, 255, 255), width=1)
        
        # Head
        head_size = 6 + tier
        draw.ellipse([center_x - head_size//2, center_y - body_height//2 - head_size//2,
                     center_x + head_size//2, center_y - body_height//2 + head_size//2],
                    fill=color, outline=(255, 255, 255), width=1)
        
        # Legs (6 legs)
        leg_length = 4 + tier
        for i in range(3):
            angle = (i - 1) * 0.5
            leg_x = center_x + int(angle * 4)
            draw.line([leg_x, center_y + body_height//2, 
                      leg_x + int(angle * leg_length), center_y + body_height//2 + leg_length],
                    fill=color, width=1)
    
    def _draw_beetle(self, draw: ImageDraw, size: Tuple[int, int], color: Tuple[int, int, int], tier: int):
        """Draw a beetle-like creature."""
        center_x, center_y = size[0] // 2, size[1] // 2
        
        # Carapace (rounded rectangle)
        carapace_width = 12 + (tier * 2)
        carapace_height = 10 + (tier * 2)
        draw.rounded_rectangle([center_x - carapace_width//2, center_y - carapace_height//2,
                               center_x + carapace_width//2, center_y + carapace_height//2],
                              radius=3, fill=color, outline=(255, 255, 255), width=1)
        
        # Head
        head_size = 8 + tier
        draw.ellipse([center_x - head_size//2, center_y - carapace_height//2 - head_size//2,
                     center_x + head_size//2, center_y - carapace_height//2 + head_size//2],
                    fill=color, outline=(255, 255, 255), width=1)
        
        # Legs
        for i in range(6):
            angle = (i - 2.5) * 0.3
            leg_x = center_x + int(angle * 6)
            draw.line([leg_x, center_y + carapace_height//2,
                      leg_x + int(angle * 3), center_y + carapace_height//2 + 4],
                    fill=color, width=1)
    
    def _draw_moth(self, draw: ImageDraw, size: Tuple[int, int], color: Tuple[int, int, int], tier: int):
        """Draw a moth-like creature."""
        center_x, center_y = size[0] // 2, size[1] // 2
        
        # Body
        body_width = 4 + tier
        body_height = 14 + (tier * 2)
        draw.ellipse([center_x - body_width//2, center_y - body_height//2,
                     center_x + body_width//2, center_y + body_height//2],
                    fill=color, outline=(255, 255, 255), width=1)
        
        # Wings (4 wings)
        wing_size = 8 + tier
        for i in range(4):
            angle = (i - 1.5) * 0.8
            wing_x = center_x + int(angle * 8)
            wing_y = center_y + int((i % 2 - 0.5) * 4)
            draw.ellipse([wing_x - wing_size//2, wing_y - wing_size//2,
                         wing_x + wing_size//2, wing_y + wing_size//2],
                        fill=(*color, 180), outline=(255, 255, 255), width=1)
    
    def _draw_leech(self, draw: ImageDraw, size: Tuple[int, int], color: Tuple[int, int, int], tier: int):
        """Draw a leech-like creature."""
        center_x, center_y = size[0] // 2, size[1] // 2
        
        # Long body
        body_length = 20 + (tier * 2)
        body_width = 6 + tier
        draw.ellipse([center_x - body_length//2, center_y - body_width//2,
                     center_x + body_length//2, center_y + body_width//2],
                    fill=color, outline=(255, 255, 255), width=1)
        
        # Sucker mouth
        draw.ellipse([center_x - body_length//2 - 4, center_y - 4,
                     center_x - body_length//2 + 4, center_y + 4],
                    fill=(255, 0, 0), outline=(255, 255, 255), width=1)
    
    def _draw_generic_insect(self, draw: ImageDraw, size: Tuple[int, int], color: Tuple[int, int, int], tier: int):
        """Draw a generic insect shape."""
        center_x, center_y = size[0] // 2, size[1] // 2
        
        # Simple oval body
        body_size = 10 + (tier * 2)
        draw.ellipse([center_x - body_size//2, center_y - body_size//2,
                     center_x + body_size//2, center_y + body_size//2],
                    fill=color, outline=(255, 255, 255), width=1)
    
    def _generate_description_from_name(self, name: str, base_creature: str, tier: int) -> str:
        """Generate a description from the broodling name if missing."""
        name_lower = name.lower()
        
        # Extract key features from name
        features = []
        if 'crystal' in name_lower:
            features.append("crystalline arthropod with reflective exoskeleton")
        elif 'phantom' in name_lower:
            features.append("phase-shifting creature that moves between dimensions")
        elif 'bombardier' in name_lower or 'bomb' in name_lower:
            features.append("explosive artillery specialist with chemical payloads")
        elif 'symbiote' in name_lower:
            features.append("supportive creature that heals and buffs allies")
        elif 'tunneler' in name_lower:
            features.append("burrowing specialist that tunnels through earth")
        elif 'mimic' in name_lower:
            features.append("shape-shifting creature that adapts its form")
        elif 'shard' in name_lower:
            features.append("fragile crystalline creature that shatters on death")
        elif 'swarmling' in name_lower:
            features.append("tiny rapid-reproduction specialist")
        elif 'hero' in name_lower:
            features.append("elite broodling with enhanced capabilities")
        elif 'leaper' in name_lower:
            features.append("powerful jumper that launches at enemies")
        elif 'glider' in name_lower:
            features.append("flying harasser with luminescent wings")
        elif 'stinger' in name_lower:
            features.append("venomous attacker with paralytic stinger")
        elif 'shell' in name_lower or 'beetle' in name_lower:
            features.append("heavily armored tank with thick chitin")
        elif 'weaver' in name_lower or 'spider' in name_lower:
            features.append("web-spinning arachnid that traps prey")
        elif 'scuttler' in name_lower or 'centipede' in name_lower:
            features.append("many-legged skittering hunter")
        elif 'ant' in name_lower or 'drone' in name_lower:
            features.append("basic worker arthropod")
        elif 'moth' in name_lower:
            features.append("flying insect with dust attacks")
        
        if not features:
            features.append(f"{base_creature}-like broodling")
        
        return f"A tier {tier} broodling. " + " ".join(features) + "."
    
    def _parse_color_code(self, color_code: str) -> Tuple[int, int, int]:
        """Parse Qud color code to RGB."""
        code = color_code.replace('&', '').replace('^', '').strip()
        if code and code[0] in self.COLORS:
            return self.COLORS[code[0]]
        return (128, 128, 128)  # Default gray
    
    def analyze_object_blueprints(self, blueprints_path: Path) -> List[Dict[str, any]]:
        """Analyze ObjectBlueprints.xml to find creatures that need tiles."""
        creatures = []
        
        if not blueprints_path.exists():
            return creatures
        
        try:
            tree = ET.parse(blueprints_path)
            root = tree.getroot()
            
            for obj in root.findall('.//object'):
                name = obj.get('Name', '')
                
                # Check if it's a creature (has Brain part or inherits from creature)
                has_brain = obj.find('.//part[@Name="Brain"]') is not None
                inherits_creature = 'Creature' in obj.get('Inherits', '') or 'Insect' in obj.get('Inherits', '')
                
                if has_brain or inherits_creature or 'Broodling' in name:
                    # Extract render info
                    render = obj.find('.//part[@Name="Render"]')
                    if render is not None:
                        tile = render.get('Tile', '')
                        render_string = render.get('RenderString', '')
                        color = render.get('TileColor', '&m')
                        
                        # Get description for Ollama
                        desc_part = obj.find('.//part[@Name="Description"]')
                        description = desc_part.get('Short', '') if desc_part is not None else ''
                        
                        # Check if tile file actually exists
                        tile_exists = False
                        if tile:
                            # Extract filename from tile path
                            tile_filename = Path(tile).name
                            tile_path = self.creatures_path / tile_filename
                            tile_exists = tile_path.exists()
                        
                        creatures.append({
                            'name': name,
                            'tile': tile,
                            'render_string': render_string,
                            'color': color,
                            'description': description,
                            'needs_tile': not tile_exists
                        })
        
        except Exception as e:
            print(f"      [Creature Assets] Failed to parse ObjectBlueprints.xml: {e}")
        
        return creatures
    
    def generate_all_creature_assets(self) -> Dict[str, int]:
        """Generate all creature assets for the mod."""
        results = {
            'tiles_created': 0,
            'sprites_created': 0
        }
        
        # Check for ObjectBlueprints.xml
        blueprints_path = self.mod_path / "ObjectBlueprints.xml"
        if blueprints_path.exists():
            creatures = self.analyze_object_blueprints(blueprints_path)
            
            for creature in creatures:
                if creature['needs_tile']:
                    # Determine base creature type from name
                    name_lower = creature['name'].lower()
                    if 'ant' in name_lower or 'drone' in name_lower:
                        base = 'ant'
                    elif 'beetle' in name_lower:
                        base = 'beetle'
                    elif 'moth' in name_lower:
                        base = 'moth'
                    elif 'leech' in name_lower:
                        base = 'leech'
                    else:
                        base = 'insect'
                    
                    # Extract tier from name if present
                    tier_match = re.search(r'_T(\d+)', creature['name'])
                    tier = int(tier_match.group(1)) if tier_match else 1
                    
                    # Get description for Ollama
                    description = creature.get('description', f"A {base} broodling")
                    
                    tile = self.generate_broodling_tile(
                        creature['name'],
                        tier=tier,
                        base_creature=base,
                        color_code=creature['color'],
                        description=description
                    )
                    
                    if tile:
                        results['tiles_created'] += 1
        
        return results

