#!/usr/bin/env python3
"""
Remap stale vanilla design types in extension XML to current official types.

Mods copy Human Space entity names with 1.0-era UNIDs, or keep pre-API54 names.
That shows up as:

  Unknown design type: 1000 / 200004
  Unknown image: 7020
  Cannot inherit from a different type.

What this rewrites:
  1. DTD copies of vanilla *names* whose hex moved (rsItems1 0x00007001 -> 0x0000F11D)
  2. Official old-type *names* from CMPT, Replaces comments, and Compatibility
     header tables (dsLoot -> dsRPGLoot, stCargoCrate -> stGenericCargoCrate,
     itLightTitaniumPlate -> itUltraLightTitaniumArmor)
  3. Quoted hex UNIDs that uniquely match a moved/replaced vanilla type
     (imageID="0x00007020" -> imageID="0x0000F150")

Leaves alone:
  Mod-range UNIDs (>= 0x00800000) so Huari / EP / Near Stars local types stay
  unidPartISystemMap (0x00200004) — still current; EP needs 000_SotPSystemMapStub.xml
  Names listed in SKIP_NAME_REMAP (no 1:1 replacement type)

Usage:
  python Remap-VanillaDesignTypes.py              # dry-run report + refresh VanillaDesignTypeMap.json
  python Remap-VanillaDesignTypes.py --apply --backup
  python Remap-VanillaDesignTypes.py --root PATH --apply
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
from datetime import datetime
from pathlib import Path

GAME_ROOT = Path(r"D:\games\Steam\steamapps\common\Transcendence")
ROOT = GAME_ROOT / "Extensions"
BACKUP_ROOT = GAME_ROOT / "Tools" / "Transcendence" / "_ext_fix_backups"
GAME_SRC = GAME_ROOT / "game_and_dlc_source"

ENTITY_RE = re.compile(
    r'<!ENTITY\s+([\w.-]+)\s+"(0x[0-9A-Fa-f]+)"',
    re.IGNORECASE,
)
ENTITY_DEF_RE = re.compile(
    r'<!ENTITY\s+(\w+)\s+"([^"]+)"\s*>[^\S\n]*(?:<!--\s*(.*?)\s*-->)?',
    re.I,
)
ENTITY_NAME_RE = re.compile(r"^[a-z]{2}[A-Za-z0-9.-]+$")
QUOTED_HEX_RE = re.compile(
    r'\b((?:UNID|unid|imageID|inherit|type|class|ammoID|armorID|deviceID|item|'
    r'dockScreen|abandonedScreen|sovereign|explosionType|ejectaType|'
    r'shipwreckID|backgroundID)=(?:\s*))"(0x[0-9A-Fa-f]+)"',
    re.IGNORECASE,
)

COMPAT_ROW_RE = re.compile(
    r"(?m)^\s+([a-z]{2}[A-Za-z0-9.-]+)\s+\d+\s+([a-z]{2}[A-Za-z0-9.-]+)\s*$"
)

# Confirmed 1.0 resource UNIDs that uniquely moved (not shared with another current type).
KNOWN_UNIQUE_HEX_MOVES = {
    0x00007020: "0x0000F150",  # rsItemsEI1
    0x00007011: "0x0000F11D",  # rsItems1
    0x00007013: "0x0000F158",  # rsItemsNAMI1
}

# Header-table rows the regex can miss, plus HSCompatibility comments with no entity token.
MANUAL_TYPE_RENAMES = {
    "stCargoCrate": "stGenericCargoCrate",
    "stNavSign": "stCommonwealthNavSign",
    "dsCargohold": "dsCargoHold",
}

STALE_COPY_UNID_MAX = 0x00800000

SKIP_DIR_NAMES = {
    "tools",
    ".git",
    "node_modules",
    "__pycache__",
    "collection",
    "_obsolete",
    "_x64_workspace",
    "_ext_fix_backups",
}

SKIP_SUFFIXES = {".bak", ".backup", ".orig", ".tmp", ".disabled"}

CANONICAL_BASENAMES = (
    "CoreTypesLibrary.xml",
    "RPGLibrary.xml",
    "GalaxyLibrary.xml",
    "HuaramarcaLibrary.xml",
    "CorporateHierarchyVol01.xml",
    "HumanSpaceVol01.xml",
)

ALIAS_BASENAMES = {
    "CMPT_API54CompatUNIDsLibrary.xml",
    "CompatibilityLibrary.xml",
}

SKIP_ENTITY_NAMES = {
    "unidExtension",
}

# Names that still exist as aliases at the same UNID; rewrite the *name* only.
SKIP_NAME_REMAP = {
    "dsFleetDockServices",
}

# Keep current: SotP/EP topology overlay (see 000_SotPSystemMapStub.xml).
KEEP_UNIDS = {
    0x00200004,  # unidPartISystemMap
}


def parse_unid(value: str) -> int | None:
    try:
        return int(value, 16)
    except ValueError:
        return None


def format_unid(value: int) -> str:
    return f"0x{value:08X}"


def is_stale_copied_unid(value: int) -> bool:
    return 0 <= value < STALE_COPY_UNID_MAX


def should_skip_xml(path: Path, root: Path) -> bool:
    if path.suffix.lower() != ".xml":
        return True
    lower = path.name.lower()
    if any(lower.endswith(suf) for suf in SKIP_SUFFIXES):
        return True
    try:
        rel_parts = path.relative_to(root).parts
    except ValueError:
        rel_parts = path.parts
    return any(part.lower() in SKIP_DIR_NAMES for part in rel_parts)


def iter_official_xml() -> list[Path]:
    roots = [
        GAME_SRC / "Transcendence_Source",
        GAME_SRC / "CorporateHierarchyVol01_Source",
        GAME_SRC / "CorporateCommand_Source",
    ]
    files: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*.xml"):
            if should_skip_xml(path, root):
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            files.append(path)
    return files


def load_vanilla_entities() -> dict[str, str]:
    """Map entity name -> canonical UNID string (0x........)."""
    general: dict[str, str] = {}
    canonical: dict[str, str] = {}
    aliases: dict[str, str] = {}

    for path in iter_official_xml():
        text = path.read_text(encoding="utf-8", errors="replace")
        target = general
        if path.name in CANONICAL_BASENAMES:
            target = canonical
        elif path.name in ALIAS_BASENAMES:
            target = aliases
        for name, unid in ENTITY_RE.findall(text):
            if name in SKIP_ENTITY_NAMES:
                continue
            n = parse_unid(unid)
            if n is None:
                continue
            target[name] = format_unid(n)

    merged = dict(general)
    merged.update(canonical)
    for name, unid in aliases.items():
        merged.setdefault(name, unid)
    return merged


def load_name_renames(canonical_unids: dict[str, str]) -> dict[str, str]:
    """Legacy entity name -> current name (CMPT, Replaces, Compatibility tables)."""
    old_to_new: dict[str, str] = dict(MANUAL_TYPE_RENAMES)

    for path in iter_official_xml():
        text = path.read_text(encoding="utf-8", errors="replace")
        is_compat = "compat" in path.name.lower()

        for m in ENTITY_DEF_RE.finditer(text):
            name, unid, comment = m.group(1), m.group(2), (m.group(3) or "")
            n = parse_unid(unid)
            if n is not None:
                canonical_unids.setdefault(name, format_unid(n))
            if not comment:
                continue
            low = comment.lower()
            if "replaces" in low:
                after = re.split(r"[Rr]eplaces", comment, maxsplit=1)[1]
                after = after.replace("instead", " ")
                for tok in re.findall(r"\b([a-z]{2}[A-Za-z0-9.-]+)\b", after):
                    if tok != name:
                        old_to_new.setdefault(tok, name)
            elif re.search(r"\buse\b", low) and "instead" in low:
                after = re.split(r"\b[Uu]se\b", comment, maxsplit=1)[1]
                after = after.replace("instead", " ")
                news = re.findall(r"\b([a-z]{2}[A-Za-z0-9.-]+)\b", after)
                if news:
                    old_to_new.setdefault(name, news[0])
            elif path.name in ALIAS_BASENAMES:
                new = comment.split()[0]
                if re.fullmatch(r"[A-Za-z]\w+", new) and new != name:
                    old_to_new.setdefault(name, new)
                    if n is not None:
                        canonical_unids.setdefault(new, format_unid(n))

        if is_compat:
            for old, new in COMPAT_ROW_RE.findall(text):
                if old != new:
                    old_to_new.setdefault(old, new)

    for k in list(old_to_new):
        new = old_to_new[k]
        if k in SKIP_NAME_REMAP or new == k:
            old_to_new.pop(k, None)
            continue
        if not ENTITY_NAME_RE.fullmatch(k) or not ENTITY_NAME_RE.fullmatch(new):
            old_to_new.pop(k, None)
    return old_to_new


def vanilla_by_lower(vanilla: dict[str, str]) -> dict[str, str]:
    """lowercase name -> unique official spelling. Drops collisions."""
    out: dict[str, str] = {}
    ambig: set[str] = set()
    for name in vanilla:
        key = name.lower()
        if key in out and out[key] != name:
            ambig.add(key)
        else:
            out[key] = name
    for key in ambig:
        out.pop(key, None)
    return out


def collect_case_aliases(root: Path, vanilla: dict[str, str]) -> dict[str, str]:
    """DTD / &ref; spellings that match exactly one official name, ignoring case."""
    by_lower = vanilla_by_lower(vanilla)
    aliases: dict[str, str] = {}
    ref_re = re.compile(r"&([\w.-]+);")
    for path in root.rglob("*.xml"):
        if should_skip_xml(path, root):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        names = set(name for name, _ in ENTITY_RE.findall(text))
        names.update(ref_re.findall(text))
        for name in names:
            if name in vanilla or name in SKIP_ENTITY_NAMES:
                continue
            canon = by_lower.get(name.lower())
            if canon and canon != name:
                aliases[name] = canon
    return aliases
    return old_to_new


def hex_moves_from_renames(
    old_to_new: dict[str, str], vanilla: dict[str, str]
) -> dict[int, str]:
    """old numeric UNID -> unique current hex, from replaced types with different UNIDs."""
    votes: dict[int, set[str]] = {}
    for old, new in old_to_new.items():
        if old not in vanilla or new not in vanilla:
            continue
        old_n = parse_unid(vanilla[old])
        new_s = vanilla[new]
        new_n = parse_unid(new_s)
        if old_n is None or new_n is None or old_n == new_n:
            continue
        if old_n in KEEP_UNIDS or new_n in KEEP_UNIDS:
            continue
        if not is_stale_copied_unid(old_n):
            continue
        votes.setdefault(old_n, set()).add(new_s)
    return {k: next(iter(v)) for k, v in votes.items() if len(v) == 1}


def remap_dtd_unids(text: str, vanilla: dict[str, str]) -> tuple[str, list[dict[str, str]]]:
    out: list[str] = []
    last = 0
    changes: list[dict[str, str]] = []
    for m in ENTITY_RE.finditer(text):
        name, old = m.group(1), m.group(2)
        if name not in vanilla or name in SKIP_ENTITY_NAMES:
            continue
        new = vanilla[name]
        old_n = parse_unid(old)
        new_n = parse_unid(new)
        if old_n is None or new_n is None or old_n == new_n:
            continue
        if old_n in KEEP_UNIDS or new_n in KEEP_UNIDS:
            continue
        if not is_stale_copied_unid(old_n):
            continue
        out.append(text[last : m.start(2)])
        out.append(new)
        last = m.end(2)
        changes.append(
            {
                "kind": "dtd-unid",
                "entity": name,
                "old": format_unid(old_n),
                "new": new,
                "reason": f"{name} official UNID moved",
            }
        )
    if not changes:
        return text, []
    out.append(text[last:])
    return "".join(out), changes


def local_entity_unids(text: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for name, unid in ENTITY_RE.findall(text):
        n = parse_unid(unid)
        if n is not None:
            out[name] = n
    return out


def remap_names(text: str, old_to_new: dict[str, str], canonical_unids: dict[str, str]) -> tuple[str, list[dict[str, str]]]:
    changes: list[dict[str, str]] = []
    locals_ = local_entity_unids(text)
    items = sorted(old_to_new.items(), key=lambda kv: -len(kv[0]))
    for old, new in items:
        local_unid = locals_.get(old)
        if local_unid is not None and local_unid >= STALE_COPY_UNID_MAX:
            continue
        pat_ref = re.compile(rf"&{re.escape(old)};")
        text2, n = pat_ref.subn(f"&{new};", text)
        if n:
            text = text2
            changes.append(
                {
                    "kind": "name-ref",
                    "entity": old,
                    "old": f"&{old};",
                    "new": f"&{new};",
                    "reason": f"API54 name {old} -> {new} (x{n})",
                }
            )

        def repl_ent(m: re.Match[str]) -> str:
            unid = m.group(1)
            if new in canonical_unids:
                unid = canonical_unids[new]
            return f'<!ENTITY {new}\t\t\t"{unid}">'

        pat_ent = re.compile(rf'<!ENTITY\s+{re.escape(old)}\s+"([^"]+)"\s*>', re.I)
        text2, n = pat_ent.subn(repl_ent, text)
        if n:
            text = text2
            changes.append(
                {
                    "kind": "name-dtd",
                    "entity": old,
                    "old": old,
                    "new": new,
                    "reason": f"ENTITY {old} -> {new}",
                }
            )
    return text, changes


def collect_unique_hex_moves(
    root: Path, vanilla: dict[str, str], old_to_new: dict[str, str]
) -> dict[int, str]:
    """old numeric UNID -> unique current hex, from DTD mismatches and type replacements."""
    votes: dict[int, set[str]] = {}
    for path in root.rglob("*.xml"):
        if should_skip_xml(path, root):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for name, old in ENTITY_RE.findall(text):
            if name not in vanilla:
                continue
            old_n = parse_unid(old)
            new_n = parse_unid(vanilla[name])
            if old_n is None or new_n is None or old_n == new_n:
                continue
            if old_n in KEEP_UNIDS:
                continue
            if not is_stale_copied_unid(old_n):
                continue
            votes.setdefault(old_n, set()).add(vanilla[name])
    merged = {k: next(iter(v)) for k, v in votes.items() if len(v) == 1}
    merged.update(hex_moves_from_renames(old_to_new, vanilla))
    for old_n, new in KNOWN_UNIQUE_HEX_MOVES.items():
        if old_n in KEEP_UNIDS:
            continue
        merged.setdefault(old_n, new)
    return merged


def remap_quoted_hex(text: str, hex_map: dict[int, str]) -> tuple[str, list[dict[str, str]]]:
    if not hex_map:
        return text, []
    changes: list[dict[str, str]] = []

    def repl(m: re.Match[str]) -> str:
        prefix, old = m.group(1), m.group(2)
        old_n = parse_unid(old)
        if old_n is None or old_n not in hex_map:
            return m.group(0)
        new = hex_map[old_n]
        if format_unid(old_n) == new:
            return m.group(0)
        changes.append(
            {
                "kind": "attr-unid",
                "entity": prefix.split("=")[0],
                "old": format_unid(old_n),
                "new": new,
                "reason": f"quoted UNID {format_unid(old_n)} -> {new}",
            }
        )
        return f'{prefix}"{new}"'

    return QUOTED_HEX_RE.sub(repl, text), changes


def remap_text(
    text: str,
    vanilla: dict[str, str],
    old_to_new: dict[str, str],
    hex_map: dict[int, str],
) -> tuple[str, list[dict[str, str]]]:
    all_changes: list[dict[str, str]] = []
    text, c = remap_names(text, old_to_new, vanilla)
    all_changes.extend(c)
    text, c = remap_dtd_unids(text, vanilla)
    all_changes.extend(c)
    text, c = remap_quoted_hex(text, hex_map)
    all_changes.extend(c)
    return text, all_changes


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--root", default=str(ROOT), help="Extensions root to scan")
    ap.add_argument("--apply", action="store_true", help="Write changes (default is dry-run)")
    ap.add_argument("--backup", action="store_true", help="Copy originals under _ext_fix_backups before write")
    ap.add_argument("--csv", default="", help="Optional path for change report CSV")
    ap.add_argument("--dump-map", default="", help="Write the loaded vanilla name->UNID map to this CSV")
    ap.add_argument(
        "--dump-json",
        default="",
        help="Write VanillaDesignTypeMap.json (unids + name remaps) for the rest of the toolset",
    )
    args = ap.parse_args()

    vanilla = load_vanilla_entities()
    old_to_new = load_name_renames(vanilla)
    root = Path(args.root)
    case_aliases = collect_case_aliases(root, vanilla)
    for old, new in case_aliases.items():
        old_to_new.setdefault(old, new)
    hex_map = collect_unique_hex_moves(root, vanilla, old_to_new)
    print(f"Loaded {len(vanilla)} official entity names")
    print(f"Loaded {len(old_to_new)} official old->new type remaps")
    print(f"Case/spelling aliases from mods: {len(case_aliases)}")
    print(f"Unique stale hex moves: {len(hex_map)}")

    emitted_unids = dict(vanilla)
    for old, new in old_to_new.items():
        if new in vanilla:
            emitted_unids[old] = vanilla[new]

    json_path = Path(args.dump_json) if args.dump_json else Path(__file__).with_name(
        "VanillaDesignTypeMap.json"
    )
    json_payload = {
        "unids": {k: emitted_unids[k] for k in sorted(emitted_unids)},
        "nameRemaps": {k: old_to_new[k] for k in sorted(old_to_new)},
        "hexRemaps": {format_unid(k): hex_map[k] for k in sorted(hex_map)},
        "keepUnids": [format_unid(n) for n in sorted(KEEP_UNIDS)],
    }
    json_path.write_text(json.dumps(json_payload, indent=2) + "\n", encoding="utf-8")
    print(f"Type map: {json_path}")

    if args.dump_map:
        dump_path = Path(args.dump_map)
        with dump_path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(["kind", "old", "new"])
            for name in sorted(vanilla):
                writer.writerow(["unid", name, vanilla[name]])
            for old in sorted(old_to_new):
                writer.writerow(["name", old, old_to_new[old]])
            for old_n in sorted(hex_map):
                writer.writerow(["hex", format_unid(old_n), hex_map[old_n]])
        print(f"Vanilla map: {dump_path}")

    apply = args.apply
    backup_dir = None
    if apply and args.backup:
        backup_dir = BACKUP_ROOT / f"vanilla_unid_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    files_touched = 0
    replacements = 0
    report_rows: list[dict[str, str]] = []

    for path in sorted(root.rglob("*.xml")):
        if should_skip_xml(path, root):
            continue
        raw = path.read_text(encoding="utf-8", errors="replace")
        new_text, changes = remap_text(raw, vanilla, old_to_new, hex_map)
        if not changes:
            continue

        files_touched += 1
        replacements += len(changes)
        rel = str(path.relative_to(root)) if path.is_relative_to(root) else str(path)
        print(f"\n{rel}")
        for c in changes:
            print(f"  [{c['kind']}] {c['old']} -> {c['new']}  ({c['reason']})")
            report_rows.append({"file": rel, **c})

        if apply:
            if backup_dir is not None:
                dest = backup_dir / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, dest)
            path.write_text(new_text, encoding="utf-8", newline="")

    mode = "APPLIED" if apply else "DRY-RUN"
    print(f"\n[{mode}] {replacements} replacement(s) in {files_touched} file(s)")
    if backup_dir is not None:
        print(f"Backups: {backup_dir}")

    csv_path = Path(args.csv) if args.csv else None
    if csv_path is None and report_rows:
        csv_path = Path(__file__).with_name(
            f"vanilla_unid_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
    if csv_path and report_rows:
        with csv_path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(
                fh, fieldnames=["file", "kind", "entity", "old", "new", "reason"]
            )
            writer.writeheader()
            writer.writerows(report_rows)
        print(f"Report: {csv_path}")


if __name__ == "__main__":
    main()
