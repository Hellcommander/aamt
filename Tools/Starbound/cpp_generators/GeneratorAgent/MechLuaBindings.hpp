#pragma once

#include "MechTypes.hpp"
#include "MechFactory.hpp"
#include <lua.hpp"
#include <memory>

namespace MagiTech {
namespace Mechs {

// Enhanced Lua binding functions for hybrid pipeline
extern "C" {
    // Core factory functions
    int lua_mt_mech_factory_generate_async(lua_State* L);
    int lua_mt_mech_factory_generate_sync(lua_State* L);
    int lua_mt_mech_factory_create_instance(lua_State* L);
    int lua_mt_mech_factory_destroy_instance(lua_State* L);
    int lua_mt_mech_factory_update_instance(lua_State* L);
    
    // Form morphing functions
    int lua_mt_mech_start_morph(lua_State* L);
    int lua_mt_mech_set_morph_progress(lua_State* L);
    int lua_mt_mech_pause_morph(lua_State* L);
    int lua_mt_mech_resume_morph(lua_State* L);
    
    // Batch operations
    int lua_mt_mech_generate_batch(lua_State* L);
    int lua_mt_mech_generate_batch_sync(lua_State* L);
    
    // Cache management
    int lua_mt_mech_clear_cache(lua_State* L);
    int lua_mt_mech_get_cache_size(lua_State* L);
    int lua_mt_mech_is_cached(lua_State* L);
    int lua_mt_mech_set_cache_size(lua_State* L);
    
    // Performance monitoring
    int lua_mt_mech_get_performance_metrics(lua_State* L);
    int lua_mt_mech_reset_performance_metrics(lua_State* L);
    
    // GPU acceleration
    int lua_mt_mech_set_gpu_acceleration(lua_State* L);
    int lua_mt_mech_is_gpu_acceleration_enabled(lua_State* L);
    
    // Hot reload
    int lua_mt_mech_watch_definition(lua_State* L);
    int lua_mt_mech_unwatch_definition(lua_State* L);
    int lua_mt_mech_process_hot_reloads(lua_State* L);
    
    // Procedural generation
    int lua_mt_mech_set_procedural_params(lua_State* L);
    int lua_mt_mech_get_procedural_params(lua_State* L);
    
    // Template system
    int lua_mt_mech_create_from_template(lua_State* L);
    int lua_mt_mech_register_template(lua_State* L);
    int lua_mt_mech_get_available_templates(lua_State* L);
    
    // Validation
    int lua_mt_mech_validate_params(lua_State* L);
    int lua_mt_mech_get_validation_errors(lua_State* L);
    
    // Utility functions
    int lua_mt_mech_spawn_mech(lua_State* L);
    int lua_mt_mech_create_mech_params(lua_State* L);
    int lua_mt_mech_get_mech_info(lua_State* L);
    int lua_mt_mech_set_mech_property(lua_State* L);
    int lua_mt_mech_get_mech_property(lua_State* L);
    
    // === SEGMENTED MECH FUNCTIONS ===
    
    // Segmented mech generation
    int lua_mt_mech_generate_segmented_async(lua_State* L);
    int lua_mt_mech_generate_segmented_sync(lua_State* L);
    int lua_mt_mech_create_segmented_instance(lua_State* L);
    int lua_mt_mech_destroy_segmented_instance(lua_State* L);
    int lua_mt_mech_update_segmented_instance(lua_State* L);
    
    // Dynamic segment management
    int lua_mt_mech_add_segment(lua_State* L);
    int lua_mt_mech_remove_segment(lua_State* L);
    int lua_mt_mech_set_segment_count(lua_State* L);
    int lua_mt_mech_update_segment_properties(lua_State* L);
    
    // Segmented mech animation
    int lua_mt_mech_start_segmented_animation(lua_State* L);
    int lua_mt_mech_set_segmented_animation_progress(lua_State* L);
    int lua_mt_mech_pause_segmented_animation(lua_State* L);
    int lua_mt_mech_resume_segmented_animation(lua_State* L);
    
    // Cockpit integration
    int lua_mt_mech_attach_cockpit(lua_State* L);
    int lua_mt_mech_detach_cockpit(lua_State* L);
    int lua_mt_mech_update_cockpit_params(lua_State* L);
    
    // Segmented mech batch operations
    int lua_mt_mech_generate_segmented_batch(lua_State* L);
    
    // Segmented mech cache management
    int lua_mt_mech_clear_segmented_cache(lua_State* L);
    int lua_mt_mech_get_segmented_cache_size(lua_State* L);
    int lua_mt_mech_is_segmented_cached(lua_State* L);
    
    // Segmented mech validation
    int lua_mt_mech_validate_segmented_params(lua_State* L);
    int lua_mt_mech_validate_cockpit_params(lua_State* L);
    int lua_mt_mech_get_segmented_validation_errors(lua_State* L);
    
    // Segmented mech templates
    int lua_mt_mech_create_segmented_from_template(lua_State* L);
    int lua_mt_mech_register_segmented_template(lua_State* L);
    int lua_mt_mech_get_available_segmented_templates(lua_State* L);
    
    // Cockpit templates
    int lua_mt_mech_create_cockpit_from_template(lua_State* L);
    int lua_mt_mech_register_cockpit_template(lua_State* L);
    int lua_mt_mech_get_available_cockpit_templates(lua_State* L);
    
    // Segmented mech utility functions
    int lua_mt_mech_spawn_segmented_mech(lua_State* L);
    int lua_mt_mech_create_segmented_mech_params(lua_State* L);
    int lua_mt_mech_create_cockpit_params(lua_State* L);
    int lua_mt_mech_create_ui_params(lua_State* L);
    int lua_mt_mech_get_segmented_mech_info(lua_State* L);
    int lua_mt_mech_set_segmented_mech_property(lua_State* L);
    int lua_mt_mech_get_segmented_mech_property(lua_State* L);
}

// Enhanced Lua binding registration
void registerMechLuaBindings(lua_State* L);

// Helper functions for enhanced Lua integration
namespace LuaHelpers {
    // Enhanced MechParams to Lua table conversion
    void pushMechParamsToLua(lua_State* L, const MechParams& params);
    bool getMechParamsFromLua(lua_State* L, int index, MechParams& params);
    
    // Enhanced MechBundle to Lua table conversion
    void pushMechBundleToLua(lua_State* L, const MechBundle& bundle);
    bool getMechBundleFromLua(lua_State* L, int index, MechBundle& bundle);
    
    // MechInstanceState to Lua table conversion
    void pushMechInstanceStateToLua(lua_State* L, const MechInstanceState& instance);
    bool getMechInstanceStateFromLua(lua_State* L, int index, MechInstanceState& instance);
    
    // ProceduralParams to Lua table conversion
    void pushProceduralParamsToLua(lua_State* L, const ProceduralParams& params);
    bool getProceduralParamsFromLua(lua_State* L, int index, ProceduralParams& params);
    
    // MechPerformanceMetrics to Lua table conversion
    void pushMechPerformanceMetricsToLua(lua_State* L, const MechPerformanceMetrics& metrics);
    bool getMechPerformanceMetricsFromLua(lua_State* L, int index, MechPerformanceMetrics& metrics);
    
    // === SEGMENTED MECH HELPERS ===
    
    // SegmentedMechParams to Lua table conversion
    void pushSegmentedMechParamsToLua(lua_State* L, const SegmentedMechParams& params);
    bool getSegmentedMechParamsFromLua(lua_State* L, int index, SegmentedMechParams& params);
    
    // SegmentedMechBundle to Lua table conversion
    void pushSegmentedMechBundleToLua(lua_State* L, const SegmentedMechBundle& bundle);
    bool getSegmentedMechBundleFromLua(lua_State* L, int index, SegmentedMechBundle& bundle);
    
    // SegmentedMechInstanceState to Lua table conversion
    void pushSegmentedMechInstanceStateToLua(lua_State* L, const SegmentedMechInstanceState& instance);
    bool getSegmentedMechInstanceStateFromLua(lua_State* L, int index, SegmentedMechInstanceState& instance);
    
    // CockpitParams to Lua table conversion
    void pushCockpitParamsToLua(lua_State* L, const CockpitParams& params);
    bool getCockpitParamsFromLua(lua_State* L, int index, CockpitParams& params);
    
    // UIParams to Lua table conversion
    void pushUIParamsToLua(lua_State* L, const UIParams& params);
    bool getUIParamsFromLua(lua_State* L, int index, UIParams& params);
    
    // Enhanced vector conversion helpers
    void pushVec3ToLua(lua_State* L, const glm::vec3& vec);
    bool getVec3FromLua(lua_State* L, int index, glm::vec3& vec);
    
    void pushVec2ToLua(lua_State* L, const glm::vec2& vec);
    bool getVec2FromLua(lua_State* L, int index, glm::vec2& vec);
    
    void pushMat4ToLua(lua_State* L, const glm::mat4& mat);
    bool getMat4FromLua(lua_State* L, int index, glm::mat4& mat);
    
    void pushQuatToLua(lua_State* L, const glm::quat& quat);
    bool getQuatFromLua(lua_State* L, int index, glm::quat& quat);
    
    // Enhanced table conversion helpers
    void pushStringMapToLua(lua_State* L, const std::unordered_map<std::string, float>& map);
    bool getStringMapFromLua(lua_State* L, int index, std::unordered_map<std::string, float>& map);
    
    void pushStringVectorToLua(lua_State* L, const std::vector<std::string>& vec);
    bool getStringVectorFromLua(lua_State* L, int index, std::vector<std::string>& vec);
    
    void pushFloatVectorToLua(lua_State* L, const std::vector<float>& vec);
    bool getFloatVectorFromLua(lua_State* L, int index, std::vector<float>& vec);
    
    // Enhanced error handling
    void luaError(lua_State* L, const std::string& message);
    void luaWarning(lua_State* L, const std::string& message);
    void luaInfo(lua_State* L, const std::string& message);
    
    // Enhanced type checking
    bool isLuaTable(lua_State* L, int index);
    bool isLuaString(lua_State* L, int index);
    bool isLuaNumber(lua_State* L, int index);
    bool isLuaBoolean(lua_State* L, int index);
    bool isLuaFunction(lua_State* L, int index);
    
    // Enhanced table field access
    std::string getTableString(lua_State* L, int index, const std::string& key, const std::string& defaultValue = "");
    float getTableNumber(lua_State* L, int index, const std::string& key, float defaultValue = 0.0f);
    bool getTableBoolean(lua_State* L, int index, const std::string& key, bool defaultValue = false);
    int getTableInteger(lua_State* L, int index, const std::string& key, int defaultValue = 0);
    
    // Enhanced table field setting
    void setTableString(lua_State* L, int index, const std::string& key, const std::string& value);
    void setTableNumber(lua_State* L, int index, const std::string& key, float value);
    void setTableBoolean(lua_State* L, int index, const std::string& key, bool value);
    void setTableInteger(lua_State* L, int index, const std::string& key, int value);
    void setTableFunction(lua_State* L, int index, const std::string& key, lua_CFunction func);
    
    // Validation helpers
    bool validateMechParams(const MechParams& params, std::vector<std::string>& errors);
    bool validateProceduralParams(const ProceduralParams& params, std::vector<std::string>& errors);
    bool validateSegmentedMechParams(const SegmentedMechParams& params, std::vector<std::string>& errors);
    bool validateCockpitParams(const CockpitParams& params, std::vector<std::string>& errors);
    bool validateUIParams(const UIParams& params, std::vector<std::string>& errors);
    
    // Template helpers
    MechParams createDefaultTemplate(const std::string& style);
    MechParams createScoutTemplate();
    MechParams createHeavyTemplate();
    MechParams createSupportTemplate();
    
    // Segmented mech template helpers
    SegmentedMechParams createSnakeTemplate();
    SegmentedMechParams createWormTemplate();
    SegmentedMechParams createSerpentTemplate();
    CockpitParams createInternalCockpitTemplate();
    CockpitParams createExternalCockpitTemplate();
    CockpitParams createModuleCockpitTemplate();
    UIParams createDefaultUIParams();
    
    // Utility functions
    std::string generateMechId(const MechParams& params);
    float computeMechMass(const MechParams& params);
    glm::vec3 computeMechSize(const MechParams& params);
    
    // Segmented mech utility functions
    std::string generateSegmentedMechId(const SegmentedMechParams& params);
    float computeSegmentedMechMass(const SegmentedMechParams& params);
    glm::vec3 computeSegmentedMechSize(const SegmentedMechParams& params);
    int computeOptimalSegmentCount(const SegmentedMechParams& params);
    
    // Performance tracking
    void startPerformanceTimer();
    uint64_t endPerformanceTimer();
    void trackMemoryUsage(uint64_t& memoryUsage);
}

// Global factory instance for Lua integration
extern std::unique_ptr<MechFactory> g_mechFactory;

} // namespace Mechs
} // namespace MagiTech
