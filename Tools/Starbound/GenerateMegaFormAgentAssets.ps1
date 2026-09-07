#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate assets for the MegaFormAgent System.
    
.DESCRIPTION
    Generates visual assets for:
    - Form shape sprites
    - Form effect particles
    - Form template icons
    - Event trigger visual indicators
    - Curve visualization elements
    - Form transformation effects
    
.PARAMETER ModPath
    Path to the mod directory
    
.PARAMETER OllamaModel
    Ollama model to use
    
.PARAMETER UseCppBackend
    Use C++ backend for generation
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$ModPath = "F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery",
    
    [Parameter(Mandatory=$false)]
    [string]$OllamaModel = "codellama:7b-instruct",
    
    [Parameter(Mandatory=$false)]
    [bool]$UseCppBackend = $true
)

$ErrorActionPreference = "Stop"
# Validate ModPath is not empty
if ([string]::IsNullOrWhiteSpace($ModPath)) {
    Write-Host "Error: ModPath cannot be empty" -ForegroundColor Red
    Write-Host "  Please provide a valid mod path or use the default" -ForegroundColor Gray
    exit 1
}


# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$assetGenerator = Join-Path $PSScriptRoot "StarboundOllamaAssetGenerator.ps1"

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  MegaFormAgent System Asset Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$generated = 0
$failed = 0

# ============================================================
# 1. FORM SHAPE SPRITES
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Form Shape Sprites" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$formShapes = @(
    @{ Id = "shape_circle"; Name = "Circle Shape"; Desc = "Circle spell form shape, circular, 64x64" },
    @{ Id = "shape_square"; Name = "Square Shape"; Desc = "Square spell form shape, square, 64x64" },
    @{ Id = "shape_triangle"; Name = "Triangle Shape"; Desc = "Triangle spell form shape, triangular, 64x64" },
    @{ Id = "shape_star"; Name = "Star Shape"; Desc = "Star spell form shape, star, 64x64" },
    @{ Id = "shape_hexagon"; Name = "Hexagon Shape"; Desc = "Hexagon spell form shape, hexagonal, 64x64" },
    @{ Id = "shape_diamond"; Name = "Diamond Shape"; Desc = "Diamond spell form shape, diamond, 64x64" },
    @{ Id = "shape_cross"; Name = "Cross Shape"; Desc = "Cross spell form shape, cross, 64x64" },
    @{ Id = "shape_spiral"; Name = "Spiral Shape"; Desc = "Spiral spell form shape, spiral, 64x64" },
    @{ Id = "shape_wave"; Name = "Wave Shape"; Desc = "Wave spell form shape, wavy, 64x64" },
    @{ Id = "shape_orb"; Name = "Orb Shape"; Desc = "Orb spell form shape, orb, 64x64" }
)

# Validate $ModPath before Join-Path
$shapeOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($shapeOutputDir)) {
    Write-Host "  [FAIL] shapeOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($shapeOutputDir)) {
    Write-Host "  [FAIL] shapeOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $shapeOutputDir)) {
    New-Item -ItemType Directory -Path $shapeOutputDir -Force | Out-Null
}

foreach ($shape in $formShapes) {
    Write-Host "Generating form shape: $($shape.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Sprite"
            AssetName = $shape.Id
            Prompt = "$($shape.Desc). Spell form shape sprite for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $shapeOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($shape.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($shape.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 2. FORM EFFECT PARTICLES
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Form Effect Particles" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$formEffects = @(
    @{ Id = "effect_energy_burst"; Name = "Energy Burst"; Desc = "Energy burst particle effect, explosive energy, 32x32" },
    @{ Id = "effect_glow_aura"; Name = "Glow Aura"; Desc = "Glow aura particle effect, glowing aura, 64x64" },
    @{ Id = "effect_sparkle"; Name = "Sparkle"; Desc = "Sparkle particle effect, sparkles, 16x16" },
    @{ Id = "effect_trail"; Name = "Trail"; Desc = "Trail particle effect, motion trail, 32x32" },
    @{ Id = "effect_ripple"; Name = "Ripple"; Desc = "Ripple particle effect, ripple wave, 64x64" },
    @{ Id = "effect_swirl"; Name = "Swirl"; Desc = "Swirl particle effect, swirling energy, 64x64" },
    @{ Id = "effect_pulse"; Name = "Pulse"; Desc = "Pulse particle effect, pulsing energy, 64x64" },
    @{ Id = "effect_orbiting"; Name = "Orbiting"; Desc = "Orbiting particle effect, orbiting particles, 64x64" },
    @{ Id = "effect_cascade"; Name = "Cascade"; Desc = "Cascade particle effect, cascading energy, 64x64" },
    @{ Id = "effect_dissolve"; Name = "Dissolve"; Desc = "Dissolve particle effect, dissolving energy, 64x64" }
)

# Validate $ModPath before Join-Path
$effectOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($effectOutputDir)) {
    Write-Host "  [FAIL] effectOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($effectOutputDir)) {
    Write-Host "  [FAIL] effectOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $effectOutputDir)) {
    New-Item -ItemType Directory -Path $effectOutputDir -Force | Out-Null
}

foreach ($effect in $formEffects) {
    Write-Host "Generating form effect: $($effect.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Particle"
            AssetName = $effect.Id
            Prompt = "$($effect.Desc). Spell form effect particle for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $effectOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($effect.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($effect.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 3. FORM TEMPLATE ICONS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Form Template Icons" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$formTemplates = @(
    @{ Id = "template_basic"; Name = "Basic Template"; Desc = "Basic spell form template icon, simple form, 32x32" },
    @{ Id = "template_advanced"; Name = "Advanced Template"; Desc = "Advanced spell form template icon, complex form, 32x32" },
    @{ Id = "template_elemental"; Name = "Elemental Template"; Desc = "Elemental spell form template icon, elemental form, 32x32" },
    @{ Id = "template_combat"; Name = "Combat Template"; Desc = "Combat spell form template icon, combat form, 32x32" },
    @{ Id = "template_utility"; Name = "Utility Template"; Desc = "Utility spell form template icon, utility form, 32x32" },
    @{ Id = "template_defensive"; Name = "Defensive Template"; Desc = "Defensive spell form template icon, defensive form, 32x32" },
    @{ Id = "template_offensive"; Name = "Offensive Template"; Desc = "Offensive spell form template icon, offensive form, 32x32" },
    @{ Id = "template_support"; Name = "Support Template"; Desc = "Support spell form template icon, support form, 32x32" }
)

# Validate $ModPath before Join-Path
$templateOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($templateOutputDir)) {
    Write-Host "  [FAIL] templateOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($templateOutputDir)) {
    Write-Host "  [FAIL] templateOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $templateOutputDir)) {
    New-Item -ItemType Directory -Path $templateOutputDir -Force | Out-Null
}

foreach ($template in $formTemplates) {
    Write-Host "Generating form template: $($template.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $template.Id
            Prompt = "$($template.Desc). Spell form template icon for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $templateOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($template.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($template.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 4. EVENT TRIGGER VISUAL INDICATORS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Event Trigger Visual Indicators" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$eventIndicators = @(
    @{ Id = "event_onhit"; Name = "OnHit Event"; Desc = "OnHit event trigger indicator, hit event, 32x32" },
    @{ Id = "event_ontimer"; Name = "OnTimer Event"; Desc = "OnTimer event trigger indicator, timer event, 32x32" },
    @{ Id = "event_ondistance"; Name = "OnDistance Event"; Desc = "OnDistance event trigger indicator, distance event, 32x32" },
    @{ Id = "event_triggered"; Name = "Event Triggered"; Desc = "Event triggered visual indicator, event active, 32x32" },
    @{ Id = "event_cooldown"; Name = "Event Cooldown"; Desc = "Event cooldown visual indicator, cooldown active, 32x32" }
)

# Validate $ModPath before Join-Path
$eventOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($eventOutputDir)) {
    Write-Host "  [FAIL] eventOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($eventOutputDir)) {
    Write-Host "  [FAIL] eventOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $eventOutputDir)) {
    New-Item -ItemType Directory -Path $eventOutputDir -Force | Out-Null
}

foreach ($indicator in $eventIndicators) {
    Write-Host "Generating event indicator: $($indicator.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $indicator.Id
            Prompt = "$($indicator.Desc). Event trigger indicator for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $eventOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($indicator.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($indicator.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 5. CURVE VISUALIZATION ELEMENTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Curve Visualization Elements" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$curveElements = @(
    @{ Id = "curve_scale"; Name = "Scale Curve"; Desc = "Scale curve visualization, scaling curve, 64x64" },
    @{ Id = "curve_color"; Name = "Color Curve"; Desc = "Color curve visualization, color gradient curve, 64x64" },
    @{ Id = "curve_speed"; Name = "Speed Curve"; Desc = "Speed curve visualization, speed curve, 64x64" },
    @{ Id = "curve_keyframe"; Name = "Curve Keyframe"; Desc = "Curve keyframe indicator, keyframe marker, 16x16" },
    @{ Id = "curve_interpolation"; Name = "Curve Interpolation"; Desc = "Curve interpolation visualization, interpolation curve, 64x64" }
)

# Validate $ModPath before Join-Path
$curveOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($curveOutputDir)) {
    Write-Host "  [FAIL] curveOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($curveOutputDir)) {
    Write-Host "  [FAIL] curveOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $curveOutputDir)) {
    New-Item -ItemType Directory -Path $curveOutputDir -Force | Out-Null
}

foreach ($element in $curveElements) {
    Write-Host "Generating curve element: $($element.Name)" -ForegroundColor Cyan
    
    try {
        $assetType = if ($element.Id -like "*keyframe*") { "Icon" } else { "Texture" }
        
        $params = @{
            AssetType = $assetType
            AssetName = $element.Id
            Prompt = "$($element.Desc). Curve visualization element for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $curveOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($element.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($element.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 6. FORM TRANSFORMATION EFFECTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Form Transformation Effects" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$transformationEffects = @(
    @{ Id = "transform_morph"; Name = "Morph Transformation"; Desc = "Morph transformation effect, shape morphing, 64x64" },
    @{ Id = "transform_scale"; Name = "Scale Transformation"; Desc = "Scale transformation effect, scaling, 64x64" },
    @{ Id = "transform_rotate"; Name = "Rotate Transformation"; Desc = "Rotate transformation effect, rotation, 64x64" },
    @{ Id = "transform_color"; Name = "Color Transformation"; Desc = "Color transformation effect, color shift, 64x64" },
    @{ Id = "transform_fade"; Name = "Fade Transformation"; Desc = "Fade transformation effect, fading, 64x64" },
    @{ Id = "transform_glow"; Name = "Glow Transformation"; Desc = "Glow transformation effect, glowing, 64x64" }
)

# Validate $ModPath before Join-Path
$transformOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($transformOutputDir)) {
    Write-Host "  [FAIL] transformOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($transformOutputDir)) {
    Write-Host "  [FAIL] transformOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $transformOutputDir)) {
    New-Item -ItemType Directory -Path $transformOutputDir -Force | Out-Null
}

foreach ($effect in $transformationEffects) {
    Write-Host "Generating transformation effect: $($effect.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Particle"
            AssetName = $effect.Id
            Prompt = "$($effect.Desc). Form transformation effect for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $transformOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($effect.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($effect.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 7. FORM CATEGORY ICONS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Form Category Icons" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$categoryIcons = @(
    @{ Id = "category_elemental"; Name = "Elemental Category"; Desc = "Elemental form category icon, elemental, 32x32" },
    @{ Id = "category_combat"; Name = "Combat Category"; Desc = "Combat form category icon, combat, 32x32" },
    @{ Id = "category_utility"; Name = "Utility Category"; Desc = "Utility form category icon, utility, 32x32" },
    @{ Id = "category_defensive"; Name = "Defensive Category"; Desc = "Defensive form category icon, defensive, 32x32" },
    @{ Id = "category_offensive"; Name = "Offensive Category"; Desc = "Offensive form category icon, offensive, 32x32" },
    @{ Id = "category_support"; Name = "Support Category"; Desc = "Support form category icon, support, 32x32" }
)

# Validate $ModPath before Join-Path
$categoryOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($categoryOutputDir)) {
    Write-Host "  [FAIL] categoryOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($categoryOutputDir)) {
    Write-Host "  [FAIL] categoryOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $categoryOutputDir)) {
    New-Item -ItemType Directory -Path $categoryOutputDir -Force | Out-Null
}

foreach ($icon in $categoryIcons) {
    Write-Host "Generating category icon: $($icon.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $icon.Id
            Prompt = "$($icon.Desc). Form category icon for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $categoryOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($icon.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($icon.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# SUMMARY
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Generation Complete" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Generated: $generated assets" -ForegroundColor Green
Write-Host "Failed: $failed assets" -ForegroundColor $(if ($failed -gt 0) { "Red" } else { "Green" })
Write-Host ""
Write-Host "Assets saved to:" -ForegroundColor Gray
Write-Host "  Form Shapes: $(Join-Path $ModPath 'assets\shapes')" -ForegroundColor Gray
Write-Host "  Form Effects: $(Join-Path $ModPath 'assets\effects')" -ForegroundColor Gray
Write-Host "  Form Templates: $(Join-Path $ModPath 'assets\forms\templates')" -ForegroundColor Gray
Write-Host "  Event Indicators: $(Join-Path $ModPath 'assets\forms\events')" -ForegroundColor Gray
Write-Host "  Curve Elements: $(Join-Path $ModPath 'assets\forms\curves')" -ForegroundColor Gray
Write-Host "  Transformations: $(Join-Path $ModPath 'assets\forms\transformations')" -ForegroundColor Gray
Write-Host "  Form Categories: $(Join-Path $ModPath 'assets\forms\categories')" -ForegroundColor Gray
Write-Host ""
