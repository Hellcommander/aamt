#!/usr/bin/env python3
"""Player-facing quality scan of installed Soulash 2 mods (read-only).

  python s2_quality.py [--json] [--all] MOD [MOD ...]     # folder names under data/mods

Complements `audit-mods` (cross-mod ids/references). This looks at what a player sees:
  tooltip  ::tokens that resolve to nothing (raw "::x" in game) or to 0 / [0,0]
  fx       abilities with no animation; animations that are empty, unreferenced, or test leftovers
  icons    icon index pointing at a blank tile, or shared by several rows of one sheet
  text     empty / placeholder names and descriptions
  files    debug / backup clutter in the mod folder (ships to the Workshop)
Tokens resolve like vanilla core_2: effects.<t>, else top-level <t> (duration, range); ::summon and
::aura are rendered from effects_keys.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

MODS = Path(r"D:\games\Steam\steamapps\common\Soulash 2\data\mods")
SPECIAL_TOKENS = {"summon", "aura"}
PLACEHOLDER = re.compile(r"\b(todo|tbd|placeholder|lorem|fixme|xxx)\b", re.I)
CLUTTER = re.compile(r"^(_|.*\.(bak|orig|tmp)$|.*backup|.*debug)", re.I)
ALL_FLAGS = (1 << 23) - 1


def load(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception as exc:  # noqa: BLE001
        return exc


def zeroish(v) -> bool:
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return v == 0
    if isinstance(v, list) and v and all(isinstance(x, (int, float)) for x in v):
        return all(x == 0 for x in v)
    return False


class Sheet:
    def __init__(self, mod: Path, name: str):
        self.img = None
        a = load(mod / "assets.json")
        if not isinstance(a, dict):
            return
        for ts in (a.get("graphics") or {}).get("tilesheets") or []:
            if ts.get("name") == name:
                try:
                    from PIL import Image

                    self.img = Image.open(mod / ts["file"]).convert("RGBA")
                    self.cols, self.rows = ts["tiles"]
                    self.tw = self.img.width // self.cols
                    self.th = self.img.height // self.rows
                except Exception:  # noqa: BLE001
                    self.img = None
                return

    def blank(self, idx: int):
        """True/False, or None when unknown (no sheet / index out of range)."""
        if self.img is None or not isinstance(idx, int) or idx < 0 or idx >= self.cols * self.rows:
            return None
        # index 0 is the BOTTOM-left tile (sheets are read bottom-up, like vanilla)
        x, y = idx % self.cols * self.tw, (self.rows - 1 - idx // self.cols) * self.th
        return self.img.crop((x, y, x + self.tw, y + self.th)).getextrema()[3][1] == 0


def all_ids(mods_dir: Path) -> set:
    """Every ability and ability-stacker id in every installed mod (references may cross mods)."""
    ids = set()
    for m in mods_dir.iterdir():
        if not m.is_dir():
            continue
        st = load(m / "ability_stackers.json")
        if isinstance(st, list):
            ids.update(str(r.get("id")) for r in st if isinstance(r, dict))
        for p in (m / "abilities").glob("*.json"):
            a = load(p)
            if isinstance(a, dict):
                ids.add(str(a.get("id")))
    return ids


def scan(mod: Path, known_ids: set = frozenset()) -> list[tuple[str, str, str]]:
    out: list[tuple[str, str, str]] = []

    def add(level, kind, msg):
        out.append((level, kind, msg))

    texts = {}
    for p in mod.rglob("*.json"):
        if ".git" in p.parts:
            continue
        try:
            texts[p] = p.read_text(encoding="utf-8-sig")
        except Exception:  # noqa: BLE001
            pass

    # ---- animations
    anims = {}
    for p in sorted((mod / "animations").glob("*.json")):
        a = load(p)
        if not isinstance(a, dict):
            add("ERROR", "fx", f"{p.name}: unreadable JSON ({a})")
            continue
        anims[str(a.get("id"))] = (p, a)
    for aid, (p, a) in anims.items():
        parts = a.get("particles") or []
        if not parts and not a.get("animation"):
            add("WARN", "fx", f"animation {p.name} ({a.get('name')}): no particles and no sub-animation (shows nothing)")
        for i, part in enumerate(parts, 1):
            # a tile-less particle carrying on_impact is vanilla's impact trigger (7_Lightning particle 5)
            if int(part.get("flags") or 0) == ALL_FLAGS or ("tile_id" not in part and not part.get("on_impact")):
                add("WARN", "fx", f"animation {p.name} particle {i}: test leftover (all flags / no tile_id)")
        refs = sum(t.count(f'"{aid}"') for q, t in texts.items() if q != p)
        if not refs:
            add("INFO", "fx", f"animation {p.name} ({a.get('name')}): referenced nowhere in the mod")

    # ---- abilities
    ab_sheet, amp_sheet, pas_sheet = Sheet(mod, "abilities"), Sheet(mod, "amplifiers"), Sheet(mod, "passive_skills")
    icon_users = defaultdict(list)
    for p in sorted((mod / "abilities").glob("*.json")):
        a = load(p)
        if not isinstance(a, dict):
            add("ERROR", "text", f"{p.name}: unreadable JSON ({a})")
            continue
        name = a.get("name") or p.stem
        desc = a.get("description") or ""
        eff = a.get("effects") or {}
        if not a.get("name"):
            add("WARN", "text", f"ability {p.name}: no name")
        if not desc.strip():
            add("WARN", "text", f"ability {name}: empty description")
        if PLACEHOLDER.search(name + " " + desc):
            add("WARN", "text", f"ability {name}: placeholder text in name/description")
        for t in sorted(set(re.findall(r"::(\w+)", desc))):
            if t in SPECIAL_TOKENS:
                continue
            if t in eff:
                v = eff[t]
            elif t in a:
                v = a[t]
            else:
                add("ERROR", "tooltip", f"ability {name}: ::{t} has no value (shows raw in game)")
                continue
            if zeroish(v):
                add("WARN", "tooltip", f"ability {name}: ::{t} = {v} (tooltip shows 0)")
        keys = a.get("effects_keys") or {}
        # Both encodings are in use: effects_keys.stacker (vanilla Ice Age, most mods) and effects.stacker,
        # which is what the F3 editor's "Stacking" field exposes (it offers an ability picker). Only a
        # reference that resolves to nothing is a defect.
        for where, k in (("effects", "stacker"), ("effects", "turn_damage_to_stacks"), ("effects", "effect_per_stack"),
                         ("effects_keys", "stacker")):
            v = (eff if where == "effects" else keys).get(k)
            if isinstance(v, str) and v and v not in known_ids:
                add("ERROR", "mech", f"ability {name}: {where}.{k}={v!r} is neither a stacker nor an ability id")
        if eff.get("stacker_count") and not (keys.get("stacker") or eff.get("stacker") or eff.get("turn_damage_to_stacks")):
            add("WARN", "mech", f"ability {name}: stacker_count without a stacker id")
        anim = a.get("animation")
        if anim in (None, "", -1, "-1"):
            add("WARN", "fx", f"ability {name}: no animation")
        img = a.get("image")
        if isinstance(img, int):
            icon_users[img].append(name)
            if ab_sheet.blank(img):
                add("WARN", "icons", f"ability {name}: icon {img} is a blank tile")
    for img, users in icon_users.items():
        if len(users) > 1:
            add("INFO", "icons", f"abilities share icon {img}: {', '.join(users)}")

    for fname, sheet, kind in (("ability_amplifiers.json", amp_sheet, "amplifier"), ("passives.json", pas_sheet, "passive")):
        rows = load(mod / fname)
        if not isinstance(rows, list):
            continue
        users = defaultdict(list)
        for r in rows:
            if not isinstance(r, dict):
                continue
            nm = r.get("name") or r.get("id")
            if PLACEHOLDER.search(str(nm) + " " + str(r.get("description") or "")):
                add("WARN", "text", f"{kind} {nm}: placeholder text")
            img = r.get("image")
            if isinstance(img, int):
                users[img].append(str(nm))
                if sheet.blank(img):
                    add("WARN", "icons", f"{kind} {nm}: icon {img} is a blank tile")
        for img, u in users.items():
            if len(u) > 1:
                add("INFO", "icons", f"{kind}s share icon {img}: {', '.join(u)}")

    # ---- clutter
    for p in mod.iterdir():
        if p.name in (".git", ".gitattributes", ".gitignore"):
            continue
        if CLUTTER.match(p.name):
            add("INFO", "files", f"{p.name}{'/' if p.is_dir() else ''}: debug/backup clutter ships with the mod")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mods", nargs="+")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--all", action="store_true", help="also print INFO lines")
    ap.add_argument("--mods-dir", default=str(MODS))
    a = ap.parse_args(argv)
    result = {}
    known = all_ids(Path(a.mods_dir))
    for m in a.mods:
        mod = Path(m) if Path(m).is_dir() else Path(a.mods_dir) / m
        result[mod.name] = scan(mod, known)
    if a.json:
        print(json.dumps({k: [list(x) for x in v] for k, v in result.items()}, indent=1))
        return 0
    for mod, rows in result.items():
        c = defaultdict(int)
        for lvl, _, _ in rows:
            c[lvl] += 1
        print(f"== {mod}: {c['ERROR']} error, {c['WARN']} warn, {c['INFO']} info")
        for lvl, kind, msg in rows:
            if lvl != "INFO" or a.all:
                print(f"  {lvl:5} {kind:7} {msg}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
