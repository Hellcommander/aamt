import re, html
from pathlib import Path
for mod in [
    Path(r"C:\Users\Arend\AppData\LocalLow\Freehold Games\CavesOfQud\Mods\Tycho's Tangent\Mutations.xml"),
    Path(r"C:\Users\Arend\AppData\LocalLow\Freehold Games\CavesOfQud\Mods\TT_ExtraBackgrounds\Mutations.xml"),
]:
    if not mod.exists():
        print("missing", mod)
        continue
    text = mod.read_text(encoding="utf-8")
    names = re.findall(r'DisplayName="([^"]+)"', text)
    print("===", mod.parent.name, "count", len(names))
    decoded = [html.unescape(n) for n in names]
    # strip &X color codes for visible length
    visible = [re.sub(r'&[A-Za-z0-9]', '', n) for n in decoded]
    for n,v in sorted(zip(decoded, visible), key=lambda t: len(t[0]), reverse=True)[:8]:
        print(f"  markup={len(n):3d} visible={len(v):2d} {v!r}  raw={n[:60]!r}")
