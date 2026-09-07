#!/usr/bin/env python3
"""Exit 0 if Broodmother prompt_pack.json has all 34 required keys complete."""
from __future__ import annotations

import json
import sys
from pathlib import Path

REQUIRED = [
    "icon",
    "sack",
    "broodling_ground",
    "broodling_flying",
    "broodling_crystal",
    "broodling_phantom",
    "broodling_bombardier",
    "broodling_symbiote",
    "broodling_tunneler",
    "broodling_mimic",
    "broodling_shard",
    "broodling_swarmling",
    "broodling_voidling",
    "broodling_fluxling",
    "broodling_leechling",
    "broodling_mindling",
    "broodling_glowling",
    "broodling_rustling",
    "broodling_necroling",
    "broodling_thornling",
    "broodling_mandibore",
    "preview",
    "texture_carapace",
    "texture_membrane",
    "texture_biometal",
    "texture_chitin",
    "ui_biomod_chip",
    "ui_birth_badge",
    "ui_evolution_node",
    "ui_swarm_frame",
    "ui_panel",
    "ui_button",
    "ui_menu_row",
    "ui_status_strip",
    "ui_tier_pip",
]


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: check_broodmother_prompt_pack.py <prompt_pack.json>", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    ok = 0
    missing = []
    for key in REQUIRED:
        entry = data.get(key)
        if (
            isinstance(entry, dict)
            and str(entry.get("prompt", "")).strip()
            and str(entry.get("negative_prompt", "")).strip()
            and " / " not in key
        ):
            ok += 1
        else:
            missing.append(key)
    print(f"{ok}/{len(REQUIRED)}")
    if missing:
        print("missing: " + ", ".join(missing), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
