#pragma once
#include <sol/sol.hpp>
#include <memory>

namespace MagiTech {
namespace GrappleHooks {

class GrappleAssetFactory;

class GrappleHookLuaBindings {
public:
    static void bind(sol::state& lua);
    // Factory used by the bindings; inject the host's instance with setFactory,
    // otherwise factory() lazily creates a default one.
    static void setFactory(std::shared_ptr<GrappleAssetFactory> factory);
    static std::shared_ptr<GrappleAssetFactory> factory();
    static void poll_assets(sol::state& lua);
};

} // namespace GrappleHooks
} // namespace MagiTech
