#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate assets for the Magic Orb weapon system.
    
.DESCRIPTION
    Generates assets for:
    - Magic Orb sprites and animations
    - Orb mod variants (20+ types)
    - UI elements (9-slot panel, hotkey indicators)

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}
    - VFX particles for orb effects
    - Sound effects
    - Status effect icons
    
.PARAMETER ModPath
    Path to the mod directory
    
.PARAMETER OllamaModel
    Ollama model to use
    
.PARAMETER PlanningModel
    Planning model for Ollama
    
.PARAMETER VisualModel
    Visual model for Ollama
    
.PARAMETER UseCppBackend
    Use C++ backend for generation
    
.PARAMETER SkipExisting
    Skip assets that already exist
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$ModPath = "F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery",
    
    [Parameter(Mandatory=$false)]
    [string]$OllamaModel = "codellama:7b-instruct",
    
    [Parameter(Mandatory=$false)]
    [string]$PlanningModel = "",
    
    [Parameter(Mandatory=$false)]
    [string]$VisualModel = "wizardlm-uncensored",
    
    [Parameter(Mandatory=$false)]
    [bool]$UseCppBackend = $true,
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipExisting
)

$ErrorActionPreference = "Continue"  # Changed from "Stop" to continue on errors and report them
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$assetGenerator = Join-Path $PSScriptRoot "StarboundOllamaAssetGenerator.ps1"

# Validate ModPath is not empty
if ([string]::IsNullOrWhiteSpace($ModPath)) {
    Write-Host "Error: ModPath cannot be empty" -ForegroundColor Red
    Write-Host "  Please provide a valid mod path or use the default" -ForegroundColor Gray
    exit 1
}

# Verify asset generator exists
if (-not (Test-Path $assetGenerator)) {
    Write-Host "[ERROR] Asset generator script not found: $assetGenerator" -ForegroundColor Red
    Write-Host "Please ensure StarboundOllamaAssetGenerator.ps1 exists in the script directory." -ForegroundColor Yellow
    exit 1
}

# Ensure output directories exist
# Validate $ModPath before Join-Path
$outputBase = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($outputBase)) {
    Write-Host "  [FAIL] outputBase is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($outputBase)) {
    Write-Host "  [FAIL] outputBase is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if ([string]::IsNullOrWhiteSpace($outputBase)) {
    Write-Host "Error: Cannot create output base directory: ModPath resulted in null path" -ForegroundColor Red
    exit 1
}
$directories = @(
    (Join-Path $outputBase "items\sprites"),
    (Join-Path $outputBase "projectiles"),
    (Join-Path $outputBase "animations\magitech"),
    (Join-Path $outputBase "interface\icons"),
    (Join-Path $outputBase "particles\magitech"),
    (Join-Path $outputBase "sfx"),
    (Join-Path $outputBase "status\icons")
)

foreach ($dir in $directories) {
    if ([string]::IsNullOrWhiteSpace($dir)) {
        Write-Host "Warning: Skipping null directory path" -ForegroundColor Yellow
        continue
    }
    if (-not (Test-Path $dir)) {
        try {
            Write-Host "Creating directory: $dir" -ForegroundColor Gray
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
        } catch {
            Write-Host "Error: Cannot create directory '$dir': $_" -ForegroundColor Red
        }
    }
}

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Magic Orb Weapon System Asset Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$generated = 0
$failed = 0
$skipped = 0

# Generate base Magic Orb sprites
Write-Host "Generating Base Magic Orb Sprites..." -ForegroundColor Yellow
Write-Host ""

$orbBaseTypes = @(
    @{Id="magicOrb"; Name="Magic Orb"; Desc="Base magical orb, glowing energy sphere, 32x32 pixels"},
    @{Id="magicOrb_orbital"; Name="Orbital Orb"; Desc="Orb in orbital mode, circling caster, 32x32 pixels"},
    @{Id="magicOrb_charging"; Name="Charging Orb"; Desc="Orb in charging mode, building energy, 32x32 pixels"},
    @{Id="magicOrb_powered"; Name="Powered Orb"; Desc="Orb in powered mode, enhanced glow, 32x32 pixels"},
    @{Id="magicOrb_returning"; Name="Returning Orb"; Desc="Orb returning to caster, energy trail, 32x32 pixels"}
)

foreach ($orb in $orbBaseTypes) {
    # Validate $ModPath before Join-Path
$spritePath = Join-Path $ModPath "assets\items\sprites\${orb.Id}.png"
 if ([string]::IsNullOrWhiteSpace($spritePath)) {
        Write-Host "  [FAIL] spritePath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
 if ([string]::IsNullOrWhiteSpace($spritePath)) {
        Write-Host "  [FAIL] spritePath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
    if ($SkipExisting -and (Test-Path $spritePath)) {
        $skipped++
        Write-Host "  [SKIP] Orb sprite already exists: $($orb.Id)" -ForegroundColor Gray
    } else {
        try {
            # Validate $ModPath before Join-Path
$targetDir = Join-Path $ModPath "assets\items\sprites"
 if ([string]::IsNullOrWhiteSpace($targetDir)) {
                Write-Host "  [FAIL] targetDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                continue
            }
 if ([string]::IsNullOrWhiteSpace($targetDir)) {
                Write-Host "  [FAIL] targetDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                continue
            }
            $params = @{
                AssetType = "ItemSprite"
                AssetName = $orb.Id
                Prompt = "A magic orb sprite: $($orb.Name) - $($orb.Desc). Magical energy sphere"
                OllamaModel = $OllamaModel
                OutputDir = $targetDir
            }
            if ($PlanningModel) { $params['PlanningModel'] = $PlanningModel }
            if ($VisualModel) { $params['VisualModel'] = $VisualModel }
            $params['UseCppBackend'] = $UseCppBackend
            
            & $assetGenerator @params | Out-Null
            
            # Move file to correct location if needed
            $generatedFile = Join-Path $targetDir "${orb.Id}.png"
            if (-not (Test-Path $generatedFile)) {
                # Check if file was generated in OutputDir root
                $rootFile = Join-Path (Join-Path $ModPath "assets") "${orb.Id}.png"
                if (Test-Path $rootFile) {
                    Move-Item -Path $rootFile -Destination $generatedFile -Force
                }
            }
            
            $generated++
            Write-Host "  [OK] Generated orb sprite: $($orb.Id)" -ForegroundColor Green
        } catch {
            $failed++
            Write-Host "  [FAIL] Orb sprite $($orb.Id) : $_" -ForegroundColor Red
        }
    }
}

Write-Host ""

# Generate orb mod projectile sprites
Write-Host "Generating Orb Mod Projectiles..." -ForegroundColor Yellow
Write-Host ""

$orbMods = @(
    @{Id="splinterOrb"; Name="Splinter Orb"; Element="crystal"; Desc="Shatters into multiple shards on impact"},
    @{Id="clusterOrb"; Name="Cluster Orb"; Element="explosive"; Desc="Fires volley of mini-orbs in cone"},
    @{Id="poisonOrb"; Name="Poison Orb"; Element="poison"; Desc="Leaves lingering acid pool on hit"},
    @{Id="frostOrb"; Name="Frost Orb"; Element="ice"; Desc="Freezes and slows targets in radius"},
    @{Id="phaseOrb"; Name="Phase Orb"; Element="void"; Desc="Pierces through enemies, multiple hits"},
    @{Id="blackHoleOrb"; Name="Black Hole Orb"; Element="void"; Desc="Creates temporary singularity pulling enemies"},
    @{Id="spikeOrb"; Name="Spike Orb"; Element="earth"; Desc="Orbiting spines damaging nearby enemies"},
    @{Id="teleportOrb"; Name="Teleport Orb"; Element="void"; Desc="Teleports caster to orb position"},
    @{Id="healingPulseOrb"; Name="Healing Pulse Orb"; Element="nature"; Desc="Burst of healing energy around caster"},
    @{Id="manaSiphonOrb"; Name="Mana Siphon Orb"; Element="arcane"; Desc="Drains mana from enemies to caster"},
    @{Id="shockwaveOrb"; Name="Shockwave Orb"; Element="electric"; Desc="Radial blast with knockback"},
    @{Id="bindingOrb"; Name="Binding Orb"; Element="earth"; Desc="Roots targets preventing movement"},
    @{Id="leechOrb"; Name="Leech Orb"; Element="poison"; Desc="Drains health and heals caster"},
    @{Id="levityOrb"; Name="Levity Orb"; Element="air"; Desc="Creates updraft lifting enemies"},
    @{Id="stickyOrb"; Name="Sticky Orb"; Element="poison"; Desc="Sticks to surface pulsing AoE damage"},
    @{Id="mirrorOrb"; Name="Mirror Orb"; Element="arcane"; Desc="Reflective barrier around caster"},
    @{Id="prismOrb"; Name="Prism Orb"; Element="crystal"; Desc="Splits into multiple shards at angles"},
    @{Id="berserkOrb"; Name="Berserk Orb"; Element="fire"; Desc="Buffs allies with attack speed"},
    @{Id="aetherialOrb"; Name="Aetherial Orb"; Element="void"; Desc="Phases caster through obstacles"},
    @{Id="nullOrb"; Name="Nullification Orb"; Element="arcane"; Desc="Dispels buffs from enemies"}
)

foreach ($mod in $orbMods) {
    # Validate $ModPath before Join-Path
$spritePath = Join-Path $ModPath "assets\projectiles\${mod.Id}.png"
 if ([string]::IsNullOrWhiteSpace($spritePath)) {
        Write-Host "  [FAIL] spritePath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
 if ([string]::IsNullOrWhiteSpace($spritePath)) {
        Write-Host "  [FAIL] spritePath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
    if ($SkipExisting -and (Test-Path $spritePath)) {
        $skipped++
        Write-Host "  [SKIP] Orb mod sprite already exists: $($mod.Id)" -ForegroundColor Gray
    } else {
        try {
            # Validate $ModPath before Join-Path
$targetDir = Join-Path $ModPath "assets\projectiles"
 if ([string]::IsNullOrWhiteSpace($targetDir)) {
                Write-Host "  [FAIL] targetDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                continue
            }
 if ([string]::IsNullOrWhiteSpace($targetDir)) {
                Write-Host "  [FAIL] targetDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                continue
            }
            $params = @{
                AssetType = "Projectile"
                AssetName = $mod.Id
                Prompt = "A projectile sprite: $($mod.Name) - $($mod.Desc). $($mod.Element) elemental orb variant, 32x32 pixels"
                OllamaModel = $OllamaModel
                OutputDir = $targetDir
            }
            if ($PlanningModel) { $params['PlanningModel'] = $PlanningModel }
            if ($VisualModel) { $params['VisualModel'] = $VisualModel }
            $params['UseCppBackend'] = $UseCppBackend
            
            & $assetGenerator @params | Out-Null
            
            # Move file to correct location if needed
            $generatedFile = Join-Path $targetDir "${mod.Id}.png"
            if (-not (Test-Path $generatedFile)) {
                # Check if file was generated in OutputDir root
                $rootFile = Join-Path (Join-Path $ModPath "assets") "${mod.Id}.png"
                if (Test-Path $rootFile) {
                    Move-Item -Path $rootFile -Destination $generatedFile -Force
                }
            }
            
            $generated++
            Write-Host "  [OK] Generated orb mod: $($mod.Id)" -ForegroundColor Green
        } catch {
            $failed++
            Write-Host "  [FAIL] Orb mod $($mod.Id) : $_" -ForegroundColor Red
        }
    }
}

Write-Host ""

# Generate orb animation sprites
Write-Host "Generating Orb Animation Sprites..." -ForegroundColor Yellow
Write-Host ""

$orbAnimations = @(
    @{Id="magicOrb_orbital_animated"; Name="Orbital Animation"; Frames=8; Desc="Orb circling caster, smooth orbit animation"},
    @{Id="magicOrb_charging_animated"; Name="Charging Animation"; Frames=6; Desc="Orb building energy, pulsing glow"},
    @{Id="magicOrb_pulse_animated"; Name="Pulse Animation"; Frames=4; Desc="Orb pulsing energy, firing pulses"},
    @{Id="magicOrb_return_animated"; Name="Return Animation"; Frames=6; Desc="Orb returning to caster, energy trail"}
)

foreach ($anim in $orbAnimations) {
    # Validate $ModPath before Join-Path
$animPath = Join-Path $ModPath "assets\animations\magitech\${anim.Id}.animation"
 if ([string]::IsNullOrWhiteSpace($animPath)) {
        Write-Host "  [FAIL] animPath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
 if ([string]::IsNullOrWhiteSpace($animPath)) {
        Write-Host "  [FAIL] animPath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
    if ($SkipExisting -and (Test-Path $animPath)) {
        $skipped++
        Write-Host "  [SKIP] Animation already exists: $($anim.Id)" -ForegroundColor Gray
    } else {
        try {
            # Validate $ModPath before Join-Path
$targetDir = Join-Path $ModPath "assets\animations\magitech"
 if ([string]::IsNullOrWhiteSpace($targetDir)) {
                Write-Host "  [FAIL] targetDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                continue
            }
 if ([string]::IsNullOrWhiteSpace($targetDir)) {
                Write-Host "  [FAIL] targetDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                continue
            }
            $params = @{
                AssetType = "AnimationSprite"
                AssetName = $anim.Id
                Prompt = "An animation spritesheet: $($anim.Name) - $($anim.Desc). $($anim.Frames) frames, 32x32 pixels per frame, horizontal spritesheet"
                OllamaModel = $OllamaModel
                OutputDir = $targetDir
            }
            if ($PlanningModel) { $params['PlanningModel'] = $PlanningModel }
            if ($VisualModel) { $params['VisualModel'] = $VisualModel }
            $params['UseCppBackend'] = $UseCppBackend
            
            # Add animation-specific parameters
            $animParams = @{
                FrameCount = $anim.Frames
                FrameWidth = 32
                FrameHeight = 32
                AnimationCycle = if ($anim.Frames -le 4) { 0.3 } else { 0.5 }
                AnimationType = "OrbAction"
            }
            $params['Parameters'] = $animParams
            
            & $assetGenerator @params | Out-Null
            
            # Move file to correct location if needed
            $generatedFile = Join-Path $targetDir "${anim.Id}.png"
            if (-not (Test-Path $generatedFile)) {
                # Check if file was generated in OutputDir root
                $rootFile = Join-Path (Join-Path $ModPath "assets") "${anim.Id}.png"
                if (Test-Path $rootFile) {
                    Move-Item -Path $rootFile -Destination $generatedFile -Force
                }
            }
            
            $generated++
            Write-Host "  [OK] Generated animation: $($anim.Id)" -ForegroundColor Green
        } catch {
            $failed++
            Write-Host "  [FAIL] Animation $($anim.Id) : $_" -ForegroundColor Red
        }
    }
}

Write-Host ""

# Generate UI elements for 9-slot system
Write-Host "Generating Orb UI Elements..." -ForegroundColor Yellow
Write-Host ""

$orbUI = @(
    @{Id="orb_slot1"; Name="Orb Slot 1"; Desc="First orb mod slot, 48x48 pixels"},
    @{Id="orb_slot2"; Name="Orb Slot 2"; Desc="Second orb mod slot, 48x48 pixels"},
    @{Id="orb_slot3"; Name="Orb Slot 3"; Desc="Third orb mod slot, 48x48 pixels"},
    @{Id="orb_slot4"; Name="Orb Slot 4"; Desc="Fourth orb mod slot, 48x48 pixels"},
    @{Id="orb_slot5"; Name="Orb Slot 5"; Desc="Fifth orb mod slot, 48x48 pixels"},
    @{Id="orb_slot6"; Name="Orb Slot 6"; Desc="Sixth orb mod slot, 48x48 pixels"},
    @{Id="orb_slot7"; Name="Orb Slot 7"; Desc="Seventh orb mod slot, 48x48 pixels"},
    @{Id="orb_slot8"; Name="Orb Slot 8"; Desc="Eighth orb mod slot, 48x48 pixels"},
    @{Id="orb_slot9"; Name="Orb Slot 9"; Desc="Ninth orb mod slot, 48x48 pixels"},
    @{Id="orb_slot_active"; Name="Active Slot Indicator"; Desc="Indicator for currently active orb mod slot, highlight"},
    @{Id="orb_slot_empty"; Name="Empty Slot"; Desc="Empty orb mod slot, placeholder frame"},
    @{Id="orb_powerHotkey"; Name="Power Hotkey Indicator"; Desc="Indicator for orb power hotkey, glowing key icon"},
    @{Id="orb_cycleHotkey"; Name="Cycle Hotkey Indicator"; Desc="Indicator for orb cycle hotkey, arrow icon"},
    @{Id="orb_throwHotkey"; Name="Throw Hotkey Indicator"; Desc="Indicator for orb throw hotkey, throw icon"},
    @{Id="orb_manaDrainBar"; Name="Mana Drain Bar"; Desc="Mana drain gauge when orb is powered, horizontal bar"},
    @{Id="orb_chargeBar"; Name="Charge Bar"; Desc="Charge bar for throw charging, horizontal bar"},
    @{Id="orb_orbitalReticle"; Name="Orbital Reticle"; Desc="Reticle showing orb orbital path, circular indicator"},
    @{Id="orb_modPreview"; Name="Mod Preview"; Desc="Preview icon showing active mod effect, small icon"}
)

foreach ($ui in $orbUI) {
    # Validate $ModPath before Join-Path
$iconPath = Join-Path $ModPath "assets\interface\icons\${ui.Id}.png"
 if ([string]::IsNullOrWhiteSpace($iconPath)) {
        Write-Host "  [FAIL] iconPath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
 if ([string]::IsNullOrWhiteSpace($iconPath)) {
        Write-Host "  [FAIL] iconPath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
    if ($SkipExisting -and (Test-Path $iconPath)) {
        $skipped++
        Write-Host "  [SKIP] UI element already exists: $($ui.Id)" -ForegroundColor Gray
    } else {
        try {
            # Validate $ModPath before Join-Path
$targetDir = Join-Path $ModPath "assets\interface\icons"
 if ([string]::IsNullOrWhiteSpace($targetDir)) {
                Write-Host "  [FAIL] targetDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                continue
            }
 if ([string]::IsNullOrWhiteSpace($targetDir)) {
                Write-Host "  [FAIL] targetDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                continue
            }
            $params = @{
                AssetType = "Icon"
                AssetName = $ui.Id
                Prompt = "A UI element: $($ui.Name) - $($ui.Desc). Clean interface style, appropriate size"
                OllamaModel = $OllamaModel
                OutputDir = $targetDir
            }
            if ($PlanningModel) { $params['PlanningModel'] = $PlanningModel }
            if ($VisualModel) { $params['VisualModel'] = $VisualModel }
            $params['UseCppBackend'] = $UseCppBackend
            
            & $assetGenerator @params | Out-Null
            
            # Move file to correct location if needed
            $generatedFile = Join-Path $targetDir "${ui.Id}.png"
            if (-not (Test-Path $generatedFile)) {
                # Check if file was generated in OutputDir root
                $rootFile = Join-Path (Join-Path $ModPath "assets") "${ui.Id}.png"
                if (Test-Path $rootFile) {
                    Move-Item -Path $rootFile -Destination $generatedFile -Force
                }
            }
            
            $generated++
            Write-Host "  [OK] Generated UI element: $($ui.Id)" -ForegroundColor Green
        } catch {
            $failed++
            Write-Host "  [FAIL] UI element $($ui.Id) : $_" -ForegroundColor Red
        }
    }
}

Write-Host ""

# Generate VFX particles for orb effects
Write-Host "Generating Orb VFX Particles..." -ForegroundColor Yellow
Write-Host ""

$orbParticles = @(
    @{Id="orb_orbital_trail"; Name="Orbital Trail"; Type="Magic"; Desc="Energy trail from orbiting orb"},
    @{Id="orb_charging_glow"; Name="Charging Glow"; Type="Magic"; Desc="Glowing energy buildup when charging"},
    @{Id="orb_powered_aura"; Name="Powered Aura"; Type="Magic"; Desc="Enhanced aura when orb is powered"},
    @{Id="orb_pulse_burst"; Name="Pulse Burst"; Type="Electric"; Desc="Energy burst when orb pulses"},
    @{Id="orb_return_trail"; Name="Return Trail"; Type="Magic"; Desc="Energy trail when orb returns to caster"},
    @{Id="orb_splinter_shards"; Name="Splinter Shards"; Type="Crystal"; Desc="Shard particles from splinter orb"},
    @{Id="orb_cluster_minis"; Name="Cluster Minis"; Type="Explosion"; Desc="Mini-orb particles from cluster orb"},
    @{Id="orb_poison_pool"; Name="Poison Pool"; Type="Poison"; Desc="Acid pool particles from poison orb"},
    @{Id="orb_frost_cloud"; Name="Frost Cloud"; Type="Ice"; Desc="Freezing cloud from frost orb"},
    @{Id="orb_phase_trail"; Name="Phase Trail"; Type="Void"; Desc="Phase trail from phase orb"},
    @{Id="orb_blackhole_singularity"; Name="Black Hole Singularity"; Type="Void"; Desc="Singularity effect from black hole orb"},
    @{Id="orb_spike_spines"; Name="Spike Spines"; Type="Earth"; Desc="Spike particles from spike orb"},
    @{Id="orb_teleport_effect"; Name="Teleport Effect"; Type="Void"; Desc="Teleportation effect particles"},
    @{Id="orb_healing_burst"; Name="Healing Burst"; Type="Magic"; Desc="Healing energy burst particles"},
    @{Id="orb_mana_siphon"; Name="Mana Siphon"; Type="Arcane"; Desc="Mana drain effect particles"},
    @{Id="orb_shockwave_ring"; Name="Shockwave Ring"; Type="Electric"; Desc="Shockwave ring particles"},
    @{Id="orb_binding_chains"; Name="Binding Chains"; Type="Earth"; Desc="Binding chain particles"},
    @{Id="orb_leech_tendrils"; Name="Leech Tendrils"; Type="Poison"; Desc="Leech effect tendrils"},
    @{Id="orb_levity_updraft"; Name="Levity Updraft"; Type="Air"; Desc="Updraft particles from levity orb"},
    @{Id="orb_sticky_goo"; Name="Sticky Goo"; Type="Poison"; Desc="Sticky goo particles"},
    @{Id="orb_mirror_barrier"; Name="Mirror Barrier"; Type="Arcane"; Desc="Reflective barrier particles"},
    @{Id="orb_prism_split"; Name="Prism Split"; Type="Crystal"; Desc="Prism split effect particles"},
    @{Id="orb_berserk_aura"; Name="Berserk Aura"; Type="Fire"; Desc="Berserk buff aura particles"},
    @{Id="orb_aetherial_phase"; Name="Aetherial Phase"; Type="Void"; Desc="Phase effect particles"},
    @{Id="orb_null_dispel"; Name="Null Dispel"; Type="Arcane"; Desc="Dispel effect particles"}
)

foreach ($particle in $orbParticles) {
    # Validate $ModPath before Join-Path
$particlePath = Join-Path $ModPath "assets\particles\magitech\${particle.Id}.particle"
 if ([string]::IsNullOrWhiteSpace($particlePath)) {
        Write-Host "  [FAIL] particlePath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
 if ([string]::IsNullOrWhiteSpace($particlePath)) {
        Write-Host "  [FAIL] particlePath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
    if ($SkipExisting -and (Test-Path $particlePath)) {
        $skipped++
        Write-Host "  [SKIP] Particle already exists: $($particle.Id)" -ForegroundColor Gray
    } else {
        try {
            # Validate $ModPath before Join-Path
$targetDir = Join-Path $ModPath "assets\particles\magitech"
 if ([string]::IsNullOrWhiteSpace($targetDir)) {
                Write-Host "  [FAIL] targetDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                continue
            }
 if ([string]::IsNullOrWhiteSpace($targetDir)) {
                Write-Host "  [FAIL] targetDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                continue
            }
            $params = @{
                AssetType = "Particle"
                AssetName = $particle.Id
                Prompt = "A particle effect: $($particle.Name) - $($particle.Desc). $($particle.Type) type effect"
                OllamaModel = $OllamaModel
                OutputDir = $targetDir
            }
            if ($PlanningModel) { $params['PlanningModel'] = $PlanningModel }
            if ($VisualModel) { $params['VisualModel'] = $VisualModel }
            $params['UseCppBackend'] = $UseCppBackend
            
            & $assetGenerator @params | Out-Null
            
            # Move file to correct location if needed
            $generatedFile = Join-Path $targetDir "${particle.Id}.particle"
            if (-not (Test-Path $generatedFile)) {
                # Check if file was generated in OutputDir root
                $rootFile = Join-Path (Join-Path $ModPath "assets") "${particle.Id}.particle"
                if (Test-Path $rootFile) {
                    Move-Item -Path $rootFile -Destination $generatedFile -Force
                }
            }
            
            $generated++
            Write-Host "  [OK] Generated particle: $($particle.Id)" -ForegroundColor Green
        } catch {
            $failed++
            Write-Host "  [FAIL] Particle $($particle.Id) : $_" -ForegroundColor Red
        }
    }
}

Write-Host ""

# Generate sound effects
Write-Host "Generating Orb Sound Effects..." -ForegroundColor Yellow
Write-Host ""

$orbSounds = @(
    @{Id="orb_spawn"; Type="Magic"; Desc="Sound when orb spawns, magical materialization"},
    @{Id="orb_orbital_loop"; Type="Ambient"; Desc="Ambient sound for orbiting orb, continuous hum"},
    @{Id="orb_pulse"; Type="Electric"; Desc="Sound when orb pulses, energy burst"},
    @{Id="orb_charge"; Type="Magic"; Desc="Sound when charging orb, building energy"},
    @{Id="orb_powered"; Type="Magic"; Desc="Sound when orb enters powered mode, enhanced energy"},
    @{Id="orb_throw"; Type="Impact"; Desc="Sound when throwing orb, launch whoosh"},
    @{Id="orb_return"; Type="Magic"; Desc="Sound when orb returns, magical return"},
    @{Id="orb_cycle"; Type="Mechanical"; Desc="Sound when cycling orb mods, mechanical click"},
    @{Id="orb_splinter"; Type="Crystal"; Desc="Sound when splinter orb shatters, crystal break"},
    @{Id="orb_cluster"; Type="Explosion"; Desc="Sound when cluster orb fires, volley sound"},
    @{Id="orb_poison_hit"; Type="Poison"; Desc="Sound when poison orb hits, toxic impact"},
    @{Id="orb_frost_freeze"; Type="Ice"; Desc="Sound when frost orb freezes, ice crack"},
    @{Id="orb_phase_pierce"; Type="Void"; Desc="Sound when phase orb pierces, void effect"},
    @{Id="orb_blackhole_pull"; Type="Void"; Desc="Sound when black hole orb pulls, gravitational effect"},
    @{Id="orb_spike_contact"; Type="Earth"; Desc="Sound when spike orb contacts enemy, spike hit"},
    @{Id="orb_teleport"; Type="Void"; Desc="Sound when teleport orb activates, teleportation"},
    @{Id="orb_healing_pulse"; Type="Magic"; Desc="Sound when healing orb pulses, healing energy"},
    @{Id="orb_mana_siphon"; Type="Arcane"; Desc="Sound when mana siphon orb drains, mana drain"},
    @{Id="orb_shockwave"; Type="Electric"; Desc="Sound when shockwave orb explodes, shockwave"},
    @{Id="orb_binding"; Type="Earth"; Desc="Sound when binding orb roots, binding effect"},
    @{Id="orb_leech"; Type="Poison"; Desc="Sound when leech orb drains, leech effect"},
    @{Id="orb_levity"; Type="Air"; Desc="Sound when levity orb creates updraft, air whoosh"},
    @{Id="orb_sticky"; Type="Poison"; Desc="Sound when sticky orb sticks, sticky impact"},
    @{Id="orb_mirror"; Type="Arcane"; Desc="Sound when mirror orb reflects, reflective barrier"},
    @{Id="orb_prism_split"; Type="Crystal"; Desc="Sound when prism orb splits, crystal split"},
    @{Id="orb_berserk"; Type="Fire"; Desc="Sound when berserk orb buffs, berserk activation"},
    @{Id="orb_aetherial"; Type="Void"; Desc="Sound when aetherial orb phases, phase effect"},
    @{Id="orb_null"; Type="Arcane"; Desc="Sound when null orb dispels, dispel effect"}
)

foreach ($sound in $orbSounds) {
    # Validate $ModPath before Join-Path
$soundPath = Join-Path $ModPath "assets\sfx\${sound.Id}.ogg"
 if ([string]::IsNullOrWhiteSpace($soundPath)) {
        Write-Host "  [FAIL] soundPath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
 if ([string]::IsNullOrWhiteSpace($soundPath)) {
        Write-Host "  [FAIL] soundPath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
    if ($SkipExisting -and (Test-Path $soundPath)) {
        $skipped++
        Write-Host "  [SKIP] Sound already exists: $($sound.Id)" -ForegroundColor Gray
    } else {
        try {
            # Validate $ModPath before Join-Path
$targetDir = Join-Path $ModPath "assets\sfx"
 if ([string]::IsNullOrWhiteSpace($targetDir)) {
                Write-Host "  [FAIL] targetDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                continue
            }
 if ([string]::IsNullOrWhiteSpace($targetDir)) {
                Write-Host "  [FAIL] targetDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                continue
            }
            $params = @{
                AssetType = "Sound"
                AssetName = $sound.Id
                Prompt = "A sound effect: $($sound.Desc). $($sound.Type) type sound"
                OllamaModel = $OllamaModel
                OutputDir = $targetDir
            }
            if ($PlanningModel) { $params['PlanningModel'] = $PlanningModel }
            if ($VisualModel) { $params['VisualModel'] = $VisualModel }
            $params['UseCppBackend'] = $UseCppBackend
            
            # Add sound-specific parameters
            $soundParams = @{
                SoundType = $sound.Type
                Format = "ogg"
            }
            $params['Parameters'] = $soundParams
            
            & $assetGenerator @params | Out-Null
            
            # Move file to correct location if needed
            $generatedFile = Join-Path $targetDir "${sound.Id}.ogg"
            if (-not (Test-Path $generatedFile)) {
                # Check if file was generated in OutputDir root
                $rootFile = Join-Path (Join-Path $ModPath "assets") "${sound.Id}.ogg"
                if (Test-Path $rootFile) {
                    Move-Item -Path $rootFile -Destination $generatedFile -Force
                }
            }
            
            $generated++
            Write-Host "  [OK] Generated sound: $($sound.Id)" -ForegroundColor Green
        } catch {
            $failed++
            Write-Host "  [FAIL] Sound $($sound.Id) : $_" -ForegroundColor Red
        }
    }
}

Write-Host ""

# Generate status effect icons
Write-Host "Generating Orb Status Effect Icons..." -ForegroundColor Yellow
Write-Host ""

$orbStatusEffects = @(
    @{Id="orb_powered"; Name="Orb Powered"; Desc="Orb in powered mode status, enhanced energy icon"},
    @{Id="orb_charging"; Name="Orb Charging"; Desc="Orb charging status, building energy icon"},
    @{Id="orb_orbital"; Name="Orb Orbital"; Desc="Orb in orbital mode status, circling icon"},
    @{Id="orb_mod_active"; Name="Orb Mod Active"; Desc="Active orb mod status, mod indicator"},
    @{Id="orb_mana_drain"; Name="Mana Drain"; Desc="Mana drain active status, drain indicator"},
    @{Id="orb_returning"; Name="Orb Returning"; Desc="Orb returning status, return indicator"}
)

foreach ($status in $orbStatusEffects) {
    # Validate $ModPath before Join-Path
$iconPath = Join-Path $ModPath "assets\status\icons\${status.Id}.png"
 if ([string]::IsNullOrWhiteSpace($iconPath)) {
        Write-Host "  [FAIL] iconPath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
 if ([string]::IsNullOrWhiteSpace($iconPath)) {
        Write-Host "  [FAIL] iconPath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
    if ($SkipExisting -and (Test-Path $iconPath)) {
        $skipped++
        Write-Host "  [SKIP] Status icon already exists: $($status.Id)" -ForegroundColor Gray
    } else {
        try {
            # Validate $ModPath before Join-Path
$targetDir = Join-Path $ModPath "assets\status\icons"
 if ([string]::IsNullOrWhiteSpace($targetDir)) {
                Write-Host "  [FAIL] targetDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                continue
            }
 if ([string]::IsNullOrWhiteSpace($targetDir)) {
                Write-Host "  [FAIL] targetDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                continue
            }
            $params = @{
                AssetType = "Icon"
                AssetName = "${status.Id}_status"
                Prompt = "A status effect icon: $($status.Name) - $($status.Desc). Status effect style, 32x32 pixels"
                OllamaModel = $OllamaModel
                OutputDir = $targetDir
            }
            if ($PlanningModel) { $params['PlanningModel'] = $PlanningModel }
            if ($VisualModel) { $params['VisualModel'] = $VisualModel }
            $params['UseCppBackend'] = $UseCppBackend
            
            & $assetGenerator @params | Out-Null
            
            # Move file to correct location if needed
            $generatedFile = Join-Path $targetDir "${status.Id}_status.png"
            if (-not (Test-Path $generatedFile)) {
                # Check if file was generated in OutputDir root
                $rootFile = Join-Path (Join-Path $ModPath "assets") "${status.Id}_status.png"
                if (Test-Path $rootFile) {
                    Move-Item -Path $rootFile -Destination $generatedFile -Force
                }
            }
            
            $generated++
            Write-Host "  [OK] Generated status icon: $($status.Id)" -ForegroundColor Green
        } catch {
            $failed++
            Write-Host "  [FAIL] Status icon $($status.Id) : $_" -ForegroundColor Red
        }
    }
}

Write-Host ""

# Generate mod icons for each orb mod type
Write-Host "Generating Orb Mod Icons..." -ForegroundColor Yellow
Write-Host ""

foreach ($mod in $orbMods) {
    # Validate $ModPath before Join-Path
$iconPath = Join-Path $ModPath "assets\interface\icons\${mod.Id}_icon.png"
 if ([string]::IsNullOrWhiteSpace($iconPath)) {
        Write-Host "  [FAIL] iconPath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
 if ([string]::IsNullOrWhiteSpace($iconPath)) {
        Write-Host "  [FAIL] iconPath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
    if ($SkipExisting -and (Test-Path $iconPath)) {
        $skipped++
        Write-Host "  [SKIP] Mod icon already exists: $($mod.Id)" -ForegroundColor Gray
    } else {
        try {
            # Validate $ModPath before Join-Path
$targetDir = Join-Path $ModPath "assets\interface\icons"
 if ([string]::IsNullOrWhiteSpace($targetDir)) {
                Write-Host "  [FAIL] targetDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                continue
            }
 if ([string]::IsNullOrWhiteSpace($targetDir)) {
                Write-Host "  [FAIL] targetDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                continue
            }
            $params = @{
                AssetType = "Icon"
                AssetName = "${mod.Id}_icon"
                Prompt = "An icon for orb mod: $($mod.Name) - $($mod.Desc). $($mod.Element) elemental mod icon, 32x32 pixels"
                OllamaModel = $OllamaModel
                OutputDir = $targetDir
            }
            if ($PlanningModel) { $params['PlanningModel'] = $PlanningModel }
            if ($VisualModel) { $params['VisualModel'] = $VisualModel }
            $params['UseCppBackend'] = $UseCppBackend
            
            & $assetGenerator @params | Out-Null
            
            # Move file to correct location if needed
            $generatedFile = Join-Path $targetDir "${mod.Id}_icon.png"
            if (-not (Test-Path $generatedFile)) {
                # Check if file was generated in OutputDir root
                $rootFile = Join-Path (Join-Path $ModPath "assets") "${mod.Id}_icon.png"
                if (Test-Path $rootFile) {
                    Move-Item -Path $rootFile -Destination $generatedFile -Force
                }
            }
            
            $generated++
            Write-Host "  [OK] Generated mod icon: $($mod.Id)" -ForegroundColor Green
        } catch {
            $failed++
            Write-Host "  [FAIL] Mod icon $($mod.Id) : $_" -ForegroundColor Red
        }
    }
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Generating Integration Scripts" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Collect all generated assets for integration scripts
$allAssets = @()

# Add base orb sprites
foreach ($orb in $orbBaseTypes) {
    $allAssets += @{
        Id = $orb.Id
        Path = "/items/sprites/$($orb.Id).png"
        Type = "ItemSprite"
        Description = $orb.Desc
    }
}

# Add orb mod projectiles
foreach ($mod in $orbMods) {
    $allAssets += @{
        Id = $mod.Id
        Path = "/projectiles/$($mod.Id).png"
        Type = "Projectile"
        Description = $mod.Desc
    }
}

# Add animations
foreach ($anim in $orbAnimations) {
    $allAssets += @{
        Id = $anim.Id
        Path = "/animations/magitech/$($anim.Id).png"
        Type = "Animation"
        Description = $anim.Desc
    }
}

# Add UI elements
foreach ($ui in $orbUI) {
    $allAssets += @{
        Id = $ui.Id
        Path = "/interface/icons/$($ui.Id).png"
        Type = "Icon"
        Description = $ui.Desc
    }
}

# Add particles
foreach ($particle in $orbParticles) {
    $allAssets += @{
        Id = $particle.Id
        Path = "/particles/magitech/$($particle.Id).particle"
        Type = "Particle"
        Description = $particle.Desc
    }
}

# Add sounds
foreach ($sound in $orbSounds) {
    $allAssets += @{
        Id = $sound.Id
        Path = "/sfx/$($sound.Id).ogg"
        Type = "Sound"
        Description = $sound.Desc
    }
}

# Add status icons
foreach ($status in $orbStatusEffects) {
    $allAssets += @{
        Id = "${status.Id}_status"
        Path = "/status/icons/${status.Id}_status.png"
        Type = "Icon"
        Description = $status.Desc
    }
}

# Add mod icons
foreach ($mod in $orbMods) {
    $allAssets += @{
        Id = "${mod.Id}_icon"
        Path = "/interface/icons/${mod.Id}_icon.png"
        Type = "Icon"
        Description = "Icon for $($mod.Name)"
    }
}

# Generate integration scripts
$integrationScript = Join-Path $PSScriptRoot "GenerateAssetIntegrationScripts.ps1"
if (Test-Path $integrationScript) {
    Write-Host "Generating Lua and C++ integration scripts..." -ForegroundColor Yellow
    
    & $integrationScript `
        -AssetName "MagicOrb" `
        -AssetType "Weapon" `
        -ModPath $ModPath `
        -Assets $allAssets
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK] Integration scripts generated" -ForegroundColor Green
    } else {
        Write-Host "  [WARN] Integration script generation had issues" -ForegroundColor Yellow
    }
} else {
    Write-Host "  [WARN] Integration script generator not found: $integrationScript" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Generation Complete" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Generated: $generated assets" -ForegroundColor Green
Write-Host "Skipped: $skipped assets (already exist)" -ForegroundColor Gray
Write-Host "Failed: $failed assets" -ForegroundColor $(if ($failed -gt 0) { "Red" } else { "Green" })
Write-Host ""
Write-Host "Asset Breakdown:" -ForegroundColor Yellow
Write-Host "  - Base orb sprites: $($orbBaseTypes.Count)" -ForegroundColor Gray
Write-Host "  - Orb mod projectiles: $($orbMods.Count)" -ForegroundColor Gray
Write-Host "  - Orb animations: $($orbAnimations.Count)" -ForegroundColor Gray
Write-Host "  - UI elements: $($orbUI.Count)" -ForegroundColor Gray
Write-Host "  - VFX particles: $($orbParticles.Count)" -ForegroundColor Gray
Write-Host "  - Sound effects: $($orbSounds.Count)" -ForegroundColor Gray
Write-Host "  - Status icons: $($orbStatusEffects.Count)" -ForegroundColor Gray
Write-Host "  - Mod icons: $($orbMods.Count)" -ForegroundColor Gray
Write-Host ""
