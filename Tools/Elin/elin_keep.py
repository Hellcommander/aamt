#!/usr/bin/env python3
"""Keep what is already in the mod.

The deploy scripts (elin_deploy_real_assets.py, elin_deploy_portraits.py, elin_trellis_unity.py deploy-ui /
deploy-icons) bake files into the mod from concepts staged months ago. Files in the mod may since have been fixed by
hand or by the mod's own tools, so by default a deploy only ADDS: a file that exists is left alone.

    if may_write(dest):
        ...write dest...

Switches (command line of the calling script, or the environment for a whole batch):
    --force     / AAMT_ELIN_FORCE=1     replace existing files; each one is first copied to
                                        Tools/Elin/Output/ModBackup/<time>/<drive>/<path>
    --dry-run   / AAMT_ELIN_DRY_RUN=1   write nothing, only say what would be added, kept or replaced
"""
from __future__ import annotations

import atexit
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Dict, List

FORCE = "--force" in sys.argv or os.environ.get("AAMT_ELIN_FORCE", "") == "1"
DRY_RUN = "--dry-run" in sys.argv or os.environ.get("AAMT_ELIN_DRY_RUN", "") == "1"
BACKUP_ROOT = Path(__file__).resolve().parent / "Output" / "ModBackup" / time.strftime("%Y%m%d_%H%M%S")

_seen: Dict[str, List[str]] = {"added": [], "kept": [], "replaced": []}


def add_arguments(ap) -> None:
    """Declare the two switches on an argparse parser (they are read from sys.argv, this only documents them)."""
    ap.add_argument("--force", action="store_true", help="replace files that already exist (they are backed up first)")
    ap.add_argument("--dry-run", action="store_true", help="write nothing; list what would be added, kept or replaced")


def may_write(dest: Path) -> bool:
    """True if the caller should write `dest` now. An existing file is kept unless --force, and then backed up first."""
    dest = Path(dest)
    if not dest.exists():
        _seen["added"].append(str(dest))
        return not DRY_RUN
    if not FORCE:
        _seen["kept"].append(str(dest))
        return False
    _seen["replaced"].append(str(dest))
    if DRY_RUN:
        return False
    full = dest.resolve()
    copy = BACKUP_ROOT / full.drive.rstrip(":") / full.relative_to(full.anchor)
    copy.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(full, copy)
    return True


def _report() -> None:
    if not any(_seen.values()):
        return
    verb = "would be " if DRY_RUN else ""
    print(f"[keep] {len(_seen['added'])} {verb}added, {len(_seen['kept'])} kept as they are, "
          f"{len(_seen['replaced'])} {verb}replaced" + ("  (dry run: nothing written)" if DRY_RUN else ""))
    for kind in ("added", "replaced"):
        for p in _seen[kind][:40]:
            print(f"[keep]   {kind}: {p}")
        if len(_seen[kind]) > 40:
            print(f"[keep]   ... and {len(_seen[kind]) - 40} more {kind}")
    if _seen["kept"] and not FORCE:
        print("[keep] existing files were left alone; pass --force to replace them (a backup is made)")
    if _seen["replaced"] and not DRY_RUN:
        print(f"[keep] backups of the replaced files: {BACKUP_ROOT}")


atexit.register(_report)
