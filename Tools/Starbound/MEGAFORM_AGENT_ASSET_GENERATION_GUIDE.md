# MegaFormAgent System Asset Generation Guide

Generate visual assets for the MegaFormAgent System including form shapes, effects, templates, event indicators, curve visualizations, transformations, and category icons.

## Quick Start

```powershell
# Generate all MegaFormAgent assets
.\GenerateMegaFormAgentAssets.ps1

# Use C++ backend for better quality
.\GenerateMegaFormAgentAssets.ps1 -UseCppBackend

# Or generate everything at once
.\GenerateAllModSprites.ps1 -OllamaModel "codellama:7b-instruct"
```

## What Gets Generated

### Form Shape Sprites (10 shapes)

1. **shape_circle** - Circle spell form shape
2. **shape_square** - Square spell form shape
3. **shape_triangle** - Triangle spell form shape
4. **shape_star** - Star spell form shape
5. **shape_hexagon** - Hexagon spell form shape
6. **shape_diamond** - Diamond spell form shape
7. **shape_cross** - Cross spell form shape
8. **shape_spiral** - Spiral spell form shape
9. **shape_wave** - Wave spell form shape
10. **shape_orb** - Orb spell form shape

### Form Effect Particles (10 effects)

1. **effect_energy_burst** - Energy burst particle effect
2. **effect_glow_aura** - Glow aura particle effect
3. **effect_sparkle** - Sparkle particle effect
4. **effect_trail** - Trail particle effect
5. **effect_ripple** - Ripple particle effect
6. **effect_swirl** - Swirl particle effect
7. **effect_pulse** - Pulse particle effect
8. **effect_orbiting** - Orbiting particle effect
9. **effect_cascade** - Cascade particle effect
10. **effect_dissolve** - Dissolve particle effect

### Form Template Icons (8 templates)

1. **template_basic** - Basic spell form template
2. **template_advanced** - Advanced spell form template
3. **template_elemental** - Elemental spell form template
4. **template_combat** - Combat spell form template
5. **template_utility** - Utility spell form template
6. **template_defensive** - Defensive spell form template
7. **template_offensive** - Offensive spell form template
8. **template_support** - Support spell form template

### Event Trigger Visual Indicators (5 indicators)

1. **event_onhit** - OnHit event trigger indicator
2. **event_ontimer** - OnTimer event trigger indicator
3. **event_ondistance** - OnDistance event trigger indicator
4. **event_triggered** - Event triggered visual indicator
5. **event_cooldown** - Event cooldown visual indicator

### Curve Visualization Elements (5 elements)

1. **curve_scale** - Scale curve visualization
2. **curve_color** - Color curve visualization
3. **curve_speed** - Speed curve visualization
4. **curve_keyframe** - Curve keyframe indicator
5. **curve_interpolation** - Curve interpolation visualization

### Form Transformation Effects (6 effects)

1. **transform_morph** - Morph transformation effect
2. **transform_scale** - Scale transformation effect
3. **transform_rotate** - Rotate transformation effect
4. **transform_color** - Color transformation effect
5. **transform_fade** - Fade transformation effect
6. **transform_glow** - Glow transformation effect

### Form Category Icons (6 icons)

1. **category_elemental** - Elemental form category
2. **category_combat** - Combat form category
3. **category_utility** - Utility form category
4. **category_defensive** - Defensive form category
5. **category_offensive** - Offensive form category
6. **category_support** - Support form category

## Total: ~50 Assets

## Output Structure

```
assets/
├── shapes/
│   ├── shape_circle.png
│   ├── shape_square.png
│   ├── shape_triangle.png
│   └── ... (all shape sprites)
├── effects/
│   ├── effect_energy_burst.particle
│   ├── effect_glow_aura.particle
│   └── ... (all effect particles)
├── forms/
│   ├── templates/
│   │   ├── template_basic.png
│   │   ├── template_advanced.png
│   │   └── ... (all template icons)
│   ├── events/
│   │   ├── event_onhit.png
│   │   ├── event_ontimer.png
│   │   └── ... (all event indicators)
│   ├── curves/
│   │   ├── curve_scale.png
│   │   ├── curve_color.png
│   │   └── ... (all curve elements)
│   ├── transformations/
│   │   ├── transform_morph.particle
│   │   ├── transform_scale.particle
│   │   └── ... (all transformation effects)
│   └── categories/
│       ├── category_elemental.png
│       ├── category_combat.png
│       └── ... (all category icons)
```

## Integration

### MegaFormAgent

```cpp
// Generate form
MegaFormAgent::generateForm(entityId, ingredients, userSeed);
// Uses: /assets/shapes/shape_*.png for form shapes
// Uses: /assets/effects/effect_*.particle for form effects
// Uses: /assets/forms/templates/template_*.png for templates

// Register shape
MegaFormAgent::registerShape(id, weight, morphTargets);
// Uses: /assets/shapes/shape_*.png

// Register effect
MegaFormAgent::registerEffect(effectTemplate);
// Uses: /assets/effects/effect_*.particle

// Trigger event
MegaFormAgent::triggerEvent(EventType::OnHit, value, form);
// Uses: /assets/forms/events/event_onhit.png
// Uses: /assets/forms/events/event_triggered.png

// Apply curve
MegaFormAgent::applyCurveToForm(form, scaleCurve, colorCurve);
// Uses: /assets/forms/curves/curve_scale.png
// Uses: /assets/forms/curves/curve_color.png
// Uses: /assets/forms/curves/curve_keyframe.png

// Get forms by category
MegaFormAgent::getFormsByCategory("elemental");
// Uses: /assets/forms/categories/category_elemental.png
```

### AgentConfig

```cpp
AgentConfig config;
config.formTemplatesPath = "assets/forms/templates/";
config.shapeAssetsPath = "assets/shapes/";
config.effectAssetsPath = "assets/effects/";
// Audio assets are handled separately
```

## Form Shapes

### Shape Types
- **Circle**: Circular spell form
- **Square**: Square spell form
- **Triangle**: Triangular spell form
- **Star**: Star-shaped spell form
- **Hexagon**: Hexagonal spell form
- **Diamond**: Diamond-shaped spell form
- **Cross**: Cross-shaped spell form
- **Spiral**: Spiral spell form
- **Wave**: Wavy spell form
- **Orb**: Orb-shaped spell form

### Morph Targets
Shapes can morph between different targets using the `morphTargets` parameter in `registerShape()`.

## Form Effects

### Effect Types
- **Energy Burst**: Explosive energy effect
- **Glow Aura**: Glowing aura effect
- **Sparkle**: Sparkle particle effect
- **Trail**: Motion trail effect
- **Ripple**: Ripple wave effect
- **Swirl**: Swirling energy effect
- **Pulse**: Pulsing energy effect
- **Orbiting**: Orbiting particles effect
- **Cascade**: Cascading energy effect
- **Dissolve**: Dissolving energy effect

## Event System

### Event Types
- **OnHit**: Triggered when form hits target
- **OnTimer**: Triggered after timer expires
- **OnDistance**: Triggered when form reaches distance

### Event Indicators
- **Event Triggered**: Visual indicator for active events
- **Event Cooldown**: Visual indicator for event cooldowns

## Curve System

### Curve Types
- **Scale Curve**: Controls form scaling over time
- **Color Curve**: Controls form color transitions
- **Speed Curve**: Controls form movement speed

### Curve Elements
- **Keyframe**: Keyframe markers for curve editing
- **Interpolation**: Interpolation visualization

## Transformation Effects

### Transformation Types
- **Morph**: Shape morphing transformation
- **Scale**: Scaling transformation
- **Rotate**: Rotation transformation
- **Color**: Color shift transformation
- **Fade**: Fading transformation
- **Glow**: Glowing transformation

## Form Categories

### Category Types
- **Elemental**: Elemental spell forms
- **Combat**: Combat spell forms
- **Utility**: Utility spell forms
- **Defensive**: Defensive spell forms
- **Offensive**: Offensive spell forms
- **Support**: Support spell forms

## Workflow

### Step 1: Generate Assets

```powershell
.\GenerateMegaFormAgentAssets.ps1 -OllamaModel "codellama:7b-instruct"
```

### Step 2: Configure MegaFormAgent

Set up AgentConfig with asset paths.

### Step 3: Register Shapes and Effects

```cpp
megaFormAgent.registerShape("circle", 1.0f, {"square", "triangle"});
megaFormAgent.registerEffect(effectTemplate);
```

### Step 4: Generate Forms

```cpp
MegaSpellForm form = megaFormAgent.generateForm(entityId, ingredients, userSeed);
```

### Step 5: Test in Game

Load the mod and test form generation in-game.

## Advanced Options

### Custom Form Shapes

Edit `GenerateMegaFormAgentAssets.ps1` to add custom form shapes.

### Custom Form Effects

Add custom form effects as needed for specific spell types.

### Custom Event Indicators

Add custom event indicators for additional event types.

## Tips

1. **Shape sprites**: Use 64x64 for form shapes
2. **Effect particles**: Use appropriate sizes for particle effects
3. **Template icons**: Use 32x32 for template icons
4. **Event indicators**: Make events clearly visible
5. **Curve elements**: Keep curves simple and clear
6. **Transformation effects**: Make transformations smooth
7. **Category icons**: Keep categories distinct

## Troubleshooting

### Forms Not Generating

- Check shape asset paths
- Verify shapes are in `assets/shapes/`
- Ensure MegaFormAgent is initialized

### Effects Not Showing

- Check effect asset paths
- Verify effects are in `assets/effects/`
- Ensure effects are registered

### Events Not Triggering

- Check event indicator paths
- Verify indicators are in `assets/forms/events/`
- Ensure event handlers are registered

### Curves Not Applying

- Check curve element paths
- Verify curves are in `assets/forms/curves/`
- Ensure curves are properly formatted

---

*Part of the Starbound Ollama Asset Generator suite*
