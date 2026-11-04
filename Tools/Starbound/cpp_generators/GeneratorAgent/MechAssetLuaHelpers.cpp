// Lua <-> C++ conversions for the FormShiftMechGen bindings (MechAssetLuaBindings.hpp).
// Tables use named fields; vectors are {x, y, z} tables (array form {1, 2, 3} is also
// accepted); enums are written as strings and read from strings or integers.

#include "MechAssetLuaBindings.hpp"
#include <cstdint>
#include <string>

namespace MagiTech {
namespace MechAssets {
namespace LuaHelpers {

namespace {

int absIndex(lua_State* L, int index) {
    return (index > 0 || index <= LUA_REGISTRYINDEX) ? index : lua_gettop(L) + index + 1;
}

// Pushes t[key] and returns true when it is a table (otherwise pops it).
bool pushField(lua_State* L, int table, const char* key, int type) {
    lua_getfield(L, table, key);
    if (lua_type(L, -1) == type) return true;
    lua_pop(L, 1);
    return false;
}

template <typename E>
E readEnumField(lua_State* L, int table, const char* key, E fallback, E (*fromString)(const std::string&)) {
    lua_getfield(L, table, key);
    E value = fallback;
    if (lua_type(L, -1) == LUA_TSTRING) value = fromString(lua_tostring(L, -1));
    else if (lua_type(L, -1) == LUA_TNUMBER) value = static_cast<E>(static_cast<int>(lua_tointeger(L, -1)));
    lua_pop(L, 1);
    return value;
}

void setString(lua_State* L, const char* key, const std::string& value) {
    lua_pushstring(L, value.c_str());
    lua_setfield(L, -2, key);
}
void setNumber(lua_State* L, const char* key, double value) {
    lua_pushnumber(L, value);
    lua_setfield(L, -2, key);
}
void setBool(lua_State* L, const char* key, bool value) {
    lua_pushboolean(L, value ? 1 : 0);
    lua_setfield(L, -2, key);
}
void setInteger(lua_State* L, const char* key, long long value) {
    lua_pushinteger(L, static_cast<lua_Integer>(value));
    lua_setfield(L, -2, key);
}

template <typename T, typename PushFn>
void pushArray(lua_State* L, const std::vector<T>& items, PushFn push) {
    lua_newtable(L);
    for (size_t i = 0; i < items.size(); ++i) {
        push(L, items[i]);
        lua_rawseti(L, -2, static_cast<int>(i + 1));
    }
}

template <typename T, typename GetFn>
bool getArray(lua_State* L, int index, std::vector<T>& out, GetFn get) {
    index = absIndex(L, index);
    if (lua_type(L, index) != LUA_TTABLE) return false;
    out.clear();
    for (int i = 1;; ++i) {
        lua_rawgeti(L, index, i);
        if (lua_isnil(L, -1)) {
            lua_pop(L, 1);
            break;
        }
        T item{};
        const bool ok = get(L, -1, item);
        lua_pop(L, 1);
        if (!ok) return false;
        out.push_back(std::move(item));
    }
    return true;
}

bool readVec3Field(lua_State* L, int table, const char* key, glm::vec3& out) {
    if (!pushField(L, table, key, LUA_TTABLE)) return false;
    const bool ok = getVec3FromLua(L, -1, out);
    lua_pop(L, 1);
    return ok;
}

bool readVec2Field(lua_State* L, int table, const char* key, glm::vec2& out) {
    if (!pushField(L, table, key, LUA_TTABLE)) return false;
    const bool ok = getVec2FromLua(L, -1, out);
    lua_pop(L, 1);
    return ok;
}

// Reads x/y/z (or 1/2/3) number fields of the table at `index`.
bool readComponents(lua_State* L, int index, float* out, const char* const* names, int count) {
    index = absIndex(L, index);
    if (lua_type(L, index) != LUA_TTABLE) return false;
    for (int c = 0; c < count; ++c) {
        lua_getfield(L, index, names[c]);
        if (lua_type(L, -1) != LUA_TNUMBER) {
            lua_pop(L, 1);
            lua_rawgeti(L, index, c + 1);
        }
        if (lua_type(L, -1) == LUA_TNUMBER) out[c] = static_cast<float>(lua_tonumber(L, -1));
        lua_pop(L, 1);
    }
    return true;
}

} // namespace

// ---------------------------------------------------------------- vectors / matrices

void pushMat4ToLua(lua_State* L, const glm::mat4& mat) {
    // Column-major array of 16 numbers.
    lua_newtable(L);
    for (int c = 0; c < 4; ++c)
        for (int r = 0; r < 4; ++r) {
            lua_pushnumber(L, mat[c][r]);
            lua_rawseti(L, -2, c * 4 + r + 1);
        }
}

bool getMat4FromLua(lua_State* L, int index, glm::mat4& mat) {
    index = absIndex(L, index);
    if (lua_type(L, index) != LUA_TTABLE) return false;
    glm::mat4 result(1.0f);
    for (int i = 0; i < 16; ++i) {
        lua_rawgeti(L, index, i + 1);
        if (lua_type(L, -1) != LUA_TNUMBER) {
            lua_pop(L, 1);
            return false;
        }
        result[i / 4][i % 4] = static_cast<float>(lua_tonumber(L, -1));
        lua_pop(L, 1);
    }
    mat = result;
    return true;
}

void pushQuatToLua(lua_State* L, const glm::quat& quat) {
    lua_newtable(L);
    setNumber(L, "w", quat.w);
    setNumber(L, "x", quat.x);
    setNumber(L, "y", quat.y);
    setNumber(L, "z", quat.z);
}

bool getQuatFromLua(lua_State* L, int index, glm::quat& quat) {
    static const char* const names[] = {"w", "x", "y", "z"};
    float c[4] = {quat.w, quat.x, quat.y, quat.z};
    if (!readComponents(L, index, c, names, 4)) return false;
    glm::quat q(c[0], c[1], c[2], c[3]);
    const float len = glm::length(q);
    quat = len > 1e-8f ? q / len : glm::quat(1.0f, 0.0f, 0.0f, 0.0f);
    return true;
}

// ---------------------------------------------------------------- maps / vectors

void pushStringMapToLua(lua_State* L, const std::unordered_map<std::string, float>& map) {
    pushStringFloatMapToLua(L, map);
}

bool getStringMapFromLua(lua_State* L, int index, std::unordered_map<std::string, float>& map) {
    return getStringFloatMapFromLua(L, index, map);
}

void pushStringVec3MapToLua(lua_State* L, const std::unordered_map<std::string, glm::vec3>& map) {
    lua_newtable(L);
    for (const auto& [key, value] : map) {
        pushVec3ToLua(L, value);
        lua_setfield(L, -2, key.c_str());
    }
}

bool getStringVec3MapFromLua(lua_State* L, int index, std::unordered_map<std::string, glm::vec3>& map) {
    index = absIndex(L, index);
    if (lua_type(L, index) != LUA_TTABLE) return false;
    map.clear();
    lua_pushnil(L);
    while (lua_next(L, index) != 0) {
        if (lua_type(L, -2) == LUA_TSTRING) {
            glm::vec3 v(0.0f);
            if (getVec3FromLua(L, -1, v)) map[lua_tostring(L, -2)] = v;
        }
        lua_pop(L, 1);
    }
    return true;
}

void pushStringFloatMapToLua(lua_State* L, const std::unordered_map<std::string, float>& map) {
    lua_newtable(L);
    for (const auto& [key, value] : map) {
        lua_pushnumber(L, value);
        lua_setfield(L, -2, key.c_str());
    }
}

bool getStringFloatMapFromLua(lua_State* L, int index, std::unordered_map<std::string, float>& map) {
    index = absIndex(L, index);
    if (lua_type(L, index) != LUA_TTABLE) return false;
    map.clear();
    lua_pushnil(L);
    while (lua_next(L, index) != 0) {
        // lua_tostring on a number key would convert it in place and confuse lua_next.
        if (lua_type(L, -2) == LUA_TSTRING && lua_type(L, -1) == LUA_TNUMBER) {
            map[lua_tostring(L, -2)] = static_cast<float>(lua_tonumber(L, -1));
        }
        lua_pop(L, 1);
    }
    return true;
}

void pushStringVectorToLua(lua_State* L, const std::vector<std::string>& vec) {
    pushArray(L, vec, [](lua_State* s, const std::string& v) { lua_pushstring(s, v.c_str()); });
}

bool getStringVectorFromLua(lua_State* L, int index, std::vector<std::string>& vec) {
    return getArray(L, index, vec, [](lua_State* s, int i, std::string& out) {
        if (lua_type(s, i) != LUA_TSTRING) return false;
        out = lua_tostring(s, i);
        return true;
    });
}

void pushFloatVectorToLua(lua_State* L, const std::vector<float>& vec) {
    pushArray(L, vec, [](lua_State* s, float v) { lua_pushnumber(s, v); });
}

bool getFloatVectorFromLua(lua_State* L, int index, std::vector<float>& vec) {
    return getArray(L, index, vec, [](lua_State* s, int i, float& out) {
        if (lua_type(s, i) != LUA_TNUMBER) return false;
        out = static_cast<float>(lua_tonumber(s, i));
        return true;
    });
}

// ---------------------------------------------------------------- definition structs

void pushModuleDefinitionToLua(lua_State* L, const ModuleDefinition& module) {
    lua_newtable(L);
    setString(L, "id", module.id);
    setString(L, "type", moduleTypeToString(module.type));
    setString(L, "meshPath", module.meshPath);
    setString(L, "attachBone", module.attachBone);
    pushVec3ToLua(L, module.attachOffset);
    lua_setfield(L, -2, "attachOffset");
    pushVec3ToLua(L, module.attachRotation);
    lua_setfield(L, -2, "attachRotation");
    setNumber(L, "mass", module.mass);
    setBool(L, "weldToParent", module.weldToParent);
    pushStringVectorToLua(L, module.childModules);
    lua_setfield(L, -2, "childModules");
    setString(L, "colliderType", colliderTypeToString(module.colliderType));
    pushVec3ToLua(L, module.colliderSize);
    lua_setfield(L, -2, "colliderSize");
    setBool(L, "generateCollision", module.generateCollision);
    setBool(L, "enableLOD", module.enableLOD);
    pushFloatVectorToLua(L, module.lodScreenSizes);
    lua_setfield(L, -2, "lodScreenSizes");
}

bool getModuleDefinitionFromLua(lua_State* L, int index, ModuleDefinition& module) {
    index = absIndex(L, index);
    if (!isLuaTable(L, index)) return false;
    module.id = getTableString(L, index, "id", module.id);
    if (module.id.empty()) return false;
    module.type = readEnumField(L, index, "type", module.type, &stringToModuleType);
    module.meshPath = getTableString(L, index, "meshPath", module.meshPath);
    module.attachBone = getTableString(L, index, "attachBone", module.attachBone);
    readVec3Field(L, index, "attachOffset", module.attachOffset);
    readVec3Field(L, index, "attachRotation", module.attachRotation);
    module.mass = getTableNumber(L, index, "mass", module.mass);
    module.weldToParent = getTableBoolean(L, index, "weldToParent", module.weldToParent);
    if (pushField(L, index, "childModules", LUA_TTABLE)) {
        getStringVectorFromLua(L, -1, module.childModules);
        lua_pop(L, 1);
    }
    module.colliderType = readEnumField(L, index, "colliderType", module.colliderType, &stringToColliderType);
    readVec3Field(L, index, "colliderSize", module.colliderSize);
    module.generateCollision = getTableBoolean(L, index, "generateCollision", module.generateCollision);
    module.enableLOD = getTableBoolean(L, index, "enableLOD", module.enableLOD);
    if (pushField(L, index, "lodScreenSizes", LUA_TTABLE)) {
        getFloatVectorFromLua(L, -1, module.lodScreenSizes);
        lua_pop(L, 1);
    }
    return true;
}

void pushMorphProfileToLua(lua_State* L, const MorphProfile& profile) {
    lua_newtable(L);
    setString(L, "name", profile.name);
    setString(L, "fromForm", formTypeToString(profile.fromForm));
    setString(L, "toForm", formTypeToString(profile.toForm));
    setNumber(L, "duration", profile.duration);
    setString(L, "curveType", morphCurveTypeToString(profile.curveType));
    pushFloatVectorToLua(L, profile.customCurve);
    lua_setfield(L, -2, "customCurve");
    pushStringVec3MapToLua(L, profile.moduleTransforms);
    lua_setfield(L, -2, "moduleTransforms");
    pushStringVec3MapToLua(L, profile.moduleScales);
    lua_setfield(L, -2, "moduleScales");
    pushStringFloatMapToLua(L, profile.moduleOpacities);
    lua_setfield(L, -2, "moduleOpacities");
}

bool getMorphProfileFromLua(lua_State* L, int index, MorphProfile& profile) {
    index = absIndex(L, index);
    if (!isLuaTable(L, index)) return false;
    profile.name = getTableString(L, index, "name", profile.name);
    if (profile.name.empty()) return false;
    profile.fromForm = readEnumField(L, index, "fromForm", profile.fromForm, &stringToFormType);
    profile.toForm = readEnumField(L, index, "toForm", profile.toForm, &stringToFormType);
    profile.duration = getTableNumber(L, index, "duration", profile.duration);
    profile.curveType = readEnumField(L, index, "curveType", profile.curveType, &stringToMorphCurveType);
    if (pushField(L, index, "customCurve", LUA_TTABLE)) {
        getFloatVectorFromLua(L, -1, profile.customCurve);
        lua_pop(L, 1);
    }
    if (pushField(L, index, "moduleTransforms", LUA_TTABLE)) {
        getStringVec3MapFromLua(L, -1, profile.moduleTransforms);
        lua_pop(L, 1);
    }
    if (pushField(L, index, "moduleScales", LUA_TTABLE)) {
        getStringVec3MapFromLua(L, -1, profile.moduleScales);
        lua_pop(L, 1);
    }
    if (pushField(L, index, "moduleOpacities", LUA_TTABLE)) {
        getStringFloatMapFromLua(L, -1, profile.moduleOpacities);
        lua_pop(L, 1);
    }
    return true;
}

namespace {
void pushJointToLua(lua_State* L, const JointConstraint& joint) {
    lua_newtable(L);
    setString(L, "jointName", joint.jointName);
    setString(L, "type", jointTypeToString(joint.type));
    pushVec3ToLua(L, joint.axis);
    lua_setfield(L, -2, "axis");
    pushVec2ToLua(L, joint.limits);
    lua_setfield(L, -2, "limits");
    setNumber(L, "stiffness", joint.stiffness);
    setNumber(L, "damping", joint.damping);
    setBool(L, "enableMotor", joint.enableMotor);
    setNumber(L, "motorTargetVelocity", joint.motorTargetVelocity);
    setNumber(L, "motorMaxForce", joint.motorMaxForce);
}

bool getJointFromLua(lua_State* L, int index, JointConstraint& joint) {
    index = absIndex(L, index);
    if (!isLuaTable(L, index)) return false;
    joint.jointName = getTableString(L, index, "jointName", joint.jointName);
    joint.type = readEnumField(L, index, "type", joint.type, &stringToJointType);
    readVec3Field(L, index, "axis", joint.axis);
    readVec2Field(L, index, "limits", joint.limits);
    joint.stiffness = getTableNumber(L, index, "stiffness", joint.stiffness);
    joint.damping = getTableNumber(L, index, "damping", joint.damping);
    joint.enableMotor = getTableBoolean(L, index, "enableMotor", joint.enableMotor);
    joint.motorTargetVelocity = getTableNumber(L, index, "motorTargetVelocity", joint.motorTargetVelocity);
    joint.motorMaxForce = getTableNumber(L, index, "motorMaxForce", joint.motorMaxForce);
    return !joint.jointName.empty();
}
} // namespace

void pushPhysicsRigDefinitionToLua(lua_State* L, const PhysicsRigDefinition& rig) {
    lua_newtable(L);
    setNumber(L, "totalMass", rig.totalMass);
    pushStringFloatMapToLua(L, rig.moduleMasses);
    lua_setfield(L, -2, "moduleMasses");
    pushArray(L, rig.joints, &pushJointToLua);
    lua_setfield(L, -2, "joints");
    pushVec3ToLua(L, rig.centerOfMass);
    lua_setfield(L, -2, "centerOfMass");
    setBool(L, "enableGravity", rig.enableGravity);
    setBool(L, "enableCollision", rig.enableCollision);
    setNumber(L, "linearDamping", rig.linearDamping);
    setNumber(L, "angularDamping", rig.angularDamping);
}

bool getPhysicsRigDefinitionFromLua(lua_State* L, int index, PhysicsRigDefinition& rig) {
    index = absIndex(L, index);
    if (!isLuaTable(L, index)) return false;
    rig.totalMass = getTableNumber(L, index, "totalMass", rig.totalMass);
    if (pushField(L, index, "moduleMasses", LUA_TTABLE)) {
        getStringFloatMapFromLua(L, -1, rig.moduleMasses);
        lua_pop(L, 1);
    }
    if (pushField(L, index, "joints", LUA_TTABLE)) {
        const bool ok = getArray(L, -1, rig.joints, &getJointFromLua);
        lua_pop(L, 1);
        if (!ok) return false;
    }
    readVec3Field(L, index, "centerOfMass", rig.centerOfMass);
    rig.enableGravity = getTableBoolean(L, index, "enableGravity", rig.enableGravity);
    rig.enableCollision = getTableBoolean(L, index, "enableCollision", rig.enableCollision);
    rig.linearDamping = getTableNumber(L, index, "linearDamping", rig.linearDamping);
    rig.angularDamping = getTableNumber(L, index, "angularDamping", rig.angularDamping);
    return true;
}

void pushLODDefinitionToLua(lua_State* L, const LODDefinition& lod) {
    lua_newtable(L);
    setString(L, "quality", lodQualityToString(lod.quality));
    setNumber(L, "screenSize", lod.screenSize);
    setNumber(L, "meshDecimateRatio", lod.meshDecimateRatio);
    setNumber(L, "morphDetailRatio", lod.morphDetailRatio);
    setBool(L, "preserveBorders", lod.preserveBorders);
    setBool(L, "preserveUVSeams", lod.preserveUVSeams);
    setInteger(L, "maxTriangles", lod.maxTriangles);
}

bool getLODDefinitionFromLua(lua_State* L, int index, LODDefinition& lod) {
    index = absIndex(L, index);
    if (!isLuaTable(L, index)) return false;
    lod.quality = readEnumField(L, index, "quality", LODQuality::HIGH, &stringToLODQuality);
    lod.screenSize = getTableNumber(L, index, "screenSize", 0.1f);
    lod.meshDecimateRatio = getTableNumber(L, index, "meshDecimateRatio", lod.meshDecimateRatio);
    lod.morphDetailRatio = getTableNumber(L, index, "morphDetailRatio", lod.morphDetailRatio);
    lod.preserveBorders = getTableBoolean(L, index, "preserveBorders", lod.preserveBorders);
    lod.preserveUVSeams = getTableBoolean(L, index, "preserveUVSeams", lod.preserveUVSeams);
    lod.maxTriangles = getTableInteger(L, index, "maxTriangles", lod.maxTriangles);
    return true;
}

void pushMechDefinitionParamsToLua(lua_State* L, const MechDefinitionParams& params) {
    lua_newtable(L);
    setString(L, "name", params.name);
    setString(L, "description", params.description);
    setString(L, "skeletonTemplate", params.skeletonTemplate);
    setBool(L, "enableGPUAcceleration", params.enableGPUAcceleration);
    setBool(L, "enableHotReload", params.enableHotReload);
    pushArray(L, params.modules, &pushModuleDefinitionToLua);
    lua_setfield(L, -2, "modules");
    pushArray(L, params.morphProfiles, &pushMorphProfileToLua);
    lua_setfield(L, -2, "morphProfiles");
    pushPhysicsRigDefinitionToLua(L, params.physicsRig);
    lua_setfield(L, -2, "physicsRig");
    pushArray(L, params.lods, &pushLODDefinitionToLua);
    lua_setfield(L, -2, "lods");
}

bool getMechDefinitionParamsFromLua(lua_State* L, int index, MechDefinitionParams& params) {
    index = absIndex(L, index);
    if (!isLuaTable(L, index)) return false;
    params.name = getTableString(L, index, "name", params.name);
    params.description = getTableString(L, index, "description", params.description);
    params.skeletonTemplate = getTableString(L, index, "skeletonTemplate", params.skeletonTemplate);
    params.enableGPUAcceleration = getTableBoolean(L, index, "enableGPUAcceleration", params.enableGPUAcceleration);
    params.enableHotReload = getTableBoolean(L, index, "enableHotReload", params.enableHotReload);

    bool ok = true;
    if (pushField(L, index, "modules", LUA_TTABLE)) {
        ok = ok && getArray(L, -1, params.modules, &getModuleDefinitionFromLua);
        lua_pop(L, 1);
    }
    if (pushField(L, index, "morphProfiles", LUA_TTABLE)) {
        ok = ok && getArray(L, -1, params.morphProfiles, &getMorphProfileFromLua);
        lua_pop(L, 1);
    }
    if (pushField(L, index, "physicsRig", LUA_TTABLE)) {
        ok = ok && getPhysicsRigDefinitionFromLua(L, -1, params.physicsRig);
        lua_pop(L, 1);
    }
    if (pushField(L, index, "lods", LUA_TTABLE)) {
        ok = ok && getArray(L, -1, params.lods, &getLODDefinitionFromLua);
        lua_pop(L, 1);
    }
    return ok && !params.name.empty();
}

// ---------------------------------------------------------------- runtime structs

void pushMechInstanceStateToLua(lua_State* L, const MechInstanceState& instance) {
    lua_newtable(L);
    setString(L, "currentForm", formTypeToString(instance.currentForm));
    setString(L, "targetForm", formTypeToString(instance.targetForm));
    setNumber(L, "morphProgress", instance.morphProgress);
    setNumber(L, "morphDuration", instance.morphDuration);
    setBool(L, "isMorphing", instance.isMorphing);
    setBool(L, "isActive", instance.isActive);
    pushVec3ToLua(L, instance.position);
    lua_setfield(L, -2, "position");
    pushQuatToLua(L, instance.rotation);
    lua_setfield(L, -2, "rotation");
    pushVec3ToLua(L, instance.velocity);
    lua_setfield(L, -2, "velocity");
    pushVec3ToLua(L, instance.angularVelocity);
    lua_setfield(L, -2, "angularVelocity");
}

bool getMechInstanceStateFromLua(lua_State* L, int index, MechInstanceState& instance) {
    index = absIndex(L, index);
    if (!isLuaTable(L, index)) return false;
    instance.currentForm = readEnumField(L, index, "currentForm", instance.currentForm, &stringToFormType);
    instance.targetForm = readEnumField(L, index, "targetForm", instance.targetForm, &stringToFormType);
    instance.morphProgress = getTableNumber(L, index, "morphProgress", instance.morphProgress);
    instance.morphDuration = getTableNumber(L, index, "morphDuration", instance.morphDuration);
    instance.isMorphing = getTableBoolean(L, index, "isMorphing", instance.isMorphing);
    instance.isActive = getTableBoolean(L, index, "isActive", instance.isActive);
    readVec3Field(L, index, "position", instance.position);
    if (pushField(L, index, "rotation", LUA_TTABLE)) {
        getQuatFromLua(L, -1, instance.rotation);
        lua_pop(L, 1);
    }
    readVec3Field(L, index, "velocity", instance.velocity);
    readVec3Field(L, index, "angularVelocity", instance.angularVelocity);
    return true;
}

void pushMechPerformanceMetricsToLua(lua_State* L, const MechPerformanceMetrics& metrics) {
    lua_newtable(L);
    setInteger(L, "totalInstances", static_cast<long long>(metrics.totalInstances.load()));
    setInteger(L, "activeInstances", static_cast<long long>(metrics.activeInstances.load()));
    setInteger(L, "morphingInstances", static_cast<long long>(metrics.morphingInstances.load()));
    setInteger(L, "cacheHits", static_cast<long long>(metrics.cacheHits.load()));
    setInteger(L, "cacheMisses", static_cast<long long>(metrics.cacheMisses.load()));
    setInteger(L, "totalProcessingTime", static_cast<long long>(metrics.totalProcessingTime.load()));
    setInteger(L, "peakMemoryUsage", static_cast<long long>(metrics.peakMemoryUsage.load()));
    setInteger(L, "gpuMemoryUsage", static_cast<long long>(metrics.gpuMemoryUsage.load()));
    setNumber(L, "cacheHitRate", metrics.getCacheHitRate());
    setNumber(L, "averageProcessingTime", metrics.getAverageProcessingTime());
}

bool getMechPerformanceMetricsFromLua(lua_State* L, int index, MechPerformanceMetrics& metrics) {
    index = absIndex(L, index);
    if (!isLuaTable(L, index)) return false;
    auto read = [&](const char* key, std::atomic<uint64_t>& field) {
        const int value = getTableInteger(L, index, key, -1);
        if (value >= 0) field = static_cast<uint64_t>(value);
    };
    read("totalInstances", metrics.totalInstances);
    read("activeInstances", metrics.activeInstances);
    read("morphingInstances", metrics.morphingInstances);
    read("cacheHits", metrics.cacheHits);
    read("cacheMisses", metrics.cacheMisses);
    read("totalProcessingTime", metrics.totalProcessingTime);
    read("peakMemoryUsage", metrics.peakMemoryUsage);
    read("gpuMemoryUsage", metrics.gpuMemoryUsage);
    return true;
}

namespace {
void pushModuleDataToLua(lua_State* L, const ModuleData& module) {
    lua_newtable(L);
    setInteger(L, "handle", module.handle);
    setString(L, "id", module.id);
    setString(L, "type", moduleTypeToString(module.type));
    pushArray(L, module.lodMeshes, [](lua_State* s, MeshHandle h) { lua_pushinteger(s, static_cast<lua_Integer>(h)); });
    lua_setfield(L, -2, "lodMeshes");
    pushArray(L, module.morphTargets, [](lua_State* s, MorphTargetHandle h) { lua_pushinteger(s, static_cast<lua_Integer>(h)); });
    lua_setfield(L, -2, "morphTargets");
    setInteger(L, "physicsBody", module.physicsBody);
    pushMat4ToLua(L, module.localTransform);
    lua_setfield(L, -2, "localTransform");
    pushMat4ToLua(L, module.worldTransform);
    lua_setfield(L, -2, "worldTransform");
    setBool(L, "isVisible", module.isVisible);
    setBool(L, "isActive", module.isActive);
}

bool getHandle(lua_State* L, int i, uint32_t& out) {
    if (lua_type(L, i) != LUA_TNUMBER) return false;
    out = static_cast<uint32_t>(lua_tointeger(L, i));
    return true;
}

bool getModuleDataFromLua(lua_State* L, int index, ModuleData& module) {
    index = absIndex(L, index);
    if (!isLuaTable(L, index)) return false;
    module.handle = static_cast<ModuleHandle>(getTableInteger(L, index, "handle", 0));
    module.id = getTableString(L, index, "id", module.id);
    module.type = readEnumField(L, index, "type", module.type, &stringToModuleType);
    if (pushField(L, index, "lodMeshes", LUA_TTABLE)) {
        getArray(L, -1, module.lodMeshes, &getHandle);
        lua_pop(L, 1);
    }
    if (pushField(L, index, "morphTargets", LUA_TTABLE)) {
        getArray(L, -1, module.morphTargets, &getHandle);
        lua_pop(L, 1);
    }
    module.physicsBody = static_cast<PhysicsRigHandle>(getTableInteger(L, index, "physicsBody", 0));
    if (pushField(L, index, "localTransform", LUA_TTABLE)) {
        getMat4FromLua(L, -1, module.localTransform);
        lua_pop(L, 1);
    }
    if (pushField(L, index, "worldTransform", LUA_TTABLE)) {
        getMat4FromLua(L, -1, module.worldTransform);
        lua_pop(L, 1);
    }
    module.isVisible = getTableBoolean(L, index, "isVisible", module.isVisible);
    module.isActive = getTableBoolean(L, index, "isActive", module.isActive);
    return !module.id.empty();
}
} // namespace

void pushMechAssetToLua(lua_State* L, const MechAsset& asset) {
    lua_newtable(L);
    setInteger(L, "handle", asset.handle);
    setString(L, "name", asset.name);
    setInteger(L, "skeleton", asset.skeleton);
    pushArray(L, asset.modules, &pushModuleDataToLua);
    lua_setfield(L, -2, "modules");
    pushArray(L, asset.morphProfiles, &pushMorphProfileToLua);
    lua_setfield(L, -2, "morphProfiles");
    setInteger(L, "physicsRig", asset.physicsRig);
    pushArray(L, asset.lods, &pushLODDefinitionToLua);
    lua_setfield(L, -2, "lods");
    setInteger(L, "packHandle", asset.packHandle);
    setBool(L, "gpuAccelerated", asset.gpuAccelerated);
    setInteger(L, "cacheHits", static_cast<long long>(asset.cacheHits.load()));
    setInteger(L, "cacheMisses", static_cast<long long>(asset.cacheMisses.load()));
}

bool getMechAssetFromLua(lua_State* L, int index, MechAsset& asset) {
    index = absIndex(L, index);
    if (!isLuaTable(L, index)) return false;
    asset.handle = static_cast<MechHandle>(getTableInteger(L, index, "handle", 0));
    asset.name = getTableString(L, index, "name", asset.name);
    asset.skeleton = static_cast<SkeletonHandle>(getTableInteger(L, index, "skeleton", 0));
    asset.physicsRig = static_cast<PhysicsRigHandle>(getTableInteger(L, index, "physicsRig", 0));
    asset.packHandle = static_cast<MechPackHandle>(getTableInteger(L, index, "packHandle", 0));
    asset.gpuAccelerated = getTableBoolean(L, index, "gpuAccelerated", asset.gpuAccelerated);
    bool ok = true;
    if (pushField(L, index, "modules", LUA_TTABLE)) {
        ok = ok && getArray(L, -1, asset.modules, &getModuleDataFromLua);
        lua_pop(L, 1);
    }
    if (pushField(L, index, "morphProfiles", LUA_TTABLE)) {
        ok = ok && getArray(L, -1, asset.morphProfiles, &getMorphProfileFromLua);
        lua_pop(L, 1);
    }
    if (pushField(L, index, "lods", LUA_TTABLE)) {
        ok = ok && getArray(L, -1, asset.lods, &getLODDefinitionFromLua);
        lua_pop(L, 1);
    }
    return ok;
}

} // namespace LuaHelpers
} // namespace MechAssets
} // namespace MagiTech
