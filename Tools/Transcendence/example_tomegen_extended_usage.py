#!/usr/bin/env python3
"""
Example usage of the Extended ToME Asset Generator
Demonstrates generating both base and extended asset types.
"""

from tome_asset_generator import (
    ToMEAssetGenerator,
    AssetType,
    ShapeModule
)
from tome_asset_generator_extended import (
    ExtendedToMEAssetGenerator,
    ExtendedAssetType
)


def main():
    print("ToME Extended Asset Generator - Example Usage")
    print("=" * 60)
    print()
    
    # Create extended generator (includes base functionality)
    generator = ExtendedToMEAssetGenerator(
        output_dir="./mods/example_extended_mod",
        mod_name="example_extended_mod",
        mod_author="ToME Asset Generator",
        mod_version="1.0.0"
    )
    
    # ============================================================
    # Generate Base Assets (Sprites, Talents, etc.)
    # ============================================================
    print("Generating Base Assets...")
    print("-" * 60)
    
    # Generate a spell
    print("1. Generating spell...")
    spell = generator.generate(
        template=AssetType.SPELL,
        shapes=[ShapeModule.RING, ShapeModule.INK_BLEED],
        seed=10001,
        variant="fire"
    )
    print(f"   ✓ {spell['id']} (balance: {spell['balance']['total_score']:.2f})")
    
    # Generate an actor
    print("2. Generating actor...")
    actor = generator.generate(
        template=AssetType.ACTOR,
        shapes=[],
        seed=10002
    )
    print(f"   ✓ {actor['id']}")
    
    # Generate a VFX effect
    print("3. Generating VFX...")
    vfx = generator.generate(
        template=AssetType.VFX,
        shapes=[ShapeModule.SPIRAL],
        seed=10003
    )
    print(f"   ✓ {vfx['id']}")
    
    print()
    
    # ============================================================
    # Generate Extended Assets
    # ============================================================
    print("Generating Extended Assets...")
    print("-" * 60)
    
    # Generate an achievement
    print("1. Generating achievement...")
    achievement = generator.generate_extended(
        asset_type=ExtendedAssetType.ACHIEVEMENT,
        seed=20001,
        category="Generated"
    )
    print(f"   ✓ {achievement['id']} - {achievement['name']}")
    
    # Generate a birth race
    print("2. Generating birth race...")
    race = generator.generate_extended(
        asset_type=ExtendedAssetType.BIRTH_RACE,
        seed=20002
    )
    print(f"   ✓ {race['id']} - {race['name']} ({race['race_type']})")
    
    # Generate a birth class
    print("3. Generating birth class...")
    birth_class = generator.generate_extended(
        asset_type=ExtendedAssetType.BIRTH_CLASS,
        seed=20003
    )
    print(f"   ✓ {birth_class['id']} - {birth_class['name']} ({birth_class['class_type']})")
    
    # Generate an NPC
    print("4. Generating NPC...")
    npc = generator.generate_extended(
        asset_type=ExtendedAssetType.NPC,
        seed=20004
    )
    print(f"   ✓ {npc['id']} - {npc['name']} (level {npc['level']})")
    
    # Generate lore
    print("5. Generating lore entry...")
    lore = generator.generate_extended(
        asset_type=ExtendedAssetType.LORE,
        seed=20005,
        category="history"
    )
    print(f"   ✓ {lore['id']} - {lore['name']} ({lore['category']})")
    
    # Generate a quest
    print("6. Generating quest...")
    quest = generator.generate_extended(
        asset_type=ExtendedAssetType.QUEST,
        seed=20006
    )
    print(f"   ✓ {quest['id']} - {quest['name']} ({quest['quest_type']})")
    
    # Generate a zone
    print("7. Generating zone...")
    zone = generator.generate_extended(
        asset_type=ExtendedAssetType.ZONE,
        seed=20007
    )
    print(f"   ✓ {zone['id']} - {zone['name']} ({zone['zone_type']})")
    
    # Generate a timed effect
    print("8. Generating timed effect...")
    effect = generator.generate_extended(
        asset_type=ExtendedAssetType.TIMED_EFFECT,
        seed=20008
    )
    print(f"   ✓ {effect['id']} - {effect['name']} ({effect['effect_type']}, {effect['duration']} turns)")
    
    print()
    
    # ============================================================
    # Generate Mod Files
    # ============================================================
    print("Generating Mod Files...")
    print("-" * 60)
    
    # Generate mod init
    init_path = generator.generate_mod_init()
    print(f"   ✓ Mod init: {init_path.name}")
    
    # Generate manifest
    manifest_path = generator.generate_extended_manifest()
    print(f"   ✓ Manifest: {manifest_path.name}")
    
    # Generate preview
    preview_path = generator.generate_preview_html()
    print(f"   ✓ Preview: {preview_path.name}")
    
    print()
    
    # ============================================================
    # Summary
    # ============================================================
    print("=" * 60)
    print("Generation Complete!")
    print("=" * 60)
    print()
    print(f"Mod location: {generator.mod_path}")
    print()
    print("Generated Assets:")
    print(f"  Base Assets: {len(generator.assets)}")
    print("    - Spells/Talents")
    print("    - Actors")
    print("    - VFX Effects")
    print()
    print("  Extended Assets: 8")
    print("    - Achievements")
    print("    - Birth Races")
    print("    - Birth Classes")
    print("    - NPCs")
    print("    - Lore Entries")
    print("    - Quests")
    print("    - Zones")
    print("    - Timed Effects")
    print()
    print("Next Steps:")
    print("  1. Review generated files in data/")
    print("  2. Customize as needed")
    print("  3. Check preview.html for visual assets")
    print("  4. Copy mod to ToME's mods/ directory")
    print("  5. Test in-game")
    print()
    
    # Check for validation warnings
    if generator.validation_warnings:
        print("Validation Warnings:")
        for warning in generator.validation_warnings:
            print(f"  ⚠ {warning}")
        print()


if __name__ == '__main__':
    main()

