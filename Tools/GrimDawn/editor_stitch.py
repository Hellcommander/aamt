#!/usr/bin/env python3
"""Prepare Maps/Quests for World Editor stitch and emit checklist + portal stubs."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

from archive_tool import ArchiveTool

# Prefer portal / riftgate stitch from a campaign hub into Nydiamar's start region.
PORTAL_HUBS: Dict[str, Dict[str, str]] = {
    "devils_crossing": {
        "label": "Devil's Crossing",
        "notes": "Early-game hub; easiest for new Custom Game characters.",
        "suggested_region_hint": "devils crossing / lower crossing area in campaign world",
    },
    "homestead": {
        "label": "Homestead",
        "notes": "Act 2 hub; good mid-campaign stitch point.",
        "suggested_region_hint": "homestead town region",
    },
    "fort_ikon": {
        "label": "Fort Ikon",
        "notes": "AoM-era hub; useful if starting after base campaign.",
        "suggested_region_hint": "fort ikon / ugdenbog approach",
    },
    "malmouth": {
        "label": "Malmouth outskirts",
        "notes": "Late base/FG adjacent; heavier pathing risk.",
        "suggested_region_hint": "malmouth approach regions",
    },
    "asterkarn": {
        "label": "Asterkarn / FoA hub",
        "notes": "Fangs of Asterkarn entry; use if FoA progression is the primary path.",
        "suggested_region_hint": "FoA intro / Asterkarn hub region from gdx3 maps",
    },
}

# ARCs to unpack for Editor / Quest Editor / Asset Manager source layout
EDITOR_ARCS = (
    "Maps.arc",
    "Quests.arc",
    "Conversations.arc",
    "Scripts.arc",
    "Text_en.arc",
)


def normalize_portal_hub(name: Optional[str]) -> str:
    if not name:
        return "devils_crossing"
    key = name.strip().lower().replace(" ", "_").replace("-", "_").replace("'", "")
    aliases = {
        "dc": "devils_crossing",
        "devils": "devils_crossing",
        "devilscrossing": "devils_crossing",
        "ikon": "fort_ikon",
        "fortikon": "fort_ikon",
        "foa": "asterkarn",
        "fangs": "asterkarn",
    }
    key = aliases.get(key, key)
    if key not in PORTAL_HUBS:
        raise ValueError(
            f"Unknown portal hub '{name}'. Choose one of: {', '.join(PORTAL_HUBS)}"
        )
    return key


def extract_editor_arcs(
    tool: ArchiveTool,
    mod_root: Path,
    out_mod: Path,
    arc_names: Tuple[str, ...] = EDITOR_ARCS,
) -> List[str]:
    """
    Unpack selected resource ARCs into out_mod/source/ for Asset Manager.
    ArchiveTool already nests assets (quests/, conversations/, scripts/, text_en/).
    Returns list of extracted arc names.
    """
    extracted: List[str] = []
    res = mod_root / "resources"
    source = out_mod / "source"
    source.mkdir(parents=True, exist_ok=True)

    for name in arc_names:
        arc = res / name
        if not arc.is_file():
            continue
        print(f"Extracting {name} -> {source} ...")
        tool.extract_arc(arc, source)
        extracted.append(name)
    return extracted


def write_portal_stubs(out_mod: Path, hub_key: str, quest_prefix: str = "nydiamar") -> List[str]:
    """
    Create stub quest/conversation/NPC DBR placeholders for a portal stitch NPC.
    These are starting points for Quest Editor / World Editor — not a finished questline.
    """
    hub = PORTAL_HUBS[hub_key]
    written: List[str] = []
    qdir = out_mod / "database" / "records" / "quests" / quest_prefix / "portal"
    cdir = out_mod / "database" / "records" / "conversations" / quest_prefix / "portal"
    ndir = out_mod / "database" / "records" / "creatures" / "npcs" / quest_prefix
    for d in (qdir, cdir, ndir):
        d.mkdir(parents=True, exist_ok=True)

    # Campaign hub -> Nydiamar
    quest = qdir / "foa_to_nydiamar_portal.dbr"
    quest.write_text(
        "\n".join(
            [
                f"// Stub: portal from {hub['label']} (campaign World001) INTO Nydiamar",
                f"FileDescription,Travel to Nydiamar ({hub['label']}),",
                "Class,Quest,",
                f"questFileName,records/quests/{quest_prefix}/portal/foa_to_nydiamar_portal.dbr,",
                "// Characters MUST start on World001.map — never on nydiamar.map.",
                "// Nydiamar/Dungeons are portal destinations only.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    written.append(quest.relative_to(out_mod).as_posix())

    # Nydiamar -> campaign return
    quest_back = qdir / "nydiamar_to_foa_return_portal.dbr"
    quest_back.write_text(
        "\n".join(
            [
                f"// Stub: RETURN portal from Nydiamar back to campaign hub ({hub['label']})",
                f"FileDescription,Return to {hub['label']},",
                "Class,Quest,",
                f"questFileName,records/quests/{quest_prefix}/portal/nydiamar_to_foa_return_portal.dbr,",
                "// Place near Nydiamar start / hub; link to World001 hub region.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    written.append(quest_back.relative_to(out_mod).as_posix())

    conv = cdir / "portal_guide.dbr"
    conv.write_text(
        "\n".join(
            [
                f"// Stub conversation: {hub['label']} -> Nydiamar",
                "FileDescription,Nydiamar Portal Guide,",
                "Class,Conversation,",
                f"// Link NPC dialogue to quest records/quests/{quest_prefix}/portal/",
                "",
            ]
        ),
        encoding="utf-8",
    )
    written.append(conv.relative_to(out_mod).as_posix())

    conv_back = cdir / "return_guide.dbr"
    conv_back.write_text(
        "\n".join(
            [
                f"// Stub conversation: Nydiamar -> {hub['label']} (return)",
                "FileDescription,Return Portal Guide,",
                "Class,Conversation,",
                f"// Link to records/quests/{quest_prefix}/portal/nydiamar_to_foa_return_portal.dbr",
                "",
            ]
        ),
        encoding="utf-8",
    )
    written.append(conv_back.relative_to(out_mod).as_posix())

    npc = ndir / "nydiamar_portal_guide.dbr"
    npc.write_text(
        "\n".join(
            [
                f"// Stub NPC: place in CAMPAIGN World001 near {hub['label']}",
                "FileDescription,Nydiamar Portal Guide,",
                "Class,Creature,",
                f"conversationName,records/conversations/{quest_prefix}/portal/portal_guide.dbr,",
                "// Teleport target: Nydiamar start region (nydiamar.map) — not a new character start.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    written.append(npc.relative_to(out_mod).as_posix())

    npc_back = ndir / "campaign_return_guide.dbr"
    npc_back.write_text(
        "\n".join(
            [
                f"// Stub NPC: place in NYDIAMAR start/hub; return to {hub['label']} on World001",
                "FileDescription,Campaign Return Guide,",
                "Class,Creature,",
                f"conversationName,records/conversations/{quest_prefix}/portal/return_guide.dbr,",
                "",
            ]
        ),
        encoding="utf-8",
    )
    written.append(npc_back.relative_to(out_mod).as_posix())

    note = out_mod / "source" / "portal_hub.txt"
    note.parent.mkdir(parents=True, exist_ok=True)
    note.write_text(
        "\n".join(
            [
                f"portal_hub={hub_key}",
                f"label={hub['label']}",
                f"notes={hub['notes']}",
                f"region_hint={hub['suggested_region_hint']}",
                "start_map=World001.map (REQUIRED — do not start on nydiamar.map)",
                f"quest_to_nydiamar=records/quests/{quest_prefix}/portal/foa_to_nydiamar_portal.dbr",
                f"quest_return=records/quests/{quest_prefix}/portal/nydiamar_to_foa_return_portal.dbr",
                f"npc_to_nydiamar=records/creatures/npcs/{quest_prefix}/nydiamar_portal_guide.dbr",
                f"npc_return=records/creatures/npcs/{quest_prefix}/campaign_return_guide.dbr",
                "dungeons=portal from Nydiamar world only after arriving via hub portal",
                "",
            ]
        ),
        encoding="utf-8",
    )
    written.append(note.relative_to(out_mod).as_posix())
    return written


def write_editor_checklist(
    path: Path,
    *,
    out_mod: Path,
    game_editor: Path,
    game_quest_editor: Path,
    game_asset_manager: Path,
    hub_key: str,
    extracted_arcs: List[str],
    stub_files: List[str],
    quest_prefix: str = "nydiamar",
) -> None:
    hub = PORTAL_HUBS[hub_key]
    lines = [
        "# Nydiamar + FoA World Editor stitch checklist",
        "",
        "Goal: one **Custom Game** where the same character reaches FoA campaign areas",
        "and Nydiamar (stock Campaign saves are a different character pool).",
        "",
        f"- Output mod: `{out_mod}`",
        f"- Asset Manager: `{game_asset_manager}`",
        f"- World Editor: `{game_editor}`",
        f"- Quest Editor: `{game_quest_editor}`",
        f"- Portal hub: **{hub['label']}** (`{hub_key}`)",
        f"  - {hub['notes']}",
        f"  - Region hint: {hub['suggested_region_hint']}",
        "",
        "## Automated prep already done",
        "",
        "1. FoA/v1.3 database compatibility (Pass A + B)",
        f"2. Quest namespace under `records/quests/{quest_prefix}/`",
        "3. Berserker dual-class combo tags (or placeholders)",
        f"4. Extracted editor ARCs: {', '.join(extracted_arcs) if extracted_arcs else '(none — re-run with --prepare-editor-stitch)'}",
        "5. Portal stub records:",
        *[f"   - `{s}`" for s in stub_files],
        "",
        "## Start map (critical)",
        "",
        "- Custom Game entry: **`World001.map`** (FoA/campaign).",
        "- **Never** create characters on `nydiamar.map` / `nydiamardungeons.map`.",
        "- Nydiamar worlds remain in `Maps.arc` for portal travel only.",
        "",
        "## Preferred stitch pattern (bidirectional)",
        "",
        "1. Keep Nydiamar as its **own** world (`nydiamar.map`).",
        "2. Edit **campaign World001** only enough to add a portal/NPC at "
        f"**{hub['label']}** → Nydiamar start region.",
        "3. In **Nydiamar**, place a return portal/NPC → back to that campaign hub.",
        "4. Dungeons: use in-world portals inside Nydiamar after you arrive — not a start map.",
        "",
        "## Concrete steps for this install",
        "",
        "1. Asset Manager working dir = this mod; build `.arz` if needed.",
        "2. Confirm `resources/Levels.arc` contains `world001.map` (see PLAY_START.txt).",
        "3. World Editor: open **World001**; place `nydiamar_portal_guide` at the hub.",
        "4. World Editor: open **nydiamar**; place `campaign_return_guide` near start/hub.",
        "5. Quest Editor: wire "
        f"`foa_to_nydiamar_portal.dbr` and `nydiamar_to_foa_return_portal.dbr`.",
        "6. Build maps/quests; playtest: Custom Game → **World001** → hub portal →",
        "   Nydiamar → return portal → campaign hub.",
        "",
        "## Same-character note",
        "",
        "Characters in this Custom Game share FoA + portal-Nydiamar.",
        "They do **not** appear under Main Menu → Campaign.",
        "",
        "See also: `editor_stitch_checklist.md` in the tools folder.",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
