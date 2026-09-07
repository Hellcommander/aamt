# Elemental Reforged — Monster Race Asset Tools (AAMT)

**Policy: reuse original game art.** Clothes/armor/weapons point at real LH/Reforged HKB meshes and textures. Icons are resized from original medallions/cards. SD/Ollama are optional polish only — they do **not** invent meshes or replace game textures.

## What each item uses

| Field | Source |
|-------|--------|
| `ModelFile` | Original race/weapon `.hkb` (e.g. `M_Darkling_Armored_Mesh_01.hkb`) |
| `Texture_*` | Original race/weapon texture (e.g. `M_Darkling_Texture_01.dds`) |
| Item icon | Original `Gfx/Medallions/*_Card.png` (or weapon icon), resized to 128² |
| `Source/*_Original.*` | Copied originals for reference |

## Commands

```powershell
cd "D:\games\Steam\steamapps\common\Transcendence\Tools\ElementalReforged"

python monster_race_tool.py doctor
python monster_race_tool.py generate --all --mode tools --install
python monster_race_tool.py harden-units --strict
# Mesh-matches all Generic_Sovereign_* / Sovereign_LHL_* skel/anim/cutscene.
# Pose morphs (Darkling, Assassin Demon, Golem, Ogre/Troll, SpiderMan) keep UnitModelType + ClothPoseIndex.
# Beast/elemental leaders strip UMT so Create Sovereign idle uses the correct AnimationPack.
python monster_race_tool.py validate
python monster_race_tool.py check-meshes
```

AI (optional — icons only, and only with `--force-ai`):

```powershell
python monster_race_tool.py generate --race Darkling --mode both --force-ai --install
```

Mod Manager banner (local SD/Ollama — no Cursor credits, no hosted filters).
Quality path: **768×640 @ 40 steps / CFG 7.5** → Lanczos+unsharp downscale to workshop **512×439**.
(Right-sized ~1.5× supersample; the old 1344×1152 wasted ~3× the generation
time for no visible gain after downscale. Configure via `modPackage.genWidth`/`genHeight`.)

```powershell
python monster_race_tool.py banner --start-sd --install --force
python monster_race_tool.py banner --start-sd --install --force --sd-steps 50 --guidance 8
.\MonsterRaceAssetGenerator.ps1 -BannerOnly -InstallToMod -StartSD -Force
```

PowerShell:

```powershell
.\MonsterRaceAssetGenerator.ps1 -Race All -Mode Tools -InstallToMod
.\MonsterRaceAssetGenerator.ps1 -Race All -Mode Tools -InstallToMod -Banner
```

## Modes

| Mode | Behavior |
|------|----------|
| `tools` | Copy/resize originals → XML + icons (default / recommended) |
| `both` | Same as tools; SD skipped unless `--force-ai` |
| `ai` + `--force-ai` | May overlay SD on **icons only**; XML textures stay original |

## Race-fit visuals without modeling

Reforged meshes are `Havok-7.1.0-r1` packfiles (in `gamedata*.dat`). There is **no
AI/script that authors new game-ready skinned meshes** — that needs a manual
Softimage/HCT session. So the tool produces race-fitting clothes/armor by:

1. **Reusing the game's own meshes** already skinned to each race's skeleton.
   Monster races animate on a few shared skeletons (Wraith / Darkling /
   Juggernaut), so meshes are interchangeable within a family.
2. **Recoloring the original DDS texture** toward each race's palette
   (ImageMagick, DXT5 + full mipmaps), installed as `LHL_<Race>_<Kind>_Texture.dds`
   into `Gfx/HKB/Monsters/` and referenced by the item XML.

This is fully automatic, requires zero manual modeling, and is guaranteed
loadable in-game.

```powershell
python monster_race_tool.py variants --all          # preview picks per race
python monster_race_tool.py generate --all --mode tools --install
```

## Config

`monster_race_config.json`:

- `clothes` / `armor` / `weapon` → `model` + `texture` (original HKB paths)
- `iconSource` → medallion/card filename
- `assetPolicy: "originals"`
- `textureVariants: true` → auto-recolor DDS per race/kind (recommended)
- `altItems: true` → emit a second `(Alt)` item per clothes/armor/weapon
- `meshPolicy: "configured"` → keep curated per-race meshes (mesh picks are
  advisory only; see `variants` output, edit a race `model` to opt in)

### Alt items + fallbacks

Every pack gets a Base and an Alt GameItemType (`…_Torso` / `…_Torso_Alt`).

| Asset | Prefer | Fallback |
|-------|--------|----------|
| Model | Different family-pool mesh | Configured model → `baseModelPath` |
| Texture | Recolored `LHL_*_Alt_Texture.dds` | Original texture → sibling kind texture → omit |
| Icon | Original medallion (hue-shifted for Alt) | Procedural icon |

```powershell
python monster_race_tool.py variants --all
python monster_race_tool.py generate --all --mode tools --install
python monster_race_tool.py validate
```
- `havokPath` → HCT **7.1** Standalone Filter Manager root
- `softimagePath` → Softimage Mod Tool 7.5 (FBX bridge to HCT)
- `blenderPath` → Blender for FBX fit exports

## New race-fit meshes (Havok)

Current generate mode reuses original race HKB. To author **new** skinned clothes/armor:

1. Fit mesh in Blender onto the race armature → FBX (`blender_fit_armor.py`)
2. Import FBX in **Softimage Mod Tool 7.5**
3. HCT 7.1 Filter Manager → **Write to Platform → Packfile** (not Tagfile)
4. Place as `.hkb` under mod `Gfx/HKB/LHL/<Race>/`
5. Point `ModelFile` at the new mesh; `AttachmentType` = Skinned

```powershell
python monster_race_tool.py doctor --havok-checklist
python monster_race_tool.py softimage --open
python monster_race_tool.py havok --open
```

Configured:
- HCT: `D:\games\Modding\Havok\Havok_7_1_32\HavokContentTools` (7.1.0.1 + XSI plugins)
- Softimage: `F:\tools\mod_tools\Softimage\Softimage_Mod_Tool_7.5` (7.5)

Link HCT into Softimage (one-time):

```powershell
python monster_race_tool.py softimage --install-havok
```

## Shared tools used

- **ImageMagick** — DDS/PNG convert + icon resize  
- **Ollama / SD** — optional icon polish (`--force-ai`) + Mod Manager banners (`banner`)  
- **Pillow** — fallback if an original file / SD is missing  
- **Havok Content Tools 7.1** — Packfile `.hkb` export for new meshes  
- **Blender** — armature fit → FBX scaffold  

Default mod: `D:\User_Directories\Documents\My Games\ElementalReforged\Mods\LH_Legacy_Expansion`  
Banner config: `modPackage` in `monster_race_config.json` (`genWidth`/`genHeight`/`bannerSteps`/`bannerGuidance`; delivery 512×439, default gen 768×640).
