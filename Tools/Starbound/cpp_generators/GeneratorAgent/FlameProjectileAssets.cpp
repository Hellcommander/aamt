#include "FlameProjectileAssets.hpp"
#include "core/rendering/AssetHandle.hpp"
#include <mutex>
#include <unordered_map>

namespace MagiTech {
namespace FlameProjectiles {

namespace {

struct AssetStore {
    std::mutex mutex;
    std::unordered_map<MeshHandle, MagiTech::Mesh> meshes;
    std::unordered_map<TextureHandle, FlameTextureData> textures;
    std::unordered_map<ShaderHandle, FlameShaderSource> shaders;
    std::unordered_map<ParticleHandle, std::string> particles;
};

AssetStore& store() {
    static AssetStore s;
    return s;
}

} // namespace

MeshHandle storeMesh(const MagiTech::Mesh& mesh) {
    if (mesh.isEmpty()) {
        return 0;
    }
    const MeshHandle handle = nextAssetHandle();
    std::lock_guard<std::mutex> lock(store().mutex);
    store().meshes[handle] = mesh;
    return handle;
}

std::optional<MagiTech::Mesh> getMesh(MeshHandle handle) {
    std::lock_guard<std::mutex> lock(store().mutex);
    auto it = store().meshes.find(handle);
    if (it == store().meshes.end()) return std::nullopt;
    return it->second;
}

TextureHandle storeTexture(int width, int height, std::vector<uint8_t> rgba) {
    const TextureHandle handle = nextAssetHandle();
    FlameTextureData data{width, height, std::move(rgba)};
    std::lock_guard<std::mutex> lock(store().mutex);
    store().textures[handle] = std::move(data);
    return handle;
}

std::optional<FlameTextureData> getTexture(TextureHandle handle) {
    std::lock_guard<std::mutex> lock(store().mutex);
    auto it = store().textures.find(handle);
    if (it == store().textures.end()) return std::nullopt;
    return it->second;
}

void storeShaderSource(ShaderHandle handle, FlameShaderSource source) {
    if (handle == 0) return;
    std::lock_guard<std::mutex> lock(store().mutex);
    store().shaders[handle] = std::move(source);
}

std::optional<FlameShaderSource> getShaderSource(ShaderHandle handle) {
    std::lock_guard<std::mutex> lock(store().mutex);
    auto it = store().shaders.find(handle);
    if (it == store().shaders.end()) return std::nullopt;
    return it->second;
}

void storeParticleConfig(ParticleHandle handle, std::string configJson) {
    if (handle == 0) return;
    std::lock_guard<std::mutex> lock(store().mutex);
    store().particles[handle] = std::move(configJson);
}

std::optional<std::string> getParticleConfig(ParticleHandle handle) {
    std::lock_guard<std::mutex> lock(store().mutex);
    auto it = store().particles.find(handle);
    if (it == store().particles.end()) return std::nullopt;
    return it->second;
}

void clearFlameAssets() {
    std::lock_guard<std::mutex> lock(store().mutex);
    store().meshes.clear();
    store().textures.clear();
    store().shaders.clear();
    store().particles.clear();
}

} // namespace FlameProjectiles
} // namespace MagiTech
