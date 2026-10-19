#include "FrostNovaLuaBindings.hpp"
#include "FrostNovaFactory.hpp"
#include <memory>
#include <mutex>
#include "core/Log.hpp"
#include <vector>

namespace MagiTech {
namespace FrostNovas {

namespace {
std::mutex& factoryMutex() {
    static std::mutex m;
    return m;
}
std::shared_ptr<FrostNovaFactory>& factorySlot() {
    static std::shared_ptr<FrostNovaFactory> f;
    return f;
}
} // namespace

void FrostNovaLuaBindings::setFactory(std::shared_ptr<FrostNovaFactory> factory) {
    std::lock_guard<std::mutex> lock(factoryMutex());
    factorySlot() = std::move(factory);
}

std::shared_ptr<FrostNovaFactory> FrostNovaLuaBindings::factory() {
    std::lock_guard<std::mutex> lock(factoryMutex());
    auto& slot = factorySlot();
    if (!slot) {
        // No factory injected (e.g. by MainPlugin): create a default one.
        slot = std::make_shared<FrostNovaFactory>();
        slot->initialize(64, 4);
    }
    return slot;
}

static std::vector<std::pair<std::future<FrostNovaAssetBundle>, std::string>> pendingNovas;

void FrostNovaLuaBindings::bind(sol::state& lua) {
    lua.new_usertype<FrostNovaParams>("FrostNovaParams",
        sol::constructors<FrostNovaParams()>(),
        "id", &FrostNovaParams::id,
        "ringRadius", &FrostNovaParams::ringRadius,
        "ringThickness", &FrostNovaParams::ringThickness,
        "expansionDuration", &FrostNovaParams::expansionDuration,
        "auraParticleCount", &FrostNovaParams::auraParticleCount,
        "auraLifetime", &FrostNovaParams::auraLifetime,
        "auraSpawnRate", &FrostNovaParams::auraSpawnRate,
        "shardCount", &FrostNovaParams::shardCount,
        "shardMinLength", &FrostNovaParams::shardMinLength,
        "shardMaxLength", &FrostNovaParams::shardMaxLength,
        "shardMinWidth", &FrostNovaParams::shardMinWidth,
        "shardMaxWidth", &FrostNovaParams::shardMaxWidth,
        "shardSpeedMin", &FrostNovaParams::shardSpeedMin,
        "shardSpeedMax", &FrostNovaParams::shardSpeedMax,
        "shardSpreadAngleDeg", &FrostNovaParams::shardSpreadAngleDeg,
        "frostDecalRadius", &FrostNovaParams::frostDecalRadius,
        "frostDecalDuration", &FrostNovaParams::frostDecalDuration,
        "ringColor", &FrostNovaParams::ringColor,
        "shardColor", &FrostNovaParams::shardColor,
        "refractionStrength", &FrostNovaParams::refractionStrength
    );

    lua.new_usertype<FrostNovaAssetBundle>("FrostNovaAssetBundle",
        sol::no_constructor,
        "ringMesh", &FrostNovaAssetBundle::ringMesh,
        "shardMesh", &FrostNovaAssetBundle::shardMesh,
        "auraParticles", &FrostNovaAssetBundle::auraParticles,
        "sparkleParticles", &FrostNovaAssetBundle::sparkleParticles,
        "frostShader", &FrostNovaAssetBundle::frostShader,
        "frostDecal", &FrostNovaAssetBundle::frostDecal
    );

    lua.set_function("cast_frost_nova",
        [](const FrostNovaParams& p) {
            auto factory = FrostNovaLuaBindings::factory();
            return factory->generateAsync(p).get();
        }
    );

    lua.set_function("cast_frost_nova_async",
        [](const FrostNovaParams& p) {
            auto factory = FrostNovaLuaBindings::factory();
            pendingNovas.emplace_back(factory->generateAsync(p), p.id);
        }
    );
}

void FrostNovaLuaBindings::poll_assets(sol::state& lua) {
    for (auto it = pendingNovas.begin(); it != pendingNovas.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            try {
                auto b = it->first.get();
                lua["print"]("Frost nova ready: " + it->second);
            } catch (const std::exception& e) {
                Log::error("FrostNovas", "Asset generation failed for {}: {}", it->second, e.what());
            }
            it = pendingNovas.erase(it);
        } else {
            ++it;
        }
    }
}

} // namespace FrostNovas
} // namespace MagiTech
