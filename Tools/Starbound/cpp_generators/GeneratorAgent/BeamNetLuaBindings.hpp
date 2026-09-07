#pragma once
#include <sol/sol.hpp>

namespace MagiTech {
namespace BeamNets {

class BeamNetLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);
};

} // namespace BeamNets
} // namespace MagiTech
