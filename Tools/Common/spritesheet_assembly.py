#!/usr/bin/env python3
"""
Spritesheet Assembly Tool
Adds texture tiles to a spritesheet, finding the first empty slot.
"""

import argparse
import os
from PIL import Image

def find_empty_slot(sheet, tile_size, columns):
    """Find the first empty slot in the spritesheet."""
    rows = sheet.height // tile_size
    max_slots = columns * rows
    
    for i in range(max_slots):
        col = i % columns
        row = i // columns
        x = col * tile_size
        y = row * tile_size
        
        # Extract region
        region = sheet.crop((x, y, x + tile_size, y + tile_size))
        
        # Check if region is empty (all transparent or all same color)
        if region.mode == 'RGBA':
            # Check alpha channel
            alpha = region.split()[3]
            if alpha.getextrema()[0] == 0:  # All transparent
                return (x, y, i)
        else:
            # Check if all pixels are the same (likely empty)
            pixels = list(region.getdata())
            if len(set(pixels)) <= 1:  # All same color
                return (x, y, i)
    
    return None

def add_tile_to_spritesheet(tile_path, sheet_path, tile_size, columns):
    """Add a tile to the spritesheet."""
    if not os.path.exists(tile_path):
        print(f"Error: Tile not found: {tile_path}")
        return False
    
    # Load and resize tile
    tile = Image.open(tile_path)
    if tile.size != (tile_size, tile_size):
        tile = tile.resize((tile_size, tile_size), Image.Resampling.LANCZOS)
    
    # Load or create spritesheet
    if os.path.exists(sheet_path):
        sheet = Image.open(sheet_path)
        if sheet.mode != 'RGBA':
            sheet = sheet.convert('RGBA')
    else:
        # Create new spritesheet (8x8 grid by default)
        rows = 8
        sheet_width = tile_size * columns
        sheet_height = tile_size * rows
        sheet = Image.new('RGBA', (sheet_width, sheet_height), (0, 0, 0, 0))
        print(f"Created new spritesheet: {sheet_width}x{sheet_height}")
    
    # Find empty slot
    slot = find_empty_slot(sheet, tile_size, columns)
    
    if slot:
        x, y, index = slot
        col = index % columns
        row = index // columns
        sheet.paste(tile, (x, y), tile if tile.mode == 'RGBA' else None)
        sheet.save(sheet_path)
        print(f"Added tile to slot {index} (row {row}, col {col})")
        return True
    else:
        print("Warning: No empty slots found. Spritesheet may need expansion.")
        # Could expand here, but for now just report
        return False

def main():
    parser = argparse.ArgumentParser(description='Add texture tiles to a spritesheet')
    parser.add_argument('--tile', required=True, help='Path to tile image')
    parser.add_argument('--sheet', required=True, help='Path to spritesheet')
    parser.add_argument('--tileSize', type=int, default=128, help='Tile size in pixels')
    parser.add_argument('--columns', type=int, default=8, help='Number of columns in spritesheet')
    
    args = parser.parse_args()
    
    success = add_tile_to_spritesheet(
        args.tile,
        args.sheet,
        args.tileSize,
        args.columns
    )
    
    exit(0 if success else 1)

if __name__ == '__main__':
    main()

