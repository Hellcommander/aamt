#include "BeamNetLuaBindings.hpp"
#include "BeamNetFactory.hpp"
#include "core/plugins/MainPlugin.hpp"
#include <vector>

namespace MagiTech {
namespace BeamNets {

static std::vector<std::pair<std::future<BeamNetAssetBundle>, std::string>> pendingNets;

void BeamNetLuaBindings::bind(sol::state& lua) {
    lua.new_usertype<BeamNetParams>("BeamNetParams",
        sol::constructors<BeamNetParams()>(),
        "id", &BeamNetParams::id,
        "rows", &BeamNetParams::rows,
        "columns", &BeamNetParams::columns,
        "cellWidth", &BeamNetParams::cellWidth,
        "cellHeight", &BeamNetParams::cellHeight,
        "beamThickness", &BeamNetParams::beamThickness,
        "beamColor", &BeamNetParams::beamColor,
        "glowIntensity", &BeamNetParams::glowIntensity,
        "flickerFrequency", &BeamNetParams::flickerFrequency,
        "weaveAmplitude", &BeamNetParams::weaveAmplitude,
        "weaveSpeed", &BeamNetParams::weaveSpeed,
        "deploymentDelay", &BeamNetParams::deploymentDelay,
        "activeDuration", &BeamNetParams::activeDuration,
        "retractOnExpire", &BeamNetParams::retractOnExpire,
        "enableSparks", &BeamNetParams::enableSparks,
        "sparkRate", &BeamNetParams::sparkRate,
        "sparkLifetime", &BeamNetParams::sparkLifetime
    );

    lua.new_usertype<BeamNetAssetBundle>("BeamNetAssetBundle",
        sol::no_constructor,
        "netMesh", &BeamNetAssetBundle::netMesh,
        "beamShader", &BeamNetAssetBundle::beamShader,
        "sparkParticles", &BeamNetAssetBundle::sparkParticles,
        "scorchDecal", &BeamNetAssetBundle::scorchDecal
    );

    lua.set_function("spawn_beam_net",
        [&](const BeamNetParams& p) {
            auto factory = MainPlugin::instance().getBeamNetFactory();
            return factory->generateAsync(p).get();
        }
    );

    lua.set_function("spawn_beam_net_async",
        [&](const BeamNetParams& p) {
            auto factory = MainPlugin::instance().getBeamNetFactory();
            pendingNets.emplace_back(factory->generateAsync(p), p.id);
        }
    );
}

void BeamNetLuaBindings::poll_assets(sol::state& lua) {
    for (auto it = pendingNets.begin(); it != pendingNets.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            try {
                auto b = it->first.get();
                lua["print"]("Beam net ready: " + it->second);
            } catch (const std::exception& e) {
                // log error
            }
            it = pendingNets.erase(it);
        } else {
            ++it;
        }
    }
}

} // namespace BeamNets
} // namespace MagiTech
