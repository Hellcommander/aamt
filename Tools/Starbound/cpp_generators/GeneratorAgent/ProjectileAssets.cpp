#include "ProjectileAssets.hpp"
#include "core/rendering/AssetHandle.hpp"
#include <mutex>
#include <sstream>
#include <unordered_map>
#include <nlohmann/json.hpp>

namespace MagiTech {
namespace Projectiles {

namespace {

struct AssetStore {
    std::mutex mutex;
    std::unordered_map<MeshHandle, MagiTech::Mesh> meshes;
    std::unordered_map<TextureHandle, ProjectileTextureData> textures;
    std::unordered_map<EffectHandle, ProjectileEffect> effects;
};

AssetStore& store() {
    static AssetStore s;
    return s;
}

nlohmann::json toJsonValue(const EffectParamValue& value) {
    return std::visit([](const auto& v) -> nlohmann::json {
        using T = std::decay_t<decltype(v)>;
        if constexpr (std::is_same_v<T, glm::vec3>) {
            return nlohmann::json::array({v.x, v.y, v.z});
        } else {
            return nlohmann::json(v);
        }
    }, value);
}

} // namespace

std::string ProjectileEffect::toJson() const {
    nlohmann::json out = nlohmann::json::array();
    for (const auto& system : m_systems) {
        nlohmann::json params = nlohmann::json::object();
        for (const auto& [key, value] : system.params) {
            params[key] = toJsonValue(value);
        }
        out.push_back({{"name", system.name}, {"parameters", params}});
    }
    return out.dump();
}

EffectHandle ProjectileEffect::upload() const {
    if (m_systems.empty()) {
        return 0;
    }
    const EffectHandle handle = nextAssetHandle();
    std::lock_guard<std::mutex> lock(store().mutex);
    store().effects[handle] = *this;
    return handle;
}

MeshHandle storeProjectileMesh(const MagiTech::Mesh& mesh) {
    if (mesh.isEmpty()) {
        return 0;
    }
    const MeshHandle handle = nextAssetHandle();
    std::lock_guard<std::mutex> lock(store().mutex);
    store().meshes[handle] = mesh;
    return handle;
}

std::optional<MagiTech::Mesh> getProjectileMesh(MeshHandle handle) {
    std::lock_guard<std::mutex> lock(store().mutex);
    auto it = store().meshes.find(handle);
    if (it == store().meshes.end()) return std::nullopt;
    return it->second;
}

TextureHandle storeProjectileTexture(int width, int height, std::vector<glm::u8vec4> pixels) {
    const TextureHandle handle = nextAssetHandle();
    ProjectileTextureData data{width, height, std::move(pixels)};
    std::lock_guard<std::mutex> lock(store().mutex);
    store().textures[handle] = std::move(data);
    return handle;
}

std::optional<ProjectileTextureData> getProjectileTexture(TextureHandle handle) {
    std::lock_guard<std::mutex> lock(store().mutex);
    auto it = store().textures.find(handle);
    if (it == store().textures.end()) return std::nullopt;
    return it->second;
}

std::optional<ProjectileEffect> getProjectileEffect(EffectHandle handle) {
    std::lock_guard<std::mutex> lock(store().mutex);
    auto it = store().effects.find(handle);
    if (it == store().effects.end()) return std::nullopt;
    return it->second;
}

void clearProjectileAssets() {
    std::lock_guard<std::mutex> lock(store().mutex);
    store().meshes.clear();
    store().textures.clear();
    store().effects.clear();
}

} // namespace Projectiles
} // namespace MagiTech
