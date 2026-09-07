#!/usr/bin/env python3
"""Fix API 59 debug bind warnings in Extensions XML.

Handles:
- repeatingDelay=N  -> repeatingShotDelay=(N+2)
- fireRate too short for repeating volleys
  volley seconds = repeating * (shotDelay + 1)
  default shotDelay is 2 when neither delay attribute is set
- maxArmor class smaller than installed armor mass
  ultraLight=1t light=2.5 medium=3.5 heavy=6 superHeavy=9
  massive=12 superMassive=100 maximum=1e6

Also reports:
- remaining repeatingDelay in .tdb files (string search)
- <Uses unid="0x00200004"> / unidPartISystemMap (SotP map missing in EP)

Official Kronosaur trees are not touched. Use --root to scan another tree.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(r"D:\games\Steam\steamapps\common\Transcendence\Extensions")
GAME = Path(r"D:\games\Steam\steamapps\common\Transcendence")

ARMOR_CLASS_TONS = [
    ("ultraLight", 1.0),
    ("light", 2.5),
    ("medium", 3.5),
    ("heavy", 6.0),
    ("superHeavy", 9.0),
    ("massive", 12.0),
    ("superMassive", 100.0),
    ("maximum", 1_000_000.0),
]
CLASS_INDEX = {name: i for i, (name, _) in enumerate(ARMOR_CLASS_TONS)}
CLASS_TONS = {name: tons for name, tons in ARMOR_CLASS_TONS}

SKIP_DIR_PARTS = {
    ".bak",
    "_ext_fix_backups",
    "backup",
}

ENTITY_RE = re.compile(
    r'<!ENTITY\s+(\w+)\s+"([^"]+)"',
    re.I,
)
ITEM_MASS_RE = re.compile(
    r'<ItemType\b([^>]*?UNID\s*=\s*"([^"]+)"[^>]*?)>(.*?)</ItemType>',
    re.I | re.S,
)
ATTR_RE = re.compile(r'\b(\w+)\s*=\s*"([^"]*)"')
WEAPON_TAG_RE = re.compile(
    r"<(Weapon|Variant)\b([^>]*?)(/?)>",
    re.I | re.S,
)
MAX_ARMOR_RE = re.compile(r'\bmaxArmor\s*=\s*"([^"]+)"', re.I)
ARMOR_ID_RE = re.compile(r'<Armor\b[^>]*\barmorID\s*=\s*"([^"]+)"', re.I)
SHIP_CLASS_RE = re.compile(
    r"<ShipClass\b([^>]*?)>(.*?)</ShipClass>",
    re.I | re.S,
)


def skip_path(path: Path) -> bool:
    parts = {p.lower() for p in path.parts}
    if parts & SKIP_DIR_PARTS:
        return True
    if path.name.endswith((".bak", ".backup")):
        return True
    return False


def parse_attrs(blob: str) -> dict[str, str]:
    return {k: v for k, v in ATTR_RE.findall(blob)}


def class_for_tons(tons: float) -> str:
    for name, size in ARMOR_CLASS_TONS:
        if tons <= size:
            return name
    return "maximum"


def volley_seconds(attrs: dict[str, str]) -> tuple[float, float] | None:
    repeating = attrs.get("repeating")
    fire_rate = attrs.get("fireRate")
    if repeating is None or fire_rate is None:
        return None
    try:
        n = float(repeating)
        fire = float(fire_rate)
    except ValueError:
        return None
    if n <= 0:
        return None
    if "repeatingShotDelay" in attrs:
        delay = float(attrs["repeatingShotDelay"])
    elif "repeatingDelay" in attrs:
        delay = float(attrs["repeatingDelay"]) + 2.0
    else:
        delay = 2.0
    return n * (delay + 1.0), fire


def convert_repeating_delay(text: str) -> tuple[str, int]:
    count = 0

    def repl(m: re.Match[str]) -> str:
        nonlocal count
        count += 1
        return f'{m.group(1)}repeatingShotDelay="{int(m.group(2)) + 2}"'

    new = re.sub(r'(\b)repeatingDelay\s*=\s*"(\d+(?:\.\d+)?)"', repl, text)
    return new, count


def bump_fire_rates(text: str) -> tuple[str, int]:
    count = 0

    def repl(m: re.Match[str]) -> str:
        nonlocal count
        attrs_blob = m.group(2)
        attrs = parse_attrs(attrs_blob)
        result = volley_seconds(attrs)
        if not result:
            return m.group(0)
        needed, fire = result
        if needed <= fire:
            return m.group(0)
        new_rate = str(int(needed) if needed == int(needed) else needed)
        count += 1
        new_blob = re.sub(
            r'\bfireRate\s*=\s*"[^"]*"',
            f'fireRate="{new_rate}"',
            attrs_blob,
            count=1,
        )
        slash = m.group(3)
        return f"<{m.group(1)}{new_blob}{slash}>"

    return WEAPON_TAG_RE.sub(repl, text), count


def index_entities_and_mass(files: list[Path]) -> tuple[dict[str, str], dict[str, float]]:
    entities: dict[str, str] = {}
    mass_by_unid: dict[str, float] = {}
    for path in files:
        raw = path.read_text(encoding="utf-8", errors="replace")
        for name, value in ENTITY_RE.findall(raw):
            entities[name] = value
        for m in ITEM_MASS_RE.finditer(raw):
            unid = m.group(2)
            body_and_head = m.group(1) + " " + m.group(3)[:800]
            attrs = parse_attrs(body_and_head)
            mass_s = attrs.get("mass")
            if not mass_s:
                continue
            try:
                mass_by_unid[unid.lower()] = float(mass_s)
            except ValueError:
                pass
            if unid.startswith("&") and unid.endswith(";"):
                continue
    return entities, mass_by_unid


def resolve_item_unid(token: str, entities: dict[str, str]) -> str | None:
    token = token.strip()
    if token.startswith("&") and token.endswith(";"):
        name = token[1:-1]
        return entities.get(name, token).lower()
    return token.lower()


def raise_max_armor(text: str, entities: dict[str, str], mass_by_unid: dict[str, float]) -> tuple[str, int]:
    count = 0

    def ship_repl(m: re.Match[str]) -> str:
        nonlocal count
        head, body = m.group(1), m.group(2)
        max_m = MAX_ARMOR_RE.search(head) or MAX_ARMOR_RE.search(body)
        armor_m = ARMOR_ID_RE.search(body)
        if not max_m or not armor_m:
            return m.group(0)
        max_class = max_m.group(1)
        if max_class not in CLASS_INDEX:
            return m.group(0)
        unid = resolve_item_unid(armor_m.group(1), entities)
        if not unid:
            return m.group(0)
        mass_kg = mass_by_unid.get(unid)
        if mass_kg is None:
            # entity may have expanded to 0x...
            mass_kg = mass_by_unid.get(entities.get(armor_m.group(1).strip("&;"), "").lower())
        if mass_kg is None:
            return m.group(0)
        need_class = class_for_tons(mass_kg / 1000.0)
        if CLASS_INDEX[need_class] <= CLASS_INDEX[max_class]:
            return m.group(0)
        count += 1
        new_head = MAX_ARMOR_RE.sub(f'maxArmor="{need_class}"', head, count=1)
        new_body = body
        if not MAX_ARMOR_RE.search(head):
            new_body = MAX_ARMOR_RE.sub(f'maxArmor="{need_class}"', body, count=1)
        return f"<ShipClass{new_head}>{new_body}</ShipClass>"

    return SHIP_CLASS_RE.sub(ship_repl, text), count


def scan_tdb(game_root: Path) -> list[str]:
    hits: list[str] = []
    needle = b"repeatingDelay"
    for path in game_root.rglob("*"):
        if path.suffix.lower() != ".tdb":
            continue
        if skip_path(path):
            continue
        try:
            data = path.read_bytes()
        except OSError:
            continue
        n = data.count(needle)
        if n:
            hits.append(f"{n}  {path}")
    return hits


def scan_sotp_uses(root: Path) -> list[str]:
    hits: list[str] = []
    for path in root.rglob("*.xml"):
        if skip_path(path):
            continue
        raw = path.read_text(encoding="utf-8", errors="replace")
        if "unidPartISystemMap" in raw or "0x00200004" in raw or "00200004" in raw:
            hits.append(str(path.relative_to(root)))
    return hits


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--game-root", default=str(GAME))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--fix-armor", action="store_true", help="Raise maxArmor to fit installed armor")
    ap.add_argument("--scan-tdb", action="store_true")
    args = ap.parse_args()
    root = Path(args.root)

    xml_files = [p for p in sorted(root.rglob("*.xml")) if not skip_path(p)]
    entities, mass_by_unid = index_entities_and_mass(xml_files)

    totals = {
        "files": 0,
        "repeatingDelay": 0,
        "fireRate": 0,
        "maxArmor": 0,
    }
    for path in xml_files:
        raw = path.read_text(encoding="utf-8", errors="replace")
        new, n_delay = convert_repeating_delay(raw)
        new, n_fire = bump_fire_rates(new)
        n_armor = 0
        if args.fix_armor:
            new, n_armor = raise_max_armor(new, entities, mass_by_unid)
        if new == raw:
            continue
        totals["files"] += 1
        totals["repeatingDelay"] += n_delay
        totals["fireRate"] += n_fire
        totals["maxArmor"] += n_armor
        try:
            rel = path.relative_to(root)
        except ValueError:
            rel = path
        print(f"{rel}: repeatingDelay={n_delay} fireRate={n_fire} maxArmor={n_armor}")
        if not args.dry_run:
            path.write_text(new, encoding="utf-8")

    print(f"Done. {totals}")

    sotp = scan_sotp_uses(root)
    if sotp:
        print("\nUses SotP system map 0x00200004 (missing in Eternity Port):")
        for line in sotp:
            print(f"  {line}")

    if args.scan_tdb:
        print("\nrepeatingDelay in TDB:")
        hits = scan_tdb(Path(args.game_root))
        if not hits:
            print("  (none found as plaintext)")
        for line in hits:
            print(f"  {line}")


if __name__ == "__main__":
    main()
