#pragma once
#include <sol/sol.hpp>

namespace MagiTech {
namespace SnakeMechs {

class SnakeMechLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);
};

} // namespace SnakeMechs
} // namespace MagiTech
