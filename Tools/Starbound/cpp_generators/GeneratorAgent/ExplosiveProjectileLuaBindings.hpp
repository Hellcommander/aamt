#pragma once
#include <sol/sol.hpp>

namespace MagiTech {
namespace ExplosiveProjectiles {

class ExplosiveProjectileLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);
};

} // namespace ExplosiveProjectiles
} // namespace MagiTech
