#pragma once
#include <sol/sol.hpp>

namespace MagiTech {
namespace ClusterBombs {

class ClusterBombLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);
};

} // namespace ClusterBombs
} // namespace MagiTech
