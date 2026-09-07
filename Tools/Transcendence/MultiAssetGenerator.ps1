#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate multiple asset types simultaneously for multiple game formats.
    
.DESCRIPTION
    Creates a unified asset generation pipeline that can generate multiple asset types
    (tiles, particles, icons, FX, projectiles, etc.) in parallel for all supported game
    formats (Terraria, Elin, Qud, Starbound, Transcendence, CDDA).
    

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}
    Features:
    - Parallel generation of multiple asset types
    - Real-time progress display for each asset
    - Support for all game formats
    - Automatic export to requested formats
    - Comprehensive logging
    
.PARAMETER AssetTypes
    Array of asset types to generate: Tile, Particle, Icon, FX, Projectile, Ship, Creature, Texture, Model, Spritesheet
    
.PARAMETER GameTypes
    Array of game types to export to: Terraria, Elin, Qud, Starbound, Transcendence, CDDA, All
    
.PARAMETER AssetName
    Base name for the assets
    
.PARAMETER AssetDescription
    Description for AI generation
    
.PARAMETER OutputDir
    Output directory
    
.PARAMETER LaunchControlRoom
    Launch the Control Room GUI
    
.PARAMETER UseAI
    Use AI for asset generation
#>

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("Tile", "Particle", "Icon", "FX", "Projectile", "Ship", "Creature", "Texture", "Model", "Spritesheet")]
    [string[]]$AssetTypes = @("Tile", "Particle"),
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("Terraria", "Elin", "Qud", "Starbound", "Transcendence", "CDDA", "All")]
    [string[]]$GameTypes = @("All"),
    
    [Parameter(Mandatory=$true)]
    [string]$AssetName,
    
    [Parameter(Mandatory=$false)]
    [string]$AssetDescription = "",
    
    [Parameter(Mandatory=$false)]
    [string]$OutputDir = "GeneratedAssets",
    
    [Parameter(Mandatory=$false)]
    [switch]$LaunchControlRoom,
    
    [Parameter(Mandatory=$false)]
    [switch]$UseAI,
    
    [Parameter(Mandatory=$false)]
    [string]$OllamaModel = "llama3.2",
    
    [Parameter(Mandatory=$false)]
    [int]$TileSize = 16,
    
    [Parameter(Mandatory=$false)]
    [int]$FrameCount = 8,
    
    [Parameter(Mandatory=$false)]
    [int]$ParticleCount = 4,
    
    [Parameter(Mandatory=$false)]
    [int]$ParticleFrames = 4
)

$ErrorActionPreference = "Stop"
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

# Setup logging
$logDir = Join-Path $PSScriptRoot "Logs"
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

$logFile = Join-Path $logDir "MultiAsset_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
$script:LogFile = $logFile

function Write-Log {
    param(
        [string]$Message,
        [string]$Level = "INFO"
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss.fff"
    $logEntry = "[$timestamp] [$Level] $Message"
    
    $color = switch ($Level) {
        "ERROR" { "Red" }
        "WARN" { "Yellow" }
        "SUCCESS" { "Green" }
        "INFO" { "Cyan" }
        default { "White" }
    }
    Write-Host $logEntry -ForegroundColor $color
    
    try {
        Add-Content -Path $script:LogFile -Value $logEntry -Encoding UTF8 -ErrorAction SilentlyContinue
    } catch { }
}

Write-Log "═══════════════════════════════════════════════════════════" "INFO"
Write-Log "  Multi-Asset Generator" "INFO"
Write-Log "═══════════════════════════════════════════════════════════" "INFO"
Write-Log "Log file: $logFile" "INFO"
Write-Log ""
Write-Log "Asset Name: $AssetName" "INFO"
Write-Log "Asset Types: $($AssetTypes -join ', ')" "INFO"
Write-Log "Game Types: $($GameTypes -join ', ')" "INFO"
Write-Log "Output Directory: $OutputDir" "INFO"
Write-Log ""

# Expand "All" game types
if ($GameTypes -contains "All") {
    $GameTypes = @("Terraria", "Elin", "Qud", "Starbound", "Transcendence", "CDDA")
}

# Create output directory structure
$baseOutputDir = Join-Path $OutputDir $AssetName
if (-not (Test-Path $baseOutputDir)) {
    New-Item -ItemType Directory -Path $baseOutputDir -Force | Out-Null
}

# Results tracking
$script:Results = @{}
$script:Jobs = @()

# Asset generator mappings
# Comprehensive mapping of all asset types to generators for each game
# Uses AssetMakerAI.ps1 as fallback for types without dedicated generators
$assetGenerators = @{
    "Terraria" = @{
        "Tile" = "TerrariaPortalGenerator.ps1"     # Portal tiles
        "Portal" = "TerrariaPortalGenerator.ps1"   # Portal effects (dedicated)
        "Particle" = "ParticleEffectGenerator.ps1"
        "Icon" = "CrossGameSpritesheet.ps1"
        "FX" = "ParticleEffectGenerator.ps1"
        "Projectile" = "ParticleEffectGenerator.ps1"
        "Ship" = $null  # Not applicable for Terraria
        "Creature" = "AssetMakerAI.ps1"  # Use AI generator
        "Texture" = "AssetMakerAI.ps1"
        "Model" = "AssetMakerAI.ps1"
        "Spritesheet" = "CrossGameSpritesheet.ps1"
    }
    "Elin" = @{
        "Tile" = "ElinTextureGenerator.ps1"        # Dedicated Elin texture generator
        "Particle" = "ParticleEffectGenerator.ps1"
        "Icon" = "ElinSpellAssetGenerator.ps1"
        "FX" = "ElinSpellAssetGenerator.ps1"
        "Projectile" = "ElinSpellAssetGenerator.ps1"
        "Ship" = $null  # Not applicable for Elin
        "Creature" = "ElinTextureGenerator.ps1"    # Character textures
        "Texture" = "ElinTextureGenerator.ps1"     # General textures
        "Item" = "ElinTextureGenerator.ps1"        # Item textures
        "Portrait" = "ElinTextureGenerator.ps1"    # Portrait textures
        "Model" = "AssetMakerAI.ps1"
        "Spritesheet" = "ElinSpellAssetGenerator.ps1"
    }
    "Qud" = @{
        # QudTileAIGenerator.ps1 is GUI-based, use AssetMakerAI for headless tile generation
        "Tile" = "AssetMakerAI.ps1"
        "Particle" = "ParticleEffectGenerator.ps1"
        "Icon" = "AssetMakerAI.ps1"
        "FX" = "ParticleEffectGenerator.ps1"
        "Projectile" = "ParticleEffectGenerator.ps1"
        "Ship" = $null  # Not applicable for Qud
        "Creature" = "AssetMakerAI.ps1"
        "Texture" = "AssetMakerAI.ps1"
        "Model" = "AssetMakerAI.ps1"
        # ExportQudTiles.ps1 requires registry, use AssetMakerAI for headless spritesheet
        "Spritesheet" = "AssetMakerAI.ps1"
    }
    "Starbound" = @{
        "Tile" = "StarboundTileGenerator.ps1"         # Dedicated tile generator
        "Particle" = "StarboundParticleGenerator.ps1"  # Dedicated particle generator
        "Icon" = "StarboundAssetGenerator.ps1"
        "FX" = "StarboundParticleGenerator.ps1"  # FX uses particle system
        "Projectile" = "StarboundAssetGenerator.ps1"
        "Ship" = "StarboundAssetGenerator.ps1"
        "Creature" = "StarboundAssetGenerator.ps1"
        "Texture" = "StarboundAssetGenerator.ps1"
        "Model" = "StarboundAssetGenerator.ps1"
        "Spritesheet" = "CrossGameSpritesheet.ps1"
        "Animation" = "StarboundAnimationGenerator.ps1"  # Dedicated animation generator
        "Behavior" = "StarboundBehaviorGenerator.ps1"    # Dedicated behavior tree generator
        "Cursor" = "StarboundCursorGenerator.ps1"        # Dedicated cursor generator
        "Ship" = "StarboundShipGenerator.ps1"            # Dedicated ship generator
    }
    "CDDA" = @{
        "Tile" = "CDDABeeSwarmGenerator.ps1"
        "Particle" = $null  # CDDA doesn't use particles
        "Icon" = "AssetMakerAI.ps1"
        "FX" = $null  # CDDA doesn't use FX
        "Projectile" = $null  # CDDA doesn't use projectiles
        "Ship" = $null  # Not applicable for CDDA
        "Creature" = "CDDABeeSwarmGenerator.ps1"
        "Texture" = "AssetMakerAI.ps1"
        "Model" = $null  # CDDA is 2D only
        "Spritesheet" = "AssetMakerAI.ps1"
    }
    "Transcendence" = @{
        "Tile" = "AssetMakerAI.ps1"
        "Particle" = "ParticleEffectGenerator.ps1"
        "Icon" = "AssetMakerAI.ps1"
        "FX" = "ParticleEffectGenerator.ps1"
        "Projectile" = "ParticleEffectGenerator.ps1"
        "Ship" = "AssetMakerAI.ps1"  # Ship textures/models
        "Creature" = "AssetMakerAI.ps1"
        "Texture" = "AssetMakerAI.ps1"
        "Model" = "AssetMakerAI.ps1"
        "Spritesheet" = "CrossGameSpritesheet.ps1"
    }
    "Soulash" = @{
        "Creature" = "SoulashAssetGenerator.ps1"
        "Portrait" = "SoulashAssetGenerator.ps1"
        "Item" = "SoulashAssetGenerator.ps1"
        "Ability" = "SoulashAssetGenerator.ps1"
        "Tile" = "SoulashAssetGenerator.ps1"
        "Building" = "SoulashAssetGenerator.ps1"
        "Effect" = "SoulashAssetGenerator.ps1"
        "Spritesheet" = "SoulashAssetGenerator.ps1"
    }
}

# Unsupported combinations documentation (for user info)
$unsupportedCombinations = @{
    "Terraria_Ship" = "Terraria doesn't have ships - use Tile for transportation structures"
    "Elin_Ship" = "Elin doesn't have ships - use Creature or Tile instead"
    "Qud_Ship" = "Qud doesn't have ships - use Creature or Tile instead"
    "CDDA_Ship" = "CDDA doesn't have ships - use Creature for vehicles"
    "CDDA_Particle" = "CDDA is a roguelike and doesn't use particle effects"
    "CDDA_FX" = "CDDA is a roguelike and doesn't use visual effects"
    "CDDA_Projectile" = "CDDA is a roguelike and doesn't use projectile sprites"
    "CDDA_Model" = "CDDA is 2D-only and doesn't support 3D models"
}

# Function to check if a combination is supported
function Test-CombinationSupported {
    param([string]$GameType, [string]$AssetType)
    
    $key = "${GameType}_${AssetType}"
    if ($unsupportedCombinations.ContainsKey($key)) {
        return @{ Supported = $false; Reason = $unsupportedCombinations[$key] }
    }
    
    $generator = $assetGenerators[$GameType][$AssetType]
    if ($null -eq $generator) {
        return @{ Supported = $false; Reason = "No generator available for $AssetType in $GameType" }
    }
    
    return @{ Supported = $true; Generator = $generator }
}

# Asset dependency definitions
# Format: AssetType -> @(DependsOn) - asset types that must be generated first
$assetDependencies = @{
    "Terraria" = @{
        "Particle" = @("Tile")      # Particles often reference tile position
        "FX" = @("Tile")            # FX may reference tile
        "Projectile" = @("Icon")    # Projectiles may use icon as base
        "Spritesheet" = @("Icon", "Tile")  # Spritesheets assemble other assets
    }
    "Elin" = @{
        "FX" = @("Icon")            # FX may reference icon
        "Projectile" = @("Icon")    # Projectiles derive from icons
        "Spritesheet" = @("Icon", "FX")
    }
    "Starbound" = @{
        "Texture" = @("Model")      # Textures often baked from models
        "Spritesheet" = @("Icon", "Texture")
    }
    "Qud" = @{
        "Spritesheet" = @("Tile", "Icon")
    }
    "CDDA" = @{
        # CDDA has simpler asset structure
    }
    "Transcendence" = @{
        "Texture" = @("Model")      # Textures baked from 3D models
        "Spritesheet" = @("Texture")
    }
}

# Function to get dependencies for an asset
function Get-AssetDependencies {
    param([string]$GameType, [string]$AssetType)
    
    $deps = $assetDependencies[$GameType]
    if ($deps -and $deps[$AssetType]) {
        return $deps[$AssetType]
    }
    return @()
}

# Function to sort assets by dependency order
function Get-SortedAssetOrder {
    param(
        [string]$GameType,
        [string[]]$AssetTypes
    )
    
    $sorted = @()
    $pending = [System.Collections.ArrayList]::new()
    foreach ($at in $AssetTypes) { [void]$pending.Add($at) }
    
    $maxIterations = $AssetTypes.Count * 2  # Prevent infinite loops
    $iteration = 0
    
    while ($pending.Count -gt 0 -and $iteration -lt $maxIterations) {
        $iteration++
        
        foreach ($assetType in @($pending)) {
            $deps = Get-AssetDependencies -GameType $GameType -AssetType $assetType
            
            # Check if all dependencies are either already sorted or not in our list
            $allDepsResolved = $true
            foreach ($dep in $deps) {
                if ($dep -in $pending -and $dep -notin $sorted) {
                    $allDepsResolved = $false
                    break
                }
            }
            
            if ($allDepsResolved) {
                $sorted += $assetType
                [void]$pending.Remove($assetType)
            }
        }
    }
    
    # Add any remaining (circular deps or errors) at the end
    foreach ($remaining in $pending) {
        $sorted += $remaining
    }
    
    return $sorted
}

# Function to generate a single asset
function Generate-Asset {
    param(
        [string]$AssetType,
        [string]$GameType,
        [string]$AssetName,
        [string]$OutputDir,
        [hashtable]$Params
    )
    
    $generatorScript = $assetGenerators[$GameType][$AssetType]
    if (-not $generatorScript) {
        return @{
            Success = $false
            Message = "No generator found for $AssetType in $GameType"
            AssetType = $AssetType
            GameType = $GameType
        }
    }
    
    $scriptPath = Join-Path $PSScriptRoot $generatorScript
    if (-not (Test-Path $scriptPath)) {
        return @{
            Success = $false
            Message = "Generator script not found: $scriptPath"
            AssetType = $AssetType
            GameType = $GameType
        }
    }
    
    try {
        # Build arguments based on asset type and game
        $args = @()
        
        switch ($GameType) {
            "Terraria" {
                switch ($AssetType) {
                    { $_ -in @("Tile", "Portal") } {
                        # Use TerrariaPortalGenerator
                        $preset = switch ($Params.Description) {
                            { $_ -match "void|space|dark" } { "Void" }
                            { $_ -match "fire|flame|nether" } { "Fire" }
                            { $_ -match "ice|frost|cold" } { "Ice" }
                            { $_ -match "electric|lightning|shock" } { "Electric" }
                            { $_ -match "nature|green|plant" } { "Nature" }
                            { $_ -match "shadow|dark|purple" } { "Shadow" }
                            { $_ -match "light|bright|gold" } { "Light" }
                            default { "Void" }
                        }
                        $args = @(
                            "-PortalName", $AssetName,
                            "-Preset", $preset,
                            "-Description", $Params.Description,
                            "-OutputDir", (Join-Path $OutputDir "Terraria")
                        )
                    }
                    "Particle" {
                        $args = @(
                            "-EffectType", "Portal",
                            "-EffectName", "${AssetName}_Particles",
                            "-ParticleCount", $Params.ParticleCount,
                            "-FrameCount", $Params.ParticleFrames,
                            "-ParticleSize", 8,
                            "-OutputDir", (Join-Path $OutputDir "Terraria"),
                            "-GameFormat", "Terraria"
                        )
                    }
                    { $_ -in @("FX", "Projectile") } {
                        $args = @(
                            "-EffectType", $AssetType,
                            "-EffectName", "${AssetName}_${AssetType}",
                            "-ParticleCount", $Params.ParticleCount,
                            "-FrameCount", $Params.ParticleFrames,
                            "-ParticleSize", 8,
                            "-OutputDir", (Join-Path $OutputDir "Terraria"),
                            "-GameFormat", "Terraria"
                        )
                    }
                    { $_ -in @("Icon", "Spritesheet") } {
                        $args = @(
                            "-OutputDir", (Join-Path $OutputDir "Terraria"),
                            "-GameFormat", "Terraria",
                            "-TileSize", $Params.TileSize,
                            "-GenerateTextures",
                            "-TextureDescriptions", $Params.Description
                        )
                    }
                    { $_ -in @("Texture", "Model") } {
                        $args = @(
                            "-Action", ("Generate" + $AssetType),
                            "-AssetType", "Effect",
                            "-InputData", $Params.Description,
                            "-OutputPath", (Join-Path $OutputDir "Terraria"),
                            "-TextureSize", $Params.TileSize
                        )
                    }
                }
            }
            "Elin" {
                $args = @(
                    "-SpellDescription", $Params.Description,
                    "-SpellName", $AssetName,
                    "-OutputDir", (Join-Path $OutputDir "Elin")
                )
                if ($AssetType -eq "Icon") { $args += "-GenerateIcon" }
                if ($AssetType -eq "FX") { $args += @("-GenerateFX", "-FXFrames", $Params.FrameCount) }
                if ($AssetType -eq "Projectile") { $args += @("-GenerateProjectile", "-ProjectileFrames", $Params.ParticleFrames) }
                if ($AssetType -eq "Spritesheet") { $args += "-GenerateAll" }
            }
            "Qud" {
                switch ($AssetType) {
                    "Tile" {
                        $args = @(
                            "-Action", "GenerateTexture",
                            "-AssetType", "Other",
                            "-InputData", $Params.Description,
                            "-OutputPath", (Join-Path $OutputDir "Qud"),
                            "-TileSize", $Params.TileSize
                        )
                    }
                    "Spritesheet" {
                        $args = @(
                            "-Action", "AssembleSpritesheet",
                            "-AssetType", "Other",
                            "-InputData", $Params.Description,
                            "-OutputPath", (Join-Path $OutputDir "Qud"),
                            "-TileSize", $Params.TileSize
                        )
                    }
                }
            }
            "Starbound" {
                switch ($AssetType) {
                    "Tile" {
                        # Use StarboundTileGenerator
                        $preset = switch ($Params.Description) {
                            { $_ -match "protect|shield" } { "Protection" }
                            { $_ -match "platform|jump" } { "Platform" }
                            { $_ -match "ore|mine" } { "Ore" }
                            { $_ -match "brick|stone|wall" } { "Brick" }
                            { $_ -match "dirt|grass|natural" } { "Natural" }
                            { $_ -match "metal|iron|steel" } { "Metal" }
                            { $_ -match "glass|window" } { "Glass" }
                            { $_ -match "organic|flesh" } { "Organic" }
                            { $_ -match "tech|sci-fi|future" } { "Tech" }
                            default { "Basic" }
                        }
                        $args = @(
                            "-TileName", $AssetName,
                            "-Preset", $preset,
                            "-OutputDir", (Join-Path $OutputDir "Starbound"),
                            "-GenerateMaterial"
                        )
                    }
                    { $_ -in @("Particle", "FX") } {
                        # Use StarboundParticleGenerator for particles/FX
                        $preset = switch ($Params.Description) {
                            { $_ -match "fire|flame|burn" } { "Fire" }
                            { $_ -match "ice|frost|cold|freeze" } { "Ice" }
                            { $_ -match "poison|toxic|acid" } { "Poison" }
                            { $_ -match "electric|shock|lightning" } { "Electric" }
                            { $_ -match "blood|gore" } { "Blood" }
                            { $_ -match "sparkle|magic|star" } { "Sparkle" }
                            { $_ -match "smoke|steam|fog" } { "Smoke" }
                            { $_ -match "bubble|water" } { "Bubble" }
                            default { "Fire" }
                        }
                        $args = @(
                            "-ParticleName", $AssetName,
                            "-Preset", $preset,
                            "-OutputDir", (Join-Path $OutputDir "Starbound")
                        )
                    }
                    "Animation" {
                        # Use StarboundAnimationGenerator
                        $preset = switch ($Params.Description) {
                            { $_ -match "fire|flame|burn" } { "Fire" }
                            { $_ -match "ice|frost|cold" } { "Ice" }
                            { $_ -match "poison|toxic" } { "Poison" }
                            { $_ -match "electric|spark" } { "Electric" }
                            { $_ -match "smoke|steam" } { "Smoke" }
                            { $_ -match "explod" } { "Explosion" }
                            default { "Default" }
                        }
                        $args = @(
                            "-AnimationName", $AssetName,
                            "-Preset", $preset,
                            "-OutputDir", (Join-Path $OutputDir "Starbound"),
                            "-FrameCount", $Params.FrameCount.ToString()
                        )
                    }
                    "Behavior" {
                        # Use StarboundBehaviorGenerator
                        $preset = switch ($Params.Description) {
                            { $_ -match "boss" } { "Boss" }
                            { $_ -match "patrol" } { "Patrol" }
                            { $_ -match "guard" } { "Guard" }
                            { $_ -match "ranged|archer|shoot" } { "Ranged" }
                            { $_ -match "melee|close|punch" } { "Melee" }
                            { $_ -match "flee|run|escape" } { "Flee" }
                            { $_ -match "chase|follow" } { "Chase" }
                            { $_ -match "wander|roam" } { "Wander" }
                            default { "Default" }
                        }
                        $args = @(
                            "-BehaviorName", $AssetName,
                            "-Preset", $preset,
                            "-OutputDir", (Join-Path $OutputDir "Starbound")
                        )
                    }
                    "Cursor" {
                        # Use StarboundCursorGenerator
                        $preset = switch ($Params.Description) {
                            { $_ -match "pointer|arrow" } { "Pointer" }
                            { $_ -match "crosshair|aim|target" } { "Crosshair" }
                            { $_ -match "joystick|direction" } { "Joystick" }
                            { $_ -match "hand|grab" } { "Hand" }
                            { $_ -match "text|ibeam" } { "Text" }
                            { $_ -match "wait|load" } { "Wait" }
                            { $_ -match "move|drag" } { "Move" }
                            { $_ -match "resize" } { "Resize" }
                            default { "Default" }
                        }
                        $args = @(
                            "-CursorName", $AssetName,
                            "-Preset", $preset,
                            "-OutputDir", (Join-Path $OutputDir "Starbound")
                        )
                    }
                    "Ship" {
                        # Use StarboundShipGenerator
                        $preset = switch ($Params.Description) {
                            { $_ -match "human" } { "Human" }
                            { $_ -match "apex" } { "Apex" }
                            { $_ -match "avian" } { "Avian" }
                            { $_ -match "floran" } { "Floran" }
                            { $_ -match "glitch" } { "Glitch" }
                            { $_ -match "hylotl" } { "Hylotl" }
                            { $_ -match "novakid" } { "Novakid" }
                            default { "Generic" }
                        }
                        $args = @(
                            "-ShipName", $AssetName,
                            "-Race", $AssetName,
                            "-Preset", $preset,
                            "-OutputDir", (Join-Path $OutputDir "Starbound"),
                            "-IncludeAllTiers"
                        )
                    }
                    default {
                        $sbAssetType = switch ($AssetType) {
                            "Texture" { "Texture" }
                            "Model" { "Animation" }
                            "Spritesheet" { "Animation" }
                            default { "Texture" }
                        }
                        $args = @(
                            "-AssetType", $sbAssetType,
                            "-AssetName", $AssetName,
                            "-Description", $Params.Description,
                            "-OutputDir", (Join-Path $OutputDir "Starbound")
                        )
                    }
                }
            }
            "CDDA" {
                $args = @(
                    "-SwarmName", $AssetName,
                    "-TileSize", $Params.TileSize,
                    "-SwarmSize", "Medium",
                    "-OutputDir", (Join-Path $OutputDir "CDDA")
                )
            }
            "Transcendence" {
                $action = switch ($AssetType) {
                    "Texture" { "GenerateTexture" }
                    "Model" { "Generate3DModel" }
                    default { "GenerateTexture" }
                }
                $args = @(
                    "-Action", $action,
                    "-AssetType", "Ship",
                    "-InputData", $Params.Description,
                    "-OutputPath", (Join-Path $OutputDir "Transcendence"),
                    "-TextureSize", $Params.TileSize
                )
            }
        }
        
        # Execute generator
        $output = & $scriptPath @args 2>&1
        $exitCode = $LASTEXITCODE
        
        return @{
            Success = ($exitCode -eq 0)
            Message = if ($exitCode -eq 0) { "Generation complete" } else { "Generation failed: $output" }
            AssetType = $AssetType
            GameType = $GameType
            Output = $output
        }
    }
    catch {
        return @{
            Success = $false
            Message = "Error: $_"
            AssetType = $AssetType
            GameType = $GameType
        }
    }
}

# Launch Control Room if requested
if ($LaunchControlRoom) {
    $controlRoomScript = Join-Path $PSScriptRoot "AssetGeneratorControlRoom.ps1"
    if (Test-Path $controlRoomScript) {
        Write-Log "Launching Control Room in Multi-Asset Mode..." "INFO"
        
        $watchDir = Join-Path $baseOutputDir "watch"
        if (-not (Test-Path $watchDir)) {
            New-Item -ItemType Directory -Path $watchDir -Force | Out-Null
        }
        
        # Build command with multi-asset mode parameters
        $assetTypesStr = ($AssetTypes | ForEach-Object { "'$_'" }) -join ','
        $gameTypesStr = ($GameTypes | ForEach-Object { "'$_'" }) -join ','
        
        $controlRoomCmd = @(
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-File", "`"$controlRoomScript`"",
            "-MultiAssetMode",
            "-AssetName", "`"$AssetName`"",
            "-AssetType", ($AssetTypes[0]),
            "-AssetTypes", "@($assetTypesStr)",
            "-GameTypes", "@($gameTypesStr)",
            "-WatchDirectory", "`"$watchDir`"",
            "-AutoExport"
        )
        
        Start-Process -FilePath "pwsh" -ArgumentList $controlRoomCmd -WindowStyle Normal
        Write-Log "Control Room launched with Multi-Asset Mode" "SUCCESS"
        Write-Log "  Watching: $watchDir" "INFO"
        Start-Sleep -Seconds 2
    }
}

# Prepare parameters (ensure proper types)
$params = @{
    Description = if ([string]::IsNullOrWhiteSpace($AssetDescription)) { "Generated $AssetName asset" } else { $AssetDescription }
    TileSize = [int]$TileSize
    FrameCount = [int]$FrameCount
    ParticleCount = [int]$ParticleCount
    ParticleFrames = [int]$ParticleFrames
}

# Setup real-time file watching
Write-Log ""
Write-Log "Setting up file watchers for real-time monitoring..." "INFO"

$script:FileWatchers = @()
$script:GeneratedFiles = [System.Collections.Concurrent.ConcurrentDictionary[string, object]]::new()
$script:FileWatcherEvents = @()

# Create file watcher for each game type's output directory
foreach ($gameType in $GameTypes) {
    $gameOutputDir = Join-Path $baseOutputDir $gameType
    
    # Ensure directory exists for watcher
    if (-not (Test-Path $gameOutputDir)) {
        New-Item -ItemType Directory -Path $gameOutputDir -Force | Out-Null
    }
    
    try {
        $watcher = [System.IO.FileSystemWatcher]::new()
        $watcher.Path = $gameOutputDir
        $watcher.Filter = "*.*"
        $watcher.IncludeSubdirectories = $true
        $watcher.EnableRaisingEvents = $true
        $watcher.NotifyFilter = [System.IO.NotifyFilters]::FileName -bor [System.IO.NotifyFilters]::Size -bor [System.IO.NotifyFilters]::LastWrite
        
        # Register event handlers
        $createdAction = {
            $path = $Event.SourceEventArgs.FullPath
            $name = $Event.SourceEventArgs.Name
            $time = Get-Date -Format "HH:mm:ss"
            
            # Skip temp files and partial files
            if ($name -notmatch '\.(tmp|partial|downloading)$') {
                $size = 0
                try {
                    if (Test-Path $path) {
                        $size = (Get-Item $path -ErrorAction SilentlyContinue).Length
                    }
                } catch { }
                
                $sizeStr = if ($size -gt 1MB) { "$([math]::Round($size/1MB, 2)) MB" }
                          elseif ($size -gt 1KB) { "$([math]::Round($size/1KB, 2)) KB" }
                          else { "$size B" }
                
                Write-Host "  📄 [$time] NEW: $name ($sizeStr)" -ForegroundColor Green
            }
        }
        
        $changedAction = {
            $path = $Event.SourceEventArgs.FullPath
            $name = $Event.SourceEventArgs.Name
            
            # Only report significant changes (not temp files)
            if ($name -notmatch '\.(tmp|partial|downloading)$') {
                $size = 0
                try {
                    if (Test-Path $path) {
                        $size = (Get-Item $path -ErrorAction SilentlyContinue).Length
                    }
                } catch { }
                
                # Only report if file has meaningful content
                if ($size -gt 0) {
                    $sizeStr = if ($size -gt 1MB) { "$([math]::Round($size/1MB, 2)) MB" }
                              elseif ($size -gt 1KB) { "$([math]::Round($size/1KB, 2)) KB" }
                              else { "$size B" }
                    Write-Host "  📝 UPDATED: $name ($sizeStr)" -ForegroundColor Yellow
                }
            }
        }
        
        $event1 = Register-ObjectEvent -InputObject $watcher -EventName Created -Action $createdAction
        $event2 = Register-ObjectEvent -InputObject $watcher -EventName Changed -Action $changedAction
        
        $script:FileWatchers += $watcher
        $script:FileWatcherEvents += $event1
        $script:FileWatcherEvents += $event2
        
        Write-Log "  Watching: $gameOutputDir" "INFO"
    }
    catch {
        Write-Log "  Warning: Could not create watcher for $gameType - $_" "WARN"
    }
}

Write-Log ""

# Generate all assets in parallel
Write-Log ""
Write-Log "Starting parallel asset generation..." "INFO"
Write-Log "  (Files will appear below as they are generated)"
Write-Log ""

$jobResults = @{}
$skippedCombinations = @{}

# Pre-validate all combinations and show summary
Write-Log "Validating asset/game combinations..." "INFO"
$supportedCount = 0
$skippedCount = 0

foreach ($gameType in $GameTypes) {
    foreach ($assetType in $AssetTypes) {
        $key = "${gameType}_${assetType}"
        $check = Test-CombinationSupported -GameType $gameType -AssetType $assetType
        
        if (-not $check.Supported) {
            $skippedCombinations[$key] = $check.Reason
            $skippedCount++
        } else {
            $supportedCount++
        }
    }
}

if ($skippedCount -gt 0) {
    Write-Log "  Supported: $supportedCount combinations" "SUCCESS"
    Write-Log "  Skipped: $skippedCount unsupported combinations" "WARN"
    Write-Log ""
    Write-Log "Unsupported combinations (will be skipped):" "WARN"
    foreach ($key in ($skippedCombinations.Keys | Sort-Object)) {
        $parts = $key -split '_'
        Write-Log "  ⚠ $($parts[0]) - $($parts[1]): $($skippedCombinations[$key])" "WARN"
    }
    Write-Log ""
}

# Track completed jobs for dependency checking
$script:CompletedJobKeys = [System.Collections.Concurrent.ConcurrentDictionary[string, bool]]::new()

foreach ($gameType in $GameTypes) {
    # Sort asset types by dependency order for this game
    $sortedAssetTypes = Get-SortedAssetOrder -GameType $gameType -AssetTypes $AssetTypes
    
    if ($sortedAssetTypes.Count -ne $AssetTypes.Count) {
        Write-Log "  Note: Reordered assets for $gameType based on dependencies" "INFO"
    }
    
    foreach ($assetType in $sortedAssetTypes) {
        $key = "${gameType}_${assetType}"
        
        # Skip unsupported combinations
        if ($skippedCombinations.ContainsKey($key)) {
            continue
        }
        
        # Check dependencies
        $deps = Get-AssetDependencies -GameType $gameType -AssetType $assetType
        $pendingDeps = @()
        foreach ($dep in $deps) {
            $depKey = "${gameType}_${dep}"
            if ($dep -in $AssetTypes -and -not $skippedCombinations.ContainsKey($depKey)) {
                $pendingDeps += $dep
            }
        }
        
        if ($pendingDeps.Count -gt 0) {
            Write-Log "Starting: $assetType for $gameType (depends on: $($pendingDeps -join ', '))" "INFO"
        } else {
            Write-Log "Starting: $assetType for $gameType" "INFO"
        }
        
        $job = Start-Job -ScriptBlock {
            param($scriptRoot, $assetType, $gameType, $assetName, $outputDir, $description, $tileSize, $frameCount, $particleCount, $particleFrames, $assetGenerators)
            
            $ErrorActionPreference = "Stop"
            
            # Reconstruct params hashtable from individual parameters
            $params = @{
                Description = $description
                TileSize = [int]$tileSize
                FrameCount = [int]$frameCount
                ParticleCount = [int]$particleCount
                ParticleFrames = [int]$particleFrames
            }
            
            # Import the Generate-Asset function logic
            $generatorScript = $assetGenerators[$gameType][$assetType]
            if (-not $generatorScript) {
                return @{
                    Success = $false
                    Message = "No generator found for $assetType in $gameType"
                    AssetType = $assetType
                    GameType = $gameType
                }
            }
            
            $scriptPath = Join-Path $scriptRoot $generatorScript
            if (-not (Test-Path $scriptPath)) {
                return @{
                    Success = $false
                    Message = "Generator script not found: $scriptPath"
                    AssetType = $assetType
                    GameType = $gameType
                }
            }
            
            try {
                # Build arguments
                $args = @()
                
                switch ($gameType) {
                    "Terraria" {
                        switch ($assetType) {
                            { $_ -in @("Tile", "Portal") } {
                                # Use TerrariaPortalGenerator
                                $preset = switch -Regex ($params.Description) {
                                    "void|space|dark" { "Void" }
                                    "fire|flame|nether" { "Fire" }
                                    "ice|frost|cold" { "Ice" }
                                    "electric|lightning|shock" { "Electric" }
                                    "nature|green|plant" { "Nature" }
                                    "shadow|dark|purple" { "Shadow" }
                                    "light|bright|gold" { "Light" }
                                    default { "Void" }
                                }
                                $args = @(
                                    "-PortalName", $assetName,
                                    "-Preset", $preset,
                                    "-Description", $params.Description,
                                    "-OutputDir", (Join-Path $outputDir "Terraria"),
                                )
                            }
                            "Particle" {
                                $args = @(
                                    "-EffectType", "Portal",
                                    "-EffectName", "${assetName}_Particles",
                                    "-ParticleCount", $params.ParticleCount.ToString(),
                                    "-FrameCount", $params.ParticleFrames.ToString(),
                                    "-ParticleSize", "8",
                                    "-OutputDir", (Join-Path $outputDir "Terraria"),
                                    "-GameFormat", "Terraria"
                                )
                            }
                            { $_ -in @("FX", "Projectile") } {
                                $args = @(
                                    "-EffectType", $assetType,
                                    "-EffectName", "${assetName}_${assetType}",
                                    "-ParticleCount", $params.ParticleCount.ToString(),
                                    "-FrameCount", $params.ParticleFrames.ToString(),
                                    "-ParticleSize", "8",
                                    "-OutputDir", (Join-Path $outputDir "Terraria"),
                                    "-GameFormat", "Terraria"
                                )
                            }
                            { $_ -in @("Icon", "Spritesheet") } {
                                $args = @(
                                    "-OutputDir", (Join-Path $outputDir "Terraria"),
                                    "-GameFormat", "Terraria",
                                    "-TileSize", $params.TileSize.ToString(),
                                    "-GenerateTextures",
                                    "-TextureDescriptions", $params.Description
                                )
                            }
                            { $_ -in @("Texture", "Model") } {
                                $args = @(
                                    "-Action", ("Generate" + $assetType),
                                    "-AssetType", "Effect",
                                    "-InputData", $params.Description,
                                    "-OutputPath", (Join-Path $outputDir "Terraria"),
                                    "-TextureSize", $params.TileSize.ToString()
                                )
                            }
                        }
                    }
                    "Elin" {
                        $args = @(
                            "-SpellDescription", $params.Description,
                            "-SpellName", $assetName,
                            "-OutputDir", (Join-Path $outputDir "Elin")
                        )
                        if ($assetType -eq "Icon") { $args += "-GenerateIcon" }
                        if ($assetType -eq "FX") { $args += @("-GenerateFX", "-FXFrames", $params.FrameCount.ToString()) }
                        if ($assetType -eq "Projectile") { $args += @("-GenerateProjectile", "-ProjectileFrames", $params.ParticleFrames.ToString()) }
                        if ($assetType -eq "Spritesheet") { $args += "-GenerateAll" }
                    }
                    "Qud" {
                        switch ($assetType) {
                            "Tile" {
                                # QudTileAIGenerator is GUI-based; use AssetMakerAI for headless generation
                                $args = @(
                                    "-Action", "GenerateTexture",
                                    "-AssetType", "Other",
                                    "-InputData", $params.Description,
                                    "-OutputPath", (Join-Path $outputDir "Qud"),
                                    "-TileSize", $params.TileSize.ToString()
                                )
                            }
                            "Spritesheet" {
                                # ExportQudTiles requires registry - use AssetMakerAI instead
                                $args = @(
                                    "-Action", "AssembleSpritesheet",
                                    "-AssetType", "Other",
                                    "-InputData", $params.Description,
                                    "-OutputPath", (Join-Path $outputDir "Qud"),
                                    "-TileSize", $params.TileSize.ToString()
                                )
                            }
                        }
                    }
                    "Starbound" {
                        switch ($assetType) {
                            "Tile" {
                                # Use StarboundTileGenerator
                                $preset = switch -Regex ($params.Description) {
                                    "protect|shield" { "Protection" }
                                    "platform|jump" { "Platform" }
                                    "ore|mine" { "Ore" }
                                    "brick|stone|wall" { "Brick" }
                                    "dirt|grass|natural" { "Natural" }
                                    "metal|iron|steel" { "Metal" }
                                    "glass|window" { "Glass" }
                                    "organic|flesh" { "Organic" }
                                    "tech|sci-fi|future" { "Tech" }
                                    default { "Basic" }
                                }
                                $args = @(
                                    "-TileName", $assetName,
                                    "-Preset", $preset,
                                    "-OutputDir", (Join-Path $outputDir "Starbound"),
                                    "-GenerateMaterial"
                                )
                            }
                            { $_ -in @("Particle", "FX") } {
                                # Use StarboundParticleGenerator for particles/FX
                                $preset = switch -Regex ($params.Description) {
                                    "fire|flame|burn" { "Fire" }
                                    "ice|frost|cold|freeze" { "Ice" }
                                    "poison|toxic|acid" { "Poison" }
                                    "electric|shock|lightning" { "Electric" }
                                    "blood|gore" { "Blood" }
                                    "sparkle|magic|star" { "Sparkle" }
                                    "smoke|steam|fog" { "Smoke" }
                                    "bubble|water" { "Bubble" }
                                    default { "Fire" }
                                }
                                $args = @(
                                    "-ParticleName", $assetName,
                                    "-Preset", $preset,
                                    "-OutputDir", (Join-Path $outputDir "Starbound")
                                )
                            }
                            "Animation" {
                                # Use StarboundAnimationGenerator
                                $preset = switch -Regex ($params.Description) {
                                    "fire|flame|burn" { "Fire" }
                                    "ice|frost|cold" { "Ice" }
                                    "poison|toxic" { "Poison" }
                                    "electric|spark" { "Electric" }
                                    "smoke|steam" { "Smoke" }
                                    "explod" { "Explosion" }
                                    default { "Default" }
                                }
                                $args = @(
                                    "-AnimationName", $assetName,
                                    "-Preset", $preset,
                                    "-OutputDir", (Join-Path $outputDir "Starbound"),
                                    "-FrameCount", $params.FrameCount.ToString()
                                )
                            }
                            "Behavior" {
                                # Use StarboundBehaviorGenerator
                                $preset = switch -Regex ($params.Description) {
                                    "boss" { "Boss" }
                                    "patrol" { "Patrol" }
                                    "guard" { "Guard" }
                                    "ranged|archer|shoot" { "Ranged" }
                                    "melee|close|punch" { "Melee" }
                                    "flee|run|escape" { "Flee" }
                                    "chase|follow" { "Chase" }
                                    "wander|roam" { "Wander" }
                                    default { "Default" }
                                }
                                $args = @(
                                    "-BehaviorName", $assetName,
                                    "-Preset", $preset,
                                    "-OutputDir", (Join-Path $outputDir "Starbound")
                                )
                            }
                            "Cursor" {
                                # Use StarboundCursorGenerator
                                $preset = switch -Regex ($params.Description) {
                                    "pointer|arrow" { "Pointer" }
                                    "crosshair|aim|target" { "Crosshair" }
                                    "joystick|direction" { "Joystick" }
                                    "hand|grab" { "Hand" }
                                    "text|ibeam" { "Text" }
                                    "wait|load" { "Wait" }
                                    "move|drag" { "Move" }
                                    "resize" { "Resize" }
                                    default { "Default" }
                                }
                                $args = @(
                                    "-CursorName", $assetName,
                                    "-Preset", $preset,
                                    "-OutputDir", (Join-Path $outputDir "Starbound")
                                )
                            }
                            "Ship" {
                                # Use StarboundShipGenerator
                                $preset = switch -Regex ($params.Description) {
                                    "human" { "Human" }
                                    "apex" { "Apex" }
                                    "avian" { "Avian" }
                                    "floran" { "Floran" }
                                    "glitch" { "Glitch" }
                                    "hylotl" { "Hylotl" }
                                    "novakid" { "Novakid" }
                                    default { "Generic" }
                                }
                                $args = @(
                                    "-ShipName", $assetName,
                                    "-Race", $assetName,
                                    "-Preset", $preset,
                                    "-OutputDir", (Join-Path $outputDir "Starbound"),
                                    "-IncludeAllTiers"
                                )
                            }
                            default {
                                # Map asset types to StarboundAssetGenerator's expected types
                                $sbAssetType = switch ($assetType) {
                                    "Texture" { "Texture" }
                                    "Model" { "Animation" }
                                    "Spritesheet" { "Animation" }
                                    default { "Texture" }
                                }
                                $args = @(
                                    "-AssetType", $sbAssetType,
                                    "-AssetName", $assetName,
                                    "-Description", $params.Description,
                                    "-OutputDir", (Join-Path $outputDir "Starbound")
                                )
                            }
                        }
                    }
                    "CDDA" {
                        $args = @(
                            "-SwarmName", $assetName,
                            "-TileSize", $params.TileSize.ToString(),
                            "-SwarmSize", "Medium",
                            "-OutputDir", (Join-Path $outputDir "CDDA")
                        )
                    }
                    "Transcendence" {
                        # Map asset types to AssetMakerAI actions
                        $action = switch ($assetType) {
                            "Texture" { "GenerateTexture" }
                            "Model" { "Generate3DModel" }
                            default { "GenerateTexture" }
                        }
                        $args = @(
                            "-Action", $action,
                            "-AssetType", "Ship",
                            "-InputData", $params.Description,
                            "-OutputPath", (Join-Path $outputDir "Transcendence"),
                            "-TextureSize", $params.TileSize.ToString()
                        )
                    }
                }
                
                # Execute with error capture
                $output = & $scriptPath @args 2>&1
                $exitCode = $LASTEXITCODE
                
                # Separate stdout and stderr
                $stdout = ($output | Where-Object { $_ -isnot [System.Management.Automation.ErrorRecord] }) -join "`n"
                $stderr = ($output | Where-Object { $_ -is [System.Management.Automation.ErrorRecord] }) -join "`n"
                
                # Analyze errors for common issues and suggestions
                $suggestion = ""
                if ($stderr -match "cannot find path|FileNotFound") {
                    $suggestion = "Check if required input files exist and paths are correct"
                } elseif ($stderr -match "Ollama|connection refused|11434") {
                    $suggestion = "Ensure Ollama is running (ollama serve) and accessible"
                } elseif ($stderr -match "parameter|argument") {
                    $suggestion = "Generator script parameter mismatch - check script compatibility"
                } elseif ($stderr -match "permission|access denied") {
                    $suggestion = "Check file/folder permissions for output directory"
                } elseif ($stderr -match "blender|python") {
                    $suggestion = "Ensure Blender/Python is installed and in PATH"
                }
                
                return @{
                    Success = ($exitCode -eq 0 -and [string]::IsNullOrWhiteSpace($stderr))
                    Message = if ($exitCode -eq 0 -and [string]::IsNullOrWhiteSpace($stderr)) { "Generation complete" } else { "Generation failed (exit: $exitCode)" }
                    AssetType = $assetType
                    GameType = $gameType
                    Output = $stdout
                    ErrorOutput = $stderr
                    ExitCode = $exitCode
                    Suggestion = $suggestion
                    Arguments = ($args -join ' ')
                    ScriptPath = $scriptPath
                }
            }
            catch {
                # Capture full exception details
                $errorMessage = $_.Exception.Message
                $stackTrace = $_.ScriptStackTrace
                $errorType = $_.Exception.GetType().Name
                $errorLine = $_.InvocationInfo.ScriptLineNumber
                $errorPosition = $_.InvocationInfo.PositionMessage
                
                # Analyze error for suggestions
                $suggestion = ""
                if ($errorMessage -match "cannot find path|FileNotFound") {
                    $suggestion = "Check if generator script exists at: $scriptPath"
                } elseif ($errorMessage -match "null|NullReference") {
                    $suggestion = "Check if all required parameters are provided"
                } elseif ($errorMessage -match "timeout|connection") {
                    $suggestion = "Check network connectivity and service availability"
                }
                
                return @{
                    Success = $false
                    Message = "Exception: $errorType - $errorMessage"
                    AssetType = $assetType
                    GameType = $gameType
                    ErrorType = $errorType
                    ErrorOutput = $errorMessage
                    StackTrace = $stackTrace
                    ErrorLine = $errorLine
                    ErrorPosition = $errorPosition
                    Suggestion = $suggestion
                    Arguments = ($args -join ' ')
                    ScriptPath = $scriptPath
                }
            }
        } -ArgumentList $PSScriptRoot, $assetType, $gameType, $AssetName, $baseOutputDir, $params.Description, $params.TileSize, $params.FrameCount, $params.ParticleCount, $params.ParticleFrames, $assetGenerators
        
        if ($job) {
            $script:Jobs += $job
            $jobResults[$key] = $job
        }
    }
}

# Monitor jobs and display results in real-time
Write-Log ""
Write-Log "Monitoring generation progress..." "INFO"
Write-Log ""

$completed = 0
$total = $script:Jobs.Count
$results = @{}
$startTime = Get-Date

# Create a hashtable to track which assets have been reported
$reported = @{}

# ETA tracking
$script:JobStartTimes = @{}
$script:JobCompletionTimes = @()

# Record start times for all jobs
foreach ($key in $jobResults.Keys) {
    $script:JobStartTimes[$key] = $startTime
}

# Function to calculate ETA
function Get-ETAString {
    param(
        [int]$Completed,
        [int]$Total,
        [double[]]$CompletionTimes
    )
    
    if ($Completed -eq 0 -or $CompletionTimes.Count -eq 0) {
        return "Calculating..."
    }
    
    $remaining = $Total - $Completed
    if ($remaining -le 0) {
        return "Complete"
    }
    
    # Use average of last 5 completion times (or all if less than 5)
    $recentTimes = $CompletionTimes | Select-Object -Last 5
    $avgTime = ($recentTimes | Measure-Object -Average).Average
    
    $etaSeconds = $remaining * $avgTime
    
    if ($etaSeconds -lt 60) {
        return "~$([math]::Ceiling($etaSeconds))s"
    } elseif ($etaSeconds -lt 3600) {
        $mins = [math]::Floor($etaSeconds / 60)
        $secs = [math]::Ceiling($etaSeconds % 60)
        return "~${mins}m ${secs}s"
    } else {
        $hours = [math]::Floor($etaSeconds / 3600)
        $mins = [math]::Ceiling(($etaSeconds % 3600) / 60)
        return "~${hours}h ${mins}m"
    }
}

while ($completed -lt $total) {
    Start-Sleep -Milliseconds 300
    
    foreach ($key in $jobResults.Keys) {
        $job = $jobResults[$key]
        
        if ($job.State -eq "Completed" -and -not $results.ContainsKey($key)) {
            $jobEndTime = Get-Date
            $result = Receive-Job $job
            Remove-Job $job
            
            $results[$key] = $result
            $completed++
            
            # Track job completion time for ETA calculation
            $jobDuration = ($jobEndTime - $script:JobStartTimes[$key]).TotalSeconds
            $script:JobCompletionTimes += $jobDuration
            
            # Show result immediately
            $elapsed = ((Get-Date) - $startTime).TotalSeconds
            $assetKey = "$($result.GameType) - $($result.AssetType)"
            
            if ($result.Success) {
                Write-Log "✓ $assetKey - Complete (${elapsed}s)" "SUCCESS"
                
                # Show generated files if available
                $gameOutputDir = Join-Path $baseOutputDir $result.GameType
                if (Test-Path $gameOutputDir) {
                    $files = Get-ChildItem -Path $gameOutputDir -Recurse -File -ErrorAction SilentlyContinue
                    if ($files.Count -gt 0) {
                        Write-Log "  Generated $($files.Count) file(s)" "INFO"
                        # Show first few files
                        $files | Select-Object -First 3 | ForEach-Object {
                            $relative = $_.FullName.Replace((Resolve-Path $baseOutputDir).Path + "\", "")
                            Write-Log "    - $relative" "INFO"
                        }
                        if ($files.Count -gt 3) {
                            Write-Log "    ... and $($files.Count - 3) more" "INFO"
                        }
                    }
                }
            } else {
                Write-Log "✗ $assetKey - Failed: $($result.Message)" "ERROR"
                
                # Show detailed error information
                if ($result.ErrorOutput) {
                    Write-Log "  Error Details:" "ERROR"
                    # Split error output and show first few lines
                    $errorLines = ($result.ErrorOutput -split "`n") | Where-Object { $_.Trim() } | Select-Object -First 5
                    foreach ($line in $errorLines) {
                        Write-Log "    $line" "ERROR"
                    }
                }
                
                # Show stack trace for debugging
                if ($result.StackTrace) {
                    Write-Log "  Stack Trace:" "WARN"
                    $traceLines = ($result.StackTrace -split "`n") | Where-Object { $_.Trim() } | Select-Object -First 3
                    foreach ($line in $traceLines) {
                        Write-Log "    $line" "WARN"
                    }
                }
                
                # Show suggestion if available
                if ($result.Suggestion) {
                    Write-Log "  💡 Suggestion: $($result.Suggestion)" "WARN"
                }
                
                # Show the command that was attempted
                if ($result.ScriptPath -and $result.Arguments) {
                    Write-Log "  Command: $($result.ScriptPath) $($result.Arguments)" "INFO"
                }
            }
        }
        elseif ($job.State -eq "Failed" -and -not $results.ContainsKey($key)) {
            $assetType = ($key -split '_')[1]
            $gameType = ($key -split '_')[0]
            
            # Try to get error details from the failed job
            $jobError = $null
            try {
                $jobError = Receive-Job $job -ErrorAction SilentlyContinue 2>&1
            } catch { }
            
            $errorMessage = "PowerShell job crashed"
            $suggestion = "Check if generator script has syntax errors or missing dependencies"
            
            if ($jobError) {
                $errorMessage = ($jobError | Out-String).Trim()
                if ($errorMessage.Length -gt 200) {
                    $errorMessage = $errorMessage.Substring(0, 200) + "..."
                }
            }
            
            $results[$key] = @{
                Success = $false
                Message = "Job crashed: $errorMessage"
                AssetType = $assetType
                GameType = $gameType
                ErrorOutput = $errorMessage
                Suggestion = $suggestion
            }
            $completed++
            
            Write-Log "✗ $gameType - $assetType - Job crashed" "ERROR"
            if ($errorMessage) {
                Write-Log "  Error: $errorMessage" "ERROR"
            }
            Write-Log "  💡 Suggestion: $suggestion" "WARN"
            
            try { Remove-Job $job -Force -ErrorAction SilentlyContinue } catch { }
        }
    }
    
    # Show progress bar with ETA
    $percent = [Math]::Floor(($completed / $total) * 100)
    $elapsed = ((Get-Date) - $startTime).TotalSeconds
    $elapsedStr = "$([math]::Round($elapsed, 1))s"
    
    # Calculate ETA
    $eta = Get-ETAString -Completed $completed -Total $total -CompletionTimes $script:JobCompletionTimes
    
    # Build progress bar
    $barLength = 30
    $filled = [Math]::Floor(($percent / 100) * $barLength)
    $bar = "[" + ("=" * $filled) + (" " * ($barLength - $filled)) + "]"
    
    # Format: [========          ] 3/10 (30%) | Elapsed: 15.2s | ETA: ~45s
    $progressLine = "$bar $completed/$total ($percent%) | Elapsed: $elapsedStr | ETA: $eta"
    
    # Pad to overwrite previous line
    $progressLine = $progressLine.PadRight(80)
    
    Write-Host "`r$progressLine" -NoNewline -ForegroundColor Cyan
}

Write-Host "" # New line after progress
$totalTime = ((Get-Date) - $startTime).TotalSeconds
Write-Log "All jobs completed in ${totalTime}s" "SUCCESS"
Write-Log ""

# Summary
Write-Log ""
Write-Log "═══════════════════════════════════════════════════════════" "INFO"
Write-Log "  Generation Summary" "INFO"
Write-Log "═══════════════════════════════════════════════════════════" "INFO"
Write-Log ""

$successCount = ($results.Values | Where-Object { $_.Success }).Count
$failCount = ($results.Values | Where-Object { -not $_.Success }).Count

Write-Log "Total: $total assets" "INFO"
Write-Log "Successful: $successCount" "SUCCESS"
Write-Log "Failed: $failCount" $(if ($failCount -gt 0) { "ERROR" } else { "INFO" })
Write-Log ""

# Detailed results
Write-Log "Detailed Results:" "INFO"
Write-Log ""

$failedResults = @()
foreach ($key in ($results.Keys | Sort-Object)) {
    $result = $results[$key]
    $status = if ($result.Success) { "✓" } else { "✗" }
    
    Write-Log "  $status $($result.GameType) - $($result.AssetType): $($result.Message)" $(if ($result.Success) { "SUCCESS" } else { "ERROR" })
    
    # Collect failed results for detailed error log
    if (-not $result.Success) {
        $failedResults += $result
    }
}

# Write detailed error log if there are failures
if ($failedResults.Count -gt 0) {
    $errorLogFile = Join-Path $logDir "MultiAsset_Errors_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
    
    Write-Log ""
    Write-Log "═══════════════════════════════════════════════════════════" "WARN"
    Write-Log "  Error Details (see: $errorLogFile)" "WARN"
    Write-Log "═══════════════════════════════════════════════════════════" "WARN"
    Write-Log ""
    
    $errorContent = @()
    $errorContent += "Multi-Asset Generator Error Report"
    $errorContent += "Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    $errorContent += "Asset Name: $AssetName"
    $errorContent += "=" * 60
    $errorContent += ""
    
    foreach ($result in $failedResults) {
        $errorContent += "FAILED: $($result.GameType) - $($result.AssetType)"
        $errorContent += "-" * 40
        $errorContent += "Message: $($result.Message)"
        
        if ($result.ErrorType) {
            $errorContent += "Error Type: $($result.ErrorType)"
        }
        if ($result.ErrorOutput) {
            $errorContent += "Error Output:"
            $errorContent += $result.ErrorOutput
        }
        if ($result.StackTrace) {
            $errorContent += "Stack Trace:"
            $errorContent += $result.StackTrace
        }
        if ($result.ErrorPosition) {
            $errorContent += "Position: $($result.ErrorPosition)"
        }
        if ($result.ScriptPath) {
            $errorContent += "Script: $($result.ScriptPath)"
        }
        if ($result.Arguments) {
            $errorContent += "Arguments: $($result.Arguments)"
        }
        if ($result.Suggestion) {
            $errorContent += "Suggestion: $($result.Suggestion)"
        }
        $errorContent += ""
        $errorContent += "=" * 60
        $errorContent += ""
        
        # Also show summary in console
        Write-Log "  $($result.GameType) - $($result.AssetType):" "ERROR"
        if ($result.Suggestion) {
            Write-Log "    💡 $($result.Suggestion)" "WARN"
        }
    }
    
    # Write error log file
    try {
        $errorContent | Out-File -FilePath $errorLogFile -Encoding UTF8
        Write-Log ""
        Write-Log "Detailed error log written to: $errorLogFile" "INFO"
    } catch {
        Write-Log "Failed to write error log: $_" "WARN"
    }
}

Write-Log ""
Write-Log "Output directory: $baseOutputDir" "INFO"
Write-Log "Log file: $logFile" "INFO"
Write-Log ""

# Show file structure organized by game type
Write-Log "Generated file structure:" "INFO"
Write-Log ""

if (Test-Path $baseOutputDir) {
    foreach ($gameType in ($GameTypes | Sort-Object)) {
        $gameDir = Join-Path $baseOutputDir $gameType
        if (Test-Path $gameDir) {
            Write-Log "  ${gameType}:" "INFO"
            $files = Get-ChildItem -Path $gameDir -Recurse -File -ErrorAction SilentlyContinue
            if ($files.Count -gt 0) {
                $files | ForEach-Object {
                    $relative = $_.FullName.Replace((Resolve-Path $baseOutputDir).Path + "\", "")
                    $size = [math]::Round($_.Length / 1KB, 2)
                    Write-Log "    $relative ($size KB)" "INFO"
                }
            } else {
                Write-Log "    (no files generated)" "WARN"
            }
            Write-Log ""
        }
    }
    
    # Show summary statistics
    $allFiles = Get-ChildItem -Path $baseOutputDir -Recurse -File -ErrorAction SilentlyContinue
    $totalSize = ($allFiles | Measure-Object -Property Length -Sum).Sum / 1MB
    Write-Log "Total files: $($allFiles.Count)" "INFO"
    Write-Log "Total size: $([math]::Round($totalSize, 2)) MB" "INFO"
}

# ============================================================
# Generate Summary Reports (JSON and HTML)
# ============================================================

Write-Log ""
Write-Log "Generating summary reports..." "INFO"

# Build report data
$reportData = @{
    generationDate = (Get-Date).ToString("o")
    assetName = $AssetName
    assetDescription = $AssetDescription
    totalAssets = $total
    successful = $successCount
    failed = $failCount
    totalTime = [math]::Round($totalTime, 2)
    averageTimePerAsset = if ($total -gt 0) { [math]::Round($totalTime / $total, 2) } else { 0 }
    outputDirectory = $baseOutputDir
    assets = @()
}

# Add asset details
foreach ($key in ($results.Keys | Sort-Object)) {
    $result = $results[$key]
    $gameOutputDir = Join-Path $baseOutputDir $result.GameType
    $files = @()
    $totalFileSize = 0
    
    if (Test-Path $gameOutputDir) {
        $gameFiles = Get-ChildItem -Path $gameOutputDir -Recurse -File -ErrorAction SilentlyContinue
        foreach ($file in $gameFiles) {
            $relativePath = $file.FullName.Replace((Resolve-Path $baseOutputDir).Path + "\", "")
            $files += $relativePath
            $totalFileSize += $file.Length
        }
    }
    
    $reportData.assets += @{
        assetType = $result.AssetType
        gameType = $result.GameType
        status = if ($result.Success) { "success" } else { "failed" }
        message = $result.Message
        outputDir = $gameOutputDir
        files = $files
        fileCount = $files.Count
        totalSize = $totalFileSize
        suggestion = if ($result.Suggestion) { $result.Suggestion } else { $null }
    }
}

# Calculate totals for report
$allFiles = Get-ChildItem -Path $baseOutputDir -Recurse -File -ErrorAction SilentlyContinue
$reportData.totalFiles = $allFiles.Count
$reportData.totalSize = ($allFiles | Measure-Object -Property Length -Sum).Sum

# Write JSON report
$jsonReportPath = Join-Path $baseOutputDir "generation_report.json"
try {
    $reportData | ConvertTo-Json -Depth 10 | Out-File -FilePath $jsonReportPath -Encoding UTF8
    Write-Log "  JSON report: $jsonReportPath" "SUCCESS"
} catch {
    Write-Log "  Failed to write JSON report: $_" "WARN"
}

# Write HTML report
$htmlReportPath = Join-Path $baseOutputDir "generation_report.html"
try {
    $htmlContent = @"
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Multi-Asset Generation Report - $($AssetName)</title>
    <style>
        :root {
            --bg-dark: #1a1a2e;
            --bg-card: #16213e;
            --accent: #0f3460;
            --success: #00d9a5;
            --error: #ff6b6b;
            --warning: #ffd93d;
            --text: #eee;
            --text-dim: #888;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: var(--bg-dark);
            color: var(--text);
            padding: 2rem;
            min-height: 100vh;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 {
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
            background: linear-gradient(135deg, var(--success), #00b4d8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .subtitle { color: var(--text-dim); margin-bottom: 2rem; }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }
        .stat-card {
            background: var(--bg-card);
            padding: 1.5rem;
            border-radius: 12px;
            border-left: 4px solid var(--accent);
        }
        .stat-card.success { border-left-color: var(--success); }
        .stat-card.error { border-left-color: var(--error); }
        .stat-value { font-size: 2rem; font-weight: bold; }
        .stat-label { color: var(--text-dim); font-size: 0.9rem; }
        .section { margin-bottom: 2rem; }
        .section-title { font-size: 1.5rem; margin-bottom: 1rem; color: var(--success); }
        .asset-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 1rem;
        }
        .asset-card {
            background: var(--bg-card);
            padding: 1.5rem;
            border-radius: 12px;
            border: 1px solid var(--accent);
        }
        .asset-card.success { border-color: var(--success); }
        .asset-card.failed { border-color: var(--error); }
        .asset-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }
        .asset-title { font-weight: bold; }
        .asset-badge {
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: bold;
        }
        .badge-success { background: var(--success); color: #000; }
        .badge-failed { background: var(--error); color: #fff; }
        .asset-meta { color: var(--text-dim); font-size: 0.9rem; }
        .file-list {
            margin-top: 1rem;
            padding: 1rem;
            background: rgba(0,0,0,0.2);
            border-radius: 8px;
            font-family: monospace;
            font-size: 0.85rem;
            max-height: 150px;
            overflow-y: auto;
        }
        .file-item { padding: 0.25rem 0; border-bottom: 1px solid rgba(255,255,255,0.1); }
        .file-item:last-child { border-bottom: none; }
        .suggestion {
            margin-top: 1rem;
            padding: 0.75rem;
            background: rgba(255, 217, 61, 0.1);
            border-left: 3px solid var(--warning);
            border-radius: 4px;
            font-size: 0.9rem;
        }
        footer {
            margin-top: 3rem;
            padding-top: 1rem;
            border-top: 1px solid var(--accent);
            color: var(--text-dim);
            font-size: 0.85rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>$($AssetName)</h1>
        <p class="subtitle">Multi-Asset Generation Report - $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')</p>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-value">$total</div>
                <div class="stat-label">Total Assets</div>
            </div>
            <div class="stat-card success">
                <div class="stat-value">$successCount</div>
                <div class="stat-label">Successful</div>
            </div>
            <div class="stat-card $(if ($failCount -gt 0) { 'error' } else { '' })">
                <div class="stat-value">$failCount</div>
                <div class="stat-label">Failed</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">$([math]::Round($totalTime, 1))s</div>
                <div class="stat-label">Total Time</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">$($allFiles.Count)</div>
                <div class="stat-label">Files Generated</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">$([math]::Round(($allFiles | Measure-Object -Property Length -Sum).Sum / 1MB, 2)) MB</div>
                <div class="stat-label">Total Size</div>
            </div>
        </div>
        
        <div class="section">
            <h2 class="section-title">Asset Details</h2>
            <div class="asset-grid">
"@

    foreach ($asset in $reportData.assets) {
        $statusClass = if ($asset.status -eq "success") { "success" } else { "failed" }
        $badgeClass = if ($asset.status -eq "success") { "badge-success" } else { "badge-failed" }
        $sizeStr = if ($asset.totalSize -gt 1MB) { "$([math]::Round($asset.totalSize/1MB, 2)) MB" }
                   elseif ($asset.totalSize -gt 1KB) { "$([math]::Round($asset.totalSize/1KB, 2)) KB" }
                   else { "$($asset.totalSize) B" }
        
        $htmlContent += @"

                <div class="asset-card $statusClass">
                    <div class="asset-header">
                        <span class="asset-title">$($asset.gameType) - $($asset.assetType)</span>
                        <span class="asset-badge $badgeClass">$($asset.status.ToUpper())</span>
                    </div>
                    <div class="asset-meta">
                        <div>Files: $($asset.fileCount) | Size: $sizeStr</div>
                    </div>
"@
        
        if ($asset.files.Count -gt 0) {
            $htmlContent += @"

                    <div class="file-list">
"@
            foreach ($file in ($asset.files | Select-Object -First 10)) {
                $htmlContent += "                        <div class='file-item'>$file</div>`n"
            }
            if ($asset.files.Count -gt 10) {
                $htmlContent += "                        <div class='file-item'>... and $($asset.files.Count - 10) more</div>`n"
            }
            $htmlContent += "                    </div>"
        }
        
        if ($asset.suggestion) {
            $htmlContent += @"

                    <div class="suggestion">💡 $($asset.suggestion)</div>
"@
        }
        
        $htmlContent += @"

                </div>
"@
    }

    $htmlContent += @"

            </div>
        </div>
        
        <footer>
            <p>Generated by Multi-Asset Generator | Output: $baseOutputDir</p>
            <p>Log file: $logFile</p>
        </footer>
    </div>
</body>
</html>
"@

    $htmlContent | Out-File -FilePath $htmlReportPath -Encoding UTF8
    Write-Log "  HTML report: $htmlReportPath" "SUCCESS"
} catch {
    Write-Log "  Failed to write HTML report: $_" "WARN"
}

Write-Log ""
Write-Log "═══════════════════════════════════════════════════════════" "INFO"
Write-Log "  Multi-Asset Generation Complete" "SUCCESS"
Write-Log "═══════════════════════════════════════════════════════════" "INFO"
Write-Log ""

# Cleanup file watchers
Write-Log "Cleaning up file watchers..." "INFO"
try {
    foreach ($event in $script:FileWatcherEvents) {
        if ($event) {
            Unregister-Event -SourceIdentifier $event.Name -ErrorAction SilentlyContinue
            Remove-Job -Id $event.Id -Force -ErrorAction SilentlyContinue
        }
    }
    foreach ($watcher in $script:FileWatchers) {
        if ($watcher) {
            $watcher.EnableRaisingEvents = $false
            $watcher.Dispose()
        }
    }
    Write-Log "File watchers cleaned up" "SUCCESS"
} catch {
    Write-Log "Warning during cleanup: $_" "WARN"
}

Write-Log ""

