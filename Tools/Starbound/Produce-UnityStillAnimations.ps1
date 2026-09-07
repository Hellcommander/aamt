#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Produce Starbound animation sheets from packed Unity stills or Pixelorama .pxo.

.DESCRIPTION
    -Backend sd (default): Magi-Tech SD draft→reference→pack pipeline, then
    StarboundAnimationGenerator for .animation. Does NOT invent walk/attack poses.
    -Backend pixelorama: headless export of authored .pxo via Shared pixels stage
    (produce_pixelorama_sheets.py). Pixelorama does not invent frames from a still.

.PARAMETER Limit
    Max assets to generate this run (0 = all in the default item set).
#>
[CmdletBinding()]
param(
    [string]$ModPath = "F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery",
    [int]$FrameCount = 8,
    [int]$TileSize = 64,
    [int]$Limit = 0,
    [switch]$AutoStartSd,
    [switch]$SkipExisting,
    [ValidateSet("sd", "pixelorama")][string]$Backend = "sd",
    [ValidateSet("fast", "mechanical", "full")][string]$QualityAssessmentDepth = "fast",
    [string[]]$AssetIds = @()
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pipeline = Join-Path $scriptDir "Generate-MagiTechSpellPipeline.ps1"
$animGen = Join-Path $scriptDir "StarboundAnimationGenerator.ps1"
$packer = Join-Path $scriptDir "StarboundSpritesheetPacker.ps1"
$installItems = Join-Path $scriptDir "install_item_sheets.py"
$startSd = Join-Path (Split-Path $scriptDir -Parent) "Start-StableDiffusionServer.ps1"
$pixelorama = Join-Path $scriptDir "Produce-PixeloramaSheets.ps1"

if ($Backend -eq "pixelorama") {
    if (-not (Test-Path $pixelorama)) { throw "Missing $pixelorama" }
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  Produce animations via Pixelorama (Shared pixels stage)" -ForegroundColor Cyan
    Write-Host "  Tile: $TileSize" -ForegroundColor Gray
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    $pxArgs = @{
        ModPath = $ModPath
        TileSize = $TileSize
        Limit = $Limit
        SkipExisting = $SkipExisting
    }
    if ($AssetIds.Count -gt 0) { $pxArgs.AssetIds = $AssetIds }
    & $pixelorama @pxArgs
    exit $LASTEXITCODE
}

if (-not (Test-Path $pipeline)) { throw "Missing $pipeline" }
if (-not (Test-Path $animGen)) { throw "Missing $animGen" }

$sheets = Join-Path $ModPath "assets\magitech\unity_sheets"
$draftDir = Join-Path $ModPath "DesignDrafts"
New-Item -ItemType Directory -Path $draftDir -Force | Out-Null

# Item stills we actually wired — not the 126 mech placeholders.
$jobs = @(
    @{ Id = "grenade_fire"; Batch = "grenade"; Kind = "projectile"; Theme = "incendiary alchemical grenade, fire, Magi-Tech Starbound sprite" }
    @{ Id = "grenade_frost"; Batch = "grenade"; Kind = "projectile"; Theme = "frost alchemical grenade, ice, Magi-Tech Starbound sprite" }
    @{ Id = "grenade_acid"; Batch = "grenade"; Kind = "projectile"; Theme = "acid alchemical grenade, Magi-Tech Starbound sprite" }
    @{ Id = "grenade_storm"; Batch = "grenade"; Kind = "projectile"; Theme = "storm alchemical grenade, lightning, Magi-Tech Starbound sprite" }
    @{ Id = "grenade_shadow"; Batch = "grenade"; Kind = "projectile"; Theme = "shadow alchemical grenade, Magi-Tech Starbound sprite" }
    @{ Id = "chemicalgrenadeammo"; Batch = "grenade"; Kind = "icon"; Theme = "chemical grenade ammo canister, Magi-Tech" }
    @{ Id = "chemicalgrenadeammo_mk2"; Batch = "grenade"; Kind = "icon"; Theme = "mk2 chemical grenade ammo, Magi-Tech" }
    @{ Id = "chemicalgrenadeammo_mk3"; Batch = "grenade"; Kind = "icon"; Theme = "mk3 chemical grenade ammo, Magi-Tech" }
    @{ Id = "chemicalgrenadelauncher"; Batch = "grenade"; Kind = "icon"; Theme = "alchemical grenade launcher gun, Magi-Tech Starbound weapon" }
    @{ Id = "chemicalgrenadelauncher_tech2"; Batch = "grenade"; Kind = "icon"; Theme = "tech2 alchemical grenade launcher, Magi-Tech" }
    @{ Id = "chemicalgrenadelauncher_tech3"; Batch = "grenade"; Kind = "icon"; Theme = "tech3 alchemical grenade launcher, Magi-Tech" }
    @{ Id = "flamelord_grenadegun"; Batch = "grenade"; Kind = "icon"; Theme = "flame lord grenade gun, Magi-Tech" }
    @{ Id = "grenade_15"; Batch = "grenade"; Kind = "icon"; Theme = "empty reagent vial, glass, Magi-Tech"; Alias = "reagent_vial" }
    @{ Id = "grenade_16"; Batch = "grenade"; Kind = "icon"; Theme = "fire essence reagent vial, Magi-Tech"; Alias = "reagent_fireessence" }
    @{ Id = "grenade_17"; Batch = "grenade"; Kind = "icon"; Theme = "ice crystal reagent vial, Magi-Tech"; Alias = "reagent_icecrystal" }
    @{ Id = "grenade_18"; Batch = "grenade"; Kind = "icon"; Theme = "poison cloud reagent vial, Magi-Tech"; Alias = "reagent_poisoncloud" }
    @{ Id = "grenade_19"; Batch = "grenade"; Kind = "icon"; Theme = "oil powder reagent vial, Magi-Tech"; Alias = "reagent_oilpowder" }
    @{ Id = "grenade_20"; Batch = "grenade"; Kind = "icon"; Theme = "catalyst reagent vial, Magi-Tech"; Alias = "reagent_catalyst" }
    @{ Id = "magitechbasicwand"; Batch = "weapon"; Kind = "icon"; Theme = "magitech wand, arcane staff-wand, Starbound held weapon" }
    @{ Id = "magitechbasicstaff"; Batch = "weapon"; Kind = "icon"; Theme = "magitech staff, Starbound held weapon" }
    @{ Id = "magitechbasicorb"; Batch = "weapon"; Kind = "icon"; Theme = "magitech orb, floating crystal, Starbound held weapon" }
    @{ Id = "magitechdevice"; Batch = "weapon"; Kind = "icon"; Theme = "magitech arcane device, activation glow, Starbound held weapon" }
    @{ Id = "deviceworkbench"; Batch = "station"; Kind = "spell"; Theme = "magitech device workbench crafting station, Starbound object" }
    @{ Id = "magitechspellcraftingstation"; Batch = "station"; Kind = "spell"; Theme = "magitech spell crafting station, crystals, Starbound object" }
    @{ Id = "spellstone_fire"; Batch = "spellstone"; Kind = "icon"; Theme = "fire spellstone crystal, Magi-Tech" }
    @{ Id = "spellstone_ice"; Batch = "spellstone"; Kind = "icon"; Theme = "ice spellstone crystal, Magi-Tech" }
    @{ Id = "spellstone_electric"; Batch = "spellstone"; Kind = "icon"; Theme = "lightning spellstone crystal, Magi-Tech" }
    @{ Id = "spellstone_core_common"; Batch = "spellstone"; Kind = "icon"; Theme = "common arcane spellstone core, Magi-Tech" }
    @{ Id = "mana_crystal"; Batch = "ingredient"; Kind = "icon"; Theme = "mana crystal spellcrafting ingredient, Magi-Tech" }
    @{ Id = "fire_ruby"; Batch = "ingredient"; Kind = "icon"; Theme = "fire ruby spellcrafting ingredient, Magi-Tech" }
    @{ Id = "magitech_berserker_core"; Batch = "minion"; Kind = "icon"; Theme = "berserker minion core, Magi-Tech" }
)

if ($AssetIds.Count -gt 0) {
    $jobs = $jobs | Where-Object { $AssetIds -contains $_.Id -or ($_.Alias -and ($AssetIds -contains $_.Alias)) }
}
if ($Limit -gt 0) {
    $jobs = @($jobs | Select-Object -First $Limit)
}

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Produce animations via Magi-Tech SD pipeline" -ForegroundColor Cyan
Write-Host "  Assets: $(@($jobs).Count)  Frames: $FrameCount  QA: $QualityAssessmentDepth" -ForegroundColor Gray
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan

if ($AutoStartSd) {
    if (-not (Test-Path $startSd)) { throw "Missing $startSd" }
    Write-Host "Starting Stable Diffusion server (GPU-first)..." -ForegroundColor Yellow
    $env:SD_IDLE_SHUTDOWN_SEC = "0"
    & $startSd -WaitSec 180 -NoStatusGui
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[WARN] SD start script exit $LASTEXITCODE — continuing if /ping is up" -ForegroundColor Yellow
    }
}

$ok = 0
$fail = 0
foreach ($job in $jobs) {
    $still = Join-Path $sheets "$($job.Batch)\$($job.Id).png"
    if (-not (Test-Path $still)) {
        Write-Host "  [SKIP] no still $($job.Id)" -ForegroundColor Yellow
        continue
    }
    $assetId = if ($job.Alias) { $job.Alias } else { $job.Id }
    $draft = Join-Path $draftDir "${assetId}_design_draft.png"
    Copy-Item -LiteralPath $still -Destination $draft -Force

    Write-Host ""
    Write-Host "── $assetId  (still $($job.Id))" -ForegroundColor Cyan
    try {
        & $pipeline `
            -ModPath $ModPath `
            -AssetId $assetId `
            -Theme $job.Theme `
            -Kind $job.Kind `
            -SkipDraft `
            -AutoStartSd:$AutoStartSd `
            -FrameCount $FrameCount `
            -TileSize $TileSize `
            -QualityAssessmentDepth $QualityAssessmentDepth `
            -MaxRetries 1 `
            -PassThreshold 12
        $pipeCode = $LASTEXITCODE

        $genDir = Join-Path $ModPath "assets\magitech\generated\$assetId"
        $sheet = Join-Path $genDir "$assetId.png"
        $staged = Join-Path $genDir "Source\frames"
        if ((Test-Path $staged) -and (Test-Path $packer)) {
            $frameFiles = @(Get-ChildItem -LiteralPath $staged -Filter "frame*.png" | Sort-Object Name | ForEach-Object { $_.FullName })
            if ($frameFiles.Count -gt 0) {
                $packedSheet = Join-Path $genDir "${assetId}_sheet.png"
                $packedFrames = Join-Path $genDir "${assetId}_sheet.frames"
                & $packer `
                    -FrameFiles $frameFiles `
                    -OutputSpritesheet $packedSheet `
                    -OutputFrames $packedFrames `
                    -FrameWidth $TileSize `
                    -FrameHeight $TileSize `
                    -Tool Auto
                if (Test-Path $packedSheet) { $sheet = $packedSheet }
            }
        }

        if (Test-Path $sheet) {
            & $animGen `
                -AnimationName $assetId `
                -ImagePath $sheet `
                -FrameCount $FrameCount `
                -FrameSize @($TileSize, $TileSize) `
                -AnimationCycle 1.2 `
                -OutputDir $genDir `
                -Description $job.Theme
        }

        if ($pipeCode -eq 0 -or (Test-Path $sheet)) {
            $ok++
            Write-Host "  [OK] $assetId" -ForegroundColor Green
        } else {
            $fail++
            Write-Host "  [WARN] $assetId pipeline exit $pipeCode" -ForegroundColor Yellow
        }
    } catch {
        $fail++
        Write-Host "  [FAIL] $assetId : $_" -ForegroundColor Red
    }
}

if (Test-Path $installItems) {
    Write-Host ""
    Write-Host "Re-installing generated sheets onto item paths..." -ForegroundColor Cyan
    python $installItems --mod-path $ModPath
}

Write-Host ""
Write-Host "Done. Generated: $ok  Failed: $fail" -ForegroundColor $(if ($fail -gt 0) { "Yellow" } else { "Green" })
Write-Host "Sheets: $ModPath\assets\magitech\generated\"
exit $(if ($fail -gt 0 -and $ok -eq 0) { 1 } else { 0 })
