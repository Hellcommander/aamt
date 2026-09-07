# Survival / Crucible DLC layers vs main campaign

## How Grim Dawn loads modes

| Entry point | Layers loaded | Kitchen-sink content? |
|-------------|---------------|------------------------|
| **Main Campaign** | `database` + `gdx1` + `gdx2` + `gdx3` | **No** — `survivalmode*` is not used |
| **Crucible / Survival** (main menu) | Campaign layers + `survivalmode1` + `survivalmode2` + `survivalmode3` (+ optional `survivalmode4`) | Yes, if deployed as a Survival layer |
| **Custom Game** (`mods\…`) | That mod’s own `database` / resources | Yes, if you built a campaign/survival Custom Game |

Official Crucible folders (game root, like `gdx*`):

| Folder | Role |
|--------|------|
| `survivalmode1\` | AoM-era Crucible |
| `survivalmode2\` | FG-era Crucible |
| `survivalmode3\` | FoA-era Crucible |
| `mods\survivalmode\` | Custom Game Crucible pack (separate from main-menu Survival) |

## Important

**`survivalmode4` alone does not give you a main campaign with the merged mods.**  
Those folders only extend Crucible/Survival. Campaign stays vanilla FoA unless you also pack a **Custom Game**.

## Two archives (required dual setup)

| Archive | Path | Used for |
|---------|------|----------|
| **Survival DLC** | `<game>\survivalmode4\` | Main-menu Crucible / Survival |
| **Campaign** | `<game>\mods\CampaignKitchenSink\` | Custom Game for main campaign with kitchen-sink classes/items |

Staging build (merge source): `mods\SurvivalPlayground` — build this first, then pack both archives from it.

```
Main Campaign  ----------->  gdx* only  ----------->  CampaignKitchenSink Custom Game
Crucible menu  ----------->  gdx* + survivalmode*  ->  survivalmode4
Custom Game    ----------->  mods\<name>           ->  CampaignKitchenSink / NydiamarIntegrated
```

## Tooling

```bat
Run-GdSurvivalClasses.bat       REM 1) build mods\SurvivalPlayground
Run-GdPackDualArchives.bat      REM 2) pack survivalmode4 + CampaignKitchenSink
Run-GdBuildArz.bat              REM 3) CLI .arz build via toolset arzedit
Build-Arzedit.bat               REM (once) compile bin\arzedit.exe from source
```

Or separately:

```bat
Run-GdSurvivalDlcLayer.bat      REM survivalmode4 only
python pack_dual_archives.py --skip-survival   REM campaign pack only
python build_mod_arz.py --target survival
python build_mod_arz.py --target campaign
```

GUI → Survival playground:

- **Build SurvivalPlayground** — merge staging
- **Pack both archives** — Survival DLC (`survivalmode4`) + Campaign Custom Game
- **Build .arz (arzedit CLI)** — compile both databases without Asset Manager
- **Deploy Crucible layer only** — survivalmode4 alone

After pack: either **Run-GdBuildArz.bat** or Asset Manager. Expected outputs:

1. `survivalmode4\database\SurvivalMode4.arz`
2. `mods\CampaignKitchenSink\database\CampaignKitchenSink.arz`

arzedit source lives under `Tools\GrimDawn\arzedit\` — see `arzedit\README.md`.

If the game ignores `survivalmode4`:

```bat
python pack_survival_dlc_layer.py --source SurvivalPlayground --fallback-patch-layer survivalmode3
```

(Backs up official `survivalmode3` first. Steam updates may restore it.)

For full story + portals (Nydiamar), prefer `NydiamarIntegrated` over `CampaignKitchenSink`.
