#!/usr/bin/env python3
"""
Mutation Asset Generator for Caves of Qud Mods
Generates visual assets for mutations: icons, tiles, ability markers, etc.
Uses Ollama AI tools when available for high-quality asset generation.
"""

import os
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont
import xml.etree.ElementTree as ET

# Import Ollama integration if available
_ollama_path = os.path.join(os.path.dirname(__file__), "..", "Shared", "ollama_integration.py")
OLLAMA_AVAILABLE = False
call_ollama = None
test_ollama_connection = None

if os.path.exists(_ollama_path):
    try:
        shared_dir = os.path.join(os.path.dirname(__file__), "..", "Shared")
        if shared_dir not in sys.path:
            sys.path.insert(0, shared_dir)
        from ollama_integration import call_ollama, test_ollama_connection
        OLLAMA_AVAILABLE = True
    except ImportError:
        OLLAMA_AVAILABLE = False


class MutationAssetGenerator:
    """Generates visual assets for mutations."""
    
    # Color palette for mutations (Qud color codes)
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
    
    def __init__(self, mod_path: Path, use_ai: bool = True):
        """Initialize mutation asset generator."""
        self.mod_path = Path(mod_path)
        self.textures_path = self.mod_path / "Textures"
        self.assets_path = self.mod_path / "Assets"
        self.visuals_path = self.mod_path / "Visuals"
        self.resources_path = self.assets_path / "Resources" if self.assets_path.exists() else None
        
        # Create directories - Textures is the standard location for Qud mod assets
        self.textures_path.mkdir(exist_ok=True)
        self.visuals_path.mkdir(exist_ok=True)
        if self.assets_path.exists():
            self.resources_path = self.assets_path / "Resources"
            self.resources_path.mkdir(exist_ok=True)
        
        # Check for Ollama availability
        self.use_ai = use_ai and OLLAMA_AVAILABLE
        if self.use_ai:
            try:
                self.ollama_available = test_ollama_connection()
                if self.ollama_available:
                    print("  [AI] Ollama available - using AI tools for asset generation")
                else:
                    print("  [WARNING] Ollama not running - falling back to procedural generation")
                    self.use_ai = False
            except:
                print("  [WARNING] Could not test Ollama - falling back to procedural generation")
                self.use_ai = False
        else:
            self.ollama_available = False
    
    def generate_mutation_icon(self, mutation_name: str, mutation_type: str = "Mental", size: Tuple[int, int] = (64, 64)) -> Optional[Path]:
        """
        Generate an icon for a mutation.
        Uses AI tools (Ollama) when available for high-quality generation.
        
        Args:
            mutation_name: Name of the mutation
            mutation_type: Type (Mental, Physical, Defect, etc.)
            size: Icon size (width, height)
        
        Returns:
            Path to generated icon, or None if failed
        """
        # Place in Textures folder (Qud standard)
        icon_path = self.textures_path / f"{mutation_name}_icon.png"
        
        if icon_path.exists():
            return icon_path
        
        # Try AI generation first if available
        if self.use_ai and self.ollama_available:
            try:
                return self._generate_icon_with_ai(mutation_name, mutation_type, size, icon_path)
            except Exception as e:
                print(f"      [Mutation Assets] AI generation failed: {e}, falling back to procedural")
        
        # Fallback to procedural generation
        try:
            # Create 32-bit PNG with alpha (Qud standard for ability icons)
            img = Image.new('RGBA', size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            # Choose color based on type
            type_colors = {
                'Mental': (100, 150, 255),      # Blue
                'Physical': (255, 100, 100),    # Red
                'Defect': (150, 150, 150),      # Gray
                'Cybernetics': (255, 200, 0),   # Yellow
            }
            color = type_colors.get(mutation_type, (200, 200, 200))
            
            # Draw circular icon with gradient effect
            margin = 4
            center_x, center_y = size[0] // 2, size[1] // 2
            radius = (size[0] - margin * 2) // 2
            
            # Outer glow
            for i in range(3):
                glow_radius = radius + i
                alpha = 50 - (i * 15)
                glow_color = (*color, alpha)
                draw.ellipse([center_x - glow_radius, center_y - glow_radius,
                             center_x + glow_radius, center_y + glow_radius],
                            fill=glow_color, outline=None)
            
            # Main circle with gradient effect
            draw.ellipse([margin, margin, size[0]-margin, size[1]-margin], 
                        fill=color, outline=(255, 255, 255), width=3)
            
            # Inner highlight
            highlight_margin = margin + 8
            highlight_color = tuple(min(255, c + 40) for c in color)
            draw.ellipse([highlight_margin, highlight_margin, 
                         size[0]-highlight_margin, size[1]-highlight_margin],
                        fill=highlight_color, outline=None)
            
            # Draw symbol based on mutation name
            symbol = self._get_mutation_symbol(mutation_name)
            if symbol:
                # Try to use a font, fallback to simple drawing
                try:
                    font_size = min(size[0], size[1]) // 2
                    font = ImageFont.truetype("arial.ttf", font_size)
                except:
                    try:
                        font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 32)
                    except:
                        font = ImageFont.load_default()
                
                bbox = draw.textbbox((0, 0), symbol, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                position = ((size[0] - text_width) // 2, (size[1] - text_height) // 2 - 2)
                # Draw with shadow for better visibility
                draw.text((position[0] + 1, position[1] + 1), symbol, fill=(0, 0, 0, 128), font=font)
                draw.text(position, symbol, fill=(255, 255, 255), font=font)
            
            img.save(icon_path, 'PNG')
            print(f"      [Mutation Assets] Created icon: {icon_path.name}")
            return icon_path
            
        except Exception as e:
            print(f"      [Mutation Assets] Failed to create icon: {e}")
            return None
    
    def _generate_icon_with_ai(self, mutation_name: str, mutation_type: str, 
                               size: Tuple[int, int], icon_path: Path) -> Optional[Path]:
        """Generate mutation icon using Ollama AI tools."""
        prompt = f"""Design a {mutation_name} mutation icon for Caves of Qud ({mutation_type} mutation).

Return ONLY valid JSON with these exact fields:
{{
  "symbol": {{
    "shape": "appropriate symbol for {mutation_name}",
    "complexity": "high",
    "distinctiveElements": ["relevant visual elements"]
  }},
  "colorScheme": {{
    "primary": "hex color",
    "secondary": "hex color",
    "glow": "hex color",
    "outline": "hex color"
  }}
}}

Use appropriate colors for a {mutation_type} mutation. Return JSON ONLY."""
        
        try:
            print(f"      [AI] Generating {mutation_name} icon with Ollama...")
            response = call_ollama(
                prompt=prompt,
                task_type="visual",
                response_length="standard",
                system_prompt="You are a pixel art designer specializing in roguelike game icons. Always return valid JSON only. Use tools to ensure quality.",
                use_tools=True
            )
            
            if response:
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response[json_start:json_end]
                    json_str = re.sub(r'(\w+):', r'"\1":', json_str)
                    json_str = re.sub(r'""(\w+)"":', r'"\1":', json_str)
                    
                    design = json.loads(json_str)
                    if 'symbol' in design and 'colorScheme' in design:
                        # Render based on AI design
                        img = self._render_icon_from_design(design, mutation_type, size)
                        try:
                            from vortex_quality import finalize_qud_sprite, validate_sprite_quality
                            img = finalize_qud_sprite(img, target_size=size)
                            ok, reason = validate_sprite_quality(img, min_edge_density=0.04)
                            if not ok:
                                print(f"      [QUALITY WARN] {reason}")
                        except ImportError:
                            pass
                        img.save(icon_path, 'PNG')
                        print(f"      [AI OK] Created icon: {icon_path.name}")
                        return icon_path
        except Exception as e:
            print(f"      [AI ERROR] {e}")
            raise
        
        return None
    
    def _render_icon_from_design(self, design: Dict, mutation_type: str, size: Tuple[int, int]) -> Image.Image:
        """Render icon from AI design."""
        try:
            from qud_procedural_render import render_rich_mutation_icon
            return render_rich_mutation_icon(design, mutation_type, size)
        except ImportError:
            pass

        img = Image.new('RGBA', size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        center_x, center_y = size[0] // 2, size[1] // 2
        cs = design.get('colorScheme', {})
        
        def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
            hex_color = hex_color.lstrip('#')
            if len(hex_color) == 6:
                return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            return (128, 128, 128)
        
        primary = hex_to_rgb(cs.get('primary', '#4a90e2'))
        secondary = hex_to_rgb(cs.get('secondary', '#7bb3f0'))
        glow = hex_to_rgb(cs.get('glow', '#00ffff'))
        outline = hex_to_rgb(cs.get('outline', '#1a1a4a'))
        
        # Outer glow
        for i in range(5, 0, -1):
            radius = center_x - (i * 2)
            if radius > 0:
                alpha = int(30 * (1 - i / 5))
                glow_color = (*glow, alpha)
                draw.ellipse([center_x - radius, center_y - radius, center_x + radius, center_y + radius],
                           fill=glow_color, outline=None)
        
        # Main circle
        margin = 4
        draw.ellipse([margin, margin, size[0]-margin, size[1]-margin], 
                    fill=primary, outline=outline, width=3)
        
        # Inner highlight
        highlight_margin = margin + 8
        highlight_color = tuple(min(255, c + 40) for c in primary)
        draw.ellipse([highlight_margin, highlight_margin, 
                     size[0]-highlight_margin, size[1]-highlight_margin],
                    fill=highlight_color, outline=None)
        
        return img
    
    def _get_mutation_symbol(self, mutation_name: str) -> str:
        """Get a symbol character for the mutation."""
        name_lower = mutation_name.lower()
        
        # Space-Time Vortex
        if 'vortex' in name_lower or 'space' in name_lower or 'time' in name_lower:
            return '◉'  # Circle with dot (singularity)
        
        # Broodmother
        if 'brood' in name_lower or 'mother' in name_lower:
            return '●'  # Filled circle (egg/sack)
        
        # Teleportation
        if 'teleport' in name_lower:
            return '↯'  # Lightning
        
        # Fire/Ice
        if 'fire' in name_lower or 'flame' in name_lower:
            return '🔥'
        if 'ice' in name_lower or 'frost' in name_lower:
            return '❄'
        
        # Default: first letter
        return mutation_name[0].upper() if mutation_name else '?'
    
    def generate_ability_marker(self, ability_name: str, color_code: str = "&M", size: Tuple[int, int] = (32, 32)) -> Optional[Path]:
        """
        Generate a visual marker for an activated ability.
        
        Args:
            ability_name: Name of the ability
            color_code: Qud color code (e.g., "&M" for magenta)
            size: Marker size
        
        Returns:
            Path to generated marker
        """
        # Place in Textures folder (Qud standard)
        marker_path = self.textures_path / f"{ability_name}_marker.png"
        
        if marker_path.exists():
            return marker_path
        
        try:
            img = Image.new('RGBA', size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            # Parse color code
            color = self._parse_color_code(color_code)
            
            # Draw diamond shape (ability marker)
            center_x, center_y = size[0] // 2, size[1] // 2
            points = [
                (center_x, 2),
                (size[0] - 2, center_y),
                (center_x, size[1] - 2),
                (2, center_y)
            ]
            draw.polygon(points, fill=color, outline=(255, 255, 255), width=1)
            
            img.save(marker_path, 'PNG')
            print(f"      [Mutation Assets] Created ability marker: {marker_path.name}")
            return marker_path
            
        except Exception as e:
            print(f"      [Mutation Assets] Failed to create marker: {e}")
            return None
    
    def _parse_color_code(self, color_code: str) -> Tuple[int, int, int]:
        """Parse Qud color code to RGB."""
        # Remove & and ^ modifiers
        code = color_code.replace('&', '').replace('^', '').strip()
        if code and code[0] in self.COLORS:
            return self.COLORS[code[0]]
        return (200, 200, 200)  # Default gray
    
    def generate_vortex_visuals(self, mod_path: Path) -> Dict[str, Path]:
        """Generate visual assets for Space-Time Vortex mutation."""
        generated = {}
        
        # Black hole visual (singularity) - animated frames for effect
        black_hole = self._generate_singularity_visual("BlackHole", (32, 32), (0, 0, 0))
        if black_hole:
            generated['black_hole'] = black_hole
            # Generate animated frames for pulsing effect
            self._generate_animated_frames("BlackHole", 4, (32, 32), (0, 0, 0))
        
        # White hole visual (rupture) - animated frames for effect
        white_hole = self._generate_singularity_visual("WhiteHole", (32, 32), (255, 255, 200))
        if white_hole:
            generated['white_hole'] = white_hole
            # Generate animated frames for pulsing effect
            self._generate_animated_frames("WhiteHole", 4, (32, 32), (255, 255, 200))
        
        # Warning marker (pre-spawn)
        warning = self._generate_warning_marker("VortexWarning", (32, 32))
        if warning:
            generated['warning'] = warning
        
        return generated
    
    def _generate_animated_frames(self, name: str, frame_count: int, size: Tuple[int, int], base_color: Tuple[int, int, int]) -> List[Path]:
        """Generate animated frames for AnimatedMaterialGeneric effects."""
        frames = []
        
        for i in range(frame_count):
            frame_path = self.textures_path / f"{name}_frame{i:02d}.png"
            
            if frame_path.exists():
                frames.append(frame_path)
                continue
            
            try:
                # Create frame with varying intensity
                img = Image.new('RGBA', size, (0, 0, 0, 0))
                draw = ImageDraw.Draw(img)
                
                center_x, center_y = size[0] // 2, size[1] // 2
                
                # Vary intensity based on frame (pulsing effect)
                intensity = 0.5 + (0.5 * (i / frame_count))
                color = tuple(int(c * intensity) for c in base_color)
                
                # Draw concentric circles with varying opacity
                for j in range(5, 0, -1):
                    radius = center_x - (j * 2)
                    if radius > 0:
                        alpha = int(255 * intensity * (1 - j / 5))
                        frame_color = (*color, alpha)
                        draw.ellipse(
                            [center_x - radius, center_y - radius, center_x + radius, center_y + radius],
                            fill=frame_color, outline=(255, 255, 255, 128), width=1
                        )
                
                img.save(frame_path, 'PNG')
                frames.append(frame_path)
            except Exception as e:
                print(f"      [Mutation Assets] Failed to create frame {i}: {e}")
        
        return frames
    
    def _generate_singularity_visual(self, name: str, size: Tuple[int, int], base_color: Tuple[int, int, int]) -> Optional[Path]:
        """Generate a singularity/black hole visual."""
        # Place in Textures folder (Qud standard)
        visual_path = self.textures_path / f"{name}_visual.png"
        
        if visual_path.exists():
            return visual_path
        
        try:
            img = Image.new('RGBA', size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            center_x, center_y = size[0] // 2, size[1] // 2
            
            # Draw concentric circles (event horizon effect)
            for i in range(5, 0, -1):
                radius = center_x - (i * 4)
                if radius > 0:
                    # Fade color toward center
                    alpha = int(255 * (1 - i / 5))
                    color = (*base_color, alpha)
                    draw.ellipse(
                        [center_x - radius, center_y - radius, center_x + radius, center_y + radius],
                        fill=color, outline=(255, 255, 255, 128), width=1
                    )
            
            # Center point
            draw.ellipse([center_x - 2, center_y - 2, center_x + 2, center_y + 2], 
                        fill=(255, 255, 255), outline=(0, 0, 0))
            
            img.save(visual_path, 'PNG')
            print(f"      [Mutation Assets] Created {name} visual: {visual_path.name}")
            return visual_path
            
        except Exception as e:
            print(f"      [Mutation Assets] Failed to create {name}: {e}")
            return None
    
    def _generate_warning_marker(self, name: str, size: Tuple[int, int]) -> Optional[Path]:
        """Generate a warning marker for pre-spawn indicators."""
        # Place in Textures folder (Qud standard)
        marker_path = self.textures_path / f"{name}_marker.png"
        
        if marker_path.exists():
            return marker_path
        
        try:
            img = Image.new('RGBA', size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            # Draw pulsing circle
            center_x, center_y = size[0] // 2, size[1] // 2
            
            # Outer ring (warning color - yellow/orange)
            draw.ellipse([2, 2, size[0]-2, size[1]-2], 
                        fill=(255, 200, 0, 128), outline=(255, 150, 0), width=2)
            
            # Inner pulsing dot
            draw.ellipse([center_x - 4, center_y - 4, center_x + 4, center_y + 4],
                        fill=(255, 100, 0), outline=(255, 200, 0))
            
            img.save(marker_path, 'PNG')
            print(f"      [Mutation Assets] Created warning marker: {marker_path.name}")
            return marker_path
            
        except Exception as e:
            print(f"      [Mutation Assets] Failed to create warning marker: {e}")
            return None
    
    def analyze_mutations_xml(self, mutations_xml_path: Path) -> List[Dict[str, any]]:
        """Analyze Mutations.xml to find mutations that need assets."""
        mutations = []
        
        # Base game mutations that should be skipped (they already have icons)
        BASE_GAME_MUTATIONS = {
            'Horns', 'Multiple Legs', 'Multiple Arms', 'Carapace', 'Spinnerets',
            'Stinger', 'Two-headed', 'TwoHeaded', 'Three-headed', 'Four-headed',
            'Hydra Heads', 'Animal Legs', 'Fluffy Tail', 'Wings', 'Armless',
            'Hooks for Feet', 'Muzzle', 'Regeneration', 'Quills', 'Burrowing Claws',
            'Life Drain', 'Confusion', 'Temporal Fugue', 'Force Wall'
        }
        
        if not mutations_xml_path.exists():
            return mutations
        
        try:
            tree = ET.parse(mutations_xml_path)
            root = tree.getroot()
            
            for mutation in root.findall('.//mutation'):
                name = mutation.get('Name', '')
                
                # Skip base game mutations
                if name in BASE_GAME_MUTATIONS:
                    continue
                
                # Skip hidden mutations (usually compatibility entries)
                if mutation.get('Hidden', '').lower() == 'true':
                    continue
                
                # Skip mutations that are just references to base game classes
                # (they have a Class attribute but it's a base game class, not a custom one)
                mutation_class = mutation.get('Class', '')
                if mutation_class and not mutation_class.startswith(('Arendeth_', 'FIM_', 'Improved_', 'Mod_')):
                    # Check if it's a known base game class
                    base_game_classes = {'Horns', 'MultipleLegs', 'MultipleArms', 'Carapace', 
                                        'Spinnerets', 'Armless', 'HooksForFeet', 'Muzzle'}
                    if mutation_class in base_game_classes:
                        continue
                
                mutation_type = mutation.get('Type', 'Mental')
                mutations.append({
                    'name': name,
                    'type': mutation_type,
                    'needs_icon': True,
                    'needs_marker': True
                })
        
        except Exception as e:
            print(f"      [Mutation Assets] Failed to parse Mutations.xml: {e}")
        
        return mutations
    
    def generate_all_mutation_assets(self) -> Dict[str, int]:
        """Generate all mutation assets for the mod."""
        results = {
            'icons_created': 0,
            'markers_created': 0,
            'visuals_created': 0
        }
        
        # Check for Mutations.xml
        mutations_xml = self.mod_path / "Mutations.xml"
        if mutations_xml.exists():
            mutations = self.analyze_mutations_xml(mutations_xml)
            
            for mutation in mutations:
                # Generate icon
                icon = self.generate_mutation_icon(mutation['name'], mutation['type'])
                if icon:
                    results['icons_created'] += 1
                
                # Generate ability markers (if it's an activated ability mutation)
                # This would need to check the C# code to see if it has abilities
                # For now, we'll generate based on mutation name patterns
                if 'vortex' in mutation['name'].lower() or 'space' in mutation['name'].lower():
                    # Special handling for Space-Time Vortex
                    visuals = self.generate_vortex_visuals(self.mod_path)
                    results['visuals_created'] += len(visuals)
        
        return results

