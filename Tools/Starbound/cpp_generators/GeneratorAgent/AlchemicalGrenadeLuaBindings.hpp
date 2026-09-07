#pragma once
#include <sol/sol.hpp>

namespace MagiTech {
namespace AlchemicalGrenades {

class AlchemicalGrenadeLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);
};

} // namespace AlchemicalGrenades
} // namespace MagiTech
