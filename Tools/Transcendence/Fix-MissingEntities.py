#!/usr/bin/env python3
"""Add missing &entity; declarations to Transcendence extension DOCTYPEs."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

CORE = Path(
    r"D:\games\Steam\steamapps\common\Transcendence"
    r"\game_and_dlc_source\TranscendenceDev-integration-API59"
    r"\Transcendence\TransCore"
)
# Also scan DLC / libraries under game_and_dlc_source
GAME_SRC = Path(
    r"D:\games\Steam\steamapps\common\Transcendence\game_and_dlc_source"
)


def _load_remap_module():
    import importlib.util

    path = Path(__file__).with_name("Remap-VanillaDesignTypes.py")
    spec = importlib.util.spec_from_file_location("remap_vanilla_design_types", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_entities() -> tuple[dict[str, str], dict[str, str]]:
    remap = _load_remap_module()
    entity_map = remap.load_vanilla_entities()
    name_remaps = remap.load_name_renames(entity_map)
    # Official source wins; fill gaps from the wider tree in first-seen order.
    for root in (CORE, GAME_SRC):
        if not root.exists():
            continue
        for p in root.rglob("*.xml"):
            text = p.read_text(encoding="utf-8", errors="replace")
            for m in re.finditer(r'<!ENTITY\s+([\w.-]+)\s+"(0x[0-9A-Fa-f]+)"', text):
                entity_map.setdefault(m.group(1), m.group(2))
    return entity_map, name_remaps


def fix_file(
    path: Path,
    entity_map: dict[str, str],
    name_remaps: dict[str, str],
    dry_run: bool,
) -> int:
    text = path.read_text(encoding="utf-8", errors="replace")
    renamed = 0
    items = sorted(name_remaps.items(), key=lambda kv: -len(kv[0]))
    for old, new in items:
        text2, n = re.subn(rf"&{re.escape(old)};", f"&{new};", text)
        if n:
            text = text2
            renamed += n

    m = re.search(r"<!DOCTYPE\s+\w+\s*\[(.*?)\]>", text, flags=re.S)
    if not m:
        if renamed and not dry_run:
            path.write_text(text, encoding="utf-8")
            print(f"{path.name}: remapped {renamed} old type refs (no DOCTYPE)")
            return renamed
        print(f"SKIP (no DOCTYPE): {path}")
        return renamed

    # Transcendence entity names may include hyphens (e.g. scZulu-II)
    # Ignore entities inside XML comments (common DySys pattern)
    doctype_live = re.sub(r"<!--.*?-->", "", m.group(1), flags=re.S)
    declared = set(re.findall(r"<!ENTITY\s+([\w.-]+)\s+", doctype_live))
    used = set(re.findall(r"&([\w.-]+);", text))
    # Built-in XML entities
    used -= {"amp", "lt", "gt", "quot", "apos"}
    missing = sorted(e for e in (used - declared) if e in entity_map)
    unknown = sorted(e for e in (used - declared) if e not in entity_map)
    if not missing:
        if renamed:
            print(f"{path.name}: remapped {renamed} old type refs" + (f"; unknown={unknown}" if unknown else ""))
            if not dry_run:
                path.write_text(text, encoding="utf-8")
            return renamed
        if unknown:
            print(f"{path.name}: no core entities missing; unknown={unknown}")
        return 0

    block = "".join(f'\n\t<!ENTITY {e}\t\t\t\t\t"{entity_map[e]}">' for e in missing)
    # Insert before closing ]>
    insert_at = m.end(1)
    new_text = text[:insert_at] + block + "\n" + text[insert_at:]
    print(
        f"{path.name}: added {len(missing)} entities"
        + (f"; remapped {renamed} old type refs" if renamed else "")
        + (f"; unknown={unknown}" if unknown else "")
    )
    if not dry_run:
        path.write_text(new_text, encoding="utf-8")
    return len(missing) + renamed


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    entity_map, name_remaps = load_entities()
    print(f"Loaded {len(entity_map)} entities from source")
    print(f"Loaded {len(name_remaps)} old->new type remaps")
    total = 0
    for f in args.files:
        total += fix_file(f, entity_map, name_remaps, args.dry_run)
    print(f"Done. added={total}")


if __name__ == "__main__":
    main()
