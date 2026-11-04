#include "LightningProjectileAssets.hpp"
#include "core/audio/AudioBuilder.hpp"
#include "core/rendering/AssetHandle.hpp"
#include <mutex>
#include <unordered_map>

namespace MagiTech {
namespace LightningProjectiles {

namespace {

struct StoredParticle {
    ParticleEmitterDesc desc;
    std::string configJson;
};

struct StoredAudio {
    ProceduralAudioDesc desc;
    std::string path;
};

struct AssetStore {
    std::mutex mutex;
    std::unordered_map<MeshHandle, LightningMeshData> meshes;
    std::unordered_map<TextureHandle, LightningTextureData> textures;
    std::unordered_map<ParticleHandle, StoredParticle> particles;
    std::unordered_map<AudioHandle, StoredAudio> audio;
};

AssetStore& store() {
    static AssetStore s;
    return s;
}

MagiTech::AudioType toBuilderAudioType(ProceduralAudioType type) {
    switch (type) {
        case ProceduralAudioType::ELECTRIC: return MagiTech::AudioType::HUM;
        case ProceduralAudioType::THUNDER: return MagiTech::AudioType::IMPACT;
        case ProceduralAudioType::ZAP:
        case ProceduralAudioType::CRACKLE: return MagiTech::AudioType::IMPACT;
    }
    return MagiTech::AudioType::CUSTOM;
}

} // namespace

MeshHandle createMeshHandle() {
    return nextAssetHandle();
}

void uploadMeshData(MeshHandle handle,
                    const std::vector<glm::vec3>& vertices,
                    const std::vector<glm::vec3>& normals,
                    const std::vector<glm::vec2>& uvs,
                    const std::vector<uint32_t>& indices) {
    LightningMeshData data{vertices, normals, uvs, indices};
    std::lock_guard<std::mutex> lock(store().mutex);
    store().meshes[handle] = std::move(data);
}

std::optional<LightningMeshData> getMeshData(MeshHandle handle) {
    std::lock_guard<std::mutex> lock(store().mutex);
    auto it = store().meshes.find(handle);
    if (it == store().meshes.end()) return std::nullopt;
    return it->second;
}

TextureHandle createTextureHandle() {
    return nextAssetHandle();
}

void uploadTextureData(TextureHandle handle, int width, int height, const uint8_t* rgba, bool generateMipmaps) {
    LightningTextureData data;
    data.width = width;
    data.height = height;
    data.generateMipmaps = generateMipmaps;
    if (rgba && width > 0 && height > 0) {
        data.rgba.assign(rgba, rgba + static_cast<size_t>(width) * static_cast<size_t>(height) * 4);
    }
    std::lock_guard<std::mutex> lock(store().mutex);
    store().textures[handle] = std::move(data);
}

std::optional<LightningTextureData> getTextureData(TextureHandle handle) {
    std::lock_guard<std::mutex> lock(store().mutex);
    auto it = store().textures.find(handle);
    if (it == store().textures.end()) return std::nullopt;
    return it->second;
}

ParticleHandle createParticleEmitter(const ParticleEmitterDesc& desc) {
    MagiTech::ParticleEmitter emitter = MagiTech::ParticleBuilder::createEmitter(desc.type);
    const float endAlpha = desc.enableFade ? desc.endColor.a : desc.startColor.a;
    emitter.setRate(desc.rate)
        .setCount(static_cast<int>(desc.rate))
        .setLifetime(desc.lifetime)
        .setStartSize(desc.startSize)
        .setEndSize(desc.endSize)
        .setColor(desc.startColor)
        .setAlpha(desc.startColor.a, endAlpha)
        .setSpeed(desc.velocityVariation)
        .setGravity(desc.enablePhysics ? desc.gravity : glm::vec3(0.0f));
    if (glm::length(desc.velocity) > 0.0f) {
        emitter.setDirection(glm::normalize(desc.velocity));
    }

    const ParticleHandle handle = emitter.getHandle();
    StoredParticle stored{desc, emitter.toOpenStarboundParticleJson()};
    std::lock_guard<std::mutex> lock(store().mutex);
    store().particles[handle] = std::move(stored);
    return handle;
}

std::optional<ParticleEmitterDesc> getParticleEmitterDesc(ParticleHandle handle) {
    std::lock_guard<std::mutex> lock(store().mutex);
    auto it = store().particles.find(handle);
    if (it == store().particles.end()) return std::nullopt;
    return it->second.desc;
}

std::optional<std::string> getParticleConfigJson(ParticleHandle handle) {
    std::lock_guard<std::mutex> lock(store().mutex);
    auto it = store().particles.find(handle);
    if (it == store().particles.end()) return std::nullopt;
    return it->second.configJson;
}

AudioHandle createProceduralAudio(const ProceduralAudioDesc& desc) {
    MagiTech::AudioBuilder builder = MagiTech::AudioBuilder::createProcedural();
    builder.setType(toBuilderAudioType(desc.type))
        .setVolume(desc.volume)
        .setPitch(desc.pitch)
        .setDuration(desc.duration)
        .modulateByParameter("intensity", desc.intensity);
    if (desc.enableSpatialAudio) {
        builder.enableSpatial(desc.distance);
    }

    const AudioHandle handle = builder.getHandle();
    StoredAudio stored{desc, builder.toOpenStarboundPath()};
    std::lock_guard<std::mutex> lock(store().mutex);
    store().audio[handle] = std::move(stored);
    return handle;
}

std::optional<ProceduralAudioDesc> getProceduralAudioDesc(AudioHandle handle) {
    std::lock_guard<std::mutex> lock(store().mutex);
    auto it = store().audio.find(handle);
    if (it == store().audio.end()) return std::nullopt;
    return it->second.desc;
}

std::optional<std::string> getAudioPath(AudioHandle handle) {
    std::lock_guard<std::mutex> lock(store().mutex);
    auto it = store().audio.find(handle);
    if (it == store().audio.end()) return std::nullopt;
    return it->second.path;
}

void clearLightningAssets() {
    std::lock_guard<std::mutex> lock(store().mutex);
    store().meshes.clear();
    store().textures.clear();
    store().particles.clear();
    store().audio.clear();
}

} // namespace LightningProjectiles
} // namespace MagiTech
