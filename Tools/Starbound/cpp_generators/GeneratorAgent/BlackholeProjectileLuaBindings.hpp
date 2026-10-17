#pragma once
#include <sol/sol.hpp>
#include <memory>

namespace MagiTech {
namespace BlackholeProjectiles {

class BlackholeProjectileFactory;

class BlackholeProjectileLuaBindings {
public:
    static void bind(sol::state& lua);
    // Factory used by the bindings; inject the host's instance with setFactory,
    // otherwise factory() lazily creates a default one.
    static void setFactory(std::shared_ptr<BlackholeProjectileFactory> factory);
    static std::shared_ptr<BlackholeProjectileFactory> factory();
    static void poll_assets(sol::state& lua);
    static void cleanup();
};

} // namespace BlackholeProjectiles
} // namespace MagiTech
