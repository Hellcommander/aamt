# Terraria Portal Ollama Spritesheet Generator
# AI-Assisted Modding Tools (AAMT) - Terraria Toolset
# Uses Ollama to generate animated portal spritesheets for tModLoader

param(
    [Parameter(Mandatory=$true)]
    [string]$PortalName,
    
    [Parameter(Mandatory=$true)]
    [string]$Description,
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("Void", "Shadow", "Fire", "Ice", "Electric", "Nature", "Light")]
    [string]$Preset = "Void",
    
    [Parameter(Mandatory=$false)]
    [ValidateSet(16, 32)]
    [int]$TileSize = 16,
    
    [Parameter(Mandatory=$false)]
    [int]$FrameCount = 8,
    
    [Parameter(Mandatory=$false)]
    [string]$OutputDir = "TerrariaPortals",
    
    [Parameter(Mandatory=$false)]
    [string]$OllamaUrl = "http://localhost:11434",
    
    [Parameter(Mandatory=$false)]
    [string]$Model = "",
    
    [Parameter(Mandatory=$false)]
    [int]$Candidates = 5,
    
    [Parameter(Mandatory=$false)]
    [double]$MinQuality = 8.0
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

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Terraria Portal Ollama Generator" -ForegroundColor Cyan
Write-Host "  AI-Assisted Modding Tools (AAMT)" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Initialize tools for Terraria portal generation
$tools = Initialize-ToolsetTools `
    -RequiredTools @("Python", "Ollama") `
    -OptionalTools @("ImageMagick")

# Check required tools
if (-not $tools.AllRequiredAvailable) {
    Write-Host ""
    Write-Host "ERROR: Missing required tools for Terraria portal generation" -ForegroundColor Red
    Show-ToolsetStatus -ToolsetName "Terraria" `
        -RequiredTools @("Python", "Ollama") `
        -OptionalTools @("ImageMagick")
    Write-Host ""
    Write-Host "This tool REQUIRES Ollama to generate unique portal designs." -ForegroundColor Red
    Write-Host "Fallback designs are generic and not recommended." -ForegroundColor Yellow
    Write-Host ""
    $useFallback = Read-Host "Continue with fallback anyway? (y/N)"
    if ($useFallback -ne 'y' -and $useFallback -ne 'Y') {
        Write-Host "Exiting. Please install required tools and try again." -ForegroundColor Red
        exit 1
    }
    Write-Host ""
}

# Get Ollama availability
$ollamaAvailable = $tools.Tools["Ollama"].Available
if ($ollamaAvailable) {
    Write-Host "[OK] Ollama is available" -ForegroundColor Green
    $ollamaInfo = Get-OllamaInfo
    if ($ollamaInfo.Available) {
        Write-Host "  URL: $($ollamaInfo.Url)" -ForegroundColor Gray
        try {
            $ollamaCheck = Invoke-RestMethod -Uri "$OllamaUrl/api/tags" -Method Get -TimeoutSec 2
            if ($ollamaCheck.models.Count -gt 0) {
                Write-Host "  Available models: $($ollamaCheck.models.Count)" -ForegroundColor Gray
                $modelNames = $ollamaCheck.models | ForEach-Object { $_.name }
                Write-Host "  Models: $($modelNames -join ', ')" -ForegroundColor Gray
            }
        } catch {
            # Ignore - already checked by unified detection
        }
    }
} else {
    Write-Host "[ERROR] Ollama not available" -ForegroundColor Red
    Write-Host "  Start Ollama: ollama serve" -ForegroundColor Yellow
    Write-Host "  Or install: https://ollama.ai" -ForegroundColor Yellow
}

# Get Python path
$pythonPath = Get-PythonPath
if (-not $pythonPath) {
    Write-Host "[ERROR] Python not found" -ForegroundColor Red
    Write-Host "  Install Python: https://www.python.org/downloads/" -ForegroundColor Gray
    exit 1
}

# Check for PIL/Pillow
try {
    $pillowCheck = python -c "from PIL import Image; print('OK')" 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[WARN] PIL/Pillow not found" -ForegroundColor Yellow
        Write-Host "  Install with: pip install Pillow" -ForegroundColor Gray
        Write-Host "  Some features may not work." -ForegroundColor Gray
    }
} catch {
    Write-Host "[WARN] Could not check PIL/Pillow" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  Portal Name: $PortalName" -ForegroundColor Gray
Write-Host "  Description: $Description" -ForegroundColor Gray
Write-Host "  Preset: $Preset" -ForegroundColor Gray
Write-Host "  Tile Size: ${TileSize}x${TileSize}" -ForegroundColor Gray
Write-Host "  Frame Count: $FrameCount" -ForegroundColor Gray
Write-Host "  Output: $OutputDir" -ForegroundColor Gray
Write-Host "  Candidates: $Candidates" -ForegroundColor Gray
Write-Host "  Min Quality: $MinQuality" -ForegroundColor Gray
if ($Model) {
    Write-Host "  Model: $Model" -ForegroundColor Gray
}
Write-Host ""

# Create output directory
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

# Build output path
$outputFile = Join-Path $OutputDir "${PortalName}_spritesheet.png"

Write-Host "Generating portal spritesheet..." -ForegroundColor Yellow
Write-Host ""

$generatorScript = Join-Path $PSScriptRoot "terraria_portal_ollama_generator.py"

if (Test-Path $generatorScript) {
    $argsList = @(
        "--portal-name", $PortalName,
        "--description", $Description,
        "--preset", $Preset,
        "--tile-size", $TileSize,
        "--frame-count", $FrameCount,
        "--output", $outputFile,
        "--ollama-url", $OllamaUrl,
        "--candidates", $Candidates,
        "--min-quality", $MinQuality
    )
    
    if ($Model) {
        $argsList += "--model", $Model
    }
    
    # Add --require-ollama flag if Ollama is available, otherwise allow fallback
    if ($ollamaAvailable) {
        $argsList += "--require-ollama"
    } else {
        $argsList += "--allow-fallback"
    }
    
    & $pythonPath $generatorScript @argsList
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "============================================" -ForegroundColor Green
        Write-Host "  Generation Complete!" -ForegroundColor Green
        Write-Host "============================================" -ForegroundColor Green
        Write-Host ""
        Write-Host "Spritesheet saved to: $outputFile" -ForegroundColor Cyan
        
        if (Test-Path $outputFile) {
            $fileInfo = Get-Item $outputFile
            Write-Host "  File size: $([math]::Round($fileInfo.Length / 1KB, 2)) KB" -ForegroundColor Gray
        }
        
        Write-Host ""
        Write-Host "Next steps:" -ForegroundColor Yellow
        Write-Host "  1. Copy spritesheet to mod Assets/Tiles/ folder" -ForegroundColor Gray
        Write-Host "  2. Update tile class to use spritesheet" -ForegroundColor Gray
        Write-Host "  3. Test animation in tModLoader" -ForegroundColor Gray
    } else {
        Write-Host ""
        Write-Host "[ERROR] Generation failed" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "[ERROR] Generator script not found: $generatorScript" -ForegroundColor Red
    exit 1
}

