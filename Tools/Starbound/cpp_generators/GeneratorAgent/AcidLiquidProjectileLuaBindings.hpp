#pragma once
#include <sol/sol.hpp>

namespace MagiTech {
namespace AcidLiquidProjectiles {

class AcidLiquidProjectileLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);
};

} // namespace AcidLiquidProjectiles
} // namespace MagiTech
