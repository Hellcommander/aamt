# Asset Generation Batch Files

This document lists all available batch files for generating mech form and system assets. Run these when ready - AI generation takes time.

## Mech Form Asset Generators

### MagiTech 10-Form System (Master Scripts)
**IMPORTANT**: All mech forms are piloted vehicles with visible cockpits. Player is visible inside via alpha channel transparency.

- `GenerateMechCockpitAssets.bat` - **REQUIRED FIRST** - Generates cockpit frames, glass, and interiors for all forms
- `GenerateAllMechFormAssets.bat` - Generates all assets for all 10 mech forms:
  - Form icons (48x48 and 64x64)
  - Enter/exit VFX particles
  - Activate/deactivate sound effects
  - Calls individual form scripts if available
- `GenerateMechFormAnimations.bat` - Generates all 136-frame animation cycles for all forms:
  - Movement: idle, walk, run, jump, swim, dash, dodge, wall-slide, wall-jump (72 frames)
  - Magic: charge, orb-emerge, channel, cast, dissipate (34 frames)
  - Weapon: aim, fire, reload, holster (24 frames)
  - Form-specific: 6 additional frames per unique ability
- `GenerateFormWheelUI.bat` - Generates Form Wheel radial menu UI:
  - Wheel background and selection highlight
  - Slot number indicators (0-9)
  - UI sounds (open, hover, select, close)
  - Locked/disabled indicators

### Individual Form Scripts (Ready to Generate)
- `GenerateCentipedeFormAssets.bat` - Centipede Form (slot 2, terrain control)
- `GenerateBladeCycloneFormAssets.bat` - Blade Cyclone Form (slot 5, area DPS)
- `GenerateTentacledHorrorFormAssets.bat` - Tentacled Horror Form (additional)
- `GenerateRaptorFormAssets.bat` - Raptor Form (additional)

### Starbound Lore-Themed Forms
- `GenerateStarboundLoreFormsAssets.bat` - **Generates all 7 Starbound race-themed forms:**
  - Apex Laboratory Mech (scientific/tech)
  - Avian Temple Guardian (temple/holy)
  - Floran Grower Mech (organic/nature)
  - Glitch Knight Mech (medieval/steampunk)
  - Hylotl Zen Mech (aquatic/zen)
  - Novakid Starburst Mech (energy/star)
  - Human Military Mech (military/industrial)

### Quadraped Mech Forms
- `GenerateQuadrapedFormsAssets.bat` - **Generates all 5 quadraped (four-legged) forms:**
  - Wolf Pack Mech (pack hunter, high mobility)
  - Tank Beast Mech (heavy defensive tank)
  - Scorpion Strike Mech (venom, burrow, ambush)
  - Saber Cat Mech (agile predator, ice abilities)
  - Spider Weaver Mech (web control, traps, support)

### Abnormal Segmented Forms
- `GenerateAbnormalFormsAssets.bat` - **Generates all 7 abnormal segmented forms:**
  - Coil Serpent (serpentine ambush, constrict/stun)
  - Crystal Spire (stationary support, crystal fields)
  - Rift Wyrm (teleport skirmisher, void blinks)
  - Echo Walker (ECM sensor, scramble controls)
  - Bloom Harvester (resource harvester, rooted healing)
  - Fracture Colossus (boss siege, fragmenting on damage)
  - Phase Swarm (swarm controller, detachable drones)

### Horror-Themed Forms
- `GenerateHorrorFormsAssets.bat` - **Generates all 5 horror-themed forms:**
  - Eldritch Abomination (cosmic horror, sanity drain)
  - Necrotic Reaper (undead, life drain, raise dead)
  - Parasitic Nightmare (infestation, parasites, corruption)
  - Flesh Weaver (body horror, shapeshift, regeneration)
  - Phantom Shroud (spectral, terror, possession)
  - **WARNING**: Generates disturbing horror imagery

## Modular Systems

### Hydra Chassis Modular Mech System
- `GenerateHydraChassisAssets.bat` - Generates:
  - Base frame concept art
  - 17 modular component sprites (head, mid, tail, legs, etc.)
  - Module icons (64x64)
  - Assembly previews for common combinations

## Alchemical Systems

### Dynamic Potion Ammo System
- `GenerateDynamicPotionAmmoAssets.bat` - Generates:
  - Reagent icons (64x64) for all registered reagents
  - Container sprites (glass vial, metal flask, powder jar, etc.)
  - Ammo sprites (potion grenades, alchemical spheres, container shells)
  - Reaction VFX particles for all reaction types
  - Crafting station sprites (alchemy table, magical forge, etc.)

### Individual Component Generators
- `GenerateReagentIcons.bat` - Generates icons for all reagents (64x64)
- `GenerateReactionVFX.bat` - Generates particle VFX for all reaction types
- `GenerateCraftingStationAssets.bat` - Generates sprites and icons for crafting stations

## Usage

### Basic Usage
```batch
cd "D:\games\Steam\steamapps\common\Transcendence\Tools\Starbound"
.\GenerateRaptorFormAssets.bat
```

### With Options
```batch
.\GenerateRaptorFormAssets.bat -SkipExisting
.\GenerateRaptorFormAssets.bat -UseCppBackend $false
```

### Quick Generation (Skip Existing Assets)
```batch
.\GenerateRaptorFormAssets.bat -SkipExisting
```

## Generation Time Estimates

- **Form Icon**: ~10-15 seconds per icon
- **VFX Particles**: ~15-20 seconds per particle
- **Sound Effects**: ~10-15 seconds per sound
- **Animation Sprites**: ~20-30 seconds per animation
- **Module Sprites**: ~20-30 seconds per module
- **Reagent Icons**: ~10-15 seconds per icon
- **Container Sprites**: ~15-20 seconds per sprite
- **Ammo Sprites**: ~15-20 seconds per sprite
- **Reaction VFX**: ~20-25 seconds per reaction
- **Crafting Station Sprites**: ~20-25 seconds per station
- **Full Form**: ~5-10 minutes total
- **Hydra Chassis (all modules)**: ~15-20 minutes total
- **Dynamic Potion Ammo System (all assets)**: ~20-30 minutes total

## Notes

- All scripts default to using C++ backend (`-UseCppBackend $true`)
- Use `-SkipExisting` to skip assets that already exist
- Scripts will create necessary directory structures automatically
- Check `ASSET_GENERATION_TODOS.md` for detailed status

## Batch Generation

### Generate All Pending Forms
```batch
.\GenerateTentacledHorrorFormAssets.bat -SkipExisting
.\GenerateBladeCycloneFormAssets.bat -SkipExisting
.\GenerateRaptorFormAssets.bat -SkipExisting
.\GenerateHydraChassisAssets.bat -SkipExisting
```

### Generate All Alchemical System Assets
```batch
.\GenerateReagentIcons.bat -SkipExisting
.\GenerateReactionVFX.bat -SkipExisting
.\GenerateCraftingStationAssets.bat -SkipExisting
.\GenerateDynamicPotionAmmoAssets.bat -SkipExisting
```

### Generate All Mech Form Assets
```batch
# IMPORTANT: Generate cockpits first (player visibility via alpha channels)
.\GenerateMechCockpitAssets.bat -SkipExisting

# Then generate form assets (includes cockpit in animations)
.\GenerateAllMechFormAssets.bat -SkipExisting
.\GenerateMechFormAnimations.bat -SkipExisting
.\GenerateFormWheelUI.bat -SkipExisting
```

### Generate Mech Variant Sets (Cohesive Visual Styles)
```batch
# Generate specific variant
.\GenerateMechVariantSet.bat -VariantName "voidCorrupted" -SkipExisting
.\GenerateMechVariantSet.bat -VariantName "crystalInfused" -SkipExisting
.\GenerateMechVariantSet.bat -VariantName "infernal" -SkipExisting
.\GenerateMechVariantSet.bat -VariantName "arctic" -SkipExisting
.\GenerateMechVariantSet.bat -VariantName "neon" -SkipExisting

# Generate all predefined variants
.\GenerateAllMechVariants.bat -SkipExisting

# Generate custom variant
.\GenerateCustomMechVariant.bat -VariantName "myVariant" -VariantDisplayName "My Custom Variant" -PrimaryColor 100,150,200 -AccentColor 200,250,255 -Aesthetic "cyber_magitech"
```
