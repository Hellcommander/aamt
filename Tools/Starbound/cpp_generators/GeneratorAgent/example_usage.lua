-- Status Effect Generation - Simple Example
-- This file shows how to use the status effect system in practice

-- Initialize the system
initialize_status_effect_factory(500, 2)

-- Example 1: Create a basic buff effect
print("Creating a basic buff effect...")
local buff_params = create_buff_params()
buff_params.id = "my_buff"

local ui_params = UIParams()
ui_params.iconSize = 48
ui_params.backgroundShape = "circle"
ui_params.flashOnApply = true

local bundle = spawn_status_effect(buff_params, ui_params)
if bundle:isValid() then
    print("✓ Buff effect created successfully!")
    print("  Shader: " .. bundle.shader)
    print("  Texture: " .. bundle.texture)
    print("  Total assets: " .. bundle:getAssetCount())
else
    print("✗ Failed to create buff effect")
end

-- Example 2: Create a powerful fire effect
print("\nCreating a powerful fire effect...")
local fire_params = create_fire_params()
fire_params.id = "my_fire"
fire_params.intensity = 1.2  -- Make it more intense
fire_params.particleCount = 100  -- More particles

local fire_ui = UIParams()
fire_ui.iconSize = 64
fire_ui.backgroundShape = "circle"
fire_ui.borderColor = {1.0, 0.5, 0.0, 0.9}
fire_ui.enableGlow = true
fire_ui.glowIntensity = 1.5

local fire_bundle = spawn_status_effect(fire_params, fire_ui)
if fire_bundle:isValid() then
    print("✓ Fire effect created successfully!")
    print("  Assets: " .. fire_bundle:getAssetCount())
else
    print("✗ Failed to create fire effect")
end

-- Example 3: Create a custom status effect
print("\nCreating a custom status effect...")
local custom_effect = StatusEffectParams()
custom_effect.id = "custom_effect"
custom_effect.effectType = EffectType.BUFF
custom_effect.shapeType = ShapeType.STAR
custom_effect.particleType = ParticleType.SPARKLE
custom_effect.iconStyle = IconStyle.GLOWING
custom_effect.category = EffectCategory.MAGIC
custom_effect.duration = 20.0
custom_effect.intensity = 0.9
custom_effect.fadeInTime = 1.0
custom_effect.fadeOutTime = 1.5
custom_effect.isPermanent = false
custom_effect.canStack = true
custom_effect.maxStacks = 3
custom_effect.noiseScale = 4.0
custom_effect.noiseSpeed = 2.0
custom_effect.oscillationFreq = 1.5
custom_effect.coverage = 100
custom_effect.particleCount = 80
custom_effect.dissolve = false
custom_effect.opacity = 0.95
custom_effect.scale = 1.2
custom_effect.colorPrimary = {0.9, 0.1, 0.9}  -- Magenta
custom_effect.colorSecondary = {0.4, 0.0, 0.4}
custom_effect.iconColor = {1.0, 0.7, 1.0}
custom_effect.glowColor = {0.4, 0.0, 0.4}
custom_effect.enablePulsing = true
custom_effect.pulseSpeed = 2.0
custom_effect.pulseIntensity = 0.5
custom_effect.enableRotation = true
custom_effect.rotationSpeed = 1.2
custom_effect.enableScaling = true
custom_effect.scaleSpeed = 1.5
custom_effect.scaleRange = 0.4
custom_effect.shaderType = "magic"
custom_effect.shaderIntensity = 1.5
custom_effect.enableDistortion = true
custom_effect.distortionStrength = 0.4
custom_effect.enableBlur = false
custom_effect.blurStrength = 0.1
custom_effect.description = "A powerful magical enhancement"
custom_effect.tags = {"custom", "magic", "enhancement"}
custom_effect.enableCaching = true
custom_effect.enableHotReload = true
custom_effect.enableParallelProcessing = true

local custom_ui = UIParams()
custom_ui.iconSize = 72
custom_ui.borderColor = {0.9, 0.1, 0.9, 1.0}
custom_ui.backgroundShape = "circle"
custom_ui.flashOnApply = true
custom_ui.enableGlow = true
custom_ui.glowIntensity = 2.0
custom_ui.enablePulse = true
custom_ui.pulseSpeed = 1.5
custom_ui.enableRotation = false
custom_ui.rotationSpeed = 1.0
custom_ui.borderWidth = 4.0
custom_ui.enableBorderGlow = true
custom_ui.borderGlowIntensity = 2.0
custom_ui.enableBackground = true
custom_ui.backgroundOpacity = 0.95
custom_ui.enableBackgroundBlur = false
custom_ui.backgroundBlurStrength = 0.1
custom_ui.enableFadeIn = true
custom_ui.fadeInDuration = 0.6
custom_ui.enableFadeOut = true
custom_ui.fadeOutDuration = 0.8
custom_ui.enableScaleIn = true
custom_ui.scaleInDuration = 0.4
custom_ui.enableScaleOut = true
custom_ui.scaleOutDuration = 0.6
custom_ui.showStackCount = true
custom_ui.stackCountStyle = "number"
custom_ui.stackCountColor = {1.0, 1.0, 1.0}
custom_ui.stackCountScale = 0.8
custom_ui.uiName = "Custom Magic Enhancement"
custom_ui.description = "A powerful magical status effect"
custom_ui.tags = {"custom", "magic", "ui"}

-- Validate before generating
local effect_validation = validate_status_effect_params(custom_effect)
local ui_validation = validate_ui_params(custom_ui)

if effect_validation.valid and ui_validation.valid then
    local custom_bundle = spawn_status_effect(custom_effect, custom_ui)
    if custom_bundle:isValid() then
        print("✓ Custom status effect created successfully!")
        print("  Hash: " .. custom_effect:getHash())
        print("  Assets: " .. custom_bundle:getAssetCount())
    else
        print("✗ Failed to create custom status effect")
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

-- Example 4: Generate multiple effects
print("\nCreating multiple status effects...")

local effects = {
    {name = "buff", params = create_buff_params()},
    {name = "debuff", params = create_debuff_params()},
    {name = "poison", params = create_poison_params()},
    {name = "fire", params = create_fire_params()},
    {name = "ice", params = create_ice_params()}
}

local standard_ui = UIParams()
standard_ui.iconSize = 32
standard_ui.backgroundShape = "circle"
standard_ui.flashOnApply = true

for i, effect in ipairs(effects) do
    effect.params.id = effect.name .. "_effect"
    
    local bundle = spawn_status_effect(effect.params, standard_ui)
    if bundle:isValid() then
        print("  ✓ " .. effect.name .. " effect created")
    else
        print("  ✗ " .. effect.name .. " effect failed")
    end
end

-- Example 5: Cache management
print("\nChecking cache statistics...")
local stats = get_status_effect_cache_stats()
if stats.initialized then
    print("  Cache size: " .. stats.cache_size)
    print("  Cache capacity: " .. stats.cache_capacity)
    
    -- Clear cache
    clear_status_effect_cache()
    local stats_after = get_status_effect_cache_stats()
    print("  Cache size after clearing: " .. stats_after.cache_size)
else
    print("  Cache not available")
end

print("\n✓ All examples completed!")
cleanup() 