#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate assets for Enhanced Alchemical Grenade Launcher system.
    
.DESCRIPTION
    Generates assets for:
    - Craftable dynamic potion ammo
    - Mana-powered launcher variants
    - Temperature-aware systems

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}
    - Magitech mage rifle
    - Alchemical sphere ammo
    - Alchemical crafting station
    - Container items and UI elements
    
.PARAMETER ModPath
    Path to the mod directory
    
.PARAMETER OllamaModel
    Ollama model to use
    
.PARAMETER PlanningModel
    Planning model for Ollama
    
.PARAMETER VisualModel
    Visual model for Ollama
    
.PARAMETER UseCppBackend
    Use C++ backend for generation
    
.PARAMETER SkipExisting
    Skip assets that already exist
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$ModPath = "F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery",
    
    [Parameter(Mandatory=$false)]
    [string]$OllamaModel = "codellama:7b-instruct",
    
    [Parameter(Mandatory=$false)]
    [string]$PlanningModel = "",
    
    [Parameter(Mandatory=$false)]
    [string]$VisualModel = "wizardlm-uncensored",
    
    [Parameter(Mandatory=$false)]
    [bool]$UseCppBackend = $true,
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipExisting
)

$ErrorActionPreference = "Stop"
# Validate ModPath is not empty
if ([string]::IsNullOrWhiteSpace($ModPath)) {
    Write-Host "Error: ModPath cannot be empty" -ForegroundColor Red
    Write-Host "  Please provide a valid mod path or use the default" -ForegroundColor Gray
    exit 1
}

$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$assetGenerator = Join-Path $PSScriptRoot "StarboundOllamaAssetGenerator.ps1"

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Enhanced Alchemical Launcher Asset Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$generated = 0
$failed = 0
$skipped = 0

# Additional reagent types (beyond the original 10)
$additionalReagents = @(
    @{Id="FireEssence"; Name="Fire Essence"; Element="fire"; State="Liquid"; Tags=@("flammable","volatile"); Color=@(255,100,50)},
    @{Id="CrystalPowder"; Name="Crystal Powder"; Element="crystal"; State="Solid"; Tags=@("catalyst","crystalline"); Color=@(200,200,255)},
    @{Id="SteamGas"; Name="Steam Gas"; Element="water"; State="Gas"; Tags=@("hot","pressurized"); Color=@(200,220,255)},
    @{Id="AirGas"; Name="Air Gas"; Element="air"; State="Gas"; Tags=@("oxidizer","light"); Color=@(240,240,255)},
    @{Id="Oxygen"; Name="Oxygen"; Element="air"; State="Gas"; Tags=@("oxidizer","reactive"); Color=@(200,200,255)},
    @{Id="Water"; Name="Water"; Element="water"; State="Liquid"; Tags=@("neutral","diluting"); Color=@(100,150,255)},
    @{Id="HealingHerb"; Name="Healing Herb"; Element="nature"; State="Solid"; Tags=@("organic","healing"); Color=@(100,255,100)},
    @{Id="PoisonGas"; Name="Poison Gas"; Element="poison"; State="Gas"; Tags=@("toxic","corrosive"); Color=@(150,255,150)},
    @{Id="IceCrystal"; Name="Ice Crystal"; Element="ice"; State="Solid"; Tags=@("cold","crystal"); Color=@(200,255,255)},
    @{Id="AcidGas"; Name="Acid Gas"; Element="poison"; State="Gas"; Tags=@("acidic","corrosive"); Color=@(100,255,100)}
)

# Generate additional reagent sprites
Write-Host "Generating Additional Reagent Assets..." -ForegroundColor Yellow
Write-Host ""

foreach ($reagent in $additionalReagents) {
    $reagentId = $reagent.Id
    $reagentName = $reagent.Name
    $element = $reagent.Element
    $state = $reagent.State
    $tags = $reagent.Tags -join ", "
    
    # Reagent item sprite
    # Validate $ModPath before Join-Path
$spritePath = Join-Path $ModPath "items\sprites\${reagentId}.png"
 if ([string]::IsNullOrWhiteSpace($spritePath)) {
        Write-Host "  [FAIL] spritePath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
 if ([string]::IsNullOrWhiteSpace($spritePath)) {
        Write-Host "  [FAIL] spritePath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
    if ($SkipExisting -and (Test-Path $spritePath)) {
        $skipped++
        Write-Host "  [SKIP] Reagent sprite already exists: $reagentId" -ForegroundColor Gray
    } else {
        try {
            $params = @{
                AssetType = "ItemSprite"
                AssetName = $reagentId
                Prompt = "A $element elemental reagent item sprite: $reagentName ($state state, $tags). Container or vial with $element colored contents, appropriate for $state material, 32x32 pixels"
                OllamaModel = $OllamaModel
                # Validate $ModPath before Join-Path
$tempOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                    Write-Host "  [FAIL] tempOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                    continue
                }
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                    Write-Host "  [FAIL] OutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                    continue
                }
            OutputDir = $tempOutputDir
            }
            if ($PlanningModel) { $params['PlanningModel'] = $PlanningModel }
            if ($VisualModel) { $params['VisualModel'] = $VisualModel }
            $params['UseCppBackend'] = $UseCppBackend
            
            & $assetGenerator @params | Out-Null
            $generated++
            Write-Host "  [OK] Generated reagent sprite: $reagentId" -ForegroundColor Green
        } catch {
            $failed++
            Write-Host "  [FAIL] Reagent sprite $reagentId : $_" -ForegroundColor Red
        }
    }
}

Write-Host ""

# Generate container items
Write-Host "Generating Container Items..." -ForegroundColor Yellow
Write-Host ""

$containerTypes = @(
    @{Id="container_solid"; Name="Solid Container"; Desc="Container for solid reagents, powder container, 32x32 pixels"},
    @{Id="container_liquid"; Name="Liquid Container"; Desc="Container for liquid reagents, vial or flask, 32x32 pixels"},
    @{Id="container_gas"; Name="Gas Container"; Desc="Container for gas reagents, pressurized canister, 32x32 pixels"},
    @{Id="container_empty"; Name="Empty Container"; Desc="Empty container ready to be filled, 32x32 pixels"},
    @{Id="container_filled"; Name="Filled Container"; Desc="Container filled with reagent, glowing contents, 32x32 pixels"}
)

foreach ($container in $containerTypes) {
    # Validate $ModPath before Join-Path
$spritePath = Join-Path $ModPath "items\sprites\${container.Id}.png"
 if ([string]::IsNullOrWhiteSpace($spritePath)) {
        Write-Host "  [FAIL] spritePath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
 if ([string]::IsNullOrWhiteSpace($spritePath)) {
        Write-Host "  [FAIL] spritePath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
    if ($SkipExisting -and (Test-Path $spritePath)) {
        $skipped++
        Write-Host "  [SKIP] Container sprite already exists: $($container.Id)" -ForegroundColor Gray
    } else {
        try {
            $params = @{
                AssetType = "ItemSprite"
                AssetName = $container.Id
                Prompt = "A container item sprite: $($container.Name) - $($container.Desc). Magitech style container"
                OllamaModel = $OllamaModel
                # Validate $ModPath before Join-Path
$tempOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                    Write-Host "  [FAIL] tempOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                    continue
                }
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                    Write-Host "  [FAIL] OutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                    continue
                }
            OutputDir = $tempOutputDir
            }
            if ($PlanningModel) { $params['PlanningModel'] = $PlanningModel }
            if ($VisualModel) { $params['VisualModel'] = $VisualModel }
            $params['UseCppBackend'] = $UseCppBackend
            
            & $assetGenerator @params | Out-Null
            $generated++
            Write-Host "  [OK] Generated container: $($container.Id)" -ForegroundColor Green
        } catch {
            $failed++
            Write-Host "  [FAIL] Container $($container.Id) : $_" -ForegroundColor Red
        }
    }
}

Write-Host ""

# Generate weapon variants
Write-Host "Generating Weapon Variants..." -ForegroundColor Yellow
Write-Host ""

$weaponVariants = @(
    @{Id="manaLauncher"; Name="Mana-Powered Launcher"; Desc="Mana-driven alchemical grenade launcher with spellpower scaling"},
    @{Id="manaLauncher_overheated"; Name="Overheated Mana Launcher"; Desc="Mana launcher with heat shield active, glowing red"},
    @{Id="magitechMageRifle"; Name="Magitech Mage Rifle"; Desc="Mage-style magitech rifle with spellpower focus, minimal ranged scaling"},
    @{Id="magitechMageRifle_charged"; Name="Charged Mage Rifle"; Desc="Mage rifle in charged state with magical energy"},
    @{Id="alchemicalSphereLauncher"; Name="Alchemical Sphere Launcher"; Desc="Launcher for bouncing alchemical sphere ammo"},
    @{Id="rebalancedLauncher"; Name="Rebalanced Magitech Launcher"; Desc="Rebalanced launcher with 3 rated material slots"}
)

foreach ($weapon in $weaponVariants) {
    # Validate $ModPath before Join-Path
$spritePath = Join-Path $ModPath "items\weapons\${weapon.Id}.png"
 if ([string]::IsNullOrWhiteSpace($spritePath)) {
        Write-Host "  [FAIL] spritePath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
 if ([string]::IsNullOrWhiteSpace($spritePath)) {
        Write-Host "  [FAIL] spritePath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
    if ($SkipExisting -and (Test-Path $spritePath)) {
        $skipped++
        Write-Host "  [SKIP] Weapon sprite already exists: $($weapon.Id)" -ForegroundColor Gray
    } else {
        try {
            $params = @{
                AssetType = "ItemSprite"
                AssetName = $weapon.Id
                Prompt = "A weapon sprite: $($weapon.Name) - $($weapon.Desc). Magitech style weapon, 64x64 pixels"
                OllamaModel = $OllamaModel
                # Validate $ModPath before Join-Path
$tempOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                    Write-Host "  [FAIL] tempOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                    continue
                }
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                    Write-Host "  [FAIL] OutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                    continue
                }
            OutputDir = $tempOutputDir
            }
            if ($PlanningModel) { $params['PlanningModel'] = $PlanningModel }
            if ($VisualModel) { $params['VisualModel'] = $VisualModel }
            $params['UseCppBackend'] = $UseCppBackend
            
            & $assetGenerator @params | Out-Null
            $generated++
            Write-Host "  [OK] Generated weapon: $($weapon.Id)" -ForegroundColor Green
        } catch {
            $failed++
            Write-Host "  [FAIL] Weapon $($weapon.Id) : $_" -ForegroundColor Red
        }
    }
}

Write-Host ""

# Generate sphere ammo sprites
Write-Host "Generating Alchemical Sphere Ammo..." -ForegroundColor Yellow
Write-Host ""

$sphereTypes = @(
    @{Id="alchemicalSphere"; Name="Alchemical Sphere"; Desc="Bouncing chemical orb with reagents, standard sphere"},
    @{Id="alchemicalSphere_fire"; Name="Fire Sphere"; Desc="Fire elemental sphere with flames"},
    @{Id="alchemicalSphere_ice"; Name="Ice Sphere"; Desc="Ice elemental sphere with frost"},
    @{Id="alchemicalSphere_toxic"; Name="Toxic Sphere"; Desc="Poison elemental sphere with toxic cloud"},
    @{Id="alchemicalSphere_explosive"; Name="Explosive Sphere"; Desc="Explosive sphere with volatile energy"},
    @{Id="alchemicalSphere_bouncing"; Name="Bouncing Sphere"; Desc="Sphere mid-bounce with energy trail"}
)

foreach ($sphere in $sphereTypes) {
    # Validate $ModPath before Join-Path
$spritePath = Join-Path $ModPath "projectiles\${sphere.Id}.png"
 if ([string]::IsNullOrWhiteSpace($spritePath)) {
        Write-Host "  [FAIL] spritePath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
 if ([string]::IsNullOrWhiteSpace($spritePath)) {
        Write-Host "  [FAIL] spritePath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
    if ($SkipExisting -and (Test-Path $spritePath)) {
        $skipped++
        Write-Host "  [SKIP] Sphere sprite already exists: $($sphere.Id)" -ForegroundColor Gray
    } else {
        try {
            $params = @{
                AssetType = "Projectile"
                AssetName = $sphere.Id
                Prompt = "A projectile sprite: $($sphere.Name) - $($sphere.Desc). Round bouncing sphere, 32x32 pixels"
                OllamaModel = $OllamaModel
                # Validate $ModPath before Join-Path
$tempOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                    Write-Host "  [FAIL] tempOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                    continue
                }
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                    Write-Host "  [FAIL] OutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                    continue
                }
            OutputDir = $tempOutputDir
            }
            if ($PlanningModel) { $params['PlanningModel'] = $PlanningModel }
            if ($VisualModel) { $params['VisualModel'] = $VisualModel }
            $params['UseCppBackend'] = $UseCppBackend
            
            & $assetGenerator @params | Out-Null
            $generated++
            Write-Host "  [OK] Generated sphere: $($sphere.Id)" -ForegroundColor Green
        } catch {
            $failed++
            Write-Host "  [FAIL] Sphere $($sphere.Id) : $_" -ForegroundColor Red
        }
    }
}

Write-Host ""

# Generate crafting station assets
Write-Host "Generating Crafting Station Assets..." -ForegroundColor Yellow
Write-Host ""

$craftingStationAssets = @(
    @{Id="alchemicalCraftingStation"; Name="Alchemical Crafting Station"; Desc="World-placed crafting table for mixing reagents, magitech station, 64x64 pixels"},
    @{Id="craftingStation_slot1"; Name="Crafting Slot 1"; Desc="First reagent slot on crafting station, 48x48 pixels"},
    @{Id="craftingStation_slot2"; Name="Crafting Slot 2"; Desc="Second reagent slot on crafting station, 48x48 pixels"},
    @{Id="craftingStation_slot3"; Name="Crafting Slot 3"; Desc="Third reagent slot on crafting station, 48x48 pixels"},
    @{Id="craftingStation_output"; Name="Output Slot"; Desc="Output slot for crafted items, 48x48 pixels"},
    @{Id="craftingStation_heatSource"; Name="Heat Source"; Desc="Heat source indicator for temperature control, glowing element"},
    @{Id="craftingStation_tempGauge"; Name="Temperature Gauge"; Desc="Temperature gauge for crafting station, thermometer style"},
    @{Id="craftingStation_craftButton"; Name="Craft Button"; Desc="Craft button for initiating crafting, UI button style"}
)

foreach ($asset in $craftingStationAssets) {
    # Validate $ModPath before Join-Path
$spritePath = Join-Path $ModPath "objects\crafting\${asset.Id}.png"
 if ([string]::IsNullOrWhiteSpace($spritePath)) {
        Write-Host "  [FAIL] spritePath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
 if ([string]::IsNullOrWhiteSpace($spritePath)) {
        Write-Host "  [FAIL] spritePath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
    if ($SkipExisting -and (Test-Path $spritePath)) {
        $skipped++
        Write-Host "  [SKIP] Crafting asset already exists: $($asset.Id)" -ForegroundColor Gray
    } else {
        try {
            $assetType = if ($asset.Id -match "slot|button|gauge") { "Icon" } else { "Sprite" }
            $params = @{
                AssetType = $assetType
                AssetName = $asset.Id
                Prompt = "A $assetType asset: $($asset.Name) - $($asset.Desc). Clean magitech style"
                OllamaModel = $OllamaModel
                # Validate $ModPath before Join-Path
$tempOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                    Write-Host "  [FAIL] tempOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                    continue
                }
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                    Write-Host "  [FAIL] OutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                    continue
                }
            OutputDir = $tempOutputDir
            }
            if ($PlanningModel) { $params['PlanningModel'] = $PlanningModel }
            if ($VisualModel) { $params['VisualModel'] = $VisualModel }
            $params['UseCppBackend'] = $UseCppBackend
            
            & $assetGenerator @params | Out-Null
            $generated++
            Write-Host "  [OK] Generated crafting asset: $($asset.Id)" -ForegroundColor Green
        } catch {
            $failed++
            Write-Host "  [FAIL] Crafting asset $($asset.Id) : $_" -ForegroundColor Red
        }
    }
}

Write-Host ""

# Generate UI elements for launcher systems
Write-Host "Generating Launcher UI Elements..." -ForegroundColor Yellow
Write-Host ""

$launcherUI = @(
    @{Id="launcher_slot1"; Name="Launcher Slot 1"; Desc="First reagent slot on launcher UI, 48x48 pixels"},
    @{Id="launcher_slot2"; Name="Launcher Slot 2"; Desc="Second reagent slot on launcher UI, 48x48 pixels"},
    @{Id="launcher_slot3"; Name="Launcher Slot 3"; Desc="Third reagent slot on launcher UI, 48x48 pixels"},
    @{Id="launcher_tempIndicator"; Name="Temperature Indicator"; Desc="Temperature indicator for launcher core temp, gauge style"},
    @{Id="launcher_heatShieldActive"; Name="Heat Shield Active"; Desc="Indicator when heat shield is active, glowing shield icon"},
    @{Id="launcher_manaCost"; Name="Mana Cost Display"; Desc="Mana cost display showing current shot cost, UI text element"},
    @{Id="launcher_chargeBar"; Name="Charge Bar"; Desc="Charge bar showing hold time progress, horizontal bar"},
    @{Id="launcher_reagentPreview"; Name="Reagent Preview"; Desc="Preview showing predicted reaction from loaded reagents, icon"},
    @{Id="launcher_stateIndicator"; Name="State Indicator"; Desc="Indicator for compatible material states (solid/liquid/gas), icon"},
    @{Id="launcher_validationWarning"; Name="Validation Warning"; Desc="Warning icon for invalid reagent combinations, warning symbol"}
)

foreach ($ui in $launcherUI) {
    # Validate $ModPath before Join-Path
$iconPath = Join-Path $ModPath "interface\icons\${ui.Id}.png"
 if ([string]::IsNullOrWhiteSpace($iconPath)) {
        Write-Host "  [FAIL] iconPath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
 if ([string]::IsNullOrWhiteSpace($iconPath)) {
        Write-Host "  [FAIL] iconPath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
    if ($SkipExisting -and (Test-Path $iconPath)) {
        $skipped++
        Write-Host "  [SKIP] UI element already exists: $($ui.Id)" -ForegroundColor Gray
    } else {
        try {
            $params = @{
                AssetType = "Icon"
                AssetName = $ui.Id
                Prompt = "A UI element: $($ui.Name) - $($ui.Desc). Clean interface style, appropriate size"
                OllamaModel = $OllamaModel
                # Validate $ModPath before Join-Path
$tempOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                    Write-Host "  [FAIL] tempOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                    continue
                }
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                    Write-Host "  [FAIL] OutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                    continue
                }
            OutputDir = $tempOutputDir
            }
            if ($PlanningModel) { $params['PlanningModel'] = $PlanningModel }
            if ($VisualModel) { $params['VisualModel'] = $VisualModel }
            $params['UseCppBackend'] = $UseCppBackend
            
            & $assetGenerator @params | Out-Null
            $generated++
            Write-Host "  [OK] Generated UI element: $($ui.Id)" -ForegroundColor Green
        } catch {
            $failed++
            Write-Host "  [FAIL] UI element $($ui.Id) : $_" -ForegroundColor Red
        }
    }
}

Write-Host ""

# Generate reaction effect particles
Write-Host "Generating Reaction Effect Particles..." -ForegroundColor Yellow
Write-Host ""

$reactionParticles = @(
    @{Id="reaction_fireOilExplosion"; Name="Fire-Oil Explosion"; Type="Explosion"; Desc="Explosive reaction from fire essence, oil, and oxygen"},
    @{Id="reaction_toxicCloud"; Name="Toxic Cloud"; Type="Smoke"; Desc="Toxic cloud from poison gas, water, and catalyst reaction"},
    @{Id="reaction_freezeCloud"; Name="Freeze Cloud"; Type="Ice"; Desc="Freezing cloud from ice crystal, water, and air gas"},
    @{Id="reaction_acidPool"; Name="Acid Pool"; Type="Poison"; Desc="Corrosive pool from acid-base neutralization"},
    @{Id="reaction_healingAura"; Name="Healing Aura"; Type="Magic"; Desc="Healing effect from healing herb, water, and crystal powder"},
    @{Id="reaction_steamBurst"; Name="Steam Burst"; Type="Smoke"; Desc="Steam explosion from hot reagents and water"},
    @{Id="reaction_crystalGrowth"; Name="Crystal Growth"; Type="Crystal"; Desc="Crystal formation reaction, growing crystals"},
    @{Id="reaction_chainReaction"; Name="Chain Reaction"; Type="Electric"; Desc="Chained alchemical reaction with multiple effects"}
)

foreach ($particle in $reactionParticles) {
    # Validate $ModPath before Join-Path
$particlePath = Join-Path $ModPath "particles\magitech\${particle.Id}.particle"
 if ([string]::IsNullOrWhiteSpace($particlePath)) {
        Write-Host "  [FAIL] particlePath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
 if ([string]::IsNullOrWhiteSpace($particlePath)) {
        Write-Host "  [FAIL] particlePath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
    if ($SkipExisting -and (Test-Path $particlePath)) {
        $skipped++
        Write-Host "  [SKIP] Particle already exists: $($particle.Id)" -ForegroundColor Gray
    } else {
        try {
            $params = @{
                AssetType = "Particle"
                AssetName = $particle.Id
                Prompt = "A particle effect: $($particle.Name) - $($particle.Desc). $($particle.Type) type reaction effect"
                OllamaModel = $OllamaModel
                # Validate $ModPath before Join-Path
$tempOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                    Write-Host "  [FAIL] tempOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                    continue
                }
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                    Write-Host "  [FAIL] OutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                    continue
                }
            OutputDir = $tempOutputDir
            }
            if ($PlanningModel) { $params['PlanningModel'] = $PlanningModel }
            if ($VisualModel) { $params['VisualModel'] = $VisualModel }
            $params['UseCppBackend'] = $UseCppBackend
            
            & $assetGenerator @params | Out-Null
            $generated++
            Write-Host "  [OK] Generated particle: $($particle.Id)" -ForegroundColor Green
        } catch {
            $failed++
            Write-Host "  [FAIL] Particle $($particle.Id) : $_" -ForegroundColor Red
        }
    }
}

Write-Host ""

# Generate sound effects
Write-Host "Generating Sound Effects..." -ForegroundColor Yellow
Write-Host ""

$sounds = @(
    @{Id="launcher_manaCharge"; Type="Magic"; Desc="Mana-powered launcher charging sound, building energy"},
    @{Id="launcher_manaFire"; Type="Impact"; Desc="Mana launcher firing sound, magical blast"},
    @{Id="launcher_overheat"; Type="Mechanical"; Desc="Launcher overheating warning sound, mechanical whir"},
    @{Id="launcher_heatShieldActivate"; Type="Magic"; Desc="Heat shield activation sound, protective barrier"},
    @{Id="mageRifle_charge"; Type="Magic"; Desc="Mage rifle charging sound, spellpower building"},
    @{Id="mageRifle_fire"; Type="Electric"; Desc="Mage rifle firing sound, magical projectile"},
    @{Id="sphere_bounce"; Type="Impact"; Desc="Alchemical sphere bounce sound, bouncy impact"},
    @{Id="sphere_explode"; Type="Explosion"; Desc="Alchemical sphere explosion sound, chemical reaction"},
    @{Id="container_load"; Type="Mechanical"; Desc="Container loading sound, mechanical click"},
    @{Id="container_unload"; Type="Mechanical"; Desc="Container unloading sound, mechanical release"},
    @{Id="crafting_station_activate"; Type="Mechanical"; Desc="Crafting station activation sound, machinery"},
    @{Id="crafting_mix"; Type="Magic"; Desc="Reagent mixing sound, alchemical reaction"},
    @{Id="crafting_success"; Type="Magic"; Desc="Successful craft sound, magical chime"},
    @{Id="crafting_fail"; Type="Mechanical"; Desc="Failed craft sound, mechanical error"},
    @{Id="reagent_validate"; Type="Magic"; Desc="Reagent validation sound, compatibility check"},
    @{Id="reagent_reject"; Type="Mechanical"; Desc="Reagent rejection sound, invalid combination"}
)

foreach ($sound in $sounds) {
    # Validate $ModPath before Join-Path
$soundPath = Join-Path $ModPath "sfx\${sound.Id}.ogg"
 if ([string]::IsNullOrWhiteSpace($soundPath)) {
        Write-Host "  [FAIL] soundPath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
 if ([string]::IsNullOrWhiteSpace($soundPath)) {
        Write-Host "  [FAIL] soundPath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
    if ($SkipExisting -and (Test-Path $soundPath)) {
        $skipped++
        Write-Host "  [SKIP] Sound already exists: $($sound.Id)" -ForegroundColor Gray
    } else {
        try {
            $params = @{
                AssetType = "Sound"
                AssetName = $sound.Id
                Prompt = "A sound effect: $($sound.Desc). $($sound.Type) type sound"
                OllamaModel = $OllamaModel
                # Validate $ModPath before Join-Path
$tempOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                    Write-Host "  [FAIL] tempOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                    continue
                }
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                    Write-Host "  [FAIL] OutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                    continue
                }
            OutputDir = $tempOutputDir
            }
            if ($PlanningModel) { $params['PlanningModel'] = $PlanningModel }
            if ($VisualModel) { $params['VisualModel'] = $VisualModel }
            $params['UseCppBackend'] = $UseCppBackend
            
            # Add sound-specific parameters
            $soundParams = @{
                SoundType = $sound.Type
                Format = "ogg"
            }
            $params['Parameters'] = $soundParams
            
            & $assetGenerator @params | Out-Null
            $generated++
            Write-Host "  [OK] Generated sound: $($sound.Id)" -ForegroundColor Green
        } catch {
            $failed++
            Write-Host "  [FAIL] Sound $($sound.Id) : $_" -ForegroundColor Red
        }
    }
}

Write-Host ""

# Generate status effect icons
Write-Host "Generating Status Effect Icons..." -ForegroundColor Yellow
Write-Host ""

$statusEffects = @(
    @{Id="heatShieldActive"; Name="Heat Shield Active"; Desc="Heat shield active status, protective barrier icon"},
    @{Id="overheatedWeapon"; Name="Overheated Weapon"; Desc="Overheated weapon status, red warning icon"},
    @{Id="reagentSynergy"; Name="Reagent Synergy"; Desc="Positive reagent synergy bonus status"},
    @{Id="reagentOpposition"; Name="Reagent Opposition"; Desc="Negative reagent opposition penalty status"},
    @{Id="temperatureWarning"; Name="Temperature Warning"; Desc="Temperature warning status, heat indicator"},
    @{Id="containerFull"; Name="Container Full"; Desc="Container full status, filled indicator"},
    @{Id="craftingReady"; Name="Crafting Ready"; Desc="Crafting station ready status, ready indicator"}
)

foreach ($status in $statusEffects) {
    # Validate $ModPath before Join-Path
$iconPath = Join-Path $ModPath "status\icons\${status.Id}.png"
 if ([string]::IsNullOrWhiteSpace($iconPath)) {
        Write-Host "  [FAIL] iconPath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
 if ([string]::IsNullOrWhiteSpace($iconPath)) {
        Write-Host "  [FAIL] iconPath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
    if ($SkipExisting -and (Test-Path $iconPath)) {
        $skipped++
        Write-Host "  [SKIP] Status icon already exists: $($status.Id)" -ForegroundColor Gray
    } else {
        try {
            $params = @{
                AssetType = "Icon"
                AssetName = "${status.Id}_status"
                Prompt = "A status effect icon: $($status.Name) - $($status.Desc). Status effect style, 32x32 pixels"
                OllamaModel = $OllamaModel
                # Validate $ModPath before Join-Path
$tempOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                    Write-Host "  [FAIL] tempOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                    continue
                }
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                    Write-Host "  [FAIL] OutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                    continue
                }
            OutputDir = $tempOutputDir
            }
            if ($PlanningModel) { $params['PlanningModel'] = $PlanningModel }
            if ($VisualModel) { $params['VisualModel'] = $VisualModel }
            $params['UseCppBackend'] = $UseCppBackend
            
            & $assetGenerator @params | Out-Null
            $generated++
            Write-Host "  [OK] Generated status icon: $($status.Id)" -ForegroundColor Green
        } catch {
            $failed++
            Write-Host "  [FAIL] Status icon $($status.Id) : $_" -ForegroundColor Red
        }
    }
}

Write-Host ""

# Generate recipe icons
Write-Host "Generating Recipe Icons..." -ForegroundColor Yellow
Write-Host ""

$recipeIcons = @(
    @{Id="recipe_fireGrenade"; Name="Fire Grenade Recipe"; Desc="Recipe icon for fire grenade, fire elemental"},
    @{Id="recipe_healingSphere"; Name="Healing Sphere Recipe"; Desc="Recipe icon for healing sphere, healing effect"},
    @{Id="recipe_toxicGrenade"; Name="Toxic Grenade Recipe"; Desc="Recipe icon for toxic grenade, poison elemental"},
    @{Id="recipe_explosiveGrenade"; Name="Explosive Grenade Recipe"; Desc="Recipe icon for explosive grenade, explosive effect"},
    @{Id="recipe_custom"; Name="Custom Recipe"; Desc="Generic custom recipe icon, alchemical symbol"}
)

foreach ($recipe in $recipeIcons) {
    # Validate $ModPath before Join-Path
$iconPath = Join-Path $ModPath "interface\icons\${recipe.Id}.png"
 if ([string]::IsNullOrWhiteSpace($iconPath)) {
        Write-Host "  [FAIL] iconPath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
 if ([string]::IsNullOrWhiteSpace($iconPath)) {
        Write-Host "  [FAIL] iconPath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
    if ($SkipExisting -and (Test-Path $iconPath)) {
        $skipped++
        Write-Host "  [SKIP] Recipe icon already exists: $($recipe.Id)" -ForegroundColor Gray
    } else {
        try {
            $params = @{
                AssetType = "Icon"
                AssetName = $recipe.Id
                Prompt = "A recipe icon: $($recipe.Name) - $($recipe.Desc). Alchemical recipe symbol, 32x32 pixels"
                OllamaModel = $OllamaModel
                # Validate $ModPath before Join-Path
$tempOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                    Write-Host "  [FAIL] tempOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                    continue
                }
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                    Write-Host "  [FAIL] OutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                    continue
                }
            OutputDir = $tempOutputDir
            }
            if ($PlanningModel) { $params['PlanningModel'] = $PlanningModel }
            if ($VisualModel) { $params['VisualModel'] = $VisualModel }
            $params['UseCppBackend'] = $UseCppBackend
            
            & $assetGenerator @params | Out-Null
            $generated++
            Write-Host "  [OK] Generated recipe icon: $($recipe.Id)" -ForegroundColor Green
        } catch {
            $failed++
            Write-Host "  [FAIL] Recipe icon $($recipe.Id) : $_" -ForegroundColor Red
        }
    }
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Generation Complete" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Generated: $generated assets" -ForegroundColor Green
Write-Host "Skipped: $skipped assets (already exist)" -ForegroundColor Gray
Write-Host "Failed: $failed assets" -ForegroundColor $(if ($failed -gt 0) { "Red" } else { "Green" })
Write-Host ""
