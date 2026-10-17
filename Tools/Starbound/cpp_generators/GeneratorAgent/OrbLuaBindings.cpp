#include "OrbLuaBindings.hpp"
#include "OrbFactory.hpp"
#include "OrbTypes.hpp"
#include <memory>
#include <mutex>
#include "core/Log.hpp"
#include <map>
#include <future>
#include <vector>

namespace MagiTech {
namespace Orbs {

namespace {
std::mutex& factoryMutex() {
    static std::mutex m;
    return m;
}
std::shared_ptr<OrbFactory>& factorySlot() {
    static std::shared_ptr<OrbFactory> f;
    return f;
}
} // namespace

void OrbLuaBindings::setFactory(std::shared_ptr<OrbFactory> factory) {
    std::lock_guard<std::mutex> lock(factoryMutex());
    factorySlot() = std::move(factory);
}

std::shared_ptr<OrbFactory> OrbLuaBindings::factory() {
    std::lock_guard<std::mutex> lock(factoryMutex());
    auto& slot = factorySlot();
    if (!slot) {
        // No factory injected (e.g. by MainPlugin): create a default one.
        slot = std::make_shared<OrbFactory>();
        slot->initialize(64, 4);
    }
    return slot;
}

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
        auto factory = OrbLuaBindings::factory();
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
