# One-shot generator: thematic StartingGear tables + TTStartingKitMaps from existing kits.
# Run from anywhere: python gen_tt_starting_kit_maps.py

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

MODS = Path(r"C:\Users\Arend\AppData\LocalLow\Freehold Games\CavesOfQud\Mods")
TT = MODS / "Tycho's Tangent"
EXTRA = MODS / "TT_ExtraBackgrounds"

# WornOn="Body" (torso) armor / clothes.
BODY = {
    "Cloth Robe",
    "Woven Tunic",
    "Vine-Weave Tunic",
    "Leather Armor",
    "Studded Leather Armor",
    "Cultist Robe",
    "Chain Mail",
    "Ring Mail",
    "Suntan Tunic",
    "Feather Kilt",
    "Wool Kilt",
    "Seeker Robes",
    "Seeker Exalted Robes",
    "Slate Frock",
    "Umber Frock",
    "Filthy Toga",
    "Crude Toga",
    "Leather Apron",
    "Cloth Overalls",
    "Furs",
    "Pocketed Vest",
    "Leafy Vest",
    "Puma Chitin Vest",
    "Flexivest",
    "Nanoweave Vest",
    "Recycling Suit",
    "Ash-Stained Robes",
    "Black Robes",
    "Bark Armor",
    "Sooty Smock",
    "Patchwork Coat",
    "Elastyne Skin Suit",
    "Rubber Suit",
    "Plastifer Jerkin",
    "Plastifer Chem Vest",
    "Steel Plate Mail",
    "Carbide Plate Armor",
    "Slate Mantle",
    "Fullerite Plate Mail",
    "Fullerite Flake Armor",
    "Crysteel Shardmail",
    "Flawless Crysteel Shardmail",
    "Thermo Cask",
    "High-Energy Thermo Cask",
    "Zetachrome Lune",
    "Chrome Womb",
    "Carapace",
    "Quills",
    "TauChime",
}
BACK = {
    "Worn Burnoose",
    "Quilted Shawl",
    "Panther's Cloak",
    "Scarlet Shawl",
    "Praetorian's Cloak",
    "Albino Monkey Braid",
    "Leather Cloak",
    "Issachari Banner",
    "Ape Fur Cloak",
    "Ogre Fur Cloak",
    "Nylon Bodypack",
    "Grassy Yurtmat",
    "Molly Netting",
    "Ironweave Cloak",
    "Chrome Mantle",
    "Rainboweave Cloak",
    "Portable Beehive",
    "Gyrocopter Backpack",
    "Helping Hands",
    "Banner of the Holy Rhombus",
    "Strength Exo",
    "Psiamp Backpack",
    "Skybear Jetpack",
    "SkybearJetpack",
    "Scrap Cape",
    "ScrapCape",
    "Nacham's Ribbon",
    "Sail from the Great Machine",
    "Camel Bladder",
    "Gas Tumbler",
    "Mechanical Wings",
}
HEAD = {
    "Leather Cap",
    "Frowning Moon Mask",
    "Carnival Mask",
    "Wide-brimmed Hat",
    "Issachari Sun Veil",
    "Crimson Hood",
    "Gas Mask",
    "Goggles",
    "Headlamp",
    "Telescopic Monocle",
    "Smiling Sun Mask",
    "Sun and Moon Mask",
    "Vinewood Sap Mask",
    "Witchwood Wreath",
}
HANDS = {
    "Steel Gauntlets",
    "Leather Gloves",
}
FEET = {
    "Sandals",
    "Leather Boots",
    "Leather Moccasins",
    "Magnetized Boots",
}
LIGHT = {
    "Torch",
    "Guiding Starcandle",
    "Headlamp",
    "Floating Glowsphere",
    "Symbiotic Firefly",
    "Luminous Mote",
    "Quantum Mote",
}
FLOATING = {
    "Floating Glowsphere",
    "Symbiotic Firefly",
    "Luminous Mote",
    "Quantum Mote",
    "Light-Obfuscating Lens",
    "Point-Defense Drone",
    "Cyclopean Prism",
    "Hoversled",
}
WATER = {
    "Waterskin",
    "HalfFullWaterskin",
    "EmptyWaterskin",
    "Canteen",
    "HalfFullCanteen",
    "EmptyCanteen",
    "PilgrimWineWaterskin",
    "ApostleHoneyWaterskin",
    "WineWaterskin",
    "HoneyWaterskin",
}
MELEE = {
    "Dagger",
    "Steel Dagger",
    "Cudgel",
    "Club",
    "Staff",
    "Amber-Tipped Staff",
    "Short Sword",
    "Long Sword",
    "Long Sword2",
    "Steel Long Sword",
    "Battle Axe",
    "Steel Battle Axe",
    "Steel Hand Axe",
    "Spear",
    "Mace",
    "Quarterstaff",
    "Stun Rod",
    "Iron Sickle",
    "Claymore Sword",
    "Pitchfork",
    "Iron Vinereaper",
    "Steel Vinereaper",
    "Pickaxe",
    "Nanopneumatic Jackhammer",
    "Reaper's Claw",
    "Desert Kris",
    "Obsidian Kris",
    "Opal-Pommeled Steel Axe",
    "Leather Whip",
    "Steel Butcher Knife",
    "Steel Utility Knife",
    "Steel Potter's Knife",
    "Steel Hammer",
    "Walking Stick",
    "Wrench",
    "Pestle",
}
RANGED = {
    "Short Bow",
    "Compound Bow",
    "Borderlands Revolver",
    "Desert Rifle",
    "Musket",
    "Semi-Automatic Pistol",
    "Carbine",
    "Laser Pistol",
}
AMMO = {
    "Wooden Arrow",
    "Lead Slug",
}
SHIELD = {
    "Bronze Shield",
    "Iron Buckler",
    "Steel Shield",
    "Rootshield",
}
TOOL = {
    "Basic Toolkit",
    "Advanced Toolkit",
}
FOOD = {
    "Vinewafer",
    "Vinewafer Sheaf",
    "Starapple",
    "Starapple Preserves",
    "Plump Mushroom",
    "Smoldered Mushroom",
    "Dried Lah Petals",
    "Bittergrette",
    "Boomrose",
    "Food Cube",
    "Ekuemekiyyen Greens",
    "Crusty Loaf",
    "Canned Have-It-All",
    "Bear Jerky",
    "Beetle Jerky",
    "Goat Jerky",
    "Salthopper Chip",
}
MEDICINE = {
    "Bandage",
    "SalveTonic",
    "Witchwood Bark",
    "Lover's Blossom",
}
BOOK = {
    "Book",
    "Across3",
    "Canticles3",
    "Ink Phial",
}
TRADE = {
    "Albino Ape Pelt",
    "Moonkoi Scales",
    "Scrap 1",
    "RandomFactionDeed",
    "Farmers Token",
    "Merchant's Token",
    "Ink Phial",
}
CELL = {
    "Chem Cell",
    "Solar Cell",
    "Nuclear Cell",
    "Fidget Cell",
    "Lead-Acid Cell",
}

GENERIC_FROM = {
    "body": [
        "Cloth Robe",
        "Woven Tunic",
        "Vine-Weave Tunic",
        "Leather Armor",
        "Studded Leather Armor",
        "Filthy Toga",
        "Crude Toga",
        "Chain Mail",
        "Ring Mail",
        "Furs",
        "Pocketed Vest",
        "Leafy Vest",
        "Recycling Suit",
        "Ash-Stained Robes",
        "Black Robes",
        "Leather Apron",
        "Cloth Overalls",
        "Bark Armor",
        "Sooty Smock",
        "Slate Frock",
        "Umber Frock",
        "Patchwork Coat",
        "Elastyne Skin Suit",
        "Rubber Suit",
        "Plastifer Jerkin",
        "Plastifer Chem Vest",
        "Puma Chitin Vest",
        "Flexivest",
        "Nanoweave Vest",
        "Steel Plate Mail",
        "Carbide Plate Armor",
        "Slate Mantle",
        "Wool Kilt",
    ],
    "back": [
        "Panther's Cloak",
        "Scarlet Shawl",
        "Praetorian's Cloak",
        "Albino Monkey Braid",
        "Leather Cloak",
        "Issachari Banner",
        "Ape Fur Cloak",
        "Ogre Fur Cloak",
        "Nylon Bodypack",
        "Grassy Yurtmat",
        "Molly Netting",
        "Ironweave Cloak",
        "Chrome Mantle",
        "Rainboweave Cloak",
        "Portable Beehive",
        "Gyrocopter Backpack",
        "Helping Hands",
        "Banner of the Holy Rhombus",
        "Strength Exo",
        "Psiamp Backpack",
        "SkybearJetpack",
        "ScrapCape",
        "Nacham's Ribbon",
        "Sail from the Great Machine",
        "Camel Bladder",
        "Gas Tumbler",
        "Mechanical Wings",
        "Quilted Shawl",
        "Worn Burnoose",
    ],
    "head": [
        "Leather Cap",
        "Crimson Hood",
        "Gas Mask",
        "Goggles",
        "Headlamp",
        "Telescopic Monocle",
        "Smiling Sun Mask",
        "Sun and Moon Mask",
        "Frowning Moon Mask",
        "Vinewood Sap Mask",
        "Wide-brimmed Hat",
        "Witchwood Wreath",
    ],
    "hands": ["Steel Gauntlets", "Leather Gloves"],
    "feet": ["Sandals", "Leather Boots", "Leather Moccasins", "Magnetized Boots"],
    "light": ["Torch", "Headlamp"],
    "floating": [
        "Floating Glowsphere",
        "Symbiotic Firefly",
        "Luminous Mote",
        "Light-Obfuscating Lens",
        "Point-Defense Drone",
        "Cyclopean Prism",
        "Hoversled",
        "Quantum Mote",
    ],
    "water": [
        "Waterskin",
        "EmptyWaterskin",
        "HalfFullWaterskin",
        "Canteen",
        "EmptyCanteen",
        "HalfFullCanteen",
        "PilgrimWineWaterskin",
        "ApostleHoneyWaterskin",
        "WineWaterskin",
        "HoneyWaterskin",
    ],
    "melee": [
        "Dagger",
        "Steel Dagger",
        "Cudgel",
        "Club",
        "Staff",
        "Amber-Tipped Staff",
        "Short Sword",
        "Long Sword",
        "Long Sword2",
        "Steel Long Sword",
        "Battle Axe",
        "Steel Battle Axe",
        "Steel Hand Axe",
        "Spear",
        "Mace",
        "Quarterstaff",
        "Stun Rod",
        "Walking Stick",
        "Desert Kris",
        "Obsidian Kris",
        "Opal-Pommeled Steel Axe",
        "Iron Vinereaper",
        "Steel Vinereaper",
        "Steel Butcher Knife",
        "Steel Potter's Knife",
        "Steel Hammer",
        "Steel Utility Knife",
        "Pestle",
        "Wrench",
        "Nanopneumatic Jackhammer",
        "Pitchfork",
        "Pickaxe",
        "Iron Sickle",
    ],
    "ranged": [
        "Short Bow",
        "Compound Bow",
        "Borderlands Revolver",
        "Desert Rifle",
        "Musket",
        "Semi-Automatic Pistol",
        "Carbine",
        "Laser Pistol",
    ],
    "ammo": [
        "Wooden Arrow",
        "Lead Slug",
    ],
    "shield": ["Bronze Shield", "Iron Buckler", "Steel Shield"],
    "tool": ["Basic Toolkit", "Advanced Toolkit"],
    "food": [
        "Ekuemekiyyen Greens",
        "Crusty Loaf",
        "Smoldered Mushroom",
        "Canned Have-It-All",
        "Bear Jerky",
        "Beetle Jerky",
        "Goat Jerky",
        "Food Cube",
        "Vinewafer Sheaf",
        "Vinewafer",
        "Salthopper Chip",
        "Starapple",
        "Plump Mushroom",
        "Dried Lah Petals",
    ],
    "medicine": [
        "Bandage",
        "SalveTonic",
        "Witchwood Bark",
    ],
    "book": [
        "Book",
        "Ink Phial",
    ],
    "trade": [
        "Farmers Token",
        "Merchant's Token",
        "Scrap 1",
        "Ink Phial",
    ],
    "cell": [
        "Chem Cell",
        "Solar Cell",
        "Lead-Acid Cell",
        "Fidget Cell",
        "Nuclear Cell",
    ],
}

SLOT_SETS = {
    "body": BODY,
    "back": BACK,
    "head": HEAD,
    "hands": HANDS,
    "feet": FEET,
    "light": LIGHT,
    "floating": FLOATING,
    "water": WATER,
    "melee": MELEE,
    "ranged": RANGED,
    "ammo": AMMO,
    "shield": SHIELD,
    "tool": TOOL,
    "food": FOOD,
    "medicine": MEDICINE,
    "book": BOOK,
    "trade": TRADE,
    "cell": CELL,
}

# Prefer these To values when several items of a slot appear in one kit.
SLOT_PREFERENCE = {
    "body": [
        "Chrome Womb",
        "Zetachrome Lune",
        "Flawless Crysteel Shardmail",
        "Crysteel Shardmail",
        "High-Energy Thermo Cask",
        "Thermo Cask",
        "Fullerite Flake Armor",
        "Fullerite Plate Mail",
        "Carbide Plate Armor",
        "Steel Plate Mail",
        "Seeker Robes",
        "Seeker Exalted Robes",
        "Cultist Robe",
        "Chain Mail",
        "Ring Mail",
        "Studded Leather Armor",
        "Leather Armor",
        "Bark Armor",
        "Suntan Tunic",
        "Feather Kilt",
        "Wool Kilt",
        "Vine-Weave Tunic",
        "Slate Frock",
        "Umber Frock",
        "Slate Mantle",
        "Leather Apron",
        "Cloth Overalls",
        "Recycling Suit",
        "Elastyne Skin Suit",
        "Rubber Suit",
        "Plastifer Chem Vest",
        "Plastifer Jerkin",
        "Nanoweave Vest",
        "Flexivest",
        "Puma Chitin Vest",
        "Leafy Vest",
        "Ash-Stained Robes",
        "Black Robes",
        "Patchwork Coat",
        "Sooty Smock",
        "Pocketed Vest",
        "Furs",
        "Filthy Toga",
        "Crude Toga",
        "Woven Tunic",
        "Cloth Robe",
        "Carapace",
        "Quills",
        "TauChime",
    ],
    "back": [
        "Chrome Mantle",
        "Ironweave Cloak",
        "Praetorian's Cloak",
        "Panther's Cloak",
        "Issachari Banner",
        "Ape Fur Cloak",
        "Ogre Fur Cloak",
        "Scarlet Shawl",
        "Rainboweave Cloak",
        "Worn Burnoose",
        "Quilted Shawl",
        "Albino Monkey Braid",
        "Molly Netting",
        "Nylon Bodypack",
        "Grassy Yurtmat",
        "Portable Beehive",
        "Banner of the Holy Rhombus",
        "Helping Hands",
        "Gyrocopter Backpack",
        "Psiamp Backpack",
        "SkybearJetpack",
        "ScrapCape",
        "Nacham's Ribbon",
        "Sail from the Great Machine",
        "Camel Bladder",
        "Gas Tumbler",
        "Mechanical Wings",
        "Leather Cloak",
        "Strength Exo",
    ],
    "head": [
        "Issachari Sun Veil",
        "Frowning Moon Mask",
        "Carnival Mask",
        "Sun and Moon Mask",
        "Smiling Sun Mask",
        "Vinewood Sap Mask",
        "Wide-brimmed Hat",
        "Crimson Hood",
        "Gas Mask",
        "Goggles",
        "Telescopic Monocle",
        "Witchwood Wreath",
        "Headlamp",
        "Leather Cap",
    ],
    "hands": ["Steel Gauntlets", "Leather Gloves"],
    "feet": ["Magnetized Boots", "Leather Boots", "Sandals", "Leather Moccasins"],
    "light": [
        "Quantum Mote",
        "Floating Glowsphere",
        "Symbiotic Firefly",
        "Luminous Mote",
        "Guiding Starcandle",
        "Headlamp",
        "Torch",
    ],
    "floating": [
        "Quantum Mote",
        "Point-Defense Drone",
        "Cyclopean Prism",
        "Floating Glowsphere",
        "Symbiotic Firefly",
        "Light-Obfuscating Lens",
        "Luminous Mote",
        "Hoversled",
    ],
    "water": [
        "HalfFullWaterskin",
        "Waterskin",
        "HalfFullCanteen",
        "Canteen",
        "PilgrimWineWaterskin",
        "ApostleHoneyWaterskin",
        "WineWaterskin",
        "HoneyWaterskin",
        "EmptyWaterskin",
        "EmptyCanteen",
    ],
    "melee": [
        "Claymore Sword",
        "Reaper's Claw",
        "Desert Kris",
        "Obsidian Kris",
        "Opal-Pommeled Steel Axe",
        "Leather Whip",
        "Steel Butcher Knife",
        "Steel Utility Knife",
        "Steel Potter's Knife",
        "Iron Sickle",
        "Iron Vinereaper",
        "Steel Vinereaper",
        "Pitchfork",
        "Pickaxe",
        "Nanopneumatic Jackhammer",
        "Amber-Tipped Staff",
        "Walking Stick",
        "Stun Rod",
        "Wrench",
        "Pestle",
        "Steel Hammer",
        "Steel Battle Axe",
        "Steel Hand Axe",
        "Battle Axe",
        "Steel Long Sword",
        "Long Sword2",
        "Long Sword",
        "Short Sword",
        "Spear",
        "Mace",
        "Quarterstaff",
        "Staff",
        "Club",
        "Cudgel",
        "Steel Dagger",
        "Dagger",
    ],
    "ranged": [
        "Desert Rifle",
        "Carbine",
        "Laser Pistol",
        "Semi-Automatic Pistol",
        "Musket",
        "Borderlands Revolver",
        "Compound Bow",
        "Short Bow",
    ],
    "ammo": [
        "Lead Slug",
        "Wooden Arrow",
    ],
    "shield": ["Steel Shield", "Rootshield", "Bronze Shield", "Iron Buckler"],
    "tool": ["Advanced Toolkit", "Basic Toolkit"],
    "food": [
        "Boomrose",
        "Starapple Preserves",
        "Dried Lah Petals",
        "Bittergrette",
        "Starapple",
        "Vinewafer",
        "Vinewafer Sheaf",
        "Plump Mushroom",
        "Smoldered Mushroom",
        "Food Cube",
        "Ekuemekiyyen Greens",
        "Crusty Loaf",
        "Canned Have-It-All",
        "Bear Jerky",
        "Beetle Jerky",
        "Goat Jerky",
        "Salthopper Chip",
    ],
    "medicine": [
        "Lover's Blossom",
        "Witchwood Bark",
        "Bandage",
        "SalveTonic",
    ],
    "book": [
        "Across3",
        "Canticles3",
        "Book",
        "Ink Phial",
    ],
    "trade": [
        "Albino Ape Pelt",
        "Moonkoi Scales",
        "RandomFactionDeed",
        "Scrap 1",
        "Merchant's Token",
        "Farmers Token",
        "Ink Phial",
    ],
    "cell": [
        "Nuclear Cell",
        "Solar Cell",
        "Chem Cell",
        "Fidget Cell",
        "Lead-Acid Cell",
    ],
}


def local_name(tag: str) -> str:
    if tag is None:
        return ""
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def collect_blueprints(el: ET.Element) -> list[str]:
    found: list[str] = []
    for child in el.iter():
        if local_name(child.tag).lower() != "object":
            continue
        bp = child.attrib.get("Blueprint") or child.attrib.get("blueprint")
        if bp:
            found.append(bp)
    return found


def parse_kits(path: Path) -> dict[str, list[str]]:
    tree = ET.parse(path)
    root = tree.getroot()
    kits: dict[str, list[str]] = {}
    for pop in root:
        if local_name(pop.tag).lower() != "population":
            continue
        name = pop.attrib.get("Name") or pop.attrib.get("name") or ""
        if not name.startswith("StartingGear_"):
            continue
        if name.endswith("_Thematic") or name == "StartingGear_Common":
            continue
        bg = name[len("StartingGear_") :]
        kits[bg] = collect_blueprints(pop)
    return kits


def pick_to(slot: str, items: list[str]) -> str | None:
    present = [i for i in items if i in SLOT_SETS[slot]]
    if not present:
        return None
    for pref in SLOT_PREFERENCE.get(slot, []):
        if pref in present:
            return pref
    return present[0]


def swaps_for(items: list[str]) -> list[tuple[str, str]]:
    swaps: list[tuple[str, str]] = []
    for slot, froms in GENERIC_FROM.items():
        to = pick_to(slot, items)
        if not to:
            continue
        # Skip identity Torch→Torch (would wipe the Common torch pile for no gain).
        # Unique lights (Guiding Starcandle) still strip Torch / Headlamp.
        if slot == "light" and to == "Torch":
            continue
        if slot == "water" and to in ("Waterskin", "EmptyWaterskin"):
            # Still map calling waterskins onto the kit waterskin.
            pass
        mapped_froms = list(froms)
        if to not in mapped_froms:
            mapped_froms.append(to)
        # Unique order, keep GENERIC_FROM order then To.
        seen = []
        for name in mapped_froms:
            if name not in seen:
                seen.append(name)
        swaps.append((",".join(seen), to))
    return swaps


def xml_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def write_maps(path: Path, kits: dict[str, list[str]], title: str) -> None:
    lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        "<!--",
        f"  {title}",
        "  From→To replacements for Thematic Swap. Calling-gear blueprints in From are",
        "  stripped; To is granted by StartingGear_<id>_Thematic (which includes the extras",
        "  table). Torch is only stripped when the kit grants a distinct light (e.g. Guiding",
        "  Starcandle); identity Torch→Torch is never mapped.",
        "-->",
        '<TTStartingKitMaps Encoding="utf-8">',
        "",
    ]
    for bg in sorted(kits):
        items = kits[bg]
        table = f"StartingGear_{bg}_Thematic"
        lines.append(f'  <map Background="{xml_escape(bg)}" ThematicGearTable="{xml_escape(table)}">')
        swaps = swaps_for(items)
        if not swaps:
            lines.append("    <!-- extras have no overlapping generic slots; unique kit items are added on top -->")
        for frm, to in swaps:
            lines.append(f'    <swap From="{xml_escape(frm)}" To="{xml_escape(to)}" />')
        lines.append("  </map>")
        lines.append("")
    lines.append("</TTStartingKitMaps>")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_thematic(path: Path, kits: dict[str, list[str]], title: str) -> None:
    lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        "<!--",
        f"  {title}",
        "  Swap kits wrap the extras table only (no torch/waterskin fillers).",
        "  Do not include StartingGear_Common here.",
        "-->",
        '<populations Encoding="utf-8">',
        "",
    ]
    for bg in sorted(kits):
        items = kits[bg]
        extras = f"StartingGear_{bg}"
        name = f"{extras}_Thematic"
        lines.append(f'  <population Name="{xml_escape(name)}">')
        lines.append(f'    <group Name="{xml_escape(name)}_Main" Style="pickeach">')
        lines.append(f'      <table Name="{xml_escape(extras)}" />')
        lines.append("    </group>")
        lines.append("  </population>")
        lines.append("")
    lines.append("</populations>")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def patch_backgrounds(path: Path, kits: dict[str, list[str]]) -> None:
    text = path.read_text(encoding="utf-8")
    for bg in kits:
        table = f"StartingGear_{bg}_Thematic"
        # Insert ThematicGearTable after GearTable="StartingGear_<id>" if missing.
        pattern = rf'(<background\b[^>]*\bId="{re.escape(bg)}"[^>]*)>'

        def repl(m: re.Match[str], table=table, bg=bg) -> str:
            open_tag = m.group(1)
            if "ThematicGearTable=" in open_tag:
                return m.group(0)
            gear = f'GearTable="StartingGear_{bg}"'
            if gear in open_tag:
                open_tag = open_tag.replace(gear, f'{gear} ThematicGearTable="{table}"', 1)
            else:
                open_tag = open_tag + f' ThematicGearTable="{table}"'
            return open_tag + ">"

        text = re.sub(pattern, repl, text, count=1, flags=re.IGNORECASE)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    tt_kits = parse_kits(TT / "PopulationTables.xml")
    extra_kits = parse_kits(EXTRA / "PopulationTables.xml")
    if len(tt_kits) != 13:
        raise SystemExit(f"expected 13 TT kits, got {len(tt_kits)}: {sorted(tt_kits)}")
    if len(extra_kits) != 70:
        raise SystemExit(f"expected 70 extra kits, got {len(extra_kits)}: {sorted(extra_kits)}")

    write_maps(TT / "TTStartingKitMaps.xml", tt_kits, "Tycho's Tangent - starting-kit maps for the 13 original backgrounds.")
    write_thematic(TT / "StartingGearThematic.xml", tt_kits, "Tycho's Tangent - thematic swap tables for the 13 original backgrounds.")
    patch_backgrounds(TT / "TTBackgrounds.xml", tt_kits)

    write_maps(EXTRA / "TTStartingKitMaps.xml", extra_kits, "Extra Backgrounds - starting-kit maps for every extra background loot list.")
    write_thematic(EXTRA / "StartingGearThematic.xml", extra_kits, "Extra Backgrounds - thematic swap tables for every extra background loot list.")
    patch_backgrounds(EXTRA / "TTBackgrounds.xml", extra_kits)

    print(f"TT maps: {len(tt_kits)}")
    print(f"Extra maps: {len(extra_kits)}")


if __name__ == "__main__":
    main()
