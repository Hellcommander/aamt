#!/usr/bin/env python3
"""Fix Transcendence.sln so x64 solution configs build x64 project configs (not Win32)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

# Intel IJL is Win32-only; never auto-add x64 Build.0 for it (LibJPEGTurbo replaces it).
SKIP_X64_BUILD_GUIDS = {
    "ECAC7E19-ACBC-4C3C-B89A-7BC7049B6F2E",  # IntelJPEGUtil
}


def main() -> int:
    sln = Path(sys.argv[1]).resolve()
    text = sln.read_text(encoding="utf-8", errors="ignore")
    original = text

    def fix_active(m: re.Match) -> str:
        guid = m.group(1)
        sol_cfg = m.group(2)
        proj_cfg = m.group(3)
        return f"{{{guid}}}.{sol_cfg}|x64.ActiveCfg = {proj_cfg}|x64"

    text2, n1 = re.subn(
        r"\{([0-9A-Fa-f-]+)\}\.([^|\r\n]+)\|x64\.ActiveCfg = ([^|\r\n]+)\|Win32",
        fix_active,
        text,
    )
    text = text2

    lines = text.splitlines(keepends=True)
    out = []
    added = 0
    removed = 0
    for i, line in enumerate(lines):
        m_intel = re.match(
            r"\s*\{([0-9A-Fa-f-]+)\}\.([^|\r\n]+)\|x64\.Build\.0 = ",
            line.rstrip("\r\n"),
        )
        if m_intel and m_intel.group(1).upper() in SKIP_X64_BUILD_GUIDS:
            removed += 1
            continue

        out.append(line)
        m = re.match(
            r"\s*\{([0-9A-Fa-f-]+)\}\.([^|\r\n]+)\|x64\.ActiveCfg = ([^|\r\n]+)\|x64\s*$",
            line.rstrip("\r\n"),
        )
        if not m:
            continue
        guid, sol_cfg, proj_cfg = m.group(1), m.group(2), m.group(3)
        if guid.upper() in SKIP_X64_BUILD_GUIDS:
            continue
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        if f"{{{guid}}}.{sol_cfg}|x64.Build.0" in nxt:
            continue
        if sol_cfg in (
            "Debug For Contributors",
            "Preview For Contributors",
            "Debug",
            "Release",
        ):
            indent = re.match(r"^(\s*)", line).group(1)
            out.append(f"{indent}{{{guid}}}.{sol_cfg}|x64.Build.0 = {proj_cfg}|x64\n")
            added += 1

    text = "".join(out)
    if text != original:
        sln.write_text(text, encoding="utf-8")
        print(
            f"Fixed ActiveCfg Win32->x64: {n1}; added Build.0: {added}; "
            f"removed IntelJPEG x64 Build.0: {removed}"
        )
    else:
        print("No sln changes needed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
