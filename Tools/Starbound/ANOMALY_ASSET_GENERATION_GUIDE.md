# Anomaly System Asset Generation Guide

Generate assets for the Anomaly Systems including black holes, wormholes, quantum fluctuations, gravity wells, gamma ray bursts, event horizons, dust clouds, and accretion disks.

## Quick Start

```powershell
# Generate all anomaly system assets
.\GenerateAnomalyAssets.ps1

# Use C++ backend for better quality
.\GenerateAnomalyAssets.ps1 -UseCppBackend

# Or generate everything at once
.\GenerateAllModSprites.ps1 -OllamaModel "codellama:7b-instruct"
```

## What Gets Generated

### Black Hole Effects (5 effects)

1. **blackhole_core** - Black hole core sprite
2. **blackhole_event_horizon** - Event horizon particle effect
3. **blackhole_pull_effect** - Gravitational pull particle effect
4. **blackhole_consume** - Consume particle effect
5. **blackhole_lensing** - Gravitational lensing effect

### Wormhole Gate Effects (4 effects)

1. **wormhole_gate_sprite** - Wormhole gate sprite
2. **wormhole_portal_effect** - Portal particle effect
3. **wormhole_warp_effect** - Warp particle effect
4. **wormhole_connection** - Connection visual effect

### Quantum Fluctuation Effects (4 effects)

1. **quantum_fluctuation_particle** - Quantum fluctuation particle
2. **quantum_teleport** - Quantum teleport effect
3. **quantum_swap** - Quantum swap effect
4. **quantum_invert** - Quantum invert effect

### Gravity Well Effects (3 effects)

1. **gravity_well_visual** - Gravity well visual sprite
2. **gravity_well_distortion** - Gravity distortion particle effect
3. **gravity_well_pull** - Gravity pull particle effect

### Gamma Ray Burst Effects (4 effects)

1. **gamma_ray_burst_projectile** - Gamma ray projectile sprite
2. **gamma_ray_burst_effect** - Gamma ray burst particle effect
3. **gamma_ray_trail** - Gamma ray trail particle effect
4. **gamma_ray_impact** - Gamma ray impact particle effect

### Event Horizon Effects (3 effects)

1. **event_horizon_distortion** - Event horizon distortion particle effect
2. **event_horizon_screen_effect** - Screen distortion effect
3. **event_horizon_entity_distortion** - Entity distortion effect

### Dust Cloud Effects (3 effects)

1. **dust_cloud_particle** - Dust cloud particle effect
2. **dust_cloud_texture** - Dust cloud texture
3. **dust_cloud_status** - Dust cloud status effect

### Accretion Disk Effects (3 effects)

1. **accretion_disk_particle** - Accretion disk particle effect
2. **accretion_disk_visual** - Accretion disk visual sprite
3. **accretion_disk_glow** - Accretion disk glow particle effect

## Total: ~29 Assets

## Output Structure

```
assets/
├── anomalies/
│   ├── blackhole/
│   │   ├── blackhole_core.png
│   │   ├── blackhole_event_horizon.particle
│   │   ├── blackhole_pull_effect.particle
│   │   ├── blackhole_consume.particle
│   │   └── blackhole_lensing.particle
│   ├── wormhole/
│   │   ├── wormhole_gate_sprite.png
│   │   ├── wormhole_portal_effect.particle
│   │   ├── wormhole_warp_effect.particle
│   │   └── wormhole_connection.particle
│   ├── quantum/
│   │   ├── quantum_fluctuation_particle.particle
│   │   ├── quantum_teleport.particle
│   │   ├── quantum_swap.particle
│   │   └── quantum_invert.particle
│   ├── gravity_well/
│   │   ├── gravity_well_visual.png
│   │   ├── gravity_well_distortion.particle
│   │   └── gravity_well_pull.particle
│   ├── gamma_ray/
│   │   ├── gamma_ray_burst_projectile.png
│   │   ├── gamma_ray_burst_effect.particle
│   │   ├── gamma_ray_trail.particle
│   │   └── gamma_ray_impact.particle
│   ├── event_horizon/
│   │   ├── event_horizon_distortion.particle
│   │   ├── event_horizon_screen_effect.particle
│   │   └── event_horizon_entity_distortion.particle
│   ├── dust_cloud/
│   │   ├── dust_cloud_particle.particle
│   │   ├── dust_cloud_texture.png
│   │   └── dust_cloud_status.particle
│   └── accretion_disk/
│       ├── accretion_disk_particle.particle
│       ├── accretion_disk_visual.png
│       └── accretion_disk_glow.particle
```

## Integration

### Black Hole Manager

```cpp
// Create black hole
BlackHoleManager::createHole(position, radius, strength);
// Uses: /anomalies/blackhole/blackhole_core.png for visual
// Uses: /anomalies/blackhole/blackhole_event_horizon.particle for horizon
// Uses: /anomalies/blackhole/blackhole_pull_effect.particle for pull
// Uses: /anomalies/blackhole/blackhole_consume.particle when consuming
// Uses: /anomalies/blackhole/blackhole_lensing.particle for lensing
```

### Wormhole Gate Manager

```cpp
// Register gate
WormholeGateManager::registerGate(id, position);
// Uses: /anomalies/wormhole/wormhole_gate_sprite.png for gate visual
// Uses: /anomalies/wormhole/wormhole_portal_effect.particle for active portal

// Warp entity
WormholeGateManager::tryWarp(position);
// Uses: /anomalies/wormhole/wormhole_warp_effect.particle for warp
// Uses: /anomalies/wormhole/wormhole_connection.particle for connection
```

### Quantum Fluctuation Manager

```cpp
// Configure fluctuation
QuantumFluctuationManager::configure(interval);
// Uses: /anomalies/quantum/quantum_fluctuation_particle.particle

// Update (triggers effects)
QuantumFluctuationManager::update(dt);
// Uses: /anomalies/quantum/quantum_teleport.particle for teleport
// Uses: /anomalies/quantum/quantum_swap.particle for swap
// Uses: /anomalies/quantum/quantum_invert.particle for invert
```

### Gravity Well Manager

```cpp
// Add gravity well
GravityWellManager::addWell(position, radius, scale);
// Uses: /anomalies/gravity_well/gravity_well_visual.png for visual
// Uses: /anomalies/gravity_well/gravity_well_distortion.particle for distortion
// Uses: /anomalies/gravity_well/gravity_well_pull.particle for pull
```

### Gamma Ray Burst Manager

```cpp
// Schedule burst
GammaRayBurstManager::scheduleBurst(position, interval, rayCount, damage);
// Uses: /anomalies/gamma_ray/gamma_ray_burst_effect.particle for burst
// Uses: /anomalies/gamma_ray/gamma_ray_burst_projectile.png for projectiles
// Uses: /anomalies/gamma_ray/gamma_ray_trail.particle for trails
// Uses: /anomalies/gamma_ray/gamma_ray_impact.particle for impacts
```

### Event Horizon Renderer

```cpp
// Add event horizon
EventHorizonRenderer::addHorizon(position, radius, strength);
// Uses: /anomalies/event_horizon/event_horizon_distortion.particle for distortion
// Uses: /anomalies/event_horizon/event_horizon_screen_effect.particle for screen
// Uses: /anomalies/event_horizon/event_horizon_entity_distortion.particle for entities
```

### Dust Cloud Manager

```cpp
// Spawn dust cloud
DustCloudManager::spawnCloud(position, radius, duration);
// Uses: /anomalies/dust_cloud/dust_cloud_particle.particle for particles
// Uses: /anomalies/dust_cloud/dust_cloud_texture.png for texture
// Uses: /anomalies/dust_cloud/dust_cloud_status.particle for status effect
```

### Accretion Disk Manager

```cpp
// Create accretion disk
AccretionDiskManager::createDisk(position, innerRadius, outerRadius, speed);
// Uses: /anomalies/accretion_disk/accretion_disk_visual.png for visual
// Uses: /anomalies/accretion_disk/accretion_disk_particle.particle for particles
// Uses: /anomalies/accretion_disk/accretion_disk_glow.particle for glow
```

## Anomaly Types

### Black Holes
- **Core**: Dark void center
- **Event Horizon**: Point of no return
- **Gravitational Pull**: Matter being pulled in
- **Consume**: Entity being consumed
- **Lensing**: Light distortion around black hole

### Wormholes
- **Gate**: Portal entrance/exit
- **Portal**: Active portal effect
- **Warp**: Entity warping through
- **Connection**: Visual connection between gates

### Quantum Fluctuations
- **Fluctuation**: Quantum instability
- **Teleport**: Entity teleporting
- **Swap**: Entities swapping positions
- **Invert**: Control inversion

### Gravity Wells
- **Visual**: Gravity well appearance
- **Distortion**: Space-time distortion
- **Pull**: Gravitational pull effect

### Gamma Ray Bursts
- **Projectile**: Gamma ray beam
- **Burst**: Burst explosion
- **Trail**: Beam trail
- **Impact**: Ray impact

### Event Horizons
- **Distortion**: Space-time distortion
- **Screen Effect**: Screen distortion
- **Entity Distortion**: Entity visual distortion

### Dust Clouds
- **Particle**: Floating dust particles
- **Texture**: Cloud texture
- **Status**: Status effect visual

### Accretion Disks
- **Particle**: Rotating matter particles
- **Visual**: Rotating disk sprite
- **Glow**: Disk glow effect

## Workflow

### Step 1: Generate Assets

```powershell
.\GenerateAnomalyAssets.ps1 -OllamaModel "codellama:7b-instruct"
```

### Step 2: Configure Anomalies

Set up anomaly managers with asset paths.

### Step 3: Test in Game

Load the mod and test anomaly systems in-game.

## Advanced Options

### Custom Anomaly Effects

Edit `GenerateAnomalyAssets.ps1` to add custom anomaly effects.

### Custom Black Hole Variants

Add custom black hole effects for different sizes/types.

### Custom Wormhole Types

Add custom wormhole gate sprites for different gate types.

## Tips

1. **Black hole effects**: Use dark colors with bright edges for event horizon
2. **Wormhole effects**: Use swirling, portal-like effects
3. **Quantum effects**: Use particle effects with quantum/glitch aesthetics
4. **Gravity effects**: Use distortion and pull effects
5. **Gamma ray effects**: Use bright, high-energy colors
6. **Event horizon**: Use strong distortion effects
7. **Dust clouds**: Use semi-transparent particles
8. **Accretion disks**: Use rotating, glowing effects

## Troubleshooting

### Anomalies Not Displaying

- Check anomaly effect paths
- Verify effects are in `assets/anomalies/`
- Ensure anomaly managers are initialized

### Effects Not Appearing

- Check particle effect paths
- Verify particle system is initialized
- Check effect spawn conditions

---

*Part of the Starbound Ollama Asset Generator suite*
