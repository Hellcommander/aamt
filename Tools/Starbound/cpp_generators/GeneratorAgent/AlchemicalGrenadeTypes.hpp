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
namespace AlchemicalGrenades {

using MeshHandle = uint32_t;
using ShaderHandle = uint32_t;
using TextureHandle = uint32_t;
using ParticleHandle = uint32_t;
using AudioHandle = uint32_t;
using PhysicsHandle = uint32_t;
using IconHandle = uint32_t;

// Enum for grenade types
enum class GrenadeType {
    FIRE,
    ACID,
    SMOKE,
    FROST,
    SHOCK,
    HEALING,
    POISON,
    EXPLOSIVE,
    STUN,
    CUSTOM
};

// Enum for casing materials
enum class CasingMaterial {
    GLASS,
    METAL,
    CERAMIC,
    CRYSTAL,
    ORGANIC,
    CUSTOM
};

// Enum for particle types
enum class ParticleType {
    EMBER,
    ACID_SPLASH,
    SMOKE_PUFF,
    FROST_SPIKE,
    SPARK,
    HEALING_GLOW,
    POISON_CLOUD,
    EXPLOSION_DEBRIS,
    STUN_WAVE,
    CUSTOM
};

// Enum for background shapes
enum class BackgroundShape {
    CIRCLE,
    SQUARE,
    HEXAGON,
    DIAMOND,
    NONE,
    CUSTOM
};

// Enum for explosion types
enum class ExplosionType {
    BURST,
    IMPACT,
    TIMED,
    PROXIMITY,
    CUSTOM
};

// Enum for residue types
enum class ResidueType {
    NONE,
    LINGERING_CLOUD,
    SURFACE_DECAL,
    DRIPPING_FLUID,
    BURNING_GROUND,
    FROST_PATCH,
    CUSTOM
};

// Enum for sound effects
enum class SoundEffect {
    GRENADE_EXPLODE,
    GLASS_SHATTER,
    METAL_CRACK,
    ACID_HISS,
    FIRE_CRACKLE,
    FROST_CRYSTAL,
    SHOCK_ZAP,
    HEALING_CHIME,
    POISON_GURGLE,
    STUN_THUD,
    CUSTOM
};

// Main alchemical grenade parameters
struct AlchemicalGrenadeParams {
    // Basic properties
    std::string id;
    GrenadeType grenadeType;
    CasingMaterial casingMaterial;
    ParticleType particleType;
    ExplosionType explosionType;
    ResidueType residueType;
    SoundEffect soundEffect;
    
    // Timing properties
    float fuseTime;
    float detonationDelay;
    float residueDuration;
    float particleLifetime;
    float shardLifetime;
    
    // Physical properties
    float coreRadius;
    float casingThickness;
    float mass;
    float density;
    float bounciness;
    float friction;
    float airResistance;
    
    // Color properties
    glm::vec3 casingColorPrimary;
    glm::vec3 casingColorSecondary;
    glm::vec4 liquidColor;
    glm::vec3 glowColor;
    glm::vec3 explosionColor;
    glm::vec4 residueColor;
    
    // Visual properties
    float noiseScale;
    float noiseSpeed;
    float noiseIntensity;
    float glowIntensity;
    float emissivePower;
    float transparency;
    float refractionIndex;
    float metallicness;
    float roughness;
    
    // Explosion properties
    float explosionRadius;
    float explosionIntensity;
    float explosionForce;
    float explosionDamage;
    bool enableShockwave;
    float shockwaveRadius;
    float shockwaveForce;
    
    // Shrapnel properties
    int shrapnelCount;
    float shardSpeed;
    float shardSize;
    float shardMass;
    bool enableShrapnelPhysics;
    bool enableShrapnelDamage;
    
    // Particle properties
    int particleBurstCount;
    float particleSpeed;
    float particleSize;
    float particleSpread;
    bool enableParticlePhysics;
    bool enableParticleTrails;
    float particleGravity;
    
    // Residue properties
    float residueSpread;
    float residueIntensity;
    float residueOpacity;
    bool enableResiduePhysics;
    bool enableResidueDamage;
    float residueDamageRate;
    
    // Audio properties
    float soundVolume;
    float soundPitch;
    float soundDuration;
    bool enableSpatialAudio;
    float audioDistance;
    bool enableEcho;
    float echoDelay;
    float echoDecay;
    
    // Shader properties
    std::string shaderType;
    float shaderIntensity;
    bool enableDistortion;
    float distortionStrength;
    bool enableRefraction;
    float refractionStrength;
    bool enableReflection;
    float reflectionStrength;
    bool enableEmission;
    float emissionStrength;
    
    // Physics properties
    bool enablePhysics;
    bool enableCollision;
    float collisionRadius;
    bool enableGravity;
    bool enableAirResistance;
    float airResistanceFactor;
    bool enableBounce;
    float bounceFactor;
    
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
        XXH64_update(&hash_state, &grenadeType, sizeof(grenadeType));
        XXH64_update(&hash_state, &casingMaterial, sizeof(casingMaterial));
        XXH64_update(&hash_state, &particleType, sizeof(particleType));
        XXH64_update(&hash_state, &explosionType, sizeof(explosionType));
        XXH64_update(&hash_state, &residueType, sizeof(residueType));
        XXH64_update(&hash_state, &soundEffect, sizeof(soundEffect));
        XXH64_update(&hash_state, &fuseTime, sizeof(fuseTime));
        XXH64_update(&hash_state, &detonationDelay, sizeof(detonationDelay));
        XXH64_update(&hash_state, &residueDuration, sizeof(residueDuration));
        XXH64_update(&hash_state, &particleLifetime, sizeof(particleLifetime));
        XXH64_update(&hash_state, &shardLifetime, sizeof(shardLifetime));
        XXH64_update(&hash_state, &coreRadius, sizeof(coreRadius));
        XXH64_update(&hash_state, &casingThickness, sizeof(casingThickness));
        XXH64_update(&hash_state, &mass, sizeof(mass));
        XXH64_update(&hash_state, &density, sizeof(density));
        XXH64_update(&hash_state, &bounciness, sizeof(bounciness));
        XXH64_update(&hash_state, &friction, sizeof(friction));
        XXH64_update(&hash_state, &airResistance, sizeof(airResistance));
        XXH64_update(&hash_state, &casingColorPrimary.x, sizeof(float) * 3);
        XXH64_update(&hash_state, &casingColorSecondary.x, sizeof(float) * 3);
        XXH64_update(&hash_state, &liquidColor.x, sizeof(float) * 4);
        XXH64_update(&hash_state, &glowColor.x, sizeof(float) * 3);
        XXH64_update(&hash_state, &explosionColor.x, sizeof(float) * 3);
        XXH64_update(&hash_state, &residueColor.x, sizeof(float) * 4);
        XXH64_update(&hash_state, &noiseScale, sizeof(noiseScale));
        XXH64_update(&hash_state, &noiseSpeed, sizeof(noiseSpeed));
        XXH64_update(&hash_state, &noiseIntensity, sizeof(noiseIntensity));
        XXH64_update(&hash_state, &glowIntensity, sizeof(glowIntensity));
        XXH64_update(&hash_state, &emissivePower, sizeof(emissivePower));
        XXH64_update(&hash_state, &transparency, sizeof(transparency));
        XXH64_update(&hash_state, &refractionIndex, sizeof(refractionIndex));
        XXH64_update(&hash_state, &metallicness, sizeof(metallicness));
        XXH64_update(&hash_state, &roughness, sizeof(roughness));
        XXH64_update(&hash_state, &explosionRadius, sizeof(explosionRadius));
        XXH64_update(&hash_state, &explosionIntensity, sizeof(explosionIntensity));
        XXH64_update(&hash_state, &explosionForce, sizeof(explosionForce));
        XXH64_update(&hash_state, &explosionDamage, sizeof(explosionDamage));
        XXH64_update(&hash_state, &enableShockwave, sizeof(enableShockwave));
        XXH64_update(&hash_state, &shockwaveRadius, sizeof(shockwaveRadius));
        XXH64_update(&hash_state, &shockwaveForce, sizeof(shockwaveForce));
        XXH64_update(&hash_state, &shrapnelCount, sizeof(shrapnelCount));
        XXH64_update(&hash_state, &shardSpeed, sizeof(shardSpeed));
        XXH64_update(&hash_state, &shardSize, sizeof(shardSize));
        XXH64_update(&hash_state, &shardMass, sizeof(shardMass));
        XXH64_update(&hash_state, &enableShrapnelPhysics, sizeof(enableShrapnelPhysics));
        XXH64_update(&hash_state, &enableShrapnelDamage, sizeof(enableShrapnelDamage));
        XXH64_update(&hash_state, &particleBurstCount, sizeof(particleBurstCount));
        XXH64_update(&hash_state, &particleSpeed, sizeof(particleSpeed));
        XXH64_update(&hash_state, &particleSize, sizeof(particleSize));
        XXH64_update(&hash_state, &particleSpread, sizeof(particleSpread));
        XXH64_update(&hash_state, &enableParticlePhysics, sizeof(enableParticlePhysics));
        XXH64_update(&hash_state, &enableParticleTrails, sizeof(enableParticleTrails));
        XXH64_update(&hash_state, &particleGravity, sizeof(particleGravity));
        XXH64_update(&hash_state, &residueSpread, sizeof(residueSpread));
        XXH64_update(&hash_state, &residueIntensity, sizeof(residueIntensity));
        XXH64_update(&hash_state, &residueOpacity, sizeof(residueOpacity));
        XXH64_update(&hash_state, &enableResiduePhysics, sizeof(enableResiduePhysics));
        XXH64_update(&hash_state, &enableResidueDamage, sizeof(enableResidueDamage));
        XXH64_update(&hash_state, &residueDamageRate, sizeof(residueDamageRate));
        XXH64_update(&hash_state, &soundVolume, sizeof(soundVolume));
        XXH64_update(&hash_state, &soundPitch, sizeof(soundPitch));
        XXH64_update(&hash_state, &soundDuration, sizeof(soundDuration));
        XXH64_update(&hash_state, &enableSpatialAudio, sizeof(enableSpatialAudio));
        XXH64_update(&hash_state, &audioDistance, sizeof(audioDistance));
        XXH64_update(&hash_state, &enableEcho, sizeof(enableEcho));
        XXH64_update(&hash_state, &echoDelay, sizeof(echoDelay));
        XXH64_update(&hash_state, &echoDecay, sizeof(echoDecay));
        XXH64_update(&hash_state, shaderType.c_str(), shaderType.length());
        XXH64_update(&hash_state, &shaderIntensity, sizeof(shaderIntensity));
        XXH64_update(&hash_state, &enableDistortion, sizeof(enableDistortion));
        XXH64_update(&hash_state, &distortionStrength, sizeof(distortionStrength));
        XXH64_update(&hash_state, &enableRefraction, sizeof(enableRefraction));
        XXH64_update(&hash_state, &refractionStrength, sizeof(refractionStrength));
        XXH64_update(&hash_state, &enableReflection, sizeof(enableReflection));
        XXH64_update(&hash_state, &reflectionStrength, sizeof(reflectionStrength));
        XXH64_update(&hash_state, &enableEmission, sizeof(enableEmission));
        XXH64_update(&hash_state, &emissionStrength, sizeof(emissionStrength));
        XXH64_update(&hash_state, &enablePhysics, sizeof(enablePhysics));
        XXH64_update(&hash_state, &enableCollision, sizeof(enableCollision));
        XXH64_update(&hash_state, &collisionRadius, sizeof(collisionRadius));
        XXH64_update(&hash_state, &enableGravity, sizeof(enableGravity));
        XXH64_update(&hash_state, &enableAirResistance, sizeof(enableAirResistance));
        XXH64_update(&hash_state, &airResistanceFactor, sizeof(airResistanceFactor));
        XXH64_update(&hash_state, &enableBounce, sizeof(enableBounce));
        XXH64_update(&hash_state, &bounceFactor, sizeof(bounceFactor));
        XXH64_update(&hash_state, &enableCaching, sizeof(enableCaching));
        XXH64_update(&hash_state, &enableHotReload, sizeof(enableHotReload));
        XXH64_update(&hash_state, &enableParallelProcessing, sizeof(enableParallelProcessing));
        XXH64_update(&hash_state, &lodLevel, sizeof(lodLevel));
        return XXH64_digest(&hash_state);
    }
};

// UI item parameters
struct UIItemParams {
    // Icon properties
    int iconSize;
    glm::vec4 borderColor;
    BackgroundShape backgroundShape;
    bool flashOnSelect;
    
    // Visual properties
    float borderThickness;
    float cornerRadius;
    bool enableGlow;
    glm::vec3 glowColor;
    float glowIntensity;
    bool enablePulse;
    float pulseFrequency;
    float pulseAmplitude;
    
    // Animation properties
    bool enableHoverEffect;
    float hoverScale;
    float hoverDuration;
    bool enableClickEffect;
    float clickScale;
    float clickDuration;
    
    // Text properties
    std::string label;
    bool enableLabel;
    glm::vec3 labelColor;
    float labelSize;
    std::string labelFont;
    
    // Performance properties
    bool enableCaching;
    bool enableHotReload;
    int lodLevel;
    
    // Metadata
    std::string description;
    std::vector<std::string> tags;
    std::map<std::string, std::string> metadata;

    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, &iconSize, sizeof(iconSize));
        XXH64_update(&hash_state, &borderColor.x, sizeof(float) * 4);
        XXH64_update(&hash_state, &backgroundShape, sizeof(backgroundShape));
        XXH64_update(&hash_state, &flashOnSelect, sizeof(flashOnSelect));
        XXH64_update(&hash_state, &borderThickness, sizeof(borderThickness));
        XXH64_update(&hash_state, &cornerRadius, sizeof(cornerRadius));
        XXH64_update(&hash_state, &enableGlow, sizeof(enableGlow));
        XXH64_update(&hash_state, &glowColor.x, sizeof(float) * 3);
        XXH64_update(&hash_state, &glowIntensity, sizeof(glowIntensity));
        XXH64_update(&hash_state, &enablePulse, sizeof(enablePulse));
        XXH64_update(&hash_state, &pulseFrequency, sizeof(pulseFrequency));
        XXH64_update(&hash_state, &pulseAmplitude, sizeof(pulseAmplitude));
        XXH64_update(&hash_state, &enableHoverEffect, sizeof(enableHoverEffect));
        XXH64_update(&hash_state, &hoverScale, sizeof(hoverScale));
        XXH64_update(&hash_state, &hoverDuration, sizeof(hoverDuration));
        XXH64_update(&hash_state, &enableClickEffect, sizeof(enableClickEffect));
        XXH64_update(&hash_state, &clickScale, sizeof(clickScale));
        XXH64_update(&hash_state, &clickDuration, sizeof(clickDuration));
        XXH64_update(&hash_state, label.c_str(), label.length());
        XXH64_update(&hash_state, &enableLabel, sizeof(enableLabel));
        XXH64_update(&hash_state, &labelColor.x, sizeof(float) * 3);
        XXH64_update(&hash_state, &labelSize, sizeof(labelSize));
        XXH64_update(&hash_state, labelFont.c_str(), labelFont.length());
        XXH64_update(&hash_state, &enableCaching, sizeof(enableCaching));
        XXH64_update(&hash_state, &enableHotReload, sizeof(enableHotReload));
        XXH64_update(&hash_state, &lodLevel, sizeof(lodLevel));
        return XXH64_digest(&hash_state);
    }
};

// Asset bundle structure
struct GrenadeAssetBundle {
    // Item assets (for inventory display)
    MeshHandle meshItem;
    TextureHandle textureItem;
    ShaderHandle shaderItem;
    
    // Projectile assets (for thrown grenade)
    MeshHandle meshProj;
    ShaderHandle shaderProj;
    
    // Effect assets
    ParticleHandle explosionFX;
    ParticleHandle residueFX;
    AudioHandle sfx;
    
    // UI assets
    IconHandle icon;
    
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
    GrenadeType parseGrenadeType(const std::string& str);
    CasingMaterial parseCasingMaterial(const std::string& str);
    ParticleType parseParticleType(const std::string& str);
    ExplosionType parseExplosionType(const std::string& str);
    ResidueType parseResidueType(const std::string& str);
    SoundEffect parseSoundEffect(const std::string& str);
    BackgroundShape parseBackgroundShape(const std::string& str);
    
    // Enum to string conversions
    std::string grenadeTypeToString(GrenadeType type);
    std::string casingMaterialToString(CasingMaterial material);
    std::string particleTypeToString(ParticleType type);
    std::string explosionTypeToString(ExplosionType type);
    std::string residueTypeToString(ResidueType type);
    std::string soundEffectToString(SoundEffect effect);
    std::string backgroundShapeToString(BackgroundShape shape);
    
    // JSON serialization/deserialization
    nlohmann::json toJson(const AlchemicalGrenadeParams& params);
    AlchemicalGrenadeParams fromJson(const nlohmann::json& json);
    nlohmann::json toJson(const UIItemParams& params);
    UIItemParams fromJson(const nlohmann::json& json);
}

} // namespace AlchemicalGrenades
} // namespace MagiTech
