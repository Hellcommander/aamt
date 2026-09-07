#!/usr/bin/env python3
"""
Starbound Asset Quality Checker
Assesses quality of generated assets for Starbound mods and keeps only the best ones
Uses Ollama AI assistance for enhanced quality assessment and recommendations
"""

import json
import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from PIL import Image
import sys
from collections import defaultdict
import requests
import base64
from io import BytesIO

# Ollama configuration
# Model auto-selection: tries llama3.1:8b, then wizardlm-uncensored, then first available
OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = ""  # Auto-selected - will try llama3.1:8b, wizardlm-uncensored, or first available

def check_ollama_connection() -> bool:
    """Check if Ollama is available."""
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=2)
        return response.status_code == 200
    except:
        return False

def get_available_ollama_model() -> str:
    """Auto-select best available Ollama model for visual/analysis tasks."""
    if not check_ollama_connection():
        return ""
    
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=2)
        if response.status_code == 200:
            models = response.json().get('models', [])
            model_names = [m.get('name', '') for m in models]
            
            # Preferred models in order (matching OllamaIntegration.psm1 preferences)
            preferred_models = [
                "llama3.1:8b",           # Tier 1: Creative concepting
                "wizardlm-uncensored",    # Tier 1/2: Visual/creative
                "qwen2.5-coder:14b",      # Tier 1: Structured planning
                "qwen2.5-coder:7b",       # Tier 1: Simple tasks
                "deepseek-r1:7b",         # Tier 1: Hybrid tasks
            ]
            
            # Try to find preferred model
            for preferred in preferred_models:
                # Check exact match
                if preferred in model_names:
                    return preferred
                # Check partial match (e.g., "wizardlm-uncensored" matches "wizardlm-uncensored:latest")
                base_name = preferred.split(':')[0]
                matching = [m for m in model_names if m.startswith(base_name)]
                if matching:
                    return matching[0]
            
            # Fallback: return first available model
            if model_names:
                return model_names[0]
    except:
        pass
    
    return ""

def enhance_quality_assessment_with_ollama(image_path: Path, basic_metrics: Dict) -> Dict:
    """Use Ollama to enhance quality assessment with AI analysis."""
    if not check_ollama_connection():
        return basic_metrics
    
    # Auto-select model if not specified
    model_to_use = OLLAMA_MODEL if OLLAMA_MODEL else get_available_ollama_model()
    if not model_to_use:
        return basic_metrics
    
    try:
        # Read image and convert to base64 for analysis
        img = Image.open(image_path)
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        # Create prompt for Ollama
        prompt = f"""Analyze this Starbound game asset image and provide quality assessment:

Basic Metrics:
- Dimensions: {basic_metrics.get('width', 0)}x{basic_metrics.get('height', 0)}
- File Size: {basic_metrics.get('size_kb', 0)}KB
- Has Alpha: {basic_metrics.get('has_alpha', False)}
- Color Count: {basic_metrics.get('colors', 'unknown')}

Provide assessment focusing on:
1. Visual quality and detail level
2. Suitability for Starbound game style (pixel art)
3. Color palette appropriateness
4. Overall asset quality score (0-10)
5. Specific recommendations for improvement

Return ONLY a JSON object with keys: quality_score, visual_assessment, style_match, recommendations
"""
        
        body = {
            "model": model_to_use,
            "prompt": prompt,
            "stream": False
        }
        
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json=body,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            ai_response = result.get('response', '').strip()
            
            # Try to extract JSON from response
            try:
                # Find JSON in response
                json_start = ai_response.find('{')
                json_end = ai_response.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    ai_assessment = json.loads(ai_response[json_start:json_end])
                    
                    # Enhance basic metrics with AI assessment
                    if 'quality_score' in ai_assessment:
                        ai_score = float(ai_assessment['quality_score'])
                        # Blend AI score with basic metrics (70% AI, 30% basic)
                        basic_metrics['ai_enhanced_score'] = round(
                            (ai_score * 0.7) + (basic_metrics.get('score', 0) * 0.3), 2
                        )
                        basic_metrics['ai_assessment'] = ai_assessment
                        basic_metrics['ollama_enhanced'] = True
            except:
                # If JSON parsing fails, add raw response as note
                basic_metrics['ai_notes'] = ai_response[:200]
                basic_metrics['ollama_enhanced'] = False
    except Exception as e:
        basic_metrics['ollama_error'] = str(e)
        basic_metrics['ollama_enhanced'] = False
    
    return basic_metrics

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
        try:
            if img.mode == 'P':
                colors = len(img.getcolors(maxcolors=256*256*256))
            else:
                colors = len(img.getcolors(maxcolors=256*256*256)) if img.mode != 'RGBA' else 'many'
        except:
            colors = 'many'
        
        # Quality score calculation
        score = 10.0
        
        # Dimension checks (Starbound uses 8x8, 16x16, 32x32, and multiples)
        valid_sizes = [8, 16, 32, 64, 128, 256]
        if width in valid_sizes and height in valid_sizes:
            if width == 16 and height == 16:
                score += 0.5  # Perfect standard item size
            elif width == 32 and height == 32:
                score += 0.5  # Perfect standard animation size
            elif width == 8 and height == 8:
                score += 0.3  # Small tile size
            elif width == height:
                score += 0.2  # Square is good
            else:
                score += 0.1  # Valid size but not square
        elif width % 8 == 0 and height % 8 == 0:
            score += 0.1  # Valid multiple of 8
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
        elif size_kb < 100:
            score -= 0.5  # Large
        else:
            score -= 1.5  # Too large
        
        # Alpha channel check (most Starbound assets need transparency)
        if has_alpha:
            score += 0.5  # Has transparency, good
        else:
            score -= 0.3  # No transparency (may be okay for some assets)
        
        # Format check
        if image_path.suffix.lower() == '.png':
            score += 0.2  # PNG is correct format
        else:
            score -= 1.0  # Wrong format
        
        # Check if image is not blank/empty
        try:
            if img.mode == 'RGBA':
                # Check if has non-transparent pixels
                alpha = img.split()[3]
                if alpha.getextrema()[1] == 0:
                    score -= 5.0  # Completely transparent
            elif img.mode == 'RGB':
                # Check if not all white/black
                extrema = img.getextrema()
                if all(c[0] == c[1] for c in extrema):
                    if extrema[0][0] == 255 or extrema[0][0] == 0:
                        score -= 3.0  # All white or all black
        except:
            pass
        
        # Notes
        notes = []
        if width not in valid_sizes or height not in valid_sizes:
            if width % 8 != 0 or height % 8 != 0:
                notes.append(f"Non-standard size: {width}x{height}")
        if not has_alpha:
            notes.append("Missing alpha channel")
        if size_kb > 20:
            notes.append(f"Large file size: {size_kb:.1f}KB")
        if colors == 'many' or (isinstance(colors, int) and colors > 256):
            notes.append("High color count (may be inefficient)")
        
        result = {
            'path': str(image_path),
            'width': width,
            'height': height,
            'size_kb': round(size_kb, 2),
            'has_alpha': has_alpha,
            'colors': colors,
            'score': round(score, 2),
            'notes': notes
        }
        
        # Enhance with Ollama AI assessment if available
        if check_ollama_connection():
            result = enhance_quality_assessment_with_ollama(image_path, result)
            if result.get('ollama_enhanced'):
                # Use AI-enhanced score if available
                if 'ai_enhanced_score' in result:
                    result['score'] = result['ai_enhanced_score']
                    result['notes'].append("AI-enhanced quality assessment")
        
        return result
    except Exception as e:
        return {
            'path': str(image_path),
            'error': str(e),
            'score': 0.0
        }

def check_json_quality(json_path: Path) -> Dict:
    """Check JSON file quality with Starbound-specific validation."""
    if not json_path.exists():
        return None
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        score = 10.0
        notes = []
        file_type = json_path.suffix.lower()
        
        # Basic JSON structure check
        if not isinstance(data, dict):
            score -= 2.0
            notes.append("Not a valid JSON object")
            return {
                'path': str(json_path),
                'score': round(score, 2),
                'notes': notes
            }
        
        # Starbound-specific file type checks
        if file_type == '.particle':
            # Check particle file structure
            if 'kind' in data and 'definition' in data:
                score += 0.5
                defn = data['definition']
                if 'type' in defn:
                    score += 0.2
                if 'timeToLive' in defn:
                    score += 0.1
            else:
                score -= 1.0
                notes.append("Missing required particle fields (kind, definition)")
        
        elif file_type == '.behavior':
            # Check behavior file structure
            if 'name' in data and 'root' in data:
                score += 0.5
                if 'scripts' in data:
                    score += 0.2
            else:
                score -= 1.0
                notes.append("Missing required behavior fields (name, root)")
        
        elif file_type == '.cursor':
            # Check cursor file structure
            if 'offset' in data and 'image' in data:
                score += 0.5
            else:
                score -= 1.0
                notes.append("Missing required cursor fields (offset, image)")
        
        elif file_type == '.frames':
            # Check frames file structure
            if 'frameGrid' in data:
                score += 0.5
                fg = data['frameGrid']
                if 'size' in fg and 'dimensions' in fg:
                    score += 0.3
            elif 'frameList' in data:
                score += 0.5  # Tile frames format
                if len(data['frameList']) > 0:
                    score += 0.2
            else:
                score -= 0.5
                notes.append("Missing frameGrid or frameList")
        
        elif file_type == '.material':
            # Check material file structure
            if 'materialId' in data and 'materialName' in data:
                score += 0.5
                if 'renderTemplate' in data:
                    score += 0.2
            else:
                score -= 1.0
                notes.append("Missing required material fields")
        
        elif file_type == '.structure':
            # Check structure file structure
            if 'config' in data or 'blockKey' in data:
                score += 0.5
            else:
                score -= 0.5
                notes.append("Missing structure configuration")
        
        elif file_type == '.animation':
            # Check animation file structure
            if 'frames' in data and 'frameNumber' in data:
                score += 0.5
                if 'animationCycle' in data:
                    score += 0.2
            else:
                score -= 1.0
                notes.append("Missing required animation fields")
        
        else:
            # Generic JSON check
            if 'frames' in data:
                frames = data['frames']
                if isinstance(frames, dict) and len(frames) > 0:
                    score += 0.3
                elif len(frames) == 0:
                    notes.append("Empty frames object")
            elif 'image' in data or 'texture' in data:
                score += 0.2  # Has image reference
        
        return {
            'path': str(json_path),
            'file_type': file_type,
            'score': round(score, 2),
            'notes': notes
        }
    except json.JSONDecodeError as e:
        return {
            'path': str(json_path),
            'error': f"Invalid JSON: {str(e)}",
            'score': 0.0
        }
    except Exception as e:
        return {
            'path': str(json_path),
            'error': str(e),
            'score': 0.0
        }

def find_asset_candidates(assets_dir: Path, asset_name: str) -> List[Path]:
    """Find all candidate files for a given asset name."""
    candidates = []
    
    # Look for files with the asset name in various formats
    patterns = [
        f"*{asset_name}*.png",
        f"*{asset_name}*.json",
        f"{asset_name}*.png",
        f"{asset_name}*.json"
    ]
    
    for pattern in patterns:
        candidates.extend(assets_dir.rglob(pattern))
    
    # Also check subdirectories
    for subdir in ['items', 'sprites', 'animations', 'projectiles', 'particles', 'textures']:
        subdir_path = assets_dir / subdir
        if subdir_path.exists():
            for pattern in patterns:
                candidates.extend(subdir_path.rglob(pattern))
    
    return list(set(candidates))  # Remove duplicates

def select_best_assets(assets_dir: Path, quality_threshold: float = 7.0) -> Dict:
    """Scan assets directory, check quality, and select best candidates."""
    
    reports = {
        'images': [],
        'json_files': [],
        'best_assets': {},
        'removed_assets': []
    }
    
    # Group assets by base name
    asset_groups = defaultdict(list)
    
    # Find all PNG and JSON files (including Starbound-specific formats)
    for img_file in assets_dir.rglob("*.png"):
        base_name = img_file.stem
        # Remove common suffixes
        for suffix in ['_candidate', '_v', '_version', '_alt', '_variant']:
            if base_name.endswith(suffix):
                base_name = base_name[:-len(suffix)]
                break
        asset_groups[base_name].append(img_file)
    
    # Find all JSON files and Starbound-specific JSON-like files
    json_patterns = ['*.json', '*.particle', '*.behavior', '*.cursor', '*.frames', 
                     '*.material', '*.matmod', '*.structure', '*.animation']
    
    for pattern in json_patterns:
        for json_file in assets_dir.rglob(pattern):
            if 'quality_report' in json_file.name or 'best_assets' in json_file.name:
                continue  # Skip our own report files
            base_name = json_file.stem
            asset_groups[base_name].append(json_file)
    
    # Check quality of each asset group
    for asset_name, files in asset_groups.items():
        if len(files) <= 1:
            # Only one candidate, check quality but keep it
            for file_path in files:
                if file_path.suffix.lower() == '.png':
                    result = check_image_quality(file_path)
                    if result:
                        result['asset_name'] = asset_name
                        reports['images'].append(result)
                        if result.get('score', 0) >= quality_threshold:
                            reports['best_assets'][asset_name] = {
                                'file': str(file_path),
                                'score': result['score'],
                                'type': 'image'
                            }
                elif file_path.suffix.lower() == '.json':
                    result = check_json_quality(file_path)
                    if result:
                        result['asset_name'] = asset_name
                        reports['json_files'].append(result)
                        if result.get('score', 0) >= quality_threshold:
                            reports['best_assets'][asset_name] = {
                                'file': str(file_path),
                                'score': result['score'],
                                'type': 'json'
                            }
        else:
            # Multiple candidates - find the best one
            candidates = []
            for file_path in files:
                if file_path.suffix.lower() == '.png':
                    result = check_image_quality(file_path)
                    if result:
                        result['asset_name'] = asset_name
                        result['file_path'] = file_path
                        reports['images'].append(result)
                        candidates.append(('image', result, file_path))
                elif file_path.suffix.lower() in ['.json', '.particle', '.behavior', '.cursor', 
                                                    '.frames', '.material', '.matmod', '.structure', '.animation']:
                    result = check_json_quality(file_path)
                    if result:
                        result['asset_name'] = asset_name
                        result['file_path'] = file_path
                        reports['json_files'].append(result)
                        candidates.append(('json', result, file_path))
            
            if candidates:
                # Sort by score (highest first)
                candidates.sort(key=lambda x: x[1].get('score', 0), reverse=True)
                best = candidates[0]
                
                if best[1].get('score', 0) >= quality_threshold:
                    # Keep the best one
                    reports['best_assets'][asset_name] = {
                        'file': str(best[2]),
                        'score': best[1]['score'],
                        'type': best[0]
                    }
                    
                    # Mark others for removal
                    for asset_type, result, file_path in candidates[1:]:
                        reports['removed_assets'].append({
                            'file': str(file_path),
                            'score': result.get('score', 0),
                            'reason': f"Lower quality than best candidate (score: {best[1]['score']:.2f})"
                        })
                else:
                    # All candidates below threshold - mark all for removal
                    for asset_type, result, file_path in candidates:
                        reports['removed_assets'].append({
                            'file': str(file_path),
                            'score': result.get('score', 0),
                            'reason': f"Below quality threshold ({quality_threshold})"
                        })
    
    return reports

def remove_low_quality_assets(reports: Dict, dry_run: bool = False) -> int:
    """Remove low quality assets, keeping only the best ones."""
    removed_count = 0
    
    # Create a set of files to keep
    files_to_keep = set()
    for asset_info in reports['best_assets'].values():
        files_to_keep.add(Path(asset_info['file']))
    
    # Remove files not in the keep set
    for removed_info in reports['removed_assets']:
        file_path = Path(removed_info['file'])
        if file_path not in files_to_keep and file_path.exists():
            if not dry_run:
                try:
                    file_path.unlink()
                    removed_count += 1
                    print(f"Removed: {file_path.name} (score: {removed_info['score']:.2f})")
                except Exception as e:
                    print(f"Error removing {file_path}: {e}")
            else:
                print(f"[DRY RUN] Would remove: {file_path.name} (score: {removed_info['score']:.2f})")
                removed_count += 1
    
    return removed_count

def generate_quality_report(assets_dir: Path, quality_threshold: float = 7.0, dry_run: bool = False):
    """Generate comprehensive quality report and clean up low quality assets."""
    
    print(f"Scanning assets directory: {assets_dir}")
    print(f"Quality threshold: {quality_threshold}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    
    # Check Ollama availability
    if check_ollama_connection():
        print(f"✓ Ollama AI assistance available - using enhanced quality assessment")
    else:
        print(f"⚠ Ollama not available - using basic quality metrics")
    print()
    
    reports = select_best_assets(assets_dir, quality_threshold)
    
    # Remove low quality assets
    removed_count = remove_low_quality_assets(reports, dry_run)
    
    # Generate markdown report
    report_path = assets_dir / "ASSET_QUALITY_REPORT.md"
    mapping_path = assets_dir / "BEST_ASSETS_MAPPING.md"
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# Starbound Asset Quality Report\n\n")
        f.write(f"Quality assessment of generated assets for Starbound mod.\n\n")
        f.write(f"**Quality Threshold**: {quality_threshold}\n")
        f.write(f"**Mode**: {'DRY RUN' if dry_run else 'LIVE'}\n")
        f.write(f"**Assets Removed**: {removed_count}\n\n")
        f.write("=" * 80 + "\n\n")
        
        # Image Quality Section
        f.write("## Image Assets\n\n")
        
        if reports['images']:
            # Summary
            total_images = len(reports['images'])
            high_quality = len([img for img in reports['images'] if img.get('score', 0) >= quality_threshold])
            low_quality = total_images - high_quality
            
            f.write(f"- **Total Images**: {total_images}\n")
            f.write(f"- **High Quality (>= {quality_threshold})**: {high_quality}\n")
            f.write(f"- **Low Quality (< {quality_threshold})**: {low_quality}\n")
            if total_images > 0:
                f.write(f"- **Quality Rate**: {high_quality / total_images * 100:.1f}%\n\n")
            
            # Best assets summary
            f.write("### Best Assets Selected\n\n")
            best_images = {k: v for k, v in reports['best_assets'].items() if v['type'] == 'image'}
            if best_images:
                f.write("| Asset Name | File | Score |\n")
                f.write("|------------|------|-------|\n")
                for asset_name, info in sorted(best_images.items()):
                    filename = Path(info['file']).name
                    f.write(f"| {asset_name} | {filename} | {info['score']:.2f} |\n")
                f.write("\n")
            else:
                f.write("No high-quality images found.\n\n")
            
            # Low quality details
            low_quality_imgs = [img for img in reports['images'] if img.get('score', 0) < quality_threshold]
            if low_quality_imgs:
                f.write("### Low Quality Images (< {})\n\n".format(quality_threshold))
                for img in sorted(low_quality_imgs, key=lambda x: x.get('score', 0)):
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
        
        # JSON Files Section (including Starbound-specific formats)
        f.write("## JSON Configuration Files\n\n")
        
        if reports['json_files']:
            total_json = len(reports['json_files'])
            high_quality = len([j for j in reports['json_files'] if j.get('score', 0) >= quality_threshold])
            
            # Group by file type
            by_type = {}
            for j in reports['json_files']:
                file_type = j.get('file_type', 'json')
                if file_type not in by_type:
                    by_type[file_type] = []
                by_type[file_type].append(j)
            
            f.write(f"- **Total JSON/Config Files**: {total_json}\n")
            f.write(f"- **High Quality (>= {quality_threshold})**: {high_quality}\n")
            f.write(f"- **Low Quality (< {quality_threshold})**: {total_json - high_quality}\n\n")
            
            # Show breakdown by type
            if len(by_type) > 1:
                f.write("### By File Type\n\n")
                f.write("| Type | Count | High Quality |\n")
                f.write("|------|-------|--------------|\n")
                for file_type, files in sorted(by_type.items()):
                    high = len([f for f in files if f.get('score', 0) >= quality_threshold])
                    f.write(f"| {file_type} | {len(files)} | {high} |\n")
                f.write("\n")
        else:
            f.write("No JSON/configuration files found.\n\n")
        
        # Removed Assets Section
        if reports['removed_assets']:
            f.write("\n" + "=" * 80 + "\n\n")
            f.write("## Removed Assets\n\n")
            f.write(f"**Total Removed**: {len(reports['removed_assets'])}\n\n")
            f.write("| File | Score | Reason |\n")
            f.write("|------|-------|--------|\n")
            for removed in reports['removed_assets']:
                filename = Path(removed['file']).name
                f.write(f"| {filename} | {removed['score']:.2f} | {removed['reason']} |\n")
        
        # Recommendations
        f.write("\n" + "=" * 80 + "\n\n")
        f.write("## Recommendations\n\n")
        f.write("1. **Standard Sizes**: Use 8x8, 16x16, 32x32, or multiples of 8 for Starbound assets\n")
        f.write("2. **Alpha Channel**: Ensure assets that need transparency have RGBA format\n")
        f.write("3. **File Size**: Keep images under 20KB for optimal performance\n")
        f.write("4. **Format**: Use PNG format for all image assets\n")
        f.write("5. **Quality Threshold**: Adjust threshold based on your needs (current: {})\n".format(quality_threshold))
    
    # Generate best assets mapping
    from datetime import datetime
    with open(mapping_path, 'w', encoding='utf-8') as f:
        f.write("# Best Assets Mapping - Starbound Asset Generator\n\n")
        f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("## Summary\n\n")
        f.write(f"Quality-based asset selection completed:\n")
        f.write(f"- **Total Assets Checked**: {len(reports['images']) + len(reports['json_files'])}\n")
        f.write(f"- **Best Assets Selected**: {len(reports['best_assets'])}\n")
        f.write(f"- **Assets Removed**: {removed_count}\n")
        f.write(f"- **Quality Threshold**: {quality_threshold}\n\n")
        f.write("---\n\n")
        
        if reports['best_assets']:
            f.write("## Selected Best Assets\n\n")
            for asset_name, info in sorted(reports['best_assets'].items()):
                f.write(f"### {asset_name}\n\n")
                f.write(f"- **File**: `{info['file']}`\n")
                f.write(f"- **Type**: {info['type']}\n")
                f.write(f"- **Quality Score**: {info['score']:.2f}/10.00\n\n")
    
    # Save JSON report
    json_report_path = assets_dir / "asset_quality_report.json"
    with open(json_report_path, 'w', encoding='utf-8') as f:
        json.dump({
            'summary': {
                'total_images': len(reports['images']),
                'total_json': len(reports['json_files']),
                'best_assets_count': len(reports['best_assets']),
                'removed_count': removed_count,
                'quality_threshold': quality_threshold
            },
            'best_assets': reports['best_assets'],
            'removed_assets': reports['removed_assets']
        }, f, indent=2)
    
    print(f"\nQuality report saved: {report_path}")
    print(f"Best assets mapping saved: {mapping_path}")
    print(f"JSON report saved: {json_report_path}")
    print(f"\nSummary:")
    print(f"  Total images: {len(reports['images'])}")
    print(f"  High quality (>= {quality_threshold}): {len([img for img in reports['images'] if img.get('score', 0) >= quality_threshold])}")
    print(f"  Best assets selected: {len(reports['best_assets'])}")
    print(f"  Assets removed: {removed_count}")
    
    return report_path

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Check quality of Starbound assets and keep only the best ones')
    parser.add_argument('assets_dir', nargs='?', type=str, 
                       default=r"F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery\assets",
                       help='Path to assets directory')
    parser.add_argument('--threshold', type=float, default=7.0,
                       help='Quality threshold (default: 7.0)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Dry run mode (do not actually remove files)')
    
    args = parser.parse_args()
    
    assets_dir = Path(args.assets_dir)
    if not assets_dir.exists():
        print(f"Error: Assets directory does not exist: {assets_dir}")
        sys.exit(1)
    
    generate_quality_report(assets_dir, args.threshold, args.dry_run)
