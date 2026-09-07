#include "BeamLuaBindings.hpp"
#include "BeamFactory.hpp"
#include "BeamTypes.hpp"
#include "core/plugins/MainPlugin.hpp"
#include <map>
#include <future>
#include <vector>

namespace MagiTech {
namespace Beams {

static std::vector<std::pair<std::future<BeamBundle>, std::string>> pendingBeams;

void BeamLuaBindings::bind(sol::state& lua) {
    lua.new_usertype<BeamParams>("BeamParams",
        "id", &BeamParams::id,
        "beamType", &BeamParams::beamType,
        "length", &BeamParams::length,
        "width", &BeamParams::width,
        "segments", &BeamParams::segments,
        "colorInner", &BeamParams::colorInner,
        "colorOuter", &BeamParams::colorOuter,
        "noiseIntensity", &BeamParams::noiseIntensity,
        "noiseScale", &BeamParams::noiseScale,
        "flickerRate", &BeamParams::flickerRate,
        "scrollSpeed", &BeamParams::scrollSpeed,
        "muzzleEffect", &BeamParams::muzzleEffect,
        "impactEffect", &BeamParams::impactEffect,
        "collisionDecal", &BeamParams::collisionDecal,
        "detailLevel", &BeamParams::detailLevel
    );

    lua.set_function("spawn_beam", [&](BeamParams p) {
        auto factory = MainPlugin::instance().getBeamFactory();
        auto fut = factory->generateAsync(p);
        pendingBeams.emplace_back(std::move(fut), p.id);
    });
}

void BeamLuaBindings::poll_assets(sol::state& lua) {
    for (auto it = pendingBeams.begin(); it != pendingBeams.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            auto b = it->first.get();
            // This would call a Lua function to spawn the beam.
            // For now, we'll just print a message.
            lua["print"]("Beam ready: " + it->second);
            it = pendingBeams.erase(it);
        } else {
            ++it;
        }
    }
}

} // namespace Beams
} // namespace MagiTech
