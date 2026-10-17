#include "CosmicAssets.hpp"
#include "core/rendering/AssetHandle.hpp"
#include <mutex>
#include <unordered_map>

namespace MagiTech {
namespace Cosmic {

namespace {

struct AssetStore {
    std::mutex mutex;
    std::unordered_map<MeshHandle, MagiTech::Mesh> meshes;
    std::unordered_map<TextureHandle, CosmicTextureData> textures;
    std::unordered_map<ShaderHandle, CosmicShaderSource> shaders;
    std::unordered_map<EffectHandle, std::vector<std::string>> effects;
};

AssetStore& store() {
    static AssetStore s;
    return s;
}

} // namespace

MeshHandle storeCosmicMesh(const MagiTech::Mesh& mesh) {
    if (mesh.isEmpty()) {
        return 0;
    }
    const MeshHandle handle = nextAssetHandle();
    std::lock_guard<std::mutex> lock(store().mutex);
    store().meshes[handle] = mesh;
    return handle;
}

std::optional<MagiTech::Mesh> getCosmicMesh(MeshHandle handle) {
    std::lock_guard<std::mutex> lock(store().mutex);
    auto it = store().meshes.find(handle);
    if (it == store().meshes.end()) return std::nullopt;
    return it->second;
}

TextureHandle storeCosmicTexture(int width, int height, std::vector<uint8_t> rgba) {
    const TextureHandle handle = nextAssetHandle();
    CosmicTextureData data{width, height, std::move(rgba)};
    std::lock_guard<std::mutex> lock(store().mutex);
    store().textures[handle] = std::move(data);
    return handle;
}

std::optional<CosmicTextureData> getCosmicTexture(TextureHandle handle) {
    std::lock_guard<std::mutex> lock(store().mutex);
    auto it = store().textures.find(handle);
    if (it == store().textures.end()) return std::nullopt;
    return it->second;
}

void storeCosmicShaderSource(ShaderHandle handle, CosmicShaderSource source) {
    if (handle == 0) return;
    std::lock_guard<std::mutex> lock(store().mutex);
    store().shaders[handle] = std::move(source);
}

std::optional<CosmicShaderSource> getCosmicShaderSource(ShaderHandle handle) {
    std::lock_guard<std::mutex> lock(store().mutex);
    auto it = store().shaders.find(handle);
    if (it == store().shaders.end()) return std::nullopt;
    return it->second;
}

EffectHandle storeCosmicEffect(std::vector<std::string> particleConfigs) {
    if (particleConfigs.empty()) {
        return 0;
    }
    const EffectHandle handle = nextAssetHandle();
    std::lock_guard<std::mutex> lock(store().mutex);
    store().effects[handle] = std::move(particleConfigs);
    return handle;
}

std::optional<std::vector<std::string>> getCosmicEffect(EffectHandle handle) {
    std::lock_guard<std::mutex> lock(store().mutex);
    auto it = store().effects.find(handle);
    if (it == store().effects.end()) return std::nullopt;
    return it->second;
}

void clearCosmicAssets() {
    std::lock_guard<std::mutex> lock(store().mutex);
    store().meshes.clear();
    store().textures.clear();
    store().shaders.clear();
    store().effects.clear();
}

} // namespace Cosmic
} // namespace MagiTech
