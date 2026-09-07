#!/usr/bin/env python3
"""Optional Blender bake for DF creature art; falls back to tile generator."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional

_HERE = Path(__file__).resolve().parent
_SHARED = _HERE.parent / "Shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))


def find_blender() -> Optional[str]:
    try:
        from tool_paths import find_blender as _fb

        return _fb()
    except Exception:
        return None


def bake_creature_art(
    spec: Dict[str, Any],
    mod_root: Path,
    *,
    no_sd: bool = True,
) -> Dict[str, Any]:
    """
    Attempt a simple Blender bake. If Blender is unavailable, no-op and call
    the Pillow/SD tile generator as a placeholder so callers still get PNGs.
    """
    from df_tile_generator import generate_art_for_spec

    blender = find_blender()
    if not blender:
        print("[df_blender_bake] Blender not found via tool_paths; skipping bake.")
        arts = generate_art_for_spec(spec, mod_root, no_sd=no_sd)
        return {"blender": None, "fallback": "tile_generator", "arts": arts}

    # Full mesh bake pipeline is out of scope; document and fall through.
    print(f"[df_blender_bake] Found Blender at {blender}")
    print("[df_blender_bake] No DF-specific bake script wired yet; using tile generator PNGs.")
    arts = generate_art_for_spec(spec, mod_root, no_sd=no_sd)
    return {"blender": blender, "fallback": "tile_generator", "arts": arts}


def main() -> int:
    import argparse
    from df_creature_schema import load_spec

    ap = argparse.ArgumentParser(description="Optional Blender bake for DF creatures")
    ap.add_argument("--spec", type=Path, required=True)
    ap.add_argument("--mod-root", type=Path, required=True)
    ap.add_argument("--no-sd", action="store_true", default=True)
    args = ap.parse_args()
    spec = load_spec(args.spec)
    result = bake_creature_art(spec, args.mod_root, no_sd=args.no_sd)
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
