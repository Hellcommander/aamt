#pragma once
#include <sol/sol.hpp>

namespace MagiTech {
namespace QuadMech {

class QuadMechLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);
    static void shutdown();
};

} // namespace QuadMech
} // namespace MagiTech 
