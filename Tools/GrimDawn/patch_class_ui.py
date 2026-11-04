#!/usr/bin/env python3
"""
Expand class-selection UI + skills_mastertable to support many masteries.

- Maps unique PC skillTree lines to classtable.dbr panes (deduped)
- Caps at --max-classes (default 120)
- Extends masteryMasteryButtons / bitmaps / tags / text lists
- Lays buttons out in a dense multi-column grid
- Enlarges the class-selection scroll window (alwaysShowScroll)

Does not bypass the engine's 2-active-masteries limit.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from dbr_io import get_list_field, read_dbr, set_list_field, write_dbr
from gd_paths import GamePaths, resolve_game_dir

TOOLS_DIR = Path(__file__).resolve().parent

# DoM-style grid (11 columns); tighter row step so ~120 fit in the selection pane
GRID_COLS = 11
GRID_ORIGIN_X = 27
GRID_ORIGIN_Y = 20
GRID_STEP_X = 72
GRID_STEP_Y = 56

MAX_DEFAULT = 120

CLASS_SEL_REL = "records/ui/skills/classselection/skills_classselectiontable.dbr"
MASTER_REL = "records/ui/skills/skills_mastertable.dbr"
SCROLL_REL = "records/ui/skills/classselection/skills_classselectionscrollbox.dbr"
PC_REL = "records/creatures/pc/malepc01.dbr"
PC_RELS = (PC_REL, "records/creatures/pc/femalepc01.dbr")


def _norm(rel: str) -> str:
    return rel.replace("\\", "/").strip().lower()


VANILLA_LAYERS = TOOLS_DIR / "work" / "_vanilla_cache" / "layers"


def index_classtables(db: Path, extra_roots: Sequence[Path] = ()) -> Dict[str, str]:
    """Map lower-case relative path -> canonical relative path for classtable.dbr.

    extra_roots: official layers -- mods that don't override the stock class UI still use it.
    """
    out: Dict[str, str] = {}
    for root in [*extra_roots, db]:
        if not Path(root).is_dir():
            continue
        for p in Path(root).rglob("classtable.dbr"):
            rel = p.relative_to(root).as_posix()
            out[_norm(rel)] = rel
    return out


def official_layer_roots() -> List[Path]:
    if not VANILLA_LAYERS.is_dir():
        return []
    return [d for d in VANILLA_LAYERS.iterdir() if d.is_dir()]


def map_tree_to_classtable(tree_rel: str, classtables: Dict[str, str]) -> Optional[str]:
    t = _norm(tree_rel)
    cands: List[str] = []

    m = re.search(r"playerclass(\d{2})", t)
    if m:
        cands.append(f"records/ui/skills/class{m.group(1)}/classtable.dbr")

    # named vanilla-style folders
    m = re.search(r"playerclass([a-z0-9]+)", t)
    if m:
        name = m.group(1)
        if not name.isdigit():
            cands += [
                f"records/ui/skills/class{name}/classtable.dbr",
                f"records/ui/skills/playerclass{name}/classtable.dbr",
                f"records/ui/skills/{name}/classtable.dbr",
            ]

    m = re.search(r"zenithclass(\d{2})", t)
    if m:
        cands.append(f"records/ui/skills/zenithclass{m.group(1)}/classtable.dbr")

    m = re.search(r"ddclass(\d{2})", t)
    if m:
        cands.append(f"records/ui/skills/ddclass{m.group(1)}/classtable.dbr")

    m = re.search(r"swampdwellerclass", t)
    if m:
        cands.append("records/ui/skills/swampdwellerclass/classtable.dbr")
    m = re.search(r"frigidhunterclass", t)
    if m:
        cands.append("records/ui/skills/frigidhunterclass/classtable.dbr")

    # records/<pack>/skills/<class>/
    m = re.search(r"records/(d3|tq|cat|ncff|apoc|zen|d2|doh|sparker)/skills/([^/]+)/", t)
    if m:
        pack, cls = m.group(1), m.group(2)
        cands += [
            f"records/{pack}/ui/skills/{cls}/classtable.dbr",
            f"records/ui/skills/{pack}/{cls}/classtable.dbr",
            f"records/ui/skills/{cls}/classtable.dbr",
        ]

    # records/skills/<folder>/
    m = re.search(r"records/skills/([^/]+)/", t)
    if m:
        folder = m.group(1)
        cands += [
            f"records/ui/skills/{folder}/classtable.dbr",
            f"records/ui/skills/class{folder}/classtable.dbr",
        ]

    for c in cands:
        hit = classtables.get(_norm(c))
        if hit:
            return hit
    return None


def collect_roster(db: Path, max_classes: int) -> Tuple[List[str], List[str], List[str]]:
    """
    Returns (skill_trees, classtables, notes_skipped).
    Dedupes by classtable path; preserves skillTree order.
    """
    pc = db / PC_REL
    if not pc.is_file():
        raise FileNotFoundError(f"Missing {pc}")
    trees = get_list_field(read_dbr(pc), "skillTree")
    classtables = index_classtables(db, official_layer_roots())

    out_trees: List[str] = []
    out_panes: List[str] = []
    seen_pane: set = set()
    skipped: List[str] = []

    for tree in trees:
        pane = map_tree_to_classtable(tree, classtables)
        if not pane:
            skipped.append(f"no classtable: {tree}")
            continue
        key = _norm(pane)
        if key in seen_pane:
            skipped.append(f"duplicate pane: {tree} -> {pane}")
            continue
        seen_pane.add(key)
        out_trees.append(tree)
        out_panes.append(pane)
        if len(out_panes) >= max_classes:
            break

    return out_trees, out_panes, skipped


def _split_semi(value: str) -> List[str]:
    return [p.strip() for p in (value or "").split(";") if p.strip()]


def _join_semi(parts: List[str]) -> str:
    return ";".join(parts)


def _grid_pos(index: int) -> Tuple[int, int]:
    col = index % GRID_COLS
    row = index // GRID_COLS
    return GRID_ORIGIN_X + col * GRID_STEP_X, GRID_ORIGIN_Y + row * GRID_STEP_Y


def _ensure_button(
    db: Path,
    index: int,
    template_btn: Path,
    existing_btn: Optional[str],
) -> str:
    """Return relative path to a button DBR positioned for this index."""
    cs = db / "records/ui/skills/classselection"
    cs.mkdir(parents=True, exist_ok=True)
    dest_rel = f"records/ui/skills/classselection/skills_classselectionbutton_ks_{index+1:03d}.dbr"
    dest = db / dest_rel

    if existing_btn:
        src = db / existing_btn
        if src.is_file():
            data = read_dbr(src)
        elif template_btn.is_file():
            data = read_dbr(template_btn)
        else:
            data = {
                "templateName": "database/templates/ingameui/buttonstatic.tpl",
                "FileDescription": f"ClassSelect {index+1}",
            }
    else:
        data = read_dbr(template_btn) if template_btn.is_file() else {
            "templateName": "database/templates/ingameui/buttonstatic.tpl",
            "FileDescription": f"ClassSelect {index+1}",
        }

    x, y = _grid_pos(index)
    data["bitmapPositionX"] = str(x)
    data["bitmapPositionY"] = str(y)
    data["FileDescription"] = f"KitchenSink class button {index+1}"
    write_dbr(dest, data)
    return dest_rel


def _copy_dbr_replace(src: Path, dest: Path) -> None:
    """Copy a DBR without shutil.copy2 (avoids WinError 32 on locked dests)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    data = read_dbr(src)
    if dest.is_file():
        try:
            dest.unlink()
        except OSError:
            pass
    write_dbr(dest, data)


def _ensure_text(db: Path, index: int, template_text: Path, existing: Optional[str]) -> str:
    dest_rel = f"records/ui/skills/classselection/skills_classselectiontext_ks_{index+1:03d}.dbr"
    dest = db / dest_rel
    if existing and (db / existing).is_file():
        _copy_dbr_replace(db / existing, dest)
    elif template_text.is_file():
        _copy_dbr_replace(template_text, dest)
    else:
        write_dbr(
            dest,
            {
                "templateName": "database/templates/ingameui/text.tpl",
                "FileDescription": f"ClassSelect text {index+1}",
            },
        )
    return dest_rel


def patch_scrollbox(db: Path) -> None:
    """Enlarge class-selection scroll window and force scrollbar."""
    path = db / SCROLL_REL
    if path.is_file():
        data = read_dbr(path)
    else:
        data = {
            "templateName": "database/templates/ingameui/scrollablewindow.tpl",
            "FileDescription": "ScrollableWindow",
            "verticalScrollbar": "records/ui/generic/scrollbox_vscroll.dbr",
        }
    # Cover the dense button grid (~11x11) + description area
    data.update(
        {
            "templateName": "database/templates/ingameui/scrollablewindow.tpl",
            "FileDescription": "ScrollableWindow (kitchen-sink class select)",
            "alwaysShowScroll": "1",
            "showBackground": "0",
            "positionX": "20",
            "positionY": "10",
            "width": "820",
            "height": "640",
            "verticalScrollbar": data.get(
                "verticalScrollbar", "records/ui/generic/scrollbox_vscroll.dbr"
            ),
        }
    )
    write_dbr(path, data)


def _newest_official(rel: str) -> Optional[Path]:
    roots = sorted(official_layer_roots(), key=lambda d: (d.name.lower() != "database", d.name.lower()), reverse=True)
    return next((r / rel for r in roots if (r / rel).is_file()), None)


def _tree_exists(db: Path, tree: str) -> bool:
    rel = tree.strip().replace("\\", "/")
    return rel.lower().endswith(".dbr") and any((r / rel).is_file() for r in [db, *official_layer_roots()])


def align_pc_trees(db: Path, roster: List[str], capped: bool) -> int:
    """Make male/female PC skillTree start with the roster in pane order; returns dropped count.

    Refuses (returns -1) when a real class tree would be dropped: only junk entries go.
    """
    pc = db / PC_REL
    if pc.is_file():
        keep_n = {_norm(t) for t in roster}
        real_lost = [t for t in get_list_field(read_dbr(pc), "skillTree") if _norm(t) not in keep_n and _tree_exists(db, t)]
        if real_lost and not capped:
            print(f"  WARN: not aligning PC trees; {len(real_lost)} real class trees have no UI pane: {real_lost[:5]}", flush=True)
            return -1
    dropped = 0
    keep = {_norm(t) for t in roster}
    for rel in PC_RELS:
        path = db / rel
        if not path.is_file():
            continue
        data = read_dbr(path)
        trees = get_list_field(data, "skillTree")
        tail: List[str] = []
        if capped:
            # Trees cut by the cap stay (unselectable) after the last rostered tree
            hits = [i for i, t in enumerate(trees) if _norm(t) in keep]
            start = hits[-1] + 1 if hits else len(trees)
            tail = [t for t in trees[start:] if _norm(t) not in keep]
        aligned = list(roster) + tail
        if [_norm(t) for t in aligned] != [_norm(t) for t in trees]:
            set_list_field(data, "skillTree", aligned)
            write_dbr(path, data)
        dropped = max(dropped, len(trees) - len(aligned))
    return dropped


def patch_mod_database(db: Path, max_classes: int = MAX_DEFAULT, align_pc: bool = True) -> str:
    trees, panes, skipped = collect_roster(db, max_classes)
    n = len(panes)
    if n == 0:
        raise RuntimeError(f"No classtables mapped under {db}")

    # Mods that don't override the stock UI records start from the newest official copy
    for rel in (MASTER_REL, CLASS_SEL_REL, SCROLL_REL):
        if not (db / rel).is_file():
            src = _newest_official(rel)
            if src:
                _copy_dbr_replace(src, db / rel)

    # --- mastertable panes ---
    mt_path = db / MASTER_REL
    mt = read_dbr(mt_path) if mt_path.is_file() else {"templateName": "database/templates/ui/skillmastertable.tpl"}
    set_list_field(mt, "skillCtrlPane", panes)
    write_dbr(mt_path, mt)

    # --- class selection lists ---
    sel_path = db / CLASS_SEL_REL
    if not sel_path.is_file():
        raise FileNotFoundError(sel_path)
    sel = read_dbr(sel_path)
    old_btns = _split_semi(sel.get("masteryMasteryButtons", ""))
    old_bmps = _split_semi(sel.get("masteryMasterySelectedBitmapNames", ""))
    old_tags = _split_semi(sel.get("masteryMasterySelectedDescriptionTags", ""))
    old_txts = _split_semi(sel.get("masteryMasteryText", ""))

    cs = db / "records/ui/skills/classselection"
    template_btn = next(cs.glob("skills_classselectionbutton*.dbr"), None)
    if template_btn is None:
        template_btn = cs / "skills_classselectionbutton01.dbr"
    template_txt = next(cs.glob("skills_classselectiontext*.dbr"), None)
    if template_txt is None:
        template_txt = cs / "skills_classselectiontext01.dbr"

    new_btns: List[str] = []
    new_txts: List[str] = []
    new_bmps: List[str] = []
    new_tags: List[str] = []

    fallback_bmp = old_bmps[0] if old_bmps else "ui/skills/classselection/skills_classselectedimage01.tex"
    for i in range(n):
        prev_btn = old_btns[i] if i < len(old_btns) else None
        prev_txt = old_txts[i] if i < len(old_txts) else None
        new_btns.append(_ensure_button(db, i, template_btn, prev_btn))
        new_txts.append(_ensure_text(db, i, template_txt, prev_txt))
        new_bmps.append(old_bmps[i] if i < len(old_bmps) else fallback_bmp)
        # Prefer existing tag; else tagSkillClassNameNN
        if i < len(old_tags):
            new_tags.append(old_tags[i])
        else:
            new_tags.append(f"tagSkillClassName{i+1:02d}")

    sel["masteryMasteryButtons"] = _join_semi(new_btns)
    sel["masteryMasteryText"] = _join_semi(new_txts)
    sel["masteryMasterySelectedBitmapNames"] = _join_semi(new_bmps)
    sel["masteryMasterySelectedDescriptionTags"] = _join_semi(new_tags)
    # Keep description scroll window pointer
    sel["masterySelectedMasteryDescriptionScrollWindow"] = SCROLL_REL.replace("\\", "/")
    write_dbr(sel_path, sel)

    patch_scrollbox(db)

    # Mastery N on the PC must be pane N in the UI (and combo tag id N), so drop PC
    # entries that have no pane; trees past the cap stay at the end (unselectable).
    dropped = align_pc_trees(db, trees, capped=n >= max_classes) if align_pc else 0
    lines = [
        f"Patched class UI in {db}",
        f"  skillCtrlPane / selection slots: {n} (cap {max_classes})",
        f"  PC skillTree count: {len(get_list_field(read_dbr(db / PC_REL), 'skillTree'))}"
        + (f" (dropped {dropped} junk entries to keep indexes aligned)" if dropped > 0 else "")
        + (" (left unaligned: see warning)" if dropped < 0 else ""),
        f"  scrollbox: {SCROLL_REL} (820x640, alwaysShowScroll=1)",
        f"  button grid: {GRID_COLS} cols, step ({GRID_STEP_X},{GRID_STEP_Y})",
    ]
    if skipped:
        lines.append(f"  skipped/unmapped: {len(skipped)}")
        for s in skipped[:25]:
            lines.append(f"    - {s}")
        if len(skipped) > 25:
            lines.append(f"    ... +{len(skipped)-25} more")
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Expand class selection UI up to N classes")
    p.add_argument("--game", default=None)
    p.add_argument(
        "--mod",
        action="append",
        default=None,
        help="Mod folder under mods/ or absolute path (repeatable). "
        "Default: SurvivalPlayground, CampaignKitchenSink, and game-root survivalmode4",
    )
    p.add_argument("--max-classes", type=int, default=MAX_DEFAULT)
    args = p.parse_args(argv)

    game = GamePaths(resolve_game_dir(args.game))
    targets: List[Path] = []
    if args.mod:
        for m in args.mod:
            path = Path(m)
            if not path.is_dir():
                path = game.mods_dir / m
            if (path / "database").is_dir():
                path = path / "database"
            targets.append(path)
    else:
        for name in ("SurvivalPlayground", "CampaignKitchenSink"):
            db = game.mods_dir / name / "database"
            if db.is_dir():
                targets.append(db)
        sm4 = game.game_dir / "survivalmode4" / "database"
        if sm4.is_dir():
            targets.append(sm4)

    if not targets:
        print("No target databases found.", file=sys.stderr)
        return 1

    rc = 0
    for db in targets:
        try:
            print(patch_mod_database(db, max_classes=args.max_classes), flush=True)
            print("", flush=True)
        except Exception as exc:
            print(f"ERROR {db}: {exc}", file=sys.stderr)
            rc = 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
