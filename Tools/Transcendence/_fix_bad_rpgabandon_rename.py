#!/usr/bin/env python3
"""
Fix incorrect dsRPGAbandonedStation -> dsAbandonedStationObsolete renames
from the previous gamesource pass, and correct a few other bad mappings.
Also remove bogus ENTITY CMPT... -> LEGACY style damage if any.
"""
from __future__ import annotations

import os
import re
import shutil
from datetime import datetime
from pathlib import Path

EXT_ROOT = Path(r"D:\games\Steam\steamapps\common\Transcendence\Extensions")
BACKUP_DIR = (
    Path(r"D:\games\Steam\steamapps\common\Transcendence\Tools\Transcendence\_ext_fix_backups")
    / f"fix_rpgabandon_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
)

# Undo wrong direction: obsolete screen should NOT replace the RPG one
UNDO = [
    # refs
    (re.compile(r"&dsAbandonedStationObsolete;"), "&dsRPGAbandonedStation;"),
    # ENTITY defs that were renamed incorrectly
    (
        re.compile(r'<!ENTITY\s+dsAbandonedStationObsolete\s+"([^"]+)"\s*>', re.I),
        r'<!ENTITY dsRPGAbandonedStation\t\t\t"\1">',
    ),
]

# But: if a file INTENTIONALLY defined dsAbandonedStationObsolete as the old UNID
# 0x0000A003, restoring the name to dsRPGAbandonedStation with that UNID would be wrong.
# Canonical:
#   dsRPGAbandonedStation = typically from RPG library
#   dsAbandonedStationObsolete = 0x0000A003
#
# Strategy: only undo reference replacements (&...;).
# For ENTITY lines: if UNID is 0x0000A003 keep as Obsolete; if it was renamed FROM
# dsRPGAbandonedStation with a different UNID, restore name.

SKIP_DIRS = {"tools", ".git", "node_modules", "__pycache__", ".vscode", "_ext_fix_backups"}


def backup_file(path: Path) -> None:
    rel = path.relative_to(EXT_ROOT)
    dest = BACKUP_DIR / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dest)


def fix_text(text: str) -> tuple[str, list[str]]:
    notes = []
    # Always restore refs: &dsAbandonedStationObsolete; that we wrongly introduced
    # when they meant the live RPG screen. Heuristic: if file also still has
    # dsAbandonedStation / dsAbandonedShip / dsAbandonedCrate mappings to RPG,
    # the Obsolete refs from our bad pass should be RPG again.
    # Safer global undo for refs introduced by bad pass:
    n = len(re.findall(r"&dsAbandonedStationObsolete;", text))
    if n:
        text = text.replace("&dsAbandonedStationObsolete;", "&dsRPGAbandonedStation;")
        notes.append(f"restored &dsRPGAbandonedStation; refs (x{n})")

    # ENTITY: if we renamed dsRPGAbandonedStation -> dsAbandonedStationObsolete
    # and UNID is NOT the obsolete 0x0000A003, restore the name.
    def repl_ent(m: re.Match) -> str:
        unid = m.group(1)
        if unid.upper() == "0X0000A003":
            return m.group(0)  # genuine obsolete entity def
        return f'<!ENTITY dsRPGAbandonedStation\t\t\t"{unid}">'

    text2, n = re.subn(
        r'<!ENTITY\s+dsAbandonedStationObsolete\s+"([^"]+)"\s*>',
        repl_ent,
        text,
        flags=re.I,
    )
    if n and text2 != text:
        text = text2
        notes.append(f"restored ENTITY dsRPGAbandonedStation (x{n})")

    return text, notes


def main() -> None:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Backups -> {BACKUP_DIR}")
    changed = 0
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
            text = raw.decode("utf-8-sig")
            if "dsAbandonedStationObsolete" not in text:
                continue
            new, notes = fix_text(text)
            if new == text or not notes:
                continue
            backup_file(path)
            nl = "\r\n" if "\r\n" in text else "\n"
            out = new.replace("\r\n", "\n").replace("\r", "\n")
            if nl != "\n":
                out = out.replace("\n", nl)
            path.write_bytes(out.encode("utf-8"))
            changed += 1
            print(f"FIXED: {path.relative_to(EXT_ROOT)}")
            for n in notes:
                print(f"       - {n}")
    print(f"\nFiles fixed: {changed}")


if __name__ == "__main__":
    main()
