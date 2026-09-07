"""Salvage SD output from server cache and finalize water magic thumbnail."""
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, r"D:\games\Steam\steamapps\common\Transcendence\Tools\Soulash2")
sys.path.insert(0, r"D:\games\Steam\steamapps\common\Transcendence\Tools\Shared")

from PIL import Image
from hydromancy_quality import finalize_thumbnail_from_sd, validate_thumbnail, score_palette_match

MOD = Path(r"E:\SteamLibrary\steamapps\common\Soulash 2\data\mods\arendeth_water_magic")
DRAFTS = MOD / "DesignDrafts"
DRAFT = DRAFTS / "thumbnail_design_draft.png"
OUT = MOD / "thumbnail2.png"
SERVER_LATEST = Path(r"E:\tools\sd3.5\sd3.5\outputs\latest.png")
PALETTE = ["#0a1628", "#0d3d56", "#1a6b8a", "#3eb8d4", "#a8e6f0", "#ffffff"]

DRAFTS.mkdir(parents=True, exist_ok=True)
if not SERVER_LATEST.exists():
    raise SystemExit(f"Missing server output: {SERVER_LATEST}")

# Backup current procedural thumbnail before replacing
backup_dir = MOD / "asset_backups" / time.strftime("%Y%m%d_%H%M%S")
if OUT.exists():
    backup_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(OUT, backup_dir / "thumbnail2.png")
    print(f"Backed up prior thumbnail to {backup_dir}")

shutil.copy2(SERVER_LATEST, DRAFT)
print(f"Salvaged SD draft: {SERVER_LATEST} -> {DRAFT} ({DRAFT.stat().st_size} bytes)")

with Image.open(DRAFT) as src:
    print(f"Draft size: {src.size}")
    thumb = finalize_thumbnail_from_sd(src.copy())
    ok, reason = validate_thumbnail(thumb)
    pal = score_palette_match(thumb, PALETTE)
    thumb.save(OUT)
    print(f"Finalized thumbnail2.png: {OUT.stat().st_size} bytes, mech={'PASS' if ok else 'FAIL'} ({reason}), palette={pal:.3f}")

if not ok:
    raise SystemExit(1)
print("OK")
