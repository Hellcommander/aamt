#!/usr/bin/env python3
"""
Cross-Game Spritesheet Generator
Generates game-compatible spritesheets for Terraria and Starbound from a single texture source.
"""

import os
import sys
import json
import argparse
from PIL import Image

# ============================================================
# Argument Parsing
# ============================================================

def parse_args():
    parser = argparse.ArgumentParser(description='Generate cross-game spritesheets')
    parser.add_argument('--input', required=True, help='Input directory with PNG textures')
    parser.add_argument('--output', required=True, help='Output directory')
    parser.add_argument('--tile-size', type=int, default=16, help='Tile size in pixels')
    parser.add_argument('--columns', type=int, default=8, help='Number of columns')
    parser.add_argument('--frames', type=int, default=1, help='Animation frames per item')
    parser.add_argument('--speed', type=int, default=5, help='Animation speed (Terraria FPS)')
    parser.add_argument('--name', default='spritesheet', help='Base name for output files')
    parser.add_argument('--terraria', action='store_true', help='Generate Terraria format only')
    parser.add_argument('--starbound', action='store_true', help='Generate Starbound format only')
    parser.add_argument('--both', action='store_true', help='Generate both formats (default)')
    
    return parser.parse_args()


# ============================================================
# Spritesheet Assembly
# ============================================================

def assemble_spritesheet(input_dir, tile_size, columns, output_path):
    """Assemble a spritesheet from individual texture files."""
    # Get all PNG files
    files = [f for f in os.listdir(input_dir) if f.lower().endswith('.png')]
    files.sort()
    
    if len(files) == 0:
        print(f"Error: No PNG files found in {input_dir}")
        return None, None, None
    
    # Calculate dimensions
    total_tiles = len(files)
    rows = (total_tiles + columns - 1) // columns
    sheet_width = columns * tile_size
    sheet_height = rows * tile_size
    
    # Create spritesheet
    sheet = Image.new('RGBA', (sheet_width, sheet_height), (0, 0, 0, 0))
    
    # Paste each texture
    for i, filename in enumerate(files):
        try:
            img = Image.open(os.path.join(input_dir, filename))
            
            # Resize to tile size
            if img.size != (tile_size, tile_size):
                img = img.resize((tile_size, tile_size), Image.Resampling.LANCZOS)
            
            # Calculate position
            x = (i % columns) * tile_size
            y = (i // columns) * tile_size
            
            # Paste (handle transparency)
            if img.mode == 'RGBA':
                sheet.paste(img, (x, y), img)
            else:
                sheet.paste(img, (x, y))
            
        except Exception as e:
            print(f"Warning: Could not process {filename}: {e}")
            continue
    
    # Save spritesheet
    sheet.save(output_path, 'PNG')
    print(f"Created spritesheet: {output_path} ({sheet_width}x{sheet_height})")
    
    return total_tiles, columns, rows


# ============================================================
# Terraria Exporter
# ============================================================

def export_terraria_metadata(sheet_path, frame_count, tile_size, frames_per_item, animation_speed, output_json):
    """Generate Terraria/tModLoader compatible metadata."""
    items = frame_count // frames_per_item if frames_per_item > 0 else frame_count
    
    data = {
        "frames": frames_per_item,
        "frameWidth": tile_size,
        "frameHeight": tile_size,
        "animationSpeed": animation_speed,
        "items": items,
        "sheetWidth": tile_size * frames_per_item if frames_per_item > 1 else tile_size,
        "sheetHeight": tile_size
    }
    
    # Add frame definitions for each item
    if frames_per_item > 1:
        data["animations"] = {}
        for i in range(items):
            frame_indices = list(range(i * frames_per_item, (i + 1) * frames_per_item))
            data["animations"][f"item_{i}"] = {
                "frames": frame_indices,
                "speed": animation_speed
            }
    
    with open(output_json, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"Created Terraria metadata: {output_json}")


# ============================================================
# Starbound Exporter
# ============================================================

def export_starbound_frames(sheet_path, frame_count, tile_size, frames_per_item, output_frames):
    """Generate Starbound .frames file."""
    items = frame_count // frames_per_item if frames_per_item > 0 else frame_count
    
    # Calculate grid dimensions
    columns = frames_per_item if frames_per_item > 1 else 1
    rows = items if frames_per_item == 1 else items
    
    data = {
        "frameGrid": {
            "size": [tile_size, tile_size],
            "dimensions": [columns, rows]
        }
    }
    
    # Add aliases for animations
    if frames_per_item > 1:
        data["aliases"] = {}
        for i in range(items):
            frame_indices = list(range(i * frames_per_item, (i + 1) * frames_per_item))
            data["aliases"][f"default_{i}"] = frame_indices
        # Default alias for first item
        if items > 0:
            data["aliases"]["default"] = list(range(frames_per_item))
    else:
        # Single frame items
        data["aliases"] = {
            "default": list(range(items))
        }
    
    with open(output_frames, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"Created Starbound frames: {output_frames}")


# ============================================================
# Main
# ============================================================

def main():
    args = parse_args()
    
    # Determine output formats
    generate_terraria = args.terraria or args.both or (not args.starbound and not args.terraria)
    generate_starbound = args.starbound or args.both or (not args.starbound and not args.terraria)
    
    # Ensure output directory exists
    os.makedirs(args.output, exist_ok=True)
    
    # Assemble base spritesheet
    base_sheet_path = os.path.join(args.output, f"{args.name}.png")
    total_tiles, columns, rows = assemble_spritesheet(
        args.input,
        args.tile_size,
        args.columns,
        base_sheet_path
    )
    
    if total_tiles is None:
        sys.exit(1)
    
    # Calculate items (assuming frames_per_item frames per item)
    items = total_tiles // args.frames if args.frames > 0 else total_tiles
    
    print(f"\nSpritesheet stats:")
    print(f"  Total tiles: {total_tiles}")
    print(f"  Items: {items}")
    print(f"  Frames per item: {args.frames}")
    print(f"  Grid: {columns}x{rows}")
    print("")
    
    # Generate Terraria format
    if generate_terraria:
        terraria_sheet = os.path.join(args.output, f"{args.name}_terraria.png")
        # Copy base sheet (Terraria can use the same format)
        import shutil
        shutil.copy2(base_sheet_path, terraria_sheet)
        
        terraria_json = os.path.join(args.output, f"{args.name}_terraria.json")
        export_terraria_metadata(
            terraria_sheet,
            total_tiles,
            args.tile_size,
            args.frames,
            args.speed,
            terraria_json
        )
    
    # Generate Starbound format
    if generate_starbound:
        starbound_sheet = os.path.join(args.output, f"{args.name}_starbound.png")
        # Copy base sheet
        import shutil
        shutil.copy2(base_sheet_path, starbound_sheet)
        
        starbound_frames = os.path.join(args.output, f"{args.name}.frames")
        export_starbound_frames(
            starbound_sheet,
            total_tiles,
            args.tile_size,
            args.frames,
            starbound_frames
        )
    
    print("\n[OK] Cross-game spritesheet generation complete!")


if __name__ == '__main__':
    main()

