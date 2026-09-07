#include "DriftingOrbitalsLuaBindings.hpp"
#include "DriftingOrbitalsFactory.hpp"
#include "core/plugins/MainPlugin.hpp"
#include <vector>

namespace MagiTech {
namespace DriftingOrbitals {

static std::vector<std::pair<std::future<DriftingOrbitalsAssetBundle>, std::string>> pendingAssets;

void DriftingOrbitalsLuaBindings::bind(sol::state& lua) {
    
    lua.new_usertype<DriftingOrbitalParams>("DriftingOrbitalParams",
        sol::constructors<DriftingOrbitalParams()>(),
        "id", &DriftingOrbitalParams::id,
        "orbCount", &DriftingOrbitalParams::orbCount,
        "orbitRadiusMin", &DriftingOrbitalParams::orbitRadiusMin,
        "orbitRadiusMax", &DriftingOrbitalParams::orbitRadiusMax,
        "orbitSpeedMin", &DriftingOrbitalParams::orbitSpeedMin,
        "orbitSpeedMax", &DriftingOrbitalParams::orbitSpeedMax,
        "radialOscillationAmp", &DriftingOrbitalParams::radialOscillationAmp,
        "radialOscillationFreq", &DriftingOrbitalParams::radialOscillationFreq,
        "orbScaleMin", &DriftingOrbitalParams::orbScaleMin,
        "orbScaleMax", &DriftingOrbitalParams::orbScaleMax,
        "orbMeshDetail", &DriftingOrbitalParams::orbMeshDetail,
        "enableTrails", &DriftingOrbitalParams::enableTrails,
        "trailLength", &DriftingOrbitalParams::trailLength,
        "trailWidth", &DriftingOrbitalParams::trailWidth,
        "trailColor", &DriftingOrbitalParams::trailColor,
        "pulseInterval", &DriftingOrbitalParams::pulseInterval,
        "pulseRadius", &DriftingOrbitalParams::pulseRadius,
        "pulseStrength", &DriftingOrbitalParams::pulseStrength,
        "pulseColor", &DriftingOrbitalParams::pulseColor
    );

    lua.new_usertype<DriftingOrbitalsAssetBundle>("DriftingOrbitalsAssetBundle",
        sol::no_constructor,
        "orbitalMeshes", &DriftingOrbitalsAssetBundle::orbitalMeshes,
        "trailMeshes", &DriftingOrbitalsAssetBundle::trailMeshes,
        "pulseParticleSystem", &DriftingOrbitalsAssetBundle::pulseParticleSystem,
        "orbitalShader", &DriftingOrbitalsAssetBundle::orbitalShader
    );

    lua.set_function("spawn_drifting_orbitals",
        [&](const DriftingOrbitalParams& p) {
            auto factory = MainPlugin::instance().getDriftingOrbitalsFactory();
            pendingAssets.emplace_back(factory->generateAsync(p), p.id);
        }
    );
}

void DriftingOrbitalsLuaBindings::poll_assets(sol::state& lua) {
    for (auto it = pendingAssets.begin(); it != pendingAssets.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            try {
                auto b = it->first.get();
                lua["print"]("Drifting orbital asset ready: " + it->second);
            } catch (const std::exception& e) { /* log error */ }
            it = pendingAssets.erase(it);
        } else { ++it; }
    }
}

} // namespace DriftingOrbitals
} // namespace MagiTech
