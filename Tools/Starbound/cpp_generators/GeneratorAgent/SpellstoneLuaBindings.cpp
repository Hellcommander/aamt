#include "SpellstoneLuaBindings.hpp"
#include "SpellstoneFactory.hpp"
#include "SpellstoneTypes.hpp"
#include <memory>
#include <mutex>
#include "core/Log.hpp"
#include <map>
#include <future>
#include <vector>

namespace MagiTech {
namespace Spellstones {

namespace {
std::mutex& factoryMutex() {
    static std::mutex m;
    return m;
}
std::shared_ptr<SpellstoneFactory>& factorySlot() {
    static std::shared_ptr<SpellstoneFactory> f;
    return f;
}
} // namespace

void SpellstoneLuaBindings::setFactory(std::shared_ptr<SpellstoneFactory> factory) {
    std::lock_guard<std::mutex> lock(factoryMutex());
    factorySlot() = std::move(factory);
}

std::shared_ptr<SpellstoneFactory> SpellstoneLuaBindings::factory() {
    std::lock_guard<std::mutex> lock(factoryMutex());
    auto& slot = factorySlot();
    if (!slot) {
        // No factory injected (e.g. by MainPlugin): create a default one.
        slot = std::make_shared<SpellstoneFactory>();
        slot->initialize(64, 4);
    }
    return slot;
}

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

    lua.set_function("spawn_spellstone", [](SpellstoneParams p) {
        auto factory = SpellstoneLuaBindings::factory();
        auto fut = factory->generateAsync(p);
        pendingSpellstones.emplace_back(std::move(fut), p.id);
    });
}

void SpellstoneLuaBindings::poll_assets(sol::state& lua) {
    for (auto it = pendingSpellstones.begin(); it != pendingSpellstones.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            try {
                auto b = it->first.get();
                lua["print"]("Spellstone ready: " + it->second);
            } catch (const std::exception& e) {
                Log::error("Spellstones", "Asset generation failed for {}: {}", it->second, e.what());
            }
            it = pendingSpellstones.erase(it);
        } else {
            ++it;
        }
    }
}

} // namespace Spellstones
} // namespace MagiTech
