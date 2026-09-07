"""
Space Whale Visual Asset Generator
Generates visual language assets: color palettes, material definitions, style guides.
"""

import json
import os
import math
import random
from PIL import Image, ImageDraw, ImageFilter, ImageChops
import colorsys

class VisualAssetGenerator:
    """Generates visual language assets for space whale."""
    
    def __init__(self, registry_path: str):
        with open(registry_path, 'r') as f:
            self.registry = json.load(f)
        
        self.visual_lang = self.registry.get('visualLanguage', {})
    
    def hex_to_rgb(self, hex_color: str) -> tuple:
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def rgb_to_hex(self, rgb: tuple) -> str:
        """Convert RGB tuple to hex color."""
        return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
    
    def generate_color_palette_swatch(self, palette_name: str, palette_data: dict, output_path: str, size: tuple = (400, 300)):
        """Generate color palette swatch image."""
        img = Image.new('RGB', size, color='#000000')
        draw = ImageDraw.Draw(img)
        
        colors = {
            'Base': palette_data.get('baseColor', '#000000'),
            'Vein': palette_data.get('veinColor', '#000000'),
            'Carapace': palette_data.get('carapaceColor', '#000000'),
            'Emissive': palette_data.get('emissiveColor', '#000000'),
            'Accent': palette_data.get('accentColor', '#000000')
        }
        
        swatch_size = (size[0] // len(colors), size[1] // 2)
        y_offset = size[1] // 4
        
        for i, (name, color) in enumerate(colors.items()):
            x = i * swatch_size[0]
            y = y_offset
            
            # Draw color swatch
            draw.rectangle([x, y, x + swatch_size[0], y + swatch_size[1]], fill=color)
            
            # Draw label
            draw.text((x + 5, y + swatch_size[1] + 5), name, fill='#ffffff')
            draw.text((x + 5, y + swatch_size[1] + 20), color, fill='#ffffff')
        
        img.save(output_path)
        print(f"Generated color palette: {output_path}")
    
    @staticmethod
    def _lerp(a: tuple, b: tuple, t: float) -> tuple:
        return tuple(int(ca + (cb - ca) * t) for ca, cb in zip(a, b))

    def generate_material_preview(self, material_name: str, material_data: dict, output_path: str, size: tuple = (256, 256)):
        """Generate a RICH material preview sphere (not a flat disc).

        Layers a radial background gradient, a shaded 3D-looking sphere (diffuse
        falloff from an offset key light), a rim/back light, a specular hotspot,
        emission bloom, and fine grain — so the preview reads as a lit material
        sample instead of a flat programmer-art circle.
        """
        props = material_data.get('properties', {})
        base_color = self.hex_to_rgb(props.get('baseColor', '#1a2a3a'))
        emission = props.get('emission', {})
        emission_color = self.hex_to_rgb(emission.get('color', '#66ccff'))
        has_emission = emission.get('intensity', 0) > 0

        w, h = size
        cx, cy = w // 2, h // 2
        radius = int(min(w, h) * 0.34)

        # --- Radial background gradient (dark vignette) ---
        bg_inner = self._lerp(base_color, (0, 0, 0), 0.55)
        bg_outer = (0, 0, 0)
        img = Image.new('RGBA', size)
        px = img.load()
        maxd = math.hypot(cx, cy)
        for y in range(h):
            for x in range(w):
                t = min(1.0, math.hypot(x - cx, y - cy) / maxd)
                r, g, b = self._lerp(bg_inner, bg_outer, t ** 1.3)
                px[x, y] = (r, g, b, 255)

        # --- Shaded sphere: diffuse falloff from an offset key light ---
        lx, ly = cx - radius * 0.4, cy - radius * 0.45  # key light direction (top-left)
        highlight = self._lerp(base_color, (255, 255, 255), 0.55)
        shadow = self._lerp(base_color, (0, 0, 0), 0.6)
        r2 = radius * radius
        for y in range(cy - radius, cy + radius + 1):
            if y < 0 or y >= h:
                continue
            for x in range(cx - radius, cx + radius + 1):
                if x < 0 or x >= w:
                    continue
                dx, dy = x - cx, y - cy
                d2 = dx * dx + dy * dy
                if d2 > r2:
                    continue
                # Fake normal-based lambert using distance from the light point.
                ld = math.hypot(x - lx, y - ly) / (radius * 1.8)
                shade = max(0.0, min(1.0, 1.0 - ld))
                # Ambient floor so the dark side isn't pure black.
                shade = 0.18 + shade * 0.82
                col = self._lerp(shadow, highlight, shade)
                # Soft edge anti-alias near the silhouette.
                edge = 1.0 - max(0.0, (math.sqrt(d2) - (radius - 2)) / 2.0)
                a = int(255 * max(0.0, min(1.0, edge)))
                if a <= 0:
                    continue
                bx = px[x, y]
                px[x, y] = (*self._lerp(bx[:3], col, a / 255.0), 255)

        draw = ImageDraw.Draw(img, 'RGBA')

        # --- Rim / back light along the lower-right crescent ---
        rim_col = self._lerp(base_color, (200, 220, 255), 0.7)
        draw.arc(
            [cx - radius, cy - radius, cx + radius, cy + radius],
            start=20, end=150, fill=(*rim_col, 180), width=max(2, radius // 18),
        )

        # --- Specular hotspot ---
        spec_r = max(3, radius // 6)
        sx, sy = int(cx - radius * 0.35), int(cy - radius * 0.4)
        spec = Image.new('RGBA', size, (0, 0, 0, 0))
        sdraw = ImageDraw.Draw(spec)
        sdraw.ellipse([sx - spec_r, sy - spec_r, sx + spec_r, sy + spec_r], fill=(255, 255, 255, 200))
        spec = spec.filter(ImageFilter.GaussianBlur(spec_r * 0.6))
        img = Image.alpha_composite(img, spec)

        # --- Emission bloom halo ---
        if has_emission:
            glow_radius = int(radius * 1.35)
            glow_img = Image.new('RGBA', size, (0, 0, 0, 0))
            gdraw = ImageDraw.Draw(glow_img)
            gdraw.ellipse(
                [cx - glow_radius, cy - glow_radius, cx + glow_radius, cy + glow_radius],
                fill=(*emission_color, 90),
            )
            glow_img = glow_img.filter(ImageFilter.GaussianBlur(radius=14))
            img = Image.alpha_composite(glow_img, img)

        # --- Fine grain for tactility ---
        try:
            grain = Image.effect_noise(size, 12).convert('L')
            grain_rgba = Image.merge('RGBA', (grain, grain, grain, Image.new('L', size, 40)))
            img = ImageChops.overlay(img.convert('RGBA'), grain_rgba)
        except Exception:
            pass

        draw = ImageDraw.Draw(img, 'RGBA')
        # Label with shadow for legibility over the gradient.
        draw.text((11, 11), material_name, fill=(0, 0, 0, 200))
        draw.text((10, 10), material_name, fill='#ffffff')

        img.save(output_path)
        print(f"Generated material preview: {output_path}")
    
    def generate_texture_pattern_preview(self, pattern_name: str, pattern_data: dict, output_path: str, size: tuple = (256, 256)):
        """Generate texture pattern preview."""
        img = Image.new('RGB', size, color='#1a2a3a')
        draw = ImageDraw.Draw(img)
        
        method = pattern_data.get('method', 'noise_texture')
        params = pattern_data.get('parameters', {})
        
        if method == 'noise_texture':
            # Simulate noise texture
            import random
            random.seed(42)
            scale = params.get('scale', 5.0)
            
            for y in range(0, size[1], 4):
                for x in range(0, size[0], 4):
                    noise_val = random.random()
                    intensity = int(noise_val * 255)
                    color = (intensity, intensity, intensity)
                    draw.rectangle([x, y, x + 4, y + 4], fill=color)
        
        elif method == 'voronoi':
            # Simulate Voronoi pattern
            import random
            random.seed(42)
            scale = params.get('scale', 3.0)
            
            # Create Voronoi-like cells
            cell_size = int(size[0] / scale)
            for y in range(0, size[1], cell_size):
                for x in range(0, size[0], cell_size):
                    intensity = random.randint(100, 200)
                    color = (intensity, intensity, intensity)
                    draw.rectangle([x, y, x + cell_size, y + cell_size], fill=color)
        
        elif method == 'sine_wave':
            # Simulate sine wave pattern
            import math
            frequency = params.get('frequency', 0.8)
            amplitude = params.get('amplitude', 0.05)
            
            for x in range(size[0]):
                y_offset = int(size[1] // 2 + size[1] * amplitude * 
                             (1 + math.sin(2 * math.pi * frequency * x / size[0])))
                draw.line([(x, y_offset - 2), (x, y_offset + 2)], fill='#66ccff', width=2)
        
        # Add label
        draw.text((10, 10), pattern_name, fill='#ffffff')
        
        img.save(output_path)
        print(f"Generated texture pattern: {output_path}")
    
    def generate_style_guide(self, output_path: str):
        """Generate comprehensive visual style guide."""
        guide = []
        guide.append("# Space Whale Visual Language Style Guide\n")
        guide.append("Generated from visual language registry.\n\n")
        
        # Aesthetic
        aesthetic = self.visual_lang.get('aesthetic', {})
        guide.append("## Aesthetic\n\n")
        guide.append(f"**Base Style**: {aesthetic.get('baseStyle', 'N/A')}\n")
        guide.append(f"**Adaptation**: {aesthetic.get('adaptation', 'N/A')}\n\n")
        guide.append("### Principles\n")
        for principle in aesthetic.get('principles', []):
            guide.append(f"- {principle}\n")
        guide.append("\n")
        
        # Color Palettes
        palettes = self.visual_lang.get('colorPalettes', {})
        guide.append("## Color Palettes\n\n")
        for name, palette in palettes.items():
            guide.append(f"### {palette.get('name', name)}\n")
            guide.append(f"**Use Case**: {palette.get('useCase', 'N/A')}\n")
            guide.append(f"**Description**: {palette.get('description', 'N/A')}\n\n")
            guide.append("Colors:\n")
            guide.append(f"- Base: {palette.get('baseColor', 'N/A')}\n")
            guide.append(f"- Vein: {palette.get('veinColor', 'N/A')}\n")
            guide.append(f"- Carapace: {palette.get('carapaceColor', 'N/A')}\n")
            guide.append(f"- Emissive: {palette.get('emissiveColor', 'N/A')}\n")
            guide.append(f"- Accent: {palette.get('accentColor', 'N/A')}\n\n")
        
        # Materials
        materials = self.visual_lang.get('materials', {})
        guide.append("## Materials\n\n")
        for name, material in materials.items():
            guide.append(f"### {material.get('name', name)}\n")
            guide.append(f"**Type**: {material.get('type', 'N/A')}\n")
            guide.append(f"**Shader**: {material.get('shader', 'N/A')}\n\n")
            props = material.get('properties', {})
            guide.append("Properties:\n")
            for prop_name, prop_value in props.items():
                if isinstance(prop_value, dict):
                    guide.append(f"- {prop_name}:\n")
                    for sub_name, sub_value in prop_value.items():
                        guide.append(f"  - {sub_name}: {sub_value}\n")
                else:
                    guide.append(f"- {prop_name}: {prop_value}\n")
            guide.append("\n")
        
        # Animations
        animations = self.visual_lang.get('animations', {})
        guide.append("## Animations\n\n")
        for name, anim in animations.items():
            guide.append(f"### {anim.get('name', name)}\n")
            guide.append(f"**Type**: {anim.get('type', 'N/A')}\n")
            guide.append(f"**Method**: {anim.get('method', 'N/A')}\n")
            guide.append(f"**Use Case**: {anim.get('useCase', 'N/A')}\n\n")
        
        # Effects
        effects = self.visual_lang.get('effects', {})
        guide.append("## Effects\n\n")
        for name, effect in effects.items():
            guide.append(f"### {effect.get('name', name)}\n")
            guide.append(f"**Type**: {effect.get('type', 'N/A')}\n")
            guide.append(f"**Use Case**: {effect.get('useCase', 'N/A')}\n\n")
        
        with open(output_path, 'w') as f:
            f.write(''.join(guide))
        
        print(f"Generated style guide: {output_path}")
    
    def generate_all_assets(self, output_dir: str):
        """Generate all visual language assets."""
        os.makedirs(output_dir, exist_ok=True)
        
        # Color palette swatches
        palettes = self.visual_lang.get('colorPalettes', {})
        palette_dir = os.path.join(output_dir, 'color_palettes')
        os.makedirs(palette_dir, exist_ok=True)
        
        for name, palette in palettes.items():
            swatch_path = os.path.join(palette_dir, f"{name}_swatch.png")
            self.generate_color_palette_swatch(name, palette, swatch_path)
        
        # Material previews
        materials = self.visual_lang.get('materials', {})
        material_dir = os.path.join(output_dir, 'materials')
        os.makedirs(material_dir, exist_ok=True)
        
        for name, material in materials.items():
            preview_path = os.path.join(material_dir, f"{name}_preview.png")
            self.generate_material_preview(name, material, preview_path)
        
        # Texture pattern previews
        patterns = self.visual_lang.get('texturePatterns', {})
        pattern_dir = os.path.join(output_dir, 'texture_patterns')
        os.makedirs(pattern_dir, exist_ok=True)
        
        for name, pattern in patterns.items():
            preview_path = os.path.join(pattern_dir, f"{name}_preview.png")
            self.generate_texture_pattern_preview(name, pattern, preview_path)
        
        # Style guide
        style_guide_path = os.path.join(output_dir, 'VISUAL_STYLE_GUIDE.md')
        self.generate_style_guide(style_guide_path)
        
        print(f"\nAll visual language assets generated in: {output_dir}")

if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate space whale visual language assets')
    parser.add_argument('--registry', required=True, help='Path to visual language registry JSON')
    parser.add_argument('--output', required=True, help='Output directory for assets')
    
    args = parser.parse_args()
    
    generator = VisualAssetGenerator(args.registry)
    generator.generate_all_assets(args.output)
    print("\nVisual language asset generation complete!")

