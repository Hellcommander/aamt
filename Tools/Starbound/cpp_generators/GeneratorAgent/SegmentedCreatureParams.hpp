#pragma once

#include <string>
#include <vector>
#include <array>
#include <map>
#include <cstdint>
#include <functional>
#include "vendor/json/include/nlohmann/json.hpp"

namespace MagiTech {
namespace SegmentedCreatures {

// Enums for creature parameters
enum class TaperProfile {
    NONE,
    LINEAR,
    EXPONENTIAL,
    CUSTOM_CURVE
};

enum class SegmentType {
    CYLINDER,
    BOX,
    HEXAGON,
    CUSTOM_MESH
};

enum class HeadType {
    SIMPLE,
    MANDIBLE,
    MULTI_EYE,
    HORNED
};

enum class TailType {
    NONE,
    SPIKE,
    FLARED
};

enum class AnimationProfile {
    SLITHER,
    CRAWL,
    COIL,
    CUSTOM
};

enum class AIProfile {
    PASSIVE,
    NEUTRAL,
    PREDATOR,
    SWARM
};

// SegmentedCreatureParams structure
struct SegmentedCreatureParams {
    std::string id;
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
    float armorThickness = 0.05f;
    bool enableSpikes = false;
    int spikeCount = 0;
    float spikeLength = 0.1f;
    
    // Metadata
    std::string description;
    std::vector<std::string> tags;
    std::map<std::string, std::string> metadata;
    
    // Performance settings
    bool enableCaching = true;
    bool enableHotReload = true;
    bool enableParallelProcessing = true;
    
    // Hash function for caching
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
        hash = hashCombine(hash, std::hash<float>{}(colorPrimary[0]));
        hash = hashCombine(hash, std::hash<float>{}(colorPrimary[1]));
        hash = hashCombine(hash, std::hash<float>{}(colorPrimary[2]));
        hash = hashCombine(hash, std::hash<float>{}(colorSecondary[0]));
        hash = hashCombine(hash, std::hash<float>{}(colorSecondary[1]));
        hash = hashCombine(hash, std::hash<float>{}(colorSecondary[2]));
        hash = hashCombine(hash, std::hash<float>{}(materialRoughness));
        hash = hashCombine(hash, std::hash<float>{}(materialMetallic));
        hash = hashCombine(hash, std::hash<int>{}(static_cast<int>(animationProfile)));
        hash = hashCombine(hash, std::hash<int>{}(static_cast<int>(aiProfile)));
        return hash;
    }
    
private:
    template<typename T>
    static uint64_t hashCombine(uint64_t seed, const T& value) {
        return seed ^ (std::hash<T>{}(value) + 0x9e3779b9 + (seed << 6) + (seed >> 2));
    }
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
    SegmentedCreatureParams fromJson(const nlohmann::json& json);
    
    nlohmann::json toJson(const BehaviorParams& params);
    BehaviorParams fromJson(const nlohmann::json& json);
}

} // namespace SegmentedCreatures
} // namespace MagiTech 
