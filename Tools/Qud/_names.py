import re
from pathlib import Path
p=Path(r"C:\Users\Arend\AppData\LocalLow\Freehold Games\CavesOfQud\Mods\Tycho's Tangent\Mutations.xml")
text=p.read_text(encoding="utf-8")
names=re.findall(r'DisplayName="([^"]+)"', text)
print("count", len(names))
for n in sorted(names, key=len, reverse=True)[:20]:
    print(len(n), n)
