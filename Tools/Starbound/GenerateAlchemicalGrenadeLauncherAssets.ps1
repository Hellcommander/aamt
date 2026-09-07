#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate assets for the Enhanced Alchemical Grenade Launcher system.
    
.DESCRIPTION
    Generates all visual and audio assets needed for the Alchemical Grenade Launcher:
    - Reagent sprites and icons
    - Grenade launcher weapon sprite
    - Grenade projectile sprites

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}
    - Reaction effect particles
    - UI elements (slots, gauges, indicators)
    - Sound effects
    - Status effect icons
    
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
Write-Host "  Alchemical Grenade Launcher Asset Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$generated = 0
$failed = 0
$skipped = 0

# Reagent definitions with properties
$reagents = @(
    @{Id="SulfurDust"; Name="Sulfur Dust"; Element="fire"; Tags=@("flammable","oxidizer"); Color=@(255,200,50)},
    @{Id="Oil"; Name="Oil"; Element="fire"; Tags=@("flammable","viscous"); Color=@(50,50,50)},
    @{Id="Nitro"; Name="Nitroglycerin"; Element="explosive"; Tags=@("volatile","explosive"); Color=@(200,200,255)},
    @{Id="Fertilizer"; Name="Fertilizer"; Element="earth"; Tags=@("organic","catalyst"); Color=@(100,200,100)},
    @{Id="Acid"; Name="Acid"; Element="poison"; Tags=@("acidic","corrosive"); Color=@(100,255,100)},
    @{Id="Base"; Name="Base"; Element="poison"; Tags=@("basic","neutralizer"); Color=@(255,100,100)},
    @{Id="IceCrystal"; Name="Ice Crystal"; Element="ice"; Tags=@("cold","crystal"); Color=@(200,255,255)},
    @{Id="MagmaCore"; Name="Magma Core"; Element="fire"; Tags=@("hot","molten"); Color=@(255,100,50)},
    @{Id="ToxicSpore"; Name="Toxic Spore"; Element="poison"; Tags=@("organic","toxic"); Color=@(150,255,150)},
    @{Id="LightningEssence"; Name="Lightning Essence"; Element="electric"; Tags=@("volatile","electric"); Color=@(255,255,100)}
)

# Generate reagent sprites and icons
Write-Host "Generating Reagent Assets..." -ForegroundColor Yellow
Write-Host ""

foreach ($reagent in $reagents) {
    $reagentId = $reagent.Id
    $reagentName = $reagent.Name
    $element = $reagent.Element
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
            # Validate $ModPath before Join-Path
            $tempOutputDir = Join-Path $ModPath "assets"
            if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                Write-Host "  [FAIL] tempOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                continue
            }
            
            $params = @{
                AssetType = "ItemSprite"
                AssetName = $reagentId
                Prompt = "A $element elemental reagent item sprite: $reagentName ($tags). Small container or vial with $element colored contents, 32x32 pixels"
                OllamaModel = $OllamaModel
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
    
    # Reagent icon for UI
    # Validate $ModPath before Join-Path
$iconPath = Join-Path $ModPath "interface\icons\${reagentId}_icon.png"
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
    } else {
        try {
            # Validate $ModPath before Join-Path
            $tempOutputDir = Join-Path $ModPath "assets"
            if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                Write-Host "  [FAIL] tempOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                continue
            }
            
            $params = @{
                AssetType = "Icon"
                AssetName = "${reagentId}_icon"
                Prompt = "An icon for reagent: $reagentName ($element elemental, $tags). Small circular icon, 32x32 pixels"
                OllamaModel = $OllamaModel
                OutputDir = $tempOutputDir
            }
            if ($PlanningModel) { $params['PlanningModel'] = $PlanningModel }
            if ($VisualModel) { $params['VisualModel'] = $VisualModel }
            $params['UseCppBackend'] = $UseCppBackend
            
            & $assetGenerator @params | Out-Null
            $generated++
            Write-Host "  [OK] Generated reagent icon: $reagentId" -ForegroundColor Green
        } catch {
            $failed++
            Write-Host "  [FAIL] Reagent icon $reagentId : $_" -ForegroundColor Red
        }
    }
}

Write-Host ""

# Generate grenade launcher weapon sprite
Write-Host "Generating Grenade Launcher Weapon..." -ForegroundColor Yellow
Write-Host ""

$weaponSprites = @(
    @{Id="alchemicalGrenadeLauncher"; Name="Alchemical Grenade Launcher"; Desc="A magitech grenade launcher with temperature gauge and reagent loading chambers"},
    @{Id="alchemicalGrenadeLauncher_charged"; Name="Charged Grenade Launcher"; Desc="Grenade launcher in charged state with glowing energy"},
    @{Id="alchemicalGrenadeLauncher_overheated"; Name="Overheated Grenade Launcher"; Desc="Grenade launcher overheated with heat shield active, glowing red"}
)

foreach ($weapon in $weaponSprites) {
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
            # Validate $ModPath before Join-Path
            $tempOutputDir = Join-Path $ModPath "assets"
            if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                Write-Host "  [FAIL] tempOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                continue
            }
            
            $params = @{
                AssetType = "ItemSprite"
                AssetName = $weapon.Id
                Prompt = "A weapon sprite: $($weapon.Name) - $($weapon.Desc). Magitech style, 64x64 pixels"
                OllamaModel = $OllamaModel
                OutputDir = $tempOutputDir
            }
            if ($PlanningModel) { $params['PlanningModel'] = $PlanningModel }
            if ($VisualModel) { $params['VisualModel'] = $VisualModel }
            $params['UseCppBackend'] = $UseCppBackend
            
            & $assetGenerator @params | Out-Null
            $generated++
            Write-Host "  [OK] Generated weapon sprite: $($weapon.Id)" -ForegroundColor Green
        } catch {
            $failed++
            Write-Host "  [FAIL] Weapon sprite $($weapon.Id) : $_" -ForegroundColor Red
        }
    }
}

Write-Host ""

# Generate grenade projectile sprites
Write-Host "Generating Grenade Projectiles..." -ForegroundColor Yellow
Write-Host ""

$grenadeTypes = @(
    @{Id="alchemicalGrenade"; Name="Alchemical Grenade"; Desc="Standard alchemical grenade projectile"},
    @{Id="alchemicalGrenade_fire"; Name="Fire Grenade"; Desc="Fire elemental grenade with flames"},
    @{Id="alchemicalGrenade_ice"; Name="Ice Grenade"; Desc="Ice elemental grenade with frost"},
    @{Id="alchemicalGrenade_toxic"; Name="Toxic Grenade"; Desc="Poison elemental grenade with toxic cloud"},
    @{Id="alchemicalGrenade_explosive"; Name="Explosive Grenade"; Desc="Explosive grenade with volatile energy"}
)

foreach ($grenade in $grenadeTypes) {
    # Validate $ModPath before Join-Path
$spritePath = Join-Path $ModPath "projectiles\${grenade.Id}.png"
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
        Write-Host "  [SKIP] Grenade sprite already exists: $($grenade.Id)" -ForegroundColor Gray
    } else {
        try {
            # Validate $ModPath before Join-Path
            $tempOutputDir = Join-Path $ModPath "assets"
            if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                Write-Host "  [FAIL] tempOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                continue
            }
            
            $params = @{
                AssetType = "Projectile"
                AssetName = $grenade.Id
                Prompt = "A projectile sprite: $($grenade.Name) - $($grenade.Desc). Round grenade shape, 32x32 pixels"
                OllamaModel = $OllamaModel
                OutputDir = $tempOutputDir
            }
            if ($PlanningModel) { $params['PlanningModel'] = $PlanningModel }
            if ($VisualModel) { $params['VisualModel'] = $VisualModel }
            $params['UseCppBackend'] = $UseCppBackend
            
            & $assetGenerator @params | Out-Null
            $generated++
            Write-Host "  [OK] Generated grenade sprite: $($grenade.Id)" -ForegroundColor Green
        } catch {
            $failed++
            Write-Host "  [FAIL] Grenade sprite $($grenade.Id) : $_" -ForegroundColor Red
        }
    }
}

Write-Host ""

# Generate reaction effect particles
Write-Host "Generating Reaction Effect Particles..." -ForegroundColor Yellow
Write-Host ""

$reactionParticles = @(
    @{Id="alchemicalExplosion"; Name="Alchemical Explosion"; Type="Explosion"; Desc="Explosive reaction with multi-colored energy"},
    @{Id="alchemicalCloud"; Name="Alchemical Cloud"; Type="Smoke"; Desc="Dispersing cloud of alchemical reaction"},
    @{Id="alchemicalFireCloud"; Name="Fire Cloud"; Type="Fire"; Desc="Burning cloud from fire reaction"},
    @{Id="alchemicalToxicCloud"; Name="Toxic Cloud"; Type="Poison"; Desc="Toxic cloud from acid-base reaction"},
    @{Id="alchemicalChainReaction"; Name="Chain Reaction"; Type="Electric"; Desc="Chained reaction with lightning effects"},
    @{Id="alchemicalCorrosivePool"; Name="Corrosive Pool"; Type="Poison"; Desc="Acid-base neutralization pool"},
    @{Id="alchemicalIceBurst"; Name="Ice Burst"; Type="Ice"; Desc="Ice crystal explosion from cold reaction"}
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
            # Validate $ModPath before Join-Path
            $tempOutputDir = Join-Path $ModPath "assets"
            if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                Write-Host "  [FAIL] tempOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                continue
            }
            
            $params = @{
                AssetType = "Particle"
                AssetName = $particle.Id
                Prompt = "A particle effect: $($particle.Name) - $($particle.Desc). $($particle.Type) type reaction effect"
                OllamaModel = $OllamaModel
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

# Generate UI elements
Write-Host "Generating UI Elements..." -ForegroundColor Yellow
Write-Host ""

$uiElements = @(
    @{Id="reagentSlot"; Name="Reagent Slot"; Desc="Empty reagent slot frame for crafting UI, 48x48 pixels"},
    @{Id="reagentSlot_filled"; Name="Filled Reagent Slot"; Desc="Reagent slot with reagent icon, 48x48 pixels"},
    @{Id="heatGauge"; Name="Heat Gauge"; Desc="Temperature gauge bar for launcher heat, horizontal bar"},
    @{Id="heatGauge_overheated"; Name="Overheated Gauge"; Desc="Red overheated heat gauge, critical temperature"},
    @{Id="shieldIndicator"; Name="Shield Indicator"; Desc="Mana shield active indicator, glowing ring icon"},
    @{Id="reactionPreview"; Name="Reaction Preview"; Desc="Preview icon showing predicted reaction outcome"},
    @{Id="environmentWarning"; Name="Environment Warning"; Desc="Warning icon for environmental conditions (low oxygen, etc.)"}
)

foreach ($ui in $uiElements) {
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
            # Validate $ModPath before Join-Path
            $tempOutputDir = Join-Path $ModPath "assets"
            if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                Write-Host "  [FAIL] tempOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                continue
            }
            
            $params = @{
                AssetType = "Icon"
                AssetName = $ui.Id
                Prompt = "A UI element: $($ui.Name) - $($ui.Desc). Clean interface style, appropriate size"
                OllamaModel = $OllamaModel
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

# Generate status effect icons
Write-Host "Generating Status Effect Icons..." -ForegroundColor Yellow
Write-Host ""

$statusEffects = @(
    @{Id="heatShield"; Name="Heat Shield"; Desc="Mana shield active status, protective barrier icon"},
    @{Id="overheated"; Name="Overheated"; Desc="Overheated status effect, red warning icon"},
    @{Id="reagentSynergy"; Name="Reagent Synergy"; Desc="Positive synergy bonus status"},
    @{Id="reagentOpposition"; Name="Reagent Opposition"; Desc="Negative opposition penalty status"}
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
            # Validate $ModPath before Join-Path
            $tempOutputDir = Join-Path $ModPath "assets"
            if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                Write-Host "  [FAIL] tempOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                continue
            }
            
            $params = @{
                AssetType = "Icon"
                AssetName = "${status.Id}_status"
                Prompt = "A status effect icon: $($status.Name) - $($status.Desc). Status effect style, 32x32 pixels"
                OllamaModel = $OllamaModel
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

# Generate sound effects
Write-Host "Generating Sound Effects..." -ForegroundColor Yellow
Write-Host ""

$sounds = @(
    @{Id="grenadeLauncher_charge"; Type="Charge"; Desc="Grenade launcher charging sound, building energy"},
    @{Id="grenadeLauncher_fire"; Type="Impact"; Desc="Grenade launcher firing sound, launch whoosh"},
    @{Id="grenadeLauncher_overheat"; Type="Mechanical"; Desc="Overheating warning sound, mechanical whir"},
    @{Id="grenadeLauncher_shieldActivate"; Type="Magic"; Desc="Heat shield activation sound, magical barrier"},
    @{Id="grenade_impact"; Type="Impact"; Desc="Grenade impact sound, explosive impact"},
    @{Id="reaction_explosion"; Type="Explosion"; Desc="Alchemical reaction explosion sound"},
    @{Id="reaction_cloud"; Type="Ambient"; Desc="Reaction cloud dispersing sound, ambient whoosh"},
    @{Id="reaction_chain"; Type="Electric"; Desc="Chain reaction sound, electric crackling"},
    @{Id="reagent_load"; Type="Mechanical"; Desc="Reagent loading sound, mechanical click"},
    @{Id="reagent_synergy"; Type="Magic"; Desc="Reagent synergy activation sound, magical chime"}
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
            # Validate $ModPath before Join-Path
            $tempOutputDir = Join-Path $ModPath "assets"
            if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                Write-Host "  [FAIL] tempOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                continue
            }
            
            $params = @{
                AssetType = "Sound"
                AssetName = $sound.Id
                Prompt = "A sound effect: $($sound.Desc). $($sound.Type) type sound"
                OllamaModel = $OllamaModel
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
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Generation Complete" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Generated: $generated assets" -ForegroundColor Green
Write-Host "Skipped: $skipped assets (already exist)" -ForegroundColor Gray
Write-Host "Failed: $failed assets" -ForegroundColor $(if ($failed -gt 0) { "Red" } else { "Green" })
Write-Host ""
