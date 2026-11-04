#pragma once

// Behaviour asset types for segmented creatures.
//
// BehaviorParams, AIHandle and AssetBundle are the canonical segmented-creature
// types (SegmentedCreatureParams.hpp / SegmentedCreatureAssetBundle.hpp); this
// header used to carry a second, incompatible BehaviorParams in the same
// namespace. It now adds only the behaviour classification enums and the
// multi-tree behaviour bundle built by BehaviorGenerators.

#include "SegmentedCreatureAssetBundle.hpp"
#include <chrono>
#include <cstdint>
#include <string>

namespace MagiTech {
namespace SegmentedCreatures {

// Behavior archetypes for segmented creatures (superset of AIProfile)
enum class BehaviorType : uint8_t {
    PASSIVE = 0,
    NEUTRAL = 1,
    PREDATOR = 2,
    SWARM = 3,
    BURROWER = 4,
    CLIMBER = 5,
    AMBUSHER = 6,
    GUARDIAN = 7,
    SCAVENGER = 8,
    HERD = 9
};

// Movement patterns for segmented creatures
enum class MovementPattern : uint8_t {
    SLITHER = 0,
    CRAWL = 1,
    BURROW = 2,
    SWIM = 3,
    CLIMB = 4,
    FLY = 5,
    COIL = 6,
    FLOAT = 7
};

// Combat styles for segmented creatures
enum class CombatStyle : uint8_t {
    MELEE = 0,
    RANGED = 1,
    VENOM = 2,
    CONSTRICT = 3,
    BURROW_ATTACK = 4,
    SWARM_ATTACK = 5,
    AMBUSH = 6,
    DEFENSIVE = 7
};

// Behavior generation result
struct BehaviorGenerationResult {
    bool success = false;
    std::string errorMessage;
    float generationTime = 0.0f;       // seconds
    size_t memoryUsage = 0;            // approximate bytes of the generated trees
    uint32_t behaviorNodeCount = 0;    // nodes over all generated trees
    uint32_t decisionTreeDepth = 0;    // deepest generated tree
    uint32_t stateMachineStates = 0;   // states over all generated trees

    explicit operator bool() const { return success; }
};

// Behavior asset bundle: the main behaviour tree plus focused sub-trees
struct BehaviorAssetBundle {
    // Core behavior assets
    AIHandle ai = 0;

    // Focused behaviour trees (0 when the creature has no such behaviour)
    AIHandle movementAI = 0;
    AIHandle combatAI = 0;
    AIHandle socialAI = 0;
    AIHandle environmentalAI = 0;

    // Metadata
    BehaviorGenerationResult result;
    BehaviorParams params;
    std::string assetPath;
    std::chrono::system_clock::time_point creationTime{};

    bool isValid() const {
        return ai != 0;
    }

    std::string getInfo() const {
        return "BehaviorAssetBundle{ai=" + std::to_string(ai) +
               ", movementAI=" + std::to_string(movementAI) +
               ", combatAI=" + std::to_string(combatAI) +
               ", socialAI=" + std::to_string(socialAI) +
               ", environmentalAI=" + std::to_string(environmentalAI) + "}";
    }
};

} // namespace SegmentedCreatures
} // namespace MagiTech
