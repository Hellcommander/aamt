#!/usr/bin/env python3
"""Quick API59 cleanup for local Extensions mods.

- Add maxInSystem=\"1\" next to maxAppearing when missing
- Convert repeatingDelay=N -> repeatingShotDelay=(N+2)
- Strip backColor=\"0x00000000\" (unsupported with bitmask/jpg path)
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(r"D:\games\Steam\steamapps\common\Transcendence\Extensions")


def fix_text(text: str) -> tuple[str, dict[str, int]]:
    stats = {"maxInSystem": 0, "repeating": 0, "backColor": 0}

    def add_max_in_system(m: re.Match[str]) -> str:
        s = m.group(0)
        if "maxInSystem" in s:
            return s
        stats["maxInSystem"] += 1
        return re.sub(r"\bmaxAppearing\b", 'maxInSystem="1" maxAppearing', s, count=1)

    text = re.sub(r"<[^>]*\bmaxAppearing\s*=\s*\"[^\"]+\"[^>]*>", add_max_in_system, text)

    def rep_delay(m: re.Match[str]) -> str:
        n = int(m.group(2))
        stats["repeating"] += 1
        return f'{m.group(1)}repeatingShotDelay="{n + 2}"'

    text2, n = re.subn(
        r'(\b)repeatingDelay\s*=\s*"(\d+)"',
        rep_delay,
        text,
    )
    text = text2

    text2, n = re.subn(
        r'\s+backColor\s*=\s*"0x00000000"',
        "",
        text,
        flags=re.IGNORECASE,
    )
    stats["backColor"] = n
    text = text2
    return text, stats


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    root = Path(args.root)
    total = {"maxInSystem": 0, "repeating": 0, "backColor": 0, "files": 0}
    for path in sorted(root.rglob("*.xml")):
        raw = path.read_text(encoding="utf-8", errors="replace")
        if "maxAppearing" not in raw and "repeatingDelay" not in raw and "backColor" not in raw:
            continue
        new, stats = fix_text(raw)
        if new == raw:
            continue
        total["files"] += 1
        for k in ("maxInSystem", "repeating", "backColor"):
            total[k] += stats[k]
        print(f"{path.relative_to(root)}: {stats}")
        if not args.dry_run:
            path.write_text(new, encoding="utf-8")
    print(f"Done. files={total['files']} {total}")


if __name__ == "__main__":
    main()
