#pragma once
#include <sol/sol.hpp>

namespace MagiTech {

class TileLibraryLuaBindings {
public:
    static void bind(sol::state& lua);
    static void update(sol::state& lua);
};

} // namespace MagiTech 
