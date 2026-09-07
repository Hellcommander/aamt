#!/usr/bin/env python3
"""Extract talent IDs and names from smog_devil.lua files."""

import re
from pathlib import Path

def extract_talents_from_file(file_path):
    """Extract talent information from a Lua file."""
    talents = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find all newTalent blocks
    pattern = r'newTalent\{[^}]*id\s*=\s*"([^"]+)"[^}]*name\s*=\s*"([^"]+)"'
    
    matches = re.finditer(pattern, content, re.DOTALL)
    for match in matches:
        talent_id = match.group(1)
        talent_name = match.group(2)
        talents.append({
            'id': talent_id,
            'name': talent_name,
            'file': str(file_path)
        })
    
    # Also try alternative pattern
    pattern2 = r'newTalent\{[^}]*name\s*=\s*"([^"]+)"[^}]*id\s*=\s*"([^"]+)"'
    matches2 = re.finditer(pattern2, content, re.DOTALL)
    for match in matches2:
        talent_name = match.group(1)
        talent_id = match.group(2)
        # Avoid duplicates
        if not any(t['id'] == talent_id for t in talents):
            talents.append({
                'id': talent_id,
                'name': talent_name,
                'file': str(file_path)
            })
    
    return talents

# Extract from talents file
talents_file = Path(r"F:\SteamLibrary\steamapps\common\TalesMajEyal\game\addons\tome-smog-devil-class\data\talents\talents\smog_devil.lua")
prodigies_file = Path(r"F:\SteamLibrary\steamapps\common\TalesMajEyal\game\addons\tome-smog-devil-class\data\talents\prodigies\smog_devil.lua")

all_talents = []

if talents_file.exists():
    talents = extract_talents_from_file(talents_file)
    all_talents.extend(talents)
    print(f"Found {len(talents)} talents in talents file")

if prodigies_file.exists():
    prodigies = extract_talents_from_file(prodigies_file)
    all_talents.extend(prodigies)
    print(f"Found {len(prodigies)} prodigies in prodigies file")

print(f"\nTotal: {len(all_talents)} talents/prodigies")
print("\nTalent List:")
for t in all_talents:
    print(f"  {t['id']}: {t['name']}")

# Save to JSON
import json
output_file = Path(__file__).parent / "smog_devil_talents.json"
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(all_talents, f, indent=2, ensure_ascii=False)

print(f"\nSaved to: {output_file}")

