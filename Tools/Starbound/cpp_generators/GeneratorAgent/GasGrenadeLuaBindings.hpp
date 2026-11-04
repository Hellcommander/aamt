#pragma once
#include <sol/sol.hpp>
#include <memory>

namespace MagiTech {
namespace GasGrenades {

class GasGrenadeFactory;

class GasGrenadeLuaBindings {
public:
    static void bind(sol::state& lua);
    // Factory used by the bindings; inject the host's instance with setFactory,
    // otherwise factory() lazily creates a default one.
    static void setFactory(std::shared_ptr<GasGrenadeFactory> factory);
    static std::shared_ptr<GasGrenadeFactory> factory();
    static void poll_assets(sol::state& lua);
};

} // namespace GasGrenades
} // namespace MagiTech
