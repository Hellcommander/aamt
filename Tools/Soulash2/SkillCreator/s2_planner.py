#!/usr/bin/env python3
"""Load selected Soulash 2 mods and plan skill potential vs race age stages.

Potential rules (live 0.10 + community / player notes):
- character.json ``max_potential`` is the shared pool (core_2 default 200; overlay mods last-write).
- Every skill starts with 10 potential that does not come from that pool.
- Character creation: pick 3 skills; those start at 20 (10 extra from the pool).
- Training raises a skill's individual potential and spends the shared pool.
- Middle-aged and elder each grant +30 max potential (60 total over a lifetime).
  Vampire-style races with adult/elder ~10000 never see those bonuses in play.
"""

from __future__ import annotations

import json
import os
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from s2_paths import core2_dir, mods_dir, output_root, skip_mod_path, soulash2_root, workshop_root
from s2_assets import TILE

FLOOR = 10
STARTING_COUNT = 3
STARTING_BONUS = 10
AGE_BONUS_MIDDLE = 30
AGE_BONUS_ELDER = 30
GOLD_BRACKETS = (5, 10, 15, 20, 25, 30, 35, 40, 45, 50)
ELDER_MENTAL = 1
ELDER_PHYSICAL = 1
STAGES = ("young", "middle", "elder")
KIND_WEAPON = "weapon"
KIND_MAGIC = "magic"
KIND_CRAFT = "craft"
KIND_USE = "use"
KIND_ORDER = {KIND_WEAPON: 0, KIND_MAGIC: 1, KIND_USE: 2, KIND_CRAFT: 3}
# World-action XP that marks Athletics / Leadership / Adventuring as Use, not Craft.
_USE_EXP = frozenset(
    {
        "walk",
        "climb",
        "jump_down",
        "drag",
        "throw",
        "order",
        "companion_kill",
        "companion_build",
        "resource_discovery",
        "location_discovery",
        "location_details_discovery",
    }
)
_CRAFT_EXP = frozenset({"craft", "salvage", "upgrade_item", "production", "carve", "settle"})
_WEAPON_EXP = frozenset({"attack", "parry"})
_RECIPE_KINDS = frozenset({"recipe", "production_action"})
_ACTIVE_KINDS = frozenset({"ability", "action", "amplifier", "passive", "control_action"})
_COLOR_TAG = re.compile(r"\[/?color(?:=[^\]]+)?\]", re.I)
_PLACEHOLDER = re.compile(r"::([a-zA-Z0-9_]+)")
_PERCENT_EFFECTS = frozenset(
    {
        "attack_on_parry",
        "bonus_damage_percent",
        "critical_hit",
        "damage_bonus_percent",
        "damage_reduce_percent",
        "dodge",
        "health_bonus_percent",
        "hit_chance",
        "parry_chance",
        "resistance_percent",
        "resting_bonus",
        "statistic_percent",
    }
)
_KIND_LABEL = {
    "ability": "Ability",
    "action": "World action",
    "amplifier": "Amplifier",
    "control_action": "Control action",
    "passive": "Passive",
    "production_action": "World action",
    "recipe": "Recipe",
    "stat": "Statistic",
}

_CACHE: Dict[str, Any] = {"key": None, "overlay": None}


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None


def user_settings_path() -> Optional[Path]:
    raw = os.environ.get("SOULASH2_USER_SETTINGS")
    if raw:
        p = Path(raw)
        return p if p.is_file() else None
    p = Path(os.environ.get("APPDATA") or "") / "WizardsOfTheCode" / "Soulash2" / "data" / "user_settings.json"
    return p if p.is_file() else None


def plans_dir() -> Path:
    d = output_root() / "plans"
    d.mkdir(parents=True, exist_ok=True)
    return d


def enabled_mod_ids() -> List[str]:
    path = user_settings_path()
    if not path:
        return ["core_2"]
    data = _load_json(path)
    ids = list((data or {}).get("mods") or [])
    if "core_2" not in ids:
        ids.insert(0, "core_2")
    return [str(x) for x in ids]


def resolve_mod(mod_id: str) -> Optional[Path]:
    sid = str(mod_id or "").strip()
    if not sid:
        return None
    local = mods_dir() / sid
    if (local / "mod.json").is_file() and not skip_mod_path(local):
        return local
    ws = workshop_root()
    if ws:
        remote = ws / sid
        if (remote / "mod.json").is_file() and not skip_mod_path(remote):
            return remote
    return None


def _mod_meta(folder: Path, fallback_id: str) -> Dict[str, Any]:
    mod = _load_json(folder / "mod.json") or {}
    return {
        "id": fallback_id,
        "name": str(mod.get("name") or fallback_id),
        "author": str(mod.get("author") or ""),
        "description": str(mod.get("description") or ""),
        "version": str(mod.get("version") or ""),
        "path": str(folder),
        "has_skills": (folder / "skills.json").is_file(),
        "has_character": (folder / "character.json").is_file(),
        "has_milestones": (folder / "milestones").is_dir(),
    }


def list_available_mods() -> List[Dict[str, Any]]:
    seen: Dict[str, Dict[str, Any]] = {}
    enabled = set(enabled_mod_ids())
    roots: List[Tuple[str, Path]] = [("local", mods_dir())]
    ws = workshop_root()
    if ws:
        roots.append(("workshop", ws))
    for origin, root in roots:
        if not root.is_dir():
            continue
        for folder in sorted(root.iterdir()):
            if not folder.is_dir() or folder.name.startswith("_") or skip_mod_path(folder):
                continue
            if not (folder / "mod.json").is_file():
                continue
            row = _mod_meta(folder, folder.name)
            row["origin"] = origin
            row["enabled"] = folder.name in enabled or row["id"] in enabled
            seen[folder.name] = row
    if "core_2" not in seen:
        core = core2_dir()
        if (core / "mod.json").is_file():
            row = _mod_meta(core, "core_2")
            row["origin"] = "local"
            row["enabled"] = True
            seen["core_2"] = row
    rows = list(seen.values())
    rows.sort(key=lambda r: (0 if r["id"] == "core_2" else 1, not r.get("enabled"), r.get("name") or r["id"]))
    return rows


def _merge_character(base: Dict[str, Any], extra: Dict[str, Any]) -> None:
    if not isinstance(extra, dict):
        return
    for key, val in extra.items():
        if key == "races" and isinstance(val, list):
            by_id = {str(r.get("id")): r for r in (base.get("races") or []) if isinstance(r, dict) and r.get("id") is not None}
            for race in val:
                if not isinstance(race, dict) or race.get("id") is None:
                    continue
                rid = str(race["id"])
                if rid in by_id:
                    by_id[rid].update(race)
                else:
                    copied = deepcopy(race)
                    by_id[rid] = copied
                    base.setdefault("races", []).append(copied)
            continue
        if key in ("production_actions", "control_actions", "tags", "base_items", "base_abilities", "base_recipes"):
            continue
        base[key] = deepcopy(val)


def _milestone_kind(row: Dict[str, Any]) -> Tuple[str, str]:
    rewards = row.get("rewards") or []
    if rewards and isinstance(rewards[0], dict) and rewards[0]:
        kind, rid = next(iter(rewards[0].items()))
        return str(kind), str(rid)
    return "", ""


def _iter_milestones(folder: Path) -> Iterable[Dict[str, Any]]:
    root = folder / "milestones"
    if not root.is_dir():
        return
    for path in root.rglob("*.json"):
        if "translations" in path.parts:
            continue
        row = _load_json(path)
        if not isinstance(row, dict):
            continue
        if not row.get("skill_id"):
            parent = path.parent.name
            row["skill_id"] = parent
        yield row


def _skill_max(skill: Dict[str, Any], miles: Sequence[Dict[str, Any]]) -> int:
    levels = []
    for m in miles:
        if m.get("innate"):
            continue
        lv = (m.get("requirements") or {}).get("skill")
        if lv is not None:
            try:
                levels.append(int(lv))
            except (TypeError, ValueError):
                pass
    for n in skill.get("stat_points") or []:
        try:
            levels.append(int(n))
        except (TypeError, ValueError):
            pass
    hi = max(levels) if levels else 0
    if hi >= 40:
        return max(hi, 50)
    if hi:
        return max(hi, 30)
    if skill.get("combat_skill") is False:
        return 30
    return 50


_SHEET_FALLBACKS = (
    "assets/gfx/skills/skills.png",
    "assets/skills.png",
    "gfx/skills/skills.png",
)
_SKILL_PNG_GLOBS = (
    "assets/skill*.png",
    "assets/skills*.png",
    "temp_art/skill*.png",
    "assets/gfx/skills/*.png",
)
_CELL_GUESSES = (30, 32, 23, 20, 64, 128)


def _png_size(path: Path) -> Optional[Tuple[int, int]]:
    try:
        with path.open("rb") as fh:
            if fh.read(8) != b"\x89PNG\r\n\x1a\n":
                return None
            length = int.from_bytes(fh.read(4), "big")
            if fh.read(4) != b"IHDR" or length < 8:
                return None
            width = int.from_bytes(fh.read(4), "big")
            height = int.from_bytes(fh.read(4), "big")
            return width, height
    except OSError:
        return None


def _infer_sheet_grid(path: Path) -> Tuple[int, int]:
    size = _png_size(path)
    if not size:
        return 0, 0
    width, height = size
    if width <= 0 or height <= 0:
        return 0, 0
    for cell in _CELL_GUESSES:
        if width % cell == 0 and height % cell == 0:
            cols = width // cell
            rows = height // cell
            if cols * rows == 1 or (cols >= 1 and rows >= 1):
                return cols, rows
    return 1, 1


def _sheet_from_png(path: Path, cols: int = 0, rows: int = 0) -> Dict[str, Any]:
    if not cols or not rows:
        inferred = _infer_sheet_grid(path)
        cols = cols or inferred[0]
        rows = rows or inferred[1]
    return {"file": str(path.resolve()), "cols": cols, "rows": rows}


def skills_sheet(folder: Path) -> Optional[Dict[str, Any]]:
    """Point at this mod's existing skills tilesheet. Does not extract or copy pixels."""
    assets = _load_json(folder / "assets.json")
    if isinstance(assets, dict):
        for sheet in ((assets.get("graphics") or {}).get("tilesheets") or []):
            if not isinstance(sheet, dict) or str(sheet.get("name") or "") not in {"skills", "skill"}:
                continue
            rel = str(sheet.get("file") or "").replace("\\", "/").lstrip("/")
            if not rel:
                continue
            path = folder / rel
            if not path.is_file():
                continue
            tiles = sheet.get("tiles") or [1, 1]
            try:
                cols = max(1, int(tiles[0]))
                rows = max(1, int(tiles[1] if len(tiles) > 1 else 1))
            except (TypeError, ValueError, IndexError):
                cols, rows = 1, 1
            return _sheet_from_png(path, cols, rows)
    for rel in _SHEET_FALLBACKS:
        path = folder / rel
        if path.is_file():
            return _sheet_from_png(path)
    hits: List[Path] = []
    for pattern in _SKILL_PNG_GLOBS:
        hits.extend(p for p in folder.glob(pattern) if p.is_file())
    uniq: List[Path] = []
    seen = set()
    for path in hits:
        key = str(path.resolve())
        if key in seen:
            continue
        seen.add(key)
        uniq.append(path)
    if len(uniq) == 1:
        return _sheet_from_png(uniq[0])
    named = [p for p in uniq if "skill" in p.stem.lower()]
    if len(named) == 1:
        return _sheet_from_png(named[0])
    return None


def _sheet_capacity(sheet: Dict[str, Any]) -> int:
    cols = int(sheet.get("cols") or 0)
    rows = int(sheet.get("rows") or 0)
    if cols and rows:
        return cols * rows
    return 10_000


def pick_skill_sheet(
    source: str,
    image: int,
    sheets: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Use the source mod's sheet when it has that tile; otherwise vanilla core_2."""
    src = sheets.get(str(source) or "")
    if src and 0 <= int(image) < _sheet_capacity(src):
        return src
    core = sheets.get("core_2")
    if core and 0 <= int(image) < _sheet_capacity(core):
        return core
    return src or core or {}


_SHEET_IMAGES: Dict[str, Tuple[int, Any]] = {}


def _cached_sheet(path: str) -> Optional[Any]:
    file = Path(path)
    if not file.is_file():
        return None
    key = str(file.resolve())
    mtime = int(file.stat().st_mtime_ns)
    hit = _SHEET_IMAGES.get(key)
    if hit and hit[0] == mtime:
        return hit[1]
    try:
        from PIL import Image

        img = Image.open(file).convert("RGBA")
    except Exception:
        return None
    _SHEET_IMAGES[key] = (mtime, img)
    return img


def crop_skill_tile(
    path: str,
    index: int,
    cols: int,
    rows: int,
    *,
    tile: int = TILE,
) -> Optional[Any]:
    """Crop one cell from a live tilesheet PNG. Index 0 is the bottom-left cell."""
    img = _cached_sheet(path)
    if img is None:
        return None
    try:
        from PIL import Image
    except ImportError:
        return None
    w, h = img.size
    cell_guess = tile if w >= tile and h >= tile else max(1, min(w, h))
    inf_cols = max(1, w // cell_guess)
    inf_rows = max(1, h // cell_guess)
    cols = max(1, int(cols or inf_cols))
    rows = max(1, int(rows or inf_rows))
    idx = max(0, int(index))
    if idx >= cols * rows:
        cols, rows = inf_cols, inf_rows
    if idx >= cols * rows:
        return None
    cell = min(max(1, w // cols), max(1, h // rows))
    col = idx % cols
    row_from_bottom = idx // cols
    x = col * cell
    y = (rows - 1 - row_from_bottom) * cell
    crop = img.crop((x, y, x + cell, y + cell))
    if cell != tile:
        crop = crop.resize((tile, tile), Image.Resampling.NEAREST)
    return crop


def classify_skill(skill: Dict[str, Any], tree: Optional[Sequence[Dict[str, Any]]] = None) -> str:
    """Split skills the way the book does: weapon / magic combat, crafting, or use."""
    combat = skill.get("combat_skill") is True or skill.get("combat") is True
    exp = skill.get("exp_sources") or []
    exp_ids = [str(e.get("id") or "") for e in exp if isinstance(e, dict)]
    armed = skill.get("weapon_type") is not None or any(eid in _WEAPON_EXP for eid in exp_ids)
    if combat:
        return KIND_WEAPON if armed else KIND_MAGIC
    use_hits = sum(1 for eid in exp_ids if eid in _USE_EXP)
    craft_hits = sum(1 for eid in exp_ids if eid in _CRAFT_EXP)
    if use_hits or craft_hits:
        return KIND_USE if use_hits > craft_hits else KIND_CRAFT
    rows = list(tree if tree is not None else skill.get("tree") or [])
    kinds = [str(row.get("kind") or "") for row in rows]
    recipe_like = sum(1 for kind in kinds if kind in _RECIPE_KINDS)
    active_like = sum(1 for kind in kinds if kind in _ACTIVE_KINDS)
    if recipe_like > active_like:
        return KIND_CRAFT
    return KIND_USE


def _compact_tree(skill: Dict[str, Any], miles: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for m in miles:
        level = (m.get("requirements") or {}).get("skill")
        if m.get("innate"):
            level = "innate"
        kind, rid = _milestone_kind(m)
        rows.append(
            {
                "level": level,
                "id": m.get("id"),
                "name": m.get("name"),
                "kind": kind,
                "reward": rid,
            }
        )
    for lv in skill.get("stat_points") or []:
        try:
            n = int(lv)
        except (TypeError, ValueError):
            continue
        rows.append({"level": n, "id": f"stat_{n}", "name": "+1 statistic", "kind": "stat", "reward": ""})

    def _key(row: Dict[str, Any]) -> tuple:
        lv = row["level"]
        if lv == "innate":
            return (-1, 0, str(row.get("name") or ""))
        try:
            n = int(lv)
        except (TypeError, ValueError):
            return (10_000, 0, str(row.get("name") or ""))
        rank = 0 if row.get("kind") == "stat" else 1
        return (n, rank, str(row.get("name") or ""))

    rows.sort(key=_key)
    return rows


def _strip_color(text: str) -> str:
    raw = _COLOR_TAG.sub("", str(text or "")).replace("::elder_age", "elder age")
    parts = [p.strip() for p in re.split(r"\n\s*\n", raw) if p.strip()]
    return "\n\n".join(" ".join(p.split()) for p in parts)


def _fmt_token(value: Any) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (list, tuple)):
        if len(value) == 2:
            return f"{_fmt_token(value[0])}-{_fmt_token(value[1])}"
        return ", ".join(_fmt_token(v) for v in value)
    if isinstance(value, float):
        if value == int(value):
            return str(int(value))
        return f"{value:g}"
    return str(value)


def _fmt_pct(value: Any) -> str:
    try:
        n = float(value)
    except (TypeError, ValueError):
        return str(value)
    pct = n * 100.0 if abs(n) <= 1 else n
    if pct == int(pct):
        return f"{int(pct)}%"
    return f"{pct:g}%"


def _is_percent_effect(eid: str, key: str) -> bool:
    if eid == "statistic_percent" and key == "value":
        return False
    if eid == "damage_type_reduction" and key == "secondary_value":
        return True
    if eid == "increase_effect_value" and key == "secondary_value":
        return True
    if eid.endswith("_percent") or "percent" in eid or eid in _PERCENT_EFFECTS:
        return True
    return False


def _fmt_effect_line(row: Dict[str, Any]) -> str:
    eid = str(row.get("effect") or "").strip()
    if not eid:
        return ""
    label = eid.replace("_", " ")
    parts: List[str] = []
    for key in ("value", "secondary_value", "third_value"):
        if key not in row or row[key] is None:
            continue
        val = row[key]
        if _is_percent_effect(eid, key) and isinstance(val, (int, float)) and not isinstance(val, bool):
            parts.append(_fmt_pct(val))
        else:
            parts.append(_fmt_token(val))
    return f"{label}: {' / '.join(parts)}" if parts else label


def _ability_tokens(ability: Dict[str, Any]) -> Dict[str, Any]:
    tokens: Dict[str, Any] = {}
    for key, val in ability.items():
        if key in ("effects", "effects_keys", "cost", "slots", "description", "animation", "image"):
            continue
        if isinstance(val, (dict, list)) and key not in ("damage",):
            continue
        tokens[str(key)] = val
    cost = ability.get("cost")
    if isinstance(cost, dict):
        tokens.update({str(k): v for k, v in cost.items()})
    effects = ability.get("effects")
    if isinstance(effects, dict):
        tokens.update({str(k): v for k, v in effects.items()})
    keys = ability.get("effects_keys")
    if isinstance(keys, dict):
        tokens.update({str(k): v for k, v in keys.items()})
    return tokens


def _fill_placeholders(text: str, tokens: Dict[str, Any]) -> str:
    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        if key in tokens and tokens[key] is not None:
            return _fmt_token(tokens[key])
        return match.group(0)

    return _PLACEHOLDER.sub(repl, text)


def _ability_stats(ability: Dict[str, Any]) -> str:
    bits: List[str] = []
    target = ability.get("target")
    if target:
        bits.append(f"target {target}")
    rng = ability.get("range")
    if rng not in (None, "", 0, 0.0):
        bits.append(f"range {_fmt_token(rng)}")
    min_range = ability.get("min_range")
    if min_range not in (None, "", 0, 0.0):
        bits.append(f"min {_fmt_token(min_range)}")
    aoe = (ability.get("effects") or {}).get("aoe_range") if isinstance(ability.get("effects"), dict) else None
    if aoe in (None, ""):
        aoe = ability.get("aoe_range")
    if aoe not in (None, "", 0, 0.0):
        bits.append(f"aoe {_fmt_token(aoe)}")
    cost = ability.get("cost") if isinstance(ability.get("cost"), dict) else {}
    stam = cost.get("stamina")
    if stam not in (None, "", 0, 0.0):
        bits.append(f"stamina {_fmt_token(stam)}")
    hp = cost.get("health")
    if hp not in (None, "", 0, 0.0):
        bits.append(f"health {_fmt_token(hp)}")
    cd = ability.get("cooldown")
    if cd not in (None, "", 0, 0.0):
        bits.append(f"cooldown {_fmt_token(cd)}")
    cast = ability.get("cast_time")
    if cast not in (None, "", 0, 0.0):
        bits.append(f"cast {_fmt_token(cast)}")
    dur = ability.get("duration")
    if dur not in (None, "", 0, 0.0):
        bits.append(f"duration {_fmt_token(dur)}")
    slots = ability.get("slots") if isinstance(ability.get("slots"), dict) else {}
    slot_bits = []
    for color in ("offensive", "utility", "defensive"):
        n = slots.get(color)
        if n not in (None, "", 0, 0.0):
            slot_bits.append(f"{_fmt_token(n)} {color}")
    if slot_bits:
        bits.append("slots " + ", ".join(slot_bits))
    return " · ".join(bits)


def _summarize_ability(ability: Optional[Dict[str, Any]], name: str) -> str:
    if not isinstance(ability, dict):
        return f"Unlocks ability {name}." if name else "Unlocks an ability."
    tokens = _ability_tokens(ability)
    desc = _fill_placeholders(_strip_color(ability.get("description") or ""), tokens)
    lines = [desc] if desc else [f"Unlocks ability {ability.get('name') or name}."]
    stats = _ability_stats(ability)
    if stats:
        lines.append(stats)
    extras: List[str] = []
    effects = ability.get("effects") if isinstance(ability.get("effects"), dict) else {}
    skip = {"damage", "damage_type", "heal", "aoe_range", "magic_power_damage"}
    for key, val in effects.items():
        if key in skip or val in (None, "", 0, 0.0, False):
            continue
        extras.append(f"{key.replace('_', ' ')} {_fmt_token(val)}")
    keys = ability.get("effects_keys") if isinstance(ability.get("effects_keys"), dict) else {}
    for key, val in keys.items():
        if val in (None, ""):
            continue
        extras.append(f"{key.replace('_', ' ')} {val}")
    if extras:
        lines.append("Also: " + ", ".join(extras[:8]))
    return "\n".join(line for line in lines if line)


def _amp_fields(amp: Dict[str, Any]) -> str:
    bits: List[str] = []
    kind = amp.get("type")
    if kind:
        bits.append(str(kind))
    for key, label in (
        ("range", "range"),
        ("cooldown", "cooldown"),
        ("cost_stamina", "stamina"),
        ("cast_time", "cast"),
    ):
        val = amp.get(key)
        if val in (None, "", 0, 0.0):
            continue
        shown = _fmt_token(val)
        if isinstance(val, (int, float)) and not isinstance(val, bool) and val > 0 and key != "range":
            shown = f"+{shown}"
        bits.append(f"{label} {shown}")
    return " · ".join(bits)


def _summarize_amplifier(amp: Optional[Dict[str, Any]], name: str) -> str:
    if not isinstance(amp, dict):
        return f"Unlocks amplifier {name}." if name else "Unlocks an amplifier socket bonus."
    lines: List[str] = []
    desc = _strip_color(amp.get("description") or "")
    if desc:
        lines.append(desc)
    else:
        lines.append(f"Amplifier: {amp.get('name') or name}.")
    fields = _amp_fields(amp)
    if fields:
        lines.append(fields)
    bonuses = [row for row in (amp.get("bonuses") or []) if isinstance(row, dict)]
    fx = [_fmt_effect_line(row) for row in bonuses]
    fx = [x for x in fx if x]
    if fx:
        lines.append("Bonuses: " + "; ".join(fx))
    return "\n".join(lines)


def _summarize_passive(passive: Optional[Dict[str, Any]], name: str) -> str:
    if not isinstance(passive, dict):
        return f"Unlocks passive {name}." if name else "Unlocks a passive."
    lines = [f"Passive: {passive.get('name') or name}."]
    restrict = passive.get("restrict_weapon_type")
    if restrict:
        lines.append(f"Requires {str(restrict).replace('_', ' ')} weapons.")
    fx = [_fmt_effect_line(row) for row in (passive.get("effects") or []) if isinstance(row, dict)]
    fx = [x for x in fx if x]
    if fx:
        lines.append("Effects: " + "; ".join(fx))
    else:
        lines.append("Always-on effect. In-game tooltip is generated from the effects list.")
    return "\n".join(lines)


def _summarize_recipe(entity: Optional[Dict[str, Any]], name: str, rid: str) -> str:
    title = ""
    desc = ""
    if isinstance(entity, dict):
        title = str(entity.get("name") or "")
        desc = _strip_color(entity.get("description") or "")
    label = title or name or rid
    lines = [f"Unlocks the crafting recipe for {label}."]
    if desc:
        lines.append(desc)
    return "\n".join(lines)


def _summarize_action(obj: Optional[Dict[str, Any]], name: str, kind: str) -> str:
    label = _KIND_LABEL.get(kind, kind.replace("_", " "))
    if not isinstance(obj, dict):
        return f"Unlocks {label.lower()} {name}." if name else f"Unlocks a {label.lower()}."
    title = str(obj.get("name") or name or obj.get("id") or label)
    desc = _strip_color(obj.get("description") or "")
    lines = [f"{label}: {title}."]
    if desc:
        lines.append(desc)
    tool = obj.get("required_tool")
    if tool not in (None, "", -1, "-1"):
        lines.append(f"Requires tool type {tool}.")
    return "\n".join(lines)


def summarize_unlock(row: Dict[str, Any], catalog: Optional[Dict[str, Dict[str, Any]]] = None) -> str:
    """Human-readable blurb for a skill-tree milestone."""
    catalog = catalog or {}
    kind = str(row.get("kind") or "")
    rid = str(row.get("reward") or "")
    name = str(row.get("name") or rid or kind)
    if kind == "stat":
        return "Grants +1 to a statistic when this skill level is reached."
    if not kind:
        return f"{name}." if name else "This milestone has no listed reward."
    obj = (catalog.get(kind) or {}).get(rid) if rid else None
    if obj is None and rid:
        if kind in ("action", "production_action"):
            obj = (catalog.get("production_action") or {}).get(rid)
        if obj is None and kind in ("action", "control_action"):
            obj = (catalog.get("control_action") or {}).get(rid)
    if kind == "ability":
        return _summarize_ability(obj, name)
    if kind == "amplifier":
        return _summarize_amplifier(obj, name)
    if kind == "passive":
        return _summarize_passive(obj, name)
    if kind == "recipe":
        return _summarize_recipe(obj, name, rid)
    if kind in ("production_action", "control_action", "action"):
        return _summarize_action(obj, name, kind)
    if isinstance(obj, dict):
        desc = _strip_color(obj.get("description") or "")
        if desc:
            return desc
    return f"Unlocks {kind.replace('_', ' ')}{(' ' + name) if name else ''}."


def _train_line(skill: Dict[str, Any]) -> str:
    names: List[str] = []
    for row in skill.get("exp_sources") or []:
        if not isinstance(row, dict):
            continue
        eid = str(row.get("id") or "").replace("_", " ")
        if not eid:
            continue
        if eid == "production" and row.get("production_action"):
            names.append(f"production ({row['production_action']})")
        else:
            names.append(eid)
    names = list(dict.fromkeys(names))
    return "Train by: " + ", ".join(names) if names else ""


def skill_tooltip_text(skill: Dict[str, Any]) -> str:
    name = str(skill.get("name") or skill.get("id") or "Skill")
    lines = [name]
    meta = [str(skill.get("kind") or "").strip()]
    src = str(skill.get("source") or "").strip()
    if src:
        meta.append(src)
    max_level = skill.get("max_level")
    if max_level not in (None, ""):
        meta.append(f"max {max_level}")
    weapon = skill.get("weapon_type")
    if weapon not in (None, ""):
        meta.append(str(weapon).replace("_", " "))
    lines.append(" · ".join(x for x in meta if x))
    desc = _strip_color(skill.get("description") or "")
    if desc:
        lines.append("")
        lines.append(desc)
    train = _train_line(skill)
    if train:
        lines.append("")
        lines.append(train)
    return "\n".join(lines).strip()


def tree_row_tooltip_text(row: Dict[str, Any]) -> str:
    kind = str(row.get("kind") or "stat")
    label = _KIND_LABEL.get(kind, kind.replace("_", " ") or "Unlock")
    name = str(row.get("name") or row.get("reward") or label)
    level = row.get("level")
    lv = "innate" if level == "innate" else (f"level {level}" if level not in (None, "") else "")
    head = " · ".join(x for x in (name, label, lv) if x)
    body = str(row.get("summary") or "").strip()
    if body and body != head:
        return f"{head}\n{body}"
    return head or body


def _index_id_rows(blob: Any, dest: Dict[str, Any]) -> None:
    rows = blob if isinstance(blob, list) else ([blob] if isinstance(blob, dict) and blob.get("id") is not None else [])
    for row in rows:
        if isinstance(row, dict) and row.get("id") is not None:
            dest[str(row["id"])] = row


def _index_mod_unlocks(
    folder: Path,
    catalog: Dict[str, Dict[str, Any]],
    *,
    character: Optional[Dict[str, Any]] = None,
) -> None:
    abil = folder / "abilities"
    if abil.is_dir():
        for path in abil.glob("*.json"):
            data = _load_json(path)
            if isinstance(data, list):
                _index_id_rows(data, catalog["ability"])
            elif isinstance(data, dict) and data.get("id") is not None:
                catalog["ability"][str(data["id"])] = data
    _index_id_rows(_load_json(folder / "passives.json"), catalog["passive"])
    amps = _load_json(folder / "ability_amplifiers.json")
    if amps is None:
        amps = _load_json(folder / "amplifiers.json")
    _index_id_rows(amps, catalog["amplifier"])
    char = character if isinstance(character, dict) else _load_json(folder / "character.json")
    if isinstance(char, dict):
        _index_id_rows(char.get("production_actions"), catalog["production_action"])
        _index_id_rows(char.get("control_actions"), catalog["control_action"])


def _empty_catalog() -> Dict[str, Dict[str, Any]]:
    return {
        "ability": {},
        "amplifier": {},
        "passive": {},
        "production_action": {},
        "control_action": {},
        "recipe": {},
        "action": {},
    }


def _resolve_recipes(folders: Sequence[Path], ids: Sequence[str]) -> Dict[str, Any]:
    remaining = {str(x) for x in ids if str(x)}
    found: Dict[str, Any] = {}
    if not remaining:
        return found
    for folder in folders:
        ent = folder / "entities"
        if not ent.is_dir():
            continue
        for rid in list(remaining):
            paths: List[Path] = []
            exact = ent / f"{rid}.json"
            if exact.is_file():
                paths.append(exact)
            paths.extend(path for path in sorted(ent.glob(f"{rid}_*.json")) if path not in paths)
            for path in paths:
                data = _load_json(path)
                if isinstance(data, dict) and str(data.get("id")) == rid:
                    found[rid] = data
                    remaining.discard(rid)
                    break
        if not remaining:
            break
    return found


def _attach_tooltips(skill_list: Sequence[Dict[str, Any]], catalog: Dict[str, Dict[str, Any]]) -> None:
    for skill in skill_list:
        skill["tooltip"] = skill_tooltip_text(skill)
        for row in skill.get("tree") or []:
            row["summary"] = summarize_unlock(row, catalog)
            row["tooltip"] = tree_row_tooltip_text(row)


def load_overlay(mod_ids: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    ids = [str(x) for x in (mod_ids if mod_ids is not None else enabled_mod_ids())]
    if "core_2" not in ids:
        ids = ["core_2"] + ids
    key = "|".join(ids)
    if _CACHE.get("key") == key and _CACHE.get("overlay"):
        return _CACHE["overlay"]

    character: Dict[str, Any] = {}
    skills: Dict[str, Dict[str, Any]] = {}
    miles_by_skill: Dict[str, List[Dict[str, Any]]] = {}
    loaded: List[Dict[str, Any]] = []
    missing: List[str] = []
    sheets: Dict[str, Dict[str, Any]] = {}
    catalog = _empty_catalog()
    folders: List[Path] = []

    for mid in ids:
        if skip_mod_path(Path(mid)):
            continue
        folder = resolve_mod(mid)
        if folder is None:
            missing.append(mid)
            continue
        meta = _mod_meta(folder, mid)
        loaded.append(meta)
        folders.append(folder)
        sheet = skills_sheet(folder)
        if sheet:
            sheets[mid] = sheet
        char = _load_json(folder / "character.json")
        if isinstance(char, dict):
            _merge_character(character, char)
        _index_mod_unlocks(folder, catalog, character=char if isinstance(char, dict) else None)
        blob = _load_json(folder / "skills.json")
        skill_rows = blob if isinstance(blob, list) else ([blob] if isinstance(blob, dict) else [])
        for skill in skill_rows:
            if not isinstance(skill, dict) or not skill.get("id"):
                continue
            sid = str(skill["id"])
            row = deepcopy(skill)
            row["_source"] = mid
            skills[sid] = row
        for mile in _iter_milestones(folder):
            sid = str(mile.get("skill_id") or "")
            if not sid:
                continue
            miles_by_skill.setdefault(sid, []).append(mile)

    skill_list: List[Dict[str, Any]] = []
    for sid, skill in skills.items():
        miles = miles_by_skill.get(sid) or []
        max_level = _skill_max(skill, miles)
        tree = _compact_tree(skill, miles)
        kind = classify_skill(skill, tree)
        src = str(skill.get("_source") or "")
        try:
            image = int(skill.get("image") or 0)
        except (TypeError, ValueError):
            image = 0
        sheet = pick_skill_sheet(src, image, sheets)
        skill_list.append(
            {
                "id": sid,
                "name": skill.get("name") or sid,
                "source": src,
                "kind": kind,
                "combat": kind in (KIND_WEAPON, KIND_MAGIC),
                "combat_skill": skill.get("combat_skill"),
                "weapon_type": skill.get("weapon_type"),
                "image": image,
                "icon_file": sheet.get("file") or "",
                "icon_cols": int(sheet.get("cols") or 0),
                "icon_rows": int(sheet.get("rows") or 0),
                "exp_sources": list(skill.get("exp_sources") or []),
                "description": skill.get("description") or "",
                "difficulty": skill.get("difficulty"),
                "max_level": max_level,
                "stat_points": [int(x) for x in (skill.get("stat_points") or []) if str(x).lstrip("-").isdigit()],
                "tree": tree,
                "milestone_count": len(miles),
            }
        )
    skill_list.sort(key=lambda s: (KIND_ORDER.get(s.get("kind") or "", 9), str(s.get("name") or "").lower()))
    recipe_ids = [
        str(row.get("reward") or "")
        for skill in skill_list
        for row in (skill.get("tree") or [])
        if row.get("kind") == "recipe" and row.get("reward")
    ]
    catalog["recipe"].update(_resolve_recipes(folders, recipe_ids))
    _attach_tooltips(skill_list, catalog)

    races: List[Dict[str, Any]] = []
    for race in character.get("races") or []:
        if not isinstance(race, dict) or not race.get("id"):
            continue
        ages = race.get("ages") or {}
        races.append(
            {
                "id": str(race.get("id")),
                "name": str(race.get("name") or race.get("id")),
                "playable": bool(race.get("playable")),
                "description": str(race.get("description") or ""),
                "tooltip": _strip_color(str(race.get("description") or "")),
                "ages": {
                    "child": _age_int(ages, "child", 14) if ages else None,
                    "adult": _age_int(ages, "adult", 50) if ages else None,
                    "elder": _age_int(ages, "elder", 70) if ages else None,
                },
                "statistics": dict(race.get("statistics") or {}),
                "passives": list(race.get("passives") or []),
                "abilities": list(race.get("abilities") or []),
            }
        )
    races.sort(key=lambda r: (not r.get("playable"), str(r.get("name") or "").lower()))

    overlay = {
        "mods": loaded,
        "missing": missing,
        "max_potential": int(character.get("max_potential") or 200),
        "gold_for_potential": dict(character.get("gold_for_potential") or {}),
        "floor": FLOOR,
        "starting_count": STARTING_COUNT,
        "starting_bonus": STARTING_BONUS,
        "age_bonus": {"middle": AGE_BONUS_MIDDLE, "elder": AGE_BONUS_ELDER},
        "skills": skill_list,
        "races": races,
        "game": str(soulash2_root()),
        "user_settings": str(user_settings_path() or ""),
    }
    _CACHE["key"] = key
    _CACHE["overlay"] = overlay
    return overlay


def _age_int(ages: Dict[str, Any], key: str, default: int) -> int:
    raw = ages.get(key)
    if raw is None or raw == "":
        return default
    return int(raw)


def race_age_plan(race: Dict[str, Any]) -> Dict[str, Any]:
    ages = race.get("ages") or {}
    child = _age_int(ages, "child", 14)
    adult = _age_int(ages, "adult", 50)
    elder = _age_int(ages, "elder", 70)
    start = child + 1
    practical = adult < 1000
    return {
        "start": start,
        "child": child,
        "middle_at": adult,
        "elder_at": elder,
        "practical_aging": practical,
        "young": {"from": start, "to": adult, "bonus": 0, "label": "young adult"},
        "middle": {"from": adult, "to": elder, "bonus": AGE_BONUS_MIDDLE if practical else 0, "label": "middle-aged"},
        "elder": {"from": elder, "to": None, "bonus": AGE_BONUS_ELDER if practical else 0, "label": "elder"},
    }


def gold_to_raise(table: Dict[str, Any], start: int, target: int) -> int:
    if target <= start:
        return 0
    total = 0
    default = int(table.get("default") or 5000)
    for n in range(start + 1, target + 1):
        cost = default
        for b in GOLD_BRACKETS:
            if n <= b:
                cost = int(table.get(str(b), default))
                break
        total += cost
    return total


def _skill_floor(sid: str, starting: Sequence[str]) -> int:
    return FLOOR + (STARTING_BONUS if sid in starting else 0)


def empty_stage_plans(
    skills: Sequence[Dict[str, Any]],
    starting: Sequence[str],
) -> Dict[str, Dict[str, int]]:
    picks = {str(x) for x in starting}
    base: Dict[str, int] = {}
    for skill in skills:
        sid = str(skill["id"])
        base[sid] = _skill_floor(sid, picks)
    return {stage: dict(base) for stage in STAGES}


def normalize_stage_plans(
    skills: Sequence[Dict[str, Any]],
    starting: Sequence[str],
    plans: Optional[Dict[str, Any]] = None,
    *,
    legacy_allocations: Optional[Dict[str, Any]] = None,
) -> Dict[str, Dict[str, int]]:
    """Build young/middle/elder plans. Lifetime rule: young <= middle <= elder per skill."""
    out = empty_stage_plans(skills, starting)
    caps = {str(s["id"]): int(s.get("max_level") or 50) for s in skills}
    picks = [str(x) for x in starting]

    def _clamp(sid: str, raw: Any) -> int:
        flo = _skill_floor(sid, picks)
        cap = caps.get(sid, 50)
        try:
            val = int(raw)
        except (TypeError, ValueError):
            val = flo
        return max(flo, min(cap, val))

    raw_plans = plans if isinstance(plans, dict) else {}
    for stage in STAGES:
        bucket = raw_plans.get(stage)
        if isinstance(bucket, dict):
            for sid in out[stage]:
                if sid in bucket:
                    out[stage][sid] = _clamp(sid, bucket[sid])

    # Legacy single allocation map → seed every stage (then enforce monotonic).
    if legacy_allocations and isinstance(legacy_allocations, dict):
        for sid in out["elder"]:
            if sid in legacy_allocations:
                val = _clamp(sid, legacy_allocations[sid])
                for stage in STAGES:
                    if sid not in (raw_plans.get(stage) or {}):
                        out[stage][sid] = val

    # Enforce young <= middle <= elder.
    for sid in out["young"]:
        y = out["young"][sid]
        m = max(y, out["middle"][sid])
        e = max(m, out["elder"][sid])
        out["young"][sid] = y
        out["middle"][sid] = m
        out["elder"][sid] = e
    return out


def set_stage_allocation(
    plans: Dict[str, Dict[str, int]],
    *,
    stage: str,
    skill_id: str,
    value: int,
    skills: Sequence[Dict[str, Any]],
    starting: Sequence[str],
) -> Dict[str, Dict[str, int]]:
    """Edit one stage; bump later stages up, and clamp to earlier stages as a floor."""
    stage = str(stage or "elder").lower()
    if stage not in STAGES:
        stage = "elder"
    sid = str(skill_id)
    caps = {str(s["id"]): int(s.get("max_level") or 50) for s in skills}
    flo = _skill_floor(sid, starting)
    cap = caps.get(sid, 50)
    planned = max(flo, min(cap, int(value)))

    idx = STAGES.index(stage)
    # Floor from earlier stages (skills only grow over a lifetime).
    for earlier in STAGES[:idx]:
        planned = max(planned, int(plans.get(earlier, {}).get(sid, flo)))
    plans.setdefault(stage, {})[sid] = planned
    # Raise later stages if they fell behind.
    for later in STAGES[idx + 1 :]:
        cur = int(plans.get(later, {}).get(sid, flo))
        plans.setdefault(later, {})[sid] = max(cur, planned)
    return plans


def evaluate(
    overlay: Dict[str, Any],
    *,
    race_id: str,
    starting: Sequence[str],
    allocations: Dict[str, int],
    stage: str = "elder",
) -> Dict[str, Any]:
    skills = {s["id"]: s for s in overlay.get("skills") or []}
    races = {r["id"]: r for r in overlay.get("races") or []}
    race = races.get(str(race_id)) or next((r for r in overlay.get("races") or [] if r.get("playable")), None)
    if not race:
        raise ValueError("No race available")
    age = race_age_plan(race)
    picks = [str(x) for x in starting if str(x) in skills][:STARTING_COUNT]
    pool = int(overlay.get("max_potential") or 200)
    gold_table = overlay.get("gold_for_potential") or {}

    spent = 0
    gold = 0
    rows: List[Dict[str, Any]] = []
    for skill in overlay.get("skills") or []:
        sid = skill["id"]
        cap = int(skill.get("max_level") or 50)
        planned = int(allocations.get(sid, FLOOR + (STARTING_BONUS if sid in picks else 0)))
        planned = max(FLOOR, min(cap, planned))
        if sid in picks:
            planned = max(planned, FLOOR + STARTING_BONUS)
        from_pool = planned - FLOOR
        spent += from_pool
        gold += gold_to_raise(gold_table, FLOOR + (STARTING_BONUS if sid in picks else 0), planned)
        unlocked = [t for t in (skill.get("tree") or []) if t.get("level") == "innate" or (isinstance(t.get("level"), int) and t["level"] <= planned)]
        rows.append(
            {
                "id": sid,
                "name": skill.get("name"),
                "source": skill.get("source"),
                "kind": skill.get("kind") or classify_skill(skill),
                "combat": bool(skill.get("combat")),
                "max_level": cap,
                "planned": planned,
                "from_pool": from_pool,
                "starting": sid in picks,
                "unlocked": len(unlocked),
                "milestones": skill.get("milestone_count") or 0,
            }
        )

    bonuses = {"young": 0, "middle": age["middle"]["bonus"], "elder": age["middle"]["bonus"] + age["elder"]["bonus"]}
    key = str(stage or "elder").lower()
    if key not in bonuses:
        key = "elder"
    available = pool + bonuses[key]
    remaining = available - spent

    stats = dict(race.get("statistics") or {})
    elder_stats = dict(stats)
    if key == "elder" and age["practical_aging"]:
        for st in ("intelligence", "willpower"):
            elder_stats[st] = int(elder_stats.get(st) or 0) + ELDER_MENTAL
        for st in ("strength", "dexterity", "endurance"):
            elder_stats[st] = int(elder_stats.get(st) or 0) - ELDER_PHYSICAL

    mastery_cost = 40
    extra_full = remaining / mastery_cost if mastery_cost else 0
    return {
        "race": race,
        "age": age,
        "stage": key,
        "starting": picks,
        "pool": pool,
        "age_bonus": bonuses[key],
        "available": available,
        "spent": spent,
        "remaining": remaining,
        "over": max(0, -remaining),
        "gold": gold,
        "budgets": {
            "young": {"available": pool, "remaining": pool - spent},
            "middle": {"available": pool + bonuses["middle"], "remaining": pool + bonuses["middle"] - spent},
            "elder": {"available": pool + bonuses["elder"], "remaining": pool + bonuses["elder"] - spent},
        },
        "stats": stats,
        "stats_at_stage": elder_stats if key == "elder" else stats,
        "full_skills_left": round(extra_full, 3),
        "skills": rows,
    }


def evaluate_stages(
    overlay: Dict[str, Any],
    *,
    race_id: str,
    starting: Sequence[str],
    stage_plans: Dict[str, Dict[str, int]],
    stage: str = "elder",
) -> Dict[str, Any]:
    """Evaluate each life stage against its own allocation plan."""
    skills = overlay.get("skills") or []
    plans = normalize_stage_plans(skills, starting, stage_plans)
    key = str(stage or "elder").lower()
    if key not in STAGES:
        key = "elder"
    by_stage = {
        name: evaluate(overlay, race_id=race_id, starting=starting, allocations=plans[name], stage=name)
        for name in STAGES
    }
    current = by_stage[key]
    # Budget cards: each stage uses that stage's own spend (not one spend vs three caps).
    budgets = {
        name: {
            "available": by_stage[name]["available"],
            "remaining": by_stage[name]["remaining"],
            "spent": by_stage[name]["spent"],
        }
        for name in STAGES
    }
    current = dict(current)
    current["budgets"] = budgets
    current["stage_plans"] = plans
    current["stages"] = {
        name: {
            "available": by_stage[name]["available"],
            "spent": by_stage[name]["spent"],
            "remaining": by_stage[name]["remaining"],
            "gold": by_stage[name]["gold"],
            "over": by_stage[name]["over"],
        }
        for name in STAGES
    }
    return current


def save_plan(name: str, payload: Dict[str, Any]) -> Path:
    slug = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in (name or "plan").strip()) or "plan"
    path = plans_dir() / f"{slug}.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def list_plans() -> List[Dict[str, str]]:
    rows = []
    for path in sorted(plans_dir().glob("*.json")):
        data = _load_json(path) or {}
        rows.append(
            {
                "id": path.stem,
                "name": str(data.get("name") or path.stem),
                "path": str(path),
                "race": str((data.get("race_id") or "")),
            }
        )
    return rows


def load_plan(name: str) -> Dict[str, Any]:
    path = plans_dir() / f"{name}.json"
    if not path.is_file():
        raise FileNotFoundError(name)
    data = _load_json(path)
    if not isinstance(data, dict):
        raise ValueError(f"Bad plan file: {path}")
    return data
