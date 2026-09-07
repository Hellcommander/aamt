#pragma once
#include <sol/sol.hpp>

namespace MagiTech {
namespace CometProjectiles {

class CometProjectileLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);
};

} // namespace CometProjectiles
} // namespace MagiTech
