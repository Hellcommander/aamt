-- Gyro Projectile Generation System Examples
-- This script demonstrates the comprehensive gyro projectile system with all its features

-- Callback functions for asset completion
function on_gyro_ready(id, bundle)
    print("✓ Gyro projectile ready: " .. id)
    print("  - Mesh handle: " .. bundle.mesh)
    print("  - Flight simulation: " .. bundle.flightSim)
    print("  - Trail mesh: " .. bundle.trailMesh)
    print("  - VFX shader: " .. bundle.vfxShader)
    print("  - Particle system: " .. bundle.particleSys)
    print("  - Hum audio: " .. bundle.humAudio)
    print("  - Impact audio: " .. bundle.impactAudio)
    print("  - Collider: " .. bundle.collider)
end

function on_gyro_error(id, error_msg)
    print("✗ Gyro projectile generation failed: " .. id .. " - " .. error_msg)
end

-- ============================================================================
-- EXAMPLE 1: BASIC GYRO PROJECTILE
-- ============================================================================

print("=== Example 1: Basic Gyro Projectile ===")

-- Create default parameters
local gyro = create_default_gyro()
gyro.id = "basic_gyro"
gyro.shape = "Disc"
gyro.radius = 0.5
gyro.thickness = 0.1
gyro.hollow = false
gyro.dynamicTess = false

local flight = create_default_flight()
flight.initialSpeed = 50.0
flight.spinRateRPM = 3600.0
flight.precessionRateDeg = 30.0
flight.stabilityFactor = 0.9
flight.gravityEnabled = true
flight.gravityScale = 1.0

local trail = create_default_trail()
trail.enableTrail = true
trail.type = "Ribbon"
trail.length = 2.0
trail.width = 0.1
trail.headColor = {1, 1, 1, 1}
trail.tailColor = {1, 1, 1, 0}
trail.uvScrollSpeed = 1.0

local vfx = create_default_vfx()
vfx.shaderTemplate = "shaders/gyro_glow.frag"
vfx.defines = {"USE_GYRO_BLUR"}
vfx.glowIntensity = 1.0
vfx.flickerSpeed = 5.0
vfx.flickerMode = "None"

local particles = create_default_particles()
particles.enableParticles = true
particles.style = "Sparks"
particles.count = 100
particles.spawnRate = 200.0
particles.lifeTime = 0.5
particles.velocityMin = {-1, -1, -1}
particles.velocityMax = {1, 1, 1}

local audio = create_default_audio()
audio.playOnLaunch = true
audio.humFile = "sfx/gyro_hum.wav"
audio.impactFile = "sfx/gyro_impact.wav"
audio.volume = 1.0
audio.pitchVariance = 0.0

local collision = create_default_collision()
collision.enableCollider = true
collision.meshCollider = false
collision.radius = 0.5
collision.triggerOnly = false
collision.enableCCD = true

if spawn_gyro(gyro, flight, trail, vfx, particles, audio, collision) then
    print("Basic gyro projectile generation started")
else
    print("Failed to start basic gyro projectile generation")
end

-- ============================================================================
-- EXAMPLE 2: FAST SPINNER (HIGH-SPEED RING)
-- ============================================================================

print("\n=== Example 2: Fast Spinner (High-Speed Ring) ===")

local fastGyro = create_fast_spinner()
local fastFlight = createFastSpinnerFlight()

local fastTrail = create_default_trail()
fastTrail.type = "Streaks"
fastTrail.length = 1.5
fastTrail.width = 0.05
fastTrail.headColor = {1, 0.8, 0.2, 1}
fastTrail.tailColor = {0.5, 0.3, 0.1, 0}
fastTrail.uvScrollSpeed = 3.0

local fastVFX = create_default_vfx()
fastVFX.glowIntensity = 1.5
fastVFX.flickerSpeed = 10.0
fastVFX.flickerMode = "Sinusoidal"

local fastParticles = create_default_particles()
fastParticles.style = "Sparkle"
fastParticles.count = 50
fastParticles.spawnRate = 300.0
fastParticles.lifeTime = 0.3

local fastAudio = create_default_audio()
fastAudio.volume = 0.8
fastAudio.pitchVariance = 0.2

local fastCollision = create_default_collision()
fastCollision.radius = 0.3

if spawn_gyro(fastGyro, fastFlight, fastTrail, fastVFX, fastParticles, fastAudio, fastCollision) then
    print("Fast spinner gyro projectile generation started")
else
    print("Failed to start fast spinner generation")
end

-- ============================================================================
-- EXAMPLE 3: HEAVY GYRO (SLOW, POWERFUL)
-- ============================================================================

print("\n=== Example 3: Heavy Gyro (Slow, Powerful) ===")

local heavyGyro = create_heavy_gyro()
local heavyFlight = createHeavyGyroFlight()

local heavyTrail = create_default_trail()
heavyTrail.type = "Ribbon"
heavyTrail.length = 3.0
heavyTrail.width = 0.15
heavyTrail.headColor = {0.8, 0.2, 0.2, 1}
heavyTrail.tailColor = {0.4, 0.1, 0.1, 0}
heavyTrail.uvScrollSpeed = 0.5

local heavyVFX = create_default_vfx()
heavyVFX.glowIntensity = 0.8
heavyVFX.flickerSpeed = 2.0
heavyVFX.flickerMode = "NoiseDriven"

local heavyParticles = create_default_particles()
heavyParticles.style = "Smoke"
heavyParticles.count = 200
heavyParticles.spawnRate = 100.0
heavyParticles.lifeTime = 1.0

local heavyAudio = create_default_audio()
heavyAudio.volume = 1.2
heavyAudio.pitchVariance = 0.1

local heavyCollision = create_default_collision()
heavyCollision.radius = 0.8

if spawn_gyro(heavyGyro, heavyFlight, heavyTrail, heavyVFX, heavyParticles, heavyAudio, heavyCollision) then
    print("Heavy gyro projectile generation started")
else
    print("Failed to start heavy gyro generation")
end

-- ============================================================================
-- EXAMPLE 4: STEALTH GYRO (MINIMAL VFX)
-- ============================================================================

print("\n=== Example 4: Stealth Gyro (Minimal VFX) ===")

local stealthGyro = create_stealth_gyro()
local stealthFlight = createStealthGyroFlight()

local stealthTrail = create_default_trail()
stealthTrail.enableTrail = false

local stealthVFX = create_default_vfx()
stealthVFX.glowIntensity = 0.3
stealthVFX.flickerSpeed = 0.0
stealthVFX.flickerMode = "None"

local stealthParticles = create_default_particles()
stealthParticles.enableParticles = false

local stealthAudio = create_default_audio()
stealthAudio.volume = 0.3
stealthAudio.pitchVariance = 0.05

local stealthCollision = create_default_collision()
stealthCollision.radius = 0.2

if spawn_gyro(stealthGyro, stealthFlight, stealthTrail, stealthVFX, stealthParticles, stealthAudio, stealthCollision) then
    print("Stealth gyro projectile generation started")
else
    print("Failed to start stealth gyro generation")
end

-- ============================================================================
-- EXAMPLE 5: SHOWY GYRO (MAXIMUM VFX)
-- ============================================================================

print("\n=== Example 5: Showy Gyro (Maximum VFX) ===")

local showyGyro = create_showy_gyro()
local showyFlight = createShowyGyroFlight()

local showyTrail = create_default_trail()
showyTrail.type = "Ribbon"
showyTrail.length = 4.0
showyTrail.width = 0.2
showyTrail.headColor = {1, 1, 0, 1}
showyTrail.tailColor = {0.5, 0.5, 0, 0}
showyTrail.uvScrollSpeed = 2.0

local showyVFX = create_default_vfx()
showyVFX.glowIntensity = 2.0
showyVFX.flickerSpeed = 15.0
showyVFX.flickerMode = "NoiseDriven"
showyVFX.defines = {"USE_GYRO_BLUR", "USE_COLOR_SHIFT", "USE_PULSE"}

local showyParticles = create_default_particles()
showyParticles.style = "Sparkle"
showyParticles.count = 300
showyParticles.spawnRate = 500.0
showyParticles.lifeTime = 0.8

local showyAudio = create_default_audio()
showyAudio.volume = 1.5
showyAudio.pitchVariance = 0.3

local showyCollision = create_default_collision()
showyCollision.radius = 0.6

if spawn_gyro(showyGyro, showyFlight, showyTrail, showyVFX, showyParticles, showyAudio, showyCollision) then
    print("Showy gyro projectile generation started")
else
    print("Failed to start showy gyro generation")
end

-- ============================================================================
-- EXAMPLE 6: CUSTOM CONFIGURATIONS
-- ============================================================================

print("\n=== Example 6: Custom Configurations ===")

-- Custom spindle gyro
local customGyro = GyroParams()
customGyro.id = "custom_spindle"
customGyro.shape = "Spindle"
customGyro.radius = 0.25
customGyro.thickness = 0.5
customGyro.hollow = false
customGyro.dynamicTess = true

local customFlight = FlightParams()
customFlight.initialSpeed = 75.0
customFlight.spinRateRPM = 4200.0
customFlight.precessionRateDeg = 20.0
customFlight.stabilityFactor = 0.92
customFlight.gravityEnabled = true
customFlight.gravityScale = 0.7

local customTrail = TrailParams()
customTrail.enableTrail = true
customTrail.type = "Particles"
customTrail.length = 1.8
customTrail.width = 0.08
customTrail.headColor = {0.2, 0.8, 1.0, 1.0}
customTrail.tailColor = {0.1, 0.4, 0.5, 0.0}
customTrail.uvScrollSpeed = 1.5

local customVFX = VFXParams()
customVFX.shaderTemplate = "shaders/gyro_ice.frag"
customVFX.defines = {"USE_ICE_EFFECT", "USE_FROST_TRAIL"}
customVFX.glowIntensity = 1.3
customVFX.flickerSpeed = 8.0
customVFX.flickerMode = "Sinusoidal"

local customParticles = ParticleParams()
customParticles.enableParticles = true
customParticles.style = "Sparkle"
customParticles.count = 150
customParticles.spawnRate = 250.0
customParticles.lifeTime = 0.6
customParticles.velocityMin = {-0.5, -0.5, -0.5}
customParticles.velocityMax = {0.5, 0.5, 0.5}

local customAudio = AudioParams()
customAudio.playOnLaunch = true
customAudio.humFile = "sfx/ice_gyro_hum.wav"
customAudio.impactFile = "sfx/ice_gyro_impact.wav"
customAudio.volume = 0.9
customAudio.pitchVariance = 0.15

local customCollision = CollisionParams()
customCollision.enableCollider = true
customCollision.meshCollider = false
customCollision.radius = 0.25
customCollision.triggerOnly = false
customCollision.enableCCD = true

if customGyro:validate() and customFlight:validate() and customTrail:validate() and
   customVFX:validate() and customParticles:validate() and customAudio:validate() and
   customCollision:validate() then
    if spawn_gyro(customGyro, customFlight, customTrail, customVFX, customParticles, customAudio, customCollision) then
        print("Custom spindle gyro projectile generation started")
    end
else
    print("Custom gyro validation failed")
end

-- ============================================================================
-- EXAMPLE 7: INVALID CONFIGURATIONS (TESTING)
-- ============================================================================

print("\n=== Example 7: Invalid Configurations (Testing) ===")

-- Test invalid gyro parameters
local invalidGyro = GyroParams()
invalidGyro.id = ""  -- Empty ID
invalidGyro.radius = -1.0  -- Negative radius
invalidGyro.thickness = 5.0  -- Too thick

if not invalidGyro:validate() then
    print("Invalid gyro correctly rejected")
end

-- Test invalid flight parameters
local invalidFlight = FlightParams()
invalidFlight.initialSpeed = -10.0  -- Negative speed
invalidFlight.spinRateRPM = 15000.0  -- Too high
invalidFlight.stabilityFactor = 1.5  -- Out of range

if not invalidFlight:validate() then
    print("Invalid flight correctly rejected")
end

-- ============================================================================
-- EXAMPLE 8: BATCH GENERATION
-- ============================================================================

print("\n=== Example 8: Batch Generation ===")

-- Generate multiple gyros with different configurations
local gyro_types = {
    {name = "light_gyro", radius = 0.3, speed = 60, spin = 4800},
    {name = "medium_gyro", radius = 0.5, speed = 50, spin = 3600},
    {name = "heavy_gyro", radius = 0.7, speed = 40, spin = 2400}
}

for i, gyro_spec in ipairs(gyro_types) do
    local batchGyro = create_default_gyro()
    batchGyro.id = gyro_spec.name
    batchGyro.radius = gyro_spec.radius
    
    local batchFlight = create_default_flight()
    batchFlight.initialSpeed = gyro_spec.speed
    batchFlight.spinRateRPM = gyro_spec.spin
    
    local batchTrail = create_default_trail()
    batchTrail.headColor = {0.5 + (i * 0.2), 0.3, 0.8, 1.0}
    
    local batchVFX = create_default_vfx()
    batchVFX.glowIntensity = 0.8 + (i * 0.2)
    
    local batchParticles = create_default_particles()
    batchParticles.count = 50 + (i * 25)
    
    local batchAudio = create_default_audio()
    batchAudio.volume = 0.7 + (i * 0.1)
    
    local batchCollision = create_default_collision()
    batchCollision.radius = gyro_spec.radius
    
    if spawn_gyro(batchGyro, batchFlight, batchTrail, batchVFX, batchParticles, batchAudio, batchCollision) then
        print("Batch gyro " .. i .. " generation started: " .. gyro_spec.name)
    end
end

-- ============================================================================
-- EXAMPLE 9: STATUS MONITORING
-- ============================================================================

print("\n=== Example 9: Status Monitoring ===")

-- Monitor pending assets
local function check_gyro_status()
    local pending = get_gyro_pending_count()
    print("Pending gyro projectiles: " .. pending)
    
    if pending == 0 then
        print("All gyro projectile generations completed!")
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

-- Test gyro generation performance
for i = 1, test_count do
    local testGyro = create_default_gyro()
    testGyro.id = "perf_test_" .. i
    testGyro.radius = 0.3 + (i * 0.1)
    
    local testFlight = create_default_flight()
    testFlight.spinRateRPM = 3000 + (i * 500)
    
    local testTrail = create_default_trail()
    testTrail.length = 1.0 + (i * 0.5)
    
    local testVFX = create_default_vfx()
    testVFX.glowIntensity = 0.5 + (i * 0.1)
    
    local testParticles = create_default_particles()
    testParticles.count = 50 + (i * 10)
    
    local testAudio = create_default_audio()
    testAudio.volume = 0.5 + (i * 0.1)
    
    local testCollision = create_default_collision()
    testCollision.radius = testGyro.radius
    
    if testGyro:validate() and testFlight:validate() and testTrail:validate() and
       testVFX:validate() and testParticles:validate() and testAudio:validate() and
       testCollision:validate() then
        spawn_gyro(testGyro, testFlight, testTrail, testVFX, testParticles, testAudio, testCollision)
    end
end

print("Started " .. test_count .. " performance test gyros")
print("Generation time per gyro: " .. ((os.clock() - start_time) / test_count * 1000) .. "ms")

-- ============================================================================
-- EXAMPLE 11: SPECIALIZED CONFIGURATIONS
-- ============================================================================

print("\n=== Example 11: Specialized Configurations ===")

-- Fire gyro (red/orange theme)
local fireGyro = create_default_gyro()
fireGyro.id = "fire_gyro"
fireGyro.shape = "Ring"
fireGyro.radius = 0.4
fireGyro.hollow = true

local fireFlight = create_default_flight()
fireFlight.initialSpeed = 70.0
fireFlight.spinRateRPM = 5400.0
fireFlight.precessionRateDeg = 40.0

local fireTrail = create_default_trail()
fireTrail.headColor = {1.0, 0.3, 0.0, 1.0}
fireTrail.tailColor = {0.5, 0.1, 0.0, 0.0}

local fireVFX = create_default_vfx()
fireVFX.glowIntensity = 1.8
fireVFX.flickerSpeed = 12.0
fireVFX.flickerMode = "NoiseDriven"

local fireParticles = create_default_particles()
fireParticles.style = "Sparks"
fireParticles.count = 200
fireParticles.spawnRate = 400.0

if spawn_gyro(fireGyro, fireFlight, fireTrail, fireVFX, fireParticles, create_default_audio(), create_default_collision()) then
    print("Fire gyro projectile generation started")
end

-- Ice gyro (blue/white theme)
local iceGyro = create_default_gyro()
iceGyro.id = "ice_gyro"
iceGyro.shape = "Spindle"
iceGyro.radius = 0.25
iceGyro.thickness = 0.5

local iceFlight = create_default_flight()
iceFlight.initialSpeed = 45.0
iceFlight.spinRateRPM = 3000.0
iceFlight.precessionRateDeg = 15.0

local iceTrail = create_default_trail()
iceTrail.headColor = {0.7, 0.9, 1.0, 1.0}
iceTrail.tailColor = {0.3, 0.5, 0.7, 0.0}

local iceVFX = create_default_vfx()
iceVFX.glowIntensity = 1.2
iceVFX.flickerSpeed = 3.0
iceVFX.flickerMode = "Sinusoidal"

local iceParticles = create_default_particles()
iceParticles.style = "Sparkle"
iceParticles.count = 80
iceParticles.spawnRate = 150.0

if spawn_gyro(iceGyro, iceFlight, iceTrail, iceVFX, iceParticles, create_default_audio(), create_default_collision()) then
    print("Ice gyro projectile generation started")
end

-- Lightning gyro (yellow/white theme)
local lightningGyro = create_default_gyro()
lightningGyro.id = "lightning_gyro"
lightningGyro.shape = "Disc"
lightningGyro.radius = 0.35
lightningGyro.dynamicTess = true

local lightningFlight = create_default_flight()
lightningFlight.initialSpeed = 90.0
lightningFlight.spinRateRPM = 7200.0
lightningFlight.precessionRateDeg = 80.0

local lightningTrail = create_default_trail()
lightningTrail.headColor = {1.0, 1.0, 0.2, 1.0}
lightningTrail.tailColor = {0.5, 0.5, 0.1, 0.0}

local lightningVFX = create_default_vfx()
lightningVFX.glowIntensity = 2.5
lightningVFX.flickerSpeed = 20.0
lightningVFX.flickerMode = "NoiseDriven"

local lightningParticles = create_default_particles()
lightningParticles.style = "Sparks"
lightningParticles.count = 300
lightningParticles.spawnRate = 600.0

if spawn_gyro(lightningGyro, lightningFlight, lightningTrail, lightningVFX, lightningParticles, create_default_audio(), create_default_collision()) then
    print("Lightning gyro projectile generation started")
end

print("\n=== Gyro Projectile Generation System Demo Complete ===")
print("Check the logs for detailed generation information and any errors.")
print("Use get_gyro_pending_count() to monitor asset generation progress.") 