#pragma once

/**
 * Asset store for the lightning projectile generators.
 *
 * The generators build CPU-side mesh / texture data and particle / audio
 * descriptions. This store keeps that data addressable by the handle the
 * generators return (handles come from MagiTech::nextAssetHandle so they never
 * collide with other GeneratorAgent assets), so later stages (merging, export
 * to OpenStarbound projectile configs, GPU upload) can retrieve it.
 */

#include "LightningProjectileTypes.hpp"
#include "core/particles/ParticleBuilder.hpp"
#include <cstdint>
#include <optional>
#include <string>
#include <vector>
#include <glm/glm.hpp>

namespace MagiTech {
namespace LightningProjectiles {

struct LightningMeshData {
    std::vector<glm::vec3> vertices;
    std::vector<glm::vec3> normals;
    std::vector<glm::vec2> uvs;
    std::vector<uint32_t> indices;
};

struct LightningTextureData {
    int width = 0;
    int height = 0;
    std::vector<uint8_t> rgba;   // width * height * 4 bytes
    bool generateMipmaps = false;
};

struct ParticleEmitterDesc {
    MagiTech::ParticleType type = MagiTech::ParticleType::BURST;
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
};

enum class ProceduralAudioType {
    CRACKLE,
    ZAP,
    ELECTRIC,
    THUNDER
};

struct ProceduralAudioDesc {
    ProceduralAudioType type = ProceduralAudioType::CRACKLE;
    float duration = 1.0f;
    float pitch = 1.0f;
    float volume = 1.0f;
    float intensity = 1.0f;
    bool enableSpatialAudio = false;
    float distance = 10.0f;
};

// Meshes
MeshHandle createMeshHandle();
void uploadMeshData(MeshHandle handle,
                    const std::vector<glm::vec3>& vertices,
                    const std::vector<glm::vec3>& normals,
                    const std::vector<glm::vec2>& uvs,
                    const std::vector<uint32_t>& indices);
std::optional<LightningMeshData> getMeshData(MeshHandle handle);

// Textures (RGBA8)
TextureHandle createTextureHandle();
void uploadTextureData(TextureHandle handle, int width, int height, const uint8_t* rgba, bool generateMipmaps);
std::optional<LightningTextureData> getTextureData(TextureHandle handle);

// Particles: returns a handle whose OpenStarbound particle config is kept in the store
ParticleHandle createParticleEmitter(const ParticleEmitterDesc& desc);
std::optional<ParticleEmitterDesc> getParticleEmitterDesc(ParticleHandle handle);
std::optional<std::string> getParticleConfigJson(ParticleHandle handle);

// Audio: returns a handle whose OpenStarbound sound path is kept in the store
AudioHandle createProceduralAudio(const ProceduralAudioDesc& desc);
std::optional<ProceduralAudioDesc> getProceduralAudioDesc(AudioHandle handle);
std::optional<std::string> getAudioPath(AudioHandle handle);

/** Drops every stored lightning asset (handles stay unique). */
void clearLightningAssets();

} // namespace LightningProjectiles
} // namespace MagiTech
