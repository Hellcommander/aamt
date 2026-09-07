#include "OrbLuaBindings.hpp"
#include "OrbFactory.hpp"
#include "OrbTypes.hpp"
#include "core/plugins/MainPlugin.hpp"
#include <map>
#include <future>
#include <vector>

namespace MagiTech {
namespace Orbs {

static std::vector<std::pair<std::future<OrbBundle>, std::string>> pendingOrbs;

void OrbLuaBindings::bind(sol::state& lua) {
    lua.new_usertype<OrbParams>("OrbParams",
        "id", &OrbParams::id,
        "orbType", &OrbParams::orbType,
        "radius", &OrbParams::radius,
        "coreColor", &OrbParams::coreColor,
        "shellColor", &OrbParams::shellColor,
        "runePattern", &OrbParams::runePattern,
        "runeDensity", &OrbParams::runeDensity,
        "auraIntensity", &OrbParams::auraIntensity,
        "trailEffect", &OrbParams::trailEffect,
        "gravitationalPull", &OrbParams::gravitationalPull,
        "spellAffinity", &OrbParams::spellAffinity,
        "detailLevel", &OrbParams::detailLevel
    );

    lua.set_function("spawn_orb", [&](OrbParams p) {
        auto factory = MainPlugin::instance().getOrbFactory();
        auto fut = factory->generateAsync(p);
        pendingOrbs.emplace_back(std::move(fut), p.id);
    });
}

void OrbLuaBindings::poll_assets(sol::state& lua) {
    for (auto it = pendingOrbs.begin(); it != pendingOrbs.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            auto b = it->first.get();
            // This would call a Lua function to spawn the orb.
            // For now, we'll just print a message.
            lua["print"]("Orb ready: " + it->second);
            it = pendingOrbs.erase(it);
        } else {
            ++it;
        }
    }
}

} // namespace Orbs
} // namespace MagiTech
