#!/usr/bin/env python3
"""Point x64 Lib.OutputFile at $(OutDir) so x64 libs don't overwrite/collide with Win32 Debug\\."""
from __future__ import annotations

import re
import sys
from pathlib import Path


def main() -> int:
    root = Path(sys.argv[1]).resolve()
    files = 0
    flips = 0
    pat = re.compile(
        r'(<ItemDefinitionGroup Condition="[^"]*\|x64[^"]*">[\s\S]*?</ItemDefinitionGroup>)'
    )

    def fix_group(m: re.Match) -> str:
        nonlocal flips
        g = m.group(1)
        g2, n = re.subn(
            r"<OutputFile>[^<]*</OutputFile>",
            "<OutputFile>$(OutDir)$(TargetName)$(TargetExt)</OutputFile>",
            g,
        )
        flips += n
        return g2

    for p in root.rglob("*.vcxproj"):
        text = p.read_text(encoding="utf-8", errors="ignore")
        before = flips
        text2, _ = pat.subn(fix_group, text)
        if flips > before:
            p.write_text(text2, encoding="utf-8")
            files += 1
            print(f"{flips - before:3}  {p.relative_to(root)}")
    print(f"TOTAL {flips} OutputFile fixes in {files} projects")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
