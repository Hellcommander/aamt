#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate assets for the Race Generation System.
    
.DESCRIPTION
    Generates sprites, icons, and portraits for:
    - Race portraits/icons
    - Character model sprites (if needed)
    - Equipment icons (weapons, armor, gadgets)
    
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
Write-Host "  Race Generation System Asset Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$generated = 0
$failed = 0

# ============================================================
# 1. RACE PORTRAITS/ICONS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Race Portraits/Icons" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$racePortraits = @(
    @{ Id = "race_portrait_human"; Name = "Human Race Portrait"; Desc = "Human race portrait icon, human character, 64x64" },
    @{ Id = "race_portrait_apex"; Name = "Apex Race Portrait"; Desc = "Apex race portrait icon, ape-like character, 64x64" },
    @{ Id = "race_portrait_avian"; Name = "Avian Race Portrait"; Desc = "Avian race portrait icon, bird-like character, 64x64" },
    @{ Id = "race_portrait_floran"; Name = "Floran Race Portrait"; Desc = "Floran race portrait icon, plant-like character, 64x64" },
    @{ Id = "race_portrait_glitch"; Name = "Glitch Race Portrait"; Desc = "Glitch race portrait icon, robotic character, 64x64" },
    @{ Id = "race_portrait_hylotl"; Name = "Hylotl Race Portrait"; Desc = "Hylotl race portrait icon, aquatic character, 64x64" },
    @{ Id = "race_portrait_novakid"; Name = "Novakid Race Portrait"; Desc = "Novakid race portrait icon, star-like character, 64x64" }
)

# Validate $ModPath before Join-Path
$racePortraitOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($racePortraitOutputDir)) {
    Write-Host "  [FAIL] racePortraitOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($racePortraitOutputDir)) {
    Write-Host "  [FAIL] racePortraitOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $racePortraitOutputDir)) {
    New-Item -ItemType Directory -Path $racePortraitOutputDir -Force | Out-Null
}

foreach ($portrait in $racePortraits) {
    Write-Host "Generating race portrait: $($portrait.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $portrait.Id
            Prompt = "$($portrait.Desc). Race portrait for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $racePortraitOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($portrait.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($portrait.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 2. EQUIPMENT ICONS (Common Set)
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Common Equipment Icons" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$commonEquipment = @(
    # Weapons
    @{ Id = "equip_primitiveLaserPistol"; Name = "Primitive Laser Pistol"; Desc = "Primitive laser pistol icon, basic energy weapon, 32x32" },
    @{ Id = "equip_woodenBow"; Name = "Wooden Bow"; Desc = "Wooden bow icon, basic ranged weapon, 32x32" },
    @{ Id = "equip_woodSword"; Name = "Wood Sword"; Desc = "Wood sword icon, basic melee weapon, 32x32" },
    @{ Id = "equip_stoneSpear"; Name = "Stone Spear"; Desc = "Stone spear icon, basic melee weapon, 32x32" },
    @{ Id = "equip_copperDagger"; Name = "Copper Dagger"; Desc = "Copper dagger icon, basic melee weapon, 32x32" },
    
    # Armor
    @{ Id = "equip_clothShirt"; Name = "Cloth Shirt"; Desc = "Cloth shirt icon, basic armor, 32x32" },
    @{ Id = "equip_leatherArmor"; Name = "Leather Armor"; Desc = "Leather armor icon, basic armor, 32x32" },
    @{ Id = "equip_ironHelmet"; Name = "Iron Helmet"; Desc = "Iron helmet icon, basic armor, 32x32" },
    @{ Id = "equip_woolCape"; Name = "Wool Cape"; Desc = "Wool cape icon, basic armor, 32x32" },
    @{ Id = "equip_boneArmor"; Name = "Bone Armor"; Desc = "Bone armor icon, basic armor, 32x32" },
    
    # Gadgets
    @{ Id = "equip_healingPotion"; Name = "Healing Potion"; Desc = "Healing potion icon, consumable item, 32x32" },
    @{ Id = "equip_repairKit"; Name = "Repair Kit"; Desc = "Repair kit icon, utility item, 32x32" },
    @{ Id = "equip_torch"; Name = "Torch"; Desc = "Torch icon, light source, 32x32" },
    @{ Id = "equip_rope"; Name = "Rope"; Desc = "Rope icon, utility item, 32x32" },
    @{ Id = "equip_compass"; Name = "Compass"; Desc = "Compass icon, navigation item, 32x32" }
)

# Validate $ModPath before Join-Path
$equipmentOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($equipmentOutputDir)) {
    Write-Host "  [FAIL] equipmentOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($equipmentOutputDir)) {
    Write-Host "  [FAIL] equipmentOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $equipmentOutputDir)) {
    New-Item -ItemType Directory -Path $equipmentOutputDir -Force | Out-Null
}

foreach ($equip in $commonEquipment) {
    Write-Host "Generating equipment icon: $($equip.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $equip.Id
            Prompt = "$($equip.Desc). Equipment icon for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $equipmentOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($equip.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($equip.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 3. EQUIPMENT ICONS (Rare Set)
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Rare Equipment Icons" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$rareEquipment = @(
    # Weapons
    @{ Id = "equip_ironRifle"; Name = "Iron Rifle"; Desc = "Iron rifle icon, advanced ranged weapon, 32x32" },
    @{ Id = "equip_floranBlade"; Name = "Floran Blade"; Desc = "Floran blade icon, plant-based weapon, 32x32" },
    @{ Id = "equip_avianSpear"; Name = "Avian Spear"; Desc = "Avian spear icon, bird-themed weapon, 32x32" },
    @{ Id = "equip_glitchSword"; Name = "Glitch Sword"; Desc = "Glitch sword icon, robotic weapon, 32x32" },
    @{ Id = "equip_hylotlTrident"; Name = "Hylotl Trident"; Desc = "Hylotl trident icon, aquatic weapon, 32x32" },
    
    # Armor
    @{ Id = "equip_chainmail"; Name = "Chainmail"; Desc = "Chainmail icon, advanced armor, 32x32" },
    @{ Id = "equip_floranHide"; Name = "Floran Hide"; Desc = "Floran hide icon, plant-based armor, 32x32" },
    @{ Id = "equip_avianFeatherCloak"; Name = "Avian Feather Cloak"; Desc = "Avian feather cloak icon, bird-themed armor, 32x32" },
    @{ Id = "equip_glitchArmor"; Name = "Glitch Armor"; Desc = "Glitch armor icon, robotic armor, 32x32" },
    @{ Id = "equip_hylotlScale"; Name = "Hylotl Scale"; Desc = "Hylotl scale icon, aquatic armor, 32x32" },
    
    # Gadgets
    @{ Id = "equip_energyCell"; Name = "Energy Cell"; Desc = "Energy cell icon, power source, 32x32" },
    @{ Id = "equip_teleporterBeacon"; Name = "Teleporter Beacon"; Desc = "Teleporter beacon icon, teleportation device, 32x32" },
    @{ Id = "equip_shieldGenerator"; Name = "Shield Generator"; Desc = "Shield generator icon, defensive device, 32x32" },
    @{ Id = "equip_jetpack"; Name = "Jetpack"; Desc = "Jetpack icon, flight device, 32x32" },
    @{ Id = "equip_scanner"; Name = "Scanner"; Desc = "Scanner icon, detection device, 32x32" }
)

# Validate $ModPath before Join-Path
$rareEquipmentOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($rareEquipmentOutputDir)) {
    Write-Host "  [FAIL] rareEquipmentOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($rareEquipmentOutputDir)) {
    Write-Host "  [FAIL] rareEquipmentOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $rareEquipmentOutputDir)) {
    New-Item -ItemType Directory -Path $rareEquipmentOutputDir -Force | Out-Null
}

foreach ($equip in $rareEquipment) {
    Write-Host "Generating equipment icon: $($equip.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $equip.Id
            Prompt = "$($equip.Desc). Equipment icon for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $rareEquipmentOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($equip.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($equip.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 4. EQUIPMENT ICONS (Legendary Set)
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Legendary Equipment Icons" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$legendaryEquipment = @(
    # Weapons
    @{ Id = "equip_etherialStaff"; Name = "Etherial Staff"; Desc = "Etherial staff icon, magical weapon, 32x32" },
    @{ Id = "equip_novaCannon"; Name = "Nova Cannon"; Desc = "Nova cannon icon, powerful energy weapon, 32x32" },
    @{ Id = "equip_voidKatana"; Name = "Void Katana"; Desc = "Void katana icon, dark energy weapon, 32x32" },
    @{ Id = "equip_dragonBlade"; Name = "Dragon Blade"; Desc = "Dragon blade icon, legendary melee weapon, 32x32" },
    @{ Id = "equip_phoenixBow"; Name = "Phoenix Bow"; Desc = "Phoenix bow icon, fire-themed weapon, 32x32" },
    
    # Armor
    @{ Id = "equip_dragonPlate"; Name = "Dragon Plate"; Desc = "Dragon plate icon, legendary armor, 32x32" },
    @{ Id = "equip_phoenixCloak"; Name = "Phoenix Cloak"; Desc = "Phoenix cloak icon, fire-themed armor, 32x32" },
    @{ Id = "equip_titanHelm"; Name = "Titan Helm"; Desc = "Titan helm icon, powerful armor, 32x32" },
    @{ Id = "equip_voidArmor"; Name = "Void Armor"; Desc = "Void armor icon, dark energy armor, 32x32" },
    @{ Id = "equip_starCloak"; Name = "Star Cloak"; Desc = "Star cloak icon, cosmic armor, 32x32" },
    
    # Gadgets
    @{ Id = "equip_gravityBoots"; Name = "Gravity Boots"; Desc = "Gravity boots icon, movement device, 32x32" },
    @{ Id = "equip_phaseBlade"; Name = "Phase Blade"; Desc = "Phase blade icon, phase-shifting weapon, 32x32" },
    @{ Id = "equip_timeDilator"; Name = "Time Dilator"; Desc = "Time dilator icon, time manipulation device, 32x32" },
    @{ Id = "equip_warpDrive"; Name = "Warp Drive"; Desc = "Warp drive icon, space travel device, 32x32" },
    @{ Id = "equip_realityShifter"; Name = "Reality Shifter"; Desc = "Reality shifter icon, reality manipulation device, 32x32" }
)

# Validate $ModPath before Join-Path
$legendaryEquipmentOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($legendaryEquipmentOutputDir)) {
    Write-Host "  [FAIL] legendaryEquipmentOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($legendaryEquipmentOutputDir)) {
    Write-Host "  [FAIL] legendaryEquipmentOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $legendaryEquipmentOutputDir)) {
    New-Item -ItemType Directory -Path $legendaryEquipmentOutputDir -Force | Out-Null
}

foreach ($equip in $legendaryEquipment) {
    Write-Host "Generating equipment icon: $($equip.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $equip.Id
            Prompt = "$($equip.Desc). Equipment icon for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $legendaryEquipmentOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($equip.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($equip.Name) : $_" -ForegroundColor Red
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
Write-Host "  Race Portraits: $(Join-Path $ModPath 'assets\races\portraits')" -ForegroundColor Gray
Write-Host "  Common Equipment: $(Join-Path $ModPath 'assets\equipment\common')" -ForegroundColor Gray
Write-Host "  Rare Equipment: $(Join-Path $ModPath 'assets\equipment\rare')" -ForegroundColor Gray
Write-Host "  Legendary Equipment: $(Join-Path $ModPath 'assets\equipment\legendary')" -ForegroundColor Gray
Write-Host ""
Write-Host "Race portraits: assets/races/portraits/race_portrait_*.png" -ForegroundColor Gray
Write-Host "Equipment icons: assets/equipment/*/equip_*.png" -ForegroundColor Gray
Write-Host ""
