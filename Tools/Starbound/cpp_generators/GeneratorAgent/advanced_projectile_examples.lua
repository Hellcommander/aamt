-- Advanced Projectile Generation System Examples
-- This script demonstrates all five specialized projectile types with their unique capabilities

-- Callback functions for asset completion
function on_missile_ready(id, bundle)
    print("✓ Guided missile ready: " .. id)
    print("  - Mesh handle: " .. bundle.mesh)
    print("  - VFX shader: " .. bundle.vfxShader)
    print("  - Particle system: " .. bundle.particleSys)
    print("  - Hum audio: " .. bundle.humAudio)
    print("  - Guidance sim: " .. bundle.guidanceSim)
    print("  - Thrust sim: " .. bundle.thrustSim)
end

function on_grenade_ready(id, bundle)
    print("✓ Shard grenade ready: " .. id)
    print("  - Body mesh: " .. bundle.bodyMesh)
    print("  - Shard count: " .. #bundle.shards)
    print("  - Timer sim: " .. bundle.timerSim)
    print("  - Explosion VFX: " .. bundle.explosionVFX)
    print("  - Explosion audio: " .. bundle.explosionAudio)
end

function on_beam_ready(id, bundle)
    print("✓ Arc beam ready: " .. id)
    print("  - Beam mesh: " .. bundle.beamMesh)
    print("  - Wave sim: " .. bundle.waveSim)
    print("  - Shader: " .. bundle.shader)
    print("  - Crackle audio: " .. bundle.crackleAudio)
end

function on_boomerang_ready(id, bundle)
    print("✓ Boomerang ready: " .. id)
    print("  - Mesh: " .. bundle.mesh)
    print("  - Flight sim: " .. bundle.flightSim)
    print("  - Whoosh audio: " .. bundle.whooshAudio)
    print("  - Trail VFX: " .. bundle.trailVFX)
end

function on_grapnel_ready(id, bundle)
    print("✓ Grapnel ready: " .. id)
    print("  - Hook mesh: " .. bundle.hookMesh)
    print("  - Tether: " .. bundle.tether)
    print("  - Launch sim: " .. bundle.launchSim)
    print("  - Retract sim: " .. bundle.retractSim)
    print("  - Reel audio: " .. bundle.reelAudio)
end

-- Error handling callbacks
function on_missile_error(id, error_msg)
    print("✗ Missile generation failed: " .. id .. " - " .. error_msg)
end

function on_grenade_error(id, error_msg)
    print("✗ Grenade generation failed: " .. id .. " - " .. error_msg)
end

function on_beam_error(id, error_msg)
    print("✗ Beam generation failed: " .. id .. " - " .. error_msg)
end

function on_boomerang_error(id, error_msg)
    print("✗ Boomerang generation failed: " .. id .. " - " .. error_msg)
end

function on_grapnel_error(id, error_msg)
    print("✗ Grapnel generation failed: " .. id .. " - " .. error_msg)
end

-- ============================================================================
-- EXAMPLE 1: GUIDED MISSILE SYSTEM
-- ============================================================================

print("=== Example 1: Guided Missile System ===")

-- Create missile parameters using defaults
local guidance = create_default_guidance()
guidance.targetTag = "boss_enemy"
guidance.lockOnDelay = 1.0
guidance.turnRateDegPerSec = 240.0
guidance.proximityFuseDist = 3.0

local propulsion = create_default_propulsion()
propulsion.maxThrust = 800.0
propulsion.fuelCapacity = 8.0
propulsion.dragCoefficient = 0.2

local target = create_default_target()
target.targetTag = "boss_enemy"
target.homingRadius = 75.0
target.targetPosition = {x = 50.0, y = 0.0, z = 0.0}

if spawn_guided_missile(guidance, propulsion, target) then
    print("Guided missile generation started")
else
    print("Failed to start guided missile generation")
end

-- ============================================================================
-- EXAMPLE 2: SHARD-BURST GRENADE SYSTEM
-- ============================================================================

print("\n=== Example 2: Shard-Burst Grenade System ===")

-- Create grenade with high shard count
local grenade = create_default_grenade()
grenade.fuseTime = 2.5
grenade.blastRadius = 12.0
grenade.shardCount = 24
grenade.spreadAngleDeg = 60.0
grenade.randomizeCount = true

local shard = create_default_shard()
shard.meshType = "spike"
shard.materialType = "steel"
shard.minVelocity = 15.0
shard.maxVelocity = 35.0
shard.lifeTime = 3.0

if spawn_shard_grenade(grenade, shard) then
    print("Shard grenade generation started")
else
    print("Failed to start shard grenade generation")
end

-- ============================================================================
-- EXAMPLE 3: ARC BEAM SYSTEM
-- ============================================================================

print("\n=== Example 3: Arc Beam System ===")

-- Create electric arc beam
local beam = create_default_beam()
beam.duration = 3.0
beam.maxRange = 25.0
beam.thickness = 0.15
beam.branchProbability = 0.4
beam.segmentCount = 75

local glow = create_default_glow()
glow.innerColor = {r = 0.9, g = 0.95, b = 1.0}
glow.outerColor = {r = 0.1, g = 0.3, b = 0.8}
glow.pulseFrequency = 15.0
glow.intensity = 1.5

if spawn_arc_beam(beam, glow) then
    print("Arc beam generation started")
else
    print("Failed to start arc beam generation")
end

-- ============================================================================
-- EXAMPLE 4: BOOMERANG SYSTEM
-- ============================================================================

print("\n=== Example 4: Boomerang System ===")

-- Create fast-returning boomerang
local boomerang = create_default_boomerang()
boomerang.returnDelay = 1.0
boomerang.returnSpeed = 20.0
boomerang.liftCoefficient = 1.0
boomerang.dragCoefficient = 0.3
boomerang.spinRateRPM = 1500.0

if spawn_boomerang(boomerang) then
    print("Boomerang generation started")
else
    print("Failed to start boomerang generation")
end

-- ============================================================================
-- EXAMPLE 5: GRAPNEL HOOK SYSTEM
-- ============================================================================

print("\n=== Example 5: Grapnel Hook System ===")

-- Create long-range grapnel
local grapnel = create_default_grapnel()
grapnel.maxRange = 40.0
grapnel.launchSpeed = 30.0
grapnel.retractionSpeed = 10.0
grapnel.enableElasticity = true
grapnel.springConstant = 150.0

local hook = create_default_hook()
hook.meshType = "barbed"
hook.materialType = "titanium"
hook.autoDetach = false
hook.hookStrength = 2000.0

if spawn_grapnel(grapnel, hook) then
    print("Grapnel generation started")
else
    print("Failed to start grapnel generation")
end

-- ============================================================================
-- EXAMPLE 6: BATCH GENERATION
-- ============================================================================

print("\n=== Example 6: Batch Generation ===")

-- Generate multiple missiles with different configurations
local missile_types = {
    {name = "light_missile", thrust = 300, fuel = 3},
    {name = "medium_missile", thrust = 600, fuel = 6},
    {name = "heavy_missile", thrust = 1000, fuel = 10}
}

for i, missile_spec in ipairs(missile_types) do
    local guidance = create_default_guidance()
    guidance.targetTag = missile_spec.name
    guidance.turnRateDegPerSec = 180.0 + (i * 30.0)
    
    local propulsion = create_default_propulsion()
    propulsion.maxThrust = missile_spec.thrust
    propulsion.fuelCapacity = missile_spec.fuel
    
    local target = create_default_target()
    target.targetTag = missile_spec.name
    target.homingRadius = 50.0 + (i * 10.0)
    
    if spawn_guided_missile(guidance, propulsion, target) then
        print("Batch missile " .. i .. " generation started: " .. missile_spec.name)
    end
end

-- ============================================================================
-- EXAMPLE 7: CUSTOM CONFIGURATIONS
-- ============================================================================

print("\n=== Example 7: Custom Configurations ===")

-- Custom high-speed missile
local custom_guidance = GuidanceParams()
custom_guidance.enableLockOn = true
custom_guidance.lockOnDelay = 0.2
custom_guidance.turnRateDegPerSec = 360.0
custom_guidance.proximityFuseDist = 1.5

local custom_propulsion = PropulsionParams()
custom_propulsion.maxThrust = 1200.0
custom_propulsion.fuelCapacity = 4.0
custom_propulsion.dragCoefficient = 0.1

local custom_target = TargetParams()
custom_target.targetTag = "fast_target"
custom_target.homingRadius = 100.0
custom_target.targetPosition = {x = 100.0, y = 0.0, z = 0.0}

if custom_guidance:validate() and custom_propulsion:validate() and custom_target:validate() then
    if spawn_guided_missile(custom_guidance, custom_propulsion, custom_target) then
        print("Custom high-speed missile generation started")
    end
else
    print("Custom missile validation failed")
end

-- Custom fragmentation grenade
local custom_grenade = GrenadeParams()
custom_grenade.fuseTime = 1.5
custom_grenade.blastRadius = 15.0
custom_grenade.shardCount = 36
custom_grenade.spreadAngleDeg = 90.0
custom_grenade.randomizeCount = false

local custom_shard = ShardParams()
custom_shard.meshType = "shard"
custom_shard.materialType = "obsidian"
custom_shard.minVelocity = 20.0
custom_shard.maxVelocity = 40.0
custom_shard.lifeTime = 4.0

if custom_grenade:validate() and custom_shard:validate() then
    if spawn_shard_grenade(custom_grenade, custom_shard) then
        print("Custom fragmentation grenade generation started")
    end
else
    print("Custom grenade validation failed")
end

-- ============================================================================
-- EXAMPLE 8: INVALID CONFIGURATIONS (TESTING)
-- ============================================================================

print("\n=== Example 8: Invalid Configurations (Testing Validation) ===")

-- Test invalid missile parameters
local invalid_guidance = GuidanceParams()
invalid_guidance.lockOnDelay = -1.0  -- Invalid negative value
invalid_guidance.turnRateDegPerSec = 1000.0  -- Too high

if not invalid_guidance:validate() then
    print("Invalid guidance correctly rejected")
end

-- Test invalid grenade parameters
local invalid_grenade = GrenadeParams()
invalid_grenade.fuseTime = 50.0  -- Too long
invalid_grenade.shardCount = 200  -- Too many

if not invalid_grenade:validate() then
    print("Invalid grenade correctly rejected")
end

-- ============================================================================
-- EXAMPLE 9: STATUS MONITORING
-- ============================================================================

print("\n=== Example 9: Status Monitoring ===")

-- Monitor pending assets
local function check_advanced_status()
    local pending = get_advanced_pending_count()
    print("Pending advanced assets:")
    print("  - Missiles: " .. pending.missiles)
    print("  - Grenades: " .. pending.grenades)
    print("  - Beams: " .. pending.beams)
    print("  - Boomerangs: " .. pending.boomerangs)
    print("  - Grapnels: " .. pending.grapnels)
    
    local total = pending.missiles + pending.grenades + pending.beams + pending.boomerangs + pending.grapnels
    if total == 0 then
        print("All advanced asset generations completed!")
        return false  -- Stop monitoring
    end
    return true  -- Continue monitoring
end

-- ============================================================================
-- EXAMPLE 10: PERFORMANCE TESTING
-- ============================================================================

print("\n=== Example 10: Performance Testing ===")

local start_time = os.clock()
local test_count = 5

-- Test beam generation performance
for i = 1, test_count do
    local beam = create_default_beam()
    beam.segmentCount = 25 + (i * 5)
    beam.branchProbability = 0.2 + (i * 0.1)
    
    local glow = create_default_glow()
    glow.intensity = 0.5 + (i * 0.1)
    
    if beam:validate() and glow:validate() then
        spawn_arc_beam(beam, glow)
    end
end

print("Started " .. test_count .. " performance test beams")
print("Generation time per beam: " .. ((os.clock() - start_time) / test_count * 1000) .. "ms")

-- ============================================================================
-- EXAMPLE 11: SPECIALIZED CONFIGURATIONS
-- ============================================================================

print("\n=== Example 11: Specialized Configurations ===")

-- Stealth missile (low thrust, high maneuverability)
local stealth_guidance = create_default_guidance()
stealth_guidance.lockOnDelay = 0.1
stealth_guidance.turnRateDegPerSec = 450.0
stealth_guidance.proximityFuseDist = 1.0

local stealth_propulsion = create_default_propulsion()
stealth_propulsion.maxThrust = 200.0
stealth_propulsion.fuelCapacity = 6.0
stealth_propulsion.dragCoefficient = 0.1

local stealth_target = create_default_target()
stealth_target.targetTag = "stealth_target"
stealth_target.homingRadius = 30.0

if spawn_guided_missile(stealth_guidance, stealth_propulsion, stealth_target) then
    print("Stealth missile generation started")
end

-- Cluster grenade (multiple small explosions)
local cluster_grenade = create_default_grenade()
cluster_grenade.fuseTime = 1.0
cluster_grenade.blastRadius = 5.0
cluster_grenade.shardCount = 8
cluster_grenade.spreadAngleDeg = 30.0

local cluster_shard = create_default_shard()
cluster_shard.meshType = "sphere"
cluster_shard.minVelocity = 8.0
cluster_shard.maxVelocity = 15.0

if spawn_shard_grenade(cluster_grenade, cluster_shard) then
    print("Cluster grenade generation started")
end

-- Lightning beam (high frequency, branching)
local lightning_beam = create_default_beam()
lightning_beam.duration = 1.0
lightning_beam.maxRange = 15.0
lightning_beam.thickness = 0.05
lightning_beam.branchProbability = 0.6
lightning_beam.segmentCount = 100

local lightning_glow = create_default_glow()
lightning_glow.innerColor = {r = 1.0, g = 1.0, b = 1.0}
lightning_glow.outerColor = {r = 0.0, g = 0.5, b = 1.0}
lightning_glow.pulseFrequency = 30.0
lightning_glow.intensity = 2.0

if spawn_arc_beam(lightning_beam, lightning_glow) then
    print("Lightning beam generation started")
end

-- Precision boomerang (long range, slow return)
local precision_boomerang = create_default_boomerang()
precision_boomerang.returnDelay = 3.0
precision_boomerang.returnSpeed = 8.0
precision_boomerang.liftCoefficient = 1.2
precision_boomerang.dragCoefficient = 0.2
precision_boomerang.spinRateRPM = 800.0

if spawn_boomerang(precision_boomerang) then
    print("Precision boomerang generation started")
end

-- Heavy grapnel (high strength, slow retraction)
local heavy_grapnel = create_default_grapnel()
heavy_grapnel.maxRange = 50.0
heavy_grapnel.launchSpeed = 20.0
heavy_grapnel.retractionSpeed = 5.0
heavy_grapnel.enableElasticity = false
heavy_grapnel.springConstant = 500.0

local heavy_hook = create_default_hook()
heavy_hook.meshType = "anchor"
heavy_hook.materialType = "tungsten"
heavy_hook.autoDetach = false
heavy_hook.hookStrength = 5000.0

if spawn_grapnel(heavy_grapnel, heavy_hook) then
    print("Heavy grapnel generation started")
end

print("\n=== Advanced Projectile Generation System Demo Complete ===")
print("Check the logs for detailed generation information and any errors.")
print("Use get_advanced_pending_count() to monitor asset generation progress.") 