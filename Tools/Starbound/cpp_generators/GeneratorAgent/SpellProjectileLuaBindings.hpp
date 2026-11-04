#pragma once
#include <sol/sol.hpp>
#include <memory>

namespace MagiTech {
namespace SpellProjectiles {

class SpellAssetFactory;

class SpellProjectileLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);
    // Factory used by the bindings; inject the host's instance (e.g. MainPlugin's) with setFactory,
    // otherwise factory() lazily creates and initializes a default one.
    static void setFactory(std::shared_ptr<SpellAssetFactory> factory);
    static std::shared_ptr<SpellAssetFactory> factory();
};

} // namespace SpellProjectiles
} // namespace MagiTech
