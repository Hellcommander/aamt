#!/usr/bin/env python3
"""
Roll Mandibore design attempts (pose variants + seeds) via local SD :1338.
Writes DesignDrafts/MandiboreVariants/*_design_draft.png — does not overwrite the main tile
unless --promote <stem> is passed later by hand.

Usage:
  python generate_mandibore_variants.py "<mod>"
  python generate_mandibore_variants.py "<mod>" --count 6
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Prefer Tools/Qud on path for qud_sd_client
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

BASE_PROMPT = (
    "Caves of Qud 16x24 tile concept, thin ant broodling side view, black chitin, "
    "lime accents, antennae, living drill mandibles, arched stinger tail, "
    "crisp silhouette, dark bg. Caves of Qud tile concept art: 16x24 aspect, "
    "bold readable silhouette, flat graphic official 18-color Qud palette, "
    "at most 3 colors, no soft gradients, biomutation arthropod chitin"
)
NEGATIVE = (
    "blurry, slime blob, soft grey wash, crab pincers, thick body, "
    "cute cartoon, anime, watermark, text"
)

POSES = [
    ("idle", "animation frame idle, neutral stance, stinger arched, mandibles closed"),
    ("sniff", "animation frame sniff, antennae tipped forward, slight lean"),
    ("drill_windup", "animation frame drill wind-up, mandibles open, body braced low"),
    ("burrow_strike", "animation frame burrow strike, drill mandibles thrust forward"),
    ("stinger_raise", "animation frame stinger raise, arched tail cocked high"),
    ("stinger_jab", "animation frame stinger jab, stinger tip angled forward over body"),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mod", type=Path)
    ap.add_argument("--count", type=int, default=6, help="How many pose slots (max 6)")
    ap.add_argument("--seed-base", type=int, default=42000)
    args = ap.parse_args()

    mod: Path = args.mod
    out_dir = mod / "DesignDrafts" / "MandiboreVariants"
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        from qud_sd_client import generate_sd_draft, SD_AVAILABLE
    except ImportError:
        print("[ERROR] qud_sd_client not importable from Tools/Qud")
        return 1
    if not SD_AVAILABLE:
        print("[ERROR] SD client reports unavailable — is :1338 up?")
        return 1

    pack_path = mod / "DesignDrafts" / "prompt_pack.json"
    if pack_path.exists():
        pack = json.loads(pack_path.read_text(encoding="utf-8"))
        entry = pack.get("broodling_mandibore") or {}
        base = str(entry.get("prompt") or BASE_PROMPT)
        neg = str(entry.get("negative_prompt") or NEGATIVE)
    else:
        base, neg = BASE_PROMPT, NEGATIVE

    n = max(1, min(args.count, len(POSES)))
    summary = []
    for i, (stem, pose) in enumerate(POSES[:n]):
        seed = args.seed_base + i * 17
        prompt = f"{base}. {pose}"
        out = out_dir / f"Mandibore_{stem}_s{seed}_design_draft.png"
        print(f"[GEN] {stem} seed={seed} -> {out.name}")
        result = generate_sd_draft(
            prompt=prompt,
            output_path=out,
            negative_prompt=neg,
            width=512,
            height=768,
            steps=12,
            guidance_scale=7.0,
            seed=seed,
            lock_label=f"mandibore_variant:{stem}",
        )
        ok = bool(result.ok and out.exists() and out.stat().st_size > 0)
        print(f"  {'OK' if ok else 'FAIL'} {getattr(result, 'error', '') or ''}")
        summary.append({"pose": stem, "seed": seed, "path": str(out), "ok": ok})

    (out_dir / "variants_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(f"[DONE] {sum(1 for s in summary if s['ok'])}/{len(summary)} -> {out_dir}")
    return 0 if all(s["ok"] for s in summary) else 2


if __name__ == "__main__":
    raise SystemExit(main())
