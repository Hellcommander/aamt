#!/usr/bin/env pwsh
<#
.SYNOPSIS
    PowerShell wrapper for spritesheet packing tools (Aseprite, Free Texture Packer, etc.)
    Integrates with OpenStarbound asset generation pipeline

.DESCRIPTION
    Provides functions to pack individual PNG frames into spritesheets using external tools.
    Supports Aseprite CLI, Free Texture Packer, and fallback to manual packing.
    Generates Starbound-compatible .frames files.

.PARAMETER FrameFiles
    Array of PNG file paths to pack into spritesheet

.PARAMETER OutputSpritesheet
    Path to output spritesheet PNG file

.PARAMETER OutputFrames
    Path to output .frames JSON file

.PARAMETER FrameWidth
    Width of each frame in pixels (for .frames metadata)

.PARAMETER FrameHeight
    Height of each frame in pixels (for .frames metadata)

.PARAMETER Tool
    Packing tool to use: "Aseprite", "FreeTexturePacker", or "Manual"

.PARAMETER PowerOfTwo
    Enforce power-of-two atlas dimensions

.PARAMETER Padding
    Padding between frames (default: 2)

.EXAMPLE
    Pack-Spritesheet -FrameFiles @("frame1.png", "frame2.png") -OutputSpritesheet "anim.png" -OutputFrames "anim.frames" -FrameWidth 16 -FrameHeight 16
#>

param(
    [Parameter(Mandatory=$true)]
    [string[]]$FrameFiles,
    
    [Parameter(Mandatory=$true)]
    [string]$OutputSpritesheet,
    
    [Parameter(Mandatory=$true)]
    [string]$OutputFrames,
    
    [Parameter(Mandatory=$true)]
    [int]$FrameWidth,
    
    [Parameter(Mandatory=$true)]
    [int]$FrameHeight,
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("Aseprite", "FreeTexturePacker", "Manual", "Auto")]
    [string]$Tool = "Auto",
    
    [Parameter(Mandatory=$false)]
    [switch]$PowerOfTwo = $true,
    
    [Parameter(Mandatory=$false)]
    [int]$Padding = 2
)

$ErrorActionPreference = "Stop"

# Function to check if Aseprite CLI is available
function Test-AsepriteAvailable {
    try {
        $aseprite = Get-Command aseprite -ErrorAction SilentlyContinue
        if ($null -ne $aseprite) {
            # Test if it actually works
            $testResult = & aseprite --version 2>&1
            return $LASTEXITCODE -eq 0
        }
        return $false
    } catch {
        return $false
    }
}

# Function to check if Free Texture Packer CLI is available
function Test-FreeTexturePackerAvailable {
    try {
        $ftp = Get-Command free-tex-packer-cli -ErrorAction SilentlyContinue
        if ($null -ne $ftp) {
            $testResult = & free-tex-packer-cli --version 2>&1
            return $LASTEXITCODE -eq 0
        }
        return $false
    } catch {
        return $false
    }
}

# Function to auto-detect available tool
function Get-AvailablePackingTool {
    if (Test-AsepriteAvailable) {
        return "Aseprite"
    } elseif (Test-FreeTexturePackerAvailable) {
        return "FreeTexturePacker"
    } else {
        return "Manual"
    }
}

# Function to pack using Aseprite CLI
function Pack-WithAseprite {
    param(
        [string[]]$Frames,
        [string]$OutputSheet,
        [string]$OutputFramesFile,
        [int]$FrameW,
        [int]$FrameH,
        [bool]$POT,
        [int]$Pad
    )
    
    Write-Host "  Using Aseprite CLI for spritesheet packing..." -ForegroundColor Cyan
    
    # Calculate power-of-two dimensions if needed
    $frameCount = $Frames.Count
    $estimatedWidth = $FrameW * $frameCount
    $estimatedHeight = $FrameH
    
    if ($POT) {
        # Find next power-of-two
        $potWidth = [Math]::Pow(2, [Math]::Ceiling([Math]::Log($estimatedWidth, 2)))
        $potHeight = [Math]::Pow(2, [Math]::Ceiling([Math]::Log($estimatedHeight, 2)))
        $sheetWidth = [int]$potWidth
        $sheetHeight = [int]$potHeight
    } else {
        $sheetWidth = $estimatedWidth
        $sheetHeight = $estimatedHeight
    }
    
    # Build Aseprite command
    $asepriteArgs = @(
        "-b"
        "--sheet", $OutputSheet
        "--data", $OutputFramesFile
        "--format", "json-array"
        "--sheet-width", $sheetWidth.ToString()
        "--sheet-height", $sheetHeight.ToString()
        "--shape-padding", $Pad.ToString()
        "--border-padding", $Pad.ToString()
        "--trim"
        "--extrude", "1"
    )
    
    if ($POT) {
        $asepriteArgs += "--size-constraints", "POT"
    }
    
    # Add frame files
    $asepriteArgs += $Frames
    
    # Execute Aseprite
    Write-Host "    Executing: aseprite $($asepriteArgs -join ' ')" -ForegroundColor Gray
    & aseprite $asepriteArgs
    
    if ($LASTEXITCODE -ne 0) {
        throw "Aseprite CLI failed with exit code $LASTEXITCODE"
    }
    
    # Convert Aseprite JSON to Starbound .frames format if needed
    if (Test-Path $OutputFramesFile) {
        $asepriteJson = Get-Content $OutputFramesFile -Raw | ConvertFrom-Json
        
        # Aseprite exports in different formats - check if conversion needed
        # If it's already in Starbound format, use it as-is
        # Otherwise convert from Aseprite's format
        
        # Check if it's Aseprite format (has "frames" array) or Starbound format (has "frameGrid")
        $jsonContent = Get-Content $OutputFramesFile -Raw
        if ($jsonContent -match '"frames"') {
            # Convert from Aseprite format to Starbound .frames format
            Write-Host "    Converting Aseprite JSON to Starbound .frames format..." -ForegroundColor Gray
            
            $starboundFrames = @{
                frameGrid = @{
                    size = @($FrameW, $FrameH)
                    dimensions = @($frameCount, 1)
                }
                aliases = @{
                    default = 0..($frameCount - 1)
                }
            }
            
            $starboundFrames | ConvertTo-Json -Depth 10 | Set-Content -Path $OutputFramesFile -Encoding UTF8
        }
    }
    
    Write-Host "  ✓ Spritesheet packed with Aseprite: $OutputSheet" -ForegroundColor Green
    return $true
}

# Function to pack using Free Texture Packer CLI
function Pack-WithFreeTexturePacker {
    param(
        [string[]]$Frames,
        [string]$OutputSheet,
        [string]$OutputFramesFile,
        [int]$FrameW,
        [int]$FrameH,
        [bool]$POT,
        [int]$Pad
    )
    
    Write-Host "  Using Free Texture Packer CLI for spritesheet packing..." -ForegroundColor Cyan
    
    # Free Texture Packer requires a temporary directory for input
    $tempDir = Join-Path $env:TEMP "starbound_pack_$(Get-Random)"
    New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
    
    try {
        # Copy frames to temp directory
        $frameIndex = 0
        foreach ($frame in $Frames) {
            $destFrame = Join-Path $tempDir "frame_$frameIndex.png"
            Copy-Item $frame $destFrame -Force
            $frameIndex++
        }
        
        # Build Free Texture Packer command
        $outputDir = Split-Path $OutputSheet -Parent
        $outputName = [System.IO.Path]::GetFileNameWithoutExtension($OutputSheet)
        
        $ftpArgs = @(
            "--input", "$tempDir\*.png"
            "--output", $outputDir
            "--format", "json"
            "--padding", $Pad.ToString()
            "--trim"
        )
        
        if ($POT) {
            $ftpArgs += "--pot"
        }
        
        # Execute Free Texture Packer
        Write-Host "    Executing: free-tex-packer-cli $($ftpArgs -join ' ')" -ForegroundColor Gray
        & free-tex-packer-cli $ftpArgs
        
        if ($LASTEXITCODE -ne 0) {
            throw "Free Texture Packer CLI failed with exit code $LASTEXITCODE"
        }
        
        # Free Texture Packer outputs files with specific naming - find and rename
        $generatedSheet = Get-ChildItem -Path $outputDir -Filter "*.png" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($generatedSheet) {
            Copy-Item $generatedSheet.FullName $OutputSheet -Force
        }
        
        $generatedJson = Get-ChildItem -Path $outputDir -Filter "*.json" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($generatedJson) {
            # Convert Free Texture Packer JSON to Starbound .frames format
            $ftpJson = Get-Content $generatedJson.FullName -Raw | ConvertFrom-Json
            
            $frameCount = $Frames.Count
            $starboundFrames = @{
                frameGrid = @{
                    size = @($FrameW, $FrameH)
                    dimensions = @($frameCount, 1)
                }
                aliases = @{
                    default = 0..($frameCount - 1)
                }
            }
            
            $starboundFrames | ConvertTo-Json -Depth 10 | Set-Content -Path $OutputFramesFile -Encoding UTF8
        }
        
        Write-Host "  ✓ Spritesheet packed with Free Texture Packer: $OutputSheet" -ForegroundColor Green
        return $true
    } finally {
        # Cleanup temp directory
        Remove-Item -Path $tempDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}

# Function to pack manually (fallback)
function Pack-Manually {
    param(
        [string[]]$Frames,
        [string]$OutputSheet,
        [string]$OutputFramesFile,
        [int]$FrameW,
        [int]$FrameH,
        [bool]$POT,
        [int]$Pad
    )
    
    Write-Host "  Using manual packing (fallback)..." -ForegroundColor Yellow
    
    # Load System.Drawing
    Add-Type -AssemblyName System.Drawing
    
    $frameCount = $Frames.Count
    $spritesheetWidth = $FrameW * $frameCount
    $spritesheetHeight = $FrameH
    
    if ($POT) {
        $spritesheetWidth = [Math]::Pow(2, [Math]::Ceiling([Math]::Log($spritesheetWidth, 2)))
        $spritesheetHeight = [Math]::Pow(2, [Math]::Ceiling([Math]::Log($spritesheetHeight, 2)))
    }
    
    # Create spritesheet bitmap
    $spritesheet = New-Object System.Drawing.Bitmap($spritesheetWidth, $spritesheetHeight, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    $graphics = [System.Drawing.Graphics]::FromImage($spritesheet)
    $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
    $graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
    $graphics.CompositingQuality = [System.Drawing.Drawing2D.CompositingQuality]::HighQuality
    $graphics.Clear([System.Drawing.Color]::Transparent)
    
    # Draw frames onto spritesheet
    $xOffset = 0
    foreach ($framePath in $Frames) {
        if (Test-Path $framePath) {
            $frame = [System.Drawing.Image]::FromFile($framePath)
            $graphics.DrawImage($frame, $xOffset, 0, $FrameW, $FrameH)
            $frame.Dispose()
            $xOffset += $FrameW
        }
    }
    
    $graphics.Dispose()
    
    # Save spritesheet
    $pngCodec = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object { $_.MimeType -eq "image/png" }
    $encoderParams = New-Object System.Drawing.Imaging.EncoderParameters(1)
    $encoderParams.Param[0] = New-Object System.Drawing.Imaging.EncoderParameter([System.Drawing.Imaging.Encoder]::Compression, [long]0)
    $spritesheet.Save($OutputSheet, $pngCodec, $encoderParams)
    $encoderParams.Dispose()
    $spritesheet.Dispose()
    
    # Create .frames file
    $starboundFrames = @{
        frameGrid = @{
            size = @($FrameW, $FrameH)
            dimensions = @($frameCount, 1)
        }
        aliases = @{
            default = 0..($frameCount - 1)
        }
    }
    
    $starboundFrames | ConvertTo-Json -Depth 10 | Set-Content -Path $OutputFramesFile -Encoding UTF8
    
    Write-Host "  ✓ Spritesheet packed manually: $OutputSheet" -ForegroundColor Green
    return $true
}

# Main execution
try {
    # Validate frame files
    foreach ($frame in $FrameFiles) {
        if (-not (Test-Path $frame)) {
            throw "Frame file not found: $frame"
        }
    }
    
    # Auto-detect tool if needed
    if ($Tool -eq "Auto") {
        $Tool = Get-AvailablePackingTool
        Write-Host "Auto-detected packing tool: $Tool" -ForegroundColor Cyan
    }
    
    # Pack using selected tool
    switch ($Tool) {
        "Aseprite" {
            if (-not (Test-AsepriteAvailable)) {
                Write-Host "  [WARN] Aseprite not available, falling back to manual packing" -ForegroundColor Yellow
                Pack-Manually -Frames $FrameFiles -OutputSheet $OutputSpritesheet -OutputFramesFile $OutputFrames -FrameW $FrameWidth -FrameH $FrameHeight -POT $PowerOfTwo -Pad $Padding
            } else {
                Pack-WithAseprite -Frames $FrameFiles -OutputSheet $OutputSpritesheet -OutputFramesFile $OutputFrames -FrameW $FrameWidth -FrameH $FrameHeight -POT $PowerOfTwo -Pad $Padding
            }
        }
        "FreeTexturePacker" {
            if (-not (Test-FreeTexturePackerAvailable)) {
                Write-Host "  [WARN] Free Texture Packer not available, falling back to manual packing" -ForegroundColor Yellow
                Pack-Manually -Frames $FrameFiles -OutputSheet $OutputSpritesheet -OutputFramesFile $OutputFrames -FrameW $FrameWidth -FrameH $FrameHeight -POT $PowerOfTwo -Pad $Padding
            } else {
                Pack-WithFreeTexturePacker -Frames $FrameFiles -OutputSheet $OutputSpritesheet -OutputFramesFile $OutputFrames -FrameW $FrameWidth -FrameH $FrameHeight -POT $PowerOfTwo -Pad $Padding
            }
        }
        "Manual" {
            Pack-Manually -Frames $FrameFiles -OutputSheet $OutputSpritesheet -OutputFramesFile $OutputFrames -FrameW $FrameWidth -FrameH $FrameHeight -POT $PowerOfTwo -Pad $Padding
        }
        default {
            throw "Unknown packing tool: $Tool"
        }
    }
    
    Write-Host "✓ Spritesheet packing complete" -ForegroundColor Green
    return $true
    
} catch {
    Write-Host "  [ERROR] Spritesheet packing failed: $_" -ForegroundColor Red
    Write-Host "    Stack trace: $($_.ScriptStackTrace)" -ForegroundColor Gray
    return $false
}
