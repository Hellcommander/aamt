#include "AlchemicalGrenadeAssets.hpp"
#include "core/rendering/AssetHandle.hpp"
#include <glm/gtc/constants.hpp>
#include <algorithm>
#include <cmath>
#include <mutex>
#include <unordered_map>

namespace MagiTech {
namespace AlchemicalGrenades {

namespace {

struct AssetStore {
    std::mutex mutex;
    std::unordered_map<MeshHandle, MagiTech::Mesh> meshes;
    std::unordered_map<TextureHandle, GrenadeTextureData> textures;
    std::unordered_map<ParticleHandle, GrenadeParticleDesc> particles;
    std::unordered_map<PhysicsHandle, GrenadePhysicsDesc> physics;
};

AssetStore& store() {
    static AssetStore s;
    return s;
}

template <typename Map>
auto lookup(Map& map, uint32_t handle) -> std::optional<typename Map::mapped_type> {
    std::lock_guard<std::mutex> lock(store().mutex);
    auto it = map.find(handle);
    if (it == map.end()) return std::nullopt;
    return it->second;
}

constexpr float kStandardGravity = 9.81f;

} // namespace

// ---------------------------------------------------------------- particles

ParticleHandle GrenadeParticleSystem::upload() const {
    GrenadeParticleDesc desc = m_desc;

    MagiTech::ParticleEmitter emitter = MagiTech::ParticleBuilder::createEmitter(desc.type);
    emitter.setCount(std::max(desc.count, 0))
        .setRate(static_cast<float>(std::max(desc.count, 0)) / std::max(desc.lifetime, 0.01f))
        .setLifetime(desc.lifetime)
        .setSpeed(desc.speed)
        .setStartSize(desc.size)
        .setEndSize(desc.size * 0.25f)
        .setColor(desc.color)
        .setAlpha(desc.color.a, 0.0f)
        .setShape(MagiTech::ParticleShape::CONE)
        .setConeAngle(glm::degrees(std::clamp(desc.spread, 0.0f, glm::pi<float>())))
        .setGravity(glm::vec3(0.0f, -kStandardGravity * desc.gravity, 0.0f));
    desc.configJson = emitter.toOpenStarboundParticleJson();

    const ParticleHandle handle = emitter.getHandle();
    std::lock_guard<std::mutex> lock(store().mutex);
    store().particles[handle] = std::move(desc);
    return handle;
}

std::optional<GrenadeParticleDesc> getGrenadeParticles(ParticleHandle handle) {
    return lookup(store().particles, handle);
}

// ---------------------------------------------------------------- physics

GrenadePhysicsBody& GrenadePhysicsSystem::body(const std::string& name) {
    for (auto& b : m_desc.bodies) {
        if (b.name == name) return b;
    }
    GrenadePhysicsBody b;
    b.name = name;
    m_desc.bodies.push_back(b);
    return m_desc.bodies.back();
}

GrenadePhysicsSystem& GrenadePhysicsSystem::addRigidBody(const std::string& name, float mass) {
    body(name).mass = mass;
    return *this;
}

GrenadePhysicsSystem& GrenadePhysicsSystem::addCollider(const std::string& name, GrenadeColliderType type, float size) {
    auto& b = body(name);
    b.hasCollider = true;
    b.colliderType = type;
    b.colliderSize = size;
    return *this;
}

GrenadePhysicsSystem& GrenadePhysicsSystem::setInitialVelocity(const std::string& name, const glm::vec3& velocity) {
    body(name).initialVelocity = velocity;
    return *this;
}

GrenadePhysicsSystem& GrenadePhysicsSystem::setLifetime(const std::string& name, float lifetime) {
    body(name).lifetime = lifetime;
    return *this;
}

GrenadePhysicsSystem& GrenadePhysicsSystem::setBounciness(const std::string& name, float bounciness) {
    body(name).bounciness = bounciness;
    return *this;
}

GrenadePhysicsSystem& GrenadePhysicsSystem::setFriction(const std::string& name, float friction) {
    body(name).friction = friction;
    return *this;
}

GrenadePhysicsSystem& GrenadePhysicsSystem::setAirResistance(const std::string& name, float airResistance) {
    body(name).airResistance = airResistance;
    return *this;
}

GrenadePhysicsSystem& GrenadePhysicsSystem::enableGravity(const std::string& name) {
    body(name).gravity = true;
    return *this;
}

GrenadePhysicsSystem& GrenadePhysicsSystem::addForceField(const std::string& name, float radius, float force) {
    m_desc.forceFields.push_back({name, radius, force, false});
    return *this;
}

GrenadePhysicsSystem& GrenadePhysicsSystem::addShockwave(const std::string& name, float radius, float force) {
    m_desc.forceFields.push_back({name, radius, force, true});
    return *this;
}

PhysicsHandle GrenadePhysicsSystem::upload() const {
    if (m_desc.bodies.empty() && m_desc.forceFields.empty()) {
        return 0;
    }
    const PhysicsHandle handle = nextAssetHandle();
    std::lock_guard<std::mutex> lock(store().mutex);
    store().physics[handle] = m_desc;
    return handle;
}

std::optional<GrenadePhysicsDesc> getGrenadePhysics(PhysicsHandle handle) {
    return lookup(store().physics, handle);
}

// ---------------------------------------------------------------- meshes / textures

MeshHandle storeGrenadeMesh(const MagiTech::Mesh& mesh) {
    if (mesh.isEmpty()) return 0;
    const MeshHandle handle = nextAssetHandle();
    std::lock_guard<std::mutex> lock(store().mutex);
    store().meshes[handle] = mesh;
    return handle;
}

std::optional<MagiTech::Mesh> getGrenadeMesh(MeshHandle handle) {
    return lookup(store().meshes, handle);
}

TextureHandle storeGrenadeTexture(int width, int height, std::vector<glm::u8vec4> pixels) {
    const TextureHandle handle = nextAssetHandle();
    GrenadeTextureData data{width, height, std::move(pixels)};
    std::lock_guard<std::mutex> lock(store().mutex);
    store().textures[handle] = std::move(data);
    return handle;
}

std::optional<GrenadeTextureData> getGrenadeTexture(TextureHandle handle) {
    return lookup(store().textures, handle);
}

void clearGrenadeAssets() {
    std::lock_guard<std::mutex> lock(store().mutex);
    store().meshes.clear();
    store().textures.clear();
    store().particles.clear();
    store().physics.clear();
}

} // namespace AlchemicalGrenades
} // namespace MagiTech
