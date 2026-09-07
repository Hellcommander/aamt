#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate game-usable mechset variants using Ollama AI
    
.DESCRIPTION
    Creates complete mechset variants with all required assets (JSON configs, icons, animations, VFX).
    Each variant is a complete, game-ready mechset with visual cohesion across all forms.
    
.PARAMETER ModPath
    Path to the mod directory
    
.PARAMETER OllamaModel
    Ollama model for general tasks
    
.PARAMETER PlanningModel
    Ollama model for planning/structured tasks
    
.PARAMETER VisualModel
    Ollama model for visual/creative tasks
    
.PARAMETER VariantNames
    Specific variant names to generate (default: all variants from MechVariantSystem.json)
    
.PARAMETER BaseMechSets
    Base mechsets to create variants of (default: all mechsets found)
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$ModPath = "F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery",
    
    [Parameter(Mandatory=$false)]
    [string]$OllamaModel = "qwen2.5-coder:7b",
    
    [Parameter(Mandatory=$false)]
    [string]$PlanningModel = "",  # Auto-selected by OllamaIntegration.psm1 (prefers qwen2.5-coder:14b)
    
    [Parameter(Mandatory=$false)]
    [string]$VisualModel = "",  # Auto-selected by OllamaIntegration.psm1 (prefers llama3.1:8b)
    
    [Parameter(Mandatory=$false)]
    [string[]]$VariantNames = @(),
    
    [Parameter(Mandatory=$false)]
    [string[]]$BaseMechSets = @()
)

$ErrorActionPreference = "Stop"
# Validate ModPath is not empty
if ([string]::IsNullOrWhiteSpace($ModPath)) {
    Write-Host "Error: ModPath cannot be empty" -ForegroundColor Red
    Write-Host "  Please provide a valid mod path or use the default" -ForegroundColor Gray
    exit 1
}

$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $scriptPath) "AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  MechSet Variant Generator (Game-Usable)" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "IMPORTANT WORKFLOW:" -ForegroundColor Yellow
Write-Host "  1. Reference Forms must be generated FIRST (templates/inspiration - not directly used by players)" -ForegroundColor Yellow
Write-Host "  2. This script generates MECHFORMS (actual forms used in mechsets)" -ForegroundColor Yellow
Write-Host "  3. Players build mechsets, which contain mechforms (not reference forms)" -ForegroundColor Yellow
Write-Host "  4. Mechforms are based on reference forms but altered to match the mechset's structural consistency" -ForegroundColor Yellow
Write-Host ""

# Load variant system config
$variantConfigPath = "$ModPath\Data\Config\Mechs\MechVariantSystem.json"
if (-not (Test-Path $variantConfigPath)) {
    Write-Host "Error: MechVariantSystem.json not found at $variantConfigPath" -ForegroundColor Red
    exit 1
}

$variantConfig = Get-Content $variantConfigPath | ConvertFrom-Json

# Get variant names
if ($VariantNames.Count -eq 0) {
    if ($variantConfig.variantTemplates.variantExamples) {
        $VariantNames = $variantConfig.variantTemplates.variantExamples | ForEach-Object { $_.id }
    } else {
        Write-Host "Warning: No variant examples found in config" -ForegroundColor Yellow
        $VariantNames = @("voidCorrupted", "crystalInfused", "infernal", "arctic", "neon")
    }
}

# Get base mechsets
$mechSetPath = "$ModPath\Data\Config\Mechs"
if ($BaseMechSets.Count -eq 0) {
    $mechSetFiles = Get-ChildItem -Path $mechSetPath -Filter "*MechSet.json" -ErrorAction SilentlyContinue
    $BaseMechSets = $mechSetFiles | ForEach-Object { $_.BaseName }
}

if ($BaseMechSets.Count -eq 0) {
    Write-Host "Error: No base mechsets found" -ForegroundColor Red
    exit 1
}

Write-Host "Variants to generate: $($VariantNames.Count)" -ForegroundColor Yellow
Write-Host "Base mechsets: $($BaseMechSets.Count)" -ForegroundColor Yellow
Write-Host "Total variant mechsets to create: $($VariantNames.Count * $BaseMechSets.Count)" -ForegroundColor Yellow
Write-Host ""

# Get Ollama asset generator script
$ollamaGenerator = Join-Path $scriptPath "StarboundOllamaAssetGenerator.ps1"
if (-not (Test-Path $ollamaGenerator)) {
    Write-Host "Error: StarboundOllamaAssetGenerator.ps1 not found" -ForegroundColor Red
    exit 1
}

$totalGenerated = 0
$totalErrors = 0

foreach ($baseMechSet in $BaseMechSets) {
    Write-Host "`n=== Processing Base MechSet: $baseMechSet ===" -ForegroundColor Cyan
    
    foreach ($variantName in $VariantNames) {
        Write-Host "`n--- Generating Variant: $variantName for $baseMechSet ---" -ForegroundColor Green
        
        try {
            # Generate mechset variant using Ollama asset generator
            $params = @{
                AssetType = "MechSetVariant"
                AssetName = $variantName
                OllamaModel = $OllamaModel
                PlanningModel = $PlanningModel
                VisualModel = $VisualModel
                Parameters = @{
                    BaseMechSet = $baseMechSet
                }
            }
            
            & $ollamaGenerator @params
            
            if ($LASTEXITCODE -eq 0) {
                $totalGenerated++
                Write-Host "[OK] Generated variant: ${baseMechSet}_${variantName}" -ForegroundColor Green
            } else {
                $totalErrors++
                Write-Host "[ERROR] Failed to generate variant: ${baseMechSet}_${variantName}" -ForegroundColor Red
            }
        } catch {
            $totalErrors++
            Write-Host "[ERROR] Exception generating variant: $_" -ForegroundColor Red
        }
    }
}

Write-Host "`n═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Generation Complete" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Total variant mechsets generated: $totalGenerated" -ForegroundColor Green
if ($totalErrors -gt 0) {
    Write-Host "Total errors: $totalErrors" -ForegroundColor Red
    exit 1
}

Write-Host "All mechset variants generated successfully!" -ForegroundColor Green
