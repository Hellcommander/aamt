#!/usr/bin/env python3
"""
Prepare-X64Workspace.py

Copy an official TranscendenceDev-integration-APIxx tree into an isolated build
workspace, then optionally run x64 autofix overlays there.

Official source trees are left untouched. Users who run the patcher later can
mix whatever they want into their own game/build.

Usage:
  python Prepare-X64Workspace.py --api-root <official> --workspace <dir> [--sync] [--apply-fixes] [--force]
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

SKIP_DIRS = {
    ".git",
    ".vs",
    ".claude",
    "x64",
    "Debug",
    "Release",
    "ipch",
    "_v3_backups",
}


def robocopy(src: Path, dst: Path, sync: bool) -> int:
    dst.mkdir(parents=True, exist_ok=True)
    # /E copy subdirs; /XD skip build junk; /NFL /NDL quieter; /NJH /NJS
    xd = []
    for d in SKIP_DIRS:
        xd += ["/XD", d]
    # Also skip configuration-named dirs
    for d in (
        "Debug For Contributors",
        "Preview For Contributors",
        "SteamRelease",
        "SteamDebug",
    ):
        xd += ["/XD", d]

    cmd = [
        "robocopy",
        str(src),
        str(dst),
        "/E",
        "/XO",  # exclude older — keep workspace newer patched files unless --sync
        "/R:1",
        "/W:1",
        "/NFL",
        "/NDL",
        "/NJH",
        "/NJS",
    ] + xd
    if sync:
        # Full refresh from official then re-apply fixes
        cmd = [
            "robocopy",
            str(src),
            str(dst),
            "/MIR",
            "/R:1",
            "/W:1",
            "/NFL",
            "/NDL",
            "/NJH",
            "/NJS",
        ] + xd

    print(" ".join(cmd))
    r = subprocess.run(cmd)
    # robocopy: 0-7 success-ish
    return 0 if r.returncode < 8 else r.returncode


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api-root", required=True)
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--sync", action="store_true", help="Mirror from official (wipes workspace overlay)")
    ap.add_argument("--apply-fixes", action="store_true", help="Run v2+v3 autofix on workspace")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    official = Path(args.api_root).resolve()
    workspace = Path(args.workspace).resolve()
    tools = Path(__file__).resolve().parent

    if not (official / "Transcendence" / "Transcendence.sln").is_file():
        print(f"ERROR: official tree missing sln: {official}", file=sys.stderr)
        return 2

    need_copy = args.sync or not (workspace / "Transcendence" / "Transcendence.sln").is_file()
    if need_copy:
        print(f"Syncing official -> workspace\n  {official}\n  {workspace}")
        code = robocopy(official, workspace, sync=args.sync or not workspace.exists())
        if code != 0:
            print(f"robocopy failed: {code}", file=sys.stderr)
            return code
    else:
        print(f"Workspace exists (use --sync to refresh from official): {workspace}")

    if args.apply_fixes:
        py = sys.executable
        for script, extra in (
            ("Fix-TranscendenceX64.py", [str(workspace)]),
            ("Fix-TranscendenceX64V3.py", ["--api-root", str(workspace)]),
            ("Fix-Api59BuildProjects.py", ["--api-root", str(workspace)]),
            ("Fix-Api59X64Deps.py", ["--api-root", str(workspace)]),
        ):
            sp = tools / script
            if not sp.is_file():
                print(f"skip missing {script}")
                continue
            cmd = [py, str(sp)] + extra
            if args.force:
                cmd.append("--force")
            print("RUN", " ".join(cmd))
            r = subprocess.run(cmd)
            if r.returncode != 0:
                return r.returncode

    # provenance note
    note = workspace / "X64_WORKSPACE_README.txt"
    note.write_text(
        "This directory is an isolated x64 build workspace.\n"
        "Official kronosaur / integration trees are not modified here.\n"
        "The Transcendence ApiSwitcher / patcher applies optional x64 overlays.\n"
        "You are free to mix, keep, or discard these changes in your own game build.\n"
        f"Official source: {official}\n",
        encoding="utf-8",
    )
    print(f"Workspace ready: {workspace}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
