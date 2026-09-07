#!/usr/bin/env python3
"""Install packed Unity sheets + .animation files onto Magi-Tech items and stations.

Copies icons/sheets next to .item files, writes cycle animations, rewrites
animationParts that pointed at missing shell/fuse/glow (or gun butt/barrel)
pieces, emits real spellstone .item files, and points stations at packed art.
"""
from __future__ import annotations

import argparse
import copy
import json
import shutil
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

_TOOLS = Path(__file__).resolve().parent
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from starbound_action_cycles import (
    build_active_item_animation,
    build_object_animation,
    cycles_for_batch,
)

SHEETS = Path("assets") / "magitech" / "unity_sheets"

# Catalog item id -> packed still id (first existing file wins if list).
SPELLSTONE_PACKED: Dict[str, List[str]] = {
    "spellstone_core_common": ["spellstone_core_common"],
    "spellstone_core_refined": ["spellstone_core_uncommon"],
    "spellstone_core_arcane": ["spellstone_core_epic"],
    "spellstone_core_apex": ["spellstone_core_legendary"],
    "spellstone_fire": ["spellstone_fire"],
    "spellstone_ice": ["spellstone_ice"],
    "spellstone_lightning": ["spellstone_electric"],
    "spellstone_nature": ["spellstone_poison", "spellstone_variant_03"],
    "spellstone_cosmic": ["spellstone_cosmic", "spellstone_variant_04"],
    "spellstone_arcane": ["spellstone_core_rare"],
    "spellstone_void": ["spellstone_variant_01"],
    "spellstone_temporal": ["spellstone_variant_02"],
}

# Existing .item stem -> (batch, packed_id) when names do not match.
ALIASES: Dict[str, Tuple[str, str]] = {
    # Reagents were classified into the grenade time window (no reagent batch).
    "reagent_vial": ("grenade", "grenade_15"),
    "reagent_fireessence": ("grenade", "grenade_16"),
    "reagent_icecrystal": ("grenade", "grenade_17"),
    "reagent_poisoncloud": ("grenade", "grenade_18"),
    "reagent_oilpowder": ("grenade", "grenade_19"),
    "reagent_catalyst": ("grenade", "grenade_20"),
    "fire_essence": ("ingredient", "fire_ruby"),
    "ice_essence": ("ingredient", "ice_crystal"),
    "lightning_essence": ("ingredient", "lightning_core"),
    "explosive_core": ("ingredient", "power_amplifier"),
    "mana_crystal": ("ingredient", "mana_crystal"),
    "mt_voidessence": ("ingredient", "void_fragment"),
    "mt_stellarfragment": ("ingredient", "star_fragment"),
    "mt_dimensionalkey": ("ingredient", "cosmic_dust"),
    "magitech_device": ("weapon", "magitechdevice"),
}

ITEM_FOLDERS = [
    ("grenade", "items/ammo/specializedgrenades"),
    ("grenade", "items/ammo/chemicalgrenadeammo"),
    ("grenade", "items/weapons/alchemicalgrenadelauncher"),
    ("reagent", "items/consumable/reagents"),
    ("minion", "items/magitech/minion_enhancements"),
    ("ingredient", "items/materials/spellcrafting"),
    ("ingredient", "items/materials/cosmic"),
    ("weapon", "items/active"),
]

INGREDIENT_LABELS = {
    "fire_ruby": "Fire Ruby",
    "ice_crystal": "Ice Crystal",
    "lightning_core": "Lightning Core",
    "earth_core": "Earth Core",
    "water_pearl": "Water Pearl",
    "air_wisp": "Air Wisp",
    "shadow_wisp": "Shadow Wisp",
    "light_prism": "Light Prism",
    "nature_seed": "Nature Seed",
    "cosmic_dust": "Cosmic Dust",
    "mana_crystal": "Mana Crystal",
    "focus_crystal": "Focus Crystal",
    "resonance_crystal": "Resonance Crystal",
    "prismatic_crystal": "Prismatic Crystal",
    "chaos_crystal": "Chaos Crystal",
    "stability_catalyst": "Stability Catalyst",
    "power_amplifier": "Power Amplifier",
    "resonance_tuner": "Resonance Tuner",
    "mana_conductor": "Mana Conductor",
    "elemental_focus": "Elemental Focus",
    "salamander_scale": "Salamander Scale",
    "frost_essence": "Frost Essence",
    "storm_catalyst": "Storm Catalyst",
    "void_fragment": "Void Fragment",
    "solar_essence": "Solar Essence",
    "mountain_stone": "Mountain Stone",
    "ocean_essence": "Ocean Essence",
    "life_essence": "Life Essence",
    "star_fragment": "Star Fragment",
    "void_crystal": "Void Crystal",
    "phoenix_feather": "Phoenix Feather",
}


def copy_if(src: Path, dest: Path) -> bool:
    if not src.exists():
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return True


def load_json(path: Path) -> Optional[dict]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def asset_rel(mod: Path, path: Path) -> str:
    return "/" + path.relative_to(mod).as_posix()


def rewrite_sheet_refs(node, sheet_rel: str) -> None:
    if isinstance(node, dict):
        for key, val in node.items():
            if key == "image" and isinstance(val, str) and ":" in val:
                node[key] = f"{sheet_rel}:{val.split(':', 1)[1]}"
            else:
                rewrite_sheet_refs(val, sheet_rel)
    elif isinstance(node, list):
        for item in node:
            rewrite_sheet_refs(item, sheet_rel)


def animation_with_parts(base: dict, part_names: Iterable[str], sheet_rel: str) -> dict:
    anim = copy.deepcopy(base)
    parts = anim.get("animatedParts", {}).get("parts") or {}
    template = next(iter(parts.values()), None)
    if template is None:
        template = build_active_item_animation("weapon", sheet_rel, cycles_for_batch("grenade"))[
            "animatedParts"
        ]["parts"]["weapon"]
    rewrite_sheet_refs(template, sheet_rel)
    anim["animatedParts"]["parts"] = {
        name: copy.deepcopy(template) for name in part_names
    }
    return anim


def packed_dir(mod: Path, batch: str) -> Path:
    return mod / SHEETS / batch


def resolve_packed(mod: Path, item_id: str, batch: str) -> Optional[str]:
    if item_id in ALIASES:
        alias_batch, packed = ALIASES[item_id]
        if (packed_dir(mod, alias_batch) / f"{packed}.png").exists():
            return packed
    src = packed_dir(mod, batch)
    if (src / f"{item_id}.png").exists() or (src / f"{item_id}_sheet.png").exists():
        return item_id
    return None


def part_names_from_item(data: Optional[dict], fallback: str) -> List[str]:
    if not data:
        return [fallback]
    parts = data.get("animationParts")
    if isinstance(parts, dict) and parts:
        return list(parts.keys())
    return [fallback]


def copy_missing_part_files(folder: Path, data: Optional[dict], fill: Path) -> None:
    """If animationParts still name missing PNGs, drop a copy so old paths load."""
    if not data or not fill.exists():
        return
    parts = data.get("animationParts")
    if not isinstance(parts, dict):
        return
    for raw in parts.values():
        if not isinstance(raw, str):
            continue
        name = Path(raw.replace("\\", "/")).name
        dest = folder / name
        if not dest.exists():
            shutil.copy2(fill, dest)


def write_animation(
    dest: Path,
    packed_anim: Path,
    part_names: List[str],
    sheet_rel: str,
    batch: str,
) -> None:
    base = load_json(packed_anim) if packed_anim.exists() else None
    if base is None:
        primary = part_names[0] if part_names else "weapon"
        base = build_active_item_animation(primary, sheet_rel, cycles_for_batch(batch))
    dest.write_text(
        json.dumps(animation_with_parts(base, part_names, sheet_rel), indent=2) + "\n",
        encoding="utf-8",
    )


def patch_item(item_path: Path, mod: Path, sheet_name: str, anim_name: str) -> None:
    data = load_json(item_path)
    if data is None:
        return
    folder = item_path.parent
    if isinstance(data.get("animationParts"), dict) and data["animationParts"]:
        data["animationParts"] = {
            name: sheet_name for name in data["animationParts"].keys()
        }
    if "inventoryIcon" in data:
        icon = folder / f"{item_path.stem}.png"
        if icon.exists():
            data["inventoryIcon"] = f"{item_path.stem}.png"
    data["animation"] = asset_rel(mod, folder / anim_name)
    item_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def overlay_generated(mod: Path, item: Path) -> bool:
    """Prefer Magi-Tech SD pipeline output over packed-still pose fakes."""
    gen = mod / "assets" / "magitech" / "generated" / item.stem
    sheet_src = gen / f"{item.stem}_sheet.png"
    icon_src = gen / f"{item.stem}.png"
    if not gen.is_dir() or not (sheet_src.exists() or icon_src.exists()):
        return False
    folder = item.parent
    copied = False
    for name in (
        f"{item.stem}.png",
        f"{item.stem}_sheet.png",
        f"{item.stem}_sheet.frames",
        f"{item.stem}.frames",
        f"{item.stem}.animation",
    ):
        if copy_if(gen / name, folder / name):
            copied = True
    data = load_json(item)
    sheet = f"{item.stem}_sheet.png" if (folder / f"{item.stem}_sheet.png").exists() else f"{item.stem}.png"
    anim = f"{item.stem}.animation"
    if (folder / anim).exists() or (folder / sheet).exists():
        names = part_names_from_item(data, "weapon")
        if data is not None:
            if not (folder / anim).exists():
                write_animation(folder / anim, gen / f"{item.stem}.animation", names, sheet, "grenade")
            copy_missing_part_files(folder, data, folder / sheet)
            patch_item(item, mod, sheet, anim)
        print(f"  [generated] {item.stem} <- assets/magitech/generated/{item.stem}")
        return True
    return copied


def install_one(mod: Path, item: Path, batch: str, packed: str) -> int:
    if overlay_generated(mod, item):
        return 1
    src_batch = batch
    if item.stem in ALIASES:
        src_batch, packed = ALIASES[item.stem]
    src = packed_dir(mod, src_batch)
    folder = item.parent
    data = load_json(item)
    names = part_names_from_item(data, "weapon")
    icon = src / f"{packed}.png"
    sheet = src / f"{packed}_sheet.png"
    idle = src / f"{packed}_idle.png"
    n = 0
    if copy_if(icon, folder / f"{item.stem}.png"):
        copy_if(src / f"{packed}.frames", folder / f"{item.stem}.frames")
        n += 1
    sheet_name = f"{item.stem}_sheet.png"
    anim_image = sheet_name
    if sheet.exists():
        copy_if(sheet, folder / sheet_name)
        copy_if(src / f"{packed}_sheet.frames", folder / f"{item.stem}_sheet.frames")
        fill = folder / sheet_name
    elif idle.exists():
        copy_if(idle, folder / f"{item.stem}_idle.png")
        copy_if(src / f"{packed}_idle.frames", folder / f"{item.stem}_idle.frames")
        copy_if(idle, folder / sheet_name)
        copy_if(src / f"{packed}_idle.frames", folder / f"{item.stem}_sheet.frames")
        anim_image = f"{item.stem}_idle.png"
        fill = folder / f"{item.stem}_idle.png"
        n += 1
    else:
        fill = folder / f"{item.stem}.png"
        anim_image = f"{item.stem}.png"
    if fill.exists():
        write_animation(
            folder / f"{item.stem}.animation",
            src / f"{packed}.animation",
            names,
            anim_image,
            batch,
        )
        copy_missing_part_files(folder, data, fill)
        patch_item(item, mod, anim_image, f"{item.stem}.animation")
        n += 1
    print(f"  [{batch}] {item.stem} <- {packed}")
    return n


def install_batch_into_folder(mod: Path, batch: str, folder: Path) -> int:
    if not folder.exists():
        return 0
    n = 0
    for item in list(folder.glob("*.item")) + list(folder.glob("*.activeitem")):
        packed = resolve_packed(mod, item.stem, batch)
        if not packed or item.stem == "magitech_device":
            continue
        n += install_one(mod, item, batch, packed)
    return n


def emit_spellstones(mod: Path) -> int:
    catalog = mod / "items" / "spellstones" / "spellstone_items.json"
    src_dir = packed_dir(mod, "spellstone")
    dest = mod / "items" / "spellstones"
    dest.mkdir(parents=True, exist_ok=True)
    data = load_json(catalog)
    if data is None:
        print("  [spellstone] catalog is not JSON; skipped emit")
        return 0
    root = data.get("spellstone_items") or {}
    n = 0
    used_packed = set()
    for group in ("base_cores", "elemental_variants"):
        block = root.get(group) or {}
        for item_id, spec in block.items():
            packed = next(
                (c for c in SPELLSTONE_PACKED.get(item_id, []) if (src_dir / f"{c}.png").exists()),
                None,
            )
            if not packed:
                continue
            used_packed.add(packed)
            copy_if(src_dir / f"{packed}.png", dest / f"{item_id}.png")
            copy_if(src_dir / f"{packed}.frames", dest / f"{item_id}.frames")
            sheet = src_dir / f"{packed}_sheet.png"
            if sheet.exists():
                copy_if(sheet, dest / f"{item_id}_sheet.png")
                copy_if(src_dir / f"{packed}_sheet.frames", dest / f"{item_id}_sheet.frames")
                write_animation(
                    dest / f"{item_id}.animation",
                    src_dir / f"{packed}.animation",
                    ["weapon"],
                    f"{item_id}_sheet.png",
                    "spellstone",
                )
            item = {
                "itemName": item_id,
                "rarity": spec.get("rarity", "Common"),
                "category": "craftingMaterial",
                "price": spec.get("price", 50),
                "maxStack": spec.get("maxStack", 100),
                "description": spec.get("description", ""),
                "shortdescription": spec.get("itemName", item_id),
                "inventoryIcon": f"{item_id}.png",
                "animation": f"{item_id}.animation",
                "animationParts": {"weapon": f"{item_id}_sheet.png"},
                "itemTags": [
                    "magitech",
                    "spellstone",
                    spec.get("properties", {}).get("elementalAffinity", "neutral"),
                ],
                "tooltipKind": "generic",
            }
            props = spec.get("properties") or {}
            if props:
                item["spellstoneData"] = props
            (dest / f"{item_id}.item").write_text(json.dumps(item, indent=2) + "\n", encoding="utf-8")
            if "asset" in spec:
                spec["asset"]["primary"] = f"/items/spellstones/{item_id}.png"
                spec["asset"]["source"] = "magitech_unity"
                spec["asset"]["license"] = "mod"
                spec["asset"]["attribution"] = "Packed Magi-Tech Unity still"
            n += 1
            print(f"  [spellstone] {item_id} <- {packed}")
    catalog.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    # Leftover variant stills become extra items so the art is used.
    for icon in sorted(src_dir.glob("spellstone_variant_*.png")):
        if "_sheet" in icon.name or any(
            icon.stem.endswith(sfx)
            for sfx in ("_idle", "_fire", "_charge", "_spark", "_charged", "_discharge", "_cooldown", "_altFire")
        ):
            continue
        packed = icon.stem
        if packed in used_packed:
            continue
        item_id = packed
        copy_if(icon, dest / f"{item_id}.png")
        copy_if(src_dir / f"{packed}.frames", dest / f"{item_id}.frames")
        sheet = src_dir / f"{packed}_sheet.png"
        if sheet.exists():
            copy_if(sheet, dest / f"{item_id}_sheet.png")
            copy_if(src_dir / f"{packed}_sheet.frames", dest / f"{item_id}_sheet.frames")
            write_animation(
                dest / f"{item_id}.animation",
                src_dir / f"{packed}.animation",
                ["weapon"],
                f"{item_id}_sheet.png",
                "spellstone",
            )
        item = {
            "itemName": item_id,
            "rarity": "Uncommon",
            "category": "craftingMaterial",
            "price": 80,
            "maxStack": 99,
            "description": "An uncatalogued spellstone still from the Magi-Tech packing run.",
            "shortdescription": item_id.replace("_", " ").title(),
            "inventoryIcon": f"{item_id}.png",
            "animation": f"{item_id}.animation",
            "animationParts": {"weapon": f"{item_id}_sheet.png"},
            "itemTags": ["magitech", "spellstone", "variant"],
        }
        (dest / f"{item_id}.item").write_text(json.dumps(item, indent=2) + "\n", encoding="utf-8")
        n += 1
        print(f"  [spellstone] extra {item_id}")
    return n


def emit_leftover_ingredients(mod: Path) -> int:
    src = packed_dir(mod, "ingredient")
    dest = mod / "items" / "materials" / "spellcrafting"
    dest.mkdir(parents=True, exist_ok=True)
    existing = {p.stem for p in dest.glob("*.item")}
    aliased = {packed for packed in (v[1] for v in ALIASES.values() if v[0] == "ingredient")}
    n = 0
    for icon in sorted(src.glob("*.png")):
        if any(
            icon.stem.endswith(sfx)
            for sfx in (
                "_idle",
                "_sheet",
                "_fire",
                "_charge",
                "_spark",
                "_charged",
                "_discharge",
                "_cooldown",
                "_altFire",
            )
        ):
            continue
        packed = icon.stem
        if packed in existing or packed in aliased:
            continue
        if (dest / f"{packed}.item").exists():
            continue
        copy_if(icon, dest / f"{packed}.png")
        copy_if(src / f"{packed}.frames", dest / f"{packed}.frames")
        sheet = src / f"{packed}_sheet.png"
        idle = src / f"{packed}_idle.png"
        anim_image = f"{packed}_sheet.png"
        if sheet.exists():
            copy_if(sheet, dest / f"{packed}_sheet.png")
            copy_if(src / f"{packed}_sheet.frames", dest / f"{packed}_sheet.frames")
        elif idle.exists():
            copy_if(idle, dest / f"{packed}_idle.png")
            copy_if(src / f"{packed}_idle.frames", dest / f"{packed}_idle.frames")
            copy_if(idle, dest / f"{packed}_sheet.png")
            anim_image = f"{packed}_idle.png"
        write_animation(
            dest / f"{packed}.animation",
            src / f"{packed}.animation",
            ["weapon"],
            anim_image,
            "ingredient",
        )
        label = INGREDIENT_LABELS.get(packed, packed.replace("_", " ").title())
        item = {
            "itemName": packed,
            "price": 40,
            "rarity": "Common",
            "category": "craftingMaterial",
            "inventoryIcon": f"{packed}.png",
            "description": f"A packed Magi-Tech spellcrafting reagent: {label}.",
            "shortdescription": label,
            "itemTags": ["magitech", "spellcrafting", "ingredient"],
            "maxStack": 99,
            "animation": f"{packed}.animation",
            "animationParts": {"weapon": f"{packed}_sheet.png"},
        }
        (dest / f"{packed}.item").write_text(json.dumps(item, indent=2) + "\n", encoding="utf-8")
        n += 1
        print(f"  [ingredient] extra {packed}")
    return n


def install_stations(mod: Path) -> int:
    src = packed_dir(mod, "station")
    n = 0
    workbench = mod / "objects" / "magitech" / "deviceworkbench"
    copy_if(src / "deviceworkbench.png", workbench / "deviceworkbenchicon.png")
    copy_if(src / "deviceworkbench_idle.png", workbench / "deviceworkbench.png")
    copy_if(src / "deviceworkbench_idle.frames", workbench / "deviceworkbench.frames")
    copy_if(src / "deviceworkbench_sheet.png", workbench / "deviceworkbench_sheet.png")
    copy_if(src / "deviceworkbench_sheet.frames", workbench / "deviceworkbench_sheet.frames")
    if (src / "deviceworkbench.animation").exists():
        copy_if(src / "deviceworkbench.animation", workbench / "deviceworkbench.animation")
    else:
        (workbench / "deviceworkbench.animation").write_text(
            json.dumps(
                build_object_animation("deviceworkbench", "deviceworkbench_sheet.png"),
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    n += 1

    station_dir = mod / "objects" / "magitech"
    name = "magitechspellcraftingstation"
    copy_if(src / f"{name}.png", station_dir / f"{name}icon.png")
    copy_if(src / f"{name}_idle.png", station_dir / f"{name}.png")
    copy_if(src / f"{name}_idle.frames", station_dir / f"{name}.frames")
    copy_if(src / f"{name}_sheet.png", station_dir / f"{name}_sheet.png")
    copy_if(src / f"{name}_sheet.frames", station_dir / f"{name}_sheet.frames")
    # Lit overlay uses the working cycle so the missing *lit.png exists.
    copy_if(src / f"{name}_working.png", station_dir / f"{name}lit.png")
    copy_if(src / f"{name}_working.frames", station_dir / f"{name}lit.frames")
    anim_path = station_dir / f"{name}.animation"
    packed_anim = src / f"{name}.animation"
    if packed_anim.exists():
        copy_if(packed_anim, anim_path)
    else:
        anim_path.write_text(
            json.dumps(build_object_animation(name, f"{name}_sheet.png"), indent=2) + "\n",
            encoding="utf-8",
        )
    n += 1

    obj = station_dir / "mt_magitechspellcraftingstation.object"
    data = load_json(obj)
    if data:
        data["inventoryIcon"] = f"{name}icon.png"
        data["animation"] = f"{name}.animation"
        data["animationParts"] = {
            name: f"{name}_sheet.png",
            "bg": f"{name}.png",
            "fg": f"{name}lit.png",
        }
        orients = data.get("orientations") or []
        if orients:
            orients[0]["dualImage"] = f"{name}.png:<color>.<frame>"
            orients[0]["frames"] = 8
        obj.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    placeholder = station_dir / "magitechspellcraftingstation.object"
    data = load_json(placeholder)
    if data:
        data["inventoryIcon"] = f"/objects/magitech/{name}icon.png"
        data["animation"] = f"/objects/magitech/{name}.animation"
        if data.get("orientations"):
            data["orientations"][0]["image"] = f"/objects/magitech/{name}.png:<color>.<frame>"
            data["orientations"][0]["frames"] = 8
        placeholder.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print("  [station] deviceworkbench + spellcraftingstation (+ lit/working anim)")
    return n


def install_magitech_device_anims(mod: Path) -> int:
    src = packed_dir(mod, "weapon")
    dest = mod / "items" / "active"
    copy_if(src / "magitechdevice.png", dest / "magitechdevice.png")
    copy_if(src / "magitechdevice.png", dest / "magitech_device.png")
    copy_if(src / "magitechdevice_sheet.png", dest / "magitechdevice_sheet.png")
    copy_if(src / "magitechdevice_sheet.frames", dest / "magitechdevice_sheet.frames")
    copy_if(src / "magitech_device_upgraded.png", dest / "magitech_device_upgraded.png")
    copy_if(src / "magitech_device_upgraded_sheet.png", dest / "magitech_device_upgraded_sheet.png")

    sheet = "magitechdevice_sheet.png"
    device_anim = {
        "animatedParts": {
            "stateTypes": {
                "activation": {
                    "default": "inactive",
                    "states": {
                        "inactive": {"frames": 8, "cycle": 1.2, "mode": "loop"},
                        "active": {"frames": 4, "cycle": 0.5, "mode": "loop"},
                        "casting": {
                            "frames": 6,
                            "cycle": 0.8,
                            "mode": "transition",
                            "transition": "active",
                        },
                    },
                },
                "device": {
                    "default": "inactive",
                    "states": {
                        "inactive": {"frames": 8, "cycle": 1.2, "mode": "loop"},
                        "active": {"frames": 4, "cycle": 0.5, "mode": "loop"},
                        "casting": {
                            "frames": 6,
                            "cycle": 0.8,
                            "mode": "transition",
                            "transition": "active",
                        },
                    },
                },
            },
            "parts": {},
        },
        "transformationGroups": {"weapon": {}},
        "sounds": {
            "activate": ["/sfx/interface/button_select.ogg"],
            "deactivate": ["/sfx/interface/button_cancel.ogg"],
            "cast": ["/sfx/projectiles/staff_projectile1.ogg"],
            "brew": ["/sfx/interface/crafting_hands.ogg"],
            "summon": ["/sfx/tech/tech_dash.ogg"],
        },
    }
    part_template = {
        "properties": {
            "zLevel": 0,
            "centered": True,
            "image": f"{sheet}:idle.<frame>",
            "offset": [0, 0],
            "transformationGroups": ["weapon"],
        },
        "partStates": {
            "activation": {
                "inactive": {"properties": {"image": f"{sheet}:idle.<frame>"}},
                "active": {"properties": {"image": f"{sheet}:loop.<frame>"}},
                "casting": {"properties": {"image": f"{sheet}:fire.<frame>"}},
            },
            "device": {
                "inactive": {"properties": {"image": f"{sheet}:idle.<frame>"}},
                "active": {"properties": {"image": f"{sheet}:loop.<frame>"}},
                "casting": {"properties": {"image": f"{sheet}:fire.<frame>"}},
            },
        },
    }
    bright = copy.deepcopy(part_template)
    bright["properties"]["zLevel"] = 1
    bright["properties"]["fullbright"] = True
    device_anim["animatedParts"]["parts"] = {
        "device": part_template,
        "deviceFullbright": bright,
    }
    text = json.dumps(device_anim, indent=2) + "\n"
    (dest / "magitechdevice.animation").write_text(text, encoding="utf-8")
    anim_dir = mod / "animations" / "magitech"
    anim_dir.mkdir(parents=True, exist_ok=True)
    # Shared animation files used by magitech_device.activeitem
    shared = copy.deepcopy(device_anim)
    rewrite_sheet_refs(shared, "/items/active/magitechdevice_sheet.png")
    (anim_dir / "mt_magitech_device.animation").write_text(
        json.dumps(shared, indent=2) + "\n", encoding="utf-8"
    )
    (anim_dir / "magitech_device.animation").write_text(
        json.dumps(shared, indent=2) + "\n", encoding="utf-8"
    )

    item = dest / "magitech_device.activeitem"
    data = load_json(item)
    if data:
        data["inventoryIcon"] = "magitech_device.png"
        data["animation"] = "/animations/magitech/mt_magitech_device.animation"
        data["animationParts"] = {
            "device": "magitechdevice_sheet.png",
            "deviceFullbright": "magitechdevice_sheet.png",
        }
        up = data.get("upgradeParameters") or {}
        up["inventoryIcon"] = "magitech_device_upgraded.png"
        up["animationParts"] = {
            "device": "magitech_device_upgraded_sheet.png",
            "deviceFullbright": "magitech_device_upgraded_sheet.png",
        }
        data["upgradeParameters"] = up
        item.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print("  [weapon] magitech_device + shared animations")
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Install packed sheets and animations onto Magi-Tech items")
    ap.add_argument(
        "--mod-path",
        default=r"F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery",
    )
    args = ap.parse_args()
    mod = Path(args.mod_path)
    total = 0
    for batch, rel in ITEM_FOLDERS:
        total += install_batch_into_folder(mod, batch, mod / rel)
    total += emit_spellstones(mod)
    total += emit_leftover_ingredients(mod)
    total += install_stations(mod)
    total += install_magitech_device_anims(mod)
    print(f"[OK] Installed item/object sheets and animations ({total} writes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
