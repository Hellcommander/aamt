#!/usr/bin/env python3
"""Flip TreatWarningAsError=false for all x64 ItemDefinitionGroups under an API tree."""
from __future__ import annotations

import re
import sys
from pathlib import Path


def main() -> int:
    root = Path(sys.argv[1]).resolve()
    total = 0
    files = 0
    pat = re.compile(
        r'<ItemDefinitionGroup Condition="[^"]*\|x64[^"]*">[\s\S]*?</ItemDefinitionGroup>'
    )
    for p in root.rglob("*.vcxproj"):
        text = p.read_text(encoding="utf-8", errors="ignore")
        flipped = 0

        def flip(m: re.Match) -> str:
            nonlocal flipped
            g2, n = re.subn(
                r"<TreatWarningAsError>true</TreatWarningAsError>",
                "<TreatWarningAsError>false</TreatWarningAsError>",
                m.group(0),
            )
            flipped += n
            return g2

        text2, _ = pat.subn(flip, text)
        if flipped:
            p.write_text(text2, encoding="utf-8")
            files += 1
            total += flipped
            print(f"{flipped:3}  {p.relative_to(root)}")
    print(f"TOTAL {total} flips in {files} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
