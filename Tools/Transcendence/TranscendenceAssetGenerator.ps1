#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Specialized asset generator for Transcendence mods with quality-focused specifications.

.DESCRIPTION
    Generates high-quality assets for Transcendence mods (icons, textures, spritesheets,
    audio, beacons, planets, ship parts). Ship and Projectile delegate to Shared\GenerateGameAsset.ps1.
    All other types write real PNG/JPG/WAV/OBJ via TranscendenceAssetGenerator.Functions.ps1
    and Shared\tx_procedural_assets.py — never .info.txt stubs.

.PARAMETER AssetType
    Ship, Weapon, Item, Projectile, Spritesheet, Icon, ShipTexture, ShipModel, Planet, Audio, Beacon, PowerIcon, AbilityIcon
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("Ship", "Weapon", "Item", "Projectile", "Spritesheet", "Icon", "ShipTexture", "ShipModel", "Planet", "Audio", "Beacon", "PowerIcon", "AbilityIcon")]
    [string]$AssetType,
    
    [Parameter(Mandatory=$true)]
    [string]$AssetName,
    
    [Parameter(Mandatory=$false)]
    [string]$Description = "",
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("Standard", "High", "Ultra")]
    [string]$Quality = "High",
    
    [Parameter(Mandatory=$false)]
    [string]$OutputDir = "",  # Defaults to Output/ if not specified
    
    [Parameter(Mandatory=$false)]
    [switch]$UseAI,
    
    [Parameter(Mandatory=$false)]
    [string]$OllamaModel = "llama3.2",
    
    [Parameter(Mandatory=$false)]
    [int]$IconSize = 96,
    
    [Parameter(Mandatory=$false)]
    [int]$Size,  # Direct size parameter (used for projectiles and other assets)
    
    [Parameter(Mandatory=$false)]
    [int]$TextureSize = 512,
    
    [Parameter(Mandatory=$false)]
    [int]$ShipTextureWidth = 512,
    
    [Parameter(Mandatory=$false)]
    [int]$ShipTextureHeight = 512,
    
    [Parameter(Mandatory=$false)]
    [int]$Facings = 120,
    
    [Parameter(Mandatory=$false)]
    [int]$FrameWidth = 150,
    
    [Parameter(Mandatory=$false)]
    [int]$FrameHeight = 150,
    
    [Parameter(Mandatory=$false)]
    [int]$SpritesheetColumns = 10,
    
    [Parameter(Mandatory=$false)]
    [string]$BlenderPath = "",
    
    [Parameter(Mandatory=$false)]
    [switch]$GenerateSpritesheet,
    
    [Parameter(Mandatory=$false)]
    [int]$SpritesheetRows = 8,
    
    [Parameter(Mandatory=$false)]
    [string]$ResourceName = "",
    
    [Parameter(Mandatory=$false)]
    [switch]$BatchMode,
    
    [Parameter(Mandatory=$false)]
    [string]$ConfigFile = "",
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("Architect", "Assault", "Battery", "Carrier", "Courser", "Engineer", "Firefly", "Hullbreaker", "Research", "Sentinel", "Leviathan", "Spectre", "Standard", "Stealth", "Viper", "")]
    [string]$NovaDriftStyle = "",
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("Blade", "Blaster", "Dart", "Flak", "Grenade", "Pulse", "Railgun", "Salvo", "SplitShot", "Swords", "ThermalLance", "Torrent", "Vortex", "")]
    [string]$NovaDriftWeaponStyle = "",
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("WeaponMod", "ConstructMod", "HullMod", "ShieldMod", "BurnMod", "BlastMod", "SuperMod", "WildMod", "Module", "Amp", "Bastion", "Halo", "Helix", "Orbital", "Reflect", "Shockwave", "Siphon", "Standard", "Temporal", "Warp", "")]
    [string]$NovaDriftItemStyle = "",
    
    [Parameter(Mandatory=$false)]
    [switch]$UseNovaDriftReference,
    
    [Parameter(Mandatory=$false)]
    [int]$AudioDuration = 3,
    
    [Parameter(Mandatory=$false)]
    [int]$AudioSampleRate = 44100,
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("Effect", "Music", "Ambient", "Weapon", "Engine", "Voice")]
    [string]$AudioType = "Effect",
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("Green", "Yellow", "Blue", "Red")]
    [string]$BeaconColor = "Green",
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("Crystal", "Orb", "Spire", "Shell", "Disk", "Cluster", "Radial")]
    [string]$PowerIconStyle = "Crystal",
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("Green", "Blue", "Red", "Purple", "Orange", "Cyan", "Yellow")]
    [string]$PowerIconColor = "Green"
)

$ErrorActionPreference = "Stop"
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

# Load shared asset generation settings
$settingsPath = Join-Path $PSScriptRoot "..\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}

# Optional tool detection (non-fatal if modules missing)
$sharedPath = Join-Path $PSScriptRoot "..\Shared"
Import-Module (Join-Path $sharedPath "ToolDetection.psm1") -ErrorAction SilentlyContinue
Import-Module (Join-Path $sharedPath "ToolsetIntegration.psm1") -ErrorAction SilentlyContinue

# ============================================================
# REFERENCE ASSETS LOCATION (Optional - Isolated Third-Party Files)
# ============================================================

function Get-ReferenceAssetsPath {
    <#
    .SYNOPSIS
        Gets the path to isolated reference assets (optional third-party files)
    
    .DESCRIPTION
        Reference assets are isolated in Tools/ReferenceAssets/TranscendenceArt (using Tools folder as root)
        These contain third-party reference files that tools can benefit from but don't require.
        Tools work fine without them, but can use them for style matching and quality examples.
    #>
    
    # Reference assets are isolated in Tools/ReferenceAssets/TranscendenceArt
    # Uses Tools folder as root - works from any subdirectory
    $toolsRoot = Split-Path -Parent $PSScriptRoot
    $referencePath = Join-Path $toolsRoot "ReferenceAssets\TranscendenceArt"
    
    if (Test-Path $referencePath) {
        return $referencePath
    }
    
    # Fallback: Check old location for migration (backward compatibility)
    $oldPath = Join-Path $PSScriptRoot "TranscendenceArt"
    if (Test-Path $oldPath) {
        # Don't warn - silently use old location for backward compatibility
        return $oldPath
    }
    
    # Not found - return null (tools work without it)
    return $null
}

# Get optional reference assets path (log after Write-Log is defined)
$script:ReferenceAssetsPath = Get-ReferenceAssetsPath

# Nova Drift ship design references
# Based on https://nova-drift.fandom.com/wiki/Ships
$novaDriftShips = @{
    "Architect" = "Modular construction ship with geometric, angular design. Features multiple attachment points and a blocky, industrial aesthetic."
    "Assault" = "Aggressive combat ship with forward-facing weapons and angular, aggressive lines. Built for direct engagement."
    "Battery" = "Heavy weapons platform with multiple hardpoints. Large, imposing design with prominent weapon mounts."
    "Carrier" = "Large support ship with hangar bays and defensive capabilities. Broad, flat design optimized for launching smaller craft."
    "Courser" = "Fast interceptor with sleek, streamlined design. Narrow profile optimized for speed and maneuverability."
    "Engineer" = "Technical support ship with modular components. Features visible repair systems and utility attachments."
    "Firefly" = "Small, agile scout ship with compact design. Quick and nimble with a distinctive insect-like appearance."
    "Hullbreaker" = "Heavy assault ship with reinforced armor. Massive, tank-like design built for breaking through defenses."
    "Research" = "Scientific vessel with sensor arrays and experimental equipment. Features unusual geometric shapes and research modules."
    "Sentinel" = "Defensive platform with protective capabilities. Shield-focused design with defensive hardpoints."
    "Leviathan" = "Massive capital ship with overwhelming firepower. Enormous size with multiple weapon systems and heavy armor."
    "Spectre" = "Stealth ship with low-profile design. Sleek, angular shape optimized for evasion and surprise attacks."
    "Standard" = "Versatile all-purpose ship with balanced design. Classic spaceship silhouette with moderate size and capabilities."
    "Stealth" = "Infiltrator ship with minimal profile. Dark, angular design optimized for stealth operations."
    "Viper" = "Fast attack ship with aggressive design. Sharp, pointed shape optimized for hit-and-run tactics."
}

# Nova Drift weapon design references
# Based on https://nova-drift.fandom.com/wiki/Weapons
$novaDriftWeapons = @{
    "Blade" = "Melee weapon with sharp cutting edge. Close-range slashing weapon with angular, blade-like appearance."
    "Blaster" = "Rapid-fire energy weapon with continuous beam or burst fire. Compact design with energy coils and focusing lenses."
    "Dart" = "Fast projectile weapon firing small, dart-like projectiles. Sleek, streamlined design optimized for speed."
    "Flak" = "Explosive area-effect weapon that detonates into fragments. Heavy, cannon-like design with explosive projectiles."
    "Grenade" = "Explosive projectile weapon with delayed detonation. Round, grenade-like projectiles with timer mechanisms."
    "Pulse" = "Energy weapon firing pulsing energy blasts. Features pulsing energy cores and discharge ports."
    "Railgun" = "Electromagnetic projectile launcher with high velocity. Long barrel design with electromagnetic coils."
    "Salvo" = "Multi-projectile weapon firing volleys of shots. Features multiple barrels or launcher tubes."
    "SplitShot" = "Projectile weapon that splits into multiple projectiles. Central barrel with splitter mechanism."
    "Swords" = "Dual melee weapons with crossed blade design. Two blades arranged in an X-pattern for close combat."
    "ThermalLance" = "Heat-based energy weapon with focused thermal beam. Features thermal focusing array and heat vents."
    "Torrent" = "Rapid-fire weapon with continuous stream of projectiles. Multiple barrels or rapid-fire mechanism."
    "Vortex" = "Gravity-based weapon creating vortex effects. Features gravitational field generators and vortex projectors."
}

# Nova Drift mod/item design references
# Based on https://nova-drift.fandom.com/wiki/Mods
# Mods are categorized: Weapon, Construct, Hull, Shield, Burn, Blast, Super, Wild
$novaDriftMods = @{
    "WeaponMod" = "Weapon modification module. Features weapon enhancement components, targeting systems, and damage amplifiers. Modular design with attachment points."
    "ConstructMod" = "Construct/drone modification module. Features construct control systems, deployment mechanisms, and enhancement circuits. Technical, mechanical appearance."
    "HullMod" = "Hull/armor modification module. Features armor plating, structural reinforcements, and defensive systems. Heavy, protective design with reinforced edges."
    "ShieldMod" = "Shield modification module. Features shield generators, energy conduits, and protection systems. Energy-focused design with shield emitters."
    "BurnMod" = "Burn/fire modification module. Features thermal systems, fire projectors, and heat management. Fiery, thermal appearance with heat vents."
    "BlastMod" = "Explosive modification module. Features explosive components, detonation systems, and blast amplifiers. Explosive, volatile design with safety mechanisms."
    "SuperMod" = "Super modification module. Features advanced enhancement systems, power cores, and superior capabilities. Premium, high-tech design with advanced components."
    "WildMod" = "Wild modification module. Features chaotic systems, unpredictable enhancements, and experimental components. Unstable, experimental design with unusual geometry."
    "Module" = "General modification module. Features modular components, enhancement systems, and upgrade mechanisms. Standard module design with connection ports."
}

# Nova Drift shield design references
# Based on https://nova-drift.fandom.com/wiki/Shields
$novaDriftShields = @{
    "Amp" = "Amplifier shield that enhances damage output. Features energy amplification systems and power conduits. Focused on offensive enhancement."
    "Bastion" = "Heavy defensive shield with maximum protection. Features reinforced shield generators and defensive barriers. Thick, protective design."
    "Halo" = "Circular shield with protective ring design. Features orbital shield emitters forming a halo around the ship. Ring-shaped energy field."
    "Helix" = "Spiral shield with helical energy pattern. Features rotating shield generators creating a spiral defense. Dynamic, rotating design."
    "Orbital" = "Shield with orbiting protective elements. Features multiple shield generators orbiting the ship. Multiple protective orbs."
    "Reflect" = "Reflective shield that bounces projectiles. Features reflective shield surfaces and deflection systems. Mirror-like, reflective design."
    "Shockwave" = "Shield that emits shockwaves when hit. Features shockwave generators and impact amplifiers. Explosive defensive design."
    "Siphon" = "Shield that drains energy from enemies. Features energy siphon systems and drain conduits. Energy-draining design."
    "Standard" = "Standard balanced shield with moderate protection. Features standard shield generators and balanced systems. Classic shield design."
    "Temporal" = "Time-based shield with temporal effects. Features temporal generators and time manipulation systems. Time-distorted appearance."
    "Warp" = "Warp shield with spatial distortion effects. Features warp field generators and spatial distortion systems. Warped, distorted design."
}

# Setup logging
$logDir = Join-Path $PSScriptRoot "Logs"
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

$logFile = Join-Path $logDir "TranscendenceAsset_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"

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
        Add-Content -Path $logFile -Value $logEntry -Encoding UTF8 -ErrorAction SilentlyContinue
    } catch { }
}

if ($script:ReferenceAssetsPath) {
    Write-Log "Reference assets available: $script:ReferenceAssetsPath" "Info"
} else {
    Write-Log "Reference assets not found (optional - tools work without them)" "Info"
}

# Real Generate-* / Create-* (must load before AssetType switch)
$functionsPath = Join-Path $PSScriptRoot "TranscendenceAssetGenerator.Functions.ps1"
if (-not (Test-Path -LiteralPath $functionsPath)) { throw "Missing $functionsPath" }
. $functionsPath

Write-Log "═══════════════════════════════════════════════════════════" "INFO"
Write-Log "  Transcendence Asset Generator" "INFO"
Write-Log "═══════════════════════════════════════════════════════════" "INFO"
Write-Log "Asset Type: $AssetType" "INFO"
Write-Log "Asset Name: $AssetName" "INFO"
Write-Log "Quality: $Quality" "INFO"
Write-Log "Output Directory: $OutputDir" "INFO"
if ($NovaDriftStyle) {
    Write-Log "Nova Drift Ship Style: $NovaDriftStyle" "INFO"
    Write-Log "  Reference: https://nova-drift.fandom.com/wiki/Ships" "INFO"
}
if ($NovaDriftWeaponStyle) {
    Write-Log "Nova Drift Weapon Style: $NovaDriftWeaponStyle" "INFO"
    Write-Log "  Reference: https://nova-drift.fandom.com/wiki/Weapons" "INFO"
}
if ($NovaDriftItemStyle) {
    $isShield = $novaDriftShields.ContainsKey($NovaDriftItemStyle)
    $reference = if ($isShield) { "https://nova-drift.fandom.com/wiki/Shields" } else { "https://nova-drift.fandom.com/wiki/Mods" }
    Write-Log "Nova Drift Item/Mod/Shield Style: $NovaDriftItemStyle" "INFO"
    Write-Log "  Reference: $reference" "INFO"
}
Write-Log ""

# Quality specifications
$qualitySpecs = @{
    "Standard" = @{
        "IconSize" = 96
        "TextureSize" = 256
        "ShipTextureWidth" = 256
        "ShipTextureHeight" = 256
        "ShipFrameWidth" = 128
        "ShipFrameHeight" = 128
        "ShipSpritesheetColumns" = 10
        "ProjectileSize" = 32
        "AntiAliasing" = "None"
        "ColorDepth" = "24bit"
        "Compression" = "Medium"
    }
    "High" = @{
        "IconSize" = 96
        "TextureSize" = 512
        "ShipTextureWidth" = 512
        "ShipTextureHeight" = 512
        "ShipFrameWidth" = 150
        "ShipFrameHeight" = 150
        "ShipSpritesheetColumns" = 10
        "ProjectileSize" = 64
        "AntiAliasing" = "2x"
        "ColorDepth" = "32bit"
        "Compression" = "High"
    }
    "Ultra" = @{
        "IconSize" = 128
        "TextureSize" = 1024
        "ShipTextureWidth" = 1024
        "ShipTextureHeight" = 1024
        "ShipFrameWidth" = 200
        "ShipFrameHeight" = 200
        "ShipSpritesheetColumns" = 10
        "ProjectileSize" = 128
        "AntiAliasing" = "4x"
        "ColorDepth" = "32bit"
        "Compression" = "Lossless"
    }
}

# Apply quality settings
$specs = $qualitySpecs[$Quality]
if ($IconSize -eq 96 -and $specs.IconSize -ne 96) {
    $IconSize = $specs.IconSize
}
if ($TextureSize -eq 512 -and $specs.TextureSize -ne 512) {
    $TextureSize = $specs.TextureSize
}
if ($ShipTextureWidth -eq 512 -and $specs.ShipTextureWidth -ne 512) {
    $ShipTextureWidth = $specs.ShipTextureWidth
    $ShipTextureHeight = $specs.ShipTextureHeight
}
# Apply ship frame size from quality specs if not explicitly set
if ($FrameWidth -eq 150 -and $specs.ShipFrameWidth) {
    $FrameWidth = $specs.ShipFrameWidth
    $FrameHeight = $specs.ShipFrameHeight
}
if ($SpritesheetColumns -eq 10 -and $specs.ShipSpritesheetColumns) {
    $SpritesheetColumns = $specs.ShipSpritesheetColumns
}

Write-Log "Quality Specifications:" "INFO"
Write-Log "  Icon Size: $($specs.IconSize)x$($specs.IconSize)" "INFO"
Write-Log "  Texture Size: $($specs.TextureSize)x$($specs.TextureSize)" "INFO"
Write-Log "  Ship Texture: $($specs.ShipTextureWidth)x$($specs.ShipTextureHeight)" "INFO"
Write-Log "  Anti-Aliasing: $($specs.AntiAliasing)" "INFO"
Write-Log "  Color Depth: $($specs.ColorDepth)" "INFO"
Write-Log ""

# Set default output directory if not specified
if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $OutputDir = Join-Path (Split-Path -Parent $PSScriptRoot) "Output"
    Write-Log "Using default output directory: $OutputDir" "Info"
}

# Create output directory structure
$assetOutputDir = Join-Path $OutputDir $AssetName
if (-not (Test-Path $assetOutputDir)) {
    New-Item -ItemType Directory -Path $assetOutputDir -Force | Out-Null
    Write-Log "Created output directory: $assetOutputDir" "SUCCESS"
}

# Asset type specific directories
$typeDirs = @{
    "Ship" = "Ships"
    "Weapon" = "Weapons"
    "Item" = "Items"
    "Projectile" = "Projectiles"
    "Spritesheet" = "Spritesheets"
    "Icon" = "Icons"
    "ShipTexture" = "Ships/Textures"
    "ShipModel" = "Ships/Models"
    "Planet" = "Planets"
    "Audio" = "Audio"
    "Beacon" = "Beacons"
    "PowerIcon" = "Icons"
    "AbilityIcon" = "Icons"
}

    $typeDir = $typeDirs[$AssetType]
    if (-not $typeDir) { $typeDir = $AssetType }
$finalOutputDir = Join-Path $assetOutputDir $typeDir
if (-not (Test-Path $finalOutputDir)) {
    New-Item -ItemType Directory -Path $finalOutputDir -Force | Out-Null
}

# Ship / Projectile: prefer Shared GenerateGameAsset pipeline (real TranscendenceExtension XML).
# Other AssetTypes use Functions.ps1 + tx_procedural_assets.py (real media).
$sharedGen = Join-Path (Split-Path -Parent $PSScriptRoot) "Shared\GenerateGameAsset.ps1"
if (($AssetType -eq "Ship" -or $AssetType -eq "Projectile") -and (Test-Path -LiteralPath $sharedGen)) {
    $kind = if ($AssetType -eq "Ship") { "ship" } else { "projectile" }
    $theme = if ($Description) { $Description } else { $AssetName }
    $outRoot = if ($OutputDir) { $OutputDir } else { Join-Path $PSScriptRoot "Output" }
    Write-Host "Delegating $AssetType -> Shared\GenerateGameAsset.ps1 (-Defs -DeployTx)" -ForegroundColor Cyan
    if ($UseAI) {
        $pipe = Join-Path $PSScriptRoot "tx_ai_pipeline.py"
        $py = (Get-Command python -ErrorAction SilentlyContinue).Source
        if ($py -and (Test-Path -LiteralPath $pipe)) {
            Write-Host "Ensuring Shared image+mesh stages..." -ForegroundColor Cyan
            & $py $pipe ensure image
            & $py $pipe ensure mesh
        }
    }
    $genArgs = @{
        Kind = $kind
        Theme = $theme
        Name = $AssetName
        OutDir = $outRoot
        SystemName = "Transcendence"
        Defs = $true
        DeployTx = $true
        NoSd = (-not $UseAI)
        Mesh = $true
    }
    & $sharedGen @genArgs
    exit $LASTEXITCODE
}

# Generate asset based on type
switch ($AssetType) {
    "Ship" {
        Write-Log "Generating ship assets..." "INFO"
        # Enhance description with Nova Drift style if specified
        $enhancedDescription = $Description
        if ($NovaDriftStyle -and $novaDriftShips.ContainsKey($NovaDriftStyle)) {
            $styleDesc = $novaDriftShips[$NovaDriftStyle]
            $enhancedDescription = "$Description. Nova Drift $NovaDriftStyle style: $styleDesc"
            Write-Log "Using Nova Drift $NovaDriftStyle design reference" "INFO"
        }
        Generate-ShipAsset -Name $AssetName -Description $enhancedDescription -OutputDir $finalOutputDir -Specs $specs -UseAI:$UseAI -OllamaModel $OllamaModel -BlenderPath $BlenderPath -Facings $Facings -FrameWidth $FrameWidth -FrameHeight $FrameHeight -SpritesheetColumns $SpritesheetColumns -NovaDriftStyle $NovaDriftStyle
    }
    "ShipTexture" {
        Write-Log "Generating ship texture..." "INFO"
        Generate-ShipTexture -Name $AssetName -Description $Description -OutputDir $finalOutputDir -Specs $specs -UseAI:$UseAI -OllamaModel $OllamaModel -Width $ShipTextureWidth -Height $ShipTextureHeight
    }
    "ShipModel" {
        Write-Log "Generating ship 3D model..." "INFO"
        Generate-ShipModel -Name $AssetName -Description $Description -OutputDir $finalOutputDir -Specs $specs -UseAI:$UseAI -OllamaModel $OllamaModel -BlenderPath $BlenderPath
    }
    "Weapon" {
        Write-Log "Generating weapon icon..." "INFO"
        # Enhance description with Nova Drift weapon style if specified
        $enhancedDescription = $Description
        if ($NovaDriftWeaponStyle -and $novaDriftWeapons.ContainsKey($NovaDriftWeaponStyle)) {
            $styleDesc = $novaDriftWeapons[$NovaDriftWeaponStyle]
            $enhancedDescription = "$Description. Nova Drift $NovaDriftWeaponStyle style: $styleDesc"
            Write-Log "Using Nova Drift $NovaDriftWeaponStyle weapon design reference" "INFO"
        }
        Generate-WeaponIcon -Name $AssetName -Description $enhancedDescription -OutputDir $finalOutputDir -Specs $specs -UseAI:$UseAI -OllamaModel $OllamaModel -Size $IconSize -NovaDriftStyle $NovaDriftWeaponStyle
    }
    "Item" {
        Write-Log "Generating item icon..." "INFO"
        # Enhance description with Nova Drift mod or shield style if specified
        $enhancedDescription = $Description
        if ($NovaDriftItemStyle) {
            if ($novaDriftShields.ContainsKey($NovaDriftItemStyle)) {
                $styleDesc = $novaDriftShields[$NovaDriftItemStyle]
                $enhancedDescription = "$Description. Nova Drift $NovaDriftItemStyle shield style: $styleDesc"
                Write-Log "Using Nova Drift $NovaDriftItemStyle shield design reference" "INFO"
            } elseif ($novaDriftMods.ContainsKey($NovaDriftItemStyle)) {
                $styleDesc = $novaDriftMods[$NovaDriftItemStyle]
                $enhancedDescription = "$Description. Nova Drift $NovaDriftItemStyle mod style: $styleDesc"
                Write-Log "Using Nova Drift $NovaDriftItemStyle mod design reference" "INFO"
            }
        }
        Generate-ItemIcon -Name $AssetName -Description $enhancedDescription -OutputDir $finalOutputDir -Specs $specs -UseAI:$UseAI -OllamaModel $OllamaModel -Size $IconSize -NovaDriftStyle $NovaDriftItemStyle
    }
    "Icon" {
        Write-Log "Generating icon..." "INFO"
        Generate-Icon -Name $AssetName -Description $Description -OutputDir $finalOutputDir -Specs $specs -UseAI:$UseAI -OllamaModel $OllamaModel -Size $IconSize
    }
    "Projectile" {
        Write-Log "Generating projectile sprite..." "INFO"
        # Use Size parameter if provided, otherwise use specs.ProjectileSize
        $projectileSize = if ($PSBoundParameters.ContainsKey('Size') -and $Size -gt 0) { $Size } else { $specs.ProjectileSize }
        Write-Log "Using projectile size: $projectileSize" "INFO"
        $result = Generate-Projectile -Name $AssetName -Description $Description -OutputDir $finalOutputDir -Specs $specs -UseAI:$UseAI -OllamaModel $OllamaModel -Size $projectileSize
        if (-not $result) {
            Write-Log "Projectile generation failed!" "ERROR"
            exit 1
        }
    }
    "Planet" {
        Write-Log "Generating planet asset..." "INFO"
        Generate-PlanetAsset -Name $AssetName -Description $Description -OutputDir $finalOutputDir -Specs $specs -UseAI:$UseAI -OllamaModel $OllamaModel -BlenderPath $BlenderPath
    }
    "Audio" {
        Write-Log "Generating audio asset..." "INFO"
        Generate-AudioAsset -Name $AssetName -Description $Description -OutputDir $finalOutputDir -Specs $specs -UseAI:$UseAI -OllamaModel $OllamaModel -Duration $AudioDuration -SampleRate $AudioSampleRate -AudioType $AudioType
    }
    "Beacon" {
        Write-Log "Generating beacon asset..." "INFO"
        Generate-BeaconAsset -Name $AssetName -Description $Description -OutputDir $finalOutputDir -Specs $specs -UseAI:$UseAI -OllamaModel $OllamaModel -BlenderPath $BlenderPath -BeaconColor $BeaconColor
    }
    "PowerIcon" {
        Write-Log "Generating power ability icon..." "INFO"
        Generate-PowerIcon -Name $AssetName -Description $Description -OutputDir $finalOutputDir -Specs $specs -UseAI:$UseAI -OllamaModel $OllamaModel -Size $IconSize -IconStyle $PowerIconStyle -IconColor $PowerIconColor
    }
    "AbilityIcon" {
        Write-Log "Generating ability icon..." "INFO"
        Generate-PowerIcon -Name $AssetName -Description $Description -OutputDir $finalOutputDir -Specs $specs -UseAI:$UseAI -OllamaModel $OllamaModel -Size $IconSize -IconStyle $PowerIconStyle -IconColor $PowerIconColor
    }
    "Spritesheet" {
        Write-Log "Generating spritesheet..." "INFO"
        # Determine game format and output format based on context
        $gameFormat = "Transcendence"  # Default for Transcendence assets
        $outputFormat = "PNG"  # Default, will be adjusted based on asset type
        
        Generate-Spritesheet -Name $AssetName -Description $Description -OutputDir $finalOutputDir -Specs $specs -Columns $SpritesheetColumns -Rows $SpritesheetRows -ResourceName $ResourceName -BlenderPath $BlenderPath -GameFormat $gameFormat -OutputFormat $outputFormat
    }
}

Write-Log "Asset generation complete!" "SUCCESS"
Write-Log "Output: $finalOutputDir" "INFO"

