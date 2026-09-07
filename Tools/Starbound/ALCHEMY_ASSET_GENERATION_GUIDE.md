# Alchemy System Asset Generation Guide

Generate assets for the alchemy system including ingredient icons, plant sprites, reaction effects, and alchemy stations.

## Quick Start

```powershell
# Generate all alchemy assets
.\GenerateAlchemyAssets.ps1

# Use C++ backend for better quality
.\GenerateAlchemyAssets.ps1 -UseCppBackend

# Or generate everything including alchemy assets
.\GenerateAllModSprites.ps1 -OllamaModel "codellama:7b-instruct"
```

## What Gets Generated

### Alchemy Ingredient Icons (12 icons)

1. **ingredient_metal** - Metal ingredient icon
2. **ingredient_organic** - Organic ingredient icon
3. **ingredient_crystal** - Crystal ingredient icon
4. **ingredient_gem** - Gem ingredient icon
5. **ingredient_liquid** - Liquid ingredient icon
6. **ingredient_gas** - Gas ingredient icon
7. **ingredient_acidic** - Acidic ingredient icon
8. **ingredient_magical** - Magical ingredient icon
9. **ingredient_bio_ooze** - Bio ooze ingredient icon
10. **ingredient_mutagene** - Mutagene ingredient icon
11. **ingredient_quantum_fluid** - Quantum fluid ingredient icon
12. **ingredient_particle_destabilizer** - Particle destabilizer icon

### Plant Sprites (5 sprites)

1. **plant_leaf** - Plant leaf sprite
2. **plant_growing** - Growing plant sprite
3. **plant_mature** - Mature plant sprite
4. **plant_dead** - Dead plant sprite
5. **plant_fibre** - Plant fibre sprite

### Reaction Effect Particles (8 effects)

1. **reaction_rust** - Rust reaction effect
2. **reaction_combustion** - Combustion reaction effect
3. **reaction_crystallization** - Crystallization reaction effect
4. **reaction_dissolution** - Dissolution reaction effect
5. **reaction_plant_growth** - Plant growth reaction effect
6. **reaction_particle_destabilization** - Particle destabilization effect
7. **reaction_super_fertilizer** - Super fertilizer reaction effect
8. **reaction_unstable_growth** - Unstable growth reaction effect

### Alchemy Station Sprites (3 sprites)

1. **alchemy_workbench** - Alchemy workbench sprite
2. **alchemy_cauldron** - Alchemy cauldron sprite
3. **alchemy_mortar_pestle** - Mortar and pestle sprite

## Total: ~28 Assets

## Output Structure

```
assets/
├── interface/
│   └── icons/
│       └── alchemy/
│           ├── ingredient_metal.png
│           ├── ingredient_organic.png
│           └── ... (all ingredient icons)
├── items/
│   └── sprites/
│       └── plants/
│           ├── plant_leaf.png
│           ├── plant_growing.png
│           └── ... (all plant sprites)
├── particles/
│   └── alchemy/
│       ├── reaction_rust.particle
│       ├── reaction_combustion.particle
│       └── ... (all reaction effects)
└── objects/
    └── alchemy/
        ├── alchemy_workbench.png
        ├── alchemy_cauldron.png
        └── ... (all station sprites)
```

## Integration

### Ingredient Icons

Reference ingredient icons in ingredient definitions:

```lua
local ingredient = engine.createIngredient({
    id = "metal_ingredient",
    icon = "/interface/icons/alchemy/ingredient_metal.png",
    tags = {"metal", "solid"},
    materialType = "metal"
})
```

### Plant Sprites

Use plant sprites for plant growth system:

```lua
local plant = engine.createPlant({
    id = "growing_plant",
    sprite = "/items/sprites/plants/plant_growing.png",
    growthStage = "growing"
})
```

### Reaction Effects

Attach reaction effects to alchemy reactions:

```lua
local reaction = engine.createReaction({
    id = "rust_reaction",
    inputs = {"metal", "water", "oxygen"},
    outputs = {"rust"},
    effect = "/particles/alchemy/reaction_rust.particle"
})
```

### Alchemy Stations

Create alchemy station objects:

```json
{
  "itemName": "alchemy_workbench",
  "shortdescription": "Alchemy Workbench",
  "description": "A workbench for alchemical crafting",
  "category": "crafting",
  "inventoryIcon": "alchemy_workbench.png",
  "object": {
    "image": "/objects/alchemy/alchemy_workbench.png"
  }
}
```

## Ingredient Types

### Material Types

| Type | Visual Style |
|------|-------------|
| Metal | Metallic appearance, gray/silver colors |
| Organic | Plant-based appearance, green/brown colors |
| Crystal | Crystalline structure, clear/sparkling |
| Gem | Faceted gem appearance, colorful |

### Phase Types

| Phase | Visual Style |
|-------|-------------|
| Solid | Solid appearance, defined shape |
| Liquid | Fluid appearance, blue/clear colors |
| Gas | Gaseous appearance, wispy, transparent |
| Plasma | Energy appearance, glowing |

### Special Ingredients

| Ingredient | Visual Style |
|-----------|-------------|
| Bio Ooze | Organic slime, green/brown colors |
| Mutagene | Unstable appearance, purple/green colors |
| Quantum Fluid | Reality-bending appearance, shimmering |
| Particle Destabilizer | Unstable energy, chaotic appearance |

## Reaction Types

### Rust Reaction
- **Visual**: Orange/brown rust particles, corrosion
- **Use**: Metal + Water + Oxygen reactions

### Combustion Reaction
- **Visual**: Fire explosion, red/orange flames
- **Use**: Combustible material reactions

### Crystallization Reaction
- **Visual**: Crystal formation, sparkling particles
- **Use**: Crystal growth reactions

### Plant Growth Reaction
- **Visual**: Green growth particles, organic
- **Use**: Plant growth boost reactions

## Workflow

### Step 1: Generate Assets

```powershell
.\GenerateAlchemyAssets.ps1 -OllamaModel "codellama:7b-instruct"
```

### Step 2: Create Ingredient Definitions

Create ingredient definitions with icon references.

### Step 3: Set Up Plant System

Configure plant growth system with plant sprites.

### Step 4: Configure Reactions

Set up alchemy reactions with effect particles.

### Step 5: Create Stations

Create alchemy station objects.

### Step 6: Test in Game

Load the mod and test alchemy system in-game.

## Advanced Options

### Custom Ingredients

Edit `GenerateAlchemyAssets.ps1` to add custom ingredient types:

```powershell
@{
    Id = "custom_ingredient"
    Name = "Custom Ingredient"
    Description = "Custom ingredient description"
}
```

### Custom Reactions

Add custom reaction effects to the `$reactionEffects` array.

### Custom Plants

Add custom plant sprites to the `$plantSprites` array.

## Tips

1. **Icon size**: Keep icons at 32x32 for UI consistency
2. **Plant sprites**: Use 32x32 or 48x48 for plant sprites
3. **Reaction effects**: Create distinct effects for each reaction type
4. **Station sprites**: Use larger sprites (64x64+) for stations
5. **Material themes**: Match visual style to material properties

## Troubleshooting

### Ingredients Not Appearing

- Check ingredient definitions reference correct icon paths
- Verify icons are in `assets/interface/icons/alchemy/`
- Check ingredient system is initialized

### Plants Not Growing

- Verify plant sprites are in correct location
- Check plant growth system configuration
- Ensure plant parameters are loaded

### Reactions Not Showing Effects

- Verify particle files are in `assets/particles/alchemy/`
- Check reaction effect paths in reaction definitions
- Ensure particle system is initialized

---

*Part of the Starbound Ollama Asset Generator suite*
