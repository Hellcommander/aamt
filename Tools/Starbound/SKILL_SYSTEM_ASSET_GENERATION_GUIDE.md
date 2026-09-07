# Skill System Asset Generation Guide

Generate assets for the Skill System including category icons, tier indicators, type indicators, skill tree UI, XP progress, level indicators, decay indicators, mastery indicators, specialization icons, and combo indicators.

## Quick Start

```powershell
# Generate all skill system assets
.\GenerateSkillSystemAssets.ps1

# Use C++ backend for better quality
.\GenerateSkillSystemAssets.ps1 -UseCppBackend

# Or generate everything at once
.\GenerateAllModSprites.ps1 -OllamaModel "codellama:7b-instruct"
```

## What Gets Generated

### Skill Category Icons (10 icons)

1. **skill_category_combat** - Combat skill category
2. **skill_category_magic** - Magic skill category
3. **skill_category_crafting** - Crafting skill category
4. **skill_category_technology** - Technology skill category
5. **skill_category_survival** - Survival skill category
6. **skill_category_social** - Social skill category
7. **skill_category_movement** - Movement skill category
8. **skill_category_defense** - Defense skill category
9. **skill_category_utility** - Utility skill category
10. **skill_category_mastery** - Mastery skill category

### Skill Tier Indicators (7 indicators)

1. **skill_tier_common** - Common tier
2. **skill_tier_uncommon** - Uncommon tier
3. **skill_tier_rare** - Rare tier
4. **skill_tier_epic** - Epic tier
5. **skill_tier_legendary** - Legendary tier
6. **skill_tier_mythic** - Mythic tier
7. **skill_tier_transcendent** - Transcendent tier

### Skill Type Indicators (6 indicators)

1. **skill_type_active** - Active skill type
2. **skill_type_passive** - Passive skill type
3. **skill_type_triggered** - Triggered skill type
4. **skill_type_channeled** - Channeled skill type
5. **skill_type_toggle** - Toggle skill type
6. **skill_type_combo** - Combo skill type

### Skill Tree UI Elements (5 elements)

1. **skill_tree_node_unlocked** - Unlocked node icon
2. **skill_tree_node_locked** - Locked node icon
3. **skill_tree_node_available** - Available node icon
4. **skill_tree_connection** - Connection line texture
5. **skill_tree_background** - Skill tree background texture

### XP Progress Indicators (4 indicators)

1. **xp_bar** - XP progress bar
2. **xp_gain_effect** - XP gain particle effect
3. **xp_milestone** - XP milestone indicator
4. **level_up_effect** - Level up particle effect

### Skill Level Indicators (4 indicators)

1. **skill_level_1** - Level 1 indicator
2. **skill_level_5** - Level 5 indicator
3. **skill_level_10** - Level 10 indicator
4. **skill_level_max** - Max level indicator

### Decay Indicators (5 indicators)

1. **skill_decay_indicator** - Decay indicator
2. **skill_decay_warning** - Decay warning
3. **skill_retention_high** - High retention indicator
4. **skill_retention_low** - Low retention indicator
5. **skill_practice_effect** - Practice particle effect

### Mastery Indicators (4 indicators)

1. **mastery_icon** - Mastery icon
2. **mastery_unlocked** - Mastery unlocked indicator
3. **mastery_progress** - Mastery progress indicator
4. **mastery_effect** - Mastery particle effect

### Specialization Icons (3 icons)

1. **specialization_icon** - Specialization icon
2. **specialization_selected** - Specialization selected indicator
3. **specialization_available** - Specialization available indicator

### Skill Combo Indicators (3 indicators)

1. **combo_indicator** - Combo indicator
2. **combo_active** - Combo active indicator
3. **combo_execute** - Combo execute particle effect

### Cooldown Indicators (3 indicators)

1. **skill_cooldown_indicator** - Cooldown indicator
2. **skill_cooldown_bar** - Cooldown progress bar
3. **skill_ready** - Skill ready indicator

## Total: ~54 Assets

## Output Structure

```
assets/
├── skills/
│   ├── categories/
│   │   ├── skill_category_combat.png
│   │   ├── skill_category_magic.png
│   │   └── ... (all category icons)
│   ├── tiers/
│   │   ├── skill_tier_common.png
│   │   ├── skill_tier_uncommon.png
│   │   └── ... (all tier indicators)
│   ├── types/
│   │   ├── skill_type_active.png
│   │   ├── skill_type_passive.png
│   │   └── ... (all type indicators)
│   ├── skill_tree/
│   │   ├── skill_tree_node_unlocked.png
│   │   ├── skill_tree_node_locked.png
│   │   ├── skill_tree_node_available.png
│   │   ├── skill_tree_connection.png
│   │   └── skill_tree_background.png
│   ├── xp/
│   │   ├── xp_bar.png
│   │   ├── xp_gain_effect.particle
│   │   ├── xp_milestone.png
│   │   └── level_up_effect.particle
│   ├── levels/
│   │   ├── skill_level_1.png
│   │   ├── skill_level_5.png
│   │   ├── skill_level_10.png
│   │   └── skill_level_max.png
│   ├── decay/
│   │   ├── skill_decay_indicator.png
│   │   ├── skill_decay_warning.png
│   │   ├── skill_retention_high.png
│   │   ├── skill_retention_low.png
│   │   └── skill_practice_effect.particle
│   ├── mastery/
│   │   ├── mastery_icon.png
│   │   ├── mastery_unlocked.png
│   │   ├── mastery_progress.png
│   │   └── mastery_effect.particle
│   ├── specialization/
│   │   ├── specialization_icon.png
│   │   ├── specialization_selected.png
│   │   └── specialization_available.png
│   ├── combo/
│   │   ├── combo_indicator.png
│   │   ├── combo_active.png
│   │   └── combo_execute.particle
│   └── cooldown/
│       ├── skill_cooldown_indicator.png
│       ├── skill_cooldown_bar.png
│       └── skill_ready.png
```

## Integration

### TrueSkillSystem

```cpp
// Register skill
TrueSkillSystem::registerSkill(skill);
// Uses: /skills/categories/skill_category_*.png based on category
// Uses: /skills/tiers/skill_tier_*.png based on tier
// Uses: /skills/types/skill_type_*.png based on type
// Uses: skill.icon path for skill icon

// Unlock skill
TrueSkillSystem::unlockSkill(playerId, skillId);
// Uses: /skills/skill_tree/skill_tree_node_unlocked.png

// Level up skill
TrueSkillSystem::levelUpSkill(playerId, skillId);
// Uses: /skills/xp/level_up_effect.particle
// Uses: /skills/levels/skill_level_*.png based on level

// Award XP
TrueSkillSystem::awardSkillXP(playerId, skillId, xp);
// Uses: /skills/xp/xp_gain_effect.particle
// Uses: /skills/xp/xp_bar.png for progress display
```

### Skill Tree Visualization

```cpp
// Generate skill tree
TrueSkillSystem::generateSkillTree(category);
// Uses: /skills/skill_tree/skill_tree_background.png for background
// Uses: /skills/skill_tree/skill_tree_node_*.png for nodes
// Uses: /skills/skill_tree/skill_tree_connection.png for connections
```

### Skill Decay System

```cpp
// Update decay
TrueSkillSystem::updateSkillDecay(deltaTime);
// Uses: /skills/decay/skill_decay_indicator.png if decaying
// Uses: /skills/decay/skill_decay_warning.png if warning threshold
// Uses: /skills/decay/skill_retention_high.png if good retention
// Uses: /skills/decay/skill_retention_low.png if poor retention

// Practice skill
TrueSkillSystem::practiceSkill(playerId, skillId, quality);
// Uses: /skills/decay/skill_practice_effect.particle
```

### Mastery System

```cpp
// Check mastery
TrueSkillSystem::checkMasteryProgress(playerId, skillId);
// Uses: /skills/mastery/mastery_progress.png for progress
// Uses: /skills/mastery/mastery_unlocked.png when unlocked
// Uses: /skills/mastery/mastery_effect.particle on unlock
```

### Specialization System

```cpp
// Select specialization
TrueSkillSystem::selectSpecialization(playerId, skillId, specializationId);
// Uses: /skills/specialization/specialization_selected.png
// Uses: /skills/specialization/specialization_icon.png
```

### Combo System

```cpp
// Check combo
TrueSkillSystem::checkCombo(playerId, recentSkills);
// Uses: /skills/combo/combo_indicator.png if combo available
// Uses: /skills/combo/combo_active.png if combo in progress

// Execute combo
TrueSkillSystem::executeCombo(playerId, comboId);
// Uses: /skills/combo/combo_execute.particle
```

### Cooldown System

```cpp
// Check cooldown
TrueSkillSystem::isOnCooldown(playerId, skillId);
// Uses: /skills/cooldown/skill_cooldown_indicator.png if on cooldown
// Uses: /skills/cooldown/skill_cooldown_bar.png for cooldown progress
// Uses: /skills/cooldown/skill_ready.png if ready
```

## Skill Categories

### Category Types
- **Combat**: Combat-related skills
- **Magic**: Magic and spell skills
- **Crafting**: Crafting and creation skills
- **Technology**: Tech and engineering skills
- **Survival**: Survival and resource skills
- **Social**: Social and interaction skills
- **Movement**: Movement and mobility skills
- **Defense**: Defense and protection skills
- **Utility**: Utility and general skills
- **Mastery**: Mastery and advanced skills

## Skill Tiers

### Tier Levels
- **Common**: Basic skills
- **Uncommon**: Improved skills
- **Rare**: Advanced skills
- **Epic**: Expert skills
- **Legendary**: Master skills
- **Mythic**: Legendary skills
- **Transcendent**: Ultimate skills

## Skill Types

### Type Classifications
- **Active**: Must be activated
- **Passive**: Always active
- **Triggered**: Activates on conditions
- **Channeled**: Requires continuous activation
- **Toggle**: Can be turned on/off
- **Combo**: Chains with other skills

## Workflow

### Step 1: Generate Assets

```powershell
.\GenerateSkillSystemAssets.ps1 -OllamaModel "codellama:7b-instruct"
```

### Step 2: Register Skills

Register skill definitions with category, tier, and type.

### Step 3: Configure Skill Trees

Set up skill trees with prerequisites.

### Step 4: Test in Game

Load the mod and test skill system in-game.

## Advanced Options

### Custom Skill Categories

Edit `GenerateSkillSystemAssets.ps1` to add custom skill categories.

### Custom Skill Tiers

Add custom tier indicators as needed.

### Custom Skill Types

Add custom type indicators for new skill types.

## Tips

1. **Category icons**: Use 32x32 for UI display
2. **Tier indicators**: Use 16x16 for small indicators
3. **Type indicators**: Use 16x16 for type badges
4. **Skill tree**: Use 32x32 for nodes, 256x256 for background
5. **XP bars**: Use 32x8 for progress bars
6. **Decay indicators**: Make decay warnings clearly visible
7. **Mastery effects**: Use impressive particle effects for mastery

## Troubleshooting

### Skills Not Displaying

- Check skill icon paths in skill definitions
- Verify icons are in `assets/skills/`
- Ensure skill system is initialized

### Skill Tree Not Rendering

- Check skill tree UI paths
- Verify elements are in `assets/skills/skill_tree/`
- Ensure skill tree system is initialized

### Decay Not Showing

- Check decay indicator paths
- Verify indicators are in `assets/skills/decay/`
- Ensure decay system is initialized

---

*Part of the Starbound Ollama Asset Generator suite*
