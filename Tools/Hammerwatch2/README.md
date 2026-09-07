# Hammerwatch 2 Tools

Specialized helpers for HW2 / HoH2 class mods under:
`F:\SteamLibrary\steamapps\common\Hammerwatch 2\`
`F:\SteamLibrary\steamapps\common\Heroes of Hammerwatch 2\`

## Asset sources (policy)

| Need | Tool | Notes |
|------|------|--------|
| **Skill / UI icons** | Local SD3.5 (`Generate-SkillIcons.ps1`) | **Only** HW2 use of the SD server. |
| **Projectiles / VFX sheets** | **Non-SD reference compose** (default) | `Generate-ProjectileEffectAssets.ps1` / `generate_hw2_vfx.py` — no SD server. |
| **Units / bodies** | Vanilla `assets.bin` paths, `hw2_tgas`, `Generate-WildshapeBody.ps1` | Prefer absolute vanilla paths when possible. |

### Projectiles / VFX without SD (default)

Reference-compose cuts frames from unpacked HoH2/HW2 art (boss_wraith skull, groundspikes, warrior tremor chips), recolors, and writes horizontal sheets.

```powershell
cd D:\games\Steam\steamapps\common\Transcendence\Tools\Hammerwatch2

# List presets
.\Generate-ProjectileEffectAssets.ps1 -List

# Soul skull sheet (Eldritchsoul)
.\Generate-ProjectileEffectAssets.ps1 -Preset soul_skull

# Earth VFX
.\Generate-ProjectileEffectAssets.ps1 -Preset stone_spikes
.\Generate-ProjectileEffectAssets.ps1 -Preset tremor_ring

# All presets + optional planar TIF
.\Generate-ProjectileEffectAssets.ps1 -Preset all -ConvertTif

# Or python directly
python .\generate_hw2_vfx.py --preset soul_skull
python .\generate_hw2_vfx_nonsd.py --preset all
```

Optional Blender / Vortex (also no SD drafts):

```powershell
cd ..\Qud
.\GenerateVortexAssets.ps1 -ModPath "..." -GenerateDesignDraft:$false

cd ..\Common
.\ProjectileSystemGenerator.ps1 -RegistryPath ".\projectile_registry_example.json"
```

Do **not** start the SD server for projectile/VFX work. Experimental SD sheets: `python generate_hw2_vfx.py --sd --preset soul_skull`.

### Presets

| Preset | Source | Default out |
|--------|--------|-------------|
| `soul_skull` | `boss_wraith/.../skull_projectile.png` | `GeneratedAssets/eldritchsoul/` |
| `stone_spikes` | `effects/spritesheets/groundspikes.png` | `GeneratedAssets/druidic_earth/` |
| `tremor_ring` | `effects.png` tremor ring/chips | `GeneratedAssets/druidic_earth/` |

Requires unpack under HoH2 (`unpacked_assets_143` or `unpacked_assets_143-1`) or set `HOH2_ROOT`.

## Texture rule (important)

HW2 mods resolve `./texture.png` **relative to the mod file**, not from the base game.
If you copy a `.unit` / `.effect` but not its `.png` / `.tif`, the game reports missing textures.

**Preferred when possible:** absolute paths into `res/assets.bin` (no local TIF copy).

## Fixing .tif files

PACKAGER does **not** write TIFs in the game format. Copying from `unpacked_assets` → empty/glitched textures, load errors, `ERR` in `HW2.exe.log`.

Game wants **planar** TIFs (`RRGGBB`). Unpacked ones are contiguous (`RGBRGB`).

### 1. Replacement (best for vanilla art)

Local copy of the HW2 TIFS ZIP:

`F:\SteamLibrary\steamapps\common\Hammerwatch 2\hw2_tgas`

```powershell
.\Copy-Hw2Tifs.ps1 -RelativePaths @(
  "actors\beasts\shamblers\shambler_small\shambler_small.tif",
  "actors\beasts\shamblers\shambler_small\shambler_small_move.tif"
) -ModRoot "F:\SteamLibrary\steamapps\common\Hammerwatch 2\Druidic_Warden"
```

### 2. GIMP + planar post-process

```powershell
.\Convert-ToPlanarTif.ps1 -Path "F:\...\yourclass" -Recurse
```

### 3. ImageMagick PNG → planar TIF

```powershell
.\Convert-PngToPlanarTif.ps1 -Path "..."
```

## Scripts (this folder)

- `generate_hw2_vfx_nonsd.py` — reference-compose VFX (no SD)
- `generate_hw2_vfx.py` — defaults to nonsd; `--sd` optional
- `Generate-ProjectileEffectAssets.ps1` — PowerShell entry for nonsd (+ optional `-ConvertTif`)
- `Copy-Hw2Tifs.ps1` — copy planar TIFs from `hw2_tgas` into a mod
- `Convert-ToPlanarTif.ps1` / `Convert-PngToPlanarTif.ps1`
- `Extract-Assets.ps1` / `Scan-MissingTextures.ps1`
- `Generate-WildshapeBody.ps1` — wildshape body units
- `Generate-SkillIcons.ps1` — **SD icons only** (32×32)

```powershell
.\Generate-WildshapeBody.ps1
.\Generate-SkillIcons.ps1 -Name "soulburst" -Description "violet necrotic soul explosion skill icon"
.\Generate-ProjectileEffectAssets.ps1 -Preset soul_skull
```

## Output

`GeneratedAssets/` is for extracted or generated HW2 sprites before copying into a mod.
