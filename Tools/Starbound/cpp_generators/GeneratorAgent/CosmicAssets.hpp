#pragma once

/**
 * Asset store for the cosmic generators (cosmic projectiles and space objects).
 *
 * Generated meshes, RGBA textures, shader sources and OpenStarbound particle
 * configs stay addressable by the handle the generators return (handles come from
 * MagiTech::nextAssetHandle, so they never collide with other GeneratorAgent assets).
 */

#include "CosmicAssetBundle.hpp"
#include "core/rendering/GeneratedMesh.hpp"
#include <cstdint>
#include <optional>
#include <string>
#include <vector>

namespace MagiTech {
namespace Cosmic {

struct CosmicTextureData {
    int width = 0;
    int height = 0;
    std::vector<uint8_t> rgba;   // width * height * 4 bytes
};

struct CosmicShaderSource {
    std::string vertexSource;
    std::string fragmentSource;
};

// Meshes (an empty mesh is not stored and yields handle 0)
MeshHandle storeCosmicMesh(const MagiTech::Mesh& mesh);
std::optional<MagiTech::Mesh> getCosmicMesh(MeshHandle handle);

// Textures (RGBA8)
TextureHandle storeCosmicTexture(int width, int height, std::vector<uint8_t> rgba);
std::optional<CosmicTextureData> getCosmicTexture(TextureHandle handle);

// Shaders: remember the source a compiled handle was built from
void storeCosmicShaderSource(ShaderHandle handle, CosmicShaderSource source);
std::optional<CosmicShaderSource> getCosmicShaderSource(ShaderHandle handle);

// Effects: OpenStarbound particle configs (JSON objects) making up one effect
EffectHandle storeCosmicEffect(std::vector<std::string> particleConfigs);
std::optional<std::vector<std::string>> getCosmicEffect(EffectHandle handle);

/** Drops every stored cosmic asset (handles stay unique). */
void clearCosmicAssets();

} // namespace Cosmic
} // namespace MagiTech
