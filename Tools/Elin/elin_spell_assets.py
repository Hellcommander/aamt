#!/usr/bin/env python3
"""
Elin Spell Asset Generator
Generates game-ready spell assets for Elin including icons, FX, projectiles, and buff icons.
"""

import os
import sys
import json
import argparse
from pathlib import Path

from PIL import Image, ImageEnhance

script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from elin_procedural import render_rich_icon, render_fx_frame, render_projectile_frame
from elin_quality import validate_icon, finalize_rgba

MAX_QUALITY_ATTEMPTS = 4

# ============================================================
# Argument Parsing
# ============================================================

def parse_args():
    parser = argparse.ArgumentParser(description='Generate Elin spell assets')
    parser.add_argument('--spec', required=True, help='JSON specification file')
    parser.add_argument('--output', required=True, help='Output directory')
    parser.add_argument('--name', required=True, help='Spell name (safe)')
    parser.add_argument('--icon', action='store_true', help='Generate icon')
    parser.add_argument('--fx', action='store_true', help='Generate FX animation')
    parser.add_argument('--fx-frames', type=int, default=4, help='Number of FX frames')
    parser.add_argument('--projectile', action='store_true', help='Generate projectile')
    parser.add_argument('--proj-frames', type=int, default=2, help='Number of projectile frames')
    parser.add_argument('--buff', action='store_true', help='Generate buff icon')
    
    return parser.parse_args()


# ============================================================
# Asset Generators
# ============================================================

def _render_icon_with_qa(size, spec):
    best = None
    for attempt in range(MAX_QUALITY_ATTEMPTS):
        seed = int(spec.get("seed", 0)) + attempt * 19
        img = render_rich_icon(size, spec, seed=seed)
        ok, reason = validate_icon(img)
        if ok:
            return finalize_rgba(img)
        best = img
        print(f"  [QA retry {attempt + 1}/{MAX_QUALITY_ATTEMPTS}] icon: {reason}", file=sys.stderr)
    return finalize_rgba(best)


def generate_icon(size, spec):
    """Generate a rich 32x32 spell icon."""
    return _render_icon_with_qa(size, spec)


def generate_fx_frames(size, frames, spec):
    """Generate multi-frame FX animation with layered motion."""
    return [render_fx_frame(size, i, frames, spec, seed=int(spec.get("seed", 0)) + i * 7) for i in range(frames)]


def generate_projectile_frames(size, frames, spec):
    """Generate projectile frames with shaded motifs."""
    return [
        render_projectile_frame(size, i, frames, spec, seed=int(spec.get("seed", 0)) + i * 11)
        for i in range(frames)
    ]


def generate_buff_icon(size, spec, base_icon=None):
    """Generate simplified buff icon from base or procedural fallback."""
    if base_icon:
        buff = base_icon.resize((size, size), Image.Resampling.LANCZOS)
        enhancer = ImageEnhance.Contrast(buff)
        buff = enhancer.enhance(1.5)
        return finalize_rgba(buff)
    return _render_icon_with_qa(size, spec)


# ============================================================
# Main
# ============================================================

def main():
    args = parse_args()
    
    # Load specification
    with open(args.spec, 'r', encoding='utf-8') as f:
        spec = json.load(f)
    
    # Create output directories
    icon_dir = os.path.join(args.output, 'icons')
    fx_dir = os.path.join(args.output, 'fx')
    proj_dir = os.path.join(args.output, 'projectiles')
    buff_dir = os.path.join(args.output, 'buffs')
    
    for dir_path in [icon_dir, fx_dir, proj_dir, buff_dir]:
        os.makedirs(dir_path, exist_ok=True)
    
    icon = None
    # Generate icon
    if args.icon:
        icon = generate_icon(32, spec.get('icon', spec))
        icon_path = os.path.join(icon_dir, f"{args.name}.png")
        icon.save(icon_path, 'PNG')
        print(f"Generated icon: {icon_path}")
    
    # Generate FX
    if args.fx:
        fx_spec = spec.get('fx', spec.get('icon', {}))
        fx_size = fx_spec.get('size', 32)
        fx_frames = generate_fx_frames(fx_size, args.fx_frames, fx_spec)
        
        # Create horizontal strip
        strip_width = fx_size * len(fx_frames)
        strip = Image.new('RGBA', (strip_width, fx_size), (0, 0, 0, 0))
        for i, frame in enumerate(fx_frames):
            strip.paste(frame, (i * fx_size, 0))
        
        fx_path = os.path.join(fx_dir, f"{args.name}_fx.png")
        strip.save(fx_path, 'PNG')
        print(f"Generated FX: {fx_path} ({len(fx_frames)} frames)")
    
    # Generate projectile
    if args.projectile:
        proj_spec = spec.get('projectile', spec.get('icon', {}))
        proj_frames = generate_projectile_frames(32, args.proj_frames, proj_spec)
        
        # Create horizontal strip
        strip_width = 32 * len(proj_frames)
        strip = Image.new('RGBA', (strip_width, 32), (0, 0, 0, 0))
        for i, frame in enumerate(proj_frames):
            strip.paste(frame, (i * 32, 0))
        
        proj_path = os.path.join(proj_dir, f"{args.name}_proj.png")
        strip.save(proj_path, 'PNG')
        print(f"Generated projectile: {proj_path} ({len(proj_frames)} frames)")
    
    # Generate buff icon
    if args.buff:
        buff_spec = spec.get('buff', spec.get('icon', {}))
        base_icon = icon if args.icon else None
        buff = generate_buff_icon(16, buff_spec, base_icon)
        buff_path = os.path.join(buff_dir, f"{args.name}_buff.png")
        buff.save(buff_path, 'PNG')
        print(f"Generated buff icon: {buff_path}")
    
    print("\n[OK] Elin spell asset generation complete!")


if __name__ == '__main__':
    main()
