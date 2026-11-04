#include "MonsterGenerators.hpp"
#include "core/Log.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <stdexcept>
#include <string>

namespace MagiTech {
namespace Monsters {

using CreatureAssets::AssetStore;
using CreatureAssets::Bone;
using CreatureAssets::BoneKey;
namespace Geometry = CreatureAssets::Geometry;
namespace Noise = CreatureAssets::Noise;

namespace {

constexpr float kPi = 3.14159265358979323846f;
constexpr float kTwoPi = 2.0f * kPi;
constexpr uint32_t kTextureSize = 256;
constexpr int kLimbSides = 8;

int tessellation(ComplexityLevel complexity) {
    switch (complexity) {
        case ComplexityLevel::LOW_POLY: return 6;
        case ComplexityLevel::MEDIUM:   return 10;
        case ComplexityLevel::HIGH:     return 16;
        case ComplexityLevel::ULTRA:    return 24;
    }
    return 10;
}

uint32_t monsterSeed(const MonsterParams& p) {
    return p.seed != 0 ? p.seed : (Noise::seedFromString(p.id) ^ static_cast<uint32_t>(p.hashKey() & 0xFFFFFFFFu));
}

// How a body type spends its limbs.
struct LimbLayout {
    int legs = 0;
    int arms = 0;
    int tentacles = 0;
    bool finArms = false;   // arms rendered as fins (aquatic)
};

LimbLayout limbLayout(BodyType bodyType, int limbCount) {
    const int n = std::max(limbCount, 0);
    LimbLayout l;
    switch (bodyType) {
        case BodyType::HUMANOID:
        case BodyType::AVIAN:
        case BodyType::CRYSTALLINE:
            l.legs = std::min(2, n);
            l.arms = n - l.legs;
            break;
        case BodyType::QUADRUPED:
        case BodyType::REPTILIAN:
            l.legs = std::min(4, n);
            l.arms = n - l.legs;
            break;
        case BodyType::INSECTOID:
        case BodyType::ARACHNID:
            l.legs = n;
            break;
        case BodyType::AMORPHOUS:
        case BodyType::CEPHALOPOD:
            l.tentacles = n;
            break;
        case BodyType::AQUATIC:
            l.arms = n;
            l.finArms = true;
            break;
    }
    return l;
}

int tailChainCount(const MonsterParams& p) {
    if (p.tailType == TailType::NONE) return 0;
    if (p.tailType == TailType::MULTIPLE_TAILS) return std::max(2, p.tailCount);
    return std::max(1, p.tailCount);
}

// ---- joint layouts shared by the mesh and the rig so bones sit inside the geometry
struct LimbJoints { glm::vec3 root, mid, end; };

LimbJoints legJoints(int index, int count, float s) {
    const int pairs = (count + 1) / 2;
    const int pair = index / 2;
    const float side = (index % 2 == 0) ? 1.0f : -1.0f;
    const float z = pairs > 1 ? glm::mix(0.35f * s, -0.35f * s, static_cast<float>(pair) / (pairs - 1)) : 0.0f;
    const bool splayed = pairs > 2;
    LimbJoints j;
    j.root = glm::vec3(side * 0.12f * s, 0.45f * s, z);
    j.mid = glm::vec3(side * (0.18f + (splayed ? 0.08f : 0.0f)) * s, (0.24f + (splayed ? 0.1f : 0.0f)) * s, z + 0.03f * s);
    j.end = glm::vec3(side * (0.2f + (splayed ? 0.14f : 0.0f)) * s, 0.0f, z);
    return j;
}

LimbJoints armJoints(int index, float s) {
    const int pair = index / 2;
    const float side = (index % 2 == 0) ? 1.0f : -1.0f;
    const float y = (0.76f - 0.1f * pair) * s;
    LimbJoints j;
    j.root = glm::vec3(side * 0.2f * s, y, 0.0f);
    j.mid = glm::vec3(side * 0.26f * s, y - 0.18f * s, 0.03f * s);
    j.end = glm::vec3(side * 0.27f * s, y - 0.36f * s, 0.08f * s);
    return j;
}

struct WingJoints { glm::vec3 root, elbow, tip, trailing; };

WingJoints wingJoints(int index, float s) {
    const int pair = index / 2;
    const float side = (index % 2 == 0) ? 1.0f : -1.0f;
    const float drop = 0.08f * pair * s;
    WingJoints w;
    w.root = glm::vec3(side * 0.08f * s, 0.72f * s - drop, -0.08f * s);
    w.elbow = glm::vec3(side * 0.45f * s, 0.95f * s - drop, -0.15f * s);
    w.tip = glm::vec3(side * 0.95f * s, 0.8f * s - drop, -0.3f * s);
    w.trailing = glm::vec3(side * 0.35f * s, 0.5f * s - drop, -0.25f * s);
    return w;
}

std::vector<glm::vec3> tentaclePath(int index, int count, float s, int points) {
    const float a = kTwoPi * static_cast<float>(index) / static_cast<float>(std::max(count, 1));
    const glm::vec3 radial(std::cos(a), 0.0f, std::sin(a));
    const glm::vec3 side(-std::sin(a), 0.0f, std::cos(a));
    const glm::vec3 base = glm::vec3(0.0f, 0.25f * s, 0.0f) + radial * 0.12f * s;
    std::vector<glm::vec3> path;
    for (int k = 0; k < points; ++k) {
        const float t = static_cast<float>(k) / static_cast<float>(points - 1);
        path.push_back(base + radial * (0.05f + 0.25f * t) * s - glm::vec3(0.0f, 0.24f * t * s, 0.0f)
                       + side * 0.05f * s * std::sin(3.0f * kPi * t + a));
    }
    return path;
}

std::vector<float> taperedRadii(size_t points, float start, float endFraction) {
    std::vector<float> radii;
    for (size_t k = 0; k < points; ++k) {
        const float t = points > 1 ? static_cast<float>(k) / static_cast<float>(points - 1) : 0.0f;
        radii.push_back(start * (1.0f - (1.0f - endFraction) * t));
    }
    return radii;
}

float tailSpread(int index, int count) {
    return count > 1 ? (static_cast<float>(index) / static_cast<float>(count - 1) - 0.5f) : 0.0f;
}

glm::vec3 tailRoot(int index, int count, float s) {
    return glm::vec3(tailSpread(index, count) * 0.15f * s, 0.45f * s, -0.15f * s);
}

std::vector<glm::vec3> tailPath(const glm::vec3& root, int index, int count, float s, int points, float waviness) {
    const float spread = tailSpread(index, count);
    std::vector<glm::vec3> path;
    for (int k = 0; k < points; ++k) {
        const float t = static_cast<float>(k) / static_cast<float>(points - 1);
        path.push_back(root + glm::vec3(spread * 0.4f * s * t + waviness * 0.06f * s * std::sin(4.0f * kPi * t),
                                        -0.3f * s * t * t,
                                        -0.6f * s * t));
    }
    return path;
}

// ---- mesh queries used to attach appendages to whatever body was generated
glm::vec3 topPoint(const Mesh& mesh) {
    glm::vec3 best(0.0f);
    float y = -1e30f;
    for (const auto& v : mesh.vertices) {
        if (v.position.y > y) { y = v.position.y; best = v.position; }
    }
    return best;
}

float meshScale(const Mesh& mesh) {
    const auto [lo, hi] = mesh.bounds();
    return std::max(glm::length(hi - lo), 1e-3f);
}

void addEyesAround(Mesh& mesh, const glm::vec3& center, float headRadius, int count) {
    if (count <= 0) return;
    const int perRow = std::max(1, std::min(count, 4));
    const int rows = (count + perRow - 1) / perRow;
    const float eyeRadius = headRadius * 0.2f / std::sqrt(static_cast<float>(std::max(1, count / 2)));
    int placed = 0;
    for (int r = 0; r < rows && placed < count; ++r) {
        const int inRow = std::min(perRow, count - placed);
        for (int k = 0; k < inRow; ++k, ++placed) {
            const float yaw = inRow > 1 ? (static_cast<float>(k) / static_cast<float>(inRow - 1) - 0.5f) * 1.2f : 0.0f;
            const float pitch = 0.25f + 0.3f * static_cast<float>(r);
            const glm::vec3 dir = glm::normalize(glm::vec3(std::sin(yaw), std::sin(pitch), std::cos(yaw) * std::cos(pitch)));
            const glm::vec3 eye = center + dir * headRadius * 0.9f;
            mesh.append(Geometry::sphere(eye, eyeRadius, 6, 8));
            mesh.append(Geometry::sphere(eye + dir * eyeRadius * 0.7f, eyeRadius * 0.45f, 4, 6));   // pupil
        }
    }
}

// ---- 2D gradient noise for textures
glm::vec2 gradient(int x, int y, uint32_t seed) {
    const float a = Noise::hash3(x, y, 7, seed) * kTwoPi;
    return glm::vec2(std::cos(a), std::sin(a));
}

float perlin2(const glm::vec2& p, uint32_t seed) {
    const glm::vec2 cell = glm::floor(p);
    const glm::vec2 f = p - cell;
    const int x = static_cast<int>(cell.x), y = static_cast<int>(cell.y);
    const glm::vec2 u = f * f * f * (f * (f * 6.0f - 15.0f) + 10.0f);
    const float n00 = glm::dot(gradient(x, y, seed), f);
    const float n10 = glm::dot(gradient(x + 1, y, seed), f - glm::vec2(1.0f, 0.0f));
    const float n01 = glm::dot(gradient(x, y + 1, seed), f - glm::vec2(0.0f, 1.0f));
    const float n11 = glm::dot(gradient(x + 1, y + 1, seed), f - glm::vec2(1.0f, 1.0f));
    return glm::mix(glm::mix(n00, n10, u.x), glm::mix(n01, n11, u.x), u.y) * 1.414f;   // ~[-1,1]
}

float perlinFbm(const glm::vec2& p, int octaves, uint32_t seed) {
    float sum = 0.0f, amp = 0.5f, norm = 0.0f;
    glm::vec2 q = p;
    for (int i = 0; i < std::max(1, octaves); ++i) {
        sum += amp * perlin2(q, seed + static_cast<uint32_t>(i) * 131u);
        norm += amp;
        amp *= 0.5f;
        q *= 2.0f;
    }
    return sum / norm;
}

/** Nearest and second-nearest feature distances of a Worley grid. */
glm::vec2 worleyF1F2(const glm::vec2& p, uint32_t seed) {
    const glm::vec2 cell = glm::floor(p);
    float f1 = 8.0f, f2 = 8.0f;
    for (int dy = -1; dy <= 1; ++dy) {
        for (int dx = -1; dx <= 1; ++dx) {
            const int cx = static_cast<int>(cell.x) + dx, cy = static_cast<int>(cell.y) + dy;
            const glm::vec2 feature(cx + Noise::hash3(cx, cy, 0, seed), cy + Noise::hash3(cx, cy, 1, seed));
            const float d = glm::length(feature - p);
            if (d < f1) { f2 = f1; f1 = d; } else if (d < f2) { f2 = d; }
        }
    }
    return glm::vec2(f1, f2);
}

int octavesFor(float detail) { return 2 + static_cast<int>(std::lround(std::clamp(detail, 0.0f, 1.0f) * 4.0f)); }

template <typename Fn>
std::unique_ptr<Texture> makeTexture(Fn&& fn) {
    auto texture = std::make_unique<Texture>(kTextureSize, kTextureSize);
    for (uint32_t y = 0; y < kTextureSize; ++y) {
        for (uint32_t x = 0; x < kTextureSize; ++x) {
            texture->set(x, y, fn((x + 0.5f) / kTextureSize, (y + 0.5f) / kTextureSize));
        }
    }
    return texture;
}

glm::vec4 gray(float h) { return glm::vec4(glm::vec3(std::clamp(h, 0.0f, 1.0f)), 1.0f); }

uint32_t colorSeed(const glm::vec3& c) {
    return Noise::seedFromString(std::to_string(c.r) + "," + std::to_string(c.g) + "," + std::to_string(c.b));
}

} // namespace

// ============================================================================ MeshGen
namespace MeshGen {

std::unique_ptr<Mesh> BaseShape::create(BodyType bodyType, float size, ComplexityLevel complexity) {
    switch (bodyType) {
        case BodyType::HUMANOID:    return createHumanoid(size, complexity);
        case BodyType::QUADRUPED:   return createQuadruped(size, complexity);
        case BodyType::INSECTOID:   return createInsectoid(size, complexity);
        case BodyType::AMORPHOUS:   return createAmorphous(size, complexity);
        case BodyType::AVIAN:       return createAvian(size, complexity);
        case BodyType::AQUATIC:     return createAquatic(size, complexity);
        case BodyType::REPTILIAN:   return createReptilian(size, complexity);
        case BodyType::ARACHNID:    return createArachnid(size, complexity);
        case BodyType::CEPHALOPOD:  return createCephalopod(size, complexity);
        case BodyType::CRYSTALLINE: return createCrystalline(size, complexity);
    }
    return createHumanoid(size, complexity);
}

std::unique_ptr<Mesh> BaseShape::createHumanoid(float s, ComplexityLevel complexity) {
    const int n = tessellation(complexity);
    auto mesh = std::make_unique<Mesh>();
    mesh->append(Geometry::ellipsoid({0.0f, 0.62f * s, 0.0f}, glm::vec3(0.17f, 0.2f, 0.11f) * s, n, n + 4));   // torso
    mesh->append(Geometry::ellipsoid({0.0f, 0.44f * s, 0.0f}, glm::vec3(0.15f, 0.08f, 0.1f) * s, n, n + 4));   // pelvis
    mesh->append(Geometry::tube({{0.0f, 0.78f * s, 0.0f}, {0.0f, 0.86f * s, 0.0f}}, {0.05f * s, 0.045f * s}, n, false));
    return mesh;
}

std::unique_ptr<Mesh> BaseShape::createQuadruped(float s, ComplexityLevel complexity) {
    const int n = tessellation(complexity);
    auto mesh = std::make_unique<Mesh>();
    mesh->append(Geometry::ellipsoid({0.0f, 0.55f * s, 0.05f * s}, glm::vec3(0.18f, 0.16f, 0.38f) * s, n, n + 4));
    mesh->append(Geometry::ellipsoid({0.0f, 0.55f * s, -0.28f * s}, glm::vec3(0.17f, 0.15f, 0.15f) * s, n, n + 4));
    mesh->append(Geometry::tube({{0.0f, 0.6f * s, 0.3f * s}, {0.0f, 0.68f * s, 0.4f * s}, {0.0f, 0.72f * s, 0.45f * s}},
                                {0.08f * s, 0.07f * s, 0.06f * s}, n, false));
    return mesh;
}

std::unique_ptr<Mesh> BaseShape::createInsectoid(float s, ComplexityLevel complexity) {
    const int n = tessellation(complexity);
    auto mesh = std::make_unique<Mesh>();
    mesh->append(Geometry::ellipsoid({0.0f, 0.4f * s, 0.05f * s}, glm::vec3(0.12f, 0.1f, 0.14f) * s, n, n + 2));    // thorax
    mesh->append(Geometry::sphere({0.0f, 0.41f * s, -0.12f * s}, 0.04f * s, n / 2 + 2, n));                         // petiole
    mesh->append(Geometry::ellipsoid({0.0f, 0.43f * s, -0.36f * s}, glm::vec3(0.15f, 0.13f, 0.25f) * s, n, n + 2)); // abdomen
    return mesh;
}

std::unique_ptr<Mesh> BaseShape::createAmorphous(float s, ComplexityLevel complexity) {
    const int n = tessellation(complexity);
    auto mesh = std::make_unique<Mesh>(Geometry::sphere({0.0f, 0.4f * s, 0.0f}, 0.4f * s, n * 2, n * 2));
    Geometry::displaceAlongNormals(*mesh, 0.12f * s, 2.5f / s, 0xB10Bu, 3);
    return mesh;
}

std::unique_ptr<Mesh> BaseShape::createAvian(float s, ComplexityLevel complexity) {
    const int n = tessellation(complexity);
    auto mesh = std::make_unique<Mesh>();
    mesh->append(Geometry::ellipsoid({0.0f, 0.55f * s, 0.0f}, glm::vec3(0.14f, 0.16f, 0.22f) * s, n, n + 4));
    mesh->append(Geometry::tube({{0.0f, 0.62f * s, 0.15f * s}, {0.0f, 0.72f * s, 0.19f * s}, {0.0f, 0.8f * s, 0.22f * s}},
                                {0.06f * s, 0.05f * s, 0.045f * s}, n, false));
    return mesh;
}

std::unique_ptr<Mesh> BaseShape::createAquatic(float s, ComplexityLevel complexity) {
    const int n = tessellation(complexity);
    auto mesh = std::make_unique<Mesh>();
    mesh->append(Geometry::ellipsoid({0.0f, 0.4f * s, 0.0f}, glm::vec3(0.15f, 0.18f, 0.5f) * s, n, n + 6));
    // dorsal fin
    mesh->append(Geometry::membrane({0.0f, 0.56f * s, 0.12f * s}, {0.0f, 0.56f * s, -0.2f * s},
                                    {0.0f, 0.72f * s, -0.3f * s}, {0.0f, 0.74f * s, -0.05f * s}));
    // caudal fin
    mesh->append(Geometry::membrane({0.0f, 0.4f * s, -0.48f * s}, {0.0f, 0.62f * s, -0.72f * s},
                                    {0.0f, 0.4f * s, -0.62f * s}, {0.0f, 0.18f * s, -0.72f * s}));
    return mesh;
}

std::unique_ptr<Mesh> BaseShape::createReptilian(float s, ComplexityLevel complexity) {
    const int n = tessellation(complexity);
    auto mesh = std::make_unique<Mesh>();
    mesh->append(Geometry::ellipsoid({0.0f, 0.3f * s, 0.0f}, glm::vec3(0.16f, 0.12f, 0.45f) * s, n, n + 6));
    mesh->append(Geometry::tube({{0.0f, 0.32f * s, 0.38f * s}, {0.0f, 0.34f * s, 0.47f * s}, {0.0f, 0.36f * s, 0.55f * s}},
                                {0.09f * s, 0.075f * s, 0.065f * s}, n, false));
    return mesh;
}

std::unique_ptr<Mesh> BaseShape::createArachnid(float s, ComplexityLevel complexity) {
    const int n = tessellation(complexity);
    auto mesh = std::make_unique<Mesh>();
    mesh->append(Geometry::ellipsoid({0.0f, 0.35f * s, 0.12f * s}, glm::vec3(0.13f, 0.09f, 0.14f) * s, n, n + 2));
    mesh->append(Geometry::ellipsoid({0.0f, 0.4f * s, -0.22f * s}, glm::vec3(0.2f, 0.17f, 0.24f) * s, n, n + 2));
    return mesh;
}

std::unique_ptr<Mesh> BaseShape::createCephalopod(float s, ComplexityLevel complexity) {
    const int n = tessellation(complexity);
    auto mesh = std::make_unique<Mesh>();
    mesh->append(Geometry::ellipsoid({0.0f, 0.7f * s, -0.04f * s}, glm::vec3(0.2f, 0.32f, 0.2f) * s, n, n + 4));  // mantle
    mesh->append(Geometry::sphere({0.0f, 0.36f * s, 0.0f}, 0.17f * s, n, n + 4));                                // head bulb
    return mesh;
}

std::unique_ptr<Mesh> BaseShape::createCrystalline(float s, ComplexityLevel complexity) {
    const int shards = 3 + static_cast<int>(complexity) * 2;
    auto mesh = std::make_unique<Mesh>();
    // Central column with a pointed top.
    mesh->append(Geometry::prism({0.0f, 0.0f, 0.0f}, {0.0f, 1.0f, 0.0f}, 0.15f * s, 0.75f * s, 6));
    mesh->append(Geometry::cone({0.0f, 0.75f * s, 0.0f}, {0.0f, 1.0f, 0.0f}, 0.15f * s, 0.15f * s, 6));
    // Leaning shards around it (deterministic per size).
    const uint32_t seed = Noise::seedFromString(std::to_string(s));
    for (int i = 0; i < shards; ++i) {
        const float a = kTwoPi * (static_cast<float>(i) + Noise::hash3(i, 0, 0, seed) * 0.5f) / static_cast<float>(shards);
        const float lean = 0.35f + 0.4f * Noise::hash3(i, 1, 0, seed);
        const float length = (0.3f + 0.35f * Noise::hash3(i, 2, 0, seed)) * s;
        const float radius = (0.05f + 0.05f * Noise::hash3(i, 3, 0, seed)) * s;
        const glm::vec3 base(std::cos(a) * 0.1f * s, (0.1f + 0.3f * Noise::hash3(i, 4, 0, seed)) * s, std::sin(a) * 0.1f * s);
        const glm::vec3 dir = glm::normalize(glm::vec3(std::cos(a) * lean, 1.0f, std::sin(a) * lean));
        mesh->append(Geometry::prism(base, dir, radius, length, 6));
        mesh->append(Geometry::cone(base + dir * length, dir, radius, radius * 1.5f, 6));
    }
    return mesh;
}

void LimbGenerator::addLimbs(std::unique_ptr<Mesh>& mesh, int limbCount, BodyType bodyType, float size) {
    const LimbLayout layout = limbLayout(bodyType, limbCount);
    addLegs(mesh, layout.legs, size);
    if (layout.finArms) {
        // Pectoral fins for aquatic bodies.
        for (int i = 0; i < layout.arms; ++i) {
            const int pair = i / 2;
            const float side = (i % 2 == 0) ? 1.0f : -1.0f;
            const float z = (0.2f - 0.25f * static_cast<float>(pair)) * size;
            const glm::vec3 root(side * 0.13f * size, 0.36f * size, z);
            mesh->append(Geometry::membrane(root, root + glm::vec3(0.0f, 0.0f, -0.12f * size),
                                            root + glm::vec3(side * 0.22f * size, -0.08f * size, -0.2f * size),
                                            root + glm::vec3(side * 0.18f * size, -0.06f * size, 0.0f)));
        }
    } else {
        addArms(mesh, layout.arms, size);
    }
    addTentacles(mesh, layout.tentacles, size);
}

void LimbGenerator::addArms(std::unique_ptr<Mesh>& mesh, int armCount, float size) {
    for (int i = 0; i < armCount; ++i) {
        const LimbJoints j = armJoints(i, size);
        mesh->append(Geometry::tube({j.root, j.mid, j.end}, {0.045f * size, 0.035f * size, 0.03f * size}, kLimbSides, true));
        mesh->append(Geometry::sphere(j.end, 0.04f * size, 5, kLimbSides));   // hand
    }
}

void LimbGenerator::addLegs(std::unique_ptr<Mesh>& mesh, int legCount, float size) {
    const int pairs = (legCount + 1) / 2;
    const float thickness = 1.0f / std::sqrt(static_cast<float>(std::max(1, pairs)));
    for (int i = 0; i < legCount; ++i) {
        const LimbJoints j = legJoints(i, legCount, size);
        mesh->append(Geometry::tube({j.root, j.mid, j.end},
                                    {0.06f * size * thickness, 0.045f * size * thickness, 0.035f * size * thickness},
                                    kLimbSides, true));
        mesh->append(Geometry::ellipsoid(j.end + glm::vec3(0.0f, 0.015f * size, 0.02f * size),
                                         glm::vec3(0.04f, 0.02f, 0.06f) * size * thickness, 4, kLimbSides));   // foot
    }
}

void LimbGenerator::addWings(std::unique_ptr<Mesh>& mesh, int wingCount, float size) {
    for (int i = 0; i < wingCount; ++i) {
        const WingJoints w = wingJoints(i, size);
        mesh->append(Geometry::tube({w.root, w.elbow, w.tip}, {0.03f * size, 0.022f * size, 0.01f * size}, 6, true));
        mesh->append(Geometry::membrane(w.root, w.elbow, w.tip, w.trailing));
    }
}

void LimbGenerator::addTentacles(std::unique_ptr<Mesh>& mesh, int tentacleCount, float size) {
    for (int i = 0; i < tentacleCount; ++i) {
        const auto path = tentaclePath(i, tentacleCount, size, 9);
        mesh->append(Geometry::tube(path, taperedRadii(path.size(), 0.045f * size, 0.15f), kLimbSides, true));
    }
}

void AppendageGenerator::addHeads(std::unique_ptr<Mesh>& mesh, int headCount, int eyeCount, float size) {
    if (headCount <= 0) return;
    const auto [lo, hi] = mesh->bounds();
    const glm::vec3 extent = hi - lo;
    // Upright bodies get heads on top, long bodies at the front.
    const float forwardness = std::clamp(extent.z / std::max(extent.y, 1e-4f) - 0.5f, 0.0f, 1.0f);
    const float headRadius = 0.11f * size / std::sqrt(static_cast<float>(headCount));
    const float centerZ = (lo.z + hi.z) * 0.5f;
    for (int h = 0; h < headCount; ++h) {
        const float x = headCount > 1 ? (static_cast<float>(h) / static_cast<float>(headCount - 1) - 0.5f) * 0.26f * size : 0.0f;
        const glm::vec3 center(x, hi.y + headRadius * (0.7f - 0.5f * forwardness), glm::mix(centerZ, hi.z, forwardness));
        mesh->append(Geometry::ellipsoid(center, glm::vec3(1.0f, 1.05f, 1.15f) * headRadius, 10, 12));
        mesh->append(Geometry::ellipsoid(center + glm::vec3(0.0f, -0.55f, 0.45f) * headRadius,
                                         glm::vec3(0.7f, 0.3f, 0.6f) * headRadius, 6, 10));   // jaw
        addEyesAround(*mesh, center, headRadius, eyeCount);
    }
}

void AppendageGenerator::addHorns(std::unique_ptr<Mesh>& mesh, HornType hornType, int hornCount, float size) {
    if (hornType == HornType::NONE || hornCount <= 0 || mesh->empty()) return;
    const glm::vec3 top = topPoint(*mesh);
    for (int i = 0; i < hornCount; ++i) {
        const float offset = hornCount > 1 ? (static_cast<float>(i) / static_cast<float>(hornCount - 1) - 0.5f) : 0.0f;
        const float side = offset >= 0.0f ? 1.0f : -1.0f;
        const glm::vec3 base = top + glm::vec3(offset * 0.12f * size, -0.02f * size, 0.0f);
        const float r = 0.025f * size;
        switch (hornType) {
            case HornType::NONE:
                break;
            case HornType::SPIKE:
                mesh->append(Geometry::cone(base, glm::vec3(offset * 0.6f, 1.0f, 0.1f), r, 0.15f * size, kLimbSides));
                break;
            case HornType::CURVED: {
                std::vector<glm::vec3> path;
                for (int k = 0; k < 7; ++k) {
                    const float t = static_cast<float>(k) / 6.0f;
                    path.push_back(base + glm::vec3(side * 0.05f * t, 0.12f * std::sin(t * kPi * 0.6f), -0.14f * t * t) * size);
                }
                mesh->append(Geometry::tube(path, taperedRadii(path.size(), r, 0.1f), kLimbSides, true));
                break;
            }
            case HornType::ANTLER: {
                const std::vector<glm::vec3> main = {base, base + glm::vec3(side * 0.05f, 0.1f, -0.02f) * size,
                                                     base + glm::vec3(side * 0.12f, 0.2f, -0.05f) * size};
                mesh->append(Geometry::tube(main, {r, r * 0.7f, r * 0.35f}, 6, true));
                for (int b = 0; b < 2; ++b) {
                    const glm::vec3 fork = glm::mix(main[1], main[2], 0.4f * static_cast<float>(b));
                    mesh->append(Geometry::tube({fork, fork + glm::vec3(side * 0.02f, 0.07f, 0.05f) * size},
                                                {r * 0.5f, r * 0.2f}, 5, true));
                }
                break;
            }
            case HornType::CRYSTAL: {
                const glm::vec3 dir = glm::normalize(glm::vec3(offset * 0.4f, 1.0f, 0.0f));
                mesh->append(Geometry::prism(base, dir, r * 1.4f, 0.1f * size, 6));
                mesh->append(Geometry::cone(base + dir * 0.1f * size, dir, r * 1.4f, 0.06f * size, 6));
                break;
            }
            case HornType::TENTACLE: {
                std::vector<glm::vec3> path;
                for (int k = 0; k < 8; ++k) {
                    const float t = static_cast<float>(k) / 7.0f;
                    path.push_back(base + glm::vec3(side * 0.04f * std::sin(t * kTwoPi), 0.18f * t, 0.03f * std::cos(t * kTwoPi)) * size);
                }
                mesh->append(Geometry::tube(path, taperedRadii(path.size(), r * 0.8f, 0.2f), 6, true));
                break;
            }
            case HornType::SPIRAL: {
                std::vector<glm::vec3> path;
                for (int k = 0; k < 13; ++k) {
                    const float t = static_cast<float>(k) / 12.0f;
                    const float a = t * kTwoPi * 2.0f * side;
                    path.push_back(base + glm::vec3(0.03f * std::cos(a), 0.2f * t, 0.03f * std::sin(a)) * size);
                }
                mesh->append(Geometry::tube(path, taperedRadii(path.size(), r, 0.1f), 6, true));
                break;
            }
        }
    }
}

void AppendageGenerator::addTails(std::unique_ptr<Mesh>& mesh, TailType tailType, int tailCount, float size) {
    if (tailType == TailType::NONE) return;
    const int count = tailType == TailType::MULTIPLE_TAILS ? std::max(2, tailCount) : std::max(1, tailCount);
    const float r = 0.06f * size;
    for (int i = 0; i < count; ++i) {
        const glm::vec3 root = tailRoot(i, count, size);
        switch (tailType) {
            case TailType::NONE:
                break;
            case TailType::TAIL:
            case TailType::MULTIPLE_TAILS: {
                const auto path = tailPath(root, i, count, size, 9, 0.0f);
                mesh->append(Geometry::tube(path, taperedRadii(path.size(), r, 0.15f), kLimbSides, true));
                break;
            }
            case TailType::SPINE: {
                const auto path = tailPath(root, i, count, size, 9, 0.0f);
                mesh->append(Geometry::tube(path, taperedRadii(path.size(), r, 0.2f), kLimbSides, true));
                for (size_t k = 1; k + 1 < path.size(); ++k) {
                    const float scale = 1.0f - static_cast<float>(k) / static_cast<float>(path.size());
                    mesh->append(Geometry::cone(path[k] + glm::vec3(0.0f, r * scale * 0.8f, 0.0f),
                                                glm::vec3(0.0f, 1.0f, -0.4f), r * 0.35f * scale, r * 1.4f * scale, 5));
                }
                break;
            }
            case TailType::TENTACLE: {
                const auto path = tailPath(root, i, count, size, 12, 1.0f);
                mesh->append(Geometry::tube(path, taperedRadii(path.size(), r * 0.8f, 0.1f), kLimbSides, true));
                break;
            }
            case TailType::CRYSTAL: {
                const auto path = tailPath(root, i, count, size, 5, 0.0f);
                for (size_t k = 0; k + 1 < path.size(); ++k) {
                    const glm::vec3 dir = path[k + 1] - path[k];
                    const float scale = 1.0f - 0.2f * static_cast<float>(k);
                    mesh->append(Geometry::prism(path[k], dir, r * scale, glm::length(dir) * 0.9f, 6));
                }
                mesh->append(Geometry::cone(path.back(), path.back() - path[path.size() - 2], r * 0.4f, r * 2.0f, 6));
                break;
            }
            case TailType::FLAME: {
                for (int tongue = 0; tongue < 5; ++tongue) {
                    const float a = (static_cast<float>(tongue) / 4.0f - 0.5f) * 1.2f;
                    const glm::vec3 dir(std::sin(a) * 0.6f, 0.4f + 0.2f * std::cos(a * 3.0f), -1.0f);
                    mesh->append(Geometry::cone(root, dir, r * (1.0f - std::abs(a) * 0.4f),
                                                0.3f * size * (1.0f - std::abs(a) * 0.3f), 6));
                }
                break;
            }
        }
    }
}

void AppendageGenerator::addEyes(std::unique_ptr<Mesh>& mesh, int eyeCount, float size) {
    if (eyeCount <= 0 || mesh->empty()) return;
    const glm::vec3 top = topPoint(*mesh);
    const float headRadius = 0.11f * size;
    addEyesAround(*mesh, top - glm::vec3(0.0f, headRadius, 0.0f), headRadius, eyeCount);
}

void NoiseGenerator::applyNoise(std::unique_ptr<Mesh>& mesh, float noiseDetail, uint32_t seed) {
    if (noiseDetail <= 0.0f || mesh->empty()) return;
    const float scale = meshScale(*mesh);
    Geometry::displaceAlongNormals(*mesh, noiseDetail * 0.015f * scale, 6.0f / scale, seed, 3);
}

void NoiseGenerator::applyVertexDisplacement(std::unique_ptr<Mesh>& mesh, float intensity, uint32_t seed) {
    if (intensity <= 0.0f || mesh->empty()) return;
    const float scale = meshScale(*mesh);
    Geometry::displaceAlongNormals(*mesh, intensity * 0.04f * scale, 1.5f / scale, seed ^ 0x5bd1e995u, 1);
}

void NoiseGenerator::applySurfaceDetail(std::unique_ptr<Mesh>& mesh, float detail, uint32_t seed) {
    if (detail <= 0.0f || mesh->empty()) return;
    const float scale = meshScale(*mesh);
    Geometry::displaceAlongNormals(*mesh, detail * 0.004f * scale, 24.0f / scale, seed ^ 0x27d4eb2fu, 4);
}

MeshHandle build(const MonsterParams& params) {
    const float size = std::max(params.size, 0.05f);
    const uint32_t seed = monsterSeed(params);

    auto mesh = BaseShape::create(params.bodyType, size, params.complexity);
    AppendageGenerator::addHeads(mesh, params.headCount, params.eyeCount, size);
    AppendageGenerator::addHorns(mesh, params.hornType, params.hornCount, size);
    AppendageGenerator::addTails(mesh, params.tailType, params.tailCount, size);
    LimbGenerator::addLimbs(mesh, params.limbCount, params.bodyType, size);
    if (params.wingCount > 0) LimbGenerator::addWings(mesh, params.wingCount, size);
    if (params.tentacleCount > 0) LimbGenerator::addTentacles(mesh, params.tentacleCount, size);

    if (params.proceduralVariation) NoiseGenerator::applyVertexDisplacement(mesh, params.noiseDetail * 0.5f, seed);
    NoiseGenerator::applyNoise(mesh, params.noiseDetail, seed);
    if (params.complexity >= ComplexityLevel::HIGH) {
        NoiseGenerator::applySurfaceDetail(mesh, params.noiseDetail * std::clamp(params.generationQuality, 0.0f, 2.0f), seed);
    }

    Log::debug("Monster", "Mesh for '{}': {} vertices, {} triangles", params.id, mesh->vertices.size(), mesh->triangleCount());
    return AssetStore::instance().addMesh(std::move(*mesh));
}

} // namespace MeshGen

// ============================================================================ TextureGen
namespace TextureGen {

std::unique_ptr<Texture> BaseTexture::generate2D(float scale, float detail, uint32_t seed) {
    const int octaves = octavesFor(detail);
    return makeTexture([&](float u, float v) {
        return gray(0.5f + 0.5f * Noise::fbm3(glm::vec3(u, v, 0.0f) * (4.0f * scale), octaves, seed));
    });
}

std::unique_ptr<Texture> BaseTexture::generatePerlin(float scale, float detail, uint32_t seed) {
    const int octaves = octavesFor(detail);
    return makeTexture([&](float u, float v) {
        return gray(0.5f + 0.5f * perlinFbm(glm::vec2(u, v) * (4.0f * scale), octaves, seed));
    });
}

std::unique_ptr<Texture> BaseTexture::generateCellular(float scale, float detail, uint32_t seed) {
    return makeTexture([&](float u, float v) {
        const glm::vec2 p = glm::vec2(u, v) * (6.0f * scale);
        const float f1 = worleyF1F2(p, seed).x;
        const float grain = detail * 0.15f * perlin2(p * 4.0f, seed + 1u);
        return gray(1.0f - f1 + grain);   // bright cell centres
    });
}

std::unique_ptr<Texture> BaseTexture::generateWorley(float scale, float detail, uint32_t seed) {
    return makeTexture([&](float u, float v) {
        const glm::vec2 p = glm::vec2(u, v) * (6.0f * scale);
        const glm::vec2 f = worleyF1F2(p, seed);
        const float grain = detail * 0.15f * perlin2(p * 4.0f, seed + 2u);
        return gray(std::clamp((f.y - f.x) * 2.0f, 0.0f, 1.0f) + grain);   // ridged cell borders
    });
}

std::unique_ptr<Texture> PatternGenerator::overlayPattern(std::unique_ptr<Texture>& base, PatternType patternType,
                                                          const glm::vec3& color, float intensity) {
    auto result = std::make_unique<Texture>(*base);
    const uint32_t seed = colorSeed(color);
    std::unique_ptr<Texture> pattern;
    switch (patternType) {
        case PatternType::NONE:       return result;
        case PatternType::STRIPES:    pattern = generateStripes(1.0f, color, seed); break;
        case PatternType::SPOTS:      pattern = generateSpots(1.0f, color, seed); break;
        case PatternType::SCALES:     pattern = generateScales(1.0f, color, seed); break;
        case PatternType::SKIN:       pattern = generateSkin(1.0f, color, seed); break;
        case PatternType::CRYSTAL:    pattern = generateCrystal(1.0f, color, seed); break;
        case PatternType::GLOW:       pattern = generateGlow(1.0f, color, seed); break;
        case PatternType::CAMOUFLAGE: pattern = generateCamouflage(1.0f, color, seed); break;
    }
    if (!pattern) return result;
    const float k = std::clamp(intensity, 0.0f, 1.0f);
    for (uint32_t y = 0; y < result->height; ++y) {
        for (uint32_t x = 0; x < result->width; ++x) {
            const glm::vec4 b = result->get(x, y);
            const glm::vec4 p = pattern->sample((x + 0.5f) / result->width, (y + 0.5f) / result->height);
            result->set(x, y, glm::vec4(glm::mix(glm::vec3(b), glm::vec3(p), p.a * k), b.a));
        }
    }
    return result;
}

std::unique_ptr<Texture> PatternGenerator::generateStripes(float scale, const glm::vec3& color, uint32_t seed) {
    return makeTexture([&](float u, float v) {
        const float warp = 0.8f * perlinFbm(glm::vec2(u, v) * 3.0f, 3, seed);
        const float band = 0.5f + 0.5f * std::sin((u * 6.0f * scale + warp) * kTwoPi);
        return glm::vec4(color, glm::smoothstep(0.45f, 0.55f, band));
    });
}

std::unique_ptr<Texture> PatternGenerator::generateSpots(float scale, const glm::vec3& color, uint32_t seed) {
    return makeTexture([&](float u, float v) {
        const float f1 = worleyF1F2(glm::vec2(u, v) * (8.0f * scale), seed).x;
        return glm::vec4(color, 1.0f - glm::smoothstep(0.2f, 0.32f, f1));
    });
}

std::unique_ptr<Texture> PatternGenerator::generateScales(float scale, const glm::vec3& color, uint32_t seed) {
    return makeTexture([&](float u, float v) {
        const float rows = 10.0f * scale;
        const float row = std::floor(v * rows);
        const float shift = std::fmod(row, 2.0f) * 0.5f;
        const glm::vec2 cell(u * rows + shift, v * rows);
        const glm::vec2 local = cell - glm::floor(cell) - glm::vec2(0.5f, 0.0f);   // scale anchored at its top edge
        const float d = glm::length(local);
        const float jitter = 0.05f * Noise::hash3(static_cast<int>(std::floor(cell.x)), static_cast<int>(row), 3, seed);
        return glm::vec4(color, glm::smoothstep(0.42f + jitter, 0.52f + jitter, d));   // scale outlines
    });
}

std::unique_ptr<Texture> PatternGenerator::generateSkin(float scale, const glm::vec3& color, uint32_t seed) {
    return makeTexture([&](float u, float v) {
        const float n = perlinFbm(glm::vec2(u * 2.0f, v * 6.0f) * (3.0f * scale), 4, seed);
        return glm::vec4(color, std::pow(1.0f - std::abs(n), 6.0f) * 0.7f);   // fine wrinkles
    });
}

std::unique_ptr<Texture> PatternGenerator::generateCrystal(float scale, const glm::vec3& color, uint32_t seed) {
    return makeTexture([&](float u, float v) {
        const glm::vec2 p = glm::vec2(u, v) * (5.0f * scale);
        const glm::vec2 f = worleyF1F2(p, seed);
        const float edge = 1.0f - glm::smoothstep(0.0f, 0.08f, f.y - f.x);
        const glm::vec2 cell = glm::floor(p);
        const float facet = 0.3f * Noise::hash3(static_cast<int>(cell.x), static_cast<int>(cell.y), 5, seed);
        return glm::vec4(color, std::max(edge, facet));
    });
}

std::unique_ptr<Texture> PatternGenerator::generateGlow(float scale, const glm::vec3& color, uint32_t seed) {
    return makeTexture([&](float u, float v) {
        const float ridge = 1.0f - std::abs(perlinFbm(glm::vec2(u, v) * (4.0f * scale), 4, seed));
        return glm::vec4(color, std::pow(ridge, 8.0f));   // glowing veins
    });
}

std::unique_ptr<Texture> PatternGenerator::generateCamouflage(float scale, const glm::vec3& color, uint32_t seed) {
    return makeTexture([&](float u, float v) {
        const float n = perlinFbm(glm::vec2(u, v) * (3.0f * scale), 3, seed);
        const float coverage = n > 0.1f ? 1.0f : (n > -0.2f ? 0.5f : 0.0f);
        return glm::vec4(color, coverage);
    });
}

std::unique_ptr<Texture> MaterialGenerator::generateNormalMap(const std::unique_ptr<Texture>& heightMap) {
    auto normal = std::make_unique<Texture>(heightMap->width, heightMap->height);
    const int w = static_cast<int>(heightMap->width), h = static_cast<int>(heightMap->height);
    auto H = [&](int x, int y) {
        return heightMap->get(static_cast<uint32_t>((x % w + w) % w), static_cast<uint32_t>((y % h + h) % h)).r;
    };
    const float strength = 2.0f;
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            // Sobel gradient
            const float dx = (H(x + 1, y - 1) + 2.0f * H(x + 1, y) + H(x + 1, y + 1)) -
                             (H(x - 1, y - 1) + 2.0f * H(x - 1, y) + H(x - 1, y + 1));
            const float dy = (H(x - 1, y + 1) + 2.0f * H(x, y + 1) + H(x + 1, y + 1)) -
                             (H(x - 1, y - 1) + 2.0f * H(x, y - 1) + H(x + 1, y - 1));
            const glm::vec3 n = glm::normalize(glm::vec3(-dx * strength, -dy * strength, 1.0f));
            normal->set(static_cast<uint32_t>(x), static_cast<uint32_t>(y), glm::vec4(n * 0.5f + 0.5f, 1.0f));
        }
    }
    return normal;
}

std::unique_ptr<Texture> MaterialGenerator::generateRoughnessMap(float roughness, float variation) {
    auto map = makeTexture([&](float u, float v) {
        return gray(roughness + variation * perlinFbm(glm::vec2(u, v) * 8.0f, 3, 0x52u));
    });
    map->roughness = std::clamp(roughness, 0.0f, 1.0f);
    return map;
}

std::unique_ptr<Texture> MaterialGenerator::generateMetallicMap(float metallic, float variation) {
    auto map = makeTexture([&](float u, float v) {
        return gray(metallic + variation * perlinFbm(glm::vec2(u, v) * 8.0f, 3, 0x4Du));
    });
    map->metallic = std::clamp(metallic, 0.0f, 1.0f);
    return map;
}

std::unique_ptr<Texture> MaterialGenerator::generateEmissiveMap(float emissive, const glm::vec3& color) {
    const uint32_t seed = colorSeed(color);
    return makeTexture([&](float u, float v) {
        const float veins = std::pow(1.0f - std::abs(perlinFbm(glm::vec2(u, v) * 4.0f, 4, seed)), 6.0f);
        return glm::vec4(color * std::clamp(emissive, 0.0f, 1.0f) * (0.4f + 0.6f * veins), 1.0f);
    });
}

std::unique_ptr<Texture> MaterialGenerator::generateAOMap(const std::unique_ptr<Texture>& heightMap) {
    auto ao = std::make_unique<Texture>(heightMap->width, heightMap->height);
    const int w = static_cast<int>(heightMap->width), h = static_cast<int>(heightMap->height);
    const int radius = 3;
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            float sum = 0.0f;
            int samples = 0;
            for (int dy = -radius; dy <= radius; ++dy) {
                for (int dx = -radius; dx <= radius; ++dx) {
                    sum += heightMap->get(static_cast<uint32_t>(((x + dx) % w + w) % w),
                                          static_cast<uint32_t>(((y + dy) % h + h) % h)).r;
                    ++samples;
                }
            }
            const float here = heightMap->get(static_cast<uint32_t>(x), static_cast<uint32_t>(y)).r;
            const float occlusion = std::max(0.0f, sum / static_cast<float>(samples) - here) * 4.0f;   // crevices are darker
            ao->set(static_cast<uint32_t>(x), static_cast<uint32_t>(y), gray(1.0f - occlusion));
        }
    }
    return ao;
}

std::unique_ptr<Texture> buildHeightMap(const MonsterParams& params) {
    const uint32_t seed = monsterSeed(params);
    const float scale = std::max(params.textureScale, 0.05f);
    if (params.bodyType == BodyType::CRYSTALLINE || params.patternType == PatternType::CRYSTAL) {
        return BaseTexture::generateWorley(scale, params.noiseDetail, seed);
    }
    if (params.patternType == PatternType::SCALES || params.bodyType == BodyType::REPTILIAN) {
        return BaseTexture::generateCellular(scale, params.noiseDetail, seed);
    }
    return BaseTexture::generatePerlin(scale, params.noiseDetail, seed);
}

TextureHandle build(const MonsterParams& params) {
    auto height = buildHeightMap(params);
    const uint32_t seed = monsterSeed(params) + 99u;
    auto albedo = std::make_unique<Texture>(height->width, height->height);
    for (uint32_t y = 0; y < height->height; ++y) {
        for (uint32_t x = 0; x < height->width; ++x) {
            const float h = height->get(x, y).r;
            glm::vec3 c = glm::mix(params.colorSecondary, params.colorPrimary, glm::smoothstep(0.2f, 0.8f, h));
            const float variation = params.colorVariation *
                perlin2(glm::vec2(static_cast<float>(x), static_cast<float>(y)) / 32.0f, seed);
            c *= 1.0f + variation;
            albedo->set(x, y, glm::vec4(c, 1.0f - std::clamp(params.materialTransparency, 0.0f, 1.0f)));
        }
    }
    auto patterned = PatternGenerator::overlayPattern(albedo, params.patternType, params.colorAccent, 0.85f);
    patterned->roughness = std::clamp(params.materialRoughness, 0.0f, 1.0f);
    patterned->metallic = std::clamp(params.materialMetallic, 0.0f, 1.0f);
    return AssetStore::instance().addTexture(std::move(*patterned));
}

} // namespace TextureGen

// ============================================================================ RigGen
namespace RigGen {

SkeletonBuilder::SkeletonBuilder(float size, BodyType bodyType)
    : m_skeleton(std::make_unique<Skeleton>()), m_size(std::max(size, 0.05f)), m_bodyType(bodyType) {}

int SkeletonBuilder::rootIndex() const { return m_skeleton->bones.empty() ? -1 : 0; }

int SkeletonBuilder::chestIndex() const {
    const int spine = m_skeleton->find("spine");
    return spine >= 0 ? spine : rootIndex();
}

void SkeletonBuilder::addChain(const std::string& prefix, int parent, const std::vector<glm::vec3>& joints,
                               const std::vector<std::string>& names) {
    int previous = parent;
    for (size_t i = 0; i + 1 < joints.size() && i < names.size(); ++i) {
        previous = m_skeleton->addBone(prefix + names[i], previous, joints[i], joints[i + 1]);
    }
}

SkeletonBuilder& SkeletonBuilder::addRootBone(const std::string& name) {
    const float s = m_size;
    const int root = m_skeleton->addBone(name, -1, {0.0f, 0.42f * s, 0.0f}, {0.0f, 0.55f * s, 0.0f});
    m_skeleton->addBone("spine", root, {0.0f, 0.55f * s, 0.0f}, {0.0f, 0.8f * s, 0.0f});
    return *this;
}

SkeletonBuilder& SkeletonBuilder::addLimbChains(int limbCount, BodyType bodyType) {
    m_bodyType = bodyType;
    if (m_skeleton->bones.empty()) addRootBone("root");
    const float s = m_size;
    const LimbLayout layout = limbLayout(bodyType, limbCount);
    for (int i = 0; i < layout.legs; ++i) {
        const LimbJoints j = legJoints(i, layout.legs, s);
        addChain("leg_" + std::to_string(i) + "_", rootIndex(), {j.root, j.mid, j.end}, {"upper", "lower"});
    }
    for (int i = 0; i < layout.arms; ++i) {
        const LimbJoints j = armJoints(i, s);
        addChain("arm_" + std::to_string(i) + "_", chestIndex(), {j.root, j.mid, j.end}, {"upper", "lower"});
    }
    addTentacleBones(layout.tentacles);
    return *this;
}

SkeletonBuilder& SkeletonBuilder::addHeadBones(int headCount) {
    if (m_skeleton->bones.empty()) addRootBone("root");
    const float s = m_size;
    for (int h = 0; h < headCount; ++h) {
        const float x = headCount > 1 ? (static_cast<float>(h) / static_cast<float>(headCount - 1) - 0.5f) * 0.26f * s : 0.0f;
        const glm::vec3 neckBase(0.0f, 0.8f * s, 0.0f);
        const glm::vec3 neckTop(x, 0.88f * s, 0.0f);
        const glm::vec3 headTop(x, 1.05f * s, 0.04f * s);
        const std::string id = std::to_string(h);
        const int neck = m_skeleton->addBone("neck_" + id, chestIndex(), neckBase, neckTop);
        m_skeleton->addBone("head_" + id, neck, neckTop, headTop);
    }
    return *this;
}

SkeletonBuilder& SkeletonBuilder::addWingBones(int wingCount) {
    if (m_skeleton->bones.empty()) addRootBone("root");
    for (int i = 0; i < wingCount; ++i) {
        const WingJoints w = wingJoints(i, m_size);
        addChain("wing_" + std::to_string(i) + "_", chestIndex(), {w.root, w.elbow, w.tip}, {"upper", "lower"});
    }
    return *this;
}

SkeletonBuilder& SkeletonBuilder::addTailBones(int tailCount) {
    if (m_skeleton->bones.empty()) addRootBone("root");
    for (int t = 0; t < tailCount; ++t) {
        const auto path = tailPath(tailRoot(t, tailCount, m_size), t, tailCount, m_size, 5, 0.0f);
        addChain("tail_" + std::to_string(t) + "_", rootIndex(), path, {"0", "1", "2", "3"});
    }
    return *this;
}

SkeletonBuilder& SkeletonBuilder::addHornBones(int hornCount) {
    if (hornCount <= 0) return *this;
    if (m_skeleton->bones.empty()) addRootBone("root");
    int head = m_skeleton->find("head_0");
    if (head < 0) head = chestIndex();
    const glm::vec3 top = m_skeleton->bones[static_cast<size_t>(head)].tail;
    for (int i = 0; i < hornCount; ++i) {
        const float offset = hornCount > 1 ? (static_cast<float>(i) / static_cast<float>(hornCount - 1) - 0.5f) : 0.0f;
        const glm::vec3 base = top + glm::vec3(offset * 0.12f * m_size, -0.02f * m_size, 0.0f);
        m_skeleton->addBone("horn_" + std::to_string(i), head, base, base + glm::vec3(offset * 0.05f, 0.15f, 0.0f) * m_size);
    }
    return *this;
}

SkeletonBuilder& SkeletonBuilder::addTentacleBones(int tentacleCount) {
    if (tentacleCount <= 0) return *this;
    if (m_skeleton->bones.empty()) addRootBone("root");
    const int total = m_tentacles + tentacleCount;
    for (int i = 0; i < tentacleCount; ++i) {
        const int index = m_tentacles + i;
        const auto path = tentaclePath(index, total, m_size, 5);
        addChain("tentacle_" + std::to_string(index) + "_", rootIndex(), path, {"0", "1", "2", "3"});
    }
    m_tentacles = total;
    return *this;
}

SkeletonHandle SkeletonBuilder::finalize() {
    switch (m_bodyType) {
        case BodyType::HUMANOID:
        case BodyType::AVIAN:
        case BodyType::CRYSTALLINE:
            BonePositioner::positionHumanoidBones(m_skeleton, m_size);
            break;
        case BodyType::QUADRUPED:
        case BodyType::REPTILIAN:
        case BodyType::AQUATIC:
            BonePositioner::positionQuadrupedBones(m_skeleton, m_size);
            break;
        case BodyType::INSECTOID:
        case BodyType::ARACHNID:
            BonePositioner::positionInsectoidBones(m_skeleton, m_size);
            break;
        case BodyType::AMORPHOUS:
        case BodyType::CEPHALOPOD:
            BonePositioner::positionAmorphousBones(m_skeleton, m_size);
            break;
    }
    if (m_bodyType == BodyType::CRYSTALLINE) {
        for (auto& bone : m_skeleton->bones) bone.stiffness = 0.95f;
    }
    return AssetStore::instance().addSkeleton(*m_skeleton);
}

namespace {

bool startsWith(const std::string& s, const char* prefix) { return s.rfind(prefix, 0) == 0; }
bool endsWith(const std::string& s, const std::string& suffix) {
    return s.size() >= suffix.size() && s.compare(s.size() - suffix.size(), suffix.size(), suffix) == 0;
}

void setLimits(Bone& bone, float minDeg, float maxDeg, float stiffness) {
    bone.minAngle = glm::radians(minDeg);
    bone.maxAngle = glm::radians(maxDeg);
    bone.stiffness = stiffness;
}

/** Default joint limits by bone role. */
void applyRoleLimits(Skeleton& skeleton, float baseStiffness) {
    for (auto& bone : skeleton.bones) {
        const std::string& n = bone.name;
        if (bone.parent < 0)                                           setLimits(bone, -180.0f, 180.0f, baseStiffness);
        else if (n == "spine")                                         setLimits(bone, -30.0f, 30.0f, baseStiffness);
        else if (startsWith(n, "neck_"))                               setLimits(bone, -45.0f, 45.0f, baseStiffness);
        else if (startsWith(n, "head_"))                               setLimits(bone, -60.0f, 60.0f, baseStiffness);
        else if (startsWith(n, "leg_") && endsWith(n, "_lower"))       setLimits(bone, 0.0f, 150.0f, baseStiffness);
        else if (startsWith(n, "arm_") && endsWith(n, "_lower"))       setLimits(bone, 0.0f, 145.0f, baseStiffness);
        else if (startsWith(n, "leg_") || startsWith(n, "arm_"))       setLimits(bone, -90.0f, 90.0f, baseStiffness);
        else if (startsWith(n, "wing_"))                               setLimits(bone, -80.0f, 80.0f, baseStiffness * 0.8f);
        else if (startsWith(n, "tail_") || startsWith(n, "tentacle_")) setLimits(bone, -50.0f, 50.0f, baseStiffness * 0.5f);
        else if (startsWith(n, "horn_"))                               setLimits(bone, 0.0f, 0.0f, 1.0f);
    }
}

/**
 * Turns the upright spine / neck / head / horn chain so it runs forward (+Z) from the root,
 * lifts the head above the shoulders and moves arms/wings along with the chest.
 */
void layTorsoForward(Skeleton& skeleton, float size) {
    if (skeleton.bones.empty()) return;
    const glm::vec3 pivot = skeleton.bones[0].tail;
    auto rotate = [&](const glm::vec3& p) {
        const glm::vec3 r = p - pivot;
        return pivot + glm::vec3(r.x, -r.z, r.y);   // +90 degrees about X: +Y -> +Z
    };
    const int spine = skeleton.find("spine");
    const glm::vec3 chestBefore = spine >= 0 ? skeleton.bones[static_cast<size_t>(spine)].tail : pivot;
    const glm::vec3 chestShift = rotate(chestBefore) - chestBefore;
    const glm::vec3 lift(0.0f, 0.15f * size, 0.0f);
    for (auto& bone : skeleton.bones) {
        const std::string& n = bone.name;
        if (n == "spine") {
            bone.head = rotate(bone.head);
            bone.tail = rotate(bone.tail);
        } else if (startsWith(n, "neck_")) {
            bone.head = rotate(bone.head);
            bone.tail = rotate(bone.tail) + lift;
        } else if (startsWith(n, "head_") || startsWith(n, "horn_")) {
            bone.head = rotate(bone.head) + lift;
            bone.tail = rotate(bone.tail) + lift;
        } else if (startsWith(n, "arm_") || startsWith(n, "wing_")) {
            bone.head += chestShift;
            bone.tail += chestShift;
        }
    }
}

} // namespace

void BonePositioner::positionHumanoidBones(std::unique_ptr<Skeleton>& skeleton, float size) {
    // The humanoid rig is authored upright; keep the feet on the ground plane and set limits.
    float lowest = 0.0f;
    for (const auto& bone : skeleton->bones) lowest = std::min({lowest, bone.head.y, bone.tail.y});
    if (lowest < 0.0f) {
        for (auto& bone : skeleton->bones) {
            bone.head.y -= lowest;
            bone.tail.y -= lowest;
        }
    }
    applyRoleLimits(*skeleton, size > 3.0f ? 0.6f : 0.5f);   // big monsters move more stiffly
}

void BonePositioner::positionQuadrupedBones(std::unique_ptr<Skeleton>& skeleton, float size) {
    layTorsoForward(*skeleton, size);
    applyRoleLimits(*skeleton, 0.6f);
    for (auto& bone : skeleton->bones) {
        if (startsWith(bone.name, "leg_") && endsWith(bone.name, "_upper")) setLimits(bone, -60.0f, 60.0f, 0.6f);
    }
}

void BonePositioner::positionInsectoidBones(std::unique_ptr<Skeleton>& skeleton, float size) {
    layTorsoForward(*skeleton, size);
    // Splay the legs: knees out and up, lower segments re-attached to the moved knees.
    for (size_t i = 0; i < skeleton->bones.size(); ++i) {
        Bone& upper = skeleton->bones[i];
        if (!(startsWith(upper.name, "leg_") && endsWith(upper.name, "_upper"))) continue;
        upper.tail.x *= 1.5f;
        upper.tail.y += 0.12f * size;
        const std::string lowerName = upper.name.substr(0, upper.name.size() - 6) + "_lower";
        const int lower = skeleton->find(lowerName);
        if (lower >= 0) skeleton->bones[static_cast<size_t>(lower)].head = upper.tail;
    }
    applyRoleLimits(*skeleton, 0.65f);
    for (auto& bone : skeleton->bones) {
        if (startsWith(bone.name, "leg_")) setLimits(bone, -70.0f, 70.0f, 0.65f);
    }
}

void BonePositioner::positionAmorphousBones(std::unique_ptr<Skeleton>& skeleton, float size) {
    if (skeleton->bones.empty()) return;
    glm::vec3 centroid(0.0f);
    for (const auto& bone : skeleton->bones) centroid += (bone.head + bone.tail) * 0.5f;
    centroid /= static_cast<float>(skeleton->bones.size());
    centroid.y = std::max(centroid.y, 0.3f * size);
    for (auto& bone : skeleton->bones) {
        bone.head = glm::mix(centroid, bone.head, 0.6f);
        bone.tail = glm::mix(centroid, bone.tail, 0.6f);
        setLimits(bone, -120.0f, 120.0f, 0.1f);
    }
}

SkeletonHandle build(const MonsterParams& params) {
    SkeletonBuilder builder(params.size, params.bodyType);
    builder.addRootBone("root")
           .addLimbChains(params.limbCount, params.bodyType)
           .addHeadBones(params.headCount)
           .addWingBones(params.wingCount)
           .addTailBones(tailChainCount(params))
           .addHornBones(params.hornType == HornType::NONE ? 0 : params.hornCount)
           .addTentacleBones(params.tentacleCount);
    return builder.finalize();
}

} // namespace RigGen

// ============================================================================ AnimGen
namespace AnimGen {
namespace {

enum class Track { Root, Spine, Neck, Head, Tail, LegUpper, LegLower, ArmUpper, ArmLower, Tentacle, WingUpper, WingLower };

struct TrackInfo {
    Track kind = Track::Root;
    int chain = 0;     // limb / tail / head index
    int segment = 0;   // segment within the chain
};

constexpr int kMaxHeads = 3;
constexpr int kMaxTails = 3;
constexpr int kMaxWings = 4;
constexpr size_t kFrames = 24;

/** Named tracks matching RigGen's bone names for monsters with up to `limbCount` chains per kind. */
std::vector<TrackInfo> tracksFor(int limbCount, std::vector<std::string>* names) {
    std::vector<TrackInfo> tracks;
    auto add = [&](Track kind, int chain, int segment, const std::string& name) {
        tracks.push_back({kind, chain, segment});
        if (names) names->push_back(name);
    };
    add(Track::Root, 0, 0, "root");
    add(Track::Spine, 0, 0, "spine");
    for (int h = 0; h < kMaxHeads; ++h) {
        add(Track::Neck, h, 0, "neck_" + std::to_string(h));
        add(Track::Head, h, 0, "head_" + std::to_string(h));
    }
    for (int t = 0; t < kMaxTails; ++t) {
        for (int k = 0; k < 4; ++k) add(Track::Tail, t, k, "tail_" + std::to_string(t) + "_" + std::to_string(k));
    }
    const int n = std::max(limbCount, 0);
    for (int i = 0; i < n; ++i) {
        const std::string id = std::to_string(i);
        add(Track::LegUpper, i, 0, "leg_" + id + "_upper");
        add(Track::LegLower, i, 1, "leg_" + id + "_lower");
        add(Track::ArmUpper, i, 0, "arm_" + id + "_upper");
        add(Track::ArmLower, i, 1, "arm_" + id + "_lower");
        for (int k = 0; k < 4; ++k) add(Track::Tentacle, i, k, "tentacle_" + id + "_" + std::to_string(k));
    }
    for (int w = 0; w < kMaxWings; ++w) {
        add(Track::WingUpper, w, 0, "wing_" + std::to_string(w) + "_upper");
        add(Track::WingLower, w, 1, "wing_" + std::to_string(w) + "_lower");
    }
    return tracks;
}

std::unique_ptr<Animation> newAnimation(int limbCount) {
    auto anim = std::make_unique<Animation>();
    tracksFor(limbCount, &anim->boneNames);
    anim->boneCount = anim->boneNames.size();
    return anim;
}

template <typename PoseFn>
void addClip(Animation& anim, int limbCount, const std::string& name, float duration, bool loop, PoseFn&& pose) {
    if (anim.boneNames.empty()) {
        tracksFor(limbCount, &anim.boneNames);
        anim.boneCount = anim.boneNames.size();
    }
    const auto tracks = tracksFor(limbCount, nullptr);
    anim.addSampledClip(name, duration, loop, kFrames, [&](size_t bone, float phase) {
        return bone < tracks.size() ? pose(tracks[bone], phase) : BoneKey{};
    });
}

float rad(float degrees) { return glm::radians(degrees); }
float wave(float phase, float offset) { return std::sin(kTwoPi * (phase + offset)); }
float sideOf(int chain) { return (chain % 2 == 0) ? 1.0f : -1.0f; }

/** Alternating gait: legs on opposite sides and consecutive pairs are out of phase. */
float legOffset(int leg) { return 0.5f * static_cast<float>(leg % 2) + 0.25f * static_cast<float>(leg / 2); }
/** Tripod gait for many-legged walkers. */
float tripodOffset(int leg) { return ((leg % 2) ^ ((leg / 2) % 2)) ? 0.5f : 0.0f; }

BoneKey gaitPose(const TrackInfo& t, float phase, float legSwing, float armSwing, float bob, float size, bool tripod) {
    BoneKey key;
    switch (t.kind) {
        case Track::Root:
            key.translation.y = bob * size * std::abs(wave(phase * 2.0f, 0.0f));
            break;
        case Track::Spine:
            key.rotation.x = rad(3.0f) * wave(phase * 2.0f, 0.0f) * (bob > 0.03f ? 2.0f : 1.0f);
            break;
        case Track::Head:
            key.rotation.x = -rad(3.0f) * wave(phase * 2.0f, 0.1f);
            break;
        case Track::Tail:
            key.rotation.y = rad(10.0f) * wave(phase, -0.15f * static_cast<float>(t.segment));
            break;
        case Track::LegUpper: {
            const float off = tripod ? tripodOffset(t.chain) : legOffset(t.chain);
            key.rotation.x = rad(legSwing) * wave(phase, off);
            break;
        }
        case Track::LegLower: {
            const float off = tripod ? tripodOffset(t.chain) : legOffset(t.chain);
            key.rotation.x = rad(legSwing * 0.8f) * std::max(0.0f, wave(phase, off + 0.25f));
            break;
        }
        case Track::ArmUpper:
            key.rotation.x = -rad(armSwing) * wave(phase, legOffset(t.chain));
            break;
        case Track::ArmLower:
            key.rotation.x = rad(armSwing * 0.5f) * (0.5f + 0.5f * wave(phase, legOffset(t.chain)));
            break;
        case Track::Tentacle:
            key.rotation.y = rad(15.0f) * wave(phase, 0.12f * static_cast<float>(t.segment) + 0.2f * static_cast<float>(t.chain));
            break;
        case Track::WingUpper:
        case Track::WingLower:
            key.rotation.z = rad(5.0f) * wave(phase, 0.0f);   // folded wings bounce slightly
            break;
        case Track::Neck:
            break;
    }
    return key;
}

/** -1 during wind-up, +1 at the strike, back to 0 on recovery. */
float strikeCurve(float phase) {
    if (phase < 0.4f) return -glm::smoothstep(0.0f, 0.4f, phase);
    if (phase < 0.55f) return glm::mix(-1.0f, 1.0f, glm::smoothstep(0.4f, 0.55f, phase));
    return 1.0f - glm::smoothstep(0.55f, 1.0f, phase);
}

} // namespace

void KeyframeGenerator::generateIdleAnimation(std::unique_ptr<Animation>& anim, int limbCount, float size) {
    addClip(*anim, limbCount, "idle", 2.5f, true, [size](const TrackInfo& t, float phase) {
        BoneKey key;
        const float seg = static_cast<float>(t.segment), chain = static_cast<float>(t.chain);
        switch (t.kind) {
            case Track::Spine:     key.rotation.x = rad(2.0f) * wave(phase, 0.0f); break;   // breathing
            case Track::Root:      key.translation.y = 0.005f * size * wave(phase, 0.0f); break;
            case Track::Head:      key.rotation.y = rad(5.0f) * wave(phase * 0.5f, 0.2f * chain); break;
            case Track::Tail:      key.rotation.y = rad(8.0f) * wave(phase, -0.1f * seg); break;
            case Track::Tentacle:  key.rotation.y = rad(10.0f) * wave(phase, 0.15f * seg + 0.3f * chain); break;
            case Track::WingUpper: key.rotation.z = rad(2.0f) * wave(phase, 0.0f); break;
            default: break;
        }
        return key;
    });
}

void KeyframeGenerator::generateWalkAnimation(std::unique_ptr<Animation>& anim, int limbCount, float size) {
    const bool tripod = limbCount >= 6;
    addClip(*anim, limbCount, "walk", 1.0f, true, [=](const TrackInfo& t, float phase) {
        return gaitPose(t, phase, 25.0f, 15.0f, 0.02f, size, tripod);
    });
}

void KeyframeGenerator::generateRunAnimation(std::unique_ptr<Animation>& anim, int limbCount, float size) {
    const bool tripod = limbCount >= 6;
    addClip(*anim, limbCount, "run", 0.6f, true, [=](const TrackInfo& t, float phase) {
        return gaitPose(t, phase, 40.0f, 25.0f, 0.05f, size, tripod);
    });
}

void KeyframeGenerator::generateAttackAnimation(std::unique_ptr<Animation>& anim, int limbCount, float size) {
    addClip(*anim, limbCount, "attack", 0.8f, false, [size](const TrackInfo& t, float phase) {
        BoneKey key;
        const float s = strikeCurve(phase);
        switch (t.kind) {
            case Track::Spine:    key.rotation.x = rad(s < 0.0f ? 15.0f : 20.0f) * s; break;
            case Track::Head:     key.rotation.x = rad(10.0f) * s;
                                  key.translation.z = 0.1f * size * std::max(s, 0.0f); break;
            case Track::ArmUpper: key.rotation.x = rad(s < 0.0f ? 60.0f : 40.0f) * -s; break;
            case Track::ArmLower: key.rotation.x = rad(30.0f) * std::abs(s); break;
            case Track::Tail:     key.rotation.x = rad(15.0f) * -s; break;
            case Track::Tentacle: key.rotation.x = rad(35.0f) * s * (1.0f + 0.3f * static_cast<float>(t.segment)); break;
            case Track::Root:     key.translation.z = 0.05f * size * std::max(s, 0.0f); break;
            default: break;
        }
        return key;
    });
}

void KeyframeGenerator::generateDeathAnimation(std::unique_ptr<Animation>& anim, int limbCount, float size) {
    addClip(*anim, limbCount, "death", 1.5f, false, [size](const TrackInfo& t, float phase) {
        BoneKey key;
        const float fall = glm::smoothstep(0.0f, 0.7f, phase);
        switch (t.kind) {
            case Track::Root:
                key.rotation.z = rad(90.0f) * fall;
                key.translation.y = -0.3f * size * fall;
                break;
            case Track::Head:      key.rotation.x = rad(30.0f) * fall; break;
            case Track::LegUpper:  key.rotation.x = rad(20.0f) * fall; break;
            case Track::LegLower:  key.rotation.x = rad(40.0f) * fall; break;
            case Track::ArmUpper:  key.rotation.z = rad(30.0f) * fall; break;
            case Track::Tail:
            case Track::Tentacle:  key.rotation.x = -rad(10.0f) * fall; break;
            case Track::WingUpper: key.rotation.z = -rad(60.0f) * fall; break;
            default: break;
        }
        return key;
    });
}

namespace {
std::unique_ptr<Animation> baseClips(int limbCount, float size) {
    auto anim = newAnimation(limbCount);
    KeyframeGenerator::generateIdleAnimation(anim, limbCount, size);
    KeyframeGenerator::generateWalkAnimation(anim, limbCount, size);
    KeyframeGenerator::generateRunAnimation(anim, limbCount, size);
    KeyframeGenerator::generateAttackAnimation(anim, limbCount, size);
    KeyframeGenerator::generateDeathAnimation(anim, limbCount, size);
    return anim;
}
} // namespace

std::unique_ptr<Animation> AnimationProfile::createBeastBasic(int limbCount, float size) {
    return baseClips(limbCount, size);
}

std::unique_ptr<Animation> AnimationProfile::createPredator(int limbCount, float size) {
    auto anim = baseClips(limbCount, size);
    // Crouch, then leap forward.
    addClip(*anim, limbCount, "pounce", 1.0f, false, [size](const TrackInfo& t, float phase) {
        BoneKey key;
        const float crouch = phase < 0.4f ? glm::smoothstep(0.0f, 0.4f, phase) : 1.0f - glm::smoothstep(0.4f, 0.5f, phase);
        const float leap = phase < 0.4f ? 0.0f : std::sin(kPi * glm::clamp((phase - 0.4f) / 0.5f, 0.0f, 1.0f));
        switch (t.kind) {
            case Track::Root:
                key.translation.y = -0.1f * size * crouch + 0.35f * size * leap;
                key.translation.z = 0.8f * size * glm::smoothstep(0.4f, 0.9f, phase);
                break;
            case Track::LegUpper: key.rotation.x = rad(35.0f) * crouch - rad(30.0f) * leap; break;
            case Track::LegLower: key.rotation.x = rad(60.0f) * crouch; break;
            case Track::ArmUpper: key.rotation.x = -rad(70.0f) * leap; break;
            case Track::Head:     key.rotation.x = -rad(10.0f) * crouch; break;
            case Track::Tail:     key.rotation.x = rad(20.0f) * leap; break;
            default: break;
        }
        return key;
    });
    return anim;
}

std::unique_ptr<Animation> AnimationProfile::createPackHunter(int limbCount, float size) {
    auto anim = baseClips(limbCount, size);
    // Howl to rally the pack.
    addClip(*anim, limbCount, "howl", 2.0f, false, [](const TrackInfo& t, float phase) {
        BoneKey key;
        const float up = glm::smoothstep(0.0f, 0.3f, phase) * (1.0f - glm::smoothstep(0.8f, 1.0f, phase));
        switch (t.kind) {
            case Track::Neck:  key.rotation.x = -rad(30.0f) * up; break;
            case Track::Head:  key.rotation.x = -rad(40.0f) * up + rad(2.0f) * up * wave(phase * 6.0f, 0.0f); break;
            case Track::Spine: key.rotation.x = -rad(8.0f) * up; break;
            case Track::Tail:  key.rotation.x = rad(10.0f) * up; break;
            default: break;
        }
        return key;
    });
    return anim;
}

std::unique_ptr<Animation> AnimationProfile::createHorrorFloat(int limbCount, float size) {
    auto anim = baseClips(limbCount, size);
    addClip(*anim, limbCount, "float", 3.0f, true, [size](const TrackInfo& t, float phase) {
        BoneKey key;
        const float seg = static_cast<float>(t.segment), chain = static_cast<float>(t.chain);
        switch (t.kind) {
            case Track::Root:
                key.translation.y = 0.25f * size + 0.06f * size * wave(phase, 0.0f);
                key.rotation.z = rad(4.0f) * wave(phase, 0.25f);
                break;
            case Track::Tentacle:
                key.rotation.x = rad(25.0f) * wave(phase, 0.15f * seg + 0.25f * chain);
                key.rotation.y = rad(15.0f) * wave(phase, 0.1f * seg);
                break;
            case Track::LegUpper:
            case Track::ArmUpper:
                key.rotation.x = rad(12.0f) * wave(phase, 0.3f * chain);   // limbs drift
                break;
            case Track::Head: key.rotation.z = rad(10.0f) * wave(phase * 0.5f, 0.0f); break;
            default: break;
        }
        return key;
    });
    return anim;
}

std::unique_ptr<Animation> AnimationProfile::createInsectScuttle(int limbCount, float size) {
    auto anim = baseClips(limbCount, size);
    addClip(*anim, limbCount, "scuttle", 0.35f, true, [size](const TrackInfo& t, float phase) {
        BoneKey key = gaitPose(t, phase, 30.0f, 10.0f, 0.01f, size, true);
        if (t.kind == Track::LegUpper) key.rotation.y = rad(20.0f) * wave(phase, tripodOffset(t.chain) + 0.25f);
        return key;
    });
    return anim;
}

std::unique_ptr<Animation> AnimationProfile::createAquaticSwim(int limbCount, float size) {
    auto anim = baseClips(limbCount, size);
    addClip(*anim, limbCount, "swim", 1.2f, true, [size](const TrackInfo& t, float phase) {
        BoneKey key;
        const float seg = static_cast<float>(t.segment);
        switch (t.kind) {
            case Track::Root:     key.translation.x = 0.03f * size * wave(phase, 0.0f); break;
            case Track::Spine:    key.rotation.y = rad(8.0f) * wave(phase, 0.0f); break;
            case Track::Head:     key.rotation.y = -rad(5.0f) * wave(phase, 0.0f); break;
            case Track::Tail:     key.rotation.y = rad(25.0f + 5.0f * seg) * wave(phase, -0.12f * (seg + 1.0f)); break;
            case Track::ArmUpper: key.rotation.z = rad(25.0f) * wave(phase, 0.5f * static_cast<float>(t.chain % 2)); break;   // fins
            case Track::Tentacle: key.rotation.x = rad(20.0f) * wave(phase, 0.15f * seg); break;
            default: break;
        }
        return key;
    });
    return anim;
}

std::unique_ptr<Animation> AnimationProfile::createAvianFly(int limbCount, float size) {
    auto anim = baseClips(limbCount, size);
    addClip(*anim, limbCount, "fly", 0.7f, true, [size](const TrackInfo& t, float phase) {
        BoneKey key;
        const float side = sideOf(t.chain);
        switch (t.kind) {
            case Track::WingUpper: key.rotation.z = side * rad(50.0f) * wave(phase, 0.0f); break;
            case Track::WingLower: key.rotation.z = side * rad(30.0f) * wave(phase, -0.1f); break;
            case Track::Root:      key.translation.y = 0.04f * size * wave(phase, 0.25f); break;
            case Track::LegUpper:  key.rotation.x = -rad(40.0f); break;   // legs tucked
            case Track::LegLower:  key.rotation.x = rad(80.0f); break;
            case Track::Tail:      key.rotation.x = rad(5.0f) * wave(phase, 0.3f); break;
            default: break;
        }
        return key;
    });
    addClip(*anim, limbCount, "glide", 2.0f, true, [](const TrackInfo& t, float phase) {
        BoneKey key;
        if (t.kind == Track::WingUpper) key.rotation.z = sideOf(t.chain) * (rad(10.0f) + rad(3.0f) * wave(phase, 0.0f));
        if (t.kind == Track::LegUpper) key.rotation.x = -rad(40.0f);
        if (t.kind == Track::LegLower) key.rotation.x = rad(80.0f);
        return key;
    });
    return anim;
}

std::unique_ptr<Animation> AnimationProfile::createCrystalPulse(int limbCount, float size) {
    auto anim = baseClips(limbCount, size);
    addClip(*anim, limbCount, "pulse", 1.6f, true, [size](const TrackInfo& t, float phase) {
        BoneKey key;
        const float pulse = std::pow(std::max(0.0f, wave(phase, 0.0f)), 3.0f);
        switch (t.kind) {
            case Track::Root:  key.translation.y = 0.02f * size * pulse; break;
            case Track::Spine: key.rotation.x = rad(2.0f) * pulse; break;
            case Track::Head:  key.rotation.y = rad(6.0f) * wave(phase * 0.5f, 0.0f); break;
            case Track::ArmUpper:
            case Track::LegUpper: key.rotation.z = sideOf(t.chain) * rad(6.0f) * pulse; break;
            default: break;
        }
        return key;
    });
    return anim;
}

AnimationHandle build(const MonsterParams& params) {
    using Profile = MagiTech::Monsters::AnimationProfile;   // the enum (AnimGen::AnimationProfile is the builder class)
    const int limbs = std::max(params.limbCount, 0) + std::max(params.tentacleCount, 0);
    const float size = std::max(params.size, 0.05f);
    std::unique_ptr<Animation> anim;
    switch (params.animationProfile) {
        case Profile::BEAST_BASIC:    anim = AnimationProfile::createBeastBasic(limbs, size); break;
        case Profile::PREDATOR:       anim = AnimationProfile::createPredator(limbs, size); break;
        case Profile::PACK_HUNTER:    anim = AnimationProfile::createPackHunter(limbs, size); break;
        case Profile::HORROR_FLOAT:   anim = AnimationProfile::createHorrorFloat(limbs, size); break;
        case Profile::INSECT_SCUTTLE: anim = AnimationProfile::createInsectScuttle(limbs, size); break;
        case Profile::AQUATIC_SWIM:   anim = AnimationProfile::createAquaticSwim(limbs, size); break;
        case Profile::AVIAN_FLY:      anim = AnimationProfile::createAvianFly(limbs, size); break;
        case Profile::CRYSTAL_PULSE:  anim = AnimationProfile::createCrystalPulse(limbs, size); break;
    }
    if (!anim) anim = AnimationProfile::createBeastBasic(limbs, size);
    return AssetStore::instance().addAnimation(std::move(*anim));
}

} // namespace AnimGen

// ============================================================================ MonsterGenerator
MonsterGenerator::MonsterGenerator() = default;

MonsterGenerator::~MonsterGenerator() { shutdown(); }

void MonsterGenerator::initialize(size_t cacheSize, size_t numThreads) {
    if (m_initialized) return;
    m_cache = std::make_unique<ConcurrentLRUCache<uint64_t, MonsterAssetBundle>>(cacheSize == 0 ? 1 : cacheSize);
    m_threadPool = std::make_unique<GeneratorTaskPool>(numThreads);
    m_initialized = true;
    Log::info("Monster", "MonsterGenerator initialized (cache {}, threads {})", cacheSize, m_threadPool->size());
}

void MonsterGenerator::shutdown() {
    if (!m_initialized) return;
    if (m_threadPool) m_threadPool->stop();
    m_initialized = false;
}

std::future<MonsterAssetBundle> MonsterGenerator::generateAsync(const MonsterParams& params) {
    if (!m_initialized) initialize();
    if (params.cacheEnabled) {
        if (auto hit = m_cache->find(params.hashKey())) {
            ++m_cacheHits;
            std::promise<MonsterAssetBundle> ready;
            ready.set_value(*hit);
            return ready.get_future();
        }
    }
    return m_threadPool->enqueue([this, params] { return generate(params); });
}

MonsterAssetBundle MonsterGenerator::generate(const MonsterParams& params) {
    if (!m_initialized) initialize();
    const uint64_t key = params.hashKey();
    if (params.cacheEnabled) {
        if (auto hit = m_cache->find(key)) {
            ++m_cacheHits;
            return *hit;
        }
        ++m_cacheMisses;
    }
    MonsterAssetBundle bundle = generateMonsterAssets(params);
    if (params.cacheEnabled && bundle.result.success) m_cache->insert(key, bundle);
    return bundle;
}

MeshHandle MonsterGenerator::generateMesh(const MonsterParams& params) { return MeshGen::build(params); }
TextureHandle MonsterGenerator::generateTexture(const MonsterParams& params) { return TextureGen::build(params); }
SkeletonHandle MonsterGenerator::generateSkeleton(const MonsterParams& params) { return RigGen::build(params); }
AnimationHandle MonsterGenerator::generateAnimation(const MonsterParams& params) { return AnimGen::build(params); }
AIHandle MonsterGenerator::generateAI(const BehaviorParams& params) { return AIGen::build(params); }

void MonsterGenerator::clearCache() {
    if (m_cache) m_cache->clear();
    m_cacheHits = 0;
    m_cacheMisses = 0;
}

size_t MonsterGenerator::getCacheSize() const { return m_cache ? m_cache->size() : 0; }
size_t MonsterGenerator::getCacheHits() const { return m_cacheHits.load(); }
size_t MonsterGenerator::getCacheMisses() const { return m_cacheMisses.load(); }
float MonsterGenerator::getGenerationTime() const { return m_generationTime.load(); }

MonsterAssetBundle MonsterGenerator::generateMonsterAssets(const MonsterParams& params) {
    ++m_activeGenerations;
    const auto start = std::chrono::steady_clock::now();
    MonsterAssetBundle bundle;
    bundle.params = params;
    bundle.assetPath = "monsters/" + (params.id.empty() ? std::string("unnamed") : params.id);
    bundle.creationTime = std::chrono::system_clock::now();

    try {
        if (!params.isValid()) {
            throw std::invalid_argument("invalid MonsterParams: " + params.toString());
        }
        updateProgress(0.0f);
        bundle.mesh = generateMesh(params);
        updateProgress(0.25f);
        bundle.texture = generateTexture(params);

        // Material maps derived from the same height field as the albedo.
        auto height = TextureGen::buildHeightMap(params);
        auto& store = AssetStore::instance();
        const float variation = std::clamp(params.colorVariation, 0.0f, 1.0f) * 0.5f;
        bundle.normalMap = store.addTexture(std::move(*TextureGen::MaterialGenerator::generateNormalMap(height)));
        bundle.roughnessMap = store.addTexture(
            std::move(*TextureGen::MaterialGenerator::generateRoughnessMap(params.materialRoughness, variation)));
        bundle.metallicMap = store.addTexture(
            std::move(*TextureGen::MaterialGenerator::generateMetallicMap(params.materialMetallic, variation)));
        if (params.materialEmissive > 0.0f) {
            bundle.emissiveMap = store.addTexture(
                std::move(*TextureGen::MaterialGenerator::generateEmissiveMap(params.materialEmissive, params.colorAccent)));
        }
        bundle.aoMap = store.addTexture(std::move(*TextureGen::MaterialGenerator::generateAOMap(height)));
        updateProgress(0.5f);

        bundle.skeleton = generateSkeleton(params);
        updateProgress(0.65f);
        bundle.anim = generateAnimation(params);
        updateProgress(0.8f);

        BehaviorParams behavior = AIGen::presetFor(params.aiProfile);
        behavior.seed = params.seed;
        behavior.maxHealth *= std::max(params.size, 0.1f) / 2.0f;   // presets are tuned for 2 m monsters
        bundle.ai = generateAI(behavior);
        updateProgress(1.0f);

        if (auto mesh = store.mesh(bundle.mesh)) {
            bundle.result.vertexCount = static_cast<uint32_t>(mesh->vertices.size());
            bundle.result.triangleCount = static_cast<uint32_t>(mesh->triangleCount());
            bundle.result.memoryUsage += mesh->vertices.size() * sizeof(CreatureAssets::MeshVertex) +
                                         mesh->indices.size() * sizeof(uint32_t);
        }
        if (auto texture = store.texture(bundle.texture)) {
            bundle.result.textureSize = texture->width;
            bundle.result.memoryUsage += texture->rgba.size() * (bundle.emissiveMap ? 6u : 5u);   // albedo + maps
        }
        if (auto anim = store.animation(bundle.anim)) {
            bundle.result.animationFrameCount = static_cast<uint32_t>(anim->frameCount());
        }
        bundle.result.success = bundle.isValid();
        if (!bundle.result.success) bundle.result.errorMessage = "one or more assets failed to generate";
    } catch (const std::exception& e) {
        bundle.result.success = false;
        bundle.result.errorMessage = e.what();
        Log::error("Monster", "Generation failed for '{}': {}", params.id, e.what());
    }

    const float seconds = std::chrono::duration<float>(std::chrono::steady_clock::now() - start).count();
    bundle.result.generationTime = seconds;
    m_generationTime = seconds;
    ++m_totalGenerations;
    --m_activeGenerations;
    logGenerationStats(params, bundle);
    return bundle;
}

void MonsterGenerator::updateProgress(float progress) {
    m_progress = std::clamp(progress, 0.0f, 1.0f);
}

void MonsterGenerator::logGenerationStats(const MonsterParams& params, const MonsterAssetBundle& bundle) {
    if (!bundle.result.success) return;
    Log::info("Monster", "Generated '{}' in {}s: {} verts, {} tris, {}px textures, {} anim frames ({} total generations)",
              params.id, bundle.result.generationTime, bundle.result.vertexCount, bundle.result.triangleCount,
              bundle.result.textureSize, bundle.result.animationFrameCount, m_totalGenerations.load());
}

} // namespace Monsters
} // namespace MagiTech
