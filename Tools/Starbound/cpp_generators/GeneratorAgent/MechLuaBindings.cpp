#include "MechLuaBindings.hpp"
#include "MechFactory.hpp"
#include "MechTypes.hpp"
#include "core/plugins/MainPlugin.hpp"
#include <map>
#include <future>
#include <vector>

namespace MagiTech {
namespace Mechs {

static std::vector<std::pair<std::future<MechBundle>, std::string>> pendingMechs;

void MechLuaBindings::bind(sol::state& lua) {
    lua.new_usertype<MechParams>("MechParams",
        "id", &MechParams::id,
        "style", &MechParams::style,
        "forms", &MechParams::forms,
        "colorPrimary", &MechParams::colorPrimary,
        "colorAccent", &MechParams::colorAccent,
        "limbCount", &MechParams::limbCount,
        "torsoSize", &MechParams::torsoSize,
        "limbLength", &MechParams::limbLength,
        "armorPlates", &MechParams::armorPlates,
        "weaponMounts", &MechParams::weaponMounts,
        "pattern", &MechParams::pattern,
        "detailLevel", &MechParams::detailLevel,
        "pulseEmission", &MechParams::pulseEmission
    );

    lua.set_function("spawn_mech", [&](const MechParams& p) {
        auto factory = MainPlugin::instance().getMechFactory();
        auto fut = factory->generateAsync(p);
        pendingMechs.emplace_back(std::move(fut), p.id);
    });
}

void MechLuaBindings::poll_assets(sol::state& lua) {
    for (auto it = pendingMechs.begin(); it != pendingMechs.end(); ) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            auto bundle = it->first.get();
            // world:spawnMech(bundle.mesh, bundle.tex, bundle.skeleton);
            // This would call a Lua function to spawn the mech.
            // For now, we'll just print a message.
            lua["print"]("Mech ready: " + it->second);
            it = pendingMechs.erase(it);
        } else {
            ++it;
        }
    }
}

} // namespace Mechs
} // namespace MagiTech
