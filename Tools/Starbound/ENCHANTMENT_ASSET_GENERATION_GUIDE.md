# Enchantment System Asset Generation Guide

Generate visual assets for the Enchantment System including enchantment tier icons, rarity icons, category icons, trigger icons, enchantment effect visuals, rune/glow effects, enchantment UI elements, mana indicators, cooldown indicators, and synergy/conflict indicators.

## Quick Start

```powershell
# Generate all Enchantment assets
.\GenerateEnchantmentAssets.ps1

# Use C++ backend for better quality
.\GenerateEnchantmentAssets.ps1 -UseCppBackend

# Or generate everything at once
.\GenerateAllModSprites.ps1 -OllamaModel "codellama:7b-instruct"
```

## What Gets Generated

### Enchantment Tier Icons (8 icons)

1. **tier_basic** - Basic tier (Tier 1)
2. **tier_common** - Common tier (Tier 2)
3. **tier_uncommon** - Uncommon tier (Tier 3)
4. **tier_rare** - Rare tier (Tier 4)
5. **tier_epic** - Epic tier (Tier 5)
6. **tier_legendary** - Legendary tier (Tier 6)
7. **tier_mythic** - Mythic tier (Tier 7)
8. **tier_divine** - Divine tier (Tier 8)

### Enchantment Rarity Icons (6 icons)

1. **rarity_common** - Common rarity
2. **rarity_uncommon** - Uncommon rarity
3. **rarity_rare** - Rare rarity
4. **rarity_epic** - Epic rarity
5. **rarity_legendary** - Legendary rarity
6. **rarity_mythic** - Mythic rarity

### Enchantment Category Icons (8 icons)

1. **category_damage** - Damage category
2. **category_utility** - Utility category
3. **category_defensive** - Defensive category
4. **category_environmental** - Environmental category
5. **category_synergy** - Synergy category
6. **category_risk** - Risk category
7. **category_stability** - Stability category
8. **category_corruption** - Corruption category

### Enchantment Trigger Icons (12 icons)

1. **trigger_on_hit** - On hit trigger
2. **trigger_on_damage** - On damage trigger
3. **trigger_critical** - Critical strike trigger
4. **trigger_block** - Block trigger
5. **trigger_dodge** - Dodge trigger
6. **trigger_kill** - Kill trigger
7. **trigger_move** - Move trigger
8. **trigger_jump** - Jump trigger
9. **trigger_biome** - Biome trigger
10. **trigger_weather** - Weather trigger
11. **trigger_time** - Time trigger
12. **trigger_custom** - Custom trigger

### Enchantment Effect Visuals (6 effects)

1. **effect_apply** - Apply enchantment particle effect
2. **effect_remove** - Remove enchantment particle effect
3. **effect_active** - Active enchantment particle effect
4. **effect_trigger** - Trigger activated particle effect
5. **effect_synergy** - Synergy activated particle effect
6. **effect_conflict** - Conflict activated particle effect

### Rune/Glow Effects (8 effects)

1. **rune_basic** - Basic enchantment rune texture
2. **rune_common** - Common enchantment rune texture
3. **rune_rare** - Rare enchantment rune texture
4. **rune_epic** - Epic enchantment rune texture
5. **rune_legendary** - Legendary enchantment rune texture
6. **glow_active** - Active enchantment glow particle effect
7. **glow_charging** - Charging enchantment glow particle effect
8. **glow_ready** - Ready enchantment glow particle effect

### Enchantment UI Elements (9 elements)

1. **ui_panel_enchantment** - Enchantment panel background
2. **ui_panel_slots** - Enchantment slots panel background
3. **ui_slot_enchantment** - Enchantment slot background
4. **ui_slot_empty** - Empty enchantment slot background
5. **ui_slot_locked** - Locked enchantment slot background
6. **ui_button_apply** - Apply enchantment button icon
7. **ui_button_remove** - Remove enchantment button icon
8. **ui_button_upgrade** - Upgrade enchantment button icon
9. **ui_tooltip_enchantment** - Enchantment tooltip background

### Mana Indicators (7 indicators)

1. **mana_full** - Mana full indicator
2. **mana_high** - Mana high indicator
3. **mana_medium** - Mana medium indicator
4. **mana_low** - Mana low indicator
5. **mana_empty** - Mana empty indicator
6. **mana_charging** - Mana charging indicator
7. **mana_bar** - Mana bar background texture

### Cooldown Indicators (4 indicators)

1. **cooldown_ready** - Cooldown ready indicator
2. **cooldown_active** - Cooldown active indicator
3. **cooldown_almost_ready** - Almost ready indicator
4. **cooldown_bar** - Cooldown bar background texture

### Synergy/Conflict Indicators (6 indicators)

1. **synergy_active** - Synergy active indicator
2. **synergy_bonus** - Synergy bonus indicator
3. **conflict_active** - Conflict active indicator
4. **conflict_penalty** - Conflict penalty indicator
5. **compatible** - Compatible indicator
6. **incompatible** - Incompatible indicator

## Total: ~74 Assets

## Output Structure

```
assets/
└── enchantment/
    ├── tiers/
    │   ├── tier_basic.png
    │   ├── tier_common.png
    │   └── ... (all tier icons)
    ├── rarities/
    │   ├── rarity_common.png
    │   ├── rarity_uncommon.png
    │   └── ... (all rarity icons)
    ├── categories/
    │   ├── category_damage.png
    │   ├── category_utility.png
    │   └── ... (all category icons)
    ├── triggers/
    │   ├── trigger_on_hit.png
    │   ├── trigger_on_damage.png
    │   └── ... (all trigger icons)
    ├── effects/
    │   ├── effect_apply.particle
    │   ├── effect_remove.particle
    │   └── ... (all effect visuals)
    ├── runes/
    │   ├── rune_basic.png
    │   ├── rune_common.png
    │   └── ... (all rune/glow effects)
    ├── ui/
    │   ├── ui_panel_enchantment.png
    │   ├── ui_slot_enchantment.png
    │   └── ... (all UI elements)
    ├── mana/
    │   ├── mana_full.png
    │   ├── mana_high.png
    │   └── ... (all mana indicators)
    ├── cooldown/
    │   ├── cooldown_ready.png
    │   ├── cooldown_active.png
    │   └── ... (all cooldown indicators)
    └── synergy/
        ├── synergy_active.png
        ├── conflict_active.png
        └── ... (all synergy/conflict indicators)
```

## Integration

### EnchantmentSystem

```cpp
// Apply enchantment
EnchantmentSystem::instance().applyEnchantment(entity, "fireEnchantment", level);
// Uses: /assets/enchantment/effects/effect_apply.particle
// Uses: /assets/enchantment/runes/rune_*.png
// Uses: /assets/enchantment/ui/ui_slot_enchantment.png

// Process event
EnchantmentSystem::instance().processEvent(entity, EnchantmentTriggerType::OnHitTarget);
// Uses: /assets/enchantment/triggers/trigger_on_hit.png
// Uses: /assets/enchantment/effects/effect_trigger.particle

// Get component
auto component = EnchantmentSystem::instance().getComponent(entity);
// Uses: /assets/enchantment/ui/ui_panel_enchantment.png
```

### EnchantmentDefinition

```cpp
// Enchantment definition
EnchantmentDefinition def;
def.tier = EnchantmentTier::Epic;
def.rarity = EnchantmentRarity::Legendary;
def.category = EnchantmentCategory::Damage;
// Uses: /assets/enchantment/tiers/tier_epic.png
// Uses: /assets/enchantment/rarities/rarity_legendary.png
// Uses: /assets/enchantment/categories/category_damage.png
```

### ActiveEnchantment

```cpp
// Active enchantment
ActiveEnchantment enchantment(def, level);
// Uses: /assets/enchantment/runes/rune_*.png
// Uses: /assets/enchantment/runes/glow_active.particle

// Check mana
if (enchantment.context.hasMana()) {
    // Uses: /assets/enchantment/mana/mana_*.png
}

// Check cooldown
if (enchantment.context.isOnCooldown()) {
    // Uses: /assets/enchantment/cooldown/cooldown_active.png
}
```

## Enchantment Tiers

### EnchantmentTier Types
- **Basic**: Tier 1
- **Common**: Tier 2
- **Uncommon**: Tier 3
- **Rare**: Tier 4
- **Epic**: Tier 5
- **Legendary**: Tier 6
- **Mythic**: Tier 7
- **Divine**: Tier 8

## Enchantment Rarities

### EnchantmentRarity Types
- **Common**: Common rarity
- **Uncommon**: Uncommon rarity
- **Rare**: Rare rarity
- **Epic**: Epic rarity
- **Legendary**: Legendary rarity
- **Mythic**: Mythic rarity

## Enchantment Categories

### EnchantmentCategory Types
- **Damage**: Damage-focused enchantments
- **Utility**: Utility-focused enchantments
- **Defensive**: Defensive-focused enchantments
- **Environmental**: Environmentally-reactive enchantments
- **Synergy**: Synergy-focused enchantments
- **Risk**: Risk/reward enchantments
- **Stability**: Stability-focused enchantments
- **Corruption**: Corruption-focused enchantments

## Enchantment Triggers

### Combat Triggers
- **OnHitTarget**: When hitting a target
- **OnReceiveDamage**: When receiving damage
- **OnCriticalStrike**: On critical strike
- **OnBlock**: When blocking
- **OnDodge**: When dodging
- **OnKill**: When killing an enemy

### Movement Triggers
- **OnMove**: When moving
- **OnJump**: When jumping

### Environmental Triggers
- **OnEnterBiome**: When entering a biome
- **OnWeatherChange**: When weather changes
- **OnTimeOfDayChange**: When time of day changes

## Mana System

### Mana States
- **Full**: Full mana
- **High**: High mana
- **Medium**: Medium mana
- **Low**: Low mana
- **Empty**: No mana
- **Charging**: Mana charging

## Cooldown System

### Cooldown States
- **Ready**: Ready to use
- **Active**: On cooldown
- **Almost Ready**: Almost ready

## Synergy/Conflict System

### Synergy States
- **Active**: Synergy active
- **Bonus**: Synergy bonus applied

### Conflict States
- **Active**: Conflict active
- **Penalty**: Conflict penalty applied

### Compatibility
- **Compatible**: Enchantments compatible
- **Incompatible**: Enchantments incompatible

## Workflow

### Step 1: Generate Assets

```powershell
.\GenerateEnchantmentAssets.ps1 -OllamaModel "codellama:7b-instruct"
```

### Step 2: Configure EnchantmentSystem

Set up EnchantmentSystem with asset paths.

### Step 3: Register Enchantments

```cpp
EnchantmentRegistry::instance().registerFromJSON("/path/to/enchantments.json");
```

### Step 4: Apply Enchantments

```cpp
EnchantmentSystem::instance().applyEnchantment(entity, "fireEnchantment", 1);
```

### Step 5: Process Events

```cpp
EnchantmentSystem::instance().processEvent(entity, EnchantmentTriggerType::OnHitTarget);
```

### Step 6: Test in Game

Load the mod and test enchantment system in-game.

## Advanced Options

### Custom Enchantment Tiers

Edit `GenerateEnchantmentAssets.ps1` to add custom tier icons.

### Custom Categories

Add custom enchantment categories as needed.

### Custom Triggers

Add custom trigger icons for new trigger types.

## Tips

1. **Tier icons**: Use 32x32 for tier icons
2. **Rarity icons**: Use 32x32 for rarity icons
3. **Category icons**: Use 32x32 for category icons
4. **Trigger icons**: Use 32x32 for trigger icons
5. **Rune textures**: Use 64x64 for rune textures
6. **UI panels**: Use 256x256 for main panels, 128x128 for smaller panels
7. **Mana/cooldown bars**: Use 128x16 for bar textures
8. **Particle effects**: Keep effects subtle and informative

## Troubleshooting

### Enchantments Not Displaying

- Check tier/rarity/category icon paths
- Verify icons are in `assets/enchantment/`
- Ensure EnchantmentSystem is initialized

### Effects Not Showing

- Check effect paths
- Verify effects are in `assets/enchantment/effects/`
- Ensure effect system is enabled

### Mana Not Displaying

- Check mana indicator paths
- Verify indicators are in `assets/enchantment/mana/`
- Ensure mana system is enabled

### Cooldown Not Displaying

- Check cooldown indicator paths
- Verify indicators are in `assets/enchantment/cooldown/`
- Ensure cooldown system is enabled

---

*Part of the Starbound Ollama Asset Generator suite*
