#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate assets for the Taming System.
    
.DESCRIPTION
    Generates sprites, icons, and effects for:
    - Taming state indicators
    - Affinity UI elements
    - Taming progress indicators
    - Food item icons
    - Taming effect particles
    - Pet/companion status indicators
    
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
Write-Host "  Taming System Asset Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$generated = 0
$failed = 0

# ============================================================
# 1. TAMING STATE INDICATORS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Taming State Indicators" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$tamingStates = @(
    @{ Id = "taming_state_wild"; Name = "Wild State"; Desc = "Wild creature state indicator icon, untamed creature, 32x32" },
    @{ Id = "taming_state_in_progress"; Name = "Taming In Progress"; Desc = "Taming in progress indicator icon, creature being tamed, 32x32" },
    @{ Id = "taming_state_tamed"; Name = "Tamed State"; Desc = "Tamed creature state indicator icon, tamed creature, 32x32" },
    @{ Id = "taming_state_failed"; Name = "Taming Failed"; Desc = "Taming failed indicator icon, failed taming attempt, 32x32" }
)

# Validate $ModPath before Join-Path
$stateOutputDir = Join-Path $ModPath "assets"
if ([string]::IsNullOrWhiteSpace($stateOutputDir)) {
    Write-Host "  [FAIL] stateOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    Write-Host "  Skipping taming state generation" -ForegroundColor Yellow
} else {
    if (-not (Test-Path $stateOutputDir)) {
        New-Item -ItemType Directory -Path $stateOutputDir -Force | Out-Null
    }
}

if (-not [string]::IsNullOrWhiteSpace($stateOutputDir)) {
    foreach ($state in $tamingStates) {
        Write-Host "Generating taming state indicator: $($state.Name)" -ForegroundColor Cyan
        
        try {
            $params = @{
                AssetType = "Icon"
                AssetName = $state.Id
                Prompt = "$($state.Desc). Taming state indicator for Starbound taming system."
                OllamaModel = $OllamaModel
                OutputDir = $stateOutputDir
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
}

# ============================================================
# 2. AFFINITY UI ELEMENTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Affinity UI Elements" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$affinityUI = @(
    @{ Id = "affinity_bar"; Name = "Affinity Bar"; Desc = "Affinity bar UI element, creature affinity indicator, 32x8" },
    @{ Id = "affinity_positive"; Name = "Positive Affinity"; Desc = "Positive affinity indicator icon, high affinity, 32x32" },
    @{ Id = "affinity_neutral"; Name = "Neutral Affinity"; Desc = "Neutral affinity indicator icon, neutral affinity, 32x32" },
    @{ Id = "affinity_negative"; Name = "Negative Affinity"; Desc = "Negative affinity indicator icon, low affinity, 32x32" },
    @{ Id = "affinity_increase"; Name = "Affinity Increase"; Desc = "Affinity increase effect icon, affinity going up, 16x16" },
    @{ Id = "affinity_decrease"; Name = "Affinity Decrease"; Desc = "Affinity decrease effect icon, affinity going down, 16x16" }
)

# Validate $ModPath before Join-Path
$affinityOutputDir = Join-Path $ModPath "assets"
if ([string]::IsNullOrWhiteSpace($affinityOutputDir)) {
    Write-Host "  [FAIL] affinityOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    Write-Host "  Skipping affinity UI generation" -ForegroundColor Yellow
} else {
    if (-not (Test-Path $affinityOutputDir)) {
        New-Item -ItemType Directory -Path $affinityOutputDir -Force | Out-Null
    }
}

if (-not [string]::IsNullOrWhiteSpace($affinityOutputDir)) {
    foreach ($affinity in $affinityUI) {
        Write-Host "Generating affinity UI element: $($affinity.Name)" -ForegroundColor Cyan
        
        try {
            $params = @{
                AssetType = "Icon"
                AssetName = $affinity.Id
                Prompt = "$($affinity.Desc). Affinity UI element for Starbound taming system."
                OllamaModel = $OllamaModel
                OutputDir = $affinityOutputDir
            }
            
            $params['UseCppBackend'] = $UseCppBackend
            
            & $assetGenerator @params | Out-Null
            
            $generated++
            Write-Host "  [OK] Generated: $($affinity.Name)" -ForegroundColor Green
        } catch {
            $failed++
            Write-Host "  [FAIL] $($affinity.Name) : $_" -ForegroundColor Red
        }
        
        Write-Host ""
    }
}

# ============================================================
# 3. TAMING PROGRESS INDICATORS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Taming Progress Indicators" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$progressIndicators = @(
    @{ Id = "taming_progress_bar"; Name = "Taming Progress Bar"; Desc = "Taming progress bar UI element, progress indicator, 32x8" },
    @{ Id = "taming_progress_0"; Name = "Progress 0%"; Desc = "Taming progress 0% indicator, no progress, 16x16" },
    @{ Id = "taming_progress_25"; Name = "Progress 25%"; Desc = "Taming progress 25% indicator, quarter progress, 16x16" },
    @{ Id = "taming_progress_50"; Name = "Progress 50%"; Desc = "Taming progress 50% indicator, half progress, 16x16" },
    @{ Id = "taming_progress_75"; Name = "Progress 75%"; Desc = "Taming progress 75% indicator, three quarters progress, 16x16" },
    @{ Id = "taming_progress_100"; Name = "Progress 100%"; Desc = "Taming progress 100% indicator, complete, 16x16" }
)

# Validate $ModPath before Join-Path
$progressOutputDir = Join-Path $ModPath "assets"
if ([string]::IsNullOrWhiteSpace($progressOutputDir)) {
    Write-Host "  [FAIL] progressOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    Write-Host "  Skipping progress indicator generation" -ForegroundColor Yellow
} else {
    if (-not (Test-Path $progressOutputDir)) {
        New-Item -ItemType Directory -Path $progressOutputDir -Force | Out-Null
    }
}

if (-not [string]::IsNullOrWhiteSpace($progressOutputDir)) {
    foreach ($progress in $progressIndicators) {
        Write-Host "Generating progress indicator: $($progress.Name)" -ForegroundColor Cyan
        
        try {
            $params = @{
                AssetType = "Icon"
                AssetName = $progress.Id
                Prompt = "$($progress.Desc). Taming progress indicator for Starbound taming system."
                OllamaModel = $OllamaModel
                OutputDir = $progressOutputDir
            }
            
            $params['UseCppBackend'] = $UseCppBackend
            
            & $assetGenerator @params | Out-Null
            
            $generated++
            Write-Host "  [OK] Generated: $($progress.Name)" -ForegroundColor Green
        } catch {
            $failed++
            Write-Host "  [FAIL] $($progress.Name) : $_" -ForegroundColor Red
        }
        
        Write-Host ""
    }
}

# ============================================================
# 4. FOOD ITEM ICONS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Food Item Icons" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$foodItems = @(
    @{ Id = "food_meat"; Name = "Meat Food"; Desc = "Meat food item icon, raw meat, 32x32" },
    @{ Id = "food_fish"; Name = "Fish Food"; Desc = "Fish food item icon, raw fish, 32x32" },
    @{ Id = "food_vegetable"; Name = "Vegetable Food"; Desc = "Vegetable food item icon, plant food, 32x32" },
    @{ Id = "food_fruit"; Name = "Fruit Food"; Desc = "Fruit food item icon, fruit food, 32x32" },
    @{ Id = "food_berry"; Name = "Berry Food"; Desc = "Berry food item icon, small berries, 32x32" },
    @{ Id = "food_treat"; Name = "Pet Treat"; Desc = "Pet treat item icon, special treat, 32x32" },
    @{ Id = "food_poison"; Name = "Poison Food"; Desc = "Poison food item icon, toxic food, 32x32" }
)

# Validate $ModPath before Join-Path
$foodOutputDir = Join-Path $ModPath "assets"
if ([string]::IsNullOrWhiteSpace($foodOutputDir)) {
    Write-Host "  [FAIL] foodOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    Write-Host "  Skipping food item generation" -ForegroundColor Yellow
} else {
    if (-not (Test-Path $foodOutputDir)) {
        New-Item -ItemType Directory -Path $foodOutputDir -Force | Out-Null
    }
}

if (-not [string]::IsNullOrWhiteSpace($foodOutputDir)) {
    foreach ($food in $foodItems) {
    Write-Host "Generating food item icon: $($food.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $food.Id
            Prompt = "$($food.Desc). Food item icon for Starbound taming system."
            OllamaModel = $OllamaModel
            OutputDir = $foodOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($food.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($food.Name) : $_" -ForegroundColor Red
    }
    
        Write-Host ""
    }
}

# ============================================================
# 5. TAMING EFFECT PARTICLES
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Taming Effect Particles" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$tamingEffects = @(
    @{ Id = "taming_effect_start"; Name = "Taming Start Effect"; Desc = "Taming start particle effect, taming initiation" },
    @{ Id = "taming_effect_progress"; Name = "Taming Progress Effect"; Desc = "Taming progress particle effect, ongoing taming" },
    @{ Id = "taming_effect_success"; Name = "Taming Success Effect"; Desc = "Taming success particle effect, successful taming" },
    @{ Id = "taming_effect_failure"; Name = "Taming Failure Effect"; Desc = "Taming failure particle effect, failed taming" },
    @{ Id = "taming_effect_food_positive"; Name = "Food Positive Effect"; Desc = "Food positive reaction particle effect, creature likes food" },
    @{ Id = "taming_effect_food_negative"; Name = "Food Negative Effect"; Desc = "Food negative reaction particle effect, creature dislikes food" }
)

# Validate $ModPath before Join-Path
$effectOutputDir = Join-Path $ModPath "assets"
if ([string]::IsNullOrWhiteSpace($effectOutputDir)) {
    Write-Host "  [FAIL] effectOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    Write-Host "  Skipping taming effect generation" -ForegroundColor Yellow
} else {
    if (-not (Test-Path $effectOutputDir)) {
        New-Item -ItemType Directory -Path $effectOutputDir -Force | Out-Null
    }
}

if (-not [string]::IsNullOrWhiteSpace($effectOutputDir)) {
        foreach ($effect in $tamingEffects) {
        Write-Host "Generating taming effect: $($effect.Name)" -ForegroundColor Cyan
        
        try {
            $params = @{
                AssetType = "Particle"
                AssetName = $effect.Id
                Prompt = "$($effect.Desc). Taming effect for Starbound taming system."
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
}

# ============================================================
# 6. PET/COMPANION STATUS INDICATORS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Pet/Companion Status Indicators" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$petStatus = @(
    @{ Id = "pet_status_healthy"; Name = "Pet Healthy"; Desc = "Pet healthy status indicator icon, healthy pet, 32x32" },
    @{ Id = "pet_status_hungry"; Name = "Pet Hungry"; Desc = "Pet hungry status indicator icon, hungry pet, 32x32" },
    @{ Id = "pet_status_injured"; Name = "Pet Injured"; Desc = "Pet injured status indicator icon, injured pet, 32x32" },
    @{ Id = "pet_status_following"; Name = "Pet Following"; Desc = "Pet following status indicator icon, pet following, 32x32" },
    @{ Id = "pet_status_staying"; Name = "Pet Staying"; Desc = "Pet staying status indicator icon, pet staying, 32x32" },
    @{ Id = "pet_status_attacking"; Name = "Pet Attacking"; Desc = "Pet attacking status indicator icon, pet in combat, 32x32" }
)

# Validate $ModPath before Join-Path
$petStatusOutputDir = Join-Path $ModPath "assets"
if ([string]::IsNullOrWhiteSpace($petStatusOutputDir)) {
    Write-Host "  [FAIL] petStatusOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    Write-Host "  Skipping pet status generation" -ForegroundColor Yellow
} else {
    if (-not (Test-Path $petStatusOutputDir)) {
        New-Item -ItemType Directory -Path $petStatusOutputDir -Force | Out-Null
    }
}

if (-not [string]::IsNullOrWhiteSpace($petStatusOutputDir)) {
        foreach ($status in $petStatus) {
        Write-Host "Generating pet status indicator: $($status.Name)" -ForegroundColor Cyan
        
        try {
            $params = @{
                AssetType = "Icon"
                AssetName = $status.Id
                Prompt = "$($status.Desc). Pet status indicator for Starbound taming system."
                OllamaModel = $OllamaModel
                OutputDir = $petStatusOutputDir
            }
            
            $params['UseCppBackend'] = $UseCppBackend
            
            & $assetGenerator @params | Out-Null
            
            $generated++
            Write-Host "  [OK] Generated: $($status.Name)" -ForegroundColor Green
        } catch {
            $failed++
            Write-Host "  [FAIL] $($status.Name) : $_" -ForegroundColor Red
        }
        
        Write-Host ""
    }
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
Write-Host "  Taming States: $(Join-Path $ModPath 'assets\taming\states')" -ForegroundColor Gray
Write-Host "  Affinity UI: $(Join-Path $ModPath 'assets\taming\affinity')" -ForegroundColor Gray
Write-Host "  Progress Indicators: $(Join-Path $ModPath 'assets\taming\progress')" -ForegroundColor Gray
Write-Host "  Food Items: $(Join-Path $ModPath 'assets\taming\food')" -ForegroundColor Gray
Write-Host "  Taming Effects: $(Join-Path $ModPath 'assets\taming\effects')" -ForegroundColor Gray
Write-Host "  Pet Status: $(Join-Path $ModPath 'assets\taming\pet_status')" -ForegroundColor Gray
Write-Host ""
