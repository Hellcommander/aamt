#!/usr/bin/env python3
"""Bump all Transcendence extension/library/module/adventure roots to apiVersion 57."""
from __future__ import annotations

import os
import re
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(r"D:\games\Steam\steamapps\common\Transcendence\Extensions")
BACKUP_DIR = (
    Path(r"D:\games\Steam\steamapps\common\Transcendence\Tools\Transcendence\_ext_fix_backups")
    / f"api57_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
)
TARGET_API = "57"

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


def set_api57(tag: str, attrs: str, self_close: str) -> tuple[str, str | None]:
    """Return (new_tag, change_note_or_None)."""
    m = API_RE.search(attrs)
    if m:
        cur = m.group(1)
        if cur == TARGET_API:
            return f"<{tag}{attrs}{self_close}>", None
        new_attrs = API_RE.sub(f'apiVersion="{TARGET_API}"', attrs, count=1)
        return f"<{tag}{new_attrs}{self_close}>", f"apiVersion {cur} -> {TARGET_API}"

    # Insert apiVersion
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
    changed: list[tuple[str, str]] = []
    already = 0
    errors: list[str] = []

    for dirpath, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d.lower() not in SKIP_DIR_NAMES]
        for fn in files:
            if not fn.lower().endswith((".xml", ".tdb")):
                continue
            # Only rewrite XML text; skip binary-ish TDB unless it starts with <?xml
            path = Path(dirpath) / fn
            rel = str(path.relative_to(ROOT))
            try:
                raw = path.read_bytes()
            except OSError as e:
                errors.append(f"{rel}: {e}")
                continue

            if not raw.lstrip().startswith((b"<?xml", b"<Transcendence", b"\xef\xbb\xbf<?xml")):
                # Compiled TDB or non-XML
                continue

            text = raw.decode("utf-8-sig")
            if not ROOT_TAG_RE.search(text):
                continue

            note_holder: list[str] = []

            def repl(m: re.Match) -> str:
                tag, attrs, sc = m.group(1), m.group(2), m.group(3)
                new_tag, note = set_api57(tag, attrs, sc)
                if note:
                    note_holder.append(note)
                return new_tag

            new_text = ROOT_TAG_RE.sub(repl, text, count=1)
            if not note_holder or new_text == text:
                already += 1
                continue

            backup_file(path)
            nl = "\r\n" if "\r\n" in text else "\n"
            out = new_text.replace("\r\n", "\n").replace("\r", "\n")
            if nl != "\n":
                out = out.replace("\n", nl)
            path.write_bytes(out.encode("utf-8"))
            changed.append((rel, note_holder[0]))
            print(f"UPDATED: {rel} ({note_holder[0]})")

    print()
    print(f"Updated: {len(changed)}")
    print(f"Already apiVersion={TARGET_API}: {already}")
    if errors:
        print("Errors:")
        for e in errors:
            print(f"  {e}")


if __name__ == "__main__":
    main()
