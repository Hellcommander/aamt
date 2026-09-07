#pragma once
#include <sol/sol.hpp>

namespace MagiTech {
namespace WormMechs {

class WormMechLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);
};

} // namespace WormMechs
} // namespace MagiTech
