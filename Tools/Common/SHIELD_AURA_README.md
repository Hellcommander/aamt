# Solar Wind Shield Aura System

A production-ready system for generating Nova Drift-inspired solar wind shield auras with alpha noise fluctuations, orbital particles, and projectile gravity well behavior.

## Overview

The system creates shield auras that:
- **Alpha Noise**: Randomly fluctuating alpha channels like solar wind
- **Scale with Shield Power**: Radius, alpha, and speed scale with shield HP
- **Gravity Well**: Projectiles get "caught" and orbit the player
- **Nova Drift Aesthetic**: High-energy, additive glows, procedural distortion
- **Layered Composition**: Base aura → wind streams → distortion → orbital particles

## Core Components

### 1. Registry Schema (`shield_aura_registry_schema.json`)

Defines aura structure:
- Visual: colors, radius scaling, alpha noise, distortion, wind streams
- Particles: orbital count, speed, gravity strength, turbulence
- Behavior: projectile influence, orbit time, shield HP scaling
- Export: UNID, Transcendence format, resource paths

### 2. Shader Recipes (`SHIELD_AURA_SHADER_RECIPES.md`)

Production-ready shader code:
- Alpha noise layer with animated Perlin/Voronoi noise
- Solar wind streams with directional flow
- Distortion field with heat-haze wobble
- Orbital particles with gravity well motion
- Shield HP scaling for all properties

### 3. Projectile Orbit Behavior (`projectile_orbit_behavior.py`)

Runtime system for projectile gravity well:
- Tangential velocity blending (orbit motion)
- Inward gravitational pull
- Orbit time limits
- Shield HP scaling

### 4. Blender Renderer (`blender_shield_aura_renderer.py`)

Renders layered aura:
- Base aura with alpha noise
- Wind streak meshes
- Orbital particle systems
- Multiple shield HP levels
- Spritesheet compositing

### 5. XML Exporter (`transcendence_shield_aura_exporter.py`)

Exports to Transcendence format:
- AuraType elements
- Visual and behavior properties
- Particle system definitions
- UNID mapping

### 6. Pipeline Orchestrator (`ShieldAuraGenerator.ps1`)

Main PowerShell script:
- Reads aura registry
- Calls Blender for rendering
- Exports XML files
- Packages assets

## Usage

### Basic Usage

```powershell
.\ShieldAuraGenerator.ps1 -RegistryPath "shield_aura_example.json" -OutputDir "Output"
```

### Generate Specific Aura

```powershell
.\ShieldAuraGenerator.ps1 -RegistryPath "shield_aura_example.json" -AuraId "solar_wind_shield" -OutputDir "Output"
```

### Skip Rendering (XML Only)

```powershell
.\ShieldAuraGenerator.ps1 -RegistryPath "shield_aura_example.json" -SkipRender -OutputDir "Output"
```

## Registry Example

See `shield_aura_example.json` for complete examples:
- **solar_wind_shield**: Standard solar wind aura with moderate gravity
- **plasma_gravity_field**: Strong gravity field with high particle count

## Aura Layers

### Base Aura (Alpha Noise Layer)
- Circular/elliptical field around ship
- Alpha fluctuates using animated noise
- Color shifts with shield strength
- Radius scales with shield HP

### Solar Wind Streams
- Thin, wispy streaks
- Flow outward or swirl around ship
- Alpha flickers independently
- Driven by noise + radial velocity

### Distortion Field
- Heat-haze style wobble
- Radial displacement
- Stronger near shield edge
- Animated with time

### Orbital Particle Field
- Particles orbit the ship
- Speed depends on shield strength
- Gravity well behavior
- Turbulence for organic motion

## Projectile Orbit Behavior

When a projectile enters the aura:

1. **Compute Radial Vector**: Direction from player to projectile
2. **Compute Tangential Vector**: Perpendicular to radial (orbit direction)
3. **Blend Velocity**: Gradually blend projectile velocity toward tangential
4. **Add Inward Pull**: Gravity well effect pulls projectiles inward
5. **Limit Orbit Time**: Release after `projectileOrbitTime` seconds

This makes fast projectiles "curve" and slow ones "orbit" around the player.

## Shield HP Scaling

As shield HP changes:
- **Radius**: Interpolates between `radiusMin` and `radiusMax`
- **Alpha**: Increases with strength
- **Wind Speed**: Increases with strength
- **Distortion Strength**: Increases with strength
- **Particle Orbit Speed**: Increases with strength

Scaling curves: linear, exponential, logarithmic, smooth

## Shader Integration

### Unity

```csharp
public class ShieldAuraController : MonoBehaviour {
    public Material auraMaterial;
    public ShieldInstance shield;
    
    void Update() {
        float shieldHP = shield.currentStrength / shield.maxStrength;
        auraMaterial.SetFloat("_ShieldHP", shieldHP);
        auraMaterial.SetFloat("_Time", Time.time);
        auraMaterial.SetVector("_AuraCenter", transform.position);
    }
}
```

### Projectile Orbit Integration

```csharp
void UpdateProjectile(Projectile proj, float dt) {
    Vector2 dir = proj.position - transform.position;
    float dist = dir.magnitude;
    
    if (dist > influenceRadius) return;
    
    // Tangential vector
    Vector2 radial = dir.normalized;
    Vector2 tangent = new Vector2(-radial.y, radial.x);
    
    // Blend toward orbit
    float blend = tangentialBlend * gravityStrength * dt;
    proj.velocity = Vector2.Lerp(proj.velocity, tangent * orbitSpeed, blend);
    
    // Inward pull
    proj.velocity -= radial * inwardPull * dt;
}
```

## Transcendence Integration

### XML Format

```xml
<AuraType unid="&auSolarWindShield;">
    <name>Solar Wind Shield</name>
    <visual radiusMin="1.2" radiusMax="2.4" baseColor="#66ccff"/>
    <alphaNoise speed="1.8" scale="3.2" strength="0.6"/>
    <distortion strength="0.05" frequency="2.6" type="heatHaze"/>
    <particles orbitCount="24" orbitSpeedMin="0.4" orbitSpeedMax="1.6"/>
    <behavior projectileInfluence="true" projectileOrbitTime="0.3"/>
    <image>Resources/Auras/solar_wind_shield.png</image>
</AuraType>
```

## File Structure

```
Tools/
├── shield_aura_registry_schema.json    # JSON schema
├── shield_aura_example.json           # Example registry
├── SHIELD_AURA_SHADER_RECIPES.md      # Shader code
├── projectile_orbit_behavior.py      # Orbit behavior system
├── blender_shield_aura_renderer.py    # Blender renderer
├── transcendence_shield_aura_exporter.py  # XML exporter
├── ShieldAuraGenerator.ps1            # Main orchestrator
└── SHIELD_AURA_README.md              # This file
```

## Integration with Other Systems

- **Shield System**: Aura scales with shield HP and state
- **Projectile System**: Projectiles get influenced by aura gravity
- **FX System**: Aura can trigger visual effects on projectile capture
- **UI System**: Aura visibility can be toggled in UI

## Performance Considerations

- Limit orbital particle count (24-32 recommended)
- Use sprite strips for base aura (not real-time shader)
- Provide LOD: High/Medium/Low quality settings
- Batch aura renders by shader/material
- Pool particle systems

## Testing Checklist

- [ ] Aura renders correctly at all shield HP levels
- [ ] Alpha noise animates smoothly
- [ ] Wind streams flow correctly
- [ ] Distortion field visible
- [ ] Orbital particles orbit correctly
- [ ] Projectiles get caught and orbit
- [ ] Shield HP scaling works
- [ ] XML exports correctly
- [ ] Performance acceptable

## Future Enhancements

- Real-time shader implementation
- Advanced turbulence patterns
- Multi-layer distortion
- Sound effects for projectile capture
- Visual feedback on projectile orbit
- Integration with shield break effects

