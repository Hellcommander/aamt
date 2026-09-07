#!/usr/bin/env python3
"""Produce Starbound item animation sheets from packed Unity stills via SD3.5 img2img.

Each still is the reference. SD generates idle / charge / fire / cooldown keyframes.
Frames are packed into a horizontal strip + .frames + .animation, then copied onto
the matching Magi-Tech .item files. Inventory icons stay single-frame.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PIL import Image

_TOOLS = Path(__file__).resolve().parent
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))
from sd_client import generate, ping, status, wait_until_up

# With T5 enabled (SD_SKIP_T5=0) prompts can use SD_MAX_SEQ_LEN (default 256).
# CLIP-only mode still truncates at 77 — start SD with T5 for longer text.
# Idle shutdown is intentional; ensure_sd() restarts the server when it's down.
NEGATIVE = (
    "text, watermark, logo, photo, blurry, cluttered background, ui chrome, "
    "different object, changed silhouette, extra limbs"
)
LAUNCH_CMD = Path(r"E:\tools\sd3.5\sd3.5\_sd_detached_launch.cmd")
START_SD_PS1 = Path(__file__).resolve().parent.parent / "Start-StableDiffusionServer.ps1"
PYTHON_CUDA = Path(r"E:\tools\miniconda3\python.exe")
SERVER_PY = Path(r"E:\tools\sd3.5\sd3.5\server.py")
PROMPT_MAX_TOKENS = 240  # under SD_MAX_SEQ_LEN=256 when T5 is loaded

SHEETS = Path("assets") / "magitech" / "unity_sheets"
GEN = Path("assets") / "magitech" / "generated"

# Idle keeps the HQ still; charge/fire only push glow/FX (still = ground truth).
KEYFRAMES = (
    ("idle", "idle, soft ambient glow only, preserve every detail of the reference still", 0.28),
    ("charging", "charging, brighter core glow and sparks, same object and materials", 0.48),
    ("fire", "firing, peak energy flash and discharge FX, same object silhouette", 0.62),
    ("cooldown", "cooldown, residual glow fading, same object as the reference", 0.40),
)

JOBS: List[Dict[str, str]] = [
    # still= + look= ground prompts in the high-quality Unity/generated still.
    {
        "id": "grenade_fire",
        "batch": "grenade",
        "theme": "incendiary pineapple grenade",
        "look": "brown segmented metal pineapple grenade, orange top fuse, painted game prop",
        "still": "assets/magitech/generated/grenade_fire/grenade_fire.png",
    },
    {
        "id": "grenade_frost",
        "batch": "grenade",
        "theme": "frost alchemical grenade flask",
        "look": "round glass flask, cyan crystal, brown cork, copper bands, ice-blue liquid",
    },
    {
        "id": "grenade_acid",
        "batch": "grenade",
        "theme": "acid alchemical grenade device",
        "look": "green-lit tech cylinder, copper pipes, gauge, toxic green chamber",
    },
    {
        "id": "grenade_storm",
        "batch": "grenade",
        "theme": "storm lightning grenade flask",
        "look": "brown flask device, yellow liquid vial, copper fittings, electric accents",
    },
    {
        "id": "grenade_shadow",
        "batch": "grenade",
        "theme": "shadow void grenade orb",
        "look": "dark metallic orb, orange core glow, rings and nozzles, void-tech bomb",
        "still": "assets/magitech/unity_sheets/grenade/chemicalgrenade.png",
    },
    {"id": "chemicalgrenadeammo", "batch": "grenade", "theme": "grenade ammo canister", "look": "metal ammo canister"},
    {"id": "chemicalgrenadeammo_mk2", "batch": "grenade", "theme": "mk2 grenade ammo", "look": "upgraded ammo canister"},
    {"id": "chemicalgrenadeammo_mk3", "batch": "grenade", "theme": "mk3 grenade ammo", "look": "advanced ammo canister"},
    {
        "id": "chemicalgrenadelauncher",
        "batch": "grenade",
        "theme": "alchemical grenade launcher",
        "look": "sci-fi grenade launcher gun, red chamber, metallic barrel, Magi-Tech firearm",
        "still": "assets/magitech/unity_sheets/grenade/grenade_shadow.png",
    },
    {
        "id": "chemicalgrenadelauncher_tech2",
        "batch": "grenade",
        "theme": "tech2 grenade launcher",
        "look": "upgraded sci-fi grenade launcher gun, red chamber, metallic barrel",
        "still": "assets/magitech/unity_sheets/grenade/grenade_shadow.png",
    },
    {
        "id": "chemicalgrenadelauncher_tech3",
        "batch": "grenade",
        "theme": "tech3 grenade launcher",
        "look": "advanced sci-fi grenade launcher gun, red chamber, metallic barrel",
        "still": "assets/magitech/unity_sheets/grenade/grenade_shadow.png",
    },
    {
        "id": "flamelord_grenadegun",
        "batch": "grenade",
        "theme": "flame lord grenade bomb",
        "look": "dark spherical bomb, green glowing seams, short nozzle, molten tech",
    },
    {"id": "grenade_15", "batch": "grenade", "theme": "empty reagent vial", "look": "clear glass vial", "alias": "reagent_vial"},
    {"id": "grenade_16", "batch": "grenade", "theme": "fire reagent vial", "look": "red-orange filled glass vial", "alias": "reagent_fireessence"},
    {"id": "grenade_17", "batch": "grenade", "theme": "ice reagent vial", "look": "blue ice crystal vial", "alias": "reagent_icecrystal"},
    {"id": "grenade_18", "batch": "grenade", "theme": "poison reagent vial", "look": "green poison vial", "alias": "reagent_poisoncloud"},
    {"id": "grenade_19", "batch": "grenade", "theme": "oil reagent vial", "look": "dark oil powder vial", "alias": "reagent_oilpowder"},
    {"id": "grenade_20", "batch": "grenade", "theme": "catalyst reagent vial", "look": "sparkling catalyst vial", "alias": "reagent_catalyst"},
    {
        "id": "magitechbasicwand",
        "batch": "weapon",
        "theme": "magitech wand",
        "look": "wooden torch-wand, leather wrap, blazing orange crystal tip",
    },
    {
        "id": "magitechbasicstaff",
        "batch": "weapon",
        "theme": "magitech staff",
        "look": "dark wooden staff, leather grip, blue crystal head, gold fittings",
    },
    {
        "id": "magitechbasicorb",
        "batch": "weapon",
        "theme": "magitech dagger focus",
        "look": "dark dagger, orange gem pommel, gold filigree, Magi-Tech ritual blade",
    },
    {
        "id": "magitechdevice",
        "batch": "weapon",
        "theme": "magitech arcane device",
        "look": "handheld multi-pronged arcane device, warm metal, glowing core",
    },
    {"id": "deviceworkbench", "batch": "station", "theme": "device workbench", "look": "magitech crafting workbench"},
    {"id": "magitechspellcraftingstation", "batch": "station", "theme": "spell crafting station", "look": "crystal spell crafting station"},
    {"id": "spellstone_fire", "batch": "spellstone", "theme": "fire spellstone", "look": "fire crystal spellstone"},
    {"id": "spellstone_ice", "batch": "spellstone", "theme": "ice spellstone", "look": "ice crystal spellstone"},
    {"id": "spellstone_electric", "batch": "spellstone", "theme": "lightning spellstone", "look": "lightning crystal spellstone"},
    {"id": "spellstone_core_common", "batch": "spellstone", "theme": "common spellstone core", "look": "common arcane spellstone"},
    {"id": "mana_crystal", "batch": "ingredient", "theme": "mana crystal", "look": "blue mana crystal"},
    {"id": "fire_ruby", "batch": "ingredient", "theme": "fire ruby", "look": "red fire ruby gem", "alias": "fire_essence"},
    {"id": "magitech_berserker_core", "batch": "minion", "theme": "berserker minion core", "look": "berserker core relic"},
]

INSTALL_FOLDERS = {
    "grenade_fire": "items/ammo/specializedgrenades",
    "grenade_frost": "items/ammo/specializedgrenades",
    "grenade_acid": "items/ammo/specializedgrenades",
    "grenade_storm": "items/ammo/specializedgrenades",
    "grenade_shadow": "items/ammo/specializedgrenades",
    "chemicalgrenadeammo": "items/ammo/chemicalgrenadeammo",
    "chemicalgrenadeammo_mk2": "items/ammo/chemicalgrenadeammo",
    "chemicalgrenadeammo_mk3": "items/ammo/chemicalgrenadeammo",
    "chemicalgrenadelauncher": "items/weapons/alchemicalgrenadelauncher",
    "chemicalgrenadelauncher_tech2": "items/weapons/alchemicalgrenadelauncher",
    "chemicalgrenadelauncher_tech3": "items/weapons/alchemicalgrenadelauncher",
    "flamelord_grenadegun": "items/weapons/alchemicalgrenadelauncher",
    "reagent_vial": "items/consumable/reagents",
    "reagent_fireessence": "items/consumable/reagents",
    "reagent_icecrystal": "items/consumable/reagents",
    "reagent_poisoncloud": "items/consumable/reagents",
    "reagent_oilpowder": "items/consumable/reagents",
    "reagent_catalyst": "items/consumable/reagents",
    "magitechbasicwand": "items/active/weapons/wand",
    "magitechbasicstaff": "items/active/weapons/staff",
    "magitechbasicorb": "items/active/weapons/orb",
    "magitechdevice": "items/active/weapons/magitech",
    "deviceworkbench": "objects/magitech/deviceworkbench",
    "magitechspellcraftingstation": "objects/magitech",
    "spellstone_fire": "items/spellstones",
    "spellstone_ice": "items/spellstones",
    "spellstone_electric": "items/spellstones",
    "spellstone_core_common": "items/spellstones",
    "fire_essence": "items/materials/spellcrafting",
    "mana_crystal": "items/materials/spellcrafting",
    "magitech_berserker_core": "items/magitech/minion_enhancements",
}


def ensure_sd(wait_sec: int = 300) -> None:
    """Start SD if idle-shutdown stopped it; wait until /ping answers (threaded server)."""
    st = status(timeout=10.0)
    if st.get("status") == "ok":
        print(
            f"[OK] SD up version={st.get('version')} loaded={st.get('loaded')} "
            f"loading={st.get('loading')} threaded={st.get('threaded')} "
            f"max_seq={st.get('max_sequence_length')}"
        )
        if st.get("loaded"):
            return
        print("[..] waiting for model preload (threaded /ping stays up)...")
        if wait_until_up(wait_sec=wait_sec, want_loaded=True):
            return
        raise SystemExit("SD answered /ping but model never finished loading")
    print("[..] SD down or idle-stopped — starting server (T5 + threaded ping)")
    os.environ["SD_IDLE_SHUTDOWN_SEC"] = "0"
    os.environ["SD_OFFLOAD"] = "gpu"
    os.environ["SD_SKIP_T5"] = "0"
    os.environ["SD_ALLOW_T5_RAM"] = "1"
    os.environ["SD_MAX_SEQ_LEN"] = "256"
    os.environ["SD_HEADROOM_GB"] = "0"
    if START_SD_PS1.is_file():
        subprocess.Popen(
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(START_SD_PS1),
                "-Force",
                "-WaitSec",
                "30",
                "-NoStatusGui",
            ],
            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            | getattr(subprocess, "DETACHED_PROCESS", 0),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    elif LAUNCH_CMD.exists():
        subprocess.Popen(
            ["cmd.exe", "/c", str(LAUNCH_CMD)],
            cwd=str(LAUNCH_CMD.parent),
            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            | getattr(subprocess, "DETACHED_PROCESS", 0),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    elif SERVER_PY.exists() and PYTHON_CUDA.exists():
        subprocess.Popen(
            [str(PYTHON_CUDA), str(SERVER_PY), "--host", "localhost", "--port", "1338"],
            cwd=str(SERVER_PY.parent),
            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            | getattr(subprocess, "DETACHED_PROCESS", 0),
        )
    else:
        raise SystemExit("SD launch files missing (Start-StableDiffusionServer.ps1 / E:\\tools\\sd3.5)")
    if wait_until_up(wait_sec=wait_sec, want_loaded=False):
        st = status(timeout=10.0)
        print(f"[OK] SD server is up version={st.get('version')} loading={st.get('loading')}")
        # First generate may still be loading T5; wait a bit for loaded when possible.
        wait_until_up(wait_sec=min(240, wait_sec), want_loaded=True)
        return
    raise SystemExit("SD server did not answer /ping after start")


def _clip_prompt(text: str, max_tokens: int = PROMPT_MAX_TOKENS) -> str:
    """Soft-cap whitespace tokens (T5 path ~256; keep under SD_MAX_SEQ_LEN)."""
    parts = text.replace(",", " ").split()
    if len(parts) <= max_tokens:
        return " ".join(parts)
    return " ".join(parts[:max_tokens])


def prompt_for(theme: str, pose: str, look: str = "") -> str:
    """Prompt grounded in the HQ still. Important words first (CLIP still reads only ~77)."""
    look_bit = f"{look}. " if look else ""
    return _clip_prompt(
        f"{theme}. {look_bit}{pose}. Magi-Tech Starbound sprite. "
        f"Keep reference silhouette materials colors. Only change glow FX. "
        f"Transparent background centered."
    )


def resolve_still(mod: Path, job: Dict[str, str]) -> Optional[Path]:
    """Pick the best reference PNG (explicit still= wins; else packed Unity still)."""
    if job.get("still"):
        cand = mod / job["still"]
        if cand.is_file():
            return cand
    packed_id = job["id"]
    cand = mod / SHEETS / job["batch"] / f"{packed_id}.png"
    if cand.is_file():
        return cand
    asset_id = job.get("alias") or packed_id
    for rel in (
        GEN / asset_id / f"{asset_id}.png",
        Path(INSTALL_FOLDERS.get(asset_id, "")) / f"{asset_id}.png" if asset_id in INSTALL_FOLDERS else None,
    ):
        if rel is None:
            continue
        p = mod / rel if not rel.is_absolute() else rel
        if p.is_file():
            return p
    return None


def pack_strip(frames: List[Path], dest: Path, tile: int) -> None:
    tiles = []
    for p in frames:
        im = Image.open(p).convert("RGBA")
        if im.size != (tile, tile):
            im = im.resize((tile, tile), Image.Resampling.LANCZOS)
        tiles.append(im)
    sheet = Image.new("RGBA", (tile * len(tiles), tile), (0, 0, 0, 0))
    for i, im in enumerate(tiles):
        sheet.paste(im, (i * tile, 0))
    dest.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(dest)
    names = [k[0] for k in KEYFRAMES]
    frames_json = {
        "frameGrid": {
            "size": [tile, tile],
            "dimensions": [len(names), 1],
            "names": [names],
        },
        "aliases": {"default": names[0], "idle": names[0]},
    }
    dest.with_suffix(".frames").write_text(json.dumps(frames_json, indent=2) + "\n", encoding="utf-8")


def write_animation(dest: Path, sheet_name: str, parts: List[str]) -> None:
    img = lambda tag: f"{sheet_name}:{tag}"
    part_template = {
        "properties": {
            "zLevel": 0,
            "centered": True,
            "image": img("idle"),
            "transformationGroups": ["weapon"],
        },
        "partStates": {
            "charge": {
                "idle": {"properties": {"image": img("idle")}},
                "charge": {"properties": {"image": img("charging")}},
                "spark": {"properties": {"image": img("charging")}},
                "charged": {"properties": {"image": img("charging")}},
                "discharge": {"properties": {"image": img("cooldown")}},
            },
            "weapon": {
                "idle": {"properties": {"image": img("idle")}},
                "fire": {"properties": {"image": img("fire")}},
                "cooldown": {"properties": {"image": img("cooldown")}},
                "altFire": {"properties": {"image": img("fire")}},
            },
        },
    }
    anim = {
        "animatedParts": {
            "stateTypes": {
                "charge": {
                    "default": "idle",
                    "states": {
                        "idle": {},
                        "charge": {"frames": 1, "cycle": 0.9, "mode": "transition", "transition": "spark"},
                        "spark": {"frames": 1, "cycle": 0.3, "mode": "transition", "transition": "charged"},
                        "charged": {"frames": 1, "cycle": 0.5, "mode": "loop"},
                        "discharge": {"frames": 1, "cycle": 0.3, "mode": "transition", "transition": "idle"},
                    },
                },
                "weapon": {
                    "default": "idle",
                    "states": {
                        "idle": {"frames": 1, "cycle": 1.2, "mode": "loop"},
                        "fire": {"frames": 1, "cycle": 0.25, "mode": "transition", "transition": "cooldown"},
                        "cooldown": {"frames": 1, "cycle": 0.4, "mode": "transition", "transition": "idle"},
                        "altFire": {"frames": 1, "cycle": 0.28, "mode": "transition", "transition": "cooldown"},
                    },
                },
            },
            "parts": {name: json.loads(json.dumps(part_template)) for name in parts},
        },
        "transformationGroups": {"weapon": {}},
    }
    dest.write_text(json.dumps(anim, indent=2) + "\n", encoding="utf-8")


def patch_item(item: Path, sheet_name: str, anim_name: str) -> None:
    try:
        data = json.loads(item.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return
    parts = data.get("animationParts")
    if isinstance(parts, dict) and parts:
        data["animationParts"] = {k: sheet_name for k in parts}
    else:
        data["animationParts"] = {"weapon": sheet_name}
    data["animation"] = anim_name
    if "inventoryIcon" in data:
        data["inventoryIcon"] = f"{item.stem}.png"
    item.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def install(mod: Path, asset_id: str, out: Path) -> None:
    rel = INSTALL_FOLDERS.get(asset_id)
    if not rel:
        return
    dest = mod / rel
    dest.mkdir(parents=True, exist_ok=True)
    for name in (
        f"{asset_id}.png",
        f"{asset_id}_sheet.png",
        f"{asset_id}_sheet.frames",
        f"{asset_id}.animation",
        f"{asset_id}.frames",
    ):
        src = out / name
        if src.exists():
            shutil.copy2(src, dest / name)
    item = dest / f"{asset_id}.item"
    if not item.exists():
        item = dest / f"{asset_id}.activeitem"
    if item.exists():
        parts = ["weapon"]
        try:
            existing = json.loads(item.read_text(encoding="utf-8")).get("animationParts") or {}
            if isinstance(existing, dict) and existing:
                parts = list(existing.keys())
        except json.JSONDecodeError:
            pass
        write_animation(dest / f"{asset_id}.animation", f"{asset_id}_sheet.png", parts)
        patch_item(item, f"{asset_id}_sheet.png", f"{asset_id}.animation")
        print(f"  installed -> {dest.relative_to(mod)}")


def _is_sd_connection_error(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return any(
        s in msg
        for s in (
            "10054",
            "10061",
            "actively refused",
            "forcibly closed",
            "connection reset",
            "connection aborted",
            "remotely closed",
            "urlopen error",
        )
    )


def produce_one(mod: Path, job: Dict[str, str], tile: int, skip_existing: bool) -> bool:
    packed_id = job["id"]
    asset_id = job.get("alias") or packed_id
    still = resolve_still(mod, job)
    if not still:
        print(f"  [SKIP] no still {packed_id}")
        return False
    out = mod / GEN / asset_id
    sheet = out / f"{asset_id}_sheet.png"
    if skip_existing and sheet.exists():
        print(f"  [SKIP] existing {asset_id}")
        install(mod, asset_id, out)
        return True
    out.mkdir(parents=True, exist_ok=True)
    (out / "Source").mkdir(parents=True, exist_ok=True)
    shutil.copy2(still, out / "Source" / "reference.png")
    try:
        ref_disp = still.relative_to(mod)
    except ValueError:
        ref_disp = still
    print(f"    ref={ref_disp}")
    frame_dir = out / "Source" / "frames"
    frame_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, pose, strength in KEYFRAMES:
        dest = frame_dir / f"{name}.png"
        print(f"    SD {asset_id}:{name} strength={strength}")
        attempts = 0
        while True:
            attempts += 1
            try:
                generate(
                    prompt_for(job["theme"], pose, job.get("look") or ""),
                    dest,
                    negative=NEGATIVE,
                    reference=still,
                    strength=float(strength),
                    width=512,
                    height=512,
                    steps=28,
                    max_sequence_length=256,
                )
                break
            except Exception as exc:
                if attempts >= 3 or not _is_sd_connection_error(exc):
                    raise
                print(f"    [warn] SD connection lost ({exc}); restarting server...")
                ensure_sd(wait_sec=300)
        tile_path = frame_dir / f"{name}_{tile}.png"
        im = Image.open(dest).convert("RGBA").resize((tile, tile), Image.Resampling.LANCZOS)
        im.save(tile_path)
        paths.append(tile_path)
    # Inventory icon = idle keyframe (not a mislabeled Unity still).
    shutil.copy2(paths[0], out / f"{asset_id}.png")
    pack_strip(paths, sheet, tile)
    write_animation(out / f"{asset_id}.animation", f"{asset_id}_sheet.png", ["weapon"])
    install(mod, asset_id, out)
    print(f"  [OK] {asset_id}")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="SD-produce Magi-Tech item animation sheets")
    ap.add_argument("--mod-path", default=r"F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery")
    ap.add_argument("--tile", type=int, default=64)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--ids", default="", help="Comma asset ids (alias or packed id)")
    ap.add_argument("--skip-existing", action="store_true")
    ap.add_argument("--no-start-sd", action="store_true")
    ap.add_argument(
        "--backend",
        choices=("sd", "pixelorama"),
        default="sd",
        help="sd = SD3.5 img2img keyframes from Unity stills; pixelorama = headless .pxo export",
    )
    args = ap.parse_args()
    if args.backend == "pixelorama":
        from produce_pixelorama_sheets import main as px_main

        forwarded = ["--mod-path", str(args.mod_path), "--tile", str(args.tile)]
        if args.ids:
            forwarded += ["--ids", args.ids]
        if args.limit:
            forwarded += ["--limit", str(args.limit)]
        if args.skip_existing:
            forwarded.append("--skip-existing")
        return px_main(forwarded)
    mod = Path(args.mod_path)
    jobs = JOBS
    if args.ids:
        want = {x.strip() for x in args.ids.split(",") if x.strip()}
        jobs = [j for j in JOBS if j["id"] in want or j.get("alias") in want]
    if args.limit:
        jobs = jobs[: args.limit]
    # Idle shutdown turns SD off on purpose — always restart unless explicitly disabled.
    if args.no_start_sd:
        if not ping(timeout=10.0):
            raise SystemExit("SD server is down; omit --no-start-sd so it can auto-start")
    else:
        ensure_sd()
    ok = fail = 0
    for job in jobs:
        print(f"-- {job.get('alias') or job['id']}")
        try:
            if produce_one(mod, job, args.tile, args.skip_existing):
                ok += 1
            else:
                fail += 1
        except Exception as exc:
            fail += 1
            print(f"  [FAIL] {exc}")
    print(f"[DONE] ok={ok} fail={fail} backend=sd")
    return 0 if ok or not fail else 1


if __name__ == "__main__":
    raise SystemExit(main())
