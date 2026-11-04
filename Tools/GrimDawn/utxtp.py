#!/usr/bin/env python3
"""
Native uTXTp ("User Text Patch") engine -- the GD-DPS patch format, applied by this toolkit.

Changes live as small declarative patch files instead of edited records, so after a game
patch or mod update the build re-extracts fresh data and simply re-applies them. Any patch
written for GD-DPS works here, and vice versa (see the GD-DPS readme for the format):

    [
        <File  = Database\\records\\creatures\\pc\\playerlevels.dbr>
        <Entry = maxDevotionPoints>
        <Data  = 200>
        <Priority = 7000>            // optional, compared as text like GD-DPS
        <Type = Update>              // U/Update (default), I/Insert Only, R/Replace Only
        <AppendAsMultiRecord = -1>   // optional: insert Data into a ';' list (0 start, -1 end, n)
    ]

Data NULL removes the entry. File paths:
    Database\\records\\...                     -> the build's record; if the build doesn't override it,
                                                 the highest official layer (gdxN > ... > base) is copied in
    Source\\GDX0|GDX1..N|SM0..N\\database\\...   -> that official layer explicitly (SMn = Crucible layer n)
    Source\\MODs\\<mod>\\database\\records\\...  -> that mod's record (applied to the build's copy)

Patched records are written into the target (unpacked) mod database only; the game
install is never modified.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

TOOLS_DIR = Path(__file__).resolve().parent
DEFAULT_PATCH_DIR = TOOLS_DIR / "patches"
DEFAULT_PRIORITY = "5000"  # above GD-DPS MOD scripts, inside the documented 1000-9999 range

_COMMENT_RE = re.compile(r"//[^\n]*")
_BLOCK_RE = re.compile(r"\[(.*?)\]", re.S)
_SECTION_RE = re.compile(r"<\s*([A-Za-z]+)\s*=(.*?)>", re.S)


@dataclass
class Patch:
    files: List[str]
    entries: List[str]
    data: List[str]
    priority: str = DEFAULT_PRIORITY
    type: str = "U"
    multi: Optional[int] = None
    source: str = ""
    order: int = 0


@dataclass
class ApplyReport:
    applied: List[str] = field(default_factory=list)
    skipped: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"uTXTp: {len(self.applied)} record edits, {len(self.skipped)} skipped, "
            f"{len(self.errors)} errors"
        )


def _split(value: str) -> List[str]:
    return [v.strip() for v in value.split(",")]


def parse_text(text: str, source: str = "") -> List[Patch]:
    text = _COMMENT_RE.sub("", text)
    out: List[Patch] = []
    for i, block in enumerate(_BLOCK_RE.findall(text)):
        sec: Dict[str, str] = {}
        for name, value in _SECTION_RE.findall(block):
            sec[name.strip().lower()] = value
        if not all(k in sec for k in ("file", "entry", "data")):
            continue  # free text between blocks is allowed; only complete blocks count
        entries, data = _split(sec["entry"]), _split(sec["data"])
        if len(entries) != len(data):
            raise ValueError(f"{source} block {i + 1}: {len(entries)} Entry vs {len(data)} Data")
        t = (sec.get("type") or "U").strip().upper()[:1] or "U"
        multi_raw = (sec.get("appendasmultirecord") or "No").strip()
        multi = None if multi_raw.lower() in ("", "no") else int(multi_raw)
        out.append(
            Patch(
                files=[f for f in _split(sec["file"]) if f],
                entries=entries,
                data=data,
                priority=(sec.get("priority") or DEFAULT_PRIORITY).strip(),
                type=t if t in "UIR" else "U",
                multi=multi,
                source=source,
            )
        )
    return out


def load_patches(paths: Iterable[Path]) -> List[Patch]:
    """Load *.txt patch files (directories: top level only, like GD-DPS 'User Text Patch')."""
    patches: List[Patch] = []
    files: List[Path] = []
    for p in paths:
        p = Path(p)
        if p.is_dir():
            files.extend(sorted(x for x in p.glob("*.txt") if x.is_file()))
        elif p.is_file():
            files.append(p)
    for f in files:
        text = f.read_text(encoding="latin-1")
        patches.extend(parse_text(text, f.name))
    for i, p in enumerate(patches):
        p.order = i
    # GD-DPS compares priorities as text; higher applies later so it wins
    return sorted(patches, key=lambda p: (p.priority, p.order))


def patch_fingerprint(paths: Iterable[Path]) -> str:
    h = hashlib.sha1()
    for p in paths:
        p = Path(p)
        for f in sorted(p.glob("*.txt")) if p.is_dir() else [p]:
            if f.is_file():
                h.update(f.name.encode())
                h.update(f.read_bytes())
    return h.hexdigest()[:16]


# ---------------------------------------------------------------- record editing (ANSI, keep order)

def _read_lines(path: Path) -> List[str]:
    return path.read_bytes().decode("latin-1").split("\n")


def _write_lines(path: Path, lines: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes("\n".join(lines).encode("latin-1"))


def _find(lines: List[str], entry: str) -> int:
    prefix = entry + ","
    for i, line in enumerate(lines):
        if line.startswith(prefix):
            return i
    return -1


def _insert_multi(current: str, data: str, pos: int) -> str:
    items = [x for x in current.split(";") if x != ""]
    new = [x for x in data.split(";") if x != ""]
    if pos == -1 or pos >= len(items):
        items.extend(new)
    else:
        items[max(pos, 0):max(pos, 0)] = new
    return ";".join(items)


def edit_record(path: Path, patch: Patch) -> List[str]:
    """Apply one patch block to one record; returns human-readable changes."""
    lines = _read_lines(path)
    changes: List[str] = []
    for entry, data in zip(patch.entries, patch.data):
        idx = _find(lines, entry)
        if data.upper() == "NULL":
            if idx >= 0:
                del lines[idx]
                changes.append(f"-{entry}")
            continue
        if idx < 0:
            if patch.type == "R":
                continue
            value = data
            # insert before the trailing blank line if there is one
            at = len(lines) - 1 if lines and lines[-1] == "" else len(lines)
            lines.insert(at, f"{entry},{value},")
            changes.append(f"+{entry}={value}")
            continue
        if patch.type == "I":
            continue
        old = lines[idx][len(entry) + 1 :]
        old = old[:-1] if old.endswith(",") else old
        value = _insert_multi(old, data, patch.multi) if patch.multi is not None else data
        if value != old:
            lines[idx] = f"{entry},{value},"
            changes.append(f"{entry}: {old} -> {value}")
    if changes:
        _write_lines(path, lines)
    return changes


# ---------------------------------------------------------------- path resolution

def _layer_key(name: str) -> Tuple[str, int]:
    m = re.fullmatch(r"(gdx|sm)(\d+)", name.lower())
    return (m.group(1), int(m.group(2))) if m else ("", -1)


def _norm_rel(rest: str) -> str:
    return "records/" + rest[8:] if rest.lower().startswith("records/") else rest


def resolve_record(
    file_spec: str,
    target_db: Path,
    official_layers: Dict[str, Path],
    mod_dbs: Dict[str, Path],
) -> Tuple[Optional[Path], Optional[Path], str]:
    """Return (target record path, source to copy from if missing, label)."""
    target, src, label = _resolve(file_spec, target_db, official_layers, mod_dbs)
    if target is not None:
        target = target_db / _norm_rel(target.relative_to(target_db).as_posix())
    return target, src, label


def _resolve(
    file_spec: str,
    target_db: Path,
    official_layers: Dict[str, Path],
    mod_dbs: Dict[str, Path],
) -> Tuple[Optional[Path], Optional[Path], str]:
    spec = file_spec.strip().replace("\\", "/").strip("/")
    low = spec.lower()
    explicit_src: Optional[Path] = None
    if low.startswith("source/mods/"):
        parts = spec.split("/")
        mod = parts[2]
        rest = "/".join(parts[3:])
        if rest.lower().startswith("database/"):
            rest = rest[len("database/"):]
        match = next((v for k, v in mod_dbs.items() if k.lower() == mod.lower()), None)
        target = target_db / rest
        if not target.is_file() and match and (match / rest).is_file():
            explicit_src = match / rest
        return target, explicit_src, f"MOD {mod}"
    if low.startswith("source/"):
        parts = spec.split("/")
        layer = parts[1].lower()
        rest = "/".join(parts[2:])
        if rest.lower().startswith("database/"):
            rest = rest[len("database/"):]
        root = official_layers.get("database" if layer in ("gdx0",) else layer)
        return target_db / rest, (root / rest if root else None), parts[1].upper()
    rest = spec[len("database/"):] if low.startswith("database/") else spec
    return target_db / rest, None, "auto"


def official_layer_roots(vanilla_cache: Path, game_dir: Optional[Path] = None) -> Dict[str, Path]:
    """Map gdx0/database, gdx1.., sm1.. to extracted roots (cache built by CompatEngine)."""
    roots: Dict[str, Path] = {}
    layers = Path(vanilla_cache) / "layers"
    if layers.is_dir():
        for d in layers.iterdir():
            if d.is_dir():
                name = d.name.lower()
                roots[name] = d
                m = re.fullmatch(r"survivalmode(\d+)", name)
                if m:
                    roots[f"sm{m.group(1)}"] = d
    if "database" in roots:
        roots["gdx0"] = roots["database"]
    return roots


def highest_official(rel: str, roots: Dict[str, Path]) -> Optional[Path]:
    gdx = sorted((k for k in roots if _layer_key(k)[0] == "gdx"), key=lambda k: _layer_key(k)[1], reverse=True)
    for key in gdx:
        cand = roots[key] / rel
        if cand.is_file():
            return cand
    return None


def apply_patches(
    target_db: Path,
    patches: Sequence[Patch],
    *,
    vanilla_cache: Path = TOOLS_DIR / "work" / "_vanilla_cache",
    mod_dbs: Optional[Dict[str, Path]] = None,
    dry_run: bool = False,
) -> ApplyReport:
    """Apply patches to an unpacked mod database (copying official records in as overrides)."""
    report = ApplyReport()
    roots = official_layer_roots(vanilla_cache)
    mod_dbs = mod_dbs or {}
    for patch in patches:
        for spec in patch.files:
            target, src, label = resolve_record(spec, target_db, roots, mod_dbs)
            if target is None:
                report.skipped.append(f"{patch.source}: {spec} (unresolved)")
                continue
            rel = target.relative_to(target_db).as_posix()
            if src is not None and label not in ("auto",) and not label.startswith("MOD"):
                # Explicit official layer: start from that layer's version
                if not src.is_file():
                    report.skipped.append(f"{patch.source}: {spec} (not in {label})")
                    continue
                if not dry_run:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(src.read_bytes())
            elif not target.is_file():
                src = src if (src and src.is_file()) else (None if label.startswith("MOD") else highest_official(rel, roots))
                if src is None:
                    report.skipped.append(f"{patch.source}: {spec} (record not in build)")
                    continue
                if not dry_run:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(src.read_bytes())
            if dry_run:
                report.applied.append(f"{patch.source}: {rel} (dry run)")
                continue
            try:
                changes = edit_record(target, patch)
            except Exception as exc:
                report.errors.append(f"{patch.source}: {rel}: {exc}")
                continue
            if changes:
                report.applied.append(f"{patch.source}: {rel}: {'; '.join(changes)}")
    return report


def find_gd_dps_dirs(game_dir: Path) -> List[Path]:
    """GD-DPS 'User Text Patch' folders (in mods/ distributions or installed at the game root)."""
    out: List[Path] = []
    for base in [Path(game_dir), *sorted((Path(game_dir) / "mods").glob("GD-DPS*"))]:
        utp = base / "User Text Patch"
        if utp.is_dir():
            out.append(utp)
    return out


def default_patch_dirs(game_dir: Optional[Path], *, include_gd_dps: bool = True) -> List[Path]:
    dirs = [DEFAULT_PATCH_DIR] if DEFAULT_PATCH_DIR.is_dir() else []
    if include_gd_dps and game_dir:
        dirs.extend(find_gd_dps_dirs(Path(game_dir)))
    return dirs


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Apply uTXTp (GD-DPS format) patches to an unpacked mod")
    p.add_argument("--mod-db", required=True, help="Unpacked database folder (mods/<name>/database)")
    p.add_argument("--patches", nargs="*", default=None, help="Patch files/folders (default: patches/ + GD-DPS User Text Patch)")
    p.add_argument("--game", default=None)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--list", action="store_true", help="Only parse and list patches")
    args = p.parse_args(argv)

    from gd_paths import resolve_game_dir

    game = resolve_game_dir(args.game)
    dirs = [Path(x) for x in args.patches] if args.patches is not None else default_patch_dirs(game)
    patches = load_patches(dirs)
    print(f"Loaded {len(patches)} patch blocks from {[str(d) for d in dirs]}")
    if args.list:
        for pt in patches:
            print(f"  [{pt.priority}] {pt.source}: {pt.files[0]}{' +' + str(len(pt.files) - 1) if len(pt.files) > 1 else ''} {pt.entries}")
        return 0
    report = apply_patches(Path(args.mod_db), patches, dry_run=args.dry_run)
    for line in report.applied[:200]:
        print("  " + line)
    for line in report.skipped[:50]:
        print("  skip " + line)
    for line in report.errors:
        print("  ERROR " + line, file=sys.stderr)
    print(report.summary())
    return 1 if report.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
