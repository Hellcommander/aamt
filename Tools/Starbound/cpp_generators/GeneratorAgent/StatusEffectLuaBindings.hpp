#pragma once

#include <sol/sol.hpp>

namespace MagiTech {
namespace StatusEffects {

class StatusEffectLuaBindings {
public:
    static void bind(sol::state& lua);
    static void cleanup();
};

} // namespace StatusEffects
} // namespace MagiTech
