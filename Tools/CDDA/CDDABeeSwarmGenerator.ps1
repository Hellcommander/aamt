#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate bee swarm creature assets for CDDA (Cataclysm: Dark Days Ahead).
    AI-Assisted Modding Tools (AAMT) - CDDA Toolset
    
.DESCRIPTION
    Creates CDDA-compatible bee swarm creature assets including:
    - Tileset sprites (16x16 or 32x32 tiles)
    - Animation frames (idle, flying, attacking)
    - JSON creature definition
    - Directional sprites (8 directions)

    Role-filling art is procedural GDI+ PNGs (always written). AI/SD is an optional upgrade, not required.
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$SwarmName = "bee_swarm",
    
    [Parameter(Mandatory=$false)]
    [ValidateSet(16, 32)]
    [int]$TileSize = 16,
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("Small", "Medium", "Large")]
    [string]$SwarmSize = "Medium",
    
    [Parameter(Mandatory=$false)]
    [string]$OutputDir = "CDDAMods\BeeSwarm",
    
    [Parameter(Mandatory=$false)]
    [switch]$LaunchControlRoom,
    
    [Parameter(Mandatory=$false)]
    [string]$WatchDirectory = ""
)

$ErrorActionPreference = "Stop"
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

# Load shared asset generation settings from Tools root
$settingsPath = Join-Path (Split-Path -Parent $PSScriptRoot) "AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}

# Setup logging
$logDir = Join-Path $PSScriptRoot "Logs"
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

$logFile = Join-Path $logDir "CDDABeeSwarm_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
$script:LogFile = $logFile

function Write-Log {
    param(
        [string]$Message,
        [string]$Level = "INFO"
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss.fff"
    $logEntry = "[$timestamp] [$Level] $Message"
    
    # Write to console
    $color = switch ($Level) {
        "ERROR" { "Red" }
        "WARN" { "Yellow" }
        "SUCCESS" { "Green" }
        "INFO" { "Cyan" }
        default { "White" }
    }
    Write-Host $logEntry -ForegroundColor $color
    
    # Write to log file
    try {
        Add-Content -Path $script:LogFile -Value $logEntry -Encoding UTF8 -ErrorAction SilentlyContinue
    } catch {
        # Silently fail if log write fails
    }
}

Write-Log "═══════════════════════════════════════════════════════════" "INFO"
Write-Log "  CDDA Bee Swarm Creature Generator" "INFO"
Write-Log "  AI-Assisted Modding Tools (AAMT)" "INFO"
Write-Log "═══════════════════════════════════════════════════════════" "INFO"
Write-Log "Log file: $logFile" "INFO"
Write-Log ""

# Create output directory structure
$modDir = Join-Path $OutputDir "mods\bee_swarm"
$gfxDir = Join-Path $modDir "gfx"
$tilesetDir = Join-Path $gfxDir "tileset"
$creatureDir = Join-Path $modDir "creatures"

foreach ($dir in @($modDir, $gfxDir, $tilesetDir, $creatureDir)) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}

# Setup watch directory for GUI
$watchDir = if ([string]::IsNullOrWhiteSpace($WatchDirectory)) {
    Join-Path $OutputDir "watch"
} else {
    $WatchDirectory
}

if (-not (Test-Path $watchDir)) {
    New-Item -ItemType Directory -Path $watchDir -Force | Out-Null
}

Write-Log "Swarm Name: $SwarmName" "INFO"
Write-Log "Tile Size: ${TileSize}x${TileSize}" "INFO"
Write-Log "Swarm Size: $SwarmSize" "INFO"
Write-Log "Output Directory: $OutputDir" "INFO"
Write-Log ""

# Launch Control Room if requested
if ($LaunchControlRoom) {
    $controlRoomScript = Join-Path $PSScriptRoot "AssetGeneratorControlRoom.ps1"
    if (Test-Path $controlRoomScript) {
        Write-Host "Launching Control Room..." -ForegroundColor Cyan
        
        $controlRoomArgs = @(
            "-AssetType", "Spritesheet",
            "-WatchDirectory", $watchDir,
            "-AutoExport"
        )
        
        $allArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$controlRoomScript`"") + $controlRoomArgs
        Start-Process -FilePath "pwsh" -ArgumentList $allArgs -WindowStyle Normal
        Write-Log "Control Room launched" "SUCCESS"
        Start-Sleep -Seconds 2
    }
}

# Determine swarm parameters
$beeCount = switch ($SwarmSize) {
    "Small" { 5 }
    "Medium" { 10 }
    "Large" { 20 }
    default { 10 }
}

$swarmRadius = switch ($SwarmSize) {
    "Small" { $TileSize * 0.6 }
    "Medium" { $TileSize * 0.8 }
    "Large" { $TileSize * 1.0 }
    default { $TileSize * 0.8 }
}

Write-Log "Generating bee swarm sprites..." "INFO"

# Generate sprites for 8 directions
$directions = @("N", "NE", "E", "SE", "S", "SW", "W", "NW")
$frames = @("idle", "flying", "attacking")
$sprites = @{}

foreach ($direction in $directions) {
    foreach ($frame in $frames) {
        $spriteName = "${SwarmName}_${direction}_${frame}"
        $spritePath = Join-Path $watchDir "${spriteName}.png"
        
        Write-Log "  Generating: $spriteName" "INFO"
        
        # Create bee swarm sprite
        $bitmap = New-Object System.Drawing.Bitmap $TileSize, $TileSize
        $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
        $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
        $graphics.Clear([System.Drawing.Color]::Transparent)
        
        # Calculate direction angle
        $angle = switch ($direction) {
            "N" { 270 }
            "NE" { 315 }
            "E" { 0 }
            "SE" { 45 }
            "S" { 90 }
            "SW" { 135 }
            "W" { 180 }
            "NW" { 225 }
            default { 0 }
        }
        
        # Draw bees in swarm pattern
        $centerX = $TileSize / 2
        $centerY = $TileSize / 2
        
        # Base bee color (yellow/orange)
        $beeColor = [System.Drawing.Color]::FromArgb(255, 255, 200, 0)
        $beeDarkColor = [System.Drawing.Color]::FromArgb(255, 200, 150, 0)
        
        # Animation offset for flying/attacking
        $animOffset = switch ($frame) {
            "idle" { 0 }
            "flying" { 1 }
            "attacking" { 2 }
            default { 0 }
        }
        
        for ($i = 0; $i -lt $beeCount; $i++) {
            # Calculate bee position in swarm
            $angleRad = [Math]::PI * 2 * $i / $beeCount
            $radius = $swarmRadius * (0.5 + (Get-Random -Minimum 0 -Maximum 0.5))
            
            # Add animation variation
            $animAngle = $angleRad + ($animOffset * 0.3)
            $x = $centerX + [Math]::Cos($animAngle) * $radius
            $y = $centerY + [Math]::Sin($animAngle) * $radius
            
            # Add direction-based offset
            $dirRad = [Math]::PI * $angle / 180
            $x += [Math]::Cos($dirRad) * ($animOffset * 0.5)
            $y += [Math]::Sin($dirRad) * ($animOffset * 0.5)
            
            # Draw bee (small circle with wings)
            $beeSize = [Math]::Max(2, $TileSize / 8)
            $beeBrush = New-Object System.Drawing.SolidBrush($beeColor)
            $beePen = New-Object System.Drawing.Pen($beeDarkColor, 1)
            
            # Bee body
            $graphics.FillEllipse($beeBrush, $x - $beeSize/2, $y - $beeSize/2, $beeSize, $beeSize)
            $graphics.DrawEllipse($beePen, $x - $beeSize/2, $y - $beeSize/2, $beeSize, $beeSize)
            
            # Wings (smaller circles)
            $wingSize = $beeSize * 0.4
            $wingBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(128, 255, 255, 255))
            $graphics.FillEllipse($wingBrush, $x - $beeSize/2 - $wingSize/2, $y - $beeSize/2, $wingSize, $wingSize)
            $graphics.FillEllipse($wingBrush, $x + $beeSize/2 - $wingSize/2, $y - $beeSize/2, $wingSize, $wingSize)
            
            $beeBrush.Dispose()
            $beePen.Dispose()
            $wingBrush.Dispose()
        }
        
        $bitmap.Save($spritePath)
        $graphics.Dispose()
        $bitmap.Dispose()
        
        $sprites["${direction}_${frame}"] = $spritePath
    }
}

Write-Log "Generated $($sprites.Count) sprites" "SUCCESS"
Write-Log ""

# Create spritesheet
Write-Log "Assembling tileset spritesheet..." "INFO"

$columns = 8  # 8 directions
$rows = 3     # 3 frames
$spritesheetWidth = $TileSize * $columns
$spritesheetHeight = $TileSize * $rows
$spritesheetPath = Join-Path $tilesetDir "${SwarmName}_tileset.png"

$spritesheet = New-Object System.Drawing.Bitmap $spritesheetWidth, $spritesheetHeight
$graphics = [System.Drawing.Graphics]::FromImage($spritesheet)
$graphics.Clear([System.Drawing.Color]::Transparent)

$row = 0
foreach ($frame in $frames) {
    $col = 0
    foreach ($direction in $directions) {
        $spriteKey = "${direction}_${frame}"
        if ($sprites.ContainsKey($spriteKey) -and (Test-Path $sprites[$spriteKey])) {
            $sprite = [System.Drawing.Image]::FromFile($sprites[$spriteKey])
            $x = $col * $TileSize
            $y = $row * $TileSize
            $graphics.DrawImage($sprite, $x, $y, $TileSize, $TileSize)
            $sprite.Dispose()
        }
        $col++
    }
    $row++
}

$spritesheet.Save($spritesheetPath)
$graphics.Dispose()
$spritesheet.Dispose()

Write-Log "Spritesheet created: $spritesheetPath" "SUCCESS"
Write-Log "  Dimensions: ${spritesheetWidth}x${spritesheetHeight}" "INFO"
Write-Log ""

# Create CDDA JSON creature definition
Write-Log "Creating CDDA creature definition..." "INFO"

$creatureJson = @{
    type = "MONSTER"
    id = $SwarmName
    name = @{
        str = "Bee Swarm"
        str_pl = "Bee Swarms"
    }
    description = "A swarm of aggressive bees. Individually weak, but dangerous in numbers."
    default_faction = "insect"
    species = @("INSECT")
    volume = "5000 ml"
    weight = "500 g"
    hp = 20
    speed = 100
    material = @("flesh")
    symbol = "b"
    color = "yellow"
    looks_like = "bee"
    phase = "gas"
    attack_cost = 100
    melee_damage = @{
        damage_type = "cut"
        amount = 2
    }
    melee_cut = 2
    dodge = 5
    armor = @{
        bash = 0
        cut = 0
        bullet = 0
        acid = 0
        fire = 0
        electric = 0
    }
    special_attacks = @(
        @{
            type = "sting"
            cooldown = 5
        }
    )
    flags = @("SEES", "HEARS", "SMELLS", "FLIES", "SWARMS", "POISON", "VENOM")
    death_drops = @{
        groups = @(
            @{
                subtype = "collection"
                items = @(
                    @{
                        item = "bee_stinger"
                        prob = 10
                        count = @(1, 3)
                    }
                )
            }
        )
    }
} | ConvertTo-Json -Depth 10

$creatureJsonPath = Join-Path $creatureDir "${SwarmName}.json"
$creatureJson | Set-Content -Path $creatureJsonPath -Encoding UTF8

Write-Log "Creature definition created: $creatureJsonPath" "SUCCESS"
Write-Log ""

# Create modinfo.json
$modinfo = @{
    type = "MOD_INFO"
    id = "bee_swarm"
    name = "Bee Swarm Creature"
    description = "Adds a bee swarm creature to CDDA"
    category = "creatures"
    dependencies = @("dda")
    version = "1.0"
} | ConvertTo-Json -Depth 10

$modinfoPath = Join-Path $modDir "modinfo.json"
$modinfo | Set-Content -Path $modinfoPath -Encoding UTF8

Write-Log "Mod info created: $modinfoPath" "SUCCESS"
Write-Log ""

# Create tileset definition
$tilesetDef = @"
# Bee Swarm Tileset Definition
# Place this in your CDDA tileset configuration

# Sprite definitions
"$SwarmName": {
    "sprite": "$spritesheetPath",
    "sprite_width": $TileSize,
    "sprite_height": $TileSize,
    "sprite_x": 0,
    "sprite_y": 0,
    "width": $TileSize,
    "height": $TileSize
}

# Animation frames
# Row 0: Idle (directions N, NE, E, SE, S, SW, W, NW)
# Row 1: Flying (directions N, NE, E, SE, S, SW, W, NW)
# Row 2: Attacking (directions N, NE, E, SE, S, SW, W, NW)
"@

$tilesetDefPath = Join-Path $tilesetDir "${SwarmName}_tileset.txt"
$tilesetDef | Set-Content -Path $tilesetDefPath -Encoding UTF8

Write-Log "Tileset definition created: $tilesetDefPath" "SUCCESS"
Write-Log ""

# Create README
$readme = @"
# Bee Swarm Creature for CDDA

## Installation

1. Copy the `bee_swarm` folder to your CDDA mods directory:
   - Windows: `%AppData%\Cataclysm-DDA\mods\`
   - Linux: `~/.cataclysm-dda/mods/`

2. Enable the mod in CDDA's mod selection menu

## Files

- `gfx/tileset/${SwarmName}_tileset.png` - Spritesheet with all frames
- `creatures/${SwarmName}.json` - Creature definition
- `modinfo.json` - Mod metadata

## Creature Stats

- **HP**: 20
- **Speed**: 100
- **Damage**: 2 cut
- **Special**: Sting attack (poison)
- **Flags**: Flies, Swarms, Poison, Venom

## Tileset Integration

Add to your tileset's sprite definitions:

```json
"$SwarmName": {
    "sprite": "gfx/tileset/${SwarmName}_tileset.png",
    "sprite_width": $TileSize,
    "sprite_height": $TileSize
}
```

## Credits

Generated using CDDA Bee Swarm Generator
"@

$readmePath = Join-Path $modDir "README.md"
$readme | Set-Content -Path $readmePath -Encoding UTF8

Write-Log "README created: $readmePath" "SUCCESS"
Write-Log ""

# Create metadata
$metadata = @{
    SwarmName = $SwarmName
    TileSize = $TileSize
    SwarmSize = $SwarmSize
    BeeCount = $beeCount
    SpriteCount = $sprites.Count
    GeneratedAt = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
    OutputDirectory = $OutputDir
    ModDirectory = $modDir
    WatchDirectory = $watchDir
} | ConvertTo-Json -Depth 10

$metadataPath = Join-Path $OutputDir "generation_metadata.json"
$metadata | Set-Content -Path $metadataPath -Encoding UTF8

Write-Log "═══════════════════════════════════════════════════════════" "INFO"
Write-Log "  Bee Swarm Generation Complete" "SUCCESS"
Write-Log "═══════════════════════════════════════════════════════════" "INFO"
Write-Log ""
Write-Log "CDDA mod created at: $modDir" "SUCCESS"
Write-Log "Spritesheet: $spritesheetPath" "SUCCESS"
Write-Log "Creature definition: $creatureJsonPath" "SUCCESS"
Write-Log "Log file: $logFile" "INFO"
Write-Log ""
Write-Log "Next steps:" "INFO"
Write-Log "  1. Copy the 'bee_swarm' folder to your CDDA mods directory" "INFO"
Write-Log "  2. Enable the mod in CDDA" "INFO"
Write-Log "  3. Configure your tileset to use the spritesheet" "INFO"
Write-Log ""

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Bee Swarm Generation Complete" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "CDDA mod created at: $modDir" -ForegroundColor Green
Write-Host "Spritesheet: $spritesheetPath" -ForegroundColor Green
Write-Host "Creature definition: $creatureJsonPath" -ForegroundColor Green
Write-Host "Log file: $logFile" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Copy the 'bee_swarm' folder to your CDDA mods directory" -ForegroundColor Gray
Write-Host "  2. Enable the mod in CDDA" -ForegroundColor Gray
Write-Host "  3. Configure your tileset to use the spritesheet" -ForegroundColor Gray
Write-Host ""

