#include "StatusEffectLuaBindings.hpp"
#include "StatusEffectFactory.hpp"
#include "StatusEffectParams.hpp"
#include "core/Log.hpp"
#include <vector>
#include <memory>

namespace MagiTech {
namespace StatusEffects {

static std::unique_ptr<StatusEffectFactory> g_factory;

// Initialize the factory if not already done
static StatusEffectFactory* getFactory() {
    if (!g_factory) {
        g_factory = std::make_unique<StatusEffectFactory>();
        g_factory->initialize(1000, 4); // 1000 cache entries, 4 threads
        Log::info("StatusEffectFactory initialized");
    }
    return g_factory.get();
}

void StatusEffectLuaBindings::bind(sol::state& lua) {
    // Bind the StatusEffectParams struct with all properties
    lua.new_usertype<StatusEffectParams>("StatusEffectParams",
        sol::constructors<StatusEffectParams()>(),
        "id", &StatusEffectParams::id,
        "effectType", &StatusEffectParams::effectType,
        "shapeType", &StatusEffectParams::shapeType,
        "particleType", &StatusEffectParams::particleType,
        "iconStyle", &StatusEffectParams::iconStyle,
        "category", &StatusEffectParams::category,
        "duration", &StatusEffectParams::duration,
        "intensity", &StatusEffectParams::intensity,
        "fadeInTime", &StatusEffectParams::fadeInTime,
        "fadeOutTime", &StatusEffectParams::fadeOutTime,
        "isPermanent", &StatusEffectParams::isPermanent,
        "canStack", &StatusEffectParams::canStack,
        "maxStacks", &StatusEffectParams::maxStacks,
        "noiseScale", &StatusEffectParams::noiseScale,
        "noiseSpeed", &StatusEffectParams::noiseSpeed,
        "oscillationFreq", &StatusEffectParams::oscillationFreq,
        "coverage", &StatusEffectParams::coverage,
        "particleCount", &StatusEffectParams::particleCount,
        "dissolve", &StatusEffectParams::dissolve,
        "opacity", &StatusEffectParams::opacity,
        "scale", &StatusEffectParams::scale,
        "colorPrimary", &StatusEffectParams::colorPrimary,
        "colorSecondary", &StatusEffectParams::colorSecondary,
        "iconColor", &StatusEffectParams::iconColor,
        "glowColor", &StatusEffectParams::glowColor,
        "enablePulsing", &StatusEffectParams::enablePulsing,
        "pulseSpeed", &StatusEffectParams::pulseSpeed,
        "pulseIntensity", &StatusEffectParams::pulseIntensity,
        "enableRotation", &StatusEffectParams::enableRotation,
        "rotationSpeed", &StatusEffectParams::rotationSpeed,
        "enableScaling", &StatusEffectParams::enableScaling,
        "scaleSpeed", &StatusEffectParams::scaleSpeed,
        "scaleRange", &StatusEffectParams::scaleRange,
        "shaderType", &StatusEffectParams::shaderType,
        "shaderIntensity", &StatusEffectParams::shaderIntensity,
        "enableDistortion", &StatusEffectParams::enableDistortion,
        "distortionStrength", &StatusEffectParams::distortionStrength,
        "enableBlur", &StatusEffectParams::enableBlur,
        "blurStrength", &StatusEffectParams::blurStrength,
        "description", &StatusEffectParams::description,
        "tags", &StatusEffectParams::tags,
        "metadata", &StatusEffectParams::metadata,
        "enableCaching", &StatusEffectParams::enableCaching,
        "enableHotReload", &StatusEffectParams::enableHotReload,
        "enableParallelProcessing", &StatusEffectParams::enableParallelProcessing,
        // Add utility methods
        "validate", [](const StatusEffectParams& p) -> bool {
            return p.duration > 0 && p.intensity >= 0 && p.intensity <= 1;
        },
        "getHash", [](const StatusEffectParams& p) -> uint64_t {
            return p.hashKey();
        }
    );

    // Bind the UIParams struct
    lua.new_usertype<UIParams>("UIParams",
        sol::constructors<UIParams()>(),
        "iconSize", &UIParams::iconSize,
        "borderColor", &UIParams::borderColor,
        "backgroundShape", &UIParams::backgroundShape,
        "flashOnApply", &UIParams::flashOnApply,
        "enableGlow", &UIParams::enableGlow,
        "glowIntensity", &UIParams::glowIntensity,
        "enablePulse", &UIParams::enablePulse,
        "pulseSpeed", &UIParams::pulseSpeed,
        "enableRotation", &UIParams::enableRotation,
        "rotationSpeed", &UIParams::rotationSpeed,
        "borderWidth", &UIParams::borderWidth,
        "enableBorderGlow", &UIParams::enableBorderGlow,
        "borderGlowIntensity", &UIParams::borderGlowIntensity,
        "enableBackground", &UIParams::enableBackground,
        "backgroundOpacity", &UIParams::backgroundOpacity,
        "enableBackgroundBlur", &UIParams::enableBackgroundBlur,
        "backgroundBlurStrength", &UIParams::backgroundBlurStrength,
        "enableFadeIn", &UIParams::enableFadeIn,
        "fadeInDuration", &UIParams::fadeInDuration,
        "enableFadeOut", &UIParams::enableFadeOut,
        "fadeOutDuration", &UIParams::fadeOutDuration,
        "enableScaleIn", &UIParams::enableScaleIn,
        "scaleInDuration", &UIParams::scaleInDuration,
        "enableScaleOut", &UIParams::enableScaleOut,
        "scaleOutDuration", &UIParams::scaleOutDuration,
        "showStackCount", &UIParams::showStackCount,
        "stackCountStyle", &UIParams::stackCountStyle,
        "stackCountColor", &UIParams::stackCountColor,
        "stackCountScale", &UIParams::stackCountScale,
        "uiName", &UIParams::uiName,
        "description", &UIParams::description,
        "tags", &UIParams::tags,
        "metadata", &UIParams::metadata,
        // Add utility methods
        "validate", [](const UIParams& p) -> bool {
            return p.iconSize > 0 && p.iconSize <= 512;
        },
        "getHash", [](const UIParams& p) -> uint64_t {
            return p.hashKey();
        }
    );

    // Bind the EffectBundle struct
    lua.new_usertype<EffectBundle>("EffectBundle",
        sol::no_constructor,
        "shader", &EffectBundle::shader,
        "texture", &EffectBundle::texture,
        "mesh", &EffectBundle::mesh,
        "particles", &EffectBundle::particles,
        "icon", &EffectBundle::icon,
        // Add utility methods
        "isValid", [](const EffectBundle& b) -> bool {
            return b.shader != 0 && b.texture != 0 && b.mesh != 0;
        },
        "getAssetCount", [](const EffectBundle& b) -> int {
            int count = 0;
            if (b.shader) count++;
            if (b.texture) count++;
            if (b.mesh) count++;
            if (b.particles) count++;
            if (b.icon) count++;
            return count;
        }
    );

    // Main generation function
    lua.set_function("spawn_status_effect",
        [&](const StatusEffectParams& s, const UIParams& u) -> EffectBundle {
            try {
                auto factory = getFactory();
                
                // Validate parameters
                if (!s.validate()) {
                    Log::error("Invalid status effect parameters for: {}", s.id);
                    return EffectBundle{}; // Return empty bundle
                }
                
                if (!u.validate()) {
                    Log::error("Invalid UI parameters for effect: {}", s.id);
                    return EffectBundle{}; // Return empty bundle
                }
                
                Log::info("Generating status effect: {}", s.id);
                auto bundle = factory->generateSync(s, u);
                
                Log::info("Status effect generated successfully: {} ({} assets)", 
                         s.id, bundle.getAssetCount());
                return bundle;
            } catch (const std::exception& e) {
                Log::error("Error generating status effect {}: {}", s.id, e.what());
                return EffectBundle{}; // Return empty bundle on error
            }
        }
    );

    // Async generation function
    lua.set_function("spawn_status_effect_async",
        [&](const StatusEffectParams& s, const UIParams& u) -> bool {
            try {
                auto factory = getFactory();
                
                if (!s.validate()) {
                    Log::error("Invalid status effect parameters for: {}", s.id);
                    return false;
                }
                
                if (!u.validate()) {
                    Log::error("Invalid UI parameters for effect: {}", s.id);
                    return false;
                }
                
                auto fut = factory->generateAsync(s, u);
                // Store future for later retrieval
                Log::info("Queued async status effect generation: {}", s.id);
                return true;
            } catch (const std::exception& e) {
                Log::error("Error queuing status effect {}: {}", s.id, e.what());
                return false;
            }
        }
    );

    // Utility functions for parameter creation
    lua.set_function("create_buff_params", []() -> StatusEffectParams {
        StatusEffectParams p;
        p.id = "buff_effect";
        p.effectType = EffectType::BUFF;
        p.shapeType = ShapeType::CIRCLE;
        p.particleType = ParticleType::SPARKLE;
        p.iconStyle = IconStyle::GLOWING;
        p.category = EffectCategory::COMBAT;
        p.duration = 10.0f;
        p.intensity = 1.0f;
        p.fadeInTime = 0.5f;
        p.fadeOutTime = 0.5f;
        p.isPermanent = false;
        p.canStack = true;
        p.maxStacks = 5;
        p.noiseScale = 1.0f;
        p.noiseSpeed = 1.0f;
        p.oscillationFreq = 1.0f;
        p.coverage = 100;
        p.particleCount = 50;
        p.dissolve = false;
        p.opacity = 1.0f;
        p.scale = 1.0f;
        p.colorPrimary = {0.0f, 1.0f, 0.0f};
        p.colorSecondary = {0.0f, 0.5f, 0.0f};
        p.iconColor = {1.0f, 1.0f, 1.0f};
        p.glowColor = {0.0f, 0.5f, 0.0f};
        p.enablePulsing = true;
        p.pulseSpeed = 1.0f;
        p.pulseIntensity = 0.2f;
        p.enableRotation = false;
        p.rotationSpeed = 1.0f;
        p.enableScaling = false;
        p.scaleSpeed = 1.0f;
        p.scaleRange = 0.2f;
        p.shaderType = "standard";
        p.shaderIntensity = 1.0f;
        p.enableDistortion = false;
        p.distortionStrength = 0.1f;
        p.enableBlur = false;
        p.blurStrength = 0.1f;
        p.description = "A beneficial status effect";
        p.tags = {"buff", "positive", "combat"};
        p.enableCaching = true;
        p.enableHotReload = true;
        p.enableParallelProcessing = true;
        return p;
    });

    lua.set_function("create_debuff_params", []() -> StatusEffectParams {
        StatusEffectParams p;
        p.id = "debuff_effect";
        p.effectType = EffectType::DEBUFF;
        p.shapeType = ShapeType::CIRCLE;
        p.particleType = ParticleType::SMOKE;
        p.iconStyle = IconStyle::PULSING;
        p.category = EffectCategory::COMBAT;
        p.duration = 8.0f;
        p.intensity = 0.8f;
        p.fadeInTime = 0.3f;
        p.fadeOutTime = 0.7f;
        p.isPermanent = false;
        p.canStack = true;
        p.maxStacks = 3;
        p.noiseScale = 2.0f;
        p.noiseSpeed = 1.5f;
        p.oscillationFreq = 0.8f;
        p.coverage = 100;
        p.particleCount = 30;
        p.dissolve = true;
        p.opacity = 0.8f;
        p.scale = 0.9f;
        p.colorPrimary = {1.0f, 0.0f, 0.0f};
        p.colorSecondary = {0.5f, 0.0f, 0.0f};
        p.iconColor = {1.0f, 0.5f, 0.5f};
        p.glowColor = {0.5f, 0.0f, 0.0f};
        p.enablePulsing = true;
        p.pulseSpeed = 1.2f;
        p.pulseIntensity = 0.3f;
        p.enableRotation = false;
        p.rotationSpeed = 1.0f;
        p.enableScaling = false;
        p.scaleSpeed = 1.0f;
        p.scaleRange = 0.2f;
        p.shaderType = "standard";
        p.shaderIntensity = 0.8f;
        p.enableDistortion = true;
        p.distortionStrength = 0.2f;
        p.enableBlur = false;
        p.blurStrength = 0.1f;
        p.description = "A harmful status effect";
        p.tags = {"debuff", "negative", "combat"};
        p.enableCaching = true;
        p.enableHotReload = true;
        p.enableParallelProcessing = true;
        return p;
    });

    lua.set_function("create_poison_params", []() -> StatusEffectParams {
        StatusEffectParams p;
        p.id = "poison_effect";
        p.effectType = EffectType::POISON;
        p.shapeType = ShapeType::CIRCLE;
        p.particleType = ParticleType::POISON;
        p.iconStyle = IconStyle::PULSING;
        p.category = EffectCategory::COMBAT;
        p.duration = 15.0f;
        p.intensity = 0.7f;
        p.fadeInTime = 0.5f;
        p.fadeOutTime = 1.0f;
        p.isPermanent = false;
        p.canStack = true;
        p.maxStacks = 5;
        p.noiseScale = 3.0f;
        p.noiseSpeed = 0.8f;
        p.oscillationFreq = 0.5f;
        p.coverage = 100;
        p.particleCount = 40;
        p.dissolve = true;
        p.opacity = 0.7f;
        p.scale = 0.8f;
        p.colorPrimary = {0.2f, 1.0f, 0.2f};
        p.colorSecondary = {0.1f, 0.3f, 0.0f};
        p.iconColor = {0.5f, 1.0f, 0.5f};
        p.glowColor = {0.1f, 0.3f, 0.0f};
        p.enablePulsing = true;
        p.pulseSpeed = 0.8f;
        p.pulseIntensity = 0.4f;
        p.enableRotation = false;
        p.rotationSpeed = 1.0f;
        p.enableScaling = false;
        p.scaleSpeed = 1.0f;
        p.scaleRange = 0.2f;
        p.shaderType = "standard";
        p.shaderIntensity = 0.7f;
        p.enableDistortion = true;
        p.distortionStrength = 0.3f;
        p.enableBlur = true;
        p.blurStrength = 0.2f;
        p.description = "A toxic status effect";
        p.tags = {"poison", "dot", "combat"};
        p.enableCaching = true;
        p.enableHotReload = true;
        p.enableParallelProcessing = true;
        return p;
    });

    lua.set_function("create_fire_params", []() -> StatusEffectParams {
        StatusEffectParams p;
        p.id = "fire_effect";
        p.effectType = EffectType::BURN;
        p.shapeType = ShapeType::CIRCLE;
        p.particleType = ParticleType::FIRE;
        p.iconStyle = IconStyle::ANIMATED;
        p.category = EffectCategory::COMBAT;
        p.duration = 12.0f;
        p.intensity = 0.9f;
        p.fadeInTime = 0.3f;
        p.fadeOutTime = 0.8f;
        p.isPermanent = false;
        p.canStack = true;
        p.maxStacks = 3;
        p.noiseScale = 4.0f;
        p.noiseSpeed = 2.0f;
        p.oscillationFreq = 1.5f;
        p.coverage = 100;
        p.particleCount = 60;
        p.dissolve = true;
        p.opacity = 0.9f;
        p.scale = 1.1f;
        p.colorPrimary = {1.0f, 0.5f, 0.0f};
        p.colorSecondary = {0.5f, 0.2f, 0.0f};
        p.iconColor = {1.0f, 0.8f, 0.5f};
        p.glowColor = {0.5f, 0.2f, 0.0f};
        p.enablePulsing = true;
        p.pulseSpeed = 1.5f;
        p.pulseIntensity = 0.5f;
        p.enableRotation = false;
        p.rotationSpeed = 1.0f;
        p.enableScaling = true;
        p.scaleSpeed = 1.2f;
        p.scaleRange = 0.3f;
        p.shaderType = "fire";
        p.shaderIntensity = 1.2f;
        p.enableDistortion = true;
        p.distortionStrength = 0.4f;
        p.enableBlur = false;
        p.blurStrength = 0.1f;
        p.description = "A burning status effect";
        p.tags = {"fire", "burn", "dot", "combat"};
        p.enableCaching = true;
        p.enableHotReload = true;
        p.enableParallelProcessing = true;
        return p;
    });

    lua.set_function("create_ice_params", []() -> StatusEffectParams {
        StatusEffectParams p;
        p.id = "ice_effect";
        p.effectType = EffectType::FREEZE;
        p.shapeType = ShapeType::HEXAGON;
        p.particleType = ParticleType::ICE;
        p.iconStyle = IconStyle::GLOWING;
        p.category = EffectCategory::COMBAT;
        p.duration = 8.0f;
        p.intensity = 0.8f;
        p.fadeInTime = 0.7f;
        p.fadeOutTime = 1.2f;
        p.isPermanent = false;
        p.canStack = true;
        p.maxStacks = 3;
        p.noiseScale = 2.5f;
        p.noiseSpeed = 0.5f;
        p.oscillationFreq = 0.3f;
        p.coverage = 100;
        p.particleCount = 25;
        p.dissolve = true;
        p.opacity = 0.8f;
        p.scale = 0.9f;
        p.colorPrimary = {0.5f, 0.8f, 1.0f};
        p.colorSecondary = {0.2f, 0.4f, 0.6f};
        p.iconColor = {0.8f, 0.9f, 1.0f};
        p.glowColor = {0.2f, 0.4f, 0.6f};
        p.enablePulsing = true;
        p.pulseSpeed = 0.6f;
        p.pulseIntensity = 0.3f;
        p.enableRotation = true;
        p.rotationSpeed = 0.5f;
        p.enableScaling = false;
        p.scaleSpeed = 1.0f;
        p.scaleRange = 0.2f;
        p.shaderType = "ice";
        p.shaderIntensity = 0.9f;
        p.enableDistortion = true;
        p.distortionStrength = 0.2f;
        p.enableBlur = true;
        p.blurStrength = 0.3f;
        p.description = "A freezing status effect";
        p.tags = {"ice", "freeze", "slow", "combat"};
        p.enableCaching = true;
        p.enableHotReload = true;
        p.enableParallelProcessing = true;
        return p;
    });

    // Parameter validation and utility functions
    lua.set_function("validate_status_effect_params", [](const StatusEffectParams& p) -> sol::table {
        sol::table result = lua.create_table();
        
        bool isValid = true;
        std::vector<std::string> errors;
        
        if (p.duration <= 0) {
            errors.push_back("Duration must be positive");
            isValid = false;
        }
        
        if (p.intensity < 0 || p.intensity > 1) {
            errors.push_back("Intensity must be between 0 and 1");
            isValid = false;
        }
        
        if (p.fadeInTime < 0) {
            errors.push_back("Fade in time must be non-negative");
            isValid = false;
        }
        
        if (p.fadeOutTime < 0) {
            errors.push_back("Fade out time must be non-negative");
            isValid = false;
        }
        
        if (p.maxStacks <= 0) {
            errors.push_back("Max stacks must be positive");
            isValid = false;
        }
        
        if (p.noiseScale <= 0) {
            errors.push_back("Noise scale must be positive");
            isValid = false;
        }
        
        if (p.noiseSpeed < 0) {
            errors.push_back("Noise speed must be non-negative");
            isValid = false;
        }
        
        if (p.oscillationFreq < 0) {
            errors.push_back("Oscillation frequency must be non-negative");
            isValid = false;
        }
        
        if (p.coverage <= 0) {
            errors.push_back("Coverage must be positive");
            isValid = false;
        }
        
        if (p.particleCount < 0) {
            errors.push_back("Particle count must be non-negative");
            isValid = false;
        }
        
        if (p.opacity < 0 || p.opacity > 1) {
            errors.push_back("Opacity must be between 0 and 1");
            isValid = false;
        }
        
        if (p.scale <= 0) {
            errors.push_back("Scale must be positive");
            isValid = false;
        }
        
        result["valid"] = isValid;
        result["errors"] = errors;
        
        return result;
    });

    lua.set_function("validate_ui_params", [](const UIParams& p) -> sol::table {
        sol::table result = lua.create_table();
        
        bool isValid = true;
        std::vector<std::string> errors;
        
        if (p.iconSize <= 0 || p.iconSize > 512) {
            errors.push_back("Icon size must be between 1 and 512");
            isValid = false;
        }
        
        if (p.glowIntensity < 0) {
            errors.push_back("Glow intensity must be non-negative");
            isValid = false;
        }
        
        if (p.pulseSpeed < 0) {
            errors.push_back("Pulse speed must be non-negative");
            isValid = false;
        }
        
        if (p.rotationSpeed < 0) {
            errors.push_back("Rotation speed must be non-negative");
            isValid = false;
        }
        
        if (p.borderWidth < 0) {
            errors.push_back("Border width must be non-negative");
            isValid = false;
        }
        
        if (p.borderGlowIntensity < 0) {
            errors.push_back("Border glow intensity must be non-negative");
            isValid = false;
        }
        
        if (p.backgroundOpacity < 0 || p.backgroundOpacity > 1) {
            errors.push_back("Background opacity must be between 0 and 1");
            isValid = false;
        }
        
        if (p.backgroundBlurStrength < 0) {
            errors.push_back("Background blur strength must be non-negative");
            isValid = false;
        }
        
        if (p.fadeInDuration < 0) {
            errors.push_back("Fade in duration must be non-negative");
            isValid = false;
        }
        
        if (p.fadeOutDuration < 0) {
            errors.push_back("Fade out duration must be non-negative");
            isValid = false;
        }
        
        if (p.scaleInDuration < 0) {
            errors.push_back("Scale in duration must be non-negative");
            isValid = false;
        }
        
        if (p.scaleOutDuration < 0) {
            errors.push_back("Scale out duration must be non-negative");
            isValid = false;
        }
        
        if (p.stackCountScale <= 0) {
            errors.push_back("Stack count scale must be positive");
            isValid = false;
        }
        
        result["valid"] = isValid;
        result["errors"] = errors;
        
        return result;
    });

    // Factory management functions
    lua.set_function("initialize_status_effect_factory", [](size_t cache_size, size_t num_threads) -> bool {
        try {
            if (!g_factory) {
                g_factory = std::make_unique<StatusEffectFactory>();
            }
            g_factory->initialize(cache_size, num_threads);
            Log::info("StatusEffectFactory initialized with cache_size={}, threads={}", 
                     cache_size, num_threads);
            return true;
        } catch (const std::exception& e) {
            Log::error("Error initializing StatusEffectFactory: {}", e.what());
            return false;
        }
    });

    lua.set_function("shutdown_status_effect_factory", []() {
        if (g_factory) {
            g_factory->shutdown();
            Log::info("StatusEffectFactory shutdown");
        }
    });

    // Cache management
    lua.set_function("get_status_effect_cache_stats", []() -> sol::table {
        sol::table stats = lua.create_table();
        if (g_factory) {
            stats["initialized"] = true;
            stats["cache_size"] = g_factory->getCacheSize();
            stats["cache_capacity"] = g_factory->getCacheCapacity();
        } else {
            stats["initialized"] = false;
        }
        return stats;
    });

    lua.set_function("clear_status_effect_cache", []() {
        if (g_factory) {
            g_factory->clearCache();
        }
    });

    Log::info("StatusEffectLuaBindings bound successfully");
}

void StatusEffectLuaBindings::cleanup() {
    if (g_factory) {
        g_factory->shutdown();
        g_factory.reset();
    }
    Log::info("StatusEffectLuaBindings cleaned up");
}

} // namespace StatusEffects
} // namespace MagiTech
