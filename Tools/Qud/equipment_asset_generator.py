#!/usr/bin/env python3
"""
Equipment Asset Generator for Caves of Qud Mods
Generates visual assets for equipment items like the broodling sack.
Supports Ollama-powered design generation for higher quality assets.
"""

import os
import re
import sys
import math
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


class EquipmentAssetGenerator:
    """Generates visual assets for equipment."""
    
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
        """Initialize equipment asset generator.
        
        Args:
            mod_path: Path to mod directory
            use_ollama: Whether to use Ollama for AI-powered design
            candidates: Number of candidate designs to generate
            tile_size: Tile size in pixels (default 48 for high quality, supports tile scaling mod)
        """
        self.mod_path = Path(mod_path)
        self.textures_path = self.mod_path / "Textures"
        self.visuals_path = self.mod_path / "Visuals"
        self.equipment_path = self.textures_path / "Equipment"
        self.biomod_path = self.textures_path / "Biomod"
        
        # Create directories - Textures is the standard location
        self.textures_path.mkdir(exist_ok=True)
        self.equipment_path.mkdir(parents=True, exist_ok=True)
        self.biomod_path.mkdir(parents=True, exist_ok=True)
        
        # Tile size for high quality assets (supports tile scaling mod)
        self.tile_size = tile_size
        self.icon_size = tile_size * 2  # Icons are typically 2x tiles
        
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
    
    def generate_sack_tile(self, sack_name: str = "Broodling_Sack",
                          color_code: str = "&m", size: Tuple[int, int] = None,
                          description: str = "A pulsating chitinous sack") -> Optional[Path]:
        """
        Generate a tile for the broodling sack.
        Uses Ollama for design if available, falls back to procedural generation.
        
        Args:
            sack_name: Name of the sack object
            color_code: Qud color code
            size: Tile size
            description: Description for Ollama design generation
        
        Returns:
            Path to generated tile
        """
        tile_path = self.equipment_path / f"{sack_name}_tile.png"
        
        # Use default size if not specified
        if size is None:
            size = (self.tile_size, self.tile_size)
        
        if tile_path.exists():
            return tile_path
        
        try:
            # Try Ollama generation if available
            if self.use_ollama and self.ollama_gen:
                candidates = []
                for i in range(self.candidates):
                    try:
                        design = self.ollama_gen.generate_equipment_design(
                            sack_name, description, "sack", color_code
                        )
                        if design is None:
                            continue
                        img = self._render_equipment_from_design(design, size, "sack")
                        quality = self.ollama_gen.assess_asset_quality(img)
                        candidates.append({
                            'image': img,
                            'design': design,
                            'quality': quality
                        })
                    except Exception as e:
                        print(f"      Warning: Ollama candidate {i+1} failed: {e}")
                        continue
                
                if candidates:
                    # Select best candidate
                    candidates.sort(key=lambda x: x['quality']['score'], reverse=True)
                    best = candidates[0]
                    img = best['image']
                    print(f"      [Equipment Assets] Created sack tile (Ollama, score: {best['quality']['score']:.2f}): {tile_path.name}")
                else:
                    print(f"      [Equipment Assets] SKIPPED: All Ollama candidates failed. Will use base game assets instead.")
                    return None
            else:
                print(f"      [Equipment Assets] SKIPPED: Ollama not available. Will use base game assets instead.")
                return None
            
            img.save(tile_path, 'PNG')
            return tile_path
            
        except Exception as e:
            print(f"      [Equipment Assets] Failed to create sack tile: {e}")
            return None
    
    def _generate_procedural_sack(self, color_code: str, size: Tuple[int, int]) -> Image.Image:
        """Generate procedural sack (fallback) with high quality detail."""
        img = Image.new('RGBA', size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        color = self._parse_color_code(color_code)
        center_x, center_y = size[0] // 2, size[1] // 2
        
        # Scale detail based on tile size
        scale = size[0] / 32.0
        line_width = max(1, int(scale))
        
        # Draw sack shape (organic, bulging) - scaled for high quality
        body_width = int(20 * scale)
        body_height = int(24 * scale)
        draw.ellipse([center_x - body_width//2, center_y - body_height//2,
                     center_x + body_width//2, center_y + body_height//2],
                    fill=color, outline=(255, 255, 255), width=line_width)
        
        # Add texture detail (chitinous segments)
        for i in range(int(4 * scale)):
            segment_y = center_y - body_height//2 + (i * body_height // (4 * scale))
            draw.line([center_x - body_width//2 + 2, segment_y,
                      center_x + body_width//2 - 2, segment_y],
                     fill=(color[0] - 20, color[1] - 20, color[2] - 20), width=1)
        
        # Bulges (eggs/broodlings inside) - more detail at higher resolution
        bulge_count = int(3 * scale)
        for i in range(bulge_count):
            angle = (i / bulge_count) * 6.28
            bulge_x = center_x + int(8 * scale * math.cos(angle))
            bulge_y = center_y + int(6 * scale * math.sin(angle))
            bulge_size = int(4 * scale)
            draw.ellipse([bulge_x - bulge_size, bulge_y - bulge_size,
                        bulge_x + bulge_size, bulge_y + bulge_size],
                       fill=(color[0] + 20, color[1] + 20, color[2] + 20),
                       outline=(255, 255, 255), width=line_width)
            # Highlight on bulges
            draw.ellipse([bulge_x - bulge_size//2, bulge_y - bulge_size//2,
                        bulge_x + bulge_size//2, bulge_y + bulge_size//2],
                       fill=(color[0] + 40, color[1] + 40, color[2] + 40))
        
        # Opening/top with more detail
        opening_width = int(12 * scale)
        opening_height = int(6 * scale)
        draw.ellipse([center_x - opening_width//2, center_y - body_height//2 - opening_height,
                     center_x + opening_width//2, center_y - body_height//2],
                    fill=(color[0] - 40, color[1] - 40, color[2] - 40),
                    outline=(255, 255, 255), width=line_width)
        
        # Add rim lighting for depth
        for i in range(int(3 * scale)):
            rim_y = center_y - body_height//2 + i
            alpha = int(100 * (1 - i / (3 * scale)))
            rim_color = (255, 255, 255, alpha)
            draw.line([center_x - body_width//2, rim_y, center_x + body_width//2, rim_y],
                     fill=rim_color, width=1)
        
        return img
    
    def _render_equipment_from_design(self, design: Dict, size: Tuple[int, int], item_type: str) -> Image.Image:
        """Render equipment image from Ollama design specification with high quality detail."""
        img = Image.new('RGBA', size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        center_x, center_y = size[0] // 2, size[1] // 2
        color_scheme = design.get('colorScheme', {})
        primary = self.ollama_gen.hex_to_rgb(color_scheme.get('primary', '#808080'))
        secondary = self.ollama_gen.hex_to_rgb(color_scheme.get('secondary', '#ffffff'))
        outline = self.ollama_gen.hex_to_rgb(color_scheme.get('outline', '#000000'))
        detail = self.ollama_gen.hex_to_rgb(color_scheme.get('detail', '#ffffff'))
        
        # Scale detail based on tile size
        scale = size[0] / 32.0
        line_width = max(1, int(scale * 0.5))
        
        if item_type == "sack":
            # Enhanced sack rendering based on design with high quality detail
            shape = design.get('shape', {})
            form = shape.get('form', 'bulging organic sack')
            texture = design.get('texture', {})
            texture_style = texture.get('style', 'smooth chitin')
            
            # Main body with scaled detail
            body_width = int(20 * scale)
            body_height = int(24 * scale)
            draw.ellipse([center_x - body_width//2, center_y - body_height//2,
                         center_x + body_width//2, center_y + body_height//2],
                        fill=primary, outline=outline, width=line_width * 2)
            
            # Add texture based on design
            if 'segmented' in texture_style.lower() or 'chitin' in texture_style.lower():
                # Chitinous segments
                segment_count = int(6 * scale)
                for i in range(segment_count):
                    segment_y = center_y - body_height//2 + (i * body_height // segment_count)
                    draw.line([center_x - body_width//2 + 2, segment_y,
                              center_x + body_width//2 - 2, segment_y],
                             fill=(primary[0] - 15, primary[1] - 15, primary[2] - 15), width=1)
            
            # Internal bulges (more detailed at higher resolution)
            bulge_count = int(5 * scale)
            for i in range(bulge_count):
                angle = (i / bulge_count) * 6.28
                bulge_x = center_x + int(8 * scale * math.cos(angle))
                bulge_y = center_y + int(6 * scale * math.sin(angle))
                bulge_size = int(5 * scale)
                draw.ellipse([bulge_x - bulge_size, bulge_y - bulge_size,
                            bulge_x + bulge_size, bulge_y + bulge_size],
                           fill=secondary, outline=outline, width=line_width)
                # Highlight
                draw.ellipse([bulge_x - bulge_size//2, bulge_y - bulge_size//2,
                            bulge_x + bulge_size//2, bulge_y + bulge_size//2],
                           fill=(secondary[0] + 30, secondary[1] + 30, secondary[2] + 30))
            
            # Top opening with detail
            opening_width = int(16 * scale)
            opening_height = int(8 * scale)
            draw.ellipse([center_x - opening_width//2, center_y - body_height//2 - opening_height,
                         center_x + opening_width//2, center_y - body_height//2],
                        fill=(primary[0] - 40, primary[1] - 40, primary[2] - 40),
                        outline=outline, width=line_width * 2)
            
            # Add rim lighting for depth
            for i in range(int(4 * scale)):
                rim_y = center_y - body_height//2 + i
                alpha = int(80 * (1 - i / (4 * scale)))
                rim_color = (*detail, alpha)
                draw.line([center_x - body_width//2, rim_y, center_x + body_width//2, rim_y],
                          fill=rim_color, width=1)
        
        return img
    
    def generate_sack_icon(self, sack_name: str = "Broodling_Sack",
                          color_code: str = "&m", size: Tuple[int, int] = None) -> Optional[Path]:
        """Generate an icon for the sack (for UI/inventory)."""
        icon_path = self.equipment_path / f"{sack_name}_icon.png"
        
        # Use default size if not specified
        if size is None:
            size = (self.icon_size, self.icon_size)
        
        if icon_path.exists():
            return icon_path
        
        try:
            img = Image.new('RGBA', size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            color = self._parse_color_code(color_code)
            center_x, center_y = size[0] // 2, size[1] // 2
            
            # Draw more detailed sack for icon
            # Main body
            body_width = 40
            body_height = 50
            draw.ellipse([center_x - body_width//2, center_y - body_height//2,
                         center_x + body_width//2, center_y + body_height//2],
                        fill=color, outline=(255, 255, 255), width=2)
            
            # Internal bulges (more visible in icon)
            for i in range(4):
                angle = (i / 4) * 6.28  # 2*pi
                bulge_x = center_x + int(8 * (i % 2 - 0.5))
                bulge_y = center_y + int(10 * (i // 2 - 0.5))
                draw.ellipse([bulge_x - 5, bulge_y - 5, bulge_x + 5, bulge_y + 5],
                            fill=(color[0] + 30, color[1] + 30, color[2] + 30),
                            outline=(255, 255, 255), width=1)
            
            # Top opening
            draw.ellipse([center_x - 12, center_y - body_height//2 - 5,
                         center_x + 12, center_y - body_height//2 + 5],
                        fill=(color[0] - 40, color[1] - 40, color[2] - 40),
                        outline=(255, 255, 255), width=2)
            
            img.save(icon_path, 'PNG')
            print(f"      [Equipment Assets] Created sack icon: {icon_path.name}")
            return icon_path
            
        except Exception as e:
            print(f"      [Equipment Assets] Failed to create sack icon: {e}")
            return None
    
    def generate_nest_seed_icon(self, seed_name: str, color_code: str = "&m",
                               size: Tuple[int, int] = (32, 32)) -> Optional[Path]:
        """Generate an icon for a nest seed."""
        icon_path = self.equipment_path / f"{seed_name}_icon.png"
        
        if icon_path.exists():
            return icon_path
        
        try:
            img = Image.new('RGBA', size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            color = self._parse_color_code(color_code)
            center_x, center_y = size[0] // 2, size[1] // 2
            
            # Draw seed shape (small, organic, pulsating)
            radius = 8
            draw.ellipse([center_x - radius, center_y - radius,
                         center_x + radius, center_y + radius],
                        fill=color, outline=(255, 255, 255), width=1)
            
            # Inner pulse (represents life/energy)
            inner_radius = 4
            draw.ellipse([center_x - inner_radius, center_y - inner_radius,
                         center_x + inner_radius, center_y + inner_radius],
                        fill=(color[0] + 30, color[1] + 30, color[2] + 30),
                        outline=(255, 255, 255), width=1)
            
            img.save(icon_path, 'PNG')
            print(f"      [Equipment Assets] Created nest seed icon: {icon_path.name}")
            return icon_path
            
        except Exception as e:
            print(f"      [Equipment Assets] Failed to create nest seed icon: {e}")
            return None
    
    def generate_nest_tile(self, nest_name: str, color_code: str = "&m",
                          size: Tuple[int, int] = (32, 32)) -> Optional[Path]:
        """Generate a tile for a nest (furniture)."""
        tile_path = self.equipment_path / f"{nest_name}_tile.png"
        
        if tile_path.exists():
            return tile_path
        
        try:
            img = Image.new('RGBA', size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            color = self._parse_color_code(color_code)
            center_x, center_y = size[0] // 2, size[1] // 2
            
            # Draw nest shape (larger, web-like structure)
            # Main body
            draw.ellipse([center_x - 14, center_y - 10,
                         center_x + 14, center_y + 10],
                        fill=color, outline=(255, 255, 255), width=1)
            
            # Web-like structure (lines radiating outward)
            for i in range(8):
                angle = (i / 8) * 6.28
                x1 = center_x + int(10 * (1 if i < 4 else -1))
                y1 = center_y + int(6 * (1 if i % 2 == 0 else -1))
                x2 = center_x + int(14 * (1 if i < 4 else -1))
                y2 = center_y + int(10 * (1 if i % 2 == 0 else -1))
                draw.line([x1, y1, x2, y2], fill=(255, 255, 255), width=1)
            
            # Cocoons inside (small circles)
            for i in range(3):
                cocoon_x = center_x - 6 + (i * 6)
                cocoon_y = center_y
                draw.ellipse([cocoon_x - 2, cocoon_y - 2,
                            cocoon_x + 2, cocoon_y + 2],
                           fill=(color[0] + 20, color[1] + 20, color[2] + 20),
                           outline=(255, 255, 255), width=1)
            
            img.save(tile_path, 'PNG')
            print(f"      [Equipment Assets] Created nest tile: {tile_path.name}")
            return tile_path
            
        except Exception as e:
            print(f"      [Equipment Assets] Failed to create nest tile: {e}")
            return None
    
    def _parse_color_code(self, color_code: str) -> Tuple[int, int, int]:
        """Parse Qud color code to RGB."""
        code = color_code.replace('&', '').replace('^', '').strip()
        if code and code[0] in self.COLORS:
            return self.COLORS[code[0]]
        return (128, 0, 128)  # Default magenta
    
    def analyze_object_blueprints(self, blueprints_path: Path) -> List[Dict[str, any]]:
        """Analyze ObjectBlueprints.xml to find equipment that needs assets."""
        equipment = []
        
        if not blueprints_path.exists():
            return equipment
        
        try:
            tree = ET.parse(blueprints_path)
            root = tree.getroot()
            
            for obj in root.findall('.//object'):
                name = obj.get('Name', '')
                
                # Check if it's equipment (has Armor part or inherits Armor)
                has_armor = obj.find('.//part[@Name="Armor"]') is not None
                inherits_armor = 'Armor' in obj.get('Inherits', '')
                is_furniture = 'Furniture' in obj.get('Inherits', '')
                
                # Include sacks, nest seeds, and furniture items
                if has_armor or inherits_armor or 'Sack' in name or 'Nest' in name or is_furniture:
                    render = obj.find('.//part[@Name="Render"]')
                    if render is not None:
                        tile = render.get('Tile', '')
                        color = render.get('TileColor', render.get('ColorString', '&m'))
                        
                        # Get description for Ollama
                        desc_part = obj.find('.//part[@Name="Description"]')
                        description = desc_part.get('Short', '') if desc_part is not None else ''
                        
                        equipment.append({
                            'name': name,
                            'tile': tile,
                            'color': color,
                            'description': description,
                            'needs_tile': not tile or not Path(tile).exists(),
                            'is_sack': 'Sack' in name,
                            'is_nest': 'Nest' in name
                        })
        
        except Exception as e:
            print(f"      [Equipment Assets] Failed to parse ObjectBlueprints.xml: {e}")
        
        return equipment
    
    def generate_biomod_icon(self, biomod_name: str, display_name: str,
                             color_code: str = "&m", size: Tuple[int, int] = None,
                             description: str = "") -> Optional[Path]:
        """
        Generate an icon for a biomod.
        Uses Ollama for design if available, falls back to procedural generation.
        
        Args:
            biomod_name: Name of the biomod object (e.g., "ModBroodSack_GestationSpeed")
            display_name: Display name (e.g., "gestation accelerator")
            color_code: Qud color code
            size: Icon size
            description: Description for Ollama design generation
        
        Returns:
            Path to generated icon
        """
        # Clean up the name for filename
        clean_name = biomod_name.replace("ModBroodSack_", "")
        icon_path = self.biomod_path / f"{clean_name}_icon.png"
        
        # Use default size if not specified
        if size is None:
            size = (self.tile_size, self.tile_size)
        
        if icon_path.exists():
            return icon_path
        
        try:
            # Try Ollama generation if available
            if self.use_ollama and self.ollama_gen and description:
                candidates = []
                for i in range(self.candidates):
                    try:
                        design = self.ollama_gen.generate_biomod_design(
                            biomod_name, display_name, description, color_code
                        )
                        if design is None:
                            continue
                        img = self._render_biomod_from_design(design, size)
                        quality = self.ollama_gen.assess_asset_quality(img)
                        candidates.append({
                            'image': img,
                            'design': design,
                            'quality': quality
                        })
                    except Exception as e:
                        continue
                
                if candidates:
                    candidates.sort(key=lambda x: x['quality']['score'], reverse=True)
                    best = candidates[0]
                    img = best['image']
                    print(f"      [Equipment Assets] Created biomod icon (Ollama, score: {best['quality']['score']:.2f}): {icon_path.name}")
                else:
                    print(f"      [Equipment Assets] SKIPPED: All Ollama candidates failed. Will use base game assets instead.")
                    return None
            else:
                print(f"      [Equipment Assets] SKIPPED: Ollama not available. Will use base game assets instead.")
                return None
            
            img.save(icon_path, 'PNG')
            return icon_path
            
        except Exception as e:
            print(f"      [Equipment Assets] Failed to create biomod icon: {e}")
            return None
    
    def _generate_procedural_biomod(self, color_code: str, size: Tuple[int, int]) -> Image.Image:
        """Generate procedural biomod icon (fallback) with high quality detail."""
        img = Image.new('RGBA', size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        color = self._parse_color_code(color_code)
        center_x, center_y = size[0] // 2, size[1] // 2
        
        # Scale detail based on tile size
        scale = size[0] / 32.0
        line_width = max(1, int(scale * 0.5))
        
        # Draw biomod icon (scaled for high quality)
        radius = int(12 * scale)
        draw.ellipse([center_x - radius, center_y - radius,
                     center_x + radius, center_y + radius],
                    fill=color, outline=(255, 255, 255), width=line_width)
        
        # Inner detail
        inner_radius = int(6 * scale)
        draw.ellipse([center_x - inner_radius, center_y - inner_radius,
                     center_x + inner_radius, center_y + inner_radius],
                    fill=(color[0] + 40, color[1] + 40, color[2] + 40),
                    outline=(255, 255, 255), width=line_width)
        
        # Small accent lines (more at higher resolution)
        line_count = int(8 * scale)
        for i in range(line_count):
            angle = (i / line_count) * 6.28
            x1 = center_x + int((radius - 2) * 0.7 * math.cos(angle))
            y1 = center_y + int((radius - 2) * 0.7 * math.sin(angle))
            x2 = center_x + int(radius * math.cos(angle))
            y2 = center_y + int(radius * math.sin(angle))
            draw.line([x1, y1, x2, y2], fill=(255, 255, 255), width=line_width)
        
        return img
    
    def _render_biomod_from_design(self, design: Dict, size: Tuple[int, int]) -> Image.Image:
        """Render biomod icon from Ollama design specification."""
        img = Image.new('RGBA', size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        center_x, center_y = size[0] // 2, size[1] // 2
        color_scheme = design.get('colorScheme', {})
        primary = self.ollama_gen.hex_to_rgb(color_scheme.get('primary', '#808080'))
        secondary = self.ollama_gen.hex_to_rgb(color_scheme.get('secondary', '#ffffff'))
        outline = self.ollama_gen.hex_to_rgb(color_scheme.get('outline', '#000000'))
        detail = self.ollama_gen.hex_to_rgb(color_scheme.get('detail', '#ffffff'))
        
        symbol = design.get('symbol', {})
        shape_desc = symbol.get('shape', 'circular node')
        complexity = symbol.get('complexity', 'medium')
        
        # Enhanced rendering based on design
        radius = 12
        if 'hexagonal' in shape_desc.lower():
            # Hexagonal shape
            points = []
            for i in range(6):
                angle = (i / 6) * 6.28
                x = center_x + radius * math.cos(angle)
                y = center_y + radius * math.sin(angle)
                points.append((x, y))
            draw.polygon(points, fill=primary, outline=outline, width=2)
        elif 'spiral' in shape_desc.lower():
            # Spiral pattern
            draw.ellipse([center_x - radius, center_y - radius,
                         center_x + radius, center_y + radius],
                        fill=primary, outline=outline, width=2)
            # Spiral lines
            for i in range(8):
                angle = (i / 8) * 6.28
                x1 = center_x + int(4 * math.cos(angle))
                y1 = center_y + int(4 * math.sin(angle))
                x2 = center_x + int(radius * math.cos(angle))
                y2 = center_y + int(radius * math.sin(angle))
                draw.line([x1, y1, x2, y2], fill=detail, width=1)
        else:
            # Default circular
            draw.ellipse([center_x - radius, center_y - radius,
                         center_x + radius, center_y + radius],
                        fill=primary, outline=outline, width=2)
        
        # Inner detail
        inner_radius = 6
        draw.ellipse([center_x - inner_radius, center_y - inner_radius,
                     center_x + inner_radius, center_y + inner_radius],
                    fill=secondary, outline=outline, width=1)
        
        # Radiating lines if specified
        if 'radiating' in shape_desc.lower() or complexity == 'high':
            for i in range(8):
                angle = (i / 8) * 6.28
                x1 = center_x + int((radius - 2) * 0.7 * math.cos(angle))
                y1 = center_y + int((radius - 2) * 0.7 * math.sin(angle))
                x2 = center_x + int(radius * math.cos(angle))
                y2 = center_y + int(radius * math.sin(angle))
                draw.line([x1, y1, x2, y2], fill=detail, width=1)
        
        return img
    
    def analyze_biomod_xml(self, biomod_xml_path: Path) -> List[Dict[str, any]]:
        """Analyze BroodlingSackMods.xml to find biomods that need assets."""
        biomods = []
        
        if not biomod_xml_path.exists():
            return biomods
        
        try:
            tree = ET.parse(biomod_xml_path)
            root = tree.getroot()
            
            for obj in root.findall('.//object'):
                name = obj.get('Name', '')
                
                # Only process biomods (ModBroodSack_*)
                if name.startswith('ModBroodSack_'):
                    render = obj.find('.//part[@Name="Render"]')
                    if render is not None:
                        display_name = render.get('DisplayName', name)
                        color = render.get('ColorString', '&m')
                        
                        # Get description for Ollama
                        desc_part = obj.find('.//part[@Name="Description"]')
                        description = desc_part.get('Short', '') if desc_part is not None else ''
                        
                        biomods.append({
                            'name': name,
                            'display_name': display_name,
                            'color': color,
                            'description': description,
                            'needs_icon': True
                        })
        
        except Exception as e:
            print(f"      [Equipment Assets] Failed to parse BroodlingSackMods.xml: {e}")
        
        return biomods
    
    def generate_all_equipment_assets(self) -> Dict[str, int]:
        """Generate all equipment assets for the mod."""
        results = {
            'tiles_created': 0,
            'icons_created': 0,
            'biomod_icons_created': 0
        }
        
        # Check for ObjectBlueprints.xml
        blueprints_path = self.mod_path / "ObjectBlueprints.xml"
        if blueprints_path.exists():
            equipment = self.analyze_object_blueprints(blueprints_path)
            
            for item in equipment:
                if item['needs_tile']:
                    if item['is_sack']:
                        # Generate sack assets
                        description = item.get('description', 'A pulsating chitinous sack')
                        tile = self.generate_sack_tile(item['name'], item['color'], description=description)
                        if tile:
                            results['tiles_created'] += 1
                        
                        icon = self.generate_sack_icon(item['name'], item['color'])
                        if icon:
                            results['icons_created'] += 1
                    elif item['is_nest']:
                        # Generate nest/seed assets
                        if 'Seed' in item['name']:
                            # Nest seed - smaller, seed-like
                            icon = self.generate_nest_seed_icon(item['name'], item['color'])
                            if icon:
                                results['icons_created'] += 1
                        else:
                            # Nest furniture - larger
                            tile = self.generate_nest_tile(item['name'], item['color'])
                            if tile:
                                results['tiles_created'] += 1
        
        # Check for BroodlingSackMods.xml (biomods)
        biomod_xml_path = self.mod_path / "BroodlingSackMods.xml"
        if biomod_xml_path.exists():
            biomods = self.analyze_biomod_xml(biomod_xml_path)
            
            for biomod in biomods:
                if biomod['needs_icon']:
                    icon = self.generate_biomod_icon(
                        biomod['name'],
                        biomod['display_name'],
                        biomod['color'],
                        description=biomod.get('description', '')
                    )
                    if icon:
                        results['biomod_icons_created'] += 1
        
        return results

