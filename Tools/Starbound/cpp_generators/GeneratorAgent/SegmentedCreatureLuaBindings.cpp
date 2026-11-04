#include "SegmentedCreatureLuaBindings.hpp"
#include "SegmentedCreatureParams.hpp"
#include "ProceduralFactory.hpp"
#include "MonsterCreatureAssets.hpp"
#include "core/Log.hpp"
#include <sol/sol.hpp>
#include <chrono>
#include <fstream>
#include <future>
#include <mutex>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>
#include <tuple>
#include <vector>

namespace MagiTech {
namespace SegmentedCreatures {

namespace {

constexpr size_t kDefaultCacheSize = 256;

size_t defaultThreadCount() {
    const unsigned hw = std::thread::hardware_concurrency();
    return hw > 2 ? hw / 2 : 1;
}

std::mutex& factoryMutex() {
    static std::mutex m;
    return m;
}
std::shared_ptr<SegmentedCreatureFactory>& creatureSlot() {
    static std::shared_ptr<SegmentedCreatureFactory> f;
    return f;
}
std::shared_ptr<BehaviorFactory>& behaviorSlot() {
    static std::shared_ptr<BehaviorFactory> f;
    return f;
}

// Requests queued by request_segmented_creature() and completed by poll_assets().
struct PendingCreature {
    std::string id;
    std::future<AssetBundle> creature;
    std::future<AssetBundle> behavior;
};
std::mutex& pendingMutex() {
    static std::mutex m;
    return m;
}
std::vector<PendingCreature>& pendingCreatures() {
    static std::vector<PendingCreature> pending;
    return pending;
}

template <typename T>
auto metadataProperty() {
    return sol::property(
        [](const T& p) { return sol::as_table(p.metadata); },
        [](T& p, const sol::table& t) {
            p.metadata.clear();
            for (const auto& [k, v] : t) {
                p.metadata[k.as<std::string>()] = v.as<std::string>();
            }
        });
}

template <typename T>
std::vector<T> paramsFromTable(const sol::table& table) {
    std::vector<T> params;
    params.reserve(table.size());
    for (size_t i = 1; i <= table.size(); ++i) {
        params.push_back(table.get<T>(i));
    }
    return params;
}

nlohmann::json readJsonFile(const std::string& filePath) {
    std::ifstream file(filePath);
    if (!file.is_open()) {
        throw std::runtime_error("Could not open file: " + filePath);
    }
    std::stringstream buffer;
    buffer << file.rdbuf();
    return nlohmann::json::parse(buffer.str());
}

bool writeJsonFile(const nlohmann::json& json, const std::string& filePath) {
    std::ofstream file(filePath);
    if (!file.is_open()) return false;
    file << json.dump(2);
    return static_cast<bool>(file);
}

bool isReady(std::future<AssetBundle>& f) {
    return f.valid() && f.wait_for(std::chrono::seconds(0)) == std::future_status::ready;
}

template <typename Factory>
sol::table batchToTable(Factory& factory, const sol::table& params, sol::this_state s) {
    using Params = std::conditional_t<std::is_same_v<Factory, SegmentedCreatureFactory>, SegmentedCreatureParams, BehaviorParams>;
    sol::state_view lua(s);
    sol::table result = lua.create_table();
    auto futures = factory.generateBatch(paramsFromTable<Params>(params));
    for (size_t i = 0; i < futures.size(); ++i) {
        result[i + 1] = std::move(futures[i]);
    }
    return result;
}

} // namespace

// ---------------------------------------------------------------------------- factories
void SegmentedCreatureLuaBindings::setCreatureFactory(std::shared_ptr<SegmentedCreatureFactory> factory) {
    std::lock_guard<std::mutex> lock(factoryMutex());
    creatureSlot() = std::move(factory);
}

std::shared_ptr<SegmentedCreatureFactory> SegmentedCreatureLuaBindings::creatureFactory() {
    std::lock_guard<std::mutex> lock(factoryMutex());
    auto& slot = creatureSlot();
    if (!slot) {
        // No factory injected (e.g. by MainPlugin): create a default one.
        slot = std::make_shared<SegmentedCreatureFactory>();
        slot->initialize(kDefaultCacheSize, defaultThreadCount());
    }
    return slot;
}

void SegmentedCreatureLuaBindings::setBehaviorFactory(std::shared_ptr<BehaviorFactory> factory) {
    std::lock_guard<std::mutex> lock(factoryMutex());
    behaviorSlot() = std::move(factory);
}

std::shared_ptr<BehaviorFactory> SegmentedCreatureLuaBindings::behaviorFactory() {
    std::lock_guard<std::mutex> lock(factoryMutex());
    auto& slot = behaviorSlot();
    if (!slot) {
        slot = std::make_shared<BehaviorFactory>();
        slot->initialize(kDefaultCacheSize, defaultThreadCount());
    }
    return slot;
}

// ---------------------------------------------------------------------------- bind
void SegmentedCreatureLuaBindings::bind(sol::state& lua) {
    // Bind parameter structures
    bindParameterStructs(lua);

    // Bind factory functions
    bindFactoryFunctions(lua);

    // Bind utility functions
    bindUtilityFunctions(lua);

    // Bind global factory instances
    bindGlobalFactories(lua);
}

void SegmentedCreatureLuaBindings::bindParameterStructs(sol::state& lua) {
    // Bind SegmentedCreatureParams
    auto creatureType = lua.new_usertype<SegmentedCreatureParams>("SegmentedCreatureParams",
        // Constructor
        sol::constructors<SegmentedCreatureParams()>(),

        // Basic properties
        "id", &SegmentedCreatureParams::id,
        "segmentCount", &SegmentedCreatureParams::segmentCount,
        "segmentLength", &SegmentedCreatureParams::segmentLength,
        "taperProfile", &SegmentedCreatureParams::taperProfile,
        "segmentRadius", &SegmentedCreatureParams::segmentRadius,
        "segmentType", &SegmentedCreatureParams::segmentType,
        "headType", &SegmentedCreatureParams::headType,
        "tailType", &SegmentedCreatureParams::tailType,
        "articulationStiffness", &SegmentedCreatureParams::articulationStiffness,
        "noiseDetail", &SegmentedCreatureParams::noiseDetail,
        "armorPlates", &SegmentedCreatureParams::armorPlates,
        "plateDetailLevel", &SegmentedCreatureParams::plateDetailLevel,
        "colorPrimary", &SegmentedCreatureParams::colorPrimary,
        "colorSecondary", &SegmentedCreatureParams::colorSecondary,
        "materialRoughness", &SegmentedCreatureParams::materialRoughness,
        "materialMetallic", &SegmentedCreatureParams::materialMetallic,
        "animationProfile", &SegmentedCreatureParams::animationProfile,
        "aiProfile", &SegmentedCreatureParams::aiProfile,
        "customTaperCurve", &SegmentedCreatureParams::customTaperCurve,

        // Additional properties
        "segmentSpacing", &SegmentedCreatureParams::segmentSpacing,
        "enableJoints", &SegmentedCreatureParams::enableJoints,
        "jointFlexibility", &SegmentedCreatureParams::jointFlexibility,
        "enableArmor", &SegmentedCreatureParams::enableArmor,
        "armorThickness", &SegmentedCreatureParams::armorThickness,
        "enableSpikes", &SegmentedCreatureParams::enableSpikes,
        "spikeCount", &SegmentedCreatureParams::spikeCount,
        "spikeLength", &SegmentedCreatureParams::spikeLength,

        // Metadata
        "description", &SegmentedCreatureParams::description,
        "tags", &SegmentedCreatureParams::tags,
        "metadata", metadataProperty<SegmentedCreatureParams>(),

        // Performance settings
        "enableCaching", &SegmentedCreatureParams::enableCaching,
        "enableHotReload", &SegmentedCreatureParams::enableHotReload,
        "enableParallelProcessing", &SegmentedCreatureParams::enableParallelProcessing,

        // Methods
        "hashKey", &SegmentedCreatureParams::hashKey,
        "isValid", &SegmentedCreatureParams::isValid,
        "toString", &SegmentedCreatureParams::toString
    );

    // Head / tail, physics, appearance and generation settings
    creatureType["name"] = &SegmentedCreatureParams::name;
    creatureType["headScale"] = &SegmentedCreatureParams::headScale;
    creatureType["tailScale"] = &SegmentedCreatureParams::tailScale;
    creatureType["headSegmentCount"] = &SegmentedCreatureParams::headSegmentCount;
    creatureType["tailSegmentCount"] = &SegmentedCreatureParams::tailSegmentCount;
    creatureType["jointLimit"] = &SegmentedCreatureParams::jointLimit;
    creatureType["segmentMass"] = &SegmentedCreatureParams::segmentMass;
    creatureType["segmentDensity"] = &SegmentedCreatureParams::segmentDensity;
    creatureType["segmentFriction"] = &SegmentedCreatureParams::segmentFriction;
    creatureType["segmentRestitution"] = &SegmentedCreatureParams::segmentRestitution;
    creatureType["colorAccent"] = &SegmentedCreatureParams::colorAccent;
    creatureType["colorVariation"] = &SegmentedCreatureParams::colorVariation;
    creatureType["materialEmissive"] = &SegmentedCreatureParams::materialEmissive;
    creatureType["materialTransparency"] = &SegmentedCreatureParams::materialTransparency;
    creatureType["plateSpacing"] = &SegmentedCreatureParams::plateSpacing;
    creatureType["plateOverlap"] = &SegmentedCreatureParams::plateOverlap;
    creatureType["gpuAccelerated"] = &SegmentedCreatureParams::gpuAccelerated;
    creatureType["simdEnabled"] = &SegmentedCreatureParams::simdEnabled;
    creatureType["adaptiveLOD"] = &SegmentedCreatureParams::adaptiveLOD;
    creatureType["proceduralVariation"] = &SegmentedCreatureParams::proceduralVariation;
    creatureType["dynamicSegments"] = &SegmentedCreatureParams::dynamicSegments;
    creatureType["damageableSegments"] = &SegmentedCreatureParams::damageableSegments;
    creatureType["seed"] = &SegmentedCreatureParams::seed;
    creatureType["generationQuality"] = &SegmentedCreatureParams::generationQuality;
    // Names used by the former creature_assets types (same storage as armorThickness / enableCaching)
    creatureType["plateThickness"] = &SegmentedCreatureParams::armorThickness;
    creatureType["cacheEnabled"] = &SegmentedCreatureParams::enableCaching;

    // Generation statistics carried by every bundle
    lua.new_usertype<SegmentedCreatureGenerationResult>("SegmentedCreatureGenerationResult",
        sol::no_constructor,
        "success", sol::readonly(&SegmentedCreatureGenerationResult::success),
        "errorMessage", sol::readonly(&SegmentedCreatureGenerationResult::errorMessage),
        "generationTime", sol::readonly(&SegmentedCreatureGenerationResult::generationTime),
        "memoryUsage", sol::readonly(&SegmentedCreatureGenerationResult::memoryUsage),
        "vertexCount", sol::readonly(&SegmentedCreatureGenerationResult::vertexCount),
        "triangleCount", sol::readonly(&SegmentedCreatureGenerationResult::triangleCount),
        "textureSize", sol::readonly(&SegmentedCreatureGenerationResult::textureSize),
        "animationFrameCount", sol::readonly(&SegmentedCreatureGenerationResult::animationFrameCount),
        "segmentCount", sol::readonly(&SegmentedCreatureGenerationResult::segmentCount),
        "boneCount", sol::readonly(&SegmentedCreatureGenerationResult::boneCount)
    );

    // Bind BehaviorParams
    lua.new_usertype<BehaviorParams>("SegmentedCreatureBehaviorParams",
        // Constructor
        sol::constructors<BehaviorParams()>(),

        // Basic properties
        "speed", &BehaviorParams::speed,
        "detectionRange", &BehaviorParams::detectionRange,
        "attackRange", &BehaviorParams::attackRange,
        "aggression", &BehaviorParams::aggression,
        "packSize", &BehaviorParams::packSize,
        "burrowDepth", &BehaviorParams::burrowDepth,
        "climbAbility", &BehaviorParams::climbAbility,

        // Additional behavior properties
        "patrolRadius", &BehaviorParams::patrolRadius,
        "idleTime", &BehaviorParams::idleTime,
        "chaseSpeed", &BehaviorParams::chaseSpeed,
        "retreatHealth", &BehaviorParams::retreatHealth,
        "canSwim", &BehaviorParams::canSwim,
        "canFly", &BehaviorParams::canFly,
        "nocturnal", &BehaviorParams::nocturnal,
        "territorial", &BehaviorParams::territorial,
        "territorySize", &BehaviorParams::territorySize,

        // Combat properties
        "attackDamage", &BehaviorParams::attackDamage,
        "attackCooldown", &BehaviorParams::attackCooldown,
        "canRangedAttack", &BehaviorParams::canRangedAttack,
        "rangedAttackRange", &BehaviorParams::rangedAttackRange,
        "canUseAbilities", &BehaviorParams::canUseAbilities,
        "abilities", &BehaviorParams::abilities,

        // Social properties
        "packHunting", &BehaviorParams::packHunting,
        "packCohesion", &BehaviorParams::packCohesion,
        "hierarchical", &BehaviorParams::hierarchical,
        "dominanceRank", &BehaviorParams::dominanceRank,

        // Environmental properties
        "burrower", &BehaviorParams::burrower,
        "climber", &BehaviorParams::climber,
        "swimmer", &BehaviorParams::swimmer,
        "flyer", &BehaviorParams::flyer,
        "preferredTemperature", &BehaviorParams::preferredTemperature,
        "temperatureTolerance", &BehaviorParams::temperatureTolerance,

        // Metadata
        "behaviorName", &BehaviorParams::behaviorName,
        "description", &BehaviorParams::description,
        "tags", &BehaviorParams::tags,
        "metadata", metadataProperty<BehaviorParams>(),

        // Methods
        "hashKey", &BehaviorParams::hashKey
    );

    // Generated asset handles (indices into the shared creature asset store)
    lua.new_usertype<AssetBundle>("SegmentedCreatureAssetBundle",
        sol::constructors<AssetBundle()>(),
        "mesh", &AssetBundle::mesh,
        "texture", &AssetBundle::texture,
        "skeleton", &AssetBundle::skeleton,
        "anim", &AssetBundle::anim,
        "ai", &AssetBundle::ai,
        "normalMap", &AssetBundle::normalMap,
        "roughnessMap", &AssetBundle::roughnessMap,
        "metallicMap", &AssetBundle::metallicMap,
        "emissiveMap", &AssetBundle::emissiveMap,
        "aoMap", &AssetBundle::aoMap,
        "result", sol::readonly(&AssetBundle::result),
        "params", sol::readonly(&AssetBundle::params),
        "assetPath", sol::readonly(&AssetBundle::assetPath),
        "isValid", &AssetBundle::isValid,
        "isBehaviorOnly", &AssetBundle::isBehaviorOnly,
        "info", &AssetBundle::getInfo,
        "vertexCount", [](const AssetBundle& b) -> size_t {
            auto mesh = CreatureAssets::AssetStore::instance().mesh(b.mesh);
            return mesh ? mesh->vertices.size() : 0;
        },
        "triangleCount", [](const AssetBundle& b) -> size_t {
            auto mesh = CreatureAssets::AssetStore::instance().mesh(b.mesh);
            return mesh ? mesh->triangleCount() : 0;
        },
        "boneCount", [](const AssetBundle& b) -> size_t {
            auto skeleton = CreatureAssets::AssetStore::instance().skeleton(b.skeleton);
            return skeleton ? skeleton->bones.size() : 0;
        },
        "behaviorNodeCount", [](const AssetBundle& b) -> size_t {
            auto ai = CreatureAssets::AssetStore::instance().behavior(b.ai);
            return ai ? ai->nodes.size() : 0;
        },
        "release", [](const AssetBundle& b) { releaseBundle(b); }
    );

    // Futures returned by the asynchronous factory methods
    lua.new_usertype<std::future<AssetBundle>>("SegmentedCreatureBundleFuture",
        sol::no_constructor,
        "valid", [](const std::future<AssetBundle>& f) { return f.valid(); },
        "ready", [](std::future<AssetBundle>& f) { return isReady(f); },
        "get", [](std::future<AssetBundle>& f) {
            if (!f.valid()) throw std::runtime_error("future already consumed");
            return f.get();
        }
    );

    // Bind enums
    bindEnums(lua);
}

void SegmentedCreatureLuaBindings::bindEnums(sol::state& lua) {
    // TaperProfile enum
    lua.new_enum("TaperProfile",
        "NONE", TaperProfile::NONE,
        "LINEAR", TaperProfile::LINEAR,
        "EXPONENTIAL", TaperProfile::EXPONENTIAL,
        "CUSTOM_CURVE", TaperProfile::CUSTOM_CURVE,
        "BELL_CURVE", TaperProfile::BELL_CURVE,
        "STEPPED", TaperProfile::STEPPED,
        "IRREGULAR", TaperProfile::IRREGULAR
    );

    // SegmentType enum
    lua.new_enum("SegmentType",
        "CYLINDER", SegmentType::CYLINDER,
        "BOX", SegmentType::BOX,
        "HEXAGON", SegmentType::HEXAGON,
        "CUSTOM_MESH", SegmentType::CUSTOM_MESH,
        "SPHERE", SegmentType::SPHERE,
        "CAPSULE", SegmentType::CAPSULE,
        "PRISM", SegmentType::PRISM,
        "IRREGULAR", SegmentType::IRREGULAR
    );

    // HeadType enum
    lua.new_enum("HeadType",
        "SIMPLE", HeadType::SIMPLE,
        "MANDIBLE", HeadType::MANDIBLE,
        "MULTI_EYE", HeadType::MULTI_EYE,
        "HORNED", HeadType::HORNED,
        "FANGED", HeadType::FANGED,
        "TENTACLED", HeadType::TENTACLED,
        "CRYSTAL", HeadType::CRYSTAL,
        "MECHANICAL", HeadType::MECHANICAL
    );

    // TailType enum
    lua.new_enum("TailType",
        "NONE", TailType::NONE,
        "SPIKE", TailType::SPIKE,
        "FLARED", TailType::FLARED,
        "TENTACLE", TailType::TENTACLE,
        "CRYSTAL", TailType::CRYSTAL,
        "MECHANICAL", TailType::MECHANICAL,
        "BIOLUMINESCENT", TailType::BIOLUMINESCENT,
        "VENOMOUS", TailType::VENOMOUS
    );

    // AnimationProfile enum (WAVE_SLITHER is an alias of SLITHER)
    lua.new_enum("AnimationProfile",
        "SLITHER", AnimationProfile::SLITHER,
        "WAVE_SLITHER", AnimationProfile::WAVE_SLITHER,
        "CRAWL", AnimationProfile::CRAWL,
        "COIL", AnimationProfile::COIL,
        "CUSTOM", AnimationProfile::CUSTOM,
        "BURROW", AnimationProfile::BURROW,
        "SWIM", AnimationProfile::SWIM,
        "FLY", AnimationProfile::FLY,
        "CLIMB", AnimationProfile::CLIMB
    );

    // AIProfile enum
    lua.new_enum("AIProfile",
        "PASSIVE", AIProfile::PASSIVE,
        "NEUTRAL", AIProfile::NEUTRAL,
        "PREDATOR", AIProfile::PREDATOR,
        "SWARM", AIProfile::SWARM,
        "BURROWER", AIProfile::BURROWER,
        "CLIMBER", AIProfile::CLIMBER,
        "AMBUSHER", AIProfile::AMBUSHER,
        "GUARDIAN", AIProfile::GUARDIAN
    );
}

void SegmentedCreatureLuaBindings::bindFactoryFunctions(sol::state& lua) {
    // Generate creature + behaviour assets and wait for both (returns ok, creatureBundle, behaviorBundle)
    lua.set_function("spawn_segmented_creature", [](const SegmentedCreatureParams& creatureParams,
                                                   const BehaviorParams& behaviorParams) {
        try {
            auto creatureFuture = creatureFactory()->generateAsync(creatureParams);
            auto behaviorFuture = behaviorFactory()->generateAsync(behaviorParams);

            auto creatureBundle = creatureFuture.get();
            auto behaviorBundle = behaviorFuture.get();
            const bool ok = creatureBundle.result.success && behaviorBundle.result.success;
            return std::make_tuple(ok, creatureBundle, behaviorBundle);
        } catch (const std::exception& e) {
            Log::error("SegmentedCreature", "Error spawning segmented creature: {}", e.what());
            return std::make_tuple(false, AssetBundle{}, AssetBundle{});
        }
    });

    // Non-blocking variant: results are delivered by poll_assets() to on_segmented_creature_ready(id, creature, behavior)
    lua.set_function("request_segmented_creature", [](const SegmentedCreatureParams& creatureParams,
                                                     const BehaviorParams& behaviorParams) {
        PendingCreature pending;
        pending.id = creatureParams.id;
        pending.creature = creatureFactory()->generateAsync(creatureParams);
        pending.behavior = behaviorFactory()->generateAsync(behaviorParams);
        std::lock_guard<std::mutex> lock(pendingMutex());
        pendingCreatures().push_back(std::move(pending));
        return pendingCreatures().size();
    });

    // Bind individual generation functions
    lua.set_function("generate_creature_assets", [](const SegmentedCreatureParams& params) {
        try {
            return creatureFactory()->generateSync(params);
        } catch (const std::exception& e) {
            Log::error("SegmentedCreature", "Error generating creature assets: {}", e.what());
            return AssetBundle{};
        }
    });

    lua.set_function("generate_behavior_assets", [](const BehaviorParams& params) {
        try {
            return behaviorFactory()->generateSync(params);
        } catch (const std::exception& e) {
            Log::error("SegmentedCreature", "Error generating behavior assets: {}", e.what());
            return AssetBundle{};
        }
    });

    // Bind batch generation (tables of params in, tables of bundles out)
    lua.set_function("generate_creature_batch", [](const sol::table& paramTable) {
        std::vector<AssetBundle> results;
        try {
            auto futures = creatureFactory()->generateBatch(paramsFromTable<SegmentedCreatureParams>(paramTable));
            results.reserve(futures.size());
            for (auto& future : futures) {
                results.push_back(future.get());
            }
        } catch (const std::exception& e) {
            Log::error("SegmentedCreature", "Error generating creature batch: {}", e.what());
            results.clear();
        }
        return sol::as_table(std::move(results));
    });

    lua.set_function("generate_behavior_batch", [](const sol::table& paramTable) {
        std::vector<AssetBundle> results;
        try {
            auto futures = behaviorFactory()->generateBatch(paramsFromTable<BehaviorParams>(paramTable));
            results.reserve(futures.size());
            for (auto& future : futures) {
                results.push_back(future.get());
            }
        } catch (const std::exception& e) {
            Log::error("SegmentedCreature", "Error generating behavior batch: {}", e.what());
            results.clear();
        }
        return sol::as_table(std::move(results));
    });

    lua.set_function("release_segmented_creature_assets", [](const AssetBundle& bundle) { releaseBundle(bundle); });
}

void SegmentedCreatureLuaBindings::bindUtilityFunctions(sol::state& lua) {
    // Bind parameter validation
    lua.set_function("validate_creature_params", [](const SegmentedCreatureParams& params) {
        return creatureFactory()->validateParams(params);
    });

    lua.set_function("get_creature_validation_errors", [](const SegmentedCreatureParams& params) {
        return creatureFactory()->getValidationErrors(params);
    });

    lua.set_function("validate_behavior_params", [](const BehaviorParams& params) {
        return behaviorFactory()->validateParams(params);
    });

    lua.set_function("get_behavior_validation_errors", [](const BehaviorParams& params) {
        return behaviorFactory()->getValidationErrors(params);
    });

    // Bind JSON serialization
    lua.set_function("save_creature_params", [](const SegmentedCreatureParams& params, const std::string& filePath) {
        try {
            return writeJsonFile(ParamUtils::toJson(params), filePath);
        } catch (const std::exception& e) {
            Log::error("SegmentedCreature", "Error saving creature params: {}", e.what());
            return false;
        }
    });

    lua.set_function("load_creature_params", [](const std::string& filePath) {
        try {
            return ParamUtils::creatureFromJson(readJsonFile(filePath));
        } catch (const std::exception& e) {
            Log::error("SegmentedCreature", "Error loading creature params: {}", e.what());
            return SegmentedCreatureParams{};
        }
    });

    lua.set_function("save_behavior_params", [](const BehaviorParams& params, const std::string& filePath) {
        try {
            return writeJsonFile(ParamUtils::toJson(params), filePath);
        } catch (const std::exception& e) {
            Log::error("SegmentedCreature", "Error saving behavior params: {}", e.what());
            return false;
        }
    });

    lua.set_function("load_behavior_params", [](const std::string& filePath) {
        try {
            return ParamUtils::behaviorFromJson(readJsonFile(filePath));
        } catch (const std::exception& e) {
            Log::error("SegmentedCreature", "Error loading behavior params: {}", e.what());
            return BehaviorParams{};
        }
    });

    // Bind parameter conversion utilities
    lua.set_function("parse_taper_profile", [](const std::string& str) {
        return ParamUtils::parseTaperProfile(str);
    });

    lua.set_function("parse_segment_type", [](const std::string& str) {
        return ParamUtils::parseSegmentType(str);
    });

    lua.set_function("parse_head_type", [](const std::string& str) {
        return ParamUtils::parseHeadType(str);
    });

    lua.set_function("parse_tail_type", [](const std::string& str) {
        return ParamUtils::parseTailType(str);
    });

    lua.set_function("parse_animation_profile", [](const std::string& str) {
        return ParamUtils::parseAnimationProfile(str);
    });

    lua.set_function("parse_ai_profile", [](const std::string& str) {
        return ParamUtils::parseAIProfile(str);
    });

    // Bind string conversion utilities
    lua.set_function("taper_profile_to_string", [](TaperProfile profile) {
        return ParamUtils::taperProfileToString(profile);
    });

    lua.set_function("segment_type_to_string", [](SegmentType type) {
        return ParamUtils::segmentTypeToString(type);
    });

    lua.set_function("head_type_to_string", [](HeadType type) {
        return ParamUtils::headTypeToString(type);
    });

    lua.set_function("tail_type_to_string", [](TailType type) {
        return ParamUtils::tailTypeToString(type);
    });

    lua.set_function("animation_profile_to_string", [](AnimationProfile profile) {
        return ParamUtils::animationProfileToString(profile);
    });

    lua.set_function("ai_profile_to_string", [](AIProfile profile) {
        return ParamUtils::aiProfileToString(profile);
    });
}

void SegmentedCreatureLuaBindings::bindGlobalFactories(sol::state& lua) {
    lua.new_usertype<SegmentedCreatureFactory>("SegmentedCreatureFactory",
        sol::no_constructor,
        "generateAsync", [](SegmentedCreatureFactory& f, const SegmentedCreatureParams& p) { return f.generateAsync(p); },
        "generateSync", [](SegmentedCreatureFactory& f, const SegmentedCreatureParams& p) { return f.generateSync(p); },
        "generateFromJson", [](SegmentedCreatureFactory& f, const std::string& path) { return f.generateFromJson(path); },
        "generateFromParams", [](SegmentedCreatureFactory& f, const SegmentedCreatureParams& p) { return f.generateFromParams(p); },
        "generateBatch", [](SegmentedCreatureFactory& f, const sol::table& params, sol::this_state s) {
            return batchToTable(f, params, s);
        },
        "validateParams", [](SegmentedCreatureFactory& f, const SegmentedCreatureParams& p) { return f.validateParams(p); },
        "getValidationErrors", [](SegmentedCreatureFactory& f, const SegmentedCreatureParams& p) { return f.getValidationErrors(p); },
        "clearCache", [](SegmentedCreatureFactory& f) { f.clearCache(); },
        "getCacheSize", [](const SegmentedCreatureFactory& f) { return f.getCacheSize(); },
        "getCacheCapacity", [](const SegmentedCreatureFactory& f) { return f.getCacheCapacity(); },
        "getCacheHitRate", [](const SegmentedCreatureFactory& f) { return f.getCacheHitRate(); }
    );

    lua.new_usertype<BehaviorFactory>("BehaviorFactory",
        sol::no_constructor,
        "generateAsync", [](BehaviorFactory& f, const BehaviorParams& p) { return f.generateAsync(p); },
        "generateSync", [](BehaviorFactory& f, const BehaviorParams& p) { return f.generateSync(p); },
        "generateFromJson", [](BehaviorFactory& f, const std::string& path) { return f.generateFromJson(path); },
        "generateFromParams", [](BehaviorFactory& f, const BehaviorParams& p) { return f.generateFromParams(p); },
        "generateBatch", [](BehaviorFactory& f, const sol::table& params, sol::this_state s) {
            return batchToTable(f, params, s);
        },
        "validateParams", [](BehaviorFactory& f, const BehaviorParams& p) { return f.validateParams(p); },
        "getValidationErrors", [](BehaviorFactory& f, const BehaviorParams& p) { return f.getValidationErrors(p); },
        "clearCache", [](BehaviorFactory& f) { f.clearCache(); },
        "getCacheSize", [](const BehaviorFactory& f) { return f.getCacheSize(); },
        "getCacheCapacity", [](const BehaviorFactory& f) { return f.getCacheCapacity(); },
        "getCacheHitRate", [](const BehaviorFactory& f) { return f.getCacheHitRate(); }
    );

    // Global factory instances (the injected or default ones)
    lua["creatureFactory"] = creatureFactory();
    lua["behaviorFactory"] = behaviorFactory();
}

void SegmentedCreatureLuaBindings::poll_assets(sol::state& lua) {
    std::vector<PendingCreature> finished;
    {
        std::lock_guard<std::mutex> lock(pendingMutex());
        auto& pending = pendingCreatures();
        for (auto it = pending.begin(); it != pending.end();) {
            if (isReady(it->creature) && isReady(it->behavior)) {
                finished.push_back(std::move(*it));
                it = pending.erase(it);
            } else {
                ++it;
            }
        }
    }

    // Deliver outside the lock so Lua callbacks may queue new requests.
    sol::protected_function callback = lua["on_segmented_creature_ready"];
    for (auto& done : finished) {
        AssetBundle creature, behavior;
        bool ok = true;
        try {
            creature = done.creature.get();
            behavior = done.behavior.get();
            ok = creature.result.success && behavior.result.success;
            if (!ok) {
                Log::warn("SegmentedCreature", "Generation for '{}' incomplete: {}{}", done.id,
                          creature.result.errorMessage, behavior.result.errorMessage);
            }
        } catch (const std::exception& e) {
            ok = false;
            Log::error("SegmentedCreature", "Generation failed for '{}': {}", done.id, e.what());
        }
        if (callback.valid()) {
            auto result = callback(done.id, ok, creature, behavior);
            if (!result.valid()) {
                sol::error err = result;
                Log::error("SegmentedCreature", "on_segmented_creature_ready failed: {}", err.what());
            }
        } else if (ok) {
            Log::info("SegmentedCreature", "Segmented creature assets ready for: {}", done.id);
        }
    }
}

} // namespace SegmentedCreatures
} // namespace MagiTech
