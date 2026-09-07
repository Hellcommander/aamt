#!/usr/bin/env python3
"""Ucupaint availability, enablement, and real-texture bake onto mesh UVs.

Ucupaint composites SD / Material Maker / TRELLIS images as layers on a mesh's
UVs, then bakes. That bake lives in ``ucupaint_bake.py`` (Blender background).
Do not use Common/bake_texture.py for this, and do not invent procedural noise
skins. Caves of Qud Space-Time Vortex generators are a separate, unused path.

From a normal process:
  python ucupaint_support.py --status
  python ucupaint_support.py --bake --mesh ship.glb --out-dir out --color d.png

From inside Blender:
  from ucupaint_support import ensure_enabled
  ensure_enabled()
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

_SHARED = Path(__file__).resolve().parent
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

ADDON_MODULE = "ucupaint"


def _blender_roots() -> List[Path]:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        return []
    base = Path(appdata) / "Blender Foundation" / "Blender"
    if not base.is_dir():
        return []
    return sorted((d for d in base.iterdir() if d.is_dir()), key=lambda d: d.name, reverse=True)


def installations() -> List[Dict[str, object]]:
    """Every Blender user-config version and whether Ucupaint is present in it."""
    found = []
    for ver in _blender_roots():
        legacy = ver / "scripts" / "addons" / ADDON_MODULE
        extension = ver / "extensions" / "user_default" / ADDON_MODULE
        path = legacy if legacy.is_dir() else (extension if extension.is_dir() else None)
        found.append(
            {
                "blender_version": ver.name,
                "installed": path is not None,
                "path": str(path) if path else None,
                "kind": "addon" if path == legacy else ("extension" if path else None),
            }
        )
    return found


def addon_dir() -> Optional[Path]:
    try:
        from tool_paths import ucupaint_addon_dir

        return ucupaint_addon_dir()
    except Exception:
        for entry in installations():
            if entry["installed"]:
                return Path(str(entry["path"]))
    return None


def is_installed() -> bool:
    return any(e["installed"] for e in installations())


def version() -> Optional[List[int]]:
    """Read bl_info version without importing the add-on."""
    d = addon_dir()
    if not d:
        return None
    init = d / "__init__.py"
    if not init.is_file():
        return None
    import re

    m = re.search(r'"version"\s*:\s*\(([^)]*)\)', init.read_text(encoding="utf-8", errors="replace"))
    if not m:
        return None
    try:
        return [int(x.strip()) for x in m.group(1).split(",") if x.strip()]
    except ValueError:
        return None


MAP_KEYS = ("color", "diffuse", "roughness", "metallic", "normal", "emission")
BAKE_SCRIPT = _SHARED / "ucupaint_bake.py"


def discover_maps(skin_dir: Union[str, Path], name: str) -> Dict[str, Path]:
    """Find real PBR PNGs named ``{name}_{kind}.png`` (no generated noise)."""
    root = Path(skin_dir)
    found: Dict[str, Path] = {}
    aliases = {
        "color": ("color", "diffuse", "albedo"),
        "roughness": ("roughness", "rough"),
        "metallic": ("metallic", "metal"),
        "normal": ("normal", "nrm"),
        "emission": ("emission", "emit"),
    }
    for kind, suffixes in aliases.items():
        for suffix in suffixes:
            hit = root / f"{name}_{suffix}.png"
            if hit.is_file():
                found[kind] = hit
                break
    return found


def bake_onto_mesh(
    mesh: Union[str, Path],
    out_dir: Union[str, Path],
    *,
    maps: Optional[Dict[str, Union[str, Path]]] = None,
    skin_dir: Optional[Union[str, Path]] = None,
    name: str = "",
    size: int = 1024,
    ao: bool = True,
    blender: Optional[str] = None,
    timeout: float = 1800.0,
) -> Dict[str, Any]:
    """Launch Blender to bake real maps onto ``mesh`` UVs via Ucupaint."""
    import subprocess

    mesh_path = Path(mesh)
    dest = Path(out_dir)
    dest.mkdir(parents=True, exist_ok=True)
    stem = name or mesh_path.stem
    resolved: Dict[str, Path] = {}
    if maps:
        for key, val in maps.items():
            p = Path(val)
            if p.is_file():
                kind = "color" if key == "diffuse" else key
                resolved[kind] = p
    if skin_dir:
        for kind, p in discover_maps(skin_dir, stem).items():
            resolved.setdefault(kind, p)
    if not resolved:
        raise RuntimeError("Ucupaint bake needs real maps (SD/MM/TRELLIS PNG); none found")
    if not BAKE_SCRIPT.is_file():
        raise RuntimeError(f"missing {BAKE_SCRIPT}")

    exe = blender
    if not exe:
        try:
            from tool_paths import find_blender as _fb

            exe = _fb()
        except Exception:
            exe = None
    if not exe:
        raise RuntimeError("Blender not found")

    cmd = [
        str(exe),
        "--background",
        "--python",
        str(BAKE_SCRIPT),
        "--",
        "--mesh",
        str(mesh_path),
        "--out-dir",
        str(dest),
        "--size",
        str(int(size)),
        "--name",
        stem,
    ]
    if ao:
        cmd.append("--ao")
    else:
        cmd.append("--no-ao")
    if resolved.get("color"):
        cmd += ["--color", str(resolved["color"])]
    for key in ("roughness", "metallic", "normal", "emission"):
        if resolved.get(key):
            cmd += [f"--{key}", str(resolved[key])]

    print(f"[ucupaint] blender bake {mesh_path.name} -> {dest}")
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if proc.stdout:
        print(proc.stdout[-4000:])
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "")[-800:]
        raise RuntimeError(f"Ucupaint bake failed ({proc.returncode}): {err}")

    report: Dict[str, Any] = {"ok": True, "maps": {}, "glb": "", "blend": ""}
    sidecar = dest / f"{stem}_ucupaint.json"
    if sidecar.is_file():
        try:
            report.update(json.loads(sidecar.read_text(encoding="utf-8")))
        except Exception:
            pass
    report["ok"] = bool(report.get("maps"))
    return report


def ensure_enabled() -> bool:
    """Enable Ucupaint in the running Blender session. Safe to call repeatedly."""
    try:
        import bpy
    except ImportError as exc:
        raise RuntimeError("ensure_enabled() must run inside Blender") from exc

    if ADDON_MODULE in bpy.context.preferences.addons:
        return True
    try:
        bpy.ops.preferences.addon_enable(module=ADDON_MODULE)
    except Exception as exc:
        print(f"[ucupaint] enable failed: {exc}", file=sys.stderr)
        return False
    return ADDON_MODULE in bpy.context.preferences.addons


def status() -> Dict[str, object]:
    return {
        "installed": is_installed(),
        "version": version(),
        "addon_dir": str(addon_dir()) if addon_dir() else None,
        "installations": installations(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Ucupaint availability + bake")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--bake", action="store_true")
    parser.add_argument("--mesh", default="")
    parser.add_argument("--out-dir", default="")
    parser.add_argument("--color", default="")
    parser.add_argument("--roughness", default="")
    parser.add_argument("--metallic", default="")
    parser.add_argument("--normal", default="")
    parser.add_argument("--size", type=int, default=1024)
    parser.add_argument("--name", default="")
    args = parser.parse_args()

    if args.bake:
        maps = {k: getattr(args, k) for k in ("color", "roughness", "metallic", "normal") if getattr(args, k)}
        report = bake_onto_mesh(args.mesh, args.out_dir, maps=maps, name=args.name, size=args.size)
        print(json.dumps(report, indent=2))
        return 0 if report.get("ok") else 1

    report = status()
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Ucupaint installed: {report['installed']}  version={report['version']}")
        for entry in report["installations"]:
            flag = "YES" if entry["installed"] else "no "
            print(f"  Blender {entry['blender_version']}: {flag}  {entry['path'] or ''}")
    return 0 if report["installed"] else 1


if __name__ == "__main__":
    sys.exit(main())
