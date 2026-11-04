#pragma once
#include <sol/sol.hpp>
#include <memory>

namespace MagiTech {
namespace Cockpits {

class CockpitFactory;

class CockpitLuaBindings {
public:
    static void bind(sol::state& lua);
    // Factory used by the bindings; inject the host's instance with setFactory,
    // otherwise factory() lazily creates a default one.
    static void setFactory(std::shared_ptr<CockpitFactory> factory);
    static std::shared_ptr<CockpitFactory> factory();
    static void poll_assets(sol::state& lua);
};

} // namespace Cockpits
} // namespace MagiTech
