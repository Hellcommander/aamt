#!/usr/bin/env python3
"""Extract Smog Devil talent short_names and regenerate asset list JSON."""
import json
import re
from pathlib import Path

MOD = Path(r"F:\SteamLibrary\steamapps\common\TalesMajEyal\game\addons\tome-smog-devil-class")
OUT = Path(r"D:\games\Steam\steamapps\common\Transcendence\Tools\ToME\SmogDevil\smog_devil_talents.json")

talents = []
seen = set()
for path in sorted((MOD / "data" / "talents").rglob("*.lua")):
    text = path.read_text(encoding="utf-8", errors="ignore")
    # Pair short_name with following name when possible
    for m in re.finditer(
        r'short_name\s*=\s*"([^"]+)"[\s\S]*?name\s*=\s*"([^"]+)"',
        text,
    ):
        sid, name = m.group(1), m.group(2)
        if sid in seen:
            continue
        # Avoid matching name from a later talent too greedily — require short distance
        chunk = text[m.start():m.start() + 400]
        nm = re.search(r'name\s*=\s*"([^"]+)"', chunk)
        if not nm:
            continue
        name = nm.group(1)
        seen.add(sid)
        talents.append({
            "id": f"T_{sid}",
            "short_name": sid,
            "name": name,
            "file": str(path),
            "icon": f"t_{sid.lower()}.png",
        })

# Fallback: any short_name missed
for path in sorted((MOD / "data" / "talents").rglob("*.lua")):
    text = path.read_text(encoding="utf-8", errors="ignore")
    for sid in re.findall(r'short_name\s*=\s*"([^"]+)"', text):
        if sid in seen:
            continue
        seen.add(sid)
        talents.append({
            "id": f"T_{sid}",
            "short_name": sid,
            "name": sid.replace("_", " ").title(),
            "file": str(path),
            "icon": f"t_{sid.lower()}.png",
        })

talents.sort(key=lambda t: t["id"])
OUT.write_text(json.dumps(talents, indent=2), encoding="utf-8")
print(f"Wrote {len(talents)} talents to {OUT}")
for t in talents:
    print(f"  {t['id']} -> {t['icon']}")
