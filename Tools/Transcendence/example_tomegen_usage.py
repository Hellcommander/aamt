#!/usr/bin/env python3
"""
Example usage of the ToME Asset Generator
Demonstrates programmatic API usage.
"""

from tome_asset_generator import (
    ToMEAssetGenerator,
    AssetType,
    ShapeModule
)

def main():
    # Create generator
    generator = ToMEAssetGenerator(
        output_dir="./mods/example_mod",
        mod_name="example_mod"
    )
    
    print("ToME Asset Generator - Example Usage")
    print("=" * 60)
    print()
    
    # Generate a spell with ring and ink_bleed shapes
    print("Generating spell asset...")
    spell_asset = generator.generate(
        template=AssetType.SPELL,
        shapes=[ShapeModule.RING, ShapeModule.INK_BLEED],
        seed=12345,
        variant="fire"
    )
    print(f"  ✓ Generated: {spell_asset['id']}")
    print(f"    Balance Score: {spell_asset['balance']['total_score']:.2f}")
    print()
    
    # Generate an actor
    print("Generating actor asset...")
    actor_asset = generator.generate(
        template=AssetType.ACTOR,
        shapes=[],
        seed=12346
    )
    print(f"  ✓ Generated: {actor_asset['id']}")
    print()
    
    # Generate a VFX effect
    print("Generating VFX asset...")
    vfx_asset = generator.generate(
        template=AssetType.VFX,
        shapes=[ShapeModule.SPIRAL],
        seed=12347
    )
    print(f"  ✓ Generated: {vfx_asset['id']}")
    print()
    
    # Check for validation warnings
    if generator.validation_warnings:
        print("Validation Warnings:")
        for warning in generator.validation_warnings:
            print(f"  ⚠ {warning}")
        print()
    
    # Generate manifest and preview
    print("Generating manifest and preview...")
    manifest_path = generator.generate_manifest()
    preview_path = generator.generate_preview_html()
    
    print(f"  ✓ Manifest: {manifest_path}")
    print(f"  ✓ Preview: {preview_path}")
    print()
    
    print("=" * 60)
    print("Example generation complete!")
    print(f"Mod location: {generator.mod_path}")
    print()
    print("Next steps:")
    print("  1. Review preview.html in the preview/ directory")
    print("  2. Check generated assets in data/")
    print("  3. Copy mod to ToME's mods/ directory")
    print("  4. Test in-game")

if __name__ == '__main__':
    main()

