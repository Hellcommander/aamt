#!/usr/bin/env python3
"""Print one race JSON object from config (stdin or --config)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from er_tool_lib import DEFAULT_CONFIG, load_config


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("race")
    ap.add_argument("--config", default="")
    args = ap.parse_args()

    if args.config:
        cfg = load_config(Path(args.config))
    elif not sys.stdin.isatty():
        cfg = json.loads(sys.stdin.read())
    else:
        cfg = load_config(DEFAULT_CONFIG)

    if args.race not in cfg["races"]:
        raise SystemExit(f"Unknown race: {args.race}")
    print(json.dumps(cfg["races"][args.race], indent=2))


if __name__ == "__main__":
    main()
