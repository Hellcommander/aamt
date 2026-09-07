"""Content repairs for workshop packs that wipe vanilla JSON or overlay global atlases.

MiningPlus, Darken's Arcane Materials, Natural Resource Plus, Better Weaponsmith.
Mechanical 0.10 scan does not catch these. Hooked from s2_fix_mod scan/upgrade.
"""

from __future__ import annotations

import shutil
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from s2_buildings import _load_json, _write_json
from s2_paths import core2_dir, workshop_root

MININGPLUS = "3352367788"
DARKEN = "3229736001"
NRP = "3559400101"
WEAPONSMITH = "3557698099"
SANDMANCY = "3736940267"
DRAKEN = "3509134344"
DEMONOLOGY = "3495517925"

CONTENT_FIX_IDS = {MININGPLUS, DARKEN, NRP, WEAPONSMITH, SANDMANCY, DRAKEN, DEMONOLOGY}

CULT_HIDEOUT_ALIASES = (
    "Cult_Hideout_I",
    "Cult_Hideout_II",
    "Cult_Hideout_III",
    "Cult_Hideout_IV",
    "Cult_Hideout_V",
    "Cult_Hideout_VI",
    "Cult_Hideout_VII",
    "Cult_Hideout_VIII",
    "Cult_Hideout_IX",
    "Cult_Hideout_X",
    "Cult_Hideout_XI",
    "Cult_Hideout_XII",
    "Cult_Hideout_XIII",
    "Cult_Hideout_XIV",
)

_CORE_ENTITIES: Optional[Dict[str, Dict[str, Any]]] = None
_CORE_MILESTONES: Optional[Set[str]] = None
_CORE_RACES: Optional[Dict[str, Dict[str, Any]]] = None

RACE_KEEP = ("id", "name", "description", "passives", "abilities")
RACE_CRASH_KEYS = ("ages", "base_entities", "playable", "statistics", "tags", "names")


def _load_optional(path: Path) -> Any:
    if not path.is_file():
        return None
    try:
        return _load_json(path)
    except Exception:
        return None


def _core_entities() -> Dict[str, Dict[str, Any]]:
    global _CORE_ENTITIES
    if _CORE_ENTITIES is not None:
        return _CORE_ENTITIES
    found: Dict[str, Dict[str, Any]] = {}
    edir = core2_dir() / "entities"
    if edir.is_dir():
        for path in edir.glob("*.json"):
            try:
                data = _load_json(path)
            except Exception:
                continue
            if isinstance(data, dict) and data.get("id") is not None:
                found[str(data["id"])] = data
    _CORE_ENTITIES = found
    return found


def _core_races() -> Dict[str, Dict[str, Any]]:
    global _CORE_RACES
    if _CORE_RACES is not None:
        return _CORE_RACES
    found: Dict[str, Dict[str, Any]] = {}
    data = _load_optional(core2_dir() / "character.json")
    if isinstance(data, dict):
        for race in data.get("races") or []:
            if isinstance(race, dict) and race.get("id") is not None:
                found[str(race["id"])] = race
    _CORE_RACES = found
    return found


def _core_milestones() -> Set[str]:
    global _CORE_MILESTONES
    if _CORE_MILESTONES is not None:
        return _CORE_MILESTONES
    found: Set[str] = set()
    mdir = core2_dir() / "milestones"
    if mdir.is_dir():
        for path in mdir.rglob("*.json"):
            try:
                data = _load_json(path)
            except Exception:
                continue
            if isinstance(data, dict) and data.get("id") is not None:
                found.add(str(data["id"]))
    _CORE_MILESTONES = found
    return found


def _mod_identity(folder: Path) -> Tuple[str, str]:
    folder = Path(folder)
    mj = folder / "mod.json"
    mod = _load_optional(mj) if mj.is_file() else {}
    if not isinstance(mod, dict):
        mod = {}
    sid = str(mod.get("steam_publish_id") or folder.name)
    name = str(mod.get("name") or "").lower()
    return sid, name


def _bump_version(folder: Path, version: str) -> List[str]:
    path = folder / "mod.json"
    mod = _load_optional(path)
    if not isinstance(mod, dict):
        return []
    if str(mod.get("version") or "") == version:
        return []
    mod["version"] = version
    _write_json(path, mod)
    return [f"version={version}"]


def _ensure_component(entity: Dict[str, Any], name: str) -> None:
    comps = list(entity.get("components") or [])
    if name not in comps:
        comps.append(name)
        entity["components"] = comps


def _drop_orphan_consumer(entity: Dict[str, Any]) -> None:
    comps = list(entity.get("components") or [])
    if "consumer" in comps and not isinstance(entity.get("consumer"), dict):
        entity["components"] = [c for c in comps if c != "consumer"]


def is_miningplus(folder: Path) -> bool:
    sid, name = _mod_identity(folder)
    return sid == MININGPLUS or name == "miningplus"


def is_darken(folder: Path) -> bool:
    sid, name = _mod_identity(folder)
    return sid == DARKEN or "arcane materials" in name


def is_nrp(folder: Path) -> bool:
    sid, name = _mod_identity(folder)
    return sid == NRP or name == "natural resource plus"


def is_better_weaponsmith(folder: Path) -> bool:
    sid, name = _mod_identity(folder)
    return sid == WEAPONSMITH or name == "better weaponsmith"


def is_sandmancy(folder: Path) -> bool:
    sid, name = _mod_identity(folder)
    return sid == SANDMANCY or name == "sandmancy"


def is_draken(folder: Path) -> bool:
    sid, name = _mod_identity(folder)
    return sid == DRAKEN or "draken races" in name


def is_demonology(folder: Path) -> bool:
    sid, name = _mod_identity(folder)
    return sid == DEMONOLOGY or name == "demonology"


def content_fixer_for(folder: Path):
    if is_miningplus(folder):
        return scan_miningplus, fix_miningplus
    if is_darken(folder):
        return scan_darken, fix_darken
    if is_nrp(folder):
        return scan_nrp, fix_nrp
    if is_better_weaponsmith(folder):
        return scan_weaponsmith, fix_weaponsmith
    if is_sandmancy(folder):
        return scan_sandmancy, fix_sandmancy
    if is_draken(folder):
        return scan_draken, fix_draken
    if is_demonology(folder):
        return scan_demonology, fix_demonology
    return None, None


# --- MiningPlus ----------------------------------------------------------------


def _producer_ids(entity: Dict[str, Any]) -> Set[str]:
    out: Set[str] = set()
    prod = entity.get("producer") or {}
    if not isinstance(prod, dict):
        return out
    for rows in (prod.get("products") or {}).values():
        for row in rows or []:
            if isinstance(row, dict) and row.get("id"):
                out.add(str(row["id"]))
    return out


def _overlay_wipes_vanilla(vanilla: Dict[str, Any], overlay: Dict[str, Any]) -> List[str]:
    hits: List[str] = []
    lost = _producer_ids(vanilla) - _producer_ids(overlay)
    if lost:
        hits.append("drops loot " + ", ".join(sorted(lost)[:6]))
    if vanilla.get("durability") and not overlay.get("durability"):
        hits.append("strips durability")
    if (vanilla.get("food") or {}).get("poisonous") is not None and (overlay.get("food") or {}).get("poisonous") is None:
        hits.append("strips poisonous")
    vcomps = set(vanilla.get("components") or [])
    ocomps = set(overlay.get("components") or [])
    if "armor" in vcomps and "weapon" in vcomps and ("armor" not in ocomps or "weapon" not in ocomps):
        hits.append("strips armor/weapon resource")
    return hits


def scan_miningplus(folder: Path) -> List[str]:
    folder = Path(folder)
    issues: List[str] = []
    core = _core_entities()
    edir = folder / "entities"
    seen_ids: Dict[str, str] = {}
    if edir.is_dir():
        for path in sorted(edir.glob("*.json")):
            ent = _load_optional(path)
            if not isinstance(ent, dict) or ent.get("id") is None:
                continue
            eid = str(ent["id"])
            if eid in seen_ids:
                issues.append(f"duplicate entity id {eid} ({seen_ids[eid]} vs {path.name})")
            else:
                seen_ids[eid] = path.name
            vanilla = core.get(eid)
            if not vanilla:
                continue
            wipes = _overlay_wipes_vanilla(vanilla, ent)
            if wipes:
                issues.append(f"{path.name}: {'; '.join(wipes)}")
    miles: Dict[str, str] = {}
    mdir = folder / "milestones"
    if mdir.is_dir():
        for path in sorted(mdir.rglob("*.json")):
            row = _load_optional(path)
            if not isinstance(row, dict) or row.get("id") is None:
                continue
            mid = str(row["id"])
            if mid in miles:
                issues.append(f"duplicate milestone id {mid} ({miles[mid]} vs {path.name})")
            else:
                miles[mid] = path.name
    oven = _load_optional(folder / "milestones" / "adventuring" / "oven.json")
    if isinstance(oven, dict):
        rewards = [str((r or {}).get("recipe") or "") for r in oven.get("rewards") or [] if isinstance(r, dict)]
        if any(r in {"core_2_2256", "2256"} for r in rewards):
            issues.append("oven.json re-grants vanilla dirt furnace (already Dirt_Furnace.json)")
    return issues


def _merge_vanilla_entity(vanilla: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
    out = deepcopy(vanilla)
    prod = overlay.get("producer")
    if isinstance(prod, dict):
        existing = out.setdefault("producer", {"products": {}, "time": prod.get("time", 10)})
        if isinstance(existing, dict):
            if prod.get("delay_on_use") is not None:
                existing["delay_on_use"] = prod.get("delay_on_use")
            products = existing.setdefault("products", {})
            for action, rows in (prod.get("products") or {}).items():
                bucket = products.setdefault(str(action), [])
                have = {str(p.get("id")) for p in bucket if isinstance(p, dict)}
                for row in rows or []:
                    if not isinstance(row, dict):
                        continue
                    pid = str(row.get("id") or "")
                    if not pid or pid in have:
                        continue
                    bucket.append(deepcopy(row))
                    have.add(pid)
        _ensure_component(out, "producer")
    if overlay.get("usable") and not vanilla.get("usable"):
        out["usable"] = deepcopy(overlay["usable"])
        _ensure_component(out, "usable")
    oc = overlay.get("craftable") or {}
    vc = out.get("craftable") or {}
    if isinstance(oc, dict) and isinstance(vc, dict):
        try:
            if int(oc.get("magic_slots") or 0) > int(vc.get("magic_slots") or 0):
                vc["magic_slots"] = oc.get("magic_slots")
                out["craftable"] = vc
        except (TypeError, ValueError):
            pass
    ot = overlay.get("tool")
    vt = out.get("tool")
    if isinstance(ot, list) and isinstance(vt, list) and ot and vt:
        oq = int((ot[0] or {}).get("quality") or 0) if isinstance(ot[0], dict) else 0
        vq = int((vt[0] or {}).get("quality") or 0) if isinstance(vt[0], dict) else 0
        if oq > vq:
            vt[0]["quality"] = oq
    return out


def fix_miningplus(folder: Path) -> List[str]:
    folder = Path(folder)
    notes: List[str] = []
    core = _core_entities()
    edir = folder / "entities"
    if edir.is_dir():
        animalia = edir / "Animalia_Bones.json"
        if animalia.is_file():
            animalia.unlink()
            notes.append("dropped duplicate Animalia_Bones.json (id 9955)")
        for path in sorted(edir.glob("*.json")):
            ent = _load_optional(path)
            if not isinstance(ent, dict) or ent.get("id") is None:
                continue
            eid = str(ent["id"])
            vanilla = core.get(eid)
            if not vanilla:
                continue
            merged = _merge_vanilla_entity(vanilla, ent)
            _write_json(path, merged)
            notes.append(f"{path.name}: merged extras onto vanilla {eid}")
    oven = folder / "milestones" / "adventuring" / "oven.json"
    if oven.is_file():
        oven.unlink()
        notes.append("dropped oven.json (duplicate dirt furnace grant)")
    tin = folder / "milestones" / "adventuring" / "Tin_ingot.json"
    row = _load_optional(tin)
    if isinstance(row, dict) and str(row.get("id") or "") == "Tin_ingot":
        row["id"] = "MiningPlus_Tin_Ingot"
        row["name"] = "Tin Ingot"
        _write_json(tin, row)
        notes.append("Tin_ingot.json id -> MiningPlus_Tin_Ingot")
    notes.extend(_bump_version(folder, "0.2.1"))
    return notes


# --- Darken Arcane Materials ---------------------------------------------------


def scan_darken(folder: Path) -> List[str]:
    folder = Path(folder)
    issues: List[str] = []
    assets = _load_optional(folder / "assets.json") or {}
    sheets = ((assets.get("graphics") or {}).get("tilesheets") or []) if isinstance(assets, dict) else []
    for sheet in sheets:
        if isinstance(sheet, dict) and str(sheet.get("name") or "") in {"items", "glyph32", "buildings", "particles32"}:
            issues.append(f"assets.json overlays {sheet.get('name')} (tiny custom sheet steals vanilla art)")
    return issues


def _tint_frames(frames: List[Any], color: List[int]) -> List[Any]:
    out = []
    for frame in frames:
        if not isinstance(frame, dict):
            continue
        row = deepcopy(frame)
        row["color"] = list(color)
        out.append(row)
    return out


def fix_darken(folder: Path) -> List[str]:
    folder = Path(folder)
    notes: List[str] = []
    assets = folder / "assets.json"
    if assets.is_file():
        assets.unlink()
        notes.append("dropped assets.json (items/glyph32 overlays)")
    steel = folder / "entities" / "Spellsteel_Ingot.json"
    ent = _load_optional(steel)
    if isinstance(ent, dict):
        ent["item"] = dict(ent.get("item") or {})
        ent["item"]["image"] = 56
        ent["glyph"] = {
            "frames": [{"color": [151, 142, 255], "delay": 0, "index": 277}],
            "random_frame_start": False,
        }
        _write_json(steel, ent)
        notes.append("Spellsteel_Ingot: vanilla steel bar 56/277")
    rune = folder / "entities" / "Rune_of_Magic.json"
    ent = _load_optional(rune)
    if isinstance(ent, dict):
        ent["item"] = dict(ent.get("item") or {})
        ent["item"]["image"] = 1040
        ent["glyph"] = {
            "frames": [{"color": [100, 109, 155], "delay": 0, "index": 2373}],
            "random_frame_start": False,
        }
        _write_json(rune, ent)
        notes.append("Rune_of_Magic: vanilla rune 1040/2373")
    circle = folder / "entities" / "Ritual_Circle.json"
    ent = _load_optional(circle)
    glowing = _core_entities().get("core_2_Glowing_Rune")
    if isinstance(ent, dict) and isinstance(glowing, dict):
        frames = (glowing.get("glyph") or {}).get("frames") or []
        ent["glyph"] = {
            "frames": _tint_frames(list(frames), [165, 83, 255]),
            "random_frame_start": False,
        }
        lit = ent.get("light_source")
        if isinstance(lit, dict):
            lit["lit_image"] = 806
        _write_json(circle, ent)
        notes.append("Ritual_Circle: vanilla glowing-rune glyphs 806–809")
    notes.extend(_bump_version(folder, "0.1.3"))
    return notes


# --- Natural Resource Plus -----------------------------------------------------


def scan_nrp(folder: Path) -> List[str]:
    folder = Path(folder)
    issues: List[str] = []
    data = _load_optional(folder / "natural_resources.json")
    if not isinstance(data, dict):
        return issues
    grass = data.get("grasslands") if isinstance(data.get("grasslands"), dict) else {}
    wheat = ((grass.get("wheat") or {}).get("entities") or []) if isinstance(grass.get("wheat"), dict) else []
    stone = ((grass.get("stone") or {}).get("entities") or []) if isinstance(grass.get("stone"), dict) else []
    wheat_ids = {str(e.get("id")) for e in wheat if isinstance(e, dict)}
    stone_ids = {str(e.get("id")) for e in stone if isinstance(e, dict)}
    if "core_2_Slate_Stone_Block" in wheat_ids:
        issues.append("grasslands wheat contains slate (belongs on stone)")
    if "core_2_Slate_Stone_Block" not in stone_ids:
        issues.append("grasslands stone is missing slate")
    return issues


def fix_nrp(folder: Path) -> List[str]:
    folder = Path(folder)
    path = folder / "natural_resources.json"
    data = _load_optional(path)
    if not isinstance(data, dict):
        return []
    grass = data.get("grasslands")
    if not isinstance(grass, dict):
        return []
    wheat = grass.get("wheat") if isinstance(grass.get("wheat"), dict) else None
    stone = grass.setdefault("stone", {"chance": 0.3, "entities": []})
    if not isinstance(stone, dict):
        return []
    wheat_ents = list((wheat or {}).get("entities") or [])
    stone_ents = list(stone.get("entities") or [])
    slate = None
    kept_wheat = []
    for row in wheat_ents:
        if isinstance(row, dict) and str(row.get("id") or "") == "core_2_Slate_Stone_Block":
            slate = row
            continue
        kept_wheat.append(row)
    if wheat is not None:
        wheat["entities"] = kept_wheat
    have_slate = any(isinstance(r, dict) and str(r.get("id") or "") == "core_2_Slate_Stone_Block" for r in stone_ents)
    if slate is not None and not have_slate:
        stone_ents.append(slate)
        stone["entities"] = stone_ents
    elif not have_slate:
        stone_ents.append({"chance": 1.0, "id": "core_2_Slate_Stone_Block", "rolls": 1, "weight": 0.5})
        stone["entities"] = stone_ents
    _write_json(path, data)
    notes = ["grasslands: slate moved from wheat to stone"]
    notes.extend(_bump_version(folder, "0.1.2"))
    return notes


# --- Better Weaponsmith --------------------------------------------------------


def _smith_files(folder: Path) -> List[Path]:
    edir = folder / "entities"
    if not edir.is_dir():
        return []
    return sorted(p for p in edir.glob("*.json") if "sign" not in p.name.lower() and "book" not in p.name.lower())


def scan_weaponsmith(folder: Path) -> List[str]:
    folder = Path(folder)
    issues: List[str] = []
    core = _core_entities()
    known = _core_milestones()
    edir = folder / "entities"
    if not edir.is_dir():
        return ["no entities"]
    have_vampire = False
    for path in _smith_files(folder):
        ent = _load_optional(path)
        if not isinstance(ent, dict):
            continue
        eid = str(ent.get("id") or "")
        if eid == "core_2_Vampire_Weaponsmith":
            have_vampire = True
        vanilla = core.get(eid)
        if not vanilla:
            continue
        vms = [str(x) for x in ((vanilla.get("skills") or {}).get("milestones") or [])]
        oms = [str(x) for x in ((ent.get("skills") or {}).get("milestones") or [])]
        missing = [m for m in vms if m not in oms]
        unknown = [m for m in oms if m not in known and m not in vms]
        dups = [m for i, m in enumerate(oms) if m in oms[:i]]
        vskills = [str(x) for x in ((vanilla.get("skills") or {}).get("skills") or [])]
        oskills = [str(x) for x in ((ent.get("skills") or {}).get("skills") or [])]
        lost_skills = [s for s in vskills if s not in oskills]
        if missing:
            issues.append(f"{path.name}: drops vanilla recipes {', '.join(missing)}")
        if unknown:
            issues.append(f"{path.name}: unknown milestone {', '.join(unknown)}")
        if dups:
            issues.append(f"{path.name}: duplicate {', '.join(dups)}")
        if lost_skills:
            issues.append(f"{path.name}: drops skills {', '.join(lost_skills)}")
    if "core_2_Vampire_Weaponsmith" in core and not have_vampire:
        issues.append("Vampire Weaponsmith not overlaid (0.10 race keeps the old 18-recipe kit)")
    return issues


def _union_smith(vanilla: Dict[str, Any], overlay: Optional[Dict[str, Any]], extras: List[str]) -> Dict[str, Any]:
    out = deepcopy(vanilla)
    known = _core_milestones()
    skills = out.setdefault("skills", {})
    merged: List[str] = []
    seen: Set[str] = set()
    overlay_ms = []
    overlay_skills = []
    if isinstance(overlay, dict):
        overlay_ms = [str(x) for x in ((overlay.get("skills") or {}).get("milestones") or [])]
        overlay_skills = [str(x) for x in ((overlay.get("skills") or {}).get("skills") or [])]
    vanilla_ms = [str(x) for x in (skills.get("milestones") or [])]
    vanilla_sk = [str(x) for x in (skills.get("skills") or [])]
    for mid in vanilla_ms:
        if not mid or mid in seen:
            continue
        merged.append(mid)
        seen.add(mid)
    for mid in overlay_ms + extras:
        if not mid or mid in seen:
            continue
        if mid not in known:
            continue
        merged.append(mid)
        seen.add(mid)
    skills["milestones"] = merged
    sk: List[str] = []
    sk_seen: Set[str] = set()
    for sid in vanilla_sk + overlay_skills:
        if sid and sid not in sk_seen:
            sk.append(sid)
            sk_seen.add(sid)
    skills["skills"] = sk
    _drop_orphan_consumer(out)
    return out


def _extra_milestones(vanilla: Dict[str, Any], overlay: Optional[Dict[str, Any]]) -> List[str]:
    known = _core_milestones()
    vset = {str(x) for x in ((vanilla.get("skills") or {}).get("milestones") or [])}
    extras: List[str] = []
    seen: Set[str] = set()
    if not isinstance(overlay, dict):
        return extras
    for mid in ((overlay.get("skills") or {}).get("milestones") or []):
        s = str(mid)
        if s in known and s not in vset and s not in seen:
            extras.append(s)
            seen.add(s)
    return extras


def fix_weaponsmith(folder: Path) -> List[str]:
    folder = Path(folder)
    notes: List[str] = []
    core = _core_entities()
    overlays: Dict[str, Tuple[Path, Dict[str, Any]]] = {}
    for path in _smith_files(folder):
        ent = _load_optional(path)
        if not isinstance(ent, dict) or ent.get("id") is None:
            continue
        overlays[str(ent["id"])] = (path, ent)
    for eid, (path, ent) in overlays.items():
        vanilla = core.get(eid)
        if not vanilla:
            continue
        merged = _union_smith(vanilla, ent, [])
        _write_json(path, merged)
        n = len((merged.get("skills") or {}).get("milestones") or [])
        notes.append(f"{path.name}: vanilla shell + extra recipes ({n})")
    vamp_src = core.get("core_2_Vampire_Weaponsmith")
    human = overlays.get("208", (None, None))[1]
    if isinstance(vamp_src, dict):
        merged = _union_smith(vamp_src, None, _extra_milestones(core.get("208") or vamp_src, human))
        _write_json(folder / "entities" / "Vampire_Weaponsmith.json", merged)
        notes.append("Vampire_Weaponsmith.json: 0.10 vampire kit + human extras")
    notes.extend(_bump_version(folder, "0.0.2"))
    return notes


def _fill_vanilla_race(overlay: Dict[str, Any], vanilla: Dict[str, Any]) -> List[str]:
    filled: List[str] = []
    for key, value in vanilla.items():
        if str(key).startswith("_") or key in RACE_KEEP:
            continue
        if key not in overlay:
            overlay[key] = deepcopy(value)
            filled.append(str(key))
    return filled


PROTECTED_ATLAS = {"particles32", "items", "glyph32", "buildings"}
# Always drop these: item.image / glyph frames have no sheet id, so a custom
# atlas under the vanilla name replaces core_2 art for the whole game.
STEAL_ATLAS = {"items", "glyph32"}
TINY_ATLAS_CELLS = 64
BOOK_ITEM_IMAGE = 777
BOOK_GLYPH_INDEX = 1946
GOLD_INGOT_IMAGE = 60
NECRO_BOOK_IMAGE = 776
NECRO_BOOK_GLYPH = 1979
DOCUMENT_NAME_HINTS = ("pact", "contract", "scroll", "tome", "grimoire", "infernal")

# Compact Demonology sheets (Geomancy-style named overlays). Tiny items /
# glyph32 strips steal vanilla art; expand those onto a full clone instead.
DEMONOLOGY_COMPACT_SHEETS = (
    {"name": "amplifiers", "tiles": [10, 1], "file": "assets/amplifiers.png"},
    {"name": "portraits", "tiles": [12, 12], "file": "assets/portrait_parts.png"},
    {"name": "skills", "tiles": [1, 1], "file": "assets/skills.png"},
    {"name": "passive_skills", "tiles": [4, 1], "file": "assets/passive_skills.png"},
    {"name": "world_tiles_locations", "tiles": [2, 1], "file": "assets/WorldTilesZoomedOverlay_Demon.png"},
    {"name": "abilities", "tiles": [10, 1], "file": "assets/abilities.png"},
)
DEMONOLOGY_PASSIVE_IMAGES = {
    "Shadowing_Demonic_Charisma": 0,
    "Shadowing_Demonic_Might": 1,
    "Shadowing_Demonic_Blood": 2,
    "Shadowing_Demonic_Might_II": 1,
    "Shadowing_Demon_Servant": 3,
}
DEMONOLOGY_PATCH_PNGS = ("amplifiers.png", "passive_skills.png")
STEAL_LEFTOVER_PNG = {
    "items": ("items_new.png",),
    "glyph32": ("glyphs_new.png",),
}
# Extra-row indexes into the expanded vanilla clone (tile 0 = first leftover cell).
DEMONOLOGY_EXPANDED_ART = {
    "Demonology_Infernal_pact_Imp": (0, 0),
    "demonology_Blood_Blessed": (1, 3),
}

_VANILLA_SHEETS: Optional[Dict[str, Dict[str, Any]]] = None

_VANILLA_ATLAS_CELLS: Optional[Dict[str, int]] = None


def _sheet_cells(sheet: Dict[str, Any]) -> int:
    tiles = sheet.get("tiles") or []
    if not isinstance(tiles, list) or not tiles:
        return 1
    try:
        cols = int(tiles[0])
        rows = int(tiles[1]) if len(tiles) > 1 else 1
        return max(1, cols) * max(1, rows)
    except (TypeError, ValueError):
        return 1


def _vanilla_sheet_info(name: str) -> Optional[Dict[str, Any]]:
    global _VANILLA_SHEETS
    if _VANILLA_SHEETS is None:
        found: Dict[str, Dict[str, Any]] = {}
        assets = _load_optional(core2_dir() / "assets.json") or {}
        for sheet in ((assets.get("graphics") or {}).get("tilesheets") or []):
            if not isinstance(sheet, dict):
                continue
            key = str(sheet.get("name") or "")
            tiles = sheet.get("tiles") or []
            if not key or not isinstance(tiles, list) or not tiles:
                continue
            try:
                cols = int(tiles[0])
                rows = int(tiles[1]) if len(tiles) > 1 else 1
            except (TypeError, ValueError):
                continue
            rel = str(sheet.get("file") or "").replace("\\", "/")
            found[key] = {
                "cols": max(1, cols),
                "rows": max(1, rows),
                "file": rel,
                "path": core2_dir().joinpath(*rel.split("/")),
            }
        _VANILLA_SHEETS = found
    return _VANILLA_SHEETS.get(name)


def _vanilla_atlas_cells() -> Dict[str, int]:
    global _VANILLA_ATLAS_CELLS
    if _VANILLA_ATLAS_CELLS is not None:
        return _VANILLA_ATLAS_CELLS
    found: Dict[str, int] = {}
    assets = _load_optional(core2_dir() / "assets.json") or {}
    for sheet in ((assets.get("graphics") or {}).get("tilesheets") or []):
        if not isinstance(sheet, dict):
            continue
        name = str(sheet.get("name") or "")
        if name:
            found[name] = _sheet_cells(sheet)
    _VANILLA_ATLAS_CELLS = found
    return found


def drop_protected_atlases(folder: Path, *, max_cells: int = TINY_ATLAS_CELLS) -> List[str]:
    """Drop vanilla-named tilesheets that are too small to replace core_2 safely.

    ``items`` / ``glyph32`` keep a full-size clone (custom tiles live in extra
    rows). Tiny strips still drop. Other protected atlases drop when they have
    fewer cells than vanilla.
    """
    path = Path(folder) / "assets.json"
    assets = _load_optional(path)
    if not isinstance(assets, dict):
        return []
    vanilla_cells = _vanilla_atlas_cells()
    sheets = ((assets.get("graphics") or {}).get("tilesheets") or [])
    kept: List[Any] = []
    dropped: List[str] = []
    for sheet in sheets:
        if not isinstance(sheet, dict):
            kept.append(sheet)
            continue
        name = str(sheet.get("name") or "")
        cells = _sheet_cells(sheet)
        limit = max(max_cells, vanilla_cells.get(name, max_cells))
        steal_tiny = name in STEAL_ATLAS and cells < limit
        other_tiny = name in PROTECTED_ATLAS and name not in STEAL_ATLAS and cells < limit
        if steal_tiny or other_tiny:
            dropped.append(f"{name}{cells}")
            continue
        kept.append(sheet)
    if not dropped:
        return []
    assets.setdefault("graphics", {})["tilesheets"] = kept
    _write_json(path, assets)
    return [f"dropped atlas overlay(s): {', '.join(dropped)}"]


def _pil_image():
    from PIL import Image

    return Image


def _unpack_strip(path: Path, tile: int) -> List[Any]:
    from s2_icon_pipeline import unpack_bottom_left

    src = _pil_image().open(path)
    cols = max(1, src.size[0] // max(1, tile))
    return unpack_bottom_left(path, cols=cols)


def _append_tiles_bottom_left(base, cols: int, tile: int, extras: Sequence[Any]):
    """Keep vanilla index 0 at bottom-left; extra tiles become a new top row."""
    Image = _pil_image()
    canvas = base.convert("RGBA") if hasattr(base, "convert") else base
    extra_rows = max(1, (len(extras) + cols - 1) // cols)
    w, h = canvas.size
    vanilla_rows = max(1, h // tile)
    rows = vanilla_rows + extra_rows
    out = Image.new("RGBA", (w, rows * tile), (0, 0, 0, 0))
    out.paste(canvas, (0, extra_rows * tile))
    for i, src in enumerate(extras):
        cell = src.convert("RGBA") if hasattr(src, "convert") else src
        if cell.size != (tile, tile):
            cell = cell.resize((tile, tile), Image.Resampling.NEAREST)
        gx = i % cols
        gy_from_bottom = vanilla_rows + (i // cols)
        py = (rows - 1 - gy_from_bottom) * tile
        out.paste(cell, (gx * tile, py), cell)
    return out


def _assets_sheets(folder: Path) -> List[Dict[str, Any]]:
    assets = _load_optional(Path(folder) / "assets.json") or {}
    sheets = ((assets.get("graphics") or {}).get("tilesheets") or []) if isinstance(assets, dict) else []
    return [s for s in sheets if isinstance(s, dict)]


def _expanded_custom_base(folder: Path, name: str) -> Optional[int]:
    info = _vanilla_sheet_info(name)
    if not info:
        return None
    vanilla_n = int(info["cols"]) * int(info["rows"])
    for sheet in _assets_sheets(folder):
        if str(sheet.get("name") or "") != name:
            continue
        if _sheet_cells(sheet) > vanilla_n:
            return vanilla_n
    return None


def tiny_steal_present(folder: Path) -> bool:
    vanilla = _vanilla_atlas_cells()
    for sheet in _assets_sheets(folder):
        name = str(sheet.get("name") or "")
        if name not in STEAL_ATLAS:
            continue
        limit = max(TINY_ATLAS_CELLS, vanilla.get(name, TINY_ATLAS_CELLS))
        if _sheet_cells(sheet) < limit:
            return True
    return False


def _steal_source_png(folder: Path, name: str) -> Optional[Path]:
    info = _vanilla_sheet_info(name)
    if not info:
        return None
    vanilla_n = int(info["cols"]) * int(info["rows"])
    folder = Path(folder)
    for sheet in _assets_sheets(folder):
        if str(sheet.get("name") or "") != name:
            continue
        if _sheet_cells(sheet) >= vanilla_n:
            return None
        rel = str(sheet.get("file") or "").replace("\\", "/")
        png = folder.joinpath(*rel.split("/"))
        if png.is_file():
            return png
    for fn in STEAL_LEFTOVER_PNG.get(name, ()):
        png = folder / "assets" / fn
        if png.is_file():
            return png
    return None


def _register_tilesheet(folder: Path, name: str, cols: int, rows: int, rel: str) -> None:
    path = Path(folder) / "assets.json"
    assets = _load_optional(path)
    if not isinstance(assets, dict):
        assets = {"graphics": {"tilesheets": []}}
    sheets = list((assets.setdefault("graphics", {})).get("tilesheets") or [])
    row = {"name": name, "tiles": [cols, rows], "file": rel}
    replaced = False
    for i, sheet in enumerate(sheets):
        if isinstance(sheet, dict) and str(sheet.get("name") or "") == name:
            sheets[i] = row
            replaced = True
            break
    if not replaced:
        sheets.append(row)
    assets["graphics"]["tilesheets"] = sheets
    _write_json(path, assets)


def _remap_expanded_entities(
    folder: Path,
    *,
    item_base: Optional[int],
    glyph_base: Optional[int],
    tiny_items: int = 0,
    tiny_glyphs: int = 0,
) -> List[str]:
    folder = Path(folder)
    edir = folder / "entities"
    if not edir.is_dir():
        return []
    core = _core_entities()
    notes: List[str] = []
    for path in sorted(edir.glob("*.json")):
        ent = _load_optional(path)
        if not isinstance(ent, dict):
            continue
        eid = str(ent.get("id") or "")
        want_item: Optional[int] = None
        want_glyph: Optional[int] = None
        if eid in DEMONOLOGY_EXPANDED_ART:
            i_off, g_off = DEMONOLOGY_EXPANDED_ART[eid]
            if item_base is not None and i_off is not None:
                want_item = item_base + int(i_off)
            if glyph_base is not None and g_off is not None:
                want_glyph = glyph_base + int(g_off)
        elif eid not in core:
            if item_base is not None and tiny_items and isinstance(ent.get("item"), dict):
                try:
                    img_n = int(ent["item"].get("image"))
                except (TypeError, ValueError):
                    img_n = -1
                if 0 <= img_n < tiny_items:
                    want_item = item_base + img_n
            if glyph_base is not None and tiny_glyphs:
                g_n = _glyph_index(ent)
                if g_n is not None and 0 <= g_n < tiny_glyphs:
                    want_glyph = glyph_base + g_n
        if want_item is None and want_glyph is None:
            continue
        cur_item = ent.get("item", {}).get("image") if isinstance(ent.get("item"), dict) else None
        cur_glyph = _glyph_index(ent)
        if cur_item == (want_item if want_item is not None else cur_item) and cur_glyph == (
            want_glyph if want_glyph is not None else cur_glyph
        ):
            continue
        _set_item_art(
            ent,
            want_item if want_item is not None else cur_item,
            want_glyph if want_glyph is not None else cur_glyph,
        )
        _write_json(path, ent)
        notes.append(f"{path.name}: custom overlay -> {want_item}/{want_glyph}")
    return notes


def expand_steal_atlases(folder: Path) -> List[str]:
    """Stamp a tiny items/glyph32 overlay onto a full vanilla clone.

    Custom tiles go in extra rows (index 0 stays vanilla bottom-left). Entity
    JSON then points at vanilla_count + leftover index instead of wrapping.
    """
    folder = Path(folder)
    notes: List[str] = []
    item_base: Optional[int] = _expanded_custom_base(folder, "items")
    glyph_base: Optional[int] = _expanded_custom_base(folder, "glyph32")
    tiny_items = 0
    tiny_glyphs = 0
    dest_rel = {"items": "assets/items.png", "glyph32": "assets/glyphs.png"}
    for name in ("items", "glyph32"):
        info = _vanilla_sheet_info(name)
        if not info or not Path(info["path"]).is_file():
            continue
        vanilla_n = int(info["cols"]) * int(info["rows"])
        src = _steal_source_png(folder, name)
        already = _expanded_custom_base(folder, name)
        if already is not None and src is None:
            if name == "items":
                item_base = already
            else:
                glyph_base = already
            continue
        if src is None and already is None:
            continue
        cols = int(info["cols"])
        tile = max(1, _pil_image().open(info["path"]).size[0] // cols)
        extras = _unpack_strip(src, tile) if src is not None else []
        if name == "items":
            tiny_items = len(extras)
        else:
            tiny_glyphs = len(extras)
        dest = folder.joinpath(*dest_rel[name].split("/"))
        if already is None or not dest.is_file():
            if not extras:
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            packed = _append_tiles_bottom_left(_pil_image().open(info["path"]), cols, tile, extras)
            packed.save(dest)
            extra_rows = max(1, (len(extras) + cols - 1) // cols)
            _register_tilesheet(folder, name, cols, int(info["rows"]) + extra_rows, dest_rel[name])
            notes.append(
                f"expanded {name}: {len(extras)} custom tile(s) at {vanilla_n}+ ({dest_rel[name]})"
            )
        if name == "items":
            item_base = vanilla_n
        else:
            glyph_base = vanilla_n
    notes.extend(
        _remap_expanded_entities(
            folder,
            item_base=item_base,
            glyph_base=glyph_base,
            tiny_items=tiny_items,
            tiny_glyphs=tiny_glyphs,
        )
    )
    return notes


def _glyph_index(entity: Dict[str, Any]) -> Optional[int]:
    frames = (entity.get("glyph") or {}).get("frames") or []
    if frames and isinstance(frames[0], dict) and frames[0].get("index") is not None:
        try:
            return int(frames[0]["index"])
        except (TypeError, ValueError):
            return None
    return None


def _set_item_art(entity: Dict[str, Any], image: Any, glyph_index: Any) -> None:
    if image is not None:
        entity.setdefault("item", {})["image"] = image
    if glyph_index is None:
        return
    glyph = entity.setdefault("glyph", {})
    frames = glyph.get("frames")
    if not isinstance(frames, list) or not frames:
        frames = [{}]
        glyph["frames"] = frames
    if isinstance(frames[0], dict):
        frames[0]["index"] = glyph_index


def _craft_donor_id(entity: Dict[str, Any]) -> str:
    resources = (entity.get("craftable") or {}).get("resources") or []
    if resources and isinstance(resources[0], dict) and resources[0].get("id") is not None:
        return str(resources[0]["id"])
    return ""


def _has_atlas(folder: Path, name: str) -> bool:
    assets = _load_optional(Path(folder) / "assets.json") or {}
    for sheet in ((assets.get("graphics") or {}).get("tilesheets") or []):
        if isinstance(sheet, dict) and str(sheet.get("name") or "") == name:
            return True
    return False


def restamp_item_art(folder: Path, *, remap_custom: Optional[bool] = None) -> List[str]:
    """Point custom items at vanilla tiles after dropping a stealing items atlas.

    Skill books use the vanilla book tile. Overlays of a vanilla entity id get
    that entity's art back. Tiny custom indexes are remapped only when this mod
    actually overlaid ``items`` / ``glyph32``.
    """
    folder = Path(folder)
    edir = folder / "entities"
    if not edir.is_dir():
        return []
    if remap_custom is None:
        remap_custom = _has_atlas(folder, "items") or _has_atlas(folder, "glyph32")
    core = _core_entities()
    by_name: Dict[str, Dict[str, Any]] = {}
    for row in core.values():
        name = str(row.get("name") or "").strip().lower()
        if name and name not in by_name and isinstance(row.get("item"), dict):
            by_name[name] = row
    notes: List[str] = []
    for path in sorted(edir.glob("*.json")):
        ent = _load_optional(path)
        if not isinstance(ent, dict) or not isinstance(ent.get("item"), dict):
            continue
        eid = str(ent.get("id") or "")
        cur_img = ent["item"].get("image")
        try:
            img_n = int(cur_img)
        except (TypeError, ValueError):
            img_n = 0
        donor: Optional[Dict[str, Any]] = core.get(eid) if eid in core else None
        usable = ent.get("usable") if isinstance(ent.get("usable"), dict) else {}
        if donor is None and (usable.get("skill_p") or usable.get("skill")):
            if img_n == 0 or _glyph_index(ent) in (0, None):
                _set_item_art(ent, BOOK_ITEM_IMAGE, BOOK_GLYPH_INDEX)
                _write_json(path, ent)
                notes.append(f"{path.name}: skill book -> vanilla book {BOOK_ITEM_IMAGE}/{BOOK_GLYPH_INDEX}")
            continue
        blob = f"{ent.get('name') or ''} {eid} {path.stem}".lower()
        gold_document = img_n == GOLD_INGOT_IMAGE and any(h in blob for h in DOCUMENT_NAME_HINTS)
        if gold_document:
            if ent["item"].get("image") != NECRO_BOOK_IMAGE or _glyph_index(ent) != NECRO_BOOK_GLYPH:
                _set_item_art(ent, NECRO_BOOK_IMAGE, NECRO_BOOK_GLYPH)
                _write_json(path, ent)
                notes.append(
                    f"{path.name}: gold-bar document -> necro book {NECRO_BOOK_IMAGE}/{NECRO_BOOK_GLYPH}"
                )
            continue
        if donor is None:
            donor = core.get(_craft_donor_id(ent)) or by_name.get(str(ent.get("name") or "").strip().lower())
        if not isinstance(donor, dict):
            continue
        d_item = donor.get("item") if isinstance(donor.get("item"), dict) else None
        d_img = d_item.get("image") if d_item else None
        d_glyph = _glyph_index(donor)
        vanilla_id = eid in core
        tiny_index = bool(remap_custom) and img_n < 32
        if not vanilla_id and not tiny_index:
            continue
        if d_img is None and d_glyph is None:
            continue
        if ent["item"].get("image") == d_img and _glyph_index(ent) == d_glyph:
            continue
        _set_item_art(ent, d_img if d_img is not None else cur_img, d_glyph)
        _write_json(path, ent)
        notes.append(f"{path.name}: item art -> vanilla {d_img}/{d_glyph}")
    return notes


def scan_sandmancy(folder: Path) -> List[str]:
    folder = Path(folder)
    issues: List[str] = []
    weak = folder / "abilities" / "Weak_Spot.json"
    if weak.is_file():
        issues.append("abilities/Weak_Spot.json: leftover ability file (id collides with passive; JSON also invalid)")
    for path in sorted((folder / "entities").glob("*.json")):
        text = path.read_text(encoding="utf-8-sig")
        if '"andmancy_Protective_Sand"' in text:
            issues.append(f"{path.name}: milestone typo andmancy_Protective_Sand")
    return issues


def fix_sandmancy(folder: Path) -> List[str]:
    folder = Path(folder)
    notes: List[str] = []
    weak = folder / "abilities" / "Weak_Spot.json"
    if weak.is_file():
        weak.unlink()
        notes.append("removed abilities/Weak_Spot.json (passive Weak Spot, not an ability)")
    notes.extend(drop_protected_atlases(folder))
    for path in sorted((folder / "entities").glob("*.json")):
        text = path.read_text(encoding="utf-8-sig")
        if '"andmancy_Protective_Sand"' not in text:
            continue
        path.write_text(
            text.replace('"andmancy_Protective_Sand"', '"Sandmancy_Protective_Sand"'),
            encoding="utf-8",
        )
        notes.append(f"{path.name}: Protective_Sand milestone id")
    notes.extend(_bump_version(folder, "0.1.2"))
    return notes


def _npc_name_rels(data: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    for race in data.get("races") or []:
        if not isinstance(race, dict):
            continue
        names = race.get("names") or {}
        if not isinstance(names, dict):
            continue
        for rel in names.values():
            if isinstance(rel, str) and rel.startswith("npc/"):
                out.append(rel.replace("\\", "/"))
    return out


def _copy_missing_npc_files(folder: Path, data: Dict[str, Any]) -> List[str]:
    notes: List[str] = []
    core = core2_dir()
    for rel in _npc_name_rels(data):
        dest = folder / rel
        if dest.is_file():
            continue
        src = core / rel
        if not src.is_file():
            notes.append(f"no vanilla file for {rel}")
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        notes.append(f"copied {rel}")
    return notes


def scan_draken(folder: Path) -> List[str]:
    folder = Path(folder)
    issues: List[str] = []
    data = _load_optional(folder / "character.json")
    if not isinstance(data, dict):
        return ["character.json missing or invalid"]
    vanilla = _core_races()
    for race in data.get("races") or []:
        if not isinstance(race, dict):
            continue
        rid = str(race.get("id") or "?")
        name = str(race.get("name") or rid)
        src = vanilla.get(rid)
        if not src:
            issues.append(f"race {rid} {name}: no vanilla counterpart to fill ages")
            continue
        missing = [k for k in RACE_CRASH_KEYS if k not in race]
        if missing:
            issues.append(f"race {rid} {name}: overlay missing {', '.join(missing)}")
    for rel in _npc_name_rels(data):
        if not (folder / rel).is_file():
            issues.append(f"missing {rel} (world gen opens these from this mod)")
    return issues


def fix_draken(folder: Path) -> List[str]:
    folder = Path(folder)
    notes: List[str] = []
    path = folder / "character.json"
    data = _load_optional(path)
    if not isinstance(data, dict):
        return ["character.json missing"]
    vanilla = _core_races()
    changed = False
    for race in data.get("races") or []:
        if not isinstance(race, dict):
            continue
        rid = str(race.get("id") or "")
        src = vanilla.get(rid)
        if not src:
            continue
        filled = _fill_vanilla_race(race, src)
        if filled:
            changed = True
            notes.append(f"race {rid} {race.get('name')}: filled {', '.join(filled)}")
    notes.extend(_copy_missing_npc_files(folder, data))
    if changed:
        _write_json(path, data)
    notes.extend(_bump_version(folder, "1.0.3"))
    return notes


def _cult_source_maps(maps: Path) -> List[Path]:
    found: List[Path] = []
    for path in sorted(maps.glob("Demonic_Cult_*_demonology_Cult_Hideout.smap")):
        if "Entrance" in path.name:
            continue
        found.append(path)
    return found


def _smap_header(path: Path) -> Optional[Tuple[str, str, str]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    parts = text.split("|", 3)
    if len(parts) < 3:
        return None
    return parts[0].strip(), parts[1], parts[2]


def _set_smap_id(path: Path, new_id: str) -> bool:
    text = path.read_text(encoding="utf-8")
    parts = text.split("|", 1)
    if len(parts) != 2 or parts[0] == new_id:
        return False
    path.write_text(f"{new_id}|{parts[1]}", encoding="utf-8", newline="\n")
    return True


def _index_smaps(maps: Path) -> Tuple[Dict[str, Path], Dict[str, Tuple[str, str, Path]]]:
    by_header: Dict[str, Path] = {}
    by_stem: Dict[str, Tuple[str, str, Path]] = {}
    if not maps.is_dir():
        return by_header, by_stem
    for path in sorted(maps.glob("*.smap")):
        header = _smap_header(path)
        if not header:
            continue
        hid, _name, building = header
        by_header[hid] = path
        by_stem[path.stem] = (hid, building, path)
    return by_header, by_stem


def _location_map_id_lists(data: Dict[str, Any]) -> List[List[str]]:
    out: List[List[str]] = []
    for loc in data.get("special") or []:
        if not isinstance(loc, dict):
            continue
        for scenario in loc.get("scenarios") or []:
            if not isinstance(scenario, dict):
                continue
            for block in scenario.get("building_maps") or []:
                if not isinstance(block, dict):
                    continue
                ids = block.get("ids")
                if isinstance(ids, list):
                    out.append(ids)
    return out


def _resolve_location_map_id(
    raw: str,
    by_header: Dict[str, Path],
    by_stem: Dict[str, Tuple[str, str, Path]],
) -> Optional[str]:
    """Vanilla locations.json uses the smap header id (Hunter_VIII), not the filename."""
    if raw in by_header:
        return raw
    for hid, building, _path in by_stem.values():
        if building and raw == f"{hid}_{building}":
            return hid
    if raw in by_stem:
        return raw
    return None


def _demonology_patch_dir() -> Path:
    return Path(__file__).resolve().parent / "workshop_patches" / DEMONOLOGY


def _demonology_assets_ok(folder: Path) -> List[str]:
    issues: List[str] = []
    assets = _load_optional(folder / "assets.json") or {}
    sheets = ((assets.get("graphics") or {}).get("tilesheets") or []) if isinstance(assets, dict) else []
    by_name: Dict[str, Dict[str, Any]] = {}
    for sheet in sheets:
        if not isinstance(sheet, dict):
            continue
        name = str(sheet.get("name") or "")
        rel = str(sheet.get("file") or "").replace("\\", "/")
        by_name[name] = sheet
        if "core_full" in rel:
            issues.append(f"assets.json {name} points at {rel} (vanilla overlay; Heretical/abilities miss custom tiles)")
    want = {str(row["name"]): row for row in DEMONOLOGY_COMPACT_SHEETS}
    for name, row in want.items():
        dest = folder.joinpath(*str(row["file"]).split("/"))
        if not dest.is_file():
            continue
        sheet = by_name.get(name)
        if not sheet:
            issues.append(f"assets.json missing compact {name} ({row['file']})")
            continue
        rel = str(sheet.get("file") or "").replace("\\", "/")
        tiles = sheet.get("tiles") or []
        if rel != row["file"] or list(tiles) != list(row["tiles"]):
            issues.append(f"assets.json {name} should be {row['file']} {list(row['tiles'])}")
    return issues


def _scan_demonology_icons(folder: Path) -> List[str]:
    issues = _demonology_assets_ok(folder)
    item_base = _expanded_custom_base(folder, "items")
    leftover_items = (folder / "assets" / "items_new.png").is_file()
    leftover_glyphs = (folder / "assets" / "glyphs_new.png").is_file()
    if leftover_items and item_base is None:
        issues.append("items_new.png is a tiny items overlay; expand onto a full vanilla clone")
    if leftover_glyphs and _expanded_custom_base(folder, "glyph32") is None:
        issues.append("glyphs_new.png is a tiny glyph32 overlay; expand onto a full vanilla clone")
    pact = _load_optional(folder / "entities" / "Infernal_Pact_of_Imp.json")
    if isinstance(pact, dict) and isinstance(pact.get("item"), dict):
        try:
            img_n = int(pact["item"].get("image"))
        except (TypeError, ValueError):
            img_n = -1
        if item_base is not None:
            if img_n != item_base:
                issues.append(f"Infernal Pact of Imp image {img_n} should be expanded custom tile {item_base}")
        elif img_n == GOLD_INGOT_IMAGE or _glyph_index(pact) == 281:
            issues.append("Infernal Pact of Imp uses gold-ingot art (60/281)")
    passives = _load_optional(folder / "passives.json")
    if isinstance(passives, list):
        for row in passives:
            if not isinstance(row, dict):
                continue
            try:
                img_n = int(row.get("image"))
            except (TypeError, ValueError):
                continue
            if img_n > 3:
                issues.append(f"passive {row.get('id')} image {img_n} is off the 4-wide custom sheet")
    return issues


def _copy_demonology_patch_pngs(folder: Path) -> List[str]:
    src_dir = _demonology_patch_dir()
    if not src_dir.is_dir():
        return []
    notes: List[str] = []
    dest_dir = folder / "assets"
    dest_dir.mkdir(parents=True, exist_ok=True)
    for name in DEMONOLOGY_PATCH_PNGS:
        src = src_dir / name
        dest = dest_dir / name
        if not src.is_file():
            continue
        if dest.is_file() and dest.read_bytes() == src.read_bytes():
            continue
        shutil.copy2(src, dest)
        notes.append(f"restored painted {name}")
    return notes


def _full_steal_sheets(folder: Path) -> List[Dict[str, Any]]:
    vanilla = _vanilla_atlas_cells()
    kept: List[Dict[str, Any]] = []
    for sheet in _assets_sheets(folder):
        name = str(sheet.get("name") or "")
        if name not in STEAL_ATLAS:
            continue
        limit = max(TINY_ATLAS_CELLS, vanilla.get(name, TINY_ATLAS_CELLS))
        if _sheet_cells(sheet) >= limit:
            kept.append(
                {
                    "name": name,
                    "tiles": list(sheet.get("tiles") or []),
                    "file": str(sheet.get("file") or "").replace("\\", "/"),
                }
            )
    return kept


def _fix_demonology_assets(folder: Path) -> List[str]:
    notes: List[str] = []
    kept: List[Dict[str, Any]] = []
    for row in DEMONOLOGY_COMPACT_SHEETS:
        dest = folder.joinpath(*str(row["file"]).split("/"))
        if dest.is_file():
            kept.append(dict(row))
        else:
            notes.append(f"missing {row['file']}")
    kept.extend(_full_steal_sheets(folder))
    if not kept:
        return notes
    path = folder / "assets.json"
    current = _load_optional(path) if path.is_file() else {}
    if not isinstance(current, dict):
        current = {}
    want = {"graphics": {"tilesheets": kept}}
    if current.get("graphics") == want["graphics"]:
        return notes
    _write_json(path, want)
    notes.append("assets.json restored compact skill sheets (full items/glyph32 kept)")
    return notes


def _fix_demonology_passives(folder: Path) -> List[str]:
    path = folder / "passives.json"
    rows = _load_optional(path)
    if not isinstance(rows, list):
        return []
    notes: List[str] = []
    changed = False
    for row in rows:
        if not isinstance(row, dict):
            continue
        pid = str(row.get("id") or "")
        if pid not in DEMONOLOGY_PASSIVE_IMAGES:
            continue
        want = DEMONOLOGY_PASSIVE_IMAGES[pid]
        if row.get("image") == want:
            continue
        row["image"] = want
        changed = True
        notes.append(f"passive {pid} image -> {want}")
    if changed:
        _write_json(path, rows)
    return notes


def _fix_demonology_pact(folder: Path) -> List[str]:
    if _expanded_custom_base(folder, "items") is not None:
        return []
    path = folder / "entities" / "Infernal_Pact_of_Imp.json"
    ent = _load_optional(path)
    if not isinstance(ent, dict) or not isinstance(ent.get("item"), dict):
        return []
    try:
        img_n = int(ent["item"].get("image"))
    except (TypeError, ValueError):
        img_n = -1
    if img_n == NECRO_BOOK_IMAGE and _glyph_index(ent) == NECRO_BOOK_GLYPH:
        return []
    if img_n != GOLD_INGOT_IMAGE and _glyph_index(ent) != 281:
        return []
    _set_item_art(ent, NECRO_BOOK_IMAGE, NECRO_BOOK_GLYPH)
    _write_json(path, ent)
    return [f"Infernal Pact of Imp -> necro book {NECRO_BOOK_IMAGE}/{NECRO_BOOK_GLYPH}"]


def _fix_demonology_icons(folder: Path) -> List[str]:
    notes: List[str] = []
    notes.extend(_copy_demonology_patch_pngs(folder))
    notes.extend(expand_steal_atlases(folder))
    notes.extend(_fix_demonology_assets(folder))
    notes.extend(_fix_demonology_passives(folder))
    notes.extend(_fix_demonology_pact(folder))
    return notes


def scan_demonology(folder: Path) -> List[str]:
    folder = Path(folder)
    issues: List[str] = []
    issues.extend(_scan_demonology_icons(folder))
    maps = folder / "building_maps"
    if not maps.is_dir():
        issues.append("building_maps missing")
        return issues
    for stem in CULT_HIDEOUT_ALIASES:
        if not (maps / f"{stem}.smap").is_file():
            issues.append(f"missing map {stem}.smap (locations.json one_of list)")
    by_header, by_stem = _index_smaps(maps)
    for stem, (hid, _building, path) in by_stem.items():
        if stem in CULT_HIDEOUT_ALIASES and hid != stem:
            issues.append(f"{path.name} header id {hid!r} should be {stem!r}")
    loc_path = folder / "locations.json"
    data = _load_optional(loc_path)
    if not isinstance(data, dict):
        issues.append("locations.json missing")
        return issues
    for ids in _location_map_id_lists(data):
        for raw in ids:
            if not isinstance(raw, str):
                continue
            resolved = _resolve_location_map_id(raw, by_header, by_stem)
            if resolved is None:
                issues.append(f"locations.json unknown map {raw}")
            elif resolved != raw:
                issues.append(f"locations.json map {raw} should be {resolved}")
    char = _load_optional(folder / "character.json")
    if isinstance(char, dict):
        for rel in _npc_name_rels(char):
            if not (folder / rel).is_file():
                issues.append(f"missing {rel} (playable race names; world gen opens these)")
        entity_ids = _entity_ids_by_lower(folder)
        for race in char.get("races") or []:
            if not isinstance(race, dict):
                continue
            base = race.get("base_entities") or {}
            if not isinstance(base, dict):
                continue
            for key, val in base.items():
                sid = str(val)
                canon = entity_ids.get(sid.lower())
                if canon and canon != sid:
                    issues.append(f"base_entities.{key} {sid} != entity id {canon}")
    return issues


def _entity_ids_by_lower(folder: Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    edir = folder / "entities"
    if not edir.is_dir():
        return out
    for path in edir.glob("*.json"):
        ent = _load_optional(path)
        if isinstance(ent, dict) and ent.get("id") is not None:
            eid = str(ent["id"])
            out[eid.lower()] = eid
    return out


def _fix_demonology_race(folder: Path) -> List[str]:
    notes: List[str] = []
    path = folder / "character.json"
    data = _load_optional(path)
    if not isinstance(data, dict):
        return ["character.json missing"]
    entity_ids = _entity_ids_by_lower(folder)
    changed = False
    for race in data.get("races") or []:
        if not isinstance(race, dict):
            continue
        base = race.get("base_entities") or {}
        if isinstance(base, dict):
            for key, val in list(base.items()):
                sid = str(val)
                canon = entity_ids.get(sid.lower())
                if canon and canon != sid:
                    base[key] = canon
                    changed = True
                    notes.append(f"base_entities.{key} {sid} -> {canon}")
        settlement = race.get("settlement")
        if race.get("playable") and not isinstance(settlement, dict):
            race["settlement"] = {"start_spawn_rate": 0}
            changed = True
            notes.append(f"race {race.get('id')}: start_spawn_rate 0 (no civ center)")
    notes.extend(_copy_missing_npc_files(folder, data))
    if changed:
        _write_json(path, data)
    return notes


def fix_demonology(folder: Path) -> List[str]:
    folder = Path(folder)
    maps = folder / "building_maps"
    notes: List[str] = []
    notes.extend(_fix_demonology_icons(folder))
    if not maps.is_dir():
        notes.append("building_maps missing")
        notes.extend(_bump_version(folder, "1.0.5"))
        return notes
    sources = _cult_source_maps(maps)
    if not sources:
        notes.append("no Demonic_Cult_* smaps to copy")
        notes.extend(_bump_version(folder, "1.0.5"))
        return notes
    for i, stem in enumerate(CULT_HIDEOUT_ALIASES):
        dest = maps / f"{stem}.smap"
        if dest.is_file():
            continue
        src = sources[i % len(sources)]
        shutil.copy2(src, dest)
        notes.append(f"copied {src.name} -> {dest.name}")
    _by_header, by_stem = _index_smaps(maps)
    for stem in CULT_HIDEOUT_ALIASES:
        dest = maps / f"{stem}.smap"
        if not dest.is_file():
            continue
        if _set_smap_id(dest, stem):
            notes.append(f"{dest.name} header id -> {stem}")
    by_header, by_stem = _index_smaps(maps)
    loc_path = folder / "locations.json"
    data = _load_optional(loc_path)
    if not isinstance(data, dict):
        notes.append("locations.json missing")
        notes.extend(_fix_demonology_race(folder))
        notes.extend(_bump_version(folder, "1.0.5"))
        return notes
    rewritten = 0
    for ids in _location_map_id_lists(data):
        for i, raw in enumerate(ids):
            if not isinstance(raw, str):
                continue
            resolved = _resolve_location_map_id(raw, by_header, by_stem)
            if resolved and resolved != raw:
                ids[i] = resolved
                rewritten += 1
                notes.append(f"locations.json {raw} -> {resolved}")
    if rewritten:
        _write_json(loc_path, data)
    notes.extend(_fix_demonology_race(folder))
    notes.extend(_bump_version(folder, "1.0.5"))
    return notes


def scan_content_mod(folder: Path) -> List[str]:
    scan, _fix = content_fixer_for(folder)
    if scan is None:
        return []
    return scan(folder)


def fix_content_mod(folder: Path) -> List[str]:
    _scan, fix = content_fixer_for(folder)
    if fix is None:
        return []
    return fix(folder)
