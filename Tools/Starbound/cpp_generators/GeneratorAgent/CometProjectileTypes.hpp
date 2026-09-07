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
namespace CometProjectiles {

using MeshHandle = uint32_t;
using ShaderHandle = uint32_t;
using TextureHandle = uint32_t;
using ParticleHandle = uint32_t;

// Enum for comet types
enum class CometType {
    METEOR,
    COMET,
    ASTEROID,
    FALLING_STAR,
    CELESTIAL_ROCK,
    CUSTOM
};

// Enum for comet shapes
enum class CometShape {
    SPHERE,
    IRREGULAR,
    FRAGMENTED,
    CRYSTALLINE,
    CUSTOM_SHAPE
};

// Enum for trail types
enum class TrailType {
    NONE,
    DUST,
    FIRE,
    SMOKE,
    SPARKS,
    CUSTOM
};

// Enum for fragmentation types
enum class FragmentationType {
    NONE,
    EXPLOSIVE,
    SHATTER,
    DISINTEGRATE,
    CUSTOM
};

// Enum for noise types
enum class NoiseType {
    PERLIN,
    SIMPLEX,
    CURL,
    FRACTAL,
    CUSTOM
};

// Enum for blend modes
enum class BlendMode {
    ADDITIVE,
    MULTIPLY,
    SCREEN,
    OVERLAY,
    NORMAL
};

struct CometProjectileParams {
    // Basic properties
    std::string id;
    CometType cometType;
    CometShape cometShape;
    TrailType trailType;
    FragmentationType fragmentationType;
    NoiseType noiseType;
    BlendMode blendMode;
    
    // Physical properties
    float coreRadius;
    float irregularity;
    float speed;
    float gravityInfluence;
    float mass;
    float drag;
    float lift;
    
    // Color properties
    glm::vec3 heatColor;
    glm::vec3 burnColor;
    glm::vec3 coreColor;
    glm::vec3 glowColor;
    glm::vec4 dustColor;
    glm::vec4 sparkColor;
    
    // Visual properties
    float glowIntensity;
    float emissivePower;
    float coreOpacity;
    float trailOpacity;
    bool enableCoreGlow;
    bool enableTrailGlow;
    
    // Trail properties
    float trailLength;
    float trailWidth;
    float trailNoiseScale;
    float trailNoiseSpeed;
    float trailFadeSpeed;
    bool enableTrailFade;
    bool enableTrailDistortion;
    float trailDistortionStrength;
    
    // Particle properties
    int dustParticleCount;
    float dustLifetime;
    float dustSize;
    float dustSpeed;
    bool enableDustFade;
    float dustFadeSpeed;
    
    int sparkParticleCount;
    float sparkLifetime;
    float sparkSize;
    float sparkSpeed;
    bool enableSparkFade;
    float sparkFadeSpeed;
    
    // Fragmentation properties
    int fragmentationCount;
    float fragmentSizeFactor;
    float fragmentSpread;
    float fragmentVelocity;
    bool enableFragmentPhysics;
    float fragmentLifetime;
    
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
    bool enableCollision;
    float collisionRadius;
    bool enableGravity;
    bool enableAirResistance;
    float airResistanceFactor;
    
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
        XXH64_update(&hash_state, &cometType, sizeof(cometType));
        XXH64_update(&hash_state, &cometShape, sizeof(cometShape));
        XXH64_update(&hash_state, &trailType, sizeof(trailType));
        XXH64_update(&hash_state, &fragmentationType, sizeof(fragmentationType));
        XXH64_update(&hash_state, &noiseType, sizeof(noiseType));
        XXH64_update(&hash_state, &blendMode, sizeof(blendMode));
        XXH64_update(&hash_state, &coreRadius, sizeof(coreRadius));
        XXH64_update(&hash_state, &irregularity, sizeof(irregularity));
        XXH64_update(&hash_state, &speed, sizeof(speed));
        XXH64_update(&hash_state, &gravityInfluence, sizeof(gravityInfluence));
        XXH64_update(&hash_state, &mass, sizeof(mass));
        XXH64_update(&hash_state, &drag, sizeof(drag));
        XXH64_update(&hash_state, &lift, sizeof(lift));
        XXH64_update(&hash_state, &heatColor.x, sizeof(float) * 3);
        XXH64_update(&hash_state, &burnColor.x, sizeof(float) * 3);
        XXH64_update(&hash_state, &coreColor.x, sizeof(float) * 3);
        XXH64_update(&hash_state, &glowColor.x, sizeof(float) * 3);
        XXH64_update(&hash_state, &dustColor.x, sizeof(float) * 4);
        XXH64_update(&hash_state, &sparkColor.x, sizeof(float) * 4);
        XXH64_update(&hash_state, &glowIntensity, sizeof(glowIntensity));
        XXH64_update(&hash_state, &emissivePower, sizeof(emissivePower));
        XXH64_update(&hash_state, &coreOpacity, sizeof(coreOpacity));
        XXH64_update(&hash_state, &trailOpacity, sizeof(trailOpacity));
        XXH64_update(&hash_state, &enableCoreGlow, sizeof(enableCoreGlow));
        XXH64_update(&hash_state, &enableTrailGlow, sizeof(enableTrailGlow));
        XXH64_update(&hash_state, &trailLength, sizeof(trailLength));
        XXH64_update(&hash_state, &trailWidth, sizeof(trailWidth));
        XXH64_update(&hash_state, &trailNoiseScale, sizeof(trailNoiseScale));
        XXH64_update(&hash_state, &trailNoiseSpeed, sizeof(trailNoiseSpeed));
        XXH64_update(&hash_state, &trailFadeSpeed, sizeof(trailFadeSpeed));
        XXH64_update(&hash_state, &enableTrailFade, sizeof(enableTrailFade));
        XXH64_update(&hash_state, &enableTrailDistortion, sizeof(enableTrailDistortion));
        XXH64_update(&hash_state, &trailDistortionStrength, sizeof(trailDistortionStrength));
        XXH64_update(&hash_state, &dustParticleCount, sizeof(dustParticleCount));
        XXH64_update(&hash_state, &dustLifetime, sizeof(dustLifetime));
        XXH64_update(&hash_state, &dustSize, sizeof(dustSize));
        XXH64_update(&hash_state, &dustSpeed, sizeof(dustSpeed));
        XXH64_update(&hash_state, &enableDustFade, sizeof(enableDustFade));
        XXH64_update(&hash_state, &dustFadeSpeed, sizeof(dustFadeSpeed));
        XXH64_update(&hash_state, &sparkParticleCount, sizeof(sparkParticleCount));
        XXH64_update(&hash_state, &sparkLifetime, sizeof(sparkLifetime));
        XXH64_update(&hash_state, &sparkSize, sizeof(sparkSize));
        XXH64_update(&hash_state, &sparkSpeed, sizeof(sparkSpeed));
        XXH64_update(&hash_state, &enableSparkFade, sizeof(enableSparkFade));
        XXH64_update(&hash_state, &sparkFadeSpeed, sizeof(sparkFadeSpeed));
        XXH64_update(&hash_state, &fragmentationCount, sizeof(fragmentationCount));
        XXH64_update(&hash_state, &fragmentSizeFactor, sizeof(fragmentSizeFactor));
        XXH64_update(&hash_state, &fragmentSpread, sizeof(fragmentSpread));
        XXH64_update(&hash_state, &fragmentVelocity, sizeof(fragmentVelocity));
        XXH64_update(&hash_state, &enableFragmentPhysics, sizeof(enableFragmentPhysics));
        XXH64_update(&hash_state, &fragmentLifetime, sizeof(fragmentLifetime));
        XXH64_update(&hash_state, shaderType.c_str(), shaderType.length());
        XXH64_update(&hash_state, &shaderIntensity, sizeof(shaderIntensity));
        XXH64_update(&hash_state, &enableDistortion, sizeof(enableDistortion));
        XXH64_update(&hash_state, &distortionStrength, sizeof(distortionStrength));
        XXH64_update(&hash_state, &enableBlur, sizeof(enableBlur));
        XXH64_update(&hash_state, &blurStrength, sizeof(blurStrength));
        XXH64_update(&hash_state, &enableHeatDistortion, sizeof(enableHeatDistortion));
        XXH64_update(&hash_state, &heatDistortionStrength, sizeof(heatDistortionStrength));
        XXH64_update(&hash_state, &enablePhysics, sizeof(enablePhysics));
        XXH64_update(&hash_state, &enableCollision, sizeof(enableCollision));
        XXH64_update(&hash_state, &collisionRadius, sizeof(collisionRadius));
        XXH64_update(&hash_state, &enableGravity, sizeof(enableGravity));
        XXH64_update(&hash_state, &enableAirResistance, sizeof(enableAirResistance));
        XXH64_update(&hash_state, &airResistanceFactor, sizeof(airResistanceFactor));
        XXH64_update(&hash_state, &enableCaching, sizeof(enableCaching));
        XXH64_update(&hash_state, &enableHotReload, sizeof(enableHotReload));
        XXH64_update(&hash_state, &enableParallelProcessing, sizeof(enableParallelProcessing));
        XXH64_update(&hash_state, &lodLevel, sizeof(lodLevel));
        return XXH64_digest(&hash_state);
    }
};

struct CometAssetBundle {
    MeshHandle mesh;
    ShaderHandle shader;
    TextureHandle texture;
    ParticleHandle dustTrail;
    ParticleHandle sparks;
    ParticleHandle fragments;
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
    CometType parseCometType(const std::string& str);
    CometShape parseCometShape(const std::string& str);
    TrailType parseTrailType(const std::string& str);
    FragmentationType parseFragmentationType(const std::string& str);
    NoiseType parseNoiseType(const std::string& str);
    BlendMode parseBlendMode(const std::string& str);
    
    // Enum to string conversions
    std::string cometTypeToString(CometType type);
    std::string cometShapeToString(CometShape shape);
    std::string trailTypeToString(TrailType type);
    std::string fragmentationTypeToString(FragmentationType type);
    std::string noiseTypeToString(NoiseType type);
    std::string blendModeToString(BlendMode mode);
    
    // JSON serialization/deserialization
    nlohmann::json toJson(const CometProjectileParams& params);
    CometProjectileParams fromJson(const nlohmann::json& json);
}

} // namespace CometProjectiles
} // namespace MagiTech
