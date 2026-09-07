#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate assets for the Centipede mech form.
    
.DESCRIPTION
    Generates all assets needed for the Centipede form including:
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
Write-Host "  Centipede Form Asset Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$generated = 0
$failed = 0
$skipped = 0

# Generate form icon
Write-Host "Generating Form Icon..." -ForegroundColor Yellow
Write-Host ""

# Validate $ModPath before Join-Path
$iconPath = Join-Path $ModPath "assets\centipede_icon.png"
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
            AssetName = "centipede_icon"
            Prompt = "An icon for the Centipede mech form. Poison elemental centipede mech, segmented body, many legs, stealthy appearance, 64x64 pixels"
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
    @{Id="centipedeEnter"; Name="Enter Effect"; Type="Poison"; Desc="Poison cloud effect when entering centipede form"},
    @{Id="centipedeTrail"; Name="Trail Effect"; Type="Poison"; Desc="Poison trail effect while in centipede form"},
    @{Id="centipedeExit"; Name="Exit Effect"; Type="Poison"; Desc="Poison cloud effect when exiting centipede form"},
    @{Id="centipedePincerStrike"; Name="Pincer Strike"; Type="Physical"; Desc="Impact effect from pincer strike ability"},
    @{Id="centipedeAcidSpray"; Name="Acid Spray"; Type="Poison"; Desc="Acid spray projectile trail effect"},
    @{Id="centipedeVenomTrail"; Name="Venom Trail"; Type="Poison"; Desc="Venomous trail effect from venom trail ability"},
    @{Id="centipedeSegmentShift"; Name="Segment Shift"; Type="Stealth"; Desc="Visual effect when segment shift is active"},
    @{Id="centipedeBurrowTrail"; Name="Burrow Trail"; Type="Earth"; Desc="Underground trail effect when burrowed"}
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
                Prompt = "A particle effect: $($particle.Name) - $($particle.Desc). $($particle.Type) type effect"
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

# Generate projectile sprites
Write-Host "Generating Projectile Sprites..." -ForegroundColor Yellow
Write-Host ""

$projectiles = @(
    @{Id="acidSpray"; Name="Acid Spray"; Desc="Acid spray projectile, poison liquid, 32x32 pixels"},
    @{Id="burst"; Name="Burst"; Desc="Burst explosion projectile for emerge damage, 32x32 pixels"}
)

foreach ($projectile in $projectiles) {
    # Validate $ModPath before Join-Path
$projPath = Join-Path $ModPath "projectiles\magitech\${projectile.Id}.png"
 if ([string]::IsNullOrWhiteSpace($projPath)) {
        Write-Host "  [FAIL] projPath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
 if ([string]::IsNullOrWhiteSpace($projPath)) {
        Write-Host "  [FAIL] projPath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
    if ($SkipExisting -and (Test-Path $projPath)) {
        $skipped++
        Write-Host "  [SKIP] Projectile sprite already exists: $($projectile.Id)" -ForegroundColor Gray
    } else {
        try {
            $params = @{
                AssetType = "Projectile"
                AssetName = $projectile.Id
                Prompt = "A projectile sprite: $($projectile.Name) - $($projectile.Desc). Poison/explosive projectile"
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
            Write-Host "  [OK] Generated projectile: $($projectile.Id)" -ForegroundColor Green
        } catch {
            $failed++
            Write-Host "  [FAIL] Projectile $($projectile.Id) : $_" -ForegroundColor Red
        }
    }
}

Write-Host ""

# Generate sound effects
Write-Host "Generating Sound Effects..." -ForegroundColor Yellow
Write-Host ""

$sounds = @(
    @{Id="centipedeOn"; Type="Roar"; Desc="Sound when entering centipede form, mechanical activation"},
    @{Id="centipedeOff"; Type="Mechanical"; Desc="Sound when exiting centipede form, mechanical deactivation"},
    @{Id="centipedePincerStrike"; Type="Impact"; Desc="Sound when pincer strike hits, sharp impact"},
    @{Id="centipedeAcidSpray"; Type="Whoosh"; Desc="Sound when acid spray fires, liquid whoosh"},
    @{Id="centipedeVenomTrail"; Type="Ambient"; Desc="Ambient sound for venom trail, poison hiss"},
    @{Id="centipedeSegmentShift"; Type="Mechanical"; Desc="Sound when segment shift activates, mechanical compression"},
    @{Id="centipedeBurrowIn"; Type="Impact"; Desc="Sound when burrowing in, earth impact"},
    @{Id="centipedeBurrowOut"; Type="Explosion"; Desc="Sound when emerging from burrow, explosive emergence"}
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
                Prompt = "A sound effect: $($sound.Desc). $($sound.Type) type sound"
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
            
            # Add sound-specific parameters
            $soundParams = @{
                SoundType = $sound.Type
                Format = "ogg"
            }
            $params['Parameters'] = $soundParams
            
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
    @{Id="centipedeVenomTrail"; Name="Venom Trail Active"; Desc="Status icon for active venom trail"},
    @{Id="centipedeSegmentShift"; Name="Segment Shift Active"; Desc="Status icon for active segment shift"},
    @{Id="centipedeBurrowed"; Name="Burrowed"; Desc="Status icon when burrowed, underground indicator"}
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
                Prompt = "A status effect icon: $($status.Name) - $($status.Desc). Status effect style, 32x32 pixels"
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

# Generate animation sprites (if needed for form-specific animations)
Write-Host "Generating Animation Sprites..." -ForegroundColor Yellow
Write-Host ""

$animations = @(
    @{Id="centipede_crawl"; Name="Crawl Animation"; Frames=12; Desc="Centipede crawling animation, many legs moving"},
    @{Id="centipede_climb"; Name="Climb Animation"; Frames=8; Desc="Centipede climbing wall animation"},
    @{Id="centipede_burrow"; Name="Burrow Animation"; Frames=6; Desc="Centipede burrowing underground animation"}
)

foreach ($anim in $animations) {
    # Validate $ModPath before Join-Path
$animPath = Join-Path $ModPath "animations\magitech\${anim.Id}.animation"
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
                Prompt = "An animation spritesheet: $($anim.Name) - $($anim.Desc). $($anim.Frames) frames, 96x96 pixels per frame, horizontal spritesheet"
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
            
            # Add animation-specific parameters
            $animParams = @{
                FrameCount = $anim.Frames
                FrameWidth = 96
                FrameHeight = 96
                AnimationCycle = if ($anim.Frames -le 6) { 0.4 } else { 0.6 }
                AnimationType = "MechForm"
            }
            $params['Parameters'] = $animParams
            
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
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Generation Complete" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Generated: $generated assets" -ForegroundColor Green
Write-Host "Skipped: $skipped assets (already exist)" -ForegroundColor Gray
Write-Host "Failed: $failed assets" -ForegroundColor $(if ($failed -gt 0) { "Red" } else { "Green" })
Write-Host ""
