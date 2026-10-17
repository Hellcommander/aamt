#include "ProceduralFactory.hpp"
#include "SegmentedCreatureParams.hpp"
#include "MonsterCreatureAssets.hpp"
#include "core/Log.hpp"

#include <glm/glm.hpp>
#include <algorithm>
#include <cmath>
#include <fstream>
#include <sstream>
#include <stdexcept>

namespace MagiTech {
namespace SegmentedCreatures {

using CreatureAssets::AssetStore;
using CreatureAssets::MeshData;
using CreatureAssets::TextureData;
using CreatureAssets::SkeletonData;
using CreatureAssets::AnimationData;
using CreatureAssets::BehaviorTreeData;
using CreatureAssets::BehaviorNodeType;
using CreatureAssets::BoneKey;
namespace Geometry = CreatureAssets::Geometry;
namespace Noise = CreatureAssets::Noise;

namespace {

constexpr float kPi = 3.14159265358979323846f;
constexpr float kTwoPi = 2.0f * kPi;

int clampedSegmentCount(const SegmentedCreatureParams& p) { return std::clamp(p.segmentCount, 1, 1000); }
float segmentPitch(const SegmentedCreatureParams& p) { return std::max(p.segmentLength, 0.01f) + std::max(p.segmentSpacing, 0.0f); }

uint32_t creatureSeed(const SegmentedCreatureParams& p) {
    return Noise::seedFromString(p.id) ^ static_cast<uint32_t>(p.hashKey() & 0xFFFFFFFFu);
}

/** Radius multiplier along the body; t = 0 at the head, 1 at the tail. */
float taperAt(const SegmentedCreatureParams& p, float t) {
    t = std::clamp(t, 0.0f, 1.0f);
    float scale = 1.0f;
    switch (p.taperProfile) {
        case TaperProfile::NONE:
            scale = 1.0f;
            break;
        case TaperProfile::LINEAR:
            scale = 1.0f - 0.7f * t;
            break;
        case TaperProfile::EXPONENTIAL:
            scale = std::exp(-2.2f * t);
            break;
        case TaperProfile::CUSTOM_CURVE: {
            const auto& curve = p.customTaperCurve;
            if (curve.empty()) {
                scale = 1.0f - 0.7f * t;            // no curve supplied: behave like LINEAR
            } else if (curve.size() == 1) {
                scale = curve.front();
            } else {
                const float x = t * static_cast<float>(curve.size() - 1);
                const size_t i = std::min(static_cast<size_t>(x), curve.size() - 2);
                scale = glm::mix(curve[i], curve[i + 1], x - static_cast<float>(i));
            }
            break;
        }
    }
    return std::max(scale, 0.1f);
}

// Centre line of the body in its resting pose: the head sits at the origin, the body trails
// along -X with a gentle lateral S-curve whose amplitude grows as the joints get looser.
glm::vec3 spinePoint(const SegmentedCreatureParams& p, float arc) {
    const float total = segmentPitch(p) * clampedSegmentCount(p);
    const float wavelength = std::max(total / 1.5f, segmentPitch(p) * 4.0f);
    const float amplitude = p.segmentRadius * 1.5f * (1.0f - std::clamp(p.articulationStiffness, 0.0f, 1.0f));
    return glm::vec3(-arc, 0.0f, amplitude * std::sin(kTwoPi * arc / wavelength));
}

struct SegmentFrame {
    glm::vec3 start{0.0f};
    glm::vec3 end{0.0f};
    glm::vec3 direction{-1.0f, 0.0f, 0.0f};   // head -> tail
    glm::vec3 up{0.0f, 1.0f, 0.0f};
    float taper = 1.0f;
};

std::vector<SegmentFrame> buildSegmentFrames(const SegmentedCreatureParams& p) {
    const int count = clampedSegmentCount(p);
    const float pitch = segmentPitch(p);
    std::vector<SegmentFrame> frames(static_cast<size_t>(count));
    for (int i = 0; i < count; ++i) {
        SegmentFrame& f = frames[static_cast<size_t>(i)];
        const float s = static_cast<float>(i) * pitch;
        f.start = spinePoint(p, s);
        f.end = spinePoint(p, s + std::max(p.segmentLength, 0.01f));
        f.direction = glm::normalize(f.end - f.start);
        const glm::vec3 side = glm::normalize(glm::cross(f.direction, glm::vec3(0.0f, 1.0f, 0.0f)));
        f.up = glm::normalize(glm::cross(side, f.direction));
        f.taper = taperAt(p, count > 1 ? static_cast<float>(i) / static_cast<float>(count - 1) : 0.0f);
    }
    return frames;
}

/** Bone layout shared by RigGen and AnimGen so animation tracks always match the skeleton. */
struct BoneLayout {
    int segmentBones = 0;
    int headBone = -1;
    int tailBone = -1;
    int total = 0;
};

BoneLayout boneLayout(const SegmentedCreatureParams& p) {
    BoneLayout layout;
    layout.segmentBones = clampedSegmentCount(p);
    layout.total = layout.segmentBones;
    if (p.headType != HeadType::SIMPLE) layout.headBone = layout.total++;
    if (p.tailType != TailType::NONE) layout.tailBone = layout.total++;
    return layout;
}

float metadataFloat(const SegmentedCreatureParams& p, const std::string& key, float fallback) {
    auto it = p.metadata.find(key);
    if (it == p.metadata.end()) return fallback;
    try {
        return std::stof(it->second);
    } catch (const std::exception&) {
        return fallback;
    }
}

} // namespace

// ============================================================================ Mesh Generation
namespace MeshGen {
namespace {

/** Minimal Wavefront OBJ reader (v / vt / vn / polygon f, negative indices supported). */
bool loadObj(const std::string& path, MeshData& out) {
    std::ifstream file(path);
    if (!file.is_open()) return false;
    std::vector<glm::vec3> positions, normals;
    std::vector<glm::vec2> uvs;
    MeshData mesh;
    std::string line;
    auto resolve = [](int index, size_t size) -> int {
        if (index > 0) return index - 1;
        if (index < 0) return static_cast<int>(size) + index;
        return -1;
    };
    while (std::getline(file, line)) {
        std::istringstream in(line);
        std::string tag;
        in >> tag;
        if (tag == "v") {
            glm::vec3 v; in >> v.x >> v.y >> v.z; positions.push_back(v);
        } else if (tag == "vt") {
            glm::vec2 t; in >> t.x >> t.y; uvs.push_back(t);
        } else if (tag == "vn") {
            glm::vec3 n; in >> n.x >> n.y >> n.z; normals.push_back(n);
        } else if (tag == "f") {
            std::vector<uint32_t> polygon;
            std::string corner;
            while (in >> corner) {
                int vi = 0, ti = 0, ni = 0;
                const size_t s1 = corner.find('/');
                vi = std::stoi(corner.substr(0, s1));
                if (s1 != std::string::npos) {
                    const size_t s2 = corner.find('/', s1 + 1);
                    const std::string t = corner.substr(s1 + 1, s2 == std::string::npos ? std::string::npos : s2 - s1 - 1);
                    if (!t.empty()) ti = std::stoi(t);
                    if (s2 != std::string::npos && s2 + 1 < corner.size()) ni = std::stoi(corner.substr(s2 + 1));
                }
                const int pv = resolve(vi, positions.size());
                if (pv < 0 || pv >= static_cast<int>(positions.size())) return false;
                CreatureAssets::MeshVertex vert;
                vert.position = positions[static_cast<size_t>(pv)];
                const int pt = resolve(ti, uvs.size());
                if (pt >= 0 && pt < static_cast<int>(uvs.size())) vert.uv = uvs[static_cast<size_t>(pt)];
                const int pn = resolve(ni, normals.size());
                if (pn >= 0 && pn < static_cast<int>(normals.size())) vert.normal = normals[static_cast<size_t>(pn)];
                polygon.push_back(static_cast<uint32_t>(mesh.vertices.size()));
                mesh.vertices.push_back(vert);
            }
            for (size_t k = 1; k + 1 < polygon.size(); ++k) {
                mesh.indices.push_back(polygon[0]);
                mesh.indices.push_back(polygon[k]);
                mesh.indices.push_back(polygon[k + 1]);
            }
        }
    }
    if (mesh.indices.empty()) return false;
    if (normals.empty()) mesh.recomputeNormals();
    out = std::move(mesh);
    return true;
}

// Segment primitives are built in local space: the segment runs along +Z from 0 to `length`,
// with +Y as the dorsal (up) direction.
MeshData createCylinderSegment(float radius, float length) {
    return Geometry::tube({glm::vec3(0.0f), glm::vec3(0.0f, 0.0f, length)}, {radius, radius}, 16, true);
}

MeshData createBoxSegment(float radius, float length) {
    // 4-sided prism rotated 45 degrees so the half-width equals `radius`.
    return Geometry::prism(glm::vec3(0.0f), glm::vec3(0.0f, 0.0f, 1.0f), radius * std::sqrt(2.0f), length, 4, kPi * 0.25f);
}

MeshData createHexagonSegment(float radius, float length) {
    return Geometry::prism(glm::vec3(0.0f), glm::vec3(0.0f, 0.0f, 1.0f), radius, length, 6);
}

MeshData createCustomSegment(const SegmentedCreatureParams& p, float radius, float length) {
    auto it = p.metadata.find("customMesh");
    MeshData mesh;
    if (it == p.metadata.end() || !loadObj(it->second, mesh)) {
        Log::warn("SegmentedCreature", "Custom segment mesh for '{}' unavailable ({}), using cylinder segment",
                  p.id, it == p.metadata.end() ? std::string("no metadata.customMesh") : it->second);
        return createCylinderSegment(radius, length);
    }
    // Fit the loaded mesh into the segment volume: Z extent -> [0, length], XY -> radius.
    const auto [lo, hi] = mesh.bounds();
    const glm::vec3 size = glm::max(hi - lo, glm::vec3(1e-4f));
    const float xyScale = 2.0f * radius / std::max(size.x, size.y);
    const glm::mat4 fit(
        glm::vec4(xyScale, 0.0f, 0.0f, 0.0f),
        glm::vec4(0.0f, xyScale, 0.0f, 0.0f),
        glm::vec4(0.0f, 0.0f, length / size.z, 0.0f),
        glm::vec4(-(lo.x + hi.x) * 0.5f * xyScale, -(lo.y + hi.y) * 0.5f * xyScale, -lo.z * length / size.z, 1.0f));
    mesh.transform(fit);
    return mesh;
}

MeshData createSegmentMesh(const SegmentedCreatureParams& p) {
    const float radius = std::max(p.segmentRadius, 0.01f);
    const float length = std::max(p.segmentLength, 0.01f);
    switch (p.segmentType) {
        case SegmentType::CYLINDER:    return createCylinderSegment(radius, length);
        case SegmentType::BOX:         return createBoxSegment(radius, length);
        case SegmentType::HEXAGON:     return createHexagonSegment(radius, length);
        case SegmentType::CUSTOM_MESH: return createCustomSegment(p, radius, length);
    }
    return createCylinderSegment(radius, length);
}

/** Places a tapered copy of `segment` on every segment frame. */
MeshData assembleAlongSpline(const MeshData& segment, const std::vector<SegmentFrame>& frames) {
    MeshData body;
    for (const auto& f : frames) {
        const glm::vec3 side = glm::cross(f.up, f.direction);
        const glm::mat4 placement(
            glm::vec4(side * f.taper, 0.0f),
            glm::vec4(f.up * f.taper, 0.0f),
            glm::vec4(f.direction, 0.0f),
            glm::vec4(f.start, 1.0f));
        MeshData copy = segment;
        copy.transform(placement);
        body.append(copy);
    }
    return body;
}

void applyNoiseDisplacement(MeshData& mesh, const SegmentedCreatureParams& p) {
    const float radius = std::max(p.segmentRadius, 0.01f);
    Geometry::displaceAlongNormals(mesh, p.noiseDetail * radius * 0.12f, 3.0f / radius, creatureSeed(p));
}

float headRadius(const SegmentedCreatureParams& p, const SegmentFrame& front) {
    return std::max(p.segmentRadius, 0.01f) * front.taper * 1.25f;
}

void addMandibleHead(MeshData& mesh, const glm::vec3& center, const glm::vec3& forward, const glm::vec3& up, float radius) {
    const glm::vec3 side = glm::normalize(glm::cross(forward, up));
    for (int s = -1; s <= 1; s += 2) {
        const glm::vec3 root = center + side * (radius * 0.6f * s) - up * (radius * 0.3f) + forward * (radius * 0.5f);
        std::vector<glm::vec3> path;
        std::vector<float> radii;
        const int steps = 6;
        for (int k = 0; k <= steps; ++k) {
            const float t = static_cast<float>(k) / steps;
            // Curve forward, then hook inward.
            path.push_back(root + forward * (radius * 1.2f * t) - side * (radius * 0.55f * s * t * t));
            radii.push_back(radius * 0.18f * (1.0f - 0.85f * t));
        }
        mesh.append(Geometry::tube(path, radii, 6, true));
    }
}

void addMultiEyeHead(MeshData& mesh, const glm::vec3& center, const glm::vec3& forward, const glm::vec3& up, float radius) {
    const glm::vec3 side = glm::normalize(glm::cross(forward, up));
    const int eyes = 6;
    for (int e = 0; e < eyes; ++e) {
        const float a = (static_cast<float>(e) / (eyes - 1) - 0.5f) * kPi * 0.7f;   // spread across the front
        const float row = (e % 2 == 0) ? 0.35f : 0.6f;
        const glm::vec3 dir = glm::normalize(forward * std::cos(a) + side * std::sin(a) + up * row);
        mesh.append(Geometry::sphere(center + dir * radius * 0.92f, radius * 0.16f, 6, 8));
    }
}

void addHornedHead(MeshData& mesh, const glm::vec3& center, const glm::vec3& forward, const glm::vec3& up, float radius) {
    const glm::vec3 side = glm::normalize(glm::cross(forward, up));
    for (int s = -1; s <= 1; s += 2) {
        const glm::vec3 base = center + up * (radius * 0.7f) + side * (radius * 0.45f * s);
        const glm::vec3 dir = glm::normalize(up * 0.8f - forward * 0.5f + side * (0.3f * s));
        mesh.append(Geometry::cone(base, dir, radius * 0.22f, radius * 1.4f, 10));
    }
}

void attachHead(MeshData& mesh, const SegmentedCreatureParams& p, const SegmentFrame& front) {
    const glm::vec3 forward = -front.direction;
    const float radius = headRadius(p, front);
    const glm::vec3 center = front.start + forward * (radius * 0.6f);
    const glm::vec3 side = glm::normalize(glm::cross(forward, front.up));
    // Head capsule, slightly elongated along the travel direction.
    MeshData head = Geometry::sphere(glm::vec3(0.0f), 1.0f, 10, 14);
    const glm::mat4 orient(
        glm::vec4(forward * radius * 1.15f, 0.0f),
        glm::vec4(front.up * radius * 0.9f, 0.0f),
        glm::vec4(side * radius, 0.0f),
        glm::vec4(center, 1.0f));
    head.transform(orient);
    mesh.append(head);

    switch (p.headType) {
        case HeadType::SIMPLE:
            break;   // plain rounded head only
        case HeadType::MANDIBLE:
            addMandibleHead(mesh, center, forward, front.up, radius);
            break;
        case HeadType::MULTI_EYE:
            addMultiEyeHead(mesh, center, forward, front.up, radius);
            break;
        case HeadType::HORNED:
            addHornedHead(mesh, center, forward, front.up, radius);
            break;
    }
}

void addSpikeTail(MeshData& mesh, const SegmentFrame& back, float radius) {
    mesh.append(Geometry::cone(back.end, back.direction, radius * 0.9f, radius * 4.0f, 12));
}

void addFlaredTail(MeshData& mesh, const SegmentFrame& back, float radius) {
    const glm::vec3 side = glm::normalize(glm::cross(back.up, back.direction));
    const glm::vec3 root = back.end;
    const glm::vec3 tip = root + back.direction * radius * 3.0f;
    // Horizontal fan plus a smaller vertical fin.
    mesh.append(Geometry::membrane(root - side * radius * 0.5f, root + side * radius * 0.5f,
                                   tip + side * radius * 2.2f, tip - side * radius * 2.2f));
    mesh.append(Geometry::membrane(root, root + back.up * radius * 0.4f,
                                   tip + back.up * radius * 1.4f, tip - back.up * radius * 0.2f));
    mesh.append(Geometry::cone(root - back.direction * radius * 0.2f, back.direction, radius * 0.6f, radius * 1.2f, 10));
}

void attachTail(MeshData& mesh, const SegmentedCreatureParams& p, const SegmentFrame& back) {
    const float radius = std::max(p.segmentRadius, 0.01f) * back.taper;
    switch (p.tailType) {
        case TailType::NONE:
            break;
        case TailType::SPIKE:
            addSpikeTail(mesh, back, radius);
            break;
        case TailType::FLARED:
            addFlaredTail(mesh, back, radius);
            break;
    }
}

void addArmorPlates(MeshData& mesh, const SegmentedCreatureParams& p, const std::vector<SegmentFrame>& frames) {
    const int detail = std::clamp(p.plateDetailLevel, 0, 3);
    if (detail == 0) return;
    const float arc = kPi * (0.6f + 0.15f * detail);
    const int arcSegments = 4 * (detail + 1);
    const float thickness = std::max(p.armorThickness, 0.005f);
    // Box segments have corners at radius*sqrt(2); keep plates clear of them.
    const float shapeScale = p.segmentType == SegmentType::BOX ? std::sqrt(2.0f) : 1.0f;
    for (const auto& f : frames) {
        Geometry::Frame frame;
        frame.origin = f.start;
        frame.tangent = f.direction;
        frame.normal = f.up;
        frame.binormal = glm::cross(f.direction, f.up);
        const float radius = std::max(p.segmentRadius, 0.01f) * f.taper * shapeScale * 1.04f;
        const float length = std::max(p.segmentLength, 0.01f) * 0.92f;
        mesh.append(Geometry::shell(frame, radius, thickness, length, arc, arcSegments));
    }
}

void addSpikes(MeshData& mesh, const SegmentedCreatureParams& p, const std::vector<SegmentFrame>& frames) {
    const int spikes = std::max(p.spikeCount, 0);
    if (spikes == 0 || frames.empty()) return;
    const float length = std::max(p.spikeLength, 0.01f);
    for (int k = 0; k < spikes; ++k) {
        const size_t index = std::min(frames.size() - 1,
            static_cast<size_t>((static_cast<float>(k) + 0.5f) / spikes * static_cast<float>(frames.size())));
        const auto& f = frames[index];
        const glm::vec3 mid = (f.start + f.end) * 0.5f;
        const float radius = std::max(p.segmentRadius, 0.01f) * f.taper;
        const glm::vec3 base = mid + f.up * (radius + (p.armorPlates ? p.armorThickness : 0.0f));
        const glm::vec3 dir = glm::normalize(f.up + f.direction * 0.35f);   // swept back
        mesh.append(Geometry::cone(base, dir, length * 0.25f, length, 8));
    }
}

} // namespace

MeshHandle build(const SegmentedCreatureParams& p) {
    const auto frames = buildSegmentFrames(p);

    // Generate base segment mesh and assemble the body along the spine spline (taper applied per segment).
    MeshData baseSegment = createSegmentMesh(p);
    MeshData fullMesh = assembleAlongSpline(baseSegment, frames);

    // Apply noise displacement
    if (p.noiseDetail > 0.0f) {
        applyNoiseDisplacement(fullMesh, p);
    }

    attachHead(fullMesh, p, frames.front());
    attachTail(fullMesh, p, frames.back());

    if (p.armorPlates) {
        addArmorPlates(fullMesh, p, frames);
    }

    if (p.enableSpikes && p.spikeCount > 0) {
        addSpikes(fullMesh, p, frames);
    }

    Log::debug("SegmentedCreature", "Mesh for '{}': {} vertices, {} triangles",
               p.id, fullMesh.vertices.size(), fullMesh.triangleCount());
    return AssetStore::instance().addMesh(std::move(fullMesh));
}

} // namespace MeshGen

// ============================================================================ Texture Generation
namespace TextureGen {
namespace {

glm::vec3 toVec3(const std::array<float, 3>& c) { return glm::vec3(c[0], c[1], c[2]); }

// Texture layout matches the segment UVs: x = around the body (0 = dorsal, 0.5 = ventral),
// y = along one segment (0 = front edge, 1 = back edge).
TextureData generateBaseTexture(const SegmentedCreatureParams& p, uint32_t size) {
    TextureData texture(size, size);
    const glm::vec3 primary = toVec3(p.colorPrimary);
    const glm::vec3 secondary = toVec3(p.colorSecondary);
    const uint32_t seed = creatureSeed(p);
    for (uint32_t y = 0; y < size; ++y) {
        for (uint32_t x = 0; x < size; ++x) {
            const float u = (x + 0.5f) / size;
            const float v = (y + 0.5f) / size;
            const float belly = 0.5f - 0.5f * std::cos(kTwoPi * u);       // 0 dorsal -> 1 ventral
            glm::vec3 color = glm::mix(primary, secondary, glm::smoothstep(0.35f, 0.75f, belly));
            const float grain = Noise::fbm3(glm::vec3(u * 8.0f, v * 8.0f, 0.0f), 4, seed);
            color *= 1.0f + grain * (0.08f + 0.15f * p.noiseDetail);
            texture.set(x, y, glm::vec4(color, 1.0f));
        }
    }
    return texture;
}

void applyArmorPattern(TextureData& texture, const SegmentedCreatureParams& p) {
    const int detail = std::clamp(p.plateDetailLevel, 0, 3);
    if (detail == 0) return;
    const uint32_t seed = creatureSeed(p) + 77u;
    const float seamWidth = 0.06f / detail;
    for (uint32_t y = 0; y < texture.height; ++y) {
        for (uint32_t x = 0; x < texture.width; ++x) {
            const float u = (x + 0.5f) / texture.width;
            const float v = (y + 0.5f) / texture.height;
            glm::vec4 c = texture.get(x, y);
            float shade = 1.0f;
            // Plate seams at the segment boundaries.
            const float edge = std::min(v, 1.0f - v);
            if (edge < seamWidth) shade *= 0.55f + 0.45f * (edge / seamWidth);
            // Scales inside each plate from medium detail up.
            if (detail >= 2) {
                const float cell = Noise::worley2(glm::vec2(u * 6.0f * detail, v * 3.0f * detail), seed);
                shade *= 0.85f + 0.15f * glm::smoothstep(0.05f, 0.45f, cell);
            }
            // Rivets along the plate rim at high detail.
            if (detail >= 3) {
                const float rivetU = std::fmod(u * 16.0f, 1.0f) - 0.5f;
                const float rivetV = v - 0.15f;
                if (rivetU * rivetU + rivetV * rivetV * 4.0f < 0.02f) shade *= 1.35f;
            }
            texture.set(x, y, glm::vec4(glm::vec3(c) * shade, c.a));
        }
    }
}

void applyMaterialProperties(TextureData& texture, float roughness, float metallic) {
    texture.roughness = std::clamp(roughness, 0.0f, 1.0f);
    texture.metallic = std::clamp(metallic, 0.0f, 1.0f);
    // Bake a soft dorsal sheen whose strength follows the PBR factors so unlit sprite
    // renders still read as glossy/metallic.
    const float sheen = texture.metallic * (1.0f - texture.roughness);
    if (sheen <= 0.0f) return;
    for (uint32_t y = 0; y < texture.height; ++y) {
        for (uint32_t x = 0; x < texture.width; ++x) {
            const float u = (x + 0.5f) / texture.width;
            const float highlight = std::pow(std::max(std::cos(kTwoPi * u), 0.0f), 8.0f) * sheen * 0.45f;
            glm::vec4 c = texture.get(x, y);
            c = glm::vec4(glm::mix(glm::vec3(c), glm::vec3(1.0f), highlight), c.a);
            texture.set(x, y, c);
        }
    }
}

} // namespace

TextureHandle build(const SegmentedCreatureParams& p) {
    const uint32_t size = 64u << std::clamp(p.plateDetailLevel, 0, 2);
    TextureData baseTexture = generateBaseTexture(p, size);

    if (p.armorPlates) {
        applyArmorPattern(baseTexture, p);
    }

    applyMaterialProperties(baseTexture, p.materialRoughness, p.materialMetallic);

    return AssetStore::instance().addTexture(std::move(baseTexture));
}

} // namespace TextureGen

// ============================================================================ Rig Generation
namespace RigGen {
namespace {

void createBoneChain(SkeletonData& skeleton, const std::vector<SegmentFrame>& frames) {
    for (size_t i = 0; i < frames.size(); ++i) {
        skeleton.addBone("segment_" + std::to_string(i), static_cast<int>(i) - 1, frames[i].start, frames[i].end);
    }
}

void addHeadBone(SkeletonData& skeleton, const SegmentedCreatureParams& p, const SegmentFrame& front) {
    const float radius = std::max(p.segmentRadius, 0.01f) * front.taper * 1.25f;
    const glm::vec3 forward = -front.direction;
    const float reach = p.headType == HeadType::MANDIBLE ? 2.2f : 1.6f;
    skeleton.addBone("head", 0, front.start, front.start + forward * radius * reach);
}

void addTailBone(SkeletonData& skeleton, const SegmentedCreatureParams& p, const SegmentFrame& back, int parent) {
    const float radius = std::max(p.segmentRadius, 0.01f) * back.taper;
    const float reach = p.tailType == TailType::SPIKE ? 4.0f : 3.0f;
    skeleton.addBone("tail", parent, back.end, back.end + back.direction * radius * reach);
}

void setJointLimits(SkeletonData& skeleton, const SegmentedCreatureParams& p) {
    const float stiffness = std::clamp(p.articulationStiffness, 0.0f, 1.0f);
    float limit = glm::radians(glm::mix(60.0f, 8.0f, stiffness));
    limit *= p.enableJoints ? (0.5f + std::clamp(p.jointFlexibility, 0.0f, 1.0f)) : 0.0f;
    for (auto& bone : skeleton.bones) {
        bone.stiffness = stiffness;
        bone.minAngle = bone.parent < 0 ? -kPi : -limit;   // root bone orients freely
        bone.maxAngle = bone.parent < 0 ? kPi : limit;
    }
}

} // namespace

SkeletonHandle build(const SegmentedCreatureParams& p) {
    const auto frames = buildSegmentFrames(p);
    const BoneLayout layout = boneLayout(p);
    SkeletonData skeleton;

    createBoneChain(skeleton, frames);
    if (layout.headBone >= 0) {
        addHeadBone(skeleton, p, frames.front());
    }
    if (layout.tailBone >= 0) {
        addTailBone(skeleton, p, frames.back(), layout.segmentBones - 1);
    }
    setJointLimits(skeleton, p);

    return AssetStore::instance().addSkeleton(std::move(skeleton));
}

} // namespace RigGen

// ============================================================================ Animation Generation
namespace AnimGen {
namespace {

constexpr size_t kFrames = 24;

/** Joint index along the spine used for wave phases (head = -1, tail = segments). */
float spineIndex(const BoneLayout& layout, size_t bone) {
    const int b = static_cast<int>(bone);
    if (b == layout.headBone) return -1.0f;
    if (b == layout.tailBone) return static_cast<float>(layout.segmentBones);
    return static_cast<float>(b);
}

float waveAmplitude(const SegmentedCreatureParams& p, float maxDegrees) {
    return glm::radians(maxDegrees) * (1.0f - 0.7f * std::clamp(p.articulationStiffness, 0.0f, 1.0f));
}

float cycleDuration(const SegmentedCreatureParams& p) {
    return 0.8f + 0.03f * static_cast<float>(clampedSegmentCount(p));
}

void createSlitherAnimation(AnimationData& animation, const SegmentedCreatureParams& p, const BoneLayout& layout) {
    const float amplitude = waveAmplitude(p, 25.0f);
    const float k = kTwoPi / std::max(4.0f, layout.segmentBones / 1.5f);
    animation.addSampledClip("slither", cycleDuration(p), true, kFrames, [&](size_t bone, float phase) {
        BoneKey key;
        const float i = spineIndex(layout, bone);
        const float scale = static_cast<int>(bone) == layout.headBone ? 0.4f : 1.0f;
        key.rotation.y = amplitude * scale * std::cos(kTwoPi * phase - k * i);
        return key;
    });
}

void createCrawlAnimation(AnimationData& animation, const SegmentedCreatureParams& p, const BoneLayout& layout) {
    const float amplitude = waveAmplitude(p, 15.0f);
    const float k = kTwoPi / std::max(3.0f, layout.segmentBones / 2.0f);
    const float lift = std::max(p.segmentRadius, 0.01f) * 0.6f;
    animation.addSampledClip("crawl", cycleDuration(p) * 1.4f, true, kFrames, [&](size_t bone, float phase) {
        BoneKey key;
        const float i = spineIndex(layout, bone);
        const float wave = std::sin(kTwoPi * phase - k * i);
        key.rotation.x = amplitude * wave;                       // vertical inchworm wave
        key.rotation.y = amplitude * 0.25f * std::cos(kTwoPi * phase - k * i);
        key.translation.y = lift * std::max(wave, 0.0f);         // arched segments leave the ground
        return key;
    });
}

void createCoilAnimation(AnimationData& animation, const SegmentedCreatureParams& p, const BoneLayout& layout) {
    const float perJoint = kTwoPi * 1.25f / std::max(1, layout.segmentBones);
    const float limit = glm::radians(glm::mix(60.0f, 8.0f, std::clamp(p.articulationStiffness, 0.0f, 1.0f)));
    const float bend = std::min(perJoint, limit);
    animation.addSampledClip("coil", cycleDuration(p) * 2.0f, true, kFrames, [&](size_t bone, float phase) {
        BoneKey key;
        const float amount = 0.5f - 0.5f * std::cos(kTwoPi * phase);    // curl in, then release
        const bool spine = static_cast<int>(bone) < layout.segmentBones;
        key.rotation.y = spine && bone > 0 ? bend * amount : 0.0f;
        key.rotation.x = static_cast<int>(bone) == layout.headBone ? -0.3f * amount : 0.0f;  // head rears up
        return key;
    });
}

void createCustomAnimation(AnimationData& animation, const SegmentedCreatureParams& p, const BoneLayout& layout) {
    // Driven by metadata: animAmplitude (degrees), animWavelength (segments), animDuration (s), animVertical (0..1).
    const float amplitude = glm::radians(metadataFloat(p, "animAmplitude", 20.0f));
    const float wavelength = std::max(1.0f, metadataFloat(p, "animWavelength", layout.segmentBones / 1.5f));
    const float duration = std::max(0.1f, metadataFloat(p, "animDuration", cycleDuration(p)));
    const float vertical = std::clamp(metadataFloat(p, "animVertical", 0.3f), 0.0f, 1.0f);
    const float k = kTwoPi / wavelength;
    animation.addSampledClip("custom", duration, true, kFrames, [&](size_t bone, float phase) {
        BoneKey key;
        const float i = spineIndex(layout, bone);
        key.rotation.y = amplitude * (1.0f - vertical) * std::cos(kTwoPi * phase - k * i);
        key.rotation.x = amplitude * vertical * std::sin(kTwoPi * phase - k * i);
        return key;
    });
}

void createIdleAnimation(AnimationData& animation, const SegmentedCreatureParams& p, const BoneLayout& layout) {
    const float breathe = std::max(p.segmentRadius, 0.01f) * 0.05f;
    animation.addSampledClip("idle", 2.5f, true, kFrames, [&](size_t bone, float phase) {
        BoneKey key;
        const float i = spineIndex(layout, bone);
        key.translation.y = breathe * std::sin(kTwoPi * phase - 0.3f * i);
        key.rotation.y = glm::radians(2.0f) * std::sin(kTwoPi * phase * 0.5f - 0.2f * i);
        return key;
    });
}

} // namespace

AnimationHandle build(const SegmentedCreatureParams& p) {
    const BoneLayout layout = boneLayout(p);
    AnimationData animation;
    animation.boneCount = static_cast<size_t>(layout.total);

    switch (p.animationProfile) {
        case AnimationProfile::SLITHER:
            createSlitherAnimation(animation, p, layout);
            break;
        case AnimationProfile::CRAWL:
            createCrawlAnimation(animation, p, layout);
            break;
        case AnimationProfile::COIL:
            createCoilAnimation(animation, p, layout);
            break;
        case AnimationProfile::CUSTOM:
            createCustomAnimation(animation, p, layout);
            break;
    }
    createIdleAnimation(animation, p, layout);

    return AssetStore::instance().addAnimation(std::move(animation));
}

} // namespace AnimGen

// ============================================================================ AI Generation
namespace AIGen {
namespace {

void createBehaviorTree(BehaviorTreeData& ai, const BehaviorParams& p) {
    ai.name = p.behaviorName.empty() ? std::string("segmented_creature") : p.behaviorName;

    // Blackboard: tunables read by the runtime behaviour executor.
    ai.blackboard = {
        {"speed", p.speed}, {"chaseSpeed", p.chaseSpeed}, {"detectionRange", p.detectionRange},
        {"attackRange", p.attackRange}, {"aggression", p.aggression}, {"packSize", static_cast<float>(p.packSize)},
        {"retreatHealth", p.retreatHealth}, {"patrolRadius", p.patrolRadius}, {"idleTime", p.idleTime},
        {"attackDamage", p.attackDamage}, {"attackCooldown", p.attackCooldown},
        {"preferredTemperature", p.preferredTemperature}, {"temperatureTolerance", p.temperatureTolerance},
        {"canSwim", (p.canSwim || p.swimmer) ? 1.0f : 0.0f}, {"canFly", (p.canFly || p.flyer) ? 1.0f : 0.0f},
        {"canClimb", (p.climbAbility || p.climber) ? 1.0f : 0.0f}, {"canBurrow", p.burrower ? 1.0f : 0.0f},
        {"dominanceRank", static_cast<float>(p.dominanceRank)}};

    const int root = ai.addNode(BehaviorNodeType::Selector, "root");

    // 1. Survival: retreat when badly hurt.
    const int flee = ai.addChildNode(root, BehaviorNodeType::Sequence, "flee");
    ai.addChildNode(flee, BehaviorNodeType::Condition, "healthBelow", {{"fraction", p.retreatHealth}});
    if (p.burrower) {
        ai.addChildNode(flee, BehaviorNodeType::Action, "burrowEscape", {{"depth", p.burrowDepth}});
    } else {
        ai.addChildNode(flee, BehaviorNodeType::Action, "retreat", {{"speed", p.speed * p.chaseSpeed}});
    }

    // 2. Combat (only for creatures that ever attack).
    int combat = -1;
    if (p.aggression > 0.0f) {
        combat = ai.addChildNode(root, BehaviorNodeType::Selector, "combat");
        if (p.canRangedAttack) {
            const int ranged = ai.addChildNode(combat, BehaviorNodeType::Sequence, "rangedAttack");
            ai.addChildNode(ranged, BehaviorNodeType::Condition, "targetInRange", {{"range", p.rangedAttackRange}});
            ai.addChildNode(ranged, BehaviorNodeType::Condition, "cooldownReady", {{"cooldown", p.attackCooldown}});
            ai.addChildNode(ranged, BehaviorNodeType::Action, "fireProjectile", {{"damage", p.attackDamage}});
        }
        if (p.canUseAbilities) {
            for (const auto& ability : p.abilities) {
                const int use = ai.addChildNode(combat, BehaviorNodeType::Sequence, "ability:" + ability);
                ai.addChildNode(use, BehaviorNodeType::Condition, "abilityReady:" + ability);
                ai.addChildNode(use, BehaviorNodeType::Action, "useAbility:" + ability, {{"aggression", p.aggression}});
            }
        }
        const int melee = ai.addChildNode(combat, BehaviorNodeType::Sequence, "meleeAttack");
        ai.addChildNode(melee, BehaviorNodeType::Condition, "targetInRange", {{"range", p.attackRange}});
        ai.addChildNode(melee, BehaviorNodeType::Condition, "cooldownReady", {{"cooldown", p.attackCooldown}});
        ai.addChildNode(melee, BehaviorNodeType::Action, "strike", {{"damage", p.attackDamage}});

        const int chase = ai.addChildNode(combat, BehaviorNodeType::Sequence, "chase");
        ai.addChildNode(chase, BehaviorNodeType::Condition, "targetDetected", {{"range", p.detectionRange}});
        ai.addChildNode(chase, BehaviorNodeType::Condition, "aggressionRoll", {{"chance", p.aggression}});
        if (p.packHunting && p.packSize > 1) {
            ai.addChildNode(chase, BehaviorNodeType::Action, "coordinatePack",
                            {{"packSize", static_cast<float>(p.packSize)}, {"cohesion", p.packCohesion},
                             {"hierarchical", p.hierarchical ? 1.0f : 0.0f}});
        }
        if (p.burrower) {
            ai.addChildNode(chase, BehaviorNodeType::Action, "burrowApproach", {{"depth", p.burrowDepth}});
        }
        ai.addChildNode(chase, BehaviorNodeType::Action, "moveToTarget", {{"speed", p.speed * p.chaseSpeed}});
    }

    // 3. Territory defence.
    if (p.territorial) {
        const int guard = ai.addChildNode(root, BehaviorNodeType::Sequence, "defendTerritory");
        ai.addChildNode(guard, BehaviorNodeType::Condition, "intruderInTerritory", {{"radius", p.territorySize}});
        ai.addChildNode(guard, BehaviorNodeType::Action, "threatDisplay", {{"aggression", p.aggression}});
    }

    // 4. Environment comfort.
    const int comfort = ai.addChildNode(root, BehaviorNodeType::Sequence, "seekComfort");
    ai.addChildNode(comfort, BehaviorNodeType::Condition, "temperatureOutside",
                    {{"preferred", p.preferredTemperature}, {"tolerance", p.temperatureTolerance}});
    ai.addChildNode(comfort, BehaviorNodeType::Action, p.burrower ? "burrow" : "relocate", {{"depth", p.burrowDepth}});

    // 5. Routine: patrol while active, otherwise idle.
    const int routine = ai.addChildNode(root, BehaviorNodeType::Sequence, "patrol");
    ai.addChildNode(routine, BehaviorNodeType::Condition, p.nocturnal ? "isNight" : "isDay");
    if (p.packHunting && p.packSize > 1) {
        ai.addChildNode(routine, BehaviorNodeType::Action, "keepFormation", {{"cohesion", p.packCohesion}});
    }
    ai.addChildNode(routine, BehaviorNodeType::Action, "wander", {{"radius", p.patrolRadius}, {"speed", p.speed}});
    ai.addChildNode(root, BehaviorNodeType::Action, "idle", {{"duration", p.idleTime}});

    // State machine view used by the runtime for animation selection.
    ai.addState("idle", root).transitions = {{"targetDetected", "chase"}, {"isActivePeriod", "patrol"}};
    ai.addState("patrol", routine).transitions = {{"targetDetected", "chase"}, {"patrolComplete", "idle"}};
    if (combat >= 0) {
        ai.addState("chase", combat).transitions = {{"targetInAttackRange", "attack"}, {"targetLost", "patrol"},
                                                    {"healthLow", "flee"}};
        ai.addState("attack", combat).transitions = {{"targetOutOfRange", "chase"}, {"healthLow", "flee"}};
    } else {
        // Non-aggressive creatures treat detection as a threat.
        ai.findState("idle")->transitions[0].target = "flee";
        ai.findState("patrol")->transitions[0].target = "flee";
    }
    ai.addState("flee", flee).transitions = {{"safe", "idle"}};
}

} // namespace

BehaviorParams presetFor(AIProfile profile) {
    BehaviorParams b;
    switch (profile) {
        case AIProfile::PASSIVE:
            b.behaviorName = "passive";
            b.aggression = 0.0f;
            b.retreatHealth = 0.9f;
            b.detectionRange = 10.0f;
            b.speed = 0.8f;
            b.chaseSpeed = 1.0f;
            break;
        case AIProfile::NEUTRAL:
            b.behaviorName = "neutral";
            b.aggression = 0.35f;
            b.territorial = true;
            b.territorySize = 8.0f;
            b.retreatHealth = 0.4f;
            break;
        case AIProfile::PREDATOR:
            b.behaviorName = "predator";
            b.aggression = 0.85f;
            b.detectionRange = 22.0f;
            b.chaseSpeed = 1.8f;
            b.burrower = true;
            b.retreatHealth = 0.2f;
            b.attackDamage = 15.0f;
            break;
        case AIProfile::SWARM:
            b.behaviorName = "swarm";
            b.aggression = 0.6f;
            b.packSize = 6;
            b.packHunting = true;
            b.packCohesion = 0.9f;
            b.attackDamage = 5.0f;
            b.retreatHealth = 0.1f;
            break;
    }
    return b;
}

AIHandle build(const BehaviorParams& p) {
    BehaviorTreeData ai;
    createBehaviorTree(ai, p);
    return AssetStore::instance().addBehavior(std::move(ai));
}

AIHandle build(const SegmentedCreatureParams& p) {
    BehaviorParams behavior = presetFor(p.aiProfile);
    behavior.behaviorName = p.id.empty() ? behavior.behaviorName : p.id + "_" + behavior.behaviorName;
    // Movement scales with body size.
    behavior.attackRange = std::max(behavior.attackRange, std::max(p.segmentRadius, 0.01f) * 3.0f);
    behavior.speed *= std::clamp(p.segmentLength * 2.0f, 0.5f, 2.0f);
    return build(behavior);
}

} // namespace AIGen

void releaseBundle(const AssetBundle& bundle) {
    auto& store = AssetStore::instance();
    if (bundle.mesh) store.releaseMesh(bundle.mesh);
    if (bundle.texture) store.releaseTexture(bundle.texture);
    if (bundle.skeleton) store.releaseSkeleton(bundle.skeleton);
    if (bundle.anim) store.releaseAnimation(bundle.anim);
    if (bundle.ai) store.releaseBehavior(bundle.ai);
}

namespace {
nlohmann::json readJsonFile(const std::string& jsonPath) {
    std::ifstream file(jsonPath);
    if (!file.is_open()) {
        throw std::runtime_error("Could not open file: " + jsonPath);
    }
    std::stringstream buffer;
    buffer << file.rdbuf();
    return nlohmann::json::parse(buffer.str());
}
} // namespace

// ============================================================================ SegmentedCreatureFactory
std::future<AssetBundle> SegmentedCreatureFactory::generateFromJson(const std::string& jsonPath) {
    return pool().enqueue([this, jsonPath]() {
        return generateSync(ParamUtils::creatureFromJson(readJsonFile(jsonPath)));
    });
}

std::future<AssetBundle> SegmentedCreatureFactory::generateFromParams(const SegmentedCreatureParams& params) {
    return generateAsync(params);
}

std::vector<std::future<AssetBundle>> SegmentedCreatureFactory::generateBatch(
    const std::vector<SegmentedCreatureParams>& params) {
    std::vector<std::future<AssetBundle>> futures;
    futures.reserve(params.size());

    for (const auto& param : params) {
        futures.push_back(generateAsync(param));
    }

    return futures;
}

bool SegmentedCreatureFactory::validateParams(const SegmentedCreatureParams& params) {
    return params.segmentCount > 0 &&
           params.segmentLength > 0.0f &&
           params.segmentRadius > 0.0f &&
           params.articulationStiffness >= 0.0f &&
           params.articulationStiffness <= 1.0f;
}

std::string SegmentedCreatureFactory::getValidationErrors(const SegmentedCreatureParams& params) {
    std::string errors;

    if (params.segmentCount <= 0) {
        errors += "segmentCount must be greater than 0\n";
    }
    if (params.segmentLength <= 0.0f) {
        errors += "segmentLength must be greater than 0\n";
    }
    if (params.segmentRadius <= 0.0f) {
        errors += "segmentRadius must be greater than 0\n";
    }
    if (params.articulationStiffness < 0.0f || params.articulationStiffness > 1.0f) {
        errors += "articulationStiffness must be between 0 and 1\n";
    }

    return errors;
}

// ============================================================================ BehaviorFactory
std::future<AssetBundle> BehaviorFactory::generateFromJson(const std::string& jsonPath) {
    return pool().enqueue([this, jsonPath]() {
        return generateSync(ParamUtils::behaviorFromJson(readJsonFile(jsonPath)));
    });
}

std::future<AssetBundle> BehaviorFactory::generateFromParams(const BehaviorParams& params) {
    return generateAsync(params);
}

std::vector<std::future<AssetBundle>> BehaviorFactory::generateBatch(
    const std::vector<BehaviorParams>& params) {
    std::vector<std::future<AssetBundle>> futures;
    futures.reserve(params.size());

    for (const auto& param : params) {
        futures.push_back(generateAsync(param));
    }

    return futures;
}

bool BehaviorFactory::validateParams(const BehaviorParams& params) {
    return params.speed >= 0.0f &&
           params.detectionRange >= 0.0f &&
           params.attackRange >= 0.0f &&
           params.aggression >= 0.0f &&
           params.aggression <= 1.0f &&
           params.packSize >= 1;
}

std::string BehaviorFactory::getValidationErrors(const BehaviorParams& params) {
    std::string errors;

    if (params.speed < 0.0f) {
        errors += "speed must be non-negative\n";
    }
    if (params.detectionRange < 0.0f) {
        errors += "detectionRange must be non-negative\n";
    }
    if (params.attackRange < 0.0f) {
        errors += "attackRange must be non-negative\n";
    }
    if (params.aggression < 0.0f || params.aggression > 1.0f) {
        errors += "aggression must be between 0 and 1\n";
    }
    if (params.packSize < 1) {
        errors += "packSize must be at least 1\n";
    }

    return errors;
}

} // namespace SegmentedCreatures
} // namespace MagiTech
