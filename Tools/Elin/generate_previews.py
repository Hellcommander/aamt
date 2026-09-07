#!/usr/bin/env python3
"""
Preview System for Asset Generator
Generates preview thumbnails and asset catalog for generated assets.
"""

import os
import sys
import json
import argparse
from pathlib import Path
import time
from datetime import datetime

# Check for required dependencies
try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError as e:
    PIL_AVAILABLE = False
    print("ERROR: Pillow (PIL) is required but not installed.", file=sys.stderr)
    print("  Install it with: pip install Pillow", file=sys.stderr)
    print(f"  Import error: {e}", file=sys.stderr)
    sys.exit(1)

# ============================================================
# Preview Generation
# ============================================================

def generate_thumbnail(source_path, output_path, size=(128, 128), quality=85):
    """
    Generate a thumbnail from a source image.
    
    Args:
        source_path: Path to source image
        output_path: Path to save thumbnail
        size: Thumbnail size (width, height)
        quality: JPEG quality (1-100) if saving as JPEG
    """
    try:
        with Image.open(source_path) as img:
            # Convert to RGB if necessary (for JPEG compatibility)
            if img.mode in ('RGBA', 'LA', 'P'):
                # Create white background for transparency
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                rgb_img.paste(img, mask=img.split()[3] if img.mode == 'RGBA' else None)
                img = rgb_img
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Calculate aspect ratio preserving resize
            img.thumbnail(size, Image.Resampling.LANCZOS)
            
            # Create a square thumbnail with padding if needed
            thumb = Image.new('RGB', size, (240, 240, 240))
            # Center the image
            x_offset = (size[0] - img.size[0]) // 2
            y_offset = (size[1] - img.size[1]) // 2
            thumb.paste(img, (x_offset, y_offset))
            
            # Save thumbnail
            output_path.parent.mkdir(parents=True, exist_ok=True)
            if output_path.suffix.lower() == '.jpg' or output_path.suffix.lower() == '.jpeg':
                thumb.save(output_path, 'JPEG', quality=quality)
            else:
                thumb.save(output_path, 'PNG')
            
            return True
    except Exception as e:
        print(f"  [WARN] Error generating thumbnail for {source_path}: {e}", file=sys.stderr)
        return False

def generate_preview_image(source_path, output_path, size=(512, 512), quality=90):
    """
    Generate a larger preview image from a source image.
    
    Args:
        source_path: Path to source image
        output_path: Path to save preview
        size: Preview size (width, height)
        quality: JPEG quality (1-100) if saving as JPEG
    """
    try:
        with Image.open(source_path) as img:
            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'LA', 'P'):
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                rgb_img.paste(img, mask=img.split()[3] if img.mode == 'RGBA' else None)
                img = rgb_img
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Resize maintaining aspect ratio
            img.thumbnail(size, Image.Resampling.LANCZOS)
            
            # Create preview with padding if needed
            preview = Image.new('RGB', size, (255, 255, 255))
            x_offset = (size[0] - img.size[0]) // 2
            y_offset = (size[1] - img.size[1]) // 2
            preview.paste(img, (x_offset, y_offset))
            
            # Add border
            draw = ImageDraw.Draw(preview)
            border_color = (200, 200, 200)
            draw.rectangle([0, 0, size[0]-1, size[1]-1], outline=border_color, width=2)
            
            # Save preview
            output_path.parent.mkdir(parents=True, exist_ok=True)
            if output_path.suffix.lower() == '.jpg' or output_path.suffix.lower() == '.jpeg':
                preview.save(output_path, 'JPEG', quality=quality)
            else:
                preview.save(output_path, 'PNG')
            
            return True
    except Exception as e:
        print(f"  [WARN] Error generating preview for {source_path}: {e}", file=sys.stderr)
        return False

# ============================================================
# Asset Discovery
# ============================================================

def discover_assets(assets_dir):
    """
    Discover all image assets in the assets directory.
    
    Returns:
        Dictionary mapping asset categories to lists of asset info
    """
    assets = {}
    assets_dir = Path(assets_dir)
    
    if not assets_dir.exists():
        return assets
    
    # Supported image extensions
    image_extensions = {'.png', '.jpg', '.jpeg', '.tga', '.bmp', '.gif'}
    
    # Walk through directory structure
    for item in assets_dir.rglob('*'):
        if item.is_file() and item.suffix.lower() in image_extensions:
            # Skip preview and thumbnail files
            if 'preview' in item.name.lower() or 'thumb' in item.name.lower():
                continue
            
            # Get relative path from assets directory
            rel_path = item.relative_to(assets_dir)
            category = rel_path.parts[0] if len(rel_path.parts) > 1 else 'root'
            
            if category not in assets:
                assets[category] = []
            
            # Get file info
            stat = item.stat()
            file_size = stat.st_size
            modified_time = datetime.fromtimestamp(stat.st_mtime)
            
            # Get image dimensions
            try:
                with Image.open(item) as img:
                    width, height = img.size
            except:
                width, height = 0, 0
            
            assets[category].append({
                'name': item.name,
                'path': str(rel_path),
                'full_path': str(item),
                'category': category,
                'size': file_size,
                'width': width,
                'height': height,
                'modified': modified_time.isoformat(),
            })
    
    # Sort assets by name within each category
    for category in assets:
        assets[category].sort(key=lambda x: x['name'])
    
    return assets

# ============================================================
# Catalog Generation
# ============================================================

def generate_catalog_json(assets, output_path):
    """
    Generate a JSON catalog of all assets.
    
    Args:
        assets: Dictionary of assets by category
        output_path: Path to save JSON catalog
    """
    catalog = {
        'generated': datetime.now().isoformat(),
        'total_assets': sum(len(cat_assets) for cat_assets in assets.values()),
        'categories': {},
    }
    
    for category, cat_assets in assets.items():
        catalog['categories'][category] = {
            'count': len(cat_assets),
            'assets': cat_assets
        }
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)
    
    print(f"[OK] Generated catalog: {output_path}")
    return catalog

def generate_catalog_html(assets, output_path, assets_dir, previews_dir=None):
    """
    Generate an HTML catalog for browsing assets.
    
    Args:
        assets: Dictionary of assets by category
        output_path: Path to save HTML catalog
        assets_dir: Base assets directory (for relative paths)
        previews_dir: Directory containing previews/thumbnails (optional)
    """
    html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Asset Catalog</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #f5f5f5;
            color: #333;
            padding: 20px;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .header p {
            opacity: 0.9;
            font-size: 1.1em;
        }
        
        .stats {
            display: flex;
            gap: 20px;
            margin-top: 20px;
            flex-wrap: wrap;
        }
        
        .stat {
            background: rgba(255,255,255,0.2);
            padding: 15px 20px;
            border-radius: 8px;
            backdrop-filter: blur(10px);
        }
        
        .stat-value {
            font-size: 2em;
            font-weight: bold;
        }
        
        .stat-label {
            font-size: 0.9em;
            opacity: 0.9;
        }
        
        .categories {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .category {
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .category:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }
        
        .category h2 {
            color: #667eea;
            margin-bottom: 15px;
            font-size: 1.5em;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }
        
        .category-count {
            color: #666;
            margin-bottom: 15px;
        }
        
        .assets {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
            gap: 15px;
        }
        
        .asset {
            text-align: center;
            cursor: pointer;
            transition: transform 0.2s;
        }
        
        .asset:hover {
            transform: scale(1.05);
        }
        
        .asset-thumb {
            width: 100%;
            aspect-ratio: 1;
            object-fit: contain;
            background: #f0f0f0;
            border: 2px solid #ddd;
            border-radius: 8px;
            padding: 5px;
            margin-bottom: 8px;
        }
        
        .asset-name {
            font-size: 0.85em;
            color: #666;
            word-break: break-word;
            overflow: hidden;
            text-overflow: ellipsis;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
        }
        
        .asset-info {
            font-size: 0.75em;
            color: #999;
            margin-top: 4px;
        }
        
        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.8);
            backdrop-filter: blur(5px);
        }
        
        .modal-content {
            position: relative;
            margin: 5% auto;
            max-width: 90%;
            max-height: 90%;
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }
        
        .modal-close {
            position: absolute;
            top: 10px;
            right: 20px;
            font-size: 2em;
            font-weight: bold;
            color: #999;
            cursor: pointer;
            z-index: 1001;
        }
        
        .modal-close:hover {
            color: #333;
        }
        
        .modal-preview {
            max-width: 100%;
            max-height: 70vh;
            display: block;
            margin: 0 auto;
            border-radius: 8px;
        }
        
        .modal-info {
            margin-top: 20px;
            padding: 20px;
            background: #f5f5f5;
            border-radius: 8px;
        }
        
        .modal-info h3 {
            margin-bottom: 10px;
            color: #667eea;
        }
        
        .modal-info p {
            margin: 5px 0;
            color: #666;
        }
        
        @media (max-width: 768px) {
            .categories {
                grid-template-columns: 1fr;
            }
            
            .header h1 {
                font-size: 2em;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Asset Catalog</h1>
        <p>Generated on {generated_date}</p>
        <div class="stats">
            <div class="stat">
                <div class="stat-value">{total_assets}</div>
                <div class="stat-label">Total Assets</div>
            </div>
            <div class="stat">
                <div class="stat-value">{total_categories}</div>
                <div class="stat-label">Categories</div>
            </div>
        </div>
    </div>
    
    <div class="categories">
"""
    
    # Calculate totals
    total_assets = sum(len(cat_assets) for cat_assets in assets.values())
    total_categories = len(assets)
    generated_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Generate category sections
    for category, cat_assets in sorted(assets.items()):
        html += f"""        <div class="category">
            <h2>{category.title()}</h2>
            <div class="category-count">{len(cat_assets)} assets</div>
            <div class="assets">
"""
        
        for asset in cat_assets:
            # Determine thumbnail path
            thumb_path = asset['path']
            if previews_dir:
                # Try to find thumbnail in previews directory
                thumb_file = Path(previews_dir) / 'thumbnails' / asset['path']
                if thumb_file.exists():
                    thumb_path = str(Path('previews') / 'thumbnails' / asset['path'])
                else:
                    # Use original asset
                    thumb_path = asset['path']
            else:
                thumb_path = asset['path']
            
            # Format file size
            size_kb = asset['size'] / 1024
            size_str = f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_kb/1024:.1f} MB"
            
            # Dimensions
            dims = f"{asset['width']}x{asset['height']}" if asset['width'] > 0 else "Unknown"
            
            html += f"""                <div class="asset" onclick="showPreview('{asset['path'].replace(chr(92), '/')}', '{asset['name']}', {asset['width']}, {asset['height']}, '{size_str}', '{asset['modified']}')">
                    <img src="{thumb_path.replace(chr(92), '/')}" alt="{asset['name']}" class="asset-thumb" loading="lazy">
                    <div class="asset-name">{asset['name']}</div>
                    <div class="asset-info">{dims} - {size_str}</div>
                </div>
"""
        
        html += """            </div>
        </div>
"""
    
    html += """    </div>
    
    <div id="previewModal" class="modal" onclick="closePreview()">
        <div class="modal-content" onclick="event.stopPropagation()">
            <span class="modal-close" onclick="closePreview()">&times;</span>
            <img id="previewImage" class="modal-preview" src="" alt="Preview">
            <div class="modal-info">
                <h3 id="previewName"></h3>
                <p><strong>Dimensions:</strong> <span id="previewDims"></span></p>
                <p><strong>Size:</strong> <span id="previewSize"></span></p>
                <p><strong>Modified:</strong> <span id="previewModified"></span></p>
            </div>
        </div>
    </div>
    
    <script>
        function showPreview(path, name, width, height, size, modified) {
            const modal = document.getElementById('previewModal');
            const img = document.getElementById('previewImage');
            const nameEl = document.getElementById('previewName');
            const dimsEl = document.getElementById('previewDims');
            const sizeEl = document.getElementById('previewSize');
            const modifiedEl = document.getElementById('previewModified');
            
            img.src = path;
            nameEl.textContent = name;
            dimsEl.textContent = width + ' x ' + height;
            sizeEl.textContent = size;
            modifiedEl.textContent = new Date(modified).toLocaleString();
            
            modal.style.display = 'block';
        }
        
        function closePreview() {
            document.getElementById('previewModal').style.display = 'none';
        }
        
        // Close on Escape key
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                closePreview();
            }
        });
    </script>
</body>
</html>
"""
    
    # Replace placeholders
    html = html.format(
        generated_date=generated_date,
        total_assets=total_assets,
        total_categories=total_categories
    )
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"[OK] Generated HTML catalog: {output_path}")

# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(description='Generate preview thumbnails and asset catalog')
    parser.add_argument('--assets-dir', required=True, help='Directory containing assets')
    parser.add_argument('--output-dir', required=True, help='Output directory for previews and catalog')
    parser.add_argument('--thumbnail-size', type=int, nargs=2, default=[128, 128], 
                        metavar=('WIDTH', 'HEIGHT'), help='Thumbnail size (default: 128 128)')
    parser.add_argument('--preview-size', type=int, nargs=2, default=[512, 512],
                        metavar=('WIDTH', 'HEIGHT'), help='Preview size (default: 512 512)')
    parser.add_argument('--skip-thumbnails', action='store_true', 
                        help='Skip thumbnail generation')
    parser.add_argument('--skip-previews', action='store_true',
                        help='Skip preview image generation')
    parser.add_argument('--skip-catalog', action='store_true',
                        help='Skip catalog generation')
    
    args = parser.parse_args()
    
    # Validate arguments
    assets_dir = Path(args.assets_dir)
    output_dir = Path(args.output_dir)
    
    if not assets_dir.exists():
        print(f"ERROR: Assets directory does not exist: {assets_dir}", file=sys.stderr)
        print(f"  Please check the path and try again.", file=sys.stderr)
        return 1
    
    if not assets_dir.is_dir():
        print(f"ERROR: Assets path is not a directory: {assets_dir}", file=sys.stderr)
        return 1
    
    print(f"Discovering assets in {assets_dir}...")
    assets = discover_assets(assets_dir)
    
    if not assets:
        print("  [WARN] No assets found")
        return 0
    
    total_assets = sum(len(cat_assets) for cat_assets in assets.values())
    print(f"  [OK] Found {total_assets} assets in {len(assets)} categories")
    
    # Generate thumbnails
    if not args.skip_thumbnails:
        print(f"\nGenerating thumbnails...")
        thumbnails_dir = output_dir / 'previews' / 'thumbnails'
        thumbnails_generated = 0
        thumbnails_failed = 0
        
        for category, cat_assets in assets.items():
            for asset in cat_assets:
                source_path = Path(asset['full_path'])
                thumb_path = thumbnails_dir / asset['path']
                
                try:
                    if generate_thumbnail(source_path, thumb_path, tuple(args.thumbnail_size)):
                        thumbnails_generated += 1
                    else:
                        thumbnails_failed += 1
                except Exception as e:
                    print(f"  [WARN] Failed to generate thumbnail for {asset['name']}: {e}", file=sys.stderr)
                    thumbnails_failed += 1
        
        print(f"  [OK] Generated {thumbnails_generated} thumbnails")
        if thumbnails_failed > 0:
            print(f"  [WARN] Failed to generate {thumbnails_failed} thumbnails", file=sys.stderr)
    
    # Generate preview images
    if not args.skip_previews:
        print(f"\nGenerating preview images...")
        previews_dir = output_dir / 'previews' / 'images'
        previews_generated = 0
        previews_failed = 0
        
        for category, cat_assets in assets.items():
            for asset in cat_assets:
                source_path = Path(asset['full_path'])
                preview_path = previews_dir / asset['path']
                
                try:
                    if generate_preview_image(source_path, preview_path, tuple(args.preview_size)):
                        previews_generated += 1
                    else:
                        previews_failed += 1
                except Exception as e:
                    print(f"  [WARN] Failed to generate preview for {asset['name']}: {e}", file=sys.stderr)
                    previews_failed += 1
        
        print(f"  [OK] Generated {previews_generated} preview images")
        if previews_failed > 0:
            print(f"  [WARN] Failed to generate {previews_failed} preview images", file=sys.stderr)
    
    # Generate catalog
    if not args.skip_catalog:
        print(f"\nGenerating asset catalog...")
        
        try:
            # JSON catalog
            catalog_json = output_dir / 'catalog.json'
            generate_catalog_json(assets, catalog_json)
        except Exception as e:
            print(f"  [ERROR] Failed to generate JSON catalog: {e}", file=sys.stderr)
            return 1
        
        try:
            # HTML catalog
            previews_dir = output_dir / 'previews' if not args.skip_thumbnails else None
            catalog_html = output_dir / 'catalog.html'
            generate_catalog_html(assets, catalog_html, assets_dir, 
                                str(previews_dir) if previews_dir else None)
        except Exception as e:
            print(f"  [ERROR] Failed to generate HTML catalog: {e}", file=sys.stderr)
            print(f"  [INFO] JSON catalog was generated successfully", file=sys.stderr)
            return 1
    
    print(f"\n[OK] Preview generation complete!")
    return 0

if __name__ == '__main__':
    sys.exit(main())
