#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate assets for all generator modules in the mod.
    
.DESCRIPTION
    Generates sprites, particles, and effects for all generator modules including:
    - Projectile generators (various types)
    - Spell generators
    - Mech generators
    - Cosmic generators
    - Asset generators
    - And many more...
    
.PARAMETER ModPath
    Path to the mod directory
    
.PARAMETER OllamaModel
    Ollama model to use
    
.PARAMETER UseCppBackend
    Use C++ backend for generation
    
.PARAMETER GeneratorFilter
    Optional filter to generate only specific generator types (comma-separated)
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$ModPath = "F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery",
    
    [Parameter(Mandatory=$false)]
    [string]$OllamaModel = "codellama:7b-instruct",
    
    [Parameter(Mandatory=$false)]
    [bool]$UseCppBackend = $true,
    
    [Parameter(Mandatory=$false)]
    [string]$GeneratorFilter = ""
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
Write-Host "  Comprehensive Generator Module Asset Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$generated = 0
$failed = 0

# Filter logic
$filterList = @()
if ($GeneratorFilter) {
    $filterList = $GeneratorFilter.Split(',') | ForEach-Object { $_.Trim().ToLower() }
}

function ShouldGenerate {
    param([string]$generatorName)
    if ($filterList.Count -eq 0) { return $true }
    return $filterList -contains $generatorName.ToLower()
}

# ============================================================
# PROJECTILE GENERATORS
# ============================================================
if (ShouldGenerate "projectile") {
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
    Write-Host "  Generating Projectile Generator Assets" -ForegroundColor Yellow
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
    Write-Host ""

    $projectileGenerators = @(
        @{ Id = "projectile_basic"; Name = "Basic Projectile"; Desc = "Basic projectile sprite, simple bullet, 32x32" },
        @{ Id = "projectile_explosive"; Name = "Explosive Projectile"; Desc = "Explosive projectile sprite, red/orange, 32x32" },
        @{ Id = "projectile_barbed"; Name = "Barbed Projectile"; Desc = "Barbed projectile sprite, spiked appearance, 32x32" },
        @{ Id = "projectile_blackhole"; Name = "Blackhole Projectile"; Desc = "Blackhole projectile sprite, dark void, 32x32" },
        @{ Id = "projectile_comet"; Name = "Comet Projectile"; Desc = "Comet projectile sprite, icy tail, 32x32" },
        @{ Id = "projectile_gyro"; Name = "Gyro Projectile"; Desc = "Gyro projectile sprite, spinning, 32x32" },
        @{ Id = "projectile_homing"; Name = "Homing Projectile"; Desc = "Homing projectile sprite, tracking, 32x32" },
        @{ Id = "projectile_lightning"; Name = "Lightning Projectile"; Desc = "Lightning projectile sprite, electrical, 32x32" },
        @{ Id = "projectile_plasma"; Name = "Plasma Projectile"; Desc = "Plasma projectile sprite, energy, 32x32" },
        @{ Id = "projectile_shotgun"; Name = "Shotgun Pellet"; Desc = "Shotgun pellet sprite, small bullet, 16x16" }
    )

    # Validate $ModPath before Join-Path
$projOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($projOutputDir)) {
        Write-Host "  [FAIL] projOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
 if ([string]::IsNullOrWhiteSpace($projOutputDir)) {
        Write-Host "  [FAIL] projOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
    if (-not (Test-Path $projOutputDir)) { New-Item -ItemType Directory -Path $projOutputDir -Force | Out-Null }

    foreach ($proj in $projectileGenerators) {
        Write-Host "Generating: $($proj.Name)" -ForegroundColor Cyan
        try {
            $params = @{
                AssetType = "Projectile"
                AssetName = $proj.Id
                Prompt = "$($proj.Desc). Projectile sprite for Starbound."
                OllamaModel = $OllamaModel
                OutputDir = $projOutputDir
            }
            $params['UseCppBackend'] = $UseCppBackend
            & $assetGenerator @params | Out-Null
            $generated++
            Write-Host "  [OK]" -ForegroundColor Green
        } catch {
            $failed++
            Write-Host "  [FAIL]: $_" -ForegroundColor Red
        }
    }
    Write-Host ""
}

# ============================================================
# SPELL GENERATORS
# ============================================================
if (ShouldGenerate "spell") {
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
    Write-Host "  Generating Spell Generator Assets" -ForegroundColor Yellow
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
    Write-Host ""

    $spellGenerators = @(
        @{ Id = "spell_vortex"; Name = "Vortex Spell"; Desc = "Vortex spell sprite, swirling energy, 64x64" },
        @{ Id = "spell_snake"; Name = "Snake Spell"; Desc = "Snake spell sprite, serpentine energy, 64x64" },
        @{ Id = "spell_fireball"; Name = "Fireball Spell"; Desc = "Fireball spell sprite, fire ball, 64x64" },
        @{ Id = "spell_ice_shard"; Name = "Ice Shard Spell"; Desc = "Ice shard spell sprite, crystal shard, 64x64" },
        @{ Id = "spell_frost_nova"; Name = "Frost Nova Spell"; Desc = "Frost nova spell sprite, ice burst, 64x64" },
        @{ Id = "spell_orb"; Name = "Orb Spell"; Desc = "Orb spell sprite, energy orb, 64x64" }
    )

    # Validate $ModPath before Join-Path
$spellOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($spellOutputDir)) {
        Write-Host "  [FAIL] spellOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
 if ([string]::IsNullOrWhiteSpace($spellOutputDir)) {
        Write-Host "  [FAIL] spellOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
    if (-not (Test-Path $spellOutputDir)) { New-Item -ItemType Directory -Path $spellOutputDir -Force | Out-Null }

    foreach ($spell in $spellGenerators) {
        Write-Host "Generating: $($spell.Name)" -ForegroundColor Cyan
        try {
            $params = @{
                AssetType = "Projectile"
                AssetName = $spell.Id
                Prompt = "$($spell.Desc). Spell sprite for Starbound."
                OllamaModel = $OllamaModel
                OutputDir = $spellOutputDir
            }
            $params['UseCppBackend'] = $UseCppBackend
            & $assetGenerator @params | Out-Null
            $generated++
            Write-Host "  [OK]" -ForegroundColor Green
        } catch {
            $failed++
            Write-Host "  [FAIL]: $_" -ForegroundColor Red
        }
    }
    Write-Host ""
}

# ============================================================
# MECH GENERATORS
# ============================================================
if (ShouldGenerate "mech") {
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
    Write-Host "  Generating Mech Generator Assets" -ForegroundColor Yellow
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
    Write-Host ""

    $mechGenerators = @(
        @{ Id = "mech_worm"; Name = "Worm Mech"; Desc = "Worm mech sprite, segmented worm, 64x64" },
        @{ Id = "mech_centipede"; Name = "Centipede Mech"; Desc = "Centipede mech sprite, multi-segmented, 64x64" },
        @{ Id = "mech_snake"; Name = "Snake Mech"; Desc = "Snake mech sprite, serpentine mech, 64x64" },
        @{ Id = "mech_cockpit"; Name = "Mech Cockpit"; Desc = "Mech cockpit sprite, cockpit interior, 64x64" }
    )

    # Validate $ModPath before Join-Path
$mechOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($mechOutputDir)) {
        Write-Host "  [FAIL] mechOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
 if ([string]::IsNullOrWhiteSpace($mechOutputDir)) {
        Write-Host "  [FAIL] mechOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
    if (-not (Test-Path $mechOutputDir)) { New-Item -ItemType Directory -Path $mechOutputDir -Force | Out-Null }

    foreach ($mech in $mechGenerators) {
        Write-Host "Generating: $($mech.Name)" -ForegroundColor Cyan
        try {
            $params = @{
                AssetType = "MechSprite"
                AssetName = $mech.Id
                Prompt = "$($mech.Desc). Mech sprite for Starbound."
                OllamaModel = $OllamaModel
                OutputDir = $mechOutputDir
            }
            $params['UseCppBackend'] = $UseCppBackend
            & $assetGenerator @params | Out-Null
            $generated++
            Write-Host "  [OK]" -ForegroundColor Green
        } catch {
            $failed++
            Write-Host "  [FAIL]: $_" -ForegroundColor Red
        }
    }
    Write-Host ""
}

# ============================================================
# COSMIC GENERATORS
# ============================================================
if (ShouldGenerate "cosmic") {
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
    Write-Host "  Generating Cosmic Generator Assets" -ForegroundColor Yellow
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
    Write-Host ""

    $cosmicAssets = @(
        @{ Id = "cosmic_star_icon"; Name = "Star Icon"; Desc = "Star icon, stellar object, 32x32" },
        @{ Id = "cosmic_planet_icon"; Name = "Planet Icon"; Desc = "Planet icon, planetary object, 32x32" },
        @{ Id = "cosmic_blackhole_icon"; Name = "Blackhole Icon"; Desc = "Blackhole icon, dark void, 32x32" },
        @{ Id = "cosmic_nebula_icon"; Name = "Nebula Icon"; Desc = "Nebula icon, cosmic cloud, 32x32" },
        @{ Id = "cosmic_quantum_storm"; Name = "Quantum Storm"; Desc = "Quantum storm effect, particle field, 64x64" },
        @{ Id = "cosmic_void_rift"; Name = "Void Rift"; Desc = "Void rift effect, dimensional tear, 64x64" }
    )

    # Validate $ModPath before Join-Path
$cosmicOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($cosmicOutputDir)) {
        Write-Host "  [FAIL] cosmicOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
 if ([string]::IsNullOrWhiteSpace($cosmicOutputDir)) {
        Write-Host "  [FAIL] cosmicOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
    if (-not (Test-Path $cosmicOutputDir)) { New-Item -ItemType Directory -Path $cosmicOutputDir -Force | Out-Null }

    foreach ($cosmic in $cosmicAssets) {
        Write-Host "Generating: $($cosmic.Name)" -ForegroundColor Cyan
        try {
            $assetType = if ($cosmic.Id -like "*icon*") { "Icon" } elseif ($cosmic.Id -like "*effect*" -or $cosmic.Id -like "*storm*" -or $cosmic.Id -like "*rift*") { "Particle" } else { "Icon" }
            $params = @{
                AssetType = $assetType
                AssetName = $cosmic.Id
                Prompt = "$($cosmic.Desc). Cosmic asset for Starbound."
                OllamaModel = $OllamaModel
                OutputDir = $cosmicOutputDir
            }
            $params['UseCppBackend'] = $UseCppBackend
            & $assetGenerator @params | Out-Null
            $generated++
            Write-Host "  [OK]" -ForegroundColor Green
        } catch {
            $failed++
            Write-Host "  [FAIL]: $_" -ForegroundColor Red
        }
    }
    Write-Host ""
}

# ============================================================
# SPECIALIZED PROJECTILE GENERATORS
# ============================================================
if (ShouldGenerate "specialized") {
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
    Write-Host "  Generating Specialized Generator Assets" -ForegroundColor Yellow
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
    Write-Host ""

    $specializedAssets = @(
        # Boomerang & Returning
        @{ Id = "boomerang_disc"; Name = "Boomerang Disc"; Desc = "Boomerang disc sprite, returning disc, 32x32"; Type = "Projectile" },
        
        # Grapple & Chain
        @{ Id = "grapple_hook"; Name = "Grapple Hook"; Desc = "Grapple hook sprite, hook and chain, 32x32"; Type = "Projectile" },
        
        # Beams
        @{ Id = "beam_energy"; Name = "Energy Beam"; Desc = "Energy beam sprite, laser beam, 32x32"; Type = "Projectile" },
        @{ Id = "beam_net"; Name = "Beam Net"; Desc = "Beam net sprite, grid of beams, 64x64"; Type = "Projectile" },
        
        # Orbitals
        @{ Id = "drifting_orbital"; Name = "Drifting Orbital"; Desc = "Drifting orbital sprite, orbiting object, 32x32"; Type = "Projectile" },
        
        # Grenades
        @{ Id = "gas_grenade"; Name = "Gas Grenade"; Desc = "Gas grenade sprite, gas canister, 32x32"; Type = "Projectile" },
        
        # Minions & Drones
        @{ Id = "drone_minion"; Name = "Drone Minion"; Desc = "Drone minion sprite, small drone, 32x32"; Type = "Sprite" },
        
        # Traps
        @{ Id = "trap_basic"; Name = "Basic Trap"; Desc = "Basic trap sprite, trap device, 32x32"; Type = "Sprite" },
        
        # Icons
        @{ Id = "status_effect_icon"; Name = "Status Effect Icon"; Desc = "Status effect icon, effect indicator, 32x32"; Type = "Icon" },
        @{ Id = "spellstone_icon"; Name = "Spellstone Icon"; Desc = "Spellstone icon, magical stone, 32x32"; Type = "Icon" },
        @{ Id = "magical_item_icon"; Name = "Magical Item Icon"; Desc = "Magical item icon, enchanted item, 32x32"; Type = "Icon" },
        @{ Id = "ingredient_icon"; Name = "Ingredient Icon"; Desc = "Ingredient icon, alchemy ingredient, 32x32"; Type = "Icon" },
        
        # Segmented Weapons
        @{ Id = "segmented_weapon_basic"; Name = "Segmented Weapon"; Desc = "Segmented weapon sprite, multi-part weapon, 64x64"; Type = "Sprite" },
        
        # Room Generator
        @{ Id = "room_tile_basic"; Name = "Room Tile"; Desc = "Room tile texture, floor tile, 16x16"; Type = "Texture" },
        @{ Id = "room_wall_basic"; Name = "Room Wall"; Desc = "Room wall texture, wall tile, 16x16"; Type = "Texture" },
        
        # Portal Generator
        @{ Id = "portal_network_node"; Name = "Portal Network Node"; Desc = "Portal network node sprite, portal connection point, 32x32"; Type = "PortalSprite" },
        
        # Particle Field
        @{ Id = "particle_field_basic"; Name = "Particle Field"; Desc = "Particle field effect, particle system, 64x64"; Type = "Particle" }
    )

    # Validate $ModPath before Join-Path
$specialOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($specialOutputDir)) {
        Write-Host "  [FAIL] specialOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
 if ([string]::IsNullOrWhiteSpace($specialOutputDir)) {
        Write-Host "  [FAIL] specialOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
    if (-not (Test-Path $specialOutputDir)) { New-Item -ItemType Directory -Path $specialOutputDir -Force | Out-Null }

    foreach ($asset in $specializedAssets) {
        Write-Host "Generating: $($asset.Name)" -ForegroundColor Cyan
        try {
            $params = @{
                AssetType = $asset.Type
                AssetName = $asset.Id
                Prompt = "$($asset.Desc). Asset for Starbound."
                OllamaModel = $OllamaModel
                OutputDir = $specialOutputDir
            }
            $params['UseCppBackend'] = $UseCppBackend
            & $assetGenerator @params | Out-Null
            $generated++
            Write-Host "  [OK]" -ForegroundColor Green
        } catch {
            $failed++
            Write-Host "  [FAIL]: $_" -ForegroundColor Red
        }
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
Write-Host "Assets saved to: $(Join-Path $ModPath 'assets')" -ForegroundColor Gray
Write-Host ""
