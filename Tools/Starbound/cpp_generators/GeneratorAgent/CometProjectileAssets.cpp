#include "CometProjectileAssets.hpp"
#include "core/particles/ParticleBuilder.hpp"
#include "core/rendering/AssetHandle.hpp"
#include "vendor/FastNoiseLite/Cpp/FastNoiseLite.h"
#include <algorithm>
#include <cmath>
#include <map>
#include <mutex>
#include <unordered_map>
#include <utility>

namespace MagiTech {
namespace CometProjectiles {

namespace {

struct StoredParticle {
    ParticleEmitterDesc desc;
    std::string configJson;
};

struct AssetStore {
    std::mutex mutex;
    std::unordered_map<MeshHandle, CometMeshData> meshes;
    std::unordered_map<TextureHandle, CometTextureData> textures;
    std::unordered_map<ParticleHandle, StoredParticle> particles;
};

AssetStore& store() {
    static AssetStore s;
    return s;
}

MagiTech::ParticleType toBuilderParticleType(ParticleType type) {
    switch (type) {
        case ParticleType::BILLBOARD: return MagiTech::ParticleType::BILLBOARD;
        case ParticleType::POINT:     return MagiTech::ParticleType::EMBER;
        case ParticleType::MESH:      return MagiTech::ParticleType::SHARD_BURST;
    }
    return MagiTech::ParticleType::BURST;
}

} // namespace

// ---------------------------------------------------------------------------
// Meshes
// ---------------------------------------------------------------------------

MeshHandle createMeshHandle() {
    return nextAssetHandle();
}

void uploadMeshData(MeshHandle handle,
                    const std::vector<glm::vec3>& vertices,
                    const std::vector<glm::vec3>& normals,
                    const std::vector<glm::vec2>& uvs,
                    const std::vector<uint32_t>& indices) {
    CometMeshData data{vertices, normals, uvs, indices};
    std::lock_guard<std::mutex> lock(store().mutex);
    store().meshes[handle] = std::move(data);
}

bool downloadMeshData(MeshHandle handle,
                      std::vector<glm::vec3>& vertices,
                      std::vector<glm::vec3>& normals,
                      std::vector<glm::vec2>& uvs,
                      std::vector<uint32_t>& indices) {
    std::lock_guard<std::mutex> lock(store().mutex);
    auto it = store().meshes.find(handle);
    if (it == store().meshes.end()) {
        vertices.clear();
        normals.clear();
        uvs.clear();
        indices.clear();
        return false;
    }
    vertices = it->second.vertices;
    normals = it->second.normals;
    uvs = it->second.uvs;
    indices = it->second.indices;
    return true;
}

std::optional<CometMeshData> getMeshData(MeshHandle handle) {
    std::lock_guard<std::mutex> lock(store().mutex);
    auto it = store().meshes.find(handle);
    if (it == store().meshes.end()) return std::nullopt;
    return it->second;
}

void destroyMeshHandle(MeshHandle handle) {
    std::lock_guard<std::mutex> lock(store().mutex);
    store().meshes.erase(handle);
}

// ---------------------------------------------------------------------------
// Textures
// ---------------------------------------------------------------------------

TextureHandle createTextureHandle() {
    return nextAssetHandle();
}

void uploadTextureData(TextureHandle handle, int width, int height, const uint8_t* rgba, bool generateMipmaps) {
    CometTextureData data;
    data.width = width;
    data.height = height;
    data.generateMipmaps = generateMipmaps;
    if (rgba && width > 0 && height > 0) {
        data.rgba.assign(rgba, rgba + static_cast<size_t>(width) * static_cast<size_t>(height) * 4);
    }
    std::lock_guard<std::mutex> lock(store().mutex);
    store().textures[handle] = std::move(data);
}

std::optional<CometTextureData> getTextureData(TextureHandle handle) {
    std::lock_guard<std::mutex> lock(store().mutex);
    auto it = store().textures.find(handle);
    if (it == store().textures.end()) return std::nullopt;
    return it->second;
}

// ---------------------------------------------------------------------------
// Particles
// ---------------------------------------------------------------------------

ParticleHandle createParticleEmitter(const ParticleEmitterDesc& desc) {
    MagiTech::ParticleEmitter emitter = MagiTech::ParticleBuilder::createEmitter(toBuilderParticleType(desc.type));
    const float endAlpha = desc.enableFade ? desc.endColor.a : desc.startColor.a;
    emitter.setRate(desc.rate)
        .setCount(static_cast<int>(desc.rate))
        .setLifetime(desc.lifetime)
        .setStartSize(desc.startSize)
        .setEndSize(desc.endSize)
        .setColor(desc.startColor)
        .setAlpha(desc.startColor.a, endAlpha)
        .setSpeed(desc.velocityVariation)
        .setGravity(desc.gravity);
    if (desc.spread > 0.0f) {
        emitter.setShape(MagiTech::ParticleShape::SPHERE).setRadius(desc.spread);
    }
    if (glm::length(desc.velocity) > 0.0f) {
        emitter.setDirection(glm::normalize(desc.velocity));
    }
    if (desc.type == ParticleType::MESH) {
        emitter.setCollidesForeground(desc.enablePhysics);
    }

    const ParticleHandle handle = emitter.getHandle();
    StoredParticle stored{desc, emitter.toOpenStarboundParticleJson()};
    std::lock_guard<std::mutex> lock(store().mutex);
    store().particles[handle] = std::move(stored);
    return handle;
}

std::optional<ParticleEmitterDesc> getParticleEmitterDesc(ParticleHandle handle) {
    std::lock_guard<std::mutex> lock(store().mutex);
    auto it = store().particles.find(handle);
    if (it == store().particles.end()) return std::nullopt;
    return it->second.desc;
}

std::optional<std::string> getParticleConfigJson(ParticleHandle handle) {
    std::lock_guard<std::mutex> lock(store().mutex);
    auto it = store().particles.find(handle);
    if (it == store().particles.end()) return std::nullopt;
    return it->second.configJson;
}

void clearCometAssets() {
    std::lock_guard<std::mutex> lock(store().mutex);
    store().meshes.clear();
    store().textures.clear();
    store().particles.clear();
}

// ---------------------------------------------------------------------------
// Geometry helpers
// ---------------------------------------------------------------------------

void generateIcosphereGeometry(float radius, int detail,
                               std::vector<glm::vec3>& vertices,
                               std::vector<glm::vec3>& normals,
                               std::vector<glm::vec2>& uvs,
                               std::vector<uint32_t>& indices) {
    // Unit icosahedron
    const float t = (1.0f + std::sqrt(5.0f)) * 0.5f;
    std::vector<glm::vec3> pts = {
        {-1,  t,  0}, { 1,  t,  0}, {-1, -t,  0}, { 1, -t,  0},
        { 0, -1,  t}, { 0,  1,  t}, { 0, -1, -t}, { 0,  1, -t},
        { t,  0, -1}, { t,  0,  1}, {-t,  0, -1}, {-t,  0,  1},
    };
    for (auto& p : pts) p = glm::normalize(p);

    std::vector<uint32_t> tris = {
        0, 11, 5,   0, 5, 1,    0, 1, 7,    0, 7, 10,   0, 10, 11,
        1, 5, 9,    5, 11, 4,   11, 10, 2,  10, 7, 6,   7, 1, 8,
        3, 9, 4,    3, 4, 2,    3, 2, 6,    3, 6, 8,    3, 8, 9,
        4, 9, 5,    2, 4, 11,   6, 2, 10,   8, 6, 7,    9, 8, 1,
    };

    // Subdivide, sharing edge midpoints
    const int passes = std::clamp(detail, 0, 7);
    for (int pass = 0; pass < passes; ++pass) {
        std::map<std::pair<uint32_t, uint32_t>, uint32_t> midpointCache;
        auto midpoint = [&](uint32_t a, uint32_t b) -> uint32_t {
            const auto key = std::minmax(a, b);
            auto it = midpointCache.find(key);
            if (it != midpointCache.end()) return it->second;
            pts.push_back(glm::normalize((pts[a] + pts[b]) * 0.5f));
            const uint32_t idx = static_cast<uint32_t>(pts.size() - 1);
            midpointCache.emplace(key, idx);
            return idx;
        };

        std::vector<uint32_t> next;
        next.reserve(tris.size() * 4);
        for (size_t i = 0; i + 2 < tris.size(); i += 3) {
            const uint32_t a = tris[i], b = tris[i + 1], c = tris[i + 2];
            const uint32_t ab = midpoint(a, b), bc = midpoint(b, c), ca = midpoint(c, a);
            next.insert(next.end(), {a, ab, ca,  b, bc, ab,  c, ca, bc,  ab, bc, ca});
        }
        tris.swap(next);
    }

    constexpr float kPi = 3.14159265358979323846f;
    vertices.clear();
    normals.clear();
    uvs.clear();
    vertices.reserve(pts.size());
    normals.reserve(pts.size());
    uvs.reserve(pts.size());
    for (const auto& p : pts) {
        vertices.push_back(p * radius);
        normals.push_back(p);
        // Spherical mapping
        uvs.emplace_back(0.5f + std::atan2(p.z, p.x) / (2.0f * kPi),
                         0.5f - std::asin(std::clamp(p.y, -1.0f, 1.0f)) / kPi);
    }
    indices = std::move(tris);
}

void recalculateNormals(const std::vector<glm::vec3>& vertices,
                        const std::vector<uint32_t>& indices,
                        std::vector<glm::vec3>& normals) {
    normals.assign(vertices.size(), glm::vec3(0.0f));
    for (size_t i = 0; i + 2 < indices.size(); i += 3) {
        const uint32_t a = indices[i], b = indices[i + 1], c = indices[i + 2];
        if (a >= vertices.size() || b >= vertices.size() || c >= vertices.size()) continue;
        // Unnormalized cross product = area-weighted face normal
        const glm::vec3 faceNormal = glm::cross(vertices[b] - vertices[a], vertices[c] - vertices[a]);
        normals[a] += faceNormal;
        normals[b] += faceNormal;
        normals[c] += faceNormal;
    }
    for (size_t i = 0; i < normals.size(); ++i) {
        const float len = glm::length(normals[i]);
        normals[i] = len > 1e-8f ? normals[i] / len
                                 : (glm::length(vertices[i]) > 1e-8f ? glm::normalize(vertices[i]) : glm::vec3(0, 1, 0));
    }
}

// ---------------------------------------------------------------------------
// Noise
// ---------------------------------------------------------------------------

struct CometNoise::Impl {
    FastNoiseLite channels[3];
};

CometNoise::CometNoise(int seed) {
    auto impl = std::make_shared<Impl>();
    for (int i = 0; i < 3; ++i) {
        impl->channels[i].SetSeed(seed + i * 7919);
        impl->channels[i].SetNoiseType(FastNoiseLite::NoiseType_Perlin);
        impl->channels[i].SetFrequency(1.0f);
    }
    m_impl = std::move(impl);
}

float CometNoise::perlin3D(const glm::vec3& p) const {
    return m_impl->channels[0].GetNoise(p.x, p.y, p.z);
}

glm::vec3 CometNoise::perlinVec3(const glm::vec3& p) const {
    return {m_impl->channels[0].GetNoise(p.x, p.y, p.z),
            m_impl->channels[1].GetNoise(p.x, p.y, p.z),
            m_impl->channels[2].GetNoise(p.x, p.y, p.z)};
}

glm::vec3 CometNoise::fractalVec3(const glm::vec3& p, int octaves) const {
    glm::vec3 sum(0.0f);
    float amplitude = 1.0f;
    float frequency = 1.0f;
    float norm = 0.0f;
    for (int i = 0; i < std::max(octaves, 1); ++i) {
        sum += perlinVec3(p * frequency) * amplitude;
        norm += amplitude;
        amplitude *= 0.5f;
        frequency *= 2.0f;
    }
    return sum / norm;
}

glm::vec3 CometNoise::curl3D(const glm::vec3& p) const {
    // curl(F) for the vector potential F = perlinVec3, via central differences
    const float e = 1e-3f;
    const glm::vec3 dx(e, 0, 0), dy(0, e, 0), dz(0, 0, e);
    const glm::vec3 fx1 = perlinVec3(p + dx), fx0 = perlinVec3(p - dx);
    const glm::vec3 fy1 = perlinVec3(p + dy), fy0 = perlinVec3(p - dy);
    const glm::vec3 fz1 = perlinVec3(p + dz), fz0 = perlinVec3(p - dz);
    const float inv = 1.0f / (2.0f * e);
    const float dFz_dy = (fy1.z - fy0.z) * inv, dFy_dz = (fz1.y - fz0.y) * inv;
    const float dFx_dz = (fz1.x - fz0.x) * inv, dFz_dx = (fx1.z - fx0.z) * inv;
    const float dFy_dx = (fx1.y - fx0.y) * inv, dFx_dy = (fy1.x - fy0.x) * inv;
    return {dFz_dy - dFy_dz, dFx_dz - dFz_dx, dFy_dx - dFx_dy};
}

} // namespace CometProjectiles
} // namespace MagiTech
