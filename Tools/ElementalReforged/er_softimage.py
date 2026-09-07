#!/usr/bin/env python3
"""
Softimage Mod Tool helpers for the Elemental Reforged Havok mesh pipeline.

Community path:
  Blender fit -> FBX -> Softimage Mod Tool 7.5 (import FBX)
  -> Havok Content Tools 7.1 Filter Manager (from Softimage or standalone)
  -> Write to Platform -> Packfile -> .hkb

HCT ships XSI plugins under HavokContentTools/Application/. Softimage only
loads them if that tree is present as an Addon, e.g.:
  Softimage_Mod_Tool_7.5/Addons/HavokContentTools/Application/...
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

KNOWN_SOFTIMAGE_ROOTS = [
    Path(r"F:\tools\mod_tools\Softimage\Softimage_Mod_Tool_7.5"),
    Path(r"C:\Softimage\Softimage_Mod_Tool_7.5"),
    Path(r"C:\Program Files (x86)\Softimage\Softimage_Mod_Tool_7.5"),
    Path(r"C:\Program Files\Softimage\Softimage_Mod_Tool_7.5"),
]

XSI_REL = Path("Application") / "bin" / "xsi.exe"
FBX_PLUGIN_REL = Path("Application") / "Plugins" / "FBXXSI.32.dll"
ADDON_NAME = "HavokContentTools"
HCT_XSI_MARKERS = (
    Path("Application") / "Plugins" / "hctXsiSceneExport.dll",
    Path("Application") / "Plugins" / "hctXsiPhysics.dll",
    Path("Application") / "toolbars" / "HavokToolbar.xsitb",
)


def _file_version(exe: Path) -> dict[str, str]:
    # Always emit four lines; empty ProductVersion is common on Mod Tool builds.
    ps = (
        f"$v=[System.Diagnostics.FileVersionInfo]::GetVersionInfo('{exe}');"
        "@($v.ProductName,$v.ProductVersion,$v.FileVersion,$v.FileDescription) | "
        "ForEach-Object { if ($null -eq $_) { '' } else { $_ } }"
    )
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        lines = (r.stdout or "").splitlines()
        while len(lines) < 4:
            lines.append("")
        return {
            "productName": lines[0].strip(),
            "productVersion": lines[1].strip(),
            "fileVersion": lines[2].strip(),
            "fileDescription": lines[3].strip(),
        }
    except Exception:
        return {}


def resolve_softimage_root(cfg: dict[str, Any] | None = None) -> Optional[Path]:
    if cfg:
        raw = cfg.get("softimagePath") or cfg.get("xsiPath")
        if raw:
            p = Path(raw)
            if (p / XSI_REL).is_file():
                return p
            if p.is_file() and p.name.lower() == "xsi.exe":
                return p.parent.parent.parent
    env = os.environ.get("XSI_ROOT") or os.environ.get("SOFTIMAGE_MOD_TOOL")
    if env:
        p = Path(env)
        if (p / XSI_REL).is_file():
            return p
    for root in KNOWN_SOFTIMAGE_ROOTS:
        if (root / XSI_REL).is_file():
            return root
    return None


def softimage_exe(cfg: dict[str, Any] | None = None) -> Optional[Path]:
    root = resolve_softimage_root(cfg)
    if not root:
        return None
    exe = root / XSI_REL
    return exe if exe.is_file() else None


def resolve_havok_root(cfg: dict[str, Any] | None = None) -> Optional[Path]:
    try:
        from er_havok import resolve_havok_root as _havok_root

        return _havok_root(cfg)
    except Exception:
        raw = (cfg or {}).get("havokPath")
        return Path(raw) if raw else None


def hct_has_xsi_plugins(hct_root: Optional[Path]) -> dict[str, Any]:
    info: dict[str, Any] = {"ok": False, "root": str(hct_root) if hct_root else None, "files": []}
    if not hct_root:
        return info
    found = []
    for rel in HCT_XSI_MARKERS:
        p = hct_root / rel
        if p.is_file():
            found.append(rel.as_posix())
    info["files"] = found
    info["ok"] = len(found) >= 1
    return info


def softimage_addon_path(xsi_root: Path) -> Path:
    return xsi_root / "Addons" / ADDON_NAME


def find_havok_xsi_plugins(root: Path) -> list[str]:
    """Return relative paths that look like installed HCT Softimage plugins."""
    hits: list[str] = []
    search_roots = [
        root / "Addons",
        root / "Application" / "Plugins",
        root / "Application" / "bin",
    ]
    keys = ("havok", "hct", "hkx", "hkb")
    for base in search_roots:
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if not p.is_file():
                continue
            name = p.name.lower()
            if any(k in name for k in keys):
                hits.append(str(p.relative_to(root)))
    return hits


def probe_softimage(cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    root = resolve_softimage_root(cfg)
    exe = softimage_exe(cfg)
    hct = resolve_havok_root(cfg)
    hct_xsi = hct_has_xsi_plugins(hct)
    info: dict[str, Any] = {
        "root": str(root) if root else None,
        "xsi": str(exe) if exe else None,
        "ok": bool(exe),
        "fileVersion": None,
        "fbxPlugin": False,
        "havokPlugins": [],
        "havokPluginsOk": False,
        "hctXsiPlugins": hct_xsi,
        "addonPath": None,
        "addonLinked": False,
        "notes": [],
    }
    if not exe or not root:
        info["notes"].append(
            "Softimage Mod Tool not found. Set softimagePath in monster_race_config.json"
        )
        return info

    ver = _file_version(exe)
    info.update(ver)
    info["fileVersion"] = ver.get("fileVersion") or None

    fbx = root / FBX_PLUGIN_REL
    info["fbxPlugin"] = fbx.is_file()
    if info["fbxPlugin"]:
        info["notes"].append(f"FBX importer present: {FBX_PLUGIN_REL.as_posix()}")
    else:
        info["notes"].append("FBX plugin missing (expected Application/Plugins/FBXXSI.32.dll)")

    addon = softimage_addon_path(root)
    info["addonPath"] = str(addon)
    info["addonLinked"] = addon.exists()

    plugins = find_havok_xsi_plugins(root)
    info["havokPlugins"] = plugins
    info["havokPluginsOk"] = bool(plugins)

    if hct_xsi.get("ok"):
        info["notes"].append(
            f"HCT package includes XSI plugins ({len(hct_xsi['files'])} markers) at {hct}"
        )
    else:
        info["notes"].append(
            "HCT package has no Application/Plugins/hctXsi*.dll - need full HCT with XSI components"
        )

    if plugins:
        info["notes"].append(f"Softimage Addons has Havok files: {len(plugins)}")
    elif hct_xsi.get("ok"):
        info["notes"].append(
            f"XSI plugins are in HCT but not under Softimage Addons. "
            f"Run: python monster_race_tool.py softimage --install-havok"
        )
    else:
        info["notes"].append("No HCT Softimage plugins available to link.")

    fv = (info.get("fileVersion") or info.get("productVersion") or "")
    if fv.startswith("7.5") or "7.5" in fv:
        info["notes"].append("Softimage Mod Tool 7.5 detected (good match for HCT 7.1 era).")
    return info


def install_havok_addon(cfg: dict[str, Any] | None = None, copy: bool = False) -> int:
    """
    Make Softimage load HCT XSI plugins by placing Addons/HavokContentTools.

    Default: directory junction to havokPath (keeps one copy).
    --copy: duplicate Application tree only.
    """
    xsi = resolve_softimage_root(cfg)
    hct = resolve_havok_root(cfg)
    if not xsi:
        print("Softimage root not found.", file=sys.stderr)
        return 1
    if not hct or not hct_has_xsi_plugins(hct).get("ok"):
        print("HCT XSI plugins not found under havokPath.", file=sys.stderr)
        return 1

    addons = xsi / "Addons"
    addons.mkdir(parents=True, exist_ok=True)
    dest = softimage_addon_path(xsi)

    if dest.exists() or dest.is_symlink():
        print(f"Removing existing addon at {dest}")
        # Junctions often report as dirs; rmdir works for empty junctions on Windows
        try:
            if dest.is_symlink():
                dest.unlink()
            else:
                try:
                    dest.rmdir()
                except OSError:
                    shutil.rmtree(dest)
        except OSError as exc:
            print(f"Could not remove {dest}: {exc}", file=sys.stderr)
            return 1

    if copy:
        # Softimage only needs Application (+ optional Data) as addon content
        dest.mkdir(parents=True, exist_ok=True)
        for sub in ("Application", "Data"):
            src = hct / sub
            if src.is_dir():
                shutil.copytree(src, dest / sub, dirs_exist_ok=True)
        print(f"Copied HCT Application/Data -> {dest}")
    else:
        # Junction whole HCT root as addon (Application/ is what Softimage reads)
        r = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(dest), str(hct)],
            capture_output=True,
            text=True,
            check=False,
        )
        if r.returncode != 0:
            print(r.stdout)
            print(r.stderr, file=sys.stderr)
            print("Junction failed; falling back to copy...", file=sys.stderr)
            return install_havok_addon(cfg, copy=True)
        print(f"Linked Softimage addon:\n  {dest}\n  -> {hct}")

    plugins = find_havok_xsi_plugins(xsi)
    print(f"Softimage now sees {len(plugins)} Havok-related file(s).")
    print("Restart Softimage; look for the Havok toolbar / menu.")
    return 0 if plugins else 1


def open_softimage(cfg: dict[str, Any] | None = None, scene: Optional[Path] = None) -> int:
    exe = softimage_exe(cfg)
    if not exe:
        print("Softimage not found. Set softimagePath.", file=sys.stderr)
        return 1
    args = [str(exe)]
    if scene:
        args.append(str(scene))
    env = os.environ.copy()
    bin_dir = str(exe.parent)
    env["PATH"] = bin_dir + os.pathsep + env.get("PATH", "")
    subprocess.Popen(args, cwd=bin_dir, env=env)
    print(f"Launched: {exe}")
    return 0


if __name__ == "__main__":
    from er_tool_lib import load_config

    cfg = load_config()
    if "--install-havok" in sys.argv:
        raise SystemExit(install_havok_addon(cfg, copy="--copy" in sys.argv))
    info = probe_softimage(cfg)
    print(json.dumps(info, indent=2))
    if "--open" in sys.argv:
        raise SystemExit(open_softimage(cfg))
