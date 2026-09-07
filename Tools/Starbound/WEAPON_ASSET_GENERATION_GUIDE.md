# Weapon System Asset Generation Guide

Generate assets for weapon systems including crossbow bolts, impact effects, trail effects, and animations.

## Quick Start

```powershell
# Generate all weapon assets
.\GenerateWeaponAssets.ps1

# Use C++ backend for better quality
.\GenerateWeaponAssets.ps1 -UseCppBackend

# Or generate everything including weapon assets
.\GenerateAllModSprites.ps1 -OllamaModel "codellama:7b-instruct"
```

## What Gets Generated

### Crossbow Bolt Projectiles (9 projectiles)

1. **bolt_standard** - Standard crossbow bolt
2. **bolt_explosive** - Explosive crossbow bolt
3. **bolt_piercing** - Piercing crossbow bolt
4. **bolt_homing** - Homing crossbow bolt
5. **bolt_spell** - Spell-loaded crossbow bolt
6. **bolt_poison** - Poison crossbow bolt
7. **bolt_fire** - Fire crossbow bolt
8. **bolt_ice** - Ice crossbow bolt
9. **bolt_lightning** - Lightning crossbow bolt

### Bolt Impact Effects (8 effects)

1. **bolt_impact_standard** - Standard bolt impact
2. **bolt_impact_explosive** - Explosive bolt impact
3. **bolt_impact_piercing** - Piercing bolt impact
4. **bolt_impact_spell** - Spell bolt impact
5. **bolt_impact_poison** - Poison bolt impact
6. **bolt_impact_fire** - Fire bolt impact
7. **bolt_impact_ice** - Ice bolt impact
8. **bolt_impact_lightning** - Lightning bolt impact

### Bolt Trail Effects (6 effects)

1. **bolt_trail_standard** - Standard bolt trail
2. **bolt_trail_explosive** - Explosive bolt trail
3. **bolt_trail_spell** - Spell bolt trail
4. **bolt_trail_fire** - Fire bolt trail
5. **bolt_trail_ice** - Ice bolt trail
6. **bolt_trail_lightning** - Lightning bolt trail

### Bolt Animations (3 animations)

1. **bolt_spin** - Bolt spinning animation (8 frames, 0.3s)
2. **bolt_glow** - Bolt glow animation (6 frames, 0.5s)
3. **bolt_spark** - Bolt spark animation (12 frames, 0.4s)

### Weapon Icons (2 icons)

1. **crossbow_icon** - Crossbow weapon icon
2. **bolt_icon** - Crossbow bolt icon

## Total: ~28 Assets

## Output Structure

```
assets/
├── projectiles/
│   └── bolts/
│       ├── bolt_standard.png
│       ├── bolt_explosive.png
│       └── ... (all bolt projectiles)
├── particles/
│   └── bolts/
│       ├── impact/
│       │   ├── bolt_impact_standard.particle
│       │   ├── bolt_impact_explosive.particle
│       │   └── ... (all impact effects)
│       └── trail/
│           ├── bolt_trail_standard.particle
│           ├── bolt_trail_explosive.particle
│           └── ... (all trail effects)
├── animations/
│   └── bolts/
│       ├── bolt_spin/
│       │   ├── bolt_spin.png
│       │   ├── bolt_spin.animation
│       │   └── bolt_spin.frames
│       └── ... (all bolt animations)
└── interface/
    └── icons/
        └── weapons/
            ├── crossbow_icon.png
            └── bolt_icon.png
```

## Integration

### Bolt Definition

After generating assets, create bolt definitions:

```lua
local bolt = Crossbow.BoltDef()
bolt.id = "explosive_bolt"
bolt.meshPath = "/projectiles/bolts/bolt_explosive.png"
bolt.materialPath = "/textures/bolts/bolt_explosive_material.png"
bolt.speed = 30.0
bolt.lifetime = 3.0
bolt.behavior = "explosive"
bolt.impactEffect = "/particles/bolts/impact/bolt_impact_explosive.particle"
bolt.trailEffect = "/particles/bolts/trail/bolt_trail_explosive.particle"
bolt.useAnimation = true
bolt.animationName = "spin"
```

### Spawning Bolts

```lua
local boltId = Crossbow.spawn({
    x = 0, y = 0, z = 0,
    dx = 0, dy = 0, dz = 1
}, function(hit)
    print("Bolt hit at: " .. hit.position)
end)
```

## Bolt Types

### Standard Bolt
- **Visual**: Wooden shaft, metal tip
- **Use**: Basic damage
- **Impact**: Small impact, wood/metal particles

### Explosive Bolt
- **Visual**: Red/orange, explosive tip
- **Use**: Area damage
- **Impact**: Large explosion, fire and smoke

### Piercing Bolt
- **Visual**: Sharp metal tip
- **Use**: Armor penetration
- **Impact**: Sparks, metal fragments

### Homing Bolt
- **Visual**: Magical energy, glowing tip
- **Use**: Target tracking
- **Impact**: Magical explosion

### Spell Bolt
- **Visual**: Magical energy, purple/blue glow
- **Use**: Spell effects
- **Impact**: Magical explosion, spell effects

### Elemental Bolts
- **Fire**: Flaming tip, red/orange
- **Ice**: Frozen tip, blue/white
- **Lightning**: Electrical energy, yellow/white
- **Poison**: Toxic appearance, green

## Workflow

### Step 1: Generate Assets

```powershell
.\GenerateWeaponAssets.ps1 -OllamaModel "codellama:7b-instruct"
```

### Step 2: Create Bolt Definitions

Create bolt definitions with asset references.

### Step 3: Configure Effects

Set up impact and trail effects for each bolt type.

### Step 4: Test in Game

Load the mod and test bolts in-game.

## Advanced Options

### Custom Bolt Types

Edit `GenerateWeaponAssets.ps1` to add custom bolt types:

```powershell
@{
    Id = "custom_bolt"
    Name = "Custom Bolt"
    Description = "Custom bolt description"
}
```

### Custom Effects

Add custom impact or trail effects to the arrays.

### Custom Animations

Add custom bolt animations to the `$boltAnimations` array.

## Tips

1. **Bolt size**: Use 32x32 or 48x48 for bolt projectiles
2. **Animation frames**: 6-12 frames work well for bolt animations
3. **Animation timing**: Match animation cycle to bolt lifetime
4. **Impact effects**: Create distinct effects for each bolt type
5. **Trail effects**: Keep trail effects subtle for visibility

## Troubleshooting

### Bolts Not Appearing

- Check bolt definitions reference correct asset paths
- Verify projectiles are in `assets/projectiles/bolts/`
- Check mesh/material paths are correct

### Effects Not Playing

- Verify particle files are in correct location
- Check effect paths in bolt definitions
- Ensure particle system is initialized

### Animations Not Playing

- Check `.animation` file references correct PNG
- Verify `.frames` file has correct dimensions
- Ensure animation cycle timing is appropriate

---

*Part of the Starbound Ollama Asset Generator suite*
