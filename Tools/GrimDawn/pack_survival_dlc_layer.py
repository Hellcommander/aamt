#!/usr/bin/env python3
"""
Deploy a SurvivalPlayground (or other) database as a Crucible/Survival DLC-style layer.

Official Crucible expansions live next to the game EXE, not under mods/:
  survivalmode1/  (AoM-era Crucible)
  survivalmode2/  (FG-era Crucible)
  survivalmode3/  (FoA-era Crucible)

Layout matches those folders:
  <game>/survivalmode4/database/SurvivalMode4.arz   (or unpacked .dbr until built)
  <game>/survivalmode4/resources/…

Playing via the normal Survival/Crucible entry keeps Steam achievements hooked to that mode,
unlike a Custom Game under mods/.

Note: the engine may only auto-load survivalmode1–3 (DLC-installed). If survivalmode4 is
ignored in-game, use --fallback-patch-layer survivalmode3 (backs up first) or keep Custom Game.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from arz_backend import build_database
from gd_paths import (
    GamePaths,
    resolve_arzedit,
    resolve_game_dir,
    survival_layer_dirs,
)

TOOLS_DIR = Path(__file__).resolve().parent


def _copy_database(src_db: Path, dest_db: Path) -> int:
    """Copy unpacked DBRs (skip .arz). Returns file count."""
    n = 0
    if dest_db.exists():
        shutil.rmtree(dest_db)
    dest_db.mkdir(parents=True)
    for path in src_db.rglob("*"):
        if not path.is_file() or path.suffix.lower() == ".arz":
            continue
        rel = path.relative_to(src_db)
        target = dest_db / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        n += 1
    return n


def _backup_layer(layer: Path) -> Optional[Path]:
    if not layer.exists():
        return None
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = layer.parent / f"{layer.name}_backup_{stamp}"
    shutil.copytree(layer, bak)
    return bak


def deploy_survival_dlc(
    game: GamePaths,
    source_mod: Path,
    *,
    layer_name: str = "survivalmode4",
    fallback_patch_layer: Optional[str] = None,
    rebuild: bool = False,
    arzedit: Optional[Path] = None,
) -> Tuple[Path, str]:
    """
    Deploy source Custom Game / unpacked mod into a game-root survivalmodeN layer.
    Returns (layer_path, message).
    """
    src_db = source_mod / "database" if (source_mod / "database").is_dir() else source_mod
    if not src_db.is_dir():
        raise FileNotFoundError(f"Source database not found: {src_db}")

    if fallback_patch_layer:
        layer_name = fallback_patch_layer

    layer = game.game_dir / layer_name
    official = {p.name.lower() for p in survival_layer_dirs(game.game_dir)}

    notes = []
    if layer_name.lower() in official and fallback_patch_layer:
        bak = _backup_layer(layer)
        notes.append(f"Backed up existing {layer_name} → {bak}")
    elif layer.exists() and layer_name.lower() not in ("survivalmode1", "survivalmode2", "survivalmode3"):
        bak = _backup_layer(layer)
        if bak:
            notes.append(f"Backed up previous {layer_name} → {bak}")
        shutil.rmtree(layer)
    elif layer_name.lower() in ("survivalmode1", "survivalmode2", "survivalmode3") and not fallback_patch_layer:
        raise ValueError(
            f"Refusing to overwrite official {layer_name} without --fallback-patch-layer {layer_name}"
        )

    layer.mkdir(parents=True, exist_ok=True)
    dest_db = layer / "database"
    n = _copy_database(src_db, dest_db)
    notes.append(f"Copied {n} database files into {dest_db}")

    # Lightweight resources: copy Text tags if present on source
    dest_res = layer / "resources"
    dest_res.mkdir(parents=True, exist_ok=True)
    src_res = source_mod / "resources"
    if src_res.is_dir():
        for arc_name in ("Text_EN.arc", "text_en.arc", "UI.arc", "ui.arc"):
            arc = src_res / arc_name
            if arc.is_file():
                shutil.copy2(arc, dest_res / arc.name)
                notes.append(f"Copied resource {arc.name}")

    arz_stem = "SurvivalMode4"
    if layer_name.lower().startswith("survivalmode") and layer_name[-1].isdigit():
        arz_stem = f"SurvivalMode{layer_name[-1]}"

    readme = layer / "README_SURVIVAL_DLC.txt"
    readme.write_text(
        "\n".join(
            [
                f"Survival/Crucible DLC-style layer: {layer_name}",
                f"Source: {source_mod}",
                "",
                "IMPORTANT: This layer only affects Crucible/Survival (main menu).",
                "It does NOT replace or extend the main campaign. Campaign still uses",
                "database + gdx1/gdx2/gdx3 (or a Custom Game under mods\\).",
                "",
                "Keep mods\\SurvivalPlayground (or a campaign Custom Game) if you want",
                "the merged classes/items outside Crucible.",
                "",
                "Official Crucible layers: survivalmode1 (AoM), survivalmode2 (FG), survivalmode3 (FoA).",
                "",
                "Build database:",
                "  1) Open Asset Manager → point at this folder as a mod/working dir, Build, OR",
                "  2) Use arzedit --rebuild from the tools GUI / CLI.",
                f"Expected ARZ name: database/{arz_stem}.arz",
                "",
                "If the game ignores survivalmode4, re-run with --fallback-patch-layer survivalmode3",
                "(creates a timestamped backup of the official FoA Crucible layer first).",
                "",
                "Steam updates may restore official survivalmode1-3 — keep backups.",
                "",
            ]
            + notes
        ),
        encoding="utf-8",
    )

    if rebuild:
        # Temporary mod-shaped folder for arzedit (expects mod root)
        ok, msg = build_database(layer, game.game_dir, arzedit or resolve_arzedit())
        notes.append(msg)
        # Rename produced .arz if needed
        for arz in (dest_db.glob("*.arz")):
            target = dest_db / f"{arz_stem}.arz"
            if arz.name != target.name:
                if target.exists():
                    target.unlink()
                arz.rename(target)
                notes.append(f"Renamed {arz.name} → {target.name}")
        if not ok:
            return layer, "\n".join(notes)

    # List official layers for the operator
    existing = [p.name for p in survival_layer_dirs(game.game_dir)]
    notes.append(f"Survival layers present: {', '.join(existing) or '(none)'}")
    return layer, "\n".join(notes)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Deploy merged Survival content as a survivalmodeN DLC-style layer"
    )
    p.add_argument("--game", default=None)
    p.add_argument(
        "--source",
        default="SurvivalPlayground",
        help="Source under mods/ or path to unpacked mod (default SurvivalPlayground)",
    )
    p.add_argument(
        "--layer",
        default="survivalmode4",
        help="Game-root layer folder name (default survivalmode4)",
    )
    p.add_argument(
        "--fallback-patch-layer",
        default=None,
        help="If set (e.g. survivalmode3), patch that official layer after backup",
    )
    p.add_argument("--rebuild", action="store_true", help="Try arzedit build")
    p.add_argument("--arzedit", default=None)
    args = p.parse_args(argv)

    game = GamePaths(resolve_game_dir(args.game))
    game.validate()

    src = Path(args.source)
    if not src.is_dir():
        cand = game.mods_dir / args.source
        if cand.is_dir():
            src = cand
        else:
            print(f"Source not found: {args.source}", file=sys.stderr)
            return 1

    try:
        layer, msg = deploy_survival_dlc(
            game,
            src,
            layer_name=args.layer,
            fallback_patch_layer=args.fallback_patch_layer,
            rebuild=args.rebuild,
            arzedit=resolve_arzedit(args.arzedit),
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(msg)
    print(f"Done: {layer}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
