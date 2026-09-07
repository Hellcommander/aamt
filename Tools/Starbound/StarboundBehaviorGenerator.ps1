<#
.SYNOPSIS
    Starbound Behavior Generator - Creates behavior tree files for monster/NPC AI

.DESCRIPTION
    Generates .behavior files for Starbound/OpenStarbound with support for:
    - Multiple behavior presets (Patrol, Attack, Flee, Boss, etc.)
    - Composite nodes (sequence, selector, parallel, dynamic)
    - Action nodes (timer, movement, combat, etc.)
    - Decorator nodes (repeater, inverter, cooldown, etc.)

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}
    - Module references for reusable sub-behaviors
    - Script dependency management

.PARAMETER BehaviorName
    Name of the behavior (used for filename and internal name)

.PARAMETER Preset
    Built-in behavior preset to use

.PARAMETER OutputDir
    Output directory for generated files

.EXAMPLE
    .\StarboundBehaviorGenerator.ps1 -BehaviorName "mymonster-attack" -Preset Attack
    .\StarboundBehaviorGenerator.ps1 -BehaviorName "myboss" -Preset Boss -HealthStages 3
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$BehaviorName,

    [Parameter(Mandatory=$false)]
    [ValidateSet("Default", "Patrol", "Attack", "Flee", "Chase", "Guard", "Boss", "Ranged", "Melee", "Idle", "Wander", "Targeting", "Custom")]
    [string]$Preset = "Default",

    [Parameter(Mandatory=$false)]
    [string]$OutputDir = "StarboundBehaviors",

    [Parameter(Mandatory=$false)]
    [string]$Description = "",

    # Common behavior parameters
    [Parameter(Mandatory=$false)]
    [float]$AggroRange = 30.0,

    [Parameter(Mandatory=$false)]
    [float]$DeaggroRange = 50.0,

    [Parameter(Mandatory=$false)]
    [float]$AttackRange = 5.0,

    [Parameter(Mandatory=$false)]
    [float]$MoveSpeed = 8.0,

    [Parameter(Mandatory=$false)]
    [float]$AttackCooldown = 1.0,

    [Parameter(Mandatory=$false)]
    [string]$ProjectileType = "",

    [Parameter(Mandatory=$false)]
    [array]$ProjectileOffset = @(0, 0),

    [Parameter(Mandatory=$false)]
    [string]$AttackAnimation = "attack",

    [Parameter(Mandatory=$false)]
    [string]$IdleAnimation = "idle",

    [Parameter(Mandatory=$false)]
    [string]$WalkAnimation = "walk",

    # Boss-specific parameters
    [Parameter(Mandatory=$false)]
    [int]$HealthStages = 0,

    [Parameter(Mandatory=$false)]
    [array]$HealthThresholds = @(0.66, 0.33),

    [Parameter(Mandatory=$false)]
    [switch]$HasDamageBar,

    # Patrol parameters
    [Parameter(Mandatory=$false)]
    [float]$PatrolRadius = 20.0,

    [Parameter(Mandatory=$false)]
    [float]$PatrolIdleTime = 2.0,

    # Target entity types
    [Parameter(Mandatory=$false)]
    [array]$TargetTypes = @("player"),

    # Custom scripts to include
    [Parameter(Mandatory=$false)]
    [array]$AdditionalScripts = @(),

    # Module references
    [Parameter(Mandatory=$false)]
    [array]$Modules = @(),

    # Custom root node (for Custom preset)
    [Parameter(Mandatory=$false)]
    [hashtable]$CustomRoot = $null
)

# ============================================================================
# SCRIPT DEFINITIONS
# ============================================================================

$ScriptCategories = @{
    "Entity" = "/scripts/actions/entity.lua"
    "Movement" = "/scripts/actions/movement.lua"
    "Monster" = "/scripts/actions/monster.lua"
    "Notification" = "/scripts/actions/notification.lua"
    "World" = "/scripts/actions/world.lua"
    "Time" = "/scripts/actions/time.lua"
    "Position" = "/scripts/actions/position.lua"
    "Status" = "/scripts/actions/status.lua"
    "Sensor" = "/scripts/actions/sensor.lua"
    "BData" = "/scripts/behavior/bdata.lua"
    "Animator" = "/scripts/actions/animator.lua"
    "Math" = "/scripts/actions/math.lua"
    "Projectiles" = "/scripts/actions/projectiles.lua"
    "NPC" = "/scripts/actions/npc.lua"
    "Query" = "/scripts/actions/query.lua"
}

# ============================================================================
# NODE BUILDER FUNCTIONS
# ============================================================================

function New-ActionNode {
    param(
        [string]$Name,
        [string]$Title = "",
        [hashtable]$Parameters = @{},
        [hashtable]$Output = $null
    )
    
    if ([string]::IsNullOrEmpty($Title)) { $Title = $Name }
    
    $node = [ordered]@{
        "title" = $Title
        "type" = "action"
        "name" = $Name
        "parameters" = [ordered]@{}
    }
    
    foreach ($key in $Parameters.Keys) {
        $val = $Parameters[$key]
        if ($val -is [hashtable] -and $val.ContainsKey("key")) {
            $node.parameters[$key] = [ordered]@{ "key" = $val.key }
        } elseif ($val -is [hashtable] -and $val.ContainsKey("value")) {
            $node.parameters[$key] = [ordered]@{ "value" = $val.value }
        } else {
            $node.parameters[$key] = [ordered]@{ "value" = $val }
        }
    }
    
    if ($Output) {
        $node["output"] = [ordered]@{}
        foreach ($key in $Output.Keys) {
            $node.output[$key] = $Output[$key]
        }
    }
    
    return $node
}

function New-CompositeNode {
    param(
        [ValidateSet("sequence", "selector", "parallel", "dynamic")]
        [string]$Type,
        [string]$Title = "",
        [hashtable]$Parameters = @{},
        [array]$Children = @()
    )
    
    if ([string]::IsNullOrEmpty($Title)) { $Title = $Type }
    
    $node = [ordered]@{
        "title" = $Title
        "type" = "composite"
        "name" = $Type
        "parameters" = [ordered]@{}
        "children" = @()
    }
    
    foreach ($key in $Parameters.Keys) {
        $node.parameters[$key] = [ordered]@{ "value" = $Parameters[$key] }
    }
    
    foreach ($child in $Children) {
        $node.children += $child
    }
    
    return $node
}

function New-DecoratorNode {
    param(
        [ValidateSet("repeater", "inverter", "succeeder", "failer", "cooldown", "limiter", "filter")]
        [string]$Type,
        [string]$Title = "",
        [hashtable]$Parameters = @{},
        $Child = $null
    )
    
    if ([string]::IsNullOrEmpty($Title)) { $Title = $Type }
    
    $node = [ordered]@{
        "title" = $Title
        "type" = "decorator"
        "name" = $Type
        "parameters" = [ordered]@{}
    }
    
    foreach ($key in $Parameters.Keys) {
        $node.parameters[$key] = [ordered]@{ "value" = $Parameters[$key] }
    }
    
    if ($Child) {
        $node["child"] = $Child
    }
    
    return $node
}

function New-ModuleNode {
    param(
        [string]$ModuleName,
        [string]$Title = "",
        [hashtable]$Parameters = @{}
    )
    
    if ([string]::IsNullOrEmpty($Title)) { $Title = $ModuleName }
    
    $node = [ordered]@{
        "title" = $Title
        "type" = "module"
        "name" = $ModuleName
        "parameters" = [ordered]@{}
    }
    
    foreach ($key in $Parameters.Keys) {
        $val = $Parameters[$key]
        if ($val -is [hashtable] -and $val.ContainsKey("key")) {
            $node.parameters[$key] = [ordered]@{ "key" = $val.key }
        } else {
            $node.parameters[$key] = [ordered]@{ "value" = $val }
        }
    }
    
    return $node
}

function New-RunnerNode {
    return New-ActionNode -Name "runner" -Title "runner"
}

function New-TimerNode {
    param([float]$Time)
    return New-ActionNode -Name "timer" -Title "timer" -Parameters @{ "time" = $Time }
}

# ============================================================================
# COMMON BEHAVIOR PATTERNS
# ============================================================================

function Get-TargetingBehavior {
    param(
        [float]$QueryRange = 30,
        [float]$KeepRange = 50,
        [array]$EntityTypes = @("player"),
        [bool]$KeepInSight = $false,
        [bool]$TargetOnDamage = $true
    )
    
    return New-ModuleNode -ModuleName "monster-targeting" -Title "monster-targeting" -Parameters @{
        "targetQueryRange" = $QueryRange
        "keepTargetInRange" = $KeepRange
        "targetEntityTypes" = $EntityTypes
        "keepTargetInSight" = $KeepInSight
        "queryTargets" = $true
        "targetOnDamage" = $TargetOnDamage
        "targetOutOfSightTime" = 1
    }
}

function Get-FaceTargetBehavior {
    return New-ActionNode -Name "faceEntity" -Title "faceTarget" -Parameters @{
        "entity" = @{ key = "target" }
    }
}

function Get-MoveToTargetBehavior {
    param([float]$Speed = 8, [float]$Tolerance = 2)
    
    return New-ActionNode -Name "moveToEntity" -Title "moveToTarget" -Parameters @{
        "entity" = @{ key = "target" }
        "speed" = $Speed
        "tolerance" = $Tolerance
    }
}

function Get-ApproachVelocityBehavior {
    param([float]$Force = 20, [array]$Velocity = @(0, 0))
    
    return New-ActionNode -Name "controlApproachVelocity" -Title "controlApproachVelocity" -Parameters @{
        "force" = $Force
        "velocity" = $Velocity
    }
}

function Get-EntityExistsBehavior {
    param([string]$EntityKey = "target")
    
    return New-ActionNode -Name "entityExists" -Title "entityExists" -Parameters @{
        "entity" = @{ key = $EntityKey }
    }
}

function Get-SetAnimationStateBehavior {
    param([string]$State, [string]$Type = "body")
    
    return New-ActionNode -Name "setAnimationState" -Title "setAnimationState" -Parameters @{
        "state" = $State
        "type" = $Type
    }
}

function Get-SpawnProjectileBehavior {
    param(
        [string]$ProjectileType,
        [array]$Offset = @(0, 0),
        [array]$AimVector = $null,
        [bool]$TrackSource = $false
    )
    
    $params = @{
        "projectileType" = $ProjectileType
        "offset" = $Offset
        "position" = @{ key = "self" }
        "projectileConfig" = @{}
        "scalePower" = $true
        "sourceEntity" = @{ key = "self" }
        "trackSource" = $TrackSource
    }
    
    if ($AimVector) {
        $params["aimVector"] = $AimVector
    } else {
        $params["aimVector"] = @{ key = "aimVector" }
    }
    
    return New-ActionNode -Name "spawnProjectile" -Title "spawnProjectile" -Parameters $params
}

function Get-PlaySoundBehavior {
    param([string]$Sound)
    
    return New-ActionNode -Name "playSound" -Title "playSound" -Parameters @{
        "sound" = $Sound
    }
}

function Get-WasDamagedBehavior {
    return New-ActionNode -Name "wasDamaged" -Title "wasDamaged"
}

function Get-SetAggressiveBehavior {
    param([bool]$Aggressive = $true)
    
    return New-ActionNode -Name "setAggressive" -Title "setAggressive" -Parameters @{
        "aggressive" = $Aggressive
    }
}

function Get-SetDyingBehavior {
    param([bool]$ShouldDie = $false)
    
    return New-ActionNode -Name "setDying" -Title "setDying" -Parameters @{
        "shouldDie" = $ShouldDie
    }
}

function Get-SetDamageBarBehavior {
    param([string]$Type = "Default")
    
    return New-ActionNode -Name "setDamageBar" -Title "setDamageBar" -Parameters @{
        "type" = $Type
    }
}

function Get-ResourcePercentageBehavior {
    param([float]$Percentage, [string]$Resource = "health")
    
    return New-ActionNode -Name "resourcePercentage" -Title "resourcePercentage" -Parameters @{
        "percentage" = $Percentage
        "resource" = $Resource
    }
}

function Get-EntityInRangeBehavior {
    param([float]$Range, [string]$EntityKey = "target")
    
    return New-ActionNode -Name "entityInRange" -Title "entityInRange" -Parameters @{
        "entity" = @{ key = $EntityKey }
        "position" = @{ key = "self" }
        "xRange" = $Range
    }
}

function Get-FaceDirectionBehavior {
    param([int]$Direction = -1)
    
    return New-ActionNode -Name "faceDirection" -Title "faceDirection" -Parameters @{
        "direction" = $Direction
    }
}

# ============================================================================
# PRESET GENERATORS
# ============================================================================

function Get-IdlePreset {
    param([string]$IdleAnimation = "idle", [float]$Duration = 2.0)
    
    $children = @(
        (Get-SetAnimationStateBehavior -State $IdleAnimation -Type "body"),
        (New-TimerNode -Time $Duration)
    )
    
    return New-CompositeNode -Type "sequence" -Title "Idle" -Children $children
}

function Get-WanderPreset {
    param([float]$MoveSpeed = 4, [float]$WanderTime = 3, [float]$IdleTime = 2)
    
    $wanderSequence = New-CompositeNode -Type "sequence" -Title "Wander" -Children @(
        (New-ActionNode -Name "setVelocity" -Title "wander" -Parameters @{
            "direction" = @{ key = "wanderDirection" }
            "speed" = $MoveSpeed
        }),
        (New-TimerNode -Time $WanderTime),
        (Get-ApproachVelocityBehavior -Force 20 -Velocity @(0, 0)),
        (New-TimerNode -Time $IdleTime)
    )
    
    $chooseDirection = New-ActionNode -Name "random" -Title "chooseDirection" -Parameters @{
        "min" = 0
        "max" = 1
    } -Output @{ "number" = "wanderDirection" }
    
    return New-CompositeNode -Type "sequence" -Title "WanderBehavior" -Children @(
        $chooseDirection,
        (New-DecoratorNode -Type "repeater" -Title "repeatWander" -Parameters @{
            "maxLoops" = -1
            "untilSuccess" = $false
        } -Child $wanderSequence)
    )
}

function Get-PatrolPreset {
    param([float]$Radius = 20, [float]$Speed = 6, [float]$IdleTime = 2)
    
    return New-CompositeNode -Type "sequence" -Title "Patrol" -Children @(
        (New-ActionNode -Name "setPosition" -Title "rememberHome" -Parameters @{
            "position" = @{ key = "self" }
        } -Output @{ "position" = "homePosition" }),
        (New-DecoratorNode -Type "repeater" -Title "patrolLoop" -Parameters @{
            "maxLoops" = -1
            "untilSuccess" = $false
        } -Child (New-CompositeNode -Type "sequence" -Title "patrolSequence" -Children @(
            (New-ActionNode -Name "offsetPosition" -Title "pickPatrolPoint" -Parameters @{
                "position" = @{ key = "homePosition" }
                "offset" = @((Get-Random -Minimum (-$Radius) -Maximum $Radius), 0)
            } -Output @{ "position" = "patrolTarget" }),
            (New-ActionNode -Name "moveToPosition" -Title "moveToPatrol" -Parameters @{
                "position" = @{ key = "patrolTarget" }
                "speed" = $Speed
                "tolerance" = 2
            }),
            (New-TimerNode -Time $IdleTime)
        )))
    )
}

function Get-ChasePreset {
    param([float]$Speed = 10, [float]$Range = 30)
    
    return New-CompositeNode -Type "sequence" -Title "Chase" -Children @(
        (Get-EntityExistsBehavior -EntityKey "target"),
        (Get-FaceTargetBehavior),
        (New-CompositeNode -Type "parallel" -Title "chaseParallel" -Parameters @{
            "fail" = 1
            "success" = -1
        } -Children @(
            (Get-EntityInRangeBehavior -Range $Range -EntityKey "target"),
            (Get-MoveToTargetBehavior -Speed $Speed -Tolerance 2)
        ))
    )
}

function Get-FleePreset {
    param([float]$Speed = 12, [float]$FleeDistance = 30)
    
    return New-CompositeNode -Type "sequence" -Title "Flee" -Children @(
        (Get-EntityExistsBehavior -EntityKey "target"),
        (New-ActionNode -Name "entityDirection" -Title "getFleeDirection" -Parameters @{
            "entity" = @{ key = "self" }
            "target" = @{ key = "target" }
        } -Output @{ "vector" = "fleeVector" }),
        (New-ActionNode -Name "vecMultiply" -Title "invertDirection" -Parameters @{
            "first" = @{ key = "fleeVector" }
            "second" = @(-1, -1)
        } -Output @{ "vector" = "fleeDirection" }),
        (New-ActionNode -Name "setVelocity" -Title "flee" -Parameters @{
            "direction" = @{ key = "fleeDirection" }
            "speed" = $Speed
        }),
        (New-TimerNode -Time 2.0)
    )
}

function Get-AttackPreset {
    param(
        [string]$AttackAnimation = "attack",
        [float]$Cooldown = 1.0,
        [float]$WindupTime = 0.2,
        [float]$RecoveryTime = 0.3,
        [string]$ProjectileType = "",
        [array]$ProjectileOffset = @(0, 0)
    )
    
    $attackChildren = @(
        (Get-FaceTargetBehavior),
        (Get-SetAnimationStateBehavior -State $AttackAnimation -Type "attack"),
        (New-TimerNode -Time $WindupTime)
    )
    
    if (-not [string]::IsNullOrEmpty($ProjectileType)) {
        # Ranged attack
        $attackChildren += (New-ActionNode -Name "entityDirection" -Title "aimAtTarget" -Parameters @{
            "entity" = @{ key = "self" }
            "target" = @{ key = "target" }
        } -Output @{ "vector" = "aimVector" })
        $attackChildren += (Get-SpawnProjectileBehavior -ProjectileType $ProjectileType -Offset $ProjectileOffset)
    }
    
    $attackChildren += @(
        (New-TimerNode -Time $RecoveryTime),
        (Get-SetAnimationStateBehavior -State "idle" -Type "attack")
    )
    
    $attackSequence = New-CompositeNode -Type "sequence" -Title "AttackSequence" -Children $attackChildren
    
    return New-DecoratorNode -Type "cooldown" -Title "attackCooldown" -Parameters @{
        "cooldown" = $Cooldown
        "onFail" = $false
        "onSuccess" = $true
    } -Child $attackSequence
}

function Get-MeleePreset {
    param(
        [float]$AttackRange = 3,
        [string]$AttackAnimation = "attack",
        [float]$Cooldown = 0.8,
        [float]$Damage = 10
    )
    
    return New-CompositeNode -Type "sequence" -Title "MeleeAttack" -Children @(
        (Get-EntityExistsBehavior -EntityKey "target"),
        (Get-EntityInRangeBehavior -Range $AttackRange -EntityKey "target"),
        (Get-AttackPreset -AttackAnimation $AttackAnimation -Cooldown $Cooldown -WindupTime 0.15 -RecoveryTime 0.2)
    )
}

function Get-RangedPreset {
    param(
        [float]$AttackRange = 15,
        [float]$MinRange = 5,
        [string]$ProjectileType = "فlarrow",
        [array]$ProjectileOffset = @(0, 0),
        [float]$Cooldown = 1.5
    )
    
    $keepDistance = New-CompositeNode -Type "selector" -Title "keepDistance" -Children @(
        # Too close - back up
        (New-CompositeNode -Type "sequence" -Title "tooClose" -Children @(
            (Get-EntityInRangeBehavior -Range $MinRange -EntityKey "target"),
            (Get-FleePreset -Speed 8 -FleeDistance 10)
        )),
        # In range - attack
        (New-CompositeNode -Type "sequence" -Title "inRange" -Children @(
            (Get-EntityInRangeBehavior -Range $AttackRange -EntityKey "target"),
            (Get-AttackPreset -AttackAnimation "attack" -Cooldown $Cooldown -ProjectileType $ProjectileType -ProjectileOffset $ProjectileOffset)
        )),
        # Too far - approach
        (Get-ChasePreset -Speed 8 -Range $AttackRange)
    )
    
    return New-CompositeNode -Type "sequence" -Title "RangedBehavior" -Children @(
        (Get-EntityExistsBehavior -EntityKey "target"),
        $keepDistance
    )
}

function Get-GuardPreset {
    param(
        [float]$GuardRadius = 15,
        [float]$ChaseRange = 30,
        [float]$AttackRange = 3
    )
    
    return New-CompositeNode -Type "sequence" -Title "Guard" -Children @(
        # Remember guard position
        (New-ActionNode -Name "setPosition" -Title "rememberPost" -Parameters @{
            "position" = @{ key = "self" }
        } -Output @{ "position" = "guardPosition" }),
        # Main guard loop
        (New-DecoratorNode -Type "repeater" -Title "guardLoop" -Parameters @{
            "maxLoops" = -1
            "untilSuccess" = $false
        } -Child (New-CompositeNode -Type "selector" -Title "guardSelector" -Children @(
            # If target exists and in range, fight
            (New-CompositeNode -Type "sequence" -Title "engageTarget" -Children @(
                (Get-EntityExistsBehavior -EntityKey "target"),
                (Get-EntityInRangeBehavior -Range $ChaseRange -EntityKey "target"),
                (New-CompositeNode -Type "selector" -Title "fightOrChase" -Children @(
                    (Get-MeleePreset -AttackRange $AttackRange),
                    (Get-ChasePreset -Speed 10 -Range $ChaseRange)
                ))
            )),
            # Return to post if too far
            (New-CompositeNode -Type "sequence" -Title "returnToPost" -Children @(
                (New-DecoratorNode -Type "inverter" -Child (New-ActionNode -Name "inRange" -Title "atPost" -Parameters @{
                    "position" = @{ key = "guardPosition" }
                    "range" = $GuardRadius
                })),
                (New-ActionNode -Name "moveToPosition" -Title "returnMove" -Parameters @{
                    "position" = @{ key = "guardPosition" }
                    "speed" = 6
                    "tolerance" = 2
                })
            )),
            # Idle at post
            (Get-IdlePreset -Duration 1.0)
        )))
    )
}

function Get-BossPreset {
    param(
        [int]$HealthStages = 3,
        [array]$HealthThresholds = @(0.66, 0.33),
        [bool]$HasDamageBar = $true,
        [float]$AggroRange = 50,
        [string]$ProjectileType = "",
        [array]$ProjectileOffset = @(0, 0)
    )
    
    # Setup sequence
    $setupChildren = @(
        (Get-SetDyingBehavior -ShouldDie $false),
        (Get-FaceDirectionBehavior -Direction -1),
        (Get-SetAggressiveBehavior -Aggressive $true)
    )
    
    if ($HasDamageBar) {
        $setupChildren += (Get-SetDamageBarBehavior -Type "Special")
    }
    
    $setupSequence = New-CompositeNode -Type "sequence" -Title "Setup" -Children $setupChildren
    
    # Stage tracking with dynamic node
    $stageChildren = @()
    for ($i = 0; $i -lt $HealthThresholds.Count; $i++) {
        $threshold = $HealthThresholds[$i]
        $stageName = "stage$($i + 1)"
        
        $stageChildren += (New-CompositeNode -Type "sequence" -Title "Stage$($i + 1)Check" -Children @(
            (Get-ResourcePercentageBehavior -Percentage $threshold -Resource "health"),
            (New-ActionNode -Name "setGlobalTag" -Title "setStage" -Parameters @{
                "tag" = $stageName
                "type" = "stage"
            })
        ))
    }
    $stageChildren += (New-RunnerNode)
    
    $stageTracker = New-CompositeNode -Type "dynamic" -Title "StageTracker" -Children $stageChildren
    
    # Main combat behavior
    $combatSelector = New-CompositeNode -Type "selector" -Title "CombatSelector" -Children @(
        # Health depleted - death sequence
        (New-CompositeNode -Type "sequence" -Title "DeathSequence" -Children @(
            (New-DecoratorNode -Type "inverter" -Child (Get-ResourcePercentageBehavior -Percentage 0 -Resource "health")),
            (Get-SetAnimationStateBehavior -State "dying" -Type "attack"),
            (New-TimerNode -Time 3.0),
            (Get-SetDyingBehavior -ShouldDie $true)
        )),
        # Normal combat
        (New-CompositeNode -Type "parallel" -Title "CombatParallel" -Parameters @{
            "fail" = -1
            "success" = -1
        } -Children @(
            # Attack pattern
            $(if (-not [string]::IsNullOrEmpty($ProjectileType)) {
                Get-RangedPreset -ProjectileType $ProjectileType -ProjectileOffset $ProjectileOffset -Cooldown 2.0
            } else {
                Get-MeleePreset -AttackRange 5
            }),
            # Stage tracker
            $stageTracker
        ))
    )
    
    # Full behavior with targeting
    return New-CompositeNode -Type "sequence" -Title "BossBehavior" -Children @(
        $setupSequence,
        (New-CompositeNode -Type "parallel" -Title "MainLoop" -Parameters @{
            "fail" = -1
            "success" = -1
        } -Children @(
            (Get-TargetingBehavior -QueryRange $AggroRange -KeepRange ($AggroRange * 1.5) -TargetOnDamage $true),
            (New-CompositeNode -Type "dynamic" -Title "BossDynamic" -Children @(
                (Get-WasDamagedBehavior),
                $combatSelector,
                (New-RunnerNode)
            ))
        ))
    )
}

function Get-DefaultPreset {
    param(
        [float]$AggroRange = 30,
        [float]$AttackRange = 5,
        [float]$MoveSpeed = 8
    )
    
    return New-CompositeNode -Type "sequence" -Title "DefaultBehavior" -Children @(
        (New-CompositeNode -Type "parallel" -Title "MainParallel" -Parameters @{
            "fail" = -1
            "success" = -1
        } -Children @(
            (Get-TargetingBehavior -QueryRange $AggroRange -KeepRange ($AggroRange * 1.5)),
            (New-CompositeNode -Type "dynamic" -Title "MainDynamic" -Children @(
                # React to damage
                (Get-WasDamagedBehavior),
                # If has target, engage
                (New-CompositeNode -Type "sequence" -Title "Engage" -Children @(
                    (Get-EntityExistsBehavior -EntityKey "target"),
                    (New-CompositeNode -Type "selector" -Title "EngageSelector" -Children @(
                        (Get-MeleePreset -AttackRange $AttackRange),
                        (Get-ChasePreset -Speed $MoveSpeed -Range $AggroRange)
                    ))
                )),
                # Otherwise wander
                (Get-WanderPreset -MoveSpeed ($MoveSpeed * 0.5)),
                (New-RunnerNode)
            ))
        ))
    )
}

# ============================================================================
# SCRIPT DEPENDENCY RESOLVER
# ============================================================================

function Get-RequiredScripts {
    param([string]$Preset, [bool]$HasProjectile = $false)
    
    $scripts = @(
        $ScriptCategories["Movement"],
        $ScriptCategories["Time"]
    )
    
    switch ($Preset) {
        "Boss" {
            $scripts += @(
                $ScriptCategories["Entity"],
                $ScriptCategories["Monster"],
                $ScriptCategories["Status"],
                $ScriptCategories["Animator"],
                $ScriptCategories["Notification"],
                $ScriptCategories["BData"]
            )
        }
        "Attack" { 
            $scripts += @($ScriptCategories["Entity"], $ScriptCategories["Animator"])
        }
        "Ranged" {
            $scripts += @(
                $ScriptCategories["Entity"],
                $ScriptCategories["Animator"],
                $ScriptCategories["Projectiles"],
                $ScriptCategories["Math"]
            )
        }
        "Melee" {
            $scripts += @($ScriptCategories["Entity"], $ScriptCategories["Animator"])
        }
        "Chase" {
            $scripts += $ScriptCategories["Entity"]
        }
        "Flee" {
            $scripts += @($ScriptCategories["Entity"], $ScriptCategories["Math"])
        }
        "Guard" {
            $scripts += @($ScriptCategories["Entity"], $ScriptCategories["Position"], $ScriptCategories["Animator"])
        }
        "Targeting" {
            $scripts += @($ScriptCategories["Entity"], $ScriptCategories["Sensor"])
        }
        default {
            $scripts += @($ScriptCategories["Entity"], $ScriptCategories["Monster"])
        }
    }
    
    if ($HasProjectile) {
        if ($scripts -notcontains $ScriptCategories["Projectiles"]) {
            $scripts += $ScriptCategories["Projectiles"]
        }
        if ($scripts -notcontains $ScriptCategories["Math"]) {
            $scripts += $ScriptCategories["Math"]
        }
    }
    
    return $scripts | Select-Object -Unique
}

# ============================================================================
# MAIN GENERATION LOGIC
# ============================================================================

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Starbound Behavior Generator" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Create output directory
$outputPath = $OutputDir
if (-not [System.IO.Path]::IsPathRooted($OutputDir)) {
    $outputPath = Join-Path (Get-Location) $OutputDir
}

if (-not (Test-Path $outputPath)) {
    New-Item -ItemType Directory -Path $outputPath -Force | Out-Null
    Write-Host "[Created] Output directory: $outputPath" -ForegroundColor Green
}

# Determine if we have a projectile
$hasProjectile = -not [string]::IsNullOrEmpty($ProjectileType)

# Get required scripts
$scripts = Get-RequiredScripts -Preset $Preset -HasProjectile $hasProjectile
$scripts += $AdditionalScripts | Where-Object { $_ }
$scripts = $scripts | Select-Object -Unique

# Generate root node based on preset
Write-Host "[Generating] Behavior: $BehaviorName (Preset: $Preset)" -ForegroundColor Yellow

$rootNode = switch ($Preset) {
    "Idle" { Get-IdlePreset -IdleAnimation $IdleAnimation -Duration 5.0 }
    "Wander" { Get-WanderPreset -MoveSpeed $MoveSpeed -WanderTime 3 -IdleTime 2 }
    "Patrol" { Get-PatrolPreset -Radius $PatrolRadius -Speed $MoveSpeed -IdleTime $PatrolIdleTime }
    "Chase" { Get-ChasePreset -Speed $MoveSpeed -Range $AggroRange }
    "Flee" { Get-FleePreset -Speed ($MoveSpeed * 1.5) -FleeDistance $DeaggroRange }
    "Attack" { Get-AttackPreset -AttackAnimation $AttackAnimation -Cooldown $AttackCooldown -ProjectileType $ProjectileType -ProjectileOffset $ProjectileOffset }
    "Melee" { Get-MeleePreset -AttackRange $AttackRange -AttackAnimation $AttackAnimation -Cooldown $AttackCooldown }
    "Ranged" { Get-RangedPreset -AttackRange $AttackRange -ProjectileType $ProjectileType -ProjectileOffset $ProjectileOffset -Cooldown $AttackCooldown }
    "Guard" { Get-GuardPreset -GuardRadius $PatrolRadius -ChaseRange $AggroRange -AttackRange $AttackRange }
    "Boss" { Get-BossPreset -HealthStages $HealthStages -HealthThresholds $HealthThresholds -HasDamageBar $HasDamageBar -AggroRange $AggroRange -ProjectileType $ProjectileType -ProjectileOffset $ProjectileOffset }
    "Targeting" { Get-TargetingBehavior -QueryRange $AggroRange -KeepRange $DeaggroRange -EntityTypes $TargetTypes }
    "Custom" { 
        if ($CustomRoot) { $CustomRoot } 
        else { Get-DefaultPreset -AggroRange $AggroRange -AttackRange $AttackRange -MoveSpeed $MoveSpeed }
    }
    default { Get-DefaultPreset -AggroRange $AggroRange -AttackRange $AttackRange -MoveSpeed $MoveSpeed }
}

# Build behavior object
$behavior = [ordered]@{
    "name" = $BehaviorName
    "description" = $Description
    "scripts" = $scripts
    "parameters" = [ordered]@{}
    "root" = $rootNode
}

# Add common parameters based on preset
if ($Preset -eq "Boss" -or $hasProjectile) {
    if ($ProjectileOffset[0] -ne 0 -or $ProjectileOffset[1] -ne 0) {
        $behavior.parameters["projectileSpawnOffset"] = $ProjectileOffset
    }
}

# Convert to JSON
$jsonContent = $behavior | ConvertTo-Json -Depth 50

# Fix JSON formatting (PowerShell's ConvertTo-Json has quirks)
$jsonContent = $jsonContent -replace '(?m)^\s*"parameters":\s*\{\s*\}', '"parameters": {}'

# Write behavior file
$behaviorFile = Join-Path $outputPath "$BehaviorName.behavior"
$jsonContent | Out-File -FilePath $behaviorFile -Encoding UTF8 -Force

Write-Host ""
Write-Host "[SUCCESS] Generated behavior file:" -ForegroundColor Green
Write-Host "  $behaviorFile" -ForegroundColor White

# Summary
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Generation Summary" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Behavior Name: $BehaviorName" -ForegroundColor White
Write-Host "  Preset: $Preset" -ForegroundColor White
Write-Host "  Scripts: $($scripts.Count)" -ForegroundColor White
Write-Host "  Output: $behaviorFile" -ForegroundColor White

if ($Preset -eq "Boss") {
    Write-Host "  Health Stages: $HealthStages" -ForegroundColor Yellow
    Write-Host "  Damage Bar: $HasDamageBar" -ForegroundColor Yellow
}

if ($hasProjectile) {
    Write-Host "  Projectile: $ProjectileType" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Usage in Starbound:" -ForegroundColor Cyan
Write-Host "  Reference this behavior in your monster/NPC config:" -ForegroundColor Gray
Write-Host "  `"behavior`": `"$BehaviorName`"" -ForegroundColor White
Write-Host ""

return @{
    Success = $true
    BehaviorFile = $behaviorFile
    BehaviorName = $BehaviorName
    Preset = $Preset
}

