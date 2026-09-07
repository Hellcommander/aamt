#pragma once
#include <sol/sol.hpp>

namespace MagiTech {
namespace BarbedExplosiveProjectiles {

class BarbedExplosiveProjectileLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);
};

} // namespace BarbedExplosiveProjectiles
} // namespace MagiTech
