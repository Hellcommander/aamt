#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate assets for the Skill System.
    
.DESCRIPTION
    Generates icons, UI elements, and effects for:
    - Skill category icons
    - Skill tier indicators
    - Skill type indicators
    - Skill tree UI elements
    - XP progress bars
    - Skill level indicators
    - Decay indicators
    - Mastery indicators
    - Specialization icons
    - Skill combo indicators
    
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
    [bool]$UseCppBackend = $true)

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
Write-Host "  Skill System Asset Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$generated = 0
$failed = 0

# ============================================================
# 1. SKILL CATEGORY ICONS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Skill Category Icons" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$skillCategories = @(
    @{ Id = "skill_category_combat"; Name = "Combat Skill"; Desc = "Combat skill category icon, combat skills, 32x32" },
    @{ Id = "skill_category_magic"; Name = "Magic Skill"; Desc = "Magic skill category icon, magic skills, 32x32" },
    @{ Id = "skill_category_crafting"; Name = "Crafting Skill"; Desc = "Crafting skill category icon, crafting skills, 32x32" },
    @{ Id = "skill_category_technology"; Name = "Technology Skill"; Desc = "Technology skill category icon, tech skills, 32x32" },
    @{ Id = "skill_category_survival"; Name = "Survival Skill"; Desc = "Survival skill category icon, survival skills, 32x32" },
    @{ Id = "skill_category_social"; Name = "Social Skill"; Desc = "Social skill category icon, social skills, 32x32" },
    @{ Id = "skill_category_movement"; Name = "Movement Skill"; Desc = "Movement skill category icon, movement skills, 32x32" },
    @{ Id = "skill_category_defense"; Name = "Defense Skill"; Desc = "Defense skill category icon, defense skills, 32x32" },
    @{ Id = "skill_category_utility"; Name = "Utility Skill"; Desc = "Utility skill category icon, utility skills, 32x32" },
    @{ Id = "skill_category_mastery"; Name = "Mastery Skill"; Desc = "Mastery skill category icon, mastery skills, 32x32" }
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

foreach ($category in $skillCategories) {
    Write-Host "Generating skill category icon: $($category.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $category.Id
            Prompt = "$($category.Desc). Skill category icon for Starbound skill system."
            OllamaModel = $OllamaModel
            OutputDir = $categoryOutputDir
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
# 2. SKILL TIER INDICATORS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Skill Tier Indicators" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$skillTiers = @(
    @{ Id = "skill_tier_common"; Name = "Common Tier"; Desc = "Common skill tier indicator, common rarity, 16x16" },
    @{ Id = "skill_tier_uncommon"; Name = "Uncommon Tier"; Desc = "Uncommon skill tier indicator, uncommon rarity, 16x16" },
    @{ Id = "skill_tier_rare"; Name = "Rare Tier"; Desc = "Rare skill tier indicator, rare rarity, 16x16" },
    @{ Id = "skill_tier_epic"; Name = "Epic Tier"; Desc = "Epic skill tier indicator, epic rarity, 16x16" },
    @{ Id = "skill_tier_legendary"; Name = "Legendary Tier"; Desc = "Legendary skill tier indicator, legendary rarity, 16x16" },
    @{ Id = "skill_tier_mythic"; Name = "Mythic Tier"; Desc = "Mythic skill tier indicator, mythic rarity, 16x16" },
    @{ Id = "skill_tier_transcendent"; Name = "Transcendent Tier"; Desc = "Transcendent skill tier indicator, transcendent rarity, 16x16" }
)

# Validate $ModPath before Join-Path
$tierOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($tierOutputDir)) {
    Write-Host "  [FAIL] tierOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($tierOutputDir)) {
    Write-Host "  [FAIL] tierOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $tierOutputDir)) {
    New-Item -ItemType Directory -Path $tierOutputDir -Force | Out-Null
}

foreach ($tier in $skillTiers) {
    Write-Host "Generating skill tier indicator: $($tier.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $tier.Id
            Prompt = "$($tier.Desc). Skill tier indicator for Starbound skill system."
            OllamaModel = $OllamaModel
            OutputDir = $tierOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($tier.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($tier.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 3. SKILL TYPE INDICATORS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Skill Type Indicators" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$skillTypes = @(
    @{ Id = "skill_type_active"; Name = "Active Skill"; Desc = "Active skill type indicator, active skill, 16x16" },
    @{ Id = "skill_type_passive"; Name = "Passive Skill"; Desc = "Passive skill type indicator, passive skill, 16x16" },
    @{ Id = "skill_type_triggered"; Name = "Triggered Skill"; Desc = "Triggered skill type indicator, triggered skill, 16x16" },
    @{ Id = "skill_type_channeled"; Name = "Channeled Skill"; Desc = "Channeled skill type indicator, channeled skill, 16x16" },
    @{ Id = "skill_type_toggle"; Name = "Toggle Skill"; Desc = "Toggle skill type indicator, toggle skill, 16x16" },
    @{ Id = "skill_type_combo"; Name = "Combo Skill"; Desc = "Combo skill type indicator, combo skill, 16x16" }
)

# Validate $ModPath before Join-Path
$typeOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($typeOutputDir)) {
    Write-Host "  [FAIL] typeOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($typeOutputDir)) {
    Write-Host "  [FAIL] typeOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $typeOutputDir)) {
    New-Item -ItemType Directory -Path $typeOutputDir -Force | Out-Null
}

foreach ($type in $skillTypes) {
    Write-Host "Generating skill type indicator: $($type.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $type.Id
            Prompt = "$($type.Desc). Skill type indicator for Starbound skill system."
            OllamaModel = $OllamaModel
            OutputDir = $typeOutputDir
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
# 4. SKILL TREE UI ELEMENTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Skill Tree UI Elements" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$skillTreeUI = @(
    @{ Id = "skill_tree_node_unlocked"; Name = "Unlocked Node"; Desc = "Skill tree unlocked node icon, unlocked skill, 32x32" },
    @{ Id = "skill_tree_node_locked"; Name = "Locked Node"; Desc = "Skill tree locked node icon, locked skill, 32x32" },
    @{ Id = "skill_tree_node_available"; Name = "Available Node"; Desc = "Skill tree available node icon, available skill, 32x32" },
    @{ Id = "skill_tree_connection"; Name = "Skill Connection"; Desc = "Skill tree connection line, skill prerequisite, 32x4" },
    @{ Id = "skill_tree_background"; Name = "Skill Tree Background"; Desc = "Skill tree background texture, tree background, 256x256" }
)

# Validate $ModPath before Join-Path
$skillTreeOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($skillTreeOutputDir)) {
    Write-Host "  [FAIL] skillTreeOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($skillTreeOutputDir)) {
    Write-Host "  [FAIL] skillTreeOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $skillTreeOutputDir)) {
    New-Item -ItemType Directory -Path $skillTreeOutputDir -Force | Out-Null
}

foreach ($ui in $skillTreeUI) {
    Write-Host "Generating skill tree UI element: $($ui.Name)" -ForegroundColor Cyan
    
    try {
        $assetType = if ($ui.Id -like "*background*") { "Texture" } else { "Icon" }
        
        $params = @{
            AssetType = $assetType
            AssetName = $ui.Id
            Prompt = "$($ui.Desc). Skill tree UI element for Starbound skill system."
            OllamaModel = $OllamaModel
            OutputDir = $skillTreeOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($ui.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($ui.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 5. XP PROGRESS INDICATORS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating XP Progress Indicators" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$xpIndicators = @(
    @{ Id = "xp_bar"; Name = "XP Bar"; Desc = "XP progress bar UI element, experience bar, 32x8" },
    @{ Id = "xp_gain_effect"; Name = "XP Gain Effect"; Desc = "XP gain particle effect, experience gained" },
    @{ Id = "xp_milestone"; Name = "XP Milestone"; Desc = "XP milestone indicator icon, milestone reached, 32x32" },
    @{ Id = "level_up_effect"; Name = "Level Up Effect"; Desc = "Level up particle effect, skill leveled up" }
)

# Validate $ModPath before Join-Path
$xpOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($xpOutputDir)) {
    Write-Host "  [FAIL] xpOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($xpOutputDir)) {
    Write-Host "  [FAIL] xpOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $xpOutputDir)) {
    New-Item -ItemType Directory -Path $xpOutputDir -Force | Out-Null
}

foreach ($indicator in $xpIndicators) {
    Write-Host "Generating XP indicator: $($indicator.Name)" -ForegroundColor Cyan
    
    try {
        $assetType = if ($indicator.Id -like "*bar*") { "Icon" } elseif ($indicator.Id -like "*effect*") { "Particle" } else { "Icon" }
        
        $params = @{
            AssetType = $assetType
            AssetName = $indicator.Id
            Prompt = "$($indicator.Desc). XP indicator for Starbound skill system."
            OllamaModel = $OllamaModel
            OutputDir = $xpOutputDir
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
# 6. SKILL LEVEL INDICATORS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Skill Level Indicators" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$levelIndicators = @(
    @{ Id = "skill_level_1"; Name = "Level 1"; Desc = "Skill level 1 indicator, level 1, 16x16" },
    @{ Id = "skill_level_5"; Name = "Level 5"; Desc = "Skill level 5 indicator, level 5, 16x16" },
    @{ Id = "skill_level_10"; Name = "Level 10"; Desc = "Skill level 10 indicator, max level, 16x16" },
    @{ Id = "skill_level_max"; Name = "Max Level"; Desc = "Skill max level indicator, maximum level, 32x32" }
)

# Validate $ModPath before Join-Path
$levelOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($levelOutputDir)) {
    Write-Host "  [FAIL] levelOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($levelOutputDir)) {
    Write-Host "  [FAIL] levelOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $levelOutputDir)) {
    New-Item -ItemType Directory -Path $levelOutputDir -Force | Out-Null
}

foreach ($indicator in $levelIndicators) {
    Write-Host "Generating level indicator: $($indicator.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $indicator.Id
            Prompt = "$($indicator.Desc). Skill level indicator for Starbound skill system."
            OllamaModel = $OllamaModel
            OutputDir = $levelOutputDir
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
# 7. DECAY INDICATORS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Decay Indicators" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$decayIndicators = @(
    @{ Id = "skill_decay_indicator"; Name = "Decay Indicator"; Desc = "Skill decay indicator icon, skill decaying, 32x32" },
    @{ Id = "skill_decay_warning"; Name = "Decay Warning"; Desc = "Skill decay warning icon, decay warning, 32x32" },
    @{ Id = "skill_retention_high"; Name = "High Retention"; Desc = "High retention indicator icon, good retention, 32x32" },
    @{ Id = "skill_retention_low"; Name = "Low Retention"; Desc = "Low retention indicator icon, poor retention, 32x32" },
    @{ Id = "skill_practice_effect"; Name = "Practice Effect"; Desc = "Skill practice particle effect, practicing skill" }
)

# Validate $ModPath before Join-Path
$decayOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($decayOutputDir)) {
    Write-Host "  [FAIL] decayOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($decayOutputDir)) {
    Write-Host "  [FAIL] decayOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $decayOutputDir)) {
    New-Item -ItemType Directory -Path $decayOutputDir -Force | Out-Null
}

foreach ($indicator in $decayIndicators) {
    Write-Host "Generating decay indicator: $($indicator.Name)" -ForegroundColor Cyan
    
    try {
        $assetType = if ($indicator.Id -like "*effect*") { "Particle" } else { "Icon" }
        
        $params = @{
            AssetType = $assetType
            AssetName = $indicator.Id
            Prompt = "$($indicator.Desc). Decay indicator for Starbound skill system."
            OllamaModel = $OllamaModel
            OutputDir = $decayOutputDir
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
# 8. MASTERY INDICATORS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Mastery Indicators" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$masteryIndicators = @(
    @{ Id = "mastery_icon"; Name = "Mastery Icon"; Desc = "Mastery indicator icon, skill mastery, 32x32" },
    @{ Id = "mastery_unlocked"; Name = "Mastery Unlocked"; Desc = "Mastery unlocked indicator icon, mastery achieved, 32x32" },
    @{ Id = "mastery_progress"; Name = "Mastery Progress"; Desc = "Mastery progress indicator icon, mastery progress, 32x32" },
    @{ Id = "mastery_effect"; Name = "Mastery Effect"; Desc = "Mastery particle effect, mastery achievement" }
)

# Validate $ModPath before Join-Path
$masteryOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($masteryOutputDir)) {
    Write-Host "  [FAIL] masteryOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($masteryOutputDir)) {
    Write-Host "  [FAIL] masteryOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $masteryOutputDir)) {
    New-Item -ItemType Directory -Path $masteryOutputDir -Force | Out-Null
}

foreach ($indicator in $masteryIndicators) {
    Write-Host "Generating mastery indicator: $($indicator.Name)" -ForegroundColor Cyan
    
    try {
        $assetType = if ($indicator.Id -like "*effect*") { "Particle" } else { "Icon" }
        
        $params = @{
            AssetType = $assetType
            AssetName = $indicator.Id
            Prompt = "$($indicator.Desc). Mastery indicator for Starbound skill system."
            OllamaModel = $OllamaModel
            OutputDir = $masteryOutputDir
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
# 9. SPECIALIZATION ICONS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Specialization Icons" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$specializationIcons = @(
    @{ Id = "specialization_icon"; Name = "Specialization Icon"; Desc = "Specialization indicator icon, skill specialization, 32x32" },
    @{ Id = "specialization_selected"; Name = "Specialization Selected"; Desc = "Specialization selected indicator icon, specialization active, 32x32" },
    @{ Id = "specialization_available"; Name = "Specialization Available"; Desc = "Specialization available indicator icon, specialization available, 32x32" }
)

# Validate $ModPath before Join-Path
$specializationOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($specializationOutputDir)) {
    Write-Host "  [FAIL] specializationOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($specializationOutputDir)) {
    Write-Host "  [FAIL] specializationOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $specializationOutputDir)) {
    New-Item -ItemType Directory -Path $specializationOutputDir -Force | Out-Null
}

foreach ($icon in $specializationIcons) {
    Write-Host "Generating specialization icon: $($icon.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $icon.Id
            Prompt = "$($icon.Desc). Specialization icon for Starbound skill system."
            OllamaModel = $OllamaModel
            OutputDir = $specializationOutputDir
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
# 10. SKILL COMBO INDICATORS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Skill Combo Indicators" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$comboIndicators = @(
    @{ Id = "combo_indicator"; Name = "Combo Indicator"; Desc = "Skill combo indicator icon, combo available, 32x32" },
    @{ Id = "combo_active"; Name = "Combo Active"; Desc = "Combo active indicator icon, combo in progress, 32x32" },
    @{ Id = "combo_execute"; Name = "Combo Execute"; Desc = "Combo execute effect, combo executed, particle effect" }
)

# Validate $ModPath before Join-Path
$comboOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($comboOutputDir)) {
    Write-Host "  [FAIL] comboOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($comboOutputDir)) {
    Write-Host "  [FAIL] comboOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $comboOutputDir)) {
    New-Item -ItemType Directory -Path $comboOutputDir -Force | Out-Null
}

foreach ($indicator in $comboIndicators) {
    Write-Host "Generating combo indicator: $($indicator.Name)" -ForegroundColor Cyan
    
    try {
        $assetType = if ($indicator.Id -like "*execute*") { "Particle" } else { "Icon" }
        
        $params = @{
            AssetType = $assetType
            AssetName = $indicator.Id
            Prompt = "$($indicator.Desc). Combo indicator for Starbound skill system."
            OllamaModel = $OllamaModel
            OutputDir = $comboOutputDir
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
# 11. COOLDOWN INDICATORS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Cooldown Indicators" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$cooldownIndicators = @(
    @{ Id = "skill_cooldown_indicator"; Name = "Cooldown Indicator"; Desc = "Skill cooldown indicator icon, skill on cooldown, 32x32" },
    @{ Id = "skill_cooldown_bar"; Name = "Cooldown Bar"; Desc = "Skill cooldown bar UI element, cooldown progress, 32x8" },
    @{ Id = "skill_ready"; Name = "Skill Ready"; Desc = "Skill ready indicator icon, skill available, 32x32" }
)

# Validate $ModPath before Join-Path
$cooldownOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($cooldownOutputDir)) {
    Write-Host "  [FAIL] cooldownOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($cooldownOutputDir)) {
    Write-Host "  [FAIL] cooldownOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $cooldownOutputDir)) {
    New-Item -ItemType Directory -Path $cooldownOutputDir -Force | Out-Null
}

foreach ($indicator in $cooldownIndicators) {
    Write-Host "Generating cooldown indicator: $($indicator.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $indicator.Id
            Prompt = "$($indicator.Desc). Cooldown indicator for Starbound skill system."
            OllamaModel = $OllamaModel
            OutputDir = $cooldownOutputDir
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
Write-Host "  Skill Categories: $(Join-Path $ModPath 'assets\skills\categories')" -ForegroundColor Gray
Write-Host "  Skill Tiers: $(Join-Path $ModPath 'assets\skills\tiers')" -ForegroundColor Gray
Write-Host "  Skill Types: $(Join-Path $ModPath 'assets\skills\types')" -ForegroundColor Gray
Write-Host "  Skill Tree: $(Join-Path $ModPath 'assets\skills\skill_tree')" -ForegroundColor Gray
Write-Host "  XP Indicators: $(Join-Path $ModPath 'assets\skills\xp')" -ForegroundColor Gray
Write-Host "  Level Indicators: $(Join-Path $ModPath 'assets\skills\levels')" -ForegroundColor Gray
Write-Host "  Decay Indicators: $(Join-Path $ModPath 'assets\skills\decay')" -ForegroundColor Gray
Write-Host "  Mastery Indicators: $(Join-Path $ModPath 'assets\skills\mastery')" -ForegroundColor Gray
Write-Host "  Specialization: $(Join-Path $ModPath 'assets\skills\specialization')" -ForegroundColor Gray
Write-Host "  Combo Indicators: $(Join-Path $ModPath 'assets\skills\combo')" -ForegroundColor Gray
Write-Host "  Cooldown Indicators: $(Join-Path $ModPath 'assets\skills\cooldown')" -ForegroundColor Gray
Write-Host ""
