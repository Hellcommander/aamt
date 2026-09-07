#include "MagicalItemLuaBindings.hpp"
#include "MagicalItemFactory.hpp"
#include "MagicalItemTypes.hpp"
#include "core/plugins/MainPlugin.hpp"
#include <map>
#include <future>
#include <vector>

namespace MagiTech {
namespace MagicalItems {

static std::vector<std::pair<std::future<MagicalItemBundle>, std::string>> pendingItems;

void MagicalItemLuaBindings::bind(sol::state& lua) {
    lua.new_usertype<MagicalItemParams>("MagicalItemParams",
        "id", &MagicalItemParams::id,
        "itemType", &MagicalItemParams::itemType,
        "length", &MagicalItemParams::length,
        "coreCrystal", &MagicalItemParams::coreCrystal,
        "shaftMaterial", &MagicalItemParams::shaftMaterial,
        "gripWrap", &MagicalItemParams::gripWrap,
        "runePattern", &MagicalItemParams::runePattern,
        "runeDensity", &MagicalItemParams::runeDensity,
        "gemCount", &MagicalItemParams::gemCount,
        "barrelCount", &MagicalItemParams::barrelCount,
        "chamberCapacity", &MagicalItemParams::chamberCapacity,
        "elementalAffinity", &MagicalItemParams::elementalAffinity,
        "auraEffect", &MagicalItemParams::auraEffect,
        "muzzleFlash", &MagicalItemParams::muzzleFlash,
        "recoilMounts", &MagicalItemParams::recoilMounts,
        "detailLevel", &MagicalItemParams::detailLevel,
        "colorPrimary", &MagicalItemParams::colorPrimary,
        "colorAccent", &MagicalItemParams::colorAccent
    );

    lua.set_function("spawn_item", [&](MagicalItemParams p) {
        auto factory = MainPlugin::instance().getMagicalItemFactory();
        auto fut = factory->generateAsync(p);
        pendingItems.emplace_back(std::move(fut), p.id);
    });
}

void MagicalItemLuaBindings::poll_assets(sol::state& lua) {
    for (auto it = pendingItems.begin(); it != pendingItems.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            auto b = it->first.get();
            // This would call a Lua function to spawn the item.
            // For now, we'll just print a message.
            lua["print"]("Magical Item ready: " + it->second);
            it = pendingItems.erase(it);
        } else {
            ++it;
        }
    }
}

} // namespace MagicalItems
} // namespace MagiTech
