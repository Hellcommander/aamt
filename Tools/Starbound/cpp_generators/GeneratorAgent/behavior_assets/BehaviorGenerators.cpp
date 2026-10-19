#include "BehaviorGenerators.hpp"
#include "core/Log.hpp"

#include <algorithm>
#include <chrono>
#include <stdexcept>
#include <string>

namespace MagiTech {
namespace Monsters {

using CreatureAssets::AssetStore;
using CreatureAssets::BehaviorNodeType;
using CreatureAssets::BehaviorState;

namespace AIGen {
namespace {

using Params = std::map<std::string, float>;

void fillBlackboard(AI& ai, const BehaviorParams& p) {
    ai.blackboard = {
        {"behaviorType", static_cast<float>(p.behaviorType)}, {"movementPattern", static_cast<float>(p.movementPattern)},
        {"combatStyle", static_cast<float>(p.combatStyle)},
        {"aggression", p.aggression}, {"fear", p.fear}, {"curiosity", p.curiosity}, {"territorial", p.territorial},
        {"speed", p.speed}, {"acceleration", p.acceleration}, {"turnSpeed", p.turnSpeed}, {"jumpHeight", p.jumpHeight},
        {"flySpeed", p.flySpeed}, {"detectionRange", p.detectionRange}, {"visionAngle", p.visionAngle},
        {"hearingRange", p.hearingRange}, {"memoryDuration", p.memoryDuration}, {"wanderRadius", p.wanderRadius},
        {"homeRadius", p.homeRadius}, {"patrolRadius", p.patrolRadius}, {"retreatDistance", p.retreatDistance},
        {"packSize", static_cast<float>(p.packSize)}, {"packCohesion", p.packCohesion},
        {"packAggression", p.packAggression}, {"socialDistance", p.socialDistance},
        {"attackRange", p.attackRange}, {"rangedAttackRange", p.rangedAttackRange}, {"attackSpeed", p.attackSpeed},
        {"damageMultiplier", p.damageMultiplier}, {"defenseMultiplier", p.defenseMultiplier},
        {"maxHealth", p.maxHealth}, {"healthRegeneration", p.healthRegeneration}, {"stamina", p.stamina},
        {"staminaRegeneration", p.staminaRegeneration}, {"aiComplexity", p.aiComplexity},
        {"adaptiveBehavior", p.adaptiveBehavior ? 1.0f : 0.0f}};
}

int newRoot(AI& ai, const std::string& name, const BehaviorParams& p) {
    ai.name = name;
    fillBlackboard(ai, p);
    const int root = ai.addNode(BehaviorNodeType::Selector, "root");
    ai.root = root;
    return root;
}

/** Retreat (and optionally call for help) when badly hurt. */
void addSurvival(AI& ai, int parent, const BehaviorParams& p) {
    if (!p.retreatWhenHurt) return;
    const int flee = ai.addChildNode(parent, BehaviorNodeType::Sequence, "survive");
    ai.addChildNode(flee, BehaviorNodeType::Condition, "healthBelow", {{"fraction", 0.2f + 0.3f * p.fear}});
    if (p.callForHelp) ai.addChildNode(flee, BehaviorNodeType::Action, "callForHelp", {{"range", p.hearingRange}});
    if (p.canBurrow) ai.addChildNode(flee, BehaviorNodeType::Action, "burrowEscape");
    ai.addChildNode(flee, BehaviorNodeType::Action, "retreat", {{"distance", p.retreatDistance}, {"speed", p.speed * 1.3f}});
}

int addCombat(AI& ai, int parent, const BehaviorParams& p, const std::string& name = "combat") {
    const int combat = ai.addChildNode(parent, BehaviorNodeType::Selector, name);
    const bool ranged = p.rangedAttackRange > 0.0f || p.combatStyle == CombatStyle::RANGED || p.combatStyle == CombatStyle::MAGIC;
    if (p.useCover) {
        const int cover = ai.addChildNode(combat, BehaviorNodeType::Sequence, "takeCover");
        ai.addChildNode(cover, BehaviorNodeType::Condition, "underFire");
        ai.addChildNode(cover, BehaviorNodeType::Action, "moveToCover", {{"speed", p.speed}});
    }
    if (ranged) {
        const float range = p.rangedAttackRange > 0.0f ? p.rangedAttackRange : p.detectionRange * 0.6f;
        const int shoot = ai.addChildNode(combat, BehaviorNodeType::Sequence,
                                          p.combatStyle == CombatStyle::MAGIC ? "castSpell" : "rangedAttack");
        ai.addChildNode(shoot, BehaviorNodeType::Condition, "targetInRange", {{"range", range}});
        ai.addChildNode(shoot, BehaviorNodeType::Condition, "lineOfSight");
        ai.addChildNode(shoot, BehaviorNodeType::Action, p.combatStyle == CombatStyle::MAGIC ? "cast" : "fire",
                        {{"rate", p.attackSpeed}, {"damage", p.damageMultiplier}});
    }
    if (p.flankEnemies) {
        const int flank = ai.addChildNode(combat, BehaviorNodeType::Sequence, "flank");
        ai.addChildNode(flank, BehaviorNodeType::Condition, "targetEngaged");
        ai.addChildNode(flank, BehaviorNodeType::Action, "circleBehindTarget", {{"speed", p.speed}, {"turnSpeed", p.turnSpeed}});
    }
    const int melee = ai.addChildNode(combat, BehaviorNodeType::Sequence, "meleeAttack");
    ai.addChildNode(melee, BehaviorNodeType::Condition, "targetInRange", {{"range", p.attackRange}});
    ai.addChildNode(melee, BehaviorNodeType::Action,
                    p.combatStyle == CombatStyle::BERSERKER ? "frenzyStrike" : "strike",
                    {{"rate", p.attackSpeed}, {"damage", p.damageMultiplier}});
    const int chase = ai.addChildNode(combat, BehaviorNodeType::Sequence, "chase");
    ai.addChildNode(chase, BehaviorNodeType::Condition, "targetDetected",
                    {{"range", p.detectionRange}, {"visionAngle", p.visionAngle}, {"hearing", p.hearingRange},
                     {"memory", p.memoryDuration}});
    ai.addChildNode(chase, BehaviorNodeType::Condition, "aggressionRoll", {{"chance", p.aggression}});
    if (p.coordinateAttacks && p.packSize > 1) {
        ai.addChildNode(chase, BehaviorNodeType::Action, "coordinateAttack",
                        {{"packAggression", p.packAggression}, {"packSize", static_cast<float>(p.packSize)}});
    }
    ai.addChildNode(chase, BehaviorNodeType::Action, "moveToTarget", {{"speed", p.speed}, {"acceleration", p.acceleration}});
    return combat;
}

int addRoaming(AI& ai, int parent, const BehaviorParams& p, float radiusScale = 1.0f) {
    const int roam = ai.addChildNode(parent, BehaviorNodeType::Sequence, "roam");
    ai.addChildNode(roam, BehaviorNodeType::Condition, p.isNocturnal ? "isNight" : "isDay");
    ai.addChildNode(roam, BehaviorNodeType::Action, "wander", {{"radius", p.wanderRadius * radiusScale}, {"speed", p.speed * 0.6f}});
    return roam;
}

void addIdle(AI& ai, int parent, const BehaviorParams& p) {
    ai.addChildNode(parent, BehaviorNodeType::Action, "idle", {{"regen", p.healthRegeneration}, {"staminaRegen", p.staminaRegeneration}});
}

} // namespace

std::unique_ptr<AI> BehaviorTreeBuilder::createPassiveAI(const BehaviorParams& params) {
    auto ai = std::make_unique<AI>();
    const int root = newRoot(*ai, "passive", params);
    const int flee = ai->addChildNode(root, BehaviorNodeType::Sequence, "fleeThreat");
    ai->addChildNode(flee, BehaviorNodeType::Condition, "threatDetected", {{"range", params.detectionRange}, {"hearing", params.hearingRange}});
    ai->addChildNode(flee, BehaviorNodeType::Action, "flee", {{"distance", params.retreatDistance}, {"speed", params.speed * 1.4f}});
    const int graze = ai->addChildNode(root, BehaviorNodeType::Sequence, "forage");
    ai->addChildNode(graze, BehaviorNodeType::Condition, "hungry");
    ai->addChildNode(graze, BehaviorNodeType::Action, "graze", {{"radius", params.homeRadius}});
    addRoaming(*ai, root, params);
    addIdle(*ai, root, params);
    return ai;
}

std::unique_ptr<AI> BehaviorTreeBuilder::createNeutralAI(const BehaviorParams& params) {
    auto ai = std::make_unique<AI>();
    const int root = newRoot(*ai, "neutral", params);
    addSurvival(*ai, root, params);
    const int retaliate = ai->addChildNode(root, BehaviorNodeType::Sequence, "retaliate");
    ai->addChildNode(retaliate, BehaviorNodeType::Condition, "wasAttacked", {{"memory", params.memoryDuration}});
    addCombat(*ai, retaliate, params);
    addRoaming(*ai, root, params);
    addIdle(*ai, root, params);
    return ai;
}

std::unique_ptr<AI> BehaviorTreeBuilder::createPredatorAI(const BehaviorParams& params) {
    auto ai = std::make_unique<AI>();
    const int root = newRoot(*ai, "predator", params);
    addSurvival(*ai, root, params);
    addCombat(*ai, root, params, "hunt");
    const int stalk = ai->addChildNode(root, BehaviorNodeType::Sequence, "stalk");
    ai->addChildNode(stalk, BehaviorNodeType::Condition, "preyScent", {{"range", params.hearingRange * 1.5f}});
    ai->addChildNode(stalk, BehaviorNodeType::Action, "sneakToward", {{"speed", params.speed * 0.5f}});
    addRoaming(*ai, root, params, 1.5f);
    addIdle(*ai, root, params);
    return ai;
}

std::unique_ptr<AI> BehaviorTreeBuilder::createPackHunterAI(const BehaviorParams& params) {
    auto ai = std::make_unique<AI>();
    const int root = newRoot(*ai, "pack_hunter", params);
    addSurvival(*ai, root, params);
    const int packHunt = ai->addChildNode(root, BehaviorNodeType::Sequence, "packHunt");
    ai->addChildNode(packHunt, BehaviorNodeType::Condition, "packAvailable", {{"minMembers", static_cast<float>(std::max(2, params.packSize / 2))}});
    ai->addChildNode(packHunt, BehaviorNodeType::Action, "surroundTarget",
                     {{"spacing", params.socialDistance}, {"packAggression", params.packAggression}});
    addCombat(*ai, packHunt, params);
    const int follow = ai->addChildNode(root, BehaviorNodeType::Sequence, "keepWithPack");
    ai->addChildNode(follow, BehaviorNodeType::Condition, "tooFarFromPack", {{"cohesion", params.packCohesion}});
    ai->addChildNode(follow, BehaviorNodeType::Action, "followLeader", {{"distance", params.socialDistance}, {"speed", params.speed}});
    addRoaming(*ai, root, params);
    addIdle(*ai, root, params);
    return ai;
}

std::unique_ptr<AI> BehaviorTreeBuilder::createBossAI(const BehaviorParams& params) {
    auto ai = std::make_unique<AI>();
    const int root = newRoot(*ai, "boss", params);
    const int enrage = ai->addChildNode(root, BehaviorNodeType::Sequence, "enrage");
    ai->addChildNode(enrage, BehaviorNodeType::Condition, "healthBelow", {{"fraction", 0.3f}});
    ai->addChildNode(enrage, BehaviorNodeType::Condition, "notEnraged");
    ai->addChildNode(enrage, BehaviorNodeType::Action, "enrage", {{"damageMultiplier", params.damageMultiplier * 1.5f}, {"speed", params.speed * 1.25f}});
    const int summon = ai->addChildNode(root, BehaviorNodeType::Sequence, "summonMinions");
    ai->addChildNode(summon, BehaviorNodeType::Condition, "cooldownReady", {{"cooldown", 20.0f}});
    ai->addChildNode(summon, BehaviorNodeType::Action, "summon", {{"count", static_cast<float>(std::max(2, params.packSize))}});
    const int slam = ai->addChildNode(root, BehaviorNodeType::Sequence, "areaAttack");
    ai->addChildNode(slam, BehaviorNodeType::Condition, "targetsNearby", {{"range", params.attackRange * 2.0f}, {"count", 2.0f}});
    ai->addChildNode(slam, BehaviorNodeType::Action, "groundSlam", {{"radius", params.attackRange * 2.0f}, {"damage", params.damageMultiplier * 2.0f}});
    addCombat(*ai, root, params);
    ai->addChildNode(root, BehaviorNodeType::Action, "holdArena", {{"radius", params.homeRadius}});
    return ai;
}

std::unique_ptr<AI> BehaviorTreeBuilder::createMinionAI(const BehaviorParams& params) {
    auto ai = std::make_unique<AI>();
    const int root = newRoot(*ai, "minion", params);
    const int guard = ai->addChildNode(root, BehaviorNodeType::Sequence, "defendMaster");
    ai->addChildNode(guard, BehaviorNodeType::Condition, "masterUnderAttack");
    addCombat(*ai, guard, params);
    addCombat(*ai, root, params, "attackMasterTarget");
    const int follow = ai->addChildNode(root, BehaviorNodeType::Sequence, "followMaster");
    ai->addChildNode(follow, BehaviorNodeType::Condition, "masterTooFar", {{"distance", params.socialDistance * 2.0f}});
    ai->addChildNode(follow, BehaviorNodeType::Action, "returnToMaster", {{"speed", params.speed * 1.2f}});
    addIdle(*ai, root, params);
    return ai;
}

std::unique_ptr<AI> BehaviorTreeBuilder::createGuardianAI(const BehaviorParams& params) {
    auto ai = std::make_unique<AI>();
    const int root = newRoot(*ai, "guardian", params);
    const int defend = ai->addChildNode(root, BehaviorNodeType::Sequence, "defendTerritory");
    ai->addChildNode(defend, BehaviorNodeType::Condition, "intruderInTerritory", {{"radius", params.homeRadius + params.patrolRadius}});
    addCombat(*ai, defend, params);
    const int home = ai->addChildNode(root, BehaviorNodeType::Sequence, "returnHome");
    ai->addChildNode(home, BehaviorNodeType::Condition, "outsideHome", {{"radius", params.homeRadius}});
    ai->addChildNode(home, BehaviorNodeType::Action, "moveHome", {{"speed", params.speed}});
    ai->addChildNode(root, BehaviorNodeType::Action, "patrolPerimeter", {{"radius", params.patrolRadius}, {"speed", params.speed * 0.5f}});
    return ai;
}

std::unique_ptr<AI> BehaviorTreeBuilder::createWandererAI(const BehaviorParams& params) {
    auto ai = std::make_unique<AI>();
    const int root = newRoot(*ai, "wanderer", params);
    if (params.fear > params.aggression) {
        const int avoid = ai->addChildNode(root, BehaviorNodeType::Sequence, "avoidThreat");
        ai->addChildNode(avoid, BehaviorNodeType::Condition, "threatDetected", {{"range", params.detectionRange}});
        ai->addChildNode(avoid, BehaviorNodeType::Action, "flee", {{"distance", params.retreatDistance}, {"speed", params.speed}});
    } else {
        const int defend = ai->addChildNode(root, BehaviorNodeType::Sequence, "selfDefence");
        ai->addChildNode(defend, BehaviorNodeType::Condition, "wasAttacked", {{"memory", params.memoryDuration}});
        addCombat(*ai, defend, params);
    }
    const int investigate = ai->addChildNode(root, BehaviorNodeType::Sequence, "investigate");
    ai->addChildNode(investigate, BehaviorNodeType::Condition, "pointOfInterest", {{"range", params.detectionRange}});
    ai->addChildNode(investigate, BehaviorNodeType::Condition, "curiosityRoll", {{"chance", params.curiosity}});
    ai->addChildNode(investigate, BehaviorNodeType::Action, "investigate", {{"speed", params.speed * 0.7f}});
    addRoaming(*ai, root, params, 2.0f);
    addIdle(*ai, root, params);
    return ai;
}

void StateMachineBuilder::addPatrolState(std::unique_ptr<AI>& ai, const BehaviorParams& params) {
    const int patrol = ai->addNode(BehaviorNodeType::Sequence, "patrolState");
    ai->addChildNode(patrol, BehaviorNodeType::Action, "patrol", {{"radius", params.patrolRadius}, {"speed", params.speed * 0.6f}});
    ai->addChildNode(patrol, BehaviorNodeType::Action, "lookAround", {{"visionAngle", params.visionAngle}});
    auto& state = ai->addState("patrol", patrol);
    state.transitions = {{"targetDetected", params.aggression >= params.fear ? "combat" : "flee"},
                         {"farFromHome", "patrol"}};
}

void StateMachineBuilder::addCombatState(std::unique_ptr<AI>& ai, const BehaviorParams& params) {
    const int holder = ai->addNode(BehaviorNodeType::Selector, "combatState");
    addCombat(*ai, holder, params);
    auto& combat = ai->addState("combat", holder);
    combat.transitions = {{"targetLost", "patrol"}};
    if (params.retreatWhenHurt) {
        combat.transitions.push_back({"healthLow", "flee"});
        const int flee = ai->addNode(BehaviorNodeType::Sequence, "fleeState");
        if (params.callForHelp) ai->addChildNode(flee, BehaviorNodeType::Action, "callForHelp", {{"range", params.hearingRange}});
        ai->addChildNode(flee, BehaviorNodeType::Action, "retreat", {{"distance", params.retreatDistance}, {"speed", params.speed * 1.3f}});
        ai->addState("flee", flee).transitions = {{"safe", "patrol"}, {"cornered", "combat"}};
    }
}

void StateMachineBuilder::addSocialState(std::unique_ptr<AI>& ai, const BehaviorParams& params) {
    const int social = ai->addNode(BehaviorNodeType::Parallel, "socialState");
    ai->addChildNode(social, BehaviorNodeType::Action, "keepFormation",
                     {{"cohesion", params.packCohesion}, {"spacing", params.socialDistance}});
    ai->addChildNode(social, BehaviorNodeType::Action, "shareTargets", {{"packSize", static_cast<float>(params.packSize)}});
    if (params.callForHelp) ai->addChildNode(social, BehaviorNodeType::Action, "answerCalls", {{"range", params.hearingRange}});
    ai->addState("social", social).transitions = {{"regrouped", "patrol"}, {"packTargetAssigned", "combat"}};
    if (BehaviorState* patrol = ai->findState("patrol")) patrol->transitions.push_back({"packScattered", "social"});
}

void StateMachineBuilder::addEnvironmentalState(std::unique_ptr<AI>& ai, const BehaviorParams& params) {
    const int env = ai->addNode(BehaviorNodeType::Selector, "environmentState");
    if (params.canSwim || params.isAquatic) {
        const int water = ai->addChildNode(env, BehaviorNodeType::Sequence, "water");
        ai->addChildNode(water, BehaviorNodeType::Condition, params.isAquatic ? "outOfWater" : "inWater");
        ai->addChildNode(water, BehaviorNodeType::Action, params.isAquatic ? "seekWater" : "swim", {{"speed", params.speed}});
    }
    if (params.canFly) {
        const int fly = ai->addChildNode(env, BehaviorNodeType::Sequence, "flight");
        ai->addChildNode(fly, BehaviorNodeType::Condition, "obstacleOrHazardBelow");
        ai->addChildNode(fly, BehaviorNodeType::Action, "takeOff", {{"flySpeed", params.flySpeed}});
    }
    if (params.canClimb) {
        const int climb = ai->addChildNode(env, BehaviorNodeType::Sequence, "climb");
        ai->addChildNode(climb, BehaviorNodeType::Condition, "wallAhead");
        ai->addChildNode(climb, BehaviorNodeType::Action, "climbWall", {{"speed", params.speed * 0.5f}});
    }
    if (params.canBurrow) {
        const int burrow = ai->addChildNode(env, BehaviorNodeType::Sequence, "burrow");
        ai->addChildNode(burrow, BehaviorNodeType::Condition, "softGround");
        ai->addChildNode(burrow, BehaviorNodeType::Action, "burrowMove", {{"speed", params.speed * 0.4f}});
    }
    const int shelter = ai->addChildNode(env, BehaviorNodeType::Sequence, "shelter");
    ai->addChildNode(shelter, BehaviorNodeType::Condition, params.isNocturnal ? "isDay" : "isNight");
    ai->addChildNode(shelter, BehaviorNodeType::Action, "rest", {{"radius", params.homeRadius}});
    ai->addState("environment", env).transitions = {{"safe", "patrol"}, {"targetDetected", "combat"}};
    if (BehaviorState* patrol = ai->findState("patrol")) patrol->transitions.push_back({"environmentHazard", "environment"});
}

std::unique_ptr<AI> createAI(const BehaviorParams& params) {
    std::unique_ptr<AI> ai;
    switch (params.behaviorType) {
        case BehaviorType::PASSIVE:     ai = BehaviorTreeBuilder::createPassiveAI(params); break;
        case BehaviorType::NEUTRAL:     ai = BehaviorTreeBuilder::createNeutralAI(params); break;
        case BehaviorType::PREDATOR:    ai = BehaviorTreeBuilder::createPredatorAI(params); break;
        case BehaviorType::PACK_HUNTER: ai = BehaviorTreeBuilder::createPackHunterAI(params); break;
        case BehaviorType::BOSS:        ai = BehaviorTreeBuilder::createBossAI(params); break;
        case BehaviorType::MINION:      ai = BehaviorTreeBuilder::createMinionAI(params); break;
        case BehaviorType::GUARDIAN:    ai = BehaviorTreeBuilder::createGuardianAI(params); break;
        case BehaviorType::WANDERER:    ai = BehaviorTreeBuilder::createWandererAI(params); break;
        case BehaviorType::SCAVENGER: {
            ai = BehaviorTreeBuilder::createWandererAI(params);
            ai->name = "scavenger";
            const int scavenge = ai->addNode(BehaviorNodeType::Sequence, "scavenge");
            ai->addChildNode(scavenge, BehaviorNodeType::Condition, "carrionNearby", {{"range", params.detectionRange}});
            ai->addChildNode(scavenge, BehaviorNodeType::Action, "feed", {{"speed", params.speed}});
            // Scavenging takes priority right after self-preservation.
            auto& children = ai->nodes[static_cast<size_t>(ai->root)].children;
            children.insert(children.begin() + std::min<size_t>(1, children.size()), scavenge);
            break;
        }
        case BehaviorType::HERD: {
            ai = BehaviorTreeBuilder::createPassiveAI(params);
            ai->name = "herd";
            const int herd = ai->addNode(BehaviorNodeType::Sequence, "stayWithHerd");
            ai->addChildNode(herd, BehaviorNodeType::Condition, "tooFarFromHerd", {{"cohesion", params.packCohesion}});
            ai->addChildNode(herd, BehaviorNodeType::Action, "moveToHerdCentre", {{"spacing", params.socialDistance}});
            auto& children = ai->nodes[static_cast<size_t>(ai->root)].children;
            children.insert(children.begin() + std::min<size_t>(1, children.size()), herd);
            break;
        }
    }
    if (!ai) ai = BehaviorTreeBuilder::createNeutralAI(params);

    StateMachineBuilder::addPatrolState(ai, params);
    if (params.behaviorType != BehaviorType::PASSIVE && params.behaviorType != BehaviorType::HERD && params.aggression > 0.0f) {
        StateMachineBuilder::addCombatState(ai, params);
    } else {
        const int flee = ai->addNode(BehaviorNodeType::Action, "fleeState", {{"distance", params.retreatDistance}, {"speed", params.speed * 1.4f}});
        ai->addState("flee", flee).transitions = {{"safe", "patrol"}};
    }
    if (params.packSize > 1 || params.behaviorType == BehaviorType::HERD) StateMachineBuilder::addSocialState(ai, params);
    if (params.canSwim || params.canFly || params.canClimb || params.canBurrow || params.isAquatic || params.isNocturnal) {
        StateMachineBuilder::addEnvironmentalState(ai, params);
    }
    ai->initialState = "patrol";
    return ai;
}

BehaviorParams presetFor(AIProfile profile) {
    BehaviorParams b;
    switch (profile) {
        case AIProfile::PASSIVE:
            b.behaviorType = BehaviorType::PASSIVE;
            b.aggression = 0.0f; b.fear = 0.8f; b.curiosity = 0.4f; b.territorial = 0.0f;
            b.combatStyle = CombatStyle::STEALTH;
            break;
        case AIProfile::NEUTRAL:
            b.behaviorType = BehaviorType::NEUTRAL;
            b.aggression = 0.4f; b.fear = 0.4f; b.territorial = 0.5f;
            break;
        case AIProfile::PREDATOR:
            b.behaviorType = BehaviorType::PREDATOR;
            b.aggression = 0.85f; b.fear = 0.15f; b.speed = 1.4f; b.detectionRange = 25.0f;
            b.flankEnemies = true;
            break;
        case AIProfile::PACK_HUNTER:
            b.behaviorType = BehaviorType::PACK_HUNTER;
            b.aggression = 0.75f; b.packSize = 5; b.packCohesion = 0.85f; b.packAggression = 0.9f;
            b.coordinateAttacks = true; b.callForHelp = true; b.flankEnemies = true;
            break;
        case AIProfile::BOSS:
            b.behaviorType = BehaviorType::BOSS;
            b.aggression = 1.0f; b.fear = 0.0f; b.maxHealth = 2500.0f; b.damageMultiplier = 2.0f;
            b.defenseMultiplier = 1.8f; b.retreatWhenHurt = false; b.combatStyle = CombatStyle::TACTICAL;
            b.packSize = 4; b.aiComplexity = 2.5f; b.detectionRange = 40.0f; b.homeRadius = 20.0f;
            break;
        case AIProfile::MINION:
            b.behaviorType = BehaviorType::MINION;
            b.aggression = 0.7f; b.maxHealth = 40.0f; b.coordinateAttacks = true; b.retreatWhenHurt = false;
            b.packSize = 4; b.socialDistance = 1.5f;
            break;
        case AIProfile::GUARDIAN:
            b.behaviorType = BehaviorType::GUARDIAN;
            b.aggression = 0.6f; b.territorial = 1.0f; b.homeRadius = 8.0f; b.patrolRadius = 12.0f;
            b.combatStyle = CombatStyle::TANK; b.defenseMultiplier = 1.5f; b.retreatWhenHurt = false;
            break;
        case AIProfile::WANDERER:
            b.behaviorType = BehaviorType::WANDERER;
            b.aggression = 0.3f; b.fear = 0.3f; b.curiosity = 0.8f; b.wanderRadius = 30.0f;
            break;
    }
    return b;
}

AIHandle build(const BehaviorParams& params) {
    auto ai = createAI(params);
    return AssetStore::instance().addBehavior(std::move(*ai));
}

} // namespace AIGen

// ============================================================================ BehaviorGenerator
BehaviorGenerator::~BehaviorGenerator() { shutdown(); }

void BehaviorGenerator::initialize(size_t cacheSize, size_t numThreads) {
    if (m_initialized) return;
    m_cache = std::make_unique<ConcurrentLRUCache<uint64_t, BehaviorAssetBundle>>(cacheSize == 0 ? 1 : cacheSize);
    m_threadPool = std::make_unique<GeneratorTaskPool>(numThreads);
    m_initialized = true;
}

void BehaviorGenerator::shutdown() {
    if (!m_initialized) return;
    if (m_threadPool) m_threadPool->stop();
    m_initialized = false;
}

std::future<BehaviorAssetBundle> BehaviorGenerator::generateAsync(const BehaviorParams& params) {
    if (!m_initialized) initialize();
    if (auto hit = m_cache->find(params.hashKey())) {
        std::promise<BehaviorAssetBundle> ready;
        ready.set_value(*hit);
        return ready.get_future();
    }
    return m_threadPool->enqueue([this, params] { return generate(params); });
}

BehaviorAssetBundle BehaviorGenerator::generate(const BehaviorParams& params) {
    if (!m_initialized) initialize();
    const uint64_t key = params.hashKey();
    if (auto hit = m_cache->find(key)) return *hit;
    BehaviorAssetBundle bundle = generateBehaviorAssets(params);
    if (bundle.result.success) m_cache->insert(key, bundle);
    return bundle;
}

void BehaviorGenerator::clearCache() {
    if (m_cache) m_cache->clear();
}

size_t BehaviorGenerator::getCacheSize() const { return m_cache ? m_cache->size() : 0; }
double BehaviorGenerator::getCacheHitRate() const { return m_cache ? m_cache->getHitRate() : 0.0; }

BehaviorAssetBundle BehaviorGenerator::generateBehaviorAssets(const BehaviorParams& params) {
    const auto start = std::chrono::steady_clock::now();
    BehaviorAssetBundle bundle;
    bundle.params = params;
    bundle.creationTime = std::chrono::system_clock::now();
    bundle.assetPath = "behaviors/" + std::to_string(params.hashKey());
    try {
        if (!params.isValid()) throw std::invalid_argument("invalid BehaviorParams: " + params.toString());
        auto& store = AssetStore::instance();
        bundle.ai = AIGen::build(params);

        // Focused state machines the runtime can swap in for specific situations.
        auto storeState = [&store, &params](const char* name, void (*addState)(std::unique_ptr<AI>&, const BehaviorParams&)) {
            auto ai = std::make_unique<AI>();
            ai->name = name;
            AIGen::fillBlackboard(*ai, params);
            addState(ai, params);
            return store.addBehavior(std::move(*ai));
        };
        bundle.patrolAI = storeState("patrol", &AIGen::StateMachineBuilder::addPatrolState);
        bundle.combatAI = storeState("combat", &AIGen::StateMachineBuilder::addCombatState);
        bundle.socialAI = storeState("social", &AIGen::StateMachineBuilder::addSocialState);
        bundle.environmentalAI = storeState("environment", &AIGen::StateMachineBuilder::addEnvironmentalState);

        if (auto ai = store.behavior(bundle.ai)) {
            bundle.result.behaviorNodeCount = static_cast<uint32_t>(ai->nodes.size());
            bundle.result.decisionTreeDepth = static_cast<uint32_t>(ai->depth());
            bundle.result.stateMachineStates = static_cast<uint32_t>(ai->states.size());
            bundle.result.memoryUsage = ai->nodes.size() * sizeof(CreatureAssets::BehaviorNode);
        }
        bundle.result.success = bundle.isValid();
    } catch (const std::exception& e) {
        bundle.result.success = false;
        bundle.result.errorMessage = e.what();
        Log::error("Behavior", "Behavior generation failed: {}", e.what());
    }
    bundle.result.generationTime = std::chrono::duration<float>(std::chrono::steady_clock::now() - start).count();
    return bundle;
}

} // namespace Monsters
} // namespace MagiTech
