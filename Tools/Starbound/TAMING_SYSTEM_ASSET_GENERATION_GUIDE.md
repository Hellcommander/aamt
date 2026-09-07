# Taming System Asset Generation Guide

Generate assets for the Taming System including state indicators, affinity UI, progress indicators, food items, effects, and pet status indicators.

## Quick Start

```powershell
# Generate all taming system assets
.\GenerateTamingSystemAssets.ps1

# Use C++ backend for better quality
.\GenerateTamingSystemAssets.ps1 -UseCppBackend

# Or generate everything including taming system assets
.\GenerateAllModSprites.ps1 -OllamaModel "codellama:7b-instruct"
```

## What Gets Generated

### Taming State Indicators (4 icons)

1. **taming_state_wild** - Wild creature state
2. **taming_state_in_progress** - Taming in progress
3. **taming_state_tamed** - Tamed creature state
4. **taming_state_failed** - Taming failed state

### Affinity UI Elements (6 elements)

1. **affinity_bar** - Affinity bar UI
2. **affinity_positive** - Positive affinity indicator
3. **affinity_neutral** - Neutral affinity indicator
4. **affinity_negative** - Negative affinity indicator
5. **affinity_increase** - Affinity increase effect
6. **affinity_decrease** - Affinity decrease effect

### Taming Progress Indicators (6 indicators)

1. **taming_progress_bar** - Taming progress bar
2. **taming_progress_0** - Progress 0%
3. **taming_progress_25** - Progress 25%
4. **taming_progress_50** - Progress 50%
5. **taming_progress_75** - Progress 75%
6. **taming_progress_100** - Progress 100%

### Food Item Icons (7 icons)

1. **food_meat** - Meat food item
2. **food_fish** - Fish food item
3. **food_vegetable** - Vegetable food item
4. **food_fruit** - Fruit food item
5. **food_berry** - Berry food item
6. **food_treat** - Pet treat item
7. **food_poison** - Poison food item

### Taming Effect Particles (6 effects)

1. **taming_effect_start** - Taming start effect
2. **taming_effect_progress** - Taming progress effect
3. **taming_effect_success** - Taming success effect
4. **taming_effect_failure** - Taming failure effect
5. **taming_effect_food_positive** - Food positive reaction
6. **taming_effect_food_negative** - Food negative reaction

### Pet/Companion Status Indicators (6 indicators)

1. **pet_status_healthy** - Pet healthy status
2. **pet_status_hungry** - Pet hungry status
3. **pet_status_injured** - Pet injured status
4. **pet_status_following** - Pet following status
5. **pet_status_staying** - Pet staying status
6. **pet_status_attacking** - Pet attacking status

## Total: ~35 Assets

## Output Structure

```
assets/
├── taming/
│   ├── states/
│   │   ├── taming_state_wild.png
│   │   ├── taming_state_in_progress.png
│   │   ├── taming_state_tamed.png
│   │   └── taming_state_failed.png
│   ├── affinity/
│   │   ├── affinity_bar.png
│   │   ├── affinity_positive.png
│   │   ├── affinity_neutral.png
│   │   ├── affinity_negative.png
│   │   ├── affinity_increase.png
│   │   └── affinity_decrease.png
│   ├── progress/
│   │   ├── taming_progress_bar.png
│   │   ├── taming_progress_0.png
│   │   ├── taming_progress_25.png
│   │   ├── taming_progress_50.png
│   │   ├── taming_progress_75.png
│   │   └── taming_progress_100.png
│   ├── food/
│   │   ├── food_meat.png
│   │   ├── food_fish.png
│   │   ├── food_vegetable.png
│   │   ├── food_fruit.png
│   │   ├── food_berry.png
│   │   ├── food_treat.png
│   │   └── food_poison.png
│   ├── effects/
│   │   ├── taming_effect_start.particle
│   │   ├── taming_effect_progress.particle
│   │   ├── taming_effect_success.particle
│   │   ├── taming_effect_failure.particle
│   │   ├── taming_effect_food_positive.particle
│   │   └── taming_effect_food_negative.particle
│   └── pet_status/
│       ├── pet_status_healthy.png
│       ├── pet_status_hungry.png
│       ├── pet_status_injured.png
│       ├── pet_status_following.png
│       ├── pet_status_staying.png
│       └── pet_status_attacking.png
```

## Integration

### Taming Manager

```cpp
// Start taming
TamingManager::startTaming(playerId, creatureId);
// Uses: /taming/states/taming_state_in_progress.png
// Uses: /taming/effects/taming_effect_start.particle

// Process interaction
TamingManager::processInteraction(playerId, creatureId, itemType);
// Uses: /taming/food/food_*.png based on item type
// Uses: /taming/effects/taming_effect_food_*.particle based on reaction
// Uses: /taming/affinity/affinity_*.png for affinity changes

// Get taming state
TamingState state = TamingManager::getTamingState(creatureId);
// Uses: /taming/states/taming_state_*.png based on state
```

### Taming States

```cpp
enum class TamingState {
    WILD,                    // Uses: taming_state_wild.png
    TAMING_IN_PROGRESS,      // Uses: taming_state_in_progress.png
    TAMED,                   // Uses: taming_state_tamed.png
    FAILED                   // Uses: taming_state_failed.png
};
```

### Affinity System

```cpp
// Display affinity
renderAffinityBar(affinity);
// Uses: /taming/affinity/affinity_bar.png
// Uses: /taming/affinity/affinity_positive.png (if > 0)
// Uses: /taming/affinity/affinity_negative.png (if < 0)
// Uses: /taming/affinity/affinity_neutral.png (if == 0)

// Affinity changes
if (affinityIncreased) {
    // Uses: /taming/affinity/affinity_increase.png
    // Uses: /taming/effects/taming_effect_food_positive.particle
}
if (affinityDecreased) {
    // Uses: /taming/affinity/affinity_decrease.png
    // Uses: /taming/effects/taming_effect_food_negative.particle
}
```

### Progress Tracking

```cpp
// Display progress
renderProgressBar(progress);
// Uses: /taming/progress/taming_progress_bar.png
// Uses: /taming/progress/taming_progress_*.png based on percentage
```

### Food Items

```cpp
// Process food interaction
processInteraction(playerId, creatureId, "food_meat");
// Uses: /taming/food/food_meat.png
// Checks favoriteFoods/hatedFoods in TamableCreature
// Uses: /taming/effects/taming_effect_food_positive.particle (if favorite)
// Uses: /taming/effects/taming_effect_food_negative.particle (if hated)
```

### Pet Status

```cpp
// Display pet status
renderPetStatus(pet);
// Uses: /taming/pet_status/pet_status_*.png based on status
// Status: healthy, hungry, injured, following, staying, attacking
```

## Taming States

### State Flow
1. **WILD** → Creature is untamed
2. **TAMING_IN_PROGRESS** → Player is actively taming
3. **TAMED** → Creature is successfully tamed
4. **FAILED** → Taming attempt failed

## Affinity System

### Affinity Values
- **Positive**: Creature likes player/item (> 0)
- **Neutral**: Creature has neutral feelings (== 0)
- **Negative**: Creature dislikes player/item (< 0)

### Affinity Changes
- **Increase**: Affinity going up (positive food, good interaction)
- **Decrease**: Affinity going down (negative food, bad interaction)

## Food Types

### Food Categories
- **Meat**: Raw meat (carnivore favorite)
- **Fish**: Raw fish (aquatic creature favorite)
- **Vegetable**: Plant food (herbivore favorite)
- **Fruit**: Fruit food (omnivore favorite)
- **Berry**: Small berries (small creature favorite)
- **Treat**: Special pet treat (universal favorite)
- **Poison**: Toxic food (universal hated)

## Workflow

### Step 1: Generate Assets

```powershell
.\GenerateTamingSystemAssets.ps1 -OllamaModel "codellama:7b-instruct"
```

### Step 2: Configure Creatures

Set up `TamableCreature` definitions with favorite/hated foods.

### Step 3: Start Taming

Begin taming process with `TamingManager::startTaming()`.

### Step 4: Process Interactions

Feed creatures and process interactions.

### Step 5: Monitor Progress

Track taming progress and affinity changes.

### Step 6: Test in Game

Load the mod and test taming system in-game.

## Advanced Options

### Custom Food Items

Edit `GenerateTamingSystemAssets.ps1` to add custom food items:

```powershell
@{
    Id = "food_custom"
    Name = "Custom Food"
    Desc = "Custom food description, 32x32"
}
```

### Custom Taming States

Add custom taming state indicators if needed.

### Custom Pet Status

Add custom pet status indicators for additional states.

## Tips

1. **State icons**: Use 32x32 for UI display
2. **Progress indicators**: Use 16x16 for small indicators, 32x8 for bars
3. **Food icons**: Use 32x32 for inventory/UI
4. **Effect particles**: Match particle colors to taming state
5. **Status indicators**: Make status icons distinct and recognizable

## Troubleshooting

### States Not Displaying

- Check state icon paths in taming system
- Verify icons are in `assets/taming/states/`
- Ensure TamingManager is initialized

### Affinity Not Showing

- Check affinity UI paths
- Verify icons are in `assets/taming/affinity/`
- Ensure affinity system is configured

### Food Not Working

- Verify food item icons are in `assets/taming/food/`
- Check favoriteFoods/hatedFoods in creature definitions
- Ensure food processing is implemented

### Effects Not Appearing

- Check effect particle paths
- Verify effects are in `assets/taming/effects/`
- Ensure particle system is initialized

---

*Part of the Starbound Ollama Asset Generator suite*
