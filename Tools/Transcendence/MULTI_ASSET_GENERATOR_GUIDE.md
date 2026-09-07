# Multi-Asset Generator Guide

Generate multiple asset types for multiple game formats simultaneously with intelligent dependency handling, real-time progress monitoring, and comprehensive error reporting.

## Table of Contents

1. [Overview](#overview)
2. [Requirements](#requirements)
3. [Quick Start](#quick-start)
4. [Basic Usage](#basic-usage)
5. [Advanced Usage](#advanced-usage)
6. [Parameters Reference](#parameters-reference)
7. [Supported Asset Types](#supported-asset-types)
8. [Game-Specific Notes](#game-specific-notes)
9. [Dependency Handling](#dependency-handling)
10. [Error Handling](#error-handling)
11. [Testing](#testing)
12. [Troubleshooting](#troubleshooting)

---

## Overview

The Multi-Asset Generator is a unified pipeline for creating game assets across multiple formats:

- **Terraria** (tModLoader) - Tiles, particles, icons, spritesheets
- **Elin** - Spell icons, FX, projectiles
- **Caves of Qud** - Tiles, spritesheets
- **Starbound** - Ships, textures, animations
- **CDDA** (Cataclysm: DDA) - Creatures, tiles
- **Transcendence** - Ship textures, 3D models

### Key Features

- Parallel generation for maximum performance
- Real-time file watching with live updates
- Intelligent dependency ordering
- ETA calculation with adaptive timing
- Comprehensive error reporting with suggestions
- JSON/HTML report generation
- Drag-and-drop support via batch file

---

## Requirements

- **PowerShell 7+** (pwsh) - recommended
- **PowerShell 5.1** - minimum (comes with Windows)
- **Ollama** - for AI-powered generation (optional)
- **Blender** - for 3D model generation (optional)

---

## Quick Start

### Method 1: Drag-and-Drop

1. Create a JSON config file:
```json
{
  "AssetName": "MagicPortal",
  "AssetTypes": ["Tile", "Particle"],
  "GameTypes": ["Terraria"],
  "Description": "A swirling magical portal with purple energy"
}
```

2. Drag the JSON file onto `MultiAssetGenerator.bat`

### Method 2: Command Line

```powershell
.\MultiAssetGenerator.ps1 -AssetTypes @("Tile", "Particle") -GameTypes @("Terraria") -AssetName "MagicPortal"
```

### Method 3: Interactive

1. Double-click `MultiAssetGenerator.bat`
2. Follow the prompts

---

## Basic Usage

### Single Asset Type, Single Game

```powershell
.\MultiAssetGenerator.ps1 `
    -AssetTypes @("Tile") `
    -GameTypes @("Terraria") `
    -AssetName "MyTile"
```

### Multiple Asset Types, Single Game

```powershell
.\MultiAssetGenerator.ps1 `
    -AssetTypes @("Tile", "Particle", "Icon") `
    -GameTypes @("Terraria") `
    -AssetName "PortalBundle"
```

### Single Asset Type, Multiple Games

```powershell
.\MultiAssetGenerator.ps1 `
    -AssetTypes @("Texture") `
    -GameTypes @("Terraria", "Starbound", "Transcendence") `
    -AssetName "SharedTexture"
```

### All Games

```powershell
.\MultiAssetGenerator.ps1 `
    -AssetTypes @("Tile", "Icon") `
    -GameTypes @("All") `
    -AssetName "UniversalAsset"
```

---

## Advanced Usage

### With AI Description

```powershell
.\MultiAssetGenerator.ps1 `
    -AssetTypes @("Tile", "Particle", "FX") `
    -GameTypes @("Terraria", "Elin") `
    -AssetName "CrystalPortal" `
    -AssetDescription "A crystalline portal emanating blue energy with floating shards"
```

### Custom Output Directory

```powershell
.\MultiAssetGenerator.ps1 `
    -AssetTypes @("Texture", "Model") `
    -GameTypes @("Transcendence") `
    -AssetName "CustomShip" `
    -OutputDir "C:\MyMods\Assets"
```

### With Control Room GUI

```powershell
.\MultiAssetGenerator.ps1 `
    -AssetTypes @("Tile") `
    -GameTypes @("Terraria") `
    -AssetName "WatchedAsset" `
    -LaunchControlRoom
```

### Custom Parameters

```powershell
.\MultiAssetGenerator.ps1 `
    -AssetTypes @("Tile", "Particle") `
    -GameTypes @("Terraria") `
    -AssetName "AnimatedPortal" `
    -TileSize 32 `
    -FrameCount 16 `
    -ParticleCount 8 `
    -ParticleFrames 6
```

---

## Parameters Reference

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `-AssetTypes` | String[] | Required | Asset types to generate |
| `-GameTypes` | String[] | `@("All")` | Target game formats |
| `-AssetName` | String | Required | Base name for assets |
| `-AssetDescription` | String | Auto-generated | Description for AI generation |
| `-OutputDir` | String | `"GeneratedAssets"` | Output directory |
| `-LaunchControlRoom` | Switch | False | Launch GUI monitor |
| `-UseAI` | Switch | False | Enable AI generation |
| `-OllamaModel` | String | `"llama3.2"` | Ollama model to use |
| `-TileSize` | Int | 16 | Tile size in pixels |
| `-FrameCount` | Int | 8 | Animation frames for tiles |
| `-ParticleCount` | Int | 4 | Number of particle variants |
| `-ParticleFrames` | Int | 4 | Frames per particle |

---

## Supported Asset Types

| Asset Type | Description | Terraria | Elin | Qud | Starbound | CDDA | Transcendence |
|------------|-------------|:--------:|:----:|:---:|:---------:|:----:|:-------------:|
| Tile | Base tile/block | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Particle | Particle effects | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| Icon | UI/inventory icons | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| FX | Visual effects | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| Projectile | Projectile sprites | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| Ship | Ship/vehicle assets | ❌ | ❌ | ❌ | ✅ | ❌ | ✅ |
| Creature | NPC/enemy sprites | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Texture | 2D textures | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Model | 3D models | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| Spritesheet | Assembled sheets | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## Game-Specific Notes

### Terraria (tModLoader)
- Uses `TerrariaPortalGenerator.ps1` for tiles
- Particle effects use `ParticleEffectGenerator.ps1`
- Output includes C# code files for tModLoader

### Elin
- Spell-focused assets via `ElinSpellAssetGenerator.ps1`
- Icon sizes: 32×32 pixels
- FX/Projectile support multi-frame animations

### Caves of Qud
- Tile sizes: 24, 32, or 48 pixels
- Uses ASCII-art-friendly color palette
- Spritesheet export for mod integration

### Starbound
- Supports C++ backend for advanced generation
- Animation frame support built-in
- Ship parts include hardpoint definitions

### CDDA (Cataclysm: DDA)
- 2D-only (no 3D models)
- No particle/FX support (roguelike)
- Tile-based creature sprites

### Transcendence
- Ship textures with XML integration
- 3D model support via Blender
- Spritesheet for animation sequences

---

## Dependency Handling

The generator automatically orders asset generation based on dependencies:

### Terraria
```
Particle → Tile (particles reference tile position)
FX → Tile
Projectile → Icon
Spritesheet → Icon, Tile
```

### Elin
```
FX → Icon
Projectile → Icon
Spritesheet → Icon, FX
```

### Starbound
```
Texture → Model (textures baked from 3D)
Spritesheet → Icon, Texture
```

### Transcendence
```
Texture → Model
Spritesheet → Texture
```

Dependencies are resolved automatically - you don't need to specify order.

---

## Error Handling

### Error Types and Suggestions

The generator provides intelligent error analysis:

| Error Pattern | Suggestion |
|--------------|------------|
| File not found | Check if required input files exist |
| Ollama connection refused | Ensure Ollama is running (`ollama serve`) |
| Parameter mismatch | Check script compatibility |
| Permission denied | Check folder permissions |
| Blender/Python error | Ensure dependencies are installed |

### Error Log Files

Detailed error logs are saved to:
```
Logs/MultiAsset_Errors_YYYYMMDD_HHMMSS.log
```

Contents include:
- Full stack traces
- Command arguments
- Suggested fixes
- Error context

---

## Testing

### Run Quick Tests
```powershell
.\TestMultiAssetGenerator.ps1 -TestType Quick
```

### Run Full Test Suite
```powershell
.\TestMultiAssetGenerator.ps1 -TestType Full -SkipCleanup
```

### Test Types

| Type | Description |
|------|-------------|
| Quick | Basic functionality (3 tests) |
| Standard | Multiple combinations (7 tests) |
| Full | All games, all types (~15 tests) |
| ErrorHandling | Unsupported combinations |
| Performance | Large batch generation |

---

## Troubleshooting

### "No generator found for X in Y"

The combination is not supported. Check the [Supported Asset Types](#supported-asset-types) table.

### "Ollama connection refused"

1. Start Ollama: `ollama serve`
2. Check it's running: `curl http://localhost:11434/api/tags`
3. Pull a model: `ollama pull llama3.2`

### "Job crashed" errors

1. Check the error log in `Logs/`
2. Verify generator scripts exist
3. Try running the generator script directly

### Slow generation

1. Reduce parallel jobs (generators are CPU-intensive)
2. Use smaller asset types first
3. Check Ollama/Blender aren't blocking

### Files not appearing

1. Check output directory exists
2. Verify file watchers are active (shown in log)
3. Some generators may not produce files immediately

---

## Examples

### Complete Portal Bundle
```powershell
.\MultiAssetGenerator.ps1 `
    -AssetTypes @("Tile", "Particle", "FX", "Icon", "Spritesheet") `
    -GameTypes @("Terraria", "Elin") `
    -AssetName "ArcanePortal" `
    -AssetDescription "A mystical portal with swirling arcane energy and floating runes" `
    -TileSize 32 `
    -FrameCount 12 `
    -ParticleCount 6
```

### Cross-Game Texture
```powershell
.\MultiAssetGenerator.ps1 `
    -AssetTypes @("Texture") `
    -GameTypes @("All") `
    -AssetName "UniversalMetal" `
    -AssetDescription "Brushed metal texture with subtle wear and scratches"
```

### Batch JSON Config
```json
{
  "AssetName": "NatureSpell",
  "AssetTypes": ["Icon", "FX", "Projectile"],
  "GameTypes": ["Elin"],
  "Description": "Nature magic with green leaves and vines",
  "OutputDir": "ElinMod/Assets"
}
```

---

## File Structure

After generation, output is organized by game:

```
GeneratedAssets/
└── MyAsset/
    ├── Terraria/
    │   ├── Assets/Textures/Tiles/
    │   │   └── MyAsset.png
    │   └── Content/Tiles/
    │       └── MyAssetTile.cs
    ├── Elin/
    │   └── Icons/
    │       └── MyAsset_icon.png
    ├── Qud/
    │   └── Tiles/
    │       └── MyAsset.png
    └── ...
```

---

## Related Tools

- `AssetGeneratorControlRoom.ps1` - GUI for real-time monitoring
- `TestMultiAssetGenerator.ps1` - Comprehensive test suite
- `TerrariaPortalGenerator.ps1` - Terraria-specific portal generator
- `ElinSpellAssetGenerator.ps1` - Elin spell asset generator
- `ParticleEffectGenerator.ps1` - Cross-game particle generator

---

*Last Updated: 2025-12-29*

