#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate new modular shapeshifting mech sets for Magi-Tech mod
    
.DESCRIPTION
    Creates multiple mech sets with different themes, forms, and configurations.
    Each mech set includes multiple transformation forms (WALKER, FLYER, TANK, etc.)
    
.PARAMETER ModPath
    Path to the mod directory
    
.PARAMETER Count
    Number of mech sets to generate (default: 5)
    
.PARAMETER Themes
    Comma-separated list of themes (default: "magitech,elemental,cosmic,arcane,void")
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$ModPath = "F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery",
    
    [Parameter(Mandatory=$false)]
    [int]$Count = 5,
    
    [Parameter(Mandatory=$false)]
    [string]$Themes = "magitech,elemental,cosmic,arcane,void"
)

$ErrorActionPreference = "Stop"
# Validate ModPath is not empty
if ([string]::IsNullOrWhiteSpace($ModPath)) {
    Write-Host "Error: ModPath cannot be empty" -ForegroundColor Red
    Write-Host "  Please provide a valid mod path or use the default" -ForegroundColor Gray
    exit 1
}


# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Modular Shapeshifting Mech Set Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Mech set definitions
$mechSets = @(
    @{
        Name = "phoenix_mk3"
        Theme = "magitech"
        Description = "Advanced Phoenix-class mech with enhanced form-shifting and arcane energy systems"
        Forms = @("WALKER", "FLYER", "TANK")
        Mass = 1200.0
        Modules = @("chassis", "left_arm", "right_arm", "thrusters", "cockpit", "arcane_core")
    },
    @{
        Name = "elemental_guardian"
        Theme = "elemental"
        Description = "Elemental-powered mech that shifts between earth, air, and water forms"
        Forms = @("WALKER", "FLYER", "AQUATIC")
        Mass = 1000.0
        Modules = @("chassis", "left_arm", "right_arm", "elemental_engine", "cockpit", "elemental_focus")
    },
    @{
        Name = "cosmic_voyager"
        Theme = "cosmic"
        Description = "Cosmic energy mech designed for space exploration with stellar form transformations"
        Forms = @("WALKER", "FLYER", "SPACE")
        Mass = 1500.0
        Modules = @("chassis", "left_arm", "right_arm", "stellar_drive", "cockpit", "cosmic_shield")
    },
    @{
        Name = "void_walker"
        Theme = "void"
        Description = "Void-touched mech that phases between dimensions with shadow form capabilities"
        Forms = @("WALKER", "FLYER", "PHASE")
        Mass = 800.0
        Modules = @("chassis", "left_arm", "right_arm", "void_engine", "cockpit", "phase_core")
    },
    @{
        Name = "arcane_construct"
        Theme = "arcane"
        Description = "Magical construct mech powered by arcane runes with spell-weaving forms"
        Forms = @("WALKER", "FLYER", "CASTING")
        Mass = 1100.0
        Modules = @("chassis", "left_arm", "right_arm", "rune_engines", "cockpit", "spell_core")
    },
    @{
        Name = "storm_rider"
        Theme = "elemental"
        Description = "Lightning-powered mech that harnesses storm energy for rapid form shifts"
        Forms = @("WALKER", "FLYER", "STORM")
        Mass = 950.0
        Modules = @("chassis", "left_arm", "right_arm", "storm_engines", "cockpit", "lightning_core")
    },
    @{
        Name = "crystal_sentinel"
        Theme = "magitech"
        Description = "Crystalline mech with geometric form transformations and energy refraction"
        Forms = @("WALKER", "FLYER", "CRYSTAL")
        Mass = 1300.0
        Modules = @("chassis", "left_arm", "right_arm", "crystal_thrusters", "cockpit", "prism_core")
    },
    @{
        Name = "nebula_drifter"
        Theme = "cosmic"
        Description = "Nebula-powered mech that shifts through cosmic forms like stellar clouds"
        Forms = @("WALKER", "FLYER", "NEBULA")
        Mass = 1400.0
        Modules = @("chassis", "left_arm", "right_arm", "nebula_drive", "cockpit", "stellar_core")
    },
    @{
        Name = "shadow_stalker"
        Theme = "void"
        Description = "Stealth mech that phases through shadows with rapid form transformations"
        Forms = @("WALKER", "FLYER", "STEALTH")
        Mass = 750.0
        Modules = @("chassis", "left_arm", "right_arm", "shadow_engines", "cockpit", "void_core")
    },
    @{
        Name = "rune_weaver"
        Theme = "arcane"
        Description = "Runic mech that weaves spells through form changes with magical energy"
        Forms = @("WALKER", "FLYER", "RUNE")
        Mass = 1050.0
        Modules = @("chassis", "left_arm", "right_arm", "rune_thrusters", "cockpit", "weave_core")
    }
)

# Filter by requested themes
$themeList = $Themes -split ',' | ForEach-Object { $_.Trim() }
$filteredMechs = $mechSets | Where-Object { $themeList -contains $_.Theme } | Select-Object -First $Count

if ($filteredMechs.Count -eq 0) {
    Write-Host "No mechs found for themes: $Themes" -ForegroundColor Red
    exit 1
}

Write-Host "Generating $($filteredMechs.Count) mech set(s)..." -ForegroundColor Yellow
Write-Host ""

# Validate $ModPath before Join-Path
$mechsDir = Join-Path $ModPath "assets\mechs"
 if ([string]::IsNullOrWhiteSpace($mechsDir)) {
    Write-Host "  [FAIL] mechsDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($mechsDir)) {
    Write-Host "  [FAIL] mechsDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $mechsDir)) {
    New-Item -ItemType Directory -Path $mechsDir -Force | Out-Null
    Write-Host "Created mechs directory: $mechsDir" -ForegroundColor Green
}

function Generate-MechDef {
    param(
        [hashtable]$MechSet
    )
    
    $mechName = $MechSet.Name
    $forms = $MechSet.Forms
    $totalMass = $MechSet.Mass
    
    # Calculate module masses (distribute total mass)
    $moduleCount = $MechSet.Modules.Count
    $baseMass = [Math]::Floor($totalMass / ($moduleCount + 1))
    $chassisMass = $baseMass * 2
    $moduleMass = [Math]::Floor(($totalMass - $chassisMass) / ($moduleCount - 1))
    
    $mechDef = @"
name: $mechName
description: "$($MechSet.Description)"

modules:
  chassis:
    id: "${mechName}_chassis"
    type: "CHASSIS"
    meshPath: "modules/${mechName}_body.fbx"
    attachBone: "root"
    attachOffset: [0.0, 0.0, 0.0]
    attachRotation: [0.0, 0.0, 0.0]
    mass: $chassisMass
    weldToParent: true
    childModules: ["left_arm", "right_arm", "thrusters"]
    colliderType: "CAPSULE"
    colliderSize: [2.0, 3.0, 1.5]
    generateCollision: true
    enableLOD: true
    lodScreenSizes: [0.1, 0.05, 0.02, 0.01]

  left_arm:
    id: "${mechName}_arm_left"
    type: "ARM"
    meshPath: "modules/${mechName}_arm_left.fbx"
    attachBone: "shoulder_L"
    attachOffset: [0.0, 0.0, 0.0]
    attachRotation: [0.0, 0.0, 0.0]
    mass: $moduleMass
    weldToParent: false
    childModules: []
    colliderType: "CAPSULE"
    colliderSize: [0.3, 1.2, 0.3]
    generateCollision: true
    enableLOD: true
    lodScreenSizes: [0.1, 0.05, 0.02, 0.01]

  right_arm:
    id: "${mechName}_arm_right"
    type: "ARM"
    meshPath: "modules/${mechName}_arm_right.fbx"
    attachBone: "shoulder_R"
    attachOffset: [0.0, 0.0, 0.0]
    attachRotation: [0.0, 0.0, 0.0]
    mass: $moduleMass
    weldToParent: false
    childModules: []
    colliderType: "CAPSULE"
    colliderSize: [0.3, 1.2, 0.3]
    generateCollision: true
    enableLOD: true
    lodScreenSizes: [0.1, 0.05, 0.02, 0.01]

  thrusters:
    id: "${mechName}_thrusters"
    type: "THRUSTER"
    meshPath: "modules/${mechName}_thrusters.fbx"
    attachBone: "back_mount"
    attachOffset: [0.0, 0.0, 0.0]
    attachRotation: [0.0, 0.0, 0.0]
    mass: $([Math]::Floor($moduleMass * 1.5))
    weldToParent: true
    childModules: []
    colliderType: "BOX"
    colliderSize: [1.0, 0.5, 0.8]
    generateCollision: true
    enableLOD: true
    lodScreenSizes: [0.1, 0.05, 0.02, 0.01]

  cockpit:
    id: "${mechName}_cockpit"
    type: "COCKPIT"
    meshPath: "modules/${mechName}_cockpit.fbx"
    attachBone: "cockpit_mount"
    attachOffset: [0.0, 0.0, 0.0]
    attachRotation: [0.0, 0.0, 0.0]
    mass: $([Math]::Floor($moduleMass * 0.7))
    weldToParent: true
    childModules: []
    colliderType: "SPHERE"
    colliderSize: [0.8, 0.8, 0.8]
    generateCollision: true
    enableLOD: true
    lodScreenSizes: [0.1, 0.05, 0.02, 0.01]

"@
    
    # Add theme-specific modules
    switch ($MechSet.Theme) {
        "magitech" {
            $mechDef += @"

  arcane_core:
    id: "${mechName}_arcane_core"
    type: "ENERGY"
    meshPath: "modules/${mechName}_core.fbx"
    attachBone: "core_mount"
    attachOffset: [0.0, 0.0, 0.0]
    attachRotation: [0.0, 0.0, 0.0]
    mass: $([Math]::Floor($moduleMass * 0.8))
    weldToParent: true
    childModules: []
    colliderType: "SPHERE"
    colliderSize: [0.6, 0.6, 0.6]
    generateCollision: false
    enableLOD: true
    lodScreenSizes: [0.1, 0.05, 0.02, 0.01]

"@
        }
        "elemental" {
            $mechDef += @"

  elemental_engine:
    id: "${mechName}_elemental_engine"
    type: "ENGINE"
    meshPath: "modules/${mechName}_engine.fbx"
    attachBone: "engine_mount"
    attachOffset: [0.0, 0.0, 0.0]
    attachRotation: [0.0, 0.0, 0.0]
    mass: $([Math]::Floor($moduleMass * 1.2))
    weldToParent: true
    childModules: []
    colliderType: "BOX"
    colliderSize: [0.8, 1.0, 0.8]
    generateCollision: true
    enableLOD: true
    lodScreenSizes: [0.1, 0.05, 0.02, 0.01]

  elemental_focus:
    id: "${mechName}_elemental_focus"
    type: "FOCUS"
    meshPath: "modules/${mechName}_focus.fbx"
    attachBone: "focus_mount"
    attachOffset: [0.0, 0.0, 0.0]
    attachRotation: [0.0, 0.0, 0.0]
    mass: $([Math]::Floor($moduleMass * 0.5))
    weldToParent: true
    childModules: []
    colliderType: "SPHERE"
    colliderSize: [0.5, 0.5, 0.5]
    generateCollision: false
    enableLOD: true
    lodScreenSizes: [0.1, 0.05, 0.02, 0.01]

"@
        }
        "cosmic" {
            $mechDef += @"

  stellar_drive:
    id: "${mechName}_stellar_drive"
    type: "DRIVE"
    meshPath: "modules/${mechName}_drive.fbx"
    attachBone: "drive_mount"
    attachOffset: [0.0, 0.0, 0.0]
    attachRotation: [0.0, 0.0, 0.0]
    mass: $([Math]::Floor($moduleMass * 1.5))
    weldToParent: true
    childModules: []
    colliderType: "BOX"
    colliderSize: [1.2, 0.8, 1.0]
    generateCollision: true
    enableLOD: true
    lodScreenSizes: [0.1, 0.05, 0.02, 0.01]

  cosmic_shield:
    id: "${mechName}_cosmic_shield"
    type: "SHIELD"
    meshPath: "modules/${mechName}_shield.fbx"
    attachBone: "shield_mount"
    attachOffset: [0.0, 0.0, 0.0]
    attachRotation: [0.0, 0.0, 0.0]
    mass: $([Math]::Floor($moduleMass * 0.6))
    weldToParent: false
    childModules: []
    colliderType: "SPHERE"
    colliderSize: [1.0, 1.0, 1.0]
    generateCollision: false
    enableLOD: true
    lodScreenSizes: [0.1, 0.05, 0.02, 0.01]

"@
        }
        "void" {
            $mechDef += @"

  void_engine:
    id: "${mechName}_void_engine"
    type: "ENGINE"
    meshPath: "modules/${mechName}_void_engine.fbx"
    attachBone: "void_mount"
    attachOffset: [0.0, 0.0, 0.0]
    attachRotation: [0.0, 0.0, 0.0]
    mass: $([Math]::Floor($moduleMass * 0.9))
    weldToParent: true
    childModules: []
    colliderType: "SPHERE"
    colliderSize: [0.7, 0.7, 0.7]
    generateCollision: false
    enableLOD: true
    lodScreenSizes: [0.1, 0.05, 0.02, 0.01]

  phase_core:
    id: "${mechName}_phase_core"
    type: "CORE"
    meshPath: "modules/${mechName}_phase_core.fbx"
    attachBone: "phase_mount"
    attachOffset: [0.0, 0.0, 0.0]
    attachRotation: [0.0, 0.0, 0.0]
    mass: $([Math]::Floor($moduleMass * 0.7))
    weldToParent: true
    childModules: []
    colliderType: "SPHERE"
    colliderSize: [0.6, 0.6, 0.6]
    generateCollision: false
    enableLOD: true
    lodScreenSizes: [0.1, 0.05, 0.02, 0.01]

"@
        }
        "arcane" {
            $mechDef += @"

  rune_engines:
    id: "${mechName}_rune_engines"
    type: "ENGINE"
    meshPath: "modules/${mechName}_runes.fbx"
    attachBone: "rune_mount"
    attachOffset: [0.0, 0.0, 0.0]
    attachRotation: [0.0, 0.0, 0.0]
    mass: $([Math]::Floor($moduleMass * 1.1))
    weldToParent: true
    childModules: []
    colliderType: "BOX"
    colliderSize: [0.9, 0.7, 0.9]
    generateCollision: true
    enableLOD: true
    lodScreenSizes: [0.1, 0.05, 0.02, 0.01]

  spell_core:
    id: "${mechName}_spell_core"
    type: "CORE"
    meshPath: "modules/${mechName}_spell_core.fbx"
    attachBone: "spell_mount"
    attachOffset: [0.0, 0.0, 0.0]
    attachRotation: [0.0, 0.0, 0.0]
    mass: $([Math]::Floor($moduleMass * 0.8))
    weldToParent: true
    childModules: []
    colliderType: "SPHERE"
    colliderSize: [0.7, 0.7, 0.7]
    generateCollision: false
    enableLOD: true
    lodScreenSizes: [0.1, 0.05, 0.02, 0.01]

"@
        }
    }
    
    # Generate morph profiles for form transformations
    $mechDef += @"
morphProfiles:
"@
    
    # Generate all form transition combinations
    for ($i = 0; $i -lt $forms.Count; $i++) {
        for ($j = 0; $j -lt $forms.Count; $j++) {
            if ($i -ne $j) {
                $fromForm = $forms[$i]
                $toForm = $forms[$j]
                $profileName = "${fromForm.ToLower()}_to_${toForm.ToLower()}"
                $duration = 1.5 + (Get-Random -Minimum -0.3 -Maximum 0.5)
                
                $mechDef += @"

  - name: "$profileName"
    fromForm: "$fromForm"
    toForm: "$toForm"
    duration: $duration
    curveType: "EASE_IN_OUT"
    customCurve: []
    moduleTransforms:
      left_arm: [0.0, 0.0, 0.0]
      right_arm: [0.0, 0.0, 0.0]
      thrusters: [0.0, 0.0, 0.0]
    moduleScales:
      left_arm: [1.0, 1.0, 1.0]
      right_arm: [1.0, 1.0, 1.0]
      thrusters: [1.0, 1.0, 1.0]
    moduleOpacities:
      left_arm: 1.0
      right_arm: 1.0
      thrusters: 1.0

"@
            }
        }
    }
    
    # Add physics configuration
    $mechDef += @"
physics:
  totalMass: $totalMass
  moduleMasses:
    chassis: $chassisMass
    left_arm: $moduleMass
    right_arm: $moduleMass
    thrusters: $([Math]::Floor($moduleMass * 1.5))
    cockpit: $([Math]::Floor($moduleMass * 0.7))
  joints:
    - jointName: "shoulder_L"
      type: "BALL"
      axis: [0.0, 1.0, 0.0]
      limits: [-45.0, 45.0]
      stiffness: 1000.0
      damping: 100.0
      enableMotor: false
      motorTargetVelocity: 0.0
      motorMaxForce: 1000.0
    - jointName: "shoulder_R"
      type: "BALL"
      axis: [0.0, 1.0, 0.0]
      limits: [-45.0, 45.0]
      stiffness: 1000.0
      damping: 100.0
      enableMotor: false
      motorTargetVelocity: 0.0
      motorMaxForce: 1000.0
    - jointName: "back_mount"
      type: "FIXED"
      axis: [0.0, 1.0, 0.0]
      limits: [0.0, 0.0]
      stiffness: 1000.0
      damping: 100.0
      enableMotor: false
      motorTargetVelocity: 0.0
      motorMaxForce: 1000.0
  centerOfMass: [0.0, 1.5, 0.0]
  enableGravity: true
  enableCollision: true
  linearDamping: 0.1
  angularDamping: 0.1

lods:
  - quality: "ULTRA_HIGH"
    screenSize: 0.1
    meshDecimateRatio: 0.0
    morphDetailRatio: 1.0
    preserveBorders: true
    preserveUVSeams: true
    maxTriangles: 50000
  - quality: "HIGH"
    screenSize: 0.05
    meshDecimateRatio: 0.2
    morphDetailRatio: 0.8
    preserveBorders: true
    preserveUVSeams: true
    maxTriangles: 25000
  - quality: "MEDIUM"
    screenSize: 0.02
    meshDecimateRatio: 0.5
    morphDetailRatio: 0.6
    preserveBorders: true
    preserveUVSeams: false
    maxTriangles: 10000
  - quality: "LOW"
    screenSize: 0.01
    meshDecimateRatio: 0.8
    morphDetailRatio: 0.3
    preserveBorders: false
    preserveUVSeams: false
    maxTriangles: 5000

skeletonTemplate: "templates/${mechName}_skeleton.fbx"
enableGPUAcceleration: true
enableHotReload: true
"@
    
    return $mechDef
}

# Generate mech sets
$generated = 0
foreach ($mechSet in $filteredMechs) {
    try {
        $mechDef = Generate-MechDef -MechSet $mechSet
        $mechFile = Join-Path $mechsDir "$($mechSet.Name).mechdef"
        
        $mechDef | Out-File -FilePath $mechFile -Encoding UTF8 -NoNewline
        $generated++
        
        Write-Host "[OK] Generated: $($mechSet.Name)" -ForegroundColor Green
        Write-Host "     Theme: $($mechSet.Theme)" -ForegroundColor Gray
        Write-Host "     Forms: $($mechSet.Forms -join ', ')" -ForegroundColor Gray
        Write-Host "     Mass: $($mechSet.Mass)" -ForegroundColor Gray
        Write-Host ""
    } catch {
        Write-Host "[FAIL] $($mechSet.Name) : $_" -ForegroundColor Red
    }
}

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Generation Complete" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Generated: $generated mech set(s)" -ForegroundColor Green
Write-Host ""
Write-Host "Mech definitions saved to: $mechsDir" -ForegroundColor Gray
Write-Host ""
Write-Host "Next step: Run GenerateAllModSprites.ps1 to generate visual assets" -ForegroundColor Yellow
Write-Host ""
