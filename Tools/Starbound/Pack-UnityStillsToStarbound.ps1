#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Pack Magi-Tech Unity AI stills into Starbound spritesheets + .frames files.

.DESCRIPTION
    Unity generated one static PNG per run (UUID filenames in <mod>/images).
    This wrapper runs pack_unity_stills_to_starbound.py which:
      - knocks out baked white/grey backgrounds
      - fits each still to a Starbound tile
      - builds an 8-frame idle-glow strip
      - writes .frames metadata
      - optionally copies mapped icons onto item/object paths

.PARAMETER ModPath
    Magi-Tech mod root (must contain an images folder)

.PARAMETER Install
    Copy mapped icons/sheets into assets/items/sprites and item folders

.PARAMETER FrameCount
    Idle frames per sheet (default 8)

.PARAMETER SkipActionCycles
    Pack idle icons only (skip Magi-Tech SD animation production)

.PARAMETER ProceduralCycles
    Fall back to the Python pose expander instead of the SD pipeline
#>
[CmdletBinding()]
param(
    [string]$ModPath = "F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery",
    [switch]$Install,
    [int]$FrameCount = 8,
    [switch]$SkipActionCycles,
    [switch]$ProceduralCycles
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pyScript = Join-Path $scriptDir "pack_unity_stills_to_starbound.py"

if (-not (Test-Path $pyScript)) {
    throw "Missing $pyScript"
}
if (-not (Test-Path (Join-Path $ModPath "images"))) {
    throw "images folder not found: $ModPath\images"
}

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { $python = Get-Command python3 -ErrorAction SilentlyContinue }
if (-not $python) { throw "Python not found" }

$pyArgs = @($pyScript, "--mod-path", $ModPath, "--frames", "$FrameCount")
if ($Install) { $pyArgs += "--install" }

Write-Host "Packing Unity stills from $ModPath\images" -ForegroundColor Cyan
& $python.Source @pyArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $SkipActionCycles) {
    $produce = Join-Path $scriptDir "Produce-UnityStillAnimations.ps1"
    if ((Test-Path $produce) -and -not $ProceduralCycles) {
        Write-Host "Producing animation sheets via Magi-Tech SD pipeline (not Python pose fakes)" -ForegroundColor Cyan
        & $produce -ModPath $ModPath -FrameCount $FrameCount -AutoStartSd
        if ($LASTEXITCODE -ne 0) { Write-Host "SD animation producer reported errors; continuing install." -ForegroundColor Yellow }
    } else {
        $expand = Join-Path $scriptDir "expand_unity_sheets_to_action_cycles.py"
        Write-Host "ProceduralCycles: expanding idle stills in Python (fallback)" -ForegroundColor Yellow
        $exArgs = @($expand, "--mod-path", $ModPath)
        if ($Install) { $exArgs += "--install" }
        & $python.Source @exArgs
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }

    $hitboxes = Join-Path $scriptDir "generate_mech_hitboxes.py"
    if (Test-Path $hitboxes) {
        Write-Host "Generating mech/minion hitboxes from sheets" -ForegroundColor Cyan
        & $python.Source @($hitboxes, "--mod-path", $ModPath)
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }

    $forms = Join-Path $scriptDir "install_mech_forms.py"
    if (Test-Path $forms) {
        Write-Host "Installing mech sheets onto Form.json ids" -ForegroundColor Cyan
        & $python.Source @($forms, "--mod-path", $ModPath)
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }

    $items = Join-Path $scriptDir "install_item_sheets.py"
    if (Test-Path $items) {
        Write-Host "Installing packed sheets onto items, reagents, and stations" -ForegroundColor Cyan
        & $python.Source @($items, "--mod-path", $ModPath)
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
}
exit 0
