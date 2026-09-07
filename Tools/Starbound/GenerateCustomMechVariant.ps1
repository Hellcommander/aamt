# GenerateCustomMechVariant.ps1
# Generates a custom variant mech set with user-defined theme

param(
    [Parameter(Mandatory=$true)]
    [string]$VariantName,
    
    [Parameter(Mandatory=$true)]
    [string]$VariantDisplayName,
    
    [string]$Description = "",
    
    [int[]]$PrimaryColor = @(150, 150, 180),
    [int[]]$SecondaryColor = @(100, 100, 140),
    [int[]]$AccentColor = @(200, 200, 255),
    [int[]]$GlowColor = @(150, 200, 255),
    
    [string]$Aesthetic = "magitech",
    [string]$Material = "enchanted_metal",
    [string]$Details = "rune_etched",
    
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

Write-Host "=== Generating Custom Variant: $VariantDisplayName ===" -ForegroundColor Cyan
Write-Host "Variant ID: $VariantName" -ForegroundColor Yellow

# Build variant template
$variantTemplate = @{
    id = $VariantName
    name = $VariantDisplayName
    description = if ($Description) { $Description } else { "Custom variant: $VariantDisplayName" }
    colorScheme = @{
        primary = $PrimaryColor
        secondary = $SecondaryColor
        accent = $AccentColor
        glow = $GlowColor
    }
    artStyle = @{
        shading = "flat"
        outline = $true
        outlineColor = @(50, 50, 50)
        paletteLimit = 16
        pixelArt = $true
    }
    designLanguage = @{
        techLevel = "advanced"
        aesthetic = $Aesthetic
        material = $Material
        details = $Details
    }
}

# Save variant template to registry
$variantRegistryPath = "$modPath\Data\Config\Mechs\VariantRegistry.json"
if (-not (Test-Path $variantRegistryPath)) {
    $registry = @{
        customVariants = @()
    } | ConvertTo-Json -Depth 10
    Set-Content -Path $variantRegistryPath -Value $registry
}

$registry = Get-Content $variantRegistryPath | ConvertFrom-Json
if (-not $registry.customVariants) {
    $registry.customVariants = @()
}

# Check if variant already exists
$existing = $registry.customVariants | Where-Object { $_.id -eq $VariantName } | Select-Object -First 1
if ($existing) {
    Write-Host "Variant already exists. Updating..." -ForegroundColor Yellow
    $existing.name = $VariantDisplayName
    $existing.description = $variantTemplate.description
    $existing.colorScheme = $variantTemplate.colorScheme
    $existing.artStyle = $variantTemplate.artStyle
    $existing.designLanguage = $variantTemplate.designLanguage
} else {
    $registry.customVariants += $variantTemplate
}

$registry | ConvertTo-Json -Depth 10 | Set-Content -Path $variantRegistryPath

# Generate the variant set
& "$scriptPath\GenerateMechVariantSet.ps1" -VariantName $VariantName -UseCppBackend $UseCppBackend -SkipExisting:$SkipExisting

Write-Host "`n=== Custom Variant Generated ===" -ForegroundColor Cyan
Write-Host "Variant saved to registry: $variantRegistryPath" -ForegroundColor Gray
