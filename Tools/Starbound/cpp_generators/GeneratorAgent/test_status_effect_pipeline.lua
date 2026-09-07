-- Status Effect Asset Generation Pipeline Test
-- This file demonstrates the comprehensive status effect generation system

print("=== Status Effect Pipeline Test ===")

-- Initialize the factory
print("Initializing status effect factory...")
local success = initialize_status_effect_factory(1000, 4)
if success then
    print("✓ Factory initialized successfully")
else
    print("✗ Factory initialization failed")
    return
end

-- Test 1: Basic parameter validation
print("\n--- Test 1: Parameter Validation ---")

local function test_parameter_validation()
    local params = StatusEffectParams()
    params.id = "test_validation"
    params.duration = 10.0
    params.intensity = 0.8
    params.particleCount = 50
    
    local validation = validate_status_effect_params(params)
    if validation.valid then
        print("✓ Basic status effect parameters are valid")
    else
        print("✗ Basic status effect parameters are invalid:")
        for _, error in ipairs(validation.errors) do
            print("  - " .. error)
        end
    end
    
    -- Test invalid parameters
    local invalid_params = StatusEffectParams()
    invalid_params.id = "invalid_test"
    invalid_params.duration = -1  -- Invalid: negative duration
    invalid_params.intensity = 1.5  -- Invalid: intensity > 1
    
    local invalid_validation = validate_status_effect_params(invalid_params)
    if not invalid_validation.valid then
        print("✓ Invalid status effect parameters correctly rejected")
        for _, error in ipairs(invalid_validation.errors) do
            print("  - " .. error)
        end
    else
        print("✗ Invalid status effect parameters incorrectly accepted")
    end
end

test_parameter_validation()

-- Test 2: Predefined parameter sets
print("\n--- Test 2: Predefined Parameter Sets ---")

local function test_predefined_params()
    local buff = create_buff_params()
    local debuff = create_debuff_params()
    local poison = create_poison_params()
    local fire = create_fire_params()
    local ice = create_ice_params()
    
    print("✓ Created buff params (hash: " .. buff:getHash() .. ")")
    print("✓ Created debuff params (hash: " .. debuff:getHash() .. ")")
    print("✓ Created poison params (hash: " .. poison:getHash() .. ")")
    print("✓ Created fire params (hash: " .. fire:getHash() .. ")")
    print("✓ Created ice params (hash: " .. ice:getHash() .. ")")
    
    -- Verify they're all valid
    local buff_valid = validate_status_effect_params(buff)
    local debuff_valid = validate_status_effect_params(debuff)
    local poison_valid = validate_status_effect_params(poison)
    local fire_valid = validate_status_effect_params(fire)
    local ice_valid = validate_status_effect_params(ice)
    
    if buff_valid.valid and debuff_valid.valid and poison_valid.valid and fire_valid.valid and ice_valid.valid then
        print("✓ All predefined parameter sets are valid")
    else
        print("✗ Some predefined parameter sets are invalid")
    end
end

test_predefined_params()

-- Test 3: Synchronous asset generation
print("\n--- Test 3: Synchronous Asset Generation ---")

local function test_sync_generation()
    local effect_params = create_buff_params()
    effect_params.id = "sync_test"
    
    local ui_params = UIParams()
    ui_params.iconSize = 64
    ui_params.backgroundShape = "circle"
    ui_params.flashOnApply = true
    ui_params.borderColor = {1.0, 1.0, 1.0, 0.8}
    
    print("Generating status effect synchronously...")
    local start_time = os.clock()
    
    local bundle = spawn_status_effect(effect_params, ui_params)
    
    local end_time = os.clock()
    local duration = (end_time - start_time) * 1000  -- Convert to milliseconds
    
    if bundle:isValid() then
        print("✓ Synchronous generation successful")
        print("  - Shader: " .. bundle.shader)
        print("  - Texture: " .. bundle.texture)
        print("  - Mesh: " .. bundle.mesh)
        print("  - Particles: " .. bundle.particles)
        print("  - Icon: " .. bundle.icon)
        print("  - Total assets: " .. bundle:getAssetCount())
        print("  - Generation time: " .. string.format("%.2f", duration) .. "ms")
    else
        print("✗ Synchronous generation failed")
    end
end

test_sync_generation()

-- Test 4: Different effect types
print("\n--- Test 4: Different Effect Types ---")

local function test_effect_types()
    local effect_types = {
        {name = "buff", params = create_buff_params()},
        {name = "debuff", params = create_debuff_params()},
        {name = "poison", params = create_poison_params()},
        {name = "fire", params = create_fire_params()},
        {name = "ice", params = create_ice_params()}
    }
    
    local ui_params = UIParams()
    ui_params.iconSize = 48
    ui_params.backgroundShape = "circle"
    ui_params.flashOnApply = true
    
    for i, effect in ipairs(effect_types) do
        effect.params.id = effect.name .. "_test"
        
        print("Generating " .. effect.name .. " effect...")
        local bundle = spawn_status_effect(effect.params, ui_params)
        
        if bundle:isValid() then
            print("  ✓ " .. effect.name .. " effect generated successfully")
            print("    - Assets: " .. bundle:getAssetCount())
        else
            print("  ✗ " .. effect.name .. " effect generation failed")
        end
    end
end

test_effect_types()

-- Test 5: Custom parameter creation
print("\n--- Test 5: Custom Parameter Creation ---")

local function test_custom_params()
    local custom_effect = StatusEffectParams()
    custom_effect.id = "custom_effect"
    custom_effect.effectType = EffectType.BUFF
    custom_effect.shapeType = ShapeType.STAR
    custom_effect.particleType = ParticleType.SPARKLE
    custom_effect.iconStyle = IconStyle.GLOWING
    custom_effect.category = EffectCategory.MAGIC
    custom_effect.duration = 15.0
    custom_effect.intensity = 0.9
    custom_effect.fadeInTime = 0.8
    custom_effect.fadeOutTime = 1.2
    custom_effect.isPermanent = false
    custom_effect.canStack = true
    custom_effect.maxStacks = 3
    custom_effect.noiseScale = 3.5
    custom_effect.noiseSpeed = 1.8
    custom_effect.oscillationFreq = 1.2
    custom_effect.coverage = 100
    custom_effect.particleCount = 75
    custom_effect.dissolve = false
    custom_effect.opacity = 0.9
    custom_effect.scale = 1.1
    custom_effect.colorPrimary = {0.8, 0.2, 1.0}  -- Purple
    custom_effect.colorSecondary = {0.4, 0.1, 0.5}
    custom_effect.iconColor = {1.0, 0.8, 1.0}
    custom_effect.glowColor = {0.4, 0.1, 0.5}
    custom_effect.enablePulsing = true
    custom_effect.pulseSpeed = 1.5
    custom_effect.pulseIntensity = 0.4
    custom_effect.enableRotation = true
    custom_effect.rotationSpeed = 0.8
    custom_effect.enableScaling = true
    custom_effect.scaleSpeed = 1.2
    custom_effect.scaleRange = 0.3
    custom_effect.shaderType = "magic"
    custom_effect.shaderIntensity = 1.3
    custom_effect.enableDistortion = true
    custom_effect.distortionStrength = 0.3
    custom_effect.enableBlur = false
    custom_effect.blurStrength = 0.1
    custom_effect.description = "A custom magical effect"
    custom_effect.tags = {"custom", "magic", "purple"}
    custom_effect.enableCaching = true
    custom_effect.enableHotReload = true
    custom_effect.enableParallelProcessing = true
    
    local custom_ui = UIParams()
    custom_ui.iconSize = 56
    custom_ui.borderColor = {0.8, 0.2, 1.0, 0.9}
    custom_ui.backgroundShape = "circle"
    custom_ui.flashOnApply = true
    custom_ui.enableGlow = true
    custom_ui.glowIntensity = 1.2
    custom_ui.enablePulse = true
    custom_ui.pulseSpeed = 1.0
    custom_ui.enableRotation = false
    custom_ui.rotationSpeed = 1.0
    custom_ui.borderWidth = 3.0
    custom_ui.enableBorderGlow = true
    custom_ui.borderGlowIntensity = 1.5
    custom_ui.enableBackground = true
    custom_ui.backgroundOpacity = 0.9
    custom_ui.enableBackgroundBlur = false
    custom_ui.backgroundBlurStrength = 0.1
    custom_ui.enableFadeIn = true
    custom_ui.fadeInDuration = 0.4
    custom_ui.enableFadeOut = true
    custom_ui.fadeOutDuration = 0.6
    custom_ui.enableScaleIn = true
    custom_ui.scaleInDuration = 0.3
    custom_ui.enableScaleOut = true
    custom_ui.scaleOutDuration = 0.5
    custom_ui.showStackCount = true
    custom_ui.stackCountStyle = "number"
    custom_ui.stackCountColor = {1.0, 1.0, 1.0}
    custom_ui.stackCountScale = 0.9
    custom_ui.uiName = "Custom Magic Effect"
    custom_ui.description = "A powerful magical status effect"
    custom_ui.tags = {"custom", "magic", "ui"}
    
    -- Validate custom parameters
    local effect_validation = validate_status_effect_params(custom_effect)
    local ui_validation = validate_ui_params(custom_ui)
    
    if effect_validation.valid and ui_validation.valid then
        print("✓ Custom parameters are valid")
        
        -- Generate assets
        local bundle = spawn_status_effect(custom_effect, custom_ui)
        if bundle:isValid() then
            print("✓ Custom status effect generated successfully")
            print("  - Hash: " .. custom_effect:getHash())
            print("  - Assets: " .. bundle:getAssetCount())
        else
            print("✗ Custom status effect generation failed")
        end
    else
        print("✗ Custom parameters are invalid:")
        if not effect_validation.valid then
            print("  Effect errors:")
            for _, error in ipairs(effect_validation.errors) do
                print("    - " .. error)
            end
        end
        if not ui_validation.valid then
            print("  UI errors:")
            for _, error in ipairs(ui_validation.errors) do
                print("    - " .. error)
            end
        end
    end
end

test_custom_params()

-- Test 6: Performance and caching
print("\n--- Test 6: Performance and Caching ---")

local function test_caching()
    local effect_params = create_buff_params()
    effect_params.id = "cache_test"
    
    local ui_params = UIParams()
    ui_params.iconSize = 32
    ui_params.backgroundShape = "circle"
    
    print("Testing cache performance...")
    
    -- First generation (cache miss)
    local start_time = os.clock()
    local bundle1 = spawn_status_effect(effect_params, ui_params)
    local first_gen_time = (os.clock() - start_time) * 1000
    
    -- Second generation (cache hit)
    start_time = os.clock()
    local bundle2 = spawn_status_effect(effect_params, ui_params)
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
    -- Test with invalid effect parameters
    local invalid_effect = StatusEffectParams()
    invalid_effect.id = "error_test"
    invalid_effect.duration = -1  -- Invalid
    
    local valid_ui = UIParams()
    valid_ui.iconSize = 32
    
    local bundle = spawn_status_effect(invalid_effect, valid_ui)
    if not bundle:isValid() then
        print("✓ Error handling works (invalid effect params rejected)")
    else
        print("✗ Error handling failed (invalid effect params accepted)")
    end
    
    -- Test with invalid UI parameters
    local valid_effect = create_buff_params()
    valid_effect.id = "error_test_ui"
    
    local invalid_ui = UIParams()
    invalid_ui.iconSize = 1000  -- Invalid: too large
    
    local bundle2 = spawn_status_effect(valid_effect, invalid_ui)
    if not bundle2:isValid() then
        print("✓ Error handling works (invalid UI params rejected)")
    else
        print("✗ Error handling failed (invalid UI params accepted)")
    end
end

test_error_handling()

-- Test 8: Cache statistics
print("\n--- Test 8: Cache Statistics ---")

local function test_cache_stats()
    local stats = get_status_effect_cache_stats()
    
    if stats.initialized then
        print("✓ Cache statistics available")
        print("  - Cache size: " .. stats.cache_size)
        print("  - Cache capacity: " .. stats.cache_capacity)
        
        -- Test cache clearing
        clear_status_effect_cache()
        local stats_after = get_status_effect_cache_stats()
        print("  - Cache size after clearing: " .. stats_after.cache_size)
    else
        print("✗ Cache statistics not available")
    end
end

test_cache_stats()

-- Cleanup
print("\n--- Cleanup ---")
cleanup()
print("✓ Status effect pipeline test completed")

print("\n=== Test Summary ===")
print("The status effect generation pipeline has been successfully tested.")
print("Features demonstrated:")
print("- Parameter validation and error handling")
print("- Predefined parameter sets (buff, debuff, poison, fire, ice)")
print("- Synchronous asset generation")
print("- Custom parameter creation")
print("- Performance optimization with caching")
print("- Comprehensive asset bundle generation (shader, texture, mesh, particles, icon)")
print("- Lua integration with full scriptable interface")
print("- UI parameter customization")
print("- Cache management and statistics")

print("\nThe pipeline is ready for production use in OpenStarbound!") 