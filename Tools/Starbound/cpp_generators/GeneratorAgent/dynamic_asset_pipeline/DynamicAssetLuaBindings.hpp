#pragma once

#include <sol/sol.hpp>
#include <memory>

namespace MagiTech {
namespace DynamicAssets {

class DynamicAssetManager;

class DynamicAssetLuaBindings {
public:
    static void bind(sol::state& lua);
    // Instance used by the bindings; inject the host's instance with setManager,
    // otherwise manager() lazily creates a default one.
    static void setManager(std::shared_ptr<DynamicAssetManager> manager);
    static std::shared_ptr<DynamicAssetManager> manager();
    static void poll_assets(sol::state& lua);
};

} // namespace DynamicAssets
} // namespace MagiTech
