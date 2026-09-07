#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate sound effects for Starbound/OpenStarbound.

.DESCRIPTION
    Creates Starbound-compatible sound files (.wav, .ogg) with support for:
    - Procedural sound generation (tones, noise, combinations)
    - AI-assisted sound descriptions via Ollama
    - Sound effect presets (impact, charge, ambient, etc.)

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}
    - Integration with existing asset generation pipeline

.PARAMETER SoundName
    Name/kind of the sound (used in file name)

.PARAMETER SoundType
    Type of sound: Impact, Charge, Ambient, Magic, Mechanical, Organic, etc.

.PARAMETER Preset
    Preset sound configuration (Impact, Charge, Ambient, Magic, Mechanical, Organic)

.PARAMETER Description
    Optional description for AI-assisted generation

.PARAMETER Duration
    Sound duration in seconds (default: 0.5)

.PARAMETER Frequency
    Base frequency in Hz (default: 440)

.PARAMETER Volume
    Volume level 0.0-1.0 (default: 0.7)

.PARAMETER OutputDir
    Output directory for generated sounds

.PARAMETER Format
    Output format: wav or ogg (default: ogg for Starbound)

.PARAMETER OllamaModel
    Ollama model for AI-assisted generation

.PARAMETER OllamaUrl
    Ollama API URL

.EXAMPLE
    .\StarboundSoundGenerator.ps1 -SoundName "rhinoChargeStart" -Preset Charge

.EXAMPLE
    .\StarboundSoundGenerator.ps1 -SoundName "magicImpact" -SoundType Magic -Description "magical energy impact sound"
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$SoundName,
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("Impact", "Charge", "Ambient", "Magic", "Mechanical", "Organic", "Explosion", "Whoosh", "Roar", "Custom")]
    [string]$SoundType = "Custom",
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("Impact", "Charge", "Ambient", "Magic", "Mechanical", "Organic", "Explosion", "Whoosh", "Roar")]
    [string]$Preset = "",
    
    [Parameter(Mandatory=$false)]
    [string]$Description = "",
    
    [Parameter(Mandatory=$false)]
    [double]$Duration = 0.5,
    
    [Parameter(Mandatory=$false)]
    [int]$Frequency = 440,
    
    [Parameter(Mandatory=$false)]
    [double]$Volume = 0.7,
    
    [Parameter(Mandatory=$false)]
    [string]$OutputDir = "StarboundSounds",
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("wav", "ogg")]
    [string]$Format = "ogg",
    
    [Parameter(Mandatory=$false)]
    [string]$OllamaModel = "codellama:7b-instruct",
    
    [Parameter(Mandatory=$false)]
    [string]$OllamaUrl = "http://localhost:11434",
    
    [Parameter(Mandatory=$false)]
    [switch]$UsePython
)

$ErrorActionPreference = "Stop"
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

# Import shared Ollama integration module
$toolsRoot = Split-Path -Parent $PSScriptRoot
$sharedModulePath = Join-Path $toolsRoot "Shared\OllamaIntegration.psm1"
if (Test-Path $sharedModulePath) {
    Import-Module $sharedModulePath -Force
    Write-Host "Using shared Ollama integration module" -ForegroundColor Green
}

# Logging setup
# Validate $OutputDir before Join-Path
$logDir = Join-Path $OutputDir "logs"
 if ([string]::IsNullOrWhiteSpace($logDir)) {
    Write-Host "  [FAIL] logDir is null (${OutputDir}: '${OutputDir}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($logDir)) {
    Write-Host "  [FAIL] logDir is null (${OutputDir}: '${OutputDir}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] [$Level] $Message"
    $logFile = Join-Path $logDir "StarboundSound_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
    Add-Content -Path $logFile -Value $logMessage
    Write-Host $logMessage
}

Write-Log "═══════════════════════════════════════════════════════════" "INFO"
Write-Log "  Starbound Sound Generator" "INFO"
Write-Log "═══════════════════════════════════════════════════════════" "INFO"
Write-Log "Sound Name: $SoundName" "INFO"
Write-Log "Sound Type: $SoundType" "INFO"

# Use preset if specified
if ($Preset -and $Preset -ne "") {
    $SoundType = $Preset
}

# Preset configurations
$presetConfigs = @{
    "Impact" = @{
        Duration = 0.2
        Frequency = 200
        Volume = 0.8
        Description = "sharp impact sound with low frequency thud"
    }
    "Charge" = @{
        Duration = 0.5
        Frequency = 300
        Volume = 0.7
        Description = "building energy charge sound with rising pitch"
    }
    "Ambient" = @{
        Duration = 2.0
        Frequency = 220
        Volume = 0.4
        Description = "subtle ambient background sound"
    }
    "Magic" = @{
        Duration = 0.8
        Frequency = 600
        Volume = 0.6
        Description = "magical energy sound with ethereal qualities"
    }
    "Mechanical" = @{
        Duration = 0.3
        Frequency = 400
        Volume = 0.7
        Description = "mechanical whirring and clicking sound"
    }
    "Organic" = @{
        Duration = 0.6
        Frequency = 150
        Volume = 0.6
        Description = "organic biological sound with natural resonance"
    }
    "Explosion" = @{
        Duration = 0.4
        Frequency = 100
        Volume = 0.9
        Description = "explosive boom with low frequency rumble"
    }
    "Whoosh" = @{
        Duration = 0.3
        Frequency = 500
        Volume = 0.6
        Description = "fast whooshing air movement sound"
    }
    "Roar" = @{
        Duration = 1.0
        Frequency = 80
        Volume = 0.8
        Description = "deep powerful roar with low frequency growl"
    }
}

# Apply preset if available
if ($presetConfigs.ContainsKey($SoundType)) {
    $preset = $presetConfigs[$SoundType]
    if (-not $Description -or $Description -eq "") {
        $Description = $preset.Description
    }
    if (-not $PSBoundParameters.ContainsKey('Duration')) {
        $Duration = $preset.Duration
    }
    if (-not $PSBoundParameters.ContainsKey('Frequency')) {
        $Frequency = $preset.Frequency
    }
    if (-not $PSBoundParameters.ContainsKey('Volume')) {
        $Volume = $preset.Volume
    }
    Write-Log "Applied preset: $SoundType" "INFO"
}

# Generate sound description using Ollama if needed
if (-not $Description -or $Description -eq "") {
    Write-Log "Generating sound description using Ollama..." "INFO"
    
    $systemPrompt = "You are a game sound designer for Starbound. Generate a creative description for a sound effect named '$SoundName' of type '$SoundType'.
    Include: sound characteristics (pitch, timbre, duration), audio style (sharp, smooth, mechanical, organic), and thematic elements.
    Return only a concise 2-3 sentence description suitable for procedural sound generation."
    
    if (Get-Command Invoke-OllamaRequest -ErrorAction SilentlyContinue) {
        try {
            $Description = Invoke-OllamaRequest -Prompt $systemPrompt -TaskType "analysis" -ResponseLength "standard" -ModelName $OllamaModel
        } catch {
            Write-Log "Ollama request failed: $_" "WARN"
        }
    }
    
    if (-not $Description -or $Description -eq "") {
        # Fallback to basic Ollama call
        $body = @{
            model = $OllamaModel
            prompt = $systemPrompt
            stream = $false
        } | ConvertTo-Json
        
        try {
            $response = Invoke-RestMethod -Uri "$OllamaUrl/api/generate" `
                -Method Post `
                -ContentType "application/json" `
                -Body $body `
                -ErrorAction Stop
            $Description = $response.response.Trim()
        } catch {
            Write-Log "Error calling Ollama: $_" "WARN"
            $Description = "A $SoundType sound effect for $SoundName"
        }
    }
}

Write-Log "Sound Description: $Description" "INFO"

# Create output directory
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
    Write-Log "Created output directory: $OutputDir" "INFO"
}

# Generate sound using Python script
$pythonScript = Join-Path $PSScriptRoot "generate_sound.py"
# Validate $OutputDir before Join-Path
$soundOutputPath = Join-Path $OutputDir "$SoundName.$Format"
 if ([string]::IsNullOrWhiteSpace($soundOutputPath)) {
    Write-Host "  [FAIL] soundOutputPath is null (${OutputDir}: '${OutputDir}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($soundOutputPath)) {
    Write-Host "  [FAIL] soundOutputPath is null (${OutputDir}: '${OutputDir}')" -ForegroundColor Red
    continue
}

# Check if Python is available
$pythonCmd = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonCmd = "python"
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    $pythonCmd = "python3"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $pythonCmd = "py"
}

if ($pythonCmd -and ($UsePython -or (Test-Path $pythonScript))) {
    Write-Log "Generating sound using Python..." "INFO"
    
    # Create Python script if it doesn't exist
    if (-not (Test-Path $pythonScript)) {
        $pythonScriptContent = @"
import numpy as np
import wave
import sys
import json
import os
from scipy import signal
import soundfile as sf

def generate_sound(sound_name, sound_type, description, duration, frequency, volume, output_path, format_type):
    sample_rate = 44100
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    
    # Generate base tone
    if 'low' in description.lower() or 'deep' in description.lower() or 'roar' in description.lower():
        freq = frequency * 0.5
    elif 'high' in description.lower() or 'sharp' in description.lower():
        freq = frequency * 2.0
    else:
        freq = frequency
    
    # Generate sound based on type
    if sound_type == 'Impact' or 'impact' in description.lower():
        # Sharp attack with quick decay
        wave_data = np.sin(2 * np.pi * freq * t) * np.exp(-t * 10)
        # Add noise for impact
        noise = np.random.normal(0, 0.1, len(t)) * np.exp(-t * 15)
        wave_data = wave_data + noise
    elif sound_type == 'Charge' or 'charge' in description.lower() or 'building' in description.lower():
        # Rising pitch
        freq_sweep = np.linspace(freq * 0.5, freq * 1.5, len(t))
        wave_data = np.sin(2 * np.pi * freq_sweep * t) * (1 - np.exp(-t * 2))
    elif sound_type == 'Magic' or 'magic' in description.lower() or 'ethereal' in description.lower():
        # Multiple harmonics with modulation
        wave_data = (np.sin(2 * np.pi * freq * t) + 
                    0.5 * np.sin(2 * np.pi * freq * 2 * t) +
                    0.3 * np.sin(2 * np.pi * freq * 3 * t)) * np.sin(2 * np.pi * 2 * t)
    elif sound_type == 'Mechanical' or 'mechanical' in description.lower():
        # Square wave with harmonics
        wave_data = signal.square(2 * np.pi * freq * t, duty=0.5) * 0.5
        wave_data += 0.3 * np.sin(2 * np.pi * freq * 2 * t)
    elif sound_type == 'Roar' or 'roar' in description.lower():
        # Low frequency with noise
        wave_data = np.sin(2 * np.pi * freq * 0.3 * t) * (1 - np.exp(-t * 0.5))
        noise = np.random.normal(0, 0.2, len(t)) * np.exp(-t * 1)
        wave_data = wave_data + noise
    elif sound_type == 'Whoosh' or 'whoosh' in description.lower():
        # White noise with frequency sweep
        noise = np.random.normal(0, 0.3, len(t))
        freq_sweep = np.linspace(freq * 2, freq * 0.5, len(t))
        wave_data = noise * np.sin(2 * np.pi * freq_sweep * t)
    else:
        # Default: simple sine wave with envelope
        wave_data = np.sin(2 * np.pi * freq * t) * (1 - np.exp(-t * 2)) * np.exp(-t * 1)
    
    # Apply volume
    wave_data = wave_data * volume
    
    # Normalize
    max_val = np.max(np.abs(wave_data))
    if max_val > 0:
        wave_data = wave_data / max_val * 0.95
    
    # Convert to 16-bit PCM
    wave_data = (wave_data * 32767).astype(np.int16)
    
    # Save as WAV or OGG
    if format_type == 'wav':
        with wave.open(output_path, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(wave_data.tobytes())
    else:  # OGG
        try:
            # Convert to float32 for soundfile
            wave_data_float = wave_data.astype(np.float32) / 32767.0
            sf.write(output_path, wave_data_float, sample_rate)
        except:
            # Fallback to WAV if OGG not supported
            with wave.open(output_path.replace('.ogg', '.wav'), 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(wave_data.tobytes())
            print(f"Note: OGG not available, saved as WAV instead")

if __name__ == '__main__':
    if len(sys.argv) < 9:
        print("Usage: generate_sound.py <name> <type> <description> <duration> <frequency> <volume> <output> <format>")
        sys.exit(1)
    
    generate_sound(
        sys.argv[1], sys.argv[2], sys.argv[3],
        float(sys.argv[4]), int(sys.argv[5]), float(sys.argv[6]),
        sys.argv[7], sys.argv[8]
    )
"@
        Set-Content -Path $pythonScript -Value $pythonScriptContent
        Write-Log "Created Python sound generation script" "INFO"
    }
    
    # Run Python script
    try {
        $pythonArgs = @(
            $pythonScript,
            $SoundName,
            $SoundType,
            $Description,
            $Duration.ToString(),
            $Frequency.ToString(),
            $Volume.ToString(),
            $soundOutputPath,
            $Format
        )
        
        $result = & $pythonCmd $pythonArgs 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Log "Sound generated successfully: $soundOutputPath" "INFO"
        } else {
            Write-Log "Python script error: $result" "ERROR"
            throw "Sound generation failed"
        }
    } catch {
        Write-Log "Error running Python script: $_" "ERROR"
        throw
    }
} else {
    # Fallback: write a real procedural WAV (never succeed with a .txt recipe alone)
    Write-Log "Python not available — writing procedural WAV via .NET" "WARN"
    if ([string]::IsNullOrWhiteSpace($soundOutputPath)) {
        $soundOutputPath = Join-Path $OutputDir "$SoundName.wav"
    }
    $outDir = Split-Path -Parent $soundOutputPath
    if ($outDir -and -not (Test-Path -LiteralPath $outDir)) {
        New-Item -ItemType Directory -Path $outDir -Force | Out-Null
    }
    $rate = 44100
    $n = [Math]::Max(1, [int]($Duration * $rate))
    $dataSize = $n * 2
    $fileSize = 36 + $dataSize
    $ms = New-Object System.IO.MemoryStream
    $bw = New-Object System.IO.BinaryWriter $ms
    $bw.Write([Text.Encoding]::ASCII.GetBytes("RIFF"))
    $bw.Write([int]$fileSize)
    $bw.Write([Text.Encoding]::ASCII.GetBytes("WAVEfmt "))
    $bw.Write([int]16)
    $bw.Write([int16]1)
    $bw.Write([int16]1)
    $bw.Write([int]$rate)
    $bw.Write([int]($rate * 2))
    $bw.Write([int16]2)
    $bw.Write([int16]16)
    $bw.Write([Text.Encoding]::ASCII.GetBytes("data"))
    $bw.Write([int]$dataSize)
    $freq = if ($Frequency -gt 0) { [double]$Frequency } else { 440.0 }
    for ($i = 0; $i -lt $n; $i++) {
        $t = $i / $rate
        $env = [Math]::Min(1.0, $t * 8.0) * [Math]::Max(0.0, 1.0 - $t / [Math]::Max(0.01, $Duration))
        $sample = [int16]([Math]::Max(-32767, [Math]::Min(32767, 12000 * $env * [Math]::Sin(2 * [Math]::PI * $freq * $t))))
        $bw.Write($sample)
    }
    $bw.Flush()
    [IO.File]::WriteAllBytes($soundOutputPath, $ms.ToArray())
    $bw.Close(); $ms.Close()
    Write-Log "Procedural WAV written: $soundOutputPath" "INFO"
}

Write-Log "Sound generation complete!" "INFO"
Write-Log "Output: $soundOutputPath" "INFO"

# Return metadata
return @{
    SoundName = $SoundName
    SoundType = $SoundType
    Description = $Description
    OutputPath = $soundOutputPath
    Format = $Format
}
