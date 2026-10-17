#pragma once

/**
 * Asset store for the flame projectile generators.
 *
 * Generated meshes, RGBA textures, shader sources and OpenStarbound particle
 * configs are kept addressable by the handle the generators return (handles come
 * from MagiTech::nextAssetHandle, so they never collide with other GeneratorAgent
 * assets). Merging and export stages read them back from here.
 */

#include "FlameProjectileTypes.hpp"
#include "core/rendering/GeneratedMesh.hpp"
#include <cstdint>
#include <optional>
#include <string>
#include <vector>

namespace MagiTech {
namespace FlameProjectiles {

struct FlameTextureData {
    int width = 0;
    int height = 0;
    std::vector<uint8_t> rgba;   // width * height * 4 bytes
};

struct FlameShaderSource {
    std::string vertexSource;
    std::string fragmentSource;
    std::string blendMode;
};

// Meshes (an empty mesh is not stored and yields handle 0)
MeshHandle storeMesh(const MagiTech::Mesh& mesh);
std::optional<MagiTech::Mesh> getMesh(MeshHandle handle);

// Textures (RGBA8)
TextureHandle storeTexture(int width, int height, std::vector<uint8_t> rgba);
std::optional<FlameTextureData> getTexture(TextureHandle handle);

// Shaders: remember the source a compiled handle was built from
void storeShaderSource(ShaderHandle handle, FlameShaderSource source);
std::optional<FlameShaderSource> getShaderSource(ShaderHandle handle);

// Particles: OpenStarbound particle config JSON for an emitter handle
void storeParticleConfig(ParticleHandle handle, std::string configJson);
std::optional<std::string> getParticleConfig(ParticleHandle handle);

/** Drops every stored flame asset (handles stay unique). */
void clearFlameAssets();

} // namespace FlameProjectiles
} // namespace MagiTech
