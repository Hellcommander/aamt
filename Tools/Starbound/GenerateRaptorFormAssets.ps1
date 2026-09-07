#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate assets for the Raptor mech form.
    
.DESCRIPTION
    Generates all assets needed for the Raptor form including:
    - Form sprites and animations
    - Ability VFX particles
    - Sound effects

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}
    - Projectile sprites
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

$ErrorActionPreference = "Stop"
# Validate ModPath is not empty
if ([string]::IsNullOrWhiteSpace($ModPath)) {
    Write-Host "Error: ModPath cannot be empty" -ForegroundColor Red
    Write-Host "  Please provide a valid mod path or use the default" -ForegroundColor Gray
    exit 1
}

$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$assetGenerator = Join-Path $PSScriptRoot "StarboundOllamaAssetGenerator.ps1"

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Raptor Form Asset Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$generated = 0
$failed = 0
$skipped = 0

# Generate form icon
Write-Host "Generating Form Icon..." -ForegroundColor Yellow
Write-Host ""

# Validate $ModPath before Join-Path
$iconPath = Join-Path $ModPath "assets\raptor_icon.png"
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
    Write-Host "  [SKIP] Form icon already exists" -ForegroundColor Gray
} else {
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = "raptor_icon"
            Prompt = "An icon for the Raptor mech form. Earth elemental predator mech, agile bipedal design, sharp claws and tail, brown/green earth colors, 64x64 pixels"
            OllamaModel = $OllamaModel
            # Validate $ModPath before Join-Path
$tempOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                Write-Host "  [FAIL] tempOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                continue
            }
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                Write-Host "  [FAIL] OutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                continue
            }
            OutputDir = $tempOutputDir
        }
        if ($PlanningModel) { $params['PlanningModel'] = $PlanningModel }
        if ($VisualModel) { $params['VisualModel'] = $VisualModel }
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        $generated++
        Write-Host "  [OK] Generated form icon" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] Form icon: $_" -ForegroundColor Red
    }
}

Write-Host ""

# Generate VFX particles
Write-Host "Generating VFX Particles..." -ForegroundColor Yellow
Write-Host ""

$particles = @(
    @{Id="raptorEnter"; Name="Enter Effect"; Type="Earth"; Desc="Earth energy burst effect when entering raptor form, predator activation"},
    @{Id="raptorLoop"; Name="Loop Effect"; Type="Earth"; Desc="Subtle earth energy aura effect while in raptor form"},
    @{Id="raptorExit"; Name="Exit Effect"; Type="Earth"; Desc="Earth energy dissipation effect when exiting raptor form"},
    @{Id="raptorPounce"; Name="Pounce"; Type="Physical"; Desc="Impact effect from pounce ability, landing impact with earth energy"},
    @{Id="clawSlash"; Name="Claw Slash"; Type="Physical"; Desc="Slashing effect from claw slash ability, sharp cutting arc"},
    @{Id="tailWhip"; Name="Tail Whip"; Type="Physical"; Desc="Spinning tail effect from tail whip ability, sweeping attack"},
    @{Id="camoEnter"; Name="Camouflage Enter"; Type="Stealth"; Desc="Stealth activation effect when camouflage activates, visual distortion"},
    @{Id="camoExit"; Name="Camouflage Exit"; Type="Stealth"; Desc="Stealth deactivation effect when camouflage ends, visual reveal"}
)

foreach ($particle in $particles) {
    # Validate $ModPath before Join-Path
$particlePath = Join-Path $ModPath "particles\magitech\${particle.Id}.particle"
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
            $params = @{
                AssetType = "Particle"
                AssetName = $particle.Id
                Prompt = "A particle effect: $($particle.Name) - $($particle.Desc). $($particle.Type) type effect, earth/predator colors"
                OllamaModel = $OllamaModel
                # Validate $ModPath before Join-Path
$tempOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                    Write-Host "  [FAIL] tempOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                    continue
                }
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                    Write-Host "  [FAIL] OutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                    continue
                }
            OutputDir = $tempOutputDir
            }
            if ($PlanningModel) { $params['PlanningModel'] = $PlanningModel }
            if ($VisualModel) { $params['VisualModel'] = $VisualModel }
            $params['UseCppBackend'] = $UseCppBackend
            
            & $assetGenerator @params | Out-Null
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
Write-Host "Generating Sound Effects..." -ForegroundColor Yellow
Write-Host ""

$sounds = @(
    @{Id="raptor_activate"; Type="Roar"; Desc="Sound when entering raptor form, predator activation roar"},
    @{Id="raptor_deactivate"; Type="Mechanical"; Desc="Sound when exiting raptor form, mechanical deactivation"},
    @{Id="raptor_leap"; Type="Whoosh"; Desc="Sound when pounce ability activates, leap whoosh with impact"},
    @{Id="claw_slash"; Type="Impact"; Desc="Sound when claw slash hits, sharp cutting impact"},
    @{Id="tail_whip"; Type="Whoosh"; Desc="Continuous sound for tail whip ability, spinning whoosh"},
    @{Id="camo_on"; Type="Ambient"; Desc="Sound when camouflage activates, stealth activation"},
    @{Id="camo_off"; Type="Ambient"; Desc="Sound when camouflage deactivates, stealth reveal"}
)

foreach ($sound in $sounds) {
    # Validate $ModPath before Join-Path
$soundPath = Join-Path $ModPath "sfx\${sound.Id}.ogg"
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
            $params = @{
                AssetType = "Sound"
                AssetName = $sound.Id
                Prompt = "A sound effect: $($sound.Desc). $($sound.Type) type sound, predator/earth theme"
                OllamaModel = $OllamaModel
                # Validate $ModPath before Join-Path
$tempOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                    Write-Host "  [FAIL] tempOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                    continue
                }
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                    Write-Host "  [FAIL] OutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                    continue
                }
            OutputDir = $tempOutputDir
            }
            if ($PlanningModel) { $params['PlanningModel'] = $PlanningModel }
            if ($VisualModel) { $params['VisualModel'] = $VisualModel }
            $params['UseCppBackend'] = $UseCppBackend
            
            & $assetGenerator @params | Out-Null
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
Write-Host "Generating Status Effect Icons..." -ForegroundColor Yellow
Write-Host ""

$statusEffects = @(
    @{Id="raptorCamouflage"; Name="Camouflage Active"; Desc="Status icon for active camouflage, stealth indicator"},
    @{Id="raptorTailWhip"; Name="Tail Whip Active"; Desc="Status icon for active tail whip, spinning indicator"}
)

foreach ($status in $statusEffects) {
    # Validate $ModPath before Join-Path
$iconPath = Join-Path $ModPath "status\icons\${status.Id}.png"
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
            $params = @{
                AssetType = "Icon"
                AssetName = "${status.Id}_status"
                Prompt = "A status effect icon: $($status.Name) - $($status.Desc). Status effect style, 32x32 pixels, earth/predator theme"
                OllamaModel = $OllamaModel
                # Validate $ModPath before Join-Path
$tempOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                    Write-Host "  [FAIL] tempOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                    continue
                }
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                    Write-Host "  [FAIL] OutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                    continue
                }
            OutputDir = $tempOutputDir
            }
            if ($PlanningModel) { $params['PlanningModel'] = $PlanningModel }
            if ($VisualModel) { $params['VisualModel'] = $VisualModel }
            $params['UseCppBackend'] = $UseCppBackend
            
            & $assetGenerator @params | Out-Null
            $generated++
            Write-Host "  [OK] Generated status icon: $($status.Id)" -ForegroundColor Green
        } catch {
            $failed++
            Write-Host "  [FAIL] Status icon $($status.Id) : $_" -ForegroundColor Red
        }
    }
}

Write-Host ""

# Generate animation sprites
Write-Host "Generating Animation Sprites..." -ForegroundColor Yellow
Write-Host ""

$animations = @(
    @{Id="raptor_idle"; Name="Idle Animation"; Frames=8; Desc="Raptor idle animation, predator stance"},
    @{Id="raptor_walk"; Name="Walk Animation"; Frames=12; Desc="Raptor walking animation, agile movement"},
    @{Id="raptor_run"; Name="Run Animation"; Frames=12; Desc="Raptor running animation, fast sprint"},
    @{Id="raptor_jump"; Name="Jump Animation"; Frames=8; Desc="Raptor jumping animation, powerful leap"},
    @{Id="raptor_fall"; Name="Fall Animation"; Frames=4; Desc="Raptor falling animation, aerial control"},
    @{Id="raptor_dash"; Name="Dash Animation"; Frames=6; Desc="Raptor dash animation, quick burst"},
    @{Id="raptor_dodge"; Name="Dodge Animation"; Frames=6; Desc="Raptor dodge animation, evasive movement"},
    @{Id="raptor_wallrun"; Name="Wall Run Animation"; Frames=6; Desc="Raptor wall running animation, vertical traversal"},
    @{Id="raptor_pounce"; Name="Pounce Animation"; Frames=8; Desc="Raptor pounce ability animation, leap attack"},
    @{Id="raptor_claw"; Name="Claw Slash Animation"; Frames=6; Desc="Raptor claw slash animation, melee attack"},
    @{Id="raptor_tailwhip"; Name="Tail Whip Animation"; Frames=6; Desc="Raptor tail whip animation, spinning attack"},
    @{Id="raptor_camo"; Name="Camouflage Animation"; Frames=4; Desc="Raptor camouflage animation, stealth activation"}
)

foreach ($anim in $animations) {
    # Validate $ModPath before Join-Path
$animPath = Join-Path $ModPath "sprites\forms\${anim.Id}.png"
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
            $params = @{
                AssetType = "AnimationSprite"
                AssetName = $anim.Id
                Prompt = "An animation spritesheet: $($anim.Name) - $($anim.Desc). $($anim.Frames) frames, 96x96 pixels per frame, horizontal spritesheet, raptor predator form"
                OllamaModel = $OllamaModel
                # Validate $ModPath before Join-Path
$tempOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                    Write-Host "  [FAIL] tempOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                    continue
                }
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                    Write-Host "  [FAIL] OutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                    continue
                }
            OutputDir = $tempOutputDir
            }
            if ($PlanningModel) { $params['PlanningModel'] = $PlanningModel }
            if ($VisualModel) { $params['VisualModel'] = $VisualModel }
            $params['UseCppBackend'] = $UseCppBackend
            
            & $assetGenerator @params | Out-Null
            $generated++
            Write-Host "  [OK] Generated animation: $($anim.Id)" -ForegroundColor Green
        } catch {
            $failed++
            Write-Host "  [FAIL] Animation $($anim.Id) : $_" -ForegroundColor Red
        }
    }
}

Write-Host ""

# Generate weapon/magic animation sprites
Write-Host "Generating Weapon/Magic Animation Sprites..." -ForegroundColor Yellow
Write-Host ""

$weaponAnimations = @(
    @{Id="raptor_weaponAim"; Name="Weapon Aim"; Frames=6; Desc="Raptor weapon aiming animation"},
    @{Id="raptor_weaponFire"; Name="Weapon Fire"; Frames=4; Desc="Raptor weapon firing animation"},
    @{Id="raptor_weaponReload"; Name="Weapon Reload"; Frames=8; Desc="Raptor weapon reloading animation"},
    @{Id="raptor_weaponHolster"; Name="Weapon Holster"; Frames=6; Desc="Raptor weapon holstering animation"},
    @{Id="raptor_orbEmerge"; Name="Orb Emerge"; Frames=6; Desc="Raptor orb emergence animation"},
    @{Id="raptor_magicChannel"; Name="Magic Channel"; Frames=8; Desc="Raptor magic channeling animation"},
    @{Id="raptor_magicCast"; Name="Magic Cast"; Frames=6; Desc="Raptor magic casting animation"},
    @{Id="raptor_orbDissipate"; Name="Orb Dissipate"; Frames=4; Desc="Raptor orb dissipation animation"}
)

foreach ($anim in $weaponAnimations) {
    # Validate $ModPath before Join-Path
$animPath = Join-Path $ModPath "sprites\forms\${anim.Id}.png"
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
        Write-Host "  [SKIP] Weapon animation already exists: $($anim.Id)" -ForegroundColor Gray
    } else {
        try {
            $params = @{
                AssetType = "AnimationSprite"
                AssetName = $anim.Id
                Prompt = "An animation spritesheet: $($anim.Name) - $($anim.Desc). $($anim.Frames) frames, 96x96 pixels per frame, horizontal spritesheet, raptor form"
                OllamaModel = $OllamaModel
                # Validate $ModPath before Join-Path
$tempOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                    Write-Host "  [FAIL] tempOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                    continue
                }
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                    Write-Host "  [FAIL] OutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                    continue
                }
            OutputDir = $tempOutputDir
            }
            if ($PlanningModel) { $params['PlanningModel'] = $PlanningModel }
            if ($VisualModel) { $params['VisualModel'] = $VisualModel }
            $params['UseCppBackend'] = $UseCppBackend
            
            & $assetGenerator @params | Out-Null
            $generated++
            Write-Host "  [OK] Generated weapon animation: $($anim.Id)" -ForegroundColor Green
        } catch {
            $failed++
            Write-Host "  [FAIL] Weapon animation $($anim.Id) : $_" -ForegroundColor Red
        }
    }
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
