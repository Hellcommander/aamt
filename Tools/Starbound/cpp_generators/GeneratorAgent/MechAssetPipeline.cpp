// FormShiftMechGen pipeline stages for MechAssetFactory:
// definition parsing/validation, module assembly, morph targets, physics rig,
// LODs, .mechpack I/O and runtime loading.
//
// Geometry uses the `mt` mesh pipeline (core/mesh); meshes, skeletons and physics
// rigs live in Mechs::MechFamilyAssetStore and are referenced by handle.

#include "MechAssetFactory.hpp"
#include "MechFamilyAssetStore.hpp"
#include "core/Log.hpp"
#include "core/mesh/Mesh.hpp"
#include "core/mesh/MeshGenerator.hpp"
#include "core/mesh/MeshHandle.hpp"
#include "vendor/json/include/nlohmann/json.hpp"

#include <algorithm>
#include <atomic>
#include <cmath>
#include <cstring>
#include <fstream>
#include <limits>
#include <stdexcept>
#include <type_traits>
#include <unordered_set>
#include <glm/gtc/matrix_transform.hpp>
#include <glm/gtc/type_ptr.hpp>

namespace MagiTech {
namespace MechAssets {

using Mechs::MechFamilyAssetStore;

namespace {

MechFamilyAssetStore& store() {
    return MechFamilyAssetStore::instance();
}

std::shared_ptr<mt::Mesh> meshFor(MeshHandle handle) {
    return handle ? store().get<mt::Mesh>(handle) : nullptr;
}

glm::mat4 composeTransform(const glm::vec3& offset, const glm::vec3& rotationDeg) {
    glm::mat4 m = glm::translate(glm::mat4(1.0f), offset);
    m = glm::rotate(m, glm::radians(rotationDeg.z), glm::vec3(0, 0, 1));
    m = glm::rotate(m, glm::radians(rotationDeg.y), glm::vec3(0, 1, 0));
    m = glm::rotate(m, glm::radians(rotationDeg.x), glm::vec3(1, 0, 0));
    return m;
}

// ---------------------------------------------------------------- enum <-> string (definition files)
template <typename E>
struct EnumName { E value; const char* name; };

constexpr EnumName<ModuleType> kModuleTypes[] = {
    {ModuleType::CHASSIS, "CHASSIS"}, {ModuleType::ARM, "ARM"}, {ModuleType::LEG, "LEG"},
    {ModuleType::WEAPON, "WEAPON"}, {ModuleType::SHIELD, "SHIELD"}, {ModuleType::THRUSTER, "THRUSTER"},
    {ModuleType::SENSOR, "SENSOR"}, {ModuleType::COCKPIT, "COCKPIT"}, {ModuleType::UTILITY, "UTILITY"}};
constexpr EnumName<FormType> kFormTypes[] = {
    {FormType::WALKER, "WALKER"}, {FormType::FLYER, "FLYER"}, {FormType::TANK, "TANK"},
    {FormType::SWIMMER, "SWIMMER"}, {FormType::CLIMBER, "CLIMBER"}, {FormType::STEALTH, "STEALTH"},
    {FormType::COMBAT, "COMBAT"}, {FormType::UTILITY, "UTILITY"}};
constexpr EnumName<MorphCurveType> kCurveTypes[] = {
    {MorphCurveType::LINEAR, "LINEAR"}, {MorphCurveType::EASE_IN, "EASE_IN"}, {MorphCurveType::EASE_OUT, "EASE_OUT"},
    {MorphCurveType::EASE_IN_OUT, "EASE_IN_OUT"}, {MorphCurveType::SMOOTHSTEP, "SMOOTHSTEP"}, {MorphCurveType::CUSTOM, "CUSTOM"}};
constexpr EnumName<LODQuality> kLodQualities[] = {
    {LODQuality::ULTRA_HIGH, "ULTRA_HIGH"}, {LODQuality::HIGH, "HIGH"}, {LODQuality::MEDIUM, "MEDIUM"},
    {LODQuality::LOW, "LOW"}, {LODQuality::ULTRA_LOW, "ULTRA_LOW"}};
constexpr EnumName<ColliderType> kColliderTypes[] = {
    {ColliderType::CAPSULE, "CAPSULE"}, {ColliderType::BOX, "BOX"}, {ColliderType::SPHERE, "SPHERE"},
    {ColliderType::CONVEX_HULL, "CONVEX_HULL"}, {ColliderType::MESH, "MESH"}};
constexpr EnumName<JointType> kJointTypes[] = {
    {JointType::HINGE, "HINGE"}, {JointType::BALL, "BALL"}, {JointType::PRISMATIC, "PRISMATIC"},
    {JointType::FIXED, "FIXED"}, {JointType::SPRING, "SPRING"}};

std::string upper(std::string s) {
    std::transform(s.begin(), s.end(), s.begin(), [](unsigned char c) { return static_cast<char>(std::toupper(c)); });
    return s;
}

template <typename E, size_t N>
E parseEnum(const nlohmann::json& j, const char* key, const EnumName<E> (&table)[N], E fallback) {
    if (!j.contains(key)) return fallback;
    const auto& v = j.at(key);
    if (v.is_number_integer()) {
        const int i = v.get<int>();
        for (const auto& e : table) if (static_cast<int>(e.value) == i) return e.value;
        throw std::runtime_error(std::string("invalid value for '") + key + "'");
    }
    const std::string name = upper(v.get<std::string>());
    for (const auto& e : table) if (name == e.name) return e.value;
    throw std::runtime_error(std::string("unknown ") + key + " '" + name + "'");
}

glm::vec3 vec3From(const nlohmann::json& j, const char* key, const glm::vec3& fallback) {
    if (!j.contains(key)) return fallback;
    const auto& v = j.at(key);
    if (v.is_array() && v.size() >= 3) return {v[0].get<float>(), v[1].get<float>(), v[2].get<float>()};
    if (v.is_object()) return {v.value("x", fallback.x), v.value("y", fallback.y), v.value("z", fallback.z)};
    throw std::runtime_error(std::string("'") + key + "' must be [x, y, z]");
}

glm::vec2 vec2From(const nlohmann::json& j, const char* key, const glm::vec2& fallback) {
    if (!j.contains(key)) return fallback;
    const auto& v = j.at(key);
    if (v.is_array() && v.size() >= 2) return {v[0].get<float>(), v[1].get<float>()};
    if (v.is_object()) return {v.value("x", fallback.x), v.value("y", fallback.y)};
    throw std::runtime_error(std::string("'") + key + "' must be [min, max]");
}

template <typename V>
std::unordered_map<std::string, V> mapFrom(const nlohmann::json& j, const char* key, V (*read)(const nlohmann::json&)) {
    std::unordered_map<std::string, V> out;
    if (!j.contains(key)) return out;
    for (auto it = j.at(key).begin(); it != j.at(key).end(); ++it) out[it.key()] = read(it.value());
    return out;
}

glm::vec3 readVec3Value(const nlohmann::json& v) {
    if (v.is_array() && v.size() >= 3) return {v[0].get<float>(), v[1].get<float>(), v[2].get<float>()};
    return {v.value("x", 0.0f), v.value("y", 0.0f), v.value("z", 0.0f)};
}
float readFloatValue(const nlohmann::json& v) { return v.get<float>(); }

// ---------------------------------------------------------------- binary I/O helpers
template <typename T>
void writePod(std::ofstream& f, const T& v) {
    static_assert(std::is_trivially_copyable_v<T>);
    f.write(reinterpret_cast<const char*>(&v), sizeof(T));
}
template <typename T>
bool readPod(std::ifstream& f, T& v) {
    static_assert(std::is_trivially_copyable_v<T>);
    f.read(reinterpret_cast<char*>(&v), sizeof(T));
    return static_cast<bool>(f);
}
void writeString(std::ofstream& f, const std::string& s) {
    writePod(f, static_cast<uint32_t>(s.size()));
    f.write(s.data(), static_cast<std::streamsize>(s.size()));
}
bool readString(std::ifstream& f, std::string& s) {
    uint32_t n = 0;
    if (!readPod(f, n) || n > (1u << 24)) return false;
    s.resize(n);
    f.read(s.data(), n);
    return static_cast<bool>(f);
}
template <typename T>
void writeVector(std::ofstream& f, const std::vector<T>& v) {
    writePod(f, static_cast<uint32_t>(v.size()));
    if (!v.empty()) f.write(reinterpret_cast<const char*>(v.data()), static_cast<std::streamsize>(v.size() * sizeof(T)));
}
template <typename T>
bool readVector(std::ifstream& f, std::vector<T>& v) {
    uint32_t n = 0;
    if (!readPod(f, n) || n > (1u << 26)) return false;
    v.resize(n);
    if (n) f.read(reinterpret_cast<char*>(v.data()), static_cast<std::streamsize>(n * sizeof(T)));
    return static_cast<bool>(f);
}

constexpr uint32_t kMechPackMagic = 0x4D454348;   // "MECH"
constexpr uint32_t kMechPackVersion = 1;

void writeMesh(std::ofstream& f, const mt::Mesh& mesh) {
    writeString(f, mesh.name);
    writePod(f, static_cast<uint32_t>(mesh.submeshes.size()));
    for (const auto& sub : mesh.submeshes) {
        writeString(f, sub.name);
        writePod(f, sub.materialIndex);
        writePod(f, sub.transform);
        writeVector(f, sub.vertices);   // mt::Vertex is plain glm data
        writeVector(f, sub.indices);
    }
    writePod(f, static_cast<uint32_t>(mesh.morphTargetNames.size()));
    for (size_t i = 0; i < mesh.morphTargetNames.size(); ++i) {
        writeString(f, mesh.morphTargetNames[i]);
        writeVector(f, i < mesh.morphTargetPositions.size() ? mesh.morphTargetPositions[i] : std::vector<glm::vec3>{});
        writeVector(f, i < mesh.morphTargetNormals.size() ? mesh.morphTargetNormals[i] : std::vector<glm::vec3>{});
    }
}

std::shared_ptr<mt::Mesh> readMesh(std::ifstream& f) {
    auto mesh = std::make_shared<mt::Mesh>();
    uint32_t submeshCount = 0;
    if (!readString(f, mesh->name) || !readPod(f, submeshCount) || submeshCount > 4096) return nullptr;
    mesh->submeshes.resize(submeshCount);
    for (auto& sub : mesh->submeshes) {
        if (!readString(f, sub.name) || !readPod(f, sub.materialIndex) || !readPod(f, sub.transform) ||
            !readVector(f, sub.vertices) || !readVector(f, sub.indices)) {
            return nullptr;
        }
    }
    uint32_t morphCount = 0;
    if (!readPod(f, morphCount) || morphCount > 4096) return nullptr;
    mesh->morphTargetNames.resize(morphCount);
    mesh->morphTargetPositions.resize(morphCount);
    mesh->morphTargetNormals.resize(morphCount);
    for (uint32_t i = 0; i < morphCount; ++i) {
        if (!readString(f, mesh->morphTargetNames[i]) || !readVector(f, mesh->morphTargetPositions[i]) ||
            !readVector(f, mesh->morphTargetNormals[i])) {
            return nullptr;
        }
    }
    mesh->calculateBoundingVolumes();
    mesh->updateCounts();
    return mesh;
}

// All vertices of a mesh in submesh order (the order morph target deltas use).
std::vector<glm::vec3> flattenPositions(const mt::Mesh& mesh) {
    std::vector<glm::vec3> out;
    for (const auto& sub : mesh.submeshes)
        for (const auto& v : sub.vertices) out.push_back(v.position);
    return out;
}

std::atomic<MechHandle> g_nextMechHandle{1};

} // namespace

MechHandle allocateMechAssetHandle() {
    return g_nextMechHandle.fetch_add(1);
}

void releaseMechAssetResources(const MechAsset& asset) {
    std::unordered_set<uint32_t> handles;
    for (const auto& module : asset.modules) {
        for (MeshHandle h : module.lodMeshes) if (h) handles.insert(h);
    }
    if (asset.skeleton) handles.insert(asset.skeleton);
    if (asset.physicsRig) handles.insert(asset.physicsRig);
    for (uint32_t h : handles) store().release(h);
}

// =====================================================================
// MechGenerator
// =====================================================================

MechGenerator::MechGenerator() = default;
MechGenerator::~MechGenerator() = default;

MechDefinitionParams MechGenerator::parseDefinition(const std::string& filePath) {
    std::ifstream file(filePath);
    if (!file.is_open()) {
        throw std::runtime_error("Could not open mech definition: " + filePath);
    }
    nlohmann::json j;
    try {
        j = nlohmann::json::parse(file);
    } catch (const std::exception& e) {
        throw std::runtime_error("Invalid JSON in " + filePath + ": " + e.what());
    }

    MechDefinitionParams params;
    params.name = j.value("name", std::filesystem::path(filePath).stem().string());
    params.description = j.value("description", std::string());
    params.skeletonTemplate = j.value("skeletonTemplate", std::string());
    params.enableGPUAcceleration = j.value("enableGPUAcceleration", true);
    params.enableHotReload = j.value("enableHotReload", true);

    for (const auto& m : j.value("modules", nlohmann::json::array())) {
        ModuleDefinition def;
        def.id = m.at("id").get<std::string>();
        def.type = parseEnum(m, "type", kModuleTypes, ModuleType::CHASSIS);
        def.meshPath = m.value("meshPath", std::string());
        def.attachBone = m.value("attachBone", std::string());
        def.attachOffset = vec3From(m, "attachOffset", glm::vec3(0.0f));
        def.attachRotation = vec3From(m, "attachRotation", glm::vec3(0.0f));
        def.mass = m.value("mass", def.mass);
        def.weldToParent = m.value("weldToParent", def.weldToParent);
        def.childModules = m.value("childModules", std::vector<std::string>{});
        def.colliderType = parseEnum(m, "colliderType", kColliderTypes, def.colliderType);
        def.colliderSize = vec3From(m, "colliderSize", def.colliderSize);
        def.generateCollision = m.value("generateCollision", def.generateCollision);
        def.enableLOD = m.value("enableLOD", def.enableLOD);
        if (m.contains("lodScreenSizes")) def.lodScreenSizes = m.at("lodScreenSizes").get<std::vector<float>>();
        params.modules.push_back(std::move(def));
    }

    for (const auto& p : j.value("morphProfiles", nlohmann::json::array())) {
        MorphProfile profile;
        profile.name = p.at("name").get<std::string>();
        profile.fromForm = parseEnum(p, "fromForm", kFormTypes, FormType::WALKER);
        profile.toForm = parseEnum(p, "toForm", kFormTypes, FormType::WALKER);
        profile.duration = p.value("duration", profile.duration);
        profile.curveType = parseEnum(p, "curveType", kCurveTypes, profile.curveType);
        profile.customCurve = p.value("customCurve", std::vector<float>{});
        profile.moduleTransforms = mapFrom<glm::vec3>(p, "moduleTransforms", &readVec3Value);
        profile.moduleScales = mapFrom<glm::vec3>(p, "moduleScales", &readVec3Value);
        profile.moduleOpacities = mapFrom<float>(p, "moduleOpacities", &readFloatValue);
        params.morphProfiles.push_back(std::move(profile));
    }

    if (j.contains("physicsRig")) {
        const auto& r = j.at("physicsRig");
        auto& rig = params.physicsRig;
        rig.totalMass = r.value("totalMass", rig.totalMass);
        rig.moduleMasses = mapFrom<float>(r, "moduleMasses", &readFloatValue);
        rig.centerOfMass = vec3From(r, "centerOfMass", rig.centerOfMass);
        rig.enableGravity = r.value("enableGravity", rig.enableGravity);
        rig.enableCollision = r.value("enableCollision", rig.enableCollision);
        rig.linearDamping = r.value("linearDamping", rig.linearDamping);
        rig.angularDamping = r.value("angularDamping", rig.angularDamping);
        for (const auto& jj : r.value("joints", nlohmann::json::array())) {
            JointConstraint joint;
            joint.jointName = jj.at("jointName").get<std::string>();
            joint.type = parseEnum(jj, "type", kJointTypes, JointType::HINGE);
            joint.axis = vec3From(jj, "axis", joint.axis);
            joint.limits = vec2From(jj, "limits", joint.limits);
            joint.stiffness = jj.value("stiffness", joint.stiffness);
            joint.damping = jj.value("damping", joint.damping);
            joint.enableMotor = jj.value("enableMotor", joint.enableMotor);
            joint.motorTargetVelocity = jj.value("motorTargetVelocity", joint.motorTargetVelocity);
            joint.motorMaxForce = jj.value("motorMaxForce", joint.motorMaxForce);
            rig.joints.push_back(std::move(joint));
        }
    }

    for (const auto& l : j.value("lods", nlohmann::json::array())) {
        LODDefinition lod;
        lod.quality = parseEnum(l, "quality", kLodQualities, LODQuality::HIGH);
        lod.screenSize = l.value("screenSize", 0.1f);
        lod.meshDecimateRatio = l.value("meshDecimateRatio", lod.meshDecimateRatio);
        lod.morphDetailRatio = l.value("morphDetailRatio", lod.morphDetailRatio);
        lod.preserveBorders = l.value("preserveBorders", lod.preserveBorders);
        lod.preserveUVSeams = l.value("preserveUVSeams", lod.preserveUVSeams);
        lod.maxTriangles = l.value("maxTriangles", lod.maxTriangles);
        params.lods.push_back(lod);
    }
    return params;
}

bool MechGenerator::validateDefinition(const MechDefinitionParams& params) {
    validationErrors_.clear();
    if (params.name.empty()) validationErrors_.push_back("Mech name is empty");
    if (params.modules.empty()) validationErrors_.push_back("Mech has no modules");

    std::unordered_set<std::string> ids;
    for (const auto& module : params.modules) {
        if (!ids.insert(module.id).second) validationErrors_.push_back("Duplicate module id '" + module.id + "'");
        validateModule(module);
    }
    for (const auto& module : params.modules) {
        for (const auto& child : module.childModules) {
            if (!ids.count(child)) validationErrors_.push_back("Module '" + module.id + "' references unknown child '" + child + "'");
            if (child == module.id) validationErrors_.push_back("Module '" + module.id + "' lists itself as a child");
        }
    }
    for (const auto& profile : params.morphProfiles) validateMorphProfile(profile, params);
    validatePhysicsRig(params.physicsRig);
    validateLODs(params.lods);
    return validationErrors_.empty();
}

std::vector<std::string> MechGenerator::getValidationErrors() const {
    return validationErrors_;
}

bool MechGenerator::validateModule(const ModuleDefinition& module) {
    const size_t before = validationErrors_.size();
    const std::string where = "Module '" + module.id + "': ";
    if (module.id.empty()) validationErrors_.push_back("Module with empty id");
    if (!(module.mass > 0.0f)) validationErrors_.push_back(where + "mass must be positive");
    if (module.colliderSize.x <= 0.0f || module.colliderSize.y <= 0.0f || module.colliderSize.z <= 0.0f)
        validationErrors_.push_back(where + "collider size must be positive");
    if (!module.meshPath.empty() && !std::filesystem::exists(module.meshPath))
        validationErrors_.push_back(where + "mesh file not found: " + module.meshPath);
    for (size_t i = 1; i < module.lodScreenSizes.size(); ++i) {
        if (module.lodScreenSizes[i] > module.lodScreenSizes[i - 1]) {
            validationErrors_.push_back(where + "LOD screen sizes must be descending");
            break;
        }
    }
    return validationErrors_.size() == before;
}

bool MechGenerator::validateMorphProfile(const MorphProfile& profile, const MechDefinitionParams& params) {
    const size_t before = validationErrors_.size();
    const std::string where = "Morph profile '" + profile.name + "': ";
    if (profile.name.empty()) validationErrors_.push_back("Morph profile with empty name");
    if (!(profile.duration > 0.0f)) validationErrors_.push_back(where + "duration must be positive");
    if (profile.curveType == MorphCurveType::CUSTOM && profile.customCurve.size() < 2)
        validationErrors_.push_back(where + "custom curve needs at least two samples");
    auto known = [&](const std::string& id) {
        return std::any_of(params.modules.begin(), params.modules.end(), [&](const ModuleDefinition& m) { return m.id == id; });
    };
    for (const auto& [id, v] : profile.moduleTransforms) if (!known(id)) validationErrors_.push_back(where + "unknown module '" + id + "'");
    for (const auto& [id, v] : profile.moduleScales) {
        if (!known(id)) validationErrors_.push_back(where + "unknown module '" + id + "'");
        if (v.x <= 0.0f || v.y <= 0.0f || v.z <= 0.0f) validationErrors_.push_back(where + "scale for '" + id + "' must be positive");
    }
    for (const auto& [id, v] : profile.moduleOpacities) {
        if (!known(id)) validationErrors_.push_back(where + "unknown module '" + id + "'");
        if (v < 0.0f || v > 1.0f) validationErrors_.push_back(where + "opacity for '" + id + "' must be in [0, 1]");
    }
    return validationErrors_.size() == before;
}

bool MechGenerator::validatePhysicsRig(const PhysicsRigDefinition& rig) {
    const size_t before = validationErrors_.size();
    if (!(rig.totalMass > 0.0f)) validationErrors_.push_back("Physics rig: total mass must be positive");
    if (rig.linearDamping < 0.0f || rig.angularDamping < 0.0f) validationErrors_.push_back("Physics rig: damping cannot be negative");
    for (const auto& [id, mass] : rig.moduleMasses)
        if (!(mass > 0.0f)) validationErrors_.push_back("Physics rig: mass of '" + id + "' must be positive");
    for (const auto& joint : rig.joints) {
        const std::string where = "Joint '" + joint.jointName + "': ";
        if (joint.jointName.empty()) validationErrors_.push_back("Joint with empty name");
        if (joint.limits.x > joint.limits.y) validationErrors_.push_back(where + "lower limit exceeds upper limit");
        if (joint.stiffness < 0.0f || joint.damping < 0.0f) validationErrors_.push_back(where + "stiffness/damping cannot be negative");
        if (glm::length(joint.axis) < 1e-6f) validationErrors_.push_back(where + "axis must be non-zero");
    }
    return validationErrors_.size() == before;
}

bool MechGenerator::validateLODs(const std::vector<LODDefinition>& lods) {
    const size_t before = validationErrors_.size();
    for (const auto& lod : lods) {
        if (!(lod.screenSize > 0.0f)) validationErrors_.push_back("LOD: screen size must be positive");
        if (lod.meshDecimateRatio < 0.0f || lod.meshDecimateRatio >= 1.0f) validationErrors_.push_back("LOD: decimate ratio must be in [0, 1)");
        if (lod.morphDetailRatio < 0.0f || lod.morphDetailRatio > 1.0f) validationErrors_.push_back("LOD: morph detail ratio must be in [0, 1]");
        if (lod.maxTriangles <= 0) validationErrors_.push_back("LOD: max triangles must be positive");
    }
    return validationErrors_.size() == before;
}

// =====================================================================
// ModuleAssembler
// =====================================================================

ModuleAssembler::ModuleAssembler() = default;
ModuleAssembler::~ModuleAssembler() = default;

namespace {

// Procedural stand-in geometry sized by the module's collider when no mesh file is given.
std::shared_ptr<mt::Mesh> buildModuleMesh(const ModuleDefinition& def) {
    if (!def.meshPath.empty()) {
        mt::MeshHandle handle = mt::MeshHandleFactory::createFromFile(def.meshPath);
        auto mesh = handle.getMesh();
        if (handle.handleId != 0) {
            // Keep our own reference; the GPU-managed registration is not needed here.
            mt::MeshHandleManager::getInstance().releaseHandle(handle.handleId);
        }
        if (mesh) return std::make_shared<mt::Mesh>(*mesh);
        Log::warn("MechAsset", "Could not load mesh '{}' for module '{}', using procedural geometry", def.meshPath, def.id);
    }
    const glm::vec3 s = def.colliderSize;
    switch (def.type) {
        case ModuleType::ARM:
        case ModuleType::LEG:
        case ModuleType::THRUSTER:
        case ModuleType::WEAPON:
            return mt::MeshGenerator::generateCylinder(0.5f * std::max(s.x, s.z), s.y, 16);
        case ModuleType::SENSOR:
        case ModuleType::COCKPIT:
            return mt::MeshGenerator::generateSphere(0.5f * std::max({s.x, s.y, s.z}), 16);
        case ModuleType::SHIELD:
            return mt::MeshGenerator::generateBox(s.x, s.y, std::max(0.05f, s.z * 0.15f));
        case ModuleType::CHASSIS:
        case ModuleType::UTILITY:
        default:
            return mt::MeshGenerator::generateBox(s.x, s.y, s.z);
    }
}

} // namespace

bool ModuleAssembler::assembleModules(const std::vector<ModuleDefinition>& modules,
                                      const std::string& skeletonTemplate,
                                      MechAsset& asset) {
    if (modules.empty()) return false;
    asset.modules.clear();

    // Parent lookup from the childModules lists.
    std::unordered_map<std::string, size_t> indexOf;
    for (size_t i = 0; i < modules.size(); ++i) indexOf[modules[i].id] = i;
    std::vector<int> parent(modules.size(), -1);
    for (size_t i = 0; i < modules.size(); ++i) {
        for (const auto& child : modules[i].childModules) {
            auto it = indexOf.find(child);
            if (it != indexOf.end() && it->second != i) parent[it->second] = static_cast<int>(i);
        }
    }

    auto skeleton = std::make_shared<Mechs::MechSkeletonData>();
    skeleton->name = skeletonTemplate.empty() ? asset.name + "_skeleton" : skeletonTemplate;

    for (size_t i = 0; i < modules.size(); ++i) {
        const auto& def = modules[i];
        auto mesh = buildModuleMesh(def);
        if (!mesh || !mesh->isValid()) {
            Log::error("MechAsset", "Failed to build geometry for module '{}'", def.id);
            return false;
        }
        mesh->name = asset.name + "_" + def.id;

        ModuleData data;
        data.handle = allocateMechAssetHandle();
        data.id = def.id;
        data.type = def.type;
        data.localTransform = composeTransform(def.attachOffset, def.attachRotation);
        data.worldTransform = data.localTransform;
        data.physicsBody = 0;
        data.lodMeshes.push_back(store().add(mesh));
        asset.modules.push_back(std::move(data));

        Mechs::MechBone bone;
        bone.name = def.attachBone.empty() ? def.id : def.attachBone;
        bone.parent = parent[i];
        bone.localTransform = asset.modules.back().localTransform;
        skeleton->bones.push_back(bone);
    }

    // World transforms follow the hierarchy (parents may be listed after children).
    std::vector<bool> resolved(modules.size(), false);
    std::function<const glm::mat4&(size_t, int)> world = [&](size_t i, int depth) -> const glm::mat4& {
        if (!resolved[i]) {
            resolved[i] = true;   // set first: protects against cycles
            if (parent[i] >= 0 && depth < static_cast<int>(modules.size())) {
                asset.modules[i].worldTransform = world(static_cast<size_t>(parent[i]), depth + 1) * asset.modules[i].localTransform;
            }
        }
        return asset.modules[i].worldTransform;
    };
    for (size_t i = 0; i < modules.size(); ++i) world(i, 0);

    // IK chains: root-to-tip paths of the module hierarchy.
    for (size_t i = 0; i < modules.size(); ++i) {
        if (!modules[i].childModules.empty()) continue;   // leaves only
        std::vector<int> chain;
        for (int b = static_cast<int>(i); b >= 0 && chain.size() <= modules.size(); b = parent[b]) chain.push_back(b);
        if (chain.size() > 1) {
            std::reverse(chain.begin(), chain.end());
            skeleton->ikChains.push_back(std::move(chain));
        }
    }

    for (size_t i = 0; i < asset.modules.size(); ++i) {
        if (!bakeSkinnedMesh(asset.modules[i], static_cast<int>(i))) return false;
    }
    weldModuleSeams(asset.modules, modules);
    if (!remapBoneIndices(asset.modules, skeleton->bones.size())) return false;

    asset.skeleton = store().add(skeleton);
    return true;
}

bool ModuleAssembler::weldModuleSeams(const std::vector<ModuleData>& modules, const std::vector<ModuleDefinition>& definitions) {
    for (size_t i = 0; i < modules.size() && i < definitions.size(); ++i) {
        if (!definitions[i].weldToParent) continue;
        if (auto mesh = meshFor(modules[i].lodMeshes.empty() ? 0 : modules[i].lodMeshes[0])) {
            mesh->weldVertices(0.001f);
            mesh->updateCounts();
        }
    }
    return true;
}

bool ModuleAssembler::bakeSkinnedMesh(const ModuleData& module, int boneIndex) {
    auto mesh = meshFor(module.lodMeshes.empty() ? 0 : module.lodMeshes[0]);
    if (!mesh) return false;
    for (auto& sub : mesh->submeshes) {
        for (auto& v : sub.vertices) {
            v.boneIndices = glm::uvec4(static_cast<unsigned>(boneIndex), 0u, 0u, 0u);
            v.boneWeights = glm::vec4(1.0f, 0.0f, 0.0f, 0.0f);
        }
    }
    return true;
}

bool ModuleAssembler::remapBoneIndices(const std::vector<ModuleData>& modules, size_t boneCount) {
    bool ok = true;
    for (size_t i = 0; i < modules.size(); ++i) {
        auto mesh = meshFor(modules[i].lodMeshes.empty() ? 0 : modules[i].lodMeshes[0]);
        if (!mesh) continue;
        for (auto& sub : mesh->submeshes) {
            for (auto& v : sub.vertices) {
                for (int c = 0; c < 4; ++c) {
                    if (v.boneWeights[c] > 0.0f && v.boneIndices[c] >= boneCount) {
                        // Out-of-range influence: rebind the vertex to its module bone.
                        v.boneIndices = glm::uvec4(static_cast<unsigned>(i), 0u, 0u, 0u);
                        v.boneWeights = glm::vec4(1.0f, 0.0f, 0.0f, 0.0f);
                        ok = ok && i < boneCount;
                        break;
                    }
                }
            }
        }
    }
    return ok;
}

// =====================================================================
// MorphGenerator
// =====================================================================

MorphGenerator::MorphGenerator() = default;
MorphGenerator::~MorphGenerator() = default;

bool MorphGenerator::generateMorphTargets(const std::vector<MorphProfile>& profiles,
                                          const std::vector<ModuleData>& modules,
                                          MechAsset& asset) {
    // `modules` may alias asset.modules, so morph target handles are written by index.
    const size_t count = modules.size();
    for (const auto& profile : profiles) {
        for (size_t i = 0; i < count; ++i) {
            const int target = computeVertexDeltas(profile, modules[i]);
            if (target < 0) return false;
            // Handle = 1-based index of the morph target on the module mesh.
            asset.modules[i].morphTargets.push_back(static_cast<MorphTargetHandle>(target + 1));
        }
    }
    return true;
}

int MorphGenerator::computeVertexDeltas(const MorphProfile& profile, const ModuleData& module) {
    auto mesh = meshFor(module.lodMeshes.empty() ? 0 : module.lodMeshes[0]);
    if (!mesh) return -1;

    auto offsetIt = profile.moduleTransforms.find(module.id);
    auto scaleIt = profile.moduleScales.find(module.id);
    auto opacityIt = profile.moduleOpacities.find(module.id);
    const glm::vec3 offset = offsetIt != profile.moduleTransforms.end() ? offsetIt->second : glm::vec3(0.0f);
    const glm::vec3 scale = scaleIt != profile.moduleScales.end() ? scaleIt->second : glm::vec3(1.0f);
    // A fully transparent target form collapses the module towards its origin.
    const float opacity = opacityIt != profile.moduleOpacities.end() ? std::clamp(opacityIt->second, 0.0f, 1.0f) : 1.0f;
    const glm::vec3 effectiveScale = scale * (0.05f + 0.95f * opacity);

    std::vector<glm::vec3> positionDeltas;
    std::vector<glm::vec3> normalDeltas;
    for (const auto& sub : mesh->submeshes) {
        for (const auto& v : sub.vertices) {
            const glm::vec3 target = v.position * effectiveScale + offset;
            positionDeltas.push_back(target - v.position);
            glm::vec3 n = v.normal / glm::max(effectiveScale, glm::vec3(1e-4f));   // inverse-transpose of a scale
            n = glm::length(n) > 1e-8f ? glm::normalize(n) : v.normal;
            normalDeltas.push_back(n - v.normal);
        }
    }
    mesh->morphTargetNames.push_back(profile.name);
    mesh->morphTargetPositions.push_back(std::move(positionDeltas));
    mesh->morphTargetNormals.push_back(std::move(normalDeltas));
    return static_cast<int>(mesh->morphTargetNames.size()) - 1;
}

float MorphGenerator::evaluateMorphCurve(MorphCurveType curveType, float t, const std::vector<float>& customCurve) {
    t = std::clamp(t, 0.0f, 1.0f);
    switch (curveType) {
        case MorphCurveType::LINEAR:      return t;
        case MorphCurveType::EASE_IN:     return t * t;
        case MorphCurveType::EASE_OUT:    return 1.0f - (1.0f - t) * (1.0f - t);
        case MorphCurveType::EASE_IN_OUT: return t < 0.5f ? 2.0f * t * t : 1.0f - 2.0f * (1.0f - t) * (1.0f - t);
        case MorphCurveType::SMOOTHSTEP:  return t * t * (3.0f - 2.0f * t);
        case MorphCurveType::CUSTOM: {
            if (customCurve.empty()) return t;
            if (customCurve.size() == 1) return customCurve[0];
            // Samples are evenly spaced over [0, 1]; linear interpolation between them.
            const float x = t * static_cast<float>(customCurve.size() - 1);
            const size_t i = std::min(static_cast<size_t>(x), customCurve.size() - 2);
            return glm::mix(customCurve[i], customCurve[i + 1], x - static_cast<float>(i));
        }
    }
    return t;
}

// =====================================================================
// PhysicsRigBuilder
// =====================================================================

PhysicsRigBuilder::PhysicsRigBuilder() = default;
PhysicsRigBuilder::~PhysicsRigBuilder() = default;

float PhysicsRigBuilder::moduleMass(const ModuleData& module, const PhysicsRigDefinition& rigDef, size_t moduleCount) const {
    auto it = rigDef.moduleMasses.find(module.id);
    if (it != rigDef.moduleMasses.end()) return it->second;
    // Remaining mass shared by the modules without an explicit mass.
    float assigned = 0.0f;
    size_t explicitCount = 0;
    for (const auto& [id, mass] : rigDef.moduleMasses) { assigned += mass; ++explicitCount; }
    const size_t remaining = moduleCount > explicitCount ? moduleCount - explicitCount : 1;
    return std::max(rigDef.totalMass - assigned, 0.0f) / static_cast<float>(remaining);
}

bool PhysicsRigBuilder::generateCollider(const ModuleData& module, float mass, Mechs::MechColliderShape& out) const {
    auto mesh = meshFor(module.lodMeshes.empty() ? 0 : module.lodMeshes[0]);
    if (!mesh) return false;
    mesh->calculateBoundingVolumes();
    const glm::vec3 extents = glm::max(mesh->boundingBoxMax - mesh->boundingBoxMin, glm::vec3(1e-3f));
    const glm::vec3 center = (mesh->boundingBoxMax + mesh->boundingBoxMin) * 0.5f;

    switch (module.type) {
        case ModuleType::ARM:
        case ModuleType::LEG:
        case ModuleType::THRUSTER:
        case ModuleType::WEAPON:
            out.type = Mechs::MechColliderShape::Type::Capsule;
            out.size = glm::vec3(0.5f * std::max(extents.x, extents.z), extents.y, 0.0f);
            break;
        case ModuleType::SENSOR:
        case ModuleType::COCKPIT:
            out.type = Mechs::MechColliderShape::Type::Sphere;
            out.size = glm::vec3(0.5f * std::max({extents.x, extents.y, extents.z}), 0.0f, 0.0f);
            break;
        default:
            out.type = Mechs::MechColliderShape::Type::Box;
            out.size = extents;
            break;
    }
    out.transform = module.worldTransform * glm::translate(glm::mat4(1.0f), center);
    out.mass = mass;
    return true;
}

bool PhysicsRigBuilder::buildPhysicsRig(const PhysicsRigDefinition& rigDef,
                                        const std::vector<ModuleData>& modules,
                                        MechAsset& asset) {
    auto rig = std::make_shared<Mechs::MechPhysicsData>();
    rig->name = asset.name + "_physics";

    glm::vec3 weightedCenter(0.0f);
    for (const auto& module : modules) {
        Mechs::MechColliderShape shape;
        if (!generateCollider(module, moduleMass(module, rigDef, modules.size()), shape)) return false;
        rig->totalMass += shape.mass;
        weightedCenter += glm::vec3(shape.transform[3]) * shape.mass;
        rig->shapes.push_back(shape);
    }
    rig->centerOfMass = glm::length(rigDef.centerOfMass) > 0.0f || rig->totalMass <= 0.0f
                            ? rigDef.centerOfMass
                            : weightedCenter / rig->totalMass;

    if (!rigDef.joints.empty()) {
        float damping = 0.0f, stiffness = 0.0f;
        for (const auto& joint : rigDef.joints) {
            damping += joint.damping;
            stiffness += joint.stiffness;
        }
        rig->jointDamping = damping / static_cast<float>(rigDef.joints.size());
        rig->jointStiffness = stiffness / static_cast<float>(rigDef.joints.size());
    }

    // Joint limits/stiffness go onto the skeleton bones of the same name.
    if (auto skeleton = store().get<Mechs::MechSkeletonData>(asset.skeleton)) {
        for (const auto& joint : rigDef.joints) {
            for (auto& bone : skeleton->bones) {
                if (bone.name != joint.jointName) continue;
                bone.minAngleDeg = joint.limits.x;
                bone.maxAngleDeg = joint.limits.y;
                bone.stiffness = joint.stiffness;
                bone.damping = joint.damping;
            }
        }
    }

    asset.physicsRig = store().add(rig);
    for (auto& module : asset.modules) module.physicsBody = asset.physicsRig;
    return asset.physicsRig != 0;
}

// =====================================================================
// LODBuilder
// =====================================================================

LODBuilder::LODBuilder() = default;
LODBuilder::~LODBuilder() = default;

MeshHandle LODBuilder::decimateMesh(MeshHandle baseMesh, const LODDefinition& lod) {
    auto base = meshFor(baseMesh);
    if (!base) return 0;
    mt::SimplificationParams params;
    params.targetRatio = std::clamp(1.0f - lod.meshDecimateRatio, 0.01f, 1.0f);
    const uint32_t budget = static_cast<uint32_t>(std::max(lod.maxTriangles, 1));
    if (base->triangleCount * params.targetRatio > budget) params.targetTriangleCount = budget;
    params.preserveBoundary = lod.preserveBorders;
    params.preserveUVs = lod.preserveUVSeams;
    std::shared_ptr<mt::Mesh> simplified = params.targetRatio >= 1.0f && base->triangleCount <= budget
                                               ? std::make_shared<mt::Mesh>(*base)
                                               : mt::MeshGenerator::simplifyMesh(base, params);
    if (!simplified || !simplified->isValid()) return 0;
    simplified->name = base->name + "_lod" + std::to_string(static_cast<int>(lod.quality));
    simplified->lods.clear();
    return store().add(simplified);
}

bool LODBuilder::downsampleMorphTargets(MeshHandle baseMesh, MeshHandle lodMesh, float detailRatio) {
    auto base = meshFor(baseMesh);
    auto lod = meshFor(lodMesh);
    if (!base || !lod) return false;
    const std::vector<glm::vec3> basePositions = flattenPositions(*base);
    const std::vector<glm::vec3> lodPositions = flattenPositions(*lod);
    lod->morphTargetNames.clear();
    lod->morphTargetPositions.clear();
    lod->morphTargetNormals.clear();
    if (base->morphTargetNames.empty() || basePositions.empty()) return true;

    // Nearest base vertex for every LOD vertex, via a uniform grid.
    glm::vec3 minP = basePositions[0], maxP = basePositions[0];
    for (const auto& p : basePositions) { minP = glm::min(minP, p); maxP = glm::max(maxP, p); }
    const float cellSize = std::max(glm::length(maxP - minP) / 32.0f, 1e-4f);
    auto cellOf = [&](const glm::vec3& p) { return glm::ivec3(glm::floor((p - minP) / cellSize)); };
    auto key = [](const glm::ivec3& c) {
        return (static_cast<int64_t>(c.x) * 73856093) ^ (static_cast<int64_t>(c.y) * 19349663) ^ (static_cast<int64_t>(c.z) * 83492791);
    };
    std::unordered_map<int64_t, std::vector<uint32_t>> grid;
    for (uint32_t i = 0; i < basePositions.size(); ++i) grid[key(cellOf(basePositions[i]))].push_back(i);

    std::vector<uint32_t> nearest(lodPositions.size(), 0);
    for (size_t v = 0; v < lodPositions.size(); ++v) {
        const glm::ivec3 c = cellOf(lodPositions[v]);
        float best = std::numeric_limits<float>::max();
        for (int radius = 1; radius <= 3 && best == std::numeric_limits<float>::max(); ++radius) {
            for (int dx = -radius; dx <= radius; ++dx)
                for (int dy = -radius; dy <= radius; ++dy)
                    for (int dz = -radius; dz <= radius; ++dz) {
                        auto it = grid.find(key(c + glm::ivec3(dx, dy, dz)));
                        if (it == grid.end()) continue;
                        for (uint32_t i : it->second) {
                            const glm::vec3 d = basePositions[i] - lodPositions[v];
                            const float dist = glm::dot(d, d);
                            if (dist < best) { best = dist; nearest[v] = i; }
                        }
                    }
        }
        if (best == std::numeric_limits<float>::max()) {
            for (uint32_t i = 0; i < basePositions.size(); ++i) {
                const glm::vec3 d = basePositions[i] - lodPositions[v];
                const float dist = glm::dot(d, d);
                if (dist < best) { best = dist; nearest[v] = i; }
            }
        }
    }

    // Reduced morph detail blends each delta towards the module-average delta.
    const float detail = std::clamp(detailRatio, 0.0f, 1.0f);
    for (size_t t = 0; t < base->morphTargetNames.size(); ++t) {
        const auto& positions = base->morphTargetPositions[t];
        const auto& normals = t < base->morphTargetNormals.size() ? base->morphTargetNormals[t] : std::vector<glm::vec3>{};
        glm::vec3 average(0.0f);
        for (const auto& d : positions) average += d;
        if (!positions.empty()) average /= static_cast<float>(positions.size());

        std::vector<glm::vec3> lodDeltas(lodPositions.size(), glm::vec3(0.0f));
        std::vector<glm::vec3> lodNormals(lodPositions.size(), glm::vec3(0.0f));
        for (size_t v = 0; v < lodPositions.size(); ++v) {
            const uint32_t src = nearest[v];
            if (src < positions.size()) lodDeltas[v] = glm::mix(average, positions[src], detail);
            if (src < normals.size()) lodNormals[v] = normals[src] * detail;
        }
        lod->morphTargetNames.push_back(base->morphTargetNames[t]);
        lod->morphTargetPositions.push_back(std::move(lodDeltas));
        lod->morphTargetNormals.push_back(std::move(lodNormals));
    }
    return true;
}

bool LODBuilder::generateLODs(const std::vector<LODDefinition>& lods,
                              const std::vector<ModuleData>& modules,
                              MechAsset& asset) {
    // `modules` may alias asset.modules: collect base handles first.
    std::vector<MeshHandle> bases;
    bases.reserve(modules.size());
    for (const auto& module : modules) bases.push_back(module.lodMeshes.empty() ? 0 : module.lodMeshes[0]);

    // lodMeshes[k + 1] corresponds to lods[k] (MechAsset::lods keeps the definition order).
    const std::vector<LODDefinition>& ordered = lods;

    for (size_t i = 0; i < bases.size(); ++i) {
        if (!bases[i]) return false;
        for (const auto& lod : ordered) {
            const MeshHandle lodMesh = decimateMesh(bases[i], lod);
            if (!lodMesh) {
                Log::error("MechAsset", "LOD generation failed for module '{}'", asset.modules[i].id);
                return false;
            }
            downsampleMorphTargets(bases[i], lodMesh, lod.morphDetailRatio);
            asset.modules[i].lodMeshes.push_back(lodMesh);
        }
        if (auto base = meshFor(bases[i])) {
            base->lodScreenSizes.clear();
            for (const auto& lod : ordered) base->lodScreenSizes.push_back(lod.screenSize);
        }
    }
    return true;
}

// =====================================================================
// PackageWriter (.mechpack, little-endian binary)
//
// header | metadata (name, flags, LOD table, skeleton) | module table (with meshes) | morph table | physics rig
// =====================================================================

PackageWriter::PackageWriter() = default;
PackageWriter::~PackageWriter() = default;

bool PackageWriter::writePackage(const MechAsset& asset, const std::string& filePath) {
    std::error_code ec;
    const auto dir = std::filesystem::path(filePath).parent_path();
    if (!dir.empty()) std::filesystem::create_directories(dir, ec);

    std::ofstream file(filePath, std::ios::binary | std::ios::trunc);
    if (!file.is_open()) {
        Log::error("MechAsset", "Cannot write mech package {}", filePath);
        return false;
    }
    MechPackHeader header;
    header.magic = kMechPackMagic;
    header.version = kMechPackVersion;
    header.moduleCount = static_cast<uint32_t>(asset.modules.size());
    header.morphProfileCount = static_cast<uint32_t>(asset.morphProfiles.size());
    header.lodCount = static_cast<uint32_t>(asset.lods.size());
    std::fill(std::begin(header.reserved), std::end(header.reserved), 0u);

    return writeHeader(header, file) && writeMetadata(asset, file) && writeModuleTable(asset.modules, file) &&
           writeMorphTable(asset.morphProfiles, file) && writePhysicsRig(asset.physicsRig, file) &&
           static_cast<bool>(file);
}

bool PackageWriter::writeHeader(const MechPackHeader& header, std::ofstream& file) {
    writePod(file, header);
    return static_cast<bool>(file);
}

bool PackageWriter::writeMetadata(const MechAsset& asset, std::ofstream& file) {
    writeString(file, asset.name);
    writePod(file, static_cast<uint8_t>(asset.gpuAccelerated ? 1 : 0));
    writePod(file, static_cast<int64_t>(std::chrono::duration_cast<std::chrono::milliseconds>(
        asset.creationTime.time_since_epoch()).count()));
    // LOD table
    for (const auto& lod : asset.lods) writePod(file, lod);
    // Skeleton
    auto skeleton = store().get<Mechs::MechSkeletonData>(asset.skeleton);
    writePod(file, static_cast<uint8_t>(skeleton ? 1 : 0));
    if (skeleton) {
        writeString(file, skeleton->name);
        writePod(file, static_cast<uint32_t>(skeleton->bones.size()));
        for (const auto& bone : skeleton->bones) {
            writeString(file, bone.name);
            writePod(file, bone.parent);
            writePod(file, bone.localTransform);
            writePod(file, bone.minAngleDeg);
            writePod(file, bone.maxAngleDeg);
            writePod(file, bone.stiffness);
            writePod(file, bone.damping);
        }
        writePod(file, static_cast<uint32_t>(skeleton->ikChains.size()));
        for (const auto& chain : skeleton->ikChains) writeVector(file, chain);
    }
    return static_cast<bool>(file);
}

bool PackageWriter::writeModuleTable(const std::vector<ModuleData>& modules, std::ofstream& file) {
    for (const auto& module : modules) {
        writeString(file, module.id);
        writePod(file, module.type);
        writePod(file, module.localTransform);
        writePod(file, module.worldTransform);
        writePod(file, static_cast<uint8_t>(module.isVisible ? 1 : 0));
        writePod(file, static_cast<uint8_t>(module.isActive ? 1 : 0));
        writeVector(file, module.morphTargets);
        writePod(file, static_cast<uint32_t>(module.lodMeshes.size()));
        for (MeshHandle h : module.lodMeshes) {
            auto mesh = meshFor(h);
            if (!mesh) {
                Log::error("MechAsset", "Module '{}' references missing mesh {}", module.id, h);
                return false;
            }
            writeMesh(file, *mesh);
        }
    }
    return static_cast<bool>(file);
}

bool PackageWriter::writeMorphTable(const std::vector<MorphProfile>& profiles, std::ofstream& file) {
    auto writeVec3Map = [&](const std::unordered_map<std::string, glm::vec3>& m) {
        writePod(file, static_cast<uint32_t>(m.size()));
        for (const auto& [k, v] : m) { writeString(file, k); writePod(file, v); }
    };
    for (const auto& profile : profiles) {
        writeString(file, profile.name);
        writePod(file, profile.fromForm);
        writePod(file, profile.toForm);
        writePod(file, profile.duration);
        writePod(file, profile.curveType);
        writeVector(file, profile.customCurve);
        writeVec3Map(profile.moduleTransforms);
        writeVec3Map(profile.moduleScales);
        writePod(file, static_cast<uint32_t>(profile.moduleOpacities.size()));
        for (const auto& [k, v] : profile.moduleOpacities) { writeString(file, k); writePod(file, v); }
    }
    return static_cast<bool>(file);
}

bool PackageWriter::writePhysicsRig(const PhysicsRigHandle& rig, std::ofstream& file) {
    auto data = store().get<Mechs::MechPhysicsData>(rig);
    writePod(file, static_cast<uint8_t>(data ? 1 : 0));
    if (!data) return static_cast<bool>(file);
    writeString(file, data->name);
    writePod(file, data->totalMass);
    writePod(file, data->centerOfMass);
    writePod(file, data->jointDamping);
    writePod(file, data->jointStiffness);
    writePod(file, static_cast<uint32_t>(data->shapes.size()));
    for (const auto& shape : data->shapes) {
        writePod(file, shape.type);
        writePod(file, shape.size);
        writePod(file, shape.transform);
        writePod(file, shape.mass);
    }
    return static_cast<bool>(file);
}

bool PackageWriter::readPackage(const std::string& filePath, MechAsset& asset) {
    std::ifstream file(filePath, std::ios::binary);
    if (!file.is_open()) return false;

    MechPackHeader header;
    if (!readHeader(header, file)) {
        Log::error("MechAsset", "{} is not a valid mech package", filePath);
        return false;
    }
    MechAsset loaded;
    const bool ok = readMetadata(loaded, header.lodCount, file) &&
                    readModuleTable(loaded.modules, header.moduleCount, file) &&
                    readMorphTable(loaded.morphProfiles, header.morphProfileCount, file) &&
                    readPhysicsRig(loaded.physicsRig, file);
    if (!ok) {
        Log::error("MechAsset", "Mech package {} is truncated or corrupt", filePath);
        releaseMechAssetResources(loaded);
        return false;
    }
    for (auto& module : loaded.modules) module.physicsBody = loaded.physicsRig;
    loaded.handle = asset.handle;
    loaded.packHandle = asset.packHandle;
    asset = loaded;
    return true;
}

bool PackageWriter::readHeader(MechPackHeader& header, std::ifstream& file) {
    return readPod(file, header) && header.magic == kMechPackMagic && header.version == kMechPackVersion &&
           header.moduleCount < 4096 && header.morphProfileCount < 4096 && header.lodCount < 64;
}

bool PackageWriter::readMetadata(MechAsset& asset, uint32_t lodCount, std::ifstream& file) {
    uint8_t gpu = 0;
    int64_t createdMs = 0;
    if (!readString(file, asset.name) || !readPod(file, gpu) || !readPod(file, createdMs)) return false;
    asset.gpuAccelerated = gpu != 0;
    asset.creationTime = std::chrono::system_clock::time_point(std::chrono::milliseconds(createdMs));
    asset.lods.resize(lodCount);
    for (auto& lod : asset.lods) if (!readPod(file, lod)) return false;

    uint8_t hasSkeleton = 0;
    if (!readPod(file, hasSkeleton)) return false;
    if (hasSkeleton) {
        auto skeleton = std::make_shared<Mechs::MechSkeletonData>();
        uint32_t boneCount = 0;
        if (!readString(file, skeleton->name) || !readPod(file, boneCount) || boneCount > 4096) return false;
        skeleton->bones.resize(boneCount);
        for (auto& bone : skeleton->bones) {
            if (!readString(file, bone.name) || !readPod(file, bone.parent) || !readPod(file, bone.localTransform) ||
                !readPod(file, bone.minAngleDeg) || !readPod(file, bone.maxAngleDeg) ||
                !readPod(file, bone.stiffness) || !readPod(file, bone.damping)) {
                return false;
            }
        }
        uint32_t chainCount = 0;
        if (!readPod(file, chainCount) || chainCount > 4096) return false;
        skeleton->ikChains.resize(chainCount);
        for (auto& chain : skeleton->ikChains) if (!readVector(file, chain)) return false;
        asset.skeleton = store().add(skeleton);
    }
    return true;
}

bool PackageWriter::readModuleTable(std::vector<ModuleData>& modules, uint32_t count, std::ifstream& file) {
    modules.clear();
    for (uint32_t m = 0; m < count; ++m) {
        ModuleData module;
        uint8_t visible = 1, active = 1;
        uint32_t lodCount = 0;
        if (!readString(file, module.id) || !readPod(file, module.type) || !readPod(file, module.localTransform) ||
            !readPod(file, module.worldTransform) || !readPod(file, visible) || !readPod(file, active) ||
            !readVector(file, module.morphTargets) || !readPod(file, lodCount) || lodCount > 64) {
            modules.push_back(std::move(module));
            return false;
        }
        module.isVisible = visible != 0;
        module.isActive = active != 0;
        module.handle = allocateMechAssetHandle();
        for (uint32_t l = 0; l < lodCount; ++l) {
            auto mesh = readMesh(file);
            if (!mesh) {
                modules.push_back(std::move(module));
                return false;
            }
            module.lodMeshes.push_back(store().add(mesh));
        }
        modules.push_back(std::move(module));
    }
    return true;
}

bool PackageWriter::readMorphTable(std::vector<MorphProfile>& profiles, uint32_t count, std::ifstream& file) {
    auto readVec3Map = [&](std::unordered_map<std::string, glm::vec3>& m) {
        uint32_t n = 0;
        if (!readPod(file, n) || n > 4096) return false;
        for (uint32_t i = 0; i < n; ++i) {
            std::string k;
            glm::vec3 v;
            if (!readString(file, k) || !readPod(file, v)) return false;
            m[k] = v;
        }
        return true;
    };
    profiles.clear();
    for (uint32_t p = 0; p < count; ++p) {
        MorphProfile profile;
        uint32_t opacityCount = 0;
        if (!readString(file, profile.name) || !readPod(file, profile.fromForm) || !readPod(file, profile.toForm) ||
            !readPod(file, profile.duration) || !readPod(file, profile.curveType) || !readVector(file, profile.customCurve) ||
            !readVec3Map(profile.moduleTransforms) || !readVec3Map(profile.moduleScales) ||
            !readPod(file, opacityCount) || opacityCount > 4096) {
            return false;
        }
        for (uint32_t i = 0; i < opacityCount; ++i) {
            std::string k;
            float v = 0.0f;
            if (!readString(file, k) || !readPod(file, v)) return false;
            profile.moduleOpacities[k] = v;
        }
        profiles.push_back(std::move(profile));
    }
    return true;
}

bool PackageWriter::readPhysicsRig(PhysicsRigHandle& rig, std::ifstream& file) {
    uint8_t present = 0;
    if (!readPod(file, present)) return false;
    rig = 0;
    if (!present) return true;
    auto data = std::make_shared<Mechs::MechPhysicsData>();
    uint32_t shapeCount = 0;
    if (!readString(file, data->name) || !readPod(file, data->totalMass) || !readPod(file, data->centerOfMass) ||
        !readPod(file, data->jointDamping) || !readPod(file, data->jointStiffness) ||
        !readPod(file, shapeCount) || shapeCount > 4096) {
        return false;
    }
    data->shapes.resize(shapeCount);
    for (auto& shape : data->shapes) {
        if (!readPod(file, shape.type) || !readPod(file, shape.size) || !readPod(file, shape.transform) ||
            !readPod(file, shape.mass)) {
            return false;
        }
    }
    rig = store().add(data);
    return true;
}

void filterMechAssetLODs(MechAsset& asset, LODQuality quality) {
    // Package LOD meshes are stored in sorted LOD-definition order after the base mesh
    // (lodMeshes[0] is always the full-detail mesh and is kept).
    std::vector<size_t> keep;
    for (size_t i = 0; i < asset.lods.size(); ++i) if (asset.lods[i].quality == quality) keep.push_back(i);
    for (auto& module : asset.modules) {
        std::vector<MeshHandle> lodMeshes;
        if (!module.lodMeshes.empty()) lodMeshes.push_back(module.lodMeshes[0]);
        for (size_t i = 0; i < asset.lods.size(); ++i) {
            const size_t meshIndex = i + 1;
            if (meshIndex >= module.lodMeshes.size()) break;
            if (std::find(keep.begin(), keep.end(), i) != keep.end()) lodMeshes.push_back(module.lodMeshes[meshIndex]);
            else store().release(module.lodMeshes[meshIndex]);
        }
        module.lodMeshes = std::move(lodMeshes);
    }
    std::vector<LODDefinition> lods;
    for (size_t i : keep) lods.push_back(asset.lods[i]);
    asset.lods = std::move(lods);
}
// =====================================================================
// MechLoader
// =====================================================================

MechLoader::MechLoader() = default;

MechLoader::~MechLoader() {
    std::lock_guard<std::mutex> lock(loaderMutex_);
    for (const auto& [handle, asset] : loadedMechs_) releaseMechAssetResources(*asset);
    loadedMechs_.clear();
}

MechHandle MechLoader::allocateHandle() {
    return allocateMechAssetHandle();
}

MechHandle MechLoader::loadMech(const std::string& name, LODQuality quality) {
    auto asset = std::make_shared<MechAsset>();
    PackageWriter reader;
    if (!reader.readPackage("assets/mechs/" + name + ".mechpack", *asset)) return 0;

    filterMechAssetLODs(*asset, quality);

    std::lock_guard<std::mutex> lock(loaderMutex_);
    asset->handle = allocateHandle();
    loadedMechs_[asset->handle] = asset;
    return asset->handle;
}

bool MechLoader::unloadMech(MechHandle handle) {
    std::shared_ptr<MechAsset> asset;
    {
        std::lock_guard<std::mutex> lock(loaderMutex_);
        auto it = loadedMechs_.find(handle);
        if (it == loadedMechs_.end()) return false;
        asset = it->second;
        loadedMechs_.erase(it);
    }
    releaseMechAssetResources(*asset);
    return true;
}

std::shared_ptr<const MechAsset> MechLoader::getMech(MechHandle handle) {
    std::lock_guard<std::mutex> lock(loaderMutex_);
    auto it = loadedMechs_.find(handle);
    return it == loadedMechs_.end() ? nullptr : it->second;
}

} // namespace MechAssets
} // namespace MagiTech
