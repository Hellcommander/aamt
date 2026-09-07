<#
.SYNOPSIS
    Elin Texture Generator - Creates texture files for Elin mods
    AI-Assisted Modding Tools (AAMT) - Elin Toolset

.DESCRIPTION
    Generates texture-related files for Elin including:
    - Standard item/object textures (.png)
    - Animated textures with .ini configuration
    - Snow/weather variants
    - Numbered variants
    - Proper folder structure for Elin mods

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}

.PARAMETER TextureName
    Base name of the texture (without extension)

.PARAMETER TextureType
    Type of texture to generate

.PARAMETER Preset
    Built-in preset to use

.EXAMPLE
    .\ElinTextureGenerator.ps1 -TextureName "my_item" -TextureType Item -Preset Basic
    .\ElinTextureGenerator.ps1 -TextureName "fountain_custom" -TextureType Item -Animated -FrameCount 4
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$TextureName,

    [Parameter(Mandatory=$false)]
    [ValidateSet("Item", "Chara", "CharaSprite", "Map", "MapTile", "Effect", "UI", "Icon", "Portrait")]
    [string]$TextureType = "Item",

    [Parameter(Mandatory=$false)]
    [ValidateSet("Basic", "Furniture", "Statue", "Sign", "Wagon", "Boat", "Tree", "Fountain", "Tent", "Custom")]
    [string]$Preset = "Basic",

    [Parameter(Mandatory=$false)]
    [string]$OutputDir = "ElinTextures",

    # Texture dimensions
    [Parameter(Mandatory=$false)]
    [int]$Width = 0,  # 0 = auto from preset

    [Parameter(Mandatory=$false)]
    [int]$Height = 0,  # 0 = auto from preset

    # Animation settings
    [Parameter(Mandatory=$false)]
    [switch]$Animated,

    [Parameter(Mandatory=$false)]
    [int]$FrameCount = 4,

    [Parameter(Mandatory=$false)]
    [int]$AnimationSpeed = 100,  # milliseconds per frame

    [Parameter(Mandatory=$false)]
    [switch]$AnimationLoop,

    # Variants
    [Parameter(Mandatory=$false)]
    [switch]$GenerateSnowVariant,

    [Parameter(Mandatory=$false)]
    [int]$NumberedVariants = 1,

    # Placeholder generation
    [Parameter(Mandatory=$false)]
    [switch]$GeneratePlaceholder,

    [Parameter(Mandatory=$false)]
    [array]$BaseColor = $null,

    # Additional metadata
    [Parameter(Mandatory=$false)]
    [string]$Description = ""
)

# Import unified tool detection and integration
$sharedPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\Shared"
Import-Module (Join-Path $sharedPath "ToolDetection.psm1") -ErrorAction SilentlyContinue
Import-Module (Join-Path $sharedPath "ToolsetIntegration.psm1") -ErrorAction SilentlyContinue

# Initialize tools (optional tools for texture generation)
$tools = Initialize-ToolsetTools `
    -RequiredTools @() `
    -OptionalTools @("Python", "ImageMagick")

# Show tool status
Show-ToolsetStatus -ToolsetName "Elin" `
    -RequiredTools @() `
    -OptionalTools @("Python", "ImageMagick")
Write-Host ""

# ============================================================================
# TEXTURE TYPE CONFIGURATIONS
# ============================================================================

$TextureConfigs = @{
    "Item" = @{
        DefaultWidth = 48
        DefaultHeight = 48
        SubFolder = "Item"
        SupportsAnimation = $true
        SupportsSnow = $true
    }
    "Chara" = @{
        DefaultWidth = 32
        DefaultHeight = 48
        SubFolder = "Chara"
        SupportsAnimation = $true
        SupportsSnow = $false
    }
    "CharaSprite" = @{
        DefaultWidth = 32
        DefaultHeight = 32
        SubFolder = "CharaSprite"
        SupportsAnimation = $true
        SupportsSnow = $false
    }
    "Map" = @{
        DefaultWidth = 256
        DefaultHeight = 256
        SubFolder = "Map"
        SupportsAnimation = $false
        SupportsSnow = $true
    }
    "MapTile" = @{
        DefaultWidth = 48
        DefaultHeight = 24
        SubFolder = "MapTile"
        SupportsAnimation = $true
        SupportsSnow = $true
    }
    "Effect" = @{
        DefaultWidth = 64
        DefaultHeight = 64
        SubFolder = "Effect"
        SupportsAnimation = $true
        SupportsSnow = $false
    }
    "UI" = @{
        DefaultWidth = 32
        DefaultHeight = 32
        SubFolder = "UI"
        SupportsAnimation = $false
        SupportsSnow = $false
    }
    "Icon" = @{
        DefaultWidth = 32
        DefaultHeight = 32
        SubFolder = "Icon"
        SupportsAnimation = $false
        SupportsSnow = $false
    }
    "Portrait" = @{
        DefaultWidth = 80
        DefaultHeight = 112
        SubFolder = "Portrait"
        SupportsAnimation = $false
        SupportsSnow = $false
    }
}

# ============================================================================
# PRESET CONFIGURATIONS
# ============================================================================

$PresetConfigs = @{
    "Basic" = @{
        Width = 48
        Height = 48
        Color = @(128, 128, 128)
    }
    "Furniture" = @{
        Width = 48
        Height = 72
        Color = @(139, 90, 43)  # Wood brown
    }
    "Statue" = @{
        Width = 48
        Height = 96
        Color = @(180, 180, 180)  # Stone gray
    }
    "Sign" = @{
        Width = 48
        Height = 48
        Color = @(160, 120, 60)  # Wood
        SupportsSnow = $true
    }
    "Wagon" = @{
        Width = 96
        Height = 72
        Color = @(100, 70, 40)  # Dark wood
        SupportsSnow = $true
    }
    "Boat" = @{
        Width = 72
        Height = 48
        Color = @(80, 60, 40)  # Dark wood
        Animated = $true
        FrameCount = 4
    }
    "Tree" = @{
        Width = 48
        Height = 96
        Color = @(60, 120, 40)  # Green
    }
    "Fountain" = @{
        Width = 48
        Height = 72
        Color = @(100, 150, 200)  # Blue-gray
        Animated = $true
        FrameCount = 4
        SupportsSnow = $true
    }
    "Tent" = @{
        Width = 72
        Height = 72
        Color = @(200, 180, 140)  # Canvas
        SupportsSnow = $true
    }
    "Custom" = @{
        Width = 48
        Height = 48
        Color = @(128, 128, 128)
    }
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

function New-ElinAnimationIni {
    param(
        [string]$OutputPath,
        [int]$FrameCount,
        [int]$Speed,
        [bool]$Loop
    )
    
    $iniContent = @"
[Animation]
Frames=$FrameCount
Speed=$Speed
Loop=$($Loop.ToString().ToLower())
"@
    
    $iniContent | Out-File -FilePath $OutputPath -Encoding UTF8 -Force
    return $true
}

function New-PlaceholderTexture {
    param(
        [string]$OutputPath,
        [int]$Width,
        [int]$Height,
        [array]$BaseColor,
        [int]$FrameCount = 1,
        [bool]$IsAnimated = $false,
        [string]$Style = "item"
    )
    
    # Prefer rich procedural Python renderer (spec-driven) when available
    $scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
    $pythonScript = Join-Path $scriptDir "generate_asset_image.py"
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCmd) { $pythonCmd = Get-Command python3 -ErrorAction SilentlyContinue }

    if ((Test-Path $pythonScript) -and $pythonCmd) {
        try {
            $spec = @{
                pattern = if ($Style -eq "tree") { "organic" } elseif ($Style -eq "statue") { "geometric" } else { "noise" }
                colors = @(
                    "#{0:x2}{1:x2}{2:x2}" -f $BaseColor[0], $BaseColor[1], $BaseColor[2]
                    "#{0:x2}{1:x2}{2:x2}" -f ([Math]::Min(255, $BaseColor[0] + 40)), ([Math]::Min(255, $BaseColor[1] + 40)), ([Math]::Min(255, $BaseColor[2] + 40))
                )
                motif = $Style
                shape = $Style
                style = "stylized"
                effects = @("rim-light")
            }
            $tempSpec = Join-Path $env:TEMP "elin_tex_spec_$(Get-Random).json"
            $json = $spec | ConvertTo-Json -Depth 6
            [System.IO.File]::WriteAllText($tempSpec, $json, (New-Object System.Text.UTF8Encoding $false))

            if ($IsAnimated -and $FrameCount -gt 1) {
                Add-Type -AssemblyName System.Drawing -ErrorAction SilentlyContinue
                $totalWidth = $Width * $FrameCount
                $strip = New-Object System.Drawing.Bitmap($totalWidth, $Height)
                $g = [System.Drawing.Graphics]::FromImage($strip)
                $g.Clear([System.Drawing.Color]::FromArgb(0, 0, 0, 0))
                for ($frame = 0; $frame -lt $FrameCount; $frame++) {
                    $framePath = Join-Path $env:TEMP "elin_tex_frame_${frame}_$(Get-Random).png"
                    $frameSpec = @{} + $spec
                    $frameSpec.seed = $frame * 31
                    $json = $frameSpec | ConvertTo-Json -Depth 6
                    [System.IO.File]::WriteAllText($tempSpec, $json, (New-Object System.Text.UTF8Encoding $false))
                    & $pythonCmd.Source $pythonScript --spec $tempSpec --output $framePath --type texture --size $Width 2>$null
                    if (Test-Path $framePath) {
                        $frameBmp = [System.Drawing.Image]::FromFile($framePath)
                        $g.DrawImage($frameBmp, $frame * $Width, 0, $Width, $Height)
                        $frameBmp.Dispose()
                        Remove-Item $framePath -Force -ErrorAction SilentlyContinue
                    }
                }
                $g.Dispose()
                $strip.Save($OutputPath, [System.Drawing.Imaging.ImageFormat]::Png)
                $strip.Dispose()
            }
            else {
                & $pythonCmd.Source $pythonScript --spec $tempSpec --output $OutputPath --type texture --size $Width 2>$null
            }

            Remove-Item $tempSpec -Force -ErrorAction SilentlyContinue
            if (Test-Path $OutputPath) {
                return $true
            }
        }
        catch {
            Write-Host "[Info] Python procedural texture fallback: $_" -ForegroundColor Gray
        }
    }

    try {
        Add-Type -AssemblyName System.Drawing
        
        $totalWidth = if ($IsAnimated) { $Width * $FrameCount } else { $Width }
        
        $bitmap = New-Object System.Drawing.Bitmap($totalWidth, $Height)
        $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
        $graphics.Clear([System.Drawing.Color]::Transparent)
        
        $baseClr = [System.Drawing.Color]::FromArgb(255, $BaseColor[0], $BaseColor[1], $BaseColor[2])
        $darkClr = [System.Drawing.Color]::FromArgb(255, 
            [Math]::Max(0, $BaseColor[0] - 40),
            [Math]::Max(0, $BaseColor[1] - 40),
            [Math]::Max(0, $BaseColor[2] - 40))
        $lightClr = [System.Drawing.Color]::FromArgb(255,
            [Math]::Min(255, $BaseColor[0] + 40),
            [Math]::Min(255, $BaseColor[1] + 40),
            [Math]::Min(255, $BaseColor[2] + 40))
        
        $baseBrush = New-Object System.Drawing.SolidBrush($baseClr)
        $darkBrush = New-Object System.Drawing.SolidBrush($darkClr)
        $lightBrush = New-Object System.Drawing.SolidBrush($lightClr)
        $outlinePen = New-Object System.Drawing.Pen([System.Drawing.Color]::Black, 1)
        
        for ($frame = 0; $frame -lt $FrameCount; $frame++) {
            $xOffset = $frame * $Width
            $animOffset = if ($IsAnimated) { [int]([Math]::Sin($frame * 0.5) * 2) } else { 0 }
            
            switch ($Style) {
                "item" {
                    # Draw item shape
                    $graphics.FillRectangle($baseBrush, $xOffset + 8, 8 + $animOffset, $Width - 16, $Height - 16)
                    $graphics.FillRectangle($lightBrush, $xOffset + 8, 8 + $animOffset, $Width - 16, 4)
                    $graphics.FillRectangle($darkBrush, $xOffset + 8, $Height - 12 + $animOffset, $Width - 16, 4)
                    $graphics.DrawRectangle($outlinePen, $xOffset + 8, 8 + $animOffset, $Width - 17, $Height - 17)
                }
                "statue" {
                    # Tall statue shape
                    $centerX = $xOffset + $Width / 2
                    $graphics.FillRectangle($baseBrush, $centerX - 12, $Height - 20, 24, 20)  # Base
                    $graphics.FillRectangle($baseBrush, $centerX - 8, 20 + $animOffset, 16, $Height - 40)  # Body
                    $graphics.FillEllipse($lightBrush, $centerX - 10, 8 + $animOffset, 20, 20)  # Head
                }
                "tree" {
                    # Tree shape
                    $centerX = $xOffset + $Width / 2
                    $graphics.FillRectangle($darkBrush, $centerX - 4, $Height - 24, 8, 24)  # Trunk
                    $greenBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(255, 60, 120 + $frame * 10, 40))
                    $graphics.FillEllipse($greenBrush, $centerX - 20, 4 + $animOffset, 40, 50)  # Foliage
                    $greenBrush.Dispose()
                }
                "fountain" {
                    # Fountain with water animation
                    $centerX = $xOffset + $Width / 2
                    $graphics.FillRectangle($baseBrush, $centerX - 16, $Height - 16, 32, 16)  # Base
                    $waterBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(180, 100, 150, 255))
                    $waterHeight = 20 + $frame * 3
                    $graphics.FillEllipse($waterBrush, $centerX - 12, $Height - 20 - $waterHeight, 24, $waterHeight)
                    $waterBrush.Dispose()
                }
                default {
                    # Generic rectangle
                    $graphics.FillRectangle($baseBrush, $xOffset + 4, 4, $Width - 8, $Height - 8)
                    $graphics.DrawRectangle($outlinePen, $xOffset + 4, 4, $Width - 9, $Height - 9)
                }
            }
        }
        
        $baseBrush.Dispose()
        $darkBrush.Dispose()
        $lightBrush.Dispose()
        $outlinePen.Dispose()
        
        $bitmap.Save($OutputPath, [System.Drawing.Imaging.ImageFormat]::Png)
        $graphics.Dispose()
        $bitmap.Dispose()
        
        return $true
    }
    catch {
        Write-Host "[Warning] Could not generate placeholder: $_" -ForegroundColor Yellow
        return $false
    }
}

function New-SnowVariantTexture {
    param(
        [string]$SourcePath,
        [string]$OutputPath
    )
    
    try {
        Add-Type -AssemblyName System.Drawing
        
        if (-not (Test-Path $SourcePath)) {
            Write-Host "[Warning] Source texture not found for snow variant" -ForegroundColor Yellow
            return $false
        }
        
        $source = [System.Drawing.Image]::FromFile($SourcePath)
        $bitmap = New-Object System.Drawing.Bitmap($source.Width, $source.Height)
        $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
        
        # Copy source
        $graphics.DrawImage($source, 0, 0)
        
        # Add snow overlay (white semi-transparent spots on top portion)
        $snowBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(180, 255, 255, 255))
        $random = New-Object System.Random
        
        for ($i = 0; $i -lt 20; $i++) {
            $x = $random.Next(0, $source.Width - 4)
            $y = $random.Next(0, [int]($source.Height * 0.4))
            $size = $random.Next(2, 6)
            $graphics.FillEllipse($snowBrush, $x, $y, $size, $size)
        }
        
        $snowBrush.Dispose()
        $source.Dispose()
        
        $bitmap.Save($OutputPath, [System.Drawing.Imaging.ImageFormat]::Png)
        $graphics.Dispose()
        $bitmap.Dispose()
        
        return $true
    }
    catch {
        Write-Host "[Warning] Could not generate snow variant: $_" -ForegroundColor Yellow
        return $false
    }
}

# ============================================================================
# MAIN GENERATION LOGIC
# ============================================================================

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Elin Texture Generator" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Get configurations
$typeConfig = $TextureConfigs[$TextureType]
$presetConfig = $PresetConfigs[$Preset]

# Determine final dimensions
$finalWidth = if ($Width -gt 0) { $Width } elseif ($presetConfig.Width) { $presetConfig.Width } else { $typeConfig.DefaultWidth }
$finalHeight = if ($Height -gt 0) { $Height } elseif ($presetConfig.Height) { $presetConfig.Height } else { $typeConfig.DefaultHeight }

# Determine if animated
$isAnimated = $Animated.IsPresent -or ($presetConfig.Animated -eq $true)
$finalFrameCount = if ($isAnimated) { 
    if ($FrameCount -ne 4) { $FrameCount } 
    elseif ($presetConfig.FrameCount) { $presetConfig.FrameCount } 
    else { 4 }
} else { 1 }

# Determine color
$finalColor = if ($BaseColor) { $BaseColor } elseif ($presetConfig.Color) { $presetConfig.Color } else { @(128, 128, 128) }

# Determine if snow variant should be generated
$generateSnow = $GenerateSnowVariant.IsPresent -or ($presetConfig.SupportsSnow -and $typeConfig.SupportsSnow)

# Create output directory structure
$outputPath = $OutputDir
if (-not [System.IO.Path]::IsPathRooted($OutputDir)) {
    $outputPath = Join-Path (Get-Location) $OutputDir
}

$textureDir = Join-Path $outputPath $typeConfig.SubFolder
if (-not (Test-Path $textureDir)) {
    New-Item -ItemType Directory -Path $textureDir -Force | Out-Null
    Write-Host "[Created] Texture directory: $textureDir" -ForegroundColor Green
}

Write-Host "[Generating] $TextureType texture: $TextureName" -ForegroundColor Yellow
Write-Host "  Preset: $Preset" -ForegroundColor Gray
Write-Host "  Size: ${finalWidth}x${finalHeight}" -ForegroundColor Gray
if ($isAnimated) {
    Write-Host "  Animated: $finalFrameCount frames" -ForegroundColor Gray
}

$generatedFiles = @()

# ============================================================================
# Generate Textures
# ============================================================================

for ($variant = 1; $variant -le $NumberedVariants; $variant++) {
    $variantSuffix = if ($variant -eq 1 -and $NumberedVariants -eq 1) { "" } else { $variant.ToString() }
    $baseName = "${TextureName}${variantSuffix}"
    
    # Main texture
    $mainTexturePath = Join-Path $textureDir "$baseName.png"
    
    if ($GeneratePlaceholder) {
        $style = switch ($Preset) {
            "Statue" { "statue" }
            "Tree" { "tree" }
            "Fountain" { "fountain" }
            default { "item" }
        }
        
        $success = New-PlaceholderTexture -OutputPath $mainTexturePath `
            -Width $finalWidth -Height $finalHeight `
            -BaseColor $finalColor -FrameCount 1 -IsAnimated $false -Style $style
        
        if ($success) {
            Write-Host "[Created] $baseName.png" -ForegroundColor Green
            $generatedFiles += $mainTexturePath
        }
    }
    else {
        # Create empty placeholder info
        Write-Host "[Info] Create texture: $baseName.png (${finalWidth}x${finalHeight})" -ForegroundColor Yellow
    }
    
    # Animated version
    if ($isAnimated) {
        $animeName = "${baseName}_anime"
        $animeTexturePath = Join-Path $textureDir "$animeName.png"
        $animeIniPath = Join-Path $textureDir "$animeName.ini"
        
        if ($GeneratePlaceholder) {
            $style = switch ($Preset) {
                "Fountain" { "fountain" }
                "Boat" { "item" }
                default { "item" }
            }
            
            $success = New-PlaceholderTexture -OutputPath $animeTexturePath `
                -Width $finalWidth -Height $finalHeight `
                -BaseColor $finalColor -FrameCount $finalFrameCount -IsAnimated $true -Style $style
            
            if ($success) {
                Write-Host "[Created] $animeName.png (${finalFrameCount} frames)" -ForegroundColor Green
                $generatedFiles += $animeTexturePath
            }
        }
        
        # Always create INI file
        $loopAnim = if ($AnimationLoop.IsPresent) { $true } else { $true }  # Default to loop
        New-ElinAnimationIni -OutputPath $animeIniPath `
            -FrameCount $finalFrameCount -Speed $AnimationSpeed -Loop $loopAnim
        Write-Host "[Created] $animeName.ini" -ForegroundColor Green
        $generatedFiles += $animeIniPath
    }
    
    # Snow variant
    if ($generateSnow -and $typeConfig.SupportsSnow) {
        $snowName = "${baseName}_snow"
        $snowTexturePath = Join-Path $textureDir "$snowName.png"
        
        if ($GeneratePlaceholder -and (Test-Path $mainTexturePath)) {
            $success = New-SnowVariantTexture -SourcePath $mainTexturePath -OutputPath $snowTexturePath
            if ($success) {
                Write-Host "[Created] $snowName.png (snow variant)" -ForegroundColor Green
                $generatedFiles += $snowTexturePath
            }
        }
        else {
            Write-Host "[Info] Create snow variant: $snowName.png" -ForegroundColor Yellow
        }
    }
}

# ============================================================================
# Generate README with texture specifications
# ============================================================================

$readmeContent = @"
# Elin Texture: $TextureName

## Specifications

| Property | Value |
|----------|-------|
| Type | $TextureType |
| Preset | $Preset |
| Width | $finalWidth px |
| Height | $finalHeight px |
| Animated | $isAnimated |
$(if ($isAnimated) { "| Frames | $finalFrameCount |`n| Speed | ${AnimationSpeed}ms |" })
| Snow Variant | $generateSnow |
| Variants | $NumberedVariants |

## File Structure

"@

$readmeContent += "``````"
$readmeContent += "`n$($typeConfig.SubFolder)/"

for ($variant = 1; $variant -le $NumberedVariants; $variant++) {
    $variantSuffix = if ($variant -eq 1 -and $NumberedVariants -eq 1) { "" } else { $variant.ToString() }
    $baseName = "${TextureName}${variantSuffix}"
    
    $readmeContent += "`n├── $baseName.png"
    if ($isAnimated) {
        $readmeContent += "`n├── ${baseName}_anime.png"
        $readmeContent += "`n├── ${baseName}_anime.ini"
    }
    if ($generateSnow) {
        $readmeContent += "`n├── ${baseName}_snow.png"
    }
}

$readmeContent += "`n``````"

$readmeContent += @"


## Animation INI Format

``````ini
[Animation]
Frames=$finalFrameCount
Speed=$AnimationSpeed
Loop=true
``````

- **Frames**: Number of horizontal frames in the animation spritesheet
- **Speed**: Milliseconds per frame
- **Loop**: Whether the animation loops

## Notes

- Place textures in: ``Package/YourMod/Texture/$($typeConfig.SubFolder)/``
- Animated textures need both ``.png`` and ``.ini`` files
- Snow variants use ``_snow`` suffix
- Numbered variants use suffix numbers (item2, item3, etc.)
"@

$readmePath = Join-Path $textureDir "${TextureName}_README.md"
$readmeContent | Out-File -FilePath $readmePath -Encoding UTF8 -Force
Write-Host "[Created] ${TextureName}_README.md" -ForegroundColor Green

# ============================================================================
# Summary
# ============================================================================

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Generation Summary" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Texture Name: $TextureName" -ForegroundColor White
Write-Host "  Type: $TextureType" -ForegroundColor White
Write-Host "  Preset: $Preset" -ForegroundColor White
Write-Host "  Dimensions: ${finalWidth}x${finalHeight}" -ForegroundColor Yellow

if ($isAnimated) {
    Write-Host "  Animation: $finalFrameCount frames @ ${AnimationSpeed}ms" -ForegroundColor Yellow
}
if ($generateSnow) {
    Write-Host "  Snow Variant: Yes" -ForegroundColor Cyan
}
if ($NumberedVariants -gt 1) {
    Write-Host "  Variants: $NumberedVariants" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Output Directory: $textureDir" -ForegroundColor Cyan
Write-Host "Files Generated: $($generatedFiles.Count)" -ForegroundColor White
Write-Host ""

# Return result
return @{
    Success = $true
    TextureDirectory = $textureDir
    TextureName = $TextureName
    TextureType = $TextureType
    GeneratedFiles = $generatedFiles
    Width = $finalWidth
    Height = $finalHeight
    Animated = $isAnimated
    FrameCount = $finalFrameCount
}

