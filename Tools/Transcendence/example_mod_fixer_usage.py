#!/usr/bin/env python3
"""
Example usage of the Mod Fixer system.
Demonstrates common use cases and patterns.
"""

import sys
from pathlib import Path
from mod_fixer import ModFixer
from mod_fixer_prompts import PromptTemplates

# Add Tools directory to path
sys.path.insert(0, str(Path(__file__).parent))


def example_fix_missing_sprite():
    """Example: Fix missing sprite reference in ToME mod."""
    print("=" * 60)
    print("Example 1: Fix Missing Sprite")
    print("=" * 60)
    
    # Initialize fixer
    profile_path = Path(__file__).parent / 'mod_fixer_profiles' / 'tome.yaml'
    fixer = ModFixer(str(profile_path))
    
    # Generate fix using template
    templates = PromptTemplates()
    prompt = templates.fix_missing_sprite(
        game="tome",
        file_list=["data/talents/gen_talent_123.lua"],
        missing_sprite="gfx/sprites/gen_proj_123.png",
        reference_file="data/talents/gen_talent_123.lua"
    )
    
    print("Generated prompt:")
    print(prompt[:300] + "...")
    print("\nTo use this fix:")
    print("  python mod_fixer.py <mod_path> --profile tome --issue 'missing sprite...' --template fix_missing_sprite")


def example_balance_talent():
    """Example: Balance a ToME talent."""
    print("\n" + "=" * 60)
    print("Example 2: Balance Talent")
    print("=" * 60)
    
    templates = PromptTemplates()
    prompt = templates.balance_talent(
        game="tome",
        talent_file="data/talents/gen_talent_123.lua",
        current_params={
            "mana": 20,
            "cooldown": 10,
            "range": 5,
            "damage": 50
        }
    )
    
    print("Generated prompt:")
    print(prompt[:300] + "...")
    print("\nTo use this fix:")
    print("  python mod_fixer.py <mod_path> --profile tome --issue 'talent is overpowered' --template balance_talent")


def example_fix_syntax_error():
    """Example: Fix syntax error."""
    print("\n" + "=" * 60)
    print("Example 3: Fix Syntax Error")
    print("=" * 60)
    
    templates = PromptTemplates()
    prompt = templates.fix_syntax_error(
        game="tome",
        file_path="data/talents/gen_talent_123.lua",
        error_message="unexpected symbol near 'end'",
        error_line=45
    )
    
    print("Generated prompt:")
    print(prompt[:300] + "...")
    print("\nTo use this fix:")
    print("  python mod_fixer.py <mod_path> --profile tome --issue 'syntax error at line 45' --template fix_syntax_error")


def example_fix_unity_prefab():
    """Example: Fix Unity prefab reference."""
    print("\n" + "=" * 60)
    print("Example 4: Fix Unity Prefab Reference")
    print("=" * 60)
    
    templates = PromptTemplates()
    prompt = templates.fix_prefab_refs(
        game="unity_game",
        prefab_file="Assets/Prefabs/MyPrefab.prefab",
        broken_refs=[
            "Assets/Materials/MissingMaterial.mat",
            "Assets/Textures/MissingTexture.png"
        ]
    )
    
    print("Generated prompt:")
    print(prompt[:300] + "...")
    print("\nTo use this fix:")
    print("  python mod_fixer.py <mod_path> --profile unity --issue 'broken prefab refs' --template fix_prefab_refs")


def example_fix_fabric_mixin():
    """Example: Fix Minecraft Fabric mixin."""
    print("\n" + "=" * 60)
    print("Example 5: Fix Fabric Mixin")
    print("=" * 60)
    
    templates = PromptTemplates()
    prompt = templates.fix_mixin(
        game="minecraft_fabric",
        mixin_file="src/main/java/com/example/MyMixin.java",
        error_message="target class net.minecraft.class_123 not found"
    )
    
    print("Generated prompt:")
    print(prompt[:300] + "...")
    print("\nTo use this fix:")
    print("  python mod_fixer.py <mod_path> --profile minecraft_fabric --issue 'mixin error' --template fix_mixin")


def example_full_workflow():
    """Example: Full workflow with dry-run and apply."""
    print("\n" + "=" * 60)
    print("Example 6: Full Workflow")
    print("=" * 60)
    
    print("""
Full workflow example:

1. Generate fix (dry-run):
   python mod_fixer.py ./my_mod --profile tome --issue "missing sprite" --output-report report.json

2. Review the report.json and console output

3. If satisfied, apply the fix:
   python mod_fixer.py ./my_mod --profile tome --issue "missing sprite" --apply

4. Verify in-game that the fix works

5. Commit to version control if successful
    """)


if __name__ == '__main__':
    print("Mod Fixer - Example Usage Patterns")
    print("=" * 60)
    print("\nThese examples show how to use the mod fixer system.")
    print("Note: Replace <mod_path> with actual mod directory path.\n")
    
    example_fix_missing_sprite()
    example_balance_talent()
    example_fix_syntax_error()
    example_fix_unity_prefab()
    example_fix_fabric_mixin()
    example_full_workflow()
    
    print("\n" + "=" * 60)
    print("For more information, see MOD_FIXER_README.md")
    print("=" * 60)

