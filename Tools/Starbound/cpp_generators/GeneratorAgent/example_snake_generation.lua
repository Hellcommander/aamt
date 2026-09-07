-- Snake Spell Generation Example
-- This script demonstrates the comprehensive snake spell generation pipeline

print("=== Snake Spell Generation Example ===")

-- Initialize the snake spell system
local function initialize_snake_system()
    print("Initializing snake spell generation system...")
    -- The factory should be initialized by the C++ backend
    -- This is just a placeholder for demonstration
end

-- Example 1: Basic predefined snake spells
local function create_basic_snakes()
    print("\n--- Creating Basic Predefined Snake Spells ---")
    
    -- Venom snake spell
    spawn_venom_snake(4.0, 12)
    
    -- Fire snake spell
    spawn_fire_snake(4.0, 12)
    
    -- Ice snake spell
    spawn_ice_snake(4.0, 12)
    
    -- Lightning snake spell
    spawn_lightning_snake(4.0, 12)
    
    print("Basic snake spells queued for generation")
end

-- Example 2: Custom snake creation
local function create_custom_snakes()
    print("\n--- Creating Custom Snake Spells ---")
    
    -- Custom venom snake
    local venomBody = create_snake_body(16, 5.0, 0.12)
    venomBody.scaleMaterial = "mat/scales_custom_venom"
    
    local venomMotion = create_snake_motion(true, true)
    venomMotion.curlFrequency = 3.0
    venomMotion.curlAmplitude = 0.4
    venomMotion.homingTurnRate = 55.0
    
    local venomVFX = create_snake_vfx(true, {0.0, 0.9, 0.0, 1.0})  -- Bright green
    venomVFX.glowIntensity = 1.8
    venomVFX.pulsateSpeed = 2.5
    
    local venomParticles = create_snake_particles(true, true)
    venomParticles.dripRate = 10.0
    venomParticles.venomColor = {0.0, 0.7, 0.0, 1.0}
    venomParticles.smokeDensity = 18.0
    
    local venomAudio = create_snake_audio(true, true)
    venomAudio.hissFile = "sfx/custom_venom_hiss.wav"
    venomAudio.hissVolume = 0.8
    venomAudio.rattleFile = "sfx/custom_venom_impact.wav"
    
    local venomCollision = create_snake_collision(16, 0.12)
    
    spawn_snake_spell(venomBody, venomMotion, venomVFX, venomParticles, venomAudio, venomCollision)
    
    -- Custom fire snake
    local fireBody = create_snake_body(14, 4.5, 0.16)
    fireBody.scaleMaterial = "mat/scales_custom_fire"
    
    local fireMotion = create_snake_motion(true, true)
    fireMotion.curlFrequency = 3.5
    fireMotion.curlAmplitude = 0.5
    fireMotion.homingTurnRate = 70.0
    
    local fireVFX = create_snake_vfx(true, {1.0, 0.2, 0.0, 1.0})  -- Bright red
    fireVFX.glowIntensity = 2.5
    fireVFX.pulsateSpeed = 5.0
    
    local fireParticles = create_snake_particles(true, true)
    fireParticles.dripRate = 15.0
    fireParticles.venomColor = {1.0, 0.1, 0.0, 1.0}
    fireParticles.smokeDensity = 25.0
    
    local fireAudio = create_snake_audio(true, true)
    fireAudio.hissFile = "sfx/custom_fire_hiss.wav"
    fireAudio.hissVolume = 0.9
    fireAudio.rattleFile = "sfx/custom_fire_impact.wav"
    
    local fireCollision = create_snake_collision(14, 0.16)
    
    spawn_snake_spell(fireBody, fireMotion, fireVFX, fireParticles, fireAudio, fireCollision)
    
    print("Custom snake spells queued for generation")
end

-- Example 3: Elemental snake variations
local function create_elemental_variations()
    print("\n--- Creating Elemental Snake Variations ---")
    
    local elements = {
        {name = "venom", color = {0.0, 0.8, 0.0, 1.0}, venomColor = {0.0, 0.6, 0.0, 1.0}, curlFreq = 2.5, turnRate = 45},
        {name = "fire", color = {1.0, 0.3, 0.0, 1.0}, venomColor = {1.0, 0.2, 0.0, 1.0}, curlFreq = 3.0, turnRate = 60},
        {name = "ice", color = {0.5, 0.8, 1.0, 1.0}, venomColor = {0.3, 0.7, 1.0, 1.0}, curlFreq = 1.8, turnRate = 35},
        {name = "lightning", color = {1.0, 1.0, 0.0, 1.0}, venomColor = {1.0, 1.0, 0.0, 1.0}, curlFreq = 4.0, turnRate = 80},
        {name = "earth", color = {0.6, 0.4, 0.2, 1.0}, venomColor = {0.5, 0.3, 0.1, 1.0}, curlFreq = 1.5, turnRate = 30}
    }
    
    for i, element in ipairs(elements) do
        local body = create_snake_body(12, 4.0, 0.18)
        body.scaleMaterial = "mat/scales_" .. element.name
        
        local motion = create_snake_motion(true, true)
        motion.curlFrequency = element.curlFreq
        motion.curlAmplitude = 0.3
        motion.homingTurnRate = element.turnRate
        
        local vfx = create_snake_vfx(true, element.color)
        vfx.glowIntensity = 1.5
        vfx.pulsateSpeed = 3.0
        
        local particles = create_snake_particles(true, true)
        particles.dripRate = 8.0
        particles.venomColor = element.venomColor
        particles.smokeDensity = 15.0
        
        local audio = create_snake_audio(true, true)
        audio.hissFile = "sfx/snake_" .. element.name .. "_hiss.wav"
        audio.hissVolume = 0.7
        audio.rattleFile = "sfx/" .. element.name .. "_impact.wav"
        
        local collision = create_snake_collision(12, 0.18)
        
        spawn_snake_spell(body, motion, vfx, particles, audio, collision)
    end
    
    print("Elemental snake variations queued for generation")
end

-- Example 4: Advanced snake configurations
local function create_advanced_snakes()
    print("\n--- Creating Advanced Snake Configurations ---")
    
    -- Multi-element snake
    local multiBody = create_snake_body(20, 6.0, 0.2)
    multiBody.scaleMaterial = "mat/scales_multi_element"
    
    local multiMotion = create_snake_motion(true, true)
    multiMotion.curlFrequency = 2.8
    multiMotion.curlAmplitude = 0.6
    multiMotion.homingTurnRate = 65.0
    
    local multiVFX = create_snake_vfx(true, {1.0, 0.5, 0.0, 1.0})  -- Orange
    multiVFX.glowIntensity = 3.0
    multiVFX.pulsateSpeed = 4.5
    
    local multiParticles = create_snake_particles(true, true)
    multiParticles.dripRate = 20.0
    multiParticles.venomColor = {1.0, 0.3, 0.0, 1.0}
    multiParticles.smokeDensity = 30.0
    
    local multiAudio = create_snake_audio(true, true)
    multiAudio.hissFile = "sfx/multi_element_hiss.wav"
    multiAudio.hissVolume = 1.0
    multiAudio.rattleFile = "sfx/multi_element_impact.wav"
    
    local multiCollision = create_snake_collision(20, 0.2)
    
    spawn_snake_spell(multiBody, multiMotion, multiVFX, multiParticles, multiAudio, multiCollision)
    
    -- Stealth snake (minimal effects)
    local stealthBody = create_snake_body(8, 3.0, 0.1)
    stealthBody.scaleMaterial = "mat/scales_stealth"
    
    local stealthMotion = create_snake_motion(false, true)  -- No curl, just homing
    stealthMotion.homingTurnRate = 25.0
    
    local stealthVFX = create_snake_vfx(false)  -- No glow
    
    local stealthParticles = create_snake_particles(false, false)  -- No particles
    
    local stealthAudio = create_snake_audio(true, true)
    stealthAudio.hissFile = "sfx/stealth_hiss.wav"
    stealthAudio.hissVolume = 0.3
    stealthAudio.rattleFile = "sfx/stealth_impact.wav"
    
    local stealthCollision = create_snake_collision(8, 0.1)
    
    spawn_snake_spell(stealthBody, stealthMotion, stealthVFX, stealthParticles, stealthAudio, stealthCollision)
    
    print("Advanced snake spells queued for generation")
end

-- Example 5: Snake size variations
local function create_snake_size_variations()
    print("\n--- Creating Snake Size Variations ---")
    
    local snakeSizes = {
        {name = "tiny", length = 2.0, segments = 8, radius = 0.08},
        {name = "small", length = 3.0, segments = 10, radius = 0.12},
        {name = "medium", length = 4.0, segments = 12, radius = 0.16},
        {name = "large", length = 5.0, segments = 14, radius = 0.2},
        {name = "huge", length = 6.0, segments = 16, radius = 0.24}
    }
    
    for i, size in ipairs(snakeSizes) do
        local body = create_snake_body(size.segments, size.length, size.radius)
        body.scaleMaterial = "mat/scales_" .. size.name
        
        local motion = create_snake_motion(true, true)
        motion.curlFrequency = 2.0 + size.segments * 0.1
        motion.curlAmplitude = 0.2 + size.radius * 2.0
        motion.homingTurnRate = 40.0 + size.segments * 2.0
        
        local vfx = create_snake_vfx(true, {0.0, 0.8, 0.0, 1.0})
        vfx.glowIntensity = 1.0 + size.radius * 5.0
        vfx.pulsateSpeed = 2.0 + size.segments * 0.2
        
        local particles = create_snake_particles(true, true)
        particles.dripRate = 5.0 + size.segments * 0.5
        particles.smokeDensity = 10.0 + size.segments * 1.0
        
        local audio = create_snake_audio(true, true)
        audio.hissVolume = 0.5 + size.radius * 2.0
        
        local collision = create_snake_collision(size.segments, size.radius)
        
        spawn_snake_spell(body, motion, vfx, particles, audio, collision)
    end
    
    print("Snake size variations queued for generation")
end

-- Example 6: Performance testing snakes
local function create_performance_test_snakes()
    print("\n--- Creating Performance Test Snakes ---")
    
    -- High segment count snake
    local highSegmentBody = create_snake_body(32, 8.0, 0.15)
    highSegmentBody.scaleMaterial = "mat/scales_performance_test"
    
    local highSegmentMotion = create_snake_motion(true, true)
    highSegmentMotion.curlFrequency = 4.0
    highSegmentMotion.curlAmplitude = 0.8
    highSegmentMotion.homingTurnRate = 100.0
    
    local highSegmentVFX = create_snake_vfx(true, {1.0, 0.0, 1.0, 1.0})  -- Magenta
    highSegmentVFX.glowIntensity = 4.0
    highSegmentVFX.pulsateSpeed = 10.0
    
    local highSegmentParticles = create_snake_particles(true, true)
    highSegmentParticles.dripRate = 50.0  -- High drip rate for testing
    highSegmentParticles.venomColor = {1.0, 0.0, 1.0, 1.0}
    highSegmentParticles.smokeDensity = 50.0  -- High smoke density for testing
    
    local highSegmentAudio = create_snake_audio(true, true)
    highSegmentAudio.hissFile = "sfx/performance_test_hiss.wav"
    highSegmentAudio.hissVolume = 1.0
    highSegmentAudio.rattleFile = "sfx/performance_test_impact.wav"
    
    local highSegmentCollision = create_snake_collision(32, 0.15)
    
    spawn_snake_spell(highSegmentBody, highSegmentMotion, highSegmentVFX, highSegmentParticles, 
                      highSegmentAudio, highSegmentCollision)
    
    print("Performance test snakes queued for generation")
end

-- Example 7: Specialized snake behaviors
local function create_specialized_snakes()
    print("\n--- Creating Specialized Snake Behaviors ---")
    
    -- Homing missile snake
    local homingBody = create_snake_body(10, 3.5, 0.14)
    homingBody.scaleMaterial = "mat/scales_homing"
    
    local homingMotion = create_snake_motion(false, true)  -- No curl, pure homing
    homingMotion.homingTurnRate = 120.0  -- Very fast turning
    
    local homingVFX = create_snake_vfx(true, {1.0, 0.0, 0.0, 1.0})  -- Red
    homingVFX.glowIntensity = 2.0
    homingVFX.pulsateSpeed = 6.0
    
    local homingParticles = create_snake_particles(false, true)  -- No venom, just smoke
    homingParticles.smokeDensity = 20.0
    
    local homingAudio = create_snake_audio(true, true)
    homingAudio.hissFile = "sfx/homing_hiss.wav"
    homingAudio.hissVolume = 0.8
    homingAudio.rattleFile = "sfx/homing_impact.wav"
    
    local homingCollision = create_snake_collision(10, 0.14)
    
    spawn_snake_spell(homingBody, homingMotion, homingVFX, homingParticles, homingAudio, homingCollision)
    
    -- Curling display snake
    local curlingBody = create_snake_body(18, 5.0, 0.18)
    curlingBody.scaleMaterial = "mat/scales_curling"
    
    local curlingMotion = create_snake_motion(true, false)  -- Curl only, no homing
    curlingMotion.curlFrequency = 1.5
    curlingMotion.curlAmplitude = 1.0  -- Large amplitude for display
    
    local curlingVFX = create_snake_vfx(true, {0.0, 1.0, 1.0, 1.0})  -- Cyan
    curlingVFX.glowIntensity = 1.8
    curlingVFX.pulsateSpeed = 2.0
    
    local curlingParticles = create_snake_particles(true, true)
    curlingParticles.dripRate = 12.0
    curlingParticles.venomColor = {0.0, 0.8, 0.8, 1.0}
    curlingParticles.smokeDensity = 18.0
    
    local curlingAudio = create_snake_audio(true, true)
    curlingAudio.hissFile = "sfx/curling_hiss.wav"
    curlingAudio.hissVolume = 0.6
    curlingAudio.rattleFile = "sfx/curling_impact.wav"
    
    local curlingCollision = create_snake_collision(18, 0.18)
    
    spawn_snake_spell(curlingBody, curlingMotion, curlingVFX, curlingParticles, curlingAudio, curlingCollision)
    
    print("Specialized snake spells queued for generation")
end

-- Main execution function
local function run_snake_generation_example()
    print("Starting Snake Spell Generation Example...")
    
    -- Initialize the system
    initialize_snake_system()
    
    -- Create various types of snake spells
    create_basic_snakes()
    create_custom_snakes()
    create_elemental_variations()
    create_advanced_snakes()
    create_snake_size_variations()
    create_performance_test_snakes()
    create_specialized_snakes()
    
    print("\n=== Snake Generation Complete ===")
    print("All snake spells have been queued for generation.")
    print("Use poll_assets() to check for completed assets.")
end

-- Export the main function
return {
    run_example = run_snake_generation_example,
    create_basic_snakes = create_basic_snakes,
    create_custom_snakes = create_custom_snakes,
    create_elemental_variations = create_elemental_variations,
    create_advanced_snakes = create_advanced_snakes,
    create_snake_size_variations = create_snake_size_variations,
    create_performance_test_snakes = create_performance_test_snakes,
    create_specialized_snakes = create_specialized_snakes
} 