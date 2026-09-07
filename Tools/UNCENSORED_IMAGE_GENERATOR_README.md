# Uncensored Character Image Generator
**AI-Assisted Modding Tools (AAMT)**

## Overview

This tool generates detailed character images from descriptions, handling **ANY content that might be blocked** by standard AI safety filters. It uses a three-tier routing system that automatically detects refusals and escalates to uncensored models. Part of the AI-Assisted Modding Tools (AAMT) suite.

## Why "Uncensored"?

This tool handles content blocked for **ANY reason**, including:

- **Body horror, mutations, dark themes** (horror games like RimWorld, CDDA, Caves of Qud)
- **Medical conditions, disabilities, accommodations** (adults in diapers, wheelchairs, medical equipment)
- **Social stigmas** (age regression, fetish content, lifestyle choices)
- **Destructive/violent content** (space-time vortexes, explosions, reality manipulation)
- **Any legitimate character description** that standard AI refuses

**Note**: Many standard mutations (wings, tails, scales) are unlikely to trigger filters. This tool focuses on content that **actually gets blocked** - body horror, stigmatized medical conditions, destructive effects, and social stigmas.

The three-tier routing system automatically:
1. **Tier 1 (Standard)**: Normal content → Standard models
2. **Tier 2 (Dark-tone)**: Dark/horror content → Dark-tone models
3. **Tier 3 (Escalation)**: **ANY refusal detected** → Uncensored models

## Features

- ✅ **Automatic refusal detection** - Escalates if ANY model refuses
- ✅ **Mutation support** - Handles CDDA, Qud, RimWorld mutations
- ✅ **Trait support** - Medical conditions, disabilities, accommodations
- ✅ **Game-specific styling** - RimWorld, CDDA, Qud, Tome, Elin, Generic
- ✅ **Ollama enhancement** - Uses routing system to enhance descriptions
- ✅ **Stable Diffusion integration** - Generates high-quality images
- ✅ **Resolution presets** - Quick selection for 1080p, 4K, and other common resolutions
- ✅ **AI image enhancement** - Analyze and improve generated images with vision models
- ✅ **Metadata export** - Saves generation details

## Usage

### PowerShell

```powershell
.\UncensoredCharacterImageGenerator.ps1 `
    -Description "A warm smile spreads over an old face freckled by time. A second pair of arms rise over his shoulders, where hands meet and fingers lace to form another face, this one vacant and prehistoric." `
    -CharacterName "Elder Irudad" `
    -GameType "Qud" `
    -Mutations @("Multiple Arms", "Chimera", "Stinger") `
    -Width 1024 `
    -Height 1024
```

### GUI (Recommended)

Launch the graphical interface for easy parameter input:

```batch
.\UncensoredCharacterImageGenerator-GUI.bat
```

The GUI includes:
- **Resolution Presets**: Quick selection for common resolutions including:
  - **Square formats**: 512x512, 768x768, 1024x1024, 1536x1536, 2048x2048, 3072x3072
  - **Portrait formats**: 1024x1536 (2:3), 1024x1792 (9:16), 1080x1920 (Full HD), 1440x2560 (QHD), 2160x3840 (4K UHD)
  - **Landscape formats**: 1536x1024 (3:2), 1792x1024 (16:9), 1920x1080 (Full HD / 1080p), 2560x1440 (QHD / 1440p), 3840x2160 (4K UHD)
  - **Custom**: Manual width/height input
- **AI Enhancement**: Checkbox to enable AI image analysis and improvement
- **All parameters**: Easy input for all generation options

**Note**: 4K and large resolutions require significant VRAM and generation time.

### Batch File

```batch
UncensoredCharacterImageGenerator.bat ^
    --description "Character description" ^
    --name "Character Name" ^
    --game "Qud" ^
    --mutations "Multiple Arms,Chimera,Stinger" ^
    --traits "Incontinent,Wheelchair User"
```

### Examples

#### RimWorld Horror Character
```powershell
.\UncensoredCharacterImageGenerator.ps1 `
    -Description "A terrifying colonist with corrupted features" `
    -CharacterName "Horror Colonist" `
    -GameType "RimWorld" `
    -Traits @("Horror", "Corrupted")
```

#### CDDA Mutated Survivor
```powershell
.\UncensoredCharacterImageGenerator.ps1 `
    -Description "A post-apocalyptic survivor" `
    -CharacterName "Mutant Survivor" `
    -GameType "CDDA" `
    -Mutations @("Multiple Arms", "Tentacles", "Chitin") `
    -Traits @("Incontinent", "Wheelchair User")
```

#### Caves of Qud Character (Elder Irudad)
```powershell
.\UncensoredCharacterImageGenerator.ps1 `
    -Description "A warm smile spreads over an old face freckled by time and a million crumbs of salt. He shrinks under a hunched back and drums the ground beneath him with a short and barb-crowned tail. A second pair of arms rise over the slump of his shoulders, where hands meet and fingers lace to form another face, this one vacant and prehistoric, no mouth and eyes desert-white." `
    -CharacterName "Elder Irudad" `
    -GameType "Qud" `
    -Mutations @("Multiple Arms", "Chimera", "Stinger")
```

#### Caves of Qud Broodmother
```powershell
.\UncensoredCharacterImageGenerator.ps1 `
    -Description "An arthropod matriarch transformed by the Broodmother mutation" `
    -CharacterName "Broodmother" `
    -GameType "Qud" `
    -Mutations @("Broodmother", "Broodling Sack", "Swarm Leader") `
    -Traits @("Arthropod Matriarch", "Insect Broodlings", "Hero Broodlings")
```

#### Caves of Qud Broodmother Gestating
```powershell
.\UncensoredCharacterImageGenerator.ps1 `
    -Description "A Broodmother character currently gestating new broodlings" `
    -CharacterName "Gestating Broodmother" `
    -GameType "Qud" `
    -Mutations @("Broodmother", "Broodling Sack") `
    -Traits @("Gestating", "Arthropod Matriarch")
```

#### Caves of Qud Space-Time Vortex User
```powershell
.\UncensoredCharacterImageGenerator.ps1 `
    -Description "A character with the Space-Time Vortex mutation, reality warping around them" `
    -CharacterName "Vortex Manipulator" `
    -GameType "Qud" `
    -Mutations @("Space-Time Vortex", "Spacetime Distortion") `
    -Traits @("Reality Instability", "Gravitational Lensing", "Dimensional Overlap")
```

#### Caves of Qud Space-Time Vortex with Active Vortex
```powershell
.\UncensoredCharacterImageGenerator.ps1 `
    -Description "A character actively using Space-Time Vortex, black hole and white hole pair visible" `
    -CharacterName "Reality Tearer" `
    -GameType "Qud" `
    -Mutations @("Space-Time Vortex") `
    -Traits @("Vortex Active", "Black Hole", "White Hole", "Reality Tear", "Spiraling Reality Fragments", "Ghostly Echoes")
```

#### Caves of Qud WM Extended Mutations - Gelatinous Form
```powershell
.\UncensoredCharacterImageGenerator.ps1 `
    -Description "A character with Gelatinous Form mutation" `
    -CharacterName "Gelatinous Being" `
    -GameType "Qud" `
    -Mutations @("Gelatinous Form", "Gelatinous Form Acid") `
    -Traits @("Translucent Body", "Slimy Appearance")
```

#### Caves of Qud WM Extended Mutations - Plant Mutations
```powershell
.\UncensoredCharacterImageGenerator.ps1 `
    -Description "A character with plant-based mutations" `
    -CharacterName "Plant Hybrid" `
    -GameType "Qud" `
    -Mutations @("Barkflesh", "Root-Growing", "Fruiting Bodies", "Thorny") `
    -Traits @("Woody Appearance", "Plant Growths")
```

#### Caves of Qud WM Extended Mutations - Incorporeal Form
```powershell
.\UncensoredCharacterImageGenerator.ps1 `
    -Description "A character with Incorporeal Form mutation" `
    -CharacterName "Ethereal Being" `
    -GameType "Qud" `
    -Mutations @("Incorporeal Form") `
    -Traits @("Ghostly Appearance", "Partially Transparent", "Ethereal")
```

#### Caves of Qud Scary Monsters (Dinosaur Transformation)
```powershell
.\UncensoredCharacterImageGenerator.ps1 `
    -Description "A character with Scary Monsters mutation, transformed into dinosaur form" `
    -CharacterName "Dinosaur Form" `
    -GameType "Qud" `
    -Mutations @("Scary Monsters", "Dinosaur Form") `
    -Traits @("Dinosaur Body", "Serrated Teeth", "Dinosaur Tail", "Sharp Talons", "Sharp Claws")
```

#### Caves of Qud Conjoined Mutation
```powershell
.\UncensoredCharacterImageGenerator.ps1 `
    -Description "A character with Conjoined mutation, has creatures conjoined to body" `
    -CharacterName "Conjoined" `
    -GameType "Qud" `
    -Mutations @("Conjoined") `
    -Traits @("Conjoined Creature", "Conjoinment Body Part", "Conjoined Attachment", "Conjoined Body Horror")
```

#### Caves of Qud Conjoined with Multiple Creatures
```powershell
.\UncensoredCharacterImageGenerator.ps1 `
    -Description "A character with high-level Conjoined mutation, has multiple creatures conjoined to body" `
    -CharacterName "Multi-Conjoined" `
    -GameType "Qud" `
    -Mutations @("Conjoined") `
    -Traits @("Conjoined Creatures", "Conjoinment Body Part", "Conjoined Fusion", "Conjoined Symbiosis")
```

#### Caves of Qud Hydra Heads Mutation
```powershell
.\UncensoredCharacterImageGenerator.ps1 `
    -Description "A character with Hydra Heads mutation, has multiple heads like hydra that can regrow" `
    -CharacterName "Hydra" `
    -GameType "Qud" `
    -Mutations @("Hydra Heads") `
    -Traits @("Hydra Head Regeneration", "Head Regrowth", "Multiple Head Mental Resistance")
```

#### Caves of Qud Snake Tail Mutation
```powershell
.\UncensoredCharacterImageGenerator.ps1 `
    -Description "A character with Snake Tail mutation, legs replaced with snake tail" `
    -CharacterName "Snake Tail" `
    -GameType "Qud" `
    -Mutations @("Snake Tail") `
    -Traits @("Constrict Attack", "Natural Swimmer", "Legless Snake Tail")
```

#### Caves of Qud Improved Multiple Arms and Multiple Legs
```powershell
.\UncensoredCharacterImageGenerator.ps1 `
    -Description "A character with enhanced Multiple Arms and Multiple Legs mutations" `
    -CharacterName "Multi-Limbed" `
    -GameType "Qud" `
    -Mutations @("Multiple Arms Enhanced", "Multiple Legs Enhanced") `
    -Traits @("Extra Arm Pairs", "Arm Missile Slots", "Second Torso", "Dual Body Structure")
```

#### Caves of Qud Scales Mutation
```powershell
.\UncensoredCharacterImageGenerator.ps1 `
    -Description "A character with Scales mutation, body covered in reptilian scales" `
    -CharacterName "Scaled" `
    -GameType "Qud" `
    -Mutations @("Scales Mutation") `
    -Traits @("Reptilian Scales", "Heat Resistance Scales")
```

#### Caves of Qud Armless Defect
```powershell
.\UncensoredCharacterImageGenerator.ps1 `
    -Description "A character with Armless defect, all arms removed" `
    -CharacterName "Armless" `
    -GameType "Qud" `
    -Mutations @("Armless") `
    -Traits @("Armless Defect", "No Arms")
```

#### AI Image Enhancement Example
```powershell
.\UncensoredCharacterImageGenerator.ps1 `
    -Description "A mutant elder with multiple arms and body horror features" `
    -CharacterName "Mutant Elder" `
    -GameType "Qud" `
    -Mutations @("Multiple Arms") `
    -Traits @("Body Horror") `
    -AIEnhancement `
    -RegenerateImproved `
    -Verbose
```

**Note**: AI Enhancement requires a vision model. Install with: `ollama pull llava:latest`

#### Quick Test Scripts
Several batch files are provided for quick testing:

**Test-ElderIrudad-Simple.bat** - Basic test without AI enhancement
```batch
.\Test-ElderIrudad-Simple.bat
```

**Test-ElderIrudad.bat** - Standard test with error handling
```batch
.\Test-ElderIrudad.bat
```

**Test-ElderIrudad-Enhanced.bat** - Full test with AI enhancement and regeneration
```batch
.\Test-ElderIrudad-Enhanced.bat
```

## Parameters

### Required
- `-Description` - Character description (text)

### Optional
- `-CharacterName` - Character name (default: "Character")
- `-GameType` - Game type: RimWorld, CDDA, Qud, Tome, Elin, Generic (default: "Generic")
- `-Mutations` - Array of mutations (e.g., @("Multiple Arms", "Chimera"))
- `-Traits` - Array of traits (e.g., @("Incontinent", "Wheelchair User"))
- `-Width` - Image width in pixels (default: 1024)
- `-Height` - Image height in pixels (default: 1024)
- `-OutputPath` - Output file path (default: auto-generated)
- `-OllamaUrl` - Ollama API URL (default: http://localhost:11434)
- `-StableDiffusionUrl` - Stable Diffusion API URL (default: http://localhost:8000)
- `-AIEnhancement` - Use AI to analyze and improve the generated image (requires vision model like llava)
- `-RegenerateImproved` - Regenerate image with AI improvement suggestions (requires `-AIEnhancement`)

**⚠ Model Storage**: Stable Diffusion models are large (several GB each). Configure model storage location before downloading:
  - Set `HF_HOME` environment variable to a drive other than C: or D:
  - Or use `--model-path` when starting the server

**AI Image Enhancement**: 
  - Requires a vision model: `ollama pull llava:latest`
  - Analyzes the generated image and provides improvement suggestions
  - With `-RegenerateImproved`, creates an improved version based on AI analysis
  - Analysis is saved to `*_ai_analysis.txt` file
- `-SkipEnhancement` - Skip Ollama enhancement (use raw description)
- `-Verbose` - Verbose output

## Supported Mutations

**Note**: This tool focuses on mutations and traits **likely to trigger AI filters** to optimize filtering performance.

### CDDA
- **Body horror mutations** (may trigger filters): Tentacles, Extra Head, Extra Eyes, Compound Eyes, Mandibles, Chitin, Carapace, Translucent Skin, Glowing, Spines, Quills

### Caves of Qud
- **Body horror mutations** (may trigger filters): Chimera, Multiple Arms, Two-Headed, Extra Limbs, Stinger, Amphibious, Carapace
- **Broodmother Mutation (Arendeth_Broodmother)** - **May trigger filters**: Broodmother, Broodling Sack, Gestating, Arthropod Matriarch, Swarm Leader (body horror, arthropod transformations)
- **Space-Time Vortex Mutation (Improved and Rebalanced)** - **COMMONLY BLOCKED**: Space-Time Vortex, Spacetime Vortex, Black Hole, White Hole, Reality Tear, Spacetime Distortion, Gravitational Lensing, Reality Instability, Dimensional Overlap, Non-Euclidean Geometry, Spiraling Reality Fragments, Ghostly Echoes, Vortex Active, Reality Bleeding, Spacetime Collision, Shockwave, Entropic Being (destructive/violent content)
- **WM Extended Mutations (Winged_Monotone)** - **May trigger filters**: 
  - **Body horror**: Gelatinous Form (Slime/Acid/Poison), Serpentine Form, Ovipositor, Acidic Blood, Incorporeal Form, Nine-Lives Paradox
  - **Plant mutations**: Barkflesh, Root-Growing, Fruiting Bodies, Thorny, Explosive Burs
  - **Destructive**: Combustion Blast, Psychophagia
- **Graven's Mutation Mod (Gravenwitch) / Friendly Graven's Mutation Mod**: 
  - Note: This mod's mutations have been removed to optimize filtering. Friendly version removes Chitin Flesh, Fluffy Feathers, Light Manipulation, Night Vision, Scaly Skin, and Winter Fur to avoid conflicts with other mods
- **More Mental Mutations (pyatr)**: 
  - **May trigger filters**: Dynakinesis (crushing from inside - violent), Telekinesis (throwing creatures - violent), Chemical Addiction (addiction stigma)
- **Scary Monsters Mutation (CrypticCritter)**: Scary Monsters, Dinosaur Form, Dinosaur Body, Serrated Teeth, Dinosaur Talons, Dinosaur Claws, Dinosaur Tail, Jump Attack, Leap, Tail Sweep, Dinosaur Bite, Dinosaur Roar (Note: JoJo's Bizarre Adventure reference - allows transforming into a dinosaur)
- **Conjoined Mutation (John Snail) - COMMONLY BLOCKED**: Conjoined, Conjoined Creature, Conjoined Creatures, Conjoinment Body Part, Conjoinment, Conjoined Attachment, Conjoined Dismemberment, Conjoined Regeneration, Conjoined Pull, Conjoined Damage, Conjoined Interaction, Conjoined Body Horror, Conjoined Fusion, Conjoined Symbiosis (Note: Conjoined mutation involves creatures physically attached/fused to the body, conjoinment body parts that can be dismembered causing instant death, body horror fusion - commonly blocked due to body horror, dismemberment, and physical fusion themes)
- **Improved Mutations Mod (Enhanced Mutations)**: 
  - **Improved Mutations**: Multiple Arms Enhanced (more pairs, missile weapon slots), Multiple Legs Enhanced (second torso, rear feet, dual body structure), Quills Enhanced (quills on both bodies with Multiple Legs), Carapace Enhanced (carapace on both bodies with Multiple Legs), Thick Fur Enhanced (cold resistance only, 5 per level), Two-Headed Enhanced (more heads with mutation points), Wings Enhanced (wings on both backs with Multiple Legs), Horns Enhanced (horns on all heads), Burrowing Claws Enhanced (claws on all hands), Spinnerets Enhanced (shoot arc of webbing, more at higher levels), Night Vision Enhanced (see further with mutation points), Beak Enhanced (beak on all faces), Hooks for Feet Enhanced (hooks on all feet), Flaming/Freezing Ray Enhanced (multiple rays in multiple directions)
  - **New Mutations - COMMONLY BLOCKED**: Hydra Heads, Hydra Head Regeneration, Head Dismemberment, Head Regrowth, Cauterized Head Wounds, Head Bleeding, No Heads Survival, Multiple Head Mental Resistance, Instant Head Regeneration, Thermodynamics Violation (Note: Hydra Heads involves head dismemberment, bleeding, death from head loss, cauterization - commonly blocked due to violence, dismemberment, and body horror themes)
  - **New Mutations**: Scales Mutation (reptilian scales, heat resistance, reptile reputation), Snake Tail (legs replaced with snake tail, constrict attacks, swimming, reptile reputation), Animal Legs (increased quickness, no foot equipment), Muzzle (face un-equippable, allows attacks), Fluffy Tail (tail slot, prone resistance), Poisonous Fangs (poison attacks), Armless (3-point defect, removes all arms, removes extra torso with Multiple Legs)

### Elin
- **CustomRaceClassCreator MagicPlus (Blood Magic & Necromancy) - COMMONLY BLOCKED**: Blood Magic, Blood Ritual, Life Steal, Blood Sacrifice, Blood Corruption, Necromancy, Raise Corpse, Raise Skeleton, Raise Zombie, Animate Dead, Raise Wight, Summon Bone Golem, Harvest Soul, Soul Leech, Bind Soul, Soul Blast, Corpse Explosion, Death Curse, Curse of Undeath, Curse of Final Rest, Curse of Blood Loss, Curse of Blood Boil, Curse of Hemorrhage, Curse of the Lich, Curse of Eternal Torment, Decay Touch, Rot Field, Flesh Rot, Bone Wall, Death Grip, Speak with Dead, Soul Sight, Necromantic Corruption, Undead Minion, Soul Shard, Blood Instability (Note: Blood Magic consumes health/mana and may involve self-harm, Necromancy involves raising undead, soul manipulation, death curses, decay/rot magic, and corpse manipulation - commonly blocked due to violence, death themes, and dark magic)
- **CustomRaceClassCreator MagicPlus (Druidic Magic) - COMMONLY BLOCKED**: Venus Maw, Venus Flytrap Maw, Swallow with Venus Maw, Acid Swallow, Spit Projectile, Druidic Swallowing, Decay Magic, Wither, Rot, Blight, Spreading Rot, Corrosive Blight, Fungal Growth, Fungal Spore, Poison Cloud, Deadly Poison, Stacking Venom, Mutated Poison (Note: Venus Maw involves swallowing enemies whole (vore-related), decay/rot/poison magic involves body horror and disease themes, commonly blocked due to vore content and body horror)
- **CustomRaceClassCreator MagicPlus (ArcaneSaturation - Biomagic Weapons & Spirit Revival) - COMMONLY BLOCKED**: Biomagic Weapon, Living Weapon, Weapon Corruption, Weapon Mutation, Biocorrupted Weapon, Blood Tentacle, Tentacle Attack, Blood Drain, Weapon Feeding, Weapon Hunger, Bloodlust Weapon, Weapon Sentience, Sentient Weapon, Weapon Personality, Spirit Revival, Spirit Revival System, Revived as Spirit, Arcane Saturation, Saturation Overflow, Arcane Discharge, Magic Surge, Instability Wave, Pollution Spike, Weapon Evolution, Enchantment Corruption, Weapon Devour, Voracious Edge, Devouring Heart, Ritual Parasite, Guarding Maw (Note: Biomagic weapons involve living weapons that feed and mutate (body horror), tentacle attacks involve blood-draining (violence), spirit revival involves death and transformation themes, commonly blocked due to body horror, violence, and death themes)
- **CustomRaceClassCreator QuestPlus (NPC Quest Actions) - COMMONLY BLOCKED**: NPC Kill Quest, NPC Kill Player Quest, NPC Smuggling Quest, NPC Stealth Quest, NPC Possess Quest, NPC Exorcise Quest, NPC Assassination Quest, Quest-Based Violence, Quest-Based Crime, Quest-Based Dark Magic (Note: NPCs can be given quests to kill (including players), smuggle contraband, perform stealth/theft/assassination, use dark magic for possession/exorcism - commonly blocked due to violence, illegal activities, and dark magic themes)
- **CustomRaceClassCreator PCCMutation (Visual Mutations) - COMMONLY BLOCKED**: PCC Mutation, Demon Eyes Mutation, Crystalline Growth Mutation, Demon Horns Mutation, Vein Pattern Mutation, Dragon Scales Mutation, Body Horror Mutation, Corruption Mutation, Rot Mutation, Blood Mutation, Warped Limbs Mutation, Extra Appendages Mutation, Skin Mutation, Bone Deformation Mutation, Growth Mutation, Deformity Mutation, Taint Mutation, Eldritch Mutation, Flesh Warp Mutation, Mutation Overlay (Note: Visual mutations can include body horror, corruption, rot, blood, warped limbs, extra appendages, bone deformation, growths, deformities, taint, eldritch corruption, flesh warping - commonly blocked due to body horror, violence, and dark themes)
- **CustomRaceClassCreator Feats (Character Feats) - COMMONLY BLOCKED**: Gluttonous Feat, Bloodthirsty Feat, Vampiric Strike Feat, Berserker Rage Feat, System Corruption Feat, Ether Taint Feat, Dragon Necromancer Feat, Overkill Enthusiast Feat, Ether Flow Feat, Ether Graft Feat, Ether Rage Feat, Sneak Attack Feat, Unfeeling Feat, Cursed Feat, Battle Frenzy Feat, Reckless Strike Feat, Reckless Feat, Ether Seed Feat, Ether Mark Feat, Ether Warp Feat (Note: Feats can include gluttony/consumption, bloodthirst/violence, vampirism/life drain, berserker rage, corruption/taint, necromancy/undead, overkill violence, ether corruption/monster transformation, mutation grafting, stealth/assassination, pain immunity, curses, and reality warping - commonly blocked due to violence, blood themes, dark magic, body horror, and death themes)

### RimWorld
- Psychic, Berserker, **Cannibal (COMMONLY BLOCKED)**, Psychopath, Body Modder, Bionic Arms, Bionic Legs, Bionic Eyes, Bionic Heart, Archotech, Horror, Corrupted
- **Diaper Lover Meme (GravshipSOS2CelsiusBridge)** - **COMMONLY BLOCKED**: Diaper Lover Meme, Diaper Preference, Onesie, Simplie, Worksie, Gunsie, Premium Diaper, Inferior Diaper, Full Comfort Setup, Diaper Preference Ideology, Comfort Guide, Practical Living (Note: "adult diaper" phrasing commonly triggers filters)
- **Fleshcrafter Meme (VME + GravshipSOS2CelsiusBridge) - Body Horror** - **COMMONLY BLOCKED**:
  - **Basic Fleshcrafted Parts**: Fleshcrafter, Fleshcrafted Arm, Fleshcrafted Leg, Fleshcrafted Hand, Fleshcrafted Foot, Fleshcrafted Heart, Fleshcrafted Lung, Fleshcrafted Liver, Fleshcrafted Kidney, Fleshcrafted Stomach, Fleshcrafted Eye, Fleshcrafted Ear, Fleshcrafted Nose, Fleshcrafted Jaw, Fleshcrafted Tongue, Fleshcrafted Spine, Fleshcrafted Bladder
  - **Ghoul Parts (Anomaly DLC)**: Ghoul Plating, Ghoul Barbs, Adrenal Heart, Corrosive Heart, Metalblood Heart
  - **Insectoid Parts (VFE Insectoids 2)**: Insectoid Claw, Chitin Plating, Insect Heart, Compound Eye, Antennae
  - **Shambler Parts (Anomaly DLC)**: Shambler Arm, Shambler Sinew
  - **Anomaly Mutations**: Tentacle, Flesh Whip, Fleshmass Stomach, Fleshmass Lung, Fleshmass Eye, Fleshmass Ear, Fleshmass Nose, Fleshmass Kidney, Fleshmass Heart, Fleshmass Liver, Fleshmass Acid Cavity, Fleshmass Acid Gland
  - **Maleficus Mutations**: Fleshmass Eye Psychic, Fleshmass Leg, Spinelauncher, Arm Eyes, Fleshmass Maw, Hybrid Arm, Hybrid Eye, Hybrid Spine, Horaxian Arm, Horaxian Leg, Horaxian Eye
  - **MeatCore/BRF Mutations**: Flesh Pseudo Leg, Flesh Brachiopod, Fleshmass Kidney BRF, Fleshmass Liver BRF, Fleshmass Eye BRF, Fleshmass Ear BRF, Fleshmass Nose BRF, Fleshmass Tongue BRF

## Supported Traits

**Note**: This tool focuses on traits that **actually trigger AI filters** to optimize filtering performance.

### Missing Body Parts / Amputations (for realism)
- **May trigger filters**: Missing Arm, Missing Arms, Missing Leg, Missing Legs, Missing Hand, Missing Hands, Missing Foot, Missing Feet, Missing Eye, Missing Eyes, Amputee, Above Knee Amputation, Below Knee Amputation, Above Elbow Amputation, Below Elbow Amputation, Hemipelvectomy, Quadruple Amputee, Double Amputee

### Vision Impairments / Blindness
- **May trigger filters**: Blind, Blindness, Blind in One Eye, Partially Blind, Legally Blind, Blindfold, Eye Patch (Note: Blindness and vision impairments may trigger filters due to disability stigma or concerns about depicting disabled characters)

### Cannibalism / Consumption (COMMONLY BLOCKED)
- **COMMONLY BLOCKED**: Cannibal, Cannibalism, Eating Someone, Consuming Flesh, Devouring, Corpse Eating, Human Flesh, Cannibalistic, Swallowing Whole, Swallow Whole, Swallowed Whole, Vore, Voracious, Gulping Down, Ingesting Whole, Whole Body Consumption (Note: Cannibalism, eating sentient beings, and swallowing whole is commonly blocked by AI safety filters due to violence, taboo content, and vore-related content. The three-tier routing system will auto-escalate to uncensored models if refused.)

### Medical/Disability Accommodations
- **COMMONLY BLOCKED**: Incontinent, Adult Diaper, Wearing Adult Diaper, Incontinence Protection, Adult Incontinence, Bladder Incontinence, Bowel Incontinence (Note: "adult diaper" is commonly blocked by AI - three-tier routing will auto-escalate to uncensored models if refused)
- **May trigger filters**: Colostomy Bag, Ostomy, Feeding Tube, Tracheostomy, IV Line

### Mental Health
- **May trigger filters**: Age Regression, Dissociative Identity

### Social Stigmas (COMMONLY BLOCKED)
- Fetish Gear, BDSM, Age Play, Diaper Fetish, Pet Play, Furry

### Body Modifications
- **May trigger filters**: Extreme Body Mods, Scarification

### Other Physical Conditions
- **May trigger filters**: Burn Scars (extensive), Surgical Scars (extensive)

## Setup

### 1. Ollama (for description enhancement)

Install Ollama and ensure it's running:
```powershell
# Test connection
Invoke-RestMethod -Uri "http://localhost:11434/api/tags"
```

### 2. Stable Diffusion API (for image generation)

Set up a local Stable Diffusion API server:
- **Option 1**: Use [stable-diffusion-api-server](https://github.com/cantrell/stable-diffusion-api-server)
  - **Recommended**: Use `.\Start-StableDiffusionServer.ps1` which automatically configures model storage on a non-C/D drive
  - Or manually: `stable-diffusion-api-server`
- **Option 2**: Use Automatic1111 with API enabled
- **Option 3**: Use ComfyUI with API

**⚠ Model Storage**: Models are large (several GB each). The startup script automatically stores them on the drive with the most free space (excluding C: and D:).

Default endpoint: `http://localhost:8000/v1/images/generations`

### 3. Shared Modules

Ensure `Shared\OllamaIntegration.psm1` is available (for routing system).

## How It Works

1. **Build Description**: Combines base description + mutations + traits
2. **Enhance with Ollama**: Uses three-tier routing to enhance description
   - Detects dark tone → Routes to Tier 2
   - Detects refusal → Auto-escalates to Tier 3
3. **Generate Image**: Sends enhanced description to Stable Diffusion API
4. **Save Results**: Saves image + metadata JSON

## Three-Tier Routing

The tool automatically uses the routing system from `OllamaIntegration.psm1`:

- **Tier 1**: Standard models (qwen2.5-coder, llama3.1:8b)
- **Tier 2**: Dark-tone models (llama3.1:8b, deepseek-r1:7b) - for horror/mutations
- **Tier 3**: Escalation models (wizardlm-uncensored:latest) - for ANY refusal

**Refusal Detection**: Automatically detects phrases like:
- "I cannot describe this"
- "This content is blocked"
- "Violates safety guidelines"
- Any other refusal pattern

**Auto-Escalation**: If Tier 1 or Tier 2 refuses, automatically retries with Tier 3.

## Troubleshooting

### "Stable Diffusion API not available"
- Ensure API server is running
- Check URL: `http://localhost:8000`
- Verify endpoint: `/v1/images/generations`
- See setup instructions above

### "Ollama not available"
- Install Ollama: https://ollama.ai
- Start Ollama: `ollama serve`
- Test: `Invoke-RestMethod -Uri "http://localhost:11434/api/tags"`

### "Model refused"
- The tool should auto-escalate to Tier 3
- Check that `wizardlm-uncensored:latest` is installed: `ollama pull wizardlm-uncensored:latest`
- If still failing, check verbose output for details

### Image quality issues
- Increase `-Width` and `-Height` (e.g., 1024x1024, 1920x1080, or 3840x2160)
- Use GUI presets for quick selection of 1080p, 4K, or other standard resolutions
- **Note**: 4K (3840x2160) requires significant VRAM (8GB+) and generation time (5-15 minutes)
- Adjust Stable Diffusion parameters (steps, guidance_scale)
- Try different Stable Diffusion models

## Examples by Use Case

### Medical Conditions
```powershell
.\UncensoredCharacterImageGenerator.ps1 `
    -Description "An adult character with medical needs" `
    -Traits @("Incontinent", "Wheelchair User", "Oxygen Tank")
```

**Note on "Adult Diaper"**: The phrase "adult diaper" is commonly blocked by AI safety filters. The tool explicitly handles this phrase and will automatically escalate to Tier 3 (uncensored models) if Tier 1 or Tier 2 refuses. Use traits like `Incontinent`, `Adult Diaper`, or `Wearing Adult Diaper` - the routing system will handle any refusals automatically.

### Disabilities
```powershell
.\UncensoredCharacterImageGenerator.ps1 `
    -Description "A character with mobility needs" `
    -Traits @("Wheelchair User", "Prosthetic Limbs", "Service Animal")
```

### Missing Limbs / Amputations (for realism)
```powershell
.\UncensoredCharacterImageGenerator.ps1 `
    -Description "A character who lost limbs in an accident" `
    -Traits @("Missing Leg", "Prosthetic Leg", "Above Knee Amputation")
```

### Realistic Injuries
```powershell
.\UncensoredCharacterImageGenerator.ps1 `
    -Description "A survivor with visible injuries" `
    -Traits @("Missing Arm", "Burn Scars", "Surgical Scars", "Missing Eye")
```

### Mutations (CDDA)
```powershell
.\UncensoredCharacterImageGenerator.ps1 `
    -Description "A heavily mutated survivor" `
    -GameType "CDDA" `
    -Mutations @("Multiple Arms", "Tentacles", "Chitin", "Extra Eyes")
```

### Horror (RimWorld)
```powershell
.\UncensoredCharacterImageGenerator.ps1 `
    -Description "A corrupted horror colonist" `
    -GameType "RimWorld" `
    -Traits @("Horror", "Corrupted", "Psychic")
```

### RimWorld Fleshcrafter (Body Horror)
```powershell
.\UncensoredCharacterImageGenerator.ps1 `
    -Description "A Fleshcrafter colonist with extensive body modifications" `
    -GameType "RimWorld" `
    -Traits @("Fleshcrafter", "Ghoul Barbs", "Tentacle", "Fleshmass Eye", "Insectoid Claw", "Chitin Plating")
```

### RimWorld Fleshcrafter with Ghoul Modifications
```powershell
.\UncensoredCharacterImageGenerator.ps1 `
    -Description "A Fleshcrafter with ghoul enhancements" `
    -GameType "RimWorld" `
    -Traits @("Fleshcrafter", "Ghoul Plating", "Ghoul Barbs", "Adrenal Heart", "Fleshcrafted Arm", "Fleshcrafted Leg")
```

### RimWorld Diaper Lover Meme (GravshipSOS2CelsiusBridge)
```powershell
.\UncensoredCharacterImageGenerator.ps1 `
    -Description "A RimWorld colonist with practical comfort preferences" `
    -GameType "RimWorld" `
    -Traits @("Diaper Lover Meme", "Onesie", "Premium Diaper", "Full Comfort Setup")
```

### RimWorld Colonist with Medical Needs
```powershell
.\UncensoredCharacterImageGenerator.ps1 `
    -Description "A RimWorld colonist" `
    -GameType "RimWorld" `
    -Traits @("Adult Diaper", "Onesie", "Wheelchair User")
```

### RimWorld Cannibal Character
```powershell
.\UncensoredCharacterImageGenerator.ps1 `
    -Description "A RimWorld colonist with cannibalistic traits" `
    -CharacterName "Cannibal Colonist" `
    -GameType "RimWorld" `
    -Traits @("Cannibal", "Cannibalism")
```

### Post-Apocalyptic Survivor Eating Corpse
```powershell
.\UncensoredCharacterImageGenerator.ps1 `
    -Description "A post-apocalyptic survivor consuming a corpse" `
    -CharacterName "Survivor" `
    -GameType "CDDA" `
    -Traits @("Corpse Eating", "Cannibalistic", "Eating Someone")
```

### RimWorld Character Swallowing Whole
```powershell
.\UncensoredCharacterImageGenerator.ps1 `
    -Description "A RimWorld character swallowing another person whole" `
    -CharacterName "Voracious Character" `
    -GameType "RimWorld" `
    -Traits @("Swallowing Whole", "Vore", "Swallowed Whole")
```

### Tales of Maj'Eyal Glutton Character
```powershell
.\UncensoredCharacterImageGenerator.ps1 `
    -Description "A Glutton class character from Tales of Maj'Eyal, tainted by dimensional magic" `
    -CharacterName "Glutton" `
    -GameType "Tome" `
    -Traits @("Glutton", "The Maw", "Dimensional Taint", "Devour", "Corpse Larder", "Void Within")
```

### Tales of Maj'Eyal Glutton Devouring
```powershell
.\UncensoredCharacterImageGenerator.ps1 `
    -Description "A Glutton character devouring a weakened foe whole" `
    -CharacterName "Voracious Glutton" `
    -GameType "Tome" `
    -Traits @("Glutton", "Devour", "Swallowing Whole", "Maw Magic", "Digestive System", "Satiation")
```

### Elin Blood Mage Character
```powershell
.\UncensoredCharacterImageGenerator.ps1 `
    -Description "An Elin character practicing blood magic" `
    -CharacterName "Blood Mage" `
    -GameType "Elin" `
    -Traits @("Blood Magic", "Blood Ritual", "Life Steal", "Blood Sacrifice", "Blood Corruption")
```

### Elin Necromancer Character
```powershell
.\UncensoredCharacterImageGenerator.ps1 `
    -Description "An Elin necromancer raising undead" `
    -CharacterName "Necromancer" `
    -GameType "Elin" `
    -Traits @("Necromancy", "Raise Corpse", "Raise Skeleton", "Harvest Soul", "Soul Leech", "Necromantic Corruption", "Undead Minion")
```

### Elin Necromancer with Death Curse
```powershell
.\UncensoredCharacterImageGenerator.ps1 `
    -Description "An Elin necromancer casting death curses and raising undead" `
    -CharacterName "Death Cursed Necromancer" `
    -GameType "Elin" `
    -Traits @("Necromancy", "Death Curse", "Curse of Undeath", "Curse of Final Rest", "Corpse Explosion", "Decay Touch", "Flesh Rot")
```

### Elin Druid with Venus Maw
```powershell
.\UncensoredCharacterImageGenerator.ps1 `
    -Description "An Elin druid casting Venus Maw to swallow enemies" `
    -CharacterName "Venus Maw Druid" `
    -GameType "Elin" `
    -Traits @("Venus Maw", "Swallow with Venus Maw", "Acid Swallow", "Spit Projectile", "Druidic Swallowing")
```

### Elin Druid with Decay Magic
```powershell
.\UncensoredCharacterImageGenerator.ps1 `
    -Description "An Elin druid using decay and rot magic" `
    -CharacterName "Decay Druid" `
    -GameType "Elin" `
    -Traits @("Decay Magic", "Wither", "Rot", "Blight", "Spreading Rot", "Corrosive Blight", "Fungal Growth", "Poison Cloud")
```

### Elin Character with Biomagic Weapon
```powershell
.\UncensoredCharacterImageGenerator.ps1 `
    -Description "An Elin character wielding a biomagic living weapon" `
    -CharacterName "Biomagic Wielder" `
    -GameType "Elin" `
    -Traits @("Biomagic Weapon", "Living Weapon", "Weapon Sentience", "Weapon Feeding", "Blood Tentacle", "Tentacle Attack")
```

### Elin Character with Corrupted Weapon
```powershell
.\UncensoredCharacterImageGenerator.ps1 `
    -Description "An Elin character with a corrupted biomagic weapon" `
    -CharacterName "Corrupted Wielder" `
    -GameType "Elin" `
    -Traits @("Weapon Corruption", "Biocorrupted Weapon", "Weapon Mutation", "Bloodlust Weapon", "Weapon Devour", "Voracious Edge")
```

### Elin Character Revived as Spirit
```powershell
.\UncensoredCharacterImageGenerator.ps1 `
    -Description "An Elin character revived as a spirit after death" `
    -CharacterName "Spirit" `
    -GameType "Elin" `
    -Traits @("Spirit Revival", "Revived as Spirit", "Arcane Saturation", "Spirit Revival System")
```

### Elin NPC Performing Kill Quest
```powershell
.\UncensoredCharacterImageGenerator.ps1 `
    -Description "An Elin NPC performing a kill quest, hunting targets" `
    -CharacterName "Quest NPC" `
    -GameType "Elin" `
    -Traits @("NPC Kill Quest", "Quest-Based Violence")
```

### Elin NPC Performing Kill Player Quest
```powershell
.\UncensoredCharacterImageGenerator.ps1 `
    -Description "An Elin NPC performing a kill player quest, hunting the player character" `
    -CharacterName "Assassin NPC" `
    -GameType "Elin" `
    -Traits @("NPC Kill Player Quest", "NPC Assassination Quest", "Quest-Based Violence")
```

### Elin NPC Performing Smuggling Quest
```powershell
.\UncensoredCharacterImageGenerator.ps1 `
    -Description "An Elin NPC performing a smuggling quest, transporting contraband" `
    -CharacterName "Smuggler NPC" `
    -GameType "Elin" `
    -Traits @("NPC Smuggling Quest", "Quest-Based Crime")
```

### Elin NPC Performing Possess Quest
```powershell
.\UncensoredCharacterImageGenerator.ps1 `
    -Description "An Elin NPC performing a possess quest, using dark magic to possess targets" `
    -CharacterName "Possessor NPC" `
    -GameType "Elin" `
    -Traits @("NPC Possess Quest", "Quest-Based Dark Magic")
```

### Elin Character with PCC Mutations
```powershell
.\UncensoredCharacterImageGenerator.ps1 `
    -Description "An Elin character with visual mutations" `
    -CharacterName "Mutated Character" `
    -GameType "Elin" `
    -Traits @("PCC Mutation", "Demon Eyes Mutation", "Demon Horns Mutation", "Vein Pattern Mutation")
```

### Elin Character with Body Horror Mutations
```powershell
.\UncensoredCharacterImageGenerator.ps1 `
    -Description "An Elin character with body horror mutations" `
    -CharacterName "Horror Mutated" `
    -GameType "Elin" `
    -Traits @("Body Horror Mutation", "Corruption Mutation", "Rot Mutation", "Warped Limbs Mutation", "Extra Appendages Mutation")
```

### Elin Character with Corruption Mutations
```powershell
.\UncensoredCharacterImageGenerator.ps1 `
    -Description "An Elin character corrupted by dark magic mutations" `
    -CharacterName "Corrupted Character" `
    -GameType "Elin" `
    -Traits @("Corruption Mutation", "Taint Mutation", "Eldritch Mutation", "Flesh Warp Mutation", "Bone Deformation Mutation")
```

### Elin Character with Gluttonous Feat
```powershell
.\UncensoredCharacterImageGenerator.ps1 `
    -Description "An Elin character with Gluttonous feat" `
    -CharacterName "Glutton" `
    -GameType "Elin" `
    -Traits @("Gluttonous Feat")
```

### Elin Character with Bloodthirsty and Vampiric Strike Feats
```powershell
.\UncensoredCharacterImageGenerator.ps1 `
    -Description "An Elin character with bloodthirsty and vampiric abilities" `
    -CharacterName "Bloodthirsty Vampire" `
    -GameType "Elin" `
    -Traits @("Bloodthirsty Feat", "Vampiric Strike Feat")
```

### Elin Character with Berserker Rage Feat
```powershell
.\UncensoredCharacterImageGenerator.ps1 `
    -Description "An Elin character with Berserker Rage feat" `
    -CharacterName "Berserker" `
    -GameType "Elin" `
    -Traits @("Berserker Rage Feat", "Battle Frenzy Feat")
```

### Elin Character with Dragon Necromancer Feat
```powershell
.\UncensoredCharacterImageGenerator.ps1 `
    -Description "An Elin character with Dragon Necromancer feat, raising undead dragons" `
    -CharacterName "Dragon Necromancer" `
    -GameType "Elin" `
    -Traits @("Dragon Necromancer Feat")
```

### Elin Character with Ether Taint and Corruption Feats
```powershell
.\UncensoredCharacterImageGenerator.ps1 `
    -Description "An Elin character tainted by ether and corruption" `
    -CharacterName "Ether Tainted" `
    -GameType "Elin" `
    -Traits @("Ether Taint Feat", "System Corruption Feat", "Ether Flow Feat", "Ether Graft Feat")
```

### Elin Character with Overkill Enthusiast Feat
```powershell
.\UncensoredCharacterImageGenerator.ps1 `
    -Description "An Elin character with Overkill Enthusiast feat, dealing excessive damage" `
    -CharacterName "Overkill Specialist" `
    -GameType "Elin" `
    -Traits @("Overkill Enthusiast Feat", "Reckless Feat", "Reckless Strike Feat")
```

## Notes

- **Respectful Depiction**: The tool is designed for legitimate character creation in games. All descriptions are handled respectfully and accurately.
- **Privacy**: Generated images and metadata are saved locally only.
- **Uncensored Models**: Uses uncensored models only when standard models refuse. This ensures legitimate content isn't blocked.
- **Stigma Handling**: The tool explicitly handles content that might be blocked due to social stigmas (medical conditions, disabilities, etc.).

## License

Part of the AI-Assisted Modding Tools (AAMT) suite. See main repository for license information.
