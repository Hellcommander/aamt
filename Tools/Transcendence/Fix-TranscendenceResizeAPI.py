#!/usr/bin/env python3
"""
Fix-TranscendenceResizeAPI.py

Autofix a TranscendenceDev-integration-APIxx tree so CrossMod ResizeAPI can
actually change ship visuals / image-scale bounds at runtime.

Adds:
  1. CSpaceObject visual scale (m_rVisualScale) + Get/SetVisualScale
  2. GetImageScale() respects visual scale (docking / overlays / bounds)
  3. CShip::Paint uses PaintScaledImage when scale != 1
  4. TLisp (objSetVisualScale obj scale) / (objGetVisualScale obj)

Idempotent: writes .resize_api_autofix_v1 under the API root.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

MARKER_NAME = ".resize_api_autofix_v1"
FIX_VERSION = 1
TAG = "TX_RESIZE_API_AUTOFIX"


def backup_file(path: Path, backup_root: Path, api_root: Path) -> None:
    rel = path.relative_to(api_root)
    dest = backup_root / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dest)


def write_text(path: Path, text: str) -> None:
    path.write_bytes(text.encode("utf-8"))


def once(text: str, old: str, new: str, notes: list[str], label: str) -> str:
    if old not in text:
        if TAG in text and label.split(":")[0] in "".join(notes):
            notes.append(f"{label}: already present")
            return text
        notes.append(f"{label}: WARNING pattern not found")
        return text
    notes.append(label)
    return text.replace(old, new, 1)


def patch_tse_h(text: str) -> tuple[str, list[str]]:
    notes: list[str] = []
    if "SetVisualScale" in text and TAG in text:
        notes.append("TSE.h: already patched")
        return text, notes

    text = once(
        text,
        "\t\tint GetImageScale (void) const;\n",
        "\t\tint GetImageScale (void) const;\n"
        f"\t\tMetric GetVisualScale (void) const {{ return m_rVisualScale; }}\t// {TAG}\n"
        f"\t\tvoid SetVisualScale (Metric rScale);\t// {TAG}\n",
        notes,
        "TSE.h: Get/SetVisualScale decls",
    )

    text = once(
        text,
        "\t\tmutable int m_iImageScale = -1;\t\t\t\t\t//\tCached value computed in GetImageScale\n",
        "\t\tmutable int m_iImageScale = -1;\t\t\t\t\t//\tCached value computed in GetImageScale\n"
        f"\t\tMetric m_rVisualScale = 1.0;\t\t\t\t\t\t//\t{TAG}: runtime paint/bounds scale\n",
        notes,
        "TSE.h: m_rVisualScale member",
    )
    return text, notes


def patch_cspaceobject_cpp(text: str) -> tuple[str, list[str]]:
    notes: list[str] = []
    if "SetVisualScale" in text and TAG in text:
        notes.append("CSpaceObject.cpp: already patched")
        return text, notes

    # Replace GetImageScale body to multiply by visual scale
    old_gis = (
        "int CSpaceObject::GetImageScale (void) const\n"
        "\n"
        "//\tGetImageScale\n"
        "//\n"
        "//\tReturns the scale.\n"
        "\n"
        "\t{\n"
        "\tif (m_iImageScale == -1)\n"
        "\t\t{\n"
        "\t\tconst CObjectImageArray &Image = GetImage();\n"
        "\t\tif (!Image.IsEmpty())\n"
        "\t\t\tm_iImageScale = Image.GetImageViewportSize();\n"
        "\t\telse\n"
        "\t\t\t{\n"
        "\t\t\t//\tIf there is no image, we return a default value, but we don't\n"
        "\t\t\t//\tcache the value, in case the image gets set later.\n"
        "\n"
        "\t\t\treturn 512;\n"
        "\t\t\t}\n"
        "\t\t}\n"
        "\n"
        "\treturn m_iImageScale;\n"
        "\t}\n"
    )
    new_gis = (
        "int CSpaceObject::GetImageScale (void) const\n"
        "\n"
        "//\tGetImageScale\n"
        "//\n"
        "//\tReturns the scale.\n"
        "\n"
        "\t{\n"
        f"\t//\t{TAG}: include runtime visual scale in spatial image size\n"
        "\tif (m_iImageScale == -1)\n"
        "\t\t{\n"
        "\t\tconst CObjectImageArray &Image = GetImage();\n"
        "\t\tif (!Image.IsEmpty())\n"
        "\t\t\tm_iImageScale = Image.GetImageViewportSize();\n"
        "\t\telse\n"
        "\t\t\t{\n"
        "\t\t\t//\tIf there is no image, we return a default value, but we don't\n"
        "\t\t\t//\tcache the value, in case the image gets set later.\n"
        "\n"
        "\t\t\treturn Max(1, (int)mathRound(512.0 * m_rVisualScale));\n"
        "\t\t\t}\n"
        "\t\t}\n"
        "\n"
        "\treturn Max(1, (int)mathRound((Metric)m_iImageScale * m_rVisualScale));\n"
        "\t}\n"
        "\n"
        f"void CSpaceObject::SetVisualScale (Metric rScale)\t// {TAG}\n"
        "\t{\n"
        "\tif (rScale < 0.1)\n"
        "\t\trScale = 0.1;\n"
        "\telse if (rScale > 5.0)\n"
        "\t\trScale = 5.0;\n"
        "\tm_rVisualScale = rScale;\n"
        "\tm_iImageScale = -1;\t// invalidate cache\n"
        "\t}\n"
    )
    text = once(text, old_gis, new_gis, notes, "CSpaceObject.cpp: GetImageScale+SetVisualScale")
    return text, notes


def patch_cship_paint(text: str) -> tuple[str, list[str]]:
    notes: list[str] = []
    if TAG in text and "PaintScaledImage" in text and "m_rVisualScale" in text:
        notes.append("CShip.cpp: already patched")
        return text, notes

    old = (
        "\tif (byShimmer)\n"
        "\t\tImage.PaintImageShimmering(Dest, x, y, Ctx.iTick, m_Rotation.GetFrameIndex(), byShimmer);\n"
        "\telse if (IsRadioactive())\n"
        "\t\tImage.PaintImageWithGlow(Dest, x, y, Ctx.iTick, m_Rotation.GetFrameIndex(), CG32bitPixel(0, 255, 0));\n"
        "\telse\n"
        "\t\tImage.PaintImage(Dest, x, y, Ctx.iTick, m_Rotation.GetFrameIndex(), false, &Ctx);\n"
    )
    new = (
        f"\t//\t{TAG}: runtime visual scale via PaintScaledImage\n"
        "\tMetric rVisScale = GetVisualScale();\n"
        "\tif (rVisScale != 1.0 && byShimmer == 0 && !IsRadioactive())\n"
        "\t\t{\n"
        "\t\tint cx = Max(1, (int)mathRound((Metric)Image.GetImageWidth() * rVisScale));\n"
        "\t\tint cy = Max(1, (int)mathRound((Metric)Image.GetImageHeight() * rVisScale));\n"
        "\t\tImage.PaintScaledImage(Dest, x, y, Ctx.iTick, m_Rotation.GetFrameIndex(), cx, cy, CObjectImageArray::FLAG_CACHED);\n"
        "\t\t}\n"
        "\telse if (byShimmer)\n"
        "\t\tImage.PaintImageShimmering(Dest, x, y, Ctx.iTick, m_Rotation.GetFrameIndex(), byShimmer);\n"
        "\telse if (IsRadioactive())\n"
        "\t\tImage.PaintImageWithGlow(Dest, x, y, Ctx.iTick, m_Rotation.GetFrameIndex(), CG32bitPixel(0, 255, 0));\n"
        "\telse\n"
        "\t\tImage.PaintImage(Dest, x, y, Ctx.iTick, m_Rotation.GetFrameIndex(), false, &Ctx);\n"
    )
    text = once(text, old, new, notes, "CShip.cpp: scaled paint")
    return text, notes


def patch_ccextensions(text: str) -> tuple[str, list[str]]:
    notes: list[str] = []
    if "FN_OBJ_SET_VISUAL_SCALE" in text and "objSetVisualScale" in text:
        notes.append("CCExtensions.cpp: already patched")
        return text, notes

    text = once(
        text,
        "#define FN_OBJ_IS_SHIP_SECTION\t\t\t156\t// TX_SEGMENTED_SHIPS_AUTOFIX\n",
        "#define FN_OBJ_IS_SHIP_SECTION\t\t\t156\t// TX_SEGMENTED_SHIPS_AUTOFIX\n"
        f"#define FN_OBJ_SET_VISUAL_SCALE\t\t\t157\t// {TAG}\n"
        f"#define FN_OBJ_GET_VISUAL_SCALE\t\t\t158\t// {TAG}\n",
        notes,
        "CCExtensions.cpp: FN defines",
    )

    # Fallback if segmented ships not applied
    if "FN_OBJ_SET_VISUAL_SCALE" not in text:
        text = once(
            text,
            "#define FN_OBJ_DESTINY_ROLL\t\t\t\t154\n",
            "#define FN_OBJ_DESTINY_ROLL\t\t\t\t154\n"
            f"#define FN_OBJ_SET_VISUAL_SCALE\t\t\t157\t// {TAG}\n"
            f"#define FN_OBJ_GET_VISUAL_SCALE\t\t\t158\t// {TAG}\n",
            notes,
            "CCExtensions.cpp: FN defines (no segmented)",
        )

    reg = (
        f"\t\t//\t{TAG}\n"
        '\t\t{	"objSetVisualScale",\t\t\t\tfnObjSet,\t\tFN_OBJ_SET_VISUAL_SCALE,\n'
        '\t\t\t"(objSetVisualScale obj scale) -> scale\\n\\n"\n'
        "\n"
        '\t\t\t"Sets runtime visual/bounds scale for Resize API (1.0 = default).",\n'
        "\n"
        '\t\t\t"in",\t\tPPFLAG_SIDEEFFECTS,\t},\n'
        "\n"
        f"\t\t//\t{TAG}\n"
        '\t\t{	"objGetVisualScale",\t\t\t\tfnObjGet,\t\tFN_OBJ_GET_VISUAL_SCALE,\n'
        '\t\t\t"(objGetVisualScale obj) -> scale",\n'
        '\t\t\t"i",\t\t0,\t},\n'
        "\n"
    )
    if '"objSetVisualScale"' not in text:
        text = once(
            text,
            '\t\t{	"objCalcBestTarget",',
            reg + '\t\t{	"objCalcBestTarget",',
            notes,
            "CCExtensions.cpp: register primitives",
        )

    # GET handler near IS_SHIP_SECTION
    get_case = (
        f"\t\tcase FN_OBJ_GET_VISUAL_SCALE:\t// {TAG}\n"
        "\t\t\treturn pCC->CreateDouble(pObj->GetVisualScale());\n"
        "\n"
    )
    if "FN_OBJ_GET_VISUAL_SCALE:" not in text:
        if "case FN_OBJ_IS_SHIP_SECTION:" in text:
            text = once(
                text,
                "\t\tcase FN_OBJ_IS_SHIP_SECTION:\t// TX_SEGMENTED_SHIPS_AUTOFIX\n",
                get_case + "\t\tcase FN_OBJ_IS_SHIP_SECTION:\t// TX_SEGMENTED_SHIPS_AUTOFIX\n",
                notes,
                "CCExtensions.cpp: GET case",
            )
        else:
            # insert before a common get case
            text = once(
                text,
                "\t\tcase FN_OBJ_DESTINY:\n",
                get_case + "\t\tcase FN_OBJ_DESTINY:\n",
                notes,
                "CCExtensions.cpp: GET case fallback",
            )

    set_case = (
        f"\t\tcase FN_OBJ_SET_VISUAL_SCALE:\t// {TAG}\n"
        "\t\t\t{\n"
        "\t\t\tMetric rScale = pArgs->GetElement(1)->GetDoubleValue();\n"
        "\t\t\tpObj->SetVisualScale(rScale);\n"
        "\t\t\treturn pCC->CreateDouble(pObj->GetVisualScale());\n"
        "\t\t\t}\n"
        "\n"
    )
    if "FN_OBJ_SET_VISUAL_SCALE:" not in text:
        if "case FN_OBJ_ATTACH_SHIP_SECTION:" in text:
            text = once(
                text,
                "\t\tcase FN_OBJ_ATTACH_SHIP_SECTION:\t// TX_SEGMENTED_SHIPS_AUTOFIX\n",
                set_case + "\t\tcase FN_OBJ_ATTACH_SHIP_SECTION:\t// TX_SEGMENTED_SHIPS_AUTOFIX\n",
                notes,
                "CCExtensions.cpp: SET case",
            )
        else:
            text = once(
                text,
                "\t\tcase FN_OBJ_SETDATA:\n",
                set_case + "\t\tcase FN_OBJ_SETDATA:\n",
                notes,
                "CCExtensions.cpp: SET case fallback",
            )

    return text, notes


def find_paths(api_root: Path) -> dict[str, Path]:
    mammoth = api_root / "Mammoth"
    if not mammoth.is_dir():
        # some trees nest Transcendence/ differently
        hits = list(api_root.rglob("Include/TSE.h"))
        if hits:
            mammoth = hits[0].parent.parent
    return {
        "tse_h": mammoth / "Include" / "TSE.h",
        "cspace": mammoth / "TSE" / "CSpaceObject.cpp",
        "cship": mammoth / "TSE" / "CShip.cpp",
        "ccext": mammoth / "TSE" / "CCExtensions.cpp",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Autofix Transcendence API tree for Resize API visual scale")
    ap.add_argument("--api-root", required=True)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    api_root = Path(args.api_root).resolve()
    marker = api_root / MARKER_NAME
    if marker.is_file() and not args.force:
        print(f"resize autofix already applied ({marker.name}). Use --force to re-run.")
        return 0

    paths = find_paths(api_root)
    for key, p in paths.items():
        if not p.is_file():
            print(f"[ERROR] missing {key}: {p}")
            return 1

    backup_root = api_root / f".resize_api_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    all_notes: list[str] = []

    patches = [
        ("tse_h", patch_tse_h),
        ("cspace", patch_cspaceobject_cpp),
        ("cship", patch_cship_paint),
        ("ccext", patch_ccextensions),
    ]

    for key, fn in patches:
        path = paths[key]
        text = path.read_text(encoding="utf-8", errors="replace")
        new_text, notes = fn(text)
        all_notes.extend(notes)
        if new_text != text:
            print(f"[PATCH] {path.relative_to(api_root)}")
            for n in notes:
                print(f"  - {n}")
            if not args.dry_run:
                backup_file(path, backup_root, api_root)
                write_text(path, new_text)
        else:
            print(f"[SKIP] {path.name}: {notes}")

    if not args.dry_run:
        marker.write_text(
            f"version={FIX_VERSION}\ntag={TAG}\napplied={datetime.now().isoformat()}\n",
            encoding="utf-8",
        )
        print(f"[OK] marker {marker}")
        if backup_root.is_dir():
            print(f"[OK] backup {backup_root}")

    warns = [n for n in all_notes if "WARNING" in n]
    return 1 if warns else 0


if __name__ == "__main__":
    raise SystemExit(main())
