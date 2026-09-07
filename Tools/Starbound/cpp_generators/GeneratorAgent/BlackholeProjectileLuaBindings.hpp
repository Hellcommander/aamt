#pragma once
#include <sol/sol.hpp>

namespace MagiTech {
namespace BlackholeProjectiles {

class BlackholeProjectileLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);
    static void cleanup();
};

} // namespace BlackholeProjectiles
} // namespace MagiTech
