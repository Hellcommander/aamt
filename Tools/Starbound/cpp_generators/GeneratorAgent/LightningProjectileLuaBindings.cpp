#include "LightningProjectileLuaBindings.hpp"
#include "LightningProjectileFactory.hpp"
#include <chrono>
#include <memory>
#include <mutex>
#include <vector>

namespace MagiTech {
namespace LightningProjectiles {

static std::vector<std::pair<std::future<LightningBundle>, std::string>> pendingBolts;

namespace {
std::mutex& factoryMutex() {
    static std::mutex m;
    return m;
}
std::shared_ptr<LightningProjectileFactory>& factorySlot() {
    static std::shared_ptr<LightningProjectileFactory> f;
    return f;
}
} // namespace

void LightningProjectileLuaBindings::setFactory(std::shared_ptr<LightningProjectileFactory> factory) {
    std::lock_guard<std::mutex> lock(factoryMutex());
    factorySlot() = std::move(factory);
}

std::shared_ptr<LightningProjectileFactory> LightningProjectileLuaBindings::factory() {
    std::lock_guard<std::mutex> lock(factoryMutex());
    auto& slot = factorySlot();
    if (!slot) {
        // No factory injected (e.g. by MainPlugin): create a default one.
        slot = std::make_shared<LightningProjectileFactory>();
        slot->initialize(64, 4);
    }
    return slot;
}

void LightningProjectileLuaBindings::bind(sol::state& lua) {
    lua.new_usertype<LightningProjectileParams>("LightningProjectileParams",
        sol::constructors<LightningProjectileParams()>(),
        "id", &LightningProjectileParams::id,
        "length", &LightningProjectileParams::length,
        "thickness", &LightningProjectileParams::thickness,
        "mainColor", &LightningProjectileParams::mainColor,
        "glowColor", &LightningProjectileParams::glowColor,
        "noiseIntensity", &LightningProjectileParams::noiseIntensity,
        "noiseScale", &LightningProjectileParams::noiseScale,
        "flickerSpeed", &LightningProjectileParams::flickerSpeed,
        "branchCount", &LightningProjectileParams::branchCount,
        "branchLengthFactor", &LightningProjectileParams::branchLengthFactor,
        "jitterAmplitude", &LightningProjectileParams::jitterAmplitude,
        "jitterFrequency", &LightningProjectileParams::jitterFrequency,
        "arcWidthVariation", &LightningProjectileParams::arcWidthVariation,
        "pulseFrequency", &LightningProjectileParams::pulseFrequency,
        "trailType", &LightningProjectileParams::trailType,
        "trailLength", &LightningProjectileParams::trailLength,
        "sparkCount", &LightningProjectileParams::sparkCount,
        "sparkLifetime", &LightningProjectileParams::sparkLifetime,
        "sparkColor", &LightningProjectileParams::sparkColor,
        "soundPitch", &LightningProjectileParams::soundPitch
    );

    lua.new_usertype<LightningBundle>("LightningBundle",
        "mesh", &LightningBundle::mesh,
        "shader", &LightningBundle::shader,
        "texture", &LightningBundle::texture,
        "sparks", &LightningBundle::sparks,
        "sfx", &LightningBundle::sfx
    );

    // Fully initialized preset to start from (a bare LightningProjectileParams() leaves fields unset)
    lua.set_function("lightning_projectile_default_params", []() {
        return LightningProjectileFactory::defaultParams();
    });

    lua.set_function("spawn_lightning_projectile",
        [](const LightningProjectileParams& p) {
            auto factory = LightningProjectileLuaBindings::factory();
            return factory->generateAsync(p).get();
        }
    );

    lua.set_function("spawn_lightning_projectile_async",
        [](const LightningProjectileParams& p) {
            auto factory = LightningProjectileLuaBindings::factory();
            auto fut = factory->generateAsync(p);
            pendingBolts.emplace_back(std::move(fut), p.id);
        }
    );
}

void LightningProjectileLuaBindings::poll_assets(sol::state& lua) {
    for (auto it = pendingBolts.begin(); it != pendingBolts.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            auto b = it->first.get();
            lua["print"]("Lightning Bolt ready: " + it->second);
            it = pendingBolts.erase(it);
        } else {
            ++it;
        }
    }
}

} // namespace LightningProjectiles
} // namespace MagiTech
