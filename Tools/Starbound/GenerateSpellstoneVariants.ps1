#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generates spellstone variants (per element / per strength level) with Stable Diffusion art.

.DESCRIPTION
    Every variant PNG is real Stable Diffusion 3.5 art (local server on :1338, started on
    demand) produced through StarboundSdArt.psm1 / Shared\sd_art.py. The prompt is built from
    the element (core glow / energy / metallic accent colours), the strength level and the
    asset type, and the result is knocked out to alpha, downsized to the size of the base
    template image and palette-quantised for pixel-art use.

    The base template image is still required: its pixel size is the delivery size of every
    variant (the template itself is no longer recoloured - recolouring a template with a flat
    colour matrix was a placeholder, not art).

    Animation frames (-GenerateAnimations) are brightness-pulse frames of the SD variant
    (ImageMagick -modulate); no frame is drawn procedurally.

    If Stable Diffusion cannot deliver, the script THROWS. The old colour-replacement code
    (ImageMagick / System.Drawing) only runs as a fallback after an SD failure, and only when
    -AllowProcedural is passed (or AAMT_SD_STRICT=0 is set).

.PARAMETER BaseImagePath
    Path to the base spellstone template image (its size is used for every variant)

.PARAMETER AssetType
    Type of assets to generate: spellform, spellshape, or "all"

.PARAMETER Element
    Element type: fire, ice, lightning, nature, arcane, void, cosmic, temporal, or "all"

.PARAMETER StrengthLevel
    Strength level: weak, moderate, strong, extreme, or "all"

.PARAMETER GenerateAnimations
    Generate animated versions with pulsing effects

.PARAMETER AnimationFrames
    Number of frames for animations (default: 8)

.PARAMETER OutputDir
    Base output directory for generated assets

.PARAMETER AllowProcedural
    Permit the legacy recolour / copy fallback when Stable Diffusion fails. Default: SD or throw.
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$BaseImagePath,

    [Parameter(Mandatory=$false)]
    [ValidateSet("spellform", "spellshape", "all")]
    [string]$AssetType = "all",

    [Parameter(Mandatory=$false)]
    [ValidateSet("fire", "ice", "lightning", "nature", "arcane", "void", "cosmic", "temporal", "all")]
    [string]$Element = "all",

    [Parameter(Mandatory=$false)]
    [ValidateSet("weak", "moderate", "strong", "extreme", "all")]
    [string]$StrengthLevel = "all",

    [Parameter(Mandatory=$false)]
    [switch]$GenerateAnimations,

    [Parameter(Mandatory=$false)]
    [int]$AnimationFrames = 0,  # 0 means use default from settings

    [Parameter(Mandatory=$false)]
    [string]$OutputDir = "",  # Empty means use default from settings

    [Parameter(Mandatory=$false)]
    [switch]$AllowProcedural
)

$ErrorActionPreference = "Stop"

try { Add-Type -AssemblyName System.Drawing -ErrorAction Stop } catch { }

# SD art helper (throws when SD fails unless procedural output is explicitly allowed)
Import-Module (Join-Path $PSScriptRoot "StarboundSdArt.psm1") -Force
$script:ProceduralAllowed = $AllowProcedural.IsPresent -or ($env:AAMT_SD_STRICT -eq '0')

# Import shared settings from Tools root
$settingsPath = Join-Path (Split-Path -Parent $PSScriptRoot) "AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
    Write-Host "[OK] Loaded shared settings" -ForegroundColor Gray
} else {
    Write-Host "[WARN] Shared settings not found, using defaults" -ForegroundColor Yellow
    $script:ImageMagickPath = "E:\tools\ImageMagick"
    $script:ImageMagickExe = Join-Path $script:ImageMagickPath "magick.exe"
    $script:SpellstoneOutputDir = "F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery\assets\items\spellstones"
    $script:DefaultAnimationFrames = 8
}

# Use default output directory from settings if not specified
if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $OutputDir = $script:SpellstoneOutputDir
}
$baseOutputDir = $OutputDir

# Use default animation frames from settings if not specified
if ($AnimationFrames -eq 0) {
    $AnimationFrames = $script:DefaultAnimationFrames
}
if (-not $AnimationFrames -or $AnimationFrames -lt 1) { $AnimationFrames = 8 }

# Check if base image exists
if (-not (Test-Path $BaseImagePath)) {
    Write-Host "Error: Base image not found: $BaseImagePath" -ForegroundColor Red
    exit 1
}

Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host "  Spellstone Variant Generator (Stable Diffusion)" -ForegroundColor Cyan
Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Base Image: $BaseImagePath" -ForegroundColor Green
Write-Host ""

# Delivery size = size of the base template image (PNG header; falls back to System.Drawing).
function Get-TemplateImageSize {
    param([string]$Path)
    try {
        $fs = [System.IO.File]::OpenRead((Resolve-Path -LiteralPath $Path).Path)
        try {
            $hdr = New-Object byte[] 24
            [void]$fs.Read($hdr, 0, 24)
        } finally { $fs.Dispose() }
        if ($hdr[0] -eq 0x89 -and $hdr[1] -eq 0x50 -and $hdr[2] -eq 0x4E -and $hdr[3] -eq 0x47) {
            $w = ([int]$hdr[18] -shl 8) -bor [int]$hdr[19]
            $h = ([int]$hdr[22] -shl 8) -bor [int]$hdr[23]
            if ($w -gt 0 -and $h -gt 0) { return @($w, $h) }
        }
    } catch { }
    try {
        $img = [System.Drawing.Image]::FromFile((Resolve-Path -LiteralPath $Path).Path)
        try { return @($img.Width, $img.Height) } finally { $img.Dispose() }
    } catch { }
    return @(64, 64)
}

$templateSize = Get-TemplateImageSize -Path $BaseImagePath
$script:CellWidth = [int]$templateSize[0]
$script:CellHeight = [int]$templateSize[1]
Write-Host "Delivery size (from base image): $($script:CellWidth)x$($script:CellHeight)" -ForegroundColor Gray
Write-Host ""

# Element definitions: colours (legacy recolour fallback) + words used to build the SD prompt.
$elementColors = @{
    fire = @{
        coreGlow = [System.Drawing.Color]::FromArgb(255, 255, 100, 50)      # Bright orange-red
        energyPattern = [System.Drawing.Color]::FromArgb(200, 255, 150, 0)  # Orange-yellow
        metallicAccent = [System.Drawing.Color]::FromArgb(255, 255, 200, 0)  # Gold
        intensity = 1.2
        look = "a bright orange-red glowing core, orange-yellow flames of energy inside, gold metal accents"
    }
    ice = @{
        coreGlow = [System.Drawing.Color]::FromArgb(255, 100, 200, 255)     # Bright cyan-blue
        energyPattern = [System.Drawing.Color]::FromArgb(200, 150, 220, 255) # Light blue
        metallicAccent = [System.Drawing.Color]::FromArgb(255, 200, 220, 255) # Silver-blue
        intensity = 0.9
        look = "a bright cyan-blue glowing core, light blue frost energy inside, silver-blue metal accents"
    }
    lightning = @{
        coreGlow = [System.Drawing.Color]::FromArgb(255, 255, 255, 150)      # Bright yellow-white
        energyPattern = [System.Drawing.Color]::FromArgb(200, 255, 255, 100) # Yellow
        metallicAccent = [System.Drawing.Color]::FromArgb(255, 255, 220, 100) # Gold-yellow
        intensity = 1.3
        look = "a bright yellow-white glowing core, crackling yellow lightning arcs inside, gold-yellow metal accents"
    }
    nature = @{
        coreGlow = [System.Drawing.Color]::FromArgb(255, 100, 255, 150)      # Bright green
        energyPattern = [System.Drawing.Color]::FromArgb(200, 150, 255, 180) # Light green
        metallicAccent = [System.Drawing.Color]::FromArgb(255, 180, 255, 150) # Green-gold
        intensity = 1.0
        look = "a bright green glowing core, light green living energy inside, green-gold metal accents"
    }
    arcane = @{
        coreGlow = [System.Drawing.Color]::FromArgb(255, 200, 100, 255)      # Bright purple
        energyPattern = [System.Drawing.Color]::FromArgb(200, 220, 150, 255) # Light purple
        metallicAccent = [System.Drawing.Color]::FromArgb(255, 240, 180, 255) # Purple-silver
        intensity = 1.1
        look = "a bright purple glowing core, light purple arcane runes inside, purple-silver metal accents"
    }
    void = @{
        coreGlow = [System.Drawing.Color]::FromArgb(255, 80, 50, 120)        # Dark purple-black
        energyPattern = [System.Drawing.Color]::FromArgb(200, 120, 80, 180)  # Dark purple
        metallicAccent = [System.Drawing.Color]::FromArgb(255, 150, 100, 150) # Dark purple-grey
        intensity = 0.8
        look = "a dark purple-black glowing core, dark purple void energy inside, dark purple-grey metal accents"
    }
    cosmic = @{
        coreGlow = [System.Drawing.Color]::FromArgb(255, 200, 200, 255)      # Bright white-blue
        energyPattern = [System.Drawing.Color]::FromArgb(200, 220, 220, 255) # Light white-blue
        metallicAccent = [System.Drawing.Color]::FromArgb(255, 255, 255, 200) # Silver-white
        intensity = 1.4
        look = "a bright white-blue glowing core, tiny stars and nebula light inside, silver-white metal accents"
    }
    temporal = @{
        coreGlow = [System.Drawing.Color]::FromArgb(255, 150, 200, 255)      # Blue-white
        energyPattern = [System.Drawing.Color]::FromArgb(200, 180, 220, 255) # Light blue-white
        metallicAccent = [System.Drawing.Color]::FromArgb(255, 200, 220, 255) # Silver-blue
        intensity = 1.0
        look = "a blue-white glowing core, light blue-white clockwork energy inside, silver-blue metal accents"
    }
}

# Strength level modifiers (glow intensity / pattern complexity; "look" feeds the SD prompt)
$strengthModifiers = @{
    weak = @{ intensity = 0.6; glowRadius = 0.7; patternDensity = 0.5; look = "faint dim glow, small simple stone" }
    moderate = @{ intensity = 1.0; glowRadius = 1.0; patternDensity = 1.0; look = "steady moderate glow" }
    strong = @{ intensity = 1.4; glowRadius = 1.3; patternDensity = 1.5; look = "bright intense glow, intricate energy patterns" }
    extreme = @{ intensity = 1.8; glowRadius = 1.6; patternDensity = 2.0; look = "blinding radiant glow with a large halo, elaborate swirling energy patterns" }
}

# ImageMagick is only used for pulse animation frames and the legacy fallback.
$imageMagickAvailable = $false
$magickExe = $null
if (Get-Command Test-ImageMagickAvailable -ErrorAction SilentlyContinue) {
    $imageMagickAvailable = [bool](Test-ImageMagickAvailable)
    if ($imageMagickAvailable) { $magickExe = Get-ImageMagickPath }
}
if ($imageMagickAvailable) {
    Write-Host "[OK] ImageMagick found at: $magickExe (pulse animation frames)" -ForegroundColor Green
} else {
    Write-Host "[WARN] ImageMagick not found - animation frames will be copies of the variant" -ForegroundColor Yellow
}

# Stable seed per asset name so a re-run reproduces the same art.
function Get-StableSeed {
    param([string]$Name)
    $h = 17
    foreach ($ch in $Name.ToCharArray()) { $h = (($h * 31) + [int]$ch) % 900000 }
    return [int]($h + 1)
}

# Legacy recolour of the template (ImageMagick / System.Drawing). Fallback only.
function Invoke-LegacyElementVariant {
    param(
        [string]$InputPath,
        [string]$OutputPath,
        [hashtable]$ElementColors,
        [hashtable]$StrengthMod
    )

    if ($imageMagickAvailable) {
        $intensity = $ElementColors.intensity * $StrengthMod.intensity
        $pct = [int][Math]::Round($intensity * 100)
        & $magickExe $InputPath -modulate "$pct,100,100" "PNG32:$OutputPath"
        if ($LASTEXITCODE -eq 0) {
            return $true
        }
    }

    try {
        $bitmap = [System.Drawing.Bitmap]::FromFile($InputPath)
        $newBitmap = New-Object System.Drawing.Bitmap($bitmap.Width, $bitmap.Height)

        for ($x = 0; $x -lt $bitmap.Width; $x++) {
            for ($y = 0; $y -lt $bitmap.Height; $y++) {
                $pixel = $bitmap.GetPixel($x, $y)

                # Detect blue glow areas (high blue component, low red/green)
                if ($pixel.B -gt 150 -and $pixel.R -lt 100 -and $pixel.G -lt 150) {
                    $newColor = [System.Drawing.Color]::FromArgb(
                        $pixel.A,
                        [int][Math]::Min(255, ($ElementColors.coreGlow.R * $StrengthMod.intensity)),
                        [int][Math]::Min(255, ($ElementColors.coreGlow.G * $StrengthMod.intensity)),
                        [int][Math]::Min(255, ($ElementColors.coreGlow.B * $StrengthMod.intensity))
                    )
                    $newBitmap.SetPixel($x, $y, $newColor)
                } else {
                    $newBitmap.SetPixel($x, $y, $pixel)
                }
            }
        }

        $newBitmap.Save($OutputPath, [System.Drawing.Imaging.ImageFormat]::Png)
        $bitmap.Dispose()
        $newBitmap.Dispose()
        return $true
    } catch {
        Write-Host "Error creating variant: $_" -ForegroundColor Red
        return $false
    }
}

# Create one variant PNG with Stable Diffusion (throws on SD failure unless procedural is allowed).
function Create-ElementVariant {
    param(
        [string]$InputPath,
        [string]$OutputPath,
        [hashtable]$ElementColors,
        [hashtable]$StrengthMod,
        [string]$Prompt,
        [int]$Seed
    )

    $made = New-StarboundSdArt -Kind sprite -Prompt $Prompt -OutputPath $OutputPath `
        -Width $script:CellWidth -Height $script:CellHeight -Transparent -Pixel -Colors 24 `
        -Seed $Seed -AllowProcedural:$script:ProceduralAllowed
    if ($made -eq $true) {
        return $true
    }

    # Only reachable when procedural output is explicitly allowed and SD failed.
    Write-Host "      [FALLBACK] SD unavailable - recolouring the template (-AllowProcedural)" -ForegroundColor Yellow
    return (Invoke-LegacyElementVariant -InputPath $InputPath -OutputPath $OutputPath -ElementColors $ElementColors -StrengthMod $StrengthMod)
}

# Create animation frames (brightness pulse of the SD variant)
function Create-AnimationFrames {
    param(
        [string]$BaseImagePath,
        [string]$OutputDir,
        [string]$AssetName,
        [int]$FrameCount,
        [hashtable]$ElementColors,
        [hashtable]$StrengthMod
    )

    $frames = @()

    for ($frame = 0; $frame -lt $FrameCount; $frame++) {
        $progress = $frame / $FrameCount
        $pulseIntensity = 0.8 + (0.4 * [Math]::Sin($progress * 2 * [Math]::PI))

        $framePath = Join-Path $OutputDir ("{0}_frame{1}.png" -f $AssetName, $frame.ToString("D2"))
        if ([string]::IsNullOrWhiteSpace($framePath)) {
            Write-Host "  [FAIL] framePath is null (OutputDir: '$OutputDir')" -ForegroundColor Red
            continue
        }

        if ($imageMagickAvailable) {
            $currentIntensity = $ElementColors.intensity * $StrengthMod.intensity * $pulseIntensity
            $pct = [int][Math]::Round($currentIntensity * 100)
            & $magickExe $BaseImagePath -modulate "$pct,100,100" "PNG32:$framePath"
        } else {
            Copy-Item $BaseImagePath $framePath -Force
        }

        $frames += $framePath
    }

    return $frames
}

# Determine elements and strength levels to generate
$elements = if ($Element -eq "all") {
    @("fire", "ice", "lightning", "nature", "arcane", "void", "cosmic", "temporal")
} else {
    @($Element)
}

$strengthLevels = if ($StrengthLevel -eq "all") {
    @("weak", "moderate", "strong", "extreme")
} else {
    @($StrengthLevel)
}

$generatedCount = 0
$failedCount = 0

# Generate spellform variants
if ($AssetType -eq "all" -or $AssetType -eq "spellform") {
    Write-Host "Generating Spellform Variants..." -ForegroundColor Yellow
    Write-Host ""

    foreach ($elementName in $elements) {
        if (-not $elementColors.ContainsKey($elementName)) {
            Write-Host "[WARN] Unknown element: $elementName, skipping" -ForegroundColor Yellow
            continue
        }

        $elementColor = $elementColors[$elementName]
        $strengthMod = $strengthModifiers["moderate"]  # Default for spellforms

        $assetName = "spellstone_${elementName}_base"
        $variantDir = Join-Path $baseOutputDir "spellforms\base\$elementName"
        if (-not (Test-Path $variantDir)) {
            New-Item -ItemType Directory -Path $variantDir -Force | Out-Null
        }
        $outputPath = Join-Path $variantDir "${assetName}.png"

        Write-Host "[GEN] $assetName" -ForegroundColor Cyan
        Write-Host "      Element: $elementName" -ForegroundColor Gray

        $prompt = "game item icon of a $elementName elemental spellstone, a faceted magical crystal gemstone with " +
            "$($elementColor.look), $($strengthMod.look), single centered object"
        $seed = Get-StableSeed -Name $assetName

        if (Create-ElementVariant -InputPath $BaseImagePath -OutputPath $outputPath -ElementColors $elementColor -StrengthMod $strengthMod -Prompt $prompt -Seed $seed) {
            Write-Host "      [OK] Generated successfully" -ForegroundColor Green
            $generatedCount++

            # Generate animation if requested
            if ($GenerateAnimations) {
                Write-Host "      Generating animation frames..." -ForegroundColor Gray
                $frames = Create-AnimationFrames -BaseImagePath $outputPath -OutputDir $variantDir -AssetName $assetName -FrameCount $AnimationFrames -ElementColors $elementColor -StrengthMod $strengthMod
                Write-Host "      [OK] Generated $($frames.Count) animation frames" -ForegroundColor Green
            }
        } else {
            Write-Host "      [FAIL] Generation failed" -ForegroundColor Red
            $failedCount++
        }

        Write-Host ""
    }
}

# Generate spellshape variants
if ($AssetType -eq "all" -or $AssetType -eq "spellshape") {
    Write-Host "Generating Spellshape Variants..." -ForegroundColor Yellow
    Write-Host ""

    # Use arcane as base for spellshape overlays (they modify existing spellforms)
    $baseElement = "arcane"
    $baseElementColor = $elementColors[$baseElement]

    foreach ($strength in $strengthLevels) {
        $strengthMod = $strengthModifiers[$strength]

        $assetName = "spellshape_overlay_${strength}"
        $variantDir = Join-Path $baseOutputDir "spellshapes\overlay\$strength"
        if (-not (Test-Path $variantDir)) {
            New-Item -ItemType Directory -Path $variantDir -Force | Out-Null
        }
        $outputPath = Join-Path $variantDir "${assetName}.png"

        Write-Host "[GEN] $assetName" -ForegroundColor Cyan
        Write-Host "      Strength: $strength" -ForegroundColor Gray

        $prompt = "game item icon of an arcane spellshape overlay, an ornate floating runic sigil ring with " +
            "$($baseElementColor.look), $($strengthMod.look), single centered emblem"
        $seed = Get-StableSeed -Name $assetName

        if (Create-ElementVariant -InputPath $BaseImagePath -OutputPath $outputPath -ElementColors $baseElementColor -StrengthMod $strengthMod -Prompt $prompt -Seed $seed) {
            Write-Host "      [OK] Generated successfully" -ForegroundColor Green
            $generatedCount++
        } else {
            Write-Host "      [FAIL] Generation failed" -ForegroundColor Red
            $failedCount++
        }

        Write-Host ""
    }
}

# Summary
Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host "  Generation Complete" -ForegroundColor Cyan
Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Statistics:" -ForegroundColor Yellow
Write-Host "  Generated: $generatedCount" -ForegroundColor Green
Write-Host "  Failed: $failedCount" -ForegroundColor $(if ($failedCount -gt 0) { "Red" } else { "Gray" })
Write-Host ""

if ($failedCount -eq 0) {
    Write-Host "[OK] All variants generated successfully!" -ForegroundColor Green
} else {
    Write-Host "[WARN] Some variants failed to generate. Check errors above." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Assets are organized in:" -ForegroundColor Cyan
Write-Host "  $baseOutputDir" -ForegroundColor Gray
Write-Host ""
