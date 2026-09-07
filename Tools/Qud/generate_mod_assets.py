#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Standalone Asset Generator for Caves of Qud Mods
Generates visual assets for mutations, creatures, and equipment.
"""

import sys
import argparse
from pathlib import Path

# Fix Unicode encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from mutation_asset_generator import MutationAssetGenerator
    from creature_asset_generator import CreatureAssetGenerator
    from equipment_asset_generator import EquipmentAssetGenerator
    ASSET_GENERATORS_AVAILABLE = True
except ImportError as e:
    ASSET_GENERATORS_AVAILABLE = False
    print(f"Warning: Asset generators require Pillow. Install with: pip install Pillow")
    print(f"Error: {e}")

# Try to import audio generator
try:
    import numpy as np
    import soundfile as sf
    from qud_audio_generator import QudAudioGenerator
    AUDIO_GENERATOR_AVAILABLE = True
except ImportError:
    AUDIO_GENERATOR_AVAILABLE = False

def main():
    parser = argparse.ArgumentParser(
        description="Generate visual assets for Caves of Qud mods",
        epilog="""
Examples:
  # Generate all assets for a mod
  python generate_mod_assets.py "Broodmother Mutation"
  
  # Generate only mutation assets
  python generate_mod_assets.py "Space Time Vortex" --mutations-only
  
  # Generate only creature assets
  python generate_mod_assets.py "Broodmother Mutation" --creatures-only
  
  # Generate only equipment assets
  python generate_mod_assets.py "Broodmother Mutation" --equipment-only
"""
    )
    
    parser.add_argument("mod_name", help="Name of the mod or path to mod directory")
    parser.add_argument("--mutations-only", action="store_true", help="Only generate mutation assets")
    parser.add_argument("--creatures-only", action="store_true", help="Only generate creature assets")
    parser.add_argument("--equipment-only", action="store_true", help="Only generate equipment assets")
    parser.add_argument("--audio-only", action="store_true", help="Only generate audio assets")
    parser.add_argument("--include-audio", action="store_true", help="Also generate audio assets")
    parser.add_argument("--mods-path", help="Path to mods directory (auto-detected if not specified)")
    parser.add_argument("--use-ollama", action="store_true", default=True, help="Use Ollama for AI-powered design generation (default: True)")
    parser.add_argument("--no-ollama", action="store_true", help="Disable Ollama, use procedural generation only")
    parser.add_argument("--candidates", type=int, default=3, help="Number of candidate designs to generate with Ollama (default: 3)")
    parser.add_argument("--tile-size", type=int, default=48, help="Tile size in pixels for high quality assets (default: 48, supports tile scaling mod)")
    
    args = parser.parse_args()
    
    if not ASSET_GENERATORS_AVAILABLE:
        print("ERROR: Asset generators are not available.")
        print("Please install Pillow: pip install Pillow")
        return 1
    
    # Find mod
    if args.mods_path:
        mods_path = Path(args.mods_path)
    else:
        # Default paths
        import os
        if os.name == 'nt':  # Windows
            mods_path = Path(os.path.expanduser("~")) / "AppData" / "LocalLow" / "Freehold Games" / "CavesOfQud" / "Mods"
        else:
            mods_path = Path.home() / ".config" / "unity3d" / "Freehold Games" / "CavesOfQud" / "Mods"
    
    # Find mod directory
    mod_path = None
    if Path(args.mod_name).exists():
        mod_path = Path(args.mod_name)
    else:
        # Search in mods directory
        for mod_dir in mods_path.iterdir():
            if mod_dir.is_dir() and args.mod_name.lower() in mod_dir.name.lower():
                mod_path = mod_dir
                break
    
    if not mod_path or not mod_path.exists():
        print(f"ERROR: Mod '{args.mod_name}' not found")
        print(f"  Searched in: {mods_path}")
        return 1
    
    print("=" * 60)
    print("Caves of Qud Mod Asset Generator")
    print("=" * 60)
    print(f"Mod: {mod_path.name}")
    print(f"Path: {mod_path}")
    print()
    
    results = {
        'mutations': {'icons': 0, 'visuals': 0},
        'creatures': {'tiles': 0},
        'equipment': {'tiles': 0, 'icons': 0, 'biomod_icons': 0},
        'audio': {'sounds': 0}
    }
    
    # Generate mutation assets
    if not args.creatures_only and not args.equipment_only:
        print("Generating mutation assets...")
        try:
            mutation_gen = MutationAssetGenerator(mod_path)
            mutation_results = mutation_gen.generate_all_mutation_assets()
            results['mutations'] = mutation_results
            print(f"  [OK] Created {mutation_results['icons_created']} icons, {mutation_results['visuals_created']} visuals")
        except Exception as e:
            print(f"  [FAIL] Failed: {e}")
    
    # Generate creature assets
    if not args.mutations_only and not args.equipment_only:
        print("Generating creature assets...")
        try:
            use_ollama = not args.no_ollama if hasattr(args, 'no_ollama') else True
            candidates = args.candidates if hasattr(args, 'candidates') else 3
            tile_size = args.tile_size if hasattr(args, 'tile_size') else 48
            
            creature_gen = CreatureAssetGenerator(mod_path, use_ollama=use_ollama, candidates=candidates, tile_size=tile_size)
            creature_results = creature_gen.generate_all_creature_assets()
            results['creatures'] = creature_results
            print(f"  [OK] Created {creature_results['tiles_created']} creature tiles")
        except Exception as e:
            print(f"  [FAIL] Failed: {e}")
    
    # Generate equipment assets
    if not args.mutations_only and not args.creatures_only and not args.audio_only:
        print("Generating equipment assets...")
        try:
            # Check if Ollama should be used (default: True)
            use_ollama = not args.no_ollama if hasattr(args, 'no_ollama') else True
            candidates = args.candidates if hasattr(args, 'candidates') else 3
            tile_size = args.tile_size if hasattr(args, 'tile_size') else 48
            
            equipment_gen = EquipmentAssetGenerator(mod_path, use_ollama=use_ollama, candidates=candidates, tile_size=tile_size)
            equipment_results = equipment_gen.generate_all_equipment_assets()
            results['equipment'] = equipment_results
            biomod_count = equipment_results.get('biomod_icons_created', 0)
            if biomod_count > 0:
                print(f"  [OK] Created {equipment_results['tiles_created']} tiles, {equipment_results['icons_created']} icons, {biomod_count} biomod icons")
            else:
                print(f"  [OK] Created {equipment_results['tiles_created']} tiles, {equipment_results['icons_created']} icons")
        except Exception as e:
            print(f"  [FAIL] Failed: {e}")
    
    # Generate audio assets
    if (args.audio_only or args.include_audio) and AUDIO_GENERATOR_AVAILABLE:
        print("Generating audio assets...")
        try:
            audio_gen = QudAudioGenerator()
            sounds_dir = mod_path / "Sounds"
            sounds_dir.mkdir(exist_ok=True)
            
            # Common sound types for Qud mods
            sound_types = [
                ("attack", {"creatureType": "generic", "duration": 0.3}),
                ("hit", {"material": "flesh", "duration": 0.2}),
                ("death", {"creatureType": "generic", "duration": 0.5}),
                ("spawn", {"creatureType": "generic", "duration": 0.4}),
                ("ambient", {"creatureType": "generic", "duration": 2.0}),
                ("walk", {"surface": "generic", "duration": 0.15})
            ]
            
            sounds_created = 0
            for sound_type, spec in sound_types:
                try:
                    # Generate sound
                    audio = audio_gen.generate_from_spec(spec, sound_type)
                    
                    # Convert to stereo
                    if len(audio.shape) == 1:
                        audio = np.column_stack([audio, audio])
                    
                    # Save
                    mod_name_safe = "".join(c for c in mod_path.name if c.isalnum() or c in (' ', '-', '_')).strip()
                    output_path = sounds_dir / f"{mod_name_safe}_{sound_type}.ogg"
                    sf.write(str(output_path), audio, audio_gen.sample_rate, format='OGG', subtype='VORBIS')
                    sounds_created += 1
                except Exception as e:
                    print(f"    Failed to generate {sound_type}: {e}")
            
            results['audio']['sounds'] = sounds_created
            print(f"  [OK] Created {sounds_created} sound files")
        except Exception as e:
            print(f"  [FAIL] Failed: {e}")
            print(f"    Note: Audio generation requires numpy and soundfile: pip install numpy soundfile")
    elif (args.audio_only or args.include_audio) and not AUDIO_GENERATOR_AVAILABLE:
        print("Skipping audio generation (numpy/soundfile not available)")
        print("  Install with: pip install numpy soundfile")
    
    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    total = (results['mutations'].get('icons_created', 0) + results['mutations'].get('visuals_created', 0) +
             results['creatures'].get('tiles_created', 0) +
             results['equipment'].get('tiles_created', 0) + results['equipment'].get('icons_created', 0) +
             results['equipment'].get('biomod_icons_created', 0) +
             results['audio'].get('sounds', 0))
    print(f"Total assets created: {total}")
    print()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

