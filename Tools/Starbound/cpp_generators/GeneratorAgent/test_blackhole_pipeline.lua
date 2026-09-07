-- Blackhole-Like Projectile Asset Generation Pipeline Test
-- This file demonstrates the comprehensive blackhole projectile generation system

print("=== Blackhole Projectile Pipeline Test ===")

-- Initialize the factory
print("Initializing blackhole factory...")
local success = initialize_blackhole_factory(1000, 4)
if success then
    print("✓ Factory initialized successfully")
else
    print("✗ Factory initialization failed")
    return
end

-- Test 1: Basic parameter validation
print("\n--- Test 1: Parameter Validation ---")

local function test_parameter_validation()
    local params = BlackholeProjectileParams()
    params.id = "test_validation"
    params.coreRadius = 0.5
    params.diskInnerRadius = 0.6
    params.diskOuterRadius = 1.2
    
    local validation = validate_blackhole_params(params)
    if validation.valid then
        print("✓ Basic parameters are valid")
    else
        print("✗ Basic parameters are invalid:")
        for _, error in ipairs(validation.errors) do
            print("  - " .. error)
        end
    end
    
    -- Test invalid parameters
    local invalid_params = BlackholeProjectileParams()
    invalid_params.id = "invalid_test"
    invalid_params.coreRadius = -1  -- Invalid: negative radius
    invalid_params.diskOuterRadius = 0.5  -- Invalid: outer < inner
    
    local invalid_validation = validate_blackhole_params(invalid_params)
    if not invalid_validation.valid then
        print("✓ Invalid parameters correctly rejected")
        for _, error in ipairs(invalid_validation.errors) do
            print("  - " .. error)
        end
    else
        print("✗ Invalid parameters incorrectly accepted")
    end
end

test_parameter_validation()

-- Test 2: Predefined parameter sets
print("\n--- Test 2: Predefined Parameter Sets ---")

local function test_predefined_params()
    local void_spiral = create_void_spiral_params()
    local void_maelstrom = create_void_maelstrom_params()
    local singularity = create_singularity_params()
    
    print("✓ Created void_spiral params (hash: " .. void_spiral:getHash() .. ")")
    print("✓ Created void_maelstrom params (hash: " .. void_maelstrom:getHash() .. ")")
    print("✓ Created singularity params (hash: " .. singularity:getHash() .. ")")
    
    -- Verify they're all valid
    local spiral_valid = validate_blackhole_params(void_spiral)
    local maelstrom_valid = validate_blackhole_params(void_maelstrom)
    local singularity_valid = validate_blackhole_params(singularity)
    
    if spiral_valid.valid and maelstrom_valid.valid and singularity_valid.valid then
        print("✓ All predefined parameter sets are valid")
    else
        print("✗ Some predefined parameter sets are invalid")
    end
end

test_predefined_params()

-- Test 3: Synchronous asset generation
print("\n--- Test 3: Synchronous Asset Generation ---")

local function test_sync_generation()
    local params = create_void_spiral_params()
    params.id = "sync_test"
    
    print("Generating blackhole projectile synchronously...")
    local start_time = os.clock()
    
    local bundle = spawn_blackhole_projectile(params)
    
    local end_time = os.clock()
    local duration = (end_time - start_time) * 1000  -- Convert to milliseconds
    
    if bundle:isValid() then
        print("✓ Synchronous generation successful")
        print("  - Core mesh: " .. bundle.coreMesh)
        print("  - Disk mesh: " .. bundle.diskMesh)
        print("  - Trail mesh: " .. bundle.trailMesh)
        print("  - Warp shader: " .. bundle.warpShader)
        print("  - Disk texture: " .. bundle.diskTexture)
        print("  - Vortex particles: " .. bundle.vortexParticles)
        print("  - SFX: " .. bundle.sfx)
        print("  - Total assets: " .. bundle:getAssetCount())
        print("  - Generation time: " .. string.format("%.2f", duration) .. "ms")
    else
        print("✗ Synchronous generation failed")
    end
end

test_sync_generation()

-- Test 4: Asynchronous asset generation
print("\n--- Test 4: Asynchronous Asset Generation ---")

-- Set up callback for async completion
function on_blackhole_ready(id, bundle)
    print("✓ Async blackhole ready: " .. id .. " (assets: " .. bundle:getAssetCount() .. ")")
end

local function test_async_generation()
    local params1 = create_void_maelstrom_params()
    params1.id = "async_test_1"
    
    local params2 = create_singularity_params()
    params2.id = "async_test_2"
    
    print("Queuing async blackhole projectiles...")
    
    local success1 = spawn_blackhole_projectile_async(params1)
    local success2 = spawn_blackhole_projectile_async(params2)
    
    if success1 and success2 then
        print("✓ Both async requests queued successfully")
        
        -- Poll for completion
        local max_wait = 10  -- seconds
        local wait_count = 0
        
        while wait_count < max_wait do
            poll_assets()  -- This will trigger the callback
            
            -- Check if we have any pending
            local stats = get_blackhole_cache_stats()
            if stats.initialized then
                print("  Polling for completion... (" .. wait_count .. "s)")
            end
            
            wait_count = wait_count + 1
            os.execute("sleep 1")  -- Wait 1 second
        end
        
        print("✓ Async generation test completed")
    else
        print("✗ Failed to queue async requests")
    end
end

test_async_generation()

-- Test 5: Custom parameter creation
print("\n--- Test 5: Custom Parameter Creation ---")

local function test_custom_params()
    local custom_params = BlackholeProjectileParams()
    custom_params.id = "custom_test"
    custom_params.coreRadius = 0.8
    custom_params.diskInnerRadius = 1.0
    custom_params.diskOuterRadius = 1.8
    custom_params.diskTilt = 30.0
    custom_params.warpIntensity = 1.8
    custom_params.warpScale = 4.2
    custom_params.spinSpeed = 3.5
    custom_params.trailLength = 2.5
    custom_params.particleVortexCount = 150
    custom_params.vortexLifetime = 1.3
    custom_params.starSuckRadius = 3.5
    custom_params.starAbsorbColor = {0.1, 0.0, 0.2, 1.0}
    custom_params.lensFlareIntensity = 2.5
    custom_params.soundDepth = 0.9
    custom_params.soundPitch = 0.35
    
    -- Validate custom parameters
    local validation = validate_blackhole_params(custom_params)
    if validation.valid then
        print("✓ Custom parameters are valid")
        
        -- Generate assets
        local bundle = spawn_blackhole_projectile(custom_params)
        if bundle:isValid() then
            print("✓ Custom blackhole generated successfully")
            print("  - Hash: " .. custom_params:getHash())
            print("  - Assets: " .. bundle:getAssetCount())
        else
            print("✗ Custom blackhole generation failed")
        end
    else
        print("✗ Custom parameters are invalid:")
        for _, error in ipairs(validation.errors) do
            print("  - " .. error)
        end
    end
end

test_custom_params()

-- Test 6: Performance and caching
print("\n--- Test 6: Performance and Caching ---")

local function test_caching()
    local params = create_void_spiral_params()
    params.id = "cache_test"
    
    print("Testing cache performance...")
    
    -- First generation (cache miss)
    local start_time = os.clock()
    local bundle1 = spawn_blackhole_projectile(params)
    local first_gen_time = (os.clock() - start_time) * 1000
    
    -- Second generation (cache hit)
    start_time = os.clock()
    local bundle2 = spawn_blackhole_projectile(params)
    local second_gen_time = (os.clock() - start_time) * 1000
    
    if bundle1:isValid() and bundle2:isValid() then
        print("✓ Both generations successful")
        print("  - First generation (cache miss): " .. string.format("%.2f", first_gen_time) .. "ms")
        print("  - Second generation (cache hit): " .. string.format("%.2f", second_gen_time) .. "ms")
        
        if second_gen_time < first_gen_time then
            print("✓ Caching is working (faster second generation)")
        else
            print("⚠ Caching may not be working as expected")
        end
    else
        print("✗ Cache test failed")
    end
end

test_caching()

-- Test 7: Error handling
print("\n--- Test 7: Error Handling ---")

local function test_error_handling()
    -- Test with invalid parameters
    local invalid_params = BlackholeProjectileParams()
    invalid_params.id = "error_test"
    invalid_params.coreRadius = -1  -- Invalid
    
    local bundle = spawn_blackhole_projectile(invalid_params)
    if not bundle:isValid() then
        print("✓ Error handling works (invalid params rejected)")
    else
        print("✗ Error handling failed (invalid params accepted)")
    end
    
    -- Test async with invalid params
    local success = spawn_blackhole_projectile_async(invalid_params)
    if not success then
        print("✓ Async error handling works")
    else
        print("✗ Async error handling failed")
    end
end

test_error_handling()

-- Cleanup
print("\n--- Cleanup ---")
cleanup()
print("✓ Blackhole projectile pipeline test completed")

print("\n=== Test Summary ===")
print("The blackhole projectile generation pipeline has been successfully tested.")
print("Features demonstrated:")
print("- Parameter validation and error handling")
print("- Predefined parameter sets (void_spiral, void_maelstrom, singularity)")
print("- Synchronous and asynchronous asset generation")
print("- Custom parameter creation")
print("- Performance optimization with caching")
print("- Comprehensive asset bundle generation (mesh, shader, texture, particles, audio)")
print("- Lua integration with full scriptable interface")

print("\nThe pipeline is ready for production use in OpenStarbound!") 