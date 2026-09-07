# Space Whale Implementation Guide

Complete implementation guide based on the comprehensive design specification.

## Overview

This guide provides step-by-step instructions for implementing the Space Whale ship system according to the design spec. The implementation supports three modes:

1. **Mod-Only**: Pure XML/TLisp implementation (API 57-59)
2. **Engine Backend**: Full C++ backend with native physics (recommended)
3. **Hybrid**: Mod-only with optional backend enhancements

## Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────┐
│                    Space Whale Ship                      │
├─────────────────────────────────────────────────────────┤
│  Core (ShipState)                                        │
│  ├─ Spine Anchors (control points)                      │
│  ├─ Resource Pools (fuel, BioCore)                      │
│  ├─ Digestion Queue                                     │
│  └─ Global State                                        │
├─────────────────────────────────────────────────────────┤
│  Segments (N ordered pieces)                            │
│  ├─ Transform (position, rotation)                      │
│  ├─ Local Collider                                      │
│  ├─ Armor Plates (per-segment)                          │
│  ├─ Device Hardpoints                                   │
│  └─ LOD Level                                           │
├─────────────────────────────────────────────────────────┤
│  Motion System                                          │
│  ├─ Spline Sampling (Catmull-Rom)                      │
│  ├─ Spring-Damped Follow                                │
│  ├─ Tail Wave (traveling sine)                          │
│  └─ Worker Compute (simulated)                         │
├─────────────────────────────────────────────────────────┤
│  Collider System                                        │
│  ├─ Compound Capsule Chain                              │
│  ├─ LOD Colliders                                       │
│  ├─ Atomic Swap                                         │
│  └─ Contact Mapping                                     │
├─────────────────────────────────────────────────────────┤
│  Gameplay Systems                                       │
│  ├─ Swallowing                                          │
│  ├─ Ramming                                             │
│  ├─ Dynamic Resizing                                    │
│  └─ Armor Regeneration                                  │
└─────────────────────────────────────────────────────────┘
```

## Data Model

### ShipState

```lisp
{
    id: shipId
    position: (objGetPos ship)
    velocity: (objGetVel ship)
    rotation: (objGetRotation ship)
    
    scale: 1.0
    mass: 5000
    fatigue: 0
    fuel: (shpGetFuelLeft ship)
    bioCore: 100
    
    segments: (list)  ; Array of Segment structures
    spineAnchors: (list)  ; Control points for spline
    digestQueue: (list)  ; Array of DigestEntry structures
    
    mawActive: False
    orbitFieldActive: False
    minionLinkActive: False
    
    lastUpdateTick: (unvGetTick)
    updateInterval: 5
}
```

### Segment

```lisp
{
    index: 0  ; 0 = head, N-1 = tail
    anchorPos: (sysVector x y)
    transform: rotationAngle
    localVel: (sysVector vx vy)
    
    plates: (list)  ; Array of Plate structures
    devices: (list)  ; Array of {deviceId, slot, enabled}
    
    colliderHandle: Nil  ; Backend collider reference
    lodLevel: 'high  ; 'high, 'medium, 'low
    
    segmentType: 'head  ; 'head, 'body, 'tail
}
```

### Plate

```lisp
{
    id: "plate_0_0"
    typeTag: 'light  ; 'light, 'medium, 'heavy, 'reinforced
    currentHP: 100
    maxHP: 100
    accum: 0.0  ; Fractional regen accumulator
    state: 'idle  ; 'idle, 'repairing, 'disabled, 'replacing
    repairPause: 0  ; Ticks until repair can resume
}
```

### DigestEntry

```lisp
{
    targetTemplate: templateId
    remainingMass: 100.0
    internalDamage: 0
    digestTimer: 0
    ejectable: True
    digestRate: 10.0  ; Mass per second
}
```

## Motion and Spine System

### Spline Sampling

The spine uses a **Catmull-Rom spline** sampled at `t = i / (N-1)` where:
- `i` = segment index (0 to N-1)
- `N` = total segment count

**Algorithm**:
1. Compute target anchor positions from spline
2. Apply tail wave (traveling sine offset)
3. Apply steering bias for turns
4. Update segment positions with spring-damped physics

### Spring-Damped Follow

Each segment follows its target position with:

```
errorPos = targetPos - currentPos
velocity += (errorPos * stiffness - velocity * damping) * dt
position += velocity * dt
```

**Tuning Values**:
- `stiffness = 0.8` (spring strength)
- `damping = 0.3` (velocity damping)
- `dt = 1/30` (tick time)

### Tail Wave

Traveling sinusoidal offset for undulation:

```
offset(t, i) = amplitude(i) * sin(frequency * time + phase(i) * t)
amplitude(i) = baseAmplitude * (i/N)²  ; Decays toward head
phase(i) = 2.0 * (i/N)  ; Larger phase at tail
```

### LOD Updates

Update frequency based on distance to player:

| Distance | LOD | Update Interval |
|----------|-----|-----------------|
| < 500 | High | Every 5 ticks |
| 500-1000 | Medium | Every 15 ticks |
| > 1000 | Low | Every 30 ticks |

## Collider System

### Compound Capsule Chain

Primary collider: capsules between adjacent anchors.

**Generation**:
1. For each anchor pair (i, i+1):
   - Create capsule from `anchor[i]` to `anchor[i+1]`
   - Radius scales with segment type (head/tail smaller)
2. Combine into compound collider
3. Cache for reuse

### Atomic Swap

Safe collider replacement during resize:

```
1. Generate new collider on worker thread
2. Validate with swept AABB on main thread
3. Set body to kinematic
4. Replace collider
5. Scale velocity for mass change
6. Re-enable dynamic physics
7. Apply stabilization damping
```

### Contact Mapping

Map collision point to nearest segment/plate:

```
1. Project contact point onto spine
2. Find nearest anchor
3. Map to segment index
4. Find nearest plate on segment
5. Apply damage to plate
6. Propagate to neighbors if plate destroyed
```

## Gameplay Systems

### Swallowing

**Eligibility Check**:
- `target.mass ≤ 0.25 * whale.mass`
- `target.health ≤ 0.35 * target.maxHealth`
- Not boss, station, player, or ally

**Ingested State**:
- Target becomes `DigestEntry` in queue
- Can attack from inside (internal damage)
- Escape threshold: `0.6 * target.maxHP + 0.2 * target.mass`

**Digestion**:
- Convert mass → fuel/BioCore over time
- Grant local plate regen bonus
- Eject on escape or forced purge

### Ramming

**Modes**:
- **Bash**: Short ram, low cost, interrupt
- **Charge**: Full ram, high damage, pierce
- **Tail-Slam**: Area knockback, defensive

**Damage Calculation**:
```
Ek = 0.5 * mass * velocity²
damage = clamp(k_scale * Ek - armor, min, max)
```

**Recoil**:
```
recoilImpulse = impulse * (targetMass / whaleMass) * recoilFactor
whale.velocity -= recoilImpulse
```

### Dynamic Resizing

**Preset Templates**:
- Small (0.6×): Compact, fast, fragile
- Medium (1.0×): Balanced
- Large (1.5×): Slow, durable
- Maximum (2.5×): Titan mode

**Cost Model**:
```
fuelCost = base + k * (scale³ - 1) + complexitySurcharge
bioCost = scaleDelta * 10
```

**Safe Application**:
1. Preview operation
2. Reserve resources
3. Swept overlap test
4. Nudge or reject if overlap
5. Atomic collider swap
6. Stabilization damping

### Armor Regeneration

**Hybrid Model**:
- Fractional accumulator: `accum += regenRate / 30` per tick
- Probabilistic burst: 10% chance per tick if `accum > 1.0`
- Baseline: 0.5 HP/s for light plate
- Multipliers: digest bonus, solar, device bonuses
- Pause on damage: 3 seconds repair pause

## Performance Optimizations

### Multithreading (Simulated)

**Worker Thread Responsibilities**:
- Spine sampling and anchor generation
- Collider generation seeds
- AI decisions
- Heavy queries
- Visual bone matrices

**Main Thread Responsibilities**:
- Authoritative physics
- Entity creation/destruction
- Collider swap
- Damage application

**Communication**:
- Double-buffered previews
- Frame stamps to ignore stale data
- Lock-free ring buffers (simulated in TLisp)

### Batching and Amortization

- Stagger segment updates (update 2-3 per frame)
- Cache colliders (reuse for same scale)
- Pool segment entities
- Reuse particle emitters

### Memory Layout

Structure of Arrays (SoA) for SIMD-friendly data:
- All segment positions in one array
- All segment rotations in one array
- All segment velocities in one array

## Implementation Modes

### Mod-Only (API 57-59)

**Approach**:
- Pooled `whale_segment` templates
- Update transforms via timers and `SetShipPos`/`SetShipRotation`
- Template swaps for resizing
- Plate regen via device data and timers

**Limitations**:
- No atomic collider swaps
- Simplified physics
- No true multithreading

**Files**:
- `SpaceWhaleDataModel.xml`
- `SpaceWhaleMotionSystem.xml`
- `SpaceWhaleColliderSystem_ModOnly.xml`

### Engine Backend (Recommended)

**Approach**:
- `SegmentedShipController` with `ControllerCommand` hooks
- `GenerateCapsuleChain` native function
- `ReplaceColliderAtomic` native function
- Worker thread pool for previews

**Benefits**:
- Full physics fidelity
- Atomic collider swaps
- True multithreading
- Procedural collider generation

**Files**:
- All mod files +
- `backend/ModBackendAPI.h`
- `backend/ModBackendAPI.cpp`
- `backend/EngineHooks.cpp`

### Hybrid

**Approach**:
- Template presets for most runtime changes
- Optional engine patch for procedural colliders
- Fallback to mod-only if backend unavailable

**Files**:
- All mod files +
- Backend files (optional)

## Generation Tool

Use the `SpaceWhaleImplementationGenerator.ps1` script:

```powershell
# Generate mod-only implementation
.\SpaceWhaleImplementationGenerator.ps1 -ImplementationMode modOnly

# Generate with backend support
.\SpaceWhaleImplementationGenerator.ps1 -ImplementationMode engineBackend

# Generate hybrid (default)
.\SpaceWhaleImplementationGenerator.ps1 -ImplementationMode hybrid
```

## Tuning Checklist

### Balance

- [ ] Base regen: 0.5 HP/s for light plate
- [ ] Digest bonus: +50% regen for 5 seconds
- [ ] Ram energy caps: prevent infinite rams
- [ ] Resize costs: make morphing tactical, not spammy

### Edge Cases

- [ ] Resizing in tight geometry (nudge or reject)
- [ ] Swallowed target escaping during ram
- [ ] Rapid morph sequences (cooldown/fatigue)
- [ ] Multiple resize sources stacking

### Performance

- [ ] Stress test: 10+ segmented whales
- [ ] Measure frame time (target: <16ms)
- [ ] Tune LOD thresholds
- [ ] Profile spine compute time
- [ ] Monitor worker queue latency

### UX

- [ ] Preview UI shows exact fuel/BioCore delta
- [ ] Time to full repair displayed
- [ ] Clear rejection reasons
- [ ] Visual feedback for all operations

## Next Steps

1. **Prototype**: Start with mod-only to validate gameplay
2. **Tune**: Balance systems and test edge cases
3. **Backend**: Add engine patch for full fidelity
4. **Polish**: Visual effects, audio, UI
5. **Documentation**: Player guide and modding docs

## Related Files

- `SpaceWhaleShip.xml` - Main ship implementation
- `ResizeAPI.xml` - Unified resize system
- `ColliderProfiles.xml` - Predefined collider shapes
- `backend/ModBackendAPI.h` - C++ backend API
- `SPACE_WHALE_SYSTEM.md` - System documentation

