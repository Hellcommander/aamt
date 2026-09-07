# Asset Generation Shared Settings (example)
# Copy to AssetGenerationSettings.ps1 beside this file and edit paths for your machine.
#   copy AssetGenerationSettings.example.ps1 AssetGenerationSettings.ps1
#
# Prefer TranscendenceTools.ini for game/output paths when a tool supports it.

function Load-AssetGenerationSettings {
    param([string]$ScriptPath = $MyInvocation.ScriptName)
    if ([string]::IsNullOrEmpty($ScriptPath)) {
        $ScriptPath = $MyInvocation.MyCommand.Path
    }
    $scriptDir = Split-Path -Parent $ScriptPath
    $toolsRoot = $scriptDir
    while ($toolsRoot -and (Split-Path -Leaf $toolsRoot) -ne "Tools") {
        $parent = Split-Path -Parent $toolsRoot
        if ($parent -eq $toolsRoot) { break }
        $toolsRoot = $parent
    }
    $settingsPath = Join-Path $toolsRoot "AssetGenerationSettings.ps1"
    if (Test-Path $settingsPath) {
        . $settingsPath
        return $true
    }
    return $false
}

$script:ImageMagickPath = "C:\tools\ImageMagick"
$script:ImageMagickExe = Join-Path $script:ImageMagickPath "magick.exe"

function Get-ImageMagickPath {
    if (Test-Path $script:ImageMagickExe) { return $script:ImageMagickExe }
    $magickCommand = Get-Command "magick" -ErrorAction SilentlyContinue
    if ($magickCommand) { return $magickCommand.Source }
    return $null
}

function Test-ImageMagickAvailable {
    return ($null -ne (Get-ImageMagickPath))
}

$script:DefaultOutputDir = "C:\Output"
$script:SpellstoneOutputDir = Join-Path $script:DefaultOutputDir "items\spellstones"

$script:OllamaUrl = "http://localhost:11434"
$script:OllamaModel = ""
$script:PlanningModel = ""
$script:VisualModel = ""

$script:DefaultVariants = 3
$script:DefaultAnimationFrames = 8

$script:StableAudioDir = if ($env:AAMT_STABLE_AUDIO_DIR) { $env:AAMT_STABLE_AUDIO_DIR } else { "C:\tools\stable-audio" }
$script:StableAudioModel = if ($env:AAMT_STABLE_AUDIO_MODEL) { $env:AAMT_STABLE_AUDIO_MODEL } else { "medium" }
$script:StableAudioPython = if ($env:AAMT_STABLE_AUDIO_PYTHON) { $env:AAMT_STABLE_AUDIO_PYTHON } else { "python" }

$script:HfTokenProfileMedia = if ($env:AAMT_HF_TOKEN_MEDIA) { $env:AAMT_HF_TOKEN_MEDIA } else { "SD3.5 Token" }
$script:HfTokenProfileTraining = if ($env:AAMT_HF_TOKEN_TRAINING) { $env:AAMT_HF_TOKEN_TRAINING } else { "Custom Modul for creation" }
