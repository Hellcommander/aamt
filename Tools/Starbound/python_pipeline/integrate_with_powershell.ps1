#!/usr/bin/env pwsh
<#
.SYNOPSIS
    PowerShell wrapper to call Python frame generator orchestrator

.DESCRIPTION
    Integrates the Python frame generator with PowerShell asset generation pipeline.
    Provides a seamless interface for calling Python from PowerShell.
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$AssetName,
    
    [Parameter(Mandatory=$false)]
    [int]$FrameCount = 8,
    
    [Parameter(Mandatory=$false)]
    [int]$FrameWidth = 16,
    
    [Parameter(Mandatory=$false)]
    [int]$FrameHeight = 16,
    
    [Parameter(Mandatory=$false)]
    [string[]]$ColorHints = @(),
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("SpellCast", "DeviceActivation", "StatusEffect", "Default")]
    [string]$AnimationType = "SpellCast",
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("pixel_art", "high_res", "ms_designer")]
    [string]$QualityLevel = "pixel_art",
    
    [Parameter(Mandatory=$false)]
    [string]$OutputDir = "output",
    
    [Parameter(Mandatory=$false)]
    [string]$OllamaUrl = "http://localhost:11434",
    
    [Parameter(Mandatory=$false)]
    [string]$PythonPath = "python"
)

$ErrorActionPreference = "Stop"

# Get script directory
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonPipelineDir = Join-Path $PSScriptRoot "python_pipeline"
$orchestratorScript = Join-Path $pythonPipelineDir "frame_generator_orchestrator.py"

# Check if Python orchestrator exists
if (-not (Test-Path $orchestratorScript)) {
    Write-Host "[WARN] Python orchestrator not found: $orchestratorScript" -ForegroundColor Yellow
    Write-Host "  Falling back to PowerShell frame generation" -ForegroundColor Gray
    return $false
}

# Check if Python is available
try {
    $pythonVersion = & $PythonPath --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Python not found"
    }
} catch {
    Write-Host "[WARN] Python not available: $_" -ForegroundColor Yellow
    Write-Host "  Falling back to PowerShell frame generation" -ForegroundColor Gray
    return $false
}

# Create temporary job JSON
$tempJobFile = Join-Path $env:TEMP "starbound_job_$(Get-Random).json"
$jobData = @{
    asset_name = $AssetName
    segment_list = @()
    frame_count = $FrameCount
    frame_width = $FrameWidth
    frame_height = $FrameHeight
    color_hints = $ColorHints
    quality_level = $QualityLevel
    animation_type = $AnimationType
    output_dir = $OutputDir
} | ConvertTo-Json -Depth 10

$jobData | Set-Content -Path $tempJobFile -Encoding UTF8

try {
    Write-Host "[INFO] Calling Python frame generator orchestrator..." -ForegroundColor Cyan
    Write-Host "  Asset: $AssetName" -ForegroundColor Gray
    Write-Host "  Frames: $FrameCount" -ForegroundColor Gray
    Write-Host "  Size: ${FrameWidth}x${FrameHeight}" -ForegroundColor Gray
    Write-Host "  Quality: $QualityLevel" -ForegroundColor Gray
    
    # Call Python orchestrator
    $result = & $PythonPath $orchestratorScript `
        --job $tempJobFile `
        --output $OutputDir `
        --ollama-url $OllamaUrl
    
    $exitCode = $LASTEXITCODE
    
    if ($exitCode -eq 0) {
        Write-Host "[OK] Python orchestrator completed successfully" -ForegroundColor Green
        
        # Check for output files
        $atlasPath = Join-Path $OutputDir "$AssetName.png"
        $framesPath = Join-Path $OutputDir "$AssetName.frames"
        
        if (Test-Path $atlasPath) {
            Write-Host "  Atlas: $atlasPath" -ForegroundColor Green
        }
        if (Test-Path $framesPath) {
            Write-Host "  Frames: $framesPath" -ForegroundColor Green
        }
        
        return $true
    } else {
        Write-Host "[WARN] Python orchestrator exited with code $exitCode" -ForegroundColor Yellow
        Write-Host "  Falling back to PowerShell frame generation" -ForegroundColor Gray
        return $false
    }
} catch {
    Write-Host "[ERROR] Python orchestrator failed: $_" -ForegroundColor Red
    Write-Host "  Falling back to PowerShell frame generation" -ForegroundColor Gray
    return $false
} finally {
    # Cleanup temp file
    if (Test-Path $tempJobFile) {
        Remove-Item $tempJobFile -Force -ErrorAction SilentlyContinue
    }
}
