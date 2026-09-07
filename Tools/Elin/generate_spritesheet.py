#!/usr/bin/env python3
"""
Enhanced Spritesheet Generator for Elin Mod Assets

Based on Transcendence spritesheet generation patterns with support for:
- Configurable grid layouts (columns/rows)
- Frame-based spritesheets (fixed frame size)
- Variable frame sizes with bin-packing optimization
- Better grid calculation algorithms
- Metadata generation
- Multiple output formats
- Proper spacing and alignment
- Asset type-specific handling
"""

import os
import sys
import json
import argparse
from pathlib import Path
from PIL import Image, ImageDraw
import math
from datetime import datetime
from typing import List, Tuple, Optional, Dict

class SpriteRect:
    """Represents a sprite rectangle with position and size"""
    def __init__(self, x=0, y=0, width=0, height=0, image_index=-1):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.image_index = image_index
    
    def __repr__(self):
        return f"SpriteRect({self.x}, {self.y}, {self.width}, {self.height}, idx={self.image_index})"

def calculate_optimal_grid(num_images: int, avg_width: float, avg_height: float, 
                          max_sheet_size: int = 8192) -> Tuple[int, int]:
    """
    Calculate optimal grid dimensions considering:
    - Aspect ratio of images
    - Power-of-2 sizes (for GPU efficiency)
    - Minimizing wasted space
    - Maximum sheet size constraints
    """
    if num_images == 0:
        return (1, 1)
    
    # Calculate aspect ratio
    aspect_ratio = avg_width / avg_height if avg_height > 0 else 1.0
    
    # Start with square-ish grid
    base_cols = int(math.ceil(math.sqrt(num_images)))
    base_rows = int(math.ceil(num_images / base_cols))
    
    # Adjust for aspect ratio
    if aspect_ratio > 1.5:  # Wide images
        base_cols = int(base_cols * 1.2)
        base_rows = int(math.ceil(num_images / base_cols))
    elif aspect_ratio < 0.67:  # Tall images
        base_rows = int(base_rows * 1.2)
        base_cols = int(math.ceil(num_images / base_rows))
    
    # Try to make dimensions power-of-2 friendly
    # Find nearest power-of-2 that can fit all images
    best_cols = base_cols
    best_rows = base_rows
    best_waste = float('inf')
    
    # Test nearby power-of-2 sizes
    for test_cols in [base_cols, base_cols + 1, base_cols - 1, 
                      int(2 ** math.ceil(math.log2(base_cols))),
                      int(2 ** math.floor(math.log2(base_cols)))]:
        if test_cols < 1:
            continue
        test_rows = int(math.ceil(num_images / test_cols))
        if test_rows < 1:
            continue
        
        # Estimate sheet size
        est_width = test_cols * avg_width
        est_height = test_rows * avg_height
        
        # Check if within limits
        if est_width > max_sheet_size or est_height > max_sheet_size:
            continue
        
        # Calculate wasted space (empty cells)
        total_cells = test_cols * test_rows
        waste = total_cells - num_images
        
        # Prefer power-of-2 dimensions
        is_pow2_cols = (test_cols & (test_cols - 1)) == 0
        is_pow2_rows = (test_rows & (test_rows - 1)) == 0
        
        # Adjust waste calculation to favor power-of-2
        adjusted_waste = waste * (0.8 if (is_pow2_cols or is_pow2_rows) else 1.0)
        
        if adjusted_waste < best_waste:
            best_waste = adjusted_waste
            best_cols = test_cols
            best_rows = test_rows
    
    return (best_cols, best_rows)

def next_power_of_2(n: int) -> int:
    """Get next power of 2 >= n"""
    if n <= 0:
        return 1
    return 1 << (n - 1).bit_length()

def bin_pack_variable_sizes(images: List[Image.Image], max_width: int = 8192, 
                            max_height: int = 8192, spacing: int = 2) -> Tuple[Image.Image, List[Dict]]:
    """
    Bin-packing algorithm for variable-sized sprites (MaxRects algorithm variant)
    Returns: (spritesheet_image, list of sprite metadata dicts)
    """
    if not images:
        return Image.new('RGBA', (1, 1), (0, 0, 0, 0)), []
    
    # Sort images by area (largest first) for better packing
    indexed_images = [(i, img) for i, img in enumerate(images)]
    indexed_images.sort(key=lambda x: x[1].width * x[1].height, reverse=True)
    
    # Initialize free rectangles (start with full sheet)
    # We'll dynamically expand the sheet as needed
    sheet_width = next_power_of_2(max(img.width for _, img in indexed_images))
    sheet_height = next_power_of_2(max(img.height for _, img in indexed_images))
    
    # Ensure minimum size
    sheet_width = max(sheet_width, 256)
    sheet_height = max(sheet_height, 256)
    
    free_rects = [SpriteRect(0, 0, sheet_width, sheet_height)]
    placed_sprites = []
    sprite_metadata = []
    
    for img_idx, img in indexed_images:
        img_width = img.width + spacing
        img_height = img.height + spacing
        
        # Find best free rectangle (Best Short Side Fit)
        best_rect = None
        best_short_side = float('inf')
        best_long_side = float('inf')
        
        for free_rect in free_rects:
            if free_rect.width >= img_width and free_rect.height >= img_height:
                leftover_horiz = abs(free_rect.width - img_width)
                leftover_vert = abs(free_rect.height - img_height)
                short_side = min(leftover_horiz, leftover_vert)
                long_side = max(leftover_horiz, leftover_vert)
                
                if short_side < best_short_side or (short_side == best_short_side and long_side < best_long_side):
                    best_short_side = short_side
                    best_long_side = long_side
                    best_rect = free_rect
        
        # If no fit found, expand sheet
        if best_rect is None:
            # Expand in the direction that minimizes total area
            new_width = next_power_of_2(sheet_width + img_width)
            new_height = next_power_of_2(sheet_height + img_height)
            
            if new_width * sheet_height < sheet_width * new_height:
                sheet_width = new_width
            else:
                sheet_height = new_height
            
            # Add new free rectangle
            if sheet_width > len(free_rects) == 0 or free_rects[0].width < sheet_width:
                free_rects.append(SpriteRect(free_rects[0].width if free_rects else 0, 0, 
                                           sheet_width - (free_rects[0].width if free_rects else 0), 
                                           sheet_height))
            if sheet_height > len(free_rects) == 0 or free_rects[0].height < sheet_height:
                free_rects.append(SpriteRect(0, free_rects[0].height if free_rects else 0, 
                                           sheet_width, 
                                           sheet_height - (free_rects[0].height if free_rects else 0)))
            
            # Retry with expanded sheet
            for free_rect in free_rects:
                if free_rect.width >= img_width and free_rect.height >= img_height:
                    best_rect = free_rect
                    break
        
        if best_rect is None:
            print(f"  [Warning] Could not place image {img_idx}, skipping")
            continue
        
        # Place sprite
        sprite_x = best_rect.x
        sprite_y = best_rect.y
        
        placed_sprites.append((img_idx, img, sprite_x, sprite_y))
        sprite_metadata.append({
            "index": img_idx,
            "x": sprite_x,
            "y": sprite_y,
            "width": img.width,
            "height": img.height,
            "original_width": img.width,
            "original_height": img.height
        })
        
        # Split free rectangle
        new_rects = []
        for free_rect in free_rects:
            if free_rect == best_rect:
                # Split into remaining rectangles
                # Right rectangle
                if best_rect.x + img_width < best_rect.x + best_rect.width:
                    new_rects.append(SpriteRect(
                        best_rect.x + img_width,
                        best_rect.y,
                        best_rect.width - img_width,
                        best_rect.height
                    ))
                # Bottom rectangle
                if best_rect.y + img_height < best_rect.y + best_rect.height:
                    new_rects.append(SpriteRect(
                        best_rect.x,
                        best_rect.y + img_height,
                        img_width,
                        best_rect.height - img_height
                    ))
            else:
                # Check if this rectangle overlaps with placed sprite
                if not (free_rect.x >= sprite_x + img_width or 
                       free_rect.x + free_rect.width <= sprite_x or
                       free_rect.y >= sprite_y + img_height or
                       free_rect.y + free_rect.height <= sprite_y):
                    # Split overlapping rectangle
                    # Left part
                    if free_rect.x < sprite_x:
                        new_rects.append(SpriteRect(
                            free_rect.x,
                            free_rect.y,
                            sprite_x - free_rect.x,
                            free_rect.height
                        ))
                    # Right part
                    if free_rect.x + free_rect.width > sprite_x + img_width:
                        new_rects.append(SpriteRect(
                            sprite_x + img_width,
                            free_rect.y,
                            free_rect.x + free_rect.width - (sprite_x + img_width),
                            free_rect.height
                        ))
                    # Top part
                    if free_rect.y < sprite_y:
                        new_rects.append(SpriteRect(
                            free_rect.x,
                            free_rect.y,
                            free_rect.width,
                            sprite_y - free_rect.y
                        ))
                    # Bottom part
                    if free_rect.y + free_rect.height > sprite_y + img_height:
                        new_rects.append(SpriteRect(
                            free_rect.x,
                            sprite_y + img_height,
                            free_rect.width,
                            free_rect.y + free_rect.height - (sprite_y + img_height)
                        ))
                else:
                    new_rects.append(free_rect)
        
        # Remove small rectangles and merge where possible
        free_rects = [r for r in new_rects if r.width >= spacing and r.height >= spacing]
        
        # Simple merge: remove contained rectangles
        free_rects = [r for r in free_rects if not any(
            r2 != r and r2.x <= r.x and r2.y <= r.y and 
            r2.x + r2.width >= r.x + r.width and r2.y + r2.height >= r.y + r.height
            for r2 in free_rects
        )]
    
    # Create spritesheet
    spritesheet = Image.new('RGBA', (sheet_width, sheet_height), (0, 0, 0, 0))
    
    # Paste all images
    for img_idx, img, x, y in placed_sprites:
        if img.mode == 'RGBA':
            spritesheet.paste(img, (x, y), img)
        else:
            spritesheet.paste(img, (x, y))
    
    return spritesheet, sprite_metadata

def create_spritesheet(
    asset_paths,
    output_path,
    columns=None,
    rows=None,
    frame_width=None,
    frame_height=None,
    spacing=2,
    background_color=(0, 0, 0, 0),
    asset_type="generic",
    generate_metadata=True,
    output_format="PNG",
    use_variable_sizes=False,
    optimize_layout=True
):
    """
    Create a spritesheet from multiple asset images with Transcendence-style features.
    
    Args:
        asset_paths: List of paths to asset images
        output_path: Output spritesheet path
        columns: Number of columns (None for auto)
        rows: Number of rows (None for auto)
        frame_width: Fixed frame width (None for auto from images)
        frame_height: Fixed frame height (None for auto from images)
        spacing: Pixels between sprites
        background_color: Background color (RGBA tuple)
        asset_type: Type of asset (icon, sprite, texture, spell_asset)
        generate_metadata: Generate JSON metadata file
        output_format: Output format (PNG, JPG)
        use_variable_sizes: Use bin-packing for variable frame sizes
        optimize_layout: Use optimized grid calculation
    """
    if not asset_paths:
        print("  [Error] No assets provided")
        return False
    
    # Load all images
    images = []
    max_width = 0
    max_height = 0
    total_width = 0
    total_height = 0
    loaded_paths = []
    
    for asset_path in asset_paths:
        if not os.path.exists(asset_path):
            print(f"  [Warning] Asset not found: {asset_path}")
            continue
        
        try:
            img = Image.open(asset_path)
            # Convert to RGBA if needed
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            
            images.append(img)
            loaded_paths.append(asset_path)
            max_width = max(max_width, img.width)
            max_height = max(max_height, img.height)
            total_width += img.width
            total_height += img.height
        except Exception as e:
            print(f"  [Warning] Failed to load {asset_path}: {e}")
            continue
    
    if not images:
        print("  [Error] No valid images to combine")
        return False
    
    # Use variable-size bin-packing if requested or if sizes vary significantly
    sizes_vary = max_width > min(img.width for img in images) * 1.5 or \
                max_height > min(img.height for img in images) * 1.5
    
    if use_variable_sizes or (sizes_vary and frame_width is None and frame_height is None):
        print("  [Info] Using variable-size bin-packing layout")
        spritesheet, sprite_metadata = bin_pack_variable_sizes(images, spacing=spacing)
        
        # Calculate actual used dimensions
        if sprite_metadata:
            max_x = max(m["x"] + m["width"] for m in sprite_metadata)
            max_y = max(m["y"] + m["height"] for m in sprite_metadata)
            # Round up to power of 2 for GPU efficiency
            actual_width = next_power_of_2(max_x)
            actual_height = next_power_of_2(max_y)
            
            # Crop if significantly smaller
            if actual_width < spritesheet.width * 0.8:
                spritesheet = spritesheet.crop((0, 0, actual_width, spritesheet.height))
            if actual_height < spritesheet.height * 0.8:
                spritesheet = spritesheet.crop((0, 0, spritesheet.width, actual_height))
        else:
            actual_width = spritesheet.width
            actual_height = spritesheet.height
        
        sheet_width = spritesheet.width
        sheet_height = spritesheet.height
        columns = None
        rows = None
        frame_width = None
        frame_height = None
    else:
        # Fixed-size grid layout
        # Determine frame dimensions
        if frame_width is None:
            frame_width = max_width
        if frame_height is None:
            frame_height = max_height
        
        # Calculate grid dimensions with optimization
        num_images = len(images)
        if optimize_layout:
            avg_width = total_width / num_images
            avg_height = total_height / num_images
            columns, rows = calculate_optimal_grid(num_images, avg_width, avg_height)
        else:
            if columns is None and rows is None:
                # Auto-calculate: try to make it roughly square
                columns = int(math.ceil(math.sqrt(num_images)))
                rows = int(math.ceil(num_images / columns))
            elif columns is None:
                # Calculate columns from rows
                columns = int(math.ceil(num_images / rows))
            elif rows is None:
                # Calculate rows from columns
                rows = int(math.ceil(num_images / columns))
        
        # Ensure we have enough space
        total_frames = columns * rows
        if num_images > total_frames:
            print(f"  [Warning] {num_images} images but only {total_frames} frames available. Adding rows...")
            rows = int(math.ceil(num_images / columns))
            total_frames = columns * rows
        
        # Calculate spritesheet size (round to power of 2 for GPU efficiency)
        base_width = columns * frame_width + (columns - 1) * spacing
        base_height = rows * frame_height + (rows - 1) * spacing
        sheet_width = next_power_of_2(base_width) if optimize_layout else base_width
        sheet_height = next_power_of_2(base_height) if optimize_layout else base_height
        
        # Create spritesheet
        spritesheet = Image.new('RGBA', (sheet_width, sheet_height), background_color)
        
        # Paste images into spritesheet
        sprite_metadata = []
        for idx, img in enumerate(images):
            if idx >= total_frames:
                print(f"  [Warning] Skipping image {idx+1} (exceeds grid capacity)")
                break
            
            row = idx // columns
            col = idx % columns
            
            x = col * (frame_width + spacing)
            y = row * (frame_height + spacing)
            
            # Center smaller images within frame
            offset_x = (frame_width - img.width) // 2
            offset_y = (frame_height - img.height) // 2
            
            sprite_metadata.append({
                "index": idx,
                "x": x + offset_x,
                "y": y + offset_y,
                "width": img.width,
                "height": img.height,
                "frame_x": x,
                "frame_y": y,
                "frame_width": frame_width,
                "frame_height": frame_height,
                "original_width": img.width,
                "original_height": img.height
            })
            
            # Paste with alpha channel support
            if img.mode == 'RGBA':
                spritesheet.paste(img, (x + offset_x, y + offset_y), img)
            else:
                spritesheet.paste(img, (x + offset_x, y + offset_y))
    
    # Ensure output directory exists
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert format if needed
    if output_format.upper() == "JPG" or output_path.suffix.lower() == ".jpg":
        # Convert RGBA to RGB for JPG
        if spritesheet.mode == 'RGBA':
            rgb_sheet = Image.new('RGB', spritesheet.size, (255, 255, 255))
            rgb_sheet.paste(spritesheet, mask=spritesheet.split()[3])  # Use alpha channel as mask
            spritesheet = rgb_sheet
        spritesheet.save(output_path, 'JPEG', quality=95)
    else:
        spritesheet.save(output_path, 'PNG')
    
    # Calculate efficiency metrics
    total_sprite_area = sum(m["width"] * m["height"] for m in sprite_metadata)
    sheet_area = sheet_width * sheet_height
    efficiency = (total_sprite_area / sheet_area * 100) if sheet_area > 0 else 0
    
    print(f"  [OK] Generated spritesheet: {output_path}")
    print(f"       Size: {sheet_width}x{sheet_height}, {len(images)} assets")
    if columns and rows:
        print(f"       Grid: {columns}x{rows}, Frame: {frame_width}x{frame_height}, Spacing: {spacing}px")
    else:
        print(f"       Layout: Variable-size bin-packing, Spacing: {spacing}px")
    print(f"       Efficiency: {efficiency:.1f}% (sprite area / sheet area)")
    
    # Generate metadata
    if generate_metadata:
        metadata_path = output_path.with_suffix('.json')
        metadata = {
            "name": output_path.stem,
            "asset_type": asset_type,
            "width": sheet_width,
            "height": sheet_height,
            "spacing": spacing,
            "asset_count": len(images),
            "format": output_format.upper(),
            "generated": datetime.now().isoformat(),
            "layout": "variable" if use_variable_sizes or (sizes_vary and frame_width is None) else "grid",
            "efficiency": round(efficiency, 2)
        }
        
        if columns and rows:
            metadata["columns"] = columns
            metadata["rows"] = rows
            metadata["frame_width"] = frame_width
            metadata["frame_height"] = frame_height
            metadata["total_frames"] = columns * rows
        
        metadata["sprites"] = sprite_metadata
        metadata["assets"] = [str(Path(p).name) for p in loaded_paths]
        
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        print(f"  [OK] Metadata saved: {metadata_path}")
    
    # Sidecar metadata next to the real spritesheet PNG/JPEG (not a stub).
    info_path = output_path.with_suffix('.info.txt')
    with open(info_path, 'w', encoding='utf-8') as f:
        f.write(f"Spritesheet: {output_path.name}\n")
        f.write(f"Dimensions: {sheet_width}x{sheet_height}\n")
        if columns and rows:
            f.write(f"Grid: {columns}x{rows} ({columns * rows} frames)\n")
            f.write(f"Frame size: {frame_width}x{frame_height}\n")
        else:
            f.write(f"Layout: Variable-size bin-packing\n")
        f.write(f"Assets: {len(images)}\n")
        f.write(f"Type: {asset_type}\n")
        f.write(f"Format: {output_format.upper()}\n")
        f.write(f"Efficiency: {efficiency:.1f}%\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    print(f"  [OK] Info file saved: {info_path}")
    
    return True

def main():
    parser = argparse.ArgumentParser(
        description='Generate spritesheet from assets (Transcendence-style)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Auto-calculate grid with optimization
  python generate_spritesheet.py --assets "icon1.png,icon2.png" --output sheet.png
  
  # Fixed grid layout
  python generate_spritesheet.py --assets "*.png" --output sheet.png --columns 10 --rows 8
  
  # Fixed frame size
  python generate_spritesheet.py --assets "*.png" --output sheet.png --frame-width 32 --frame-height 32
  
  # Variable-size bin-packing (for different frame sizes)
  python generate_spritesheet.py --assets "*.png" --output sheet.png --variable-sizes
        """
    )
    parser.add_argument('--assets', required=True, help='Comma-separated list of asset paths (or glob pattern)')
    parser.add_argument('--output', required=True, help='Output spritesheet path')
    parser.add_argument('--type', default='generic', help='Asset type (icon, sprite, texture, spell_asset)')
    parser.add_argument('--columns', type=int, help='Number of columns (auto if not specified)')
    parser.add_argument('--rows', type=int, help='Number of rows (auto if not specified)')
    parser.add_argument('--frame-width', type=int, help='Fixed frame width (auto from images if not specified)')
    parser.add_argument('--frame-height', type=int, help='Fixed frame height (auto from images if not specified)')
    parser.add_argument('--spacing', type=int, default=2, help='Pixels between sprites (default: 2)')
    parser.add_argument('--format', choices=['PNG', 'JPG'], default='PNG', help='Output format (default: PNG)')
    parser.add_argument('--no-metadata', action='store_true', help='Skip metadata generation')
    parser.add_argument('--variable-sizes', action='store_true', help='Use bin-packing for variable frame sizes')
    parser.add_argument('--no-optimize', action='store_true', help='Disable layout optimization')
    
    args = parser.parse_args()
    
    # Parse asset paths (support glob patterns)
    import glob
    asset_paths = []
    for pattern in args.assets.split(','):
        pattern = pattern.strip()
        if not pattern:
            continue
        
        # Check if it's a glob pattern
        if '*' in pattern or '?' in pattern:
            matches = glob.glob(pattern, recursive=True)
            asset_paths.extend(matches)
        else:
            # Single file path
            if os.path.exists(pattern):
                asset_paths.append(pattern)
    
    # Remove duplicates and sort
    asset_paths = sorted(list(set(asset_paths)))
    
    if not asset_paths:
        print("  [Error] No asset paths found")
        return 1
    
    print(f"  [Info] Found {len(asset_paths)} assets")
    
    # Create spritesheet
    success = create_spritesheet(
        asset_paths=asset_paths,
        output_path=args.output,
        columns=args.columns,
        rows=args.rows,
        frame_width=args.frame_width,
        frame_height=args.frame_height,
        spacing=args.spacing,
        asset_type=args.type,
        generate_metadata=not args.no_metadata,
        output_format=args.format,
        use_variable_sizes=args.variable_sizes,
        optimize_layout=not args.no_optimize
    )
    
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())
