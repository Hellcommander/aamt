#!/usr/bin/env python3
"""
Pack two archives from the kitchen-sink merge:

1) Survival / Crucible DLC layer  →  <game>/survivalmode4/
   - Same layout as survivalmode1/2/3
   - Seeds Crucible flag files from official survivalmode3

2) Campaign Custom Game          →  <game>/mods/CampaignKitchenSink/
   - Base: NydiamarIntegrated (Nydiamar + Dungeons + portal stubs)
   - Overlay: SurvivalPlayground kitchen-sink classes/items (world maps kept from Nydiamar)

Source DB defaults to mods/SurvivalPlayground (build that first).
Build NydiamarIntegrated before packing campaign (Run-NydiamarFoACampaign).
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from dbr_io import merge_dbr_preserve_both, read_dbr, write_dbr
from gd_paths import GamePaths, resolve_game_dir
from pack_survival_dlc_layer import deploy_survival_dlc

TOOLS_DIR = Path(__file__).resolve().parent

# Official Crucible layers always ship these under records/game/
SURVIVAL_FLAG_RELS = (
    "records/game/gameachievements.dbr",
    "records/game/gamefactions.dbr",
)


def _probe_dir() -> Path:
    return TOOLS_DIR / "work" / "survival_layers_probe"


def ensure_survival_probe(game: GamePaths) -> Path:
    """Extract survivalmode3 once for flag-file seeding."""
    from archive_tool import ArchiveTool, kill_orphan_archivetool

    probe = _probe_dir() / "survivalmode3"
    marker = probe / ".ok"
    if marker.is_file():
        return probe
    layer = game.game_dir / "survivalmode3"
    arz = next((layer / "database").glob("*.arz"), None)
    if arz is None:
        raise FileNotFoundError(f"No SurvivalMode3.arz under {layer}")
    if probe.exists():
        shutil.rmtree(probe)
    probe.mkdir(parents=True)
    print(f"Extracting {arz.name} for Crucible flag seeds ...", flush=True)
    ArchiveTool(game.game_dir).extract_database(arz, probe)
    marker.write_text("ok", encoding="utf-8")
    kill_orphan_archivetool()
    return probe


def seed_survival_flags(dest_db: Path, official_db: Path) -> List[str]:
    """
    Ensure survivalmode4 carries the same game/* flag DBRs official layers use.
    Official survivalmode3 is the base; kitchen-sink only adds keys that do not
    conflict with ACH / Steam / faction reward hooks.
    """
    notes: List[str] = []
    for rel in SURVIVAL_FLAG_RELS:
        src = official_db / rel
        dest = dest_db / rel
        if not src.is_file():
            notes.append(f"WARN: missing official seed {rel}")
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.is_file():
            merged = merge_dbr_preserve_both(
                read_dbr(src),
                read_dbr(dest),
                prefer_overlay_substrings=(),
                keep_base_substrings=("ach", "ACH", "steam", "faction", "reward"),
            )
            write_dbr(dest, merged)
            notes.append(f"Seeded+merged flag {rel}")
        else:
            shutil.copy2(src, dest)
            notes.append(f"Seeded flag {rel}")
    return notes


# When overlaying Survival playground DB onto Nydiamar campaign base, never replace
# Nydiamar/dungeon world maps. Proxies are merged (needed for World001 + mob scaling).
CAMPAIGN_KEEP_BASE_PREFIXES = (
    "records/world/",
    "records/levels/",
    "records/storyelements/",
    "maps/",
)


def _overlay_db_onto_campaign(src_db: Path, dest_db: Path) -> Tuple[int, int, int]:
    """
    Additive merge of kitchen-sink DBRs onto campaign base.
    Skips survival world/map paths. Existing .dbr files are field-merged
    (unique keys from both); never whole-file replace.
    Returns (added, field_merged, skipped_world).
    """
    added = field_merged = skipped = 0
    for path in src_db.rglob("*"):
        if not path.is_file() or path.suffix.lower() == ".arz":
            continue
        rel = path.relative_to(src_db).as_posix()
        rl = rel.lower()
        if any(rl.startswith(p) for p in CAMPAIGN_KEEP_BASE_PREFIXES):
            skipped += 1
            continue
        target = dest_db / rel
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            added += 1
            continue
        if path.suffix.lower() == ".dbr" and target.suffix.lower() == ".dbr":
            try:
                merged = merge_dbr_preserve_both(
                    read_dbr(target),
                    read_dbr(path),
                    prefer_overlay_substrings=(
                        "skill",
                        "Skill",
                        "item",
                        "Item",
                        "loot",
                        "Loot",
                        "character",
                        "Character",
                        "class",
                        "Class",
                        "mastery",
                        "Mastery",
                    ),
                    keep_base_substrings=(
                        "quest",
                        "Quest",
                        "conversation",
                        "Conversation",
                        "nydiamar",
                        "Nydiamar",
                        "spawn",
                        "Spawn",
                    ),
                    list_prefixes=(
                        "skillName",
                        "skillTree",
                        "itemName",
                        "lootName",
                        "skillCtrlPane",
                    ),
                    semicolon_keys=("skillTree",),
                )
                write_dbr(target, merged)
                field_merged += 1
            except Exception:
                # Keep campaign base on parse failure — never clobber
                pass
        # Non-dbr same path: keep campaign base (no binary override)
    return added, field_merged, skipped


def pack_campaign_mod(
    game: GamePaths,
    source_mod: Path,
    out_name: str = "CampaignKitchenSink",
    *,
    campaign_base: str = "NydiamarIntegrated",
) -> Tuple[Path, str]:
    """
    Build the CAMPAIGN Custom Game:

      base  = NydiamarIntegrated (FoA + Nydiamar + Dungeons, portal stubs)
      overlay = kitchen-sink DB from SurvivalPlayground (classes/items/UI)

    Dungeons stay reachable via portals inside the Nydiamar world after the
    campaign-hub → Nydiamar stitch — not as a separate campaign replace.
    """
    out = game.mods_dir / out_name
    if out.exists():
        shutil.rmtree(out)

    base = game.mods_dir / campaign_base
    notes: List[str] = []

    if base.is_dir() and (base / "database").is_dir():
        shutil.copytree(base, out, ignore=shutil.ignore_patterns("*.arz"))
        notes.append(f"Campaign base: {base.name} (Nydiamar + Dungeons + portal stubs)")
        src_db = source_mod / "database" if (source_mod / "database").is_dir() else source_mod
        if src_db.is_dir():
            c, o, s = _overlay_db_onto_campaign(src_db, out / "database")
            notes.append(
                f"Kitchen-sink merge from {source_mod.name}: "
                f"added={c} field_merged={o} skipped_world={s}"
            )
        # Merge kitchen-sink text/UI into campaign resources (additive; never wipe Maps)
        src_res = source_mod / "resources"
        dest_res = out / "resources"
        if src_res.is_dir():
            dest_res.mkdir(parents=True, exist_ok=True)
            from nydiamar_campaign import merge_arc_contents

            for name in ("Text_EN.arc", "text_en.arc", "UI.arc", "ui.arc"):
                arc = src_res / name
                if not arc.is_file():
                    continue
                dest = dest_res / arc.name
                if dest.is_file():
                    notes.append(merge_arc_contents(game, dest, arc, dest))
                else:
                    shutil.copy2(arc, dest)
                    notes.append(f"Resource added: {arc.name}")
        # Localization / combo tags — add missing only
        for sub in ("localization",):
            sdir = source_mod / sub
            if sdir.is_dir():
                ddir = out / sub
                ddir.mkdir(parents=True, exist_ok=True)
                for f in sdir.glob("*.txt"):
                    dest = ddir / f.name
                    if dest.exists():
                        notes.append(f"Kept base localization: {f.name}")
                        continue
                    shutil.copy2(f, dest)
    else:
        notes.append(
            f"WARN: {campaign_base} missing — packing kitchen-sink only "
            f"(run Nydiamar pipeline first for portals/dungeons)."
        )
        if (source_mod / "database").is_dir():
            shutil.copytree(source_mod, out, ignore=shutil.ignore_patterns("*.arz"))
        else:
            out.mkdir(parents=True)
            shutil.copytree(source_mod, out / "database")

    # Kitchen-sink World001 (Grimarillion levels, etc.) is the Custom Game START.
    # Nydiamar Maps.arc stays for portal destinations only — never the spawn world.
    # Do NOT copy vanilla gdx Levels; that drops Grimarillion map edits.
    try:
        from campaign_start_world import install_campaign_start_world

        notes.extend(
            install_campaign_start_world(game, out, staging_mod=source_mod)
        )
    except Exception as exc:
        notes.append(f"WARN: kitchen-sink start world not installed: {exc}")

    readme = out / "README_CAMPAIGN_ARCHIVE.txt"
    readme.write_text(
        "\n".join(
            [
                f"Campaign Custom Game archive: {out_name}",
                f"Kitchen-sink source: {source_mod}",
                f"Campaign base: {campaign_base}",
                "",
                "Start world = kitchen-sink World001 (Grimarillion levels merge),",
                "NOT stock FoA and NOT Nydiamar. Nydiamar/Dungeons = portal only.",
                "",
                "Access: Custom Game → this folder → select **World001.map** (NOT nydiamar).",
                "  1) Play merged campaign world from normal start",
                "  2) Editor-stitch portal: campaign hub → Nydiamar (and return portal)",
                "  3) NydiamarDungeons: in-world portals inside Nydiamar after you arrive",
                "",
                "Crucible/Survival uses survivalmode4 separately (no Nydiamar maps there).",
                "",
                "Notes:",
                *[f"  - {n}" for n in notes],
                "",
            ]
        ),
        encoding="utf-8",
    )
    n = sum(1 for _ in (out / "database").rglob("*.dbr")) if (out / "database").is_dir() else 0
    return out, f"Campaign Custom Game -> {out} ({n} DBRs)\n" + "\n".join(f"  {n}" for n in notes)


def pack_dual(
    game: GamePaths,
    source: Path,
    *,
    survival_layer: str = "survivalmode4",
    campaign_mod: str = "CampaignKitchenSink",
    campaign_base: str = "NydiamarIntegrated",
    skip_survival: bool = False,
    skip_campaign: bool = False,
) -> str:
    lines: List[str] = ["# Dual archive pack", ""]
    if not skip_survival:
        layer, msg = deploy_survival_dlc(
            game, source, layer_name=survival_layer, rebuild=False
        )
        lines.append("## Survival DLC layer")
        lines.append(msg)
        try:
            official = ensure_survival_probe(game)
            seed_notes = seed_survival_flags(layer / "database", official)
            lines.extend(seed_notes)
        except Exception as exc:
            lines.append(f"WARN: could not seed Crucible flags: {exc}")
        lines.append(f"Survival layer path: {layer}")
        lines.append("")

    if not skip_campaign:
        out, msg = pack_campaign_mod(
            game,
            source,
            out_name=campaign_mod,
            campaign_base=campaign_base,
        )
        lines.append("## Campaign Custom Game")
        lines.append(msg)
        lines.append("")

    # Re-apply class UI on packed outputs (safe if already applied on source)
    try:
        from patch_class_ui import patch_mod_database as patch_class_ui_db

        lines.append("## Class UI (up to 120)")
        for label, db in (
            ("survivalmode4", game.game_dir / "survivalmode4" / "database"),
            (campaign_mod, game.mods_dir / campaign_mod / "database"),
        ):
            if skip_survival and label.startswith("survival"):
                continue
            if skip_campaign and label == campaign_mod:
                continue
            if db.is_dir():
                lines.append(patch_class_ui_db(db, max_classes=120))
        lines.append("")
    except Exception as exc:
        lines.append(f"WARN: class UI patch failed: {exc}")
        lines.append("")

    # Imbalance: mobs fully scale to player level (only this Smash n Grab–style feature)
    try:
        from patch_mob_player_scale import patch_database as patch_mob_scale

        lines.append("## Mob player-level scale")
        for label, db in (
            ("survivalmode4", game.game_dir / "survivalmode4" / "database"),
            (campaign_mod, game.mods_dir / campaign_mod / "database"),
            ("SurvivalPlayground", source / "database"),
        ):
            if skip_survival and label.startswith("survival"):
                continue
            if skip_campaign and label == campaign_mod:
                continue
            if db is not None and db.is_dir():
                c, a, s = patch_mob_scale(db)
                lines.append(f"{label}: changed={c} already={a} skipped={s}")
        lines.append("")
    except Exception as exc:
        lines.append(f"WARN: mob scale patch failed: {exc}")
        lines.append("")

    lines.append("Next: Asset Manager / arzedit build .arz for each output.")
    lines.append(
        "Play: Crucible -> survivalmode4; "
        "Campaign -> Custom Game CampaignKitchenSink "
        "(Nydiamar + Dungeons + kitchen-sink classes)."
    )
    report = TOOLS_DIR / "work" / "dual_archive_pack_report.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(lines) + "\n"
    report.write_text(text, encoding="utf-8")
    lines.append(f"Report: {report}")
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(
        description="Pack Survival DLC layer + Campaign Custom Game from kitchen-sink"
    )
    p.add_argument("--game", default=None)
    p.add_argument("--source", default="SurvivalPlayground")
    p.add_argument("--survival-layer", default="survivalmode4")
    p.add_argument("--campaign-mod", default="CampaignKitchenSink")
    p.add_argument(
        "--campaign-base",
        default="NydiamarIntegrated",
        help="Campaign shell under mods/ (Nydiamar + Dungeons). Default NydiamarIntegrated",
    )
    p.add_argument("--skip-survival", action="store_true")
    p.add_argument("--skip-campaign", action="store_true")
    p.add_argument(
        "--rebuild",
        action="store_true",
        help="After packing, build .arz via toolset arzedit",
    )
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
            print("Build SurvivalPlayground first.", file=sys.stderr)
            return 1

    report = pack_dual(
        game,
        src,
        survival_layer=args.survival_layer,
        campaign_mod=args.campaign_mod,
        campaign_base=args.campaign_base,
        skip_survival=args.skip_survival,
        skip_campaign=args.skip_campaign,
    )
    try:
        print(report)
    except UnicodeEncodeError:
        print(report.encode("ascii", "replace").decode("ascii"))

    if args.rebuild:
        from build_mod_arz import build_target
        from gd_paths import resolve_arzedit

        arz = resolve_arzedit()
        if arz is None:
            print("WARN: --rebuild requested but arzedit.exe missing. Run Build-Arzedit.bat.", file=sys.stderr)
            return 1
        if not args.skip_survival:
            ok, msg = build_target(
                game, game.game_dir / args.survival_layer, arz_stem="SurvivalMode4", arzedit=arz
            )
            print(msg)
            if not ok:
                return 1
        if not args.skip_campaign:
            ok, msg = build_target(
                game, game.mods_dir / args.campaign_mod, arz_stem=args.campaign_mod, arzedit=arz
            )
            print(msg)
            if not ok:
                return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
