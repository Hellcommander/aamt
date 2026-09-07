#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate assets for the Moving Floating Dungeon Generator system.
    
.DESCRIPTION
    Generates all visual and audio assets needed for procedurally generated floating dungeons:
    - Platform tiles (floor, wall, corner, edge pieces)
    - Dungeon decorations and props
    - Background elements (sky, clouds)

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}
    - Spawn markers and indicators
    - Entrance/exit portals
    - Particle effects
    - UI elements
    - Sound effects
    
.PARAMETER ModPath
    Path to the mod directory
    
.PARAMETER OllamaModel
    Ollama model to use
    
.PARAMETER PlanningModel
    Planning model for Ollama
    
.PARAMETER VisualModel
    Visual model for Ollama
    
.PARAMETER UseCppBackend
    Use C++ backend for generation
    
.PARAMETER SkipExisting
    Skip assets that already exist
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$ModPath = "F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery",
    
    [Parameter(Mandatory=$false)]
    [string]$OllamaModel = "codellama:7b-instruct",
    
    [Parameter(Mandatory=$false)]
    [string]$PlanningModel = "",
    
    [Parameter(Mandatory=$false)]
    [string]$VisualModel = "wizardlm-uncensored",
    
    [Parameter(Mandatory=$false)]
    [bool]$UseCppBackend = $true,
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipExisting
)

$ErrorActionPreference = "Stop"
# Validate ModPath is not empty
if ([string]::IsNullOrWhiteSpace($ModPath)) {
    Write-Host "Error: ModPath cannot be empty" -ForegroundColor Red
    Write-Host "  Please provide a valid mod path or use the default" -ForegroundColor Gray
    exit 1
}

$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$assetGenerator = Join-Path $PSScriptRoot "StarboundOllamaAssetGenerator.ps1"

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Moving Floating Dungeon Generator Asset Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$generated = 0
$failed = 0
$skipped = 0

# Generate platform tiles
Write-Host "Generating Platform Tiles..." -ForegroundColor Yellow
Write-Host ""

$platformTiles = @(
    @{Id="dungeon_platform_floor"; Name="Dungeon Floor"; Desc="Main floor tile for floating dungeon platform, stone texture, 16x16 pixels"},
    @{Id="dungeon_platform_wall"; Name="Dungeon Wall"; Desc="Vertical wall tile for dungeon edges, stone brick texture, 16x16 pixels"},
    @{Id="dungeon_platform_corner"; Name="Dungeon Corner"; Desc="Corner piece for dungeon platforms, rounded stone corner, 16x16 pixels"},
    @{Id="dungeon_platform_edge_top"; Name="Top Edge"; Desc="Top edge tile for platform boundaries, stone edge with detail, 16x16 pixels"},
    @{Id="dungeon_platform_edge_bottom"; Name="Bottom Edge"; Desc="Bottom edge tile for platform boundaries, stone edge with detail, 16x16 pixels"},
    @{Id="dungeon_platform_edge_left"; Name="Left Edge"; Desc="Left edge tile for platform boundaries, stone edge with detail, 16x16 pixels"},
    @{Id="dungeon_platform_edge_right"; Name="Right Edge"; Desc="Right edge tile for platform boundaries, stone edge with detail, 16x16 pixels"},
    @{Id="dungeon_platform_cracked"; Name="Cracked Platform"; Desc="Damaged/cracked platform tile, weathered stone, 16x16 pixels"},
    @{Id="dungeon_platform_mossy"; Name="Mossy Platform"; Desc="Moss-covered platform tile, aged stone with green moss, 16x16 pixels"},
    @{Id="dungeon_platform_magical"; Name="Magical Platform"; Desc="Magical glowing platform tile, enchanted stone with runes, 16x16 pixels"}
)

foreach ($tile in $platformTiles) {
    # Validate $ModPath before Join-Path
$tilePath = Join-Path $ModPath "tiles\${tile.Id}.png"
 if ([string]::IsNullOrWhiteSpace($tilePath)) {
        Write-Host "  [FAIL] tilePath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
 if ([string]::IsNullOrWhiteSpace($tilePath)) {
        Write-Host "  [FAIL] tilePath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
    if ($SkipExisting -and (Test-Path $tilePath)) {
        $skipped++
        Write-Host "  [SKIP] Platform tile already exists: $($tile.Id)" -ForegroundColor Gray
    } else {
        try {
            $params = @{
                AssetType = "Tile"
                AssetName = $tile.Id
                Prompt = "A tile sprite: $($tile.Name) - $($tile.Desc). Seamless tileable texture"
                OllamaModel = $OllamaModel
                # Validate $ModPath before Join-Path
$tempOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                    Write-Host "  [FAIL] tempOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                    continue
                }
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                    Write-Host "  [FAIL] OutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                    continue
                }
            OutputDir = $tempOutputDir
            }
            if ($PlanningModel) { $params['PlanningModel'] = $PlanningModel }
            if ($VisualModel) { $params['VisualModel'] = $VisualModel }
            $params['UseCppBackend'] = $UseCppBackend
            
            & $assetGenerator @params | Out-Null
            $generated++
            Write-Host "  [OK] Generated platform tile: $($tile.Id)" -ForegroundColor Green
        } catch {
            $failed++
            Write-Host "  [FAIL] Platform tile $($tile.Id) : $_" -ForegroundColor Red
        }
    }
}

Write-Host ""

# Generate dungeon decorations
Write-Host "Generating Dungeon Decorations..." -ForegroundColor Yellow
Write-Host ""

$decorations = @(
    @{Id="dungeon_pillar"; Name="Stone Pillar"; Desc="Decorative stone pillar for dungeon rooms, vertical column"},
    @{Id="dungeon_rune_stone"; Name="Rune Stone"; Desc="Magical rune-carved stone, glowing runes"},
    @{Id="dungeon_crystal_cluster"; Name="Crystal Cluster"; Desc="Cluster of magical crystals growing from platform"},
    @{Id="dungeon_brazier"; Name="Brazier"; Desc="Magical brazier with floating flame, light source"},
    @{Id="dungeon_archway"; Name="Archway"; Desc="Decorative stone archway between rooms"},
    @{Id="dungeon_statue"; Name="Statue"; Desc="Ancient stone statue, weathered and mysterious"},
    @{Id="dungeon_altar"; Name="Altar"; Desc="Magical altar with glowing symbols"},
    @{Id="dungeon_floating_orb"; Name="Floating Orb"; Desc="Magical floating energy orb, ambient light"},
    @{Id="dungeon_chain"; Name="Chain"; Desc="Hanging chain decoration, connects to sky"},
    @{Id="dungeon_skull_pile"; Name="Skull Pile"; Desc="Pile of bones/skulls, atmospheric decoration"}
)

foreach ($dec in $decorations) {
    # Validate $ModPath before Join-Path
$spritePath = Join-Path $ModPath "objects\dungeon\${dec.Id}.png"
 if ([string]::IsNullOrWhiteSpace($spritePath)) {
        Write-Host "  [FAIL] spritePath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
 if ([string]::IsNullOrWhiteSpace($spritePath)) {
        Write-Host "  [FAIL] spritePath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
    if ($SkipExisting -and (Test-Path $spritePath)) {
        $skipped++
        Write-Host "  [SKIP] Decoration already exists: $($dec.Id)" -ForegroundColor Gray
    } else {
        try {
            $params = @{
                AssetType = "Sprite"
                AssetName = $dec.Id
                Prompt = "A dungeon decoration sprite: $($dec.Name) - $($dec.Desc). Atmospheric dungeon prop, 32x32 to 64x64 pixels"
                OllamaModel = $OllamaModel
                # Validate $ModPath before Join-Path
$tempOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                    Write-Host "  [FAIL] tempOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                    continue
                }
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                    Write-Host "  [FAIL] OutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                    continue
                }
            OutputDir = $tempOutputDir
            }
            if ($PlanningModel) { $params['PlanningModel'] = $PlanningModel }
            if ($VisualModel) { $params['VisualModel'] = $VisualModel }
            $params['UseCppBackend'] = $UseCppBackend
            
            & $assetGenerator @params | Out-Null
            $generated++
            Write-Host "  [OK] Generated decoration: $($dec.Id)" -ForegroundColor Green
        } catch {
            $failed++
            Write-Host "  [FAIL] Decoration $($dec.Id) : $_" -ForegroundColor Red
        }
    }
}

Write-Host ""

# Generate background elements
Write-Host "Generating Background Elements..." -ForegroundColor Yellow
Write-Host ""

$backgrounds = @(
    @{Id="dungeon_sky_background"; Name="Sky Background"; Desc="Sky background for floating dungeons, clouds and atmosphere"},
    @{Id="dungeon_cloud_layer1"; Name="Cloud Layer 1"; Desc="Foreground cloud layer, close clouds"},
    @{Id="dungeon_cloud_layer2"; Name="Cloud Layer 2"; Desc="Midground cloud layer, distant clouds"},
    @{Id="dungeon_cloud_layer3"; Name="Cloud Layer 3"; Desc="Background cloud layer, far distant clouds"},
    @{Id="dungeon_sun"; Name="Sun"; Desc="Sun or moon in sky background, atmospheric lighting"},
    @{Id="dungeon_stars"; Name="Stars"; Desc="Starfield background for night sky dungeons"}
)

foreach ($bg in $backgrounds) {
    # Validate $ModPath before Join-Path
$bgPath = Join-Path $ModPath "backgrounds\dungeon\${bg.Id}.png"
 if ([string]::IsNullOrWhiteSpace($bgPath)) {
        Write-Host "  [FAIL] bgPath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
 if ([string]::IsNullOrWhiteSpace($bgPath)) {
        Write-Host "  [FAIL] bgPath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
    if ($SkipExisting -and (Test-Path $bgPath)) {
        $skipped++
        Write-Host "  [SKIP] Background already exists: $($bg.Id)" -ForegroundColor Gray
    } else {
        try {
            $params = @{
                AssetType = "Texture"
                AssetName = $bg.Id
                Prompt = "A background texture: $($bg.Name) - $($bg.Desc). Atmospheric sky/cloud texture, seamless or tiling"
                OllamaModel = $OllamaModel
                # Validate $ModPath before Join-Path
$tempOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                    Write-Host "  [FAIL] tempOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                    continue
                }
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                    Write-Host "  [FAIL] OutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                    continue
                }
            OutputDir = $tempOutputDir
            }
            if ($PlanningModel) { $params['PlanningModel'] = $PlanningModel }
            if ($VisualModel) { $params['VisualModel'] = $VisualModel }
            $params['UseCppBackend'] = $UseCppBackend
            
            & $assetGenerator @params | Out-Null
            $generated++
            Write-Host "  [OK] Generated background: $($bg.Id)" -ForegroundColor Green
        } catch {
            $failed++
            Write-Host "  [FAIL] Background $($bg.Id) : $_" -ForegroundColor Red
        }
    }
}

Write-Host ""

# Generate spawn markers
Write-Host "Generating Spawn Markers..." -ForegroundColor Yellow
Write-Host ""

$spawnMarkers = @(
    @{Id="spawn_marker_ingredient"; Name="Ingredient Spawn"; Desc="Visual marker for ingredient spawn point, glowing indicator"},
    @{Id="spawn_marker_spellstone"; Name="Spellstone Spawn"; Desc="Visual marker for spellstone spawn point, magical glow"},
    @{Id="spawn_marker_mech"; Name="Mech Spawn"; Desc="Visual marker for mech spawn point, mechanical indicator"},
    @{Id="spawn_marker_generic"; Name="Generic Spawn"; Desc="Generic spawn point marker, neutral indicator"}
)

foreach ($marker in $spawnMarkers) {
    # Validate $ModPath before Join-Path
$markerPath = Join-Path $ModPath "interface\icons\${marker.Id}.png"
 if ([string]::IsNullOrWhiteSpace($markerPath)) {
        Write-Host "  [FAIL] markerPath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
 if ([string]::IsNullOrWhiteSpace($markerPath)) {
        Write-Host "  [FAIL] markerPath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
    if ($SkipExisting -and (Test-Path $markerPath)) {
        $skipped++
        Write-Host "  [SKIP] Spawn marker already exists: $($marker.Id)" -ForegroundColor Gray
    } else {
        try {
            $params = @{
                AssetType = "Icon"
                AssetName = $marker.Id
                Prompt = "A spawn marker icon: $($marker.Name) - $($marker.Desc). Small indicator icon, 16x16 to 32x32 pixels"
                OllamaModel = $OllamaModel
                # Validate $ModPath before Join-Path
$tempOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                    Write-Host "  [FAIL] tempOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                    continue
                }
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                    Write-Host "  [FAIL] OutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                    continue
                }
            OutputDir = $tempOutputDir
            }
            if ($PlanningModel) { $params['PlanningModel'] = $PlanningModel }
            if ($VisualModel) { $params['VisualModel'] = $VisualModel }
            $params['UseCppBackend'] = $UseCppBackend
            
            & $assetGenerator @params | Out-Null
            $generated++
            Write-Host "  [OK] Generated spawn marker: $($marker.Id)" -ForegroundColor Green
        } catch {
            $failed++
            Write-Host "  [FAIL] Spawn marker $($marker.Id) : $_" -ForegroundColor Red
        }
    }
}

Write-Host ""

# Generate entrance/exit portals
Write-Host "Generating Entrance/Exit Portals..." -ForegroundColor Yellow
Write-Host ""

$portals = @(
    @{Id="dungeon_portal_entrance"; Name="Dungeon Entrance"; Desc="Portal entrance to floating dungeon, magical gateway"},
    @{Id="dungeon_portal_exit"; Name="Dungeon Exit"; Desc="Portal exit from floating dungeon, return gateway"},
    @{Id="dungeon_portal_interior"; Name="Interior Portal"; Desc="Portal between dungeon rooms, teleport gateway"}
)

foreach ($portal in $portals) {
    # Validate $ModPath before Join-Path
$portalPath = Join-Path $ModPath "objects\dungeon\${portal.Id}.png"
 if ([string]::IsNullOrWhiteSpace($portalPath)) {
        Write-Host "  [FAIL] portalPath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
 if ([string]::IsNullOrWhiteSpace($portalPath)) {
        Write-Host "  [FAIL] portalPath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
    if ($SkipExisting -and (Test-Path $portalPath)) {
        $skipped++
        Write-Host "  [SKIP] Portal already exists: $($portal.Id)" -ForegroundColor Gray
    } else {
        try {
            $params = @{
                AssetType = "Sprite"
                AssetName = $portal.Id
                Prompt = "A portal sprite: $($portal.Name) - $($portal.Desc). Magical portal with swirling energy, 64x64 pixels"
                OllamaModel = $OllamaModel
                # Validate $ModPath before Join-Path
$tempOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                    Write-Host "  [FAIL] tempOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                    continue
                }
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                    Write-Host "  [FAIL] OutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                    continue
                }
            OutputDir = $tempOutputDir
            }
            if ($PlanningModel) { $params['PlanningModel'] = $PlanningModel }
            if ($VisualModel) { $params['VisualModel'] = $VisualModel }
            $params['UseCppBackend'] = $UseCppBackend
            
            & $assetGenerator @params | Out-Null
            $generated++
            Write-Host "  [OK] Generated portal: $($portal.Id)" -ForegroundColor Green
        } catch {
            $failed++
            Write-Host "  [FAIL] Portal $($portal.Id) : $_" -ForegroundColor Red
        }
    }
}

Write-Host ""

# Generate particle effects
Write-Host "Generating Particle Effects..." -ForegroundColor Yellow
Write-Host ""

$particles = @(
    @{Id="dungeon_atmosphere_clouds"; Name="Atmospheric Clouds"; Type="Smoke"; Desc="Floating clouds around dungeon, ambient atmosphere"},
    @{Id="dungeon_magic_aura"; Name="Magic Aura"; Type="Magic"; Desc="Magical aura surrounding floating dungeon"},
    @{Id="dungeon_wind_particles"; Name="Wind Particles"; Type="Ambient"; Desc="Wind particles flowing around platform"},
    @{Id="dungeon_portal_energy"; Name="Portal Energy"; Type="Electric"; Desc="Energy particles from portal activation"},
    @{Id="dungeon_drift_dust"; Name="Drift Dust"; Type="Smoke"; Desc="Dust particles from moving platform"},
    @{Id="dungeon_spawn_glow"; Name="Spawn Glow"; Type="Magic"; Desc="Glowing particles at spawn points"},
    @{Id="dungeon_cellular_glow"; Name="Cellular Glow"; Type="Magic"; Desc="Glow effect for cellular automata generation"}
)

foreach ($particle in $particles) {
    # Validate $ModPath before Join-Path
$particlePath = Join-Path $ModPath "particles\magitech\${particle.Id}.particle"
 if ([string]::IsNullOrWhiteSpace($particlePath)) {
        Write-Host "  [FAIL] particlePath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
 if ([string]::IsNullOrWhiteSpace($particlePath)) {
        Write-Host "  [FAIL] particlePath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
    if ($SkipExisting -and (Test-Path $particlePath)) {
        $skipped++
        Write-Host "  [SKIP] Particle already exists: $($particle.Id)" -ForegroundColor Gray
    } else {
        try {
            $params = @{
                AssetType = "Particle"
                AssetName = $particle.Id
                Prompt = "A particle effect: $($particle.Name) - $($particle.Desc). $($particle.Type) type atmospheric effect"
                OllamaModel = $OllamaModel
                # Validate $ModPath before Join-Path
$tempOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                    Write-Host "  [FAIL] tempOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                    continue
                }
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                    Write-Host "  [FAIL] OutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                    continue
                }
            OutputDir = $tempOutputDir
            }
            if ($PlanningModel) { $params['PlanningModel'] = $PlanningModel }
            if ($VisualModel) { $params['VisualModel'] = $VisualModel }
            $params['UseCppBackend'] = $UseCppBackend
            
            & $assetGenerator @params | Out-Null
            $generated++
            Write-Host "  [OK] Generated particle: $($particle.Id)" -ForegroundColor Green
        } catch {
            $failed++
            Write-Host "  [FAIL] Particle $($particle.Id) : $_" -ForegroundColor Red
        }
    }
}

Write-Host ""

# Generate UI elements
Write-Host "Generating UI Elements..." -ForegroundColor Yellow
Write-Host ""

$uiElements = @(
    @{Id="dungeon_map_icon"; Name="Dungeon Map Icon"; Desc="Icon for dungeon on minimap, floating platform icon"},
    @{Id="dungeon_path_indicator"; Name="Path Indicator"; Desc="UI indicator showing dungeon movement path"},
    @{Id="dungeon_cell_indicator"; Name="Cell Indicator"; Desc="Visual indicator for dungeon cell grid"},
    @{Id="dungeon_spawn_density_gauge"; Name="Spawn Density Gauge"; Desc="UI gauge showing spawn density settings"},
    @{Id="dungeon_waypoint_marker"; Name="Waypoint Marker"; Desc="Marker for dungeon path waypoints on map"}
)

foreach ($ui in $uiElements) {
    # Validate $ModPath before Join-Path
$uiPath = Join-Path $ModPath "interface\icons\${ui.Id}.png"
 if ([string]::IsNullOrWhiteSpace($uiPath)) {
        Write-Host "  [FAIL] uiPath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
 if ([string]::IsNullOrWhiteSpace($uiPath)) {
        Write-Host "  [FAIL] uiPath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
    if ($SkipExisting -and (Test-Path $uiPath)) {
        $skipped++
        Write-Host "  [SKIP] UI element already exists: $($ui.Id)" -ForegroundColor Gray
    } else {
        try {
            $params = @{
                AssetType = "Icon"
                AssetName = $ui.Id
                Prompt = "A UI element: $($ui.Name) - $($ui.Desc). Clean interface style, appropriate size"
                OllamaModel = $OllamaModel
                # Validate $ModPath before Join-Path
$tempOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                    Write-Host "  [FAIL] tempOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                    continue
                }
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                    Write-Host "  [FAIL] OutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                    continue
                }
            OutputDir = $tempOutputDir
            }
            if ($PlanningModel) { $params['PlanningModel'] = $PlanningModel }
            if ($VisualModel) { $params['VisualModel'] = $VisualModel }
            $params['UseCppBackend'] = $UseCppBackend
            
            & $assetGenerator @params | Out-Null
            $generated++
            Write-Host "  [OK] Generated UI element: $($ui.Id)" -ForegroundColor Green
        } catch {
            $failed++
            Write-Host "  [FAIL] UI element $($ui.Id) : $_" -ForegroundColor Red
        }
    }
}

Write-Host ""

# Generate sound effects
Write-Host "Generating Sound Effects..." -ForegroundColor Yellow
Write-Host ""

$sounds = @(
    @{Id="dungeon_ambient_wind"; Type="Ambient"; Desc="Ambient wind sound around floating dungeon"},
    @{Id="dungeon_platform_movement"; Type="Mechanical"; Desc="Sound of platform moving through air"},
    @{Id="dungeon_cellular_generation"; Type="Magic"; Desc="Sound of cellular automata generating dungeon"},
    @{Id="dungeon_spawn_ingredient"; Type="Magic"; Desc="Sound when ingredient spawns"},
    @{Id="dungeon_spawn_spellstone"; Type="Magic"; Desc="Sound when spellstone spawns"},
    @{Id="dungeon_spawn_mech"; Type="Mechanical"; Desc="Sound when mech spawns"},
    @{Id="dungeon_portal_activate"; Type="Magic"; Desc="Portal activation sound"},
    @{Id="dungeon_portal_teleport"; Type="Magic"; Desc="Portal teleportation sound"},
    @{Id="dungeon_waypoint_reach"; Type="Ambient"; Desc="Sound when reaching waypoint"},
    @{Id="dungeon_atmosphere_ambient"; Type="Ambient"; Desc="General atmospheric ambient sound"}
)

foreach ($sound in $sounds) {
    # Validate $ModPath before Join-Path
$soundPath = Join-Path $ModPath "sfx\${sound.Id}.ogg"
 if ([string]::IsNullOrWhiteSpace($soundPath)) {
        Write-Host "  [FAIL] soundPath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
 if ([string]::IsNullOrWhiteSpace($soundPath)) {
        Write-Host "  [FAIL] soundPath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
    if ($SkipExisting -and (Test-Path $soundPath)) {
        $skipped++
        Write-Host "  [SKIP] Sound already exists: $($sound.Id)" -ForegroundColor Gray
    } else {
        try {
            $params = @{
                AssetType = "Sound"
                AssetName = $sound.Id
                Prompt = "A sound effect: $($sound.Desc). $($sound.Type) type sound"
                OllamaModel = $OllamaModel
                # Validate $ModPath before Join-Path
$tempOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                    Write-Host "  [FAIL] tempOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                    continue
                }
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                    Write-Host "  [FAIL] OutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                    continue
                }
            OutputDir = $tempOutputDir
            }
            if ($PlanningModel) { $params['PlanningModel'] = $PlanningModel }
            if ($VisualModel) { $params['VisualModel'] = $VisualModel }
            $params['UseCppBackend'] = $UseCppBackend
            
            # Add sound-specific parameters
            $soundParams = @{
                SoundType = $sound.Type
                Format = "ogg"
            }
            $params['Parameters'] = $soundParams
            
            & $assetGenerator @params | Out-Null
            $generated++
            Write-Host "  [OK] Generated sound: $($sound.Id)" -ForegroundColor Green
        } catch {
            $failed++
            Write-Host "  [FAIL] Sound $($sound.Id) : $_" -ForegroundColor Red
        }
    }
}

Write-Host ""

# Generate animation sprites for moving elements
Write-Host "Generating Animation Sprites..." -ForegroundColor Yellow
Write-Host ""

$animations = @(
    @{Id="dungeon_portal_animated"; Name="Animated Portal"; Desc="Animated portal with swirling energy, 8 frames"},
    @{Id="dungeon_floating_orb_animated"; Name="Animated Floating Orb"; Desc="Animated floating orb with pulsing glow, 6 frames"},
    @{Id="dungeon_brazier_flame"; Name="Brazier Flame"; Desc="Animated flame for brazier, 8 frames"},
    @{Id="dungeon_crystal_growth"; Name="Crystal Growth"; Desc="Animated crystal cluster growing, 10 frames"}
)

foreach ($anim in $animations) {
    # Validate $ModPath before Join-Path
$animPath = Join-Path $ModPath "animations\dungeon\${anim.Id}.animation"
 if ([string]::IsNullOrWhiteSpace($animPath)) {
        Write-Host "  [FAIL] animPath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
 if ([string]::IsNullOrWhiteSpace($animPath)) {
        Write-Host "  [FAIL] animPath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
    if ($SkipExisting -and (Test-Path $animPath)) {
        $skipped++
        Write-Host "  [SKIP] Animation already exists: $($anim.Id)" -ForegroundColor Gray
    } else {
        try {
            $params = @{
                AssetType = "AnimationSprite"
                AssetName = $anim.Id
                Prompt = "An animation spritesheet: $($anim.Name) - $($anim.Desc). Horizontal spritesheet"
                OllamaModel = $OllamaModel
                # Validate $ModPath before Join-Path
$tempOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                    Write-Host "  [FAIL] tempOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                    continue
                }
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                    Write-Host "  [FAIL] OutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                    continue
                }
            OutputDir = $tempOutputDir
            }
            if ($PlanningModel) { $params['PlanningModel'] = $PlanningModel }
            if ($VisualModel) { $params['VisualModel'] = $VisualModel }
            $params['UseCppBackend'] = $UseCppBackend
            
            & $assetGenerator @params | Out-Null
            $generated++
            Write-Host "  [OK] Generated animation: $($anim.Id)" -ForegroundColor Green
        } catch {
            $failed++
            Write-Host "  [FAIL] Animation $($anim.Id) : $_" -ForegroundColor Red
        }
    }
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Generation Complete" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Generated: $generated assets" -ForegroundColor Green
Write-Host "Skipped: $skipped assets (already exist)" -ForegroundColor Gray
Write-Host "Failed: $failed assets" -ForegroundColor $(if ($failed -gt 0) { "Red" } else { "Green" })
Write-Host ""
