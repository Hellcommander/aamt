#include "StatusEffectGenAssets.hpp"
#include "core/rendering/AssetHandle.hpp"
#include <mutex>
#include <unordered_map>

namespace MagiTech {
namespace StatusEffects {

namespace {

struct AssetStore {
    std::mutex mutex;
    std::unordered_map<ShaderHandle, StatusEffectShaderSource> shaders;
    std::unordered_map<TextureHandle, StatusEffectTextureData> textures;
    std::unordered_map<MeshHandle, MagiTech::Mesh> meshes;
    std::unordered_map<ParticleHandle, std::string> particles;
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

} // namespace

void storeStatusEffectShader(ShaderHandle handle, StatusEffectShaderSource source) {
    if (handle == 0) return;
    std::lock_guard<std::mutex> lock(store().mutex);
    store().shaders[handle] = std::move(source);
}

std::optional<StatusEffectShaderSource> getStatusEffectShader(ShaderHandle handle) {
    return lookup(store().shaders, handle);
}

TextureHandle storeStatusEffectTexture(int width, int height, std::vector<uint8_t> rgba) {
    const TextureHandle handle = nextAssetHandle();
    StatusEffectTextureData data{width, height, std::move(rgba)};
    std::lock_guard<std::mutex> lock(store().mutex);
    store().textures[handle] = std::move(data);
    return handle;
}

std::optional<StatusEffectTextureData> getStatusEffectTexture(TextureHandle handle) {
    return lookup(store().textures, handle);
}

MeshHandle storeStatusEffectMesh(const MagiTech::Mesh& mesh) {
    if (mesh.isEmpty()) return 0;
    const MeshHandle handle = nextAssetHandle();
    std::lock_guard<std::mutex> lock(store().mutex);
    store().meshes[handle] = mesh;
    return handle;
}

std::optional<MagiTech::Mesh> getStatusEffectMesh(MeshHandle handle) {
    return lookup(store().meshes, handle);
}

ParticleHandle storeStatusEffectParticles(std::string configJson) {
    const ParticleHandle handle = nextAssetHandle();
    std::lock_guard<std::mutex> lock(store().mutex);
    store().particles[handle] = std::move(configJson);
    return handle;
}

std::optional<std::string> getStatusEffectParticles(ParticleHandle handle) {
    return lookup(store().particles, handle);
}

void clearStatusEffectAssets() {
    std::lock_guard<std::mutex> lock(store().mutex);
    store().shaders.clear();
    store().textures.clear();
    store().meshes.clear();
    store().particles.clear();
}

} // namespace StatusEffects
} // namespace MagiTech
