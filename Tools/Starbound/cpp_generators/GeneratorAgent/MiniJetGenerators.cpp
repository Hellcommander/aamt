#include "MiniJetFactory.hpp"
#include "core/Log.hpp"
#include <glm/gtc/quaternion.hpp>
#include <algorithm>
#include <array>
#include <cctype>
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <limits>
#include <map>
#include <sstream>
#include <unordered_set>

namespace MiniJetGen {

using MagiTech::Log;
using Json = nlohmann::json;

// =============================================================================================
// Shared helpers (declared before use)
// =============================================================================================
namespace {

// ---- enum <-> string tables (definition JSON) -----------------------------------------------

constexpr std::array<const char*, 10> kModuleTypeNames = {
    "fuselage", "wing_left", "wing_right", "tailplane", "thruster_main",
    "thruster_aux", "cockpit", "weapon_left", "weapon_right", "energy_core"};
constexpr std::array<const char*, 5> kControlSurfaceNames = {"aileron", "elevator", "rudder", "flap", "spoiler"};
constexpr std::array<const char*, 9> kAnimationTypeNames = {
    "takeoff", "hover", "forward_flight", "banking", "landing",
    "cockpit_open", "cockpit_close", "weapon_deploy", "weapon_retract"};
constexpr std::array<const char*, 4> kQualityNames = {"ultra", "high", "medium", "low"};
constexpr std::array<const char*, 3> kCollisionShapeNames = {"box", "capsule", "convex_hull"};

std::string toLower(std::string s) {
    std::transform(s.begin(), s.end(), s.begin(), [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
    return s;
}

template <typename E, size_t N>
bool enumFromName(const std::string& name, const std::array<const char*, N>& names, E& out) {
    const std::string lower = toLower(name);
    for (size_t i = 0; i < N; ++i) {
        if (lower == names[i]) {
            out = static_cast<E>(i);
            return true;
        }
    }
    return false;
}

template <typename E, size_t N>
const char* enumName(E value, const std::array<const char*, N>& names) {
    const size_t i = static_cast<size_t>(value);
    return i < N ? names[i] : names[0];
}

// Infers a module's type from its id when the definition does not state it ("left_wing" -> Wing_Left)
ModuleType inferModuleType(const std::string& id) {
    const std::string s = toLower(id);
    const bool left = s.find("left") != std::string::npos;
    if (s.find("cockpit") != std::string::npos) return ModuleType::Cockpit;
    if (s.find("wing") != std::string::npos) return left ? ModuleType::Wing_Left : ModuleType::Wing_Right;
    if (s.find("tail") != std::string::npos) return ModuleType::Tailplane;
    if (s.find("thruster") != std::string::npos || s.find("engine") != std::string::npos)
        return s.find("aux") != std::string::npos ? ModuleType::Thruster_Aux : ModuleType::Thruster_Main;
    if (s.find("weapon") != std::string::npos || s.find("gun") != std::string::npos)
        return left ? ModuleType::Weapon_Left : ModuleType::Weapon_Right;
    if (s.find("core") != std::string::npos) return ModuleType::Energy_Core;
    return ModuleType::Fuselage;
}

glm::vec3 readVec3(const Json& node) {
    return {node.at(0).get<float>(), node.at(1).get<float>(), node.at(2).get<float>()};
}

Json vec3Json(const glm::vec3& v) { return Json::array({v.x, v.y, v.z}); }

template <typename T>
void readOptional(const Json& node, const char* key, T& out) {
    if (node.contains(key)) out = node.at(key).get<T>();
}

void readOptionalVec3(const Json& node, const char* key, glm::vec3& out) {
    if (node.contains(key)) out = readVec3(node.at(key));
}

std::string getQualityName(Quality quality) {
    switch (quality) {
        case Quality::Ultra: return "ultra";
        case Quality::High: return "high";
        case Quality::Medium: return "medium";
        case Quality::Low: return "low";
        default: return "high";
    }
}

// ---- mesh ---------------------------------------------------------------------------------

void computeNormals(MeshHandle& mesh) {
    mesh.normals.assign(mesh.positions.size(), glm::vec3(0.0f));
    for (size_t i = 0; i + 2 < mesh.indices.size(); i += 3) {
        const uint32_t a = mesh.indices[i], b = mesh.indices[i + 1], c = mesh.indices[i + 2];
        const glm::vec3 n = glm::cross(mesh.positions[b] - mesh.positions[a], mesh.positions[c] - mesh.positions[a]);
        mesh.normals[a] += n;
        mesh.normals[b] += n;
        mesh.normals[c] += n;
    }
    for (auto& n : mesh.normals) {
        const float len = glm::length(n);
        n = len > 1e-12f ? n / len : glm::vec3(0.0f, 1.0f, 0.0f);
    }
}

std::pair<glm::vec3, glm::vec3> bounds(const std::vector<glm::vec3>& points) {
    glm::vec3 mn(std::numeric_limits<float>::max()), mx(-std::numeric_limits<float>::max());
    for (const auto& p : points) {
        mn = glm::min(mn, p);
        mx = glm::max(mx, p);
    }
    if (points.empty()) mn = mx = glm::vec3(0.0f);
    return {mn, mx};
}

// Wavefront OBJ loader: v / vt / vn / f (any polygon, fan-triangulated, negative indices allowed)
MeshHandle loadMeshFromFile(const std::string& path) {
    MeshHandle mesh;
    std::ifstream file(path);
    if (!file.is_open()) return mesh;
    mesh.name = std::filesystem::path(path).stem().string();

    std::vector<glm::vec3> positions, normals;
    std::vector<glm::vec2> uvs;
    std::map<std::tuple<int, int, int>, uint32_t> vertexIds;
    bool fileHasNormals = false;

    auto resolve = [](int idx, size_t count) { return idx < 0 ? static_cast<int>(count) + idx : idx - 1; };
    std::string line;
    while (std::getline(file, line)) {
        std::istringstream ls(line);
        std::string tag;
        ls >> tag;
        if (tag == "v") {
            glm::vec3 p(0.0f);
            ls >> p.x >> p.y >> p.z;
            positions.push_back(p);
        } else if (tag == "vt") {
            glm::vec2 t(0.0f);
            ls >> t.x >> t.y;
            uvs.push_back(t);
        } else if (tag == "vn") {
            glm::vec3 n(0.0f);
            ls >> n.x >> n.y >> n.z;
            normals.push_back(n);
        } else if (tag == "f") {
            std::vector<uint32_t> face;
            std::string token;
            while (ls >> token) {
                int vi = 0, ti = 0, ni = 0;
                const size_t s1 = token.find('/');
                vi = std::stoi(token.substr(0, s1));
                if (s1 != std::string::npos) {
                    const size_t s2 = token.find('/', s1 + 1);
                    const std::string t = token.substr(s1 + 1, s2 == std::string::npos ? std::string::npos : s2 - s1 - 1);
                    if (!t.empty()) ti = std::stoi(t);
                    if (s2 != std::string::npos && s2 + 1 < token.size()) ni = std::stoi(token.substr(s2 + 1));
                }
                const int p = resolve(vi, positions.size());
                const int t = ti ? resolve(ti, uvs.size()) : -1;
                const int n = ni ? resolve(ni, normals.size()) : -1;
                if (p < 0 || p >= static_cast<int>(positions.size())) continue;
                auto key = std::make_tuple(p, t, n);
                auto it = vertexIds.find(key);
                if (it == vertexIds.end()) {
                    const uint32_t id = static_cast<uint32_t>(mesh.positions.size());
                    mesh.positions.push_back(positions[p]);
                    mesh.uvs.push_back(t >= 0 && t < static_cast<int>(uvs.size()) ? uvs[t] : glm::vec2(0.0f));
                    mesh.normals.push_back(n >= 0 && n < static_cast<int>(normals.size()) ? normals[n] : glm::vec3(0.0f));
                    if (n >= 0) fileHasNormals = true;
                    it = vertexIds.emplace(key, id).first;
                }
                face.push_back(it->second);
            }
            for (size_t i = 1; i + 1 < face.size(); ++i) {
                mesh.indices.push_back(face[0]);
                mesh.indices.push_back(face[i]);
                mesh.indices.push_back(face[i + 1]);
            }
        }
    }
    if (!fileHasNormals) computeNormals(mesh);
    return mesh;
}

MeshHandle applyTransform(const MeshHandle& mesh, const glm::vec3& offset, const glm::vec3& scale, const glm::quat& rotation) {
    MeshHandle out = mesh;
    const glm::vec3 safeScale = glm::max(glm::abs(scale), glm::vec3(1e-6f)) * glm::sign(scale + glm::vec3(1e-12f));
    for (auto& p : out.positions) p = rotation * (p * scale) + offset;
    for (auto& n : out.normals) {
        const glm::vec3 t = rotation * (n / safeScale);   // inverse-transpose for non-uniform scale
        const float len = glm::length(t);
        n = len > 1e-12f ? t / len : n;
    }
    return out;
}

MaterialHandle createMaterial(const std::string& name) {
    MaterialHandle material;
    material.name = name;
    material.shader = "MagitechStandard";
    return material;
}

MaterialHandle createMaterial() { return createMaterial("Material"); }

void setMaterialProperty(MaterialHandle& material, const std::string& name, const glm::vec3& value) {
    material.vec3Params[name] = value;
}

void setMaterialProperty(MaterialHandle& material, const std::string& name, float value) {
    material.floatParams[name] = value;
}

void setMaterialShader(MaterialHandle& material, const std::string& shaderName) {
    material.shader = shaderName;
}

MaterialHandle createDefaultMaterial() {
    MaterialHandle material = createMaterial("Default");
    setMaterialProperty(material, "baseColor", glm::vec3(0.62f, 0.64f, 0.68f));
    setMaterialProperty(material, "metallic", 0.85f);
    setMaterialProperty(material, "roughness", 0.35f);
    return material;
}

// One bone per distinct attach bone, parented to "root", placed at the first attaching module's offset
Skeleton buildSkeletonFromModules(const std::vector<ModuleDefinition>& modules) {
    Skeleton skeleton;
    skeleton.bones.push_back(Bone{"root", -1, glm::vec3(0.0f)});
    for (const auto& module : modules) {
        if (module.attachBone.empty() || skeleton.findBone(module.attachBone) >= 0) continue;
        skeleton.bones.push_back(Bone{module.attachBone, 0, module.offset});
    }
    // Bones named after a module hang off that module's attach bone
    for (auto& bone : skeleton.bones) {
        for (const auto& module : modules) {
            if (bone.name == module.id && module.attachBone != bone.name) {
                const int parent = skeleton.findBone(module.attachBone);
                if (parent >= 0) bone.parent = parent;
            }
        }
    }
    return skeleton;
}

bool areModulesAdjacent(const ModuleDefinition& m1, const ModuleDefinition& m2) {
    return m1.attachBone == m2.id || m2.attachBone == m1.id ||
           (!m1.attachBone.empty() && m1.attachBone == m2.attachBone);
}

// Parent/child connection only (one joint per pair)
bool areModulesConnected(const ModuleDefinition& m1, const ModuleDefinition& m2) {
    return !m1.attachBone.empty() && m1.attachBone == m2.id;
}

// Snaps coincident boundary vertices of two meshes together so the seam has no cracks
void weldMeshesAtSeam(MeshHandle& mesh1, MeshHandle& mesh2, const std::string& bone1, const std::string& bone2) {
    if (!mesh1.isValid() || !mesh2.isValid()) return;
    auto [mn1, mx1] = bounds(mesh1.positions);
    auto [mn2, mx2] = bounds(mesh2.positions);
    const float diag = glm::length(glm::max(mx1, mx2) - glm::min(mn1, mn2));
    const float tolerance = std::max(1e-4f, diag * 0.005f);

    std::unordered_map<int64_t, std::vector<uint32_t>> grid;
    auto cellOf = [tolerance](const glm::vec3& p) {
        const glm::ivec3 c(glm::floor(p / tolerance));
        return glm::ivec3(c);
    };
    auto key = [](const glm::ivec3& c) {
        return (static_cast<int64_t>(c.x) * 73856093) ^ (static_cast<int64_t>(c.y) * 19349663) ^ (static_cast<int64_t>(c.z) * 83492791);
    };
    for (uint32_t i = 0; i < mesh1.positions.size(); ++i) grid[key(cellOf(mesh1.positions[i]))].push_back(i);

    size_t welded = 0;
    for (uint32_t j = 0; j < mesh2.positions.size(); ++j) {
        const glm::ivec3 c = cellOf(mesh2.positions[j]);
        for (int dz = -1; dz <= 1; ++dz)
            for (int dy = -1; dy <= 1; ++dy)
                for (int dx = -1; dx <= 1; ++dx) {
                    auto it = grid.find(key(c + glm::ivec3(dx, dy, dz)));
                    if (it == grid.end()) continue;
                    for (uint32_t i : it->second) {
                        if (glm::length(mesh1.positions[i] - mesh2.positions[j]) > tolerance) continue;
                        const glm::vec3 mid = 0.5f * (mesh1.positions[i] + mesh2.positions[j]);
                        mesh1.positions[i] = mesh2.positions[j] = mid;
                        if (i < mesh1.normals.size() && j < mesh2.normals.size()) {
                            const glm::vec3 n = mesh1.normals[i] + mesh2.normals[j];
                            if (glm::length(n) > 1e-9f) mesh1.normals[i] = mesh2.normals[j] = glm::normalize(n);
                        }
                        ++welded;
                    }
                }
    }
    if (welded) {
        Log::debug("MiniJet", "Welded {} seam vertices ({} <-> {})", welded, bone1, bone2);
    }
}

// Distance-based skinning: up to 4 nearest bones, inverse-square weights, attach bone favoured
void bakeSkinWeightsForMesh(MeshHandle& mesh, const Skeleton& skeleton, const std::string& attachBone) {
    mesh.boneIndices.assign(mesh.positions.size(), glm::uvec4(0));
    mesh.boneWeights.assign(mesh.positions.size(), glm::vec4(0.0f));
    if (skeleton.bones.empty()) return;
    const int attach = skeleton.findBone(attachBone);
    for (size_t v = 0; v < mesh.positions.size(); ++v) {
        std::vector<std::pair<float, uint32_t>> scored;
        for (uint32_t b = 0; b < skeleton.bones.size(); ++b) {
            const float d = glm::length(mesh.positions[v] - skeleton.bones[b].position);
            float w = 1.0f / (d * d + 1e-4f);
            if (static_cast<int>(b) == attach) w *= 4.0f;
            scored.emplace_back(w, b);
        }
        std::sort(scored.begin(), scored.end(), [](const auto& a, const auto& b) { return a.first > b.first; });
        float total = 0.0f;
        const size_t n = std::min<size_t>(4, scored.size());
        for (size_t k = 0; k < n; ++k) total += scored[k].first;
        for (size_t k = 0; k < n; ++k) {
            mesh.boneIndices[v][static_cast<int>(k)] = scored[k].second;
            mesh.boneWeights[v][static_cast<int>(k)] = scored[k].first / total;
        }
    }
}

MeshHandle createMesh() { return MeshHandle{}; }

// Vertex clustering on a uniform grid; `factor` in (0,1) is the fraction of vertices removed
void decimateMeshGeometry(const MeshHandle& source, MeshHandle& target, float factor) {
    target = MeshHandle{};
    target.name = source.name;
    if (!source.isValid()) return;
    factor = std::clamp(factor, 0.0f, 0.99f);
    auto [mn, mx] = bounds(source.positions);
    const glm::vec3 extent = glm::max(mx - mn, glm::vec3(1e-6f));
    const float targetVerts = std::max(8.0f, static_cast<float>(source.positions.size()) * (1.0f - factor));
    const float cell = std::cbrt(std::max(extent.x * extent.y * extent.z, 1e-12f) / targetVerts);
    const glm::ivec3 dims = glm::max(glm::ivec3(glm::ceil(extent / std::max(cell, 1e-6f))), glm::ivec3(1));

    std::unordered_map<int64_t, uint32_t> cellIds;
    std::vector<float> counts;
    std::vector<uint32_t> remap(source.positions.size());
    const bool hasUv = source.uvs.size() == source.positions.size();
    const bool hasNormals = source.normals.size() == source.positions.size();
    const bool hasSkin = source.boneWeights.size() == source.positions.size();
    for (size_t i = 0; i < source.positions.size(); ++i) {
        const glm::ivec3 c = glm::clamp(glm::ivec3((source.positions[i] - mn) / extent * glm::vec3(dims)), glm::ivec3(0), dims - 1);
        const int64_t k = (static_cast<int64_t>(c.x) * dims.y + c.y) * dims.z + c.z;
        auto it = cellIds.find(k);
        if (it == cellIds.end()) {
            it = cellIds.emplace(k, static_cast<uint32_t>(target.positions.size())).first;
            target.positions.push_back(glm::vec3(0.0f));
            target.normals.push_back(glm::vec3(0.0f));
            target.uvs.push_back(glm::vec2(0.0f));
            if (hasSkin) {
                target.boneIndices.push_back(source.boneIndices[i]);
                target.boneWeights.push_back(source.boneWeights[i]);
            }
            counts.push_back(0.0f);
        }
        const uint32_t id = it->second;
        target.positions[id] += source.positions[i];
        if (hasNormals) target.normals[id] += source.normals[i];
        if (hasUv) target.uvs[id] += source.uvs[i];
        counts[id] += 1.0f;
        remap[i] = id;
    }
    for (size_t i = 0; i < target.positions.size(); ++i) {
        target.positions[i] /= counts[i];
        target.uvs[i] /= counts[i];
        const float len = glm::length(target.normals[i]);
        target.normals[i] = len > 1e-9f ? target.normals[i] / len : glm::vec3(0.0f, 1.0f, 0.0f);
    }
    for (size_t i = 0; i + 2 < source.indices.size(); i += 3) {
        const uint32_t a = remap[source.indices[i]], b = remap[source.indices[i + 1]], c = remap[source.indices[i + 2]];
        if (a == b || b == c || a == c) continue;
        target.indices.insert(target.indices.end(), {a, b, c});
    }
    if (!hasNormals) computeNormals(target);
}

void copyMaterialProperties(const MaterialHandle& source, MaterialHandle& target) {
    target.name = source.name;
    target.shader = source.shader;
    target.floatParams = source.floatParams;
    target.vec3Params = source.vec3Params;
    target.textureResolutionScale = source.textureResolutionScale;
    target.shaderComplexity = source.shaderComplexity;
}

void reduceTextureResolution(MaterialHandle& material, float factor) {
    material.textureResolutionScale = std::clamp(material.textureResolutionScale * factor, 1.0f / 64.0f, 1.0f);
}

// Lower detail levels drop the most expensive effects
void simplifyShader(MaterialHandle& material, float factor) {
    material.shaderComplexity = std::clamp(static_cast<int>(std::lround(3.0f * factor)), 0, 3);
    if (material.shaderComplexity < 2) {
        material.floatParams.erase("distortionIntensity");
        material.floatParams.erase("patternScale");
    }
    if (material.shaderComplexity < 1) {
        material.floatParams.erase("pulseRate");
        material.floatParams.erase("flickerRate");
    }
    material.floatParams["shaderComplexity"] = static_cast<float>(material.shaderComplexity);
}

// ---- shader graphs (JSON node graphs consumed by the material compiler) --------------------

std::string makeShaderGraph(const std::string& name, const Json& parameters, const Json& nodes, const Json& links) {
    Json graph;
    graph["name"] = name;
    graph["parameters"] = parameters;
    graph["nodes"] = nodes;
    graph["links"] = links;
    return graph.dump(2);
}

std::string generateRuneGlowShaderGraph(const MagitechMaterials::RuneGlow& p) {
    return makeShaderGraph("MagitechRuneGlow",
        {{"emissiveColor", vec3Json(p.emissiveColor)}, {"pulseRate", p.pulseRate},
         {"patternScale", p.patternScale}, {"glowIntensity", p.glowIntensity}},
        Json::array({{{"id", "time"}, {"type", "Time"}},
                     {{"id", "pulse"}, {"type", "Sine"}, {"frequency", "pulseRate"}},
                     {{"id", "runes"}, {"type", "RunePattern"}, {"scale", "patternScale"}},
                     {{"id", "glow"}, {"type", "Multiply"}, {"inputs", {"runes", "pulse", "emissiveColor", "glowIntensity"}}},
                     {{"id", "output"}, {"type", "Output"}, {"slot", "emission"}}}),
        Json::array({{"time", "pulse"}, {"pulse", "glow"}, {"runes", "glow"}, {"glow", "output"}}));
}

std::string generateEngineHeatShaderGraph(const MagitechMaterials::EngineHeat& p) {
    return makeShaderGraph("MagitechEngineHeat",
        {{"distortionIntensity", p.distortionIntensity}, {"flickerRate", p.flickerRate},
         {"heatColor", vec3Json(p.heatColor)}, {"maxTemperature", p.maxTemperature}},
        Json::array({{{"id", "time"}, {"type", "Time"}},
                     {{"id", "noise"}, {"type", "ScrollingNoise"}, {"speed", "flickerRate"}},
                     {{"id", "distort"}, {"type", "ScreenDistortion"}, {"strength", "distortionIntensity"}},
                     {{"id", "blackbody"}, {"type", "Blackbody"}, {"temperature", "maxTemperature"}, {"tint", "heatColor"}},
                     {{"id", "output"}, {"type", "Output"}, {"slot", "emission+refraction"}}}),
        Json::array({{"time", "noise"}, {"noise", "distort"}, {"distort", "output"}, {"blackbody", "output"}}));
}

std::string generateEnergyTrailShaderGraph(const MagitechMaterials::EnergyTrail& p) {
    return makeShaderGraph("MagitechEnergyTrail",
        {{"trailColor", vec3Json(p.trailColor)}, {"trailLength", p.trailLength},
         {"trailWidth", p.trailWidth}, {"fadeRate", p.fadeRate}},
        Json::array({{{"id", "uv"}, {"type", "TexCoord"}},
                     {{"id", "fade"}, {"type", "Power"}, {"base", "fadeRate"}, {"exponent", "uv.x*trailLength"}},
                     {{"id", "edge"}, {"type", "SmoothStep"}, {"width", "trailWidth"}},
                     {{"id", "color"}, {"type", "Multiply"}, {"inputs", {"trailColor", "fade", "edge"}}},
                     {{"id", "output"}, {"type", "Output"}, {"slot", "emission+alpha"}, {"blend", "additive"}}}),
        Json::array({{"uv", "fade"}, {"uv", "edge"}, {"fade", "color"}, {"edge", "color"}, {"color", "output"}}));
}

MaterialHandle createCanopyMaterial(float transparency) {
    MaterialHandle material = createMaterial("Canopy");
    setMaterialProperty(material, "transparency", std::clamp(transparency, 0.0f, 1.0f));
    setMaterialProperty(material, "tint", glm::vec3(0.55f, 0.8f, 1.0f));
    setMaterialProperty(material, "fresnelPower", 4.0f);
    setMaterialProperty(material, "roughness", 0.05f);
    setMaterialShader(material, "MagitechCanopyShield");
    return material;
}

std::string generateCanopyShaderGraph(float transparency) {
    return makeShaderGraph("MagitechCanopyShield",
        {{"transparency", transparency}, {"fresnelPower", 4.0f}},
        Json::array({{{"id", "fresnel"}, {"type", "Fresnel"}, {"power", "fresnelPower"}},
                     {{"id", "alpha"}, {"type", "Lerp"}, {"a", "1-transparency"}, {"b", 1.0}, {"t", "fresnel"}},
                     {{"id", "output"}, {"type", "Output"}, {"slot", "alpha"}, {"blend", "alpha"}}}),
        Json::array({{"fresnel", "alpha"}, {"alpha", "output"}}));
}

// ---- animation ----------------------------------------------------------------------------

// JSON clip: {"name", "duration", "skeleton":[{"name","parent","position"}],
//             "tracks":[{"bone","keys":[{"time","translation","rotation":[w,x,y,z],"scale"}]}]}
Animation loadAnimationFromFile(const std::string& path) {
    Animation anim;
    std::ifstream file(path);
    if (!file.is_open()) return anim;
    Json j = Json::parse(file, nullptr, false);
    if (j.is_discarded() || !j.is_object()) return anim;
    try {
        anim.name = j.value("name", std::filesystem::path(path).stem().string());
        anim.duration = j.value("duration", 0.0f);
        if (j.contains("skeleton")) {
            for (const auto& b : j.at("skeleton")) {
                Bone bone;
                bone.name = b.at("name").get<std::string>();
                bone.parent = b.value("parent", -1);
                if (b.contains("position")) bone.position = readVec3(b.at("position"));
                anim.skeleton.bones.push_back(bone);
            }
        }
        for (const auto& t : j.at("tracks")) {
            AnimationTrack track;
            track.boneName = t.at("bone").get<std::string>();
            for (const auto& k : t.at("keys")) {
                Keyframe key;
                key.time = k.at("time").get<float>();
                if (k.contains("translation")) key.translation = readVec3(k.at("translation"));
                if (k.contains("rotation")) {
                    const Json& r = k.at("rotation");
                    key.rotation = glm::normalize(glm::quat(r.at(0).get<float>(), r.at(1).get<float>(), r.at(2).get<float>(), r.at(3).get<float>()));
                }
                if (k.contains("scale")) key.scale = readVec3(k.at("scale"));
                track.keys.push_back(key);
                anim.duration = std::max(anim.duration, key.time);
            }
            std::sort(track.keys.begin(), track.keys.end(), [](const Keyframe& a, const Keyframe& b) { return a.time < b.time; });
            anim.tracks.push_back(std::move(track));
        }
    } catch (const Json::exception& e) {
        Log::error("MiniJet", "Invalid animation clip {}: {}", path, e.what());
        return Animation{};
    }
    return anim;
}

std::string stripBonePrefix(const std::string& name) {
    const size_t pos = name.find_last_of(":|");
    return toLower(pos == std::string::npos ? name : name.substr(pos + 1));
}

// Maps source bone names to target bones: exact, then case/prefix-insensitive, then by hierarchy order
std::unordered_map<std::string, std::string> createBoneMapping(const Skeleton& source, const Skeleton& target) {
    std::unordered_map<std::string, std::string> mapping;
    std::unordered_map<std::string, std::string> normalizedTarget;
    for (const auto& bone : target.bones) normalizedTarget.emplace(stripBonePrefix(bone.name), bone.name);
    for (size_t i = 0; i < source.bones.size(); ++i) {
        const std::string& name = source.bones[i].name;
        if (target.findBone(name) >= 0) {
            mapping[name] = name;
        } else if (auto it = normalizedTarget.find(stripBonePrefix(name)); it != normalizedTarget.end()) {
            mapping[name] = it->second;
        } else if (source.bones.size() == target.bones.size()) {
            mapping[name] = target.bones[i].name;
        }
    }
    return mapping;
}

// Keeps roughly `factor` of each track's keys (evenly spaced), always keeping the first and last
void reduceKeyframeDensity(Animation& anim, float factor) {
    factor = std::clamp(factor, 0.0f, 1.0f);
    for (auto& track : anim.tracks) {
        const size_t n = track.keys.size();
        if (n <= 2) continue;
        const size_t keep = std::max<size_t>(2, static_cast<size_t>(std::ceil(static_cast<float>(n) * factor)));
        if (keep >= n) continue;
        std::vector<Keyframe> reduced;
        reduced.reserve(keep);
        for (size_t k = 0; k < keep; ++k) {
            const size_t idx = static_cast<size_t>(std::lround(static_cast<double>(k) * (n - 1) / (keep - 1)));
            if (reduced.empty() || reduced.back().time != track.keys[idx].time) reduced.push_back(track.keys[idx]);
        }
        track.keys = std::move(reduced);
    }
}

// Removes keys that linear interpolation of their neighbours reproduces within tolerance
void simplifyCurves(Animation& anim) {
    constexpr float posTol = 1e-3f, scaleTol = 1e-3f, angleTol = 0.5f * 3.14159265f / 180.0f;
    for (auto& track : anim.tracks) {
        if (track.keys.size() <= 2) continue;
        std::vector<Keyframe> out{track.keys.front()};
        for (size_t i = 1; i + 1 < track.keys.size(); ++i) {
            const Keyframe& a = out.back();
            const Keyframe& b = track.keys[i];
            const Keyframe& c = track.keys[i + 1];
            const float span = c.time - a.time;
            const float t = span > 0.0f ? (b.time - a.time) / span : 0.0f;
            const glm::vec3 pos = glm::mix(a.translation, c.translation, t);
            const glm::vec3 scl = glm::mix(a.scale, c.scale, t);
            const glm::quat rot = glm::slerp(a.rotation, c.rotation, t);
            const float angle = 2.0f * std::acos(std::clamp(std::abs(glm::dot(rot, b.rotation)), 0.0f, 1.0f));
            const bool redundant = glm::length(pos - b.translation) < posTol && glm::length(scl - b.scale) < scaleTol && angle < angleTol;
            if (!redundant) out.push_back(b);
        }
        out.push_back(track.keys.back());
        track.keys = std::move(out);
    }
}

// Drops empty tracks, tracks for bones the skeleton does not have, and constant identity tracks
void removeUnusedTracks(Animation& anim) {
    auto isIdentity = [](const Keyframe& k) {
        return glm::length(k.translation) < 1e-5f && glm::length(k.scale - glm::vec3(1.0f)) < 1e-5f &&
               std::abs(std::abs(k.rotation.w) - 1.0f) < 1e-5f;
    };
    anim.tracks.erase(std::remove_if(anim.tracks.begin(), anim.tracks.end(), [&](const AnimationTrack& track) {
        if (track.keys.empty()) return true;
        if (!anim.skeleton.bones.empty() && anim.skeleton.findBone(track.boneName) < 0) return true;
        return std::all_of(track.keys.begin(), track.keys.end(), isIdentity);
    }), anim.tracks.end());
}

// ---- physics ------------------------------------------------------------------------------

PhysicsBody createPhysicsBody() { return PhysicsBody{}; }

void setBoxCollider(PhysicsBody& body, const glm::vec3& size) {
    body.shape = PhysicsBody::Shape::Box;
    body.halfExtents = glm::abs(size) * 0.5f;
}

void setCapsuleCollider(PhysicsBody& body, float radius, float height) {
    body.shape = PhysicsBody::Shape::Capsule;
    body.radius = std::max(radius, 0.0f);
    body.height = std::max(height, 0.0f);
}

// Hull points: extreme vertices of the module mesh along 26 directions (a k-DOP approximation)
void setConvexHullCollider(PhysicsBody& body, const std::string& meshPath) {
    const MeshHandle mesh = loadMeshFromFile(meshPath);
    body.shape = PhysicsBody::Shape::ConvexHull;
    body.hullPoints.clear();
    if (!mesh.isValid()) {
        Log::warn("MiniJet", "Convex hull source mesh missing: {}", meshPath);
        return;
    }
    std::unordered_set<size_t> chosen;
    for (int x = -1; x <= 1; ++x)
        for (int y = -1; y <= 1; ++y)
            for (int z = -1; z <= 1; ++z) {
                if (!x && !y && !z) continue;
                const glm::vec3 dir(static_cast<float>(x), static_cast<float>(y), static_cast<float>(z));
                size_t best = 0;
                float bestDot = -std::numeric_limits<float>::max();
                for (size_t i = 0; i < mesh.positions.size(); ++i) {
                    const float d = glm::dot(mesh.positions[i], dir);
                    if (d > bestDot) { bestDot = d; best = i; }
                }
                if (chosen.insert(best).second) body.hullPoints.push_back(mesh.positions[best]);
            }
}

float getModuleMass(ModuleType type) {
    switch (type) {
        case ModuleType::Fuselage: return 320.0f;
        case ModuleType::Wing_Left:
        case ModuleType::Wing_Right: return 90.0f;
        case ModuleType::Tailplane: return 45.0f;
        case ModuleType::Thruster_Main: return 140.0f;
        case ModuleType::Thruster_Aux: return 40.0f;
        case ModuleType::Cockpit: return 110.0f;
        case ModuleType::Weapon_Left:
        case ModuleType::Weapon_Right: return 35.0f;
        case ModuleType::Energy_Core: return 60.0f;
        default: return 100.0f;
    }
}

void setBodyMass(PhysicsBody& body, float mass) { body.mass = std::max(mass, 0.0f); }

ThrusterNode createThrusterNode() { return ThrusterNode{}; }
void setThrusterForce(ThrusterNode& thruster, float force) { thruster.force = std::max(force, 0.0f); }
void setThrusterDirection(ThrusterNode& thruster, const glm::vec3& direction) {
    const float len = glm::length(direction);
    thruster.direction = len > 1e-9f ? direction / len : glm::vec3(0.0f, 0.0f, -1.0f);
}
void setThrusterHeat(ThrusterNode& thruster, float heat) { thruster.heatDistortion = std::max(heat, 0.0f); }

// ---- binary serialization -----------------------------------------------------------------

constexpr uint32_t kMeshMagic = 0x4853454D;      // "MESH"
constexpr uint32_t kMaterialMagic = 0x4C54414D;  // "MATL"
constexpr uint32_t kAnimMagic = 0x4D494E41;      // "ANIM"
constexpr uint32_t kPhysicsMagic = 0x53594850;   // "PHYS"
constexpr uint32_t kSkeletonMagic = 0x4E4C4B53;  // "SKLN"

template <typename T>
void writePod(std::ostream& out, const T& v) { out.write(reinterpret_cast<const char*>(&v), sizeof(T)); }

template <typename T>
bool readPod(std::istream& in, T& v) { return static_cast<bool>(in.read(reinterpret_cast<char*>(&v), sizeof(T))); }

void writeString(std::ostream& out, const std::string& s) {
    writePod(out, static_cast<uint32_t>(s.size()));
    out.write(s.data(), static_cast<std::streamsize>(s.size()));
}

bool readString(std::istream& in, std::string& s) {
    uint32_t n = 0;
    if (!readPod(in, n) || n > (1u << 26)) return false;
    s.resize(n);
    return static_cast<bool>(in.read(s.data(), n));
}

template <typename T>
void writeVector(std::ostream& out, const std::vector<T>& v) {
    writePod(out, static_cast<uint64_t>(v.size()));
    if (!v.empty()) out.write(reinterpret_cast<const char*>(v.data()), static_cast<std::streamsize>(v.size() * sizeof(T)));
}

template <typename T>
bool readVector(std::istream& in, std::vector<T>& v) {
    uint64_t n = 0;
    if (!readPod(in, n) || n > (1ull << 32)) return false;
    v.resize(static_cast<size_t>(n));
    return n == 0 || static_cast<bool>(in.read(reinterpret_cast<char*>(v.data()), static_cast<std::streamsize>(n * sizeof(T))));
}

void serializeMesh(const MeshHandle& mesh, std::ostream& out) {
    writePod(out, kMeshMagic);
    writeString(out, mesh.name);
    writeVector(out, mesh.positions);
    writeVector(out, mesh.normals);
    writeVector(out, mesh.uvs);
    writeVector(out, mesh.indices);
    writeVector(out, mesh.boneIndices);
    writeVector(out, mesh.boneWeights);
}

MeshHandle deserializeMesh(std::istream& in) {
    MeshHandle mesh;
    uint32_t magic = 0;
    if (!readPod(in, magic) || magic != kMeshMagic) return MeshHandle{};
    if (!readString(in, mesh.name) || !readVector(in, mesh.positions) || !readVector(in, mesh.normals) ||
        !readVector(in, mesh.uvs) || !readVector(in, mesh.indices) || !readVector(in, mesh.boneIndices) ||
        !readVector(in, mesh.boneWeights)) {
        return MeshHandle{};
    }
    return mesh;
}

void serializeMaterial(const MaterialHandle& material, std::ostream& out) {
    writePod(out, kMaterialMagic);
    writeString(out, material.name);
    writeString(out, material.shader);
    writePod(out, material.textureResolutionScale);
    writePod(out, static_cast<int32_t>(material.shaderComplexity));
    writePod(out, static_cast<uint32_t>(material.floatParams.size()));
    for (const auto& [k, v] : material.floatParams) { writeString(out, k); writePod(out, v); }
    writePod(out, static_cast<uint32_t>(material.vec3Params.size()));
    for (const auto& [k, v] : material.vec3Params) { writeString(out, k); writePod(out, v); }
}

MaterialHandle deserializeMaterial(std::istream& in) {
    MaterialHandle material;
    uint32_t magic = 0, count = 0;
    int32_t complexity = 0;
    if (!readPod(in, magic) || magic != kMaterialMagic) return MaterialHandle{};
    if (!readString(in, material.name) || !readString(in, material.shader) ||
        !readPod(in, material.textureResolutionScale) || !readPod(in, complexity)) {
        return MaterialHandle{};
    }
    material.shaderComplexity = complexity;
    if (!readPod(in, count)) return MaterialHandle{};
    for (uint32_t i = 0; i < count; ++i) {
        std::string k;
        float v = 0.0f;
        if (!readString(in, k) || !readPod(in, v)) return MaterialHandle{};
        material.floatParams[k] = v;
    }
    if (!readPod(in, count)) return MaterialHandle{};
    for (uint32_t i = 0; i < count; ++i) {
        std::string k;
        glm::vec3 v(0.0f);
        if (!readString(in, k) || !readPod(in, v)) return MaterialHandle{};
        material.vec3Params[k] = v;
    }
    return material;
}

void serializeSkeleton(const Skeleton& skeleton, std::ostream& out) {
    writePod(out, kSkeletonMagic);
    writePod(out, static_cast<uint32_t>(skeleton.bones.size()));
    for (const auto& b : skeleton.bones) {
        writeString(out, b.name);
        writePod(out, static_cast<int32_t>(b.parent));
        writePod(out, b.position);
    }
}

bool deserializeSkeleton(std::istream& in, Skeleton& skeleton) {
    uint32_t magic = 0, count = 0;
    if (!readPod(in, magic) || magic != kSkeletonMagic || !readPod(in, count)) return false;
    skeleton.bones.clear();
    for (uint32_t i = 0; i < count; ++i) {
        Bone b;
        int32_t parent = -1;
        if (!readString(in, b.name) || !readPod(in, parent) || !readPod(in, b.position)) return false;
        b.parent = parent;
        skeleton.bones.push_back(b);
    }
    return true;
}

void serializeAnimation(const Animation& animation, std::ostream& out) {
    writePod(out, kAnimMagic);
    writeString(out, animation.name);
    writePod(out, animation.duration);
    serializeSkeleton(animation.skeleton, out);
    writePod(out, static_cast<uint32_t>(animation.tracks.size()));
    for (const auto& track : animation.tracks) {
        writeString(out, track.boneName);
        writeVector(out, track.keys);
    }
}

Animation deserializeAnimation(std::istream& in) {
    Animation animation;
    uint32_t magic = 0, count = 0;
    if (!readPod(in, magic) || magic != kAnimMagic) return Animation{};
    if (!readString(in, animation.name) || !readPod(in, animation.duration) ||
        !deserializeSkeleton(in, animation.skeleton) || !readPod(in, count)) {
        return Animation{};
    }
    for (uint32_t i = 0; i < count; ++i) {
        AnimationTrack track;
        if (!readString(in, track.boneName) || !readVector(in, track.keys)) return Animation{};
        animation.tracks.push_back(std::move(track));
    }
    return animation;
}

void serializeBody(const PhysicsBody& body, std::ostream& out) {
    writeString(out, body.name);
    writePod(out, static_cast<uint32_t>(body.shape));
    writePod(out, body.halfExtents);
    writePod(out, body.radius);
    writePod(out, body.height);
    writePod(out, body.mass);
    writeVector(out, body.hullPoints);
}

bool deserializeBody(std::istream& in, PhysicsBody& body) {
    uint32_t shape = 0;
    if (!readString(in, body.name) || !readPod(in, shape) || !readPod(in, body.halfExtents) ||
        !readPod(in, body.radius) || !readPod(in, body.height) || !readPod(in, body.mass) ||
        !readVector(in, body.hullPoints)) {
        return false;
    }
    body.shape = static_cast<PhysicsBody::Shape>(std::min(shape, 3u));
    return true;
}

void serializePhysics(const PhysicsRigBuilder::PhysicsResult& physics, std::ostream& out) {
    writePod(out, kPhysicsMagic);
    writePod(out, static_cast<uint32_t>(physics.bodies.size()));
    for (const auto& [id, body] : physics.bodies) {
        writeString(out, id);
        serializeBody(body, out);
    }
    writePod(out, static_cast<uint32_t>(physics.thrusters.size()));
    for (const auto& [id, t] : physics.thrusters) {
        writeString(out, id);
        writeString(out, t.name);
        writePod(out, t.force);
        writePod(out, t.direction);
        writePod(out, t.heatDistortion);
        writePod(out, t.position);
    }
    writePod(out, static_cast<uint32_t>(physics.joints.size()));
    for (const auto& [a, b] : physics.joints) {
        writeString(out, a);
        writeString(out, b);
    }
}

bool deserializePhysics(std::istream& in, PhysicsRigBuilder::PhysicsResult& physics) {
    uint32_t magic = 0, count = 0;
    if (!readPod(in, magic) || magic != kPhysicsMagic || !readPod(in, count)) return false;
    for (uint32_t i = 0; i < count; ++i) {
        std::string id;
        PhysicsBody body;
        if (!readString(in, id) || !deserializeBody(in, body)) return false;
        physics.bodies[id] = body;
    }
    if (!readPod(in, count)) return false;
    for (uint32_t i = 0; i < count; ++i) {
        std::string id;
        ThrusterNode t;
        if (!readString(in, id) || !readString(in, t.name) || !readPod(in, t.force) || !readPod(in, t.direction) ||
            !readPod(in, t.heatDistortion) || !readPod(in, t.position)) {
            return false;
        }
        physics.thrusters[id] = t;
    }
    if (!readPod(in, count)) return false;
    for (uint32_t i = 0; i < count; ++i) {
        std::string a, b;
        if (!readString(in, a) || !readString(in, b)) return false;
        physics.joints.emplace_back(a, b);
    }
    return true;
}

// Physics rig of a built asset (bodies / thrusters live on the modules)
PhysicsRigBuilder::PhysicsResult physicsFromAsset(const MiniJetAsset& asset) {
    PhysicsRigBuilder::PhysicsResult physics;
    physics.bodies = asset.physicsBodies;
    for (const auto& [id, module] : asset.modules) {
        if (module.physicsBody.isValid()) physics.bodies[id] = module.physicsBody;
        if (module.thruster.isValid()) physics.thrusters[id] = module.thruster;
    }
    for (const auto& m1 : asset.definition.modules)
        for (const auto& m2 : asset.definition.modules)
            if (m1.id != m2.id && areModulesConnected(m1, m2)) physics.joints.emplace_back(m1.id, m2.id);
    return physics;
}

} // namespace

// =============================================================================================
// DefinitionParser implementation
// Definitions are JSON documents (yaml-cpp is not vendored). The layout is the same as the
// former YAML format: "modules" and "physics.moduleMass" are objects keyed by name,
// "animations" and "lods" are arrays.
// =============================================================================================
namespace DefinitionParser {

MiniJetDefinition parseFromJson(const Json& root) {
    MiniJetDefinition def;

    // Parse basic info
    def.name = root.at("name").get<std::string>();
    def.version = root.at("version").get<std::string>();

    // Parse modules
    if (root.contains("modules")) {
        for (const auto& [moduleId, moduleData] : root.at("modules").items()) {
            ModuleDefinition module;
            module.id = moduleId;
            module.meshPath = moduleData.at("mesh").get<std::string>();
            module.attachBone = moduleData.at("attachBone").get<std::string>();
            if (!moduleData.contains("type") ||
                !enumFromName(moduleData.at("type").get<std::string>(), kModuleTypeNames, module.type)) {
                module.type = inferModuleType(moduleId);
            }

            readOptionalVec3(moduleData, "offset", module.offset);
            readOptionalVec3(moduleData, "scale", module.scale);
            if (moduleData.contains("rotation")) {
                const Json& r = moduleData.at("rotation");
                module.rotation = glm::normalize(glm::quat(r.at(0).get<float>(), r.at(1).get<float>(), r.at(2).get<float>(), r.at(3).get<float>()));
            }

            // Parse thruster-specific parameters
            readOptional(moduleData, "thrustForce", module.thrustForce);
            readOptionalVec3(moduleData, "thrustDirection", module.thrustDirection);
            readOptional(moduleData, "heatDistortion", module.heatDistortion);

            // Parse control surface parameters
            if (moduleData.contains("controlSurface")) {
                enumFromName(moduleData.at("controlSurface").get<std::string>(), kControlSurfaceNames, module.controlSurface);
            }
            readOptional(moduleData, "maxDeflection", module.maxDeflection);

            // Parse weapon parameters
            readOptional(moduleData, "weaponType", module.weaponType);
            readOptional(moduleData, "weaponRange", module.weaponRange);

            def.modules.push_back(module);
        }
    }

    // Parse cockpit
    if (root.contains("cockpit")) {
        const auto& cockpitNode = root.at("cockpit");
        def.cockpit.meshPath = cockpitNode.at("mesh").get<std::string>();
        def.cockpit.attachBone = cockpitNode.at("attachBone").get<std::string>();
        readOptionalVec3(cockpitNode, "seatPosition", def.cockpit.seatPosition);

        if (cockpitNode.contains("hudAnchors")) {
            const auto& anchors = cockpitNode.at("hudAnchors");
            for (size_t i = 0; i < 4 && i < anchors.size(); ++i) {
                def.cockpit.hudAnchors[i] = readVec3(anchors.at(i));
            }
        }

        readOptional(cockpitNode, "canopyMaterial", def.cockpit.canopyMaterial);
        readOptional(cockpitNode, "canopyTransparency", def.cockpit.canopyTransparency);
        readOptional(cockpitNode, "enableHolographicHUD", def.cockpit.enableHolographicHUD);
    }

    // Parse Magitech materials
    if (root.contains("magitechMaterials")) {
        const auto& materials = root.at("magitechMaterials");

        if (materials.contains("runeGlow")) {
            const auto& runeGlow = materials.at("runeGlow");
            auto& out = def.magitechMaterials.runeGlow;
            readOptionalVec3(runeGlow, "emissiveColor", out.emissiveColor);
            readOptional(runeGlow, "pulseRate", out.pulseRate);
            readOptional(runeGlow, "patternScale", out.patternScale);
            readOptional(runeGlow, "glowIntensity", out.glowIntensity);
        }

        if (materials.contains("engineHeat")) {
            const auto& engineHeat = materials.at("engineHeat");
            auto& out = def.magitechMaterials.engineHeat;
            readOptional(engineHeat, "distortionIntensity", out.distortionIntensity);
            readOptional(engineHeat, "flickerRate", out.flickerRate);
            readOptionalVec3(engineHeat, "heatColor", out.heatColor);
            readOptional(engineHeat, "maxTemperature", out.maxTemperature);
        }

        if (materials.contains("energyTrail")) {
            const auto& energyTrail = materials.at("energyTrail");
            auto& out = def.magitechMaterials.energyTrail;
            readOptionalVec3(energyTrail, "trailColor", out.trailColor);
            readOptional(energyTrail, "trailLength", out.trailLength);
            readOptional(energyTrail, "trailWidth", out.trailWidth);
            readOptional(energyTrail, "fadeRate", out.fadeRate);
        }
    }

    // Parse flight parameters
    if (root.contains("flightParameters")) {
        const auto& flight = root.at("flightParameters");
        auto& out = def.flightParameters;
        readOptional(flight, "maxSpeed", out.maxSpeed);
        readOptional(flight, "maxAltitude", out.maxAltitude);
        readOptional(flight, "maxThrust", out.maxThrust);
        readOptional(flight, "liftCoefficient", out.liftCoefficient);
        readOptional(flight, "dragCoefficient", out.dragCoefficient);
        readOptional(flight, "turnRate", out.turnRate);
        readOptional(flight, "climbRate", out.climbRate);

        if (flight.contains("controlSurface")) {
            for (const auto& [name, surface] : flight.at("controlSurface").items()) {
                out.controlSurfaceLimits[name] = surface.at("maxDeflection").get<float>();
            }
        }
    }

    // Parse animations
    if (root.contains("animations")) {
        for (const auto& animNode : root.at("animations")) {
            AnimationDefinition anim;
            anim.id = animNode.at("id").get<std::string>();
            anim.path = animNode.at("path").get<std::string>();
            enumFromName(animNode.at("type").get<std::string>(), kAnimationTypeNames, anim.type);

            readOptional(animNode, "speed", anim.speed);
            readOptional(animNode, "loop", anim.loop);
            readOptional(animNode, "blendTime", anim.blendTime);

            def.animations.push_back(anim);
        }
    }

    // Parse physics
    if (root.contains("physics")) {
        const auto& physics = root.at("physics");
        readOptional(physics, "totalMass", def.physics.totalMass);
        readOptionalVec3(physics, "centerOfMass", def.physics.centerOfMass);

        if (physics.contains("moduleMass")) {
            for (const auto& [moduleName, massValue] : physics.at("moduleMass").items()) {
                def.physics.moduleMass[moduleName] = massValue.get<float>();
            }
        }
        if (physics.contains("jointConstraints")) {
            for (const auto& [joint, c] : physics.at("jointConstraints").items()) {
                PhysicsDefinition::JointConstraint jc;
                readOptional(c, "minAngle", jc.minAngle);
                readOptional(c, "maxAngle", jc.maxAngle);
                readOptional(c, "damping", jc.damping);
                readOptional(c, "stiffness", jc.stiffness);
                def.physics.jointConstraints[joint] = jc;
            }
        }
        if (physics.contains("collisionShapes")) {
            for (const auto& [moduleId, s] : physics.at("collisionShapes").items()) {
                PhysicsDefinition::CollisionShape shape;
                if (s.contains("type")) enumFromName(s.at("type").get<std::string>(), kCollisionShapeNames, shape.type);
                readOptionalVec3(s, "size", shape.size);
                readOptional(s, "radius", shape.radius);
                readOptional(s, "height", shape.height);
                def.physics.collisionShapes[moduleId] = shape;
            }
        }
    }

    // Parse LODs
    if (root.contains("lods")) {
        for (const auto& lodNode : root.at("lods")) {
            LODDefinition lod;
            enumFromName(lodNode.at("quality").get<std::string>(), kQualityNames, lod.quality);

            readOptional(lodNode, "meshDecimate", lod.meshDecimate);
            readOptional(lodNode, "materialDetail", lod.materialDetail);
            readOptional(lodNode, "maxBoneInfluences", lod.maxBoneInfluences);
            readOptional(lodNode, "enableShadows", lod.enableShadows);
            readOptional(lodNode, "enableReflections", lod.enableReflections);

            def.lods.push_back(lod);
        }
    }

    return def;
}

Json definitionToJson(const MiniJetDefinition& def) {
    Json root;
    root["name"] = def.name;
    root["version"] = def.version;

    root["modules"] = Json::object();
    for (const auto& m : def.modules) {
        root["modules"][m.id] = {
            {"type", enumName(m.type, kModuleTypeNames)},
            {"mesh", m.meshPath},
            {"attachBone", m.attachBone},
            {"offset", vec3Json(m.offset)},
            {"scale", vec3Json(m.scale)},
            {"rotation", Json::array({m.rotation.w, m.rotation.x, m.rotation.y, m.rotation.z})},
            {"thrustForce", m.thrustForce},
            {"thrustDirection", vec3Json(m.thrustDirection)},
            {"heatDistortion", m.heatDistortion},
            {"controlSurface", enumName(m.controlSurface, kControlSurfaceNames)},
            {"maxDeflection", m.maxDeflection},
            {"weaponType", m.weaponType},
            {"weaponRange", m.weaponRange}};
    }

    Json anchors = Json::array();
    for (const auto& a : def.cockpit.hudAnchors) anchors.push_back(vec3Json(a));
    root["cockpit"] = {{"mesh", def.cockpit.meshPath},
                       {"attachBone", def.cockpit.attachBone},
                       {"seatPosition", vec3Json(def.cockpit.seatPosition)},
                       {"hudAnchors", anchors},
                       {"canopyMaterial", def.cockpit.canopyMaterial},
                       {"canopyTransparency", def.cockpit.canopyTransparency},
                       {"enableHolographicHUD", def.cockpit.enableHolographicHUD}};

    const auto& mm = def.magitechMaterials;
    root["magitechMaterials"] = {
        {"runeGlow", {{"emissiveColor", vec3Json(mm.runeGlow.emissiveColor)}, {"pulseRate", mm.runeGlow.pulseRate},
                      {"patternScale", mm.runeGlow.patternScale}, {"glowIntensity", mm.runeGlow.glowIntensity}}},
        {"engineHeat", {{"distortionIntensity", mm.engineHeat.distortionIntensity}, {"flickerRate", mm.engineHeat.flickerRate},
                        {"heatColor", vec3Json(mm.engineHeat.heatColor)}, {"maxTemperature", mm.engineHeat.maxTemperature}}},
        {"energyTrail", {{"trailColor", vec3Json(mm.energyTrail.trailColor)}, {"trailLength", mm.energyTrail.trailLength},
                         {"trailWidth", mm.energyTrail.trailWidth}, {"fadeRate", mm.energyTrail.fadeRate}}}};

    const auto& fp = def.flightParameters;
    root["flightParameters"] = {{"maxSpeed", fp.maxSpeed}, {"maxAltitude", fp.maxAltitude}, {"maxThrust", fp.maxThrust},
                                {"liftCoefficient", fp.liftCoefficient}, {"dragCoefficient", fp.dragCoefficient},
                                {"turnRate", fp.turnRate}, {"climbRate", fp.climbRate},
                                {"controlSurface", Json::object()}};
    for (const auto& [name, limit] : fp.controlSurfaceLimits) {
        root["flightParameters"]["controlSurface"][name] = {{"maxDeflection", limit}};
    }

    root["animations"] = Json::array();
    for (const auto& a : def.animations) {
        root["animations"].push_back({{"id", a.id}, {"type", enumName(a.type, kAnimationTypeNames)}, {"path", a.path},
                                      {"speed", a.speed}, {"loop", a.loop}, {"blendTime", a.blendTime}});
    }

    Json physics = {{"totalMass", def.physics.totalMass}, {"centerOfMass", vec3Json(def.physics.centerOfMass)},
                    {"moduleMass", def.physics.moduleMass}, {"jointConstraints", Json::object()},
                    {"collisionShapes", Json::object()}};
    for (const auto& [joint, c] : def.physics.jointConstraints) {
        physics["jointConstraints"][joint] = {{"minAngle", c.minAngle}, {"maxAngle", c.maxAngle},
                                              {"damping", c.damping}, {"stiffness", c.stiffness}};
    }
    for (const auto& [id, s] : def.physics.collisionShapes) {
        physics["collisionShapes"][id] = {{"type", enumName(s.type, kCollisionShapeNames)}, {"size", vec3Json(s.size)},
                                          {"radius", s.radius}, {"height", s.height}};
    }
    root["physics"] = physics;

    root["lods"] = Json::array();
    for (const auto& l : def.lods) {
        root["lods"].push_back({{"quality", enumName(l.quality, kQualityNames)}, {"meshDecimate", l.meshDecimate},
                                {"materialDetail", l.materialDetail}, {"maxBoneInfluences", l.maxBoneInfluences},
                                {"enableShadows", l.enableShadows}, {"enableReflections", l.enableReflections}});
    }
    return root;
}

MiniJetDefinition parseFromFile(const std::string& filePath) {
    MiniJetDefinition def;

    try {
        std::ifstream file(filePath);
        if (!file.is_open()) {
            Log::error("MiniJet", "Failed to open MiniJet definition: {}", filePath);
            return def;
        }
        Json root = Json::parse(file);
        def = parseFromJson(root);
        Log::info("MiniJet", "Successfully parsed MiniJet definition: {}", def.name);
    } catch (const Json::exception& e) {
        Log::error("MiniJet", "Failed to parse MiniJet definition from {}: {}", filePath, e.what());
    } catch (const std::exception& e) {
        Log::error("MiniJet", "Error parsing MiniJet definition from {}: {}", filePath, e.what());
    }

    return def;
}

bool validateDefinition(const MiniJetDefinition& def) {
    if (def.name.empty()) {
        Log::error("MiniJet definition validation failed: name is empty");
        return false;
    }

    if (def.modules.empty()) {
        Log::error("MiniJet definition validation failed: no modules defined");
        return false;
    }

    // Check for required modules
    bool hasFuselage = false;
    bool hasCockpit = false;

    for (const auto& module : def.modules) {
        if (module.id.empty()) {
            Log::error("MiniJet definition validation failed: module has empty ID");
            return false;
        }

        if (module.meshPath.empty()) {
            Log::error("MiniJet", "MiniJet definition validation failed: module {} has empty mesh path", module.id);
            return false;
        }

        if (module.type == ModuleType::Fuselage) hasFuselage = true;
        if (module.type == ModuleType::Cockpit) hasCockpit = true;
    }

    if (!hasFuselage) {
        Log::error("MiniJet definition validation failed: no fuselage module found");
        return false;
    }

    if (!hasCockpit) {
        Log::error("MiniJet definition validation failed: no cockpit module found");
        return false;
    }

    // Validate flight parameters
    if (def.flightParameters.maxSpeed <= 0) {
        Log::error("MiniJet definition validation failed: invalid max speed");
        return false;
    }

    if (def.flightParameters.maxAltitude <= 0) {
        Log::error("MiniJet definition validation failed: invalid max altitude");
        return false;
    }

    Log::info("MiniJet", "MiniJet definition validation passed: {}", def.name);
    return true;
}

} // namespace DefinitionParser

// =============================================================================================
// ModuleAssembler implementation
// =============================================================================================
namespace ModuleAssembler {

AssemblyResult assembleModules(const MiniJetDefinition& def) {
    AssemblyResult result;

    Log::info("MiniJet", "Assembling modules for MiniJet: {}", def.name);

    // Load and process each module
    for (const auto& moduleDef : def.modules) {
        // Load mesh from file
        MeshHandle mesh = loadMeshFromFile(moduleDef.meshPath);
        if (!mesh.isValid()) {
            Log::error("MiniJet", "Failed to load mesh for module {}: {}", moduleDef.id, moduleDef.meshPath);
            continue;
        }

        // Apply module transformations
        mesh = applyTransform(mesh, moduleDef.offset, moduleDef.scale, moduleDef.rotation);
        mesh.name = moduleDef.id;

        // Create default material
        MaterialHandle material = createDefaultMaterial();

        result.meshes[moduleDef.id] = mesh;
        result.materials[moduleDef.id] = material;

        Log::debug("MiniJet", "Assembled module: {}", moduleDef.id);
    }

    // Build skeleton from module attachments
    result.skeleton = buildSkeletonFromModules(def.modules);

    Log::info("MiniJet", "Module assembly completed for MiniJet: {}", def.name);
    return result;
}

void weldModuleSeams(AssemblyResult& result, const MiniJetDefinition& def) {
    Log::info("MiniJet", "Welding module seams for MiniJet: {}", def.name);

    // Find adjacent modules and weld their seams (each unordered pair once)
    for (size_t i = 0; i < def.modules.size(); ++i) {
        for (size_t j = i + 1; j < def.modules.size(); ++j) {
            const auto& module1 = def.modules[i];
            const auto& module2 = def.modules[j];
            if (!areModulesAdjacent(module1, module2)) continue;
            auto it1 = result.meshes.find(module1.id);
            auto it2 = result.meshes.find(module2.id);
            if (it1 == result.meshes.end() || it2 == result.meshes.end()) continue;

            // Weld vertices at the seam
            weldMeshesAtSeam(it1->second, it2->second, module1.attachBone, module2.attachBone);
            Log::debug("MiniJet", "Welded seam between {} and {}", module1.id, module2.id);
        }
    }

    Log::info("Module seam welding completed");
}

void bakeSkinWeights(AssemblyResult& result, const MiniJetDefinition& def) {
    Log::info("MiniJet", "Baking skin weights for MiniJet: {}", def.name);

    // Bake skin weights for each module based on skeleton
    for (const auto& moduleDef : def.modules) {
        auto it = result.meshes.find(moduleDef.id);
        if (it == result.meshes.end()) continue;

        // Calculate skin weights based on distance to bones
        bakeSkinWeightsForMesh(it->second, result.skeleton, moduleDef.attachBone);

        Log::debug("MiniJet", "Baked skin weights for module: {}", moduleDef.id);
    }

    Log::info("Skin weight baking completed");
}

} // namespace ModuleAssembler

// =============================================================================================
// MaterialSynthesizer implementation
// =============================================================================================
namespace MaterialSynthesizer {

MaterialResult synthesizeMagitechMaterials(const MiniJetDefinition& def) {
    MaterialResult result;

    Log::info("MiniJet", "Synthesizing Magitech materials for MiniJet: {}", def.name);

    // Create rune glow material
    result.materials["runeGlow"] = createRuneGlowMaterial(def.magitechMaterials.runeGlow);
    result.shaderGraphs["runeGlow"] = generateRuneGlowShaderGraph(def.magitechMaterials.runeGlow);

    // Create engine heat material
    result.materials["engineHeat"] = createEngineHeatMaterial(def.magitechMaterials.engineHeat);
    result.shaderGraphs["engineHeat"] = generateEngineHeatShaderGraph(def.magitechMaterials.engineHeat);

    // Create energy trail material
    result.materials["energyTrail"] = createEnergyTrailMaterial(def.magitechMaterials.energyTrail);
    result.shaderGraphs["energyTrail"] = generateEnergyTrailShaderGraph(def.magitechMaterials.energyTrail);

    // Create canopy material
    result.materials["canopy"] = createCanopyMaterial(def.cockpit.canopyTransparency);
    result.shaderGraphs["canopy"] = generateCanopyShaderGraph(def.cockpit.canopyTransparency);

    Log::info("Magitech material synthesis completed");
    return result;
}

MaterialHandle createRuneGlowMaterial(const MagitechMaterials::RuneGlow& params) {
    MaterialHandle material = createMaterial("RuneGlow");

    // Set material properties
    setMaterialProperty(material, "emissiveColor", params.emissiveColor);
    setMaterialProperty(material, "pulseRate", params.pulseRate);
    setMaterialProperty(material, "patternScale", params.patternScale);
    setMaterialProperty(material, "glowIntensity", params.glowIntensity);

    // Set shader
    setMaterialShader(material, "MagitechRuneGlow");

    return material;
}

MaterialHandle createEngineHeatMaterial(const MagitechMaterials::EngineHeat& params) {
    MaterialHandle material = createMaterial("EngineHeat");

    // Set material properties
    setMaterialProperty(material, "distortionIntensity", params.distortionIntensity);
    setMaterialProperty(material, "flickerRate", params.flickerRate);
    setMaterialProperty(material, "heatColor", params.heatColor);
    setMaterialProperty(material, "maxTemperature", params.maxTemperature);

    // Set shader
    setMaterialShader(material, "MagitechEngineHeat");

    return material;
}

MaterialHandle createEnergyTrailMaterial(const MagitechMaterials::EnergyTrail& params) {
    MaterialHandle material = createMaterial("EnergyTrail");

    // Set material properties
    setMaterialProperty(material, "trailColor", params.trailColor);
    setMaterialProperty(material, "trailLength", params.trailLength);
    setMaterialProperty(material, "trailWidth", params.trailWidth);
    setMaterialProperty(material, "fadeRate", params.fadeRate);

    // Set shader
    setMaterialShader(material, "MagitechEnergyTrail");

    return material;
}

} // namespace MaterialSynthesizer

// =============================================================================================
// AnimationProcessor implementation
// =============================================================================================
namespace AnimationProcessor {

AnimationResult processAnimations(const MiniJetDefinition& def, const Skeleton& skeleton) {
    AnimationResult result;

    Log::info("MiniJet", "Processing animations for MiniJet: {}", def.name);

    for (const auto& animDef : def.animations) {
        // Load animation from file
        Animation sourceAnim = loadAnimationFromFile(animDef.path);
        if (!sourceAnim.isValid()) {
            Log::error("MiniJet", "Failed to load animation: {}", animDef.path);
            continue;
        }

        // Retarget animation to the assembled skeleton
        Animation retargetedAnim = retargetAnimation(sourceAnim, skeleton);
        retargetedAnim.name = animDef.id;

        // Optimize animation based on quality settings
        optimizeAnimation(retargetedAnim, Quality::High); // Default to high quality for processing

        result.animations[animDef.id] = retargetedAnim;
        result.blendTimes[animDef.id] = animDef.blendTime;

        Log::debug("MiniJet", "Processed animation: {}", animDef.id);
    }

    Log::info("Animation processing completed");
    return result;
}

Animation retargetAnimation(const Animation& source, const Skeleton& target) {
    Animation retargeted = source.clone();

    // Map bone names between source and target skeletons
    std::unordered_map<std::string, std::string> boneMapping = createBoneMapping(source.getSkeleton(), target);

    // Retarget animation data
    for (auto& track : retargeted.getTracks()) {
        auto it = boneMapping.find(track.boneName);
        if (it != boneMapping.end() && !it->second.empty()) {
            track.boneName = it->second;
        }
    }
    retargeted.skeleton = target;

    return retargeted;
}

void optimizeAnimation(Animation& anim, Quality quality) {
    switch (quality) {
        case Quality::Ultra:
            // No optimization for ultra quality
            break;
        case Quality::High:
            // Light optimization
            reduceKeyframeDensity(anim, 0.8f);
            break;
        case Quality::Medium:
            // Medium optimization
            reduceKeyframeDensity(anim, 0.6f);
            simplifyCurves(anim);
            break;
        case Quality::Low:
        default:
            // Heavy optimization
            reduceKeyframeDensity(anim, 0.3f);
            simplifyCurves(anim);
            removeUnusedTracks(anim);
            break;
    }
}

} // namespace AnimationProcessor

// =============================================================================================
// PhysicsRigBuilder implementation
// =============================================================================================
namespace PhysicsRigBuilder {

PhysicsResult buildPhysicsRig(const MiniJetDefinition& def) {
    PhysicsResult result;

    Log::info("MiniJet", "Building physics rig for MiniJet: {}", def.name);

    // Create physics bodies for each module
    for (const auto& moduleDef : def.modules) {
        // Get collision shape for this module
        auto shapeIt = def.physics.collisionShapes.find(moduleDef.id);
        if (shapeIt != def.physics.collisionShapes.end()) {
            PhysicsBody body = createModuleCollider(moduleDef, shapeIt->second);
            auto massIt = def.physics.moduleMass.find(moduleDef.id);
            if (massIt != def.physics.moduleMass.end()) setBodyMass(body, massIt->second);
            result.bodies[moduleDef.id] = body;
        }

        // Create thruster node if this is a thruster module
        if (moduleDef.thrustForce > 0) {
            ThrusterNode thruster = createThrusterNode(moduleDef);
            result.thrusters[moduleDef.id] = thruster;
        }
    }

    // Create joints between modules
    for (const auto& module1 : def.modules) {
        for (const auto& module2 : def.modules) {
            if (module1.id == module2.id) continue;

            if (areModulesConnected(module1, module2)) {
                std::string jointName = module1.id + "_to_" + module2.id;
                result.joints.push_back({module1.id, module2.id});

                Log::debug("MiniJet", "Created joint: {}", jointName);
            }
        }
    }

    Log::info("Physics rig building completed");
    return result;
}

PhysicsBody createModuleCollider(const ModuleDefinition& module, const PhysicsDefinition::CollisionShape& shape) {
    PhysicsBody body = createPhysicsBody();
    body.name = module.id;

    switch (shape.type) {
        case PhysicsDefinition::CollisionShape::Type::Box:
            setBoxCollider(body, shape.size * module.scale);
            break;
        case PhysicsDefinition::CollisionShape::Type::Capsule:
            setCapsuleCollider(body, shape.radius, shape.height);
            break;
        case PhysicsDefinition::CollisionShape::Type::ConvexHull:
            setConvexHullCollider(body, module.meshPath);
            for (auto& p : body.hullPoints) p = module.rotation * (p * module.scale) + module.offset;
            break;
    }

    // Set mass based on module type
    float mass = getModuleMass(module.type);
    setBodyMass(body, mass);

    return body;
}

ThrusterNode createThrusterNode(const ModuleDefinition& module) {
    ThrusterNode thruster = MiniJetGen::createThrusterNode();
    thruster.name = module.id;
    thruster.position = module.offset;

    // Set thruster properties
    setThrusterForce(thruster, module.thrustForce);
    setThrusterDirection(thruster, module.rotation * module.thrustDirection);
    setThrusterHeat(thruster, module.heatDistortion);

    return thruster;
}

} // namespace PhysicsRigBuilder

// =============================================================================================
// LODGenerator implementation
// =============================================================================================
namespace LODGenerator {

LODResult generateLODs(const MiniJetDefinition& def, const ModuleAssembler::AssemblyResult& assembly) {
    LODResult result;

    Log::info("MiniJet", "Generating LODs for MiniJet: {}", def.name);

    // Generate LODs for each module
    for (const auto& moduleDef : def.modules) {
        auto meshIt = assembly.meshes.find(moduleDef.id);
        auto materialIt = assembly.materials.find(moduleDef.id);
        if (meshIt == assembly.meshes.end()) continue;
        const MeshHandle& sourceMesh = meshIt->second;
        const MaterialHandle sourceMaterial = materialIt != assembly.materials.end() ? materialIt->second : createDefaultMaterial();

        auto& meshes = result.lodMeshes[moduleDef.id];
        auto& materials = result.lodMaterials[moduleDef.id];
        // Every quality slot gets the source until a LOD definition overrides it
        meshes.fill(sourceMesh);
        materials.fill(sourceMaterial);

        // Generate LOD meshes
        for (const auto& lodDef : def.lods) {
            const size_t slot = static_cast<size_t>(lodDef.quality);
            if (slot >= meshes.size()) continue;
            meshes[slot] = decimateMesh(sourceMesh, lodDef.meshDecimate);
            materials[slot] = simplifyMaterial(sourceMaterial, lodDef.materialDetail);
            materials[slot].floatParams["castShadows"] = lodDef.enableShadows ? 1.0f : 0.0f;
            materials[slot].floatParams["reflections"] = lodDef.enableReflections ? 1.0f : 0.0f;
            materials[slot].floatParams["maxBoneInfluences"] = static_cast<float>(lodDef.maxBoneInfluences);
        }

        Log::debug("MiniJet", "Generated LODs for module: {}", moduleDef.id);
    }

    Log::info("LOD generation completed");
    return result;
}

MeshHandle decimateMesh(const MeshHandle& mesh, float decimateFactor) {
    if (decimateFactor <= 0.0f) {
        return mesh; // No decimation
    }

    // Create decimated mesh
    MeshHandle decimatedMesh = createMesh();

    // Apply mesh decimation algorithm
    decimateMeshGeometry(mesh, decimatedMesh, decimateFactor);

    return decimatedMesh;
}

MaterialHandle simplifyMaterial(const MaterialHandle& material, float detailLevel) {
    if (detailLevel >= 1.0f) {
        return material; // No simplification
    }

    // Create simplified material
    MaterialHandle simplifiedMaterial = createMaterial();

    // Copy base properties
    copyMaterialProperties(material, simplifiedMaterial);

    // Reduce texture resolution
    reduceTextureResolution(simplifiedMaterial, detailLevel);

    // Simplify shader complexity
    simplifyShader(simplifiedMaterial, detailLevel);

    return simplifiedMaterial;
}

} // namespace LODGenerator

// =============================================================================================
// PackageWriter implementation
// =============================================================================================
namespace PackageWriter {

bool writePackage(const std::string& name, const MiniJetAsset& asset) {
    return writePackageTo("assets/minijets/" + name + ".mjpack", asset);
}

bool writePackageTo(const std::string& packagePath, const MiniJetAsset& asset) {
    Log::info("MiniJet", "Writing MiniJet package: {}", packagePath);

    try {
        // Create package directory
        std::filesystem::create_directories(packagePath);
        bool ok = true;

        // Write meshes
        for (const auto& [moduleName, moduleAssets] : asset.modules) {
            for (size_t i = 0; i < static_cast<size_t>(Quality::COUNT); ++i) {
                std::string meshPath = packagePath + "/meshes/" + getQualityName(static_cast<Quality>(i)) + "/" + moduleName + ".bin";
                std::filesystem::create_directories(std::filesystem::path(meshPath).parent_path());
                ok &= writeMesh(meshPath, moduleAssets.lodMeshes[i]);
            }
        }

        // Write materials
        for (const auto& [moduleName, moduleAssets] : asset.modules) {
            for (size_t i = 0; i < static_cast<size_t>(Quality::COUNT); ++i) {
                std::string materialPath = packagePath + "/materials/" + getQualityName(static_cast<Quality>(i)) + "/" + moduleName + ".mat";
                std::filesystem::create_directories(std::filesystem::path(materialPath).parent_path());
                ok &= writeMaterial(materialPath, moduleAssets.lodMaterials[i]);
            }
        }

        // Write animations
        for (const auto& [animName, animation] : asset.animations) {
            std::string animPath = packagePath + "/animations/" + animName + ".anim";
            std::filesystem::create_directories(std::filesystem::path(animPath).parent_path());
            ok &= writeAnimation(animPath, animation);
        }

        // Write skeleton
        {
            std::ofstream file(packagePath + "/skeleton.bin", std::ios::binary);
            if (file.is_open()) serializeSkeleton(asset.skeleton, file);
            ok &= static_cast<bool>(file);
        }

        // Write physics (bodies and thrusters from the modules, joints from the definition)
        std::string physicsPath = packagePath + "/physics/rig.bin";
        std::filesystem::create_directories(std::filesystem::path(physicsPath).parent_path());
        ok &= writePhysics(physicsPath, physicsFromAsset(asset));

        // Write metadata
        std::string metadataPath = packagePath + "/metadata.json";
        ok &= writeMetadata(metadataPath, asset.definition);

        if (!ok) {
            Log::error("MiniJet", "MiniJet package written with errors: {}", packagePath);
            return false;
        }
        Log::info("MiniJet", "MiniJet package written successfully: {}", packagePath);
        return true;

    } catch (const std::exception& e) {
        Log::error("MiniJet", "Failed to write MiniJet package: {}", e.what());
        return false;
    }
}

bool writeMesh(const std::string& path, const MeshHandle& mesh) {
    // Serialize mesh data to binary format
    std::ofstream file(path, std::ios::binary);
    if (!file.is_open()) {
        Log::error("MiniJet", "Failed to open mesh file for writing: {}", path);
        return false;
    }

    // Write mesh data
    serializeMesh(mesh, file);

    return static_cast<bool>(file);
}

bool writeMaterial(const std::string& path, const MaterialHandle& material) {
    // Serialize material data to binary format
    std::ofstream file(path, std::ios::binary);
    if (!file.is_open()) {
        Log::error("MiniJet", "Failed to open material file for writing: {}", path);
        return false;
    }

    // Write material data
    serializeMaterial(material, file);

    return static_cast<bool>(file);
}

bool writeAnimation(const std::string& path, const Animation& animation) {
    // Serialize animation data to binary format
    std::ofstream file(path, std::ios::binary);
    if (!file.is_open()) {
        Log::error("MiniJet", "Failed to open animation file for writing: {}", path);
        return false;
    }

    // Write animation data
    serializeAnimation(animation, file);

    return static_cast<bool>(file);
}

bool writePhysics(const std::string& path, const PhysicsRigBuilder::PhysicsResult& physics) {
    // Serialize physics data to binary format
    std::ofstream file(path, std::ios::binary);
    if (!file.is_open()) {
        Log::error("MiniJet", "Failed to open physics file for writing: {}", path);
        return false;
    }

    // Write physics data
    serializePhysics(physics, file);

    return static_cast<bool>(file);
}

bool writeMetadata(const std::string& path, const MiniJetDefinition& def) {
    // Write metadata as JSON
    std::ofstream file(path);
    if (!file.is_open()) {
        Log::error("MiniJet", "Failed to open metadata file for writing: {}", path);
        return false;
    }

    // Convert definition to JSON and write
    file << DefinitionParser::definitionToJson(def).dump(2);

    return static_cast<bool>(file);
}

} // namespace PackageWriter

// =============================================================================================
// PackageReader implementation
// =============================================================================================
namespace PackageReader {

MiniJetAsset readPackage(const std::string& name) {
    return readPackageFrom("assets/minijets/" + name + ".mjpack");
}

MiniJetAsset readPackageFrom(const std::string& packagePath) {
    Log::info("MiniJet", "Reading MiniJet package: {}", packagePath);

    MiniJetAsset asset;

    try {
        // Read metadata
        std::string metadataPath = packagePath + "/metadata.json";
        asset.definition = readMetadata(metadataPath);
        if (asset.definition.name.empty()) {
            return asset;
        }

        // Read meshes and materials for each module
        for (const auto& moduleDef : asset.definition.modules) {
            ModuleAssets moduleAssets;

            // Read LOD meshes and materials
            for (size_t i = 0; i < static_cast<size_t>(Quality::COUNT); ++i) {
                std::string meshPath = packagePath + "/meshes/" + getQualityName(static_cast<Quality>(i)) + "/" + moduleDef.id + ".bin";
                std::string materialPath = packagePath + "/materials/" + getQualityName(static_cast<Quality>(i)) + "/" + moduleDef.id + ".mat";

                moduleAssets.lodMeshes[i] = readMesh(meshPath);
                moduleAssets.lodMaterials[i] = readMaterial(materialPath);
            }

            asset.modules[moduleDef.id] = moduleAssets;
        }

        // Read animations
        for (const auto& animDef : asset.definition.animations) {
            std::string animPath = packagePath + "/animations/" + animDef.id + ".anim";
            asset.animations[animDef.id] = readAnimation(animPath);
        }

        // Read skeleton
        {
            std::ifstream file(packagePath + "/skeleton.bin", std::ios::binary);
            if (!file.is_open() || !deserializeSkeleton(file, asset.skeleton)) {
                Log::warn("MiniJet", "Package has no readable skeleton: {}", packagePath);
            }
        }

        // Read physics
        std::string physicsPath = packagePath + "/physics/rig.bin";
        PhysicsRigBuilder::PhysicsResult physics = readPhysics(physicsPath);
        asset.physicsBodies = physics.bodies;
        for (auto& [id, module] : asset.modules) {
            if (auto it = physics.bodies.find(id); it != physics.bodies.end()) module.physicsBody = it->second;
            if (auto it = physics.thrusters.find(id); it != physics.thrusters.end()) module.thruster = it->second;
        }

        Log::info("MiniJet", "MiniJet package read successfully: {}", packagePath);

    } catch (const std::exception& e) {
        Log::error("MiniJet", "Failed to read MiniJet package: {}", e.what());
    }

    return asset;
}

MeshHandle readMesh(const std::string& path) {
    std::ifstream file(path, std::ios::binary);
    if (!file.is_open()) {
        Log::error("MiniJet", "Failed to open mesh file for reading: {}", path);
        return MeshHandle{};
    }

    // Deserialize mesh data
    return deserializeMesh(file);
}

MaterialHandle readMaterial(const std::string& path) {
    std::ifstream file(path, std::ios::binary);
    if (!file.is_open()) {
        Log::error("MiniJet", "Failed to open material file for reading: {}", path);
        return MaterialHandle{};
    }

    // Deserialize material data
    return deserializeMaterial(file);
}

Animation readAnimation(const std::string& path) {
    std::ifstream file(path, std::ios::binary);
    if (!file.is_open()) {
        Log::error("MiniJet", "Failed to open animation file for reading: {}", path);
        return Animation{};
    }

    // Deserialize animation data
    return deserializeAnimation(file);
}

PhysicsRigBuilder::PhysicsResult readPhysics(const std::string& path) {
    PhysicsRigBuilder::PhysicsResult physics;
    std::ifstream file(path, std::ios::binary);
    if (!file.is_open()) {
        Log::error("MiniJet", "Failed to open physics file for reading: {}", path);
        return physics;
    }

    // Deserialize physics data
    if (!deserializePhysics(file, physics)) {
        Log::error("MiniJet", "Corrupt physics file: {}", path);
        return PhysicsRigBuilder::PhysicsResult{};
    }
    return physics;
}

MiniJetDefinition readMetadata(const std::string& path) {
    std::ifstream file(path);
    if (!file.is_open()) {
        Log::error("MiniJet", "Failed to open metadata file for reading: {}", path);
        return MiniJetDefinition{};
    }

    // Read JSON and convert to definition
    Json root = Json::parse(file, nullptr, false);
    if (root.is_discarded()) {
        Log::error("MiniJet", "Invalid metadata JSON: {}", path);
        return MiniJetDefinition{};
    }
    try {
        return DefinitionParser::parseFromJson(root);
    } catch (const Json::exception& e) {
        Log::error("MiniJet", "Invalid metadata {}: {}", path, e.what());
        return MiniJetDefinition{};
    }
}

} // namespace PackageReader

} // namespace MiniJetGen
