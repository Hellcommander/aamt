<#
.SYNOPSIS
    Generate a Transcendence/game WAV with Stable Audio 3.

.EXAMPLE
    .\Generate-StableAudio.ps1 -Prompt "short spaceship laser shot" -Output ".\TestOutput\laser.wav" -Seconds 2

.EXAMPLE
    .\Generate-StableAudio.ps1 -Model small-sfx -Prompt "metal airlock clang" -Output ".\TestOutput\airlock.wav"
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Prompt,
    [Parameter(Mandatory = $true)][string]$Output,
    [string]$Model = "medium",
    [string]$NegativePrompt = "Low quality, muffled, distorted, silence",
    [double]$Seconds = 4.0,
    [int]$Steps = -1,
    [int]$Seed = -1,
    [string]$PythonPath = ""
)

$ErrorActionPreference = "Stop"
$ToolsRoot = $PSScriptRoot

$envFile = "E:\tools\stable-audio\aamt_stable_audio_env.ps1"
if (Test-Path $envFile) { . $envFile }

$mod = Join-Path $ToolsRoot "Shared\StableAudioIntegration.psm1"
Import-Module $mod -Force

$seedArg = $null
if ($Seed -ge 0) { $seedArg = $Seed }
$stepsArg = $null
if ($Steps -gt 0) { $stepsArg = $Steps }

$path = Invoke-StableAudioGeneration `
    -Prompt $Prompt `
    -OutputPath $Output `
    -Model $Model `
    -NegativePrompt $NegativePrompt `
    -Seconds $Seconds `
    -Steps $stepsArg `
    -Seed $seedArg `
    -PythonPath $PythonPath `
    -Verbose

Write-Host "OK: $path" -ForegroundColor Green
