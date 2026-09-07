# Shield and Armor System

A production-ready, data-driven system for shields, armor plating UI, and shield particle effects in Transcendence.

## Overview

The system separates visuals, mechanics, and effects so artists and designers can iterate independently:

- **ShieldProfile**: Defines shield visuals and behavior
- **ArmorProfile**: Defines plating visuals and damage mitigation
- **ShieldInstance**: Runtime state for active shields
- **DamageEvent**: Standardized damage input
- **Particle Profiles**: Ambient and impact particle systems
- **UI Data Binding**: Shield ring, armor map, numeric readouts

## Core Components

### 1. Registry Schema (`shield_armor_registry_schema.json`)

Defines the structure for shield and armor definitions:
- Shield properties: maxStrength, rechargeRate, rechargeDelay, absorptionCurve
- Visual properties: radius, thickness, colors, pulse, distortion
- FX properties: hit flash, impact particles, sounds
- Armor slots: directional plating with damage reduction

### 2. Runtime Model (`shield_runtime_model.py`)

Python implementation of runtime state:
- `ShieldInstance`: Damage handling, recharge logic, state management
- `ArmorInstance`: Directional damage routing, slot management
- `DamageEvent`: Standardized damage input
- State tracking: active, recharging, broken, overloaded

### 3. Blender Renderer (`blender_shield_renderer.py`)

Renders shield visuals with:
- Procedural node groups for rim, pulse, distortion
- Sprite strip generation for fallback
- Normal map generation
- Editable .blend files with node groups

### 4. Shader Recipes (`SHADER_RECIPES.md`)

Production-ready shader code:
- GLSL/HLSL pseudocode for shield visuals
- Rim, core, pulse, distortion effects
- Hit flash and visual intensity
- Sprite strip fallback
- Performance optimizations and LOD

### 5. Particle Profiles (`particle_profile_schema.json`)

Particle system definitions:
- Ambient particles: continuous shield effects
- Impact particles: hit bursts
- Motion patterns: OrbitInwardSpiral, RadialBurst, NoiseDrift
- Blend modes, color gradients, trails

### 6. XML Exporter (`transcendence_shield_armor_exporter.py`)

Exports to Transcendence XML format:
- ShieldType elements with properties
- ArmorType elements with slots
- Visual and FX configuration
- UNID mapping

### 7. UI Data Binding (`ui_data_binding_model.json`)

Data model for UI:
- Shield state: current, max, percentage, state, visual intensity
- Armor slots: HP, percentage, damage reduction, visual damage
- Modes, power allocation, cooldowns

### 8. UI Layout (`UI_LAYOUT_SPEC.md`)

Complete UI specification:
- Shield ring overlay on ship silhouette
- Armor plating map with health bars
- Numeric readouts and state icons
- Interactive controls
- Animation guidelines

### 9. Pipeline Orchestrator (`ShieldArmorSystemGenerator.ps1`)

Main PowerShell script that:
- Reads registry JSON
- Calls Blender for rendering
- Exports particle systems
- Generates XML files
- Packages assets

## Usage

### Basic Usage

```powershell
.\ShieldArmorSystemGenerator.ps1 -RegistryPath "shield_armor_example.json" -ParticleProfilePath "particle_profiles_example.json" -OutputDir "Output"
```

### Generate Specific Shield

```powershell
.\ShieldArmorSystemGenerator.ps1 -RegistryPath "shield_armor_example.json" -ShieldId "energy_shield_mk2" -OutputDir "Output"
```

### Skip Rendering (XML Only)

```powershell
.\ShieldArmorSystemGenerator.ps1 -RegistryPath "shield_armor_example.json" -SkipRender -OutputDir "Output"
```

## Registry Example

See `shield_armor_example.json` for complete examples:
- **Energy Shield Mk2**: Standard shield with distortion
- **Plasma Barrier**: High-strength barrier with enhanced FX
- **Reinforced Plating Mk1**: 4-slot armor with damage reduction

## Runtime Integration

### Python

```python
from shield_runtime_model import CreateShieldInstance, DamageEvent

# Load profile
shield_profile = {...}  # From registry
shield = CreateShieldInstance(shield_profile)

# Apply damage
damage = DamageEvent(amount=30.0, damageType="laser")
remaining = shield.ApplyDamage(damage)

# Update each frame
shield.Update(dt=0.016)  # ~60 FPS

# Get state for UI
state = shield.GetState()
```

### C# (Unity/Similar)

```csharp
public class ShieldController : MonoBehaviour {
    private ShieldInstance shield;
    
    void Update() {
        shield.Update(Time.deltaTime);
        UpdateShaderParameters();
        UpdateUI();
    }
    
    public void OnHit(DamageEvent damage) {
        float remaining = shield.ApplyDamage(damage);
        if (remaining > 0) {
            // Apply to hull/armor
        }
    }
}
```

## Shader Integration

### Unity

```csharp
shieldMaterial.SetFloat("_VisualIntensity", shield.visualIntensity);
shieldMaterial.SetFloat("_HitFlashIntensity", shield.hitFlashIntensity);
shieldMaterial.SetVector("_HitPosition", lastHitPosition);
shieldMaterial.SetFloat("_Time", Time.time);
```

### Unreal

```cpp
ShieldMaterialInstance->SetScalarParameterValue("VisualIntensity", ShieldInstance->visualIntensity);
ShieldMaterialInstance->SetScalarParameterValue("HitFlashIntensity", ShieldInstance->hitFlashIntensity);
ShieldMaterialInstance->SetVectorParameterValue("HitPosition", LastHitPosition);
```

## Particle System Integration

Particle profiles define:
- Spawn shapes: disk, ring, sphere, point
- Motion patterns: OrbitInwardSpiral, RadialBurst, NoiseDrift
- Color gradients, blend modes, trails
- Lifetime, size, velocity ranges

See `particle_profiles_example.json` for examples.

## UI Integration

### Data Binding

```javascript
// Update shield ring
const shieldState = shieldInstance.GetState();
shieldRing.fillAmount = shieldState.percentage / 100.0;
shieldRing.color = lerp(damagedColor, baseColor, shieldState.percentage / 100.0);

// Update armor slots
armorSlots.forEach(slot => {
    const slotState = slot.GetState();
    updateHealthBar(slot.slot, slotState.percentage);
});
```

### Event Handling

```javascript
// On shield hit
function onShieldHit(damageEvent) {
    // Update UI
    updateShieldRing();
    showHitFlash(damageEvent.position);
    playSound('shieldHit');
    
    // Spawn impact particles
    spawnImpactParticles(damageEvent.position, particleProfile.impact);
}
```

## Performance Considerations

### Budgeting
- Limit ambient particle count per shield (12-16 recommended)
- Use GPU instancing for particles
- Use low-sample shader passes
- Provide LOD: High/Medium/Low quality settings

### Pooling
- Preallocate particle pools
- Reuse textures and materials
- Batch particle draws by blend mode

### Optimization
- Disable distortion on low-end devices
- Use sprite strips instead of shaders when needed
- Reduce particle counts at distance

## Testing Checklist

### Functional Tests
- [ ] Shield absorbs expected damage
- [ ] Recharge timing correct
- [ ] Shield break triggers correctly
- [ ] Armor damage reduction works
- [ ] Directional damage routing correct

### Visual Tests
- [ ] Hit flash aligns with hit position
- [ ] Particles spawn inside shield radius
- [ ] Shader pulse visible
- [ ] UI updates correctly
- [ ] Color gradients work

### Performance Tests
- [ ] Spawn many shields, measure frame time
- [ ] Test low/medium/high settings
- [ ] Verify particle pooling works
- [ ] Check LOD switching

### Gameplay Tests
- [ ] Shield/armor balance feels fair
- [ ] Edge cases: simultaneous multi-hit
- [ ] Recharge delay works correctly
- [ ] UI responsive and readable

## File Structure

```
Tools/
├── shield_armor_registry_schema.json    # JSON schema
├── shield_armor_example.json            # Example registry
├── particle_profile_schema.json         # Particle schema
├── particle_profiles_example.json      # Particle examples
├── shield_runtime_model.py              # Runtime state model
├── blender_shield_renderer.py          # Blender renderer
├── transcendence_shield_armor_exporter.py  # XML exporter
├── ui_data_binding_model.json          # UI data model
├── UI_LAYOUT_SPEC.md                   # UI layout spec
├── SHADER_RECIPES.md                   # Shader code
├── ShieldArmorSystemGenerator.ps1      # Main orchestrator
└── SHIELD_ARMOR_SYSTEM_README.md       # This file
```

## Future Enhancements

- Preview GUI for live preview + iterative AI tweak loop
- Advanced shader effects (refraction, caustics)
- Dynamic shield shapes (not just spheres)
- Shield modes with different behaviors
- Repair system integration
- Multi-layer shields

## Integration with Projectile System

The shield/armor system integrates with the projectile system:
- Projectiles apply `DamageEvent` to shields
- Shield absorption reduces projectile damage
- Remaining damage routes to armor
- Particle effects coordinate between systems

See `PROJECTILE_SYSTEM_README.md` for projectile system details.

