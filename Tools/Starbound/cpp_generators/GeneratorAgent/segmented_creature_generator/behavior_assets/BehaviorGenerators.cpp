#include "BehaviorGenerators.hpp"
#include "MonsterCreatureAssets.hpp"
#include "core/Log.hpp"
#include <algorithm>
#include <chrono>
#include <exception>

namespace MagiTech {
namespace SegmentedCreatures {

namespace {

// Archetypes shared with the creature AI profiles map onto AIGen's presets.
std::optional<AIProfile> toAIProfile(BehaviorType type) {
    switch (type) {
        case BehaviorType::PASSIVE:  return AIProfile::PASSIVE;
        case BehaviorType::NEUTRAL:  return AIProfile::NEUTRAL;
        case BehaviorType::PREDATOR: return AIProfile::PREDATOR;
        case BehaviorType::SWARM:    return AIProfile::SWARM;
        case BehaviorType::BURROWER: return AIProfile::BURROWER;
        case BehaviorType::CLIMBER:  return AIProfile::CLIMBER;
        case BehaviorType::AMBUSHER: return AIProfile::AMBUSHER;
        case BehaviorType::GUARDIAN: return AIProfile::GUARDIAN;
        case BehaviorType::SCAVENGER:
        case BehaviorType::HERD:     return std::nullopt;
    }
    return std::nullopt;
}

const char* behaviorTypeName(BehaviorType type) {
    switch (type) {
        case BehaviorType::PASSIVE:   return "passive";
        case BehaviorType::NEUTRAL:   return "neutral";
        case BehaviorType::PREDATOR:  return "predator";
        case BehaviorType::SWARM:     return "swarm";
        case BehaviorType::BURROWER:  return "burrower";
        case BehaviorType::CLIMBER:   return "climber";
        case BehaviorType::AMBUSHER:  return "ambusher";
        case BehaviorType::GUARDIAN:  return "guardian";
        case BehaviorType::SCAVENGER: return "scavenger";
        case BehaviorType::HERD:      return "herd";
    }
    return "behavior";
}

void addAbility(BehaviorParams& p, const std::string& ability) {
    if (std::find(p.abilities.begin(), p.abilities.end(), ability) == p.abilities.end()) {
        p.abilities.push_back(ability);
    }
    p.canUseAbilities = true;
}

// Accumulates statistics of one stored behaviour tree into the result.
void accumulateTreeStats(AIHandle handle, BehaviorGenerationResult& result) {
    if (handle == 0) return;
    auto tree = CreatureAssets::AssetStore::instance().behavior(handle);
    if (!tree) return;
    result.behaviorNodeCount += static_cast<uint32_t>(tree->nodes.size());
    result.stateMachineStates += static_cast<uint32_t>(tree->states.size());
    result.decisionTreeDepth = std::max(result.decisionTreeDepth, static_cast<uint32_t>(std::max(tree->depth(), 0)));
    size_t bytes = sizeof(CreatureAssets::BehaviorTreeData) + tree->name.size();
    for (const auto& node : tree->nodes) {
        bytes += sizeof(node) + node.name.size() + node.children.size() * sizeof(int) +
                 node.params.size() * (sizeof(float) + 16);
    }
    for (const auto& state : tree->states) {
        bytes += sizeof(state) + state.name.size() + state.transitions.size() * sizeof(CreatureAssets::BehaviorTransition);
    }
    result.memoryUsage += bytes;
}

BehaviorParams focused(const BehaviorParams& base, const std::string& suffix) {
    BehaviorParams p = base;
    p.behaviorName = (base.behaviorName.empty() ? std::string("behavior") : base.behaviorName) + "_" + suffix;
    return p;
}

} // namespace

BehaviorParams makeBehaviorParams(BehaviorType type, MovementPattern movement, CombatStyle combat) {
    BehaviorParams p;
    if (auto profile = toAIProfile(type)) {
        p = AIGen::presetFor(*profile);
    } else if (type == BehaviorType::SCAVENGER) {
        p = AIGen::presetFor(AIProfile::NEUTRAL);
        p.aggression = 0.25f;
        p.patrolRadius = std::max(p.patrolRadius, 30.0f);
        p.retreatHealth = 0.5f;
        p.detectionRange = std::max(p.detectionRange, 20.0f);
    } else { // HERD
        p = AIGen::presetFor(AIProfile::PASSIVE);
        p.packSize = std::max(p.packSize, 8);
        p.packCohesion = 0.9f;
        p.hierarchical = true;
        p.aggression = std::min(p.aggression, 0.2f);
    }
    p.behaviorName = behaviorTypeName(type);

    // Movement capabilities
    switch (movement) {
        case MovementPattern::SLITHER: break;
        case MovementPattern::CRAWL:   p.speed *= 0.8f; break;
        case MovementPattern::BURROW:  p.burrower = true; p.burrowDepth = std::max(p.burrowDepth, 2.0f); break;
        case MovementPattern::SWIM:    p.swimmer = true; p.canSwim = true; break;
        case MovementPattern::CLIMB:   p.climber = true; p.climbAbility = true; break;
        case MovementPattern::FLY:     p.flyer = true; p.canFly = true; p.speed *= 1.3f; break;
        case MovementPattern::COIL:    p.speed *= 0.9f; addAbility(p, "coil"); break;
        case MovementPattern::FLOAT:   p.flyer = true; p.canFly = true; p.speed *= 0.6f; break;
    }

    // Combat style
    switch (combat) {
        case CombatStyle::MELEE: break;
        case CombatStyle::RANGED:
            p.canRangedAttack = true;
            p.rangedAttackRange = std::max(p.rangedAttackRange, 8.0f);
            break;
        case CombatStyle::VENOM:
            addAbility(p, "venom");
            p.attackDamage *= 0.8f;
            break;
        case CombatStyle::CONSTRICT:
            addAbility(p, "constrict");
            p.attackCooldown *= 1.5f;
            p.attackDamage *= 1.3f;
            break;
        case CombatStyle::BURROW_ATTACK:
            addAbility(p, "burrow_strike");
            p.burrower = true;
            break;
        case CombatStyle::SWARM_ATTACK:
            p.packHunting = true;
            p.packSize = std::max(p.packSize, 4);
            break;
        case CombatStyle::AMBUSH:
            addAbility(p, "ambush");
            p.idleTime = std::max(p.idleTime, 5.0f);
            break;
        case CombatStyle::DEFENSIVE:
            p.territorial = true;
            p.aggression = std::min(p.aggression, 0.4f);
            p.retreatHealth = std::min(p.retreatHealth, 0.15f);
            break;
    }
    return p;
}

BehaviorAssetBundle buildBehaviorAssets(const BehaviorParams& params) {
    const auto start = std::chrono::steady_clock::now();

    BehaviorAssetBundle bundle;
    bundle.params = params;
    bundle.creationTime = std::chrono::system_clock::now();
    bundle.assetPath = "behaviors/segmented/" +
        (params.behaviorName.empty() ? std::to_string(params.hashKey()) : params.behaviorName);

    try {
        // Main tree
        bundle.ai = AIGen::build(params);

        // Movement-only tree: no engagement, just locomotion / patrol.
        {
            BehaviorParams p = focused(params, "movement");
            p.aggression = 0.0f;
            p.packHunting = false;
            p.canRangedAttack = false;
            bundle.movementAI = AIGen::build(p);
        }

        // Combat tree (only for creatures that fight back)
        if (params.aggression > 0.0f || params.canRangedAttack || params.territorial) {
            BehaviorParams p = focused(params, "combat");
            p.aggression = std::max(params.aggression, 0.5f);
            p.idleTime = 0.0f;
            bundle.combatAI = AIGen::build(p);
        }

        // Social tree (groups only)
        if (params.packSize > 1 || params.packHunting || params.hierarchical) {
            BehaviorParams p = focused(params, "social");
            p.packHunting = true;
            p.packSize = std::max(params.packSize, 2);
            bundle.socialAI = AIGen::build(p);
        }

        // Environmental tree (special locomotion / habitat)
        if (params.burrower || params.climber || params.swimmer || params.flyer || params.nocturnal) {
            BehaviorParams p = focused(params, "environment");
            p.aggression = 0.0f;
            bundle.environmentalAI = AIGen::build(p);
        }

        for (AIHandle h : {bundle.ai, bundle.movementAI, bundle.combatAI, bundle.socialAI, bundle.environmentalAI}) {
            accumulateTreeStats(h, bundle.result);
        }
        bundle.result.success = bundle.ai != 0;
        if (!bundle.result.success) {
            bundle.result.errorMessage = "Behaviour tree generation returned no tree";
        }
    } catch (const std::exception& e) {
        bundle.result.success = false;
        bundle.result.errorMessage = e.what();
        Log::error("SegmentedCreatures", "Behaviour generation failed for '{}': {}", params.behaviorName, e.what());
    }

    bundle.result.generationTime =
        std::chrono::duration<float>(std::chrono::steady_clock::now() - start).count();
    return bundle;
}

void releaseBehaviorAssets(const BehaviorAssetBundle& bundle) {
    auto& store = CreatureAssets::AssetStore::instance();
    for (AIHandle h : {bundle.ai, bundle.movementAI, bundle.combatAI, bundle.socialAI, bundle.environmentalAI}) {
        if (h != 0) store.releaseBehavior(h);
    }
}

} // namespace SegmentedCreatures
} // namespace MagiTech
