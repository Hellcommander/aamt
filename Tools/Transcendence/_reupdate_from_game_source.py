#!/usr/bin/env python3
"""
Reupdate Extensions from official game data sources:
  Transcendence_Source, CorporateCommand_Source, CorporateHierarchyVol01_Source,
  CorporateHierarchyVol1UNIDs_Source, StarsOfThePilgrimHD_Source,
  StarsOfThePilgrimSoundtrack_Source

Applies entity renames / canonical UNIDs that those sources define but
extensions still lack (API54+ renames, HSCompatibility type swaps, etc.).
"""
from __future__ import annotations

import os
import re
import shutil
from collections import defaultdict
from datetime import datetime
from pathlib import Path

GAME_DLC = Path(r"D:\games\Steam\steamapps\common\Transcendence\game_and_dlc_source")
EXT_ROOT = Path(r"D:\games\Steam\steamapps\common\Transcendence\Extensions")
BACKUP_DIR = (
    Path(r"D:\games\Steam\steamapps\common\Transcendence\Tools\Transcendence\_ext_fix_backups")
    / f"gamesource_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
)

SOURCE_FOLDERS = [
    "Transcendence_Source",
    "CorporateCommand_Source",
    "CorporateHierarchyVol01_Source",
    "CorporateHierarchyVol1UNIDs_Source",
    "StarsOfThePilgrimHD_Source",
    "StarsOfThePilgrimSoundtrack_Source",
]

TARGET_API = "59"

# Manual HSCompatibility / header table renames (old -> new)
MANUAL_TYPE_RENAMES = {
    "stCargoCrate": "stGenericCargoCrate",
    "stNavSign": "stCommonwealthNavSign",
    # dsFleetDockServices -> use rpgDockServices; leave name alone (behavioral, not entity)
}

# Do not rewrite these even if they appear as "old" (keep as-is / ambiguous)
SKIP_OLD = {
    "dsFleetDockServices",
}

ENTITY_DEF_RE = re.compile(
    r'<!ENTITY\s+(\w+)\s+"([^"]+)"\s*>\s*(?:<!--\s*(.*?)\s*-->)?',
    re.I,
)
REPLACES_RE = re.compile(
    r"(?:[Rr]eplaces|[Rr]eplace[sd]?|[Uu]se)\s+([A-Za-z][\w]*(?:\s+[A-Za-z][\w]*)*)",
)
API_RE = re.compile(r'apiVersion\s*=\s*["\']([^"\']+)["\']', re.I)
ROOT_TAG_RE = re.compile(
    r"<(Transcendence(?:Extension|Adventure|Library|Module))\b([^>]*?)(/?)>",
    re.I | re.S,
)

SKIP_DIRS = {"tools", ".git", "node_modules", "__pycache__", ".vscode", "_ext_fix_backups"}


def _load_remap_module():
    import importlib.util

    path = Path(__file__).with_name("Remap-VanillaDesignTypes.py")
    spec = importlib.util.spec_from_file_location("remap_vanilla_design_types", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def parse_renames_from_sources() -> tuple[dict[str, str], dict[str, str]]:
    """Delegate to Remap-VanillaDesignTypes.py (Compatibility tables + CMPT + Replaces)."""
    remap = _load_remap_module()
    canonical_unids = remap.load_vanilla_entities()
    old_to_new = remap.load_name_renames(canonical_unids)
    for k in list(old_to_new):
        if k in SKIP_OLD or old_to_new[k] == k:
            old_to_new.pop(k, None)
    return old_to_new, canonical_unids


def backup_file(path: Path) -> None:
    rel = path.relative_to(EXT_ROOT)
    dest = BACKUP_DIR / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dest)


def ensure_api59(text: str) -> tuple[str, bool]:
    m = ROOT_TAG_RE.search(text)
    if not m:
        return text, False
    attrs = m.group(2)
    am = API_RE.search(attrs)
    if am and am.group(1) == TARGET_API:
        return text, False
    if am:
        new_attrs = API_RE.sub(f'apiVersion="{TARGET_API}"', attrs, count=1)
    else:
        insert = f'\n\tapiVersion="{TARGET_API}"'
        if "\n" in attrs:
            head, rest = attrs.split("\n", 1)
            new_attrs = head + insert + "\n" + rest
        else:
            if attrs and not attrs[:1].isspace():
                attrs = " " + attrs
            new_attrs = insert + attrs
    new_tag = f"<{m.group(1)}{new_attrs}{m.group(3)}>"
    return text[: m.start()] + new_tag + text[m.end() :], True


def apply_renames(text: str, old_to_new: dict[str, str], canonical_unids: dict[str, str]) -> tuple[str, list[str]]:
    notes: list[str] = []
    # Sort longer names first to avoid partial collisions
    items = sorted(old_to_new.items(), key=lambda kv: -len(kv[0]))

    for old, new in items:
        # Entity refs &old; -> &new;
        pat_ref = re.compile(rf"&{re.escape(old)};")
        text2, n = pat_ref.subn(f"&{new};", text)
        if n:
            text = text2
            notes.append(f"&{old}; -> &{new}; (x{n})")

        # DOCTYPE entity definitions: rename old entity to new (keep UNID if present)
        def repl_ent(m: re.Match) -> str:
            unid = m.group(1)
            # Prefer canonical UNID from game source when available
            if new in canonical_unids:
                unid = canonical_unids[new]
            return f'<!ENTITY {new}\t\t\t"{unid}">'

        pat_ent = re.compile(
            rf'<!ENTITY\s+{re.escape(old)}\s+"([^"]+)"\s*>',
            re.I,
        )
        text2, n = pat_ent.subn(repl_ent, text)
        if n:
            text = text2
            notes.append(f"ENTITY {old} -> {new} (x{n})")

    return text, notes


def main() -> None:
    print("Parsing game source renames...")
    old_to_new, canonical_unids = parse_renames_from_sources()
    print(f"  rename map entries: {len(old_to_new)}")
    print(f"  canonical UNIDs: {len(canonical_unids)}")
    # Show a sample of the most relevant
    for old in sorted(old_to_new)[:25]:
        print(f"    {old} -> {old_to_new[old]}")
    if len(old_to_new) > 25:
        print(f"    ... +{len(old_to_new) - 25} more")

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\nBackups -> {BACKUP_DIR}")

    changed_files = 0
    total_notes = 0
    hit_counts: dict[str, int] = defaultdict(int)

    for dirpath, dirs, files in os.walk(EXT_ROOT):
        dirs[:] = [d for d in dirs if d.lower() not in SKIP_DIRS]
        for fn in files:
            if not fn.lower().endswith(".xml"):
                continue
            path = Path(dirpath) / fn
            try:
                raw = path.read_bytes()
            except OSError:
                continue
            if not raw.lstrip().startswith((b"<?xml", b"<!", b"<Transcendence", b"\xef\xbb\xbf")):
                continue
            text = raw.decode("utf-8-sig")
            original = text

            text, notes = apply_renames(text, old_to_new, canonical_unids)
            text, api_changed = ensure_api59(text)
            if api_changed:
                notes.append(f"apiVersion -> {TARGET_API}")

            if text == original:
                continue

            backup_file(path)
            nl = "\r\n" if "\r\n" in original else "\n"
            out = text.replace("\r\n", "\n").replace("\r", "\n")
            if nl != "\n":
                out = out.replace("\n", nl)
            path.write_bytes(out.encode("utf-8"))
            changed_files += 1
            total_notes += len(notes)
            rel = str(path.relative_to(EXT_ROOT))
            print(f"UPDATED: {rel}")
            for n in notes[:8]:
                print(f"         - {n}")
                # tally rename kinds
                if "->" in n and "&" in n:
                    hit_counts[n.split("(x")[0].strip()] += 1
            if len(notes) > 8:
                print(f"         - ... +{len(notes) - 8} more")

    print()
    print(f"Files updated: {changed_files}")
    print(f"Fix notes: {total_notes}")
    if hit_counts:
        print("Top renames applied:")
        for k, v in sorted(hit_counts.items(), key=lambda kv: -kv[1])[:20]:
            print(f"  {v:4d}  {k}")


if __name__ == "__main__":
    main()
