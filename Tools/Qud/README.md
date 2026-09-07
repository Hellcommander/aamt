# Caves of Qud — AI-assisted toolkit

`D:\games\Ai assisted toolkit\Tools\Qud`

This folder is the Qud home under **AI assisted toolkit\Tools**: tile/audio/asset generators, Qud Lab, Choose Your Fighter, **and** the obsolete-API migrator (moved here from `CavesOfQud\_tools`).

Local mods still live at `%USERPROFILE%\AppData\LocalLow\Freehold Games\CavesOfQud\Mods`. Game install / Workshop are autodetected (`SteamInstall` / `Get-CoqSteamLibrary`). Overrides: `COQ_MODS_ROOT`, `COQ_TOOLS_ROOT`, `QUDLAB_QUD_PATH`.

Double-click **`Launch-Gui.bat`** for a menu of every desktop GUI. ApiMigrator alone: **`Launch-ApiMigrator.bat`**.

---

## ApiMigrator (obsolete APIs, CP437, chargen XML)

Moved from LocalLow `_tools`. Full notes: **[ApiMigrator.md](ApiMigrator.md)**

| Launch | What |
|---|---|
| `Launch-ApiMigrator.bat` | GUI — migrate / obsolete map / DLL research |
| `Update-ObsoleteApis.ps1` | PowerShell migrate (best for Workshop writes) |
| `Convert-Cp437.ps1` | CP437 → UTF-16 |
| `Validate-ChargenXml.ps1` | New-game / chargen XML checks |
| `Resolve-Cs0618.ps1` | Compile against Managed, harvest CS0618 |
| `Switch-Api.bat` | Pin dump+rules to public / lang-experimental / live |

Old paths under `CavesOfQud\_tools\` still redirect here (`Launch-Gui.bat` there opens ApiMigrator directly).

---

## Qud Lab (mod IDE)

Unity 6–hosted IDE + restricted simulator + local AI. **[QudLab/README.md](QudLab/README.md)**

| Launch | What |
|---|---|
| `QudLab\QudLab.bat` | Desktop control panel |
| `QudLab\qudlab-cli.bat` | CLI (`serve`, `compile`, `simulate`, `ollama scan`) |
| `Qud Lab IDE.code-workspace` | Cursor workspace |

Requires a Steam/GOG CoQ install. Match Unity **6000.0.77f1**. Does not redistribute game DLLs.

---

## Tiles, drawing, and Unity assets

Unified Blender / ImageMagick / Ollama detection: **[QUD_TOOLSET_INTEGRATION.md](QUD_TOOLSET_INTEGRATION.md)**

| Launch | What | Guide |
|---|---|---|
| `BakeQudTile.bat` / `.ps1` | Bake a drawing to a Qud tile | [DRAWING_TO_QUD_TILE_GUIDE.md](DRAWING_TO_QUD_TILE_GUIDE.md) |
| `ExportQudTiles.bat` / `.ps1` | Export tiles | [QUD_TILE_EXPORT_GUIDE.md](QUD_TILE_EXPORT_GUIDE.md) |
| `QudTileAIGenerator.bat` / `.ps1` | AI-assisted tile from a drawing | [QUD_TILE_AI_GENERATOR_GUIDE.md](QUD_TILE_AI_GENERATOR_GUIDE.md) |
| `QudUnityAssetGenerator.bat` / `.ps1` | Unity `.meta` / import helpers | |
| `GeneratePbrSkin.ps1` | PBR skin bake | |
| `GetQudSettings.ps1` | Read `settings.json` (game / Unity paths) | |

`settings.json` — live game root; Unity editor path is resolved from the game binary.

---

## Choose Your Fighter

Player tile + unfiltered detailed art from Recur export / save. **[CHOOSE_YOUR_FIGHTER.md](CHOOSE_YOUR_FIGHTER.md)**

```bat
ChooseYourFighter-GUI.bat
```

---

## Atlas art / CP437 text

**[ATLAS_ART_TRANSLATOR.md](ATLAS_ART_TRANSLATOR.md)**

```bat
AtlasArtTranslator-GUI.bat
```

---

## Mod fixer (Ollama / CodeLlama)

API + Harmony asset-path fixer (separate from ApiMigrator’s curated dump rewrites). **[QUD_MOD_FIXER_README.md](QUD_MOD_FIXER_README.md)** · [ASSET_GENERATION_GUIDE.md](ASSET_GENERATION_GUIDE.md)

```bat
QudModFixer.bat
GenerateModAssets.bat
```

Python: `qud_mod_fixer.py`, `generate_mod_assets.py`, `mutation_asset_generator.py`, `creature_asset_generator.py`, `equipment_asset_generator.py`, `unity_asset_generator.py`.

---

## Broodmother / biomutation / Mandibore assets

**[BROODMOTHER_ASSET_GENERATION_README.md](BROODMOTHER_ASSET_GENERATION_README.md)** · `BiomutationTheme\`

```bat
BroodmotherAssets-Menu.bat
GenerateBroodmotherAssets.bat
Start-BroodmotherSDServer.bat
Stop-BroodmotherSDServer.bat
SDServer-Status-GUI.bat
```

---

## Space-Time Vortex assets

**[QUICK_START.md](QUICK_START.md)** · **[VORTEX_ASSET_GENERATOR_README.md](VORTEX_ASSET_GENERATOR_README.md)**

```bat
GenerateVortexAssetsQuick.bat
GenerateVortexAssets.bat
```

---

## Audio

**[QUD_AUDIO_GENERATOR_GUIDE.md](QUD_AUDIO_GENERATOR_GUIDE.md)**

```bat
QudAudioGenerator.bat
```

Python: `qud_audio_generator.py`.

---

## Other scripts in this folder

| File | Role |
|---|---|
| `Balance-TTExtraBackgroundRep.ps1` | True Kin extra-background reputation balance |
| `gen_tt_starting_kit_maps.py` | True Kin starting-kit maps |
| `mandibore_sketch_to_tile.py` | Mandibore sketch → tile |
| `fix_both_mutations.bat` / `fix_space_time_vortex.bat` / `fix_with_simulation.bat` | Mutation fix launchers |
| `Test-DesignDraftGeneration.ps1` / `Test-SD3Module.ps1` | SD / draft tests |
| `Wait-SdReady.ps1` / `Stop-SdServer.ps1` | SD server helpers |
| `scripts\fix_becoming_*.py` / `gen_biomod_icons.py` | Becoming / biomod helpers |
| `data\spring_ui_broodmother_catalog.json` | Broodmother UI catalog |
| Embark `*.cs` at repo root | Decompiled chargen reference (not a game mod) |

---

## Layout

| Path | Role |
|------|------|
| `src\ApiMigrator.*` | Obsolete-API migrator (CLI / Core / GUI) |
| `data\` | ApiMigrator dump + rewrite rules (+ leftover catalogs) |
| `docs\coq-internal-patching.md` | CoQ XML overlay / Harmony notes |
| `QudLab\` | Mod IDE (own `src\`, Unity project, Workspace) |
| `BiomutationTheme\` | Broodmother biomutation theme pack |
| `reports\` | Migrator / scan reports |
| `ref\` / `archive\` | Reference dumps |

Mods workspace Cursor rules point here. Do not put this folder under `CavesOfQud\Mods` — the game would treat it as a mod.
