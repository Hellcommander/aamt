# Ollama Visual Variation Generator
# Uses Ollama to generate 50 variations and assess quality

param(
    [Parameter(Mandatory=$false)]
    [string]$RegistryPath = "space_whale_visual_language_registry.json",
    
    [Parameter(Mandatory=$false)]
    [string]$OutputDir = "Output/OllamaVariations",
    
    [Parameter(Mandatory=$false)]
    [int]$Count = 50,
    
    [Parameter(Mandatory=$false)]
    [string]$Model = "llama3.2"
)

$ErrorActionPreference = "Stop"

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}

Write-Host "Ollama Visual Variation Generator" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

# Check if Ollama is available
try {
    $ollamaCheck = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -Method Get -TimeoutSec 2
    Write-Host "Ollama is available" -ForegroundColor Green
} catch {
    Write-Host "WARNING: Ollama not available at http://localhost:11434" -ForegroundColor Yellow
    Write-Host "Start Ollama: ollama serve" -ForegroundColor Yellow
    Write-Host "Or install: https://ollama.ai" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Will use fallback generation instead." -ForegroundColor Gray
}

# Check if registry exists
if (-not (Test-Path $RegistryPath)) {
    Write-Host "ERROR: Registry file not found: $RegistryPath" -ForegroundColor Red
    exit 1
}

# Create output directory
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  Model: $Model" -ForegroundColor Gray
Write-Host "  Variations: $Count" -ForegroundColor Gray
Write-Host "  Registry: $RegistryPath" -ForegroundColor Gray
Write-Host "  Output: $OutputDir" -ForegroundColor Gray
Write-Host ""

# Check for Python
$python = Get-Command python -ErrorAction SilentlyContinue
if ($null -eq $python) {
    Write-Host "ERROR: Python not found" -ForegroundColor Red
    exit 1
}

Write-Host "Generating $Count variations using Ollama..." -ForegroundColor Yellow
Write-Host "This may take a while..." -ForegroundColor Gray
Write-Host ""

$generatorScript = "ollama_visual_variation_generator.py"

if (Test-Path $generatorScript) {
    & python $generatorScript --registry $RegistryPath --output $OutputDir --count $Count --model $Model
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "Generation complete!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Results saved to: $OutputDir" -ForegroundColor Cyan
        Write-Host "  - ollama_palette_variations.json (all variations with quality scores)" -ForegroundColor Gray
    } else {
        Write-Host "WARNING: Generation may have failed" -ForegroundColor Yellow
    }
} else {
    Write-Host "ERROR: Generator script not found: $generatorScript" -ForegroundColor Red
    exit 1
}

