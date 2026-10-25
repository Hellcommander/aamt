#!/usr/bin/env python3
"""
Import a game mode's content (e.g. the Crucible) into a campaign Custom Game.

Used by world_link.py profiles ("content" section) so the Crucible arenas merged into the
campaign world have their wave controllers, NPCs, reward chests, scripts and assets.

Sources are layered in the game's own load order (later wins), e.g.
  mods/survivalmode  ->  survivalmode1  ->  survivalmode2  ->  survivalmode3
and re-read every build, so official Crucible patches flow in automatically.

Rules (so the campaign never breaks):
  database   records the campaign game itself also defines (base/gdx layers) are left alone;
             mode-only records are refreshed from the newest source every build
  scripts    official scripts imported fresh; entry files (main.lua, grimdawn.lua,
             questhelper.lua) stay the campaign's; renames re-applied (questevents.lua ->
             questeventssurvival.lua) and the Script.Load lines added to grimdawn.lua
  resources  files missing from the mod's same-named .arc are added; mode-specific paths
             (matching the profile's refresh words, e.g. "survival") are refreshed
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from archive_tool import ArchiveTool, arc_root, kill_orphan_archivetool, pack_arc
from gd_paths import GamePaths, file_stamp

TOOLS_DIR = Path(__file__).resolve().parent
WORK = TOOLS_DIR / "work" / "content"


def source_root(game: GamePaths, spec: dict) -> Path:
    if spec.get("layer"):
        return game.game_dir / spec["layer"]
    return game.mods_dir / spec["mod"]


def _extract_db(game: GamePaths, root: Path) -> Optional[Path]:
    arzs = sorted((root / "database").glob("*.arz"))
    if not arzs:
        return None
    out = WORK / "db" / root.name
    stamp = out / ".stamp"
    if stamp.is_file() and stamp.read_text(encoding="utf-8") == file_stamp(arzs):
        return out / "database"
    if out.exists():
        shutil.rmtree(out)
    (out / "database").mkdir(parents=True)
    tool = ArchiveTool(game.game_dir)
    for a in arzs:
        tool.extract_database(a, out / "database")
    stamp.write_text(file_stamp(arzs), encoding="utf-8")
    return out / "database"


def _extract_arc(game: GamePaths, arc: Path, label: str) -> Path:
    """Extract (cached) and return the archive's top-level folder (paths inside the .arc)."""
    out = WORK / "arc" / label / arc.stem
    stamp = out.parent / f".{arc.stem}.stamp"
    if stamp.is_file() and stamp.read_text(encoding="utf-8") == file_stamp([arc]) and out.exists():
        return arc_root(out, arc)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    ArchiveTool(game.game_dir).extract_arc(arc, out)
    stamp.write_text(file_stamp([arc]), encoding="utf-8")
    return arc_root(out, arc)


def _layered_files(roots: Sequence[Path]) -> Dict[str, Path]:
    """rel (lower) -> newest file across roots (later roots win)."""
    out: Dict[str, Path] = {}
    for root in roots:
        for p in root.rglob("*"):
            if p.is_file() and not p.name.startswith("."):
                out[p.relative_to(root).as_posix().lower()] = p
    return out


def _official_record_set(vanilla_cache: Path) -> set:
    rels = set()
    layers = vanilla_cache / "layers"
    for layer in layers.iterdir() if layers.is_dir() else []:
        for p in layer.rglob("*.dbr"):
            rels.add(p.relative_to(layer).as_posix().lower())
    return rels


def import_database(game: GamePaths, sources: Sequence[dict], out_db: Path, vanilla_cache: Path) -> Tuple[int, int, int]:
    roots = [db for db in (_extract_db(game, source_root(game, s)) for s in sources) if db]
    files = _layered_files(roots)
    official = _official_record_set(vanilla_cache)
    added = refreshed = kept = 0
    for rel, src in files.items():
        if not rel.endswith(".dbr"):
            continue
        dest = out_db / rel
        if dest.exists():
            if rel in official:
                kept += 1  # campaign/expansion record: campaign wins
                continue
            if dest.read_bytes() == src.read_bytes():
                continue
            refreshed += 1
        else:
            added += 1
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
    return added, refreshed, kept


def _repack(arc: Path, root: Path) -> None:
    """root = the archive's top level (never the folder ArchiveTool nests it in)."""
    if arc.is_file():
        bak = arc.with_suffix(".arc.bak_content")
        if not bak.exists():
            shutil.copy2(arc, bak)
    pack_arc(root, arc)


def _open_mod_arc(game: GamePaths, arc: Path, work: Path) -> Path:
    """Extract the mod's current archive into work and return its top level (repairs old prefixes)."""
    if arc.is_file():
        ArchiveTool(game.game_dir).extract_arc(arc, work)
        kill_orphan_archivetool()
        return arc_root(work, arc)
    return work


def _mod_arc(mod_root: Path, name: str) -> Optional[Path]:
    return next((p for p in (mod_root / "resources").glob("*.arc") if p.name.lower() == name.lower()), None)


def import_scripts(game: GamePaths, sources: Sequence[dict], out_mod: Path, cfg: dict) -> int:
    roots = []
    for s in sources:
        arc = _mod_arc(source_root(game, s), "Scripts.arc")
        if arc:
            roots.append(_extract_arc(game, arc, source_root(game, s).name))
    files = _layered_files(roots)

    def inner(p: str) -> str:  # Scripts.arc entries have no "scripts/" prefix; Script.Load paths do
        p = p.replace("\\", "/").lower()
        return p[len("scripts/"):] if p.startswith("scripts/") else p

    keep_campaign = {inner(k) for k in cfg.get("keep_campaign", ["main.lua", "game/grimdawn.lua", "game/questhelper.lua"])}
    renames = {inner(k): inner(v) for k, v in (cfg.get("rename") or {"game/questevents.lua": "game/questeventssurvival.lua"}).items()}
    loads = cfg.get("loads", ['Script.Load("scripts/game/survival.lua")', 'Script.Load("scripts/game/events/survivalEvent.lua")'])

    from archive_tool import needs_repair

    arc = _mod_arc(out_mod, "Scripts.arc") or (out_mod / "resources" / "Scripts.arc")
    broken = arc.is_file() and needs_repair(game.game_dir, arc)
    work = Path(tempfile.mkdtemp(prefix="scripts_", dir=str(WORK)))
    try:
        root = _open_mod_arc(game, arc, work)
        n = 0
        for rel, src in files.items():
            if rel in keep_campaign and (root / rel).exists():
                continue
            text = src.read_bytes()
            for old, new in renames.items():  # fix Script.Load paths of renamed files
                text = text.replace(f'"scripts/{old}"'.encode(), f'"scripts/{new}"'.encode())
            dest = root / renames.get(rel, rel)
            if dest.exists() and dest.read_bytes() == text:
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(text)
            n += 1
        gd = root / "game" / "grimdawn.lua"
        if gd.is_file():
            body = gd.read_bytes().decode("latin-1")
            missing = [l for l in loads if l.lower() not in body.lower()]
            if missing:
                body = body.rstrip() + "\n\n// Crucible (added by world_content.py)\n" + "\n".join(missing) + "\n"
                gd.write_bytes(body.encode("latin-1"))
                n += 1
        if n or broken:  # broken = packed with a wrong prefix by an older build
            _repack(arc, root)
        return n
    finally:
        shutil.rmtree(work, ignore_errors=True)


def import_resources(game: GamePaths, sources: Sequence[dict], out_mod: Path, cfg: dict) -> Dict[str, int]:
    skip = {a.lower() for a in cfg.get("skip_arcs", ["maps.arc", "scripts.arc", "levels.arc"])}
    refresh_words = [w.lower() for w in cfg.get("refresh_words", ["survival", "crucible"])]
    by_arc: Dict[str, List[Path]] = {}
    for s in sources:
        root = source_root(game, s)
        for arc in sorted((root / "resources").glob("*.arc")):
            if arc.name.lower() not in skip:
                by_arc.setdefault(arc.name.lower(), []).append(_extract_arc(game, arc, root.name))
    result: Dict[str, int] = {}
    for arc_l, roots in by_arc.items():
        files = _layered_files(roots)
        arc = _mod_arc(out_mod, arc_l) or (out_mod / "resources" / Path(roots[-1]).name)
        if not arc.suffix:
            arc = arc.with_suffix(".arc")
        from archive_tool import arc_entries, needs_repair

        listed = {e.lower() for e in arc_entries(game.game_dir, arc)} if arc.is_file() else set()
        broken = arc.is_file() and needs_repair(game.game_dir, arc)
        todo = {rel: src for rel, src in files.items() if rel not in listed or any(w in rel for w in refresh_words)}
        if not todo and not broken:
            continue
        work = Path(tempfile.mkdtemp(prefix="res_", dir=str(WORK)))
        try:
            root = _open_mod_arc(game, arc, work)
            changed = 0
            for rel, src in todo.items():
                dest = root / rel
                if dest.exists() and dest.read_bytes() == src.read_bytes():
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)
                changed += 1
            if changed or broken:
                _repack(arc, root)
                result[arc.name] = changed
        finally:
            shutil.rmtree(work, ignore_errors=True)
    return result


def _merge_text_files(paths: Sequence[Path]) -> bytes:
    """Same-named text files from several mods: union of tags, later file wins per tag."""
    order: List[str] = []
    values: Dict[str, str] = {}
    for p in paths:
        for line in p.read_bytes().decode("utf-8", errors="replace").splitlines():
            k, sep, _ = line.partition("=")
            key = k.strip().lower()
            if not sep or not key or key.startswith("//"):
                continue
            if key not in values:
                order.append(key)
            values[key] = line
    return ("\n".join(values[k] for k in order) + "\n").encode("utf-8")


def _merge_lua_entry(paths: Sequence[Path]) -> bytes:
    """Entry scripts (grimdawn.lua / main.lua): newest file + every other mod's Script.Load lines."""
    import re

    base = paths[-1].read_bytes().decode("latin-1")
    have = {m.lower() for m in re.findall(r'Script\.Load\(\s*"([^"]+)"\s*\)', base)}
    extra = []
    for p in paths[:-1]:
        for m in re.findall(r'Script\.Load\(\s*"([^"]+)"\s*\)', p.read_bytes().decode("latin-1")):
            if m.lower() not in have:
                have.add(m.lower())
                extra.append(f'Script.Load("{m}")')
    if extra:
        base = base.rstrip() + "\n\n// merged from other mods (world_content.py)\n" + "\n".join(extra) + "\n"
    return base.encode("latin-1")


def merge_mod_resources(game: GamePaths, cfg: dict, out_mod: Path) -> List[str]:
    """
    Build the output mod's resource archives from every source mod, in priority order
    (later wins per file). Archives only one mod has are copied as-is; same-named ones are
    unpacked and combined file by file -- text files tag by tag, entry Lua by Script.Load union.
    """
    skip = {a.lower() for a in cfg.get("skip_arcs", ["levels.arc", "maps.arc"])}
    entry_lua = {e.lower() for e in cfg.get("entry_lua", ["main.lua", "game/grimdawn.lua"])}
    by_arc: Dict[str, List[Tuple[str, Path]]] = {}
    for s in cfg["sources"]:
        root = source_root(game, s)
        for arc in sorted((root / "resources").glob("*.arc")):
            if arc.name.lower() not in skip:
                by_arc.setdefault(arc.name.lower(), []).append((root.name, arc))
    res = out_mod / "resources"
    res.mkdir(parents=True, exist_ok=True)
    notes: List[str] = []
    copied = merged = 0
    for arc_l, versions in sorted(by_arc.items()):
        name = versions[-1][1].name
        existing = next((p for p in res.glob("*.arc") if p.name.lower() == arc_l), None)
        target = existing or (res / name)
        if target.is_file() and not target.with_suffix(".arc.bak_resmerge").exists():
            shutil.copy2(target, target.with_suffix(".arc.bak_resmerge"))
        if len(versions) == 1:
            shutil.copy2(versions[0][1], target)
            copied += 1
            continue
        roots = [_extract_arc(game, arc, label) for label, arc in versions]
        files: Dict[str, List[Path]] = {}
        for r in roots:
            for p in r.rglob("*"):
                if p.is_file() and not p.name.startswith("."):
                    files.setdefault(p.relative_to(r).as_posix().lower(), []).append(p)
        work = Path(tempfile.mkdtemp(prefix="resmerge_", dir=str(WORK)))
        try:
            text_arc = arc_l.startswith("text_")
            for rel, paths in files.items():
                dest = work / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                if len(paths) > 1 and text_arc and rel.endswith(".txt"):
                    dest.write_bytes(_merge_text_files(paths))
                elif len(paths) > 1 and arc_l == "scripts.arc" and rel in entry_lua:
                    dest.write_bytes(_merge_lua_entry(paths))
                else:
                    shutil.copy2(paths[-1], dest)
            pack_arc(work, target)
            merged += 1
            notes.append(f"{name}: {len(files)} files from {[l for l, _ in versions]}")
        finally:
            shutil.rmtree(work, ignore_errors=True)
    notes.insert(0, f"resources: {copied} archives copied, {merged} merged from {len(cfg['sources'])} mods")
    kill_orphan_archivetool()
    return notes


def import_content(game: GamePaths, cfg: dict, out_mod: Path, vanilla_cache: Path) -> List[str]:
    WORK.mkdir(parents=True, exist_ok=True)
    sources = cfg["sources"]
    notes = []
    a, r, k = import_database(game, sources, out_mod / "database", vanilla_cache)
    notes.append(f"{cfg.get('id', 'content')} database: +{a} records, {r} refreshed, {k} campaign records kept")
    n = import_scripts(game, sources, out_mod, cfg.get("scripts", {}))
    notes.append(f"{cfg.get('id', 'content')} scripts: {n} files updated")
    res = import_resources(game, sources, out_mod, cfg.get("resources", {}))
    notes.append(f"{cfg.get('id', 'content')} resources: {res or 'up to date'}")
    kill_orphan_archivetool()
    return notes
