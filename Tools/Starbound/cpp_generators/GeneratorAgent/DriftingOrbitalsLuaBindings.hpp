#pragma once
#include <sol/sol.hpp>

namespace MagiTech {
namespace DriftingOrbitals {

class DriftingOrbitalsLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);
};

} // namespace DriftingOrbitals
} // namespace MagiTech
