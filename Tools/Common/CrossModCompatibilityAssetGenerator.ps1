#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Batch asset generator for CrossModCompatibility extension.
    
.DESCRIPTION
    Scans CrossModCompatibility XML files and generates all required assets:
    - Ships (120 facings)
    - Weapons (icons)
    - Items (icons)

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}
    - Projectiles (sprites)
    - Spritesheets for weapon parts
    
.PARAMETER ExtensionPath
    Path to CrossModCompatibility extension directory
    
.PARAMETER Quality
    Quality level: Standard, High, Ultra
    
.PARAMETER UseAI
    Use AI for generation
    
.PARAMETER GenerateShips
    Generate ship assets
    
.PARAMETER GenerateWeapons
    Generate weapon icons
    
.PARAMETER GenerateItems
    Generate item icons
    
.PARAMETER GenerateProjectiles
    Generate projectile sprites
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [string]$ExtensionPath = "",  # Defaults to Extensions/ZZZ_CrossModCompatibility relative to Transcendence root
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("Standard", "High", "Ultra")]
    [string]$Quality = "High",
    
    [Parameter(Mandatory=$false)]
    [switch]$UseAI,
    
    [Parameter(Mandatory=$false)]
    [string]$OllamaModel = "llama3.2",
    
    [Parameter(Mandatory=$false)]
    [switch]$GenerateShips,
    
    [Parameter(Mandatory=$false)]
    [switch]$GenerateWeapons,
    
    [Parameter(Mandatory=$false)]
    [switch]$GenerateItems,
    
    [Parameter(Mandatory=$false)]
    [switch]$GenerateProjectiles,
    
    [Parameter(Mandatory=$false)]
    [switch]$GenerateAll,
    
    [Parameter(Mandatory=$false)]
    [string]$OutputDir = ""  # Defaults to Output/CrossModCompatibility if not specified
)

# Ensure parameters are strings (not arrays) - PowerShell can sometimes pass arrays
if ($ExtensionPath -is [Array]) {
    $ExtensionPath = $ExtensionPath[0]
}
$ExtensionPath = $ExtensionPath.ToString().Trim()

if ($OutputDir -is [Array]) {
    $OutputDir = $OutputDir[0]
}
$OutputDir = $OutputDir.ToString().Trim()

$ErrorActionPreference = "Stop"
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$toolsRoot = Split-Path -Parent $PSScriptRoot

# Helper function to get Transcendence root from settings
function Get-TranscendenceRootFromSettings {
    $settingsFile = Join-Path $toolsRoot "TranscendenceTools.ini"
    
    if (Test-Path $settingsFile) {
        $content = Get-Content $settingsFile -Raw
        if ($content -match '(?m)^\s*TranscendencePath\s*=\s*(.+)$') {
            $path = $matches[1].Trim()
            $path = [System.Environment]::ExpandEnvironmentVariables($path)
            if (Test-Path $path) {
                return $path
            }
        }
    }
    
    return $null
}

# Helper function to find Transcendence root
function Find-TranscendenceRoot {
    param([string]$StartPath = $toolsRoot)
    
    # First, check settings file
    $settingsPath = Get-TranscendenceRootFromSettings
    if ($settingsPath) {
        return $settingsPath
    }
    
    # Then try common Steam installation locations
    $searchPaths = @(
        "${env:ProgramFiles(x86)}\Steam\steamapps\common\Transcendence",
        "${env:ProgramFiles}\Steam\steamapps\common\Transcendence",
        "$env:LOCALAPPDATA\Programs\Steam\steamapps\common\Transcendence",
        "$env:USERPROFILE\SteamLibrary\steamapps\common\Transcendence",
        "$env:USERPROFILE\Steam\steamapps\common\Transcendence"
    )
    
    # Check common drive letters for games partition (D:, E:, F:, etc.)
    $commonDrives = @('D', 'E', 'F', 'G', 'H')
    foreach ($drive in $commonDrives) {
        # Check for \games\Steam\ pattern (common for partitioned OS drives)
        $gamesPath = "${drive}:\games\Steam\steamapps\common\Transcendence"
        if (Test-Path $gamesPath) {
            $searchPaths += $gamesPath
        }
        
        # Check for \SteamLibrary\ pattern (common for additional Steam libraries)
        $steamLibraryPath = "${drive}:\SteamLibrary\steamapps\common\Transcendence"
        if (Test-Path $steamLibraryPath) {
            $searchPaths += $steamLibraryPath
        }
    }
    
    # Also try relative to start path
    $relativePaths = @(
        (Split-Path -Parent $StartPath),
        $StartPath
    )
    $searchPaths = $relativePaths + $searchPaths
    
    foreach ($path in $searchPaths) {
        if ([string]::IsNullOrWhiteSpace($path)) { continue }
        if (-not (Test-Path $path)) { continue }
        
        $tdbFile = Join-Path $path "Transcendence.tdb"
        if (Test-Path $tdbFile) { return $path }
        
        $extensionsPath = Join-Path $path "Extensions"
        if (Test-Path $extensionsPath) { return $path }
    }
    
    return $null
}

# Set default extension path if not specified (relative to Transcendence installation)
# Note: This is optional - most asset generation tools don't need Transcendence
if ([string]::IsNullOrWhiteSpace($ExtensionPath)) {
    $transcendenceRoot = Find-TranscendenceRoot -StartPath $toolsRoot
    
    if ($transcendenceRoot) {
        $ExtensionPath = Join-Path $transcendenceRoot "Extensions\ZZZ_CrossModCompatibility"
    } else {
        # No default - user must specify ExtensionPath if they want to output to a mod folder
        # Asset generation can work standalone without Transcendence
        $ExtensionPath = ""
    }
}

# Set default output directory if not specified
if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $OutputDir = Join-Path $toolsRoot "Output\CrossModCompatibility"
}

# Setup logging
$logDir = Join-Path $PSScriptRoot "Logs"
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

$logFile = Join-Path $logDir "CrossModCompatibilityAssets_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"

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

Write-Log "═══════════════════════════════════════════════════════════" "INFO"
Write-Log "  CrossModCompatibility Asset Generator" "INFO"
Write-Log "═══════════════════════════════════════════════════════════" "INFO"
Write-Log "Extension Path: $ExtensionPath" "INFO"
Write-Log "Quality: $Quality" "INFO"
Write-Log "Output Directory: $OutputDir" "INFO"
Write-Log ""

# Get the TranscendenceAssetGenerator script
$assetGenScript = Join-Path $PSScriptRoot "..\Transcendence\TranscendenceAssetGenerator.ps1"
if (-not (Test-Path $assetGenScript)) {
    Write-Log "ERROR: TranscendenceAssetGenerator.ps1 not found at $assetGenScript" "ERROR"
    exit 1
}

# If GenerateAll is set, enable all generation types
if ($GenerateAll) {
    $GenerateShips = $true
    $GenerateWeapons = $true
    $GenerateItems = $true
    $GenerateProjectiles = $true
}

# If nothing is selected, default to all
if (-not ($GenerateShips -or $GenerateWeapons -or $GenerateItems -or $GenerateProjectiles)) {
    Write-Log "No generation types selected. Enabling all..." "WARN"
    $GenerateShips = $true
    $GenerateWeapons = $true
    $GenerateItems = $true
    $GenerateProjectiles = $true
}

# Find XML files
$xmlFiles = @(
    (Join-Path $ExtensionPath "CrossModCompatibility_Part1.xml"),
    (Join-Path $ExtensionPath "CrossModCompatibility_Part2.xml"),
    (Join-Path $ExtensionPath "CrossModCompatibility_Part3.xml")
)

$allXmlFiles = $xmlFiles | Where-Object { Test-Path $_ }

if ($allXmlFiles.Count -eq 0) {
    Write-Log "ERROR: No CrossModCompatibility XML files found" "ERROR"
    exit 1
}

Write-Log "Found $($allXmlFiles.Count) XML file(s)" "INFO"

# Extract entities that need assets
$shipsToGenerate = @()
$weaponsToGenerate = @()
$itemsToGenerate = @()
$projectilesToGenerate = @()

Write-Log "Scanning XML files for asset requirements..." "INFO"

# Map item/module names to Nova Drift mod styles (if applicable)
# Based on https://nova-drift.fandom.com/wiki/Mods
# Define before the loop so it's available for all items
$novaDriftItemMap = @{
    # Weapon mods
    "Chamber" = "WeaponMod"
    "FireModule" = "WeaponMod"
    "Amplifier" = "WeaponMod"
    "DamageUnit" = "WeaponMod"
        # Shield mods (general shield modifications)
        "ShieldModule" = "ShieldMod"
        "Aegis" = "Aegis"
        "Bastion" = "Bastion"
        "Regen" = "Siphon"
        "Reflect" = "Reflect"
        "Absorb" = "Siphon"
        "LivingAegis" = "Aegis"
        "LivingBastion" = "Bastion"
        "LivingRegen" = "Siphon"
        "LivingReflect" = "Reflect"
        "LivingAbsorb" = "Siphon"
        "LivingExplosive" = "Shockwave"
        "LivingCapacity" = "Bastion"
        "LivingRecharge" = "Standard"
    # Hull/armor mods
    "Armor" = "HullMod"
    "Plate" = "HullMod"
    "Reinforcement" = "HullMod"
    # Construct/drone mods
    "Drone" = "ConstructMod"
    "Swarm" = "ConstructMod"
    "Launcher" = "ConstructMod"
    # Explosive mods
    "Explosive" = "BlastMod"
    "Grenade" = "BlastMod"
    "Fragmentation" = "BlastMod"
    # Thermal mods
    "Flamethrower" = "BurnMod"
    "Igniter" = "BurnMod"
    "Thermal" = "BurnMod"
    # General modules
    "Module" = "Module"
    "Stabilizer" = "Module"
    "Cooler" = "Module"
    "Link" = "Module"
}

foreach ($xmlFile in $allXmlFiles) {
    Write-Log "Scanning: $(Split-Path $xmlFile -Leaf)" "INFO"
    
    $content = Get-Content $xmlFile -Raw -Encoding UTF8
    
    # Find evolved ships (scEvolved*)
    $evolvedShipMatches = [regex]::Matches($content, 'scEvolved(\w+)')
    foreach ($match in $evolvedShipMatches) {
        $shipName = $match.Groups[1].Value
        if ($shipName -and $shipsToGenerate -notcontains $shipName) {
            $shipsToGenerate += $shipName
            Write-Log "  Found evolved ship: $shipName" "INFO"
        }
    }
    
    # Map ship names to Nova Drift styles (if applicable)
    # Firefly is a known Nova Drift ship, others can be mapped
    $novaDriftStyleMap = @{
        "Firefly" = "Firefly"
        # Add more mappings as needed
    }
    
    # Map weapon names to Nova Drift weapon styles (if applicable)
    # Based on https://nova-drift.fandom.com/wiki/Weapons
    $novaDriftWeaponMap = @{
        "NovaBlade" = "Blade"
        "NovaBladeChamber" = "Blade"
        "NovaSword" = "Swords"
        "NovaSwordChamber" = "Swords"
        "NovaSalvo" = "Salvo"
        "NovaSalvoModule" = "Salvo"
        "NovaGrenade" = "Grenade"
        "NovaGrenadeModule" = "Grenade"
        "Flakker" = "Flak"
        "FlakkerModule" = "Flak"
        "QuantumSplit" = "SplitShot"
        "QuantumSplitModule" = "SplitShot"
        "NovaSplit" = "SplitShot"
        "NovaSplitModule" = "SplitShot"
        "NovaVolley" = "Salvo"
        "NovaVolleyModule" = "Salvo"
        "NovaRapidFire" = "Torrent"
        "NovaRapidFireModule" = "Torrent"
        "NovaBarrage" = "Salvo"
        "NovaBarrageModule" = "Salvo"
    }
    
    # Find weapon parts (itIWL*)
    $weaponMatches = [regex]::Matches($content, 'itIWL(\w+)')
    foreach ($match in $weaponMatches) {
        $weaponName = $match.Groups[1].Value
        if ($weaponName -and $weaponsToGenerate -notcontains $weaponName) {
            $weaponsToGenerate += $weaponName
            # Each weapon needs a projectile sprite
            $projectileName = "${weaponName}Projectile"
            if ($projectilesToGenerate -notcontains $projectileName) {
                $projectilesToGenerate += $projectileName
            }
        }
    }
    
    # Find projectile/missile definitions (vt* for virtual projectiles, or missile ammoIDs)
    $projectileMatches = [regex]::Matches($content, '(?:ammoID|type)=["\s]*&(?:vt|it)(\w+);')
    foreach ($match in $projectileMatches) {
        $projectileName = $match.Groups[1].Value
        if ($projectileName -and 
            $projectileName -notmatch '^(IWL|Living|Evolved|Favor|Emergency|Trade|Navigation|Gravity|Explosion|Blast|Fragment)' -and
            $projectilesToGenerate -notcontains $projectileName) {
            $projectilesToGenerate += $projectileName
        }
    }
    
    # Find virtual projectile types (vt*)
    $virtualProjectileMatches = [regex]::Matches($content, '<ItemType[^>]*UNID="&(vt\w+);"[^>]*virtual="true"')
    foreach ($match in $virtualProjectileMatches) {
        $projectileName = $match.Groups[1].Value -replace '^vt', ''
        if ($projectileName -and $projectilesToGenerate -notcontains $projectileName) {
            $projectilesToGenerate += $projectileName
        }
    }
    
    # Find items (it*)
    $itemMatches = [regex]::Matches($content, 'it(\w+)\s+="0x[^"]+"')
    foreach ($match in $itemMatches) {
        $itemName = $match.Groups[1].Value
        # Filter out common patterns that aren't actual items
        if ($itemName -and 
            $itemName -notmatch '^(IWL|Living|Evolved|Favor|Emergency|Trade|Navigation|Gravity)' -and
            $itemsToGenerate -notcontains $itemName) {
            $itemsToGenerate += $itemName
        }
    }
}

Write-Log "" "INFO"
Write-Log "Asset Generation Summary:" "INFO"
Write-Log "  Ships: $($shipsToGenerate.Count)" "INFO"
Write-Log "  Weapons: $($weaponsToGenerate.Count)" "INFO"
Write-Log "  Items: $($itemsToGenerate.Count)" "INFO"
Write-Log "  Projectiles: $($projectilesToGenerate.Count)" "INFO"
Write-Log ""

# Generate assets
$totalAssets = 0
$generatedAssets = 0

# Generate ships (120 facings)
if ($GenerateShips -and $shipsToGenerate.Count -gt 0) {
    Write-Log "═══════════════════════════════════════════════════════════" "INFO"
    Write-Log "Generating Ship Assets (120 facings)..." "INFO"
    Write-Log "═══════════════════════════════════════════════════════════" "INFO"
    
    foreach ($ship in $shipsToGenerate) {
        $totalAssets++
        Write-Log "Generating ship: $ship" "INFO"
        
        try {
            $description = "Evolved $ship class ship for CrossModCompatibility"
            
            # Check if ship has a Nova Drift style mapping
            $novaStyle = ""
            if ($novaDriftStyleMap.ContainsKey($ship)) {
                $novaStyle = $novaDriftStyleMap[$ship]
                Write-Log "  Using Nova Drift style: $novaStyle" "INFO"
            }
            
            $params = @{
                AssetType = "Ship"
                AssetName = "Evolved$ship"
                Description = $description
                Quality = $Quality
                OutputDir = $OutputDir
                Facings = 120
                FrameWidth = 150
                FrameHeight = 150
                SpritesheetColumns = 10
            }
            
            if ($UseAI) {
                $params["UseAI"] = $true
                $params["OllamaModel"] = $OllamaModel
            }
            
            if ($novaStyle) {
                $params["NovaDriftStyle"] = $novaStyle
            }
            
            & $assetGenScript @params
            
            if ($LASTEXITCODE -eq 0) {
                $generatedAssets++
                Write-Log "  ✓ Generated: Evolved$ship" "SUCCESS"
            } else {
                Write-Log "  ✗ Failed: Evolved$ship" "ERROR"
            }
        } catch {
            Write-Log "  ✗ Error generating $ship : $_" "ERROR"
        }
    }
}

# Generate weapon icons and projectiles
if ($GenerateWeapons -and $weaponsToGenerate.Count -gt 0) {
    Write-Log "═══════════════════════════════════════════════════════════" "INFO"
    Write-Log "Generating Weapon Assets (Icons + Projectiles)..." "INFO"
    Write-Log "═══════════════════════════════════════════════════════════" "INFO"
    
    foreach ($weapon in $weaponsToGenerate) {
        # Generate weapon icon
        $totalAssets++
        Write-Log "Generating weapon icon: $weapon" "INFO"
        
        try {
            $description = "Weapon part: $weapon"
            
            # Check if weapon has a Nova Drift style mapping
            $novaWeaponStyle = ""
            foreach ($key in $novaDriftWeaponMap.Keys) {
                if ($weapon -like "*$key*") {
                    $novaWeaponStyle = $novaDriftWeaponMap[$key]
                    Write-Log "  Using Nova Drift weapon style: $novaWeaponStyle" "INFO"
                    break
                }
            }
            
            $params = @{
                AssetType = "Weapon"
                AssetName = $weapon
                Description = $description
                Quality = $Quality
                OutputDir = $OutputDir
                IconSize = 96
            }
            
            if ($UseAI) {
                $params["UseAI"] = $true
                $params["OllamaModel"] = $OllamaModel
            }
            
            if ($novaWeaponStyle) {
                $params["NovaDriftWeaponStyle"] = $novaWeaponStyle
            }
            
            & $assetGenScript @params
            
            if ($LASTEXITCODE -eq 0) {
                $generatedAssets++
                Write-Log "  ✓ Generated icon: $weapon" "SUCCESS"
            } else {
                Write-Log "  ✗ Failed icon: $weapon" "ERROR"
            }
        } catch {
            Write-Log "  ✗ Error generating weapon icon $weapon : $_" "ERROR"
        }
        
        # Generate weapon projectile sprite
        $projectileName = "${weapon}Projectile"
        $totalAssets++
        Write-Log "Generating weapon projectile: $projectileName" "INFO"
        
        try {
            $projectileDescription = "Projectile sprite for $weapon weapon"
            
            $projectileParams = @{
                AssetType = "Projectile"
                AssetName = $projectileName
                Description = $projectileDescription
                Quality = $Quality
                OutputDir = $OutputDir
                Size = 32  # Projectiles are typically smaller - use Size parameter directly
            }
            
            if ($UseAI) {
                $projectileParams["UseAI"] = $true
                $projectileParams["OllamaModel"] = $OllamaModel
            }
            
            if ($novaWeaponStyle) {
                # Use same style for projectile
                $projectileParams["NovaDriftWeaponStyle"] = $novaWeaponStyle
            }
            
            & $assetGenScript @projectileParams
            
            if ($LASTEXITCODE -eq 0) {
                $generatedAssets++
                Write-Log "  ✓ Generated projectile: $projectileName" "SUCCESS"
            } else {
                Write-Log "  ✗ Failed projectile: $projectileName" "ERROR"
            }
        } catch {
            Write-Log "  ✗ Error generating projectile $projectileName : $_" "ERROR"
        }
    }
}

# Generate item icons
if ($GenerateItems -and $itemsToGenerate.Count -gt 0) {
    Write-Log "═══════════════════════════════════════════════════════════" "INFO"
    Write-Log "Generating Item Icons..." "INFO"
    Write-Log "═══════════════════════════════════════════════════════════" "INFO"
    
    # Limit to first 50 items to avoid overwhelming the system
    $itemsToProcess = $itemsToGenerate | Select-Object -First 50
    
    foreach ($item in $itemsToProcess) {
        $totalAssets++
        Write-Log "Generating item icon: $item" "INFO"
        
        try {
            $description = "Item: $item"
            
            # Check if item has a Nova Drift mod style mapping
            $novaItemStyle = ""
            foreach ($key in $novaDriftItemMap.Keys) {
                if ($item -like "*$key*") {
                    $novaItemStyle = $novaDriftItemMap[$key]
                    Write-Log "  Using Nova Drift mod style: $novaItemStyle" "INFO"
                    break
                }
            }
            
            $params = @{
                AssetType = "Item"
                AssetName = $item
                Description = $description
                Quality = $Quality
                OutputDir = $OutputDir
                IconSize = 96
            }
            
            if ($UseAI) {
                $params["UseAI"] = $true
                $params["OllamaModel"] = $OllamaModel
            }
            
            if ($novaItemStyle) {
                $params["NovaDriftItemStyle"] = $novaItemStyle
            }
            
            & $assetGenScript @params
            
            if ($LASTEXITCODE -eq 0) {
                $generatedAssets++
                Write-Log "  ✓ Generated: $item" "SUCCESS"
            } else {
                Write-Log "  ✗ Failed: $item" "ERROR"
            }
        } catch {
            Write-Log "  ✗ Error generating $item : $_" "ERROR"
        }
    }
}

# Generate projectiles
if ($GenerateProjectiles -and $projectilesToGenerate.Count -gt 0) {
    Write-Log "═══════════════════════════════════════════════════════════" "INFO"
    Write-Log "Generating Projectile Sprites..." "INFO"
    Write-Log "═══════════════════════════════════════════════════════════" "INFO"
    
    # Limit to first 100 projectiles to avoid overwhelming the system
    $projectilesToProcess = $projectilesToGenerate | Select-Object -First 100
    
    foreach ($projectile in $projectilesToProcess) {
        $totalAssets++
        Write-Log "Generating projectile sprite: $projectile" "INFO"
        
        try {
            $description = "Projectile sprite: $projectile"
            
            $params = @{
                AssetType = "Projectile"
                AssetName = $projectile
                Description = $description
                Quality = $Quality
                OutputDir = $OutputDir
                Size = 32  # Projectiles are typically smaller - use Size parameter directly
            }
            
            if ($UseAI) {
                $params["UseAI"] = $true
                $params["OllamaModel"] = $OllamaModel
            }
            
            & $assetGenScript @params
            
            if ($LASTEXITCODE -eq 0) {
                $generatedAssets++
                Write-Log "  ✓ Generated: $projectile" "SUCCESS"
            } else {
                Write-Log "  ✗ Failed: $projectile" "ERROR"
            }
        } catch {
            Write-Log "  ✗ Error generating $projectile : $_" "ERROR"
        }
    }
}

# Generate weapon parts spritesheet
if ($GenerateWeapons -and $weaponsToGenerate.Count -gt 0) {
    Write-Log "═══════════════════════════════════════════════════════════" "INFO"
    Write-Log "Generating Weapon Parts Spritesheet..." "INFO"
    Write-Log "═══════════════════════════════════════════════════════════" "INFO"
    
    try {
        # Calculate spritesheet size (8x8 grid = 64 items, adjust as needed)
        $columns = 8
        $rows = [math]::Ceiling($weaponsToGenerate.Count / $columns)
        
        & $assetGenScript `
            -AssetType Spritesheet `
            -AssetName "IWLWeaponParts" `
            -Description "Weapon Labs 51 weapon parts spritesheet" `
            -Quality $Quality `
            -OutputDir $OutputDir `
            -SpritesheetColumns $columns `
            -SpritesheetRows $rows `
            -ResourceName "rsIWLWeaponParts"
        
        if ($LASTEXITCODE -eq 0) {
            $generatedAssets++
            Write-Log "  ✓ Generated: IWLWeaponParts spritesheet" "SUCCESS"
        } else {
            Write-Log "  ✗ Failed: IWLWeaponParts spritesheet" "ERROR"
        }
    } catch {
        Write-Log "  ✗ Error generating spritesheet : $_" "ERROR"
    }
}

Write-Log "" "INFO"
Write-Log "═══════════════════════════════════════════════════════════" "INFO"
Write-Log "Generation Complete!" "SUCCESS"
Write-Log "  Total assets processed: $totalAssets" "INFO"
Write-Log "  Successfully generated: $generatedAssets" "SUCCESS"
Write-Log "  Failed: $($totalAssets - $generatedAssets)" "INFO"
Write-Log "═══════════════════════════════════════════════════════════" "INFO"
Write-Log "Output directory: $OutputDir" "INFO"
Write-Log "Log file: $logFile" "INFO"

