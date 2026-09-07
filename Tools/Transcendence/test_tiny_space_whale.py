#!/usr/bin/env python3
"""
Test Space Whale Generation - Creates a simple tiny space whale
Quick test to verify all systems work with minimal variations
"""

import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime

def main():
    print("=" * 60)
    print("  Space Whale Generation Test")
    print("=" * 60)
    print()
    print("This will generate a simple tiny space whale with:")
    print("  - 3 variations per asset type (instead of 150)")
    print("  - All core systems tested")
    print("  - Quick verification (~1-2 minutes)")
    print()
    
    base_dir = Path(__file__).parent
    output_dir = base_dir / "Output" / "TestSpaceWhale"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Output directory: {output_dir}")
    print()
    
    start_time = datetime.now()
    variations = 3
    
    # Test 1: FX Assets (fastest test)
    print("[1/3] Testing FX Assets Generator (3 variations per effect)...")
    fx_script = base_dir / "space_whale_fx_variation_generator.py"
    if fx_script.exists():
        try:
            result = subprocess.run([
                sys.executable, str(fx_script),
                "space_whale_fx_registry.json", str(variations), "2"
            ], capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                print("  [OK] FX Assets test complete")
            else:
                print(f"  [ERROR] FX Assets test failed: {result.stderr[:200]}")
        except Exception as e:
            print(f"  [ERROR] FX Assets test error: {e}")
    else:
        print("  [WARNING] FX Assets script not found")
    
    # Test 2: Audio Assets
    print("[2/3] Testing Audio Assets Generator (3 variations)...")
    audio_script = base_dir / "space_whale_audio_generator.py"
    audio_registry = base_dir / "space_whale_audio_registry.json"
    if audio_script.exists() and audio_registry.exists():
        try:
            result = subprocess.run([
                sys.executable, str(audio_script),
                "--registry", str(audio_registry),
                "--output", str(output_dir / "Audio"),
                "--variations", str(variations)
            ], capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                print("  [OK] Audio Assets test complete")
            else:
                print(f"  [ERROR] Audio Assets test failed: {result.stderr[:200]}")
        except Exception as e:
            print(f"  [ERROR] Audio Assets test error: {e}")
    else:
        print("  [WARNING] Audio Assets script or registry not found")
    
    # Test 3: Textures
    print("[3/3] Testing Texture Generator...")
    texture_script = base_dir / "space_whale_texture_generator.py"
    ship_registry = base_dir / "space_whale_ship_example.json"
    visual_registry = base_dir / "space_whale_visual_language_registry.json"
    skinning_registry = base_dir / "space_whale_skinning_registry.json"
    
    if (texture_script.exists() and 
        ship_registry.exists() and 
        visual_registry.exists() and 
        skinning_registry.exists()):
        try:
            result = subprocess.run([
                sys.executable, str(texture_script),
                "--ship-registry", str(ship_registry),
                "--visual-registry", str(visual_registry),
                "--skinning-registry", str(skinning_registry),
                "--output", str(output_dir / "Textures")
            ], capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                print("  [OK] Texture Generator test complete")
            else:
                print(f"  [ERROR] Texture Generator test failed: {result.stderr[:200]}")
        except Exception as e:
            print(f"  [ERROR] Texture Generator test error: {e}")
    else:
        print("  [WARNING] Texture Generator script or registries not found")
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print()
    print("=" * 60)
    print("  Test Complete!")
    print("=" * 60)
    print()
    print(f"Duration: {duration:.1f} seconds")
    print(f"Output directory: {output_dir}")
    print()
    
    # Check what was generated
    files = list(output_dir.rglob("*"))
    files = [f for f in files if f.is_file()]
    if files:
        print(f"Generated {len(files)} files:")
        for file in files[:10]:  # Show first 10
            rel_path = file.relative_to(output_dir)
            print(f"  - {rel_path}")
        if len(files) > 10:
            print(f"  ... and {len(files) - 10} more files")
    else:
        print("No files generated")
    
    print()
    print("If all tests passed, the system is working correctly!")
    print("You can now run the full generation with 150 variations.")

if __name__ == "__main__":
    main()

