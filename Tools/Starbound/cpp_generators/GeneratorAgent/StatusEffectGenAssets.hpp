#pragma once

/**
 * Asset store for the status effect generators (StatusEffectGenerators.cpp).
 *
 * Shader sources, RGBA textures / icons, meshes and OpenStarbound particle configs
 * stay addressable by the handle the generators return. Handles come from
 * MagiTech::nextAssetHandle, so they are unique across threads and asset families.
 */

#include "StatusEffectTypes.hpp"
#include "core/rendering/GeneratedMesh.hpp"
#include <optional>
#include <string>
#include <vector>

namespace MagiTech {
namespace StatusEffects {

struct StatusEffectShaderSource {
    std::string vertexSource;
    std::string fragmentSource;
};

struct StatusEffectTextureData {
    int width = 0;
    int height = 0;
    std::vector<uint8_t> rgba;   // width * height * 4 bytes
};

void storeStatusEffectShader(ShaderHandle handle, StatusEffectShaderSource source);
std::optional<StatusEffectShaderSource> getStatusEffectShader(ShaderHandle handle);

TextureHandle storeStatusEffectTexture(int width, int height, std::vector<uint8_t> rgba);
std::optional<StatusEffectTextureData> getStatusEffectTexture(TextureHandle handle);

MeshHandle storeStatusEffectMesh(const MagiTech::Mesh& mesh);
std::optional<MagiTech::Mesh> getStatusEffectMesh(MeshHandle handle);

ParticleHandle storeStatusEffectParticles(std::string configJson);
std::optional<std::string> getStatusEffectParticles(ParticleHandle handle);

/** Drops every stored status effect asset (handles stay unique). */
void clearStatusEffectAssets();

} // namespace StatusEffects
} // namespace MagiTech
