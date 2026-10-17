#include "MagicalItemLuaBindings.hpp"
#include "MagicalItemFactory.hpp"
#include "MagicalItemTypes.hpp"
#include <memory>
#include <mutex>
#include "core/Log.hpp"
#include <map>
#include <future>
#include <vector>

namespace MagiTech {
namespace MagicalItems {

namespace {
std::mutex& factoryMutex() {
    static std::mutex m;
    return m;
}
std::shared_ptr<MagicalItemFactory>& factorySlot() {
    static std::shared_ptr<MagicalItemFactory> f;
    return f;
}
} // namespace

void MagicalItemLuaBindings::setFactory(std::shared_ptr<MagicalItemFactory> factory) {
    std::lock_guard<std::mutex> lock(factoryMutex());
    factorySlot() = std::move(factory);
}

std::shared_ptr<MagicalItemFactory> MagicalItemLuaBindings::factory() {
    std::lock_guard<std::mutex> lock(factoryMutex());
    auto& slot = factorySlot();
    if (!slot) {
        // No factory injected (e.g. by MainPlugin): create a default one.
        slot = std::make_shared<MagicalItemFactory>();
        slot->initialize(64, 4);
    }
    return slot;
}

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
        auto factory = MagicalItemLuaBindings::factory();
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
