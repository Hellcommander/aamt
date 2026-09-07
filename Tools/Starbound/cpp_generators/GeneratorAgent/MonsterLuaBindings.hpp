#pragma once

#include <sol/sol.hpp>

namespace MagiTech {
namespace Monsters {

class MonsterLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);
};

} // namespace Monsters
} // namespace MagiTech
