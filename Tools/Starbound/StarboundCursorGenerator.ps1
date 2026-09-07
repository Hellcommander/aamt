<#
.SYNOPSIS
    Starbound Cursor Generator - Creates cursor files for custom mouse cursors

.DESCRIPTION
    Generates .cursor and .frames files for Starbound/OpenStarbound with support for:
    - Static cursors (single image)
    - Animated cursors (multiple frames)
    - Named frame states (neutral, hover, click, etc.)
    - Customizable hotspot offset

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}
    - Placeholder image generation

.PARAMETER CursorName
    Name of the cursor (used for filename)

.PARAMETER Preset
    Built-in cursor preset to use

.PARAMETER OutputDir
    Output directory for generated files

.EXAMPLE
    .\StarboundCursorGenerator.ps1 -CursorName "mycursor" -Preset Default
    .\StarboundCursorGenerator.ps1 -CursorName "joystick" -Preset Joystick -FrameSize @(30,30)
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$CursorName,

    [Parameter(Mandatory=$false)]
    [ValidateSet("Default", "Pointer", "Crosshair", "Joystick", "Hand", "Text", "Wait", "Move", "Resize", "Custom")]
    [string]$Preset = "Default",

    [Parameter(Mandatory=$false)]
    [string]$OutputDir = "StarboundCursors",

    # Cursor properties
    [Parameter(Mandatory=$false)]
    [array]$Offset = $null,  # Hotspot offset [x, y] - if null, auto-calculated

    [Parameter(Mandatory=$false)]
    [array]$FrameSize = @(16, 16),  # Size of each frame [width, height]

    [Parameter(Mandatory=$false)]
    [array]$FrameNames = $null,  # Custom frame names

    [Parameter(Mandatory=$false)]
    [int]$FrameColumns = 1,  # Number of columns in spritesheet

    [Parameter(Mandatory=$false)]
    [int]$FrameRows = 1,  # Number of rows in spritesheet

    [Parameter(Mandatory=$false)]
    [string]$DefaultFrame = "",  # Default frame to display

    [Parameter(Mandatory=$false)]
    [string]$ImagePath = "",  # Path to existing image (relative to assets)

    [Parameter(Mandatory=$false)]
    [switch]$GeneratePlaceholderImage,  # Generate a placeholder PNG

    [Parameter(Mandatory=$false)]
    [switch]$Animated  # Whether cursor has multiple states
)

# Import shared Ollama integration module if available
$toolsRoot = Split-Path -Parent $PSScriptRoot
$sharedModulePath = Join-Path $toolsRoot "Shared\OllamaIntegration.psm1"
if (Test-Path $sharedModulePath) {
    Import-Module $sharedModulePath -Force -ErrorAction SilentlyContinue
    if (Get-Command Test-OllamaConnection -ErrorAction SilentlyContinue) {
        if (-not (Test-OllamaConnection)) {
            Initialize-OllamaModels
        }
    }
}

# ============================================================================
# PRESET DEFINITIONS
# ============================================================================

$CursorPresets = @{
    "Default" = @{
        FrameSize = @(16, 16)
        Offset = @(0, 0)  # Top-left hotspot
        FrameNames = @(@("default"))
        Columns = 1
        Rows = 1
        DefaultFrame = "default"
    }
    "Pointer" = @{
        FrameSize = @(16, 16)
        Offset = @(1, 1)  # Near top-left for pointer tip
        FrameNames = @(@("normal", "hover", "click"))
        Columns = 3
        Rows = 1
        DefaultFrame = "normal"
    }
    "Crosshair" = @{
        FrameSize = @(32, 32)
        Offset = @(16, 16)  # Center
        FrameNames = @(@("default", "active"))
        Columns = 2
        Rows = 1
        DefaultFrame = "default"
    }
    "Joystick" = @{
        FrameSize = @(30, 30)
        Offset = @(15, 15)  # Center
        FrameNames = @(@("neutral", "down", "up", "left", "right"))
        Columns = 5
        Rows = 1
        DefaultFrame = "neutral"
    }
    "Hand" = @{
        FrameSize = @(24, 24)
        Offset = @(8, 4)  # Pointing finger tip
        FrameNames = @(@("open", "pointing", "grabbing"))
        Columns = 3
        Rows = 1
        DefaultFrame = "open"
    }
    "Text" = @{
        FrameSize = @(8, 16)
        Offset = @(4, 8)  # Center of I-beam
        FrameNames = @(@("default"))
        Columns = 1
        Rows = 1
        DefaultFrame = "default"
    }
    "Wait" = @{
        FrameSize = @(24, 24)
        Offset = @(12, 12)  # Center
        FrameNames = @(@("frame1", "frame2", "frame3", "frame4", "frame5", "frame6", "frame7", "frame8"))
        Columns = 8
        Rows = 1
        DefaultFrame = "frame1"
    }
    "Move" = @{
        FrameSize = @(24, 24)
        Offset = @(12, 12)  # Center
        FrameNames = @(@("default"))
        Columns = 1
        Rows = 1
        DefaultFrame = "default"
    }
    "Resize" = @{
        FrameSize = @(24, 24)
        Offset = @(12, 12)  # Center
        FrameNames = @(@("horizontal", "vertical", "diagonal1", "diagonal2"))
        Columns = 4
        Rows = 1
        DefaultFrame = "horizontal"
    }
    "Custom" = @{
        FrameSize = @(16, 16)
        Offset = @(0, 0)
        FrameNames = @(@("default"))
        Columns = 1
        Rows = 1
        DefaultFrame = "default"
    }
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

function New-PlaceholderCursorImage {
    param(
        [string]$OutputPath,
        [int]$Width,
        [int]$Height,
        [int]$Columns,
        [int]$Rows,
        [string]$Style = "crosshair"
    )
    
    try {
        Add-Type -AssemblyName System.Drawing

        # Force scalars — PowerShell array indexing / hashtable values can leak Object[]
        $w = [int]$Width
        $h = [int]$Height
        $cols = [int]$Columns
        $rows = [int]$Rows
        
        $totalWidth = $w * $cols
        $totalHeight = $h * $rows
        
        $bitmap = New-Object System.Drawing.Bitmap($totalWidth, $totalHeight)
        $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
        
        # Transparent background
        $graphics.Clear([System.Drawing.Color]::Transparent)
        
        # Draw each frame
        for ($row = 0; $row -lt $rows; $row++) {
            for ($col = 0; $col -lt $cols; $col++) {
                $x = [int]($col * $w)
                $y = [int]($row * $h)
                $centerX = $x + [int]($w / 2)
                $centerY = $y + [int]($h / 2)
                
                # Different colors for each frame
                $hue = [int]((($row * $cols + $col) * 40) % 360)
                $color = [System.Drawing.Color]::FromArgb(255, 
                    [int](255 * [Math]::Abs([Math]::Sin($hue * [Math]::PI / 180))),
                    [int](255 * [Math]::Abs([Math]::Sin(($hue + 120) * [Math]::PI / 180))),
                    [int](255 * [Math]::Abs([Math]::Sin(($hue + 240) * [Math]::PI / 180)))
                )
                
                $pen = New-Object System.Drawing.Pen($color, 2)
                $brush = New-Object System.Drawing.SolidBrush($color)
                
                switch ($Style) {
                    "crosshair" {
                        # Draw crosshair
                        $graphics.DrawLine($pen, $centerX, $y + 2, $centerX, $y + $h - 2)
                        $graphics.DrawLine($pen, $x + 2, $centerY, $x + $w - 2, $centerY)
                        # Center dot
                        $graphics.FillEllipse($brush, $centerX - 2, $centerY - 2, 4, 4)
                    }
                    "pointer" {
                        # Draw simple pointer triangle
                        $points = [System.Drawing.Point[]]@(
                            [System.Drawing.Point]::new(($x + 2), ($y + 2)),
                            [System.Drawing.Point]::new(($x + 2), ($y + $h - 4)),
                            [System.Drawing.Point]::new(($x + $w - 4), ($y + [int]($h / 2)))
                        )
                        $graphics.FillPolygon($brush, $points)
                    }
                    "joystick" {
                        # Draw joystick circle with direction indicator
                        $graphics.DrawEllipse($pen, $x + 4, $y + 4, $w - 8, $h - 8)
                        
                        # Direction indicator based on frame index
                        $frameIndex = $row * $cols + $col
                        $indicatorX = $centerX
                        $indicatorY = $centerY
                        
                        switch ($frameIndex) {
                            1 { $indicatorY = $centerY + 5 }  # down
                            2 { $indicatorY = $centerY - 5 }  # up
                            3 { $indicatorX = $centerX - 5 }  # left
                            4 { $indicatorX = $centerX + 5 }  # right
                        }
                        
                        $graphics.FillEllipse($brush, $indicatorX - 3, $indicatorY - 3, 6, 6)
                    }
                    default {
                        # Simple box with X
                        $graphics.DrawRectangle($pen, $x + 2, $y + 2, $w - 4, $h - 4)
                        $graphics.DrawLine($pen, $x + 2, $y + 2, $x + $w - 2, $y + $h - 2)
                        $graphics.DrawLine($pen, $x + $w - 2, $y + 2, $x + 2, $y + $h - 2)
                    }
                }
                
                $pen.Dispose()
                $brush.Dispose()
            }
        }
        
        $bitmap.Save($OutputPath, [System.Drawing.Imaging.ImageFormat]::Png)
        $graphics.Dispose()
        $bitmap.Dispose()
        
        return $true
    }
    catch {
        Write-Host "[Warning] Could not generate procedural cursor image: $_" -ForegroundColor Yellow
        return $false
    }
}

# ============================================================================
# MAIN GENERATION LOGIC
# ============================================================================

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Starbound Cursor Generator" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Create output directory
$outputPath = $OutputDir
if (-not [System.IO.Path]::IsPathRooted($OutputDir)) {
    $outputPath = Join-Path (Get-Location) $OutputDir
}

if (-not (Test-Path $outputPath)) {
    New-Item -ItemType Directory -Path $outputPath -Force | Out-Null
    Write-Host "[Created] Output directory: $outputPath" -ForegroundColor Green
}

# Apply preset
$presetConfig = $CursorPresets[$Preset]

# Override with custom parameters if provided
$finalFrameSize = if ($FrameSize[0] -ne 16 -or $FrameSize[1] -ne 16) { $FrameSize } else { $presetConfig.FrameSize }
$finalOffset = if ($Offset) { $Offset } else { $presetConfig.Offset }
$finalFrameNames = if ($FrameNames) { $FrameNames } else { $presetConfig.FrameNames }
$finalColumns = if ($FrameColumns -ne 1) { $FrameColumns } else { $presetConfig.Columns }
$finalRows = if ($FrameRows -ne 1) { $FrameRows } else { $presetConfig.Rows }
$finalDefaultFrame = if ($DefaultFrame) { $DefaultFrame } else { $presetConfig.DefaultFrame }

# Calculate total frame count
$totalFrames = 0
foreach ($row in $finalFrameNames) {
    $totalFrames += $row.Count
}

$hasMultipleFrames = $totalFrames -gt 1 -or $Animated

Write-Host "[Generating] Cursor: $CursorName (Preset: $Preset)" -ForegroundColor Yellow
Write-Host "  Frame Size: $($finalFrameSize[0])x$($finalFrameSize[1])" -ForegroundColor Gray
Write-Host "  Offset: [$($finalOffset[0]), $($finalOffset[1])]" -ForegroundColor Gray
Write-Host "  Frames: $totalFrames ($finalColumns x $finalRows)" -ForegroundColor Gray

# ============================================================================
# Generate .cursor file
# ============================================================================

$imagePath = if ($ImagePath) { 
    $ImagePath 
} else { 
    "/cursors/$CursorName.png"
}

# Add default frame to image path if cursor has named frames
$imageReference = if ($hasMultipleFrames -and $finalDefaultFrame) {
    "${imagePath}:${finalDefaultFrame}"
} else {
    $imagePath
}

$cursorData = [ordered]@{
    "offset" = $finalOffset
    "image" = $imageReference
}

$cursorJson = $cursorData | ConvertTo-Json -Depth 10
$cursorFile = Join-Path $outputPath "$CursorName.cursor"
$cursorJson | Out-File -FilePath $cursorFile -Encoding UTF8 -Force

Write-Host ""
Write-Host "[Created] $cursorFile" -ForegroundColor Green

# ============================================================================
# Generate .frames file (if multiple frames)
# ============================================================================

if ($hasMultipleFrames) {
    # Build names as proper 2D array for JSON
    # PowerShell's ConvertTo-Json flattens single-row arrays, so we build JSON manually for names
    $namesRows = @()
    if ($finalFrameNames[0] -is [array]) {
        # Already 2D
        foreach ($row in $finalFrameNames) {
            $rowJson = "[" + (($row | ForEach-Object { "`"$_`"" }) -join ", ") + "]"
            $namesRows += $rowJson
        }
    } else {
        # 1D array, wrap as single row
        $rowJson = "[" + (($finalFrameNames | ForEach-Object { "`"$_`"" }) -join ", ") + "]"
        $namesRows += $rowJson
    }
    $namesJson = "[`n      " + ($namesRows -join ",`n      ") + "`n    ]"
    
    # Build the frames JSON manually to ensure proper 2D array
    $framesJson = @"
{
  "frameGrid" : {
    "size" : [$($finalFrameSize[0]), $($finalFrameSize[1])],
    "dimensions" : [$finalColumns, $finalRows],

    "names" : $namesJson
  }
}
"@
    
    $framesFile = Join-Path $outputPath "$CursorName.frames"
    $framesJson | Out-File -FilePath $framesFile -Encoding UTF8 -Force
    
    Write-Host "[Created] $framesFile" -ForegroundColor Green
}

# ============================================================================
# Use Ollama for intelligent cursor design if requested
# ============================================================================

$script:cursorDesign = $null
if ($UseOllama -and (-not [string]::IsNullOrEmpty($Description))) {
    Write-Host "Using Ollama for intelligent cursor design..." -ForegroundColor Cyan
    
    if (Get-Command Invoke-OllamaRequest -ErrorAction SilentlyContinue) {
        $cursorPrompt = "You are designing a cursor for a Starbound game mod named '$CursorName'.
Description: $Description
Cursor Size: $($finalFrameSize[0])x$($finalFrameSize[1]) pixels
States: $totalFrames

Generate a visual design specification in JSON:
{
  'ColorPalette': [[R,G,B], [R,G,B]] - 2 colors for the cursor,
  'CursorStyle': string - style (pointer, crosshair, joystick, etc.),
  'VisualDescription': string - how the cursor should look
}

Return ONLY the JSON object."
        
        $modelToUse = if ($VisualModel) { $VisualModel } else { $OllamaModel }
        $cursorResponse = Invoke-OllamaRequest -Prompt $cursorPrompt -TaskType "visual" -ResponseLength "short" -ModelName $modelToUse
        
        if ($cursorResponse) {
            $jsonMatch = $cursorResponse | Select-String -Pattern '\{[\s\S]*\}' | Select-Object -First 1
            if ($jsonMatch) {
                try {
                    $script:cursorDesign = $jsonMatch.Matches[0].Value | ConvertFrom-Json
                    Write-Host "AI cursor design: $($script:cursorDesign.VisualDescription)" -ForegroundColor Green
                } catch {
                    Write-Host "Could not parse AI cursor design: $_" -ForegroundColor Yellow
                }
            }
        }
    }
}

# ============================================================================
# Generate placeholder or intelligent image (optional)
# ============================================================================

# Always write a real cursor PNG (procedural art fills the role)
if ($true) {
    $pngFile = Join-Path $outputPath "$CursorName.png"
    
    # Use AI design if available
    $style = if ($script:cursorDesign -and $script:cursorDesign.CursorStyle) {
        $script:cursorDesign.CursorStyle.ToLower()
    } else {
        switch ($Preset) {
            "Pointer" { "pointer" }
            "Joystick" { "joystick" }
            "Crosshair" { "crosshair" }
            default { "crosshair" }
        }
    }
    
    $success = New-PlaceholderCursorImage -OutputPath $pngFile `
        -Width ([int]$finalFrameSize[0]) -Height ([int]$finalFrameSize[1]) `
        -Columns ([int]$finalColumns) -Rows ([int]$finalRows) `
        -Style ([string]$style)
    
    if ($success) {
        Write-Host "[Created] $pngFile" -ForegroundColor Green
        if ($script:cursorDesign) {
            Write-Host "  AI-designed cursor" -ForegroundColor Gray
        }
    }
}

# ============================================================================
# Summary
# ============================================================================

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Generation Summary" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Cursor Name: $CursorName" -ForegroundColor White
Write-Host "  Preset: $Preset" -ForegroundColor White
Write-Host "  Frame Size: $($finalFrameSize[0])x$($finalFrameSize[1])" -ForegroundColor White
Write-Host "  Hotspot: [$($finalOffset[0]), $($finalOffset[1])]" -ForegroundColor White

if ($hasMultipleFrames) {
    Write-Host "  Frame States: $($finalFrameNames | ForEach-Object { $_ -join ', ' })" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Generated Files:" -ForegroundColor Cyan
Write-Host "  - $CursorName.cursor" -ForegroundColor White
if ($hasMultipleFrames) {
    Write-Host "  - $CursorName.frames" -ForegroundColor White
}
if (Test-Path (Join-Path $outputPath "$CursorName.png")) {
    Write-Host "  - $CursorName.png (procedural)" -ForegroundColor White
}

Write-Host ""
Write-Host "Usage in Starbound:" -ForegroundColor Cyan
Write-Host "  Set cursor in your interface config or script:" -ForegroundColor Gray
Write-Host "  cursor.setCursor(`"$imageReference`")" -ForegroundColor White
Write-Host ""

# Return result object
return @{
    Success = $true
    CursorFile = $cursorFile
    FramesFile = if ($hasMultipleFrames) { $framesFile } else { $null }
    CursorName = $CursorName
    Preset = $Preset
    FrameCount = $totalFrames
}

