#!/usr/bin/env python3
"""
Update Ratlich race definition to use generated assets.
This script updates the race.lua file to reference the new paperdoll assets.
"""

import sys
from pathlib import Path
import json
import re


def update_race_file(mod_path: Path, config_path: Path):
    """Update the race definition file with new asset paths."""
    race_file = mod_path / "data" / "races" / "ratlich.lua"
    
    if not race_file.exists():
        print(f"ERROR: Race file not found: {race_file}")
        return False
    
    if not config_path.exists():
        print(f"ERROR: Config file not found: {config_path}")
        return False
    
    # Load config
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # Read race file
    with open(race_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Convert paths to relative paths from mod root
    def get_relative_path(full_path: str) -> str:
        if not full_path:
            return ""
        path = Path(full_path)
        # Find data/gfx in path
        try:
            idx = path.parts.index('data')
            return '/'.join(path.parts[idx:])
        except ValueError:
            return full_path
    
    # Update image paths
    map_32_path = get_relative_path(config['map_sprites']['32'])
    map_64_path = get_relative_path(config['map_sprites']['64'])
    map_128_path = get_relative_path(config['map_sprites']['128'])
    icon_32_path = get_relative_path(config['icons']['32'])
    icon_128_path = get_relative_path(config['icons']['128'])
    
    # Update image = "..." lines
    if map_64_path:
        content = re.sub(
            r'image\s*=\s*"[^"]*"',
            f'image = "{map_64_path}"',
            content,
            count=1
        )
    
    # Update image32 and image128
    if icon_32_path:
        content = re.sub(
            r'image32\s*=\s*"[^"]*"',
            f'image32 = "{icon_32_path}"',
            content
        )
    
    if icon_128_path:
        content = re.sub(
            r'image128\s*=\s*"[^"]*"',
            f'image128 = "{icon_128_path}"',
            content
        )
    
    # Add doll_back if we have base_body_back
    base_body_back = get_relative_path(config.get('base_body_back', ''))
    if base_body_back:
        # Find the equipdoll definition
        doll_back_pattern = r'(doll_h\s*=\s*\d+,\s*)'
        replacement = f'\\1\n    doll_back = "{base_body_back}",'
        
        if 'doll_back' not in content:
            content = re.sub(doll_back_pattern, replacement, content)
        else:
            # Update existing doll_back
            content = re.sub(
                r'doll_back\s*=\s*"[^"]*"',
                f'doll_back = "{base_body_back}"',
                content
            )
    
    # Update talent icons
    talents_config = config.get('talents', {})
    if talents_config:
        talent_file = mod_path / "data" / "races" / "ratlich_talents.lua"
        if talent_file.exists():
            with open(talent_file, 'r', encoding='utf-8') as f:
                talent_content = f.read()
            
            # Map talent IDs to their icon paths
            talent_updates = {
                'T_RAT_LICH_CUNNING': get_relative_path(talents_config.get('T_RAT_LICH_CUNNING', '')),
                'T_RAT_LICH_ILLUSORY_GUISE': get_relative_path(talents_config.get('T_RAT_LICH_ILLUSORY_GUISE', '')),
                'T_RAT_LICH_RACE_EQUIP_TAIL_WEAPON': get_relative_path(talents_config.get('T_RAT_LICH_RACE_EQUIP_TAIL_WEAPON', '')),
                'T_RAT_LICH_DARK_FEED_RUSH': get_relative_path(talents_config.get('T_RAT_LICH_DARK_FEED_RUSH', '')),
                'T_RAT_LICH_SUMMON_UNDEAD_RATS': get_relative_path(talents_config.get('T_RAT_LICH_SUMMON_UNDEAD_RATS', '')),
            }
            
            # Update each talent's image path
            for talent_id, icon_path in talent_updates.items():
                if icon_path:
                    # Find the talent block and update its image
                    pattern = rf'(id\s*=\s*"{re.escape(talent_id)}"[^}}]*?image\s*=\s*)"[^"]*"'
                    replacement = f'\\1"{icon_path}"'
                    talent_content = re.sub(pattern, replacement, talent_content, flags=re.DOTALL)
            
            # Write updated talent file
            talent_backup = talent_file.with_suffix('.lua.backup')
            if not talent_backup.exists():
                shutil.copy2(talent_file, talent_backup)
                print(f"Created talent file backup: {talent_backup}")
            
            with open(talent_file, 'w', encoding='utf-8') as f:
                f.write(talent_content)
            
            print(f"Updated talent file: {talent_file}")
    
    # Write updated file
    backup_file = race_file.with_suffix('.lua.backup')
    if not backup_file.exists():
        shutil.copy2(race_file, backup_file)
        print(f"Created backup: {backup_file}")
    
    with open(race_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Updated race file: {race_file}")
    return True


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Update Ratlich race definition with generated assets')
    parser.add_argument('--mod-path', type=str,
                       default=r"F:\SteamLibrary\steamapps\common\TalesMajEyal\game\addons\tome-ratlich-race",
                       help='Path to Ratlich race mod')
    parser.add_argument('--config', type=str,
                       default=None,
                       help='Path to paperdoll config JSON (auto-detected if not specified)')
    
    args = parser.parse_args()
    
    mod_path = Path(args.mod_path)
    if not mod_path.exists():
        print(f"ERROR: Mod path does not exist: {mod_path}")
        return 1
    
    if args.config:
        config_path = Path(args.config)
    else:
        config_path = mod_path / "data" / "gfx" / "ratlich_paperdoll_config.json"
    
    if not config_path.exists():
        print(f"ERROR: Config file not found: {config_path}")
        print("Run the asset generator first to create the config file.")
        return 1
    
    print("="*60)
    print("Updating Ratlich Race Definition")
    print("="*60)
    print(f"Mod path: {mod_path}")
    print(f"Config: {config_path}")
    print("="*60)
    
    if update_race_file(mod_path, config_path):
        print("\nUpdate complete!")
        return 0
    else:
        print("\nUpdate failed!")
        return 1


if __name__ == '__main__':
    sys.exit(main())

