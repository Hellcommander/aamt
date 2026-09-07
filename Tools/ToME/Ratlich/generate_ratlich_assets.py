#!/usr/bin/env python3
"""
Generate high-quality assets for Ratlich race mod.
Focuses on paperdoll system with base sprites and equipment overlays.
"""

import sys
from pathlib import Path
import json
import shutil
from typing import Dict, List, Tuple, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from tome_asset_generator_ai import AIEnhancedToMEGenerator
from tome_asset_generator import AssetType, ShapeModule
from tome_asset_generator_logger import (
    get_logger, log_exception, log_generation_start, log_generation_end,
    log_asset_generation, log_file_operation, log_performance
)
import time

class RatlichAssetGenerator:
    """Specialized generator for Ratlich race assets."""
    
    def __init__(self, mod_path: Path, use_ai: bool = True):
        self.logger = get_logger(self.__class__.__name__)
        self.mod_path = Path(mod_path)
        self.use_ai = use_ai
        
        self.logger.info(f"Initializing RatlichAssetGenerator for mod: {mod_path}")
        self.logger.debug(f"AI enhancement: {use_ai}")
        
        # Output directory within mod
        self.output_dir = self.mod_path / "data" / "gfx"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger.debug(f"Output directory: {self.output_dir}")
        
        # Initialize generator
        try:
            self.generator = AIEnhancedToMEGenerator(
                output_dir=str(self.output_dir),
                mod_name="ratlich-race",
                mod_author="ToME Asset Generator",
                mod_version="1.0.0",
                use_ai=use_ai
            )
            self.logger.info("Generator initialized successfully")
        except Exception as e:
            log_exception(e, "generator initialization")
            raise
        
        # Asset definitions for Ratlich
        # Using existing shape modules creatively for rodent/undead appearance
        self.asset_defs = {
            # Base character sprites (front and back for paperdoll)
            'base_body_front': {
                'type': AssetType.ACTOR,
                'shapes': [ShapeModule.SPHERE, ShapeModule.CLOUD],  # Organic, rounded shapes
                'description': 'Ratlich base body (front view) - undead rodent',
                'output_path': 'actors/ratlich_body_front.png',
                'variations': 100,  # More variations for higher quality
            },
            'base_body_back': {
                'type': AssetType.ACTOR,
                'shapes': [ShapeModule.SPHERE, ShapeModule.CLOUD],
                'description': 'Ratlich base body (back view) - undead rodent',
                'output_path': 'actors/ratlich_body_back.png',
                'variations': 100,
            },
            # Equipment overlays
            'overlay_head': {
                'type': AssetType.ITEM,
                'shapes': [ShapeModule.RING, ShapeModule.SPIRAL],  # Crown/helmet-like
                'description': 'Head equipment overlay for Ratlich',
                'output_path': 'overlays/ratlich_head.png',
                'variations': 80,
            },
            'overlay_body': {
                'type': AssetType.ITEM,
                'shapes': [ShapeModule.CUBE, ShapeModule.WALL],  # Armor-like
                'description': 'Body equipment overlay for Ratlich',
                'output_path': 'overlays/ratlich_body.png',
                'variations': 80,
            },
            'overlay_hands': {
                'type': AssetType.ITEM,
                'shapes': [ShapeModule.RING, ShapeModule.SPHERE],  # Glove-like
                'description': 'Hand equipment overlay for Ratlich',
                'output_path': 'overlays/ratlich_hands.png',
                'variations': 60,
            },
            'overlay_tail_weapon': {
                'type': AssetType.ITEM,
                'shapes': [ShapeModule.BOLT, ShapeModule.BEAM],  # Weapon-like
                'description': 'Tail weapon overlay for Ratlich',
                'output_path': 'overlays/ratlich_tail_weapon.png',
                'variations': 80,
            },
            # Map display sprites (32x32, 64x64, 128x128)
            'map_32': {
                'type': AssetType.ACTOR,
                'shapes': [ShapeModule.SPHERE, ShapeModule.CLOUD],
                'description': 'Ratlich map sprite 32x32',
                'output_path': 'actors/ratlich_32.png',
                'variations': 100,
            },
            'map_64': {
                'type': AssetType.ACTOR,
                'shapes': [ShapeModule.SPHERE, ShapeModule.CLOUD],
                'description': 'Ratlich map sprite 64x64',
                'output_path': 'actors/ratlich_64.png',
                'variations': 100,
            },
            'map_128': {
                'type': AssetType.ACTOR,
                'shapes': [ShapeModule.SPHERE, ShapeModule.CLOUD],
                'description': 'Ratlich map sprite 128x128',
                'output_path': 'actors/ratlich_128.png',
                'variations': 100,
            },
            # Icon sprites for birther/character sheet
            'icon_32': {
                'type': AssetType.ACTOR,
                'shapes': [ShapeModule.SPHERE, ShapeModule.CLOUD],
                'description': 'Ratlich icon 32x32',
                'output_path': 'icons/ratlich_32.png',
                'variations': 100,
            },
            'icon_128': {
                'type': AssetType.ACTOR,
                'shapes': [ShapeModule.SPHERE, ShapeModule.CLOUD],
                'description': 'Ratlich icon 128x128',
                'output_path': 'icons/ratlich_128.png',
                'variations': 100,
            },
            # Talent icons (themed for each talent)
            'talent_cunning': {
                'type': AssetType.SPELL,
                'shapes': [ShapeModule.RING, ShapeModule.SPIRAL],  # Intelligence/cunning theme
                'description': 'Rat Lich Cunning talent icon - stat bonus',
                'output_path': 'talents/rat_lich_cunning.png',
                'talent_id': 'T_RAT_LICH_CUNNING',
                'variations': 100,  # Higher quality for talents
            },
            'talent_illusory_guise': {
                'type': AssetType.SPELL,
                'shapes': [ShapeModule.CLOUD, ShapeModule.SPIRAL],  # Illusion/mystical theme
                'description': 'Illusory Guise talent icon - disguise ability',
                'output_path': 'talents/rat_lich_illusory_guise.png',
                'talent_id': 'T_RAT_LICH_ILLUSORY_GUISE',
                'variations': 100,
            },
            'talent_equip_tail_weapon': {
                'type': AssetType.ITEM,
                'shapes': [ShapeModule.BOLT, ShapeModule.BEAM],  # Weapon/equipment theme
                'description': 'Equip Tail Weapon talent icon - tail weapon slot',
                'output_path': 'talents/rat_lich_equip_tail_weapon.png',
                'talent_id': 'T_RAT_LICH_RACE_EQUIP_TAIL_WEAPON',
                'variations': 100,
            },
            'talent_dark_feed_rush': {
                'type': AssetType.SPELL,
                'shapes': [ShapeModule.BOLT, ShapeModule.NOVA],  # Dark/attack theme
                'description': 'Dark Feed Rush talent icon - dark rush attack',
                'output_path': 'talents/rat_lich_dark_feed_rush.png',
                'talent_id': 'T_RAT_LICH_DARK_FEED_RUSH',
                'variations': 100,
            },
            'talent_summon_undead_rats': {
                'type': AssetType.SPELL,
                'shapes': [ShapeModule.CLOUD, ShapeModule.SPHERE],  # Summoning theme
                'description': 'Summon Undead Rats talent icon - summon ability',
                'output_path': 'talents/rat_lich_summon_undead_rats.png',
                'talent_id': 'T_RAT_LICH_SUMMON_UNDEAD_RATS',
                'variations': 100,
            },
        }
    
    def generate_all(self, progress_callback=None):
        """Generate all Ratlich assets."""
        start_time = time.time()
        log_generation_start("RatlichAssetGenerator", "ratlich-race", {
            "use_ai": self.use_ai,
            "total_assets": len(self.asset_defs),
            "total_variations": sum(def_['variations'] for def_ in self.asset_defs.values())
        })
        
        results = {}
        total_assets = sum(def_['variations'] for def_ in self.asset_defs.values())
        generated = 0
        
        for asset_key, asset_def in self.asset_defs.items():
            asset_start_time = time.time()
            self.logger.info(f"Generating asset: {asset_key} ({asset_def['variations']} variations)")
            
            if progress_callback:
                progress_callback(f"Generating {asset_key}...", generated, total_assets)
            
            best_asset = None
            best_score = -1
            all_assets = []
            
            for i in range(asset_def['variations']):
                seed = hash(asset_key) + i * 1000
                variant = f"{asset_key}_{i:03d}"
                
                try:
                    asset = self.generator.generate(
                        template=asset_def['type'],
                        shapes=asset_def.get('shapes', []),
                        seed=seed,
                        variant=variant,
                        name=f"Ratlich {asset_key}",
                        description=asset_def['description']
                    )
                    
                    score = asset['balance']['total_score']
                    all_assets.append((asset, score, i))
                    
                    if score > best_score:
                        best_score = score
                        best_asset = (asset, i)
                    
                    generated += 1
                    log_asset_generation(asset_key, i+1, asset_def['variations'], score)
                    
                    if progress_callback:
                        progress_callback(f"  Variation {i+1}/{asset_def['variations']} (score: {score:.2f})", generated, total_assets)
                    
                except Exception as e:
                    log_exception(e, f"generating {asset_key} variation {i+1}")
                    if progress_callback:
                        progress_callback(f"  [ERROR] Variation {i+1}: {e}", generated, total_assets)
                    continue
            
            if best_asset:
                asset, best_idx = best_asset
                self.logger.info(f"Best variation for {asset_key}: {best_idx+1} (score: {best_score:.2f})")
                
                # Copy best asset to final location
                source_sprite = self.generator.mod_path / asset['sprite']
                target_path = self.output_dir / asset_def['output_path']
                target_path.parent.mkdir(parents=True, exist_ok=True)
                
                if source_sprite.exists():
                    try:
                        shutil.copy2(source_sprite, target_path)
                        log_file_operation("copy", source_sprite, target_path)
                        
                        # Copy metadata
                        meta_source = source_sprite.with_suffix('.meta.json')
                        if meta_source.exists():
                            meta_target = target_path.with_suffix('.meta.json')
                            shutil.copy2(meta_source, meta_target)
                            log_file_operation("copy", meta_source, meta_target)
                        
                        results[asset_key] = {
                            'path': str(target_path),
                            'score': best_score,
                            'variation': best_idx
                        }
                        self.logger.info(f"Successfully copied {asset_key} to {target_path}")
                    except Exception as e:
                        log_exception(e, f"copying {asset_key}")
                        self.logger.error(f"Failed to copy {asset_key}: {e}")
                else:
                    self.logger.error(f"Source sprite not found: {source_sprite}")
            else:
                self.logger.warning(f"No valid assets generated for {asset_key}")
            
            asset_duration = time.time() - asset_start_time
            log_performance(f"generate_{asset_key}", asset_duration, {
                "variations": asset_def['variations'],
                "best_score": best_score if best_asset else None
            })
        
        total_duration = time.time() - start_time
        log_performance("generate_all", total_duration, {
            "total_assets": len(results),
            "total_variations": generated
        })
        log_generation_end("RatlichAssetGenerator", results)
        
        return results
    
    def create_paperdoll_config(self, results: Dict):
        """Create paperdoll configuration for ToME."""
        config = {
            'base_body_front': results.get('base_body_front', {}).get('path', ''),
            'base_body_back': results.get('base_body_back', {}).get('path', ''),
            'overlays': {
                'head': results.get('overlay_head', {}).get('path', ''),
                'body': results.get('overlay_body', {}).get('path', ''),
                'hands': results.get('overlay_hands', {}).get('path', ''),
                'tail_weapon': results.get('overlay_tail_weapon', {}).get('path', ''),
            },
            'map_sprites': {
                '32': results.get('map_32', {}).get('path', ''),
                '64': results.get('map_64', {}).get('path', ''),
                '128': results.get('map_128', {}).get('path', ''),
            },
            'icons': {
                '32': results.get('icon_32', {}).get('path', ''),
                '128': results.get('icon_128', {}).get('path', ''),
            },
            'talents': {
                'T_RAT_LICH_CUNNING': results.get('talent_cunning', {}).get('path', ''),
                'T_RAT_LICH_ILLUSORY_GUISE': results.get('talent_illusory_guise', {}).get('path', ''),
                'T_RAT_LICH_RACE_EQUIP_TAIL_WEAPON': results.get('talent_equip_tail_weapon', {}).get('path', ''),
                'T_RAT_LICH_DARK_FEED_RUSH': results.get('talent_dark_feed_rush', {}).get('path', ''),
                'T_RAT_LICH_SUMMON_UNDEAD_RATS': results.get('talent_summon_undead_rats', {}).get('path', ''),
            }
        }
        
        config_path = self.output_dir / 'ratlich_paperdoll_config.json'
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        
        print(f"\nPaperdoll config saved to: {config_path}")
        return config


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate Ratlich race assets')
    parser.add_argument('--mod-path', type=str, 
                       default=r"F:\SteamLibrary\steamapps\common\TalesMajEyal\game\addons\tome-ratlich-race",
                       help='Path to Ratlich race mod')
    parser.add_argument('--no-ai', action='store_true', help='Disable AI enhancement')
    
    args = parser.parse_args()
    
    mod_path = Path(args.mod_path)
    if not mod_path.exists():
        print(f"ERROR: Mod path does not exist: {mod_path}")
        return 1
    
    print("="*60)
    print("Ratlich Race Asset Generator")
    print("="*60)
    print(f"Mod path: {mod_path}")
    print(f"AI enhancement: {not args.no_ai}")
    print("="*60)
    
    generator = RatlichAssetGenerator(mod_path, use_ai=not args.no_ai)
    
    def progress(msg, current, total):
        pct = (current / total * 100) if total > 0 else 0
        print(f"\r[{pct:5.1f}%] {msg}", end='', flush=True)
    
    results = generator.generate_all(progress_callback=progress)
    
    print("\n" + "="*60)
    print("Generation complete!")
    print("="*60)
    
    # Create paperdoll config
    config = generator.create_paperdoll_config(results)
    
    print("\nGenerated assets:")
    for key, result in results.items():
        print(f"  {key}: {result.get('path', 'N/A')} (score: {result.get('score', 0):.2f})")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

