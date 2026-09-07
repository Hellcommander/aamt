#!/usr/bin/env python3
"""
Audit-X64Libs.py — fail if required .lib files are machine(x86) when building x64.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def find_dumpbin() -> Path | None:
    vs = Path(r"D:\tools\Microsoft Visual Studio\18\Community\VC\Tools\MSVC")
    if vs.is_dir():
        hits = sorted(vs.glob("*/bin/Hostx64/x64/dumpbin.exe"), reverse=True)
        if hits:
            return hits[0]
    return None


def lib_machines(dumpbin: Path, lib: Path) -> list[str]:
    r = subprocess.run(
        [str(dumpbin), "/HEADERS", str(lib)],
        capture_output=True,
        text=True,
        errors="ignore",
    )
    machines = []
    for line in (r.stdout or "").splitlines():
        if "machine (" in line.lower():
            machines.append(line.strip())
    return machines


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api-root", required=True)
    args = ap.parse_args()
    root = Path(args.api_root).resolve()
    dumpbin = find_dumpbin()
    if not dumpbin:
        print("WARN: dumpbin not found — skip lib arch audit")
        return 0

    libs = [
        root / "Alchemy" / "LibJPEGTurboUtil" / "turbojpeg.lib",
        root / "Alchemy" / "LibJPEGTurboUtil" / "LibJPEGTurboUtil.lib",
        root / "Alchemy" / "LibJPEGTurboUtil" / "jpeg.lib",
    ]
    bad = []
    for lib in libs:
        if not lib.is_file():
            print(f"  skip missing {lib.name}")
            continue
        machines = lib_machines(dumpbin, lib)
        print(f"  {lib.name}: {machines[:3]}")
        joined = " ".join(machines).lower()
        if "x86" in joined and "x64" not in joined:
            bad.append(str(lib))

    if bad:
        print("ERROR: x86-only libs in x64 build:", file=sys.stderr)
        for b in bad:
            print(f"  {b}", file=sys.stderr)
        return 1
    print("Lib arch audit OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
