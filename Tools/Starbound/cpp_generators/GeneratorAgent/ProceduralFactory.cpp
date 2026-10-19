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
float baseRadius(const SegmentedCreatureParams& p) { return std::max(p.segmentRadius, 0.01f); }
float quality(const SegmentedCreatureParams& p) { return std::clamp(p.generationQuality, 0.25f, 2.0f); }
int qualitySides(const SegmentedCreatureParams& p, int base) {
    return std::clamp(static_cast<int>(std::lround(static_cast<float>(base) * quality(p))), 4, 48);
}

/** Explicit seed when given, otherwise derived from the id and the parameters. */
uint32_t creatureSeed(const SegmentedCreatureParams& p) {
    if (p.seed != 0) return p.seed;
    return Noise::seedFromString(p.id) ^ static_cast<uint32_t>(p.hashKey() & 0xFFFFFFFFu);
}

/** Maximum joint bend in radians: stiffness-derived limit capped by jointLimit (degrees). */
float jointLimitRadians(const SegmentedCreatureParams& p) {
    const float fromStiffness = glm::radians(glm::mix(60.0f, 8.0f, std::clamp(p.articulationStiffness, 0.0f, 1.0f)));
    const float cap = glm::radians(std::clamp(p.jointLimit, 0.0f, 180.0f));
    return std::min(fromStiffness, cap);
}

/** Radius multiplier along the body; t = 0 at the head, 1 at the tail. */
float taperAt(const SegmentedCreatureParams& p, float t, uint32_t seed) {
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
        case TaperProfile::BELL_CURVE:
            scale = 0.55f + 0.45f * std::sin(kPi * t);      // thin ends, thick middle
            break;
        case TaperProfile::STEPPED:
            scale = 1.0f - 0.7f * std::floor(t * 4.0f) / 4.0f;   // four discrete radius bands
            break;
        case TaperProfile::IRREGULAR:
            scale = (1.0f - 0.6f * t) * (1.0f + 0.25f * Noise::value3(glm::vec3(t * 6.0f, 0.5f, 0.5f), seed));
            break;
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
    const uint32_t seed = creatureSeed(p);
    std::vector<SegmentFrame> frames(static_cast<size_t>(count));
    for (int i = 0; i < count; ++i) {
        SegmentFrame& f = frames[static_cast<size_t>(i)];
        const float s = static_cast<float>(i) * pitch;
        f.start = spinePoint(p, s);
        f.end = spinePoint(p, s + std::max(p.segmentLength, 0.01f));
        f.direction = glm::normalize(f.end - f.start);
        const glm::vec3 side = glm::normalize(glm::cross(f.direction, glm::vec3(0.0f, 1.0f, 0.0f)));
        f.up = glm::normalize(glm::cross(side, f.direction));
        f.taper = taperAt(p, count > 1 ? static_cast<float>(i) / static_cast<float>(count - 1) : 0.0f, seed);
        if (p.proceduralVariation) {
            // Seeded +-8% per-segment size variation.
            f.taper *= 1.0f + 0.08f * (Noise::hash3(i, 11, 0, seed) * 2.0f - 1.0f);
        }
    }
    return frames;
}

/** Bone layout shared by RigGen and AnimGen so animation tracks always match the skeleton. */
struct BoneLayout {
    int segmentBones = 0;
    int headFirst = -1;
    int headCount = 0;
    int tailFirst = -1;
    int tailCount = 0;
    int total = 0;
};

BoneLayout boneLayout(const SegmentedCreatureParams& p) {
    BoneLayout layout;
    layout.segmentBones = clampedSegmentCount(p);
    layout.total = layout.segmentBones;
    if (p.headType != HeadType::SIMPLE) {
        layout.headFirst = layout.total;
        layout.headCount = std::max(1, p.headSegmentCount);
        layout.total += layout.headCount;
    }
    if (p.tailType != TailType::NONE) {
        layout.tailFirst = layout.total;
        layout.tailCount = std::max(1, p.tailSegmentCount);
        layout.total += layout.tailCount;
    }
    return layout;
}

/** Neck segments and head placement in front of the first body segment. */
struct HeadLayout {
    glm::vec3 forward{1.0f, 0.0f, 0.0f};
    glm::vec3 up{0.0f, 1.0f, 0.0f};
    glm::vec3 side{0.0f, 0.0f, 1.0f};
    std::vector<glm::vec3> neckCenters;
    std::vector<float> neckRadii;
    glm::vec3 center{0.0f};
    float radius = 0.1f;
};

HeadLayout headLayout(const SegmentedCreatureParams& p, const SegmentFrame& front) {
    HeadLayout h;
    h.forward = -front.direction;
    h.up = front.up;
    h.side = glm::normalize(glm::cross(h.forward, h.up));
    const float bodyRadius = baseRadius(p) * front.taper;
    h.radius = bodyRadius * std::max(p.headScale, 0.1f);
    const int segments = std::max(1, p.headSegmentCount);
    const float step = (bodyRadius + h.radius) * 0.45f;
    for (int k = 1; k < segments; ++k) {
        const float t = static_cast<float>(k) / static_cast<float>(segments);
        h.neckCenters.push_back(front.start + h.forward * (step * static_cast<float>(k)));
        h.neckRadii.push_back(glm::mix(bodyRadius, h.radius, t) * 0.85f);
    }
    h.center = front.start + h.forward * (step * static_cast<float>(segments - 1) + h.radius * 0.6f);
    return h;
}

float tailRadius(const SegmentedCreatureParams& p, const SegmentFrame& back) {
    return baseRadius(p) * back.taper * std::max(p.tailScale, 0.1f);
}

/** Centre line of the tail behind the last segment, shared by the mesh and the rig. */
std::vector<glm::vec3> tailCurve(const SegmentedCreatureParams& p, const SegmentFrame& back, int points) {
    const float r = tailRadius(p, back);
    const float lengthScale = 1.0f + 0.5f * static_cast<float>(std::max(1, p.tailSegmentCount) - 1);
    const glm::vec3 dir = back.direction;
    const glm::vec3 up = back.up;
    const glm::vec3 side = glm::normalize(glm::cross(up, dir));
    std::vector<glm::vec3> curve;
    points = std::max(points, 2);
    for (int k = 0; k < points; ++k) {
        const float t = static_cast<float>(k) / static_cast<float>(points - 1);
        glm::vec3 offset(0.0f);
        switch (p.tailType) {
            case TailType::NONE:
                break;
            case TailType::SPIKE:
                offset = dir * (4.0f * r * lengthScale * t);
                break;
            case TailType::FLARED:
            case TailType::MECHANICAL:
                offset = dir * (3.0f * r * lengthScale * t);
                break;
            case TailType::TENTACLE:
                offset = dir * (5.0f * r * lengthScale * t) + side * (0.6f * r * std::sin(3.0f * kPi * t) * t);
                break;
            case TailType::CRYSTAL:
                offset = dir * (3.5f * r * lengthScale * t);
                break;
            case TailType::BIOLUMINESCENT:
                offset = dir * (3.0f * r * lengthScale * t) + up * (2.0f * r * lengthScale * t * t);   // lure stalk
                break;
            case TailType::VENOMOUS: {
                const float a = kPi * 0.9f * t;   // scorpion arc up and over the body
                offset = dir * (2.5f * r * lengthScale * std::sin(a)) + up * (2.5f * r * lengthScale * (1.0f - std::cos(a)));
                break;
            }
        }
        curve.push_back(back.end + offset);
    }
    return curve;
}

std::vector<float> taperedRadii(size_t points, float start, float endFraction) {
    std::vector<float> radii;
    for (size_t k = 0; k < points; ++k) {
        const float t = points > 1 ? static_cast<float>(k) / static_cast<float>(points - 1) : 0.0f;
        radii.push_back(start * (1.0f - (1.0f - endFraction) * t));
    }
    return radii;
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

/** Emissive strength: explicit materialEmissive, at least 0.6 for bioluminescent tails. */
float emissiveStrength(const SegmentedCreatureParams& p) {
    const float base = std::clamp(p.materialEmissive, 0.0f, 1.0f);
    return p.tailType == TailType::BIOLUMINESCENT ? std::max(base, 0.6f) : base;
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
MeshData createCylinderSegment(float radius, float length, int sides) {
    return Geometry::tube({glm::vec3(0.0f), glm::vec3(0.0f, 0.0f, length)}, {radius, radius}, sides, true);
}

MeshData createBoxSegment(float radius, float length) {
    // 4-sided prism rotated 45 degrees so the half-width equals `radius`.
    return Geometry::prism(glm::vec3(0.0f), glm::vec3(0.0f, 0.0f, 1.0f), radius * std::sqrt(2.0f), length, 4, kPi * 0.25f);
}

MeshData createHexagonSegment(float radius, float length) {
    return Geometry::prism(glm::vec3(0.0f), glm::vec3(0.0f, 0.0f, 1.0f), radius, length, 6);
}

MeshData createSphereSegment(float radius, float length, int sides) {
    // Bead: ellipsoid spanning the segment length.
    return Geometry::ellipsoid(glm::vec3(0.0f, 0.0f, length * 0.5f), glm::vec3(radius, radius, std::max(length * 0.55f, radius * 0.5f)),
                               std::max(4, sides / 2), sides);
}

MeshData createCapsuleSegment(float radius, float length, int sides) {
    MeshData mesh = Geometry::tube({glm::vec3(0.0f), glm::vec3(0.0f, 0.0f, length)}, {radius, radius}, sides, false);
    mesh.append(Geometry::sphere(glm::vec3(0.0f), radius, std::max(4, sides / 2), sides));
    mesh.append(Geometry::sphere(glm::vec3(0.0f, 0.0f, length), radius, std::max(4, sides / 2), sides));
    return mesh;
}

MeshData createPrismSegment(float radius, float length) {
    // Triangular prism with one edge on the dorsal line; scaled so the inscribed circle is ~radius.
    return Geometry::prism(glm::vec3(0.0f), glm::vec3(0.0f, 0.0f, 1.0f), radius * 1.6f, length, 3, 0.0f);
}

MeshData createIrregularSegment(float radius, float length, int sides, uint32_t seed) {
    MeshData mesh = Geometry::tube({glm::vec3(0.0f), glm::vec3(0.0f, 0.0f, length * 0.5f), glm::vec3(0.0f, 0.0f, length)},
                                   {radius, radius, radius}, sides, true);
    Geometry::displaceAlongNormals(mesh, radius * 0.25f, 2.0f / radius, seed ^ 0x1E5u, 2);
    return mesh;
}

MeshData createCustomSegment(const SegmentedCreatureParams& p, float radius, float length, int sides) {
    auto it = p.metadata.find("customMesh");
    MeshData mesh;
    if (it == p.metadata.end() || !loadObj(it->second, mesh)) {
        Log::warn("SegmentedCreature", "Custom segment mesh for '{}' unavailable ({}), using cylinder segment",
                  p.id, it == p.metadata.end() ? std::string("no metadata.customMesh") : it->second);
        return createCylinderSegment(radius, length, sides);
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
    const float radius = baseRadius(p);
    const float length = std::max(p.segmentLength, 0.01f);
    const int sides = qualitySides(p, 16);
    switch (p.segmentType) {
        case SegmentType::CYLINDER:    return createCylinderSegment(radius, length, sides);
        case SegmentType::BOX:         return createBoxSegment(radius, length);
        case SegmentType::HEXAGON:     return createHexagonSegment(radius, length);
        case SegmentType::CUSTOM_MESH: return createCustomSegment(p, radius, length, sides);
        case SegmentType::SPHERE:      return createSphereSegment(radius, length, sides);
        case SegmentType::CAPSULE:     return createCapsuleSegment(radius, length, sides);
        case SegmentType::PRISM:       return createPrismSegment(radius, length);
        case SegmentType::IRREGULAR:   return createIrregularSegment(radius, length, sides, creatureSeed(p));
    }
    return createCylinderSegment(radius, length, sides);
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
    const float radius = baseRadius(p);
    Geometry::displaceAlongNormals(mesh, p.noiseDetail * radius * 0.12f, 3.0f / radius, creatureSeed(p));
}

void addMandibleHead(MeshData& mesh, const HeadLayout& h) {
    for (int s = -1; s <= 1; s += 2) {
        const glm::vec3 root = h.center + h.side * (h.radius * 0.6f * s) - h.up * (h.radius * 0.3f) + h.forward * (h.radius * 0.5f);
        std::vector<glm::vec3> path;
        std::vector<float> radii;
        const int steps = 6;
        for (int k = 0; k <= steps; ++k) {
            const float t = static_cast<float>(k) / steps;
            // Curve forward, then hook inward.
            path.push_back(root + h.forward * (h.radius * 1.2f * t) - h.side * (h.radius * 0.55f * s * t * t));
            radii.push_back(h.radius * 0.18f * (1.0f - 0.85f * t));
        }
        mesh.append(Geometry::tube(path, radii, 6, true));
    }
}

void addMultiEyeHead(MeshData& mesh, const HeadLayout& h) {
    const int eyes = 6;
    for (int e = 0; e < eyes; ++e) {
        const float a = (static_cast<float>(e) / (eyes - 1) - 0.5f) * kPi * 0.7f;   // spread across the front
        const float row = (e % 2 == 0) ? 0.35f : 0.6f;
        const glm::vec3 dir = glm::normalize(h.forward * std::cos(a) + h.side * std::sin(a) + h.up * row);
        mesh.append(Geometry::sphere(h.center + dir * h.radius * 0.92f, h.radius * 0.16f, 6, 8));
    }
}

void addHornedHead(MeshData& mesh, const HeadLayout& h) {
    for (int s = -1; s <= 1; s += 2) {
        const glm::vec3 base = h.center + h.up * (h.radius * 0.7f) + h.side * (h.radius * 0.45f * s);
        const glm::vec3 dir = glm::normalize(h.up * 0.8f - h.forward * 0.5f + h.side * (0.3f * s));
        mesh.append(Geometry::cone(base, dir, h.radius * 0.22f, h.radius * 1.4f, 10));
    }
}

void addFangedHead(MeshData& mesh, const HeadLayout& h) {
    for (int s = -1; s <= 1; s += 2) {
        const glm::vec3 base = h.center + h.forward * (h.radius * 0.7f) - h.up * (h.radius * 0.35f) + h.side * (h.radius * 0.35f * s);
        const glm::vec3 dir = glm::normalize(-h.up + h.forward * 0.3f);
        mesh.append(Geometry::cone(base, dir, h.radius * 0.12f, h.radius * 0.9f, 8));
    }
}

void addTentacledHead(MeshData& mesh, const HeadLayout& h) {
    const int tentacles = 6;
    for (int i = 0; i < tentacles; ++i) {
        const float a = kTwoPi * static_cast<float>(i) / tentacles;
        const glm::vec3 ring = std::cos(a) * h.up + std::sin(a) * h.side;
        const glm::vec3 base = h.center + h.forward * (h.radius * 0.85f) + ring * (h.radius * 0.35f);
        std::vector<glm::vec3> path;
        for (int k = 0; k < 6; ++k) {
            const float t = static_cast<float>(k) / 5.0f;
            path.push_back(base + h.forward * (h.radius * 1.6f * t) + ring * (h.radius * 0.4f * t)
                           + h.side * (h.radius * 0.15f * std::sin(kTwoPi * t + a)));
        }
        mesh.append(Geometry::tube(path, taperedRadii(path.size(), h.radius * 0.12f, 0.25f), 6, true));
    }
}

void addCrystalHead(MeshData& mesh, const HeadLayout& h) {
    const int shards = 5;
    for (int k = 0; k < shards; ++k) {
        const float spread = static_cast<float>(k) - 0.5f * static_cast<float>(shards - 1);
        const glm::vec3 dir = glm::normalize(h.up - h.forward * (0.3f + 0.1f * std::abs(spread)) + h.side * (0.35f * spread));
        const glm::vec3 base = h.center + dir * (h.radius * 0.7f);
        const float length = h.radius * (0.6f + 0.15f * (2.0f - std::abs(spread)));
        mesh.append(Geometry::prism(base, dir, h.radius * 0.15f, length, 6));
        mesh.append(Geometry::cone(base + dir * length, dir, h.radius * 0.15f, h.radius * 0.3f, 6));
    }
}

void addMechanicalHead(MeshData& mesh, const HeadLayout& h) {
    // Visor bar across the face.
    mesh.append(Geometry::prism(h.center + h.forward * (h.radius * 0.8f) + h.up * (h.radius * 0.2f) - h.side * (h.radius * 0.7f),
                                h.side, h.radius * 0.18f, h.radius * 1.4f, 4, kPi * 0.25f));
    for (int s = -1; s <= 1; s += 2) {
        // Jaw plates
        mesh.append(Geometry::prism(h.center - h.up * (h.radius * 0.45f) + h.side * (h.radius * 0.5f * s),
                                    h.forward, h.radius * 0.15f, h.radius * 1.1f, 4, kPi * 0.25f));
        // Antennae with sensor tips
        const glm::vec3 dir = glm::normalize(h.up - h.forward * 0.4f + h.side * (0.25f * s));
        const glm::vec3 base = h.center + h.up * (h.radius * 0.8f) + h.side * (h.radius * 0.3f * s);
        mesh.append(Geometry::prism(base, dir, h.radius * 0.04f, h.radius * 1.2f, 6));
        mesh.append(Geometry::sphere(base + dir * h.radius * 1.2f, h.radius * 0.08f, 4, 6));
    }
}

void attachHead(MeshData& mesh, const SegmentedCreatureParams& p, const SegmentFrame& front) {
    const HeadLayout h = headLayout(p, front);
    const int sides = qualitySides(p, 12);
    // Neck segments between the body and the head.
    for (size_t k = 0; k < h.neckCenters.size(); ++k) {
        mesh.append(Geometry::ellipsoid(h.neckCenters[k], glm::vec3(h.neckRadii[k]), std::max(4, sides / 2), sides));
    }
    // Head capsule, slightly elongated along the travel direction.
    MeshData head = Geometry::sphere(glm::vec3(0.0f), 1.0f, std::max(6, sides - 2), sides + 2);
    const glm::mat4 orient(
        glm::vec4(h.forward * h.radius * 1.15f, 0.0f),
        glm::vec4(h.up * h.radius * 0.9f, 0.0f),
        glm::vec4(h.side * h.radius, 0.0f),
        glm::vec4(h.center, 1.0f));
    head.transform(orient);
    mesh.append(head);

    switch (p.headType) {
        case HeadType::SIMPLE:
            break;   // plain rounded head (and neck) only
        case HeadType::MANDIBLE:
            addMandibleHead(mesh, h);
            break;
        case HeadType::MULTI_EYE:
            addMultiEyeHead(mesh, h);
            break;
        case HeadType::HORNED:
            addHornedHead(mesh, h);
            break;
        case HeadType::FANGED:
            addFangedHead(mesh, h);
            break;
        case HeadType::TENTACLED:
            addTentacledHead(mesh, h);
            break;
        case HeadType::CRYSTAL:
            addCrystalHead(mesh, h);
            break;
        case HeadType::MECHANICAL:
            addMechanicalHead(mesh, h);
            break;
    }
}

void attachTail(MeshData& mesh, const SegmentedCreatureParams& p, const SegmentFrame& back) {
    const float r = tailRadius(p, back);
    const glm::vec3 side = glm::normalize(glm::cross(back.up, back.direction));
    const int sides = qualitySides(p, 12);
    switch (p.tailType) {
        case TailType::NONE:
            break;
        case TailType::SPIKE: {
            const auto curve = tailCurve(p, back, 2);
            mesh.append(Geometry::cone(back.end, back.direction, r * 0.9f, glm::length(curve.back() - curve.front()), sides));
            break;
        }
        case TailType::FLARED: {
            const auto curve = tailCurve(p, back, 2);
            const glm::vec3 root = back.end;
            const glm::vec3 tip = curve.back();
            // Horizontal fan plus a smaller vertical fin.
            mesh.append(Geometry::membrane(root - side * r * 0.5f, root + side * r * 0.5f,
                                           tip + side * r * 2.2f, tip - side * r * 2.2f));
            mesh.append(Geometry::membrane(root, root + back.up * r * 0.4f,
                                           tip + back.up * r * 1.4f, tip - back.up * r * 0.2f));
            mesh.append(Geometry::cone(root - back.direction * r * 0.2f, back.direction, r * 0.6f, r * 1.2f, sides));
            break;
        }
        case TailType::TENTACLE: {
            const auto curve = tailCurve(p, back, 10);
            mesh.append(Geometry::tube(curve, taperedRadii(curve.size(), r * 0.7f, 0.12f), sides, true));
            break;
        }
        case TailType::CRYSTAL: {
            const auto curve = tailCurve(p, back, 5);
            for (size_t k = 0; k + 1 < curve.size(); ++k) {
                const glm::vec3 d = curve[k + 1] - curve[k];
                const float scale = 1.0f - 0.18f * static_cast<float>(k);
                mesh.append(Geometry::prism(curve[k], d, r * scale, glm::length(d) * 0.92f, 6));
            }
            const glm::vec3 lastDir = curve.back() - curve[curve.size() - 2];
            mesh.append(Geometry::cone(curve.back(), lastDir, r * 0.35f, r * 1.5f, 6));
            break;
        }
        case TailType::MECHANICAL: {
            const auto curve = tailCurve(p, back, 4);
            for (size_t k = 0; k + 1 < curve.size(); ++k) {
                const glm::vec3 d = curve[k + 1] - curve[k];
                const float scale = 0.9f - 0.15f * static_cast<float>(k);
                mesh.append(Geometry::prism(curve[k], d, r * scale * std::sqrt(2.0f), glm::length(d) * 0.85f, 4, kPi * 0.25f));
            }
            for (int s = -1; s <= 1; s += 2) {   // pincer claw
                mesh.append(Geometry::cone(curve.back(), glm::normalize(back.direction + side * (0.45f * s)), r * 0.25f, r * 1.3f, 5));
            }
            break;
        }
        case TailType::BIOLUMINESCENT: {
            const auto curve = tailCurve(p, back, 8);
            mesh.append(Geometry::tube(curve, taperedRadii(curve.size(), r * 0.35f, 0.6f), sides, false));
            mesh.append(Geometry::sphere(curve.back(), r * 0.8f, std::max(4, sides / 2), sides));   // glowing lure
            break;
        }
        case TailType::VENOMOUS: {
            const auto curve = tailCurve(p, back, 10);
            mesh.append(Geometry::tube(curve, taperedRadii(curve.size(), r * 0.8f, 0.5f), sides, false));
            mesh.append(Geometry::sphere(curve.back(), r * 0.6f, std::max(4, sides / 2), sides));     // venom bulb
            const glm::vec3 lastDir = glm::normalize(curve.back() - curve[curve.size() - 2]);
            mesh.append(Geometry::cone(curve.back() + lastDir * r * 0.4f, lastDir - back.up * 0.5f, r * 0.2f, r * 1.5f, 6));   // stinger
            break;
        }
    }
}

void addArmorPlates(MeshData& mesh, const SegmentedCreatureParams& p, const std::vector<SegmentFrame>& frames) {
    const int detail = std::clamp(p.plateDetailLevel, 0, 3);
    if (detail == 0) return;
    const float arc = kPi * (0.6f + 0.15f * detail);
    const int arcSegments = std::max(2, static_cast<int>(std::lround(4.0f * (detail + 1) * quality(p))));
    const float thickness = std::max(p.armorThickness, 0.005f);
    const float segmentLength = std::max(p.segmentLength, 0.01f);
    const float gap = std::clamp(p.plateSpacing, 0.0f, 0.9f);
    // Box segments have corners at radius*sqrt(2); keep plates clear of them.
    const float shapeScale = (p.segmentType == SegmentType::BOX || p.segmentType == SegmentType::PRISM) ? std::sqrt(2.0f) : 1.0f;
    for (size_t i = 0; i < frames.size(); ++i) {
        const auto& f = frames[i];
        float length = segmentLength * (1.0f - gap);
        float offset = segmentLength * gap * 0.5f;
        float radius = baseRadius(p) * f.taper * shapeScale * 1.04f;
        if (p.plateOverlap) {
            // Plates bridge the segment gap and overlap their neighbours; alternate radii avoid z-fighting.
            length = segmentLength * 1.15f + std::max(p.segmentSpacing, 0.0f);
            offset = -segmentLength * 0.075f;
            if (i % 2 == 1) radius += thickness;
        }
        Geometry::Frame frame;
        frame.origin = f.start + f.direction * offset;
        frame.tangent = f.direction;
        frame.normal = f.up;
        frame.binormal = glm::cross(f.direction, f.up);
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
        const float radius = baseRadius(p) * f.taper;
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

uint32_t textureSize(const SegmentedCreatureParams& p) {
    const float base = static_cast<float>(64u << std::clamp(p.plateDetailLevel, 0, 2));
    return static_cast<uint32_t>(std::clamp(std::lround(base * quality(p)), 32L, 1024L));
}

// Texture layout matches the segment UVs: x = around the body (0 = dorsal, 0.5 = ventral),
// y = along one segment (0 = front edge, 1 = back edge).
TextureData generateBaseTexture(const SegmentedCreatureParams& p, uint32_t size) {
    TextureData texture(size, size);
    const glm::vec3 primary = toVec3(p.colorPrimary);
    const glm::vec3 secondary = toVec3(p.colorSecondary);
    const glm::vec3 accent = toVec3(p.colorAccent);
    const uint32_t seed = creatureSeed(p);
    const float alpha = 1.0f - std::clamp(p.materialTransparency, 0.0f, 1.0f);
    for (uint32_t y = 0; y < size; ++y) {
        for (uint32_t x = 0; x < size; ++x) {
            const float u = (x + 0.5f) / size;
            const float v = (y + 0.5f) / size;
            const float belly = 0.5f - 0.5f * std::cos(kTwoPi * u);       // 0 dorsal -> 1 ventral
            glm::vec3 color = glm::mix(primary, secondary, glm::smoothstep(0.35f, 0.75f, belly));
            // Dorsal accent stripe.
            const float stripe = 1.0f - glm::smoothstep(0.015f, 0.04f, std::min(u, 1.0f - u));
            color = glm::mix(color, accent, stripe * 0.6f);
            const float grain = Noise::fbm3(glm::vec3(u * 8.0f, v * 8.0f, 0.0f), 4, seed);
            const float variation = Noise::value3(glm::vec3(u * 3.0f, v * 3.0f, 1.5f), seed + 5u);
            color *= 1.0f + grain * (0.08f + 0.15f * p.noiseDetail) + variation * std::clamp(p.colorVariation, 0.0f, 1.0f);
            texture.set(x, y, glm::vec4(color, alpha));
        }
    }
    return texture;
}

void applyArmorPattern(TextureData& texture, const SegmentedCreatureParams& p) {
    const int detail = std::clamp(p.plateDetailLevel, 0, 3);
    if (detail == 0) return;
    const uint32_t seed = creatureSeed(p) + 77u;
    const glm::vec3 accent = toVec3(p.colorAccent);
    const float seamWidth = 0.06f / detail;
    for (uint32_t y = 0; y < texture.height; ++y) {
        for (uint32_t x = 0; x < texture.width; ++x) {
            const float u = (x + 0.5f) / texture.width;
            const float v = (y + 0.5f) / texture.height;
            const glm::vec4 c = texture.get(x, y);
            glm::vec3 color(c);
            // Plate seams at the segment boundaries, with an accent-coloured rim just inside.
            const float edge = std::min(v, 1.0f - v);
            if (edge < seamWidth) {
                color *= 0.55f + 0.45f * (edge / seamWidth);
            } else if (edge < seamWidth * 1.6f) {
                color = glm::mix(color, accent, 0.35f);
            }
            // Scales inside each plate from medium detail up.
            if (detail >= 2) {
                const float cell = Noise::worley2(glm::vec2(u * 6.0f * detail, v * 3.0f * detail), seed);
                color *= 0.85f + 0.15f * glm::smoothstep(0.05f, 0.45f, cell);
            }
            // Accent rivets along the plate rim at high detail.
            if (detail >= 3) {
                const float rivetU = std::fmod(u * 16.0f, 1.0f) - 0.5f;
                const float rivetV = v - 0.15f;
                if (rivetU * rivetU + rivetV * rivetV * 4.0f < 0.02f) color = glm::mix(color, accent, 0.8f);
            }
            texture.set(x, y, glm::vec4(color, c.a));
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

float luminance(const glm::vec4& c) { return glm::dot(glm::vec3(c), glm::vec3(0.299f, 0.587f, 0.114f)); }

glm::vec4 gray(float value) { return glm::vec4(glm::vec3(std::clamp(value, 0.0f, 1.0f)), 1.0f); }

} // namespace

TextureHandle build(const SegmentedCreatureParams& p) {
    TextureData baseTexture = generateBaseTexture(p, textureSize(p));

    if (p.armorPlates) {
        applyArmorPattern(baseTexture, p);
    }

    applyMaterialProperties(baseTexture, p.materialRoughness, p.materialMetallic);

    return AssetStore::instance().addTexture(std::move(baseTexture));
}

void buildMaterialMaps(const SegmentedCreatureParams& p, AssetBundle& bundle) {
    auto& store = AssetStore::instance();
    const auto albedo = store.texture(bundle.texture);
    if (!albedo || albedo->empty()) return;
    const uint32_t w = albedo->width, h = albedo->height;
    const int wi = static_cast<int>(w), hi = static_cast<int>(h);
    auto H = [&](int x, int y) {
        return luminance(albedo->get(static_cast<uint32_t>((x % wi + wi) % wi), static_cast<uint32_t>((y % hi + hi) % hi)));
    };

    TextureData normal(w, h), rough(w, h), metal(w, h), ao(w, h);
    for (int y = 0; y < hi; ++y) {
        for (int x = 0; x < wi; ++x) {
            const float here = H(x, y);
            // Sobel normal from the albedo luminance.
            const float dx = (H(x + 1, y - 1) + 2.0f * H(x + 1, y) + H(x + 1, y + 1)) -
                             (H(x - 1, y - 1) + 2.0f * H(x - 1, y) + H(x - 1, y + 1));
            const float dy = (H(x - 1, y + 1) + 2.0f * H(x, y + 1) + H(x + 1, y + 1)) -
                             (H(x - 1, y - 1) + 2.0f * H(x, y - 1) + H(x + 1, y - 1));
            const glm::vec3 n = glm::normalize(glm::vec3(-dx * 2.0f, -dy * 2.0f, 1.0f));
            normal.set(static_cast<uint32_t>(x), static_cast<uint32_t>(y), glm::vec4(n * 0.5f + 0.5f, 1.0f));
            // Darker crevices (seams) are rougher and less metallic.
            rough.set(static_cast<uint32_t>(x), static_cast<uint32_t>(y), gray(p.materialRoughness + (0.5f - here) * 0.3f));
            metal.set(static_cast<uint32_t>(x), static_cast<uint32_t>(y), gray(p.materialMetallic * (0.8f + 0.4f * here)));
            // Ambient occlusion: lower than the neighbourhood average means occluded.
            float sum = 0.0f;
            for (int oy = -2; oy <= 2; ++oy) {
                for (int ox = -2; ox <= 2; ++ox) sum += H(x + ox, y + oy);
            }
            ao.set(static_cast<uint32_t>(x), static_cast<uint32_t>(y), gray(1.0f - std::max(0.0f, sum / 25.0f - here) * 4.0f));
        }
    }
    rough.roughness = std::clamp(p.materialRoughness, 0.0f, 1.0f);
    metal.metallic = std::clamp(p.materialMetallic, 0.0f, 1.0f);
    bundle.normalMap = store.addTexture(std::move(normal));
    bundle.roughnessMap = store.addTexture(std::move(rough));
    bundle.metallicMap = store.addTexture(std::move(metal));
    bundle.aoMap = store.addTexture(std::move(ao));

    const float glow = emissiveStrength(p);
    if (glow > 0.0f) {
        const glm::vec3 accent = toVec3(p.colorAccent);
        const uint32_t seed = creatureSeed(p) + 313u;
        TextureData emissive(w, h);
        for (uint32_t y = 0; y < h; ++y) {
            for (uint32_t x = 0; x < w; ++x) {
                const float u = (x + 0.5f) / w;
                const float v = (y + 0.5f) / h;
                const float belly = 0.5f - 0.5f * std::cos(kTwoPi * u);
                const float spots = 1.0f - glm::smoothstep(0.1f, 0.25f, Noise::worley2(glm::vec2(u * 8.0f, v * 4.0f), seed));
                const float pattern = std::max(glm::smoothstep(0.7f, 0.95f, belly), spots * 0.8f);   // ventral glow + photophores
                emissive.set(x, y, glm::vec4(accent * glow * pattern, 1.0f));
            }
        }
        bundle.emissiveMap = store.addTexture(std::move(emissive));
    }
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

float headReach(HeadType type) {
    switch (type) {
        case HeadType::MANDIBLE:
        case HeadType::TENTACLED:  return 2.2f;
        case HeadType::HORNED:
        case HeadType::CRYSTAL:    return 1.8f;
        case HeadType::FANGED:
        case HeadType::MECHANICAL: return 1.7f;
        case HeadType::MULTI_EYE:
        case HeadType::SIMPLE:     return 1.6f;
    }
    return 1.6f;
}

/** Neck bones (all but the last) and the head bone, following HeadLayout. */
void addHeadBones(SkeletonData& skeleton, const SegmentedCreatureParams& p, const SegmentFrame& front, int count) {
    const HeadLayout h = headLayout(p, front);
    std::vector<glm::vec3> joints{front.start};
    for (const auto& c : h.neckCenters) joints.push_back(c);
    joints.push_back(h.center + h.forward * h.radius * (headReach(p.headType) - 0.6f));
    int parent = 0;
    for (int k = 0; k < count && static_cast<size_t>(k) + 1 < joints.size(); ++k) {
        const bool last = k == count - 1;
        parent = skeleton.addBone(last ? "head" : "neck_" + std::to_string(k), parent,
                                  joints[static_cast<size_t>(k)], last ? joints.back() : joints[static_cast<size_t>(k) + 1]);
    }
}

/** Tail bones following tailCurve(). */
void addTailBones(SkeletonData& skeleton, const SegmentedCreatureParams& p, const SegmentFrame& back, int parent, int count) {
    const auto curve = tailCurve(p, back, count + 1);
    for (int k = 0; k < count; ++k) {
        parent = skeleton.addBone(count == 1 ? "tail" : "tail_" + std::to_string(k), parent,
                                  curve[static_cast<size_t>(k)], curve[static_cast<size_t>(k) + 1]);
    }
}

void setJointLimits(SkeletonData& skeleton, const SegmentedCreatureParams& p) {
    const float stiffness = std::clamp(p.articulationStiffness, 0.0f, 1.0f);
    float limit = jointLimitRadians(p);
    limit *= p.enableJoints ? (0.5f + std::clamp(p.jointFlexibility, 0.0f, 1.0f)) : 0.0f;
    limit = std::min(limit, glm::radians(std::clamp(p.jointLimit, 0.0f, 180.0f)));
    for (auto& bone : skeleton.bones) {
        bone.stiffness = stiffness;
        bone.minAngle = bone.parent < 0 ? -kPi : -limit;   // root bone orients freely
        bone.maxAngle = bone.parent < 0 ? kPi : limit;
    }
}

/** Rigid-body values per bone: segment mass scales with cross-section, head/tail with their scale. */
void setPhysics(SkeletonData& skeleton, const SegmentedCreatureParams& p, const std::vector<SegmentFrame>& frames,
                const BoneLayout& layout) {
    const float unitMass = std::max(p.segmentMass, 0.0f) * std::max(p.segmentDensity, 0.0f);
    for (size_t b = 0; b < skeleton.bones.size(); ++b) {
        auto& bone = skeleton.bones[b];
        const int i = static_cast<int>(b);
        float mass = unitMass;
        if (i < layout.segmentBones) {
            mass *= frames[b].taper * frames[b].taper;
        } else if (layout.headCount > 0 && i >= layout.headFirst && i < layout.headFirst + layout.headCount) {
            mass *= std::pow(std::max(p.headScale, 0.1f), 3.0f) / static_cast<float>(layout.headCount);
        } else if (layout.tailCount > 0 && i >= layout.tailFirst) {
            mass *= std::pow(std::max(p.tailScale, 0.1f), 3.0f) / static_cast<float>(layout.tailCount);
        }
        bone.mass = mass;
        bone.friction = std::clamp(p.segmentFriction, 0.0f, 1.0f);
        bone.restitution = std::clamp(p.segmentRestitution, 0.0f, 1.0f);
    }
}

} // namespace

SkeletonHandle build(const SegmentedCreatureParams& p) {
    const auto frames = buildSegmentFrames(p);
    const BoneLayout layout = boneLayout(p);
    SkeletonData skeleton;

    createBoneChain(skeleton, frames);
    if (layout.headCount > 0) {
        addHeadBones(skeleton, p, frames.front(), layout.headCount);
    }
    if (layout.tailCount > 0) {
        addTailBones(skeleton, p, frames.back(), layout.segmentBones - 1, layout.tailCount);
    }
    setJointLimits(skeleton, p);
    setPhysics(skeleton, p, frames, layout);

    return AssetStore::instance().addSkeleton(std::move(skeleton));
}

} // namespace RigGen

// ============================================================================ Animation Generation
namespace AnimGen {
namespace {

constexpr size_t kFrames = 24;

bool isHeadBone(const BoneLayout& layout, size_t bone) {
    const int b = static_cast<int>(bone);
    return layout.headCount > 0 && b >= layout.headFirst && b < layout.headFirst + layout.headCount;
}

/** Joint index along the spine used for wave phases (head chain < 0, tail chain >= segments). */
float spineIndex(const BoneLayout& layout, size_t bone) {
    const int b = static_cast<int>(bone);
    if (isHeadBone(layout, bone)) return -1.0f - static_cast<float>(b - layout.headFirst);
    if (layout.tailCount > 0 && b >= layout.tailFirst) return static_cast<float>(layout.segmentBones + (b - layout.tailFirst));
    return static_cast<float>(b);
}

float waveAmplitude(const SegmentedCreatureParams& p, float maxDegrees) {
    const float amplitude = glm::radians(maxDegrees) * (1.0f - 0.7f * std::clamp(p.articulationStiffness, 0.0f, 1.0f));
    return std::min(amplitude, jointLimitRadians(p));
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
        const float scale = isHeadBone(layout, bone) ? 0.4f : 1.0f;
        key.rotation.y = amplitude * scale * std::cos(kTwoPi * phase - k * i);
        return key;
    });
}

void createCrawlAnimation(AnimationData& animation, const SegmentedCreatureParams& p, const BoneLayout& layout) {
    const float amplitude = waveAmplitude(p, 15.0f);
    const float k = kTwoPi / std::max(3.0f, layout.segmentBones / 2.0f);
    const float lift = baseRadius(p) * 0.6f;
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
    const float bend = std::min(perJoint, jointLimitRadians(p));
    animation.addSampledClip("coil", cycleDuration(p) * 2.0f, true, kFrames, [&](size_t bone, float phase) {
        BoneKey key;
        const float amount = 0.5f - 0.5f * std::cos(kTwoPi * phase);    // curl in, then release
        const bool spine = static_cast<int>(bone) < layout.segmentBones;
        key.rotation.y = spine && bone > 0 ? bend * amount : 0.0f;
        key.rotation.x = isHeadBone(layout, bone) ? -0.3f * amount : 0.0f;  // head rears up
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

void createBurrowAnimation(AnimationData& animation, const SegmentedCreatureParams& p, const BoneLayout& layout) {
    const float amplitude = waveAmplitude(p, 30.0f);
    const float k = kTwoPi / std::max(4.0f, layout.segmentBones / 1.5f);
    const float depth = baseRadius(p) * 2.0f;
    const float segments = static_cast<float>(std::max(1, layout.segmentBones));
    animation.addSampledClip("burrow", cycleDuration(p) * 1.6f, true, kFrames, [&](size_t bone, float phase) {
        BoneKey key;
        const float i = spineIndex(layout, bone);
        key.rotation.x = amplitude * std::sin(kTwoPi * phase - k * i);   // head-first dive and surface
        // Segments follow the head below the surface one after another.
        key.translation.y = -depth * std::max(0.0f, std::sin(kTwoPi * (phase - 0.5f * std::max(i, 0.0f) / segments)));
        return key;
    });
}

void createSwimAnimation(AnimationData& animation, const SegmentedCreatureParams& p, const BoneLayout& layout) {
    const float amplitude = waveAmplitude(p, 18.0f);
    const float k = kTwoPi / std::max(6.0f, static_cast<float>(layout.segmentBones));
    const float segments = static_cast<float>(std::max(1, layout.segmentBones));
    animation.addSampledClip("swim", cycleDuration(p) * 0.8f, true, kFrames, [&](size_t bone, float phase) {
        BoneKey key;
        const float i = spineIndex(layout, bone);
        const float growth = 0.4f + 0.6f * std::clamp(i / segments, 0.0f, 1.0f);   // amplitude grows toward the tail
        key.rotation.y = amplitude * growth * std::sin(kTwoPi * phase - k * i);
        return key;
    });
}

void createFlyAnimation(AnimationData& animation, const SegmentedCreatureParams& p, const BoneLayout& layout) {
    const float amplitude = waveAmplitude(p, 12.0f);
    const float k = kTwoPi / std::max(5.0f, layout.segmentBones / 1.2f);
    const float bob = baseRadius(p) * 0.8f;
    animation.addSampledClip("fly", cycleDuration(p) * 1.2f, true, kFrames, [&](size_t bone, float phase) {
        BoneKey key;
        const float i = spineIndex(layout, bone);
        key.rotation.x = amplitude * std::sin(kTwoPi * phase - k * i);           // airborne serpent undulation
        key.rotation.y = glm::radians(5.0f) * std::cos(kTwoPi * phase - 0.5f * k * i);
        key.translation.y = bob * std::sin(kTwoPi * phase - 0.3f * i);
        return key;
    });
}

void createClimbAnimation(AnimationData& animation, const SegmentedCreatureParams& p, const BoneLayout& layout) {
    const int lifted = std::max(1, layout.segmentBones / 2);
    const float bend = std::min(kPi * 0.5f / static_cast<float>(lifted), jointLimitRadians(p));
    const float grip = waveAmplitude(p, 6.0f);
    animation.addSampledClip("climb", cycleDuration(p) * 1.5f, true, kFrames, [&](size_t bone, float phase) {
        BoneKey key;
        const float i = spineIndex(layout, bone);
        const float amount = 0.6f + 0.4f * std::sin(kTwoPi * phase);
        // Front half bends upward onto the wall, the rest pushes; small lateral grip wave.
        if (i < static_cast<float>(lifted)) key.rotation.x = -bend * amount;
        key.rotation.y = grip * std::sin(kTwoPi * phase * 2.0f - 0.8f * i);
        return key;
    });
}

void createIdleAnimation(AnimationData& animation, const SegmentedCreatureParams& p, const BoneLayout& layout) {
    const float breathe = baseRadius(p) * 0.05f;
    animation.addSampledClip("idle", 2.5f, true, kFrames, [&](size_t bone, float phase) {
        BoneKey key;
        const float i = spineIndex(layout, bone);
        key.translation.y = breathe * std::sin(kTwoPi * phase - 0.3f * i);
        key.rotation.y = std::min(glm::radians(2.0f), jointLimitRadians(p)) * std::sin(kTwoPi * phase * 0.5f - 0.2f * i);
        return key;
    });
}

} // namespace

AnimationHandle build(const SegmentedCreatureParams& p) {
    const BoneLayout layout = boneLayout(p);
    AnimationData animation;
    animation.boneCount = static_cast<size_t>(layout.total);

    switch (p.animationProfile) {
        case AnimationProfile::SLITHER:   // also WAVE_SLITHER
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
        case AnimationProfile::BURROW:
            createBurrowAnimation(animation, p, layout);
            break;
        case AnimationProfile::SWIM:
            createSwimAnimation(animation, p, layout);
            break;
        case AnimationProfile::FLY:
            createFlyAnimation(animation, p, layout);
            break;
        case AnimationProfile::CLIMB:
            createClimbAnimation(animation, p, layout);
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
    } else if (p.climber) {
        ai.addChildNode(flee, BehaviorNodeType::Action, "climbAway", {{"speed", p.speed}});
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
    if (p.climber || p.climbAbility) {
        ai.addChildNode(routine, BehaviorNodeType::Action, "preferHighGround", {{"radius", p.patrolRadius}});
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
        case AIProfile::BURROWER:
            b.behaviorName = "burrower";
            b.burrower = true;
            b.burrowDepth = 3.0f;
            b.aggression = 0.6f;
            b.detectionRange = 12.0f;
            b.chaseSpeed = 1.6f;
            b.retreatHealth = 0.3f;
            break;
        case AIProfile::CLIMBER:
            b.behaviorName = "climber";
            b.climber = true;
            b.climbAbility = true;
            b.aggression = 0.5f;
            b.patrolRadius = 15.0f;
            break;
        case AIProfile::AMBUSHER:
            b.behaviorName = "ambusher";
            b.aggression = 0.95f;
            b.detectionRange = 8.0f;     // waits until prey is close
            b.idleTime = 10.0f;
            b.chaseSpeed = 2.5f;
            b.attackDamage = 20.0f;
            b.retreatHealth = 0.35f;
            b.nocturnal = true;
            break;
        case AIProfile::GUARDIAN:
            b.behaviorName = "guardian";
            b.territorial = true;
            b.territorySize = 12.0f;
            b.aggression = 0.65f;
            b.retreatHealth = 0.0f;      // never retreats
            b.patrolRadius = 6.0f;
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
    const std::string label = !p.name.empty() ? p.name : p.id;
    behavior.behaviorName = label.empty() ? behavior.behaviorName : label + "_" + behavior.behaviorName;
    // Reach and speed scale with body size.
    behavior.attackRange = std::max(behavior.attackRange, baseRadius(p) * 3.0f * std::max(p.headScale, 0.1f));
    behavior.speed *= std::clamp(p.segmentLength * 2.0f, 0.5f, 2.0f);
    if (p.animationProfile == AnimationProfile::BURROW) behavior.burrower = true;
    if (p.animationProfile == AnimationProfile::CLIMB) behavior.climber = true;
    if (p.animationProfile == AnimationProfile::SWIM) behavior.swimmer = true;
    if (p.animationProfile == AnimationProfile::FLY) behavior.flyer = true;
    if (p.tailType == TailType::VENOMOUS) behavior.attackDamage *= 1.5f;

    BehaviorTreeData ai;
    createBehaviorTree(ai, behavior);
    // Body facts the runtime needs for physics and damage handling.
    const float segments = static_cast<float>(clampedSegmentCount(p));
    ai.blackboard["segmentCount"] = segments;
    ai.blackboard["bodyMass"] = std::max(p.segmentMass, 0.0f) * std::max(p.segmentDensity, 0.0f) * segments;
    ai.blackboard["damageableSegments"] = p.damageableSegments ? 1.0f : 0.0f;
    ai.blackboard["dynamicSegments"] = p.dynamicSegments ? 1.0f : 0.0f;
    return AssetStore::instance().addBehavior(std::move(ai));
}

} // namespace AIGen

void releaseBundle(const AssetBundle& bundle) {
    auto& store = AssetStore::instance();
    if (bundle.mesh) store.releaseMesh(bundle.mesh);
    if (bundle.texture) store.releaseTexture(bundle.texture);
    for (TextureHandle map : {bundle.normalMap, bundle.roughnessMap, bundle.metallicMap, bundle.emissiveMap, bundle.aoMap}) {
        if (map) store.releaseTexture(map);
    }
    if (bundle.skeleton) store.releaseSkeleton(bundle.skeleton);
    if (bundle.anim) store.releaseAnimation(bundle.anim);
    if (bundle.ai) store.releaseBehavior(bundle.ai);
}

void finalizeBundle(AssetBundle& bundle, float generationSeconds) {
    auto& store = AssetStore::instance();
    auto& r = bundle.result;
    r.generationTime = generationSeconds;
    r.memoryUsage = 0;
    if (auto mesh = store.mesh(bundle.mesh)) {
        r.vertexCount = static_cast<uint32_t>(mesh->vertices.size());
        r.triangleCount = static_cast<uint32_t>(mesh->triangleCount());
        r.memoryUsage += mesh->vertices.size() * sizeof(CreatureAssets::MeshVertex) + mesh->indices.size() * sizeof(uint32_t);
    }
    if (auto texture = store.texture(bundle.texture)) {
        r.textureSize = texture->width;
        r.memoryUsage += texture->rgba.size();
    }
    for (TextureHandle map : {bundle.normalMap, bundle.roughnessMap, bundle.metallicMap, bundle.emissiveMap, bundle.aoMap}) {
        if (auto texture = store.texture(map)) r.memoryUsage += texture->rgba.size();
    }
    if (auto skeleton = store.skeleton(bundle.skeleton)) {
        r.boneCount = static_cast<uint32_t>(skeleton->bones.size());
        r.memoryUsage += skeleton->bones.size() * sizeof(CreatureAssets::Bone);
    }
    if (auto anim = store.animation(bundle.anim)) {
        r.animationFrameCount = static_cast<uint32_t>(anim->frameCount());
        r.memoryUsage += anim->frameCount() * anim->boneCount * sizeof(BoneKey);
    }
    if (auto ai = store.behavior(bundle.ai)) {
        r.memoryUsage += ai->nodes.size() * sizeof(CreatureAssets::BehaviorNode);
    }
    r.segmentCount = bundle.isBehaviorOnly() ? 0u : static_cast<uint32_t>(clampedSegmentCount(bundle.params));
    r.success = r.errorMessage.empty() && bundle.isValid();
    if (!r.success && r.errorMessage.empty()) r.errorMessage = "one or more assets failed to generate";
    if (!r.success) {
        Log::warn("SegmentedCreature", "Generation of '{}' failed: {}", bundle.assetPath, r.errorMessage);
    }
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
    return getValidationErrors(params).empty();
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
    if (params.headScale <= 0.0f || params.tailScale <= 0.0f) {
        errors += "headScale and tailScale must be greater than 0\n";
    }
    if (params.headSegmentCount < 1 || params.tailSegmentCount < 1) {
        errors += "headSegmentCount and tailSegmentCount must be at least 1\n";
    }
    if (params.jointLimit < 0.0f || params.jointLimit > 180.0f) {
        errors += "jointLimit must be between 0 and 180 degrees\n";
    }
    if (params.segmentMass < 0.0f || params.segmentDensity <= 0.0f) {
        errors += "segmentMass must be non-negative and segmentDensity greater than 0\n";
    }
    if (params.materialTransparency < 0.0f || params.materialTransparency > 1.0f) {
        errors += "materialTransparency must be between 0 and 1\n";
    }
    if (params.generationQuality <= 0.0f || params.generationQuality > 2.0f) {
        errors += "generationQuality must be in (0, 2]\n";
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
