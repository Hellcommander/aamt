# Biometal Manta Ray — Parallel Support / Area-Control Line

A graceful, wide-winged living capital or cruiser that glides through starfields like a manta through water. Emphasizes **area control, sensor projection, and graceful mobility** rather than brute force. Broad wing surfaces and internal organs weave spells, shape fields, and shepherd allied formations. Reads as a single living organism optimized for sweeping maneuvers and support-centric spell-weaving.

Parallel to the Space Shark predator line and beside the Space Whale organic ladder.

## Leveling / lines

| Line | Progression |
|---|---|
| Organic capitals | Horn → Leviathan → Space Whale → Biometal Dragon |
| Biometal predators | Space Shark Scout → Hunter → Apex |
| **Biometal support** | **Scout Manta → Space Manta → Guardian / Rift Manta** |

`scSpaceManta` is the default mid pack. Scout / Guardian / Rift are head (or full-hull) variants sharing wing / tail / drone kits.

## Ship IDs

| ID | Role | Variant | Frame |
|---|---|---|---:|
| `scSpaceManta` | head / body | **Baseline** support cruiser | 224 |
| `scSpaceMantaScout` | head | Scout — glide efficiency, Song Beacon, smaller Aether | 192 |
| `scSpaceMantaGuardian` | head | Guardian — stronger Veil / glands, less mobility | 224 |
| `scSpaceMantaRift` | head | Rift — more Rift Buoys, higher instability | 224 |
| `scSpaceMantaWing` | wing panel | shared pectoral / membrane | 128 |
| `scSpaceMantaTail` | fluke | tapered tail fin + wake | 96 |
| `scSpaceMantaDrone` | drone | sensor buoy / mine / micro-rift | 64 |

Poses (heads): `idle`, `mawOpen`, `bodyCompress`, `bellyGlow`, `wingSpread`  
Poses (wing/tail/drone): `idle`, `bodyCompress` (+ `veilUp` later for Guardian)

## Exterior

Flattened diamond silhouette with broad pectoral wings and a tapered tail fin.

- **Skin:** layered biometal dermis with translucent ventral membranes showing pulsing vascular rails and organ glow.
- Leading edges: scale vents and sensor filaments.
- Trailing edges: faint arcane wake on burst thrust or spell-weave.
- Wing tips and dorsal ridges: modular ports for scale launchers, rift seeds, and sensor arrays.

## Internal anatomy

| Organ | Role |
|---|---|
| **Aether Heart** | Central, low-profile heart for steady Aether flow and field generation |
| **Flux Lungs** | Wide, shallow sacs that pressurize the ventral membrane for sweeping fields and long-duration abilities |
| **Song Sacs** | Resonant organs along the wings for long-range sensor pulses and area buffs |
| **Vascular Rails** | Braided conduits wing-to-tail; pulse when routing Aether to weapons or fins |
| **Glandular Nodes** | Distributed repair glands; secrete adaptive alloys for membrane patching and scale hardening |
| **Brood Pockets** | Small dorsal pouches for sensor drones, buoyant mines, or micro-rifts |

## Organ → TX / ArcaneConduit

| Organ | Mapping | Pose / VFX | Notes |
|---|---|---|---|
| **Aether Heart** | Steady pool + field generation | `bellyGlow`; slow pulse | Support economy, not shark burst |
| **Flux Lungs** | Glide Mode, Sweep Burst, field sustain | Ventral membrane inflate | Trade mobility vs Sweep Field |
| **Song Sacs** | Wing Chorus / sensor pulses | Wing glow ripple | Long-range reveal + ally sensor buff |
| **Vascular Rails** | Route Aether wing→tail | Visible ventral veins | Soft-gates field vs thrust |
| **Glandular Nodes** | Arcane Veil + membrane repair | Scale harden flash | Guardian bias |
| **Brood Pockets** | Sensor drones / mines / micro-rifts | Dorsal pouch spawn | Cap by variant |

## Propulsion

Primary locomotion is **muscular undulation of the wings** plus bioplasma jets along the trailing edge for bursts.

| Mode | Behavior |
|---|---|
| **Glide Mode** | Minimal Aether; long, energy-efficient travel and passive sensor projection |
| **Sweep Burst** | Lateral burst; consumes Aether; rapid flank reposition; leaves a temporary gravity wake |
| **Phase fins** | Short micro-teleports; high Aether and instability (Glide Flicker) |

## Weapons and spell weaving

Organ-driven, area control and support — not single-target alpha.

| System | Role |
|---|---|
| **Ventral Field Projector** | Compiles Growth / Gravity / Field into persistent areas that slow, heal, or buff |
| **Wing Scale Launchers** | Enchanted scales that orbit (Orbit modifier) or act as sensor buoys |
| **Rift Seed Dispensers** | Temporary portals for drone deployment or tactical repositioning |
| **Breath Conduit** | Maw cone of arcane mist / ion breath; deterrent, not primary offense |

## Aether

Single regenerating resource for thrust, weapons, and specials. Heart provides steady regen; Flux Lungs and ambient arcane density modify rates. Movement, field projection, and sustained areas share the pool — mobility vs prolonged support. Gentle grazing collisions and environmental interactions restore Aether with low instability.

Baseline snapshot: Max Aether **1000**, regen **10/s**, glide **4/s**, Sweep Burst **140**, Sweep Field sustain **18/s**, hull **10,500**.

## Signature abilities → combat kit

| Ability | Kit tag | Cost | TX sketch |
|---|---|---|---|
| Wing Chorus | `wingChorus` | low | Song Sacs pulse: reveal cloaked + ally sensor range |
| Arcane Veil | `arcaneVeil` | medium | Glands thicken ventral membrane into a DR dome |
| Sweep Field | `sweepField` | sustain drain | Moving field: slow enemies, heal allies |
| Rift Buoy | `riftBuoy` | high + instability | Anchored portal for drones / evac |
| Glide Flicker | `glideFlicker` | moderate | Phase hop preserving momentum; brief stealth |
| Sweep Burst | `sweepBurst` | 140 | Lateral reposition + gravity wake |
| Scale Launchers | `wingScales` | — | Orbit scales / sensor buoys |
| Breath Conduit | `breathMist` | — | Wide deterrent cone (secondary) |

## Physics & balance

Role: **fleet support and area controller**. Excels at shaping engagements, protecting convoys, enabling allied tactics. Strengths: long-duration fields, sensor projection, graceful repositioning, strong Aether economy. Weaknesses: lower single-target damage, vulnerability to focused long-range fire, Aether management. Design intent: movement, field placement, and ability timing — not raw DPS.

| Variant | mass | thrustRatio | maxSpeed | crashOut | brood | maxAether | fieldSustain |
|---|---:|---:|---:|---:|---:|---:|---:|
| Scout | 110 | 2.8 | 22 | 0.9 | 4 | 800 | 14/s |
| **Baseline** | **160** | **2.2** | **18** | **1.0** | **6** | **1000** | **18/s** |
| Guardian | 190 | 1.8 | 15 | 1.1 | 5 | 1100 | 20/s |
| Rift | 170 | 2.0 | 17 | 1.0 | 8 | 1000 | 16/s |
| Drone | 20 | 3.5 | 26 | 0.5 | — | — | — |

## Implementation blueprint (engine)

Core components: `MantaShip` actor, `AetherHeartComponent`, `FluxLungComponent`, `SongSackComponent`, `FieldProjector`, `RiftDispenser`, `BroodBay`.

Hooks: `OnTick(dt)` organ updates + Aether regen; `PerformAbility(id)` validation + instability; `OnDeployField()` field lifecycle + LOD; `OnCollision(info)` kinetic conversion.

Performance: pool field entities and drones; LOD wing animation; approximate membrane deformation with shaders.

## Art direction

- **Palette:** pearl `#e8e4f0`, indigo `#2a2858`, membrane violet `#6e5cff`, soft cyan `#7ad8ff`, glow rose `#ff9ad4`
- **Silhouette:** flattened diamond, broad pectorals, tapered tail — reads as manta, not shark torpedo or dragon serpent
- **Ventral:** translucent membrane showing vascular rails / organ glow (support fantasy signature)

## Audio (SA3)

| Event | TX | Starfield-only |
|---|---|---|
| idle | soft wing-glide hum | spatial_loop membrane bed |
| chorus | resonant song pulse | — |
| field | low gravity thrum | field sustain loop |
| fire / mist | soft breath cone | proximity wash |

## Pipeline

3D three-quarter concept → TRELLIS 1024 → Ucupaint → 120 facings → Starfield GLB/DDS + `nd_scSpaceManta_*.wav`.

## Concise art prompt

Biometal manta ray spaceship, flattened diamond hull, broad pectoral wings, translucent ventral membrane with pulsing violet vascular rails, pearl-indigo dermis, tapered tail wake, dark starfield, cinematic 3D sculpt.
