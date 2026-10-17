#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate Stable Diffusion art for the stand-in ("placeholder") item/object/interface images.

.DESCRIPTION
    Several systems of the Magi-Tech mod reference small stand-in images: the enchantment
    table interface (backgrounds, buttons, icons), crossbow / bolt / arrow sprites, flame
    projectile textures and particles, AI-art / visual-QA / GPU interface images.

    This script produces those images as real Stable Diffusion 3.5 art (local server on
    :1338, started on demand) through StarboundSdArt.psm1 / Shared\sd_art.py. Every image is
    written as <Id>.png at the exact pixel size given in its description (e.g. 260x40), into:

        interface assets  ->  <ModPath>\interface\<Id>.png
        everything else   ->  <ModPath>\assets\<Id>.png

    Nothing is drawn procedurally. If Stable Diffusion cannot deliver, the script THROWS.
    With -AllowProcedural (or AAMT_SD_STRICT=0) an SD failure for one image falls back to the
    old Ollama + StarboundAssetGenerator pipeline (which may itself draw procedural art).

.PARAMETER ModPath
    Path to the mod directory

.PARAMETER OllamaModel
    Ollama model for the legacy fallback pipeline only (unused for the SD art itself)

.PARAMETER UseCppBackend
    Legacy fallback pipeline only: use the C++ backend (unused for the SD art itself)

.PARAMETER AllowProcedural
    Permit the legacy procedural pipeline as a fallback when Stable Diffusion fails.
    Default: SD or throw.
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$ModPath = "F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery",

    [Parameter(Mandatory=$false)]
    [string]$OllamaModel = "codellama:7b-instruct",

    [Parameter(Mandatory=$false)]
    [bool]$UseCppBackend = $true,

    [Parameter(Mandatory=$false)]
    [switch]$AllowProcedural
)

$ErrorActionPreference = "Stop"
# Validate ModPath is not empty
if ([string]::IsNullOrWhiteSpace($ModPath)) {
    Write-Host "Error: ModPath cannot be empty" -ForegroundColor Red
    Write-Host "  Please provide a valid mod path or use the default" -ForegroundColor Gray
    exit 1
}

# SD art helper (throws when SD fails unless procedural output is explicitly allowed)
Import-Module (Join-Path $PSScriptRoot "StarboundSdArt.psm1") -Force
$script:ProceduralAllowed = $AllowProcedural.IsPresent -or ($env:AAMT_SD_STRICT -eq '0')

# Load shared asset generation settings
$settingsPath = Join-Path $PSScriptRoot "..\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}
$assetGenerator = Join-Path $PSScriptRoot "StarboundOllamaAssetGenerator.ps1"

Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host "  Stand-in Asset Generator (Stable Diffusion art)" -ForegroundColor Cyan
Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host ""

$generated = 0
$failed = 0

# Stable seed per asset id so a re-run reproduces the same art.
function Get-StableSeed {
    param([string]$Name)
    $h = 17
    foreach ($ch in $Name.ToCharArray()) { $h = (($h * 31) + [int]$ch) % 900000 }
    return [int]($h + 1)
}

# Generate one stand-in image: SD art at the exact size, legacy pipeline only as an allowed fallback.
function New-StandInAsset {
    param(
        [hashtable]$Asset,
        [string]$OutputDir,
        [string]$Context,
        [string]$LegacyAssetType
    )

    $outPath = Join-Path $OutputDir "$($Asset.Id).png"
    $made = New-StarboundSdArt -Kind sprite -Prompt $Asset.Prompt -OutputPath $outPath `
        -Width $Asset.W -Height $Asset.H -SdKind $Asset.SdKind `
        -Transparent:([bool]$Asset.Transparent) -Pixel:([bool]$Asset.Pixel) -Colors 32 `
        -Seed (Get-StableSeed -Name $Asset.Id) -AllowProcedural:$script:ProceduralAllowed
    if ($made -eq $true) {
        return $true
    }

    # Only reachable when procedural output is explicitly allowed and SD failed.
    Write-Host "  [FALLBACK] SD unavailable - legacy procedural pipeline (-AllowProcedural)" -ForegroundColor Yellow
    $params = @{
        AssetType = $LegacyAssetType
        AssetName = $Asset.Id
        Prompt = "$($Asset.Desc). $Context"
        OllamaModel = $OllamaModel
        OutputDir = $OutputDir
        AllowProcedural = $true
    }
    $params['UseCppBackend'] = $UseCppBackend
    & $assetGenerator @params | Out-Null
    return $true
}

function Invoke-AssetGroup {
    param(
        [string]$Title,
        [object[]]$Assets,
        [string]$OutputDir,
        [string]$Context,
        [scriptblock]$LegacyTypeFor
    )

    Write-Host "===========================================================" -ForegroundColor Yellow
    Write-Host "  $Title" -ForegroundColor Yellow
    Write-Host "===========================================================" -ForegroundColor Yellow
    Write-Host ""

    if ([string]::IsNullOrWhiteSpace($OutputDir)) {
        throw "Output directory is empty for group '$Title' (ModPath: '$ModPath')"
    }
    if (-not (Test-Path $OutputDir)) {
        New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
    }

    foreach ($asset in $Assets) {
        Write-Host "Generating: $($asset.Name) ($($asset.W)x$($asset.H))" -ForegroundColor Cyan
        try {
            $legacyType = & $LegacyTypeFor $asset
            [void](New-StandInAsset -Asset $asset -OutputDir $OutputDir -Context $Context -LegacyAssetType $legacyType)
            $script:generated++
            Write-Host "  [OK] Generated: $($asset.Name)" -ForegroundColor Green
        } catch {
            $script:failed++
            Write-Host "  [FAIL] $($asset.Name) : $_" -ForegroundColor Red
            # SD or throw: do not keep spending minutes per image against a dead SD server.
            if (-not $script:ProceduralAllowed) { throw }
        }
        Write-Host ""
    }
}

# Size is the trailing "WxH" of each description; the art prompt is written per asset.
function Get-SizeFromDesc {
    param([string]$Desc)
    if ($Desc -match '(\d+)x(\d+)\s*$') { return @([int]$Matches[1], [int]$Matches[2]) }
    return @(64, 64)
}

function New-Spec {
    param(
        [string]$Id, [string]$Name, [string]$Desc, [string]$Prompt,
        [string]$SdKind = "icon", [switch]$Transparent, [switch]$Pixel
    )
    $wh = Get-SizeFromDesc -Desc $Desc
    return @{
        Id = $Id; Name = $Name; Desc = $Desc; Prompt = $Prompt
        W = $wh[0]; H = $wh[1]; SdKind = $SdKind
        Transparent = $Transparent.IsPresent; Pixel = $Pixel.IsPresent
    }
}

$uiStyle = "Magi-Tech arcane alchemy enchantment table user interface, dark engraved metal with glowing violet runes, flat orthographic front view, no text"

# ============================================================
# 1. ENCHANTMENT TABLE INTERFACE ASSETS
# ============================================================
$interfaceAssets = @(
    (New-Spec "magi_tech_item_placeholder" "Item Placeholder" "Item placeholder icon, empty item slot, 150x150" `
        "empty inventory item slot, ornate square socket frame with faint glowing violet runes around the border and a hollow dark center, $uiStyle" -SdKind sprite),
    (New-Spec "magi_tech_enchantment_table_background" "Enchantment Table Background" "Enchantment table background texture, UI background panel, 1000x700" `
        "ornate dark stone and metal interface panel background with subtle arcane circuit engravings and faint violet glow, empty center, $uiStyle" -SdKind hud),
    (New-Spec "magi_tech_enchant_button" "Enchant Button" "Enchant button icon, apply enchantment button, 260x40" `
        "wide horizontal button plate, polished dark metal with a glowing violet rune gem in the middle, $uiStyle" -SdKind hud),
    (New-Spec "magi_tech_enchant_button_hover" "Enchant Button Hover" "Enchant button hover state, hover effect, 260x40" `
        "wide horizontal button plate, polished dark metal with a bright glowing violet rune gem, highlighted hover state with extra glow, $uiStyle" -SdKind hud),
    (New-Spec "magi_tech_enchant_button_pressed" "Enchant Button Pressed" "Enchant button pressed state, pressed effect, 260x40" `
        "wide horizontal button plate, dark metal pushed in and dimmer, violet rune gem glowing faintly, pressed state, $uiStyle" -SdKind hud),
    (New-Spec "magi_tech_remove_button" "Remove Button" "Remove enchantment button icon, remove button, 260x40" `
        "wide horizontal button plate, polished dark metal with a glowing crimson rune gem in the middle, $uiStyle" -SdKind hud),
    (New-Spec "magi_tech_remove_button_hover" "Remove Button Hover" "Remove button hover state, hover effect, 260x40" `
        "wide horizontal button plate, polished dark metal with a bright glowing crimson rune gem, highlighted hover state with extra glow, $uiStyle" -SdKind hud),
    (New-Spec "magi_tech_remove_button_pressed" "Remove Button Pressed" "Remove button pressed state, pressed effect, 260x40" `
        "wide horizontal button plate, dark metal pushed in and dimmer, crimson rune gem glowing faintly, pressed state, $uiStyle" -SdKind hud),
    (New-Spec "magi_tech_filter_button" "Filter Button" "Filter button icon, filter button, 180x25" `
        "narrow horizontal filter tab button, dark engraved metal strip with a small teal rune, $uiStyle" -SdKind hud),
    (New-Spec "magi_tech_filter_button_hover" "Filter Button Hover" "Filter button hover state, hover effect, 180x25" `
        "narrow horizontal filter tab button, dark engraved metal strip with a bright glowing teal rune, hover highlight, $uiStyle" -SdKind hud),
    (New-Spec "magi_tech_close_button" "Close Button" "Close button icon, close interface button, 40x40" `
        "small square close button, dark metal plate with a glowing violet X-shaped rune mark, $uiStyle" -SdKind sprite),
    (New-Spec "magi_tech_close_button_hover" "Close Button Hover" "Close button hover state, hover effect, 40x40" `
        "small square close button, dark metal plate with a bright glowing violet X-shaped rune mark, hover highlight, $uiStyle" -SdKind sprite),
    (New-Spec "magi_tech_enchantment_icon" "Enchantment Icon" "Enchantment table icon, interface icon, 32x32" `
        "icon of an enchanting table: a small stone altar with a floating glowing violet rune crystal above it, single centered object" -SdKind icon -Transparent -Pixel)
)

Invoke-AssetGroup -Title "Generating Enchantment Table Interface Assets" -Assets $interfaceAssets `
    -OutputDir (Join-Path $ModPath "interface") -Context "Interface asset for Starbound enchantment table." `
    -LegacyTypeFor { param($a) if ($a.Id -like "*background*") { "Texture" } else { "Icon" } }

$assetsDir = Join-Path $ModPath "assets"

# ============================================================
# 2. CROSSBOW GENERATOR ASSETS
# ============================================================
$crossbowAssets = @(
    (New-Spec "crossbow_basic_sprite" "Basic Crossbow Sprite" "Basic crossbow sprite, crossbow weapon sprite, 64x64" `
        "a simple wooden crossbow weapon, side view, iron fittings, loaded bolt, single centered object" -SdKind sprite -Transparent -Pixel),
    (New-Spec "crossbow_basic_icon" "Basic Crossbow Icon" "Basic crossbow icon, crossbow item icon, 32x32" `
        "a simple wooden crossbow weapon, item icon, iron fittings, single centered object" -SdKind icon -Transparent -Pixel),
    (New-Spec "crossbow_advanced_sprite" "Advanced Crossbow Sprite" "Advanced crossbow sprite, enhanced crossbow sprite, 64x64" `
        "an advanced mechanical repeating crossbow weapon, side view, brass gears, glowing violet energy core, single centered object" -SdKind sprite -Transparent -Pixel),
    (New-Spec "crossbow_advanced_icon" "Advanced Crossbow Icon" "Advanced crossbow icon, enhanced crossbow icon, 32x32" `
        "an advanced mechanical repeating crossbow weapon, item icon, brass gears, glowing violet energy core, single centered object" -SdKind icon -Transparent -Pixel),
    (New-Spec "bolt_basic_sprite" "Basic Bolt Sprite" "Basic bolt sprite, crossbow bolt projectile, 32x32" `
        "a single crossbow bolt projectile, iron tip and feathered tail, diagonal flight view, single centered object" -SdKind icon -Transparent -Pixel),
    (New-Spec "bolt_basic_icon" "Basic Bolt Icon" "Basic bolt icon, bolt item icon, 32x32" `
        "a single crossbow bolt, item icon, iron tip and feathered tail, single centered object" -SdKind icon -Transparent -Pixel),
    (New-Spec "arrow_basic_sprite" "Basic Arrow Sprite" "Basic arrow sprite, arrow projectile, 32x32" `
        "a single wooden arrow projectile, steel arrowhead and feather fletching, diagonal flight view, single centered object" -SdKind icon -Transparent -Pixel),
    (New-Spec "arrow_basic_icon" "Basic Arrow Icon" "Basic arrow icon, arrow item icon, 32x32" `
        "a single wooden arrow, item icon, steel arrowhead and feather fletching, single centered object" -SdKind icon -Transparent -Pixel)
)

Invoke-AssetGroup -Title "Generating Crossbow Generator Assets" -Assets $crossbowAssets `
    -OutputDir $assetsDir -Context "Crossbow generator asset for Starbound." `
    -LegacyTypeFor { param($a) if ($a.Id -like "*sprite*") { "Sprite" } else { "Icon" } }

# ============================================================
# 3. FLAME PROJECTILE ASSETS
# ============================================================
$flameAssets = @(
    (New-Spec "flame_noise_texture" "Flame Noise Texture" "Flame noise texture, procedural noise texture, 128x128" `
        "turbulent fire noise texture, swirling orange and red flame wisps over deep black-red, seamless flat texture" -SdKind texture),
    (New-Spec "flame_gradient_texture" "Flame Gradient Texture" "Flame gradient texture, radial gradient texture, 128x128" `
        "radial fire glow texture, bright yellow-white core fading through orange to deep red at the edges, soft smooth gradient" -SdKind texture),
    (New-Spec "flame_merged_texture" "Flame Merged Texture" "Flame merged texture, combined noise and gradient, 128x128" `
        "radial fire texture with turbulent flame wisps, bright yellow core, orange and red flickering edges, flat texture" -SdKind texture),
    (New-Spec "flame_ember_particle" "Flame Ember Particle" "Flame ember particle effect, ember particles, 64x64" `
        "a few glowing orange embers and sparks floating, particle effect, small bright points" -SdKind icon -Transparent),
    (New-Spec "flame_trail_particle" "Flame Trail Particle" "Flame trail particle effect, trail particles, 128x32" `
        "a horizontal streak of fire trailing to the left, bright yellow head fading to red-orange tail, particle effect" -SdKind hud -Transparent),
    (New-Spec "flame_smoke_particle" "Flame Smoke Particle" "Flame smoke particle effect, smoke particles, 64x64" `
        "a soft puff of dark grey smoke with faint orange glow at the base, particle effect" -SdKind icon -Transparent)
)

Invoke-AssetGroup -Title "Generating Flame Projectile Assets" -Assets $flameAssets `
    -OutputDir $assetsDir -Context "Flame projectile asset for Starbound." `
    -LegacyTypeFor { param($a) if ($a.Id -like "*particle*") { "Particle" } else { "Texture" } }

# ============================================================
# 4. AI ART GENERATOR STAND-IN ASSETS
# ============================================================
$aiArtAssets = @(
    (New-Spec "ai_art_placeholder" "AI Art Placeholder" "AI art placeholder image, generated art placeholder, 256x256" `
        "an empty gilded picture frame on a wall holding swirling abstract violet and teal arcane mist, art gallery stand-in image" -SdKind sprite),
    (New-Spec "ai_art_default" "AI Art Default" "AI art default image, default generated art, 256x256" `
        "a default fantasy landscape painting: floating crystal islands over a glowing violet sky, hand-painted game art" -SdKind sprite)
)

Invoke-AssetGroup -Title "Generating AI Art Generator Stand-in Assets" -Assets $aiArtAssets `
    -OutputDir $assetsDir -Context "AI art generator asset for Starbound." `
    -LegacyTypeFor { param($a) "Texture" }

# ============================================================
# 5. VISUAL QA SYSTEM STAND-IN ASSETS
# ============================================================
$qaAssets = @(
    (New-Spec "qa_placeholder_image" "QA Placeholder Image" "Visual QA placeholder image, QA test image, 128x128" `
        "a clear simple test scene for image quality checks: a small stone wizard tower on a grassy hill under a blue sky" -SdKind sprite),
    (New-Spec "qa_reference_image" "QA Reference Image" "Visual QA reference image, QA reference, 128x128" `
        "a clear reference image for image quality checks: a glowing violet crystal on a stone pedestal, plain dark background" -SdKind sprite)
)

Invoke-AssetGroup -Title "Generating Visual QA System Stand-in Assets" -Assets $qaAssets `
    -OutputDir $assetsDir -Context "Visual QA system asset for Starbound." `
    -LegacyTypeFor { param($a) "Texture" }

# ============================================================
# 6. GPU INTERFACE STAND-IN ASSETS
# ============================================================
$gpuAssets = @(
    (New-Spec "gpu_texture_placeholder" "GPU Texture Placeholder" "GPU texture placeholder, default GPU texture, 64x64" `
        "seamless tileable engraved stone and brass circuit pattern texture, flat top-down view" -SdKind texture),
    (New-Spec "gpu_audio_texture_placeholder" "GPU Audio Texture Placeholder" "GPU audio texture placeholder, audio texture, 64x64" `
        "glowing audio spectrum texture, vertical bars of teal and violet light of varying height on a dark background" -SdKind texture)
)

Invoke-AssetGroup -Title "Generating GPU Interface Stand-in Assets" -Assets $gpuAssets `
    -OutputDir $assetsDir -Context "GPU interface asset for Starbound." `
    -LegacyTypeFor { param($a) "Texture" }

# ============================================================
# SUMMARY
# ============================================================
Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host "  Generation Complete" -ForegroundColor Cyan
Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Generated: $generated assets" -ForegroundColor Green
Write-Host "Failed: $failed assets" -ForegroundColor $(if ($failed -gt 0) { "Red" } else { "Green" })
Write-Host ""
Write-Host "Assets saved to:" -ForegroundColor Gray
Write-Host "  Interface (enchantment table): $(Join-Path $ModPath 'interface')" -ForegroundColor Gray
Write-Host "  Crossbow / flame / AI art / QA / GPU: $(Join-Path $ModPath 'assets')" -ForegroundColor Gray
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Update code references to use the generated asset paths" -ForegroundColor Gray
Write-Host "  2. Review the generated art and re-run for any image you want regenerated" -ForegroundColor Gray
Write-Host "  3. Test assets in-game" -ForegroundColor Gray
Write-Host ""
