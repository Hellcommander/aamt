#pragma once
#include <sol/sol.hpp>

namespace MagiTech {
namespace HomingMissiles {

class HomingMissileLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);
};

} // namespace HomingMissiles
} // namespace MagiTech
