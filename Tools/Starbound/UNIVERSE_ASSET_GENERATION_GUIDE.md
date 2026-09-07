# Universe System Asset Generation Guide

Generate assets for the universe generation system including portals, star system icons, and planet icons.

## Quick Start

```powershell
# Generate all universe assets
.\GenerateUniverseAssets.ps1

# Use C++ backend for better quality
.\GenerateUniverseAssets.ps1 -UseCppBackend

# Or generate everything including universe assets
.\GenerateAllModSprites.ps1 -OllamaModel "codellama:7b-instruct"
```

## What Gets Generated

### Portal Assets (6 portals × 2 assets = 12 assets)

**Portal Types:**
1. **portal_reflective** - Reflective portal with shimmering surface
2. **portal_wormhole** - Wormhole portal with void energy
3. **portal_arcane** - Arcane portal with magical energy
4. **portal_void** - Void portal with dark energy
5. **portal_quantum** - Quantum portal with reality-bending effects
6. **portal_temporal** - Temporal portal with time distortion

**Each portal generates:**
- Portal entity sprite (ItemSprite)
- Portal activation animation (AnimationSprite, 8 frames)

### Star System Icons (7 icons)

1. **star_normal** - Normal star icon
2. **star_arcane** - Arcane star icon
3. **star_void** - Void star icon
4. **star_quantum** - Quantum star icon
5. **star_temporal** - Temporal star icon
6. **star_chaos** - Chaos star icon
7. **star_order** - Order star icon

### Planet Icons (7 icons)

1. **planet_normal** - Normal planet icon
2. **planet_arcane_forest** - Arcane forest planet icon
3. **planet_void_wastes** - Void wastes planet icon
4. **planet_quantum_plains** - Quantum plains planet icon
5. **planet_temporal_mountains** - Temporal mountains planet icon
6. **planet_chaos_swamps** - Chaos swamps planet icon
7. **planet_order_gardens** - Order gardens planet icon

## Total: ~26 Assets

## Output Structure

```
assets/
├── items/
│   └── sprites/
│       ├── portal_reflective.png
│       ├── portal_wormhole.png
│       ├── portal_arcane.png
│       └── ... (all portal sprites)
├── animations/
│   ├── portal_reflective_animation/
│   │   ├── portal_reflective_animation.png
│   │   ├── portal_reflective_animation.animation
│   │   └── portal_reflective_animation.frames
│   └── ... (all portal animations)
└── interface/
    └── icons/
        ├── star_normal.png
        ├── star_arcane.png
        ├── planet_normal.png
        └── ... (all star/planet icons)
```

## Portal Types

### Reflective Portal
- **Visual**: Shimmering surface, mirror-like appearance
- **Use**: Standard portal connections
- **Animation**: Smooth opening, reflective surface shimmer

### Wormhole Portal
- **Visual**: Swirling void energy, dark center
- **Use**: Long-distance travel
- **Animation**: Void energy swirling, gravitational distortion

### Arcane Portal
- **Visual**: Purple magical energy, runic patterns
- **Use**: Magical system connections
- **Animation**: Runic patterns appearing, magical energy swirling

### Void Portal
- **Visual**: Dark energy, void corruption
- **Use**: Void system connections
- **Animation**: Void corruption spreading, shadowy appearance

### Quantum Portal
- **Visual**: Reality-bending effects, shimmering
- **Use**: Quantum system connections
- **Animation**: Reality distortion, quantum instability effects

### Temporal Portal
- **Visual**: Time distortion effects, clockwork patterns
- **Use**: Temporal system connections
- **Animation**: Time distortion, clockwork patterns rotating

## Integration

### Portal Entity Definition

After generating assets, create portal entity definitions:

```json
{
  "type": "portal",
  "name": "Reflective Portal",
  "asset": "/items/sprites/portal_reflective.png",
  "animation": "/animations/portal_reflective_animation/portal_reflective_animation.animation",
  "behavior": "reflective",
  "cooldown": 5.0
}
```

### Star System Configuration

Reference star icons in system configurations:

```json
{
  "id": "arcane_system",
  "name": "Arcane Star System",
  "starType": "arcane",
  "icon": "/interface/icons/star_arcane.png",
  "planets": [
    {
      "id": "arcane_forest_planet",
      "icon": "/interface/icons/planet_arcane_forest.png"
    }
  ]
}
```

### Portal Entry Configuration

Reference portal assets in portal entries:

```json
{
  "from": "system_a",
  "to": "system_b",
  "type": "reflective",
  "asset": "/items/sprites/portal_reflective.png",
  "particleEffect": "/particles/portal_reflective.particle",
  "soundEffect": "/sfx/portals/portal_activate.ogg"
}
```

## Workflow

### Step 1: Generate Assets

```powershell
.\GenerateUniverseAssets.ps1 -OllamaModel "codellama:7b-instruct"
```

### Step 2: Create Portal Entities

Create portal entity definitions in `objects/portals/` directory.

### Step 3: Update System Configurations

Update star system configurations to reference generated icons.

### Step 4: Create Portal Entries

Create portal entries in universe configuration files.

### Step 5: Test in Game

Load the mod and verify portals and star systems appear correctly.

## Advanced Options

### Custom Portal Types

Edit `GenerateUniverseAssets.ps1` to add custom portal types:

```powershell
@{
    Id = "portal_custom"
    Name = "Custom Portal"
    Description = "Custom portal description"
    Type = "custom"
}
```

### Custom Star Types

Add custom star types to the `$starTypes` array.

### Custom Planet Types

Add custom planet types to the `$planetTypes` array.

## Tips

1. **Portal animations**: Use 8 frames for smooth portal opening
2. **Icon size**: Keep icons at 32x32 for UI consistency
3. **Portal sprites**: Use 64x64 or larger for entity sprites
4. **Color themes**: Match portal colors to their types
5. **Animation timing**: 0.8s cycle works well for portal animations

## Troubleshooting

### Portals Not Appearing

- Check portal entity definitions reference correct asset paths
- Verify animation files are in correct location
- Check portal entry configurations

### Icons Not Showing

- Verify icon paths in system configurations
- Check icon files are in `assets/interface/icons/`
- Ensure icon size is 32x32

### Animations Not Playing

- Check `.animation` file references correct PNG
- Verify `.frames` file has correct dimensions
- Ensure animation cycle timing is appropriate

---

*Part of the Starbound Ollama Asset Generator suite*
