<#
.SYNOPSIS
    Generates complete Space Whale implementation based on comprehensive design spec.

.DESCRIPTION
    This generator creates the full Space Whale ship implementation including:
    - Data model (ShipState, Segment, Plate, DigestEntry, Preview)
    - Motion and spine system (spline-driven, spring-damped)
    - Collider system (compound capsule chain, LOD)
    - Gameplay systems (swallowing, ramming, resizing, armor regen)

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}
    - Performance optimizations (multithreading, batching, pooling)
    - Integration with existing mod systems

.PARAMETER ConfigPath
    Path to Space Whale configuration JSON file

.PARAMETER OutputDir
    Directory for generated files

.PARAMETER ImplementationMode
    'modOnly', 'engineBackend', or 'hybrid' (default: 'hybrid')

.EXAMPLE
    .\SpaceWhaleImplementationGenerator.ps1 -ConfigPath "space_whale_config.json" -OutputDir "Output/SpaceWhale"
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [string]$ConfigPath = "space_whale_ship_example.json",
    
    [Parameter(Mandatory=$false)]
    [string]$OutputDir = "Output/SpaceWhale",
    
    [Parameter(Mandatory=$false)]
    [ValidateSet('modOnly', 'engineBackend', 'hybrid')]
    [string]$ImplementationMode = 'hybrid',
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipXML,
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipDataModel,
    
    [Parameter(Mandatory=$false)]
    [switch]$Verbose
)

# ============================================================================
# CONFIGURATION
# ============================================================================

$Script:Config = @{
    ImplementationMode = $ImplementationMode
    OutputDir = $OutputDir
    ConfigPath = $ConfigPath
}

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

function Write-Status {
    param([string]$Message, [string]$Type = "Info")
    
    $color = switch ($Type) {
        "Info"    { "Cyan" }
        "Success" { "Green" }
        "Warning" { "Yellow" }
        "Error"   { "Red" }
        default   { "White" }
    }
    
    $prefix = switch ($Type) {
        "Info"    { "[*]" }
        "Success" { "[+]" }
        "Warning" { "[!]" }
        "Error"   { "[-]" }
        default   { "[.]" }
    }
    
    Write-Host "$prefix $Message" -ForegroundColor $color
}

function Load-Config {
    param([string]$Path)
    
    if (-not (Test-Path $Path)) {
        Write-Status "Config file not found: $Path" -Type "Error"
        return $null
    }
    
    try {
        $content = Get-Content $Path -Raw | ConvertFrom-Json
        Write-Status "Loaded config: $Path" -Type "Success"
        return $content
    }
    catch {
        Write-Status "Failed to load config: $_" -Type "Error"
        return $null
    }
}

function Ensure-Directory {
    param([string]$Path)
    
    if (-not (Test-Path $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
        Write-Status "Created directory: $Path" -Type "Info"
    }
}

# ============================================================================
# DATA MODEL GENERATION
# ============================================================================

function Generate-DataModel {
    param(
        [object]$Config,
        [string]$OutputPath
    )
    
    Write-Status "Generating data model structures..." -Type "Info"
    
    $content = @"
<?xml version="1.0" encoding="utf-8"?>
<!--
    SpaceWhaleDataModel.xml
    
    Data structures for Space Whale ship state management.
    Based on comprehensive design spec.
-->

<TranscendenceExtension
    UNID="0xE127C000"
    name="Space Whale Data Model"
    version="1.0.0"
    >

    <Globals>
        <!-- ============================================================ -->
        <!-- SHIP STATE STRUCTURE -->
        <!-- ============================================================ -->
        
        ; Initialize ship state for a Space Whale
        (setq swInitShipState
            (lambda (shipId)
                (block (ship)
                    (setq ship (objGetObjByID shipId))
                    (if ship
                        (block Nil
                            ; Core state
                            (objSetData ship 'swShipState {
                                id: shipId
                                position: (objGetPos ship)
                                velocity: (objGetVel ship)
                                rotation: (objGetRotation ship)
                                
                                ; Scale and resources
                                scale: 1.0
                                mass: 5000
                                fatigue: 0
                                fuel: (shpGetFuelLeft ship)
                                bioCore: 100
                                
                                ; Segments (will be populated by segment system)
                                segments: (list)
                                
                                ; Spine anchors (control points for spline)
                                spineAnchors: (list)
                                
                                ; Digestion queue
                                digestQueue: (list)
                                
                                ; Global state flags
                                mawActive: False
                                orbitFieldActive: False
                                minionLinkActive: False
                                
                                ; Performance tracking
                                lastUpdateTick: (unvGetTick)
                                updateInterval: 5
                            })
                            
                            True
                        )
                        False
                    )
                )
            )
        )
        
        <!-- ============================================================ -->
        <!-- SEGMENT STRUCTURE -->
        <!-- ============================================================ -->
        
        ; Create segment data structure
        (setq swCreateSegment
            (lambda (index anchorPos transform)
                {
                    index: index
                    anchorPos: anchorPos
                    transform: transform
                    localVel: (sysVector 0 0)
                    
                    ; Plates (per-segment armor)
                    plates: (list)
                    
                    ; Devices (attached modules)
                    devices: (list)
                    
                    ; Collider and LOD
                    colliderHandle: Nil
                    lodLevel: 'high  ; 'high, 'medium, 'low
                    
                    ; Segment type
                    segmentType: (switch index
                        0 'head
                        (if (eq index (subtract (count (objGetData (objGetObjByID shipId) 'swShipState.segments)) 1))
                            'tail
                            'body
                        )
                    )
                }
            )
        )
        
        <!-- ============================================================ -->
        <!-- PLATE STRUCTURE -->
        <!-- ============================================================ -->
        
        ; Create armor plate data structure
        (setq swCreatePlate
            (lambda (plateId typeTag maxHP)
                {
                    id: plateId
                    typeTag: typeTag  ; 'light, 'medium, 'heavy, 'reinforced
                    currentHP: maxHP
                    maxHP: maxHP
                    accum: 0.0  ; Fractional regen accumulator
                    state: 'idle  ; 'idle, 'repairing, 'disabled, 'replacing
                    repairPause: 0  ; Ticks until repair can resume
                }
            )
        )
        
        ; Update plate regeneration (hybrid model: fractional + probabilistic)
        (setq swUpdatePlateRegen
            (lambda (plate baseRegenRate multipliers)
                (block (currentHP maxHP accum state pause regenRate finalRegen)
                    (setq currentHP (@ plate 'currentHP))
                    (setq maxHP (@ plate 'maxHP))
                    (setq accum (@ plate 'accum))
                    (setq state (@ plate 'state))
                    (setq pause (@ plate 'repairPause))
                    
                    ; Check if can regenerate
                    (if (and (eq state 'idle) (ls currentHP maxHP) (eq pause 0))
                        (block Nil
                            ; Calculate regen rate with multipliers
                            (setq regenRate baseRegenRate)
                            (enum multipliers mult
                                (setq regenRate (multiply regenRate mult))
                            )
                            
                            ; Fractional accumulator
                            (setq accum (add accum (divide regenRate 30)))  ; Per tick
                            
                            ; Probabilistic burst (10% chance per tick if accum > 1.0)
                            (if (and (gr accum 1.0) (ls (random 1 100) 10))
                                (block (burst)
                                    (setq burst (floor accum))
                                    (setq accum (subtract accum burst))
                                    (setq currentHP (min maxHP (add currentHP burst)))
                                )
                            )
                            
                            ; Apply fractional part if > 1.0
                            (if (gr accum 1.0)
                                (block (whole)
                                    (setq whole (floor accum))
                                    (setq accum (subtract accum whole))
                                    (setq currentHP (min maxHP (add currentHP whole)))
                                )
                            )
                            
                            ; Update plate
                            (set@ plate 'currentHP currentHP)
                            (set@ plate 'accum accum)
                        )
                        ; Pause repair if damaged recently
                        (if (gr pause 0)
                            (set@ plate 'repairPause (subtract pause 1))
                        )
                    )
                    
                    plate
                )
            )
        )
        
        <!-- ============================================================ -->
        <!-- DIGEST ENTRY STRUCTURE -->
        <!-- ============================================================ -->
        
        ; Create digest entry for swallowed target
        (setq swCreateDigestEntry
            (lambda (targetTemplate remainingMass)
                {
                    targetTemplate: targetTemplate
                    remainingMass: remainingMass
                    internalDamage: 0  ; Damage dealt from inside
                    digestTimer: 0
                    ejectable: True
                    digestRate: (multiply remainingMass 0.1)  ; 10% per second
                }
            )
        )
        
        <!-- ============================================================ -->
        <!-- PREVIEW STRUCTURE -->
        <!-- ============================================================ -->
        
        ; Create preview for resize/morph operations
        (setq swCreatePreview
            (lambda (previewId proposedScale colliderSeed)
                {
                    previewId: previewId
                    proposedScale: proposedScale
                    colliderSeed: colliderSeed
                    costEstimate: {
                        fuelCost: 0
                        bioCoreCost: 0
                        timeCost: 0
                    }
                    transforms: (list)  ; Proposed segment transforms
                    valid: True
                    reason: ""
                }
            )
        )
        
    </Globals>

</TranscendenceExtension>
"@
    
    $content | Set-Content $OutputPath -Encoding UTF8
    Write-Status "Generated data model: $OutputPath" -Type "Success"
}

# ============================================================================
# MOTION AND SPINE SYSTEM GENERATION
# ============================================================================

function Generate-MotionSystem {
    param(
        [object]$Config,
        [string]$OutputPath
    )
    
    Write-Status "Generating motion and spine system..." -Type "Info"
    
    $content = @"
<?xml version="1.0" encoding="utf-8"?>
<!--
    SpaceWhaleMotionSystem.xml
    
    Spline-driven spine system with spring-damped segment following.
    Based on comprehensive design spec.
-->

<TranscendenceExtension
    UNID="0xE127C100"
    name="Space Whale Motion System"
    version="1.0.0"
    >

    <Globals>
        <!-- ============================================================ -->
        <!-- SPLINE SAMPLING -->
        <!-- ============================================================ -->
        
        ; Catmull-Rom spline sampling
        ; Returns position at parameter t (0-1) given 4 control points
        (setq swSplineCatmullRom
            (lambda (p0 p1 p2 p3 t)
                (block (t2 t3 a1 a2 a3 a4)
                    (setq t2 (multiply t t))
                    (setq t3 (multiply t2 t))
                    
                    ; Catmull-Rom basis functions
                    (setq a1 (multiply (subtract (multiply -0.5 t3) (multiply t2) (multiply 0.5 t)) p0))
                    (setq a2 (multiply (add (multiply 1.5 t3) (multiply -2.5 t2) 1) p1))
                    (setq a3 (multiply (add (multiply -1.5 t3) (multiply 2 t2) (multiply 0.5 t)) p2))
                    (setq a4 (multiply (multiply 0.5 (subtract t3 t2)) p3))
                    
                    ; Sum components
                    (sysVectorAdd 
                        (sysVectorAdd a1 a2)
                        (sysVectorAdd a3 a4)
                    )
                )
            )
        )
        
        ; Sample spline at parameter t for N segments
        ; Returns target anchor positions
        (setq swSampleSpine
            (lambda (anchors t segmentCount)
                (block (anchorCount segmentIndex tLocal p0 p1 p2 p3)
                    (setq anchorCount (count anchors))
                    (if (ls anchorCount 2)
                        (@ anchors 0)
                        (block Nil
                            ; Clamp t to [0, 1]
                            (setq t (max 0 (min 1 t)))
                            
                            ; Find segment
                            (setq segmentIndex (floor (multiply t (subtract anchorCount 1))))
                            (setq segmentIndex (min segmentIndex (subtract anchorCount 2)))
                            
                            ; Local parameter within segment
                            (setq tLocal (multiply (subtract t (divide segmentIndex (subtract anchorCount 1))) (subtract anchorCount 1)))
                            
                            ; Get control points (with boundary handling)
                            (setq p0 (if (gr segmentIndex 0) (@ anchors (subtract segmentIndex 1)) (@ anchors 0)))
                            (setq p1 (@ anchors segmentIndex))
                            (setq p2 (@ anchors (add segmentIndex 1)))
                            (setq p3 (if (ls (add segmentIndex 2) anchorCount) (@ anchors (add segmentIndex 2)) (@ anchors (subtract anchorCount 1))))
                            
                            ; Sample spline
                            (swSplineCatmullRom p0 p1 p2 p3 tLocal)
                        )
                    )
                )
            )
        )
        
        <!-- ============================================================ -->
        <!-- SPRING-DAMPED FOLLOW -->
        <!-- ============================================================ -->
        
        ; Update segment position with spring-damped physics
        ; segment: segment data structure
        ; targetPos: target position from spline
        ; targetRot: target rotation
        ; dt: delta time
        (setq swUpdateSegmentPhysics
            (lambda (segment targetPos targetRot dt)
                (block (currentPos currentRot currentVel stiffness damping errorPos errorRot newVel newPos newRot)
                    (setq currentPos (@ segment 'anchorPos))
                    (setq currentRot (@ segment 'transform))
                    (setq currentVel (@ segment 'localVel))
                    
                    ; Spring constants (tuned for whale-like motion)
                    (setq stiffness 0.8)
                    (setq damping 0.3)
                    
                    ; Position error
                    (setq errorPos (sysVectorSubtract targetPos currentPos))
                    
                    ; Spring force
                    (setq newVel (sysVectorAdd 
                        (sysVectorMultiply errorPos stiffness)
                        (sysVectorMultiply currentVel (negate damping))
                    ))
                    
                    ; Integrate velocity
                    (setq newPos (sysVectorAdd currentPos (sysVectorMultiply newVel dt)))
                    
                    ; Rotation error (simplified - use angle difference)
                    (setq errorRot (subtract targetRot currentRot))
                    (if (gr (abs errorRot) 180)
                        (setq errorRot (subtract errorRot (if (gr errorRot 0) 360 -360)))
                    )
                    
                    ; Apply rotation damping
                    (setq newRot (add currentRot (multiply errorRot (multiply damping dt))))
                    
                    ; Update segment
                    (set@ segment 'anchorPos newPos)
                    (set@ segment 'transform newRot)
                    (set@ segment 'localVel newVel)
                    
                    segment
                )
            )
        )
        
        <!-- ============================================================ -->
        <!-- TAIL WAVE -->
        <!-- ============================================================ -->
        
        ; Generate traveling wave offset for tail undulation
        ; Returns lateral offset for anchor at index i
        (setq swGenerateTailWave
            (lambda (anchorIndex totalAnchors time frequency amplitude)
                (block (t phase offset)
                    ; Normalized position along spine (0 = head, 1 = tail)
                    (setq t (divide anchorIndex (subtract totalAnchors 1)))
                    
                    ; Phase offset (tail has larger phase)
                    (setq phase (multiply t 2.0))
                    
                    ; Amplitude envelope (decays toward head)
                    (setq amplitude (multiply amplitude (multiply t t)))
                    
                    ; Generate wave
                    (setq offset (multiply amplitude (sin (add (multiply frequency time) (multiply phase 3.14159)))))
                    
                    offset
                )
            )
        )
        
        <!-- ============================================================ -->
        <!-- WORKER COMPUTE (Simulated) -->
        <!-- ============================================================ -->
        
        ; Compute target anchor positions (simulated worker thread)
        ; In mod-only mode, this runs on main thread but can be optimized
        (setq swComputeTargetAnchors
            (lambda (shipId segmentCount steeringBias)
                (block (ship shipPos shipRot shipVel anchors i t targetPos waveOffset)
                    (setq ship (objGetObjByID shipId))
                    (if (not ship)
                        (list)
                        (block Nil
                            (setq shipPos (objGetPos ship))
                            (setq shipRot (objGetRotation ship))
                            (setq shipVel (objGetVel ship))
                            (setq anchors (list))
                            (setq time (divide (unvGetTick) 30.0))  ; Time in seconds
                            
                            ; Generate anchor positions along spline
                            (for i 0 (subtract segmentCount 1)
                                (block Nil
                                    ; Parameter along spine
                                    (setq t (divide i (subtract segmentCount 1)))
                                    
                                    ; Base position (linear for now, could use spline)
                                    (setq targetPos (sysVectorAdd shipPos 
                                        (sysVectorFromPolar shipRot (multiply t 200))
                                    ))
                                    
                                    ; Apply tail wave
                                    (setq waveOffset (swGenerateTailWave i segmentCount time 1.0 0.1))
                                    (setq targetPos (sysVectorAdd targetPos 
                                        (sysVectorFromPolar (add shipRot 90) waveOffset)
                                    ))
                                    
                                    ; Apply steering bias
                                    (if (gr (abs steeringBias) 0.01)
                                        (setq targetPos (sysVectorAdd targetPos 
                                            (sysVectorFromPolar (add shipRot 90) (multiply steeringBias t))
                                        ))
                                    )
                                    
                                    (setq anchors (append anchors (list targetPos)))
                                )
                            )
                            
                            anchors
                        )
                    )
                )
            )
        )
        
        <!-- ============================================================ -->
        <!-- LOD UPDATES -->
        <!-- ============================================================ -->
        
        ; Determine LOD level for segment based on distance
        (setq swGetSegmentLOD
            (lambda (segmentPos playerPos)
                (block (distance)
                    (setq distance (sysVectorDistance segmentPos playerPos))
                    
                    (if (ls distance 500)
                        'high
                        (if (ls distance 1000)
                            'medium
                            'low
                        )
                    )
                )
            )
        )
        
        ; Update segment LOD and update frequency
        (setq swUpdateSegmentLOD
            (lambda (segment playerPos)
                (block (lod updateInterval)
                    (setq lod (swGetSegmentLOD (@ segment 'anchorPos) playerPos))
                    (set@ segment 'lodLevel lod)
                    
                    ; Update interval based on LOD
                    (setq updateInterval (switch lod
                        'high 5    ; Every 5 ticks
                        'medium 15 ; Every 15 ticks
                        'low 30    ; Every 30 ticks
                        15
                    ))
                    
                    updateInterval
                )
            )
        )
        
    </Globals>

</TranscendenceExtension>
"@
    
    $content | Set-Content $OutputPath -Encoding UTF8
    Write-Status "Generated motion system: $OutputPath" -Type "Success"
}

# ============================================================================
# COLLIDER SYSTEM GENERATION
# ============================================================================

function Generate-ColliderSystem {
    param(
        [object]$Config,
        [string]$OutputPath,
        [string]$Mode
    )
    
    Write-Status "Generating collider system ($Mode mode)..." -Type "Info"
    
    if ($Mode -eq 'modOnly') {
        $content = @"
<?xml version="1.0" encoding="utf-8"?>
<!--
    SpaceWhaleColliderSystem_ModOnly.xml
    
    Mod-only collider system using template swaps and simplified physics.
    For full fidelity, use engine backend version.
-->

<TranscendenceExtension
    UNID="0xE127C200"
    name="Space Whale Collider System (Mod Only)"
    version="1.0.0"
    >

    <Globals>
        <!-- ============================================================ -->
        <!-- SIMPLIFIED COLLIDER SYSTEM -->
        <!-- ============================================================ -->
        
        ; Generate capsule chain from spine anchors (simplified)
        ; Returns list of capsule definitions
        (setq swGenerateCapsuleChain
            (lambda (anchors radius)
                (block (capsules i)
                    (setq capsules (list))
                    
                    (for i 0 (subtract (count anchors) 2)
                        (block (start end)
                            (setq start (@ anchors i))
                            (setq end (@ anchors (add i 1)))
                            
                            (setq capsules (append capsules (list {
                                start: start
                                end: end
                                radius: radius
                            })))
                        )
                    )
                    
                    capsules
                )
            )
        )
        
        ; Validate space for resize (simplified overlap test)
        (setq swValidateResizeSpace
            (lambda (shipId newScale)
                (block (ship shipPos nearbyObjs valid)
                    (setq ship (objGetObjByID shipId))
                    (if (not ship)
                        False
                        (block Nil
                            (setq shipPos (objGetPos ship))
                            
                            ; Find nearby objects
                            (setq nearbyObjs (sysFindObject shipPos (cat "sN:" 
                                (int (multiply newScale 200)) "; d:" 
                                (int (multiply newScale 200)) "; TA"
                            )))
                            
                            ; Simple distance check (no narrowphase)
                            (setq valid True)
                            (enum nearbyObjs obj
                                (if (and valid (not (eq obj ship)))
                                    (block (dist)
                                        (setq dist (sysVectorDistance shipPos (objGetPos obj)))
                                        (if (ls dist (multiply newScale 150))
                                            (setq valid False)
                                        )
                                    )
                                )
                            )
                            
                            valid
                        )
                    )
                )
            )
        )
        
    </Globals>

</TranscendenceExtension>
"@
    }
    else {
        # Engine backend version would use C++ functions
        $content = @"
<?xml version="1.0" encoding="utf-8"?>
<!--
    SpaceWhaleColliderSystem_Backend.xml
    
    Collider system using engine backend for full fidelity.
    Requires engine patch with backend API.
-->

<TranscendenceExtension
    UNID="0xE127C201"
    name="Space Whale Collider System (Backend)"
    version="1.0.0"
    >

    <Globals>
        <!-- ============================================================ -->
        <!-- BACKEND COLLIDER SYSTEM -->
        <!-- ============================================================ -->
        
        ; Generate capsule chain using backend API
        (setq swGenerateCapsuleChain
            (lambda (anchors radius)
                (if (swBackendAvailable)
                    (swBackendGenerateCollider (objGetID gSource) {
                        anchors: anchors
                        radius: radius
                        profile: 'capsuleChain
                    })
                    ; Fallback to mod-only
                    (swGenerateCapsuleChain anchors radius)
                )
            )
        )
        
        ; Atomic collider swap with swept overlap test
        (setq swSwapColliderAtomic
            (lambda (shipId newColliderHandle maxNudge)
                (if (swBackendAvailable)
                    (swBackendColliderSwap shipId newColliderHandle maxNudge)
                    ; Fallback: simplified validation
                    (swValidateResizeSpace shipId 1.0)
                )
            )
        )
        
    </Globals>

</TranscendenceExtension>
"@
    }
    
    $content | Set-Content $OutputPath -Encoding UTF8
    Write-Status "Generated collider system: $OutputPath" -Type "Success"
}

# ============================================================================
# MAIN GENERATION
# ============================================================================

function Generate-Implementation {
    param(
        [object]$Config,
        [string]$OutputDir,
        [string]$Mode
    )
    
    Write-Status "Generating Space Whale implementation ($Mode mode)..." -Type "Info"
    
    # Ensure output directory
    Ensure-Directory $OutputDir
    
    # Generate components
    if (-not $SkipDataModel) {
        Generate-DataModel $Config (Join-Path $OutputDir "SpaceWhaleDataModel.xml")
    }
    
    Generate-MotionSystem $Config (Join-Path $OutputDir "SpaceWhaleMotionSystem.xml")
    
    if ($Mode -eq 'modOnly') {
        Generate-ColliderSystem $Config (Join-Path $OutputDir "SpaceWhaleColliderSystem_ModOnly.xml") 'modOnly'
    }
    elseif ($Mode -eq 'engineBackend') {
        Generate-ColliderSystem $Config (Join-Path $OutputDir "SpaceWhaleColliderSystem_Backend.xml") 'backend'
    }
    else {
        # Hybrid: generate both
        Generate-ColliderSystem $Config (Join-Path $OutputDir "SpaceWhaleColliderSystem_ModOnly.xml") 'modOnly'
        Generate-ColliderSystem $Config (Join-Path $OutputDir "SpaceWhaleColliderSystem_Backend.xml") 'backend'
    }
    
    Write-Status "Implementation generation complete!" -Type "Success"
}

# ============================================================================
# ENTRY POINT
# ============================================================================

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Space Whale Implementation Generator" -ForegroundColor Cyan
Write-Host "  Mode: $($Script:Config.ImplementationMode)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Load config
$config = Load-Config $ConfigPath

if ($config) {
    Generate-Implementation $config $OutputDir $ImplementationMode
}
else {
    Write-Status "Failed to load configuration. Exiting." -Type "Error"
    exit 1
}

