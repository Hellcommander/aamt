#include "SpellProjectileAssets.hpp"
#include "core/rendering/AssetHandle.hpp"
#include <mutex>
#include <unordered_map>

namespace MagiTech {
namespace SpellProjectiles {

namespace {

struct AssetStore {
    std::mutex mutex;
    std::unordered_map<MeshHandle, MagiTech::Mesh> meshes;
    std::unordered_map<ShaderHandle, std::string> shaders;
    std::unordered_map<ParticleHandle, std::string> particles;
    std::unordered_map<LightHandle, SpellLightDesc> lights;
    std::unordered_map<AudioHandle, SpellAudioDesc> audio;
    std::unordered_map<ColliderHandle, SpellColliderDesc> colliders;
};

AssetStore& store() {
    static AssetStore s;
    return s;
}

template <typename Map, typename Value>
uint32_t insertNew(Map& map, Value value) {
    const uint32_t handle = nextAssetHandle();
    std::lock_guard<std::mutex> lock(store().mutex);
    map[handle] = std::move(value);
    return handle;
}

template <typename Map>
auto lookup(Map& map, uint32_t handle) -> std::optional<typename Map::mapped_type> {
    std::lock_guard<std::mutex> lock(store().mutex);
    auto it = map.find(handle);
    if (it == map.end()) return std::nullopt;
    return it->second;
}

} // namespace

MeshHandle storeSpellMesh(const MagiTech::Mesh& mesh) {
    if (mesh.isEmpty()) return 0;
    return insertNew(store().meshes, mesh);
}

std::optional<MagiTech::Mesh> getSpellMesh(MeshHandle handle) {
    return lookup(store().meshes, handle);
}

void storeSpellShaderSource(ShaderHandle handle, std::string source) {
    if (handle == 0) return;
    std::lock_guard<std::mutex> lock(store().mutex);
    store().shaders[handle] = std::move(source);
}

std::optional<std::string> getSpellShaderSource(ShaderHandle handle) {
    return lookup(store().shaders, handle);
}

ParticleHandle storeSpellParticleConfig(std::string configJson) {
    return insertNew(store().particles, std::move(configJson));
}

std::optional<std::string> getSpellParticleConfig(ParticleHandle handle) {
    return lookup(store().particles, handle);
}

LightHandle storeSpellLight(const SpellLightDesc& light) {
    return insertNew(store().lights, light);
}

std::optional<SpellLightDesc> getSpellLight(LightHandle handle) {
    return lookup(store().lights, handle);
}

AudioHandle storeSpellAudio(const SpellAudioDesc& audio) {
    return insertNew(store().audio, audio);
}

std::optional<SpellAudioDesc> getSpellAudio(AudioHandle handle) {
    return lookup(store().audio, handle);
}

ColliderHandle storeSpellCollider(const SpellColliderDesc& collider) {
    return insertNew(store().colliders, collider);
}

std::optional<SpellColliderDesc> getSpellCollider(ColliderHandle handle) {
    return lookup(store().colliders, handle);
}

void clearSpellAssets() {
    std::lock_guard<std::mutex> lock(store().mutex);
    store().meshes.clear();
    store().shaders.clear();
    store().particles.clear();
    store().lights.clear();
    store().audio.clear();
    store().colliders.clear();
}

} // namespace SpellProjectiles
} // namespace MagiTech
