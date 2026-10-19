#include "MechGenerators.hpp"
#include "MechFamilyAssetStore.hpp"
#include "core/Log.hpp"
#include "core/mesh/MeshGenerator.hpp"
#include <FastNoiseLite.h>
#include <algorithm>
#include <cctype>
#include <cmath>
#include <numbers>

namespace MagiTech {
namespace Mechs {

// ============================================================================
// Shared helpers
// ============================================================================
namespace {

constexpr float kPi = std::numbers::pi_v<float>;
using MtMesh = mt::Mesh;

MechFamilyAssetStore& assets() { return MechFamilyAssetStore::instance(); }

std::string lower(std::string s) {
    std::transform(s.begin(), s.end(), s.begin(), [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
    return s;
}

glm::mat4 trs(const glm::vec3& t, const glm::quat& r = glm::quat(1.0f, 0.0f, 0.0f, 0.0f),
              const glm::vec3& s = glm::vec3(1.0f)) {
    return glm::translate(glm::mat4(1.0f), t) * glm::mat4_cast(r) * glm::scale(glm::mat4(1.0f), s);
}

// Shortest-arc rotation taking unit vector `from` onto unit vector `to`.
glm::quat rotationBetween(const glm::vec3& from, const glm::vec3& to) {
    const float d = glm::dot(from, to);
    if (d > 0.9999f) return glm::quat(1.0f, 0.0f, 0.0f, 0.0f);
    if (d < -0.9999f) {
        glm::vec3 axis = glm::cross(glm::vec3(1, 0, 0), from);
        if (glm::dot(axis, axis) < 1e-6f) axis = glm::cross(glm::vec3(0, 0, 1), from);
        return glm::angleAxis(kPi, glm::normalize(axis));
    }
    const glm::vec3 axis = glm::cross(from, to);
    return glm::normalize(glm::quat(1.0f + d, axis.x, axis.y, axis.z));
}

// mt cylinders are built along +Y; this turns them to run along +Z.
glm::quat yToZ() { return glm::angleAxis(kPi * 0.5f, glm::vec3(1.0f, 0.0f, 0.0f)); }
uint32_t subdivisionsFor(int detailLevel) {
    return 8u << static_cast<uint32_t>(std::clamp(detailLevel, 0, 3));
}

std::shared_ptr<MtMesh> makeMesh(const std::string& name) {
    auto mesh = std::make_shared<MtMesh>();
    mesh->name = name;
    return mesh;
}

std::shared_ptr<MtMesh> box(const glm::vec3& size) {
    return mt::MeshGenerator::generateBox(size.x, size.y, size.z);
}
std::shared_ptr<MtMesh> cylinder(float radius, float height, uint32_t sides = 16) {
    return mt::MeshGenerator::generateCylinder(radius, height, std::max(3u, sides));
}
std::shared_ptr<MtMesh> sphere(float radius, uint32_t subdivisions = 12) {
    return mt::MeshGenerator::generateSphere(radius, std::max(4u, subdivisions));
}
std::shared_ptr<MtMesh> ring(float radius, float thickness, uint32_t segments = 24) {
    return mt::MeshGenerator::generateTorus(radius, thickness, std::max(6u, segments), 6);
}

// Transforms `part` (a freshly generated mesh) and appends its submeshes to `dst`.
void appendPart(MtMesh& dst, const std::shared_ptr<MtMesh>& part, const glm::mat4& transform,
                const std::string& name, uint32_t materialIndex, const glm::vec4& color) {
    if (!part) return;
    part->transform(transform);
    for (auto& sub : part->submeshes) {
        sub.name = name;
        sub.materialIndex = materialIndex;
        for (auto& v : sub.vertices) v.color = color;
        dst.submeshes.push_back(std::move(sub));
    }
}

MeshHandle storeMesh(const std::shared_ptr<MtMesh>& mesh) {
    mesh->calculateBoundingVolumes();
    mesh->updateCounts();
    return assets().add(mesh);
}

// ---------------------------------------------------------------- textures --

std::shared_ptr<MechTextureData> makeTexture(const std::string& name, int width, int height) {
    auto tex = std::make_shared<MechTextureData>();
    tex->name = name;
    tex->width = width;
    tex->height = height;
    tex->rgba.assign(static_cast<size_t>(width) * static_cast<size_t>(height) * 4u, 0);
    return tex;
}

unsigned char toByte(float v) {
    return static_cast<unsigned char>(std::lround(std::clamp(v, 0.0f, 1.0f) * 255.0f));
}

glm::vec4 readPixel(const std::vector<unsigned char>& px, int width, int x, int y) {
    const size_t i = (static_cast<size_t>(y) * width + x) * 4u;
    return glm::vec4(px[i], px[i + 1], px[i + 2], px[i + 3]) / 255.0f;
}

void writePixel(std::vector<unsigned char>& px, int width, int x, int y, const glm::vec4& c) {
    const size_t i = (static_cast<size_t>(y) * width + x) * 4u;
    px[i] = toByte(c.r);
    px[i + 1] = toByte(c.g);
    px[i + 2] = toByte(c.b);
    px[i + 3] = toByte(c.a);
}

void blendPixel(std::vector<unsigned char>& px, int width, int height, int x, int y, const glm::vec4& c) {
    if (x < 0 || y < 0 || x >= width || y >= height) return;
    const glm::vec4 dst = readPixel(px, width, x, y);
    const glm::vec3 rgb = glm::mix(glm::vec3(dst), glm::vec3(c), c.a);
    writePixel(px, width, x, y, glm::vec4(rgb, std::max(dst.a, c.a)));
}

int textureSize(int requested) {
    int size = 16;
    while (size < requested && size < 4096) size <<= 1;
    return size;
}

FastNoiseLite makeNoise(const ProceduralParams& proc, bool fractal, int seed) {
    FastNoiseLite noise(seed);
    noise.SetNoiseType(FastNoiseLite::NoiseType_OpenSimplex2);
    noise.SetFrequency(std::max(0.0001f, proc.frequency) * 0.01f);
    if (fractal) {
        noise.SetFractalType(FastNoiseLite::FractalType_FBm);
        noise.SetFractalOctaves(std::clamp(proc.octaves, 1, 10));
        noise.SetFractalLacunarity(proc.lacunarity);
        noise.SetFractalGain(proc.persistence);
    }
    return noise;
}

int seedFor(const std::string& id) {
    return static_cast<int>(MechHash::hashFields(id) & 0x7fffffff);
}

ProceduralParams proceduralFor(const MechParams& p) {
    ProceduralParams proc;
    proc.frequency = std::max(0.01f, p.noiseScale);
    proc.amplitude = 1.0f;
    proc.patternScale = std::max(0.01f, p.noiseScale);
    proc.patternType = p.pattern.empty() ? proc.patternType : p.pattern;
    proc.emissive = (p.pulseEmission || p.enableGlow) ? 1.0f : 0.0f;
    return proc;
}

// Height field used by the normal and roughness maps (panel seams + surface noise).
std::vector<float> surfaceHeight(const MechParams& p, int size) {
    std::vector<float> height(static_cast<size_t>(size) * size);
    FastNoiseLite noise = makeNoise(proceduralFor(p), true, seedFor(p.id));
    const int panel = std::max(8, size / (4 + 2 * std::clamp(p.detailLevel, 0, 3)));
    for (int y = 0; y < size; ++y) {
        for (int x = 0; x < size; ++x) {
            float h = 0.5f + 0.25f * noise.GetNoise(static_cast<float>(x), static_cast<float>(y));
            if (x % panel == 0 || y % panel == 0) h -= 0.35f;   // panel seams
            height[static_cast<size_t>(y) * size + x] = std::clamp(h, 0.0f, 1.0f);
        }
    }
    return height;
}

// ---------------------------------------------------------------- physics ---

void appendBoxTriangles(std::vector<glm::vec3>& vertices, std::vector<uint32_t>& indices,
                        const glm::vec3& center, const glm::vec3& half) {
    const uint32_t base = static_cast<uint32_t>(vertices.size());
    for (int i = 0; i < 8; ++i) {
        vertices.push_back(center + glm::vec3((i & 1) ? half.x : -half.x,
                                              (i & 2) ? half.y : -half.y,
                                              (i & 4) ? half.z : -half.z));
    }
    static const uint32_t faces[36] = {0, 2, 1, 1, 2, 3, 4, 5, 6, 5, 7, 6, 0, 1, 4, 1, 5, 4,
                                       2, 6, 3, 3, 6, 7, 0, 4, 2, 2, 4, 6, 1, 3, 5, 3, 7, 5};
    for (uint32_t f : faces) indices.push_back(base + f);
}

// Capsule between a and b as a closed prism with pointed caps (convex, collision grade).
void appendCapsuleTriangles(std::vector<glm::vec3>& vertices, std::vector<uint32_t>& indices,
                            const glm::vec3& a, const glm::vec3& b, float radius, int sides = 8) {
    glm::vec3 axis = b - a;
    const float len = glm::length(axis);
    axis = len > 1e-5f ? axis / len : glm::vec3(0.0f, 1.0f, 0.0f);
    const glm::vec3 helper = std::abs(axis.y) < 0.9f ? glm::vec3(0, 1, 0) : glm::vec3(1, 0, 0);
    const glm::vec3 u = glm::normalize(glm::cross(axis, helper));
    const glm::vec3 v = glm::cross(axis, u);
    const uint32_t base = static_cast<uint32_t>(vertices.size());
    for (int ring = 0; ring < 2; ++ring) {
        const glm::vec3 c = ring == 0 ? a : b;
        for (int s = 0; s < sides; ++s) {
            const float t = 2.0f * kPi * s / sides;
            vertices.push_back(c + radius * (std::cos(t) * u + std::sin(t) * v));
        }
    }
    const uint32_t tipA = static_cast<uint32_t>(vertices.size());
    vertices.push_back(a - axis * radius);
    const uint32_t tipB = static_cast<uint32_t>(vertices.size());
    vertices.push_back(b + axis * radius);
    for (int s = 0; s < sides; ++s) {
        const uint32_t s0 = base + s, s1 = base + (s + 1) % sides;
        const uint32_t t0 = s0 + sides, t1 = s1 + sides;
        indices.insert(indices.end(), {s0, s1, t1, s0, t1, t0, tipA, s1, s0, tipB, t0, t1});
    }
}

// ---------------------------------------------------------------- mech body -

struct LimbLayout {
    bool isLeg = true;
    float side = 1.0f;       // -1 left, +1 right
    int pairIndex = 0;       // front-to-back index among limbs of the same kind
    glm::vec3 anchor{0.0f};  // attachment point on the torso
};

int legCountFor(int limbCount) {
    if (limbCount <= 0) return 0;
    return std::min(limbCount, std::max(2, limbCount - 2));
}

LimbLayout limbLayout(int limbIndex, const MechParams& p) {
    LimbLayout layout;
    const int legs = legCountFor(p.limbCount);
    layout.isLeg = limbIndex < legs;
    const int kindIndex = layout.isLeg ? limbIndex : limbIndex - legs;
    const int kindCount = layout.isLeg ? legs : p.limbCount - legs;
    layout.side = (kindIndex % 2 == 0) ? -1.0f : 1.0f;
    layout.pairIndex = kindIndex / 2;
    const int pairs = std::max(1, (kindCount + 1) / 2);
    const glm::vec3 half = p.torsoSize * 0.5f;
    const float zSpread = pairs > 1 ? (static_cast<float>(layout.pairIndex) / (pairs - 1) - 0.5f) * p.torsoSize.z : 0.0f;
    if (layout.isLeg) {
        layout.anchor = glm::vec3(layout.side * half.x * 0.6f, -half.y, zSpread);
    } else {
        layout.anchor = glm::vec3(layout.side * (half.x + 0.1f), half.y * 0.6f, zSpread);
    }
    return layout;
}

// Height of the torso centre above the ground.
float hipHeight(const MechParams& p) {
    return (legCountFor(p.limbCount) > 0 ? p.limbLength * 2.0f : 0.0f) + p.torsoSize.y * 0.5f;
}

MechSkeletonData buildRigData(const MechParams& p) {
    MechSkeletonData rig;
    rig.name = p.id + "_rig";
    auto addBone = [&rig](const std::string& name, int parent, const glm::vec3& offset) {
        MechBone bone;
        bone.name = name;
        bone.parent = parent;
        bone.localTransform = glm::translate(glm::mat4(1.0f), offset);
        rig.bones.push_back(bone);
        return static_cast<int>(rig.bones.size()) - 1;
    };
    const int root = addBone("root", -1, glm::vec3(0.0f));
    const int pelvis = addBone("pelvis", root, glm::vec3(0.0f, hipHeight(p) - p.torsoSize.y * 0.5f, 0.0f));
    const int torso = addBone("torso", pelvis, glm::vec3(0.0f, p.torsoSize.y * 0.5f, 0.0f));
    addBone("head", torso, glm::vec3(0.0f, p.torsoSize.y * 0.5f, p.torsoSize.z * 0.25f));

    for (int i = 0; i < p.limbCount; ++i) {
        const LimbLayout layout = limbLayout(i, p);
        const std::string prefix = (layout.isLeg ? "leg_" : "arm_") + std::to_string(i);
        const int parent = layout.isLeg ? pelvis : torso;
        const glm::vec3 anchor = layout.isLeg ? layout.anchor + glm::vec3(0.0f, p.torsoSize.y * 0.5f, 0.0f)
                                              : layout.anchor - glm::vec3(0.0f, p.torsoSize.y * 0.5f, 0.0f);
        const int upper = addBone(prefix + "_upper", parent, anchor);
        const int lower = addBone(prefix + "_lower", upper, glm::vec3(0.0f, -p.limbLength, 0.0f));
        const int end = addBone(prefix + (layout.isLeg ? "_foot" : "_hand"), lower, glm::vec3(0.0f, -p.limbLength, 0.0f));
        rig.bones[lower].minAngleDeg = layout.isLeg ? 0.0f : -150.0f;
        rig.bones[lower].maxAngleDeg = layout.isLeg ? 150.0f : 0.0f;
        if (p.enableIK) rig.ikChains.push_back({upper, lower, end});
    }
    for (size_t m = 0; m < p.weaponMounts.size(); ++m) {
        const float side = (m % 2 == 0) ? -1.0f : 1.0f;
        addBone("mount_" + p.weaponMounts[m], torso,
                glm::vec3(side * p.torsoSize.x * 0.5f, p.torsoSize.y * 0.5f, 0.0f));
    }
    if (p.enablePhysics) {
        for (auto& bone : rig.bones) {
            bone.stiffness = 50.0f;
            bone.damping = 0.5f;
        }
    }
    rig.morphTargets = p.forms;
    return rig;
}

float easeCurve(const std::string& curve, float t) {
    t = std::clamp(t, 0.0f, 1.0f);
    const std::string c = lower(curve);
    if (c == "linear") return t;
    if (c == "easein") return t * t;
    if (c == "easeout") return 1.0f - (1.0f - t) * (1.0f - t);
    return t * t * (3.0f - 2.0f * t);   // easeInOut (smoothstep)
}

// ---------------------------------------------------------- segmented body --

float taperedRadius(const SegmentedMechParams& p, int index) {
    const int n = std::max(1, p.segmentCount);
    const float t = n > 1 ? static_cast<float>(index) / (n - 1) : 0.0f;
    const std::string profile = lower(p.taperProfile);
    float factor = 1.0f;
    if (profile == "linear") factor = 1.0f - 0.5f * t;
    else if (profile == "exponential") factor = std::exp(-1.5f * t);
    else if (profile == "bulge") factor = 0.7f + 0.3f * std::sin(t * kPi);
    return p.segmentRadius * std::max(0.25f, factor);
}

glm::vec3 segmentCenter(const SegmentedMechParams& p, int index) {
    return glm::vec3(0.0f, 0.0f, -static_cast<float>(index) * (p.segmentLength + p.connectorGap));
}

std::shared_ptr<MtMesh> segmentShape(const SegmentedMechParams& p, float radius) {
    const std::string shape = lower(p.segmentShape);
    const uint32_t sides = 8u + 4u * static_cast<uint32_t>(std::clamp(p.platingDetailLevel, 0, 4));
    if (shape == "hexagon" || shape == "hex") return cylinder(radius, p.segmentLength, 6);
    if (shape == "box" || shape == "square") return box(glm::vec3(radius * 2.0f, radius * 2.0f, p.segmentLength));
    if (shape == "sphere" || shape == "ball") return sphere(std::max(radius, p.segmentLength * 0.5f), sides);
    return cylinder(radius, p.segmentLength, sides);
}

// Appends one complete segment (body, plates, stripes) to `dst`.
void appendSegment(MtMesh& dst, const SegmentedMechParams& p, int index) {
    const float radius = taperedRadius(p, index);
    const glm::vec3 center = segmentCenter(p, index);
    const glm::vec4 hull(p.colorPrimary, 1.0f);
    const std::string shape = lower(p.segmentShape);
    const bool boxShaped = shape == "box" || shape == "square";
    const bool sphereShaped = shape == "sphere" || shape == "ball";
    appendPart(dst, segmentShape(p, radius),
               trs(center, (boxShaped || sphereShaped) ? glm::quat(1, 0, 0, 0) : yToZ()),
               "segment_" + std::to_string(index), 0, hull);

    if (p.enablePlating && p.platesPerSegment > 0) {
        const float plateWidth = 2.0f * kPi * radius / p.platesPerSegment * 0.8f;
        for (int k = 0; k < p.platesPerSegment; ++k) {
            const float angle = 2.0f * kPi * k / p.platesPerSegment;
            const glm::quat rot = glm::angleAxis(angle, glm::vec3(0, 0, 1));
            const glm::vec3 offset = rot * glm::vec3(0.0f, radius + p.plateThickness * 0.5f, 0.0f);
            appendPart(dst, box(glm::vec3(plateWidth, p.plateThickness, p.segmentLength * 0.85f)),
                       trs(center + offset, rot), "plate_" + std::to_string(index) + "_" + std::to_string(k),
                       1, p.platingColor);
        }
    }
    for (int s = 0; s < p.stripeCount; ++s) {
        const float z = (static_cast<float>(s + 1) / (p.stripeCount + 1) - 0.5f) * p.segmentLength;
        appendPart(dst, ring(radius + p.plateThickness, std::max(0.005f, p.stripeWidth * 0.5f)),
                   trs(center + glm::vec3(0.0f, 0.0f, z), yToZ()),
                   "stripe_" + std::to_string(index) + "_" + std::to_string(s), 2, p.stripeColor);
    }
}

int segmentedBoneCount(const SegmentedMechParams& p) {
    return std::max(1, p.segmentCount) + 2;   // root + one per segment + cockpit
}

// Animation where every segment bone follows `rotationAt(segment, phase)`.
template <typename RotationFn>
AnimationHandle storeSegmentAnimation(const SegmentedMechParams& p, const std::string& name, float frequency,
                                      RotationFn rotationAt) {
    auto anim = std::make_shared<MechAnimationData>();
    anim->name = name;
    anim->duration = 1.0f / std::max(0.01f, frequency);
    anim->looping = true;
    const int boneCount = segmentedBoneCount(p);
    constexpr int kSamples = 16;
    for (int k = 0; k <= kSamples; ++k) {
        MechAnimationKey key;
        key.time = anim->duration * k / kSamples;
        const float phase = 2.0f * kPi * k / kSamples;
        key.boneRotations.assign(boneCount, glm::quat(1, 0, 0, 0));
        key.boneOffsets.assign(boneCount, glm::vec3(0.0f));
        for (int s = 0; s < std::max(1, p.segmentCount); ++s) {
            key.boneRotations[s + 1] = rotationAt(s, phase);
        }
        anim->keys.push_back(std::move(key));
    }
    return assets().add(anim);
}

float maxBendRad(const SegmentedMechParams& p) {
    return glm::radians(std::clamp(p.maxBendAngleDeg, 0.0f, 180.0f));
}

// ---------------------------------------------------------- cockpit / icon --

std::shared_ptr<MtMesh> cockpitMesh(const CockpitParams& p, const std::string& name) {
    auto mesh = makeMesh(name);
    const glm::vec4 fabric = p.seatFabricColor;
    const glm::vec4 metal(0.35f, 0.35f, 0.4f, 1.0f);
    // Seat and headrest
    appendPart(*mesh, box(glm::vec3(p.seatWidth, p.seatHeight * 0.3f, p.seatDepth * 0.6f)),
               trs(glm::vec3(0.0f, p.seatHeight, 0.0f)), "seat", 0, fabric);
    appendPart(*mesh, box(glm::vec3(p.seatWidth, p.seatHeight * 1.4f, p.seatHeight * 0.25f)),
               trs(glm::vec3(0.0f, p.seatHeight * 1.7f, p.seatDepth * 0.3f)), "seat_back", 0, fabric);
    if (p.headrestEnabled) {
        appendPart(*mesh, box(glm::vec3(p.seatWidth * 0.5f, p.seatHeight * 0.4f, p.seatHeight * 0.25f)),
                   trs(glm::vec3(0.0f, p.seatHeight * 2.6f, p.seatDepth * 0.3f)), "headrest", 0, fabric);
    }
    // Console with displays and gauges
    const glm::vec3 consolePos(0.0f, p.seatHeight * 1.5f, -p.seatDepth * 0.6f);
    appendPart(*mesh, box(glm::vec3(p.seatWidth * 1.4f, p.seatHeight * 0.6f, p.seatDepth * 0.3f)),
               trs(consolePos), "console", 1, metal);
    for (int d = 0; d < p.displayCount; ++d) {
        const float x = (static_cast<float>(d) + 0.5f) / p.displayCount - 0.5f;
        const float aspect = p.displayResolution.y > 0.0f ? p.displayResolution.x / p.displayResolution.y : 1.33f;
        const float h = p.seatHeight * 0.35f;
        appendPart(*mesh, box(glm::vec3(h * aspect, h, 0.01f)),
                   trs(consolePos + glm::vec3(x * p.seatWidth * 1.3f, p.seatHeight * 0.45f, 0.1f)),
                   "display_" + std::to_string(d), 2, glm::vec4(0.1f, 0.6f, 0.9f, 1.0f));
    }
    for (int g = 0; g < p.gaugeCount; ++g) {
        const float x = (static_cast<float>(g) + 0.5f) / p.gaugeCount - 0.5f;
        appendPart(*mesh, cylinder(p.gaugeRadius, 0.02f, 12),
                   trs(consolePos + glm::vec3(x * p.seatWidth * 1.3f, p.seatHeight * 0.1f, 0.16f), yToZ()),
                   "gauge_" + std::to_string(g), 2, p.gaugeNeedleColor);
    }
    // Controls
    appendPart(*mesh, cylinder(0.02f, 0.3f, 8),
               trs(glm::vec3(p.stickOffsetX, p.seatHeight + 0.15f, -p.stickOffsetY)), "stick", 1, metal);
    if (p.throttleLever) {
        appendPart(*mesh, cylinder(0.02f, 0.25f, 8),
                   trs(glm::vec3(-p.stickOffsetX, p.seatHeight + 0.12f, -p.stickOffsetY)), "throttle", 1, metal);
    }
    if (p.pedalControls) {
        for (int side = -1; side <= 1; side += 2) {
            appendPart(*mesh, box(glm::vec3(0.1f, 0.02f, 0.2f)),
                       trs(glm::vec3(side * 0.15f, 0.05f, -p.seatDepth * 0.8f)), "pedal", 1, metal);
        }
    }
    // Canopy (flattened dome) and optional HUD plane
    appendPart(*mesh, sphere(1.0f, 16),
               trs(glm::vec3(0.0f, p.seatHeight, 0.0f), glm::quat(1, 0, 0, 0),
                   glm::vec3(p.canopyRadius, p.canopyHeight, p.canopyRadius)),
               "canopy", 3, p.glassTint);
    if (p.holographicHUD) {
        appendPart(*mesh, box(glm::vec3(p.seatWidth, p.seatHeight * 0.5f, 0.005f)),
                   trs(consolePos + glm::vec3(0.0f, p.seatHeight * 0.9f, 0.2f)), "hud", 2,
                   glm::vec4(0.3f, 1.0f, 0.6f, 0.4f));
    }
    mesh->transform(trs(p.mountOffset, p.mountRotation));
    return mesh;
}

std::vector<glm::vec2> iconShape(const std::string& shape, int size) {
    std::vector<glm::vec2> pts;
    const glm::vec2 c(size * 0.5f);
    const float r = size * 0.48f;
    const std::string s = lower(shape);
    const int corners = s == "hexagon" ? 6 : (s == "square" ? 4 : (s == "triangle" ? 3 : 48));
    const float start = s == "square" ? kPi * 0.25f : (s == "hexagon" ? 0.0f : -kPi * 0.5f);
    for (int i = 0; i <= corners; ++i) {
        const float a = start + 2.0f * kPi * i / corners;
        pts.push_back(c + r * glm::vec2(std::cos(a), std::sin(a)));
    }
    return pts;
}

bool insidePolygon(const std::vector<glm::vec2>& poly, const glm::vec2& pt) {
    bool inside = false;
    for (size_t i = 0, j = poly.size() - 1; i < poly.size(); j = i++) {
        if (((poly[i].y > pt.y) != (poly[j].y > pt.y)) &&
            (pt.x < (poly[j].x - poly[i].x) * (pt.y - poly[i].y) / (poly[j].y - poly[i].y) + poly[i].x)) {
            inside = !inside;
        }
    }
    return inside;
}

void drawLine(std::vector<unsigned char>& px, int w, int h, glm::vec2 a, glm::vec2 b, float thickness,
              const glm::vec4& color) {
    const float len = glm::length(b - a);
    const int steps = std::max(1, static_cast<int>(len * 2.0f));
    const int r = std::max(0, static_cast<int>(thickness * 0.5f));
    for (int i = 0; i <= steps; ++i) {
        const glm::vec2 p = glm::mix(a, b, static_cast<float>(i) / steps);
        for (int dy = -r; dy <= r; ++dy) {
            for (int dx = -r; dx <= r; ++dx) {
                if (dx * dx + dy * dy > r * r) continue;
                blendPixel(px, w, h, static_cast<int>(p.x) + dx, static_cast<int>(p.y) + dy, color);
            }
        }
    }
}

// ---------------------------------------------------------------- centipede -

float centipedeSegmentZ(const CentipedeMechParams& p, int index) {
    return -static_cast<float>(index) * p.segmentLength;
}

glm::vec3 centipedeHip(const CentipedeMechParams& p, int segmentIndex, int legIndex) {
    const int perSide = std::max(1, (p.legsPerSegment + 1) / 2);
    const float side = (legIndex % 2 == 0) ? -1.0f : 1.0f;
    const int row = legIndex / 2;
    const float zOffset = perSide > 1 ? (static_cast<float>(row) / (perSide - 1) - 0.5f) * p.segmentLength * 0.6f : 0.0f;
    return glm::vec3(side * p.segmentRadius, 0.0f, centipedeSegmentZ(p, segmentIndex) + zOffset);
}

glm::vec3 centipedeFoot(const CentipedeMechParams& p, int segmentIndex, int legIndex) {
    const glm::vec3 hip = centipedeHip(p, segmentIndex, legIndex);
    const float side = hip.x < 0.0f ? -1.0f : 1.0f;
    return glm::vec3(hip.x + side * p.upperLegLength * 0.9f, -p.lowerLegLength, hip.z);
}

MaterialHandle storeMaterial(const std::string& name, const glm::vec4& albedo, float metallic, float roughness,
                             const glm::vec3& emissive = glm::vec3(0.0f), float emissiveIntensity = 0.0f) {
    auto mat = std::make_shared<MechMaterialData>();
    mat->name = name;
    mat->albedo = albedo;
    mat->metallic = metallic;
    mat->roughness = roughness;
    mat->emissive = emissive;
    mat->emissiveIntensity = emissiveIntensity;
    mat->opacity = albedo.a;
    return assets().add(mat);
}

ParticleHandle storeParticles(const std::string& name, float rate, float lifetime, float speed, float size,
                              const glm::vec4& color, std::vector<glm::vec3> positions) {
    auto fx = std::make_shared<MechParticleData>();
    fx->name = name;
    fx->spawnRate = rate;
    fx->lifetime = lifetime;
    fx->speed = speed;
    fx->size = size;
    fx->color = color;
    fx->emitterPositions = std::move(positions);
    return assets().add(fx);
}

AudioHandle storeAudio(const std::string& name, const std::string& category, float frequency, float volume,
                       float pitch, bool looping) {
    auto audio = std::make_shared<MechAudioData>();
    audio->name = name;
    audio->category = category;
    audio->frequency = frequency;
    audio->volume = volume;
    audio->pitch = pitch;
    audio->looping = looping;
    return assets().add(audio);
}

MechColliderShape capsuleShape(const glm::vec3& a, const glm::vec3& b, float radius, float mass) {
    MechColliderShape shape;
    shape.type = MechColliderShape::Type::Capsule;
    const glm::vec3 axis = b - a;
    const float len = glm::length(axis);
    shape.size = glm::vec3(radius, len, 0.0f);
    const glm::quat rot = len > 1e-5f ? rotationBetween(glm::vec3(0, 1, 0), axis / len) : glm::quat(1, 0, 0, 0);
    shape.transform = trs((a + b) * 0.5f, rot);
    shape.mass = mass;
    return shape;
}

void finalizePhysics(MechPhysicsData& physics) {
    physics.totalMass = 0.0f;
    glm::vec3 weighted(0.0f);
    for (const auto& s : physics.shapes) {
        physics.totalMass += s.mass;
        weighted += glm::vec3(s.transform[3]) * s.mass;
    }
    physics.centerOfMass = physics.totalMass > 0.0f ? weighted / physics.totalMass : glm::vec3(0.0f);
}

} // namespace

// ============================================================================
// MeshGenerator (biped / multi-limb mechs)
// ============================================================================

MeshHandle MeshGenerator::buildMechMesh(const MechParams& p) {
    Log::debug("Mech", "Building mech mesh for: {}", p.id);
    auto mesh = makeMesh(p.id + "_mesh");
    const uint32_t sub = subdivisionsFor(p.detailLevel);
    const glm::vec4 primary(p.colorPrimary, 1.0f);
    const glm::vec4 accent(p.colorAccent, 1.0f);
    const float hip = hipHeight(p);

    // Torso and head
    appendPart(*mesh, box(p.torsoSize), trs(glm::vec3(0.0f, hip, 0.0f)), "torso", 0, primary);
    appendPart(*mesh, sphere(std::min(p.torsoSize.x, p.torsoSize.z) * 0.3f, sub),
               trs(glm::vec3(0.0f, hip + p.torsoSize.y * 0.6f, p.torsoSize.z * 0.25f)), "head", 0, accent);

    // Limbs: upper segment, joint, lower segment, foot/hand
    const float limbRadius = std::max(0.05f, std::min(p.torsoSize.x, p.torsoSize.z) * 0.12f);
    for (int i = 0; i < p.limbCount; ++i) {
        const LimbLayout layout = limbLayout(i, p);
        const glm::vec3 anchor = layout.anchor + glm::vec3(0.0f, hip, 0.0f);
        const std::string prefix = (layout.isLeg ? "leg_" : "arm_") + std::to_string(i);
        appendPart(*mesh, cylinder(limbRadius, p.limbLength, sub),
                   trs(anchor - glm::vec3(0.0f, p.limbLength * 0.5f, 0.0f)), prefix + "_upper", 0, primary);
        appendPart(*mesh, sphere(limbRadius * 1.3f, sub),
                   trs(anchor - glm::vec3(0.0f, p.limbLength, 0.0f)), prefix + "_joint", 1, accent);
        appendPart(*mesh, cylinder(limbRadius * 0.85f, p.limbLength, sub),
                   trs(anchor - glm::vec3(0.0f, p.limbLength * 1.5f, 0.0f)), prefix + "_lower", 0, primary);
        const glm::vec3 endSize = layout.isLeg ? glm::vec3(limbRadius * 3.0f, limbRadius, limbRadius * 4.0f)
                                               : glm::vec3(limbRadius * 2.0f);
        appendPart(*mesh, box(endSize), trs(anchor - glm::vec3(0.0f, p.limbLength * 2.0f, 0.0f)),
                   prefix + (layout.isLeg ? "_foot" : "_hand"), 1, accent);
    }

    // Armor plating
    if (p.armorPlates) {
        const float thickness = 0.04f + 0.02f * static_cast<float>(p.armorTypes.size());
        const glm::vec3 t = p.torsoSize;
        appendPart(*mesh, box(glm::vec3(t.x * 0.9f, t.y * 0.8f, thickness)),
                   trs(glm::vec3(0.0f, hip, t.z * 0.5f + thickness * 0.5f)), "armor_front", 1, accent);
        appendPart(*mesh, box(glm::vec3(t.x * 0.9f, t.y * 0.8f, thickness)),
                   trs(glm::vec3(0.0f, hip, -t.z * 0.5f - thickness * 0.5f)), "armor_back", 1, accent);
        for (int side = -1; side <= 1; side += 2) {
            appendPart(*mesh, box(glm::vec3(thickness, t.y * 0.7f, t.z * 0.8f)),
                       trs(glm::vec3(side * (t.x * 0.5f + thickness * 0.5f), hip, 0.0f)), "armor_side", 1, accent);
        }
    }

    // Weapon mounts: a turret base plus one barrel per weapon type assigned to the mount
    for (size_t m = 0; m < p.weaponMounts.size(); ++m) {
        const float side = (m % 2 == 0) ? -1.0f : 1.0f;
        const glm::vec3 base(side * p.torsoSize.x * 0.5f, hip + p.torsoSize.y * 0.5f, 0.0f);
        appendPart(*mesh, cylinder(limbRadius * 1.5f, limbRadius, sub), trs(base), "mount_" + p.weaponMounts[m], 1, accent);
        const std::string weapon = m < p.weaponTypes.size() ? p.weaponTypes[m] : p.weaponMounts[m];
        appendPart(*mesh, cylinder(limbRadius * 0.4f, p.torsoSize.z, sub),
                   trs(base + glm::vec3(0.0f, limbRadius, p.torsoSize.z * 0.5f), yToZ()), "weapon_" + weapon, 1, primary);
    }

    // Shield emitter ring
    if (p.enableShield) {
        appendPart(*mesh, ring(std::max(p.torsoSize.x, p.torsoSize.z) * 0.8f, 0.03f),
                   trs(glm::vec3(0.0f, hip, 0.0f)), "shield_emitter", 2, glm::vec4(p.colorAccent, 0.6f));
    }

    mesh->transform(glm::scale(glm::mat4(1.0f), p.scale));
    return storeMesh(mesh);
}

// ============================================================================
// TextureGenerator
// ============================================================================

float TextureGenerator::generateNoise(float x, float y, const ProceduralParams& proc) {
    FastNoiseLite noise = makeNoise(proc, false, 1337);
    return noise.GetNoise(x, y) * proc.amplitude;
}

float TextureGenerator::generateFractalNoise(float x, float y, const ProceduralParams& proc) {
    FastNoiseLite noise = makeNoise(proc, true, 1337);
    return noise.GetNoise(x, y) * proc.amplitude;
}

float TextureGenerator::generateTurbulence(float x, float y, const ProceduralParams& proc) {
    return std::abs(generateFractalNoise(x, y, proc));
}

glm::vec3 TextureGenerator::blendColors(const glm::vec3& color1, const glm::vec3& color2, float factor) {
    return glm::mix(color1, color2, std::clamp(factor, 0.0f, 1.0f));
}

glm::vec3 TextureGenerator::adjustBrightness(const glm::vec3& color, float factor) {
    return glm::clamp(color * factor, glm::vec3(0.0f), glm::vec3(1.0f));
}

glm::vec3 TextureGenerator::adjustContrast(const glm::vec3& color, float factor) {
    return glm::clamp((color - glm::vec3(0.5f)) * factor + glm::vec3(0.5f), glm::vec3(0.0f), glm::vec3(1.0f));
}

glm::vec3 TextureGenerator::adjustSaturation(const glm::vec3& color, float factor) {
    const float luma = glm::dot(color, glm::vec3(0.299f, 0.587f, 0.114f));
    return glm::clamp(glm::mix(glm::vec3(luma), color, factor), glm::vec3(0.0f), glm::vec3(1.0f));
}

void TextureGenerator::generateHexPattern(std::vector<unsigned char>& pixels, int width, int height,
                                          const ProceduralParams& proc) {
    const float cell = std::max(4.0f, 24.0f * proc.patternScale);
    const float c = std::cos(proc.patternRotation), s = std::sin(proc.patternRotation);
    for (int y = 0; y < height; ++y) {
        for (int x = 0; x < width; ++x) {
            const glm::vec2 q(c * x - s * y, s * x + c * y);
            // Distance to the nearest hex edge via axial coordinates
            const glm::vec2 h(q.x / (cell * 1.5f), (q.y - (static_cast<int>(std::floor(q.x / (cell * 1.5f))) % 2) * cell * 0.5f) / cell);
            const glm::vec2 f = glm::fract(h) - glm::vec2(0.5f);
            const float edge = std::max(std::abs(f.x) * 1.5f, std::abs(f.y) + std::abs(f.x) * 0.5f);
            if (edge > 0.45f) {
                glm::vec4 px = readPixel(pixels, width, x, y);
                px = glm::vec4(glm::mix(glm::vec3(px), proc.patternColor * 0.3f, 0.6f * proc.amplitude), px.a);
                writePixel(pixels, width, x, y, px);
            }
        }
    }
}

void TextureGenerator::generateCamouflagePattern(std::vector<unsigned char>& pixels, int width, int height,
                                                 const ProceduralParams& proc) {
    FastNoiseLite noise = makeNoise(proc, true, 4242);
    const float scale = 1.0f / std::max(0.01f, proc.patternScale);
    for (int y = 0; y < height; ++y) {
        for (int x = 0; x < width; ++x) {
            const float n = noise.GetNoise(x * scale, y * scale);
            const float band = n < -0.2f ? 0.55f : (n < 0.25f ? 0.8f : 1.0f);
            glm::vec4 px = readPixel(pixels, width, x, y);
            px = glm::vec4(glm::vec3(px) * glm::mix(1.0f, band, std::clamp(proc.amplitude, 0.0f, 1.0f)), px.a);
            writePixel(pixels, width, x, y, px);
        }
    }
}

void TextureGenerator::generateTechPattern(std::vector<unsigned char>& pixels, int width, int height,
                                           const ProceduralParams& proc) {
    const int panel = std::max(8, static_cast<int>(32.0f * proc.patternScale));
    for (int y = 0; y < height; ++y) {
        for (int x = 0; x < width; ++x) {
            const int lx = x % panel, ly = y % panel;
            glm::vec4 px = readPixel(pixels, width, x, y);
            if (lx == 0 || ly == 0) {
                px = glm::vec4(glm::vec3(px) * 0.45f, px.a);                       // seam
            } else if ((lx == 3 || lx == panel - 3) && (ly == 3 || ly == panel - 3)) {
                px = glm::vec4(glm::mix(glm::vec3(px), proc.patternColor, 0.7f), px.a);   // rivet
            }
            writePixel(pixels, width, x, y, px);
        }
    }
}

void TextureGenerator::generateDamagedPattern(std::vector<unsigned char>& pixels, int width, int height,
                                              const ProceduralParams& proc) {
    FastNoiseLite scorch = makeNoise(proc, true, 777);
    FastNoiseLite scratches(778);
    scratches.SetNoiseType(FastNoiseLite::NoiseType_Cellular);
    scratches.SetFrequency(0.05f / std::max(0.01f, proc.patternScale));
    scratches.SetCellularReturnType(FastNoiseLite::CellularReturnType_Distance2Sub);
    for (int y = 0; y < height; ++y) {
        for (int x = 0; x < width; ++x) {
            glm::vec4 px = readPixel(pixels, width, x, y);
            const float burn = std::clamp(scorch.GetNoise(static_cast<float>(x), static_cast<float>(y)), 0.0f, 1.0f);
            glm::vec3 rgb = glm::mix(glm::vec3(px), glm::vec3(0.08f, 0.06f, 0.05f), burn * 0.7f);
            if (scratches.GetNoise(static_cast<float>(x), static_cast<float>(y)) > 0.92f) {
                rgb = glm::mix(rgb, glm::vec3(0.75f), 0.6f);   // bare metal scratch
            }
            writePixel(pixels, width, x, y, glm::vec4(rgb, px.a));
        }
    }
}

void TextureGenerator::applyEmissiveEffects(std::vector<unsigned char>& pixels, int width, int height,
                                            const MechParams& p) {
    const int spacing = std::max(8, height / 8);
    for (int y = 0; y < height; ++y) {
        if (y % spacing > 1) continue;
        for (int x = 0; x < width; ++x) {
            blendPixel(pixels, width, height, x, y, glm::vec4(p.colorAccent, 0.85f));
        }
    }
}

TextureHandle TextureGenerator::buildProceduralSkin(const MechParams& p, const ProceduralParams& proc) {
    const int size = textureSize(p.textureResolution);
    auto tex = makeTexture(p.id + "_skin", size, size);
    FastNoiseLite noise = makeNoise(proc, true, seedFor(p.id));
    for (int y = 0; y < size; ++y) {
        for (int x = 0; x < size; ++x) {
            const float n = 0.5f + 0.5f * noise.GetNoise(static_cast<float>(x), static_cast<float>(y));
            const glm::vec3 rgb = blendColors(p.colorPrimary, p.colorAccent, n * p.patternIntensity * 0.5f);
            writePixel(tex->rgba, size, x, y, glm::vec4(rgb, 1.0f));
        }
    }
    const std::string pattern = lower(p.pattern.empty() ? proc.patternType : p.pattern);
    ProceduralParams patternProc = proc;
    patternProc.amplitude = proc.amplitude * std::clamp(p.patternIntensity * 2.0f, 0.0f, 1.0f);
    patternProc.patternColor = p.colorAccent;
    if (pattern.find("hex") != std::string::npos) generateHexPattern(tex->rgba, size, size, patternProc);
    if (pattern.find("camo") != std::string::npos) generateCamouflagePattern(tex->rgba, size, size, patternProc);
    if (pattern.find("tech") != std::string::npos) generateTechPattern(tex->rgba, size, size, patternProc);
    if (pattern.find("damage") != std::string::npos) generateDamagedPattern(tex->rgba, size, size, patternProc);
    if (p.pulseEmission || p.enableGlow) applyEmissiveEffects(tex->rgba, size, size, p);
    return assets().add(tex);
}

TextureHandle TextureGenerator::buildMechSkin(const MechParams& p) {
    Log::debug("Mech", "Building mech skin for: {}", p.id);
    return buildProceduralSkin(p, proceduralFor(p));
}

TextureHandle TextureGenerator::buildNormalMap(const MechParams& p) {
    const int size = textureSize(p.textureResolution);
    const std::vector<float> height = surfaceHeight(p, size);
    auto tex = makeTexture(p.id + "_normal", size, size);
    const float strength = 2.0f + static_cast<float>(p.detailLevel);
    for (int y = 0; y < size; ++y) {
        for (int x = 0; x < size; ++x) {
            auto h = [&](int sx, int sy) {
                sx = (sx + size) % size;
                sy = (sy + size) % size;
                return height[static_cast<size_t>(sy) * size + sx];
            };
            const float dx = (h(x + 1, y) - h(x - 1, y)) * strength;
            const float dy = (h(x, y + 1) - h(x, y - 1)) * strength;
            const glm::vec3 n = glm::normalize(glm::vec3(-dx, -dy, 1.0f));
            writePixel(tex->rgba, size, x, y, glm::vec4(n * 0.5f + 0.5f, 1.0f));
        }
    }
    return assets().add(tex);
}

TextureHandle TextureGenerator::buildRoughnessMap(const MechParams& p) {
    const int size = textureSize(p.textureResolution);
    const std::vector<float> height = surfaceHeight(p, size);
    auto tex = makeTexture(p.id + "_roughness", size, size);
    const float base = p.armorPlates ? 0.35f : 0.55f;
    for (int y = 0; y < size; ++y) {
        for (int x = 0; x < size; ++x) {
            const float r = std::clamp(base + (0.5f - height[static_cast<size_t>(y) * size + x]) * 0.6f, 0.0f, 1.0f);
            writePixel(tex->rgba, size, x, y, glm::vec4(r, r, r, 1.0f));
        }
    }
    return assets().add(tex);
}

TextureHandle TextureGenerator::buildMetallicMap(const MechParams& p) {
    const int size = textureSize(p.textureResolution);
    const std::vector<float> height = surfaceHeight(p, size);
    auto tex = makeTexture(p.id + "_metallic", size, size);
    for (int y = 0; y < size; ++y) {
        for (int x = 0; x < size; ++x) {
            // Panels are metal, seams are painted/dirty
            const float m = height[static_cast<size_t>(y) * size + x] > 0.3f ? 0.9f : 0.2f;
            writePixel(tex->rgba, size, x, y, glm::vec4(m, m, m, 1.0f));
        }
    }
    return assets().add(tex);
}

TextureHandle TextureGenerator::buildEmissiveMap(const MechParams& p) {
    const int size = textureSize(p.textureResolution);
    auto tex = makeTexture(p.id + "_emissive", size, size);
    for (int y = 0; y < size; ++y) {
        for (int x = 0; x < size; ++x) writePixel(tex->rgba, size, x, y, glm::vec4(0.0f, 0.0f, 0.0f, 1.0f));
    }
    if (p.pulseEmission || p.enableGlow) applyEmissiveEffects(tex->rgba, size, size, p);
    return assets().add(tex);
}

// ============================================================================
// SkeletonGenerator
// ============================================================================

SkeletonHandle SkeletonGenerator::buildRig(const MechParams& p) {
    Log::debug("Mech", "Building skeleton rig for: {}", p.id);
    return assets().add(std::make_shared<MechSkeletonData>(buildRigData(p)));
}

AnimationHandle SkeletonGenerator::createIdleAnimation(const MechParams& p) {
    const MechSkeletonData rig = buildRigData(p);
    auto anim = std::make_shared<MechAnimationData>();
    anim->name = p.id + "_idle";
    anim->duration = 2.0f;
    anim->looping = true;
    constexpr int kSamples = 8;
    const int torso = 2;
    for (int k = 0; k <= kSamples; ++k) {
        MechAnimationKey key;
        key.time = anim->duration * k / kSamples;
        key.boneRotations.assign(rig.bones.size(), glm::quat(1, 0, 0, 0));
        key.boneOffsets.assign(rig.bones.size(), glm::vec3(0.0f));
        const float phase = 2.0f * kPi * k / kSamples;
        key.boneOffsets[torso] = glm::vec3(0.0f, 0.02f * p.torsoSize.y * std::sin(phase), 0.0f);   // breathing
        key.boneRotations[torso] = glm::angleAxis(0.02f * std::sin(phase * 0.5f), glm::vec3(0, 1, 0));
        anim->keys.push_back(std::move(key));
    }
    return assets().add(anim);
}

AnimationHandle SkeletonGenerator::createMorphAnimation(const MechParams& p, const std::string& fromForm,
                                                        const std::string& toForm) {
    const MechSkeletonData rig = buildRigData(p);
    auto anim = std::make_shared<MechAnimationData>();
    anim->name = p.id + "_morph_" + fromForm + "_to_" + toForm;
    anim->duration = std::max(0.01f, p.morphDuration);
    anim->looping = false;
    // Each form is a distinct compact/extended pose: fold the limbs by a per-form angle.
    auto formAngle = [&p](const std::string& form) {
        const auto it = std::find(p.forms.begin(), p.forms.end(), form);
        const size_t index = it == p.forms.end() ? 0 : static_cast<size_t>(it - p.forms.begin());
        return p.forms.size() > 1 ? glm::radians(90.0f) * index / (p.forms.size() - 1) : 0.0f;
    };
    const float from = formAngle(fromForm), to = formAngle(toForm);
    constexpr int kSamples = 10;
    for (int k = 0; k <= kSamples; ++k) {
        MechAnimationKey key;
        key.time = anim->duration * k / kSamples;
        const float angle = glm::mix(from, to, easeCurve(p.morphCurve, static_cast<float>(k) / kSamples));
        key.boneRotations.assign(rig.bones.size(), glm::quat(1, 0, 0, 0));
        key.boneOffsets.assign(rig.bones.size(), glm::vec3(0.0f));
        for (size_t b = 0; b < rig.bones.size(); ++b) {
            if (rig.bones[b].name.find("_lower") != std::string::npos) {
                key.boneRotations[b] = glm::angleAxis(angle, glm::vec3(1, 0, 0));
            }
        }
        anim->keys.push_back(std::move(key));
    }
    return assets().add(anim);
}

// ============================================================================
// MaterialGenerator
// ============================================================================

MaterialHandle MaterialGenerator::createMaterialFromTextures(const MechParams& p, TextureHandle albedo,
                                                             TextureHandle normal, TextureHandle roughness,
                                                             TextureHandle metallic, TextureHandle emissive) {
    auto mat = std::make_shared<MechMaterialData>();
    mat->name = p.id + "_material";
    mat->albedo = glm::vec4(p.colorPrimary, 1.0f);
    mat->metallic = p.armorPlates ? 0.85f : 0.6f;
    mat->roughness = std::clamp(0.6f - 0.1f * static_cast<float>(p.detailLevel), 0.1f, 1.0f);
    const bool glowing = p.pulseEmission || p.enableGlow;
    mat->emissive = glowing ? p.colorAccent : glm::vec3(0.0f);
    mat->emissiveIntensity = glowing ? 2.0f : 0.0f;
    mat->normalStrength = 1.0f;
    mat->albedoMap = albedo;
    mat->normalMap = normal;
    mat->roughnessMap = roughness;
    mat->metallicMap = metallic;
    mat->emissiveMap = emissive;
    return assets().add(mat);
}

MaterialHandle MaterialGenerator::buildMechMaterial(const MechParams& p) {
    return createMaterialFromTextures(p, 0, 0, 0, 0, 0);
}

MaterialHandle MaterialGenerator::buildSegmentedMaterial(const SegmentedMechParams& p) {
    auto mat = std::make_shared<MechMaterialData>();
    mat->name = p.id + "_hull";
    mat->albedo = glm::vec4(p.colorPrimary, 1.0f);
    mat->metallic = p.enablePlating ? 0.8f : 0.5f;
    mat->roughness = std::clamp(0.3f + p.noiseDetail, 0.05f, 1.0f);
    mat->emissive = glm::vec3(p.stripeColor);
    mat->emissiveIntensity = p.stripeCount > 0 ? p.stripeGlowIntensity : 0.0f;
    mat->albedoMap = SegmentedTextureGenerator::buildSegmentedSkin(p);
    return assets().add(mat);
}

// ============================================================================
// PhysicsGenerator
// ============================================================================

void PhysicsGenerator::generateBoxCollision(const MechParams& p, std::vector<glm::vec3>& vertices,
                                            std::vector<uint32_t>& indices) {
    appendBoxTriangles(vertices, indices, glm::vec3(0.0f, hipHeight(p), 0.0f) * p.scale, p.torsoSize * 0.5f * p.scale);
}

void PhysicsGenerator::generateCapsuleCollision(const MechParams& p, std::vector<glm::vec3>& vertices,
                                                std::vector<uint32_t>& indices) {
    const float radius = std::max(0.05f, std::min(p.torsoSize.x, p.torsoSize.z) * 0.15f) * p.scale.x;
    const float hip = hipHeight(p);
    for (int i = 0; i < p.limbCount; ++i) {
        const glm::vec3 anchor = (limbLayout(i, p).anchor + glm::vec3(0.0f, hip, 0.0f)) * p.scale;
        const glm::vec3 end = anchor - glm::vec3(0.0f, p.limbLength * 2.0f, 0.0f) * p.scale;
        appendCapsuleTriangles(vertices, indices, anchor, end, radius);
    }
}

void PhysicsGenerator::generateCollisionMesh(const MechParams& p, std::vector<glm::vec3>& vertices,
                                             std::vector<uint32_t>& indices) {
    vertices.clear();
    indices.clear();
    generateBoxCollision(p, vertices, indices);
    if (p.limbCount > 0) generateCapsuleCollision(p, vertices, indices);
}

glm::vec3 PhysicsGenerator::computeCenterOfMass(const MechParams& p) {
    // Torso carries ~70% of the mass, limbs share the rest.
    glm::vec3 com = glm::vec3(0.0f, hipHeight(p), 0.0f) * 0.7f;
    if (p.limbCount > 0) {
        glm::vec3 limbs(0.0f);
        for (int i = 0; i < p.limbCount; ++i) {
            limbs += limbLayout(i, p).anchor + glm::vec3(0.0f, hipHeight(p) - p.limbLength, 0.0f);
        }
        com += limbs / static_cast<float>(p.limbCount) * 0.3f;
    } else {
        com /= 0.7f;
    }
    return com * p.scale;
}

glm::mat3 PhysicsGenerator::computeInertiaTensor(const MechParams& p, const glm::vec3& centerOfMass) {
    const glm::vec3 d = p.torsoSize * p.scale;
    const float m = p.mass;
    glm::mat3 inertia(0.0f);
    inertia[0][0] = m / 12.0f * (d.y * d.y + d.z * d.z);
    inertia[1][1] = m / 12.0f * (d.x * d.x + d.z * d.z);
    inertia[2][2] = m / 12.0f * (d.x * d.x + d.y * d.y);
    // Parallel axis shift from the torso centre to the centre of mass
    const glm::vec3 r = glm::vec3(0.0f, hipHeight(p), 0.0f) * p.scale - centerOfMass;
    const float r2 = glm::dot(r, r);
    for (int i = 0; i < 3; ++i) {
        for (int j = 0; j < 3; ++j) inertia[i][j] += m * ((i == j ? r2 : 0.0f) - r[i] * r[j]);
    }
    return inertia;
}

void PhysicsGenerator::generateRigidBody(const MechParams& p, float& mass, glm::vec3& centerOfMass, glm::mat3& inertia) {
    mass = p.mass;
    centerOfMass = computeCenterOfMass(p);
    inertia = computeInertiaTensor(p, centerOfMass);
}

// ============================================================================
// Segmented (snake / worm) generators
// ============================================================================

MeshHandle SegmentedMeshGenerator::buildSegmentedMech(const SegmentedMechParams& p) {
    Log::debug("Mech", "Building segmented mech mesh for: {}", p.id);
    auto mesh = makeMesh(p.id + "_segments");
    const int n = std::max(1, p.segmentCount);
    for (int i = 0; i < n; ++i) {
        appendSegment(*mesh, p, i);
        if (i + 1 < n && p.connectorGap > 0.0f) {
            const float r = std::min(taperedRadius(p, i), taperedRadius(p, i + 1)) * 0.7f;
            const glm::vec3 mid = segmentCenter(p, i) - glm::vec3(0.0f, 0.0f, (p.segmentLength + p.connectorGap) * 0.5f);
            appendPart(*mesh, cylinder(r, p.connectorGap + 0.02f, 12), trs(mid, yToZ()),
                       "connector_" + std::to_string(i), 1, p.platingColor);
        }
    }
    return storeMesh(mesh);
}

MeshHandle SegmentedMeshGenerator::createSegment(const SegmentedMechParams& p, int segmentIndex) {
    auto mesh = makeMesh(p.id + "_segment_" + std::to_string(segmentIndex));
    appendSegment(*mesh, p, segmentIndex);
    return storeMesh(mesh);
}

void SegmentedTextureGenerator::generateHexPattern(std::vector<unsigned char>& pixels, int width, int height,
                                                   const SegmentedMechParams& p) {
    ProceduralParams proc;
    proc.patternScale = std::max(0.1f, p.textureScale) * 0.5f;
    proc.patternColor = glm::vec3(p.platingColor);
    proc.amplitude = 1.0f;
    TextureGenerator::generateHexPattern(pixels, width, height, proc);
}

void SegmentedTextureGenerator::generateEmissiveStrips(std::vector<unsigned char>& pixels, int width, int height,
                                                       const SegmentedMechParams& p) {
    if (p.stripeCount <= 0) return;
    const int stripePx = std::max(1, static_cast<int>(p.stripeWidth * height * 4.0f));
    const glm::vec4 glow(glm::vec3(p.stripeColor) * std::min(1.0f, p.stripeGlowIntensity / 3.0f), 1.0f);
    for (int s = 0; s < p.stripeCount; ++s) {
        const int center = (s + 1) * height / (p.stripeCount + 1);
        for (int y = center - stripePx / 2; y <= center + stripePx / 2; ++y) {
            for (int x = 0; x < width; ++x) blendPixel(pixels, width, height, x, y, glow);
        }
    }
}

TextureHandle SegmentedTextureGenerator::buildSegmentedSkin(const SegmentedMechParams& p) {
    constexpr int kSize = 256;
    auto tex = makeTexture(p.id + "_skin", kSize, kSize);
    ProceduralParams proc;
    proc.frequency = std::max(0.1f, p.textureScale) * 2.0f;
    FastNoiseLite noise = makeNoise(proc, true, seedFor(p.id));
    const int bands = std::max(1, p.segmentCount);
    for (int y = 0; y < kSize; ++y) {
        for (int x = 0; x < kSize; ++x) {
            const float n = noise.GetNoise(static_cast<float>(x), static_cast<float>(y)) * p.noiseDetail;
            const bool secondary = (x * bands / kSize) % 2 == 1;
            const glm::vec3 base = secondary ? glm::mix(p.colorPrimary, p.colorSecondary, 0.35f) : p.colorPrimary;
            writePixel(tex->rgba, kSize, x, y, glm::vec4(glm::clamp(base * (1.0f + n), 0.0f, 1.0f), 1.0f));
        }
    }
    if (p.enablePlating) generateHexPattern(tex->rgba, kSize, kSize, p);
    generateEmissiveStrips(tex->rgba, kSize, kSize, p);
    return assets().add(tex);
}

SkeletonHandle SegmentedSkeletonGenerator::buildSegmentedRig(const SegmentedMechParams& p) {
    auto rig = std::make_shared<MechSkeletonData>();
    rig->name = p.id + "_rig";
    MechBone root;
    root.name = "root";
    rig->bones.push_back(root);
    const int n = std::max(1, p.segmentCount);
    std::vector<int> chain;
    for (int i = 0; i < n; ++i) {
        MechBone bone;
        bone.name = "segment_" + std::to_string(i);
        bone.parent = i == 0 ? 0 : i;   // bone index of the previous segment
        bone.localTransform = glm::translate(glm::mat4(1.0f),
            i == 0 ? glm::vec3(0.0f) : glm::vec3(0.0f, 0.0f, -(p.segmentLength + p.connectorGap)));
        bone.minAngleDeg = -p.maxBendAngleDeg;
        bone.maxAngleDeg = p.maxBendAngleDeg;
        bone.stiffness = p.bendStiffness * (1.0f - std::clamp(p.jointFlexibility, 0.0f, 1.0f) * 0.5f);
        bone.damping = p.jointDamping;
        rig->bones.push_back(bone);
        chain.push_back(i + 1);
    }
    MechBone cockpit;
    cockpit.name = "cockpit";
    cockpit.parent = std::clamp(p.cockpitSegmentIndex, 0, n - 1) + 1;
    const float radius = taperedRadius(p, cockpit.parent - 1);
    const glm::vec3 up = glm::length(p.cockpitOrientation) > 1e-5f ? glm::normalize(p.cockpitOrientation)
                                                                    : glm::vec3(0, 1, 0);
    const bool external = lower(p.cockpitType) == "external";
    cockpit.localTransform = glm::translate(glm::mat4(1.0f), up * (external ? radius + p.cockpitRadius : 0.0f));
    rig->bones.push_back(cockpit);
    rig->ikChains.push_back(chain);
    return assets().add(rig);
}

AnimationHandle SegmentedSkeletonGenerator::createWaveAnimation(const SegmentedMechParams& p, float amplitude,
                                                                float frequency) {
    const float limit = maxBendRad(p);
    const int n = std::max(1, p.segmentCount);
    return storeSegmentAnimation(p, p.id + "_wave", frequency, [&](int s, float phase) {
        const float angle = std::clamp(amplitude * 0.25f * std::sin(phase - 2.0f * kPi * s / n), -limit, limit);
        return glm::angleAxis(angle, glm::vec3(0, 1, 0));
    });
}

AnimationHandle SegmentedSkeletonGenerator::createSlitherAnimation(const SegmentedMechParams& p) {
    const float limit = maxBendRad(p);
    const int n = std::max(1, p.segmentCount);
    return storeSegmentAnimation(p, p.id + "_slither", p.waveFrequency, [&](int s, float phase) {
        // Lateral undulation whose amplitude grows towards the tail
        const float falloff = 0.5f + 0.5f * static_cast<float>(s) / n;
        const float angle = std::clamp(p.waveAmplitude * 0.3f * falloff * std::sin(phase - 4.0f * kPi * s / n), -limit, limit);
        return glm::angleAxis(angle, glm::vec3(0, 1, 0));
    });
}

AnimationHandle SegmentedSkeletonGenerator::createCoilAnimation(const SegmentedMechParams& p) {
    const float limit = maxBendRad(p);
    const int n = std::max(1, p.segmentCount);
    return storeSegmentAnimation(p, p.id + "_coil", p.waveFrequency * 0.5f, [&](int s, float phase) {
        // Progressive curl from the tail forward, then release
        const float curl = 0.5f - 0.5f * std::cos(phase);
        const float weight = static_cast<float>(s + 1) / n;
        return glm::angleAxis(std::min(limit, limit * curl * weight), glm::vec3(0, 1, 0));
    });
}

AnimationHandle SegmentedSkeletonGenerator::createUndulateAnimation(const SegmentedMechParams& p) {
    const float limit = maxBendRad(p);
    const int n = std::max(1, p.segmentCount);
    return storeSegmentAnimation(p, p.id + "_undulate", p.waveFrequency, [&](int s, float phase) {
        // Vertical (pitch) wave
        const float angle = std::clamp(p.waveAmplitude * 0.2f * std::sin(phase - 2.0f * kPi * s / n), -limit, limit);
        return glm::angleAxis(angle, glm::vec3(1, 0, 0));
    });
}

AnimationHandle SegmentedSkeletonGenerator::createCustomAnimation(const SegmentedMechParams& p,
                                                                  const std::string& profile) {
    const std::string name = lower(profile);
    if (name == "mech_slither" || name == "slither") return createSlitherAnimation(p);
    if (name == "coil") return createCoilAnimation(p);
    if (name == "undulate") return createUndulateAnimation(p);
    return createWaveAnimation(p, p.waveAmplitude, p.waveFrequency);
}

PhysicsHandle SegmentedPhysicsGenerator::createSegmentPhysics(const SegmentedMechParams& p, int segmentIndex) {
    auto physics = std::make_shared<MechPhysicsData>();
    physics->name = p.id + "_segment_" + std::to_string(segmentIndex) + "_physics";
    const glm::vec3 c = segmentCenter(p, segmentIndex);
    const glm::vec3 halfAxis(0.0f, 0.0f, p.segmentLength * 0.5f);
    physics->shapes.push_back(capsuleShape(c + halfAxis, c - halfAxis, taperedRadius(p, segmentIndex), p.segmentMass));
    physics->jointDamping = p.jointDamping;
    physics->jointStiffness = p.bendStiffness;
    finalizePhysics(*physics);
    return assets().add(physics);
}

PhysicsHandle SegmentedPhysicsGenerator::buildSegmentedPhysics(const SegmentedMechParams& p) {
    auto physics = std::make_shared<MechPhysicsData>();
    physics->name = p.id + "_physics";
    const glm::vec3 halfAxis(0.0f, 0.0f, p.segmentLength * 0.5f);
    for (int i = 0; i < std::max(1, p.segmentCount); ++i) {
        const glm::vec3 c = segmentCenter(p, i);
        physics->shapes.push_back(capsuleShape(c + halfAxis, c - halfAxis, taperedRadius(p, i), p.segmentMass));
    }
    physics->jointDamping = p.jointDamping;
    physics->jointStiffness = p.bendStiffness;
    finalizePhysics(*physics);
    return assets().add(physics);
}

ParticleHandle SegmentedParticleGenerator::buildJointSparks(const SegmentedMechParams& p) {
    if (!p.enableJointSparks) return 0;   // no emitter requested
    std::vector<glm::vec3> joints;
    for (int i = 0; i + 1 < std::max(1, p.segmentCount); ++i) {
        joints.push_back(segmentCenter(p, i) - glm::vec3(0.0f, 0.0f, (p.segmentLength + p.connectorGap) * 0.5f));
    }
    return storeParticles(p.id + "_joint_sparks", p.sparkRate, p.sparkLifetime, 2.0f, 0.02f, p.sparkColor,
                          std::move(joints));
}

MeshHandle CockpitGenerator::buildCockpit(const CockpitParams& p) {
    return storeMesh(cockpitMesh(p, "cockpit"));
}

TextureHandle CockpitGenerator::buildCockpitTexture(const CockpitParams& p) {
    constexpr int kSize = 128;
    auto tex = makeTexture("cockpit_panel", kSize, kSize);
    for (int y = 0; y < kSize; ++y) {
        for (int x = 0; x < kSize; ++x) writePixel(tex->rgba, kSize, x, y, glm::vec4(0.12f, 0.12f, 0.14f, 1.0f));
    }
    // Display rectangles along the top half
    for (int d = 0; d < p.displayCount; ++d) {
        const int x0 = 4 + d * (kSize - 8) / std::max(1, p.displayCount);
        const int x1 = 4 + (d + 1) * (kSize - 8) / std::max(1, p.displayCount) - 4;
        for (int y = 8; y < kSize / 2 - 4; ++y) {
            for (int x = x0; x < x1; ++x) writePixel(tex->rgba, kSize, x, y, glm::vec4(0.05f, 0.35f, 0.55f, 1.0f));
        }
    }
    // Gauge dials along the bottom half
    for (int g = 0; g < p.gaugeCount; ++g) {
        const glm::vec2 c((g + 0.5f) * kSize / std::max(1, p.gaugeCount), kSize * 0.75f);
        const float r = std::min(kSize / (2.5f * std::max(1, p.gaugeCount)), kSize * 0.15f);
        for (int y = 0; y < kSize; ++y) {
            for (int x = 0; x < kSize; ++x) {
                const float d = glm::length(glm::vec2(x, y) - c);
                if (std::abs(d - r) < 1.0f) writePixel(tex->rgba, kSize, x, y, glm::vec4(0.8f, 0.8f, 0.8f, 1.0f));
            }
        }
        drawLine(tex->rgba, kSize, kSize, c, c + glm::vec2(r * 0.7f, -r * 0.5f), 1.0f, p.gaugeNeedleColor);
    }
    return assets().add(tex);
}

MaterialHandle CockpitGenerator::buildCockpitMaterial(const CockpitParams& p) {
    auto mat = std::make_shared<MechMaterialData>();
    mat->name = "cockpit_glass";
    mat->albedo = p.glassTint;
    mat->opacity = p.glassTint.a;
    mat->metallic = 0.0f;
    mat->roughness = std::clamp(1.0f - p.reflectivity, 0.0f, 1.0f);
    mat->emissive = p.cockpitLight ? glm::vec3(p.lightColor) : glm::vec3(0.0f);
    mat->emissiveIntensity = p.cockpitLight ? p.lightIntensity : 0.0f;
    return assets().add(mat);
}

void UIIconGenerator::drawBackground(std::vector<unsigned char>& pixels, int width, int height, const UIParams& ui) {
    const auto shape = iconShape(ui.backgroundShape, std::min(width, height));
    for (int y = 0; y < height; ++y) {
        for (int x = 0; x < width; ++x) {
            if (insidePolygon(shape, glm::vec2(x + 0.5f, y + 0.5f))) {
                const float t = static_cast<float>(y) / height;
                writePixel(pixels, width, x, y, glm::vec4(glm::mix(glm::vec3(0.12f), glm::vec3(0.05f), t), 0.9f));
            }
        }
    }
}

void UIIconGenerator::drawBorder(std::vector<unsigned char>& pixels, int width, int height, const UIParams& ui) {
    const auto shape = iconShape(ui.backgroundShape, std::min(width, height));
    const float thickness = std::max(1.0f, std::min(width, height) / 32.0f);
    for (size_t i = 0; i + 1 < shape.size(); ++i) drawLine(pixels, width, height, shape[i], shape[i + 1], thickness, ui.borderColor);
}

void UIIconGenerator::addFlashEffect(std::vector<unsigned char>& pixels, int width, int height, const UIParams& ui) {
    const glm::vec2 c(width * 0.35f, height * 0.3f);
    const float r = std::min(width, height) * 0.5f;
    for (int y = 0; y < height; ++y) {
        for (int x = 0; x < width; ++x) {
            const float d = glm::length(glm::vec2(x, y) - c) / r;
            if (d < 1.0f && readPixel(pixels, width, x, y).a > 0.0f) {
                blendPixel(pixels, width, height, x, y, glm::vec4(glm::vec3(ui.borderColor), 0.25f * (1.0f - d)));
            }
        }
    }
}

void UIIconGenerator::generateSilhouettePoints(const SegmentedMechParams& p, std::vector<glm::vec2>& points) {
    points.clear();
    const int n = std::max(2, p.segmentCount);
    for (int i = 0; i < n; ++i) {
        const float t = static_cast<float>(i) / (n - 1);
        // Normalised [0,1] space: an S-curve from head (left) to tail (right)
        points.emplace_back(0.15f + 0.7f * t, 0.5f + 0.2f * std::sin(t * 2.0f * kPi));
    }
}

void UIIconGenerator::drawPolyline(std::vector<unsigned char>& pixels, int width, int height,
                                   const std::vector<glm::vec2>& points, const glm::vec4& color) {
    const float thickness = std::max(2.0f, std::min(width, height) / 10.0f);
    for (size_t i = 0; i + 1 < points.size(); ++i) {
        const float taper = 1.0f - 0.6f * static_cast<float>(i) / points.size();
        drawLine(pixels, width, height, points[i], points[i + 1], thickness * taper, color);
    }
}

void UIIconGenerator::drawMechSilhouette(std::vector<unsigned char>& pixels, int width, int height,
                                         const SegmentedMechParams& p) {
    std::vector<glm::vec2> points;
    generateSilhouettePoints(p, points);
    for (auto& pt : points) pt *= glm::vec2(width, height);
    drawPolyline(pixels, width, height, points, glm::vec4(p.colorPrimary, 1.0f));
    if (!points.empty()) {
        const float r = std::max(2.0f, std::min(width, height) / 14.0f);
        drawLine(pixels, width, height, points.front(), points.front(), r * 2.0f, glm::vec4(glm::vec3(p.stripeColor), 1.0f));
    }
}

TextureHandle UIIconGenerator::buildMechIcon(const SegmentedMechParams& p, const UIParams& ui) {
    const int size = std::clamp(ui.iconSize, 16, 1024);
    auto tex = makeTexture(p.id + "_icon", size, size);
    drawBackground(tex->rgba, size, size, ui);
    drawMechSilhouette(tex->rgba, size, size, p);
    drawBorder(tex->rgba, size, size, ui);
    if (ui.flashOnSelect) addFlashEffect(tex->rgba, size, size, ui);
    return assets().add(tex);
}

// ============================================================================
// Centipede generators
// ============================================================================

MeshHandle CentipedeSegmentGenerator::createSegment(const CentipedeMechParams& p, int segmentIndex) {
    auto mesh = makeMesh(p.id + "_segment_" + std::to_string(segmentIndex));
    const glm::vec3 c(0.0f, 0.0f, centipedeSegmentZ(p, segmentIndex));
    appendPart(*mesh, cylinder(p.segmentRadius, p.segmentLength * 0.9f, 16), trs(c, yToZ()), "body", 0, p.baseColor);
    if (p.seamlessJoints) {
        for (int end = -1; end <= 1; end += 2) {
            appendPart(*mesh, sphere(p.segmentRadius * 0.95f, 12),
                       trs(c + glm::vec3(0.0f, 0.0f, end * p.segmentLength * 0.45f), glm::quat(1, 0, 0, 0),
                           glm::vec3(1.0f, 1.0f, 0.4f)),
                       "bevel", 0, p.baseColor);
        }
    }
    if (p.armorPlates) {
        appendPart(*mesh, box(glm::vec3(p.segmentRadius * 1.8f, p.segmentRadius * 0.15f, p.segmentLength * 0.8f)),
                   trs(c + glm::vec3(0.0f, p.segmentRadius, 0.0f)), "armor", 1,
                   glm::vec4(glm::vec3(p.baseColor) * 0.6f, 1.0f));
    }
    return storeMesh(mesh);
}

std::vector<MeshHandle> CentipedeSegmentGenerator::buildSegments(const CentipedeMechParams& p) {
    std::vector<MeshHandle> segments;
    for (int i = 0; i < std::max(1, p.segmentCount); ++i) segments.push_back(createSegment(p, i));
    return segments;
}

MeshHandle CentipedeJointGenerator::createJoint(const CentipedeMechParams& p, int jointIndex) {
    auto mesh = makeMesh(p.id + "_joint_" + std::to_string(jointIndex));
    const float z = centipedeSegmentZ(p, jointIndex) - p.segmentLength * 0.5f;
    appendPart(*mesh, sphere(p.segmentRadius * 0.6f, 12), trs(glm::vec3(0.0f, 0.0f, z)), "joint", 1,
               glm::vec4(0.3f, 0.3f, 0.32f, 1.0f));
    return storeMesh(mesh);
}

std::vector<MeshHandle> CentipedeJointGenerator::buildJoints(const CentipedeMechParams& p) {
    std::vector<MeshHandle> joints;
    for (int j = 0; j + 1 < std::max(1, p.segmentCount); ++j) joints.push_back(createJoint(p, j));
    return joints;
}

MeshHandle CentipedeLegGenerator::buildSingleLeg(const CentipedeMechParams& p, int segmentIndex, int legIndex) {
    auto mesh = makeMesh(p.id + "_leg_" + std::to_string(segmentIndex) + "_" + std::to_string(legIndex));
    const glm::vec3 hip = centipedeHip(p, segmentIndex, legIndex);
    const glm::vec3 foot = centipedeFoot(p, segmentIndex, legIndex);
    const float side = hip.x < 0.0f ? -1.0f : 1.0f;
    const glm::vec3 knee = hip + glm::vec3(side * p.upperLegLength * 0.9f, p.upperLegLength * 0.4f, 0.0f);
    const glm::vec4 legColor(glm::vec3(p.baseColor) * 0.8f, 1.0f);
    auto limb = [&](const glm::vec3& a, const glm::vec3& b, float radius, const std::string& name) {
        const glm::vec3 axis = b - a;
        const float len = glm::length(axis);
        const glm::quat rot = len > 1e-5f ? rotationBetween(glm::vec3(0, 1, 0), axis / len) : glm::quat(1, 0, 0, 0);
        appendPart(*mesh, cylinder(radius, len, 8), trs((a + b) * 0.5f, rot), name, 0, legColor);
    };
    limb(hip, knee, p.jointRadius * 0.8f, "upper");
    appendPart(*mesh, sphere(p.jointRadius, 8), trs(knee), "knee", 1, glm::vec4(0.3f, 0.3f, 0.32f, 1.0f));
    limb(knee, foot, p.jointRadius * 0.6f, "lower");
    const std::string footType = lower(p.footType);
    if (footType == "pad") {
        appendPart(*mesh, sphere(p.jointRadius * 1.5f, 8), trs(foot, glm::quat(1, 0, 0, 0), glm::vec3(1.0f, 0.3f, 1.0f)),
                   "foot", 1, legColor);
    } else if (footType == "spike") {
        appendPart(*mesh, cylinder(p.jointRadius * 0.2f, p.jointRadius * 3.0f, 6), trs(foot), "foot", 1, legColor);
    } else {   // Claw
        for (int toe = -1; toe <= 1; ++toe) {
            appendPart(*mesh, box(glm::vec3(p.jointRadius * 0.3f, p.jointRadius * 0.3f, p.jointRadius * 1.5f)),
                       trs(foot + glm::vec3(toe * p.jointRadius * 0.5f, 0.0f, 0.0f)), "claw", 1, legColor);
        }
    }
    if (p.armorPlates) {
        appendPart(*mesh, box(glm::vec3(p.upperLegLength * 0.6f, 0.02f, p.jointRadius * 2.0f)),
                   trs((hip + knee) * 0.5f + glm::vec3(0.0f, p.jointRadius, 0.0f)), "leg_armor", 1,
                   glm::vec4(glm::vec3(p.baseColor) * 0.6f, 1.0f));
    }
    return storeMesh(mesh);
}

std::vector<MeshHandle> CentipedeLegGenerator::buildAllLegs(const CentipedeMechParams& p) {
    std::vector<MeshHandle> legs;
    for (int s = 0; s < std::max(1, p.segmentCount); ++s) {
        for (int l = 0; l < p.legsPerSegment; ++l) legs.push_back(buildSingleLeg(p, s, l));
    }
    return legs;
}

MeshHandle CentipedeCockpitGenerator::buildCockpit(const CentipedeMechParams& p) {
    auto mesh = makeMesh(p.id + "_cockpit");
    const glm::vec3 base = p.cockpitPosition + glm::vec3(0.0f, p.segmentRadius, p.segmentLength * 0.25f);
    const glm::vec4 shell(glm::vec3(p.baseColor) * 0.7f, 1.0f);
    appendPart(*mesh, box(glm::vec3(p.cockpitWidth, p.cockpitHeight * 0.4f, p.cockpitDepth)),
               trs(base + glm::vec3(0.0f, p.cockpitHeight * 0.2f, 0.0f)), "shell", 0, shell);
    appendPart(*mesh, sphere(1.0f, 16),
               trs(base + glm::vec3(0.0f, p.cockpitHeight * 0.4f, 0.0f), glm::quat(1, 0, 0, 0),
                   glm::vec3(p.cockpitWidth * 0.5f, p.cockpitHeight * 0.6f, p.cockpitDepth * 0.5f)),
               "canopy", 3, glm::vec4(0.1f, 0.15f, 0.2f, 0.35f));
    const std::string seat = lower(p.seatMaterial);
    const glm::vec4 seatColor = seat == "leather" ? glm::vec4(0.35f, 0.2f, 0.1f, 1.0f) : glm::vec4(0.2f, 0.2f, 0.25f, 1.0f);
    appendPart(*mesh, box(glm::vec3(p.cockpitWidth * 0.4f, p.cockpitHeight * 0.3f, p.cockpitDepth * 0.3f)),
               trs(base + glm::vec3(0.0f, p.cockpitHeight * 0.35f, -p.cockpitDepth * 0.1f)), "seat", 0, seatColor);
    if (p.enableDisplays) {
        const bool holo = lower(p.controlStyle) == "holographic";
        for (int d = 0; d < p.displayCount; ++d) {
            const float x = (static_cast<float>(d) + 0.5f) / p.displayCount - 0.5f;
            appendPart(*mesh, box(glm::vec3(p.cockpitWidth * 0.8f / p.displayCount, p.cockpitHeight * 0.15f, 0.01f)),
                       trs(base + glm::vec3(x * p.cockpitWidth * 0.8f, p.cockpitHeight * 0.5f, p.cockpitDepth * 0.35f)),
                       "display_" + std::to_string(d), 2,
                       holo ? glm::vec4(0.3f, 1.0f, 0.7f, 0.5f) : glm::vec4(0.1f, 0.5f, 0.8f, 1.0f));
        }
    }
    return storeMesh(mesh);
}

MeshHandle CentipedeWeaponGenerator::createMissileTube(const CentipedeMechParams& p, int tubeIndex) {
    auto mesh = makeMesh(p.id + "_missile_tube_" + std::to_string(tubeIndex));
    const float side = (tubeIndex % 2 == 0) ? -1.0f : 1.0f;
    const glm::vec3 pos(side * p.segmentRadius * 0.6f, p.segmentRadius * 1.2f,
                        centipedeSegmentZ(p, std::min(1, p.segmentCount - 1)) - 0.15f * (tubeIndex / 2));
    appendPart(*mesh, cylinder(p.segmentRadius * 0.15f, p.segmentLength * 0.6f, 12), trs(pos, yToZ()),
               "missile_tube", 1, glm::vec4(0.25f, 0.25f, 0.28f, 1.0f));
    return storeMesh(mesh);
}

MeshHandle CentipedeWeaponGenerator::createAutocannon(const CentipedeMechParams& p, int slotIndex) {
    auto mesh = makeMesh(p.id + "_autocannon_" + std::to_string(slotIndex));
    const glm::vec3 pos(0.0f, -p.segmentRadius * 0.6f, p.segmentLength * 0.5f + 0.1f * slotIndex);
    appendPart(*mesh, box(glm::vec3(p.segmentRadius * 0.5f)), trs(pos), "breech", 1, glm::vec4(0.2f, 0.2f, 0.22f, 1.0f));
    appendPart(*mesh, cylinder(p.segmentRadius * 0.06f, p.segmentLength, 8),
               trs(pos + glm::vec3(0.0f, 0.0f, p.segmentLength * 0.5f), yToZ()), "barrel", 1,
               glm::vec4(0.15f, 0.15f, 0.17f, 1.0f));
    return storeMesh(mesh);
}

MeshHandle CentipedeWeaponGenerator::createTurret(const CentipedeMechParams& p) {
    auto mesh = makeMesh(p.id + "_turret");
    const glm::vec3 pos(0.0f, p.segmentRadius * 1.3f, centipedeSegmentZ(p, std::max(0, p.segmentCount / 2)));
    appendPart(*mesh, cylinder(p.segmentRadius * 0.5f, p.segmentRadius * 0.3f, 16), trs(pos), "turret_base", 1,
               glm::vec4(0.25f, 0.25f, 0.28f, 1.0f));
    for (int b = -1; b <= 1; b += 2) {
        appendPart(*mesh, cylinder(p.segmentRadius * 0.05f, p.segmentLength * 0.8f, 8),
                   trs(pos + glm::vec3(b * p.segmentRadius * 0.15f, p.segmentRadius * 0.1f, p.segmentLength * 0.4f), yToZ()),
                   "turret_barrel", 1, glm::vec4(0.15f, 0.15f, 0.17f, 1.0f));
    }
    return storeMesh(mesh);
}

MeshHandle CentipedeWeaponGenerator::createWeaponBarrel(const CentipedeMechParams& p, const std::string& weaponType) {
    const std::string type = lower(weaponType);
    if (type.find("missile") != std::string::npos) return createMissileTube(p, 0);
    if (type.find("turret") != std::string::npos) return createTurret(p);
    return createAutocannon(p, 0);
}

std::vector<MeshHandle> CentipedeWeaponGenerator::buildWeapons(const CentipedeMechParams& p) {
    std::vector<MeshHandle> weapons;
    for (int i = 0; i < p.missileTubes; ++i) weapons.push_back(createMissileTube(p, i));
    for (int i = 0; i < p.autocannonSlots; ++i) weapons.push_back(createAutocannon(p, i));
    if (p.enableTurret) weapons.push_back(createTurret(p));
    return weapons;
}

MeshHandle CentipedeSensorGenerator::createSensorDish(const CentipedeMechParams& p) {
    auto mesh = makeMesh(p.id + "_sensor_dish");
    // Dish size grows with radar range (300 m -> 0.5 m dish)
    const float r = std::clamp(p.radarRange / 600.0f, 0.15f, 1.5f);
    appendPart(*mesh, sphere(r, 12), trs(glm::vec3(0.0f, p.segmentRadius * 2.0f, 0.0f), glm::quat(1, 0, 0, 0),
                                          glm::vec3(1.0f, 0.25f, 1.0f)),
               "dish", 1, glm::vec4(0.7f, 0.7f, 0.72f, 1.0f));
    return storeMesh(mesh);
}

MeshHandle CentipedeSensorGenerator::createSensorAntenna(const CentipedeMechParams& p) {
    auto mesh = makeMesh(p.id + "_sensor_antenna");
    appendPart(*mesh, cylinder(0.01f, p.segmentRadius * 2.0f, 6),
               trs(glm::vec3(p.segmentRadius * 0.4f, p.segmentRadius * 2.0f, -p.segmentLength * 0.2f)), "antenna", 1,
               glm::vec4(0.5f, 0.5f, 0.5f, 1.0f));
    return storeMesh(mesh);
}

MeshHandle CentipedeSensorGenerator::createRadarArray(const CentipedeMechParams& p) {
    auto mesh = makeMesh(p.id + "_radar_array");
    const float r = std::clamp(p.radarRange / 600.0f, 0.15f, 1.5f);
    appendPart(*mesh, cylinder(0.03f, p.segmentRadius * 1.5f, 8),
               trs(glm::vec3(0.0f, p.segmentRadius * 1.25f, 0.0f)), "mast", 1, glm::vec4(0.4f, 0.4f, 0.42f, 1.0f));
    appendPart(*mesh, sphere(r, 12), trs(glm::vec3(0.0f, p.segmentRadius * 2.0f, 0.0f), glm::quat(1, 0, 0, 0),
                                          glm::vec3(1.0f, 0.25f, 1.0f)),
               "dish", 1, glm::vec4(0.7f, 0.7f, 0.72f, 1.0f));
    appendPart(*mesh, cylinder(0.01f, p.segmentRadius * 2.0f, 6),
               trs(glm::vec3(p.segmentRadius * 0.4f, p.segmentRadius * 2.0f, -p.segmentLength * 0.2f)), "antenna", 1,
               glm::vec4(0.5f, 0.5f, 0.5f, 1.0f));
    return storeMesh(mesh);
}

MeshHandle CentipedeSensorGenerator::buildSensorArray(const CentipedeMechParams& p) {
    return p.enableRadarArray ? createRadarArray(p) : createSensorAntenna(p);
}

MaterialHandle CentipedeMaterialGenerator::createMaterialFromColor(const glm::vec4& color, float metallic, float roughness) {
    return storeMaterial("centipede_material", color, metallic, roughness);
}

MaterialHandle CentipedeMaterialGenerator::createHullMaterial(const CentipedeMechParams& p) {
    return storeMaterial(p.id + "_hull", p.baseColor, 0.7f, 0.4f);
}
MaterialHandle CentipedeMaterialGenerator::createJointMaterial(const CentipedeMechParams& p) {
    return storeMaterial(p.id + "_joint", glm::vec4(0.3f, 0.3f, 0.32f, 1.0f), 0.9f, 0.3f);
}
MaterialHandle CentipedeMaterialGenerator::createLegMaterial(const CentipedeMechParams& p) {
    return storeMaterial(p.id + "_leg", glm::vec4(glm::vec3(p.baseColor) * 0.8f, 1.0f), 0.75f, 0.45f);
}
MaterialHandle CentipedeMaterialGenerator::createCockpitMaterial(const CentipedeMechParams& p) {
    const bool holo = lower(p.controlStyle) == "holographic";
    return storeMaterial(p.id + "_cockpit", glm::vec4(0.1f, 0.15f, 0.2f, 0.35f), 0.0f, 0.05f,
                         holo ? glm::vec3(0.3f, 1.0f, 0.7f) : glm::vec3(0.1f, 0.5f, 0.8f), p.enableDisplays ? 1.5f : 0.0f);
}
MaterialHandle CentipedeMaterialGenerator::createWeaponMaterial(const CentipedeMechParams& p) {
    return storeMaterial(p.id + "_weapon", glm::vec4(0.2f, 0.2f, 0.22f, 1.0f), 0.95f, 0.35f);
}
MaterialHandle CentipedeMaterialGenerator::createSensorMaterial(const CentipedeMechParams& p) {
    return storeMaterial(p.id + "_sensor", glm::vec4(0.7f, 0.7f, 0.72f, 1.0f), 0.8f, 0.25f);
}

std::vector<MaterialHandle> CentipedeMaterialGenerator::assignMechMaterials(const CentipedeMechParams& p) {
    return {createHullMaterial(p), createJointMaterial(p), createLegMaterial(p),
            createCockpitMaterial(p), createWeaponMaterial(p), createSensorMaterial(p)};
}

ParticleHandle CentipedeVFXGenerator::createThrusterFX(const CentipedeMechParams& p, int segmentIndex) {
    const glm::vec3 pos(0.0f, 0.0f, centipedeSegmentZ(p, segmentIndex) - p.segmentLength * 0.5f);
    return storeParticles(p.id + "_thruster_" + std::to_string(segmentIndex), 60.0f, 0.5f, 4.0f, 0.08f,
                          glm::vec4(0.4f, 0.7f, 1.0f, 1.0f), {pos});
}

ParticleHandle CentipedeVFXGenerator::createDamageSparks(const CentipedeMechParams& p) {
    std::vector<glm::vec3> joints;
    for (int j = 0; j + 1 < std::max(1, p.segmentCount); ++j) {
        joints.emplace_back(0.0f, 0.0f, centipedeSegmentZ(p, j) - p.segmentLength * 0.5f);
    }
    return storeParticles(p.id + "_damage_sparks", 15.0f, 0.4f, 2.5f, 0.02f, glm::vec4(1.0f, 0.8f, 0.4f, 1.0f),
                          std::move(joints));
}

ParticleHandle CentipedeVFXGenerator::createLegImpactFX(const CentipedeMechParams& p, int segmentIndex, int legIndex) {
    return storeParticles(p.id + "_impact_" + std::to_string(segmentIndex) + "_" + std::to_string(legIndex), 0.0f, 0.8f,
                          0.6f, 0.1f, glm::vec4(0.55f, 0.5f, 0.45f, 0.7f), {centipedeFoot(p, segmentIndex, legIndex)});
}

std::vector<ParticleHandle> CentipedeVFXGenerator::buildDamageAndThrusterFX(const CentipedeMechParams& p) {
    std::vector<ParticleHandle> fx;
    fx.push_back(createThrusterFX(p, std::max(0, p.segmentCount - 1)));
    fx.push_back(createDamageSparks(p));
    for (int s = 0; s < std::max(1, p.segmentCount); ++s) {
        for (int l = 0; l < p.legsPerSegment; ++l) fx.push_back(createLegImpactFX(p, s, l));
    }
    return fx;
}

AudioHandle CentipedeAudioGenerator::createStepSounds(const CentipedeMechParams& p) {
    // A full leg wave every second, so steps per second = total leg count
    return storeAudio(p.id + "_steps", "footstep", static_cast<float>(std::max(1, p.segmentCount * p.legsPerSegment)),
                      0.6f, 1.0f + 0.3f * (1.0f - std::clamp(p.segmentRadius, 0.0f, 1.0f)), true);
}
AudioHandle CentipedeAudioGenerator::createJointCreaks(const CentipedeMechParams& p) {
    return storeAudio(p.id + "_creaks", "joint", 0.5f, 0.3f, 0.8f, true);
}
AudioHandle CentipedeAudioGenerator::createCockpitHum(const CentipedeMechParams& p) {
    return storeAudio(p.id + "_cockpit_hum", "ambience", 0.0f, 0.25f, 1.0f, true);
}
AudioHandle CentipedeAudioGenerator::createWeaponFire(const CentipedeMechParams& p) {
    return storeAudio(p.id + "_weapon_fire", "weapon", 0.0f, 1.0f, p.missileTubes > 0 ? 0.8f : 1.2f, false);
}

std::vector<AudioHandle> CentipedeAudioGenerator::buildMechSounds(const CentipedeMechParams& p) {
    std::vector<AudioHandle> audio{createStepSounds(p), createJointCreaks(p)};
    if (p.hasCockpit) audio.push_back(createCockpitHum(p));
    if (p.missileTubes > 0 || p.autocannonSlots > 0 || p.enableTurret) audio.push_back(createWeaponFire(p));
    return audio;
}

PhysicsHandle CentipedeCollisionGenerator::buildMechCollider(const CentipedeMechParams& p) {
    auto physics = std::make_shared<MechPhysicsData>();
    physics->name = p.id + "_collider";
    const float segmentMass = 50.0f * p.segmentRadius * p.segmentLength;
    for (int s = 0; s < std::max(1, p.segmentCount); ++s) {
        const float z = centipedeSegmentZ(p, s);
        physics->shapes.push_back(capsuleShape(glm::vec3(0, 0, z + p.segmentLength * 0.5f),
                                               glm::vec3(0, 0, z - p.segmentLength * 0.5f), p.segmentRadius, segmentMass));
        for (int l = 0; l < p.legsPerSegment; ++l) {
            physics->shapes.push_back(capsuleShape(centipedeHip(p, s, l), centipedeFoot(p, s, l), p.jointRadius,
                                                   segmentMass * 0.1f));
        }
    }
    if (p.hasCockpit) {
        MechColliderShape cockpit;
        cockpit.type = MechColliderShape::Type::Box;
        cockpit.size = glm::vec3(p.cockpitWidth, p.cockpitHeight, p.cockpitDepth);
        cockpit.transform = trs(p.cockpitPosition + glm::vec3(0.0f, p.segmentRadius + p.cockpitHeight * 0.5f, 0.0f));
        cockpit.mass = segmentMass * 0.5f;
        physics->shapes.push_back(cockpit);
    }
    finalizePhysics(*physics);
    return assets().add(physics);
}

} // namespace Mechs
} // namespace MagiTech
