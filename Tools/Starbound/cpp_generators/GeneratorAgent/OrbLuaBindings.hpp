#pragma once

#include <sol/sol.hpp>

namespace MagiTech {
namespace Orbs {

class OrbLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);
};

} // namespace Orbs
} // namespace MagiTech
