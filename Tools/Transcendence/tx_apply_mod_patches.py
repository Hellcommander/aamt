#!/usr/bin/env python3
"""
tx_apply_mod_patches.py - re-apply local fixes to third-party mods after they update.

Each folder in mod_patches/ is one patch:
  patch.json      target file name, the mod's UNID, entities to declare, root attributes to remove,
                  the fragment to insert and a marker string
  <fragment>.xml  XML inserted just before </TranscendenceExtension> (or </TranscendenceLibrary>)

Steps, all idempotent:
  - declare missing entities in the DOCTYPE (an entity the mod already declares is left alone)
  - remove the listed attributes from the root element
  - insert the fragment once, wrapped in <!-- marker begin/end --> comments
The file is backed up to <file>.bak_<stamp>_modpatch before writing.

Usage:
  python tx_apply_mod_patches.py                       report what would change (default Extensions folder)
  python tx_apply_mod_patches.py --write
  python tx_apply_mod_patches.py --extensions <folder> --only corporate_command_ep_addon --write
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PATCHES = HERE / "mod_patches"
DEFAULT_EXT = Path(r"D:\games\Steam\steamapps\common\Transcendence\Extensions")
ROOT_RE = re.compile(r"<(TranscendenceExtension|TranscendenceLibrary|TranscendenceAdventure)\b[^>]*>", re.S)


def find_target(ext: Path, spec: dict) -> Path | None:
    want = spec["target"].lower()
    hits = [p for p in ext.rglob("*.xml") if p.name.lower() == want]
    if not hits:   # renamed by the author: fall back to the mod UNID
        unid = spec.get("match_unid", "").lower()
        for p in ext.rglob("*.xml"):
            t = p.read_text(encoding="utf-8", errors="replace")
            m = ROOT_RE.search(t)
            if m and unid and unid in t.lower() and re.search(r'UNID="&?\w*;?"', m.group(0)):
                ents = dict((n.lower(), v.lower()) for n, v in re.findall(r'<!ENTITY\s+(\w+)\s+"([^"]+)"', t))
                u = re.search(r'UNID="([^"]+)"', m.group(0)).group(1)
                u = ents.get(u.strip("&;").lower(), u.lower())
                if u == unid:
                    hits.append(p)
    return hits[0] if hits else None


def apply(text: str, spec: dict, frag: str) -> tuple[str, list[str]]:
    done = []
    # 1. entities
    declared = {n.lower() for n in re.findall(r'<!ENTITY\s+(\w+)\s', text)}
    add = [(n, v) for n, v in spec.get("entities", {}).items() if n.lower() not in declared]
    if add:
        lines = "".join(f'\t<!ENTITY {n:<36}"{v}">\n' for n, v in add)
        m = re.search(r"\n?\s*\]>", text)
        if not m:
            raise SystemExit("no DOCTYPE internal subset to add entities to")
        text = text[:m.start()] + "\n" + lines.rstrip("\n") + text[m.start():]
        done.append("declared " + ", ".join(n for n, _ in add))
    # 2. root attributes
    m = ROOT_RE.search(text)
    root = m.group(0)
    new_root = root
    for a in spec.get("remove_root_attributes", []):
        new_root = re.sub(r'\s+' + re.escape(a) + r'\s*=\s*"[^"]*"', "", new_root)
    if new_root != root:
        text = text[:m.start()] + new_root + text[m.end():]
        done.append("removed root " + ", ".join(spec["remove_root_attributes"]))
    # 3. fragment
    marker = spec["marker"]
    if marker not in text:
        close = text.rfind("</" + m.group(1) + ">")
        block = f"\t<!-- {marker} begin (tx_apply_mod_patches.py) -->\n{frag.rstrip()}\n\t<!-- {marker} end -->\n\n"
        text = text[:close] + block + text[close:]
        done.append("inserted " + spec["insert_fragment"])
    return text, done


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--extensions", default=str(DEFAULT_EXT))
    ap.add_argument("--only")
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    ext = Path(a.extensions)
    for d in sorted(p for p in PATCHES.iterdir() if p.is_dir()):
        if a.only and d.name != a.only:
            continue
        spec = json.loads((d / "patch.json").read_text(encoding="utf-8"))
        target = find_target(ext, spec)
        if not target:
            print(f"SKIP   {d.name}: {spec['target']} not installed")
            continue
        raw = target.read_bytes()
        bom = raw.startswith(b"\xef\xbb\xbf")
        text = raw.decode("utf-8-sig", errors="surrogateescape")
        crlf = "\r\n" in text
        text = text.replace("\r\n", "\n")
        frag = (d / spec["insert_fragment"]).read_text(encoding="utf-8").replace("\r\n", "\n")
        new, done = apply(text, spec, frag)
        if not done:
            print(f"OK     {d.name}: already patched ({target})")
            continue
        print(f"{'PATCH ' if a.write else 'WOULD '} {d.name}: {'; '.join(done)}  ({target})")
        if a.write:
            shutil.copy2(target, f"{target}.bak_{stamp}_modpatch")
            out = new.replace("\n", "\r\n") if crlf else new
            target.write_bytes((b"\xef\xbb\xbf" if bom else b"") + out.encode("utf-8", errors="surrogateescape"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
