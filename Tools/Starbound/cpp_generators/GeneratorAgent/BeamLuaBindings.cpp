#include "BeamLuaBindings.hpp"
#include "BeamFactory.hpp"
#include "BeamTypes.hpp"
#include <memory>
#include <mutex>
#include "core/Log.hpp"
#include <map>
#include <future>
#include <vector>

namespace MagiTech {
namespace Beams {

namespace {
std::mutex& factoryMutex() {
    static std::mutex m;
    return m;
}
std::shared_ptr<BeamFactory>& factorySlot() {
    static std::shared_ptr<BeamFactory> f;
    return f;
}
} // namespace

void BeamLuaBindings::setFactory(std::shared_ptr<BeamFactory> factory) {
    std::lock_guard<std::mutex> lock(factoryMutex());
    factorySlot() = std::move(factory);
}

std::shared_ptr<BeamFactory> BeamLuaBindings::factory() {
    std::lock_guard<std::mutex> lock(factoryMutex());
    auto& slot = factorySlot();
    if (!slot) {
        // No factory injected (e.g. by MainPlugin): create a default one.
        slot = std::make_shared<BeamFactory>();
        slot->initialize(64, 4);
    }
    return slot;
}

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
        auto factory = BeamLuaBindings::factory();
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
