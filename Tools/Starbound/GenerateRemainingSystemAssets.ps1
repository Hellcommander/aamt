#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate assets for remaining systems (UI, Weapons, Wildfire, Status Effects, Traps, Tiles).
    
.DESCRIPTION
    Generates sprites, icons, and effects for:
    - UI elements (spell mod icons, widgets, buttons, panels)
    - Weapon sprites and sub-ability icons
    - Wildfire particle effects
    - Status effect icons and particles
    - Trap sprites and effects
    - Tile textures
    
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
Write-Host "  Remaining System Assets Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$generated = 0
$failed = 0

# ============================================================
# 1. UI ELEMENTS (Spell Mod Icons, Widgets)
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating UI Elements" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$uiElements = @(
    @{ Id = "ui_spell_mod_icon_template"; Name = "Spell Mod Icon Template"; Desc = "Spell mod icon template, generic spell modifier, 32x32" },
    @{ Id = "ui_button_default"; Name = "Default Button"; Desc = "Default UI button sprite, standard button, 64x32" },
    @{ Id = "ui_button_hover"; Name = "Button Hover"; Desc = "Button hover state sprite, highlighted button, 64x32" },
    @{ Id = "ui_button_pressed"; Name = "Button Pressed"; Desc = "Button pressed state sprite, active button, 64x32" },
    @{ Id = "ui_panel_background"; Name = "Panel Background"; Desc = "UI panel background texture, panel background, 128x128" },
    @{ Id = "ui_panel_border"; Name = "Panel Border"; Desc = "UI panel border texture, panel border, 128x128" },
    @{ Id = "ui_scrollbar"; Name = "Scrollbar"; Desc = "UI scrollbar sprite, scrollbar element, 16x64" },
    @{ Id = "ui_slot_template"; Name = "Slot Template"; Desc = "UI slot template sprite, item slot, 32x32" },
    @{ Id = "ui_overflow_indicator"; Name = "Overflow Indicator"; Desc = "UI overflow indicator icon, more items indicator, 16x16" }
)

# Validate $ModPath before Join-Path
$uiOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($uiOutputDir)) {
    Write-Host "  [FAIL] uiOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($uiOutputDir)) {
    Write-Host "  [FAIL] uiOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $uiOutputDir)) {
    New-Item -ItemType Directory -Path $uiOutputDir -Force | Out-Null
}

foreach ($ui in $uiElements) {
    Write-Host "Generating UI element: $($ui.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $ui.Id
            Prompt = "$($ui.Desc). UI element for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $uiOutputDir
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
# 2. WEAPON SPRITES AND SUB-ABILITY ICONS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Weapon Sprites and Sub-Ability Icons" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$weaponSprites = @(
    @{ Id = "weapon_sword_basic"; Name = "Basic Sword"; Desc = "Basic sword weapon sprite, simple sword, 64x64" },
    @{ Id = "weapon_bow_basic"; Name = "Basic Bow"; Desc = "Basic bow weapon sprite, simple bow, 64x64" },
    @{ Id = "weapon_staff_basic"; Name = "Basic Staff"; Desc = "Basic staff weapon sprite, simple staff, 64x64" },
    @{ Id = "weapon_pistol_basic"; Name = "Basic Pistol"; Desc = "Basic pistol weapon sprite, simple gun, 64x64" },
    @{ Id = "subability_icon_template"; Name = "Sub-Ability Icon Template"; Desc = "Sub-ability icon template, generic ability, 32x32" },
    @{ Id = "subability_cooldown"; Name = "Sub-Ability Cooldown"; Desc = "Sub-ability cooldown indicator, ability on cooldown, 32x32" },
    @{ Id = "subability_ready"; Name = "Sub-Ability Ready"; Desc = "Sub-ability ready indicator, ability available, 32x32" }
)

# Validate $ModPath before Join-Path
$weaponOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($weaponOutputDir)) {
    Write-Host "  [FAIL] weaponOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($weaponOutputDir)) {
    Write-Host "  [FAIL] weaponOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $weaponOutputDir)) {
    New-Item -ItemType Directory -Path $weaponOutputDir -Force | Out-Null
}

foreach ($weapon in $weaponSprites) {
    Write-Host "Generating weapon sprite: $($weapon.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Sprite"
            AssetName = $weapon.Id
            Prompt = "$($weapon.Desc). Weapon sprite for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $weaponOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($weapon.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($weapon.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 3. CLUSTER BOMB SPRITES
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Cluster Bomb Sprites" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$clusterBombTypes = @(
    @{ Id = "cluster_bomb_explosive"; Name = "Explosive Cluster Bomb"; Desc = "Explosive cluster bomb sprite, standard explosive, 32x32" },
    @{ Id = "cluster_bomb_incendiary"; Name = "Incendiary Cluster Bomb"; Desc = "Incendiary cluster bomb sprite, fire cluster, 32x32" },
    @{ Id = "cluster_bomb_shrapnel"; Name = "Shrapnel Cluster Bomb"; Desc = "Shrapnel cluster bomb sprite, fragment cluster, 32x32" },
    @{ Id = "cluster_bomb_plasma"; Name = "Plasma Cluster Bomb"; Desc = "Plasma cluster bomb sprite, energy cluster, 32x32" },
    @{ Id = "cluster_bomb_cryo"; Name = "Cryo Cluster Bomb"; Desc = "Cryo cluster bomb sprite, ice cluster, 32x32" },
    @{ Id = "cluster_bomb_poison_gas"; Name = "Poison Gas Cluster Bomb"; Desc = "Poison gas cluster bomb sprite, toxic cluster, 32x32" },
    @{ Id = "cluster_bomb_emp"; Name = "EMP Cluster Bomb"; Desc = "EMP cluster bomb sprite, electronic disruption, 32x32" },
    @{ Id = "cluster_bomb_gravity"; Name = "Gravity Cluster Bomb"; Desc = "Gravity cluster bomb sprite, gravitational anomaly, 32x32" },
    @{ Id = "cluster_bomb_temporal"; Name = "Temporal Cluster Bomb"; Desc = "Temporal cluster bomb sprite, time distortion, 32x32" },
    @{ Id = "cluster_bomb_arcane"; Name = "Arcane Cluster Bomb"; Desc = "Arcane cluster bomb sprite, magical cluster, 32x32" },
    @{ Id = "cluster_bomb_void"; Name = "Void Cluster Bomb"; Desc = "Void cluster bomb sprite, void cluster, 32x32" }
)

# Validate $ModPath before Join-Path
$clusterBombOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($clusterBombOutputDir)) {
    Write-Host "  [FAIL] clusterBombOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($clusterBombOutputDir)) {
    Write-Host "  [FAIL] clusterBombOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $clusterBombOutputDir)) {
    New-Item -ItemType Directory -Path $clusterBombOutputDir -Force | Out-Null
}

foreach ($bomb in $clusterBombTypes) {
    Write-Host "Generating cluster bomb sprite: $($bomb.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Sprite"
            AssetName = $bomb.Id
            Prompt = "$($bomb.Desc). Cluster bomb sprite for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $clusterBombOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($bomb.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($bomb.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 4. WILDFIRE EFFECTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Wildfire Effects" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$wildfireEffects = @(
    @{ Id = "wildfire_fire_particle"; Name = "Wildfire Fire Particle"; Desc = "Wildfire fire particle effect, spreading fire" },
    @{ Id = "wildfire_smoke"; Name = "Wildfire Smoke"; Desc = "Wildfire smoke particle effect, fire smoke" },
    @{ Id = "wildfire_ember"; Name = "Wildfire Ember"; Desc = "Wildfire ember particle effect, flying embers" },
    @{ Id = "wildfire_ignition"; Name = "Wildfire Ignition"; Desc = "Wildfire ignition effect, fire starting" },
    @{ Id = "wildfire_extinguish"; Name = "Wildfire Extinguish"; Desc = "Wildfire extinguish effect, fire being put out" },
    @{ Id = "wildfire_texture"; Name = "Wildfire Texture"; Desc = "Wildfire texture, fire cell texture, 16x16" }
)

# Validate $ModPath before Join-Path
$wildfireOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($wildfireOutputDir)) {
    Write-Host "  [FAIL] wildfireOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($wildfireOutputDir)) {
    Write-Host "  [FAIL] wildfireOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $wildfireOutputDir)) {
    New-Item -ItemType Directory -Path $wildfireOutputDir -Force | Out-Null
}

foreach ($effect in $wildfireEffects) {
    Write-Host "Generating wildfire effect: $($effect.Name)" -ForegroundColor Cyan
    
    try {
        $assetType = if ($effect.Id -like "*texture*") { "Texture" } else { "Particle" }
        
        $params = @{
            AssetType = $assetType
            AssetName = $effect.Id
            Prompt = "$($effect.Desc). Wildfire effect for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $wildfireOutputDir
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
# 5. STATUS EFFECT ICONS AND PARTICLES
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Status Effect Icons and Particles" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$statusEffects = @(
    @{ Id = "status_burn"; Name = "Burn Status"; Desc = "Burn status effect icon, fire damage, 32x32" },
    @{ Id = "status_freeze"; Name = "Freeze Status"; Desc = "Freeze status effect icon, ice damage, 32x32" },
    @{ Id = "status_poison"; Name = "Poison Status"; Desc = "Poison status effect icon, poison damage, 32x32" },
    @{ Id = "status_stun"; Name = "Stun Status"; Desc = "Stun status effect icon, stunned, 32x32" },
    @{ Id = "status_slow"; Name = "Slow Status"; Desc = "Slow status effect icon, movement slowed, 32x32" },
    @{ Id = "status_regeneration"; Name = "Regeneration Status"; Desc = "Regeneration status effect icon, health regen, 32x32" },
    @{ Id = "status_strength"; Name = "Strength Status"; Desc = "Strength status effect icon, damage boost, 32x32" },
    @{ Id = "status_weakness"; Name = "Weakness Status"; Desc = "Weakness status effect icon, damage reduction, 32x32" },
    @{ Id = "status_burn_particle"; Name = "Burn Particle"; Desc = "Burn status particle effect, fire particles" },
    @{ Id = "status_freeze_particle"; Name = "Freeze Particle"; Desc = "Freeze status particle effect, ice particles" },
    @{ Id = "status_poison_particle"; Name = "Poison Particle"; Desc = "Poison status particle effect, toxic particles" }
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

foreach ($status in $statusEffects) {
    Write-Host "Generating status effect: $($status.Name)" -ForegroundColor Cyan
    
    try {
        $assetType = if ($status.Id -like "*particle*") { "Particle" } else { "Icon" }
        
        $params = @{
            AssetType = $assetType
            AssetName = $status.Id
            Prompt = "$($status.Desc). Status effect for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $statusOutputDir
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

# ============================================================
# 6. TRAP SPRITES AND EFFECTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Trap Sprites and Effects" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$traps = @(
    @{ Id = "trap_spike"; Name = "Spike Trap"; Desc = "Spike trap sprite, spike trap, 32x32" },
    @{ Id = "trap_pressure_plate"; Name = "Pressure Plate Trap"; Desc = "Pressure plate trap sprite, pressure plate, 32x32" },
    @{ Id = "trap_arrow"; Name = "Arrow Trap"; Desc = "Arrow trap sprite, arrow trap, 32x32" },
    @{ Id = "trap_fire"; Name = "Fire Trap"; Desc = "Fire trap sprite, fire trap, 32x32" },
    @{ Id = "trap_poison"; Name = "Poison Trap"; Desc = "Poison trap sprite, poison trap, 32x32" },
    @{ Id = "trap_activation"; Name = "Trap Activation"; Desc = "Trap activation particle effect, trap triggering" },
    @{ Id = "trap_disarmed"; Name = "Trap Disarmed"; Desc = "Trap disarmed effect, trap disabled" }
)

# Validate $ModPath before Join-Path
$trapOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($trapOutputDir)) {
    Write-Host "  [FAIL] trapOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($trapOutputDir)) {
    Write-Host "  [FAIL] trapOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $trapOutputDir)) {
    New-Item -ItemType Directory -Path $trapOutputDir -Force | Out-Null
}

foreach ($trap in $traps) {
    Write-Host "Generating trap asset: $($trap.Name)" -ForegroundColor Cyan
    
    try {
        $assetType = if ($trap.Id -like "*activation*" -or $trap.Id -like "*disarmed*") { "Particle" } else { "Sprite" }
        
        $params = @{
            AssetType = $assetType
            AssetName = $trap.Id
            Prompt = "$($trap.Desc). Trap asset for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $trapOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($trap.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($trap.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 7. TILE TEXTURES
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Tile Textures" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$tiles = @(
    @{ Id = "tile_stone"; Name = "Stone Tile"; Desc = "Stone tile texture, seamless stone tile, 16x16" },
    @{ Id = "tile_dirt"; Name = "Dirt Tile"; Desc = "Dirt tile texture, seamless dirt tile, 16x16" },
    @{ Id = "tile_grass"; Name = "Grass Tile"; Desc = "Grass tile texture, seamless grass tile, 16x16" },
    @{ Id = "tile_sand"; Name = "Sand Tile"; Desc = "Sand tile texture, seamless sand tile, 16x16" },
    @{ Id = "tile_wood"; Name = "Wood Tile"; Desc = "Wood tile texture, seamless wood tile, 16x16" },
    @{ Id = "tile_metal"; Name = "Metal Tile"; Desc = "Metal tile texture, seamless metal tile, 16x16" },
    @{ Id = "tile_brick"; Name = "Brick Tile"; Desc = "Brick tile texture, seamless brick tile, 16x16" },
    @{ Id = "tile_cobblestone"; Name = "Cobblestone Tile"; Desc = "Cobblestone tile texture, seamless cobblestone, 16x16" }
)

# Validate $ModPath before Join-Path
$tileOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($tileOutputDir)) {
    Write-Host "  [FAIL] tileOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($tileOutputDir)) {
    Write-Host "  [FAIL] tileOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $tileOutputDir)) {
    New-Item -ItemType Directory -Path $tileOutputDir -Force | Out-Null
}

foreach ($tile in $tiles) {
    Write-Host "Generating tile texture: $($tile.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Texture"
            AssetName = $tile.Id
            Prompt = "$($tile.Desc). Tile texture for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $tileOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($tile.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($tile.Name) : $_" -ForegroundColor Red
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
Write-Host "  UI Elements: $(Join-Path $ModPath 'assets\ui\elements')" -ForegroundColor Gray
Write-Host "  Weapon Sprites: $(Join-Path $ModPath 'assets\weapons\sprites')" -ForegroundColor Gray
Write-Host "  Cluster Bombs: $(Join-Path $ModPath 'assets\weapons\cluster_bombs')" -ForegroundColor Gray
Write-Host "  Wildfire: $(Join-Path $ModPath 'assets\wildfire')" -ForegroundColor Gray
Write-Host "  Status Effects: $(Join-Path $ModPath 'assets\status_effects')" -ForegroundColor Gray
Write-Host "  Traps: $(Join-Path $ModPath 'assets\traps')" -ForegroundColor Gray
Write-Host "  Tiles: $(Join-Path $ModPath 'assets\tiles')" -ForegroundColor Gray
Write-Host ""
