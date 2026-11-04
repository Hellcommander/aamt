#include "AdvancedProjectileAssets.hpp"
#include "core/audio/AudioBuilder.hpp"
#include "core/physics/Simulation.hpp"
#include "core/rendering/AssetHandle.hpp"
#include <mutex>
#include <unordered_map>

namespace MagiTech {
namespace AdvancedProjectiles {
namespace Assets {

namespace {

struct AssetStore {
    std::mutex mutex;
    std::unordered_map<SimulationHandle, SimulationDesc> simulations;
    std::unordered_map<TetherHandle, TetherDesc> tethers;
    std::unordered_map<AudioHandle, ProjectileAudioDesc> audio;
    std::unordered_map<ShaderHandle, ShaderProgramDesc> shaders;
};

AssetStore& store() {
    // Intentionally never destroyed: generator worker threads owned by other
    // function-local statics (the Lua bindings' manager) may still register
    // assets while static destructors run at process exit.
    static AssetStore* s = new AssetStore();
    return *s;
}

SimulationHandle registerSimulation(SimulationHandle handle, SimulationDesc desc) {
    if (handle == 0) return 0;
    std::lock_guard<std::mutex> lock(store().mutex);
    store().simulations[handle] = std::move(desc);
    return handle;
}

} // namespace

SimulationHandle createGuidanceSim(const GuidanceSimDesc& desc) {
    return registerSimulation(nextAssetHandle(), desc);
}

SimulationHandle createPropulsionSim(const PropulsionSimDesc& desc) {
    return registerSimulation(nextAssetHandle(), desc);
}

SimulationHandle createTimerSim(const TimerSimDesc& desc) {
    return registerSimulation(nextAssetHandle(), desc);
}

SimulationHandle createArcSim(const ArcSimDesc& desc) {
    return registerSimulation(nextAssetHandle(), desc);
}

SimulationHandle createBoomerangSim(const BoomerangSimDesc& desc) {
    return registerSimulation(nextAssetHandle(), desc);
}

SimulationHandle createLinearProjectileSim(const ProjectileSimDesc& desc) {
    MagiTech::SimulationParams params;
    params.dragCoefficient = desc.dragCoefficient;
    params.gravityInfluence = desc.gravityInfluence;
    params.maxDistance = desc.maxRange;
    return registerSimulation(MagiTech::Simulation::createLinearProjectile(params), desc);
}

SimulationHandle createReelSim(const ReelSimDesc& desc) {
    return registerSimulation(nextAssetHandle(), desc);
}

std::optional<SimulationDesc> getSimulationDesc(SimulationHandle handle) {
    std::lock_guard<std::mutex> lock(store().mutex);
    auto it = store().simulations.find(handle);
    if (it == store().simulations.end()) return std::nullopt;
    return it->second;
}

TetherHandle createTether(const TetherDesc& desc) {
    const TetherHandle handle = nextAssetHandle();
    std::lock_guard<std::mutex> lock(store().mutex);
    store().tethers[handle] = desc;
    return handle;
}

std::optional<TetherDesc> getTetherDesc(TetherHandle handle) {
    std::lock_guard<std::mutex> lock(store().mutex);
    auto it = store().tethers.find(handle);
    if (it == store().tethers.end()) return std::nullopt;
    return it->second;
}

AudioHandle loadAudio(const ProjectileAudioDesc& desc) {
    MagiTech::AudioDesc coreDesc;
    coreDesc.filename = desc.filename;
    coreDesc.volume = desc.volume;
    coreDesc.looping = desc.looping;
    const AudioHandle handle = MagiTech::AudioSystem::load(coreDesc);
    if (handle == 0) return 0;

    std::lock_guard<std::mutex> lock(store().mutex);
    store().audio[handle] = desc;
    return handle;
}

std::optional<ProjectileAudioDesc> getAudioDesc(AudioHandle handle) {
    std::lock_guard<std::mutex> lock(store().mutex);
    auto it = store().audio.find(handle);
    if (it == store().audio.end()) return std::nullopt;
    return it->second;
}

ShaderHandle compileShaderProgram(const ShaderProgramDesc& desc) {
    MagiTech::ShaderDesc coreDesc;
    coreDesc.vertexSource = desc.vertexSource;
    coreDesc.fragmentSource = desc.fragmentSource;
    coreDesc.stage = ShaderStage::Fragment;
    coreDesc.language = ShaderLanguage::GLSL;
    coreDesc.target = ShaderTarget::SPIRV;
    coreDesc.uniforms = desc.uniforms;
    const ShaderHandle handle = MagiTech::Shaders::compile(coreDesc);
    if (handle == 0) return 0;

    std::lock_guard<std::mutex> lock(store().mutex);
    store().shaders[handle] = desc;
    return handle;
}

std::optional<ShaderProgramDesc> getShaderProgramDesc(ShaderHandle handle) {
    std::lock_guard<std::mutex> lock(store().mutex);
    auto it = store().shaders.find(handle);
    if (it == store().shaders.end()) return std::nullopt;
    return it->second;
}

void clearAll() {
    std::lock_guard<std::mutex> lock(store().mutex);
    store().simulations.clear();
    store().tethers.clear();
    store().audio.clear();
    store().shaders.clear();
}

} // namespace Assets
} // namespace AdvancedProjectiles
} // namespace MagiTech
