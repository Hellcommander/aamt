#!/usr/bin/env python3
"""
Extended ToME Asset Generator CLI
Command-line interface for extended asset types (achievements, NPCs, zones, etc.)
"""

import argparse
import sys
from pathlib import Path
from tome_asset_generator_extended import (
    ExtendedToMEAssetGenerator,
    ExtendedAssetType
)


def cmd_generate_extended(args):
    """Generate an extended asset type."""
    try:
        asset_type = ExtendedAssetType(args.asset_type)
    except ValueError:
        print(f"Error: Unknown asset type '{args.asset_type}'")
        print(f"Valid types: {[t.value for t in ExtendedAssetType]}")
        return 1
    
    generator = ExtendedToMEAssetGenerator(
        args.out,
        args.mod_name,
        args.mod_author,
        args.mod_version
    )
    
    print(f"Generating {asset_type.value} asset...")
    print(f"  Type: {asset_type.value}")
    print(f"  Seed: {args.seed}")
    print(f"  Output: {args.out}")
    print()
    
    # Prepare kwargs from additional args
    kwargs = {}
    if args.category:
        kwargs['category'] = args.category
    
    asset = generator.generate_extended(
        asset_type=asset_type,
        seed=args.seed,
        variant=args.variant or "",
        **kwargs
    )
    
    print(f"✓ Generated asset: {asset['id']}")
    print(f"  File: {asset['file']}")
    print(f"  Name: {asset.get('name', 'N/A')}")
    
    # Generate mod init if first extended asset
    if not (generator.mod_path / "init.lua").exists():
        init_path = generator.generate_mod_init()
        print(f"✓ Generated mod init: {init_path}")
    
    # Generate manifest
    manifest_path = generator.generate_extended_manifest()
    print(f"✓ Manifest: {manifest_path}")
    print()
    print("Generation complete!")
    
    return 0


def cmd_batch_extended(args):
    """Generate multiple extended assets from CSV."""
    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"Error: CSV file not found: {csv_path}")
        return 1
    
    import csv
    
    generator = ExtendedToMEAssetGenerator(
        args.out,
        args.mod_name,
        args.mod_author,
        args.mod_version
    )
    
    print(f"Batch generating extended assets from: {csv_path}")
    print(f"Output: {args.out}")
    print()
    
    count = 0
    errors = 0
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                asset_type_str = row.get('asset_type', '').strip()
                seed_str = row.get('seed', '').strip()
                variant = row.get('variant', '').strip()
                category = row.get('category', '').strip()
                
                if not asset_type_str or not seed_str:
                    print(f"Warning: Skipping row (missing asset_type or seed)")
                    continue
                
                try:
                    asset_type = ExtendedAssetType(asset_type_str.lower())
                except ValueError:
                    print(f"Warning: Unknown asset type '{asset_type_str}', skipping")
                    errors += 1
                    continue
                
                try:
                    seed = int(seed_str)
                except ValueError:
                    print(f"Warning: Invalid seed '{seed_str}', skipping")
                    errors += 1
                    continue
                
                kwargs = {}
                if category:
                    kwargs['category'] = category
                
                asset = generator.generate_extended(
                    asset_type=asset_type,
                    seed=seed,
                    variant=variant,
                    **kwargs
                )
                
                count += 1
                print(f"  [{count}] {asset['id']} ({asset['type']})")
                
            except Exception as e:
                print(f"Error processing row: {e}")
                errors += 1
                continue
    
    print()
    print(f"Generated {count} extended assets")
    if errors > 0:
        print(f"Errors: {errors}")
    
    # Generate mod init
    init_path = generator.generate_mod_init()
    print(f"✓ Mod init: {init_path}")
    
    # Generate manifest
    manifest_path = generator.generate_extended_manifest()
    print(f"✓ Manifest: {manifest_path}")
    print()
    print("Batch generation complete!")
    
    return 0


def main():
    parser = argparse.ArgumentParser(
        description='Extended ToME Asset Generator - Generate additional asset types',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate an achievement
  tomegen-extended generate --asset-type achievement --seed 12345 --out ./mods/my_mod

  # Generate a birth race
  tomegen-extended generate --asset-type birth_race --seed 12346 --out ./mods/my_mod

  # Generate an NPC
  tomegen-extended generate --asset-type npc --seed 12347 --out ./mods/my_mod

  # Batch generate from CSV
  tomegen-extended batch --csv extended_assets.csv --out ./mods/batch_mod
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Generate command
    gen_parser = subparsers.add_parser('generate', help='Generate a single extended asset')
    gen_parser.add_argument('--asset-type', required=True,
                          choices=[t.value for t in ExtendedAssetType],
                          help='Extended asset type')
    gen_parser.add_argument('--seed', type=int, required=True,
                          help='Seed for deterministic generation')
    gen_parser.add_argument('--variant', default='',
                          help='Optional variant identifier')
    gen_parser.add_argument('--category', default='',
                          help='Category (for achievements, lore, etc.)')
    gen_parser.add_argument('--out', default='./mods/tomegen_mod',
                          help='Output directory')
    gen_parser.add_argument('--mod-name', default='tomegen_mod',
                          help='Mod name')
    gen_parser.add_argument('--mod-author', default='Generated',
                          help='Mod author')
    gen_parser.add_argument('--mod-version', default='1.0.0',
                          help='Mod version')
    
    # Batch command
    batch_parser = subparsers.add_parser('batch', help='Generate assets from CSV')
    batch_parser.add_argument('--csv', required=True,
                            help='CSV file with columns: asset_type,seed,variant,category')
    batch_parser.add_argument('--out', default='./mods/batch_mod',
                            help='Output directory')
    batch_parser.add_argument('--mod-name', default='batch_mod',
                          help='Mod name')
    batch_parser.add_argument('--mod-author', default='Generated',
                          help='Mod author')
    batch_parser.add_argument('--mod-version', default='1.0.0',
                          help='Mod version')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    if args.command == 'generate':
        return cmd_generate_extended(args)
    elif args.command == 'batch':
        return cmd_batch_extended(args)
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())

