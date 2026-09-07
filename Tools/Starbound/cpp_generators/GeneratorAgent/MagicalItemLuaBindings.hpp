#pragma once

#include <sol/sol.hpp>

namespace MagiTech {
namespace MagicalItems {

class MagicalItemLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);
};

} // namespace MagicalItems
} // namespace MagiTech
