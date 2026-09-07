#pragma once
#include <string>
#include <vector>
#include <map>
#include <array>
#include <cstdint>
#include <functional>
#include <glm/glm.hpp>
#include "vendor/xxhash/xxhash.h"
#include "vendor/json/include/nlohmann/json.hpp"

namespace MagiTech {
namespace FlameProjectiles {

using MeshHandle = uint32_t;
using ShaderHandle = uint32_t;
using TextureHandle = uint32_t;
using ParticleHandle = uint32_t;

// Enum for flame types
enum class FlameType {
    FIREBALL,
    INFERNO_BOLT,
    HELLFIRE,
    PLASMA_FLAME,
    MAGIC_FIRE,
    CUSTOM
};

// Enum for flame shapes
enum class FlameShape {
    CONE,
    RIBBON,
    SPHERE,
    CYLINDER,
    CUSTOM_SHAPE
};

// Enum for blend modes
enum class BlendMode {
    ADDITIVE,
    MULTIPLY,
    SCREEN,
    OVERLAY,
    NORMAL
};

// Enum for noise types
enum class NoiseType {
    PERLIN,
    SIMPLEX,
    CURL,
    FRACTAL,
    CUSTOM
};

// Enum for trail types
enum class TrailType {
    NONE,
    RIBBON,
    PARTICLES,
    SMOKE,
    HEAT_DISTORTION,
    CUSTOM
};

struct FlameProjectileParams {
    // Basic properties
    std::string id;
    FlameType flameType;
    FlameShape flameShape;
    BlendMode blendMode;
    NoiseType noiseType;
    TrailType trailType;
    
    // Physical properties
    float speed;
    float length;
    float width;
    float flameHeight;
    float flameWidthVariation;
    
    // Color properties
    glm::vec3 coreColor;
    glm::vec3 outerColor;
    glm::vec3 glowColor;
    glm::vec4 emberColor;
    
    // Animation properties
    float flickerIntensity;
    float flickerSpeed;
    float turbulenceStrength;
    float turbulenceScale;
    float oscillationFreq;
    float oscillationAmplitude;
    
    // Trail properties
    float trailLength;
    float trailWidth;
    float trailOpacity;
    bool enableTrailFade;
    float trailFadeSpeed;
    
    // Particle properties
    int emberCount;
    float emberLifetime;
    float emberSize;
    float emberSpeed;
    bool enableEmberFade;
    float emberFadeSpeed;
    
    // Shader properties
    std::string shaderType;
    float shaderIntensity;
    bool enableDistortion;
    float distortionStrength;
    bool enableBlur;
    float blurStrength;
    bool enableHeatDistortion;
    float heatDistortionStrength;
    
    // Physics properties
    bool enablePhysics;
    float physicsMass;
    float physicsDrag;
    float physicsLift;
    bool enableCollision;
    float collisionRadius;
    
    // Performance properties
    bool enableCaching;
    bool enableHotReload;
    bool enableParallelProcessing;
    int lodLevel;
    
    // Metadata
    std::string description;
    std::vector<std::string> tags;
    std::map<std::string, std::string> metadata;

    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, id.c_str(), id.length());
        XXH64_update(&hash_state, &flameType, sizeof(flameType));
        XXH64_update(&hash_state, &flameShape, sizeof(flameShape));
        XXH64_update(&hash_state, &blendMode, sizeof(blendMode));
        XXH64_update(&hash_state, &noiseType, sizeof(noiseType));
        XXH64_update(&hash_state, &trailType, sizeof(trailType));
        XXH64_update(&hash_state, &speed, sizeof(speed));
        XXH64_update(&hash_state, &length, sizeof(length));
        XXH64_update(&hash_state, &width, sizeof(width));
        XXH64_update(&hash_state, &flameHeight, sizeof(flameHeight));
        XXH64_update(&hash_state, &flameWidthVariation, sizeof(flameWidthVariation));
        XXH64_update(&hash_state, &coreColor.x, sizeof(float) * 3);
        XXH64_update(&hash_state, &outerColor.x, sizeof(float) * 3);
        XXH64_update(&hash_state, &glowColor.x, sizeof(float) * 3);
        XXH64_update(&hash_state, &emberColor.x, sizeof(float) * 4);
        XXH64_update(&hash_state, &flickerIntensity, sizeof(flickerIntensity));
        XXH64_update(&hash_state, &flickerSpeed, sizeof(flickerSpeed));
        XXH64_update(&hash_state, &turbulenceStrength, sizeof(turbulenceStrength));
        XXH64_update(&hash_state, &turbulenceScale, sizeof(turbulenceScale));
        XXH64_update(&hash_state, &oscillationFreq, sizeof(oscillationFreq));
        XXH64_update(&hash_state, &oscillationAmplitude, sizeof(oscillationAmplitude));
        XXH64_update(&hash_state, &trailLength, sizeof(trailLength));
        XXH64_update(&hash_state, &trailWidth, sizeof(trailWidth));
        XXH64_update(&hash_state, &trailOpacity, sizeof(trailOpacity));
        XXH64_update(&hash_state, &enableTrailFade, sizeof(enableTrailFade));
        XXH64_update(&hash_state, &trailFadeSpeed, sizeof(trailFadeSpeed));
        XXH64_update(&hash_state, &emberCount, sizeof(emberCount));
        XXH64_update(&hash_state, &emberLifetime, sizeof(emberLifetime));
        XXH64_update(&hash_state, &emberSize, sizeof(emberSize));
        XXH64_update(&hash_state, &emberSpeed, sizeof(emberSpeed));
        XXH64_update(&hash_state, &enableEmberFade, sizeof(enableEmberFade));
        XXH64_update(&hash_state, &emberFadeSpeed, sizeof(emberFadeSpeed));
        XXH64_update(&hash_state, shaderType.c_str(), shaderType.length());
        XXH64_update(&hash_state, &shaderIntensity, sizeof(shaderIntensity));
        XXH64_update(&hash_state, &enableDistortion, sizeof(enableDistortion));
        XXH64_update(&hash_state, &distortionStrength, sizeof(distortionStrength));
        XXH64_update(&hash_state, &enableBlur, sizeof(enableBlur));
        XXH64_update(&hash_state, &blurStrength, sizeof(blurStrength));
        XXH64_update(&hash_state, &enableHeatDistortion, sizeof(enableHeatDistortion));
        XXH64_update(&hash_state, &heatDistortionStrength, sizeof(heatDistortionStrength));
        XXH64_update(&hash_state, &enablePhysics, sizeof(enablePhysics));
        XXH64_update(&hash_state, &physicsMass, sizeof(physicsMass));
        XXH64_update(&hash_state, &physicsDrag, sizeof(physicsDrag));
        XXH64_update(&hash_state, &physicsLift, sizeof(physicsLift));
        XXH64_update(&hash_state, &enableCollision, sizeof(enableCollision));
        XXH64_update(&hash_state, &collisionRadius, sizeof(collisionRadius));
        XXH64_update(&hash_state, &enableCaching, sizeof(enableCaching));
        XXH64_update(&hash_state, &enableHotReload, sizeof(enableHotReload));
        XXH64_update(&hash_state, &enableParallelProcessing, sizeof(enableParallelProcessing));
        XXH64_update(&hash_state, &lodLevel, sizeof(lodLevel));
        return XXH64_digest(&hash_state);
    }
};

struct FlameAssetBundle {
    MeshHandle mesh;
    ShaderHandle shader;
    TextureHandle texture;
    ParticleHandle embers;
    ParticleHandle trail;
    ParticleHandle smoke;
    ShaderHandle heatDistortion;
    
    // Performance metrics
    float generationTime;
    size_t vertexCount;
    size_t triangleCount;
    size_t particleCount;
    bool gpuAccelerated;
};

// Utility namespace for parameter conversion and JSON serialization
namespace ParamUtils {
    // String to enum conversions
    FlameType parseFlameType(const std::string& str);
    FlameShape parseFlameShape(const std::string& str);
    BlendMode parseBlendMode(const std::string& str);
    NoiseType parseNoiseType(const std::string& str);
    TrailType parseTrailType(const std::string& str);
    
    // Enum to string conversions
    std::string flameTypeToString(FlameType type);
    std::string flameShapeToString(FlameShape shape);
    std::string blendModeToString(BlendMode mode);
    std::string noiseTypeToString(NoiseType type);
    std::string trailTypeToString(TrailType type);
    
    // JSON serialization/deserialization
    nlohmann::json toJson(const FlameProjectileParams& params);
    FlameProjectileParams fromJson(const nlohmann::json& json);
}

} // namespace FlameProjectiles
} // namespace MagiTech
