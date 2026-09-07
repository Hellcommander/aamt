#!/usr/bin/env python3
"""Rebuild the water and blood skill mods through the Skill Creator CLI.

Live hydromancy / hemohydraulic folders are the *content* source (names, levels,
numbers). Layout, ids, and effect encoding follow Geomancy + the CLI — those
old folders are banned as a schema template and as install targets.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from s2_paths import mods_dir, output_root  # noqa: E402
from s2_schema import load_effects, slug_name  # noqa: E402

CLI = HERE / "s2_skill_cli.py"
MODS = mods_dir()
REC = MODS / "_recovered"
LIVE_AQUA = MODS / "arendeth_hydromancy"
LIVE_SANG = MODS / "arendeth_hemohydraulic_magic"
REC_WATER = REC / "arendeth_water_magic"
if not REC_WATER.is_dir():
    REC_WATER = REC / "from_transcript_reads" / "arendeth_water_magic"

WET = "88"
ICE_SLIVER = "core_2_Ice_Sliver"
FREEZE = "core_2_freeze"

DELAYED_STAT_POINTS = [
    13, 14, 16, 17, 19, 20, 22, 23, 25, 26, 28, 29, 31, 33, 35, 37, 39, 41, 43, 45, 47, 49
]

ABILITY_KEEP = [
    "damage",
    "damage_type",
    "magic_power_damage",
    "bleed",
    "stacker_count",
    "summon_count",
    "aoe_range",
    "knockback",
    "stun",
    "pierce",
    "lunge",
    "heal",
    "hide",
    "movement_speed",
    "chain",
    "immobilize",
    "vulnerable",
    "pull_target",
    "break_armor",
    "damage_reduce_percent",
    "damage_per_stacks",
    "duration",
    "slow",
    "fear",
    "silence",
    "thorns",
    "clear_cooldowns",
]

ABILITY_DROP = {
    "aoe_break",
    "hit_self",
    "ability_can_crit",
    "aoe_shape",
    "turn_damage_to_stacks",
}

AMP_BONUS_TO_FIELD = {
    "stamina_cost": "cost_stamina",
    "range": "range",
    "cooldown": "cooldown",
    "duration": "duration",
    "cast_time": "cast_time",
}

AMP_REWRITE = {
    "trade_places": ("pull_target", 1),
    "bonus_knockback_damage_percent": ("knockback", 1),
    "move_speed": ("movement_speed", None),
    "stamina_cost": None,  # lifted to cost_stamina
}

PASSIVE_REWRITE = {
    "movement_speed": "move_speed",
}

AQUA_PREFIXES = (
    "arendeth_hydromancy_",
    "arendeth_water_magic_",
    "arendeth_water_magic_hydromancy_",
)
SANG_PREFIXES = (
    "arendeth_hemohydraulic_magic_",
    "arendeth_hemohydraulic_magic_mastery_",
)

MISSING_SANG: List[Dict[str, Any]] = [
    {
        "name": "Capillary Rupture",
        "level": 3,
        "damage": "[2,5]",
        "target": "aoe_target",
        "range": 4,
        "stamina": 5,
        "cooldown": 3,
        "effects": ["bleed=6", "aoe_range=1", "magic_power_damage=0.8"],
        "desc": "Burst nearby capillaries for ::damage ::damage_type damage and a light hemorrhage.",
    },
    {
        "name": "Hypertensive Field",
        "level": 12,
        "damage": "[6,10]",
        "target": "aoe_tile",
        "range": 5,
        "stamina": 8,
        "cooldown": 8,
        "effects": ["bleed=8", "aoe_range=2", "immobilize=1", "magic_power_damage=0.9"],
        "desc": "Spike blood pressure in an area for ::damage ::damage_type damage, hemorrhage, and a brief lock.",
    },
    {
        "name": "Circulatory Lock",
        "level": 15,
        "damage": "[8,12]",
        "target": "health",
        "range": 5,
        "stamina": 8,
        "cooldown": 10,
        "duration": 2,
        "effects": ["bleed=10", "immobilize=1", "magic_power_damage=1.0"],
        "desc": "Clamp a target's circulation: ::damage ::damage_type damage, hemorrhage, and immobilize.",
    },
    {
        "name": "Aneurysm Mark",
        "level": 18,
        "damage": "[4,8]",
        "target": "health",
        "range": 6,
        "stamina": 7,
        "cooldown": 8,
        "duration": 4,
        "effects": ["bleed=12", "vulnerable=1", "magic_power_damage=0.8"],
        "desc": "Mark a vessel wall. Deals ::damage ::damage_type damage, hemorrhage, and leaves the target vulnerable.",
    },
    {
        "name": "Contagious Rupture",
        "level": 24,
        "damage": "[10,16]",
        "target": "health",
        "range": 5,
        "stamina": 10,
        "cooldown": 12,
        "effects": ["bleed=16", "chain=2", "magic_power_damage=1.0"],
        "desc": "A rupture that leaps. Deals ::damage ::damage_type damage and hemorrhage, then chains to nearby bodies.",
    },
    {
        "name": "Systolic Surge",
        "level": 30,
        "damage": "[16,24]",
        "target": "health",
        "range": 5,
        "stamina": 10,
        "cooldown": 8,
        "effects": ["bleed=18", "knockback=1", "magic_power_damage=1.1"],
        "desc": "Drive systolic pressure into a spike of ::damage ::damage_type trauma and hemorrhage.",
    },
    {
        "name": "Blood Hammer",
        "level": 32,
        "damage": "[20,30]",
        "target": "health",
        "range": 4,
        "stamina": 12,
        "cooldown": 10,
        "effects": ["knockback=2", "stun=1", "pierce=1", "magic_power_damage=1.2"],
        "desc": "Hammer a pressurized column through the body for ::damage ::damage_type execute trauma.",
    },
    {
        "name": "Arterial Collapse",
        "level": 38,
        "damage": "[22,34]",
        "target": "health",
        "range": 5,
        "stamina": 14,
        "cooldown": 14,
        "effects": ["bleed=24", "immobilize=1", "pierce=1", "magic_power_damage=1.2"],
        "desc": "Collapse a major artery: ::damage ::damage_type piercing trauma, heavy hemorrhage, and a lock.",
    },
    {
        "name": "Pressure Rupture",
        "level": 42,
        "damage": "[24,38]",
        "target": "aoe_tile",
        "range": 6,
        "stamina": 16,
        "cooldown": 16,
        "effects": ["bleed=20", "aoe_range=2", "knockback=2", "magic_power_damage=1.3"],
        "desc": "Detonate built pressure across a field for ::damage ::damage_type trauma and hemorrhage.",
    },
]


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def cli(args: List[str], *, check: bool = True) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(CLI), *args]
    proc = subprocess.run(cmd, cwd=str(HERE), capture_output=True, text=True)
    if proc.stdout:
        sys.stdout.write(proc.stdout)
        if not proc.stdout.endswith("\n"):
            sys.stdout.write("\n")
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr or proc.stdout or f"CLI failed: {cmd}\n")
        if check:
            raise SystemExit(proc.returncode)
    return proc


def catalog_index() -> Dict[Tuple[str, str], Dict[str, Any]]:
    out: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in load_effects():
        out[(row["kind"], row["id"])] = row
    return out


def confidence_ok(row: Optional[Dict[str, Any]]) -> bool:
    if not row:
        return False
    return row.get("confidence") != "unconfirmed"


def effect_row(cat: Dict[Tuple[str, str], Dict[str, Any]], eid: str, kinds: Iterable[str]) -> Optional[Dict[str, Any]]:
    for kind in kinds:
        row = cat.get((kind, eid))
        if row:
            return row
    return None


def remap_id(old: str, skill: str, prefixes: Tuple[str, ...]) -> str:
    rest = str(old)
    for p in prefixes:
        if rest.startswith(p):
            rest = rest[len(p) :]
            break
    rest = slug_name(rest).lower()
    if rest.startswith(f"{skill}_"):
        return rest
    return f"{skill}_{rest}"


def remap_blob(obj: Any, skill: str, prefixes: Tuple[str, ...], skill_aliases: Tuple[str, ...]) -> Any:
    if isinstance(obj, dict):
        return {k: remap_blob(v, skill, prefixes, skill_aliases) for k, v in obj.items()}
    if isinstance(obj, list):
        return [remap_blob(v, skill, prefixes, skill_aliases) for v in obj]
    if isinstance(obj, str):
        if obj in skill_aliases:
            return skill
        if any(obj.startswith(p) for p in prefixes):
            return remap_id(obj, skill, prefixes)
    return obj


def load_reward_levels(mile_dir: Path) -> Dict[Tuple[str, str], Tuple[int, str]]:
    out: Dict[Tuple[str, str], Tuple[int, str]] = {}
    if not mile_dir.is_dir():
        return out
    for path in mile_dir.glob("*.json"):
        try:
            mile = load(path)
        except json.JSONDecodeError:
            continue
        req = mile.get("requirements") or {}
        level = int(req.get("skill") if req.get("skill") is not None else 1)
        name = str(mile.get("name") or path.stem)
        for reward in mile.get("rewards") or []:
            if not isinstance(reward, dict):
                continue
            for kind, rid in reward.items():
                out[(kind, str(rid))] = (level, name)
    return out


def trim_ability_effects(ability: Dict[str, Any], cat: Dict[Tuple[str, str], Dict[str, Any]]) -> None:
    effects = ability.get("effects")
    if not isinstance(effects, dict):
        ability["effects"] = {}
        effects = ability["effects"]
    for drop in list(effects):
        if drop in ABILITY_DROP:
            effects.pop(drop, None)
            continue
        row = effect_row(cat, drop, ("ability", "amplifier"))
        if not confidence_ok(row):
            effects.pop(drop, None)
    keys = ability.get("effects_keys")
    if isinstance(keys, dict):
        for drop in list(keys):
            row = effect_row(cat, drop, ("ability_key",))
            if not confidence_ok(row):
                keys.pop(drop, None)
        if not keys:
            ability.pop("effects_keys", None)
    else:
        keys = {}
    n = len(effects) + len(keys)
    if n <= 8:
        return
    keep = [k for k in ABILITY_KEEP if k in effects]
    extra = [k for k in effects if k not in keep]
    ordered = keep + extra
    while len(ordered) + len(keys) > 8 and ordered:
        victim = ordered.pop()
        if victim in ("damage", "damage_type"):
            continue
        effects.pop(victim, None)
        ordered = [k for k in ordered if k != victim]


def sanitize_ability(
    ability: Dict[str, Any],
    *,
    skill: str,
    prefixes: Tuple[str, ...],
    aliases: Tuple[str, ...],
    cat: Dict[Tuple[str, str], Dict[str, Any]],
) -> Dict[str, Any]:
    ability = remap_blob(ability, skill, prefixes, aliases)
    ability["id"] = remap_id(str(ability.get("id") or ability.get("name") or "ability"), skill, prefixes)
    ability["skill"] = skill
    ability["image"] = 0
    anim = str(ability.get("animation") or "0")
    if not (anim.isdigit() or anim.startswith("core_2_") or anim.startswith(f"{skill}_")):
        ability["animation"] = "0"
    else:
        ability["animation"] = anim
    slots = ability.get("slots") or {"offensive": 1, "utility": 1}
    total = sum(int(v or 0) for v in slots.values())
    if total > 4:
        ability["slots"] = {"offensive": 1, "utility": 1}
    keys = ability.setdefault("effects_keys", {})
    if not isinstance(keys, dict):
        keys = {}
        ability["effects_keys"] = keys
    if str(keys.get("stacker")) == "88":
        keys["stacker"] = f"{skill}_wet"
    effects = ability.get("effects") or {}
    if skill == "aquamancy" and not keys.get("stacker") and (
        "stacker_count" in effects or "damage_per_stacks" in effects
    ):
        keys["stacker"] = f"{skill}_wet"
    trim_ability_effects(ability, cat)
    return ability


def sanitize_amplifier(
    amp: Dict[str, Any],
    *,
    skill: str,
    prefixes: Tuple[str, ...],
    aliases: Tuple[str, ...],
    cat: Dict[Tuple[str, str], Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    amp = remap_blob(amp, skill, prefixes, aliases)
    amp["id"] = remap_id(str(amp.get("id") or amp.get("name") or "support"), skill, prefixes)
    amp["image"] = 0
    amp.setdefault("type", "utility")
    bonuses = []
    for bonus in amp.get("bonuses") or []:
        if not isinstance(bonus, dict):
            continue
        eid = str(bonus.get("effect") or "")
        if eid in AMP_BONUS_TO_FIELD:
            field = AMP_BONUS_TO_FIELD[eid]
            amp[field] = bonus.get("value")
            continue
        rewrite = AMP_REWRITE.get(eid)
        if rewrite is None and eid in AMP_REWRITE:
            continue
        if rewrite:
            eid, default = rewrite
            bonus = dict(bonus)
            bonus["effect"] = eid
            if default is not None and bonus.get("value") is None:
                bonus["value"] = default
        if eid == "bonus_damage":
            n = bonus.get("value") or 1
            try:
                n = int(n)
            except (TypeError, ValueError):
                n = 1
            bonus = {"effect": "damage", "value": [n, n]}
            eid = "damage"
        row = effect_row(cat, eid, ("amplifier", "amplifier_field", "ability"))
        if not confidence_ok(row):
            continue
        bonuses.append(bonus)
    if bonuses:
        amp["bonuses"] = bonuses[:2]
    else:
        amp.pop("bonuses", None)
    if "bonuses" not in amp and not any(k in amp for k in ("cost_stamina", "range", "cooldown", "cast_time", "duration")):
        return None
    return amp


def sanitize_passive(
    passive: Dict[str, Any],
    *,
    skill: str,
    prefixes: Tuple[str, ...],
    aliases: Tuple[str, ...],
    cat: Dict[Tuple[str, str], Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    passive = remap_blob(passive, skill, prefixes, aliases)
    passive["id"] = remap_id(str(passive.get("id") or passive.get("name") or "passive"), skill, prefixes)
    passive["image"] = 0
    passive.pop("description", None)
    effects = []
    for fx in passive.get("effects") or []:
        if not isinstance(fx, dict):
            continue
        eid = str(fx.get("effect") or "")
        eid = PASSIVE_REWRITE.get(eid, eid)
        fx = dict(fx)
        fx["effect"] = eid
        if eid == "increase_effect_value" and str(fx.get("value")) == "88":
            fx["value"] = f"{skill}_wet"
        row = effect_row(cat, eid, ("passive", "amplifier"))
        if not confidence_ok(row):
            continue
        effects.append(fx)
    if not effects:
        return None
    passive["effects"] = effects[:3]
    return passive


def sanitize_entity(
    entity: Dict[str, Any],
    *,
    skill: str,
    prefixes: Tuple[str, ...],
    aliases: Tuple[str, ...],
) -> Dict[str, Any]:
    entity = remap_blob(entity, skill, prefixes, aliases)
    entity["id"] = remap_id(str(entity.get("id") or entity.get("name") or "entity"), skill, prefixes)
    usable = entity.get("usable")
    if isinstance(usable, dict) and usable.get("skill_p"):
        usable["skill_p"] = skill
    comps = set(entity.get("components") or [])
    if "actor" in comps:
        ai = entity.setdefault("artificial_intelligence", {})
        ai["allies"] = ["5"]
        ai["enemies"] = []
        tags = [str(t) for t in entity.get("tags") or []]
        if "9" not in tags:
            tags.append("9")
        if "3" not in tags:
            tags.append("3")
        entity["tags"] = tags
    return entity


def write_temp(data: Any, folder: Path, name: str) -> Path:
    path = folder / name
    dump(path, data)
    return path


def add_from_json(cmd: str, spec_id: str, payload: Dict[str, Any], tmp: Path, extra: List[str]) -> None:
    path = write_temp(payload, tmp, f"{cmd}_{payload.get('id') or 'item'}.json")
    cli([cmd, "--id", spec_id, "--from-json", str(path), *extra])


def patch_stat_points(spec_id: str, points: List[int], description: str) -> None:
    path = output_root() / spec_id / "skill.json"
    spec = load(path)
    spec["skill"]["stat_points"] = list(points)
    spec["skill"]["description"] = description
    spec["mod"]["author"] = "Arendeth"
    spec["mod"]["version"] = "2.0.0"
    dump(path, spec)


def collect_abilities(live: Path, recovered: Path) -> Dict[str, Path]:
    found: Dict[str, Path] = {}
    for folder in (recovered / "abilities", live / "abilities"):
        if not folder.is_dir():
            continue
        for path in folder.glob("*.json"):
            found[path.stem.lower()] = path
    return found


def rebuild_school(
    *,
    spec_id: str,
    skill_id: str,
    display_name: str,
    description: str,
    mod_description: str,
    live: Path,
    recovered: Path,
    prefixes: Tuple[str, ...],
    aliases: Tuple[str, ...],
    mile_dirs: List[Path],
    cat: Dict[Tuple[str, str], Dict[str, Any]],
    missing_abilities: Optional[List[Dict[str, Any]]] = None,
    book_name: str,
) -> None:
    dest = output_root() / spec_id
    if dest.exists():
        shutil.rmtree(dest)
    tmp = Path(tempfile.mkdtemp(prefix=f"s2_{spec_id}_"))
    try:
        cli(
            [
                "new",
                "--id",
                skill_id,
                "--name",
                display_name,
                "--mod",
                spec_id,
                "--difficulty",
                "2",
                "--exp-source",
                "ability=2",
            ]
        )
        cli(
            [
                "set-skill",
                "--id",
                spec_id,
                "--description",
                description,
            ]
        )
        spec = load(output_root() / spec_id / "skill.json")
        spec["mod"]["description"] = mod_description
        spec["mod"]["author"] = "Arendeth"
        dump(output_root() / spec_id / "skill.json", spec)
        patch_stat_points(spec_id, DELAYED_STAT_POINTS, description)

        if skill_id == "aquamancy":
            cli(
                [
                    "add-stacker",
                    "--id",
                    spec_id,
                    "--name",
                    "Wet",
                    "--effect",
                    "movement_speed=0.02",
                    "--max-stacks",
                    "20",
                    "--duration",
                    "4",
                ]
            )
            cli(["clone-entity", "--id", spec_id, "--source", "Ice_Sliver", "--new-id", "core_2_Ice_Sliver"])
            cli(["clone-entity", "--id", spec_id, "--source", "Fog", "--new-id", "core_2_Fog"])

        rewards: Dict[Tuple[str, str], Tuple[int, str]] = {}
        for mile_dir in mile_dirs:
            rewards.update(load_reward_levels(mile_dir))

        # Items / creatures first so summon ids exist.
        ent_dir = live / "entities"
        rec_ent = recovered / "entities"
        seen_ent = set()
        for folder in (ent_dir, rec_ent):
            if not folder.is_dir():
                continue
            for path in folder.glob("*.json"):
                raw_ent = load(path)
                usable = raw_ent.get("usable") or {}
                if isinstance(usable, dict) and usable.get("skill_p"):
                    # Geomancy-style skill book is added via add-item --preset skill_book.
                    continue
                entity = sanitize_entity(raw_ent, skill=skill_id, prefixes=prefixes, aliases=aliases)
                eid = entity["id"]
                if eid in seen_ent:
                    continue
                seen_ent.add(eid)
                comps = set(entity.get("components") or [])
                cmd = "add-creature" if "actor" in comps else "add-item"
                add_from_json(cmd, spec_id, entity, tmp, [])
                old_id = load(path).get("id")
                rec = rewards.get(("recipe", str(old_id)))
                if rec and "item" in comps:
                    level, name = rec
                    if level <= 0:
                        level = 44
                    cli(
                        [
                            "grant-existing",
                            "--id",
                            spec_id,
                            "--kind",
                            "recipe",
                            "--reward",
                            eid,
                            "--name",
                            name,
                            "--unlock-level",
                            str(level),
                        ]
                    )

        cli(
            [
                "add-item",
                "--id",
                spec_id,
                "--preset",
                "skill_book",
                "--name",
                book_name,
                "--unlock-level",
                "44",
            ]
        )

        abilities = collect_abilities(live, recovered)
        added_ab = set()
        for stem, path in sorted(abilities.items()):
            raw = load(path)
            old_id = str(raw.get("id") or "")
            ability = sanitize_ability(raw, skill=skill_id, prefixes=prefixes, aliases=aliases, cat=cat)
            if ability["id"] in added_ab:
                continue
            rec = rewards.get(("ability", old_id))
            extra = []
            if rec:
                extra = ["--unlock-level", str(rec[0])]
            else:
                extra = ["--no-milestone"]
            add_from_json("add-ability", spec_id, ability, tmp, extra)
            added_ab.add(ability["id"])

        for missing in missing_abilities or []:
            slug = f"{skill_id}_{slug_name(missing['name']).lower()}"
            if slug in added_ab:
                continue
            args = [
                "add-ability",
                "--id",
                spec_id,
                "--ability-name",
                missing["name"],
                "--unlock-level",
                str(missing["level"]),
                "--damage",
                missing["damage"],
                "--damage-type",
                "physical",
                "--target",
                missing["target"],
                "--range",
                str(missing["range"]),
                "--stamina",
                str(missing["stamina"]),
                "--animation",
                "196",
                "--description",
                missing["desc"],
            ]
            if missing.get("cooldown") is not None:
                args += ["--cooldown", str(missing["cooldown"])]
            if missing.get("duration") is not None:
                args += ["--duration", str(missing["duration"])]
            for fx in missing.get("effects") or []:
                args += ["--effect", fx]
            cli(args)
            added_ab.add(slug)

        amps_path = live / "ability_amplifiers.json"
        if amps_path.is_file():
            for amp in load(amps_path):
                old_id = str(amp.get("id") or "")
                clean = sanitize_amplifier(amp, skill=skill_id, prefixes=prefixes, aliases=aliases, cat=cat)
                if not clean:
                    print(f"skip amplifier {old_id}")
                    continue
                rec = rewards.get(("amplifier", old_id))
                extra = ["--unlock-level", str(rec[0])] if rec else ["--no-milestone"]
                add_from_json("add-amplifier", spec_id, clean, tmp, extra)

        pass_path = live / "passives.json"
        rec_pass = recovered / "passives.json"
        passives = []
        if rec_pass.is_file():
            passives.extend(load(rec_pass))
        if pass_path.is_file():
            passives.extend(load(pass_path))
        seen_pa = set()
        for passive in passives:
            old_id = str(passive.get("id") or "")
            clean = sanitize_passive(passive, skill=skill_id, prefixes=prefixes, aliases=aliases, cat=cat)
            if not clean or clean["id"] in seen_pa:
                continue
            seen_pa.add(clean["id"])
            rec = rewards.get(("passive", old_id))
            extra = ["--unlock-level", str(rec[0])] if rec else ["--no-milestone"]
            add_from_json("add-passive", spec_id, clean, tmp, extra)

        print(f"--- validate {spec_id} ---")
        proc = cli(["validate", "--id", spec_id], check=False)
        if proc.returncode != 0:
            raise SystemExit(f"validate failed for {spec_id}")
        print(f"--- write {spec_id} ---")
        cli(["write", "--id", spec_id])
        print(f"--- tree {spec_id} ---")
        cli(["tree", "--id", spec_id])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    cat = catalog_index()
    for eid in ("bleed", "pull_target", "hide", "lunge", "vulnerable", "chain", "pierce", "immobilize"):
        cli(["explain", eid])

    aqua_desc = (
        "Pressure-and-flow water magic. Pressurized jets cut flesh from afar while Wet stacks "
        "set up detonations.\n\nLevels 1–10 grant abilities and supports only; stat points begin at 11.\n\n"
        "You can train this skill by using abilities."
    )
    sang_desc = (
        "Forbidden art of manipulating blood pressure within living bodies. Build pressure, then "
        "rupture it with physical trauma and hemorrhage.\n\nLevels 1–10 grant abilities and supports only; "
        "stat points begin at 11.\n\nYou can train this skill by using abilities."
    )

    rebuild_school(
        spec_id="aquamancy",
        skill_id="aquamancy",
        display_name="Hydromancy",
        description=aqua_desc,
        mod_description="Hydromancy rebuilt through Skill Creator: physical cut damage, Wet synergy, summons, and slottable flow/pressure supports.",
        live=LIVE_AQUA,
        recovered=REC_WATER,
        prefixes=AQUA_PREFIXES,
        aliases=("arendeth_hydromancy", "arendeth_water_magic_hydromancy", "arendeth_water_magic"),
        mile_dirs=[
            LIVE_AQUA / "milestones" / "hydromancy",
            LIVE_AQUA / "milestones" / "arendeth_hydromancy",
            REC_WATER / "milestones" / "hydromancy",
        ],
        cat=cat,
        book_name="Book of Aquamancy",
    )
    rebuild_school(
        spec_id="sanguimancy",
        skill_id="sanguimancy",
        display_name="Hemohydraulics",
        description=sang_desc,
        mod_description="Hemohydraulics rebuilt through Skill Creator: internal pressure sorcery that ruptures living bodies.",
        live=LIVE_SANG,
        recovered=REC / "from_transcript_reads" / "arendeth_hemohydraulic_magic",
        prefixes=SANG_PREFIXES,
        aliases=("arendeth_hemohydraulic_magic_mastery", "arendeth_hemohydraulic_magic"),
        mile_dirs=[
            LIVE_SANG / "milestones" / "hemohydraulics",
            LIVE_SANG / "milestones" / "mastery",
            REC / "from_transcript_reads" / "arendeth_hemohydraulic_magic" / "milestones" / "mastery",
        ],
        cat=cat,
        missing_abilities=MISSING_SANG,
        book_name="Book of Sanguimancy",
    )
    print("Staged under", output_root())
    print("Did not install. Say the word if you want these copied into the game mods folder.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
