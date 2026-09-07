<#
.SYNOPSIS
    Exports source assets (Blender renders, textures) to spritesheets

.DESCRIPTION
    This tool exports previously generated source assets to spritesheets.
    It preserves high-quality source files (Blender renders, textures) and
    allows re-exporting to spritesheets with different settings.
    
    Source files are kept in a "Source" subdirectory, while final spritesheets

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) ".\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}
    are in the main output directory.

.PARAMETER InputDir
    Directory containing source assets (Blender renders, textures)

.PARAMETER OutputDir
    Output directory for spritesheets

.PARAMETER AssetName
    Name of the asset (used for output filenames)

.PARAMETER Columns
    Number of columns in spritesheet

.PARAMETER Rows
    Number of rows in spritesheet (auto-calculated if not specified)

.PARAMETER FrameWidth
    Width of each frame in pixels

.PARAMETER FrameHeight
    Height of each frame in pixels

.PARAMETER BlenderPath
    Path to Blender executable (optional, for re-rendering if needed)

.PARAMETER KeepSourceFiles
    Keep source files after export (default: true)

.PARAMETER CleanLowQuality
    Remove lower quality intermediate files (default: true)

.EXAMPLE
    .\ExportToSpritesheet.ps1 -InputDir "Output\SpaceWhaleAssets\Source" -AssetName "SpaceWhale" -Columns 10 -Rows 12

.EXAMPLE
    .\ExportToSpritesheet.ps1 -InputDir "Output\SpaceWhaleAssets" -OutputDir "Output\SpaceWhaleAssets\Spritesheets" -Columns 10
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$InputDir,
    
    [Parameter(Mandatory=$false)]
    [string]$OutputDir = "",
    
    [Parameter(Mandatory=$false)]
    [string]$AssetName = "",
    
    [Parameter(Mandatory=$false)]
    [int]$Columns = 10,
    
    [Parameter(Mandatory=$false)]
    [int]$Rows = 0,  # Auto-calculate if 0
    
    [Parameter(Mandatory=$false)]
    [int]$FrameWidth = 150,
    
    [Parameter(Mandatory=$false)]
    [int]$FrameHeight = 150,
    
    [Parameter(Mandatory=$false)]
    [string]$BlenderPath = "",
    
    [Parameter(Mandatory=$false)]
    [switch]$KeepSourceFiles = $true,
    
    [Parameter(Mandatory=$false)]
    [switch]$CleanLowQuality = $true,
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("PNG", "JPG", "BMP")]
    [string]$OutputFormat = "PNG"
)

$ErrorActionPreference = "Continue"

# ============================================================
# HELPER FUNCTIONS
# ============================================================

function Write-Status {
    param(
        [string]$Message,
        [ValidateSet("Info", "Success", "Warning", "Error")]
        [string]$Type = "Info"
    )
    
    $color = switch ($Type) {
        "Success" { "Green" }
        "Warning" { "Yellow" }
        "Error"   { "Red" }
        default   { "Cyan" }
    }
    
    Write-Host "[$Type] $Message" -ForegroundColor $color
}

function Get-SourceFiles {
    param([string]$Dir)
    
    # Look for source files in common locations
    $sourceFiles = @()
    
    # Check for Blender renders
    $blenderRenders = Get-ChildItem -Path $Dir -Recurse -Include "*.png", "*.jpg", "*.bmp" -File | 
        Where-Object { 
            $_.DirectoryName -like "*Source*" -or 
            $_.DirectoryName -like "*Render*" -or 
            $_.DirectoryName -like "*Blender*" -or
            $_.Name -like "*render*" -or
            $_.Name -like "*frame*"
        }
    
    # Check for texture files
    $textureFiles = Get-ChildItem -Path $Dir -Recurse -Include "*.png", "*.jpg", "*.tga", "*.bmp" -File | 
        Where-Object { 
            $_.DirectoryName -like "*Texture*" -or 
            $_.Name -like "*texture*" -or
            $_.Name -like "*diffuse*" -or
            $_.Name -like "*normal*"
        }
    
    # Check for Blender .blend files
    $blendFiles = Get-ChildItem -Path $Dir -Recurse -Filter "*.blend" -File
    
    # Combine and return
    $sourceFiles = $blenderRenders + $textureFiles + $blendFiles
    
    return $sourceFiles | Sort-Object FullName
}

function Remove-LowQualityFiles {
    param(
        [string]$Dir,
        [array]$SourceFiles
    )
    
    if (-not $CleanLowQuality) {
        return
    }
    
    Write-Status "Cleaning low-quality intermediate files..." "Info"
    
    # Files to remove (lower quality versions)
    $patternsToRemove = @(
        "*_low.png",
        "*_low.jpg",
        "*_preview.png",
        "*_preview.jpg",
        "*_thumb.png",
        "*_thumb.jpg",
        "*_temp.png",
        "*_temp.jpg",
        "*_tmp.png",
        "*_tmp.jpg",
        "*_draft.png",
        "*_draft.jpg"
    )
    
    $removedCount = 0
    foreach ($pattern in $patternsToRemove) {
        $files = Get-ChildItem -Path $Dir -Recurse -Filter $pattern -File -ErrorAction SilentlyContinue
        foreach ($file in $files) {
            # Don't remove if it's in our source files list
            $isSource = $SourceFiles | Where-Object { $_.FullName -eq $file.FullName }
            if (-not $isSource) {
                try {
                    Remove-Item -Path $file.FullName -Force -ErrorAction SilentlyContinue
                    $removedCount++
                } catch {
                    # Ignore errors
                }
            }
        }
    }
    
    if ($removedCount -gt 0) {
        Write-Status "Removed $removedCount low-quality intermediate files" "Success"
    }
}

function Organize-SourceFiles {
    param(
        [string]$OutputDir,
        [array]$SourceFiles
    )
    
    if ($SourceFiles.Count -eq 0) {
        return
    }
    
    Write-Status "Organizing source files..." "Info"
    
    # Create Source subdirectory
    $sourceDir = Join-Path $OutputDir "Source"
    if (-not (Test-Path $sourceDir)) {
        New-Item -ItemType Directory -Path $sourceDir -Force | Out-Null
    }
    
    # Organize by type
    $blenderDir = Join-Path $sourceDir "Blender"
    $textureDir = Join-Path $sourceDir "Textures"
    $modelDir = Join-Path $sourceDir "Models"
    
    foreach ($dir in @($blenderDir, $textureDir, $modelDir)) {
        if (-not (Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
        }
    }
    
    $organizedCount = 0
    foreach ($file in $SourceFiles) {
        try {
            $destDir = $null
            
            # Determine destination based on file type/location
            if ($file.Extension -eq ".blend") {
                $destDir = $modelDir
            } elseif ($file.DirectoryName -like "*Render*" -or $file.DirectoryName -like "*Blender*" -or $file.Name -like "*render*" -or $file.Name -like "*frame*") {
                $destDir = $blenderDir
            } elseif ($file.DirectoryName -like "*Texture*" -or $file.Name -like "*texture*" -or $file.Name -like "*diffuse*" -or $file.Name -like "*normal*") {
                $destDir = $textureDir
            } else {
                # Default to Blender renders
                $destDir = $blenderDir
            }
            
            $destPath = Join-Path $destDir $file.Name
            
            # Copy if not already there
            if (-not (Test-Path $destPath)) {
                Copy-Item -Path $file.FullName -Destination $destPath -Force -ErrorAction SilentlyContinue
                $organizedCount++
            }
        } catch {
            Write-Status "Error organizing $($file.Name): $_" "Warning"
        }
    }
    
    if ($organizedCount -gt 0) {
        Write-Status "Organized $organizedCount source files into Source directory" "Success"
    }
}

function Export-Spritesheet {
    param(
        [string]$InputDir,
        [string]$OutputDir,
        [string]$AssetName,
        [int]$Columns,
        [int]$Rows,
        [int]$FrameWidth,
        [int]$FrameHeight,
        [string]$OutputFormat
    )
    
    Write-Status "Exporting spritesheet..." "Info"
    
    # Find source images
    $sourceFiles = Get-SourceFiles -Dir $InputDir
    
    if ($sourceFiles.Count -eq 0) {
        Write-Status "No source files found in $InputDir" "Error"
        return $false
    }
    
    Write-Status "Found $($sourceFiles.Count) source files" "Info"
    
    # Sort files by name to ensure correct order
    $sortedFiles = $sourceFiles | Sort-Object Name
    
    # Calculate rows if not specified
    if ($Rows -eq 0) {
        $Rows = [Math]::Ceiling($sortedFiles.Count / $Columns)
    }
    
    $spritesheetWidth = $Columns * $FrameWidth
    $spritesheetHeight = $Rows * $FrameHeight
    
    Write-Status "Spritesheet dimensions: ${spritesheetWidth}x${spritesheetHeight}" "Info"
    Write-Status "Layout: ${Columns} columns x ${Rows} rows" "Info"
    
    # Check if Python/Pillow is available
    $pythonCmd = Get-Command "python" -ErrorAction SilentlyContinue
    if (-not $pythonCmd) {
        $pythonCmd = Get-Command "python3" -ErrorAction SilentlyContinue
    }
    
    if (-not $pythonCmd) {
        Write-Status "Python not found. Install Python to export spritesheets." "Error"
        return $false
    }
    
    # Use CrossGameSpritesheet tool if available
    $spritesheetScript = Join-Path $PSScriptRoot "Common\CrossGameSpritesheet.ps1"
    if (Test-Path $spritesheetScript) {
        Write-Status "Using CrossGameSpritesheet tool..." "Info"
        
        $outputName = if ($AssetName) { $AssetName } else { "spritesheet" }
        $outputFile = Join-Path $OutputDir "${outputName}.$($OutputFormat.ToLower())"
        
        # Create a temporary directory with sorted source files
        $tempDir = Join-Path $env:TEMP "SpritesheetExport_$([Guid]::NewGuid().ToString('N').Substring(0,8))"
        New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
        
        try {
            # Copy sorted files to temp directory with numbered names
            $index = 0
            foreach ($file in $sortedFiles) {
                $ext = $file.Extension
                $newName = "{0:D4}{1}" -f $index, $ext
                Copy-Item -Path $file.FullName -Destination (Join-Path $tempDir $newName) -Force
                $index++
            }
            
            # Call CrossGameSpritesheet
            & $spritesheetScript -InputDir $tempDir -OutputDir $OutputDir -GameFormat "Terraria" -TileSize $FrameWidth -Columns $Columns -SpritesheetName $outputName
            
            # Clean up temp directory
            Remove-Item -Path $tempDir -Recurse -Force -ErrorAction SilentlyContinue
            
            Write-Status "Spritesheet exported: $outputFile" "Success"
            return $true
        } catch {
            Write-Status "Error exporting spritesheet: $_" "Error"
            # Clean up temp directory
            if (Test-Path $tempDir) {
                Remove-Item -Path $tempDir -Recurse -Force -ErrorAction SilentlyContinue
            }
            return $false
        }
    } else {
        Write-Status "CrossGameSpritesheet tool not found. Manual export required." "Warning"
        return $false
    }
}

# ============================================================
# MAIN EXECUTION
# ============================================================

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Export to Spritesheet" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Validate input directory
if (-not (Test-Path $InputDir)) {
    Write-Status "Input directory not found: $InputDir" "Error"
    exit 1
}

# Set output directory
if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $OutputDir = $InputDir
}

# Create output directory if needed
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

Write-Status "Input: $InputDir" "Info"
Write-Status "Output: $OutputDir" "Info"
Write-Host ""

# Get source files
$sourceFiles = Get-SourceFiles -Dir $InputDir

if ($sourceFiles.Count -eq 0) {
    Write-Status "No source files found. Nothing to export." "Warning"
    exit 0
}

Write-Status "Found $($sourceFiles.Count) source files" "Info"
Write-Host ""

# Organize source files
if ($KeepSourceFiles) {
    Organize-SourceFiles -OutputDir $OutputDir -SourceFiles $sourceFiles
    Write-Host ""
}

# Remove low quality files
if ($CleanLowQuality) {
    Remove-LowQualityFiles -Dir $InputDir -SourceFiles $sourceFiles
    Write-Host ""
}

# Export spritesheet
$success = Export-Spritesheet -InputDir $InputDir -OutputDir $OutputDir -AssetName $AssetName -Columns $Columns -Rows $Rows -FrameWidth $FrameWidth -FrameHeight $FrameHeight -OutputFormat $OutputFormat

Write-Host ""
if ($success) {
    Write-Status "Export complete!" "Success"
    Write-Status "Source files preserved in: $(Join-Path $OutputDir 'Source')" "Info"
} else {
    Write-Status "Export failed. Check errors above." "Error"
    exit 1
}

Write-Host ""

