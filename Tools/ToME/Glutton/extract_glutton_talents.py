#!/usr/bin/env python3
"""Extract talent IDs and names from glutton-remade mod."""

import re
import json
from pathlib import Path

def extract_talents_from_file(file_path):
    """Extract talent information from a Lua file."""
    talents = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return talents
    
    # Find all newTalent blocks - handle both id and short_name
    # Pattern 1: name = "...", short_name = "..."
    pattern1 = r'newTalent\{[^}]*?name\s*=\s*"([^"]+)"[^}]*?short_name\s*=\s*"([^"]+)"'
    matches1 = re.finditer(pattern1, content, re.DOTALL)
    for match in matches1:
        talent_name = match.group(1)
        talent_id = match.group(2)
        if not any(t['id'] == talent_id for t in talents):
            talents.append({
                'id': talent_id,
                'name': talent_name,
                'file': str(file_path)
            })
    
    # Pattern 2: short_name = "...", name = "..."
    pattern2 = r'newTalent\{[^}]*?short_name\s*=\s*"([^"]+)"[^}]*?name\s*=\s*"([^"]+)"'
    matches2 = re.finditer(pattern2, content, re.DOTALL)
    for match in matches2:
        talent_id = match.group(1)
        talent_name = match.group(2)
        if not any(t['id'] == talent_id for t in talents):
            talents.append({
                'id': talent_id,
                'name': talent_name,
                'file': str(file_path)
            })
    
    # Pattern 3: id = "..." (fallback for talents that use id instead of short_name)
    pattern3 = r'newTalent\{[^}]*?id\s*=\s*"([^"]+)"[^}]*?name\s*=\s*"([^"]+)"'
    matches3 = re.finditer(pattern3, content, re.DOTALL)
    for match in matches3:
        talent_id = match.group(1)
        talent_name = match.group(2)
        if not any(t['id'] == talent_id for t in talents):
            talents.append({
                'id': talent_id,
                'name': talent_name,
                'file': str(file_path)
            })
    
    return talents

# Mod path
mod_path = Path(r"F:\SteamLibrary\steamapps\common\TalesMajEyal\game\addons\tome-glutton-remade")
talents_dir = mod_path / "data" / "talents"

all_talents = []

# Extract from all talent files
if talents_dir.exists():
    talent_files = list(talents_dir.rglob("*.lua"))
    print(f"Found {len(talent_files)} talent files")
    
    for talent_file in talent_files:
        talents = extract_talents_from_file(talent_file)
        if talents:
            all_talents.extend(talents)
            print(f"  {talent_file.name}: {len(talents)} talents")

print(f"\nTotal: {len(all_talents)} talents")
print("\nTalent List:")
for t in all_talents[:20]:  # Show first 20
    print(f"  {t['id']}: {t['name']}")
if len(all_talents) > 20:
    print(f"  ... and {len(all_talents) - 20} more")

# Save to JSON
output_file = Path(__file__).parent / "glutton_remade_talents.json"
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(all_talents, f, indent=2, ensure_ascii=False)

print(f"\nSaved to: {output_file}")

