#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate assets for the Hydra Chassis modular mech system.
    
.DESCRIPTION
    Generates all assets needed for the Hydra Chassis including:
    - Base frame concept art
    - All 17 modular component sprites
    - Module icons

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}
    - Assembly previews
    
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
Write-Host "  Hydra Chassis Modular Mech Asset Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$generated = 0
$failed = 0
$skipped = 0

# Generate base frame concept art
Write-Host "Generating Base Frame Concept Art..." -ForegroundColor Yellow
Write-Host ""

# Validate $ModPath before Join-Path
$baseFramePath = Join-Path $ModPath "sprites\mechs\hydraBase_concept.png"
 if ([string]::IsNullOrWhiteSpace($baseFramePath)) {
    Write-Host "  [FAIL] baseFramePath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($baseFramePath)) {
    Write-Host "  [FAIL] baseFramePath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if ($SkipExisting -and (Test-Path $baseFramePath)) {
    $skipped++
    Write-Host "  [SKIP] Base frame already exists" -ForegroundColor Gray
} else {
    try {
        $params = @{
            AssetType = "Sprite"
            AssetName = "hydraBase_concept"
            Prompt = "Concept art for Hydra Chassis base frame mech. Modular mech chassis with hard-surface details, panel lines, rivets, pistons, cables. Biomechanical design, 512x512 pixels, side view"
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
        Write-Host "  [OK] Generated base frame concept" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] Base frame: $_" -ForegroundColor Red
    }
}

Write-Host ""

# Define all 17 modules with their art brief details
$modules = @(
    @{Id="abyssalMaw"; Slot="head"; Name="Abyssal Maw"; Desc="Bone-white draconic skull plates grafted over cockpit, rune-etched eye sockets glowing electric blue, crackled fissures along jaw, lethal skeletal predator"},
    @{Id="chitinSpine"; Slot="mid"; Name="Chitin Spine"; Desc="Overlapping vaulted carapace segments coiling around torso, razor-sharp spines tipped with faint blue plasma, flexible segment joints, living armor shell"},
    @{Id="barbedLash"; Slot="tail"; Name="Barbed Lash"; Desc="Segmented whip-tail of interlocked barb plates, venom-violet fluid dripping from hooked edges, cable-like tubing running along length, biomechanical stinger"},
    @{Id="mandibleSwarm"; Slot="head"; Name="Mandible Swarm"; Desc="Twin hydraulic pincers flanking cockpit, each lined with sensor feelers, inner grinding spikes, exposed actuator rods, crushing insectoid grip"},
    @{Id="legionCrawler"; Slot="mid"; Name="Legion Crawler"; Desc="Dozens of slim jointed legs splayed from waist, piston-driven joints, segmented cabling like muscle fibers, rapid skittering mass"},
    @{Id="clubbedTail"; Slot="tail"; Name="Clubbed Tail"; Desc="Heavy mace-like club reinforced with black chitin ribs, circular rivets, shock-absorbent coil springs at base, blunt-force battering ram"},
    @{Id="fangstrike"; Slot="head"; Name="Fangstrike"; Desc="Snake-skull mask over cockpit, elongated fangs dripping acid, translucent venom sacs, green-glow before each strike, venomous ambush"},
    @{Id="constrictorCoil"; Slot="mid"; Name="Constrictor Coil"; Desc="Smooth rotating band of scale plates wrapping waist, retractable clamps hidden beneath plates, subtle hydraulic bands, squeezing immobilizing power"},
    @{Id="venomLash"; Slot="tail"; Name="Venom Lash"; Desc="Slender tail ending in glowing plasma barb, fluid conduits pulsing with neon green toxin, precise corrosive strike"},
    @{Id="cycloneRazor"; Slot="ring"; Name="Cyclone Razor"; Desc="Hovering ring of seven spinning steel blades, magnetic nodes, electric sparks at blade roots, whirling cutting storm"},
    @{Id="turbineSlice"; Slot="rotor"; Name="Turbine Slice"; Desc="Vertical stack of high-speed rotor blades in cylindrical housing, intake vents, heat-vent channels, exhaust flares, slicing gale force"},
    @{Id="grapnelHook"; Slot="arm"; Name="Grapnel Hook"; Desc="Telescoping claw and winch drum mounted on shoulder, coiled high-tension cable, ratchet gears, anchoring yanking power"},
    @{Id="chargeHorn"; Slot="ram"; Name="Charge Horn"; Desc="Reinforced ram horn fused to nose cone, piston-vent ports, steam-burst valves, head-on battering"},
    @{Id="predatorDive"; Slot="legs"; Name="Predator Dive"; Desc="Slender bird-leg assemblies with spring-loaded calves, talon toes, knee-mounted boost thrusters, aerial pounce"},
    @{Id="amphibianLeap"; Slot="legs"; Name="Amphibian Leap"; Desc="Stout hydraulic legs with visible coil springs, web-patterned plating, shock-absorbent pads, spring-powered launch"},
    @{Id="webWeaver"; Slot="legs"; Name="Web Weaver"; Desc="Eight jointed limbs with spinnerets on wrist plates, silk-line cartridges, magnetic clamp claws, wall-crawling arachnid"},
    @{Id="scarabShell"; Slot="dome"; Name="Scarab Shell"; Desc="Domed beetle shell that folds over cockpit, spiked wheel pods on sides, segmented hinge plates, rolling fortress"}
)

# Generate module sprites
Write-Host "Generating Module Sprites..." -ForegroundColor Yellow
Write-Host ""

foreach ($module in $modules) {
    # Validate $ModPath before Join-Path
$spritePath = Join-Path $ModPath "sprites\modules\$($module.Id).png"
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
        Write-Host "  [SKIP] Module sprite already exists: $($module.Id)" -ForegroundColor Gray
    } else {
        try {
            $params = @{
                AssetType = "Sprite"
                AssetName = $module.Id
                Prompt = "Modular mech component sprite: $($module.Name) - $($module.Desc). Hard-surface details: panel lines, rivets, pistons, cables. Beast theme: $($module.Slot) slot. 256x256 pixels, side view"
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
            Write-Host "  [OK] Generated module sprite: $($module.Id)" -ForegroundColor Green
        } catch {
            $failed++
            Write-Host "  [FAIL] Module sprite $($module.Id) : $_" -ForegroundColor Red
        }
    }
}

Write-Host ""

# Generate module icons
Write-Host "Generating Module Icons..." -ForegroundColor Yellow
Write-Host ""

foreach ($module in $modules) {
    # Validate $ModPath before Join-Path
$iconPath = Join-Path $ModPath "interface\icons\modules\$($module.Id)_icon.png"
 if ([string]::IsNullOrWhiteSpace($iconPath)) {
        Write-Host "  [FAIL] iconPath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
 if ([string]::IsNullOrWhiteSpace($iconPath)) {
        Write-Host "  [FAIL] iconPath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
    if ($SkipExisting -and (Test-Path $iconPath)) {
        $skipped++
        Write-Host "  [SKIP] Module icon already exists: $($module.Id)" -ForegroundColor Gray
    } else {
        try {
            $params = @{
                AssetType = "Icon"
                AssetName = "$($module.Id)_icon"
                Prompt = "Icon for $($module.Name) module: $($module.Desc). Module icon, 64x64 pixels, clear silhouette"
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
            Write-Host "  [OK] Generated module icon: $($module.Id)" -ForegroundColor Green
        } catch {
            $failed++
            Write-Host "  [FAIL] Module icon $($module.Id) : $_" -ForegroundColor Red
        }
    }
}

Write-Host ""

# Generate assembly previews for common combinations
Write-Host "Generating Assembly Previews..." -ForegroundColor Yellow
Write-Host ""

$assemblies = @(
    @{Id="hydraPredator"; Modules=@("abyssalMaw", "chitinSpine", "barbedLash", "predatorDive"); Name="Predator Assembly"; Desc="Full predator configuration with abyssal maw, chitin spine, barbed lash, and predator dive legs"},
    @{Id="hydraCrawler"; Modules=@("mandibleSwarm", "legionCrawler", "clubbedTail", "webWeaver"); Name="Crawler Assembly"; Desc="Crawler configuration with mandible swarm, legion crawler, clubbed tail, and web weaver legs"},
    @{Id="hydraStriker"; Modules=@("fangstrike", "constrictorCoil", "venomLash", "amphibianLeap"); Name="Striker Assembly"; Desc="Striker configuration with fangstrike, constrictor coil, venom lash, and amphibian leap legs"},
    @{Id="hydraTank"; Modules=@("chargeHorn", "scarabShell", "cycloneRazor", "turbineSlice"); Name="Tank Assembly"; Desc="Tank configuration with charge horn, scarab shell, cyclone razor, and turbine slice"}
)

foreach ($assembly in $assemblies) {
    # Validate $ModPath before Join-Path
$previewPath = Join-Path $ModPath "sprites\mechs\$($assembly.Id)_preview.png"
 if ([string]::IsNullOrWhiteSpace($previewPath)) {
        Write-Host "  [FAIL] previewPath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
 if ([string]::IsNullOrWhiteSpace($previewPath)) {
        Write-Host "  [FAIL] previewPath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
    if ($SkipExisting -and (Test-Path $previewPath)) {
        $skipped++
        Write-Host "  [SKIP] Assembly preview already exists: $($assembly.Id)" -ForegroundColor Gray
    } else {
        try {
            $moduleList = $assembly.Modules -join ", "
            $params = @{
                AssetType = "Sprite"
                AssetName = "$($assembly.Id)_preview"
                Prompt = "Assembly preview: $($assembly.Name) - $($assembly.Desc). Complete mech assembled from modules: $moduleList. Full mech view, 512x512 pixels, side view"
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
            Write-Host "  [OK] Generated assembly preview: $($assembly.Id)" -ForegroundColor Green
        } catch {
            $failed++
            Write-Host "  [FAIL] Assembly preview $($assembly.Id) : $_" -ForegroundColor Red
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
