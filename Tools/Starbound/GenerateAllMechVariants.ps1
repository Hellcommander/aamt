# GenerateAllMechVariants.ps1
# Generates all predefined variant mech sets

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

# Load variant config to get all variant IDs
$modPath = "F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery"
$variantConfig = Get-Content "$modPath\Data\Config\Mechs\MechVariantSystem.json" | ConvertFrom-Json

# Get all variant IDs
$variants = @()
if ($variantConfig.variantTemplates.variantExamples) {
    $variants = $variantConfig.variantTemplates.variantExamples | ForEach-Object { $_.id }
}

Write-Host "=== Generating All Mech Variant Sets ===" -ForegroundColor Cyan
Write-Host "Found $($variants.Count) variant templates" -ForegroundColor Yellow

foreach ($variantId in $variants) {
    Write-Host "`n--- Generating Variant: $variantId ---" -ForegroundColor Green
    & "$scriptPath\GenerateMechVariantSet.ps1" -VariantName $variantId -UseCppBackend $UseCppBackend -SkipExisting:$SkipExisting
}

Write-Host "`n=== All Variant Sets Generated ===" -ForegroundColor Cyan
