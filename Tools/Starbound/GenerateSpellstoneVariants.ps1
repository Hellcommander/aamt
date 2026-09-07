#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generates spellstone variants from a base template image with color modifications and animations.
    
.DESCRIPTION
    Uses a base spellstone image as a template and creates variants by:
    - Modifying colors for different elements
    - Adjusting glow intensity for strength levels
    - Creating animation frames for pulsing/swirling effects
    - Adding spellshape overlays
    
.PARAMETER BaseImagePath
    Path to the base spellstone template image
    
.PARAMETER AssetType
    Type of assets to generate: spellform, spellshape, or "all"
    
.PARAMETER Element
    Element type: fire, ice, lightning, nature, arcane, void, cosmic, temporal, or "all"
    
.PARAMETER StrengthLevel
    Strength level: weak, moderate, strong, extreme, or "all"
    
.PARAMETER GenerateAnimations
    Generate animated versions with pulsing/swirling effects
    
.PARAMETER AnimationFrames
    Number of frames for animations (default: 8)
    
.PARAMETER OutputDir
    Base output directory for generated assets
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
    [string]$OutputDir = ""  # Empty means use default from settings
)

$ErrorActionPreference = "Stop"
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

# Import shared settings from Tools root
$settingsPath = Join-Path (Split-Path -Parent $PSScriptRoot) "AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
    Write-Host "✓ Loaded shared settings" -ForegroundColor Gray
} else {
    Write-Host "⚠ Shared settings not found, using defaults" -ForegroundColor Yellow
    $script:ImageMagickPath = "E:\tools\ImageMagick"
    $script:ImageMagickExe = Join-Path $script:ImageMagickPath "magick.exe"
    $script:SpellstoneOutputDir = "F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery\assets\items\spellstones"
}

# Use default output directory from settings if not specified
if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $OutputDir = $script:SpellstoneOutputDir
}

# Use default animation frames from settings if not specified
if ($AnimationFrames -eq 0) {
    $AnimationFrames = $script:DefaultAnimationFrames
}

# Check if base image exists
if (-not (Test-Path $BaseImagePath)) {
    Write-Host "Error: Base image not found: $BaseImagePath" -ForegroundColor Red
    exit 1
}

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Spellstone Variant Generator (Template-Based)" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Base Image: $BaseImagePath" -ForegroundColor Green
Write-Host ""

# Element color mappings (RGB values for core glow and energy patterns)
$elementColors = @{
    fire = @{
        coreGlow = [System.Drawing.Color]::FromArgb(255, 255, 100, 50)      # Bright orange-red
        energyPattern = [System.Drawing.Color]::FromArgb(200, 255, 150, 0)  # Orange-yellow
        metallicAccent = [System.Drawing.Color]::FromArgb(255, 255, 200, 0)  # Gold
        intensity = 1.2
    }
    ice = @{
        coreGlow = [System.Drawing.Color]::FromArgb(255, 100, 200, 255)     # Bright cyan-blue
        energyPattern = [System.Drawing.Color]::FromArgb(200, 150, 220, 255) # Light blue
        metallicAccent = [System.Drawing.Color]::FromArgb(255, 200, 220, 255) # Silver-blue
        intensity = 0.9
    }
    lightning = @{
        coreGlow = [System.Drawing.Color]::FromArgb(255, 255, 255, 150)      # Bright yellow-white
        energyPattern = [System.Drawing.Color]::FromArgb(200, 255, 255, 100) # Yellow
        metallicAccent = [System.Drawing.Color]::FromArgb(255, 255, 220, 100) # Gold-yellow
        intensity = 1.3
    }
    nature = @{
        coreGlow = [System.Drawing.Color]::FromArgb(255, 100, 255, 150)      # Bright green
        energyPattern = [System.Drawing.Color]::FromArgb(200, 150, 255, 180) # Light green
        metallicAccent = [System.Drawing.Color]::FromArgb(255, 180, 255, 150) # Green-gold
        intensity = 1.0
    }
    arcane = @{
        coreGlow = [System.Drawing.Color]::FromArgb(255, 200, 100, 255)      # Bright purple
        energyPattern = [System.Drawing.Color]::FromArgb(200, 220, 150, 255) # Light purple
        metallicAccent = [System.Drawing.Color]::FromArgb(255, 240, 180, 255) # Purple-silver
        intensity = 1.1
    }
    void = @{
        coreGlow = [System.Drawing.Color]::FromArgb(255, 80, 50, 120)        # Dark purple-black
        energyPattern = [System.Drawing.Color]::FromArgb(200, 120, 80, 180)  # Dark purple
        metallicAccent = [System.Drawing.Color]::FromArgb(255, 150, 100, 150) # Dark purple-grey
        intensity = 0.8
    }
    cosmic = @{
        coreGlow = [System.Drawing.Color]::FromArgb(255, 200, 200, 255)      # Bright white-blue
        energyPattern = [System.Drawing.Color]::FromArgb(200, 220, 220, 255) # Light white-blue
        metallicAccent = [System.Drawing.Color]::FromArgb(255, 255, 255, 200) # Silver-white
        intensity = 1.4
    }
    temporal = @{
        coreGlow = [System.Drawing.Color]::FromArgb(255, 150, 200, 255)      # Blue-white
        energyPattern = [System.Drawing.Color]::FromArgb(200, 180, 220, 255) # Light blue-white
        metallicAccent = [System.Drawing.Color]::FromArgb(255, 200, 220, 255) # Silver-blue
        intensity = 1.0
    }
}

# Strength level modifiers (affects glow intensity and pattern complexity)
$strengthModifiers = @{
    weak = @{ intensity = 0.6; glowRadius = 0.7; patternDensity = 0.5 }
    moderate = @{ intensity = 1.0; glowRadius = 1.0; patternDensity = 1.0 }
    strong = @{ intensity = 1.4; glowRadius = 1.3; patternDensity = 1.5 }
    extreme = @{ intensity = 1.8; glowRadius = 1.6; patternDensity = 2.0 }
}

# Check if ImageMagick is available using shared settings
$imageMagickAvailable = Test-ImageMagickAvailable
$magickExe = Get-ImageMagickPath

if ($imageMagickAvailable) {
    Write-Host "✓ ImageMagick found at: $magickExe" -ForegroundColor Green
} else {
    Write-Host "⚠ ImageMagick not found at: $script:ImageMagickExe" -ForegroundColor Yellow
    Write-Host "  Will use PowerShell/C# image processing (lower quality)" -ForegroundColor Gray
    Write-Host "  Expected location: $script:ImageMagickExe" -ForegroundColor Gray
}

# Function to create element variant using ImageMagick
function Create-ElementVariant {
    param(
        [string]$InputPath,
        [string]$OutputPath,
        [hashtable]$ElementColors,
        [hashtable]$StrengthMod
    )
    
    if ($imageMagickAvailable) {
        # Use ImageMagick for color replacement
        $coreR = $ElementColors.coreGlow.R
        $coreG = $ElementColors.coreGlow.G
        $coreB = $ElementColors.coreGlow.B
        
        $energyR = $ElementColors.energyPattern.R
        $energyG = $ElementColors.energyPattern.G
        $energyB = $ElementColors.energyPattern.B
        
        $intensity = $ElementColors.intensity * $StrengthMod.intensity
        
        # Replace blue colors with element colors
        # This is a simplified approach - in practice, you'd use more sophisticated color mapping
        & $magickExe $InputPath `
            -colorspace RGB `
            -channel-matrix "1 0 0 0 1 0 0 0 1" `
            -modulate ($intensity * 100), 100, 100 `
            -colorize 0%,0%,0% `
            $OutputPath
        
        if ($LASTEXITCODE -eq 0) {
            return $true
        }
    }
    
    # Fallback: Use .NET System.Drawing for basic color adjustments
    try {
        Add-Type -AssemblyName System.Drawing
        
        $bitmap = [System.Drawing.Bitmap]::FromFile($InputPath)
        $newBitmap = New-Object System.Drawing.Bitmap($bitmap.Width, $bitmap.Height)
        
        for ($x = 0; $x -lt $bitmap.Width; $x++) {
            for ($y = 0; $y -lt $bitmap.Height; $y++) {
                $pixel = $bitmap.GetPixel($x, $y)
                
                # Detect blue glow areas (high blue component, low red/green)
                if ($pixel.B -gt 150 -and $pixel.R -lt 100 -and $pixel.G -lt 150) {
                    # Replace with element color, maintaining alpha
                    $newColor = [System.Drawing.Color]::FromArgb(
                        $pixel.A,
                        [Math]::Min(255, ($ElementColors.coreGlow.R * $StrengthMod.intensity)),
                        [Math]::Min(255, ($ElementColors.coreGlow.G * $StrengthMod.intensity)),
                        [Math]::Min(255, ($ElementColors.coreGlow.B * $StrengthMod.intensity))
                    )
                    $newBitmap.SetPixel($x, $y, $newColor)
                } else {
                    # Keep original pixel
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

# Function to create animation frames
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
        
        # Validate $OutputDir before Join-Path
        $framePath = Join-Path $OutputDir "${AssetName}_frame$($frame.ToString("
 if ([string]::IsNullOrWhiteSpace($framePath)) {
            Write-Host "  [FAIL] framePath is null (${OutputDir}: '${OutputDir}')" -ForegroundColor Red
            continue
        }
 if ([string]::IsNullOrWhiteSpace($framePath)) {
            Write-Host "  [FAIL] framePath is null (${OutputDir}: '${OutputDir}')" -ForegroundColor Red
            continue
        }
        
        # Create frame with pulsing effect
        if ($imageMagickAvailable) {
            $currentIntensity = $ElementColors.intensity * $StrengthMod.intensity * $pulseIntensity
            & $magickExe $BaseImagePath `
                -modulate ($currentIntensity * 100), 100, 100 `
                $framePath
        } else {
            # Use base variant for now (full animation would require more complex processing)
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
    
    foreach ($element in $elements) {
        if (-not $elementColors.ContainsKey($element)) {
            Write-Host "⚠ Unknown element: $element, skipping" -ForegroundColor Yellow
            continue
        }
        
        $elementColor = $elementColors[$element]
        $strengthMod = $strengthModifiers["moderate"]  # Default for spellforms
        
        $assetName = "spellstone_${element}_base"
        # Validate $OutputDir before Join-Path
        $outputDir = Join-Path $OutputDir "spellforms\base\$element"
 if ([string]::IsNullOrWhiteSpace($outputDir)) {
            Write-Host "  [FAIL] outputDir is null (${OutputDir}: '${OutputDir}')" -ForegroundColor Red
            continue
        }
 if ([string]::IsNullOrWhiteSpace($outputDir)) {
            Write-Host "  [FAIL] outputDir is null (${OutputDir}: '${OutputDir}')" -ForegroundColor Red
            continue
        }
        
        if (-not (Test-Path $outputDir)) {
            New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
        }
        
        # Validate $outputDir before Join-Path
        $outputPath = Join-Path $outputDir "${assetName}.png"
 if ([string]::IsNullOrWhiteSpace($outputPath)) {
            Write-Host "  [FAIL] outputPath is null (${outputDir}: '${outputDir}')" -ForegroundColor Red
            continue
        }
 if ([string]::IsNullOrWhiteSpace($outputPath)) {
            Write-Host "  [FAIL] outputPath is null (${outputDir}: '${outputDir}')" -ForegroundColor Red
            continue
        }
        
        Write-Host "[GEN] $assetName" -ForegroundColor Cyan
        Write-Host "      Element: $element" -ForegroundColor Gray
        
        if (Create-ElementVariant -InputPath $BaseImagePath -OutputPath $outputPath -ElementColors $elementColor -StrengthMod $strengthMod) {
            Write-Host "      ✓ Generated successfully" -ForegroundColor Green
            $generatedCount++
            
            # Generate animation if requested
            if ($GenerateAnimations) {
                Write-Host "      Generating animation frames..." -ForegroundColor Gray
                $frames = Create-AnimationFrames -BaseImagePath $outputPath -OutputDir $outputDir -AssetName $assetName -FrameCount $AnimationFrames -ElementColors $elementColor -StrengthMod $strengthMod
                Write-Host "      ✓ Generated $($frames.Count) animation frames" -ForegroundColor Green
            }
        } else {
            Write-Host "      ✗ Generation failed" -ForegroundColor Red
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
        # Validate $OutputDir before Join-Path
        $outputDir = Join-Path $OutputDir "spellshapes\overlay\$strength"
 if ([string]::IsNullOrWhiteSpace($outputDir)) {
            Write-Host "  [FAIL] outputDir is null (${OutputDir}: '${OutputDir}')" -ForegroundColor Red
            continue
        }
 if ([string]::IsNullOrWhiteSpace($outputDir)) {
            Write-Host "  [FAIL] outputDir is null (${OutputDir}: '${OutputDir}')" -ForegroundColor Red
            continue
        }
        
        if (-not (Test-Path $outputDir)) {
            New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
        }
        
        # Validate $outputDir before Join-Path
        $outputPath = Join-Path $outputDir "${assetName}.png"
 if ([string]::IsNullOrWhiteSpace($outputPath)) {
            Write-Host "  [FAIL] outputPath is null (${outputDir}: '${outputDir}')" -ForegroundColor Red
            continue
        }
 if ([string]::IsNullOrWhiteSpace($outputPath)) {
            Write-Host "  [FAIL] outputPath is null (${outputDir}: '${outputDir}')" -ForegroundColor Red
            continue
        }
        
        Write-Host "[GEN] $assetName" -ForegroundColor Cyan
        Write-Host "      Strength: $strength" -ForegroundColor Gray
        
        if (Create-ElementVariant -InputPath $BaseImagePath -OutputPath $outputPath -ElementColors $baseElementColor -StrengthMod $strengthMod) {
            Write-Host "      ✓ Generated successfully" -ForegroundColor Green
            $generatedCount++
        } else {
            Write-Host "      ✗ Generation failed" -ForegroundColor Red
            $failedCount++
        }
        
        Write-Host ""
    }
}

# Summary
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Generation Complete" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Statistics:" -ForegroundColor Yellow
Write-Host "  Generated: $generatedCount" -ForegroundColor Green
Write-Host "  Failed: $failedCount" -ForegroundColor $(if ($failedCount -gt 0) { "Red" } else { "Gray" })
Write-Host ""

if ($failedCount -eq 0) {
    Write-Host "✓ All variants generated successfully!" -ForegroundColor Green
} else {
    Write-Host "⚠ Some variants failed to generate. Check errors above." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Assets are organized in:" -ForegroundColor Cyan
Write-Host "  $OutputDir" -ForegroundColor Gray
Write-Host ""
