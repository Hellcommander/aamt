<#
.SYNOPSIS
    Terraria Portal Generator — full tModLoader portal mod packs (gameplay + art).

.DESCRIPTION
    Generates a drop-in tModLoader 1.4+ mod folder with:
    - Placeable ModItem + craft recipe
    - Lit ModTile with nearby FX and right-click spawn recall
    - Particle ModSystem, localization, build.txt, README
    - Procedural textures (base/frame/normal/distort) and effect profile JSON
    - Optional portal audio via TerrariaPortalAudioGenerator.ps1

.PARAMETER PortalName
    Name/ID of the portal

.PARAMETER Preset
    Built-in portal preset

.PARAMETER Description
    Natural language description for AI generation

.EXAMPLE
    .\TerrariaPortalGenerator.ps1 -PortalName "voidgate" -Preset Void -Description "cold blue void portal"
    .\TerrariaPortalGenerator.ps1 -PortalName "nethergate" -Preset Fire -Description "reddish spacetime distortion"
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$PortalName,

    [Parameter(Mandatory=$false)]
    [ValidateSet("Void", "Fire", "Ice", "Electric", "Nature", "Shadow", "Light", "Custom")]
    [string]$Preset = "Void",

    [Parameter(Mandatory=$false)]
    [string]$Description = "",

    [Parameter(Mandatory=$false)]
    [string]$OutputDir = "TerrariaPortals",

    # Texture dimensions
    [Parameter(Mandatory=$false)]
    [int]$TileSize = 32,

    [Parameter(Mandatory=$false)]
    [switch]$Animated,

    [Parameter(Mandatory=$false)]
    [int]$AnimationFrames = 4,

    # Portal shape
    [Parameter(Mandatory=$false)]
    [ValidateSet("Circle", "Ellipse", "Tear", "Hexagon", "Square")]
    [string]$Shape = "Circle",

    # Particle settings
    [Parameter(Mandatory=$false)]
    [int]$ParticleCount = 40,

    [Parameter(Mandatory=$false)]
    [ValidateSet("orbitInwardSpiral", "orbitOutwardSpiral", "inflow", "outflow", "orbit", "random")]
    [string]$MotionPattern = "orbitInwardSpiral",

    # Color scheme
    [Parameter(Mandatory=$false)]
    [string]$CoreColor = "",

    [Parameter(Mandatory=$false)]
    [string]$RimColor = "",

    [Parameter(Mandatory=$false)]
    [string]$AccentColor = "",

    # Shader settings
    [Parameter(Mandatory=$false)]
    [float]$DistortStrength = 0.04,

    [Parameter(Mandatory=$false)]
    [float]$WaveFrequency = 3.2,

    [Parameter(Mandatory=$false)]
    [float]$ChromaticAberration = 0.015,

    # Generate procedural portal textures (default on). Pass -SkipTextures for profile/code only.
    [Parameter(Mandatory=$false)]
    [switch]$GeneratePlaceholders,

    [Parameter(Mandatory=$false)]
    [switch]$SkipTextures
)

$ErrorActionPreference = "Stop"
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

# Optional shared tooling
$sharedPath = Join-Path $PSScriptRoot "..\Shared"
Import-Module (Join-Path $sharedPath "ToolDetection.psm1") -ErrorAction SilentlyContinue
Import-Module (Join-Path $sharedPath "ToolsetIntegration.psm1") -ErrorAction SilentlyContinue
$settingsPath = Join-Path $PSScriptRoot "..\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) { . $settingsPath }

# ============================================================================
# PRESET CONFIGURATIONS
# ============================================================================

$PortalPresets = @{
    "Void" = @{
        CoreColor = "#b3f0ff"
        RimColor = "#3b7fff"
        AccentColor = "#ff66ff"
        MotionPattern = "orbitInwardSpiral"
        ParticleCount = 40
        DistortStrength = 0.04
        WaveFrequency = 3.2
        ChromaticAberration = 0.015
        Description = "Cold blue void portal with spacetime distortion"
    }
    "Fire" = @{
        CoreColor = "#ff6600"
        RimColor = "#ff3300"
        AccentColor = "#ffff00"
        MotionPattern = "outflow"
        ParticleCount = 50
        DistortStrength = 0.06
        WaveFrequency = 4.0
        ChromaticAberration = 0.02
        Description = "Fiery red portal with outward particle flow"
    }
    "Ice" = @{
        CoreColor = "#a0e0ff"
        RimColor = "#4080ff"
        AccentColor = "#ffffff"
        MotionPattern = "inflow"
        ParticleCount = 35
        DistortStrength = 0.03
        WaveFrequency = 2.5
        ChromaticAberration = 0.01
        Description = "Frosty blue portal with inward particle flow"
    }
    "Electric" = @{
        CoreColor = "#ffff00"
        RimColor = "#00ffff"
        AccentColor = "#ffffff"
        MotionPattern = "random"
        ParticleCount = 60
        DistortStrength = 0.08
        WaveFrequency = 5.0
        ChromaticAberration = 0.025
        Description = "Electric portal with chaotic particle motion"
    }
    "Nature" = @{
        CoreColor = "#66ff66"
        RimColor = "#228822"
        AccentColor = "#ffff88"
        MotionPattern = "orbit"
        ParticleCount = 30
        DistortStrength = 0.02
        WaveFrequency = 2.0
        ChromaticAberration = 0.01
        Description = "Green nature portal with orbiting particles"
    }
    "Shadow" = @{
        CoreColor = "#6600ff"
        RimColor = "#330066"
        AccentColor = "#ff00ff"
        MotionPattern = "orbitInwardSpiral"
        ParticleCount = 45
        DistortStrength = 0.05
        WaveFrequency = 3.5
        ChromaticAberration = 0.018
        Description = "Dark shadow portal with purple distortion"
    }
    "Light" = @{
        CoreColor = "#ffffff"
        RimColor = "#ffff88"
        AccentColor = "#ffaa00"
        MotionPattern = "orbitOutwardSpiral"
        ParticleCount = 35
        DistortStrength = 0.03
        WaveFrequency = 2.8
        ChromaticAberration = 0.012
        Description = "Bright light portal with golden particles"
    }
    "Custom" = @{
        CoreColor = "#b3f0ff"
        RimColor = "#3b7fff"
        AccentColor = "#ff66ff"
        MotionPattern = "orbitInwardSpiral"
        ParticleCount = 40
        DistortStrength = 0.04
        WaveFrequency = 3.2
        ChromaticAberration = 0.015
        Description = "Custom portal configuration"
    }
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

function Convert-HexToRgb {
    param([string]$Hex)
    
    $hex = $Hex -replace '#', ''
    if ($hex.Length -eq 6) {
        $r = [Convert]::ToInt32($hex.Substring(0, 2), 16)
        $g = [Convert]::ToInt32($hex.Substring(2, 2), 16)
        $b = [Convert]::ToInt32($hex.Substring(4, 2), 16)
        return @($r, $g, $b)
    }
    return @(179, 240, 255)  # Default cyan
}

function New-PortalTexture {
    param(
        [string]$OutputPath,
        [int]$Size,
        [array]$CoreColor,
        [array]$RimColor,
        [array]$AccentColor,
        [string]$Shape,
        [bool]$IsDistortion = $false,
        [bool]$IsNormal = $false
    )
    
    try {
        Add-Type -AssemblyName System.Drawing
        
        $bitmap = New-Object System.Drawing.Bitmap($Size, $Size)
        $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
        $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
        $graphics.Clear([System.Drawing.Color]::Transparent)
        
        $centerX = [double]($Size / 2.0)
        $centerY = [double]($Size / 2.0)
        $radius = [double]($Size * 0.4)
        
        if ($IsDistortion) {
            # Distortion map: encode offset vectors in RG channels
            for ($y = 0; $y -lt $Size; $y++) {
                for ($x = 0; $x -lt $Size; $x++) {
                    $dx = $x - $centerX
                    $dy = $y - $centerY
                    $dist = [Math]::Sqrt($dx * $dx + $dy * $dy)
                    
                    if ($dist -lt $radius) {
                        # Radial distortion pattern
                        $angle = [Math]::Atan2($dy, $dx)
                        $wave = [Math]::Sin($dist * 0.3 + $angle * 2) * 0.5 + 0.5
                        $offsetX = [Math]::Sin($angle) * $wave * 127 + 128
                        $offsetY = [Math]::Cos($angle) * $wave * 127 + 128
                        
                        $bitmap.SetPixel($x, $y, [System.Drawing.Color]::FromArgb(255, 
                            [int]$offsetX, [int]$offsetY, 128))
                    } else {
                        $bitmap.SetPixel($x, $y, [System.Drawing.Color]::FromArgb(255, 128, 128, 128))
                    }
                }
            }
        }
        elseif ($IsNormal) {
            # Normal map: encode surface normals
            for ($y = 0; $y -lt $Size; $y++) {
                for ($x = 0; $x -lt $Size; $x++) {
                    $dx = $x - $centerX
                    $dy = $y - $centerY
                    $dist = [Math]::Sqrt($dx * $dx + $dy * $dy)
                    
                    if ($dist -lt $radius -and $dist -gt 0) {
                        # Radial normal map - encode surface normals
                        $normalX = ($dx / $dist)
                        $normalY = ($dy / $dist)
                        $normalZ = 0.5  # Slight depth
                        
                        # Convert to 0-255 range (normal maps use 128 as "no offset")
                        $r = [Math]::Max(0, [Math]::Min(255, [int](($normalX * 0.5 + 0.5) * 255)))
                        $g = [Math]::Max(0, [Math]::Min(255, [int](($normalY * 0.5 + 0.5) * 255)))
                        $b = [Math]::Max(0, [Math]::Min(255, [int](($normalZ + 0.5) * 255)))
                        
                        $bitmap.SetPixel($x, $y, [System.Drawing.Color]::FromArgb(255, $r, $g, $b))
                    } elseif ($dist -eq 0) {
                        # Center point
                        $bitmap.SetPixel($x, $y, [System.Drawing.Color]::FromArgb(255, 128, 128, 255))
                    } else {
                        $bitmap.SetPixel($x, $y, [System.Drawing.Color]::FromArgb(255, 128, 128, 255))
                    }
                }
            }
        }
        else {
            # Base portal texture
            $coreR = [int]$CoreColor[0]
            $coreG = [int]$CoreColor[1]
            $coreB = [int]$CoreColor[2]
            $rimR = [int]$RimColor[0]
            $rimG = [int]$RimColor[1]
            $rimB = [int]$RimColor[2]
            $accentR = [int]$AccentColor[0]
            $accentG = [int]$AccentColor[1]
            $accentB = [int]$AccentColor[2]
            
            $coreClr = [System.Drawing.Color]::FromArgb(255, $coreR, $coreG, $coreB)
            $rimClr = [System.Drawing.Color]::FromArgb(255, $rimR, $rimG, $rimB)
            $accentClr = [System.Drawing.Color]::FromArgb(255, $accentR, $accentG, $accentB)
            
            # Draw portal shape
            switch ($Shape) {
                "Circle" {
                    $graphics.FillEllipse((New-Object System.Drawing.SolidBrush($rimClr)), 
                        $centerX - $radius, $centerY - $radius, $radius * 2, $radius * 2)
                    $graphics.FillEllipse((New-Object System.Drawing.SolidBrush($coreClr)), 
                        $centerX - $radius * 0.7, $centerY - $radius * 0.7, $radius * 1.4, $radius * 1.4)
                }
                "Ellipse" {
                    $graphics.FillEllipse((New-Object System.Drawing.SolidBrush($rimClr)), 
                        $centerX - $radius * 1.2, $centerY - $radius * 0.8, $radius * 2.4, $radius * 1.6)
                    $graphics.FillEllipse((New-Object System.Drawing.SolidBrush($coreClr)), 
                        $centerX - $radius, $centerY - $radius * 0.6, $radius * 2, $radius * 1.2)
                }
                "Tear" {
                    # Jagged tear shape - simplified to avoid array issues
                    $cx = [int][Math]::Round($centerX)
                    $cy = [int][Math]::Round($centerY)
                    $r = [int][Math]::Round($radius)
                    
                    # Outer tear shape
                    $points = New-Object System.Drawing.Point[] 8
                    $points[0] = New-Object System.Drawing.Point($cx, $cy - $r)
                    $points[1] = New-Object System.Drawing.Point($cx + [int]($r * 0.6), $cy - [int]($r * 0.3))
                    $points[2] = New-Object System.Drawing.Point($cx + [int]($r * 0.8), $cy)
                    $points[3] = New-Object System.Drawing.Point($cx + [int]($r * 0.4), $cy + [int]($r * 0.5))
                    $points[4] = New-Object System.Drawing.Point($cx, $cy + $r)
                    $points[5] = New-Object System.Drawing.Point($cx - [int]($r * 0.4), $cy + [int]($r * 0.5))
                    $points[6] = New-Object System.Drawing.Point($cx - [int]($r * 0.8), $cy)
                    $points[7] = New-Object System.Drawing.Point($cx - [int]($r * 0.6), $cy - [int]($r * 0.3))
                    
                    $rimBrush = New-Object System.Drawing.SolidBrush($rimClr)
                    $graphics.FillPolygon($rimBrush, $points)
                    $rimBrush.Dispose()
                    
                    # Inner core (scaled down)
                    $innerPoints = New-Object System.Drawing.Point[] 8
                    for ($i = 0; $i -lt 8; $i++) {
                        $px = [int]($points[$i].X * 0.7 + $cx * 0.3)
                        $py = [int]($points[$i].Y * 0.7 + $cy * 0.3)
                        $innerPoints[$i] = New-Object System.Drawing.Point($px, $py)
                    }
                    $coreBrush = New-Object System.Drawing.SolidBrush($coreClr)
                    $graphics.FillPolygon($coreBrush, $innerPoints)
                    $coreBrush.Dispose()
                }
                default {
                    # Default to circle
                    $graphics.FillEllipse((New-Object System.Drawing.SolidBrush($rimClr)), 
                        $centerX - $radius, $centerY - $radius, $radius * 2, $radius * 2)
                    $graphics.FillEllipse((New-Object System.Drawing.SolidBrush($coreClr)), 
                        $centerX - $radius * 0.7, $centerY - $radius * 0.7, $radius * 1.4, $radius * 1.4)
                }
            }
            
            # Add rim glow
            $pen = New-Object System.Drawing.Pen($accentClr, 2)
            $graphics.DrawEllipse($pen, $centerX - $radius, $centerY - $radius, $radius * 2, $radius * 2)
            $pen.Dispose()
        }
        
        $bitmap.Save($OutputPath, [System.Drawing.Imaging.ImageFormat]::Png)
        $graphics.Dispose()
        $bitmap.Dispose()
        
        return $true
    }
    catch {
        Write-Host "[Warning] Could not generate texture: $_" -ForegroundColor Yellow
        return $false
    }
}

# ============================================================================
# MAIN GENERATION LOGIC
# ============================================================================

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Terraria Portal Generator" -ForegroundColor Cyan
Write-Host "  AI-Assisted Modding Tools (AAMT)" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Initialize tools (Python is optional for this script, but check if available)
$tools = Initialize-ToolsetTools `
    -RequiredTools @() `
    -OptionalTools @("Python", "ImageMagick")

# Show tool status
Show-ToolsetStatus -ToolsetName "Terraria" `
    -RequiredTools @() `
    -OptionalTools @("Python", "ImageMagick")
Write-Host ""

# Get preset configuration
$presetConfig = $PortalPresets[$Preset]

# Apply colors
$finalCoreColor = if ($CoreColor) { Convert-HexToRgb -Hex $CoreColor } else { Convert-HexToRgb -Hex $presetConfig.CoreColor }
$finalRimColor = if ($RimColor) { Convert-HexToRgb -Hex $RimColor } else { Convert-HexToRgb -Hex $presetConfig.RimColor }
$finalAccentColor = if ($AccentColor) { Convert-HexToRgb -Hex $AccentColor } else { Convert-HexToRgb -Hex $presetConfig.AccentColor }

# Apply other settings
$finalMotion = if ($MotionPattern -ne "orbitInwardSpiral") { $MotionPattern } else { $presetConfig.MotionPattern }
$finalParticleCount = if ($ParticleCount -ne 40) { $ParticleCount } else { $presetConfig.ParticleCount }
$finalDistort = if ($DistortStrength -ne 0.04) { $DistortStrength } else { $presetConfig.DistortStrength }
$finalWave = if ($WaveFrequency -ne 3.2) { $WaveFrequency } else { $presetConfig.WaveFrequency }
$finalChromatic = if ($ChromaticAberration -ne 0.015) { $ChromaticAberration } else { $presetConfig.ChromaticAberration }
$finalDescription = if ($Description) { $Description } else { $presetConfig.Description }

# Create output directory
$outputPath = $OutputDir
if (-not [System.IO.Path]::IsPathRooted($OutputDir)) {
    $outputPath = Join-Path (Get-Location) $OutputDir
}

$portalDir = Join-Path $outputPath $PortalName
if (-not (Test-Path $portalDir)) {
    New-Item -ItemType Directory -Path $portalDir -Force | Out-Null
    Write-Host "[Created] Portal directory: $portalDir" -ForegroundColor Green
}

$textureDir = Join-Path $portalDir "Textures"
if (-not (Test-Path $textureDir)) {
    New-Item -ItemType Directory -Path $textureDir -Force | Out-Null
}

Write-Host "[Generating] Portal: $PortalName" -ForegroundColor Yellow
Write-Host "  Preset: $Preset" -ForegroundColor Gray
Write-Host "  Shape: $Shape" -ForegroundColor Gray
Write-Host "  Colors: Core=$($presetConfig.CoreColor), Rim=$($presetConfig.RimColor)" -ForegroundColor Gray

# ============================================================================
# Generate Portal Profile JSON
# ============================================================================

$portalProfile = [ordered]@{
    id = $PortalName
    game = "Terraria"
    type = "portalEffect"
    description = $finalDescription
    tiles = [ordered]@{
        size = $TileSize
        baseTexture = "Textures/Portals/${PortalName}_Base.png"
        frameTexture = "Textures/Portals/${PortalName}_Frame.png"
        normalMap = "Textures/Portals/${PortalName}_Normal.png"
        distortionMap = "Textures/Portals/${PortalName}_Distort.png"
    }
    particles = [ordered]@{
        count = $finalParticleCount
        spawnShape = "ellipse"
        spawnRadiusInner = 0.2
        spawnRadiusOuter = 0.9
        motion = $finalMotion
        speedMin = 0.4
        speedMax = 1.2
        lifetimeMin = 30
        lifetimeMax = 90
        sizeStart = 0.5
        sizeEnd = 0.1
        alphaStart = 0.0
        alphaPeak = 0.8
        alphaEnd = 0.0
        colors = [ordered]@{
            core = $presetConfig.CoreColor
            rim = $presetConfig.RimColor
            accent = $presetConfig.AccentColor
        }
    }
    shader = [ordered]@{
        type = "distortion"
        distortStrength = $finalDistort
        waveFrequency = $finalWave
        chromaticAbberation = $finalChromatic
    }
}

if ($Animated) {
    $portalProfile.tiles["animated"] = $true
    $portalProfile.tiles["animationFrames"] = $AnimationFrames
    $portalProfile.tiles["baseTexture"] = "Textures/Portals/${PortalName}_Base_Animated.png"
}

$profileJson = $portalProfile | ConvertTo-Json -Depth 10
$profileFile = Join-Path $portalDir "${PortalName}_profile.json"
$profileJson | Out-File -FilePath $profileFile -Encoding UTF8 -Force
Write-Host ""
Write-Host "[Created] ${PortalName}_profile.json" -ForegroundColor Green

# ============================================================================
# Generate Textures
# ============================================================================

# Procedural textures fill the generator role by default (AI/Ollama is an upgrade path).
if (-not $SkipTextures -or $GeneratePlaceholders) {
    # Base texture
    $basePath = Join-Path $textureDir "${PortalName}_Base.png"
    $success = New-PortalTexture -OutputPath $basePath -Size $TileSize `
        -CoreColor $finalCoreColor -RimColor $finalRimColor -AccentColor $finalAccentColor -Shape $Shape
    if ($success) {
        Write-Host "[Created] ${PortalName}_Base.png" -ForegroundColor Green
    }
    
    # Frame texture (slightly different)
    $framePath = Join-Path $textureDir "${PortalName}_Frame.png"
    $success = New-PortalTexture -OutputPath $framePath -Size $TileSize `
        -CoreColor $finalRimColor -RimColor $finalAccentColor -AccentColor $finalCoreColor -Shape $Shape
    if ($success) {
        Write-Host "[Created] ${PortalName}_Frame.png" -ForegroundColor Green
    }
    
    # Normal map
    $normalPath = Join-Path $textureDir "${PortalName}_Normal.png"
    $success = New-PortalTexture -OutputPath $normalPath -Size $TileSize `
        -CoreColor @(128,128,128) -RimColor @(128,128,128) -AccentColor @(128,128,128) `
        -Shape $Shape -IsNormal $true
    if ($success) {
        Write-Host "[Created] ${PortalName}_Normal.png" -ForegroundColor Green
    }
    
    # Distortion map
    $distortPath = Join-Path $textureDir "${PortalName}_Distort.png"
    $success = New-PortalTexture -OutputPath $distortPath -Size $TileSize `
        -CoreColor @(128,128,128) -RimColor @(128,128,128) -AccentColor @(128,128,128) `
        -Shape $Shape -IsDistortion $true
    if ($success) {
        Write-Host "[Created] ${PortalName}_Distort.png" -ForegroundColor Green
    }
}
else {
    Write-Host "[Info] -SkipTextures: profile/code only (no PNGs)." -ForegroundColor Yellow
}

# ============================================================================
# Emit full tModLoader mod pack (Item + Tile + System + build + loc) — not art-only
# ============================================================================

$emitScript = Join-Path $PSScriptRoot "Emit-TerrariaPortalModPack.ps1"
. $emitScript

$baseTex = Join-Path $textureDir "${PortalName}_Base.png"
$modPack = Emit-TerrariaPortalModPack `
    -PortalName $PortalName `
    -PortalDir $portalDir `
    -Description $finalDescription `
    -Preset $Preset `
    -TileSize $TileSize `
    -CoreRgb $finalCoreColor `
    -RimRgb $finalRimColor `
    -AccentRgb $finalAccentColor `
    -MotionPattern $finalMotion `
    -ParticleCount $finalParticleCount `
    -DistortStrength ([float]$finalDistort) `
    -WaveFrequency ([float]$finalWave) `
    -ChromaticAberration ([float]$finalChromatic) `
    -ProfileJsonPath $profileFile `
    -BaseTexturePath $(if (Test-Path -LiteralPath $baseTex) { $baseTex } else { "" }) `
    -Animated:$Animated `
    -AnimationFrames $AnimationFrames

# Optional: generate portal SFX into the mod pack if audio tool is present
$audioGen = Join-Path $PSScriptRoot "TerrariaPortalAudioGenerator.ps1"
if ((Test-Path -LiteralPath $audioGen) -and $modPack -and $modPack.ModRoot) {
    $audioOut = Join-Path $modPack.ModRoot "Sounds\Custom"
    try {
        Write-Host "[Audio] Generating portal SFX into mod pack..." -ForegroundColor Cyan
        & $audioGen -PortalName $PortalName -Preset $Preset -OutputDir $audioOut -ErrorAction SilentlyContinue
    } catch {
        Write-Host "[Audio] Skipped (optional): $_" -ForegroundColor DarkYellow
    }
}

# ============================================================================
# Summary
# ============================================================================

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Generation Summary" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Portal Name: $PortalName" -ForegroundColor White
Write-Host "  Preset: $Preset" -ForegroundColor White
Write-Host "  Shape: $Shape" -ForegroundColor Yellow
Write-Host "  Motion Pattern: $finalMotion" -ForegroundColor Yellow
Write-Host "  Particle Count: $finalParticleCount" -ForegroundColor Yellow
Write-Host "  Colors:" -ForegroundColor Yellow
Write-Host "    Core: $($presetConfig.CoreColor)" -ForegroundColor Gray
Write-Host "    Rim: $($presetConfig.RimColor)" -ForegroundColor Gray
Write-Host "    Accent: $($presetConfig.AccentColor)" -ForegroundColor Gray
Write-Host ""
Write-Host "Output Directory: $portalDir" -ForegroundColor Cyan
if ($modPack) {
    Write-Host "tModLoader mod: $($modPack.ModRoot)" -ForegroundColor Green
}
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "  1. Copy $($modPack.ModName) into tModLoader ModSources" -ForegroundColor Gray
Write-Host "  2. Build the mod and enable it in-game" -ForegroundColor Gray
Write-Host "  3. Craft $($modPack.ItemClass) (Glass + Fallen Star), place tile, right-click to recall" -ForegroundColor Gray
Write-Host ""

return @{
    Success = $true
    PortalDirectory = $portalDir
    ProfileFile = $profileFile
    PortalName = $PortalName
    Preset = $Preset
    ModRoot = $(if ($modPack) { $modPack.ModRoot } else { $null })
    ModName = $(if ($modPack) { $modPack.ModName } else { $null })
}
