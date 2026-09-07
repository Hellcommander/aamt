#include "SpellstoneLuaBindings.hpp"
#include "SpellstoneFactory.hpp"
#include "SpellstoneTypes.hpp"
#include "core/plugins/MainPlugin.hpp"
#include <map>
#include <future>
#include <vector>

namespace MagiTech {
namespace Spellstones {

static std::vector<std::pair<std::future<SpellstoneBundle>, std::string>> pendingSpellstones;

void SpellstoneLuaBindings::bind(sol::state& lua) {
    lua.new_usertype<SpellstoneParams>("SpellstoneParams",
        "id", &SpellstoneParams::id,
        "stoneType", &SpellstoneParams::stoneType,
        "baseRadius", &SpellstoneParams::baseRadius,
        "height", &SpellstoneParams::height,
        "facets", &SpellstoneParams::facets,
        "runePattern", &SpellstoneParams::runePattern,
        "glowColor", &SpellstoneParams::glowColor,
        "glowIntensity", &SpellstoneParams::glowIntensity,
        "beamColor", &SpellstoneParams::beamColor,
        "beamWidth", &SpellstoneParams::beamWidth,
        "beamLength", &SpellstoneParams::beamLength,
        "beamTexture", &SpellstoneParams::beamTexture,
        "idleEffect", &SpellstoneParams::idleEffect,
        "castEffect", &SpellstoneParams::castEffect,
        "detailLevel", &SpellstoneParams::detailLevel
    );

    lua.set_function("spawn_spellstone", [&](SpellstoneParams p) {
        auto factory = MainPlugin::instance().getSpellstoneFactory();
        auto fut = factory->generateAsync(p);
        pendingSpellstones.emplace_back(std::move(fut), p.id);
    });
}

void SpellstoneLuaBindings::poll_assets(sol::state& lua) {
    for (auto it = pendingSpellstones.begin(); it != pendingSpellstones.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            auto b = it->first.get();
            // This would call a Lua function to spawn the spellstone.
            // For now, we'll just print a message.
            lua["print"]("Spellstone ready: " + it->second);
            it = pendingSpellstones.erase(it);
        } else {
            ++it;
        }
    }
}

} // namespace Spellstones
} // namespace MagiTech
