# GenerateCraftingStationAssets.ps1
# Generates sprites and UI elements for crafting stations

param(
    [Parameter(Mandatory=$false)]
    [string]$ModPath = "F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery",
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

# Load station definitions
$stationConfig = Get-Content "$ModPath\Data\Config\Alchemy\CraftingStationConfig.json" | ConvertFrom-Json
$stations = $stationConfig.stationTypes.PSObject.Properties | ForEach-Object { $_.Name }

Write-Host "=== Generating Crafting Station Assets ===" -ForegroundColor Cyan
Write-Host "Found $($stations.Count) station types" -ForegroundColor Yellow

# Ensure directories exist
$spriteDir = "$ModPath\sprites\crafting\stations"
$iconDir = "$ModPath\interface\icons\crafting"
if (-not (Test-Path $spriteDir)) {
    New-Item -ItemType Directory -Path $spriteDir -Force | Out-Null
}
if (-not (Test-Path $iconDir)) {
    New-Item -ItemType Directory -Path $iconDir -Force | Out-Null
}

foreach ($stationId in $stations) {
    $station = $stationConfig.stationTypes.$stationId
    $spritePath = "$spriteDir\$stationId.png"
    $iconPath = "$iconDir\$stationId.png"
    
    # Generate station sprite (64x64)
    if (-not ($SkipExisting -and (Test-Path $spritePath))) {
        $params = @{
            AssetType = "Sprite"
            AssetName = "station_$stationId"
            Prompt = "$($station.displayName) - Crafting station sprite, $($station.tier) tier, 64x64 pixels"
            OutputDir = $spriteDir
            UseCppBackend = $UseCppBackend
            Parameters = @{
                Style = "crafting_station"
                StationType = $stationId
                DisplayName = $station.displayName
                Tier = $station.tier
                HasHeatSource = $station.hasHeatSource
                HasCoolingSystem = $station.hasCoolingSystem
                Width = 64
                Height = 64
            }
        }
        
        Write-Host "  Generating sprite: $stationId" -ForegroundColor White
        & "$scriptPath\StarboundOllamaAssetGenerator.ps1" @params
    } else {
        Write-Host "  Skipping existing sprite: $stationId" -ForegroundColor Gray
    }
    
    # Generate station icon (32x32)
    if (-not ($SkipExisting -and (Test-Path $iconPath))) {
        $params = @{
            AssetType = "Icon"
            AssetName = "station_icon_$stationId"
            Prompt = "$($station.displayName) - Crafting station icon, 32x32 pixels"
            OutputDir = $iconDir
            UseCppBackend = $UseCppBackend
            Parameters = @{
                Size = 32
                Shape = "Square"
                Color = @(150, 150, 200)
                Glow = $true
                GlowIntensity = 0.4
                Label = $station.displayName
            }
        }
        
        Write-Host "  Generating icon: $stationId" -ForegroundColor White
        & "$scriptPath\StarboundOllamaAssetGenerator.ps1" @params
    } else {
        Write-Host "  Skipping existing icon: $stationId" -ForegroundColor Gray
    }
}

Write-Host "`n=== Crafting Station Asset Generation Complete ===" -ForegroundColor Cyan
