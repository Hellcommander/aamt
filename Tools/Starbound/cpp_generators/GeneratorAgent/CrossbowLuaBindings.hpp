#pragma once
#include <sol/sol.hpp>

namespace MagiTech {
namespace Crossbows {

class CrossbowLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);
};

} // namespace Crossbows
} // namespace MagiTech
