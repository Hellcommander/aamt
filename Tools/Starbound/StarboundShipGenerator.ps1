<#
.SYNOPSIS
    Starbound Ship Generator - Creates ship structure files and block key configs

.DESCRIPTION
    Generates ship-related files for Starbound/OpenStarbound:
    - .structure files for each ship tier
    - blockKey.config for color-to-object mapping
    - Block map PNGs (exact-colour key maps: data, drawn with System.Drawing, not art)
    - Side-view hull sprite PNGs per tier, painted by the local Stable Diffusion 3.5
      server (:1338). SD or throw: with -AllowProcedural (or AAMT_SD_STRICT=0) a failed
      hull sprite is skipped with a warning instead.
    - Documentation for manual sprite creation

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}

.PARAMETER ShipName
    Base name of the ship (e.g., "myrace" generates myraceTX files)

.PARAMETER Race
    Race name for race-specific objects

.PARAMETER Preset
    Built-in ship preset to use

.PARAMETER MaxTier
    Maximum ship tier to generate (0-8)

.EXAMPLE
    .\StarboundShipGenerator.ps1 -ShipName "human" -Race "human" -Preset Human
    .\StarboundShipGenerator.ps1 -ShipName "custom" -Race "customrace" -MaxTier 4
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$ShipName,

    [Parameter(Mandatory=$false)]
    [string]$Race = "",

    [Parameter(Mandatory=$false)]
    [ValidateSet("Human", "Apex", "Avian", "Floran", "Glitch", "Hylotl", "Novakid", "Generic", "Custom")]
    [string]$Preset = "Generic",

    [Parameter(Mandatory=$false)]
    [string]$OutputDir = "StarboundShips",

    [Parameter(Mandatory=$false)]
    [ValidateRange(1, 8)]
    [int]$MaxTier = 8,

    [Parameter(Mandatory=$false)]
    [array]$SpritePosition = @(8, 14),  # Position offset for sprite overlays

    [Parameter(Mandatory=$false)]
    [switch]$GeneratePlaceholders,  # Deprecated/no-op: block maps and SD hull sprites are always written; kept for CLI compatibility

    [Parameter(Mandatory=$false)]
    [switch]$IncludeAllTiers,  # Generate all tier files

    # Custom block key entries
    [Parameter(Mandatory=$false)]
    [array]$CustomBlockEntries = $null,

    # Ship capabilities per tier
    [Parameter(Mandatory=$false)]
    [hashtable]$TierCapabilities = $null,

    # Crew sizes per tier
    [Parameter(Mandatory=$false)]
    [hashtable]$TierCrewSizes = $null,
    
    # Ollama integration for intelligent design
    [Parameter(Mandatory=$false)]
    [string]$Description = "",
    
    [Parameter(Mandatory=$false)]
    [switch]$UseOllama,
    
    [Parameter(Mandatory=$false)]
    [string]$OllamaModel = "codellama:7b-instruct",
    
    [Parameter(Mandatory=$false)]
    [string]$PlanningModel = "",  # Defaults to OllamaModel if not specified
    
    [Parameter(Mandatory=$false)]
    [string]$VisualModel = "wizardlm-uncensored",

    # Stable Diffusion: hull sprites are always painted by SD; this only permits skipping a
    # failed sprite (instead of throwing) when SD is unavailable (or AAMT_SD_STRICT=0).
    [Parameter(Mandatory=$false)]
    [switch]$AllowProcedural
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
# DEFAULT TIER CONFIGURATIONS
# ============================================================================

$DefaultTierCapabilities = @{
    0 = @()
    1 = @()
    2 = @("teleport")
    3 = @("teleport", "planetTravel", "systemTravel")
    4 = @("teleport", "planetTravel", "systemTravel")
    5 = @("teleport", "planetTravel", "systemTravel")
    6 = @("teleport", "planetTravel", "systemTravel")
    7 = @("teleport", "planetTravel", "systemTravel")
    8 = @("teleport", "planetTravel", "systemTravel")
}

$DefaultTierCrewSizes = @{
    0 = 2
    1 = 2
    2 = 2
    3 = 2
    4 = 4
    5 = 6
    6 = 8
    7 = 10
    8 = 12
}

# Ship sizes per tier in game tiles (block map size; hull sprites are 8 px per tile)
$TierSizes = @{
    0 = @{ Width = 80; Height = 50 }
    1 = @{ Width = 70; Height = 40 }
    2 = @{ Width = 70; Height = 40 }
    3 = @{ Width = 100; Height = 55 }
    4 = @{ Width = 100; Height = 55 }
    5 = @{ Width = 145; Height = 70 }
    6 = @{ Width = 155; Height = 95 }
    7 = @{ Width = 195; Height = 95 }
    8 = @{ Width = 195; Height = 95 }
}

# ============================================================================
# BLOCK KEY COLOR DEFINITIONS
# ============================================================================

# Standard block key entries (based on human ship)
$StandardBlockKey = @(
    # Empty space
    @{
        value = @(255, 255, 255, 255)
        foregroundBlock = $false
        backgroundBlock = $false
        comment = "Empty - no blocks"
    },
    
    # Background only
    @{
        value = @(0, 0, 255, 255)
        foregroundBlock = $false
        backgroundBlock = $true
        comment = "Background only (ship interior)"
    },
    
    # Foreground + Background (solid walls)
    @{
        value = @(255, 0, 0, 255)
        foregroundBlock = $true
        backgroundBlock = $true
        comment = "Solid wall (foreground + background)"
    },
    
    # Ship Locker (green)
    @{
        value = @(0, 255, 0, 255)
        foregroundBlock = $false
        backgroundBlock = $true
        backgroundMat = "RACE_shipwall"
        flags = @("shipLockerPosition")
        object = "RACE_shiplocker"
        objectParameters = @{
            treasurePools = @("RACE_StarterTreasure")
            level = 0.5
            unbreakable = $true
        }
        objectResidual = $true
        comment = "Ship Locker"
    },
    
    # Tech Station (light green)
    @{
        value = @(142, 255, 142, 255)
        foregroundBlock = $false
        backgroundBlock = $true
        backgroundMat = "RACE_shipwall"
        object = "RACE_techstation"
        objectParameters = @{
            unbreakable = $true
        }
        objectResidual = $true
        comment = "Tech Station"
    },
    
    # Fuel Hatch (salmon)
    @{
        value = @(255, 90, 90, 255)
        foregroundBlock = $false
        backgroundBlock = $true
        object = "RACE_fuelhatch"
        objectParameters = @{
            unbreakable = $true
        }
        objectResidual = $true
        comment = "Fuel Hatch"
    },
    
    # Broken Fuel Hatch
    @{
        value = @(255, 87, 81, 255)
        foregroundBlock = $false
        backgroundBlock = $true
        object = "brokenRAC_Efuelhatch"
        objectParameters = @{
            unbreakable = $true
        }
        comment = "Broken Fuel Hatch (T0)"
    },
    
    # Ship Light (yellow)
    @{
        value = @(255, 255, 0, 255)
        foregroundBlock = $false
        backgroundBlock = $true
        backgroundMat = "RACE_shipdetails"
        object = "RACE_shiplight"
        objectResidual = $true
        comment = "Ship Light"
    },
    
    # Ship Door (orange)
    @{
        value = @(255, 102, 0, 255)
        foregroundBlock = $false
        backgroundBlock = $false
        object = "RACE_shipdoor"
        objectResidual = $true
        comment = "Ship Door"
    },
    
    # Teleporter (purple)
    @{
        value = @(156, 0, 255, 255)
        anchor = $true
        foregroundBlock = $false
        backgroundBlock = $true
        backgroundMat = "RACE_shipdetails"
        object = "RACE_teleporter"
        flags = @("playerSpawn")
        objectParameters = @{
            unbreakable = $true
        }
        comment = "Teleporter (player spawn)"
    },
    
    # Captain's Chair (cyan)
    @{
        value = @(0, 255, 255, 255)
        foregroundBlock = $false
        backgroundBlock = $true
        object = "RACE_captainschair"
        objectDirection = "right"
        objectParameters = @{
            unbreakable = $true
        }
        comment = "Captain's Chair"
    },
    
    # Booster Flame (light blue)
    @{
        value = @(167, 167, 255, 255)
        foregroundBlock = $false
        backgroundBlock = $true
        object = "boosterflameRAC_E"
        objectParameters = @{
            unbreakable = $true
        }
        comment = "Booster Flame"
    },
    
    # Big Booster Flame
    @{
        value = @(200, 200, 200, 255)
        foregroundBlock = $false
        backgroundBlock = $true
        object = "bigboosterflameRAC_E"
        objectParameters = @{
            unbreakable = $true
        }
        comment = "Big Booster Flame"
    },
    
    # Invisible Light
    @{
        value = @(122, 122, 122, 255)
        foregroundBlock = $false
        backgroundBlock = $true
        object = "invisiblelight"
        objectParameters = @{
            unbreakable = $true
        }
        comment = "Invisible Light"
    },
    
    # Ship Engine
    @{
        value = @(174, 137, 81, 255)
        foregroundBlock = $false
        backgroundBlock = $true
        object = "shipengine"
        objectParameters = @{
            unbreakable = $true
        }
        comment = "Ship Engine"
    },
    
    # Background material only - Wall
    @{
        value = @(255, 255, 144)
        foregroundBlock = $false
        backgroundBlock = $true
        backgroundMat = "RACE_shipwall"
        comment = "Background - Ship Wall"
    },
    
    # Background material only - Details
    @{
        value = @(255, 117, 144)
        foregroundBlock = $false
        backgroundBlock = $true
        backgroundMat = "RACE_shipdetails"
        comment = "Background - Ship Details"
    },
    
    # Background material only - Support
    @{
        value = @(255, 117, 255)
        foregroundBlock = $false
        backgroundBlock = $true
        backgroundMat = "RACE_shipsupport"
        comment = "Background - Ship Support"
    }
)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

function Replace-RaceInBlockKey {
    param(
        [array]$BlockKey,
        [string]$Race
    )
    
    $result = @()
    foreach ($entry in $BlockKey) {
        $newEntry = @{}
        foreach ($key in $entry.Keys) {
            $value = $entry[$key]
            if ($value -is [string]) {
                $newEntry[$key] = $value -replace "RACE_", "${Race}" -replace "RAC_E", "${Race}"
            } elseif ($value -is [hashtable]) {
                $newEntry[$key] = Replace-RaceInBlockKey -BlockKey @($value) -Race $Race
                $newEntry[$key] = $newEntry[$key][0]
            } elseif ($value -is [array] -and $value[0] -is [string]) {
                $newEntry[$key] = $value | ForEach-Object { $_ -replace "RACE_", "${Race}" -replace "RAC_E", "${Race}" }
            } else {
                $newEntry[$key] = $value
            }
        }
        $result += $newEntry
    }
    return $result
}

function New-ShipBlockMap {
    # Writes the exact-colour block key map (red = outside, blue = interior, key pixels for
    # objects). This is a data file the game parses by RGB value, not artwork, so it is
    # deliberately drawn directly rather than generated by Stable Diffusion.
    param(
        [string]$OutputPath,
        [int]$Width,
        [int]$Height,
        [int]$Tier
    )
    
    try {
        Add-Type -AssemblyName System.Drawing
        
        $bitmap = New-Object System.Drawing.Bitmap($Width, $Height)
        $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
        
        # Red background (standard for block maps)
        $graphics.Clear([System.Drawing.Color]::FromArgb(255, 255, 0, 0))
        
        # Draw basic ship shape with blue (interior)
        $blue = [System.Drawing.Color]::FromArgb(255, 0, 0, 255)
        $blueBrush = New-Object System.Drawing.SolidBrush($blue)
        
        # Simple rectangular interior
        $interiorWidth = [int]($Width * 0.7)
        $interiorHeight = [int]($Height * 0.5)
        $interiorX = [int](($Width - $interiorWidth) / 2)
        $interiorY = [int](($Height - $interiorHeight) / 2)
        
        $graphics.FillRectangle($blueBrush, $interiorX, $interiorY, $interiorWidth, $interiorHeight)
        
        # Add some key objects
        # Teleporter (purple) - bottom center
        $purple = [System.Drawing.Color]::FromArgb(255, 156, 0, 255)
        $bitmap.SetPixel([int]($Width / 2), $interiorY + $interiorHeight - 2, $purple)
        $bitmap.SetPixel([int]($Width / 2) + 1, $interiorY + $interiorHeight - 2, $purple)
        
        # Captain's chair (cyan) - right side
        $cyan = [System.Drawing.Color]::FromArgb(255, 0, 255, 255)
        $bitmap.SetPixel($interiorX + $interiorWidth - 5, $interiorY + [int]($interiorHeight / 2), $cyan)
        
        # Fuel hatch (salmon) - left side
        $salmon = [System.Drawing.Color]::FromArgb(255, 255, 90, 90)
        $bitmap.SetPixel($interiorX + 2, $interiorY + [int]($interiorHeight / 2), $salmon)
        
        # Ship locker (green) - near teleporter
        $green = [System.Drawing.Color]::FromArgb(255, 0, 255, 0)
        $bitmap.SetPixel([int]($Width / 2) - 5, $interiorY + $interiorHeight - 3, $green)
        
        $blueBrush.Dispose()
        $bitmap.Save($OutputPath, [System.Drawing.Imaging.ImageFormat]::Png)
        $graphics.Dispose()
        $bitmap.Dispose()
        
        return $true
    }
    catch {
        Write-Host "[Warning] Could not write ship block map: $_" -ForegroundColor Yellow
        return $false
    }
}

function Get-StableSeed {
    param([string]$Text)
    $h = 17
    foreach ($ch in $Text.ToCharArray()) { $h = (($h * 31) + [int]$ch) % 900000 }
    return [int]($h + 1)
}

function ConvertTo-CleanJson {
    param($Object, [int]$Depth = 10)
    
    # Convert to JSON and clean up formatting
    $json = $Object | ConvertTo-Json -Depth $Depth
    
    # Fix array formatting to be more compact for small arrays
    $json = $json -replace '\[\s+(\d+),\s+(\d+),\s+(\d+),\s+(\d+)\s+\]', '[$1, $2, $3, $4]'
    $json = $json -replace '\[\s+(\d+),\s+(\d+),\s+(\d+)\s+\]', '[$1, $2, $3]'
    $json = $json -replace '\[\s+(\d+),\s+(\d+)\s+\]', '[$1, $2]'
    
    return $json
}

# ============================================================================
# MAIN GENERATION LOGIC
# ============================================================================

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Starbound Ship Generator" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Set race from preset if not specified
if ([string]::IsNullOrEmpty($Race)) {
    $Race = switch ($Preset) {
        "Human" { "human" }
        "Apex" { "apex" }
        "Avian" { "avian" }
        "Floran" { "floran" }
        "Glitch" { "glitch" }
        "Hylotl" { "hylotl" }
        "Novakid" { "novakid" }
        default { $ShipName }
    }
}

# Create output directory
$outputPath = $OutputDir
if (-not [System.IO.Path]::IsPathRooted($OutputDir)) {
    $outputPath = Join-Path (Get-Location) $OutputDir
}

$shipDir = Join-Path $outputPath $ShipName
if (-not (Test-Path $shipDir)) {
    New-Item -ItemType Directory -Path $shipDir -Force | Out-Null
    Write-Host "[Created] Ship directory: $shipDir" -ForegroundColor Green
}

# Apply tier configurations
$finalCapabilities = if ($TierCapabilities) { $TierCapabilities } else { $DefaultTierCapabilities }
$finalCrewSizes = if ($TierCrewSizes) { $TierCrewSizes } else { $DefaultTierCrewSizes }

Write-Host "[Generating] Ship: $ShipName (Race: $Race)" -ForegroundColor Yellow
Write-Host "  Preset: $Preset" -ForegroundColor Gray
Write-Host "  Max Tier: T$MaxTier" -ForegroundColor Gray

# ============================================================================
# Generate blockKey.config
# ============================================================================

Write-Host ""
Write-Host "[Creating] blockKey.config..." -ForegroundColor Yellow

$blockKeyEntries = Replace-RaceInBlockKey -BlockKey $StandardBlockKey -Race $Race

# Add custom entries if provided
if ($CustomBlockEntries) {
    $blockKeyEntries += $CustomBlockEntries
}

# Build blockKey array (removing comment field for actual output)
$cleanBlockKey = @()
foreach ($entry in $blockKeyEntries) {
    $cleanEntry = [ordered]@{}
    foreach ($key in $entry.Keys) {
        if ($key -ne "comment") {
            $cleanEntry[$key] = $entry[$key]
        }
    }
    $cleanBlockKey += $cleanEntry
}

$blockKeyConfig = [ordered]@{
    blockKey = $cleanBlockKey
}

$blockKeyJson = ConvertTo-CleanJson -Object $blockKeyConfig
$blockKeyFile = Join-Path $shipDir "blockKey.config"
$blockKeyJson | Out-File -FilePath $blockKeyFile -Encoding UTF8 -Force

Write-Host "[Created] $blockKeyFile" -ForegroundColor Green

# ============================================================================
# Generate structure files for each tier
# ============================================================================

Write-Host ""
Write-Host "[Creating] Structure files..." -ForegroundColor Yellow

$tiersToGenerate = if ($IncludeAllTiers) { 0..$MaxTier } else { @(0, $MaxTier) }
$shipDesign = $null

foreach ($tier in $tiersToGenerate) {
    $tierName = "${ShipName}T${tier}"
    
    $capabilities = if ($finalCapabilities.ContainsKey($tier)) { 
        $finalCapabilities[$tier] 
    } else { 
        $finalCapabilities[[int][Math]::Min($tier, 8)]
    }
    
    $crewSize = if ($finalCrewSizes.ContainsKey($tier)) {
        $finalCrewSizes[$tier]
    } else {
        $finalCrewSizes[[int][Math]::Min($tier, 8)]
    }
    
    $structure = [ordered]@{
        config = [ordered]@{
            shipUpgrades = [ordered]@{
                capabilities = $capabilities
                crewSize = $crewSize
            }
        }
        backgroundOverlays = @(
            [ordered]@{
                image = "${tierName}.png"
                position = $SpritePosition
                fullbright = $true
            },
            [ordered]@{
                image = "${tierName}lit.png"
                position = $SpritePosition
            }
        )
        blockKey = "blockKey.config:blockKey"
        blockImage = "${tierName}blocks.png"
    }
    
    $structureJson = ConvertTo-CleanJson -Object $structure
    $structureFile = Join-Path $shipDir "${tierName}.structure"
    $structureJson | Out-File -FilePath $structureFile -Encoding UTF8 -Force
    
    Write-Host "[Created] ${tierName}.structure (Crew: $crewSize, Capabilities: $($capabilities.Count))" -ForegroundColor Green
    
    # Always write the block-map PNG (data key map) and the SD hull sprite
    if ($true) {
        $size = $TierSizes[$tier]
        $blockMapFile = Join-Path $shipDir "${tierName}blocks.png"
        
        # Use Ollama for intelligent ship layout if requested
        if ($UseOllama -and (-not [string]::IsNullOrEmpty($Description)) -and $tier -eq 0) {
            Write-Host "Using Ollama for intelligent ship layout design..." -ForegroundColor Cyan
            
            if (Get-Command Invoke-OllamaRequest -ErrorAction SilentlyContinue) {
                $shipPrompt = "You are designing a ship interior layout for a Starbound game mod.
Ship Name: $ShipName
Race: $Race
Description: $Description
Tier: T$tier (Size: $($size.Width)x$($size.Height) pixels)

Generate a ship layout design specification in JSON:
{
  'LayoutStyle': string - layout type (compact, spacious, organized, etc.),
  'InteriorShape': string - shape description (rectangular, organic, etc.),
  'KeyFeatures': string - important features to include
}

Return ONLY the JSON object."
                
                $modelToUse = if ($VisualModel) { $VisualModel } else { $OllamaModel }
                $shipResponse = Invoke-OllamaRequest -Prompt $shipPrompt -TaskType "visual" -ResponseLength "short" -ModelName $modelToUse
                
                if ($shipResponse) {
                    $jsonMatch = $shipResponse | Select-String -Pattern '\{[\s\S]*\}' | Select-Object -First 1
                    if ($jsonMatch) {
                        try {
                            $shipDesign = $jsonMatch.Matches[0].Value | ConvertFrom-Json
                            Write-Host "AI ship design: $($shipDesign.LayoutStyle) - $($shipDesign.InteriorShape)" -ForegroundColor Green
                            Write-Host "  Features: $($shipDesign.KeyFeatures)" -ForegroundColor Gray
                        } catch {
                            Write-Host "Could not parse AI ship design: $_" -ForegroundColor Yellow
                        }
                    }
                }
            }
        }
        
        $success = New-ShipBlockMap -OutputPath $blockMapFile `
            -Width $size.Width -Height $size.Height -Tier $tier

        if ($success) {
            Write-Host "[Created] ${tierName}blocks.png (block key map)" -ForegroundColor Green
        }

        # ---- Hull sprite (${tierName}.png): transparent side-view hull, Stable Diffusion ----
        $raceFlavor = switch ($Preset) {
            "Human"   { "sleek utilitarian steel hull with blue accents and a glass cockpit" }
            "Apex"    { "rugged industrial grey-brown hull with exposed pipes and rivets" }
            "Avian"   { "ornate golden temple-like hull with swept wings and red banners" }
            "Floran"  { "organic overgrown hull of wood, vines and leaves" }
            "Glitch"  { "medieval castle-like stone and iron hull with turrets" }
            "Hylotl"  { "elegant blue and white hull with round porthole windows and curved fins" }
            "Novakid" { "rustic frontier brass and wood hull with lanterns and exhaust pipes" }
            default   { "sci-fi spaceship hull" }
        }
        $tierLook = if ($tier -eq 0) { "wrecked, broken and battered, crashed and barely holding together, missing panels, scorch marks, dim" }
            elseif ($tier -le 2) { "small basic starter ship, simple patched hull" }
            elseif ($tier -le 4) { "mid-size ship with solid hull and visible engines" }
            elseif ($tier -le 6) { "large advanced ship with layered armour and big engines" }
            else { "huge flagship with elaborate armoured hull, multiple engines and glowing details" }
        $hullParts = New-Object System.Collections.Generic.List[string]
        $hullParts.Add("$Race spaceship exterior, side view, $raceFlavor, tier $tier, $tierLook")
        if (-not [string]::IsNullOrWhiteSpace($Description)) { $hullParts.Add($Description.Trim()) }
        if ($shipDesign) {
            if ($shipDesign.LayoutStyle)  { $hullParts.Add("$($shipDesign.LayoutStyle) layout") }
            if ($shipDesign.KeyFeatures)  { $hullParts.Add([string]$shipDesign.KeyFeatures) }
        }
        $hullParts.Add("single ship hull facing right, long horizontal silhouette, Starbound sci-fantasy pixel art")
        $hullPrompt = $hullParts -join ", "

        $hullFile = Join-Path $shipDir "${tierName}.png"
        $hullW = [int]$size.Width * 8
        $hullH = [int]$size.Height * 8
        Write-Host "[SD] Painting hull sprite ${tierName}.png (${hullW}x${hullH}) with Stable Diffusion..." -ForegroundColor Yellow
        # Throws when SD fails and procedural art is not allowed; returns $false only when it is allowed.
        $hullOk = New-StarboundSdArt -Kind sprite -Prompt $hullPrompt -OutputPath $hullFile `
            -Width $hullW -Height $hullH -SdKind sprite -Transparent -Pixel -Colors 32 `
            -Seed (Get-StableSeed -Text "$ShipName|$Preset|$tier") -AllowProcedural:$AllowProcedural
        if ($hullOk) {
            Write-Host "[Created] ${tierName}.png (Stable Diffusion hull sprite)" -ForegroundColor Green
        } else {
            Write-Host "[Skipped] ${tierName}.png - SD unavailable and procedural hull art is not generated" -ForegroundColor Yellow
        }
    }
}

# ============================================================================
# Generate README with block key documentation
# ============================================================================

$readmeContent = @"
# Ship: $ShipName

## Block Key Color Reference

Use these colors in your block map PNGs:

| Color (RGBA) | Hex | Description |
|--------------|-----|-------------|
"@

foreach ($entry in $blockKeyEntries) {
    $rgba = $entry.value
    $hexColor = "#{0:X2}{1:X2}{2:X2}" -f $rgba[0], $rgba[1], $rgba[2]
    $comment = if ($entry.comment) { $entry.comment } else { "Block entry" }
    $readmeContent += "`n| ($($rgba[0]), $($rgba[1]), $($rgba[2]), $($rgba[3])) | $hexColor | $comment |"
}

$readmeContent += @"


## File Structure

Each tier requires:
- `${ShipName}TX.structure` - Ship structure definition
- `${ShipName}TXblocks.png` - Block map (colored pixels)
- `${ShipName}TX.png` - Ship hull sprite (Stable Diffusion, generated; 8 px per block-map pixel)
- `${ShipName}TXlit.png` - Lit overlay (thrusters, etc.) - not generated, create manually

## Tier Capabilities

| Tier | Crew Size | Capabilities |
|------|-----------|--------------|
"@

foreach ($tier in 0..$MaxTier) {
    $caps = $finalCapabilities[$tier] -join ", "
    if (-not $caps) { $caps = "(none)" }
    $crew = $finalCrewSizes[$tier]
    $readmeContent += "`n| T$tier | $crew | $caps |"
}

$readmeContent += @"


## Creating Block Maps

1. Create a PNG with the ship's interior layout
2. Use colors from the table above
3. Red background = outside ship
4. Blue = interior floor (walkable)
5. Place objects using their designated colors

## Tips

- Start with T0 (broken ship) and T8 (final form)
- Block maps are at 8 pixels per game tile
- Sprites can be any resolution (typically 2-4x block map size)
- Lit overlays should only contain glowing elements
"@

$readmeFile = Join-Path $shipDir "README.md"
$readmeContent | Out-File -FilePath $readmeFile -Encoding UTF8 -Force

Write-Host ""
Write-Host "[Created] README.md (documentation)" -ForegroundColor Green

# ============================================================================
# Summary
# ============================================================================

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Generation Summary" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Ship Name: $ShipName" -ForegroundColor White
Write-Host "  Race: $Race" -ForegroundColor White
Write-Host "  Preset: $Preset" -ForegroundColor White
Write-Host "  Tiers Generated: $($tiersToGenerate -join ', ')" -ForegroundColor Yellow
Write-Host ""
Write-Host "Output Directory: $shipDir" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "  1. Review the generated hull sprites (${ShipName}TX.png, Stable Diffusion)" -ForegroundColor Gray
Write-Host "  2. Create lit overlays (${ShipName}TXlit.png) matching the hull" -ForegroundColor Gray
Write-Host "  3. Edit the generated block maps (${ShipName}TXblocks.png) to match the hull layout" -ForegroundColor Gray
Write-Host "  4. Register ship in species config" -ForegroundColor Gray
Write-Host ""

# Return result object
return @{
    Success = $true
    ShipDirectory = $shipDir
    BlockKeyFile = $blockKeyFile
    ShipName = $ShipName
    Race = $Race
    TiersGenerated = $tiersToGenerate
}

