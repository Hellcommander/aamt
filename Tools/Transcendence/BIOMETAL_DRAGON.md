# Biometal Dragon — Apex Leveling Capital (above Space Whale)

Living-machine capital craft for Transcendence / ArcaneConduit. Tier sits **above** Space Whale and Leviathan: endgame flagship / dreadnought / living carrier.

## Leveling ladder (organic capitals)

| Tier | Ship family | Role |
|---|---|---|
| Mid | Horn / Ceratotitan | Kinetic charge / swarm screen |
| High | Leviathan | Spiked serpent capital |
| Peak organic | **Space Whale** | Celestial plated leviathan, song/EM, drone bay |
| **Apex** | **Biometal Dragon** | Semi-sentient biometal dragon, organ meters, breath + scale drones |

**Parallel biometal predator line** (see `SPACE_SHARK.md`): Scout → Hunter → Apex Space Shark — skirmishers beside the whale ladder, not a whale evolution.

Whale = ethereal violet crystal organism. Shark = steel-cyan hydrodynamic hunter. Dragon = copper/bronze living-machine capital. Same *segmented capital + drones* pattern; different fantasy and combat kit.

## Ship IDs (asset pack)

| ID | Role | Frame (HD) | Notes |
|---|---|---:|---|
| `scBiometalDragon` | head / capital | 256 | Maw, heart chamber, wing-fins |
| `scBiometalDragonSegment` | body vertebra | 128 | Scale vents, vascular rails |
| `scBiometalDragonTail` | fluke / aft | 128 | Stabilizers + spine weapon |
| `scBiometalDragonDrone` | scale-drone | 64 | Ejected from Scale Launchers |

Poses (head): `idle`, `mawOpen`, `bodyCompress`, `bellyGlow`, `wingSpread`  
Poses (segment/tail/drone): `idle`, `bodyCompress` (+ `spineReady` for tail later)

## Organ → Transcendence systems

| Organ (concept) | TX / combat mapping | Visual / pose | Player feedback |
|---|---|---|---|
| **Aether Heart** | Max power / weapon charge budget; “heart rate” scales DPS & ability uptime | `bellyGlow`; pulse overlay on hull | Meter 30–180 BPM → power mult |
| **Flux Lungs** | Sustained thrust vs stealth (expand = thrust, contract = quieter signature) | `bodyCompress` cycle | Lung volume → thrust / detectability |
| **Vascular Rails** | Power routing to shields / weapons / regen (mutually soft-gated) | Vein pulse VFX along segments | Flow viz when routing |
| **Synaptic Mantle** | AI aggression / aim assist / temper (calm ↔ rage) | Flicker along spine | Temper tied to heart rate |
| **Glandular Nodes** | Hull regen / adaptive armor resist stacks after hit types | Scale discoloration when repairing | Regen HP/s, resist tags |
| **Egg Chamber** | Drone / seed bay (like whale drone rebuild) | Membrane ripple on spawn | Cap 0–48; droneId `scBiometalDragonDrone` |
| **Breath Projectors** | Primary maw weapon (beam / mist / swarm-seed modes) | `mawOpen` | Charge from heart |
| **Scale Launchers** | Secondary: eject guided micro-drones / charges | Segment vents open | Consumes Egg Chamber |
| **Vascular Shock Coils** | Defensive EMP / arc pulse on hull | Full-body flash | Heart + vascular cost |
| **Phase Fins** | Short rift hop / micro-teleport (high cooldown) | `wingSpread` | Flux lungs + heart spike |
| **Tail Spine** | Aft weapon mount / counter-thrust stab | Tail `spineReady` | Independent of maw facing |
| **Bioplasma Jets** | Engine plume color = metabolic load | Trail VFX | Linked to lungs |
| **Camouflage Membrane** | Stealth / refraction (lungs contracted) | Dimmed scales | Opposes high heart rate |

## Combat physics (TX principles)

Same family rules as Space Whale / Ceratotitan:

- Damage from **relative speed × mass × contact**, not scripted multi-hit windows.
- Breath and coils are energy systems gated by **Aether Heart** + **Vascular Throughput**.
- Swarm rebuilds over time from Egg Chamber (whale/Ceratotitan pattern).
- Critical organ failure: regen dump, rift-eject (Phase Fins), or self-sacrifice explosion.

### Balance anchors (starting targets)

| Ship | mass | thrustRatio | maxSpeed | crashOut | maxDrones |
|---|---:|---:|---:|---:|---:|
| scSpaceWhale (ref) | ~200+ | mid | mid | high | mid |
| **scBiometalDragon** | **280** | **2.0** | **16** | **2.0** | **8** |
| scBiometalDragonSegment | — | — | — | — | — |
| scBiometalDragonTail | — | — | — | spine bonus | — |
| scBiometalDragonDrone | **30** | **3.8** | **30** | **0.9** | — |

Dragon is heavier/slower than whale; higher crash and drone cap; breath + coils carry DPS while charge is commitment.

## Audio (SA3 archetypes)

| Event | TX | Starfield-only | Archetype |
|---|---|---|---|
| idle | cardiac thrum | spatial_loop bed | alien / ship |
| fire / breath | roar + plasma | proximity whoosh | laser / impact |
| heart spike | — | 3D organ pulse loop | alien |
| scale eject | short chitter | — | mech |

Files follow existing batch: `nd_scBiometalDragon_*.wav` under Starfield `Data/Sound/ArcaneConduit`.

## Art direction

- **Palette:** copper `#8a4a28`, bronze `#c47a3a`, gunmetal `#2a2e33`, ember `#ff6a20`, heart gold `#ffe08a`
- **Vs whale:** metal-organic scales + molten seams, not violet crystal nebula plates
- **Pipeline:** 3D three-quarter concept → TRELLIS 1024 → Ucupaint → 120 facings @ 256 → Starfield GLB/DDS

## Lore hooks (short)

Grown in a starforge from alloyed living tissue and arcane seedstock. Organs sometimes sing frequencies that open micro-rifts (ties to ArcaneConduit rift tools). Factions harvest glandular nodes for adaptive alloys; pilots who neural-sync to the Synaptic Mantle face ship-welfare dilemmas.

## Concise art prompt

Biometal dragon spaceship, sinuous copper-bronze alloy scales, glowing pulsing Aether Heart chamber, plasma breath maw, articulated wing-fins, semi-organic bridge, dark starfield, cinematic 3D sculpt.
