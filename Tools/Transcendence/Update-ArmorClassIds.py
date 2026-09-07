#!/usr/bin/env python3
"""
Remap legacy ShipClass armor mass limits to Human Space armor class IDs.

API59 Human Space treats maxArmor/stdArmor as class names (light, medium, …).
Unitless numbers (and kg/t strings when classes are defined) become
"Invalid armor class: …" load errors.

Class ceilings (compatibility tons ≈ kg/1000), from StdArmor:
  ultraLight 1 | light 2.5 | medium 3.5 | heavy 6
  superHeavy 9 | massive 12 | dreadnought 100 | maximum 1e6

Uses dreadnought (not superMassive) so both older dreadnought tables and
API59 alias tables resolve.

Usage:
  python Update-ArmorClassIds.py              # dry-run report
  python Update-ArmorClassIds.py --apply      # write changes
  python Update-ArmorClassIds.py --root PATH --apply
"""
from __future__ import annotations

import argparse
import csv
import re
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(r"D:\games\Steam\steamapps\common\Transcendence\Extensions")
BACKUP_ROOT = Path(r"D:\games\Steam\steamapps\common\Transcendence\Tools\Transcendence\_ext_fix_backups")

SKIP_DIR_NAMES = {
    "tools",
    ".git",
    "node_modules",
    "__pycache__",
    "Collection",
}

SKIP_SUFFIXES = {".bak", ".backup", ".orig", ".tmp"}

# Smallest class whose ceiling is >= mass (tons).
CLASS_CEILINGS: list[tuple[float, str]] = [
    (1.0, "ultraLight"),
    (2.5, "light"),
    (3.5, "medium"),
    (6.0, "heavy"),
    (9.0, "superHeavy"),
    (12.0, "massive"),
    (100.0, "dreadnought"),
    (1_000_000.0, "maximum"),
]

VALID_CLASS_IDS = {name for _, name in CLASS_CEILINGS} | {
    "superMassive",  # API59 primary name; remapped to dreadnought
    "dreadnought",
}

# Known renames / aliases that fail on older StdArmor tables.
CLASS_ALIASES = {
    "superMassive": "dreadnought",
    "supermassive": "dreadnought",
    "dreadnaught": "dreadnought",
}

ATTR_RE = re.compile(
    r'\b(maxArmor|stdArmor)(\s*=\s*)"([^"]*)"',
    re.IGNORECASE,
)

MASS_RE = re.compile(
    r"^\s*([0-9]+(?:\.[0-9]+)?)\s*(kg|t|tons?)?\s*$",
    re.IGNORECASE,
)


def mass_to_class(tons: float) -> str:
    if tons < 0 or tons != tons:  # NaN
        raise ValueError(f"invalid mass tons: {tons}")
    for ceiling, name in CLASS_CEILINGS:
        if tons <= ceiling + 1e-9:
            return name
    return "maximum"


def parse_mass_to_tons(value: str) -> float | None:
    m = MASS_RE.match(value)
    if not m:
        return None
    amount = float(m.group(1))
    unit = (m.group(2) or "").lower()
    if unit in ("t", "ton", "tons"):
        return amount
    # bare number or kg → kg (legacy Transcendence maxArmor units)
    return amount / 1000.0


def map_armor_value(raw: str) -> tuple[str | None, str]:
    """
    Returns (new_value_or_None_if_unchanged, reason).
    """
    value = raw.strip()
    if not value:
        return None, "empty"

    alias = CLASS_ALIASES.get(value) or CLASS_ALIASES.get(value.lower())
    if alias and alias != value:
        return alias, f"alias {value} -> {alias}"

    if value in VALID_CLASS_IDS and value not in CLASS_ALIASES:
        return None, "already class id"

    tons = parse_mass_to_tons(value)
    if tons is None:
        # Unknown token — leave alone (may be adventure-specific class)
        return None, f"unknown token ({value})"

    mapped = mass_to_class(tons)
    if mapped == value:
        return None, "already mapped"
    return mapped, f"{value} ({tons:g}t) -> {mapped}"


def should_skip(path: Path, root: Path) -> bool:
    if path.suffix.lower() != ".xml":
        return True
    if any(path.name.lower().endswith(suf) for suf in SKIP_SUFFIXES):
        return True
    try:
        rel_parts = path.relative_to(root).parts
    except ValueError:
        rel_parts = path.parts
    return any(part.lower() in SKIP_DIR_NAMES for part in rel_parts)


def process_text(text: str) -> tuple[str, list[dict[str, str]]]:
    changes: list[dict[str, str]] = []

    def repl(m: re.Match[str]) -> str:
        attr, eq, raw = m.group(1), m.group(2), m.group(3)
        new_val, reason = map_armor_value(raw)
        if new_val is None:
            return m.group(0)
        changes.append(
            {
                "attr": attr,
                "old": raw,
                "new": new_val,
                "reason": reason,
            }
        )
        return f'{attr}{eq}"{new_val}"'

    return ATTR_RE.sub(repl, text), changes


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=str(ROOT), help="Extensions root to scan")
    ap.add_argument("--apply", action="store_true", help="Write changes (default is dry-run)")
    ap.add_argument("--backup", action="store_true", help="Copy originals under _ext_fix_backups before write")
    ap.add_argument("--csv", default="", help="Optional path for change report CSV")
    args = ap.parse_args()

    root = Path(args.root)
    if not root.is_dir():
        raise SystemExit(f"Root not found: {root}")

    apply = bool(args.apply)
    backup_dir: Path | None = None
    if apply and args.backup:
        backup_dir = BACKUP_ROOT / f"armorclass_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_dir.mkdir(parents=True, exist_ok=True)

    report_rows: list[dict[str, str]] = []
    files_touched = 0
    replacements = 0

    for path in sorted(root.rglob("*.xml")):
        if should_skip(path, root):
            continue
        raw = path.read_text(encoding="utf-8", errors="replace")
        new_text, changes = process_text(raw)
        if not changes:
            continue

        files_touched += 1
        replacements += len(changes)
        rel = str(path.relative_to(root)) if path.is_relative_to(root) else str(path)
        print(f"\n{rel}")
        for c in changes:
            print(f"  {c['attr']}: \"{c['old']}\" -> \"{c['new']}\"  ({c['reason']})")
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
            f"armorclass_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
    if csv_path and report_rows:
        with csv_path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=["file", "attr", "old", "new", "reason"])
            writer.writeheader()
            writer.writerows(report_rows)
        print(f"Report: {csv_path}")


if __name__ == "__main__":
    main()
