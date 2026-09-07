#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate assets for the Spell Systems (Spellcasting, SpellReactions, Spells).
    
.DESCRIPTION
    Generates sprites, particles, and effects for:
    - Spell projectiles (all element types)
    - Spell shape textures
    - Spell reaction effects
    - Fusion effects
    - Area effects
    - Summon sprites
    - Terrain transformation effects
    - Spellcasting UI elements
    
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
Write-Host "  Spell System Asset Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$generated = 0
$failed = 0

# ============================================================
# 1. SPELL PROJECTILES (Element Types)
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Spell Projectiles (Element Types)" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$elementProjectiles = @(
    @{ Id = "spell_projectile_fire"; Name = "Fire Projectile"; Desc = "Fire spell projectile sprite, red/orange flame, 32x32" },
    @{ Id = "spell_projectile_ice"; Name = "Ice Projectile"; Desc = "Ice spell projectile sprite, blue/white ice crystal, 32x32" },
    @{ Id = "spell_projectile_lightning"; Name = "Lightning Projectile"; Desc = "Lightning spell projectile sprite, yellow/white electrical, 32x32" },
    @{ Id = "spell_projectile_arcane"; Name = "Arcane Projectile"; Desc = "Arcane spell projectile sprite, purple magical energy, 32x32" },
    @{ Id = "spell_projectile_nature"; Name = "Nature Projectile"; Desc = "Nature spell projectile sprite, green organic, 32x32" },
    @{ Id = "spell_projectile_shadow"; Name = "Shadow Projectile"; Desc = "Shadow spell projectile sprite, dark/black shadow, 32x32" },
    @{ Id = "spell_projectile_light"; Name = "Light Projectile"; Desc = "Light spell projectile sprite, white/yellow holy, 32x32" },
    @{ Id = "spell_projectile_poison"; Name = "Poison Projectile"; Desc = "Poison spell projectile sprite, green toxic, 32x32" },
    @{ Id = "spell_projectile_physical"; Name = "Physical Projectile"; Desc = "Physical spell projectile sprite, grey kinetic, 32x32" },
    @{ Id = "spell_projectile_void"; Name = "Void Projectile"; Desc = "Void spell projectile sprite, black/purple void, 32x32" }
)

# Validate $ModPath before Join-Path
$projectileOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($projectileOutputDir)) {
    Write-Host "  [FAIL] projectileOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($projectileOutputDir)) {
    Write-Host "  [FAIL] projectileOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $projectileOutputDir)) {
    New-Item -ItemType Directory -Path $projectileOutputDir -Force | Out-Null
}

foreach ($proj in $elementProjectiles) {
    Write-Host "Generating spell projectile: $($proj.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "SpellProjectile"
            AssetName = $proj.Id
            Prompt = "$($proj.Desc). Spell projectile for Starbound spell system."
            OllamaModel = $OllamaModel
            OutputDir = $projectileOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($proj.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($proj.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 2. PRESET SPELL PROJECTILES
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Preset Spell Projectiles" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$presetSpells = @(
    @{ Id = "spell_fireball"; Name = "Fireball"; Desc = "Fireball spell projectile sprite, large fireball, 64x64" },
    @{ Id = "spell_ice_shard"; Name = "Ice Shard"; Desc = "Ice shard spell projectile sprite, sharp ice crystal, 32x32" },
    @{ Id = "spell_lightning_bolt"; Name = "Lightning Bolt"; Desc = "Lightning bolt spell projectile sprite, electrical bolt, 32x32" },
    @{ Id = "spell_magic_missile"; Name = "Magic Missile"; Desc = "Magic missile spell projectile sprite, arcane energy, 32x32" },
    @{ Id = "spell_poison_cloud"; Name = "Poison Cloud"; Desc = "Poison cloud spell sprite, toxic cloud, 64x64" },
    @{ Id = "spell_healing_orb"; Name = "Healing Orb"; Desc = "Healing orb spell projectile sprite, green healing energy, 32x32" },
    @{ Id = "spell_shield_barrier"; Name = "Shield Barrier"; Desc = "Shield barrier spell sprite, protective barrier, 64x64" },
    @{ Id = "spell_meteor_strike"; Name = "Meteor Strike"; Desc = "Meteor strike spell sprite, falling meteor, 64x64" }
)

foreach ($spell in $presetSpells) {
    Write-Host "Generating preset spell: $($spell.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "SpellProjectile"
            AssetName = $spell.Id
            Prompt = "$($spell.Desc). Preset spell for Starbound spell system."
            OllamaModel = $OllamaModel
            OutputDir = $projectileOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($spell.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($spell.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 3. SPELL TRAIL EFFECTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Spell Trail Effects" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$trailEffects = @(
    @{ Id = "spell_trail_fire"; Name = "Fire Trail"; Desc = "Fire spell trail particle effect, flame trail" },
    @{ Id = "spell_trail_ice"; Name = "Ice Trail"; Desc = "Ice spell trail particle effect, frost trail" },
    @{ Id = "spell_trail_lightning"; Name = "Lightning Trail"; Desc = "Lightning spell trail particle effect, electrical trail" },
    @{ Id = "spell_trail_arcane"; Name = "Arcane Trail"; Desc = "Arcane spell trail particle effect, magical trail" },
    @{ Id = "spell_trail_nature"; Name = "Nature Trail"; Desc = "Nature spell trail particle effect, organic trail" },
    @{ Id = "spell_trail_shadow"; Name = "Shadow Trail"; Desc = "Shadow spell trail particle effect, dark trail" },
    @{ Id = "spell_trail_light"; Name = "Light Trail"; Desc = "Light spell trail particle effect, holy trail" },
    @{ Id = "spell_trail_poison"; Name = "Poison Trail"; Desc = "Poison spell trail particle effect, toxic trail" },
    @{ Id = "spell_trail_void"; Name = "Void Trail"; Desc = "Void spell trail particle effect, void trail" }
)

# Validate $ModPath before Join-Path
$trailOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($trailOutputDir)) {
    Write-Host "  [FAIL] trailOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($trailOutputDir)) {
    Write-Host "  [FAIL] trailOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $trailOutputDir)) {
    New-Item -ItemType Directory -Path $trailOutputDir -Force | Out-Null
}

foreach ($trail in $trailEffects) {
    Write-Host "Generating spell trail: $($trail.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Particle"
            AssetName = $trail.Id
            Prompt = "$($trail.Desc). Spell trail effect for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $trailOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($trail.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($trail.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 4. SPELL IMPACT EFFECTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Spell Impact Effects" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$impactEffects = @(
    @{ Id = "spell_impact_fire"; Name = "Fire Impact"; Desc = "Fire spell impact particle effect, fire explosion" },
    @{ Id = "spell_impact_ice"; Name = "Ice Impact"; Desc = "Ice spell impact particle effect, ice shatter" },
    @{ Id = "spell_impact_lightning"; Name = "Lightning Impact"; Desc = "Lightning spell impact particle effect, electrical burst" },
    @{ Id = "spell_impact_arcane"; Name = "Arcane Impact"; Desc = "Arcane spell impact particle effect, magical explosion" },
    @{ Id = "spell_impact_nature"; Name = "Nature Impact"; Desc = "Nature spell impact particle effect, organic burst" },
    @{ Id = "spell_impact_shadow"; Name = "Shadow Impact"; Desc = "Shadow spell impact particle effect, dark explosion" },
    @{ Id = "spell_impact_light"; Name = "Light Impact"; Desc = "Light spell impact particle effect, holy burst" },
    @{ Id = "spell_impact_poison"; Name = "Poison Impact"; Desc = "Poison spell impact particle effect, toxic cloud" },
    @{ Id = "spell_impact_void"; Name = "Void Impact"; Desc = "Void spell impact particle effect, void explosion" }
)

# Validate $ModPath before Join-Path
$impactOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($impactOutputDir)) {
    Write-Host "  [FAIL] impactOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($impactOutputDir)) {
    Write-Host "  [FAIL] impactOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $impactOutputDir)) {
    New-Item -ItemType Directory -Path $impactOutputDir -Force | Out-Null
}

foreach ($impact in $impactEffects) {
    Write-Host "Generating spell impact: $($impact.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Particle"
            AssetName = $impact.Id
            Prompt = "$($impact.Desc). Spell impact effect for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $impactOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($impact.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($impact.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 5. SPELL SHAPE TEXTURES
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Spell Shape Textures" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$spellShapes = @(
    @{ Id = "spell_shape_sphere"; Name = "Sphere Shape"; Desc = "Spell sphere shape texture, spherical magical energy, 64x64" },
    @{ Id = "spell_shape_cone"; Name = "Cone Shape"; Desc = "Spell cone shape texture, conical magical energy, 64x64" },
    @{ Id = "spell_shape_beam"; Name = "Beam Shape"; Desc = "Spell beam shape texture, linear beam energy, 64x64" },
    @{ Id = "spell_shape_wave"; Name = "Wave Shape"; Desc = "Spell wave shape texture, expanding wave energy, 64x64" },
    @{ Id = "spell_shape_helix"; Name = "Helix Shape"; Desc = "Spell helix shape texture, spiral magical energy, 64x64" },
    @{ Id = "spell_shape_cube"; Name = "Cube Shape"; Desc = "Spell cube shape texture, cubic magical energy, 64x64" },
    @{ Id = "spell_shape_torus"; Name = "Torus Shape"; Desc = "Spell torus shape texture, donut magical energy, 64x64" },
    @{ Id = "spell_shape_star"; Name = "Star Shape"; Desc = "Spell star shape texture, star pattern magical energy, 64x64" },
    @{ Id = "spell_shape_rune"; Name = "Rune Shape"; Desc = "Spell rune shape texture, runic symbol magical energy, 64x64" }
)

# Validate $ModPath before Join-Path
$shapeOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($shapeOutputDir)) {
    Write-Host "  [FAIL] shapeOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($shapeOutputDir)) {
    Write-Host "  [FAIL] shapeOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $shapeOutputDir)) {
    New-Item -ItemType Directory -Path $shapeOutputDir -Force | Out-Null
}

foreach ($shape in $spellShapes) {
    Write-Host "Generating spell shape: $($shape.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Texture"
            AssetName = $shape.Id
            Prompt = "$($shape.Desc). Spell shape texture for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $shapeOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($shape.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($shape.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 6. SPELL REACTION EFFECTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Spell Reaction Effects" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$reactionEffects = @(
    @{ Id = "reaction_projectile_hit_surface"; Name = "Projectile Hit Surface"; Desc = "Projectile hit surface reaction particle effect, impact reaction" },
    @{ Id = "reaction_projectile_collide"; Name = "Projectile Collide"; Desc = "Projectile collide reaction particle effect, projectile fusion" },
    @{ Id = "reaction_spell_impact"; Name = "Spell Impact Reaction"; Desc = "Spell impact reaction particle effect, spell surface interaction" },
    @{ Id = "reaction_terrain_transform"; Name = "Terrain Transform"; Desc = "Terrain transform particle effect, terrain modification" },
    @{ Id = "reaction_area_effect"; Name = "Area Effect"; Desc = "Area effect particle effect, area of effect spell" }
)

# Validate $ModPath before Join-Path
$reactionOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($reactionOutputDir)) {
    Write-Host "  [FAIL] reactionOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($reactionOutputDir)) {
    Write-Host "  [FAIL] reactionOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $reactionOutputDir)) {
    New-Item -ItemType Directory -Path $reactionOutputDir -Force | Out-Null
}

foreach ($reaction in $reactionEffects) {
    Write-Host "Generating spell reaction: $($reaction.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Particle"
            AssetName = $reaction.Id
            Prompt = "$($reaction.Desc). Spell reaction effect for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $reactionOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($reaction.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($reaction.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 7. SPELL FUSION EFFECTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Spell Fusion Effects" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$fusionEffects = @(
    @{ Id = "fusion_effect_start"; Name = "Fusion Start"; Desc = "Spell fusion start particle effect, fusion initiation" },
    @{ Id = "fusion_effect_process"; Name = "Fusion Process"; Desc = "Spell fusion process particle effect, spells combining" },
    @{ Id = "fusion_effect_complete"; Name = "Fusion Complete"; Desc = "Spell fusion complete particle effect, fusion result" },
    @{ Id = "fusion_effect_failed"; Name = "Fusion Failed"; Desc = "Spell fusion failed particle effect, fusion failure" }
)

# Validate $ModPath before Join-Path
$fusionOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($fusionOutputDir)) {
    Write-Host "  [FAIL] fusionOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($fusionOutputDir)) {
    Write-Host "  [FAIL] fusionOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $fusionOutputDir)) {
    New-Item -ItemType Directory -Path $fusionOutputDir -Force | Out-Null
}

foreach ($fusion in $fusionEffects) {
    Write-Host "Generating fusion effect: $($fusion.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Particle"
            AssetName = $fusion.Id
            Prompt = "$($fusion.Desc). Spell fusion effect for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $fusionOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($fusion.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($fusion.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 8. SUMMON SPRITES
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Summon Sprites" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$summonSprites = @(
    @{ Id = "summon_generic"; Name = "Generic Summon"; Desc = "Generic summon sprite, magical creature, 32x32" },
    @{ Id = "summon_elemental_fire"; Name = "Fire Elemental Summon"; Desc = "Fire elemental summon sprite, fire creature, 32x32" },
    @{ Id = "summon_elemental_ice"; Name = "Ice Elemental Summon"; Desc = "Ice elemental summon sprite, ice creature, 32x32" },
    @{ Id = "summon_elemental_lightning"; Name = "Lightning Elemental Summon"; Desc = "Lightning elemental summon sprite, electrical creature, 32x32" },
    @{ Id = "summon_turret"; Name = "Turret Summon"; Desc = "Turret summon sprite, defensive turret, 32x32" },
    @{ Id = "summon_minion"; Name = "Minion Summon"; Desc = "Minion summon sprite, small creature, 16x16" }
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

foreach ($summon in $summonSprites) {
    Write-Host "Generating summon sprite: $($summon.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Sprite"
            AssetName = $summon.Id
            Prompt = "$($summon.Desc). Summon sprite for Starbound spell system."
            OllamaModel = $OllamaModel
            OutputDir = $summonOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($summon.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($summon.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 9. SPELLCASTING UI ELEMENTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Spellcasting UI Elements" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$uiElements = @(
    @{ Id = "ui_mana_bar"; Name = "Mana Bar"; Desc = "Mana bar UI element, energy indicator, 32x8" },
    @{ Id = "ui_cooldown_indicator"; Name = "Cooldown Indicator"; Desc = "Cooldown indicator icon, spell recovery, 32x32" },
    @{ Id = "ui_spell_ready"; Name = "Spell Ready"; Desc = "Spell ready indicator icon, spell available, 32x32" },
    @{ Id = "ui_spell_casting"; Name = "Spell Casting"; Desc = "Spell casting indicator icon, spell in progress, 32x32" }
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
            Prompt = "$($ui.Desc). UI element for Starbound spellcasting system."
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
Write-Host "  Spell Projectiles: $(Join-Path $ModPath 'assets\spells\projectiles')" -ForegroundColor Gray
Write-Host "  Spell Trails: $(Join-Path $ModPath 'assets\spells\trails')" -ForegroundColor Gray
Write-Host "  Spell Impacts: $(Join-Path $ModPath 'assets\spells\impacts')" -ForegroundColor Gray
Write-Host "  Spell Shapes: $(Join-Path $ModPath 'assets\spells\shapes')" -ForegroundColor Gray
Write-Host "  Spell Reactions: $(Join-Path $ModPath 'assets\spells\reactions')" -ForegroundColor Gray
Write-Host "  Spell Fusion: $(Join-Path $ModPath 'assets\spells\fusion')" -ForegroundColor Gray
Write-Host "  Summons: $(Join-Path $ModPath 'assets\spells\summons')" -ForegroundColor Gray
Write-Host "  UI Elements: $(Join-Path $ModPath 'assets\spells\ui')" -ForegroundColor Gray
Write-Host ""
