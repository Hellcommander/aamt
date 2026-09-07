#!/usr/bin/env python3
"""Soulash 2 animation studio.

Engine animations are JSON in ``animations/``. Particle ``tile_id`` is always
the ``particles32`` atlas (no per-particle tilesheet field in the exe). Do not
copy vanilla ``particles.png`` into a skill or append extra rows — extra skills
will fight over that name. Clone core_2 motion (rain drop ``114``, water wave
``196``, blood drop ``185``, …) and tint. ``use-vanilla-particles`` does that
for every bound FX.
"""

from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union

from s2_assets import clone_animation, _iter_animation_files
from s2_schema import slug_name

# Motion templates. Glyphs stay vanilla; we clone the *choreography*.
PRESETS: Dict[str, Dict[str, str]] = {
    "bolt": {"clone": "3", "kind": "projectile", "blurb": "Fireball projectile (impact 4)", "look": "streaking orb/bolt that flies then explodes"},
    "nova": {"clone": "61", "kind": "aoe", "blurb": "Expanding nova rings", "look": "rings expanding from the caster"},
    "wave": {"clone": "196", "kind": "wave", "blurb": "Traveling wave (hits 197 / 198)", "look": "side-on crest traveling left to right, stacked heights"},
    "line": {"clone": "7", "kind": "line", "blurb": "Lightning pierce line (hit 63)", "look": "thin piercing line / lightning lance"},
    "whirl": {"clone": "15", "kind": "melee", "blurb": "Whirlwind spin", "look": "spinning melee swirl around the body"},
    "lunge": {"clone": "31", "kind": "dash", "blurb": "Lunge dash", "look": "forward dash / lunge streak"},
    "teleport": {"clone": "65", "kind": "self", "blurb": "Phaseshift", "look": "self-cast blink / dissolve at the caster"},
    "fog": {"clone": "core_2_Fog", "kind": "cloud", "blurb": "Fog cloud", "look": "drifting cloud / mist puffs"},
    "burst": {"clone": "4", "kind": "impact", "blurb": "Fireball explosion", "look": "point-blank explosion burst"},
    "blood_hit": {"clone": "185", "kind": "impact", "blurb": "Blood drop impact", "look": "single blood splash / droplet hit"},
    "water_hit": {"clone": "197", "kind": "impact", "blurb": "Water wave hit", "look": "water splash impact, not a projectile"},
    "rain": {"clone": "core_2_Heavy_Rain", "kind": "cloud", "blurb": "Heavy rain container", "look": "many falling drops (inner rain-drop animation)"},
    "drop": {"clone": "114", "kind": "impact", "blurb": "Single rain drop fall", "look": "one drop falling from high elevation then splash"},
    "geyser": {"clone": "20", "kind": "aoe", "blurb": "Ground burst (small explosion)", "look": "burst at the targeted tile, not a cone spit"},
    "spit": {"clone": "core_2_Magma_Spit", "kind": "projectile", "blurb": "Magma spit bolt", "look": "short spit / glob projectile"},
    "smoke": {"clone": "core_2_Smoke_bomb", "kind": "cloud", "blurb": "Smoke bomb cloud", "look": "billowing smoke cloud"},
    "frost": {"clone": "core_2_Frost_armor", "kind": "self", "blurb": "Frost armor aura", "look": "aura wrapping the caster, not a projectile"},
    "heal": {"clone": "core_2_Healing_Wave", "kind": "wave", "blurb": "Healing wave", "look": "gentle traveling heal pulse"},
    "hammer": {"clone": "core_2_Hammer", "kind": "impact", "blurb": "Hammer stomp", "look": "ground stomp / slam impact"},
    "ice_age": {"clone": "core_2_Ice_age", "kind": "aoe", "blurb": "Ice age freeze field", "look": "area freeze / frost field"},
}


def parse_rgba(raw: Union[str, Sequence[int], None]) -> Optional[List[int]]:
    if raw is None:
        return None
    if isinstance(raw, (list, tuple)):
        parts = [int(x) for x in raw]
    else:
        parts = [int(x.strip()) for x in str(raw).split(",") if x.strip()]
    if len(parts) < 3:
        raise ValueError(f"Color needs R,G,B or R,G,B,A — got {raw!r}")
    rgba = list(parts) + [255] * max(0, 4 - len(parts))
    return [max(0, min(255, int(rgba[0]))), max(0, min(255, int(rgba[1]))), max(0, min(255, int(rgba[2]))), max(0, min(255, int(rgba[3])))]


def recolor_animation(anim: Dict[str, Any], rgba: Sequence[int]) -> Dict[str, Any]:
    color = [int(rgba[0]), int(rgba[1]), int(rgba[2]), int(rgba[3] if len(rgba) > 3 else 255)]
    for part in anim.get("particles") or []:
        if isinstance(part, dict) and part.get("color"):
            part["color"] = [color[:]]
    return anim


def impact_ids(anim: Dict[str, Any]) -> List[str]:
    ids: List[str] = []
    for part in anim.get("particles") or []:
        if not isinstance(part, dict):
            continue
        oid = part.get("on_impact")
        if oid not in (None, ""):
            ids.append(str(oid))
    inner = anim.get("animation")
    if inner not in (None, ""):
        ids.append(str(inner))
    return ids


def remap_impacts(anim: Dict[str, Any], mapping: Dict[str, str]) -> Dict[str, Any]:
    for part in anim.get("particles") or []:
        if not isinstance(part, dict):
            continue
        oid = str(part.get("on_impact") or "")
        if oid in mapping:
            part["on_impact"] = mapping[oid]
    inner = str(anim.get("animation") or "")
    if inner in mapping:
        anim["animation"] = mapping[inner]
    return anim


def compose_animation(
    *,
    source: Optional[str] = None,
    preset: Optional[str] = None,
    new_id: str,
    name: Optional[str] = None,
    color: Optional[Union[str, Sequence[int]]] = None,
    clone_impact: bool = False,
    on_impact: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Build a new animation (and optional cloned impact FX).

    Returns the main animation first, then any cloned impact animations.
    """
    if preset:
        key = str(preset).strip().lower()
        if key not in PRESETS:
            raise KeyError(f"Unknown preset '{preset}'. Choose: {', '.join(PRESETS)}")
        source = PRESETS[key]["clone"]
    if not source:
        raise ValueError("compose_animation needs --preset or --clone")
    rgba = parse_rgba(color) if color is not None else None
    main = clone_animation(source, new_id=new_id, name=name or new_id, color=rgba)
    extras: List[Dict[str, Any]] = []
    if on_impact:
        remap_impacts(main, {oid: str(on_impact) for oid in set(impact_ids(main))})
        return [main]
    if not clone_impact:
        return [main]
    mapping: Dict[str, str] = {}
    for oid in impact_ids(main):
        if oid in mapping or oid == new_id:
            continue
        suffix = slug_name(oid) or "hit"
        child_id = f"{new_id}_hit" if not mapping else f"{new_id}_hit_{suffix}"
        child_name = f"{name or new_id} Hit {suffix}"
        try:
            child = clone_animation(
                oid,
                new_id=child_id,
                name=child_name,
                color=rgba,
            )
        except FileNotFoundError:
            continue
        extras.append(child)
        mapping[oid] = child_id
    remap_impacts(main, mapping)
    return [main] + extras


def list_presets() -> List[Dict[str, str]]:
    rows = []
    for key, meta in PRESETS.items():
        rows.append({"preset": key, **meta})
    return rows


def list_particle_usage(query: str = "", limit: int = 40) -> List[Dict[str, Any]]:
    """Which vanilla animations use which particle tile_id (glyph index)."""
    q = (query or "").strip().lower()
    usage: Dict[int, List[str]] = defaultdict(list)
    for _source, path in _iter_animation_files():
        try:
            data = __import__("json").loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        label = f"{data.get('id') or path.stem} ({data.get('name') or path.stem})"
        for part in data.get("particles") or []:
            if not isinstance(part, dict) or "tile_id" not in part:
                continue
            try:
                tid = int(part["tile_id"])
            except (TypeError, ValueError):
                continue
            if label not in usage[tid]:
                usage[tid].append(label)
    rows: List[Dict[str, Any]] = []
    for tid in sorted(usage):
        names = usage[tid]
        blob = f"{tid} " + " ".join(names)
        if q and q not in blob.lower() and q not in str(tid):
            continue
        rows.append({"tile_id": tid, "used_by": names[:8], "count": len(names)})
        if len(rows) >= limit:
            break
    return rows


def make_rain_burst(
    *,
    new_id: str,
    name: str,
    color: Optional[Sequence[int]] = None,
    repeat: int = 22,
    random_delay: Optional[Sequence[int]] = None,
    drop_source: str = "114",
    clone_drops: bool = False,
) -> List[Dict[str, Any]]:
    """Combat-length Heavy Rain: inner rain-drop fall (elevation_drop) plus splash.

    Water can keep vanilla ``114``/``115``. Blood (or any tint) clones those drops
    so the glyph colors change without overlaying ``particles32``.
    """
    extras: List[Dict[str, Any]] = []
    inner_id = drop_source
    if clone_drops or color is not None:
        extras = compose_animation(
            source=drop_source,
            new_id=f"{new_id}_drop",
            name=f"{name} Drop",
            color=color,
            clone_impact=True,
        )
        inner_id = extras[0]["id"]
    container = clone_animation(source_id="core_2_Heavy_Rain", new_id=new_id, name=name)
    container["animation"] = inner_id
    container["repeat"] = int(repeat)
    container["random_target"] = True
    container["ignore_roof"] = True
    container["random_delay"] = list(random_delay if random_delay is not None else (0, 70))
    container["camera_shake"] = {
        "bounces": 4,
        "duration": 0.35,
        "power": 5,
        "type": 1,
    }
    return [container] + extras


def referenced_animation_ids(spec: Dict[str, Any]) -> set:
    ids = set()
    for ab in spec.get("abilities") or []:
        aid = ab.get("animation")
        if aid not in (None, ""):
            ids.add(str(aid))
    changed = True
    while changed:
        changed = False
        by_id = {str(a.get("id")): a for a in spec.get("animations") or [] if isinstance(a, dict)}
        for aid in list(ids):
            anim = by_id.get(aid)
            if not anim:
                continue
            inner = anim.get("animation")
            if inner not in (None, "") and str(inner) not in ids:
                ids.add(str(inner))
                changed = True
            for part in anim.get("particles") or []:
                if not isinstance(part, dict):
                    continue
                oid = part.get("on_impact")
                if oid not in (None, "") and str(oid) not in ids:
                    ids.add(str(oid))
                    changed = True
    return ids


def prune_unreferenced_animations(spec: Dict[str, Any]) -> List[str]:
    keep = referenced_animation_ids(spec)
    kept, dropped = [], []
    for anim in spec.get("animations") or []:
        if str(anim.get("id")) in keep:
            kept.append(anim)
        else:
            dropped.append(str(anim.get("id")))
    spec["animations"] = kept
    return dropped


def infer_vanilla_fx(name: str, *, theme: str = "water") -> Dict[str, Any]:
    """Pick a core_2 animation that already uses particles32. Never extends the atlas."""
    blob = (name or "").lower().replace("_", " ").replace("-", " ")
    theme = (theme or "water").lower()
    blood = theme == "blood" or "blood" in blob
    if blood and "burst" in blob and "steam" not in blob:
        return {"kind": "rain_burst", "repeat": 18, "random_delay": (0, 55), "clone_drops": True}
    if any(w in blob for w in ("waterfall", "deluge", "downpour", "torrent")):
        repeat = 42 if "deluge" in blob else 22
        delay = (0, 110) if "deluge" in blob else (0, 70)
        return {"kind": "rain_burst", "repeat": repeat, "random_delay": delay, "clone_drops": blood}
    if "geyser" in blob:
        return {"kind": "clone", "source": "20", "clone_impact": False}
    if any(w in blob for w in ("lance", "spike")):
        return {"kind": "clone", "source": "7", "clone_impact": False}
    if any(w in blob for w in ("jet", "spit")):
        return {"kind": "clone", "source": "core_2_Magma_Spit", "on_impact": "185" if blood else "115"}
    if "bolt" in blob:
        return {"kind": "clone", "source": "51", "clone_impact": True}
    if any(w in blob for w in ("fireball", "meteor")):
        return {"kind": "clone", "source": "3", "clone_impact": True}
    if any(w in blob for w in ("fire", "flame", "ember", "burn", "immolat")):
        return {"kind": "clone", "source": "4"}
    if any(w in blob for w in ("lightning", "thunder", "shock", "spark", "volt")):
        return {"kind": "clone", "source": "7", "clone_impact": False}
    if any(w in blob for w in ("poison", "acid", "toxic", "venom")):
        return {"kind": "clone", "source": "23"}
    if any(w in blob for w in ("rock", "stone", "boulder", "earth")):
        return {"kind": "clone", "source": "1", "clone_impact": True}
    if any(w in blob for w in ("steam", "smoke")):
        return {"kind": "clone", "source": "core_2_Smoke_bomb"}
    if any(w in blob for w in ("fog", "mist", "cloud")):
        return {"kind": "clone", "source": "core_2_Fog"}
    if any(w in blob for w in ("shield", "ward", "armor")):
        return {"kind": "clone", "source": "core_2_Frost_armor"}
    if any(w in blob for w in ("splash", "impact")) and "blood" not in blob:
        return {"kind": "clone", "source": "197"}
    if any(w in blob for w in ("whirl", "whirlpool")):
        return {"kind": "clone", "source": "15"}
    if any(w in blob for w in ("ice age", "glaciation", "glac")):
        return {"kind": "clone", "source": "core_2_Ice_age"}
    if any(w in blob for w in ("wave", "undertow", "tide", "surge", "current")):
        return {"kind": "clone", "source": "196", "clone_impact": True}
    if any(w in blob for w in ("freeze", "frost", "ice")):
        return {"kind": "clone", "source": "core_2_Ice_age"}
    if any(w in blob for w in ("hammer", "stomp")):
        return {"kind": "clone", "source": "core_2_Hammer"}
    if any(w in blob for w in ("channel", "heal", "siphon")):
        return {"kind": "clone", "source": "core_2_Healing_Wave"}
    if any(w in blob for w in ("implosion", "nova", "crush")):
        return {"kind": "clone", "source": "61"}
    if any(w in blob for w in ("rupture", "capillary", "vein", "wound", "bleed")):
        return {"kind": "clone", "source": "185"}
    if blood:
        return {"kind": "clone", "source": "185"}
    return {"kind": "clone", "source": "196", "clone_impact": True}


def retarget_to_vanilla(
    spec: Dict[str, Any],
    anim: Dict[str, Any],
    *,
    theme: str = "water",
    color: Optional[Sequence[int]] = None,
) -> List[Dict[str, Any]]:
    """Replace one spec animation with a vanilla-glyph clone. Returns rows to upsert."""
    aid = str(anim.get("id") or "")
    name = str(anim.get("name") or aid)
    plan = infer_vanilla_fx(name, theme=theme)
    rgba = parse_rgba(color) if color is not None else None
    if plan["kind"] == "rain_burst":
        return make_rain_burst(
            new_id=aid,
            name=name,
            color=rgba,
            repeat=int(plan.get("repeat") or 22),
            random_delay=plan.get("random_delay"),
            clone_drops=bool(plan.get("clone_drops")),
        )
    return compose_animation(
        source=plan["source"],
        new_id=aid,
        name=name,
        color=rgba,
        clone_impact=bool(plan.get("clone_impact")),
        on_impact=plan.get("on_impact"),
    )


def theme_tint(theme: str) -> List[int]:
    from s2_particle_art import theme_rgba

    return theme_rgba(theme)


def tint_for_name(name: str, theme: str = "water") -> Optional[List[int]]:
    from s2_particle_art import infer_theme, theme_rgba

    blob = (name or "").lower()
    guessed = infer_theme(blob, fallback=theme or "water")
    return theme_rgba(guessed)


THEME_TINT = {
    "water": [70, 170, 230, 255],
    "blood": [180, 36, 48, 255],
    "steam": [210, 228, 236, 255],
    "ice": [180, 220, 255, 255],
    "lightning": [160, 210, 255, 255],
    "earth": [160, 130, 70, 255],
    "fire": [255, 120, 40, 255],
    "poison": [80, 180, 60, 255],
    "arcane": [160, 90, 220, 255],
}


def _tint_for(name: str, theme: str) -> Optional[List[int]]:
    return tint_for_name(name, theme)


def produce_fx(
    *,
    new_id: str,
    name: str,
    preset: Optional[str] = None,
    clone: Optional[str] = None,
    theme: Optional[str] = None,
    color: Optional[Union[str, Sequence[int]]] = None,
    clone_impact: Optional[bool] = None,
    on_impact: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a tinted vanilla-glyph clone. Never copies particles32.

    Returns plan, theme, rgba, and animation rows (main first).
    """
    from s2_particle_art import infer_theme, resolve_theme, theme_rgba

    theme_id = resolve_theme(theme, name=name) if theme not in (None, "", "auto") else infer_theme(name, fallback="generic")
    if theme in (None, "", "auto"):
        theme_id = infer_theme(name, fallback=theme_id or "water")
    rgba = parse_rgba(color) if color is not None else theme_rgba(theme_id)
    if preset or clone:
        key = str(preset or "").strip().lower()
        meta = PRESETS.get(key) or {}
        impact = bool(clone_impact) if clone_impact is not None else True
        rows = compose_animation(
            source=clone,
            preset=preset,
            new_id=new_id,
            name=name,
            color=rgba,
            clone_impact=impact,
            on_impact=on_impact,
        )
        return {
            "theme": theme_id,
            "rgba": rgba,
            "plan": {
                "kind": "preset" if preset else "clone",
                "preset": preset,
                "source": clone or meta.get("clone"),
                "clone_impact": impact,
                "look": meta.get("look") or "",
            },
            "rows": rows,
        }
    plan = infer_vanilla_fx(name, theme=theme_id)
    if clone_impact is not None:
        plan = dict(plan)
        plan["clone_impact"] = bool(clone_impact)
    if on_impact:
        plan = dict(plan)
        plan["on_impact"] = on_impact
    dummy = {"id": new_id, "name": name}
    rows = retarget_to_vanilla({"animations": []}, dummy, theme=theme_id, color=rgba)
    look = ""
    src = plan.get("source")
    for key, meta in PRESETS.items():
        if meta.get("clone") == src:
            look = meta.get("look") or ""
            plan = dict(plan)
            plan["preset"] = key
            break
    return {"theme": theme_id, "rgba": rgba, "plan": {**plan, "look": look}, "rows": rows}


def use_vanilla_particles(spec: Dict[str, Any], *, theme: str = "water", root: Optional[Any] = None) -> List[str]:
    """Retarget every ability-bound custom FX to vanilla particles32 glyphs."""
    from s2_particle_art import strip_particle_overlay
    from s2_skill_spec import add_animation

    notes: List[str] = []
    bound: List[str] = []
    for ab in spec.get("abilities") or []:
        aid = str(ab.get("animation") or "")
        if aid and not aid.isdigit():
            bound.append(aid)
    by_id = {str(a.get("id")): a for a in spec.get("animations") or [] if isinstance(a, dict)}
    for aid in list(dict.fromkeys(bound)):
        anim = by_id.get(aid) or {"id": aid, "name": aid}
        plan = infer_vanilla_fx(str(anim.get("name") or aid), theme=theme)
        tint = _tint_for(str(anim.get("name") or aid), theme)
        if plan["kind"] == "rain_burst" and not plan.get("clone_drops"):
            tint = None
        rows = retarget_to_vanilla(spec, anim, theme=theme, color=tint)
        for row in rows:
            add_animation(spec, row)
            by_id[str(row.get("id"))] = row
        src = "rain:" + str(plan.get("repeat")) if plan["kind"] == "rain_burst" else plan.get("source")
        notes.append(f"{aid} <- {src}")
    dropped = prune_unreferenced_animations(spec)
    if dropped:
        notes.append("pruned " + ", ".join(dropped))
    removed = strip_particle_overlay(spec, root=root)
    if removed:
        notes.append("removed overlay " + ", ".join(removed))
    return notes


def bind_animation(spec: Dict[str, Any], animation_id: str, ability_ids: Iterable[str]) -> List[str]:
    bound: List[str] = []
    wanted = [str(x).strip() for x in ability_ids if str(x).strip()]
    abilities = spec.get("abilities") or []
    for bid in wanted:
        found = False
        for ab in abilities:
            if ab.get("id") == bid:
                ab["animation"] = animation_id
                bound.append(bid)
                found = True
                break
        if not found:
            raise KeyError(f"Ability not found: {bid}")
    return bound
