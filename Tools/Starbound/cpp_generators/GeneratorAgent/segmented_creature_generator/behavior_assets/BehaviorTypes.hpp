#pragma once

#include <string>
#include <vector>
#include <array>
#include <glm/glm.hpp>
#include "xxhash.h"

namespace MagiTech {
namespace SegmentedCreatures {

// Behavior types for segmented creatures
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

// Enhanced BehaviorParams with C++23 features
struct BehaviorParams {
    // Basic behavior
    BehaviorType behaviorType = BehaviorType::BURROWER;
    MovementPattern movementPattern = MovementPattern::SLITHER;
    CombatStyle combatStyle = CombatStyle::MELEE;
    
    // Movement parameters
    float speed = 1.0f;                    // Movement speed multiplier
    float acceleration = 2.0f;              // Acceleration rate
    float turnSpeed = 90.0f;               // Degrees per second
    float burrowSpeed = 0.5f;              // Burrowing speed multiplier
    float climbSpeed = 0.8f;               // Climbing speed multiplier
    float swimSpeed = 1.2f;                // Swimming speed multiplier
    
    // Detection and awareness
    float detectionRange = 15.0f;          // Detection radius in meters
    float attackRange = 1.5f;              // Attack range in meters
    float visionAngle = 120.0f;            // Vision cone in degrees
    float hearingRange = 12.0f;            // Hearing range in meters
    float vibrationSense = 8.0f;           // Vibration detection range
    
    // Personality and aggression
    float aggression = 0.6f;               // Attack likelihood 0-1
    float fear = 0.3f;                     // Flee likelihood 0-1
    float curiosity = 0.4f;                // Investigate likelihood 0-1
    float territorial = 0.5f;              // Defend area likelihood 0-1
    
    // Burrowing and environmental
    float burrowDepth = 2.0f;              // Maximum burrow depth
    bool climbAbility = true;              // Can climb walls/ceilings
    bool swimAbility = false;              // Can swim in water
    bool flyAbility = false;               // Can fly
    bool burrowAbility = true;             // Can dig underground
    bool surfaceAbility = true;            // Can move on surface
    
    // Social behavior
    int packSize = 1;                      // Solo or group size
    float packCohesion = 0.6f;             // How close pack stays together
    float packAggression = 0.7f;           // Pack attack coordination
    float socialDistance = 1.5f;           // Distance between pack members
    bool swarmBehavior = false;             // Swarm-like movement
    bool herdBehavior = false;             // Herd-like movement
    
    // Combat parameters
    float attackSpeed = 1.0f;              // Attacks per second
    float damageMultiplier = 1.0f;         // Damage output multiplier
    float defenseMultiplier = 1.0f;        // Damage resistance multiplier
    float venomPotency = 0.0f;             // Venom strength 0-1
    float constrictStrength = 0.0f;        // Constriction strength 0-1
    
    // Health and survival
    float maxHealth = 100.0f;              // Maximum health points
    float healthRegeneration = 0.0f;       // Health regen per second
    float stamina = 100.0f;                // Maximum stamina
    float staminaRegeneration = 8.0f;      // Stamina regen per second
    float segmentHealth = 10.0f;           // Health per segment
    
    // Environmental adaptation
    bool isNocturnal = false;              // Active at night
    bool isAquatic = false;                // Lives in water
    bool isSubterranean = true;             // Lives underground
    bool isArboreal = false;               // Lives in trees
    bool isDesertAdapted = false;          // Desert survival
    bool isColdAdapted = false;            // Cold weather survival
    
    // Advanced AI features
    bool useCover = false;                 // Use cover in combat
    bool flankEnemies = false;             // Try to flank opponents
    bool coordinateAttacks = false;        // Coordinate with pack
    bool retreatWhenHurt = true;           // Retreat when low health
    bool callForHelp = false;              // Call pack for assistance
    bool useAmbushTactics = false;         // Use ambush strategies
    
    // Generation settings
    uint32_t seed = 0;                     // Random seed (0 = auto)
    float aiComplexity = 1.0f;             // AI complexity multiplier
    bool adaptiveBehavior = true;           // Learn from encounters
    bool proceduralVariation = true;       // Add random behavior variations
    
    // C++23 Modern hash function
    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, seed);
        
        // Hash behavior parameters
        XXH64_update(&hash_state, &behaviorType, sizeof(behaviorType));
        XXH64_update(&hash_state, &movementPattern, sizeof(movementPattern));
        XXH64_update(&hash_state, &combatStyle, sizeof(combatStyle));
        
        // Hash movement parameters
        XXH64_update(&hash_state, &speed, sizeof(speed));
        XXH64_update(&hash_state, &acceleration, sizeof(acceleration));
        XXH64_update(&hash_state, &turnSpeed, sizeof(turnSpeed));
        XXH64_update(&hash_state, &burrowSpeed, sizeof(burrowSpeed));
        XXH64_update(&hash_state, &climbSpeed, sizeof(climbSpeed));
        XXH64_update(&hash_state, &swimSpeed, sizeof(swimSpeed));
        
        // Hash detection parameters
        XXH64_update(&hash_state, &detectionRange, sizeof(detectionRange));
        XXH64_update(&hash_state, &attackRange, sizeof(attackRange));
        XXH64_update(&hash_state, &visionAngle, sizeof(visionAngle));
        XXH64_update(&hash_state, &hearingRange, sizeof(hearingRange));
        XXH64_update(&hash_state, &vibrationSense, sizeof(vibrationSense));
        
        // Hash personality parameters
        XXH64_update(&hash_state, &aggression, sizeof(aggression));
        XXH64_update(&hash_state, &fear, sizeof(fear));
        XXH64_update(&hash_state, &curiosity, sizeof(curiosity));
        XXH64_update(&hash_state, &territorial, sizeof(territorial));
        
        // Hash environmental parameters
        XXH64_update(&hash_state, &burrowDepth, sizeof(burrowDepth));
        XXH64_update(&hash_state, &climbAbility, sizeof(climbAbility));
        XXH64_update(&hash_state, &swimAbility, sizeof(swimAbility));
        XXH64_update(&hash_state, &flyAbility, sizeof(flyAbility));
        XXH64_update(&hash_state, &burrowAbility, sizeof(burrowAbility));
        XXH64_update(&hash_state, &surfaceAbility, sizeof(surfaceAbility));
        
        // Hash social parameters
        XXH64_update(&hash_state, &packSize, sizeof(packSize));
        XXH64_update(&hash_state, &packCohesion, sizeof(packCohesion));
        XXH64_update(&hash_state, &packAggression, sizeof(packAggression));
        XXH64_update(&hash_state, &socialDistance, sizeof(socialDistance));
        XXH64_update(&hash_state, &swarmBehavior, sizeof(swarmBehavior));
        XXH64_update(&hash_state, &herdBehavior, sizeof(herdBehavior));
        
        // Hash combat parameters
        XXH64_update(&hash_state, &attackSpeed, sizeof(attackSpeed));
        XXH64_update(&hash_state, &damageMultiplier, sizeof(damageMultiplier));
        XXH64_update(&hash_state, &defenseMultiplier, sizeof(defenseMultiplier));
        XXH64_update(&hash_state, &venomPotency, sizeof(venomPotency));
        XXH64_update(&hash_state, &constrictStrength, sizeof(constrictStrength));
        
        // Hash health parameters
        XXH64_update(&hash_state, &maxHealth, sizeof(maxHealth));
        XXH64_update(&hash_state, &healthRegeneration, sizeof(healthRegeneration));
        XXH64_update(&hash_state, &stamina, sizeof(stamina));
        XXH64_update(&hash_state, &staminaRegeneration, sizeof(staminaRegeneration));
        XXH64_update(&hash_state, &segmentHealth, sizeof(segmentHealth));
        
        // Hash environmental adaptation
        XXH64_update(&hash_state, &isNocturnal, sizeof(isNocturnal));
        XXH64_update(&hash_state, &isAquatic, sizeof(isAquatic));
        XXH64_update(&hash_state, &isSubterranean, sizeof(isSubterranean));
        XXH64_update(&hash_state, &isArboreal, sizeof(isArboreal));
        XXH64_update(&hash_state, &isDesertAdapted, sizeof(isDesertAdapted));
        XXH64_update(&hash_state, &isColdAdapted, sizeof(isColdAdapted));
        
        // Hash AI features
        XXH64_update(&hash_state, &useCover, sizeof(useCover));
        XXH64_update(&hash_state, &flankEnemies, sizeof(flankEnemies));
        XXH64_update(&hash_state, &coordinateAttacks, sizeof(coordinateAttacks));
        XXH64_update(&hash_state, &retreatWhenHurt, sizeof(retreatWhenHurt));
        XXH64_update(&hash_state, &callForHelp, sizeof(callForHelp));
        XXH64_update(&hash_state, &useAmbushTactics, sizeof(useAmbushTactics));
        
        // Hash generation settings
        XXH64_update(&hash_state, &seed, sizeof(seed));
        XXH64_update(&hash_state, &aiComplexity, sizeof(aiComplexity));
        XXH64_update(&hash_state, &adaptiveBehavior, sizeof(adaptiveBehavior));
        XXH64_update(&hash_state, &proceduralVariation, sizeof(proceduralVariation));
        
        return XXH64_digest(&hash_state);
    }
    
    // C++23 Modern validation
    bool isValid() const {
        return speed > 0.0f && speed <= 10.0f &&
               detectionRange > 0.0f && detectionRange <= 100.0f &&
               attackRange > 0.0f && attackRange <= 20.0f &&
               aggression >= 0.0f && aggression <= 1.0f &&
               fear >= 0.0f && fear <= 1.0f &&
               curiosity >= 0.0f && curiosity <= 1.0f &&
               territorial >= 0.0f && territorial <= 1.0f &&
               packSize >= 1 && packSize <= 50 &&
               maxHealth > 0.0f && maxHealth <= 10000.0f &&
               aiComplexity > 0.0f && aiComplexity <= 3.0f;
    }
    
    // C++23 Modern serialization helpers
    std::string toString() const {
        return "BehaviorParams{behaviorType=" + std::to_string(static_cast<int>(behaviorType)) + 
               ", speed=" + std::to_string(speed) + 
               ", detectionRange=" + std::to_string(detectionRange) + 
               ", attackRange=" + std::to_string(attackRange) + "}";
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
    AIHandle movementAI = 0;
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
               ", movementAI=" + std::to_string(movementAI) + 
               ", combatAI=" + std::to_string(combatAI) + 
               ", socialAI=" + std::to_string(socialAI) + 
               ", environmentalAI=" + std::to_string(environmentalAI) + "}";
    }
};

} // namespace SegmentedCreatures
} // namespace MagiTech
