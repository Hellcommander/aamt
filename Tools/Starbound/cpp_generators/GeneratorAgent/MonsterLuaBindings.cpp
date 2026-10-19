#include "MonsterLuaBindings.hpp"
#include "monster_assets/MonsterTypes.hpp"
#include "monster_assets/MonsterGenerators.hpp"
#include "behavior_assets/BehaviorTypes.hpp"
#include "behavior_assets/BehaviorGenerators.hpp"
#include "core/Log.hpp"
#include <chrono>
#include <future>
#include <mutex>
#include <string>
#include <thread>
#include <utility>
#include <vector>

namespace MagiTech {
namespace Monsters {

namespace {

size_t defaultThreadCount() {
    const unsigned hw = std::thread::hardware_concurrency();
    return hw > 2 ? hw / 2 : 1;
}

std::mutex& factoryMutex() {
    static std::mutex m;
    return m;
}
std::shared_ptr<MonsterGenerator>& monsterSlot() {
    static std::shared_ptr<MonsterGenerator> f;
    return f;
}
std::shared_ptr<BehaviorGenerator>& behaviorSlot() {
    static std::shared_ptr<BehaviorGenerator> f;
    return f;
}

// Requests queued by spawn_monster() and completed by poll_assets().
std::mutex& pendingMutex() {
    static std::mutex m;
    return m;
}
std::vector<std::pair<std::future<MonsterAssetBundle>, std::string>>& pendingMonsters() {
    static std::vector<std::pair<std::future<MonsterAssetBundle>, std::string>> pending;
    return pending;
}
std::vector<std::pair<std::future<BehaviorAssetBundle>, std::string>>& pendingBehaviors() {
    static std::vector<std::pair<std::future<BehaviorAssetBundle>, std::string>> pending;
    return pending;
}

template <typename Bundle>
std::vector<std::pair<Bundle, std::string>> takeReady(std::vector<std::pair<std::future<Bundle>, std::string>>& pending) {
    std::vector<std::pair<Bundle, std::string>> ready;
    for (auto it = pending.begin(); it != pending.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            try {
                ready.emplace_back(it->first.get(), it->second);
            } catch (const std::exception& e) {
                Log::error("Monster", "Asset generation failed for '{}': {}", it->second, e.what());
            }
            it = pending.erase(it);
        } else {
            ++it;
        }
    }
    return ready;
}

void reportCallbackError(const sol::protected_function_result& result, const char* callback) {
    if (!result.valid()) {
        sol::error err = result;
        Log::error("Monster", "{} failed: {}", callback, err.what());
    }
}

} // namespace

void MonsterLuaBindings::setMonsterFactory(std::shared_ptr<MonsterGenerator> factory) {
    std::lock_guard<std::mutex> lock(factoryMutex());
    monsterSlot() = std::move(factory);
}

std::shared_ptr<MonsterGenerator> MonsterLuaBindings::monsterFactory() {
    std::lock_guard<std::mutex> lock(factoryMutex());
    auto& slot = monsterSlot();
    if (!slot) {
        // No factory injected (e.g. by MainPlugin): create a default one.
        slot = std::make_shared<MonsterGenerator>();
        slot->initialize(1000, defaultThreadCount());
    }
    return slot;
}

void MonsterLuaBindings::setBehaviorFactory(std::shared_ptr<BehaviorGenerator> factory) {
    std::lock_guard<std::mutex> lock(factoryMutex());
    behaviorSlot() = std::move(factory);
}

std::shared_ptr<BehaviorGenerator> MonsterLuaBindings::behaviorFactory() {
    std::lock_guard<std::mutex> lock(factoryMutex());
    auto& slot = behaviorSlot();
    if (!slot) {
        slot = std::make_shared<BehaviorGenerator>();
        slot->initialize(256, defaultThreadCount());
    }
    return slot;
}

void MonsterLuaBindings::bind(sol::state& lua) {
    lua.new_enum("MonsterBodyType",
        "HUMANOID", BodyType::HUMANOID, "QUADRUPED", BodyType::QUADRUPED, "INSECTOID", BodyType::INSECTOID,
        "AMORPHOUS", BodyType::AMORPHOUS, "AVIAN", BodyType::AVIAN, "AQUATIC", BodyType::AQUATIC,
        "REPTILIAN", BodyType::REPTILIAN, "ARACHNID", BodyType::ARACHNID, "CEPHALOPOD", BodyType::CEPHALOPOD,
        "CRYSTALLINE", BodyType::CRYSTALLINE);
    lua.new_enum("MonsterComplexity",
        "LOW_POLY", ComplexityLevel::LOW_POLY, "MEDIUM", ComplexityLevel::MEDIUM,
        "HIGH", ComplexityLevel::HIGH, "ULTRA", ComplexityLevel::ULTRA);
    lua.new_enum("MonsterHornType",
        "NONE", HornType::NONE, "SPIKE", HornType::SPIKE, "CURVED", HornType::CURVED, "ANTLER", HornType::ANTLER,
        "CRYSTAL", HornType::CRYSTAL, "TENTACLE", HornType::TENTACLE, "SPIRAL", HornType::SPIRAL);
    lua.new_enum("MonsterTailType",
        "NONE", TailType::NONE, "TAIL", TailType::TAIL, "MULTIPLE_TAILS", TailType::MULTIPLE_TAILS,
        "SPINE", TailType::SPINE, "TENTACLE", TailType::TENTACLE, "CRYSTAL", TailType::CRYSTAL, "FLAME", TailType::FLAME);
    lua.new_enum("MonsterPatternType",
        "NONE", PatternType::NONE, "STRIPES", PatternType::STRIPES, "SPOTS", PatternType::SPOTS,
        "SCALES", PatternType::SCALES, "SKIN", PatternType::SKIN, "CRYSTAL", PatternType::CRYSTAL,
        "GLOW", PatternType::GLOW, "CAMOUFLAGE", PatternType::CAMOUFLAGE);
    lua.new_enum("MonsterAnimationProfile",
        "BEAST_BASIC", AnimationProfile::BEAST_BASIC, "PREDATOR", AnimationProfile::PREDATOR,
        "PACK_HUNTER", AnimationProfile::PACK_HUNTER, "HORROR_FLOAT", AnimationProfile::HORROR_FLOAT,
        "INSECT_SCUTTLE", AnimationProfile::INSECT_SCUTTLE, "AQUATIC_SWIM", AnimationProfile::AQUATIC_SWIM,
        "AVIAN_FLY", AnimationProfile::AVIAN_FLY, "CRYSTAL_PULSE", AnimationProfile::CRYSTAL_PULSE);
    lua.new_enum("MonsterAIProfile",
        "PASSIVE", AIProfile::PASSIVE, "NEUTRAL", AIProfile::NEUTRAL, "PREDATOR", AIProfile::PREDATOR,
        "PACK_HUNTER", AIProfile::PACK_HUNTER, "BOSS", AIProfile::BOSS, "MINION", AIProfile::MINION,
        "GUARDIAN", AIProfile::GUARDIAN, "WANDERER", AIProfile::WANDERER);
    lua.new_enum("MonsterBehaviorType",
        "PASSIVE", BehaviorType::PASSIVE, "NEUTRAL", BehaviorType::NEUTRAL, "PREDATOR", BehaviorType::PREDATOR,
        "PACK_HUNTER", BehaviorType::PACK_HUNTER, "BOSS", BehaviorType::BOSS, "MINION", BehaviorType::MINION,
        "GUARDIAN", BehaviorType::GUARDIAN, "WANDERER", BehaviorType::WANDERER,
        "SCAVENGER", BehaviorType::SCAVENGER, "HERD", BehaviorType::HERD);

    lua.new_usertype<MonsterParams>("MonsterParams",
        sol::constructors<MonsterParams()>(),
        "id", &MonsterParams::id,
        "bodyType", &MonsterParams::bodyType,
        "size", &MonsterParams::size,
        "complexity", &MonsterParams::complexity,
        "limbCount", &MonsterParams::limbCount,
        "headCount", &MonsterParams::headCount,
        "eyeCount", &MonsterParams::eyeCount,
        "wingCount", &MonsterParams::wingCount,
        "tentacleCount", &MonsterParams::tentacleCount,
        "hornType", &MonsterParams::hornType,
        "hornCount", &MonsterParams::hornCount,
        "tailType", &MonsterParams::tailType,
        "tailCount", &MonsterParams::tailCount,
        "patternType", &MonsterParams::patternType,
        "colorPrimary", &MonsterParams::colorPrimary,
        "colorSecondary", &MonsterParams::colorSecondary,
        "colorAccent", &MonsterParams::colorAccent,
        "noiseDetail", &MonsterParams::noiseDetail,
        "textureScale", &MonsterParams::textureScale,
        "materialRoughness", &MonsterParams::materialRoughness,
        "materialMetallic", &MonsterParams::materialMetallic,
        "materialEmissive", &MonsterParams::materialEmissive,
        "animationProfile", &MonsterParams::animationProfile,
        "aiProfile", &MonsterParams::aiProfile,
        "seed", &MonsterParams::seed,
        "isValid", &MonsterParams::isValid
    );

    lua.new_usertype<BehaviorParams>("MonsterBehaviorParams",
        sol::constructors<BehaviorParams()>(),
        "behaviorType", &BehaviorParams::behaviorType,
        "aggression", &BehaviorParams::aggression,
        "fear", &BehaviorParams::fear,
        "curiosity", &BehaviorParams::curiosity,
        "speed", &BehaviorParams::speed,
        "detectionRange", &BehaviorParams::detectionRange,
        "wanderRadius", &BehaviorParams::wanderRadius,
        "attackRange", &BehaviorParams::attackRange,
        "rangedAttackRange", &BehaviorParams::rangedAttackRange,
        "packSize", &BehaviorParams::packSize,
        "maxHealth", &BehaviorParams::maxHealth,
        "isValid", &BehaviorParams::isValid
    );

    lua.new_usertype<MonsterAssetBundle>("MonsterAssetBundle",
        sol::no_constructor,
        "mesh", sol::readonly(&MonsterAssetBundle::mesh),
        "texture", sol::readonly(&MonsterAssetBundle::texture),
        "skeleton", sol::readonly(&MonsterAssetBundle::skeleton),
        "anim", sol::readonly(&MonsterAssetBundle::anim),
        "ai", sol::readonly(&MonsterAssetBundle::ai),
        "normalMap", sol::readonly(&MonsterAssetBundle::normalMap),
        "roughnessMap", sol::readonly(&MonsterAssetBundle::roughnessMap),
        "metallicMap", sol::readonly(&MonsterAssetBundle::metallicMap),
        "emissiveMap", sol::readonly(&MonsterAssetBundle::emissiveMap),
        "aoMap", sol::readonly(&MonsterAssetBundle::aoMap),
        "assetPath", sol::readonly(&MonsterAssetBundle::assetPath),
        "success", [](const MonsterAssetBundle& b) { return b.result.success; },
        "error", [](const MonsterAssetBundle& b) { return b.result.errorMessage; },
        "vertexCount", [](const MonsterAssetBundle& b) { return b.result.vertexCount; },
        "triangleCount", [](const MonsterAssetBundle& b) { return b.result.triangleCount; },
        "isValid", &MonsterAssetBundle::isValid,
        "info", &MonsterAssetBundle::getInfo
    );

    lua.new_usertype<BehaviorAssetBundle>("MonsterBehaviorAssetBundle",
        sol::no_constructor,
        "ai", sol::readonly(&BehaviorAssetBundle::ai),
        "patrolAI", sol::readonly(&BehaviorAssetBundle::patrolAI),
        "combatAI", sol::readonly(&BehaviorAssetBundle::combatAI),
        "socialAI", sol::readonly(&BehaviorAssetBundle::socialAI),
        "environmentalAI", sol::readonly(&BehaviorAssetBundle::environmentalAI),
        "nodeCount", [](const BehaviorAssetBundle& b) { return b.result.behaviorNodeCount; },
        "isValid", &BehaviorAssetBundle::isValid,
        "info", &BehaviorAssetBundle::getInfo
    );

    // Queue monster + behaviour generation; results arrive through poll_assets().
    lua.set_function("spawn_monster", [](const MonsterParams& m, const BehaviorParams& b) {
        auto monsterFut = monsterFactory()->generateAsync(m);
        auto behaviorFut = behaviorFactory()->generateAsync(b);
        std::lock_guard<std::mutex> lock(pendingMutex());
        pendingMonsters().emplace_back(std::move(monsterFut), m.id);
        pendingBehaviors().emplace_back(std::move(behaviorFut), m.id);
    });

    // Blocking variants
    lua.set_function("generate_monster", [](const MonsterParams& m) { return monsterFactory()->generate(m); });
    lua.set_function("generate_monster_behavior", [](const BehaviorParams& b) { return behaviorFactory()->generate(b); });
}

void MonsterLuaBindings::poll_assets(sol::state& lua) {
    std::vector<std::pair<MonsterAssetBundle, std::string>> monsters;
    std::vector<std::pair<BehaviorAssetBundle, std::string>> behaviors;
    {
        std::lock_guard<std::mutex> lock(pendingMutex());
        monsters = takeReady(pendingMonsters());
        behaviors = takeReady(pendingBehaviors());
    }

    // Deliver outside the lock so callbacks may queue new spawns.
    sol::protected_function onMonster = lua["on_monster_assets_ready"];
    for (auto& [bundle, id] : monsters) {
        if (onMonster.valid()) {
            reportCallbackError(onMonster(id, bundle), "on_monster_assets_ready");
        } else {
            lua["print"]("Monster assets ready for: " + id);
        }
    }

    sol::protected_function onBehavior = lua["on_monster_behavior_ready"];
    for (auto& [bundle, id] : behaviors) {
        if (onBehavior.valid()) {
            reportCallbackError(onBehavior(id, bundle), "on_monster_behavior_ready");
        } else {
            lua["print"]("Behavior assets ready for: " + id);
        }
    }
}

} // namespace Monsters
} // namespace MagiTech
