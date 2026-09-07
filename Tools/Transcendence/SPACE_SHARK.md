# Space Shark — Parallel Biometal Predator Line

Predatory biometal capital/cruiser family beside the Space Whale line. Emphasizes **speed, burst mobility, and close-range predation**, with organ-driven Aether and ArcaneConduit spell-weaving hooks.

Whale = ethereal plated leviathan (sustained presence).  
Shark = hydrodynamic biometal hunter (hit-and-run).  
Dragon = apex biometal capital (above whale).  

## Leveling / lines

| Line | Progression |
|---|---|
| Organic capitals | Horn → Leviathan → **Space Whale** → Biometal Dragon |
| **Biometal predators (parallel)** | **Scout Shark → Hunter Shark → Apex Shark** |

Hunter is the default pack (`scSpaceShark`). Scout/Apex are head variants sharing segment / tail / drone kits.

## Ship IDs

| ID | Role | Variant | Frame |
|---|---|---|---:|
| `scSpaceShark` | head | **Hunter** (baseline) | 192 |
| `scSpaceSharkScout` | head | Scout — lighter, faster, smaller brood | 160 |
| `scSpaceSharkApex` | head | Apex — larger heart/jaws, limited stealth | 224 |
| `scSpaceSharkSegment` | body | shared | 96 |
| `scSpaceSharkTail` | fluke | crescent tail + spine launcher | 96 |
| `scSpaceSharkDrone` | drone | brood micro-drone / spore | 64 |

Poses (heads): `idle`, `mawOpen`, `bodyCompress`, `bellyGlow`, `finFlar`  
Poses (segment/tail/drone): `idle`, `bodyCompress` (+ `spineReady` for tail)

## Organ → TX / ArcaneConduit

| Organ | Mapping | Pose / VFX | Notes |
|---|---|---|---|
| **Aether Heart** | Resource pool + burst window DPS | `bellyGlow`; fast pulse | Optimized for burst, not whale sustain |
| **Flux Lungs** | Burst Swim + Phase Flicker + Camouflage Drift | `bodyCompress` / `finFlar` | Pressure = stealth vs hop fuel |
| **Jaw Glands** | Jaw Projector ammo / corrosion | `mawOpen` | Plasma / mist / lightning modes |
| **Vascular Rails** | Route Aether to fins / maw / dorsal | Flank vein pulse | Soft-gates simultaneous spend |
| **Synaptic Mantle** | Predator AI + Synaptic Weave compiler | Spine flicker | Maps base spells → ship projectiles (hex offset) |
| **Shock Sacs** | OnCollision → Aether from kinetic | Impact flash | Rewards ramming / grazing |
| **Brood Pouch** | Brood Spit drones / mines | Spawn ripple | Cap by variant (Scout 3 / Hunter 6 / Apex 8) |

## Signature abilities → combat kit

| Ability | Kit tag | TX sketch |
|---|---|---|
| Predator Burst | `predatorBurst` | Short speed+damage window; arcane wake DoT behind |
| Hunter’s Song | `huntersSong` | Reveal/mark pulse (EM channel, whale-song cousin) |
| Razor Bloom | `razorBloom` | Dorsal scales → Orbit ring (AC Orbit modifier) |
| Jaw Rend | `jawRend` | Charged maw; stacking corrosion + hull open |
| Brood Spit | `broodSpit` | Micro-drones / proximity mines from pouch |
| Camouflage Drift | `camouflageDrift` | Dim lateral lines; drains lung pressure |
| Phase Flicker | `phaseFlicker` | Lateral micro-teleport; instability spike |
| Tail Spine | `tailSpine` | Tether/pull (Host of Chains–style hook) |
| Ventral Rift Seed | `riftSeed` | Tiny portal for drones / escape (AC rift) |

## Physics & balance anchors

Weapon damage mult **0.85** (tactical, not brute). High burst Aether cost + cooldown.

| Variant | mass | thrustRatio | maxSpeed | crashOut | brood | weaponMult |
|---|---:|---:|---:|---:|---:|---:|
| Scout | 90 | 3.6 | 28 | 1.1 | 3 | 0.80 |
| **Hunter** | **140** | **3.0** | **24** | **1.4** | **6** | **0.85** |
| Apex | 200 | 2.4 | 20 | 1.7 | 8 | 0.90 |
| Drone | 22 | 4.2 | 32 | 0.7 | — | — |

Strengths: burst close, collision→Aether, spell-weapon versatility.  
Weaknesses: sustained DPS vs capitals, long-range kite, Aether starvation if bursting constantly.

## Art direction

- **Palette:** steel `#4a5a6a`, silver `#c8d4e0`, deep teal `#0a3a44`, lateral cyan `#40e0ff`, charge violet `#7a5cff`
- **Silhouette:** torpedo body, crescent tail, pectoral fins, serrated dorsal ridge
- **Vs whale:** sleek predator, not bulky plated organism  
- **Vs dragon:** piscine hydrodynamics, not serpentine dragon capital

## Audio (SA3)

| Event | TX | Starfield-only |
|---|---|---|
| idle | low predator hum + lateral-line tick | spatial_loop hunt bed |
| fire / jaw | wet plasma snap | proximity bite whoosh |
| burst | — | wake roar loop |
| brood | chitter spit | — |

## Pipeline

3D three-quarter concept → TRELLIS 1024 → Ucupaint → 120 facings → Starfield GLB/DDS + `nd_scSpaceShark_*.wav`.

## Concise art prompt

Biometal space shark ship, torpedo piscine hull, steel-silver scales, cyan bioluminescent lateral lines, crescent tail arcane wake, jaw maw weapon ports, serrated dorsal vents, dark starfield, cinematic 3D sculpt.
