#pragma once
#include <sol/sol.hpp>

namespace MagiTech {
namespace Traps {

class TrapLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);
};

} // namespace Traps
} // namespace MagiTech
