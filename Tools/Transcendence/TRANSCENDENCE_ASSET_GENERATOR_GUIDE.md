# Transcendence Asset Generator Guide

Complete guide for generating high-quality assets for Transcendence mods, with special focus on 120-facings ships.

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Ship Generation (120 Facings)](#ship-generation-120-facings)
4. [Weapon & Item Icons](#weapon--item-icons)
5. [Projectile Sprites](#projectile-sprites)
6. [Spritesheets](#spritesheets)
7. [Quality Levels](#quality-levels)
8. [Batch Generation](#batch-generation)
9. [Troubleshooting](#troubleshooting)

---

## Overview

The Transcendence Asset Generator creates assets specifically formatted for Transcendence mods, with optional Nova Drift design inspiration:

- **Ships**: 120-facings spritesheets with hero images
- **Weapons**: 96×96 pixel icons
- **Items**: 96×96 pixel icons
- **Projectiles**: Animated sprites
- **Spritesheets**: Resource images for mods
- **Nova Drift Styles**: Optional design references from [Nova Drift ships](https://nova-drift.fandom.com/wiki/Ships)

- **Ships**: 120-facings spritesheets with hero images
- **Weapons**: 96x96 pixel icons
- **Items**: 96x96 pixel icons
- **Projectiles**: Animated sprites
- **Spritesheets**: Resource images for mods

### Key Features

- **120 Facings Support**: Ships generate with proper rotation frames
- **Quality Levels**: Standard, High, Ultra quality presets
- **AI Integration**: Optional AI-powered generation via Ollama
- **Batch Processing**: Generate all CrossModCompatibility assets at once
- **XML Integration**: Auto-generates XML reference files

---

## Quick Start

### Generate a Single Ship

```powershell
.\TranscendenceAssetGenerator.ps1 `
    -AssetType Ship `
    -AssetName "MyShip" `
    -Description "A fast scout ship with twin engines" `
    -Quality High `
    -Facings 120
```

### Generate Weapon Icon

```powershell
.\TranscendenceAssetGenerator.ps1 `
    -AssetType Weapon `
    -AssetName "QuantumChamber" `
    -Description "Quantum weapon chamber" `
    -Quality High `
    -IconSize 96
```

### Generate All CrossModCompatibility Assets

```powershell
.\CrossModCompatibilityAssetGenerator.ps1 `
    -GenerateAll `
    -Quality High `
    -UseAI
```

---

## Ship Generation (120 Facings)

Transcendence ships require **120 rotation frames** for smooth rotation. The generator creates:

1. **Main Spritesheet**: 10 columns × 12 rows = 120 frames
2. **Hero Image**: 320×320 for ship selection screen
3. **Mask Files**: For transparency
4. **XML Reference**: Shows how to use in your mod

### Ship Spritesheet Layout

```
Frame Layout (10 columns × 12 rows):
┌────┬────┬────┬────┬────┬────┬────┬────┬────┬────┐
│  0 │  1 │  2 │  3 │  4 │  5 │  6 │  7 │  8 │  9 │
├────┼────┼────┼────┼────┼────┼────┼────┼────┼────┤
│ 10 │ 11 │ 12 │ 13 │ 14 │ 15 │ 16 │ 17 │ 18 │ 19 │
├────┼────┼────┼────┼────┼────┼────┼────┼────┼────┤
│ ...                                 ...         │
├────┼────┼────┼────┼────┼────┼────┼────┼────┼────┤
│110 │111 │112 │113 │114 │115 │116 │117 │118 │119 │
└────┴────┴────┴────┴────┴────┴────┴────┴────┴────┘
```

Each frame rotates by **3 degrees** (360° / 120 = 3°).

### Example: Generate Ship

```powershell
.\TranscendenceAssetGenerator.ps1 `
    -AssetType Ship `
    -AssetName "EvolvedFirefly" `
    -Description "An evolved Firefly-class ship with enhanced capabilities" `
    -Quality High `
    -Facings 120 `
    -FrameWidth 150 `
    -FrameHeight 150 `
    -SpritesheetColumns 10 `
    -NovaDriftStyle Firefly `
    -UseAI
```

### Nova Drift Design Styles

The generator supports Nova Drift design inspiration for both ships and weapons:

#### Ship Styles (15 types)

- **Architect**: Modular construction ship with geometric, angular design
- **Assault**: Aggressive combat ship with forward-facing weapons
- **Battery**: Heavy weapons platform with multiple hardpoints
- **Carrier**: Large support ship with hangar bays
- **Courser**: Fast interceptor with sleek, streamlined design
- **Engineer**: Technical support ship with modular components
- **Firefly**: Small, agile scout ship with compact design
- **Hullbreaker**: Heavy assault ship with reinforced armor
- **Research**: Scientific vessel with sensor arrays
- **Sentinel**: Defensive platform with protective capabilities
- **Leviathan**: Massive capital ship with overwhelming firepower
- **Spectre**: Stealth ship with low-profile design
- **Standard**: Versatile all-purpose ship with balanced design
- **Stealth**: Infiltrator ship with minimal profile
- **Viper**: Fast attack ship with aggressive design

Reference: [Nova Drift Ships Wiki](https://nova-drift.fandom.com/wiki/Ships)

#### Weapon Styles (13 types)

- **Blade**: Melee weapon with sharp cutting edge
- **Blaster**: Rapid-fire energy weapon with continuous beam
- **Dart**: Fast projectile weapon firing small, dart-like projectiles
- **Flak**: Explosive area-effect weapon that detonates into fragments
- **Grenade**: Explosive projectile weapon with delayed detonation
- **Pulse**: Energy weapon firing pulsing energy blasts
- **Railgun**: Electromagnetic projectile launcher with high velocity
- **Salvo**: Multi-projectile weapon firing volleys of shots
- **SplitShot**: Projectile weapon that splits into multiple projectiles
- **Swords**: Dual melee weapons with crossed blade design
- **ThermalLance**: Heat-based energy weapon with focused thermal beam
- **Torrent**: Rapid-fire weapon with continuous stream of projectiles
- **Vortex**: Gravity-based weapon creating vortex effects

Reference: [Nova Drift Weapons Wiki](https://nova-drift.fandom.com/wiki/Weapons)

#### Item/Mod Styles (9 types)

- **WeaponMod**: Weapon modification module with enhancement components and targeting systems
- **ConstructMod**: Construct/drone modification module with control systems and deployment mechanisms
- **HullMod**: Hull/armor modification module with armor plating and structural reinforcements
- **ShieldMod**: Shield modification module with shield generators and energy conduits
- **BurnMod**: Burn/fire modification module with thermal systems and fire projectors
- **BlastMod**: Explosive modification module with explosive components and detonation systems
- **SuperMod**: Super modification module with advanced enhancement systems and power cores
- **WildMod**: Wild modification module with chaotic systems and experimental components
- **Module**: General modification module with modular components and upgrade mechanisms

Reference: [Nova Drift Mods Wiki](https://nova-drift.fandom.com/wiki/Mods)

#### Shield Styles (11 types)

- **Amp**: Amplifier shield that enhances damage output with energy amplification systems
- **Bastion**: Heavy defensive shield with maximum protection and reinforced generators
- **Halo**: Circular shield with protective ring design and orbital shield emitters
- **Helix**: Spiral shield with helical energy pattern and rotating generators
- **Orbital**: Shield with orbiting protective elements and multiple shield generators
- **Reflect**: Reflective shield that bounces projectiles with mirror-like surfaces
- **Shockwave**: Shield that emits shockwaves when hit with impact amplifiers
- **Siphon**: Shield that drains energy from enemies with energy siphon systems
- **Standard**: Standard balanced shield with moderate protection and balanced systems
- **Temporal**: Time-based shield with temporal effects and time manipulation systems
- **Warp**: Warp shield with spatial distortion effects and warp field generators

Reference: [Nova Drift Shields Wiki](https://nova-drift.fandom.com/wiki/Shields)

### Example: Generate Ship with Nova Drift Style

```powershell
.\TranscendenceAssetGenerator.ps1 `
    -AssetType Ship `
    -AssetName "MyShip" `
    -Description "A custom ship design" `
    -NovaDriftStyle Viper `
    -Quality High `
    -Facings 120 `
    -UseAI
```

### Example: Generate Weapon with Nova Drift Style

```powershell
.\TranscendenceAssetGenerator.ps1 `
    -AssetType Weapon `
    -AssetName "NovaBlade" `
    -Description "A blade weapon chamber" `
    -NovaDriftWeaponStyle Blade `
    -Quality High `
    -IconSize 96 `
    -UseAI
```

### Example: Generate Item with Nova Drift Mod Style

```powershell
.\TranscendenceAssetGenerator.ps1 `
    -AssetType Item `
    -AssetName "QuantumChamber" `
    -Description "A quantum weapon chamber module" `
    -NovaDriftItemStyle WeaponMod `
    -Quality High `
    -IconSize 96 `
    -UseAI
```

### Auto-Mapping in CrossModCompatibility

The batch generator automatically maps names to Nova Drift styles:

#### Weapon Mappings:
- `NovaBlade*` → **Blade** style
- `NovaSword*` → **Swords** style
- `NovaSalvo*` → **Salvo** style
- `NovaGrenade*` → **Grenade** style
- `Flakker*` → **Flak** style
- `NovaSplit*` → **SplitShot** style
- `NovaVolley*` → **Salvo** style
- `NovaRapidFire*` → **Torrent** style
- `NovaBarrage*` → **Salvo** style

#### Item/Mod Mappings:
- `*Chamber*`, `*FireModule*`, `*Amplifier*`, `*DamageUnit*` → **WeaponMod** style
- `*ShieldModule*` → **ShieldMod** style (general shield modifications)
- `*Armor*`, `*Plate*`, `*Reinforcement*` → **HullMod** style
- `*Drone*`, `*Swarm*`, `*Launcher*` → **ConstructMod** style
- `*Explosive*`, `*Grenade*`, `*Fragmentation*` → **BlastMod** style
- `*Flamethrower*`, `*Igniter*`, `*Thermal*` → **BurnMod** style
- `*Module*`, `*Stabilizer*`, `*Cooler*`, `*Link*` → **Module** style

#### Shield Mappings:
- `*Aegis*` → **Aegis** shield style
- `*Bastion*` → **Bastion** shield style
- `*Reflect*` → **Reflect** shield style
- `*Regen*`, `*Absorb*`, `*Siphon*` → **Siphon** shield style
- `*Explosive*` (shield) → **Shockwave** shield style
- `*Capacity*` → **Bastion** shield style
- `*Recharge*` → **Standard** shield style

### Output Files

For Transcendence ships, the generator creates **three separate image files**:

```
TranscendenceArt/EvolvedFirefly/
└── Ships/
    ├── EvolvedFirefly.jpg          # Main spritesheet (1500×1800) - 120 rotation frames in grid
    ├── EvolvedFireflyMask.bmp      # Spritesheet mask (if needed)
    ├── EvolvedFireflyLarge.jpg     # Hero image (320×320) - Single larger image for ship selection
    ├── EvolvedFireflyLargeMask.bmp # Hero mask - Black background with white ship outline
    ├── EvolvedFirefly_model.obj     # 3D model (if Blender available)
    └── EvolvedFirefly_ImageReference.xml  # XML usage example
```

**File Descriptions:**

1. **Main Spritesheet** (`EvolvedFirefly.jpg`):
   - 120 rotation frames arranged in 10×12 grid
   - JPG format for smaller file size
   - Used for in-game ship rotation

2. **Hero Image** (`EvolvedFireflyLarge.jpg`):
   - Single larger image (320×320)
   - Front-facing view
   - Used for ship selection screen
   - JPG format

3. **Hero Mask** (`EvolvedFireflyLargeMask.bmp`):
   - Black background
   - White outline of the ship
   - BMP format
   - Used for transparency on hero image

**Note:** Transcendence ships use **JPG** format for spritesheets and hero images (with separate BMP mask files), while items/weapons use **PNG** format. The generator automatically selects the correct format based on asset type.

### XML Integration

The generator creates an XML reference file showing how to use the ship:

```xml
<Image imageID="&rsEvolvedFireflyImage;" 
       imageWidth="150" 
       imageHeight="150" 
       rotationCount="120" 
       viewportRatio="0.005625" 
       rotationOffset="17" />

<HeroImage imageID="&rsEvolvedFireflyLarge;" 
           imageWidth="320" 
           imageHeight="320"/>
```

---

## Weapon & Item Icons

Weapons and items use **96×96 pixel icons** (standard Transcendence size).

### Generate Weapon Icon

```powershell
.\TranscendenceAssetGenerator.ps1 `
    -AssetType Weapon `
    -AssetName "QuantumChamber" `
    -Description "Quantum weapon chamber with energy coils" `
    -Quality High `
    -IconSize 96 `
    -UseAI
```

### Generate Item Icon

```powershell
.\TranscendenceAssetGenerator.ps1 `
    -AssetType Item `
    -AssetName "LivingWeaponManager" `
    -Description "Living weapon management device" `
    -Quality High `
    -IconSize 96 `
    -UseAI
```

### Output Structure

```
TranscendenceArt/QuantumChamber/
└── Weapons/
    └── QuantumChamber_icon.png  # 96×96 icon
```

---

## Projectile Sprites

Projectiles are smaller sprites used for weapon effects.

### Generate Projectile

```powershell
.\TranscendenceAssetGenerator.ps1 `
    -AssetType Projectile `
    -AssetName "QuantumBolt" `
    -Description "Quantum energy projectile with trail" `
    -Quality High `
    -UseAI
```

### Quality-Based Sizes

- **Standard**: 32×32
- **High**: 64×64
- **Ultra**: 128×128

---

## Spritesheets

Spritesheets combine multiple icons into a single image resource.

### Generate Weapon Parts Spritesheet

```powershell
.\TranscendenceAssetGenerator.ps1 `
    -AssetType Spritesheet `
    -AssetName "IWLWeaponParts" `
    -Description "Weapon Labs 51 weapon parts" `
    -Quality High `
    -SpritesheetColumns 8 `
    -SpritesheetRows 8 `
    -ResourceName "rsIWLWeaponParts"
```

### Output

- **Spritesheet**: `IWLWeaponParts_spritesheet.png`
- **Metadata**: `IWLWeaponParts_metadata.json` (dimensions, layout info)

---

## Quality Levels

### Standard Quality

- Ship frames: 128×128
- Icons: 96×96
- Textures: 256×256
- Anti-aliasing: None
- Color depth: 24-bit
- Compression: Medium

**Use for**: Quick prototypes, testing

### High Quality (Recommended)

- Ship frames: 150×150
- Icons: 96×96
- Textures: 512×512
- Anti-aliasing: 2×
- Color depth: 32-bit
- Compression: High

**Use for**: Production mods, public releases

### Ultra Quality

- Ship frames: 200×200
- Icons: 128×128
- Textures: 1024×1024
- Anti-aliasing: 4×
- Color depth: 32-bit
- Compression: Lossless

**Use for**: High-end mods, showcase content

---

## Batch Generation

### Generate All CrossModCompatibility Assets

```powershell
.\CrossModCompatibilityAssetGenerator.ps1 `
    -ExtensionPath "D:\games\Steam\steamapps\common\Transcendence\Extensions\ZZZ_CrossModCompatibility" `
    -GenerateAll `
    -Quality High `
    -UseAI `
    -OllamaModel "llama3.2"
```

### Selective Generation

```powershell
# Only ships
.\CrossModCompatibilityAssetGenerator.ps1 -GenerateShips -Quality High

# Only weapons
.\CrossModCompatibilityAssetGenerator.ps1 -GenerateWeapons -Quality High

# Ships and weapons
.\CrossModCompatibilityAssetGenerator.ps1 -GenerateShips -GenerateWeapons -Quality High
```

### Output Structure

```
TranscendenceArt/CrossModCompatibility/
├── EvolvedFirefly/
│   └── Ships/
│       ├── EvolvedFirefly.jpg
│       └── ...
├── QuantumChamber/
│   └── Weapons/
│       └── QuantumChamber_icon.png
├── IWLWeaponParts/
│   └── Spritesheets/
│       └── IWLWeaponParts_spritesheet.png
└── ...
```

---

## Troubleshooting

### "TranscendenceAssetGenerator.ps1 not found"

Ensure you're running from the `Tools` directory:
```powershell
cd "D:\games\Steam\steamapps\common\Transcendence\Tools"
```

### "Ollama connection refused"

1. Start Ollama: `ollama serve`
2. Check it's running: `curl http://localhost:11434/api/tags`
3. Pull a model: `ollama pull llama3.2`

### Ship spritesheet not generating correctly

- Verify `Facings` is set to 120
- Check `SpritesheetColumns` × `SpritesheetRows` = 120
- Default: 10 columns × 12 rows

### Icons appear blurry

- Use `-Quality High` or `-Quality Ultra`
- Ensure `IconSize` is 96 or higher
- Check anti-aliasing settings

### Missing mask files

Mask files are placeholders. In production:
- Use image editing software to create proper masks
- Masks should be black (transparent) and white (opaque)
- Save as BMP format

---

## Advanced Usage

### Custom Frame Dimensions

```powershell
.\TranscendenceAssetGenerator.ps1 `
    -AssetType Ship `
    -AssetName "CustomShip" `
    -Facings 120 `
    -FrameWidth 200 `
    -FrameHeight 200 `
    -SpritesheetColumns 10
```

### With Blender for 3D Models

```powershell
.\TranscendenceAssetGenerator.ps1 `
    -AssetType Ship `
    -AssetName "MyShip" `
    -BlenderPath "C:\Program Files\Blender Foundation\Blender\blender.exe" `
    -UseAI
```

### Custom Output Directory

```powershell
.\TranscendenceAssetGenerator.ps1 `
    -AssetType Ship `
    -AssetName "MyShip" `
    -OutputDir "C:\MyMod\Assets"
```

---

## Integration with Existing Tools

The Transcendence Asset Generator integrates with:

- **AssetMakerAI.ps1**: AI-powered generation
- **MultiAssetGenerator.ps1**: Cross-game asset generation
- **AssetGeneratorControlRoom.ps1**: GUI monitoring

### Example: Using with Control Room

```powershell
.\TranscendenceAssetGenerator.ps1 `
    -AssetType Ship `
    -AssetName "MyShip" `
    -UseAI `
    -LaunchControlRoom
```

---

## Best Practices

1. **Always use 120 facings** for ships (required for smooth rotation)
2. **Use High quality** for production mods
3. **Generate hero images** for ship selection screens
4. **Create proper masks** for transparency
5. **Test assets in-game** before finalizing
6. **Use batch generation** for large mods
7. **Keep original source files** for future edits

---

## File Naming Conventions

- **Ships**: `ShipName.jpg` (spritesheet), `ShipNameLarge.jpg` (hero)
- **Weapons**: `WeaponName_icon.png`
- **Items**: `ItemName_icon.png`
- **Projectiles**: `ProjectileName_projectile.png`
- **Spritesheets**: `ResourceName_spritesheet.png`

---

*Last Updated: 2025-01-XX*

