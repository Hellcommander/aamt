#!/usr/bin/env python3
"""
tx_fix_obsolete_designs.py - replace references to retired TransCore design types in mod XML attributes.

A mod whose apiVersion is at or past a type's obsoleteVersion cannot see that type; a reference in its data
(armorID="&itDarkMatterPlate;", <Station type="&stSungNEWall;">, <Lookup table="&tbStoneAsteroidOre;">) stops the
game loading with "Unknown design type". Replacements come from data/obsolete_design_replacements.json and are
written as literal hex UNIDs, so the mod needs no new entity declarations. References inside scripts are only
reported (they fail when that code runs, not at load, and need a look by hand).

Usage:
  python tx_fix_obsolete_designs.py <Extensions folder or mod folder> [...]          report
  python tx_fix_obsolete_designs.py <folder> --write                                 patch (backup .bak_<stamp>_obsdesign)
  [--core <current TransCore>]
"""
from __future__ import annotations

import argparse
import datetime as _dt
import glob
import json
import os
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPL = HERE / "data" / "obsolete_design_replacements.json"
DEFAULT_CORE = Path(r"D:\games\Steam\steamapps\common\Transcendence\game_and_dlc_source\TranscendenceDev-master\Transcendence\TransCore")
ENT = re.compile(r'<!ENTITY\s+(\w+)\s+"(0x[0-9A-Fa-f]+)"')
API = re.compile(r'<Transcendence(?:Extension|Library|Adventure)\b[^>]*?apiVersion="(\d+)"', re.S)


def read(p) -> str:
    return open(p, "rb").read().decode("utf-8", errors="surrogateescape")


def blank_comments(t: str) -> str:
    return re.sub(r"<!--.*?-->", lambda m: " " * len(m.group(0)), t, flags=re.S)


def core_obsolete(core: Path):
    files = glob.glob(str(core / "**" / "*.xml"), recursive=True)
    ent = {}
    for f in files:
        for n, v in ENT.findall(blank_comments(read(f))):
            ent[n.lower()] = int(v, 16)
    obs = {}
    for f in files:
        for m in re.finditer(r'<(\w+)\s+(?:UNID|unid)="&(\w+);"([^>]*)>', blank_comments(read(f))):
            o = re.search(r'obsoleteVersion\s*=\s*"(\d+)"', m.group(3))
            if o and m.group(1) != "Image" and m.group(2).lower() in ent:
                obs[ent[m.group(2).lower()]] = (m.group(1), m.group(2), int(o.group(1)))
    return ent, obs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("targets", nargs="+")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--core", default=str(DEFAULT_CORE))
    a = ap.parse_args()

    repl = {k.lower(): v for k, v in json.loads(REPL.read_text(encoding="utf-8")).items() if not k.startswith("_")}
    ent, obs = core_obsolete(Path(a.core))
    stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")

    # mods are folders under Extensions (or the folders given); a folder's API is its highest apiVersion
    mods = []
    for t in a.targets:
        p = Path(t)
        subs = [d for d in p.iterdir() if d.is_dir()] if p.is_dir() and not list(p.glob("*.xml")) else [p]
        mods += subs
    all_files = [f for m in mods for f in (m.rglob("*.xml") if m.is_dir() else [m])]
    mine = set()   # UNIDs a mod defines itself (it may re-create a retired type)
    for f in all_files:
        t = blank_comments(read(f))
        loc = {n.lower(): int(v, 16) for n, v in ENT.findall(t)}
        for m in re.finditer(r'<\w+\s+(?:UNID|unid)="&(\w+);"', t):
            u = loc.get(m.group(1).lower(), ent.get(m.group(1).lower()))
            if u:
                mine.add(u)

    n_static = n_fixed = n_script = 0
    for mod in mods:
        files = list(mod.rglob("*.xml")) if mod.is_dir() else [mod]
        apis = [int(x) for f in files for x in API.findall(blank_comments(read(f)))]
        api = max(apis) if apis else None
        for f in files:
            raw = read(f)
            t = blank_comments(raw)
            loc = {n.lower(): int(v, 16) for n, v in ENT.findall(t)}
            dt = re.search(r"<!DOCTYPE.*?\]>", t, re.S)
            base = dt.end() if dt else 0
            edits = []
            static_spans = []
            for tm in re.finditer(r"<(\w+)\b([^<>]*?)/?>", t[base:]):
                for am in re.finditer(r'(\w+)\s*=\s*"([^"]*)"', tm.group(2)):
                    for em in re.finditer(r"&(\w+);", am.group(2)):
                        name = em.group(1).lower()
                        u = loc.get(name, ent.get(name))
                        if u not in obs or u in mine or (api is not None and api < obs[u][2]):
                            continue
                        s = base + tm.start() + tm.group(0).find(tm.group(2)) + am.start(2) + em.start()
                        static_spans.append(s)
                        n_static += 1
                        line = t.count("\n", 0, s) + 1
                        r = repl.get(name)
                        tag = f"<{tm.group(1)} {am.group(1)}=...>"
                        if r:
                            edits.append((s, s + len(em.group(0)), r["to"]))
                            print(f"FIX    {f.relative_to(mod.parent)}:{line}  {tag}  {obs[u][1]} -> {r['as']} ({r['why']})")
                        else:
                            print(f"MANUAL {f.relative_to(mod.parent)}:{line}  {tag}  {obs[u][0]} {obs[u][1]} (retired API {obs[u][2]}, mod API {api}): add a replacement to {REPL.name}")
            for em in re.finditer(r"&(\w+);", t[base:]):
                s = base + em.start()
                u = loc.get(em.group(1).lower(), ent.get(em.group(1).lower()))
                if u in obs and u not in mine and (api is None or api >= obs[u][2]) and s not in static_spans:
                    n_script += 1
            if edits and a.write:
                shutil.copy2(f, f"{f}.bak_{stamp}_obsdesign")
                for s, e, new in sorted(edits, reverse=True):
                    assert raw[s] == "&" and raw[e - 1] == ";", f"offset drift in {f} at {s}: {raw[s:e]!r}"
                    raw = raw[:s] + new + raw[e:]
                open(f, "wb").write(raw.encode("utf-8", errors="surrogateescape"))
                n_fixed += len(edits)
                print(f"  patched {len(edits)} in {f}  (backup .bak_{stamp}_obsdesign)")
    print(f"{n_static} load-blocking references ({n_fixed} patched), {n_script} script references (runtime, left alone)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
