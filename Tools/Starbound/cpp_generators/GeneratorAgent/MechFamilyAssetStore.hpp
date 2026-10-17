#pragma once

// Storage for the assets produced by the Mechs generators (MechGenerators.hpp).
// Generators return small integer handles (MechTypes.hpp); the data behind each
// handle lives here so that factories, bindings and renderers can resolve it.

#include "MechTypes.hpp"
#include <memory>
#include <mutex>
#include <shared_mutex>
#include <string>
#include <unordered_map>
#include <variant>
#include <vector>

namespace mt {
class Mesh;
}

namespace MagiTech {
namespace Mechs {

struct MechTextureData {
    std::string name;
    int width = 0;
    int height = 0;
    std::vector<unsigned char> rgba;   // width * height * 4 bytes
};

struct MechBone {
    std::string name;
    int parent = -1;
    glm::mat4 localTransform{1.0f};
    float minAngleDeg = -180.0f;
    float maxAngleDeg = 180.0f;
    float stiffness = 0.0f;
    float damping = 0.0f;
};

struct MechSkeletonData {
    std::string name;
    std::vector<MechBone> bones;
    std::vector<std::vector<int>> ikChains;        // bone index chains, root to tip
    std::vector<std::string> morphTargets;         // one per mech form
};

struct MechAnimationKey {
    float time = 0.0f;
    std::vector<glm::quat> boneRotations;          // one per bone
    std::vector<glm::vec3> boneOffsets;            // one per bone
};

struct MechAnimationData {
    std::string name;
    float duration = 1.0f;
    bool looping = true;
    std::vector<MechAnimationKey> keys;
};

struct MechMaterialData {
    std::string name;
    glm::vec4 albedo{1.0f};
    float metallic = 0.0f;
    float roughness = 0.5f;
    glm::vec3 emissive{0.0f};
    float emissiveIntensity = 0.0f;
    float normalStrength = 1.0f;
    float opacity = 1.0f;
    TextureHandle albedoMap = 0;
    TextureHandle normalMap = 0;
    TextureHandle roughnessMap = 0;
    TextureHandle metallicMap = 0;
    TextureHandle emissiveMap = 0;
};

struct MechParticleData {
    std::string name;
    float spawnRate = 10.0f;      // particles per second
    float lifetime = 1.0f;        // seconds
    float speed = 1.0f;
    float size = 0.05f;
    glm::vec4 color{1.0f};
    std::vector<glm::vec3> emitterPositions;
};

struct MechColliderShape {
    enum class Type { Box, Capsule, Sphere };
    Type type = Type::Box;
    glm::vec3 size{1.0f};         // box: full extents; capsule: (radius, length, 0); sphere: (radius, 0, 0)
    glm::mat4 transform{1.0f};
    float mass = 1.0f;
};

struct MechPhysicsData {
    std::string name;
    std::vector<MechColliderShape> shapes;
    float totalMass = 0.0f;
    glm::vec3 centerOfMass{0.0f};
    float jointDamping = 0.0f;
    float jointStiffness = 0.0f;
};

struct MechAudioData {
    std::string name;
    std::string category;
    float frequency = 1.0f;       // repetitions per second for cyclic sounds
    float volume = 1.0f;
    float pitch = 1.0f;
    bool looping = false;
};

class MechFamilyAssetStore {
public:
    static MechFamilyAssetStore& instance() {
        static MechFamilyAssetStore store;
        return store;
    }

    template <typename T>
    uint32_t add(std::shared_ptr<T> asset) {
        if (!asset) return 0;
        std::unique_lock lock(mutex_);
        const uint32_t handle = nextHandle_++;
        assets_.emplace(handle, Entry(std::move(asset)));
        return handle;
    }

    template <typename T>
    std::shared_ptr<T> get(uint32_t handle) const {
        std::shared_lock lock(mutex_);
        auto it = assets_.find(handle);
        if (it == assets_.end()) return nullptr;
        if (auto ptr = std::get_if<std::shared_ptr<T>>(&it->second)) return *ptr;
        return nullptr;
    }

    bool release(uint32_t handle) {
        std::unique_lock lock(mutex_);
        return assets_.erase(handle) > 0;
    }

    size_t size() const {
        std::shared_lock lock(mutex_);
        return assets_.size();
    }

private:
    MechFamilyAssetStore() = default;

    using Entry = std::variant<std::shared_ptr<mt::Mesh>,
                               std::shared_ptr<MechTextureData>,
                               std::shared_ptr<MechSkeletonData>,
                               std::shared_ptr<MechAnimationData>,
                               std::shared_ptr<MechMaterialData>,
                               std::shared_ptr<MechParticleData>,
                               std::shared_ptr<MechPhysicsData>,
                               std::shared_ptr<MechAudioData>>;

    mutable std::shared_mutex mutex_;
    std::unordered_map<uint32_t, Entry> assets_;
    uint32_t nextHandle_ = 1;   // 0 is the invalid handle
};

} // namespace Mechs
} // namespace MagiTech
