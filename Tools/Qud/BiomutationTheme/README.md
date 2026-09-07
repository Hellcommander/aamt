# Biomutation Theme Pack (Broodmother)

Real textures come from **Ollama prompt packs + SD3.5 drafts**, not procedural shapes.

## Generate game tiles

Use `wizardlm-uncensored:latest` for all Ollama prompt-pack / art-director calls (no content filters). Override with `-OllamaModel` / `--model` if needed.

## Double-click launchers (no agent)

From the mod folder:
- `START_SD_SERVER.bat`
- `GENERATE_ASSETS.bat` — biomutation prompt pack → SD → Textures (recommended)
- `GENERATE_ASSETS_FRESH_PROMPTS.bat` — new wizardlm prompts + SD
- `GENERATE_ASSETS_MENU.bat`

From Tools:
- `D:\games\Steam\steamapps\common\Transcendence\Tools\Qud\BroodmotherAssets-Menu.bat`

```powershell
# 1) Start SD3.5 (port 1338) if not already running
& "D:\games\Steam\steamapps\common\Transcendence\Tools\Start-StableDiffusionServer.ps1"

# 2) Generate drafts + export PNGs into the mod
& "D:\games\Steam\steamapps\common\Transcendence\Tools\Qud\GenerateBroodmotherAssets.ps1" `
  -ModPath "$env:USERPROFILE\AppData\LocalLow\Freehold Games\CavesOfQud\Mods\Broodmother Mutation" `
  -OllamaModel "wizardlm-uncensored:latest" `
  -LoadExisting -Verbose
```

Outputs land in:
- `Mods\Broodmother Mutation\DesignDrafts\` (1024 SD drafts + `prompt_pack.json`)
- `Mods\Broodmother Mutation\Textures\` (exported game PNGs)

## Theme lock

Every prompt must keep: veined magenta membranes, arthropod chitin, ichor, biometal filaments, glandular organs, hive pheromone sheen, Caves of Qud organic terminal mood. No cute cartoon / anime / purple neon HUD / simple geometry.

## Unity AI materials

Point Unity Assistant at:
`...\Broodmother Mutation UI\...\Assets\Arendeth_UI\Docs\BIOMUTATION_THEME_MATERIALS.md`

Use `prompt_pack.json` from DesignDrafts after a successful run as the SD prompt source of truth.
