#!/usr/bin/env python3
"""Export Magi-Tech animation sheets from Pixelorama .pxo via Shared pixels stage.

Headless path (GPU-locked Godot CLI):
  python produce_pixelorama_sheets.py --ids grenade_fire
  python produce_pixelorama_sheets.py --open-gui grenade_fire   # visible editor
  python produce_pixelorama_sheets.py --see                     # screenshot GUI

Looks for projects under (first hit wins):
  <mod>/assets/magitech/pixelorama/<id>.pxo
  <mod>/DesignDrafts/<id>.pxo
  <mod>/assets/magitech/pixelorama/<id>/<id>.pxo

Does not invent walk/attack limbs. Pixelorama exports authored frames only.
True gait/attack silhouettes need posed frames in the .pxo (or a 3D turntable
bake that was imported into Pixelorama).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional, Sequence

_TOOLS = Path(__file__).resolve().parent
_SHARED = _TOOLS.parent / "Shared"
for p in (_SHARED, _TOOLS):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from PIL import Image  # noqa: E402

try:
    from ai_resources import make_pixels
except Exception:  # pragma: no cover
    from pixelorama_client import export_project as make_pixels  # type: ignore

from pixelorama_client import inspect, open_gui, screenshot_gui, status  # noqa: E402
from produce_unity_still_animations import install, write_animation  # noqa: E402

DEFAULT_MOD = Path(r"F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery")
PXO_REL = (
    Path("assets") / "magitech" / "pixelorama",
    Path("DesignDrafts"),
)
GEN = Path("assets") / "magitech" / "generated"

# Pose names used when Pixelorama exports N discrete frames we can slice.
DEFAULT_POSE_NAMES = ("idle", "charging", "fire", "cooldown")


def find_pxo(mod: Path, asset_id: str) -> Optional[Path]:
    candidates = [
        mod / PXO_REL[0] / f"{asset_id}.pxo",
        mod / PXO_REL[1] / f"{asset_id}.pxo",
        mod / PXO_REL[0] / asset_id / f"{asset_id}.pxo",
    ]
    for c in candidates:
        if c.is_file():
            return c
    return None


def list_pxo_assets(mod: Path) -> List[str]:
    found: List[str] = []
    for root in (mod / PXO_REL[0], mod / PXO_REL[1]):
        if not root.is_dir():
            continue
        for p in sorted(root.rglob("*.pxo")):
            found.append(p.stem)
    # Unique, preserve order
    seen = set()
    out: List[str] = []
    for name in found:
        if name not in seen:
            seen.add(name)
            out.append(name)
    return out


def _write_frames_json(dest: Path, tile: int, names: Sequence[str]) -> None:
    first = names[0]
    aliases = {
        "default": first,
        "idle": first,
        "charging": names[1] if len(names) > 1 else first,
        "fire": names[2] if len(names) > 2 else first,
        "cooldown": names[3] if len(names) > 3 else first,
    }
    payload = {
        "frameGrid": {
            "size": [tile, tile],
            "dimensions": [len(names), 1],
            "names": [list(names)],
        },
        "aliases": aliases,
    }
    dest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _normalize_sheet(src: Path, dest: Path, tile: int, pose_names: Sequence[str]) -> List[str]:
    """Resize/slice Pixelorama export into a horizontal Starbound strip."""
    im = Image.open(src).convert("RGBA")
    w, h = im.size
    # Already a horizontal strip of square cells
    if h == tile and w % tile == 0:
        n = w // tile
        names = list(pose_names[:n]) if n <= len(pose_names) else [f"frame{i+1}" for i in range(n)]
        if n < len(pose_names) and n > 0:
            names = list(pose_names[:n])
        dest.parent.mkdir(parents=True, exist_ok=True)
        if src.resolve() != dest.resolve():
            im.save(dest)
        _write_frames_json(dest.with_suffix(".frames"), tile, names)
        return names
    # Single square / near-square → one-frame idle sheet
    if abs(w - h) <= 2:
        cell = im.resize((tile, tile), Image.Resampling.NEAREST)
        sheet = Image.new("RGBA", (tile, tile), (0, 0, 0, 0))
        sheet.paste(cell, (0, 0))
        dest.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(dest)
        names = ["idle"]
        _write_frames_json(dest.with_suffix(".frames"), tile, names)
        return names
    # Horizontal strip at other height → scale height to tile, keep frame count
    if w > h and w % h == 0:
        n = w // h
        names = list(pose_names[:n]) if n <= len(pose_names) else [f"frame{i+1}" for i in range(n)]
        sheet = Image.new("RGBA", (tile * n, tile), (0, 0, 0, 0))
        for i in range(n):
            cell = im.crop((i * h, 0, (i + 1) * h, h)).resize((tile, tile), Image.Resampling.NEAREST)
            sheet.paste(cell, (i * tile, 0))
        dest.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(dest)
        _write_frames_json(dest.with_suffix(".frames"), tile, names)
        return names
    # Fallback: fit whole image into one tile
    cell = im.resize((tile, tile), Image.Resampling.NEAREST)
    sheet = Image.new("RGBA", (tile, tile), (0, 0, 0, 0))
    sheet.paste(cell, (0, 0))
    dest.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(dest)
    names = ["idle"]
    _write_frames_json(dest.with_suffix(".frames"), tile, names)
    return names


def produce_one(mod: Path, asset_id: str, tile: int, skip_existing: bool) -> bool:
    pxo = find_pxo(mod, asset_id)
    if not pxo:
        print(f"  [SKIP] no .pxo for {asset_id} (put one in assets/magitech/pixelorama/)")
        return False
    out = mod / GEN / asset_id
    sheet = out / f"{asset_id}_sheet.png"
    if skip_existing and sheet.exists():
        print(f"  [SKIP] existing {asset_id}")
        install(mod, asset_id, out)
        return True
    out.mkdir(parents=True, exist_ok=True)
    raw = out / "Source" / "pixelorama_export.png"
    raw.parent.mkdir(parents=True, exist_ok=True)
    print(f"    Pixelorama export {pxo.name}")
    info = inspect(pxo)
    if info.get("ok"):
        print(f"    size={info.get('size')} frames={info.get('framecount')}")
    result = make_pixels(pxo, raw, spritesheet=True)
    if not result.get("ok"):
        # Some projects export better as a plain frame export
        result = make_pixels(pxo, raw, spritesheet=False)
    if not result.get("ok"):
        raise RuntimeError(result.get("error") or f"Pixelorama export failed for {pxo}")
    # Prefer the requested path; fall back to whatever Pixelorama wrote.
    export_path = raw if raw.is_file() else None
    if not export_path:
        written = [Path(p) for p in result.get("written") or []]
        pngs = [p for p in written if p.suffix.lower() == ".png"]
        if pngs:
            export_path = pngs[0]
    if not export_path or not export_path.is_file():
        raise RuntimeError(f"Pixelorama produced no PNG for {asset_id}")
    # Keep a single-frame icon copy (first cell / whole image).
    icon = Image.open(export_path).convert("RGBA")
    if icon.height > 0 and icon.width >= icon.height and icon.width % icon.height == 0:
        cell = icon.crop((0, 0, icon.height, icon.height)).resize((tile, tile), Image.Resampling.NEAREST)
    else:
        cell = icon.resize((tile, tile), Image.Resampling.NEAREST)
    cell.save(out / f"{asset_id}.png")
    names = _normalize_sheet(export_path, sheet, tile, DEFAULT_POSE_NAMES)
    write_animation(out / f"{asset_id}.animation", f"{asset_id}_sheet.png", ["weapon"])
    install(mod, asset_id, out)
    print(f"  [OK] {asset_id} frames={names}")
    return True


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Pixelorama → Magi-Tech Starbound sheets (Shared pixels stage)")
    ap.add_argument("--mod-path", type=Path, default=DEFAULT_MOD)
    ap.add_argument("--tile", type=int, default=64)
    ap.add_argument("--ids", default="", help="Comma asset ids (stems of .pxo files)")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--skip-existing", action="store_true")
    ap.add_argument("--list", action="store_true", help="List discoverable .pxo assets and exit")
    ap.add_argument("--open-gui", metavar="ID", nargs="?", const="", help="Open Pixelorama GUI (optional asset id)")
    ap.add_argument("--see", type=Path, nargs="?", const=Path("."), help="Screenshot Pixelorama GUI")
    ap.add_argument("--status", action="store_true")
    args = ap.parse_args(argv)

    if args.status:
        st = status()
        print(json.dumps(st, indent=2))
        return 0 if st.get("available") else 1

    if args.see is not None:
        out = None if args.see == Path(".") else args.see
        print(json.dumps(screenshot_gui(out), indent=2))
        return 0

    if args.open_gui is not None:
        pxo = find_pxo(args.mod_path, args.open_gui) if args.open_gui else None
        print(json.dumps(open_gui(pxo), indent=2))
        return 0

    mod = Path(args.mod_path)
    if args.list:
        assets = list_pxo_assets(mod)
        print(json.dumps({"mod": str(mod), "count": len(assets), "assets": assets}, indent=2))
        return 0

    st = status()
    if not st.get("available"):
        raise SystemExit(
            "Pixelorama not found. Expected D:\\tools\\Orama Interactive\\Pixelorama\\Pixelorama.exe "
            "(see Shared/PIXELORAMA.md)"
        )

    if args.ids:
        ids = [x.strip() for x in args.ids.split(",") if x.strip()]
    else:
        ids = list_pxo_assets(mod)
    if args.limit:
        ids = ids[: args.limit]
    if not ids:
        print("No .pxo projects found under assets/magitech/pixelorama or DesignDrafts.")
        print("Author frames in Pixelorama (open via --open-gui), save .pxo, then re-run.")
        return 1

    ok = fail = 0
    for asset_id in ids:
        print(f"-- {asset_id}")
        try:
            if produce_one(mod, asset_id, args.tile, args.skip_existing):
                ok += 1
            else:
                fail += 1
        except Exception as exc:
            fail += 1
            print(f"  [FAIL] {exc}")
    print(f"[DONE] ok={ok} fail={fail} backend=pixelorama")
    return 0 if ok or not fail else 1


if __name__ == "__main__":
    sys.exit(main())
