#pragma once
#include <sol/sol.hpp>

namespace MagiTech {
namespace ShotgunPellets {

class ShotgunPelletLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);
};

} // namespace ShotgunPellets
} // namespace MagiTech
