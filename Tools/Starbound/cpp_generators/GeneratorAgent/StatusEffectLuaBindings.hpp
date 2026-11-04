#pragma once

#include <sol/sol.hpp>
#include <memory>

namespace MagiTech {
namespace StatusEffects {

class StatusEffectFactory;

class StatusEffectLuaBindings {
public:
    static void bind(sol::state& lua);
    static void cleanup();
    // Factory used by the bindings; inject the host's instance with setFactory,
    // otherwise factory() lazily creates a default one.
    static void setFactory(std::shared_ptr<StatusEffectFactory> factory);
    static std::shared_ptr<StatusEffectFactory> factory();
};

} // namespace StatusEffects
} // namespace MagiTech
