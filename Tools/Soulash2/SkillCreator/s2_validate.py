#!/usr/bin/env python3
"""Validate a skill spec or vanilla/workshop JSON against the mined catalog."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from s2_assets import animation_known
from s2_buildings import is_player_building
from s2_entities import ENTITY_REF_KEYS
from s2_paths import core2_dir
from s2_races import PLAYABLE_MIN, grant_sources
from s2_schema import load_effects, load_enums, observed_count_warning
from s2_skill_spec import has_author_prefix, is_rebalance_mastery, prefixed_skill_id

KNOWN_ABILITY_TOP = {
    "id",
    "name",
    "description",
    "image",
    "animation",
    "cast_time",
    "cooldown",
    "duration",
    "cost",
    "range",
    "min_range",
    "target",
    "effects",
    "effects_keys",
    "effect_keys",
    "skill",
    "slots",
    "requirements",
    "level",
    "profession",
    "upgrades",
}

KNOWN_AMP_TOP = {
    "id",
    "name",
    "type",
    "image",
    "bonuses",
    "description",
    "cooldown",
    "cast_time",
    "duration",
    "range",
    "range_melee",
    "cost_stamina",
    "cost_health",
}

REWARD_KINDS = {"ability", "passive", "amplifier", "recipe", "production_action", "action", "control_action"}

KNOWN_PASSIVE_TOP = {
    "id",
    "name",
    "image",
    "effects",
    "apply_mode",
    "restrict_tags",
    "restrict_tags_enemy",
    "restrict_weapon_type",
    "description",
    "disable_consumer",
}

APPLY_MODES = {"party_only", "solo_only"}

# Live encoding mistakes from rebuilding Hydromancy / Hemohydraulics through this tool.
AMP_BONUS_SHOULD_BE_FIELD = {
    "stamina_cost": "top-level cost_stamina (not a bonuses[] row)",
    "range": "top-level range",
    "cooldown": "top-level cooldown",
    "cast_time": "top-level cast_time",
    "duration": "top-level duration",
}


def _non_int_number(val: Any) -> bool:
    if isinstance(val, bool) or val is None:
        return False
    if isinstance(val, float):
        return not val.is_integer()
    return False


def _encoding_issues(spec: Dict[str, Any], issues: List[Issue]) -> None:
    for ab in spec.get("abilities") or []:
        fx = ab.get("effects")
        if not isinstance(fx, dict):
            continue
        aid = ab.get("id") or ""
        kb = fx.get("knockback")
        if _non_int_number(kb) or (isinstance(kb, (int, float)) and not isinstance(kb, bool) and 0 < float(kb) < 1):
            issues.append(
                Issue(
                    "warn",
                    f"knockback {kb} should be integer tiles (0.25 is ignored in practice)",
                    aid,
                )
            )
        sc = fx.get("summon_count")
        if isinstance(sc, (int, float)) and not isinstance(sc, bool) and sc > 24:
            issues.append(
                Issue(
                    "warn",
                    f"summon_count {sc} is unusually high (100 fog tiles over-covered; typical 1–16, ice slivers used 24)",
                    aid,
                )
            )
        tgt = str(ab.get("target") or "")
        if tgt in ("aoe_tile", "aoe_target", "aoe_self") and "aoe_range" in fx and "aoe_shape" not in fx:
            issues.append(
                Issue(
                    "error",
                    "AoE with aoe_range needs aoe_shape (vanilla Meteor/Fireball use 1). Missing it makes the cast do nothing.",
                    aid,
                )
            )
        if "heal" in fx and "damage" in fx:
            issues.append(
                Issue(
                    "warn",
                    "ability has both damage and flat heal; Warlock-style lifesteal is damage_as_life",
                    aid,
                )
            )
        if "stamina_cost" in fx:
            issues.append(
                Issue(
                    "warn",
                    "stamina_cost on an ability effect is the wrong encoding; amplifiers use top-level cost_stamina",
                    aid,
                )
            )

    for amp in spec.get("amplifiers") or []:
        aid = amp.get("id") or ""
        for bonus in amp.get("bonuses") or []:
            eid = bonus.get("effect")
            val = bonus.get("value")
            hint = AMP_BONUS_SHOULD_BE_FIELD.get(str(eid or ""))
            if hint:
                issues.append(Issue("warn", f"amplifier bonus {eid} should be {hint}", aid))
            if eid == "trade_places":
                issues.append(
                    Issue(
                        "warn",
                        "trade_places is ability-only; on amplifiers use chain or pull_target",
                        aid,
                    )
                )
            if eid == "bonus_damage":
                issues.append(
                    Issue(
                        "warn",
                        "bonus_damage on amplifiers is the wrong encoding; use damage [n,n] or skill_level_damage",
                        aid,
                    )
                )
            if eid == "heal":
                issues.append(
                    Issue(
                        "warn",
                        "flat heal on an amplifier; prefer damage_as_life (Warlock Lifedrinker is 0.04)",
                        aid,
                    )
                )
            if eid == "knockback" and (
                _non_int_number(val) or (isinstance(val, (int, float)) and not isinstance(val, bool) and 0 < float(val) < 1)
            ):
                issues.append(Issue("warn", f"knockback {val} should be integer tiles", aid))
            if eid == "move_speed":
                issues.append(
                    Issue(
                        "warn",
                        "move_speed is a passive key; on amplifiers use movement_speed",
                        aid,
                    )
                )

    for p in spec.get("passives") or []:
        for fx in p.get("effects") or []:
            if fx.get("effect") == "movement_speed":
                issues.append(
                    Issue(
                        "warn",
                        "passive movement_speed does not apply; use move_speed",
                        p.get("id") or "",
                    )
                )
            if fx.get("effect") in ("heal_on_damage_type", "damage_type_reduction", "damage_type") and isinstance(
                fx.get("value"), bool
            ):
                issues.append(
                    Issue(
                        "error",
                        f"{fx.get('effect')} value must be the string \"true\" (damage type), not JSON boolean true",
                        p.get("id") or "",
                    )
                )

KNOWN_COST_KEYS = {"health", "stamina", "item", "item_type", "ammo"}
KNOWN_REQ_KEYS = {"one_of", "always"}
KNOWN_SKILL_TOP = {
    "id",
    "name",
    "image",
    "description",
    "combat_skill",
    "exp_sources",
    "starting_gear",
    "stat_points",
    "difficulty",
    "level_start",
}
KNOWN_MOD_TOP = {
    "author",
    "description",
    "game_required",
    "icon",
    "mods_required",
    "name",
    "version",
    "thumbnail",
    "steam_publish_id",
    "disable_portraits",
}


class Issue:
    def __init__(self, level: str, message: str, path: str = "") -> None:
        self.level = level
        self.message = message
        self.path = path

    def to_dict(self) -> Dict[str, str]:
        return {"level": self.level, "message": self.message, "path": self.path}


def _index_effects() -> Dict[Tuple[str, str], Dict[str, Any]]:
    out = {}
    for e in load_effects():
        out[(e["kind"], e["id"])] = e
    return out


def _prereq_issues(spec: Dict[str, Any], issues: List[Issue]) -> None:
    by_id = {str(m.get("id")): m for m in spec.get("milestones") or []}

    def level(m: Dict[str, Any]) -> int:
        if m.get("innate"):
            return 0
        try:
            return int((m.get("requirements") or {}).get("skill") or 0)
        except (TypeError, ValueError):
            return 0

    graph: Dict[str, List[str]] = {}
    for mid, m in by_id.items():
        pre = (m.get("requirements") or {}).get("milestones") or []
        graph[mid] = [str(p) for p in pre if str(p) in by_id]
        for p in pre:
            p = str(p)
            if p == mid:
                issues.append(Issue("error", "Milestone lists itself as a prerequisite", mid))
            elif p not in by_id:
                issues.append(Issue("error", f"Unknown prerequisite milestone {p}", mid))
            elif level(by_id[p]) > level(m):
                issues.append(
                    Issue("warn", f"Prerequisite {p} unlocks at level {level(by_id[p])}, after this milestone ({level(m)})", mid)
                )
    state: Dict[str, int] = {}
    for start in graph:
        if state.get(start):
            continue
        stack = [(start, iter(graph[start]))]
        state[start] = 1
        while stack:
            node, it = stack[-1]
            nxt = next(it, None)
            if nxt is None:
                state[node] = 2
                stack.pop()
            elif state.get(nxt) == 1:
                if nxt != node:
                    issues.append(Issue("error", f"Prerequisite cycle through {nxt}", node))
            elif not state.get(nxt):
                state[nxt] = 1
                stack.append((nxt, iter(graph[nxt])))


def validate_spec(spec: Dict[str, Any]) -> List[Issue]:
    issues: List[Issue] = []
    catalog = _index_effects()
    enums = load_enums()
    targets = set(enums.get("target") or [])
    amp_types = set(enums.get("amplifier_type") or ["offensive", "defensive", "utility"])
    skill_id = spec.get("skill_id")
    if not skill_id:
        issues.append(Issue("error", "Missing skill_id"))
        return issues
    author = (spec.get("mod") or {}).get("author")
    if not has_author_prefix(str(skill_id), author=author):
        want = prefixed_skill_id(str(skill_id), author=author)
        issues.append(
            Issue(
                "warn",
                f"skill_id {skill_id} has no author prefix; vanilla may add the same school later. Use {want} (rename-id --to {want})",
            )
        )
    if (spec.get("mod") or {}).get("icon") in ("S.png", "S2.png", ""):
        issues.append(Issue("warn", "mod.icon should be icon.png (write generates a 32x32 placeholder)"))
    mod = spec.get("mod") or {}
    for extra in mod:
        if extra not in KNOWN_MOD_TOP:
            issues.append(Issue("warn", f"Unknown mod.json field {extra}"))
    if mod.get("disable_portraits"):
        issues.append(
            Issue(
                "warn",
                "disable_portraits is global and overrides portraits in other mods (docs §2). Omit it unless you mean that",
            )
        )
    skill = spec.get("skill") or {}
    for extra in skill:
        if extra not in KNOWN_SKILL_TOP:
            issues.append(Issue("warn", f"Unknown skills.json field {extra}"))
    exp_ids = set(enums.get("exp_source") or [])
    for src in skill.get("exp_sources") or []:
        if not isinstance(src, dict):
            issues.append(Issue("error", "exp_sources entries must be objects"))
            continue
        sid = src.get("id")
        if sid and exp_ids and sid not in exp_ids:
            issues.append(Issue("warn", f"Unknown exp_source id {sid} (docs list is incomplete; walk/carve/production are valid)"))
        if sid == "production" and not src.get("production_action"):
            issues.append(Issue("warn", "exp_source production usually needs production_action (vanilla Agriculture uses it)"))
    ent_ids = {str(e.get("id")) for e in spec.get("entities") or [] if e.get("id")}
    for i, choice in enumerate(skill.get("starting_gear") or []):
        if not isinstance(choice, dict) or "first" not in choice:
            issues.append(Issue("error", "starting_gear choice needs first:{id, amount}", f"starting_gear[{i}]"))
            continue
        for side in ("first", "second"):
            item = choice.get(side)
            if not item:
                continue
            if not isinstance(item, dict) or not item.get("id"):
                issues.append(Issue("error", f"starting_gear {side} needs id and amount", f"starting_gear[{i}]"))
                continue
            iid = str(item["id"])
            if iid.isdigit() or iid.startswith("core_2_") or iid in ent_ids:
                continue
            issues.append(
                Issue(
                    "warn",
                    f"starting_gear {side} id {iid} is not in this spec and is not a vanilla numeric / core_2_ id",
                    f"starting_gear[{i}]",
                )
            )
    stats = [int(x) for x in (skill.get("stat_points") or [])]
    combat = skill.get("combat_skill") is not False
    if combat:
        early_stats = [n for n in stats if n < 11]
        if early_stats:
            shown = ", ".join(str(n) for n in early_stats[:8])
            extra = "…" if len(early_stats) > 8 else ""
            issues.append(
                Issue(
                    "error",
                    f"Skill Stat Rebalance: no +1 statistic on 1–10 (found {shown}{extra})",
                    "stat_points",
                )
            )
        missing_after_10 = [n for n in range(11, 51) if n not in stats]
        if missing_after_10:
            shown = ", ".join(str(n) for n in missing_after_10[:10])
            extra = "…" if len(missing_after_10) > 10 else ""
            issues.append(
                Issue(
                    "warn",
                    f"Combat skill is missing +1 statistic on levels {shown}{extra}. "
                    "Milestones can share those levels; run fill-stats-after-10.",
                    "stat_points",
                )
            )
    ab_ids = {a.get("id") for a in spec.get("abilities") or []}
    pa_ids = {p.get("id") for p in spec.get("passives") or []}
    am_ids = {a.get("id") for a in spec.get("amplifiers") or []}
    mile_ids = {m.get("id") for m in spec.get("milestones") or []}
    if len(ab_ids) != len(spec.get("abilities") or []):
        issues.append(Issue("error", "Duplicate ability ids"))
    if len(pa_ids) != len(spec.get("passives") or []):
        issues.append(Issue("error", "Duplicate passive ids"))
    if len(am_ids) != len(spec.get("amplifiers") or []):
        issues.append(Issue("error", "Duplicate amplifier ids"))
    if len(mile_ids) != len(spec.get("milestones") or []):
        issues.append(Issue("error", "Duplicate milestone ids"))
    st_ids = {s.get("id") for s in spec.get("stackers") or []}
    if len(st_ids) != len(spec.get("stackers") or []):
        issues.append(Issue("error", "Duplicate stacker ids"))
    an_ids = {a.get("id") for a in spec.get("animations") or []}
    if len(an_ids) != len(spec.get("animations") or []):
        issues.append(Issue("error", "Duplicate animation ids"))

    from s2_particle_art import PARTICLE_SHEET, VANILLA_TILES

    has_particle_sheet = any(
        s.get("name") == PARTICLE_SHEET
        for s in ((spec.get("assets") or {}).get("graphics") or {}).get("tilesheets") or []
    )
    for anim in spec.get("animations") or []:
        for part in anim.get("particles") or []:
            if not isinstance(part, dict):
                continue
            try:
                tid = int(part.get("tile_id"))
            except (TypeError, ValueError):
                continue
            if tid >= VANILLA_TILES and not has_particle_sheet:
                issues.append(
                    Issue(
                        "error",
                        f"Animation {anim.get('id')} tile_id {tid} needs a vanilla glyph (use-vanilla-particles); do not overlay particles32",
                        anim.get("id") or "",
                    )
                )
                break
    if has_particle_sheet:
        issues.append(
            Issue(
                "warn",
                "assets.json particles32 overlay fights other skills; clone vanilla tile_ids (use-vanilla-particles) instead",
            )
        )

    slot_colors = {"offensive": 0, "defensive": 0, "utility": 0}
    for ab in spec.get("abilities") or []:
        aid = str(ab.get("id") or "")
        if aid.isdigit():
            issues.append(
                Issue(
                    "warn",
                    f"Ability id {aid} is numeric; custom skills should use string ids like {skill_id}_fireball (clone-ability retargets this)",
                    aid,
                )
            )
        if ab.get("skill") and ab.get("skill") != skill_id:
            issues.append(Issue("error", f"Ability skill {ab.get('skill')} != {skill_id}", ab.get("id") or ""))
        tgt = ab.get("target")
        if tgt and targets and tgt not in targets:
            issues.append(Issue("warn", f"Unknown target {tgt}", ab.get("id") or ""))
        cost = ab.get("cost")
        if isinstance(cost, dict):
            for extra in cost:
                if extra not in KNOWN_COST_KEYS:
                    issues.append(Issue("warn", f"Unknown ability cost field {extra}", ab.get("id") or ""))
        req = ab.get("requirements")
        if isinstance(req, dict):
            for extra in req:
                if extra not in KNOWN_REQ_KEYS:
                    issues.append(
                        Issue(
                            "warn",
                            f"Unknown ability requirements key {extra} (vanilla uses one_of / always; docs say require_one_of / require_all)",
                            ab.get("id") or "",
                        )
                    )
        anim = str(ab.get("animation") or "")
        if anim and anim not in an_ids and not anim.isdigit() and not anim.startswith("core_2_"):
            if not animation_known(anim):
                issues.append(
                    Issue(
                        "warn",
                        f"Unknown animation {anim} — clone with add-animation --clone or use a vanilla id like 0 / 3 / 65",
                        ab.get("id") or "",
                    )
                )
        effects = ab.get("effects")
        if isinstance(effects, dict):
            for k in effects:
                row = catalog.get(("ability", k)) or catalog.get(("amplifier", k))
                if ("ability", k) not in catalog and ("amplifier", k) not in catalog:
                    issues.append(Issue("warn", f"Unknown ability effect {k}", ab.get("id") or ""))
                elif (row or {}).get("confidence") == "unconfirmed":
                    issues.append(Issue("warn", f"Unconfirmed exe-only effect {k}; may not work in JSON", ab.get("id") or ""))
        keys = ab.get("effects_keys") or ab.get("effect_keys")
        if isinstance(keys, dict):
            for k in keys:
                row = catalog.get(("ability_key", k))
                if not row:
                    issues.append(Issue("warn", f"Unknown effects_keys {k}", ab.get("id") or ""))
                elif row.get("confidence") == "unconfirmed":
                    issues.append(Issue("warn", f"Unconfirmed exe-only effects_keys {k}; may not work in JSON", ab.get("id") or ""))
        n_fx = (len(effects) if isinstance(effects, dict) else 0) + (len(keys) if isinstance(keys, dict) else 0)
        note = observed_count_warning("ability_effects", n_fx)
        if note:
            issues.append(Issue("warn", note, ab.get("id") or ""))
        slot_total = 0
        for color, n in (ab.get("slots") or {}).items():
            if color in slot_colors:
                slot_colors[color] += int(n or 0)
                slot_total += int(n or 0)
        note = observed_count_warning("ability_slots_total", slot_total)
        if note:
            issues.append(Issue("warn", note, ab.get("id") or ""))

    amp_colors = {"offensive": 0, "defensive": 0, "utility": 0}
    for amp in spec.get("amplifiers") or []:
        t = amp.get("type")
        if t not in amp_types:
            issues.append(Issue("error", f"Amplifier type must be offensive/defensive/utility, got {t}", amp.get("id") or ""))
        else:
            amp_colors[t] += 1
        bonuses = amp.get("bonuses") or []
        n_bonus = len(bonuses)
        note = observed_count_warning("amplifier_bonuses", n_bonus)
        if note:
            issues.append(Issue("warn", note, amp.get("id") or ""))
        for fx in bonuses:
            eid = fx.get("effect")
            row = catalog.get(("amplifier", eid)) or catalog.get(("ability", eid)) if eid else None
            if eid and ("amplifier", eid) not in catalog and ("ability", eid) not in catalog:
                issues.append(Issue("warn", f"Unknown amplifier bonus {eid}", amp.get("id") or ""))
            elif (row or {}).get("confidence") == "unconfirmed":
                issues.append(Issue("warn", f"Unconfirmed exe-only amplifier bonus {eid}; may not work in JSON", amp.get("id") or ""))

    for color, n in amp_colors.items():
        if n and not slot_colors.get(color):
            issues.append(Issue("warn", f"Skill has {n} {color} amplifier(s) but no ability with {color} slots"))

    for p in spec.get("passives") or []:
        fx_list = p.get("effects") or []
        n_pass = len(fx_list)
        note = observed_count_warning("passive_effects", n_pass)
        if note:
            issues.append(Issue("warn", note, p.get("id") or ""))
        if p.get("description"):
            issues.append(
                Issue(
                    "warn",
                    "Passive description is ignored by the engine; tooltip is generated from effects only",
                    p.get("id") or "",
                )
            )
        if "only_party" in p:
            issues.append(
                Issue(
                    "warn",
                    "only_party is obsolete. Use apply_mode: party_only or solo_only",
                    p.get("id") or "",
                )
            )
        mode = p.get("apply_mode")
        if mode and mode not in APPLY_MODES:
            issues.append(
                Issue(
                    "error",
                    f"apply_mode must be party_only or solo_only, got {mode}",
                    p.get("id") or "",
                )
            )
        for extra in p:
            if extra not in KNOWN_PASSIVE_TOP and extra != "only_party":
                issues.append(Issue("warn", f"Unknown passive field {extra}", p.get("id") or ""))
        for fx in fx_list:
            eid = fx.get("effect")
            row = catalog.get(("passive", eid)) if eid else None
            if eid and not row:
                issues.append(Issue("warn", f"Unknown passive effect {eid}", p.get("id") or ""))
            elif (row or {}).get("confidence") == "unconfirmed":
                issues.append(Issue("warn", f"Unconfirmed exe-only passive {eid}; may not work in JSON", p.get("id") or ""))

    ent_ids = {e.get("id") for e in spec.get("entities") or [] if e.get("id")}
    if len(ent_ids) != len(spec.get("entities") or []):
        issues.append(Issue("error", "Duplicate entity ids"))
    ab_ids = {str(a.get("id")) for a in spec.get("abilities") or [] if a.get("id")}
    for ab in spec.get("abilities") or []:
        keys = ab.get("effects_keys") or ab.get("effect_keys") or {}
        if not isinstance(keys, dict):
            continue
        for k in ENTITY_REF_KEYS:
            ref = keys.get(k)
            if not ref:
                continue
            rid = str(ref)
            if rid.isdigit():
                continue
            if k == "aura" and rid in ab_ids:
                continue
            if rid not in ent_ids:
                issues.append(
                    Issue(
                        "warn",
                        f"Ability {k} references entity {rid} which is not in this spec — add it with add-item/add-creature or clone-entity",
                        ab.get("id") or "",
                    )
                )

    used_stackers: set = set()
    for ab in spec.get("abilities") or []:
        keys = ab.get("effects_keys") or ab.get("effect_keys") or {}
        if not isinstance(keys, dict):
            continue
        sid = keys.get("stacker")
        if not sid:
            continue
        rid = str(sid)
        used_stackers.add(rid)
        if rid not in st_ids and not rid.startswith("core_2_"):
            issues.append(
                Issue(
                    "warn",
                    f"Ability stacker {rid} is not in this spec — add-stacker or use a core_2_ id",
                    ab.get("id") or "",
                )
            )
    for amp in spec.get("amplifiers") or []:
        for fx in amp.get("bonuses") or []:
            if fx.get("effect") != "stacker" or not fx.get("value"):
                continue
            rid = str(fx.get("value"))
            used_stackers.add(rid)
            if rid not in st_ids and not rid.startswith("core_2_"):
                issues.append(
                    Issue(
                        "warn",
                        f"Amplifier stacker {rid} is not in this spec — add-stacker or use a core_2_ id",
                        amp.get("id") or "",
                    )
                )

    for s in spec.get("stackers") or []:
        fx_list = s.get("effects") or []
        note = observed_count_warning("stacker_effects", len(fx_list))
        if note:
            issues.append(Issue("warn", note, s.get("id") or ""))
        for fx in fx_list:
            eid = fx.get("effect")
            if not eid:
                continue
            row = (
                catalog.get(("stacker", eid))
                or catalog.get(("ability", eid))
                or catalog.get(("passive", eid))
                or catalog.get(("amplifier", eid))
            )
            if not row:
                issues.append(Issue("warn", f"Unknown stacker effect {eid}", s.get("id") or ""))
            elif row.get("confidence") == "unconfirmed":
                issues.append(Issue("warn", f"Unconfirmed exe-only stacker effect {eid}; may not work in JSON", s.get("id") or ""))
        cast = s.get("on_max_stacks_cast")
        if cast and str(cast) not in ab_ids and not str(cast).startswith("core_2_"):
            issues.append(
                Issue(
                    "warn",
                    f"on_max_stacks_cast {cast} is not an ability in this spec",
                    s.get("id") or "",
                )
            )
        if s.get("id") not in used_stackers:
            issues.append(
                Issue(
                    "warn",
                    "Stacker is never referenced by an ability effects_keys.stacker or amplifier bonus",
                    s.get("id") or "",
                )
            )

    _encoding_issues(spec, issues)

    unlocked = {"ability": set(), "passive": set(), "amplifier": set()}
    for m in spec.get("milestones") or []:
        if m.get("skill_id") != skill_id:
            issues.append(Issue("error", f"Milestone skill_id {m.get('skill_id')} != {skill_id}", m.get("id") or ""))
        req = m.get("requirements") or {}
        innate = bool(m.get("innate"))
        if "skill" not in req and not innate:
            issues.append(Issue("error", "Milestone missing requirements.skill", m.get("id") or ""))
        for reward in m.get("rewards") or []:
            if not isinstance(reward, dict) or not reward:
                continue
            kind, rid = next(iter(reward.items()))
            if kind == "control_action":
                issues.append(
                    Issue(
                        "error",
                        "control_action does not work as a skill milestone reward. Put it on character.json (add-control-action)",
                        m.get("id") or "",
                    )
                )
            if kind not in REWARD_KINDS:
                issues.append(Issue("warn", f"Unknown reward kind {kind}", m.get("id") or ""))
            if kind in unlocked:
                unlocked[kind].add(rid)
            if kind == "ability" and rid not in ab_ids:
                issues.append(Issue("error", f"Milestone rewards missing ability {rid}", m.get("id") or ""))
            if kind == "passive" and rid not in pa_ids:
                issues.append(Issue("error", f"Milestone rewards missing passive {rid}", m.get("id") or ""))
            if kind == "passive" and not innate:
                lv = req.get("skill")
                try:
                    lv_n = int(lv)
                except (TypeError, ValueError):
                    lv_n = None
                if lv_n is not None and lv_n < 11:
                    issues.append(
                        Issue(
                            "error",
                            f"Passive {rid} unlocks at skill {lv_n}; levels 1–10 are free (Skill Stat Rebalance). Move to 11+.",
                            m.get("id") or "",
                        )
                    )
            if kind == "amplifier" and rid not in am_ids:
                issues.append(Issue("warn", f"Amplifier {rid} not in this spec (ok if granting an existing core_2 id)", m.get("id") or ""))
            if kind == "production_action":
                prod_ids = {str(p.get("id")) for p in spec.get("production_actions") or [] if p.get("id")}
                srid = str(rid)
                if srid not in prod_ids and not srid.isdigit() and not srid.startswith("core_2_"):
                    issues.append(
                        Issue(
                            "warn",
                            f"production_action {rid} is not in this spec — clone with add-production-action or grant a vanilla numeric id",
                            m.get("id") or "",
                        )
                    )

    _prereq_issues(spec, issues)

    if combat:
        pas_map = {p.get("id"): p for p in spec.get("passives") or []}
        mastery_ok = False
        for m in spec.get("milestones") or []:
            if m.get("innate"):
                continue
            if (m.get("requirements") or {}).get("skill") != 30:
                continue
            for reward in m.get("rewards") or []:
                if not isinstance(reward, dict):
                    continue
                pid = reward.get("passive")
                row = pas_map.get(pid)
                if row and is_rebalance_mastery(row):
                    mastery_ok = True
        if not mastery_ok:
            issues.append(
                Issue(
                    "error",
                    "Combat skill needs a unique level-30 mastery: +10% strength/dexterity/endurance/intelligence/willpower (add-combat-mastery).",
                    "mastery",
                )
            )

    race_abs, race_pas = grant_sources(spec)
    aura_ids = set()
    for ab in spec.get("abilities") or []:
        keys = ab.get("effects_keys") if isinstance(ab.get("effects_keys"), dict) else {}
        aura = keys.get("aura")
        if aura:
            aura_ids.add(str(aura))
    entity_granted = set()
    for ent in spec.get("entities") or []:
        eid = str(ent.get("id") or "")
        for aid in ent.get("ability_user") or []:
            sid = str(aid)
            entity_granted.add(sid)
            if sid not in ab_ids and not sid.isdigit() and not sid.startswith("core_2_"):
                issues.append(
                    Issue(
                        "warn",
                        f"Entity ability_user {sid} is not in this spec — add-ability --no-milestone for transform/summon kits",
                        eid,
                    )
                )
    for ab in spec.get("abilities") or []:
        aid = ab.get("id")
        if aid not in unlocked["ability"] and str(aid) not in race_abs:
            if str(aid) in aura_ids or str(aid) in entity_granted:
                continue
            issues.append(Issue("warn", f"Ability never unlocked by a milestone", ab.get("id") or ""))
    for p in spec.get("passives") or []:
        if p.get("id") not in unlocked["passive"] and str(p.get("id")) not in race_pas:
            issues.append(Issue("warn", f"Passive never unlocked by a milestone", p.get("id") or ""))
    for amp in spec.get("amplifiers") or []:
        if amp.get("id") not in unlocked["amplifier"]:
            issues.append(Issue("warn", f"Amplifier never unlocked by a milestone", amp.get("id") or ""))

    race_ids = [r.get("id") for r in spec.get("races") or [] if r.get("id")]
    if len(set(race_ids)) != len(race_ids):
        issues.append(Issue("error", "Duplicate race ids"))
    action_ids = [a.get("id") for a in spec.get("control_actions") or [] if a.get("id")]
    if len(set(action_ids)) != len(action_ids):
        issues.append(Issue("error", "Duplicate control_action ids"))
    prod_ids = [p.get("id") for p in spec.get("production_actions") or [] if p.get("id")]
    if len(set(prod_ids)) != len(prod_ids):
        issues.append(Issue("error", "Duplicate production_action ids"))
    tool_ids = {t.get("id") for t in (enums.get("tool_types") or []) if isinstance(t, dict)}
    for act in spec.get("production_actions") or []:
        pid = str(act.get("id") or "")
        if pid.isdigit():
            issues.append(
                Issue(
                    "warn",
                    f"Production action id {pid} is numeric; custom ids should use a mod prefix (docs §9)",
                    pid,
                )
            )
        tool = act.get("required_tool")
        if tool is not None and tool_ids and tool not in tool_ids:
            issues.append(Issue("warn", f"required_tool {tool} is not a messages.json tool_types id", pid))
        for key in ("id", "name", "description", "required_tool", "image"):
            if key not in act:
                issues.append(Issue("warn", f"Production action missing {key} (docs §9)", pid))
    for race in spec.get("races") or []:
        rid = race.get("id") or ""
        if race.get("playable"):
            for key in PLAYABLE_MIN:
                if key not in race:
                    issues.append(Issue("warn", f"Playable race missing {key} (docs §7.1)", str(rid)))
        names = race.get("names")
        if race.get("playable") and (not isinstance(names, dict) or not names.get("male") or not names.get("female")):
            issues.append(Issue("warn", "Playable race names need male and female txt paths", str(rid)))
        for aid in race.get("abilities") or []:
            sid = str(aid)
            if sid.isdigit() or sid.startswith("core_2_"):
                continue
            if sid not in ab_ids:
                issues.append(
                    Issue(
                        "warn",
                        f"Race starting ability {sid} is not in this spec — add-ability / clone-ability first",
                        str(rid),
                    )
                )
        for pid in race.get("passives") or []:
            sid = str(pid)
            if sid.startswith("core_2_"):
                continue
            if sid not in pa_ids:
                issues.append(
                    Issue(
                        "warn",
                        f"Race passive {sid} is not in this spec — add-passive first (or use a core_2_ id)",
                        str(rid),
                    )
                )
    skill_id = str(spec.get("skill_id") or "")
    spec_entity_ids = {str(e.get("id")) for e in spec.get("entities") or [] if e.get("id")}
    for building in spec.get("buildings") or []:
        bid = str(building.get("id") or "")
        if not bid:
            issues.append(Issue("error", "Building missing id"))
            continue
        if is_player_building(building):
            if "occupation_image" not in building:
                issues.append(Issue("warn", "Player building missing occupation_image (0.10 buildings list)", bid))
            if "produces" not in building:
                issues.append(Issue("warn", "Player building missing produces (use [] if none)", bid))
            opr = building.get("occupation_per_race") or {}
            if isinstance(opr, dict) and "6" not in opr:
                issues.append(Issue("warn", "Player building occupation_per_race missing vampire race 6", bid))
        for sid in building.get("enables") or []:
            sid = str(sid)
            if sid == skill_id or sid.startswith("core_2_"):
                continue
            issues.append(
                Issue(
                    "warn",
                    f"Building enables {sid} which is not this spec's skill_id ({skill_id})",
                    bid,
                )
            )
        occ = building.get("occupation")
        if occ and str(occ) not in spec_entity_ids and not str(occ).startswith("core_2_") and not str(occ).isdigit():
            issues.append(
                Issue(
                    "warn",
                    f"Building occupation {occ} is not in this spec's entities (ok if it lives in another mod)",
                    bid,
                )
            )
    return issues


def _load(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        return {"__error__": str(exc)}


def validate_vanilla() -> List[Issue]:
    """Accept every core_2 ability/passive/amplifier; fail if unknown keys appear after mine."""
    issues: List[Issue] = []
    catalog = _index_effects()
    core = core2_dir()
    abdir = core / "abilities"
    for path in sorted(abdir.glob("*.json")):
        data = _load(path)
        if not isinstance(data, dict) or "__error__" in data:
            issues.append(Issue("error", f"Unreadable {path.name}", str(path)))
            continue
        effects = data.get("effects")
        if isinstance(effects, dict):
            for k in effects:
                if ("ability", k) not in catalog:
                    issues.append(Issue("error", f"Uncatalogued ability effect {k}", path.name))
        keys = data.get("effects_keys") or data.get("effect_keys")
        if isinstance(keys, dict):
            for k in keys:
                if ("ability_key", k) not in catalog:
                    issues.append(Issue("error", f"Uncatalogued effects_keys {k}", path.name))
    passives = _load(core / "passives.json")
    if isinstance(passives, list):
        for item in passives:
            for fx in item.get("effects") or []:
                eid = fx.get("effect")
                if eid and ("passive", eid) not in catalog:
                    issues.append(Issue("error", f"Uncatalogued passive effect {eid}", item.get("id") or ""))
    amps = _load(core / "ability_amplifiers.json")
    if isinstance(amps, list):
        for item in amps:
            for fx in item.get("bonuses") or []:
                eid = fx.get("effect")
                if eid and ("amplifier", eid) not in catalog and ("ability", eid) not in catalog:
                    issues.append(Issue("error", f"Uncatalogued amplifier bonus {eid}", item.get("id") or ""))
    return issues


def format_issues(issues: List[Issue]) -> str:
    if not issues:
        return "OK"
    lines = []
    for i in issues:
        loc = f" [{i.path}]" if i.path else ""
        lines.append(f"{i.level.upper()}: {i.message}{loc}")
    return "\n".join(lines)
