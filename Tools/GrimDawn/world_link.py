#!/usr/bin/env python3
"""
Merge companion worlds into the campaign world and link them with two-way portals.

Grim Dawn runs one world per session, so "go to Nydiamar and keep your progress" means:
  1. merge Nydiamar's regions + quests + riftgate/entrance index into the campaign world001
  2. place a portal object in each world (Devil's Crossing riftgate area <-> Nydiamar start)
  3. pair the two portals in the world's "Dungeon Entrances" index -- the same mechanism the
     game uses for every cave/dungeon door (the pairing lives only in that index)
  4. pack the world into the output mod's Levels.arc, add the portal records + names

Everything is driven by profiles/world_links/<name>.json and is safe to re-run after game or
mod updates (sources are re-extracted when their .arc changes; portal ids are deterministic).

  python world_link.py --profile nydiamar [--rebuild] [--dry-run]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import gd_map
from dbr_io import read_dbr, write_dbr
from gd_paths import GamePaths, file_stamp, find_mod_roots, resolve_arzedit, resolve_game_dir

TOOLS_DIR = Path(__file__).resolve().parent
PROFILES = TOOLS_DIR / "profiles" / "world_links"
WORK = TOOLS_DIR / "work" / "maps"
PORTAL_DIR = "records/kitchensink/portals"
LINK_TAG_FILE = "tags_world_links.txt"
# Things that are not solid: never block a portal spot
SOFT = (
    "decal", "fx", "sound", "light", "lantern", "candle", "trigger", "proxy", "particle", "ambient",
    "weeds", "grass", "mist", "fog", "book", "clothing", "bedding", "ivy", "bush", "cluster", "pile",
    "rug", "carpet", "spawn",
)


def _uid(*parts: str) -> bytes:
    return hashlib.md5("|".join(("gd-kitchensink",) + parts).encode()).digest()


def _arc(mod_root: Path, name: str) -> Optional[Path]:
    return next((p for p in (mod_root / "resources").glob("*.arc") if p.name.lower() == name.lower()), None)


def _world_root(game: GamePaths, spec: dict) -> Path:
    if spec.get("layer"):  # game-root expansion/Crucible folder, e.g. survivalmode3
        return game.game_dir / spec["layer"]
    return (find_mod_roots(game.mods_dir, spec["mod"]) or [game.mods_dir / spec["mod"]])[0]


def extract_map(game: GamePaths, spec: dict) -> Path:
    """Unpack one .map from a mod/layer .arc with arzedit (ArchiveTool fails on >2 GB files); cached."""
    root, arc_name, map_name = _world_root(game, spec), spec["arc"], spec["map"]
    mod = root.name
    arc = _arc(root, arc_name)
    if not arc:
        raise FileNotFoundError(f"{mod}: resources/{arc_name} not found")
    out = WORK / root.name / arc.stem
    stamp = out / ".stamp"
    found = next((p for p in out.rglob("*.map") if p.name.lower() == map_name.lower()), None) if out.exists() else None
    if found and stamp.is_file() and stamp.read_text(encoding="utf-8") == file_stamp([arc]):
        return found
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    arz = _arzedit()
    print(f"Extracting {arc} ...", flush=True)
    proc = subprocess.run([str(arz), "unarc", str(arc), "-o", str(out)], capture_output=True, text=True)
    found = next((p for p in out.rglob("*.map") if p.name.lower() == map_name.lower()), None)
    if proc.returncode != 0 or not found:
        raise RuntimeError(f"unarc failed for {arc}: {(proc.stdout + proc.stderr)[-800:]}")
    stamp.write_text(file_stamp([arc]), encoding="utf-8")
    return found


def _arzedit() -> Path:
    arz = resolve_arzedit()
    if not arz:
        raise RuntimeError("bin/arzedit.exe missing (run Build-Arzedit.bat)")
    return arz


GROUND = ("decal", "weeds", "grass", "rug", "carpet")


def find_clear_spot(
    lvl: gd_map.Level,
    center: Sequence[float],
    rmin: float = 3.0,
    rmax: float = 18.0,
    *,
    center_walkable: bool = False,
    avoid: Sequence[Sequence[float]] = (),
    spacing: float = 5.0,
) -> Tuple[Tuple[float, float, float], float]:
    """
    Pick a ground spot near `center` that is as far as possible from solid objects.

    Ground decals / ground cover are candidate spots (they sit on walkable ground, so no
    terrain height lookup is needed); a player spawn point counts too. Returns (pos, clearance).
    """
    def flat(a, b):
        return math.hypot(a[0] - b[0], a[2] - b[2])

    solids = [o.pos for o in lvl.objects if not any(s in lvl.records[o.record].lower() for s in SOFT)]

    def clear(c) -> float:  # only things on the same floor can block
        return min((flat(c, s) for s in solids if abs(s[1] - c[1]) <= 2.5), default=99.0)

    cands = [o.pos for o in lvl.objects if any(g in lvl.records[o.record].lower() for g in GROUND)]
    cands = [c for c in cands if rmin <= flat(c, center) <= rmax and abs(c[1] - center[1]) <= 3.0]
    if center_walkable:
        cands.append(tuple(center))
    cands = [c for c in cands if all(flat(c, a) >= spacing for a in avoid)]  # portals side by side, not stacked
    best, best_score = None, -1e9
    for c in cands:
        clearance = clear(c)
        score = min(clearance, 8.0) - flat(c, center) * 0.05  # clear enough, then close
        if clearance >= 2.0 and score > best_score:
            best, best_score = c, score
    if best is None:
        best = (center[0] + rmin + spacing * len(avoid), center[1], center[2])
    return tuple(best), clear(best)  # type: ignore[return-value]


def _anchor(gm: gd_map.GameMap, side: dict) -> Tuple[int, gd_map.Region, Tuple[float, float, float]]:
    if side.get("near_uid"):
        e = gd_map.find_point(gm, bytes.fromhex(side["near_uid"]))
        if not e:
            raise KeyError(f"anchor uid {side['near_uid']} not in this world's index")
        i, r = gd_map.region_by(gm, e.region)
        return i, r, e.pos
    if side.get("near") == "start":
        import struct

        _, ri, x, y, z = struct.unpack("<II3f", gm.start)
        return ri, gm.regions[ri], (x, y, z)
    i, r = gd_map.region_by(gm, side["region"])
    return i, r, tuple(side["pos"])  # type: ignore[return-value]


def write_portal_records(game: GamePaths, out_db: Path, portal: dict, work: Path) -> Dict[str, str]:
    """Portal object records (copies of the template door) + their tags. Returns tag -> text."""
    tpl_rel = portal["template"]
    src = out_db / tpl_rel
    if not src.is_file() and portal.get("template_mod"):
        from patch_mod_for_dlc import prepare_mod_database

        root = find_mod_roots(game.mods_dir, portal["template_mod"])[0]
        src = prepare_mod_database(game, root, work / "_merge_cache") / tpl_rel
    if not src.is_file():
        raise FileNotFoundError(f"portal template {tpl_rel} not found")
    tags = {}
    for side in ("a", "b"):
        tag = f"tagKSPortal_{portal['id']}_{side}"
        data = read_dbr(src)
        data["description"] = tag
        data["FileDescription"] = portal[side]["name"]
        data["locked"] = "0"
        write_dbr(out_db / f"{PORTAL_DIR}/portal_{portal['id']}_{side}.dbr", data)
        tags[tag] = portal[side]["name"]
    return tags


def build_database_from_mods(game: GamePaths, cfg: dict, out_mod: Path) -> None:
    """
    Rebuild the output mod's database from the CURRENT installed mods every run (merge rules:
    priority, field merge, per-mod compat, class UI, combo names, skill labels, uTXTp patches,
    templates). The output folder is recreated, so a one-time copy of the previous build is
    kept as <mod>_before_rebuild.
    """
    from merge_mod_databases import merge_mods

    roots = []
    for s in cfg["sources"]:
        found = find_mod_roots(game.mods_dir, s["mod"])
        if not found:
            raise FileNotFoundError(f"database source mod not found: {s['mod']}")
        roots.append(found[0])
    print(f"Database from current mods: {[r.name for r in roots]}", flush=True)
    merge_mods(
        game,
        roots,
        out_mod.name,
        None,
        False,  # .arz is built at the very end (after portal + Crucible records)
        use_rules=True,
        field_mode=cfg.get("field_merge", "rules"),
        skip_resources=True,  # the profile's "resources" step builds the archives
        latest=True,
        use_ollama=bool(cfg.get("ollama", False)),
        ollama_limit=int(cfg.get("ollama_limit", -1)),
    )


def build(profile_name: str, *, rebuild: bool = False, dry_run: bool = False) -> int:
    prof = json.loads((PROFILES / f"{profile_name}.json").read_text(encoding="utf-8"))
    game = GamePaths(resolve_game_dir(None))
    final_mod = game.mods_dir / prof["output_mod"]
    out_mod = final_mod
    db_cfg = prof.get("database")
    if db_cfg and not dry_run:
        # Build in a staging folder; the playable mod is only replaced once everything succeeded
        out_mod = final_mod.with_name(final_mod.name + "__building")
        if out_mod.exists():
            shutil.rmtree(out_mod)
        build_database_from_mods(game, db_cfg, out_mod)
    if not out_mod.is_dir():
        raise FileNotFoundError(f"output mod {out_mod} missing (add a 'database' section or build it first)")

    base_cfg = prof["base"]
    base_path = extract_map(game, base_cfg)
    worlds = {"base": gd_map.read_map(base_path)}
    base = worlds["base"]
    print(f"Base world: {base_path.name}: {len(base.regions)} regions", flush=True)
    others = []
    for w in prof.get("worlds", []):
        p = extract_map(game, w)
        worlds[w["id"]] = gd_map.read_map(p)
        others.append(worlds[w["id"]])
    # Each world goes into empty floor space: the engine's own worlds never overlap regions,
    # and stacking them (all Crucible arenas sit around the origin) hangs the world load.
    offsets = gd_map.auto_offsets(base, others)
    for note in gd_map.merge_maps(base, others, offsets=offsets):
        print("  " + note, flush=True)
    clashes = gd_map.find_overlaps(base.regions)
    if clashes:
        a, b = clashes[0]
        raise RuntimeError(
            f"{len(clashes)}+ overlapping regions after merge, e.g. {base.regions[a].level} / {base.regions[b].level}"
        )
    print("  region overlap check: none", flush=True)

    report = [f"# World links: {profile_name}", "", f"World: {base_path.name} + {[w['map'] for w in prof.get('worlds', [])]}", ""]
    tags: Dict[str, str] = {}
    used: Dict[bytes, List[Tuple[float, float, float]]] = {}  # portal spots taken per region
    for portal in prof.get("portals", []):
        placed = {}
        for side in ("a", "b"):
            cfg = portal[side]
            src_world = worlds[cfg["world"]]
            _, region, center = _anchor(src_world, cfg)
            # merged world shares region GUIDs with its source
            mi, mregion = gd_map.region_by(base, region.guid)
            lvl = gd_map.parse_level(gd_map.read_level_bytes(base, mregion))
            pos, clearance = find_clear_spot(
                lvl, center, rmax=cfg.get("rmax", 30.0), center_walkable=cfg.get("near") == "start",
                avoid=used.setdefault(mregion.guid, []),
            )
            used[mregion.guid].append(pos)
            pos = tuple(a + b for a, b in zip(pos, cfg.get("nudge", (0, 0, 0))))
            uid = _uid(profile_name, portal["id"], side)
            rec = f"{PORTAL_DIR}/portal_{portal['id']}_{side}.dbr"
            gd_map.add_object(base, mregion, rec, pos, uid=uid)
            placed[side] = gd_map.PointEntry(uid, rec, mregion.guid, pos)  # type: ignore[arg-type]
            line = (
                f"- {cfg['name']}: region {mi} `{mregion.level}` at ({pos[0]:.1f}, {pos[1]:.1f}, {pos[2]:.1f}), "
                f"near {cfg.get('label', '')}, clearance {clearance:.1f}"
            )
            print("  " + line, flush=True)
            report.append(line)
        group = f"-KS Portal {portal['id']}"
        head, groups = gd_map.parse_points(base.raw[17])
        groups = [g for g in groups if g.name != group]
        groups.append(gd_map.PointGroup(3, group, "Dungeon Entrances", [placed["a"], placed["b"]], _uid(profile_name, portal["id"], "group")))
        base.raw[17] = gd_map.encode_points(head, groups)
        if not dry_run:
            tags.update(write_portal_records(game, out_mod / "database", portal, TOOLS_DIR / "work"))

    # folder = Levels.arc's top level (entries are "world001.map", never "levels/world001.map")
    out_map = WORK / "_out" / prof["output_mod"] / Path(prof["out_arc"]).stem / base_path.name
    out_map.parent.mkdir(parents=True, exist_ok=True)
    print(f"Writing {out_map} ...", flush=True)
    gd_map.write_map(base, out_map)
    check = gd_map.read_map(out_map)
    print(f"  verified: {len(check.regions)} regions, {len(check.quests)} quests", flush=True)
    if dry_run:
        print("Dry run: not packing into the mod.")
        return 0

    # pack world into the output mod
    arc = _arc(out_mod, prof["out_arc"]) or (out_mod / "resources" / prof["out_arc"])
    if arc.is_file():
        bak = arc.with_suffix(".arc.bak_worldlink")
        if not bak.exists():
            shutil.copy2(arc, bak)
    print(f"Packing {arc} (large world, takes a while) ...", flush=True)
    from archive_tool import arc_entries, pack_arc

    for stale in out_map.parent.glob("*"):
        if stale.is_file() and stale != out_map:
            stale.unlink()  # only the merged world goes into this archive
    pack_arc(out_map.parent, arc)
    entries = arc_entries(game.game_dir, arc)
    if base_path.name.lower() not in [e.lower() for e in entries]:
        raise RuntimeError(f"{arc.name} entries look wrong: {entries[:5]}")
    print(f"  {arc.name}: {entries}", flush=True)

    # other copies of the merged worlds would compete with world001 at Custom Game start
    for arc_name, maps in (prof.get("remove_maps_from") or {}).items():
        a = _arc(out_mod, arc_name)
        if not a:
            continue
        listed = subprocess.run([str(game.archive_tool), str(a), "-list"], capture_output=True, text=True, cwd=str(game.game_dir)).stdout.lower()
        others_in_arc = [l for l in listed.splitlines() if l.strip().endswith(".map") and not any(m.lower() in l for m in maps)]
        if not others_in_arc and all(m.lower() in listed for m in maps):
            a.rename(a.with_suffix(".arc.bak_worldlink"))
            print(f"Moved {a.name} aside (it only held {maps}; Dungeons stays its own Custom Game)", flush=True)
        else:
            print(f"WARN: {a.name} holds other maps too; left in place: {others_in_arc[:5]}", flush=True)

    if prof.get("resources"):  # every kitchen-sink mod's assets, so the merged world finds them
        from world_content import merge_mod_resources

        for note in merge_mod_resources(game, prof["resources"], out_mod):
            print("  " + note, flush=True)
            report.append(f"- {note}")

    for content in prof.get("content", []):  # e.g. the Crucible's records, scripts, assets
        from world_content import import_content

        for note in import_content(game, content, out_mod, TOOLS_DIR / "work" / "_vanilla_cache"):
            print("  " + note, flush=True)
            report.append(f"- {note}")

    tag_file = out_mod / "localization" / LINK_TAG_FILE
    tag_file.parent.mkdir(parents=True, exist_ok=True)
    tag_file.write_text("\n".join(f"{k}={v}" for k, v in sorted(tags.items())) + "\n", encoding="utf-8")
    from fill_combo_tags import inject_tags_into_text_arc

    # every generated text file (combo names, skill labels, portal names): the resource merge
    # rebuilt Text_EN.arc from the source mods, so re-add them all
    generated = [tag_file] + [
        out_mod / "localization" / n
        for n in ("tags_mod_combos.txt", "tags_skill_class_labels.txt")
        if (out_mod / "localization" / n).is_file()
    ]
    print(inject_tags_into_text_arc(game, out_mod, generated, create=True), flush=True)

    if rebuild:
        from arz_backend import build_database

        ok, msg = build_database(out_mod, game.game_dir, _arzedit())
        print(msg if ok else f"Rebuild failed: {msg}", flush=True)

    report += ["", "Use either portal; it takes you to the other one. Same world, so quests and progress carry over.",
               "Re-run after game/mod updates: `python world_link.py --profile " + profile_name + " --rebuild`"]
    (out_mod / "WORLD_LINKS.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    if out_mod != final_mod:
        if db_cfg and rebuild and not list((out_mod / "database").glob("*.arz")):
            raise RuntimeError(f"no .arz was built in {out_mod}; keeping the current {final_mod.name}")
        prev = final_mod.with_name(final_mod.name + "__previous")
        if prev.exists():
            shutil.rmtree(prev)
        if final_mod.exists():
            final_mod.rename(prev)
        out_mod.rename(final_mod)
        # the database file is named after the mod folder
        for arz in (final_mod / "database").glob(f"{out_mod.name}.arz"):
            arz.rename(arz.with_name(f"{final_mod.name}.arz"))
        print(f"Swapped in the new build; previous build kept as {prev.name}", flush=True)
    print(f"Done: {final_mod / 'WORLD_LINKS.md'}")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Merge companion worlds into the campaign world + portals")
    p.add_argument("--profile", default="campaign", help="profiles/world_links/<name>.json (campaign = Nydiamar + Crucible)")
    p.add_argument("--rebuild", action="store_true", help="Also rebuild the output mod's .arz")
    p.add_argument("--dry-run", action="store_true", help="Build and verify the world only; don't touch the mod")
    p.add_argument("--game", default=None, help="Grim Dawn folder (default: auto / GD_GAME_DIR)")
    a = p.parse_args(argv)
    if a.game:
        import os

        os.environ["GD_GAME_DIR"] = a.game
    return build(a.profile, rebuild=a.rebuild, dry_run=a.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
