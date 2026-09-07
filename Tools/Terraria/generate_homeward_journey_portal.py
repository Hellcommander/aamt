#!/usr/bin/env python3
"""
Generate Homeward Journey Portal Assets
Creates animated spritesheet and item icon for the Homeward Journey portal
Theme: Cyan/blue with starry/journey aesthetic
"""

import os
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter
import math

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, ValueError):
        pass

def create_portal_frame(frame_num: int, total_frames: int = 8) -> Image.Image:
    """
    Create a single 16x16 portal frame with cyan/blue theme.
    Frame animates with pulsing effect and rotating stars.
    """
    img = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Animation phase (0.0 to 1.0)
    phase = frame_num / total_frames
    
    # Center point
    center_x, center_y = 8, 8
    
    # Outer ring - cyan/blue glow
    outer_radius = 7 + math.sin(phase * math.pi * 2) * 0.5
    inner_radius = 5 + math.sin(phase * math.pi * 2) * 0.3
    
    # Draw outer glow ring
    for angle in range(0, 360, 5):
        rad = math.radians(angle)
        x1 = center_x + math.cos(rad) * outer_radius
        y1 = center_y + math.sin(rad) * outer_radius
        x2 = center_x + math.cos(rad) * inner_radius
        y2 = center_y + math.sin(rad) * inner_radius
        
        # Cyan to blue gradient
        intensity = (math.sin(phase * math.pi * 2 + angle / 10) + 1) / 2
        r = int(51 * intensity)  # 0.2 * 255
        g = int(204 + 51 * intensity)  # 0.8-1.0 * 255
        b = 255
        
        # Draw glow line
        draw.line([(x1, y1), (x2, y2)], fill=(r, g, b, 200), width=1)
    
    # Inner portal core - darker blue with stars
    core_radius = 4
    draw.ellipse(
        [center_x - core_radius, center_y - core_radius,
         center_x + core_radius, center_y + core_radius],
        fill=(20, 80, 150, 180),
        outline=(51, 204, 255, 255)
    )
    
    # Add rotating stars (4 stars rotating around center)
    star_radius = 5
    for i in range(4):
        star_angle = (phase * 360 + i * 90) % 360
        rad = math.radians(star_angle)
        star_x = center_x + math.cos(rad) * star_radius
        star_y = center_y + math.sin(rad) * star_radius
        
        # Draw small star
        star_size = 1
        draw.ellipse(
            [star_x - star_size, star_y - star_size,
             star_x + star_size, star_y + star_size],
            fill=(255, 255, 255, 255)
        )
        # Cross pattern for star
        draw.line([(star_x - 2, star_y), (star_x + 2, star_y)], fill=(255, 255, 255, 200), width=1)
        draw.line([(star_x, star_y - 2), (star_x, star_y + 2)], fill=(255, 255, 255, 200), width=1)
    
    # Add central bright point
    draw.ellipse(
        [center_x - 1, center_y - 1,
         center_x + 1, center_y + 1],
        fill=(255, 255, 255, 255)
    )
    
    # Add particle effects (cyan sparkles)
    for i in range(3):
        particle_angle = (phase * 360 + i * 120) % 360
        rad = math.radians(particle_angle)
        particle_radius = 6 + math.sin(phase * math.pi * 4 + i) * 1
        particle_x = center_x + math.cos(rad) * particle_radius
        particle_y = center_y + math.sin(rad) * particle_radius
        
        if 0 <= particle_x < 16 and 0 <= particle_y < 16:
            draw.ellipse(
                [particle_x - 0.5, particle_y - 0.5,
                 particle_x + 0.5, particle_y + 0.5],
                fill=(51, 204, 255, 180)
            )
    
    return img

def create_spritesheet(output_path: Path):
    """Create 8-frame animated spritesheet (128x16)."""
    print("Creating Homeward Journey portal spritesheet...")
    
    # Create spritesheet: 8 frames of 16x16 = 128x16
    spritesheet = Image.new('RGBA', (128, 16), (0, 0, 0, 0))
    
    for frame in range(8):
        frame_img = create_portal_frame(frame, 8)
        # Paste frame at correct position
        x_offset = frame * 16
        spritesheet.paste(frame_img, (x_offset, 0))
    
    spritesheet.save(output_path, 'PNG')
    print(f"✓ Spritesheet saved: {output_path}")
    return spritesheet

def create_item_icon(output_path: Path):
    """Create 16x16 item icon (first frame of animation)."""
    print("Creating Homeward Journey portal item icon...")
    
    # Use first frame as item icon
    icon = create_portal_frame(0, 8)
    
    # Make it slightly brighter for item icon
    icon = icon.point(lambda p: min(255, int(p * 1.2)))
    
    icon.save(output_path, 'PNG')
    print(f"✓ Item icon saved: {output_path}")
    return icon

def main():
    """Generate all Homeward Journey portal assets."""
    # Determine output directory
    # Try multiple possible locations
    script_dir = Path(__file__).parent.absolute()
    
    # Try to find CrossModStabilizer mod directory
    # Check current working directory first (most reliable)
    cwd = Path.cwd()
    if (cwd / "Assets").exists() or (cwd / "CrossModStabilizer.cs").exists():
        mod_dir = cwd
    else:
        # Try other possible locations
        possible_paths = [
            Path("D:/User_Directories/Documents/My Games/Terraria/tModLoader/ModSources/CrossModStabilizer"),
            Path("E:/SteamLibrary/steamapps/common/tModLoader/ModSources/CrossModStabilizer"),
            script_dir.parent.parent.parent / "CrossModStabilizer",
            cwd / "CrossModStabilizer",
        ]
        
        mod_dir = None
        for path in possible_paths:
            if path.exists() and ((path / "Assets").exists() or (path / "CrossModStabilizer.cs").exists()):
                mod_dir = path
                break
        
        if mod_dir is None:
            # Use current working directory as fallback
            mod_dir = cwd
            print(f"Warning: Could not find mod directory, using: {mod_dir}")
    
    assets_dir = mod_dir / "Assets"
    tiles_dir = assets_dir / "Tiles"
    items_dir = assets_dir / "Items"
    
    # Create directories if they don't exist
    tiles_dir.mkdir(parents=True, exist_ok=True)
    items_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("Homeward Journey Portal Asset Generator")
    print("=" * 60)
    print(f"Output directory: {assets_dir}")
    print()
    
    # Generate spritesheet
    spritesheet_path = tiles_dir / "HomewardJourneyPortal_spritesheet.png"
    create_spritesheet(spritesheet_path)
    
    # Generate item icon
    item_path = items_dir / "HomewardJourneyPortalItem.png"
    create_item_icon(item_path)
    
    print()
    print("=" * 60)
    print("✓ All assets generated successfully!")
    print("=" * 60)
    print(f"Spritesheet: {spritesheet_path}")
    print(f"Item icon: {item_path}")
    print()
    print("Note: The portal uses cyan/blue theme with rotating stars")
    print("      representing the journey home theme.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

