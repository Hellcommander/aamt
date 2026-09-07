#!/usr/bin/env python3
"""Patch LHL ExtraUnits with UnitModelType (+ optional base mesh) so clothes/armor packs apply."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def patch_unit_block(block: str, race: dict) -> str:
    primary = race.get("unitModelTypePrimary") or (race.get("unitModelTypes") or [None])[0]
    if not primary:
        return block

    if re.search(r"<UnitModelType>[^<]+</UnitModelType>", block):
        block = re.sub(
            r"<UnitModelType>[^<]+</UnitModelType>",
            f"<UnitModelType>{primary}</UnitModelType>",
            block,
            count=1,
        )
    else:
        # Insert after Texture_Skin if present, else after SkeletonPath, else after ModelPath
        insert = f"\t\t<UnitModelType>{primary}</UnitModelType>\n"
        if re.search(r"</Texture_Skin>", block):
            block = re.sub(r"(</Texture_Skin>\s*\n)", r"\1" + insert, block, count=1)
        elif re.search(r"</SkeletonPath>", block):
            block = re.sub(r"(</SkeletonPath>\s*\n)", r"\1" + insert, block, count=1)
        elif re.search(r"</ModelPath>", block):
            block = re.sub(r"(</ModelPath>\s*\n)", r"\1" + insert, block, count=1)

    if race.get("baseModelPath"):
        repl_model = f"<ModelPath>{race['baseModelPath']}</ModelPath>"
        block = re.sub(
            r"<ModelPath>[^<]+</ModelPath>",
            lambda _m: repl_model,
            block,
            count=1,
        )
    if race.get("baseSkeletonPath"):
        repl_skel = f"<SkeletonPath>{race['baseSkeletonPath']}</SkeletonPath>"
        block = re.sub(
            r"<SkeletonPath>[^<]+</SkeletonPath>",
            lambda _m: repl_skel,
            block,
            count=1,
        )
    return block


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--units", required=True, help="LHL_ExtraUnits.xml path")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    path = Path(args.units)
    text = path.read_text(encoding="utf-8")
    patched = 0

    for race_key, race in cfg["races"].items():
        pattern = re.compile(
            rf'(<UnitType InternalName="Unit_\w+_{re.escape(race_key)}">)(.*?)(</UnitType>)',
            re.S,
        )

        def repl(m: re.Match[str], race=race) -> str:
            nonlocal patched
            new_body = patch_unit_block(m.group(2), race)
            if new_body != m.group(2):
                patched += 1
            return m.group(1) + new_body + m.group(3)

        text, n = pattern.subn(repl, text)
        # subn count is replacements; patched tracks content changes

    if args.dry_run:
        print(json.dumps({"would_patch_units": patched, "file": str(path)}))
        return

    path.write_text(text, encoding="utf-8")
    print(json.dumps({"patched_units": patched, "file": str(path)}))


if __name__ == "__main__":
    main()
