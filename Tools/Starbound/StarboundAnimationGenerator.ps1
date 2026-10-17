#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate animation files for Starbound/OpenStarbound.
    
.DESCRIPTION
    Creates Starbound-compatible .animation and .frames files with support for:
    - Simple frame strip animations
    - Grid-based spritesheets
    - Multiple animation variants

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}
    - Looping animations
    - Automatic frame calculation from images
    
.PARAMETER AnimationName
    Name of the animation (used in file names)
    
.PARAMETER FrameCount
    Number of frames in the animation
    
.PARAMETER FrameSize
    Size of each frame [width, height] in pixels
    
.PARAMETER AnimationCycle
    Duration of one animation cycle in seconds
    
.PARAMETER Variants
    Number of animation variants (rows in spritesheet)
    
.PARAMETER Offset
    Animation offset [x, y] in pixels
    
.PARAMETER Loops
    Number of loops (optional, for limited looping)
    
.PARAMETER ImagePath
    Path to existing spritesheet image (optional - auto-calculates frames)
    
.PARAMETER Preset
    Use a preset: Fire, Ice, Poison, Electric, Smoke, Sparkle, Poof, HitSpark
    
.PARAMETER OutputDir
    Output directory for generated files

.PARAMETER AllowProcedural
    The spritesheet is rendered with the local Stable Diffusion 3.5 server (:1338) via
    StarboundSdArt.psm1. By default the script throws if SD cannot deliver. With this switch
    (or AAMT_SD_STRICT=0) the legacy System.Drawing placeholder sheet may be drawn instead,
    but only after an SD failure.

.PARAMETER GeneratePlaceholderImage
    Legacy switch kept for caller compatibility. A real SD spritesheet is always generated.

.EXAMPLE
    .\StarboundAnimationGenerator.ps1 -AnimationName "myeffect" -FrameCount 8 -FrameSize @(32,32)
    
.EXAMPLE
    .\StarboundAnimationGenerator.ps1 -AnimationName "fireblast" -Preset Fire
    
.EXAMPLE
    .\StarboundAnimationGenerator.ps1 -AnimationName "custom" -ImagePath "mysheet.png" -FrameCount 6
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$AnimationName,
    
    [Parameter(Mandatory=$false)]
    [int]$FrameCount = 8,
    
    [Parameter(Mandatory=$false)]
    [int[]]$FrameSize = @(32, 32),
    
    [Parameter(Mandatory=$false)]
    [float]$AnimationCycle = 0.5,
    
    [Parameter(Mandatory=$false)]
    [int]$Variants = 1,
    
    [Parameter(Mandatory=$false)]
    [int[]]$Offset = @(0, 0),
    
    [Parameter(Mandatory=$false)]
    [float]$Loops = 0,
    
    [Parameter(Mandatory=$false)]
    [string]$ImagePath = "",
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("Fire", "Ice", "Poison", "Electric", "Smoke", "Sparkle", "Poof", "HitSpark", "Gas", "Charge", "None")]
    [string]$Preset = "None",
    
    [Parameter(Mandatory=$false)]
    [string]$OutputDir = "StarboundAnimations",
    
    [Parameter(Mandatory=$false)]
    [switch]$GeneratePlaceholderImage,   # legacy; ignored (real SD art is always generated)

    [Parameter(Mandatory=$false)]
    [switch]$AllowProcedural,            # permit the legacy System.Drawing sheet after an SD failure

    [Parameter(Mandatory=$false)]
    [int[]]$PlaceholderColor = @(255, 255, 255, 128),   # colour hint (prompt) / fallback fill colour
    
    [Parameter(Mandatory=$false)]
    [string]$Description = "",
    
    [Parameter(Mandatory=$false)]
    [switch]$UseOllama,
    
    [Parameter(Mandatory=$false)]
    [string]$OllamaModel = "codellama:7b-instruct",
    
    [Parameter(Mandatory=$false)]
    [string]$PlanningModel = "",  # Defaults to OllamaModel if not specified
    
    [Parameter(Mandatory=$false)]
    [string]$VisualModel = "wizardlm-uncensored"
)

$ErrorActionPreference = "Stop"
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

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

# Setup logging
$logDir = Join-Path $PSScriptRoot "Logs"
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

$logFile = Join-Path $logDir "StarboundAnimation_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$timestamp] [$Level] $Message"
    $color = switch ($Level) {
        "ERROR" { "Red" }
        "WARN" { "Yellow" }
        "SUCCESS" { "Green" }
        default { "Cyan" }
    }
    Write-Host $logEntry -ForegroundColor $color
    Add-Content -Path $logFile -Value $logEntry -ErrorAction SilentlyContinue
}

# ---------------------------------------------------------------------------
# Stable Diffusion art: real pixels from the local SD3.5 server (:1338).
# There is no procedural placeholder unless -AllowProcedural / AAMT_SD_STRICT=0.
# ---------------------------------------------------------------------------
Import-Module (Join-Path $PSScriptRoot "StarboundSdArt.psm1") -Force
$script:ProceduralAllowed = $AllowProcedural.IsPresent -or ($env:AAMT_SD_STRICT -eq '0')

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
    (single sprite, or a Frames-cell sheet) through New-StarboundSdArt. Returns $true when
    the PNG was written; $false only when SD failed AND procedural output is allowed;
    throws otherwise.
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
        "Animation"       { "animation spritesheet frame of" }
        "AnimationSprite" { "animation spritesheet frame of" }
        "Effect"          { "visual effect sprite of" }
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
    return [bool](New-StarboundSdArt @common)
}

Write-Log "═══════════════════════════════════════════════════════════"
Write-Log "  Starbound Animation Generator"
Write-Log "═══════════════════════════════════════════════════════════"
Write-Log ""
Write-Log "Animation Name: $AnimationName"
Write-Log "Preset: $Preset"
Write-Log "Output Directory: $OutputDir"
Write-Log ""

# Create output directory
$animOutputDir = Join-Path $OutputDir $AnimationName
if (-not (Test-Path $animOutputDir)) {
    New-Item -ItemType Directory -Path $animOutputDir -Force | Out-Null
}

# Preset definitions
$presets = @{
    "Fire" = @{
        FrameCount = 4
        FrameSize = @(32, 32)
        AnimationCycle = 0.4
        Variants = 1
        Loops = 0
        Description = "Burning flame animation"
    }
    "Ice" = @{
        FrameCount = 6
        FrameSize = @(32, 32)
        AnimationCycle = 0.6
        Variants = 1
        Loops = 0
        Description = "Ice crystal shimmer"
    }
    "Poison" = @{
        FrameCount = 8
        FrameSize = @(32, 32)
        AnimationCycle = 0.8
        Variants = 1
        Loops = 0
        Description = "Toxic gas cloud"
    }
    "Electric" = @{
        FrameCount = 4
        FrameSize = @(24, 24)
        AnimationCycle = 0.15
        Variants = 1
        Loops = 0
        Description = "Electric spark"
    }
    "Smoke" = @{
        FrameCount = 8
        FrameSize = @(32, 32)
        AnimationCycle = 0.4
        Variants = 1
        Loops = 0
        Description = "Rising smoke puff"
    }
    "Sparkle" = @{
        FrameCount = 4
        FrameSize = @(16, 16)
        AnimationCycle = 0.6
        Variants = 1
        Loops = 0
        Description = "Magic sparkle effect"
    }
    "Poof" = @{
        FrameCount = 6
        FrameSize = @(48, 48)
        AnimationCycle = 0.3
        Variants = 1
        Loops = 0
        Description = "Explosion poof"
    }
    "HitSpark" = @{
        FrameCount = 4
        FrameSize = @(16, 16)
        AnimationCycle = 0.15
        Variants = 1
        Loops = 0
        Description = "Weapon hit spark"
    }
    "Gas" = @{
        FrameCount = 8
        FrameSize = @(32, 32)
        AnimationCycle = 0.8
        Variants = 1
        Loops = 0
        Description = "Gas cloud animation"
    }
    "Charge" = @{
        FrameCount = 17
        FrameSize = @(48, 48)
        AnimationCycle = 0.4
        Variants = 1
        Loops = 0
        Description = "Charging energy effect"
    }
}

# Apply preset if specified
if ($Preset -ne "None" -and $presets.ContainsKey($Preset)) {
    Write-Log "Applying preset: $Preset" "INFO"
    $presetData = $presets[$Preset]
    
    if ($PSBoundParameters.ContainsKey('FrameCount') -eq $false) { $FrameCount = $presetData.FrameCount }
    if ($PSBoundParameters.ContainsKey('FrameSize') -eq $false) { $FrameSize = $presetData.FrameSize }
    if ($PSBoundParameters.ContainsKey('AnimationCycle') -eq $false) { $AnimationCycle = $presetData.AnimationCycle }
    if ($PSBoundParameters.ContainsKey('Variants') -eq $false) { $Variants = $presetData.Variants }
    if ($PSBoundParameters.ContainsKey('Loops') -eq $false) { $Loops = $presetData.Loops }
    if ([string]::IsNullOrEmpty($Description)) { $Description = $presetData.Description }
}

# If image path provided, try to calculate frames from image dimensions
if (-not [string]::IsNullOrEmpty($ImagePath) -and (Test-Path $ImagePath)) {
    Write-Log "Analyzing image: $ImagePath" "INFO"
    
    try {
        Add-Type -AssemblyName System.Drawing
        $image = [System.Drawing.Image]::FromFile((Resolve-Path $ImagePath).Path)
        $imageWidth = $image.Width
        $imageHeight = $image.Height
        $image.Dispose()
        
        # Calculate frame count if not explicitly set
        if ($PSBoundParameters.ContainsKey('FrameCount') -eq $false) {
            # Assume horizontal strip
            $FrameCount = [Math]::Floor($imageWidth / $FrameSize[0])
            Write-Log "  Auto-detected $FrameCount frames from image" "INFO"
        }
        
        # Calculate variants if not explicitly set
        if ($PSBoundParameters.ContainsKey('Variants') -eq $false) {
            $Variants = [Math]::Floor($imageHeight / $FrameSize[1])
            if ($Variants -lt 1) { $Variants = 1 }
            Write-Log "  Auto-detected $Variants variant(s)" "INFO"
        }
        
        Write-Log "  Image size: ${imageWidth}x${imageHeight}" "INFO"
    }
    catch {
        Write-Log "  Could not analyze image: $_" "WARN"
    }
}

Write-Log ""
Write-Log "Animation Settings:" "INFO"
Write-Log "  Frame Count: $FrameCount" "INFO"
Write-Log "  Frame Size: $($FrameSize[0])x$($FrameSize[1])" "INFO"
Write-Log "  Animation Cycle: ${AnimationCycle}s" "INFO"
Write-Log "  Variants: $Variants" "INFO"
if ($Loops -gt 0) { Write-Log "  Loops: $Loops" "INFO" }
Write-Log ""

# Build .animation file
$animationFile = [ordered]@{
    frames = "$AnimationName.png"
    variants = $Variants
    frameNumber = $FrameCount
    animationCycle = $AnimationCycle
    offset = $Offset
}

# Add loops if specified
if ($Loops -gt 0) {
    $animationFile["loops"] = $Loops
}

# Convert to JSON
$animationJson = $animationFile | ConvertTo-Json -Depth 5
$animationJson = $animationJson -replace '(?<="):\s*', ' : '

# Write .animation file
$animationPath = Join-Path $animOutputDir "$AnimationName.animation"
$animationJson | Out-File -FilePath $animationPath -Encoding UTF8 -NoNewline
Write-Log "Created: $animationPath" "SUCCESS"

# Build .frames file
$framesFile = [ordered]@{
    frameGrid = [ordered]@{
        size = @($FrameSize[0], $FrameSize[1])
        dimensions = @($FrameCount, $Variants)
    }
}

$framesJson = $framesFile | ConvertTo-Json -Depth 5
$framesJson = $framesJson -replace '(?<="):\s*', ' : '

# Write .frames file
$framesPath = Join-Path $animOutputDir "$AnimationName.frames"
$framesJson | Out-File -FilePath $framesPath -Encoding UTF8 -NoNewline
Write-Log "Created: $framesPath" "SUCCESS"

# Generate intelligent visual asset using Ollama if requested
$script:visualDesign = $null
if ($UseOllama -and (-not [string]::IsNullOrEmpty($Description))) {
    Write-Log "Using Ollama to generate intelligent animation spritesheet..." "INFO"
    
    if (Get-Command Invoke-OllamaRequest -ErrorAction SilentlyContinue) {
        # Generate visual design using Ollama
        $visualPrompt = "You are creating an animation spritesheet for a Starbound game mod.
Animation Name: $AnimationName
Description: $Description
Frame Count: $FrameCount
Frame Size: $($FrameSize[0])x$($FrameSize[1]) pixels

Generate a detailed visual design specification in JSON:
{
  'ColorPalette': [[R,G,B], [R,G,B], [R,G,B]] - 3 colors for the animation,
  'VisualStyle': string - description of visual appearance,
  'AnimationPattern': string - how the animation progresses (growing, rotating, pulsing, etc.),
  'FrameVariations': string - how each frame differs from the previous
}

Return ONLY the JSON object."
        
        $modelToUse = if ($VisualModel) { $VisualModel } else { $OllamaModel }
        $visualResponse = Invoke-OllamaRequest -Prompt $visualPrompt -TaskType "visual" -ResponseLength "short" -ModelName $modelToUse
        
        if ($visualResponse) {
            $jsonMatch = $visualResponse | Select-String -Pattern '\{[\s\S]*\}' | Select-Object -First 1
            if ($jsonMatch) {
                try {
                    $script:visualDesign = $jsonMatch.Matches[0].Value | ConvertFrom-Json
                    $PlaceholderColor = if ($script:visualDesign.ColorPalette -and $script:visualDesign.ColorPalette.Count -gt 0) {
                        $firstColor = $script:visualDesign.ColorPalette[0]
                        @($firstColor[0], $firstColor[1], $firstColor[2], 255)
                    } else { $PlaceholderColor }
                    
                    Write-Log "AI visual design: $($script:visualDesign.VisualStyle)" "SUCCESS"
                    Write-Log "  Pattern: $($script:visualDesign.AnimationPattern)" "INFO"
                } catch {
                    Write-Log "Could not parse AI visual design: $_" "WARN"
                }
            }
        }
    }
}

# Always write a real spritesheet PNG rendered by Stable Diffusion (one cell per frame,
# one row per variant). An external -ImagePath replaces it, so SD is skipped in that case.
$sheetPath = Join-Path $animOutputDir "$AnimationName.png"
$haveExternalImage = (-not [string]::IsNullOrEmpty($ImagePath)) -and (Test-Path $ImagePath)
$sdSheetOk = $false
if (-not $haveExternalImage) {
    Write-Log "Generating animation spritesheet with Stable Diffusion..." "INFO"

    # Description + any Ollama visual design feed the prompt.
    $artDescription = $Description
    $artPalette = $null
    $patternHint = ""
    if ($script:visualDesign) {
        if ($script:visualDesign.VisualStyle) { $artDescription = "$artDescription. $($script:visualDesign.VisualStyle)" }
        if ($script:visualDesign.FrameVariations) { $artDescription = "$artDescription. $($script:visualDesign.FrameVariations)" }
        if ($script:visualDesign.AnimationPattern) { $patternHint = "$($script:visualDesign.AnimationPattern)" }
        if ($script:visualDesign.ColorPalette -and $script:visualDesign.ColorPalette.Count -gt 0) { $artPalette = $script:visualDesign.ColorPalette }
    }
    if ($null -eq $artPalette -and $PSBoundParameters.ContainsKey('PlaceholderColor')) {
        $artPalette = @(, @($PlaceholderColor[0], $PlaceholderColor[1], $PlaceholderColor[2]))
    }

    # Per-frame motion phase notes (cells are rendered one at a time, row-major).
    $frameNotes = @()
    for ($v = 0; $v -lt $Variants; $v++) {
        for ($f = 0; $f -lt $FrameCount; $f++) {
            $progress = if ($FrameCount -gt 1) { $f / [double]($FrameCount - 1) } else { 0.0 }
            $phase = if ($progress -lt 0.25) { "start of the animation, small and faint" }
                     elseif ($progress -lt 0.5) { "building up, growing stronger" }
                     elseif ($progress -lt 0.75) { "at peak intensity, largest and brightest" }
                     else { "fading out, dissipating" }
            $note = "frame $($f + 1) of $FrameCount, $phase"
            if ($patternHint) { $note = "$note, motion: $patternHint" }
            if ($Variants -gt 1) { $note = "$note, variant $($v + 1)" }
            $frameNotes += $note
        }
    }

    # Throws when SD cannot deliver unless -AllowProcedural / AAMT_SD_STRICT=0 (then returns $false).
    $sdSheetOk = Write-StarboundArt -AssetType "Animation" -Name $AnimationName -Description $artDescription `
        -Width $FrameSize[0] -Height $FrameSize[1] -OutputPath $sheetPath `
        -Frames ($FrameCount * $Variants) -Columns $FrameCount -FrameNotes $frameNotes -Palette $artPalette
    if ($sdSheetOk) {
        Write-Log "Created animation spritesheet (Stable Diffusion): $sheetPath" "SUCCESS"
        Write-Log "  Spritesheet size: $($FrameSize[0] * $FrameCount)x$($FrameSize[1] * $Variants)" "INFO"
    }
}

# Legacy System.Drawing sheet: only after an SD failure with procedural output explicitly allowed.
if (-not $haveExternalImage -and -not $sdSheetOk) {
    Write-Log "Stable Diffusion unavailable - drawing procedural placeholder sheet (-AllowProcedural)" "WARN"

    try {
        Add-Type -AssemblyName System.Drawing
        
        $totalWidth = $FrameSize[0] * $FrameCount
        $totalHeight = $FrameSize[1] * $Variants
        
        $bitmap = New-Object System.Drawing.Bitmap($totalWidth, $totalHeight)
        $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
        $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
        
        # Fill with transparent
        $graphics.Clear([System.Drawing.Color]::Transparent)
        
        # Get color palette (from AI or default)
        $colors = @()
        if ($UseOllama -and $script:visualDesign -and $script:visualDesign.ColorPalette) {
            foreach ($color in $script:visualDesign.ColorPalette) {
                $colors += [System.Drawing.Color]::FromArgb($color[0], $color[1], $color[2])
            }
        }
        if ($colors.Count -eq 0) {
            $colors = @(
                [System.Drawing.Color]::FromArgb($PlaceholderColor[0], $PlaceholderColor[1], $PlaceholderColor[2]),
                [System.Drawing.Color]::FromArgb([Math]::Max(0, $PlaceholderColor[0] - 50), [Math]::Max(0, $PlaceholderColor[1] - 50), [Math]::Max(0, $PlaceholderColor[2] - 50)),
                [System.Drawing.Color]::FromArgb([Math]::Max(0, $PlaceholderColor[0] - 100), [Math]::Max(0, $PlaceholderColor[1] - 100), [Math]::Max(0, $PlaceholderColor[2] - 100))
            )
        }
        
        $pen = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(255, $PlaceholderColor[0], $PlaceholderColor[1], $PlaceholderColor[2]), 1)
        
        for ($v = 0; $v -lt $Variants; $v++) {
            for ($f = 0; $f -lt $FrameCount; $f++) {
                $x = $f * $FrameSize[0]
                $y = $v * $FrameSize[1]
                $progress = $f / ($FrameCount - 1)  # 0 to 1
                
                # Generate intelligent frame based on AI design or description
                if ($UseOllama -and $script:visualDesign) {
                    # Use AI-generated pattern
                    $colorIndex = [Math]::Floor($progress * ($colors.Count - 1))
                    $brush = New-Object System.Drawing.SolidBrush($colors[$colorIndex])
                    
                    # Apply animation pattern
                    switch ($script:visualDesign.AnimationPattern.ToLower()) {
                        { $_ -match "grow|expand|scale" } {
                            $size = $FrameSize[0] * (0.2 + $progress * 0.8)
                            $centerX = $x + ($FrameSize[0] / 2) - ($size / 2)
                            $centerY = $y + ($FrameSize[1] / 2) - ($size / 2)
                            $graphics.FillEllipse($brush, $centerX, $centerY, $size, $size)
                        }
                        { $_ -match "rotate|spin" } {
                            $size = $FrameSize[0] * 0.7
                            $centerX = $x + ($FrameSize[0] / 2)
                            $centerY = $y + ($FrameSize[1] / 2)
                            $angle = $progress * 360
                            $points = @()
                            for ($i = 0; $i -lt 8; $i++) {
                                $a = ($angle + $i * 45) * [Math]::PI / 180
                                $px = $centerX + $size * 0.4 * [Math]::Cos($a)
                                $py = $centerY + $size * 0.4 * [Math]::Sin($a)
                                $points += (New-Object System.Drawing.Point([int]$px, [int]$py))
                            }
                            $graphics.FillPolygon($brush, $points)
                        }
                        { $_ -match "pulse|fade" } {
                            $alpha = [int](128 + 127 * [Math]::Sin($progress * [Math]::PI * 2))
                            $pulseBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb($alpha, $colors[$colorIndex].R, $colors[$colorIndex].G, $colors[$colorIndex].B))
                            $size = $FrameSize[0] * 0.6
                            $centerX = $x + ($FrameSize[0] / 2) - ($size / 2)
                            $centerY = $y + ($FrameSize[1] / 2) - ($size / 2)
                            $graphics.FillEllipse($pulseBrush, $centerX, $centerY, $size, $size)
                            $pulseBrush.Dispose()
                        }
                        default {
                            # Default: growing circle
                            $size = $FrameSize[0] * (0.3 + $progress * 0.7)
                            $centerX = $x + ($FrameSize[0] / 2) - ($size / 2)
                            $centerY = $y + ($FrameSize[1] / 2) - ($size / 2)
                            $graphics.FillEllipse($brush, $centerX, $centerY, $size, $size)
                        }
                    }
                    $brush.Dispose()
                } else {
                    # Fallback: simple growing shape
                    $size = [Math]::Max(4, ($FrameSize[0] - 4) * (($f + 1) / $FrameCount))
                    $centerX = $x + ($FrameSize[0] / 2) - ($size / 2)
                    $centerY = $y + ($FrameSize[1] / 2) - ($size / 2)
                    $brush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb([Math]::Floor($PlaceholderColor[3]/2), $PlaceholderColor[0], $PlaceholderColor[1], $PlaceholderColor[2]))
                    $graphics.FillEllipse($brush, $centerX, $centerY, $size, $size)
                    $brush.Dispose()
                }
                
                # Draw frame border
                $graphics.DrawRectangle($pen, $x, $y, $FrameSize[0] - 1, $FrameSize[1] - 1)
            }
        }
        
        $pen.Dispose()
        $bitmap.Save($sheetPath, [System.Drawing.Imaging.ImageFormat]::Png)

        $graphics.Dispose()
        $bitmap.Dispose()

        Write-Log "Created procedural placeholder spritesheet: $sheetPath" "SUCCESS"
        Write-Log "  Spritesheet size: ${totalWidth}x${totalHeight}" "INFO"
    }
    catch {
        Write-Log "Could not generate animation spritesheet: $_" "WARN"
    }
}

# Optional: use a provided source image as the spritesheet
if (-not [string]::IsNullOrEmpty($ImagePath) -and (Test-Path $ImagePath)) {
    $destImagePath = Join-Path $animOutputDir "$AnimationName.png"
    $srcFullPath = (Resolve-Path $ImagePath).Path
    $destFullPath = Join-Path (Resolve-Path $animOutputDir).Path "$AnimationName.png"
    
    # Only copy if source and destination are different
    if ($srcFullPath -ne $destFullPath) {
        Copy-Item -Path $ImagePath -Destination $destImagePath -Force
        Write-Log "Copied source image to: $destImagePath" "SUCCESS"
    }
}

# Generate metadata
$metadata = @{
    AnimationName = $AnimationName
    Preset = $Preset
    FrameCount = $FrameCount
    FrameSize = $FrameSize
    AnimationCycle = $AnimationCycle
    Variants = $Variants
    Offset = $Offset
    Loops = $Loops
    Description = $Description
    GeneratedAt = (Get-Date).ToString("o")
    OutputDirectory = $animOutputDir
    Files = @(
        "$AnimationName.animation",
        "$AnimationName.frames"
    )
    StarboundFormat = "1.4+"
}

$metadataPath = Join-Path $animOutputDir "animation_metadata.json"
$metadata | ConvertTo-Json -Depth 5 | Out-File -FilePath $metadataPath -Encoding UTF8

Write-Log ""
Write-Log "═══════════════════════════════════════════════════════════"
Write-Log "  Generation Complete!" "SUCCESS"
Write-Log "═══════════════════════════════════════════════════════════"
Write-Log ""
Write-Log "Generated files:" "INFO"

Get-ChildItem -Path $animOutputDir | ForEach-Object {
    Write-Log "  - $($_.Name)" "SUCCESS"
}

Write-Log ""
Write-Log "To use in Starbound/OpenStarbound:" "INFO"
Write-Log "  1. Copy the $AnimationName folder to your mod's animations/ directory" "INFO"
Write-Log "  2. Reference in particles as: /animations/$AnimationName/$AnimationName.animation" "INFO"
Write-Log ""
Write-Log "Required spritesheet:" "INFO"
Write-Log "  - Size: $($FrameSize[0] * $FrameCount)x$($FrameSize[1] * $Variants) pixels" "INFO"
Write-Log "  - Frames: $FrameCount columns x $Variants rows" "INFO"
Write-Log "  - Each frame: $($FrameSize[0])x$($FrameSize[1]) pixels" "INFO"
Write-Log ""

# Return data for piping
return @{
    Success = $true
    AnimationName = $AnimationName
    OutputPath = $animOutputDir
    AnimationFile = $animationPath
    FramesFile = $framesPath
    FrameCount = $FrameCount
    FrameSize = $FrameSize
    AnimationCycle = $AnimationCycle
}

