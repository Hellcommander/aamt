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
namespace AlchemicalLaunchers {

using MeshHandle = uint32_t;
using TextureHandle = uint32_t;
using ShaderHandle = uint32_t;
using ParticleHandle = uint32_t;
using PhysicsHandle = uint32_t;
using AudioHandle = uint32_t;
using IconHandle = uint32_t;

// Enum for launcher types
enum class LauncherType {
    CATAPULT,
    CROSSBOW,
    BALLISTA,
    CANNON,
    ROCKET,
    RAILGUN,
    MAGIC_STAFF,
    WAND,
    CUSTOM
};

// Enum for material types
enum class MaterialType {
    STEEL,
    IRON,
    BRONZE,
    WOOD,
    STONE,
    CRYSTAL,
    MAGIC,
    ORGANIC,
    CUSTOM
};

// Enum for sight types
enum class SightType {
    NONE,
    IRON_SIGHT,
    SCOPE,
    MAGIC_SIGHT,
    THERMAL,
    CUSTOM
};

// Enum for engraving patterns
enum class EngravingPattern {
    NONE,
    ALCHEMY_RUNES,
    MAGIC_SIGILS,
    GEOMETRIC,
    FLORAL,
    DRAGON,
    PHOENIX,
    CUSTOM
};

// Enum for background shapes
enum class BackgroundShape {
    RECTANGLE,
    CIRCLE,
    HEXAGON,
    DIAMOND,
    NONE,
    CUSTOM
};

// Main alchemical launcher parameters
struct AlchemicalLauncherParams {
    // Basic properties
    std::string id;
    LauncherType launcherType;
    MaterialType materialMain;
    MaterialType materialSecondary;
    SightType sightType;
    EngravingPattern engravingPattern;
    
    // Physical properties
    float barrelLength;
    float barrelRadius;
    float barrelThickness;
    float frameLength;
    float frameWidth;
    float frameHeight;
    float gripLength;
    float gripWidth;
    float gripHeight;
    float magazineRadius;
    float magazineHeight;
    int magazineCapacity;
    float sightHeight;
    float sightWidth;
    
    // Performance properties
    float fireRate;
    float reloadTime;
    float accuracy;
    float range;
    float projectileSpeed;
    float recoilForce;
    float recoilRecovery;
    float muzzleVelocity;
    
    // Visual properties
    glm::vec3 colorPrimary;
    glm::vec3 colorSecondary;
    glm::vec3 colorAccent;
    glm::vec3 glowColor;
    float noiseScale;
    float noiseIntensity;
    float metallicness;
    float roughness;
    float emissivePower;
    float transparency;
    float refractionIndex;
    float reflectionStrength;
    
    // Muzzle effects
    float muzzleGlowIntensity;
    float muzzleFlashSize;
    float muzzleFlashDuration;
    int muzzleSmokeCount;
    float muzzleSmokeLifetime;
    float muzzleSmokeSize;
    float muzzleSmokeSpeed;
    glm::vec3 muzzleFlashColor;
    glm::vec3 muzzleSmokeColor;
    
    // Particle effects
    bool enableShellEjection;
    int shellEjectionCount;
    float shellEjectionSpeed;
    float shellEjectionLifetime;
    bool enableHeatDistortion;
    float heatDistortionStrength;
    float heatDistortionRadius;
    
    // Audio properties
    float soundVolume;
    float soundPitch;
    float soundDuration;
    bool enableSpatialAudio;
    float audioDistance;
    bool enableEcho;
    float echoDelay;
    float echoDecay;
    bool enableReverb;
    float reverbIntensity;
    
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
    float mass;
    float density;
    float friction;
    float bounciness;
    
    // Ornamentation properties
    bool ornamentation;
    float ornamentationScale;
    float ornamentationIntensity;
    bool enableRunes;
    float runeGlowIntensity;
    bool enableCrystals;
    float crystalGlowIntensity;
    bool enableGems;
    float gemGlowIntensity;
    
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
        XXH64_update(&hash_state, &launcherType, sizeof(launcherType));
        XXH64_update(&hash_state, &materialMain, sizeof(materialMain));
        XXH64_update(&hash_state, &materialSecondary, sizeof(materialSecondary));
        XXH64_update(&hash_state, &sightType, sizeof(sightType));
        XXH64_update(&hash_state, &engravingPattern, sizeof(engravingPattern));
        XXH64_update(&hash_state, &barrelLength, sizeof(barrelLength));
        XXH64_update(&hash_state, &barrelRadius, sizeof(barrelRadius));
        XXH64_update(&hash_state, &barrelThickness, sizeof(barrelThickness));
        XXH64_update(&hash_state, &frameLength, sizeof(frameLength));
        XXH64_update(&hash_state, &frameWidth, sizeof(frameWidth));
        XXH64_update(&hash_state, &frameHeight, sizeof(frameHeight));
        XXH64_update(&hash_state, &gripLength, sizeof(gripLength));
        XXH64_update(&hash_state, &gripWidth, sizeof(gripWidth));
        XXH64_update(&hash_state, &gripHeight, sizeof(gripHeight));
        XXH64_update(&hash_state, &magazineRadius, sizeof(magazineRadius));
        XXH64_update(&hash_state, &magazineHeight, sizeof(magazineHeight));
        XXH64_update(&hash_state, &magazineCapacity, sizeof(magazineCapacity));
        XXH64_update(&hash_state, &sightHeight, sizeof(sightHeight));
        XXH64_update(&hash_state, &sightWidth, sizeof(sightWidth));
        XXH64_update(&hash_state, &fireRate, sizeof(fireRate));
        XXH64_update(&hash_state, &reloadTime, sizeof(reloadTime));
        XXH64_update(&hash_state, &accuracy, sizeof(accuracy));
        XXH64_update(&hash_state, &range, sizeof(range));
        XXH64_update(&hash_state, &projectileSpeed, sizeof(projectileSpeed));
        XXH64_update(&hash_state, &recoilForce, sizeof(recoilForce));
        XXH64_update(&hash_state, &recoilRecovery, sizeof(recoilRecovery));
        XXH64_update(&hash_state, &muzzleVelocity, sizeof(muzzleVelocity));
        XXH64_update(&hash_state, &colorPrimary.x, sizeof(float) * 3);
        XXH64_update(&hash_state, &colorSecondary.x, sizeof(float) * 3);
        XXH64_update(&hash_state, &colorAccent.x, sizeof(float) * 3);
        XXH64_update(&hash_state, &glowColor.x, sizeof(float) * 3);
        XXH64_update(&hash_state, &noiseScale, sizeof(noiseScale));
        XXH64_update(&hash_state, &noiseIntensity, sizeof(noiseIntensity));
        XXH64_update(&hash_state, &metallicness, sizeof(metallicness));
        XXH64_update(&hash_state, &roughness, sizeof(roughness));
        XXH64_update(&hash_state, &emissivePower, sizeof(emissivePower));
        XXH64_update(&hash_state, &transparency, sizeof(transparency));
        XXH64_update(&hash_state, &refractionIndex, sizeof(refractionIndex));
        XXH64_update(&hash_state, &reflectionStrength, sizeof(reflectionStrength));
        XXH64_update(&hash_state, &muzzleGlowIntensity, sizeof(muzzleGlowIntensity));
        XXH64_update(&hash_state, &muzzleFlashSize, sizeof(muzzleFlashSize));
        XXH64_update(&hash_state, &muzzleFlashDuration, sizeof(muzzleFlashDuration));
        XXH64_update(&hash_state, &muzzleSmokeCount, sizeof(muzzleSmokeCount));
        XXH64_update(&hash_state, &muzzleSmokeLifetime, sizeof(muzzleSmokeLifetime));
        XXH64_update(&hash_state, &muzzleSmokeSize, sizeof(muzzleSmokeSize));
        XXH64_update(&hash_state, &muzzleSmokeSpeed, sizeof(muzzleSmokeSpeed));
        XXH64_update(&hash_state, &muzzleFlashColor.x, sizeof(float) * 3);
        XXH64_update(&hash_state, &muzzleSmokeColor.x, sizeof(float) * 3);
        XXH64_update(&hash_state, &enableShellEjection, sizeof(enableShellEjection));
        XXH64_update(&hash_state, &shellEjectionCount, sizeof(shellEjectionCount));
        XXH64_update(&hash_state, &shellEjectionSpeed, sizeof(shellEjectionSpeed));
        XXH64_update(&hash_state, &shellEjectionLifetime, sizeof(shellEjectionLifetime));
        XXH64_update(&hash_state, &enableHeatDistortion, sizeof(enableHeatDistortion));
        XXH64_update(&hash_state, &heatDistortionStrength, sizeof(heatDistortionStrength));
        XXH64_update(&hash_state, &heatDistortionRadius, sizeof(heatDistortionRadius));
        XXH64_update(&hash_state, &soundVolume, sizeof(soundVolume));
        XXH64_update(&hash_state, &soundPitch, sizeof(soundPitch));
        XXH64_update(&hash_state, &soundDuration, sizeof(soundDuration));
        XXH64_update(&hash_state, &enableSpatialAudio, sizeof(enableSpatialAudio));
        XXH64_update(&hash_state, &audioDistance, sizeof(audioDistance));
        XXH64_update(&hash_state, &enableEcho, sizeof(enableEcho));
        XXH64_update(&hash_state, &echoDelay, sizeof(echoDelay));
        XXH64_update(&hash_state, &echoDecay, sizeof(echoDecay));
        XXH64_update(&hash_state, &enableReverb, sizeof(enableReverb));
        XXH64_update(&hash_state, &reverbIntensity, sizeof(reverbIntensity));
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
        XXH64_update(&hash_state, &mass, sizeof(mass));
        XXH64_update(&hash_state, &density, sizeof(density));
        XXH64_update(&hash_state, &friction, sizeof(friction));
        XXH64_update(&hash_state, &bounciness, sizeof(bounciness));
        XXH64_update(&hash_state, &ornamentation, sizeof(ornamentation));
        XXH64_update(&hash_state, &ornamentationScale, sizeof(ornamentationScale));
        XXH64_update(&hash_state, &ornamentationIntensity, sizeof(ornamentationIntensity));
        XXH64_update(&hash_state, &enableRunes, sizeof(enableRunes));
        XXH64_update(&hash_state, &runeGlowIntensity, sizeof(runeGlowIntensity));
        XXH64_update(&hash_state, &enableCrystals, sizeof(enableCrystals));
        XXH64_update(&hash_state, &crystalGlowIntensity, sizeof(crystalGlowIntensity));
        XXH64_update(&hash_state, &enableGems, sizeof(enableGems));
        XXH64_update(&hash_state, &gemGlowIntensity, sizeof(gemGlowIntensity));
        XXH64_update(&hash_state, &enableCaching, sizeof(enableCaching));
        XXH64_update(&hash_state, &enableHotReload, sizeof(enableHotReload));
        XXH64_update(&hash_state, &enableParallelProcessing, sizeof(enableParallelProcessing));
        XXH64_update(&hash_state, &lodLevel, sizeof(lodLevel));
        return XXH64_digest(&hash_state);
    }
};

// UI parameters for launcher icons
struct UIParams {
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
struct LauncherAssetBundle {
    // Main launcher assets
    MeshHandle meshBody;
    TextureHandle textureBody;
    ShaderHandle shaderBody;
    
    // Effect assets
    ParticleHandle muzzleFlash;
    ParticleHandle muzzleSmoke;
    ParticleHandle shellEjection;
    ParticleHandle heatDistortion;
    
    // Physics assets
    PhysicsHandle recoilPhysics;
    PhysicsHandle magazinePhysics;
    
    // Audio assets
    AudioHandle sfxFire;
    AudioHandle sfxReload;
    AudioHandle sfxShellEject;
    AudioHandle sfxHeatDistortion;
    
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
    LauncherType parseLauncherType(const std::string& str);
    MaterialType parseMaterialType(const std::string& str);
    SightType parseSightType(const std::string& str);
    EngravingPattern parseEngravingPattern(const std::string& str);
    BackgroundShape parseBackgroundShape(const std::string& str);
    
    // Enum to string conversions
    std::string launcherTypeToString(LauncherType type);
    std::string materialTypeToString(MaterialType material);
    std::string sightTypeToString(SightType sight);
    std::string engravingPatternToString(EngravingPattern pattern);
    std::string backgroundShapeToString(BackgroundShape shape);
    
    // JSON serialization/deserialization
    nlohmann::json toJson(const AlchemicalLauncherParams& params);
    AlchemicalLauncherParams fromJson(const nlohmann::json& json);
    nlohmann::json toJson(const UIParams& params);
    UIParams fromJson(const nlohmann::json& json);
}

} // namespace AlchemicalLaunchers
} // namespace MagiTech
