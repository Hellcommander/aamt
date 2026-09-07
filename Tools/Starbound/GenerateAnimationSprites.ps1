#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate animation spritesheets for all animations in the mod.
    
.DESCRIPTION
    Generates animation spritesheets with .animation and .frames files for:
    - Magitech device animations
    - Spell casting animations
    - Status effect animations
    - Custom animations
    
.PARAMETER ModPath
    Path to the mod directory
    
.PARAMETER OllamaModel
    Ollama model to use
    
.PARAMETER UseCppBackend
    Use C++ backend for generation
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$ModPath = "F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery",
    
    [Parameter(Mandatory=$false)]
    [string]$OllamaModel = "codellama:7b-instruct",
    
    [Parameter(Mandatory=$false)]
    [bool]$UseCppBackend = $true)

$ErrorActionPreference = "Stop"

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$assetGenerator = Join-Path $PSScriptRoot "StarboundOllamaAssetGenerator.ps1"

# Validate ModPath is not empty
if ([string]::IsNullOrWhiteSpace($ModPath)) {
    Write-Host "Error: ModPath cannot be empty" -ForegroundColor Red
    Write-Host "  Please provide a valid mod path or use the default" -ForegroundColor Gray
    exit 1
}

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Animation Spritesheet Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$animations = @(
    @{
        Id = "magitech_device"
        Name = "Magitech Device Activation"
        Description = "Magitech device activation animation with pulsing energy, blue and purple colors, 6 frames showing device powering up"
        FrameCount = 6
        AnimationCycle = 1.0
        AnimationType = "DeviceActivation"
        FrameSize = @(64, 64)
    },
    @{
        Id = "spell_cast"
        Name = "Spell Cast Animation"
        Description = "Spell casting animation with growing magical energy, swirling particles, arcane symbols appearing"
        FrameCount = 8
        AnimationCycle = 0.6
        AnimationType = "SpellCast"
        FrameSize = @(48, 48)
    },
    @{
        Id = "magic_aura"
        Name = "Magic Aura"
        Description = "Magical aura status effect animation, shimmering energy field, pulsing glow"
        FrameCount = 4
        AnimationCycle = 0.8
        AnimationType = "StatusEffect"
        FrameSize = @(32, 32)
    },
    @{
        Id = "alchemical_reaction"
        Name = "Alchemical Reaction"
        Description = "Alchemical reaction animation, mixing chemicals, color changes, bubbling effects"
        FrameCount = 10
        AnimationCycle = 1.2
        AnimationType = "SpellCast"
        FrameSize = @(48, 48)
    },
    @{
        Id = "portal_opening"
        Name = "Portal Opening"
        Description = "Portal opening animation, swirling void energy, dimensional rift forming"
        FrameCount = 12
        AnimationCycle = 1.5
        AnimationType = "SpellCast"
        FrameSize = @(64, 64)
    }
)

$generated = 0
$failed = 0

foreach ($anim in $animations) {
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  Generating: $($anim.Name)" -ForegroundColor Cyan
    Write-Host "  ID: $($anim.Id)" -ForegroundColor Gray
    Write-Host "  Frames: $($anim.FrameCount)" -ForegroundColor Gray
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
    
    try {
        # Validate ModPath before creating output directory
        if ([string]::IsNullOrWhiteSpace($ModPath)) {
            Write-Host "  [FAIL] Cannot generate animation $($anim.Id): ModPath is null or empty" -ForegroundColor Red
            $failed++
            continue
        }
        
        # Validate $ModPath before Join-Path
$outputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($outputDir)) {
            Write-Host "  [FAIL] outputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
            continue
        }
 if ([string]::IsNullOrWhiteSpace($outputDir)) {
            Write-Host "  [FAIL] outputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
            continue
        }
        if ([string]::IsNullOrWhiteSpace($outputDir)) {
            Write-Host "  [FAIL] Cannot create output directory: ModPath resulted in null path" -ForegroundColor Red
            $failed++
            continue
        }
        
        $params = @{
            AssetType = "AnimationSprite"
            AssetName = $anim.Id
            Prompt = $anim.Description
            OllamaModel = $OllamaModel
            OutputDir = $outputDir
        }
        
        # Add animation-specific parameters
        $paramHashtable = @{
            FrameWidth = $anim.FrameSize[0]
            FrameHeight = $anim.FrameSize[1]
            FrameCount = $anim.FrameCount
            AnimationCycle = $anim.AnimationCycle
            AnimationType = $anim.AnimationType
        }
        $params['Parameters'] = $paramHashtable
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "✓ Generated animation: $($anim.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "✗ Failed to generate animation: $($anim.Name): $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Generation Complete" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Generated: $generated animations" -ForegroundColor Green
Write-Host "Failed: $failed animations" -ForegroundColor $(if ($failed -gt 0) { "Red" } else { "Green" })
Write-Host ""
Write-Host "Animations saved to: $(Join-Path $ModPath 'assets\animations')" -ForegroundColor Gray
Write-Host ""
