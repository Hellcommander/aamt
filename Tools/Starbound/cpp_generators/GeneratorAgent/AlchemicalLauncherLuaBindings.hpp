#pragma once
#include <sol/sol.hpp>
#include <memory>

namespace MagiTech {
namespace AlchemicalLaunchers {

class AlchemicalLauncherFactory;

class AlchemicalLauncherLuaBindings {
public:
    static void bind(sol::state& lua);
    // Instance used by the bindings; inject the host's instance with setFactory,
    // otherwise factory() lazily creates a default one.
    static void setFactory(std::shared_ptr<AlchemicalLauncherFactory> factory);
    static std::shared_ptr<AlchemicalLauncherFactory> factory();
    static void poll_assets(sol::state& lua);
};

} // namespace AlchemicalLaunchers
} // namespace MagiTech
