# Acid/Liquid Projectile Generator Asset Generation Guide

Generate assets for the Acid/Liquid Projectile Generator system including projectiles, impact effects, splatters, decals, and bubble effects.

## Quick Start

```powershell
# Generate all acid/liquid assets
.\GenerateAcidLiquidAssets.ps1

# Use C++ backend for better quality
.\GenerateAcidLiquidAssets.ps1 -UseCppBackend

# Or generate everything including acid/liquid assets
.\GenerateAllModSprites.ps1 -OllamaModel "codellama:7b-instruct"
```

## What Gets Generated

### Acid Projectile Sprites (4 sprites)

1. **acid_projectile_basic** - Basic acid projectile
2. **acid_projectile_strong** - Strong acid projectile
3. **acid_projectile_corrosive** - Corrosive acid projectile
4. **acid_projectile_spray** - Acid spray projectile

### Liquid Droplet Sprites (5 sprites)

1. **liquid_droplet_water** - Water droplet
2. **liquid_droplet_oil** - Oil droplet
3. **liquid_droplet_poison** - Poison droplet
4. **liquid_droplet_healing** - Healing droplet
5. **liquid_droplet_magma** - Magma droplet

### Acid Impact Effects (4 effects)

1. **acid_impact_basic** - Basic acid impact
2. **acid_impact_strong** - Strong acid impact
3. **acid_impact_corrosive** - Corrosive acid impact
4. **acid_impact_spray** - Acid spray impact

### Liquid Splatter Effects (4 effects)

1. **liquid_splatter_water** - Water splatter
2. **liquid_splatter_oil** - Oil splatter
3. **liquid_splatter_poison** - Poison splatter
4. **liquid_splatter_magma** - Magma splatter

### Corrosive Decals (3 decals)

1. **corrosive_decal_basic** - Basic corrosive decal
2. **corrosive_decal_strong** - Strong corrosive decal
3. **corrosive_decal_severe** - Severe corrosive decal

### Bubble Particle Effects (4 effects)

1. **bubble_effect_acid** - Acid bubble effect
2. **bubble_effect_water** - Water bubble effect
3. **bubble_effect_oil** - Oil bubble effect
4. **bubble_effect_poison** - Poison bubble effect

## Total: ~24 Assets

## Output Structure

```
assets/
└── projectiles/
    ├── acid/
    │   ├── acid_projectile_basic.png
    │   ├── acid_projectile_strong.png
    │   ├── acid_projectile_corrosive.png
    │   ├── acid_projectile_spray.png
    │   ├── acid_impact_basic.particle
    │   ├── acid_impact_strong.particle
    │   ├── acid_impact_corrosive.particle
    │   ├── acid_impact_spray.particle
    │   ├── corrosive_decal_basic.png
    │   ├── corrosive_decal_strong.png
    │   ├── corrosive_decal_severe.png
    │   ├── bubble_effect_acid.particle
    │   ├── bubble_effect_water.particle
    │   ├── bubble_effect_oil.particle
    │   └── bubble_effect_poison.particle
    └── liquid/
        ├── liquid_droplet_water.png
        ├── liquid_droplet_oil.png
        ├── liquid_droplet_poison.png
        ├── liquid_droplet_healing.png
        ├── liquid_droplet_magma.png
        ├── liquid_splatter_water.particle
        ├── liquid_splatter_oil.particle
        ├── liquid_splatter_poison.particle
        └── liquid_splatter_magma.particle
```

## Integration

### Acid Projectiles

```lua
-- Create acid projectile
local projectile = AcidLiquidProjectileGenerator:createAcidProjectile({
    type = "basic",
    sprite = "/projectiles/acid/acid_projectile_basic.png",
    impactEffect = "/projectiles/acid/acid_impact_basic.particle",
    decal = "/projectiles/acid/corrosive_decal_basic.png"
})
```

### Liquid Droplets

```lua
-- Create liquid droplet
local droplet = AcidLiquidProjectileGenerator:createLiquidDroplet({
    type = "water",
    sprite = "/projectiles/liquid/liquid_droplet_water.png",
    splatterEffect = "/projectiles/liquid/liquid_splatter_water.particle"
})
```

### Impact Effects

```lua
-- Spawn acid impact effect
AcidLiquidProjectileGenerator:spawnImpactEffect(
    position,
    "/projectiles/acid/acid_impact_basic.particle",
    "/projectiles/acid/corrosive_decal_basic.png"
)
```

### Bubble Effects

```lua
-- Spawn bubble effect
AcidLiquidProjectileGenerator:spawnBubbleEffect(
    position,
    "/projectiles/acid/bubble_effect_acid.particle"
)
```

## Projectile Types

### Acid Projectiles
- **Basic**: Standard green toxic acid
- **Strong**: Dark green concentrated acid
- **Corrosive**: Yellow-green highly corrosive acid
- **Spray**: Multiple small acid droplets

### Liquid Droplets
- **Water**: Blue transparent water
- **Oil**: Dark brown/black viscous oil
- **Poison**: Purple toxic liquid
- **Healing**: Green healing liquid
- **Magma**: Red/orange molten magma

## Workflow

### Step 1: Generate Assets

```powershell
.\GenerateAcidLiquidAssets.ps1 -OllamaModel "codellama:7b-instruct"
```

### Step 2: Configure Projectiles

Configure acid/liquid projectiles with asset references.

### Step 3: Integrate Effects

Integrate impact effects, splatters, and decals.

### Step 4: Test in Game

Load the mod and test acid/liquid projectiles in-game.

## Advanced Options

### Custom Acid Types

Edit `GenerateAcidLiquidAssets.ps1` to add custom acid types:

```powershell
@{
    Id = "acid_projectile_custom"
    Name = "Custom Acid Projectile"
    Description = "Custom acid projectile description"
}
```

### Custom Liquid Types

Add custom liquid types to the `$liquidDroplets` array.

### Custom Decals

Add custom corrosive decals to the `$corrosiveDecals` array.

## Tips

1. **Projectile size**: Use 32x32 for projectiles
2. **Decal size**: Use 64x64 for decals
3. **Impact effects**: Create distinct effects for each type
4. **Splatter effects**: Make splatters look fluid and natural
5. **Bubble effects**: Use appropriate colors for each liquid type

## Troubleshooting

### Projectiles Not Appearing

- Check projectile definitions reference correct asset paths
- Verify sprites are in `assets/projectiles/acid/` or `assets/projectiles/liquid/`
- Check projectile system is initialized

### Effects Not Playing

- Verify particle files are in correct location
- Check effect paths in projectile definitions
- Ensure particle system is initialized

### Decals Not Rendering

- Check decal texture paths
- Verify decal system is initialized
- Ensure decal textures are in correct format

---

*Part of the Starbound Ollama Asset Generator suite*
