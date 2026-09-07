#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate assets for the Tentacled Horror mech form.
    
.DESCRIPTION
    Generates all assets needed for the Tentacled Horror form including:
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
Write-Host "  Tentacled Horror Form Asset Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$generated = 0
$failed = 0
$skipped = 0

# Generate form icon
Write-Host "Generating Form Icon..." -ForegroundColor Yellow
Write-Host ""

# Validate $ModPath before Join-Path
$iconPath = Join-Path $ModPath "assets\tentacledHorror_icon.png"
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
            AssetName = "tentacledHorror_icon"
            Prompt = "An icon for the Tentacled Horror mech form. Void elemental eldritch horror mech, massive writhing tentacles, dark purple/black colors, organic-mechanical fusion, 64x64 pixels"
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
    @{Id="tentacledHorrorEnter"; Name="Enter Effect"; Type="Void"; Desc="Void energy explosion effect when entering tentacled horror form, dark purple/black void essence"},
    @{Id="tentacledHorrorLoop"; Name="Loop Effect"; Type="Void"; Desc="Writhing tentacle aura effect while in tentacled horror form, continuous void energy"},
    @{Id="tentacledHorrorExit"; Name="Exit Effect"; Type="Void"; Desc="Void energy dissipation effect when exiting tentacled horror form"},
    @{Id="tentacledHorrorTentacleStrike"; Name="Tentacle Strike"; Type="Physical"; Desc="Impact effect from tentacle strike ability, tentacle slam with void energy"},
    @{Id="tentacledHorrorGrapple"; Name="Grapple Tentacle"; Type="Void"; Desc="Tentacle grab effect from grapple ability, void energy tendrils"},
    @{Id="tentacledHorrorAura"; Name="Horror Aura"; Type="Void"; Desc="Fear aura effect, dark void energy waves that slow and damage enemies"},
    @{Id="tentacledHorrorInkCloud"; Name="Ink Cloud"; Type="Void"; Desc="Dark ink cloud effect that blinds enemies, black void mist"}
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
                Prompt = "A particle effect: $($particle.Name) - $($particle.Desc). $($particle.Type) type effect, dark purple/black void colors"
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
    @{Id="tentacleProjectile"; Name="Tentacle Projectile"; Desc="Tentacle projectile sprite, void energy tentacle, 32x32 pixels"},
    @{Id="inkCloudProjectile"; Name="Ink Cloud Projectile"; Desc="Ink cloud projectile sprite, dark void mist, 32x32 pixels"}
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
                Prompt = "A projectile sprite: $($projectile.Name) - $($projectile.Desc). Void/eldritch projectile, dark purple/black"
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
    @{Id="tentacledHorrorOn"; Type="Roar"; Desc="Sound when entering tentacled horror form, eldritch void roar, mechanical-organic fusion"},
    @{Id="tentacledHorrorOff"; Type="Mechanical"; Desc="Sound when exiting tentacled horror form, void energy dissipation"},
    @{Id="tentacledHorrorTentacleStrike"; Type="Impact"; Desc="Sound when tentacle strike hits, heavy organic impact with void energy"},
    @{Id="tentacledHorrorGrapple"; Type="Whoosh"; Desc="Sound when grapple tentacle fires, tentacle extension with void energy"},
    @{Id="tentacledHorrorAura"; Type="Ambient"; Desc="Ambient sound for horror aura, dark void energy hum, fear-inducing"},
    @{Id="tentacledHorrorInkCloud"; Type="Whoosh"; Desc="Sound when ink cloud activates, dark void mist expansion"}
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
                Prompt = "A sound effect: $($sound.Desc). $($sound.Type) type sound, eldritch void theme"
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
    @{Id="tentacledHorrorAura"; Name="Horror Aura Active"; Desc="Status icon for active horror aura, void energy indicator"},
    @{Id="tentacledHorrorGrappled"; Name="Grappled"; Desc="Status icon when target is grappled, tentacle hold indicator"},
    @{Id="tentacledHorrorBlinded"; Name="Blinded by Ink"; Desc="Status icon when blinded by ink cloud, dark void mist indicator"}
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
                Prompt = "A status effect icon: $($status.Name) - $($status.Desc). Status effect style, 32x32 pixels, dark purple/black void theme"
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
    @{Id="tentacledHorror_crawl"; Name="Crawl Animation"; Frames=12; Desc="Tentacled horror crawling animation, writhing tentacles moving"},
    @{Id="tentacledHorror_climb"; Name="Climb Animation"; Frames=8; Desc="Tentacled horror climbing wall/ceiling animation, tentacles gripping"},
    @{Id="tentacledHorror_idle"; Name="Idle Animation"; Frames=10; Desc="Tentacled horror idle animation, tentacles writhing slowly"}
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
                Prompt = "An animation spritesheet: $($anim.Name) - $($anim.Desc). $($anim.Frames) frames, 96x96 pixels per frame, horizontal spritesheet, dark void colors"
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
    @{Id="tentacledHorror_weaponAim"; Name="Weapon Aim"; Frames=6; Desc="Tentacled horror weapon aiming animation"},
    @{Id="tentacledHorror_weaponFire"; Name="Weapon Fire"; Frames=4; Desc="Tentacled horror weapon firing animation"},
    @{Id="tentacledHorror_weaponReload"; Name="Weapon Reload"; Frames=8; Desc="Tentacled horror weapon reloading animation"},
    @{Id="tentacledHorror_weaponHolster"; Name="Weapon Holster"; Frames=6; Desc="Tentacled horror weapon holstering animation"},
    @{Id="tentacledHorror_orbEmerge"; Name="Orb Emerge"; Frames=6; Desc="Tentacled horror orb emergence animation"},
    @{Id="tentacledHorror_magicChannel"; Name="Magic Channel"; Frames=8; Desc="Tentacled horror magic channeling animation"},
    @{Id="tentacledHorror_magicCast"; Name="Magic Cast"; Frames=6; Desc="Tentacled horror magic casting animation"},
    @{Id="tentacledHorror_orbDissipate"; Name="Orb Dissipate"; Frames=4; Desc="Tentacled horror orb dissipation animation"}
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
                Prompt = "An animation spritesheet: $($anim.Name) - $($anim.Desc). $($anim.Frames) frames, 96x96 pixels per frame, horizontal spritesheet, tentacled horror form"
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
