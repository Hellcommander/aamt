#pragma once

/**
 * Asset store plus the particle / physics description builders used by the
 * alchemical grenade generators.
 *
 * Meshes, textures, particle systems and physics setups stay addressable by the
 * handle the generators return (handles come from MagiTech::nextAssetHandle).
 */

#include "AlchemicalGrenadeTypes.hpp"
#include "core/particles/ParticleBuilder.hpp"
#include "core/rendering/GeneratedMesh.hpp"
#include <optional>
#include <string>
#include <vector>
#include <glm/glm.hpp>

namespace MagiTech {
namespace AlchemicalGrenades {

// ---------------------------------------------------------------- particles

struct GrenadeParticleDesc {
    MagiTech::ParticleType type = MagiTech::ParticleType::BURST;
    int count = 1;
    float lifetime = 1.0f;
    float speed = 1.0f;
    float size = 0.1f;
    float spread = 1.0f;          // emission cone half-angle in radians
    float gravity = 0.0f;         // multiple of standard gravity (positive pulls down)
    glm::vec4 color{1.0f};
    std::vector<std::string> effects;   // named OpenStarbound effect / particle presets layered on top
    std::string configJson;             // OpenStarbound particle config for the base emitter
};

/** Builder for a grenade particle system; upload() stores it and returns its handle. */
class GrenadeParticleSystem {
public:
    GrenadeParticleSystem& setType(MagiTech::ParticleType type) { m_desc.type = type; return *this; }
    GrenadeParticleSystem& setCount(int count) { m_desc.count = count; return *this; }
    GrenadeParticleSystem& setLifetime(float lifetime) { m_desc.lifetime = lifetime; return *this; }
    GrenadeParticleSystem& setSpeed(float speed) { m_desc.speed = speed; return *this; }
    GrenadeParticleSystem& setSize(float size) { m_desc.size = size; return *this; }
    GrenadeParticleSystem& setSpread(float spread) { m_desc.spread = spread; return *this; }
    GrenadeParticleSystem& setGravity(float gravity) { m_desc.gravity = gravity; return *this; }
    GrenadeParticleSystem& setColor(const glm::vec3& color) { m_desc.color = glm::vec4(color, 1.0f); return *this; }
    GrenadeParticleSystem& setColor(const glm::vec4& color) { m_desc.color = color; return *this; }
    GrenadeParticleSystem& addEffect(const std::string& effect) { m_desc.effects.push_back(effect); return *this; }

    const GrenadeParticleDesc& desc() const { return m_desc; }

    ParticleHandle upload() const;

private:
    GrenadeParticleDesc m_desc;
};

std::optional<GrenadeParticleDesc> getGrenadeParticles(ParticleHandle handle);

// ---------------------------------------------------------------- physics

enum class GrenadeColliderType { SPHERE, CAPSULE, BOX };

struct GrenadePhysicsBody {
    std::string name;
    float mass = 1.0f;
    bool hasCollider = false;
    GrenadeColliderType colliderType = GrenadeColliderType::SPHERE;
    float colliderSize = 0.0f;
    glm::vec3 initialVelocity{0.0f};
    float lifetime = 0.0f;       // 0 = lives until destroyed
    float bounciness = 0.0f;
    float friction = 0.5f;
    float airResistance = 0.0f;
    bool gravity = false;
};

struct GrenadeForceField {
    std::string name;
    float radius = 0.0f;
    float force = 0.0f;
    bool shockwave = false;      // expanding ring instead of an instantaneous radial impulse
};

struct GrenadePhysicsDesc {
    std::vector<GrenadePhysicsBody> bodies;
    std::vector<GrenadeForceField> forceFields;
};

/** Builder for grenade physics setups; upload() stores it and returns its handle. */
class GrenadePhysicsSystem {
public:
    GrenadePhysicsSystem& addRigidBody(const std::string& name, float mass);
    GrenadePhysicsSystem& addCollider(const std::string& name, GrenadeColliderType type, float size);
    GrenadePhysicsSystem& setInitialVelocity(const std::string& name, const glm::vec3& velocity);
    GrenadePhysicsSystem& setLifetime(const std::string& name, float lifetime);
    GrenadePhysicsSystem& setBounciness(const std::string& name, float bounciness);
    GrenadePhysicsSystem& setFriction(const std::string& name, float friction);
    GrenadePhysicsSystem& setAirResistance(const std::string& name, float airResistance);
    GrenadePhysicsSystem& enableGravity(const std::string& name);
    GrenadePhysicsSystem& addForceField(const std::string& name, float radius, float force);
    GrenadePhysicsSystem& addShockwave(const std::string& name, float radius, float force);

    const GrenadePhysicsDesc& desc() const { return m_desc; }

    PhysicsHandle upload() const;

private:
    GrenadePhysicsBody& body(const std::string& name);

    GrenadePhysicsDesc m_desc;
};

std::optional<GrenadePhysicsDesc> getGrenadePhysics(PhysicsHandle handle);

// ---------------------------------------------------------------- meshes / textures

struct GrenadeTextureData {
    int width = 0;
    int height = 0;
    std::vector<glm::u8vec4> pixels;
};

MeshHandle storeGrenadeMesh(const MagiTech::Mesh& mesh);
std::optional<MagiTech::Mesh> getGrenadeMesh(MeshHandle handle);

TextureHandle storeGrenadeTexture(int width, int height, std::vector<glm::u8vec4> pixels);
std::optional<GrenadeTextureData> getGrenadeTexture(TextureHandle handle);

/** Drops every stored grenade asset (handles stay unique). */
void clearGrenadeAssets();

} // namespace AlchemicalGrenades
} // namespace MagiTech
