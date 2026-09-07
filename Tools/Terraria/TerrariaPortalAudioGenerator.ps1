<#
.SYNOPSIS
    Generates sound effects for Terraria portal mods using procedural audio generation.
    AI-Assisted Modding Tools (AAMT) - Terraria Toolset

.DESCRIPTION
    Creates Terraria-compatible portal sound effects including:
    - Activation sounds (portal opening)
    - Ambient sounds (loopable while portal is active)
    - Teleport sounds (when using portal)
    - Deactivation sounds (portal closing)

.PARAMETER PortalName
    Name/ID of the portal

.PARAMETER Preset
    Portal preset (Void, Fire, Ice, Electric, Nature, Shadow, Light)

.PARAMETER Description
    Natural language description of the portal

.PARAMETER OutputDir
    Output directory for audio files

.PARAMETER GenerateActivation
    Generate activation sound

.PARAMETER GenerateAmbient
    Generate ambient sound

.PARAMETER GenerateTeleport
    Generate teleport sound

.PARAMETER GenerateDeactivation
    Generate deactivation sound

.PARAMETER GenerateAll
    Generate all sound types

.PARAMETER UseAI
    Use Ollama to generate audio specifications

.PARAMETER AssessQuality
    Assess audio quality using shared quality assessment system

.PARAMETER MinQualityScore
    Minimum quality score to keep (default: 17/20)

.EXAMPLE
    .\TerrariaPortalAudioGenerator.ps1 -PortalName "VoidPortal" -Preset Void -GenerateAll

.EXAMPLE
    .\TerrariaPortalAudioGenerator.ps1 -PortalName "FirePortal" -Preset Fire -GenerateAll -AssessQuality
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$PortalName,
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("Void", "Fire", "Ice", "Electric", "Nature", "Shadow", "Light", "Generic")]
    [string]$Preset = "Void",
    
    [Parameter(Mandatory=$false)]
    [string]$Description = "",
    
    [string]$OutputDir = "TerrariaPortals",
    
    [switch]$GenerateActivation,
    
    [switch]$GenerateAmbient,
    
    [switch]$GenerateTeleport,
    
    [switch]$GenerateDeactivation,
    
    [switch]$GenerateAll,
    
    [switch]$UseAI,
    
    [switch]$AssessQuality,
    
    [int]$MinQualityScore = 17,
    
    [string]$OllamaModel = ""
)

$ErrorActionPreference = "Stop"

# Import unified tool detection and integration
$sharedPath = Join-Path (Split-Path $PSScriptRoot -Parent) "Shared"
Import-Module (Join-Path $sharedPath "ToolDetection.psm1") -ErrorAction SilentlyContinue
Import-Module (Join-Path $sharedPath "ToolsetIntegration.psm1") -ErrorAction SilentlyContinue
Import-Module (Join-Path $sharedPath "OllamaIntegration.psm1") -ErrorAction SilentlyContinue

# Initialize tools
$tools = Initialize-ToolsetTools `
    -RequiredTools @("Python") `
    -OptionalTools @("Ollama")

# Check required tools
if (-not $tools.AllRequiredAvailable) {
    Write-Host ""
    Write-Host "ERROR: Missing required tools for Terraria portal audio generation" -ForegroundColor Red
    Show-ToolsetStatus -ToolsetName "Terraria Portal Audio" `
        -RequiredTools @("Python") `
        -OptionalTools @("Ollama")
    exit 1
}

# Use Ollama if available and requested
if ($UseAI) {
    $ollamaAvailable = Use-OllamaIfAvailable
    if (-not $ollamaAvailable) {
        Write-Host "⚠ Warning: Ollama not available, but -UseAI was specified" -ForegroundColor Yellow
        Write-Host "  Continuing without AI features..." -ForegroundColor Gray
        $UseAI = $false
    }
}

# ============================================================
# CONFIGURATION
# ============================================================

$script:PythonScript = Join-Path $PSScriptRoot "terraria_portal_audio_generator.py"
if (-not $script:OllamaUrl) {
    $script:OllamaUrl = "http://localhost:11434"
    $script:OllamaApiUrl = "$script:OllamaUrl/api"
}

# ============================================================
# HELPER FUNCTIONS
# ============================================================

function Invoke-OllamaChat {
    param(
        [string]$Prompt,
        [string]$ModelName
    )
    
    # Use shared module if available
    if (Get-Command Invoke-OllamaRequest -ErrorAction SilentlyContinue) {
        $systemPrompt = "You are a game audio designer specializing in portal sound effects for Terraria. Generate JSON specifications for procedural audio generation."
        return Invoke-OllamaRequest -Prompt $Prompt -TaskType "audio" -SystemPrompt $systemPrompt -ModelName $ModelName -UseChatAPI
    }
    
    # Fallback implementation
    if ([string]::IsNullOrWhiteSpace($ModelName)) {
        $ModelName = "wizardlm-uncensored:latest"
    }
    
    $requestBody = @{
        model = $ModelName
        messages = @(
            @{
                role = "system"
                content = "You are a game audio designer specializing in portal sound effects for Terraria. Generate JSON specifications for procedural audio generation."
            },
            @{
                role = "user"
                content = $Prompt
            }
        )
        stream = $false
    } | ConvertTo-Json -Depth 10
    
    try {
        $response = Invoke-RestMethod -Uri "$script:OllamaApiUrl/chat" -Method Post -Body $requestBody -ContentType "application/json" -TimeoutSec 120
        
        if ($response.message -and $response.message.content) {
            return $response.message.content.Trim()
        }
    }
    catch {
        Write-Host "  Error calling Ollama: $_" -ForegroundColor Yellow
    }
    
    return $null
}

function Generate-AudioSpec {
    param(
        [string]$PortalName,
        [string]$Preset,
        [string]$Description,
        [string]$ModelName
    )
    
    if ($UseAI) {
        Write-Host "Generating audio specification with AI..." -ForegroundColor Cyan
        
        $prompt = @"
Generate a JSON specification for a Terraria portal sound effect:

Portal Name: $PortalName
Preset: $Preset
Description: $Description

Output JSON with this structure:
{
  "portalName": "$PortalName",
  "preset": "$Preset",
  "duration": 1.0
}

Output ONLY valid JSON, no explanations, no markdown.
"@
        
        $result = Invoke-OllamaChat -Prompt $prompt -ModelName $ModelName
        
        if ($result) {
            $jsonMatch = $result -match '\{[\s\S]*\}'
            if ($jsonMatch) {
                try {
                    $spec = $matches[0] | ConvertFrom-Json
                    return $spec
                }
                catch {
                    Write-Host "  Error parsing JSON: $_" -ForegroundColor Yellow
                }
            }
        }
    }
    
    # Fallback: generate basic spec
    return @{
        portalName = $PortalName
        preset = $Preset
        duration = 1.0
    }
}

function Get-SafeFileName {
    param([string]$Name)
    
    $invalid = [System.IO.Path]::GetInvalidFileNameChars()
    $safe = $Name
    foreach ($char in $invalid) {
        $safe = $safe.Replace($char, '_')
    }
    
    $safe = $safe.Replace(' ', '_').ToLower()
    return $safe
}

# ============================================================
# MAIN EXECUTION
# ============================================================

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Terraria Portal Audio Generator" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Generate specification
$spec = Generate-AudioSpec -PortalName $PortalName -Preset $Preset -Description $Description -ModelName $OllamaModel

if ($null -eq $spec) {
    Write-Host "ERROR: Failed to generate specification" -ForegroundColor Red
    exit 1
}

# Save spec to temp file
$specFile = Join-Path $env:TEMP "terraria_audio_spec_$(Get-Random).json"
$specJson = $spec | ConvertTo-Json -Depth 10
$specJson | Out-File -FilePath $specFile -Encoding UTF8

# Generate safe name
$safeName = Get-SafeFileName -Name $PortalName

# Determine what to generate
$generateActivation = $GenerateActivation -or $GenerateAll
$generateAmbient = $GenerateAmbient -or $GenerateAll
$generateTeleport = $GenerateTeleport -or $GenerateAll
$generateDeactivation = $GenerateDeactivation -or $GenerateAll

if (-not ($generateActivation -or $generateAmbient -or $generateTeleport -or $generateDeactivation)) {
    Write-Host "ERROR: No sound types specified. Use -GenerateActivation, -GenerateAmbient, -GenerateTeleport, -GenerateDeactivation, or -GenerateAll" -ForegroundColor Red
    exit 1
}

# Build Python command
$pythonArgs = @(
    $script:PythonScript,
    "--spec", $specFile,
    "--output", $OutputDir,
    "--name", $safeName
)

if ($generateActivation) { $pythonArgs += "--activation" }
if ($generateAmbient) { $pythonArgs += "--ambient" }
if ($generateTeleport) { $pythonArgs += "--teleport" }
if ($generateDeactivation) { $pythonArgs += "--deactivation" }
if ($generateActivation -and $generateAmbient -and $generateTeleport -and $generateDeactivation) { 
    $pythonArgs += "--all"
}

# Run Python script
Write-Host "Generating portal audio..." -ForegroundColor Cyan
Write-Host "  Portal: $PortalName" -ForegroundColor Gray
Write-Host "  Preset: $Preset" -ForegroundColor Gray
Write-Host ""

try {
    $pythonCmd = $tools.Python.Path
    & $pythonCmd $pythonArgs
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Python script failed with exit code $LASTEXITCODE" -ForegroundColor Red
        exit 1
    }
    
    Write-Host ""
    Write-Host "✓ Audio generation complete!" -ForegroundColor Green
    
    # Assess quality if requested
    if ($AssessQuality) {
        Write-Host ""
        Write-Host "Assessing audio quality..." -ForegroundColor Cyan
        
        # Import shared audio quality assessment
        $audioQaPath = Join-Path $sharedPath "audio_quality_assessment.py"
        
        if (Test-Path $audioQaPath) {
            $audioDir = Join-Path $OutputDir "Sounds"
            if (Test-Path $audioDir) {
                # Use Python to run quality assessment
                $qaScript = @"
import sys
import os
from pathlib import Path

# Add Shared to path
shared_path = r'$sharedPath'
sys.path.insert(0, shared_path)

from audio_quality_assessment import batch_assess_audio_quality, filter_audio_by_quality

audio_dir = Path(r'$audioDir')
assessments, total, filtered = batch_assess_audio_quality(
    audio_dir,
    min_score=$MinQualityScore,
    ollama_url='$script:OllamaUrl',
    ollama_model='llama3.1:8b'
)

if filtered > 0:
    removed = filter_audio_by_quality(audio_dir, assessments, $MinQualityScore)
    print(f'Filtered {removed} files below score $MinQualityScore')
else:
    print(f'All {total} files meet quality threshold')
"@
                $qaScript | & $pythonCmd -
            } else {
                Write-Host "  No audio directory found for quality assessment" -ForegroundColor Yellow
            }
        } else {
            Write-Host "  Audio quality assessment module not found (optional)" -ForegroundColor Yellow
        }
    }
}
catch {
    Write-Host "ERROR: Failed to generate audio: $_" -ForegroundColor Red
    exit 1
}
finally {
    # Clean up temp file
    if (Test-Path $specFile) {
        Remove-Item $specFile -ErrorAction SilentlyContinue
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
