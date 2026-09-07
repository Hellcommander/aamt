#!/usr/bin/env python3
"""
High-Quality Asset Image Generator using AI Specifications

Generates game-ready assets based on AI-generated specifications from Ollama.
Uses the Shared ollama_integration module for optimal performance.
"""

import os
import sys
import json
import argparse
import uuid
import time
from pathlib import Path

# Check for required dependencies
try:
    from PIL import Image, ImageEnhance
    PIL_AVAILABLE = True
except ImportError as e:
    PIL_AVAILABLE = False
    print("ERROR: Pillow (PIL) is required but not installed.", file=sys.stderr)
    print("  Install it with: pip install Pillow", file=sys.stderr)
    print(f"  Import error: {e}", file=sys.stderr)
    sys.exit(1)

# Add Shared directory to path
script_dir = Path(__file__).parent
shared_dir = script_dir.parent / "Shared"
sys.path.insert(0, str(shared_dir))
sys.path.insert(0, str(script_dir))

try:
    from ollama_integration import call_ollama, test_ollama_connection
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    print("  [Info] Shared ollama_integration not available, using local generation")

from elin_procedural import render_rich_icon, render_rich_texture
from elin_quality import validate_icon, validate_texture, finalize_rgba, finalize_texture

# Optional local Stable Diffusion backend (procedural fallback if unavailable).
try:
    import elin_sd
    ELIN_SD_MODULE = True
except Exception as _sd_exc:
    ELIN_SD_MODULE = False
    print(f"  [Info] elin_sd unavailable ({_sd_exc}); procedural only", file=sys.stderr)

# Shared Unity .meta writer (preferred); fall back to local generate_unity_meta_file.
try:
    _shared = Path(__file__).resolve().parent.parent / "Shared"
    if str(_shared) not in sys.path:
        sys.path.insert(0, str(_shared))
    from unity_meta import write_texture_meta as shared_write_texture_meta
    SHARED_META = True
except Exception:
    SHARED_META = False
    shared_write_texture_meta = None  # type: ignore

MAX_QUALITY_ATTEMPTS = 4

# ============================================================
# Asset Type Generators
# ============================================================

def generate_icon(size, spec, seed=0):
    """Generate a rich shaded icon from a design spec."""
    return render_rich_icon(size, spec, seed=seed)


def generate_sprite(size, spec, seed=0):
    """Generate a sprite asset (rich procedural, same pipeline as icons)."""
    return render_rich_icon(size, spec, seed=seed)


def generate_texture(size, spec, seed=0):
    """Generate a game-ready tileable texture with layered detail."""
    img = render_rich_texture(size, spec, seed=seed)
    return make_tileable(img)


def make_tileable(img):
    """Make an image tileable by blending edges."""
    width, height = img.size
    # Ensure image is RGB (not RGBA) for texture generation
    if img.mode == 'RGBA':
        # Convert to RGB, discarding alpha for textures
        rgb_img = Image.new('RGB', img.size, (255, 255, 255))
        rgb_img.paste(img, mask=img.split()[3] if img.mode == 'RGBA' else None)
        img = rgb_img
    elif img.mode != 'RGB':
        img = img.convert('RGB')
    
    # Create a copy for blending
    tiled = img.copy()
    
    # Blend horizontal edges
    blend_width = min(10, width // 10)
    if blend_width > 0:
        for x in range(blend_width):
            alpha = x / blend_width
            for y in range(height):
                left_pixel = img.getpixel((x, y))
                right_pixel = img.getpixel((width - blend_width + x, y))
                # Handle both RGB and RGBA
                num_channels = len(left_pixel)
                if num_channels == 3:
                    blended = tuple(int(left_pixel[i] * (1 - alpha) + right_pixel[i] * alpha) for i in range(3))
                else:
                    blended = tuple(int(left_pixel[i] * (1 - alpha) + right_pixel[i] * alpha) for i in range(3))
                tiled.putpixel((x, y), blended)
                tiled.putpixel((width - 1 - x, y), blended)
    
    # Blend vertical edges
    blend_height = min(10, height // 10)
    if blend_height > 0:
        for y in range(blend_height):
            alpha = y / blend_height
            for x in range(width):
                top_pixel = img.getpixel((x, y))
                bottom_pixel = img.getpixel((x, height - blend_height + y))
                # Handle both RGB and RGBA
                num_channels = len(top_pixel)
                if num_channels == 3:
                    blended = tuple(int(top_pixel[i] * (1 - alpha) + bottom_pixel[i] * alpha) for i in range(3))
                else:
                    blended = tuple(int(top_pixel[i] * (1 - alpha) + bottom_pixel[i] * alpha) for i in range(3))
                tiled.putpixel((x, y), blended)
                tiled.putpixel((x, height - 1 - y), blended)
    
    return tiled


def generate_spell_asset(size, spec, seed=0):
    """Generate a spell asset (icon, effect, etc.)."""
    return generate_icon(size, spec, seed=seed)


def _try_sd(asset_type, size, spec):
    """Attempt an SD render (validated by the same QA gate). None -> procedural."""
    if not (ELIN_SD_MODULE and elin_sd.sd_enabled()):
        return None
    seed = int(spec.get("seed", 0))
    try:
        if asset_type == "texture":
            img = elin_sd.generate_texture_sd(size, spec, seed=seed)
            if img is None:
                return None
            img = make_tileable(img)
            ok, reason = validate_texture(img)
        else:
            img = elin_sd.generate_icon_sd(size, spec, asset_type=asset_type, seed=seed)
            if img is None:
                return None
            ok, reason = validate_icon(img)
            if ok:
                img = finalize_rgba(img)
        if ok:
            print("  [SD] used local Stable Diffusion", file=sys.stderr)
            return img
        print(f"  [SD] failed QA ({reason}); procedural fallback", file=sys.stderr)
    except Exception as exc:
        print(f"  [SD] error ({exc}); procedural fallback", file=sys.stderr)
    return None


def _generate_with_quality(asset_type, size, spec):
    """Prefer local SD (if a server is up), else procedural with QA + seed retries."""
    # High-fidelity path first; transparently falls through on any problem.
    sd_img = _try_sd(asset_type, size, spec)
    if sd_img is not None:
        return sd_img

    is_texture = asset_type == "texture"
    best_img = None
    best_reason = ""

    for attempt in range(MAX_QUALITY_ATTEMPTS):
        seed = int(spec.get("seed", 0)) + attempt * 17 + hash(json.dumps(spec, sort_keys=True)) % 997
        if asset_type == "texture":
            img = generate_texture(size, spec, seed=seed)
            ok, reason = validate_texture(img)
        else:
            img = generate_icon(size, spec, seed=seed)
            ok, reason = validate_icon(img)
            if ok:
                img = finalize_rgba(img)

        if ok:
            return img

        best_img = img
        best_reason = reason
        print(f"  [QA retry {attempt + 1}/{MAX_QUALITY_ATTEMPTS}] {reason}", file=sys.stderr)

    print(f"  [QA warn] Using best attempt after retries: {best_reason}", file=sys.stderr)
    return best_img


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description='Generate asset image from specification',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python generate_asset_image.py --spec spec.json --output icon.png --type icon
  python generate_asset_image.py --spec spec.json --output texture.png --type texture --size 512

Error Codes:
  1 - Missing required dependencies (Pillow)
  2 - Invalid arguments or file paths
  3 - Image generation failed
  4 - File I/O error
        '''
    )
    parser.add_argument('--spec', required=True, help='JSON specification file path')
    parser.add_argument('--output', required=True, help='Output image path')
    parser.add_argument('--type', required=True, help='Asset type (icon, sprite, texture, spell_asset)')
    parser.add_argument('--size', type=int, help='Override size in pixels')
    parser.add_argument('--seed', type=int, default=None, help='Optional render seed')
    parser.add_argument('--sd', choices=['auto', 'on', 'off'], default=None,
                        help='Local Stable Diffusion: auto=use if server up, on=require, off=procedural')
    parser.add_argument('--sd-quality', choices=['draft', 'standard', 'high', 'ultra'], default=None,
                        help='SD sampling budget (default standard)')
    parser.add_argument('--api-url', default=None, help='Explicit SD API URL (else auto-detect)')

    args = parser.parse_args()

    # CLI overrides for the env-driven SD backend (elin_sd reads these).
    if args.sd:
        os.environ['ELIN_SD'] = args.sd
    if args.sd_quality:
        os.environ['ELIN_SD_QUALITY'] = args.sd_quality
    if args.api_url:
        os.environ['ELIN_SD_API_URL'] = args.api_url
    
    # Validate arguments
    if not args.spec:
        print("ERROR: --spec argument is required", file=sys.stderr)
        parser.print_help()
        sys.exit(2)
    
    if not args.output:
        print("ERROR: --output argument is required", file=sys.stderr)
        parser.print_help()
        sys.exit(2)
    
    # Load specification with error handling
    try:
        spec_path = Path(args.spec)
        if not spec_path.exists():
            print(f"ERROR: Specification file not found: {spec_path}", file=sys.stderr)
            print(f"  Please check the file path and try again.", file=sys.stderr)
            sys.exit(2)
        
        with open(spec_path, 'r', encoding='utf-8') as f:
            spec = json.load(f)
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to parse JSON specification file: {args.spec}", file=sys.stderr)
        print(f"  JSON error: {e}", file=sys.stderr)
        print(f"  Please check the file format and try again.", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f"ERROR: Failed to read specification file: {args.spec}", file=sys.stderr)
        print(f"  Error: {e}", file=sys.stderr)
        sys.exit(2)
    
    # Validate specification
    if not isinstance(spec, dict):
        print("ERROR: Specification must be a JSON object", file=sys.stderr)
        sys.exit(2)

    if args.seed is not None:
        spec["seed"] = args.seed
    
    # Determine size
    try:
        size = args.size if args.size else spec.get('size', 256)
        size = int(size)
        if size <= 0 or size > 8192:
            print(f"ERROR: Invalid size {size}. Size must be between 1 and 8192 pixels.", file=sys.stderr)
            sys.exit(2)
    except (ValueError, TypeError) as e:
        print(f"ERROR: Invalid size value: {size}", file=sys.stderr)
        print(f"  Error: {e}", file=sys.stderr)
        sys.exit(2)
    
    # Generate based on type
    asset_type = args.type.lower()
    try:
        if asset_type in ('icon', 'sprite', 'texture', 'spell_asset', 'spellassets'):
            img = _generate_with_quality(
                'texture' if asset_type == 'texture' else 'icon',
                size,
                spec,
            )
        else:
            print(f"WARNING: Unknown asset type '{asset_type}', using icon generator", file=sys.stderr)
            img = _generate_with_quality('icon', size, spec)
    except Exception as e:
        print(f"ERROR: Failed to generate {asset_type} asset", file=sys.stderr)
        print(f"  Size: {size}x{size}", file=sys.stderr)
        print(f"  Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(3)
    
    # Ensure output directory exists
    output_path = Path(args.output)
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"ERROR: Failed to create output directory: {output_path.parent}", file=sys.stderr)
        print(f"  Error: {e}", file=sys.stderr)
        sys.exit(4)
    
    # For Unity, ensure texture dimensions are powers of 2
    if asset_type == 'texture':
        try:
            img = ensure_power_of_2(img)
        except Exception as e:
            print(f"ERROR: Failed to process texture dimensions", file=sys.stderr)
            print(f"  Error: {e}", file=sys.stderr)
            sys.exit(3)
    
    # Save image in Unity-compatible format
    try:
        if asset_type == 'texture':
            # Save as PNG (Unity's preferred format)
            img.save(output_path, 'PNG', compress_level=6)  # Balanced compression
        else:
            img.save(output_path, 'PNG')
        # Unity .meta for all image types (sprite/gui for icons, default for textures)
        try:
            kind = "default" if asset_type == "texture" else "sprite"
            if SHARED_META and shared_write_texture_meta:
                shared_write_texture_meta(output_path, kind=kind, overwrite=False)
                print(f"[OK] Unity .meta ({kind}): {output_path}.meta")
            elif asset_type == "texture":
                generate_unity_meta_file(output_path)
        except Exception as e:
            print(f"WARNING: Failed to generate Unity .meta file: {e}", file=sys.stderr)
    except Exception as e:
        print(f"ERROR: Failed to save image to: {output_path}", file=sys.stderr)
        print(f"  Error: {e}", file=sys.stderr)
        print(f"  Check that the directory exists and you have write permissions.", file=sys.stderr)
        sys.exit(4)
    
    print(f"[OK] Generated: {output_path}")

def ensure_power_of_2(img):
    """Ensure image dimensions are powers of 2 for Unity compatibility."""
    width, height = img.size
    
    # Find next power of 2
    def next_power_of_2(n):
        return 1 << (n - 1).bit_length()
    
    new_width = next_power_of_2(width)
    new_height = next_power_of_2(height)
    
    # Only resize if needed
    if new_width != width or new_height != height:
        # Use high-quality resampling for textures
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    return img

def generate_unity_meta_file(texture_path):
    """Generate a Unity .meta file for the texture."""
    meta_path = Path(str(texture_path) + '.meta')
    
    # Generate a GUID for the texture
    texture_guid = str(uuid.uuid4()).replace('-', '')
    
    # Get file modification time
    mtime = int(time.time())
    
    # Unity texture importer meta file template
    meta_content = f"""fileFormatVersion: 2
guid: {texture_guid}
TextureImporter:
  internalIDToNameTable: []
  externalObjects: {{}}
  preprocessorSettings: {{}}
  serializedVersion: 2
  mipmaps:
    mipMapMode: 0
    enableMipMap: 1
    sRGBTexture: 1
    linearTexture: 0
    fadeOut: 0
    borderMipMap: 0
    mipMapsPreserveCoverage: 0
    alphaTestReferenceValue: 0.5
    mipMapFadeDistanceStart: 1
    mipMapFadeDistanceEnd: 3
  bumpmap:
    convertToNormalMap: 0
    externalNormalMap: 0
    heightScale: 0.25
    normalMapFilter: 0
  isReadable: 0
  streamingMipmaps: 0
  streamingMipmapsPriority: 0
  grayScaleToAlpha: 0
  generateCubemap: 6
  cubemapConvolution: 0
  seamlessCubemap: 0
  textureFormat: 1
  maxTextureSize: 2048
  textureSettings:
    serializedVersion: 2
    filterMode: 0
    aniso: 1
    mipBias: 0
    wrapU: 1
    wrapV: 1
    wrapW: 1
  nPOTScale: 0
  lightmap: 0
  compressionQuality: 50
  spriteMode: 0
  spriteExtrude: 1
  spriteMeshType: 1
  alignment: 0
  spritePivot: {{x: 0.5, y: 0.5}}
  spritePixelsToUnits: 100
  spriteBorder: {{x: 0, y: 0, z: 0, w: 0}}
  spriteGenerateFallbackPhysicsShape: 1
  alphaUsage: 1
  alphaIsTransparency: 0
  spriteTessellationDetail: -1
  textureType: 0
  textureShape: 1
  singleChannelTexture: 0
  maxTextureSizeSet: 0
  compressionQualitySet: 0
  textureCompression: 1
  crunchedCompression: 0
  textureFormatSet: 0
  platformSettings:
  - serializedVersion: 3
    buildTarget: DefaultTexturePlatform
    maxTextureSize: 2048
    resizeAlgorithm: 0
    textureFormat: -1
    textureCompression: 1
    compressionQuality: 50
    crunchedCompression: 0
    allowsAlphaSplitting: 0
    overridden: 0
    androidETC2FallbackOverride: 0
    forceMaximumCompressionQuality_BC6H_BC7: 0
  - serializedVersion: 3
    buildTarget: Standalone
    maxTextureSize: 2048
    resizeAlgorithm: 0
    textureFormat: -1
    textureCompression: 1
    compressionQuality: 50
    crunchedCompression: 0
    allowsAlphaSplitting: 0
    overridden: 0
    androidETC2FallbackOverride: 0
    forceMaximumCompressionQuality_BC6H_BC7: 0
  spriteSheet:
    serializedVersion: 2
    sprites: []
    outline: []
    physicsShape: []
  spritePackingTag: 
  pSDRemoveMatte: 0
  pSDShowRemoveMatteOption: 0
  userData: 
  assetBundleName: 
  assetBundleVariant: 
"""
    
    with open(meta_path, 'w', encoding='utf-8') as f:
        f.write(meta_content)
    
    print(f"[OK] Generated Unity .meta file: {meta_path}")

if __name__ == '__main__':
    main()
