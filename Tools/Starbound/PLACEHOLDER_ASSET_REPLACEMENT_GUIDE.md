# Placeholder Asset Replacement Guide

This guide documents the process of replacing placeholder assets with real generated assets throughout the codebase.

## Quick Start

```powershell
# Generate all placeholder replacement assets
.\GeneratePlaceholderAssets.ps1

# Use C++ backend for better quality
.\GeneratePlaceholderAssets.ps1 -UseCppBackend

# Or generate everything at once
.\GenerateAllModSprites.ps1 -OllamaModel "codellama:7b-instruct"
```

## What Gets Generated

### Enchantment Table Interface Assets (13 assets)

1. **magi_tech_item_placeholder** - Item placeholder icon (150x150)
2. **magi_tech_enchantment_table_background** - Enchantment table background (1000x700)
3. **magi_tech_enchant_button** - Enchant button (260x40)
4. **magi_tech_enchant_button_hover** - Enchant button hover state
5. **magi_tech_enchant_button_pressed** - Enchant button pressed state
6. **magi_tech_remove_button** - Remove button (260x40)
7. **magi_tech_remove_button_hover** - Remove button hover state
8. **magi_tech_remove_button_pressed** - Remove button pressed state
9. **magi_tech_filter_button** - Filter button (180x25)
10. **magi_tech_filter_button_hover** - Filter button hover state
11. **magi_tech_close_button** - Close button (40x40)
12. **magi_tech_close_button_hover** - Close button hover state
13. **magi_tech_enchantment_icon** - Enchantment table icon (32x32)

### Crossbow Generator Assets (8 assets)

1. **crossbow_basic_sprite** - Basic crossbow sprite (64x64)
2. **crossbow_basic_icon** - Basic crossbow icon (32x32)
3. **crossbow_advanced_sprite** - Advanced crossbow sprite (64x64)
4. **crossbow_advanced_icon** - Advanced crossbow icon (32x32)
5. **bolt_basic_sprite** - Basic bolt sprite (32x32)
6. **bolt_basic_icon** - Basic bolt icon (32x32)
7. **arrow_basic_sprite** - Basic arrow sprite (32x32)
8. **arrow_basic_icon** - Basic arrow icon (32x32)

### Flame Projectile Assets (6 assets)

1. **flame_noise_texture** - Flame noise texture (128x128)
2. **flame_gradient_texture** - Flame gradient texture (128x128)
3. **flame_merged_texture** - Flame merged texture (128x128)
4. **flame_ember_particle** - Flame ember particle effect (64x64)
5. **flame_trail_particle** - Flame trail particle effect (128x32)
6. **flame_smoke_particle** - Flame smoke particle effect (64x64)

### AI Art Generator Assets (2 assets)

1. **ai_art_placeholder** - AI art placeholder image (256x256)
2. **ai_art_default** - AI art default image (256x256)

### Visual QA System Assets (2 assets)

1. **qa_placeholder_image** - QA placeholder image (128x128)
2. **qa_reference_image** - QA reference image (128x128)

### GPU Interface Assets (2 assets)

1. **gpu_texture_placeholder** - GPU texture placeholder (64x64)
2. **gpu_audio_texture_placeholder** - GPU audio texture placeholder (64x64)

## Total: ~33 Assets

## Code Locations to Update

### Interface Assets

**File**: `interface/magi_tech_enchantment_table.config`
- Line 44: Update `magi_tech_item_placeholder.png` path
- Line 5: Update `magi_tech_enchantment_table_background.png` path
- Lines 166-168: Update enchant button paths
- Lines 179-181: Update remove button paths
- Lines 211-212, 223-224, 235-236, 247-248, 259-260: Update filter button paths
- Lines 312-313: Update close button path
- Line 324: Update enchantment icon path

### Crossbow Generator Assets

**File**: `cpp_backend/agents/GeneratorAgent/CrossbowAssetGenerator.cpp`
- Line 50-52: Update sprite generation (currently placeholder)
- Line 374: Update placeholder sprite file creation
- Line 414: Update placeholder icon creation

### Flame Projectile Assets

**File**: `cpp_backend/agents/GeneratorAgent/FlameProjectileGenerators.cpp`
- Lines 155-157: Replace placeholder noise texture generation
- Lines 164-166: Replace placeholder gradient texture generation
- Lines 171-173: Replace placeholder texture merging
- Lines 193-194: Replace placeholder ember particle generation
- Lines 213-214: Replace placeholder trail particle generation
- Lines 220-221: Replace placeholder smoke particle generation

### AI Art Generator Assets

**File**: `cpp_backend/agents/GeneratorAgent/AIArtGenerator.cpp`
- Lines 391-392: Replace placeholder image creation

### Visual QA System Assets

**File**: `cpp_backend/agents/GeneratorAgent/visual_qa/VisualQASystem.cpp`
- Line 197: Replace placeholder image creation

### GPU Interface Assets

**File**: `cpp_backend/agents/GeneratorAgent/GPUDeviceInterface.cpp`
- Line 61: Replace placeholder texture creation

**File**: `cpp_backend/agents/GeneratorAgent/GPUAudioInterface.cpp`
- Lines 178-179: Replace placeholder GPU texture creation
- Lines 211-212: Replace placeholder GPU texture update

## Output Structure

```
interface/
├── magi_tech_item_placeholder.png
├── magi_tech_enchantment_table_background.png
├── magi_tech_enchant_button.png
├── magi_tech_enchant_button_hover.png
├── magi_tech_enchant_button_pressed.png
├── magi_tech_remove_button.png
├── magi_tech_remove_button_hover.png
├── magi_tech_remove_button_pressed.png
├── magi_tech_filter_button.png
├── magi_tech_filter_button_hover.png
├── magi_tech_close_button.png
├── magi_tech_close_button_hover.png
└── magi_tech_enchantment_icon.png

assets/
├── weapons/
│   └── crossbow/
│       ├── crossbow_basic_sprite.png
│       ├── crossbow_basic_icon.png
│       ├── crossbow_advanced_sprite.png
│       ├── crossbow_advanced_icon.png
│       ├── bolt_basic_sprite.png
│       ├── bolt_basic_icon.png
│       ├── arrow_basic_sprite.png
│       └── arrow_basic_icon.png
├── projectiles/
│   └── flame/
│       ├── flame_noise_texture.png
│       ├── flame_gradient_texture.png
│       ├── flame_merged_texture.png
│       ├── flame_ember_particle.particle
│       ├── flame_trail_particle.particle
│       └── flame_smoke_particle.particle
├── ai_art/
│   ├── ai_art_placeholder.png
│   └── ai_art_default.png
├── qa/
│   ├── qa_placeholder_image.png
│   └── qa_reference_image.png
└── gpu/
    ├── gpu_texture_placeholder.png
    └── gpu_audio_texture_placeholder.png
```

## Integration Steps

### Step 1: Generate Assets

```powershell
.\GeneratePlaceholderAssets.ps1 -OllamaModel "codellama:7b-instruct"
```

### Step 2: Update Code References

Update all code files that reference placeholder assets to use the new generated assets.

### Step 3: Remove Placeholder Comments

Remove or update placeholder comments in the code to reflect that real assets are now being used.

### Step 4: Test in Game

Load the mod and test all systems that use these assets to ensure they work correctly.

## Tips

1. **Interface assets**: Ensure button states (hover, pressed) are visually distinct
2. **Crossbow assets**: Match the style of existing Starbound weapons
3. **Flame assets**: Keep particle effects performant and visually appealing
4. **AI art assets**: Use as fallbacks when AI generation fails
5. **QA assets**: Use for visual quality assurance testing
6. **GPU assets**: Keep textures optimized for GPU usage

## Troubleshooting

### Assets Not Loading

- Check asset paths in code match generated asset locations
- Verify assets are in the correct directories
- Ensure file extensions match (.png, .particle, etc.)

### Interface Not Displaying

- Check interface config file paths
- Verify all button state assets exist
- Ensure background texture is correct size

### Generators Not Working

- Check generator code references updated asset paths
- Verify asset generation functions are called correctly
- Ensure placeholder comments are removed

---

*Part of the Starbound Ollama Asset Generator suite*
