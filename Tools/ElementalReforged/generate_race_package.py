#!/usr/bin/env python3
"""Generate monster-race clothes/armor/weapon package (thin wrapper)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from monster_race_tool import generate_race_package
from er_tool_lib import load_config


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--race", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--icon-size", type=int, default=128)
    ap.add_argument("--texture-size", type=int, default=512)
    ap.add_argument("--kinds", default="clothes,armor,weapon")
    args = ap.parse_args()

    cfg = load_config(Path(args.config))
    kinds = [k.strip() for k in args.kinds.split(",") if k.strip()]
    result = generate_race_package(
        cfg,
        args.race,
        Path(args.out_dir),
        icon_size=args.icon_size,
        texture_size=args.texture_size,
        kinds=kinds,
    )
    # back-compat fields for older PS1 callers
    if result["items"]:
        last = result["items"][-1]
        result["icon"] = last["icon"]
        result["texture"] = last["texture"]
        result["internal"] = last["internal"]
    print(json.dumps(result))


if __name__ == "__main__":
    main()
