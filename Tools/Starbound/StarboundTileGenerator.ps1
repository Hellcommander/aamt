<#
.SYNOPSIS
    Starbound Tile Generator - Creates tile/material files for terrain and blocks

.DESCRIPTION
    Generates tile-related files for Starbound/OpenStarbound:
    - .frames files with frameList format (pixel coordinates)
    - .material files for tile properties
    - .matmod files for material modifiers
    - Tile PNG spritesheets painted by the local Stable Diffusion 3.5 server (:1338),
      downsized and palette-quantized to the tile cell size. SD or throw: procedural
      System.Drawing art only runs with -AllowProcedural (or AAMT_SD_STRICT=0) after SD fails.

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}

.PARAMETER TileName
    Name of the tile (used for filename)

.PARAMETER Preset
    Built-in tile preset to use

.PARAMETER OutputDir
    Output directory for generated files

.EXAMPLE
    .\StarboundTileGenerator.ps1 -TileName "mytile" -Preset Basic
    .\StarboundTileGenerator.ps1 -TileName "customblock" -Preset Protection -TileCount 5
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$TileName,

    [Parameter(Mandatory=$false)]
    [ValidateSet("Basic", "Protection", "Platform", "Ore", "Brick", "Natural", "Metal", "Glass", "Organic", "Tech", "Custom")]
    [string]$Preset = "Basic",

    [Parameter(Mandatory=$false)]
    [string]$OutputDir = "StarboundTiles",

    # Tile properties
    [Parameter(Mandatory=$false)]
    [int]$TileSize = 8,  # Size of each tile in pixels

    [Parameter(Mandatory=$false)]
    [int]$TileCount = 1,  # Number of tile variants

    [Parameter(Mandatory=$false)]
    [int]$Columns = 0,  # Columns in spritesheet (0 = auto, all in one row)

    [Parameter(Mandatory=$false)]
    [array]$FrameNames = $null,  # Custom frame names (default: numbered)

    # Material properties
    [Parameter(Mandatory=$false)]
    [switch]$GenerateMaterial,  # Generate .material file

    [Parameter(Mandatory=$false)]
    [int]$MaterialId = 0,  # Material ID (0 = auto-assign)

    [Parameter(Mandatory=$false)]
    [string]$MaterialCategory = "materials",

    [Parameter(Mandatory=$false)]
    [float]$Health = 1.0,

    [Parameter(Mandatory=$false)]
    [string]$FootstepSound = "/sfx/blocks/footstep_stone.ogg",

    [Parameter(Mandatory=$false)]
    [string]$DamageTable = "/tiles/damagetypes.config:normal",

    [Parameter(Mandatory=$false)]
    [string]$TillingEffect = "",

    [Parameter(Mandatory=$false)]
    [array]$ItemDrop = $null,  # Items dropped when mined

    # Matmod properties
    [Parameter(Mandatory=$false)]
    [switch]$GenerateMatmod,  # Generate material modifier

    [Parameter(Mandatory=$false)]
    [int]$MatmodId = 0,

    # Rendering properties
    [Parameter(Mandatory=$false)]
    [string]$RenderTemplate = "/tiles/classicmaterialtemplate.config",

    [Parameter(Mandatory=$false)]
    [hashtable]$RenderParameters = $null,

    [Parameter(Mandatory=$false)]
    [switch]$Multicolored,  # Has color variants

    [Parameter(Mandatory=$false)]
    [switch]$GeneratePlaceholderImage,  # Kept for compatibility: the PNG is always written (via Stable Diffusion)

    [Parameter(Mandatory=$false)]
    [switch]$AllowProcedural,  # Permit the old System.Drawing art, only as fallback after SD failure (or AAMT_SD_STRICT=0)

    # Ollama / art direction
    [Parameter(Mandatory=$false)]
    [string]$Description = "",

    [Parameter(Mandatory=$false)]
    [switch]$UseOllama,

    [Parameter(Mandatory=$false)]
    [string]$OllamaModel = "codellama:7b-instruct",

    [Parameter(Mandatory=$false)]
    [string]$VisualModel = "wizardlm-uncensored"
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

# Stable Diffusion art helper (SD3.5 server :1338). No procedural art unless -AllowProcedural.
Import-Module (Join-Path $PSScriptRoot "StarboundSdArt.psm1") -Force

# ============================================================================
# PRESET DEFINITIONS
# ============================================================================

$TilePresets = @{
    "Basic" = @{
        TileSize = 8
        TileCount = 1
        Health = 1.0
        FootstepSound = "/sfx/blocks/footstep_stone.ogg"
        DamageTable = "/tiles/damagetypes.config:normal"
        RenderTemplate = "/tiles/classicmaterialtemplate.config"
        Category = "materials"
    }
    "Protection" = @{
        TileSize = 8
        TileCount = 5
        Health = 10.0
        FootstepSound = "/sfx/blocks/footstep_stone.ogg"
        DamageTable = "/tiles/damagetypes.config:normal"
        RenderTemplate = "/tiles/classicmaterialtemplate.config"
        Category = "materials"
    }
    "Platform" = @{
        TileSize = 8
        TileCount = 4
        Health = 0.5
        FootstepSound = "/sfx/blocks/footstep_wood.ogg"
        DamageTable = "/tiles/damagetypes.config:platform"
        RenderTemplate = "/tiles/platformtemplate.config"
        Category = "platforms"
    }
    "Ore" = @{
        TileSize = 8
        TileCount = 1
        Health = 3.0
        FootstepSound = "/sfx/blocks/footstep_stone.ogg"
        DamageTable = "/tiles/damagetypes.config:ore"
        RenderTemplate = "/tiles/classicmaterialtemplate.config"
        Category = "ores"
        ItemDrop = @(@{ "item" = "oreitem"; "count" = 1 })
    }
    "Brick" = @{
        TileSize = 8
        TileCount = 16
        Health = 2.0
        FootstepSound = "/sfx/blocks/footstep_stone.ogg"
        DamageTable = "/tiles/damagetypes.config:normal"
        RenderTemplate = "/tiles/classicmaterialtemplate.config"
        Category = "materials"
        Multicolored = $true
    }
    "Natural" = @{
        TileSize = 8
        TileCount = 4
        Health = 0.8
        FootstepSound = "/sfx/blocks/footstep_dirt.ogg"
        DamageTable = "/tiles/damagetypes.config:normal"
        RenderTemplate = "/tiles/classicmaterialtemplate.config"
        Category = "materials"
    }
    "Metal" = @{
        TileSize = 8
        TileCount = 1
        Health = 3.0
        FootstepSound = "/sfx/blocks/footstep_metal.ogg"
        DamageTable = "/tiles/damagetypes.config:normal"
        RenderTemplate = "/tiles/classicmaterialtemplate.config"
        Category = "materials"
    }
    "Glass" = @{
        TileSize = 8
        TileCount = 1
        Health = 0.5
        FootstepSound = "/sfx/blocks/footstep_glass.ogg"
        DamageTable = "/tiles/damagetypes.config:glass"
        RenderTemplate = "/tiles/classicmaterialtemplate.config"
        Category = "materials"
    }
    "Organic" = @{
        TileSize = 8
        TileCount = 4
        Health = 0.6
        FootstepSound = "/sfx/blocks/footstep_flesh.ogg"
        DamageTable = "/tiles/damagetypes.config:organic"
        RenderTemplate = "/tiles/classicmaterialtemplate.config"
        Category = "materials"
    }
    "Tech" = @{
        TileSize = 8
        TileCount = 8
        Health = 2.5
        FootstepSound = "/sfx/blocks/footstep_metal.ogg"
        DamageTable = "/tiles/damagetypes.config:normal"
        RenderTemplate = "/tiles/classicmaterialtemplate.config"
        Category = "materials"
    }
    "Custom" = @{
        TileSize = 8
        TileCount = 1
        Health = 1.0
        FootstepSound = "/sfx/blocks/footstep_stone.ogg"
        DamageTable = "/tiles/damagetypes.config:normal"
        RenderTemplate = "/tiles/classicmaterialtemplate.config"
        Category = "materials"
    }
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

function Get-TileColorWord {
    # Coarse RGB -> colour word so Ollama palettes can steer the SD prompt.
    param([int]$R, [int]$G, [int]$B)
    $max = [Math]::Max($R, [Math]::Max($G, $B)); $min = [Math]::Min($R, [Math]::Min($G, $B))
    if ($max -lt 50) { return "black" }
    if (($max - $min) -lt 28) { if ($max -gt 205) { return "white" } elseif ($max -gt 120) { return "grey" } else { return "dark grey" } }
    $d = [double]($max - $min)
    $h = if ($max -eq $R) { 60.0 * ((($G - $B) / $d) % 6) } elseif ($max -eq $G) { 60.0 * ((($B - $R) / $d) + 2) } else { 60.0 * ((($R - $G) / $d) + 4) }
    if ($h -lt 0) { $h += 360 }
    $tone = if ($max -lt 110) { "dark " } elseif ($max -gt 215 -and ($max - $min) -lt 120) { "pale " } else { "" }
    $name = if ($h -lt 15 -or $h -ge 345) { "red" } elseif ($h -lt 40) { "orange" } elseif ($h -lt 70) { "yellow" } elseif ($h -lt 160) { "green" } elseif ($h -lt 200) { "teal" } elseif ($h -lt 255) { "blue" } elseif ($h -lt 300) { "purple" } else { "magenta" }
    return "$tone$name"
}

function Get-StableSeed {
    param([string]$Text)
    $h = 17
    foreach ($ch in $Text.ToCharArray()) { $h = (($h * 31) + [int]$ch) % 900000 }
    return [int]($h + 1)
}

function New-ProceduralTileFallbackImage {
    # LEGACY FALLBACK ONLY: coloured rectangles/checkerboards. Runs solely when
    # -AllowProcedural (or AAMT_SD_STRICT=0) is set and Stable Diffusion failed.
    param(
        [string]$OutputPath,
        [int]$TileSize,
        [int]$TileCount,
        [int]$Columns,
        [string]$Style = "checker"
    )
    
    try {
        Add-Type -AssemblyName System.Drawing
        
        $cols = if ($Columns -gt 0) { $Columns } else { $TileCount }
        $rows = [Math]::Ceiling($TileCount / $cols)
        
        $width = $TileSize * $cols
        $height = $TileSize * $rows
        
        $bitmap = New-Object System.Drawing.Bitmap($width, $height)
        $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
        $graphics.Clear([System.Drawing.Color]::Transparent)
        
        for ($i = 0; $i -lt $TileCount; $i++) {
            $col = $i % $cols
            $row = [Math]::Floor($i / $cols)
            $x = $col * $TileSize
            $y = $row * $TileSize
            
            # Generate different colors for each tile
            $hue = ($i * 30) % 360
            $baseColor = [System.Drawing.Color]::FromArgb(
                200,
                [int](128 + 64 * [Math]::Sin($hue * [Math]::PI / 180)),
                [int](128 + 64 * [Math]::Sin(($hue + 120) * [Math]::PI / 180)),
                [int](128 + 64 * [Math]::Sin(($hue + 240) * [Math]::PI / 180))
            )
            
            $darkColor = [System.Drawing.Color]::FromArgb(
                200,
                [int]($baseColor.R * 0.7),
                [int]($baseColor.G * 0.7),
                [int]($baseColor.B * 0.7)
            )
            
            $brush1 = New-Object System.Drawing.SolidBrush($baseColor)
            $brush2 = New-Object System.Drawing.SolidBrush($darkColor)
            
            switch ($Style) {
                "checker" {
                    # Checkerboard pattern
                    $halfSize = [int]($TileSize / 2)
                    for ($py = 0; $py -lt 2; $py++) {
                        for ($px = 0; $px -lt 2; $px++) {
                            $brush = if (($px + $py) % 2 -eq 0) { $brush1 } else { $brush2 }
                            $graphics.FillRectangle($brush, $x + $px * $halfSize, $y + $py * $halfSize, $halfSize, $halfSize)
                        }
                    }
                }
                "solid" {
                    $graphics.FillRectangle($brush1, $x, $y, $TileSize, $TileSize)
                }
                "border" {
                    $graphics.FillRectangle($brush1, $x, $y, $TileSize, $TileSize)
                    $pen = New-Object System.Drawing.Pen($darkColor, 1)
                    $graphics.DrawRectangle($pen, $x, $y, $TileSize - 1, $TileSize - 1)
                    $pen.Dispose()
                }
                default {
                    $graphics.FillRectangle($brush1, $x, $y, $TileSize, $TileSize)
                }
            }
            
            $brush1.Dispose()
            $brush2.Dispose()
        }
        
        $bitmap.Save($OutputPath, [System.Drawing.Imaging.ImageFormat]::Png)
        $graphics.Dispose()
        $bitmap.Dispose()
        
        return $true
    }
    catch {
        Write-Host "[Warning] Could not generate placeholder image: $_" -ForegroundColor Yellow
        return $false
    }
}

# ============================================================================
# MAIN GENERATION LOGIC
# ============================================================================

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Starbound Tile Generator" -ForegroundColor Cyan
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
$presetConfig = $TilePresets[$Preset]

# Override with custom parameters
$finalTileSize = if ($TileSize -ne 8) { $TileSize } else { $presetConfig.TileSize }
$finalTileCount = if ($TileCount -ne 1) { $TileCount } else { $presetConfig.TileCount }
$finalHealth = if ($Health -ne 1.0) { $Health } else { $presetConfig.Health }
$finalFootstep = if ($FootstepSound -ne "/sfx/blocks/footstep_stone.ogg") { $FootstepSound } else { $presetConfig.FootstepSound }
$finalDamageTable = if ($DamageTable -ne "/tiles/damagetypes.config:normal") { $DamageTable } else { $presetConfig.DamageTable }
$finalRenderTemplate = if ($RenderTemplate -ne "/tiles/classicmaterialtemplate.config") { $RenderTemplate } else { $presetConfig.RenderTemplate }
$finalCategory = if ($MaterialCategory -ne "materials") { $MaterialCategory } else { $presetConfig.Category }
$finalColumns = if ($Columns -gt 0) { $Columns } else { $finalTileCount }
$finalItemDrop = if ($ItemDrop) { $ItemDrop } elseif ($presetConfig.ItemDrop) { $presetConfig.ItemDrop } else { $null }

Write-Host "[Generating] Tile: $TileName (Preset: $Preset)" -ForegroundColor Yellow
Write-Host "  Tile Size: ${finalTileSize}x${finalTileSize}" -ForegroundColor Gray
Write-Host "  Tile Count: $finalTileCount" -ForegroundColor Gray

# ============================================================================
# Generate .frames file (frameList format)
# ============================================================================

$frameListEntries = @()
for ($i = 0; $i -lt $finalTileCount; $i++) {
    $col = $i % $finalColumns
    $row = [Math]::Floor($i / $finalColumns)
    
    $x1 = $col * $finalTileSize
    $y1 = $row * $finalTileSize
    $x2 = $x1 + $finalTileSize
    $y2 = $y1 + $finalTileSize
    
    $frameName = if ($FrameNames -and $i -lt $FrameNames.Count) {
        $FrameNames[$i]
    } else {
        ($i + 1).ToString()
    }
    
    $frameListEntries += "    `"$frameName`" : [$x1, $y1, $x2, $y2]"
}

$framesJson = @"
{
  "frameList" : {
$($frameListEntries -join ",`n")
  }
}
"@

$framesFile = Join-Path $outputPath "$TileName.frames"
$framesJson | Out-File -FilePath $framesFile -Encoding UTF8 -Force

Write-Host ""
Write-Host "[Created] $framesFile" -ForegroundColor Green

# ============================================================================
# Generate .material file (optional)
# ============================================================================

if ($GenerateMaterial) {
    $materialData = [ordered]@{
        "materialId" = if ($MaterialId -gt 0) { $MaterialId } else { (Get-Random -Minimum 10000 -Maximum 65000) }
        "materialName" = $TileName
        "particleColor" = @(100, 100, 100, 255)
        "itemDrop" = if ($finalItemDrop) { $finalItemDrop[0].item } else { $TileName }
        "description" = "A $TileName tile."
        "shortdescription" = $TileName
        "footstepSound" = $finalFootstep
        "health" = $finalHealth
        "category" = $finalCategory
        "renderTemplate" = $finalRenderTemplate
        "renderParameters" = [ordered]@{
            "texture" = "/tiles/$TileName.png"
            "variants" = $finalTileCount
            "multiColored" = $Multicolored.IsPresent
        }
        "damageTable" = $finalDamageTable
    }
    
    if ($RenderParameters) {
        foreach ($key in $RenderParameters.Keys) {
            $materialData.renderParameters[$key] = $RenderParameters[$key]
        }
    }
    
    $materialJson = $materialData | ConvertTo-Json -Depth 10
    $materialFile = Join-Path $outputPath "$TileName.material"
    $materialJson | Out-File -FilePath $materialFile -Encoding UTF8 -Force
    
    Write-Host "[Created] $materialFile" -ForegroundColor Green
}

# ============================================================================
# Generate .matmod file (optional)
# ============================================================================

if ($GenerateMatmod) {
    $matmodData = [ordered]@{
        "modId" = if ($MatmodId -gt 0) { $MatmodId } else { (Get-Random -Minimum 1000 -Maximum 9000) }
        "modName" = "${TileName}mod"
        "description" = "A $TileName modification."
        "itemDrop" = "${TileName}mod"
        "health" = $finalHealth
        "harvestLevel" = 1
        "breaksWithTile" = $true
        "renderTemplate" = "/tiles/classicmaterialtemplate.config"
        "renderParameters" = [ordered]@{
            "texture" = "/tiles/mods/${TileName}mod.png"
            "variants" = $finalTileCount
        }
    }
    
    $matmodJson = $matmodData | ConvertTo-Json -Depth 10
    $matmodFile = Join-Path $outputPath "${TileName}.matmod"
    $matmodJson | Out-File -FilePath $matmodFile -Encoding UTF8 -Force
    
    Write-Host "[Created] $matmodFile" -ForegroundColor Green
}

# ============================================================================
# Use Ollama for intelligent tile design if requested
# ============================================================================

$script:tileDesign = $null
if ($UseOllama -and (-not [string]::IsNullOrEmpty($Description))) {
    Write-Host "Using Ollama for intelligent tile design..." -ForegroundColor Cyan
    
    if (Get-Command Invoke-OllamaRequest -ErrorAction SilentlyContinue) {
        $tilePrompt = "You are designing a tile texture for a Starbound game mod named '$TileName'.
Description: $Description
Tile Size: ${finalTileSize}x${finalTileSize} pixels
Variants: $finalTileCount

Generate a visual design specification in JSON:
{
  'ColorPalette': [[R,G,B], [R,G,B], [R,G,B]] - 3 colors for the tile,
  'PatternStyle': string - pattern type (checker, solid, border, texture, etc.),
  'VisualDescription': string - how the tile should look
}

Return ONLY the JSON object."
        
        $modelToUse = if ($VisualModel) { $VisualModel } else { $OllamaModel }
        $tileResponse = Invoke-OllamaRequest -Prompt $tilePrompt -TaskType "visual" -ResponseLength "short" -ModelName $modelToUse
        
        if ($tileResponse) {
            $jsonMatch = $tileResponse | Select-String -Pattern '\{[\s\S]*\}' | Select-Object -First 1
            if ($jsonMatch) {
                try {
                    $script:tileDesign = $jsonMatch.Matches[0].Value | ConvertFrom-Json
                    Write-Host "AI tile design: $($script:tileDesign.VisualDescription)" -ForegroundColor Green
                } catch {
                    Write-Host "Could not parse AI tile design: $_" -ForegroundColor Yellow
                }
            }
        }
    }
}

# ============================================================================
# Generate the tile spritesheet PNG with Stable Diffusion (SD3.5 :1338)
# ============================================================================

# Always write a real tile PNG. Pixels come from SD; Ollama refines the prompt above.
if ($true) {
    $pngFile = Join-Path $outputPath "$TileName.png"

    # Per-preset subject + per-cell variant wording (cycled across the sheet).
    $presetArt = switch ($Preset) {
        "Basic"      { @{ Subject = "plain solid stone block";                           Variants = @() } }
        "Protection" { @{ Subject = "reinforced protective barrier block, riveted armour plating"; Variants = @("intact and pristine", "light scratches", "cracked", "heavily damaged", "glowing energy fractures") } }
        "Platform"   { @{ Subject = "thin horizontal metal walkway platform, one strip across the middle of the frame"; Variants = @("left end cap", "middle section", "right end cap", "single isolated piece") } }
        "Ore"        { @{ Subject = "rough rock with embedded glowing ore crystal veins"; Variants = @() } }
        "Brick"      { @{ Subject = "masonry brick wall";                                Variants = @("plain bricks", "cracked bricks", "mossy bricks", "darker worn bricks", "lighter clean bricks", "chipped bricks") } }
        "Natural"    { @{ Subject = "natural soil and earth ground with pebbles and tufts of grass"; Variants = @("grassy", "rocky", "dense packed soil", "tangled roots") } }
        "Metal"      { @{ Subject = "scratched steel metal plate with rivets and panel seams"; Variants = @() } }
        "Glass"      { @{ Subject = "clear glass pane with bright light reflections, pale blue tint"; Variants = @() } }
        "Organic"    { @{ Subject = "alien organic flesh tissue with veins and slime";   Variants = @("pulsing veins", "slimy surface", "fibrous muscle", "spore pods") } }
        "Tech"       { @{ Subject = "futuristic sci-fi tech wall panel";                 Variants = @("glowing circuit lines", "vent grille", "glowing energy core", "hazard stripes", "screen panel", "wiring conduit", "plain armoured plate", "blinking status lights") } }
        default      { @{ Subject = "game block material";                               Variants = @() } }
    }

    $readableName = ($TileName -creplace '([a-z])([A-Z])', '$1 $2') -replace '[_\-]+', ' '
    $parts = New-Object System.Collections.Generic.List[string]
    $parts.Add("$readableName tile, $($presetArt.Subject)")
    if (-not [string]::IsNullOrWhiteSpace($Description)) { $parts.Add($Description.Trim()) }
    if ($script:tileDesign) {
        if ($script:tileDesign.VisualDescription) { $parts.Add([string]$script:tileDesign.VisualDescription) }
        if ($script:tileDesign.PatternStyle)      { $parts.Add("$($script:tileDesign.PatternStyle) pattern") }
        if ($script:tileDesign.ColorPalette) {
            $words = @()
            foreach ($rgb in @($script:tileDesign.ColorPalette)) {
                try { if (@($rgb).Count -ge 3) { $words += (Get-TileColorWord -R ([int]$rgb[0]) -G ([int]$rgb[1]) -B ([int]$rgb[2])) } } catch { }
            }
            $words = $words | Select-Object -Unique
            if ($words) { $parts.Add("color palette: " + ($words -join ", ")) }
        }
    }
    if ($Multicolored) { $parts.Add("neutral colouring that takes tinting well") }
    $parts.Add("flat front-on view of a 2D platformer terrain material texture, seamless tileable, fills the entire frame edge to edge, Starbound sci-fantasy pixel art")
    $tilePromptText = $parts -join ", "

    $cellVariants = @()
    if ($FrameNames -and $FrameNames.Count -gt 0 -and $finalTileCount -gt 1) {
        $cellVariants = @($FrameNames | ForEach-Object { "variant: $_" })
    } elseif ($finalTileCount -gt 1) {
        $cellVariants = @($presetArt.Variants)
    }

    $sdArgs = @{
        Kind      = "sheet"
        Prompt    = $tilePromptText
        OutputPath = $pngFile
        Width     = [int]$finalTileSize
        Height    = [int]$finalTileSize
        Count     = [int]$finalTileCount
        Columns   = [int]$finalColumns
        SdKind    = "texture"
        Pixel     = $true
        Colors    = 16
        Seed      = (Get-StableSeed -Text "$TileName|$Preset")
        AllowProcedural = $AllowProcedural
    }
    if ($cellVariants.Count -gt 0) { $sdArgs.Variants = [string[]]$cellVariants }

    Write-Host "[SD] Painting $finalTileCount tile cell(s) at ${finalTileSize}x${finalTileSize} with Stable Diffusion..." -ForegroundColor Yellow
    # Throws when SD fails and procedural art is not allowed; returns $false only when it is allowed.
    $success = New-StarboundSdArt @sdArgs

    if (-not $success) {
        Write-Host "[Fallback] Drawing procedural tile art (explicitly allowed)" -ForegroundColor Yellow
        $style = if ($script:tileDesign -and $script:tileDesign.PatternStyle) {
            ([string]$script:tileDesign.PatternStyle).ToLower()
        } else {
            switch ($Preset) {
                "Brick" { "checker" }
                "Glass" { "solid" }
                default { "border" }
            }
        }
        $success = New-ProceduralTileFallbackImage -OutputPath $pngFile `
            -TileSize $finalTileSize -TileCount $finalTileCount `
            -Columns $finalColumns -Style $style
        $tileArtSource = "procedural fallback"
    } else {
        $tileArtSource = "Stable Diffusion"
    }

    if ($success) {
        Write-Host "[Created] $pngFile ($tileArtSource)" -ForegroundColor Green
        if ($script:tileDesign) {
            Write-Host "  AI-designed tile prompt" -ForegroundColor Gray
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
Write-Host "  Tile Name: $TileName" -ForegroundColor White
Write-Host "  Preset: $Preset" -ForegroundColor White
Write-Host "  Tile Size: ${finalTileSize}x${finalTileSize}px" -ForegroundColor White
Write-Host "  Variants: $finalTileCount" -ForegroundColor White

if ($GenerateMaterial) {
    Write-Host "  Category: $finalCategory" -ForegroundColor Yellow
    Write-Host "  Health: $finalHealth" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Generated Files:" -ForegroundColor Cyan
Write-Host "  - $TileName.frames" -ForegroundColor White
if ($GenerateMaterial) {
    Write-Host "  - $TileName.material" -ForegroundColor White
}
if ($GenerateMatmod) {
    Write-Host "  - $TileName.matmod" -ForegroundColor White
}
if (Test-Path (Join-Path $outputPath "$TileName.png")) {
    $pngLabel = if ($tileArtSource) { $tileArtSource } else { "existing file" }
    Write-Host "  - $TileName.png ($pngLabel)" -ForegroundColor White
}

Write-Host ""
Write-Host "Frame List Format:" -ForegroundColor Cyan
Write-Host "  Each frame: [x1, y1, x2, y2] (pixel coordinates)" -ForegroundColor Gray
Write-Host ""

# Return result object
return @{
    Success = $true
    FramesFile = $framesFile
    MaterialFile = if ($GenerateMaterial) { $materialFile } else { $null }
    MatmodFile = if ($GenerateMatmod) { $matmodFile } else { $null }
    TileName = $TileName
    Preset = $Preset
    TileCount = $finalTileCount
}

