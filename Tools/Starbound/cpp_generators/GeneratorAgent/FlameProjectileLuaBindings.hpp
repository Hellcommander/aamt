#pragma once
#include <sol/sol.hpp>
#include <memory>

namespace MagiTech {
namespace FlameProjectiles {

class FlameProjectileFactory;

class FlameProjectileLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);
    // Factory used by the bindings; inject the host's instance (e.g. MainPlugin's) with setFactory,
    // otherwise factory() lazily initializes and returns the global g_flameFactory.
    static void setFactory(std::shared_ptr<FlameProjectileFactory> factory);
    static std::shared_ptr<FlameProjectileFactory> factory();
};

} // namespace FlameProjectiles
} // namespace MagiTech
