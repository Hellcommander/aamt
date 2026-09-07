#pragma once
#include <sol/sol.hpp>

namespace MagiTech {
namespace SnakeSpells {

class SnakeSpellLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);
};

} // namespace SnakeSpells
} // namespace MagiTech
