#!/usr/bin/env python3
"""
Fix Transcendence extension roots that fail with:
  Unable to load extension: incompatible version: ...

Also applies a few known API-57 entity renames found in Debug.log.
"""
from __future__ import annotations

import os
import re
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(r"D:\games\Steam\steamapps\common\Transcendence\Extensions")
BACKUP_DIR = Path(r"D:\games\Steam\steamapps\common\Transcendence\Tools\Transcendence\_ext_fix_backups") / datetime.now().strftime("%Y%m%d_%H%M%S")
TARGET_API = "57"

ROOT_TAG_RE = re.compile(
    r"<(Transcendence(?:Extension|Adventure|Library|Module))\b([^>]*?)(/?)>",
    re.I | re.S,
)
API_RE = re.compile(r'apiVersion\s*=\s*["\']([^"\']+)["\']', re.I)
VER_RE = re.compile(r'(?<![a-zA-Z])version\s*=\s*["\']([^"\']+)["\']', re.I)

OLD_OK = {
    "0.95", "0.95a", "0.95b",
    "0.96", "0.96a",
    "0.97", "0.97a",
    "0.98", "0.98a", "0.98b", "0.98c", "0.98d",
    "0.99", "0.99a", "0.99b", "0.99c",
    "1.0", "1.1",
}

# Specific known-bad entity fixes (path relative to Extensions, regex replacements)
ENTITY_FIXES = {
    r"1365_VCantHeliotropeGunship\VcantHeliotrope.xml": [
        (
            re.compile(r'<!ENTITY\s+itSolarArmor\s+"0x0000407C">'),
            '<!ENTITY itLightSolarArmor\t\t\t"0x0000407C">',
        ),
        (
            re.compile(r"&itSolarArmor;"),
            "&itLightSolarArmor;",
        ),
    ],
    r"1108_ChangeCargoholdViewByCategory\configureScreen.xml": [
        # Wrong UNID (0x00001010); base game uses 0x00002003
        (
            re.compile(r'<!ENTITY\s+stCargoCrate\s+"0x00001010">'),
            '<!ENTITY\tstCargoCrate\t\t\t"0x00002003">',
        ),
    ],
}

SKIP_DIR_NAMES = {"tools", ".git", "node_modules", "__pycache__", ".vscode"}


def backup_file(path: Path) -> None:
    rel = path.relative_to(ROOT)
    dest = BACKUP_DIR / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dest)


def needs_api_fix(attrs: str) -> tuple[bool, str | None]:
    api = API_RE.search(attrs)
    ver = VER_RE.search(attrs)
    api_v = api.group(1) if api else None
    ver_v = ver.group(1) if ver else None

    if api_v is None:
        if ver_v is None:
            return True, "missing apiVersion and version"
        if ver_v.lower() not in OLD_OK:
            return True, f"unrecognized version={ver_v} without apiVersion"
        return False, None

    m = re.match(r"(\d+)", api_v)
    n = int(m.group(1)) if m else 0
    if n < 12:
        return True, f"apiVersion={api_v} rejected (<12)"
    return False, None


def inject_api_version(tag: str, attrs: str, self_close: str) -> str:
    """Insert or replace apiVersion on a root tag."""
    if API_RE.search(attrs):
        new_attrs = API_RE.sub(f'apiVersion="{TARGET_API}"', attrs, count=1)
    else:
        # Prefer inserting after UNID/name if present; else at start of attrs
        new_attrs = attrs
        if new_attrs and not new_attrs.startswith((" ", "\t", "\n")):
            new_attrs = " " + new_attrs
        # Put apiVersion near the front for readability
        insert = f'\n\tapiVersion="{TARGET_API}"'
        # After opening whitespace of attrs
        if "\n" in new_attrs:
            # multiline attribute block — insert as first attribute line
            parts = new_attrs.split("\n", 1)
            new_attrs = parts[0] + insert + "\n" + parts[1]
        else:
            new_attrs = insert + new_attrs

    return f"<{tag}{new_attrs}{self_close}>"


def fix_root_api(text: str) -> tuple[str, list[str]]:
    notes: list[str] = []

    def repl(m: re.Match) -> str:
        tag, attrs, self_close = m.group(1), m.group(2), m.group(3)
        bad, reason = needs_api_fix(attrs)
        if not bad:
            return m.group(0)
        notes.append(reason or "apiVersion fix")
        return inject_api_version(tag, attrs, self_close)

    new_text, n = ROOT_TAG_RE.subn(repl, text, count=1)
    return new_text, notes


def main() -> None:
    changed: list[str] = []
    skipped_ok = 0
    errors: list[str] = []

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Backups -> {BACKUP_DIR}")

    for dirpath, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d.lower() not in SKIP_DIR_NAMES]
        for fn in files:
            if not fn.lower().endswith(".xml"):
                continue
            path = Path(dirpath) / fn
            rel = str(path.relative_to(ROOT))
            try:
                raw = path.read_bytes()
            except OSError as e:
                errors.append(f"{rel}: read error {e}")
                continue

            # Skip BOM-less check later; decode leniently
            text = raw.decode("utf-8-sig")
            original = text
            notes: list[str] = []

            # Only touch files that actually have a Transcendence root
            if not ROOT_TAG_RE.search(text):
                continue

            text, api_notes = fix_root_api(text)
            notes.extend(api_notes)

            # Path-specific entity fixes
            key = rel
            # normalize for dict lookup
            for pattern_rel, reps in ENTITY_FIXES.items():
                if rel.replace("/", "\\") == pattern_rel:
                    for cre, repl in reps:
                        text2, n = cre.subn(repl, text)
                        if n:
                            text = text2
                            notes.append(f"entity fix x{n}: {cre.pattern[:40]}")

            if text == original:
                skipped_ok += 1
                continue

            backup_file(path)
            # Preserve original newline style; UTF-8 without BOM
            nl = "\r\n" if "\r\n" in original else "\n"
            out = text.replace("\r\n", "\n").replace("\r", "\n")
            if nl != "\n":
                out = out.replace("\n", nl)
            path.write_bytes(out.encode("utf-8"))
            changed.append(rel)
            print(f"FIXED: {rel}")
            for n in notes:
                print(f"       - {n}")

    print()
    print(f"Changed: {len(changed)}")
    print(f"Unchanged roots: {skipped_ok}")
    if errors:
        print("Errors:")
        for e in errors:
            print(f"  {e}")


if __name__ == "__main__":
    main()
