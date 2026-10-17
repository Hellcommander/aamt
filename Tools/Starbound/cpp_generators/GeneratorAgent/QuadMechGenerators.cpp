#include "QuadMechFactory.hpp"
#include "QuadMechYaml.hpp"
#include "core/Log.hpp"
#include <nlohmann/json.hpp>
#include <glm/glm.hpp>
#include <glm/gtc/matrix_transform.hpp>
#include <glm/gtc/quaternion.hpp>
#include <atomic>
#include <cctype>
#include <fstream>
#include <filesystem>
#include <algorithm>
#include <optional>
#include <random>
#include <stdexcept>

namespace MagiTech {
namespace QuadMechGen {

using namespace ::MagiTech::QuadMech;

#define LOG_QUAD_MECH(Action, Id) Log::info("QuadMechGen", "{}: {}", #Action, Id)

namespace {

constexpr const char* kLogCategory = "QuadMechGen";
using ojson = nlohmann::ordered_json;

// ----------------------------------------------------------------------------
// Enum <-> string helpers (shared by the parser and the serializer)
// ----------------------------------------------------------------------------

std::string toLower(std::string s) {
    std::transform(s.begin(), s.end(), s.begin(), [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
    return s;
}

struct ModuleTypeName { ModuleType type; const char* name; };
constexpr ModuleTypeName kModuleTypeNames[] = {
    {ModuleType::CHASSIS, "chassis"},
    {ModuleType::LEG_FRONT_LEFT, "leg_front_left"},
    {ModuleType::LEG_FRONT_RIGHT, "leg_front_right"},
    {ModuleType::LEG_BACK_LEFT, "leg_back_left"},
    {ModuleType::LEG_BACK_RIGHT, "leg_back_right"},
    {ModuleType::HEAD, "head"},
    {ModuleType::COCKPIT, "cockpit"},
    {ModuleType::WEAPON_LEFT, "weapon_left"},
    {ModuleType::WEAPON_RIGHT, "weapon_right"},
    {ModuleType::ENERGY_CORE, "energy_core"},
};

struct AnimationTypeName { AnimationType type; const char* name; };
constexpr AnimationTypeName kAnimationTypeNames[] = {
    {AnimationType::WALK, "walk"},
    {AnimationType::TROT, "trot"},
    {AnimationType::GALLOP, "gallop"},
    {AnimationType::COCKPIT_OPEN, "cockpit_open"},
    {AnimationType::COCKPIT_CLOSE, "cockpit_close"},
    {AnimationType::PILOT_ENTRY, "pilot_entry"},
    {AnimationType::PILOT_EXIT, "pilot_exit"},
    {AnimationType::IDLE, "idle"},
    {AnimationType::ATTACK, "attack"},
    {AnimationType::DEFEND, "defend"},
};

struct LODQualityName { LODQuality quality; const char* name; };
constexpr LODQualityName kLODQualityNames[] = {
    {LODQuality::HIGH, "high"},
    {LODQuality::MEDIUM, "medium"},
    {LODQuality::LOW, "low"},
    {LODQuality::ULTRA_LOW, "ultra_low"},
};

std::optional<ModuleType> moduleTypeFromString(const std::string& s) {
    const std::string key = toLower(s);
    for (const auto& e : kModuleTypeNames) if (key == e.name) return e.type;
    return std::nullopt;
}

std::optional<AnimationType> animationTypeFromString(const std::string& s) {
    const std::string key = toLower(s);
    for (const auto& e : kAnimationTypeNames) if (key == e.name) return e.type;
    return std::nullopt;
}

std::optional<LODQuality> lodQualityFromString(const std::string& s) {
    const std::string key = toLower(s);
    for (const auto& e : kLODQualityNames) if (key == e.name) return e.quality;
    return std::nullopt;
}

const char* toString(ModuleType t) {
    for (const auto& e : kModuleTypeNames) if (e.type == t) return e.name;
    return "chassis";
}

const char* toString(AnimationType t) {
    for (const auto& e : kAnimationTypeNames) if (e.type == t) return e.name;
    return "idle";
}

const char* toString(LODQuality q) {
    for (const auto& e : kLODQualityNames) if (e.quality == q) return e.name;
    return "high";
}

// ----------------------------------------------------------------------------
// Typed field readers. Missing (or null) keys keep the struct default; a key
// with the wrong type is an error, as it was with yaml-cpp's as<T>().
// ----------------------------------------------------------------------------

[[noreturn]] void fieldError(const std::string& path, const char* expected) {
    throw std::runtime_error("QuadMech definition: '" + path + "' must be " + expected);
}

const ojson* child(const ojson& node, const char* key) {
    if (!node.is_object()) return nullptr;
    auto it = node.find(key);
    if (it == node.end() || it->is_null()) return nullptr;
    return &*it;
}

void readFloat(const ojson& node, const char* key, float& out, const std::string& ctx) {
    if (const ojson* v = child(node, key)) {
        if (!v->is_number()) fieldError(ctx + "." + key, "a number");
        out = v->get<float>();
    }
}

void readInt(const ojson& node, const char* key, int& out, const std::string& ctx) {
    if (const ojson* v = child(node, key)) {
        if (!v->is_number()) fieldError(ctx + "." + key, "an integer");
        out = v->is_number_integer() ? v->get<int>() : static_cast<int>(v->get<double>());
    }
}

void readBool(const ojson& node, const char* key, bool& out, const std::string& ctx) {
    if (const ojson* v = child(node, key)) {
        if (!v->is_boolean()) fieldError(ctx + "." + key, "true or false");
        out = v->get<bool>();
    }
}

std::string scalarToString(const ojson& v, const std::string& path) {
    if (v.is_string()) return v.get<std::string>();
    if (v.is_number() || v.is_boolean()) return v.dump(); // YAML scalars convert to strings
    fieldError(path, "a scalar");
}

void readString(const ojson& node, const char* key, std::string& out, const std::string& ctx) {
    if (const ojson* v = child(node, key)) out = scalarToString(*v, ctx + "." + key);
}

template<int N>
void parseVec(const ojson& v, glm::vec<N, float, glm::defaultp>& out, const std::string& path) {
    if (!v.is_array() || v.size() < static_cast<size_t>(N)) {
        fieldError(path, N == 2 ? "a list of 2 numbers" : N == 3 ? "a list of 3 numbers" : "a list of 4 numbers");
    }
    for (int i = 0; i < N; ++i) {
        const ojson& c = v[static_cast<size_t>(i)];
        if (!c.is_number()) fieldError(path, "a list of numbers");
        out[i] = c.get<float>();
    }
}

template<int N>
void readVec(const ojson& node, const char* key, glm::vec<N, float, glm::defaultp>& out, const std::string& ctx) {
    if (const ojson* v = child(node, key)) parseVec<N>(*v, out, ctx + "." + key);
}

// Reads a [min, max] pair given either as a list or as {min: , max: }.
void readRange(const ojson& node, const char* key, glm::vec2& out, const std::string& ctx) {
    const ojson* v = child(node, key);
    if (!v) return;
    if (v->is_object()) {
        readFloat(*v, "min", out.x, ctx + "." + key);
        readFloat(*v, "max", out.y, ctx + "." + key);
    } else {
        readVec<2>(node, key, out, ctx);
    }
}

// Reads the RGBA canopy tint; an RGB list keeps the current alpha.
void readTint(const ojson& node, const char* key, glm::vec4& out, const std::string& ctx) {
    const ojson* v = child(node, key);
    if (!v) return;
    if (v->is_array() && v->size() == 3) {
        glm::vec3 rgb(out);
        readVec<3>(node, key, rgb, ctx);
        out = glm::vec4(rgb, out.a);
    } else {
        readVec<4>(node, key, out, ctx);
    }
}

ModuleDefinition parseModule(const std::string& id, const ojson& m) {
    const std::string ctx = "modules." + id;
    if (!m.is_object()) fieldError(ctx, "a mapping");

    ModuleDefinition module;
    module.id = id;
    if (const ojson* t = child(m, "type")) {
        const std::string typeStr = scalarToString(*t, ctx + ".type");
        auto type = moduleTypeFromString(typeStr);
        if (!type) throw std::runtime_error("QuadMech definition: unknown module type '" + typeStr + "' in " + ctx);
        module.type = *type;
    } else if (auto type = moduleTypeFromString(id)) {
        module.type = *type; // standard module ids double as their type
    } else {
        Log::warn(kLogCategory, "Module '{}' has no type and a non-standard id; assuming chassis", id);
    }

    readString(m, "mesh", module.meshPath, ctx);
    readString(m, "attachBone", module.attachBone, ctx);
    readVec<3>(m, "offset", module.offset, ctx);
    readVec<3>(m, "scale", module.scale, ctx);
    readVec<3>(m, "rotation", module.rotation, ctx);
    readFloat(m, "mass", module.mass, ctx);
    readVec<3>(m, "inertia", module.inertia, ctx);
    readString(m, "materialOverride", module.materialOverride, ctx);
    return module;
}

ojson vecToJson(const glm::vec2& v) { return ojson::array({v.x, v.y}); }
ojson vecToJson(const glm::vec3& v) { return ojson::array({v.x, v.y, v.z}); }
ojson vecToJson(const glm::vec4& v) { return ojson::array({v.x, v.y, v.z, v.w}); }

} // namespace

// ============================================================================
// DEFINITION PARSER
// ============================================================================

namespace DefinitionParser {

QuadMechDefinition parseFromYAML(const std::string& yamlContent) {
    LOG_QUAD_MECH(ParsingDefinition, "YAML");

    const ojson node = parseQuadMechYaml(yamlContent);
    if (!node.is_object()) {
        throw std::runtime_error("QuadMech definition: document root must be a mapping");
    }
    QuadMechDefinition def;

    // Parse basic info
    const ojson* name = child(node, "name");
    if (!name) throw std::runtime_error("QuadMech definition: missing required key 'name'");
    def.name = scalarToString(*name, "name");
    readString(node, "version", def.version, "");
    readString(node, "author", def.author, "");
    readString(node, "description", def.description, "");

    // Parse modules: either a mapping of id -> module, or a list of modules with an "id" key
    if (const ojson* modules = child(node, "modules")) {
        if (modules->is_object()) {
            for (auto it = modules->begin(); it != modules->end(); ++it) {
                def.modules.push_back(parseModule(it.key(), it.value()));
            }
        } else if (modules->is_array()) {
            for (size_t i = 0; i < modules->size(); ++i) {
                const ojson& m = (*modules)[i];
                const ojson* id = child(m, "id");
                if (!id) throw std::runtime_error("QuadMech definition: modules[" + std::to_string(i) + "] needs an 'id'");
                def.modules.push_back(parseModule(scalarToString(*id, "modules.id"), m));
            }
        } else {
            fieldError("modules", "a mapping or a list");
        }
    }

    // Parse cockpit
    if (const ojson* cockpit = child(node, "cockpit")) {
        readVec<3>(*cockpit, "seatPosition", def.cockpit.seatPosition, "cockpit");
        readTint(*cockpit, "canopyTint", def.cockpit.canopyTint, "cockpit");
        readString(*cockpit, "canopyMaterial", def.cockpit.canopyMaterial, "cockpit");
        readFloat(*cockpit, "transparency", def.cockpit.transparency, "cockpit");
        readBool(*cockpit, "enableHologram", def.cockpit.enableHologram, "cockpit");
        if (const ojson* anchors = child(*cockpit, "hudAnchorPoints")) {
            if (!anchors->is_array()) fieldError("cockpit.hudAnchorPoints", "a list");
            for (size_t i = 0; i < anchors->size(); ++i) {
                glm::vec3 p(0.0f);
                parseVec<3>((*anchors)[i], p, "cockpit.hudAnchorPoints[" + std::to_string(i) + "]");
                def.cockpit.hudAnchorPoints.push_back(p);
            }
        }
    }

    // Parse Magitech materials
    if (const ojson* mat = child(node, "magitechMaterials")) {
        auto& runes = def.magitechMaterials.energyRunes;
        if (const ojson* r = child(*mat, "energyRunes")) {
            const std::string ctx = "magitechMaterials.energyRunes";
            readVec<3>(*r, "emissiveColor", runes.emissiveColor, ctx);
            readRange(*r, "glowIntensity", runes.glowIntensity, ctx);
            readFloat(*r, "animationRate", runes.animationRate, ctx);
            readFloat(*r, "pulseFrequency", runes.pulseFrequency, ctx);
            readBool(*r, "enableFlicker", runes.enableFlicker, ctx);
            readFloat(*r, "flickerIntensity", runes.flickerIntensity, ctx);
        }

        auto& core = def.magitechMaterials.energyCore;
        if (const ojson* c = child(*mat, "energyCore")) {
            const std::string ctx = "magitechMaterials.energyCore";
            readVec<3>(*c, "coreColor", core.coreColor, ctx);
            readFloat(*c, "energyLevel", core.energyLevel, ctx);
            readFloat(*c, "pulseRate", core.pulseRate, ctx);
            readBool(*c, "enableArcs", core.enableArcs, ctx);
            readFloat(*c, "arcIntensity", core.arcIntensity, ctx);
            readInt(*c, "arcCount", core.arcCount, ctx);
        }

        auto& canopy = def.magitechMaterials.canopy;
        if (const ojson* c = child(*mat, "canopy")) {
            const std::string ctx = "magitechMaterials.canopy";
            readTint(*c, "tint", canopy.tint, ctx);
            readFloat(*c, "transparency", canopy.transparency, ctx);
            readFloat(*c, "reflectivity", canopy.reflectivity, ctx);
            readBool(*c, "enableScratches", canopy.enableScratches, ctx);
            readFloat(*c, "scratchDensity", canopy.scratchDensity, ctx);
        }
    }

    // Parse animations
    if (const ojson* anims = child(node, "animations")) {
        if (!anims->is_array()) fieldError("animations", "a list");
        for (size_t i = 0; i < anims->size(); ++i) {
            const ojson& a = (*anims)[i];
            const std::string ctx = "animations[" + std::to_string(i) + "]";
            if (!a.is_object()) fieldError(ctx, "a mapping");
            AnimationDefinition anim;
            readString(a, "id", anim.id, ctx);
            readString(a, "path", anim.path, ctx);
            readFloat(a, "speed", anim.speed, ctx);
            readBool(a, "loop", anim.loop, ctx);
            readFloat(a, "blendTime", anim.blendTime, ctx);
            readFloat(a, "gaitPhase", anim.gaitPhase, ctx);
            readFloat(a, "strideLength", anim.strideLength, ctx);
            readFloat(a, "legLift", anim.legLift, ctx);

            std::string typeStr = anim.id;
            readString(a, "type", typeStr, ctx);
            if (auto type = animationTypeFromString(typeStr)) {
                anim.type = *type;
            } else {
                Log::warn(kLogCategory, "Animation '{}' has unknown type '{}'; using idle", anim.id, typeStr);
            }

            def.animations.push_back(anim);
        }
    }

    // Parse physics
    if (const ojson* physics = child(node, "physics")) {
        readFloat(*physics, "totalMass", def.physics.totalMass, "physics");
        readBool(*physics, "enableCCD", def.physics.enableCCD, "physics");
        readFloat(*physics, "collisionMargin", def.physics.collisionMargin, "physics");

        if (const ojson* masses = child(*physics, "moduleMass")) {
            if (!masses->is_object()) fieldError("physics.moduleMass", "a mapping");
            for (auto it = masses->begin(); it != masses->end(); ++it) {
                if (!it.value().is_number()) fieldError("physics.moduleMass." + it.key(), "a number");
                def.physics.moduleMass[it.key()] = it.value().get<float>();
            }
        }

        if (const ojson* joints = child(*physics, "jointLimits")) {
            if (!joints->is_object()) fieldError("physics.jointLimits", "a mapping");
            for (auto it = joints->begin(); it != joints->end(); ++it) {
                const std::string ctx = "physics.jointLimits." + it.key();
                JointLimit limit;
                readVec<2>(it.value(), "swing", limit.swing, ctx);
                readVec<2>(it.value(), "twist", limit.twist, ctx);
                readFloat(it.value(), "damping", limit.damping, ctx);
                readFloat(it.value(), "friction", limit.friction, ctx);
                def.physics.jointLimits[it.key()] = limit;
            }
        }
    }

    // Parse LODs
    if (const ojson* lods = child(node, "lods")) {
        if (!lods->is_array()) fieldError("lods", "a list");
        for (size_t i = 0; i < lods->size(); ++i) {
            const ojson& l = (*lods)[i];
            const std::string ctx = "lods[" + std::to_string(i) + "]";
            LODDefinition lod;
            std::string qualityStr = "high";
            readString(l, "quality", qualityStr, ctx);
            if (auto quality = lodQualityFromString(qualityStr)) {
                lod.quality = *quality;
            } else {
                throw std::runtime_error("QuadMech definition: unknown LOD quality '" + qualityStr + "' in " + ctx);
            }

            readFloat(l, "meshDecimate", lod.meshDecimate, ctx);
            readFloat(l, "materialDetail", lod.materialDetail, ctx);
            readInt(l, "maxBones", lod.maxBones, ctx);
            readBool(l, "enableMorphTargets", lod.enableMorphTargets, ctx);

            def.lods.push_back(lod);
        }
    }

    // Tags
    if (const ojson* tags = child(node, "tags")) {
        if (!tags->is_array()) fieldError("tags", "a list");
        for (size_t i = 0; i < tags->size(); ++i) {
            def.tags.push_back(scalarToString((*tags)[i], "tags[" + std::to_string(i) + "]"));
        }
    }

    return def;
}

std::string serializeDefinition(const QuadMechDefinition& def) {
    ojson root = ojson::object();
    root["name"] = def.name;
    root["version"] = def.version;
    root["author"] = def.author;
    root["description"] = def.description;

    ojson modules = ojson::object();
    for (const auto& m : def.modules) {
        ojson j = ojson::object();
        j["type"] = toString(m.type);
        j["mesh"] = m.meshPath;
        j["attachBone"] = m.attachBone;
        j["offset"] = vecToJson(m.offset);
        j["scale"] = vecToJson(m.scale);
        j["rotation"] = vecToJson(m.rotation);
        j["mass"] = m.mass;
        j["inertia"] = vecToJson(m.inertia);
        if (!m.materialOverride.empty()) j["materialOverride"] = m.materialOverride;
        modules[m.id] = std::move(j);
    }
    root["modules"] = std::move(modules);

    ojson cockpit = ojson::object();
    cockpit["seatPosition"] = vecToJson(def.cockpit.seatPosition);
    cockpit["canopyTint"] = vecToJson(def.cockpit.canopyTint);
    cockpit["canopyMaterial"] = def.cockpit.canopyMaterial;
    cockpit["transparency"] = def.cockpit.transparency;
    cockpit["enableHologram"] = def.cockpit.enableHologram;
    ojson anchors = ojson::array();
    for (const auto& p : def.cockpit.hudAnchorPoints) anchors.push_back(vecToJson(p));
    cockpit["hudAnchorPoints"] = std::move(anchors);
    root["cockpit"] = std::move(cockpit);

    const auto& runes = def.magitechMaterials.energyRunes;
    const auto& core = def.magitechMaterials.energyCore;
    const auto& canopy = def.magitechMaterials.canopy;
    root["magitechMaterials"] = {
        {"energyRunes", {
            {"emissiveColor", vecToJson(runes.emissiveColor)},
            {"glowIntensity", {{"min", runes.glowIntensity.x}, {"max", runes.glowIntensity.y}}},
            {"animationRate", runes.animationRate},
            {"pulseFrequency", runes.pulseFrequency},
            {"enableFlicker", runes.enableFlicker},
            {"flickerIntensity", runes.flickerIntensity}}},
        {"energyCore", {
            {"coreColor", vecToJson(core.coreColor)},
            {"energyLevel", core.energyLevel},
            {"pulseRate", core.pulseRate},
            {"enableArcs", core.enableArcs},
            {"arcIntensity", core.arcIntensity},
            {"arcCount", core.arcCount}}},
        {"canopy", {
            {"tint", vecToJson(canopy.tint)},
            {"transparency", canopy.transparency},
            {"reflectivity", canopy.reflectivity},
            {"enableScratches", canopy.enableScratches},
            {"scratchDensity", canopy.scratchDensity}}}
    };

    ojson anims = ojson::array();
    for (const auto& a : def.animations) {
        anims.push_back({
            {"id", a.id}, {"type", toString(a.type)}, {"path", a.path},
            {"speed", a.speed}, {"loop", a.loop}, {"blendTime", a.blendTime},
            {"gaitPhase", a.gaitPhase}, {"strideLength", a.strideLength}, {"legLift", a.legLift}});
    }
    root["animations"] = std::move(anims);

    ojson physics = ojson::object();
    physics["totalMass"] = def.physics.totalMass;
    ojson masses = ojson::object();
    for (const auto& k : sortedKeys(def.physics.moduleMass)) masses[k] = def.physics.moduleMass.at(k);
    physics["moduleMass"] = std::move(masses);
    ojson joints = ojson::object();
    for (const auto& k : sortedKeys(def.physics.jointLimits)) {
        const JointLimit& l = def.physics.jointLimits.at(k);
        joints[k] = {{"swing", vecToJson(l.swing)}, {"twist", vecToJson(l.twist)},
                     {"damping", l.damping}, {"friction", l.friction}};
    }
    physics["jointLimits"] = std::move(joints);
    physics["enableCCD"] = def.physics.enableCCD;
    physics["collisionMargin"] = def.physics.collisionMargin;
    root["physics"] = std::move(physics);

    ojson lods = ojson::array();
    for (const auto& l : def.lods) {
        lods.push_back({
            {"quality", toString(l.quality)}, {"meshDecimate", l.meshDecimate},
            {"materialDetail", l.materialDetail}, {"maxBones", l.maxBones},
            {"enableMorphTargets", l.enableMorphTargets}});
    }
    root["lods"] = std::move(lods);
    root["tags"] = def.tags;

    return root.dump(2);
}

bool validateDefinition(const QuadMechDefinition& def) {
    LOG_QUAD_MECH(ValidatingDefinition, def.name);

    // Check basic requirements
    if (def.name.empty()) {
        Log::error("QuadMech definition must have a name");
        return false;
    }

    if (def.modules.empty()) {
        Log::error("QuadMech definition must have at least one module");
        return false;
    }

    // Check for required modules
    bool hasChassis = false;
    bool hasLegs = false;

    for (const auto& module : def.modules) {
        if (module.id == "chassis") hasChassis = true;
        if (module.id.find("leg") != std::string::npos) hasLegs = true;

        if (module.meshPath.empty()) {
            Log::error(kLogCategory, "Module {} must have a mesh path", module.id);
            return false;
        }

        if (module.attachBone.empty()) {
            Log::error(kLogCategory, "Module {} must have an attach bone", module.id);
            return false;
        }
    }

    if (!hasChassis) {
        Log::error("QuadMech must have a chassis module");
        return false;
    }

    if (!hasLegs) {
        Log::error("QuadMech must have leg modules");
        return false;
    }

    // Validate physics
    if (def.physics.totalMass <= 0) {
        Log::error("Total mass must be positive");
        return false;
    }

    // Validate animations
    for (const auto& anim : def.animations) {
        if (anim.path.empty()) {
            Log::error(kLogCategory, "Animation {} must have a path", anim.id);
            return false;
        }
    }

    Log::info(kLogCategory, "QuadMech definition validation passed for: {}", def.name);
    return true;
}

} // namespace DefinitionParser

// ============================================================================
// MODULE ASSEMBLER
// ============================================================================

namespace ModuleAssembler {

std::vector<ModuleEntry> assembleModules(const QuadMechDefinition& def, LODQuality quality) {
    LOG_QUAD_MECH(AssemblingModules, def.name);
    
    std::vector<ModuleEntry> modules;
    
    for (const auto& moduleDef : def.modules) {
        ModuleEntry entry;
        
        // Load mesh for all LOD levels
        for (int i = 0; i < 4; ++i) {
            LODQuality lodQuality = static_cast<LODQuality>(i);
            
            // In real implementation, this would load the actual mesh
            // For now, we create placeholder handles
            static std::atomic<uint32_t> nextMeshHandle{1000};
            entry.lodMeshes[i] = nextMeshHandle++;
            
            // Load material for this LOD
            static std::atomic<uint32_t> nextMaterialHandle{2000};
            entry.lodMaterials[i] = nextMaterialHandle++;
        }
        
        // Create physics body
        static std::atomic<uint32_t> nextPhysicsHandle{3000};
        entry.physicsBody = nextPhysicsHandle++;
        
        // Calculate transform from module definition
        glm::mat4 transform = glm::mat4(1.0f);
        transform = glm::translate(transform, moduleDef.offset);
        transform = glm::scale(transform, moduleDef.scale);
        transform = glm::rotate(transform, glm::radians(moduleDef.rotation.x), glm::vec3(1, 0, 0));
        transform = glm::rotate(transform, glm::radians(moduleDef.rotation.y), glm::vec3(0, 1, 0));
        transform = glm::rotate(transform, glm::radians(moduleDef.rotation.z), glm::vec3(0, 0, 1));
        
        entry.transform = transform;
        
        modules.push_back(entry);
    }
    
    return modules;
}

SkeletonHandle buildSkeleton(const QuadMechDefinition& def) {
    LOG_QUAD_MECH(BuildingSkeleton, def.name);
    
    // Create quadraped skeleton
    // Root -> Spine -> Neck -> Head
    // Root -> Spine -> Hip_FL -> Thigh_FL -> Shin_FL -> Foot_FL
    // Root -> Spine -> Hip_FR -> Thigh_FR -> Shin_FR -> Foot_FR
    // Root -> Spine -> Hip_BL -> Thigh_BL -> Shin_BL -> Foot_BL
    // Root -> Spine -> Hip_BR -> Thigh_BR -> Shin_BR -> Foot_BR
    
    static std::atomic<uint32_t> nextSkeletonHandle{4000};
    SkeletonHandle skeleton = nextSkeletonHandle++;
    
    // In real implementation, this would create the actual bone hierarchy
    // For now, we return a placeholder handle
    
    return skeleton;
}

} // namespace ModuleAssembler

// ============================================================================
// MATERIAL SYNTHESIZER
// ============================================================================

namespace MaterialSynthesizer {

MaterialHandle createEnergyRunesMaterial(const EnergyRunes& runes) {
    LOG_QUAD_MECH(CreatingEnergyRunesMaterial, runes.hashKey());
    
    // Create procedural material for energy runes
    // This would generate a shader with:
    // - Emissive color with pulsing intensity
    // - Noise-based flicker effect
    // - Animated glow patterns
    
    static std::atomic<uint32_t> nextMaterialHandle{5000};
    MaterialHandle material = nextMaterialHandle++;
    
    return material;
}

MaterialHandle createEnergyCoreMaterial(const EnergyCore& core) {
    LOG_QUAD_MECH(CreatingEnergyCoreMaterial, core.hashKey());
    
    // Create procedural material for energy core
    // This would generate a shader with:
    // - Pulsing core color
    // - Energy arc effects
    // - Dynamic intensity based on energy level
    
    static std::atomic<uint32_t> nextMaterialHandle{6000};
    MaterialHandle material = nextMaterialHandle++;
    
    return material;
}

MaterialHandle createCanopyMaterial(const CanopyMaterial& canopy) {
    LOG_QUAD_MECH(CreatingCanopyMaterial, canopy.hashKey());
    
    // Create procedural material for cockpit canopy
    // This would generate a shader with:
    // - Transparency with tint
    // - Reflectivity
    // - Optional scratch effects
    
    static std::atomic<uint32_t> nextMaterialHandle{7000};
    MaterialHandle material = nextMaterialHandle++;
    
    return material;
}

std::vector<MaterialHandle> generateLODMaterials(const MagitechMaterials& materials, LODQuality quality) {
    LOG_QUAD_MECH(GeneratingLODMaterials, static_cast<int>(quality));
    
    std::vector<MaterialHandle> lodMaterials;
    
    // Generate LOD versions of all Magitech materials
    for (int i = 0; i < 4; ++i) {
        LODQuality lodQuality = static_cast<LODQuality>(i);
        
        // Create simplified versions for lower LODs
        static std::atomic<uint32_t> nextLODMaterialHandle{8000};
        MaterialHandle lodMaterial = nextLODMaterialHandle++;
        
        lodMaterials.push_back(lodMaterial);
    }
    
    return lodMaterials;
}

} // namespace MaterialSynthesizer

// ============================================================================
// ANIMATION PROCESSOR
// ============================================================================

namespace AnimationProcessor {

AnimationHandle retargetAnimation(const std::string& path, const SkeletonHandle& skeleton, AnimationType type) {
    LOG_QUAD_MECH(RetargetingAnimation, path);
    
    // Retarget animation to the quadraped skeleton
    // This would:
    // - Load the animation from file
    // - Map bone names to the target skeleton
    // - Adjust timing for quadraped locomotion
    // - Apply gait-specific modifications
    
    static std::atomic<uint32_t> nextAnimationHandle{9000};
    AnimationHandle animation = nextAnimationHandle++;
    
    return animation;
}

std::unordered_map<std::string, AnimationHandle> processAllAnimations(const QuadMechDefinition& def, const SkeletonHandle& skeleton) {
    LOG_QUAD_MECH(ProcessingAllAnimations, def.name);
    
    std::unordered_map<std::string, AnimationHandle> animations;
    
    for (const auto& animDef : def.animations) {
        AnimationHandle anim = retargetAnimation(animDef.path, skeleton, animDef.type);
        animations[animDef.id] = anim;
    }
    
    return animations;
}

} // namespace AnimationProcessor

// ============================================================================
// PHYSICS RIG BUILDER
// ============================================================================

namespace PhysicsRigBuilder {

PhysicsBodyHandle createModulePhysics(const ModuleDefinition& module, float mass) {
    LOG_QUAD_MECH(CreatingModulePhysics, module.id);
    
    // Create physics body for module
    // This would:
    // - Generate collision shape based on mesh
    // - Set mass and inertia
    // - Configure physics properties
    
    static std::atomic<uint32_t> nextPhysicsHandle{10000};
    PhysicsBodyHandle body = nextPhysicsHandle++;
    
    return body;
}

std::vector<PhysicsBodyHandle> buildPhysicsRig(const QuadMechDefinition& def) {
    LOG_QUAD_MECH(BuildingPhysicsRig, def.name);
    
    std::vector<PhysicsBodyHandle> bodies;
    
    for (const auto& module : def.modules) {
        float mass = def.physics.moduleMass.count(module.id) ? 
                    def.physics.moduleMass.at(module.id) : module.mass;
        
        PhysicsBodyHandle body = createModulePhysics(module, mass);
        bodies.push_back(body);
    }
    
    return bodies;
}

void setupJointConstraints(const QuadMechDefinition& def, std::vector<PhysicsBodyHandle>& bodies) {
    LOG_QUAD_MECH(SettingUpJointConstraints, def.name);
    
    // Setup joint constraints between physics bodies
    // This would:
    // - Create joints between connected modules
    // - Apply joint limits from definition
    // - Configure damping and friction
    
    for (const auto& jointLimit : def.physics.jointLimits) {
        // Apply joint limits
        // In real implementation, this would create actual physics joints
    }
}

} // namespace PhysicsRigBuilder

// ============================================================================
// LOD GENERATOR
// ============================================================================

namespace LODGenerator {

MeshHandle generateLODMesh(const MeshHandle& original, LODQuality quality, float decimateFactor) {
    LOG_QUAD_MECH(GeneratingLODMesh, static_cast<int>(quality));
    
    // Generate LOD mesh by decimating the original
    // This would:
    // - Reduce vertex count based on decimateFactor
    // - Preserve important features
    // - Optimize for rendering performance
    
    static std::atomic<uint32_t> nextLODMeshHandle{11000};
    MeshHandle lodMesh = nextLODMeshHandle++;
    
    return lodMesh;
}

MaterialHandle generateLODMaterial(const MaterialHandle& original, LODQuality quality, float detailFactor) {
    LOG_QUAD_MECH(GeneratingLODMaterial, static_cast<int>(quality));
    
    // Generate LOD material by simplifying the original
    // This would:
    // - Reduce texture resolution
    // - Simplify shader complexity
    // - Remove expensive effects for lower LODs
    
    static std::atomic<uint32_t> nextLODMaterialHandle{12000};
    MaterialHandle lodMaterial = nextLODMaterialHandle++;
    
    return lodMaterial;
}

std::array<MeshHandle, 4> generateAllLODs(const MeshHandle& original, const std::vector<LODDefinition>& lods) {
    LOG_QUAD_MECH(GeneratingAllLODs, original);
    
    std::array<MeshHandle, 4> lodMeshes = {0, 0, 0, 0};
    
    for (const auto& lod : lods) {
        MeshHandle lodMesh = generateLODMesh(original, lod.quality, lod.meshDecimate);
        lodMeshes[static_cast<int>(lod.quality)] = lodMesh;
    }
    
    return lodMeshes;
}

} // namespace LODGenerator

// ============================================================================
// PACKAGE WRITER
// ============================================================================

namespace PackageWriter {

namespace {

bool writeBinary(const std::filesystem::path& path, const void* data, size_t size) {
    std::filesystem::create_directories(path.parent_path());
    std::ofstream out(path, std::ios::binary | std::ios::trunc);
    if (!out.is_open()) {
        Log::error(kLogCategory, "Failed to write package file: {}", path.string());
        return false;
    }
    out.write(static_cast<const char*>(data), static_cast<std::streamsize>(size));
    return static_cast<bool>(out);
}

template<typename T>
bool writeValue(const std::filesystem::path& path, const T& value) {
    static_assert(std::is_trivially_copyable_v<T>);
    return writeBinary(path, &value, sizeof(T));
}

// Mesh payload: the module's mesh handle for this LOD followed by its transform.
struct MeshRecord {
    MeshHandle mesh = 0;
    glm::mat4 transform = glm::mat4(1.0f);
};

} // namespace

bool writeMechPackage(const QuadMechAsset& asset, const std::string& outputPath) {
    LOG_QUAD_MECH(WritingMechPackage, outputPath);

    // Package layout (see createPackageStructure):
    //   metadata.json, definition.yaml, skeleton/, meshes/<lod>/, materials/<lod>/,
    //   animations/, physics/
    std::error_code ec;
    std::filesystem::create_directories(outputPath, ec);
    if (ec) {
        Log::error(kLogCategory, "Cannot create package directory {}: {}", outputPath, ec.message());
        return false;
    }
    const MechPackage layout = createPackageStructure(asset.definition.name, outputPath);
    bool ok = true;

    // Write metadata
    {
        ojson metadata = ojson::object();
        metadata["name"] = asset.definition.name;
        metadata["version"] = asset.definition.version;
        metadata["hashKey"] = asset.hashKey();
        ojson moduleIds = ojson::array();
        for (const auto& m : asset.definition.modules) moduleIds.push_back(m.id);
        metadata["modules"] = std::move(moduleIds);
        ojson animIds = ojson::array();
        for (const auto& [id, handle] : asset.animations) animIds.push_back(id);
        metadata["animations"] = std::move(animIds);

        std::ofstream metadataFile(layout.metadataPath, std::ios::trunc);
        if (metadataFile.is_open()) {
            metadataFile << metadata.dump(2) << "\n";
        } else {
            Log::error(kLogCategory, "Failed to write metadata: {}", layout.metadataPath);
            ok = false;
        }
    }

    // Write the source definition so the package can be regenerated / reloaded
    {
        std::ofstream definitionFile(layout.definitionPath, std::ios::trunc);
        if (definitionFile.is_open()) {
            definitionFile << DefinitionParser::serializeDefinition(asset.definition) << "\n";
        } else {
            Log::error(kLogCategory, "Failed to write definition: {}", layout.definitionPath);
            ok = false;
        }
    }

    // Write LOD-specific data
    for (const auto& [moduleId, module] : asset.modules) {
        for (int i = 0; i < 4; ++i) {
            const LODQuality quality = static_cast<LODQuality>(i);

            MeshRecord record;
            record.mesh = module.lodMeshes[i];
            record.transform = module.transform;
            ok &= writeValue(layout.meshPaths.at(quality) + moduleId + ".bin", record);
            ok &= writeValue(layout.materialPaths.at(quality) + moduleId + ".mat", module.lodMaterials[i]);
        }
    }

    // Write skeleton
    ok &= writeValue(layout.skeletonPath, asset.skeleton);

    // Write animations
    for (const auto& [animId, handle] : asset.animations) {
        ok &= writeValue(std::filesystem::path(outputPath) / "animations" / (animId + ".anim"), handle);
    }

    // Write physics data
    ok &= writeValue(layout.physicsPath, asset.rootBody);

    if (ok) {
        Log::info(kLogCategory, "Mech package written successfully to: {}", outputPath);
    }
    return ok;
}

MechPackage createPackageStructure(const std::string& mechName, const std::string& outputDir) {
    LOG_QUAD_MECH(CreatingPackageStructure, mechName);

    MechPackage package;
    package.name = mechName;
    package.version = "1.0.0";
    package.definitionPath = outputDir + "/definition.yaml";
    package.skeletonPath = outputDir + "/skeleton/skeleton.bin";
    package.physicsPath = outputDir + "/physics/rig.bin";
    package.metadataPath = outputDir + "/metadata.json";

    // Setup LOD paths
    for (int i = 0; i < 4; ++i) {
        const LODQuality quality = static_cast<LODQuality>(i);
        const std::string qualityStr = toString(quality);

        package.meshPaths[quality] = outputDir + "/meshes/" + qualityStr + "/";
        package.materialPaths[quality] = outputDir + "/materials/" + qualityStr + "/";
    }

    return package;
}

} // namespace PackageWriter

// ============================================================================
// PACKAGE READER
// ============================================================================

namespace PackageReader {

namespace {

ojson readJsonFile(const std::string& path) {
    std::ifstream in(path);
    if (!in.is_open()) return ojson();
    ojson j = ojson::parse(in, nullptr, false);
    return j.is_discarded() ? ojson() : j;
}

} // namespace

QuadMechAsset readMechPackage(const std::string& packagePath) {
    LOG_QUAD_MECH(ReadingMechPackage, packagePath);

    QuadMechAsset asset;
    const MechPackage package = readPackageMetadata(packagePath);
    std::error_code ec;

    // Restore the definition the package was generated from
    if (std::filesystem::exists(package.definitionPath, ec)) {
        std::ifstream definitionFile(package.definitionPath, std::ios::binary);
        std::string content((std::istreambuf_iterator<char>(definitionFile)), std::istreambuf_iterator<char>());
        try {
            asset.definition = DefinitionParser::parseFromYAML(content);
        } catch (const std::exception& e) {
            Log::warn(kLogCategory, "Package {} has an unreadable definition: {}", packagePath, e.what());
        }
    }
    if (asset.definition.name.empty()) asset.definition.name = package.name;
    if (!package.version.empty()) asset.definition.version = package.version;

    // Read skeleton
    static std::atomic<uint32_t> nextSkeletonHandle{13000};
    asset.skeleton = nextSkeletonHandle++;

    // Read modules for all LODs
    static std::atomic<uint32_t> nextMeshHandle{14000};
    static std::atomic<uint32_t> nextMaterialHandle{15000};
    for (int i = 0; i < 4; ++i) {
        const LODQuality quality = static_cast<LODQuality>(i);
        const std::string& meshDir = package.meshPaths.at(quality);
        if (!std::filesystem::is_directory(meshDir, ec)) continue;

        // Read all module files in this LOD directory
        for (const auto& entry : std::filesystem::directory_iterator(meshDir, ec)) {
            if (entry.is_regular_file() && entry.path().extension() == ".bin") {
                const std::string moduleId = entry.path().stem().string();
                ModuleEntry& moduleEntry = asset.modules[moduleId]; // accumulate all LODs per module

                moduleEntry.lodMeshes[i] = nextMeshHandle++;
                moduleEntry.lodMaterials[i] = nextMaterialHandle++;

                // Restore the module transform stored after the mesh handle
                std::ifstream meshFile(entry.path(), std::ios::binary);
                MeshHandle storedMesh = 0;
                glm::mat4 transform(1.0f);
                if (meshFile.read(reinterpret_cast<char*>(&storedMesh), sizeof(storedMesh)) &&
                    meshFile.read(reinterpret_cast<char*>(&transform), sizeof(transform))) {
                    moduleEntry.transform = transform;
                }
            }
        }
    }

    // Read animations
    const std::string animDir = packagePath + "/animations/";
    static std::atomic<uint32_t> nextAnimationHandle{16000};
    if (std::filesystem::is_directory(animDir, ec)) {
        for (const auto& entry : std::filesystem::directory_iterator(animDir, ec)) {
            if (entry.is_regular_file() && entry.path().extension() == ".anim") {
                asset.animations[entry.path().stem().string()] = nextAnimationHandle++;
            }
        }
    }

    // Read physics data
    static std::atomic<uint32_t> nextPhysicsHandle{17000};
    if (std::filesystem::exists(package.physicsPath, ec)) {
        asset.rootBody = nextPhysicsHandle++;
    }

    // Create Magitech materials
    asset.energyRunesMaterial = MaterialSynthesizer::createEnergyRunesMaterial(asset.definition.magitechMaterials.energyRunes);
    asset.energyCoreMaterial = MaterialSynthesizer::createEnergyCoreMaterial(asset.definition.magitechMaterials.energyCore);
    asset.canopyMaterial = MaterialSynthesizer::createCanopyMaterial(asset.definition.magitechMaterials.canopy);

    return asset;
}

MechPackage readPackageMetadata(const std::string& packagePath) {
    LOG_QUAD_MECH(ReadingPackageMetadata, packagePath);

    // Default layout, derived from the package directory name
    std::string mechName = std::filesystem::path(packagePath).stem().string();
    MechPackage package = PackageWriter::createPackageStructure(mechName, packagePath);
    package.version.clear();

    // Read metadata from JSON
    const ojson metadata = readJsonFile(package.metadataPath);
    if (metadata.is_object()) {
        if (auto it = metadata.find("name"); it != metadata.end() && it->is_string()) package.name = it->get<std::string>();
        if (auto it = metadata.find("version"); it != metadata.end() && it->is_string()) package.version = it->get<std::string>();
    } else {
        Log::warn(kLogCategory, "Package {} has no readable metadata.json", packagePath);
    }

    // Animation files present in the package
    std::error_code ec;
    const std::string animDir = packagePath + "/animations/";
    if (std::filesystem::is_directory(animDir, ec)) {
        for (const auto& entry : std::filesystem::directory_iterator(animDir, ec)) {
            if (entry.is_regular_file() && entry.path().extension() == ".anim") {
                package.animationPaths[entry.path().stem().string()] = entry.path().string();
            }
        }
    }

    return package;
}

} // namespace PackageReader

} // namespace QuadMechGen
} // namespace MagiTech 
