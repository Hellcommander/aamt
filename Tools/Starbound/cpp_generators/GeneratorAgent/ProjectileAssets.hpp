#pragma once

/**
 * Asset store and particle-effect description for the generic projectile generators.
 *
 * Meshes, RGBA textures and effects stay addressable by the handle the generators
 * return (handles come from MagiTech::nextAssetHandle, unique across asset families).
 */

#include "ProjectileTypes.hpp"
#include "core/rendering/GeneratedMesh.hpp"
#include <map>
#include <optional>
#include <string>
#include <utility>
#include <variant>
#include <vector>
#include <glm/glm.hpp>

namespace MagiTech {
namespace Projectiles {

using EffectParamValue = std::variant<float, int, std::string, glm::vec3>;
using EffectParams = std::map<std::string, EffectParamValue>;

struct ProjectileParticleSystem {
    std::string name;      // OpenStarbound particle / effect name, e.g. "ember_trail"
    EffectParams params;
};

/** A projectile effect: one or more named particle systems with their parameters. */
class ProjectileEffect {
public:
    ProjectileEffect& addParticleSystem(const std::string& name, EffectParams params) {
        m_systems.push_back({name, std::move(params)});
        return *this;
    }

    const std::vector<ProjectileParticleSystem>& systems() const { return m_systems; }

    /** OpenStarbound-style JSON array: [{"name": ..., "parameters": {...}}, ...] */
    std::string toJson() const;

    /** Registers the effect in the projectile asset store; 0 when it has no systems. */
    EffectHandle upload() const;

private:
    std::vector<ProjectileParticleSystem> m_systems;
};

struct ProjectileTextureData {
    int width = 0;
    int height = 0;
    std::vector<glm::u8vec4> pixels;
};

MeshHandle storeProjectileMesh(const MagiTech::Mesh& mesh);
std::optional<MagiTech::Mesh> getProjectileMesh(MeshHandle handle);

TextureHandle storeProjectileTexture(int width, int height, std::vector<glm::u8vec4> pixels);
std::optional<ProjectileTextureData> getProjectileTexture(TextureHandle handle);

std::optional<ProjectileEffect> getProjectileEffect(EffectHandle handle);

/** Drops every stored projectile asset (handles stay unique). */
void clearProjectileAssets();

} // namespace Projectiles
} // namespace MagiTech
