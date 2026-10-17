#pragma once
#include <sol/sol.hpp>
#include <memory>

namespace MagiTech {
namespace HomingMissiles {

class HomingMissileFactory;

class HomingMissileLuaBindings {
public:
    static void bind(sol::state& lua);
    // Instance used by the bindings; inject the host's instance with setFactory,
    // otherwise factory() lazily creates a default one.
    static void setFactory(std::shared_ptr<HomingMissileFactory> factory);
    static std::shared_ptr<HomingMissileFactory> factory();
    static void poll_assets(sol::state& lua);
};

} // namespace HomingMissiles
} // namespace MagiTech
