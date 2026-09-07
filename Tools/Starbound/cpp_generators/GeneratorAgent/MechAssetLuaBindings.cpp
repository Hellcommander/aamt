#include "MechAssetLuaBindings.hpp"
#include <iostream>
#include <sstream>

namespace MagiTech {
namespace MechAssets {

// Global factory instance
static std::unique_ptr<MechAssetFactory> g_mechFactory = nullptr;

// Factory management Lua bindings
int lua_mt_mech_factory_create(lua_State* L) {
    if (!g_mechFactory) {
        g_mechFactory = std::make_unique<MechAssetFactory>();
    }
    
    MechDefinitionParams params;
    if (!LuaHelpers::getMechDefinitionParamsFromLua(L, 1, params)) {
        LuaHelpers::luaError(L, "Invalid mech definition parameters");
        return 0;
    }
    
    MechHandle handle = g_mechFactory->createMech(params);
    lua_pushinteger(L, static_cast<lua_Integer>(handle));
    return 1;
}

int lua_mt_mech_factory_load(lua_State* L) {
    if (!g_mechFactory) {
        g_mechFactory = std::make_unique<MechAssetFactory>();
    }
    
    std::string name = lua_tostring(L, 1);
    LODQuality quality = LODQuality::HIGH;
    
    if (lua_gettop(L) > 1) {
        std::string qualityStr = lua_tostring(L, 2);
        quality = LuaHelpers::stringToLODQuality(qualityStr);
    }
    
    MechHandle handle = g_mechFactory->loadMech(name, quality);
    lua_pushinteger(L, static_cast<lua_Integer>(handle));
    return 1;
}

int lua_mt_mech_factory_unload(lua_State* L) {
    if (!g_mechFactory) {
        lua_pushboolean(L, false);
        return 1;
    }
    
    MechHandle handle = static_cast<MechHandle>(lua_tointeger(L, 1));
    bool result = g_mechFactory->unloadMech(handle);
    lua_pushboolean(L, result);
    return 1;
}

// Instance management Lua bindings
int lua_mt_mech_instance_create(lua_State* L) {
    if (!g_mechFactory) {
        LuaHelpers::luaError(L, "Mech factory not initialized");
        return 0;
    }
    
    MechHandle mechHandle = static_cast<MechHandle>(lua_tointeger(L, 1));
    MechInstanceState instance = g_mechFactory->createInstance(mechHandle);
    
    LuaHelpers::pushMechInstanceStateToLua(L, instance);
    return 1;
}

int lua_mt_mech_instance_destroy(lua_State* L) {
    if (!g_mechFactory) {
        lua_pushboolean(L, false);
        return 1;
    }
    
    MechInstanceState instance;
    if (!LuaHelpers::getMechInstanceStateFromLua(L, 1, instance)) {
        lua_pushboolean(L, false);
        return 1;
    }
    
    bool result = g_mechFactory->destroyInstance(instance);
    lua_pushboolean(L, result);
    return 1;
}

int lua_mt_mech_instance_update(lua_State* L) {
    if (!g_mechFactory) {
        lua_pushboolean(L, false);
        return 1;
    }
    
    MechInstanceState instance;
    if (!LuaHelpers::getMechInstanceStateFromLua(L, 1, instance)) {
        lua_pushboolean(L, false);
        return 1;
    }
    
    float deltaTime = static_cast<float>(lua_tonumber(L, 2));
    bool result = g_mechFactory->updateInstance(instance, deltaTime);
    
    // Update the instance in Lua
    LuaHelpers::pushMechInstanceStateToLua(L, instance);
    lua_pushboolean(L, result);
    return 2;
}

// Morph control Lua bindings
int lua_mt_mech_morph_start(lua_State* L) {
    if (!g_mechFactory) {
        lua_pushboolean(L, false);
        return 1;
    }
    
    MechInstanceState instance;
    if (!LuaHelpers::getMechInstanceStateFromLua(L, 1, instance)) {
        lua_pushboolean(L, false);
        return 1;
    }
    
    std::string profileName = lua_tostring(L, 2);
    bool result = g_mechFactory->startMorph(instance, profileName);
    
    LuaHelpers::pushMechInstanceStateToLua(L, instance);
    lua_pushboolean(L, result);
    return 2;
}

int lua_mt_mech_morph_set_progress(lua_State* L) {
    if (!g_mechFactory) {
        lua_pushboolean(L, false);
        return 1;
    }
    
    MechInstanceState instance;
    if (!LuaHelpers::getMechInstanceStateFromLua(L, 1, instance)) {
        lua_pushboolean(L, false);
        return 1;
    }
    
    float progress = static_cast<float>(lua_tonumber(L, 2));
    bool result = g_mechFactory->setMorphProgress(instance, progress);
    
    LuaHelpers::pushMechInstanceStateToLua(L, instance);
    lua_pushboolean(L, result);
    return 2;
}

int lua_mt_mech_morph_pause(lua_State* L) {
    if (!g_mechFactory) {
        lua_pushboolean(L, false);
        return 1;
    }
    
    MechInstanceState instance;
    if (!LuaHelpers::getMechInstanceStateFromLua(L, 1, instance)) {
        lua_pushboolean(L, false);
        return 1;
    }
    
    bool result = g_mechFactory->pauseMorph(instance);
    
    LuaHelpers::pushMechInstanceStateToLua(L, instance);
    lua_pushboolean(L, result);
    return 2;
}

int lua_mt_mech_morph_resume(lua_State* L) {
    if (!g_mechFactory) {
        lua_pushboolean(L, false);
        return 1;
    }
    
    MechInstanceState instance;
    if (!LuaHelpers::getMechInstanceStateFromLua(L, 1, instance)) {
        lua_pushboolean(L, false);
        return 1;
    }
    
    bool result = g_mechFactory->resumeMorph(instance);
    
    LuaHelpers::pushMechInstanceStateToLua(L, instance);
    lua_pushboolean(L, result);
    return 2;
}

// Hot reload Lua bindings
int lua_mt_mech_watch_definition(lua_State* L) {
    if (!g_mechFactory) {
        lua_pushboolean(L, false);
        return 1;
    }
    
    std::string mechName = lua_tostring(L, 1);
    bool result = g_mechFactory->watchDefinition(mechName);
    lua_pushboolean(L, result);
    return 1;
}

int lua_mt_mech_unwatch_definition(lua_State* L) {
    if (!g_mechFactory) {
        lua_pushboolean(L, false);
        return 1;
    }
    
    std::string mechName = lua_tostring(L, 1);
    bool result = g_mechFactory->unwatchDefinition(mechName);
    lua_pushboolean(L, result);
    return 1;
}

int lua_mt_mech_process_hot_reloads(lua_State* L) {
    if (!g_mechFactory) {
        return 0;
    }
    
    g_mechFactory->processHotReloads();
    return 0;
}

// Performance and debugging Lua bindings
int lua_mt_mech_get_performance_metrics(lua_State* L) {
    if (!g_mechFactory) {
        lua_pushnil(L);
        return 1;
    }
    
    const MechPerformanceMetrics& metrics = g_mechFactory->getPerformanceMetrics();
    LuaHelpers::pushMechPerformanceMetricsToLua(L, metrics);
    return 1;
}

int lua_mt_mech_reset_performance_metrics(lua_State* L) {
    if (!g_mechFactory) {
        return 0;
    }
    
    g_mechFactory->resetPerformanceMetrics();
    return 0;
}

int lua_mt_mech_get_cache_size(lua_State* L) {
    if (!g_mechFactory) {
        lua_pushinteger(L, 0);
        return 1;
    }
    
    size_t cacheSize = g_mechFactory->getCacheSize();
    lua_pushinteger(L, static_cast<lua_Integer>(cacheSize));
    return 1;
}

int lua_mt_mech_clear_cache(lua_State* L) {
    if (!g_mechFactory) {
        return 0;
    }
    
    g_mechFactory->clearCache();
    return 0;
}

// GPU acceleration Lua bindings
int lua_mt_mech_set_gpu_acceleration(lua_State* L) {
    if (!g_mechFactory) {
        return 0;
    }
    
    bool enabled = lua_toboolean(L, 1);
    g_mechFactory->setGPUAcceleration(enabled);
    return 0;
}

int lua_mt_mech_is_gpu_acceleration_enabled(lua_State* L) {
    if (!g_mechFactory) {
        lua_pushboolean(L, false);
        return 1;
    }
    
    bool enabled = g_mechFactory->isGPUAccelerationEnabled();
    lua_pushboolean(L, enabled);
    return 1;
}

// Utility Lua bindings
int lua_mt_mech_get_form_type_from_string(lua_State* L) {
    std::string str = lua_tostring(L, 1);
    FormType type = LuaHelpers::stringToFormType(str);
    lua_pushinteger(L, static_cast<lua_Integer>(type));
    return 1;
}

int lua_mt_mech_get_module_type_from_string(lua_State* L) {
    std::string str = lua_tostring(L, 1);
    ModuleType type = LuaHelpers::stringToModuleType(str);
    lua_pushinteger(L, static_cast<lua_Integer>(type));
    return 1;
}

int lua_mt_mech_get_lod_quality_from_string(lua_State* L) {
    std::string str = lua_tostring(L, 1);
    LODQuality quality = LuaHelpers::stringToLODQuality(str);
    lua_pushinteger(L, static_cast<lua_Integer>(quality));
    return 1;
}

int lua_mt_mech_get_morph_curve_type_from_string(lua_State* L) {
    std::string str = lua_tostring(L, 1);
    MorphCurveType type = LuaHelpers::stringToMorphCurveType(str);
    lua_pushinteger(L, static_cast<lua_Integer>(type));
    return 1;
}

int lua_mt_mech_get_collider_type_from_string(lua_State* L) {
    std::string str = lua_tostring(L, 1);
    ColliderType type = LuaHelpers::stringToColliderType(str);
    lua_pushinteger(L, static_cast<lua_Integer>(type));
    return 1;
}

int lua_mt_mech_get_joint_type_from_string(lua_State* L) {
    std::string str = lua_tostring(L, 1);
    JointType type = LuaHelpers::stringToJointType(str);
    lua_pushinteger(L, static_cast<lua_Integer>(type));
    return 1;
}

// Lua binding registration
void registerMechAssetLuaBindings(lua_State* L) {
    // Create mech table
    lua_newtable(L);
    
    // Factory functions
    lua_pushcfunction(L, lua_mt_mech_factory_create);
    lua_setfield(L, -2, "create");
    
    lua_pushcfunction(L, lua_mt_mech_factory_load);
    lua_setfield(L, -2, "load");
    
    lua_pushcfunction(L, lua_mt_mech_factory_unload);
    lua_setfield(L, -2, "unload");
    
    // Instance functions
    lua_pushcfunction(L, lua_mt_mech_instance_create);
    lua_setfield(L, -2, "createInstance");
    
    lua_pushcfunction(L, lua_mt_mech_instance_destroy);
    lua_setfield(L, -2, "destroyInstance");
    
    lua_pushcfunction(L, lua_mt_mech_instance_update);
    lua_setfield(L, -2, "updateInstance");
    
    // Morph functions
    lua_pushcfunction(L, lua_mt_mech_morph_start);
    lua_setfield(L, -2, "startMorph");
    
    lua_pushcfunction(L, lua_mt_mech_morph_set_progress);
    lua_setfield(L, -2, "setMorphProgress");
    
    lua_pushcfunction(L, lua_mt_mech_morph_pause);
    lua_setfield(L, -2, "pauseMorph");
    
    lua_pushcfunction(L, lua_mt_mech_morph_resume);
    lua_setfield(L, -2, "resumeMorph");
    
    // Hot reload functions
    lua_pushcfunction(L, lua_mt_mech_watch_definition);
    lua_setfield(L, -2, "watchDefinition");
    
    lua_pushcfunction(L, lua_mt_mech_unwatch_definition);
    lua_setfield(L, -2, "unwatchDefinition");
    
    lua_pushcfunction(L, lua_mt_mech_process_hot_reloads);
    lua_setfield(L, -2, "processHotReloads");
    
    // Performance functions
    lua_pushcfunction(L, lua_mt_mech_get_performance_metrics);
    lua_setfield(L, -2, "getPerformanceMetrics");
    
    lua_pushcfunction(L, lua_mt_mech_reset_performance_metrics);
    lua_setfield(L, -2, "resetPerformanceMetrics");
    
    lua_pushcfunction(L, lua_mt_mech_get_cache_size);
    lua_setfield(L, -2, "getCacheSize");
    
    lua_pushcfunction(L, lua_mt_mech_clear_cache);
    lua_setfield(L, -2, "clearCache");
    
    // GPU acceleration functions
    lua_pushcfunction(L, lua_mt_mech_set_gpu_acceleration);
    lua_setfield(L, -2, "setGPUAcceleration");
    
    lua_pushcfunction(L, lua_mt_mech_is_gpu_acceleration_enabled);
    lua_setfield(L, -2, "isGPUAccelerationEnabled");
    
    // Utility functions
    lua_pushcfunction(L, lua_mt_mech_get_form_type_from_string);
    lua_setfield(L, -2, "getFormTypeFromString");
    
    lua_pushcfunction(L, lua_mt_mech_get_module_type_from_string);
    lua_setfield(L, -2, "getModuleTypeFromString");
    
    lua_pushcfunction(L, lua_mt_mech_get_lod_quality_from_string);
    lua_setfield(L, -2, "getLODQualityFromString");
    
    lua_pushcfunction(L, lua_mt_mech_get_morph_curve_type_from_string);
    lua_setfield(L, -2, "getMorphCurveTypeFromString");
    
    lua_pushcfunction(L, lua_mt_mech_get_collider_type_from_string);
    lua_setfield(L, -2, "getColliderTypeFromString");
    
    lua_pushcfunction(L, lua_mt_mech_get_joint_type_from_string);
    lua_setfield(L, -2, "getJointTypeFromString");
    
    // Set the table as global
    lua_setglobal(L, "mt_mech");
}

// LuaHelpers implementation
namespace LuaHelpers {

// Enum conversion helpers
FormType stringToFormType(const std::string& str) {
    if (str == "WALKER") return FormType::WALKER;
    if (str == "FLYER") return FormType::FLYER;
    if (str == "TANK") return FormType::TANK;
    if (str == "SWIMMER") return FormType::SWIMMER;
    if (str == "CLIMBER") return FormType::CLIMBER;
    if (str == "STEALTH") return FormType::STEALTH;
    if (str == "COMBAT") return FormType::COMBAT;
    if (str == "UTILITY") return FormType::UTILITY;
    return FormType::WALKER;
}

std::string formTypeToString(FormType type) {
    switch (type) {
        case FormType::WALKER: return "WALKER";
        case FormType::FLYER: return "FLYER";
        case FormType::TANK: return "TANK";
        case FormType::SWIMMER: return "SWIMMER";
        case FormType::CLIMBER: return "CLIMBER";
        case FormType::STEALTH: return "STEALTH";
        case FormType::COMBAT: return "COMBAT";
        case FormType::UTILITY: return "UTILITY";
        default: return "WALKER";
    }
}

ModuleType stringToModuleType(const std::string& str) {
    if (str == "CHASSIS") return ModuleType::CHASSIS;
    if (str == "ARM") return ModuleType::ARM;
    if (str == "LEG") return ModuleType::LEG;
    if (str == "WEAPON") return ModuleType::WEAPON;
    if (str == "SHIELD") return ModuleType::SHIELD;
    if (str == "THRUSTER") return ModuleType::THRUSTER;
    if (str == "SENSOR") return ModuleType::SENSOR;
    if (str == "COCKPIT") return ModuleType::COCKPIT;
    if (str == "UTILITY") return ModuleType::UTILITY;
    return ModuleType::CHASSIS;
}

std::string moduleTypeToString(ModuleType type) {
    switch (type) {
        case ModuleType::CHASSIS: return "CHASSIS";
        case ModuleType::ARM: return "ARM";
        case ModuleType::LEG: return "LEG";
        case ModuleType::WEAPON: return "WEAPON";
        case ModuleType::SHIELD: return "SHIELD";
        case ModuleType::THRUSTER: return "THRUSTER";
        case ModuleType::SENSOR: return "SENSOR";
        case ModuleType::COCKPIT: return "COCKPIT";
        case ModuleType::UTILITY: return "UTILITY";
        default: return "CHASSIS";
    }
}

LODQuality stringToLODQuality(const std::string& str) {
    if (str == "ULTRA_HIGH") return LODQuality::ULTRA_HIGH;
    if (str == "HIGH") return LODQuality::HIGH;
    if (str == "MEDIUM") return LODQuality::MEDIUM;
    if (str == "LOW") return LODQuality::LOW;
    if (str == "ULTRA_LOW") return LODQuality::ULTRA_LOW;
    return LODQuality::HIGH;
}

std::string lodQualityToString(LODQuality quality) {
    switch (quality) {
        case LODQuality::ULTRA_HIGH: return "ULTRA_HIGH";
        case LODQuality::HIGH: return "HIGH";
        case LODQuality::MEDIUM: return "MEDIUM";
        case LODQuality::LOW: return "LOW";
        case LODQuality::ULTRA_LOW: return "ULTRA_LOW";
        default: return "HIGH";
    }
}

MorphCurveType stringToMorphCurveType(const std::string& str) {
    if (str == "LINEAR") return MorphCurveType::LINEAR;
    if (str == "EASE_IN") return MorphCurveType::EASE_IN;
    if (str == "EASE_OUT") return MorphCurveType::EASE_OUT;
    if (str == "EASE_IN_OUT") return MorphCurveType::EASE_IN_OUT;
    if (str == "SMOOTHSTEP") return MorphCurveType::SMOOTHSTEP;
    if (str == "CUSTOM") return MorphCurveType::CUSTOM;
    return MorphCurveType::EASE_IN_OUT;
}

std::string morphCurveTypeToString(MorphCurveType type) {
    switch (type) {
        case MorphCurveType::LINEAR: return "LINEAR";
        case MorphCurveType::EASE_IN: return "EASE_IN";
        case MorphCurveType::EASE_OUT: return "EASE_OUT";
        case MorphCurveType::EASE_IN_OUT: return "EASE_IN_OUT";
        case MorphCurveType::SMOOTHSTEP: return "SMOOTHSTEP";
        case MorphCurveType::CUSTOM: return "CUSTOM";
        default: return "EASE_IN_OUT";
    }
}

ColliderType stringToColliderType(const std::string& str) {
    if (str == "CAPSULE") return ColliderType::CAPSULE;
    if (str == "BOX") return ColliderType::BOX;
    if (str == "SPHERE") return ColliderType::SPHERE;
    if (str == "CONVEX_HULL") return ColliderType::CONVEX_HULL;
    if (str == "MESH") return ColliderType::MESH;
    return ColliderType::CAPSULE;
}

std::string colliderTypeToString(ColliderType type) {
    switch (type) {
        case ColliderType::CAPSULE: return "CAPSULE";
        case ColliderType::BOX: return "BOX";
        case ColliderType::SPHERE: return "SPHERE";
        case ColliderType::CONVEX_HULL: return "CONVEX_HULL";
        case ColliderType::MESH: return "MESH";
        default: return "CAPSULE";
    }
}

JointType stringToJointType(const std::string& str) {
    if (str == "HINGE") return JointType::HINGE;
    if (str == "BALL") return JointType::BALL;
    if (str == "PRISMATIC") return JointType::PRISMATIC;
    if (str == "FIXED") return JointType::FIXED;
    if (str == "SPRING") return JointType::SPRING;
    return JointType::HINGE;
}

std::string jointTypeToString(JointType type) {
    switch (type) {
        case JointType::HINGE: return "HINGE";
        case JointType::BALL: return "BALL";
        case JointType::PRISMATIC: return "PRISMATIC";
        case JointType::FIXED: return "FIXED";
        case JointType::SPRING: return "SPRING";
        default: return "HINGE";
    }
}

// Vector conversion helpers
void pushVec3ToLua(lua_State* L, const glm::vec3& vec) {
    lua_newtable(L);
    lua_pushnumber(L, vec.x);
    lua_setfield(L, -2, "x");
    lua_pushnumber(L, vec.y);
    lua_setfield(L, -2, "y");
    lua_pushnumber(L, vec.z);
    lua_setfield(L, -2, "z");
}

bool getVec3FromLua(lua_State* L, int index, glm::vec3& vec) {
    if (!isLuaTable(L, index)) return false;
    
    vec.x = getTableNumber(L, index, "x", 0.0f);
    vec.y = getTableNumber(L, index, "y", 0.0f);
    vec.z = getTableNumber(L, index, "z", 0.0f);
    return true;
}

void pushVec2ToLua(lua_State* L, const glm::vec2& vec) {
    lua_newtable(L);
    lua_pushnumber(L, vec.x);
    lua_setfield(L, -2, "x");
    lua_pushnumber(L, vec.y);
    lua_setfield(L, -2, "y");
}

bool getVec2FromLua(lua_State* L, int index, glm::vec2& vec) {
    if (!isLuaTable(L, index)) return false;
    
    vec.x = getTableNumber(L, index, "x", 0.0f);
    vec.y = getTableNumber(L, index, "y", 0.0f);
    return true;
}

// Error handling
void luaError(lua_State* L, const std::string& message) {
    lua_pushstring(L, message.c_str());
    lua_error(L);
}

void luaWarning(lua_State* L, const std::string& message) {
    std::cerr << "Lua Warning: " << message << std::endl;
}

// Type checking
bool isLuaTable(lua_State* L, int index) {
    return lua_type(L, index) == LUA_TTABLE;
}

bool isLuaString(lua_State* L, int index) {
    return lua_type(L, index) == LUA_TSTRING;
}

bool isLuaNumber(lua_State* L, int index) {
    return lua_type(L, index) == LUA_TNUMBER;
}

bool isLuaBoolean(lua_State* L, int index) {
    return lua_type(L, index) == LUA_TBOOLEAN;
}

// Table field access
std::string getTableString(lua_State* L, int index, const std::string& key, const std::string& defaultValue) {
    lua_pushstring(L, key.c_str());
    lua_gettable(L, index - 1);
    if (lua_isstring(L, -1)) {
        std::string result = lua_tostring(L, -1);
        lua_pop(L, 1);
        return result;
    }
    lua_pop(L, 1);
    return defaultValue;
}

float getTableNumber(lua_State* L, int index, const std::string& key, float defaultValue) {
    lua_pushstring(L, key.c_str());
    lua_gettable(L, index - 1);
    if (lua_isnumber(L, -1)) {
        float result = static_cast<float>(lua_tonumber(L, -1));
        lua_pop(L, 1);
        return result;
    }
    lua_pop(L, 1);
    return defaultValue;
}

bool getTableBoolean(lua_State* L, int index, const std::string& key, bool defaultValue) {
    lua_pushstring(L, key.c_str());
    lua_gettable(L, index - 1);
    if (lua_isboolean(L, -1)) {
        bool result = lua_toboolean(L, -1);
        lua_pop(L, 1);
        return result;
    }
    lua_pop(L, 1);
    return defaultValue;
}

int getTableInteger(lua_State* L, int index, const std::string& key, int defaultValue) {
    lua_pushstring(L, key.c_str());
    lua_gettable(L, index - 1);
    if (lua_isnumber(L, -1)) {
        int result = static_cast<int>(lua_tointeger(L, -1));
        lua_pop(L, 1);
        return result;
    }
    lua_pop(L, 1);
    return defaultValue;
}

// Table field setting
void setTableString(lua_State* L, int index, const std::string& key, const std::string& value) {
    lua_pushstring(L, key.c_str());
    lua_pushstring(L, value.c_str());
    lua_settable(L, index - 2);
}

void setTableNumber(lua_State* L, int index, const std::string& key, float value) {
    lua_pushstring(L, key.c_str());
    lua_pushnumber(L, value);
    lua_settable(L, index - 2);
}

void setTableBoolean(lua_State* L, int index, const std::string& key, bool value) {
    lua_pushstring(L, key.c_str());
    lua_pushboolean(L, value);
    lua_settable(L, index - 2);
}

void setTableInteger(lua_State* L, int index, const std::string& key, int value) {
    lua_pushstring(L, key.c_str());
    lua_pushinteger(L, value);
    lua_settable(L, index - 2);
}

} // namespace LuaHelpers

} // namespace MechAssets
} // namespace MagiTech 
