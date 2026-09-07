#!/usr/bin/env python3
"""
Find Broodmother DesignDrafts that are too dark / empty / low-signal (CLIP leftovers)
and delete them so generate_broodmother_assets_ollama.py will regenerate + re-export.

Heuristic (draft PNG, not the 16x24 export):
  - mean luminance of opaque pixels < 18, OR
  - >85% near-black opaque pixels, OR
  - opaque coverage < 5%, OR
  - very few unique colors AND mean < 40

Usage:
  python finish_low_quality_broodmother_drafts.py "<mod>" --dry-run
  python finish_low_quality_broodmother_drafts.py "<mod>" --apply
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

from PIL import Image


# Draft stem -> exported map tile(s) under Textures/ (for post-quantize collapse).
_EXPORT_MAP = {
    "broodling_ground": ["Textures/Creatures/sw_broodling_ground.png"],
    "broodling_flying": ["Textures/Creatures/sw_broodling_flying.png"],
    "icon": ["Textures/Broodmother_icon.png"],
    "sack": [
        "Textures/Equipment/Broodling_Sack_tile.png",
        "Textures/Equipment/Broodling_Sack_icon.png",
    ],
}


def _draft_export_paths(mod: Path, draft_name: str) -> List[Path]:
    stem = draft_name.replace("_design_draft.png", "")
    out: List[Path] = []
    if stem in _EXPORT_MAP:
        out.extend(mod / rel for rel in _EXPORT_MAP[stem])
    # Unique creatures: BroodlingCrystal_T4_design_draft.png -> Creatures/BroodlingCrystal_T4.png
    creature = mod / "Textures" / "Creatures" / f"{stem}.png"
    if creature.exists() or stem.startswith("Broodling"):
        out.append(creature)
    return out


def _export_collapsed(path: Path) -> Tuple[bool, int, float]:
    """True if palette export has <2 distinct opaque colors (flat blob)."""
    if not path.exists():
        return False, 0, 0.0
    with Image.open(path) as im:
        rgba = im.convert("RGBA")
        opaque = [(r, g, b) for r, g, b, a in rgba.getdata() if a >= 16]
    if not opaque:
        return True, 0, 0.0
    uniq = len(set(opaque))
    mean = sum(r + g + b for r, g, b in opaque) / (3.0 * len(opaque))
    return uniq < 2, uniq, mean


def _score(path: Path, mod: Path | None = None) -> Dict[str, Any]:
    with Image.open(path) as im:
        rgba = im.convert("RGBA")
        px = list(rgba.getdata())
    n = max(1, len(px))
    opaque = [(r, g, b) for r, g, b, a in px if a >= 16]
    if not opaque:
        return {
            "path": str(path),
            "name": path.name,
            "coverage": 0.0,
            "mean_luma": 0.0,
            "unique": 0,
            "dark_frac": 1.0,
            "low": True,
            "reasons": ["no_opaque_pixels"],
        }
    cov = len(opaque) / n
    mean = sum(r + g + b for r, g, b in opaque) / (3.0 * len(opaque))
    uniq = len(set(opaque))
    dark = sum(1 for r, g, b in opaque if (r + g + b) < 40) / len(opaque)
    reasons: List[str] = []
    if cov < 0.05:
        reasons.append(f"coverage={cov:.3f}<0.05")
    if mean < 18.0:
        reasons.append(f"mean_luma={mean:.1f}<18")
    if dark > 0.85:
        reasons.append(f"dark_frac={dark:.3f}>0.85")
    if uniq <= 3 and mean < 40.0:
        reasons.append(f"uniq={uniq}<=3 and mean={mean:.1f}<40")
    # Map fidelity: quantized export collapsed to a single color (e.g. sw_broodling_ground).
    if mod is not None:
        for exp in _draft_export_paths(mod, path.name):
            collapsed, euniq, emean = _export_collapsed(exp)
            if collapsed:
                reasons.append(f"export_collapsed:{exp.name}:uniq={euniq}")
    return {
        "path": str(path),
        "name": path.name,
        "coverage": round(cov, 4),
        "mean_luma": round(mean, 2),
        "unique": uniq,
        "dark_frac": round(dark, 4),
        "low": bool(reasons),
        "reasons": reasons,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Delete low-quality Broodmother SD drafts for regen")
    ap.add_argument("mod_path", type=str, help="Broodmother Mutation mod folder")
    ap.add_argument("--draft-dir", default="DesignDrafts", help="Draft folder name inside mod")
    ap.add_argument("--dry-run", action="store_true", help="List only (default if neither flag)")
    ap.add_argument("--apply", action="store_true", help="Delete low-quality draft PNGs")
    args = ap.parse_args()

    if not args.apply:
        args.dry_run = True

    mod = Path(args.mod_path)
    draft_dir = mod / args.draft_dir
    if not draft_dir.is_dir():
        print(f"[ERROR] Draft dir missing: {draft_dir}")
        return 1

    drafts = sorted(
        p
        for p in draft_dir.glob("*_design_draft.png")
        if not p.name.startswith("_smoke")
    )
    if not drafts:
        print(f"[WARN] No design drafts in {draft_dir}")
        return 0

    rows = [_score(p, mod) for p in drafts]
    low = [r for r in rows if r["low"]]
    ok = [r for r in rows if not r["low"]]

    print(f"Scanned {len(rows)} drafts in {draft_dir}")
    print(f"  OK:  {len(ok)}")
    print(f"  LOW: {len(low)}")
    print()
    for r in sorted(low, key=lambda x: (x["mean_luma"], x["name"])):
        why = ", ".join(r["reasons"])
        print(
            f"  LOW  mean={r['mean_luma']:6.1f} dark={r['dark_frac']:.3f} "
            f"uniq={r['unique']:5d}  {r['name']}  ({why})"
        )

    # Spot-check flyer even if draft mean looks OK — export must stay ≥2 colors.
    flyer_draft = draft_dir / "broodling_flying_design_draft.png"
    if flyer_draft.exists():
        fr = _score(flyer_draft, mod)
        if not fr["low"]:
            print(
                f"\n  flyer check OK: mean={fr['mean_luma']:.1f} "
                f"(export not collapsed)"
            )

    report = {
        "draft_dir": str(draft_dir),
        "total": len(rows),
        "ok": len(ok),
        "low": len(low),
        "low_names": [r["name"] for r in low],
        "rows": rows,
    }
    report_path = draft_dir / "low_quality_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\n[OK] Wrote {report_path}")

    if args.dry_run and not args.apply:
        print("\nDry-run only. Re-run with --apply to delete LOW drafts for regeneration.")
        return 0

    deleted = 0
    for r in low:
        p = Path(r["path"])
        try:
            p.unlink(missing_ok=True)
            deleted += 1
            print(f"  deleted {p.name}")
        except OSError as exc:
            print(f"  [WARN] could not delete {p.name}: {exc}")

    print(f"\n[OK] Deleted {deleted}/{len(low)} low-quality drafts.")
    print("Next: run generate_broodmother_assets_ollama.py --load-existing (keeps good drafts).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
