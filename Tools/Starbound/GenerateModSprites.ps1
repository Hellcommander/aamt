#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate sprites for all spellstones and unique items in the Magi-Tech mod.
    
.DESCRIPTION
    Automatically generates sprites for:
    - All spellstone cores (common, refined, arcane, apex)
    - All elemental spellstones (fire, ice, lightning, nature, arcane, void, cosmic, temporal)
    - Unique mod items (alchemical grenade launcher, etc.)
    
.PARAMETER ModPath
    Path to the mod directory
    
.PARAMETER OllamaModel
    Ollama model to use
    
.PARAMETER UseCppBackend
    Use C++ backend for sprite generation
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
Write-Host "  Magi-Tech Mod Sprite Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Load spellstone definitions
# Validate $ModPath before Join-Path
$spellstoneFile = Join-Path $ModPath "items\spellstones\spellstone_items.json"
 if ([string]::IsNullOrWhiteSpace($spellstoneFile)) {
    Write-Host "  [FAIL] spellstoneFile is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($spellstoneFile)) {
    Write-Host "  [FAIL] spellstoneFile is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $spellstoneFile)) {
    Write-Host "Error: Spellstone file not found: $spellstoneFile" -ForegroundColor Red
    exit 1
}

$spellstoneData = Get-Content $spellstoneFile -Raw | ConvertFrom-Json
$spellstones = @()

# Extract base cores
if ($spellstoneData.spellstone_items.base_cores) {
    $spellstoneData.spellstone_items.base_cores.PSObject.Properties | ForEach-Object {
        $spellstones += @{
            Id = $_.Name
            Name = $_.Value.itemName
            Description = $_.Value.description
            Rarity = $_.Value.rarity
            Type = "Core"
        }
    }
}

# Extract elemental variants
if ($spellstoneData.spellstone_items.elemental_variants) {
    $spellstoneData.spellstone_items.elemental_variants.PSObject.Properties | ForEach-Object {
        $spellstones += @{
            Id = $_.Name
            Name = $_.Value.itemName
            Description = $_.Value.description
            Rarity = $_.Value.rarity
            Type = "Elemental"
            Element = $_.Value.properties.elementalAffinity
        }
    }
}

Write-Host "Found $($spellstones.Count) spellstones to generate" -ForegroundColor Green
Write-Host ""

# Generate sprites for each spellstone
$generated = 0
$failed = 0

foreach ($spellstone in $spellstones) {
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  Generating: $($spellstone.Name)" -ForegroundColor Cyan
    Write-Host "  ID: $($spellstone.Id)" -ForegroundColor Gray
    Write-Host "  Rarity: $($spellstone.Rarity)" -ForegroundColor Gray
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
    
    # Create prompt based on description and rarity
    $prompt = $spellstone.Description
    if ($spellstone.Element) {
        $prompt = "$($spellstone.Element) elemental crystal spellstone, $prompt"
    }
    
    # Add rarity-based visual cues
    switch ($spellstone.Rarity) {
        "Common" { $prompt = "$prompt, simple translucent crystal, basic magical glow" }
        "Rare" { $prompt = "$prompt, faceted crystal with enhanced glow, refined appearance" }
        "Epic" { $prompt = "$prompt, pulsating crystal with animated runes, powerful arcane energy" }
        "Legendary" { $prompt = "$prompt, radiant crystal with rotating inner shards, pure magical power" }
    }
    
    try {
        $params = @{
            AssetType = "ItemSprite"
            AssetName = $spellstone.Id
            Prompt = $prompt
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
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params
        
        $generated++
        Write-Host "✓ Generated sprite for $($spellstone.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "✗ Failed to generate sprite for $($spellstone.Name): $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# Generate sprites for unique items
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Generating Unique Item Sprites" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$uniqueItems = @(
    @{
        Id = "alchemical_grenade_launcher"
        Name = "Alchemical Grenade Launcher"
        Description = "A sophisticated launcher that mixes alchemical compounds to create devastating chemical reactions."
        Prompt = "alchemical grenade launcher weapon sprite, chemical mixing device, green and blue colors, mechanical appearance"
    }
)

foreach ($item in $uniqueItems) {
    Write-Host "Generating: $($item.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "ItemSprite"
            AssetName = $item.Id
            Prompt = $item.Prompt
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
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params
        
        $generated++
        Write-Host "✓ Generated sprite for $($item.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "✗ Failed to generate sprite for $($item.Name): $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# Summary
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Generation Complete" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Generated: $generated sprites" -ForegroundColor Green
Write-Host "Failed: $failed sprites" -ForegroundColor $(if ($failed -gt 0) { "Red" } else { "Green" })
Write-Host ""
Write-Host "Sprites saved to: $(Join-Path $ModPath 'assets\items\sprites')" -ForegroundColor Gray
Write-Host ""
