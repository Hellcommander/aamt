#!/usr/bin/env python3
"""
Terraria Portal Asset Quality Checker
Assesses quality of generated portal assets for tModLoader mods
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from PIL import Image
import sys

def check_image_quality(image_path: Path) -> Dict:
    """Check individual image quality metrics."""
    if not image_path.exists():
        return None
    
    try:
        img = Image.open(image_path)
        width, height = img.size
        file_size = image_path.stat().st_size
        
        # Check if has alpha channel
        has_alpha = img.mode in ('RGBA', 'LA') or 'transparency' in img.info
        
        # Check color count (simpler images are better for game assets)
        if img.mode == 'P':
            colors = len(img.getcolors(maxcolors=256*256*256))
        else:
            colors = len(img.getcolors(maxcolors=256*256*256)) if img.mode != 'RGBA' else 'many'
        
        # Quality score calculation
        score = 10.0
        
        # Dimension checks (Terraria tiles are typically 16x16 or 32x32)
        if width == 16 and height == 16:
            score += 0.5  # Perfect standard size
        elif width == 32 and height == 32:
            score += 0.3  # Good high-res size
        elif width % 16 == 0 and height % 16 == 0:
            score += 0.1  # Valid multiple
        else:
            score -= 2.0  # Invalid size
        
        # File size check (should be reasonable for game assets)
        size_kb = file_size / 1024
        if size_kb < 1:
            score += 0.5  # Very small, good
        elif size_kb < 5:
            score += 0.3  # Small, good
        elif size_kb < 20:
            score += 0.0  # Acceptable
        else:
            score -= 1.0  # Too large
        
        # Alpha channel check
        if has_alpha:
            score += 0.5  # Has transparency, good for portals
        else:
            score -= 0.5  # No transparency, portals usually need it
        
        # Format check
        if image_path.suffix.lower() == '.png':
            score += 0.2  # PNG is correct format
        
        # Notes
        notes = []
        if width != 16 and width != 32:
            notes.append(f"Non-standard size: {width}x{height}")
        if not has_alpha:
            notes.append("Missing alpha channel")
        if size_kb > 20:
            notes.append(f"Large file size: {size_kb:.1f}KB")
        
        return {
            'path': str(image_path),
            'width': width,
            'height': height,
            'size_kb': round(size_kb, 2),
            'has_alpha': has_alpha,
            'colors': colors,
            'score': round(score, 2),
            'notes': notes
        }
    except Exception as e:
        return {
            'path': str(image_path),
            'error': str(e),
            'score': 0.0
        }

def check_portal_profile(profile_path: Path) -> Dict:
    """Check portal profile JSON quality."""
    if not profile_path.exists():
        return None
    
    try:
        with open(profile_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        score = 10.0
        notes = []
        
        # Check required fields
        required_fields = ['id', 'game', 'type', 'tiles', 'particles', 'shader']
        for field in required_fields:
            if field not in data:
                score -= 2.0
                notes.append(f"Missing required field: {field}")
        
        # Check tile size
        if 'tiles' in data:
            tile_size = data['tiles'].get('size', 0)
            if tile_size in [16, 32]:
                score += 0.5
            elif tile_size > 0:
                notes.append(f"Non-standard tile size: {tile_size}")
            else:
                score -= 1.0
                notes.append("Invalid or missing tile size")
        
        # Check particle configuration
        if 'particles' in data:
            particle_count = data['particles'].get('count', 0)
            if 20 <= particle_count <= 100:
                score += 0.3
            elif particle_count > 100:
                notes.append(f"High particle count: {particle_count} (may impact performance)")
            elif particle_count < 20:
                notes.append(f"Low particle count: {particle_count}")
        
        # Check colors
        if 'particles' in data and 'colors' in data['particles']:
            colors = data['particles']['colors']
            if all(key in colors for key in ['core', 'rim', 'accent']):
                score += 0.2
            else:
                notes.append("Missing color definitions")
        
        return {
            'path': str(profile_path),
            'id': data.get('id', 'unknown'),
            'score': round(score, 2),
            'notes': notes,
            'tile_size': data.get('tiles', {}).get('size', 0),
            'particle_count': data.get('particles', {}).get('count', 0)
        }
    except Exception as e:
        return {
            'path': str(profile_path),
            'error': str(e),
            'score': 0.0
        }

def generate_quality_report(assets_dir: Path):
    """Generate comprehensive quality report for portal assets."""
    
    reports = {
        'images': [],
        'profiles': []
    }
    
    # Find all portal directories
    portal_dirs = [d for d in assets_dir.iterdir() if d.is_dir() and 'Portal' in d.name]
    
    for portal_dir in portal_dirs:
        portal_name = portal_dir.name
        
        # Check images in Textures subdirectory
        textures_dir = portal_dir / "Textures"
        if textures_dir.exists():
            for img_file in textures_dir.glob("*.png"):
                result = check_image_quality(img_file)
                if result:
                    result['portal'] = portal_name
                    reports['images'].append(result)
        
        # Check images in Items and Tiles directories
        for subdir in ['Items', 'Tiles']:
            subdir_path = assets_dir / subdir
            if subdir_path.exists():
                for img_file in subdir_path.glob(f"*{portal_name}*.png"):
                    result = check_image_quality(img_file)
                    if result:
                        result['portal'] = portal_name
                        result['category'] = subdir
                        reports['images'].append(result)
        
        # Check profile JSON
        profile_file = portal_dir / f"{portal_name}_profile.json"
        if profile_file.exists():
            result = check_portal_profile(profile_file)
            if result:
                result['portal'] = portal_name
                reports['profiles'].append(result)
    
    # Generate markdown report
    report_path = assets_dir / "PORTAL_QUALITY_REPORT.md"
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# Terraria Portal Asset Quality Report\n\n")
        f.write("Quality assessment of generated portal assets for CrossModStabilizer mod.\n\n")
        f.write("=" * 80 + "\n\n")
        
        # Image Quality Section
        f.write("## Image Assets\n\n")
        
        if reports['images']:
            # Summary
            total_images = len(reports['images'])
            high_quality = len([img for img in reports['images'] if img.get('score', 0) >= 8.0])
            low_quality = total_images - high_quality
            
            f.write(f"- **Total Images**: {total_images}\n")
            f.write(f"- **High Quality (>= 8.0)**: {high_quality}\n")
            f.write(f"- **Low Quality (< 8.0)**: {low_quality}\n")
            f.write(f"- **Quality Rate**: {high_quality / total_images * 100:.1f}%\n\n")
            
            # Detailed table
            f.write("### Image Quality Details\n\n")
            f.write("| Portal | Category | File | Dimensions | Size | Alpha | Score | Notes |\n")
            f.write("|--------|----------|------|------------|------|-------|-------|-------|\n")
            
            for img in sorted(reports['images'], key=lambda x: x.get('score', 0)):
                portal = img.get('portal', 'N/A')
                category = img.get('category', 'Textures')
                filename = Path(img['path']).name
                dims = f"{img.get('width', 0)}x{img.get('height', 0)}"
                size = f"{img.get('size_kb', 0)}KB"
                alpha = "✓" if img.get('has_alpha', False) else "✗"
                score = img.get('score', 0)
                notes = ", ".join(img.get('notes', []))[:50] or "-"
                
                f.write(f"| {portal} | {category} | {filename} | {dims} | {size} | {alpha} | {score:.2f} | {notes} |\n")
            
            f.write("\n")
            
            # Low quality details
            low_quality_imgs = [img for img in reports['images'] if img.get('score', 0) < 8.0]
            if low_quality_imgs:
                f.write("### Low Quality Images (< 8.0)\n\n")
                for img in low_quality_imgs:
                    f.write(f"#### {Path(img['path']).name}\n\n")
                    f.write(f"- **Score**: {img.get('score', 0):.2f}\n")
                    f.write(f"- **Dimensions**: {img.get('width', 0)}x{img.get('height', 0)}\n")
                    f.write(f"- **Size**: {img.get('size_kb', 0)}KB\n")
                    f.write(f"- **Alpha Channel**: {'Yes' if img.get('has_alpha', False) else 'No'}\n")
                    if img.get('notes'):
                        f.write(f"- **Issues**: {', '.join(img['notes'])}\n")
                    f.write("\n")
        else:
            f.write("No image assets found.\n\n")
        
        f.write("\n" + "-" * 80 + "\n\n")
        
        # Profile Quality Section
        f.write("## Portal Profiles\n\n")
        
        if reports['profiles']:
            total_profiles = len(reports['profiles'])
            high_quality = len([p for p in reports['profiles'] if p.get('score', 0) >= 8.0])
            
            f.write(f"- **Total Profiles**: {total_profiles}\n")
            f.write(f"- **High Quality (>= 8.0)**: {high_quality}\n")
            f.write(f"- **Low Quality (< 8.0)**: {total_profiles - high_quality}\n\n")
            
            f.write("### Profile Quality Details\n\n")
            for profile in reports['profiles']:
                f.write(f"#### {profile.get('id', 'unknown')}\n\n")
                f.write(f"- **Score**: {profile.get('score', 0):.2f}\n")
                f.write(f"- **Tile Size**: {profile.get('tile_size', 0)}\n")
                f.write(f"- **Particle Count**: {profile.get('particle_count', 0)}\n")
                if profile.get('notes'):
                    f.write(f"- **Notes**: {', '.join(profile['notes'])}\n")
                f.write("\n")
        else:
            f.write("No profile files found.\n\n")
        
        # Recommendations
        f.write("\n" + "=" * 80 + "\n\n")
        f.write("## Recommendations\n\n")
        f.write("1. **Standard Sizes**: Use 16x16 or 32x32 pixels for Terraria tiles\n")
        f.write("2. **Alpha Channel**: Ensure all portal textures have transparency\n")
        f.write("3. **File Size**: Keep images under 5KB for optimal performance\n")
        f.write("4. **Profile Completeness**: Ensure all required fields are present in JSON profiles\n")
        f.write("5. **Particle Count**: Keep particle counts between 20-100 for balance\n")
        f.write("6. **Test In-Game**: Always verify visual quality in tModLoader\n")
    
    print(f"Quality report saved: {report_path}")
    print(f"\nSummary:")
    print(f"  Total images: {len(reports['images'])}")
    print(f"  High quality (>= 8.0): {len([img for img in reports['images'] if img.get('score', 0) >= 8.0])}")
    print(f"  Total profiles: {len(reports['profiles'])}")
    
    return report_path

if __name__ == "__main__":
    assets_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("d:/User_Directories/Documents/My Games/Terraria/tModLoader/ModSources/CrossModStabilizer/Assets")
    generate_quality_report(assets_dir)

