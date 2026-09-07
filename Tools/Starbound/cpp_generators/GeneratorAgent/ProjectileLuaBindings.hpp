#pragma once

#include <sol/sol.hpp>

namespace MagiTech {
namespace Projectiles {

class ProjectileLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);
};

} // namespace Projectiles
} // namespace MagiTech
