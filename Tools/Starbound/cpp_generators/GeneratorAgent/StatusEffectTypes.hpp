#pragma once

#include <string>
#include <vector>
#include <array>
#include <map>
#include <cstdint>
#include <functional>
#include <glm/glm.hpp>
#include "xxhash.h"
#include "vendor/json/include/nlohmann/json.hpp"

namespace MagiTech {
namespace StatusEffects {

using ShaderHandle = uint32_t;
using TextureHandle = uint32_t;
using MeshHandle = uint32_t;
using ParticleHandle = uint32_t;

// Enums for status effect parameters
enum class EffectType {
    BUFF,
    DEBUFF,
    DOT,           // Damage over time
    HOT,           // Healing over time
    SHIELD,
    STUN,
    SLOW,
    HASTE,
    INVISIBILITY,
    POISON,
    BURN,
    FREEZE,
    SHOCK,
    CURSE,
    BLESSING,
    CUSTOM
};

enum class ShapeType {
    CIRCLE,
    SQUARE,
    HEXAGON,
    STAR,
    CROSS,
    DIAMOND,
    CUSTOM_SHAPE
};

enum class ParticleType {
    NONE,
    SPARKLE,
    SMOKE,
    FIRE,
    ICE,
    LIGHTNING,
    POISON,
    HEALING,
    SHIELD,
    CUSTOM_PARTICLE
};

enum class IconStyle {
    SIMPLE,
    DETAILED,
    ANIMATED,
    GLOWING,
    PULSING,
    CUSTOM_ICON
};

enum class EffectCategory {
    COMBAT,
    MAGIC,
    ENVIRONMENTAL,
    TEMPORARY,
    PERMANENT,
    STACKING,
    NON_STACKING
};

struct StatusEffectParams {
    std::string id = "default_effect";
    EffectType effectType = EffectType::BUFF;
    ShapeType shapeType = ShapeType::CIRCLE;
    ParticleType particleType = ParticleType::NONE;
    IconStyle iconStyle = IconStyle::SIMPLE;
    EffectCategory category = EffectCategory::COMBAT;
    
    // Timing parameters
    float duration = 10.0f;
    float intensity = 1.0f;
    float fadeInTime = 0.5f;
    float fadeOutTime = 0.5f;
    bool isPermanent = false;
    bool canStack = false;
    int maxStacks = 1;
    
    // Visual parameters
    float noiseScale = 1.0f;
    float noiseSpeed = 1.0f;
    float oscillationFreq = 1.0f;
    int coverage = 100;
    int particleCount = 50;
    bool dissolve = false;
    float opacity = 1.0f;
    float scale = 1.0f;
    
    // Color parameters
    glm::vec3 colorPrimary = {1.0f, 1.0f, 1.0f};
    glm::vec3 colorSecondary = {0.5f, 0.5f, 0.5f};
    glm::vec3 iconColor = {1.0f, 1.0f, 1.0f};
    glm::vec3 glowColor = {0.0f, 0.0f, 0.0f};
    
    // Animation parameters
    bool enablePulsing = false;
    float pulseSpeed = 1.0f;
    float pulseIntensity = 0.2f;
    bool enableRotation = false;
    float rotationSpeed = 1.0f;
    bool enableScaling = false;
    float scaleSpeed = 1.0f;
    float scaleRange = 0.2f;
    
    // Shader parameters
    std::string shaderType = "standard";
    float shaderIntensity = 1.0f;
    bool enableDistortion = false;
    float distortionStrength = 0.1f;
    bool enableBlur = false;
    float blurStrength = 0.1f;
    
    // Metadata
    std::string description;
    std::vector<std::string> tags;
    std::map<std::string, std::string> metadata;
    
    // Performance settings
    bool enableCaching = true;
    bool enableHotReload = true;
    bool enableParallelProcessing = true;

    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, id.c_str(), id.length());
        XXH64_update(&hash_state, &effectType, sizeof(effectType));
        XXH64_update(&hash_state, &shapeType, sizeof(shapeType));
        XXH64_update(&hash_state, &particleType, sizeof(particleType));
        XXH64_update(&hash_state, &iconStyle, sizeof(iconStyle));
        XXH64_update(&hash_state, &category, sizeof(category));
        XXH64_update(&hash_state, &duration, sizeof(duration));
        XXH64_update(&hash_state, &intensity, sizeof(intensity));
        XXH64_update(&hash_state, &fadeInTime, sizeof(fadeInTime));
        XXH64_update(&hash_state, &fadeOutTime, sizeof(fadeOutTime));
        XXH64_update(&hash_state, &isPermanent, sizeof(isPermanent));
        XXH64_update(&hash_state, &canStack, sizeof(canStack));
        XXH64_update(&hash_state, &maxStacks, sizeof(maxStacks));
        XXH64_update(&hash_state, &noiseScale, sizeof(noiseScale));
        XXH64_update(&hash_state, &noiseSpeed, sizeof(noiseSpeed));
        XXH64_update(&hash_state, &oscillationFreq, sizeof(oscillationFreq));
        XXH64_update(&hash_state, &coverage, sizeof(coverage));
        XXH64_update(&hash_state, &particleCount, sizeof(particleCount));
        XXH64_update(&hash_state, &dissolve, sizeof(dissolve));
        XXH64_update(&hash_state, &opacity, sizeof(opacity));
        XXH64_update(&hash_state, &scale, sizeof(scale));
        XXH64_update(&hash_state, &colorPrimary, sizeof(colorPrimary));
        XXH64_update(&hash_state, &colorSecondary, sizeof(colorSecondary));
        XXH64_update(&hash_state, &iconColor, sizeof(iconColor));
        XXH64_update(&hash_state, &glowColor, sizeof(glowColor));
        XXH64_update(&hash_state, &enablePulsing, sizeof(enablePulsing));
        XXH64_update(&hash_state, &pulseSpeed, sizeof(pulseSpeed));
        XXH64_update(&hash_state, &pulseIntensity, sizeof(pulseIntensity));
        XXH64_update(&hash_state, &enableRotation, sizeof(enableRotation));
        XXH64_update(&hash_state, &rotationSpeed, sizeof(rotationSpeed));
        XXH64_update(&hash_state, &enableScaling, sizeof(enableScaling));
        XXH64_update(&hash_state, &scaleSpeed, sizeof(scaleSpeed));
        XXH64_update(&hash_state, &scaleRange, sizeof(scaleRange));
        return XXH64_digest(&hash_state);
    }
};

struct UIParams {
    int iconSize = 32;
    glm::vec4 borderColor = {1.0f, 1.0f, 1.0f, 1.0f};
    std::string backgroundShape = "circle";
    bool flashOnApply = true;
    
    // Additional UI parameters
    bool enableGlow = false;
    float glowIntensity = 1.0f;
    bool enablePulse = false;
    float pulseSpeed = 1.0f;
    bool enableRotation = false;
    float rotationSpeed = 1.0f;
    
    // Border parameters
    float borderWidth = 2.0f;
    bool enableBorderGlow = false;
    float borderGlowIntensity = 1.0f;
    
    // Background parameters
    bool enableBackground = true;
    float backgroundOpacity = 0.8f;
    bool enableBackgroundBlur = false;
    float backgroundBlurStrength = 0.1f;
    
    // Animation parameters
    bool enableFadeIn = true;
    float fadeInDuration = 0.3f;
    bool enableFadeOut = true;
    float fadeOutDuration = 0.3f;
    bool enableScaleIn = true;
    float scaleInDuration = 0.2f;
    bool enableScaleOut = true;
    float scaleOutDuration = 0.2f;
    
    // Stacking parameters
    bool showStackCount = true;
    std::string stackCountStyle = "number";
    glm::vec3 stackCountColor = {1.0f, 1.0f, 1.0f};
    float stackCountScale = 0.8f;
    
    // Metadata
    std::string uiName;
    std::string description;
    std::vector<std::string> tags;
    std::map<std::string, std::string> metadata;

    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, &iconSize, sizeof(iconSize));
        XXH64_update(&hash_state, &borderColor, sizeof(borderColor));
        XXH64_update(&hash_state, backgroundShape.c_str(), backgroundShape.length());
        XXH64_update(&hash_state, &flashOnApply, sizeof(flashOnApply));
        XXH64_update(&hash_state, &enableGlow, sizeof(enableGlow));
        XXH64_update(&hash_state, &glowIntensity, sizeof(glowIntensity));
        XXH64_update(&hash_state, &enablePulse, sizeof(enablePulse));
        XXH64_update(&hash_state, &pulseSpeed, sizeof(pulseSpeed));
        XXH64_update(&hash_state, &enableRotation, sizeof(enableRotation));
        XXH64_update(&hash_state, &rotationSpeed, sizeof(rotationSpeed));
        XXH64_update(&hash_state, &borderWidth, sizeof(borderWidth));
        XXH64_update(&hash_state, &enableBorderGlow, sizeof(enableBorderGlow));
        XXH64_update(&hash_state, &borderGlowIntensity, sizeof(borderGlowIntensity));
        XXH64_update(&hash_state, &enableBackground, sizeof(enableBackground));
        XXH64_update(&hash_state, &backgroundOpacity, sizeof(backgroundOpacity));
        XXH64_update(&hash_state, &enableBackgroundBlur, sizeof(enableBackgroundBlur));
        XXH64_update(&hash_state, &backgroundBlurStrength, sizeof(backgroundBlurStrength));
        XXH64_update(&hash_state, &enableFadeIn, sizeof(enableFadeIn));
        XXH64_update(&hash_state, &fadeInDuration, sizeof(fadeInDuration));
        XXH64_update(&hash_state, &enableFadeOut, sizeof(enableFadeOut));
        XXH64_update(&hash_state, &fadeOutDuration, sizeof(fadeOutDuration));
        XXH64_update(&hash_state, &enableScaleIn, sizeof(enableScaleIn));
        XXH64_update(&hash_state, &scaleInDuration, sizeof(scaleInDuration));
        XXH64_update(&hash_state, &enableScaleOut, sizeof(enableScaleOut));
        XXH64_update(&hash_state, &scaleOutDuration, sizeof(scaleOutDuration));
        XXH64_update(&hash_state, &showStackCount, sizeof(showStackCount));
        XXH64_update(&hash_state, stackCountStyle.c_str(), stackCountStyle.length());
        XXH64_update(&hash_state, &stackCountColor, sizeof(stackCountColor));
        XXH64_update(&hash_state, &stackCountScale, sizeof(stackCountScale));
        return XXH64_digest(&hash_state);
    }
};

struct EffectBundle {
    ShaderHandle   shader;
    TextureHandle  texture;
    MeshHandle     mesh;
    ParticleHandle particles;
    TextureHandle  icon;
};

// Utility functions for parameter conversion
namespace ParamUtils {
    // Convert string to enum
    EffectType parseEffectType(const std::string& str);
    ShapeType parseShapeType(const std::string& str);
    ParticleType parseParticleType(const std::string& str);
    IconStyle parseIconStyle(const std::string& str);
    EffectCategory parseEffectCategory(const std::string& str);
    
    // Convert enum to string
    std::string effectTypeToString(EffectType type);
    std::string shapeTypeToString(ShapeType type);
    std::string particleTypeToString(ParticleType type);
    std::string iconStyleToString(IconStyle style);
    std::string effectCategoryToString(EffectCategory category);
    
    // JSON serialization
    nlohmann::json toJson(const StatusEffectParams& params);
    StatusEffectParams fromJson(const nlohmann::json& json);
    
    nlohmann::json toJson(const UIParams& params);
    UIParams fromJson(const nlohmann::json& json);
}

} // namespace StatusEffects
} // namespace MagiTech
