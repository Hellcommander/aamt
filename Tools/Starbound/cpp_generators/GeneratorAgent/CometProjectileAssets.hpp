#pragma once

/**
 * Asset store and geometry/noise helpers for the comet projectile generators.
 *
 * The generators build CPU-side mesh / texture data and particle descriptions and
 * return handles (from MagiTech::nextAssetHandle, so they never collide with other
 * GeneratorAgent assets). The store keeps that data addressable by handle so later
 * stages (deformation passes, merging, export to OpenStarbound projectile configs,
 * GPU upload) can retrieve and update it.
 */

#include "CometProjectileTypes.hpp"
#include <cstdint>
#include <memory>
#include <optional>
#include <string>
#include <vector>
#include <glm/glm.hpp>

namespace MagiTech {
namespace CometProjectiles {

struct CometMeshData {
    std::vector<glm::vec3> vertices;
    std::vector<glm::vec3> normals;
    std::vector<glm::vec2> uvs;
    std::vector<uint32_t> indices;
};

struct CometTextureData {
    int width = 0;
    int height = 0;
    std::vector<uint8_t> rgba;   // width * height * 4 bytes
    bool generateMipmaps = false;
};

/** Particle emitter kinds used by the comet generators. */
enum class ParticleType {
    BILLBOARD,  // camera-facing dust puffs
    POINT,      // small bright sparks
    MESH        // mesh fragments (debris)
};

struct ParticleEmitterDesc {
    ParticleType type = ParticleType::BILLBOARD;
    float rate = 0.0f;
    float lifetime = 1.0f;
    glm::vec4 startColor{1.0f};
    glm::vec4 endColor{1.0f, 1.0f, 1.0f, 0.0f};
    float startSize = 0.1f;
    float endSize = 0.0f;
    glm::vec3 velocity{0.0f};
    float velocityVariation = 0.0f;
    glm::vec3 gravity{0.0f};
    bool enableFade = true;
    float fadeSpeed = 1.0f;
    bool enablePhysics = false;
    float spread = 0.0f;         // emission cone / radius
};

// Meshes
MeshHandle createMeshHandle();
void uploadMeshData(MeshHandle handle,
                    const std::vector<glm::vec3>& vertices,
                    const std::vector<glm::vec3>& normals,
                    const std::vector<glm::vec2>& uvs,
                    const std::vector<uint32_t>& indices);
/** Copies the stored data into the output vectors; returns false (outputs cleared) for unknown handles. */
bool downloadMeshData(MeshHandle handle,
                      std::vector<glm::vec3>& vertices,
                      std::vector<glm::vec3>& normals,
                      std::vector<glm::vec2>& uvs,
                      std::vector<uint32_t>& indices);
std::optional<CometMeshData> getMeshData(MeshHandle handle);
void destroyMeshHandle(MeshHandle handle);

// Textures (RGBA8)
TextureHandle createTextureHandle();
void uploadTextureData(TextureHandle handle, int width, int height, const uint8_t* rgba, bool generateMipmaps);
std::optional<CometTextureData> getTextureData(TextureHandle handle);

// Particles: the OpenStarbound particle config is kept with the description
ParticleHandle createParticleEmitter(const ParticleEmitterDesc& desc);
std::optional<ParticleEmitterDesc> getParticleEmitterDesc(ParticleHandle handle);
std::optional<std::string> getParticleConfigJson(ParticleHandle handle);

/** Drops every stored comet asset (handles stay unique). */
void clearCometAssets();

// Geometry helpers
/** Subdivided icosahedron of the given radius (detail = subdivision passes). */
void generateIcosphereGeometry(float radius, int detail,
                               std::vector<glm::vec3>& vertices,
                               std::vector<glm::vec3>& normals,
                               std::vector<glm::vec2>& uvs,
                               std::vector<uint32_t>& indices);
/** Smooth (area-weighted) vertex normals from the triangle list. */
void recalculateNormals(const std::vector<glm::vec3>& vertices,
                        const std::vector<uint32_t>& indices,
                        std::vector<glm::vec3>& normals);

/** Gradient-noise helpers used for mesh deformation and textures. */
class CometNoise {
public:
    explicit CometNoise(int seed = 1337);
    /** Scalar Perlin noise in [-1, 1]. */
    float perlin3D(const glm::vec3& p) const;
    /** Vector-valued Perlin noise (three decorrelated channels, each in [-1, 1]). */
    glm::vec3 perlinVec3(const glm::vec3& p) const;
    /** Vector-valued fractal (fBm) noise with the given number of octaves. */
    glm::vec3 fractalVec3(const glm::vec3& p, int octaves) const;
    /** Divergence-free curl of a vector noise potential (finite differences). */
    glm::vec3 curl3D(const glm::vec3& p) const;

private:
    struct Impl;                         // FastNoiseLite generators (kept out of the header)
    std::shared_ptr<const Impl> m_impl;
};

} // namespace CometProjectiles
} // namespace MagiTech
