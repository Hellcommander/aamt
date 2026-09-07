#pragma once
#include <sol/sol.hpp>

namespace MagiTech {
namespace GasGrenades {

class GasGrenadeLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);
};

} // namespace GasGrenades
} // namespace MagiTech
