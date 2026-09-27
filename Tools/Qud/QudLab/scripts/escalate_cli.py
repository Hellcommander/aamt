#!/usr/bin/env python3
"""CLI entry for shelve / escalate (called from Escalate-VllmContext.ps1)."""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from shelve_context import (  # noqa: E402
    HIGH_CTX_MODEL,
    create_shelf,
    escalate,
    format_shelf_prompt,
    list_shelves,
    load_shelf,
    set_pending_unshelve,
    consume_pending_shelf_prompt,
)


def main() -> int:
    p = argparse.ArgumentParser(description="Shelve / escalate vLLM context")
    p.add_argument("action", choices=("shelve", "escalate", "unshelve", "list"))
    p.add_argument("--task", default="")
    p.add_argument("--to-model", default=HIGH_CTX_MODEL)
    p.add_argument("--no-frontend", action="store_true")
    p.add_argument("--no-swap", action="store_true")
    args = p.parse_args()

    if args.action == "list":
        print(json.dumps({"shelves": list_shelves()}, indent=2))
        return 0
    if args.action == "unshelve":
        text = consume_pending_shelf_prompt() or format_shelf_prompt(load_shelf("latest") or {})
        print(text or "(no shelf)")
        return 0 if text else 1
    if args.action == "shelve" or args.no_swap:
        shelf = create_shelf(task=args.task, reason="manual_shelve", to_model=args.to_model)
        set_pending_unshelve(str(shelf["id"]), args.to_model)
        print(json.dumps({"shelf_id": shelf["id"], "swapped": False, "pending": True, "to_model": args.to_model}))
        return 0
    result = escalate(
        task=args.task,
        to_model=args.to_model,
        do_swap=True,
        restart_frontend=not args.no_frontend,
    )
    print(json.dumps(result))
    return 0 if result.get("shelf_id") else 1


if __name__ == "__main__":
    raise SystemExit(main())
