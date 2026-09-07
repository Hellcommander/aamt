#include "PlasmaDiscLuaBindings.hpp"
#include "PlasmaDiscFactory.hpp"
#include "core/plugins/MainPlugin.hpp"
#include <vector>

namespace MagiTech {
namespace PlasmaDiscs {

static std::vector<std::pair<std::future<PlasmaDiscAssetBundle>, std::string>> pendingDiscs;

void PlasmaDiscLuaBindings::bind(sol::state& lua) {
    lua.new_usertype<PlasmaDiscParams>("PlasmaDiscParams",
        sol::constructors<PlasmaDiscParams()>(),
        "id", &PlasmaDiscParams::id,
        "outerRadius", &PlasmaDiscParams::outerRadius,
        "innerRadius", &PlasmaDiscParams::innerRadius,
        "thickness", &PlasmaDiscParams::thickness,
        "radialSegments", &PlasmaDiscParams::radialSegments,
        "spinRateRPM", &PlasmaDiscParams::spinRateRPM,
        "motionBlurStrength", &PlasmaDiscParams::motionBlurStrength,
        "enableBlur", &PlasmaDiscParams::enableBlur,
        "rimColor", &PlasmaDiscParams::rimColor,
        "rimIntensity", &PlasmaDiscParams::rimIntensity,
        "rimFalloff", &PlasmaDiscParams::rimFalloff,
        "flickerFrequency", &PlasmaDiscParams::flickerFrequency,
        "enableTrail", &PlasmaDiscParams::enableTrail,
        "trailLength", &PlasmaDiscParams::trailLength,
        "trailWidth", &PlasmaDiscParams::trailWidth,
        "trailColor", &PlasmaDiscParams::trailColor,
        "sparkCount", &PlasmaDiscParams::sparkCount,
        "sparkColor", &PlasmaDiscParams::sparkColor,
        "sparkLifetime", &PlasmaDiscParams::sparkLifetime,
        "sparkSpeedMin", &PlasmaDiscParams::sparkSpeedMin,
        "sparkSpeedMax", &PlasmaDiscParams::sparkSpeedMax
    );

    lua.new_usertype<PlasmaDiscAssetBundle>("PlasmaDiscAssetBundle",
        sol::no_constructor,
        "discMesh", &PlasmaDiscAssetBundle::discMesh,
        "discShader", &PlasmaDiscAssetBundle::discShader,
        "trail", &PlasmaDiscAssetBundle::trail,
        "sparkParticles", &PlasmaDiscAssetBundle::sparkParticles
    );

    lua.set_function("spawn_plasma_disc",
        [&](const PlasmaDiscParams& p) {
            auto factory = MainPlugin::instance().getPlasmaDiscFactory();
            return factory->generateAsync(p).get();
        }
    );

    lua.set_function("spawn_plasma_disc_async",
        [&](const PlasmaDiscParams& p) {
            auto factory = MainPlugin::instance().getPlasmaDiscFactory();
            pendingDiscs.emplace_back(factory->generateAsync(p), p.id);
        }
    );
}

void PlasmaDiscLuaBindings::poll_assets(sol::state& lua) {
    for (auto it = pendingDiscs.begin(); it != pendingDiscs.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            try {
                auto b = it->first.get();
                lua["print"]("Plasma disc ready: " + it->second);
            } catch (const std::exception& e) {
                // log error
            }
            it = pendingDiscs.erase(it);
        } else {
            ++it;
        }
    }
}

} // namespace PlasmaDiscs
} // namespace MagiTech
