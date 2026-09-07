#pragma once
#include <sol/sol.hpp>

namespace MagiTech {
namespace FlameProjectiles {

class FlameProjectileLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);
};

} // namespace FlameProjectiles
} // namespace MagiTech
