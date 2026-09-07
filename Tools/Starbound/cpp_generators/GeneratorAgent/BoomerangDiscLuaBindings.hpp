#pragma once
#include <sol/sol.hpp>

namespace MagiTech {
namespace BoomerangDiscs {

class BoomerangDiscLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);
};

} // namespace BoomerangDiscs
} // namespace MagiTech
