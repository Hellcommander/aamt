#!/usr/bin/env python3
"""Soulash 2 out-of-game skill creator CLI."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Optional

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from s2_assets import clone_animation, load_animation, search_animations
from s2_animations import PRESETS, compose_animation, list_particle_usage, list_presets, produce_fx, use_vanilla_particles
from s2_particle_art import THEMES, paint_animations
from s2_buildings import (
    add_building,
    clone_building,
    copy_building_map,
    copy_mod_to_output,
    find_building_map,
    load_building,
    make_training_building,
    public_building,
    resolve_workshop_mod,
    scan_mod_folder,
    search_buildings,
    upgrade_mod_folder,
)
from s2_fix_mod import (
    copy_mod_to_fixed,
    resolve_fix_targets,
    scan_outdated_mod,
    summarize_scan,
    upgrade_outdated_mod,
)
from s2_mine_effects import mine_all, write_catalog
from s2_entities import (
    attach_granted_passive,
    clone_entity,
    grant_entity_milestones,
    make_creature,
    make_item,
    make_tile,
    search_entities,
)
from s2_paths import mods_dir, output_root, staging_dir
from s2_races import (
    add_character_tag,
    add_control_action,
    add_production_action,
    add_race,
    clone_race,
    load_vanilla_control_action,
    load_vanilla_production_action,
    load_vanilla_race,
    make_character_tag,
    make_control_action,
    make_production_action,
    make_race,
    make_settlement,
    parse_base_entity,
    parse_stat_flag,
    public_race,
    search_control_actions,
    search_production_actions,
    search_races,
    search_tags,
)
from s2_schema import (
    apply_ability_kv,
    bonus_from_kv,
    dropdowns,
    effect_cards,
    find_effect,
    list_effects,
    parse_value,
    reload,
    slug_name,
)
from s2_skill_spec import (
    add_ability,
    add_amplifier,
    add_animation,
    add_combat_mastery,
    add_entity,
    add_exp_source,
    add_loot_exclude,
    add_passive,
    add_stacker,
    add_starting_gear,
    apply_skill_update,
    apply_stat_preset,
    bind_ability_entity,
    clear_ability_effect,
    clone_ability,
    clone_stacker,
    cycle_images,
    ensure_aoe_shape,
    fill_stats_after_10,
    find_row,
    grant_existing,
    load_mod_folder,
    load_spec,
    load_vanilla_ability,
    new_spec,
    parse_exp_source,
    parse_starting_gear,
    patch_ability_costs,
    patch_amplifier,
    patch_mod_meta,
    patch_passive,
    patch_stacker,
    prefixed_skill_id,
    remove_ability,
    remove_amplifier,
    remove_passive,
    retarget_owned_ids,
    save_spec,
    search_abilities,
    set_ability_effect,
    set_slots,
    tree_rows,
    write_mod,
)
from s2_validate import format_issues, validate_spec, validate_vanilla


def _spec_path(args: argparse.Namespace) -> Path:
    if getattr(args, "spec", None):
        return Path(args.spec)
    if getattr(args, "id", None):
        return output_root() / args.id / "skill.json"
    raise SystemExit("Provide --spec or --id")


def _load(args: argparse.Namespace) -> tuple[dict, Path]:
    path = _spec_path(args)
    if path.is_dir():
        spec = load_mod_folder(path)
        return spec, path / "skill.json"
    spec = load_spec(path)
    return spec, path


def _csv_list(items: Optional[list]) -> list:
    out = []
    for item in items or []:
        out.extend(x.strip() for x in str(item).split(",") if x.strip())
    return out


def cmd_mine(_args: argparse.Namespace) -> int:
    payload = mine_all()
    e, n, m = write_catalog(payload)
    reload()
    print(f"Wrote {e}")
    print(f"Wrote {n}")
    print(f"Wrote {m}")
    print(f"Effects: {len(payload['effects'])}")
    print("Workshop mods:", ", ".join(payload["workshop_mods"]) or "(none)")
    print("EXE:", payload.get("exe"), "ids", payload.get("exe_id_count"))
    unconf = sum(1 for fx in payload["effects"] if fx.get("confidence") == "unconfirmed")
    print("Unconfirmed (exe-only):", unconf)
    return 0


def cmd_list_effects(args: argparse.Namespace) -> int:
    if args.dropdown:
        d = dropdowns()
        kind = args.kind or "ability"
        rows = d.get(kind) or []
        if args.json:
            print(json.dumps(rows, indent=2))
            return 0
        for e in rows:
            print(f"{e.get('kind','?'):16} {e['id']:32} {e.get('schema','?'):12} {e.get('group','')}")
        print(f"{len(rows)} dropdown effects")
        return 0
    rows = list_effects(args.kind)
    if args.json:
        print(json.dumps(rows, indent=2))
        return 0
    for e in rows:
        print(f"{e['kind']:16} {e['id']:32} {e['value_schema']:12} n={e['count']:<5} {e['confidence']}")
    print(f"{len(rows)} effects")
    return 0


def cmd_explain(args: argparse.Namespace) -> int:
    card = effect_cards().get(args.effect_id)
    matches = [x for x in list_effects() if x["id"] == args.effect_id]
    if args.kind:
        matches = [x for x in matches if x.get("kind") == args.kind]
        if not matches:
            e = find_effect(args.effect_id, args.kind)
            matches = [e] if e else []
    if not card and not matches:
        print(f"Unknown effect: {args.effect_id}", file=sys.stderr)
        return 1
    print(json.dumps({"card": card, "rows": matches}, indent=2))
    return 0


def cmd_new(args: argparse.Namespace) -> int:
    raw_id = str(args.id).strip()
    sid = raw_id if args.no_prefix else prefixed_skill_id(raw_id)
    if sid != raw_id:
        print(f"Prefixed id {raw_id} -> {sid} (vanilla uses core_2_*; pass --no-prefix to skip)")
    spec = new_spec(sid, args.name, mod_id=args.mod or sid, level_start=args.level_start, prefix=False)
    if args.no_combat:
        spec["skill"]["combat_skill"] = False
    if args.difficulty is not None:
        spec["skill"]["difficulty"] = args.difficulty
    if args.exp_source:
        spec["skill"]["exp_sources"] = []
        for item in args.exp_source:
            try:
                add_exp_source(spec, parse_exp_source(item))
            except ValueError as exc:
                raise SystemExit(str(exc)) from exc
    for item in args.gear or []:
        try:
            add_starting_gear(spec, parse_starting_gear(item))
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
    if args.thumbnail or args.steam_publish_id is not None or args.disable_portraits:
        patch_mod_meta(
            spec,
            thumbnail=args.thumbnail,
            steam_publish_id=args.steam_publish_id,
            disable_portraits=True if args.disable_portraits else None,
        )
    path = Path(args.output) if args.output else (staging_dir(spec) / "skill.json")
    if not args.no_combat and not args.no_mastery:
        mastery = add_combat_mastery(spec)
        print(f"Combat mastery {mastery.get('id')} at level 30 (+10% all attributes)")
    save_spec(spec, path)
    print(f"Created spec: {path}")
    print(json.dumps({"id": spec["id"], "skill_id": spec["skill_id"], "name": spec["skill"]["name"]}, indent=2))
    return 0


def cmd_set_skill(args: argparse.Namespace) -> int:
    spec, path = _load(args)
    if args.no_combat:
        spec["skill"]["combat_skill"] = False
    if args.combat:
        spec["skill"]["combat_skill"] = True
    payload: dict = {}
    if args.difficulty is not None:
        payload["difficulty"] = args.difficulty
    if args.level_start is not None:
        payload["level_start"] = args.level_start
    if args.description is not None:
        payload["description"] = args.description
    if args.name:
        payload["name"] = args.name
    if payload:
        apply_skill_update(spec, payload)
    if args.clear_gear:
        spec["skill"].pop("starting_gear", None)
    for item in args.gear or []:
        try:
            add_starting_gear(spec, parse_starting_gear(item))
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
    if args.replace_exp:
        spec["skill"]["exp_sources"] = []
    for item in args.exp_source or []:
        try:
            add_exp_source(spec, parse_exp_source(item), replace_same_id=not args.replace_exp)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
    patch_mod_meta(
        spec,
        thumbnail=args.thumbnail,
        steam_publish_id=args.steam_publish_id,
        disable_portraits=True if args.disable_portraits else (False if args.clear_disable_portraits else None),
        author=args.author,
        version=args.version,
        description=args.mod_description,
        name=args.mod_name or args.name,
    )
    if args.stat_points:
        apply_stat_preset(spec, args.stat_points)
    if args.fill_stats_after_10:
        added = fill_stats_after_10(spec)
        if added:
            print(f"Added +1 statistic on levels: {added}")
    save_spec(spec, path)
    print(f"Updated skill {spec['skill_id']} -> {path}")
    return 0


def cmd_rename_id(args: argparse.Namespace) -> int:
    spec, path = _load(args)
    old = str(spec.get("skill_id") or spec.get("id") or "")
    author = (spec.get("mod") or {}).get("author")
    dest = str(args.to).strip()
    new = dest if args.no_prefix else prefixed_skill_id(dest, author=author)
    if new == old:
        print(f"Already {new}")
        return 0
    n = retarget_owned_ids(spec, old, new)
    old_dir = path.parent
    new_dir = output_root() / new
    if old_dir.resolve() != new_dir.resolve():
        if new_dir.exists():
            raise SystemExit(f"Destination already exists: {new_dir}")
        shutil.move(str(old_dir), str(new_dir))
        path = new_dir / "skill.json"
    save_spec(spec, path)
    leftover = path.parent / "milestones" / old
    if leftover.is_dir():
        shutil.rmtree(leftover)
    print(f"Retargeted {n} ids: {old} -> {new}")
    print(f"Staging: {path.parent}")
    return 0


def cmd_add_gear(args: argparse.Namespace) -> int:
    spec, path = _load(args)
    try:
        choice = parse_starting_gear(args.choice)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    add_starting_gear(spec, choice)
    save_spec(spec, path)
    print(json.dumps(choice, indent=2))
    return 0


def cmd_add_exp_source(args: argparse.Namespace) -> int:
    spec, path = _load(args)
    try:
        src = parse_exp_source(args.source)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    add_exp_source(spec, src, replace_same_id=bool(args.replace))
    save_spec(spec, path)
    print(json.dumps(src, indent=2))
    return 0


def cmd_add_ability(args: argparse.Namespace) -> int:
    spec, path = _load(args)
    if args.clone:
        try:
            ability = clone_ability(
                args.clone,
                skill_id=spec["skill_id"],
                new_id=args.ability_id,
                name=args.ability_name,
            )
        except (FileNotFoundError, ValueError) as exc:
            raise SystemExit(str(exc)) from exc
    elif args.from_json:
        ability = json.loads(Path(args.from_json).read_text(encoding="utf-8") if Path(args.from_json).is_file() else args.from_json)
    else:
        aid = args.ability_id or f"{spec['skill_id']}_{slug_name(args.ability_name or 'ability').lower()}"
        ability = {
            "id": aid,
            "name": args.ability_name or aid,
            "description": args.description or "",
            "target": args.target or "health",
            "range": args.range if args.range is not None else 4,
            "effects": {},
        }
    if args.ability_name:
        ability["name"] = args.ability_name
    if args.description:
        ability["description"] = args.description
    if args.target:
        ability["target"] = args.target
    if args.range is not None:
        ability["range"] = args.range
    if args.damage:
        ability.setdefault("effects", {})["damage"] = parse_value(args.damage)
    if args.damage_type:
        ability.setdefault("effects", {})["damage_type"] = args.damage_type
    if args.summon:
        ability.setdefault("effects_keys", {})["summon"] = args.summon
        ability.setdefault("effects", {})["summon_count"] = args.summon_count if args.summon_count is not None else 1
        ability["target"] = args.target or ability.get("target") or "tile"
    if args.stacker:
        ability.setdefault("effects_keys", {})["stacker"] = args.stacker
        ability.setdefault("effects", {})["stacker_count"] = args.stacker_count if args.stacker_count is not None else 1
    if args.animation:
        ability["animation"] = args.animation
    for item in args.effect or []:
        try:
            apply_ability_kv(ability, item)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
    ones = _csv_list(args.require_one_of)
    always = _csv_list(getattr(args, "require_always", None))
    patch_ability_costs(
        ability,
        stamina=args.stamina,
        health=args.health,
        cost_item=args.cost_item,
        cost_item_type=args.cost_item_type,
        ammo=args.ammo,
        min_range=args.min_range,
        require_one_of=ones or None,
        require_always=always or None,
        cast_time=args.cast_time,
        cooldown=args.cooldown,
        duration=args.duration,
    )
    existed = any(a.get("id") == ability.get("id") for a in spec.get("abilities") or [])
    add_ability(spec, ability, unlock_level=args.unlock_level, no_milestone=args.no_milestone)
    if args.clone_animation:
        _clone_ability_animation(spec, ability)
    save_spec(spec, path)
    verb = "Replaced" if existed else "Added"
    print(f"{verb} ability {ability.get('id')} -> {path}")
    return 0


def cmd_add_amplifier(args: argparse.Namespace) -> int:
    spec, path = _load(args)
    if args.grant_existing:
        grant_existing(
            spec,
            kind="amplifier",
            reward_id=args.grant_existing,
            name=args.name or args.grant_existing,
            unlock_level=args.unlock_level if args.unlock_level is not None else 1,
        )
        save_spec(spec, path)
        print(f"Linked existing amplifier {args.grant_existing}")
        return 0
    if args.from_json:
        amp = json.loads(Path(args.from_json).read_text(encoding="utf-8") if Path(args.from_json).is_file() else args.from_json)
    else:
        aid = args.amplifier_id or f"{spec['skill_id']}_{slug_name(args.name or 'support').lower()}"
        bonuses = []
        if args.bonus:
            for item in args.bonus:
                try:
                    bonuses.append(bonus_from_kv(item))
                except ValueError as exc:
                    raise SystemExit(str(exc)) from exc
        amp = {"id": aid, "name": args.name or aid, "type": args.type, "bonuses": bonuses, "image": 0}
        if args.cooldown is not None:
            amp["cooldown"] = args.cooldown
        if args.cast_time is not None:
            amp["cast_time"] = args.cast_time
        if args.range is not None:
            amp["range"] = args.range
        if args.cost_stamina is not None:
            amp["cost_stamina"] = args.cost_stamina
            if not bonuses:
                amp.pop("bonuses", None)
        if args.description:
            amp["description"] = args.description
    existed = any(a.get("id") == amp.get("id") for a in spec.get("amplifiers") or [])
    add_amplifier(spec, amp, unlock_level=args.unlock_level, no_milestone=args.no_milestone)
    save_spec(spec, path)
    verb = "Replaced" if existed else "Added"
    print(f"{verb} amplifier {amp.get('id')} -> {path}")
    return 0


def cmd_add_passive(args: argparse.Namespace) -> int:
    spec, path = _load(args)
    if args.from_json:
        passive = json.loads(Path(args.from_json).read_text(encoding="utf-8") if Path(args.from_json).is_file() else args.from_json)
    else:
        pid = args.passive_id or f"{spec['skill_id']}_{slug_name(args.name or 'passive').lower()}"
        effects = []
        for item in args.effect or []:
            try:
                effects.append(bonus_from_kv(item))
            except ValueError as exc:
                raise SystemExit(str(exc)) from exc
        passive = {"id": pid, "name": args.name or pid, "image": 0, "effects": effects}
        if args.apply_mode:
            passive["apply_mode"] = args.apply_mode
        tags = _csv_list(args.restrict_tags)
        if tags:
            passive["restrict_tags"] = tags
        enemy = _csv_list(args.restrict_tags_enemy)
        if enemy:
            passive["restrict_tags_enemy"] = enemy
        if args.restrict_weapon_type is not None:
            passive["restrict_weapon_type"] = args.restrict_weapon_type
    existed = any(p.get("id") == passive.get("id") for p in spec.get("passives") or [])
    try:
        add_passive(
            spec,
            passive,
            unlock_level=args.unlock_level,
            no_milestone=args.no_milestone,
            innate=bool(args.innate),
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    save_spec(spec, path)
    verb = "Replaced" if existed else "Added"
    print(f"{verb} passive {passive.get('id')} -> {path}")
    return 0


def cmd_add_combat_mastery(args: argparse.Namespace) -> int:
    spec, path = _load(args)
    existed = any(p.get("id") == f"{spec['skill_id']}_mastery" for p in spec.get("passives") or [])
    mastery = add_combat_mastery(spec, unlock_level=int(args.unlock_level or 30), name=args.name)
    save_spec(spec, path)
    verb = "Replaced" if existed else "Added"
    print(f"{verb} combat mastery {mastery.get('id')} at level {args.unlock_level or 30} -> {path}")
    return 0


def cmd_add_stacker(args: argparse.Namespace) -> int:
    spec, path = _load(args)
    if args.clone:
        sid = args.stacker_id or f"{spec['skill_id']}_{slug_name(args.name or args.clone).lower()}"
        stacker = clone_stacker(args.clone, new_id=sid, name=args.name)
    elif args.from_json:
        stacker = json.loads(Path(args.from_json).read_text(encoding="utf-8") if Path(args.from_json).is_file() else args.from_json)
    else:
        sid = args.stacker_id or f"{spec['skill_id']}_{slug_name(args.name or 'stacker').lower()}"
        effects = []
        for item in args.effect or []:
            try:
                effects.append(bonus_from_kv(item))
            except ValueError as exc:
                raise SystemExit(str(exc)) from exc
        stacker = {
            "id": sid,
            "name": args.name or sid,
            "image": args.image if args.image is not None else 0,
            "effects": effects,
            "max_stacks": args.max_stacks if args.max_stacks is not None else 10,
            "apply_caster": bool(args.apply_caster),
        }
        if args.duration is not None:
            stacker["duration"] = args.duration
        if args.on_max_stacks_cast:
            stacker["on_max_stacks_cast"] = args.on_max_stacks_cast
            stacker["max_stacks_cast_unlock"] = bool(args.max_stacks_cast_unlock)
        if args.description:
            stacker["description"] = args.description
    existed = any(s.get("id") == stacker.get("id") for s in spec.get("stackers") or [])
    try:
        add_stacker(
            spec,
            stacker,
            bind_ability=args.bind_ability,
            stacker_count=args.stacker_count if args.stacker_count is not None else 1,
        )
    except KeyError as exc:
        raise SystemExit(str(exc)) from exc
    save_spec(spec, path)
    verb = "Replaced" if existed else "Added"
    print(f"{verb} stacker {stacker.get('id')} -> {path}")
    return 0


def cmd_list_animations(args: argparse.Namespace) -> int:
    rows = search_animations(args.search, limit=args.limit or 40)
    if args.json:
        print(json.dumps(rows, indent=2))
        return 0
    for row in rows:
        print(f"{row['source']:16} {row['id']:40} {row['name']}")
    print(f"{len(rows)} matches")
    return 0


def cmd_list_anim_presets(args: argparse.Namespace) -> int:
    rows = list_presets()
    if getattr(args, "json", False):
        print(json.dumps(rows, indent=2))
        return 0
    for row in rows:
        look = row.get("look") or ""
        extra = f"  look: {look}" if look else ""
        print(f"{row['preset']:12} {row['kind']:12} clone={row['clone']:16} {row['blurb']}{extra}")
    return 0


def cmd_dump_animation(args: argparse.Namespace) -> int:
    data = load_animation(args.source)
    data.pop("_cloned_from", None)
    print(json.dumps(data, indent=2))
    return 0


def cmd_list_particles(args: argparse.Namespace) -> int:
    rows = list_particle_usage(args.search or "", limit=args.limit or 40)
    if args.json:
        print(json.dumps(rows, indent=2))
        return 0
    for row in rows:
        used = ", ".join(row["used_by"][:4])
        extra = f" +{row['count'] - 4}" if row["count"] > 4 else ""
        print(f"tile {row['tile_id']:<5} x{row['count']:<3} {used}{extra}")
    print(f"{len(rows)} tiles")
    return 0


def _art_color(args: argparse.Namespace) -> Optional[str]:
    if getattr(args, "color", None):
        return str(args.color)
    art = getattr(args, "art", None)
    if not art:
        return None
    from s2_particle_art import resolve_theme, theme_rgb

    name = getattr(args, "name", None) or getattr(args, "preset", None) or getattr(args, "clone", None) or ""
    theme = None if str(art) in ("auto", "1", "True") else str(art)
    r, g, b = theme_rgb(resolve_theme(theme, name=str(name)))
    return f"{r},{g},{b},255"


def _add_composed_animations(spec: dict, path: Path, anims: list, bind: list, *, paint: Optional[dict] = None) -> int:
    if paint:
        notes = paint_animations(spec, anims, root=path.parent, **paint)
        for line in notes:
            print(f"Art {line}")
    main = anims[0]
    for extra in anims[1:]:
        add_animation(spec, extra)
        print(f"Added impact {extra.get('id')}")
    add_animation(spec, main, bind_ability=bind or None)
    save_spec(spec, path)
    binds = ", ".join(bind) if bind else "(unbound)"
    print(f"Added animation {main.get('id')} bound to {binds} -> {path}")
    return 0


def cmd_add_animation(args: argparse.Namespace) -> int:
    spec, path = _load(args)
    bind = list(args.bind_ability or [])
    try:
        paint = None
        if args.preset or args.clone_impact or args.on_impact:
            if not (args.preset or args.clone):
                raise SystemExit("add-animation needs --preset or --clone")
            aid = args.animation_id or f"{spec['skill_id']}_{slug_name(args.name or args.preset or args.clone).lower()}"
            anims = compose_animation(
                source=args.clone,
                preset=args.preset,
                new_id=aid,
                name=args.name,
                color=_art_color(args),
                clone_impact=bool(args.clone_impact),
                on_impact=args.on_impact,
            )
            return _add_composed_animations(spec, path, anims, bind, paint=paint)
        if args.clone:
            aid = args.animation_id or f"{spec['skill_id']}_{slug_name(args.name or args.clone).lower()}"
            color = None
            raw = _art_color(args)
            if raw:
                from s2_animations import parse_rgba

                color = parse_rgba(raw)
            anim = clone_animation(args.clone, new_id=aid, name=args.name, color=color)
        elif args.from_json:
            anim = json.loads(Path(args.from_json).read_text(encoding="utf-8") if Path(args.from_json).is_file() else args.from_json)
        else:
            raise SystemExit("add-animation needs --preset, --clone, or --from-json")
        add_animation(spec, anim, bind_ability=bind or None)
    except (KeyError, FileNotFoundError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    save_spec(spec, path)
    print(f"Added animation {anim.get('id')} -> {path}")
    return 0


def cmd_new_animation(args: argparse.Namespace) -> int:
    spec, path = _load(args)
    bind = list(args.bind_ability or [])
    aid = args.animation_id or f"{spec['skill_id']}_{slug_name(args.name or args.preset or 'fx').lower()}"
    try:
            anims = compose_animation(
                source=args.clone,
                preset=args.preset,
                new_id=aid,
                name=args.name,
                color=_art_color(args),
                clone_impact=bool(args.clone_impact),
                on_impact=args.on_impact,
            )
    except (KeyError, FileNotFoundError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    return _add_composed_animations(spec, path, anims, bind)


def cmd_generate_anim_art(args: argparse.Namespace) -> int:
    from s2_particle_gui import run_gui

    return run_gui(spec_id=getattr(args, "id", None), spec_path=getattr(args, "spec", None))


def cmd_particles(args: argparse.Namespace) -> int:
    from s2_particle_gui import run_gui

    return run_gui(spec_id=getattr(args, "id", None), spec_path=getattr(args, "spec", None))


def _preview_dir_for(path: Path, anim_id: str) -> Path:
    from s2_fx_preview import preview_root

    return preview_root(path) / slug_name(anim_id).lower()


def cmd_fx_preview(args: argparse.Namespace) -> int:
    from s2_fx_preview import write_preview_pack
    from s2_particle_art import infer_theme, resolve_theme, theme_rgba
    from s2_animations import parse_rgba, recolor_animation

    name = args.name or args.source or args.preset or "fx"
    theme = args.art
    theme_id = resolve_theme(None if not theme or theme == "auto" else theme, name=str(name))
    if not theme or theme == "auto":
        theme_id = infer_theme(str(name), fallback=theme_id)
    color = parse_rgba(args.color) if args.color else theme_rgba(theme_id)
    if args.preset:
        anims = compose_animation(
            source=args.source,
            preset=args.preset,
            new_id="preview",
            name=name,
            color=color,
            clone_impact=bool(args.clone_impact),
        )
        anim = anims[0]
        extras = anims[1:]
    elif args.source:
        anim = load_animation(args.source)
        recolor_animation(anim, color)
        extras = []
    else:
        raise SystemExit("fx-preview needs --preset or --source")
    dest = Path(args.out) if args.out else preview_root_fallback(anim.get("id") or name)
    pack = write_preview_pack(
        anim,
        dest,
        extras=extras,
        theme=theme_id,
        plan={"source": args.source, "preset": args.preset, "look": (PRESETS.get(args.preset) or {}).get("look")},
        compare=bool(args.compare),
        name=str(name),
    )
    print(json.dumps(pack, indent=2))
    return 0


def preview_root_fallback(anim_id: str) -> Path:
    from s2_fx_preview import preview_root

    return preview_root(None) / slug_name(str(anim_id)).lower()


def cmd_produce_fx(args: argparse.Namespace) -> int:
    from s2_fx_preview import write_preview_pack
    from s2_skill_spec import add_animation

    jobs = []
    if args.missing:
        spec, path = _load(args)
        for ab in spec.get("abilities") or []:
            anim = str(ab.get("animation") or "")
            if anim and not anim.isdigit():
                continue
            jobs.append(
                {
                    "name": str(ab.get("name") or ab.get("id") or "fx"),
                    "bind": [str(ab.get("id"))] if ab.get("id") else [],
                    "new_id": f"{spec['skill_id']}_{slug_name(ab.get('name') or ab.get('id') or 'fx').lower()}_fx",
                }
            )
        if not jobs:
            print(json.dumps({"ok": True, "produced": [], "note": "every ability already has a custom FX id"}))
            return 0
    else:
        spec, path = _load(args)
        if not (args.name or args.preset or args.clone):
            raise SystemExit("produce-fx needs --name, --preset/--clone, or --missing")
        name = args.name or args.preset or args.clone or "fx"
        aid = args.animation_id or f"{spec['skill_id']}_{slug_name(name).lower()}"
        jobs.append({"name": name, "bind": list(args.bind_ability or []), "new_id": aid})

    produced = []
    for job in jobs:
        built = produce_fx(
            new_id=job["new_id"],
            name=job["name"],
            preset=args.preset,
            clone=args.clone,
            theme=args.art,
            color=args.color,
            clone_impact=True if args.clone_impact else (False if args.no_clone_impact else None),
            on_impact=args.on_impact,
        )
        rows = built["rows"]
        main = rows[0]
        dest = _preview_dir_for(path, str(main.get("id")))
        pack = write_preview_pack(
            main,
            dest,
            extras=rows[1:],
            theme=built["theme"],
            plan=built["plan"],
            compare=bool(args.compare) or not (args.preset or args.clone),
            name=job["name"],
        )
        if not args.dry_run:
            for extra in rows[1:]:
                add_animation(spec, extra)
            add_animation(spec, main, bind_ability=job["bind"] or None)
        produced.append(
            {
                "id": main.get("id"),
                "name": main.get("name"),
                "theme": built["theme"],
                "plan": built["plan"],
                "bound": job["bind"],
                "preview": pack["files"],
                "manifest": pack.get("manifest"),
                "particles": pack.get("particles"),
                "committed": not args.dry_run,
            }
        )
    if not args.dry_run:
        save_spec(spec, path)
    print(json.dumps({"ok": True, "spec": str(path), "dry_run": bool(args.dry_run), "produced": produced}, indent=2))
    return 0


def cmd_use_vanilla_particles(args: argparse.Namespace) -> int:
    spec, path = _load(args)
    theme = str(args.theme or "").strip().lower()
    if not theme:
        blob = f"{spec.get('skill_id') or ''} {(spec.get('skill') or {}).get('name') or ''}".lower()
        theme = "blood" if any(w in blob for w in ("sangui", "hemo", "blood")) else "water"
    notes = use_vanilla_particles(spec, theme=theme, root=path.parent)
    save_spec(spec, path)
    assets = spec.get("assets")
    if assets:
        (path.parent / "assets.json").write_text(json.dumps(assets, indent="\t") + "\n", encoding="utf-8")
    for line in notes:
        print(line)
    print(f"Vanilla particles bound ({theme}) -> {path}")
    return 0


def _damage_pair(raw: Optional[str], default: list) -> list:
    if not raw:
        return default
    val = parse_value(raw)
    if isinstance(val, list) and val:
        return [int(val[0]), int(val[-1])]
    return [int(val), int(val)]


def cmd_add_item(args: argparse.Namespace) -> int:
    spec, path = _load(args)
    if args.from_json:
        item = json.loads(Path(args.from_json).read_text(encoding="utf-8") if Path(args.from_json).is_file() else args.from_json)
    else:
        eid = args.item_id or f"{spec['skill_id']}_{slug_name(args.name or 'item').lower()}"
        item = make_item(
            eid=eid,
            name=args.name or eid,
            preset=args.preset,
            description=args.description or "",
            skill_id=spec["skill_id"],
            glyph_index=args.glyph if args.glyph is not None else 0,
            value=args.value if args.value is not None else 100,
            weight=args.weight if args.weight is not None else 0.2,
            damage=_damage_pair(args.damage, [2, 4]),
            damage_type=args.damage_type or "physical",
        )
        if args.granted_passive:
            attach_granted_passive(item, args.granted_passive)
    add_entity(spec, item)
    if args.loot_exclude:
        add_loot_exclude(spec, item["id"])
    if args.unlock_level is not None and (args.preset or "").lower() in ("skill_book", "book"):
        grant_existing(
            spec,
            kind="recipe",
            reward_id=item["id"],
            name=item.get("name") or item["id"],
            unlock_level=args.unlock_level,
        )
    save_spec(spec, path)
    print(f"Added item {item.get('id')} -> {path}")
    return 0


def cmd_add_creature(args: argparse.Namespace) -> int:
    spec, path = _load(args)
    if args.from_json:
        creature = json.loads(Path(args.from_json).read_text(encoding="utf-8") if Path(args.from_json).is_file() else args.from_json)
    elif args.preset == "tile":
        eid = args.creature_id or f"{spec['skill_id']}_{slug_name(args.name or 'tile').lower()}"
        creature = make_tile(
            eid=eid,
            name=args.name or eid,
            description=args.description or "",
            glyph_index=args.glyph or 1,
            health=args.health or 1,
        )
    else:
        eid = args.creature_id or f"{spec['skill_id']}_{slug_name(args.name or 'summon').lower()}"
        creature = make_creature(
            eid=eid,
            name=args.name or eid,
            preset=args.preset,
            description=args.description or "",
            health=args.health if args.health is not None else 80,
            damage=_damage_pair(args.damage, [3, 6]),
            damage_type=args.damage_type or "physical",
            glyph_index=args.glyph if args.glyph is not None else 90,
            can_regenerate_health=False if args.no_health_regen else None,
        )
    add_entity(spec, creature)
    if args.grant_milestone:
        grant_entity_milestones(creature, _csv_list(args.grant_milestone))
        add_entity(spec, creature)
    if args.summon_ability:
        bind_ability_entity(spec, args.summon_ability, "summon", creature["id"])
    save_spec(spec, path)
    print(f"Added {creature.get('_role') or 'creature'} {creature.get('id')} -> {path}")
    return 0


def _clone_ability_animation(spec: dict, ability: dict) -> None:
    src = str(ability.get("animation") or "").strip()
    if not src:
        print("No animation id on ability; skipped --clone-animation")
        return
    anim_id = f"{ability['id']}_fx"
    try:
        anim = clone_animation(src, new_id=anim_id, name=f"{ability.get('name') or ability['id']} FX")
    except FileNotFoundError as exc:
        raise SystemExit(str(exc)) from exc
    add_animation(spec, anim, bind_ability=ability["id"])
    print(f"Cloned animation {src} -> {anim_id}")


def cmd_clone_ability(args: argparse.Namespace) -> int:
    spec, path = _load(args)
    try:
        ability = clone_ability(
            args.source,
            skill_id=spec["skill_id"],
            new_id=args.new_id or args.ability_id,
            name=args.name,
            keep_image=bool(args.keep_image),
        )
    except (FileNotFoundError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    add_ability(spec, ability, unlock_level=args.unlock_level, no_milestone=args.no_milestone)
    if args.clone_animation:
        _clone_ability_animation(spec, ability)
    save_spec(spec, path)
    print(f"Cloned {args.source} -> {ability.get('id')}")
    return 0


def cmd_list_abilities(args: argparse.Namespace) -> int:
    if args.search:
        rows = search_abilities(args.search, limit=args.limit or 40)
        if args.json:
            print(json.dumps(rows, indent=2))
            return 0
        for row in rows:
            print(f"{row['source']:16} {row['id']:40} {row['name']}")
        print(f"{len(rows)} matches")
        return 0
    spec, _ = _load(args)
    rows = spec.get("abilities") or []
    if args.json:
        print(json.dumps([{"id": a.get("id"), "name": a.get("name"), "target": a.get("target")} for a in rows], indent=2))
        return 0
    for a in rows:
        print(f"{a.get('id'):40} {a.get('name')}  target={a.get('target')}  anim={a.get('animation')}")
    print(f"{len(rows)} abilities in spec")
    return 0


def cmd_clone_entity(args: argparse.Namespace) -> int:
    spec, path = _load(args)
    new_id = args.new_id or f"{spec['skill_id']}_{slug_name(args.name or args.source).lower()}"
    ent = clone_entity(args.source, new_id=new_id, name=args.name)
    add_entity(spec, ent)
    if args.summon_ability:
        bind_ability_entity(spec, args.summon_ability, "summon", ent["id"])
    save_spec(spec, path)
    print(f"Cloned {args.source} -> {ent.get('id')} ({ent.get('_role')})")
    return 0


def cmd_list_entities(args: argparse.Namespace) -> int:
    if args.search:
        rows = search_entities(args.search, limit=args.limit or 40)
        if args.json:
            print(json.dumps(rows, indent=2))
            return 0
        for row in rows:
            print(f"{row['source']:16} {row['role']:10} {row['id']:40} {row['name']}")
        print(f"{len(rows)} matches")
        return 0
    spec, _ = _load(args)
    rows = spec.get("entities") or []
    if args.json:
        print(json.dumps([{"id": e.get("id"), "name": e.get("name"), "role": e.get("_role")} for e in rows], indent=2))
        return 0
    for e in rows:
        print(f"{(e.get('_role') or '?'):10} {e.get('id'):40} {e.get('name')}")
    print(f"{len(rows)} entities in spec")
    return 0


def cmd_tree(args: argparse.Namespace) -> int:
    spec, _ = _load(args)
    if args.json:
        print(json.dumps(tree_rows(spec), indent=2))
        return 0
    for row in tree_rows(spec):
        print(f"L{row['level']:<3} {row['kind']:<12} {row['name']:<28} {row['reward']}")
    return 0


def cmd_fill_stats_after_10(args: argparse.Namespace) -> int:
    spec, path = _load(args)
    added = fill_stats_after_10(spec, through=int(args.through or 50))
    save_spec(spec, path)
    points = (spec.get("skill") or {}).get("stat_points") or []
    if added:
        print(f"Added +1 statistic on {len(added)} levels: {added}")
    else:
        print("No missing post-10 statistic levels.")
    print(f"stat_points ({len(points)}): {points}")
    print("Milestones were left in place; a level can grant both a milestone and +1 statistic.")
    return 0


def cmd_generate_icons(args: argparse.Namespace) -> int:
    from s2_spritesheets import generate_spritesheets

    spec, path = _load(args)
    kinds = None
    if args.kinds:
        kinds = [part.strip() for part in str(args.kinds).replace(",", " ").split() if part.strip()]
    names = None
    if getattr(args, "names", None):
        names = [part.strip() for part in str(args.names).split(",") if part.strip()]
    written = generate_spritesheets(
        spec,
        path.parent,
        kinds=kinds,
        use_sd=not args.no_sd,
        overwrite=bool(args.overwrite),
        include_icon=not args.no_icon,
        include_thumbnail=bool(args.thumbnail),
        dry_run=bool(args.dry_run),
        limit=args.limit,
        steps=int(args.steps or 24),
        from_existing=bool(args.from_existing),
        strength=float(args.strength or 0.58),
        names=names,
    )
    if not args.dry_run:
        save_spec(spec, path)
    for rel in written:
        print(f"Wrote {rel}")
    if args.dry_run:
        print("Dry run; no files written.")
    elif not written:
        print("No sheets written (existing PNGs kept). Pass --overwrite to replace placeholders.")
    return 0


def cmd_inject_icon(args: argparse.Namespace) -> int:
    """Pack an external PNG (Cursor/SD/etc.) into one atlas cell via the repacker."""
    from s2_spritesheets import inject_external_icons

    spec, path = _load(args)
    inj: dict = {"png": str(Path(args.png).resolve())}
    if args.name:
        inj["name"] = args.name
    if args.sheet:
        inj["sheet"] = args.sheet
    if args.index is not None:
        inj["index"] = int(args.index)
    written = inject_external_icons(spec, [inj], path.parent)
    save_spec(spec, path)
    for rel in written:
        print(f"Wrote {rel}")
    return 0


def cmd_set_effect(args: argparse.Namespace) -> int:
    spec, path = _load(args)
    try:
        if args.clear:
            bucket = clear_ability_effect(spec, args.ability, args.key)
            save_spec(spec, path)
            print(f"Cleared {args.ability} {bucket}.{args.key}")
            return 0
        if args.value is None:
            raise SystemExit("set-effect needs --value, or --clear to remove the key")
        set_ability_effect(spec, args.ability, args.key, parse_value(args.value), keys=True if args.keys else None)
    except KeyError as exc:
        raise SystemExit(str(exc)) from exc
    save_spec(spec, path)
    print(f"Set {args.ability} {args.key}={args.value}")
    return 0


def _parse_bonuses(items: Optional[list]) -> list:
    bonuses = []
    for item in items or []:
        try:
            bonuses.append(bonus_from_kv(item))
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
    return bonuses


def _bonus_line(row: dict) -> str:
    parts = []
    for bonus in row.get("bonuses") or row.get("effects") or []:
        eid = bonus.get("effect")
        val = bonus.get("value")
        sec = bonus.get("secondary_value")
        if sec is not None:
            parts.append(f"{eid}={val}:{sec}")
        elif val is not None:
            parts.append(f"{eid}={val}")
        else:
            parts.append(str(eid))
    for key in ("cost_stamina", "range", "cooldown", "cast_time", "duration"):
        if key in row:
            parts.append(f"{key}={row[key]}")
    return ", ".join(parts) or "(none)"


def cmd_set_amplifier(args: argparse.Namespace) -> int:
    spec, path = _load(args)
    bonuses = _parse_bonuses(args.bonus) if args.bonus else None
    append = _parse_bonuses(args.append_bonus) if args.append_bonus else None
    try:
        row = patch_amplifier(
            spec,
            args.amplifier,
            name=args.name,
            amp_type=args.type,
            description=args.description,
            bonuses=bonuses,
            append_bonuses=append,
            clear_bonuses=bool(args.clear_bonuses),
            cooldown=args.cooldown,
            cast_time=args.cast_time,
            range_val=args.range,
            cost_stamina=args.cost_stamina,
            duration=args.duration,
            image=args.image,
        )
    except KeyError as exc:
        raise SystemExit(str(exc)) from exc
    save_spec(spec, path)
    print(f"Updated amplifier {row.get('id')}: {_bonus_line(row)}")
    return 0


def cmd_set_passive(args: argparse.Namespace) -> int:
    spec, path = _load(args)
    effects = _parse_bonuses(args.effect) if args.effect else None
    append = _parse_bonuses(args.append_effect) if args.append_effect else None
    try:
        row = patch_passive(
            spec,
            args.passive,
            name=args.name,
            effects=effects,
            append_effects=append,
            clear_effects=bool(args.clear_effects),
            apply_mode=args.apply_mode,
            image=args.image,
        )
    except KeyError as exc:
        raise SystemExit(str(exc)) from exc
    save_spec(spec, path)
    print(f"Updated passive {row.get('id')}: {_bonus_line(row)}")
    return 0


def cmd_set_stacker(args: argparse.Namespace) -> int:
    spec, path = _load(args)
    effects = _parse_bonuses(args.effect) if args.effect else None
    append = _parse_bonuses(args.append_effect) if args.append_effect else None
    try:
        row = patch_stacker(
            spec,
            args.stacker,
            name=args.name,
            effects=effects,
            append_effects=append,
            clear_effects=bool(args.clear_effects),
            max_stacks=args.max_stacks,
            duration=args.duration,
            description=args.description,
            image=args.image,
            apply_caster=True if args.apply_caster else (False if args.no_apply_caster else None),
        )
    except KeyError as exc:
        raise SystemExit(str(exc)) from exc
    save_spec(spec, path)
    print(f"Updated stacker {row.get('id')}: {_bonus_line(row)}")
    return 0


def cmd_set_ability(args: argparse.Namespace) -> int:
    spec, path = _load(args)
    try:
        ab = find_row(spec.get("abilities") or [], args.ability, what="Ability")
    except KeyError as exc:
        raise SystemExit(str(exc)) from exc
    if args.name:
        ab["name"] = args.name
    if args.description is not None:
        ab["description"] = args.description
    if args.target:
        ab["target"] = args.target
    if args.range is not None:
        ab["range"] = args.range
    if args.animation:
        ab["animation"] = args.animation
    if args.image is not None:
        ab["image"] = args.image
    if args.damage:
        ab.setdefault("effects", {})["damage"] = parse_value(args.damage)
    if args.damage_type:
        ab.setdefault("effects", {})["damage_type"] = args.damage_type
    patch_ability_costs(
        ab,
        stamina=args.stamina,
        health=args.health,
        cast_time=args.cast_time,
        cooldown=args.cooldown,
        duration=args.duration,
        min_range=args.min_range,
    )
    for item in args.effect or []:
        try:
            apply_ability_kv(ab, item)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
    for key in args.clear_effect or []:
        try:
            clear_ability_effect(spec, args.ability, key)
        except KeyError as exc:
            raise SystemExit(str(exc)) from exc
    ensure_aoe_shape(ab)
    save_spec(spec, path)
    print(f"Updated ability {ab.get('id')}")
    return 0


def cmd_cycle_images(args: argparse.Namespace) -> int:
    spec, path = _load(args)
    kinds = _csv_list(args.kind) or None
    try:
        counts = cycle_images(spec, kinds=kinds, modulo=args.modulo)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    save_spec(spec, path)
    summary = ", ".join(f"{k}={n}" for k, n in counts.items())
    print(f"Cycled image indexes (mod {args.modulo}): {summary}")
    return 0


def _cmd_remove_kind(args: argparse.Namespace, *, kind: str, flag: str, fn) -> int:
    spec, path = _load(args)
    ids = getattr(args, flag) or []
    removed = []
    for rid in ids:
        try:
            row = fn(spec, rid)
        except KeyError as exc:
            raise SystemExit(str(exc)) from exc
        removed.append(f"{row.get('id')} ({row.get('name')})")
    if not removed:
        raise SystemExit(f"Provide --{flag.replace('_', '-')} at least once")
    save_spec(spec, path)
    print(f"Removed {kind} " + ", ".join(removed))
    return 0


def cmd_remove_amplifier(args: argparse.Namespace) -> int:
    return _cmd_remove_kind(args, kind="amplifier", flag="amplifier", fn=remove_amplifier)


def cmd_remove_ability(args: argparse.Namespace) -> int:
    return _cmd_remove_kind(args, kind="ability", flag="ability", fn=remove_ability)


def cmd_remove_passive(args: argparse.Namespace) -> int:
    return _cmd_remove_kind(args, kind="passive", flag="passive", fn=remove_passive)


def cmd_list_amplifiers(args: argparse.Namespace) -> int:
    spec, _ = _load(args)
    rows = spec.get("amplifiers") or []
    if args.json:
        print(json.dumps([{"id": r.get("id"), "name": r.get("name"), "type": r.get("type"), "bonuses": r.get("bonuses")} for r in rows], indent=2))
        return 0
    for row in rows:
        print(f"{row.get('id'):42} {(row.get('type') or '?'):10} {row.get('name')}  {_bonus_line(row)}")
    print(f"{len(rows)} amplifiers in spec")
    return 0


def cmd_list_passives(args: argparse.Namespace) -> int:
    spec, _ = _load(args)
    rows = spec.get("passives") or []
    if args.json:
        print(json.dumps([{"id": r.get("id"), "name": r.get("name"), "effects": r.get("effects")} for r in rows], indent=2))
        return 0
    for row in rows:
        print(f"{row.get('id'):42} {row.get('name')}  {_bonus_line(row)}")
    print(f"{len(rows)} passives in spec")
    return 0


def cmd_list_stackers(args: argparse.Namespace) -> int:
    spec, _ = _load(args)
    rows = spec.get("stackers") or []
    if args.json:
        print(json.dumps(rows, indent=2))
        return 0
    for row in rows:
        print(f"{row.get('id'):42} {row.get('name')}  stacks={row.get('max_stacks')} dur={row.get('duration')}  {_bonus_line(row)}")
    print(f"{len(rows)} stackers in spec")
    return 0


def cmd_set_slots(args: argparse.Namespace) -> int:
    spec, path = _load(args)
    slots = {}
    if args.offensive is not None:
        slots["offensive"] = args.offensive
    if args.defensive is not None:
        slots["defensive"] = args.defensive
    if args.utility is not None:
        slots["utility"] = args.utility
    set_slots(spec, args.ability, **slots)
    save_spec(spec, path)
    print(f"Slots {args.ability}: {slots}")
    return 0


def cmd_list_races(args: argparse.Namespace) -> int:
    if args.search:
        rows = search_races(args.search, limit=args.limit or 40)
        if args.json:
            print(json.dumps(rows, indent=2))
            return 0
        for row in rows:
            flag = "playable" if row.get("playable") else "npc"
            civ = " civ" if row.get("civilization") else ""
            print(f"{row['source']:16} {row['id']:12} {row['name']:<22} {flag}{civ}")
        print(f"{len(rows)} matches")
        return 0
    spec, _ = _load(args)
    rows = spec.get("races") or []
    if args.json:
        print(json.dumps(rows, indent=2))
        return 0
    for race in rows:
        print(f"{race.get('id'):16} {race.get('name')}  playable={race.get('playable')}")
    print(f"{len(rows)} races in spec")
    return 0


def cmd_clone_race(args: argparse.Namespace) -> int:
    spec, path = _load(args)
    display = args.name or args.source
    new_id = args.race_id or args.new_id or f"{spec['skill_id']}_{slug_name(display).lower()}"
    try:
        race, blobs = clone_race(
            args.source,
            new_id=new_id,
            name=args.name,
            keep_id=bool(args.keep_id),
            civilization=bool(args.civilization),
            overlay=bool(args.overlay),
        )
    except FileNotFoundError as exc:
        raise SystemExit(str(exc)) from exc
    if args.playable is True:
        race["playable"] = True
    if args.passive:
        race["passives"] = list(dict.fromkeys(list(race.get("passives") or []) + _csv_list(args.passive)))
    if args.ability:
        race["abilities"] = list(dict.fromkeys(list(race.get("abilities") or []) + _csv_list(args.ability)))
    if args.item:
        race["items"] = list(dict.fromkeys(list(race.get("items") or []) + _csv_list(args.item)))
    if args.recipe:
        race["recipes"] = list(dict.fromkeys(list(race.get("recipes") or []) + _csv_list(args.recipe)))
    bases = dict(race.get("base_entities") or {})
    for item in args.base_entity or []:
        try:
            role, eid = parse_base_entity(item)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        bases[role] = eid
    if bases:
        race["base_entities"] = bases
    for item in args.stat or []:
        try:
            key, value = parse_stat_flag(item)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        race.setdefault("statistics", {})[key] = value
    add_race(spec, race, name_files=blobs or None)
    save_spec(spec, path)
    print(f"Cloned race {args.source} -> {race.get('id')}")
    return 0


def cmd_add_race(args: argparse.Namespace) -> int:
    spec, path = _load(args)
    if args.from_json:
        race = json.loads(Path(args.from_json).read_text(encoding="utf-8") if Path(args.from_json).is_file() else args.from_json)
        add_race(spec, race)
        save_spec(spec, path)
        print(f"Added race {race.get('id')} -> {path}")
        return 0
    if not args.name:
        raise SystemExit("add-race needs --name (or --from-json / clone-race)")
    rid = args.race_id or f"{spec['skill_id']}_{slug_name(args.name).lower()}"
    stats = {}
    for item in args.stat or []:
        try:
            key, value = parse_stat_flag(item)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        stats[key] = value
    settle = make_settlement(
        max_settlements=args.settle_max,
        disabled_trading=bool(args.no_trading),
        collapse_on_leader_death=True if args.collapse_on_leader_death else None,
        war_causes=_csv_list(args.war_cause) or None,
        birth_resource=args.birth_resource,
        birth_amount=args.birth_amount if args.birth_amount is not None else 1,
        aggression_default=True if args.aggression_default else None,
        single_family=bool(args.single_family),
        migration=False if args.no_migration else None,
    )
    bases = {}
    for item in args.base_entity or []:
        try:
            role, eid = parse_base_entity(item)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        bases[role] = eid
    race, blobs = make_race(
        race_id=rid,
        name=args.name,
        description=args.description or "",
        playable=not args.unplayable,
        statistics=stats or None,
        tags=_csv_list(args.tag) or None,
        passives=_csv_list(args.passive) or None,
        abilities=_csv_list(args.ability) or None,
        items=_csv_list(args.item) or None,
        recipes=_csv_list(args.recipe) or None,
        adult=args.adult if args.adult is not None else 50,
        child=args.child if args.child is not None else 14,
        elder=args.elder if args.elder is not None else 70,
        settlement=None if args.no_settle else settle,
        base_entities=bases or None,
        orphan_surname=args.orphan_surname,
    )
    if args.new_tag:
        tag_id = args.new_tag_id or rid
        add_character_tag(spec, make_character_tag(tag_id=tag_id, name=args.new_tag))
        tags = list(race.get("tags") or [])
        if str(tag_id) not in tags:
            tags.append(str(tag_id))
            race["tags"] = tags
    add_race(spec, race, name_files=blobs)
    save_spec(spec, path)
    print(f"Added race {race.get('id')} -> {path}")
    return 0


def cmd_add_control_action(args: argparse.Namespace) -> int:
    spec, path = _load(args)
    tags = _csv_list(args.tag)
    if not tags:
        raise SystemExit("add-control-action needs --tag (creature tag id, e.g. 2 animal / 4 undead)")
    name = args.name or "Control"
    cid = args.action_id or f"{spec['skill_id']}_{slug_name(name).lower()}"
    try:
        action = make_control_action(
            action_id=cid,
            name=name,
            tags=tags,
            description=args.description,
            clone_from=args.clone or "core_2_tame",
        )
    except FileNotFoundError as exc:
        raise SystemExit(str(exc)) from exc
    add_control_action(spec, action)
    save_spec(spec, path)
    print(f"Added control action {action.get('id')} -> {path}")
    return 0


def cmd_list_tags(args: argparse.Namespace) -> int:
    rows = search_tags(args.search or "", limit=args.limit or 80)
    if args.json:
        print(json.dumps(rows, indent=2))
        return 0
    for row in rows:
        print(f"{row['id']:8} {row['name']}")
    print(f"{len(rows)} tags")
    return 0


def cmd_list_control_actions(args: argparse.Namespace) -> int:
    in_spec = bool(getattr(args, "id", None) or getattr(args, "spec", None))
    q = args.search or ""
    if in_spec and not q:
        spec, _ = _load(args)
        rows = spec.get("control_actions") or []
        if args.json:
            print(json.dumps(rows, indent=2))
            return 0
        for row in rows:
            print(f"{row.get('id'):32} {row.get('name')}  tags={','.join(str(t) for t in (row.get('tags') or []))}")
        print(f"{len(rows)} control actions in spec")
        return 0
    rows = search_control_actions(q, limit=args.limit or 40)
    if args.json:
        print(json.dumps(rows, indent=2))
        return 0
    for row in rows:
        tags = ",".join(str(t) for t in (row.get("tags") or []))
        print(f"{row['source']:16} {row['id']:32} {row['name']:<22} tags={tags}")
    print(f"{len(rows)} control actions")
    return 0


def cmd_add_production_action(args: argparse.Namespace) -> int:
    spec, path = _load(args)
    if not args.clone and not args.name:
        raise SystemExit("add-production-action needs --clone and/or --name")
    try:
        if args.clone:
            src = load_vanilla_production_action(args.clone)
            display = args.name or str(src.get("name") or args.clone)
            cid = args.action_id or f"{spec['skill_id']}_{slug_name(display).lower()}"
            action = make_production_action(
                cid,
                display,
                description=args.description or "",
                required_tool=args.tool if args.tool is not None else 0,
                image=args.image if args.image is not None else 0,
                sound=args.sound or "",
                equipment=bool(args.equipment),
                clone_from=args.clone,
            )
            if not args.name:
                action["name"] = src.get("name") or action.get("name")
        else:
            cid = args.action_id or f"{spec['skill_id']}_{slug_name(args.name).lower()}"
            action = make_production_action(
                cid,
                args.name,
                description=args.description or "",
                required_tool=args.tool if args.tool is not None else 0,
                image=args.image if args.image is not None else 0,
                sound=args.sound or "",
                equipment=bool(args.equipment),
            )
    except FileNotFoundError as exc:
        raise SystemExit(str(exc)) from exc
    add_production_action(spec, action)
    if args.unlock_level is not None:
        grant_existing(
            spec,
            kind="production_action",
            reward_id=str(action["id"]),
            name=action.get("name") or name,
            unlock_level=args.unlock_level,
        )
    save_spec(spec, path)
    print(f"Added production action {action.get('id')} -> {path}")
    return 0


def cmd_list_production_actions(args: argparse.Namespace) -> int:
    in_spec = bool(getattr(args, "id", None) or getattr(args, "spec", None))
    q = args.search or ""
    if in_spec and not q:
        spec, _ = _load(args)
        rows = spec.get("production_actions") or []
        if args.json:
            print(json.dumps(rows, indent=2))
            return 0
        for row in rows:
            print(f"{row.get('id'):32} {row.get('name')}  tool={row.get('required_tool')}")
        print(f"{len(rows)} production actions in spec")
        return 0
    rows = search_production_actions(q, limit=args.limit or 40)
    if args.json:
        print(json.dumps(rows, indent=2))
        return 0
    for row in rows:
        print(f"{row['source']:16} {row['id']:12} {row['name']:<22} tool={row.get('required_tool')}")
    print(f"{len(rows)} production actions")
    return 0


def cmd_dump_production_action(args: argparse.Namespace) -> int:
    try:
        row = load_vanilla_production_action(args.action_id)
    except FileNotFoundError as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps({k: v for k, v in row.items() if not str(k).startswith("_")}, indent=2))
    return 0


def cmd_grant_existing(args: argparse.Namespace) -> int:
    spec, path = _load(args)
    try:
        grant_existing(
            spec,
            kind=args.kind,
            reward_id=args.reward,
            name=args.name or args.reward,
            unlock_level=args.unlock_level,
            innate=bool(args.innate),
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    save_spec(spec, path)
    print(f"Granted {args.kind} {args.reward} at L{args.unlock_level}")
    return 0


def cmd_dump_race(args: argparse.Namespace) -> int:
    try:
        race = load_vanilla_race(args.race_id)
        print(json.dumps(public_race(race), indent=2))
        return 0
    except FileNotFoundError:
        pass
    if getattr(args, "spec", None) or getattr(args, "id", None):
        spec, _ = _load(args)
        for race in spec.get("races") or []:
            if str(race.get("id") or "") == str(args.race_id) or str(race.get("name") or "").lower() == str(args.race_id).lower():
                print(json.dumps(public_race(race), indent=2))
                return 0
    print(f"Race not found: {args.race_id}", file=sys.stderr)
    return 1


def cmd_dump_control_action(args: argparse.Namespace) -> int:
    try:
        row = load_vanilla_control_action(args.action_id)
        row.pop("_cloned_from", None)
        row.pop("_source", None)
        print(json.dumps(row, indent=2))
        return 0
    except FileNotFoundError:
        print(f"Control action not found: {args.action_id}", file=sys.stderr)
        return 1


def cmd_list_buildings(args: argparse.Namespace) -> int:
    if args.search:
        rows = search_buildings(args.search, limit=args.limit or 40)
        if args.json:
            print(json.dumps(rows, indent=2))
            return 0
        for row in rows:
            enables = ",".join(row.get("enables") or []) or "-"
            player = "player" if row.get("allow_player") else "civ"
            print(f"{row['source']:16} {row['id']:28} {row['name']:<28} {player} enables={enables}")
        print(f"{len(rows)} matches")
        return 0
    spec, _ = _load(args)
    rows = spec.get("buildings") or []
    if args.json:
        print(json.dumps([public_building(b) for b in rows], indent=2))
        return 0
    for b in rows:
        print(f"{b.get('id'):28} {b.get('name')}  enables={','.join(b.get('enables') or []) or '-'}")
    print(f"{len(rows)} buildings in spec")
    return 0


def cmd_dump_building(args: argparse.Namespace) -> int:
    try:
        row = load_building(args.building_id)
        print(json.dumps(public_building(row), indent=2))
        return 0
    except FileNotFoundError:
        pass
    if getattr(args, "spec", None) or getattr(args, "id", None):
        spec, _ = _load(args)
        for b in spec.get("buildings") or []:
            if str(b.get("id") or "") == str(args.building_id) or str(b.get("name") or "").lower() == str(args.building_id).lower():
                print(json.dumps(public_building(b), indent=2))
                return 0
    print(f"Building not found: {args.building_id}", file=sys.stderr)
    return 1


def cmd_clone_building(args: argparse.Namespace) -> int:
    spec, path = _load(args)
    display = args.name or args.source
    new_id = args.building_id or f"{spec['skill_id']}_{slug_name(display).lower()}"
    enables = _csv_list(args.enable) if args.enable else ([spec["skill_id"]] if args.train else None)
    try:
        row = clone_building(args.source, new_id=new_id, name=args.name, enables=enables)
    except FileNotFoundError as exc:
        raise SystemExit(str(exc)) from exc
    add_building(spec, row)
    save_spec(spec, path)
    print(f"Cloned building {args.source} -> {row.get('id')} enables={row.get('enables')}")
    return 0


def cmd_add_training_building(args: argparse.Namespace) -> int:
    spec, path = _load(args)
    name = args.name or f"{spec['skill'].get('name') or spec['skill_id']} Hall"
    new_id = args.building_id or f"{spec['skill_id']}_hall"
    skill_id = args.enable or spec["skill_id"]
    row = make_training_building(
        new_id=new_id,
        name=name,
        skill_id=skill_id,
        template=args.template,
    )
    add_building(spec, row)
    save_spec(spec, path)
    print(f"Training building {row.get('id')} enables={row.get('enables')} (template {args.template})")
    return 0


def cmd_copy_building_map(args: argparse.Namespace) -> int:
    src = Path(args.source) if Path(args.source).suffix.lower() == ".smap" else find_building_map(args.source)
    if src is None:
        raise SystemExit(f"No existing .smap found for {args.source}")
    dest_dir = Path(args.dest) if args.dest else staging_dir(_load(args)[0]) / "building_maps"
    out = copy_building_map(src, dest_dir, dest_name=args.name)
    print(f"Copied {src} -> {out}")
    return 0


def _fix_targets(args: argparse.Namespace) -> list[Path]:
    names = list(args.mods or [])
    if not names:
        names = ["officers", "battlemages", "silkworm"]
    out = []
    for name in names:
        p = Path(name)
        if p.is_dir() and (p / "mod.json").is_file():
            out.append(p.resolve())
            continue
        out.append(resolve_workshop_mod(name))
    return out


def cmd_fix_buildings(args: argparse.Namespace) -> int:
    if getattr(args, "id", None) or getattr(args, "spec", None):
        spec, path = _load(args)
        from s2_buildings import fix_building

        changed = 0
        for b in spec.get("buildings") or []:
            notes = fix_building(b)
            if notes:
                changed += 1
                print(f"{b.get('id')}: {', '.join(notes)}")
        save_spec(spec, path)
        print(f"Fixed {changed} buildings in spec")
        return 0
    try:
        folders = _fix_targets(args)
    except FileNotFoundError as exc:
        raise SystemExit(str(exc)) from exc
    rc = 0
    for folder in folders:
        issues = scan_mod_folder(folder)
        print(f"== {folder.name} {folder} ==")
        if issues:
            for line in issues:
                print(f"  {line}")
        else:
            print("  (no 0.10 building issues)")
        if args.scan and not args.apply:
            continue
        if not args.apply:
            print("  pass --apply to write Output (and --in-place to patch workshop)")
            continue
        dest = Path(args.dest) if args.dest and len(folders) == 1 else copy_mod_to_output(folder)
        if dest.resolve() != folder.resolve():
            notes = upgrade_mod_folder(dest)
            print(f"  Output {dest}")
            for n in notes:
                print(f"    {n}")
        if args.in_place:
            notes = upgrade_mod_folder(folder)
            print(f"  In-place {folder}")
            for n in notes:
                print(f"    {n}")
        leftover = scan_mod_folder(dest if dest.exists() else folder)
        if leftover:
            print("  remaining:")
            for line in leftover:
                print(f"    {line}")
            rc = 1
    return rc


def cmd_fix_mods(args: argparse.Namespace) -> int:
    try:
        folders = resolve_fix_targets(
            list(args.mods or []),
            workshop=bool(args.workshop),
            enabled=bool(args.enabled),
        )
    except FileNotFoundError as exc:
        raise SystemExit(str(exc)) from exc
    if not folders:
        print("No mods found.")
        return 1
    apply = bool(args.apply or args.in_place)
    if not apply and not args.scan:
        print("Scanning. Pass --apply to write Output/_fixed copies; --in-place also patches workshop.")
        args.scan = True
    rc = 0
    touched = 0
    clean = 0
    for folder in folders:
        issues = scan_outdated_mod(folder)
        print(f"== {folder.name} {summarize_scan(issues)} ==")
        for line in issues:
            print(f"  {line}")
        if args.scan and not apply:
            if issues:
                rc = 1
            else:
                clean += 1
            continue
        if not issues and not args.force:
            clean += 1
            continue
        dest = Path(args.dest) if args.dest and len(folders) == 1 else copy_mod_to_fixed(folder)
        wrote = False
        if dest.resolve() != folder.resolve():
            notes = upgrade_outdated_mod(dest)
            print(f"  Output {dest}")
            for n in notes:
                print(f"    {n}")
            wrote = wrote or bool(notes)
        if args.in_place:
            notes = upgrade_outdated_mod(folder)
            print(f"  In-place {folder}")
            for n in notes:
                print(f"    {n}")
            wrote = wrote or bool(notes)
        if wrote:
            touched += 1
        leftover = scan_outdated_mod(folder if args.in_place else dest)
        leftover = [x for x in leftover if not x.startswith("assets.json overlays particles32")]
        if leftover:
            print("  remaining:")
            for line in leftover:
                print(f"    {line}")
            rc = 1
    print(f"Scanned {len(folders)} mods; {clean} already ok; {touched} updated")
    if args.in_place:
        print("Patched workshop in place. Steam can overwrite these folders on next update.")
    return rc


def cmd_validate(args: argparse.Namespace) -> int:
    if args.vanilla:
        issues = validate_vanilla()
        print(format_issues(issues))
        return 1 if any(i.level == "error" for i in issues) else 0
    spec, _ = _load(args)
    issues = validate_spec(spec)
    print(format_issues(issues))
    return 1 if any(i.level == "error" for i in issues) else 0


def cmd_write(args: argparse.Namespace) -> int:
    spec, _ = _load(args)
    issues = validate_spec(spec)
    print(format_issues(issues))
    if any(i.level == "error" for i in issues) and not args.force:
        print("Write aborted because of errors. Fix them or pass --force.", file=sys.stderr)
        return 1
    dest = Path(args.output) if args.output else None
    root = write_mod(spec, dest)
    print(f"Wrote mod: {root}")
    if (root / "character.json").is_file():
        print(f"Wrote character.json ({len(spec.get('races') or [])} races, {len(spec.get('control_actions') or [])} control actions, {len(spec.get('production_actions') or [])} production actions)")
    return 0


def cmd_install(args: argparse.Namespace) -> int:
    if not args.yes:
        print(
            "install copies into the live Soulash 2 mods folder. Re-run with --yes only if the human asked to install.",
            file=sys.stderr,
        )
        return 2
    spec, _ = _load(args)
    dest = mods_dir() / (args.mod or spec["id"])
    issues = validate_spec(spec)
    print(format_issues(issues))
    if any(i.level == "error" for i in issues) and not args.force:
        print("Install aborted because of errors. Fix them or pass --force --yes.", file=sys.stderr)
        return 1
    root = write_mod(spec)
    dest.mkdir(parents=True, exist_ok=True)
    skip_names = {"skill.json", "_sd_work", "__pycache__", "_fx_preview", "_icon_preview"}
    leftover_preview = dest / "_fx_preview"
    if leftover_preview.is_dir():
        shutil.rmtree(leftover_preview)
    for item in root.iterdir():
        if item.name in skip_names:
            continue
        target = dest / item.name
        if item.is_dir():
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(item, target)
        else:
            shutil.copy2(item, target)
    print(f"Installed -> {dest}")
    return 0


def cmd_dump(args: argparse.Namespace) -> int:
    aid = args.ability_id
    try:
        data = load_vanilla_ability(aid)
        data.pop("_cloned_from", None)
        print(json.dumps(data, indent=2))
        return 0
    except FileNotFoundError:
        pass
    if getattr(args, "spec", None) or getattr(args, "id", None):
        spec, _ = _load(args)
        for ab in spec.get("abilities") or []:
            if ab.get("id") == aid:
                print(json.dumps(ab, indent=2))
                return 0
    print(f"Ability not found: {aid}", file=sys.stderr)
    return 1


def cmd_editor(args: argparse.Namespace) -> int:
    from s2_editor import run_server

    spec = None
    if getattr(args, "spec", None):
        spec = Path(args.spec)
    elif getattr(args, "id", None):
        spec = output_root() / args.id / "skill.json"
    run_server(
        args.host or "127.0.0.1",
        int(args.port or 8775),
        spec,
        open_browser=not args.no_browser,
        start_path="/planner.html" if args.planner else "/",
    )
    return 0


def cmd_planner(args: argparse.Namespace) -> int:
    if getattr(args, "web", False):
        args.planner = True
        args.spec = None
        args.id = None
        args.host = getattr(args, "host", None) or "127.0.0.1"
        args.port = getattr(args, "port", None) or 8775
        args.no_browser = bool(getattr(args, "no_browser", False))
        return cmd_editor(args)
    from s2_planner_gui import run_gui

    return run_gui()


def cmd_plan_dump(args: argparse.Namespace) -> int:
    from s2_planner import evaluate, load_overlay

    overlay = load_overlay(args.mod)
    alloc = {}
    for item in args.alloc or []:
        sid, _, raw = str(item).partition("=")
        alloc[sid.strip()] = int(raw or 10)
    result = evaluate(
        overlay,
        race_id=str(args.race),
        starting=list(args.start or []),
        allocations=alloc,
        stage=args.stage,
    )
    print(json.dumps({
        "max_potential": overlay["max_potential"],
        "skills": len(overlay["skills"]),
        "races": len(overlay["races"]),
        "missing": overlay["missing"],
        "eval": {
            "race": result["race"]["name"],
            "stage": result["stage"],
            "pool": result["pool"],
            "age_bonus": result["age_bonus"],
            "available": result["available"],
            "spent": result["spent"],
            "remaining": result["remaining"],
            "gold": result["gold"],
            "age": result["age"],
            "budgets": result["budgets"],
        },
    }, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="s2_skill_cli", description="Soulash 2 skill creator")
    sub = p.add_subparsers(dest="command", required=True)

    m = sub.add_parser("mine", help="Rebuild effect catalog from docs + core_2 + workshop + Soulash 2.exe")
    m.set_defaults(func=cmd_mine)

    le = sub.add_parser("list-effects", help="List mined effects")
    le.add_argument("--kind", choices=["ability", "ability_key", "passive", "amplifier", "amplifier_field", "stacker", "stacker_field"])
    le.add_argument("--json", action="store_true")
    le.add_argument("--dropdown", action="store_true", help="Only confirmed in-game-style ids (no exe-only guesses)")
    le.set_defaults(func=cmd_list_effects)

    ex = sub.add_parser("explain", help="Show one effect")
    ex.add_argument("effect_id")
    ex.add_argument("--kind")
    ex.set_defaults(func=cmd_explain)

    n = sub.add_parser("new", help="Create empty skill spec in Output/Soulash2")
    n.add_argument("--id", required=True)
    n.add_argument("--name", required=True)
    n.add_argument("--mod")
    n.add_argument("--output", "-o")
    n.add_argument("--no-prefix", action="store_true", help="Do not prepend the author slug (arendeth_). Vanilla is core_2_*; custom skills should keep the prefix.")
    n.add_argument("--level-start", type=int, help="Optional skills.json starting level (patch)")
    n.add_argument("--no-combat", action="store_true", help="Crafting/utility skill: no combat_skill, no level-30 mastery")
    n.add_argument("--no-mastery", action="store_true", help="Combat skill without the Skill Stat Rebalance level-30 +10% all-attributes passive")
    n.add_argument("--difficulty", type=int, help="skills.json difficulty (vanilla Adventuring is 0)")
    n.add_argument("--exp-source", action="append", help="Repeatable id=rate, e.g. ability=2 or production=2:6")
    n.add_argument("--gear", action="append", help="Repeatable starting_gear: 70:1 or first=70:1,second=111:1")
    n.add_argument("--thumbnail", help="mod.json Steam workshop PNG (4:3). write generates a placeholder")
    n.add_argument("--steam-publish-id", type=int, help="mod.json steam_publish_id (docs §2)")
    n.add_argument("--disable-portraits", action="store_true", help="Global; overrides other mods. Usually omit")
    n.set_defaults(func=cmd_new)

    def spec_args(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--spec")
        sp.add_argument("--id")

    ss = sub.add_parser("set-skill", help="Patch skills.json / mod.json fields (starting_gear, exp_sources, thumbnail)")
    spec_args(ss)
    ss.add_argument("--combat", action="store_true")
    ss.add_argument("--no-combat", action="store_true")
    ss.add_argument("--difficulty", type=int)
    ss.add_argument("--level-start", type=int)
    ss.add_argument("--description")
    ss.add_argument("--name", help="In-game skill name (skills.json)")
    ss.add_argument("--mod-name", help="mod.json display name (defaults to --name)")
    ss.add_argument("--exp-source", action="append", help="Append id=rate (ability=2). Use --replace-exp to start clean")
    ss.add_argument("--replace-exp", action="store_true")
    ss.add_argument("--gear", action="append")
    ss.add_argument("--clear-gear", action="store_true")
    ss.add_argument("--thumbnail")
    ss.add_argument("--steam-publish-id", type=int)
    ss.add_argument("--disable-portraits", action="store_true")
    ss.add_argument("--clear-disable-portraits", action="store_true")
    ss.add_argument("--version", help="mod.json version (e.g. 2.1.0)")
    ss.add_argument("--author")
    ss.add_argument("--mod-description", help="mod.json description (distinct from --description on the skill)")
    ss.add_argument(
        "--stat-points",
        choices=["default", "rebalance", "after10", "early", "vanilla", "none"],
        help="Replace skill.stat_points. default/rebalance/after10 = 11–50 only (Skill Stat Rebalance). early = 2,4,5,7,8,10 then 11–50. vanilla = interleaved Pyromancy. Milestones stay put.",
    )
    ss.add_argument(
        "--fill-stats-after-10",
        action="store_true",
        help="Union levels 11–50 into stat_points without moving milestones",
    )
    ss.set_defaults(func=cmd_set_skill)

    rid = sub.add_parser(
        "rename-id",
        help="Rewrite skill/mod id and every owned <old>_* id, then move the staging folder",
    )
    spec_args(rid)
    rid.add_argument("--to", required=True, help="New skill id (author prefix is added unless already present)")
    rid.add_argument("--no-prefix", action="store_true", help="Keep --to exactly; do not prepend arendeth_")
    rid.set_defaults(func=cmd_rename_id)

    ag = sub.add_parser("add-gear", help="Append a starting_gear choice (docs §5.1)")
    spec_args(ag)
    ag.add_argument("choice", help="70:1 or first=70:1,second=111:1 or 70:1|111:1")
    ag.set_defaults(func=cmd_add_gear)

    aes = sub.add_parser("add-exp-source", help="Append an exp_sources entry")
    spec_args(aes)
    aes.add_argument("source", help="ability=2 or production=2:6")
    aes.add_argument("--replace", action="store_true", help="Replace any existing row with the same id")
    aes.set_defaults(func=cmd_add_exp_source)

    ab = sub.add_parser("add-ability")
    spec_args(ab)
    ab.add_argument("--from-json")
    ab.add_argument("--clone", help="Copy a vanilla/workshop ability (id, name, or filename stem, e.g. 15 or Fireball)")
    ab.add_argument("--clone-animation", action="store_true", help="Also clone the source animation into this mod")
    ab.add_argument("--ability-id")
    ab.add_argument("--ability-name")
    ab.add_argument("--description")
    ab.add_argument("--target")
    ab.add_argument("--range", type=int)
    ab.add_argument("--min-range", type=int, help="Minimum range (docs §6.2)")
    ab.add_argument("--stamina", type=int, help="cost.stamina")
    ab.add_argument("--health", type=int, help="cost.health")
    ab.add_argument("--cost-item", help="cost.item entity id (docs Entity Cost)")
    ab.add_argument("--cost-item-type", type=int, help="cost.item_type (docs Item Type Cost; 18 is corpse)")
    ab.add_argument("--ammo", type=int, help="cost.ammo")
    ab.add_argument("--require-one-of", action="append", help="requirements.one_of weapon/item type id")
    ab.add_argument("--require-all", action="append", dest="require_always", help="requirements.always (docs require_all)")
    ab.add_argument("--cast-time", type=float)
    ab.add_argument("--cooldown", type=float)
    ab.add_argument("--duration", type=float)
    ab.add_argument("--damage")
    ab.add_argument("--damage-type")
    ab.add_argument("--summon", help="effects_keys.summon entity id (create the creature with add-creature first, or clone-entity)")
    ab.add_argument("--summon-count", type=int)
    ab.add_argument("--stacker", help="effects_keys.stacker id (create with add-stacker, or a core_2_ id)")
    ab.add_argument("--stacker-count", type=int)
    ab.add_argument("--animation", help="Vanilla animation id (0, 3, 65, core_2_…) or a cloned id from add-animation")
    ab.add_argument("--effect", action="append", help="Repeatable key=value. summon/construct/stacker go to effects_keys automatically. Example: --effect bleed=1 --effect aoe_range=2")
    ab.add_argument("--unlock-level", type=int)
    ab.add_argument("--no-milestone", action="store_true")
    ab.set_defaults(func=cmd_add_ability)

    am = sub.add_parser("add-amplifier", help="Create or replace an amplifier by id (same id updates, does not duplicate)")
    spec_args(am)
    am.add_argument("--from-json")
    am.add_argument("--amplifier-id")
    am.add_argument("--name")
    am.add_argument("--type", choices=["offensive", "defensive", "utility"])
    am.add_argument("--bonus", action="append", help="Repeatable effect=value or effect=value:secondary. Example: --bonus bleed=1 --bonus statistic_percent=dexterity:0.1")
    am.add_argument("--cooldown", type=float)
    am.add_argument("--cast-time", type=float)
    am.add_argument("--range", type=int)
    am.add_argument("--cost-stamina", type=int)
    am.add_argument("--description", help="Amplifier tooltip (unlike passives, this is used)")
    am.add_argument("--grant-existing")
    am.add_argument("--unlock-level", type=int)
    am.add_argument("--no-milestone", action="store_true")
    am.set_defaults(func=cmd_add_amplifier)

    ap = sub.add_parser("add-passive", help="Create or replace a passive by id (same id updates, does not duplicate)")
    spec_args(ap)
    ap.add_argument("--from-json")
    ap.add_argument("--passive-id")
    ap.add_argument("--name")
    ap.add_argument("--effect", action="append", help="Repeatable effect=value or effect=value:secondary")
    ap.add_argument("--apply-mode", choices=["party_only", "solo_only"], help="Replaces only_party")
    ap.add_argument("--restrict-tags", action="append", help="Only apply if the unit has these character tags")
    ap.add_argument("--restrict-tags-enemy", action="append", help="Only apply vs these enemy tags")
    ap.add_argument("--restrict-weapon-type", type=int, help="Weapon type index from messages.json")
    ap.add_argument("--innate", action="store_true", help="Innate milestone (empty requirements; grant on entities via skills.milestones)")
    ap.add_argument(
        "--unlock-level",
        type=int,
        help="Milestone skill level. Must be 11+ (1–10 is free). Use --innate for racial/entity grants.",
    )
    ap.add_argument("--no-milestone", action="store_true")
    ap.set_defaults(func=cmd_add_passive)

    acm = sub.add_parser(
        "add-combat-mastery",
        help="Unique level-30 passive: +10%% strength/dexterity/endurance/intelligence/willpower (Skill Stat Rebalance 3766934606)",
    )
    spec_args(acm)
    acm.add_argument("--unlock-level", type=int, default=30)
    acm.add_argument("--name", help="Default is '{skill name} Mastery'")
    acm.set_defaults(func=cmd_add_combat_mastery)

    st = sub.add_parser("add-stacker", help="Create or replace an ability_stackers.json entry (not a milestone). Bind with --bind-ability or add-ability --stacker")
    spec_args(st)
    st.add_argument("--from-json")
    st.add_argument("--clone", help="Copy a vanilla/workshop stacker id (e.g. core_2_freeze)")
    st.add_argument("--stacker-id")
    st.add_argument("--name")
    st.add_argument("--effect", action="append", help="Repeatable per-stack bonus: movement_speed=0.01")
    st.add_argument("--max-stacks", type=int)
    st.add_argument("--duration", type=int)
    st.add_argument("--apply-caster", action="store_true", help="Buff on caster. Default is a debuff on the target.")
    st.add_argument("--on-max-stacks-cast", help="Ability id to fire at max stacks")
    st.add_argument("--max-stacks-cast-unlock", action="store_true")
    st.add_argument("--image", type=int)
    st.add_argument("--description")
    st.add_argument("--bind-ability", help="Set this ability's effects_keys.stacker to the new stacker")
    st.add_argument("--stacker-count", type=int, default=1)
    st.set_defaults(func=cmd_add_stacker)

    la = sub.add_parser("list-animations", help="Search vanilla/workshop animations")
    la.add_argument("--search", required=True)
    la.add_argument("--limit", type=int, default=40)
    la.add_argument("--json", action="store_true")
    la.set_defaults(func=cmd_list_animations)

    lpset = sub.add_parser("list-anim-presets", help="Motion templates for new-animation (bolt/nova/wave/line/…)")
    lpset.add_argument("--json", action="store_true")
    lpset.set_defaults(func=cmd_list_anim_presets)

    lp = sub.add_parser("list-particles", help="Which vanilla animations use which particles32 tile_id")
    lp.add_argument("--search", default="")
    lp.add_argument("--limit", type=int, default=40)
    lp.add_argument("--json", action="store_true")
    lp.set_defaults(func=cmd_list_particles)

    da = sub.add_parser("dump-animation", help="Print vanilla/workshop animation JSON (does not retarget)")
    da.add_argument("source", help="Animation id, name, or filename stem (e.g. 196 or Water wave)")
    da.set_defaults(func=cmd_dump_animation)

    aa = sub.add_parser("add-animation", help="Clone a vanilla/workshop animation into this mod")
    spec_args(aa)
    aa.add_argument("--clone", help="Source id, name, or filename stem (e.g. 3 or Fireball or 3_Fireball)")
    aa.add_argument("--preset", choices=sorted(PRESETS), help="Motion template (see list-anim-presets)")
    aa.add_argument("--from-json")
    aa.add_argument("--animation-id")
    aa.add_argument("--name")
    aa.add_argument("--color", help="Recolor particles R,G,B or R,G,B,A (e.g. 114,113,115)")
    aa.add_argument("--clone-impact", action="store_true", help="Also clone on_impact animations and retarget this FX to them")
    aa.add_argument("--on-impact", help="Force every particle on_impact to this existing animation id")
    aa.add_argument("--bind-ability", action="append", help="Set this ability's animation field (repeatable)")
    aa.add_argument("--art", nargs="?", const="auto", help="Theme tint (steam/water/blood/ice/…) using vanilla particles32 glyphs. Does not copy the atlas.")
    aa.add_argument("--sd-art", action="store_true", help=argparse.SUPPRESS)
    aa.add_argument("--no-sd", action="store_true", help="Procedural circles instead of SD")
    aa.add_argument("--keep-tint", action="store_true", help="Keep particle color tint instead of white")
    aa.set_defaults(func=cmd_add_animation)

    na = sub.add_parser("new-animation", help="Author FX from a motion preset (vanilla particles32 glyphs, tinted)")
    spec_args(na)
    na.add_argument("--preset", choices=sorted(PRESETS), help="Motion template (list-anim-presets)")
    na.add_argument("--clone", help="Or clone this vanilla/workshop id instead of a preset")
    na.add_argument("--animation-id")
    na.add_argument("--name")
    na.add_argument("--color", help="Recolor particles R,G,B or R,G,B,A (also hints --art theme)")
    na.add_argument("--clone-impact", action="store_true", help="Clone on_impact FX into this mod and retarget")
    na.add_argument("--on-impact", help="Point all particle on_impact at this existing id instead of cloning")
    na.add_argument("--bind-ability", action="append", help="Bind this ability (repeatable)")
    na.add_argument("--art", nargs="?", const="auto", help="Theme tint on vanilla particles32 glyphs (does not copy the atlas)")
    na.add_argument("--sd-art", action="store_true", help=argparse.SUPPRESS)
    na.add_argument("--no-sd", action="store_true", help="Procedural circles instead of SD (placeholder-quality)")
    na.add_argument("--keep-tint", action="store_true")
    na.set_defaults(func=cmd_new_animation)

    ga = sub.add_parser(
        "generate-anim-art",
        help="Open the particle FX producer (vanilla glyphs + tint; does not copy particles32)",
    )
    spec_args(ga)
    ga.add_argument("--animation", action="append", help=argparse.SUPPRESS)
    ga.add_argument("--all", action="store_true", help=argparse.SUPPRESS)
    ga.add_argument("--theme", help=argparse.SUPPRESS)
    ga.add_argument("--no-sd", action="store_true", help=argparse.SUPPRESS)
    ga.add_argument("--sd", action="store_true", help=argparse.SUPPRESS)
    ga.add_argument("--overwrite", action="store_true", help=argparse.SUPPRESS)
    ga.add_argument("--keep-tint", action="store_true", help=argparse.SUPPRESS)
    ga.add_argument("--dry-run", action="store_true", help=argparse.SUPPRESS)
    ga.add_argument("--steps", type=int, default=24, help=argparse.SUPPRESS)
    ga.set_defaults(func=cmd_generate_anim_art)

    fx = sub.add_parser("particles", help="Open the particle FX producer desktop window")
    spec_args(fx)
    fx.set_defaults(func=cmd_particles)

    fxp = sub.add_parser(
        "fx-preview",
        help="Write labeled PNG previews of a vanilla/preset FX for vision (does not edit the spec)",
    )
    fxp.add_argument("--source", help="Vanilla/workshop animation id or name")
    fxp.add_argument("--preset", choices=sorted(PRESETS))
    fxp.add_argument("--name", help="Caption / theme hint")
    fxp.add_argument("--art", "--theme", dest="art", help="Theme tint: water/blood/steam/ice/lightning/earth/fire/poison/arcane")
    fxp.add_argument("--color", help="R,G,B or R,G,B,A")
    fxp.add_argument("--clone-impact", action="store_true")
    fxp.add_argument("--compare", action="store_true", help="Also write compare.png of motion presets")
    fxp.add_argument("--out", help="Output folder (default Output/Soulash2/_fx_preview/<id>/)")
    fxp.set_defaults(func=cmd_fx_preview)

    pfx = sub.add_parser(
        "produce-fx",
        help="Infer/clone tinted vanilla FX, write vision PNGs, optionally save into the spec",
    )
    spec_args(pfx)
    pfx.add_argument("--name", help="Ability/FX name used to infer motion + theme")
    pfx.add_argument("--preset", choices=sorted(PRESETS))
    pfx.add_argument("--clone", help="Vanilla/workshop animation id instead of inferring")
    pfx.add_argument("--animation-id")
    pfx.add_argument("--art", "--theme", dest="art", help="Theme tint (auto from --name if omitted)")
    pfx.add_argument("--color", help="R,G,B or R,G,B,A override")
    pfx.add_argument("--clone-impact", action="store_true", help="Force cloning on_impact FX")
    pfx.add_argument("--no-clone-impact", action="store_true")
    pfx.add_argument("--on-impact", help="Point every particle on_impact at this id")
    pfx.add_argument("--bind-ability", action="append")
    pfx.add_argument("--missing", action="store_true", help="Produce FX for every ability still on a vanilla numeric animation")
    pfx.add_argument("--compare", action="store_true", help="Always write compare.png (default when inferring)")
    pfx.add_argument("--dry-run", action="store_true", help="Write PNGs + JSON only; do not save the spec")
    pfx.set_defaults(func=cmd_produce_fx)

    uv = sub.add_parser(
        "use-vanilla-particles",
        help="Retarget every bound FX to core_2 particles32 glyphs (rain 114, wave 196, blood 185). No atlas copy.",
    )
    spec_args(uv)
    uv.add_argument("--theme", choices=["water", "blood"], help="Default infers from skill id (sangui/hemo/blood -> blood)")
    uv.set_defaults(func=cmd_use_vanilla_particles)

    ai = sub.add_parser("add-item", help="Create an item entity (skill book, weapon, usable)")
    spec_args(ai)
    ai.add_argument("--from-json")
    ai.add_argument("--item-id")
    ai.add_argument("--name")
    ai.add_argument("--preset", default="generic", choices=["generic", "skill_book", "book", "weapon", "usable", "consumable", "resource"])
    ai.add_argument("--description")
    ai.add_argument("--glyph", type=int)
    ai.add_argument("--value", type=int)
    ai.add_argument("--weight", type=float)
    ai.add_argument("--damage")
    ai.add_argument("--damage-type")
    ai.add_argument("--granted-passive", help="resource.granted_passive (Storm Core). Use with --preset resource")
    ai.add_argument("--loot-exclude", action="store_true", help="Add this item id to loot_exclude.json")
    ai.add_argument("--unlock-level", type=int, help="For skill_book: also grant a recipe milestone")
    ai.set_defaults(func=cmd_add_item)

    ac = sub.add_parser("add-creature", help="Create a summon/enemy creature or terrain tile")
    spec_args(ac)
    ac.add_argument("--from-json")
    ac.add_argument("--creature-id")
    ac.add_argument("--name")
    ac.add_argument("--preset", default="summon", choices=["summon", "ally", "companion", "enemy", "tile"])
    ac.add_argument("--description")
    ac.add_argument("--health", type=int)
    ac.add_argument("--damage")
    ac.add_argument("--damage-type")
    ac.add_argument("--glyph", type=int)
    ac.add_argument("--no-health-regen", action="store_true", help="can_regenerate_health=false (Ghast / monuments)")
    ac.add_argument("--grant-milestone", action="append", help="Entity skills.milestones id (innate passives)")
    ac.add_argument("--summon-ability", help="Set this ability's effects_keys.summon to the new creature")
    ac.set_defaults(func=cmd_add_creature)

    cl = sub.add_parser("clone-entity", help="Copy a vanilla/workshop entity into this spec")
    spec_args(cl)
    cl.add_argument("--source", required=True, help="Vanilla or workshop entity id / filename stem (e.g. 2893 or Golem)")
    cl.add_argument("--new-id")
    cl.add_argument("--name")
    cl.add_argument("--summon-ability")
    cl.set_defaults(func=cmd_clone_entity)

    ca = sub.add_parser("clone-ability", help="Copy a vanilla/workshop ability into this spec (string id, this skill)")
    spec_args(ca)
    ca.add_argument("--source", required=True, help="Vanilla/workshop ability id, name, or filename stem (e.g. 15 or Fireball)")
    ca.add_argument("--new-id")
    ca.add_argument("--ability-id", help=argparse.SUPPRESS)
    ca.add_argument("--name")
    ca.add_argument("--unlock-level", type=int)
    ca.add_argument("--no-milestone", action="store_true")
    ca.add_argument("--clone-animation", action="store_true", help="Also copy the animation JSON into this mod")
    ca.add_argument("--keep-image", action="store_true", help="Keep the source image index (default 0 for placeholder sheets)")
    ca.set_defaults(func=cmd_clone_ability)

    lab = sub.add_parser("list-abilities", help="List spec abilities, or search vanilla/workshop with --search")
    spec_args(lab)
    lab.add_argument("--search", help="Search core_2 + workshop ability names/ids")
    lab.add_argument("--limit", type=int, default=40)
    lab.add_argument("--json", action="store_true")
    lab.set_defaults(func=cmd_list_abilities)

    le2 = sub.add_parser("list-entities", help="List spec entities, or search vanilla/workshop with --search")
    spec_args(le2)
    le2.add_argument("--search", help="Search core_2 + workshop entity names/ids")
    le2.add_argument("--limit", type=int, default=40)
    le2.add_argument("--json", action="store_true")
    le2.set_defaults(func=cmd_list_entities)

    tr = sub.add_parser("tree")
    spec_args(tr)
    tr.add_argument("--json", action="store_true")
    tr.set_defaults(func=cmd_tree)

    fs = sub.add_parser(
        "fill-stats-after-10",
        help="Grant +1 statistic on every level 11–50. Does not move milestones; both can share a level.",
    )
    spec_args(fs)
    fs.add_argument("--through", type=int, default=50, help="Last level to fill (default 50)")
    fs.set_defaults(func=cmd_fill_stats_after_10)

    gi = sub.add_parser(
        "generate-icons",
        help="Pack 128px-cell tilesheets (padded grid). SD paints at 512 then fits. Index 0 is bottom left. Does not run during write.",
    )
    spec_args(gi)
    gi.add_argument(
        "--no-sd",
        action="store_true",
        help="Explicit placeholder rings only (default waits for SD; never auto-falls back to procedural)",
    )
    gi.add_argument("--overwrite", action="store_true", help="Replace existing placeholder PNGs")
    gi.add_argument("--dry-run", action="store_true")
    gi.add_argument("--limit", type=int, help="Cap tiles per sheet (smoke tests)")
    gi.add_argument("--kinds", help="Comma/space list: skills,abilities,amplifiers,passives,stackers")
    gi.add_argument("--names", help="Only regenerate these ability/skill names (keep other 128px cells)")
    gi.add_argument("--thumbnail", action="store_true", help="Also generate the Steam 4:3 thumbnail")
    gi.add_argument("--no-icon", action="store_true", help="Skip mod icon.png")
    gi.add_argument("--steps", type=int, default=24, help="SD steps (default 24)")
    gi.add_argument(
        "--from-existing",
        action="store_true",
        help="Img2img restyle each current-sheet tile into the 128px padded atlas",
    )
    gi.add_argument("--strength", type=float, default=0.58, help="Img2img strength with --from-existing (0-1)")
    gi.set_defaults(func=cmd_generate_icons)

    ij = sub.add_parser(
        "inject-icon",
        help="Pack an external PNG into one atlas cell (fit + bottom-left repack). Use for Cursor or hand-made art.",
    )
    spec_args(ij)
    ij.add_argument("--png", required=True, help="Source PNG path")
    ij.add_argument("--name", help="Display name of ability/amplifier/passive/stacker/skill")
    ij.add_argument("--sheet", help="skills|abilities|amplifiers|passives|stackers (required with --index)")
    ij.add_argument("--index", type=int, help="Explicit tile index (0 = bottom-left)")
    ij.set_defaults(func=cmd_inject_icon)

    se = sub.add_parser("set-effect", help="Set or clear one ability effects / effects_keys field")
    spec_args(se)
    se.add_argument("--ability", required=True)
    se.add_argument("--key", required=True)
    se.add_argument("--value", help="Omit when using --clear")
    se.add_argument("--clear", action="store_true", help="Remove this key (e.g. drop a leftover heal)")
    se.add_argument("--keys", action="store_true", help="Force effects_keys. Default auto-routes summon/construct/stacker/etc.")
    se.set_defaults(func=cmd_set_effect)

    sab = sub.add_parser("set-ability", help="Patch an existing ability without replacing the whole JSON")
    spec_args(sab)
    sab.add_argument("--ability", required=True)
    sab.add_argument("--name")
    sab.add_argument("--description")
    sab.add_argument("--target")
    sab.add_argument("--range", type=int)
    sab.add_argument("--min-range", type=int)
    sab.add_argument("--animation")
    sab.add_argument("--image", type=int)
    sab.add_argument("--stamina", type=int)
    sab.add_argument("--health", type=int)
    sab.add_argument("--cast-time", type=float)
    sab.add_argument("--cooldown", type=float)
    sab.add_argument("--duration", type=float)
    sab.add_argument("--damage")
    sab.add_argument("--damage-type")
    sab.add_argument("--effect", action="append", help="Set effects key=value (repeatable)")
    sab.add_argument("--clear-effect", action="append", help="Remove this effects key (repeatable)")
    sab.set_defaults(func=cmd_set_ability)

    samp = sub.add_parser("set-amplifier", help="Patch an existing amplifier (bonuses, description, cost_stamina). Does not duplicate.")
    spec_args(samp)
    samp.add_argument("--amplifier", required=True)
    samp.add_argument("--name")
    samp.add_argument("--type", choices=["offensive", "defensive", "utility"])
    samp.add_argument("--description")
    samp.add_argument("--bonus", action="append", help="Replace bonuses[] with these (repeatable)")
    samp.add_argument("--append-bonus", action="append", help="Append a bonus without wiping existing")
    samp.add_argument("--clear-bonuses", action="store_true")
    samp.add_argument("--cooldown", type=float)
    samp.add_argument("--cast-time", type=float)
    samp.add_argument("--range", type=int)
    samp.add_argument("--cost-stamina", type=int)
    samp.add_argument("--duration", type=float)
    samp.add_argument("--image", type=int)
    samp.set_defaults(func=cmd_set_amplifier)

    spa = sub.add_parser("set-passive", help="Patch an existing passive without duplicating the id")
    spec_args(spa)
    spa.add_argument("--passive", required=True)
    spa.add_argument("--name")
    spa.add_argument("--effect", action="append", help="Replace effects[] with these (repeatable)")
    spa.add_argument("--append-effect", action="append")
    spa.add_argument("--clear-effects", action="store_true")
    spa.add_argument("--apply-mode", choices=["party_only", "solo_only"])
    spa.add_argument("--image", type=int)
    spa.set_defaults(func=cmd_set_passive)

    sst = sub.add_parser("set-stacker", help="Patch an existing stacker (duration, max-stacks, effects)")
    spec_args(sst)
    sst.add_argument("--stacker", required=True)
    sst.add_argument("--name")
    sst.add_argument("--effect", action="append", help="Replace per-stack effects")
    sst.add_argument("--append-effect", action="append")
    sst.add_argument("--clear-effects", action="store_true")
    sst.add_argument("--max-stacks", type=int)
    sst.add_argument("--duration", type=int)
    sst.add_argument("--description")
    sst.add_argument("--image", type=int)
    sst.add_argument("--apply-caster", action="store_true")
    sst.add_argument("--no-apply-caster", action="store_true")
    sst.set_defaults(func=cmd_set_stacker)

    ram = sub.add_parser("remove-amplifier", help="Delete an amplifier and the milestone that grants it")
    spec_args(ram)
    ram.add_argument("--amplifier", action="append", required=True, help="Amplifier id. Repeat to remove several.")
    ram.set_defaults(func=cmd_remove_amplifier)

    rab = sub.add_parser("remove-ability", help="Delete an ability and the milestone that grants it")
    spec_args(rab)
    rab.add_argument("--ability", action="append", required=True, help="Ability id. Repeat to remove several.")
    rab.set_defaults(func=cmd_remove_ability)

    rp = sub.add_parser("remove-passive", help="Delete a passive and the milestone that grants it")
    spec_args(rp)
    rp.add_argument("--passive", action="append", required=True, help="Passive id. Repeat to remove several.")
    rp.set_defaults(func=cmd_remove_passive)

    lam = sub.add_parser("list-amplifiers", help="List amplifiers in this spec")
    spec_args(lam)
    lam.add_argument("--json", action="store_true")
    lam.set_defaults(func=cmd_list_amplifiers)

    lp = sub.add_parser("list-passives", help="List passives in this spec")
    spec_args(lp)
    lp.add_argument("--json", action="store_true")
    lp.set_defaults(func=cmd_list_passives)

    ls = sub.add_parser("list-stackers", help="List stackers in this spec")
    spec_args(ls)
    ls.add_argument("--json", action="store_true")
    ls.set_defaults(func=cmd_list_stackers)

    ci = sub.add_parser("cycle-images", help="Spread placeholder tilesheet indexes so every icon is not 0")
    spec_args(ci)
    ci.add_argument("--kind", action="append", help="ability, amplifier, passive, stacker (repeatable). Default: first three")
    ci.add_argument("--modulo", type=int, default=8)
    ci.set_defaults(func=cmd_cycle_images)

    ss = sub.add_parser("set-slots")
    spec_args(ss)
    ss.add_argument("--ability", required=True)
    ss.add_argument("--offensive", type=int)
    ss.add_argument("--defensive", type=int)
    ss.add_argument("--utility", type=int)
    ss.set_defaults(func=cmd_set_slots)

    v = sub.add_parser("validate")
    spec_args(v)
    v.add_argument("--vanilla", action="store_true")
    v.set_defaults(func=cmd_validate)

    w = sub.add_parser("write")
    spec_args(w)
    w.add_argument("--output", "-o")
    w.add_argument("--force", action="store_true", help="Write even if validate reported errors")
    w.set_defaults(func=cmd_write)

    ins = sub.add_parser("install")
    spec_args(ins)
    ins.add_argument("--mod")
    ins.add_argument("--yes", action="store_true", help="Required. Copies into the live game data/mods folder.")
    ins.add_argument("--force", action="store_true")
    ins.set_defaults(func=cmd_install)

    d = sub.add_parser("dump-ability", help="Print vanilla/workshop ability JSON (does not retarget). Prefer clone-ability.")
    spec_args(d)
    d.add_argument("ability_id")
    d.set_defaults(func=cmd_dump)

    lr = sub.add_parser("list-races", help="Search vanilla/workshop races, or list races in this spec")
    spec_args(lr)
    lr.add_argument("--search")
    lr.add_argument("--limit", type=int, default=40)
    lr.add_argument("--json", action="store_true")
    lr.set_defaults(func=cmd_list_races)

    cr = sub.add_parser("clone-race", help="Copy a vanilla/workshop race into this spec (partial character.json)")
    spec_args(cr)
    cr.add_argument("--source", required=True, help="Race id or name (0, Human, Vampire, 23, Reptilion)")
    cr.add_argument("--name")
    cr.add_argument("--race-id")
    cr.add_argument("--new-id")
    cr.add_argument("--keep-id", action="store_true", help="Keep vanilla numeric id (overlays that race on merge)")
    cr.add_argument("--overlay", action="store_true", help="With --keep-id: Draken-style patch (passives/abilities only)")
    cr.add_argument("--civilization", action="store_true", help="Keep settlement / base_entities / crests")
    cr.add_argument("--playable", action="store_true")
    cr.add_argument("--passive", action="append", help="Extra racial passive ids")
    cr.add_argument("--ability", action="append", help="Starting abilities (race.abilities, not skill milestones)")
    cr.add_argument("--item", action="append")
    cr.add_argument("--recipe", action="append")
    cr.add_argument("--stat", action="append", help="Override/add statistics, e.g. health_regen_tick=7")
    cr.add_argument("--base-entity", action="append", help="base_entities role=id, e.g. adult=skilltest_stone_warden")
    cr.set_defaults(func=cmd_clone_race)

    ar = sub.add_parser("add-race", help="Author a playable race (character.json races[] merge)")
    spec_args(ar)
    ar.add_argument("--from-json")
    ar.add_argument("--race-id")
    ar.add_argument("--name")
    ar.add_argument("--description")
    ar.add_argument("--unplayable", action="store_true")
    ar.add_argument("--stat", action="append", help="Repeatable strength=2 endurance=1 health_regen_tick=7")
    ar.add_argument("--tag", action="append", help="Character tag ids (9=alive, 2=animal, 4=undead). Repeatable / comma-separated")
    ar.add_argument("--passive", action="append")
    ar.add_argument("--ability", action="append", help="Starting ability ids (patch field on the race)")
    ar.add_argument("--item", action="append")
    ar.add_argument("--recipe", action="append")
    ar.add_argument("--base-entity", action="append", help="adult=entity_id (also child/leader/recruit/rebel/adventurer)")
    ar.add_argument("--orphan-surname")
    ar.add_argument("--adult", type=int)
    ar.add_argument("--child", type=int)
    ar.add_argument("--elder", type=int)
    ar.add_argument("--settle-max", type=int, help="settlement.max")
    ar.add_argument("--no-trading", action="store_true")
    ar.add_argument("--collapse-on-leader-death", action="store_true")
    ar.add_argument("--war-cause", action="append", help="conquest, ride_for_wealth, soul_harvest")
    ar.add_argument("--birth-resource")
    ar.add_argument("--birth-amount", type=int)
    ar.add_argument("--aggression-default", action="store_true")
    ar.add_argument("--single-family", action="store_true")
    ar.add_argument("--no-migration", action="store_true")
    ar.add_argument("--no-settle", action="store_true", help="Playable race without a civ (no settlement block)")
    ar.add_argument("--new-tag", help="Also emit a character tag with this name (like Servile Imp)")
    ar.add_argument("--new-tag-id")
    ar.set_defaults(func=cmd_add_race)

    aca = sub.add_parser("add-control-action", help="Tame-style character.json control_actions (NOT a skill milestone)")
    spec_args(aca)
    aca.add_argument("--clone", default="core_2_tame", help="Template: core_2_tame or core_2_control_undead")
    aca.add_argument("--name")
    aca.add_argument("--action-id")
    aca.add_argument("--tag", action="append", required=True, help="Creature tags this action targets")
    aca.add_argument("--description")
    aca.set_defaults(func=cmd_add_control_action)

    apa = sub.add_parser("add-production-action", help="character.json production_actions (docs §9). Clone vanilla, do not invent Producer entities here")
    spec_args(apa)
    apa.add_argument("--clone", help="Vanilla id or name, e.g. 1 or Mine")
    apa.add_argument("--name")
    apa.add_argument("--action-id")
    apa.add_argument("--description")
    apa.add_argument("--tool", type=int, help="messages.json tool_types id (13 woodcutter, 9 miner)")
    apa.add_argument("--image", type=int, help="Index on the actions tilesheet (write adds a placeholder sheet)")
    apa.add_argument("--sound", help="Sound path, usually a core_2 sfx")
    apa.add_argument("--equipment", action="store_true")
    apa.add_argument("--unlock-level", type=int, help="Also write a production_action milestone")
    apa.set_defaults(func=cmd_add_production_action)

    lpa = sub.add_parser("list-production-actions")
    spec_args(lpa)
    lpa.add_argument("--search", default="")
    lpa.add_argument("--limit", type=int, default=40)
    lpa.add_argument("--json", action="store_true")
    lpa.set_defaults(func=cmd_list_production_actions)

    dpa = sub.add_parser("dump-production-action")
    dpa.add_argument("action_id")
    dpa.set_defaults(func=cmd_dump_production_action)

    ge = sub.add_parser("grant-existing", help="Milestone that grants an existing ability/passive/amplifier/recipe/production_action id")
    spec_args(ge)
    ge.add_argument("--kind", required=True, choices=["ability", "passive", "amplifier", "recipe", "production_action"])
    ge.add_argument("--reward", required=True)
    ge.add_argument("--name")
    ge.add_argument("--unlock-level", type=int, required=True)
    ge.add_argument("--innate", action="store_true")
    ge.set_defaults(func=cmd_grant_existing)

    lt = sub.add_parser("list-tags", help="Search character.json tags (alive=9, undead=4, animal=2)")
    lt.add_argument("--search", default="")
    lt.add_argument("--limit", type=int, default=80)
    lt.add_argument("--json", action="store_true")
    lt.set_defaults(func=cmd_list_tags)

    lca = sub.add_parser("list-control-actions", help="Search vanilla/workshop tame-style control actions")
    spec_args(lca)
    lca.add_argument("--search", default="")
    lca.add_argument("--limit", type=int, default=40)
    lca.add_argument("--json", action="store_true")
    lca.set_defaults(func=cmd_list_control_actions)

    dr = sub.add_parser("dump-race", help="Print vanilla/workshop race JSON (does not retarget). Prefer clone-race.")
    spec_args(dr)
    dr.add_argument("race_id")
    dr.set_defaults(func=cmd_dump_race)

    dca = sub.add_parser("dump-control-action", help="Print vanilla/workshop control_action JSON")
    spec_args(dca)
    dca.add_argument("action_id")
    dca.set_defaults(func=cmd_dump_control_action)

    lb = sub.add_parser("list-buildings", help="Search vanilla/workshop buildings, or list this spec")
    spec_args(lb)
    lb.add_argument("--search", default="")
    lb.add_argument("--limit", type=int, default=40)
    lb.add_argument("--json", action="store_true")
    lb.set_defaults(func=cmd_list_buildings)

    db = sub.add_parser("dump-building", help="Print vanilla/workshop building JSON (does not retarget)")
    spec_args(db)
    db.add_argument("building_id")
    db.set_defaults(func=cmd_dump_building)

    cb = sub.add_parser("clone-building", help="Clone a vanilla/workshop building into this spec")
    spec_args(cb)
    cb.add_argument("--source", required=True, help="Building id, e.g. 389 Collegium Magicae")
    cb.add_argument("--name")
    cb.add_argument("--building-id")
    cb.add_argument("--enable", action="append", help="Skill id this hall trains (enables). Repeatable")
    cb.add_argument("--train", action="store_true", help="Set enables to this spec's skill_id")
    cb.set_defaults(func=cmd_clone_building)

    atb = sub.add_parser(
        "add-training-building",
        help="Player settlement hall that trains this skill (clone Collegium/Dojo/ranch)",
    )
    spec_args(atb)
    atb.add_argument("--template", choices=["magic", "combat", "farm"], default="magic")
    atb.add_argument("--name")
    atb.add_argument("--building-id")
    atb.add_argument("--enable", help="Skill id in enables (default: this spec's skill_id)")
    atb.set_defaults(func=cmd_add_training_building)

    cbm = sub.add_parser("copy-building-map", help="Copy an existing .smap (never invents maps)")
    spec_args(cbm)
    cbm.add_argument("--source", required=True, help="Building id or path to an existing .smap")
    cbm.add_argument("--dest", help="Destination building_maps folder")
    cbm.add_argument("--name", help="Destination filename")
    cbm.set_defaults(func=cmd_copy_building_map)

    fb = sub.add_parser(
        "fix-buildings",
        help="Upgrade 0.9.x player buildings to the 0.10 API (Officers!, Battlemages, Silkworm Farm)",
    )
    spec_args(fb)
    fb.add_argument("mods", nargs="*", help="officers / battlemages / silkworm, steam id, or folder")
    fb.add_argument("--scan", action="store_true", help="Print issues only")
    fb.add_argument("--apply", action="store_true", help="Write a fixed copy under Output/Soulash2/<name>/")
    fb.add_argument("--in-place", action="store_true", help="Also patch the workshop/source folder")
    fb.add_argument("--dest", help="Output folder when fixing a single mod")
    fb.set_defaults(func=cmd_fix_buildings)

    fm = sub.add_parser(
        "fix-mods",
        help="Upgrade outdated workshop mods to the 0.10 JSON contract (icons, amplifiers, passives, buildings)",
    )
    fm.add_argument("mods", nargs="*", help="Steam id, folder, or display name (default: all workshop mods)")
    fm.add_argument("--workshop", action="store_true", help="All workshop mods (default when no ids given)")
    fm.add_argument("--enabled", action="store_true", help="Enabled mods from user_settings.json (skips core_2)")
    fm.add_argument("--scan", action="store_true", help="Print issues only")
    fm.add_argument("--apply", action="store_true", help="Write fixed copies under Output/Soulash2/_fixed/<id>/")
    fm.add_argument("--in-place", action="store_true", help="Also patch the workshop/source folder the game loads")
    fm.add_argument("--dest", help="Output folder when fixing a single mod")
    fm.add_argument("--force", action="store_true", help="Apply even when the scan is clean")
    fm.set_defaults(func=cmd_fix_mods)

    ed = sub.add_parser("editor")
    spec_args(ed)
    ed.add_argument("--host", default="127.0.0.1")
    ed.add_argument("--port", type=int, default=8775)
    ed.add_argument("--no-browser", action="store_true")
    ed.add_argument("--planner", action="store_true", help="Open the skill path planner instead of the authoring studio")
    ed.set_defaults(func=cmd_editor)

    pl = sub.add_parser("planner", help="Open the skill path planner desktop window")
    pl.add_argument("--web", action="store_true", help="Open the old HTML planner in a browser instead")
    pl.add_argument("--host", default="127.0.0.1", help="Only used with --web")
    pl.add_argument("--port", type=int, default=8775, help="Only used with --web")
    pl.add_argument("--no-browser", action="store_true", help="Only used with --web")
    pl.set_defaults(func=cmd_planner, spec=None, id=None, planner=True)

    pd = sub.add_parser("plan-dump", help="Print a potential budget for selected mods/race (JSON)")
    pd.add_argument("--mod", action="append", help="Mod id to include (repeatable). Default: in-game enabled list")
    pd.add_argument("--race", default="0", help="Race id (Human is 0)")
    pd.add_argument("--start", action="append", help="Starting skill id (up to 3)")
    pd.add_argument("--alloc", action="append", help="skill_id=level, e.g. core_2_pyromancy=50")
    pd.add_argument("--stage", choices=["young", "middle", "elder"], default="elder")
    pd.set_defaults(func=cmd_plan_dump)
    return p


def main(argv: Optional[list[str]] = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    # Bare launch (double-click / no subcommand) opens the Studio.
    if not raw:
        raw = ["editor"]
    parser = build_parser()
    args = parser.parse_args(raw)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
