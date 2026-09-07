#pragma once
#include <sol/sol.hpp>

namespace MagiTech {
namespace GrappleHooks {

class GrappleHookLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);
};

} // namespace GrappleHooks
} // namespace MagiTech
