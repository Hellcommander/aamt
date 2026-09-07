#!/usr/bin/env python3
"""Build and install OSF UI settings pages and in-game views for the local mods."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import osfui_gen as gen

DATA = Path(r"F:\SteamLibrary\steamapps\common\Starfield\Data")
PLUGINS = DATA / "SFSE" / "Plugins"
SPECS = Path(__file__).resolve().parent / "specs"

ARCANE_VIEW = {
    "name": "conduit",
    "title": "Arcane Conduit",
    "description": "Essence, constructs, and live spell state.",
    "hub": True,
    "sections": [
        {
            "title": "Essence",
            "rows": [
                {
                    "kind": "bar",
                    "label": "Essence",
                    "data": "essence",
                    "maxData": "maxEssence",
                    "sample": 72,
                    "maxSample": 100,
                    "format": {"decimals": 0},
                },
                {
                    "kind": "stat",
                    "label": "Regen",
                    "data": "regen",
                    "sample": 0.0,
                    "format": {"suffix": " /s", "decimals": 1},
                },
            ],
        },
        {
            "title": "Field",
            "rows": [
                {"kind": "stat", "label": "Bloom orbs", "data": "bloomCount", "sample": 2},
                {"kind": "stat", "label": "Constructs", "data": "constructCount", "sample": 1},
                {
                    "kind": "bar",
                    "label": "Overheat",
                    "data": "overheat",
                    "max": 1,
                    "sample": 0.35,
                    "format": {"scale": 100, "decimals": 0, "suffix": "%"},
                },
            ],
        },
        {
            "title": "Controls",
            "rows": [
                {"kind": "toggle", "label": "Enabled", "setting": "General.Enabled"},
                {"kind": "toggle", "label": "Verbose log", "setting": "General.Verbose"},
                {
                    "kind": "button",
                    "label": "Dump constructs",
                    "action": "dumpConstructs",
                    "variant": "ghost",
                },
            ],
        },
    ],
}

HEX_VIEW = {
    "name": "grid",
    "title": "Spell Grid",
    "description": "Triangle hex: one spell docked on the north edge, mods and triggers on the vertices.",
    "custom": True,
    "hub": True,
    "width": 1600,
    "height": 900,
    "sections": [
        {
            "title": "Hex",
            "rows": [{"kind": "text", "text": "Custom hex board."}],
        }
    ],
}

TEMPLATES_VIEW = {
    "name": "templates",
    "title": "Spell Templates",
    "description": "Mod and personal loadouts. Preview the eight banks, then apply, save, rename, or delete.",
    "custom": True,
    "hub": True,
    "width": 1600,
    "height": 900,
    "sections": [
        {
            "title": "Templates",
            "rows": [{"kind": "text", "text": "Custom template browser."}],
        }
    ],
}

SFMAG_VIEW = {
    "name": "status",
    "title": "SFMAG",
    "description": "Needs, garment load, and accident controls.",
    "hub": True,
    "sections": [
        {
            "title": "Needs",
            "rows": [
                {
                    "kind": "bar",
                    "label": "Bladder",
                    "data": "bladder",
                    "max": 1,
                    "sample": 0.42,
                    "format": {"scale": 100, "decimals": 0, "suffix": "%"},
                },
                {
                    "kind": "bar",
                    "label": "Bowel",
                    "data": "bowel",
                    "max": 1,
                    "sample": 0.18,
                    "format": {"scale": 100, "decimals": 0, "suffix": "%"},
                },
            ],
        },
        {
            "title": "Garment",
            "rows": [
                {"kind": "toggle", "label": "Enable MAG / diapers", "setting": "Garment.EnableGarments"},
                {"kind": "toggle", "label": "Auto MAG in space", "setting": "Garment.AutoWearVirtualMAGInSpace"},
                {"kind": "select", "label": "Flavor", "setting": "General.Flavor",
                 "options": ["space", "casual"], "optionLabels": ["Space", "Casual"]},
            ],
        },
    ],
}

ECHO_VIEW = {
    "name": "intercept",
    "title": "Echo Intercept",
    "description": "Missile intercept orbs.",
    "hub": True,
    "sections": [
        {
            "title": "Intercept",
            "rows": [
                {"kind": "toggle", "label": "Enabled", "setting": "General.Enabled"},
                {"kind": "stat", "label": "Live intercepts", "data": "liveIntercepts", "sample": 1},
                {
                    "kind": "slider",
                    "label": "Max concurrent",
                    "setting": "Detection.MaxConcurrentIntercepts",
                    "min": 1,
                    "max": 16,
                    "step": 1,
                },
            ],
        },
    ],
}

MAD_VIEW = {
    "name": "extras",
    "title": "Mad Science",
    "description": "Threading, diagnostics, and Data folder watcher.",
    "hub": True,
    "sections": [
        {
            "title": "Threading",
            "rows": [
                {"kind": "toggle", "label": "Worker threads", "setting": "Threading.Enabled"},
                {
                    "kind": "slider",
                    "label": "Worker count",
                    "hint": "0 leaves one core for the game.",
                    "setting": "Threading.WorkerThreadCount",
                    "min": 0,
                    "max": 8,
                    "step": 1,
                },
            ],
        },
        {
            "title": "Diagnostics",
            "rows": [
                {"kind": "toggle", "label": "Record diagnostics", "setting": "RecordDiagnostics.Enabled"},
                {"kind": "toggle", "label": "Data folder watcher", "setting": "FileChangeNotify.Enabled"},
                {
                    "kind": "text",
                    "text": "AOB engine patches stay off unless you turn General.Enabled on. Leave that off if Engine Fixes is installed.",
                },
            ],
        },
    ],
}

SHIP_VIEW = {
    "name": "arsenal",
    "title": "Ship Weapon Powers",
    "description": "Starborn ship arsenal casts.",
    "hub": True,
    "sections": [
        {
            "title": "Casting",
            "rows": [
                {
                    "kind": "toggle",
                    "label": "Weapon Starborn casting",
                    "setting": "General.EnableWeaponStarbornCasting",
                },
                {"kind": "toggle", "label": "Replace normal fire", "setting": "General.ReplaceNormalFire"},
                {"kind": "toggle", "label": "Drain essence", "setting": "General.DrainEssence"},
            ],
        },
    ],
}

MODS = [
    {
        "ini": "ArcaneConduit.ini",
        "mod_id": "arendeth.arcane-conduit",
        "title": "Arcane Conduit",
        "description": "Arcane Essence reservoir and spell grid.",
        "accent": "#7B5CFF",
        "views": [ARCANE_VIEW, HEX_VIEW, TEMPLATES_VIEW],
    },
    {
        "ini": "SFMAG.ini",
        "mod_id": "arendeth.sfmag",
        "title": "SFMAG",
        "description": "Maximum Absorbency Garment simulation.",
        "accent": "#4AA3C7",
        "views": [SFMAG_VIEW],
    },
    {
        "ini": "EchoIntercept.ini",
        "mod_id": "arendeth.echo-intercept",
        "title": "Echo Intercept",
        "description": "Conjured missile intercept.",
        "accent": "#5CE1E6",
        "views": [ECHO_VIEW],
    },
    {
        "ini": "MadScience.ini",
        "mod_id": "arendeth.mad-science",
        "title": "Mad Science",
        "description": "Shared engine extras for the magic collection.",
        "accent": "#E07A3D",
        "views": [MAD_VIEW],
    },
    {
        "ini": "ShipWeaponPowers.ini",
        "mod_id": "arendeth.ship-weapon-powers",
        "title": "Ship Weapon Powers",
        "description": "Starborn ship arsenal.",
        "accent": "#D4A017",
        "views": [SHIP_VIEW],
    },
]


def _patch_arcane_template_keys(spec: dict) -> None:
    if spec.get("modId") != "arendeth.arcane-conduit":
        return
    groups = spec.setdefault("settings", {}).setdefault("groups", [])
    # Combat apply keys are native Input steals from the INI; OSF cannot consume
    # them, so keep F10 from showing raw uKey integers.
    groups[:] = [g for g in groups if g.get("id") != "templatehotkeys"]
    if any(g.get("id") == "templates" for g in groups):
        return
    insert_at = 1
    for i, group in enumerate(groups):
        if group.get("id") == "general":
            insert_at = i + 1
            break
    groups.insert(
        insert_at,
        {
            "id": "templates",
            "label": "Templates",
            "settings": [
                {
                    "key": "Templates.OpenKey",
                    "label": "Open templates",
                    "type": "key",
                    "default": "F8",
                    "hint": "Opens the template list. Apply, save, rename, delete, or bind F2–F4/F6 combat loadouts without the console.",
                },
                {
                    "key": "Templates.OpenGridKey",
                    "label": "Open spell grid",
                    "type": "key",
                    "default": "F7",
                    "hint": "Opens the hex spell grid.",
                },
            ],
        },
    )


def _patch_enums(spec: dict) -> None:
    for group in spec.get("settings", {}).get("groups", []):
        for setting in group.get("settings", []):
            if setting.get("key") == "General.Flavor":
                setting["type"] = "enum"
                setting["options"] = ["space", "casual"]
                setting["optionLabels"] = ["Space", "Casual"]
                setting.pop("maxLength", None)
            if setting.get("key") == "Garment.DefaultClass":
                setting["type"] = "enum"
                setting["options"] = ["Light", "Standard", "Overnight", "EvaMax", "Hybrid"]
                setting.pop("maxLength", None)


def rune_catalog(ini: Path) -> dict:
    wanted = {"Spells": "form", "Modifiers": "modifier", "Triggers": "trigger", "Elements": "element"}
    out = {v: [] for v in wanted.values()}
    for section in gen.parse_ini(ini):
        bucket = wanted.get(section["section"])
        if not bucket:
            continue
        for entry in section["keys"]:
            name, _ = gen._split_ini_key(entry["key"])
            out[bucket].append(name)
    return out


def write_grid_catalog(mod: dict, dest_dir: Path) -> None:
    if mod["mod_id"] != "arendeth.arcane-conduit":
        return
    catalog = rune_catalog(PLUGINS / mod["ini"])
    dest = dest_dir / "catalog.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"       catalog {len(catalog['form'])} spells, {len(catalog['modifier'])} mods, {len(catalog['trigger'])} triggers")


def build_spec(mod: dict) -> dict:
    ini = PLUGINS / mod["ini"]
    if not ini.exists():
        raise FileNotFoundError(ini)
    spec = gen.spec_from_ini(
        ini,
        mod["mod_id"],
        mod["title"],
        description=mod["description"],
        accent=mod.get("accent"),
        ini_relpath=f"SFSE/Plugins/{mod['ini']}",
    )
    _patch_enums(spec)
    _patch_arcane_template_keys(spec)
    spec["views"] = mod.get("views") or []
    return spec


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate OSF UI pages for local Starfield mods.")
    parser.add_argument("--data", type=Path, default=DATA)
    parser.add_argument("--install", action="store_true", help="write into the game Data folder")
    parser.add_argument("--preview", action="store_true", help="stage browser previews")
    args = parser.parse_args()

    SPECS.mkdir(parents=True, exist_ok=True)
    status = 0
    for mod in MODS:
        spec = build_spec(mod)
        problems = gen.validate_spec(spec)
        spec_path = SPECS / f"{mod['mod_id']}.json"
        spec_path.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        count = sum(len(g["settings"]) for g in spec["settings"]["groups"])
        if problems:
            print(f"[fail] {mod['mod_id']}: {len(problems)} problem(s)")
            for problem in problems[:12]:
                print(f"       {problem}")
            if len(problems) > 12:
                print(f"       ... {len(problems) - 12} more")
            status = 2
            continue
        print(f"[ok]   {spec_path.name}: {len(spec['settings']['groups'])} groups, {count} settings, {len(spec['views'])} view(s)")
        if args.install:
            written = gen.emit(spec, args.data, for_install=True)
            print(f"       installed {len(written)} file(s)")
            write_grid_catalog(
                mod,
                args.data / "SFSE" / "Plugins" / "OSFUI" / "views" / mod["mod_id"] / "grid",
            )
        if args.preview:
            preview_root = Path(__file__).resolve().parent / "build" / "preview"
            for view in spec.get("views", []):
                if view.get("custom"):
                    dest = preview_root / "views" / spec["modId"] / view["name"]
                    src = Path(__file__).resolve().parent / "custom-views" / spec["modId"] / view["name"]
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copytree(src, dest, dirs_exist_ok=True)
                    write_grid_catalog(mod, dest)
                    shared_src = DATA / "SFSE" / "Plugins" / "OSFUI" / "views" / "shared"
                    shared_dst = preview_root / "shared"
                    if shared_src.is_dir():
                        shutil.copytree(shared_src, shared_dst, dirs_exist_ok=True)
                    pad = DATA / "SFSE" / "Plugins" / "OSFUI" / "views" / "osfui" / "padnav.js"
                    if pad.exists():
                        shutil.copy2(pad, dest.parent / "padnav.js")
                    print(f"       preview {dest / 'index.html'}")
                else:
                    index = gen.build_preview(spec, view, preview_root)
                    print(f"       preview {index}")
    return status


if __name__ == "__main__":
    sys.exit(main())
