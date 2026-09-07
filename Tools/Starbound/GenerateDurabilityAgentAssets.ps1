#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate assets for the DurabilityAgent System.
    
.DESCRIPTION
    Generates visual assets for:
    - Condition state indicators (Pristine, Maintained, Used, Worn, Damaged, CriticallyDamaged, Broken)
    - Wear category icons (Structural, Magical, Ingredient, Environmental, UsageFatigue)
    - Repair type icons (Preventive, Minor, Major, Restoration)
    - Repair quality indicators (Poor, Basic, Good, Excellent, Masterful, Perfect)
    - Durability bar/meter UI elements
    - Repair UI elements (panels, buttons, tooltips)
    - Damage/wear visual effects
    - Repair visual effects
    - Condition overlay textures
    - Durability status icons
    
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
Write-Host "  DurabilityAgent System Asset Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$generated = 0
$failed = 0

# ============================================================
# 1. CONDITION STATE INDICATORS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Condition State Indicators" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$conditionStates = @(
    @{ Id = "condition_pristine"; Name = "Pristine"; Desc = "Pristine condition indicator, 100% condition, 32x32" },
    @{ Id = "condition_maintained"; Name = "Maintained"; Desc = "Maintained condition indicator, 90-99% condition, 32x32" },
    @{ Id = "condition_used"; Name = "Used"; Desc = "Used condition indicator, 70-89% condition, 32x32" },
    @{ Id = "condition_worn"; Name = "Worn"; Desc = "Worn condition indicator, 50-69% condition, 32x32" },
    @{ Id = "condition_damaged"; Name = "Damaged"; Desc = "Damaged condition indicator, 20-49% condition, 32x32" },
    @{ Id = "condition_critically_damaged"; Name = "Critically Damaged"; Desc = "Critically damaged condition indicator, 1-19% condition, 32x32" },
    @{ Id = "condition_broken"; Name = "Broken"; Desc = "Broken condition indicator, 0% condition, 32x32" }
)

# Validate $ModPath before Join-Path
$conditionOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($conditionOutputDir)) {
    Write-Host "  [FAIL] conditionOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($conditionOutputDir)) {
    Write-Host "  [FAIL] conditionOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $conditionOutputDir)) {
    New-Item -ItemType Directory -Path $conditionOutputDir -Force | Out-Null
}

foreach ($state in $conditionStates) {
    Write-Host "Generating condition indicator: $($state.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $state.Id
            Prompt = "$($state.Desc). Condition state indicator for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $conditionOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($state.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($state.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 2. WEAR CATEGORY ICONS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Wear Category Icons" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$wearCategories = @(
    @{ Id = "wear_structural"; Name = "Structural Wear"; Desc = "Structural wear icon, physical damage, 32x32" },
    @{ Id = "wear_magical"; Name = "Magical Wear"; Desc = "Magical wear icon, magical degradation, 32x32" },
    @{ Id = "wear_ingredient"; Name = "Ingredient Wear"; Desc = "Ingredient wear icon, ingredient breakdown, 32x32" },
    @{ Id = "wear_environmental"; Name = "Environmental Wear"; Desc = "Environmental wear icon, climate damage, 32x32" },
    @{ Id = "wear_usage_fatigue"; Name = "Usage Fatigue"; Desc = "Usage fatigue icon, casting wear, 32x32" }
)

# Validate $ModPath before Join-Path
$wearOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($wearOutputDir)) {
    Write-Host "  [FAIL] wearOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($wearOutputDir)) {
    Write-Host "  [FAIL] wearOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $wearOutputDir)) {
    New-Item -ItemType Directory -Path $wearOutputDir -Force | Out-Null
}

foreach ($category in $wearCategories) {
    Write-Host "Generating wear category icon: $($category.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $category.Id
            Prompt = "$($category.Desc). Wear category icon for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $wearOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($category.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($category.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 3. REPAIR TYPE ICONS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Repair Type Icons" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$repairTypes = @(
    @{ Id = "repair_preventive"; Name = "Preventive Repair"; Desc = "Preventive repair icon, regular maintenance, 32x32" },
    @{ Id = "repair_minor"; Name = "Minor Repair"; Desc = "Minor repair icon, surface repair, 32x32" },
    @{ Id = "repair_major"; Name = "Major Repair"; Desc = "Major repair icon, structural repair, 32x32" },
    @{ Id = "repair_restoration"; Name = "Restoration"; Desc = "Restoration icon, complete overhaul, 32x32" }
)

# Validate $ModPath before Join-Path
$repairTypeOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($repairTypeOutputDir)) {
    Write-Host "  [FAIL] repairTypeOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($repairTypeOutputDir)) {
    Write-Host "  [FAIL] repairTypeOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $repairTypeOutputDir)) {
    New-Item -ItemType Directory -Path $repairTypeOutputDir -Force | Out-Null
}

foreach ($type in $repairTypes) {
    Write-Host "Generating repair type icon: $($type.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $type.Id
            Prompt = "$($type.Desc). Repair type icon for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $repairTypeOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($type.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($type.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 4. REPAIR QUALITY INDICATORS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Repair Quality Indicators" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$repairQualities = @(
    @{ Id = "quality_poor"; Name = "Poor Quality"; Desc = "Poor repair quality indicator, 60-70% effectiveness, 32x32" },
    @{ Id = "quality_basic"; Name = "Basic Quality"; Desc = "Basic repair quality indicator, 70-80% effectiveness, 32x32" },
    @{ Id = "quality_good"; Name = "Good Quality"; Desc = "Good repair quality indicator, 80-90% effectiveness, 32x32" },
    @{ Id = "quality_excellent"; Name = "Excellent Quality"; Desc = "Excellent repair quality indicator, 90-95% effectiveness, 32x32" },
    @{ Id = "quality_masterful"; Name = "Masterful Quality"; Desc = "Masterful repair quality indicator, 95-98% effectiveness, 32x32" },
    @{ Id = "quality_perfect"; Name = "Perfect Quality"; Desc = "Perfect repair quality indicator, 98-100% effectiveness, 32x32" }
)

# Validate $ModPath before Join-Path
$qualityOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($qualityOutputDir)) {
    Write-Host "  [FAIL] qualityOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($qualityOutputDir)) {
    Write-Host "  [FAIL] qualityOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $qualityOutputDir)) {
    New-Item -ItemType Directory -Path $qualityOutputDir -Force | Out-Null
}

foreach ($quality in $repairQualities) {
    Write-Host "Generating quality indicator: $($quality.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $quality.Id
            Prompt = "$($quality.Desc). Repair quality indicator for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $qualityOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($quality.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($quality.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 5. DURABILITY BAR/METER UI ELEMENTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Durability Bar/Meter UI Elements" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$durabilityUI = @(
    @{ Id = "ui_bar_background"; Name = "Durability Bar Background"; Desc = "Durability bar background texture, durability meter background, 128x16" },
    @{ Id = "ui_bar_fill_pristine"; Name = "Pristine Fill"; Desc = "Pristine durability bar fill, 100% condition fill, 128x16" },
    @{ Id = "ui_bar_fill_maintained"; Name = "Maintained Fill"; Desc = "Maintained durability bar fill, 90-99% condition fill, 128x16" },
    @{ Id = "ui_bar_fill_used"; Name = "Used Fill"; Desc = "Used durability bar fill, 70-89% condition fill, 128x16" },
    @{ Id = "ui_bar_fill_worn"; Name = "Worn Fill"; Desc = "Worn durability bar fill, 50-69% condition fill, 128x16" },
    @{ Id = "ui_bar_fill_damaged"; Name = "Damaged Fill"; Desc = "Damaged durability bar fill, 20-49% condition fill, 128x16" },
    @{ Id = "ui_bar_fill_critical"; Name = "Critical Fill"; Desc = "Critical durability bar fill, 1-19% condition fill, 128x16" },
    @{ Id = "ui_bar_fill_broken"; Name = "Broken Fill"; Desc = "Broken durability bar fill, 0% condition fill, 128x16" },
    @{ Id = "ui_meter_frame"; Name = "Durability Meter Frame"; Desc = "Durability meter frame texture, meter border, 64x64" }
)

# Validate $ModPath before Join-Path
$durabilityUIOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($durabilityUIOutputDir)) {
    Write-Host "  [FAIL] durabilityUIOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($durabilityUIOutputDir)) {
    Write-Host "  [FAIL] durabilityUIOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $durabilityUIOutputDir)) {
    New-Item -ItemType Directory -Path $durabilityUIOutputDir -Force | Out-Null
}

foreach ($element in $durabilityUI) {
    Write-Host "Generating durability UI element: $($element.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Texture"
            AssetName = $element.Id
            Prompt = "$($element.Desc). Durability UI element for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $durabilityUIOutputDir
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
# 6. REPAIR UI ELEMENTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Repair UI Elements" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$repairUI = @(
    @{ Id = "ui_panel_repair"; Name = "Repair Panel"; Desc = "Repair panel background, repair interface panel, 256x256" },
    @{ Id = "ui_panel_assessment"; Name = "Assessment Panel"; Desc = "Assessment panel background, repair assessment panel, 128x128" },
    @{ Id = "ui_tooltip_repair"; Name = "Repair Tooltip"; Desc = "Repair tooltip background, repair information tooltip, 128x128" },
    @{ Id = "ui_button_repair"; Name = "Repair Button"; Desc = "Repair button icon, perform repair, 32x32" },
    @{ Id = "ui_button_assess"; Name = "Assess Button"; Desc = "Assess button icon, assess repair needs, 32x32" },
    @{ Id = "ui_button_maintenance"; Name = "Maintenance Button"; Desc = "Maintenance button icon, perform maintenance, 32x32" },
    @{ Id = "ui_button_quick_repair"; Name = "Quick Repair Button"; Desc = "Quick repair button icon, quick repair, 32x32" },
    @{ Id = "ui_icon_ingredient"; Name = "Ingredient Icon"; Desc = "Required ingredient icon, repair ingredient, 24x24" },
    @{ Id = "ui_icon_tool"; Name = "Tool Icon"; Desc = "Required tool icon, repair tool, 24x24" },
    @{ Id = "ui_icon_skill"; Name = "Skill Icon"; Desc = "Skill requirement icon, repair skill, 24x24" }
)

# Validate $ModPath before Join-Path
$repairUIOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($repairUIOutputDir)) {
    Write-Host "  [FAIL] repairUIOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($repairUIOutputDir)) {
    Write-Host "  [FAIL] repairUIOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $repairUIOutputDir)) {
    New-Item -ItemType Directory -Path $repairUIOutputDir -Force | Out-Null
}

foreach ($element in $repairUI) {
    Write-Host "Generating repair UI element: $($element.Name)" -ForegroundColor Cyan
    
    try {
        $assetType = if ($element.Id -like "*panel*" -or $element.Id -like "*tooltip*") { "Texture" } else { "Icon" }
        
        $params = @{
            AssetType = $assetType
            AssetName = $element.Id
            Prompt = "$($element.Desc). Repair UI element for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $repairUIOutputDir
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
# 7. DAMAGE/WEAR VISUAL EFFECTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Damage/Wear Visual Effects" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$damageEffects = @(
    @{ Id = "effect_wear_structural"; Name = "Structural Wear Effect"; Desc = "Structural wear particle effect, physical damage visual, 64x64" },
    @{ Id = "effect_wear_magical"; Name = "Magical Wear Effect"; Desc = "Magical wear particle effect, magical degradation visual, 64x64" },
    @{ Id = "effect_wear_ingredient"; Name = "Ingredient Wear Effect"; Desc = "Ingredient wear particle effect, ingredient breakdown visual, 64x64" },
    @{ Id = "effect_wear_environmental"; Name = "Environmental Wear Effect"; Desc = "Environmental wear particle effect, climate damage visual, 64x64" },
    @{ Id = "effect_wear_usage"; Name = "Usage Wear Effect"; Desc = "Usage wear particle effect, casting fatigue visual, 64x64" },
    @{ Id = "effect_damage_critical"; Name = "Critical Damage Effect"; Desc = "Critical damage particle effect, severe damage visual, 64x64" },
    @{ Id = "effect_break"; Name = "Break Effect"; Desc = "Break particle effect, item breaking visual, 64x64" }
)

# Validate $ModPath before Join-Path
$damageOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($damageOutputDir)) {
    Write-Host "  [FAIL] damageOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($damageOutputDir)) {
    Write-Host "  [FAIL] damageOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $damageOutputDir)) {
    New-Item -ItemType Directory -Path $damageOutputDir -Force | Out-Null
}

foreach ($effect in $damageEffects) {
    Write-Host "Generating damage effect: $($effect.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Particle"
            AssetName = $effect.Id
            Prompt = "$($effect.Desc). Damage/wear visual effect for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $damageOutputDir
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
# 8. REPAIR VISUAL EFFECTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Repair Visual Effects" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$repairEffects = @(
    @{ Id = "effect_repair_preventive"; Name = "Preventive Repair Effect"; Desc = "Preventive repair particle effect, maintenance visual, 64x64" },
    @{ Id = "effect_repair_minor"; Name = "Minor Repair Effect"; Desc = "Minor repair particle effect, surface repair visual, 64x64" },
    @{ Id = "effect_repair_major"; Name = "Major Repair Effect"; Desc = "Major repair particle effect, structural repair visual, 64x64" },
    @{ Id = "effect_repair_restoration"; Name = "Restoration Effect"; Desc = "Restoration particle effect, complete overhaul visual, 64x64" },
    @{ Id = "effect_repair_success"; Name = "Repair Success Effect"; Desc = "Repair success particle effect, successful repair visual, 64x64" },
    @{ Id = "effect_repair_fail"; Name = "Repair Fail Effect"; Desc = "Repair fail particle effect, failed repair visual, 64x64" }
)

# Validate $ModPath before Join-Path
$repairEffectOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($repairEffectOutputDir)) {
    Write-Host "  [FAIL] repairEffectOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($repairEffectOutputDir)) {
    Write-Host "  [FAIL] repairEffectOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $repairEffectOutputDir)) {
    New-Item -ItemType Directory -Path $repairEffectOutputDir -Force | Out-Null
}

foreach ($effect in $repairEffects) {
    Write-Host "Generating repair effect: $($effect.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Particle"
            AssetName = $effect.Id
            Prompt = "$($effect.Desc). Repair visual effect for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $repairEffectOutputDir
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
# 9. CONDITION OVERLAY TEXTURES
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Condition Overlay Textures" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$overlays = @(
    @{ Id = "overlay_pristine"; Name = "Pristine Overlay"; Desc = "Pristine condition overlay texture, perfect condition visual, 64x64" },
    @{ Id = "overlay_maintained"; Name = "Maintained Overlay"; Desc = "Maintained condition overlay texture, good condition visual, 64x64" },
    @{ Id = "overlay_used"; Name = "Used Overlay"; Desc = "Used condition overlay texture, used condition visual, 64x64" },
    @{ Id = "overlay_worn"; Name = "Worn Overlay"; Desc = "Worn condition overlay texture, worn condition visual, 64x64" },
    @{ Id = "overlay_damaged"; Name = "Damaged Overlay"; Desc = "Damaged condition overlay texture, damaged condition visual, 64x64" },
    @{ Id = "overlay_critical"; Name = "Critical Overlay"; Desc = "Critical condition overlay texture, critical condition visual, 64x64" },
    @{ Id = "overlay_broken"; Name = "Broken Overlay"; Desc = "Broken condition overlay texture, broken condition visual, 64x64" }
)

# Validate $ModPath before Join-Path
$overlayOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($overlayOutputDir)) {
    Write-Host "  [FAIL] overlayOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($overlayOutputDir)) {
    Write-Host "  [FAIL] overlayOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $overlayOutputDir)) {
    New-Item -ItemType Directory -Path $overlayOutputDir -Force | Out-Null
}

foreach ($overlay in $overlays) {
    Write-Host "Generating overlay: $($overlay.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Texture"
            AssetName = $overlay.Id
            Prompt = "$($overlay.Desc). Condition overlay texture for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $overlayOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($overlay.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($overlay.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 10. DURABILITY STATUS ICONS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Durability Status Icons" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$statusIcons = @(
    @{ Id = "status_durability"; Name = "Durability Status"; Desc = "Durability status icon, durability indicator, 32x32" },
    @{ Id = "status_repair_needed"; Name = "Repair Needed"; Desc = "Repair needed icon, requires repair, 32x32" },
    @{ Id = "status_maintenance_needed"; Name = "Maintenance Needed"; Desc = "Maintenance needed icon, requires maintenance, 32x32" },
    @{ Id = "status_repairing"; Name = "Repairing"; Desc = "Repairing icon, currently repairing, 32x32" },
    @{ Id = "status_repairable"; Name = "Repairable"; Desc = "Repairable icon, can be repaired, 32x32" },
    @{ Id = "status_beyond_repair"; Name = "Beyond Repair"; Desc = "Beyond repair icon, cannot be repaired, 32x32" }
)

# Validate $ModPath before Join-Path
$statusOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($statusOutputDir)) {
    Write-Host "  [FAIL] statusOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($statusOutputDir)) {
    Write-Host "  [FAIL] statusOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $statusOutputDir)) {
    New-Item -ItemType Directory -Path $statusOutputDir -Force | Out-Null
}

foreach ($icon in $statusIcons) {
    Write-Host "Generating status icon: $($icon.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $icon.Id
            Prompt = "$($icon.Desc). Durability status icon for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $statusOutputDir
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
Write-Host "  Condition States: $(Join-Path $ModPath 'assets\durability\conditions')" -ForegroundColor Gray
Write-Host "  Wear Categories: $(Join-Path $ModPath 'assets\durability\wear')" -ForegroundColor Gray
Write-Host "  Repair Types: $(Join-Path $ModPath 'assets\durability\repair_types')" -ForegroundColor Gray
Write-Host "  Repair Quality: $(Join-Path $ModPath 'assets\durability\quality')" -ForegroundColor Gray
Write-Host "  Durability UI: $(Join-Path $ModPath 'assets\durability\ui\bars')" -ForegroundColor Gray
Write-Host "  Repair UI: $(Join-Path $ModPath 'assets\durability\ui\repair')" -ForegroundColor Gray
Write-Host "  Damage Effects: $(Join-Path $ModPath 'assets\durability\effects\damage')" -ForegroundColor Gray
Write-Host "  Repair Effects: $(Join-Path $ModPath 'assets\durability\effects\repair')" -ForegroundColor Gray
Write-Host "  Condition Overlays: $(Join-Path $ModPath 'assets\durability\overlays')" -ForegroundColor Gray
Write-Host "  Status Icons: $(Join-Path $ModPath 'assets\durability\status')" -ForegroundColor Gray
Write-Host ""
