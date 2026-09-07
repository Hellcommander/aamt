# Space Whale Nova Drift Visual Template

A comprehensive guide for adapting Nova Drift's space whale visual style to this mod's space whale ship features.

## Overview

This template uses **Nova Drift's high-energy, glowing, smooth additive effects** as a base and adapts them for this mod's unique systems:
- Spline-driven spine with traveling wave undulation
- Bio-Core energy system
- Orbit Field (gravity-like aura)
- Song Pulse Shockwave
- Shared Shield Pool
- Drone Bay/Maw
- Swallow System
- Regenerative Tissue
- Mutation System

## Visual Language Principles

### Core Aesthetic (Nova Drift Base)
- **High-Energy Glows**: Soft, additive, color-driven, pulsing or expanding
- **Smooth Transitions**: No harsh cutoffs, everything blends smoothly
- **Procedural Distortion**: Heat-haze wobble, radial displacement, subtle chromatic aberration
- **Particle-Driven Motion**: Radial bursts, spirals, chaotic turbulence
- **Layered Composition**: Core glow + shockwave rings + bloom + particles

### Adaptation for Space Whale
- **Organic Flow**: Energy flows along the spline spine like blood through veins
- **Bioluminescent Skin**: Subsurface scattering with animated vein patterns
- **Breathing Rhythm**: Slow, organic pulsing that syncs with Bio-Core
- **Gravity Aura**: Orbit Field creates visible distortion and particle trails
- **Shockwave Expansion**: Song Pulse creates expanding rings with turbulence

## Feature-Specific Visual Templates

### 1. Orbit Field (Passive Gravity Aura)

**Nova Drift Base**: Distortion field with heat-haze effect

**Space Whale Adaptation**:
```json
{
  "id": "space_whale_orbit_field",
  "type": "aura",
  "style": "novaDrift",
  "visual": {
    "coreColor": "#66ccff",
    "rimColor": "#ffffff",
    "shockwaveColor": "#88ddff",
    "bloomColor": "#aaffff",
    "distortionStrength": 0.08,
    "distortionType": "gravityWell",
    "noiseType": "perlin",
    "noiseSpeed": 0.5,
    "noiseScale": 2.0,
    "spriteSize": 256,
    "frames": 24,
    "layers": ["distortion", "particles", "glow"],
    "coreGlow": {
      "enabled": true,
      "intensity": 2.0,
      "pulse": true,
      "expand": false
    },
    "shockwave": {
      "enabled": false
    },
    "bloom": {
      "enabled": true,
      "intensity": 1.2,
      "radius": 1.5
    },
    "chromaticAberration": true
  },
  "particles": {
    "burstCount": 0,
    "motionPattern": "orbital",
    "orbitalParticles": {
      "enabled": true,
      "count": 32,
      "speedMin": 0.2,
      "speedMax": 0.5,
      "lifeMin": 2.0,
      "lifeMax": 4.0,
      "orbitRadius": 1.0,
      "spiralInward": true
    }
  },
  "timing": {
    "coreExpandTime": 0.0,
    "fadeOutTime": 0.0,
    "sustain": true
  }
}
```

**Visual Description**:
- Subtle radial distortion (like looking through water)
- Slow-orbiting particles that spiral inward
- Soft blue-white glow that pulses with Bio-Core
- Chromatic aberration at edges (blue shift)
- Particles accelerate as they approach center

**Integration Points**:
- Scales with Bio-Core output (brighter = more energy)
- Pull strength affects particle speed
- Radius matches orbit field range (500 units)

### 2. Song Pulse Shockwave

**Nova Drift Base**: Expanding shockwave ring with particle burst

**Space Whale Adaptation**:
```json
{
  "id": "space_whale_song_pulse",
  "type": "shockwave",
  "style": "novaDrift",
  "visual": {
    "coreColor": "#ff66ff",
    "rimColor": "#ffffff",
    "shockwaveColor": "#ff99ff",
    "bloomColor": "#ffccff",
    "distortionStrength": 0.12,
    "distortionType": "turbulent",
    "noiseType": "voronoi",
    "noiseSpeed": 2.0,
    "noiseScale": 3.0,
    "spriteSize": 512,
    "frames": 16,
    "layers": ["core", "shockwave", "bloom", "distortion", "particles"],
    "coreGlow": {
      "enabled": true,
      "intensity": 4.0,
      "pulse": false,
      "expand": true
    },
    "shockwave": {
      "enabled": true,
      "ringCount": 2,
      "thickness": 0.04,
      "expandSpeed": 3.0
    },
    "bloom": {
      "enabled": true,
      "intensity": 2.5,
      "radius": 1.8
    },
    "chromaticAberration": true
  },
  "particles": {
    "burstCount": 48,
    "burstSpeedMin": 1.5,
    "burstSpeedMax": 4.0,
    "lifetimeMin": 0.4,
    "lifetimeMax": 1.2,
    "sizeMin": 0.04,
    "sizeMax": 0.12,
    "blend": "additive",
    "motionPattern": "radialBurst",
    "coreParticles": {
      "enabled": true,
      "count": 16,
      "speedMin": 0.3,
      "speedMax": 0.8,
      "lifeMin": 0.6,
      "lifeMax": 1.5
    },
    "shockwaveParticles": {
      "enabled": true,
      "count": 24,
      "ringRadius": 0.7,
      "expandSpeed": 2.5
    }
  },
  "timing": {
    "coreExpandTime": 0.1,
    "shockwaveExpandTime": 0.2,
    "fadeOutTime": 0.5,
    "easeIn": "easeOut",
    "easeOut": "easeIn"
  }
}
```

**Visual Description**:
- Double-ring shockwave expanding outward
- High-energy purple-pink core
- Turbulent distortion (like sound waves)
- Radial particle burst
- Chromatic aberration (red shift at edges)

**Integration Points**:
- Triggers on Bio-Core consumption (10 energy)
- Radius matches shockwave range (300 units)
- Push force affects particle velocity
- Collision damage scales with visual intensity

### 3. Bio-Core Energy System

**Nova Drift Base**: Pulsing core glow with energy flow

**Space Whale Adaptation**:
```json
{
  "id": "space_whale_bio_core",
  "type": "energy",
  "style": "novaDrift",
  "visual": {
    "coreColor": "#00ff88",
    "rimColor": "#ffffff",
    "shockwaveColor": "#44ffaa",
    "bloomColor": "#88ffcc",
    "distortionStrength": 0.02,
    "distortionType": "radial",
    "noiseType": "simplex",
    "noiseSpeed": 1.0,
    "noiseScale": 4.0,
    "spriteSize": 128,
    "frames": 12,
    "layers": ["core", "bloom", "particles"],
    "coreGlow": {
      "enabled": true,
      "intensity": 3.5,
      "pulse": true,
      "expand": false
    },
    "shockwave": {
      "enabled": false
    },
    "bloom": {
      "enabled": true,
      "intensity": 2.0,
      "radius": 1.3
    }
  },
  "particles": {
    "burstCount": 0,
    "motionPattern": "core",
    "coreParticles": {
      "enabled": true,
      "count": 12,
      "speedMin": 0.1,
      "speedMax": 0.3,
      "lifeMin": 1.0,
      "lifeMax": 2.0,
      "spiralOutward": true
    }
  },
  "timing": {
    "coreExpandTime": 0.0,
    "fadeOutTime": 0.0,
    "pulseFrequency": 1.0,
    "sustain": true
  }
}
```

**Visual Description**:
- Green-cyan core at ship center (Bio-Core location)
- Pulsing intensity scales with energy level (0-100)
- Slow spiral particles drift outward
- Soft bloom creates organic feel
- Distortion creates "energy field" effect

**Integration Points**:
- Intensity = `(bioCore / 100) * 3.5`
- Pulse frequency = `0.5 + (regenRate / 30)`
- Particles spawn when energy consumed
- Color shifts red when low (< 20%)

### 4. Shared Shield Pool Link

**Nova Drift Base**: Energy tether/beam effect

**Space Whale Adaptation**:
```json
{
  "id": "space_whale_shield_link",
  "type": "tether",
  "style": "novaDrift",
  "visual": {
    "coreColor": "#88ffff",
    "rimColor": "#ffffff",
    "shockwaveColor": "#aaffff",
    "bloomColor": "#ccffff",
    "distortionStrength": 0.03,
    "distortionType": "linear",
    "noiseType": "perlin",
    "noiseSpeed": 1.5,
    "noiseScale": 6.0,
    "spriteSize": 64,
    "frames": 8,
    "layers": ["core", "bloom", "particles"],
    "coreGlow": {
      "enabled": true,
      "intensity": 2.5,
      "pulse": true,
      "expand": false
    },
    "shockwave": {
      "enabled": false
    },
    "bloom": {
      "enabled": true,
      "intensity": 1.5,
      "radius": 1.2
    }
  },
  "particles": {
    "burstCount": 0,
    "motionPattern": "linear",
    "linearParticles": {
      "enabled": true,
      "count": 16,
      "speedMin": 0.5,
      "speedMax": 1.2,
      "lifeMin": 0.5,
      "lifeMax": 1.5,
      "direction": "towardMinion"
    }
  },
  "timing": {
    "coreExpandTime": 0.0,
    "fadeOutTime": 0.0,
    "sustain": true
  }
}
```

**Visual Description**:
- Cyan beam connecting whale to minions
- Particles flow along beam (toward minions)
- Pulsing intensity shows shield transfer
- Soft glow creates "energy conduit" feel
- Linear distortion (like heat shimmer)

**Integration Points**:
- Beam visible when `spaceWhaleMinionLinkActive` = true
- Intensity scales with shield transfer rate
- Particles spawn at whale, flow to minions
- Color shifts red when pool low (< 20%)

### 5. Drone Bay/Maw Spawn Effect

**Nova Drift Base**: Radial burst with expanding ring

**Space Whale Adaptation**:
```json
{
  "id": "space_whale_drone_spawn",
  "type": "spawn",
  "style": "novaDrift",
  "visual": {
    "coreColor": "#ffaa00",
    "rimColor": "#ffffff",
    "shockwaveColor": "#ffcc44",
    "bloomColor": "#ffdd88",
    "distortionStrength": 0.06,
    "distortionType": "radial",
    "noiseType": "voronoi",
    "noiseSpeed": 1.8,
    "noiseScale": 3.5,
    "spriteSize": 96,
    "frames": 10,
    "layers": ["core", "shockwave", "bloom", "particles"],
    "coreGlow": {
      "enabled": true,
      "intensity": 3.0,
      "pulse": false,
      "expand": true
    },
    "shockwave": {
      "enabled": true,
      "ringCount": 1,
      "thickness": 0.03,
      "expandSpeed": 2.2
    },
    "bloom": {
      "enabled": true,
      "intensity": 2.0,
      "radius": 1.4
    }
  },
  "particles": {
    "burstCount": 24,
    "burstSpeedMin": 0.8,
    "burstSpeedMax": 2.0,
    "lifetimeMin": 0.3,
    "lifetimeMax": 0.8,
    "sizeMin": 0.03,
    "sizeMax": 0.08,
    "blend": "additive",
    "motionPattern": "radialBurst",
    "coreParticles": {
      "enabled": false
    }
  },
  "timing": {
    "coreExpandTime": 0.12,
    "shockwaveExpandTime": 0.18,
    "fadeOutTime": 0.3,
    "easeIn": "easeOut",
    "easeOut": "easeIn"
  }
}
```

**Visual Description**:
- Orange-yellow burst from belly bay
- Expanding ring shows spawn location
- Radial particles burst outward
- Quick, energetic feel
- Distortion creates "portal" effect

**Integration Points**:
- Triggers when drone spawns (20 Bio-Core cost)
- Positioned at belly bay module
- Scale matches drone size
- Color varies by drone type

### 6. Swallow System (Consumption)

**Nova Drift Base**: Implosion effect with inward particles

**Space Whale Adaptation**:
```json
{
  "id": "space_whale_swallow",
  "type": "consumption",
  "style": "novaDrift",
  "visual": {
    "coreColor": "#ff0066",
    "rimColor": "#ffffff",
    "shockwaveColor": "#ff4488",
    "bloomColor": "#ff88aa",
    "distortionStrength": 0.1,
    "distortionType": "implosion",
    "noiseType": "voronoi",
    "noiseSpeed": 2.5,
    "noiseScale": 2.5,
    "spriteSize": 192,
    "frames": 14,
    "layers": ["core", "shockwave", "bloom", "distortion", "particles"],
    "coreGlow": {
      "enabled": true,
      "intensity": 4.5,
      "pulse": false,
      "expand": false
    },
    "shockwave": {
      "enabled": true,
      "ringCount": 2,
      "thickness": 0.05,
      "expandSpeed": -2.0,
      "inward": true
    },
    "bloom": {
      "enabled": true,
      "intensity": 3.0,
      "radius": 1.6
    },
    "chromaticAberration": true
  },
  "particles": {
    "burstCount": 32,
    "burstSpeedMin": -1.5,
    "burstSpeedMax": -3.0,
    "lifetimeMin": 0.4,
    "lifetimeMax": 1.0,
    "sizeMin": 0.04,
    "sizeMax": 0.1,
    "blend": "additive",
    "motionPattern": "radialBurst",
    "inward": true,
    "coreParticles": {
      "enabled": true,
      "count": 12,
      "speedMin": -0.5,
      "speedMax": -1.2,
      "lifeMin": 0.6,
      "lifeMax": 1.2
    }
  },
  "timing": {
    "coreExpandTime": 0.15,
    "shockwaveExpandTime": 0.25,
    "fadeOutTime": 0.4,
    "easeIn": "easeIn",
    "easeOut": "easeOut"
  }
}
```

**Visual Description**:
- Red-pink implosion effect
- Inward-collapsing rings
- Particles pulled toward maw
- Strong distortion (like black hole)
- Chromatic aberration (blue shift at center)

**Integration Points**:
- Triggers during windup (0.5s before swallow)
- Positioned at maw (head module)
- Scale matches target size
- Intensity scales with target mass
- Color shifts based on digestion progress

### 7. Regenerative Tissue (Healing Glow)

**Nova Drift Base**: Soft pulsing glow with gentle particles

**Space Whale Adaptation**:
```json
{
  "id": "space_whale_regeneration",
  "type": "healing",
  "style": "novaDrift",
  "visual": {
    "coreColor": "#00ff44",
    "rimColor": "#ffffff",
    "shockwaveColor": "#44ff88",
    "bloomColor": "#88ffaa",
    "distortionStrength": 0.01,
    "distortionType": "radial",
    "noiseType": "simplex",
    "noiseSpeed": 0.3,
    "noiseScale": 5.0,
    "spriteSize": 64,
    "frames": 16,
    "layers": ["core", "bloom", "particles"],
    "coreGlow": {
      "enabled": true,
      "intensity": 1.5,
      "pulse": true,
      "expand": false
    },
    "shockwave": {
      "enabled": false
    },
    "bloom": {
      "enabled": true,
      "intensity": 1.2,
      "radius": 1.1
    }
  },
  "particles": {
    "burstCount": 0,
    "motionPattern": "gentle",
    "gentleParticles": {
      "enabled": true,
      "count": 8,
      "speedMin": 0.05,
      "speedMax": 0.15,
      "lifeMin": 2.0,
      "lifeMax": 4.0,
      "driftUpward": true
    }
  },
  "timing": {
    "coreExpandTime": 0.0,
    "fadeOutTime": 0.0,
    "pulseFrequency": 0.5,
    "sustain": true
  }
}
```

**Visual Description**:
- Soft green glow on damaged segments
- Gentle upward-drifting particles
- Slow pulsing (like breathing)
- Subtle bloom creates organic feel
- Minimal distortion (just warmth)

**Integration Points**:
- Visible on segments with < 100% armor
- Intensity scales with regen rate
- Particles spawn at damaged plates
- Color shifts based on mutation bonuses
- Fades when segment fully healed

### 8. Traveling Wave Undulation

**Nova Drift Base**: Motion blur and trail effects

**Space Whale Adaptation**:
```json
{
  "id": "space_whale_wave_trail",
  "type": "trail",
  "style": "novaDrift",
  "visual": {
    "coreColor": "#66ccff",
    "rimColor": "#ffffff",
    "shockwaveColor": "#88ddff",
    "bloomColor": "#aaffff",
    "distortionStrength": 0.02,
    "distortionType": "linear",
    "noiseType": "perlin",
    "noiseSpeed": 1.0,
    "noiseScale": 4.0,
    "spriteSize": 32,
    "frames": 8,
    "layers": ["core", "bloom", "particles"],
    "coreGlow": {
      "enabled": true,
      "intensity": 1.8,
      "pulse": false,
      "expand": false
    },
    "shockwave": {
      "enabled": false
    },
    "bloom": {
      "enabled": true,
      "intensity": 1.0,
      "radius": 1.1
    }
  },
  "particles": {
    "burstCount": 0,
    "motionPattern": "trail",
    "trailParticles": {
      "enabled": true,
      "count": 16,
      "speedMin": 0.1,
      "speedMax": 0.3,
      "lifeMin": 1.0,
      "lifeMax": 2.0,
      "followSpine": true
    }
  },
  "timing": {
    "coreExpandTime": 0.0,
    "fadeOutTime": 0.0,
    "sustain": true
  }
}
```

**Visual Description**:
- Soft blue trail along spine segments
- Particles follow wave motion
- Gentle glow creates "energy flow" feel
- Minimal distortion (just motion blur)
- Fades toward head (amplitude decay)

**Integration Points**:
- Trail follows spline spine
- Particle density matches wave amplitude
- Color shifts with mutation (SpineFlexibility)
- Intensity scales with movement speed
- Fades when stationary

### 9. Spline Spine Bending Visual

**Nova Drift Base**: Motion trails and energy flow

**Space Whale Adaptation**:
```json
{
  "id": "space_whale_spine_glow",
  "type": "spine",
  "style": "novaDrift",
  "visual": {
    "coreColor": "#88ffff",
    "rimColor": "#ffffff",
    "shockwaveColor": "#aaffff",
    "bloomColor": "#ccffff",
    "distortionStrength": 0.015,
    "distortionType": "linear",
    "noiseType": "simplex",
    "noiseSpeed": 0.8,
    "noiseScale": 5.0,
    "spriteSize": 16,
    "frames": 4,
    "layers": ["core", "bloom"],
    "coreGlow": {
      "enabled": true,
      "intensity": 2.0,
      "pulse": false,
      "expand": false
    },
    "shockwave": {
      "enabled": false
    },
    "bloom": {
      "enabled": true,
      "intensity": 1.5,
      "radius": 1.2
    }
  },
  "particles": {
    "burstCount": 0,
    "motionPattern": "none"
  },
  "timing": {
    "coreExpandTime": 0.0,
    "fadeOutTime": 0.0,
    "sustain": true
  }
}
```

**Visual Description**:
- Cyan glow along spline curve
- Soft bloom creates "energy spine" feel
- Subtle distortion (like heat shimmer)
- Intensity scales with bend angle
- Color shifts with steering bias

**Integration Points**:
- Glow follows spline anchors
- Intensity = `abs(bendAngle) / 45.0 * 2.0`
- Color shifts: blue (straight) → purple (bent)
- Fades at LOD distances
- Updates every 5 ticks (spine update rate)

### 10. Mutation Visual Effects

**Nova Drift Base**: Color shifts and intensity changes

**Space Whale Adaptation**:

#### Bio-Core Amplifier
- Core glow intensity: `+25%`
- Pulse frequency: `+15%`
- Color shift: More cyan (from green)

#### Gravity Well (Orbit Field)
- Distortion strength: `+50%`
- Particle count: `+50%`
- Color shift: Deeper blue (from cyan)

#### Resonance Cascade (Song Pulse)
- Shockwave ring count: `+1` (3 total)
- Particle burst: `+50%`
- Color shift: Brighter purple (from pink)

#### Void Rift (Corrupt)
- Distortion strength: `+100%`
- Color shift: Dark purple-black
- Chromatic aberration: `+200%`
- Particle motion: Chaotic (from orbital)

## Color Palette

### Base Colors (Nova Drift Inspired)
- **Core Energy**: `#00ff88` (green-cyan)
- **Orbit Field**: `#66ccff` (cyan-blue)
- **Song Pulse**: `#ff66ff` (purple-pink)
- **Shield Link**: `#88ffff` (cyan)
- **Drone Spawn**: `#ffaa00` (orange-yellow)
- **Swallow**: `#ff0066` (red-pink)
- **Regeneration**: `#00ff44` (green)
- **Spine Glow**: `#88ffff` (cyan)

### Mutation Modifiers
- **Minor**: `+10%` saturation, `+5%` brightness
- **Major**: `+20%` saturation, `+10%` brightness
- **Corrupt**: `+30%` saturation, `-10%` brightness, color shift toward purple/black

## Integration Guide

### Step 1: Create FX Registry
Create `space_whale_fx_registry.json` with all 10 effect templates above.

### Step 2: Generate Assets
```powershell
.\NovaDriftFXGenerator.ps1 -RegistryPath "space_whale_fx_registry.json" -OutputDir "Output/SpaceWhaleFX"
```

### Step 3: Integrate with Space Whale Ship
Add FX triggers to `SpaceWhaleShip.xml`:
- Orbit Field: Continuous aura effect
- Song Pulse: Trigger on ability use
- Bio-Core: Continuous pulsing glow
- Shield Link: Beam effect when active
- Drone Spawn: Burst on spawn
- Swallow: Implosion on consumption
- Regeneration: Glow on damaged segments
- Wave Trail: Continuous trail effect
- Spine Glow: Continuous along spline

### Step 4: Mutation Integration
Modify FX parameters based on active mutations:
- Read mutation list from ship data
- Apply color/intensity modifiers
- Update particle counts and speeds
- Adjust distortion strengths

## Performance Considerations

### LOD System
- **High** (< 500 units): Full FX, all particles
- **Medium** (500-1000): Reduced particles, simpler distortion
- **Low** (> 1000): Minimal FX, no particles

### Optimization
- Pool FX objects (don't create/destroy every frame)
- Batch particle updates
- Use sprite strips instead of real-time particles when possible
- Limit active FX count (max 3-4 simultaneous)

## Testing Checklist

- [ ] Orbit Field creates visible distortion and particles
- [ ] Song Pulse expands correctly with double rings
- [ ] Bio-Core pulses with energy level
- [ ] Shield Link beam connects to minions
- [ ] Drone Spawn bursts from belly bay
- [ ] Swallow creates implosion effect
- [ ] Regeneration glows on damaged segments
- [ ] Wave Trail follows spline spine
- [ ] Spine Glow intensifies with bend angle
- [ ] Mutations modify FX correctly
- [ ] LOD reduces FX complexity at distance
- [ ] Performance acceptable with multiple whales

## Next Steps

1. Generate all FX assets using Blender renderer
2. Integrate FX triggers into SpaceWhaleShip.xml
3. Add mutation-based FX modifiers
4. Implement LOD system for FX
5. Test and tune visual intensity
6. Add audio integration (whale songs, energy sounds)

## References

- **Nova Drift FX System**: `NOVA_DRIFT_FX_README.md`
- **Space Whale System**: `SPACE_WHALE_SYSTEM.md`
- **Blender Renderer**: `blender_nova_drift_fx_renderer.py`
- **FX Exporter**: `transcendence_fx_exporter.py`

