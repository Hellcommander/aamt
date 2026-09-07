#!/usr/bin/env python3
"""
Fix-TranscendenceSysEventRegister.py

Workspace overlay: objRegisterForSystemEvents must not dereference a NULL
system (intro/virtual stations created with a nil position).

Official Kronosaur trees stay clean. Idempotent via .sys_event_register_autofix_v1.
"""
from __future__ import annotations

import argparse
from pathlib import Path

MARKER_NAME = ".sys_event_register_autofix_v1"
TAG = "TX_SYS_EVENT_REGISTER_AUTOFIX"

OLD = """\t\tcase FN_OBJ_REGISTER_SYSTEM_EVENTS:
\t\t\tif (pObj->IsDestroyed())
\t\t\t\treturn pCC->CreateNil();

\t\t\tpObj->GetSystem()->RegisterEventHandler(pObj, pArgs->GetElement(1)->GetIntegerValue() * LIGHT_SECOND);
\t\t\treturn pCC->CreateTrue();
"""

NEW = """\t\tcase FN_OBJ_REGISTER_SYSTEM_EVENTS:
\t\t\tif (pObj->IsDestroyed())
\t\t\t\treturn pCC->CreateNil();

\t\t\t//\t""" + TAG + """: intro/virtual objects may have no system yet.
\t\t\tif (pObj->GetSystem() == NULL)
\t\t\t\treturn pCC->CreateNil();

\t\t\tpObj->GetSystem()->RegisterEventHandler(pObj, pArgs->GetElement(1)->GetIntegerValue() * LIGHT_SECOND);
\t\t\treturn pCC->CreateTrue();
"""


def patch_text(text: str) -> tuple[str, list[str]]:
    notes: list[str] = []
    if TAG in text:
        notes.append("already patched")
        return text, notes
    if OLD not in text:
        notes.append("WARNING: objRegisterForSystemEvents block not found")
        return text, notes
    return text.replace(OLD, NEW, 1), ["null-check GetSystem before RegisterEventHandler"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("api_root", nargs="?", default="")
    parser.add_argument("--api-root", dest="api_root_opt", default="")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    root = Path(args.api_root_opt or args.api_root)
    if not root:
        raise SystemExit("api root required")
    marker = root / MARKER_NAME
    src = root / "Mammoth" / "TSE" / "CCExtensions.cpp"
    if not src.exists():
        raise SystemExit(f"missing {src}")
    if marker.exists() and not args.force:
        print(f"sys-event-register autofix already applied ({marker.name}). Use --force to re-run.")
        return
    raw = src.read_text(encoding="utf-8", errors="replace")
    new, notes = patch_text(raw)
    print(f"{src}: {', '.join(notes)}")
    if args.dry_run or new == raw:
        if TAG in new and not args.dry_run:
            marker.write_text("v1\n", encoding="utf-8")
            print(f"wrote {marker.name}")
        return
    src.write_text(new, encoding="utf-8")
    marker.write_text("v1\n", encoding="utf-8")
    print(f"wrote {marker.name}")


if __name__ == "__main__":
    main()
