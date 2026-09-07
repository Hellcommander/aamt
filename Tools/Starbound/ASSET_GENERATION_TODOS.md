# Asset Generation TODO List

This file tracks ongoing and pending asset generation tasks for the Magi-Tech Arcane Alchemy and Sorcery mod.

## Status Legend
- [ ] Not Started
- [ ] In Progress
- [x] Completed
- [~] Partially Complete

---

## Recently Completed (2025-01-19)

### Locomotion System Integration - COMPLETE ✅
- [x] Updated all 6 new Magitech mechforms with proper locomotion types
  - Aether Warden: `hover` (support positioning)
  - Flux Strider: `fly` (high mobility skirmisher)
  - Iron Bloom: `hover` (heavy support with rooting)
  - Null Harrier: `fly` (stealth teleporter)
  - Shardwright: `hover` (modular adaptive)
  - Helix Bastion: `track` (heavy artillery platform)
- [x] Updated existing mechforms to use correct locomotion types
  - Jet Form: `hover` → `fly` (aerial assault)
  - Coil Serpent Form: `serpentine` → `hover_snake` (segmented hover)
  - Rift Wyrm Form: `serpentine` → `hover_snake` (segmented hover with warp)
  - Centipede Form: `crawler` → `ground_crawler` (multi-leg crawler)
  - Tentacled Horror Form: `crawler` → `ground_crawler` (multi-leg crawler)
- [x] Created comprehensive locomotion system integration guide (`LOCOMOTION_SYSTEM_INTEGRATION.md`)
- [x] Documented all 9 locomotion types and their parameters
- [x] Added selection guide for choosing appropriate locomotion types
- [x] Documented performance considerations for each type

### Ollama AI Integration - COMPLETE ✅
- [x] Fixed all parameter mismatches (Name -> AssetName) across PowerShell scripts
- [x] Updated all generation scripts to use `StarboundOllamaAssetGenerator.ps1`
- [x] Created PowerShell bridge (`OllamaCppBridge.ps1`) for C++ backend
- [x] Created Lua helper (`OllamaLuaHelper.lua`) for Lua/C++ integration  
- [x] Created C++ client (`OllamaClient.hpp/cpp`) for direct C++ integration
- [x] Updated `StarboundCppBackendBridge.ps1` to use Ollama for all generator types
- [x] Updated `StarboundAssetGenerator.ps1` to prioritize Ollama-enhanced descriptions
- [x] Updated Python quality checker with Ollama AI assessment
- [x] All scripts now automatically use Ollama when available

### Ollama Model Optimization - COMPLETE ✅ (2025-01-19)
- [x] Optimized model selection for asset generation pipeline:
  - **Structured Planning** (`qwen2.5-coder:14b`): JSON, atlas layouts, segment definitions, spritesheet packing
  - **Creative Concepting** (`llama3.1:8b`): Descriptions, silhouettes, mechform ideas, visual style guides
  - **Hybrid Tasks** (`deepseek-r1:7b`): Concept + structured output, math/balancing, thrust-to-weight ratios
  - **Fallback** (`qwen2.5-coder:7b`): Simple tasks, general fallback
- [x] Updated all asset generation scripts with optimized model routing:
  - `StarboundOllamaAssetGenerator.ps1` - Model routing based on asset type
  - `GenerateMechSetVariants.ps1` - Updated model defaults
  - `GenerateAllAssets.bat` - Updated environment variables
  - `OllamaImageGenerator.ps1` - Creative model for descriptions
  - `OllamaCppBridge.ps1` - Structured model for analysis
  - `OllamaIntegration.psm1` - Updated preferred models list
- [x] Downloaded all required models (23.3 GB total):
  - qwen2.5-coder:14b (9.0 GB) ✅
  - qwen2.5-coder:7b (4.7 GB) ✅
  - llama3.1:8b (4.9 GB) ✅
  - deepseek-r1:7b (4.7 GB) ✅
- [x] Verified Ollama connection and model selection working correctly

**Result**: Asset generation pipeline now uses deterministic models for structured tasks and creative models for visual assets, optimized for spritesheet layouts, atlas packing, and mechform generation.

### GenerateAllAssets.bat - COMPLETE ✅
- [x] Updated to include ALL asset generation scripts
- [x] Added all mech form generation scripts
- [x] Added all system asset generation scripts  
- [x] Added all agent asset generation scripts
- [x] Added all specialized form generation scripts
- [x] Added all crafting and alchemy generation scripts
- [x] Integrated comprehensive error tracking
- [x] Added summary reporting

**Result**: All asset generation tools are now integrated with Ollama AI and ready for batch generation.

---

## Mech Forms - Asset Generation

**System Architecture**: 
- Each mech is a buildable **10-form transforming mech** that can shapeshift between forms using player mana
- Initial generation creates **reference forms** (generic templates)
- Reference forms are used to create **complete 10-form mech sets** (full transforming mechs)
- Each complete mech has up to 10 forms it can transform between

### Workflow
1. **Generate Reference Forms** - Create generic form templates using generation scripts (these are templates)
2. **Build Complete 10-Form Mechs** - Combine reference forms into complete transforming mechs (10 forms per mech)
3. **Apply Variants** - Create visual style variants for complete mechs (optional reskins)

### Completed Reference Forms
- [x] Rhino Mech - Reference form assets generated
- [x] Centipede Mech - Reference form assets generated

### Reference Forms (Initial Generation - Generic Templates)
These are generic reference forms used as templates for creating complete 10-form mech sets:

- [ ] **Biped Form** - All-Purpose reference (JSON + `GenerateAllMechFormAssets.bat` ready)
- [ ] **Hook Slinger Form** - Traversal/Grapple reference (JSON + `GenerateAllMechFormAssets.bat` ready)
- [ ] **Centipede Form** - Terrain Control reference (JSON + `GenerateCentipedeFormAssets.bat` ready)
- [ ] **Rhino Form** - Impact Combat reference (JSON + existing assets)
- [ ] **Jet Form** - Aerial Assault reference (JSON + `GenerateAllMechFormAssets.bat` ready)
- [ ] **Blade Cyclone Form** - Area DPS reference (JSON + `GenerateBladeCycloneFormAssets.bat` ready)
- [ ] **Stealth Form** - Infiltration reference (JSON + `GenerateAllMechFormAssets.bat` ready)
- [ ] **Magma Form** - Environmental reference (JSON + `GenerateAllMechFormAssets.bat` ready)
- [ ] **Gorilla Form** - Heavy Melee reference (JSON + `GenerateAllMechFormAssets.bat` ready)
- [ ] **Walker Form** - Turret/Defense reference (JSON + `GenerateAllMechFormAssets.bat` ready)

**Note**: These reference forms serve as templates. Complete 10-form mechs will be built using these as references.

#### Shared System Assets (Used by All 10-Form Mechs)
These assets are shared systems that work across all 10-form transforming mechs:

- [ ] **Cockpit Assets - REQUIRED** - All forms in all mechs need visible cockpits with alpha channels (`GenerateMechCockpitAssets.bat` ready)
  - Cockpit frames (opaque, per-form style)
  - Cockpit glass (alpha transparency)
  - Cockpit interiors (player visibility area)
- [ ] **Form Wheel UI** - Radial menu for switching between 10 forms in a mech (mana-powered) (`GenerateFormWheelUI.bat` ready)
- [ ] **Form Animation System** - 136 frames per form, 18 cycles - **MUST include cockpit with alpha** (`GenerateMechFormAnimations.bat` ready)
- [ ] **Form Icon System** - 48x48 and 64x64 icons for all forms in all mechs (`GenerateAllMechFormAssets.bat` ready)
- [ ] **Form VFX System** - Enter/exit particles for form transformations (mana-powered shapeshifting) (`GenerateAllMechFormAssets.bat` ready)
- [ ] **Form SFX System** - Activate/deactivate sounds for form transformations (`GenerateAllMechFormAssets.bat` ready)
- [ ] **Mana System Integration** - Visual/audio feedback for mana-powered transformations

### Additional Reference Forms (For Complete 10-Form Mech Sets)
These additional reference forms provide more variety for building complete 10-form mech sets:

#### Elemental Reference Forms
- [ ] **Phoenix Form** - Fire aerial with rebirth ability (JSON created)
- [ ] **Frost Form** - Ice defensive with barriers (JSON created)
- [ ] **Storm Form** - Electric mobility with chain lightning (JSON created)
- [ ] **Crystal Form** - Crystal defensive with reflection (JSON created)
- [ ] **Void Form** - Void teleport with debuffs (JSON created)
- [ ] **Aquatic Form** - Water healing with swim abilities (JSON created)

#### Horror/Eldritch Reference Forms
- [ ] **Tentacled Horror Form** - Void/eldritch abilities (JSON + `GenerateTentacledHorrorFormAssets.bat` ready)
- [ ] **FleshWeaver Form** - Organic horror reference (JSON created)
- [ ] **EldritchAbomination Form** - Eldritch horror reference (JSON created)
- [ ] **NecroticReaper Form** - Death-themed reference (JSON created)
- [ ] **PhantomShroud Form** - Ghostly reference (JSON created)
- [ ] **ParasiticNightmare Form** - Parasitic horror reference (JSON created)

#### Abnormal/Segmented Reference Forms
- [ ] **Coil Serpent Form** - Serpentine reference (JSON + `GenerateAbnormalFormsAssets.bat` ready)
- [ ] **Crystal Spire Form** - Crystal support reference (JSON + `GenerateAbnormalFormsAssets.bat` ready)
- [ ] **Rift Wyrm Form** - Void teleport reference (JSON + `GenerateAbnormalFormsAssets.bat` ready)
- [ ] **Echo Walker Form** - ECM sensor reference (JSON + `GenerateAbnormalFormsAssets.bat` ready)
- [ ] **Bloom Harvester Form** - Organic harvester reference (JSON + `GenerateAbnormalFormsAssets.bat` ready)
- [ ] **Fracture Colossus Form** - Siege boss reference (JSON + `GenerateAbnormalFormsAssets.bat` ready)
- [ ] **Phase Swarm Form** - Swarm controller reference (JSON + `GenerateAbnormalFormsAssets.bat` ready)

#### Quadruped Reference Forms
- [ ] **Raptor Form** - High-agility predator (JSON + `GenerateRaptorFormAssets.bat` ready)
- [ ] **SpiderWeaver Form** - Spider-themed reference (JSON created)
- [ ] **ScorpionStrike Form** - Scorpion-themed reference (JSON created)
- [ ] **SaberCat Form** - Feline predator reference (JSON created)
- [ ] **TankBeast Form** - Heavy quadruped reference (JSON created)
- [ ] **WolfPack Form** - Pack hunter reference (JSON created)

#### Race-Themed Reference Forms
- [ ] **HumanMilitary Form** - Human military reference (JSON created)
- [ ] **HylotlZen Form** - Hylotl zen reference (JSON created)
- [ ] **NovakidStarburst Form** - Novakid starburst reference (JSON created)
- [ ] **ApexLab Form** - Apex lab reference (JSON created)
- [ ] **FloranGrower Form** - Floran grower reference (JSON created)
- [ ] **GlitchKnight Form** - Glitch knight reference (JSON created)
- [ ] **AvianTemple Form** - Avian temple reference (JSON created)

#### Specialized Reference Forms
- [x] **Hydra Chassis Form** - Modular beast components (17 modules, JSON + `GenerateHydraChassisAssets.bat` ready, UI implemented)
  - Module Swapper UI: `/interface/magitech/hydraChassisModuleUI.config` - Visual component swapping interface
  - FormBus Plugin: `/scripts/BusPlugins/FormBus/HydraChassisBusPlugin.lua` - Module management and swapping logic
  - 17 modules across 9 slot types: head (3), mid (3), tail (3), ring (1), rotor (1), arm (1, can equip 2), ram (1), legs (3), dome (1)

#### New Magitech Mechforms (Balanced & Modular)
These are new balanced, modular mechforms tuned for gameplay variety and balance. Each includes shapeshift modes and segment layouts. Mass, thrust-to-weight, and base fuel capacity are defined at the mechset level, but individual forms can modify fuel consumption rates (e.g., Glide Mode might reduce fuel consumption, while Burst Overdrive increases it).
- [x] **Aether Warden Form** - Support/battlefield control mech (JSON created)
  - Ward Mode: Moving hemispherical shield for allies
  - Anchor Mode: Tether anchor that slows enemies and redirects projectiles
  - Phase Relay: Short-range teleport burst for allies
- [x] **Flux Strider Form** - Hit-and-run skirmisher mech (JSON created)
  - Blade Dash: High-speed dash attack using thrusters with blade extensions for melee damage
  - Glide Mode: Low-drag aerodynamic configuration for sustained high-speed movement
  - Burst Overdrive: Temporary thrust overdrive for rapid repositioning and escape
- [x] **Iron Bloom Form** - Area control/sustain mech (JSON created)
  - Bloom: Unfolds layered armor petals with healing aura
  - Harvest: Roots to siphon energy nodes for fuel and heals
  - Petal Barrage: Ejects hardened petals as ricocheting projectiles
- [x] **Null Harrier Form** - Disruption/assassination mech (JSON created)
  - Nullstep: Short teleport with EMP pulse at arrival
  - Corruptor: Converts kinetic damage into system debuffs
  - Shadowform: Temporary invisibility with reduced movement
- [x] **Shardwright Form** - Adaptive offense/fragmentation mech (JSON created)
  - Shardcast: Ejects shards that home on targets and explode
  - Reforge: Reabsorbs shards to repair and boost armor
  - Arrayform: Rearranges shard mounts into rotating volley platform
- [x] **Helix Bastion Form** - Mobile artillery/area denial mech (JSON created)
  - Bastion: Locks into high-stability firing platform with armor boost
  - Helix Array: Rotates turrets into spiral volley covering wide arc
  - Rollout: Reconfigures into compact transport for relocation

**Note**: All JSON configs are complete. Asset generation scripts need to be created or adapted for these forms.

---

## Complete 10-Form MagiTech Mechs (Full Transforming Mechs)

**Note**: These are complete buildable mechs with 10 forms each. Players build these mechs and can shapeshift between all 10 forms using mana. Reference forms above are used as templates.

### New Magitech 10-Form Mech Sets (Based on New Magitech Mechforms)
Complete transforming mechs built around the new balanced Magitech Mechforms:
- [x] **Magitech Support Mech Set** - Complete 10-form mech (JSON created)
  - Primary: Aether Warden (Support/battlefield control)
  - Forms: Aether Warden, Iron Bloom, Walker, Crystal Spire, Aquatic, Frost, Hylotl Zen, Bloom Harvester, Biped, Crystal
  - Focus: Support, healing, defensive capabilities
- [x] **Magitech Skirmisher Mech Set** - Complete 10-form mech (JSON created)
  - Primary: Flux Strider (Hit-and-run skirmisher)
  - Forms: Flux Strider, Raptor, Jet, Hook Slinger, Blade Cyclone, Stealth, Storm, Saber Cat, Scorpion Strike, Biped
  - Focus: High mobility, burst damage, hit-and-run tactics
- [x] **Magitech Siege Mech Set** - Complete 10-form mech (JSON created)
  - Primary: Helix Bastion (Mobile artillery/area denial)
  - Forms: Helix Bastion, Fracture Colossus, Walker, Gorilla, Rhino, Tank Beast, Magma, Phoenix, Human Military, Biped
  - Focus: Heavy artillery, area denial, siege warfare
- [x] **Magitech Adaptive Mech Set** - Complete 10-form mech (JSON created)
  - Primary: Shardwright (Adaptive offense/fragmentation)
  - Forms: Shardwright, Phase Swarm, Hydra Chassis, Crystal, Blade Cyclone, Coil Serpent, Spider Weaver, Echo Walker, Biped, Void
  - Focus: Adaptive offense, modular versatility, fragmentation
- [x] **Magitech Assassin Mech Set** - Complete 10-form mech (JSON created)
  - Primary: Null Harrier (Disruption/assassination)
  - Forms: Null Harrier, Stealth, Void, Phantom Shroud, Rift Wyrm, Necrotic Reaper, Tentacled Horror, Raptor, Flux Strider, Biped
  - Focus: Stealth, disruption, assassination tactics
- [x] **Magitech Control Mech Set** - Complete 10-form mech (JSON created)
  - Primary: Iron Bloom (Area control/sustain)
  - Forms: Iron Bloom, Aether Warden, Bloom Harvester, Centipede, Frost, Crystal Spire, Floran Grower, Aquatic, Walker, Biped
  - Focus: Area control, sustain, battlefield manipulation

### Base MagiTech 10-Form Mech Set
Complete transforming mechs built from reference forms:

- [ ] **MagiTech Biped Mech** - Complete 10-form transforming mech (uses Biped + 9 other reference forms)
- [ ] **MagiTech Hook Slinger Mech** - Complete 10-form transforming mech (uses Hook Slinger + 9 other reference forms)
- [ ] **MagiTech Centipede Mech** - Complete 10-form transforming mech (uses Centipede + 9 other reference forms)
- [ ] **MagiTech Rhino Mech** - Complete 10-form transforming mech (uses Rhino + 9 other reference forms)
- [ ] **MagiTech Jet Mech** - Complete 10-form transforming mech (uses Jet + 9 other reference forms)
- [ ] **MagiTech Blade Cyclone Mech** - Complete 10-form transforming mech (uses Blade Cyclone + 9 other reference forms)
- [ ] **MagiTech Stealth Mech** - Complete 10-form transforming mech (uses Stealth + 9 other reference forms)
- [ ] **MagiTech Magma Mech** - Complete 10-form transforming mech (uses Magma + 9 other reference forms)
- [ ] **MagiTech Gorilla Mech** - Complete 10-form transforming mech (uses Gorilla + 9 other reference forms)
- [ ] **MagiTech Walker Mech** - Complete 10-form transforming mech (uses Walker + 9 other reference forms)

### Themed 10-Form Mech Sets (NEW)
Complete transforming mechs with cohesive themes (10 forms per mech):

- [x] **Magitech Elemental Dominance Mech Set** - Complete (JSON created)
  - Forms: Phoenix, Frost, Storm, Crystal, Void, Aquatic, Magma, Shardwright, Null Harrier, Iron Bloom
  - Focus: Master all elemental forces with unique synergies
- [x] **Magitech Eldritch Nightmare Mech Set** - Complete (JSON created)
  - Forms: Tentacled Horror, Flesh Weaver, Eldritch Abomination, Necrotic Reaper, Phantom Shroud, Parasitic Nightmare, Null Harrier, Rift Wyrm, Void, Phase Swarm
  - Focus: Embrace cosmic horror and void corruption
- [x] **Magitech Apex Predator Mech Set** - Complete (JSON created)
  - Forms: Raptor, Saber Cat, Wolf Pack, Spider Weaver, Scorpion Strike, Flux Strider, Coil Serpent, Rift Wyrm, Phoenix, Rhino
  - Focus: Ultimate hunting and predatory instincts with pack bonuses
- [x] **Magitech Galactic Empires Mech Set** - Complete (JSON created)
  - Forms: Human Military, Hylotl Zen, Novakid Starburst, Apex Lab, Floran Grower, Glitch Knight, Avian Temple, Aether Warden, Shardwright, Biped
  - Focus: United technologies of all galactic races with racial synergies
- [x] **Magitech Swarm Commander Mech Set** - Complete (JSON created)
  - Forms: Phase Swarm, Shardwright, Hydra Chassis, Spider Weaver, Wolf Pack, Parasitic Nightmare, Floran Grower, Bloom Harvester, Centipede, Echo Walker
  - Focus: Summon and command autonomous units (max 50 minions)
- [x] **Magitech Titan Warrior Mech Set** - Complete (JSON created)
  - Forms: Helix Bastion, Fracture Colossus, Gorilla, Rhino, Tank Beast, Iron Bloom, Walker, Magma, Glitch Knight, Aether Warden
  - Focus: Overwhelming power and devastating impact with terrain destruction
- [x] **Magitech Dimensional Nomad Mech Set** - Complete (JSON created)
  - Forms: Rift Wyrm, Null Harrier, Void, Phantom Shroud, Echo Walker, Phase Swarm, Flux Strider, Stealth, Aether Warden, Jet
  - Focus: Transcend space and time with teleportation and phasing
- [x] **Magitech Nature Spirit Mech Set** - Complete (JSON created)
  - Forms: Iron Bloom, Bloom Harvester, Floran Grower, Aquatic, Crystal, Crystal Spire, Centipede, Gorilla, Rhino, Phoenix
  - Focus: Harmonize with natural forces for growth and primal fury
- [x] **Magitech Metamorph Master Mech Set** - Complete (JSON created)
  - Forms: Shardwright, Flux Strider, Hydra Chassis, Blade Cyclone, Coil Serpent, Echo Walker, Phase Swarm, Centipede, Phoenix, Biped
  - Focus: Rapid shapeshifting with chain transformation combos
- [x] **Magitech Balanced Warrior Mech Set** - Complete (JSON created)
  - Forms: Biped, Aether Warden, Flux Strider, Helix Bastion, Null Harrier, Shardwright, Iron Bloom, Raptor, Walker, Jet
  - Focus: Perfect balance across all combat roles
- [x] **Magitech Chrono Weaver Mech Set** - Complete (JSON created)
  - Forms: Echo Walker, Phoenix, Frost, Storm, Flux Strider, Rift Wyrm, Phase Swarm, Aether Warden, Shardwright, Stealth
  - Focus: Time manipulation (Rewind, Time Stop, Accelerate, Future Vision)
- [x] **Magitech Dragonlords Legacy Mech Set** - Complete (JSON created)
  - Forms: Phoenix, Frost, Storm, Rift Wyrm, Magma, Coil Serpent, Crystal, Tentacled Horror, Helix Bastion, Hydra Chassis
  - Focus: Draconic powers with multiple breath weapons (Fire, Ice, Lightning, Void)
- [x] **Magitech Chaos & Harmony Mech Set** - Complete (JSON created)
  - Forms: Shardwright, Blade Cyclone, Aether Warden, Fracture Colossus, Crystal Spire, Phase Swarm, Hylotl Zen, Void, Iron Bloom, Biped
  - Focus: Toggle between chaos and order for different bonuses
- [x] **Magitech Stormcaller Mech Set** - Complete (JSON created)
  - Forms: Storm, Frost, Phoenix, Aquatic, Jet, Magma, Void, Blade Cyclone, Crystal, Novakid Starburst
  - Focus: Control all weather (Thunderstorms, Blizzards, Hurricanes, Tornadoes)
- [x] **Magitech Necrotic Overlord Mech Set** - Complete (JSON created)
  - Forms: Necrotic Reaper, Phantom Shroud, Parasitic Nightmare, Flesh Weaver, Eldritch Abomination, Tentacled Horror, Void, Phase Swarm, Centipede, Hydra Chassis
  - Focus: Necromancy (Raise 30 undead, life drain, plague, soul harvest)
- [x] **Magitech Ancient Mystic Mech Set** - Complete (JSON created)
  - Forms: Avian Temple, Glitch Knight, Hylotl Zen, Crystal Spire, Iron Bloom, Aether Warden, Phoenix, Rift Wyrm, Fracture Colossus, Hydra Chassis
  - Focus: Ancient magic and primordial forces (Forgotten spells, artifacts, timelessness)
- [x] **Magitech Vanguard Assault Mech Set** - Complete (JSON created)
  - Forms: Train Siege, Modular Walker, Drone Carrier, Flight Command, Phase Swarm, Fracture Colossus, Rhino, Crystal, Hook Slinger, Jet
  - Focus: Combined arms warfare - heavy siege, mobility, and tactical drone support
  - Features: Max 30 drones, energy drain per active drone (0.9/drone/sec)

### System-Integrated 10-Form Mech Sets (MOD SYSTEM INTEGRATION)
Complete transforming mechs integrating with specific mod systems:

- [x] **Magitech Grand Alchemist Mech Set** - Complete (JSON created)
  - Forms: Iron Bloom, Shardwright, Magma, Frost, Aquatic, Storm, Void, Phase Swarm, Helix Bastion, Biped
  - System: Dynamic Potion Ammo, Reagents, Crafting Stations, Alchemical Reactions
  - Features: 2x alchemy mastery, mobile lab, instant craft, parallel processing
- [x] **Magitech Arcane Sorcerer Mech Set** - Complete (JSON created)
  - Forms: Phoenix, Frost, Storm, Void, Crystal, Aether Warden, Shardwright, Echo Walker, Helix Bastion, Biped
  - System: Magic Orbs, Spellstones (3 elemental + 3 destructive + 3 utility slots)
  - Features: 2.2x spell power, 6 orb mod slots, spell echoes, chain casting
- [x] **Magitech Golemancer Mech Set** - Complete (JSON created)
  - Forms: Fracture Colossus, Iron Bloom, Magma, Frost, Crystal, Flesh Weaver, Phase Swarm, Hydra Chassis, Walker, Biped
  - System: Golemancy (Stone, Iron, Magma, Ice, Crystal, Flesh, Void golems)
  - Features: Max 10 golems, permanent duration, 2x golem power, auto-upgrade
- [x] **Magitech Portal Master Mech Set** - Complete (JSON created)
  - Forms: Rift Wyrm, Void, Null Harrier, Phase Swarm, Echo Walker, Aether Warden, Flux Strider, Hydra Chassis, Crystal, Biped
  - System: Portal Agent, Portal Networks, Dimensional Travel
  - Features: 20 simultaneous portals, 1000m link range, portal bombs, temporal portals
- [x] **Magitech Wild Magic Channeler Mech Set** - Complete (JSON created)
  - Forms: Void, Eldritch Abomination, Shardwright, Flux Strider, Phase Swarm, Storm, Blade Cyclone, Fracture Colossus, Phoenix, Biped
  - System: Wild Magic, Spell Backslash, Chaos Magic
  - Features: 3x wild magic resonance, 40% surge chance, chaos tolerance, reality warping
- [x] **Magitech Relic Hunter Mech Set** - Complete (JSON created)
  - Forms: Avian Temple, Glitch Knight, Hylotl Zen, Apex Lab, Crystal Spire, Fracture Colossus, Rift Wyrm, Echo Walker, Aether Warden, Biped
  - System: Relics, Artifacts, Ancient Items
  - Features: 10 relic slots, set bonuses (up to 3x at 10 pieces), 3x discovery rate
- [x] **Magitech Terra Shaper Mech Set** - Complete (JSON created)
  - Forms: Centipede, Fracture Colossus, Gorilla, Crystal, Magma, Frost, Iron Bloom, Walker, Helix Bastion, Biped
  - System: Terrain Manipulation, Mining, Construction
  - Features: 15m dig radius, 5x dig speed, 3x mining bonus, free block placement, terraforming
- [x] **Magitech Reaction Catalyst Mech Set** - Complete (JSON created)
  - Forms: Shardwright, Magma, Frost, Storm, Void, Aquatic, Crystal, Phase Swarm, Helix Bastion, Biped
  - System: Magical Reactions, Science Reactions, Chain Reactions
  - Features: 2.5x reaction mastery, 10-chain reactions, all known reactions, cascading explosions
- [x] **Magitech Dungeon Delve Mech Set** - Complete (JSON created)
  - Forms: Echo Walker, Hook Slinger, Stealth, Centipede, Walker, Aether Warden, Iron Bloom, Fracture Colossus, Crystal, Biped
  - System: Dungeon Exploration, Boss Battles, Loot Finding
  - Features: 3x secret detection, trap immunity, boss damage bonus, instant lockpick
- [x] **Magitech Weather Lord Mech Set** - Complete (JSON created)
  - Forms: Storm, Frost, Phoenix, Aquatic, Jet, Blade Cyclone, Void, Magma, Novakid Starburst, Biped
  - System: Weather Control, Atmospheric Manipulation
  - Features: Global weather change, extreme weather (tornadoes, blizzards), 500m range
- [x] **Magitech Enchanter Supreme Mech Set** - Complete (JSON created)
  - Forms: Crystal, Aether Warden, Shardwright, Glitch Knight, Phoenix, Void, Avian Temple, Apex Lab, Iron Bloom, Biped
  - System: Enchantment, Augmentation, Equipment Enhancement
  - Features: 15 enchantment slots, 2.5x power, permanent enchants, mass enchanting
- [x] **Magitech Space Voyager Mech Set** - Complete (JSON created)
  - Forms: Jet, Novakid Starburst, Rift Wyrm, Helix Bastion, Aether Warden, Phase Swarm, Echo Walker, Walker, Flux Strider, Biped
  - System: Orbital Strikes, Hyperdrive, Ship Physics, Satellites
  - Features: Orbital bombardment (500 damage), FTL travel, 10 satellites, ship integration
- [x] **Magitech Biome Adaptive Mech Set** - Complete (JSON created)
  - Forms: Magma, Frost, Aquatic, Jet, Iron Bloom, Centipede, Void, Storm, Crystal Spire, Biped
  - System: Biome Adaptation, Environmental Hazards
  - Features: 3x environmental adaptation, biome-specific immunity, local biome control
- [x] **Magitech Drone Command Mech Set** - Complete (JSON created, rebalanced)
  - Forms: Drone Carrier, Flight Command, Artillery Drone, Sub Drone, Phase Swarm, Serpent Swarm, Shardwright, Echo Walker, Spider Weaver, Modular Walker
  - System: Drone Deployment, Coordination
  - Features: Max 50 drones, energy drain per active drone (0.8/drone/sec)
- [x] **Magitech Swarm Master Mech Set** - Complete (JSON created, rebalanced)
  - Forms: Phase Swarm, Serpent Swarm, Spider Weaver, Parasitic Nightmare, Wolf Pack, Floran Grower, Centipede, Shardwright, Hydra Chassis, Echo Walker
  - System: Massive Drone Swarms, Coordinated Attacks
  - Features: Max 75 drones, energy drain per active drone (0.6/drone/sec)
- [x] **Magitech Tactical Drone Mech Set** - Complete (JSON created, rebalanced)
  - Forms: Drone Carrier, Flight Command, Artillery Drone, Sub Drone, Echo Walker, Modular Walker, Shardwright, Aether Warden, Stealth, Null Harrier
  - System: Tactical Drone Deployment, Specialized Units
  - Features: Max 30 drones, energy drain per active drone (1.0/drone/sec)
- [x] **Magitech Hybrid Drone Mech Set** - Complete (JSON created, rebalanced)
  - Forms: Serpent Swarm, Drone Carrier, Spider Weaver, Parasitic Nightmare, Floran Grower, Bloom Harvester, Flesh Weaver, Phase Swarm, Centipede, Shardwright
  - System: Organic/Mechanical Drone Fusion
  - Features: Max 45 drones, energy drain per active drone (0.7/drone/sec)

### Mech Variant Sets (Visual Style Variants for 10-Form Mechs)
Each variant set applies a cohesive visual style to complete 10-form mechs. Variants are visual reskins that maintain the same transforming functionality:

- [ ] **Void-Corrupted Variant Set** - Dark shadowy variant for all 10-form mechs (`GenerateMechVariantSet.bat -VariantName voidCorrupted`)
- [ ] **Crystal-Infused Variant Set** - Brilliant crystal variant for all 10-form mechs (`GenerateMechVariantSet.bat -VariantName crystalInfused`)
- [ ] **Infernal Variant Set** - Fire-forged variant for all 10-form mechs (`GenerateMechVariantSet.bat -VariantName infernal`)
- [ ] **Arctic Variant Set** - Frost-forged variant for all 10-form mechs (`GenerateMechVariantSet.bat -VariantName arctic`)
- [ ] **Neon Variant Set** - High-tech neon variant for all 10-form mechs (`GenerateMechVariantSet.bat -VariantName neon`)
- [ ] **Custom Variants** - User-defined visual themes for 10-form mechs (`GenerateCustomMechVariant.bat`)

### Reference Form Asset Checklist (per reference form)
Each reference form template requires:
- [ ] Reference form icon (64x64) - Icon for the reference form template
- [ ] **Cockpit assets (REQUIRED)** - For the reference form:
  - [ ] Cockpit frame sprite (opaque, form-specific style)
  - [ ] Cockpit glass sprite (alpha channel, transparent for player visibility)
  - [ ] Cockpit interior sprite (fully transparent alpha channel for player)
- [ ] Reference form assets:
  - [ ] Form sprite/base image
  - [ ] Form VFX particles (enter, loop, exit)
  - [ ] Form animations (136 frames, 18 cycles) - **MUST include cockpit with alpha channel**
  - [ ] Form-specific ability VFX particles
  - [ ] Form sound effects (transform, abilities)
  - [ ] Status effect icons (if form-specific)
  - [ ] Weapon/magic animation sprites - **MUST include cockpit**
  - [ ] Projectile sprites (if applicable)

### Complete 10-Form Mech Asset Checklist (per buildable mech)
Each complete buildable 10-form transforming mech requires:

- [ ] **Mech icon (64x64)** - Icon for the complete buildable mech
- [ ] **All 10 form assets** - Each form in the mech's transformation set:
  - [ ] Form icon (48x48 and 64x64) for each of the 10 forms
  - [ ] Form sprite/base image for each of the 10 forms
  - [ ] **Cockpit assets for each form** (REQUIRED):
    - [ ] Cockpit frame sprite (opaque, form-specific style)
    - [ ] Cockpit glass sprite (alpha channel, transparent for player visibility)
    - [ ] Cockpit interior sprite (fully transparent alpha channel for player)
  - [ ] Form VFX particles (enter, loop, exit) for each form
  - [ ] Form animations (136 frames, 18 cycles) for each form - **MUST include cockpit with alpha channel**
  - [ ] Form-specific ability VFX particles for each form
  - [ ] Form sound effects (transform, abilities) for each form
- [ ] **Shared mech assets**:
  - [ ] Form Wheel UI integration (for switching between 10 forms)
  - [ ] Transformation VFX (mana-powered shapeshifting effects)
  - [ ] Status effect icons (shared across all forms)
  - [ ] Weapon/magic animation sprites - **MUST include cockpit**
  - [ ] Projectile sprites (if applicable)

---

## Weapon Systems - Asset Generation

### Completed Systems
- [x] Enhanced Alchemical Grenade Launcher - All assets generated

### Dynamic Potion Ammo System (Scripts Ready - Run When Ready)
- [ ] Reagent Icons - All reagent icons (64x64) (`GenerateReagentIcons.bat` ready)
- [ ] Container Sprites - All container types (glass vial, metal flask, etc.) (`GenerateDynamicPotionAmmoAssets.bat` ready)
- [ ] Ammo Sprites - Potion grenades, alchemical spheres, container shells (`GenerateDynamicPotionAmmoAssets.bat` ready)
- [ ] Reaction VFX Particles - All reaction type particle effects (`GenerateReactionVFX.bat` ready)
- [ ] Crafting Station Sprites - All station types (alchemy table, magical forge, etc.) (`GenerateCraftingStationAssets.bat` ready)
- [ ] Crafting Station Icons - Station UI icons (32x32) (`GenerateCraftingStationAssets.bat` ready)
- [x] Magic Orb Weapon System - All assets generated

### Pending Weapon Systems
- [ ] Spellstone System - Core spellstone sprites and variants
- [ ] Reagent System - All reagent item sprites
- [ ] Container System - Container item sprites (solid/liquid/gas)
- [ ] Crafting Station - Station object and UI elements
- [ ] Mage Rifle Variants - Different rifle configurations
- [ ] Projectile Variants - Additional projectile types
- [ ] Status Effect Icons - All status effect visual indicators

---

## Animation Assets

### Mech Form Animations
- [ ] Complete animation spritesheets for all reference forms (used as templates)
- [ ] Complete animation spritesheets for all 10 forms in each complete mech:
  - [ ] Base MagiTech 10-Form Mech Set (10 mechs × 10 forms = 100 form animations)
  - [ ] Themed 10-Form Mech Sets (multiple sets × 10 forms each)
- [ ] Weapon-fire animations for all forms in all mechs
- [ ] Magic-cast animations for all forms in all mechs
- [ ] Form-specific movement animations (crawl, climb, swim, etc.) per form type
- [ ] Transformation animations (mana-powered shapeshifting between forms)

### System Animations
- [ ] Crafting station animations
- [ ] Orb mod cycling animations
- [ ] Launcher charging animations
- [ ] Reagent mixing animations

---

## VFX Particles

### Pending Particle Effects
- [ ] Additional elemental particle effects (fire, ice, electric, poison, void)
- [ ] Environmental particles (underwater, lava, space)
- [ ] Status effect particles (buff/debuff indicators)
- [ ] UI particles (hover effects, selection indicators)
- [ ] Reaction particles (alchemical combinations)

---

## Sound Effects

### Pending Sound Categories
- [ ] Additional mech form sounds (remaining forms)
- [ ] Environmental sounds (biome-specific)
- [ ] UI sounds (menu interactions, notifications)
- [ ] Ambient sounds (background loops)
- [ ] Music tracks (if applicable)

---

## UI Assets

### Pending UI Elements
- [ ] Crafting UI panels and buttons
- [ ] Inventory UI elements
- [ ] Status bar components
- [ ] Minimap icons
- [ ] Tooltip backgrounds
- [ ] Menu backgrounds and frames
- [ ] Button states (normal, hover, pressed, disabled)

---

## Projectile Assets

### Pending Projectiles
- [ ] Additional elemental projectiles
- [ ] Grenade variants
- [ ] Orb mod projectiles (remaining mods)
- [ ] Spell projectiles
- [ ] Status effect projectiles

---

## Status Effect Assets

### Pending Status Effects
- [ ] All buff status icons
- [ ] All debuff status icons
- [ ] Temporary effect indicators
- [ ] Stacking effect indicators

---

## Quality Assurance

### Asset Quality Tasks
- [ ] Run quality checker on all generated assets
- [ ] Review and select best assets from duplicates
- [ ] Update BEST_ASSETS_MAPPING.md
- [ ] Verify all asset paths in JSON configs
- [ ] Check for missing asset references
- [ ] Validate asset dimensions and formats
- [ ] Optimize asset file sizes

---

## Integration Tasks

### Code Integration
- [ ] Ensure all form JSON files reference correct asset paths
- [ ] Verify all Lua plugins reference correct asset paths
- [ ] Update asset manifest files
- [ ] Test asset loading in-game
- [ ] Fix any broken asset references

### Documentation
- [x] Document asset naming conventions
- [x] Create asset organization guide
- [ ] Update mod README with asset information
- [x] Document asset generation workflow

### Ollama AI Integration (COMPLETED)
- [x] Fixed parameter mismatches (Name -> AssetName) across all generation scripts
- [x] Updated all PowerShell scripts to use `StarboundOllamaAssetGenerator.ps1`
- [x] Created `OllamaImageGenerator.ps1` for description enhancement and parameter extraction
- [x] Created `OllamaCppBridge.ps1` for C++ backend to call Ollama
- [x] Created `OllamaLuaHelper.lua` for Lua/C++ integration
- [x] Created `OllamaClient.hpp` and `OllamaClient.cpp` for direct C++ integration
- [x] Updated `StarboundCppBackendBridge.ps1` to use Ollama for all generator types
- [x] Updated `StarboundAssetGenerator.ps1` to prioritize Ollama-enhanced descriptions
- [x] Updated Python quality checker to use Ollama for AI-enhanced assessment
- [x] All scripts now automatically use Ollama when available for high-quality asset generation

---

## Batch Generation Tasks

### Large-Scale Generation
- [x] **GenerateAllAssets.bat** - Updated to include ALL asset generation scripts
  - All mech form assets (AllMechForm, Animations, Cockpits, etc.)
  - All specialized forms (Abnormal, Quadruped, Lore, Horror, etc.)
  - All system assets (Enchantment, AlchemistBus, Orbital, VFS, etc.)
  - All agent assets (Buff, Composition, Durability, Inventory, Portal, etc.)
  - All weapon systems (Alchemical Grenade, Enhanced Launcher, Magic Orb)
  - All crafting and alchemy assets (Crafting Station, Potions, Reagents, VFX)
  - All variant sets and custom variants
  - Specialized assets (particles, behaviors, cursors, tiles, ships)
  - Quality checking integrated
- [ ] Generate all remaining mech form assets in batch (scripts ready, run when needed)
- [ ] Generate all reagent sprites in batch (scripts ready)
- [ ] Generate all projectile sprites in batch (scripts ready)
- [ ] Generate all particle effects in batch (scripts ready)
- [ ] Generate all sound effects in batch (scripts ready)

---

## Specialized Asset Sets

### Themed Asset Sets
- [ ] Fire elemental asset set
- [ ] Ice elemental asset set
- [ ] Electric elemental asset set
- [ ] Poison elemental asset set
- [ ] Void/shadow elemental asset set
- [ ] Crystal/earth elemental asset set
- [ ] Water/aquatic asset set
- [ ] Air/wind asset set

---

## Optimization Tasks

### Asset Optimization
- [ ] Compress large sprite files
- [ ] Optimize particle effect configurations
- [ ] Reduce sound file sizes (if needed)
- [ ] Create sprite atlases for better performance
- [ ] Remove unused or duplicate assets

---

## Testing & Validation

### Asset Testing
- [ ] Test all assets load correctly in-game
- [ ] Verify VFX particles display properly
- [ ] Test sound effects play at correct volumes
- [ ] Validate animation cycles are smooth
- [ ] Check projectile sprites are visible
- [ ] Test UI elements display correctly

---

## Priority Tasks (Next Steps)

### High Priority
1. [x] **Ollama AI Integration** - All scripts now use Ollama for high-quality generation
2. [x] **GenerateAllAssets.bat** - Updated to include all asset generation scripts
3. [ ] **Generate reference forms** - Run scripts to create generic reference form templates
4. [ ] **Build complete 10-form mechs** - Use reference forms to create full 10-form transforming mechs
5. [ ] Generate assets for remaining reference forms (Phoenix, Frost, Storm, etc.) - Scripts ready
6. [ ] Complete all reagent and container sprites - Scripts ready
7. [ ] Generate crafting station assets - Scripts ready
8. [ ] Run quality checker on all generated assets (integrated into GenerateAllAssets.bat)
9. [ ] Fix any broken asset references

### Medium Priority
1. [ ] Generate additional projectile variants
2. [ ] Create status effect icon set
3. [ ] Generate UI element library
4. [ ] Complete animation spritesheets

### Low Priority
1. [ ] Generate ambient sound effects
2. [ ] Create additional particle effects
3. [ ] Generate themed asset sets
4. [ ] Optimize existing assets

---

## Notes

- All asset generation scripts are located in: `D:\games\Steam\steamapps\common\Transcendence\Tools\Starbound\`
- Generated assets should be placed in the mod directory: `F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery\`
- **Use `GenerateAllAssets.bat` for full pipeline generation** - Now includes ALL asset types
- Use `GenerateAllAssetsQuick.bat` for quick generation (skips existing)
- Use `GenerateAllAssetsWithCpp.bat` for C++ backend generation
- Run `starbound_asset_quality_checker.bat` after generation to validate quality (now includes Ollama AI assessment)

### Ollama Integration Notes
- **All scripts now use Ollama AI** for high-quality asset generation when available
- Ollama enhances descriptions and extracts parameters to guide procedural generation
- Falls back gracefully if Ollama is unavailable
- C++ backend can use Ollama directly via `OllamaClient` class
- Lua scripts can use Ollama via `OllamaLuaHelper.lua` and PowerShell bridge
- Python quality checker uses Ollama for AI-enhanced quality assessment
- See `CPP_OLLAMA_INTEGRATION.md` and `OLLAMA_INTEGRATION.md` for details

---

## Last Updated
- Date: 2025-01-19 (Updated: 35 Complete Mech Sets + System Integration + Drone Rebalancing)
- Last Completed: 
  - **Ollama AI Integration** - Complete integration across all asset generation tools
    - Fixed parameter mismatches (Name -> AssetName) in all PowerShell scripts
    - Updated all scripts to use `StarboundOllamaAssetGenerator.ps1` for AI-assisted generation
    - Created PowerShell bridge (`OllamaCppBridge.ps1`) for C++ backend
    - Created Lua helper (`OllamaLuaHelper.lua`) for Lua/C++ integration
    - Created C++ client (`OllamaClient.hpp/cpp`) for direct C++ integration
    - Updated bridge scripts to use Ollama for description enhancement
    - Updated Python quality checker with Ollama AI assessment
  - **GenerateAllAssets.bat** - Comprehensive update to include ALL asset generation scripts
    - Added all mech form generation scripts
    - Added all system asset generation scripts
    - Added all agent asset generation scripts
    - Added all specialized form generation scripts
    - Added all crafting and alchemy generation scripts
    - Integrated error tracking and summary reporting
- Last Completed:
  - **Drone Mech Set Rebalancing** - Removed all damage/defense bonuses, added energy drain per active drone
    - Magitech Drone Command Mech Set: 0.8 energy/drone/sec
    - Magitech Swarm Master Mech Set: 0.6 energy/drone/sec
    - Magitech Tactical Drone Mech Set: 1.0 energy/drone/sec
    - Magitech Hybrid Drone Mech Set: 0.7 energy/drone/sec
    - Magitech Vanguard Assault Mech Set: 0.9 energy/drone/sec
    - All sets now properly balanced with energy management instead of combat bonuses
- Last Added: 
  - **Magitech Vanguard Assault Mech Set** (10-form set - JSON config complete)
    - Train Siege, Modular Walker, Drone Carrier, Flight Command, Phase Swarm, Fracture Colossus, Rhino, Crystal, Hook Slinger, Jet
    - Theme: Combined arms warfare with heavy siege, mobility, and drone support
  - **Magitech Bio-Mechanical Hybrid Mech Set** (10-form set - JSON config complete)
    - Blade Cyclone, Spiderweave, Bloom Harvester, Fleshweaver, Raptor, Rift Wyrm, Coil Serpent, Hook Slinger, Jet, Centipede
    - Theme: Organic/Mechanical fusion with segmented mastery and predator tactics 
  - **Expanded Themed Mech Sets** (6 new advanced sets - JSON configs complete)
    - Magitech Chrono Weaver Mech Set (Echo Walker primary, time manipulation)
    - Magitech Dragonlords Legacy Mech Set (Phoenix primary, draconic breath weapons)
    - Magitech Chaos & Harmony Mech Set (Shardwright primary, duality system)
    - Magitech Stormcaller Mech Set (Storm primary, weather control)
    - Magitech Necrotic Overlord Mech Set (Necrotic Reaper primary, necromancy)
    - Magitech Ancient Mystic Mech Set (Avian Temple primary, ancient magic)
  - **Additional Themed Mech Sets** (4 more unique sets - JSON configs complete)
    - Magitech Dimensional Nomad Mech Set (Rift Wyrm primary, teleportation mastery)
    - Magitech Nature Spirit Mech Set (Iron Bloom primary, natural harmony)
    - Magitech Metamorph Master Mech Set (Shardwright primary, rapid transformation)
    - Magitech Balanced Warrior Mech Set (Biped primary, perfect versatility)
  - **Themed Magitech 10-Form Mech Sets** (6 new themed sets - JSON configs complete)
    - Magitech Elemental Dominance Mech Set (Phoenix primary, elemental mastery)
    - Magitech Eldritch Nightmare Mech Set (Tentacled Horror primary, cosmic horror)
    - Magitech Apex Predator Mech Set (Raptor primary, hunting instincts)
    - Magitech Galactic Empires Mech Set (Human Military primary, racial unity)
    - Magitech Swarm Commander Mech Set (Phase Swarm primary, minion mastery)
    - Magitech Titan Warrior Mech Set (Helix Bastion primary, overwhelming power)
  - **New Magitech 10-Form Mech Sets** (6 complete transforming mechs - JSON configs complete)
    - Magitech Support Mech Set (10 forms, Aether Warden primary)
    - Magitech Skirmisher Mech Set (10 forms, Flux Strider primary)
    - Magitech Siege Mech Set (10 forms, Helix Bastion primary)
    - Magitech Adaptive Mech Set (10 forms, Shardwright primary)
    - Magitech Assassin Mech Set (10 forms, Null Harrier primary)
    - Magitech Control Mech Set (10 forms, Iron Bloom primary)
  - **New Magitech Mechforms** (6 balanced, modular mechforms - JSON configs complete)
    - Aether Warden Form (Support/battlefield control)
    - Flux Strider Form (Hit-and-run skirmisher)
    - Iron Bloom Form (Area control/sustain)
    - Null Harrier Form (Disruption/assassination)
    - Shardwright Form (Adaptive offense/fragmentation)
    - Helix Bastion Form (Mobile artillery/area denial)
  - Raptor Form (JSON + generation scripts ready)
  - Blade Cyclone Form (JSON + generation scripts ready)
  - Tentacled Horror Form (JSON + generation scripts ready)
  - Hydra Chassis modular system (JSON + generation scripts ready)
  - Dynamic Potion Ammo System (JSON configs + generation scripts ready)
    - Reagent icons, container sprites, ammo sprites, reaction VFX, crafting stations
- Next Focus: 
  - Run `GenerateAllAssets.bat` to generate all assets with Ollama AI assistance
  - All scripts are ready and will automatically use Ollama when available
  - Quality checking is integrated into the generation pipeline
