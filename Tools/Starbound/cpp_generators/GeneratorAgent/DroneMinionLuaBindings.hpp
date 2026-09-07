#pragma once
#include <sol/sol.hpp>

namespace MagiTech {
namespace DroneMinions {

class DroneMinionLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);
};

} // namespace DroneMinions
} // namespace MagiTech
