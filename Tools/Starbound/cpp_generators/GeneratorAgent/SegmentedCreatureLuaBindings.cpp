#include "SegmentedCreatureLuaBindings.hpp"
#include "SegmentedCreatureParams.hpp"
#include "ProceduralFactory.hpp"
#include <sol/sol.hpp>
#include <iostream>

namespace MagiTech {
namespace SegmentedCreatures {

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
    lua.new_usertype<SegmentedCreatureParams>("SegmentedCreatureParams",
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
        "metadata", &SegmentedCreatureParams::metadata,
        
        // Performance settings
        "enableCaching", &SegmentedCreatureParams::enableCaching,
        "enableHotReload", &SegmentedCreatureParams::enableHotReload,
        "enableParallelProcessing", &SegmentedCreatureParams::enableParallelProcessing,
        
        // Methods
        "hashKey", &SegmentedCreatureParams::hashKey
    );
    
    // Bind BehaviorParams
    lua.new_usertype<BehaviorParams>("BehaviorParams",
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
        "metadata", &BehaviorParams::metadata,
        
        // Methods
        "hashKey", &BehaviorParams::hashKey
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
        "CUSTOM_CURVE", TaperProfile::CUSTOM_CURVE
    );
    
    // SegmentType enum
    lua.new_enum("SegmentType",
        "CYLINDER", SegmentType::CYLINDER,
        "BOX", SegmentType::BOX,
        "HEXAGON", SegmentType::HEXAGON,
        "CUSTOM_MESH", SegmentType::CUSTOM_MESH
    );
    
    // HeadType enum
    lua.new_enum("HeadType",
        "SIMPLE", HeadType::SIMPLE,
        "MANDIBLE", HeadType::MANDIBLE,
        "MULTI_EYE", HeadType::MULTI_EYE,
        "HORNED", HeadType::HORNED
    );
    
    // TailType enum
    lua.new_enum("TailType",
        "NONE", TailType::NONE,
        "SPIKE", TailType::SPIKE,
        "FLARED", TailType::FLARED
    );
    
    // AnimationProfile enum
    lua.new_enum("AnimationProfile",
        "SLITHER", AnimationProfile::SLITHER,
        "CRAWL", AnimationProfile::CRAWL,
        "COIL", AnimationProfile::COIL,
        "CUSTOM", AnimationProfile::CUSTOM
    );
    
    // AIProfile enum
    lua.new_enum("AIProfile",
        "PASSIVE", AIProfile::PASSIVE,
        "NEUTRAL", AIProfile::NEUTRAL,
        "PREDATOR", AIProfile::PREDATOR,
        "SWARM", AIProfile::SWARM
    );
}

void SegmentedCreatureLuaBindings::bindFactoryFunctions(sol::state& lua) {
    // Bind factory functions
    lua.set_function("spawn_segmented_creature", [](const SegmentedCreatureParams& creatureParams, 
                                                   const BehaviorParams& behaviorParams) {
        try {
            // Generate creature assets
            auto creatureFuture = g_creatureFactory.generateAsync(creatureParams);
            auto behaviorFuture = g_behaviorFactory.generateAsync(behaviorParams);
            
            // Wait for both to complete
            auto creatureBundle = creatureFuture.get();
            auto behaviorBundle = behaviorFuture.get();
            
            // TODO: Create actual entity with the generated assets
            // For now, return success status
            return std::make_tuple(true, creatureBundle, behaviorBundle);
        } catch (const std::exception& e) {
            std::cerr << "Error spawning segmented creature: " << e.what() << std::endl;
            return std::make_tuple(false, AssetBundle{}, AssetBundle{});
        }
    });
    
    // Bind individual generation functions
    lua.set_function("generate_creature_assets", [](const SegmentedCreatureParams& params) {
        try {
            auto bundle = g_creatureFactory.generateSync(params);
            return bundle;
        } catch (const std::exception& e) {
            std::cerr << "Error generating creature assets: " << e.what() << std::endl;
            return AssetBundle{};
        }
    });
    
    lua.set_function("generate_behavior_assets", [](const BehaviorParams& params) {
        try {
            auto bundle = g_behaviorFactory.generateSync(params);
            return bundle;
        } catch (const std::exception& e) {
            std::cerr << "Error generating behavior assets: " << e.what() << std::endl;
            return AssetBundle{};
        }
    });
    
    // Bind batch generation
    lua.set_function("generate_creature_batch", [](const std::vector<SegmentedCreatureParams>& params) {
        try {
            auto futures = g_creatureFactory.generateBatch(params);
            std::vector<AssetBundle> results;
            results.reserve(futures.size());
            
            for (auto& future : futures) {
                results.push_back(future.get());
            }
            
            return results;
        } catch (const std::exception& e) {
            std::cerr << "Error generating creature batch: " << e.what() << std::endl;
            return std::vector<AssetBundle>{};
        }
    });
    
    lua.set_function("generate_behavior_batch", [](const std::vector<BehaviorParams>& params) {
        try {
            auto futures = g_behaviorFactory.generateBatch(params);
            std::vector<AssetBundle> results;
            results.reserve(futures.size());
            
            for (auto& future : futures) {
                results.push_back(future.get());
            }
            
            return results;
        } catch (const std::exception& e) {
            std::cerr << "Error generating behavior batch: " << e.what() << std::endl;
            return std::vector<AssetBundle>{};
        }
    });
}

void SegmentedCreatureLuaBindings::bindUtilityFunctions(sol::state& lua) {
    // Bind parameter validation
    lua.set_function("validate_creature_params", [](const SegmentedCreatureParams& params) {
        return g_creatureFactory.validateParams(params);
    });
    
    lua.set_function("get_creature_validation_errors", [](const SegmentedCreatureParams& params) {
        return g_creatureFactory.getValidationErrors(params);
    });
    
    lua.set_function("validate_behavior_params", [](const BehaviorParams& params) {
        return g_behaviorFactory.validateParams(params);
    });
    
    lua.set_function("get_behavior_validation_errors", [](const BehaviorParams& params) {
        return g_behaviorFactory.getValidationErrors(params);
    });
    
    // Bind JSON serialization
    lua.set_function("save_creature_params", [](const SegmentedCreatureParams& params, const std::string& filePath) {
        try {
            auto json = ParamUtils::toJson(params);
            std::ofstream file(filePath);
            if (file.is_open()) {
                file << json.dump(2);
                return true;
            }
            return false;
        } catch (const std::exception& e) {
            std::cerr << "Error saving creature params: " << e.what() << std::endl;
            return false;
        }
    });
    
    lua.set_function("load_creature_params", [](const std::string& filePath) {
        try {
            std::ifstream file(filePath);
            if (!file.is_open()) {
                throw std::runtime_error("Could not open file: " + filePath);
            }
            
            std::stringstream buffer;
            buffer << file.rdbuf();
            
            auto json = nlohmann::json::parse(buffer.str());
            return ParamUtils::fromJson(json);
        } catch (const std::exception& e) {
            std::cerr << "Error loading creature params: " << e.what() << std::endl;
            return SegmentedCreatureParams{};
        }
    });
    
    lua.set_function("save_behavior_params", [](const BehaviorParams& params, const std::string& filePath) {
        try {
            auto json = ParamUtils::toJson(params);
            std::ofstream file(filePath);
            if (file.is_open()) {
                file << json.dump(2);
                return true;
            }
            return false;
        } catch (const std::exception& e) {
            std::cerr << "Error saving behavior params: " << e.what() << std::endl;
            return false;
        }
    });
    
    lua.set_function("load_behavior_params", [](const std::string& filePath) {
        try {
            std::ifstream file(filePath);
            if (!file.is_open()) {
                throw std::runtime_error("Could not open file: " + filePath);
            }
            
            std::stringstream buffer;
            buffer << file.rdbuf();
            
            auto json = nlohmann::json::parse(buffer.str());
            return ParamUtils::fromJson(json);
        } catch (const std::exception& e) {
            std::cerr << "Error loading behavior params: " << e.what() << std::endl;
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
    // Bind global factory instances
    lua["creatureFactory"] = &g_creatureFactory;
    lua["behaviorFactory"] = &g_behaviorFactory;
    
    // Bind factory methods
    lua.new_usertype<SegmentedCreatureFactory>("SegmentedCreatureFactory",
        "generateAsync", &SegmentedCreatureFactory::generateAsync,
        "generateSync", &SegmentedCreatureFactory::generateSync,
        "generateFromJson", &SegmentedCreatureFactory::generateFromJson,
        "generateFromParams", &SegmentedCreatureFactory::generateFromParams,
        "generateBatch", &SegmentedCreatureFactory::generateBatch,
        "validateParams", &SegmentedCreatureFactory::validateParams,
        "getValidationErrors", &SegmentedCreatureFactory::getValidationErrors,
        "clearCache", &SegmentedCreatureFactory::clearCache,
        "getCacheSize", &SegmentedCreatureFactory::getCacheSize,
        "getCacheCapacity", &SegmentedCreatureFactory::getCacheCapacity
    );
    
    lua.new_usertype<BehaviorFactory>("BehaviorFactory",
        "generateAsync", &BehaviorFactory::generateAsync,
        "generateSync", &BehaviorFactory::generateSync,
        "generateFromJson", &BehaviorFactory::generateFromJson,
        "generateFromParams", &BehaviorFactory::generateFromParams,
        "generateBatch", &BehaviorFactory::generateBatch,
        "validateParams", &BehaviorFactory::validateParams,
        "getValidationErrors", &BehaviorFactory::getValidationErrors,
        "clearCache", &BehaviorFactory::clearCache,
        "getCacheSize", &BehaviorFactory::getCacheSize,
        "getCacheCapacity", &BehaviorFactory::getCacheCapacity
    );
}

void SegmentedCreatureLuaBindings::poll_assets(sol::state& lua) {
    // This function can be used to poll for completed asset generation
    // and update Lua state accordingly
    // For now, it's a placeholder for future implementation
}

} // namespace SegmentedCreatures
} // namespace MagiTech
