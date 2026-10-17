#include "TrapLuaBindings.hpp"
#include "TrapFactory.hpp"
#include <memory>
#include <mutex>
#include <vector>

namespace MagiTech {
namespace Traps {

static std::vector<std::pair<std::future<TrapAssetBundle>, std::string>> pendingTraps;

namespace {
std::mutex& factoryMutex() {
    static std::mutex m;
    return m;
}
std::shared_ptr<TrapFactory>& factorySlot() {
    static std::shared_ptr<TrapFactory> f;
    return f;
}
} // namespace

void TrapLuaBindings::setFactory(std::shared_ptr<TrapFactory> factory) {
    std::lock_guard<std::mutex> lock(factoryMutex());
    factorySlot() = std::move(factory);
}

std::shared_ptr<TrapFactory> TrapLuaBindings::factory() {
    std::lock_guard<std::mutex> lock(factoryMutex());
    auto& slot = factorySlot();
    if (!slot) {
        // No factory injected (e.g. by MainPlugin): create a default one.
        slot = std::make_shared<TrapFactory>();
        slot->initialize(64, 4);
    }
    return slot;
}

void TrapLuaBindings::bind(sol::state& lua) {
    lua.new_usertype<TrapParams>("TrapParams",
        sol::constructors<TrapParams()>(),
        "id", &TrapParams::id,
        "trapType", &TrapParams::trapType,
        "size", &TrapParams::size,
        "activationType", &TrapParams::activationType,
        "triggerDelay", &TrapParams::triggerDelay,
        "resetTime", &TrapParams::resetTime,
        "autoReset", &TrapParams::autoReset,
        "damageType", &TrapParams::damageType,
        "damageValue", &TrapParams::damageValue,
        "damageRadius", &TrapParams::damageRadius,
        "effectDuration", &TrapParams::effectDuration,
        "spikeCount", &TrapParams::spikeCount,
        "spikeHeight", &TrapParams::spikeHeight,
        "swingAngle", &TrapParams::swingAngle,
        "swingSpeed", &TrapParams::swingSpeed,
        "jetHeight", &TrapParams::jetHeight,
        "jetWidth", &TrapParams::jetWidth,
        "gasRadius", &TrapParams::gasRadius,
        "gasDensity", &TrapParams::gasDensity,
        "pitDepth", &TrapParams::pitDepth,
        "acidType", &TrapParams::acidType
    );

    lua.new_usertype<BehaviorParams>("BehaviorParams",
        sol::constructors<BehaviorParams()>(),
        "detectionRange", &BehaviorParams::detectionRange,
        "resetOnPlayerLeave", &BehaviorParams::resetOnPlayerLeave,
        "randomizeInterval", &BehaviorParams::randomizeInterval,
        "minTriggerInterval", &BehaviorParams::minTriggerInterval,
        "maxTriggerInterval", &BehaviorParams::maxTriggerInterval
    );

    lua.new_usertype<TrapAssetBundle>("TrapAssetBundle",
        "mesh", &TrapAssetBundle::mesh,
        "shader", &TrapAssetBundle::shader,
        "texture", &TrapAssetBundle::texture,
        "physics", &TrapAssetBundle::physics,
        "particleFX", &TrapAssetBundle::particleFX,
        "sfx", &TrapAssetBundle::sfx,
        "icon", &TrapAssetBundle::icon
    );

    lua.set_function("spawn_trap",
        [&](const TrapParams& t, const BehaviorParams& b) {
            auto factory = TrapLuaBindings::factory();
            return factory->generateAsync(t, b).get();
        }
    );

    lua.set_function("spawn_trap_async",
        [&](const TrapParams& t, const BehaviorParams& b) {
            auto factory = TrapLuaBindings::factory();
            auto fut = factory->generateAsync(t, b);
            pendingTraps.emplace_back(std::move(fut), t.id);
        }
    );
}

void TrapLuaBindings::poll_assets(sol::state& lua) {
    for (auto it = pendingTraps.begin(); it != pendingTraps.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            auto b = it->first.get();
            lua["print"]("Trap ready: " + it->second);
            it = pendingTraps.erase(it);
        } else {
            ++it;
        }
    }
}

} // namespace Traps
} // namespace MagiTech
