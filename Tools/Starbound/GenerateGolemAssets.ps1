#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate assets for the Golem System.
    
.DESCRIPTION
    Generates visual assets for:
    - Golem sprites (different golem types)
    - Golem part sprites
    - Golem blueprint icons
    - Golem stance animations
    - Golem summon effects
    - Golem command indicators
    - Golem circuit icons
    - Golem material icons
    
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
Write-Host "  Golem System Asset Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$generated = 0
$failed = 0

# ============================================================
# 1. GOLEM SPRITES
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Golem Sprites" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$golemTypes = @(
    @{ Id = "golem_basic"; Name = "Basic Golem"; Desc = "Basic golem sprite, simple stone golem, 64x64" },
    @{ Id = "golem_stone"; Name = "Stone Golem"; Desc = "Stone golem sprite, stone golem, 64x64" },
    @{ Id = "golem_iron"; Name = "Iron Golem"; Desc = "Iron golem sprite, iron golem, 64x64" },
    @{ Id = "golem_crystal"; Name = "Crystal Golem"; Desc = "Crystal golem sprite, crystal golem, 64x64" },
    @{ Id = "golem_wood"; Name = "Wood Golem"; Desc = "Wood golem sprite, wooden golem, 64x64" },
    @{ Id = "golem_arcane"; Name = "Arcane Golem"; Desc = "Arcane golem sprite, magical golem, 64x64" }
)

# Validate $ModPath before Join-Path
$golemOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($golemOutputDir)) {
    Write-Host "  [FAIL] golemOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($golemOutputDir)) {
    Write-Host "  [FAIL] golemOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $golemOutputDir)) {
    New-Item -ItemType Directory -Path $golemOutputDir -Force | Out-Null
}

foreach ($golem in $golemTypes) {
    Write-Host "Generating golem: $($golem.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Sprite"
            AssetName = $golem.Id
            Prompt = "$($golem.Desc). Golem sprite for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $golemOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($golem.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($golem.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 2. GOLEM PART SPRITES
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Golem Part Sprites" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$golemParts = @(
    @{ Id = "part_head"; Name = "Head Part"; Desc = "Golem head part sprite, golem head, 32x32" },
    @{ Id = "part_torso"; Name = "Torso Part"; Desc = "Golem torso part sprite, golem torso, 32x32" },
    @{ Id = "part_arm_left"; Name = "Left Arm Part"; Desc = "Golem left arm part sprite, golem left arm, 32x32" },
    @{ Id = "part_arm_right"; Name = "Right Arm Part"; Desc = "Golem right arm part sprite, golem right arm, 32x32" },
    @{ Id = "part_leg_left"; Name = "Left Leg Part"; Desc = "Golem left leg part sprite, golem left leg, 32x32" },
    @{ Id = "part_leg_right"; Name = "Right Leg Part"; Desc = "Golem right leg part sprite, golem right leg, 32x32" },
    @{ Id = "part_hand"; Name = "Hand Part"; Desc = "Golem hand part sprite, golem hand, 16x16" },
    @{ Id = "part_foot"; Name = "Foot Part"; Desc = "Golem foot part sprite, golem foot, 16x16" }
)

# Validate $ModPath before Join-Path
$partOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($partOutputDir)) {
    Write-Host "  [FAIL] partOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($partOutputDir)) {
    Write-Host "  [FAIL] partOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $partOutputDir)) {
    New-Item -ItemType Directory -Path $partOutputDir -Force | Out-Null
}

foreach ($part in $golemParts) {
    Write-Host "Generating golem part: $($part.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Sprite"
            AssetName = $part.Id
            Prompt = "$($part.Desc). Golem part sprite for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $partOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($part.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($part.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 3. GOLEM BLUEPRINT ICONS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Golem Blueprint Icons" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$blueprintIcons = @(
    @{ Id = "blueprint_basic"; Name = "Basic Blueprint"; Desc = "Basic golem blueprint icon, simple blueprint, 32x32" },
    @{ Id = "blueprint_advanced"; Name = "Advanced Blueprint"; Desc = "Advanced golem blueprint icon, complex blueprint, 32x32" },
    @{ Id = "blueprint_custom"; Name = "Custom Blueprint"; Desc = "Custom golem blueprint icon, custom blueprint, 32x32" },
    @{ Id = "blueprint_template"; Name = "Blueprint Template"; Desc = "Blueprint template icon, blueprint template, 32x32" }
)

# Validate $ModPath before Join-Path
$blueprintOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($blueprintOutputDir)) {
    Write-Host "  [FAIL] blueprintOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($blueprintOutputDir)) {
    Write-Host "  [FAIL] blueprintOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $blueprintOutputDir)) {
    New-Item -ItemType Directory -Path $blueprintOutputDir -Force | Out-Null
}

foreach ($icon in $blueprintIcons) {
    Write-Host "Generating blueprint icon: $($icon.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $icon.Id
            Prompt = "$($icon.Desc). Golem blueprint icon for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $blueprintOutputDir
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
# 4. GOLEM STANCE ANIMATIONS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Golem Stance Animations" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$stances = @(
    @{ Id = "stance_idle"; Name = "Idle Stance"; Desc = "Golem idle stance animation, idle pose, 8 frames, 64x64" },
    @{ Id = "stance_guard"; Name = "Guard Stance"; Desc = "Golem guard stance animation, guard pose, 8 frames, 64x64" },
    @{ Id = "stance_patrol"; Name = "Patrol Stance"; Desc = "Golem patrol stance animation, patrol walk, 8 frames, 64x64" },
    @{ Id = "stance_follow"; Name = "Follow Stance"; Desc = "Golem follow stance animation, follow walk, 8 frames, 64x64" },
    @{ Id = "stance_combat"; Name = "Combat Stance"; Desc = "Golem combat stance animation, combat pose, 8 frames, 64x64" },
    @{ Id = "stance_attack"; Name = "Attack Stance"; Desc = "Golem attack stance animation, attack motion, 8 frames, 64x64" }
)

# Validate $ModPath before Join-Path
$stanceOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($stanceOutputDir)) {
    Write-Host "  [FAIL] stanceOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($stanceOutputDir)) {
    Write-Host "  [FAIL] stanceOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $stanceOutputDir)) {
    New-Item -ItemType Directory -Path $stanceOutputDir -Force | Out-Null
}

foreach ($stance in $stances) {
    Write-Host "Generating stance animation: $($stance.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "AnimationSprite"
            AssetName = $stance.Id
            Prompt = "$($stance.Desc). Golem stance animation for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $stanceOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($stance.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($stance.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 5. GOLEM SUMMON EFFECTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Golem Summon Effects" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$summonEffects = @(
    @{ Id = "summon_effect"; Name = "Summon Effect"; Desc = "Golem summon particle effect, golem summoning, 64x64" },
    @{ Id = "summon_formation"; Name = "Formation Effect"; Desc = "Golem formation particle effect, golem forming, 64x64" },
    @{ Id = "summon_complete"; Name = "Complete Effect"; Desc = "Golem summon complete particle effect, summon complete, 64x64" },
    @{ Id = "summon_fail"; Name = "Fail Effect"; Desc = "Golem summon fail particle effect, summon failed, 64x64" }
)

# Validate $ModPath before Join-Path
$summonOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($summonOutputDir)) {
    Write-Host "  [FAIL] summonOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($summonOutputDir)) {
    Write-Host "  [FAIL] summonOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $summonOutputDir)) {
    New-Item -ItemType Directory -Path $summonOutputDir -Force | Out-Null
}

foreach ($effect in $summonEffects) {
    Write-Host "Generating summon effect: $($effect.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Particle"
            AssetName = $effect.Id
            Prompt = "$($effect.Desc). Golem summon effect for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $summonOutputDir
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
# 6. GOLEM COMMAND INDICATORS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Golem Command Indicators" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$commandIndicators = @(
    @{ Id = "command_guard"; Name = "Guard Command"; Desc = "Guard command indicator, guard command, 32x32" },
    @{ Id = "command_patrol"; Name = "Patrol Command"; Desc = "Patrol command indicator, patrol command, 32x32" },
    @{ Id = "command_follow"; Name = "Follow Command"; Desc = "Follow command indicator, follow command, 32x32" },
    @{ Id = "command_attack"; Name = "Attack Command"; Desc = "Attack command indicator, attack command, 32x32" },
    @{ Id = "command_stop"; Name = "Stop Command"; Desc = "Stop command indicator, stop command, 32x32" },
    @{ Id = "command_idle"; Name = "Idle Command"; Desc = "Idle command indicator, idle command, 32x32" }
)

# Validate $ModPath before Join-Path
$commandOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($commandOutputDir)) {
    Write-Host "  [FAIL] commandOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($commandOutputDir)) {
    Write-Host "  [FAIL] commandOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $commandOutputDir)) {
    New-Item -ItemType Directory -Path $commandOutputDir -Force | Out-Null
}

foreach ($indicator in $commandIndicators) {
    Write-Host "Generating command indicator: $($indicator.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $indicator.Id
            Prompt = "$($indicator.Desc). Golem command indicator for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $commandOutputDir
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
# 7. GOLEM CIRCUIT ICONS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Golem Circuit Icons" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$circuitIcons = @(
    @{ Id = "circuit_basic"; Name = "Basic Circuit"; Desc = "Basic golem circuit icon, simple circuit, 32x32" },
    @{ Id = "circuit_enhanced"; Name = "Enhanced Circuit"; Desc = "Enhanced golem circuit icon, enhanced circuit, 32x32" },
    @{ Id = "circuit_magic"; Name = "Magic Circuit"; Desc = "Magic golem circuit icon, magical circuit, 32x32" },
    @{ Id = "circuit_combat"; Name = "Combat Circuit"; Desc = "Combat golem circuit icon, combat circuit, 32x32" },
    @{ Id = "circuit_utility"; Name = "Utility Circuit"; Desc = "Utility golem circuit icon, utility circuit, 32x32" }
)

# Validate $ModPath before Join-Path
$circuitOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($circuitOutputDir)) {
    Write-Host "  [FAIL] circuitOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($circuitOutputDir)) {
    Write-Host "  [FAIL] circuitOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $circuitOutputDir)) {
    New-Item -ItemType Directory -Path $circuitOutputDir -Force | Out-Null
}

foreach ($icon in $circuitIcons) {
    Write-Host "Generating circuit icon: $($icon.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $icon.Id
            Prompt = "$($icon.Desc). Golem circuit icon for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $circuitOutputDir
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
# 8. GOLEM MATERIAL ICONS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Golem Material Icons" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$materialIcons = @(
    @{ Id = "material_stone"; Name = "Stone Material"; Desc = "Stone material icon, stone material, 32x32" },
    @{ Id = "material_iron"; Name = "Iron Material"; Desc = "Iron material icon, iron material, 32x32" },
    @{ Id = "material_crystal"; Name = "Crystal Material"; Desc = "Crystal material icon, crystal material, 32x32" },
    @{ Id = "material_wood"; Name = "Wood Material"; Desc = "Wood material icon, wood material, 32x32" },
    @{ Id = "material_arcane"; Name = "Arcane Material"; Desc = "Arcane material icon, arcane material, 32x32" },
    @{ Id = "material_metal"; Name = "Metal Material"; Desc = "Metal material icon, metal material, 32x32" }
)

# Validate $ModPath before Join-Path
$materialOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($materialOutputDir)) {
    Write-Host "  [FAIL] materialOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($materialOutputDir)) {
    Write-Host "  [FAIL] materialOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $materialOutputDir)) {
    New-Item -ItemType Directory -Path $materialOutputDir -Force | Out-Null
}

foreach ($icon in $materialIcons) {
    Write-Host "Generating material icon: $($icon.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $icon.Id
            Prompt = "$($icon.Desc). Golem material icon for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $materialOutputDir
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
# 9. GOLEM SLOT INDICATORS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Golem Slot Indicators" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$slotIndicators = @(
    @{ Id = "slot_empty"; Name = "Empty Slot"; Desc = "Empty golem slot indicator, empty slot, 32x32" },
    @{ Id = "slot_occupied"; Name = "Occupied Slot"; Desc = "Occupied golem slot indicator, occupied slot, 32x32" },
    @{ Id = "slot_attachment"; Name = "Attachment Slot"; Desc = "Attachment slot indicator, attachment point, 32x32" },
    @{ Id = "slot_resonance"; Name = "Resonance Slot"; Desc = "Resonance slot indicator, resonance point, 32x32" }
)

# Validate $ModPath before Join-Path
$slotOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($slotOutputDir)) {
    Write-Host "  [FAIL] slotOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($slotOutputDir)) {
    Write-Host "  [FAIL] slotOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $slotOutputDir)) {
    New-Item -ItemType Directory -Path $slotOutputDir -Force | Out-Null
}

foreach ($indicator in $slotIndicators) {
    Write-Host "Generating slot indicator: $($indicator.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $indicator.Id
            Prompt = "$($indicator.Desc). Golem slot indicator for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $slotOutputDir
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
Write-Host "  Golem Sprites: $(Join-Path $ModPath 'assets\golems\sprites')" -ForegroundColor Gray
Write-Host "  Golem Parts: $(Join-Path $ModPath 'assets\golems\parts')" -ForegroundColor Gray
Write-Host "  Golem Blueprints: $(Join-Path $ModPath 'assets\golems\blueprints')" -ForegroundColor Gray
Write-Host "  Golem Stances: $(Join-Path $ModPath 'assets\golems\stances')" -ForegroundColor Gray
Write-Host "  Golem Summon: $(Join-Path $ModPath 'assets\golems\summon')" -ForegroundColor Gray
Write-Host "  Golem Commands: $(Join-Path $ModPath 'assets\golems\commands')" -ForegroundColor Gray
Write-Host "  Golem Circuits: $(Join-Path $ModPath 'assets\golems\circuits')" -ForegroundColor Gray
Write-Host "  Golem Materials: $(Join-Path $ModPath 'assets\golems\materials')" -ForegroundColor Gray
Write-Host "  Golem Slots: $(Join-Path $ModPath 'assets\golems\slots')" -ForegroundColor Gray
Write-Host ""
