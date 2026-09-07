# Atlas Art Translator

Feed **[Atlas of Qud](https://steamcommunity.com/sharedfiles/filedetails/?id=3767493819)** automap PNGs into your AAMT SD stack and translate them into **non-tile** illustrated maps/landscapes (img2img).

## Input (from Atlas)

`%LocalLow%\Freehold Games\CavesOfQud\Synced\Saves\<save>\Automap\tiles\`

- One PNG per visited zone  
- Native size **1280×600**  
- Name: `World.ParasangX.ParasangY.ZoneX.ZoneY.Z.png`

Capture happens as you explore (or when opening Atlas with **Ctrl+M**).

## Quick start

```batch
AtlasArtTranslator-GUI.bat
```

1. Refresh → pick a save with tiles  
2. Select a zone (preview on the right)  
3. Style: cartography / landscape / dream  
4. Optional: Ollama caption, parasang 3×3 stitch  
5. **Generate illustrated art** (needs SD server)

CLI:

```powershell
.\AtlasArtTranslator.ps1 -Action List

.\AtlasArtTranslator.ps1 -Action Generate `
  -Path "...\Automap\tiles\JoppaWorld.11.22.1.1.10.png" `
  -Style landscape -OllamaCaption

# Stitch parasang then translate
.\AtlasArtTranslator.ps1 -Action Generate `
  -Path "...\Automap\tiles" `
  -Parasang "JoppaWorld.11.22.10" `
  -Style cartography -OllamaCaption
```

## Styles (denoising strength)

| Style | Strength | Intent |
|-------|----------|--------|
| cartography | ~0.42 | Keep roads/rooms; paint over tiles |
| landscape | ~0.60 | Illustrated overhead, same geography |
| dream | ~0.78 | Loose vibe piece |

Override: `-Strength 0.55`

## Outputs

`Tools\Output\AtlasArt\<zoneId>\`

- `<zoneId>.<style>.png` — illustrated result  
- `job.json` — prompt, strength, source path  

## Requirements

- Python 3 + Pillow  
- Stable Diffusion via `Shared\StableDiffusionIntegration.psm1` (img2img)  
- Optional: Ollama (+ vision model like `llava` for better layout captions)
