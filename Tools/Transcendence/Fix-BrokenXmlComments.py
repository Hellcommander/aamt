#!/usr/bin/env python3
"""Fix broken XML comments of the form <!- ... -> into <!-- ... -->."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

# Single-line broken comments (most common in Transcendence mods)
LINE_PAT = re.compile(r"<!-([^-].*?)->")


def fix_text(text: str) -> tuple[str, int]:
    return LINE_PAT.subn(r"<!--\1-->", text)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--root",
        default=r"D:\games\Steam\steamapps\common\Transcendence\Extensions",
    )
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    root = Path(args.root)
    files = total = 0
    for path in sorted(root.rglob("*.xml")):
        raw = path.read_text(encoding="utf-8", errors="replace")
        new, count = fix_text(raw)
        if not count:
            continue
        files += 1
        total += count
        print(f"{count:3d}  {path.relative_to(root)}")
        if not args.dry_run:
            path.write_text(new, encoding="utf-8")
    print(f"Done: {total} comments in {files} files")


if __name__ == "__main__":
    main()
