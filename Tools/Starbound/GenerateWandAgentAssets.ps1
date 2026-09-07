#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate assets for the WandAgent System.
    
.DESCRIPTION
    Generates visual assets for:
    - Wand sprites (runic, chronomancer, elementalist, battlemage, etc.)
    - Staff sprites (various staff types)
    - Metagem icons
    - Relic icons
    - Mod core icons
    - Wand casting effects
    - Staff casting effects
    - Slot node indicators
    - Graph connection visuals
    
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
Write-Host "  WandAgent System Asset Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$generated = 0
$failed = 0

# ============================================================
# 1. WAND SPRITES
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Wand Sprites" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$wandTypes = @(
    @{ Id = "wand_runic"; Name = "Runic Wand"; Desc = "Runic wand sprite, basic runic wand, 32x32" },
    @{ Id = "wand_chronomancer"; Name = "Chronomancer Wand"; Desc = "Chronomancer wand sprite, time magic wand, 32x32" },
    @{ Id = "wand_elementalist"; Name = "Elementalist Wand"; Desc = "Elementalist wand sprite, elemental magic wand, 32x32" },
    @{ Id = "wand_battlemage"; Name = "Battlemage Wand"; Desc = "Battlemage wand sprite, combat wand, 32x32" },
    @{ Id = "wand_apprentice"; Name = "Apprentice Wand"; Desc = "Apprentice wand sprite, beginner wand, 32x32" },
    @{ Id = "wand_journeyman"; Name = "Journeyman Wand"; Desc = "Journeyman wand sprite, intermediate wand, 32x32" },
    @{ Id = "wand_master"; Name = "Master Wand"; Desc = "Master wand sprite, advanced wand, 32x32" },
    @{ Id = "wand_archmage"; Name = "Archmage Wand"; Desc = "Archmage wand sprite, expert wand, 32x32" },
    @{ Id = "wand_legendary"; Name = "Legendary Wand"; Desc = "Legendary wand sprite, legendary wand, 32x32" }
)

# Validate $ModPath before Join-Path
$wandOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($wandOutputDir)) {
    Write-Host "  [FAIL] wandOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($wandOutputDir)) {
    Write-Host "  [FAIL] wandOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $wandOutputDir)) {
    New-Item -ItemType Directory -Path $wandOutputDir -Force | Out-Null
}

foreach ($wand in $wandTypes) {
    Write-Host "Generating wand: $($wand.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "WandSprite"
            AssetName = $wand.Id
            Prompt = "$($wand.Desc). Wand sprite for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $wandOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($wand.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($wand.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 2. STAFF SPRITES
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Staff Sprites" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$staffTypes = @(
    @{ Id = "staff_wooden"; Name = "Wooden Staff"; Desc = "Wooden staff sprite, basic wooden staff, 32x64" },
    @{ Id = "staff_crystal"; Name = "Crystal Staff"; Desc = "Crystal staff sprite, crystal staff, 32x64" },
    @{ Id = "staff_metal"; Name = "Metal Staff"; Desc = "Metal staff sprite, metallic staff, 32x64" },
    @{ Id = "staff_bone"; Name = "Bone Staff"; Desc = "Bone staff sprite, bone staff, 32x64" },
    @{ Id = "staff_living"; Name = "Living Staff"; Desc = "Living staff sprite, organic staff, 32x64" },
    @{ Id = "staff_hybrid"; Name = "Hybrid Staff"; Desc = "Hybrid staff sprite, hybrid staff, 32x64" },
    @{ Id = "staff_world_tree"; Name = "World Tree Staff"; Desc = "World tree staff sprite, world tree staff, 32x64" },
    @{ Id = "staff_star_metal"; Name = "Star Metal Staff"; Desc = "Star metal staff sprite, star metal staff, 32x64" },
    @{ Id = "staff_dragon_bone"; Name = "Dragon Bone Staff"; Desc = "Dragon bone staff sprite, dragon bone staff, 32x64" },
    @{ Id = "staff_void_crystal"; Name = "Void Crystal Staff"; Desc = "Void crystal staff sprite, void crystal staff, 32x64" }
)

# Validate $ModPath before Join-Path
$staffOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($staffOutputDir)) {
    Write-Host "  [FAIL] staffOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($staffOutputDir)) {
    Write-Host "  [FAIL] staffOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $staffOutputDir)) {
    New-Item -ItemType Directory -Path $staffOutputDir -Force | Out-Null
}

foreach ($staff in $staffTypes) {
    Write-Host "Generating staff: $($staff.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "StaffSprite"
            AssetName = $staff.Id
            Prompt = "$($staff.Desc). Staff sprite for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $staffOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($staff.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($staff.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 3. METAGEM ICONS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Metagem Icons" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$metagems = @(
    @{ Id = "metagem_reduce_mana"; Name = "Reduce Mana Metagem"; Desc = "Reduce mana cost metagem icon, mana reduction gem, 32x32" },
    @{ Id = "metagem_enhance_elemental"; Name = "Enhance Elemental Metagem"; Desc = "Enhance elemental damage metagem icon, elemental enhancement gem, 32x32" },
    @{ Id = "metagem_enhance_damage"; Name = "Enhance Damage Metagem"; Desc = "Enhance damage metagem icon, damage enhancement gem, 32x32" },
    @{ Id = "metagem_crit_chance"; Name = "Crit Chance Metagem"; Desc = "Crit chance metagem icon, critical chance gem, 32x32" },
    @{ Id = "metagem_cast_speed"; Name = "Cast Speed Metagem"; Desc = "Cast speed metagem icon, cast speed gem, 32x32" },
    @{ Id = "metagem_spell_range"; Name = "Spell Range Metagem"; Desc = "Spell range metagem icon, range enhancement gem, 32x32" }
)

# Validate $ModPath before Join-Path
$metagemOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($metagemOutputDir)) {
    Write-Host "  [FAIL] metagemOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($metagemOutputDir)) {
    Write-Host "  [FAIL] metagemOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $metagemOutputDir)) {
    New-Item -ItemType Directory -Path $metagemOutputDir -Force | Out-Null
}

foreach ($metagem in $metagems) {
    Write-Host "Generating metagem: $($metagem.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $metagem.Id
            Prompt = "$($metagem.Desc). Metagem icon for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $metagemOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($metagem.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($metagem.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 4. RELIC ICONS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Relic Icons" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$relics = @(
    @{ Id = "relic_power"; Name = "Power Relic"; Desc = "Power relic icon, power enhancement relic, 32x32" },
    @{ Id = "relic_speed"; Name = "Speed Relic"; Desc = "Speed relic icon, speed enhancement relic, 32x32" },
    @{ Id = "relic_protection"; Name = "Protection Relic"; Desc = "Protection relic icon, protection relic, 32x32" },
    @{ Id = "relic_wisdom"; Name = "Wisdom Relic"; Desc = "Wisdom relic icon, wisdom relic, 32x32" },
    @{ Id = "relic_chaos"; Name = "Chaos Relic"; Desc = "Chaos relic icon, chaos relic, 32x32" },
    @{ Id = "relic_order"; Name = "Order Relic"; Desc = "Order relic icon, order relic, 32x32" }
)

# Validate $ModPath before Join-Path
$relicOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($relicOutputDir)) {
    Write-Host "  [FAIL] relicOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($relicOutputDir)) {
    Write-Host "  [FAIL] relicOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $relicOutputDir)) {
    New-Item -ItemType Directory -Path $relicOutputDir -Force | Out-Null
}

foreach ($relic in $relics) {
    Write-Host "Generating relic: $($relic.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $relic.Id
            Prompt = "$($relic.Desc). Relic icon for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $relicOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($relic.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($relic.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 5. MOD CORE ICONS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Mod Core Icons" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$modCores = @(
    @{ Id = "modcore_basic"; Name = "Basic Mod Core"; Desc = "Basic mod core icon, basic modification core, 32x32" },
    @{ Id = "modcore_advanced"; Name = "Advanced Mod Core"; Desc = "Advanced mod core icon, advanced modification core, 32x32" },
    @{ Id = "modcore_elemental"; Name = "Elemental Mod Core"; Desc = "Elemental mod core icon, elemental modification core, 32x32" },
    @{ Id = "modcore_combat"; Name = "Combat Mod Core"; Desc = "Combat mod core icon, combat modification core, 32x32" },
    @{ Id = "modcore_utility"; Name = "Utility Mod Core"; Desc = "Utility mod core icon, utility modification core, 32x32" }
)

# Validate $ModPath before Join-Path
$modCoreOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($modCoreOutputDir)) {
    Write-Host "  [FAIL] modCoreOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($modCoreOutputDir)) {
    Write-Host "  [FAIL] modCoreOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $modCoreOutputDir)) {
    New-Item -ItemType Directory -Path $modCoreOutputDir -Force | Out-Null
}

foreach ($modCore in $modCores) {
    Write-Host "Generating mod core: $($modCore.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $modCore.Id
            Prompt = "$($modCore.Desc). Mod core icon for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $modCoreOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($modCore.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($modCore.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 6. WAND CASTING EFFECTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Wand Casting Effects" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$wandCastingEffects = @(
    @{ Id = "wand_cast_effect"; Name = "Wand Cast Effect"; Desc = "Wand casting particle effect, wand cast, 64x64" },
    @{ Id = "wand_charge_effect"; Name = "Wand Charge Effect"; Desc = "Wand charging particle effect, wand charge, 64x64" },
    @{ Id = "wand_reload_effect"; Name = "Wand Reload Effect"; Desc = "Wand reloading particle effect, wand reload, 64x64" },
    @{ Id = "wand_shuffle_effect"; Name = "Wand Shuffle Effect"; Desc = "Wand shuffle particle effect, wand shuffle, 64x64" }
)

# Validate $ModPath before Join-Path
$wandEffectOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($wandEffectOutputDir)) {
    Write-Host "  [FAIL] wandEffectOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($wandEffectOutputDir)) {
    Write-Host "  [FAIL] wandEffectOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $wandEffectOutputDir)) {
    New-Item -ItemType Directory -Path $wandEffectOutputDir -Force | Out-Null
}

foreach ($effect in $wandCastingEffects) {
    Write-Host "Generating wand effect: $($effect.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Particle"
            AssetName = $effect.Id
            Prompt = "$($effect.Desc). Wand casting effect for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $wandEffectOutputDir
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
# 7. STAFF CASTING EFFECTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Staff Casting Effects" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$staffCastingEffects = @(
    @{ Id = "staff_cast_effect"; Name = "Staff Cast Effect"; Desc = "Staff casting particle effect, staff cast, 64x64" },
    @{ Id = "staff_charge_effect"; Name = "Staff Charge Effect"; Desc = "Staff charging particle effect, staff charge, 64x64" },
    @{ Id = "staff_aoe_effect"; Name = "Staff AOE Effect"; Desc = "Staff area of effect particle effect, staff AOE, 64x64" },
    @{ Id = "staff_elemental_effect"; Name = "Staff Elemental Effect"; Desc = "Staff elemental particle effect, staff elemental, 64x64" }
)

# Validate $ModPath before Join-Path
$staffEffectOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($staffEffectOutputDir)) {
    Write-Host "  [FAIL] staffEffectOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($staffEffectOutputDir)) {
    Write-Host "  [FAIL] staffEffectOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $staffEffectOutputDir)) {
    New-Item -ItemType Directory -Path $staffEffectOutputDir -Force | Out-Null
}

foreach ($effect in $staffCastingEffects) {
    Write-Host "Generating staff effect: $($effect.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Particle"
            AssetName = $effect.Id
            Prompt = "$($effect.Desc). Staff casting effect for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $staffEffectOutputDir
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
# 8. SLOT NODE INDICATORS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Slot Node Indicators" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$slotIndicators = @(
    @{ Id = "slot_spellstone"; Name = "Spellstone Slot"; Desc = "Spellstone slot indicator, spellstone slot, 32x32" },
    @{ Id = "slot_modcore"; Name = "Mod Core Slot"; Desc = "Mod core slot indicator, mod core slot, 32x32" },
    @{ Id = "slot_metagem"; Name = "Metagem Slot"; Desc = "Metagem slot indicator, metagem slot, 32x32" },
    @{ Id = "slot_relic"; Name = "Relic Slot"; Desc = "Relic slot indicator, relic slot, 32x32" },
    @{ Id = "slot_empty"; Name = "Empty Slot"; Desc = "Empty slot indicator, empty slot, 32x32" },
    @{ Id = "slot_ready"; Name = "Ready Slot"; Desc = "Ready slot indicator, ready slot, 32x32" },
    @{ Id = "slot_cooldown"; Name = "Cooldown Slot"; Desc = "Cooldown slot indicator, cooldown slot, 32x32" },
    @{ Id = "slot_active"; Name = "Active Slot"; Desc = "Active slot indicator, active slot, 32x32" }
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
            Prompt = "$($indicator.Desc). Slot node indicator for Starbound."
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
# 9. GRAPH CONNECTION VISUALS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Graph Connection Visuals" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$graphVisuals = @(
    @{ Id = "graph_connection"; Name = "Graph Connection"; Desc = "Graph connection line, connection line, 32x4" },
    @{ Id = "graph_prerequisite"; Name = "Graph Prerequisite"; Desc = "Graph prerequisite indicator, prerequisite marker, 16x16" },
    @{ Id = "graph_branch_active"; Name = "Active Branch"; Desc = "Active branch indicator, active branch, 32x32" },
    @{ Id = "graph_branch_inactive"; Name = "Inactive Branch"; Desc = "Inactive branch indicator, inactive branch, 32x32" }
)

# Validate $ModPath before Join-Path
$graphOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($graphOutputDir)) {
    Write-Host "  [FAIL] graphOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($graphOutputDir)) {
    Write-Host "  [FAIL] graphOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $graphOutputDir)) {
    New-Item -ItemType Directory -Path $graphOutputDir -Force | Out-Null
}

foreach ($visual in $graphVisuals) {
    Write-Host "Generating graph visual: $($visual.Name)" -ForegroundColor Cyan
    
    try {
        $assetType = if ($visual.Id -like "*connection*") { "Texture" } else { "Icon" }
        
        $params = @{
            AssetType = $assetType
            AssetName = $visual.Id
            Prompt = "$($visual.Desc). Graph connection visual for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $graphOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($visual.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($visual.Name) : $_" -ForegroundColor Red
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
Write-Host "  Wands: $(Join-Path $ModPath 'assets\wands')" -ForegroundColor Gray
Write-Host "  Staves: $(Join-Path $ModPath 'assets\staves')" -ForegroundColor Gray
Write-Host "  Metagems: $(Join-Path $ModPath 'assets\wands\metagems')" -ForegroundColor Gray
Write-Host "  Relics: $(Join-Path $ModPath 'assets\wands\relics')" -ForegroundColor Gray
Write-Host "  Mod Cores: $(Join-Path $ModPath 'assets\wands\modcores')" -ForegroundColor Gray
Write-Host "  Wand Effects: $(Join-Path $ModPath 'assets\wands\effects')" -ForegroundColor Gray
Write-Host "  Staff Effects: $(Join-Path $ModPath 'assets\staves\effects')" -ForegroundColor Gray
Write-Host "  Slot Indicators: $(Join-Path $ModPath 'assets\wands\slots')" -ForegroundColor Gray
Write-Host "  Graph Visuals: $(Join-Path $ModPath 'assets\wands\graph')" -ForegroundColor Gray
Write-Host ""
