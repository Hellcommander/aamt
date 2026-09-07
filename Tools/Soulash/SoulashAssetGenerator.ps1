<#
.SYNOPSIS
    Soulash Asset Generator - Creates asset definition files for Soulash mods
    AI-Assisted Modding Tools (AAMT) - Soulash Toolset

.DESCRIPTION
    Generates asset files for Soulash including:
    - Creature spritesheets (modular body parts)
    - Portraits (character/creature faces)
    - Item icons (equipment, consumables)
    - Ability icons (skills, spells)
    - Tileset pieces (buildings, terrain)
    - Animation frames

.PARAMETER AssetName
    Name of the asset

.PARAMETER AssetType
    Type of asset to generate

.PARAMETER Preset
    Built-in preset to use

.EXAMPLE
    .\SoulashAssetGenerator.ps1 -AssetName "demon" -AssetType Creature -Preset Demon
    .\SoulashAssetGenerator.ps1 -AssetName "health_potion" -AssetType Item -Preset Potion
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$AssetName,

    [Parameter(Mandatory=$false)]
    [ValidateSet("Creature", "Portrait", "Item", "Ability", "Tile", "Building", "Effect", "UI", "Spritesheet")]
    [string]$AssetType = "Creature",

    [Parameter(Mandatory=$false)]
    [ValidateSet("Default", "Demon", "Undead", "Beast", "Humanoid", "Elemental", "Construct", 
                 "Weapon", "Armor", "Potion", "Book", "Gem", "Food", "Tool",
                 "Attack", "Magic", "Buff", "Debuff", "Passive",
                 "Ground", "Wall", "Door", "Container", "Decoration")]
    [string]$Preset = "Default",

    [Parameter(Mandatory=$false)]
    [string]$OutputDir = "SoulashAssets",

    [Parameter(Mandatory=$false)]
    [string]$Description = "",

    # Sprite dimensions
    [Parameter(Mandatory=$false)]
    [int]$SpriteWidth = 32,

    [Parameter(Mandatory=$false)]
    [int]$SpriteHeight = 32,

    # Portrait dimensions
    [Parameter(Mandatory=$false)]
    [int]$PortraitSize = 64,

    # Creature body parts
    [Parameter(Mandatory=$false)]
    [switch]$HasTail,

    [Parameter(Mandatory=$false)]
    [switch]$HasWings,

    [Parameter(Mandatory=$false)]
    [switch]$HasHorns,

    [Parameter(Mandatory=$false)]
    [int]$ColorVariants = 1,

    # Animation frames
    [Parameter(Mandatory=$false)]
    [int]$AnimationFrames = 4,

    # Directions (for creatures)
    [Parameter(Mandatory=$false)]
    [int]$Directions = 4,

    # Item properties
    [Parameter(Mandatory=$false)]
    [string]$ItemCategory = "",

    [Parameter(Mandatory=$false)]
    [string]$ItemSlot = "",

    # Stats for creatures/items
    [Parameter(Mandatory=$false)]
    [hashtable]$Stats = $null,

    # Generate art PNG (default on). Pass -SkipArt for defs-only.
    [Parameter(Mandatory=$false)]
    [switch]$GeneratePlaceholder,

    [Parameter(Mandatory=$false)]
    [switch]$SkipArt
)

# Load shared asset generation settings from Tools root
$settingsPath = Join-Path (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)) "AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}

# ============================================================================
# ASSET TYPE CONFIGURATIONS
# ============================================================================

$AssetConfigs = @{
    "Creature" = @{
        DefaultWidth = 32
        DefaultHeight = 32
        Directions = 4
        AnimFrames = 4
        HasPortrait = $true
        BodyParts = @("base", "head", "body", "arms", "legs")
        OptionalParts = @("tail", "wings", "horns", "eyes")
    }
    "Portrait" = @{
        DefaultWidth = 64
        DefaultHeight = 64
        Directions = 1
        AnimFrames = 1
    }
    "Item" = @{
        DefaultWidth = 32
        DefaultHeight = 32
        Directions = 1
        AnimFrames = 1
        Categories = @("weapon", "armor", "consumable", "material", "quest", "misc")
    }
    "Ability" = @{
        DefaultWidth = 32
        DefaultHeight = 32
        Directions = 1
        AnimFrames = 1
    }
    "Tile" = @{
        DefaultWidth = 32
        DefaultHeight = 32
        Directions = 1
        AnimFrames = 1
        Variants = 4
    }
    "Building" = @{
        DefaultWidth = 64
        DefaultHeight = 64
        Directions = 1
        AnimFrames = 1
    }
    "Effect" = @{
        DefaultWidth = 32
        DefaultHeight = 32
        Directions = 1
        AnimFrames = 8
    }
    "UI" = @{
        DefaultWidth = 16
        DefaultHeight = 16
        Directions = 1
        AnimFrames = 1
    }
    "Spritesheet" = @{
        DefaultWidth = 256
        DefaultHeight = 256
        Directions = 4
        AnimFrames = 4
    }
}

# ============================================================================
# PRESET CONFIGURATIONS
# ============================================================================

$PresetConfigs = @{
    # Creature presets
    "Demon" = @{
        Type = "Creature"
        HasHorns = $true
        HasTail = $true
        HasWings = $false
        ColorVariants = 2
        BaseColor = @(200, 50, 50)
        Stats = @{
            HP = 100
            Strength = 15
            Agility = 10
            Intelligence = 12
        }
    }
    "Undead" = @{
        Type = "Creature"
        HasHorns = $false
        HasTail = $false
        HasWings = $false
        ColorVariants = 1
        BaseColor = @(100, 100, 80)
        Stats = @{
            HP = 80
            Strength = 12
            Agility = 6
            Intelligence = 5
        }
    }
    "Beast" = @{
        Type = "Creature"
        HasHorns = $false
        HasTail = $true
        HasWings = $false
        ColorVariants = 3
        BaseColor = @(139, 90, 43)
        Stats = @{
            HP = 60
            Strength = 14
            Agility = 16
            Intelligence = 3
        }
    }
    "Humanoid" = @{
        Type = "Creature"
        HasHorns = $false
        HasTail = $false
        HasWings = $false
        ColorVariants = 4
        BaseColor = @(200, 160, 130)
        Stats = @{
            HP = 50
            Strength = 10
            Agility = 10
            Intelligence = 10
        }
    }
    "Elemental" = @{
        Type = "Creature"
        HasHorns = $false
        HasTail = $false
        HasWings = $true
        ColorVariants = 4
        BaseColor = @(100, 150, 255)
        Stats = @{
            HP = 70
            Strength = 8
            Agility = 12
            Intelligence = 18
        }
    }
    
    # Item presets
    "Weapon" = @{
        Type = "Item"
        Category = "weapon"
        Slots = @("main_hand", "off_hand")
        IconSize = 32
    }
    "Armor" = @{
        Type = "Item"
        Category = "armor"
        Slots = @("head", "chest", "legs", "feet", "hands")
        IconSize = 32
    }
    "Potion" = @{
        Type = "Item"
        Category = "consumable"
        Stackable = $true
        MaxStack = 10
        IconSize = 32
    }
    "Book" = @{
        Type = "Item"
        Category = "misc"
        Stackable = $false
        IconSize = 32
    }
    "Gem" = @{
        Type = "Item"
        Category = "material"
        Stackable = $true
        MaxStack = 99
        IconSize = 32
    }
    
    # Ability presets
    "Attack" = @{
        Type = "Ability"
        Category = "active"
        TargetType = "enemy"
        Range = 1
        IconSize = 32
    }
    "Magic" = @{
        Type = "Ability"
        Category = "spell"
        TargetType = "any"
        Range = 5
        ManaCost = 10
        IconSize = 32
    }
    "Buff" = @{
        Type = "Ability"
        Category = "support"
        TargetType = "self"
        Duration = 10
        IconSize = 32
    }
    
    # Tile presets
    "Ground" = @{
        Type = "Tile"
        Walkable = $true
        Variants = 4
        TileSize = 32
    }
    "Wall" = @{
        Type = "Tile"
        Walkable = $false
        BlocksVision = $true
        Variants = 4
        TileSize = 32
    }
    "Door" = @{
        Type = "Tile"
        Walkable = $true
        Interactable = $true
        States = @("open", "closed", "locked")
        TileSize = 32
    }
    
    # Default
    "Default" = @{
        Type = "Generic"
        ColorVariants = 1
        BaseColor = @(128, 128, 128)
    }
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

function New-PlaceholderAssetImage {
    param(
        [string]$OutputPath,
        [int]$Width,
        [int]$Height,
        [string]$Type,
        [array]$BaseColor = @(128, 128, 128),
        [int]$Variants = 1,
        [int]$Frames = 1
    )
    
    try {
        Add-Type -AssemblyName System.Drawing
        
        $totalWidth = $Width * $Frames * $Variants
        $totalHeight = $Height
        
        $bitmap = New-Object System.Drawing.Bitmap($totalWidth, $totalHeight)
        $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
        $graphics.Clear([System.Drawing.Color]::Transparent)
        
        for ($v = 0; $v -lt $Variants; $v++) {
            # Shift hue for each variant
            $hueShift = $v * 60
            $varColor = [System.Drawing.Color]::FromArgb(
                255,
                [Math]::Min(255, [Math]::Max(0, $BaseColor[0] + $hueShift * 0.5)),
                [Math]::Min(255, [Math]::Max(0, $BaseColor[1] - $hueShift * 0.3)),
                [Math]::Min(255, [Math]::Max(0, $BaseColor[2] + $hueShift * 0.2))
            )
            
            for ($f = 0; $f -lt $Frames; $f++) {
                $x = ($v * $Frames + $f) * $Width
                $y = 0
                
                $brush = New-Object System.Drawing.SolidBrush($varColor)
                $pen = New-Object System.Drawing.Pen([System.Drawing.Color]::Black, 1)
                
                switch ($Type) {
                    "Creature" {
                        # Draw simple creature shape
                        $centerX = $x + $Width / 2
                        $centerY = $y + $Height / 2
                        # Body
                        $graphics.FillEllipse($brush, $x + 8, $y + 12, $Width - 16, $Height - 16)
                        # Head
                        $headBrush = New-Object System.Drawing.SolidBrush(
                            [System.Drawing.Color]::FromArgb(255, 
                                [Math]::Min(255, $varColor.R + 30),
                                [Math]::Min(255, $varColor.G + 30),
                                [Math]::Min(255, $varColor.B + 30))
                        )
                        $graphics.FillEllipse($headBrush, $x + 10, $y + 4, $Width - 20, 14)
                        $headBrush.Dispose()
                    }
                    "Portrait" {
                        # Draw portrait frame
                        $graphics.FillRectangle($brush, $x + 2, $y + 2, $Width - 4, $Height - 4)
                        $graphics.DrawRectangle($pen, $x + 2, $y + 2, $Width - 5, $Height - 5)
                        # Eyes
                        $eyeBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::Yellow)
                        $graphics.FillEllipse($eyeBrush, $x + $Width/3 - 3, $y + $Height/3, 6, 6)
                        $graphics.FillEllipse($eyeBrush, $x + 2*$Width/3 - 3, $y + $Height/3, 6, 6)
                        $eyeBrush.Dispose()
                    }
                    "Item" {
                        # Draw item shape
                        $graphics.FillRectangle($brush, $x + 6, $y + 4, $Width - 12, $Height - 8)
                        $graphics.DrawRectangle($pen, $x + 6, $y + 4, $Width - 13, $Height - 9)
                    }
                    "Ability" {
                        # Draw ability icon (circular)
                        $graphics.FillEllipse($brush, $x + 4, $y + 4, $Width - 8, $Height - 8)
                        $graphics.DrawEllipse($pen, $x + 4, $y + 4, $Width - 9, $Height - 9)
                    }
                    "Tile" {
                        # Draw tile with border
                        $graphics.FillRectangle($brush, $x, $y, $Width, $Height)
                        $graphics.DrawRectangle($pen, $x, $y, $Width - 1, $Height - 1)
                    }
                    default {
                        # Generic square
                        $graphics.FillRectangle($brush, $x + 2, $y + 2, $Width - 4, $Height - 4)
                    }
                }
                
                $brush.Dispose()
                $pen.Dispose()
            }
        }
        
        $bitmap.Save($OutputPath, [System.Drawing.Imaging.ImageFormat]::Png)
        $graphics.Dispose()
        $bitmap.Dispose()
        
        return $true
    }
    catch {
        Write-Host "[Warning] Could not generate procedural image: $_" -ForegroundColor Yellow
        return $false
    }
}

# ============================================================================
# MAIN GENERATION LOGIC
# ============================================================================

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Soulash Asset Generator" -ForegroundColor Cyan
Write-Host "  AI-Assisted Modding Tools (AAMT)" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Create output directory
$outputPath = $OutputDir
if (-not [System.IO.Path]::IsPathRooted($OutputDir)) {
    $outputPath = Join-Path (Get-Location) $OutputDir
}

$assetDir = Join-Path $outputPath $AssetType.ToLower()
if (-not (Test-Path $assetDir)) {
    New-Item -ItemType Directory -Path $assetDir -Force | Out-Null
    Write-Host "[Created] Asset directory: $assetDir" -ForegroundColor Green
}

# Get configurations
$assetConfig = $AssetConfigs[$AssetType]
$presetConfig = $PresetConfigs[$Preset]

# Apply defaults
$finalWidth = if ($SpriteWidth -ne 32) { $SpriteWidth } else { $assetConfig.DefaultWidth }
$finalHeight = if ($SpriteHeight -ne 32) { $SpriteHeight } else { $assetConfig.DefaultHeight }
$finalFrames = if ($AnimationFrames -ne 4) { $AnimationFrames } else { $assetConfig.AnimFrames }
$finalDirections = if ($Directions -ne 4) { $Directions } else { $assetConfig.Directions }
$finalVariants = if ($ColorVariants -ne 1) { $ColorVariants } elseif ($presetConfig.ColorVariants) { $presetConfig.ColorVariants } else { 1 }
$baseColor = if ($presetConfig.BaseColor) { $presetConfig.BaseColor } else { @(128, 128, 128) }

# Check for body parts from preset
$hasHornsFlag = $HasHorns.IsPresent -or ($presetConfig.HasHorns -eq $true)
$hasTailFlag = $HasTail.IsPresent -or ($presetConfig.HasTail -eq $true)
$hasWingsFlag = $HasWings.IsPresent -or ($presetConfig.HasWings -eq $true)

Write-Host "[Generating] $AssetType`: $AssetName" -ForegroundColor Yellow
Write-Host "  Preset: $Preset" -ForegroundColor Gray
Write-Host "  Size: ${finalWidth}x${finalHeight}" -ForegroundColor Gray

# ============================================================================
# Generate Asset Definition (JSON)
# ============================================================================

$assetDefinition = [ordered]@{
    "id" = $AssetName
    "name" = (Get-Culture).TextInfo.ToTitleCase(($AssetName -replace "_", " ").ToLower())
    "type" = $AssetType.ToLower()
    "description" = if ($Description) { $Description } else { "A $Preset $($AssetType.ToLower())." }
}

switch ($AssetType) {
    "Creature" {
        $assetDefinition["sprite"] = [ordered]@{
            "path" = "sprites/$AssetName.png"
            "width" = $finalWidth
            "height" = $finalHeight
            "frames" = $finalFrames
            "directions" = $finalDirections
            "variants" = $finalVariants
        }
        
        $assetDefinition["portrait"] = [ordered]@{
            "path" = "portraits/$AssetName.png"
            "width" = $PortraitSize
            "height" = $PortraitSize
        }
        
        $assetDefinition["body_parts"] = [ordered]@{
            "base" = $true
            "head" = $true
            "body" = $true
            "horns" = $hasHornsFlag
            "tail" = $hasTailFlag
            "wings" = $hasWingsFlag
        }
        
        $assetDefinition["stats"] = if ($Stats) { $Stats } elseif ($presetConfig.Stats) { $presetConfig.Stats } else {
            [ordered]@{
                "HP" = 50
                "Strength" = 10
                "Agility" = 10
                "Intelligence" = 10
            }
        }
        
        $assetDefinition["category"] = $Preset.ToLower()
    }
    
    "Portrait" {
        $assetDefinition["sprite"] = [ordered]@{
            "path" = "portraits/$AssetName.png"
            "width" = $PortraitSize
            "height" = $PortraitSize
        }
        $assetDefinition["variants"] = $finalVariants
    }
    
    "Item" {
        $assetDefinition["icon"] = [ordered]@{
            "path" = "items/$AssetName.png"
            "width" = $finalWidth
            "height" = $finalHeight
        }
        
        $category = if ($ItemCategory) { $ItemCategory } elseif ($presetConfig.Category) { $presetConfig.Category } else { "misc" }
        $assetDefinition["category"] = $category
        
        if ($ItemSlot -or $presetConfig.Slots) {
            $assetDefinition["slot"] = if ($ItemSlot) { $ItemSlot } else { $presetConfig.Slots[0] }
        }
        
        if ($presetConfig.Stackable) {
            $assetDefinition["stackable"] = $true
            $assetDefinition["max_stack"] = $presetConfig.MaxStack
        }
        
        if ($Stats) {
            $assetDefinition["stats"] = $Stats
        }
    }
    
    "Ability" {
        $assetDefinition["icon"] = [ordered]@{
            "path" = "abilities/$AssetName.png"
            "width" = $finalWidth
            "height" = $finalHeight
        }
        
        $assetDefinition["category"] = if ($presetConfig.Category) { $presetConfig.Category } else { "active" }
        
        if ($presetConfig.TargetType) {
            $assetDefinition["target_type"] = $presetConfig.TargetType
        }
        if ($presetConfig.Range) {
            $assetDefinition["range"] = $presetConfig.Range
        }
        if ($presetConfig.ManaCost) {
            $assetDefinition["mana_cost"] = $presetConfig.ManaCost
        }
        if ($presetConfig.Duration) {
            $assetDefinition["duration"] = $presetConfig.Duration
        }
    }
    
    "Tile" {
        $assetDefinition["sprite"] = [ordered]@{
            "path" = "tiles/$AssetName.png"
            "width" = $finalWidth
            "height" = $finalHeight
            "variants" = if ($presetConfig.Variants) { $presetConfig.Variants } else { 4 }
        }
        
        $assetDefinition["walkable"] = if ($null -ne $presetConfig.Walkable) { $presetConfig.Walkable } else { $true }
        
        if ($presetConfig.BlocksVision) {
            $assetDefinition["blocks_vision"] = $true
        }
        if ($presetConfig.Interactable) {
            $assetDefinition["interactable"] = $true
        }
    }
    
    "Building" {
        $assetDefinition["sprite"] = [ordered]@{
            "path" = "buildings/$AssetName.png"
            "width" = $finalWidth
            "height" = $finalHeight
        }
        $assetDefinition["footprint"] = [ordered]@{
            "width" = [int]($finalWidth / 32)
            "height" = [int]($finalHeight / 32)
        }
    }
    
    "Effect" {
        $assetDefinition["animation"] = [ordered]@{
            "path" = "effects/$AssetName.png"
            "width" = $finalWidth
            "height" = $finalHeight
            "frames" = $finalFrames
            "fps" = 12
            "loop" = $false
        }
    }
    
    "Spritesheet" {
        $assetDefinition["spritesheet"] = [ordered]@{
            "path" = "spritesheets/$AssetName.png"
            "sprite_width" = $finalWidth
            "sprite_height" = $finalHeight
            "columns" = $finalFrames
            "rows" = $finalDirections * $finalVariants
        }
        
        $assetDefinition["animations"] = [ordered]@{
            "idle" = @{ "row" = 0; "frames" = $finalFrames; "fps" = 4 }
            "walk" = @{ "row" = 1; "frames" = $finalFrames; "fps" = 8 }
            "attack" = @{ "row" = 2; "frames" = $finalFrames; "fps" = 12 }
            "death" = @{ "row" = 3; "frames" = $finalFrames; "fps" = 6 }
        }
    }
}

# Write asset definition
$jsonFile = Join-Path $assetDir "$AssetName.json"
$assetDefinition | ConvertTo-Json -Depth 10 | Out-File -FilePath $jsonFile -Encoding UTF8 -Force
Write-Host ""
Write-Host "[Created] $jsonFile" -ForegroundColor Green

# ============================================================================
# Generate Placeholder Images (optional)
# ============================================================================

# Art is on by default so the generator fills its role (PNG + JSON).
if (-not $SkipArt -or $GeneratePlaceholder) {
    $spritePath = switch ($AssetType) {
        "Creature" { Join-Path $assetDir "sprites" }
        "Portrait" { Join-Path $assetDir "portraits" }
        "Item" { Join-Path $assetDir "items" }
        "Ability" { Join-Path $assetDir "abilities" }
        "Tile" { Join-Path $assetDir "tiles" }
        "Building" { Join-Path $assetDir "buildings" }
        "Effect" { Join-Path $assetDir "effects" }
        "Spritesheet" { Join-Path $assetDir "spritesheets" }
        default { $assetDir }
    }
    
    if (-not (Test-Path $spritePath)) {
        New-Item -ItemType Directory -Path $spritePath -Force | Out-Null
    }
    
    $pngFile = Join-Path $spritePath "$AssetName.png"
    $success = New-PlaceholderAssetImage -OutputPath $pngFile `
        -Width $finalWidth -Height $finalHeight `
        -Type $AssetType -BaseColor $baseColor `
        -Variants $finalVariants -Frames $finalFrames
    
    if ($success) {
        Write-Host "[Created] $pngFile (procedural)" -ForegroundColor Green
    }
    
    # For creatures, also generate portrait art
    if ($AssetType -eq "Creature") {
        $portraitPath = Join-Path $assetDir "portraits"
        if (-not (Test-Path $portraitPath)) {
            New-Item -ItemType Directory -Path $portraitPath -Force | Out-Null
        }
        
        $portraitFile = Join-Path $portraitPath "$AssetName.png"
        $success = New-PlaceholderAssetImage -OutputPath $portraitFile `
            -Width $PortraitSize -Height $PortraitSize `
            -Type "Portrait" -BaseColor $baseColor `
            -Variants $finalVariants -Frames 1
        
        if ($success) {
            Write-Host "[Created] $portraitFile (procedural portrait)" -ForegroundColor Green
        }
    }
}

# ============================================================================
# Generate Spritesheet Layout Guide (for Creatures)
# ============================================================================

if ($AssetType -eq "Creature" -or $AssetType -eq "Spritesheet") {
    $guideContent = @"
# Spritesheet Layout: $AssetName

## Grid Layout
- Sprite Size: ${finalWidth}x${finalHeight} pixels
- Animation Frames: $finalFrames
- Directions: $finalDirections (down, left, right, up)
- Color Variants: $finalVariants

## Row Layout
| Row | Content |
|-----|---------|
| 0 | Idle animation (Direction 1) |
| 1 | Walk animation (Direction 1) |
| 2 | Attack animation (Direction 1) |
| 3 | Death animation (Direction 1) |
"@
    
    if ($finalDirections -gt 1) {
        $guideContent += @"

| 4-7 | Direction 2 animations |
| 8-11 | Direction 3 animations |
| 12-15 | Direction 4 animations |
"@
    }
    
    if ($hasHornsFlag -or $hasTailFlag -or $hasWingsFlag) {
        $guideContent += @"


## Body Parts (Separate Rows)
"@
        if ($hasHornsFlag) { $guideContent += "`n- Horns: Row after main animations" }
        if ($hasTailFlag) { $guideContent += "`n- Tail: Following row" }
        if ($hasWingsFlag) { $guideContent += "`n- Wings: Following row" }
    }
    
    $guideFile = Join-Path $assetDir "${AssetName}_layout.md"
    $guideContent | Out-File -FilePath $guideFile -Encoding UTF8 -Force
    Write-Host "[Created] ${AssetName}_layout.md (spritesheet guide)" -ForegroundColor Green
}

# ============================================================================
# Summary
# ============================================================================

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Generation Summary" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Asset Name: $AssetName" -ForegroundColor White
Write-Host "  Asset Type: $AssetType" -ForegroundColor White
Write-Host "  Preset: $Preset" -ForegroundColor White
Write-Host "  Dimensions: ${finalWidth}x${finalHeight}" -ForegroundColor Yellow

if ($AssetType -eq "Creature") {
    Write-Host "  Color Variants: $finalVariants" -ForegroundColor Yellow
    Write-Host "  Body Parts:" -ForegroundColor Yellow
    Write-Host "    - Horns: $hasHornsFlag" -ForegroundColor Gray
    Write-Host "    - Tail: $hasTailFlag" -ForegroundColor Gray
    Write-Host "    - Wings: $hasWingsFlag" -ForegroundColor Gray
}

Write-Host ""
Write-Host "Output Directory: $assetDir" -ForegroundColor Cyan
Write-Host ""

# Return result
return @{
    Success = $true
    AssetFile = $jsonFile
    AssetName = $AssetName
    AssetType = $AssetType
    Preset = $Preset
    OutputDirectory = $assetDir
}

