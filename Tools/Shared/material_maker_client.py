#!/usr/bin/env python3
"""Material Maker wrapper: procedural, seamless PBR maps for any game toolset.

Material Maker is the only resource in the kit that produces mathematically
clean tileable normal/roughness data (SD guesses, TRELLIS bakes low-res), so
it owns the "base material" stage of asset generation.

  python material_maker_client.py --status
  python material_maker_client.py --export fabric.ptex --out D:/out
  python material_maker_client.py --export-dir library/ --out D:/out

KNOWN LIMITATION (verified on 1.7 / Godot 4.7, this machine):
  --export-material segfaults (0xC0000005) on any graph with more than one
  connected output map, across every renderer (vulkan/d3d12/opengl3) and every
  target (Blender/Godot/Unity). Single-output graphs export fine. Treat MM as
  GUI-author-once, then let the pipeline consume the PNGs it wrote. This module
  still exposes the CLI so single-map graphs and future fixed builds work, and
  reports the crash clearly instead of silently producing nothing.

Also note: MM resolves the -o path relative to its own cwd and concatenates it
with '/', so BACKSLASH PATHS SILENTLY WRITE NOTHING. Always pass forward
slashes — export() does this for you.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

_SHARED = Path(__file__).resolve().parent
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

# MM renders its node graph on the GPU and crashes outright when VRAM is tight
# (verified: exports that succeed on an idle card fail with SD/TRELLIS resident),
# so it takes the same shared lock as the model servers.
try:
    from gpu_hub import acquire_gpu
except Exception:
    import contextlib

    def acquire_gpu(label, timeout=None, poll=2.0, enabled=True):  # type: ignore
        return contextlib.nullcontext()

# Access violation. Windows reports this as signed via PowerShell's
# $LASTEXITCODE but unsigned via Python's subprocess, so match both.
CRASH_ACCESS_VIOLATION = -1073741819
CRASH_CODES = {CRASH_ACCESS_VIOLATION, CRASH_ACCESS_VIOLATION + 2**32}

TARGETS = ("Blender", "Godot", "Unity", "Unreal")

# Map-name suffixes MM writes, normalised to the engine-neutral names the rest
# of the toolkit uses.
SUFFIX_ALIASES = {
    "albedo": "color",
    "basecolor": "color",
    "base_color": "color",
    "diffuse": "color",
    "orm": "orm",
    "normal": "normal",
    "roughness": "rough",
    "rough": "rough",
    "metallic": "metal",
    "depth": "height",
    "height": "height",
    "emission": "emissive",
    "ao": "ao",
    "occlusion": "ao",
}


def material_maker_exe() -> Optional[Path]:
    try:
        from tool_paths import material_maker_exe as _mm

        return _mm()
    except Exception:
        default = Path(r"D:\tools\Texture_Making_tools\material_maker_1_7_windows\material_maker.exe")
        return default if default.is_file() else None


def is_available() -> bool:
    return material_maker_exe() is not None


def status() -> Dict[str, object]:
    exe = material_maker_exe()
    root = exe.parent if exe else None
    examples = sorted(p.name for p in (root / "examples").glob("*.ptex")) if root and (root / "examples").is_dir() else []
    return {
        "available": exe is not None,
        "exe": str(exe) if exe else None,
        "targets": list(TARGETS),
        "examples": len(examples),
        "known_limitation": "multi-output graphs crash the 1.7 headless exporter (0xC0000005)",
    }


def classify_map(png: Path) -> Optional[str]:
    """Normalise an MM output filename to a toolkit map kind (color/normal/rough/...)."""
    stem = png.stem.lower()
    for raw, kind in sorted(SUFFIX_ALIASES.items(), key=lambda kv: -len(kv[0])):
        if stem.endswith("_" + raw):
            return kind
    return None


def export(
    ptex: Path,
    out_dir: Path,
    *,
    target: str = "Blender",
    timeout: float = 600.0,
) -> Dict[str, object]:
    """
    Export one .ptex to PNG maps.

    Returns {ok, files, maps, error}. `maps` is {kind: path} using toolkit map
    names, ready to hand to a DDS/engine converter.
    """
    exe = material_maker_exe()
    if not exe:
        return {"ok": False, "error": "Material Maker not installed", "files": [], "maps": {}}
    ptex = Path(ptex)
    if not ptex.is_file():
        return {"ok": False, "error": f"missing .ptex: {ptex}", "files": [], "maps": {}}
    if target not in TARGETS:
        return {"ok": False, "error": f"unknown target {target!r}; use one of {TARGETS}", "files": [], "maps": {}}

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    before = {p.name for p in out_dir.glob("*.png")}

    # MM joins -o with '/', so backslashes silently produce no output.
    cmd = [
        str(exe),
        "--export-material",
        "--target",
        target,
        "-o",
        out_dir.as_posix(),
        ptex.resolve().as_posix(),
    ]
    try:
        with acquire_gpu(f"MaterialMaker {ptex.name}"):
            proc = subprocess.run(cmd, cwd=str(exe.parent), capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"Material Maker timed out after {timeout:.0f}s", "files": [], "maps": {}}

    written = sorted(p for p in out_dir.glob("*.png") if p.name not in before)

    if proc.returncode in CRASH_CODES:
        return {
            "ok": False,
            "error": (
                f"Material Maker crashed (access violation) exporting {ptex.name}. "
                "Causes seen on this build: graphs with multiple output maps, and "
                "insufficient free VRAM (MM renders its graph on the GPU). Free VRAM "
                "by stopping the SD/TRELLIS servers, or export from the GUI instead."
            ),
            "returncode": proc.returncode,
            "files": [str(p) for p in written],
            "maps": {},
        }
    if proc.returncode != 0:
        return {
            "ok": False,
            "error": f"Material Maker exit {proc.returncode}: {(proc.stderr or proc.stdout)[-400:]}",
            "returncode": proc.returncode,
            "files": [str(p) for p in written],
            "maps": {},
        }
    if not written:
        return {
            "ok": False,
            "error": f"Material Maker reported success but wrote nothing to {out_dir}",
            "files": [],
            "maps": {},
        }

    maps: Dict[str, str] = {}
    for png in written:
        kind = classify_map(png)
        if kind:
            maps[kind] = str(png)
    return {"ok": True, "files": [str(p) for p in written], "maps": maps, "target": target}


def export_many(ptex_files: List[Path], out_dir: Path, *, target: str = "Blender") -> Dict[str, object]:
    """Export several graphs, isolating crashes so one bad graph can't stop the batch."""
    results = []
    ok = 0
    for ptex in ptex_files:
        res = export(Path(ptex), out_dir, target=target)
        res["ptex"] = str(ptex)
        results.append(res)
        ok += 1 if res.get("ok") else 0
    return {"ok": ok > 0, "exported": ok, "total": len(results), "results": results}


def main() -> int:
    parser = argparse.ArgumentParser(description="Material Maker procedural material export")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--export", type=Path, default=None, help="a .ptex file")
    parser.add_argument("--export-dir", type=Path, default=None, help="folder of .ptex files")
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--target", default="Blender", choices=TARGETS)
    args = parser.parse_args()

    if args.status or (not args.export and not args.export_dir):
        print(json.dumps(status(), indent=2))
        return 0 if is_available() else 1

    if not args.out:
        print("[ERROR] --out is required", file=sys.stderr)
        return 2

    if args.export_dir:
        files = sorted(Path(args.export_dir).glob("*.ptex"))
        if not files:
            print(f"[ERROR] no .ptex files in {args.export_dir}", file=sys.stderr)
            return 1
        result = export_many(files, args.out, target=args.target)
    else:
        result = export(args.export, args.out, target=args.target)

    print(json.dumps(result, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
