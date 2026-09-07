# GenerateReagentIcons.ps1
# Generates icons for all registered reagents

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

# Load reagent definitions from both config files
$reagentConfig1 = Get-Content "$modPath\config\enhancedAlchemicalGrenadeLauncher.json" | ConvertFrom-Json
$reagentConfig2 = Get-Content "$modPath\scripts\BusPlugins\AlchemistBus\config\reagents.json" | ConvertFrom-Json

$allReagents = @()
if ($reagentConfig1.reagents) {
    $reagentConfig1.reagents.PSObject.Properties | ForEach-Object { $allReagents += $_.Name }
}
if ($reagentConfig2.reagents) {
    $reagentConfig2.reagents.PSObject.Properties | ForEach-Object { $allReagents += $_.Name }
}

$allReagents = $allReagents | Select-Object -Unique

Write-Host "=== Generating Reagent Icons ===" -ForegroundColor Cyan
Write-Host "Found $($allReagents.Count) unique reagents" -ForegroundColor Yellow

# Ensure directory exists
$iconDir = "$modPath\interface\icons\reagents"
if (-not (Test-Path $iconDir)) {
    New-Item -ItemType Directory -Path $iconDir -Force | Out-Null
}

foreach ($reagentId in $allReagents) {
    $iconPath = "$iconDir\$reagentId.png"
    
    if ($SkipExisting -and (Test-Path $iconPath)) {
        Write-Host "  Skipping existing: $reagentId" -ForegroundColor Gray
        continue
    }
    
    # Get reagent properties
    $reagent = $null
    if ($reagentConfig1.reagents.$reagentId) {
        $reagent = $reagentConfig1.reagents.$reagentId
    } elseif ($reagentConfig2.reagents.$reagentId) {
        $reagent = $reagentConfig2.reagents.$reagentId
    }
    
    # Determine color from reagent properties
    $color = @(100, 150, 255) # default blue
    if ($reagent.color) {
        $color = $reagent.color
    } elseif ($reagent.tags) {
        # Color based on tags
        if ($reagent.tags -contains "flammable" -or $reagent.tags -contains "fire") {
            $color = @(255, 100, 0)
        } elseif ($reagent.tags -contains "cold" -or $reagent.tags -contains "ice") {
            $color = @(200, 230, 255)
        } elseif ($reagent.tags -contains "toxic" -or $reagent.tags -contains "acid") {
            $color = @(100, 255, 100)
        } elseif ($reagent.tags -contains "magical" -or $reagent.tags -contains "crystal") {
            $color = @(200, 150, 255)
        } elseif ($reagent.tags -contains "healing") {
            $color = @(150, 255, 150)
        }
    }
    
    $params = @{
        AssetType = "Icon"
        AssetName = "reagent_$reagentId"
        Prompt = "A reagent icon for $reagentId. Circular icon, 64x64 pixels, glowing effect, color scheme based on reagent properties"
        OutputDir = "$modPath\assets"
        UseCppBackend = $UseCppBackend
        Parameters = @{
            Size = 64
            Shape = "Circle"
            Color = $color
            Glow = $true
            GlowIntensity = 0.6
            Label = $reagentId
        }
    }
    
    Write-Host "  Generating icon: $reagentId" -ForegroundColor White
    & "$scriptPath\StarboundOllamaAssetGenerator.ps1" @params
}

Write-Host "`n=== Reagent Icon Generation Complete ===" -ForegroundColor Cyan
