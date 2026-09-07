# Spell System Asset Generation Guide

Generate assets for the Spell Systems including spellcasting, spell reactions, and spell projectiles.

## Quick Start

```powershell
# Generate all spell system assets
.\GenerateSpellSystemAssets.ps1

# Use C++ backend for better quality
.\GenerateSpellSystemAssets.ps1 -UseCppBackend

# Or generate everything including spell system assets
.\GenerateAllModSprites.ps1 -OllamaModel "codellama:7b-instruct"
```

## What Gets Generated

### Spell Projectiles - Element Types (10 projectiles)

1. **spell_projectile_fire** - Fire projectile
2. **spell_projectile_ice** - Ice projectile
3. **spell_projectile_lightning** - Lightning projectile
4. **spell_projectile_arcane** - Arcane projectile
5. **spell_projectile_nature** - Nature projectile
6. **spell_projectile_shadow** - Shadow projectile
7. **spell_projectile_light** - Light projectile
8. **spell_projectile_poison** - Poison projectile
9. **spell_projectile_physical** - Physical projectile
10. **spell_projectile_void** - Void projectile

### Preset Spell Projectiles (8 projectiles)

1. **spell_fireball** - Fireball spell
2. **spell_ice_shard** - Ice shard spell
3. **spell_lightning_bolt** - Lightning bolt spell
4. **spell_magic_missile** - Magic missile spell
5. **spell_poison_cloud** - Poison cloud spell
6. **spell_healing_orb** - Healing orb spell
7. **spell_shield_barrier** - Shield barrier spell
8. **spell_meteor_strike** - Meteor strike spell

### Spell Trail Effects (9 effects)

1. **spell_trail_fire** - Fire trail
2. **spell_trail_ice** - Ice trail
3. **spell_trail_lightning** - Lightning trail
4. **spell_trail_arcane** - Arcane trail
5. **spell_trail_nature** - Nature trail
6. **spell_trail_shadow** - Shadow trail
7. **spell_trail_light** - Light trail
8. **spell_trail_poison** - Poison trail
9. **spell_trail_void** - Void trail

### Spell Impact Effects (9 effects)

1. **spell_impact_fire** - Fire impact
2. **spell_impact_ice** - Ice impact
3. **spell_impact_lightning** - Lightning impact
4. **spell_impact_arcane** - Arcane impact
5. **spell_impact_nature** - Nature impact
6. **spell_impact_shadow** - Shadow impact
7. **spell_impact_light** - Light impact
8. **spell_impact_poison** - Poison impact
9. **spell_impact_void** - Void impact

### Spell Shape Textures (9 textures)

1. **spell_shape_sphere** - Sphere shape
2. **spell_shape_cone** - Cone shape
3. **spell_shape_beam** - Beam shape
4. **spell_shape_wave** - Wave shape
5. **spell_shape_helix** - Helix shape
6. **spell_shape_cube** - Cube shape
7. **spell_shape_torus** - Torus shape
8. **spell_shape_star** - Star shape
9. **spell_shape_rune** - Rune shape

### Spell Reaction Effects (5 effects)

1. **reaction_projectile_hit_surface** - Projectile hit surface
2. **reaction_projectile_collide** - Projectile collide
3. **reaction_spell_impact** - Spell impact reaction
4. **reaction_terrain_transform** - Terrain transform
5. **reaction_area_effect** - Area effect

### Spell Fusion Effects (4 effects)

1. **fusion_effect_start** - Fusion start
2. **fusion_effect_process** - Fusion process
3. **fusion_effect_complete** - Fusion complete
4. **fusion_effect_failed** - Fusion failed

### Summon Sprites (6 sprites)

1. **summon_generic** - Generic summon
2. **summon_elemental_fire** - Fire elemental
3. **summon_elemental_ice** - Ice elemental
4. **summon_elemental_lightning** - Lightning elemental
5. **summon_turret** - Turret summon
6. **summon_minion** - Minion summon

### Spellcasting UI Elements (4 elements)

1. **ui_mana_bar** - Mana bar
2. **ui_cooldown_indicator** - Cooldown indicator
3. **ui_spell_ready** - Spell ready indicator
4. **ui_spell_casting** - Spell casting indicator

## Total: ~64 Assets

## Output Structure

```
assets/
├── spells/
│   ├── projectiles/
│   │   ├── spell_projectile_fire.png
│   │   ├── spell_projectile_ice.png
│   │   └── ... (all element projectiles + preset spells)
│   ├── trails/
│   │   ├── spell_trail_fire.particle
│   │   ├── spell_trail_ice.particle
│   │   └── ... (all trail effects)
│   ├── impacts/
│   │   ├── spell_impact_fire.particle
│   │   ├── spell_impact_ice.particle
│   │   └── ... (all impact effects)
│   ├── shapes/
│   │   ├── spell_shape_sphere.png
│   │   ├── spell_shape_cone.png
│   │   └── ... (all shape textures)
│   ├── reactions/
│   │   ├── reaction_projectile_hit_surface.particle
│   │   ├── reaction_projectile_collide.particle
│   │   └── ... (all reaction effects)
│   ├── fusion/
│   │   ├── fusion_effect_start.particle
│   │   ├── fusion_effect_process.particle
│   │   └── ... (all fusion effects)
│   ├── summons/
│   │   ├── summon_generic.png
│   │   ├── summon_elemental_fire.png
│   │   └── ... (all summon sprites)
│   └── ui/
│       ├── ui_mana_bar.png
│       ├── ui_cooldown_indicator.png
│       └── ... (all UI elements)
```

## Integration

### Spell Projectile System

```cpp
// Cast spell
SpellProjectileSystem::castSpell("fireball", origin, direction);
// Uses: /spells/projectiles/spell_fireball.png
// Uses: /spells/trails/spell_trail_fire.particle
// Uses: /spells/impacts/spell_impact_fire.particle on impact
```

### Spell Shape System

```cpp
// Generate shaped spell
SpellShapeSystem::generateShapedSpellMesh(shape, spellType);
// Uses: /spells/shapes/spell_shape_*.png textures
```

### Spell Reaction System

```cpp
// Handle projectile hit surface
SpellReactionSystem::onProjectileHitSurface(projectile, surface);
// Uses: /spells/reactions/reaction_projectile_hit_surface.particle

// Handle projectile collision (fusion)
SpellReactionSystem::onProjectileCollideProjectile(projA, projB);
// Uses: /spells/fusion/fusion_effect_*.particle
```

### Spellcasting Module

```cpp
// Cast spell through module
SpellcastingModule::onKeyPressed("spell_key");
// Uses: /spells/ui/ui_spell_casting.png indicator
// Uses: /spells/ui/ui_mana_bar.png for mana display
// Uses: /spells/ui/ui_cooldown_indicator.png for cooldown
```

## Element Types

### Spell Elements
- **Fire**: Red/orange flame
- **Ice**: Blue/white ice
- **Lightning**: Yellow/white electrical
- **Arcane**: Purple magical energy
- **Nature**: Green organic
- **Shadow**: Dark/black shadow
- **Light**: White/yellow holy
- **Poison**: Green toxic
- **Physical**: Grey kinetic
- **Void**: Black/purple void

## Spell Types

### Projectile Types
- **PROJECTILE**: Standard projectile (fireball, ice shard)
- **BEAM**: Continuous beam (lightning, laser)
- **AOE**: Area of effect (explosion, nova)
- **HITSCAN**: Instant hit (railgun)
- **PERSISTENT**: Ongoing effect (wall of fire, poison cloud)
- **HOMING**: Seeking projectiles
- **CHAIN**: Chain effects (chain lightning)
- **SUMMON**: Summoned entities
- **BUFF_DEBUFF**: Status effects
- **SHIELD**: Barriers, deflection fields

## Spell Shapes

### Base Shapes
- **SPHERE**: Spherical projectile
- **CONE**: Cone/spray shape
- **BEAM**: Linear beam
- **WAVE**: Expanding wave
- **HELIX**: Spiral/helix shape
- **CUBE**: Cubic form
- **TORUS**: Donut shape
- **STAR**: Star pattern
- **RUNE**: Runic symbol

## Workflow

### Step 1: Generate Assets

```powershell
.\GenerateSpellSystemAssets.ps1 -OllamaModel "codellama:7b-instruct"
```

### Step 2: Register Spells

Register spell definitions with the SpellProjectileSystem.

### Step 3: Configure Reactions

Set up reaction rules in SpellReactionSystem.

### Step 4: Test in Game

Load the mod and test spell casting in-game.

## Advanced Options

### Custom Element Types

Edit `GenerateSpellSystemAssets.ps1` to add custom element types:

```powershell
@{
    Id = "spell_projectile_custom"
    Name = "Custom Element Projectile"
    Desc = "Custom element projectile description, 32x32"
}
```

### Custom Spell Shapes

Add custom spell shape textures to the `$spellShapes` array.

### Custom Preset Spells

Add custom preset spell projectiles to the `$presetSpells` array.

## Tips

1. **Projectile sprites**: Use 32x32 for most, 64x64 for large spells
2. **Trail effects**: Match trail color to element type
3. **Impact effects**: Create distinct impacts for each element
4. **Shape textures**: Use 64x64 for shape textures
5. **UI elements**: Use appropriate sizes for UI (32x32 for icons, 32x8 for bars)

## Troubleshooting

### Projectiles Not Appearing

- Check projectile sprite paths in spell definitions
- Verify projectiles are in `assets/spells/projectiles/`
- Ensure SpellProjectileSystem is initialized

### Trails Not Showing

- Verify trail effect paths in spell definitions
- Check effects are in `assets/spells/trails/`
- Ensure particle system is initialized

### Reactions Not Triggering

- Check reaction effect paths in reaction rules
- Verify effects are in `assets/spells/reactions/`
- Ensure SpellReactionSystem is configured

---

*Part of the Starbound Ollama Asset Generator suite*
