#!/usr/bin/env python3
"""
Generate Origins Mod Biome Portal Assets
Creates animated spritesheets and item icons for Origins biome portals:
- Defiled Wastelands: Desaturated gray-purple theme
- Riven Hive: Blue-teal aquatic/bug-like theme
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

def create_defiled_portal_frame(frame_num: int, total_frames: int = 8) -> Image.Image:
    """
    Create a single 16x16 portal frame for Defiled Wastelands.
    Theme: Desaturated gray-purple with bleak, wasteland aesthetic.
    """
    img = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Animation phase (0.0 to 1.0)
    phase = frame_num / total_frames
    
    # Center point
    center_x, center_y = 8, 8
    
    # Outer ring - desaturated gray-purple glow
    outer_radius = 7 + math.sin(phase * math.pi * 2) * 0.5
    inner_radius = 5 + math.sin(phase * math.pi * 2) * 0.3
    
    # Draw outer glow ring (desaturated purple-gray)
    for angle in range(0, 360, 5):
        rad = math.radians(angle)
        x1 = center_x + math.cos(rad) * outer_radius
        y1 = center_y + math.sin(rad) * outer_radius
        x2 = center_x + math.cos(rad) * inner_radius
        y2 = center_y + math.sin(rad) * inner_radius
        
        # Desaturated gray-purple gradient
        intensity = (math.sin(phase * math.pi * 2 + angle / 10) + 1) / 2
        r = int(100 + 20 * intensity)  # 100-120 (desaturated)
        g = int(100 + 20 * intensity)  # 100-120 (desaturated)
        b = int(120 + 30 * intensity)  # 120-150 (slight purple)
        
        # Draw glow line
        draw.line([(x1, y1), (x2, y2)], fill=(r, g, b, 200), width=1)
    
    # Inner portal core - darker desaturated purple
    core_radius = 4
    draw.ellipse(
        [center_x - core_radius, center_y - core_radius,
         center_x + core_radius, center_y + core_radius],
        fill=(60, 60, 80, 180),
        outline=(100, 100, 120, 255)
    )
    
    # Add desaturated spikes/particles (wasteland theme)
    spike_count = 6
    for i in range(spike_count):
        spike_angle = (phase * 360 + i * 60) % 360
        rad = math.radians(spike_angle)
        spike_radius = 5.5 + math.sin(phase * math.pi * 4 + i) * 0.5
        spike_x = center_x + math.cos(rad) * spike_radius
        spike_y = center_y + math.sin(rad) * spike_radius
        
        # Draw small desaturated spike
        spike_size = 1
        draw.ellipse(
            [spike_x - spike_size, spike_y - spike_size,
             spike_x + spike_size, spike_y + spike_size],
            fill=(120, 120, 140, 255)
        )
        # Cross pattern for spike
        draw.line([(spike_x - 1.5, spike_y), (spike_x + 1.5, spike_y)], fill=(100, 100, 120, 200), width=1)
        draw.line([(spike_x, spike_y - 1.5), (spike_x, spike_y + 1.5)], fill=(100, 100, 120, 200), width=1)
    
    # Add central dim point
    draw.ellipse(
        [center_x - 1, center_y - 1,
         center_x + 1, center_y + 1],
        fill=(150, 150, 170, 255)
    )
    
    # Add desaturated particle effects
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
                fill=(100, 100, 120, 180)
            )
    
    return img

def create_riven_portal_frame(frame_num: int, total_frames: int = 8) -> Image.Image:
    """
    Create a single 16x16 portal frame for Riven Hive.
    Theme: Blue-teal aquatic/bug-like with exoskeletal aesthetic.
    """
    img = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Animation phase (0.0 to 1.0)
    phase = frame_num / total_frames
    
    # Center point
    center_x, center_y = 8, 8
    
    # Outer ring - blue-teal glow
    outer_radius = 7 + math.sin(phase * math.pi * 2) * 0.5
    inner_radius = 5 + math.sin(phase * math.pi * 2) * 0.3
    
    # Draw outer glow ring (blue-teal)
    for angle in range(0, 360, 5):
        rad = math.radians(angle)
        x1 = center_x + math.cos(rad) * outer_radius
        y1 = center_y + math.sin(rad) * outer_radius
        x2 = center_x + math.cos(rad) * inner_radius
        y2 = center_y + math.sin(rad) * inner_radius
        
        # Blue-teal gradient
        intensity = (math.sin(phase * math.pi * 2 + angle / 10) + 1) / 2
        r = int(80 * intensity)  # 0-80 (blue)
        g = int(150 + 50 * intensity)  # 150-200 (teal-green)
        b = int(180 + 30 * intensity)  # 180-210 (cyan)
        
        # Draw glow line
        draw.line([(x1, y1), (x2, y2)], fill=(r, g, b, 200), width=1)
    
    # Inner portal core - darker blue-teal
    core_radius = 4
    draw.ellipse(
        [center_x - core_radius, center_y - core_radius,
         center_x + core_radius, center_y + core_radius],
        fill=(40, 100, 140, 180),
        outline=(80, 150, 180, 255)
    )
    
    # Add exoskeletal segments (hive theme - hexagonal pattern)
    segment_count = 6
    for i in range(segment_count):
        segment_angle = (phase * 360 + i * 60) % 360
        rad = math.radians(segment_angle)
        segment_radius = 5.5 + math.sin(phase * math.pi * 4 + i) * 0.5
        segment_x = center_x + math.cos(rad) * segment_radius
        segment_y = center_y + math.sin(rad) * segment_radius
        
        # Draw hexagonal segment (simplified as small hexagon)
        hex_size = 1.5
        points = []
        for j in range(6):
            hex_angle = math.radians(segment_angle + j * 60)
            hx = segment_x + math.cos(hex_angle) * hex_size
            hy = segment_y + math.sin(hex_angle) * hex_size
            points.append((hx, hy))
        
        if len(points) >= 3:
            draw.polygon(points, fill=(60, 130, 160, 255), outline=(80, 150, 180, 255))
    
    # Add central bright point (hive core)
    draw.ellipse(
        [center_x - 1, center_y - 1,
         center_x + 1, center_y + 1],
        fill=(120, 200, 220, 255)
    )
    
    # Add aquatic particle effects (blue-teal sparkles)
    for i in range(4):
        particle_angle = (phase * 360 + i * 90) % 360
        rad = math.radians(particle_angle)
        particle_radius = 6 + math.sin(phase * math.pi * 4 + i) * 1
        particle_x = center_x + math.cos(rad) * particle_radius
        particle_y = center_y + math.sin(rad) * particle_radius
        
        if 0 <= particle_x < 16 and 0 <= particle_y < 16:
            draw.ellipse(
                [particle_x - 0.5, particle_y - 0.5,
                 particle_x + 0.5, particle_y + 0.5],
                fill=(80, 150, 180, 180)
            )
    
    return img

def create_spritesheet(portal_type: str, output_path: Path):
    """Create 8-frame animated spritesheet (128x16)."""
    print(f"Creating {portal_type} portal spritesheet...")
    
    # Create spritesheet: 8 frames of 16x16 = 128x16
    spritesheet = Image.new('RGBA', (128, 16), (0, 0, 0, 0))
    
    for frame in range(8):
        if portal_type == "DefiledWastelands":
            frame_img = create_defiled_portal_frame(frame, 8)
        elif portal_type == "RivenHive":
            frame_img = create_riven_portal_frame(frame, 8)
        elif portal_type == "BrinePool":
            frame_img = create_brine_portal_frame(frame, 8)
        elif portal_type == "LimestoneCave":
            frame_img = create_limestone_portal_frame(frame, 8)
        elif portal_type == "FiberglassUndergrowth":
            frame_img = create_fiberglass_portal_frame(frame, 8)
        else:
            raise ValueError(f"Unknown portal type: {portal_type}")
        
        # Paste frame at correct position
        x_offset = frame * 16
        spritesheet.paste(frame_img, (x_offset, 0))
    
    spritesheet.save(output_path, 'PNG')
    print(f"✓ Spritesheet saved: {output_path}")
    return spritesheet

def create_item_icon(portal_type: str, output_path: Path):
    """Create 16x16 item icon (first frame of animation)."""
    print(f"Creating {portal_type} portal item icon...")
    
    # Use first frame as item icon
    if portal_type == "DefiledWastelands":
        icon = create_defiled_portal_frame(0, 8)
    elif portal_type == "RivenHive":
        icon = create_riven_portal_frame(0, 8)
    else:
        raise ValueError(f"Unknown portal type: {portal_type}")
    
    # Make it slightly brighter for item icon
    icon = icon.point(lambda p: min(255, int(p * 1.2)))
    
    icon.save(output_path, 'PNG')
    print(f"✓ Item icon saved: {output_path}")
    return icon

def create_brine_portal_frame(frame_num: int, total_frames: int = 8) -> Image.Image:
    """
    Create a single 16x16 portal frame for Brine Pool.
    Theme: Brine blue with aquatic aesthetic.
    """
    img = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    phase = frame_num / total_frames
    center_x, center_y = 8, 8
    
    outer_radius = 7 + math.sin(phase * math.pi * 2) * 0.5
    inner_radius = 5 + math.sin(phase * math.pi * 2) * 0.3
    
    for angle in range(0, 360, 5):
        rad = math.radians(angle)
        x1 = center_x + math.cos(rad) * outer_radius
        y1 = center_y + math.sin(rad) * outer_radius
        x2 = center_x + math.cos(rad) * inner_radius
        y2 = center_y + math.sin(rad) * inner_radius
        
        intensity = (math.sin(phase * math.pi * 2 + angle / 10) + 1) / 2
        r = int(100 * intensity)
        g = int(150 + 50 * intensity)
        b = int(200 + 30 * intensity)
        
        draw.line([(x1, y1), (x2, y2)], fill=(r, g, b, 200), width=1)
    
    core_radius = 4
    draw.ellipse(
        [center_x - core_radius, center_y - core_radius,
         center_x + core_radius, center_y + core_radius],
        fill=(50, 100, 150, 180),
        outline=(100, 150, 200, 255)
    )
    
    for i in range(4):
        particle_angle = (phase * 360 + i * 90) % 360
        rad = math.radians(particle_angle)
        particle_radius = 6 + math.sin(phase * math.pi * 4 + i) * 1
        particle_x = center_x + math.cos(rad) * particle_radius
        particle_y = center_y + math.sin(rad) * particle_radius
        
        if 0 <= particle_x < 16 and 0 <= particle_y < 16:
            draw.ellipse(
                [particle_x - 0.5, particle_y - 0.5,
                 particle_x + 0.5, particle_y + 0.5],
                fill=(100, 150, 200, 180)
            )
    
    return img

def create_limestone_portal_frame(frame_num: int, total_frames: int = 8) -> Image.Image:
    """
    Create a single 16x16 portal frame for Limestone Cave.
    Theme: Limestone beige with cave aesthetic.
    """
    img = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    phase = frame_num / total_frames
    center_x, center_y = 8, 8
    
    outer_radius = 7 + math.sin(phase * math.pi * 2) * 0.5
    inner_radius = 5 + math.sin(phase * math.pi * 2) * 0.3
    
    for angle in range(0, 360, 5):
        rad = math.radians(angle)
        x1 = center_x + math.cos(rad) * outer_radius
        y1 = center_y + math.sin(rad) * outer_radius
        x2 = center_x + math.cos(rad) * inner_radius
        y2 = center_y + math.sin(rad) * inner_radius
        
        intensity = (math.sin(phase * math.pi * 2 + angle / 10) + 1) / 2
        r = int(200 * intensity)
        g = int(200 * intensity)
        b = int(180 * intensity)
        
        draw.line([(x1, y1), (x2, y2)], fill=(r, g, b, 200), width=1)
    
    core_radius = 4
    draw.ellipse(
        [center_x - core_radius, center_y - core_radius,
         center_x + core_radius, center_y + core_radius],
        fill=(150, 150, 130, 180),
        outline=(200, 200, 180, 255)
    )
    
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
                fill=(200, 200, 180, 180)
            )
    
    return img

def create_fiberglass_portal_frame(frame_num: int, total_frames: int = 8) -> Image.Image:
    """
    Create a single 16x16 portal frame for Fiberglass Undergrowth.
    Theme: Fiberglass cyan with glass-like aesthetic.
    """
    img = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    phase = frame_num / total_frames
    center_x, center_y = 8, 8
    
    outer_radius = 7 + math.sin(phase * math.pi * 2) * 0.5
    inner_radius = 5 + math.sin(phase * math.pi * 2) * 0.3
    
    for angle in range(0, 360, 5):
        rad = math.radians(angle)
        x1 = center_x + math.cos(rad) * outer_radius
        y1 = center_y + math.sin(rad) * outer_radius
        x2 = center_x + math.cos(rad) * inner_radius
        y2 = center_y + math.sin(rad) * inner_radius
        
        intensity = (math.sin(phase * math.pi * 2 + angle / 10) + 1) / 2
        r = int(150 * intensity)
        g = int(200 * intensity)
        b = int(200 * intensity)
        
        draw.line([(x1, y1), (x2, y2)], fill=(r, g, b, 200), width=1)
    
    core_radius = 4
    draw.ellipse(
        [center_x - core_radius, center_y - core_radius,
         center_x + core_radius, center_y + core_radius],
        fill=(100, 150, 150, 180),
        outline=(150, 200, 200, 255)
    )
    
    for i in range(5):
        particle_angle = (phase * 360 + i * 72) % 360
        rad = math.radians(particle_angle)
        particle_radius = 6 + math.sin(phase * math.pi * 4 + i) * 1
        particle_x = center_x + math.cos(rad) * particle_radius
        particle_y = center_y + math.sin(rad) * particle_radius
        
        if 0 <= particle_x < 16 and 0 <= particle_y < 16:
            draw.ellipse(
                [particle_x - 0.5, particle_y - 0.5,
                 particle_x + 0.5, particle_y + 0.5],
                fill=(150, 200, 200, 180)
            )
    
    return img

def main():
    """Generate all Origins biome portal assets."""
    # Determine output directory
    script_dir = Path(__file__).parent.absolute()
    
    # Try to find CrossModStabilizer mod directory
    cwd = Path.cwd()
    if (cwd / "Assets").exists() or (cwd / "CrossModStabilizer.cs").exists():
        mod_dir = cwd
    else:
        # Try other possible locations
        possible_paths = [
            Path("D:/User_Directories/Documents/My Games/Terraria/tModLoader/ModSources/CrossModStabilizer"),
            Path("E:/SteamLibrary/steamapps/common/tModLoader/ModSources/CrossModStabilizer"),
            Path("d:/User_Directories/Documents/My Games/Terraria/tModLoader/ModSources/CrossModStabilizer"),
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
    tiles_dir = assets_dir / "tiles"
    
    # Create directories if they don't exist
    tiles_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("Origins Biome Portal Asset Generator")
    print("=" * 60)
    print(f"Output directory: {assets_dir}")
    print()
    
    # Generate Defiled Wastelands portal
    print("Generating Defiled Wastelands portal...")
    defiled_spritesheet_path = tiles_dir / "defiledwastelandsbiomeportal_spritesheet.png"
    create_spritesheet("DefiledWastelands", defiled_spritesheet_path)
    
    print()
    
    # Generate Riven Hive portal
    print("Generating Riven Hive portal...")
    riven_spritesheet_path = tiles_dir / "rivenhivebiomeportal_spritesheet.png"
    create_spritesheet("RivenHive", riven_spritesheet_path)
    
    print()
    
    # Generate Brine Pool portal
    print("Generating Brine Pool portal...")
    brine_spritesheet_path = tiles_dir / "brinepoolbiomeportal_spritesheet.png"
    create_spritesheet("BrinePool", brine_spritesheet_path)
    
    print()
    
    # Generate Limestone Cave portal
    print("Generating Limestone Cave portal...")
    limestone_spritesheet_path = tiles_dir / "limestonecavebiomeportal_spritesheet.png"
    create_spritesheet("LimestoneCave", limestone_spritesheet_path)
    
    print()
    
    # Generate Fiberglass Undergrowth portal
    print("Generating Fiberglass Undergrowth portal...")
    fiberglass_spritesheet_path = tiles_dir / "fiberglassundergrowthbiomeportal_spritesheet.png"
    create_spritesheet("FiberglassUndergrowth", fiberglass_spritesheet_path)
    
    print()
    print("=" * 60)
    print("✓ All Origins biome portal assets generated successfully!")
    print("=" * 60)
    print(f"Defiled Wastelands spritesheet: {defiled_spritesheet_path}")
    print(f"Riven Hive spritesheet: {riven_spritesheet_path}")
    print(f"Brine Pool spritesheet: {brine_spritesheet_path}")
    print(f"Limestone Cave spritesheet: {limestone_spritesheet_path}")
    print(f"Fiberglass Undergrowth spritesheet: {fiberglass_spritesheet_path}")
    print()
    print("Note: Portals use themes matching Origins mod aesthetics.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
