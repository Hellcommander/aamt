# BuffAgent System Asset Generation Guide

Generate visual assets for the BuffAgent System including buff icons, debuff icons, stack indicators, duration indicators, buff UI elements, aura effects, buff application effects, status effect overlays, and buff type indicators.

## Quick Start

```powershell
# Generate all BuffAgent assets
.\GenerateBuffAgentAssets.ps1

# Use C++ backend for better quality
.\GenerateBuffAgentAssets.ps1 -UseCppBackend

# Or generate everything at once
.\GenerateAllModSprites.ps1 -OllamaModel "codellama:7b-instruct"
```

## What Gets Generated

### Buff Icons (12 icons)

1. **buff_strength** - Strength buff icon
2. **buff_agility** - Agility buff icon
3. **buff_defense** - Defense buff icon
4. **buff_speed** - Speed buff icon
5. **buff_heal** - Heal buff icon
6. **buff_mana_regen** - Mana regeneration buff icon
7. **buff_shield** - Shield buff icon
8. **buff_arcane_shield** - Arcane shield buff icon
9. **buff_berserker_rage** - Berserker rage buff icon
10. **buff_mighty_strength** - Mighty strength buff icon
11. **buff_frost_aura** - Frost aura buff icon
12. **buff_fire_aura** - Fire aura buff icon

### Debuff Icons (10 icons)

1. **debuff_weakness** - Weakness debuff icon
2. **debuff_slow** - Slow debuff icon
3. **debuff_poison** - Poison debuff icon
4. **debuff_burn** - Burn debuff icon
5. **debuff_freeze** - Freeze debuff icon
6. **debuff_stun** - Stun debuff icon
7. **debuff_silence** - Silence debuff icon
8. **debuff_curse** - Curse debuff icon
9. **debuff_fear** - Fear debuff icon
10. **debuff_bleed** - Bleed debuff icon

### Stack Indicators (6 indicators)

1. **stack_indicator** - Stack indicator icon
2. **stack_1** - Stack 1 indicator
3. **stack_2** - Stack 2 indicator
4. **stack_3** - Stack 3 indicator
5. **stack_max** - Max stacks indicator
6. **stack_overflow** - Stack overflow indicator

### Duration Indicators (6 indicators)

1. **duration_full** - Full duration indicator
2. **duration_high** - High duration indicator
3. **duration_medium** - Medium duration indicator
4. **duration_low** - Low duration indicator
5. **duration_expiring** - Expiring indicator
6. **duration_infinite** - Infinite duration indicator

### Buff UI Elements (8 elements)

1. **ui_panel_buffs** - Buffs panel background
2. **ui_panel_debuffs** - Debuffs panel background
3. **ui_tooltip_buff** - Buff tooltip background
4. **ui_tooltip_debuff** - Debuff tooltip background
5. **ui_inspector_panel** - Buff inspector panel background
6. **ui_slot_buff** - Buff slot background
7. **ui_slot_debuff** - Debuff slot background
8. **ui_button_remove_buff** - Remove buff button icon

### Aura Effects (6 effects)

1. **aura_frost** - Frost aura particle effect
2. **aura_fire** - Fire aura particle effect
3. **aura_arcane** - Arcane aura particle effect
4. **aura_heal** - Heal aura particle effect
5. **aura_shield** - Shield aura particle effect
6. **aura_radius_indicator** - Aura radius indicator

### Buff Application Effects (5 effects)

1. **effect_apply_buff** - Apply buff particle effect
2. **effect_remove_buff** - Remove buff particle effect
3. **effect_refresh_buff** - Refresh buff particle effect
4. **effect_stack_buff** - Stack buff particle effect
5. **effect_expire_buff** - Expire buff particle effect

### Status Effect Overlays (6 overlays)

1. **overlay_buff_glow** - Buff glow overlay
2. **overlay_debuff_glow** - Debuff glow overlay
3. **overlay_shield** - Shield overlay
4. **overlay_poison** - Poison overlay
5. **overlay_freeze** - Freeze overlay
6. **overlay_burn** - Burn overlay

### Buff Type Indicators (5 indicators)

1. **type_buff** - Buff type indicator
2. **type_debuff** - Debuff type indicator
3. **type_aura** - Aura type indicator
4. **type_tick** - Tick type indicator
5. **type_permanent** - Permanent type indicator

## Total: ~64 Assets

## Output Structure

```
assets/
└── buffs/
    ├── icons/
    │   ├── buff_strength.png
    │   ├── buff_agility.png
    │   └── ... (all buff icons)
    ├── debuffs/
    │   ├── debuff_weakness.png
    │   ├── debuff_slow.png
    │   └── ... (all debuff icons)
    ├── stacks/
    │   ├── stack_indicator.png
    │   ├── stack_1.png
    │   └── ... (all stack indicators)
    ├── duration/
    │   ├── duration_full.png
    │   ├── duration_high.png
    │   └── ... (all duration indicators)
    ├── ui/
    │   ├── ui_panel_buffs.png
    │   ├── ui_panel_debuffs.png
    │   └── ... (all UI elements)
    ├── auras/
    │   ├── aura_frost.particle
    │   ├── aura_fire.particle
    │   └── ... (all aura effects)
    ├── effects/
    │   ├── effect_apply_buff.particle
    │   ├── effect_remove_buff.particle
    │   └── ... (all application effects)
    ├── overlays/
    │   ├── overlay_buff_glow.png
    │   ├── overlay_debuff_glow.png
    │   └── ... (all status overlays)
    └── types/
        ├── type_buff.png
        ├── type_debuff.png
        └── ... (all type indicators)
```

## Integration

### BuffAgent

```cpp
// Register buff definition
BuffDef def;
def.id = "arcaneShield";
def.icon = "assets/buffs/icons/buff_arcane_shield.png";
def.effectVFX = "assets/buffs/auras/aura_shield.particle";
buffAgent.registerBuffDef(def);

// Apply buff
buffAgent.applyBuff(target, "arcaneShield", source);
// Uses: /assets/buffs/icons/buff_arcane_shield.png
// Uses: /assets/buffs/effects/effect_apply_buff.particle
// Uses: /assets/buffs/overlays/overlay_shield.png

// Get buff stacks
int stacks = buffAgent.getBuffStacks(target, "arcaneShield");
// Uses: /assets/buffs/stacks/stack_*.png

// Get remaining duration
double duration = buffAgent.getRemainingDuration(target, "arcaneShield");
// Uses: /assets/buffs/duration/duration_*.png

// Create aura buff
buffAgent.createAuraBuff(source, "frostAura", radius, true, false);
// Uses: /assets/buffs/auras/aura_frost.particle
// Uses: /assets/buffs/auras/aura_radius_indicator.png
```

### BuffDef

```cpp
// Buff definition with visual properties
BuffDef def;
def.icon = "assets/buffs/icons/buff_strength.png";
def.effectVFX = "assets/buffs/auras/aura_arcane.particle";
def.effectSFX = "sounds/buff_apply.ogg";
```

### BuffInstance

```cpp
// Buff instance with stack count
BuffInstance instance;
instance.stacks = 3;
// Uses: /assets/buffs/stacks/stack_3.png

// Buff instance with duration
double remaining = instance.getRemainingTime();
// Uses: /assets/buffs/duration/duration_*.png
```

## Stack Rules

### StackRule Types
- **Replace**: Overwrite duration & magnitude
- **Refresh**: Reset duration only
- **Accumulate**: Increment stack count
- **Unique**: Only one instance allowed

### Stack Indicators
- **Stack 1-3**: Individual stack count indicators
- **Stack Max**: Maximum stacks reached
- **Stack Overflow**: Over maximum stacks

## Duration States

### Duration Indicators
- **Full**: Full duration remaining
- **High**: High duration remaining
- **Medium**: Medium duration remaining
- **Low**: Low duration remaining
- **Expiring**: About to expire
- **Infinite**: Permanent buff

## Aura System

### Aura Types
- **Frost Aura**: Frost effect aura
- **Fire Aura**: Fire effect aura
- **Arcane Aura**: Arcane effect aura
- **Heal Aura**: Healing effect aura
- **Shield Aura**: Protective effect aura

### Aura Radius
- Visual indicator for aura range
- Shows affected area

## Application Effects

### Effect Types
- **Apply**: Buff applied visual feedback
- **Remove**: Buff removed visual feedback
- **Refresh**: Buff refreshed visual feedback
- **Stack**: Buff stacked visual feedback
- **Expire**: Buff expired visual feedback

## Status Overlays

### Overlay Types
- **Buff Glow**: Positive effect glow
- **Debuff Glow**: Negative effect glow
- **Shield**: Protective shield overlay
- **Poison**: Poison effect overlay
- **Freeze**: Frozen effect overlay
- **Burn**: Burning effect overlay

## Buff Types

### Type Indicators
- **Buff**: Positive effect indicator
- **Debuff**: Negative effect indicator
- **Aura**: Aura effect indicator
- **Tick**: Periodic effect indicator
- **Permanent**: Permanent effect indicator

## Workflow

### Step 1: Generate Assets

```powershell
.\GenerateBuffAgentAssets.ps1 -OllamaModel "codellama:7b-instruct"
```

### Step 2: Configure BuffAgent

Set up BuffAgent with asset paths.

### Step 3: Register Buff Definitions

```cpp
BuffAgent agent;
BuffDef def;
def.id = "mightyStrength";
def.icon = "assets/buffs/icons/buff_mighty_strength.png";
def.effectVFX = "assets/buffs/effects/effect_apply_buff.particle";
agent.registerBuffDef(def);
```

### Step 4: Apply Buffs

```cpp
agent.applyBuff(target, "mightyStrength", source);
```

### Step 5: Display Buffs

```cpp
// Get active buffs
auto buffs = agent.getActiveBuffs(target);
// Display buff icons with stack and duration indicators
```

### Step 6: Test in Game

Load the mod and test buff system in-game.

## Advanced Options

### Custom Buff Icons

Edit `GenerateBuffAgentAssets.ps1` to add custom buff icons.

### Custom Debuff Icons

Add custom debuff icons as needed.

### Custom Aura Effects

Add custom aura effects with unique visuals.

## Tips

1. **Buff icons**: Use 32x32 for buff/debuff icons
2. **Stack indicators**: Use 16x16 for stack indicators
3. **Duration indicators**: Use 16x16 for duration indicators
4. **UI panels**: Use 128x256 for buff panels
5. **Aura effects**: Keep aura effects subtle and visible
6. **Application effects**: Make application effects noticeable but not overwhelming
7. **Status overlays**: Keep overlays transparent and non-intrusive

## Troubleshooting

### Buffs Not Displaying

- Check buff icon paths
- Verify icons are in `assets/buffs/icons/`
- Ensure BuffAgent is initialized

### Stacks Not Showing

- Check stack indicator paths
- Verify indicators are in `assets/buffs/stacks/`
- Ensure stack system is configured

### Duration Not Displaying

- Check duration indicator paths
- Verify indicators are in `assets/buffs/duration/`
- Ensure duration tracking is enabled

### Aura Effects Not Working

- Check aura effect paths
- Verify effects are in `assets/buffs/auras/`
- Ensure aura system is enabled

### Application Effects Not Showing

- Check application effect paths
- Verify effects are in `assets/buffs/effects/`
- Ensure effect system is enabled

---

*Part of the Starbound Ollama Asset Generator suite*
