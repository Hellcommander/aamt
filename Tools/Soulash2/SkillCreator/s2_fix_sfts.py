"""Repair Gespenst's Soup for the Soulash (3317585513) and Buildings addon (3328313908).

0.10 broke these packs by overlaying the global `items` / `glyph32` / `buildings`
atlases (tiny custom sheets steal every vanilla icon) and by replacing vanilla
crops/NPCs with 0.9 copies (wrong glyph indexes, missing craftable, broken
growth chains). Same rule as particles32: leave the vanilla atlas alone and
stamp new foods onto existing core_2 icons.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional

from s2_buildings import (
    VANILLA_FARMER,
    _load_json,
    _write_json,
    is_player_building,
)
from s2_paths import core2_dir, workshop_root

SFTS_MAIN = "3317585513"
SFTS_BUILDINGS = "3328313908"
SFTS_IDS = {SFTS_MAIN, SFTS_BUILDINGS}

PROTECTED_SHEETS = {"items", "glyph32", "buildings", "particles32"}
DROP_VANILLA_OVERLAY_IDS = {
    "211",
    "2261",
    "2427",
    "3078",
    "3079",
    "879",
    "880",
    "core_2_Potato_Seedling",
    "core_2_Barley_Bread",
    "core_2_Barley_Flour",
}
# Replacing campfire output with a duplicate baked potato; vanilla already bakes.
SKIP_PRODUCER_PRODUCTS = {"sfts_baked_potato"}
# 0.9 harvest plants. Vanilla 0.10 grows carrot/onion into the food item itself
# (793 / 2872). Stamping item art onto these producer+stackable leftovers crashes
# entity load ("Failed to load entity 'sfts_carrot'").
DROP_FAKE_PLANTS = {"sfts_carrot", "sfts_onion"}

PLAYER_IMAGES = {
    "sfts_potato_farm": 238,
    "sfts_carrot_farm": 3,
    "sfts_onion_farm": 3,
    "sfts_pastry_shop": 7,
    "sfts_restaurant": 10,
    "sfts_player_fromager": 7,
}

VANILLA_BAKER = {
    "0": "2261",
    "1": "core_2_Dwarf_Miller",
    "2": "core_2_Elf_Baker",
    "4": "core_2_Goblin_Baker",
    "6": "core_2_Vampire_Baker",
    "7": "core_2_Troll_Baker",
    "8": "core_2_Orc_Miller",
    "10": "2331",
    "23": "core_2_Reptilion_Baker",
    "26": "core_2_Bone_Wraith_Miller",
    "31": "core_2_Gnoll_Miller",
    "32": "core_2_Mushman_Forager",
    "33": "core_2_Ursan_Forager",
}

VANILLA_TAVERN = {
    "0": "211",
    "1": "core_2_Dwarf_Miller",
    "2": "2271",
    "4": "core_2_Goblin_Baker",
    "6": "core_2_Vampire_Baker",
    "7": "core_2_Troll_Baker",
    "8": "core_2_Orc_Miller",
    "10": "2331",
    "23": "core_2_Reptilion_Baker",
    "26": "core_2_Bone_Wraith_Miller",
    "31": "core_2_Gnoll_Miller",
    "32": "core_2_Mushman_Miller",
    "33": "core_2_Ursan_Miller",
}

ART_DONORS = (
    ("knife", "70"),
    ("cheese", "3026"),
    ("pie", "879"),
    ("tart", "879"),
    ("cake", "879"),
    ("cookie", "803"),
    ("muffin", "803"),
    ("waffle", "803"),
    ("bread", "803"),
    ("loaf", "803"),
    ("soup", "810"),
    ("stew", "810"),
    ("curry", "810"),
    ("salad", "810"),
    ("salsa", "810"),
    ("slug", "core_2_Slug_Meat"),
    ("larva", "core_2_Larva_Meat"),
    ("jelly", "core_2_Ground_Jelly"),
    ("lichen", "core_2_Lichen"),
    ("onion", "2872"),
    ("carrot", "793"),
    ("potato", "core_2_Baked_Potato"),
    ("mushroom", "343"),
    ("egg", "826"),
    ("sauce", "809"),
    ("glaze", "809"),
    ("barbeque", "809"),
    ("scampi", "809"),
    ("chops", "809"),
    ("steak", "809"),
    ("ham", "809"),
    ("meat", "809"),
    ("rub", "809"),
)

_CORE_ENTITIES: Optional[Dict[str, Dict[str, Any]]] = None
_CORE_BUILDINGS: Optional[Dict[str, Dict[str, Any]]] = None


def is_sfts_mod(folder: Path) -> bool:
    folder = Path(folder)
    if folder.name in SFTS_IDS:
        return True
    mj = folder / "mod.json"
    if not mj.is_file():
        return False
    try:
        mod = _load_json(mj)
    except Exception:
        return False
    sid = str(mod.get("steam_publish_id") or "")
    name = str(mod.get("name") or "").lower()
    return sid in SFTS_IDS or name.startswith("soup for the soulash")


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


def _core_buildings() -> Dict[str, Dict[str, Any]]:
    global _CORE_BUILDINGS
    if _CORE_BUILDINGS is not None:
        return _CORE_BUILDINGS
    found: Dict[str, Dict[str, Any]] = {}
    bdir = core2_dir() / "buildings"
    if bdir.is_dir():
        for path in bdir.glob("*.json"):
            try:
                data = _load_json(path)
            except Exception:
                continue
            if isinstance(data, dict) and data.get("id") is not None:
                found[str(data["id"])] = data
    _CORE_BUILDINGS = found
    return found


def _load_optional(path: Path) -> Any:
    if not path.is_file():
        return None
    try:
        return _load_json(path)
    except Exception:
        return None


def scan_sfts(folder: Path) -> List[str]:
    folder = Path(folder)
    issues: List[str] = []
    if not is_sfts_mod(folder):
        return issues
    seen_miles: Dict[str, str] = {}
    miles = folder / "milestones"
    if miles.is_dir():
        for path in miles.rglob("*.json"):
            row = _load_optional(path)
            if not isinstance(row, dict) or not row.get("id"):
                continue
            mid = str(row["id"])
            if mid in seen_miles:
                issues.append(f"duplicate milestone id {mid} ({seen_miles[mid]} and {path.name})")
            seen_miles[mid] = path.name
    soup = folder / "milestones" / "agriculture" / "sfts_soup.json"
    row = _load_optional(soup)
    if isinstance(row, dict) and str(row.get("id") or "") == "sfts_mulberry":
        issues.append("sfts_soup.json id is sfts_mulberry (clobbers mulberry recipes)")
    conv = _load_optional(folder / "conversations.json") or {}
    for convo in conv.get("conversations") or []:
        if not isinstance(convo, dict):
            continue
        cid = str(convo.get("id") or "")
        if cid.startswith("core_2_"):
            issues.append(f"conversations.json overlays {cid}")
    edir = folder / "entities"
    core_ids = _core_entities()
    if edir.is_dir():
        for path in edir.glob("*.json"):
            ent = _load_optional(path)
            if not isinstance(ent, dict):
                continue
            eid = str(ent.get("id") or "")
            if eid in DROP_FAKE_PLANTS:
                issues.append(f"{path.name}: leftover 0.9 plant {eid} (crashes entity load)")
                continue
            vanilla = core_ids.get(eid)
            if not vanilla:
                continue
            if eid in DROP_VANILLA_OVERLAY_IDS:
                issues.append(f"{path.name}: overlays vanilla {eid} (should drop)")
                continue
            vg = ((vanilla.get("glyph") or {}).get("frames") or [{}])[0]
            mg = ((ent.get("glyph") or {}).get("frames") or [{}])[0]
            if isinstance(vg, dict) and isinstance(mg, dict) and vg.get("index") != mg.get("index"):
                issues.append(f"{path.name}: overlay {eid} replaced vanilla glyph {vg.get('index')} with {mg.get('index')}")
    bdir = folder / "buildings"
    if bdir.is_dir():
        for path in bdir.glob("*.json"):
            data = _load_optional(path)
            if not isinstance(data, dict):
                continue
            bid = str(data.get("id") or path.stem)
            if is_player_building(data):
                opr = data.get("occupation_per_race") or {}
                if isinstance(opr, dict) and len(opr) <= 1:
                    issues.append(f"{bid}: occupation_per_race incomplete")
            elif "occupation_image" not in data:
                issues.append(f"{bid}: NPC building missing occupation_image")
            if data.get("enables") and str(data.get("race") or "") not in ("", "-1"):
                issues.append(f"{bid}: NPC building has enables (player-hall leftover)")
            blob = str(data.get("required_entities") or "")
            for pid in DROP_FAKE_PLANTS:
                if pid in blob:
                    issues.append(f"{bid}: required_entities still lists {pid}")
    if folder.name == SFTS_BUILDINGS:
        extra = folder / "entities"
        if extra.is_dir() and any(extra.glob("*.json")):
            issues.append("addon duplicates the main pack (entities/milestones/player buildings)")
    return issues


def _copy_art(src: Dict[str, Any], dest: Dict[str, Any]) -> bool:
    changed = False
    dest_comps = set(dest.get("components") or [])
    if "item" in dest_comps and src.get("glyph") is not None and dest.get("glyph") != src["glyph"]:
        dest["glyph"] = deepcopy(src["glyph"])
        changed = True
    if "item" in dest_comps and src.get("item") is not None:
        item = dict(dest.get("item") or {})
        src_item = src.get("item") or {}
        if src_item.get("image") is not None and item.get("image") != src_item["image"]:
            item["image"] = src_item["image"]
            dest["item"] = item
            changed = True
    return changed


def _merge_producer(vanilla: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
    out = deepcopy(vanilla)
    prod = overlay.get("producer")
    if not isinstance(prod, dict):
        return out
    comps = list(out.get("components") or [])
    if "producer" not in comps:
        comps.append("producer")
        out["components"] = comps
    existing = out.setdefault("producer", {"products": {}, "time": prod.get("time", 10)})
    products = existing.setdefault("products", {})
    for action, rows in (prod.get("products") or {}).items():
        bucket = products.setdefault(str(action), [])
        have = {str(p.get("id")) for p in bucket if isinstance(p, dict)}
        for row in rows or []:
            if not isinstance(row, dict):
                continue
            pid = str(row.get("id") or "")
            if not pid or pid in have or pid in SKIP_PRODUCER_PRODUCTS:
                continue
            bucket.append(deepcopy(row))
            have.add(pid)
    food = overlay.get("food")
    if isinstance(food, dict) and food.get("raw") is True:
        out.setdefault("food", {}).setdefault("raw", True)
        if out["food"].get("raw") is False:
            out["food"]["raw"] = True
    return out


def _donor_for(entity: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    blob = f"{entity.get('id') or ''} {entity.get('name') or ''}".lower()
    core = _core_entities()
    for key, src_id in ART_DONORS:
        if key in blob:
            return core.get(src_id)
    if "food" in (entity.get("components") or []):
        return core.get("809")
    return None


def _fix_assets(folder: Path) -> List[str]:
    path = folder / "assets.json"
    data = _load_optional(path)
    if not isinstance(data, dict):
        return []
    sheets = ((data.get("graphics") or {}).get("tilesheets") or [])
    kept = [s for s in sheets if not (isinstance(s, dict) and str(s.get("name") or "") in PROTECTED_SHEETS)]
    if len(kept) == len(sheets):
        return []
    if kept:
        data["graphics"]["tilesheets"] = kept
        _write_json(path, data)
        return [f"assets.json: removed {len(sheets) - len(kept)} vanilla atlas overlay(s)"]
    path.unlink()
    return ["deleted assets.json (only overlaid vanilla atlases)"]


def _fix_milestones(folder: Path) -> List[str]:
    notes: List[str] = []
    soup = folder / "milestones" / "agriculture" / "sfts_soup.json"
    row = _load_optional(soup)
    if isinstance(row, dict) and str(row.get("id") or "") == "sfts_mulberry":
        row["id"] = "sfts_soup"
        row["name"] = "Hearty Soup"
        _write_json(soup, row)
        notes.append("sfts_soup.json id=sfts_soup")
    return notes


def _fix_conversations(folder: Path) -> List[str]:
    path = folder / "conversations.json"
    data = _load_optional(path)
    if not isinstance(data, dict):
        return []
    rows = data.get("conversations") or []
    kept: List[Any] = []
    notes: List[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        cid = str(row.get("id") or "")
        if cid.startswith("core_2_"):
            notes.append(f"dropped conversation overlay {cid}")
            continue
        ents = row.setdefault("entities", [])
        if cid.startswith("sfts_") and "Fromager_Vampire" not in ents:
            ents.append("Fromager_Vampire")
            notes.append(f"{cid}: Fromager_Vampire")
        kept.append(row)
    if kept != rows:
        data["conversations"] = kept
        if kept:
            _write_json(path, data)
        else:
            path.unlink(missing_ok=True)
            notes.append("deleted empty conversations.json")
        return notes
    return notes


def _fix_entities(folder: Path) -> List[str]:
    notes: List[str] = []
    edir = folder / "entities"
    if not edir.is_dir():
        return notes
    core = _core_entities()
    for path in sorted(edir.glob("*.json")):
        ent = _load_optional(path)
        if not isinstance(ent, dict):
            continue
        eid = str(ent.get("id") or "")
        if eid in DROP_FAKE_PLANTS:
            path.unlink()
            notes.append(f"deleted leftover plant {path.name} ({eid})")
            continue
        vanilla = core.get(eid)
        if vanilla and eid in DROP_VANILLA_OVERLAY_IDS:
            path.unlink()
            notes.append(f"deleted overlay {path.name} ({eid})")
            continue
        if vanilla:
            if not ent.get("producer"):
                path.unlink()
                notes.append(f"deleted overlay {path.name} ({eid})")
                continue
            merged = _merge_producer(vanilla, ent)
            vp = (vanilla.get("producer") or {}).get("products")
            mp = (merged.get("producer") or {}).get("products")
            food_changed = (merged.get("food") or {}).get("raw") != (vanilla.get("food") or {}).get("raw")
            if mp == vp and not food_changed:
                path.unlink()
                notes.append(f"deleted redundant overlay {eid}")
                continue
            _write_json(path, merged)
            notes.append(f"restored vanilla {eid} (kept extra cook recipes)")
            continue
        donor = _donor_for(ent)
        if donor and _copy_art(donor, ent):
            _write_json(path, ent)
            notes.append(f"{eid}: vanilla art from {donor.get('id')}")
    return notes


def _ensure_opr(building: Dict[str, Any], mapping: Dict[str, str], occupation_0: Optional[str] = None) -> None:
    opr = dict(mapping)
    if occupation_0:
        opr["0"] = occupation_0
    if building.get("occupation") == "Fromager":
        opr["0"] = "Fromager"
        opr["6"] = "Fromager_Vampire"
    building["occupation_per_race"] = opr


def _fix_player_buildings(folder: Path) -> List[str]:
    notes: List[str] = []
    bdir = folder / "buildings"
    if not bdir.is_dir():
        return notes
    bakery = _core_buildings().get("9")
    tavern = _core_buildings().get("393")
    for path in sorted(bdir.glob("*.json")):
        data = _load_optional(path)
        if not isinstance(data, dict):
            continue
        bid = str(data.get("id") or "")
        if bid == "9" and bakery:
            path.unlink()
            notes.append("deleted 9_Bakery.json (vanilla already has barley bread)")
            continue
        if bid == "393" and tavern:
            merged = deepcopy(tavern)
            have: set[str] = set()
            for block in merged.get("produces") or []:
                for ent in (block.get("entities") or []) if isinstance(block, dict) else []:
                    if isinstance(ent, dict) and ent.get("id"):
                        have.add(str(ent["id"]))
            extra = []
            for block in data.get("produces") or []:
                if not isinstance(block, dict):
                    continue
                ids = [str(e.get("id")) for e in (block.get("entities") or []) if isinstance(e, dict)]
                if ids and not any(i in have for i in ids):
                    extra.append(block)
            merged["produces"] = list(merged.get("produces") or []) + extra
            _write_json(path, merged)
            notes.append(f"393 tavern: vanilla 0.10 fields + {len(extra)} SFTS dishes")
            continue
        if not is_player_building(data):
            continue
        changed = False
        if bid in PLAYER_IMAGES and data.get("image") != PLAYER_IMAGES[bid]:
            data["image"] = PLAYER_IMAGES[bid]
            changed = True
        name = str(data.get("name") or "").lower()
        if "farm" in name:
            _ensure_opr(data, VANILLA_FARMER)
            workers = data.get("workers") or [1, 2]
            want = int(workers[1]) if len(workers) >= 2 else 2
            data["required_entities"] = _farm_required(str(data.get("name") or ""), want)
            changed = True
        elif "pastry" in name:
            _ensure_opr(data, VANILLA_BAKER)
            changed = True
        elif "restaurant" in name or "tavern" in name:
            _ensure_opr(data, VANILLA_TAVERN)
            changed = True
        elif "fromager" in name:
            _ensure_opr(data, VANILLA_BAKER, "Fromager")
            data["occupation_per_race"]["6"] = "Fromager_Vampire"
            changed = True
        if changed:
            _write_json(path, data)
            notes.append(f"{path.name}: player 0.10 occupation map / vanilla building image")
    return notes


def _kind_for_npc(building: Dict[str, Any]) -> str:
    name = str(building.get("name") or "").lower()
    occ = str(building.get("occupation") or "")
    if "farm" in name:
        return "farm"
    if "fromager" in name or occ == "Fromager":
        return "fromager"
    if "pastry" in name or "bakery" in name:
        return "bakery"
    if "mill" in name:
        return "mill"
    return "kitchen"


def _npc_defaults(kind: str) -> Dict[str, Any]:
    tavern = _core_buildings().get("393") or {}
    bakery = _core_buildings().get("9") or {}
    mill = _core_buildings().get("8") or {}
    if kind == "farm":
        return {
            "occupation_image": 95,
            "group": "food",
            "min_area": 30,
            "image": 238,
            "required_entities": [],
        }
    if kind == "bakery":
        return {
            "occupation_image": bakery.get("occupation_image", 3),
            "group": "producers",
            "min_area": bakery.get("min_area", 30),
            "image": 7,
            "required_entities": bakery.get("required_entities") or [],
        }
    if kind == "mill":
        return {
            "occupation_image": mill.get("occupation_image", 46),
            "group": "resources",
            "min_area": mill.get("min_area", 20),
            "image": mill.get("image", 6),
            "required_entities": mill.get("required_entities") or [],
        }
    if kind == "fromager":
        return {
            "occupation_image": 20,
            "group": "producers",
            "min_area": 20,
            "image": 7,
            "required_entities": [
                {"entities": ["928", "2408"], "count": 1},
                {"component": "resting_place", "count": 2},
            ],
        }
    return {
        "occupation_image": tavern.get("occupation_image", 5),
        "group": "producers",
        "min_area": tavern.get("min_area", 40),
        "image": 10,
        "required_entities": tavern.get("required_entities") or [],
    }


def _farm_required(name: str, workers_max: int) -> List[Dict[str, Any]]:
    plants = ["core_2_Potato_Seedling", "core_2_Potato_Plant", "core_2_Potato"]
    lowered = name.lower()
    if "carrot" in lowered:
        plants = ["793", "3079"]
    elif "onion" in lowered:
        plants = ["2872", "3078"]
    return [
        {"entities": plants, "count": 4},
        {"component": "resting_place", "count": workers_max},
    ]


def _fit_resting(building: Dict[str, Any]) -> None:
    workers = building.get("workers")
    want = None
    if isinstance(workers, list) and len(workers) >= 2:
        try:
            want = int(workers[1])
        except (TypeError, ValueError):
            want = None
    req = building.get("required_entities")
    if not want or not isinstance(req, list):
        return
    for slot in req:
        if isinstance(slot, dict) and slot.get("component") == "resting_place":
            slot["count"] = want
            return
    req.append({"component": "resting_place", "count": want})


def _fix_npc_buildings(folder: Path) -> List[str]:
    notes: List[str] = []
    bdir = folder / "buildings"
    if not bdir.is_dir():
        return notes
    for path in sorted(bdir.glob("*.json")):
        data = _load_optional(path)
        if not isinstance(data, dict):
            continue
        if is_player_building(data):
            continue
        changed = False
        if "enables" in data:
            data.pop("enables", None)
            changed = True
        kind = _kind_for_npc(data)
        defaults = _npc_defaults(kind)
        for key in ("occupation_image", "group", "min_area"):
            if key not in data:
                data[key] = defaults[key]
                changed = True
        if kind == "farm":
            workers = data.get("workers") or [1, 2]
            want = int(workers[1]) if len(workers) >= 2 else 2
            want_req = _farm_required(str(data.get("name") or ""), want)
            if data.get("required_entities") != want_req:
                data["required_entities"] = want_req
                changed = True
        elif "required_entities" not in data:
            data["required_entities"] = deepcopy(defaults.get("required_entities") or [])
            changed = True
        img = defaults.get("image")
        if img is not None and int(data.get("image") or 0) < 12:
            data["image"] = img
            changed = True
        before = deepcopy(data.get("required_entities"))
        _fit_resting(data)
        if data.get("required_entities") != before:
            changed = True
        if "produces" not in data:
            data["produces"] = []
            changed = True
        if changed:
            _write_json(path, data)
            notes.append(f"{path.name}: NPC 0.10 fields ({kind})")
    return notes


def _strip_addon_duplicates(folder: Path) -> List[str]:
    notes: List[str] = []
    ws = workshop_root()
    main = (ws / SFTS_MAIN) if ws else None
    if main is None or not main.is_dir():
        return notes
    keep_buildings = {
        "Restaurant.json",
        "Potato_Farm.json",
        "Onion_Farm.json",
        "Pastry_Shop.json",
        "Carrot_Farm.json",
        "Player_Fromager.json",
        "9_Bakery.json",
        "393_Tavern.json",
    }
    for rel in (
        "assets.json",
        "conversations.json",
        "dialogues.json",
    ):
        path = folder / rel
        if path.is_file() and (main / rel).is_file():
            path.unlink()
            notes.append(f"dropped duplicate {rel}")
    for sub in ("entities", "milestones"):
        src = folder / sub
        if not src.is_dir():
            continue
        for path in list(src.rglob("*")):
            if path.is_file():
                path.unlink()
        for leftover in sorted(src.rglob("*"), reverse=True):
            if leftover.is_dir():
                try:
                    leftover.rmdir()
                except OSError:
                    pass
        notes.append(f"dropped duplicate {sub}/ (lives in {SFTS_MAIN})")
    bdir = folder / "buildings"
    if bdir.is_dir():
        for name in keep_buildings:
            path = bdir / name
            if path.is_file():
                path.unlink()
                notes.append(f"dropped duplicate buildings/{name}")
    return notes


def _bump_version(folder: Path) -> List[str]:
    path = folder / "mod.json"
    mod = _load_optional(path)
    if not isinstance(mod, dict):
        return []
    if str(mod.get("version") or "") == "1.0.3":
        return []
    mod["version"] = "1.0.3"
    _write_json(path, mod)
    return ["version=1.0.3"]


def fix_sfts_mod(folder: Path) -> List[str]:
    folder = Path(folder)
    if not is_sfts_mod(folder):
        return []
    notes: List[str] = []
    notes.extend(_fix_assets(folder))
    notes.extend(_fix_milestones(folder))
    notes.extend(_fix_conversations(folder))
    if folder.name == SFTS_BUILDINGS:
        notes.extend(_strip_addon_duplicates(folder))
        notes.extend(_fix_npc_buildings(folder))
    else:
        notes.extend(_fix_entities(folder))
        notes.extend(_fix_player_buildings(folder))
    notes.extend(_bump_version(folder))
    return notes
