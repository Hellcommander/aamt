#include "CockpitLuaBindings.hpp"
#include "CockpitFactory.hpp"
#include "core/plugins/MainPlugin.hpp"
#include <vector>

namespace MagiTech {
namespace Cockpits {

static std::vector<std::pair<std::future<CockpitAssetBundle>, std::string>> pendingCockpits;

void CockpitLuaBindings::bind(sol::state& lua) {
    lua.new_usertype<CockpitParams>("CockpitParams",
        sol::constructors<CockpitParams()>(),
        "id", &CockpitParams::id,
        // Seat & Interior
        "seatWidth", &CockpitParams::seatWidth,
        "seatDepth", &CockpitParams::seatDepth,
        "seatHeight", &CockpitParams::seatHeight,
        "seatFabricColor", &CockpitParams::seatFabricColor,
        "headrestEnabled", &CockpitParams::headrestEnabled,
        // Canopy & Glass
        "canopyRadius", &CockpitParams::canopyRadius,
        "canopyHeight", &CockpitParams::canopyHeight,
        "glassThickness", &CockpitParams::glassThickness,
        "glassTint", &CockpitParams::glassTint,
        "reflectivity", &CockpitParams::reflectivity,
        // Console & Controls
        "displayCount", &CockpitParams::displayCount,
        "displayResolution", &CockpitParams::displayResolution,
        "stickOffsetX", &CockpitParams::stickOffsetX,
        "stickOffsetY", &CockpitParams::stickOffsetY,
        "throttleLever", &CockpitParams::throttleLever,
        "pedalControls", &CockpitParams::pedalControls,
        // Instrumentation
        "gaugeCount", &CockpitParams::gaugeCount,
        "gaugeRadius", &CockpitParams::gaugeRadius,
        "gaugeNeedleColor", &CockpitParams::gaugeNeedleColor,
        "holographicHUD", &CockpitParams::holographicHUD,
        // Ambient FX
        "cockpitLight", &CockpitParams::cockpitLight,
        "lightColor", &CockpitParams::lightColor,
        "lightIntensity", &CockpitParams::lightIntensity,
        // Interaction
        "canopyAnimEnabled", &CockpitParams::canopyAnimEnabled,
        "canopyOpenAngleDeg", &CockpitParams::canopyOpenAngleDeg,
        "canopyOpenDuration", &CockpitParams::canopyOpenDuration,
        // Integration
        "mountOffset", &CockpitParams::mountOffset,
        "mountRotation", &CockpitParams::mountRotation
    );

    lua.new_usertype<CockpitAssetBundle>("CockpitAssetBundle",
        sol::no_constructor,
        "seatMesh", &CockpitAssetBundle::seatMesh,
        "canopyMesh", &CockpitAssetBundle::canopyMesh,
        "consoleMesh", &CockpitAssetBundle::consoleMesh,
        "gaugeMesh", &CockpitAssetBundle::gaugeMesh,
        "hudMesh", &CockpitAssetBundle::hudMesh,
        "glassShader", &CockpitAssetBundle::glassShader,
        "screenShader", &CockpitAssetBundle::screenShader,
        "canopyAnimation", &CockpitAssetBundle::canopyAnimation,
        "collisionVolume", &CockpitAssetBundle::collisionVolume,
        "uiDecals", &CockpitAssetBundle::uiDecals
    );

    lua.set_function("attach_cockpit",
        [&](const CockpitParams& p) {
            auto factory = MainPlugin::instance().getCockpitFactory();
            return factory->generateAsync(p).get();
        }
    );

    lua.set_function("attach_cockpit_async",
        [&](const CockpitParams& p) {
            auto factory = MainPlugin::instance().getCockpitFactory();
            pendingCockpits.emplace_back(factory->generateAsync(p), p.id);
        }
    );
}

void CockpitLuaBindings::poll_assets(sol::state& lua) {
    for (auto it = pendingCockpits.begin(); it != pendingCockpits.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            try {
                auto b = it->first.get();
                lua["print"]("Cockpit module ready: " + it->second);
            } catch (const std::exception& e) {
                // log error
            }
            it = pendingCockpits.erase(it);
        } else {
            ++it;
        }
    }
}

} // namespace Cockpits
} // namespace MagiTech
