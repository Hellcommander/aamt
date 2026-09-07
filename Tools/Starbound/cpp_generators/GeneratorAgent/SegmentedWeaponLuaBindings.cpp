#include "SegmentedWeaponLuaBindings.hpp"
#include "SegmentedWeaponFactory.hpp"
#include "SegmentedWeaponTypes.hpp"
#include "SegmentedWeaponParams.hpp"
#include "core/Log.hpp"
#include <vector>
#include <fstream>
#include <sstream>

namespace MagiTech {
namespace SegmentedWeapons {

static std::vector<std::pair<std::future<AssetBundle>, std::string>> pendingWeapons;

void SegmentedWeaponLuaBindings::bind(sol::state& lua) {
    // Bind enums
    bindEnums(lua);
    
    // Bind parameter structures
    bindParameterStructs(lua);
    
    // Bind factory functions
    bindFactoryFunctions(lua);
    
    // Bind utility functions
    bindUtilityFunctions(lua);
    
    // Bind global factory instance
    bindGlobalFactory(lua);
}

void SegmentedWeaponLuaBindings::bindEnums(sol::state& lua) {
    // WeaponType enum
    lua.new_enum("WeaponType",
        "WHIP", WeaponType::WHIP,
        "CHAIN", WeaponType::CHAIN,
        "FLAIL", WeaponType::FLAIL,
        "NUNCHAKU", WeaponType::NUNCHAKU,
        "ROPE", WeaponType::ROPE
    );
    
    // SegmentShape enum
    lua.new_enum("SegmentShape",
        "CYLINDER", SegmentShape::CYLINDER,
        "BOX", SegmentShape::BOX,
        "SPHERE", SegmentShape::SPHERE,
        "CUSTOM_MESH", SegmentShape::CUSTOM_MESH
    );
    
    // TaperProfile enum
    lua.new_enum("TaperProfile",
        "NONE", TaperProfile::NONE,
        "LINEAR", TaperProfile::LINEAR,
        "EXPONENTIAL", TaperProfile::EXPONENTIAL,
        "CUSTOM_CURVE", TaperProfile::CUSTOM_CURVE
    );
    
    // MaterialType enum
    lua.new_enum("MaterialType",
        "LEATHER", MaterialType::LEATHER,
        "STEEL", MaterialType::STEEL,
        "ROPE", MaterialType::ROPE,
        "CHAIN_METAL", MaterialType::CHAIN_METAL
    );
    
    // EndAttachment enum
    lua.new_enum("EndAttachment",
        "NONE", EndAttachment::NONE,
        "WEIGHT", EndAttachment::WEIGHT,
        "SPIKE", EndAttachment::SPIKE,
        "HOOK", EndAttachment::HOOK,
        "BLADE", EndAttachment::BLADE
    );
}

void SegmentedWeaponLuaBindings::bindParameterStructs(sol::state& lua) {
    // Bind ArticulationLimits
    lua.new_usertype<ArticulationLimits>("ArticulationLimits",
        sol::constructors<ArticulationLimits()>(),
        "twist", &ArticulationLimits::twist,
        "swing", &ArticulationLimits::swing,
        "hashKey", &ArticulationLimits::hashKey
    );

    // Bind SegmentedWeaponParams
    lua.new_usertype<SegmentedWeaponParams>("SegmentedWeaponParams",
        sol::constructors<SegmentedWeaponParams()>(),
        
        // Basic properties
        "id", &SegmentedWeaponParams::id,
        "weaponType", &SegmentedWeaponParams::weaponType,
        "segmentCount", &SegmentedWeaponParams::segmentCount,
        "segmentLength", &SegmentedWeaponParams::segmentLength,
        "segmentRadius", &SegmentedWeaponParams::segmentRadius,
        "segmentShape", &SegmentedWeaponParams::segmentShape,
        "taperProfile", &SegmentedWeaponParams::taperProfile,
        "jointFlexibility", &SegmentedWeaponParams::jointFlexibility,
        "articulationLimits", &SegmentedWeaponParams::articulationLimits,
        "materialType", &SegmentedWeaponParams::materialType,
        "colorPrimary", &SegmentedWeaponParams::colorPrimary,
        "colorSecondary", &SegmentedWeaponParams::colorSecondary,
        "noiseDetail", &SegmentedWeaponParams::noiseDetail,
        "textureScale", &SegmentedWeaponParams::textureScale,
        "ornamentation", &SegmentedWeaponParams::ornamentation,
        "endAttachment", &SegmentedWeaponParams::endAttachment,
        
        // Additional properties
        "segmentSpacing", &SegmentedWeaponParams::segmentSpacing,
        "enableJoints", &SegmentedWeaponParams::enableJoints,
        "jointDamping", &SegmentedWeaponParams::jointDamping,
        "enableCollision", &SegmentedWeaponParams::enableCollision,
        "collisionRadius", &SegmentedWeaponParams::collisionRadius,
        "enablePhysics", &SegmentedWeaponParams::enablePhysics,
        "physicsMass", &SegmentedWeaponParams::physicsMass,
        
        // Metadata
        "description", &SegmentedWeaponParams::description,
        "tags", &SegmentedWeaponParams::tags,
        "metadata", &SegmentedWeaponParams::metadata,
        
        // Performance settings
        "enableCaching", &SegmentedWeaponParams::enableCaching,
        "enableHotReload", &SegmentedWeaponParams::enableHotReload,
        "enableParallelProcessing", &SegmentedWeaponParams::enableParallelProcessing,
        
        // Methods
        "hashKey", &SegmentedWeaponParams::hashKey
    );

    // Bind PhysicsParams
    lua.new_usertype<PhysicsParams>("PhysicsParams",
        sol::constructors<PhysicsParams()>(),
        
        // Basic properties
        "massPerSegment", &PhysicsParams::massPerSegment,
        "damping", &PhysicsParams::damping,
        "restitution", &PhysicsParams::restitution,
        "collisionRadius", &PhysicsParams::collisionRadius,
        "solverIterations", &PhysicsParams::solverIterations,
        "gravityInfluence", &PhysicsParams::gravityInfluence,
        
        // Additional physics properties
        "friction", &PhysicsParams::friction,
        "rollingFriction", &PhysicsParams::rollingFriction,
        "spinningFriction", &PhysicsParams::spinningFriction,
        "enableGravity", &PhysicsParams::enableGravity,
        "enableCollisionDetection", &PhysicsParams::enableCollisionDetection,
        "maxLinearVelocity", &PhysicsParams::maxLinearVelocity,
        "maxAngularVelocity", &PhysicsParams::maxAngularVelocity,
        
        // Joint properties
        "jointDamping", &PhysicsParams::jointDamping,
        "jointFriction", &PhysicsParams::jointFriction,
        "enableJointLimits", &PhysicsParams::enableJointLimits,
        "jointLimitSoftness", &PhysicsParams::jointLimitSoftness,
        "jointLimitBias", &PhysicsParams::jointLimitBias,
        "jointLimitRelaxation", &PhysicsParams::jointLimitRelaxation,
        
        // Metadata
        "physicsName", &PhysicsParams::physicsName,
        "description", &PhysicsParams::description,
        "tags", &PhysicsParams::tags,
        "metadata", &PhysicsParams::metadata,
        
        // Methods
        "hashKey", &PhysicsParams::hashKey
    );

    // Bind AssetBundle
    lua.new_usertype<AssetBundle>("AssetBundle",
        "meshId", &AssetBundle::mesh,
        "textureId", &AssetBundle::texture,
        "skeletonId", &AssetBundle::skeleton,
        "physicsId", &AssetBundle::physics
    );
}

void SegmentedWeaponLuaBindings::bindFactoryFunctions(sol::state& lua) {
    // Bind spawn functions
    lua.set_function("spawn_segmented_weapon",
        [&](const SegmentedWeaponParams& w, const PhysicsParams& p) {
            Log::info("Lua request to spawn segmented weapon: {}", w.id);
            auto bundle = g_weaponFactory.generateSync(w, p);
            return bundle;
        }
    );

    lua.set_function("spawn_segmented_weapon_async",
        [&](const SegmentedWeaponParams& w, const PhysicsParams& p, sol::function cb) {
            Log::info("Lua async request to spawn segmented weapon: {}", w.id);
            auto fut = g_weaponFactory.generateAsync(w, p);
            pendingWeapons.emplace_back(std::move(fut), w.id);
        }
    );

    // Bind batch generation
    lua.set_function("generate_weapon_batch", 
        [&](const std::vector<std::pair<SegmentedWeaponParams, PhysicsParams>>& params) {
            try {
                auto futures = g_weaponFactory.generateBatch(params);
                std::vector<AssetBundle> results;
                results.reserve(futures.size());
                
                for (auto& future : futures) {
                    results.push_back(future.get());
                }
                
                return results;
            } catch (const std::exception& e) {
                Log::error("Error generating weapon batch: {}", e.what());
                return std::vector<AssetBundle>{};
            }
        }
    );
}

void SegmentedWeaponLuaBindings::bindUtilityFunctions(sol::state& lua) {
    // Bind parameter validation
    lua.set_function("validate_weapon_params", [](const SegmentedWeaponParams& params) {
        return g_weaponFactory.validateWeaponParams(params);
    });
    
    lua.set_function("get_weapon_validation_errors", [](const SegmentedWeaponParams& params) {
        return g_weaponFactory.getWeaponValidationErrors(params);
    });
    
    lua.set_function("validate_physics_params", [](const PhysicsParams& params) {
        return g_weaponFactory.validatePhysicsParams(params);
    });
    
    lua.set_function("get_physics_validation_errors", [](const PhysicsParams& params) {
        return g_weaponFactory.getPhysicsValidationErrors(params);
    });
    
    // Bind JSON serialization
    lua.set_function("save_weapon_params", [](const SegmentedWeaponParams& params, const std::string& filePath) {
        try {
            auto json = ParamUtils::toJson(params);
            std::ofstream file(filePath);
            if (file.is_open()) {
                file << json.dump(2);
                return true;
            }
            return false;
        } catch (const std::exception& e) {
            Log::error("Error saving weapon params: {}", e.what());
            return false;
        }
    });
    
    lua.set_function("load_weapon_params", [](const std::string& filePath) {
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
            Log::error("Error loading weapon params: {}", e.what());
            return SegmentedWeaponParams{};
        }
    });
    
    lua.set_function("save_physics_params", [](const PhysicsParams& params, const std::string& filePath) {
        try {
            auto json = ParamUtils::toJson(params);
            std::ofstream file(filePath);
            if (file.is_open()) {
                file << json.dump(2);
                return true;
            }
            return false;
        } catch (const std::exception& e) {
            Log::error("Error saving physics params: {}", e.what());
            return false;
        }
    });
    
    lua.set_function("load_physics_params", [](const std::string& filePath) {
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
            Log::error("Error loading physics params: {}", e.what());
            return PhysicsParams{};
        }
    });
    
    // Bind parameter conversion utilities
    lua.set_function("parse_weapon_type", [](const std::string& str) {
        return ParamUtils::parseWeaponType(str);
    });
    
    lua.set_function("parse_segment_shape", [](const std::string& str) {
        return ParamUtils::parseSegmentShape(str);
    });
    
    lua.set_function("parse_taper_profile", [](const std::string& str) {
        return ParamUtils::parseTaperProfile(str);
    });
    
    lua.set_function("parse_material_type", [](const std::string& str) {
        return ParamUtils::parseMaterialType(str);
    });
    
    lua.set_function("parse_end_attachment", [](const std::string& str) {
        return ParamUtils::parseEndAttachment(str);
    });
    
    // Bind string conversion utilities
    lua.set_function("weapon_type_to_string", [](WeaponType type) {
        return ParamUtils::weaponTypeToString(type);
    });
    
    lua.set_function("segment_shape_to_string", [](SegmentShape shape) {
        return ParamUtils::segmentShapeToString(shape);
    });
    
    lua.set_function("taper_profile_to_string", [](TaperProfile profile) {
        return ParamUtils::taperProfileToString(profile);
    });
    
    lua.set_function("material_type_to_string", [](MaterialType type) {
        return ParamUtils::materialTypeToString(type);
    });
    
    lua.set_function("end_attachment_to_string", [](EndAttachment attachment) {
        return ParamUtils::endAttachmentToString(attachment);
    });
}

void SegmentedWeaponLuaBindings::bindGlobalFactory(sol::state& lua) {
    // Bind global factory instance
    lua["weaponFactory"] = &g_weaponFactory;
    
    // Bind factory methods
    lua.new_usertype<SegmentedWeaponFactory>("SegmentedWeaponFactory",
        "generateAsync", &SegmentedWeaponFactory::generateAsync,
        "generateSync", &SegmentedWeaponFactory::generateSync,
        "generateFromJson", &SegmentedWeaponFactory::generateFromJson,
        "generateFromParams", &SegmentedWeaponFactory::generateFromParams,
        "generateBatch", &SegmentedWeaponFactory::generateBatch,
        "validateWeaponParams", &SegmentedWeaponFactory::validateWeaponParams,
        "getWeaponValidationErrors", &SegmentedWeaponFactory::getWeaponValidationErrors,
        "validatePhysicsParams", &SegmentedWeaponFactory::validatePhysicsParams,
        "getPhysicsValidationErrors", &SegmentedWeaponFactory::getPhysicsValidationErrors,
        "clearCache", &SegmentedWeaponFactory::clearCache,
        "getCacheSize", &SegmentedWeaponFactory::getCacheSize,
        "getCacheCapacity", &SegmentedWeaponFactory::getCacheCapacity
    );
}

void SegmentedWeaponLuaBindings::poll_assets(sol::state& lua) {
    for (auto it = pendingWeapons.begin(); it != pendingWeapons.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            auto b = it->first.get();
            lua["print"]("Segmented Weapon ready: " + it->second);
            it = pendingWeapons.erase(it);
        } else {
            ++it;
        }
    }
}

} // namespace SegmentedWeapons
} // namespace MagiTech
