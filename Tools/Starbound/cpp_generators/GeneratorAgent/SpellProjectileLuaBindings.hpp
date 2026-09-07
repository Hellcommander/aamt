#pragma once
#include <sol/sol.hpp>

namespace MagiTech {
namespace SpellProjectiles {

class SpellProjectileLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);
};

} // namespace SpellProjectiles
} // namespace MagiTech
