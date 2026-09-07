#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate assets for the BuffAgent System.
    
.DESCRIPTION
    Generates visual assets for:
    - Buff icons (various buff types)
    - Debuff icons (various debuff types)
    - Stack indicators
    - Duration indicators
    - Buff UI elements (panels, tooltips, inspector)
    - Aura effects
    - Buff application effects
    - Status effect overlays
    - Buff type indicators
    
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
Write-Host "  BuffAgent System Asset Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$generated = 0
$failed = 0

# ============================================================
# 1. BUFF ICONS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Buff Icons" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$buffIcons = @(
    @{ Id = "buff_strength"; Name = "Strength Buff"; Desc = "Strength buff icon, increased strength, 32x32" },
    @{ Id = "buff_agility"; Name = "Agility Buff"; Desc = "Agility buff icon, increased agility, 32x32" },
    @{ Id = "buff_defense"; Name = "Defense Buff"; Desc = "Defense buff icon, increased defense, 32x32" },
    @{ Id = "buff_speed"; Name = "Speed Buff"; Desc = "Speed buff icon, increased speed, 32x32" },
    @{ Id = "buff_heal"; Name = "Heal Buff"; Desc = "Heal buff icon, regeneration, 32x32" },
    @{ Id = "buff_mana_regen"; Name = "Mana Regeneration"; Desc = "Mana regeneration buff icon, mana regen, 32x32" },
    @{ Id = "buff_shield"; Name = "Shield Buff"; Desc = "Shield buff icon, protective shield, 32x32" },
    @{ Id = "buff_arcane_shield"; Name = "Arcane Shield"; Desc = "Arcane shield buff icon, magical shield, 32x32" },
    @{ Id = "buff_berserker_rage"; Name = "Berserker Rage"; Desc = "Berserker rage buff icon, rage effect, 32x32" },
    @{ Id = "buff_mighty_strength"; Name = "Mighty Strength"; Desc = "Mighty strength buff icon, powerful strength, 32x32" },
    @{ Id = "buff_frost_aura"; Name = "Frost Aura"; Desc = "Frost aura buff icon, frost effect, 32x32" },
    @{ Id = "buff_fire_aura"; Name = "Fire Aura"; Desc = "Fire aura buff icon, fire effect, 32x32" }
)

# Validate $ModPath before Join-Path
$buffOutputDir = Join-Path $ModPath "assets"
if ([string]::IsNullOrWhiteSpace($buffOutputDir)) {
    Write-Host "  [FAIL] buffOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    Write-Host "  Skipping buff icon generation" -ForegroundColor Yellow
} else {
    if (-not (Test-Path $buffOutputDir)) {
        New-Item -ItemType Directory -Path $buffOutputDir -Force | Out-Null
    }

if (-not [string]::IsNullOrWhiteSpace($buffOutputDir)) {
    foreach ($icon in $buffIcons) {
        Write-Host "Generating buff icon: $($icon.Name)" -ForegroundColor Cyan
        
        try {
            $params = @{
                AssetType = "Icon"
                AssetName = $icon.Id
                Prompt = "$($icon.Desc). Buff icon for Starbound."
                OllamaModel = $OllamaModel
                OutputDir = $buffOutputDir
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
}

# ============================================================
# 2. DEBUFF ICONS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Debuff Icons" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$debuffIcons = @(
    @{ Id = "debuff_weakness"; Name = "Weakness Debuff"; Desc = "Weakness debuff icon, reduced strength, 32x32" },
    @{ Id = "debuff_slow"; Name = "Slow Debuff"; Desc = "Slow debuff icon, reduced speed, 32x32" },
    @{ Id = "debuff_poison"; Name = "Poison Debuff"; Desc = "Poison debuff icon, poison effect, 32x32" },
    @{ Id = "debuff_burn"; Name = "Burn Debuff"; Desc = "Burn debuff icon, fire damage over time, 32x32" },
    @{ Id = "debuff_freeze"; Name = "Freeze Debuff"; Desc = "Freeze debuff icon, frozen status, 32x32" },
    @{ Id = "debuff_stun"; Name = "Stun Debuff"; Desc = "Stun debuff icon, stunned status, 32x32" },
    @{ Id = "debuff_silence"; Name = "Silence Debuff"; Desc = "Silence debuff icon, silenced status, 32x32" },
    @{ Id = "debuff_curse"; Name = "Curse Debuff"; Desc = "Curse debuff icon, cursed status, 32x32" },
    @{ Id = "debuff_fear"; Name = "Fear Debuff"; Desc = "Fear debuff icon, fear effect, 32x32" },
    @{ Id = "debuff_bleed"; Name = "Bleed Debuff"; Desc = "Bleed debuff icon, bleeding effect, 32x32" }
)

# Validate $ModPath before Join-Path
$debuffOutputDir = Join-Path $ModPath "assets"
if ([string]::IsNullOrWhiteSpace($debuffOutputDir)) {
    Write-Host "  [FAIL] debuffOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    Write-Host "  Skipping debuff icon generation" -ForegroundColor Yellow
} else {
    if (-not (Test-Path $debuffOutputDir)) {
        New-Item -ItemType Directory -Path $debuffOutputDir -Force | Out-Null
    }
}

if (-not [string]::IsNullOrWhiteSpace($debuffOutputDir)) {
    foreach ($icon in $debuffIcons) {
        Write-Host "Generating debuff icon: $($icon.Name)" -ForegroundColor Cyan
        
        try {
            $params = @{
                AssetType = "Icon"
                AssetName = $icon.Id
                Prompt = "$($icon.Desc). Debuff icon for Starbound."
                OllamaModel = $OllamaModel
                OutputDir = $debuffOutputDir
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
}

# ============================================================
# 3. STACK INDICATORS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Stack Indicators" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$stackIndicators = @(
    @{ Id = "stack_indicator"; Name = "Stack Indicator"; Desc = "Stack indicator icon, buff stack count, 16x16" },
    @{ Id = "stack_1"; Name = "Stack 1"; Desc = "Stack 1 indicator, single stack, 16x16" },
    @{ Id = "stack_2"; Name = "Stack 2"; Desc = "Stack 2 indicator, two stacks, 16x16" },
    @{ Id = "stack_3"; Name = "Stack 3"; Desc = "Stack 3 indicator, three stacks, 16x16" },
    @{ Id = "stack_max"; Name = "Max Stacks"; Desc = "Max stacks indicator, maximum stacks, 16x16" },
    @{ Id = "stack_overflow"; Name = "Stack Overflow"; Desc = "Stack overflow indicator, over max stacks, 16x16" }
)

# Validate $ModPath before Join-Path
$stackOutputDir = Join-Path $ModPath "assets"
if ([string]::IsNullOrWhiteSpace($stackOutputDir)) {
    Write-Host "  [FAIL] stackOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    Write-Host "  Skipping stack indicator generation" -ForegroundColor Yellow
} else {
    if (-not (Test-Path $stackOutputDir)) {
        New-Item -ItemType Directory -Path $stackOutputDir -Force | Out-Null
    }
}

if (-not [string]::IsNullOrWhiteSpace($stackOutputDir)) {
    foreach ($indicator in $stackIndicators) {
        Write-Host "Generating stack indicator: $($indicator.Name)" -ForegroundColor Cyan
        
        try {
            $params = @{
                AssetType = "Icon"
                AssetName = $indicator.Id
                Prompt = "$($indicator.Desc). Stack indicator for Starbound."
                OllamaModel = $OllamaModel
                OutputDir = $stackOutputDir
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
}

# ============================================================
# 4. DURATION INDICATORS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Duration Indicators" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$durationIndicators = @(
    @{ Id = "duration_full"; Name = "Full Duration"; Desc = "Full duration indicator, full time remaining, 16x16" },
    @{ Id = "duration_high"; Name = "High Duration"; Desc = "High duration indicator, high time remaining, 16x16" },
    @{ Id = "duration_medium"; Name = "Medium Duration"; Desc = "Medium duration indicator, medium time remaining, 16x16" },
    @{ Id = "duration_low"; Name = "Low Duration"; Desc = "Low duration indicator, low time remaining, 16x16" },
    @{ Id = "duration_expiring"; Name = "Expiring"; Desc = "Expiring indicator, about to expire, 16x16" },
    @{ Id = "duration_infinite"; Name = "Infinite Duration"; Desc = "Infinite duration indicator, permanent buff, 16x16" }
)

# Validate $ModPath before Join-Path
$durationOutputDir = Join-Path $ModPath "assets"
if ([string]::IsNullOrWhiteSpace($durationOutputDir)) {
    Write-Host "  [FAIL] durationOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    Write-Host "  Skipping duration indicator generation" -ForegroundColor Yellow
} else {
    if (-not (Test-Path $durationOutputDir)) {
        New-Item -ItemType Directory -Path $durationOutputDir -Force | Out-Null
    }
}

if (-not [string]::IsNullOrWhiteSpace($durationOutputDir)) {
    foreach ($indicator in $durationIndicators) {
        Write-Host "Generating duration indicator: $($indicator.Name)" -ForegroundColor Cyan
        
        try {
            $params = @{
                AssetType = "Icon"
                AssetName = $indicator.Id
                Prompt = "$($indicator.Desc). Duration indicator for Starbound."
                OllamaModel = $OllamaModel
                OutputDir = $durationOutputDir
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
}
}

# ============================================================
# 5. BUFF UI ELEMENTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Buff UI Elements" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$uiElements = @(
    @{ Id = "ui_panel_buffs"; Name = "Buffs Panel"; Desc = "Buffs panel background, buff display panel, 128x256" },
    @{ Id = "ui_panel_debuffs"; Name = "Debuffs Panel"; Desc = "Debuffs panel background, debuff display panel, 128x256" },
    @{ Id = "ui_tooltip_buff"; Name = "Buff Tooltip"; Desc = "Buff tooltip background, buff information tooltip, 128x128" },
    @{ Id = "ui_tooltip_debuff"; Name = "Debuff Tooltip"; Desc = "Debuff tooltip background, debuff information tooltip, 128x128" },
    @{ Id = "ui_inspector_panel"; Name = "Inspector Panel"; Desc = "Buff inspector panel background, debug inspector, 256x256" },
    @{ Id = "ui_slot_buff"; Name = "Buff Slot"; Desc = "Buff slot background, buff icon slot, 32x32" },
    @{ Id = "ui_slot_debuff"; Name = "Debuff Slot"; Desc = "Debuff slot background, debuff icon slot, 32x32" },
    @{ Id = "ui_button_remove_buff"; Name = "Remove Buff Button"; Desc = "Remove buff button icon, remove buff, 16x16" }
)

# Validate $ModPath before Join-Path
$uiOutputDir = Join-Path $ModPath "assets"
if ([string]::IsNullOrWhiteSpace($uiOutputDir)) {
    Write-Host "  [FAIL] uiOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    Write-Host "  Skipping UI element generation" -ForegroundColor Yellow
} else {
    if (-not (Test-Path $uiOutputDir)) {
        New-Item -ItemType Directory -Path $uiOutputDir -Force | Out-Null
    }
}

if (-not [string]::IsNullOrWhiteSpace($uiOutputDir)) {
    foreach ($element in $uiElements) {
        Write-Host "Generating UI element: $($element.Name)" -ForegroundColor Cyan
        
        try {
            $assetType = if ($element.Id -like "*panel*" -or $element.Id -like "*tooltip*" -or $element.Id -like "*slot*") { "Texture" } else { "Icon" }
            
            $params = @{
                AssetType = $assetType
                AssetName = $element.Id
                Prompt = "$($element.Desc). Buff UI element for Starbound."
                OllamaModel = $OllamaModel
                OutputDir = $uiOutputDir
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
}

# ============================================================
# 6. AURA EFFECTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Aura Effects" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$auraEffects = @(
    @{ Id = "aura_frost"; Name = "Frost Aura"; Desc = "Frost aura particle effect, frost aura visual, 64x64" },
    @{ Id = "aura_fire"; Name = "Fire Aura"; Desc = "Fire aura particle effect, fire aura visual, 64x64" },
    @{ Id = "aura_arcane"; Name = "Arcane Aura"; Desc = "Arcane aura particle effect, arcane aura visual, 64x64" },
    @{ Id = "aura_heal"; Name = "Heal Aura"; Desc = "Heal aura particle effect, healing aura visual, 64x64" },
    @{ Id = "aura_shield"; Name = "Shield Aura"; Desc = "Shield aura particle effect, protective aura visual, 64x64" },
    @{ Id = "aura_radius_indicator"; Name = "Aura Radius"; Desc = "Aura radius indicator, aura range visual, 128x128" }
)

# Validate $ModPath before Join-Path
$auraOutputDir = Join-Path $ModPath "assets"
if ([string]::IsNullOrWhiteSpace($auraOutputDir)) {
    Write-Host "  [FAIL] auraOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    Write-Host "  Skipping aura effect generation" -ForegroundColor Yellow
} else {
    if (-not (Test-Path $auraOutputDir)) {
        New-Item -ItemType Directory -Path $auraOutputDir -Force | Out-Null
    }
}

if (-not [string]::IsNullOrWhiteSpace($auraOutputDir)) {
    foreach ($effect in $auraEffects) {
        Write-Host "Generating aura effect: $($effect.Name)" -ForegroundColor Cyan
        
        try {
            $assetType = if ($effect.Id -like "*radius*") { "Texture" } else { "Particle" }
            
            $params = @{
                AssetType = $assetType
                AssetName = $effect.Id
                Prompt = "$($effect.Desc). Aura effect for Starbound."
                OllamaModel = $OllamaModel
                OutputDir = $auraOutputDir
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
# 7. BUFF APPLICATION EFFECTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Buff Application Effects" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$applicationEffects = @(
    @{ Id = "effect_apply_buff"; Name = "Apply Buff Effect"; Desc = "Buff application particle effect, buff applied visual, 64x64" },
    @{ Id = "effect_remove_buff"; Name = "Remove Buff Effect"; Desc = "Buff removal particle effect, buff removed visual, 64x64" },
    @{ Id = "effect_refresh_buff"; Name = "Refresh Buff Effect"; Desc = "Buff refresh particle effect, buff refreshed visual, 64x64" },
    @{ Id = "effect_stack_buff"; Name = "Stack Buff Effect"; Desc = "Buff stack particle effect, buff stacked visual, 64x64" },
    @{ Id = "effect_expire_buff"; Name = "Expire Buff Effect"; Desc = "Buff expiration particle effect, buff expired visual, 64x64" }
)

# Validate $ModPath before Join-Path
$applicationOutputDir = Join-Path $ModPath "assets"
if ([string]::IsNullOrWhiteSpace($applicationOutputDir)) {
    Write-Host "  [FAIL] applicationOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    Write-Host "  Skipping application effect generation" -ForegroundColor Yellow
} else {
    if (-not (Test-Path $applicationOutputDir)) {
        New-Item -ItemType Directory -Path $applicationOutputDir -Force | Out-Null
    }
}

if (-not [string]::IsNullOrWhiteSpace($applicationOutputDir)) {
    foreach ($effect in $applicationEffects) {
        Write-Host "Generating application effect: $($effect.Name)" -ForegroundColor Cyan
        
        try {
            $params = @{
                AssetType = "Particle"
                AssetName = $effect.Id
                Prompt = "$($effect.Desc). Buff application effect for Starbound."
                OllamaModel = $OllamaModel
                OutputDir = $applicationOutputDir
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
# 8. STATUS EFFECT OVERLAYS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Status Effect Overlays" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$overlays = @(
    @{ Id = "overlay_buff_glow"; Name = "Buff Glow Overlay"; Desc = "Buff glow overlay texture, positive effect glow, 64x64" },
    @{ Id = "overlay_debuff_glow"; Name = "Debuff Glow Overlay"; Desc = "Debuff glow overlay texture, negative effect glow, 64x64" },
    @{ Id = "overlay_shield"; Name = "Shield Overlay"; Desc = "Shield overlay texture, protective shield visual, 64x64" },
    @{ Id = "overlay_poison"; Name = "Poison Overlay"; Desc = "Poison overlay texture, poison effect visual, 64x64" },
    @{ Id = "overlay_freeze"; Name = "Freeze Overlay"; Desc = "Freeze overlay texture, frozen effect visual, 64x64" },
    @{ Id = "overlay_burn"; Name = "Burn Overlay"; Desc = "Burn overlay texture, burning effect visual, 64x64" }
)

# Validate $ModPath before Join-Path
$overlayOutputDir = Join-Path $ModPath "assets"
if ([string]::IsNullOrWhiteSpace($overlayOutputDir)) {
    Write-Host "  [FAIL] overlayOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    Write-Host "  Skipping overlay generation" -ForegroundColor Yellow
} else {
    if (-not (Test-Path $overlayOutputDir)) {
        New-Item -ItemType Directory -Path $overlayOutputDir -Force | Out-Null
    }
}

if (-not [string]::IsNullOrWhiteSpace($overlayOutputDir)) {
    foreach ($overlay in $overlays) {
        Write-Host "Generating overlay: $($overlay.Name)" -ForegroundColor Cyan
        
        try {
            $params = @{
                AssetType = "Texture"
                AssetName = $overlay.Id
                Prompt = "$($overlay.Desc). Status effect overlay for Starbound."
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
}

# ============================================================
# 9. BUFF TYPE INDICATORS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Buff Type Indicators" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$typeIndicators = @(
    @{ Id = "type_buff"; Name = "Buff Type"; Desc = "Buff type indicator icon, positive effect, 16x16" },
    @{ Id = "type_debuff"; Name = "Debuff Type"; Desc = "Debuff type indicator icon, negative effect, 16x16" },
    @{ Id = "type_aura"; Name = "Aura Type"; Desc = "Aura type indicator icon, aura effect, 16x16" },
    @{ Id = "type_tick"; Name = "Tick Type"; Desc = "Tick type indicator icon, periodic effect, 16x16" },
    @{ Id = "type_permanent"; Name = "Permanent Type"; Desc = "Permanent type indicator icon, permanent effect, 16x16" }
)

# Validate $ModPath before Join-Path
$typeOutputDir = Join-Path $ModPath "assets"
if ([string]::IsNullOrWhiteSpace($typeOutputDir)) {
    Write-Host "  [FAIL] typeOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    Write-Host "  Skipping type indicator generation" -ForegroundColor Yellow
} else {
    if (-not (Test-Path $typeOutputDir)) {
        New-Item -ItemType Directory -Path $typeOutputDir -Force | Out-Null
    }
}

if (-not [string]::IsNullOrWhiteSpace($typeOutputDir)) {
    foreach ($indicator in $typeIndicators) {
        Write-Host "Generating type indicator: $($indicator.Name)" -ForegroundColor Cyan
        
        try {
            $params = @{
                AssetType = "Icon"
                AssetName = $indicator.Id
                Prompt = "$($indicator.Desc). Buff type indicator for Starbound."
                OllamaModel = $OllamaModel
                OutputDir = $typeOutputDir
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
Write-Host "  Buff Icons: $(Join-Path $ModPath 'assets\buffs\icons')" -ForegroundColor Gray
Write-Host "  Debuff Icons: $(Join-Path $ModPath 'assets\buffs\debuffs')" -ForegroundColor Gray
Write-Host "  Stack Indicators: $(Join-Path $ModPath 'assets\buffs\stacks')" -ForegroundColor Gray
Write-Host "  Duration Indicators: $(Join-Path $ModPath 'assets\buffs\duration')" -ForegroundColor Gray
Write-Host "  UI Elements: $(Join-Path $ModPath 'assets\buffs\ui')" -ForegroundColor Gray
Write-Host "  Aura Effects: $(Join-Path $ModPath 'assets\buffs\auras')" -ForegroundColor Gray
Write-Host "  Application Effects: $(Join-Path $ModPath 'assets\buffs\effects')" -ForegroundColor Gray
Write-Host "  Status Overlays: $(Join-Path $ModPath 'assets\buffs\overlays')" -ForegroundColor Gray
Write-Host "  Type Indicators: $(Join-Path $ModPath 'assets\buffs\types')" -ForegroundColor Gray
Write-Host ""
