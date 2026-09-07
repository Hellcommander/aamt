#pragma once
#include <sol/sol.hpp>

namespace MagiTech {
namespace GyroProjectiles {

class GyroProjectileLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);
};

} // namespace GyroProjectiles
} // namespace MagiTech
