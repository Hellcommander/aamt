# GenerateFormWheelUI.ps1
# Generates UI assets for the Form Wheel radial menu

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

Write-Host "=== Generating Form Wheel UI Assets ===" -ForegroundColor Cyan

# 1. Generate wheel background
Write-Host "[1/5] Generating wheel background..." -ForegroundColor Green
$bgPath = "$modPath\interface\formwheel\background.png"
if (-not ($SkipExisting -and (Test-Path $bgPath))) {
    $params = @{
        AssetType = "Sprite"
        AssetName = "formwheel_background"
        Width = 400
        Height = 400
        UseCppBackend = $UseCppBackend
        Parameters = @{
            Style = "radial_background"
            Transparency = 0.7
        }
    }
    & "$scriptPath\StarboundOllamaAssetGenerator.ps1" @params
}

# 2. Generate selection highlight
Write-Host "[2/5] Generating selection highlight..." -ForegroundColor Green
$highlightPath = "$modPath\interface\formwheel\highlight.png"
if (-not ($SkipExisting -and (Test-Path $highlightPath))) {
    $params = @{
        AssetType = "Sprite"
        AssetName = "formwheel_highlight"
        Width = 64
        Height = 64
        UseCppBackend = $UseCppBackend
        Parameters = @{
            Style = "selection_highlight"
            Color = @(255, 200, 0)
            Glow = $true
        }
    }
    & "$scriptPath\StarboundOllamaAssetGenerator.ps1" @params
}

# 3. Generate slot indicators (0-9)
Write-Host "[3/5] Generating slot indicators..." -ForegroundColor Green
for ($i = 0; $i -lt 10; $i++) {
    $slotPath = "$modPath\interface\formwheel\slot_$i.png"
    if (-not ($SkipExisting -and (Test-Path $slotPath))) {
        $params = @{
            AssetType = "Sprite"
            AssetName = "formwheel_slot_$i"
            Width = 32
            Height = 32
            UseCppBackend = $UseCppBackend
            Parameters = @{
                Style = "number_indicator"
                Number = $i
            }
        }
        & "$scriptPath\StarboundOllamaAssetGenerator.ps1" @params
    }
}

# 4. Generate UI sounds
Write-Host "[4/5] Generating UI sounds..." -ForegroundColor Green
$sounds = @("open", "hover", "select", "close")
foreach ($sound in $sounds) {
    $soundPath = "$modPath\sfx\formWheel_$sound.wav"
    if (-not ($SkipExisting -and (Test-Path $soundPath))) {
        $params = @{
            AssetType = "Sound"
            AssetName = "formWheel_$sound"
            UseCppBackend = $UseCppBackend
            Parameters = @{
                Type = "ui_$sound"
                Duration = 0.3
            }
        }
        & "$scriptPath\StarboundOllamaAssetGenerator.ps1" @params
    }
}

# 5. Generate locked/disabled indicator
Write-Host "[5/5] Generating locked indicator..." -ForegroundColor Green
$lockedPath = "$modPath\interface\formwheel\locked.png"
if (-not ($SkipExisting -and (Test-Path $lockedPath))) {
    $params = @{
        AssetType = "Sprite"
        AssetName = "formwheel_locked"
        Width = 48
        Height = 48
        UseCppBackend = $UseCppBackend
        Parameters = @{
            Style = "locked_icon"
            Color = @(80, 80, 80)
        }
    }
    & "$scriptPath\StarboundOllamaAssetGenerator.ps1" @params
}

Write-Host "`n=== Form Wheel UI Asset Generation Complete ===" -ForegroundColor Cyan
