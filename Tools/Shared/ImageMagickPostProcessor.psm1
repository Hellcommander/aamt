# ImageMagick Post-Processor Module
# Standardized post-processing for all AI-generated images
# Ensures consistent format, quality, and game compatibility

# Import unified tool detection if available
$toolDetectionPath = Join-Path $PSScriptRoot "ToolDetection.psm1"
if (Test-Path $toolDetectionPath) {
    Import-Module $toolDetectionPath -ErrorAction SilentlyContinue
}

# Load shared settings
$toolsRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$settingsPath = Join-Path $toolsRoot "AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}

<#
.SYNOPSIS
    Post-processes AI-generated images using ImageMagick for game compatibility.
    
.DESCRIPTION
    Standardizes all AI-generated images through ImageMagick processing:
    - Format conversion (to PNG with proper bit depth)
    - Size normalization
    - Color space optimization
    - Quality optimization
    - Alpha channel handling
    - Game-specific format requirements
    
.PARAMETER InputPath
    Path to the AI-generated image file
    
.PARAMETER OutputPath
    Output path for processed image (default: overwrites input)
    
.PARAMETER TargetSize
    Target size as "WxH" or "W" for square (default: preserve original)
    
.PARAMETER Format
    Output format: PNG, JPG, etc. (default: PNG)
    
.PARAMETER Quality
    Quality level: low, medium, high, ultra (default: high)
    
.PARAMETER GameType
    Game type for format requirements: Starbound, Qud, Terraria, etc.
    
.EXAMPLE
    Process-AIGeneratedImage -InputPath "ai_output.jpg" -OutputPath "processed.png" -GameType "Starbound"
#>
function Process-AIGeneratedImage {
    param(
        [Parameter(Mandatory=$true)]
        [string]$InputPath,
        
        [Parameter(Mandatory=$false)]
        [string]$OutputPath = "",
        
        [Parameter(Mandatory=$false)]
        [string]$TargetSize = "",
        
        [Parameter(Mandatory=$false)]
        [ValidateSet("PNG", "JPG", "JPEG", "GIF", "WEBP")]
        [string]$Format = "PNG",
        
        [Parameter(Mandatory=$false)]
        [ValidateSet("low", "medium", "high", "ultra")]
        [string]$Quality = "high",
        
        [Parameter(Mandatory=$false)]
        [ValidateSet("Starbound", "Qud", "Terraria", "CDDA", "Soulash", "Elin", "Generic")]
        [string]$GameType = "Starbound"
    )
    
    if (-not (Test-Path $InputPath)) {
        Write-Error "Input file not found: $InputPath"
        return $false
    }
    
    # Use output path or overwrite input
    if ([string]::IsNullOrWhiteSpace($OutputPath)) {
        $OutputPath = $InputPath
    }
    
    # Get ImageMagick executable
    $magickExe = Get-ImageMagickPath
    if (-not $magickExe) {
        Write-Warning "ImageMagick not available. Skipping post-processing for: $InputPath"
        return $false
    }
    
    # Game-specific format requirements
    $gameSettings = @{
        "Starbound" = @{
            Format = "PNG"
            BitDepth = 8
            Colorspace = "sRGB"
            Compression = "zip"
            MaxSize = "2048x2048"
        }
        "Qud" = @{
            Format = "PNG"
            BitDepth = 8
            Colorspace = "sRGB"
            Compression = "zip"
            MaxSize = "512x512"
        }
        "Terraria" = @{
            Format = "PNG"
            BitDepth = 8
            Colorspace = "sRGB"
            Compression = "zip"
            MaxSize = "1024x1024"
        }
        "CDDA" = @{
            Format = "PNG"
            BitDepth = 8
            Colorspace = "sRGB"
            Compression = "zip"
            MaxSize = "32x32"
        }
        "Soulash" = @{
            Format = "PNG"
            BitDepth = 8
            Colorspace = "sRGB"
            Compression = "zip"
            MaxSize = "512x512"
        }
        "Elin" = @{
            Format = "PNG"
            BitDepth = 8
            Colorspace = "sRGB"
            Compression = "zip"
            MaxSize = "1024x1024"
        }
        "Generic" = @{
            Format = "PNG"
            BitDepth = 8
            Colorspace = "sRGB"
            Compression = "zip"
            MaxSize = "2048x2048"
        }
    }
    
    $settings = $gameSettings[$GameType]
    
    # Quality settings
    $qualitySettings = @{
        "low" = @{ Quality = 60; Compression = "fast" }
        "medium" = @{ Quality = 75; Compression = "medium" }
        "high" = @{ Quality = 90; Compression = "zip" }
        "ultra" = @{ Quality = 100; Compression = "zip" }
    }
    
    $qSettings = $qualitySettings[$Quality]
    
    # Build ImageMagick command
    $magickArgs = @()
    
    # Input file
    $magickArgs += "`"$InputPath`""
    
    # Color space conversion
    $magickArgs += "-colorspace"
    $magickArgs += $settings.Colorspace
    
    # Resize if specified
    if (-not [string]::IsNullOrWhiteSpace($TargetSize)) {
        $magickArgs += "-resize"
        if ($TargetSize -match "^\d+$") {
            $magickArgs += "${TargetSize}x${TargetSize}"
        } else {
            $magickArgs += $TargetSize
        }
        $magickArgs += "-filter"
        $magickArgs += "Lanczos"  # High-quality resampling
    }
    
    # Ensure max size for game
    if ($settings.MaxSize) {
        $magickArgs += "-resize"
        $magickArgs += "$($settings.MaxSize)>"  # Only shrink if larger
    }
    
    # Format and quality
    if ($Format -eq "PNG") {
        $magickArgs += "-depth"
        $magickArgs += $settings.BitDepth
        $magickArgs += "-define"
        $magickArgs += "png:compression-level=9"
        $magickArgs += "-define"
        $magickArgs += "png:compression-strategy=1"
    } elseif ($Format -eq "JPG" -or $Format -eq "JPEG") {
        $magickArgs += "-quality"
        $magickArgs += $qSettings.Quality
    }
    
    # Strip metadata (reduce file size, privacy)
    $magickArgs += "-strip"
    
    # Alpha channel handling (preserve if exists)
    $magickArgs += "-alpha"
    $magickArgs += "on"
    
    # Output file
    $magickArgs += "`"$OutputPath`""
    
    try {
        Write-Host "  Post-processing with ImageMagick..." -ForegroundColor Gray
        & $magickExe $magickArgs 2>&1 | Out-Null
        
        if ($LASTEXITCODE -eq 0 -and (Test-Path $OutputPath)) {
            $inputSize = (Get-Item $InputPath).Length / 1KB
            $outputSize = (Get-Item $OutputPath).Length / 1KB
            Write-Host "  ✓ Processed: $([Math]::Round($inputSize, 1))KB → $([Math]::Round($outputSize, 1))KB" -ForegroundColor Green
            return $true
        } else {
            Write-Warning "ImageMagick processing failed for: $InputPath"
            return $false
        }
    } catch {
        Write-Warning "Error processing image: $_"
        return $false
    }
}

<#
.SYNOPSIS
    Batch processes multiple AI-generated images.
    
.PARAMETER InputPaths
    Array of input image paths
    
.PARAMETER OutputDir
    Output directory (default: same as input)
    
.PARAMETER GameType
    Game type for format requirements
#>
function Process-AIGeneratedImages {
    param(
        [Parameter(Mandatory=$true)]
        [string[]]$InputPaths,
        
        [Parameter(Mandatory=$false)]
        [string]$OutputDir = "",
        
        [Parameter(Mandatory=$false)]
        [string]$GameType = "Starbound"
    )
    
    $processed = 0
    $failed = 0
    
    foreach ($inputPath in $InputPaths) {
        if (-not (Test-Path $inputPath)) {
            Write-Warning "Skipping missing file: $inputPath"
            $failed++
            continue
        }
        
        $outputPath = $inputPath
        if (-not [string]::IsNullOrWhiteSpace($OutputDir)) {
            $fileName = Split-Path -Leaf $inputPath
            $outputPath = Join-Path $OutputDir $fileName
        }
        
        if (Process-AIGeneratedImage -InputPath $inputPath -OutputPath $outputPath -GameType $GameType) {
            $processed++
        } else {
            $failed++
        }
    }
    
    Write-Host ""
    Write-Host "Batch processing complete:" -ForegroundColor Cyan
    Write-Host "  Processed: $processed" -ForegroundColor Green
    Write-Host "  Failed: $failed" -ForegroundColor $(if ($failed -gt 0) { "Red" } else { "Gray" })
    
    return @{
        Processed = $processed
        Failed = $failed
    }
}

Export-ModuleMember -Function Process-AIGeneratedImage, Process-AIGeneratedImages
