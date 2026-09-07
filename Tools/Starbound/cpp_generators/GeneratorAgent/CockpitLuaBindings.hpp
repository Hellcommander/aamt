#pragma once
#include <sol/sol.hpp>

namespace MagiTech {
namespace Cockpits {

class CockpitLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);
};

} // namespace Cockpits
} // namespace MagiTech
