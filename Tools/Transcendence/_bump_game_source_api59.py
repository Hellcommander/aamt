#!/usr/bin/env python3
"""Bump apiVersion on game_and_dlc_source pack roots to 59 before compile."""
from __future__ import annotations
import re
from pathlib import Path

TARGET = "59"
FILES = [
    Path(r"D:\games\Steam\steamapps\common\Transcendence\game_and_dlc_source\Transcendence_Source\Transcendence.xml"),
    Path(r"D:\games\Steam\steamapps\common\Transcendence\game_and_dlc_source\CorporateCommand_Source\CorporateCommand.xml"),
    Path(r"D:\games\Steam\steamapps\common\Transcendence\game_and_dlc_source\CorporateHierarchyVol01_Source\CorporateHierarchyVol01.xml"),
    Path(r"D:\games\Steam\steamapps\common\Transcendence\game_and_dlc_source\CorporateHierarchyVol1UNIDs_Source\CorporateHierarchyVol1UNIDs.xml"),
    Path(r"D:\games\Steam\steamapps\common\Transcendence\game_and_dlc_source\StarsOfThePilgrimHD_Source\StarsOfThePilgrimHD.xml"),
    Path(r"D:\games\Steam\steamapps\common\Transcendence\game_and_dlc_source\StarsOfThePilgrimSoundtrack_Source\StarsOfThePilgrimSoundtrack.xml"),
]

API_RE = re.compile(r'(apiVersion\s*=\s*["\'])([^"\']+)(["\'])', re.I)
ROOT_RE = re.compile(
    r"<(Transcendence(?:Universe|Extension|Library|Adventure|Module))\b([^>]*?)(/?)>",
    re.I | re.S,
)

for path in FILES:
    text = path.read_text(encoding="utf-8-sig")
    m = ROOT_RE.search(text)
    if not m:
        print(f"SKIP (no root): {path.name}")
        continue
    attrs = m.group(2)
    am = API_RE.search(attrs)
    if am and am.group(2) == TARGET:
        print(f"OK already {TARGET}: {path.name}")
        continue
    if am:
        new_attrs = API_RE.sub(rf'\g<1>{TARGET}\g<3>', attrs, count=1)
        note = f"{am.group(2)} -> {TARGET}"
    else:
        insert = f'\n\tapiVersion="{TARGET}"'
        if "\n" in attrs:
            head, rest = attrs.split("\n", 1)
            new_attrs = head + insert + "\n" + rest
        else:
            new_attrs = insert + ((" " + attrs) if attrs and not attrs[:1].isspace() else attrs)
        note = f"added {TARGET}"
    # HD pack has obsoleteVersion="49" which would disable it on API59 - bump/remove
    if "obsoleteVersion" in new_attrs and "StarsOfThePilgrimHD" in path.name:
        new_attrs = re.sub(r'\s*obsoleteVersion\s*=\s*["\'][^"\']+["\']', "", new_attrs)
        note += "; removed obsoleteVersion"
    new_tag = f"<{m.group(1)}{new_attrs}{m.group(3)}>"
    text = text[: m.start()] + new_tag + text[m.end() :]
    path.write_text(text, encoding="utf-8", newline="\n")
    print(f"UPDATED {path.name}: {note}")
