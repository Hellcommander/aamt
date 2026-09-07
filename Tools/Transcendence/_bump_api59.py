#!/usr/bin/env python3
"""Bump all Transcendence extension/library/module/adventure roots to apiVersion 59."""
from __future__ import annotations

import os
import re
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(r"D:\games\Steam\steamapps\common\Transcendence\Extensions")
BACKUP_DIR = (
    Path(r"D:\games\Steam\steamapps\common\Transcendence\Tools\Transcendence\_ext_fix_backups")
    / f"api59_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
)
TARGET_API = "59"

ROOT_TAG_RE = re.compile(
    r"<(Transcendence(?:Extension|Adventure|Library|Module))\b([^>]*?)(/?)>",
    re.I | re.S,
)
API_RE = re.compile(r'apiVersion\s*=\s*["\']([^"\']+)["\']', re.I)

SKIP_DIR_NAMES = {"tools", ".git", "node_modules", "__pycache__", ".vscode"}


def backup_file(path: Path) -> None:
    rel = path.relative_to(ROOT)
    dest = BACKUP_DIR / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dest)


def set_api(tag: str, attrs: str, self_close: str) -> tuple[str, str | None]:
    m = API_RE.search(attrs)
    if m:
        cur = m.group(1)
        if cur == TARGET_API:
            return f"<{tag}{attrs}{self_close}>", None
        new_attrs = API_RE.sub(f'apiVersion="{TARGET_API}"', attrs, count=1)
        return f"<{tag}{new_attrs}{self_close}>", f"apiVersion {cur} -> {TARGET_API}"

    insert = f'\n\tapiVersion="{TARGET_API}"'
    if "\n" in attrs:
        head, rest = attrs.split("\n", 1)
        new_attrs = head + insert + "\n" + rest
    else:
        if attrs and not attrs[:1].isspace():
            attrs = " " + attrs
        new_attrs = insert + attrs
    return f"<{tag}{new_attrs}{self_close}>", f"added apiVersion={TARGET_API}"


def main() -> None:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Backups -> {BACKUP_DIR}")
    changed = 0
    already = 0
    skipped_tdb = 0

    for dirpath, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d.lower() not in SKIP_DIR_NAMES]
        for fn in files:
            if not fn.lower().endswith((".xml", ".tdb")):
                continue
            path = Path(dirpath) / fn
            rel = str(path.relative_to(ROOT))
            try:
                raw = path.read_bytes()
            except OSError as e:
                print(f"ERROR: {rel}: {e}")
                continue

            if not raw.lstrip().startswith((b"<?xml", b"<Transcendence", b"\xef\xbb\xbf<?xml")):
                skipped_tdb += 1
                continue

            text = raw.decode("utf-8-sig")
            if not ROOT_TAG_RE.search(text):
                continue

            notes: list[str] = []

            def repl(m: re.Match) -> str:
                new_tag, note = set_api(m.group(1), m.group(2), m.group(3))
                if note:
                    notes.append(note)
                return new_tag

            new_text = ROOT_TAG_RE.sub(repl, text, count=1)
            if not notes or new_text == text:
                already += 1
                continue

            backup_file(path)
            nl = "\r\n" if "\r\n" in text else "\n"
            out = new_text.replace("\r\n", "\n").replace("\r", "\n")
            if nl != "\n":
                out = out.replace("\n", nl)
            path.write_bytes(out.encode("utf-8"))
            changed += 1
            print(f"UPDATED: {rel} ({notes[0]})")

    print()
    print(f"Updated: {changed}")
    print(f"Already apiVersion={TARGET_API}: {already}")
    print(f"Skipped non-XML/binary TDB: {skipped_tdb}")


if __name__ == "__main__":
    main()
