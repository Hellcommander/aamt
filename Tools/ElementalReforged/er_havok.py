#!/usr/bin/env python3
"""
Havok Content Tools helpers for Elemental Reforged .hkb mesh export.

Elemental / Reforged expects HCT **7.1 (32-bit)** Packfile output (used as .hkb).
Tagfile (.hkt) will not load in-game.

Typical pipeline:
  Blender (fit mesh to race armature) → FBX
  → Softimage Mod Tool / 3ds Max / Maya + HCT 7.1 plugins
  → Standalone Filter Manager → Write to Platform → Packfile
  → place under mod Gfx/HKB/... as .hkb
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parent

KNOWN_HAVOK_ROOTS = [
    Path(r"D:\games\Modding\Havok\Havok_7_1_32\HavokContentTools"),
    Path(r"D:\games\Modding\Havok_7_1_32\HavokContentTools"),
    Path(r"D:\games\Modding\Havok\HavokContentTools"),
    Path(r"C:\Program Files (x86)\Havok\HavokContentTools"),
    Path(r"C:\Program Files\Havok\HavokContentTools"),
]

FILTER_MANAGER = "hctStandAloneFilterManager.exe"
RECOMMENDED_PRODUCT = "7, 1, 0"


def resolve_havok_root(cfg: dict[str, Any] | None = None) -> Optional[Path]:
    if cfg:
        raw = cfg.get("havokPath") or cfg.get("havokContentToolsPath")
        if raw:
            p = Path(raw)
            if (p / FILTER_MANAGER).is_file():
                return p
            if p.name.lower() != "havokcontenttools" and (p / "HavokContentTools" / FILTER_MANAGER).is_file():
                return p / "HavokContentTools"
            if p.is_file() and p.name.lower() == FILTER_MANAGER.lower():
                return p.parent
    env = os.environ.get("HAVOK_CONTENT_TOOLS") or os.environ.get("HCT_ROOT")
    if env:
        p = Path(env)
        if (p / FILTER_MANAGER).is_file():
            return p
    for root in KNOWN_HAVOK_ROOTS:
        if (root / FILTER_MANAGER).is_file():
            return root
    return None


def filter_manager_exe(cfg: dict[str, Any] | None = None) -> Optional[Path]:
    root = resolve_havok_root(cfg)
    if not root:
        return None
    exe = root / FILTER_MANAGER
    return exe if exe.is_file() else None


def _file_version(exe: Path) -> dict[str, str]:
    """Read Windows FileVersionInfo via PowerShell (no pywin32 required)."""
    ps = (
        f"$v=[System.Diagnostics.FileVersionInfo]::GetVersionInfo('{exe}');"
        "Write-Output $v.ProductName;"
        "Write-Output $v.ProductVersion;"
        "Write-Output $v.FileVersion;"
        "Write-Output $v.FileDescription"
    )
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        lines = [ln.strip() for ln in (r.stdout or "").splitlines() if ln.strip()]
        if len(lines) >= 3:
            return {
                "productName": lines[0],
                "productVersion": lines[1],
                "fileVersion": lines[2],
                "fileDescription": lines[3] if len(lines) > 3 else "",
            }
    except Exception:
        pass
    return {}


def is_recommended_version(product_version: str) -> bool:
    # Accept 7, 1, 0, * or 7.1.0*
    v = product_version.replace(" ", "")
    return v.startswith("7,1,0") or v.startswith("7.1.0")


def probe_havok(cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    root = resolve_havok_root(cfg)
    exe = filter_manager_exe(cfg)
    info: dict[str, Any] = {
        "root": str(root) if root else None,
        "filterManager": str(exe) if exe else None,
        "ok": bool(exe),
        "productVersion": None,
        "recommended": False,
        "manual": None,
        "notes": [],
    }
    if not exe:
        info["notes"].append(
            "Havok Content Tools 7.1 (32-bit) not found. Set havokPath in monster_race_config.json"
        )
        return info

    ver = _file_version(exe)
    info.update(ver)
    pv = ver.get("productVersion") or ""
    info["productVersion"] = pv
    info["recommended"] = is_recommended_version(pv)
    if not info["recommended"]:
        info["notes"].append(
            f"Found HCT {pv or '?'}; Elemental modding recommends 7.1.0.x (Packfile). "
            "Newer packs (e.g. 2010.2) may export but are not the documented target."
        )
    else:
        info["notes"].append("HCT 7.1 detected - use Write to Platform -> Packfile (not Tagfile).")

    manual = (root / "Havok710ContentToolsManual.chm") if root else None
    if manual and manual.is_file():
        info["manual"] = str(manual)
    return info


def open_filter_manager(cfg: dict[str, Any] | None = None) -> int:
    exe = filter_manager_exe(cfg)
    if not exe:
        print("HCT Filter Manager not found. Set havokPath.", file=sys.stderr)
        return 1
    subprocess.Popen([str(exe)], cwd=str(exe.parent))
    print(f"Launched: {exe}")
    print_export_checklist()
    return 0


def print_export_checklist() -> None:
    print(
        """
Havok Packfile export checklist (Elemental Reforged):
  1. Author skinned mesh on the race UnitModelType armature (Blender -> FBX).
  2. Import FBX into Softimage Mod Tool 7.5 (File > Import > FBX).
  3. Open HCT 7.1 Filter Manager (from Softimage if plugins installed, else standalone).
  4. Filter chain ending in: Write to Platform -> format = Packfile (.hkx).
  5. Do NOT use Tagfile (.hkt).
  6. Copy/rename to mod: Gfx/HKB/<Race>/LHL_<Race>_<Kind>_Mesh.hkb
  7. Point GameItemTypeArtDef ModelFile at that path; AttachmentType = Skinned.
""".strip()
    )


def packfile_output_path(mod: Path, race_key: str, kind: str) -> Path:
    """Canonical mod-relative destination for a newly authored mesh."""
    name = f"LHL_{race_key}_{kind.capitalize()}_Mesh.hkb"
    return mod / "Gfx" / "HKB" / "LHL" / race_key / name


def write_export_manifest(
    out_dir: Path,
    race_key: str,
    kind: str,
    fbx_path: Path,
    target_hkb: Path,
) -> Path:
    """Write a small JSON note for the manual HCT step."""
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{race_key}_{kind}_havok_export.json"
    data = {
        "race": race_key,
        "kind": kind,
        "fbx": str(fbx_path),
        "targetHkb": str(target_hkb),
        "export": "Write to Platform -> Packfile",
        "avoid": "Tagfile (.hkt)",
        "havokVersion": "7.1.0.x",
    }
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


if __name__ == "__main__":
    from er_tool_lib import load_config

    cfg = load_config()
    info = probe_havok(cfg)
    print(json.dumps(info, indent=2))
    if "--open" in sys.argv:
        raise SystemExit(open_filter_manager(cfg))
    if "--checklist" in sys.argv:
        print_export_checklist()
