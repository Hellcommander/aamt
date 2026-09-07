# GenerateDynamicPotionAmmoAssets.ps1
# Generates assets for the Dynamic Potion Ammo system
# Includes: reagent icons, container sprites, ammo sprites, reaction VFX, crafting station sprites

param(
    [bool]$UseCppBackend = $true,
    [switch]$SkipExisting
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
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$modPath = "F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery"

# Load reagent definitions
$reagentConfig = Get-Content "$modPath\config\enhancedAlchemicalGrenadeLauncher.json" | ConvertFrom-Json
$reagents = $reagentConfig.reagents.PSObject.Properties | ForEach-Object { $_.Name }

Write-Host "=== Generating Dynamic Potion Ammo Assets ===" -ForegroundColor Cyan
Write-Host "Reagents found: $($reagents.Count)" -ForegroundColor Yellow

# 1. Generate Reagent Icons (64x64)
Write-Host "`n[1/5] Generating Reagent Icons..." -ForegroundColor Green
foreach ($reagentId in $reagents) {
    $reagent = $reagentConfig.reagents.$reagentId
    $iconPath = "$modPath\interface\icons\reagents\$reagentId.png"
    
    if ($SkipExisting -and (Test-Path $iconPath)) {
        Write-Host "  Skipping existing: $reagentId" -ForegroundColor Gray
        continue
    }
    
    $params = @{
        AssetType = "Icon"
        Name = "reagent_$reagentId"
        Size = 64
        Shape = "Circle"
        UseCppBackend = $UseCppBackend
        Parameters = @{
            Color = if ($reagent.color) { $reagent.color } else { @(100, 150, 255) }
            Glow = $true
            GlowIntensity = 0.6
        }
    }
    
    & "$scriptPath\StarboundOllamaAssetGenerator.ps1" @params
}

# 2. Generate Container Sprites
Write-Host "`n[2/5] Generating Container Sprites..." -ForegroundColor Green
$containerTypes = @("glassVial", "metalFlask", "powderJar", "gasCanister", "crystalPhial", "herbSatchel")
foreach ($containerType in $containerTypes) {
    $spritePath = "$modPath\sprites\containers\$containerType.png"
    
    if ($SkipExisting -and (Test-Path $spritePath)) {
        Write-Host "  Skipping existing: $containerType" -ForegroundColor Gray
        continue
    }
    
    $params = @{
        AssetType = "Sprite"
        Name = "container_$containerType"
        Width = 32
        Height = 32
        UseCppBackend = $UseCppBackend
        Parameters = @{
            Style = "container"
            ContainerType = $containerType
        }
    }
    
    & "$scriptPath\StarboundOllamaAssetGenerator.ps1" @params
}

# 3. Generate Ammo Sprites (Grenades, Spheres)
Write-Host "`n[3/5] Generating Ammo Sprites..." -ForegroundColor Green
$ammoTypes = @(
    @{Type="potionGrenade"; Size=24; Shape="Grenade"},
    @{Type="alchemicalSphere"; Size=32; Shape="Sphere"},
    @{Type="containerShell"; Size=28; Shape="Shell"}
)

foreach ($ammo in $ammoTypes) {
    $spritePath = "$modPath\sprites\ammo\$($ammo.Type).png"
    
    if ($SkipExisting -and (Test-Path $spritePath)) {
        Write-Host "  Skipping existing: $($ammo.Type)" -ForegroundColor Gray
        continue
    }
    
    $params = @{
        AssetType = "Sprite"
        Name = "ammo_$($ammo.Type)"
        Width = $ammo.Size
        Height = $ammo.Size
        UseCppBackend = $UseCppBackend
        Parameters = @{
            Style = "ammo"
            AmmoType = $ammo.Type
            Shape = $ammo.Shape
        }
    }
    
    & "$scriptPath\StarboundOllamaAssetGenerator.ps1" @params
}

# 4. Generate Reaction VFX Particles
Write-Host "`n[4/5] Generating Reaction VFX Particles..." -ForegroundColor Green
$reactionTypes = @(
    "fireOilExplosion",
    "iceWaterFreeze",
    "toxicAcidCloud",
    "healingCrystalResonance",
    "nitroExplosion",
    "manaCrystalAmplification"
)

foreach ($reactionType in $reactionTypes) {
    $particlePath = "$modPath\particles\reactions\$reactionType.particle"
    
    if ($SkipExisting -and (Test-Path $particlePath)) {
        Write-Host "  Skipping existing: $reactionType" -ForegroundColor Gray
        continue
    }
    
    $params = @{
        AssetType = "Particle"
        Name = "reaction_$reactionType"
        UseCppBackend = $UseCppBackend
        Parameters = @{
            ReactionType = $reactionType
            Intensity = "high"
        }
    }
    
    & "$scriptPath\StarboundOllamaAssetGenerator.ps1" @params
}

# 5. Generate Crafting Station Sprites
Write-Host "`n[5/5] Generating Crafting Station Sprites..." -ForegroundColor Green
$stationTypes = @("alchemy_table", "magical_forge", "cold_lab", "pressure_chamber")
foreach ($stationType in $stationTypes) {
    $spritePath = "$modPath\sprites\crafting\stations\$stationType.png"
    
    if ($SkipExisting -and (Test-Path $spritePath)) {
        Write-Host "  Skipping existing: $stationType" -ForegroundColor Gray
        continue
    }
    
    $params = @{
        AssetType = "Sprite"
        Name = "station_$stationType"
        Width = 64
        Height = 64
        UseCppBackend = $UseCppBackend
        Parameters = @{
            Style = "crafting_station"
            StationType = $stationType
        }
    }
    
    & "$scriptPath\StarboundOllamaAssetGenerator.ps1" @params
}

Write-Host "`n=== Asset Generation Complete ===" -ForegroundColor Cyan
