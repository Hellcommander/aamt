#pragma once
#include <sol/sol.hpp>

namespace MagiTech {
namespace AlchemicalLaunchers {

class AlchemicalLauncherLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);
};

} // namespace AlchemicalLaunchers
} // namespace MagiTech
