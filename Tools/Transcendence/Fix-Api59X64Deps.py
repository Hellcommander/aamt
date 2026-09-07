#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

DEFAULT_API = Path(
    r"D:\games\Steam\steamapps\common\Transcendence"
    r"\game_and_dlc_source\TranscendenceDev-integration-API59"
)

API: Path = DEFAULT_API


def fix_zlib() -> None:
    z = API / "Alchemy" / "zlib-1.2.7" / "contrib" / "vstudio" / "vc10" / "zlibstat.vcxproj"
    t = z.read_text(encoding="utf-8")
    n = t.count("v140_xp")
    z.write_text(t.replace("v140_xp", "v145"), encoding="utf-8")
    print(f"zlibstat: replaced {n} v140_xp -> v145")


def fix_jpeg_itemdefs() -> None:
    p = API / "Alchemy" / "LibJPEGTurboUtil" / "LibJPEGTurboUtil.vcxproj"
    t = p.read_text(encoding="utf-8")
    if "=='Debug For Contributors|x64'" in t and "ItemDefinitionGroup Condition" in t:
        # Only count ItemDefinitionGroups, not PropertyGroups
        defs = re.findall(
            r"<ItemDefinitionGroup Condition=\"'\$\(Configuration\)\|\$\(Platform\)'=='Debug For Contributors\|x64'\">",
            t,
        )
        if defs:
            print("JPEG: Contributors|x64 ItemDefinitionGroup already present")
            return

    def clone(src_cfg: str, dst_cfg: str) -> str:
        pat = re.compile(
            rf"(<ItemDefinitionGroup Condition=\"'\$\(Configuration\)\|\$\(Platform\)'=='{re.escape(src_cfg)}'\">.*?</ItemDefinitionGroup>)",
            re.S,
        )
        m = pat.search(t)
        if not m:
            raise SystemExit(f"missing ItemDefinitionGroup for {src_cfg}")
        return m.group(1).replace(f"=='{src_cfg}'", f"=='{dst_cfg}'")

    clone_x64 = clone("Debug|x64", "Debug For Contributors|x64")
    clone_w32 = clone("Debug|Win32", "Debug For Contributors|Win32")
    if "AdditionalIncludeDirectories" not in clone_w32:
        clone_w32 = clone_w32.replace(
            "<ConformanceMode>true</ConformanceMode>",
            "<ConformanceMode>true</ConformanceMode>\n"
            "      <AdditionalIncludeDirectories>.\\include;..\\Include;%(AdditionalIncludeDirectories)</AdditionalIncludeDirectories>",
            1,
        )

    insert = "\n" + clone_w32 + "\n" + clone_x64 + "\n"
    anchor = "<ItemDefinitionGroup Condition=\"'$(Configuration)|$(Platform)'=='Release|x64'\">"
    idx = t.find(anchor)
    if idx < 0:
        raise SystemExit("Release|x64 ItemDefinitionGroup anchor missing")
    p.write_text(t[:idx] + insert + t[idx:], encoding="utf-8")
    print("JPEG: added Contributors ItemDefinitionGroups")


def main() -> None:
    global API
    ap = argparse.ArgumentParser()
    ap.add_argument("--api-root", default=str(DEFAULT_API))
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args, _ = ap.parse_known_args()
    API = Path(args.api_root).resolve()
    if args.dry_run:
        print(f"[DryRun] would patch deps under {API}")
        return
    print(f"api-root: {API}")
    fix_zlib()
    fix_jpeg_itemdefs()
    print("OK")


if __name__ == "__main__":
    main()
