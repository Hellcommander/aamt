#!/usr/bin/env python3
"""
ToME Asset Generator CLI
Command-line interface for the Tales of Maj'Eyal asset generator.
"""

import argparse
import sys
import csv
from pathlib import Path
from tome_asset_generator import (
    ToMEAssetGenerator,
    AssetType,
    ShapeModule
)


def parse_shapes(shape_str: str) -> list:
    """Parse comma-separated shape list."""
    if not shape_str:
        return []
    shapes = []
    for s in shape_str.split(','):
        s = s.strip().lower()
        try:
            shapes.append(ShapeModule(s))
        except ValueError:
            print(f"Warning: Unknown shape '{s}', skipping")
    return shapes


def cmd_generate(args):
    """Generate a single asset."""
    try:
        template = AssetType(args.template)
    except ValueError:
        print(f"Error: Unknown template '{args.template}'")
        print(f"Valid templates: {[t.value for t in AssetType]}")
        return 1
    
    shapes = parse_shapes(args.shapes)
    
    generator = ToMEAssetGenerator(args.out, args.mod_name)
    
    print(f"Generating {template.value} asset...")
    print(f"  Template: {template.value}")
    print(f"  Shapes: {[s.value for s in shapes]}")
    print(f"  Seed: {args.seed}")
    print(f"  Output: {args.out}")
    print()
    
    asset = generator.generate(
        template=template,
        shapes=shapes,
        seed=args.seed,
        variant=args.variant or ""
    )
    
    print(f"✓ Generated asset: {asset['id']}")
    print(f"  Sprite: {asset['sprite']}")
    print(f"  Balance Score: {asset['balance']['total_score']:.2f}")
    
    # Generate manifest and preview
    manifest_path = generator.generate_manifest()
    preview_html = generator.generate_preview_html()
    
    print()
    print(f"✓ Manifest: {manifest_path}")
    print(f"✓ Preview: {preview_html}")
    print()
    print("Generation complete!")
    
    return 0


def cmd_preview(args):
    """Preview assets from manifest."""
    import json
    
    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f"Error: Manifest not found: {manifest_path}")
        return 1
    
    with open(manifest_path) as f:
        manifest = json.load(f)
    
    print(f"Mod: {manifest.get('mod_name', 'unknown')}")
    print(f"Version: {manifest.get('version', 'unknown')}")
    print(f"Assets: {len(manifest.get('assets', []))}")
    print()
    
    for asset in manifest.get('assets', []):
        print(f"  {asset['id']}")
        print(f"    Template: {asset['template']}")
        print(f"    Shapes: {', '.join(asset['shapes'])}")
        print(f"    Balance: {asset['balance_score']:.2f}")
        print(f"    Seed: {asset['seed']}")
        print()
    
    # Try to open preview HTML
    preview_path = manifest_path.parent / "preview" / "preview.html"
    if preview_path.exists():
        print(f"Preview HTML: {preview_path}")
        try:
            import webbrowser
            webbrowser.open(f"file://{preview_path.absolute()}")
        except Exception:
            pass
    
    return 0


def cmd_batch(args):
    """Generate assets from CSV file."""
    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"Error: CSV file not found: {csv_path}")
        return 1
    
    generator = ToMEAssetGenerator(args.out, args.mod_name)
    
    print(f"Batch generating from: {csv_path}")
    print(f"Output: {args.out}")
    print()
    
    count = 0
    errors = 0
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                template_str = row.get('template', '').strip()
                shapes_str = row.get('shapes', '').strip()
                seed_str = row.get('seed', '').strip()
                variant = row.get('variant', '').strip()
                
                if not template_str or not seed_str:
                    print(f"Warning: Skipping row (missing template or seed)")
                    continue
                
                try:
                    template = AssetType(template_str.lower())
                except ValueError:
                    print(f"Warning: Unknown template '{template_str}', skipping")
                    errors += 1
                    continue
                
                try:
                    seed = int(seed_str)
                except ValueError:
                    print(f"Warning: Invalid seed '{seed_str}', skipping")
                    errors += 1
                    continue
                
                shapes = parse_shapes(shapes_str)
                
                asset = generator.generate(
                    template=template,
                    shapes=shapes,
                    seed=seed,
                    variant=variant
                )
                
                count += 1
                print(f"  [{count}] {asset['id']} (balance: {asset['balance']['total_score']:.2f})")
                
            except Exception as e:
                print(f"Error processing row: {e}")
                errors += 1
                continue
    
    print()
    print(f"Generated {count} assets")
    if errors > 0:
        print(f"Errors: {errors}")
    
    # Generate manifest and preview
    manifest_path = generator.generate_manifest()
    preview_html = generator.generate_preview_html()
    
    print()
    print(f"✓ Manifest: {manifest_path}")
    print(f"✓ Preview: {preview_html}")
    print()
    print("Batch generation complete!")
    
    return 0


def main():
    parser = argparse.ArgumentParser(
        description='ToME Asset Generator - Generate mod assets for Tales of Maj\'Eyal',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate a spell with ring and ink_bleed shapes
  tomegen generate --template spell --shapes ring,ink_bleed --seed 12345 --out ./mods/tomegen_mod

  # Preview generated assets
  tomegen preview --manifest mods/tomegen_mod/manifest.json

  # Batch generate from CSV
  tomegen batch --csv seeds.csv --out ./mods/batch_mod
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Generate command
    gen_parser = subparsers.add_parser('generate', help='Generate a single asset')
    gen_parser.add_argument('--template', required=True,
                          choices=[t.value for t in AssetType],
                          help='Asset template (spell, actor, item, vfx, projectile)')
    gen_parser.add_argument('--shapes', default='',
                          help='Comma-separated shape modules (ring,ink_bleed,bolt,etc.)')
    gen_parser.add_argument('--seed', type=int, required=True,
                          help='Seed for deterministic generation')
    gen_parser.add_argument('--variant', default='',
                          help='Optional variant identifier')
    gen_parser.add_argument('--out', default='./mods/tomegen_mod',
                          help='Output directory (default: ./mods/tomegen_mod)')
    gen_parser.add_argument('--mod-name', default='tomegen_mod',
                          help='Mod name (default: tomegen_mod)')
    
    # Preview command
    preview_parser = subparsers.add_parser('preview', help='Preview assets from manifest')
    preview_parser.add_argument('--manifest', required=True,
                              help='Path to manifest.json')
    
    # Batch command
    batch_parser = subparsers.add_parser('batch', help='Generate assets from CSV file')
    batch_parser.add_argument('--csv', required=True,
                            help='CSV file with columns: template,shapes,seed,variant')
    batch_parser.add_argument('--out', default='./mods/batch_mod',
                            help='Output directory (default: ./mods/batch_mod)')
    batch_parser.add_argument('--mod-name', default='batch_mod',
                            help='Mod name (default: batch_mod)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    if args.command == 'generate':
        return cmd_generate(args)
    elif args.command == 'preview':
        return cmd_preview(args)
    elif args.command == 'batch':
        return cmd_batch(args)
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())

