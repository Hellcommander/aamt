<#
.SYNOPSIS
    Unified spritesheet generator for Terraria and Starbound modding.

.DESCRIPTION
    Generates game-compatible spritesheets with metadata for both Terraria (tModLoader)
    and Starbound from a single texture source. Supports batch processing and
    automatic metadata generation.

.PARAMETER InputDir

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}
    Directory containing source PNG textures

.PARAMETER OutputDir
    Output directory for spritesheets and metadata

.PARAMETER GameFormat
    Target game format: Terraria, Starbound, Both

.PARAMETER TileSize
    Tile size in pixels (Terraria: 16/32, Starbound: 8-aligned)

.PARAMETER Columns
    Number of columns in spritesheet

.PARAMETER AnimationFrames
    Number of animation frames (for horizontal strips)

.PARAMETER AnimationSpeed
    Animation speed (Terraria frames per second)

.PARAMETER GenerateTextures
    Generate textures using AssetMakerAI before assembling

.PARAMETER TextureDescriptions
    Array of texture descriptions for generation

.EXAMPLE
    .\CrossGameSpritesheet.ps1 -InputDir "Textures" -GameFormat Both -TileSize 16 -Columns 8

.EXAMPLE
    .\CrossGameSpritesheet.ps1 -GenerateTextures -TextureDescriptions @("wood", "stone", "metal") -GameFormat Terraria -TileSize 32
#>

[CmdletBinding()]
param(
    [string]$InputDir = "",
    
    [string]$OutputDir = "GameSpritesheets",
    
    [ValidateSet("Terraria", "Starbound", "Both")]
    [string]$GameFormat = "Both",
    
    [int]$TileSize = 16,
    
    [int]$Columns = 8,
    
    [int]$AnimationFrames = 1,
    
    [int]$AnimationSpeed = 5,
    
    [switch]$GenerateTextures,
    
    [string[]]$TextureDescriptions = @(),
    
    [string]$SpritesheetName = "spritesheet",
    
    [string]$BlenderPath = "",
    
    [string]$ModelPath = "",
    
    [ValidateSet("rotation", "animation", "static")]
    [string]$SpritesheetType = "static",
    
    [int]$RotationFrames = 1
)

$ErrorActionPreference = "Stop"

# ============================================================
# CONFIGURATION
# ============================================================

$script:PythonScript = Join-Path $PSScriptRoot "cross_game_spritesheet.py"
$script:BlenderScript = Join-Path $PSScriptRoot "blender_asset_spritesheet_export.py"

# ============================================================
# HELPER FUNCTIONS
# ============================================================

function Test-PythonAvailable {
    $python = Get-Command "python" -ErrorAction SilentlyContinue
    if (-not $python) {
        $python = Get-Command "python3" -ErrorAction SilentlyContinue
    }
    return $null -ne $python
}

function Test-PillowInstalled {
    $pythonCmd = Get-PythonCommand
    if (-not $pythonCmd) {
        return $false
    }
    
    try {
        $result = & $pythonCmd -c "import PIL; print('OK')" 2>&1
        return $result -eq "OK"
    }
    catch {
        return $false
    }
}

function Get-PythonCommand {
    $python = Get-Command "python" -ErrorAction SilentlyContinue
    if ($python) {
        return $python.Source
    }
    $python = Get-Command "python3" -ErrorAction SilentlyContinue
    if ($python) {
        return $python.Source
    }
    return $null
}

# ============================================================
# TEXTURE GENERATION
# ============================================================

function Generate-TexturesIfNeeded {
    if (-not $GenerateTextures -or $TextureDescriptions.Count -eq 0) {
        return $InputDir
    }
    
    Write-Host "Generating textures..." -ForegroundColor Cyan
    
    $tempTextureDir = Join-Path $env:TEMP "CrossGameTextures_$(Get-Random)"
    if (-not (Test-Path $tempTextureDir)) {
        New-Item -ItemType Directory -Path $tempTextureDir -Force | Out-Null
    }
    
    # Use BatchBakeTextures if available
    $batchBakeScript = Join-Path $PSScriptRoot "BatchBakeTextures.ps1"
    if (Test-Path $batchBakeScript) {
        & $batchBakeScript -MaterialList $TextureDescriptions -OutputDir $tempTextureDir -TextureSize $TileSize
    } else {
        # Fallback to AssetMakerAI
        foreach ($desc in $TextureDescriptions) {
            $outputPath = Join-Path $tempTextureDir "$desc.png"
            & (Join-Path $PSScriptRoot "..\Transcendence\AssetMakerAI.ps1") -Action GenerateTexture -InputData $desc -TextureMethod Procedural -TextureSize $TileSize -OutputPath $outputPath -ErrorAction SilentlyContinue
        }
    }
    
    return $tempTextureDir
}

# ============================================================
# MAIN EXECUTION
# ============================================================

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Cross-Game Spritesheet Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Generate textures if needed
$sourceDir = if ($GenerateTextures) {
    Generate-TexturesIfNeeded
} else {
    if ([string]::IsNullOrWhiteSpace($InputDir)) {
        Write-Host "Error: InputDir required unless -GenerateTextures is specified" -ForegroundColor Red
        exit 1
    }
    $InputDir
}

if (-not (Test-Path $sourceDir)) {
    Write-Host "Error: Source directory not found: $sourceDir" -ForegroundColor Red
    exit 1
}

# Check Python
if (-not (Test-PythonAvailable)) {
    Write-Host "Error: Python not found. Required for spritesheet assembly." -ForegroundColor Red
    Write-Host "  Install Python from: https://www.python.org/" -ForegroundColor Yellow
    exit 1
}

$pythonCmd = Get-PythonCommand
Write-Host "Python: $pythonCmd" -ForegroundColor Green

# Check Pillow
if (-not (Test-PillowInstalled)) {
    Write-Host ""
    Write-Host "Warning: PIL/Pillow not installed" -ForegroundColor Yellow
    Write-Host "  Installing Pillow..." -ForegroundColor Cyan
    try {
        & $pythonCmd -m pip install Pillow --quiet 2>&1 | Out-Null
        if (Test-PillowInstalled) {
            Write-Host "  ✓ Pillow installed successfully" -ForegroundColor Green
        } else {
            Write-Host "  ✗ Pillow installation failed" -ForegroundColor Red
            Write-Host "  Install manually: python -m pip install Pillow" -ForegroundColor Yellow
            exit 1
        }
    }
    catch {
        Write-Host "  ✗ Could not install Pillow automatically" -ForegroundColor Red
        Write-Host "  Install manually: python -m pip install Pillow" -ForegroundColor Yellow
        exit 1
    }
}
Write-Host ""

# Check Python script
if (-not (Test-Path $script:PythonScript)) {
    Write-Host "Error: Python script not found: $script:PythonScript" -ForegroundColor Red
    exit 1
}

# Create output directory
$OutputDir = [System.IO.Path]::GetFullPath($OutputDir)
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

Write-Host "Source: $sourceDir" -ForegroundColor Gray
Write-Host "Output: $OutputDir" -ForegroundColor Gray
Write-Host "Format: $GameFormat" -ForegroundColor Gray
Write-Host "Tile Size: ${TileSize}x${TileSize}" -ForegroundColor Gray
Write-Host "Columns: $Columns" -ForegroundColor Gray
Write-Host ""

# Build Python command
$pythonArgs = @(
    $script:PythonScript,
    "--input", $sourceDir,
    "--output", $OutputDir,
    "--tile-size", $TileSize.ToString(),
    "--columns", $Columns.ToString(),
    "--frames", $AnimationFrames.ToString(),
    "--speed", $AnimationSpeed.ToString(),
    "--name", $SpritesheetName
)

if ($GameFormat -eq "Terraria") {
    $pythonArgs += "--terraria"
} elseif ($GameFormat -eq "Starbound") {
    $pythonArgs += "--starbound"
} else {
    $pythonArgs += "--both"
}

Write-Host "Assembling spritesheets..." -ForegroundColor Cyan
Write-Host ""

try {
    $process = Start-Process -FilePath $pythonCmd -ArgumentList $pythonArgs -Wait -NoNewWindow -PassThru
    
    if ($process.ExitCode -eq 0) {
        Write-Host ""
        Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
        Write-Host "  Complete" -ForegroundColor Cyan
        Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
        Write-Host ""
        
        # List generated files
        $generatedFiles = Get-ChildItem -LiteralPath $OutputDir -File | Sort-Object Name
        if ($generatedFiles.Count -gt 0) {
            Write-Host "Generated files:" -ForegroundColor Green
            foreach ($file in $generatedFiles) {
                $size = [math]::Round($file.Length / 1KB, 2)
                Write-Host "  - $($file.Name) ($size KB)" -ForegroundColor Gray
            }
        }
        
        Write-Host ""
        Write-Host "Spritesheets ready for:" -ForegroundColor Yellow
        if ($GameFormat -eq "Both" -or $GameFormat -eq "Terraria") {
            Write-Host "  Terraria (tModLoader)" -ForegroundColor White
        }
        if ($GameFormat -eq "Both" -or $GameFormat -eq "Starbound") {
            Write-Host "  Starbound" -ForegroundColor White
        }
    } else {
        Write-Host ""
        Write-Host "Error: Spritesheet generation failed (exit code: $($process.ExitCode))" -ForegroundColor Red
        exit 1
    }
}
catch {
    Write-Host ""
    Write-Host "Error: $_" -ForegroundColor Red
    exit 1
}

