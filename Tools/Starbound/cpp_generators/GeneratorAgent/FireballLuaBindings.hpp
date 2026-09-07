#pragma once
#include <sol/sol.hpp>

namespace MagiTech {
namespace Fireballs {

class FireballLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);
};

} // namespace Fireballs
} // namespace MagiTech
