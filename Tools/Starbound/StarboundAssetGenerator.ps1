#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Unified Starbound asset generator that integrates PowerShell tools with C++ backend.
    AI-Assisted Modding Tools (AAMT)
    
.DESCRIPTION
    Generates Starbound-compatible assets using:
    - PowerShell asset generators (Blender, Ollama, etc.)
    - C++ backend generators (via Lua bridge)
    - Automatic format conversion for Starbound
    Part of the AI-Assisted Modding Tools (AAMT) suite.

.PARAMETER AssetType
    Type of asset: Portal, Particle, Texture, Animation, Icon, Spell, Projectile
    
.PARAMETER AssetName
    Name of the asset
    
.PARAMETER Description
    Description for AI generation
    
.PARAMETER UseCppBackend
    Use C++ backend instead of PowerShell generators
    
.PARAMETER CppBackendPath
    Path to C++ backend
    
.PARAMETER OutputDir
    Output directory

.PARAMETER AllowProcedural
    All sprite / icon / animation-sheet / texture art is rendered with the local Stable
    Diffusion 3.5 server (:1338) through StarboundSdArt.psm1 and the script throws when SD
    cannot deliver. With this switch (or AAMT_SD_STRICT=0) the legacy procedural drawing
    (System.Drawing shapes, the C++ backend, AssetMakerAI procedural textures) may run, but
    only as a fallback after an SD failure. -UseCppBackend is ignored without it because the
    C++ backend only draws procedural art.
#>

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("Portal", "PortalSprite", "Particle", "Texture", "Animation", "Icon", "Spell", "Projectile", "Sprite", "ItemSprite", "MechSprite", "AnimationSprite", "Ship", "Tile", "Cursor", "Behavior", "Sound", "DungeonFloorTile", "DungeonDecorTile", "DungeonWallTile", "PlantSprite")]
    [string]$AssetType = "Texture",
    
    [Parameter(Mandatory=$true)]
    [string]$AssetName,
    
    [Parameter(Mandatory=$false)]
    [string]$Description = "",
    
    [Parameter(Mandatory=$false)]
    [switch]$UseCppBackend,
    
    [Parameter(Mandatory=$false)]
    [string]$CppBackendPath = "F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery\cpp_backend",
    
    [Parameter(Mandatory=$false)]
    [string]$OutputDir = "StarboundAssets",
    
    [Parameter(Mandatory=$false)]
    [hashtable]$Parameters = @{},

    [Parameter(Mandatory=$false)]
    [switch]$AllowProcedural
)

$ErrorActionPreference = "Stop"

# Validate MyInvocation.MyCommand.Path is not null before using it
$scriptPath = $MyInvocation.MyCommand.Path
if ([string]::IsNullOrWhiteSpace($scriptPath)) {
    Write-Host "Error: Cannot determine script path (MyInvocation.MyCommand.Path is null)" -ForegroundColor Red
    exit 1
}

$PSScriptRoot = Split-Path -Parent $scriptPath

# Validate PSScriptRoot is not null or empty
if ([string]::IsNullOrWhiteSpace($PSScriptRoot)) {
    Write-Host "Error: Cannot determine script root directory" -ForegroundColor Red
    Write-Host "  MyInvocation.MyCommand.Path: '$scriptPath'" -ForegroundColor Gray
    exit 1
}

# Import unified tool detection and integration
$sharedPath = Join-Path (Split-Path -Parent $PSScriptRoot) "Shared"
Import-Module (Join-Path $sharedPath "ToolDetection.psm1") -ErrorAction SilentlyContinue
Import-Module (Join-Path $sharedPath "ToolsetIntegration.psm1") -ErrorAction SilentlyContinue

# Stable Diffusion art (real pixels from the SD3.5 server on :1338). No procedural fallback
# unless -AllowProcedural is passed or AAMT_SD_STRICT=0.
Import-Module (Join-Path $PSScriptRoot "StarboundSdArt.psm1") -Force
$script:ProceduralAllowed = $AllowProcedural.IsPresent -or ($env:AAMT_SD_STRICT -eq '0')

# Initialize tools for Starbound asset generation
$tools = Initialize-ToolsetTools `
    -RequiredTools @("ImageMagick") `
    -OptionalTools @("Ollama", "StableDiffusion", "Python", "Blender")

# Check required tools
if (-not $tools.AllRequiredAvailable) {
    Write-Host "`nERROR: Missing required tools for Starbound asset generation" -ForegroundColor Red
    Show-ToolsetStatus -ToolsetName "Starbound" `
        -RequiredTools @("ImageMagick") `
        -OptionalTools @("Ollama", "StableDiffusion", "Python", "Blender")
    exit 1
}

# Use Ollama if available
if ($tools.Tools["Ollama"].Available) {
    Use-OllamaIfAvailable | Out-Null
}

# Load shared asset generation settings (moved here after validation)
$settingsPath = Join-Path (Split-Path -Parent $PSScriptRoot) "AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Starbound Asset Generator" -ForegroundColor Cyan
Write-Host "  AI-Assisted Modding Tools (AAMT)" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Validate AssetName is not empty
if ([string]::IsNullOrWhiteSpace($AssetName)) {
    Write-Host "Error: AssetName cannot be empty" -ForegroundColor Red
    Write-Host "  AssetType: $AssetType" -ForegroundColor Gray
    exit 1
}

# Validate OutputDir is not empty (use default if needed)
if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $OutputDir = "StarboundAssets"
    Write-Host "Warning: OutputDir was empty, using default: $OutputDir" -ForegroundColor Yellow
}

# Convert OutputDir to absolute path if it's relative
if (-not [System.IO.Path]::IsPathRooted($OutputDir)) {
    $OutputDir = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot $OutputDir))
    Write-Host "Converted relative OutputDir to absolute path: $OutputDir" -ForegroundColor Gray
} else {
    # Ensure it's a fully resolved absolute path
    $OutputDir = [System.IO.Path]::GetFullPath($OutputDir)
}

# Ensure OutputDir exists (create if needed)
if (-not (Test-Path $OutputDir)) {
    try {
        New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
        Write-Host "Created output directory: $OutputDir" -ForegroundColor Green
    } catch {
        Write-Host "Error: Failed to create output directory '$OutputDir': $_" -ForegroundColor Red
        exit 1
    }
}

# Helper function to validate sprite quality (detect colored boxes)
function Test-SpriteQuality {
    param(
        [string]$ImagePath,
        [int]$MinUniqueColors = 10,
        [double]$MinStdDev = 0.1
    )
    
    if (-not (Test-Path $ImagePath)) {
        return $false
    }
    
    try {
        Add-Type -AssemblyName System.Drawing
        $bitmap = New-Object System.Drawing.Bitmap($ImagePath)
        
        # Count unique colors
        $colorSet = New-Object System.Collections.Generic.HashSet[string]
        $pixelCount = 0
        $totalR = 0
        $totalG = 0
        $totalB = 0
        
        for ($y = 0; $y -lt $bitmap.Height; $y++) {
            for ($x = 0; $x -lt $bitmap.Width; $x++) {
                $pixel = $bitmap.GetPixel($x, $y)
                if ($pixel.A -gt 0) {  # Only count non-transparent pixels
                    $colorKey = "$($pixel.R),$($pixel.G),$($pixel.B)"
                    if (-not $colorSet.Contains($colorKey)) {
                        $colorSet.Add($colorKey) | Out-Null
                    }
                    $totalR += $pixel.R
                    $totalG += $pixel.G
                    $totalB += $pixel.B
                    $pixelCount++
                }
            }
        }
        
        $bitmap.Dispose()
        
        # Check unique color count
        if ($colorSet.Count -lt $MinUniqueColors) {
            return $false
        }
        
        # Calculate standard deviation of colors (rough estimate)
        if ($pixelCount -gt 0) {
            $avgR = $totalR / $pixelCount
            $avgG = $totalG / $pixelCount
            $avgB = $totalB / $pixelCount
            
            # Simple variance estimate (not true std dev, but good enough for detection)
            $variance = ($avgR + $avgG + $avgB) / 3.0
            $stdDev = [Math]::Sqrt($variance) / 255.0
            
            if ($stdDev -lt $MinStdDev) {
                return $false
            }
        }
        
        return $true
    } catch {
        # If validation fails, assume valid (don't block generation)
        return $true
    }
}

# ---------------------------------------------------------------------------
# Stable Diffusion art helpers. Every routine that used to draw a PNG procedurally
# now delegates to Write-StarboundArt, which builds the prompt and calls New-StarboundSdArt.
# ---------------------------------------------------------------------------
function Get-StarboundArtSeed {
    param([string]$Text)
    $h = 17
    foreach ($ch in $Text.ToCharArray()) { $h = (($h * 31) + [int]$ch) % 899981 }
    return ($h + 1)
}

function ConvertTo-StarboundColorWord {
    param([int]$R, [int]$G, [int]$B)
    $max = [Math]::Max($R, [Math]::Max($G, $B))
    $min = [Math]::Min($R, [Math]::Min($G, $B))
    $delta = $max - $min
    if ($max -lt 50) { return "black" }
    if ($delta -lt 30) {
        if ($max -gt 215) { return "white" }
        if ($max -gt 150) { return "light gray" }
        return "dark gray"
    }
    if ($max -eq $R) { $hue = 60.0 * ((($G - $B) / [double]$delta) % 6) }
    elseif ($max -eq $G) { $hue = 60.0 * ((($B - $R) / [double]$delta) + 2) }
    else { $hue = 60.0 * ((($R - $G) / [double]$delta) + 4) }
    if ($hue -lt 0) { $hue += 360 }
    $name = "red"
    if ($hue -ge 15 -and $hue -lt 40) { $name = "orange" }
    elseif ($hue -ge 40 -and $hue -lt 70) { $name = "yellow" }
    elseif ($hue -ge 70 -and $hue -lt 160) { $name = "green" }
    elseif ($hue -ge 160 -and $hue -lt 200) { $name = "cyan" }
    elseif ($hue -ge 200 -and $hue -lt 255) { $name = "blue" }
    elseif ($hue -ge 255 -and $hue -lt 290) { $name = "purple" }
    elseif ($hue -ge 290 -and $hue -lt 345) { $name = "magenta" }
    if ($max -lt 120) { return "dark $name" }
    if ($max -gt 230 -and $delta -lt 110) { return "pale $name" }
    return $name
}

function Get-StarboundPaletteWords {
    # Palette: array of @(r,g,b) triples (or one flat @(r,g,b)). Returns "red, dark blue, ...".
    param($Palette)
    if ($null -eq $Palette) { return "" }
    $items = @($Palette)
    if ($items.Count -eq 0) { return "" }
    if ($items[0] -is [ValueType] -or $items[0] -is [string]) { $items = @(, $items) }
    $words = @()
    foreach ($c in $items) {
        $arr = @($c)
        if ($arr.Count -lt 3) { continue }
        try { $w = ConvertTo-StarboundColorWord -R ([int]$arr[0]) -G ([int]$arr[1]) -B ([int]$arr[2]) } catch { continue }
        if ($words -notcontains $w) { $words += $w }
    }
    return ($words -join ", ")
}

function Write-StarboundArt {
    <#
    .SYNOPSIS
    Builds an SD prompt from asset type / name / description / palette and renders the PNG
    (single sprite, or a Frames-cell sheet) through New-StarboundSdArt. Returns $true when the
    PNG was written; $false only when SD failed AND procedural output is allowed; throws
    otherwise.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][string]$AssetType,
        [Parameter(Mandatory = $true)][string]$Name,
        [string]$Description = "",
        [Parameter(Mandatory = $true)][int]$Width,
        [Parameter(Mandatory = $true)][int]$Height,
        [Parameter(Mandatory = $true)][string]$OutputPath,
        [int]$Frames = 1,
        [int]$Columns = 0,
        [string[]]$FrameNotes = @(),
        $Palette = $null,
        [bool]$Transparent = $true,
        [bool]$Pixel = $true,
        [int]$Colors = 24,
        [string]$SdKind = "icon"
    )

    $subject = switch ($AssetType) {
        "ItemSprite"      { "inventory item icon of" }
        "MechSprite"      { "mech part icon of" }
        "Icon"            { "user interface icon of" }
        "Sprite"          { "game object sprite of" }
        "Projectile"      { "projectile sprite in flight of" }
        "Particle"        { "small glowing particle effect sprite of" }
        "Texture"         { "seamless tileable texture of" }
        "Animation"       { "animation spritesheet frame of" }
        "AnimationSprite" { "animation spritesheet frame of" }
        default           { "game sprite of" }
    }
    $readable = (($Name -creplace '([a-z0-9])([A-Z])', '$1 $2') -replace '[_\-\.]+', ' ').Trim()
    $desc = ($Description -replace '[\r\n\t]+', ' ' -replace '["`|]', '').Trim()
    if ($desc.Length -gt 320) { $desc = $desc.Substring(0, 320) }
    $parts = @("$subject $readable")
    if ($desc) { $parts += $desc }
    $pal = Get-StarboundPaletteWords -Palette $Palette
    if ($pal) { $parts += "color palette: $pal" }
    $prompt = ($parts -join ". ")

    $common = @{
        Prompt          = $prompt
        OutputPath      = $OutputPath
        Width           = $Width
        Height          = $Height
        Transparent     = $Transparent
        Pixel           = $Pixel
        Colors          = $Colors
        Seed            = (Get-StarboundArtSeed "$AssetType|$Name")
        SdKind          = $SdKind
        AllowProcedural = $script:ProceduralAllowed
    }
    if ($Frames -gt 1) {
        $notes = @($FrameNotes | ForEach-Object { ($_ -replace '["`|]', '').Trim() } | Where-Object { $_ })
        $cols = if ($Columns -gt 0) { $Columns } else { $Frames }
        $common['Kind'] = "sheet"
        $common['Count'] = $Frames
        $common['Columns'] = $cols
        $common['Consistent'] = $true   # animation frames keep one subject (img2img from frame 1)
        if ($notes.Count -gt 0) { $common['Variants'] = $notes }
    } else {
        $common['Kind'] = "sprite"
    }
    # Throws when SD cannot deliver unless procedural output is allowed (then returns $false).
    return [bool](New-StarboundSdArt @common)
}

# Function to generate individual sprites (not spritesheets)
# Art comes from Stable Diffusion (Write-StarboundArt); the System.Drawing shapes further down
# are the -AllowProcedural fallback only.
# Note: For spritesheets (animations), see Generate-AnimationSprite which handles per-frame scaling.
# Individual sprite size limits (Starbound requirements):
# - ItemSprite: 16x16 (item icons in inventory/hotbar)
# - MechSprite: 48x48 (mech part icons in UI)
# - Icon: 64x64 (UI interface icons)
# - Sprite (generic): 48x48 (object/furniture icons)
# - Projectile: 48x48 (projectile sprites)
# - Particle: 32x32 (particle effects, typically small)
# Sprites are generated at higher resolution (64x64 or 32x32 for particles) for detail, then scaled down to final size.
# Must be defined before it's called in the switch statement below
function Generate-AssetSprite {
    param(
        [string]$AssetName,
        [string]$Description,
        [hashtable]$Parameters,
        [string]$OutputDir,
        [string]$SpriteType
    )
    
    # Validate AssetName is not empty
    if ([string]::IsNullOrWhiteSpace($AssetName)) {
        Write-Host "  [FAIL] Skipping ${SpriteType} with empty AssetName" -ForegroundColor Red
        return $false
    }
    
    # Validate OutputDir is not empty
    if ([string]::IsNullOrWhiteSpace($OutputDir)) {
        Write-Host "  [FAIL] Skipping ${SpriteType} '$AssetName' with empty OutputDir" -ForegroundColor Red
        return $false
    }
    
    Write-Host "Generating ${SpriteType}: $AssetName" -ForegroundColor Cyan
    
    # Determine sprite dimensions
    # Generate at higher resolution for detail, then scale down to Starbound's required sizes:
    # - ItemSprite: Generate at 64x64, scale to 16x16 (Starbound requirement for item icons)
    # - MechSprite: Generate at 64x64, scale to 48x48 (max for mech part icons)
    # - Icon: Generate at 64x64, keep at 64x64 (UI icon limit)
    # - Sprite (generic): Generate at 64x64, scale to 48x48 (object/furniture icon limit)
    # - Projectile: Generate at 64x64, scale to 48x48 (projectile sprite limit)
    # - Particle: Generate at 32x32, keep at 32x32 (particles are typically small)
    $generateWidth = if ($Parameters.Width) { $Parameters.Width } else { 
        if ($SpriteType -eq "ItemSprite") { 64 }  # Generate at 64x64 for detail, scale to 16x16
        elseif ($SpriteType -eq "MechSprite") { 64 }  # Generate at 64x64 for detail, scale to 48x48
        elseif ($SpriteType -eq "Icon") { if ($Parameters.Size) { $Parameters.Size } else { 64 } }
        elseif ($SpriteType -eq "Particle") { 32 }  # Particles are small, generate at 32x32
        else { 64 }  # Default: generate at 64x64 for other sprites
    }
    $generateHeight = if ($Parameters.Height) { $Parameters.Height } else { 
        if ($SpriteType -eq "ItemSprite") { 64 }  # Generate at 64x64 for detail, scale to 16x16
        elseif ($SpriteType -eq "MechSprite") { 64 }  # Generate at 64x64 for detail, scale to 48x48
        elseif ($SpriteType -eq "Icon") { if ($Parameters.Size) { $Parameters.Size } else { 64 } }
        elseif ($SpriteType -eq "Particle") { 32 }  # Particles are small, generate at 32x32
        else { 64 }  # Default: generate at 64x64 for other sprites
    }
    
    # Final output dimensions (Starbound requirements per asset type)
    $finalWidth = if ($SpriteType -eq "ItemSprite") { 16 }
                  elseif ($SpriteType -eq "MechSprite") { 48 }
                  elseif ($SpriteType -eq "Sprite") { 48 }  # Generic sprites (objects/furniture) use 48x48
                  elseif ($SpriteType -eq "Projectile") { 48 }  # Projectiles use 48x48
                  elseif ($SpriteType -eq "Particle") { 32 }  # Particles stay at 32x32
                  else { $generateWidth }  # Icon and others keep generation size
    $finalHeight = if ($SpriteType -eq "ItemSprite") { 16 }
                   elseif ($SpriteType -eq "MechSprite") { 48 }
                   elseif ($SpriteType -eq "Sprite") { 48 }  # Generic sprites (objects/furniture) use 48x48
                   elseif ($SpriteType -eq "Projectile") { 48 }  # Projectiles use 48x48
                   elseif ($SpriteType -eq "Particle") { 32 }  # Particles stay at 32x32
                   else { $generateHeight }  # Icon and others keep generation size
    
    # Use generation dimensions for bitmap creation
    $width = $generateWidth
    $height = $generateHeight
    $frameCount = if ($Parameters.FrameCount) { $Parameters.FrameCount } else { 1 }
    
    # Validate OutputDir before using it in Join-Path
    if ([string]::IsNullOrWhiteSpace($OutputDir)) {
        Write-Host "  [FAIL] OutputDir is null or empty, cannot create sprite directory" -ForegroundColor Red
        return $false
    }
    
    # Create output directory structure
    # Note: Final output sizes:
    # - ItemSprite: 16x16 (Starbound requirement)
    # - MechSprite: 48x48 (max for mech part icons)
    # - Icon: 64x64 (UI icon limit)
    $spriteDir = if ($SpriteType -eq "ItemSprite") {
        Join-Path $OutputDir "items\sprites"
    } elseif ($SpriteType -eq "MechSprite") {
        Join-Path $OutputDir "mechs\sprites"
    } elseif ($SpriteType -eq "Icon") {
        Join-Path $OutputDir "interface\icons"
    } else {
        Join-Path $OutputDir "sprites"
    }
    
    # Validate spriteDir is not null before creating directory
    if ([string]::IsNullOrWhiteSpace($spriteDir)) {
        Write-Host "  [FAIL] Cannot create directory: spriteDir is null (OutputDir: '$OutputDir')" -ForegroundColor Red
        return $false
    }
    
    if (-not (Test-Path $spriteDir)) {
        try {
            New-Item -ItemType Directory -Path $spriteDir -Force | Out-Null
        } catch {
            Write-Host "  [FAIL] Cannot create directory '$spriteDir': $_" -ForegroundColor Red
            return $false
        }
    }
    
    # Delivered PNG size. ItemSprite/MechSprite are always delivered at their Starbound size;
    # every other type keeps the generation size ($width x $height).
    $outW = if ($SpriteType -eq "ItemSprite" -or $SpriteType -eq "MechSprite") { [int]$finalWidth } else { [int]$width }
    $outH = if ($SpriteType -eq "ItemSprite" -or $SpriteType -eq "MechSprite") { [int]$finalHeight } else { [int]$height }

    # Real art first: Stable Diffusion, prompted from the sprite type, name, (Ollama) description
    # and colour palette. Throws if SD fails unless procedural output is explicitly allowed,
    # in which case $sdOk is $false and the legacy drawing below runs.
    $sdSpritePath = Join-Path $spriteDir "$AssetName.png"
    Write-Host "Generating $SpriteType art with Stable Diffusion (${outW}x${outH})..." -ForegroundColor Green
    $sdOk = Write-StarboundArt -AssetType $SpriteType -Name $AssetName -Description $Description `
        -Width $outW -Height $outH -OutputPath $sdSpritePath -Palette $Parameters.ColorPalette
    if ($sdOk) {
        $fileInfo = Get-Item $sdSpritePath
        Write-Host "✓ Sprite saved: $sdSpritePath ($([math]::Round($fileInfo.Length/1KB, 2)) KB)" -ForegroundColor Green
    }

    # Legacy fallback only (SD failed and -AllowProcedural / AAMT_SD_STRICT=0):
    # prioritize Description-based drawing when Description is provided (from Ollama),
    # otherwise the C++ backend.
    $cppBackendPath ="F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery\cpp_backend"
    
    # Validate PSScriptRoot before using it
    if ([string]::IsNullOrWhiteSpace($PSScriptRoot)) {
        Write-Host "  [FAIL] PSScriptRoot is null, cannot locate bridge script" -ForegroundColor Red
        return $false
    }
    
    $bridgeScript = Join-Path $PSScriptRoot "StarboundCppBackendBridge.ps1"
    
    # Validate bridgeScript path is not null
    if ([string]::IsNullOrWhiteSpace($bridgeScript)) {
        Write-Host "  [FAIL] Failed to construct bridge script path" -ForegroundColor Red
        Write-Host "    PSScriptRoot: '$PSScriptRoot'" -ForegroundColor Gray
        return $false
    }
    
    # If Description is provided (from Ollama), prefer description-based generation over simple C++ backend shapes
    $useDescriptionBased = $Description -and $Description.Trim().Length -gt 20  # Meaningful description from Ollama
    
    if ($sdOk) {
        # Stable Diffusion already wrote the PNG; only the .frames file remains.
    } elseif ($useDescriptionBased) {
        Write-Host "[FALLBACK] Stable Diffusion unavailable - drawing procedural sprite from the Ollama description (-AllowProcedural)..." -ForegroundColor Yellow
        Write-Host "Description: $($Description.Substring(0, [Math]::Min(100, $Description.Length)))..." -ForegroundColor Gray
        # Fall through to the procedural fallback below
    } elseif ((Test-Path $bridgeScript) -and (Test-Path $cppBackendPath)) {
        Write-Host "[FALLBACK] Stable Diffusion unavailable - using C++ backend procedural generation (-AllowProcedural)..." -ForegroundColor Yellow
        
        $bridgeParams = @{
            BackendPath = $cppBackendPath
            GeneratorType = "Image"
            Action = "Generate"
            AssetName = $AssetName
            OutputDir = $spriteDir
            Parameters = @{
                Width = $width
                Height = $height
                FrameCount = $frameCount
                SpriteType = $SpriteType
                # Always pass Description and UseOllama when Description is available
                Description = if ($Description) { $Description } else { "" }
                UseOllama = if ($Description -and $Description.Trim().Length -gt 0) { $true } else { $false }
            }
        }
        
        # Log Ollama usage
        if ($bridgeParams.Parameters.UseOllama) {
            Write-Host "  → C++ backend will use Ollama for high-quality generation" -ForegroundColor Green
            Write-Host "    Description: $($Description.Substring(0, [Math]::Min(80, $Description.Length)))..." -ForegroundColor Gray
        }
        
        & $bridgeScript @bridgeParams
        return  # Exit early if C++ backend was used
    }
    
    # PROCEDURAL FALLBACK ONLY: runs when Stable Diffusion failed and -AllowProcedural (or
    # AAMT_SD_STRICT=0) is set. Never runs by default.
    if (-not $sdOk) {
        Write-Host "Generating procedural placeholder sprite (SD fallback)..." -ForegroundColor Yellow

        # Create a simple procedural sprite using .NET Graphics
        Add-Type -AssemblyName System.Drawing
        
        # Validate spriteDir and AssetName before Join-Path
        if ([string]::IsNullOrWhiteSpace($spriteDir)) {
            Write-Host "  [FAIL] spriteDir is null, cannot create sprite path" -ForegroundColor Red
            return $false
        }
        if ([string]::IsNullOrWhiteSpace($AssetName)) {
            Write-Host "  [FAIL] AssetName is null, cannot create sprite path" -ForegroundColor Red
            return $false
        }
        
        $spritePath = Join-Path $spriteDir "$AssetName.png"
        
        # Validate spritePath is not null
        if ([string]::IsNullOrWhiteSpace($spritePath)) {
            Write-Host "  [FAIL] spritePath is null (spriteDir: '$spriteDir', AssetName: '$AssetName')" -ForegroundColor Red
            return $false
        }
        
        # Validate width and height before creating bitmap
        if ($width -le 0 -or $height -le 0) {
            Write-Host "  [FAIL] Invalid bitmap dimensions: width=$width, height=$height" -ForegroundColor Red
            Write-Host "    Width and height must be greater than 0" -ForegroundColor Yellow
            return $false
        }
        
        # Ensure width and height are integers
        $width = [int]$width
        $height = [int]$height
        
        if ($width -le 0 -or $height -le 0) {
            Write-Host "  [FAIL] Invalid bitmap dimensions after conversion: width=$width, height=$height" -ForegroundColor Red
            return $false
        }
        
        # Create bitmap in 32-bit ARGB format (Starbound requirement)
        try {
            $bitmap = New-Object System.Drawing.Bitmap($width, $height, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
        } catch {
            Write-Host "  [FAIL] Failed to create bitmap: $_" -ForegroundColor Red
            Write-Host "    Width: $width, Height: $height" -ForegroundColor Gray
            return $false
        }
        $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
        $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
        $graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
        $graphics.CompositingMode = [System.Drawing.Drawing2D.CompositingMode]::SourceOver
        $graphics.CompositingQuality = [System.Drawing.Drawing2D.CompositingQuality]::HighQuality
        
        # Get color palette from parameters or use defaults
        $colors = if ($Parameters.ColorPalette) {
            $Parameters.ColorPalette | ForEach-Object {
                if ($_ -is [array] -and $_.Count -ge 3) {
                    [System.Drawing.Color]::FromArgb($_[0], $_[1], $_[2])
                } else {
                    [System.Drawing.Color]::FromArgb(255, 200, 100)
                }
            }
        } else {
            @(
                [System.Drawing.Color]::FromArgb(255, 200, 100),
                [System.Drawing.Color]::FromArgb(200, 150, 80),
                [System.Drawing.Color]::FromArgb(150, 100, 60)
            )
        }
        
        # Generate procedural sprite based on description (enhanced usage)
        # Use description to determine visual style, colors, and patterns
        $descLower = $Description.ToLower()
        
        # Determine style from description
        $style = "default"
        $hasGradient = $false
        $hasPattern = $false
        $hasSparkles = $false
        $hasBorder = $true
        
        if ($descLower -match "magic|arcane|spell|mystical|enchant") {
            $style = "magical"
            $hasGradient = $true
            $hasSparkles = $true
        } elseif ($descLower -match "weapon|sword|blade|tool|metal") {
            $style = "metallic"
            $hasPattern = $true
        } elseif ($descLower -match "crystal|gem|shiny|glowing") {
            $style = "crystalline"
            $hasGradient = $true
            $hasSparkles = $true
        } elseif ($descLower -match "organic|plant|nature|wood") {
            $style = "organic"
            $hasPattern = $true
        } elseif ($descLower -match "energy|plasma|electric|lightning") {
            $style = "energy"
            $hasGradient = $true
            $hasPattern = $true
        }
        
        # Extract ALL color hints from description (not just first match)
        # This allows for multi-colored sprites (e.g., "ruby, sapphire, emerald")
        $extractedColors = @()
        $colorDefinitions = @{
            "purple|violet" = @(
                [System.Drawing.Color]::FromArgb(200, 100, 255),
                [System.Drawing.Color]::FromArgb(150, 50, 200),
                [System.Drawing.Color]::FromArgb(100, 25, 150)
            )
            "blue|azure|sapphire" = @(
                [System.Drawing.Color]::FromArgb(100, 150, 255),
                [System.Drawing.Color]::FromArgb(50, 100, 200),
                [System.Drawing.Color]::FromArgb(25, 50, 150)
            )
            "red|crimson|fire|ruby" = @(
                [System.Drawing.Color]::FromArgb(255, 100, 100),
                [System.Drawing.Color]::FromArgb(200, 50, 50),
                [System.Drawing.Color]::FromArgb(150, 25, 25)
            )
            "green|emerald|jade" = @(
                [System.Drawing.Color]::FromArgb(100, 255, 100),
                [System.Drawing.Color]::FromArgb(50, 200, 50),
                [System.Drawing.Color]::FromArgb(25, 150, 25)
            )
            "gold|golden|yellow" = @(
                [System.Drawing.Color]::FromArgb(255, 200, 100),
                [System.Drawing.Color]::FromArgb(200, 150, 80),
                [System.Drawing.Color]::FromArgb(150, 100, 60)
            )
            "silver|gray|grey|metalwork" = @(
                [System.Drawing.Color]::FromArgb(200, 200, 200),
                [System.Drawing.Color]::FromArgb(160, 160, 160),
                [System.Drawing.Color]::FromArgb(120, 120, 120)
            )
            "white|light|glow|ethereal" = @(
                [System.Drawing.Color]::FromArgb(255, 255, 255),
                [System.Drawing.Color]::FromArgb(220, 220, 255),
                [System.Drawing.Color]::FromArgb(200, 200, 240)
            )
            "orange|amber" = @(
                [System.Drawing.Color]::FromArgb(255, 150, 50),
                [System.Drawing.Color]::FromArgb(220, 120, 30),
                [System.Drawing.Color]::FromArgb(180, 90, 20)
            )
        }
        
        # Find all color matches in the description
        foreach ($pattern in $colorDefinitions.Keys) {
            if ($descLower -match $pattern) {
                $extractedColors += $colorDefinitions[$pattern]
            }
        }
        
        # If we found multiple color sets, use them all
        # Otherwise fall back to the default color
        if ($extractedColors.Count -gt 0) {
            $colors = $extractedColors
        }
        
        # Clear with transparent background
        $graphics.Clear([System.Drawing.Color]::Transparent)
        
        # Use Terraria-style layered approach for better quality
        # Create layered shapes: outer rim, inner core, accent glow
        $centerX = $width / 2.0
        $centerY = $height / 2.0
        $maxRadius = [Math]::Min($width, $height) / 2.0 - 1
        
        # Determine primary shape from description or default to circle
        $shapeType = "Circle"
        if ($descLower -match "square|rectangular|block") {
            $shapeType = "Square"
        } elseif ($descLower -match "hex|hexagonal") {
            $shapeType = "Hexagon"
        } elseif ($descLower -match "tear|jagged|irregular") {
            $shapeType = "Tear"
        } elseif ($descLower -match "ellipse|oval") {
            $shapeType = "Ellipse"
        }
        
        # Create layered portal-style sprite (like Terraria generator)
        # Use multiple colors if available for different elements
        $colorCount = $colors.Count
        
        # Layer 1: Outer rim (darker, larger)
        # For multi-color sprites, use a different color for the rim
        $rimColorIndex = if ($colorCount -gt 3) { 3 } else { [Math]::Max(0, $colorCount - 1) }
        $rimColor = if ($colors.Count -gt $rimColorIndex) { $colors[$rimColorIndex] } else { 
            [System.Drawing.Color]::FromArgb(
                [Math]::Max(0, $colors[0].R - 40),
                [Math]::Max(0, $colors[0].G - 40),
                [Math]::Max(0, $colors[0].B - 40)
            )
        }
        $rimRadius = $maxRadius
        
        # Layer 2: Middle ring (medium color)
        # Use a different color if we have multiple color sets
        $midColorIndex = if ($colorCount -gt 6) { 1 } elseif ($colorCount -gt 3) { 4 } else { [Math]::Min(1, $colorCount - 1) }
        $midColor = if ($colors.Count -gt $midColorIndex) { $colors[$midColorIndex] } else { $colors[0] }
        $midRadius = $maxRadius * 0.85
        
        # Layer 3: Inner core (brightest)
        # Use yet another color if available
        $coreColorIndex = if ($colorCount -gt 6) { 7 } elseif ($colorCount -gt 3) { 0 } else { 0 }
        $coreColor = if ($colors.Count -gt $coreColorIndex) { $colors[$coreColorIndex] } else { $colors[0] }
        $coreRadius = $maxRadius * 0.65
        
        # Draw outer rim
        $rimBrush = New-Object System.Drawing.SolidBrush($rimColor)
        switch ($shapeType) {
            "Square" {
                $rimRect = New-Object System.Drawing.RectangleF(
                    $centerX - $rimRadius, $centerY - $rimRadius,
                    $rimRadius * 2, $rimRadius * 2
                )
                $graphics.FillRectangle($rimBrush, $rimRect)
            }
            "Hexagon" {
                $hexPath = New-Object System.Drawing.Drawing2D.GraphicsPath
                for ($i = 0; $i -lt 6; $i++) {
                    $angle = ($i * 60 - 30) * [Math]::PI / 180
                    $x = $centerX + $rimRadius * [Math]::Cos($angle)
                    $y = $centerY + $rimRadius * [Math]::Sin($angle)
                    if ($i -eq 0) {
                        $hexPath.StartFigure()
                        $hexPath.AddLine([float]$centerX, [float]$centerY, [float]$x, [float]$y)
                    } else {
                        $hexPath.AddLine([float]$x, [float]$y, [float]$x, [float]$y)
                    }
                }
                $hexPath.CloseFigure()
                $graphics.FillPath($rimBrush, $hexPath)
                $hexPath.Dispose()
            }
            "Tear" {
                # Jagged tear shape
                $points = New-Object System.Drawing.Point[] 8
                $points[0] = New-Object System.Drawing.Point([int]$centerX, [int]($centerY - $rimRadius))
                $points[1] = New-Object System.Drawing.Point([int]($centerX + $rimRadius * 0.6), [int]($centerY - $rimRadius * 0.3))
                $points[2] = New-Object System.Drawing.Point([int]($centerX + $rimRadius * 0.8), [int]$centerY)
                $points[3] = New-Object System.Drawing.Point([int]($centerX + $rimRadius * 0.4), [int]($centerY + $rimRadius * 0.5))
                $points[4] = New-Object System.Drawing.Point([int]$centerX, [int]($centerY + $rimRadius))
                $points[5] = New-Object System.Drawing.Point([int]($centerX - $rimRadius * 0.4), [int]($centerY + $rimRadius * 0.5))
                $points[6] = New-Object System.Drawing.Point([int]($centerX - $rimRadius * 0.8), [int]$centerY)
                $points[7] = New-Object System.Drawing.Point([int]($centerX - $rimRadius * 0.6), [int]($centerY - $rimRadius * 0.3))
                $graphics.FillPolygon($rimBrush, $points)
            }
            default {  # Circle or Ellipse
                if ($shapeType -eq "Ellipse") {
                    $graphics.FillEllipse($rimBrush, 
                        [float]($centerX - $rimRadius * 1.2), [float]($centerY - $rimRadius * 0.8),
                        [float]($rimRadius * 2.4), [float]($rimRadius * 1.6))
                } else {
                    $graphics.FillEllipse($rimBrush, 
                        [float]($centerX - $rimRadius), [float]($centerY - $rimRadius),
                        [float]($rimRadius * 2), [float]($rimRadius * 2))
                }
            }
        }
        $rimBrush.Dispose()
        
        # Draw middle ring
        $midBrush = New-Object System.Drawing.SolidBrush($midColor)
        if ($shapeType -eq "Square") {
            $midRect = New-Object System.Drawing.RectangleF(
                $centerX - $midRadius, $centerY - $midRadius,
                $midRadius * 2, $midRadius * 2
            )
            $graphics.FillRectangle($midBrush, $midRect)
        } elseif ($shapeType -eq "Ellipse") {
            $graphics.FillEllipse($midBrush,
                [float]($centerX - $midRadius * 1.1), [float]($centerY - $midRadius * 0.7),
                [float]($midRadius * 2.2), [float]($midRadius * 1.4))
        } else {
            $graphics.FillEllipse($midBrush,
                [float]($centerX - $midRadius), [float]($centerY - $midRadius),
                [float]($midRadius * 2), [float]($midRadius * 2))
        }
        $midBrush.Dispose()
        
        # Draw inner core (brightest)
        $coreBrush = New-Object System.Drawing.SolidBrush($coreColor)
        if ($shapeType -eq "Square") {
            $coreRect = New-Object System.Drawing.RectangleF(
                $centerX - $coreRadius, $centerY - $coreRadius,
                $coreRadius * 2, $coreRadius * 2
            )
            $graphics.FillRectangle($coreBrush, $coreRect)
        } elseif ($shapeType -eq "Ellipse") {
            $graphics.FillEllipse($coreBrush,
                [float]($centerX - $coreRadius * 1.0), [float]($centerY - $coreRadius * 0.6),
                [float]($coreRadius * 2.0), [float]($coreRadius * 1.2))
        } else {
            $graphics.FillEllipse($coreBrush,
                [float]($centerX - $coreRadius), [float]($centerY - $coreRadius),
                [float]($coreRadius * 2), [float]($coreRadius * 2))
        }
        $coreBrush.Dispose()
        
        # Add accent glow ring (like Terraria)
        $accentPen = New-Object System.Drawing.Pen($coreColor, 1.5)
        if ($shapeType -eq "Square") {
            $graphics.DrawRectangle($accentPen, 
                [float]($centerX - $rimRadius + 0.5), [float]($centerY - $rimRadius + 0.5),
                [float]($rimRadius * 2 - 1), [float]($rimRadius * 2 - 1))
        } else {
            $graphics.DrawEllipse($accentPen,
                [float]($centerX - $rimRadius), [float]($centerY - $rimRadius),
                [float]($rimRadius * 2), [float]($rimRadius * 2))
        }
        $accentPen.Dispose()
        
        # Add pattern details based on style
        if ($hasPattern) {
            if ($style -eq "metallic") {
                # Metallic highlights (subtle)
                $highlightPen = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(180, 255, 255, 255), 1)
                $graphics.DrawLine($highlightPen, 
                    [float]($centerX - $coreRadius * 0.5), [float]($centerY - $coreRadius * 0.5),
                    [float]($centerX + $coreRadius * 0.3), [float]($centerY - $coreRadius * 0.3))
                $highlightPen.Dispose()
            } elseif ($style -eq "organic") {
                # Organic texture - small random dots
                $random = New-Object System.Random
                $dotBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(100, $rimColor))
                for ($i = 0; $i -lt 8; $i++) {
                    $angle = $random.NextDouble() * [Math]::PI * 2
                    $dist = $random.NextDouble() * ($rimRadius * 0.7)
                    $x = $centerX + [Math]::Cos($angle) * $dist
                    $y = $centerY + [Math]::Sin($angle) * $dist
                    $size = $random.Next(1, 3)
                    $graphics.FillEllipse($dotBrush, [float]($x - $size/2), [float]($y - $size/2), [float]$size, [float]$size)
                }
                $dotBrush.Dispose()
            } elseif ($style -eq "energy") {
                # Energy waves - concentric rings
                $wavePen = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(150, $midColor), 1)
                for ($i = 1; $i -le 3; $i++) {
                    $waveRadius = $coreRadius + ($rimRadius - $coreRadius) * ($i / 4.0)
                    $graphics.DrawEllipse($wavePen,
                        [float]($centerX - $waveRadius), [float]($centerY - $waveRadius),
                        [float]($waveRadius * 2), [float]($waveRadius * 2))
                }
                $wavePen.Dispose()
            }
        }
        
        # Add sparkles for magical/crystalline styles (more visible)
        if ($hasSparkles) {
            $random = New-Object System.Random
            $sparkleCount = if ($style -eq "crystalline") { 6 } else { 4 }
            for ($i = 0; $i -lt $sparkleCount; $i++) {
                $angle = $random.NextDouble() * [Math]::PI * 2
                $dist = $random.NextDouble() * ($rimRadius * 0.8)
                $x = $centerX + [Math]::Cos($angle) * $dist
                $y = $centerY + [Math]::Sin($angle) * $dist
                $sparkleSize = 2
                $graphics.FillEllipse([System.Drawing.Brushes]::White, 
                    [float]($x - $sparkleSize/2), [float]($y - $sparkleSize/2), 
                    [float]$sparkleSize, [float]$sparkleSize)
            }
        }
        
        # Add gemstones if description mentions them (ruby, sapphire, emerald, etc.)
        if ($descLower -match "gemstone|ruby|sapphire|emerald|diamond|crystal|gem") {
            $random = New-Object System.Random(42)  # Fixed seed for consistent placement
            $gemCount = 0
            $gemColors = @()
            
            # Identify specific gemstones mentioned
            if ($descLower -match "ruby|red") { $gemColors += [System.Drawing.Color]::FromArgb(255, 60, 60); $gemCount++ }
            if ($descLower -match "sapphire|blue") { $gemColors += [System.Drawing.Color]::FromArgb(60, 120, 255); $gemCount++ }
            if ($descLower -match "emerald|green") { $gemColors += [System.Drawing.Color]::FromArgb(60, 255, 60); $gemCount++ }
            if ($descLower -match "diamond|white") { $gemColors += [System.Drawing.Color]::FromArgb(240, 240, 255); $gemCount++ }
            if ($descLower -match "amber|orange") { $gemColors += [System.Drawing.Color]::FromArgb(255, 150, 40); $gemCount++ }
            
            # If no specific gemstones, use generic colors
            if ($gemCount -eq 0) {
                $gemColors = @([System.Drawing.Color]::FromArgb(255, 100, 255), [System.Drawing.Color]::FromArgb(100, 255, 255))
                $gemCount = 2
            }
            
            # Place gemstones around the sprite
            $gemSize = [Math]::Max(2, [int]($rimRadius * 0.15))
            for ($i = 0; $i -lt $gemCount; $i++) {
                $angle = ($i * (360.0 / $gemCount)) * [Math]::PI / 180
                $dist = $rimRadius * 0.7
                $x = $centerX + [Math]::Cos($angle) * $dist
                $y = $centerY + [Math]::Sin($angle) * $dist
                
                $gemColor = $gemColors[$i % $gemColors.Count]
                $gemBrush = New-Object System.Drawing.SolidBrush($gemColor)
                $graphics.FillEllipse($gemBrush, 
                    [float]($x - $gemSize/2), [float]($y - $gemSize/2), 
                    [float]$gemSize, [float]$gemSize)
                $gemBrush.Dispose()
                
                # Add gem highlight
                $highlightColor = [System.Drawing.Color]::FromArgb(200, 255, 255, 255)
                $highlightBrush = New-Object System.Drawing.SolidBrush($highlightColor)
                $highlightSize = [Math]::Max(1, [int]($gemSize * 0.4))
                $graphics.FillEllipse($highlightBrush,
                    [float]($x - $gemSize/4), [float]($y - $gemSize/4),
                    [float]$highlightSize, [float]$highlightSize)
                $highlightBrush.Dispose()
            }
        }
        
        # Add runes if description mentions them
        if ($descLower -match "rune|glyph|sigil|inscript|etch") {
            $runePen = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(200, 255, 255, 200), 1)
            $random = New-Object System.Random(123)  # Fixed seed
            $runeCount = 3
            for ($i = 0; $i -lt $runeCount; $i++) {
                $angle = $random.NextDouble() * [Math]::PI * 2
                $dist = $random.NextDouble() * ($rimRadius * 0.5)
                $x = $centerX + [Math]::Cos($angle) * $dist
                $y = $centerY + [Math]::Sin($angle) * $dist
                
                # Simple rune-like marks (cross, line, dot pattern)
                $runeType = $i % 3
                if ($runeType -eq 0) {
                    # Small cross
                    $size = 2
                    $graphics.DrawLine($runePen, [float]($x - $size), [float]$y, [float]($x + $size), [float]$y)
                    $graphics.DrawLine($runePen, [float]$x, [float]($y - $size), [float]$x, [float]($y + $size))
                } elseif ($runeType -eq 1) {
                    # Diagonal line
                    $size = 3
                    $graphics.DrawLine($runePen, [float]($x - $size), [float]($y - $size), [float]($x + $size), [float]($y + $size))
                } else {
                    # Dot cluster
                    $graphics.FillEllipse([System.Drawing.Brushes]::Yellow, [float]($x-1), [float]($y-1), 2, 2)
                }
            }
            $runePen.Dispose()
        }
        
        # Add shaft/stick for staff-like items
        if ($descLower -match "staff|wand|rod|stick|shaft") {
            $shaftColor = if ($colors.Count -gt 9) { $colors[9] } else { [System.Drawing.Color]::FromArgb(120, 80, 40) }
            $shaftBrush = New-Object System.Drawing.SolidBrush($shaftColor)
            $shaftWidth = [Math]::Max(2, [int]($width * 0.15))
            $shaftHeight = [int]($height * 0.6)
            $shaftX = [int]($centerX - $shaftWidth / 2)
            $shaftY = [int]($centerY + $rimRadius * 0.3)
            $graphics.FillRectangle($shaftBrush, $shaftX, $shaftY, $shaftWidth, $shaftHeight)
            $shaftBrush.Dispose()
            
            # Add shaft highlight
            $shaftHighlightPen = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(180, 255, 255, 200), 1)
            $graphics.DrawLine($shaftHighlightPen,
                [float]($shaftX + 1), [float]$shaftY,
                [float]($shaftX + 1), [float]($shaftY + $shaftHeight))
            $shaftHighlightPen.Dispose()
        }
        
        # Add energy wisps/trails if mentioned
        if ($descLower -match "energy|wisp|ethereal|trail|emanat") {
            $wispColor = if ($colors.Count -gt 12) { $colors[12] } else { [System.Drawing.Color]::FromArgb(150, 150, 200, 255) }
            $wispPen = New-Object System.Drawing.Pen($wispColor, 1.5)
            $random = New-Object System.Random(456)  # Fixed seed
            $wispCount = 4
            for ($i = 0; $i -lt $wispCount; $i++) {
                $angle = ($i * (360.0 / $wispCount) + 45) * [Math]::PI / 180
                $startDist = $rimRadius * 0.9
                $endDist = $rimRadius * 1.3
                $x1 = $centerX + [Math]::Cos($angle) * $startDist
                $y1 = $centerY + [Math]::Sin($angle) * $startDist
                $x2 = $centerX + [Math]::Cos($angle) * $endDist
                $y2 = $centerY + [Math]::Sin($angle) * $endDist
                
                # Draw wisp trail
                if ($x2 -ge 0 -and $x2 -lt $width -and $y2 -ge 0 -and $y2 -lt $height) {
                    $graphics.DrawLine($wispPen, [float]$x1, [float]$y1, [float]$x2, [float]$y2)
                }
            }
            $wispPen.Dispose()
        }
        
        # Scale down to final Starbound-required dimensions if needed
        # - ItemSprite: 16x16 (Starbound requirement)
        # - MechSprite: 48x48 (max for mech part icons)
        # - Icon: 64x64 (UI icon limit, no scaling needed)
        if (($SpriteType -eq "ItemSprite" -and ($width -ne 16 -or $height -ne 16)) -or
            ($SpriteType -eq "MechSprite" -and ($width -ne 48 -or $height -ne 48))) {
            Write-Host "  Scaling down from ${width}x${height} to ${finalWidth}x${finalHeight} for Starbound compatibility..." -ForegroundColor Gray
            $finalBitmap = New-Object System.Drawing.Bitmap($finalWidth, $finalHeight)
            $finalGraphics = [System.Drawing.Graphics]::FromImage($finalBitmap)
            $finalGraphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
            $finalGraphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
            $finalGraphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
            $finalGraphics.CompositingQuality = [System.Drawing.Drawing2D.CompositingQuality]::HighQuality
            $finalGraphics.DrawImage($bitmap, 0, 0, $finalWidth, $finalHeight)
            $finalGraphics.Dispose()
            $bitmap.Dispose()
            $bitmap = $finalBitmap
            Write-Host "  ✓ Scaled to ${finalWidth}x${finalHeight}" -ForegroundColor Green
        }
        
        # Save sprite as 32-bit RGBA PNG (Starbound requirement)
        # Ensure the bitmap is in 32-bit ARGB format
        if ($bitmap.PixelFormat -ne [System.Drawing.Imaging.PixelFormat]::Format32bppArgb) {
            $newBitmap = New-Object System.Drawing.Bitmap($bitmap.Width, $bitmap.Height, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
            $newGraphics = [System.Drawing.Graphics]::FromImage($newBitmap)
            $newGraphics.DrawImage($bitmap, 0, 0)
            $newGraphics.Dispose()
            $bitmap.Dispose()
            $bitmap = $newBitmap
        }
        
        # Ensure sprite directory exists before saving
        $spriteDirParent = Split-Path -Parent $spritePath
        if (-not (Test-Path $spriteDirParent)) {
            try {
                New-Item -ItemType Directory -Path $spriteDirParent -Force | Out-Null
                Write-Host "  Created sprite directory: $spriteDirParent" -ForegroundColor Gray
            } catch {
                Write-Host "  [ERROR] Failed to create sprite directory '$spriteDirParent': $_" -ForegroundColor Red
                $graphics.Dispose()
                $bitmap.Dispose()
                return $false
            }
        }
        
        # Save with PNG encoder settings for uncompressed 32-bit RGBA
        try {
            $pngCodec = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object { $_.MimeType -eq "image/png" }
            if ($null -eq $pngCodec) {
                throw "PNG codec not found"
            }
            $encoderParams = New-Object System.Drawing.Imaging.EncoderParameters(1)
            # PNG compression: 0 = no compression (uncompressed), 9 = maximum compression
            # Use 0 for uncompressed PNG (Starbound requirement)
            $encoderParams.Param[0] = New-Object System.Drawing.Imaging.EncoderParameter([System.Drawing.Imaging.Encoder]::Compression, [long]0)
            $bitmap.Save($spritePath, $pngCodec, $encoderParams)
            $encoderParams.Dispose()
            
            # Verify file was actually saved
            if (-not (Test-Path $spritePath)) {
                throw "File was not created at: $spritePath"
            }
            
            $fileInfo = Get-Item $spritePath
            if ($fileInfo.Length -eq 0) {
                throw "File was created but is empty (0 bytes)"
            }
            
            Write-Host "✓ Sprite saved: $spritePath ($([math]::Round($fileInfo.Length/1KB, 2)) KB)" -ForegroundColor Green
        } catch {
            Write-Host "  [ERROR] Failed to save sprite to '$spritePath': $_" -ForegroundColor Red
            Write-Host "    Exception: $($_.Exception.Message)" -ForegroundColor Gray
            return $false
        } finally {
            # Cleanup resources
            if ($null -ne $graphics) {
                try { $graphics.Dispose() } catch { }
            }
            if ($null -ne $bitmap) {
                try { $bitmap.Dispose() } catch { }
            }
        }
        
        # Validate sprite quality (ensure it's not just a colored box)
        $isValid = Test-SpriteQuality -ImagePath $spritePath -MinUniqueColors 15 -MinStdDev 0.15
        if (-not $isValid) {
            Write-Host "  [WARNING] Generated sprite may be low quality (colored box detected)" -ForegroundColor Yellow
            Write-Host "    This sprite will be marked for regeneration" -ForegroundColor Gray
        }
    }
    
    # Create .frames file for Starbound (correct format for single sprites)
    # For single sprites, frameGrid.size is the sprite size, dimensions is [1, 1]
    $framesContent = @{
        frameGrid = @{
            size = @($outW, $outH)  # Frame size matches the delivered PNG size for single sprites
            dimensions = @(1, 1)  # Single frame, 1x1 grid
        }
        aliases = @{
            default = @(0)  # Single frame at index 0
        }
    }
    
    # Validate spriteDir and AssetName before Join-Path
    if ([string]::IsNullOrWhiteSpace($spriteDir)) {
        Write-Host "  [FAIL] spriteDir is null, cannot create frames path" -ForegroundColor Red
        return $false
    }
    if ([string]::IsNullOrWhiteSpace($AssetName)) {
        Write-Host "  [FAIL] AssetName is null, cannot create frames path" -ForegroundColor Red
        return $false
    }
    
    $framesPath = Join-Path $spriteDir "$AssetName.frames"
    
    # Validate framesPath is not null
    if ([string]::IsNullOrWhiteSpace($framesPath)) {
        Write-Host "  [FAIL] framesPath is null (spriteDir: '$spriteDir', AssetName: '$AssetName')" -ForegroundColor Red
        return $false
    }
    
    $framesContent | ConvertTo-Json -Depth 10 | Set-Content -Path $framesPath -Encoding UTF8
    
    Write-Host "✓ Frames file created: $framesPath" -ForegroundColor Green
}

# Function to generate animation spritesheets
# Note: Spritesheets can be large (multiple frames), but each individual frame must respect size limits:
# - ItemSprite: 16x16 per frame (Starbound requirement for item animations)
# - MechSprite: 48x48 per frame (max for mech part animations)
# - Sprite/Projectile: 48x48 per frame (object/projectile animations)
# - Particle: 32x32 per frame (particle effect animations)
# - Icon/Other: 64x64 per frame (UI icon animations)
# Frames are generated at higher resolution (64x64 or 32x32 for particles) for detail, then scaled down to final size before being placed in the spritesheet.
# Must be defined before it's called in the switch statement below
function Generate-AnimationSprite {
    param(
        [string]$AssetName,
        [string]$Description,
        [hashtable]$Parameters,
        [string]$OutputDir,
        [string]$SpriteType = ""  # Optional: "ItemSprite", "MechSprite", "Icon" - determines final frame size
    )
    
    Write-Host "Generating Animation Spritesheet: $AssetName" -ForegroundColor Cyan
    
    # Determine sprite type from Parameters if not provided
    if ([string]::IsNullOrWhiteSpace($SpriteType) -and $Parameters.SpriteType) {
        $SpriteType = $Parameters.SpriteType
    }
    
    # Get parameters and validate them
    # Generate frames at higher resolution for detail, then scale to final size per sprite type
    # - ItemSprite: Generate at 64x64, scale to 16x16 per frame
    # - MechSprite: Generate at 64x64, scale to 48x48 per frame
    # - Sprite/Projectile: Generate at 64x64, scale to 48x48 per frame
    # - Particle: Generate at 32x32, keep at 32x32 per frame
    # - Icon/Other: Generate at 64x64, keep at 64x64 per frame
    $generateFrameWidth = if ($Parameters.FrameWidth) { [int]$Parameters.FrameWidth } else { 
        if ($SpriteType -eq "Particle") { 32 } else { 64 }
    }
    $generateFrameHeight = if ($Parameters.FrameHeight) { [int]$Parameters.FrameHeight } else { 
        if ($SpriteType -eq "Particle") { 32 } else { 64 }
    }
    
    # Final frame dimensions (Starbound requirements per sprite type)
    $finalFrameWidth = if ($SpriteType -eq "ItemSprite") { 16 }
                       elseif ($SpriteType -eq "MechSprite") { 48 }
                       elseif ($SpriteType -eq "Sprite") { 48 }
                       elseif ($SpriteType -eq "Projectile") { 48 }
                       elseif ($SpriteType -eq "Particle") { 32 }
                       else { $generateFrameWidth }
    $finalFrameHeight = if ($SpriteType -eq "ItemSprite") { 16 }
                        elseif ($SpriteType -eq "MechSprite") { 48 }
                        elseif ($SpriteType -eq "Sprite") { 48 }
                        elseif ($SpriteType -eq "Projectile") { 48 }
                        elseif ($SpriteType -eq "Particle") { 32 }
                        else { $generateFrameHeight }
    
    # Use generation dimensions for creating individual frames
    $frameWidth = $generateFrameWidth
    $frameHeight = $generateFrameHeight
    $frameCount = if ($Parameters.FrameCount) { [int]$Parameters.FrameCount } else { 8 }
    $animationCycle = if ($Parameters.AnimationCycle) { $Parameters.AnimationCycle } else { 0.5 }
    $animationType = if ($Parameters.AnimationType) { $Parameters.AnimationType } else { "SpellCast" }
    
    # Validate frame dimensions
    if ($frameWidth -le 0) {
        Write-Host "  [FAIL] Invalid frameWidth: $frameWidth (must be > 0)" -ForegroundColor Red
        return $false
    }
    if ($frameHeight -le 0) {
        Write-Host "  [FAIL] Invalid frameHeight: $frameHeight (must be > 0)" -ForegroundColor Red
        return $false
    }
    if ($frameCount -le 0) {
        Write-Host "  [FAIL] Invalid frameCount: $frameCount (must be > 0)" -ForegroundColor Red
        return $false
    }
    
    # Create output directory
    # Validate $OutputDir before Join-Path
    $animDir = Join-Path $OutputDir "animations\$AssetName"
    if ([string]::IsNullOrWhiteSpace($animDir)) {
        Write-Host "  [FAIL] animDir is null (OutputDir: '$OutputDir')" -ForegroundColor Red
        return
    }
    if (-not (Test-Path $animDir)) {
        New-Item -ItemType Directory -Path $animDir -Force | Out-Null
    }
    
    # Real art first: Stable Diffusion renders one cell per frame and packs them into a single
    # horizontal strip (frameCount columns x 1 row) at the final Starbound frame size.
    # Throws if SD fails unless procedural output is explicitly allowed ($sdSheetOk = $false).
    $sdSheetPath = Join-Path $animDir "$AssetName.png"
    $motion = switch ($animationType) {
        "SpellCast"        { "spell casting, energy gathering and growing" }
        "DeviceActivation" { "device activating, pulsing power" }
        "StatusEffect"     { "status effect aura, shimmering" }
        default            { "looping effect animation" }
    }
    $sdFrameNotes = @()
    for ($sdf = 0; $sdf -lt $frameCount; $sdf++) {
        $sdProgress = if ($frameCount -gt 1) { $sdf / [double]($frameCount - 1) } else { 0.0 }
        $sdPhase = if ($sdProgress -lt 0.25) { "start of the animation, small and faint" }
                   elseif ($sdProgress -lt 0.5) { "building up, growing stronger" }
                   elseif ($sdProgress -lt 0.75) { "at peak intensity, largest and brightest" }
                   else { "fading out, dissipating" }
        $sdFrameNotes += "frame $($sdf + 1) of ${frameCount}, $motion, $sdPhase"
    }
    Write-Host "Generating animation spritesheet with Stable Diffusion (${frameCount} frames of ${finalFrameWidth}x${finalFrameHeight})..." -ForegroundColor Green
    $sdSheetOk = Write-StarboundArt -AssetType "AnimationSprite" -Name $AssetName -Description $Description `
        -Width ([int]$finalFrameWidth) -Height ([int]$finalFrameHeight) -OutputPath $sdSheetPath `
        -Frames $frameCount -Columns $frameCount -FrameNotes $sdFrameNotes -Palette $Parameters.ColorPalette
    if ($sdSheetOk) {
        Write-Host "✓ Animation spritesheet created (Stable Diffusion): $sdSheetPath" -ForegroundColor Green
    }

    # Legacy fallback only (SD failed and -AllowProcedural / AAMT_SD_STRICT=0):
    # try the C++ backend if available, otherwise draw System.Drawing shapes.
    $cppBackendPath = "F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery\cpp_backend"
    # Use PSScriptRoot instead of MyInvocation.MyCommand.Path (already validated)
    if ([string]::IsNullOrWhiteSpace($PSScriptRoot)) {
        Write-Host "  [FAIL] PSScriptRoot is null, cannot locate bridge script" -ForegroundColor Red
        return $false
    }
    $bridgeScript = Join-Path $PSScriptRoot "StarboundCppBackendBridge.ps1"
    
    # Validate bridgeScript path is not null
    if ([string]::IsNullOrWhiteSpace($bridgeScript)) {
        Write-Host "  [FAIL] Failed to construct bridge script path" -ForegroundColor Red
        Write-Host "    PSScriptRoot: '$PSScriptRoot'" -ForegroundColor Gray
        return $false
    }
    
    if ($sdSheetOk) {
        # Stable Diffusion already wrote the spritesheet; only the .animation/.frames files remain.
    } elseif ((Test-Path $bridgeScript) -and (Test-Path $cppBackendPath)) {
        Write-Host "[FALLBACK] Stable Diffusion unavailable - using C++ backend procedural animation (-AllowProcedural)..." -ForegroundColor Yellow

        $bridgeParams = @{
            BackendPath = $cppBackendPath
            GeneratorType = "Animation"
            Action = "Generate"
            AssetName = $AssetName
            OutputDir = $animDir
            Parameters = @{
                FrameWidth = $frameWidth
                FrameHeight = $frameHeight
                FrameCount = $frameCount
                AnimationCycle = $animationCycle
                Description = $Description
                AnimationType = $animationType
            }
        }
        
        & $bridgeScript @bridgeParams
    } else {
        # PROCEDURAL FALLBACK ONLY (SD failed and -AllowProcedural / AAMT_SD_STRICT=0)
        Write-Host "[FALLBACK] Stable Diffusion unavailable - drawing procedural placeholder animation spritesheet..." -ForegroundColor Yellow
        
        Add-Type -AssemblyName System.Drawing
        
        # Spritesheet dimensions: total width = final frame width * frame count
        # Each frame will be generated at $frameWidth x $frameHeight, then scaled to $finalFrameWidth x $finalFrameHeight
        $totalWidth = $finalFrameWidth * $frameCount
        $totalHeight = $finalFrameHeight
        
        # Validate total dimensions before creating bitmap
        if ($totalWidth -le 0 -or $totalHeight -le 0) {
            Write-Host "  [FAIL] Invalid total bitmap dimensions: width=$totalWidth, height=$totalHeight" -ForegroundColor Red
            Write-Host "    frameWidth: $frameWidth, frameHeight: $frameHeight, frameCount: $frameCount" -ForegroundColor Gray
            return $false
        }
        
        # Ensure dimensions are integers
        $totalWidth = [int]$totalWidth
        $totalHeight = [int]$totalHeight
        
        if ($totalWidth -le 0 -or $totalHeight -le 0) {
            Write-Host "  [FAIL] Invalid total bitmap dimensions after conversion: width=$totalWidth, height=$totalHeight" -ForegroundColor Red
            return $false
        }
        
        $spritePath = Join-Path $animDir "$AssetName.png"
        
        # Validate spritePath
        if ([string]::IsNullOrWhiteSpace($spritePath)) {
            Write-Host "  [FAIL] spritePath is null (animDir: '$animDir', AssetName: '$AssetName')" -ForegroundColor Red
            return $false
        }
        
        # Create bitmap in 32-bit ARGB format (Starbound requirement)
        try {
            $bitmap = New-Object System.Drawing.Bitmap($totalWidth, $totalHeight, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
        } catch {
            Write-Host "  [FAIL] Failed to create animation bitmap: $_" -ForegroundColor Red
            Write-Host "    TotalWidth: $totalWidth, TotalHeight: $totalHeight" -ForegroundColor Gray
            Write-Host "    FrameWidth: $frameWidth, FrameHeight: $frameHeight, FrameCount: $frameCount" -ForegroundColor Gray
            return $false
        }
        $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
        $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
        $graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
        $graphics.CompositingMode = [System.Drawing.Drawing2D.CompositingMode]::SourceOver
        $graphics.CompositingQuality = [System.Drawing.Drawing2D.CompositingQuality]::HighQuality
        
        # Get color palette
        $colors = if ($Parameters.ColorPalette) {
            $Parameters.ColorPalette | ForEach-Object {
                if ($_ -is [array] -and $_.Count -ge 3) {
                    [System.Drawing.Color]::FromArgb($_[0], $_[1], $_[2])
                } else {
                    [System.Drawing.Color]::FromArgb(255, 200, 100)
                }
            }
        } else {
            @(
                [System.Drawing.Color]::FromArgb(255, 200, 100),
                [System.Drawing.Color]::FromArgb(200, 150, 80),
                [System.Drawing.Color]::FromArgb(150, 100, 60)
            )
        }
        
        # Try to use spritesheet packer tool first (Aseprite, Free Texture Packer, etc.)
        $packerScript = Join-Path $PSScriptRoot "StarboundSpritesheetPacker.ps1"
        $usePacker = $false
        $tempFrameDir = $null
        $frameFiles = @()
        
        if (Test-Path $packerScript) {
            # Create temporary directory for individual frames
            $tempFrameDir = Join-Path $env:TEMP "starbound_frames_$(Get-Random)"
            New-Item -ItemType Directory -Path $tempFrameDir -Force | Out-Null
            $usePacker = $true
            Write-Host "  Using spritesheet packer tool for optimized packing..." -ForegroundColor Cyan
        } else {
            Write-Host "  Spritesheet packer not found, using manual packing..." -ForegroundColor Yellow
        }
        
        # Generate animation frames
        # Each frame is generated at full resolution, then scaled down to final size
        $random = New-Object System.Random
        for ($frame = 0; $frame -lt $frameCount; $frame++) {
            $progress = $frame / ($frameCount - 1)  # 0 to 1
            
            # Create individual frame bitmap at generation resolution (32-bit ARGB)
            $frameBitmap = New-Object System.Drawing.Bitmap($frameWidth, $frameHeight, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
            $frameGraphics = [System.Drawing.Graphics]::FromImage($frameBitmap)
            $frameGraphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
            $frameGraphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
            $frameGraphics.CompositingMode = [System.Drawing.Drawing2D.CompositingMode]::SourceOver
            $frameGraphics.CompositingQuality = [System.Drawing.Drawing2D.CompositingQuality]::HighQuality
            
            # Create frame based on animation type
            switch ($animationType) {
                "SpellCast" {
                    # Spell casting - growing energy
                    $size = $frameWidth * (0.3 + $progress * 0.7)
                    $brush = New-Object System.Drawing.SolidBrush($colors[0])
                    $frameGraphics.FillEllipse($brush, ($frameWidth - $size) / 2, ($frameHeight - $size) / 2, $size, $size)
                    
                    # Add glow
                    $glowSize = $size * 1.2
                    $glowBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(128, $colors[0]))
                    $frameGraphics.FillEllipse($glowBrush, ($frameWidth - $glowSize) / 2, ($frameHeight - $glowSize) / 2, $glowSize, $glowSize)
                }
                "DeviceActivation" {
                    # Device activation - pulsing
                    $pulse = [Math]::Sin($progress * [Math]::PI * 2)
                    $size = $frameWidth * (0.5 + $pulse * 0.3)
                    $brush = New-Object System.Drawing.SolidBrush($colors[0])
                    $frameGraphics.FillRectangle($brush, ($frameWidth - $size) / 2, ($frameHeight - $size) / 2, $size, $size)
                    
                    # Add inner glow
                    $innerSize = $size * 0.6
                    $innerBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(200, $colors[1]))
                    $frameGraphics.FillRectangle($innerBrush, ($frameWidth - $innerSize) / 2, ($frameHeight - $innerSize) / 2, $innerSize, $innerSize)
                }
                "StatusEffect" {
                    # Status effect - shimmering
                    $pulse = [Math]::Sin($progress * [Math]::PI * 2)
                    $alpha = [int](128 + $pulse * 127)
                    $brush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb($alpha, $colors[0]))
                    $frameGraphics.FillEllipse($brush, 2, 2, $frameWidth - 4, $frameHeight - 4)
                }
                default {
                    # Default - simple animation
                    $size = $frameWidth * (0.4 + $progress * 0.6)
                    $brush = New-Object System.Drawing.SolidBrush($colors[0])
                    $frameGraphics.FillEllipse($brush, ($frameWidth - $size) / 2, ($frameHeight - $size) / 2, $size, $size)
                }
            }
            
            # Scale frame down to final size if needed (maintain 32-bit ARGB format)
            $scaledFrame = $frameBitmap
            if ($frameWidth -ne $finalFrameWidth -or $frameHeight -ne $finalFrameHeight) {
                $scaledFrame = New-Object System.Drawing.Bitmap($finalFrameWidth, $finalFrameHeight, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
                $scaledGraphics = [System.Drawing.Graphics]::FromImage($scaledFrame)
                $scaledGraphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
                $scaledGraphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
                $scaledGraphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
                $scaledGraphics.CompositingMode = [System.Drawing.Drawing2D.CompositingMode]::SourceOver
                $scaledGraphics.CompositingQuality = [System.Drawing.Drawing2D.CompositingQuality]::HighQuality
                $scaledGraphics.DrawImage($frameBitmap, 0, 0, $finalFrameWidth, $finalFrameHeight)
                $scaledGraphics.Dispose()
                $frameGraphics.Dispose()
                $frameBitmap.Dispose()
            } else {
                $frameGraphics.Dispose()
            }
            
            # Always draw scaled frame onto spritesheet (for manual packing fallback)
            $x = $frame * $finalFrameWidth
            $graphics.DrawImage($scaledFrame, $x, 0)
            
            # If using packer, also save individual frame to temp directory
            if ($usePacker -and $null -ne $tempFrameDir) {
                $framePath = Join-Path $tempFrameDir "frame_$frame.png"
                $pngCodec = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object { $_.MimeType -eq "image/png" }
                $encoderParams = New-Object System.Drawing.Imaging.EncoderParameters(1)
                $encoderParams.Param[0] = New-Object System.Drawing.Imaging.EncoderParameter([System.Drawing.Imaging.Encoder]::Compression, [long]0)
                $scaledFrame.Save($framePath, $pngCodec, $encoderParams)
                $encoderParams.Dispose()
                $frameFiles += $framePath
            }
            
            $scaledFrame.Dispose()
        }
        
        # Use packer tool if available, otherwise use manual packing
        $packerSuccess = $false
        if ($usePacker -and $frameFiles.Count -gt 0) {
            try {
                Write-Host "  Packing $($frameFiles.Count) frames with spritesheet packer..." -ForegroundColor Gray
                
                $framesPath = Join-Path $animDir "$AssetName.frames"
                
                $packerResult = & $packerScript `
                    -FrameFiles $frameFiles `
                    -OutputSpritesheet $spritePath `
                    -OutputFrames $framesPath `
                    -FrameWidth $finalFrameWidth `
                    -FrameHeight $finalFrameHeight `
                    -Tool "Auto" `
                    -PowerOfTwo `
                    -Padding 2
                
                if ($packerResult -and (Test-Path $spritePath) -and (Test-Path $framesPath)) {
                    Write-Host "  ✓ Spritesheet packed successfully with tool" -ForegroundColor Green
                    $packerSuccess = $true
                } else {
                    Write-Host "  [WARN] Packer tool failed, falling back to manual packing..." -ForegroundColor Yellow
                    $packerSuccess = $false
                }
            } catch {
                Write-Host "  [WARN] Packer tool error: $_, falling back to manual packing..." -ForegroundColor Yellow
                $packerSuccess = $false
            }
            
            # Cleanup temp directory
            if ($null -ne $tempFrameDir -and (Test-Path $tempFrameDir)) {
                Remove-Item -Path $tempFrameDir -Recurse -Force -ErrorAction SilentlyContinue
            }
            
            # If packer failed, fall through to manual packing (frames already drawn to spritesheet)
            if (-not $packerSuccess) {
                $usePacker = $false
            }
        }
        
        # Manual packing fallback (if packer not used or failed)
        if (-not $usePacker) {
            # Save spritesheet as 32-bit RGBA PNG (Starbound requirement)
            # Ensure the bitmap is in 32-bit ARGB format
            if ($bitmap.PixelFormat -ne [System.Drawing.Imaging.PixelFormat]::Format32bppArgb) {
                $newBitmap = New-Object System.Drawing.Bitmap($bitmap.Width, $bitmap.Height, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
                $newGraphics = [System.Drawing.Graphics]::FromImage($newBitmap)
                $newGraphics.DrawImage($bitmap, 0, 0)
                $newGraphics.Dispose()
                $bitmap.Dispose()
                $bitmap = $newBitmap
            }
            
            # Save with PNG encoder settings for uncompressed 32-bit RGBA
            $pngCodec = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object { $_.MimeType -eq "image/png" }
            $encoderParams = New-Object System.Drawing.Imaging.EncoderParameters(1)
            # PNG compression: 0 = no compression (uncompressed), 9 = maximum compression
            # Use 0 for uncompressed PNG (Starbound requirement)
            $encoderParams.Param[0] = New-Object System.Drawing.Imaging.EncoderParameter([System.Drawing.Imaging.Encoder]::Compression, [long]0)
            $bitmap.Save($spritePath, $pngCodec, $encoderParams)
            $encoderParams.Dispose()
            $graphics.Dispose()
            $bitmap.Dispose()
        } else {
            # Cleanup graphics objects if packer was used
            $graphics.Dispose()
            $bitmap.Dispose()
        }
        
        # Validate spritesheet quality
        if (Test-Path $spritePath) {
            $isValid = Test-SpriteQuality -ImagePath $spritePath -MinUniqueColors 20 -MinStdDev 0.15
            if (-not $isValid) {
                Write-Host "  [WARNING] Generated spritesheet may be low quality (colored boxes detected)" -ForegroundColor Yellow
                Write-Host "    This spritesheet will be marked for regeneration" -ForegroundColor Gray
            }
            
            Write-Host "✓ Animation spritesheet created: $spritePath" -ForegroundColor Green
        } else {
            Write-Host "  [FAIL] Spritesheet file not created: $spritePath" -ForegroundColor Red
            return $false
        }
    }
    
    # Create .animation file
    $animationFile = [ordered]@{
        frames = "$AssetName.png"
        variants = 1
        frameNumber = $frameCount
        animationCycle = $animationCycle
        offset = @(0, 0)
    }
    
    $animationPath = Join-Path $animDir "$AssetName.animation"
    $animationJson = $animationFile | ConvertTo-Json -Depth 5
    # Fix JSON formatting - replace colon-space with colon-space (PowerShell doesn't support lookbehind)
    $animationJson = $animationJson -replace '":\s+', '": '
    $animationJson | Set-Content -Path $animationPath -Encoding UTF8 -NoNewline
    
    Write-Host "✓ Animation file created: $animationPath" -ForegroundColor Green
    
    # Create .frames file with correct frame sizes (use final frame dimensions, not generation dimensions)
    # Only create if packer tool didn't already create it
    $framesPath = Join-Path $animDir "$AssetName.frames"
    
    if (-not (Test-Path $framesPath)) {
        $framesContent = @{
            frameGrid = @{
                size = @($finalFrameWidth, $finalFrameHeight)  # Use final frame size, not generation size
                dimensions = @($frameCount, 1)
            }
            aliases = @{
                default = @(0..($frameCount - 1))
            }
        }
        
        # Validate framesPath is not null
        if ([string]::IsNullOrWhiteSpace($framesPath)) {
            Write-Host "  [FAIL] framesPath is null (animDir: '$animDir', AssetName: '$AssetName')" -ForegroundColor Red
            return
        }
        
        $framesContent | ConvertTo-Json -Depth 10 | Set-Content -Path $framesPath -Encoding UTF8
        
        Write-Host "✓ Frames file created: $framesPath" -ForegroundColor Green
    } else {
        Write-Host "✓ Frames file already created by packer tool: $framesPath" -ForegroundColor Green
    }
}

# The C++ backend only draws procedural art, so it is honoured only when procedural output is
# explicitly allowed; otherwise the request is served by the Stable Diffusion path below.
if ($UseCppBackend -and -not $script:ProceduralAllowed) {
    Write-Host "  [WARN] -UseCppBackend ignored: the C++ backend draws procedural art. Using Stable Diffusion generators (pass -AllowProcedural to force it)." -ForegroundColor Yellow
}
if ($UseCppBackend -and $script:ProceduralAllowed) {
    Write-Host "Using C++ Backend (procedural, explicitly allowed)" -ForegroundColor Yellow
    
    $bridgeScript = Join-Path $PSScriptRoot "StarboundCppBackendBridge.ps1"
    if (Test-Path $bridgeScript) {
        # Ensure Description and UseOllama are always passed when Description is available
        $enhancedParams = $Parameters.Clone()
        if ($Description -and $Description.Trim().Length -gt 0) {
            $enhancedParams['Description'] = $Description
            $enhancedParams['UseOllama'] = $true
            Write-Host "  → Ollama will be used for high-quality asset generation" -ForegroundColor Green
            Write-Host "    Description: $($Description.Substring(0, [Math]::Min(80, $Description.Length)))..." -ForegroundColor Gray
        } elseif (-not $enhancedParams.ContainsKey('Description')) {
            $enhancedParams['Description'] = ""
            $enhancedParams['UseOllama'] = $false
        }
        
        $bridgeParams = @{
            BackendPath = $CppBackendPath
            GeneratorType = switch ($AssetType) {
                "Particle" { "Particle" }
                "Texture" { "Texture" }
                "Animation" { "Animation" }
                "AnimationSprite" { "Animation" }
                "Icon" { "Icon" }
                "Spell" { "Spell" }
                "Sprite" { "Image" }
                "ItemSprite" { "Image" }
                "MechSprite" { "Image" }
                default { "Image" }
            }
            Action = "Generate"
            AssetName = $AssetName
            OutputDir = $OutputDir
            Parameters = $enhancedParams
        }
        
        & $bridgeScript @bridgeParams
    } else {
        Write-Host "Error: Bridge script not found" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "Using PowerShell Generators" -ForegroundColor Green
    
    # Use existing PowerShell generators and convert to Starbound format
    switch ($AssetType) {
        "Particle" {
            # Use specialized StarboundParticleGenerator
            $particleScript = Join-Path $PSScriptRoot "StarboundParticleGenerator.ps1"
            if (Test-Path $particleScript) {
                # Determine preset from description or parameters
                $preset = "None"
                
                # Check if Parameters.Preset exists and extract it properly
                if ($Parameters.Preset) {
                    if ($Parameters.Preset -is [string]) {
                        $preset = $Parameters.Preset
                    } elseif ($Parameters.Preset -is [hashtable]) {
                        # If it's a hashtable, try to extract a string value
                        if ($Parameters.Preset.Name) {
                            $preset = $Parameters.Preset.Name
                        } elseif ($Parameters.Preset.Value) {
                            $preset = $Parameters.Preset.Value
                        } else {
                            # Convert hashtable to string representation of first value
                            $presetValues = $Parameters.Preset.Values | Where-Object { $_ -is [string] }
                            if ($presetValues) {
                                $preset = $presetValues[0]
                            }
                        }
                    }
                }
                
                # Do NOT auto-detect presets from description - use description directly
                # Presets should only come from explicit Parameters.Preset
                
                $particleParams = @{
                    ParticleName = $AssetName
                    Description = $Description
                    OutputDir = $OutputDir
                    UseOllama = $true  # Enable intelligent asset generation
                }
                
                # Only add Preset if it's a valid string value
                if ($preset -ne "None" -and $preset -is [string] -and $preset.Trim() -ne "") {
                    $particleParams['Preset'] = $preset
                }
                
                if ($Parameters.Color) {
                    $particleParams['Color'] = $Parameters.Color
                }
                if ($Parameters.Size) {
                    $particleParams['Size'] = $Parameters.Size
                }
                if ($Parameters.TimeToLive) {
                    $particleParams['TimeToLive'] = $Parameters.TimeToLive
                }
                if ($Parameters.InitialVelocity) {
                    $particleParams['InitialVelocity'] = $Parameters.InitialVelocity
                }
                if ($Parameters.FinalVelocity) {
                    $particleParams['FinalVelocity'] = $Parameters.FinalVelocity
                }
                
                & $particleScript @particleParams
            } else {
                Write-Host "StarboundParticleGenerator not found, using fallback" -ForegroundColor Yellow
            }
        }
        
        "Texture" {
            # Real texture art from Stable Diffusion (opaque, full-frame, not pixel-quantized).
            # Throws when SD fails unless -AllowProcedural / AAMT_SD_STRICT=0, in which case the
            # legacy Transcendence AssetMakerAI procedural texture path below runs instead.
            $texSize = if ($Parameters.Size) { [int]$Parameters.Size } else { 256 }
            $texExportDir = Join-Path $OutputDir "StarboundExport"
            if (-not (Test-Path $texExportDir)) {
                New-Item -ItemType Directory -Path $texExportDir -Force | Out-Null
            }
            $texPath = Join-Path $texExportDir "$AssetName.png"
            Write-Host "Generating texture '$AssetName' with Stable Diffusion (${texSize}x${texSize})..." -ForegroundColor Green
            $texOk = Write-StarboundArt -AssetType "Texture" -Name $AssetName -Description $Description `
                -Width $texSize -Height $texSize -OutputPath $texPath -Palette $Parameters.ColorPalette `
                -Transparent $false -Pixel $false -SdKind "texture"
            if ($texOk) {
                $texFrames = @{
                    frameGrid = @{
                        size = @($texSize, $texSize)
                        dimensions = @(1, 1)
                    }
                    aliases = @{
                        default = @(0)
                    }
                }
                $texFrames | ConvertTo-Json -Depth 10 | Set-Content -Path (Join-Path $texExportDir "$AssetName.frames") -Encoding UTF8
                Write-Host "✓ Starbound format exported (Stable Diffusion): $texPath" -ForegroundColor Green
            } else {
            # PROCEDURAL FALLBACK ONLY: Transcendence AssetMakerAI procedural texture
            $toolsDir = Split-Path -Parent $PSScriptRoot
            $textureScript = Join-Path $toolsDir "Transcendence\AssetMakerAI.ps1"
            if (Test-Path $textureScript) {
                # Validate $OutputDir before Join-Path
                $watchDir = Join-Path $OutputDir "watch"
                if ([string]::IsNullOrWhiteSpace($watchDir)) {
                    Write-Host "  [FAIL] watchDir is null (OutputDir: '$OutputDir')" -ForegroundColor Red
                    Write-Host "  Skipping texture generation" -ForegroundColor Yellow
                } else {
                    if (-not (Test-Path $watchDir)) {
                        New-Item -ItemType Directory -Path $watchDir -Force | Out-Null
                    }
                
                & $textureScript `
                    -Action GenerateTexture `
                    -InputData $Description `
                    -TextureMethod Procedural `
                    -TextureSize $(if ($Parameters.Size) { $Parameters.Size } else { 256 }) `
                    -OutputPath $watchDir `
                    -ErrorAction Continue
                
                # Convert to Starbound format
                Start-Sleep -Seconds 3
                $generatedFiles = Get-ChildItem -LiteralPath $watchDir -Filter "*.png" -File -ErrorAction SilentlyContinue
                
                if ($generatedFiles.Count -gt 0) {
                    # Validate $OutputDir before Join-Path
                    $starboundDir = Join-Path $OutputDir "StarboundExport"
                    if ([string]::IsNullOrWhiteSpace($starboundDir)) {
                        Write-Host "  [FAIL] starboundDir is null (OutputDir: '$OutputDir')" -ForegroundColor Red
                        Write-Host "  Skipping texture export" -ForegroundColor Yellow
                    } else {
                        if (-not (Test-Path $starboundDir)) {
                            New-Item -ItemType Directory -Path $starboundDir -Force | Out-Null
                        }
                        
                        foreach ($file in $generatedFiles) {
                            Copy-Item -Path $file.FullName -Destination (Join-Path $starboundDir $file.Name) -Force
                        }
                        
                        # Create .frames file for Starbound
                        $framesContent = @{
                            frameGrid = @{
                                size = @($(if ($Parameters.Size) { $Parameters.Size } else { 256 }), $(if ($Parameters.Size) { $Parameters.Size } else { 256 }))
                                dimensions = @(1, 1)
                            }
                            aliases = @{
                                default = @(0)
                            }
                        }
                        
                        # Validate starboundDir and AssetName before Join-Path
                        if ([string]::IsNullOrWhiteSpace($starboundDir)) {
                            Write-Host "  [FAIL] starboundDir is null, cannot create frames path" -ForegroundColor Red
                            continue
                        }
                        if ([string]::IsNullOrWhiteSpace($AssetName)) {
                            Write-Host "  [FAIL] AssetName is null, cannot create frames path" -ForegroundColor Red
                            continue
                        }
                        
                        $framesPath = Join-Path $starboundDir "$AssetName.frames"
                        
                        # Validate framesPath is not null
                        if ([string]::IsNullOrWhiteSpace($framesPath)) {
                            Write-Host "  [FAIL] framesPath is null (starboundDir: '$starboundDir', AssetName: '$AssetName')" -ForegroundColor Red
                            continue
                        }
                        
                        $framesContent | ConvertTo-Json -Depth 10 | Set-Content -Path $framesPath -Encoding UTF8
                        
                        Write-Host "✓ Starbound format exported" -ForegroundColor Green
                    }
                }
                }
            } else {
                Write-Host "Texture script not found" -ForegroundColor Yellow
            }
            }
        }
        
        "Animation" {
            # Use specialized StarboundAnimationGenerator with Ollama
            $animationScript = Join-Path $PSScriptRoot "StarboundAnimationGenerator.ps1"
            if (Test-Path $animationScript) {
                # Do NOT auto-detect presets from description - use description directly
                # Presets should only come from explicit Parameters.Preset
                $preset = "None"
                
                $animParams = @{
                    AnimationName = $AssetName
                    Description = $Description
                    OutputDir = $OutputDir
                    GeneratePlaceholderImage = $false
                    UseOllama = $true  # Enable intelligent asset generation
                }
                
                if ($preset -ne "None") {
                    $animParams['Preset'] = $preset
                } else {
                    # Use parameters if no preset
                    if ($Parameters.FrameCount) { $animParams['FrameCount'] = $Parameters.FrameCount }
                    if ($Parameters.FrameSize) { $animParams['FrameSize'] = $Parameters.FrameSize }
                    if ($Parameters.AnimationCycle) { $animParams['AnimationCycle'] = $Parameters.AnimationCycle }
                }
                if ($AllowProcedural) { $animParams['AllowProcedural'] = $true }

                & $animationScript @animParams
            } else {
                Write-Host "StarboundAnimationGenerator not found" -ForegroundColor Yellow
            }
        }
        
        "Icon" {
            # Use sprite generator for icons (icons are just small sprites)
            # Validate OutputDir is not empty
            if ([string]::IsNullOrWhiteSpace($OutputDir)) {
                Write-Host "  [FAIL] Cannot generate Icon '$AssetName': OutputDir is empty" -ForegroundColor Red
                break
            }
            
            $iconSize = if ($Parameters.Size) { $Parameters.Size } else { 64 }
            $iconParams = @{
                Width = $iconSize
                Height = $iconSize
                FrameCount = 1
                ColorPalette = if ($Parameters.ColorPalette) { $Parameters.ColorPalette } else { $null }
                Style = if ($Parameters.Style) { $Parameters.Style } else { "Icon" }
                Shape = if ($Parameters.Shape) { $Parameters.Shape } else { "Square" }
            }
            
            # Merge any additional parameters
            foreach ($key in $Parameters.Keys) {
                if (-not $iconParams.ContainsKey($key)) {
                    $iconParams[$key] = $Parameters[$key]
                }
            }
            
            # Create icon directory structure
            # Validate $OutputDir before Join-Path
            $iconDir = Join-Path $OutputDir "interface\icons"
            if ([string]::IsNullOrWhiteSpace($iconDir)) {
                Write-Host "  [FAIL] iconDir is null (OutputDir: '$OutputDir')" -ForegroundColor Red
                Write-Host "  Skipping icon generation" -ForegroundColor Yellow
            } else {
                if (-not (Test-Path $iconDir)) {
                    New-Item -ItemType Directory -Path $iconDir -Force | Out-Null
                }
            
                Generate-AssetSprite -AssetName $AssetName -Description $Description -Parameters $iconParams -OutputDir $iconDir -SpriteType "Icon"
            }
        }
        
        "Sprite" {
            # Generic sprites (objects, furniture, etc.) - 48x48 limit
            Generate-AssetSprite -AssetName $AssetName -Description $Description -Parameters $Parameters -OutputDir $OutputDir -SpriteType "Sprite"
        }
        
        "ItemSprite" {
            # Item icons - 16x16 limit (Starbound requirement)
            Generate-AssetSprite -AssetName $AssetName -Description $Description -Parameters $Parameters -OutputDir $OutputDir -SpriteType "ItemSprite"
        }
        
        "MechSprite" {
            # Mech part icons - 48x48 limit
            Generate-AssetSprite -AssetName $AssetName -Description $Description -Parameters $Parameters -OutputDir $OutputDir -SpriteType "MechSprite"
        }
        
        "Projectile" {
            # Projectile sprites - 48x48 limit
            Generate-AssetSprite -AssetName $AssetName -Description $Description -Parameters $Parameters -OutputDir $OutputDir -SpriteType "Projectile"
        }
        
        "Particle" {
            # Particle effects - 32x32 (typically small)
            Generate-AssetSprite -AssetName $AssetName -Description $Description -Parameters $Parameters -OutputDir $OutputDir -SpriteType "Particle"
        }
        
        "Sound" {
            # Use StarboundSoundGenerator for sound effects
            $soundScript = Join-Path $PSScriptRoot "StarboundSoundGenerator.ps1"
            if (Test-Path $soundScript) {
                # Do NOT auto-detect sound type from description - use description directly
                # Sound type should only come from explicit Parameters.SoundType
                $soundType = if ($Parameters.SoundType) { $Parameters.SoundType } else { "Custom" }
                
                $soundParams = @{
                    SoundName = $AssetName
                    SoundType = $soundType
                    Description = $Description
                    OutputDir = $OutputDir
                    UsePython = $true
                }
                
                # Handle Preset parameter - extract properly if it's a hashtable
                if ($Parameters.Preset) {
                    $presetValue = $Parameters.Preset
                    if ($presetValue -is [hashtable]) {
                        # If it's a hashtable, try to extract a string value
                        if ($presetValue.Name) {
                            $presetValue = $presetValue.Name
                        } elseif ($presetValue.Value) {
                            $presetValue = $presetValue.Value
                        } else {
                            # Convert hashtable to string representation of first value
                            $presetValues = $presetValue.Values | Where-Object { $_ -is [string] }
                            if ($presetValues) {
                                $presetValue = $presetValues[0]
                            }
                        }
                    }
                    # Only add Preset if it's a valid string value
                    if ($presetValue -is [string] -and $presetValue.Trim() -ne "") {
                        $soundParams['Preset'] = $presetValue
                    }
                }
                
                if ($Parameters.Duration) { $soundParams['Duration'] = $Parameters.Duration }
                if ($Parameters.Frequency) { $soundParams['Frequency'] = $Parameters.Frequency }
                if ($Parameters.Volume) { $soundParams['Volume'] = $Parameters.Volume }
                if ($Parameters.Format) { $soundParams['Format'] = $Parameters.Format }
                
                & $soundScript @soundParams
            } else {
                Write-Host "StarboundSoundGenerator not found, using fallback" -ForegroundColor Yellow
            }
        }
        
        "AnimationSprite" {
            # Use StarboundAnimationGenerator for animation spritesheets
            $animationScript = Join-Path $PSScriptRoot "StarboundAnimationGenerator.ps1"
            if (Test-Path $animationScript) {
                $animParams = @{
                    AnimationName = $AssetName
                    Description = $Description
                    OutputDir = $OutputDir
                    GeneratePlaceholderImage = $false
                    UseOllama = $true  # Enable intelligent asset generation
                }
                
                if ($Parameters.FrameCount) { $animParams['FrameCount'] = $Parameters.FrameCount }
                if ($Parameters.FrameSize) { $animParams['FrameSize'] = $Parameters.FrameSize }
                elseif ($Parameters.FrameWidth -and $Parameters.FrameHeight) {
                    $animParams['FrameSize'] = @($Parameters.FrameWidth, $Parameters.FrameHeight)
                }
                if ($Parameters.AnimationCycle) { $animParams['AnimationCycle'] = $Parameters.AnimationCycle }
                if ($AllowProcedural) { $animParams['AllowProcedural'] = $true }

                & $animationScript @animParams
            } else {
                # Fallback to existing function
                # Determine SpriteType from AssetType context if available
                $spriteType = if ($Parameters.SpriteType) { $Parameters.SpriteType } else { "" }
                Generate-AnimationSprite -AssetName $AssetName -Description $Description -Parameters $Parameters -OutputDir $OutputDir -SpriteType $spriteType
            }
        }
        
        "Ship" {
            # Use StarboundShipGenerator with Ollama
            $shipScript = Join-Path $PSScriptRoot "StarboundShipGenerator.ps1"
            if (Test-Path $shipScript) {
                & $shipScript `
                    -ShipName $AssetName `
                    -Description $Description `
                    -UseOllama:($null -ne $Description) `
                    -OutputDir $OutputDir
            } else {
                Write-Host "StarboundShipGenerator not found" -ForegroundColor Yellow
            }
        }
        
        "Tile" {
            # Use StarboundTileGenerator with Ollama
            $tileScript = Join-Path $PSScriptRoot "StarboundTileGenerator.ps1"
            if (Test-Path $tileScript) {
                $tileParams = @{
                    TileName = $AssetName
                    Description = $Description
                    OutputDir = $OutputDir
                    GeneratePlaceholderImage = $false
                    UseOllama = $true
                }
                
                if ($Parameters.TileSize) { $tileParams['TileSize'] = $Parameters.TileSize }
                if ($Parameters.TileCount) { $tileParams['TileCount'] = $Parameters.TileCount }
                if ($Parameters.Preset) { $tileParams['Preset'] = $Parameters.Preset }
                
                & $tileScript @tileParams
            } else {
                Write-Host "StarboundTileGenerator not found" -ForegroundColor Yellow
            }
        }
        
        "Cursor" {
            # Use StarboundCursorGenerator with Ollama
            $cursorScript = Join-Path $PSScriptRoot "StarboundCursorGenerator.ps1"
            if (Test-Path $cursorScript) {
                $cursorParams = @{
                    CursorName = $AssetName
                    Description = $Description
                    OutputDir = $OutputDir
                    GeneratePlaceholderImage = $false
                    UseOllama = $true
                }
                
                if ($Parameters.Preset) { $cursorParams['Preset'] = $Parameters.Preset }
                if ($Parameters.FrameSize) { $cursorParams['FrameSize'] = $Parameters.FrameSize }
                
                & $cursorScript @cursorParams
            } else {
                Write-Host "StarboundCursorGenerator not found" -ForegroundColor Yellow
            }
        }
        
        "Behavior" {
            # Use StarboundBehaviorGenerator
            $behaviorScript = Join-Path $PSScriptRoot "StarboundBehaviorGenerator.ps1"
            if (Test-Path $behaviorScript) {
                $behaviorParams = @{
                    BehaviorName = $AssetName
                    Description = $Description
                    OutputDir = $OutputDir
                }
                
                if ($Parameters.Preset) { $behaviorParams['Preset'] = $Parameters.Preset }
                if ($Parameters.AggroRange) { $behaviorParams['AggroRange'] = $Parameters.AggroRange }
                if ($Parameters.AttackRange) { $behaviorParams['AttackRange'] = $Parameters.AttackRange }
                
                & $behaviorScript @behaviorParams
            } else {
                Write-Host "StarboundBehaviorGenerator not found" -ForegroundColor Yellow
            }
        }
    }
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Generation Complete" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

