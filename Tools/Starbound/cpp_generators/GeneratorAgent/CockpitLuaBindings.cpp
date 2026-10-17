#include "CockpitLuaBindings.hpp"
#include "CockpitFactory.hpp"
#include <memory>
#include <mutex>
#include "core/Log.hpp"
#include <vector>

namespace MagiTech {
namespace Cockpits {

static std::vector<std::pair<std::future<CockpitAssetBundle>, std::string>> pendingCockpits;

namespace {
std::mutex& factoryMutex() {
    static std::mutex m;
    return m;
}
std::shared_ptr<CockpitFactory>& factorySlot() {
    static std::shared_ptr<CockpitFactory> f;
    return f;
}
} // namespace

void CockpitLuaBindings::setFactory(std::shared_ptr<CockpitFactory> factory) {
    std::lock_guard<std::mutex> lock(factoryMutex());
    factorySlot() = std::move(factory);
}

std::shared_ptr<CockpitFactory> CockpitLuaBindings::factory() {
    std::lock_guard<std::mutex> lock(factoryMutex());
    auto& slot = factorySlot();
    if (!slot) {
        // No factory injected (e.g. by MainPlugin): create a default one.
        slot = std::make_shared<CockpitFactory>();
        slot->initialize(64, 4);
    }
    return slot;
}

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
            auto factory = CockpitLuaBindings::factory();
            return factory->generateAsync(p).get();
        }
    );

    lua.set_function("attach_cockpit_async",
        [&](const CockpitParams& p) {
            auto factory = CockpitLuaBindings::factory();
            pendingCockpits.emplace_back(factory->generateAsync(p), p.id);
        }
    );
}

void CockpitLuaBindings::poll_assets(sol::state& lua) {
    for (auto it = pendingCockpits.begin(); it != pendingCockpits.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            try {
                it->first.get();
                lua["print"]("Cockpit module ready: " + it->second);
            } catch (const std::exception& e) {
                Log::error("Cockpits", "Cockpit module {} failed: {}", it->second, e.what());
            }
            it = pendingCockpits.erase(it);
        } else {
            ++it;
        }
    }
}

} // namespace Cockpits
} // namespace MagiTech
