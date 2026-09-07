#pragma once
#include <sol/sol.hpp>

namespace MagiTech {
namespace PlasmaDiscs {

class PlasmaDiscLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);
};

} // namespace PlasmaDiscs
} // namespace MagiTech
