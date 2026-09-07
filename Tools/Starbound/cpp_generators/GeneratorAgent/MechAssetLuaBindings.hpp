#pragma once
#include "MechAssetTypes.hpp"
#include "MechAssetFactory.hpp"

// Forward declarations to avoid Lua header conflicts
// The actual Lua headers will be included by implementation files
struct lua_State;
typedef int (*lua_CFunction)(lua_State*);

namespace MagiTech {
namespace MechAssets {

// Lua binding functions for FormShiftMechGen pipeline
extern "C" {
    // Factory management
    int lua_mt_mech_factory_create(lua_State* L);
    int lua_mt_mech_factory_load(lua_State* L);
    int lua_mt_mech_factory_unload(lua_State* L);
    
    // Instance management
    int lua_mt_mech_instance_create(lua_State* L);
    int lua_mt_mech_instance_destroy(lua_State* L);
    int lua_mt_mech_instance_update(lua_State* L);
    
    // Morph control
    int lua_mt_mech_morph_start(lua_State* L);
    int lua_mt_mech_morph_set_progress(lua_State* L);
    int lua_mt_mech_morph_pause(lua_State* L);
    int lua_mt_mech_morph_resume(lua_State* L);
    
    // Hot reload
    int lua_mt_mech_watch_definition(lua_State* L);
    int lua_mt_mech_unwatch_definition(lua_State* L);
    int lua_mt_mech_process_hot_reloads(lua_State* L);
    
    // Performance and debugging
    int lua_mt_mech_get_performance_metrics(lua_State* L);
    int lua_mt_mech_reset_performance_metrics(lua_State* L);
    int lua_mt_mech_get_cache_size(lua_State* L);
    int lua_mt_mech_clear_cache(lua_State* L);
    
    // GPU acceleration
    int lua_mt_mech_set_gpu_acceleration(lua_State* L);
    int lua_mt_mech_is_gpu_acceleration_enabled(lua_State* L);
    
    // Definition parsing and validation
    int lua_mt_mech_parse_definition(lua_State* L);
    int lua_mt_mech_validate_definition(lua_State* L);
    int lua_mt_mech_get_validation_errors(lua_State* L);
    
    // Module management
    int lua_mt_mech_create_module_definition(lua_State* L);
    int lua_mt_mech_create_morph_profile(lua_State* L);
    int lua_mt_mech_create_physics_rig(lua_State* L);
    int lua_mt_mech_create_lod_definition(lua_State* L);
    
    // Utility functions
    int lua_mt_mech_get_form_type_from_string(lua_State* L);
    int lua_mt_mech_get_module_type_from_string(lua_State* L);
    int lua_mt_mech_get_lod_quality_from_string(lua_State* L);
    int lua_mt_mech_get_morph_curve_type_from_string(lua_State* L);
    int lua_mt_mech_get_collider_type_from_string(lua_State* L);
    int lua_mt_mech_get_joint_type_from_string(lua_State* L);
}

// Lua binding registration
void registerMechAssetLuaBindings(lua_State* L);

// Helper functions for Lua integration
namespace LuaHelpers {
    // MechAsset to Lua table conversion
    void pushMechAssetToLua(lua_State* L, const MechAsset& asset);
    
    // Lua table to MechAsset conversion
    bool getMechAssetFromLua(lua_State* L, int index, MechAsset& asset);
    
    // MechInstanceState to Lua table conversion
    void pushMechInstanceStateToLua(lua_State* L, const MechInstanceState& instance);
    
    // Lua table to MechInstanceState conversion
    bool getMechInstanceStateFromLua(lua_State* L, int index, MechInstanceState& instance);
    
    // MechDefinitionParams to Lua table conversion
    void pushMechDefinitionParamsToLua(lua_State* L, const MechDefinitionParams& params);
    
    // Lua table to MechDefinitionParams conversion
    bool getMechDefinitionParamsFromLua(lua_State* L, int index, MechDefinitionParams& params);
    
    // ModuleDefinition to Lua table conversion
    void pushModuleDefinitionToLua(lua_State* L, const ModuleDefinition& module);
    
    // Lua table to ModuleDefinition conversion
    bool getModuleDefinitionFromLua(lua_State* L, int index, ModuleDefinition& module);
    
    // MorphProfile to Lua table conversion
    void pushMorphProfileToLua(lua_State* L, const MorphProfile& profile);
    
    // Lua table to MorphProfile conversion
    bool getMorphProfileFromLua(lua_State* L, int index, MorphProfile& profile);
    
    // PhysicsRigDefinition to Lua table conversion
    void pushPhysicsRigDefinitionToLua(lua_State* L, const PhysicsRigDefinition& rig);
    
    // Lua table to PhysicsRigDefinition conversion
    bool getPhysicsRigDefinitionFromLua(lua_State* L, int index, PhysicsRigDefinition& rig);
    
    // LODDefinition to Lua table conversion
    void pushLODDefinitionToLua(lua_State* L, const LODDefinition& lod);
    
    // Lua table to LODDefinition conversion
    bool getLODDefinitionFromLua(lua_State* L, int index, LODDefinition& lod);
    
    // MechPerformanceMetrics to Lua table conversion
    void pushMechPerformanceMetricsToLua(lua_State* L, const MechPerformanceMetrics& metrics);
    
    // Lua table to MechPerformanceMetrics conversion
    bool getMechPerformanceMetricsFromLua(lua_State* L, int index, MechPerformanceMetrics& metrics);
    
    // Enum conversion helpers
    FormType stringToFormType(const std::string& str);
    std::string formTypeToString(FormType type);
    
    ModuleType stringToModuleType(const std::string& str);
    std::string moduleTypeToString(ModuleType type);
    
    LODQuality stringToLODQuality(const std::string& str);
    std::string lodQualityToString(LODQuality quality);
    
    MorphCurveType stringToMorphCurveType(const std::string& str);
    std::string morphCurveTypeToString(MorphCurveType type);
    
    ColliderType stringToColliderType(const std::string& str);
    std::string colliderTypeToString(ColliderType type);
    
    JointType stringToJointType(const std::string& str);
    std::string jointTypeToString(JointType type);
    
    // Vector conversion helpers
    void pushVec3ToLua(lua_State* L, const glm::vec3& vec);
    bool getVec3FromLua(lua_State* L, int index, glm::vec3& vec);
    
    void pushVec2ToLua(lua_State* L, const glm::vec2& vec);
    bool getVec2FromLua(lua_State* L, int index, glm::vec2& vec);
    
    void pushMat4ToLua(lua_State* L, const glm::mat4& mat);
    bool getMat4FromLua(lua_State* L, int index, glm::mat4& mat);
    
    void pushQuatToLua(lua_State* L, const glm::quat& quat);
    bool getQuatFromLua(lua_State* L, int index, glm::quat& quat);
    
    // Table conversion helpers
    void pushStringMapToLua(lua_State* L, const std::unordered_map<std::string, float>& map);
    bool getStringMapFromLua(lua_State* L, int index, std::unordered_map<std::string, float>& map);
    
    void pushStringVec3MapToLua(lua_State* L, const std::unordered_map<std::string, glm::vec3>& map);
    bool getStringVec3MapFromLua(lua_State* L, int index, std::unordered_map<std::string, glm::vec3>& map);
    
    void pushStringFloatMapToLua(lua_State* L, const std::unordered_map<std::string, float>& map);
    bool getStringFloatMapFromLua(lua_State* L, int index, std::unordered_map<std::string, float>& map);
    
    void pushStringVectorToLua(lua_State* L, const std::vector<std::string>& vec);
    bool getStringVectorFromLua(lua_State* L, int index, std::vector<std::string>& vec);
    
    void pushFloatVectorToLua(lua_State* L, const std::vector<float>& vec);
    bool getFloatVectorFromLua(lua_State* L, int index, std::vector<float>& vec);
    
    // Error handling
    void luaError(lua_State* L, const std::string& message);
    void luaWarning(lua_State* L, const std::string& message);
    
    // Type checking
    bool isLuaTable(lua_State* L, int index);
    bool isLuaString(lua_State* L, int index);
    bool isLuaNumber(lua_State* L, int index);
    bool isLuaBoolean(lua_State* L, int index);
    
    // Table field access
    std::string getTableString(lua_State* L, int index, const std::string& key, const std::string& defaultValue = "");
    float getTableNumber(lua_State* L, int index, const std::string& key, float defaultValue = 0.0f);
    bool getTableBoolean(lua_State* L, int index, const std::string& key, bool defaultValue = false);
    int getTableInteger(lua_State* L, int index, const std::string& key, int defaultValue = 0);
    
    // Table field setting
    void setTableString(lua_State* L, int index, const std::string& key, const std::string& value);
    void setTableNumber(lua_State* L, int index, const std::string& key, float value);
    void setTableBoolean(lua_State* L, int index, const std::string& key, bool value);
    void setTableInteger(lua_State* L, int index, const std::string& key, int value);
}

} // namespace MechAssets
} // namespace MagiTech 
