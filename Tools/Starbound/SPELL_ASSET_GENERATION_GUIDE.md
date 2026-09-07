# Spell System Asset Generation Guide

Generate assets for the spell system including icons, projectiles, animations, and particle effects.

## Quick Start

```powershell
# Generate all spell assets
.\GenerateSpellAssets.ps1

# Use C++ backend for better quality
.\GenerateSpellAssets.ps1 -UseCppBackend

# Or generate everything including spell assets
.\GenerateAllModSprites.ps1 -OllamaModel "codellama:7b-instruct"
```

## What Gets Generated

### Spell Icons (7 icons)

1. **fireBolt** - Fire bolt spell icon
2. **iceBolt** - Ice bolt spell icon
3. **lightningBolt** - Lightning bolt spell icon
4. **arcaneBolt** - Arcane bolt spell icon
5. **fireball** - Fireball spell icon
6. **iceStorm** - Ice storm spell icon
7. **plasmaBolt** - Plasma bolt spell icon

### Spell Projectiles (6 projectiles)

1. **fire_bolt_projectile** - Fire bolt projectile sprite
2. **ice_bolt_projectile** - Ice bolt projectile sprite
3. **lightning_bolt_projectile** - Lightning bolt projectile sprite
4. **arcane_bolt_projectile** - Arcane bolt projectile sprite
5. **fireball_projectile** - Fireball projectile sprite
6. **plasma_bolt_projectile** - Plasma bolt projectile sprite

### Spell Animations (5 animations)

1. **spell_rotate** - Rotation animation (8 frames, 0.5s)
2. **spell_spin** - Spin animation (8 frames, 0.4s)
3. **spell_electric** - Electric animation (12 frames, 0.3s)
4. **spell_float** - Float animation (6 frames, 0.8s)
5. **spell_pulse** - Pulse animation (8 frames, 0.6s)

### Impact Particle Effects (11 effects)

1. **fire_explosion** - Fire explosion effect
2. **ice_impact** - Ice impact effect
3. **lightning_impact** - Lightning impact effect
4. **arcane_explosion** - Arcane explosion effect
5. **plasma_explosion** - Plasma explosion effect
6. **fireBurst** - Fire burst effect
7. **iceBurst** - Ice burst effect
8. **lightningBurst** - Lightning burst effect
9. **arcaneBurst** - Arcane burst effect
10. **fireballExplosion** - Fireball explosion effect
11. **iceStorm** - Ice storm effect

### Trail Particle Effects (5 effects)

1. **fire_trail** - Fire trail effect
2. **ice_trail** - Ice trail effect
3. **lightning_trail** - Lightning trail effect
4. **arcane_trail** - Arcane trail effect
5. **plasma_trail** - Plasma trail effect

## Total: ~34 Assets

## Output Structure

```
assets/
├── interface/
│   └── icons/
│       └── spells/
│           ├── fireBolt.png
│           ├── iceBolt.png
│           └── ... (all spell icons)
├── projectiles/
│   └── spells/
│       ├── fire_bolt_projectile.png
│       ├── ice_bolt_projectile.png
│       └── ... (all projectile sprites)
├── animations/
│   └── spells/
│       ├── spell_rotate/
│       │   ├── spell_rotate.png
│       │   ├── spell_rotate.animation
│       │   └── spell_rotate.frames
│       └── ... (all spell animations)
└── particles/
    └── spells/
        ├── fire_explosion.particle
        ├── fire_trail.particle
        └── ... (all particle effects)
```

## Integration

### Spell Definition

After generating assets, create spell definitions:

```lua
-- Create fire bolt spell
local fireBolt = engine.createSpell({
    id = "fire_bolt",
    type = "projectile",
    sourceSprite = "/interface/icons/spells/fireBolt.png",
    speed = 25.0,
    lifetime = 2.0,
    impactEffect = "/particles/spells/fire_explosion.particle",
    trailEffect = "/particles/spells/fire_trail.particle",
    useAnimation = true,
    animationName = "rotate",
    animationSpeed = 2.0
})
```

### Dual Asset Spell

For dual asset spells (sprite + mesh):

```lua
local dualSpell = engine.createDualAssetSpell({
    id = "fire_bolt_dual",
    assetType = "sprite",
    spritePath = "/projectiles/spells/fire_bolt_projectile.png",
    useMeshExtrusion = true,
    meshThickness = 0.5,
    impactEffect = "/particles/spells/fire_explosion.particle"
})
```

### Spell Shape Integration

Apply shapes to spell projectiles:

```lua
local spell = engine.createSpell({
    id = "wave_spell",
    sourceSprite = "/interface/icons/spells/arcaneBolt.png",
    useShapeDeformation = true,
    shapeProfile = "wave",
    amplitude = 2.0,
    frequency = 3.0
})
```

## Element Types

### Fire
- **Colors**: Red/orange
- **Effects**: Flames, explosions, bursts
- **Icons**: Flame symbols
- **Projectiles**: Trailing flames

### Ice
- **Colors**: Blue/white
- **Effects**: Frost, shattering, blizzards
- **Icons**: Ice crystal symbols
- **Projectiles**: Frost particles

### Lightning
- **Colors**: Yellow/white
- **Effects**: Electrical arcs, sparks
- **Icons**: Lightning bolt symbols
- **Projectiles**: Electrical energy

### Arcane
- **Colors**: Purple
- **Effects**: Magical energy, swirling particles
- **Icons**: Magical symbols
- **Projectiles**: Magical energy

### Plasma
- **Colors**: Green/purple
- **Effects**: Plasma energy, energy bursts
- **Icons**: Plasma symbols
- **Projectiles**: Plasma effects

## Workflow

### Step 1: Generate Assets

```powershell
.\GenerateSpellAssets.ps1 -OllamaModel "codellama:7b-instruct"
```

### Step 2: Create Spell Definitions

Create spell definitions in Lua or JSON files.

### Step 3: Configure Spell System

Set up spell system configuration with asset paths.

### Step 4: Test in Game

Load the mod and test spells in-game.

## Advanced Options

### Custom Spell Types

Edit `GenerateSpellAssets.ps1` to add custom spell types:

```powershell
@{
    Id = "custom_spell"
    Name = "Custom Spell"
    Description = "Custom spell description"
}
```

### Custom Animations

Add custom animations to the `$spellAnimations` array.

### Custom Particle Effects

Add custom particle effects to `$impactEffects` or `$trailEffects` arrays.

## Tips

1. **Icon size**: Keep icons at 32x32 for UI consistency
2. **Projectile size**: Use 32x32 or 48x48 for projectiles
3. **Animation frames**: 6-12 frames work well for spell animations
4. **Animation timing**: Match animation cycle to spell lifetime
5. **Particle effects**: Create both impact and trail effects for each element

## Troubleshooting

### Spells Not Appearing

- Check spell definitions reference correct asset paths
- Verify icons are in `assets/interface/icons/spells/`
- Check projectile sprites are in `assets/projectiles/spells/`

### Animations Not Playing

- Check `.animation` file references correct PNG
- Verify `.frames` file has correct dimensions
- Ensure animation cycle timing is appropriate

### Particle Effects Not Working

- Verify particle files are in `assets/particles/spells/`
- Check particle effect paths in spell definitions
- Ensure particle system is initialized

---

*Part of the Starbound Ollama Asset Generator suite*
