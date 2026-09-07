#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate assets for the Blade Cyclone mech form.
    
.DESCRIPTION
    Generates all assets needed for the Blade Cyclone form including:
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
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$assetGenerator = Join-Path $PSScriptRoot "StarboundOllamaAssetGenerator.ps1"

# Validate ModPath is not empty
if ([string]::IsNullOrWhiteSpace($ModPath)) {
    Write-Host "Error: ModPath cannot be empty" -ForegroundColor Red
    Write-Host "  Please provide a valid mod path or use the default" -ForegroundColor Gray
    exit 1
}

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Blade Cyclone Form Asset Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$generated = 0
$failed = 0
$skipped = 0

# Generate form icon
Write-Host "Generating Form Icon..." -ForegroundColor Yellow
Write-Host ""

# Validate $ModPath before Join-Path
$iconPath = Join-Path $ModPath "assets\bladeCyclone_icon.png"
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
            AssetName = "bladeCyclone_icon"
            Prompt = "An icon for the Blade Cyclone mech form. Wind elemental mech, spinning blades, cyclone effect, silver/blue colors, aerodynamic design, 64x64 pixels"
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
    @{Id="bladeCycloneEnter"; Name="Enter Effect"; Type="Wind"; Desc="Wind energy burst effect when entering blade cyclone form, spinning blades appear"},
    @{Id="bladeCycloneLoop"; Name="Loop Effect"; Type="Wind"; Desc="Continuous spinning blade cyclone effect while in form, rotating blades"},
    @{Id="bladeCycloneExit"; Name="Exit Effect"; Type="Wind"; Desc="Wind energy dissipation effect when exiting blade cyclone form"},
    @{Id="bladeCycloneSpin"; Name="Blade Spin"; Type="Physical"; Desc="Spinning blade effect for blade cyclone ability, rotating cutting blades"}
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
            # Validate $ModPath before Join-Path
$outputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($outputDir)) {
                Write-Host "  [FAIL] outputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                continue
            }
 if ([string]::IsNullOrWhiteSpace($outputDir)) {
                Write-Host "  [FAIL] outputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                continue
            }
            if ([string]::IsNullOrWhiteSpace($outputDir)) {
                Write-Host "  [FAIL] Particle $($particle.Id): OutputDir is null (ModPath: '$ModPath')" -ForegroundColor Red
                $failed++
                continue
            }
            
            $params = @{
                AssetType = "Particle"
                AssetName = $particle.Id
                Prompt = "A particle effect: $($particle.Name) - $($particle.Desc). $($particle.Type) type effect, silver/blue wind colors"
                OllamaModel = $OllamaModel
                OutputDir = $outputDir
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
    @{Id="cycloneStart"; Type="Whoosh"; Desc="Sound when entering blade cyclone form, wind rush and blade activation"},
    @{Id="cycloneStop"; Type="Mechanical"; Desc="Sound when exiting blade cyclone form, wind dissipation"},
    @{Id="cycloneWhirl"; Type="Ambient"; Desc="Continuous sound for blade cyclone ability, spinning blades and wind"}
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
            # Validate $ModPath before Join-Path
$outputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($outputDir)) {
                Write-Host "  [FAIL] outputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                continue
            }
 if ([string]::IsNullOrWhiteSpace($outputDir)) {
                Write-Host "  [FAIL] outputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                continue
            }
            if ([string]::IsNullOrWhiteSpace($outputDir)) {
                Write-Host "  [FAIL] Sound $($sound.Id): OutputDir is null (ModPath: '$ModPath')" -ForegroundColor Red
                $failed++
                continue
            }
            
            $params = @{
                AssetType = "Sound"
                AssetName = $sound.Id
                Prompt = "A sound effect: $($sound.Desc). $($sound.Type) type sound, wind/blade theme"
                OllamaModel = $OllamaModel
                OutputDir = $outputDir
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
    @{Id="bladeCycloneActive"; Name="Blade Cyclone Active"; Desc="Status icon for active blade cyclone ability, spinning blades indicator"}
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
                Prompt = "A status effect icon: $($status.Name) - $($status.Desc). Status effect style, 32x32 pixels, silver/blue wind theme"
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
    @{Id="bladeCyclone_idle"; Name="Idle Animation"; Frames=10; Desc="Blade cyclone idle animation, subtle blade rotation"},
    @{Id="bladeCyclone_dash"; Name="Dash Animation"; Frames=8; Desc="Blade cyclone dash animation, wind trail effect"},
    @{Id="bladeCyclone_dodge"; Name="Dodge Animation"; Frames=6; Desc="Blade cyclone dodge animation, quick blade spin"}
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
                Prompt = "An animation spritesheet: $($anim.Name) - $($anim.Desc). $($anim.Frames) frames, 96x96 pixels per frame, horizontal spritesheet, wind/blade colors"
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
    @{Id="bladeCyclone_weaponAim"; Name="Weapon Aim"; Frames=6; Desc="Blade cyclone weapon aiming animation"},
    @{Id="bladeCyclone_weaponFire"; Name="Weapon Fire"; Frames=4; Desc="Blade cyclone weapon firing animation"},
    @{Id="bladeCyclone_weaponReload"; Name="Weapon Reload"; Frames=8; Desc="Blade cyclone weapon reloading animation"},
    @{Id="bladeCyclone_weaponHolster"; Name="Weapon Holster"; Frames=6; Desc="Blade cyclone weapon holstering animation"},
    @{Id="bladeCyclone_orbEmerge"; Name="Orb Emerge"; Frames=6; Desc="Blade cyclone orb emergence animation"},
    @{Id="bladeCyclone_magicChannel"; Name="Magic Channel"; Frames=8; Desc="Blade cyclone magic channeling animation"},
    @{Id="bladeCyclone_magicCast"; Name="Magic Cast"; Frames=6; Desc="Blade cyclone magic casting animation"},
    @{Id="bladeCyclone_orbDissipate"; Name="Orb Dissipate"; Frames=4; Desc="Blade cyclone orb dissipation animation"}
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
                Prompt = "An animation spritesheet: $($anim.Name) - $($anim.Desc). $($anim.Frames) frames, 96x96 pixels per frame, horizontal spritesheet, blade cyclone form"
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
