# Starbound C++ Backend Integration Guide

## Overview

This integration connects the PowerShell asset generation tools with your C++ backend for the **Magi-Tech Arcane Alchemy and Sorcery** Starbound mod. It provides a bridge between:

- **PowerShell Generators**: Blender, Ollama, procedural generation
- **C++ Backend**: High-performance asset factories (Image, Texture, Particle, Animation, Icon, etc.)

## Architecture

```
PowerShell Tools → Lua Bridge → C++ Backend → Starbound Assets
     ↓                ↓              ↓              ↓
  Blender         Script Gen    Asset Factory   .frames/.png
  Ollama AI      Parameters     GPU Processing   JSON metadata
  Procedural     Execution     Thread Pool      Mod integration
```

## Quick Start

### Basic Usage

**Using PowerShell Generators (with Starbound export):**
```powershell
.\StarboundAssetGenerator.ps1 `
    -AssetType "Particle" `
    -AssetName "PortalEnergy" `
    -Description "Magical portal energy particles" `
    -OutputDir "StarboundAssets"
```

**Using C++ Backend:**
```powershell
.\StarboundAssetGenerator.ps1 `
    -AssetType "Particle" `
    -AssetName "PortalEnergy" `
    -UseCppBackend `
    -CppBackendPath "F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery\cpp_backend" `
    -OutputDir "StarboundAssets"
```

## Available Generators

### 1. Image Generator
- **C++ Class**: `ImageGenerator`
- **Lua Bindings**: `ImageGeneratorLuaBindings`
- **Features**: Images, spritesheets, animations, frame capture
- **Usage**:
```powershell
.\StarboundCppBackendBridge.ps1 `
    -GeneratorType "Image" `
    -AssetName "MyImage" `
    -Parameters @{Width=256; Height=256; Format="PNG"}
```

### 2. Texture Asset Factory
- **C++ Class**: `TextureAssetFactory`
- **Lua Bindings**: `TextureAssetLuaBindings`
- **Features**: Procedural noise, masks, PBR textures, atlases, compression
- **Usage**:
```powershell
.\StarboundCppBackendBridge.ps1 `
    -GeneratorType "Texture" `
    -AssetName "NoiseTexture" `
    -Parameters @{Width=512; Height=512; NoiseScale=4.0; Seed=0}
```

### 3. Particle Asset Factory
- **C++ Class**: `ParticleAssetFactory`
- **Lua Bindings**: `ParticleAssetLuaBindings`
- **Features**: Particle effects, emitters, behaviors, rendering
- **Usage**:
```powershell
.\StarboundCppBackendBridge.ps1 `
    -GeneratorType "Particle" `
    -AssetName "MagicParticles" `
    -Parameters @{ParticleCount=100; FrameCount=8; EffectType="Portal"}
```

### 4. Animation Asset Factory
- **C++ Class**: `AnimationAssetFactory`
- **Lua Bindings**: `AnimationAssetLuaBindings`
- **Features**: Frame sequences, timelines, Starbound animation JSON
- **Usage**:
```powershell
.\StarboundCppBackendBridge.ps1 `
    -GeneratorType "Animation" `
    -AssetName "SpellCast" `
    -Parameters @{FrameCount=8; FrameDuration=0.1; Mode="Loop"}
```

### 5. Icon Asset Factory
- **C++ Class**: `IconAssetFactory`
- **Lua Bindings**: `IconAssetLuaBindings`
- **Features**: Primitive shapes, SDF generation, atlases
- **Usage**:
```powershell
.\StarboundCppBackendBridge.ps1 `
    -GeneratorType "Icon" `
    -AssetName "SpellIcon" `
    -Parameters @{Size=64; Style="Default"; Shape="Circle"}
```

### 6. Spell Generator
- **C++ Class**: `GeneratorAgent`
- **Lua Bindings**: `GeneratorAgentLuaBindings`
- **Features**: Spell definitions, synthesis, genetic evolution
- **Usage**:
```powershell
.\StarboundCppBackendBridge.ps1 `
    -GeneratorType "Spell" `
    -AssetName "FireBolt" `
    -Parameters @{Name="Fire Bolt"; SpellType="projectile"; Power=1.5}
```

## Integration Workflow

### Step 1: Generate Assets

**Option A: PowerShell → Starbound Format**
```powershell
# Generate particles using PowerShell
.\ParticleEffectGenerator.ps1 `
    -EffectType "Portal" `
    -EffectName "PortalParticles" `
    -GameFormat @("Starbound") `
    -OutputDir "StarboundAssets"
```

**Option B: C++ Backend → Starbound Format**
```powershell
# Generate using C++ backend
.\StarboundCppBackendBridge.ps1 `
    -GeneratorType "Particle" `
    -AssetName "PortalParticles" `
    -OutputDir "StarboundAssets"
```

### Step 2: Execute in Starbound

The bridge generates Lua scripts that need to be executed in Starbound:

1. **Start Starbound** with the mod loaded
2. **Open console** or use mod interface
3. **Load the generated Lua script**:
```lua
local helper = require("integration_helper")
helper.execute("path/to/generated_script.lua")
```

### Step 3: Export Assets

Assets are exported to the `OutputDir` with:
- **PNG images** (spritesheets, textures, icons)
- **`.frames` files** (Starbound animation metadata)
- **JSON metadata** (asset information)
- **Lua scripts** (for mod integration)

## Example: Complete Particle Generation

```powershell
# 1. Generate particles
.\StarboundAssetGenerator.ps1 `
    -AssetType "Particle" `
    -AssetName "MagicExplosion" `
    -Description "Explosive magical particles with purple and blue colors" `
    -UseCppBackend `
    -Parameters @{
        ParticleCount = 100
        FrameCount = 8
        ParticleSize = 8
        EffectType = "Explosion"
    }

# 2. Generated files:
# - StarboundAssets/MagicExplosion/MagicExplosion_Particles.png
# - StarboundAssets/MagicExplosion/StarboundExport/MagicExplosion_Particles.png
# - StarboundAssets/MagicExplosion/StarboundExport/MagicExplosion_particles.json
# - StarboundAssets/MagicExplosion/generation_metadata.json
# - StarboundAssets/integration_helper.lua
```

## C++ Backend Structure

Your C++ backend is located at:
```
F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery\cpp_backend\agents\GeneratorAgent
```

### Key Components:

1. **GeneratorAgent.hpp/cpp**: Main agent for spell generation
2. **ImageGenerator.hpp/cpp**: Image/spritesheet/animation generation
3. **TextureAssetFactory.hpp/cpp**: Procedural texture generation
4. **ParticleAssetFactory**: Particle effect generation
5. **AnimationAssetFactory**: Animation generation
6. **IconAssetFactory**: Icon generation
7. **Lua Bindings**: Expose C++ functions to Lua

### Factory Pattern:

Each generator follows this pattern:
- `*Factory.hpp`: Factory class definition
- `*Generators.cpp`: Generation logic
- `*LuaBindings.cpp/hpp`: Lua interface
- `*Types.hpp`: Type definitions

## Lua Script Generation

The bridge generates Lua scripts that call your C++ backend:

```lua
-- Example generated script
require("agents.GeneratorAgent.ParticleAssetFactory")

initialize_particle_asset_factory(500, 4)

local particleParams = create_particle_params()
particleParams.id = "PortalParticles"
particleParams.particleCount = 4
particleParams.frameCount = 4
particleParams.particleSize = 8
particleParams.effectType = "Portal"

local bundle = generate_particle_async(particleParams):get()
if bundle and bundle:isValid() then
    print("✓ Particles generated successfully")
    export_particle_bundle(bundle, "StarboundAssets")
end
```

## Integration with Existing Tools

### Particle Generator Integration

The PowerShell `ParticleEffectGenerator.ps1` can now export directly to Starbound format:

```powershell
.\ParticleEffectGenerator.ps1 `
    -EffectType "Portal" `
    -EffectName "PortalEnergy" `
    -GameFormat @("Starbound") `
    -OutputDir "StarboundAssets"
```

This creates:
- Spritesheet PNG
- `.frames` metadata file
- JSON configuration

### Asset Maker AI Integration

Generate assets with AI and export to Starbound:

```powershell
.\AssetMakerAI.ps1 `
    -Action GenerateTexture `
    -InputData "Magical portal texture, purple and blue energy" `
    -OutputPath "StarboundAssets" `
    -TextureSize 256

# Then convert to Starbound format
.\StarboundAssetGenerator.ps1 `
    -AssetType "Texture" `
    -AssetName "PortalTexture" `
    -OutputDir "StarboundAssets"
```

## Best Practices

1. **Use C++ Backend for Performance**: For real-time generation or batch processing
2. **Use PowerShell for AI/Blender**: For AI-generated or Blender-rendered assets
3. **Export to Starbound Format**: Always use `-GameFormat @("Starbound")` for compatibility
4. **Test in Starbound**: Always test generated assets in-game
5. **Cache Results**: Use the C++ backend's caching system for repeated generations

## Troubleshooting

### Lua Script Not Executing

- **Check Starbound Console**: Look for error messages
- **Verify Mod Loaded**: Ensure the mod is active
- **Check Paths**: Ensure all paths are correct
- **Test Lua Bindings**: Verify C++ backend Lua bindings are registered

### Assets Not Generating

- **Check Backend Path**: Verify `CppBackendPath` is correct
- **Check Factory Initialization**: Ensure factories are initialized
- **Check Parameters**: Verify parameters match expected types
- **Check Output Directory**: Ensure write permissions

### Format Issues

- **Starbound `.frames` Format**: Ensure frame grid dimensions are correct
- **PNG Format**: Use RGBA PNG for transparency
- **JSON Metadata**: Verify JSON structure matches Starbound expectations

## Advanced Usage

### Custom Lua Scripts

You can provide custom Lua scripts:

```powershell
.\StarboundCppBackendBridge.ps1 `
    -LuaScript @"
-- Custom generation logic
local params = create_custom_params()
-- ... custom code ...
"@ `
    -OutputDir "StarboundAssets"
```

### Batch Generation

Generate multiple assets:

```powershell
$assets = @("FireParticles", "IceParticles", "LightningParticles")
foreach ($asset in $assets) {
    .\StarboundAssetGenerator.ps1 `
        -AssetType "Particle" `
        -AssetName $asset `
        -UseCppBackend `
        -OutputDir "StarboundAssets"
}
```

### Integration with Mod Development

1. **Generate Assets**: Use the tools to create assets
2. **Export to Mod Directory**: Copy assets to mod's asset folder
3. **Update Mod Code**: Reference assets in mod Lua/JSON
4. **Test in Game**: Verify assets work correctly

## References

- **C++ Backend**: `F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery\cpp_backend`
- **GeneratorAgent**: `agents\GeneratorAgent\`
- **Example Scripts**: `example_*.lua` files in GeneratorAgent directory
- **Documentation**: `COMPREHENSIVE_PIPELINE_INTEGRATION.md`

---

**Generated by**: Starbound C++ Backend Bridge  
**Compatible with**: Magi-Tech Arcane Alchemy and Sorcery mod  
**Version**: 1.0

