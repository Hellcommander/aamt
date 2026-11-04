#include "BarbedExplosiveProjectileLuaBindings.hpp"
#include "BarbedExplosiveProjectileFactory.hpp"
#include <memory>
#include <mutex>
#include <vector>

namespace MagiTech {
namespace BarbedExplosiveProjectiles {

static std::vector<std::pair<std::future<BarbedExplosiveProjectileBundle>, std::string>> pendingProjectiles;

namespace {
std::mutex& factoryMutex() {
    static std::mutex m;
    return m;
}
std::shared_ptr<BarbedExplosiveProjectileFactory>& factorySlot() {
    static std::shared_ptr<BarbedExplosiveProjectileFactory> f;
    return f;
}
} // namespace

void BarbedExplosiveProjectileLuaBindings::setFactory(std::shared_ptr<BarbedExplosiveProjectileFactory> factory) {
    std::lock_guard<std::mutex> lock(factoryMutex());
    factorySlot() = std::move(factory);
}

std::shared_ptr<BarbedExplosiveProjectileFactory> BarbedExplosiveProjectileLuaBindings::factory() {
    std::lock_guard<std::mutex> lock(factoryMutex());
    auto& slot = factorySlot();
    if (!slot) {
        // No factory injected (e.g. by MainPlugin): create a default one.
        slot = std::make_shared<BarbedExplosiveProjectileFactory>();
        slot->initialize(4);
    }
    return slot;
}

void BarbedExplosiveProjectileLuaBindings::bind(sol::state& lua) {
    lua.new_usertype<GeometryParams>("GeometryParams", sol::constructors<GeometryParams()>(),
        "length", &GeometryParams::length, "radius", &GeometryParams::radius,
        "numBarbs", &GeometryParams::numBarbs, "barbLength", &GeometryParams::barbLength,
        "barbThickness", &GeometryParams::barbThickness, "barbCurvature", &GeometryParams::barbCurvature);

    lua.new_usertype<ExplosionParams>("ExplosionParams", sol::constructors<ExplosionParams()>(),
        "radius", &ExplosionParams::radius, "impulseStrength", &ExplosionParams::impulseStrength,
        "particleCount", &ExplosionParams::particleCount, "particleLifespan", &ExplosionParams::particleLifespan,
        "shardSize", &ExplosionParams::shardSize, "shardVelocity", &ExplosionParams::shardVelocity);

    lua.new_usertype<VisualParams>("VisualParams", sol::constructors<VisualParams()>(),
        "baseColor", &VisualParams::baseColor, "dirtVariation", &VisualParams::dirtVariation,
        "emissiveIntensity", &VisualParams::emissiveIntensity, "specularHighlight", &VisualParams::specularHighlight);

    lua.new_usertype<BarbedExplosiveProjectileBundle>("BarbedExplosiveProjectileBundle", sol::no_constructor,
        "lods", &BarbedExplosiveProjectileBundle::lods, "material", &BarbedExplosiveProjectileBundle::material,
        "explosionEffect", &BarbedExplosiveProjectileBundle::explosionEffect);

    lua.set_function("generateBarbProj",
        [](const GeometryParams& gp, const ExplosionParams& ep, const VisualParams& vp) {
            auto factory = BarbedExplosiveProjectileLuaBindings::factory();
            auto id = std::to_string(gp.hashKey() ^ ep.hashKey() ^ vp.hashKey());
            pendingProjectiles.emplace_back(factory->generateAsync(gp, ep, vp), id);
        }
    );
}

void BarbedExplosiveProjectileLuaBindings::poll_assets(sol::state& lua) {
    for (auto it = pendingProjectiles.begin(); it != pendingProjectiles.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            try {
                auto b = it->first.get();
                lua["print"]("Barbed explosive projectile asset ready: " + it->second);
            } catch (const std::exception& e) { /* log error */ }
            it = pendingProjectiles.erase(it);
        } else { ++it; }
    }
}

} // namespace BarbedExplosiveProjectiles
} // namespace MagiTech
