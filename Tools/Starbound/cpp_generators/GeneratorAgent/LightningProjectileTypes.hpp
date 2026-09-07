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
namespace LightningProjectiles {

using MeshHandle = uint32_t;
using ShaderHandle = uint32_t;
using TextureHandle = uint32_t;
using ParticleHandle = uint32_t;
using AudioHandle = uint32_t;

// Enum for lightning types
enum class LightningType {
    BOLT,
    ARC,
    CHAIN,
    FORK,
    STORM,
    PLASMA,
    MAGIC,
    CUSTOM
};

// Enum for trail types
enum class TrailType {
    NONE,
    ELECTRIC_TAIL,
    PLASMA_STREAK,
    MAGIC_TRAIL,
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

// Enum for audio types
enum class AudioType {
    CRACKLE,
    ZAP,
    THUNDER,
    ELECTRIC,
    CUSTOM
};

struct LightningProjectileParams {
    // Basic properties
    std::string id;
    LightningType lightningType;
    TrailType trailType;
    NoiseType noiseType;
    BlendMode blendMode;
    AudioType audioType;
    
    // Physical properties
    float length;
    float thickness;
    float speed;
    float mass;
    float charge;
    float conductivity;
    
    // Color properties
    glm::vec3 mainColor;
    glm::vec3 glowColor;
    glm::vec3 coreColor;
    glm::vec3 sparkColor;
    glm::vec4 trailColor;
    
    // Visual properties
    float noiseIntensity;
    float noiseScale;
    float flickerSpeed;
    float pulseFrequency;
    float glowIntensity;
    float emissivePower;
    float coreOpacity;
    float trailOpacity;
    bool enableCoreGlow;
    bool enableTrailGlow;
    
    // Branch properties
    int branchCount;
    float branchLengthFactor;
    float branchSpread;
    float branchAngle;
    bool enableBranching;
    bool enableBranchPhysics;
    
    // Jitter properties
    float jitterAmplitude;
    float jitterFrequency;
    float jitterPhase;
    bool enableJitter;
    bool enableRandomJitter;
    
    // Arc properties
    float arcWidthVariation;
    float arcSegments;
    float arcSmoothness;
    bool enableArcPhysics;
    float arcStiffness;
    
    // Trail properties
    float trailLength;
    float trailWidth;
    float trailFadeSpeed;
    bool enableTrailFade;
    bool enableTrailDistortion;
    float trailDistortionStrength;
    
    // Particle properties
    int sparkCount;
    float sparkLifetime;
    float sparkSize;
    float sparkSpeed;
    bool enableSparkFade;
    float sparkFadeSpeed;
    bool enableSparkPhysics;
    float sparkGravity;
    
    // Audio properties
    float soundPitch;
    float soundVolume;
    float soundDuration;
    bool enableAudio;
    bool enableSpatialAudio;
    float audioDistance;
    
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
        XXH64_update(&hash_state, &lightningType, sizeof(lightningType));
        XXH64_update(&hash_state, &trailType, sizeof(trailType));
        XXH64_update(&hash_state, &noiseType, sizeof(noiseType));
        XXH64_update(&hash_state, &blendMode, sizeof(blendMode));
        XXH64_update(&hash_state, &audioType, sizeof(audioType));
        XXH64_update(&hash_state, &length, sizeof(length));
        XXH64_update(&hash_state, &thickness, sizeof(thickness));
        XXH64_update(&hash_state, &speed, sizeof(speed));
        XXH64_update(&hash_state, &mass, sizeof(mass));
        XXH64_update(&hash_state, &charge, sizeof(charge));
        XXH64_update(&hash_state, &conductivity, sizeof(conductivity));
        XXH64_update(&hash_state, &mainColor.x, sizeof(float) * 3);
        XXH64_update(&hash_state, &glowColor.x, sizeof(float) * 3);
        XXH64_update(&hash_state, &coreColor.x, sizeof(float) * 3);
        XXH64_update(&hash_state, &sparkColor.x, sizeof(float) * 3);
        XXH64_update(&hash_state, &trailColor.x, sizeof(float) * 4);
        XXH64_update(&hash_state, &noiseIntensity, sizeof(noiseIntensity));
        XXH64_update(&hash_state, &noiseScale, sizeof(noiseScale));
        XXH64_update(&hash_state, &flickerSpeed, sizeof(flickerSpeed));
        XXH64_update(&hash_state, &pulseFrequency, sizeof(pulseFrequency));
        XXH64_update(&hash_state, &glowIntensity, sizeof(glowIntensity));
        XXH64_update(&hash_state, &emissivePower, sizeof(emissivePower));
        XXH64_update(&hash_state, &coreOpacity, sizeof(coreOpacity));
        XXH64_update(&hash_state, &trailOpacity, sizeof(trailOpacity));
        XXH64_update(&hash_state, &enableCoreGlow, sizeof(enableCoreGlow));
        XXH64_update(&hash_state, &enableTrailGlow, sizeof(enableTrailGlow));
        XXH64_update(&hash_state, &branchCount, sizeof(branchCount));
        XXH64_update(&hash_state, &branchLengthFactor, sizeof(branchLengthFactor));
        XXH64_update(&hash_state, &branchSpread, sizeof(branchSpread));
        XXH64_update(&hash_state, &branchAngle, sizeof(branchAngle));
        XXH64_update(&hash_state, &enableBranching, sizeof(enableBranching));
        XXH64_update(&hash_state, &enableBranchPhysics, sizeof(enableBranchPhysics));
        XXH64_update(&hash_state, &jitterAmplitude, sizeof(jitterAmplitude));
        XXH64_update(&hash_state, &jitterFrequency, sizeof(jitterFrequency));
        XXH64_update(&hash_state, &jitterPhase, sizeof(jitterPhase));
        XXH64_update(&hash_state, &enableJitter, sizeof(enableJitter));
        XXH64_update(&hash_state, &enableRandomJitter, sizeof(enableRandomJitter));
        XXH64_update(&hash_state, &arcWidthVariation, sizeof(arcWidthVariation));
        XXH64_update(&hash_state, &arcSegments, sizeof(arcSegments));
        XXH64_update(&hash_state, &arcSmoothness, sizeof(arcSmoothness));
        XXH64_update(&hash_state, &enableArcPhysics, sizeof(enableArcPhysics));
        XXH64_update(&hash_state, &arcStiffness, sizeof(arcStiffness));
        XXH64_update(&hash_state, &trailLength, sizeof(trailLength));
        XXH64_update(&hash_state, &trailWidth, sizeof(trailWidth));
        XXH64_update(&hash_state, &trailFadeSpeed, sizeof(trailFadeSpeed));
        XXH64_update(&hash_state, &enableTrailFade, sizeof(enableTrailFade));
        XXH64_update(&hash_state, &enableTrailDistortion, sizeof(enableTrailDistortion));
        XXH64_update(&hash_state, &trailDistortionStrength, sizeof(trailDistortionStrength));
        XXH64_update(&hash_state, &sparkCount, sizeof(sparkCount));
        XXH64_update(&hash_state, &sparkLifetime, sizeof(sparkLifetime));
        XXH64_update(&hash_state, &sparkSize, sizeof(sparkSize));
        XXH64_update(&hash_state, &sparkSpeed, sizeof(sparkSpeed));
        XXH64_update(&hash_state, &enableSparkFade, sizeof(enableSparkFade));
        XXH64_update(&hash_state, &sparkFadeSpeed, sizeof(sparkFadeSpeed));
        XXH64_update(&hash_state, &enableSparkPhysics, sizeof(enableSparkPhysics));
        XXH64_update(&hash_state, &sparkGravity, sizeof(sparkGravity));
        XXH64_update(&hash_state, &soundPitch, sizeof(soundPitch));
        XXH64_update(&hash_state, &soundVolume, sizeof(soundVolume));
        XXH64_update(&hash_state, &soundDuration, sizeof(soundDuration));
        XXH64_update(&hash_state, &enableAudio, sizeof(enableAudio));
        XXH64_update(&hash_state, &enableSpatialAudio, sizeof(enableSpatialAudio));
        XXH64_update(&hash_state, &audioDistance, sizeof(audioDistance));
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

struct LightningBundle {
    MeshHandle mesh;
    ShaderHandle shader;
    TextureHandle texture;
    ParticleHandle sparks;
    AudioHandle sfx;
    
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
    LightningType parseLightningType(const std::string& str);
    TrailType parseTrailType(const std::string& str);
    NoiseType parseNoiseType(const std::string& str);
    BlendMode parseBlendMode(const std::string& str);
    AudioType parseAudioType(const std::string& str);
    
    // Enum to string conversions
    std::string lightningTypeToString(LightningType type);
    std::string trailTypeToString(TrailType type);
    std::string noiseTypeToString(NoiseType type);
    std::string blendModeToString(BlendMode mode);
    std::string audioTypeToString(AudioType type);
    
    // JSON serialization/deserialization
    nlohmann::json toJson(const LightningProjectileParams& params);
    LightningProjectileParams fromJson(const nlohmann::json& json);
}

} // namespace LightningProjectiles
} // namespace MagiTech
