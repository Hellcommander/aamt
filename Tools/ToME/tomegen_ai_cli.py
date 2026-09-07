#!/usr/bin/env python3
"""
AI-Enhanced ToME Asset Generator CLI
Uses Ollama dual-agent system for AI-powered content generation.
"""

import argparse
import sys
from pathlib import Path
from tome_asset_generator_ai import (
    AIEnhancedToMEGenerator,
    AssetType,
    ShapeModule,
    ExtendedAssetType
)


def cmd_generate(args):
    """Generate assets with AI enhancement."""
    try:
        template = AssetType(args.template)
    except ValueError:
        print(f"Error: Unknown template '{args.template}'")
        return 1
    
    shapes = []
    if args.shapes:
        for s in args.shapes.split(','):
            s = s.strip().lower()
            try:
                shapes.append(ShapeModule(s))
            except ValueError:
                print(f"Warning: Unknown shape '{s}', skipping")
    
    generator = AIEnhancedToMEGenerator(
        args.out,
        args.mod_name,
        args.mod_author,
        args.mod_version,
        args.ollama_url,
        use_ai=not args.no_ai
    )
    
    print(f"Generating {template.value} asset with AI enhancement...")
    if generator.use_ai:
        print(f"  AI Models: Code={generator.code_model}, Visual={generator.visual_model}")
    else:
        print("  AI: Disabled")
    print(f"  Template: {template.value}")
    print(f"  Shapes: {[s.value for s in shapes]}")
    print(f"  Seed: {args.seed}")
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


def cmd_generate_extended(args):
    """Generate extended asset with AI enhancement."""
    try:
        asset_type = ExtendedAssetType(args.asset_type)
    except ValueError:
        print(f"Error: Unknown asset type '{args.asset_type}'")
        return 1
    
    generator = AIEnhancedToMEGenerator(
        args.out,
        args.mod_name,
        args.mod_author,
        args.mod_version,
        args.ollama_url,
        use_ai=not args.no_ai
    )
    
    print(f"Generating {asset_type.value} asset with AI enhancement...")
    if generator.use_ai:
        print(f"  AI Models: Code={generator.code_model}, Visual={generator.visual_model}")
    else:
        print("  AI: Disabled")
    print(f"  Type: {asset_type.value}")
    print(f"  Seed: {args.seed}")
    print()
    
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
    
    # Generate mod init if needed
    if not (generator.mod_path / "init.lua").exists():
        init_path = generator.generate_mod_init()
        print(f"✓ Generated mod init: {init_path}")
    
    # Generate manifest
    manifest_path = generator.generate_extended_manifest()
    print(f"✓ Manifest: {manifest_path}")
    print()
    print("Generation complete!")
    
    return 0


def main():
    parser = argparse.ArgumentParser(
        description='AI-Enhanced ToME Asset Generator - Uses Ollama dual-agent system',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate a spell with AI-enhanced descriptions
  tomegen-ai generate --template spell --shapes ring,ink_bleed --seed 12345

  # Generate an achievement with AI description
  tomegen-ai extended --asset-type achievement --seed 12345 --category "My Category"

  # Disable AI (use fallback text)
  tomegen-ai generate --template spell --seed 12345 --no-ai
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Generate command (base assets)
    gen_parser = subparsers.add_parser('generate', help='Generate base assets with AI')
    gen_parser.add_argument('--template', required=True,
                          choices=[t.value for t in AssetType],
                          help='Asset template')
    gen_parser.add_argument('--shapes', default='',
                          help='Comma-separated shape modules')
    gen_parser.add_argument('--seed', type=int, required=True,
                          help='Seed for deterministic generation')
    gen_parser.add_argument('--variant', default='',
                          help='Optional variant identifier')
    gen_parser.add_argument('--ollama-url', default='http://localhost:11434',
                          help='Ollama API URL')
    gen_parser.add_argument('--no-ai', action='store_true',
                          help='Disable AI generation')
    gen_parser.add_argument('--out', default='./mods/tomegen_mod',
                          help='Output directory')
    gen_parser.add_argument('--mod-name', default='tomegen_mod',
                          help='Mod name')
    gen_parser.add_argument('--mod-author', default='Generated',
                          help='Mod author')
    gen_parser.add_argument('--mod-version', default='1.0.0',
                          help='Mod version')
    
    # Extended command
    ext_parser = subparsers.add_parser('extended', help='Generate extended assets with AI')
    ext_parser.add_argument('--asset-type', required=True,
                          choices=[t.value for t in ExtendedAssetType],
                          help='Extended asset type')
    ext_parser.add_argument('--seed', type=int, required=True,
                          help='Seed for deterministic generation')
    ext_parser.add_argument('--variant', default='',
                          help='Optional variant identifier')
    ext_parser.add_argument('--category', default='',
                          help='Category (for achievements, lore, etc.)')
    ext_parser.add_argument('--ollama-url', default='http://localhost:11434',
                          help='Ollama API URL')
    ext_parser.add_argument('--no-ai', action='store_true',
                          help='Disable AI generation')
    ext_parser.add_argument('--out', default='./mods/tomegen_mod',
                          help='Output directory')
    ext_parser.add_argument('--mod-name', default='tomegen_mod',
                          help='Mod name')
    ext_parser.add_argument('--mod-author', default='Generated',
                          help='Mod author')
    ext_parser.add_argument('--mod-version', default='1.0.0',
                          help='Mod version')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    if args.command == 'generate':
        return cmd_generate(args)
    elif args.command == 'extended':
        return cmd_generate_extended(args)
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())

