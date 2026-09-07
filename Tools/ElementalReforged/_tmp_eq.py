from pathlib import Path
import re

gc = Path(r"D:\User_Directories\Documents\My Games\ElementalReforged\Mods\LH_Legacy_Expansion\Data\GameCore")
for p in sorted(gc.glob("LHL_*Units.xml")):
    t = p.read_text(encoding="utf-8")
    for name, body in re.findall(r'<UnitType InternalName="([^"]+)">(.*?)</UnitType>', t, re.S):
        if not name.startswith("Generic_Sovereign_"):
            continue
        if "AutoCreateEquipment" not in body:
            continue
        eq = re.findall(r"<AutoCreateEquipment>([^<]+)", body)
        print(f"{name}: {eq}")
