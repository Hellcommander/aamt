#pragma once
#include <sol/sol.hpp>
#include <memory>

namespace MagiTech {
namespace ExplosiveProjectiles {

class ExplosiveProjectileFactory;

class ExplosiveProjectileLuaBindings {
public:
    static void bind(sol::state& lua);
    // Instance used by the bindings; inject the host's instance with setFactory,
    // otherwise factory() lazily creates a default one.
    static void setFactory(std::shared_ptr<ExplosiveProjectileFactory> factory);
    static std::shared_ptr<ExplosiveProjectileFactory> factory();
    static void poll_assets(sol::state& lua);
};

} // namespace ExplosiveProjectiles
} // namespace MagiTech
