#pragma once

#include <string>
#include <vector>
#include <array>
#include <map>
#include <cstdint>
#include <cstring>
#include <functional>
#include "vendor/json/include/nlohmann/json.hpp"

namespace MagiTech {
namespace SegmentedCreatures {

// Enums for creature parameters (new values are appended so existing numeric values stay stable)
enum class TaperProfile {
    NONE,
    LINEAR,
    EXPONENTIAL,
    CUSTOM_CURVE,
    BELL_CURVE,     // thickest in the middle
    STEPPED,        // radius drops in discrete steps
    IRREGULAR       // seeded random variation around a linear taper
};

enum class SegmentType {
    CYLINDER,
    BOX,
    HEXAGON,
    CUSTOM_MESH,
    SPHERE,
    CAPSULE,
    PRISM,          // triangular prism
    IRREGULAR       // noise-deformed cylinder
};

enum class HeadType {
    SIMPLE,
    MANDIBLE,
    MULTI_EYE,
    HORNED,
    FANGED,
    TENTACLED,
    CRYSTAL,
    MECHANICAL
};

enum class TailType {
    NONE,
    SPIKE,
    FLARED,
    TENTACLE,
    CRYSTAL,
    MECHANICAL,
    BIOLUMINESCENT,
    VENOMOUS
};

enum class AnimationProfile {
    SLITHER,
    CRAWL,
    COIL,
    CUSTOM,
    BURROW,
    SWIM,
    FLY,
    CLIMB,
    WAVE_SLITHER = SLITHER   // alias used by the former creature_assets types
};

enum class AIProfile {
    PASSIVE,
    NEUTRAL,
    PREDATOR,
    SWARM,
    BURROWER,
    CLIMBER,
    AMBUSHER,
    GUARDIAN
};

// SegmentedCreatureParams structure
struct SegmentedCreatureParams {
    std::string id;
    std::string name;
    int segmentCount = 20;
    float segmentLength = 0.5f;
    TaperProfile taperProfile = TaperProfile::LINEAR;
    float segmentRadius = 0.2f;
    SegmentType segmentType = SegmentType::CYLINDER;
    HeadType headType = HeadType::MANDIBLE;
    TailType tailType = TailType::SPIKE;
    float articulationStiffness = 0.7f;
    float noiseDetail = 0.4f;
    bool armorPlates = true;
    int plateDetailLevel = 2;
    std::array<float, 3> colorPrimary = {0.3f, 0.3f, 0.35f};
    std::array<float, 3> colorSecondary = {0.1f, 0.1f, 0.1f};
    float materialRoughness = 0.6f;
    float materialMetallic = 0.8f;
    AnimationProfile animationProfile = AnimationProfile::SLITHER;
    AIProfile aiProfile = AIProfile::PREDATOR;

    // Custom curve for taper profile
    std::vector<float> customTaperCurve;

    // Additional parameters
    float segmentSpacing = 0.1f;
    bool enableJoints = true;
    float jointFlexibility = 0.5f;
    bool enableArmor = true;
    float armorThickness = 0.05f;          // armour plate thickness (JSON/Lua alias: plateThickness)
    bool enableSpikes = false;
    int spikeCount = 0;
    float spikeLength = 0.1f;

    // Head and tail configuration
    float headScale = 1.2f;                // head size multiplier
    float tailScale = 0.8f;                // tail size multiplier
    int headSegmentCount = 1;              // head/neck segments
    int tailSegmentCount = 1;              // tail segments

    // Articulation and physics
    float jointLimit = 45.0f;              // maximum joint angle in degrees
    float segmentMass = 1.0f;              // mass per segment
    float segmentDensity = 1.0f;           // material density
    float segmentFriction = 0.5f;          // surface friction
    float segmentRestitution = 0.3f;       // bounce factor

    // Visual appearance
    std::array<float, 3> colorAccent = {0.8f, 0.8f, 0.8f};
    float colorVariation = 0.1f;           // random colour variation
    float materialEmissive = 0.0f;         // glow intensity
    float materialTransparency = 0.0f;     // transparency factor

    // Armour plate layout
    float plateSpacing = 0.1f;             // gap between consecutive plates (fraction of segment length)
    bool plateOverlap = false;             // plates extend over the segment gap and overlap

    // Advanced features
    bool gpuAccelerated = true;            // execution hint for hosts with a GPU path
    bool simdEnabled = true;               // execution hint for SIMD code paths
    bool adaptiveLOD = true;               // hint: runtime may pick lower detail for distant creatures
    bool proceduralVariation = true;       // seeded per-segment variation
    bool dynamicSegments = false;          // segment count may change at runtime
    bool damageableSegments = false;       // individual segments can be damaged / severed

    // Generation settings
    uint32_t seed = 0;                     // random seed (0 = derived from id)
    float generationQuality = 1.0f;        // tessellation / texture quality multiplier (0..2]

    // Metadata
    std::string description;
    std::vector<std::string> tags;
    std::map<std::string, std::string> metadata;

    // Performance settings
    bool enableCaching = true;             // JSON/Lua alias: cacheEnabled
    bool enableHotReload = true;
    bool enableParallelProcessing = true;

    // Hash function for caching (every field that changes the generated assets)
    uint64_t hashKey() const {
        uint64_t hash = 0;
        hash = hashCombine(hash, std::hash<std::string>{}(id));
        hash = hashCombine(hash, std::hash<int>{}(segmentCount));
        hash = hashCombine(hash, std::hash<float>{}(segmentLength));
        hash = hashCombine(hash, std::hash<int>{}(static_cast<int>(taperProfile)));
        hash = hashCombine(hash, std::hash<float>{}(segmentRadius));
        hash = hashCombine(hash, std::hash<int>{}(static_cast<int>(segmentType)));
        hash = hashCombine(hash, std::hash<int>{}(static_cast<int>(headType)));
        hash = hashCombine(hash, std::hash<int>{}(static_cast<int>(tailType)));
        hash = hashCombine(hash, std::hash<float>{}(articulationStiffness));
        hash = hashCombine(hash, std::hash<float>{}(noiseDetail));
        hash = hashCombine(hash, std::hash<bool>{}(armorPlates));
        hash = hashCombine(hash, std::hash<int>{}(plateDetailLevel));
        for (float c : colorPrimary) hash = hashCombine(hash, std::hash<float>{}(c));
        for (float c : colorSecondary) hash = hashCombine(hash, std::hash<float>{}(c));
        hash = hashCombine(hash, std::hash<float>{}(materialRoughness));
        hash = hashCombine(hash, std::hash<float>{}(materialMetallic));
        hash = hashCombine(hash, std::hash<int>{}(static_cast<int>(animationProfile)));
        hash = hashCombine(hash, std::hash<int>{}(static_cast<int>(aiProfile)));
        for (float v : customTaperCurve) hash = hashCombine(hash, std::hash<float>{}(v));
        hash = hashCombine(hash, std::hash<float>{}(segmentSpacing));
        hash = hashCombine(hash, std::hash<bool>{}(enableJoints));
        hash = hashCombine(hash, std::hash<float>{}(jointFlexibility));
        hash = hashCombine(hash, std::hash<bool>{}(enableArmor));
        hash = hashCombine(hash, std::hash<float>{}(armorThickness));
        hash = hashCombine(hash, std::hash<bool>{}(enableSpikes));
        hash = hashCombine(hash, std::hash<int>{}(spikeCount));
        hash = hashCombine(hash, std::hash<float>{}(spikeLength));
        hash = hashCombine(hash, std::hash<float>{}(headScale));
        hash = hashCombine(hash, std::hash<float>{}(tailScale));
        hash = hashCombine(hash, std::hash<int>{}(headSegmentCount));
        hash = hashCombine(hash, std::hash<int>{}(tailSegmentCount));
        hash = hashCombine(hash, std::hash<float>{}(jointLimit));
        hash = hashCombine(hash, std::hash<float>{}(segmentMass));
        hash = hashCombine(hash, std::hash<float>{}(segmentDensity));
        hash = hashCombine(hash, std::hash<float>{}(segmentFriction));
        hash = hashCombine(hash, std::hash<float>{}(segmentRestitution));
        for (float c : colorAccent) hash = hashCombine(hash, std::hash<float>{}(c));
        hash = hashCombine(hash, std::hash<float>{}(colorVariation));
        hash = hashCombine(hash, std::hash<float>{}(materialEmissive));
        hash = hashCombine(hash, std::hash<float>{}(materialTransparency));
        hash = hashCombine(hash, std::hash<float>{}(plateSpacing));
        hash = hashCombine(hash, std::hash<bool>{}(plateOverlap));
        hash = hashCombine(hash, std::hash<bool>{}(proceduralVariation));
        hash = hashCombine(hash, std::hash<bool>{}(dynamicSegments));
        hash = hashCombine(hash, std::hash<bool>{}(damageableSegments));
        hash = hashCombine(hash, std::hash<uint32_t>{}(seed));
        hash = hashCombine(hash, std::hash<float>{}(generationQuality));
        hash = hashCombine(hash, std::hash<std::string>{}(name));
        for (const auto& [key, value] : metadata) {
            hash = hashCombine(hash, std::hash<std::string>{}(key));
            hash = hashCombine(hash, std::hash<std::string>{}(value));
        }
        return hash;
    }

    bool isValid() const {
        return !id.empty() &&
               segmentCount > 0 && segmentCount <= 1000 &&
               segmentLength > 0.0f && segmentLength <= 10.0f &&
               segmentRadius > 0.0f && segmentRadius <= 5.0f &&
               articulationStiffness >= 0.0f && articulationStiffness <= 1.0f &&
               headSegmentCount >= 1 && tailSegmentCount >= 1 &&
               headScale > 0.0f && tailScale > 0.0f &&
               generationQuality > 0.0f && generationQuality <= 2.0f;
    }

    std::string toString() const {
        return "SegmentedCreatureParams{id='" + id + "', segmentCount=" + std::to_string(segmentCount) +
               ", segmentLength=" + std::to_string(segmentLength) + ", segmentRadius=" + std::to_string(segmentRadius) + "}";
    }

private:
    template<typename T>
    static uint64_t hashCombine(uint64_t seed, const T& value) {
        return seed ^ (std::hash<T>{}(value) + 0x9e3779b9 + (seed << 6) + (seed >> 2));
    }
};

// Segmented creature generation statistics (filled by the factory into AssetBundle::result)
struct SegmentedCreatureGenerationResult {
    bool success = false;
    std::string errorMessage;
    float generationTime = 0.0f;       // seconds
    size_t memoryUsage = 0;            // bytes of generated CPU data
    uint32_t vertexCount = 0;
    uint32_t triangleCount = 0;
    uint32_t textureSize = 0;
    uint32_t animationFrameCount = 0;
    uint32_t segmentCount = 0;
    uint32_t boneCount = 0;

    explicit operator bool() const { return success; }
};

// BehaviorParams structure
struct BehaviorParams {
    float speed = 1.0f;
    float detectionRange = 15.0f;
    float attackRange = 1.5f;
    float aggression = 0.6f;
    int packSize = 1;
    float burrowDepth = 2.0f;
    bool climbAbility = true;

    // Additional behavior parameters
    float patrolRadius = 10.0f;
    float idleTime = 2.0f;
    float chaseSpeed = 1.5f;
    float retreatHealth = 0.3f;
    bool canSwim = false;
    bool canFly = false;
    bool nocturnal = false;
    bool territorial = false;
    float territorySize = 20.0f;

    // Combat parameters
    float attackDamage = 10.0f;
    float attackCooldown = 1.0f;
    bool canRangedAttack = false;
    float rangedAttackRange = 5.0f;
    bool canUseAbilities = false;
    std::vector<std::string> abilities;

    // Social parameters
    bool packHunting = false;
    float packCohesion = 0.8f;
    bool hierarchical = false;
    int dominanceRank = 0;

    // Environmental parameters
    bool burrower = false;
    bool climber = false;
    bool swimmer = false;
    bool flyer = false;
    float preferredTemperature = 20.0f;
    float temperatureTolerance = 10.0f;

    // Metadata
    std::string behaviorName;
    std::string description;
    std::vector<std::string> tags;
    std::map<std::string, std::string> metadata;

    // Hash function for caching
    uint64_t hashKey() const {
        uint64_t hash = 0;
        hash = hashCombine(hash, std::hash<float>{}(speed));
        hash = hashCombine(hash, std::hash<float>{}(detectionRange));
        hash = hashCombine(hash, std::hash<float>{}(attackRange));
        hash = hashCombine(hash, std::hash<float>{}(aggression));
        hash = hashCombine(hash, std::hash<int>{}(packSize));
        hash = hashCombine(hash, std::hash<float>{}(burrowDepth));
        hash = hashCombine(hash, std::hash<bool>{}(climbAbility));
        hash = hashCombine(hash, std::hash<float>{}(patrolRadius));
        hash = hashCombine(hash, std::hash<float>{}(idleTime));
        hash = hashCombine(hash, std::hash<float>{}(chaseSpeed));
        hash = hashCombine(hash, std::hash<float>{}(retreatHealth));
        hash = hashCombine(hash, std::hash<bool>{}(canSwim));
        hash = hashCombine(hash, std::hash<bool>{}(canFly));
        hash = hashCombine(hash, std::hash<bool>{}(nocturnal));
        hash = hashCombine(hash, std::hash<bool>{}(territorial));
        hash = hashCombine(hash, std::hash<float>{}(territorySize));
        hash = hashCombine(hash, std::hash<float>{}(attackDamage));
        hash = hashCombine(hash, std::hash<float>{}(attackCooldown));
        hash = hashCombine(hash, std::hash<bool>{}(canRangedAttack));
        hash = hashCombine(hash, std::hash<float>{}(rangedAttackRange));
        hash = hashCombine(hash, std::hash<bool>{}(canUseAbilities));
        hash = hashCombine(hash, std::hash<bool>{}(packHunting));
        hash = hashCombine(hash, std::hash<float>{}(packCohesion));
        hash = hashCombine(hash, std::hash<bool>{}(hierarchical));
        hash = hashCombine(hash, std::hash<int>{}(dominanceRank));
        hash = hashCombine(hash, std::hash<bool>{}(burrower));
        hash = hashCombine(hash, std::hash<bool>{}(climber));
        hash = hashCombine(hash, std::hash<bool>{}(swimmer));
        hash = hashCombine(hash, std::hash<bool>{}(flyer));
        hash = hashCombine(hash, std::hash<float>{}(preferredTemperature));
        hash = hashCombine(hash, std::hash<float>{}(temperatureTolerance));
        for (const auto& ability : abilities) hash = hashCombine(hash, std::hash<std::string>{}(ability));
        hash = hashCombine(hash, std::hash<std::string>{}(behaviorName));
        return hash;
    }

private:
    template<typename T>
    static uint64_t hashCombine(uint64_t seed, const T& value) {
        return seed ^ (std::hash<T>{}(value) + 0x9e3779b9 + (seed << 6) + (seed >> 2));
    }
};

// Utility functions for parameter conversion
namespace ParamUtils {
    // Convert string to enum
    TaperProfile parseTaperProfile(const std::string& str);
    SegmentType parseSegmentType(const std::string& str);
    HeadType parseHeadType(const std::string& str);
    TailType parseTailType(const std::string& str);
    AnimationProfile parseAnimationProfile(const std::string& str);
    AIProfile parseAIProfile(const std::string& str);

    // Convert enum to string
    std::string taperProfileToString(TaperProfile profile);
    std::string segmentTypeToString(SegmentType type);
    std::string headTypeToString(HeadType type);
    std::string tailTypeToString(TailType type);
    std::string animationProfileToString(AnimationProfile profile);
    std::string aiProfileToString(AIProfile profile);

    // JSON serialization
    nlohmann::json toJson(const SegmentedCreatureParams& params);
    SegmentedCreatureParams creatureFromJson(const nlohmann::json& json);

    nlohmann::json toJson(const BehaviorParams& params);
    BehaviorParams behaviorFromJson(const nlohmann::json& json);
}

} // namespace SegmentedCreatures
} // namespace MagiTech
