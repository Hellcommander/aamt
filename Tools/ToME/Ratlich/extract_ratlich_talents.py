#!/usr/bin/env python3
"""Extract talent IDs and names from Ratlich race mod."""

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
    
    # Find all newTalent blocks with id and name
    pattern = r'newTalent\{[^}]*?id\s*=\s*"([^"]+)"[^}]*?name\s*=\s*"([^"]+)"'
    matches = re.finditer(pattern, content, re.DOTALL)
    
    for match in matches:
        talent_id = match.group(1)
        talent_name = match.group(2)
        
        # Avoid duplicates
        if not any(t['id'] == talent_id for t in talents):
            talents.append({
                'id': talent_id,
                'name': talent_name,
                'file': str(file_path)
            })
    
    return talents

# Mod path
mod_path = Path(r"F:\SteamLibrary\steamapps\common\TalesMajEyal\game\addons\tome-ratlich-race")
talents_file = mod_path / "data" / "races" / "ratlich_talents.lua"

all_talents = []

# Extract from talent file
if talents_file.exists():
    talents = extract_talents_from_file(talents_file)
    if talents:
        all_talents.extend(talents)
        print(f"  {talents_file.name}: {len(talents)} talents")
else:
    print(f"Talent file not found: {talents_file}")

print(f"\nTotal: {len(all_talents)} talents")
print("\nTalent List:")
for t in all_talents:
    print(f"  {t['id']}: {t['name']}")

# Save to JSON
output_file = Path(__file__).parent / "ratlich_talents.json"
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(all_talents, f, indent=2, ensure_ascii=False)

print(f"\nSaved to: {output_file}")

