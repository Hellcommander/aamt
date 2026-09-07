#!/usr/bin/env python3
"""Headless Unity pack of Workshop Asset/ UnityFS (crcc_spell_particle).

Requires the Elin-matching editor at E:\\tools\\Unity_Editor\\2021.3.45f2.

  python elin_unity_pack_asset.py
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

_SHARED = Path(__file__).resolve().parent.parent / "Shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from unity_version import resolve_for_game  # noqa: E402

_ELIN_GAME = Path(r"E:\SteamLibrary\steamapps\common\Elin")
_MOD = Path(r"E:\SteamLibrary\steamapps\common\Elin\Package\Mod\CustomRaceClassCreator")
_LOG = Path(__file__).resolve().parent / "Output" / "unity_asset_pack.log"
_METHOD = "CustomRaceClassCreator.Editor.BuildWorkshopAssetFolder.Build"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mod-path", default=str(_MOD))
    ap.add_argument("--timeout", type=int, default=1200)
    args = ap.parse_args()
    mod = Path(args.mod_path)
    ver, match = resolve_for_game(_ELIN_GAME)
    exe = match.editor_exe
    print(f"[unity] elin={ver} editor={exe} exact={match.exact}")
    if not exe or not Path(exe).is_file():
        print(match.install_hint)
        return 2

    _LOG.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        exe,
        "-batchmode",
        "-nographics",
        "-quit",
        "-projectPath",
        str(mod),
        "-executeMethod",
        _METHOD,
        "-logFile",
        str(_LOG),
    ]
    print("[unity]", " ".join(cmd), flush=True)
    try:
        proc = subprocess.run(cmd, timeout=args.timeout)
    except subprocess.TimeoutExpired:
        print(f"[unity] timed out after {args.timeout}s — see {_LOG}")
        return 3

    bundle = mod / "Asset" / "crcc_spell_particle"
    print(f"[unity] exit={proc.returncode} log={_LOG}")
    if bundle.is_file():
        magic = bundle.read_bytes()[:7]
        print(f"[unity] bundle={bundle} bytes={bundle.stat().st_size} magic={magic!r}")
        if magic != b"UnityFS":
            print("[unity] WARNING: not a UnityFS file")
            return 4
    else:
        print("[unity] bundle missing")
        # Tail the log for the actual error
        if _LOG.is_file():
            lines = _LOG.read_text(encoding="utf-8", errors="replace").splitlines()
            for line in lines[-40:]:
                print(line)
        return proc.returncode or 5
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
