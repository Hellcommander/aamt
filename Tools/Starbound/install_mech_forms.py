#!/usr/bin/env python3
"""Map packed mech_NN sheets onto Magi-Tech Form.json animation paths.

Form configs expect /sprites/forms/{id}_{anim}.png. Unity packing produced
mech_01..mech_N strips. This copies those strips under the form ids (sorted),
rewrites animation frame counts / sizes, and patches collisionBox from the
hitbox generator (pixel bounds, Y flipped to Starbound +Y up).
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_TOOLS = Path(__file__).resolve().parent
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

PIXELS_PER_TILE = 32.0

# form animation key substring -> generated cycle names (first existing file wins)
KEYWORD_CYCLES: List[Tuple[List[str], List[str]]] = [
    (["idle", "stand", "wait", "turretidle"], ["idle"]),
    (["walk", "step", "crawl"], ["walk", "move", "idle"]),
    (["run", "sprint"], ["run", "walk"]),
    (["jump", "launch"], ["jump"]),
    (["fall", "drop"], ["fall", "jump"]),
    (["swim", "aquatic", "dive", "underwater"], ["swim", "move", "walk"]),
    (["dash", "boost", "burst", "overdrive", "glide", "fly", "hover", "bank", "thruster"], ["dash", "boost", "run"]),
    (["dodge", "evade", "flinch"], ["dodge", "hurt"]),
    (["hurt", "damage", "hit"], ["hurt"]),
    (["death", "die", "explode"], ["death"]),
    (["fire", "shoot", "cannon", "weaponfire", "missile", "rotary"], ["fire", "attack"]),
    (["attack", "cast", "slash", "strike", "swarm", "claw", "blade"], ["attack", "fire"]),
    (["charge", "channel", "aim", "reload"], ["charge", "idle"]),
    (["deploy", "emerge", "open", "enter", "activate", "turretdeploy"], ["deploy", "jump", "idle"]),
    (["close", "exit", "deactivate", "dissipate", "holster"], ["idle"]),
    (["shield", "turret"], ["idle"]),
    (["move", "loco"], ["move", "walk"]),
    (["weapon"], ["fire", "attack", "idle"]),
]


def list_forms(mod: Path) -> List[Tuple[Path, dict]]:
    out = []
    for path in sorted((mod / "Data" / "Config" / "Mechs").glob("*Form.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if not data.get("id"):
            continue
        out.append((path, data))
    return out


def list_mech_ids(sheets: Path) -> List[str]:
    ids = []
    for p in (sheets / "mech").glob("mech_*_idle.png"):
        m = re.match(r"(mech_(\d+))_idle$", p.stem)
        if m:
            ids.append((int(m.group(2)), m.group(1)))
    ids.sort()
    return [name for _, name in ids]


DEFAULT_ANIM_KEYS = [
    "idle", "walk", "run", "jump", "fall", "dash", "dodge",
    "attack", "fire", "hurt", "death", "charge", "deploy",
]


def iter_anim_slots(form: dict):
    """Yield (writeback_dict, key, spec) for every animation the form declares."""
    if not isinstance(form.get("animations"), dict) or not form["animations"]:
        form["animations"] = {k: {} for k in DEFAULT_ANIM_KEYS}
    anims = form["animations"]
    for key, spec in anims.items():
        if isinstance(spec, dict):
            yield anims, key, spec
    for k, v in list(form.items()):
        if k.endswith("Animation") and isinstance(v, dict):
            yield form, k, v


def resolve_cycle(anim_key: str, mech_id: str, search_dirs: List[Path]) -> Optional[str]:
    key = anim_key.lower()
    candidates: List[str] = []
    if key in ("idle", "walk", "run", "jump", "fall", "swim", "dash", "dodge",
               "fire", "attack", "hurt", "death", "boost", "move", "charge", "deploy"):
        candidates.append(key)
    for needles, cycles in KEYWORD_CYCLES:
        if any(n in key for n in needles):
            candidates.extend(cycles)
    candidates.extend(["idle"])
    seen = set()
    for cycle in candidates:
        if cycle in seen:
            continue
        seen.add(cycle)
        for d in search_dirs:
            if (d / f"{mech_id}_{cycle}.png").exists():
                return cycle
    return None


def tile_from_frames(frames_path: Path) -> Tuple[int, int, int]:
    data = json.loads(frames_path.read_text(encoding="utf-8"))
    grid = data.get("frameGrid") or {}
    size = grid.get("size") or [96, 96]
    dims = grid.get("dimensions") or [1, 1]
    return int(size[0]), int(size[1]), int(dims[0]) * int(dims[1])


def collision_from_hitbox(hitbox_path: Path) -> Optional[List[List[float]]]:
    if not hitbox_path.exists():
        return None
    data = json.loads(hitbox_path.read_text(encoding="utf-8"))
    hb = data.get("maxHitbox") or data.get("averageHitbox")
    if not hb or not hb.get("is_valid"):
        return None
    mn = hb["min"]
    mx = hb["max"]
    # Image Y down -> Starbound Y up
    left = round(mn[0] / PIXELS_PER_TILE, 3)
    right = round(mx[0] / PIXELS_PER_TILE, 3)
    bottom = round(-mx[1] / PIXELS_PER_TILE, 3)
    top = round(-mn[1] / PIXELS_PER_TILE, 3)
    return [[left, bottom], [right, bottom], [right, top], [left, top]]


def rewrite_animation(src_anim: Path, dest: Path, form_id: str, mech_id: str) -> None:
    text = src_anim.read_text(encoding="utf-8")
    text = text.replace(f"{mech_id}_sheet.png", f"{form_id}_sheet.png")
    dest.write_text(text, encoding="utf-8")


def install_form(
    *,
    mod: Path,
    form_path: Path,
    form: dict,
    mech_id: str,
    search_dirs: List[Path],
    dest_dir: Path,
) -> dict:
    form_id = form["id"]
    dest_dir.mkdir(parents=True, exist_ok=True)
    installed = []
    for store, key, spec in iter_anim_slots(form):
        cycle = resolve_cycle(key, mech_id, search_dirs)
        if cycle is None:
            continue
        src_png = next(d / f"{mech_id}_{cycle}.png" for d in search_dirs if (d / f"{mech_id}_{cycle}.png").exists())
        src_frames = src_png.with_suffix(".frames")
        file_key = key.removesuffix("Animation") if key.endswith("Animation") else key
        dest_png = dest_dir / f"{form_id}_{file_key}.png"
        dest_frames = dest_dir / f"{form_id}_{file_key}.frames"
        shutil.copy2(src_png, dest_png)
        if src_frames.exists():
            shutil.copy2(src_frames, dest_frames)
        tw, th, n = tile_from_frames(src_frames) if src_frames.exists() else (128, 128, spec.get("frames") or 8)
        spec["frames"] = n
        spec["frameSize"] = [tw, th]
        spec["image"] = f"/sprites/forms/{form_id}_{file_key}.png"
        spec["sourceCycle"] = cycle
        store[key] = spec
        installed.append(file_key)

    sheet_src = next((d / f"{mech_id}_sheet.png" for d in search_dirs if (d / f"{mech_id}_sheet.png").exists()), None)
    if sheet_src and sheet_src.exists():
        shutil.copy2(sheet_src, dest_dir / f"{form_id}_sheet.png")
        fr = sheet_src.with_suffix(".frames")
        if fr.exists():
            shutil.copy2(fr, dest_dir / f"{form_id}_sheet.frames")
    anim_src = next((d / f"{mech_id}.animation" for d in search_dirs if (d / f"{mech_id}.animation").exists()), None)
    if anim_src:
        rewrite_animation(anim_src, dest_dir / f"{form_id}.animation", form_id, mech_id)

    hitbox = None
    for d in search_dirs:
        candidate = d / f"{mech_id}_walk.hitbox.json"
        if candidate.exists():
            hitbox = candidate
            break
    box = collision_from_hitbox(hitbox) if hitbox else None
    if box:
        form["collisionBox"] = box

    form["unitySheet"] = mech_id
    form_path.write_text(json.dumps(form, indent=2) + "\n", encoding="utf-8")
    return {
        "formId": form_id,
        "mechId": mech_id,
        "formFile": str(form_path),
        "animations": installed,
        "collisionBox": box,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Install mech_NN sheets onto Form.json ids")
    ap.add_argument(
        "--mod-path",
        default=r"F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery",
    )
    args = ap.parse_args()
    mod = Path(args.mod_path)
    sheets = mod / "assets" / "magitech" / "unity_sheets"
    dest = mod / "sprites" / "forms"
    forms = list_forms(mod)
    mechs = list_mech_ids(sheets)
    search = [sheets / "mech", dest]
    mapped = []
    extras = mechs[len(forms):]
    for (form_path, form), mech_id in zip(forms, mechs):
        info = install_form(
            mod=mod, form_path=form_path, form=form, mech_id=mech_id,
            search_dirs=search, dest_dir=dest,
        )
        mapped.append(info)
        print(f"  {mech_id} -> {info['formId']} ({len(info['animations'])} anims)")

    manifest = sheets / "form_sheet_map.json"
    manifest.write_text(json.dumps({
        "mapped": mapped,
        "unmappedMechs": extras,
        "pixelsPerTile": PIXELS_PER_TILE,
    }, indent=2) + "\n", encoding="utf-8")
    print(f"[OK] Mapped {len(mapped)} forms, {len(extras)} leftover mech sheets")
    print(f"  Manifest: {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
