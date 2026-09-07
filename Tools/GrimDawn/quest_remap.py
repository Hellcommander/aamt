#!/usr/bin/env python3
"""Namespace mod quests so they do not override vanilla quest paths."""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path
from typing import Dict, List, Tuple

QUEST_TAG_RE = re.compile(r"(records[/\\]quests[/\\])([^\"'\s,]+)", re.IGNORECASE)
SOURCE_QUEST_RE = re.compile(r"(source[/\\]quests[/\\])([^\"'\s,]+)", re.IGNORECASE)


def _loose_quest_re(prefix: str) -> re.Pattern:
    """Match quests/... paths that are not already under the namespace prefix."""
    esc = re.escape(prefix)
    return re.compile(
        rf"(?<![\w/\\])(quests[/\\])(?!{esc}[/\\])([^\"'\s,]+)",
        re.IGNORECASE,
    )


def namespace_rel(rel: str, prefix: str = "nydiamar") -> str:
    parts = [p for p in rel.replace("\\", "/").split("/") if p]
    if not parts:
        return rel.replace("\\", "/")

    # records/quests/... -> records/quests/<prefix>/...
    if len(parts) >= 2 and parts[0].lower() == "records" and parts[1].lower() == "quests":
        if len(parts) > 2 and parts[2].lower() == prefix.lower():
            return "/".join(parts)
        return "/".join(parts[:2] + [prefix] + parts[2:])

    # source/quests/... -> source/quests/<prefix>/...
    if len(parts) >= 2 and parts[0].lower() == "source" and parts[1].lower() == "quests":
        if len(parts) > 2 and parts[2].lower() == prefix.lower():
            return "/".join(parts)
        return "/".join(parts[:2] + [prefix] + parts[2:])

    # quests/... (Quests.arc extract) -> quests/<prefix>/...
    if parts[0].lower() == "quests":
        if len(parts) > 1 and parts[1].lower() == prefix.lower():
            return "/".join(parts)
        return "/".join(["quests", prefix] + parts[1:])

    # conversations/... (Conversations.arc) -> conversations/<prefix>/...
    if parts[0].lower() == "conversations":
        if len(parts) > 1 and parts[1].lower() == prefix.lower():
            return "/".join(parts)
        return "/".join(["conversations", prefix] + parts[1:])

    return "/".join(parts)


def _collect_mapping(root: Path, base: str, prefix: str) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    src_root = root.joinpath(*base.split("/"))
    if not src_root.is_dir():
        return mapping
    for path in list(src_root.rglob("*")):
        if path.is_dir():
            continue
        rel = path.relative_to(root).as_posix()
        new_rel = namespace_rel(rel, prefix)
        if new_rel != rel:
            mapping[rel] = new_rel
    return mapping


def remap_tree(root: Path, prefix: str = "nydiamar", dry_run: bool = False) -> Tuple[List[str], List[str]]:
    moves: List[str] = []
    rewrites: List[str] = []
    mapping: Dict[str, str] = {}

    for base in ("records/quests", "source/quests", "quests", "conversations", "records/conversations"):
        mapping.update(_collect_mapping(root, base, prefix))

    # Conversations.arc extracts as flat/nested .cnv at the extract root (not under conversations/).
    # Namespace into <prefix>/ beside those files when this root is a conversation extract.
    cnv_at_root = list(root.glob("*.cnv"))
    has_records = (root / "records").is_dir() or (root / "quests").is_dir()
    if cnv_at_root and not has_records and not (root / "conversations").is_dir():
        for path in list(root.rglob("*")):
            if path.is_dir() or path.name.endswith("_report.md"):
                continue
            rel = path.relative_to(root).as_posix()
            first = rel.split("/")[0]
            if first.lower() == prefix.lower():
                continue
            mapping[rel] = f"{prefix}/{rel}"

    for old_rel, new_rel in sorted(mapping.items()):
        old_path = root.joinpath(*old_rel.split("/"))
        new_path = root.joinpath(*new_rel.split("/"))
        if not old_path.exists():
            continue
        moves.append(f"{old_rel} -> {new_rel}")
        if not dry_run:
            new_path.parent.mkdir(parents=True, exist_ok=True)
            if new_path.exists():
                new_path.unlink()
            shutil.move(str(old_path), str(new_path))

    text_ext = {".dbr", ".txt", ".lua", ".qst", ".cnv", ".md", ".json"}
    skip_names = {
        "quest_remap_report.md",
        "merge_conflicts.txt",
        "compat_report.md",
        "EDITOR_STITCH_CHECKLIST.md",
        "editor_stitch_checklist.md",
        "portal_hub.txt",
    }

    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in text_ext:
            continue
        if path.name in skip_names:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        original = text

        def repl_records(m: re.Match) -> str:
            return namespace_rel(m.group(1).replace("\\", "/") + m.group(2).replace("\\", "/"), prefix)

        def repl_loose(m: re.Match) -> str:
            rest = m.group(2).replace("\\", "/")
            return f"quests/{prefix}/{rest}"

        text = QUEST_TAG_RE.sub(repl_records, text)
        text = SOURCE_QUEST_RE.sub(repl_records, text)
        text = _loose_quest_re(prefix).sub(repl_loose, text)
        for old, new in mapping.items():
            if old in text:
                text = text.replace(old, new)

        if text != original:
            rewrites.append(path.relative_to(root).as_posix())
            if not dry_run:
                path.write_text(text, encoding="utf-8")

    return moves, rewrites


def write_report(path: Path, moves: List[str], rewrites: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Quest remap report",
        "",
        f"## Moves ({len(moves)})",
        *[f"- {m}" for m in moves],
        "",
        f"## Rewritten files ({len(rewrites)})",
        *[f"- {r}" for r in rewrites],
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Namespace mod quests to avoid vanilla overrides")
    p.add_argument("--root", required=True, help="Unpacked mod database/source root")
    p.add_argument("--prefix", default="nydiamar")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--report", default=None)
    args = p.parse_args(argv)

    root = Path(args.root)
    moves, rewrites = remap_tree(root, args.prefix, dry_run=args.dry_run)
    report = Path(args.report) if args.report else root / "quest_remap_report.md"
    write_report(report, moves, rewrites)
    print(f"Moves: {len(moves)}  Rewrites: {len(rewrites)}")
    print(f"Report: {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
