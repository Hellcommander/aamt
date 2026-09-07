<#
.SYNOPSIS
    Generates sound effects for Caves of Qud mods using procedural audio generation.
    AI-Assisted Modding Tools (AAMT) - Qud Toolset

.DESCRIPTION
    Creates Qud-compatible sound effects including:
    - Attack sounds (swing, strike)
    - Hit sounds (impact, contact)
    - Death sounds (creature death)
    - Spawn sounds (appear, summon)
    - Ambient/Idle sounds (loopable)
    - Walk/Run/Jump/Land sounds (footsteps)
    - Use sounds (item activation)
    - Missile fire sounds (projectile launch)
    - Detonated sounds (explosions)

.PARAMETER ModName
    Name of the mod or path to mod directory

.PARAMETER SoundTypes
    Comma-separated list of sound types to generate (default: all)
    Available: attack, hit, death, spawn, ambient, idle, walk, run, jump, land, use, missilefire, detonated

.PARAMETER CreatureType
    Type of creature (small, medium, large, insect, beast, robot, mutant, generic)

.PARAMETER Material
    Material type for hit sounds (flesh, metal, stone, wood, crystal, generic)

.PARAMETER Surface
    Surface type for walk sounds (dirt, stone, metal, wood, sand, generic)

.PARAMETER OutputDir
    Output directory for audio files (default: mod's Sounds directory)

.PARAMETER UseAI
    Use Ollama to generate audio specifications

.PARAMETER AssessQuality
    Assess audio quality using shared quality assessment system

.PARAMETER MinQualityScore
    Minimum quality score to keep (default: 17/20)

.EXAMPLE
    .\QudAudioGenerator.ps1 -ModName "Broodmother Mutation" -SoundTypes "attack,hit,death"

.EXAMPLE
    .\QudAudioGenerator.ps1 -ModName "Space Time Vortex" -SoundTypes "all" -UseAI -AssessQuality
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$ModName,
    
    [string]$SoundTypes = "all",
    
    [string]$CreatureType = "generic",
    
    [string]$Material = "generic",
    
    [string]$Surface = "generic",
    
    [string]$OutputDir = "",
    
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
    Write-Host "ERROR: Missing required tools for Qud audio generation" -ForegroundColor Red
    Show-ToolsetStatus -ToolsetName "Qud Audio" `
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

$script:PythonScript = Join-Path $PSScriptRoot "qud_audio_generator.py"
if (-not $script:OllamaUrl) {
    $script:OllamaUrl = "http://localhost:11434"
    $script:OllamaApiUrl = "$script:OllamaUrl/api"
}

# ============================================================
# HELPER FUNCTIONS
# ============================================================

function Find-ModDirectory {
    param([string]$ModName)
    
    # Check if it's a direct path
    if (Test-Path $ModName) {
        return (Get-Item $ModName).FullName
    }
    
    # Default mods paths
    $modsPaths = @(
        "$env:USERPROFILE\AppData\LocalLow\Freehold Games\CavesOfQud\Mods",
        "$env:USERPROFILE\.config\unity3d\Freehold Games\CavesOfQud\Mods"
    )
    
    foreach ($modsPath in $modsPaths) {
        if (Test-Path $modsPath) {
            $modDirs = Get-ChildItem -Path $modsPath -Directory -ErrorAction SilentlyContinue
            foreach ($modDir in $modDirs) {
                if ($modDir.Name -like "*$ModName*") {
                    return $modDir.FullName
                }
            }
        }
    }
    
    return $null
}

function Invoke-OllamaChat {
    param(
        [string]$Prompt,
        [string]$ModelName
    )
    
    # Use shared module if available
    if (Get-Command Invoke-OllamaRequest -ErrorAction SilentlyContinue) {
        $systemPrompt = "You are a game audio designer specializing in sound effects for Caves of Qud. Generate JSON specifications for procedural audio generation."
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
                content = "You are a game audio designer specializing in sound effects for Caves of Qud. Generate JSON specifications for procedural audio generation."
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
        [string]$SoundType,
        [string]$CreatureType,
        [string]$Material,
        [string]$Surface,
        [string]$ModelName
    )
    
    if ($UseAI) {
        Write-Host "Generating audio specification with AI..." -ForegroundColor Cyan
        
        $prompt = @"
Generate a JSON specification for a Caves of Qud sound effect:

Sound Type: $SoundType
Creature Type: $CreatureType
Material: $Material
Surface: $Surface

Output JSON with this structure:
{
  "name": "sound_name",
  "creatureType": "$CreatureType",
  "material": "$Material",
  "surface": "$Surface",
  "duration": 0.3
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
        name = $SoundType
        creatureType = $CreatureType
        material = $Material
        surface = $Surface
        duration = 0.3
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
Write-Host "Qud Audio Generator" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Find mod directory
$modPath = Find-ModDirectory -ModName $ModName

if (-not $modPath) {
    Write-Host "ERROR: Mod '$ModName' not found" -ForegroundColor Red
    Write-Host "  Searched in default mods directories" -ForegroundColor Gray
    exit 1
}

Write-Host "Mod: $(Split-Path $modPath -Leaf)" -ForegroundColor Gray
Write-Host "Path: $modPath" -ForegroundColor Gray
Write-Host ""

# Determine output directory
if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $OutputDir = Join-Path $modPath "Sounds"
} else {
    $OutputDir = $OutputDir
}

# Determine sound types to generate
$soundTypesList = @()
if ($SoundTypes -eq "all") {
    $soundTypesList = @("attack", "hit", "death", "spawn", "ambient", "idle", "walk", "run", "jump", "land", "use", "missilefire", "detonated")
} else {
    $soundTypesList = $SoundTypes -split ',' | ForEach-Object { $_.Trim().ToLower() }
}

# Generate sounds
$generatedCount = 0
$failedCount = 0

foreach ($soundType in $soundTypesList) {
    Write-Host "Generating $soundType sound..." -ForegroundColor Cyan
    
    # Generate specification
    $modelName = if ([string]::IsNullOrWhiteSpace($OllamaModel)) { "" } else { $OllamaModel }
    $spec = Generate-AudioSpec -SoundType $soundType -CreatureType $CreatureType -Material $Material -Surface $Surface -ModelName $modelName
    
    if ($null -eq $spec) {
        Write-Host "  ERROR: Failed to generate specification" -ForegroundColor Red
        $failedCount++
        continue
    }
    
    # Save spec to temp file
    $specFile = Join-Path $env:TEMP "qud_audio_spec_$(Get-Random).json"
    $specJson = $spec | ConvertTo-Json -Depth 10
    $specJson | Out-File -FilePath $specFile -Encoding UTF8
    
    # Generate safe name
    $safeName = Get-SafeFileName -Name "$(Split-Path $modPath -Leaf)_$soundType"
    
    # Build Python command
    $pythonArgs = @(
        $script:PythonScript,
        "--spec", $specFile,
        "--output", $OutputDir,
        "--name", $safeName,
        "--type", $soundType
    )
    
    # Run Python script
    try {
        $pythonCmd = $tools.Python.Path
        & $pythonCmd $pythonArgs
        
        if ($LASTEXITCODE -eq 0) {
            $generatedCount++
            Write-Host "  ✓ Generated: $safeName.ogg" -ForegroundColor Green
        } else {
            $failedCount++
            Write-Host "  ✗ Failed with exit code $LASTEXITCODE" -ForegroundColor Red
        }
    }
    catch {
        $failedCount++
        Write-Host "  ✗ Error: $_" -ForegroundColor Red
    }
    finally {
        # Clean up temp file
        if (Test-Path $specFile) {
            Remove-Item $specFile -ErrorAction SilentlyContinue
        }
    }
}

Write-Host ""
Write-Host "Generation Summary:" -ForegroundColor Cyan
Write-Host "  Generated: $generatedCount" -ForegroundColor Green
if ($failedCount -gt 0) {
    Write-Host "  Failed: $failedCount" -ForegroundColor Red
}

# Assess quality if requested
if ($AssessQuality -and $generatedCount -gt 0) {
    Write-Host ""
    Write-Host "Assessing audio quality..." -ForegroundColor Cyan
    
    # Import shared audio quality assessment
    $audioQaPath = Join-Path $sharedPath "audio_quality_assessment.py"
    
    if (Test-Path $audioQaPath) {
        if (Test-Path $OutputDir) {
            # Use Python to run quality assessment
            $qaScript = @"
import sys
import os
from pathlib import Path

# Add Shared to path
shared_path = r'$sharedPath'
sys.path.insert(0, shared_path)

from audio_quality_assessment import batch_assess_audio_quality, filter_audio_by_quality

audio_dir = Path(r'$OutputDir')
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
            $qaScript | & $tools.Python.Path -
        } else {
            Write-Host "  No output directory found for quality assessment" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  Audio quality assessment module not found (optional)" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
