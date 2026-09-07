#!/usr/bin/env python3
"""
Gameplay def writers for Shared game_asset_kind packs.

Writes portable JSON (Unity/Elin-facing) plus Transcendence module XML
(ItemType missile weapons / ShipClass) that reference generated art paths.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from xml.dom import minidom
from xml.etree.ElementTree import Element, SubElement, tostring


def _rel(path: Optional[str], root: Path) -> Optional[str]:
    if not path:
        return None
    p = Path(path)
    try:
        return p.resolve().relative_to(root.resolve()).as_posix()
    except Exception:
        return p.name


def _rel_list(paths: Optional[List[str]], root: Path) -> List[str]:
    out = []
    for p in paths or []:
        r = _rel(p, root)
        if r:
            out.append(r)
    return out


def _display_name(name: str, theme: str) -> str:
    pretty = re.sub(r"[_\-]+", " ", name).strip()
    return pretty.title() if pretty else theme[:48]


def _entity_token(kind: str, name: str, role: str) -> str:
    """Entity name without &/; e.g. rsAamtProjA1B2C3."""
    dig = hashlib.md5(f"{kind}:{name}:{role}".encode("utf-8")).hexdigest()[:6].upper()
    prefixes = {
        ("projectile", "image"): "rsAamtProj",
        ("projectile", "effect"): "efAamtProj",
        ("projectile", "hit"): "efAamtHit",
        ("projectile", "item"): "itAamtWpn",
        ("ship", "image"): "rsAamtShip",
        ("ship", "hero"): "rsAamtShipHero",
        ("ship", "class"): "scAamtShip",
        ("ship", "armorHud"): "rsAamtArmorHud",
        ("ship", "armorSeg"): "rsAamtArmorSeg",
        ("ship", "shieldHud"): "rsAamtShieldHud",
        ("ship", "shieldEffect"): "efAamtShieldHud",
        ("ship", "shieldOverlay"): "rsAamtShieldOv",
        ("ship", "shieldOverlayType"): "ovAamtShield",
        ("spell", "image"): "rsAamtSpell",
    }
    return f"{prefixes.get((kind, role), 'rsAamt')}{dig}"


def _hex_unid(kind: str, name: str, role: str) -> str:
    """
    Private-range UNID (0xDAAxxxxx) deterministic per kind/name/role.
    Safe for local Extensions; remapped if publishing to Multiverse.
    """
    dig = hashlib.md5(f"aamt:{kind}:{name}:{role}".encode("utf-8")).hexdigest()[:5].upper()
    # 0xDAA00000 .. 0xDAAFFFFF band
    return f"0xDAA{dig}"


def _stable_unid(name: str, kind: str) -> str:
    """Back-compat entity reference for callers expecting &token; form."""
    role = "image"
    return f"&{_entity_token(kind, name, role)};"


def _stats_for(kind: str, spec: Dict[str, Any]) -> Dict[str, Any]:
    colors = spec.get("colors") or []
    base = {
        "spell": {"damage": 12, "manaCost": 8, "cooldownSec": 3.0, "range": 6, "projectileSpeed": 14},
        "projectile": {"damage": 10, "speed": 18, "lifetimeSec": 2.5, "homing": 0.0, "fireRate": 15, "powerUse": 50, "level": 5},
        "ship": {"hull": 100, "armor": 20, "thrust": 300, "turnRate": 8.0, "cargo": 50, "mass": 40, "size": 36, "maxSpeed": 20, "level": 5},
    }.get(kind, {})
    theme = (spec.get("theme") or "").lower()
    if "plasma" in theme or "fire" in theme:
        if "damage" in base:
            base["damage"] = int(base["damage"] * 1.2)
    if "obsidian" in theme or "armor" in theme:
        if "armor" in base:
            base["armor"] = int(base["armor"] * 1.3)
        if "mass" in base:
            base["mass"] = int(base["mass"] * 1.2)
    if "frigate" in theme or "heavy" in theme:
        if "size" in base:
            base["size"] = int(base["size"] * 1.4)
        if "cargo" in base:
            base["cargo"] = int(base["cargo"] * 1.5)
    if colors:
        base["primaryColor"] = colors[0]
        if len(colors) > 1:
            base["secondaryColor"] = colors[1]
    return base


def _tx_damage_type(theme: str) -> str:
    t = theme.lower()
    if any(k in t for k in ("plasma", "fire", "flame", "thermo")):
        return "blast"
    if any(k in t for k in ("ion", "positron", "particle")):
        return "positron"
    if any(k in t for k in ("laser", "beam", "photon", "light")):
        return "laser"
    if any(k in t for k in ("missile", "rocket", "kinetic", "slug")):
        return "kinetic"
    return "kinetic"


def _tx_dice(damage: int) -> str:
    """Map AAMT damage int to Transcendence NdM dice roughly."""
    dmg = max(1, int(damage))
    if dmg <= 4:
        return f"1d{max(2, dmg)}"
    if dmg <= 12:
        return f"2d{max(3, (dmg + 1) // 2)}"
    return f"3d{max(4, dmg // 3)}"


def _png_size(path: Optional[Path]) -> Tuple[int, int]:
    if not path or not path.is_file():
        return (32, 32)
    try:
        from PIL import Image

        with Image.open(path) as im:
            return (int(im.width), int(im.height))
    except Exception:
        return (32, 32)


def _write_tx_extension(
    path: Path,
    *,
    pack_entity: str,
    pack_hex: str,
    display_name: str,
    entities: List[Tuple[str, str]],
    body: str,
) -> Path:
    """
    Write a drop-in TranscendenceExtension (api 57) for Extensions/.
    Pattern mirrors game_and_dlc_source + Armstrong playership: extends HumanSpaceLibrary.
    """
    all_ents: List[Tuple[str, str]] = [(pack_entity, pack_hex), ("unidHumanSpaceLibrary", "0x00100000")]
    seen = {pack_entity, "unidHumanSpaceLibrary"}
    for name, hex_id in entities:
        if name not in seen:
            all_ents.append((name, hex_id))
            seen.add(name)

    entity_lines = "\n".join(f'<!ENTITY {n} "{h}">' for n, h in all_ents)
    text = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        "<!DOCTYPE TranscendenceExtension [\n"
        f"{entity_lines}\n"
        "]>\n"
        f'<TranscendenceExtension UNID="&{pack_entity};"\n'
        f'\tname="{display_name}"\n'
        '\tapiVersion="57"\n'
        '\textends="0x00100000"\n'
        '\tversion="1.0"\n'
        '\tcredits="AAMT">\n'
        "\n"
        "<!-- Generated by AAMT from Shared/game_asset_defs.py -->\n"
        "<!-- Schema refs: game_and_dlc_source/Transcendence_Source (StdWeapons / CommonwealthShips) -->\n"
        '\t<Library unid="&unidHumanSpaceLibrary;"/>\n'
        "\n"
        f"{body}\n"
        "</TranscendenceExtension>\n"
    )
    path.write_text(text, encoding="utf-8")
    # Sidecar install note
    readme = path.with_name("AAMT_TRANSCENDENCE_README.txt")
    if not readme.exists():
        readme.write_text(
            "Drop this folder (XML + image files) into:\n"
            "  D:\\games\\Steam\\steamapps\\common\\Transcendence\\Extensions\\\n"
            "Or run Tools\\Transcendence\\Deploy-AamtTranscendence.ps1 -SourceDir <pack>.\n"
            "Enable the extension in Transcendence. UNIDs use private 0xDAAxxxxx band.\n"
            "Weapons: frequency=uncommon + majorItem (standard treasure/shops).\n"
            "Ships: initialClass + playerClass/shipBroker (new-game picker + shipbroker).\n"
            "Ship art: HD {Name}.jpg + Mask.bmp from Blender mesh.\n"
            "Final mesh for touch-ups: Source/Models/{Name}.fbx (re-export via Export-AamtShipSpritesheet.ps1 -ReexportFrom).\n"
            "Unique hull/shield HUD: {Name}ArmorHUDShip.jpg + Segments + ShieldsHUD; alt meshes/textures in Source/Models/Alt/.\n"
            "Disable unique HUD (circular ArmorDisplay + efShieldHUDDefault): GenerateGameAsset.ps1 ... -NoUniqueHud / --no-unique-hud.\n"
            "Regen alt UI textures from current armor/shield content: Generate-AamtShipHudAltTextures.ps1 -PackDir <pack>.\n",
            encoding="utf-8",
        )
    return path



def _tx_horizontal_sheet(
    out_dir: Path, name: str, frame_paths: List[Path]
) -> Tuple[Optional[Path], int, int, int]:
    """Stitch frame PNGs left-to-right for Transcendence imageFrameCount animation."""
    existing = [fp for fp in frame_paths if fp and fp.is_file()]
    if not existing:
        return None, 32, 32, 1
    try:
        from PIL import Image as PILImage
    except ImportError:
        w, h = _png_size(existing[0])
        return existing[0], w, h, 1
    imgs = [PILImage.open(fp).convert("RGBA") for fp in existing]
    w, h = imgs[0].size
    sheet = PILImage.new("RGBA", (w * len(imgs), h), (0, 0, 0, 0))
    for i, im in enumerate(imgs):
        if im.size != (w, h):
            im = im.resize((w, h), PILImage.Resampling.NEAREST)
        sheet.paste(im, (i * w, 0), im)
    out = out_dir / "Frames" / f"{name}_sheet.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    return out, w, h, len(imgs)


def write_transcendence_projectile_xml(
    out_dir: Path,
    *,
    name: str,
    theme: str,
    manifest: Dict[str, Any],
    spec: Dict[str, Any],
) -> Path:
    """
    Emit installable missile Weapon ItemType (vanilla Recoilless pattern from StdWeapons.xml)
    plus Image + Effect using generated projectile frame art.
    """
    files = manifest.get("files") or {}
    frames = files.get("frames") or files.get("projectile") or []
    frame_paths = [Path(p) for p in frames if p]
    if not frame_paths and files.get("icon"):
        frame_paths = [Path(files["icon"])]
    sheet_abs, w, h, frame_count = _tx_horizontal_sheet(out_dir, name, frame_paths)
    first_rel = _rel(str(sheet_abs), out_dir) if sheet_abs else None
    stats = _stats_for("projectile", {**spec, "theme": theme})
    colors = spec.get("colors") or [stats.get("primaryColor", "#c0c0c0"), "#808080"]
    primary = str(colors[0])
    secondary = str(colors[1] if len(colors) > 1 else colors[0])
    dtype = _tx_damage_type(theme)
    dice = _tx_dice(int(stats.get("damage", 10)))
    speed = int(stats.get("speed", 18))
    # lifetime in ticks (~30/sec); convert from lifetimeSec
    life_ticks = max(10, int(float(stats.get("lifetimeSec", 2.5)) * 30))
    fire_rate = int(stats.get("fireRate", 15))
    power = int(stats.get("powerUse", 50))
    level = int(stats.get("level", 5))
    display = _display_name(name, theme)

    rs = _entity_token("projectile", name, "image")
    ef = _entity_token("projectile", name, "effect")
    it = _entity_token("projectile", name, "item")
    pack = f"unidAamtProj{hashlib.md5(name.encode()).hexdigest()[:6].upper()}"

    entities = [
        (rs, _hex_unid("projectile", name, "image")),
        (ef, _hex_unid("projectile", name, "effect")),
        (it, _hex_unid("projectile", name, "item")),
    ]

    bitmap_attr = f' bitmap="{first_rel}"' if first_rel else ""
    frame_count = max(1, int(frame_count))
    mesh_note = ""
    if files.get("mesh"):
        mesh_rel = _rel(files["mesh"], out_dir) or ""
        mesh_note = f"\n\t<!-- Optional mesh (not used by engine ItemType): {mesh_rel} -->\n"

    body = f'''{mesh_note}\t<!-- Projectile image (AAMT Frames/) -->
\t<Image UNID="&{rs};"{bitmap_attr} loadOnUse="true"/>

\t<!-- Flight effect: image + ray (StdWeapons kinetic bolt pattern) -->
\t<Effect UNID="&{ef};">
\t\t<Image imageID="&{rs};" imageX="0" imageY="0" imageWidth="{w}" imageHeight="{h}" imageFrameCount="{frame_count}" imageTicksPerFrame="2" rotationCount="1"/>
\t\t<Ray style="smooth" shape="oval" width="{max(8, w // 2)}" length="{max(16, w)}" primaryColor="{primary}" secondaryColor="{secondary}" intensity="14"/>
\t</Effect>

\t<!-- Weapon ItemType — StdWeapons recoilless; frequency uncommon for treasure -->
\t<ItemType UNID="&{it};"
\t\t\tname=\t\t\t\t"{display.lower()} cannon"
\t\t\tattributes=\t\t\t"aamt, majorItem, energyWeapon"
\t\t\tlevel=\t\t\t\t"{level}"
\t\t\tfrequency=\t\t\t"uncommon"
\t\t\tvalue=\t\t\t\t"{max(100, level * 200)}"
\t\t\tmass=\t\t\t\t"2000"
\t\t\tdescription=\t\t"{theme.replace(chr(34), "'")}"
\t\t\t>
\t\t<Image imageID="&{rs};" imageX="0" imageY="0" imageWidth="{w}" imageHeight="{h}"/>
\t\t<Weapon
\t\t\t\ttype=\t\t\t\t"missile"
\t\t\t\tdamage=\t\t\t\t"{dtype}:{dice}"
\t\t\t\tfireRate=\t\t\t"{fire_rate}"
\t\t\t\tmissileSpeed=\t\t"{max(10, speed)}"
\t\t\t\tlifetime=\t\t\t"{life_ticks}"
\t\t\t\tpowerUse=\t\t\t"{power}"
\t\t\t\teffect=\t\t\t\t"&{ef};"
\t\t\t\tsound=\t\t\t\t"&snRecoillessCannon;"
\t\t\t\t>
\t\t</Weapon>
\t</ItemType>
'''

    path = out_dir / f"{name}_transcendence.xml"
    return _write_tx_extension(
        path,
        pack_entity=pack,
        pack_hex=_hex_unid("projectile", name, "pack"),
        display_name=f"AAMT {display}",
        entities=entities,
        body=body,
    )


def write_transcendence_ship_xml(
    out_dir: Path,
    *,
    name: str,
    theme: str,
    manifest: Dict[str, Any],
    spec: Dict[str, Any],
) -> Path:
    """
    Emit installable ShipClass (Sapphire-yacht pattern from CommonwealthShips.xml)
    with 120-facings rotation spritesheet (JPG) from mesh render pipeline.
    """
    files = manifest.get("files") or {}
    rot = manifest.get("shipRotation") or {}

    sheet_abs = None
    for key in ("spritesheet", "sprite"):
        if files.get(key):
            sheet_abs = Path(files[key])
            break
    sheet_rel = _rel(str(sheet_abs), out_dir) if sheet_abs else None

    hero_abs = Path(files["hero"]) if files.get("hero") else None
    hero_rel = _rel(str(hero_abs), out_dir) if hero_abs else None

    fw = int(rot.get("frame_width") or rot.get("frameWidth") or 62)
    fh = int(rot.get("frame_height") or rot.get("frameHeight") or fw)
    facings = int(rot.get("facings") or 120)
    columns = int(rot.get("columns") or rot.get("rotationColumns") or 12)
    viewport = float(rot.get("viewportRatio") or max(0.003, min(0.01, (fw / 62.0) * 0.00475)))

    hw, hh = _png_size(hero_abs)
    if hero_abs is None:
        hw, hh = fw, fh

    stats = _stats_for("ship", {**spec, "theme": theme})
    display = _display_name(name, theme)
    size = int(stats.get("size", 36))
    mass = int(stats.get("mass", 40))
    cargo = int(stats.get("cargo", 50))
    thrust = int(stats.get("thrust", 300))
    max_speed = int(stats.get("maxSpeed", 20))
    turn = float(stats.get("turnRate", 8.0))
    level = int(stats.get("level", 5))

    rs = _entity_token("ship", name, "image")
    rh = _entity_token("ship", name, "hero")
    sc = _entity_token("ship", name, "class")
    rah = _entity_token("ship", name, "armorHud")
    ras = _entity_token("ship", name, "armorSeg")
    rsh = _entity_token("ship", name, "shieldHud")
    efsh = _entity_token("ship", name, "shieldEffect")
    rso = _entity_token("ship", name, "shieldOverlay")
    ovs = _entity_token("ship", name, "shieldOverlayType")
    pack = f"unidAamtShip{hashlib.md5(name.encode()).hexdigest()[:6].upper()}"
    entities = [
        (rs, _hex_unid("ship", name, "image")),
        (sc, _hex_unid("ship", name, "class")),
    ]
    if hero_rel:
        entities.append((rh, _hex_unid("ship", name, "hero")))

    sheet_bitmap = f' bitmap="{sheet_rel}"' if sheet_rel else ""
    mask_rel = _rel(files["spritesheetMask"], out_dir) if files.get("spritesheetMask") else None
    sheet_bitmask = f' bitmask="{mask_rel}"' if mask_rel else ""
    hero_bitmap = f' bitmap="{hero_rel}"' if hero_rel else ""
    hero_mask_rel = None
    if hero_rel and hero_abs:
        cand = hero_abs.with_name(hero_abs.stem + "Mask.bmp")
        if cand.is_file():
            hero_mask_rel = _rel(str(cand), out_dir)
            files.setdefault("heroMask", str(cand))
    hero_bitmask = f' bitmask="{hero_mask_rel}"' if hero_mask_rel else ""
    rot_source = rot.get("source") or "sheet"
    mesh_note = ""
    if files.get("mesh"):
        mesh_rel = _rel(files["mesh"], out_dir) or ""
        mesh_note = f"\n\t<!-- Source mesh (Blender facings export): {mesh_rel} -->\n"

    hero_img_tag = ""
    if hero_rel:
        hero_img_tag = f'\n\t<Image UNID="&{rh};"{hero_bitmap}{hero_bitmask} loadOnUse="true"/>'
    large_ref = f"&{rh};" if hero_rel else f"&{rs};"
    hero_ship_image = f"&{rh};" if hero_rel else f"&{rs};"

    unique = (manifest.get("uniqueHud") or {})
    unique_on = bool(unique.get("enabled")) and bool(files.get("armorHudShip")) and bool(files.get("shieldsHud"))
    # Spec can force circular HUD even if assets exist
    if spec.get("no_unique_hud") or unique.get("enabled") is False:
        unique_on = False

    armor_entity = ((unique.get("armor") or {}).get("entity")) or "itReactiveArmor"
    shield_entity = ((unique.get("shield") or {}).get("entity")) or "itClass1Deflector"
    armor_entity = str(armor_entity).strip().strip("&;")
    shield_entity = str(shield_entity).strip().strip("&;")

    hud_images = ""
    shield_effect_xml = ""
    player_hud = ""
    if unique_on:
        ah_rel = _rel(files.get("armorHudShip"), out_dir)
        ah_mask = _rel(files.get("armorHudShipMask"), out_dir)
        as_rel = _rel(files.get("armorHudSegments"), out_dir)
        sh_rel = _rel(files.get("shieldsHud"), out_dir)
        sh_mask = _rel(files.get("shieldsHudMask"), out_dir)
        entities.extend(
            [
                (rah, _hex_unid("ship", name, "armorHud")),
                (ras, _hex_unid("ship", name, "armorSeg")),
                (rsh, _hex_unid("ship", name, "shieldHud")),
                (efsh, _hex_unid("ship", name, "shieldEffect")),
            ]
        )
        ah_bit = f' bitmask="{ah_mask}"' if ah_mask else ""
        sh_bit = f' bitmask="{sh_mask}"' if sh_mask else ""
        hud_images = f'''
\t<!-- Unique ship Armor/Shield HUD (Sapphire layout; alt-mesh: Source/Models/Alt) -->
\t<Image UNID="&{rah};" bitmap="{ah_rel}"{ah_bit} loadOnUse="true"/>
\t<Image UNID="&{ras};" bitmap="{as_rel}" loadOnUse="true"/>
\t<Image UNID="&{rsh};" bitmap="{sh_rel}"{sh_bit} loadOnUse="true"/>
'''
        levels = unique.get("shieldLevels") or [
            {"maxValue": 0, "imageY": 680},
            {"maxValue": 24, "imageY": 544},
            {"maxValue": 49, "imageY": 408},
            {"maxValue": 74, "imageY": 272},
            {"maxValue": 99, "imageY": 136},
            {"maxValue": 100, "imageY": 0},
        ]
        variants = "\n".join(
            f'\t\t\t\t<Effect maxValue="{int(lv["maxValue"])}">\n'
            f'\t\t\t\t\t<Image imageID="&{rsh};" imageX="0" imageY="{int(lv["imageY"])}" '
            f'imageWidth="136" imageHeight="136"/>\n'
            f"\t\t\t\t</Effect>"
            for lv in levels
        )
        shield_effect_xml = f'''
\t<Effect UNID="&{efsh};">
\t\t<Variants>
{variants}
\t\t</Variants>
\t</Effect>
'''
        segs = unique.get("segments") or []
        if not segs:
            # Fallback Sapphire-style rects
            segs = [
                {"name": "forward", "segment": 0, "x": 0, "y": 0, "w": 52, "h": 29,
                 "destX": 42, "destY": 15, "hpX": 55, "hpY": 14, "nameY": 8,
                 "nameBreakWidth": 200, "nameDestX": 0, "nameDestY": 10},
                {"name": "starboard", "segment": 3, "x": 52, "y": 0, "w": 22, "h": 59,
                 "destX": 92, "destY": 45, "hpX": 95, "hpY": 60, "nameY": 30,
                 "nameBreakWidth": 360, "nameDestX": 12, "nameDestY": 0},
                {"name": "port", "segment": 1, "x": 142, "y": 0, "w": 22, "h": 59,
                 "destX": 22, "destY": 45, "hpX": 15, "hpY": 60, "nameY": 52,
                 "nameBreakWidth": 200, "nameDestX": 0, "nameDestY": 8},
                {"name": "aft", "segment": 2, "x": 74, "y": 0, "w": 68, "h": 14,
                 "destX": 34, "destY": 103, "hpX": 55, "hpY": 105, "nameY": 74,
                 "nameBreakWidth": 360, "nameDestX": 12, "nameDestY": 0},
            ]
        section_xml = []
        for seg in segs:
            section_xml.append(
                f'\t\t\t\t<ArmorSection name="{seg["name"]}" segment="{seg["segment"]}"\n'
                f'\t\t\t\t\t\timageID="&{ras};" imageX="{seg["x"]}" imageY="{seg["y"]}" '
                f'imageWidth="{seg["w"]}" imageHeight="{seg["h"]}"\n'
                f'\t\t\t\t\t\tdestX="{seg["destX"]}" destY="{seg["destY"]}" '
                f'hpX="{seg["hpX"]}" hpY="{seg["hpY"]}"\n'
                f'\t\t\t\t\t\tnameY="{seg["nameY"]}" nameBreakWidth="{seg["nameBreakWidth"]}" '
                f'nameDestX="{seg["nameDestX"]}" nameDestY="{seg["nameDestY"]}"/>'
            )
        player_hud = f'''\t\t\t<ArmorDisplay>
\t\t\t\t<ShipImage imageID="&{rah};" imageWidth="136" imageHeight="136"/>
{chr(10).join(section_xml)}
\t\t\t</ArmorDisplay>
\t\t\t<ShieldDisplay shieldLevelEffect="&{efsh};"/>'''
    else:
        player_hud = '''\t\t\t<!-- Unique HUD disabled: procedural circular hull + default shield -->
\t\t\t<ArmorDisplay style="circular" scale="hp"/>
\t\t\t<ShieldDisplay shieldLevelEffect="&efShieldHUDDefault;"/>'''

    # Masked shield-ring spritesheet overlay (swapout); optional
    swap = manifest.get("sheetSwapouts") or {}
    active_swap = swap.get("active") or {}
    shield_ov_path = files.get("shieldOverlaySheet") or active_swap.get("shieldSheet")
    shield_ov_mask = files.get("shieldOverlayMask") or active_swap.get("shieldMask")
    overlay_xml = ""
    overlay_events = ""
    if shield_ov_path and Path(str(shield_ov_path)).is_file():
        so_rel = _rel(str(shield_ov_path), out_dir)
        so_mask_rel = _rel(str(shield_ov_mask), out_dir) if shield_ov_mask else None
        entities.extend(
            [
                (rso, _hex_unid("ship", name, "shieldOverlay")),
                (ovs, _hex_unid("ship", name, "shieldOverlayType")),
            ]
        )
        so_bit = f' bitmask="{so_mask_rel}"' if so_mask_rel else ""
        hud_images += f'''
\t<!-- Shield effect spritesheet (masked ring overlay; family={active_swap.get("shieldFamily") or "deflector"}) -->
\t<Image UNID="&{rso};" bitmap="{so_rel}"{so_bit} loadOnUse="true"/>
'''
        overlay_xml = f'''
\t<OverlayType UNID="&{ovs};" attributes="aamt, effect, shield">
\t\t<Image imageID="&{rso};" imageWidth="{fw}" imageHeight="{fh}" rotationCount="{facings}" rotationColumns="{columns}"/>
\t\t<Effect>
\t\t\t<Image imageID="&{rso};" imageWidth="{fw}" imageHeight="{fh}" rotationCount="{facings}" rotationColumns="{columns}"/>
\t\t</Effect>
\t</OverlayType>
'''
        overlay_events = f'''
\t\t<Events>
\t\t\t<OnCreate>
\t\t\t\t(objAddOverlay gSource &{ovs};)
\t\t\t</OnCreate>
\t\t</Events>
'''

    body = f'''{mesh_note}\t<!-- HD rotation sheet ({facings} facings, {columns} cols, {fw}px) source={rot_source} -->
\t<Image UNID="&{rs};"{sheet_bitmap}{sheet_bitmask} loadOnUse="true"/>{hero_img_tag}{hud_images}{shield_effect_xml}{overlay_xml}
\t<!-- ShipClass — Sapphire yacht hull + StdPlayerShips playerClass/shipBroker -->
\t<ShipClass UNID="&{sc};"
\t\t\tmanufacturer=\t\t"AAMT"
\t\t\tclass=\t\t\t\t"{display}"
\t\t\ttype=\t\t\t\t"yacht"
\t\t\tdefaultSovereign=\t"&svCommonwealth;"
\t\t\tlevel=\t\t\t\t"{level}"
\t\t\tattributes=\t\t\t"aamt, commonwealth, playerClass, shipBroker, genericClass"
\t\t\tinherit=\t\t\t"&baHumanTechShip;"
\t\t\t>

\t\t<Hull
\t\t\tsize=\t\t\t\t"{size}"
\t\t\tmass=\t\t\t\t"{mass}"
\t\t\tcargoSpace=\t\t\t"{cargo}"
\t\t\tmaxReactorPower=\t"10000"
\t\t\tmaxCargoSpace=\t\t"{max(cargo, cargo * 2)}"
\t\t\tmaxDevices=\t\t\t"8"
\t\t\tmaxArmor=\t\t\t"heavy"
\t\t\tstdArmor=\t\t\t"medium"
\t\t\t/>

\t\t<Drive
\t\t\tmaxSpeed=\t\t\t"{max_speed}"
\t\t\tthrust=\t\t\t\t"{thrust}"
\t\t\tpowerUse=\t\t\t"20"
\t\t\t/>

\t\t<Maneuver
\t\t\tmaxRotationRate=\t"{turn:.1f}"
\t\t\trotationAccel=\t\t"{max(1.0, turn / 4):.1f}"
\t\t\trotationStopAccel=\t"{turn:.1f}"
\t\t\t/>

\t\t<DeviceSlots>
\t\t\t<DeviceSlot criteria="w +property:omnidirectional;" posAngle="0" posRadius="{max(8, size // 3)}"/>
\t\t\t<DeviceSlot criteria="w" posAngle="0" posRadius="{max(12, size // 2)}"/>
\t\t</DeviceSlots>

\t\t<Armor
\t\t\tarmorID=\t\t\t"&{armor_entity};"
\t\t\tcount=\t\t\t\t"4"
\t\t\t/>

\t\t<Devices>
\t\t\t<Device deviceID="&itRecoillessCannon;"/>
\t\t\t<Device deviceID="&{shield_entity};"/>
\t\t</Devices>

\t\t<Items>
\t\t\t<Item count="4d6" item="&itHelium3FuelRod;"/>
\t\t</Items>

\t\t<Image imageID="&{rs};" imageWidth="{fw}" imageHeight="{fh}" rotationCount="{facings}" rotationColumns="{columns}" viewportRatio="{viewport:.5f}"/>
\t\t<HeroImage imageID="{hero_ship_image}" imageWidth="{hw}" imageHeight="{hh}"/>

\t\t<Effects>
\t\t\t<Effect type="thrustMain" posAngle="160" posRadius="{max(4, size // 6)}" posZ="0" rotation="180" bringToFront="*"/>
\t\t\t<Effect type="thrustMain" posAngle="-160" posRadius="{max(4, size // 6)}" posZ="0" rotation="180" bringToFront="*"/>
\t\t</Effects>
{overlay_events}
\t\t<!-- initialClass: new-game picker; playerClass/shipBroker: mid-game broker -->
\t\t<PlayerSettings
\t\t\tdesc=\t\t\t\t"{theme.replace(chr(34), "'")}"
\t\t\tlargeImage=\t\t\t"{large_ref}"
\t\t\tinitialClass=\t\t"true"
\t\t\tstartingCredits=\t"5d20+250"
\t\t\tsortOrder=\t\t\t"90"
\t\t\t>
{player_hud}
\t\t</PlayerSettings>
\t</ShipClass>
'''

    path = out_dir / f"{name}_ship_transcendence.xml"
    return _write_tx_extension(
        path,
        pack_entity=pack,
        pack_hex=_hex_unid("ship", name, "pack"),
        display_name=f"AAMT {display}",
        entities=entities,
        body=body,
    )


def write_unity_json_def(
    out_dir: Path,
    *,
    kind: str,
    name: str,
    theme: str,
    system: str,
    manifest: Dict[str, Any],
    spec: Dict[str, Any],
) -> Path:
    files = manifest.get("files") or {}
    defn = {
        "schema": "aamt.game_asset.v1",
        "kind": kind,
        "id": name,
        "displayName": _display_name(name, theme),
        "theme": theme,
        "system": system,
        "resourcesPath": f"{system}/{'Spells' if kind=='spell' else 'Projectiles' if kind=='projectile' else 'Ships'}/{name}",
        "assets": {
            "icon": _rel(files.get("icon") or files.get("sprite"), out_dir),
            "sprite": _rel(files.get("sprite"), out_dir),
            "fxFrames": _rel_list(files.get("fx"), out_dir),
            "projectileFrames": _rel_list(files.get("projectile") or files.get("frames"), out_dir),
            "frames": _rel_list(files.get("frames"), out_dir),
            "mesh": _rel(files.get("mesh"), out_dir),
        },
        "stats": _stats_for(kind, {**spec, "theme": theme}),
        "spec": {
            "shape": spec.get("shape"),
            "colors": spec.get("colors"),
            "glow": spec.get("glow"),
            "pattern": spec.get("pattern"),
        },
    }
    # Drop nulls in assets
    defn["assets"] = {k: v for k, v in defn["assets"].items() if v}
    path = out_dir / f"{name}_def.json"
    path.write_text(json.dumps(defn, indent=2), encoding="utf-8")
    return path


def write_elin_ability_stub(
    out_dir: Path,
    *,
    name: str,
    theme: str,
    system: str,
    manifest: Dict[str, Any],
    spec: Dict[str, Any],
) -> Path:
    """
    Elin-facing ability stub aligned to decompiled SourceElement.Row
    (G:\\Elin_decompiled_source\\Elin\\SourceElement.cs).

    Icons in-game resolve via:
      SpriteSheet.Get("Media/Graphics/Icon/Element/icon_ability", alias)

    Runtime casting uses ACT.Create(row) where row.group is SPELL/ABILITY and
    row.type selects the Act class (default "Spell"). proc[0] is an EffectId name.
    """
    files = manifest.get("files") or {}
    stats = _stats_for("spell", {**spec, "theme": theme})
    display = _display_name(name, theme)
    alias = "Sp" + re.sub(r"[^A-Za-z0-9]", "", name)
    if not alias.startswith("Sp") or len(alias) < 3:
        alias = "SpAamt" + re.sub(r"[^A-Za-z0-9]", "", name)
    # High id band to avoid vanilla SPELL.* constants (e.g. bolt_Fire=50300)
    dig = int(hashlib.md5(alias.encode("utf-8")).hexdigest()[:6], 16)
    eid = 920000 + (dig % 70000)

    element = _guess_element(theme)
    # Map element hint -> EffectId-ish proc used by Act.Perform / ActEffect.ProcAt
    proc_map = {
        "Fire": "Arrow",
        "Cold": "Arrow",
        "Nature": "Arrow",
        "Lightning": "Bolt",
        "Arcane": "Magic",
        "Dark": "Miasma",
        "Holy": "Holy",
    }
    proc0 = proc_map.get(element, "Arrow")
    mana = int(stats.get("manaCost", 8))
    cd = int(round(float(stats.get("cooldownSec", 3.0))))

    row = {
        "schema": "aamt.elin_source_element.v1",
        "notes": {
            "from": "Elin SourceElement.Row",
            "iconSheet": "Media/Graphics/Icon/Element/icon_ability",
            "iconKey": alias,
            "actCreate": "ACT.Create(row) / ClassCache.Create<Act>(type)",
        },
        "row": {
            "id": eid,
            "alias": alias,
            "name": display,
            "name_JP": display,
            "altname": "",
            "altname_JP": "",
            "aliasParent": "",
            "aliasRef": "",
            "aliasMtp": "",
            "parentFactor": 1.0,
            "lvFactor": 10,
            "encFactor": 0,
            "encSlot": "",
            "mtp": 1,
            "LV": 1,
            "chance": 100,
            "value": int(stats.get("damage", 12)),
            "cost": [mana],
            "geneSlot": 0,
            "sort": eid,
            "target": "Enemy",
            "proc": [proc0],
            "type": "Spell",
            "group": "SPELL",
            "category": "ability",
            "categorySub": "spell",
            "abilityType": ["attack"],
            "tag": ["aamt", system.lower()],
            "thing": "",
            "eleP": 100,
            "cooldown": max(0, cd),
            "charge": 15,
            "radius": float(stats.get("range", 6)),
            "max": 0,
            "req": [],
            "idTrainer": "",
            "partySkill": 0,
            "tagTrainer": "",
            "detail": theme,
            "detail_JP": theme,
            "textPhase": display,
            "textPhase_JP": display,
        },
        "assets": {
            "iconPath": _rel(files.get("icon"), out_dir),
            "fxPaths": _rel_list(files.get("fx"), out_dir),
            "projectilePaths": _rel_list(files.get("projectile"), out_dir),
            "meshPath": _rel(files.get("mesh"), out_dir),
            "elinIconInstall": f"Media/Graphics/Icon/Element/icon_ability/{alias}.png",
        },
        "system": system,
        "elementHint": element,
        "aamtPower": stats.get("damage", 12),
    }

    path = out_dir / f"{name}_elin_ability.json"
    path.write_text(json.dumps(row, indent=2), encoding="utf-8")

    # TSV one-liner for pasting into elements.xlsx-style sheets (common columns)
    tsv = out_dir / f"{name}_elin_element.tsv"
    cols = [
        str(eid),
        alias,
        display,
        display,
        "",
        "",
        "",
        "",
        "",
        "1",
        "10",
        "0",
        "",
        "1",
        "1",
        "100",
        str(int(stats.get("damage", 12))),
        str(mana),
        "0",
        str(eid),
        "Enemy",
        proc0,
        "Spell",
        "SPELL",
        "ability",
        "spell",
        "attack",
        "aamt",
        "",
        "100",
        str(max(0, cd)),
        "0",
        str(stats.get("range", 6)),
        theme.replace("\t", " "),
    ]
    header = "\t".join(
        [
            "id",
            "alias",
            "name",
            "name_JP",
            "altname",
            "altname_JP",
            "aliasParent",
            "aliasRef",
            "aliasMtp",
            "parentFactor",
            "lvFactor",
            "encFactor",
            "encSlot",
            "mtp",
            "LV",
            "chance",
            "value",
            "cost",
            "geneSlot",
            "sort",
            "target",
            "proc",
            "type",
            "group",
            "category",
            "categorySub",
            "abilityType",
            "tag",
            "thing",
            "eleP",
            "cooldown",
            "charge",
            "radius",
            "detail",
        ]
    )
    tsv.write_text(header + "\n" + "\t".join(cols) + "\n", encoding="utf-8")

    # Copy icon into Elin Media path beside the pack for mod authors
    icon_src = files.get("icon")
    if icon_src and Path(icon_src).exists():
        dest = out_dir / "Media" / "Graphics" / "Icon" / "Element" / "icon_ability" / f"{alias}.png"
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            import shutil

            shutil.copy2(icon_src, dest)
        except Exception:
            pass

    return path


def _guess_element(theme: str) -> str:
    t = theme.lower()
    for key, el in (
        ("fire", "Fire"),
        ("flame", "Fire"),
        ("ice", "Cold"),
        ("frost", "Cold"),
        ("verdant", "Nature"),
        ("nature", "Nature"),
        ("life", "Nature"),
        ("plasma", "Lightning"),
        ("lightning", "Lightning"),
        ("arcane", "Arcane"),
        ("shadow", "Dark"),
        ("holy", "Holy"),
    ):
        if key in t:
            return el
    return "Arcane"


def _prettify_xml(elem: Element) -> str:
    rough = tostring(elem, encoding="unicode")
    pretty = minidom.parseString(rough).toprettyxml(indent="  ")
    # Transcendence expects &entity; not &amp;entity;
    pretty = re.sub(r'(UNID|unid)="&amp;([^"]+)"', r'\1="&\2"', pretty)
    return pretty


def assemble_ship_manifest_from_pack(pack_dir: Path, name: str) -> Dict[str, Any]:
    """Rebuild a ship manifest from on-disk art + Alt HUD/swapout sidecars."""
    pack_dir = Path(pack_dir)
    files: Dict[str, Any] = {}
    for key, rel in [
        ("spritesheet", f"{name}.jpg"),
        ("spritesheetMask", f"{name}Mask.bmp"),
        ("hero", f"{name}Large.jpg"),
        ("heroMask", f"{name}LargeMask.bmp"),
        ("mesh", f"Source/Models/{name}.fbx"),
        ("armorHudShip", f"{name}ArmorHUDShip.jpg"),
        ("armorHudShipMask", f"{name}ArmorHUDShipMask.bmp"),
        ("armorHudSegments", f"{name}ArmorHUDSegments.bmp"),
        ("shieldsHud", f"{name}ShieldsHUD.jpg"),
        ("shieldsHudMask", f"{name}ShieldsHUDMask.bmp"),
        ("hudJson", f"{name}_hud.json"),
    ]:
        p = pack_dir / rel
        if p.is_file():
            files[key] = str(p)
    if files.get("spritesheet"):
        files["sprite"] = files["spritesheet"]

    unique: Dict[str, Any] = {}
    hud_json = pack_dir / f"{name}_hud.json"
    if hud_json.is_file():
        try:
            unique = json.loads(hud_json.read_text(encoding="utf-8"))
        except Exception:
            unique = {"enabled": bool(files.get("armorHudShip"))}
    elif files.get("armorHudShip"):
        unique = {"enabled": True}

    swap: Dict[str, Any] = {}
    swap_json = pack_dir / "Source" / "Models" / "Alt" / "Sheets" / "manifest.json"
    if swap_json.is_file():
        try:
            swap = json.loads(swap_json.read_text(encoding="utf-8"))
        except Exception:
            swap = {}
    active = (swap.get("active") or {}) if isinstance(swap, dict) else {}
    if active.get("shieldSheet"):
        files["shieldOverlaySheet"] = active["shieldSheet"]
    if active.get("shieldMask"):
        files["shieldOverlayMask"] = active["shieldMask"]
    if active.get("hullSheet"):
        files["hullSwapSheet"] = active["hullSheet"]

    rot = {
        "facings": int((swap.get("facings") if swap else None) or 120),
        "columns": int((swap.get("columns") if swap else None) or 12),
        "frame_width": 128,
        "frame_height": 128,
        "source": "pack",
    }
    if isinstance(swap.get("frame"), list) and len(swap["frame"]) >= 2:
        rot["frame_width"] = int(swap["frame"][0])
        rot["frame_height"] = int(swap["frame"][1])

    return {
        "files": files,
        "uniqueHud": unique,
        "sheetSwapouts": swap,
        "shipRotation": rot,
    }


def rewrite_ship_defs_from_pack(
    pack_dir: Path,
    name: str,
    *,
    theme: str = "",
    spec: Optional[Dict[str, Any]] = None,
) -> Path:
    """Rewrite Transcendence ship XML from pack folder contents."""
    man = assemble_ship_manifest_from_pack(pack_dir, name)
    return write_transcendence_ship_xml(
        Path(pack_dir),
        name=name,
        theme=theme or name,
        manifest=man,
        spec=dict(spec or {}),
    )


def write_defs_for_pack(
    out_dir: Path,
    *,
    kind: str,
    name: str,
    theme: str,
    system: str,
    manifest: Dict[str, Any],
    spec: Dict[str, Any],
) -> Dict[str, str]:
    written: Dict[str, str] = {}
    unity = write_unity_json_def(
        out_dir, kind=kind, name=name, theme=theme, system=system, manifest=manifest, spec=spec
    )
    written["unity"] = str(unity)

    if kind == "spell":
        elin = write_elin_ability_stub(
            out_dir, name=name, theme=theme, system=system, manifest=manifest, spec=spec
        )
        written["elin"] = str(elin)
    if kind == "projectile":
        tx = write_transcendence_projectile_xml(
            out_dir, name=name, theme=theme, manifest=manifest, spec=spec
        )
        written["transcendence"] = str(tx)
    if kind == "ship":
        tx = write_transcendence_ship_xml(
            out_dir, name=name, theme=theme, manifest=manifest, spec=spec
        )
        written["transcendence"] = str(tx)
    return written


def _cli_elin_ability_from_folder(
    out_dir: Path,
    *,
    name: str,
    theme: str,
    system: str = "Elin",
) -> Path:
    """Write *_elin_ability.json for an existing ElinSpellAssetGenerator folder."""
    files: Dict[str, Any] = {}
    icons = sorted((out_dir / "icons").glob("*.png")) if (out_dir / "icons").is_dir() else []
    if icons:
        files["icon"] = str(icons[0])
    fx = sorted((out_dir / "fx").glob("*.png")) if (out_dir / "fx").is_dir() else []
    if fx:
        files["fx"] = [str(p) for p in fx]
    projs = (
        sorted((out_dir / "projectiles").glob("*.png"))
        if (out_dir / "projectiles").is_dir()
        else []
    )
    if projs:
        files["projectile"] = [str(p) for p in projs]
    return write_elin_ability_stub(
        out_dir,
        name=name,
        theme=theme,
        system=system,
        manifest={"files": files},
        spec={},
    )


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="AAMT gameplay def helpers")
    ap.add_argument(
        "--elin-ability-from-folder",
        action="store_true",
        help="Write *_elin_ability.json from an existing spell asset folder",
    )
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--theme", default="")
    ap.add_argument("--system", default="Elin")
    args = ap.parse_args()
    if args.elin_ability_from_folder:
        theme = args.theme or args.name
        path = _cli_elin_ability_from_folder(
            Path(args.out_dir), name=args.name, theme=theme, system=args.system
        )
        print(path)
    else:
        raise SystemExit("Specify --elin-ability-from-folder")
