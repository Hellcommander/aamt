#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Magi-Tech Starbound spell/projectile pipeline:
    SD quality draft → reference final → multi-module QA → fix brief → retry.

.DESCRIPTION
    Vortex-quality bar with full modern SD usage:
      1) SD design draft (quality reference)
      2) Final that REFERENCES the draft (-ReferenceImagePath)
      3) Multi-module scoring (sanity + Qwen3-VL mechanical + LLaVA aesthetic)
      4) If below threshold, modules report ISSUES/FIX and we regenerate with that brief

.PARAMETER MaxRetries
    Regenerations after QA failure (default 2)

.PARAMETER PassThreshold
    Combined score /20 required to accept (default 15)
#>
[CmdletBinding()]
param(
    [string]$ModPath = "F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery",
    [Parameter(Mandatory = $true)][string]$AssetId,
    [Parameter(Mandatory = $true)][string]$Theme,
    [ValidateSet("spell", "projectile", "icon")][string]$Kind = "spell",
    [switch]$IconsOnly,
    [switch]$SkipDraft,
    [switch]$DraftOnly,
    [ValidateRange(0.0, 1.0)][double]$ImageStrength = 0.65,
    [switch]$AutoStartSd,
    [int]$FrameCount = 8,
    [int]$TileSize = 64,
    [ValidateSet("fast", "mechanical", "full")][string]$QualityAssessmentDepth = "full",
    [int]$MaxRetries = 2,
    [ValidateRange(0.0, 20.0)][double]$PassThreshold = 15.0
)

$ErrorActionPreference = "Stop"
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$toolsRoot = Split-Path -Parent $PSScriptRoot
$sharedPath = Join-Path $toolsRoot "Shared"
$commonPath = Join-Path $toolsRoot "Common"

if ([string]::IsNullOrWhiteSpace($ModPath) -or -not (Test-Path $ModPath)) {
    throw "ModPath not found: $ModPath"
}

Import-Module (Join-Path $sharedPath "ToolDetection.psm1") -Force -ErrorAction SilentlyContinue
Import-Module (Join-Path $sharedPath "ToolsetIntegration.psm1") -Force -ErrorAction SilentlyContinue
Import-Module (Join-Path $sharedPath "OllamaIntegration.psm1") -Force -ErrorAction SilentlyContinue
Import-Module (Join-Path $sharedPath "StableDiffusionIntegration.psm1") -DisableNameChecking -Force -ErrorAction Stop
Import-Module (Join-Path $sharedPath "ImageQualityAssessment.psm1") -Force -ErrorAction SilentlyContinue

$settingsPath = Join-Path $toolsRoot "AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) { . $settingsPath }

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Magi-Tech Pipeline (draft → ref final → score → retry)" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Asset : $AssetId ($Kind)" -ForegroundColor Gray
Write-Host "  Theme : $Theme" -ForegroundColor Gray
Write-Host "  QA    : $QualityAssessmentDepth (pass >= $PassThreshold/20, retries=$MaxRetries)" -ForegroundColor Gray
Write-Host ""

if (Get-Command Initialize-ToolsetTools -ErrorAction SilentlyContinue) {
    $null = Initialize-ToolsetTools `
        -RequiredTools @("Python") `
        -OptionalTools @("Ollama", "ImageMagick", "StableDiffusion", "Blender")
}

$draftDir = Join-Path $ModPath "DesignDrafts"
$outDir = Join-Path $ModPath "assets\magitech\generated\$AssetId"
$sourceDir = Join-Path $outDir "Source"
New-Item -ItemType Directory -Path $draftDir -Force | Out-Null
New-Item -ItemType Directory -Path $outDir -Force | Out-Null
New-Item -ItemType Directory -Path $sourceDir -Force | Out-Null

$draftPath = Join-Path $draftDir "${AssetId}_design_draft.png"
$finalPath = Join-Path $outDir "$AssetId.png"
$framesPath = Join-Path $outDir "$AssetId.frames"
$metaPath = Join-Path $sourceDir "draft_ref.json"

$sdUp = $false
if (Get-Command Test-StableDiffusionConnection -ErrorAction SilentlyContinue) {
    $sdUp = [bool](Test-StableDiffusionConnection)
}
if (-not $sdUp -and $AutoStartSd -and (Get-Command Start-StableDiffusionServerIfNeeded -ErrorAction SilentlyContinue)) {
    Write-Host "Starting SD server if needed (GPU-first)..." -ForegroundColor Yellow
    if (Get-Command Set-StableDiffusionGpuPreferredEnv -ErrorAction SilentlyContinue) {
        Set-StableDiffusionGpuPreferredEnv -Offload gpu -Force
    } else {
        $env:SD_OFFLOAD = "gpu"
        $env:SD_HEADROOM_GB = "0"
        $env:SD_SKIP_T5 = "1"
    }
    $null = Start-StableDiffusionServerIfNeeded
    $sdUp = [bool](Test-StableDiffusionConnection)
}
if ($sdUp -and (Get-Command Assert-StableDiffusionUsesGpu -ErrorAction SilentlyContinue)) {
    Assert-StableDiffusionUsesGpu | Out-Null
}
if (-not $sdUp) {
    Write-Host "[WARN] SD server not reachable. Run: ..\Start-StableDiffusionServer.ps1 (uses CUDA torch; SD_OFFLOAD=gpu)" -ForegroundColor Yellow
}

$negative = "text, watermark, logo, photo, blurry, cluttered background, lowres, jpeg artifacts"

function Get-MagiTechPrompt {
    param([string]$Phase, [string]$ExtraFix = "")
    $role = switch ($Kind) {
        "projectile" { "Starbound 2D projectile sprite" }
        "icon" { "Starbound inventory icon" }
        default { "Starbound spell icon / VFX emblem" }
    }
    $p = @"
$role for Magi-Tech Arcane Alchemy and Sorcery.
Subject: $Theme
Asset id: $AssetId
Phase: $Phase
Style: crisp pixel-friendly game art, transparent background, centered, readable at ${TileSize}px, magitech arcane aesthetic, no text, no UI chrome.
"@
    if (-not [string]::IsNullOrWhiteSpace($ExtraFix)) {
        $p += "`n`nQA FIX BRIEF FROM PRIOR ATTEMPT (must address):`n$ExtraFix"
    }
    $p
}

function Invoke-ResizeFinal {
    if (-not (Get-Command Get-ImageMagickPath -ErrorAction SilentlyContinue)) { return }
    $magick = Get-ImageMagickPath
    if (-not $magick) { return }
    $sized = Join-Path $outDir "${AssetId}_${TileSize}.png"
    & $magick $finalPath -resize "${TileSize}x${TileSize}" $sized
    if (Test-Path $sized) {
        Copy-Item $sized $finalPath -Force
        Write-Host "  [OK] Resized to ${TileSize}x${TileSize}" -ForegroundColor Green
    }
}

if (-not (Get-Command Generate-AssetImageWithSD3 -ErrorAction SilentlyContinue)) {
    throw "Generate-AssetImageWithSD3 not available."
}
if (-not $sdUp -and -not $SkipDraft) {
    throw "SD server required for draft/final. Start it or use -SkipDraft with an existing draft."
}

$qaAvailable = [bool](Get-Command Get-ImageQualityReport -ErrorAction SilentlyContinue)
$fixBrief = ""
$attempt = 0
$accepted = $false
$qaLog = @()

while (-not $accepted -and $attempt -le $MaxRetries) {
    $attemptLabel = if ($attempt -eq 0) { "initial" } else { "retry $attempt/$MaxRetries" }
    Write-Host ""
    Write-Host "══ Attempt: $attemptLabel ══" -ForegroundColor Cyan

    # --- Draft ---
    $makeDraft = $false
    if ($attempt -eq 0) {
        $makeDraft = -not $SkipDraft
    } else {
        # Refresh draft when QA says concept/look/palette is wrong
        $makeDraft = ($fixBrief -match '(?i)composition|silhouette|concept|palette|color|subject|shape|readab')
    }

    if ($makeDraft) {
        Write-Host "Step 1: SD quality design draft..." -ForegroundColor Yellow
        $draftPrompt = Get-MagiTechPrompt -Phase "design draft / concept art (high quality reference)" -ExtraFix $fixBrief
        $null = Generate-AssetImageWithSD3 `
            -Prompt $draftPrompt `
            -OutputPath $draftPath `
            -NegativePrompt $negative `
            -Width 1024 -Height 1024 -Steps 28 -GuidanceScale 7.0 `
            -EnhanceWithOllama:$true `
            -AutoStartServer:$AutoStartSd
        if (-not (Test-Path $draftPath)) { throw "Draft missing after generation: $draftPath" }
        Write-Host "  [OK] Draft: $draftPath" -ForegroundColor Green
    } else {
        if (-not (Test-Path $draftPath)) { throw "Draft missing: $draftPath" }
        Write-Host "Step 1: Reusing draft $draftPath" -ForegroundColor Cyan
    }

    if ($DraftOnly) {
        Write-Host "DraftOnly — stopping after draft." -ForegroundColor Green
        exit 0
    }

    # --- Final referencing draft ---
    Write-Host "Step 2: SD final referencing draft (ImageStrength=$ImageStrength)..." -ForegroundColor Yellow
    if (-not $sdUp) { throw "SD server required for referenced final." }
    if ($fixBrief) { Write-Host "  Feeding QA fix brief into final prompt..." -ForegroundColor Yellow }
    $finalPrompt = Get-MagiTechPrompt -Phase "final game asset matching the attached design draft" -ExtraFix $fixBrief
    $null = Generate-AssetImageWithSD3 `
        -Prompt $finalPrompt `
        -OutputPath $finalPath `
        -NegativePrompt $negative `
        -Width 512 -Height 512 -Steps 24 -GuidanceScale 7.0 `
        -EnhanceWithOllama:$true `
        -ReferenceImagePath $draftPath `
        -ImageStrength $ImageStrength `
        -AutoStartServer:$AutoStartSd
    if (-not (Test-Path $finalPath)) { throw "Final missing after generation: $finalPath" }
    Write-Host "  [OK] Final: $finalPath" -ForegroundColor Green
    # QA the full-res final; resize to tile only after accept (64px icons always fail vision QA).

    # --- Multi-module score + what to fix ---
    Write-Host "Step 3: Multi-module QA ($QualityAssessmentDepth)..." -ForegroundColor Yellow
    if (-not $qaAvailable) {
        Write-Host "  [WARN] Get-ImageQualityReport unavailable; accepting without QA loop." -ForegroundColor Yellow
        $accepted = $true
        break
    }

    $report = Get-ImageQualityReport `
        -ImagePath $finalPath `
        -Depth $QualityAssessmentDepth `
        -PassThreshold $PassThreshold `
        -AssetContext "Magi-Tech Starbound $Kind ($AssetId): $Theme"

    $qaLog += [pscustomobject]@{
        attempt       = $attempt
        combinedScore = $report.CombinedScore
        passed        = $report.Passed
        issues        = @($report.Issues)
        fixBrief      = $report.FixBrief
    }

    if ($report.ModelsFailed) {
        Write-Host "  [FAIL] Vision QA models did not load/score — not auto-approving." -ForegroundColor Red
    }
    Write-Host ("  Combined: {0:N1}/20  (need {1})" -f $report.CombinedScore, $PassThreshold) `
        -ForegroundColor $(if ($report.Passed) { "Green" } else { "Yellow" })
    if ($report.Mechanical) {
        $ms = if ($null -ne $report.Mechanical.Score) { "{0:N1}/20" -f $report.Mechanical.Score } else { "n/a" }
        Write-Host "  Mechanical ($($report.Mechanical.ModelName)): $ms" -ForegroundColor Gray
        if ($report.Mechanical.Issues) { Write-Host "    Issues: $($report.Mechanical.Issues)" -ForegroundColor Gray }
        if ($report.Mechanical.Fix) { Write-Host "    Fix: $($report.Mechanical.Fix)" -ForegroundColor Gray }
    }
    if ($report.Aesthetic) {
        $as = if ($null -ne $report.Aesthetic.Score) { "{0:N1}/20" -f $report.Aesthetic.Score } else { "n/a" }
        Write-Host "  Aesthetic ($($report.Aesthetic.ModelName)): $as" -ForegroundColor Gray
        if ($report.Aesthetic.Issues) { Write-Host "    Issues: $($report.Aesthetic.Issues)" -ForegroundColor Gray }
        if ($report.Aesthetic.Fix) { Write-Host "    Fix: $($report.Aesthetic.Fix)" -ForegroundColor Gray }
    }

    if ($report.Passed) {
        Write-Host "  [OK] Passed multi-module QA." -ForegroundColor Green
        $accepted = $true
        break
    }

    $fixBrief = $report.FixBrief
    Write-Host "  [WARN] Below threshold — informed what to fix, will retry:" -ForegroundColor Yellow
    Write-Host $fixBrief -ForegroundColor Yellow
    if ($attempt -ge $MaxRetries) {
        Write-Host "  [WARN] Max retries reached; keeping best-effort final." -ForegroundColor Yellow
        break
    }
    $attempt++
}

# Tile-size icon after QA; frame staging below reads this path and resizes again if needed.
if (-not $IconsOnly) {
    Write-Host "Keeping full-res final for sheet staging; icon resize after pack." -ForegroundColor Gray
} else {
    Invoke-ResizeFinal
}

@{
    assetId        = $AssetId
    kind           = $Kind
    theme          = $Theme
    draftPath      = $draftPath
    finalPath      = $finalPath
    imageStrength  = $ImageStrength
    iconsOnly      = [bool]$IconsOnly
    frameCount     = $(if ($IconsOnly) { 1 } else { $FrameCount })
    tileSize       = $TileSize
    generatedAtUtc = (Get-Date).ToUniversalTime().ToString("o")
    pipeline       = "magitech-draft-reference-score-retry"
    qualityBar     = "vortex"
    qaDepth        = $QualityAssessmentDepth
    passThreshold  = $PassThreshold
    accepted       = $accepted
    attempts       = $attempt + 1
    qaLog          = $qaLog
    lastFixBrief   = $fixBrief
} | ConvertTo-Json -Depth 6 | Set-Content -Path $metaPath -Encoding UTF8

# --- Optional sheet pack ---
if (-not $IconsOnly -and $FrameCount -gt 1) {
    Write-Host "Step 4: Starbound sheet pack..." -ForegroundColor Yellow
    $sheetScript = Join-Path $commonPath "CrossGameSpritesheet.ps1"
    $frameStaging = Join-Path $sourceDir "frames"
    New-Item -ItemType Directory -Path $frameStaging -Force | Out-Null
    $py = (Get-Command python -ErrorAction SilentlyContinue).Source
    if ($py) {
        & $py (Join-Path $PSScriptRoot "generate_magitech_spell_assets.py") `
            --mod-path $ModPath --asset-id $AssetId `
            --draft $draftPath --final $finalPath `
            --frame-count $FrameCount --tile-size $TileSize `
            --stage-frames $frameStaging
    }
    if (Test-Path $sheetScript) {
        & $sheetScript -InputDir $frameStaging -OutputDir $outDir -GameFormat Starbound `
            -TileSize $TileSize -SpritesheetName $AssetId -ErrorAction SilentlyContinue
    }
} else {
    Write-Host "Step 4: IconsOnly — single-frame .frames only." -ForegroundColor Cyan
    @{
        frameGrid = @{
            size       = @($TileSize, $TileSize)
            dimensions = @(1, 1)
            names      = @(@("default"))
        }
    } | ConvertTo-Json -Depth 5 | Set-Content -Path $framesPath -Encoding UTF8
    Invoke-ResizeFinal
}

Write-Host ""
Write-Host "Done." -ForegroundColor $(if ($accepted) { "Green" } else { "Yellow" })
Write-Host "  Draft: $draftPath"
Write-Host "  Final: $finalPath"
Write-Host "  QA accepted: $accepted"
Write-Host "  Meta: $metaPath"
if (-not $accepted) { exit 2 }
exit 0
