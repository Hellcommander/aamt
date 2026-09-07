# SpellBus System Asset Generation Guide

Generate assets for the SpellBus System including spell casting effects, material reactions, spell compositions, spellstones, event effects, persistent effects, and durability indicators.

## Quick Start

```powershell
# Generate all SpellBus assets
.\GenerateSpellBusAssets.ps1

# Use C++ backend for better quality
.\GenerateSpellBusAssets.ps1 -UseCppBackend

# Or generate everything including SpellBus assets
.\GenerateAllModSprites.ps1 -OllamaModel "codellama:7b-instruct"
```

## What Gets Generated

### Spell Casting Effects (4 effects)

1. **spell_cast_effect** - Spell casting particle effect
2. **spell_cast_complete** - Spell cast complete effect
3. **spell_cast_interrupt** - Spell cast interrupt effect
4. **spell_cast_failed** - Spell cast failed effect

### Material Reaction Effects (11 effects)

1. **reaction_steam_burst** - Steam burst reaction
2. **reaction_freeze** - Freeze reaction
3. **reaction_combustion** - Combustion reaction
4. **reaction_melting** - Melting reaction
5. **reaction_evaporation** - Evaporation reaction
6. **reaction_condensation** - Condensation reaction
7. **reaction_electrolysis** - Electrolysis reaction
8. **reaction_transmutation** - Transmutation reaction
9. **reaction_dissolution** - Dissolution reaction
10. **reaction_crystallization** - Crystallization reaction
11. **reaction_polymerization** - Polymerization reaction

### Spell Composition/Chain Effects (4 effects)

1. **spell_chain_effect** - Spell chain effect
2. **spell_combo_effect** - Spell combo effect
3. **spell_composition_start** - Spell composition start
4. **spell_composition_link** - Spell composition link

### Spellstone Icons (7 icons)

1. **spellstone_base** - Base spellstone icon
2. **spellstone_evolved** - Evolved spellstone icon
3. **spellstone_fused** - Fused spellstone icon
4. **spellstone_durability_high** - High durability spellstone
5. **spellstone_durability_medium** - Medium durability spellstone
6. **spellstone_durability_low** - Low durability spellstone
7. **spellstone_durability_critical** - Critical durability spellstone

### Spell Event Effects (8 effects)

1. **spell_event_learn** - Spell learn event
2. **spell_event_forget** - Spell forget event
3. **spell_event_upgrade** - Spell upgrade event
4. **spell_event_cooldown** - Spell cooldown event
5. **spell_event_resource** - Spell resource event
6. **spell_event_target** - Spell target event
7. **spell_event_area** - Spell area event
8. **spell_event_counter** - Spell counter event

### Persistent Effect Visuals (3 effects)

1. **persistent_effect_active** - Active persistent effect
2. **persistent_effect_tick** - Persistent effect tick
3. **persistent_effect_expire** - Persistent effect expire

### Durability Indicators (3 indicators)

1. **durability_change_effect** - Durability change effect
2. **repair_complete_effect** - Repair complete effect
3. **durability_warning** - Durability warning icon

## Total: ~40 Assets

## Output Structure

```
assets/
├── spellbus/
│   ├── casting/
│   │   ├── spell_cast_effect.particle
│   │   ├── spell_cast_complete.particle
│   │   ├── spell_cast_interrupt.particle
│   │   └── spell_cast_failed.particle
│   ├── reactions/
│   │   ├── reaction_steam_burst.particle
│   │   ├── reaction_freeze.particle
│   │   ├── reaction_combustion.particle
│   │   └── ... (all material reactions)
│   ├── compositions/
│   │   ├── spell_chain_effect.particle
│   │   ├── spell_combo_effect.particle
│   │   ├── spell_composition_start.particle
│   │   └── spell_composition_link.particle
│   ├── spellstones/
│   │   ├── spellstone_base.png
│   │   ├── spellstone_evolved.png
│   │   ├── spellstone_fused.png
│   │   └── ... (all spellstone icons)
│   ├── events/
│   │   ├── spell_event_learn.particle
│   │   ├── spell_event_forget.particle
│   │   └── ... (all spell event effects)
│   ├── persistent/
│   │   ├── persistent_effect_active.particle
│   │   ├── persistent_effect_tick.particle
│   │   └── persistent_effect_expire.particle
│   └── durability/
│       ├── durability_change_effect.particle
│       ├── repair_complete_effect.particle
│       └── durability_warning.png
```

## Integration

### Spell Casting

```cpp
// Fire spell through SpellBus
ISpellBus::fireSpell(spellId, context);
// Uses: /spellbus/casting/spell_cast_effect.particle
// Uses: /spellbus/casting/spell_cast_complete.particle on success
```

### Material Reactions

```cpp
// Create material reaction
ISpellBus::createMaterialReaction(ReactionType::COMBUSTION, params);
// Uses: /spellbus/reactions/reaction_combustion.particle

// Create specialized effects
ISpellBus::createSteamBurst(position, params, temperatureChange);
// Uses: /spellbus/reactions/reaction_steam_burst.particle

ISpellBus::createFreezeEffect(position);
// Uses: /spellbus/reactions/reaction_freeze.particle

ISpellBus::createCombustionReaction(position, intensity, params);
// Uses: /spellbus/reactions/reaction_combustion.particle
```

### Spell Compositions

```cpp
// Execute spell composition
ISpellBus::executeSpellComposition(compositionId, caster, params);
// Uses: /spellbus/compositions/spell_composition_start.particle
// Uses: /spellbus/compositions/spell_chain_effect.particle
// Uses: /spellbus/compositions/spell_combo_effect.particle
```

### Spellstones

```cpp
// Generate spellstone
ISpellBus::generateSpellstone(params);
// Uses: /spellbus/spellstones/spellstone_base.png

// Evolve spellstone
ISpellBus::evolveSpellstone(oldId, params);
// Uses: /spellbus/spellstones/spellstone_evolved.png

// Fuse spellstones
ISpellBus::fuseSpellstones(spellstoneA, spellstoneB);
// Uses: /spellbus/spellstones/spellstone_fused.png
```

### Spell Events

```cpp
// Publish spell event
SpellBusModule::publish(SpellEvent(EventType::SpellLearn, spellId));
// Uses: /spellbus/events/spell_event_learn.particle

// Various event types trigger corresponding effects
// SpellCast, SpellEffect, SpellComplete, SpellInterrupt, etc.
```

### Persistent Effects

```cpp
// Create persistent effect
ISpellBus::createPersistentEffect(effect);
// Uses: /spellbus/persistent/persistent_effect_active.particle
// Uses: /spellbus/persistent/persistent_effect_tick.particle on each tick
// Uses: /spellbus/persistent/persistent_effect_expire.particle on expiration
```

### Durability System

```cpp
// Apply spellstone wear
ISpellBus::applySpellstoneWear(spellstoneId, usageFatigue);
// Uses: /spellbus/durability/durability_change_effect.particle
// Updates: /spellbus/spellstones/spellstone_durability_*.png based on condition

// Repair spellstone
RepairManager::repair(spellstoneId);
// Uses: /spellbus/durability/repair_complete_effect.particle
```

## Material Reaction Types

### Reaction Types
- **Combustion**: Fire explosion
- **Freezing**: Ice crystallization
- **Melting**: Material liquefaction
- **Evaporation**: Liquid to gas
- **Condensation**: Gas to liquid
- **Electrolysis**: Electrical separation
- **Transmutation**: Material transformation
- **Dissolution**: Material dissolving
- **Crystallization**: Crystal formation
- **Polymerization**: Chain formation

## Spell Event Types

### Event Categories
- **SpellCast**: Spell casting initiated
- **SpellEffect**: Spell effect applied
- **SpellComplete**: Spell casting completed
- **SpellInterrupt**: Spell casting interrupted
- **SpellLearn**: Spell learned
- **SpellForget**: Spell forgotten
- **SpellUpgrade**: Spell upgraded
- **SpellCooldown**: Spell cooldown active
- **SpellResource**: Spell resource consumed
- **SpellTarget**: Spell target acquired
- **SpellArea**: Spell area of effect
- **SpellChain**: Spell chain triggered
- **SpellCombo**: Spell combo executed
- **SpellCounter**: Spell countered

## Durability States

### Spellstone Conditions
- **High**: Pristine condition (>75%)
- **Medium**: Worn condition (25-75%)
- **Low**: Damaged condition (10-25%)
- **Critical**: Near broken (<10%)

## Workflow

### Step 1: Generate Assets

```powershell
.\GenerateSpellBusAssets.ps1 -OllamaModel "codellama:7b-instruct"
```

### Step 2: Register Spell Definitions

Load spell definitions into the SpellBus system.

### Step 3: Test Spell Casting

Test spell casting and material interactions in-game.

### Step 4: Monitor Events

Monitor spell events and effects through the event bus.

## Advanced Options

### Custom Material Reactions

Edit `GenerateSpellBusAssets.ps1` to add custom material reactions:

```powershell
@{
    Id = "reaction_custom"
    Name = "Custom Reaction"
    Desc = "Custom material reaction description"
}
```

### Custom Spell Events

Add custom spell event effects to the `$spellEventEffects` array.

### Custom Spellstone Types

Add custom spellstone icons to the `$spellstoneIcons` array.

## Tips

1. **Spell casting effects**: Create distinct effects for each casting state
2. **Material reactions**: Match reaction effects to material types
3. **Spell compositions**: Use linking effects to show spell connections
4. **Spellstones**: Use durability icons to show condition
5. **Event effects**: Create visual feedback for all event types

## Troubleshooting

### Spell Effects Not Appearing

- Check spell effect paths in spell definitions
- Verify effects are in `assets/spellbus/casting/`
- Ensure SpellBus system is initialized

### Material Reactions Not Triggering

- Verify reaction effect paths in reaction system
- Check effects are in `assets/spellbus/reactions/`
- Ensure material interaction system is active

### Spellstones Not Displaying

- Check spellstone icon paths in spellstone definitions
- Verify icons are in `assets/spellbus/spellstones/`
- Ensure spellstone system is initialized

---

*Part of the Starbound Ollama Asset Generator suite*
