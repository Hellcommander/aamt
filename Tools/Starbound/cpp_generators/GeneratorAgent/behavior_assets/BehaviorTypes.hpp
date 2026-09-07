#pragma once

#include <string>
#include <vector>
#include <array>
#include <glm/glm.hpp>
#include "xxhash.h"

namespace MagiTech {
namespace Monsters {

// Behavior types
enum class BehaviorType : uint8_t {
    PASSIVE = 0,
    NEUTRAL = 1,
    PREDATOR = 2,
    PACK_HUNTER = 3,
    BOSS = 4,
    MINION = 5,
    GUARDIAN = 6,
    WANDERER = 7,
    SCAVENGER = 8,
    HERD = 9
};

// Movement patterns
enum class MovementPattern : uint8_t {
    WALK = 0,
    RUN = 1,
    CRAWL = 2,
    FLY = 3,
    SWIM = 4,
    BURROW = 5,
    TELEPORT = 6,
    FLOAT = 7
};

// Combat styles
enum class CombatStyle : uint8_t {
    MELEE = 0,
    RANGED = 1,
    MAGIC = 2,
    STEALTH = 3,
    TANK = 4,
    SUPPORT = 5,
    BERSERKER = 6,
    TACTICAL = 7
};

// Enhanced BehaviorParams with C++23 features
struct BehaviorParams {
    // Basic behavior
    BehaviorType behaviorType = BehaviorType::PREDATOR;
    MovementPattern movementPattern = MovementPattern::WALK;
    CombatStyle combatStyle = CombatStyle::MELEE;
    
    // Aggression and personality
    float aggression = 0.8f;              // Attack likelihood 0-1
    float fear = 0.2f;                    // Flee likelihood 0-1
    float curiosity = 0.3f;               // Investigate likelihood 0-1
    float territorial = 0.6f;             // Defend area likelihood 0-1
    
    // Movement parameters
    float speed = 1.2f;                   // Movement speed multiplier
    float acceleration = 2.0f;             // Acceleration rate
    float turnSpeed = 90.0f;              // Degrees per second
    float jumpHeight = 0.0f;              // Jump height in meters
    float flySpeed = 0.0f;                // Flying speed multiplier
    
    // Detection and awareness
    float detectionRange = 20.0f;         // Detection radius in meters
    float visionAngle = 120.0f;           // Vision cone in degrees
    float hearingRange = 15.0f;           // Hearing range in meters
    float memoryDuration = 30.0f;         // Memory duration in seconds
    
    // Territory and roaming
    float wanderRadius = 10.0f;           // Roaming circle radius
    float homeRadius = 5.0f;              // Home territory radius
    float patrolRadius = 8.0f;            // Patrol area radius
    float retreatDistance = 15.0f;        // Retreat distance when hurt
    
    // Social behavior
    int packSize = 1;                     // Solo or group size
    float packCohesion = 0.7f;            // How close pack stays together
    float packAggression = 0.8f;          // Pack attack coordination
    float socialDistance = 2.0f;          // Distance between pack members
    
    // Combat parameters
    float attackRange = 2.0f;             // Melee attack range
    float rangedAttackRange = 0.0f;       // Ranged attack range
    float attackSpeed = 1.0f;             // Attacks per second
    float damageMultiplier = 1.0f;        // Damage output multiplier
    float defenseMultiplier = 1.0f;       // Damage resistance multiplier
    
    // Health and survival
    float maxHealth = 100.0f;             // Maximum health points
    float healthRegeneration = 0.0f;      // Health regen per second
    float stamina = 100.0f;               // Maximum stamina
    float staminaRegeneration = 10.0f;    // Stamina regen per second
    
    // Environmental adaptation
    bool canSwim = false;                 // Can move in water
    bool canFly = false;                  // Can fly
    bool canClimb = false;                // Can climb walls
    bool canBurrow = false;               // Can dig underground
    bool isNocturnal = false;             // Active at night
    bool isAquatic = false;               // Lives in water
    
    // Advanced AI features
    bool useCover = false;                // Use cover in combat
    bool flankEnemies = false;            // Try to flank opponents
    bool coordinateAttacks = false;       // Coordinate with pack
    bool retreatWhenHurt = true;          // Retreat when low health
    bool callForHelp = false;             // Call pack for assistance
    
    // Generation settings
    uint32_t seed = 0;                    // Random seed (0 = auto)
    float aiComplexity = 1.0f;            // AI complexity multiplier
    bool adaptiveBehavior = true;          // Learn from encounters
    bool proceduralVariation = true;      // Add random behavior variations
    
    // C++23 Modern hash function
    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, seed);
        
        // Hash behavior parameters
        XXH64_update(&hash_state, &behaviorType, sizeof(behaviorType));
        XXH64_update(&hash_state, &movementPattern, sizeof(movementPattern));
        XXH64_update(&hash_state, &combatStyle, sizeof(combatStyle));
        
        // Hash personality parameters
        XXH64_update(&hash_state, &aggression, sizeof(aggression));
        XXH64_update(&hash_state, &fear, sizeof(fear));
        XXH64_update(&hash_state, &curiosity, sizeof(curiosity));
        XXH64_update(&hash_state, &territorial, sizeof(territorial));
        
        // Hash movement parameters
        XXH64_update(&hash_state, &speed, sizeof(speed));
        XXH64_update(&hash_state, &acceleration, sizeof(acceleration));
        XXH64_update(&hash_state, &turnSpeed, sizeof(turnSpeed));
        XXH64_update(&hash_state, &jumpHeight, sizeof(jumpHeight));
        XXH64_update(&hash_state, &flySpeed, sizeof(flySpeed));
        
        // Hash detection parameters
        XXH64_update(&hash_state, &detectionRange, sizeof(detectionRange));
        XXH64_update(&hash_state, &visionAngle, sizeof(visionAngle));
        XXH64_update(&hash_state, &hearingRange, sizeof(hearingRange));
        XXH64_update(&hash_state, &memoryDuration, sizeof(memoryDuration));
        
        // Hash territory parameters
        XXH64_update(&hash_state, &wanderRadius, sizeof(wanderRadius));
        XXH64_update(&hash_state, &homeRadius, sizeof(homeRadius));
        XXH64_update(&hash_state, &patrolRadius, sizeof(patrolRadius));
        XXH64_update(&hash_state, &retreatDistance, sizeof(retreatDistance));
        
        // Hash social parameters
        XXH64_update(&hash_state, &packSize, sizeof(packSize));
        XXH64_update(&hash_state, &packCohesion, sizeof(packCohesion));
        XXH64_update(&hash_state, &packAggression, sizeof(packAggression));
        XXH64_update(&hash_state, &socialDistance, sizeof(socialDistance));
        
        // Hash combat parameters
        XXH64_update(&hash_state, &attackRange, sizeof(attackRange));
        XXH64_update(&hash_state, &rangedAttackRange, sizeof(rangedAttackRange));
        XXH64_update(&hash_state, &attackSpeed, sizeof(attackSpeed));
        XXH64_update(&hash_state, &damageMultiplier, sizeof(damageMultiplier));
        XXH64_update(&hash_state, &defenseMultiplier, sizeof(defenseMultiplier));
        
        // Hash health parameters
        XXH64_update(&hash_state, &maxHealth, sizeof(maxHealth));
        XXH64_update(&hash_state, &healthRegeneration, sizeof(healthRegeneration));
        XXH64_update(&hash_state, &stamina, sizeof(stamina));
        XXH64_update(&hash_state, &staminaRegeneration, sizeof(staminaRegeneration));
        
        // Hash environmental parameters
        XXH64_update(&hash_state, &canSwim, sizeof(canSwim));
        XXH64_update(&hash_state, &canFly, sizeof(canFly));
        XXH64_update(&hash_state, &canClimb, sizeof(canClimb));
        XXH64_update(&hash_state, &canBurrow, sizeof(canBurrow));
        XXH64_update(&hash_state, &isNocturnal, sizeof(isNocturnal));
        XXH64_update(&hash_state, &isAquatic, sizeof(isAquatic));
        
        // Hash AI features
        XXH64_update(&hash_state, &useCover, sizeof(useCover));
        XXH64_update(&hash_state, &flankEnemies, sizeof(flankEnemies));
        XXH64_update(&hash_state, &coordinateAttacks, sizeof(coordinateAttacks));
        XXH64_update(&hash_state, &retreatWhenHurt, sizeof(retreatWhenHurt));
        XXH64_update(&hash_state, &callForHelp, sizeof(callForHelp));
        
        // Hash generation settings
        XXH64_update(&hash_state, &seed, sizeof(seed));
        XXH64_update(&hash_state, &aiComplexity, sizeof(aiComplexity));
        XXH64_update(&hash_state, &adaptiveBehavior, sizeof(adaptiveBehavior));
        XXH64_update(&hash_state, &proceduralVariation, sizeof(proceduralVariation));
        
        return XXH64_digest(&hash_state);
    }
    
    // C++23 Modern validation
    bool isValid() const {
        return aggression >= 0.0f && aggression <= 1.0f &&
               fear >= 0.0f && fear <= 1.0f &&
               curiosity >= 0.0f && curiosity <= 1.0f &&
               territorial >= 0.0f && territorial <= 1.0f &&
               speed > 0.0f && speed <= 10.0f &&
               detectionRange > 0.0f && detectionRange <= 100.0f &&
               wanderRadius > 0.0f && wanderRadius <= 50.0f &&
               packSize >= 1 && packSize <= 20 &&
               maxHealth > 0.0f && maxHealth <= 10000.0f &&
               aiComplexity > 0.0f && aiComplexity <= 3.0f;
    }
    
    // C++23 Modern serialization helpers
    std::string toString() const {
        return "BehaviorParams{behaviorType=" + std::to_string(static_cast<int>(behaviorType)) + 
               ", aggression=" + std::to_string(aggression) + 
               ", speed=" + std::to_string(speed) + 
               ", detectionRange=" + std::to_string(detectionRange) + "}";
    }
};

// Behavior generation result
struct BehaviorGenerationResult {
    bool success = false;
    std::string errorMessage;
    float generationTime = 0.0f;
    size_t memoryUsage = 0;
    uint32_t behaviorNodeCount = 0;
    uint32_t decisionTreeDepth = 0;
    uint32_t stateMachineStates = 0;
    
    // C++23 Modern result type
    explicit operator bool() const { return success; }
};

// Behavior asset bundle
struct BehaviorAssetBundle {
    // Core behavior assets
    AIHandle ai = 0;
    
    // Additional behavior assets
    AIHandle patrolAI = 0;
    AIHandle combatAI = 0;
    AIHandle socialAI = 0;
    AIHandle environmentalAI = 0;
    
    // Metadata
    BehaviorGenerationResult result;
    BehaviorParams params;
    std::string assetPath;
    std::chrono::system_clock::time_point creationTime;
    
    // C++23 Modern asset validation
    bool isValid() const {
        return ai != 0;
    }
    
    // C++23 Modern asset info
    std::string getInfo() const {
        return "BehaviorAssetBundle{ai=" + std::to_string(ai) + 
               ", patrolAI=" + std::to_string(patrolAI) + 
               ", combatAI=" + std::to_string(combatAI) + 
               ", socialAI=" + std::to_string(socialAI) + 
               ", environmentalAI=" + std::to_string(environmentalAI) + "}";
    }
};

} // namespace Monsters
} // namespace MagiTech
