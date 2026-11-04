#include "WeaponGen.hpp"
#include "core/Log.hpp"
#include "vendor/json/include/nlohmann/json.hpp"
#include <stb_image.h>
#include <algorithm>
#include <array>
#include <cmath>
#include <cstring>
#include <numeric>
#include <stdexcept>
#include <random>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <sstream>
#include <unordered_map>

namespace MagiTech {
namespace Audio {
namespace Weapons {

// Constants
constexpr float PI = 3.14159265359f;
constexpr float TWO_PI = 2.0f * PI;

namespace {

using Json = nlohmann::json;

// ---------------------------------------------------------------------------------------------
// Mesh building helpers
// ---------------------------------------------------------------------------------------------

uint32_t addVertex(WeaponMesh& mesh, const glm::vec3& p) {
    Vertex v;
    v.position = p;
    mesh.vertices.push_back(v);
    return static_cast<uint32_t>(mesh.vertices.size() - 1);
}

void addTri(WeaponMesh& mesh, uint32_t a, uint32_t b, uint32_t c) {
    mesh.indices.push_back(a);
    mesh.indices.push_back(b);
    mesh.indices.push_back(c);
}

void addQuad(WeaponMesh& mesh, uint32_t a, uint32_t b, uint32_t c, uint32_t d) {
    addTri(mesh, a, b, c);
    addTri(mesh, a, c, d);
}

// Keeps vertexCount / indexCount / boundingBox consistent with the geometry arrays.
void finalizeMesh(WeaponMesh& mesh) {
    mesh.vertexCount = static_cast<uint32_t>(mesh.vertices.size());
    mesh.indexCount = static_cast<uint32_t>(mesh.indices.size());
    if (mesh.vertices.empty()) {
        mesh.boundingBox = {glm::vec3(0.0f), glm::vec3(0.0f)};
        return;
    }
    glm::vec3 mn(std::numeric_limits<float>::max()), mx(-std::numeric_limits<float>::max());
    for (const auto& v : mesh.vertices) {
        mn = glm::min(mn, v.position);
        mx = glm::max(mx, v.position);
    }
    mesh.boundingBox = {mn, mx};
}

void appendMesh(WeaponMesh& dst, const WeaponMesh& src, const glm::vec3& offset) {
    const uint32_t base = static_cast<uint32_t>(dst.vertices.size());
    for (Vertex v : src.vertices) {
        v.position += offset;
        dst.vertices.push_back(v);
    }
    for (uint32_t i : src.indices) dst.indices.push_back(base + i);
}

// Closed loft of rings: rings[i] are vertex rings (same size) along the part; caps at both ends.
WeaponMesh loftRings(const std::vector<std::vector<glm::vec3>>& rings, bool capStart, bool capEnd) {
    WeaponMesh mesh;
    if (rings.size() < 2) return mesh;
    const size_t n = rings.front().size();
    std::vector<std::vector<uint32_t>> ids(rings.size());
    for (size_t r = 0; r < rings.size(); ++r)
        for (const auto& p : rings[r]) ids[r].push_back(addVertex(mesh, p));
    for (size_t r = 0; r + 1 < rings.size(); ++r) {
        for (size_t i = 0; i < n; ++i) {
            const size_t j = (i + 1) % n;
            addQuad(mesh, ids[r][i], ids[r][j], ids[r + 1][j], ids[r + 1][i]);
        }
    }
    auto cap = [&](const std::vector<glm::vec3>& ring, bool reverse) {
        glm::vec3 c(0.0f);
        for (const auto& p : ring) c += p;
        c /= static_cast<float>(ring.size());
        const uint32_t center = addVertex(mesh, c);
        const uint32_t first = addVertex(mesh, ring[0]);
        std::vector<uint32_t> loop{first};
        for (size_t i = 1; i < ring.size(); ++i) loop.push_back(addVertex(mesh, ring[i]));
        for (size_t i = 0; i < loop.size(); ++i) {
            const uint32_t a = loop[i], b = loop[(i + 1) % loop.size()];
            if (reverse) addTri(mesh, center, b, a);
            else addTri(mesh, center, a, b);
        }
    };
    if (capStart) cap(rings.front(), false);
    if (capEnd) cap(rings.back(), true);
    return mesh;
}

std::vector<glm::vec3> circleRing(float y, float rx, float rz, int segments, const glm::vec3& center = glm::vec3(0.0f)) {
    std::vector<glm::vec3> ring;
    for (int i = 0; i < segments; ++i) {
        const float a = TWO_PI * static_cast<float>(i) / static_cast<float>(segments);
        ring.push_back(center + glm::vec3(std::cos(a) * rx, y, std::sin(a) * rz));
    }
    return ring;
}

// Ellipsoid / sphere centred at the origin with radii (rx, ry, rz); profile scales each latitude.
WeaponMesh ellipsoid(float rx, float ry, float rz, int segments, int stacks, float (*profile)(float) = nullptr) {
    std::vector<std::vector<glm::vec3>> rings;
    for (int s = 1; s < stacks; ++s) {
        const float t = static_cast<float>(s) / static_cast<float>(stacks);   // 0 bottom .. 1 top
        const float phi = PI * t;
        float scale = std::sin(phi);
        if (profile) scale *= profile(t);
        rings.push_back(circleRing(-std::cos(phi) * ry, rx * scale, rz * scale, segments));
    }
    WeaponMesh mesh = loftRings(rings, false, false);
    // poles
    const uint32_t bottom = addVertex(mesh, glm::vec3(0.0f, -ry, 0.0f));
    const uint32_t top = addVertex(mesh, glm::vec3(0.0f, ry, 0.0f));
    const uint32_t lastRing = static_cast<uint32_t>((rings.size() - 1) * segments);
    for (int i = 0; i < segments; ++i) {
        const uint32_t j = static_cast<uint32_t>((i + 1) % segments);
        addTri(mesh, bottom, j, static_cast<uint32_t>(i));
        addTri(mesh, top, lastRing + static_cast<uint32_t>(i), lastRing + j);
    }
    return mesh;
}

// Axis-aligned box centred at c
WeaponMesh box(const glm::vec3& c, const glm::vec3& size) {
    const glm::vec3 h = size * 0.5f;
    std::vector<std::vector<glm::vec3>> rings = {
        {c + glm::vec3(-h.x, -h.y, -h.z), c + glm::vec3(h.x, -h.y, -h.z), c + glm::vec3(h.x, -h.y, h.z), c + glm::vec3(-h.x, -h.y, h.z)},
        {c + glm::vec3(-h.x, h.y, -h.z), c + glm::vec3(h.x, h.y, -h.z), c + glm::vec3(h.x, h.y, h.z), c + glm::vec3(-h.x, h.y, h.z)}};
    return loftRings(rings, true, true);
}

float param(const std::map<std::string, float>& params, const char* key, float fallback) {
    auto it = params.find(key);
    return it != params.end() ? it->second : fallback;
}

float teardropProfile(float t) { return 0.6f + 0.6f * (1.0f - t); }
float brazilNutProfile(float t) { return 0.75f + 0.25f * std::cos(TWO_PI * t); }

// ---------------------------------------------------------------------------------------------
// Convex hull (incremental, O(n^2)) for collider generation
// ---------------------------------------------------------------------------------------------

struct HullFace {
    uint32_t a, b, c;
    glm::vec3 normal;
    float offset;
};

std::vector<HullFace> convexHull(const std::vector<glm::vec3>& pts) {
    std::vector<HullFace> faces;
    if (pts.size() < 4) return faces;
    auto makeFace = [&](uint32_t a, uint32_t b, uint32_t c) {
        glm::vec3 n = glm::cross(pts[b] - pts[a], pts[c] - pts[a]);
        const float len = glm::length(n);
        n = len > 0 ? n / len : glm::vec3(0.0f);
        return HullFace{a, b, c, n, glm::dot(n, pts[a])};
    };
    // initial tetrahedron from extreme, non-degenerate points
    uint32_t i0 = 0, i1 = 0;
    for (uint32_t i = 1; i < pts.size(); ++i) {
        if (pts[i].x < pts[i0].x) i0 = i;
        if (pts[i].x > pts[i1].x) i1 = i;
    }
    if (glm::length(pts[i1] - pts[i0]) < 1e-7f) return faces;
    uint32_t i2 = i0;
    float best = 0.0f;
    for (uint32_t i = 0; i < pts.size(); ++i) {
        const float d = glm::length(glm::cross(pts[i1] - pts[i0], pts[i] - pts[i0]));
        if (d > best) { best = d; i2 = i; }
    }
    if (best < 1e-9f) return faces;
    const glm::vec3 pn = glm::normalize(glm::cross(pts[i1] - pts[i0], pts[i2] - pts[i0]));
    uint32_t i3 = i0;
    best = 0.0f;
    for (uint32_t i = 0; i < pts.size(); ++i) {
        const float d = std::abs(glm::dot(pn, pts[i] - pts[i0]));
        if (d > best) { best = d; i3 = i; }
    }
    if (best < 1e-7f) return faces;

    const glm::vec3 centroid = (pts[i0] + pts[i1] + pts[i2] + pts[i3]) * 0.25f;
    auto oriented = [&](uint32_t a, uint32_t b, uint32_t c) {
        HullFace f = makeFace(a, b, c);
        if (glm::dot(f.normal, centroid) - f.offset > 0) f = makeFace(a, c, b);
        return f;
    };
    faces = {oriented(i0, i1, i2), oriented(i0, i1, i3), oriented(i0, i2, i3), oriented(i1, i2, i3)};

    constexpr float eps = 1e-6f;
    for (uint32_t p = 0; p < pts.size(); ++p) {
        std::vector<bool> visible(faces.size(), false);
        bool any = false;
        for (size_t f = 0; f < faces.size(); ++f) {
            if (glm::dot(faces[f].normal, pts[p]) - faces[f].offset > eps) {
                visible[f] = true;
                any = true;
            }
        }
        if (!any) continue;
        // horizon edges: edges of visible faces not shared with another visible face
        std::map<std::pair<uint32_t, uint32_t>, int> edgeCount;
        for (size_t f = 0; f < faces.size(); ++f) {
            if (!visible[f]) continue;
            const uint32_t e[3][2] = {{faces[f].a, faces[f].b}, {faces[f].b, faces[f].c}, {faces[f].c, faces[f].a}};
            for (auto& ed : e) edgeCount[{ed[0], ed[1]}]++;
        }
        std::vector<HullFace> next;
        for (size_t f = 0; f < faces.size(); ++f)
            if (!visible[f]) next.push_back(faces[f]);
        for (const auto& [edge, count] : edgeCount) {
            if (edgeCount.count({edge.second, edge.first})) continue; // shared between visible faces
            next.push_back(makeFace(edge.first, edge.second, p));
        }
        faces = std::move(next);
    }
    return faces;
}

// ---------------------------------------------------------------------------------------------
// JSON <-> definition
// ---------------------------------------------------------------------------------------------

template <typename E, size_t N>
E enumFromString(const std::string& s, const std::array<const char*, N>& names, E fallback) {
    for (size_t i = 0; i < N; ++i)
        if (s == names[i]) return static_cast<E>(i);
    return fallback;
}

constexpr std::array<const char*, 10> kWeaponTypes = {"sword", "axe", "mace", "dagger", "spear", "bow", "crossbow", "staff", "wand", "shield"};
constexpr std::array<const char*, 6> kBladeShapes = {"straight", "curved", "wavy", "serrated", "double_edged", "single_edged"};
constexpr std::array<const char*, 5> kGuardStyles = {"cross", "basket", "ring", "quillon", "none"};
constexpr std::array<const char*, 5> kPommelStyles = {"ball", "wheel", "teardrop", "brazil_nut", "none"};
constexpr std::array<const char*, 6> kShaderTypes = {"pbr_metal", "pbr_leather", "pbr_wood", "pbr_stone", "unlit", "emissive"};
constexpr std::array<const char*, 4> kCollisionTypes = {"convex_hull", "primitive", "mesh", "none"};
constexpr std::array<const char*, 4> kQualityLevels = {"low", "medium", "high", "ultra"};

template <typename T>
void readIf(const Json& j, const char* key, T& out) {
    if (j.contains(key)) out = j.at(key).get<T>();
}

uint64_t fnv1a(uint64_t h, const void* data, size_t size) {
    const auto* p = static_cast<const uint8_t*>(data);
    for (size_t i = 0; i < size; ++i) {
        h ^= p[i];
        h *= 1099511628211ULL;
    }
    return h;
}

uint64_t hashMesh(uint64_t h, const WeaponMesh& mesh) {
    for (const auto& v : mesh.vertices) h = fnv1a(h, &v.position, sizeof(v.position));
    if (!mesh.indices.empty()) h = fnv1a(h, mesh.indices.data(), mesh.indices.size() * sizeof(uint32_t));
    return h;
}

template <typename T>
void writePod(std::ofstream& out, const T& v) {
    out.write(reinterpret_cast<const char*>(&v), sizeof(T));
}

void writeBlob(std::ofstream& out, const void* data, size_t size) {
    writePod(out, static_cast<uint64_t>(size));
    if (size) out.write(static_cast<const char*>(data), static_cast<std::streamsize>(size));
}

void writeString(std::ofstream& out, const std::string& s) {
    writeBlob(out, s.data(), s.size());
}

void writeMesh(std::ofstream& out, const WeaponMesh& mesh) {
    writePod(out, static_cast<uint32_t>(mesh.vertices.size()));
    writePod(out, static_cast<uint32_t>(mesh.indices.size()));
    if (!mesh.vertices.empty())
        out.write(reinterpret_cast<const char*>(mesh.vertices.data()), static_cast<std::streamsize>(mesh.vertices.size() * sizeof(Vertex)));
    if (!mesh.indices.empty())
        out.write(reinterpret_cast<const char*>(mesh.indices.data()), static_cast<std::streamsize>(mesh.indices.size() * sizeof(uint32_t)));
}

Json definitionToJson(const WeaponDefinition& def) {
    Json j;
    j["name"] = def.name;
    j["type"] = kWeaponTypes[static_cast<size_t>(def.type)];
    j["description"] = def.description;
    const auto& p = def.parts;
    j["parts"]["blade"] = {{"shape", kBladeShapes[static_cast<size_t>(p.blade.shape)]}, {"length", p.blade.length},
                           {"width", p.blade.width}, {"thickness", p.blade.thickness}, {"bevel", p.blade.bevel},
                           {"curvature", p.blade.curvature}, {"parameters", p.blade.parameters}};
    j["parts"]["guard"] = {{"style", kGuardStyles[static_cast<size_t>(p.guard.style)]}, {"width", p.guard.width},
                           {"thickness", p.guard.thickness}, {"parameters", p.guard.parameters}};
    j["parts"]["hilt"] = {{"length", p.hilt.length}, {"radius", p.hilt.radius}, {"parameters", p.hilt.parameters}};
    j["parts"]["pommel"] = {{"style", kPommelStyles[static_cast<size_t>(p.pommel.style)]}, {"radius", p.pommel.radius},
                            {"parameters", p.pommel.parameters}};
    j["parts"]["additional"] = p.additionalParts;
    for (const auto& [name, m] : def.materials) {
        j["materials"][name] = {{"shader", kShaderTypes[static_cast<size_t>(m.shader)]}, {"textures", m.textures},
                                {"parameters", m.parameters}};
    }
    j["animations"] = def.animations;
    j["physics"] = {{"collisionType", kCollisionTypes[static_cast<size_t>(def.physics.collisionType)]},
                    {"mass", def.physics.mass}, {"friction", def.physics.friction},
                    {"restitution", def.physics.restitution}, {"parameters", def.physics.parameters}};
    j["variants"] = Json::array();
    for (const auto& v : def.variants) {
        j["variants"].push_back({{"quality", kQualityLevels[static_cast<size_t>(v.quality)]},
                                 {"lodReduction", v.lodReduction}, {"parameters", v.parameters}});
    }
    j["metadata"] = def.metadata;
    j["tags"] = def.tags;
    j["enableHotReload"] = def.enableHotReload;
    j["enableCaching"] = def.enableCaching;
    j["enableParallelProcessing"] = def.enableParallelProcessing;
    j["maxConcurrentParts"] = def.maxConcurrentParts;
    return j;
}

void definitionFromJson(const Json& j, WeaponDefinition& def) {
    readIf(j, "name", def.name);
    if (j.contains("type")) def.type = enumFromString(j.at("type").get<std::string>(), kWeaponTypes, def.type);
    readIf(j, "description", def.description);
    if (j.contains("parts")) {
        const Json& parts = j.at("parts");
        if (parts.contains("blade")) {
            const Json& b = parts.at("blade");
            auto& blade = def.parts.blade;
            if (b.contains("shape")) blade.shape = enumFromString(b.at("shape").get<std::string>(), kBladeShapes, blade.shape);
            readIf(b, "length", blade.length);
            readIf(b, "width", blade.width);
            readIf(b, "thickness", blade.thickness);
            readIf(b, "bevel", blade.bevel);
            readIf(b, "curvature", blade.curvature);
            readIf(b, "parameters", blade.parameters);
        }
        if (parts.contains("guard")) {
            const Json& g = parts.at("guard");
            auto& guard = def.parts.guard;
            if (g.contains("style")) guard.style = enumFromString(g.at("style").get<std::string>(), kGuardStyles, guard.style);
            readIf(g, "width", guard.width);
            readIf(g, "thickness", guard.thickness);
            readIf(g, "parameters", guard.parameters);
        }
        if (parts.contains("hilt")) {
            const Json& h = parts.at("hilt");
            readIf(h, "length", def.parts.hilt.length);
            readIf(h, "radius", def.parts.hilt.radius);
            readIf(h, "parameters", def.parts.hilt.parameters);
        }
        if (parts.contains("pommel")) {
            const Json& pm = parts.at("pommel");
            auto& pommel = def.parts.pommel;
            if (pm.contains("style")) pommel.style = enumFromString(pm.at("style").get<std::string>(), kPommelStyles, pommel.style);
            readIf(pm, "radius", pommel.radius);
            readIf(pm, "parameters", pommel.parameters);
        }
        readIf(parts, "additional", def.parts.additionalParts);
    }
    if (j.contains("materials")) {
        def.materials.clear();
        for (const auto& [name, m] : j.at("materials").items()) {
            MaterialDefinition md;
            if (m.contains("shader")) md.shader = enumFromString(m.at("shader").get<std::string>(), kShaderTypes, md.shader);
            readIf(m, "textures", md.textures);
            readIf(m, "parameters", md.parameters);
            def.materials[name] = md;
        }
    }
    if (j.contains("animations")) {
        def.animations = j.at("animations").get<std::map<std::string, std::string>>();
    }
    if (j.contains("physics")) {
        const Json& ph = j.at("physics");
        if (ph.contains("collisionType"))
            def.physics.collisionType = enumFromString(ph.at("collisionType").get<std::string>(), kCollisionTypes, def.physics.collisionType);
        readIf(ph, "mass", def.physics.mass);
        readIf(ph, "friction", def.physics.friction);
        readIf(ph, "restitution", def.physics.restitution);
        readIf(ph, "parameters", def.physics.parameters);
    }
    if (j.contains("variants")) {
        def.variants.clear();
        for (const auto& v : j.at("variants")) {
            WeaponVariant wv;
            if (v.contains("quality")) wv.quality = enumFromString(v.at("quality").get<std::string>(), kQualityLevels, wv.quality);
            readIf(v, "lodReduction", wv.lodReduction);
            readIf(v, "parameters", wv.parameters);
            def.variants.push_back(wv);
        }
    }
    readIf(j, "metadata", def.metadata);
    readIf(j, "tags", def.tags);
    readIf(j, "enableHotReload", def.enableHotReload);
    readIf(j, "enableCaching", def.enableCaching);
    readIf(j, "enableParallelProcessing", def.enableParallelProcessing);
    readIf(j, "maxConcurrentParts", def.maxConcurrentParts);
}

// Built-in longsword: the template every loaded definition starts from.
WeaponDefinition longswordTemplate() {
    WeaponDefinition def;
    def.name = "longsword";
    def.type = WeaponType::SWORD;
    def.description = "A classic longsword";

    def.parts.blade.shape = BladeShape::STRAIGHT;
    def.parts.blade.length = 1.2f;
    def.parts.blade.width = 0.1f;
    def.parts.blade.thickness = 0.02f;
    def.parts.blade.bevel = 0.005f;
    def.parts.blade.curvature = 0.0f;

    def.parts.guard.style = GuardStyle::CROSS;
    def.parts.guard.width = 0.3f;
    def.parts.guard.thickness = 0.04f;

    def.parts.hilt.length = 0.2f;
    def.parts.hilt.radius = 0.03f;

    def.parts.pommel.style = PommelStyle::BALL;
    def.parts.pommel.radius = 0.035f;

    MaterialDefinition bladeMaterial;
    bladeMaterial.shader = ShaderType::PBR_METAL;
    bladeMaterial.textures["albedo"] = "textures/metal_alb.png";
    bladeMaterial.textures["normal"] = "textures/metal_nrm.png";
    def.materials["blade"] = bladeMaterial;

    MaterialDefinition guardMaterial;
    guardMaterial.shader = ShaderType::PBR_LEATHER;
    guardMaterial.textures["albedo"] = "textures/leather_alb.png";
    def.materials["guard"] = guardMaterial;

    def.animations["draw"] = "animations/longsword_draw.anim";
    def.animations["swing"] = "animations/longsword_swing.anim";

    def.physics.collisionType = CollisionType::CONVEX_HULL;

    WeaponVariant highVariant;
    highVariant.quality = QualityLevel::HIGH;
    highVariant.lodReduction = 0.0f;
    def.variants.push_back(highVariant);

    WeaponVariant mediumVariant;
    mediumVariant.quality = QualityLevel::MEDIUM;
    mediumVariant.lodReduction = 0.5f;
    def.variants.push_back(mediumVariant);

    WeaponVariant lowVariant;
    lowVariant.quality = QualityLevel::LOW;
    lowVariant.lodReduction = 0.8f;
    def.variants.push_back(lowVariant);
    return def;
}

} // namespace

// WeaponGen Implementation
WeaponGen::WeaponGen()
    : m_gpuAccelerationEnabled(false)
    , m_processingQuality(1)
    , m_lodReduction(DEFAULT_LOD_REDUCTION)
    , m_enablePhysics(true)
    , m_maxProcessingThreads(4)
    , m_lastError("") {

    // Initialize with default settings
    m_enableHotReload = true;
    m_enableCaching = true;
    m_enableParallelProcessing = true;

    // Initialize weapon part generators
    initializeWeaponGenerators();
}

WeaponGen::~WeaponGen() = default;

AudioBundle WeaponGen::process(const WeaponParams& params) {
    try {
        AudioBundle bundle;
        bundle.meta.id = params.id + "_" + std::to_string(std::chrono::system_clock::now().time_since_epoch().count());
        bundle.meta.duration = 0.0f;
        bundle.meta.loop = false;
        bundle.creationTime = std::chrono::system_clock::now();

        // Load weapon definition if provided
        WeaponDefinition weaponDef;
        if (!params.weaponDefinitionPath.empty()) {
            weaponDef = loadWeaponDefinition(params.weaponDefinitionPath);
        } else {
            weaponDef = createDefaultWeaponDefinition(params);
        }

        // Process weapon pipeline
        WeaponResult result = processWeaponPipeline(weaponDef, params);

        // The bundle carries the weapon's primary sound (the swing)
        if (!result.audioAssets.empty()) {
            const auto& audio = result.audioAssets[0];
            bundle.buffer = audio.audioData;
            bundle.meta.duration = static_cast<float>(audio.audioData.size()) /
                                   static_cast<float>(std::max(1u, audio.sampleRate * audio.numChannels));
        }

        // Calculate quality metrics
        if (!bundle.buffer.empty()) {
            bundle.quality.peakAmplitude = calculatePeakAmplitude(bundle.buffer);
            bundle.quality.rmsAmplitude = calculateRMSAmplitude(bundle.buffer);
            bundle.quality.dynamicRange = calculateDynamicRange(bundle.buffer);
            bundle.quality.signalToNoiseRatio = calculateSignalToNoiseRatio(bundle.buffer);
            bundle.meta.quality = bundle.quality;
        }

        return bundle;

    } catch (const std::exception& e) {
        m_lastError = e.what();
        throw;
    }
}

// Weapon Definition Loading
WeaponDefinition WeaponGen::loadWeaponDefinition(const std::string& filePath) {
    // Start from the built-in longsword so a definition file only needs to override what differs
    WeaponDefinition def = longswordTemplate();

    std::ifstream file(filePath);
    if (!file.is_open()) {
        m_lastError = "Weapon definition not found: " + filePath;
        Log::warn("WeaponGen", "{} (using built-in longsword)", m_lastError);
        return def;
    }
    Json j = Json::parse(file, nullptr, false);
    if (j.is_discarded() || !j.is_object()) {
        m_lastError = "Invalid weapon definition JSON: " + filePath;
        Log::error("WeaponGen", "{}", m_lastError);
        return def;
    }
    try {
        definitionFromJson(j, def);
    } catch (const Json::exception& e) {
        m_lastError = std::string("Weapon definition error in ") + filePath + ": " + e.what();
        Log::error("WeaponGen", "{}", m_lastError);
    }
    return def;
}

WeaponDefinition WeaponGen::createDefaultWeaponDefinition(const WeaponParams& params) {
    WeaponDefinition def;
    def.name = params.id.empty() ? "default_weapon" : params.id;
    def.type = params.weaponType;
    def.description = "Default weapon";

    // Create basic parts
    BladePart bladePart;
    bladePart.shape = params.bladeShape;
    bladePart.length = params.bladeLength;
    bladePart.width = params.bladeWidth;
    bladePart.thickness = 0.02f;
    bladePart.bevel = 0.005f;
    bladePart.curvature = params.bladeShape == BladeShape::CURVED ? 0.15f : 0.0f;
    def.parts.blade = bladePart;

    // Add default material
    MaterialDefinition defaultMaterial;
    defaultMaterial.shader = ShaderType::PBR_METAL;
    def.materials["default"] = defaultMaterial;

    // Default LOD chain
    def.variants = {WeaponVariant{QualityLevel::HIGH, 0.0f, {}},
                    WeaponVariant{QualityLevel::MEDIUM, 0.5f, {}},
                    WeaponVariant{QualityLevel::LOW, 0.8f, {}}};
    return def;
}

bool WeaponGen::saveWeaponDefinition(const WeaponDefinition& def, const std::string& filePath) {
    std::error_code ec;
    const std::filesystem::path path(filePath);
    if (path.has_parent_path()) std::filesystem::create_directories(path.parent_path(), ec);
    std::ofstream file(filePath);
    if (!file.is_open()) {
        m_lastError = "Cannot write weapon definition: " + filePath;
        Log::error("WeaponGen", "{}", m_lastError);
        return false;
    }
    file << definitionToJson(def).dump(2);
    return static_cast<bool>(file);
}

// Weapon Pipeline Processing
WeaponResult WeaponGen::processWeaponPipeline(const WeaponDefinition& weaponDef, const WeaponParams& params) {
    WeaponResult result;
    result.processingTime = std::chrono::system_clock::now();

    // Step 1: Generate weapon parts
    std::vector<ProcessedPart> processedParts = generateWeaponParts(weaponDef);

    // Step 2: Assemble weapon mesh
    WeaponMesh assembledMesh = assembleWeaponMesh(processedParts, weaponDef);

    // Step 3: Generate LOD variants
    std::vector<LODMesh> lodMeshes = generateLODVariants(assembledMesh, weaponDef.variants);

    // Step 4: Process materials and textures
    std::vector<ProcessedMaterial> processedMaterials = processMaterials(weaponDef.materials);
    for (const auto& material : processedMaterials) {
        for (const auto& [type, texture] : material.textures) {
            auto err = texture.metadata.find("error");
            if (err != texture.metadata.end()) result.warnings.push_back(err->second);
        }
    }

    // Step 5: Generate physics colliders
    PhysicsCollider collider = generatePhysicsCollider(assembledMesh, weaponDef.physics);

    // Step 6: Process animations
    std::vector<ProcessedAnimation> animations = processAnimations(weaponDef.animations);
    for (const auto& animation : animations) {
        auto err = animation.metadata.find("error");
        if (err != animation.metadata.end()) result.warnings.push_back(err->second);
    }

    // Step 7: Synthesize weapon audio
    result.audioAssets.push_back(generateSwingSound(weaponDef, assembledMesh, params));

    // Step 8: Create weapon pack
    result.weaponPack = createWeaponPack(weaponDef, assembledMesh, lodMeshes, processedMaterials, collider, animations);

    // Step 9: Categorize assets by type
    categorizeAssets(processedParts, lodMeshes, processedMaterials, animations, result);

    result.processedParts = processedParts;
    result.assembledMesh = assembledMesh;
    result.lodMeshes = lodMeshes;
    result.materials = processedMaterials;
    result.collider = collider;
    result.animations = animations;
    result.weaponDef = weaponDef;
    result.success = assembledMesh.vertexCount > 0;
    if (!result.success) result.errorMessage = "Weapon produced no geometry";

    return result;
}

// Weapon Generator Initialization
void WeaponGen::initializeWeaponGenerators() {
    // Initialize part generators
    m_bladeGenerator = std::make_unique<BladeGenerator>();
    m_guardGenerator = std::make_unique<GuardGenerator>();
    m_hiltGenerator = std::make_unique<HiltGenerator>();
    m_pommelGenerator = std::make_unique<PommelGenerator>();

    // Initialize mesh processors
    m_meshAssembler = std::make_unique<MeshAssembler>();
    m_lodGenerator = std::make_unique<LODGenerator>();
    m_colliderGenerator = std::make_unique<ColliderGenerator>();

    // Initialize material processors
    m_materialProcessor = std::make_unique<MaterialProcessor>();
    m_textureProcessor = std::make_unique<TextureProcessor>();

    // Initialize animation processors
    m_animationProcessor = std::make_unique<AnimationProcessor>();
}

// Weapon Part Generation
std::vector<ProcessedPart> WeaponGen::generateWeaponParts(const WeaponDefinition& weaponDef) {
    std::vector<ProcessedPart> parts;

    // Generate blade
    if (weaponDef.parts.blade.length > 0.0f) {
        ProcessedPart bladePart = m_bladeGenerator->generate(weaponDef.parts.blade);
        bladePart.id = "blade";
        bladePart.type = PartType::BLADE;
        parts.push_back(bladePart);
    }

    // Generate guard
    if (weaponDef.parts.guard.width > 0.0f && weaponDef.parts.guard.style != GuardStyle::NONE) {
        ProcessedPart guardPart = m_guardGenerator->generate(weaponDef.parts.guard);
        guardPart.id = "guard";
        guardPart.type = PartType::GUARD;
        parts.push_back(guardPart);
    }

    // Generate hilt
    if (weaponDef.parts.hilt.length > 0.0f) {
        ProcessedPart hiltPart = m_hiltGenerator->generate(weaponDef.parts.hilt);
        hiltPart.id = "hilt";
        hiltPart.type = PartType::HILT;
        parts.push_back(hiltPart);
    }

    // Generate pommel
    if (weaponDef.parts.pommel.radius > 0.0f && weaponDef.parts.pommel.style != PommelStyle::NONE) {
        ProcessedPart pommelPart = m_pommelGenerator->generate(weaponDef.parts.pommel);
        pommelPart.id = "pommel";
        pommelPart.type = PartType::POMMEL;
        parts.push_back(pommelPart);
    }

    return parts;
}

// Mesh Assembly
WeaponMesh WeaponGen::assembleWeaponMesh(const std::vector<ProcessedPart>& parts, const WeaponDefinition& weaponDef) {
    WeaponMesh assembledMesh;

    // Assemble parts into unified mesh
    assembledMesh = m_meshAssembler->assemble(parts);

    // Compute UVs, normals, tangents
    assembledMesh = computeMeshAttributes(assembledMesh);

    // Generate vertex colors for ornament maps
    assembledMesh = generateVertexColors(assembledMesh, weaponDef);

    assembledMesh.metadata["weapon"] = weaponDef.name;
    return assembledMesh;
}

// LOD Generation
std::vector<LODMesh> WeaponGen::generateLODVariants(const WeaponMesh& baseMesh, const std::vector<WeaponVariant>& variants) {
    std::vector<LODMesh> lodMeshes;

    for (const auto& variant : variants) {
        if (lodMeshes.size() >= MAX_LOD_LEVELS) break;
        // Generate LOD mesh
        LODMesh lodMesh = m_lodGenerator->generate(baseMesh, variant.lodReduction);
        lodMesh.quality = variant.quality;
        lodMesh.lodReduction = variant.lodReduction;
        lodMesh.parameters = variant.parameters;
        lodMeshes.push_back(lodMesh);
    }

    return lodMeshes;
}

// Material Processing
std::vector<ProcessedMaterial> WeaponGen::processMaterials(const std::map<std::string, MaterialDefinition>& materials) {
    std::vector<ProcessedMaterial> processedMaterials;

    for (const auto& [name, materialDef] : materials) {
        ProcessedMaterial processedMaterial = m_materialProcessor->process(materialDef);
        processedMaterial.id = name;
        processedMaterials.push_back(processedMaterial);
    }

    return processedMaterials;
}

// Physics Collider Generation
PhysicsCollider WeaponGen::generatePhysicsCollider(const WeaponMesh& mesh, const PhysicsSettings& physics) {
    PhysicsCollider collider;

    const CollisionType type = m_enablePhysics ? physics.collisionType : CollisionType::NONE;
    switch (type) {
        case CollisionType::CONVEX_HULL:
            collider = m_colliderGenerator->generateConvexHull(mesh);
            break;
        case CollisionType::PRIMITIVE:
            collider = m_colliderGenerator->generatePrimitive(mesh);
            break;
        case CollisionType::MESH:
            collider = m_colliderGenerator->generateMeshCollider(mesh);
            break;
        case CollisionType::NONE:
            collider.type = CollisionType::NONE;
            collider.boundingBox = mesh.boundingBox;
            break;
    }

    collider.mass = physics.mass;
    collider.friction = physics.friction;
    collider.restitution = physics.restitution;
    for (const auto& [k, v] : physics.parameters) collider.parameters[k] = v;
    return collider;
}

// Animation Processing
std::vector<ProcessedAnimation> WeaponGen::processAnimations(const std::map<std::string, std::string>& animations) {
    std::vector<ProcessedAnimation> processedAnimations;

    for (const auto& [name, path] : animations) {
        ProcessedAnimation animation = m_animationProcessor->process(path);
        animation.id = name;
        processedAnimations.push_back(animation);
    }

    return processedAnimations;
}

WeaponAudioAsset WeaponGen::generateSwingSound(const WeaponDefinition& weaponDef, const WeaponMesh& mesh,
                                               const WeaponParams& params) {
    WeaponAudioAsset asset;
    asset.id = weaponDef.name + "_swing";
    asset.sampleRate = std::max(8000u, params.sampleRate);
    asset.numChannels = std::clamp(params.numChannels, 1u, 2u);

    // Longer / heavier weapons swing slower and sound lower
    const float reach = std::max(0.1f, mesh.boundingBox.second.y - mesh.boundingBox.first.y);
    const float mass = std::max(0.1f, weaponDef.physics.mass);
    const float duration = 0.25f + 0.3f * reach;
    const float cutoffHz = std::clamp(2400.0f / std::sqrt(mass * reach), 300.0f, 6000.0f);

    const size_t frames = static_cast<size_t>(duration * static_cast<float>(asset.sampleRate));
    asset.audioData.resize(frames * asset.numChannels);

    std::mt19937 rng(params.seed);
    std::uniform_real_distribution<float> noise(-1.0f, 1.0f);
    // Two-pole low-pass over white noise whose cutoff sweeps up then down (doppler-like whoosh)
    float lp1 = 0.0f, lp2 = 0.0f;
    for (size_t i = 0; i < frames; ++i) {
        const float t = static_cast<float>(i) / static_cast<float>(frames);
        const float sweep = 0.4f + 0.6f * std::sin(PI * t);
        const float fc = cutoffHz * sweep;
        const float alpha = 1.0f - std::exp(-TWO_PI * fc / static_cast<float>(asset.sampleRate));
        lp1 += alpha * (noise(rng) - lp1);
        lp2 += alpha * (lp1 - lp2);
        const float envelope = std::pow(std::sin(PI * t), 1.5f);
        const float sample = std::clamp(lp2 * envelope * 2.5f, -1.0f, 1.0f);
        for (uint32_t c = 0; c < asset.numChannels; ++c) {
            // gentle stereo pan across the swing
            const float pan = asset.numChannels == 2 ? (c == 0 ? 1.0f - 0.5f * t : 0.5f + 0.5f * t) : 1.0f;
            asset.audioData[i * asset.numChannels + c] = sample * pan;
        }
    }
    return asset;
}

// Weapon Pack Creation
WeaponPack WeaponGen::createWeaponPack(const WeaponDefinition& weaponDef,
                                      const WeaponMesh& assembledMesh,
                                      const std::vector<LODMesh>& lodMeshes,
                                      const std::vector<ProcessedMaterial>& materials,
                                      const PhysicsCollider& collider,
                                      const std::vector<ProcessedAnimation>& animations) {
    WeaponPack pack;

    pack.name = weaponDef.name;
    pack.type = weaponDef.type;
    pack.version = "1.0.0";
    pack.assembledMesh = assembledMesh;
    pack.lodMeshes = lodMeshes;
    pack.materials = materials;
    pack.collider = collider;
    pack.animations = animations;
    pack.weaponDef = weaponDef;

    // Calculate total size
    pack.totalSize = calculatePackSize(pack);
    pack.creationTime = std::chrono::system_clock::now();

    // Generate pack checksum (the archive itself is written on demand by writeWeaponPack)
    pack.checksum = calculatePackChecksum(pack);

    return pack;
}

bool WeaponGen::writeWeaponPack(WeaponPack& pack, const std::string& filePath) {
    std::error_code ec;
    const std::filesystem::path path(filePath);
    if (path.has_parent_path()) std::filesystem::create_directories(path.parent_path(), ec);
    std::ofstream out(filePath, std::ios::binary);
    if (!out.is_open()) {
        m_lastError = "Cannot write weapon pack: " + filePath;
        Log::error("WeaponGen", "{}", m_lastError);
        return false;
    }

    // Fixed-size header
    char header[PACK_HEADER_SIZE] = {};
    std::memcpy(header, "WPNPACK1", 8);
    const uint32_t lodCount = static_cast<uint32_t>(pack.lodMeshes.size());
    const uint32_t materialCount = static_cast<uint32_t>(pack.materials.size());
    const uint32_t animationCount = static_cast<uint32_t>(pack.animations.size());
    const uint64_t totalSize = pack.totalSize;
    std::memcpy(header + 8, &lodCount, 4);
    std::memcpy(header + 12, &materialCount, 4);
    std::memcpy(header + 16, &animationCount, 4);
    std::memcpy(header + 20, &totalSize, 8);
    std::memcpy(header + 28, pack.checksum.data(), std::min<size_t>(pack.checksum.size(), 32));
    out.write(header, sizeof(header));

    writeString(out, pack.name);
    writeString(out, pack.version);
    writeMesh(out, pack.assembledMesh);
    for (const auto& lod : pack.lodMeshes) {
        writePod(out, static_cast<uint32_t>(lod.quality));
        writePod(out, lod.lodReduction);
        writeMesh(out, lod.mesh);
    }
    writePod(out, static_cast<uint32_t>(pack.collider.type));
    writeBlob(out, pack.collider.vertices.data(), pack.collider.vertices.size() * sizeof(glm::vec3));
    writeBlob(out, pack.collider.indices.data(), pack.collider.indices.size() * sizeof(uint32_t));
    for (const auto& material : pack.materials) {
        writeString(out, material.id);
        writePod(out, static_cast<uint32_t>(material.shaderType));
        writePod(out, static_cast<uint32_t>(material.textures.size()));
        for (const auto& [type, texture] : material.textures) {
            writeString(out, type);
            writePod(out, texture.width);
            writePod(out, texture.height);
            writePod(out, texture.mipLevels);
            writeBlob(out, texture.data.data(), texture.data.size());
        }
    }
    for (const auto& animation : pack.animations) {
        writeString(out, animation.id);
        writePod(out, animation.duration);
        writePod(out, animation.frameRate);
        writePod(out, animation.frameCount);
        writeBlob(out, animation.data.data(), animation.data.size());
    }
    writeString(out, definitionToJson(pack.weaponDef).dump());

    if (!out) {
        m_lastError = "Write failed for weapon pack: " + filePath;
        return false;
    }
    pack.filePath = filePath;
    return true;
}

// Asset Categorization
void WeaponGen::categorizeAssets(const std::vector<ProcessedPart>& parts,
                                const std::vector<LODMesh>& lodMeshes,
                                const std::vector<ProcessedMaterial>& materials,
                                const std::vector<ProcessedAnimation>& animations,
                                WeaponResult& result) {
    // Categorize parts
    for (const auto& part : parts) {
        switch (part.type) {
            case PartType::BLADE:
                result.bladeParts.push_back(part);
                break;
            case PartType::GUARD:
                result.guardParts.push_back(part);
                break;
            case PartType::HILT:
            case PartType::GRIP:
                result.hiltParts.push_back(part);
                break;
            case PartType::POMMEL:
                result.pommelParts.push_back(part);
                break;
            case PartType::ORNAMENT:
                result.warnings.push_back("Ornament part '" + part.id + "' is not categorized");
                break;
        }
    }

    // Categorize LOD meshes
    for (const auto& lodMesh : lodMeshes) {
        switch (lodMesh.quality) {
            case QualityLevel::ULTRA:
            case QualityLevel::HIGH:
                result.highQualityMeshes.push_back(lodMesh);
                break;
            case QualityLevel::MEDIUM:
                result.mediumQualityMeshes.push_back(lodMesh);
                break;
            case QualityLevel::LOW:
                result.lowQualityMeshes.push_back(lodMesh);
                break;
        }
    }

    // Categorize materials
    for (const auto& material : materials) {
        switch (material.shaderType) {
            case ShaderType::PBR_METAL:
                result.metalMaterials.push_back(material);
                break;
            case ShaderType::PBR_LEATHER:
                result.leatherMaterials.push_back(material);
                break;
            case ShaderType::PBR_WOOD:
                result.woodMaterials.push_back(material);
                break;
            default:
                result.otherMaterials.push_back(material);
                break;
        }
    }

    // Categorize animations
    for (const auto& animation : animations) {
        if (animation.id.find("draw") != std::string::npos) {
            result.drawAnimations.push_back(animation);
        } else if (animation.id.find("swing") != std::string::npos) {
            result.swingAnimations.push_back(animation);
        } else if (animation.id.find("sheath") != std::string::npos) {
            result.sheathAnimations.push_back(animation);
        } else {
            result.otherAnimations.push_back(animation);
        }
    }
}

// Mesh Attribute Computation
WeaponMesh WeaponGen::computeMeshAttributes(const WeaponMesh& mesh) {
    WeaponMesh processedMesh = mesh;

    // UVs first: tangents are derived from them
    processedMesh = generateUVs(processedMesh);

    // Compute normals
    processedMesh = computeNormals(processedMesh);

    // Compute tangents
    processedMesh = computeTangents(processedMesh);

    return processedMesh;
}

WeaponMesh WeaponGen::computeNormals(const WeaponMesh& mesh) {
    // Area-weighted face normals accumulated per vertex
    WeaponMesh out = mesh;
    std::vector<glm::vec3> acc(out.vertices.size(), glm::vec3(0.0f));
    for (size_t i = 0; i + 2 < out.indices.size(); i += 3) {
        const uint32_t a = out.indices[i], b = out.indices[i + 1], c = out.indices[i + 2];
        const glm::vec3 n = glm::cross(out.vertices[b].position - out.vertices[a].position,
                                       out.vertices[c].position - out.vertices[a].position);
        acc[a] += n;
        acc[b] += n;
        acc[c] += n;
    }
    for (size_t i = 0; i < out.vertices.size(); ++i) {
        const float len = glm::length(acc[i]);
        out.vertices[i].normal = len > 1e-12f ? acc[i] / len : glm::vec3(0.0f, 1.0f, 0.0f);
    }
    return out;
}

WeaponMesh WeaponGen::computeTangents(const WeaponMesh& mesh) {
    // Per-triangle UV-space tangents, accumulated and Gram-Schmidt orthogonalized
    WeaponMesh out = mesh;
    std::vector<glm::vec3> acc(out.vertices.size(), glm::vec3(0.0f));
    for (size_t i = 0; i + 2 < out.indices.size(); i += 3) {
        const uint32_t ia = out.indices[i], ib = out.indices[i + 1], ic = out.indices[i + 2];
        const Vertex &a = out.vertices[ia], &b = out.vertices[ib], &c = out.vertices[ic];
        const glm::vec3 e1 = b.position - a.position, e2 = c.position - a.position;
        const glm::vec2 d1 = b.uv - a.uv, d2 = c.uv - a.uv;
        const float det = d1.x * d2.y - d2.x * d1.y;
        if (std::abs(det) < 1e-12f) continue;
        const glm::vec3 t = (e1 * d2.y - e2 * d1.y) / det;
        acc[ia] += t;
        acc[ib] += t;
        acc[ic] += t;
    }
    for (size_t i = 0; i < out.vertices.size(); ++i) {
        const glm::vec3 n = out.vertices[i].normal;
        glm::vec3 t = acc[i] - n * glm::dot(n, acc[i]);
        if (glm::length(t) < 1e-9f) {
            // fall back to any vector perpendicular to the normal
            t = std::abs(n.x) < 0.9f ? glm::cross(n, glm::vec3(1, 0, 0)) : glm::cross(n, glm::vec3(0, 1, 0));
        }
        out.vertices[i].tangent = glm::normalize(t);
    }
    return out;
}

WeaponMesh WeaponGen::generateUVs(const WeaponMesh& mesh) {
    // Cylindrical projection around the weapon's long (Y) axis
    WeaponMesh out = mesh;
    finalizeMesh(out);
    const float minY = out.boundingBox.first.y;
    const float height = std::max(1e-6f, out.boundingBox.second.y - minY);
    for (auto& v : out.vertices) {
        const float angle = std::atan2(v.position.z, v.position.x);
        v.uv = glm::vec2(angle / TWO_PI + 0.5f, (v.position.y - minY) / height);
    }
    return out;
}

WeaponMesh WeaponGen::generateVertexColors(const WeaponMesh& mesh, const WeaponDefinition& weaponDef) {
    // Ornament map packed in vertex colors:
    //  r = height along the weapon, g = edge mask (distance from the axis),
    //  b = ornament band pattern along the blade, a = 1
    WeaponMesh out = mesh;
    finalizeMesh(out);
    const float minY = out.boundingBox.first.y;
    const float height = std::max(1e-6f, out.boundingBox.second.y - minY);
    float maxRadius = 1e-6f;
    for (const auto& v : out.vertices) maxRadius = std::max(maxRadius, glm::length(glm::vec2(v.position.x, v.position.z)));
    const float frequency = param(weaponDef.parts.blade.parameters, "ornamentFrequency", 6.0f);
    for (auto& v : out.vertices) {
        const float h = (v.position.y - minY) / height;
        const float edge = glm::length(glm::vec2(v.position.x, v.position.z)) / maxRadius;
        const float band = v.position.y > 0.0f ? 0.5f + 0.5f * std::sin(TWO_PI * frequency * h) : 0.0f;
        v.color = glm::vec4(h, edge, band, 1.0f);
    }
    return out;
}

// Size and Checksum Calculation
size_t WeaponGen::calculatePackSize(const WeaponPack& pack) {
    size_t totalSize = PACK_HEADER_SIZE;

    totalSize += pack.assembledMesh.vertices.size() * sizeof(Vertex);
    totalSize += pack.assembledMesh.indices.size() * sizeof(uint32_t);

    // Add mesh sizes
    for (const auto& lodMesh : pack.lodMeshes) {
        totalSize += lodMesh.mesh.vertexCount * sizeof(Vertex);
        totalSize += lodMesh.mesh.indexCount * sizeof(uint32_t);
    }

    totalSize += pack.collider.vertices.size() * sizeof(glm::vec3);
    totalSize += pack.collider.indices.size() * sizeof(uint32_t);

    // Add material sizes
    for (const auto& material : pack.materials) {
        for (const auto& [type, texture] : material.textures) {
            totalSize += texture.data.size();
        }
    }

    // Add animation sizes
    for (const auto& animation : pack.animations) {
        totalSize += animation.data.size();
    }

    return totalSize;
}

std::string WeaponGen::calculatePackChecksum(const WeaponPack& pack) {
    // 64-bit FNV-1a over the pack's identity and payload
    uint64_t h = 14695981039346656037ULL;
    h = fnv1a(h, pack.name.data(), pack.name.size());
    h = fnv1a(h, pack.version.data(), pack.version.size());
    h = hashMesh(h, pack.assembledMesh);
    for (const auto& lod : pack.lodMeshes) h = hashMesh(h, lod.mesh);
    for (const auto& material : pack.materials) {
        h = fnv1a(h, material.id.data(), material.id.size());
        for (const auto& [type, texture] : material.textures) {
            h = fnv1a(h, type.data(), type.size());
            if (!texture.data.empty()) h = fnv1a(h, texture.data.data(), texture.data.size());
        }
    }
    for (const auto& animation : pack.animations) {
        if (!animation.data.empty()) h = fnv1a(h, animation.data.data(), animation.data.size());
    }
    std::ostringstream oss;
    oss << std::hex << std::setw(16) << std::setfill('0') << h;
    return oss.str();
}

// Part Generator Implementations
ProcessedPart WeaponGen::BladeGenerator::generate(const BladePart& bladePart) {
    ProcessedPart part;
    part.id = "blade";
    part.type = PartType::BLADE;
    part.parameters = bladePart.parameters;

    // Diamond cross-section lofted from the base (y = 0) to the tip (y = length).
    const int segments = std::max(2, static_cast<int>(param(bladePart.parameters, "segments", 16.0f)));
    const float halfWidth = bladePart.width * 0.5f;
    const float halfThick = bladePart.thickness * 0.5f;
    const int serrations = static_cast<int>(param(bladePart.parameters, "serrationCount", 12.0f));
    const float waves = param(bladePart.parameters, "waveCount", 4.0f);
    const float tipStart = param(bladePart.parameters, "tipStart", 0.85f);

    std::vector<std::vector<glm::vec3>> rings;
    for (int s = 0; s < segments; ++s) {
        const float t = static_cast<float>(s) / static_cast<float>(segments);
        const float y = t * bladePart.length;
        float w = halfWidth;
        if (t > tipStart) w *= (1.0f - t) / (1.0f - tipStart);                 // taper into the tip
        float xOffset = bladePart.curvature * t * t * bladePart.length;      // curved blades bend along X
        float leftEdge = w, rightEdge = w;
        switch (bladePart.shape) {
            case BladeShape::WAVY:
                xOffset += 0.25f * halfWidth * std::sin(TWO_PI * waves * t);
                break;
            case BladeShape::SERRATED:
                if (serrations > 0 && (s % 2) == 1) { leftEdge *= 0.8f; rightEdge *= 0.8f; }
                break;
            case BladeShape::SINGLE_EDGED:
                rightEdge = std::max(halfThick, w * 0.35f);                   // flat spine on one side
                break;
            default:
                break;
        }
        const float edgeThick = std::max(0.0f, bladePart.bevel);            // bevel keeps a small edge flat
        rings.push_back({
            glm::vec3(xOffset - leftEdge, y, -edgeThick * 0.5f),
            glm::vec3(xOffset, y, -halfThick),
            glm::vec3(xOffset + rightEdge, y, -edgeThick * 0.5f),
            glm::vec3(xOffset + rightEdge, y, edgeThick * 0.5f),
            glm::vec3(xOffset, y, halfThick),
            glm::vec3(xOffset - leftEdge, y, edgeThick * 0.5f),
        });
    }
    part.mesh = loftRings(rings, true, false);
    // close the tip
    const float tipX = bladePart.curvature * bladePart.length;
    const uint32_t tip = addVertex(part.mesh, glm::vec3(tipX, bladePart.length, 0.0f));
    const uint32_t lastRing = static_cast<uint32_t>((rings.size() - 1) * rings.back().size());
    const uint32_t n = static_cast<uint32_t>(rings.back().size());
    for (uint32_t i = 0; i < n; ++i) addTri(part.mesh, lastRing + i, lastRing + (i + 1) % n, tip);

    finalizeMesh(part.mesh);
    return part;
}

ProcessedPart WeaponGen::GuardGenerator::generate(const GuardPart& guardPart) {
    ProcessedPart part;
    part.id = "guard";
    part.type = PartType::GUARD;
    part.parameters = guardPart.parameters;

    const float w = guardPart.width;
    const float t = guardPart.thickness;
    switch (guardPart.style) {
        case GuardStyle::CROSS:
            part.mesh = box(glm::vec3(0.0f), glm::vec3(w, t, t * 1.5f));
            break;
        case GuardStyle::QUILLON: {
            // bar whose arms curve towards the blade
            // Circular cross-sections (in the YZ plane) swept along X; the arms rise quadratically.
            std::vector<std::vector<glm::vec3>> rings;
            const int segs = 12;
            for (int i = 0; i <= segs; ++i) {
                const float u = static_cast<float>(i) / segs * 2.0f - 1.0f;     // -1..1 across
                const glm::vec3 center(u * w * 0.5f, 1.2f * t * u * u, 0.0f);
                std::vector<glm::vec3> ring;
                for (int k = 0; k < 8; ++k) {
                    const float a = TWO_PI * static_cast<float>(k) / 8.0f;
                    ring.push_back(center + glm::vec3(0.0f, std::cos(a) * t * 0.5f, std::sin(a) * t * 0.5f));
                }
                rings.push_back(ring);
            }
            part.mesh = loftRings(rings, true, true);
            break;
        }
        case GuardStyle::RING: {
            // torus around the blade axis
            const float R = w * 0.5f, r = t * 0.5f;
            const int major = 24, minor = 8;
            std::vector<std::vector<glm::vec3>> rings;
            for (int i = 0; i <= major; ++i) {
                const float a = TWO_PI * static_cast<float>(i % major) / major;
                const glm::vec3 dir(std::cos(a), 0.0f, std::sin(a));
                std::vector<glm::vec3> ring;
                for (int k = 0; k < minor; ++k) {
                    const float b = TWO_PI * static_cast<float>(k) / minor;
                    ring.push_back(dir * (R + r * std::cos(b)) + glm::vec3(0.0f, r * std::sin(b), 0.0f));
                }
                rings.push_back(ring);
            }
            part.mesh = loftRings(rings, false, false);
            break;
        }
        case GuardStyle::BASKET: {
            // open hemispherical shell opening towards the hilt (-Y)
            std::vector<std::vector<glm::vec3>> rings;
            const int stacks = 6;
            for (int s = 0; s <= stacks; ++s) {
                const float phi = 0.5f * PI * static_cast<float>(s) / stacks;
                rings.push_back(circleRing(-std::sin(phi) * w * 0.5f + t * 0.5f, std::cos(phi) * w * 0.5f + 1e-4f,
                                           std::cos(phi) * w * 0.5f + 1e-4f, 16));
            }
            part.mesh = loftRings(rings, true, false);
            break;
        }
        case GuardStyle::NONE:
            break;
    }
    finalizeMesh(part.mesh);
    return part;
}

ProcessedPart WeaponGen::HiltGenerator::generate(const HiltPart& hiltPart) {
    ProcessedPart part;
    part.id = "hilt";
    part.type = PartType::HILT;
    part.parameters = hiltPart.parameters;

    // Grip cylinder from y = 0 down to -length, with optional wrap ridges
    const int segments = 12;
    const int rows = std::max(2, static_cast<int>(param(hiltPart.parameters, "wraps", 8.0f)) * 2);
    std::vector<std::vector<glm::vec3>> rings;
    for (int r = 0; r <= rows; ++r) {
        const float y = -hiltPart.length * static_cast<float>(r) / rows;
        const float radius = hiltPart.radius * ((r % 2) ? 0.92f : 1.0f);
        rings.push_back(circleRing(y, radius, radius, segments));
    }
    part.mesh = loftRings(rings, true, true);
    finalizeMesh(part.mesh);
    return part;
}

ProcessedPart WeaponGen::PommelGenerator::generate(const PommelPart& pommelPart) {
    ProcessedPart part;
    part.id = "pommel";
    part.type = PartType::POMMEL;
    part.parameters = pommelPart.parameters;

    const float r = pommelPart.radius;
    switch (pommelPart.style) {
        case PommelStyle::BALL:
            part.mesh = ellipsoid(r, r, r, 16, 10);
            break;
        case PommelStyle::WHEEL: {
            std::vector<std::vector<glm::vec3>> rings = {circleRing(-r * 0.3f, r, r, 20), circleRing(r * 0.3f, r, r, 20)};
            // wheel disc lies in the XY plane: rotate rings around X by 90 degrees
            for (auto& ring : rings)
                for (auto& p : ring) p = glm::vec3(p.x, p.z, p.y);
            part.mesh = loftRings(rings, true, true);
            break;
        }
        case PommelStyle::TEARDROP:
            part.mesh = ellipsoid(r, r * 1.4f, r, 16, 10, &teardropProfile);
            break;
        case PommelStyle::BRAZIL_NUT:
            part.mesh = ellipsoid(r * 0.8f, r * 1.3f, r, 16, 12, &brazilNutProfile);
            break;
        case PommelStyle::NONE:
            break;
    }
    finalizeMesh(part.mesh);
    return part;
}

// Mesh Processor Implementations
WeaponMesh WeaponGen::MeshAssembler::assemble(const std::vector<ProcessedPart>& parts) {
    // Stack the parts along Y using their bounding boxes:
    // guard centred on the origin, blade above it, hilt below it, pommel below the hilt.
    WeaponMesh assembledMesh;
    const ProcessedPart *blade = nullptr, *guard = nullptr, *hilt = nullptr, *pommel = nullptr;
    std::vector<const ProcessedPart*> extras;
    for (const auto& part : parts) {
        switch (part.type) {
            case PartType::BLADE: blade = &part; break;
            case PartType::GUARD: guard = &part; break;
            case PartType::HILT:
            case PartType::GRIP: hilt = &part; break;
            case PartType::POMMEL: pommel = &part; break;
            default: extras.push_back(&part); break;
        }
    }

    float top = 0.0f, bottom = 0.0f;
    if (guard) {
        const auto& bb = guard->mesh.boundingBox;
        const float cy = (bb.first.y + bb.second.y) * 0.5f;
        appendMesh(assembledMesh, guard->mesh, glm::vec3(0.0f, -cy, 0.0f));
        top = bb.second.y - cy;
        bottom = bb.first.y - cy;
    }
    if (blade) {
        appendMesh(assembledMesh, blade->mesh, glm::vec3(0.0f, top - blade->mesh.boundingBox.first.y, 0.0f));
    }
    if (hilt) {
        const float offset = bottom - hilt->mesh.boundingBox.second.y;
        appendMesh(assembledMesh, hilt->mesh, glm::vec3(0.0f, offset, 0.0f));
        bottom = hilt->mesh.boundingBox.first.y + offset;
    }
    if (pommel) {
        appendMesh(assembledMesh, pommel->mesh, glm::vec3(0.0f, bottom - pommel->mesh.boundingBox.second.y, 0.0f));
    }
    for (const auto* extra : extras) appendMesh(assembledMesh, extra->mesh, glm::vec3(0.0f));

    finalizeMesh(assembledMesh);
    return assembledMesh;
}

LODMesh WeaponGen::LODGenerator::generate(const WeaponMesh& baseMesh, float reduction) {
    LODMesh lodMesh;
    lodMesh.lodReduction = reduction;

    reduction = std::clamp(reduction, 0.0f, 0.99f);
    if (reduction <= 0.0f || baseMesh.vertices.empty()) {
        lodMesh.mesh = baseMesh;
    } else {
        // Vertex clustering: snap vertices to a grid whose resolution shrinks with the reduction,
        // merge each cell into its average vertex and drop degenerate triangles.
        WeaponMesh base = baseMesh;
        finalizeMesh(base);
        const glm::vec3 extent = glm::max(base.boundingBox.second - base.boundingBox.first, glm::vec3(1e-6f));
        const float targetVerts = std::max(8.0f, static_cast<float>(base.vertices.size()) * (1.0f - reduction));
        // cells roughly proportional to the target vertex count, distributed by extent
        const float volume = extent.x * extent.y * extent.z;
        const float cell = std::cbrt(std::max(volume, 1e-12f) / targetVerts);
        const glm::ivec3 dims = glm::max(glm::ivec3(glm::ceil(extent / std::max(cell, 1e-6f))), glm::ivec3(1));

        std::unordered_map<int64_t, uint32_t> cellToVertex;
        std::vector<Vertex> merged;
        std::vector<float> weights;
        std::vector<uint32_t> remap(base.vertices.size());
        for (size_t i = 0; i < base.vertices.size(); ++i) {
            const glm::vec3 rel = (base.vertices[i].position - base.boundingBox.first) / extent;
            const glm::ivec3 c = glm::clamp(glm::ivec3(rel * glm::vec3(dims)), glm::ivec3(0), dims - 1);
            const int64_t key = (static_cast<int64_t>(c.x) * dims.y + c.y) * dims.z + c.z;
            auto it = cellToVertex.find(key);
            if (it == cellToVertex.end()) {
                it = cellToVertex.emplace(key, static_cast<uint32_t>(merged.size())).first;
                merged.push_back(base.vertices[i]);
                weights.push_back(1.0f);
            } else {
                Vertex& m = merged[it->second];
                const float w = weights[it->second];
                m.position = (m.position * w + base.vertices[i].position) / (w + 1.0f);
                m.uv = (m.uv * w + base.vertices[i].uv) / (w + 1.0f);
                m.color = (m.color * w + base.vertices[i].color) / (w + 1.0f);
                m.normal += base.vertices[i].normal;
                weights[it->second] = w + 1.0f;
            }
            remap[i] = it->second;
        }
        for (auto& v : merged) {
            const float len = glm::length(v.normal);
            v.normal = len > 1e-9f ? v.normal / len : glm::vec3(0, 1, 0);
        }
        lodMesh.mesh.vertices = std::move(merged);
        for (size_t i = 0; i + 2 < base.indices.size(); i += 3) {
            const uint32_t a = remap[base.indices[i]], b = remap[base.indices[i + 1]], c = remap[base.indices[i + 2]];
            if (a == b || b == c || a == c) continue;
            addTri(lodMesh.mesh, a, b, c);
        }
        lodMesh.mesh.metadata = base.metadata;
    }
    finalizeMesh(lodMesh.mesh);
    lodMesh.vertexCount = lodMesh.mesh.vertexCount;
    lodMesh.indexCount = lodMesh.mesh.indexCount;
    return lodMesh;
}

PhysicsCollider WeaponGen::ColliderGenerator::generateConvexHull(const WeaponMesh& mesh) {
    PhysicsCollider collider;
    collider.type = CollisionType::CONVEX_HULL;
    collider.boundingBox = mesh.boundingBox;

    std::vector<glm::vec3> points;
    points.reserve(mesh.vertices.size());
    for (const auto& v : mesh.vertices) points.push_back(v.position);
    const auto faces = convexHull(points);
    if (faces.empty()) {
        // Degenerate (flat/too few points): fall back to the bounding box
        return generatePrimitive(mesh);
    }

    // Compact the hull's vertex set
    std::unordered_map<uint32_t, uint32_t> remap;
    auto index = [&](uint32_t original) {
        auto it = remap.find(original);
        if (it != remap.end()) return it->second;
        const uint32_t id = static_cast<uint32_t>(collider.vertices.size());
        collider.vertices.push_back(points[original]);
        remap.emplace(original, id);
        return id;
    };
    for (const auto& f : faces) {
        collider.indices.push_back(index(f.a));
        collider.indices.push_back(index(f.b));
        collider.indices.push_back(index(f.c));
    }
    collider.parameters["hullVertexCount"] = static_cast<float>(collider.vertices.size());
    return collider;
}

PhysicsCollider WeaponGen::ColliderGenerator::generatePrimitive(const WeaponMesh& mesh) {
    // Capsule along the weapon's long axis, plus its box corners for debug drawing
    PhysicsCollider collider;
    collider.type = CollisionType::PRIMITIVE;
    collider.boundingBox = mesh.boundingBox;

    const glm::vec3 mn = mesh.boundingBox.first, mx = mesh.boundingBox.second;
    const glm::vec3 extent = mx - mn;
    const float radius = 0.5f * std::max(extent.x, extent.z);
    collider.parameters["shape"] = 1.0f;                       // 0 = box, 1 = capsule
    collider.parameters["radius"] = radius;
    collider.parameters["height"] = std::max(0.0f, extent.y - 2.0f * radius);
    collider.parameters["centerX"] = 0.5f * (mn.x + mx.x);
    collider.parameters["centerY"] = 0.5f * (mn.y + mx.y);
    collider.parameters["centerZ"] = 0.5f * (mn.z + mx.z);

    for (int i = 0; i < 8; ++i) {
        collider.vertices.push_back(glm::vec3((i & 1) ? mx.x : mn.x, (i & 2) ? mx.y : mn.y, (i & 4) ? mx.z : mn.z));
    }
    static const uint32_t boxIndices[36] = {0, 2, 1, 1, 2, 3, 4, 5, 6, 5, 7, 6, 0, 1, 4, 1, 5, 4,
                                            2, 6, 3, 3, 6, 7, 0, 4, 2, 2, 4, 6, 1, 3, 5, 3, 7, 5};
    collider.indices.assign(std::begin(boxIndices), std::end(boxIndices));
    return collider;
}

PhysicsCollider WeaponGen::ColliderGenerator::generateMeshCollider(const WeaponMesh& mesh) {
    PhysicsCollider collider;
    collider.type = CollisionType::MESH;
    collider.boundingBox = mesh.boundingBox;
    collider.vertices.reserve(mesh.vertices.size());
    for (const auto& v : mesh.vertices) collider.vertices.push_back(v.position);
    collider.indices = mesh.indices;
    return collider;
}

// Material Processor Implementations
ProcessedMaterial WeaponGen::MaterialProcessor::process(const MaterialDefinition& materialDef) {
    ProcessedMaterial material;
    material.shaderType = materialDef.shader;
    material.parameters = materialDef.parameters;

    TextureProcessor textures;
    for (const auto& [type, path] : materialDef.textures) {
        material.textures[type] = textures.process(path, type);
    }
    material.metadata["textureCount"] = std::to_string(material.textures.size());
    return material;
}

ProcessedTexture WeaponGen::TextureProcessor::process(const std::string& path, const std::string& type) {
    ProcessedTexture texture;
    texture.path = path;
    texture.type = type;

    // Load as RGBA8 and build a box-filtered mip chain
    int w = 0, h = 0, n = 0;
    stbi_uc* pixels = stbi_load(path.c_str(), &w, &h, &n, 4);
    if (!pixels) {
        texture.metadata["error"] = "Failed to load texture: " + path;
        return texture;
    }
    texture.width = static_cast<uint32_t>(w);
    texture.height = static_cast<uint32_t>(h);
    texture.format = TextureFormat::RGBA8;
    texture.metadata["sourceChannels"] = std::to_string(n);
    texture.data.assign(pixels, pixels + static_cast<size_t>(w) * h * 4);
    stbi_image_free(pixels);

    std::vector<uint8_t> level(texture.data);
    int lw = w, lh = h;
    texture.mipLevels = 1;
    while (lw > 1 || lh > 1) {
        const int nw = std::max(1, lw / 2), nh = std::max(1, lh / 2);
        std::vector<uint8_t> next(static_cast<size_t>(nw) * nh * 4);
        for (int y = 0; y < nh; ++y) {
            for (int x = 0; x < nw; ++x) {
                for (int c = 0; c < 4; ++c) {
                    int sum = 0;
                    for (int dy = 0; dy < 2; ++dy)
                        for (int dx = 0; dx < 2; ++dx) {
                            const int sx = std::min(lw - 1, x * 2 + dx), sy = std::min(lh - 1, y * 2 + dy);
                            sum += level[(static_cast<size_t>(sy) * lw + sx) * 4 + c];
                        }
                    next[(static_cast<size_t>(y) * nw + x) * 4 + c] = static_cast<uint8_t>((sum + 2) / 4);
                }
            }
        }
        texture.data.insert(texture.data.end(), next.begin(), next.end());
        level = std::move(next);
        lw = nw;
        lh = nh;
        ++texture.mipLevels;
    }
    return texture;
}

// Animation Processor Implementations
ProcessedAnimation WeaponGen::AnimationProcessor::process(const std::string& path) {
    ProcessedAnimation animation;
    animation.path = path;

    std::ifstream file(path, std::ios::binary);
    if (!file.is_open()) {
        animation.metadata["error"] = "Failed to open animation: " + path;
        return animation;
    }
    animation.data.assign(std::istreambuf_iterator<char>(file), std::istreambuf_iterator<char>());

    // JSON animation clips carry their timing; other formats are kept as opaque compiled data
    Json j = Json::parse(animation.data.begin(), animation.data.end(), nullptr, false);
    if (!j.is_discarded() && j.is_object()) {
        readIf(j, "frameRate", animation.frameRate);
        if (j.contains("frames") && j.at("frames").is_array()) {
            animation.frameCount = static_cast<uint32_t>(j.at("frames").size());
        }
        readIf(j, "frameCount", animation.frameCount);
        readIf(j, "duration", animation.duration);
        if (animation.duration <= 0.0f && animation.frameRate > 0.0f) {
            animation.duration = static_cast<float>(animation.frameCount) / animation.frameRate;
        }
        if (animation.frameCount == 0) {
            animation.frameCount = static_cast<uint32_t>(std::lround(animation.duration * animation.frameRate));
        }
        animation.metadata["format"] = "json";
    } else {
        animation.metadata["format"] = "binary";
    }
    return animation;
}

// Quality calculation functions
float WeaponGen::calculatePeakAmplitude(const std::vector<float>& samples) {
    if (samples.empty()) return 0.0f;
    float peak = 0.0f;
    for (float s : samples) peak = std::max(peak, std::abs(s));
    return peak;
}

float WeaponGen::calculateRMSAmplitude(const std::vector<float>& samples) {
    if (samples.empty()) return 0.0f;
    float sum = 0.0f;
    for (float sample : samples) {
        sum += sample * sample;
    }
    return std::sqrt(sum / samples.size());
}

float WeaponGen::calculateDynamicRange(const std::vector<float>& samples) {
    if (samples.empty()) return 0.0f;
    float peak = calculatePeakAmplitude(samples);
    float rms = calculateRMSAmplitude(samples);
    return (peak > 0.0f && rms > 0.0f) ? 20.0f * std::log10(peak / rms) : 0.0f;
}

float WeaponGen::calculateSignalToNoiseRatio(const std::vector<float>& samples) {
    if (samples.empty()) return 0.0f;
    float signal = calculateRMSAmplitude(samples);
    float noise = 0.001f; // Assumed noise floor
    return signal > 0.0f ? 20.0f * std::log10(signal / noise) : 0.0f;
}

// Quality Settings
void WeaponGen::setProcessingQuality(int quality) {
    m_processingQuality = clamp(quality, 1, 10);
}

void WeaponGen::setLODReduction(float reduction) {
    m_lodReduction = clamp(reduction, 0.0f, 1.0f);
}

void WeaponGen::setPhysicsEnabled(bool enable) {
    m_enablePhysics = enable;
}

// Processing Options
void WeaponGen::enableGPUAcceleration(bool enable) {
    m_gpuAccelerationEnabled = enable;
}

void WeaponGen::setMaxProcessingThreads(int threads) {
    m_maxProcessingThreads = clamp(threads, 1, 16);
}

// Error Handling
std::string WeaponGen::getLastError() const {
    return m_lastError;
}

void WeaponGen::clearLastError() {
    m_lastError.clear();
}

// Utility Functions
float WeaponGen::clamp(float value, float min, float max) {
    return std::max(min, std::min(max, value));
}

int WeaponGen::clamp(int value, int min, int max) {
    return std::max(min, std::min(max, value));
}

} // namespace Weapons
} // namespace Audio
} // namespace MagiTech
