# DurabilityAgent System Asset Generation Guide

Generate visual assets for the DurabilityAgent System including condition state indicators, wear category icons, repair type icons, repair quality indicators, durability bar/meter UI elements, repair UI elements, damage/wear visual effects, repair visual effects, condition overlay textures, and durability status icons.

## Quick Start

```powershell
# Generate all DurabilityAgent assets
.\GenerateDurabilityAgentAssets.ps1

# Use C++ backend for better quality
.\GenerateDurabilityAgentAssets.ps1 -UseCppBackend

# Or generate everything at once
.\GenerateAllModSprites.ps1 -OllamaModel "codellama:7b-instruct"
```

## What Gets Generated

### Condition State Indicators (7 indicators)

1. **condition_pristine** - Pristine condition (100%)
2. **condition_maintained** - Maintained condition (90-99%)
3. **condition_used** - Used condition (70-89%)
4. **condition_worn** - Worn condition (50-69%)
5. **condition_damaged** - Damaged condition (20-49%)
6. **condition_critically_damaged** - Critically damaged condition (1-19%)
7. **condition_broken** - Broken condition (0%)

### Wear Category Icons (5 icons)

1. **wear_structural** - Structural wear icon
2. **wear_magical** - Magical wear icon
3. **wear_ingredient** - Ingredient wear icon
4. **wear_environmental** - Environmental wear icon
5. **wear_usage_fatigue** - Usage fatigue icon

### Repair Type Icons (4 icons)

1. **repair_preventive** - Preventive repair icon
2. **repair_minor** - Minor repair icon
3. **repair_major** - Major repair icon
4. **repair_restoration** - Restoration icon

### Repair Quality Indicators (6 indicators)

1. **quality_poor** - Poor quality (60-70%)
2. **quality_basic** - Basic quality (70-80%)
3. **quality_good** - Good quality (80-90%)
4. **quality_excellent** - Excellent quality (90-95%)
5. **quality_masterful** - Masterful quality (95-98%)
6. **quality_perfect** - Perfect quality (98-100%)

### Durability Bar/Meter UI Elements (9 elements)

1. **ui_bar_background** - Durability bar background
2. **ui_bar_fill_pristine** - Pristine fill
3. **ui_bar_fill_maintained** - Maintained fill
4. **ui_bar_fill_used** - Used fill
5. **ui_bar_fill_worn** - Worn fill
6. **ui_bar_fill_damaged** - Damaged fill
7. **ui_bar_fill_critical** - Critical fill
8. **ui_bar_fill_broken** - Broken fill
9. **ui_meter_frame** - Durability meter frame

### Repair UI Elements (10 elements)

1. **ui_panel_repair** - Repair panel background
2. **ui_panel_assessment** - Assessment panel background
3. **ui_tooltip_repair** - Repair tooltip background
4. **ui_button_repair** - Repair button icon
5. **ui_button_assess** - Assess button icon
6. **ui_button_maintenance** - Maintenance button icon
7. **ui_button_quick_repair** - Quick repair button icon
8. **ui_icon_ingredient** - Required ingredient icon
9. **ui_icon_tool** - Required tool icon
10. **ui_icon_skill** - Skill requirement icon

### Damage/Wear Visual Effects (7 effects)

1. **effect_wear_structural** - Structural wear particle effect
2. **effect_wear_magical** - Magical wear particle effect
3. **effect_wear_ingredient** - Ingredient wear particle effect
4. **effect_wear_environmental** - Environmental wear particle effect
5. **effect_wear_usage** - Usage wear particle effect
6. **effect_damage_critical** - Critical damage particle effect
7. **effect_break** - Break particle effect

### Repair Visual Effects (6 effects)

1. **effect_repair_preventive** - Preventive repair particle effect
2. **effect_repair_minor** - Minor repair particle effect
3. **effect_repair_major** - Major repair particle effect
4. **effect_repair_restoration** - Restoration particle effect
5. **effect_repair_success** - Repair success particle effect
6. **effect_repair_fail** - Repair fail particle effect

### Condition Overlay Textures (7 overlays)

1. **overlay_pristine** - Pristine condition overlay
2. **overlay_maintained** - Maintained condition overlay
3. **overlay_used** - Used condition overlay
4. **overlay_worn** - Worn condition overlay
5. **overlay_damaged** - Damaged condition overlay
6. **overlay_critical** - Critical condition overlay
7. **overlay_broken** - Broken condition overlay

### Durability Status Icons (6 icons)

1. **status_durability** - Durability status icon
2. **status_repair_needed** - Repair needed icon
3. **status_maintenance_needed** - Maintenance needed icon
4. **status_repairing** - Repairing icon
5. **status_repairable** - Repairable icon
6. **status_beyond_repair** - Beyond repair icon

## Total: ~67 Assets

## Output Structure

```
assets/
└── durability/
    ├── conditions/
    │   ├── condition_pristine.png
    │   ├── condition_maintained.png
    │   └── ... (all condition state indicators)
    ├── wear/
    │   ├── wear_structural.png
    │   ├── wear_magical.png
    │   └── ... (all wear category icons)
    ├── repair_types/
    │   ├── repair_preventive.png
    │   ├── repair_minor.png
    │   └── ... (all repair type icons)
    ├── quality/
    │   ├── quality_poor.png
    │   ├── quality_basic.png
    │   └── ... (all repair quality indicators)
    ├── ui/
    │   ├── bars/
    │   │   ├── ui_bar_background.png
    │   │   ├── ui_bar_fill_pristine.png
    │   │   └── ... (all durability bar elements)
    │   └── repair/
    │       ├── ui_panel_repair.png
    │       ├── ui_button_repair.png
    │       └── ... (all repair UI elements)
    ├── effects/
    │   ├── damage/
    │   │   ├── effect_wear_structural.particle
    │   │   ├── effect_wear_magical.particle
    │   │   └── ... (all damage/wear effects)
    │   └── repair/
    │       ├── effect_repair_preventive.particle
    │       ├── effect_repair_minor.particle
    │       └── ... (all repair effects)
    ├── overlays/
    │   ├── overlay_pristine.png
    │   ├── overlay_maintained.png
    │   └── ... (all condition overlays)
    └── status/
        ├── status_durability.png
        ├── status_repair_needed.png
        └── ... (all status icons)
```

## Integration

### DurabilityAgent

```cpp
// Register component
DurabilityAgent agent;
auto component = std::make_shared<SpellstoneDurabilityComponent>("spellstone_001");
agent.registerComponent(component);
// Uses: /assets/durability/conditions/condition_*.png
// Uses: /assets/durability/ui/bars/ui_bar_*.png

// Apply usage wear
agent.applyUsageWear("spellstone_001", 0.5f);
// Uses: /assets/durability/effects/damage/effect_wear_usage.particle
// Uses: /assets/durability/wear/wear_usage_fatigue.png

// Assess repair needs
auto assessment = agent.assessRepairNeeds(component);
// Uses: /assets/durability/ui/repair/ui_panel_assessment.png
// Uses: /assets/durability/ui/repair/ui_button_assess.png

// Perform repair
auto requirements = agent.calculateRepairRequirements(assessment, RepairType::Minor);
auto result = agent.performRepair(component, requirements, skillLevel, ingredients, tools);
// Uses: /assets/durability/ui/repair/ui_button_repair.png
// Uses: /assets/durability/effects/repair/effect_repair_minor.particle
// Uses: /assets/durability/quality/quality_*.png
```

### SpellstoneDurabilityComponent

```cpp
// Update condition
component->updateCondition();
// Uses: /assets/durability/conditions/condition_*.png
// Uses: /assets/durability/overlays/overlay_*.png

// Get condition state
ConditionState state = component->currentState;
// Uses: /assets/durability/conditions/condition_*.png
```

## Condition States

### ConditionState Types
- **Pristine**: 100% condition, no wear
- **Maintained**: 90-99% condition, minor wear
- **Used**: 70-89% condition, noticeable wear
- **Worn**: 50-69% condition, significant degradation
- **Damaged**: 20-49% condition, severe issues
- **CriticallyDamaged**: 1-19% condition, barely functional
- **Broken**: 0% condition, non-functional

## Wear Categories

### WearCategory Types
- **Structural**: Physical damage to structure
- **Magical**: Degradation of magical properties
- **Ingredient**: Individual ingredient breakdown
- **Environmental**: Damage from climate/storage
- **UsageFatigue**: Wear from repeated casting

## Repair Types

### RepairType Types
- **Preventive**: Regular cleaning and stabilization
- **Minor**: Surface repair and ingredient stabilization
- **Major**: Structural reconstruction and ingredient replacement
- **Restoration**: Complete overhaul and magical reformation

## Repair Quality

### RepairQuality Types
- **Poor**: 60-70% effectiveness
- **Basic**: 70-80% effectiveness
- **Good**: 80-90% effectiveness
- **Excellent**: 90-95% effectiveness
- **Masterful**: 95-98% effectiveness
- **Perfect**: 98-100% effectiveness

## Workflow

### Step 1: Generate Assets

```powershell
.\GenerateDurabilityAgentAssets.ps1 -OllamaModel "codellama:7b-instruct"
```

### Step 2: Configure DurabilityAgent

Set up DurabilityAgent with asset paths.

### Step 3: Register Component

```cpp
DurabilityAgent agent;
auto component = std::make_shared<SpellstoneDurabilityComponent>("spellstone_001");
agent.registerComponent(component);
```

### Step 4: Apply Wear

```cpp
agent.applyUsageWear("spellstone_001", 0.5f);
agent.applyEnvironmentalWear("spellstone_001", 0.2f);
```

### Step 5: Assess and Repair

```cpp
auto assessment = agent.assessRepairNeeds(component);
auto requirements = agent.calculateRepairRequirements(assessment, RepairType::Minor);
auto result = agent.performRepair(component, requirements, skillLevel, ingredients, tools);
```

### Step 6: Test in Game

Load the mod and test durability system in-game.

## Advanced Options

### Custom Condition States

Edit `GenerateDurabilityAgentAssets.ps1` to add custom condition states.

### Custom Wear Categories

Add custom wear categories as needed.

### Custom Repair Types

Add custom repair types with unique icons.

## Tips

1. **Condition indicators**: Use 32x32 for condition state icons
2. **Durability bars**: Use 128x16 for durability bar textures
3. **UI panels**: Use 256x256 for main panels, 128x128 for smaller panels
4. **UI buttons**: Use 32x32 for buttons
5. **Particle effects**: Keep effects subtle and informative
6. **Overlays**: Keep overlays transparent and non-intrusive
7. **Status icons**: Make status icons clear and recognizable

## Troubleshooting

### Durability Not Displaying

- Check condition indicator paths
- Verify icons are in `assets/durability/conditions/`
- Ensure DurabilityAgent is initialized

### Wear Not Tracking

- Check wear category icon paths
- Verify icons are in `assets/durability/wear/`
- Ensure wear system is enabled

### Repair Not Working

- Check repair UI element paths
- Verify elements are in `assets/durability/ui/repair/`
- Ensure repair system is enabled

### Effects Not Showing

- Check effect paths
- Verify effects are in `assets/durability/effects/`
- Ensure effect system is enabled

---

*Part of the Starbound Ollama Asset Generator suite*
