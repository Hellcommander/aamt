# AlchemistBus System Asset Generation Guide

Generate visual assets for the AlchemistBus System including ingredient icons, phase indicators, elemental type icons, material type icons, reaction visual effects, grid reaction visuals, alchemy station UI elements, plant sprites, environmental condition indicators, reaction status indicators, and ingredient state indicators.

## Quick Start

```powershell
# Generate all AlchemistBus assets
.\GenerateAlchemistBusAssets.ps1

# Use C++ backend for better quality
.\GenerateAlchemistBusAssets.ps1 -UseCppBackend

# Or generate everything at once
.\GenerateAllModSprites.ps1 -OllamaModel "codellama:7b-instruct"
```

## What Gets Generated

### Ingredient Type Icons (6 icons)

1. **ingredient_basic** - Basic ingredient
2. **ingredient_crystal** - Crystal ingredient
3. **ingredient_organic** - Organic ingredient
4. **ingredient_metal** - Metal ingredient
5. **ingredient_gem** - Gem ingredient
6. **ingredient_catalyst** - Catalyst ingredient

### Phase Indicators (4 indicators)

1. **phase_solid** - Solid phase
2. **phase_liquid** - Liquid phase
3. **phase_gas** - Gas phase
4. **phase_plasma** - Plasma phase

### Elemental Type Icons (6 icons)

1. **element_fire** - Fire element
2. **element_water** - Water element
3. **element_earth** - Earth element
4. **element_air** - Air element
5. **element_void** - Void element
6. **element_neutral** - Neutral element

### Material Type Icons (6 icons)

1. **material_metal** - Metal material
2. **material_organic** - Organic material
3. **material_crystal** - Crystal material
4. **material_gem** - Gem material
5. **material_wood** - Wood material
6. **material_bone** - Bone material

### Reaction Visual Effects (8 effects)

1. **reaction_explosion** - Explosion reaction particle effect
2. **reaction_toxic_smoke** - Toxic smoke reaction particle effect
3. **reaction_healing_mist** - Healing mist reaction particle effect
4. **reaction_intense_heat** - Intense heat reaction particle effect
5. **reaction_extinguish** - Extinguish reaction particle effect
6. **reaction_steam** - Steam reaction particle effect
7. **reaction_energy_storage** - Energy storage reaction particle effect
8. **reaction_active** - Active reaction particle effect

### Grid Reaction Visuals (4 visuals)

1. **grid_cell** - Grid reaction cell texture
2. **grid_cell_active** - Active grid cell texture
3. **grid_connection** - Grid connection line
4. **grid_diffusion** - Diffusion particle effect

### Alchemy Station UI Elements (11 elements)

1. **ui_panel_alchemy** - Alchemy station panel background
2. **ui_panel_reactions** - Reactions panel background
3. **ui_slot_ingredient** - Ingredient slot background
4. **ui_slot_output** - Output slot background
5. **ui_button_react** - React button icon
6. **ui_button_clear** - Clear button icon
7. **ui_indicator_temperature** - Temperature indicator icon
8. **ui_indicator_pressure** - Pressure indicator icon
9. **ui_indicator_humidity** - Humidity indicator icon
10. **ui_indicator_wind** - Wind indicator icon
11. **ui_indicator_mana** - Mana indicator icon

### Plant Sprites (4 sprites)

1. **plant_basic** - Basic alchemical plant sprite
2. **plant_herb** - Herb plant sprite
3. **plant_crystal** - Crystal plant sprite
4. **plant_magical** - Magical plant sprite

### Environmental Condition Indicators (9 indicators)

1. **env_temperature_high** - High temperature indicator
2. **env_temperature_low** - Low temperature indicator
3. **env_pressure_high** - High pressure indicator
4. **env_pressure_low** - Low pressure indicator
5. **env_humidity_high** - High humidity indicator
6. **env_humidity_low** - Low humidity indicator
7. **env_wind_strong** - Strong wind indicator
8. **env_wind_calm** - Calm wind indicator
9. **env_corrosive** - Corrosive atmosphere indicator

### Reaction Status Indicators (7 indicators)

1. **status_ready** - Reaction ready indicator
2. **status_active** - Reaction active indicator
3. **status_complete** - Reaction complete indicator
4. **status_failed** - Reaction failed indicator
5. **status_incompatible** - Incompatible indicator
6. **status_conditions_met** - Conditions met indicator
7. **status_conditions_not_met** - Conditions not met indicator

### Ingredient State Indicators (9 indicators)

1. **state_rust** - Rust state indicator
2. **state_hot** - Hot state indicator
3. **state_cold** - Cold state indicator
4. **state_wet** - Wet state indicator
5. **state_dry** - Dry state indicator
6. **state_charged** - Mana charged indicator
7. **state_active** - Active state indicator
8. **state_pure** - Pure state indicator
9. **state_contaminated** - Contaminated state indicator

## Total: ~73 Assets

## Output Structure

```
assets/
└── alchemy/
    ├── ingredients/
    │   ├── ingredient_basic.png
    │   ├── ingredient_crystal.png
    │   └── ... (all ingredient type icons)
    ├── phases/
    │   ├── phase_solid.png
    │   ├── phase_liquid.png
    │   └── ... (all phase indicators)
    ├── elements/
    │   ├── element_fire.png
    │   ├── element_water.png
    │   └── ... (all elemental type icons)
    ├── materials/
    │   ├── material_metal.png
    │   ├── material_organic.png
    │   └── ... (all material type icons)
    ├── reactions/
    │   └── effects/
    │       ├── reaction_explosion.particle
    │       ├── reaction_toxic_smoke.particle
    │       └── ... (all reaction visual effects)
    ├── grid/
    │   ├── grid_cell.png
    │   ├── grid_cell_active.png
    │   └── ... (all grid reaction visuals)
    ├── ui/
    │   └── station/
    │       ├── ui_panel_alchemy.png
    │       ├── ui_slot_ingredient.png
    │       └── ... (all station UI elements)
    ├── plants/
    │   ├── plant_basic.png
    │   ├── plant_herb.png
    │   └── ... (all plant sprites)
    ├── environment/
    │   ├── env_temperature_high.png
    │   ├── env_pressure_high.png
    │   └── ... (all environmental indicators)
    ├── status/
    │   ├── status_ready.png
    │   ├── status_active.png
    │   └── ... (all reaction status indicators)
    └── states/
        ├── state_rust.png
        ├── state_hot.png
        └── ... (all ingredient state indicators)
```

## Integration

### AlchemistBus

```cpp
// Register reaction rule
ReactionRule rule;
rule.requiredTags = {"fire", "solid:sodium"};
rule.cppHandler = [](ReactionContext& ctx) {
    ctx.effects.push_back("explosion");
};
AlchemistBus::instance().registerRule(std::move(rule));
// Uses: /assets/alchemy/reactions/effects/reaction_explosion.particle

// Process reaction
ReactionContext ctx;
ctx.inputs = {&ingredient1, &ingredient2};
ctx.temperature = 100.0f;
AlchemistBus::instance().react(ctx);
// Uses: /assets/alchemy/ui/station/ui_indicator_temperature.png
// Uses: /assets/alchemy/status/status_active.png
```

### Ingredient

```cpp
// Create ingredient
Ingredient ingredient("iron", tags);
ingredient.setPhase("solid");
ingredient.setElementalType("fire");
// Uses: /assets/alchemy/phases/phase_solid.png
// Uses: /assets/alchemy/elements/element_fire.png

// Set state
ingredient.setRustLevel(0.5f);
ingredient.setTemperature(150.0f);
// Uses: /assets/alchemy/states/state_rust.png
// Uses: /assets/alchemy/states/state_hot.png
```

### ReactionContext

```cpp
// Reaction context
ReactionContext ctx;
ctx.temperature = 100.0f;
ctx.pressure = 101.3f;
ctx.humidity = 50.0f;
ctx.wind = {10.0f, 5.0f};
ctx.ambientMana = 50.0f;
// Uses: /assets/alchemy/ui/station/ui_indicator_temperature.png
// Uses: /assets/alchemy/ui/station/ui_indicator_pressure.png
// Uses: /assets/alchemy/ui/station/ui_indicator_humidity.png
// Uses: /assets/alchemy/ui/station/ui_indicator_wind.png
// Uses: /assets/alchemy/ui/station/ui_indicator_mana.png
```

### GridReactionModule

```cpp
// Grid reaction
GridReactionModule module;
module.registerGridReaction("A + B -> C", 0.5f);
// Uses: /assets/alchemy/grid/grid_cell.png
// Uses: /assets/alchemy/grid/grid_connection.png
// Uses: /assets/alchemy/grid/grid_diffusion.particle
```

## Ingredient States

### Phase States
- **Solid**: Solid phase
- **Liquid**: Liquid phase
- **Gas**: Gas phase
- **Plasma**: Plasma phase

### Elemental Types
- **Fire**: Fire element
- **Water**: Water element
- **Earth**: Earth element
- **Air**: Air element
- **Void**: Void element
- **Neutral**: Neutral element

### Material Types
- **Metal**: Metallic material
- **Organic**: Organic material
- **Crystal**: Crystalline material
- **Gem**: Gemstone material
- **Wood**: Wooden material
- **Bone**: Bone material

### Ingredient States
- **Rust**: Rusted ingredient
- **Hot**: Heated ingredient
- **Cold**: Cooled ingredient
- **Wet**: Moist ingredient
- **Dry**: Dry ingredient
- **Charged**: Mana charged ingredient
- **Active**: Active ingredient
- **Pure**: Pure ingredient
- **Contaminated**: Contaminated ingredient

## Reaction Types

### Reaction Effects
- **Explosion**: Explosive reaction
- **Toxic Smoke**: Toxic smoke reaction
- **Healing Mist**: Healing mist reaction
- **Intense Heat**: Intense heat reaction
- **Extinguish**: Extinguish reaction
- **Steam**: Steam reaction
- **Energy Storage**: Energy storage reaction
- **Active**: Active reaction

### Reaction Status
- **Ready**: Ready to react
- **Active**: Reaction in progress
- **Complete**: Reaction finished
- **Failed**: Reaction failed
- **Incompatible**: Ingredients incompatible
- **Conditions Met**: Reaction conditions satisfied
- **Conditions Not Met**: Reaction conditions not satisfied

## Environmental Conditions

### Temperature
- **High**: High temperature
- **Low**: Low temperature

### Pressure
- **High**: High pressure
- **Low**: Low pressure

### Humidity
- **High**: High humidity
- **Low**: Low humidity

### Wind
- **Strong**: Strong wind
- **Calm**: Calm wind

### Atmosphere
- **Corrosive**: Corrosive atmosphere

## Workflow

### Step 1: Generate Assets

```powershell
.\GenerateAlchemistBusAssets.ps1 -OllamaModel "codellama:7b-instruct"
```

### Step 2: Configure AlchemistBus

Set up AlchemistBus with asset paths.

### Step 3: Register Reactions

```cpp
AlchemistBus::instance().initializeLua("Scripts/Reactions/");
AlchemistBus::instance().initializeJson("Config/Reactions/");
```

### Step 4: Create Ingredients

```cpp
Ingredient ingredient("iron", {"metal", "solid"});
ingredient.setPhase("solid");
ingredient.setElementalType("fire");
```

### Step 5: Process Reactions

```cpp
ReactionContext ctx;
ctx.inputs = {&ingredient1, &ingredient2};
AlchemistBus::instance().react(ctx);
```

### Step 6: Test in Game

Load the mod and test alchemy system in-game.

## Advanced Options

### Custom Ingredient Types

Edit `GenerateAlchemistBusAssets.ps1` to add custom ingredient type icons.

### Custom Reactions

Add custom reaction visual effects for new reaction types.

### Custom Environmental Conditions

Add custom environmental condition indicators for new conditions.

## Tips

1. **Ingredient icons**: Use 32x32 for ingredient type icons
2. **Phase indicators**: Use 32x32 for phase indicators
3. **Elemental icons**: Use 32x32 for elemental type icons
4. **Material icons**: Use 32x32 for material type icons
5. **Reaction effects**: Keep effects visually distinct and informative
6. **Grid visuals**: Use 32x32 for grid cells, 64x8 for connections
7. **UI panels**: Use 256x256 for main panels, 128x128 for smaller panels
8. **Plant sprites**: Use 32x32 for plant sprites
9. **Status indicators**: Use 32x32 for status indicators
10. **State indicators**: Use 32x32 for state indicators

## Troubleshooting

### Reactions Not Displaying

- Check reaction effect paths
- Verify effects are in `assets/alchemy/reactions/effects/`
- Ensure AlchemistBus is initialized

### Ingredients Not Displaying

- Check ingredient icon paths
- Verify icons are in `assets/alchemy/ingredients/`
- Ensure ingredient system is enabled

### UI Not Displaying

- Check UI element paths
- Verify elements are in `assets/alchemy/ui/station/`
- Ensure UI system is enabled

### Grid Reactions Not Displaying

- Check grid visual paths
- Verify visuals are in `assets/alchemy/grid/`
- Ensure GridReactionModule is initialized

---

*Part of the Starbound Ollama Asset Generator suite*
