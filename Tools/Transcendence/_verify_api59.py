#!/usr/bin/env python3
import os
import re
from pathlib import Path

root = Path(r"D:\games\Steam\steamapps\common\Transcendence\Extensions")
pat = re.compile(
    r"<(Transcendence(?:Extension|Adventure|Library|Module))\b([^>]*)>",
    re.I | re.S,
)
api_re = re.compile(r'apiVersion\s*=\s*["\']([^"\']+)["\']', re.I)
not59 = []
missing = []

for dp, dns, fns in os.walk(root):
    dns[:] = [d for d in dns if d.lower() not in ("tools", ".git", "node_modules", "__pycache__")]
    for fn in fns:
        if not fn.lower().endswith((".xml", ".tdb")):
            continue
        p = Path(dp) / fn
        try:
            raw = p.read_bytes()[:24576]
        except OSError:
            continue
        text = raw.decode("utf-8", "ignore")
        m = pat.search(text)
        if not m:
            continue
        am = api_re.search(m.group(2))
        rel = str(p.relative_to(root))
        if not am:
            missing.append(rel)
        elif am.group(1) != "59":
            not59.append((rel, am.group(1)))

print(f"Not apiVersion=59: {len(not59)}")
for r, v in not59:
    print(f"  {r}: api={v}")
print(f"Missing apiVersion: {len(missing)}")
for r in missing:
    print(f"  {r}")
