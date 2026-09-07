# UncensoredCharacterImageGenerator.ps1
# Generates detailed character images from descriptions, handling ANY content that might be blocked
# Supports: RimWorld, CDDA, Caves of Qud, and any game with characters that might trigger safety filters
# 
# Why "Uncensored"? This tool handles content blocked for ANY reason:
# - Body horror, mutations, dark themes (horror games)
# - Medical conditions, disabilities, accommodations (adults in diapers, wheelchairs, etc.)
# - Social stigmas (age regression, fetish content, etc.)
# - Any legitimate character description that standard AI refuses
#
# Uses three-tier routing system: Standard → Dark-tone → Escalation (auto-detects refusals)

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$Description,
    
    [Parameter(Mandatory=$false)]
    [string]$CharacterName = "Character",
    
    [Parameter(Mandatory=$false)]
    [string]$GameType = "Generic",  # RimWorld, CDDA, Qud, Generic
    
    [Parameter(Mandatory=$false)]
    [string[]]$Mutations = @(),  # List of mutations that affect appearance
    
    [Parameter(Mandatory=$false)]
    [string[]]$Traits = @(),  # Additional traits (medical conditions, disabilities, etc.)
    
    [Parameter(Mandatory=$false)]
    [int]$Width = 1024,
    
    [Parameter(Mandatory=$false)]
    [int]$Height = 1024,
    
    [Parameter(Mandatory=$false)]
    [int]$Steps = 50,

    [Parameter(Mandatory=$false)]
    [double]$GuidanceScale = 7.5,

    [Parameter(Mandatory=$false)]
    [string]$OutputPath = "",
    
    [Parameter(Mandatory=$false)]
    [string]$OllamaUrl = "http://localhost:11434",
    
    [Parameter(Mandatory=$false)]
    [string]$StableDiffusionUrl = "http://localhost:1338",  # Stable Diffusion API endpoint (SD3.5 Server)
    
    [Parameter(Mandatory=$false)]
    [switch]$AIEnhancement,  # Analyze generated image with a vision model
    
    [Parameter(Mandatory=$false)]
    [switch]$RegenerateImproved,  # Regenerate image using improvement suggestions (requires -AIEnhancement)
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipEnhancement,  # Skip Ollama enhancement (use raw description)
    
    [Parameter(Mandatory=$false)]
    [switch]$NoAutoStartServer,  # (Deprecated/no-op) Kept for backward compatibility; auto-start is OFF by default

    [Parameter(Mandatory=$false)]
    [switch]$AllowStartServer,  # Opt-in ONLY: allow spawning an SD server if none is running (single-server policy)

    [Parameter(Mandatory=$false)]
    [switch]$NoOpen  # Do not auto-open the generated image / Explorer (for unattended/overnight runs)
)

$ErrorActionPreference = "Stop"
$script:IsVerbose = $PSBoundParameters.ContainsKey('Verbose')
# Single-server policy: NEVER auto-start a second SD server unless the caller
# explicitly opts in with -AllowStartServer. This prevents overnight batches
# from spinning up duplicate GPU servers that contend for VRAM.
$script:AllowStartServer = $PSBoundParameters.ContainsKey('AllowStartServer')
# Unattended-friendly: suppress GUI pop-ups unless a console is actually present.
$script:NoOpen = $PSBoundParameters.ContainsKey('NoOpen') -or (-not [Environment]::UserInteractive)
# Generous FINITE SD timeout so slow-but-complete generations aren't discarded.
$script:SDHttpTimeoutSec = 3600
if ($env:AAMT_SD_HTTP_TIMEOUT_SEC) {
    $parsed = 0
    if ([int]::TryParse($env:AAMT_SD_HTTP_TIMEOUT_SEC, [ref]$parsed) -and $parsed -gt 0) { $script:SDHttpTimeoutSec = $parsed }
}
$script:SDOutputsDir = "E:\tools\sd3.5\sd3.5\outputs"

# Normalize Mutations and Traits - handle both arrays and comma-separated strings
if ($Mutations -and $Mutations.Count -gt 0) {
    if ($Mutations.Count -eq 1 -and $Mutations[0] -match ',') {
        # Single string with commas - split it
        $Mutations = $Mutations[0] -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ }
    }
} else {
    $Mutations = @()
}

if ($Traits -and $Traits.Count -gt 0) {
    if ($Traits.Count -eq 1 -and $Traits[0] -match ',') {
        # Single string with commas - split it
        $Traits = $Traits[0] -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ }
    }
} else {
    $Traits = @()
}

# Import shared modules
$sharedPath = Join-Path $PSScriptRoot "Shared"
$ollamaModule = Join-Path $sharedPath "OllamaIntegration.psm1"
if (Test-Path $ollamaModule) {
    Import-Module $ollamaModule -Force
} else {
    Write-Host "[WARN] OllamaIntegration module not found at: $ollamaModule" -ForegroundColor Yellow
    Write-Host "  Some features may be limited. Continuing anyway..." -ForegroundColor Gray
}

# ============================================================
# MUTATION & TRAIT PROCESSING
# ============================================================

function Get-MutationVisualEffects {
    <#
    .SYNOPSIS
    Converts mutation names into visual description elements.
    #>
    param([string[]]$Mutations)
    
    $visualEffects = @()
    $mutationMap = @{
        # CDDA Mutations
        "Multiple Arms" = "has multiple pairs of arms extending from shoulders"
        "Multiple Legs" = "has multiple pairs of legs, spider-like or centipede-like"
        "Hooves" = "has hooved feet instead of human feet"
        "Talons" = "has sharp talons on hands and feet"
        "Claws" = "has sharp claws extending from fingers"
        "Fangs" = "has prominent fangs visible when mouth opens"
        "Antennae" = "has antennae protruding from head"
        "Wings" = "has wings extending from back or shoulders"
        "Tail" = "has a tail extending from base of spine"
        "Horns" = "has horns protruding from head"
        "Scales" = "has scaly skin covering body"
        "Fur" = "has fur covering body"
        "Feathers" = "has feathers covering body or parts of body"
        "Chitin" = "has chitinous exoskeleton covering body"
        "Tentacles" = "has tentacles extending from body"
        "Extra Head" = "has an additional head"
        "Extra Eyes" = "has multiple eyes, some in unusual locations"
        "Webbed" = "has webbed fingers and toes"
        "Gills" = "has gills visible on neck or sides"
        "Amphibian" = "has amphibian-like features: moist skin, webbed digits"
        "Beak" = "has a beak instead of normal mouth"
        "Compound Eyes" = "has compound insect-like eyes"
        "Mandibles" = "has mandibles extending from face"
        "Carapace" = "has hard carapace covering parts of body"
        "Spinnerets" = "has spinnerets for web production"
        "Stinger" = "has a stinger or barbed tail"
        "Prehensile Tail" = "has a prehensile tail that can grasp objects"
        "Paws" = "has paw-like hands and feet"
        "Elongated Limbs" = "has unusually long limbs"
        "Short Limbs" = "has unusually short limbs"
        "Thick Hide" = "has thick, leathery hide"
        "Translucent Skin" = "has translucent or semi-transparent skin"
        "Glowing" = "has bioluminescent features that glow"
        "Spines" = "has sharp spines protruding from body"
        "Quills" = "has quills covering parts of body"
        
        # Caves of Qud Mutations
        "Chimera" = "has mismatched body parts from different creatures fused together"
        "Amphibious" = "has amphibian features: webbed digits, gills"
        "Regeneration" = "shows signs of rapid healing, scars that fade quickly"
        "Photosynthetic Skin" = "has green-tinted skin that can photosynthesize"
        "Two-Headed" = "has two heads"
        "Extra Limbs" = "has additional limbs beyond normal humanoid form"
        
        # Caves of Qud - Broodmother Mutation (Arendeth_Broodmother)
        "Broodmother" = "is an arthropod matriarch with a pulsating chitinous broodling sack permanently fused to their back, can birth arthropod minions"
        "Broodling Sack" = "has a pulsating chitinous sack permanently fused to their back, swelling with unborn broodlings, flexible yet tough exterior, organic birthing organ"
        "Gestating" = "is currently gestating, the broodling sack is bulging and swollen with developing broodlings, reduced mobility and carry capacity, defensive shell hardening"
        "Arthropod Matriarch" = "has transformed into an arthropod matriarch, appearance reflects insect/arachnid characteristics, chitinous features, mandibles, compound eyes"
        "Broodling Drones" = "has small arthropod minions (drones with soft chitinous plates clicking mandibles, mites with iridescent wings, grubs) following them"
        "Broodling Soldiers" = "has medium arthropod minions (soldiers, skimmers, weavers) following them"
        "Broodling Leapers" = "has advanced arthropod minions (leapers, gliders, stingers) following them"
        "Broodling Hunters" = "has elite arthropod minions (hunters, raiders, juggernauts) following them"
        "Broodling Ravagers" = "has powerful arthropod minions (ravagers, strikers, deathstrikes) following them"
        "Broodling Warmasters" = "has legendary arthropod minions (warmasters, destroyers) following them"
        "Hero Broodlings" = "has hero variant arthropod minions with enhanced stats and unique colorations, superior to standard broodlings"
        "Insect Broodlings" = "has insect-type minions (ants, beetles, moths, dragonflies) with chitinous exoskeletons"
        "Arachnid Broodlings" = "has arachnid-type minions (spiders, scorpions) that can spin webs, requires web immunity"
        "Worm Broodlings" = "has worm-type minions (burrowers, tanks) with segmented bodies"
        "Swarm Leader" = "leads a swarm of arthropod minions, surrounded by loyal broodlings, commanding presence"
        "Biomod Sack" = "has a biomod-enhanced broodling sack with biometal enhancements visible on the chitinous surface"
        "Chitinous Sack" = "has a chitinous broodling sack with hard exoskeletal plates visible on the surface"
        
        # Caves of Qud - WM Extended Mutations (Winged_Monotone)
        # Physical Mutations (filter-triggering only)
        "Serpentine Form" = "has a serpentine form, snake-like body with elongated torso and tail"
        "Ovipositor" = "has an ovipositor, an egg-laying organ extending from the body"
        "Gelatinous Form" = "has a gelatinous form, body is semi-transparent and slimy, jelly-like consistency"
        "Gelatinous Form Slime" = "has a gelatinous slime form, body is translucent and slimy, can flow and reshape"
        "Gelatinous Form Acid" = "has a gelatinous acid form, body is acidic and corrosive, translucent with acidic properties"
        "Gelatinous Form Poison" = "has a gelatinous poison form, body is toxic and venomous, translucent with poisonous properties"
        "Fruiting Bodies" = "has fruiting bodies growing from body, mushroom or plant-like growths"
        "Root-Growing" = "has roots growing from body, plant-like root systems extending from limbs or torso"
        "Thorny" = "has thorns covering body, sharp plant-like thorns protruding from skin"
        "Acidic Blood" = "has acidic blood, corrosive blood that may cause visible damage to surroundings"
        "Barkflesh" = "has barkflesh, tree-like bark covering body, woody appearance"
        "Explosive Burs" = "has explosive burs, seed pods or burrs that can explode, plant-like growths"
        
        # Mental Mutations (filter-triggering only)
        "Psychophagia" = "has psychophagia, can consume minds, may have unsettling mental presence"
        "Combustion Blast" = "has combustion blast abilities, can create explosive blasts, may have visible fire or explosion effects"
        
        # Metaphysical Mutations
        "Nine-Lives Paradox" = "has nine-lives paradox, can cheat death multiple times, may have paradoxical or death-defying appearance"
        "Nine Lives Paradox" = "has nine-lives paradox, can cheat death multiple times, may have paradoxical or death-defying appearance"
        "Incorporeal Form" = "has incorporeal form, can become intangible, appears ghostly or ethereal, partially transparent"
        
        # Caves of Qud - Graven's Mutation Mod (Gravenwitch) / Friendly Graven's Mutation Mod
        # Note: All mutations from this mod are rarely blocked and have been removed to optimize filtering
        
        # Caves of Qud - More Mental Mutations (pyatr)
        "Dynakinesis" = "has dynakinesis abilities, can crush targets from inside, internal damage based on target's toughness, may have visible kinetic effects"
        "Telekinesis" = "has telekinesis abilities, can throw or place creatures and weapons with mental force, may have visible telekinetic effects"
        "Chemical Addiction" = "has chemical addiction defect, requires alcohol or intoxicating items daily, may show signs of dependency or withdrawal"
        
        # Caves of Qud - Scary Monsters Mutation (CrypticCritter)
        "Scary Monsters" = "has Scary Monsters mutation, can transform into a dinosaur and back, dinosaur form has serrated teeth, sharp talons, sharp claws, and a tail"
        "Dinosaur Form" = "is transformed into dinosaur form, cannot speak, has dinosaur body with tail, serrated teeth, sharp talons on feet, sharp claws on hands"
        "Dinosaur Body" = "has dinosaur body with tail, reptilian dinosaur appearance"
        "Serrated Teeth" = "has serrated teeth, sharp dinosaur-like teeth for biting"
        "Dinosaur Talons" = "has sharp talons on feet, dinosaur-like claws for feet"
        "Dinosaur Claws" = "has sharp claws on hands, dinosaur-like claws for hands"
        "Dinosaur Tail" = "has a dinosaur tail extending from base of spine"
        "Jump Attack" = "can perform jump attack, can hit flying enemies with leaping attacks"
        "Leap" = "can perform long jump, powerful leaping ability"
        "Tail Sweep" = "can perform tail sweep, knocks enemies away with tail attack"
        "Dinosaur Bite" = "can bite with serrated teeth, powerful bite attack"
        "Dinosaur Roar" = "can roar, makes enemies run away briefly with intimidating roar"
        
        # Caves of Qud - Conjoined Mutation (John Snail)
        "Conjoined" = "has Conjoined mutation, has creatures conjoined to body, visible signs of conjoined creatures attached to body"
        "Conjoined Creature" = "has conjoined creature, another creature is conjoined to the body, visible signs of attached creature"
        "Conjoined Creatures" = "has multiple conjoined creatures, multiple beings are conjoined to the body, visible signs of multiple attached creatures"
        "Conjoinment Body Part" = "has conjoinment body part, body part that connects to conjoined creature, visible signs of conjoinment attachment"
        "Conjoinment" = "has conjoinment, creature is conjoined to body through conjoinment body part, visible signs of creature attachment"
        "Conjoined Attachment" = "has conjoined attachment, creature is physically attached to body, visible signs of physical connection"
        "Conjoined Dismemberment" = "has conjoined dismemberment, conjoined creature can be dismembered causing instant death, visible signs of dismemberment risk"
        "Conjoined Regeneration" = "can regenerate conjoined creatures, can regrow conjoinment body part to revive dead conjoined creature, visible signs of regeneration"
        "Conjoined Pull" = "can pull conjoined creatures back, conjoined creatures over a tile away are pulled back, visible signs of connection or pulling"
        "Conjoined Damage" = "conjoined creatures take damage when connection fails, visible signs of connection strain or damage"
        "Conjoined Interaction" = "can interact with conjoined creatures, can view character sheet and skills of conjoined creatures, visible signs of conjoined creature control"
        "Conjoined Body Horror" = "has conjoined body horror, creatures physically attached to body, visible signs of body horror or physical fusion"
        "Conjoined Fusion" = "has conjoined fusion, creatures are fused to body, visible signs of physical fusion or attachment"
        "Conjoined Symbiosis" = "has conjoined symbiosis, creatures are symbiotically attached to body, visible signs of symbiotic connection"
        
        # Caves of Qud - Improved Mutations Mod (Enhanced Mutations)
        # Improved Multiple Arms
        "Multiple Arms Enhanced" = "has enhanced multiple arms mutation, can spend more mutation points for more pairs of arms, each extra arm has missile weapon slot, visible signs of multiple pairs of arms with weapon capabilities"
        "Extra Arm Pairs" = "has multiple pairs of arms, can have many pairs of arms through mutation points, visible signs of multiple arm pairs"
        "Arm Missile Slots" = "has missile weapon slots on extra arms, each extra arm can equip missile weapons, visible signs of multiple weapon-equipped arms"
        
        # Improved Multiple Legs
        "Multiple Legs Enhanced" = "has enhanced multiple legs mutation, has second body slot named torso with rear feet attached, has own worn on back slot, visible signs of multiple leg pairs with separate torso"
        "Second Torso" = "has second torso body slot, rear feet are attached to second torso, visible signs of dual torso structure"
        "Rear Feet" = "has rear feet attached to second torso, multiple pairs of legs with separate body structure, visible signs of rear leg pairs"
        "Dual Body Structure" = "has dual body structure from multiple legs, two separate torsos with legs, visible signs of multiple body segments"
        
        # Improved Quills (when paired with Multiple Legs)
        "Quills Enhanced" = "has enhanced quills mutation, when paired with multiple legs quills are on both bodies, visible signs of quills covering multiple body segments"
        "Dual Body Quills" = "has quills on both bodies, quills cover both torsos when combined with multiple legs, visible signs of quills on multiple body segments"
        
        # Improved Carapace (when paired with Multiple Legs)
        "Carapace Enhanced" = "has enhanced carapace mutation, when paired with multiple legs has carapaces on both bodies, visible signs of hard carapace covering multiple body segments"
        "Dual Body Carapace" = "has carapace on both bodies, hard carapace covers both torsos when combined with multiple legs, visible signs of carapace on multiple body segments"
        
        # Improved Thick Fur
        "Thick Fur Enhanced" = "has enhanced thick fur mutation, only gives cold resistance but gives 5 for each level, visible signs of thick fur covering body"
        "Thick Fur Cold Resistance" = "has thick fur providing cold resistance, 5 cold resistance per level, visible signs of dense fur insulation"
        
        # Improved Two-Headed
        "Two-Headed Enhanced" = "has enhanced two-headed mutation, can spend more mutation points to get more heads at character select, visible signs of multiple heads"
        "Multiple Heads" = "has multiple heads, can have many heads through mutation points, visible signs of multiple heads on body"
        "Extra Heads" = "has extra heads beyond two, additional heads from mutation points, visible signs of multiple head growth"
        
        # Improved Wings (when paired with Multiple Legs)
        "Wings Enhanced" = "has enhanced wings mutation, when paired with multiple legs wings are added to both backs, visible signs of wings on multiple body segments"
        "Dual Back Wings" = "has wings on both backs, wings extend from both torsos when combined with multiple legs, visible signs of multiple wing pairs"
        
        # Improved Horns
        "Horns Enhanced" = "has enhanced horns mutation, adds horns to all heads, visible signs of horns on every head"
        "Horns on All Heads" = "has horns on all heads, every head has horns protruding, visible signs of horns on multiple heads"
        
        # Improved Burrowing Claws
        "Burrowing Claws Enhanced" = "has enhanced burrowing claws mutation, adds claws to all hands slots, visible signs of claws on all hands"
        "Claws on All Hands" = "has claws on all hands, every hand has burrowing claws, visible signs of claws extending from all hands"
        
        # Improved Spinnerets
        "Spinnerets Enhanced" = "has enhanced spinnerets mutation, can shoot arc of webbing behind, higher levels mean more webbing shot further away, visible signs of web production and shooting"
        "Web Arc Shooting" = "can shoot arc of webbing behind, can launch webbing in arc pattern, visible signs of web shooting ability"
        "Enhanced Web Production" = "has enhanced web production, can produce more webbing at higher levels, visible signs of increased web generation"
        
        # Improved Night Vision
        "Night Vision Enhanced" = "has enhanced night vision mutation, can put mutation points to see further away, visible signs of enhanced dark vision"
        "Extended Night Vision" = "has extended night vision range, can see much further in darkness with mutation points, visible signs of enhanced dark vision radius"
        
        # Improved Beak
        "Beak Enhanced" = "has enhanced beak mutation, adds beak to all face slots, visible signs of beak on every face"
        "Beak on All Faces" = "has beak on all faces, every face has a beak, visible signs of beak on multiple faces"
        
        # Improved Hooks for Feet
        "Hooks for Feet Enhanced" = "has enhanced hooks for feet mutation, adds hooks to all feet slots, visible signs of hooks on all feet"
        "Hooks on All Feet" = "has hooks on all feet, every foot has hooks, visible signs of hooks on multiple feet"
        
        # Improved Flaming/Freezing Ray
        "Flaming Ray Enhanced" = "has enhanced flaming ray mutation, applies to all body parts in question, can shoot multiple rays in multiple directions at once, visible signs of multiple flame rays"
        "Freezing Ray Enhanced" = "has enhanced freezing ray mutation, applies to all body parts in question, can shoot multiple rays in multiple directions at once, visible signs of multiple ice rays"
        "Multiple Ray Shooting" = "can shoot multiple rays in multiple directions, can fire rays from multiple body parts simultaneously, visible signs of multi-directional ray attacks"
        
        # New Mutations - Hydra Heads
        "Hydra Heads" = "has Hydra Heads mutation, heads are like those of nine-headed hydra from Greek mythology, starts with two heads, visible signs of hydra-like multiple heads"
        "Hydra Head Regeneration" = "has hydra head regeneration, heads are easier to cut off and double up when they grow back, visible signs of head regeneration or regrowth"
        "Head Dismemberment" = "has head dismemberment risk, heads can be cut off, visible signs of head vulnerability to dismemberment"
        "Head Regrowth" = "can regrow heads, heads grow back and double up, visible signs of head regrowth or new head growth"
        "Cauterized Head Wounds" = "being set on fire with head missing cauterizes wounds, fire prevents head regrowth, visible signs of cauterized head stumps"
        "Head Bleeding" = "can bleed to death while waiting for head to grow back, visible signs of bleeding from head wounds"
        "No Heads Survival" = "cannot survive without any heads left, death if all heads are removed, visible signs of critical head dependency"
        "Multiple Head Mental Resistance" = "extra heads allow shaking off mental status effects, each head re-rolls chance but lower individually than Two-Headed, visible signs of mental resistance from multiple heads"
        "Instant Head Regeneration" = "heads grow back instantaneously at level 10, new heads regenerate immediately, visible signs of rapid head regeneration"
        "Thermodynamics Violation" = "helps violate first law of thermodynamics, head regeneration creates matter, visible signs of impossible regeneration"
        
        # New Mutations - Scales
        "Scales Mutation" = "has Scales mutation, body covered in reptilian scales that protect from heat, visible signs of reptilian scales covering body"
        "Reptilian Scales" = "has reptilian scales covering body, scales protect from heat like Thick Fur protects from cold, visible signs of scale-covered skin"
        "Heat Resistance Scales" = "has heat resistance from scales, 5 heat resistance per level like improved Thick Fur, visible signs of heat-resistant scales"
        "Reptile Reputation" = "improves reputation with unshelled reptiles by 100 points, visible signs of reptilian affinity"
        
        # New Mutations - Snake Tail
        "Snake Tail" = "has Snake Tail mutation, 6 mutation point defect that replaces legs with snake-like tail, visible signs of snake tail instead of legs"
        "Snake Tail Defect" = "has snake tail defect, legs replaced with snake tail, cuts movement speed in half, visible signs of serpentine lower body"
        "Constrict Attack" = "can wrap tail around enemies to constrict them, snake tail allows constriction attacks, visible signs of tail constriction ability"
        "Natural Swimmer" = "is naturally better swimmer with snake tail, tail improves swimming ability, visible signs of enhanced swimming capability"
        "Snake Tail Reptile Reputation" = "improves reputation with unshelled reptiles by 200 points, visible signs of strong reptilian affinity"
        "Legless Snake Tail" = "has no legs, replaced with snake tail, visible signs of legless serpentine lower body"
        
        # New Mutations - Animal Legs
        "Animal Legs" = "has Animal Legs mutation, addition from Enhanced Edition, increases quickness at cost of not allowing foot equipment, visible signs of animal-like legs"
        "Animal Legs Quickness" = "has increased quickness from animal legs, faster movement from animal leg structure, visible signs of enhanced speed"
        "No Foot Equipment" = "cannot equip anything on feet due to animal legs, feet are un-equippable, visible signs of animal feet that cannot wear equipment"
        
        # New Mutations - Muzzle
        "Muzzle" = "has Muzzle mutation, addition from Enhanced Edition, makes face slots un-equippable but allows attacks, visible signs of muzzle on face"
        "Muzzle Face" = "has muzzle instead of normal face, face slots are un-equippable, visible signs of animal-like muzzle"
        "Muzzle Attacks" = "can make attacks with muzzle, muzzle allows bite or attack actions, visible signs of attack-capable muzzle"
        
        # New Mutations - Fluffy Tail
        "Fluffy Tail" = "has Fluffy Tail mutation, gives useless tail slot and greatly reduces chances of being knocked prone, visible signs of fluffy tail"
        "Fluffy Tail Slot" = "has fluffy tail with tail slot, tail provides equipment slot but is mostly useless, visible signs of fluffy tail"
        "Prone Resistance" = "has greatly reduced chance of being knocked prone from fluffy tail, tail helps maintain balance, visible signs of stability from tail"
        
        # New Mutations - Poisonous Fangs
        "Poisonous Fangs" = "has Poisonous Fangs mutation, has fangs that can poison enemies, visible signs of poisonous fangs"
        "Poison Fangs" = "has poison fangs, fangs can inject poison into enemies, visible signs of venomous fangs"
        "Fang Poison Attack" = "can poison enemies with fangs, fang attacks apply poison, visible signs of poison-delivering fangs"
        
        # New Mutations - Armless
        "Armless" = "has Armless mutation, 3-point defect that removes all arms, visible signs of no arms"
        "Armless Defect" = "has armless defect, all arms removed, cannot use arms, visible signs of armless body"
        "No Arms" = "has no arms, all arms removed by defect, visible signs of missing arms"
        "Armless Multiple Legs" = "armless defect removes extra torso when combined with multiple legs, visible signs of armless body with multiple legs but no extra torso"
        
        # RimWorld Traits/Modifications
        "Psychic" = "has an otherworldly presence, eyes may glow or shimmer"
        "Berserker" = "has scars and signs of battle, intense expression"
        "Cannibal" = "is a cannibal, eats other sentient beings, may have unsettling features or signs of consuming humanoid flesh"
        "Cannibalism" = "practices cannibalism, consumes other sentient beings, may show signs of eating humanoid flesh"
        "Eating Someone" = "is eating another person, consuming a humanoid being, visible act of cannibalism"
        "Consuming Flesh" = "is consuming flesh, eating meat from sentient beings, may show signs of cannibalism"
        "Devouring" = "is devouring another being, consuming a creature or person, visible act of eating"
        "Corpse Eating" = "eats corpses, consumes dead bodies, may show signs of consuming humanoid remains"
        "Human Flesh" = "consumes human flesh, eats other humans, visible signs of cannibalism"
        "Cannibalistic" = "is cannibalistic, has cannibalistic tendencies, may show signs of consuming sentient beings"
        "Swallowing Whole" = "is swallowing someone whole, consuming another person entirely, visible act of swallowing a humanoid being"
        "Swallow Whole" = "can swallow others whole, able to consume entire beings, may show signs of swallowing whole"
        "Swallowed Whole" = "has swallowed someone whole, has consumed another person entirely, visible bulge or distended stomach"
        "Vore" = "practices vore, consumes others whole, visible act of swallowing beings whole"
        "Voracious" = "is voracious, consumes beings whole, has ability to swallow others entirely"
        "Gulping Down" = "is gulping down another being, consuming someone whole, visible act of swallowing"
        "Ingesting Whole" = "is ingesting someone whole, consuming another person entirely, visible act of whole-body consumption"
        "Whole Body Consumption" = "consumes whole bodies, swallows beings entirely, visible signs of whole-body consumption"
        
        # Tales of Maj'Eyal - Glutton Remade (tome-glutton-remade)
        "Glutton" = "is a Glutton, an eldritch being tainted by dimensional magic that exists only to consume, devours everything: flesh, bone, stone, wood, and the very essence of victims"
        "Glutton Class" = "is a Glutton class character, warped by dimensional taint, digestive system allows absorbing abilities from consumed beings"
        "The Maw" = "is touched by the Maw, an eldritch entity from beyond reality that exists only to consume, void within demands constant feeding"
        "Devour" = "can devour weakened foes whole (below 45% life), swallows enemies entirely, absorbs their skills and essence"
        "Gnaw" = "can gnaw on enemies, bites and tears with voracious hunger"
        "Corpse Larder" = "has a corpse larder, impossible internal space that stores bodies for later consumption, distended stomach or dimensional storage"
        "World Consumption" = "can consume the world itself, eats walls, trees, and terrain, visible signs of environmental consumption"
        "Maw Magic" = "uses Maw Magic, corrupted abilities transformed through digestive system, bile-fueled and digestive-themed powers"
        "Bile Burst" = "can create bile burst attacks, acidic digestive fluid eruptions"
        "Storm Vomit" = "can vomit storms, expels corrupted energy and digestive fluids"
        "Gluttonous Fireball" = "can create gluttonous fireball, bile-fueled fire attacks"
        "Digestive Inferno" = "can create digestive inferno, massive digestive fluid and fire attacks"
        "Stunning Regurgitation" = "can perform stunning regurgitation, expels consumed matter to stun enemies"
        "Gorge Slam" = "can perform gorge slam, attacks with distended stomach or gorged body"
        "Predatory Lunge" = "can perform predatory lunge, voracious hunting attack"
        "Ravenous Rage" = "enters ravenous rage, consumed by insatiable hunger, visible signs of voracious hunger"
        "Self Cannibalize" = "can self-cannibalize, consumes own flesh for power, visible signs of self-consumption"
        "Vampiric Hunger" = "has vampiric hunger, drains life through consumption, visible signs of life-draining consumption"
        "Desperate Gorge" = "can perform desperate gorge, consumes everything in desperation, visible signs of desperate consumption"
        "Rolling Mass" = "can become a rolling mass, transforms into a ball of consumption, visible signs of mass transformation"
        "Expulsion" = "can expel consumed matter, vomits or regurgitates stored contents, visible signs of expulsion"
        "Essence Consumption" = "consumes essence, devours the very essence of victims for permanent power"
        "Escort Consumption" = "can devour escorts, consumes companions for unique warped powers"
        "Digestive System" = "has warped digestive system, dimensional taint allows impossible consumption and storage"
        "Satiation" = "uses satiation as resource, constant hunger that demands feeding, visible signs of hunger or satiation"
        "Dimensional Taint" = "tainted by dimensional magic, eldritch corruption from beyond reality, visible signs of otherworldly corruption"
        "Eldritch Entity" = "is an eldritch entity, exists beyond normal reality, visible signs of otherworldly nature"
        "Void Within" = "has the void within, endless hunger that demands constant feeding, visible signs of internal void or hunger"
        
        # Elin - CustomRaceClassCreator MagicPlus (Blood Magic & Necromancy)
        "Blood Magic" = "uses blood magic, consumes health and mana to cast spells, visible signs of blood magic casting or blood sacrifice"
        "Blood Ritual" = "performs blood rituals, uses blood sacrifice for power, visible signs of ritual blood magic"
        "Life Steal" = "has life steal abilities, drains life force from targets, visible signs of life draining"
        "Blood Sacrifice" = "performs blood sacrifice, sacrifices health for power, visible signs of self-harm or blood sacrifice"
        "Blood Corruption" = "tainted by blood corruption, instability from blood magic use, visible signs of blood magic corruption"
        "Necromancy" = "practices necromancy, raises and controls undead, visible signs of necromantic power or undead minions"
        "Raise Corpse" = "can raise corpses, animates dead bodies as undead minions, visible signs of corpse raising or undead minions"
        "Raise Skeleton" = "can raise skeletons, animates skeletal warriors, visible signs of skeletal minions"
        "Raise Zombie" = "can raise zombies, creates shambling undead, visible signs of zombie minions"
        "Animate Dead" = "can animate dead, creates undead constructs, visible signs of animated undead"
        "Raise Wight" = "can raise wights, summons intelligent undead commanders, visible signs of wight minions"
        "Summon Bone Golem" = "can summon bone golems, creates massive bone constructs, visible signs of bone golem minions"
        "Harvest Soul" = "can harvest souls, extracts soul shards from corpses, visible signs of soul harvesting"
        "Soul Leech" = "can leech souls, drains life force and converts to soul shards, visible signs of soul draining"
        "Bind Soul" = "can bind souls, creates persistent bound servants, visible signs of soul binding"
        "Soul Blast" = "can create soul blasts, explosive soul energy attacks, visible signs of soul energy"
        "Corpse Explosion" = "can explode corpses, detonates corpses for area damage, visible signs of corpse detonation"
        "Death Curse" = "can cast death curses, marks targets for death and auto-harvests souls, visible signs of death magic"
        "Curse of Undeath" = "can curse with undeath, targets rise as zombies on death, visible signs of undeath curse"
        "Curse of Final Rest" = "can curse with final rest, prevents resurrection and binds soul to torment, visible signs of soul binding curse"
        "Curse of Blood Loss" = "can curse with blood loss, causes continuous bleeding, visible signs of bleeding curse"
        "Curse of Blood Boil" = "can curse with blood boil, causes fire damage and extreme pain, visible signs of blood boiling curse"
        "Curse of Hemorrhage" = "can curse with hemorrhage, all damage causes severe bleeding, visible signs of hemorrhagic curse"
        "Curse of the Lich" = "can curse with lich transformation, transforms target to lich-like state, visible signs of lich curse"
        "Curse of Eternal Torment" = "can curse with eternal torment, all forms of decay and soul binding, visible signs of eternal torment curse"
        "Decay Touch" = "can use decay touch, causes damage over time and reduces max health, visible signs of decay magic"
        "Rot Field" = "can create rot fields, areas of decay that spread, visible signs of decay and rot"
        "Flesh Rot" = "can cause flesh rot, rapid decay that reduces armor, visible signs of rotting flesh"
        "Bone Wall" = "can create bone walls, defensive barriers from bones, visible signs of bone construction"
        "Death Grip" = "can use death grip, pulls and restrains enemies, visible signs of death magic"
        "Speak with Dead" = "can speak with dead, communicates with corpse spirits, visible signs of necromantic communication"
        "Soul Sight" = "can use soul sight, sees souls of living creatures, visible signs of soul perception"
        "Necromantic Corruption" = "tainted by necromantic corruption, corruption from raising undead, visible signs of necromantic corruption"
        "Undead Minion" = "has undead minions, raised corpses or skeletons under control, visible signs of undead servants"
        "Soul Shard" = "uses soul shards, extracted souls used as currency, visible signs of soul shard collection"
        "Blood Instability" = "has blood instability, instability from blood magic backlash, visible signs of blood magic instability"
        
        # Elin - CustomRaceClassCreator MagicPlus (Druidic Magic)
        "Venus Maw" = "can cast Venus Maw, summons a creeping vine that erupts into a giant venus flytrap maw that swallows enemies whole, visible signs of plant-based swallowing magic"
        "Venus Flytrap Maw" = "can create venus flytrap maws, giant plant maws that swallow enemies, visible signs of carnivorous plant magic"
        "Swallow with Venus Maw" = "can swallow enemies with Venus Maw, plant maw swallows targets whole and spits them out, visible signs of plant-based vore"
        "Acid Swallow" = "can swallow with acid, targets take acid damage while swallowed, visible signs of acid digestion"
        "Spit Projectile" = "can spit swallowed targets as projectiles, launches enemies after swallowing, visible signs of spitting magic"
        "Druidic Swallowing" = "uses druidic swallowing magic, plant-based consumption of enemies, visible signs of nature-based vore"
        "Wildform" = "can transform into wildforms, shapeshifts into animal or plant forms, visible signs of animal or plant transformation"
        "Wildform Transformation" = "transformed into wildform, animal or plant form, visible signs of shapeshifting"
        "Primal Wildform" = "in primal wildform, permanent animal or plant transformation, visible signs of permanent shapeshifting"
        "Decay Magic" = "uses decay magic, rot, wither, disease, poison, blight spells, visible signs of decay and rot"
        "Wither" = "can cause withering, gradual decay and prevents healing, visible signs of withering magic"
        "Rot" = "can cause rot, rapid decay that reduces armor, visible signs of rotting"
        "Blight" = "can cause blight, spreading disease and decay, visible signs of blight magic"
        "Spreading Rot" = "can spread rot, disease that spreads to adjacent enemies, visible signs of spreading decay"
        "Corrosive Blight" = "can create corrosive blight, acid-based decay magic, visible signs of corrosive decay"
        "Fungal Growth" = "can create fungal growth, spreading fungal terrain with spores, visible signs of fungal magic"
        "Fungal Spore" = "can create fungal spores, poison damage spores that stack, visible signs of spore magic"
        "Poison Cloud" = "can create poison clouds, area poison damage, visible signs of poison magic"
        "Deadly Poison" = "can apply deadly poison, lethal poison damage, visible signs of deadly poison"
        "Stacking Venom" = "can apply stacking venom, poison that stacks multiple times, visible signs of venom magic"
        "Mutated Poison" = "can create mutated poison, poison that becomes stronger variant, visible signs of mutated poison"
        
        # Elin - CustomRaceClassCreator MagicPlus (ArcaneSaturation - Biomagic Weapons & Spirit Revival)
        "Biomagic Weapon" = "has a biomagic weapon, living weapon corrupted by arcane saturation, visible signs of living weapon or weapon mutation"
        "Living Weapon" = "has a living weapon, sentient weapon with needs and personality, visible signs of sentient weapon"
        "Weapon Corruption" = "has weapon corruption, weapon accumulating corruption from arcane saturation, visible signs of weapon corruption"
        "Weapon Mutation" = "has weapon mutation, weapon mutated into biomagic weapon, visible signs of weapon mutation"
        "Biocorrupted Weapon" = "has biocorrupted weapon, weapon corrupted by arcane energy, visible signs of biological corruption on weapon"
        "Blood Tentacle" = "weapon has blood tentacle trait, can fire blood-draining tentacle projectiles, visible signs of tentacle attacks"
        "Tentacle Attack" = "weapon can perform tentacle attacks, blood-draining tentacle projectiles that pierce targets, visible signs of tentacle projectiles"
        "Blood Drain" = "weapon can drain blood, tentacle attacks drain blood from targets, visible signs of blood draining"
        "Weapon Feeding" = "weapon requires feeding, living weapon needs food to reduce hunger, visible signs of weapon feeding or hunger"
        "Weapon Hunger" = "weapon has hunger, living weapon needs to be fed, visible signs of weapon hunger"
        "Bloodlust Weapon" = "weapon has bloodlust trait, weapon may attack allies when raging, visible signs of bloodlust or weapon rage"
        "Weapon Sentience" = "weapon has sentience, living weapon with personality and memories, visible signs of sentient weapon"
        "Sentient Weapon" = "has sentient weapon, weapon with consciousness and communication, visible signs of sentient weapon"
        "Weapon Personality" = "weapon has personality, living weapon with traits and preferences, visible signs of weapon personality"
        "Spirit Revival" = "can revive as spirit, monsters with high arcane saturation revive as spirits on death, visible signs of spirit revival"
        "Spirit Revival System" = "uses spirit revival system, monsters revive as spirits after death, visible signs of spirit transformation"
        "Revived as Spirit" = "revived as spirit, transformed into spirit form after death, visible signs of spirit form or ethereal appearance"
        "Arcane Saturation" = "has arcane saturation, accumulated arcane energy from spell casting, visible signs of arcane saturation or magic buildup"
        "Saturation Overflow" = "has saturation overflow, uncontrolled magic bursts from critical saturation, visible signs of magic overflow or uncontrolled magic"
        "Arcane Discharge" = "can create arcane discharge, releases stored saturation as environmental effects, visible signs of arcane discharge"
        "Magic Surge" = "can create magic surge, temporary massive power bonus from saturation overflow, visible signs of magic surge"
        "Instability Wave" = "can create instability wave, affects nearby casters with interference, visible signs of magic instability"
        "Pollution Spike" = "can create pollution spike, automatically dumps saturation to pollution, visible signs of pollution or environmental corruption"
        "Weapon Evolution" = "weapon can evolve, biomagic weapon evolves based on usage patterns, visible signs of weapon evolution"
        "Enchantment Corruption" = "weapon has enchantment corruption, enchantments corrupted by biomagic traits, visible signs of corrupted enchantments"
        "Weapon Devour" = "weapon can devour, living weapon with devouring heart trait, visible signs of weapon devouring"
        "Voracious Edge" = "weapon has voracious edge trait, weapon hungers for more, visible signs of voracious weapon"
        "Devouring Heart" = "weapon has devouring heart trait, weapon consumes essence, visible signs of devouring weapon"
        "Ritual Parasite" = "weapon has ritual parasite trait, weapon feeds on rituals, visible signs of parasitic weapon"
        "Guarding Maw" = "weapon has guarding maw trait, weapon protects with maw-like features, visible signs of maw weapon"
        
        # Elin - CustomRaceClassCreator QuestPlus (NPC Quest Actions)
        "NPC Kill Quest" = "NPC performing kill quest, hunting and killing targets for quest objectives, visible signs of quest-based combat or hunting"
        "NPC Kill Player Quest" = "NPC performing kill player quest, hunting and attempting to kill the player character, visible signs of player hunting or assassination attempt"
        "NPC Smuggling Quest" = "NPC performing smuggling quest, transporting contraband illegally, avoiding checkpoints, visible signs of smuggling or illegal transport"
        "NPC Stealth Quest" = "NPC performing stealth quest, sneaking undetected, may involve theft or infiltration, visible signs of stealth or sneaking"
        "NPC Possess Quest" = "NPC performing possess quest, using dark magic to possess targets, visible signs of possession magic or dark magic"
        "NPC Exorcise Quest" = "NPC performing exorcise quest, exorcising possessed targets, visible signs of exorcism or spirit removal"
        "NPC Assassination Quest" = "NPC performing assassination quest, stealthily killing specific targets, visible signs of assassination attempt"
        "Quest-Based Violence" = "performing quest-based violence, engaging in combat or killing for quest objectives, visible signs of quest-driven combat"
        "Quest-Based Crime" = "performing quest-based crime, engaging in illegal activities for quest objectives, visible signs of criminal activity"
        "Quest-Based Dark Magic" = "performing quest-based dark magic, using dark magic for quest objectives, visible signs of dark magic use"
        
        # Elin - CustomRaceClassCreator PCCMutation (Visual Mutations)
        "PCC Mutation" = "has PCC mutation, visual mutation affecting appearance, visible signs of mutation"
        "Demon Eyes Mutation" = "has demon eyes mutation, eyes glow with demonic red light, visible signs of demonic eyes"
        "Crystalline Growth Mutation" = "has crystalline growth mutation, crystals grow on the skin, visible signs of crystal growth"
        "Demon Horns Mutation" = "has demon horns mutation, horns sprout from the head, visible signs of demon horns"
        "Vein Pattern Mutation" = "has vein pattern mutation, dark veins spread across the skin, visible signs of vein patterns"
        "Dragon Scales Mutation" = "has dragon scales mutation, scales cover the skin, visible signs of dragon scales"
        "Body Horror Mutation" = "has body horror mutation, body deformed or warped by mutation, visible signs of body horror"
        "Corruption Mutation" = "has corruption mutation, body corrupted by dark magic or taint, visible signs of corruption"
        "Rot Mutation" = "has rot mutation, body showing signs of decay or rot, visible signs of rotting flesh"
        "Blood Mutation" = "has blood mutation, body marked by blood or bleeding, visible signs of blood mutation"
        "Warped Limbs Mutation" = "has warped limbs mutation, limbs deformed or twisted by mutation, visible signs of limb deformation"
        "Extra Appendages Mutation" = "has extra appendages mutation, extra limbs or appendages from mutation, visible signs of extra appendages"
        "Skin Mutation" = "has skin mutation, skin altered by mutation, visible signs of skin mutation"
        "Bone Deformation Mutation" = "has bone deformation mutation, bones warped or deformed by mutation, visible signs of bone deformation"
        "Growth Mutation" = "has growth mutation, abnormal growths on the body, visible signs of growths"
        "Deformity Mutation" = "has deformity mutation, body deformed by mutation, visible signs of physical deformity"
        "Taint Mutation" = "has taint mutation, body tainted by dark magic or corruption, visible signs of taint"
        "Eldritch Mutation" = "has eldritch mutation, body warped by otherworldly forces, visible signs of eldritch corruption"
        "Flesh Warp Mutation" = "has flesh warp mutation, flesh warped or distorted by mutation, visible signs of flesh warping"
        "Mutation Overlay" = "has mutation overlay, visual overlay from mutation system, visible signs of mutation overlay"
        
        # Elin - CustomRaceClassCreator Feats (Character Feats)
        "Gluttonous Feat" = "has Gluttonous feat, food restores more HP/MP but hunger increases faster, visible signs of gluttony or voracious appetite"
        "Bloodthirsty Feat" = "has Bloodthirsty feat, deals more damage to bleeding enemies, visible signs of bloodthirst or bloodlust"
        "Vampiric Strike Feat" = "has Vampiric Strike feat, melee attacks restore HP as life drain, visible signs of vampiric life drain or blood consumption"
        "Berserker Rage Feat" = "has Berserker Rage feat, enters berserker rage dealing massive damage, visible signs of berserker rage or battle frenzy"
        "System Corruption Feat" = "has System Corruption feat, random stat bonuses and penalties from corruption, visible signs of system corruption or mechanical corruption"
        "Ether Taint Feat" = "has Ether Taint feat, presence taints area with ether disease, visible signs of ether taint or ether corruption"
        "Dragon Necromancer Feat" = "has Dragon Necromancer feat, can raise undead dragons from dragon corpses, visible signs of dragon necromancy or undead dragon raising"
        "Overkill Enthusiast Feat" = "has Overkill Enthusiast feat, dealing excessive overkill damage intimidates enemies, visible signs of overkill violence or excessive damage"
        "Ether Flow Feat" = "has Ether Flow feat, applies ether corruption to enemies transforming them into ether monsters, visible signs of ether corruption or monster transformation"
        "Ether Graft Feat" = "has Ether Graft feat, grafts ether mutations from enemies, visible signs of ether grafting or mutation theft"
        "Ether Rage Feat" = "has Ether Rage feat, ether disease fuels rage dealing massive physical damage, visible signs of ether-fueled rage or violent transformation"
        "Sneak Attack Feat" = "has Sneak Attack feat, attacks from behind deal massive damage, visible signs of stealth attacks or assassination"
        "Unfeeling Feat" = "has Unfeeling feat, immune to pain and bleeding, visible signs of unfeeling or pain immunity"
        "Cursed Feat" = "has Cursed feat, cursed with stat penalties but gains experience faster, visible signs of curse or dark magic curse"
        "Battle Frenzy Feat" = "has Battle Frenzy feat, deals more damage when below 50% HP, visible signs of battle frenzy or combat rage"
        "Reckless Strike Feat" = "has Reckless Strike feat, melee attacks have high crit chance but low accuracy, visible signs of reckless combat or wild attacks"
        "Reckless Feat" = "has Reckless feat, deals more damage but takes more damage, visible signs of reckless combat or dangerous fighting style"
        "Ether Seed Feat" = "has Ether Seed feat, plants ether seeds in enemies that grow into mutations, visible signs of ether seeding or mutation planting"
        "Ether Mark Feat" = "has Ether Mark feat, marks enemies with ether causing mutations, visible signs of ether marking or mutation marking"
        "Ether Warp Feat" = "has Ether Warp feat, warps reality with ether for teleportation, visible signs of ether warping or reality distortion"
        
        "Psychopath" = "has cold, emotionless expression"
        "Body Modder" = "has visible cybernetic or bionic modifications"
        "Bionic Arms" = "has mechanical or bionic arms"
        "Bionic Legs" = "has mechanical or bionic legs"
        "Bionic Eyes" = "has mechanical or glowing eyes"
        "Bionic Heart" = "has visible cybernetic chest modifications"
        "Archotech" = "has advanced technological body modifications"
        "Horror" = "has disturbing, unsettling features that defy normal description"
        "Corrupted" = "has signs of corruption: twisted features, unnatural colors"
        
        # RimWorld - Diaper Lover Meme (GravshipSOS2CelsiusBridge / Zealous Innocence)
        "Diaper Lover Meme" = "follows the diaper preference ideology, prefers wearing adult diapers for comfort and practicality"
        "Diaper Preference" = "prefers wearing adult diapers for comfort and practicality"
        "Onesie" = "wears a onesie, a full-body support garment that provides diaper support"
        "Simplie" = "wears a simplie, a basic onesie with diaper support"
        "Worksie" = "wears a worksie, a work-focused onesie with diaper support and work speed bonus"
        "Gunsie" = "wears a gunsie, a combat-focused onesie with diaper support and combat bonuses"
        "Premium Diaper" = "wears a premium adult diaper with maximum absorbency, best comfort, minimal bulk"
        "Inferior Diaper" = "wears a low-quality adult diaper that is uncomfortable and barely absorbent"
        "Full Comfort Setup" = "wears both an adult diaper and a onesie for complete comfort and support"
    }
    
    foreach ($mutation in $Mutations) {
        if ($mutationMap.ContainsKey($mutation)) {
            $visualEffects += $mutationMap[$mutation]
        } else {
            # Generic mutation - try to infer visual effect
            $mutationLower = $mutation.ToLower()
            if ($mutationLower -match "arm|limb") {
                $visualEffects += "has unusual arm or limb modifications"
            } elseif ($mutationLower -match "eye|vision|sight") {
                $visualEffects += "has unusual eye modifications"
            } elseif ($mutationLower -match "skin|hide|carapace|scale") {
                $visualEffects += "has unusual skin or body covering modifications"
            } elseif ($mutationLower -match "head|face|mouth|jaw") {
                $visualEffects += "has unusual head or facial modifications"
            } elseif ($mutationLower -match "tail|appendage|tentacle") {
                $visualEffects += "has unusual appendages or tail modifications"
            } else {
                $visualEffects += "has $mutation mutation affecting appearance"
            }
        }
    }
    
    return $visualEffects
}

function Get-TraitVisualEffects {
    <#
    .SYNOPSIS
    Converts trait names (medical conditions, disabilities, etc.) into visual description elements.
    Handles content that might be blocked due to stigmas or social associations.
    #>
    param([string[]]$Traits)
    
    $visualEffects = @()
    $traitMap = @{
        # Missing Body Parts / Amputations (for realism)
        "Missing Arm" = "is missing one arm, with visible amputation site or stump"
        "Missing Arms" = "is missing both arms, with visible amputation sites or stumps"
        "Missing Leg" = "is missing one leg, with visible amputation site or stump"
        "Missing Legs" = "is missing both legs, with visible amputation sites or stumps"
        "Missing Hand" = "is missing one hand, with visible amputation at wrist"
        "Missing Hands" = "is missing both hands, with visible amputations at wrists"
        "Missing Foot" = "is missing one foot, with visible amputation at ankle"
        "Missing Feet" = "is missing both feet, with visible amputations at ankles"
        "Missing Eye" = "is missing one eye, with empty eye socket or eye patch"
        "Missing Eyes" = "is missing both eyes, with empty eye sockets or blindfold"
        "Blind" = "is blind, cannot see, may have empty eye sockets, covered eyes, or non-functional eyes"
        "Blindness" = "has blindness, cannot see, may have empty eye sockets, covered eyes, or non-functional eyes"
        "Blind in One Eye" = "is blind in one eye, one eye is non-functional or missing"
        "Partially Blind" = "is partially blind, has limited vision"
        "Legally Blind" = "is legally blind, has severe vision impairment"
        "Blindfold" = "wears a blindfold, eyes are covered"
        "Eye Patch" = "wears an eye patch, one eye is covered"
        "Amputee" = "has visible amputations, missing limbs"
        "Above Knee Amputation" = "has above-knee amputation, missing leg above knee"
        "Below Knee Amputation" = "has below-knee amputation, missing leg below knee"
        "Above Elbow Amputation" = "has above-elbow amputation, missing arm above elbow"
        "Below Elbow Amputation" = "has below-elbow amputation, missing arm below elbow"
        "Hemipelvectomy" = "has hemipelvectomy, missing entire leg and part of pelvis"
        "Quadruple Amputee" = "is missing all four limbs"
        "Double Amputee" = "is missing two limbs"
        
        # Medical/Disability Accommodations (often blocked due to stigma)
        # Note: "adult diaper" is commonly blocked - three-tier routing will auto-escalate if refused
        "Incontinent" = "wears an adult diaper for medical necessity"
        "Adult Diaper" = "wears an adult diaper"
        "Wearing Adult Diaper" = "wears an adult diaper"
        "Incontinence Protection" = "wears an adult diaper for medical necessity"
        "Adult Incontinence" = "wears an adult diaper for medical necessity"
        "Bladder Incontinence" = "wears an adult diaper for medical necessity"
        "Bowel Incontinence" = "wears an adult diaper for medical necessity"
        "Colostomy Bag" = "has a colostomy bag visible"
        "Feeding Tube" = "has a feeding tube"
        "Tracheostomy" = "has a tracheostomy tube"
        "IV Line" = "has an IV line attached"
        "Ostomy" = "has an ostomy bag"
        
        # Mental Health (often stigmatized)
        "Age Regression" = "exhibits age regression behaviors or appearance"
        "Dissociative Identity" = "shows signs of dissociative identity, may have distinct appearance shifts"
        
        # Social Stigmas (often blocked)
        "Fetish Gear" = "wears fetish-related clothing or gear"
        "BDSM" = "wears BDSM-related attire or accessories"
        "Age Play" = "exhibits age play characteristics"
        "Diaper Fetish" = "wears diapers as part of fetish or lifestyle"
        "Pet Play" = "wears pet play gear or accessories"
        "Furry" = "has anthropomorphic animal features"
        
        # RimWorld - Diaper Lover Meme Context (from GravshipSOS2CelsiusBridge)
        # Note: This is a practical meme for comfort/preference, NOT age regression
        "Diaper Preference Ideology" = "follows an ideology that values wearing adult diapers for practical reasons: medical needs, long work shifts, hazardous environments, space travel, personal comfort, or anxiety about finding bathrooms"
        "Comfort Guide" = "is a leader in the diaper preference ideology, values practical comfort"
        "Practical Living" = "values practical living and personal comfort choices"
        
        # Body Modifications (sometimes blocked)
        "Extreme Body Mods" = "has extreme body modifications (stretched piercings, implants, etc.)"
        "Scarification" = "has extensive scarification patterns"
        
        # Other Physical Conditions
        "Burn Scars" = "has visible burn scars covering parts of body"
        "Surgical Scars" = "has visible surgical scars"
        
        # Caves of Qud - Broodmother Traits (visual states and swarm characteristics)
        "Pulsating Sack" = "has a pulsating chitinous broodling sack that visibly pulses and swells"
        "Swelling Sack" = "has a broodling sack that is visibly swelling with developing broodlings"
        "Biometal Enhanced" = "has biometal enhancements visible on the broodling sack, metallic components integrated into chitin"
        "Swarm Surrounding" = "is surrounded by a swarm of arthropod minions, broodlings visible in the background"
        "Broodling Nest" = "has a broodling nest nearby where cocooned broodlings are stored"
        "Cannibalizing Swarm" = "has a swarm that is cannibalizing weaker members, visible signs of swarm feeding"
        "Starving Swarm" = "has a swarm that appears hungry, broodlings looking thin or desperate"
        "Well-Fed Swarm" = "has a healthy, well-fed swarm with vibrant, energetic broodlings"
    }
    
    foreach ($trait in $Traits) {
        if ($traitMap.ContainsKey($trait)) {
            $visualEffects += $traitMap[$trait]
        } else {
            # Generic trait - add as-is
            $visualEffects += "has $trait trait affecting appearance"
        }
    }
    
    return $visualEffects
}

function Build-CharacterDescription {
    <#
    .SYNOPSIS
    Builds a comprehensive character description from base description, mutations, and traits.
    #>
    param(
        [string]$BaseDescription,
        [string[]]$Mutations,
        [string[]]$Traits,
        [string]$GameType
    )
    
    $fullDescription = $BaseDescription
    
    # Add mutation visual effects
    if ($Mutations.Count -gt 0) {
        $mutationEffects = Get-MutationVisualEffects -Mutations $Mutations
        if ($mutationEffects.Count -gt 0) {
            $fullDescription += "`n`nMutations and physical modifications: " + ($mutationEffects -join ". ") + "."
        }
    }
    
    # Add trait visual effects
    if ($Traits.Count -gt 0) {
        $traitEffects = Get-TraitVisualEffects -Traits $Traits
        if ($traitEffects.Count -gt 0) {
            $fullDescription += "`n`nAdditional traits and characteristics: " + ($traitEffects -join ". ") + "."
        }
    }
    
    # Add game-specific context
    switch ($GameType.ToLower()) {
        "rimworld" {
            $fullDescription += "`n`nThis is a RimWorld character. Style: detailed character portrait, post-apocalyptic sci-fi setting, may include scars, cybernetics, mutations, medical conditions, practical apparel like adult diapers and onesies (Simplie, Worksie, Gunsie), or extensive body horror modifications from the Fleshcrafter meme (fleshmass organs, tentacles, ghoul barbs erupting through skin, insectoid claws, twisted flesh, visible mutations, grotesque appearances)."
        }
        "cdda" {
            $fullDescription += "`n`nThis is a Cataclysm: Dark Days Ahead character. Style: post-apocalyptic survivor, realistic mutations and body modifications, gritty and detailed, may include medical equipment or disabilities."
        }
        "qud" {
            $fullDescription += "`n`nThis is a Caves of Qud character. Style: science fantasy, bizarre mutations, vibrant colors, detailed character design. May include arthropod matriarch features, broodling sacks, swarms of insect/arachnid minions, space-time vortex effects (black holes, white holes, reality tears, spacetime distortions, gravitational lensing, dimensional overlap, non-euclidean geometry, spiraling reality fragments, ghostly echoes from other dimensions), conjoined creatures (creatures physically attached/fused to the body through conjoinment body parts, body horror fusion, symbiotic connections), improved mutations (enhanced multiple arms with missile slots, multiple legs with dual torso structure, wings on both backs, horns on all heads, claws on all hands, enhanced spinnerets shooting web arcs, enhanced flaming/freezing rays in multiple directions), hydra heads (multiple heads that regrow when cut off, head dismemberment and regeneration, cauterization from fire), snake tail (legs replaced with snake tail for constriction and swimming), scales (reptilian scales for heat resistance), animal legs (increased quickness, no foot equipment), muzzle (animal-like muzzle for attacks), fluffy tail (prone resistance), poisonous fangs (venom attacks), or armless defect (no arms, removes extra torso with multiple legs)."
        }
        "tome" {
            $fullDescription += "`n`nThis is a Tales of Maj'Eyal character. Style: fantasy RPG, detailed character design. May include Glutton class features (eldritch consumption, dimensional taint, warped digestive systems, the Maw, devouring whole, corpse larders, world consumption, Maw Magic, bile attacks, digestive infernos, rolling mass transformations, void within demanding constant feeding)."
        }
        "elin" {
            $fullDescription += "`n`nThis is an Elin character. Style: fantasy RPG, detailed character design. May include Blood Magic features (health sacrifice, blood rituals, life steal, blood corruption, blood instability), Necromancy features (raising undead, soul harvesting, soul leeching, death curses, decay magic, rot spells, bone construction, necromantic corruption, undead minions, soul shards), Druidic Magic features (Venus Maw swallowing, wildform transformations, decay magic, rot, blight, poison, fungal growth, plant-based consumption), or ArcaneSaturation features (biomagic living weapons, weapon corruption, tentacle attacks, blood-draining weapons, weapon feeding, weapon sentience, spirit revival, arcane saturation overflow, magic surges, pollution spikes)."
        }
        default {
            $fullDescription += "`n`nStyle: detailed character portrait, high quality, professional illustration, realistic and respectful depiction."
        }
    }
    
    return $fullDescription
}

# ============================================================
# OLLAMA ENHANCEMENT (with automatic routing)
# ============================================================

function Enhance-DescriptionWithOllama {
    <#
    .SYNOPSIS
    Enhances character description using Ollama with automatic dark-tone and refusal detection routing.
    The three-tier system will automatically escalate if content is refused for ANY reason.
    #>
    param(
        [string]$Description,
        [string]$CharacterName,
        [string]$GameType
    )
    
    if (-not (Test-Path $ollamaModule)) {
        Write-Host "[WARN] OllamaIntegration module not found, skipping enhancement" -ForegroundColor Yellow
        return $Description
    }
    
    try {
        # Test Ollama connection
        $ollamaAvailable = Test-OllamaConnection
        if (-not $ollamaAvailable) {
            Write-Host "[WARN] Ollama not available, using original description" -ForegroundColor Yellow
            return $Description
        }
        
        Write-Host "  Enhancing description with Ollama (auto-routing enabled)..." -ForegroundColor Cyan
        
        # Build enhancement prompt - explicitly mentions handling all content types
        $enhancementPrompt = @"
You are a character artist creating a detailed visual description for image generation.

Character Name: $CharacterName
Game Type: $GameType
Base Description: $Description

Create an enhanced, detailed visual description suitable for generating a high-quality character portrait. Include:
- Detailed physical appearance (face, body, proportions)
- Specific visual details about mutations, modifications, medical conditions, disabilities, or unusual features
- Color palette and texture details (skin, hair, clothing, mutations, medical equipment)
- Lighting and atmosphere suggestions
- Pose and expression
- Any distinctive features that make this character unique
- Respectful and accurate depiction of any medical conditions, disabilities, or accommodations

Be specific and detailed. This description will be used to generate a detailed character image (not pixel art).

IMPORTANT: This is for legitimate character creation in games. Describe all features accurately, including:
- Medical equipment (adult diapers, wheelchairs, prosthetics, etc.)
- Disabilities and accommodations
- Mutations and body modifications
- Any other characteristics mentioned

Be direct and accurate. If the character wears an adult diaper, describe it as such. This is legitimate medical equipment for character creation.

Return ONLY the enhanced description, no introductory text or explanations.
"@
        
        # Use Ollama with automatic routing (will detect dark tone and route appropriately)
        # AutoEscalate ensures that if ANY model refuses, it escalates to Tier 3
        $enhanced = Invoke-OllamaRequest `
            -Prompt $enhancementPrompt `
            -TaskType "visual" `
            -ResponseLength "detailed" `
            -AutoEscalate:$true
        
        if ($enhanced -and $enhanced.Length -gt $Description.Length) {
            Write-Host "  [OK] Description enhanced with Ollama" -ForegroundColor Green
            if ($script:IsVerbose) {
                Write-Host "  Enhanced length: $($enhanced.Length) chars (original: $($Description.Length) chars)" -ForegroundColor Gray
            }
            return $enhanced.Trim()
        } else {
            Write-Host "  [WARN] Enhancement returned shorter result, using original" -ForegroundColor Yellow
            return $Description
        }
    } catch {
        Write-Host "  [WARN] Ollama enhancement failed: $_" -ForegroundColor Yellow
        return $Description
    }
}

# ============================================================
# STABLE DIFFUSION IMAGE GENERATION
# ============================================================

function Test-StableDiffusionConnection {
    <#
    .SYNOPSIS
    Tests if Stable Diffusion API is available.
    #>
    param([string]$Url)
    
    try {
        $response = Invoke-RestMethod -Uri "$Url/docs" -Method Get -TimeoutSec 3 -ErrorAction Stop
        return $true
    } catch {
        try {
            # Try health check endpoint
            $response = Invoke-RestMethod -Uri "$Url/health" -Method Get -TimeoutSec 3 -ErrorAction Stop
            return $true
        } catch {
            try {
                # Try root endpoint
                $response = Invoke-RestMethod -Uri $Url -Method Get -TimeoutSec 3 -ErrorAction Stop
                return $true
            } catch {
                return $false
            }
        }
    }
}

function Start-StableDiffusionServer {
    <#
    .SYNOPSIS
    Starts the Stable Diffusion API server if it's not already running.
    #>
    param(
        [string]$ScriptRoot = $PSScriptRoot,
        [switch]$Verbose
    )
    
    # Check if server is already running
    if (Test-StableDiffusionConnection -Url "http://localhost:1338") {
        if ($Verbose) {
            Write-Host "  [OK] Stable Diffusion API server is already running" -ForegroundColor Green
        }
        return $true
    }
    
    Write-Host "  Starting Stable Diffusion API server..." -ForegroundColor Cyan
    
    # Check if stable-diffusion-api-server command is available
    $serverCmd = Get-Command "stable-diffusion-api-server" -ErrorAction SilentlyContinue
    if (-not $serverCmd) {
        Write-Host "  [WARN] 'stable-diffusion-api-server' command not found in PATH" -ForegroundColor Yellow
        Write-Host "  Please ensure stable-diffusion-api-server is installed and in your PATH" -ForegroundColor Gray
        Write-Host "  Installation: pip install stable-diffusion-api-server" -ForegroundColor Gray
        return $false
    }
    
    # Check if Start-StableDiffusionServer.ps1 exists and use it
    $startScript = Join-Path $ScriptRoot "Start-StableDiffusionServer.ps1"
    if (Test-Path $startScript) {
        Write-Host "  Using startup script: $startScript" -ForegroundColor Gray
        # Start the server in a new PowerShell window (detached)
        $job = Start-Job -ScriptBlock {
            param($scriptPath)
            & $scriptPath
        } -ArgumentList $startScript
        
        # Wait a moment for the job to start
        Start-Sleep -Seconds 2
        
        # Check if job is running
        if ($job.State -eq "Running") {
            Write-Host "  [OK] Server startup job started (PID: $($job.Id))" -ForegroundColor Green
        } else {
            Write-Host "  [WARN] Server startup job may have failed" -ForegroundColor Yellow
        }
    } else {
        # Start server directly
        Write-Host "  Starting server directly..." -ForegroundColor Gray
        
        # Determine best drive for model storage (not C: or D:)
        $availableDrives = Get-PSDrive -PSProvider FileSystem | Where-Object { 
            $_.Name -ne "C" -and $_.Name -ne "D" -and $_.Free -gt 10GB 
        } | Sort-Object Free -Descending
        
        if ($availableDrives) {
            $bestDrive = $availableDrives[0].Name
            $modelPath = "${bestDrive}:\StableDiffusion\Models"
            
            # Create directory if it doesn't exist
            if (-not (Test-Path $modelPath)) {
                New-Item -ItemType Directory -Path $modelPath -Force | Out-Null
            }
            
            # Set HF_HOME environment variable
            $env:HF_HOME = $modelPath
            
            if ($Verbose) {
                Write-Host "  Model storage: $env:HF_HOME" -ForegroundColor Gray
                Write-Host "  Drive: $bestDrive (Free: $([math]::Round($availableDrives[0].Free/1GB, 2)) GB)" -ForegroundColor Green
            }
        } else {
            if ($Verbose) {
                Write-Host "  [WARN] No suitable drive found (need >10GB free, not C: or D:)" -ForegroundColor Yellow
                Write-Host "  Models will download to default location" -ForegroundColor Gray
            }
        }
        
        # Start the server in background
        $job = Start-Job -ScriptBlock {
            stable-diffusion-api-server
        }
        
        if ($job.State -eq "Running") {
            Write-Host "  [OK] Server startup job started (PID: $($job.Id))" -ForegroundColor Green
        } else {
            Write-Host "  [WARN] Server startup job may have failed" -ForegroundColor Yellow
        }
    }
    
    # Wait for server to become available (with timeout)
    Write-Host "  Waiting for server to start..." -ForegroundColor Cyan
    $maxWait = 120  # 2 minutes
    $waitInterval = 2  # Check every 2 seconds
    $elapsed = 0
    
    while ($elapsed -lt $maxWait) {
        Start-Sleep -Seconds $waitInterval
        $elapsed += $waitInterval
        
        if (Test-StableDiffusionConnection -Url "http://localhost:1338") {
            Write-Host "  [OK] Server is ready! (waited $elapsed seconds)" -ForegroundColor Green
            return $true
        }
        
        if ($elapsed % 10 -eq 0) {
            Write-Host "  Still waiting... ($elapsed/$maxWait seconds)" -ForegroundColor Gray
        }
    }
    
    Write-Host "  [WARN] Server did not become available within $maxWait seconds" -ForegroundColor Yellow
    Write-Host "  The server may still be starting in the background" -ForegroundColor Gray
    return $false
}

function Enhance-ImageWithAI {
    <#
    .SYNOPSIS
    Enhances a generated image using AI analysis and improvement suggestions.
    Uses Ollama vision models to analyze the image and suggest improvements.
    #>
    param(
        [string]$ImagePath,
        [string]$OriginalPrompt,
        [string]$CharacterName,
        [string]$GameType,
        [int]$Width,
        [int]$Height,
        [string]$OllamaUrl = "http://localhost:11434",
        [string]$StableDiffusionUrl = "http://localhost:1338",
        [switch]$RegenerateImproved,
        [switch]$Verbose
    )
    
    if (-not (Test-Path $ImagePath)) {
        throw "Image file not found: $ImagePath"
    }
    
    Write-Host "  Analyzing image with AI for improvements..." -ForegroundColor Cyan
    
    # Convert image to base64 for Ollama vision model
    try {
        $imageBytes = [System.IO.File]::ReadAllBytes($ImagePath)
        $imageBase64 = [Convert]::ToBase64String($imageBytes)
    } catch {
        Write-Host "  [WARN] Could not read image for analysis: $_" -ForegroundColor Yellow
        return $ImagePath
    }
    
    # Check if Ollama is available
    $ollamaModule = Join-Path $PSScriptRoot "Shared\OllamaIntegration.psm1"
    if (-not (Test-Path $ollamaModule)) {
        Write-Host "  [WARN] OllamaIntegration module not found, skipping AI enhancement" -ForegroundColor Yellow
        return $ImagePath
    }
    
    try {
        Import-Module $ollamaModule -Force -ErrorAction SilentlyContinue
        
        # Build analysis prompt
        $charName = $CharacterName
        $gameType = $GameType
        $origPrompt = $OriginalPrompt
        
        # Use string formatting to avoid here-string parsing issues
        $analysisPrompt = 'Analyze this character image and provide specific improvement suggestions.' + "`n`n" +
            'Character: ' + $charName + "`n" +
            'Game Type: ' + $gameType + "`n" +
            'Original Prompt: ' + $origPrompt + "`n`n" +
            'Examine the image carefully and provide:' + "`n" +
            '1. What looks good and should be preserved' + "`n" +
            '2. Specific areas that need improvement - details, colors, composition, lighting, anatomy, accuracy to description, etc.' + "`n" +
            '3. Concrete suggestions for enhancement' + "`n" +
            '4. A refined, detailed prompt that would generate an improved version with better quality, detail, and accuracy' + "`n`n" +
            'Be specific and actionable. Focus on visual quality, detail, and accuracy to the description.' + "`n" +
            'Return a refined prompt that can be used to generate an improved version.'
        
        # Check for vision models using ollama list
        $visionModels = @("llava:latest", "llava:13b", "llava:7b", "llama3.2-vision:latest", "bakllava:latest")
        $selectedModel = $null
        
        try {
            $availableModels = ollama list 2>&1
            if ($LASTEXITCODE -eq 0) {
                foreach ($model in $visionModels) {
                    $modelName = $model -replace ':.*$', ''
                    if ($availableModels -match $modelName) {
                        $selectedModel = $model
                        break
                    }
                }
            }
        } catch {
            # Try to use first model anyway
            $selectedModel = $visionModels[0]
        }
        
        if (-not $selectedModel) {
            Write-Host "  [WARN] No vision model available, skipping AI enhancement" -ForegroundColor Yellow
            Write-Host "    Install a vision model: ollama pull llava:latest" -ForegroundColor Gray
            return $ImagePath
        }
        
        Write-Host "    Using vision model: $selectedModel" -ForegroundColor Gray
        
        # Use Ollama's vision API (requires base64 image)
        $ollamaApiUrl = "$OllamaUrl/api"
        $requestBody = @{
            model = $selectedModel
            prompt = $analysisPrompt
            images = @($imageBase64)
            stream = $false
        } | ConvertTo-Json -Depth 10
        
        $analysisResponse = Invoke-RestMethod `
            -Uri "$ollamaApiUrl/generate" `
            -Method Post `
            -ContentType "application/json" `
            -Body $requestBody `
            -TimeoutSec 180 `
            -ErrorAction Stop
        
        $improvementSuggestions = $analysisResponse.response
        
        if ($Verbose) {
            Write-Host "  AI Analysis:" -ForegroundColor Cyan
            Write-Host ("    {0}" -f ($improvementSuggestions -replace "`n", "`n    ")) -ForegroundColor Gray
        }
        
        Write-Host "  [OK] Image analyzed" -ForegroundColor Green
        
        # If regenerate is requested, create improved prompt and regenerate
        if ($RegenerateImproved) {
            Write-Host "  Generating improved version based on AI analysis..." -ForegroundColor Cyan
            
            # Extract improved prompt from analysis
            # Try to find a refined prompt in the response, or combine original with improvements
            $improvedPrompt = $improvementSuggestions
            if ($improvedPrompt -notmatch "refined prompt|improved prompt|enhanced prompt" -and $improvedPrompt.Length -lt 500) {
                # Analysis is short, likely just suggestions - combine with original
                $improvedPrompt = "$OriginalPrompt`n`nAI Enhancement Suggestions: $improvementSuggestions`n`nApply these improvements: better detail, improved composition, enhanced lighting, more accurate to description."
            }
            
            # Generate improved version
            $improvedPath = $ImagePath -replace '\.png$', '_improved.png'
            $improvedImage = Generate-ImageWithStableDiffusion `
                -Prompt $improvedPrompt `
                -Width $Width `
                -Height $Height `
                -ApiUrl $StableDiffusionUrl `
                -Steps $Steps `
                -GuidanceScale $GuidanceScale `
                -OutputPath $improvedPath
            
            $improvedMsg = '  [OK] Improved version generated: ' + $improvedPath
            Write-Host $improvedMsg -ForegroundColor Green
            return $improvedPath
        }
        
        # Save analysis to metadata
        $analysisPath = $ImagePath -replace '\.png$', '_ai_analysis.txt'
        $improvementSuggestions | Set-Content -Path $analysisPath -Encoding UTF8
        Write-Host "  Analysis saved: $analysisPath" -ForegroundColor Gray
        
        return $ImagePath
        
    } catch {
        Write-Host "  [WARN] AI enhancement failed: $_" -ForegroundColor Yellow
        if ($Verbose) {
            Write-Host "    Error details: $($_.Exception.Message)" -ForegroundColor Gray
        }
        return $ImagePath
    }
}

function Generate-ImageWithStableDiffusion {
    <#
    .SYNOPSIS
    Generates an image using Stable Diffusion API (typically uncensored).
    #>
    param(
        [string]$Prompt,
        [string]$NegativePrompt = "blurry, low quality, pixelated, distorted, deformed, bad anatomy, text, watermark",
        [int]$Width = 1024,
        [int]$Height = 1024,
        [string]$ApiUrl = "http://localhost:1338",
        [int]$Steps = 50,
        [double]$GuidanceScale = 7.5,
        [string]$OutputPath
    )
    
    if (-not (Test-StableDiffusionConnection -Url $ApiUrl)) {
        # Single-server policy: only spawn a server when explicitly allowed.
        if ($script:AllowStartServer) {
            Write-Host "  Stable Diffusion API not available, attempting to start server (opt-in)..." -ForegroundColor Yellow
            $serverStarted = Start-StableDiffusionServer -ScriptRoot $PSScriptRoot -Verbose:$script:IsVerbose
            
            if ($serverStarted -and (Test-StableDiffusionConnection -Url $ApiUrl)) {
                Write-Host "  [OK] Server started successfully!" -ForegroundColor Green
            } else {
                Write-Host "  [WARN] Server startup may have failed or is still starting" -ForegroundColor Yellow
            }
        } else {
            Write-Host "  [INFO] No SD server detected. Auto-start is disabled (single-server policy)." -ForegroundColor Gray
            Write-Host "  [INFO] Start one with Tools\Start-StableDiffusionServer.ps1, or pass -AllowStartServer." -ForegroundColor Gray
        }
        
        # Final check - throw error if still not available
        if (-not (Test-StableDiffusionConnection -Url $ApiUrl)) {
            throw "Stable Diffusion API not available at $ApiUrl. Start it with Tools\Start-StableDiffusionServer.ps1 (single-server; auto-start is disabled by default)."
        }
    }
    
    Write-Host "  Generating image with Stable Diffusion..." -ForegroundColor Cyan
    Write-Host "    Prompt length: $($Prompt.Length) characters" -ForegroundColor Gray
    Write-Host "    Dimensions: ${Width}x${Height}" -ForegroundColor Gray

    # Prefer the robust shared Python HTTP client (generous finite timeout +
    # on-disk salvage of slow-but-complete generations). Falls back to the
    # inline PowerShell path below if the client is missing or errors.
    $pyClient = Join-Path $PSScriptRoot "Shared\sd_http_client.py"
    if (Test-Path $pyClient) {
        $pyCmd = if (Get-Command python -ErrorAction SilentlyContinue) { "python" }
                 elseif (Get-Command python3 -ErrorAction SilentlyContinue) { "python3" }
                 else { $null }
        if ($pyCmd) {
            try {
                $outDir = Split-Path -Parent $OutputPath
                if ($outDir -and -not (Test-Path $outDir)) { New-Item -ItemType Directory -Path $outDir -Force | Out-Null }
                $pyArgs = @(
                    $pyClient, "--prompt", $Prompt, "--output", $OutputPath,
                    "--negative-prompt", $NegativePrompt,
                    "--width", $Width, "--height", $Height,
                    "--steps", $Steps, "--guidance-scale", $GuidanceScale,
                    "--timeout", $script:SDHttpTimeoutSec
                )
                if ($ApiUrl) { $pyArgs += @("--api-url", "$ApiUrl/v1/images/generations") }
                Write-Host "    Using shared Python SD client (robust timeout + salvage)..." -ForegroundColor Gray
                & $pyCmd @pyArgs
                if ($LASTEXITCODE -eq 0 -and (Test-Path $OutputPath)) {
                    Write-Host "  [OK] Image generated successfully (Python client)" -ForegroundColor Green
                    return $OutputPath
                }
                Write-Host "  [WARN] Python SD client did not produce output; falling back to inline HTTP client" -ForegroundColor Yellow
            } catch {
                Write-Host "  [WARN] Python SD client failed: $_ ; falling back to inline HTTP client" -ForegroundColor Yellow
            }
        }
    }
    
    $generationStartedAt = Get-Date
    try {
        # Prepare request body (OpenAI-compatible format)
        $body = @{
            prompt = $Prompt
            negative_prompt = $NegativePrompt
            width = $Width
            height = $Height
            n = 1
            steps = $Steps
            guidance_scale = $GuidanceScale
        } | ConvertTo-Json
        
        # Generate image (generous FINITE timeout; slow-but-complete != discarded)
        $response = Invoke-RestMethod `
            -Uri "$ApiUrl/v1/images/generations" `
            -Method Post `
            -ContentType "application/json" `
            -Body $body `
            -TimeoutSec $script:SDHttpTimeoutSec `
            -ErrorAction Stop
        
        # Extract image data
        if ($response.data -and $response.data.Count -gt 0) {
            $imageData = $response.data[0].b64_json
            if (-not $imageData) {
                $imageData = $response.data[0].url
                if ($imageData) {
                    # Download from URL
                    $imageBytes = Invoke-RestMethod -Uri $imageData -Method Get
                    $imageData = [Convert]::ToBase64String($imageBytes)
                }
            }
            
            if ($imageData) {
                # Decode base64 and save
                $imageBytes = [Convert]::FromBase64String($imageData)
                [System.IO.File]::WriteAllBytes($OutputPath, $imageBytes)
                Write-Host "  [OK] Image generated successfully" -ForegroundColor Green
                return $OutputPath
            } else {
                throw "No image data in API response"
            }
        } else {
            throw "Invalid API response format: $($response | ConvertTo-Json -Depth 5)"
        }
    } catch {
        $failMsg = '  [ERROR] Image generation failed: ' + $_.ToString()
        Write-Host $failMsg -ForegroundColor Red
        if ($script:IsVerbose) {
            Write-Host "  Response: $($_.Exception.Response)" -ForegroundColor Gray
        }

        # Salvage: the server may have finished a slow generation even though the
        # HTTP client errored/timed out. Recover it from the on-disk output cache.
        try {
            if (Test-Path $script:SDOutputsDir) {
                $latest = Get-ChildItem -Path $script:SDOutputsDir -Filter "*.png" -ErrorAction SilentlyContinue |
                    Where-Object { $_.LastWriteTime -ge $generationStartedAt.AddSeconds(-5) } |
                    Sort-Object LastWriteTime -Descending | Select-Object -First 1
                if ($latest) {
                    Copy-Item -Path $latest.FullName -Destination $OutputPath -Force
                    Write-Host "  [OK] Salvaged completed SD output from server cache: $($latest.FullName)" -ForegroundColor Green
                    return $OutputPath
                }
            }
        } catch {
            # salvage best-effort only
        }

        # CUDA OOM: retry once at reduced settings rather than failing hard.
        $msgLower = $_.ToString().ToLower()
        $isOom = ($msgLower -match "out of memory") -or ($msgLower -match "cuda" -and $msgLower -match "memory") -or ($msgLower -match "oom")
        if ($isOom) {
            $redW = [Math]::Max(512, [int]($Width * 0.66))
            $redH = [Math]::Max(512, [int]($Height * 0.66))
            $redSteps = [Math]::Max(12, [int]($Steps * 0.6))
            Write-Host "  [SD] CUDA OOM detected; retrying once at ${redW}x${redH}@${redSteps}..." -ForegroundColor Yellow
            try {
                $bodyRetry = @{
                    prompt = $Prompt; negative_prompt = $NegativePrompt
                    width = $redW; height = $redH; n = 1
                    steps = $redSteps; guidance_scale = $GuidanceScale
                } | ConvertTo-Json
                $response = Invoke-RestMethod -Uri "$ApiUrl/v1/images/generations" -Method Post `
                    -ContentType "application/json" -Body $bodyRetry -TimeoutSec $script:SDHttpTimeoutSec -ErrorAction Stop
                if ($response.data -and $response.data.Count -gt 0 -and $response.data[0].b64_json) {
                    $imageBytes = [Convert]::FromBase64String($response.data[0].b64_json)
                    [System.IO.File]::WriteAllBytes($OutputPath, $imageBytes)
                    Write-Host "  [OK] Image generated at reduced settings after OOM" -ForegroundColor Green
                    return $OutputPath
                }
            } catch {
                Write-Host "  [WARN] OOM retry also failed: $_" -ForegroundColor Yellow
            }
        }
        throw
    }
}

# ============================================================
# MAIN EXECUTION
# ============================================================

Write-Host "`n=== Uncensored Character Image Generator ===" -ForegroundColor Cyan
Write-Host "Character: $CharacterName" -ForegroundColor White
Write-Host "Game Type: $GameType" -ForegroundColor White
if ($Mutations.Count -gt 0) {
    Write-Host "Mutations: $($Mutations.Count)" -ForegroundColor White
    if ($script:IsVerbose) {
        foreach ($mutation in $Mutations) {
            Write-Host "  - $mutation" -ForegroundColor Gray
        }
    }
}
if ($Traits.Count -gt 0) {
    Write-Host "Traits: $($Traits.Count)" -ForegroundColor White
    if ($script:IsVerbose) {
        foreach ($trait in $Traits) {
            Write-Host "  - $trait" -ForegroundColor Gray
        }
    }
}
Write-Host ''

# Build full description
$fullDescription = Build-CharacterDescription `
    -BaseDescription $Description `
    -Mutations $Mutations `
    -Traits $Traits `
    -GameType $GameType

# Enhance with Ollama (unless skipped)
if (-not $SkipEnhancement) {
    $enhancedDescription = Enhance-DescriptionWithOllama `
        -Description $fullDescription `
        -CharacterName $CharacterName `
        -GameType $GameType
} else {
    $enhancedDescription = $fullDescription
    Write-Host "  Skipping Ollama enhancement (using raw description)" -ForegroundColor Yellow
}

# Determine output path
if (-not $OutputPath) {
    $safeName = $CharacterName -replace '[^\w\s-]', '' -replace '\s+', '_'
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    # Use a dedicated "UncensoredCharacterImageGenerator_images" subdirectory for better organization
    $outputDir = Join-Path $PSScriptRoot "UncensoredCharacterImageGenerator_images"
    if (-not (Test-Path $outputDir)) {
        New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
        Write-Host "Created output directory: $outputDir" -ForegroundColor Gray
    }
    $OutputPath = Join-Path $outputDir "${safeName}_${timestamp}.png"
} else {
    # Ensure output directory exists if custom path provided
    $outputDir = Split-Path -Parent $OutputPath
    if (-not $outputDir) {
        $outputDir = $PSScriptRoot
        $OutputPath = Join-Path $outputDir (Split-Path -Leaf $OutputPath)
    }
    if (-not (Test-Path $outputDir)) {
        New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
    }
}

# Generate image
Write-Host ''
Write-Host 'Generating image...' -ForegroundColor Cyan
try {
    $imagePath = Generate-ImageWithStableDiffusion `
        -Prompt $enhancedDescription `
        -Width $Width `
        -Height $Height `
        -ApiUrl $StableDiffusionUrl `
        -Steps $Steps `
        -GuidanceScale $GuidanceScale `
        -OutputPath $OutputPath
    
    Write-Host ''
    Write-Host '[OK] Image generated successfully!' -ForegroundColor Green
    Write-Host ''
    Write-Host '========================================' -ForegroundColor Cyan
    Write-Host 'IMAGE SAVED TO:' -ForegroundColor Yellow
    Write-Host $imagePath -ForegroundColor White
    Write-Host '========================================' -ForegroundColor Cyan
    Write-Host ''
    
    # Show the full path and open the directory
    $outputDir = Split-Path -Parent $imagePath
    Write-Host "Output directory: $outputDir" -ForegroundColor Cyan
    Write-Host ''
    
    # Try to open the image automatically (skipped for unattended/overnight runs)
    if ((Test-Path $imagePath) -and (-not $script:NoOpen)) {
        try {
            Start-Process $imagePath
            Write-Host '  [OK] Opened image in default viewer' -ForegroundColor Green
        } catch {
            Write-Host '  [INFO] Could not auto-open image (you can open it manually)' -ForegroundColor Gray
        }
        
        # Also open the output directory in Explorer
        try {
            Start-Process explorer.exe -ArgumentList "/select,`"$imagePath`""
            Write-Host '  [OK] Opened output directory in Explorer' -ForegroundColor Green
        } catch {
            # Fallback: just open the directory
            try {
                Start-Process $outputDir
            } catch {
                Write-Host '  [INFO] Could not open output directory' -ForegroundColor Gray
            }
        }
    } elseif ($script:NoOpen) {
        Write-Host '  [INFO] Skipping auto-open (unattended mode / -NoOpen)' -ForegroundColor Gray
    }
    
    # AI Enhancement (if requested)
    if ($AIEnhancement) {
        Write-Host ''
        $enhancedImagePath = Enhance-ImageWithAI `
            -ImagePath $imagePath `
            -OriginalPrompt $enhancedDescription `
            -CharacterName $CharacterName `
            -GameType $GameType `
            -Width $Width `
            -Height $Height `
            -OllamaUrl $OllamaUrl `
            -StableDiffusionUrl $StableDiffusionUrl `
            -RegenerateImproved:$RegenerateImproved `
            -Verbose:$script:IsVerbose
        
        if ($enhancedImagePath -ne $imagePath) {
            $imagePath = $enhancedImagePath
            $enhancedMsg = '  Using AI-enhanced image: ' + $imagePath
            Write-Host $enhancedMsg -ForegroundColor Cyan
        }
    }
    
    # Save metadata
    $metadataPath = $OutputPath -replace '\.png$', '_metadata.json'
    $metadata = @{
        CharacterName = $CharacterName
        GameType = $GameType
        Mutations = $Mutations
        Traits = $Traits
        OriginalDescription = $Description
        EnhancedDescription = $enhancedDescription
        Dimensions = @{
            Width = $Width
            Height = $Height
        }
        GeneratedAt = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
        AIEnhanced = $AIEnhancement
        Regenerated = $RegenerateImproved
        Notes = 'Generated with uncensored routing system - handles any content that might be blocked'
    }
    $metadata | ConvertTo-Json -Depth 10 | Set-Content -Path $metadataPath -Encoding UTF8
    if ($script:IsVerbose) {
        $metaMsg = '  Metadata: ' + $metadataPath
        Write-Host $metaMsg -ForegroundColor Gray
    }
    
    Write-Host ''
    Write-Host 'Summary:' -ForegroundColor Cyan
    Write-Host "  Image: $imagePath" -ForegroundColor White
    Write-Host "  Metadata: $metadataPath" -ForegroundColor White
    if ($AIEnhancement) {
        $analysisPath = $imagePath -replace '\.png$', '_ai_analysis.txt'
        if (Test-Path $analysisPath) {
            Write-Host "  AI Analysis: $analysisPath" -ForegroundColor White
        }
    }
    Write-Host ''
    
} catch {
    Write-Host ''
    $errorMsg = '[ERROR] Failed to generate image: ' + $_.ToString()
    Write-Host $errorMsg -ForegroundColor Red
    Write-Host ''
    $troubleMsg = 'Troubleshooting:'
    Write-Host $troubleMsg -ForegroundColor Yellow
    $msg1 = '  1. Ensure Stable Diffusion API is running at: ' + $StableDiffusionUrl
    Write-Host $msg1 -ForegroundColor Gray
    $docUrl = $StableDiffusionUrl + '/docs'
    $msg2 = '  2. Check API documentation: ' + $docUrl
    Write-Host $msg2 -ForegroundColor Gray
    $endpointMsg = '  3. Verify the API endpoint supports /v1/images/generations'
    Write-Host $endpointMsg -ForegroundColor Gray
    $setupUrl = 'https://github.com/cantrell/stable-diffusion-api-server'
    $msg4 = '  4. For local setup, see: ' + $setupUrl
    Write-Host $msg4 -ForegroundColor Gray
    Write-Host ''
    $noteMsg = 'Note: This tool uses uncensored routing to handle ANY content that might be blocked.'
    Write-Host $noteMsg -ForegroundColor Cyan
    $tierNote = '      If Ollama refused the description, it was automatically escalated to Tier 3.'
    Write-Host $tierNote -ForegroundColor DarkGray
    exit 1
}

Write-Host ''
