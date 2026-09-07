<#
.SYNOPSIS
    Batch Asset Generator - Generate all mod assets at once
    AI-Assisted Modding Tools (AAMT) - Elin Toolset

.DESCRIPTION
    Comprehensive batch processing script that generates all assets for the mod
    using the Ollama-powered asset generator. Processes multiple systems and
    asset types efficiently.

.PARAMETER ModPath
    Path to the mod directory

.PARAMETER Quality
    Asset quality level (low, medium, high, ultra)

.PARAMETER GenerateSpritesheets
    Generate spritesheets for batch assets

.PARAMETER Systems
    Comma-separated list of systems (or "all")

.EXAMPLE
    .\BatchAssetGenerator.ps1 -ModPath "E:\...\CustomRaceClassCreator" -Quality "high" -GenerateSpritesheets
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$ModPath,
    
    [ValidateSet("low", "medium", "high", "ultra")]
    [string]$Quality = "high",
    
    [switch]$GenerateSpritesheets,
    
    [string]$Systems = "all"
)

$ErrorActionPreference = "Stop"

# Import unified tool detection and integration
$sharedPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\Shared"
Import-Module (Join-Path $sharedPath "ToolDetection.psm1") -ErrorAction SilentlyContinue
Import-Module (Join-Path $sharedPath "ToolsetIntegration.psm1") -ErrorAction SilentlyContinue

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}

# Initialize tools
$tools = Initialize-ToolsetTools `
    -RequiredTools @() `
    -OptionalTools @("Ollama", "Python", "ImageMagick")

Write-Host "`n🚀 Batch Asset Generator" -ForegroundColor Cyan
Write-Host "AI-Assisted Modding Tools (AAMT)" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Gray

# Show tool status
Show-ToolsetStatus -ToolsetName "Elin" `
    -RequiredTools @() `
    -OptionalTools @("Ollama", "Python", "ImageMagick")
Write-Host ""

# Import the Ollama asset generator
$generatorScript = Join-Path $PSScriptRoot "OllamaAssetGenerator.ps1"

if (-not (Test-Path $generatorScript)) {
    Write-Host "❌ Error: OllamaAssetGenerator.ps1 not found!" -ForegroundColor Red
    exit 1
}

# Define asset types to generate
$assetTypes = @("textures", "icons", "sprites", "spell_assets")

# Build command
$params = @{
    ModPath = $ModPath
    AssetTypes = ($assetTypes -join ",")
    Systems = $Systems
    Quality = $Quality
    UseOllama = $true
}

if ($GenerateSpritesheets) {
    $params.GenerateSpritesheets = $true
}

# Execute generator
Write-Host "`n📋 Configuration:" -ForegroundColor Cyan
Write-Host "  Mod Path: $ModPath" -ForegroundColor White
Write-Host "  Quality: $Quality" -ForegroundColor White
Write-Host "  Systems: $Systems" -ForegroundColor White
Write-Host "  Asset Types: $($assetTypes -join ', ')" -ForegroundColor White
Write-Host "  Spritesheets: $(if ($GenerateSpritesheets) { 'Yes' } else { 'No' })" -ForegroundColor White
Write-Host ""

& $generatorScript @params

Write-Host "`n✅ Batch generation complete!" -ForegroundColor Green
