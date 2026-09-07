#!/usr/bin/env python3
"""HTTP server for the Soulash 2 skill studio GUI."""

from __future__ import annotations

import json
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from s2_assets import clone_animation, search_animations
from s2_animations import compose_animation
from s2_buildings import (
    add_building,
    clone_building,
    make_training_building,
    search_buildings,
)
from s2_entities import (
    attach_granted_passive,
    clone_entity,
    grant_entity_milestones,
    make_creature,
    make_item,
    make_tile,
    search_entities,
)
from s2_paths import mods_dir, output_root, skip_mod_path, soulash2_root, staging_dir, workshop_root
from s2_planner import evaluate, list_available_mods, list_plans, load_overlay, load_plan, save_plan
from s2_races import (
    add_character_tag,
    add_control_action,
    add_production_action,
    add_race,
    clone_race,
    make_character_tag,
    make_control_action,
    make_production_action,
    make_race,
    make_settlement,
    parse_base_entity,
    parse_stat_flag,
    search_control_actions,
    search_production_actions,
    search_races,
    search_tags,
)
from s2_schema import dropdowns, effect_cards, infer_amplifier_type, list_effects, load_enums, observed_limits, parse_value, slug_name
from s2_skill_spec import (
    add_ability,
    add_amplifier,
    add_animation,
    add_entity,
    add_loot_exclude,
    add_passive,
    add_stacker,
    apply_skill_update,
    bind_ability_entity,
    clone_ability,
    grant_existing,
    load_mod_folder,
    load_spec,
    new_spec,
    save_spec,
    search_abilities,
    tree_rows,
    write_mod,
)
from s2_validate import format_issues, validate_spec

EDITOR_DIR = _HERE / "editor"
_STATE: Dict[str, Any] = {"spec_path": None}


def _json_response(handler: BaseHTTPRequestHandler, code: int, payload: Any) -> None:
    data = json.dumps(payload, indent=2).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.end_headers()
    handler.wfile.write(data)


def _read_json(handler: BaseHTTPRequestHandler) -> Any:
    length = int(handler.headers.get("Content-Length") or 0)
    raw = handler.rfile.read(length) if length else b"{}"
    return json.loads(raw.decode("utf-8") or "{}")


def _current() -> Path:
    if _STATE.get("spec_path"):
        return Path(_STATE["spec_path"])
    raise FileNotFoundError("No spec loaded")


def _try_spec() -> Optional[Dict[str, Any]]:
    try:
        return load_spec(_current())
    except Exception:
        return None


def _project_row(*, source: str, path: Path, spec: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    sid = None
    name = None
    if spec:
        sid = spec.get("id") or spec.get("skill_id") or spec.get("mod_id")
        name = (spec.get("skill") or {}).get("name")
    if not sid:
        sid = path.parent.name if path.name == "skill.json" else path.name
    return {
        "id": sid,
        "name": name or sid,
        "path": str(path),
        "source": source,
        "label": f"{source}: {name or sid}",
    }


def _projects() -> list:
    """Staging skill.json first, then live/workshop skill mods (folder paths)."""
    items: list = []
    seen: set = set()
    root = output_root()
    if root.is_dir():
        for child in sorted(root.iterdir()):
            if not child.is_dir() or child.name.startswith("_") or skip_mod_path(child):
                continue
            sp = child / "skill.json"
            if not sp.is_file():
                continue
            try:
                spec = load_spec(sp)
            except Exception:
                continue
            row = _project_row(source="staging", path=sp, spec=spec)
            items.append(row)
            seen.add(str(row["id"]))

    def _scan_mod_root(mod_root: Optional[Path], source: str) -> None:
        if not mod_root or not mod_root.is_dir():
            return
        for child in sorted(mod_root.iterdir()):
            if not child.is_dir() or child.name.startswith("_") or skip_mod_path(child):
                continue
            if child.name in ("core_2",) or child.name.startswith("core_"):
                continue
            # Skill mods have skills.json or a milestones tree; skip pure race/building packs.
            if not (child / "skills.json").is_file() and not (child / "milestones").is_dir():
                continue
            if child.name in seen:
                continue
            name = child.name
            if (child / "skills.json").is_file():
                try:
                    skills = json.loads((child / "skills.json").read_text(encoding="utf-8"))
                    if skills and isinstance(skills[0], dict):
                        name = skills[0].get("name") or name
                except Exception:
                    pass
            items.append(_project_row(source=source, path=child, spec={"id": child.name, "skill": {"name": name}}))
            seen.add(child.name)

    try:
        _scan_mod_root(mods_dir(), "live")
    except Exception:
        pass
    try:
        _scan_mod_root(workshop_root(), "workshop")
    except Exception:
        pass
    return items


def _load_into_studio(raw_path: str, *, force_import: bool = False) -> Dict[str, Any]:
    """Load a skill.json or mod folder into the studio (always editable via Output staging)."""
    path = Path(str(raw_path).strip().strip('"'))
    if not path.exists():
        raise FileNotFoundError(f"Path not found: {path}")
    if path.is_file():
        if path.name != "skill.json":
            raise ValueError("File load expects skill.json (or pass a mod folder)")
        spec = load_spec(path)
        dest = staging_dir(spec) / "skill.json"
        if path.resolve() != dest.resolve():
            save_spec(spec, dest)
            path = dest
        _STATE["spec_path"] = str(path.resolve())
        return {"path": str(path), "spec": spec, "imported": False}

    folder = path
    guess_id = folder.name
    if (folder / "skills.json").is_file():
        try:
            skills = json.loads((folder / "skills.json").read_text(encoding="utf-8"))
            if skills and isinstance(skills[0], dict) and skills[0].get("id"):
                guess_id = str(skills[0]["id"])
        except Exception:
            pass
    staging_skill = staging_dir({"id": guess_id}) / "skill.json"
    if (
        staging_skill.is_file()
        and not force_import
        and folder.resolve() != staging_skill.parent.resolve()
    ):
        spec = load_spec(staging_skill)
        _STATE["spec_path"] = str(staging_skill.resolve())
        return {
            "path": str(staging_skill),
            "spec": spec,
            "imported": False,
            "note": f"Opened existing staging copy (use force to re-import from {folder})",
        }

    if (folder / "skill.json").is_file():
        spec = load_spec(folder / "skill.json")
    else:
        spec = load_mod_folder(folder)
    dest = staging_dir(spec) / "skill.json"
    save_spec(spec, dest)
    _STATE["spec_path"] = str(dest.resolve())
    return {
        "path": str(dest),
        "spec": spec,
        "imported": folder.resolve() != dest.parent.resolve(),
        "note": f"Loaded into staging {dest}",
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[skill-studio] {self.address_string()} {fmt % args}")

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            self._serve(EDITOR_DIR / "index.html", "text/html; charset=utf-8")
            return
        if path in ("/planner", "/planner.html"):
            self._serve(EDITOR_DIR / "planner.html", "text/html; charset=utf-8")
            return
        if path == "/api/status":
            spec = _try_spec()
            game = None
            try:
                game = str(soulash2_root())
            except Exception:
                game = None
            ws = workshop_root()
            _json_response(
                self,
                200,
                {
                    "spec_path": _STATE.get("spec_path"),
                    "spec_id": (spec or {}).get("id"),
                    "skill_id": (spec or {}).get("skill_id"),
                    "game": game,
                    "workshop": str(ws) if ws else None,
                    "projects": _projects(),
                },
            )
            return
        if path == "/api/spec":
            try:
                sp = _current()
                _json_response(self, 200, {"path": str(sp), "spec": load_spec(sp)})
            except Exception as exc:
                _json_response(self, 404, {"error": str(exc)})
            return
        if path == "/api/catalog":
            _json_response(
                self,
                200,
                {
                    "effects": list_effects(),
                    "enums": load_enums(),
                    "dropdowns": dropdowns(),
                    "cards": effect_cards(),
                    "limits": observed_limits(),
                },
            )
            return
        if path == "/api/tree":
            spec = _try_spec()
            if not spec:
                _json_response(self, 404, {"error": "No spec"})
                return
            _json_response(self, 200, {"tree": tree_rows(spec)})
            return
        if path == "/api/projects":
            _json_response(self, 200, {"projects": _projects()})
            return
        if path == "/api/entities/search":
            qs = parse_qs(urlparse(self.path).query)
            q = (qs.get("q") or [""])[0]
            role = (qs.get("role") or [""])[0]
            _json_response(self, 200, {"results": search_entities(q, role=role or None)})
            return
        if path == "/api/entities/get":
            qs = parse_qs(urlparse(self.path).query)
            eid = (qs.get("id") or [""])[0].strip()
            if not eid:
                _json_response(self, 400, {"error": "id required"})
                return
            try:
                from s2_entities import load_vanilla_entity

                ent = load_vanilla_entity(eid)
            except Exception as exc:
                _json_response(self, 404, {"error": str(exc)})
                return
            _json_response(self, 200, {"entity": ent})
            return
        if path == "/api/animations/search":
            qs = parse_qs(urlparse(self.path).query)
            q = (qs.get("q") or [""])[0]
            _json_response(self, 200, {"results": search_animations(q)})
            return
        if path == "/api/abilities/search":
            qs = parse_qs(urlparse(self.path).query)
            q = (qs.get("q") or [""])[0]
            _json_response(self, 200, {"results": search_abilities(q)})
            return
        if path == "/api/races/search":
            qs = parse_qs(urlparse(self.path).query)
            q = (qs.get("q") or [""])[0]
            _json_response(self, 200, {"results": search_races(q)})
            return
        if path == "/api/tags/search":
            qs = parse_qs(urlparse(self.path).query)
            q = (qs.get("q") or [""])[0]
            _json_response(self, 200, {"results": search_tags(q)})
            return
        if path == "/api/control-actions/search":
            qs = parse_qs(urlparse(self.path).query)
            q = (qs.get("q") or [""])[0]
            _json_response(self, 200, {"results": search_control_actions(q)})
            return
        if path == "/api/production-actions/search":
            qs = parse_qs(urlparse(self.path).query)
            q = (qs.get("q") or [""])[0]
            _json_response(self, 200, {"results": search_production_actions(q)})
            return
        if path == "/api/buildings/search":
            qs = parse_qs(urlparse(self.path).query)
            q = (qs.get("q") or [""])[0]
            _json_response(self, 200, {"results": search_buildings(q)})
            return
        if path == "/api/planner/mods":
            _json_response(self, 200, {"mods": list_available_mods()})
            return
        if path == "/api/planner/plans":
            qs = parse_qs(urlparse(self.path).query)
            pid = (qs.get("id") or [""])[0]
            if pid:
                try:
                    _json_response(self, 200, {"plan": load_plan(pid)})
                except FileNotFoundError:
                    _json_response(self, 404, {"error": f"No plan {pid}"})
                return
            _json_response(self, 200, {"plans": list_plans()})
            return
        _json_response(self, 404, {"error": "not found"})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        body = _read_json(self)

        if path == "/api/planner/overlay":
            try:
                overlay = load_overlay(body.get("mods"))
            except Exception as exc:
                _json_response(self, 400, {"error": str(exc)})
                return
            _json_response(self, 200, overlay)
            return

        if path == "/api/planner/evaluate":
            try:
                overlay = load_overlay(body.get("mods"))
                result = evaluate(
                    overlay,
                    race_id=str(body.get("race_id") or ""),
                    starting=list(body.get("starting") or []),
                    allocations={str(k): int(v) for k, v in (body.get("allocations") or {}).items()},
                    stage=str(body.get("stage") or "elder"),
                )
            except Exception as exc:
                _json_response(self, 400, {"error": str(exc)})
                return
            _json_response(self, 200, result)
            return

        if path == "/api/planner/plans":
            name = str(body.get("name") or "plan")
            path_out = save_plan(name, body)
            _json_response(self, 200, {"ok": True, "path": str(path_out), "id": path_out.stem})
            return

        if path == "/api/new":
            spec = new_spec(body["id"], body.get("name") or body["id"], mod_id=body.get("mod_id"))
            sp = save_spec(spec)
            _STATE["spec_path"] = str(sp.resolve())
            _json_response(self, 200, {"path": str(sp), "spec": spec})
            return

        if path == "/api/load":
            try:
                raw = body.get("path") or body.get("folder") or body.get("file")
                if not raw:
                    raise ValueError("Provide path to a skill.json or mod folder")
                payload = _load_into_studio(str(raw), force_import=bool(body.get("force")))
                _json_response(self, 200, payload)
            except Exception as exc:
                _json_response(self, 400, {"error": str(exc)})
            return

        if path == "/api/spec":
            if "path" in body and "spec" not in body:
                try:
                    payload = _load_into_studio(str(body["path"]), force_import=bool(body.get("force")))
                    _json_response(self, 200, payload)
                except Exception as exc:
                    _json_response(self, 400, {"error": str(exc)})
                return
            if "spec" in body:
                spec = body["spec"]
                sp = Path(body.get("path") or _STATE.get("spec_path") or (output_root() / spec["id"] / "skill.json"))
                save_spec(spec, sp)
                _STATE["spec_path"] = str(sp.resolve())
                _json_response(self, 200, {"ok": True, "path": str(sp), "spec": spec})
                return
            _json_response(self, 400, {"error": "Provide path and/or spec"})
            return

        if path == "/api/skill":
            spec = load_spec(_current())
            apply_skill_update(spec, body)
            save_spec(spec, _current())
            _json_response(self, 200, {"ok": True, "spec": spec})
            return

        if path == "/api/add":
            spec = load_spec(_current())
            kind = body.get("kind")
            level = body.get("unlock_level")
            if kind == "ability":
                add_ability(spec, body["payload"], unlock_level=level)
            elif kind == "amplifier":
                payload = body["payload"]
                if not payload.get("type") and (payload.get("bonuses") or []):
                    payload["type"] = infer_amplifier_type(str(payload["bonuses"][0].get("effect")))
                add_amplifier(spec, payload, unlock_level=level)
            elif kind == "passive":
                add_passive(
                    spec,
                    body["payload"],
                    unlock_level=level,
                    innate=bool(body.get("innate")),
                    no_milestone=bool(body.get("no_milestone")),
                )
            elif kind == "stacker":
                payload = body["payload"]
                payload.pop("bind_ability", None)
                payload.pop("stacker_count", None)
                try:
                    add_stacker(
                        spec,
                        payload,
                        bind_ability=body.get("bind_ability"),
                        stacker_count=int(body.get("stacker_count") or 1),
                    )
                except KeyError as exc:
                    _json_response(self, 400, {"error": str(exc)})
                    return
            elif kind == "animation":
                payload = body["payload"]
                try:
                    add_animation(spec, payload, bind_ability=body.get("bind_ability"))
                except KeyError as exc:
                    _json_response(self, 400, {"error": str(exc)})
                    return
            elif kind in ("item", "creature", "tile"):
                payload = body["payload"]
                add_entity(spec, payload)
                if body.get("loot_exclude"):
                    add_loot_exclude(spec, payload["id"])
                if kind == "item" and payload.get("usable", {}).get("skill_p") and body.get("recipe_level") is not None:
                    grant_existing(
                        spec,
                        kind="recipe",
                        reward_id=payload["id"],
                        name=payload.get("name") or payload["id"],
                        unlock_level=int(body["recipe_level"]),
                    )
                if body.get("summon_ability"):
                    bind_ability_entity(spec, body["summon_ability"], "summon", payload["id"])
            elif kind == "race":
                payload = body["payload"]
                add_race(spec, payload, name_files=body.get("name_files"))
                if body.get("tag"):
                    add_character_tag(spec, body["tag"])
                if body.get("control_action"):
                    add_control_action(spec, body["control_action"])
            elif kind == "control_action":
                payload = body["payload"] or {}
                if payload.get("clone_from") or (payload.get("tags") and not payload.get("id")):
                    action = make_control_action(
                        action_id=payload.get("id") or f"{spec['skill_id']}_{slug_name(payload.get('name') or 'control').lower()}",
                        name=payload.get("name") or "Control",
                        tags=[str(t) for t in (payload.get("tags") or [])],
                        description=payload.get("description"),
                        clone_from=payload.get("clone_from") or "core_2_tame",
                    )
                    add_control_action(spec, action)
                else:
                    add_control_action(spec, payload)
            elif kind == "production_action":
                payload = body["payload"] or {}
                sid = spec.get("skill_id") or "skill"
                pid = payload.get("id") or f"{sid}_{slug_name(payload.get('name') or payload.get('clone_from') or 'action').lower()}"
                action = make_production_action(
                    pid,
                    payload.get("name") or pid,
                    description=payload.get("description") or "",
                    required_tool=int(payload.get("required_tool") or 0),
                    image=int(payload.get("image") or 0),
                    sound=payload.get("sound") or "",
                    equipment=bool(payload.get("equipment")),
                    clone_from=payload.get("clone_from"),
                )
                add_production_action(spec, action)
                if body.get("unlock_level") is not None:
                    grant_existing(
                        spec,
                        kind="production_action",
                        reward_id=str(action["id"]),
                        name=action.get("name") or action["id"],
                        unlock_level=int(body["unlock_level"]),
                    )
            else:
                _json_response(self, 400, {"error": f"Unknown kind {kind}"})
                return
            save_spec(spec, _current())
            _json_response(self, 200, {"ok": True, "spec": spec, "tree": tree_rows(spec)})
            return

        if path == "/api/build-entity":
            spec = _try_spec() or {}
            sid = spec.get("skill_id") or "skill"
            role = (body.get("role") or "item").lower()
            name = body.get("name") or role
            eid = body.get("id") or f"{sid}_{slug_name(name).lower()}"
            dmg = body.get("damage") or [3, 6]
            if isinstance(dmg, str):
                dmg = parse_value(dmg)
            if role == "item":
                payload = make_item(
                    eid=eid,
                    name=name,
                    preset=body.get("preset") or "generic",
                    description=body.get("description") or "",
                    skill_id=sid,
                    glyph_index=int(body.get("glyph") or 0),
                    value=int(body.get("value") or 100),
                    damage=dmg if isinstance(dmg, list) else [2, 4],
                    damage_type=body.get("damage_type") or "physical",
                )
            elif role == "tile":
                payload = make_tile(eid=eid, name=name, description=body.get("description") or "", glyph_index=int(body.get("glyph") or 1), health=int(body.get("health") or 1))
            else:
                payload = make_creature(
                    eid=eid,
                    name=name,
                    preset=body.get("preset") or "summon",
                    description=body.get("description") or "",
                    health=int(body.get("health") or 80),
                    damage=dmg if isinstance(dmg, list) else [3, 6],
                    damage_type=body.get("damage_type") or "physical",
                    glyph_index=int(body.get("glyph") or 90),
                )
            if body.get("granted_passive"):
                attach_granted_passive(payload, body["granted_passive"])
            if role != "item" and body.get("no_health_regen"):
                payload["can_regenerate_health"] = False
            if body.get("grant_milestone"):
                miles = body["grant_milestone"]
                if isinstance(miles, str):
                    miles = [x.strip() for x in miles.split(",") if x.strip()]
                grant_entity_milestones(payload, list(miles or []))
            _json_response(self, 200, {"payload": payload})
            return

        if path == "/api/clone-entity":
            spec = load_spec(_current())
            new_id = body.get("new_id") or f"{spec['skill_id']}_{slug_name(body.get('name') or body['source']).lower()}"
            ent = clone_entity(body["source"], new_id=new_id, name=body.get("name"))
            add_entity(spec, ent)
            if body.get("summon_ability"):
                bind_ability_entity(spec, body["summon_ability"], "summon", ent["id"])
            save_spec(spec, _current())
            _json_response(self, 200, {"ok": True, "spec": spec, "entity": ent})
            return

        if path == "/api/clone-animation":
            spec = load_spec(_current())
            source = body.get("source")
            preset = body.get("preset")
            if not source and not preset:
                _json_response(self, 400, {"error": "source or preset required"})
                return
            new_id = body.get("new_id") or f"{spec['skill_id']}_{slug_name(body.get('name') or preset or source).lower()}"
            color = body.get("color")
            art = body.get("art")
            if not color and art:
                from s2_particle_art import resolve_theme, theme_rgba

                theme = None if art in (True, "auto", "1") else str(art)
                color = theme_rgba(resolve_theme(theme, name=str(body.get("name") or "")))
            try:
                anim = compose_animation(
                    source=source,
                    preset=body.get("preset"),
                    new_id=new_id,
                    name=body.get("name"),
                    color=color,
                    clone_impact=bool(body.get("clone_impact")),
                    on_impact=body.get("on_impact"),
                )
                binds = body.get("bind_ability")
                main = anim[0]
                for extra in anim[1:]:
                    add_animation(spec, extra)
                add_animation(spec, main, bind_ability=binds)
            except (FileNotFoundError, KeyError, ValueError) as exc:
                _json_response(self, 400, {"error": str(exc)})
                return
            save_spec(spec, _current())
            _json_response(self, 200, {"ok": True, "spec": spec, "animation": main})
            return

        if path == "/api/clone-ability":
            spec = load_spec(_current())
            source = body.get("source")
            if not source:
                _json_response(self, 400, {"error": "source required"})
                return
            try:
                ability = clone_ability(
                    source,
                    skill_id=spec["skill_id"],
                    new_id=body.get("new_id"),
                    name=body.get("name"),
                    keep_image=bool(body.get("keep_image")),
                )
                add_ability(spec, ability, unlock_level=body.get("unlock_level"))
                if body.get("clone_animation"):
                    src_anim = str(ability.get("animation") or "").strip()
                    if src_anim:
                        anim = clone_animation(
                            src_anim,
                            new_id=f"{ability['id']}_fx",
                            name=f"{ability.get('name') or ability['id']} FX",
                        )
                        add_animation(spec, anim, bind_ability=ability["id"])
            except (FileNotFoundError, KeyError, ValueError) as exc:
                _json_response(self, 400, {"error": str(exc)})
                return
            save_spec(spec, _current())
            _json_response(self, 200, {"ok": True, "spec": spec, "ability": ability})
            return

        if path == "/api/clone-race":
            spec = load_spec(_current())
            source = body.get("source")
            if not source:
                _json_response(self, 400, {"error": "source required"})
                return
            display = body.get("name") or source
            new_id = body.get("new_id") or f"{spec['skill_id']}_{slug_name(display).lower()}"
            try:
                race, blobs = clone_race(
                    source,
                    new_id=new_id,
                    name=body.get("name"),
                    keep_id=bool(body.get("keep_id")),
                    civilization=bool(body.get("civilization")),
                    overlay=bool(body.get("overlay")),
                )
            except FileNotFoundError as exc:
                _json_response(self, 400, {"error": str(exc)})
                return
            if body.get("playable"):
                race["playable"] = True
            if body.get("passives"):
                race["passives"] = list(dict.fromkeys(list(race.get("passives") or []) + list(body["passives"])))
            if body.get("abilities"):
                race["abilities"] = list(dict.fromkeys(list(race.get("abilities") or []) + list(body["abilities"])))
            add_race(spec, race, name_files=blobs or None)
            save_spec(spec, _current())
            _json_response(self, 200, {"ok": True, "spec": spec, "race": race})
            return

        if path == "/api/clone-building":
            spec = load_spec(_current())
            source = body.get("source")
            display = body.get("name") or source or spec.get("skill_id")
            new_id = body.get("new_id") or f"{spec['skill_id']}_{slug_name(display).lower()}"
            skill_id = body.get("enable") or spec.get("skill_id")
            template = body.get("template") or "magic"
            try:
                if body.get("training"):
                    row = make_training_building(
                        new_id=new_id,
                        name=body.get("name") or f"{spec.get('skill', {}).get('name') or spec['skill_id']} Hall",
                        skill_id=skill_id,
                        template=template,
                    )
                else:
                    if not source:
                        _json_response(self, 400, {"error": "source required"})
                        return
                    enables = [skill_id] if body.get("train", True) else None
                    row = clone_building(source, new_id=new_id, name=body.get("name"), enables=enables)
            except FileNotFoundError as exc:
                _json_response(self, 400, {"error": str(exc)})
                return
            add_building(spec, row)
            save_spec(spec, _current())
            _json_response(self, 200, {"ok": True, "spec": spec, "building": row})
            return

        if path == "/api/build-race":
            spec = _try_spec() or {}
            sid = spec.get("skill_id") or "skill"
            name = body.get("name") or "New Race"
            rid = body.get("id") or f"{sid}_{slug_name(name).lower()}"
            stats = body.get("statistics") or {}
            if isinstance(stats, str):
                parsed = {}
                for part in stats.split(","):
                    part = part.strip()
                    if not part:
                        continue
                    try:
                        k, v = parse_stat_flag(part.replace(":", "=") if "=" not in part else part)
                        parsed[k] = v
                    except ValueError as exc:
                        _json_response(self, 400, {"error": str(exc)})
                        return
                stats = parsed
            settle = make_settlement(
                max_settlements=body.get("settle_max"),
                disabled_trading=bool(body.get("no_trading")),
                collapse_on_leader_death=True if body.get("collapse_on_leader_death") else None,
                war_causes=body.get("war_causes"),
                birth_resource=body.get("birth_resource"),
                birth_amount=int(body.get("birth_amount") or 1),
                aggression_default=True if body.get("aggression_default") else None,
                single_family=bool(body.get("single_family")),
            )
            bases = {}
            for raw in body.get("base_entities") or []:
                if isinstance(raw, str):
                    try:
                        role, eid = parse_base_entity(raw)
                    except ValueError as exc:
                        _json_response(self, 400, {"error": str(exc)})
                        return
                    bases[role] = eid
                elif isinstance(raw, dict):
                    bases.update({str(k): str(v) for k, v in raw.items() if v})
            if body.get("base_adult"):
                bases["adult"] = str(body["base_adult"])
            race, blobs = make_race(
                race_id=rid,
                name=name,
                description=body.get("description") or "",
                playable=not body.get("unplayable"),
                statistics=stats or None,
                tags=body.get("tags") or None,
                passives=body.get("passives") or None,
                abilities=body.get("abilities") or None,
                items=body.get("items") or None,
                recipes=body.get("recipes") or None,
                settlement=None if body.get("no_settle") else settle,
                base_entities=bases or None,
                orphan_surname=body.get("orphan_surname"),
            )
            if body.get("new_tag"):
                tag = make_character_tag(tag_id=body.get("new_tag_id") or rid, name=body["new_tag"])
                tags = list(race.get("tags") or [])
                if tag["id"] not in tags:
                    tags.append(tag["id"])
                    race["tags"] = tags
            else:
                tag = None
            action = None
            if body.get("control_tag"):
                action = make_control_action(
                    action_id=f"{sid}_control_{slug_name(name).lower()}",
                    name=body.get("control_name") or f"Control {name}",
                    tags=[str(body["control_tag"])],
                    clone_from=body.get("clone_control") or "core_2_tame",
                )
            _json_response(self, 200, {"payload": race, "name_files": blobs, "tag": tag, "control_action": action})
            return

        if path == "/api/validate":
            spec = body.get("spec") or load_spec(_current())
            issues = validate_spec(spec)
            _json_response(
                self,
                200,
                {
                    "ok": not any(i.level == "error" for i in issues),
                    "text": format_issues(issues),
                    "issues": [i.to_dict() for i in issues],
                },
            )
            return

        if path == "/api/write":
            spec = load_spec(_current())
            root = write_mod(spec)
            _json_response(self, 200, {"ok": True, "path": str(root)})
            return

        if path == "/api/parse-value":
            try:
                _json_response(self, 200, {"value": parse_value(str(body.get("raw") or ""))})
            except Exception as exc:
                _json_response(self, 400, {"error": str(exc)})
            return

        _json_response(self, 404, {"error": "not found"})

    def _serve(self, path: Path, content_type: str) -> None:
        if not path.is_file():
            _json_response(self, 404, {"error": f"missing {path.name}"})
            return
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def run_server(host: str, port: int, spec: Optional[Path], open_browser: bool, start_path: str = "/") -> None:
    EDITOR_DIR.mkdir(parents=True, exist_ok=True)
    if spec:
        _STATE["spec_path"] = str(Path(spec).resolve())
    httpd = ThreadingHTTPServer((host, port), Handler)
    url = f"http://{host}:{port}{start_path}"
    print(f"Soulash 2 Skill Studio {url}", flush=True)
    if spec:
        print(f"  Spec: {spec}", flush=True)
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
