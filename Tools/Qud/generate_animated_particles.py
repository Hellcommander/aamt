#!/usr/bin/env python3
"""
Generate animated particle sprites for Space-Time Vortex
Creates 8-frame animations for each particle type
"""

import os
import sys
from pathlib import Path
from typing import Tuple
from PIL import Image, ImageDraw, ImageFilter
import math

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except:
        pass


class AnimatedParticleGenerator:
    """Generate animated particle sprites."""
    
    def __init__(self, mod_path: Path):
        self.mod_path = Path(mod_path)
        self.textures_path = self.mod_path / "Textures"
        self.textures_path.mkdir(exist_ok=True)
    
    def generate_animated_spark(self, color: Tuple[int, int, int], name: str, size: Tuple[int, int] = (16, 16)):
        """Generate 8-frame animated spark particle with high-quality rendering."""
        frames = []
        
        for frame in range(8):
            img = Image.new('RGBA', size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            cx, cy = size[0] // 2, size[1] // 2
            
            # Rotation for this frame
            rotation = (frame / 8) * (2 * math.pi)
            
            # Pulsing size with smooth curve
            pulse = 0.7 + (0.3 * math.sin(frame * math.pi / 4))
            
            # High-quality spark with 8 rays (instead of 4) and gradients
            num_rays = 8
            for i in range(num_rays):
                angle = rotation + (i * 2 * math.pi / num_rays)
                length = int(7 * pulse)
                
                # Draw ray with gradient
                ray_points = 10
                for j in range(ray_points):
                    t = j / ray_points
                    x = int(cx + length * t * math.cos(angle))
                    y = int(cy + length * t * math.sin(angle))
                    
                    if 0 <= x < size[0] and 0 <= y < size[1]:
                        # Gradient from bright center to dim tip
                        alpha = int(255 * (1 - t * 0.6))
                        thickness = int(3 * (1 - t * 0.5))
                        if thickness > 0:
                            draw.ellipse([x - thickness, y - thickness, x + thickness, y + thickness],
                                       fill=(*color, alpha), outline=None)
                
                # Add glow at tip
                tip_x = int(cx + length * math.cos(angle))
                tip_y = int(cy + length * math.sin(angle))
                if 0 <= tip_x < size[0] and 0 <= tip_y < size[1]:
                    draw.ellipse([tip_x - 2, tip_y - 2, tip_x + 2, tip_y + 2],
                               fill=(*color, 150), outline=None)
            
            # Layered bright center with glow
            center_size = int(3 * pulse)
            for i in range(3, 0, -1):
                glow_size = center_size * (i / 3)
                alpha = int(200 * (1 - i / 3))
                draw.ellipse([cx - glow_size, cy - glow_size, cx + glow_size, cy + glow_size],
                           fill=(*color, alpha), outline=None)
            
            # Apply smooth filter
            img = img.filter(ImageFilter.SMOOTH)
            frames.append(img)
        
        return frames
    
    def generate_animated_swirl(self, color: Tuple[int, int, int], name: str, size: Tuple[int, int] = (16, 16)):
        """Generate 8-frame animated swirl particle with high-quality rendering."""
        frames = []
        
        for frame in range(8):
            img = Image.new('RGBA', size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            cx, cy = size[0] // 2, size[1] // 2
            
            # Rotation for this frame
            rotation = (frame / 8) * (2 * math.pi)
            
            # High-quality spiral with many points and gradient
            spiral_points = 40  # More points for smoother spiral
            for i in range(spiral_points):
                t = i / spiral_points
                angle = rotation + (t * 6 * math.pi)  # More turns
                radius = t * 7
                x = int(cx + radius * math.cos(angle))
                y = int(cy + radius * math.sin(angle))
                
                if 0 <= x < size[0] and 0 <= y < size[1]:
                    # Gradient from bright center to dim edge
                    alpha = int(255 * (1 - t * 0.7))
                    # Thickness varies along spiral
                    thickness = int(2.5 * (1 - t * 0.4))
                    if thickness > 0:
                        draw.ellipse([x - thickness, y - thickness, x + thickness, y + thickness],
                                   fill=(*color, alpha), outline=None)
                    
                    # Add glow around points near center
                    if t < 0.5:
                        glow_size = thickness + 1
                        glow_alpha = int(100 * (1 - t * 2))
                        draw.ellipse([x - glow_size, y - glow_size, x + glow_size, y + glow_size],
                                   fill=(*color, glow_alpha), outline=None)
            
            # Bright center with layered glow
            for i in range(3, 0, -1):
                center_radius = 2 * (i / 3)
                alpha = int(220 * (1 - i / 3))
                draw.ellipse([cx - center_radius, cy - center_radius, cx + center_radius, cy + center_radius],
                           fill=(*color, alpha), outline=None)
            
            # Apply smooth filter
            img = img.filter(ImageFilter.SMOOTH)
            frames.append(img)
        
        return frames
    
    def generate_animated_dot(self, color: Tuple[int, int, int], name: str, size: Tuple[int, int] = (16, 16)):
        """Generate 8-frame animated pulsing dot with high-quality rendering."""
        frames = []
        
        for frame in range(8):
            img = Image.new('RGBA', size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            cx, cy = size[0] // 2, size[1] // 2
            
            # Pulsing size with smooth curve
            pulse = 0.5 + (0.5 * math.sin(frame * math.pi / 4))
            dot_size = int(5 * pulse)
            
            # Layered outer glow with gradient
            for i in range(5, 0, -1):
                glow_size = int((6 + i * 1.5) * pulse)
                alpha = int(80 * pulse * (1 - i / 5))
                if glow_size > 0 and alpha > 0:
                    draw.ellipse([cx - glow_size, cy - glow_size, cx + glow_size, cy + glow_size],
                               fill=(*color, alpha), outline=None)
            
            # Main dot with gradient layers
            for i in range(3, 0, -1):
                layer_size = dot_size * (i / 3)
                alpha = int(255 * (1 - i / 3))
                draw.ellipse([cx - layer_size, cy - layer_size, cx + layer_size, cy + layer_size],
                           fill=(*color, alpha), outline=None)
            
            # Bright center core
            core_size = int(2 * pulse)
            if core_size > 0:
                # Make center slightly brighter/whiter
                bright_color = tuple(min(255, c + 30) for c in color)
                draw.ellipse([cx - core_size, cy - core_size, cx + core_size, cy + core_size],
                           fill=(*bright_color, 255), outline=None)
            
            # Apply smooth filter
            img = img.filter(ImageFilter.SMOOTH)
            frames.append(img)
        
        return frames
    
    def generate_all(self):
        """Generate all animated particle sprites."""
        print("=" * 60)
        print("Animated Particle Generator")
        print("=" * 60)
        print()
        
        particles = [
            ("spark", "purple", (200, 0, 255)),
            ("spark", "cyan", (0, 255, 255)),
            ("swirl", "purple", (200, 0, 255)),
            ("swirl", "white", (255, 255, 255)),
            ("dot", "magenta", (255, 0, 255)),
            ("dot", "yellow", (255, 255, 0))
        ]
        
        total_frames = 0
        
        for ptype, color_name, color in particles:
            print(f"Generating {ptype}_{color_name} (8 frames)...")
            
            if ptype == "spark":
                frames = self.generate_animated_spark(color, f"{ptype}_{color_name}")
            elif ptype == "swirl":
                frames = self.generate_animated_swirl(color, f"{ptype}_{color_name}")
            else:  # dot
                frames = self.generate_animated_dot(color, f"{ptype}_{color_name}")
            
            # Save all frames
            for i, frame in enumerate(frames):
                frame_path = self.textures_path / f"VortexParticle_{ptype}_{color_name}_frame{i:02d}.png"
                frame.save(frame_path, 'PNG')
                total_frames += 1
            
            print(f"  ✓ Created 8 frames")
        
        print()
        print("=" * 60)
        print(f"Complete: {total_frames} animated particle frames")
        print("=" * 60)
        print()
        print("Particles will automatically animate when used with VortexAnimatedParticlePatch!")
        print()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate animated particle sprites")
    parser.add_argument("mod_path", help="Path to mod directory")
    args = parser.parse_args()
    
    mod_path = Path(args.mod_path)
    if not mod_path.exists():
        print(f"ERROR: Mod path not found: {mod_path}")
        return 1
    
    try:
        generator = AnimatedParticleGenerator(mod_path)
        generator.generate_all()
        return 0
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
