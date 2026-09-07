#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate assets for the Runic Weapon System.
    
.DESCRIPTION
    Generates sprites, icons, and effects for:
    - Rune icons (all rune types)
    - Wand sprites (all wand types)
    - Staff sprites (all staff types)
    - Rune glow effects
    - Rune activation effects
    - Combination casting effects
    
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
Write-Host "  Runic Weapon System Asset Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$generated = 0
$failed = 0

# ============================================================
# 1. RUNE ICONS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Rune Icons" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$runeIcons = @(
    # Elemental Runes
    @{ Id = "rune_fire"; Name = "Fire Rune"; Desc = "Fire rune icon, Ignis symbol, red/orange, 32x32" },
    @{ Id = "rune_water"; Name = "Water Rune"; Desc = "Water rune icon, Aqua symbol, blue/cyan, 32x32" },
    @{ Id = "rune_earth"; Name = "Earth Rune"; Desc = "Earth rune icon, Terra symbol, brown/green, 32x32" },
    @{ Id = "rune_air"; Name = "Air Rune"; Desc = "Air rune icon, Ventus symbol, white/light blue, 32x32" },
    
    # Power Runes
    @{ Id = "rune_force"; Name = "Force Rune"; Desc = "Force rune icon, Vis symbol, purple, 32x32" },
    @{ Id = "rune_shield"; Name = "Shield Rune"; Desc = "Shield rune icon, Aegis symbol, golden, 32x32" },
    @{ Id = "rune_heal"; Name = "Heal Rune"; Desc = "Heal rune icon, Vitae symbol, green, 32x32" },
    @{ Id = "rune_drain"; Name = "Drain Rune"; Desc = "Drain rune icon, Vampyr symbol, dark red, 32x32" },
    
    # Utility Runes
    @{ Id = "rune_teleport"; Name = "Teleport Rune"; Desc = "Teleport rune icon, Porta symbol, purple/blue, 32x32" },
    @{ Id = "rune_time"; Name = "Time Rune"; Desc = "Time rune icon, Chronos symbol, gold/blue, 32x32" },
    @{ Id = "rune_illusion"; Name = "Illusion Rune"; Desc = "Illusion rune icon, Mirage symbol, purple/pink, 32x32" },
    @{ Id = "rune_summon"; Name = "Summon Rune"; Desc = "Summon rune icon, Evocatio symbol, dark purple, 32x32" },
    
    # Modifier Runes
    @{ Id = "rune_amplify"; Name = "Amplify Rune"; Desc = "Amplify rune icon, Magnus symbol, yellow, 32x32" },
    @{ Id = "rune_split"; Name = "Split Rune"; Desc = "Split rune icon, Divisio symbol, cyan, 32x32" },
    @{ Id = "rune_chain"; Name = "Chain Rune"; Desc = "Chain rune icon, Catena symbol, silver, 32x32" },
    @{ Id = "rune_pierce"; Name = "Pierce Rune"; Desc = "Pierce rune icon, Penetratio symbol, dark blue, 32x32" },
    
    # Forbidden Runes
    @{ Id = "rune_chaos"; Name = "Chaos Rune"; Desc = "Chaos rune icon, Entropy symbol, chaotic colors, 32x32" },
    @{ Id = "rune_void"; Name = "Void Rune"; Desc = "Void rune icon, Nihil symbol, black/purple, 32x32" },
    @{ Id = "rune_soul"; Name = "Soul Rune"; Desc = "Soul rune icon, Anima symbol, dark purple, 32x32" },
    @{ Id = "rune_corrupt"; Name = "Corrupt Rune"; Desc = "Corrupt rune icon, Corruptio symbol, dark red/black, 32x32" }
)

# Validate $ModPath before Join-Path
$runeOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($runeOutputDir)) {
    Write-Host "  [FAIL] runeOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($runeOutputDir)) {
    Write-Host "  [FAIL] runeOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $runeOutputDir)) {
    New-Item -ItemType Directory -Path $runeOutputDir -Force | Out-Null
}

foreach ($rune in $runeIcons) {
    Write-Host "Generating rune icon: $($rune.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $rune.Id
            Prompt = "$($rune.Desc). Rune icon for Starbound runic weapon system."
            OllamaModel = $OllamaModel
            OutputDir = $runeOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($rune.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($rune.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 2. WAND SPRITES
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Wand Sprites" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$wandSprites = @(
    @{ Id = "wand_apprentice"; Name = "Apprentice Wand"; Desc = "Apprentice wand sprite, basic wand, 1-2 rune slots, 64x64" },
    @{ Id = "wand_journeyman"; Name = "Journeyman Wand"; Desc = "Journeyman wand sprite, intermediate wand, 3-4 rune slots, 64x64" },
    @{ Id = "wand_master"; Name = "Master Wand"; Desc = "Master wand sprite, advanced wand, 5-6 rune slots, 64x64" },
    @{ Id = "wand_archmage"; Name = "Archmage Wand"; Desc = "Archmage wand sprite, elite wand, 7-8 rune slots, 64x64" },
    @{ Id = "wand_legendary"; Name = "Legendary Wand"; Desc = "Legendary wand sprite, unique wand, 9+ rune slots, 64x64" },
    @{ Id = "wand_battle"; Name = "Battle Wand"; Desc = "Battle wand sprite, combat-focused wand, 64x64" },
    @{ Id = "wand_utility"; Name = "Utility Wand"; Desc = "Utility wand sprite, non-combat wand, 64x64" },
    @{ Id = "wand_channeling"; Name = "Channeling Wand"; Desc = "Channeling wand sprite, continuous effects wand, 64x64" },
    @{ Id = "wand_ritual"; Name = "Ritual Wand"; Desc = "Ritual wand sprite, ceremonial wand, 64x64" }
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

foreach ($wand in $wandSprites) {
    Write-Host "Generating wand sprite: $($wand.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "WandSprite"
            AssetName = $wand.Id
            Prompt = "$($wand.Desc). Wand sprite for Starbound runic weapon system."
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
# 3. STAFF SPRITES
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Staff Sprites" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$staffSprites = @(
    @{ Id = "staff_wooden"; Name = "Wooden Staff"; Desc = "Wooden staff sprite, traditional wood staff, 64x64" },
    @{ Id = "staff_crystal"; Name = "Crystal Staff"; Desc = "Crystal staff sprite, crystal-core staff, 64x64" },
    @{ Id = "staff_metal"; Name = "Metal Staff"; Desc = "Metal staff sprite, metallic conductor staff, 64x64" },
    @{ Id = "staff_bone"; Name = "Bone Staff"; Desc = "Bone staff sprite, necromantic staff, 64x64" },
    @{ Id = "staff_living"; Name = "Living Staff"; Desc = "Living staff sprite, living wood staff, 64x64" },
    @{ Id = "staff_hybrid"; Name = "Hybrid Staff"; Desc = "Hybrid staff sprite, multi-material staff, 64x64" },
    @{ Id = "staff_world_tree"; Name = "World Tree Staff"; Desc = "World Tree staff sprite, Yggdrasil wood, legendary, 64x64" },
    @{ Id = "staff_star_metal"; Name = "Star Metal Staff"; Desc = "Star Metal staff sprite, meteorite metal, legendary, 64x64" },
    @{ Id = "staff_dragon_bone"; Name = "Dragon Bone Staff"; Desc = "Dragon Bone staff sprite, dragon remains, legendary, 64x64" },
    @{ Id = "staff_void_crystal"; Name = "Void Crystal Staff"; Desc = "Void Crystal staff sprite, void-touched crystal, legendary, 64x64" }
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

foreach ($staff in $staffSprites) {
    Write-Host "Generating staff sprite: $($staff.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "StaffSprite"
            AssetName = $staff.Id
            Prompt = "$($staff.Desc). Staff sprite for Starbound runic weapon system."
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
# 4. RUNE GLOW EFFECTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Rune Glow Effects" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$runeGlows = @(
    @{ Id = "rune_glow_fire"; Name = "Fire Rune Glow"; Desc = "Fire rune glow particle effect, red/orange glow, pulsing" },
    @{ Id = "rune_glow_water"; Name = "Water Rune Glow"; Desc = "Water rune glow particle effect, blue/cyan glow, flowing" },
    @{ Id = "rune_glow_earth"; Name = "Earth Rune Glow"; Desc = "Earth rune glow particle effect, brown/green glow, steady" },
    @{ Id = "rune_glow_air"; Name = "Air Rune Glow"; Desc = "Air rune glow particle effect, white/light blue glow, swirling" },
    @{ Id = "rune_glow_force"; Name = "Force Rune Glow"; Desc = "Force rune glow particle effect, purple glow, intense" },
    @{ Id = "rune_glow_shield"; Name = "Shield Rune Glow"; Desc = "Shield rune glow particle effect, golden glow, protective" },
    @{ Id = "rune_glow_heal"; Name = "Heal Rune Glow"; Desc = "Heal rune glow particle effect, green glow, healing" },
    @{ Id = "rune_glow_void"; Name = "Void Rune Glow"; Desc = "Void rune glow particle effect, black/purple glow, dark" }
)

foreach ($glow in $runeGlows) {
    Write-Host "Generating rune glow: $($glow.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Particle"
            AssetName = $glow.Id
            Prompt = "$($glow.Desc). Rune glow particle effect for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $runeOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($glow.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($glow.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 5. RUNE ACTIVATION EFFECTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Rune Activation Effects" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$runeActivations = @(
    @{ Id = "rune_activation_fire"; Name = "Fire Rune Activation"; Desc = "Fire rune activation particle effect, fire burst, red/orange" },
    @{ Id = "rune_activation_water"; Name = "Water Rune Activation"; Desc = "Water rune activation particle effect, water burst, blue/cyan" },
    @{ Id = "rune_activation_earth"; Name = "Earth Rune Activation"; Desc = "Earth rune activation particle effect, earth burst, brown/green" },
    @{ Id = "rune_activation_air"; Name = "Air Rune Activation"; Desc = "Air rune activation particle effect, wind burst, white/light blue" },
    @{ Id = "rune_activation_force"; Name = "Force Rune Activation"; Desc = "Force rune activation particle effect, force burst, purple" },
    @{ Id = "rune_activation_shield"; Name = "Shield Rune Activation"; Desc = "Shield rune activation particle effect, shield burst, golden" },
    @{ Id = "rune_activation_teleport"; Name = "Teleport Rune Activation"; Desc = "Teleport rune activation particle effect, teleport burst, purple/blue" },
    @{ Id = "rune_activation_combination"; Name = "Combination Rune Activation"; Desc = "Combination rune activation particle effect, multi-rune burst, mixed colors" }
)

foreach ($activation in $runeActivations) {
    Write-Host "Generating rune activation: $($activation.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Particle"
            AssetName = $activation.Id
            Prompt = "$($activation.Desc). Rune activation particle effect for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $runeOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($activation.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($activation.Name) : $_" -ForegroundColor Red
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
Write-Host "  Runes: $(Join-Path $ModPath 'assets\runes')" -ForegroundColor Gray
Write-Host "  Wands: $(Join-Path $ModPath 'assets\weapons\wands')" -ForegroundColor Gray
Write-Host "  Staves: $(Join-Path $ModPath 'assets\weapons\staves')" -ForegroundColor Gray
Write-Host ""
Write-Host "Rune icons: assets/runes/rune_*.png" -ForegroundColor Gray
Write-Host "Rune glows: assets/runes/rune_glow_*.particle" -ForegroundColor Gray
Write-Host "Rune activations: assets/runes/rune_activation_*.particle" -ForegroundColor Gray
Write-Host "Wand sprites: assets/weapons/wands/wand_*.png" -ForegroundColor Gray
Write-Host "Staff sprites: assets/weapons/staves/staff_*.png" -ForegroundColor Gray
Write-Host ""
