<#
.SYNOPSIS
    Generates spell sound effects for the game Elin using procedural audio generation.
    AI-Assisted Modding Tools (AAMT) - Elin Toolset

.DESCRIPTION
    Creates Elin-compatible spell sound effects including:
    - Cast sounds (whoosh, charge, etc.)
    - Impact sounds (hit, explosion, etc.)
    - Loop sounds (for channeled spells, buffs, etc.)

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}

.PARAMETER SpellDescription
    Description of the spell (e.g., "Nature Magic - Verdant Pulse: a burst of green life energy")

.PARAMETER SpellName
    Name of the spell (auto-generated if not provided)

.PARAMETER OutputDir
    Output directory for Elin audio assets

.PARAMETER GenerateCast
    Generate cast sound

.PARAMETER GenerateImpact
    Generate impact sound

.PARAMETER GenerateLoop
    Generate loop sound

.PARAMETER GenerateAll
    Generate all sound types

.PARAMETER UseAI
    Use Ollama to generate audio specifications

.PARAMETER AssessQuality
    Assess audio quality using shared quality assessment system

.PARAMETER MinQualityScore
    Minimum quality score to keep (default: 17/20)

.EXAMPLE
    .\ElinSpellAudioGenerator.ps1 -SpellDescription "Nature Magic - Verdant Pulse" -GenerateAll

.EXAMPLE
    .\ElinSpellAudioGenerator.ps1 -SpellDescription "Fireball spell" -GenerateCast -GenerateImpact -AssessQuality
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$SpellDescription,
    
    [string]$SpellName = "",
    
    [string]$OutputDir = "ElinAssets",
    
    [switch]$GenerateCast,
    
    [switch]$GenerateImpact,
    
    [switch]$GenerateLoop,
    
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
    Write-Host "ERROR: Missing required tools for Elin spell audio generation" -ForegroundColor Red
    Show-ToolsetStatus -ToolsetName "Elin Audio" `
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

$script:PythonScript = Join-Path $PSScriptRoot "elin_spell_audio.py"
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
        $systemPrompt = "You are a game audio designer specializing in spell sound effects. Generate JSON specifications for procedural audio generation."
        return Invoke-OllamaRequest -Prompt $Prompt -TaskType "audio" -SystemPrompt $systemPrompt -ModelName $ModelName -UseChatAPI
    }
    
    # Fallback implementation
    if ([string]::IsNullOrWhiteSpace($ModelName)) {
        $ModelName = "llama3.1:8b"  # Default for regular content (wizardlm-uncensored reserved for taboo/mutation)
    }
    
    $requestBody = @{
        model = $ModelName
        messages = @(
            @{
                role = "system"
                content = "You are a game audio designer specializing in spell sound effects. Generate JSON specifications for procedural audio generation."
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
        [string]$Description,
        [string]$ModelName
    )
    
    Write-Host "Generating audio specification..." -ForegroundColor Cyan
    
    $prompt = @"
Generate a JSON specification for Elin spell audio based on this description:

$Description

Requirements:
- Cast sound: 0.3-0.8 seconds, whoosh/charge/activation sound
- Impact sound: 0.2-0.5 seconds, hit/explosion sound
- Loop sound: 1-3 seconds, loopable for channeled spells/buffs

Output JSON with this structure:
{
  "spellName": "spell name",
  "school": "nature|fire|ice|lightning|dark|light|arachnomancy|dragon|blood|generic",
  "spellType": "cast|charge|burst|beam|channel|generic",
  "colors": ["#hex1", "#hex2"],
  "castDuration": 0.5,
  "impactDuration": 0.3,
  "loopDuration": 2.0
}

Output ONLY valid JSON, no explanations, no markdown.
"@
    
    $result = Invoke-OllamaChat -Prompt $prompt -ModelName $ModelName
    
    if ($result) {
        # Extract JSON from response
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
    
    # Fallback: generate basic spec from description
    Write-Host "  Using fallback specification..." -ForegroundColor Gray
    return Generate-FallbackSpec -Description $Description
}

function Generate-FallbackSpec {
    param([string]$Description)
    
    # Extract school from description
    $school = "generic"
    if ($Description -match "Nature|nature") { $school = "nature" }
    elseif ($Description -match "Fire|fire|flame") { $school = "fire" }
    elseif ($Description -match "Ice|ice|frost|cold") { $school = "ice" }
    elseif ($Description -match "Lightning|lightning|electric|shock") { $school = "lightning" }
    elseif ($Description -match "Dark|dark|shadow|void") { $school = "dark" }
    elseif ($Description -match "Light|light|holy|divine") { $school = "light" }
    elseif ($Description -match "Arachnomancy|spider|web|venom") { $school = "arachnomancy" }
    elseif ($Description -match "Dragon|dragon") { $school = "dragon" }
    elseif ($Description -match "Blood|blood|vampire") { $school = "blood" }
    
    # Extract spell type
    $spellType = "generic"
    if ($Description -match "charge|charging") { $spellType = "charge" }
    elseif ($Description -match "burst|explosion|explode") { $spellType = "burst" }
    elseif ($Description -match "beam|channel|channeled") { $spellType = "beam" }
    elseif ($Description -match "cast|casting") { $spellType = "cast" }
    
    # Get colors based on school
    $schoolColors = @{
        "nature" = @("#4caf50", "#81c784")
        "fire" = @("#f44336", "#ff7043")
        "ice" = @("#03a9f4", "#81d4fa")
        "lightning" = @("#ffeb3b", "#fff59d")
        "dark" = @("#424242", "#757575")
        "light" = @("#fff9c4", "#ffffff")
        "arachnomancy" = @("#6a1b9a", "#9c27b0")
        "dragon" = @("#d32f2f", "#f57c00")
        "blood" = @("#c62828", "#e53935")
        "generic" = @("#9e9e9e", "#bdbdbd")
    }
    
    $colors = $schoolColors[$school]
    if (-not $colors) { $colors = $schoolColors["generic"] }
    
    # Extract spell name
    $spellName = ""
    if ($Description -match "([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)") {
        $spellName = $matches[1]
    }
    if ([string]::IsNullOrWhiteSpace($spellName)) {
        $spellName = "Spell"
    }
    
    return @{
        spellName = $spellName
        school = $school
        spellType = $spellType
        colors = $colors
        castDuration = 0.5
        impactDuration = 0.3
        loopDuration = 2.0
    }
}

function Get-SafeFileName {
    param([string]$Name)
    
    # Remove invalid characters
    $invalid = [System.IO.Path]::GetInvalidFileNameChars()
    $safe = $Name
    foreach ($char in $invalid) {
        $safe = $safe.Replace($char, '_')
    }
    
    # Remove spaces and make lowercase
    $safe = $safe.Replace(' ', '_').ToLower()
    
    return $safe
}

# ============================================================
# MAIN EXECUTION
# ============================================================

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Elin Spell Audio Generator" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Generate or load specification
$spec = $null
$specFile = Join-Path $env:TEMP "elin_audio_spec_$(Get-Random).json"

if ($UseAI) {
    $modelName = if ([string]::IsNullOrWhiteSpace($OllamaModel)) { "" } else { $OllamaModel }
    $spec = Generate-AudioSpec -Description $SpellDescription -ModelName $modelName
} else {
    $spec = Generate-FallbackSpec -Description $SpellDescription
}

if ($null -eq $spec) {
    Write-Host "ERROR: Failed to generate specification" -ForegroundColor Red
    exit 1
}

# Convert to JSON and save
$specJson = $spec | ConvertTo-Json -Depth 10
[System.IO.File]::WriteAllText($specFile, $specJson, (New-Object System.Text.UTF8Encoding $false))

# Generate spell name if not provided
if ([string]::IsNullOrWhiteSpace($SpellName)) {
    $SpellName = $spec.spellName
    if ([string]::IsNullOrWhiteSpace($SpellName)) {
        $SpellName = "spell"
    }
}
$safeName = Get-SafeFileName -Name $SpellName

# Determine what to generate
$generateCast = $GenerateCast -or $GenerateAll
$generateImpact = $GenerateImpact -or $GenerateAll
$generateLoop = $GenerateLoop -or $GenerateAll

if (-not ($generateCast -or $generateImpact -or $generateLoop)) {
    Write-Host "ERROR: No sound types specified. Use -GenerateCast, -GenerateImpact, -GenerateLoop, or -GenerateAll" -ForegroundColor Red
    exit 1
}

# Build Python command
$pythonArgs = @(
    $script:PythonScript,
    "--spec", $specFile,
    "--output", $OutputDir,
    "--name", $safeName
)

if ($generateCast) { $pythonArgs += "--cast" }
if ($generateImpact) { $pythonArgs += "--impact" }
if ($generateLoop) { $pythonArgs += "--loop" }
if ($generateCast -and $generateImpact -and $generateLoop) { 
    $pythonArgs += "--all"
}

# Run Python script
Write-Host "Generating spell audio..." -ForegroundColor Cyan
Write-Host "  Spell: $SpellName" -ForegroundColor Gray
Write-Host "  School: $($spec.school)" -ForegroundColor Gray
Write-Host "  Type: $($spec.spellType)" -ForegroundColor Gray
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
        $sharedPath = Join-Path (Split-Path $PSScriptRoot -Parent) "Shared"
        $audioQaPath = Join-Path $sharedPath "audio_quality_assessment.py"
        
        if (Test-Path $audioQaPath) {
            $audioDir = Join-Path $OutputDir "audio"
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
